#!/usr/bin/env python3
"""
pipeline/golden.py — golden-anchor resolver (D-2939, label vs pointer).
==========================================================================
WHY
---
config/golden/retrieval_queries.yaml pins `expected` fb_ids. An fb_id is a CONTENT
HASH of the verified input (D-2898), so every corpus reprocess mints new ids: a
hand-signed golden set rots in one pass. Measured 2026-10-11 (BUG-710): 0/30 golden
ids AND 0/30 golden NAMES were re-anchorable after rechunk-v4 — the harness then
reported recall@k = 0.000, which measured the GOLDEN SET, not retrieval.

THE SEPARATION (this module is the whole fix)
-------------------------------------------
  LABEL   = the query + the human-readable NAME of the correct answer.
            Owner-owned. Stable across a reprocess. The thing a human can judge.
  POINTER = the current fb_id of that NAME. MECHANICAL, run-scoped, recomputable.
            Not something an owner can or should sign.

D-2898 is unchanged: no agent mints a LABEL. This module mints POINTERS ONLY.

RAILS (C16 — fail loud; never let an unreturnable anchor print as recall 0)
--------------------------------------------------------------------------
  * name -> 0 rows in the serving scope  => UNRESOLVED (reported)
  * name -> >1 row, ruler mode `single`  => AMBIGUOUS  (refused, never guessed)
  * name -> >1 row, ruler mode `set`     => EVERY row is expected, multiplicity REPORTED
                                            (BUG-970: dropping the query would make a
                                            set-valued ruler LOOSER, against INV-4)
  * a query whose anchor cannot be resolved is EXCLUDED from the denominator and
    the exclusion is printed.
  * the stored `expected` snapshot is a LEGACY FALLBACK for a query that carries no
    `expected_names`; where names exist it is EVIDENCE of the last apply and never
    enters the denominator (BUG-969: a receipt is not an authority).

C12: serving scope + anchor mode come from config/serving. No LLM. No network.
No store writes. Deterministic.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_paths import CANONICAL_RUN, required, required_mapping  # noqa: E402

_CFG_PATH = PROJECT_ROOT / "config" / "pipeline_config.yaml"
_CFG_HOME = str(_CFG_PATH.relative_to(_CFG_PATH.parent.parent))  # D-2982: derived, never a second copy
with open(_CFG_PATH, encoding='utf-8') as _f:
    _CFG: dict = yaml.safe_load(_f) or {}
# D-2982 (C16/D-2644): the serving block is DECLARED. A missing block must be an ERROR - the old
# `_CFG.get("serving", {})` read an EMPTY anchoring contract instead, so golden.py would silently
# stop honouring every rule below it (fail-OPEN on a gate, the BUG-504 class).
_SERVING: dict = required_mapping(_CFG, "serving", where=_CFG_HOME)
# D-2939: `name_then_id` = prefer the owner-approved NAME, keep `expected` ids as a
# legacy fallback. `id` = legacy behaviour (ids only, BUG-710 rail applies).
ANCHOR_MODE: str = str(required(_SERVING, "golden_anchor_mode", where=_CFG_HOME))
REQUIRE_RESOLVABLE: bool = bool(required(_SERVING, "require_resolvable_goldens", where=_CFG_HOME))
# BUG-970: whether a label matching >1 row ENLARGES the expected set or REFUSES the query is a property
# of the RULER's declared semantics, not of this module's taste - so the resolver consults the ONE
# declaration the applier already obeys (retrieval_benchmark.reanchor.anchor_mode) instead of inventing
# a second knob (C12). Fail-closed: an absent block or an unknown token is an ERROR, never a default.
_REANCHOR: dict = required_mapping(
    required_mapping(_CFG, "retrieval_benchmark", where=_CFG_HOME), "reanchor", where=_CFG_HOME)
RULER_MODE: str = str(required(_REANCHOR, "anchor_mode", where=_CFG_HOME))
RULER_MODES: tuple[str, ...] = tuple(str(m).strip() for m in (required(_REANCHOR, "anchor_modes", where=_CFG_HOME) or ()))
if not RULER_MODES:
    raise SystemExit(
        f"FATAL: {_CFG_HOME}#retrieval_benchmark.reanchor.anchor_modes is EMPTY - the implemented token "
        f"list must be DECLARED, never guessed (BUG-971)"
    )
if RULER_MODE not in RULER_MODES:
    raise SystemExit(
        f"FATAL: {_CFG_HOME}#retrieval_benchmark.reanchor.anchor_mode is {RULER_MODE!r} - declared "
        f"modes are {list(RULER_MODES)} (an unknown mode is a ruler whose meaning nobody declared)"
    )
GOLDEN_PATH: Path = PROJECT_ROOT / "config" / "golden" / "retrieval_queries.yaml"


def load_golden(path: Path) -> list[dict]:
    """Load the golden query list from YAML."""
    with open(path, encoding='utf-8') as f:
        return (yaml.safe_load(f) or {}).get("queries", [])


def resolve_name(conn, name: str, serving_scope: str = "canonical_run",
                 canonical_run: str | None = None) -> tuple[str | None, str, int]:
    """Resolve an owner-approved answer NAME to its current fb_id.

    Returns (fb_id | None, why, n_matches). n_matches > 1 is AMBIGUOUS and is
    refused rather than guessed (C16): two rows sharing a name means the name is
    not a label, and silently taking the first would be a coin flip.
    """
    run = canonical_run or CANONICAL_RUN
    where = "lower(name) = lower(?) AND status = 'PASS'"
    params: list = [name]
    if serving_scope == "canonical_run":
        where += " AND pipeline_run_id = ?"
        params.append(run)
    rows = conn.execute(f"SELECT fb_id, pipeline_run_id FROM fbs WHERE {where}", tuple(params)).fetchall()
    if not rows:
        return None, f"no PASS row named {name!r} in scope {serving_scope}", 0
    if len(rows) > 1:
        return None, f"AMBIGUOUS: {len(rows)} PASS rows share the name in scope {serving_scope}", len(rows)
    return rows[0]["fb_id"], "resolved", len(rows)


def resolve_name_all(conn, name: str, serving_scope: str = "canonical_run",
                     canonical_run: str | None = None) -> tuple[list[str], str]:
    """Resolve a label to EVERY PASS row carrying it, ordered by fb_id (deterministic).

    BUG-970: a SET-valued ruler measures over `expected`, so an ambiguous label must ENLARGE the set
    (INV-4: bigger is stricter). Excluding the whole query instead would drop its anchors from the
    denominator and make the ruler LOOSER - the exact direction INV-4 forbids. This is the set-mode
    sibling of resolve_name(), which keeps refusing for the single-answer join; the choice between
    them is the DECLARED `reanchor.anchor_mode`, never a caller's preference.
    """
    run = canonical_run or CANONICAL_RUN
    where = "lower(name) = lower(?) AND status = 'PASS'"
    params: list = [name]
    if serving_scope == "canonical_run":
        where += " AND pipeline_run_id = ?"
        params.append(run)
    rows = conn.execute(
        f"SELECT fb_id FROM fbs WHERE {where} ORDER BY fb_id", tuple(params)
    ).fetchall()
    if not rows:
        return [], f"no PASS row named {name!r} in scope {serving_scope}"
    return [r["fb_id"] for r in rows], "resolved"


def resolve_golden_anchors(conn, queries: list[dict], serving_scope: str = "canonical_run",
                           ruler_mode: str | None = None) -> tuple[list[dict], dict]:
    """Resolve every `expected_names` entry in place; drop queries with no anchor.

    Returns (kept_queries, report). Mutates a COPY of each query, never the input.

    `kept_queries` entries always carry a non-empty `expected` list, so downstream
    consumers never KeyError and never divide by an unresolvable anchor.

    THE SNAPSHOT IS EVIDENCE, NOT AN AUTHORITY (BUG-969). `expected` in the file is the receipt of the
    last apply: it is the LEGACY FALLBACK for a query that carries no `expected_names` (and for the
    legacy `id` anchor mode). Where names exist they are the ruler, and unioning a stale receipt into
    the denominator would make a SECOND authority - so what was ignored is REPORTED instead
    (`snapshot_ignored`), and a name that stopped resolving can never be masked by an old id.
    """
    mode = str(ruler_mode or RULER_MODE)
    if mode not in RULER_MODES:
        raise SystemExit(f"FATAL: ruler_mode {mode!r} is not one of {list(RULER_MODES)}")
    report: dict = {
        "anchor_mode": ANCHOR_MODE, "ruler_mode": mode, "serving_scope": serving_scope,
        "canonical_run": CANONICAL_RUN, "resolved": [], "unresolved": [],
        "ambiguous": [], "multiplicity": [], "excluded_queries": [],
        "snapshot_ignored": [], "legacy_fallback": [],
    }
    kept: list[dict] = []
    for q in queries:
        q2 = dict(q)
        qlabel = str(q.get("query", ""))
        ids: list[str] = []
        names: list[str] = list(q.get("expected_names") or [])
        snapshot: list[str] = list(q.get("expected") or [])
        if ANCHOR_MODE == "name_then_id" and names:
            for nm in names:
                if mode == "set":
                    # BUG-970: every matching row is expected; the multiplicity is REPORTED, never silent.
                    fids, why = resolve_name_all(conn, nm, serving_scope)
                    if fids:
                        ids.extend(fids)
                        report["resolved"].append(
                            {"query": qlabel, "name": nm, "fb_id": fids[0], "n": len(fids)})
                        if len(fids) > 1:
                            report["multiplicity"].append(
                                {"query": qlabel, "name": nm, "n": len(fids), "fb_ids": fids, "why": why})
                    else:
                        report["unresolved"].append({"query": qlabel, "name": nm, "why": why, "n": 0})
                else:
                    fid, why, n = resolve_name(conn, nm, serving_scope)
                    if fid:
                        ids.append(fid)
                        report["resolved"].append({"query": qlabel, "name": nm, "fb_id": fid})
                    else:
                        bucket = "ambiguous" if n > 1 else "unresolved"
                        report[bucket].append({"query": qlabel, "name": nm, "why": why, "n": n})
            if snapshot:
                # The names ARE the ruler; the snapshot is the receipt of the last apply (BUG-969).
                report["snapshot_ignored"].append({"query": qlabel, "n": len(snapshot)})
        else:
            # LEGACY FALLBACK: the query carries no names, or the declared anchor mode is `id`.
            ids.extend(snapshot)
            if snapshot:
                report["legacy_fallback"].append({"query": qlabel, "n": len(snapshot)})
        if ids:
            q2["expected"] = list(dict.fromkeys(ids))
            kept.append(q2)
        else:
            report["excluded_queries"].append({"query": qlabel, "names": names})
    return kept, report


def sample_self_retrieval(conn, n: int, order: str = "fb_id",
                          canonical_run: str | None = None) -> list[dict]:
    """Deterministic sample of served PASS principle rows (label-free slice).

    No gold label is minted and no owner gate is crossed (D-2898 governs LABELS;
    this slice has none). `order` is config-owned so the sample is reproducible
    (C12/C20: no unrecorded randomness).
    """
    run = canonical_run or CANONICAL_RUN
    rows = conn.execute(
        "SELECT fb_id, name, definition FROM fbs "
        "WHERE pipeline_run_id = ? AND status = 'PASS' AND content_type = 'principle' "
        "AND length(name) > 10 AND length(coalesce(definition, '')) > 80 "
        f"ORDER BY {order} LIMIT ?",
        (run, int(n)),
    ).fetchall()
    return [{"fb_id": r["fb_id"], "name": r["name"], "definition": r["definition"]} for r in rows]


def controls() -> list[tuple[str, bool]]:
    """Known-answer controls for the two pointer-authority rails (BUG-969, BUG-970).

    Each control is a FIXTURE whose right answer was written down before the code was trusted: a guard
    that has never been SEEN failing is a comment (BUG-492), and the ladder runs this with `--selftest`.
    The `id` anchor mode takes the same branch as a nameless query (control 2), so it needs no fixture
    of its own - and a mode override that production never passes would be a knob nobody declared.
    """
    import sqlite3

    run = CANONICAL_RUN
    dead = "a" * 64
    alpha = "b" * 64
    dup1, dup2 = "c" * 64, "d" * 64

    def fixture(rows: list[tuple[str, str]]) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            "create table fbs (fb_id text primary key, name text, pipeline_run_id text, status text)"
        )
        conn.executemany(
            "insert into fbs values (?,?,?,'PASS')", [(fb, nm, run) for fb, nm in rows]
        )
        return conn

    def judge(queries: list[dict], mode: str | None = None,
              rows: list[tuple[str, str]] | None = None) -> tuple[list[dict], dict]:
        conn = fixture(rows if rows is not None else [(alpha, "Alpha")])
        try:
            return resolve_golden_anchors(conn, queries, "canonical_run", ruler_mode=mode)
        finally:
            conn.close()

    # 1. BUG-969: the stored snapshot is EVIDENCE. A dead id beside a live name must not be counted.
    kept, rep = judge([{"query": "q", "expected_names": ["Alpha"], "expected": [dead]}])
    c1 = (len(kept) == 1 and kept[0]["expected"] == [alpha]
          and [r["n"] for r in rep["snapshot_ignored"]] == [1])

    # 2. The LEGACY FALLBACK survives: a query with no names reads its ids, and is COUNTED as doing so.
    kept, rep = judge([{"query": "q", "expected": [dead]}])
    c2 = (len(kept) == 1 and kept[0]["expected"] == [dead]
          and [r["n"] for r in rep["legacy_fallback"]] == [1])

    # 3. A name that no longer resolves EXCLUDES the query - a stale id may never rescue it (BUG-710).
    kept, rep = judge([{"query": "q", "expected_names": ["Ghost"], "expected": [dead]}])
    c3 = (not kept and len(rep["excluded_queries"]) == 1 and len(rep["unresolved"]) == 1)

    # 4. BUG-970: a duplicated label ENLARGES a set-valued ruler (INV-4) and the multiplicity is REPORTED.
    kept, rep = judge([{"query": "q", "expected_names": ["Dup"]}],
                      rows=[(dup1, "Dup"), (dup2, "Dup")])
    c4 = (len(kept) == 1 and sorted(kept[0]["expected"]) == sorted([dup1, dup2])
          and [m["n"] for m in rep["multiplicity"]] == [2] and not rep["excluded_queries"])

    # 5. ...while a SINGLE-answer ruler still REFUSES the same fixture: the coin flip is not taken.
    kept, rep = judge([{"query": "q", "expected_names": ["Dup"]}], mode="single",
                      rows=[(dup1, "Dup"), (dup2, "Dup")])
    c5 = (not kept and len(rep["ambiguous"]) == 1 and len(rep["excluded_queries"]) == 1
          and not rep["multiplicity"])

    return [
        ("a_stored_snapshot_never_enters_the_denominator_when_the_names_resolve", c1),
        ("a_legacy_query_with_no_names_still_reads_its_ids_and_says_so", c2),
        ("a_query_whose_names_all_fail_is_EXCLUDED_never_rescued_by_a_stale_id", c3),
        ("a_set_valued_ruler_keeps_EVERY_row_sharing_a_label_and_reports_multiplicity", c4),
        ("a_single_valued_ruler_still_REFUSES_an_ambiguous_label", c5),
    ]


def main() -> int:
    """CLI: a bare run prints the anchor resolution report without touching the store; --selftest proves
    the two pointer-authority rails on fixtures (no store, no files)."""
    ap = argparse.ArgumentParser(description="Golden-anchor resolver (D-2939)")
    ap.add_argument("--golden", type=Path, default=GOLDEN_PATH)
    ap.add_argument("--serving-scope", default="canonical_run", choices=["canonical_run", "all_runs"])
    ap.add_argument("--selftest", action="store_true", help="known-answer controls (no store, no files)")
    args = ap.parse_args()
    if args.selftest:
        failed = 0
        for label, ok in controls():
            print(f"  {'ok' if ok else '!!'}  {label}")
            failed += 0 if ok else 1
        total = len(controls())
        if failed:
            print(f"FAIL golden --selftest: {failed} of {total} known-answer control(s) did NOT fire")
            return 1
        print(f"ok golden --selftest: {total}/{total} known-answer control(s) fire")
        return 0
    from pipeline.retrieve import get_conn  # local import: keeps this module import-light
    conn = get_conn()
    queries = load_golden(args.golden)
    kept, report = resolve_golden_anchors(conn, queries, args.serving_scope)
    print("═══ GOLDEN ANCHOR RESOLUTION (D-2939) ═══")
    print(f"anchor mode      : {report['anchor_mode']}")
    print(f"ruler mode       : {report['ruler_mode']} (BUG-970: set keeps every row sharing a label)")
    print(f"serving scope    : {report['serving_scope']} (canonical run = {report['canonical_run']})")
    print(f"queries in file  : {len(queries)}")
    print(f"measurable       : {len(kept)}")
    print(f"resolved names   : {len(report['resolved'])}")
    print(f"unresolved names : {len(report['unresolved'])}")
    print(f"ambiguous names  : {len(report['ambiguous'])}")
    print(f"multi-row labels : {len(report['multiplicity'])} (kept as a SET, never dropped)")
    print(f"snapshot ignored : {len(report['snapshot_ignored'])} quer(ies) (names are the ruler, BUG-969)")
    print(f"legacy fallback  : {len(report['legacy_fallback'])} quer(ies) (no names: ids ARE the ruler)")
    for r in report["unresolved"]:
        print(f"   ✗ {r['name'][:52]!r} <- {r['query'][:40]}")
    for r in report["ambiguous"]:
        print(f"   ⚠ {r['name'][:52]!r} ({r['n']} rows) <- {r['query'][:40]}")
    for m in report["multiplicity"]:
        print(f"   • {m['name'][:52]!r} matched {m['n']} PASS rows - all kept in the expected set")
    if REQUIRE_RESOLVABLE and not kept:
        print("   ❌ nothing measurable (C16)")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
