#!/usr/bin/env python3
"""scripts/normalize_duplicate_of_marker.py — reshape the `duplicate_of` marker to ONE shape.

FINDING (measured on the live store, 2026-10-12): all 7,640 rows carry `duplicate_of = ''`
(TEXT), never NULL — because stage6_commit's `_safe_str` maps an absent value to `""`. So the
predicate D-271d documents as the retrieval guard, `duplicate_of IS NULL`, matched ZERO rows,
and the column's own schema comment ("canonical fb_id when this row is a dedup (NULL
otherwise)") was a claim the code could not keep — the BUG-498 class. That was harmless while
`duplicate_of` was reserved debt with no writer and no reader. It stops being harmless the
moment the D-2951 commit gate WRITES the column: a marker would then coexist with 7,640
absent-but-non-NULL cells, i.e. two shapes for one meaning, and the first reader to trust the
documented predicate would silently see the whole store as "marked".

FIX (two halves, in this order):
  1. the WRITER emits NULL for absent (`pipeline/dedup_gate.duplicate_marker`, landed);
  2. this script normalizes the rows written BEFORE that fix.
Readers use truthiness (`if row.get("duplicate_of")`) and `duplicate_marker()` tolerates both
shapes, so this is an IDENTITY-PRESERVING reshaping of "absent" — nothing observable changes.
It is measured before the write, not assumed.

C13/R-D410: --apply takes a crash-safe backup FIRST, writes in ONE `BEGIN IMMEDIATE`
transaction, verifies the post-state, and refuses to proceed if any row already carries a real
marker (that would be a dedup defect to review, not a shape to reshape). Dry-run is the
default and never writes.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"
BACKUP_DIR = DB_PATH.parent / "backups"


def audit(cur: sqlite3.Cursor) -> dict[str, int]:
    """Count the three possible states of the marker column (read-only)."""
    cur.execute(
        "SELECT CASE WHEN duplicate_of IS NULL THEN 'null' "
        "WHEN TRIM(duplicate_of) = '' THEN 'empty' ELSE 'marked' END AS shape, COUNT(*) "
        "FROM fbs GROUP BY 1"
    )
    return {shape: n for shape, n in cur.fetchall()}


def real_markers(cur: sqlite3.Cursor) -> list[dict]:
    """Rows that already point at another row — a dedup fact, never reshaped by this script."""
    cur.execute(
        "SELECT fb_id, name, duplicate_of, status FROM fbs "
        "WHERE duplicate_of IS NOT NULL AND TRIM(duplicate_of) <> ''"
    )
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def apply(cur: sqlite3.Cursor) -> int:
    """Normalize every empty-string marker to NULL. Returns the number of rows changed."""
    cur.execute("UPDATE fbs SET duplicate_of = NULL WHERE duplicate_of IS NOT NULL AND TRIM(duplicate_of) = ''")
    return cur.rowcount


def _backup() -> Path:
    """C13: crash-safe copy of the live DB before the mutation."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"maxwell.db.pre_dupmarker_{time.strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(DB_PATH, dest)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize the duplicate_of marker to one shape ('', -> NULL).")
    ap.add_argument("--apply", action="store_true", help="write (default is dry-run; C13 backup first)")
    args = ap.parse_args()

    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()

    before = audit(cur)
    markers = real_markers(cur)
    rows = before.get("empty", 0)

    print(f"db: {DB_PATH}")
    print(f"marker shapes before: {before}")
    print(f"rows to normalize (empty -> NULL): {rows}")
    print(f"rows ALREADY carrying a real marker: {len(markers)}")
    for r in markers[:10]:
        print(f"    {r['fb_id'][:12]} {str(r['name'])[:40]:42} -> {str(r['duplicate_of'])[:12]} status={r['status']}")
    if len(markers) > 10:
        print(f"    ... and {len(markers) - 10} more (NOT touched by this script — review as a dedup fact)")

    if not args.apply:
        print("\n[dry-run] nothing written. Re-run with --apply to normalize (C13 backup first).")
        con.close()
        return 0

    if rows == 0 and before.get("null", 0):
        print("\n[no-op] every marker is already NULL — nothing to normalize.")
        con.close()
        return 0

    bak = _backup()
    print(f"\nC13 backup: {bak}")

    try:
        con.execute("BEGIN IMMEDIATE")
        changed = apply(cur)
        after = audit(cur)
        if after.get("empty", 0) != 0:
            raise RuntimeError(f"post-state still holds {after.get('empty')} empty marker(s) — rolling back")
        con.commit()
    except BaseException:
        con.rollback()
        con.close()
        raise

    print(f"normalized {changed} row(s)")
    print(f"marker shapes after: {after}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
