#!/usr/bin/env python3
"""repair_single_concept_provenance.py — fill the provenance holes ONE insert left (BUG-977).

WHY THIS EXISTS (MEASURED 2026-10-23). pipeline/insert_single_concept.py wrote exactly one row
(f523504ee9030e02bd02d5ca6ba6a5f9e174b217b83e805e73025323b44cc31d, "The Kernel of Strategy") and left
FOUR cells blank that the other 7,640/7,640 rows carry:
    content_type_source      ''   the label's AUTHORSHIP — absent
    discipline_source        ''   the discipline's authorship — absent
    extraction_type_source   ''   the form's authorship — absent
    created_at               ''   the row's time stamp — blank
That is the BUG-742 class (a label present, its authorship absent) plus the blank shape
check_store_columns reads as CONSTANT-OR-BLANK on a declared `value` column (it went RED on it).

THE VALUES ARE DERIVED, NEVER INVENTED (D-3034/D-3109):
  * the three * authorships come from config/pipeline_config.yaml#single_concept — the SAME declaration the
    repaired producer now stamps, read through the SAME reader (pipeline.insert_single_concept.declared_ontology),
    so the repair and the producer cannot disagree (C21: one rule, one home);
  * created_at is derived from the row's OWN committed_at — on this path the extraction and the commit are
    the same act, and committed_at was written by the producer, so this is a RE-DERIVATION, not a guess.

NEVER OVERWRITES. A cell is filled only when it is BLANK; a row that is already stamped is refused
(idempotent, and a second run is a no-op rather than a silent re-stamp). Dry-run by default; --apply writes
ONE transaction with a C13 backup first and re-derives the post-state INSIDE the transaction before COMMIT.

spec: BUG-977 / D-3130. LLM-free, deterministic (D-343/C1).

usage: python3 scripts/repair_single_concept_provenance.py --fb-id <id> [--apply]
exit:  0 nothing owed | 0 applied (with --apply) | 1 refused | 2 cannot evaluate
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_DEFAULT = "knowledge pipeline/maxwell.db"
#: the three authorship columns this repair may fill, mapped to their key in the declaration
AUTHORSHIP_COLUMNS: dict[str, str] = {
    "content_type_source": "content_type_source",
    "discipline_source": "discipline_source",
    "extraction_type_source": "extraction_type_source",
}


def _factual_passed(verification_results: object) -> bool | None:
    """The `factual` check's verdict from the row's OWN record (the serving gate's co-derivation input).

    Returns None when the record carries no factual check — the caller then REFUSES rather than deriving a
    label from a record that cannot answer (D-3034: a value must resolve).
    """
    import json as _json

    try:
        record = _json.loads(verification_results) if isinstance(verification_results, str) else verification_results
    except (TypeError, ValueError):
        return None
    if not isinstance(record, list):
        return None
    for check in record:
        if isinstance(check, dict) and check.get("check_name") == "factual" and "passed" in check:
            return bool(check["passed"])
    return None


def _isor_rating(isor_raw: object) -> str | None:
    """The ISOR rating from the row's own `isor` cell, or None (the derivation fails closed on absence)."""
    import json as _json

    isor = isor_raw
    if isinstance(isor, str) and isor.strip():
        try:
            isor = _json.loads(isor)
        except ValueError:
            return None
    return isor.get("rating") if isinstance(isor, dict) else None


def _blank(v: object) -> bool:
    """True when a stored cell is EITHER shape of absent (NULL or a non-NULL blank, BUG-737)."""
    return v is None or str(v).strip() == ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Fill the BUG-977 provenance holes on ONE single-concept row.")
    ap.add_argument("--fb-id", required=True, help="the fb_id to repair (exact)")
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--apply", action="store_true", help="write (default: dry-run)")
    ap.add_argument("--backup-dir", default="backups")
    args = ap.parse_args()

    import yaml

    from pipeline.insert_single_concept import declared_ontology

    cfg = yaml.safe_load((PROJECT_ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
    ontology = declared_ontology(cfg)  # the SAME reader the producer uses: the repair cannot drift from it

    db = PROJECT_ROOT / args.db
    if not db.exists():
        print(f"CANNOT EVALUATE: store not found at {db}")
        return 2

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "select fb_id, name, content_type, content_type_source, discipline_source, "
            "extraction_type_source, created_at, committed_at, epistemic_status, "
            "verification_results, isor from fbs where fb_id = ?",
            (args.fb_id,),
        ).fetchone()
        if row is None:
            print(f"CANNOT EVALUATE: no row with fb_id {args.fb_id!r} (D-3034: nothing resolves)")
            return 2

        print(f"row   : {row['fb_id']}  {row['name']!r}  content_type={row['content_type']!r}")
        print(f"before: content_type_source={row['content_type_source']!r} "
              f"discipline_source={row['discipline_source']!r} "
              f"extraction_type_source={row['extraction_type_source']!r} "
              f"created_at={row['created_at']!r} committed_at={row['committed_at']!r} "
              f"epistemic_status={row['epistemic_status']!r}")

        writes: dict[str, str] = {}
        for column, key in AUTHORSHIP_COLUMNS.items():
            if _blank(row[column]):
                writes[column] = ontology[key]
        if _blank(row["created_at"]):
            if _blank(row["committed_at"]):
                # no time stamp anywhere on the row: inventing one would be a fabricated measurement
                print("REFUSED: created_at AND committed_at are both blank — no derivable time stamp exists "
                      "(D-3034: a value must RESOLVE, never be invented)")
                return 1
            writes["created_at"] = str(row["committed_at"])

        # hole 5 (D-2284/BUG-499): the epistemic LABEL is co-derived from the row's OWN record — the same rule
        # S5 uses (stage5_verify.py:1268) and the same one scripts/check_serving_gate.py re-derives with. A
        # derivation whose input is absent is REFUSED, never guessed.
        if _blank(row["epistemic_status"]):
            from pipeline.serving_gate import derive_epistemic_status

            passed = _factual_passed(row["verification_results"])
            if passed is None:
                print("REFUSED: the row carries no readable `factual` verdict, so the epistemic label cannot be "
                      "DERIVED (D-3034: never invented)")
                return 1
            writes["epistemic_status"] = derive_epistemic_status(passed, _isor_rating(row["isor"]))

        if not writes:
            print("NOT OWED: every provenance cell is already stamped (idempotent — nothing written).")
            return 0

        print("would write: " + ", ".join(f"{k}={v!r}" for k, v in writes.items()))
        if not args.apply:
            print("[dry-run] rerun with --apply to write.")
            return 0

        # C13: a store mutation gets a backup, taken with sqlite's own backup API (consistent under WAL).
        backup_dir = PROJECT_ROOT / args.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"maxwell.db.pre_bug977_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        dest = sqlite3.connect(backup_path)
        try:
            conn.backup(dest)
        finally:
            dest.close()
        print(f"backup: {backup_path.relative_to(PROJECT_ROOT)} "
              f"({backup_path.stat().st_size / 1_048_576:.1f} MiB)")

        assignments = ", ".join(f"{c} = ?" for c in writes)
        conn.execute("BEGIN IMMEDIATE")
        try:
            cur = conn.execute(
                f"update fbs set {assignments} where fb_id = ?", (*writes.values(), args.fb_id)
            )
            if cur.rowcount != 1:
                raise RuntimeError(f"expected 1 row, updated {cur.rowcount} — rolling back")
            # post-state re-derived INSIDE the transaction, before COMMIT (the D-2970 pattern)
            after = conn.execute(
                "select content_type_source, discipline_source, extraction_type_source, created_at, "
                "epistemic_status from fbs where fb_id = ?", (args.fb_id,)
            ).fetchone()
            still_blank = [c for c in (*AUTHORSHIP_COLUMNS, "created_at", "epistemic_status") if _blank(after[c])]
            if still_blank:
                raise RuntimeError(f"post-state still blank on {still_blank} — rolling back")
            for column, key in AUTHORSHIP_COLUMNS.items():
                if after[column] != ontology[key]:
                    raise RuntimeError(f"post-state {column}={after[column]!r} != declared {ontology[key]!r}")
            if "epistemic_status" in writes and after["epistemic_status"] != writes["epistemic_status"]:
                raise RuntimeError(f"post-state epistemic_status={after['epistemic_status']!r} != derived "
                                   f"{writes['epistemic_status']!r}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        print(f"after : content_type_source={after['content_type_source']!r} "
              f"discipline_source={after['discipline_source']!r} "
              f"extraction_type_source={after['extraction_type_source']!r} "
              f"created_at={after['created_at']!r}")
        print(f"APPLIED: {len(writes)} cell(s) on 1 row ({args.fb_id}).")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
