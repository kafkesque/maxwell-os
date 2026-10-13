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
import difflib
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_paths import CANONICAL_RUN, RERANK_ENABLED, RETRIEVAL_METHOD  # noqa: E402

# D-2991: the STORE-touching imports are LAZY (imported inside the functions that need them). `--selftest` is the
# control the ladder runs, and a control that cannot run without loading the FAISS index and the cross-encoder is a
# control that quietly gets skipped (BUG-492). The JUDGMENT (judge_review) is pure and store-free; only --apply and
# the generator need the store.

STAMP: str = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
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
    raise SystemExit(
        "FAIL-CLOSED (C16): config/pipeline_config.yaml declares no "
        "retrieval_benchmark.reanchor.decisions - the review vocabulary has ONE home and this "
        "applier will not guess it (D-2987)"
    )
# D-2939 declares anchors are OWNER-SIGNED and no model may sign one. MEASURED 2026-10-13: the CSV's
# `owner_signature` column was written here and read by NOTHING in the repository, so the declaration had no
# control behind it (BUG-492: a detector nobody has seen fail is not a detector).
OWNER_SIGNATURE_REQUIRED: bool = bool(REANCHOR_CFG.get("owner_signature_required", False))

# D-2991 (the ANCHOR-SET decision). A query's expected answer is EITHER one owner-signed row (mode `single`) OR every
# row the owner marked (mode `set`). MEASURED 2026-10-13: the owner's 150-cell review marked 3-5 candidates per
# query - it answered "which of these are CORRECT ANSWERS", a coverage question the harness ALREADY measures
# (recall@k is micro over `expected`; `expected_names` is a list). The v2 applier refused that sheet because the
# `single` reading was hardcoded in TWO places. The mode is now DECLARED and never INFERRED from the sheet: an
# inferred mode is a ruler whose meaning depends on the data it measured (and T-101 exists because the ruler was
# saturated - one accepted answer per query is the easiest ruler the format can express).
ANCHOR_MODE: str = str(REANCHOR_CFG.get("anchor_mode", "single")).strip()
ANCHOR_MODES: tuple = ("single", "set")
if ANCHOR_MODE not in ANCHOR_MODES:
    raise SystemExit(
        f"FAIL-CLOSED (C16): config/pipeline_config.yaml declares retrieval_benchmark.reanchor."
        f"anchor_mode = {ANCHOR_MODE!r}, which this applier does not implement (known modes: "
        f"{ANCHOR_MODES}) - it will not guess the semantics of a golden set."
    )


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
    return {
        "fb_id": r["fb_id"],
        "name": r["name"],
        "run": r["pipeline_run_id"],
        "status": r["status"],
    }


def _tok(row: dict) -> str:
    """The row's verdict token, normalised. Blank is NOT a verdict (see judge_review)."""
    return str(row.get("decision") or "").strip().lower()


def _rank(row: dict) -> int:
    """The candidate's rank as an int; a rank that cannot be read sorts LAST.

    The order of an expected SET is the reviewer's evidence of preference, so a malformed rank must never sort
    first: this function will not invent a preference it did not read (C16 - it sorts last and stays visible).
    """
    try:
        return int(str(row.get("rank") or "").strip())
    except (TypeError, ValueError):
        return 10**6


