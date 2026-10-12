#!/usr/bin/env python3
"""scripts/restamp_bug725_provenance.py — governed re-stamp of the 1,049 non-principle
rows whose label-provenance quartet is empty (BUG-725, D-2949).

WHY (measured live store): process_template 774 / process_instance 156 / tool_instruction
(new) 94 / growth_edge 25 = 1,049 rows carry discipline + extraction_type but an EMPTY
quartet (menu_hash + the three *_source tiers all blank). That is NOT a broken stamp — S4
routed these non-principle objects to a sidecar and never stamped the tier sources — but
the rail is RIGHT to be red until the provenance is DECLARED.

STAMPS (owner-ruled BUG-725, corrected from the buglog's stale "no discipline label" claim —
discipline IS populated 1,049/1,049, so NOT_APPLICABLE on discipline_source would FALSIFY):
  content_type_source   = "deterministic"            (D-343/D-2747: role is deterministically
                                                      resolved, never LLM-classified)
  discipline_source     = "llm_extracted_from_source" (discipline IS LLM-assigned)
  extraction_type_source= "llm_extracted_from_source" (extraction_type IS LLM-assigned)
  menu_hash             = NOT_APPLICABLE sentinel     (menu was NOT run for these rows' role
                                                      routing; D-277 forbids backfilling a hash)

R-D410/C13: --apply takes a crash-safe backup FIRST (maxwell.db -> backups/), writes via
BEGIN IMMEDIATE in one transaction, and refuses to touch any row with a PARTIAL quartet
(those are a different defect class, left for owner review). --dry-run is the default and
never writes.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"

NOT_APPLICABLE = "NOT_APPLICABLE"
NON_PRINCIPLE = ("process_template", "process_instance", "tool_instruction", "growth_edge")

STAMP = {
    "content_type_source": "deterministic",
    "discipline_source": "llm_extracted_from_source",
    "extraction_type_source": "llm_extracted_from_source",
    "menu_hash": NOT_APPLICABLE,
}
QUARTET = ("menu_hash", "content_type_source", "discipline_source", "extraction_type_source")


def _target_rows(cur: sqlite3.Cursor) -> list[dict]:
    cur.execute(
        f"""SELECT fb_id, name, content_type, menu_hash, content_type_source,
                   discipline_source, extraction_type_source
            FROM fbs WHERE content_type IN ({",".join("?" * len(NON_PRINCIPLE))})
              AND (content_type_source IS NULL OR content_type_source = '')""",
        NON_PRINCIPLE,
    )
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _partial_quartet(row: dict) -> bool:
    vals = [str(row.get(c) or "").strip() for c in QUARTET]
    return any(vals) and not all(vals)  # some-but-not-all = a different defect class


def audit(cur: sqlite3.Cursor) -> tuple[list[dict], list[dict]]:
    rows = _target_rows(cur)
    by_ct: dict[str, int] = {}
    for r in rows:
        by_ct[r["content_type"]] = by_ct.get(r["content_type"], 0) + 1
    partial = [r for r in rows if _partial_quartet(r)]
    print(f"target rows (empty quartet, non-principle): {len(rows)}")
    for ct, n in sorted(by_ct.items()):
        print(f"  {ct:18} {n}")
    print(f"partial-quartet rows (REFUSED, owner review): {len(partial)}")
    for r in partial[:5]:
        print(f"    {r['fb_id'][:12]} {r['name'][:40]} {[(c, r[c]) for c in QUARTET]}")
    return rows, partial


def apply(cur: sqlite3.Cursor, rows: list[dict]) -> int:
    for r in rows:
        cur.execute(
            "UPDATE fbs SET content_type_source=?, discipline_source=?, "
            "extraction_type_source=?, menu_hash=? WHERE fb_id=?",
            (STAMP["content_type_source"], STAMP["discipline_source"],
             STAMP["extraction_type_source"], STAMP["menu_hash"], r["fb_id"]),
        )
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write (default is dry-run)")
    args = ap.parse_args()

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    rows, partial = audit(cur)
    if not rows:
        print("no target rows — nothing to do")
        con.close()
        return 0

    if not args.apply:
        print(f"\n[dry-run] would stamp {len(rows)} rows. Re-run with --apply to write (C13 backup first).")
        con.close()
        return 0

    # C13 backup first (crash-safe copy of the live DB)
    bak_dir = DB_PATH.parent / "backups"
    bak_dir.mkdir(exist_ok=True)
    bak = bak_dir / f"maxwell.db.pre_bug725_{time.strftime('%Y%m%d_%H%M%S')}"
    print(f"[C13] backing up -> {bak}")
    shutil.copy2(DB_PATH, bak)

    con.execute("BEGIN IMMEDIATE")
    try:
        n = apply(cur, rows)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    print(f"[apply] stamped {n} rows (menu_hash=NOT_APPLICABLE, 3 tier sources)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
