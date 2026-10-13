#!/usr/bin/env python3
"""
scripts/reanchor_retrieval_goldens.py — re-anchor a stale retrieval golden set
=============================================================================
BUG-717 (this file's own defect, found 2026-10-11 by forensic audit)
-------------------------------------------------------------------
The v1 generator screened candidates with `search_hybrid(..., rerank=False)`,
i.e. the legacy RRF leg, and its docstring claimed that WAS "the SERVING path".
Production is `retrieval.method: vector` + `rerank.enabled: true` (D-2724), so the
table it produced was evidence about a leg the system does not serve. It also
auto-proposed rank-1 as the expected anchor, which invited a rubber-stamp of a
coin flip: measured, hybrid rank-1 and the production leg's rank-1 DISAGREE on the
same query ("how to build resilient distributed systems" -> hybrid "Golden Goose
System Creation" vs vector "Zapatista Power Dispersion Network").

v2 (this file) changes THREE things and nothing else:
  1. the leg is the PRODUCTION leg from config (overridable, and the leg actually
     used is printed into the artifact header — no unverifiable "serving path" claim);
  2. rank-1 is EVIDENCE, not a proposal: every candidate row carries the reviewer's
     readable fields (name + definition snippet) and the leg's score, and `decision`
     is blank until a human writes it;
  3. the emitted golden draft anchors by NAME (`expected_names`, D-2939), so it
     survives the next reprocess instead of rotting with the next content hash.

CALIBRATION HONESTY (measured 2026-10-11, do not turn this into a threshold)
---------------------------------------------------------------------------
The cross-encoder (BAAI/bge-reranker-v2-m3) ORDERS correctly — a known-positive
pair scores -6.76 against -11.05 for an unrelated pair — but its logits are NOT
calibrated in absolute terms: the self-retrieval distribution spans -6.01..+8.63
with median +0.06. An absolute cut like "top1 < 0 => no answer" would therefore be
a hallucinated gate on this corpus. Scores are recorded as EVIDENCE only. A
relative margin is reported and is likewise evidence only.

Owner action (D-2898: no agent mints a LABEL): read each candidate NAME and mark
`decision` = anchor | rewrite-query | retire-query | ambiguous. The NAME is then
the anchor and the id is resolved per run by pipeline/golden.py.

C12: top-N, leg, paths from config. C16: a query with no candidate is loud.
No store writes; never edits config/golden/retrieval_queries.yaml.

Usage:
    python3 scripts/reanchor_retrieval_goldens.py                 # production leg
    python3 scripts/reanchor_retrieval_goldens.py --no-rerank     # A/B the pool
    python3 scripts/reanchor_retrieval_goldens.py --top 8
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_paths import CANONICAL_RUN, RERANK_ENABLED, RETRIEVAL_METHOD  # noqa: E402
from pipeline.golden import load_golden, resolve_name  # noqa: E402
from pipeline.retrieve import get_conn, search  # noqa: E402

STAMP: str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
CFG_PATH: Path = PROJECT_ROOT / "config" / "pipeline_config.yaml"
GOLDEN_PATH: Path = PROJECT_ROOT / "config" / "golden" / "retrieval_queries.yaml"
with open(CFG_PATH) as _f:
    _CFG: dict = yaml.safe_load(_f) or {}
_BENCH: dict = _CFG.get("retrieval_benchmark", {})
REANCHOR_CFG: dict = _BENCH.get("reanchor", {})
DEFAULT_TOP: int = int(REANCHOR_CFG.get("candidates", 5))
SNIPPET_CHARS: int = int(REANCHOR_CFG.get("snippet_chars", 220))
CSV_OUT: Path = PROJECT_ROOT / "governance" / "golden_reanchor_candidates_20261011.csv"
YAML_OUT: Path = PROJECT_ROOT / "governance" / "golden_reanchor_proposed_20261011.yaml"
# D-2987: the vocabulary has ONE home (config/pipeline_config.yaml -> retrieval_benchmark.reanchor).
# MEASURED 2026-10-13: it existed ONLY as this literal, and TWO consecutive session handoffs (D-2985, D-2986)
# told the owner to write `keep/replace/drop/add` - tokens this applier accepts NOWHERE. A vocabulary that
# exists only inside its reader is a vocabulary the writer guesses at, and the guess costs real work: `--apply`
# fails closed on an unrecognised verdict, so the owner would have filled 150 cells and been refused. Fail
# closed rather than guess (C16).
DECISIONS: tuple = tuple(str(x) for x in (REANCHOR_CFG.get("decisions") or ()))
if len(DECISIONS) < 2:
    raise SystemExit("FAIL-CLOSED (C16): config/pipeline_config.yaml declares no "
                     "retrieval_benchmark.reanchor.decisions - the review vocabulary has ONE home and this "
                     "applier will not guess it (D-2987)")
# D-2939 declares anchors are OWNER-SIGNED and no model may sign one. MEASURED 2026-10-13: the CSV's
# `owner_signature` column was written here and read by NOTHING in the repository, so the declaration had no
# control behind it (BUG-492: a detector nobody has seen fail is not a detector).
OWNER_SIGNATURE_REQUIRED: bool = bool(REANCHOR_CFG.get("owner_signature_required", False))


def _old_row(conn, expected: str) -> dict:
    """Look up the retired golden id so the reviewer sees old vs new side by side."""
    if not expected:
        return {"fb_id": None, "name": None, "run": None, "status": None}
    r = conn.execute(
        "SELECT fb_id, name, pipeline_run_id, status FROM fbs WHERE fb_id LIKE ? LIMIT 1",
        (expected + "%",),
    ).fetchone()
    if r is None:
        return {"fb_id": expected, "name": None, "run": None, "status": None}
    return {"fb_id": r["fb_id"], "name": r["name"], "run": r["pipeline_run_id"], "status": r["status"]}


def _apply_reviewed(csv_path: Path, draft_path: Path, target: Path, conn,
                  serving_scope: str = "canonical_run") -> int:
    """R5/Q6 — the ONLY path from a reviewed draft to the live golden set.

    Refuses (exit 2, writing nothing) unless ALL of these hold:
      * every query in the draft has exactly ONE candidate row marked `decision: anchor`
        (the reviewer chooses the NAME they judge correct — rank-1 carries no authority);
      * every chosen NAME resolves in the serving scope (a name that does not resolve
        would silently drop the query from the denominator later);
      * a C13 backup of the live file is taken before the write.
    Queries marked `retire-query` or `rewrite-query` are dropped from the set on purpose
    and reported; a query with NO verdict fails the apply instead of being guessed.
    C16: every failure prints and returns non-zero.
    """
    if not csv_path.exists() or not draft_path.exists():
        print(f"  ❌ apply needs both the reviewed CSV and the draft ({csv_path.name}, {draft_path.name})")
        return 2
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    draft = yaml.safe_load(draft_path.read_text(encoding="utf-8")) or {}
    queries = draft.get("queries", [])
    if not queries:
        print("  ❌ draft contains no queries (C16)")
        return 2

    live = {str(q.get("query", "")) for q in
            ((yaml.safe_load(target.read_text(encoding="utf-8")) or {}).get("queries") or [])} \
        if target.exists() else set()
    final: list[dict] = []
    retired: list[str] = []
    unreviewed: list[str] = []
    added: list[str] = []
    for q in queries:
        qrows = [r for r in rows if r.get("query") == q.get("query")]
        verdicts = {(r.get("decision") or "").strip().lower() for r in qrows}
        chosen = [r for r in qrows if (r.get("decision") or "").strip().lower() == "anchor"]
        if not chosen:
            if verdicts & {"retire-query", "rewrite-query"}:
                retired.append(q.get("query", ""))
            else:
                unreviewed.append(q.get("query", ""))
            continue
        if len(chosen) > 1:
            print(f"  ❌ {q.get('query', '')[:44]!r}: {len(chosen)} rows marked `anchor` — "
                  f"exactly one is required (C16)")
            return 2
        if OWNER_SIGNATURE_REQUIRED and not (chosen[0].get("owner_signature") or "").strip():
            print(f"  ❌ {q.get('query', '')[:44]!r}: the chosen anchor "
                  f"{str(chosen[0].get('cand_name'))[:40]!r} carries NO owner_signature - D-2939 anchors are "
                  f"owner-SIGNED and no model may sign one; refusing to write (C16)")
            return 2
        if str(q.get("query", "")) not in live:
            added.append(str(q.get("query", "")))
        name = chosen[0]["cand_name"]
        fid, why, _n = resolve_name(conn, name, serving_scope)
        if not fid:
            print(f"  ❌ chosen anchor does not resolve: {name!r} ({why}) — refusing to write (C16)")
            return 2
        final.append({
            "query": q.get("query", ""), "expected_names": [name], "expected": [fid],
            "query_type": q.get("query_type", "?"), "verified_run": CANONICAL_RUN,
        })

    if unreviewed:
        print(f"  ❌ {len(unreviewed)} query(ies) have NO verdict in the reviewed CSV — "
              f"refusing to apply (a guess is not a label):")
        for u in unreviewed[:8]:
            print(f"       ? {u[:70]}")
        return 2
    if not final:
        print("  ❌ nothing to apply — every query was retired/rewritten (C16)")
        return 2

    backup = target.with_suffix(target.suffix + f".bak_{STAMP}")
    if target.exists():
        shutil.copy2(target, backup)
        print(f"  C13 backup: {backup.name}")
    header = (
        f"# Golden retrieval query set — re-anchored by scripts/reanchor_retrieval_goldens.py --apply\n"
        f"# {STAMP}  served run: {CANONICAL_RUN}\n"
        f"# D-2939: anchors are NAMES (owner-approved); IDs are resolved per run by pipeline/golden.py\n"
        f"# and are recorded here as the verified snapshot. Retired/rewritten this pass: "
        f"{len(retired)}\n"
    )
    target.write_text(header + yaml.safe_dump({"version": 4, "queries": final}, sort_keys=False),
                      encoding="utf-8")
    print(f"  ✅ applied {len(final)} reviewed anchor(s) -> {target}")
    print(f"     retired/rewritten (dropped): {len(retired)}")
    if added:
        print(f"     ADDED (were absent from the live set): {len(added)}")
        for a in added[:8]:
            print(f"       + {a[:70]}")
    for r in retired[:8]:
        print(f"       - {r[:70]}")
    print("     next: python3 pipeline/retrieval_benchmark.py   (the semantic baseline is now measurable)")
    return 0


def _check_reviewed(csv_path: Path, draft_path: Path) -> int:
    """D-2987: the PRE-FLIGHT for a reviewed CSV - what `--apply` would refuse, reported BEFORE the write.

    MEASURED 2026-10-13: the vocabulary lived only in this file's DECISIONS literal and two consecutive
    handoffs handed the owner `keep/replace/drop/add`, tokens no reader accepts. `--apply` fails closed on an
    unrecognised verdict, so that work would have been refused at the END of a 150-row sitting. This mode runs
    the same judgement FIRST, and it NAMES the offending token and the allowed set (C16: no silent failures).

    Reads the reviewed CSV and the draft it belongs to. Writes NOTHING.
    """
    if not csv_path.exists():
        print(f"  ❌ no reviewed CSV at {csv_path} (C16)")
        return 1
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("  ❌ the reviewed CSV has no rows (C16)")
        return 1
    if not draft_path.exists():
        print(f"  ❌ no candidate draft at {draft_path} - run the generator first to rebuild the sheet (C16)")
        return 1
    draft = yaml.safe_load(draft_path.read_text(encoding="utf-8")) or {}
    qs = [str(q.get("query", "")) for q in (draft.get("queries") or [])]
    # D-2987: the draft and the LIVE set were measured OUT OF PHASE by one query on 2026-10-13 (the draft
    # carries "can a large language model be compressed into a smaller one", which the 20261011T221956Z apply
    # RETIRED). `--apply` rebuilds the set from the draft, so anchoring that row would silently RE-ADD a query
    # that was retired ON PURPOSE. ADDING is legitimate and is half of what T-101 asks for - but it must be a
    # DECLARED act, never a side effect, so it is reported here rather than performed quietly.
    live = {str(q.get("query", "")) for q in
            ((yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8")) or {}).get("queries") or [])}
    adds = [q for q in qs if q not in live]
    allowed = set(DECISIONS)
    faults: list[str] = []
    by_query: dict[str, list[dict]] = {}
    for n, r in enumerate(rows, start=2):
        by_query.setdefault(str(r.get("query", "")), []).append(r)
        tok = (r.get("decision") or "").strip().lower()
        if tok and tok not in allowed:
            faults.append(f"row {n}: decision {tok!r} is NOT one of {sorted(allowed)} - this token is read by "
                          f"nothing and `--apply` would refuse the whole sheet")
    for q in qs:
        qrows = by_query.get(q, [])
        if not qrows:
            faults.append(f"query {q[:50]!r}: the draft has this query but the CSV carries no row for it")
            continue
        chosen = [r for r in qrows if (r.get("decision") or "").strip().lower() == "anchor"]
        dropped = bool({(r.get("decision") or "").strip().lower() for r in qrows} & {"retire-query",
                                                                                    "rewrite-query"})
        if not chosen and not dropped:
            faults.append(f"query {q[:50]!r}: NO row marked 'anchor' and no retire/rewrite verdict - "
                          f"{len(qrows)} candidate row(s) to choose from")
        if len(chosen) > 1:
            faults.append(f"query {q[:50]!r}: {len(chosen)} rows marked 'anchor' - exactly ONE is required")
        if OWNER_SIGNATURE_REQUIRED:
            for r in chosen:
                if not (r.get("owner_signature") or "").strip():
                    faults.append(f"query {q[:50]!r}: the chosen anchor "
                                  f"{str(r.get('cand_name'))[:40]!r} carries no owner_signature")
    reviewed = len(qs) - len({q for q in qs if not [
        r for r in by_query.get(q, []) if (r.get("decision") or "").strip().lower() == "anchor"]})
    print("\n═══ REVIEWED-CSV PRE-FLIGHT (D-2987) - nothing is written ═══")
    print(f"  rows {len(rows)} · queries {len(qs)} · vocabulary: {', '.join(DECISIONS)}")
    print(f"  queries with exactly one anchor: {reviewed} / {len(qs)}")
    if adds:
        print(f"  ⚠️  {len(adds)} draft query(ies) are NOT in the live set - anchoring one would ADD it "
              f"(the live set holds {len(live)}):")
        for a in adds[:8]:
            print(f"       + {a[:70]}")
    if faults:
        print(f"  ❌ {len(faults)} fault(s) - `--apply` would REFUSE the sheet:")
        for f in faults[:20]:
            print(f"       ✗ {f}")
        if len(faults) > 20:
            print(f"       ... {len(faults) - 20} more")
        return 1
    print("  ✅ every query carries exactly ONE verdict")
    if OWNER_SIGNATURE_REQUIRED:
        print("  ✅ every chosen anchor carries an owner_signature")
    print("     next: python3 scripts/reanchor_retrieval_goldens.py --apply")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-anchor stale retrieval goldens to the served run (BUG-710)")
    ap.add_argument("--top", type=int, default=DEFAULT_TOP, help="candidate rows per query")
    ap.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    ap.add_argument("--csv", type=Path, default=CSV_OUT)
    ap.add_argument("--yaml-out", type=Path, default=YAML_OUT)
    ap.add_argument("--method", default=RETRIEVAL_METHOD,
                    choices=["vector", "rrf"], help="candidate leg (config retrieval.method)")
    ap.add_argument("--no-rerank", action="store_true",
                    help="disable the cross-encoder (A/B only; the D-2724 production leg reranks)")
    ap.add_argument("--apply", action="store_true",
                    help="R5/Q6 gate: apply the REVIEWED CSV to config/golden/retrieval_queries.yaml "
                         "(refuses unless every query has exactly one `anchor` row that resolves)")
    ap.add_argument("--check", action="store_true",
                    help="D-2987 pre-flight: report what --apply would refuse, WITHOUT writing and WITHOUT "
                         "touching the store. Run this the moment you have filled the CSV")
    args = ap.parse_args()

    if args.check:
        return _check_reviewed(args.csv, args.yaml_out)

    leg: str = args.method
    should_rerank: bool = (not args.no_rerank) and RERANK_ENABLED
    leg_label: str = f"{leg}{'+rerank' if should_rerank else ''}"
    if (leg, should_rerank) != (RETRIEVAL_METHOD, RERANK_ENABLED):
        print(f"  ⚠️  NON-PRODUCTION LEG ({leg_label}); production is "
              f"{RETRIEVAL_METHOD}{'+rerank' if RERANK_ENABLED else ''} — recorded in the artifact header")

    conn = get_conn()
    queries = load_golden(args.golden)
    if not queries:
        print("  ❌ golden query set is empty")
        return 1

    if args.apply:
        # D-2941 / R5: apply reads the already-REVIEWED CSV + draft. Regenerating
        # candidates here would overwrite the CSV and blank the human's `decision`
        # column, so the gate could never pass. Early-return instead.
        return _apply_reviewed(args.csv, args.yaml_out, args.golden, conn)

    rows: list[dict] = []
    no_candidate: list[str] = []
    proposed: list[dict] = []
    for q in queries:
        old = _old_row(conn, (q.get("expected") or [""])[0])
        candidates = search(conn, q["query"], limit=args.top, method=leg, rerank=should_rerank)
        if not candidates:
            no_candidate.append(q["query"])
            continue
        scores = [c.get("_rerank_score") for c in candidates]
        for rank, c in enumerate(candidates, 1):
            rows.append({
                "query": q["query"], "query_type": q.get("query_type", "?"),
                "old_fb_id": (old["fb_id"] or "")[:16], "old_run": old["run"],
                "old_status": old["status"], "old_name": old["name"],
                "rank": rank, "cand_name": c["name"],
                "cand_definition": (c.get("definition") or "")[:SNIPPET_CHARS].replace("\n", " "),
                "cand_discipline": c.get("discipline"), "cand_domains": c.get("domains"),
                "cand_source_diversity": c.get("source_diversity"), "cand_status": c.get("status"),
                "cand_fb_id_resolved": c["fb_id"],
                "leg": leg_label, "leg_score": scores[rank - 1],
                "leg_margin_to_next": (
                    round(scores[rank - 1] - scores[rank], 3)
                    if rank < len(scores) and scores[rank] is not None and scores[rank - 1] is not None
                    else None
                ),
                "decision": "", "owner_signature": "",
            })
        # BUG-717: rank-1 is EVIDENCE. The anchor is the NAME (D-2939), so the id can
        # change every run without re-signing the label.
        proposed.append({
            "query": q["query"],
            "expected_names": [candidates[0]["name"]],
            "expected": [],
            "query_type": q.get("query_type", "?"),
            "_needs_review": True,
            "_old_name": old["name"],
            "_replaces": (old["fb_id"] or "")[:16],
            "_evidence": {"leg": leg_label, "rank1_score": candidates[0].get("_rerank_score"),
                          "margin_to_2": (round(scores[0] - scores[1], 3)
                                          if len(scores) > 1 and None not in scores[:2] else None)},
        })

    if not rows:
        raise RuntimeError("no candidates produced — the candidate leg returned nothing for every "
                           "golden query (C16). Check serving.index_scope and the served run.")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    header = (
        f"# PROPOSED re-anchor of config/golden/retrieval_queries.yaml — NOT APPLIED.\n"
        f"# generated {datetime.now(timezone.utc).isoformat()} by scripts/reanchor_retrieval_goldens.py\n"
        f"# candidate leg: {leg_label}   (production = {RETRIEVAL_METHOD}"
        f"{'+rerank' if RERANK_ENABLED else ''})   served run: {CANONICAL_RUN}\n"
        f"# BUG-717: rank-1 is EVIDENCE, never a proposal. Scores are NOT thresholds\n"
        f"# (logits are uncalibrated: measured range -6.0..+8.6 on known-positive pairs).\n"
        f"# D-2939: the anchor is the NAME; pipeline/golden.py resolves the fb_id per run.\n"
        f"# D-2898: a human marks `decision` = {' | '.join(DECISIONS)} in the CSV.\n"
    )
    args.yaml_out.write_text(
        header + yaml.safe_dump({"version": 3, "queries": proposed}, sort_keys=False), encoding="utf-8"
    )

    print("\n═══ GOLDEN RE-ANCHOR (BUG-710/BUG-717) — dry-run ═══")
    print(f"candidate leg       : {leg_label}   served run: {CANONICAL_RUN}")
    print(f"golden queries      : {len(queries)}")
    print(f"candidate rows      : {len(rows)} -> {args.csv}")
    print(f"proposed YAML       : {args.yaml_out}  (review, then copy over config/golden/)")
    print(f"queries with NO candidate: {len(no_candidate)}")
    for q in no_candidate:
        print(f"   ✗ {q[:70]}")
    print("\n  first 6 candidate rows (reviewer view — judge the NAME, not the id):")
    for r in rows[:6]:
        sc = f"{r['leg_score']:.3f}" if isinstance(r["leg_score"], (int, float)) else "n/a"
        print(f"   [{r['query_type']:<18}] r{r['rank']} {sc:>8} {str(r['cand_name'])[:44]:<46} <- {r['query'][:40]}")
    print("\n  decision vocabulary:", ", ".join(DECISIONS))
    if args.apply:
        print("\n  decision vocabulary:", ", ".join(DECISIONS))
        return _apply_reviewed(args.csv, args.yaml_out, args.golden, conn)
    print("\n  decision vocabulary:", ", ".join(DECISIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