def judge_review(
    rows: list[dict],
    queries: list[str],
    mode: str | None = None,
    signature_required: bool | None = None,
    live: list | None = None,
) -> dict:
    """THE ONE judgment of a reviewed sheet (D-2991) - pure, store-free, shared by --check and --apply.

    WHY IT IS ONE FUNCTION. Until 2026-10-13 --check and --apply each carried their OWN copy of the verdict logic,
    so the pre-flight could PASS a sheet the writer then refused: two implementations of one rule drift, and the
    drift is invisible in exactly the direction that hurts (the D-2642 class, in a control instead of a value).

    Args:
        rows: the reviewed CSV rows (as read by csv.DictReader).
        queries: the draft's query strings, IN DRAFT ORDER (the draft is the sheet's denominator).
        mode: 'single' (exactly one anchor row per query) | 'set' (the anchor rows ARE the expected set, ordered by
            rank). Defaults to the DECLARED ANCHOR_MODE - the mode is never inferred from the sheet (INV-3).
        signature_required: D-2939 - an anchor with no owner_signature is refused. Defaults to config.
        live: query strings already in the live golden set (so an ADD is reported, never a side effect).

    Returns:
        {"mode", "faults": [str], "plans": [{query, names, verdict, abstained, signatures, in_live}],
         "dropped": [str], "unreviewed": [str], "added": [str], "abstentions": int,
         "unknown_tokens": [str], "near_miss": {token: suggestion}}
    """
    mode = mode or ANCHOR_MODE
    sig_req: bool = (
        OWNER_SIGNATURE_REQUIRED if signature_required is None else bool(signature_required)
    )
    live_set: set = {str(x) for x in (live or ())}
    allowed: set = set(DECISIONS)
    by_query: dict[str, list[dict]] = {}
    faults: list[str] = []
    unknown: list[str] = []
    near_miss: dict[str, str] = {}
    # Row numbers start at 2: the header is row 1 and the number is what a reviewer sees in a spreadsheet, because
    # the reader of a fault is a human and "row 104" must mean the same thing to both of us.
    for n, r in enumerate(rows, start=2):
        by_query.setdefault(str(r.get("query", "")), []).append(r)
        tok = _tok(r)
        if tok and tok not in allowed:
            unknown.append(tok)
            close = difflib.get_close_matches(tok, sorted(allowed), n=1, cutoff=0.7)
            if close:
                near_miss[tok] = close[0]
            faults.append(
                f"row {n}: decision {tok!r} is NOT one of {sorted(allowed)} - this token is read by "
                f"nothing and --apply would refuse the whole sheet"
                + (f" (did you mean {close[0]!r}?)" if close else "")
            )
    plans: list[dict] = []
    dropped: list[str] = []
    unreviewed: list[str] = []
    added: list[str] = []
    abstentions = 0
    for q in queries:
        qs = str(q)
        qrows = by_query.get(qs, [])
        if not qrows:
            faults.append(
                f"query {qs[:50]!r}: the draft has this query but the CSV carries no row for it"
            )
            continue
        anchors = sorted([r for r in qrows if _tok(r) == "anchor"], key=_rank)
        abstained = [r for r in qrows if _tok(r) == "ambiguous"]
        abstentions += len(abstained)
        verbs = {_tok(r) for r in qrows}
        plan: dict = {
            "query": qs,
            "names": [str(r.get("cand_name", "")) for r in anchors],
            "abstained": len(abstained),
            "signatures": [str(r.get("owner_signature") or "").strip() for r in anchors],
            "in_live": qs in live_set,
        }
        if not anchors:
            plan["verdict"] = (
                "dropped" if (verbs & {"retire-query", "rewrite-query"}) else "unreviewed"
            )
            if plan["verdict"] == "dropped":
                dropped.append(qs)
            else:
                unreviewed.append(qs)
                faults.append(
                    f"query {qs[:50]!r}: NO row marked 'anchor' and no retire/rewrite verdict - "
                    f"{len(qrows)} candidate row(s) to choose from (a guess is not a label)"
                )
            plans.append(plan)
            continue
        if mode == "single" and len(anchors) > 1:
            faults.append(
                f"query {qs[:50]!r}: {len(anchors)} rows marked 'anchor' - anchor_mode 'single' "
                f"requires exactly ONE (declare reanchor.anchor_mode: set in config/pipeline_config.yaml "
                f"to treat the marked rows as the query's expected SET)"
            )
        if sig_req and any(not s for s in plan["signatures"]):
            faults.append(
                f"query {qs[:50]!r}: a chosen anchor carries no owner_signature - D-2939 anchors are "
                f"owner-SIGNED and no model may sign one (C16)"
            )
        if not plan["in_live"]:
            added.append(qs)
        plan["verdict"] = "anchor-set" if mode == "set" else "anchor"
        plans.append(plan)
    return {
        "mode": mode,
        "faults": faults,
        "plans": plans,
        "dropped": dropped,
        "unreviewed": unreviewed,
        "added": added,
        "abstentions": abstentions,
        "unknown_tokens": sorted(set(unknown)),
        "near_miss": near_miss,
    }


