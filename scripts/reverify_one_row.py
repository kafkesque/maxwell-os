#!/usr/bin/env python3
"""scripts/reverify_one_row.py - re-run the S5 checks ONE named row should already carry (BUG-979).

WHY THIS EXISTS (MEASURED 2026-10-23). The single-concept write path ran HALF the verification: it recorded a
`factual` check and never called `check_mechanism_quality`, so the row it wrote (f523504e, "The Kernel of
Strategy") is UNDECIDABLE to scripts/check_s5_score_axis.py - and `just health` is RED on that rail because of it.
The PREVENTION half is fixed at the producer (pipeline/insert_single_concept.py now runs BOTH checks). This is the
DATA half for the row already in the store.

WHY NOT scripts/repair_s5_score_axis.py. That instrument RE-DERIVES the score axis from a record the row already
holds, and it correctly refuses a row whose record is incomplete (`unevaluable`). The missing thing here is the
CHECK ITSELF - a measurement, not a re-derivation - so it cannot come from a deriver: it comes from the pipeline's
own check functions (pipeline/stage5_verify.py), the SAME instrument the single-concept path should have called.
No rule is minted here and no model is consulted beyond the declared local NLI check (C1/D343: deterministic,
LLM-free).

WHAT IT MAY WRITE (declared, T-196/D-3136). The STORE FACE of the ONE verification home
(pipeline/verify_record.py::verify_one_record → store_cells()): the record, the score axis (confidence +
review flag), the label co-derived from the same record, the ISOR payload the axis consumed, the facet tier and the
verifier identity. It writes no subset of its own: a hand-picked subset is how this tool used to write a confidence
derived WITH an ISOR rating beside a BLANK `isor` cell. `status` and `s5_reason` remain the AGGREGATION's outputs -
if the fresh factual verdict DISAGREES with the stored one, the tool REFUSES and names the row, because that row
needs a full re-verification, not a cell edit (a verdict change is available only through --allow-verdict-change).

SAFETY. Dry-run is the default. --apply takes a C13 SQLite backup, opens ONE BEGIN IMMEDIATE, re-reads and
re-derives the post-state INSIDE the transaction (D-2970) and commits only when every derived cell agrees.

Usage:
    python3 scripts/reverify_one_row.py --fb-id <id>            # dry-run: measure and print, write nothing
    python3 scripts/reverify_one_row.py --fb-id <id> --apply    # back up, write, verify (one transaction)
    python3 scripts/reverify_one_row.py --selftest              # known-answer controls on a FIXTURE store
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.serving_gate import content_types_without_factual_claim  # noqa: E402
from pipeline.verify_record import hydrate_json_lists as hydrate  # noqa: E402
from pipeline.verify_record import verify_one_record  # noqa: E402

RECEIPT: Path = ROOT / "governance" / "evidence" / "reverify_one_row_receipt.json"

# T-196/D-3136: the ONE home of the sequence (this tool no longer asks the checks itself).
#: The write set IS the home's store face (T-196/D-3136): the record, the score axis (whose inputs include ISOR,
#: so a confidence derived WITH an ISOR rating may not be written beside a blank `isor` — D279 quartet atomicity),
#: the label co-derived from the same record, the facet tier and the verifier identity. A hand-picked subset was
#: how this tool left `isor` blank while writing a confidence that had consumed it.
WRITE_COLUMNS: tuple[str, ...] = ("verification_results", "confidence_score", "needs_human_review",
                                  "epistemic_status", "status", "s5_reason", "verification_method",
                                  "isor", "practicality", "verifier_model")
# THE INPUT CONTRACT OF THE CHECKS, MEASURED (BUG-979 owed item 2). The store keeps these two columns as JSON TEXT;
# pipeline/schema_accessor.fb_source_texts accepts only a LIST, so a raw store row makes the NLI check answer
# "No evidence — QUARANTINE" for a row that plainly HAS evidence (MEASURED 2026-10-23 on f523504e: stored
# passed=True, re-run passed=False, detail "No evidence"). A re-verification must therefore HYDRATE the row first.
def compute(fb: dict[str, Any]) -> dict[str, Any]:
    """Ask the ONE verification home what this row's record is, and return it in a flat, printable shape.

    Args:
        fb: the FULL row (a column subset makes the checks and the derivers grade empty fields — BUG-979).

    Returns:
        {"results", "fact_passed", "mech_score", "enrich", "confidence", "needs_review", "epistemic_status",
         "status", "s5_reason", "verification_method", "cells"} where `cells` is the STORE face of the record.

    Raises:
        SystemExit: when the row's role is declared as carrying no factual claim (the axis is ABSENT by D-2942).
    """
    if str(fb.get("content_type") or "") in content_types_without_factual_claim():
        raise SystemExit("REFUSED: this role is declared as carrying NO factual claim - its score axis is ABSENT "
                         "by design (D-2942/D-2957) and must never be manufactured here")
    outcome = verify_one_record(fb)
    return {"results": outcome.verification_results, "fact_passed": outcome.fact_passed,
            "mech_score": outcome.mech_score, "enrich": outcome.enrich_score,
            "confidence": outcome.confidence_score, "needs_review": outcome.needs_human_review,
            "epistemic_status": outcome.epistemic_status, "status": outcome.status,
            "s5_reason": outcome.s5_reason, "verification_method": outcome.verification_method,
            "cells": outcome.store_cells()}


def stored_factual(fb: dict[str, Any]) -> dict[str, Any] | None:
    """Return the row's stored `factual` check, or None when the record carries no such check."""
    try:
        results = json.loads(fb.get("verification_results") or "[]")
    except (TypeError, ValueError):
        return None
    return next((x for x in results if isinstance(x, dict) and x.get("check_name") == "factual"), None)


