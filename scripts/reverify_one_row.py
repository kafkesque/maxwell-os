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

WHAT IT MAY WRITE (declared, minimal). verification_results, confidence_score, needs_human_review, epistemic_status
- the record and the two halves of the score axis plus the label that is CO-DERIVED from the same record
(serving_gate.derive_epistemic_status, the ONE home). `status` and `s5_reason` are the S5 AGGREGATION's outputs and
are NEVER written here: if the fresh factual verdict DISAGREES with the stored one, the tool REFUSES and names the
row, because that row needs a full re-verification, not a cell edit.

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
from pipeline.serving_gate import (  # noqa: E402
    content_types_without_factual_claim,
    derive_conf_and_review,
    derive_epistemic_status,
)
from pipeline.stage5_verify import (  # noqa: E402
    _check_enrichment_quality,
    check_mechanism_quality,
    deberta_check,
)

WRITE_COLUMNS: tuple[str, ...] = ("verification_results", "confidence_score", "needs_human_review",
                                  "epistemic_status", "status", "s5_reason", "verification_method")
# THE INPUT CONTRACT OF THE CHECKS, MEASURED (BUG-979 owed item 2). The store keeps these two columns as JSON TEXT;
# pipeline/schema_accessor.fb_source_texts accepts only a LIST, so a raw store row makes the NLI check answer
# "No evidence — QUARANTINE" for a row that plainly HAS evidence (MEASURED 2026-10-23 on f523504e: stored
# passed=True, re-run passed=False, detail "No evidence"). A re-verification must therefore HYDRATE the row first.
JSON_LIST_COLUMNS: tuple[str, ...] = ("evidence_passages", "evidence_passages_shown")
RECEIPT: Path = ROOT / "governance" / "evidence" / "reverify_one_row_receipt.json"


def _isor(raw: object) -> dict[str, Any]:
    """Return the row's ISOR payload as a mapping; a blank/absent value is the declared empty mapping."""
    if isinstance(raw, dict):
        return raw
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:  # C16: loud, never silently an empty score
        raise SystemExit(f"FAIL-CLOSED: isor is not parseable JSON: {text[:80]!r}") from exc
    return parsed if isinstance(parsed, dict) else {}


def hydrate(fb: dict[str, Any]) -> dict[str, Any]:
    """Decode the JSON-LIST columns a store row carries as TEXT, so the checks read the shape they declare.

    Args:
        fb: a row as read from the store (JSON columns still TEXT).

    Returns:
        The same mapping with every JSON_LIST_COLUMNS value decoded into a list (an absent/blank value stays as-is).

    Raises:
        SystemExit: when a declared JSON column is not parseable (C16: never silently "no evidence").
    """
    out = dict(fb)
    for col in JSON_LIST_COLUMNS:
        value = out.get(col)
        if isinstance(value, str) and value.strip().startswith("["):
            try:
                out[col] = json.loads(value)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"FAIL-CLOSED: {col} is not parseable JSON: {value[:80]!r}") from exc
    return out


def compute(fb: dict[str, Any]) -> dict[str, Any]:
    """Run the S5 checks over one stored row and derive the axis from what they say.

    Args:
        fb: the FULL row (a column subset makes the enrichment check read empty fields and invents a defect).

    Returns:
        {"results": [...], "fact_passed": bool, "mech_score": float, "enrich": float,
         "confidence": float, "needs_review": bool, "epistemic_status": str}

    Raises:
        SystemExit: when the row's role is declared as carrying no factual claim (the axis is ABSENT by D-2942).
    """
    if str(fb.get("content_type") or "") in content_types_without_factual_claim():
        raise SystemExit("REFUSED: this role is declared as carrying NO factual claim - its score axis is ABSENT "
                         "by design (D-2942/D-2957) and must never be manufactured here")
    mech_passed, mech_score, mech_detail = check_mechanism_quality(fb)
    if mech_passed:
        fact_passed, fact_score, fact_detail, method = *deberta_check(fb), "deberta-nli"
    else:
        # BUG-980: the SAME ordering S5 declares - a failed mechanism gate IS the factual verdict, the NLI is never
        # asked (stage5_verify.py). MEASURED 2026-10-23: 2,086/2,086 stored rows with mechanism_quality=false are
        # QUARANTINE, so any other outcome would be a state the store has never held.
        fact_passed, fact_score, fact_detail, method = False, 0.0, f"MECH FAIL: {mech_detail}", "mech_quality"
    results = [
        {"check_name": "mechanism_quality", "passed": bool(mech_passed), "score": float(mech_score), "detail": str(mech_detail)},
        {"check_name": "factual", "passed": bool(fact_passed), "score": float(fact_score), "detail": str(fact_detail)},
    ]
    _ok, enrich, _detail = _check_enrichment_quality(fb)
    isor = _isor(fb.get("isor"))
    confidence, needs_review = derive_conf_and_review(bool(fact_passed), float(mech_score), float(enrich), isor)
    from pipeline.serving_gate import derive_status  # PLC0415: the ONE home of (status, s5_reason)

    status, s5_reason = derive_status(json.dumps(results))
    return {"results": results, "fact_passed": bool(fact_passed), "mech_score": float(mech_score),
            "enrich": float(enrich), "confidence": confidence, "needs_review": needs_review,
            "epistemic_status": derive_epistemic_status(bool(fact_passed), isor.get("rating")),
            "status": status, "s5_reason": s5_reason, "verification_method": method}


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
    post = {"verification_results": json.dumps(fresh["results"]), "confidence_score": fresh["confidence"],
            "needs_human_review": 1 if fresh["needs_review"] else 0, "epistemic_status": fresh["epistemic_status"],
            "status": fresh["status"], "s5_reason": fresh["s5_reason"], "verification_method": fresh["verification_method"]}
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
        ("the write set is DECLARED: every cell of the S5 outcome, and nothing outside it",
         WRITE_COLUMNS == ("verification_results", "confidence_score", "needs_human_review", "epistemic_status",
                           "status", "s5_reason", "verification_method")),
        ("an unparseable ISOR payload FAILS CLOSED, not silently empty",
         _raises(lambda: _isor("{not json"))),
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