def _print_review(rep: dict, rows_n: int, queries_n: int, where: str) -> None:
    """Print the ONE judgment in the reviewer's terms - shared by --check and --apply (INV-6)."""
    print(f"\n═══ REVIEWED-CSV {where} - nothing is written (D-2987/D-2991) ═══")
    print(
        f"  rows {rows_n} · queries {queries_n} · anchor_mode: {rep['mode']}"
        f" · vocabulary: {', '.join(DECISIONS)}"
    )
    sets = [p for p in rep["plans"] if p["verdict"] in ("anchor", "anchor-set")]
    print(
        f"  quer(ies) with an expected set: {len(sets)} / {queries_n}"
        f" · anchor name(s): {sum(len(p['names']) for p in sets)}"
        f" · owner abstention(s) excluded: {rep['abstentions']}"
        f" · dropped on purpose: {len(rep['dropped'])}"
    )
    for tok, sug in sorted(rep["near_miss"].items()):
        print(
            f"  ~ {tok!r} is not a verdict: did you mean {sug!r}? (the applier will not guess - fix the cell)"
        )
    if rep["added"]:
        print(
            f"  ⚠️  {len(rep['added'])} draft query(ies) are NOT in the live set - anchoring one would ADD it:"
        )
        for a in rep["added"][:8]:
            print(f"       + {a[:70]}")
    for d in rep["dropped"][:8]:
        print(f"       - dropped: {d[:70]}")
    if rep["faults"]:
        print(f"  ❌ {len(rep['faults'])} fault(s) - --apply would REFUSE the sheet:")
        for f in rep["faults"][:20]:
            print(f"       ✗ {f}")
        if len(rep["faults"]) > 20:
            print(f"       ... {len(rep['faults']) - 20} more")
        return
    print("  ✅ every query carries a verdict: one owner-signed anchor, or a declared expected SET")
    if OWNER_SIGNATURE_REQUIRED:
        print("  ✅ every chosen anchor carries an owner_signature (D-2939)")