def decide(fb: dict[str, Any]) -> dict[str, Any]:
    """Return the pre-state, the freshly computed state and the write set - refusing an inexpressible change.

    Raises:
        SystemExit: when the fresh factual verdict DISAGREES with the stored one (a full re-verification is
            needed, and this tool never rewrites the aggregation's own verdict).
    """
    fresh = compute(hydrate(fb))
    pre = {c: fb.get(c) for c in WRITE_COLUMNS}
    post = {c: fresh["cells"][c] for c in WRITE_COLUMNS}
    changed = [c for c in WRITE_COLUMNS if str(pre[c]) != str(post[c])]
    verdict_changed = str(pre.get("status")) != str(post["status"])
    return {"pre": pre, "post": post, "fresh": fresh, "changed": changed, "verdict_changed": verdict_changed}


def _backup() -> Path:
    """Take a SQLite-API backup of the store before the first write (C13)."""
    dest_dir = DB_PATH.parent / "backups"
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / f"maxwell.db.pre_reverify_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    src, out = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True), sqlite3.connect(dest)
    try:
        src.backup(out)
    finally:
        out.close()
        src.close()
    print(f"  [C13] backup -> {dest.relative_to(ROOT)}")
    return dest


def apply_one(con: sqlite3.Connection, fb_id: str, plan: dict[str, Any]) -> dict[str, Any]:
    """Write the derived cells, then RE-DERIVE them inside the same transaction (D-2970/C6)."""
    con.execute("BEGIN IMMEDIATE")
    try:
        sets = ", ".join(f"{c} = ?" for c in plan["changed"])
        con.execute(f"UPDATE fbs SET {sets} WHERE fb_id = ?", [plan["post"][c] for c in plan["changed"]] + [fb_id])
        row = con.execute("SELECT * FROM fbs WHERE fb_id = ?", (fb_id,)).fetchone()
        residual = decide(dict(row))["changed"] if row else ["row vanished"]
        if residual:
            con.rollback()
            raise SystemExit(f"FAIL-CLOSED: the post-state does not re-derive inside the transaction: {residual}")
        con.commit()
    except BaseException:
        con.rollback()
        raise
    return {"changed": plan["changed"], "verified_in_transaction": True}


