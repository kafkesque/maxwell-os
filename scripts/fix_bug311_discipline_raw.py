#!/usr/bin/env python3
"""
fix_bug311_discipline_raw.py — T-311 (D2540 step 1) deterministic empty-raw repair.

BUG: 311 FBs carry a RESOLVED canonical `discipline` (non-'emerging') but an EMPTY
`discipline_raw`. The raw label was lost during the Track B reclassification that
resolved the discipline; the canonical survived, so this is a pure metadata-copy
repair (no LLM, no re-classification).

Rule (deterministic, D2540):
    discipline_raw := discipline          -- metadata copy (raw == canonical)
    taxonomy_match_method := 'exact'      -- raw now literally equals canonical

    WHERE discipline <> 'emerging'
      AND (discipline_raw IS NULL OR TRIM(discipline_raw) = '')

NOTES:
  * discipline_raw is SINGULAR (schema: "LLM original, preserved (singular)"),
    so we copy the singular canonical string, not a JSON array.
  * Setting 'exact' is truthful post-copy (raw == canonical). It also normalises
    the 69 undocumented 'alias' values on these rows into a documented enum member
    ('exact'). Track B provenance for those rows remains in temp/trackb_full.jsonl.
  * Rows already carrying a non-empty discipline_raw are UNTOUCHED (WHERE guard).

Safety (C6/C13):
  * MUTATION IS OPT-IN via `--apply`; default is read-only `--manifest`.
  * `--apply`: PRAGMA quick_check + foreign_key_check gate -> shutil.copy2 backup
    (fsync) -> single-transaction UPDATE -> post-verify recount.

Run:
    python3 scripts/fix_bug311_discipline_raw.py --manifest
    python3 scripts/fix_bug311_discipline_raw.py --apply
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402


def _fsync_copy(src: Path, dst: Path) -> None:
    """C6 crash-safe copy: copy then fsync the file + directory entry."""
    shutil.copy2(src, dst)
    with open(dst, "rb") as f:
        os.fsync(f.fileno())
    dfd = os.open(str(dst.parent), os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def _targets(con: sqlite3.Connection) -> list[tuple[str, str, str]]:
    """(fb_id, name, discipline) for the empty-raw resolved rows."""
    cur = con.cursor()
    cur.execute(
        "SELECT fb_id, name, discipline FROM fbs "
        "WHERE discipline <> 'emerging' "
        "AND (discipline_raw IS NULL OR TRIM(discipline_raw) = '') "
        "ORDER BY rowid"
    )
    return cur.fetchall()


def _count(con: sqlite3.Connection) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM fbs WHERE discipline <> 'emerging' "
        "AND (discipline_raw IS NULL OR TRIM(discipline_raw) = '')"
    ).fetchone()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="T-311: copy discipline -> discipline_raw (empty-raw repair)")
    ap.add_argument("--manifest", action="store_true", help="list targets (read-only)")
    ap.add_argument("--apply", action="store_true", help="backup + gate + transactional repair")
    args = ap.parse_args()

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    targets = _targets(con)

    print(f"📋 T-311 targets: {len(targets)} empty discipline_raw rows with resolved discipline")

    if args.manifest or not args.apply:
        con.close()
        for fid, name, disc in targets[:20]:
            print(f"  {fid[:12]}  {name[:38]:38}  → {disc}")
        if len(targets) > 20:
            print(f"  … and {len(targets) - 20} more")
        print(f"\nRun --apply to write ({len(targets)} rows).")
        return 0

    if not targets:
        con.close()
        print("✅ nothing to repair (idempotent)")
        return 0

    # Gate 1: structural integrity before write.
    qk = con.execute("PRAGMA quick_check").fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if qk != "ok" or fk:
        con.close()
        print(f"❌ integrity gate failed: quick_check={qk!r} fk_issues={len(fk)}")
        return 1

    # C13: backup before batch write (fsync).
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.with_name(DB_PATH.name + f".bak_t311_{ts}")
    con.close()
    _fsync_copy(DB_PATH, backup)
    print(f"💾 backed up {DB_PATH.name} -> {backup.name}")

    # Single transaction: all-or-nothing.
    con = sqlite3.connect(str(DB_PATH))
    try:
        con.execute("BEGIN IMMEDIATE")
        n = 0
        for fid, name, disc in targets:
            con.execute(
                "UPDATE fbs SET discipline_raw = ?, taxonomy_match_method = 'exact' "
                "WHERE fb_id = ? AND discipline <> 'emerging' "
                "AND (discipline_raw IS NULL OR TRIM(discipline_raw) = '')",
                (disc, fid),
            )
            n += 1
        con.commit()
    except Exception as e:  # noqa: BLE001 — C16: log AND raise
        con.rollback()
        con.close()
        print(f"❌ transaction failed, rolled back: {e}")
        raise

    remaining = _count(con)
    con.close()
    print(f"✅ T-311 applied: {n} rows repaired (discipline_raw := discipline, method := 'exact')")
    print(f"   remaining empty discipline_raw (resolved): {remaining}")
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