def _apply_reviewed(
    csv_path: Path, draft_path: Path, target: Path, conn, serving_scope: str = "canonical_run"
) -> int:
    """R5/Q6 — the ONLY path from a reviewed sheet to the live golden set.

    Refuses (exit 2, writing nothing) unless ALL of these hold:
      * the sheet PASSES judge_review — the same judgment --check reports (INV-6), so the pre-flight can never
        disagree with the writer;
      * every chosen NAME resolves in the serving scope (a name that does not resolve would silently drop the
        query from the denominator later, BUG-710);
      * a C13 backup of the live file is taken before the write.
    Queries marked `retire-query` or `rewrite-query` are dropped from the set on purpose and reported; a query with
    NO verdict fails the apply instead of being guessed; a row marked `ambiguous` is an ABSTENTION — excluded from
    the expected set and counted (INV-5).
    Anchor multiplicity is DECLARED (`reanchor.anchor_mode`): `single` = exactly one anchor row per query, `set` =
    the marked rows ARE the expected set, ordered by rank (D-2991). C16: every failure prints and returns non-zero.
    """
    if not csv_path.exists() or not draft_path.exists():
        print(
            f"  ❌ apply needs both the reviewed CSV and the draft ({csv_path.name}, {draft_path.name})"
        )
        return 2
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    draft = yaml.safe_load(draft_path.read_text(encoding="utf-8")) or {}
    queries = [str(q.get("query", "")) for q in (draft.get("queries") or [])]
    qtypes = {
        str(q.get("query", "")): q.get("query_type", "?") for q in (draft.get("queries") or [])
    }
    if not queries:
        print("  ❌ draft contains no queries (C16)")
        return 2

    live = (
        {
            str(q.get("query", ""))
            for q in (
                (yaml.safe_load(target.read_text(encoding="utf-8")) or {}).get("queries") or []
            )
        }
        if target.exists()
        else set()
    )
    rep = judge_review(rows, queries, live=sorted(live))
    _print_review(rep, len(rows), len(queries), "PRE-FLIGHT (--apply)")
    if rep["faults"]:
        print("  ❌ refusing to write: the judgment above is the SAME one --check reports (INV-6)")
        return 2

    from pipeline.golden import resolve_name  # D-2991: store imports are LAZY

    final: list[dict] = []
    for plan in rep["plans"]:
        if plan["verdict"] not in ("anchor", "anchor-set"):
            continue
        names: list[str] = list(plan["names"]) if rep["mode"] == "set" else list(plan["names"])[:1]
        ids: list[str] = []
        for name in names:
            fid, why, _n = resolve_name(conn, name, serving_scope)
            if not fid:
                print(
                    f"  ❌ chosen anchor does not resolve: {name!r} ({why}) — refusing to write (C16)"
                )
                return 2
            ids.append(fid)
        final.append(
            {
                "query": plan["query"],
                "expected_names": names,
                "expected": ids,
                "query_type": qtypes.get(plan["query"], "?"),
                "verified_run": CANONICAL_RUN,
            }
        )
    if not final:
        print("  ❌ nothing to apply — every query was retired/rewritten (C16)")
        return 2

    backup = target.with_suffix(target.suffix + f".bak_{STAMP}")
    if target.exists():
        shutil.copy2(target, backup)
        print(f"  C13 backup: {backup.name}")
    n_names = sum(len(q["expected_names"]) for q in final)
    header = (
        f"# Golden retrieval query set — re-anchored by scripts/reanchor_retrieval_goldens.py --apply\n"
        f"# {STAMP}  served run: {CANONICAL_RUN}  anchor_mode: {rep['mode']}\n"
        f"# D-2939: anchors are NAMES (owner-signed); IDs are resolved per run by pipeline/golden.py and are\n"
        f"# recorded here as the verified snapshot.\n"
        f"# D-2991: a query's expected answer is the SET of rows the owner marked (version 5). recall@k is MICRO\n"
        f"# over `expected` (pipeline/retrieval_benchmark.py::_recall_at_k), so a larger set is a STRICTER ruler,\n"
        f"# never an easier one — that is the ONLY reason a set is allowed (T-101).\n"
        f"# {len(final)} quer(ies) x {n_names} anchor name(s) · owner abstentions EXCLUDED: {rep['abstentions']}"
        f" · dropped on purpose: {len(rep['dropped'])}\n"
    )
    target.write_text(
        header + yaml.safe_dump({"version": 5, "queries": final}, sort_keys=False), encoding="utf-8"
    )
    print(
        f"  ✅ applied {len(final)} quer(ies) / {n_names} owner-signed anchor name(s) -> {target}"
    )
    print(f"     owner abstentions excluded from the sets: {rep['abstentions']}")
    print(f"     dropped on purpose (retire/rewrite): {len(rep['dropped'])}")
    if rep["added"]:
        print(f"     ADDED (were absent from the live set): {len(rep['added'])}")
        for a in rep["added"][:8]:
            print(f"       + {a[:70]}")
    for r in rep["dropped"][:8]:
        print(f"       - {r[:70]}")
    print(
        "     next: python3 pipeline/retrieval_benchmark.py   (the semantic baseline is now measurable)"
    )
    return 0