def selftest() -> int:
    """Known-answer controls for this tool's own decisions - no model, no store (BUG-491/492)."""
    fact = {"check_name": "factual", "passed": True, "score": 0.9, "detail": "d" * 40}

    def row(results: list[dict[str, Any]], conf: object = None) -> dict[str, Any]:
        return {"content_type": "principle", "verification_results": json.dumps(results),
                "confidence_score": conf, "needs_human_review": 0, "epistemic_status": "source-supported",
                "isor": None, "application": "a" * 60, "failure_mode": "b" * 60, "definition": "c" * 60,
                "boundary": "d" * 60}

    checks: list[tuple[str, bool]] = [
        ("a record with only `factual` is exactly the BUG-979 shape", stored_factual(row([fact])) == fact),
        ("a record with NO factual check returns None (never an invented one)", stored_factual(row([])) is None),
        ("the write set is DECLARED: every cell of the home's store face, and nothing outside it",
         WRITE_COLUMNS == ("verification_results", "confidence_score", "needs_human_review", "epistemic_status",
                           "status", "s5_reason", "verification_method", "isor", "practicality",
                           "verifier_model")),
        ("a role with no factual claim is REFUSED (its axis is ABSENT by design)",
         _raises(lambda: compute({"content_type": sorted(content_types_without_factual_claim())[0]}))),
        ("a store row's JSON-TEXT evidence_passages is HYDRATED to a list (the shape the checks declare)",
         isinstance(hydrate({"evidence_passages": json.dumps(["a passage"])})["evidence_passages"], list)),
        ("a row already carrying a list is left alone", hydrate({"evidence_passages": ["x"]})["evidence_passages"] == ["x"]),
        ("unparseable JSON in a declared column FAILS CLOSED",
         _raises(lambda: hydrate({"evidence_passages": "[not json"}))),
    ]
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(f"selftest: {len(checks) - len(bad)}/{len(checks)} controls held")
    return 1 if bad else 0


def _raises(fn: Any) -> bool:
    """Return True when the callable refuses (SystemExit) - a one-line shape for the controls above."""
    try:
        fn()
    except SystemExit:
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="re-run the S5 checks ONE named row should carry (dry-run default)")
    ap.add_argument("--fb-id", default="", help="the full fb_id (a prefix is refused: an exact row, never a sweep)")
    ap.add_argument("--apply", action="store_true", help="write (requires a C13 backup; default is dry-run)")
    ap.add_argument("--allow-verdict-change", action="store_true",
                    help="permit the repair to move the row's VERDICT (status/s5_reason), not only its cells")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls only")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.fb_id or len(args.fb_id) != 64:
        print("FAIL-CLOSED: --fb-id must be a full 64-hex fb_id (this tool repairs ONE named row)")
        return 1

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT * FROM fbs WHERE fb_id = ?", (args.fb_id,)).fetchone()
        if row is None:
            print(f"FAIL-CLOSED: no row {args.fb_id} in the store")
            return 1
        fb = dict(row)
        print(f"row {args.fb_id[:12]} {fb.get('name')!r} | role {fb.get('content_type')} | status {fb.get('status')}")
        plan = decide(fb)
        print(f"  mechanism_quality: passed={plan['fresh']['results'][0]['passed']} score={plan['fresh']['mech_score']}")
        print(f"  factual:           passed={plan['fresh']['fact_passed']} score={plan['fresh']['results'][1]['score']}")
        print(f"  enrichment={plan['fresh']['enrich']} -> confidence {plan['pre']['confidence_score']} -> "
              f"{plan['fresh']['confidence']} | needs_human_review {plan['pre']['needs_human_review']} -> "
              f"{int(plan['fresh']['needs_review'])}")
        print(f"  epistemic_status {plan['pre']['epistemic_status']} -> {plan['fresh']['epistemic_status']}")
        print(f"  status {plan['pre']['status']} -> {plan['fresh']['status']} | s5_reason "
              f"{plan['pre']['s5_reason']} -> {plan['fresh']['s5_reason']}")
        print(f"  write set: {plan['changed']}")
        if plan["verdict_changed"] and not args.allow_verdict_change:
            print("REFUSED: this repair would CHANGE THE VERDICT - re-run with --allow-verdict-change "
                  "(a verdict change is a bigger act than a cell repair, so it is never implicit)")
            return 1
        if not args.apply:
            print("\n[dry-run] nothing was mutated.")
            return 0
        if not plan["changed"]:
            print("nothing to write - the row already carries the complete record")
            return 0
        backup = _backup()
        stats = apply_one(con, args.fb_id, plan)
        print(f"[apply] {stats}")
        receipt = {"schema_version": 1, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "tool": "scripts/reverify_one_row.py", "bug": "BUG-979", "fb_id": args.fb_id,
                   "name": fb.get("name"), "backup": str(backup.relative_to(ROOT)),
                   "pre": plan["pre"], "post": plan["post"], "fresh": plan["fresh"], "stats": stats}
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"receipt -> {RECEIPT.relative_to(ROOT)}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