def _check_reviewed(csv_path: Path, draft_path: Path) -> int:
    """D-2987/D-2991 pre-flight: the SAME judgment `--apply` will make, reported BEFORE the write.

    MEASURED 2026-10-13: the vocabulary lived only in this file's DECISIONS literal and two consecutive handoffs
    handed the owner `keep/replace/drop/add`, tokens no reader accepts; `--apply` fails closed on an unrecognised
    verdict, so that work would have been refused at the END of a 150-row sitting. It was then refused for a SECOND
    reason nobody had declared: the owner marked an expected SET and the applier hardcoded a single anchor. This
    mode runs the judgment FIRST, writes NOTHING, touches NO store, and NAMES the offending token (with a near-miss
    suggestion it refuses to apply) — C16: no silent failures.
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
        print(
            f"  ❌ no candidate draft at {draft_path} - run the generator first to rebuild the sheet (C16)"
        )
        return 1
    draft = yaml.safe_load(draft_path.read_text(encoding="utf-8")) or {}
    queries = [str(q.get("query", "")) for q in (draft.get("queries") or [])]
    if not queries:
        print("  ❌ the draft carries no queries (C16)")
        return 1
    # D-2987: the draft and the LIVE set were measured OUT OF PHASE by one query on 2026-10-13 (the draft carries
    # "can a large language model be compressed into a smaller one", which the 20261011T221956Z apply RETIRED).
    # `--apply` rebuilds the set from the draft, so anchoring that row would silently RE-ADD a query retired on
    # purpose. ADDING is legitimate and is half of what T-101 asks for — but it must be a DECLARED act, never a
    # side effect, so judge_review reports it (INV-7) instead of performing it quietly.
    live = {
        str(q.get("query", ""))
        for q in (
            (yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8")) or {}).get("queries") or []
        )
    }
    rep = judge_review(rows, queries, live=sorted(live))
    _print_review(rep, len(rows), len(queries), "PRE-FLIGHT (--check)")
    if rep["faults"]:
        return 1
    print("     next: python3 scripts/reanchor_retrieval_goldens.py --apply")
    return 0


def _sheet(
    decisions: list[str], sig: str = "B.", query: str = "q1", names: list[str] | None = None
) -> list[dict]:
    """Build minimal reviewed-CSV rows for the controls (rank = index + 1): no store, no CSV, no randomness."""
    nm = list(names) if names else [f"name{i + 1}" for i in range(len(decisions))]
    return [
        {
            "query": query,
            "rank": str(i + 1),
            "cand_name": nm[i],
            "decision": d,
            "owner_signature": sig,
        }
        for i, d in enumerate(decisions)
    ]


def controls() -> list[tuple[str, bool]]:
    """The known-answer controls, one per named guard (a guardrail never seen failing is not a guardrail).

    Pure: every control drives judge_review on a tiny fixture, so the ladder can run them without a store, a CSV or
    a model (BUG-492: a control that needs the FAISS index never runs).
    """
    one = judge_review(_sheet(["anchor", "", ""]), ["q1"], mode="single", signature_required=True)
    two_single = judge_review(
        _sheet(["anchor", "anchor", ""]), ["q1"], mode="single", signature_required=True
    )
    two_set = judge_review(
        _sheet(["anchor", "anchor", ""]), ["q1"], mode="set", signature_required=True
    )
    typo = judge_review(
        _sheet(["anchor", "ambigouos"]), ["q1"], mode="set", signature_required=True
    )
    unsigned = judge_review(
        _sheet(["anchor", ""], sig=""), ["q1"], mode="single", signature_required=True
    )
    noverdict = judge_review(_sheet(["", "", ""]), ["q1"], mode="single", signature_required=True)
    rewritten = judge_review(
        _sheet(["rewrite-query", "", ""]), ["q1"], mode="single", signature_required=True
    )
    abstained = judge_review(
        _sheet(["anchor", "ambiguous", "anchor"]), ["q1"], mode="set", signature_required=True
    )
    added = judge_review(
        _sheet(["anchor", "", ""]),
        ["q1"],
        mode="single",
        signature_required=True,
        live=["some other query"],
    )
    missing = judge_review(
        _sheet(["anchor", "", ""]), ["q1", "q2"], mode="single", signature_required=True
    )
    return [
        (
            "a_single_anchor_in_single_mode_is_accepted",
            not one["faults"] and one["plans"][0]["verdict"] == "anchor",
        ),
        (
            "two_anchors_in_single_mode_are_refused",
            any("requires exactly ONE" in f for f in two_single["faults"]),
        ),
        (
            "two_anchors_in_set_mode_become_the_expected_set_in_rank_order",
            not two_set["faults"]
            and two_set["plans"][0]["names"] == ["name1", "name2"]
            and two_set["plans"][0]["verdict"] == "anchor-set",
        ),
        (
            "a_token_outside_the_vocabulary_is_refused_and_suggested_but_NEVER_applied",
            any("ambigouos" in f for f in typo["faults"])
            and typo["near_miss"].get("ambigouos") == "ambiguous"
            and not any(_tok(r) == "ambiguous" for r in _sheet(["anchor", "ambigouos"])),
        ),
        (
            "an_anchor_with_no_owner_signature_is_refused",
            any("owner_signature" in f for f in unsigned["faults"]),
        ),
        (
            "a_query_with_no_anchor_and_no_verdict_is_unreviewed_and_refuses_the_write",
            noverdict["unreviewed"] == ["q1"] and bool(noverdict["faults"]),
        ),
        (
            "a_rewrite_query_row_drops_the_query_instead_of_reviewing_it",
            rewritten["dropped"] == ["q1"] and not rewritten["faults"],
        ),
        (
            "an_abstention_is_excluded_from_the_set_and_counted",
            abstained["plans"][0]["names"] == ["name1", "name3"]
            and abstained["abstentions"] == 1
            and abstained["plans"][0]["abstained"] == 1,
        ),
        ("a_query_absent_from_the_live_set_is_declared_as_an_addition", added["added"] == ["q1"]),
        (
            "a_draft_query_with_no_csv_rows_is_a_fault",
            any("carries no row for it" in f for f in missing["faults"]),
        ),
        (
            "the_vocabulary_and_the_anchor_mode_have_ONE_home_in_config",
            len(DECISIONS) >= 2 and ANCHOR_MODE in ANCHOR_MODES,
        ),
    ]


def _selftest() -> int:
    """Run the known-answer controls. rc 0 = every control fires; 1 = at least one is DEAD (C16).

    The marker line for a control that did NOT fire is '  !!  <label>', which is what the mutation gate looks for
    (config/rail_mutations.yaml): a guard whose failure nobody has SEEN is a comment (BUG-492).
    """
    cs = controls()
    bad = 0
    for label, ok in cs:
        print(("  ok  " if ok else "  !!  ") + label)
        bad += 0 if ok else 1
    if bad:
        print(f"FAIL reanchor --selftest: {bad} of {len(cs)} known-answer control(s) did NOT fire")
    else:
        print(f"ok reanchor --selftest: {len(cs)}/{len(cs)} known-answer control(s) fire")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Re-anchor stale retrieval goldens to the served run (BUG-710)"
    )
    ap.add_argument("--top", type=int, default=DEFAULT_TOP, help="candidate rows per query")
    ap.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    ap.add_argument("--csv", type=Path, default=CSV_OUT)
    ap.add_argument("--yaml-out", type=Path, default=YAML_OUT)
    ap.add_argument(
        "--method",
        default=RETRIEVAL_METHOD,
        choices=["vector", "rrf"],
        help="candidate leg (config retrieval.method)",
    )
    ap.add_argument(
        "--no-rerank",
        action="store_true",
        help="disable the cross-encoder (A/B only; the D-2724 production leg reranks)",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="R5/Q6 gate: apply the REVIEWED CSV to config/golden/retrieval_queries.yaml "
        "(refuses unless every query carries a verdict that resolves, under the DECLARED "
        "anchor_mode: one anchor row, or the marked rows as an expected SET)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="D-2987 pre-flight: report what --apply would refuse, WITHOUT writing and WITHOUT "
        "touching the store. Run this the moment you have filled the CSV",
    )
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="D-2991: run the known-answer controls for the reviewed-sheet judgment (no store, no "
        "CSV, no model) - the ladder pins this, so a dead guard is SEEN (BUG-492)",
    )
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    if args.check:
        return _check_reviewed(args.csv, args.yaml_out)

    # D-2991: the store imports happen HERE, after the two store-free modes have returned, so --selftest and
    # --check stay hermetic (a rail that needs the FAISS index is a rail that gets skipped).
    from pipeline.golden import load_golden  # noqa: PLC0415
    from pipeline.retrieve import get_conn, search  # noqa: PLC0415

    leg: str = args.method
    should_rerank: bool = (not args.no_rerank) and RERANK_ENABLED
    leg_label: str = f"{leg}{'+rerank' if should_rerank else ''}"
    if (leg, should_rerank) != (RETRIEVAL_METHOD, RERANK_ENABLED):
        print(
            f"  ⚠️  NON-PRODUCTION LEG ({leg_label}); production is "
            f"{RETRIEVAL_METHOD}{'+rerank' if RERANK_ENABLED else ''} — recorded in the artifact header"
        )

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
            rows.append(
                {
                    "query": q["query"],
                    "query_type": q.get("query_type", "?"),
                    "old_fb_id": (old["fb_id"] or "")[:16],
                    "old_run": old["run"],
                    "old_status": old["status"],
                    "old_name": old["name"],
                    "rank": rank,
                    "cand_name": c["name"],
                    "cand_definition": (c.get("definition") or "")[:SNIPPET_CHARS].replace(
                        "\n", " "
                    ),
                    "cand_discipline": c.get("discipline"),
                    "cand_domains": c.get("domains"),
                    "cand_source_diversity": c.get("source_diversity"),
                    "cand_status": c.get("status"),
                    "cand_fb_id_resolved": c["fb_id"],
                    "leg": leg_label,
                    "leg_score": scores[rank - 1],
                    "leg_margin_to_next": (
                        round(scores[rank - 1] - scores[rank], 3)
                        if rank < len(scores)
                        and scores[rank] is not None
                        and scores[rank - 1] is not None
                        else None
                    ),
                    "decision": "",
                    "owner_signature": "",
                }
            )
        # BUG-717: rank-1 is EVIDENCE. The anchor is the NAME (D-2939), so the id can
        # change every run without re-signing the label.
        proposed.append(
            {
                "query": q["query"],
                "expected_names": [candidates[0]["name"]],
                "expected": [],
                "query_type": q.get("query_type", "?"),
                "_needs_review": True,
                "_old_name": old["name"],
                "_replaces": (old["fb_id"] or "")[:16],
                "_evidence": {
                    "leg": leg_label,
                    "rank1_score": candidates[0].get("_rerank_score"),
                    "margin_to_2": (
                        round(scores[0] - scores[1], 3)
                        if len(scores) > 1 and None not in scores[:2]
                        else None
                    ),
                },
            }
        )

    if not rows:
        raise RuntimeError(
            "no candidates produced — the candidate leg returned nothing for every "
            "golden query (C16). Check serving.index_scope and the served run."
        )

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    header = (
        f"# PROPOSED re-anchor of config/golden/retrieval_queries.yaml — NOT APPLIED.\n"
        f"# generated {datetime.now(UTC).isoformat()} by scripts/reanchor_retrieval_goldens.py\n"
        f"# candidate leg: {leg_label}   (production = {RETRIEVAL_METHOD}"
        f"{'+rerank' if RERANK_ENABLED else ''})   served run: {CANONICAL_RUN}\n"
        f"# BUG-717: rank-1 is EVIDENCE, never a proposal. Scores are NOT thresholds\n"
        f"# (logits are uncalibrated: measured range -6.0..+8.6 on known-positive pairs).\n"
        f"# D-2939: the anchor is the NAME; pipeline/golden.py resolves the fb_id per run.\n"
        f"# D-2898: a human marks `decision` = {' | '.join(DECISIONS)} in the CSV.\n"
    )
    args.yaml_out.write_text(
        header + yaml.safe_dump({"version": 3, "queries": proposed}, sort_keys=False),
        encoding="utf-8",
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
        print(
            f"   [{r['query_type']:<18}] r{r['rank']} {sc:>8} {str(r['cand_name'])[:44]:<46} <- {r['query'][:40]}"
        )
    print("\n  decision vocabulary:", ", ".join(DECISIONS))
    if args.apply:
        print("\n  decision vocabulary:", ", ".join(DECISIONS))
        return _apply_reviewed(args.csv, args.yaml_out, args.golden, conn)
    print("\n  decision vocabulary:", ", ".join(DECISIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
