#!/usr/bin/env python3
"""apply_dedup_marks.py — mark duplicate_of + QUARANTINE (NEVER delete).

D2627/D2625: after the mechanism-aware judge (judge_suffix_duplicates.py) confirms
which "(N)"-suffix pairs are TRUE duplicates, this script applies the dedup policy:
  - adds the `duplicate_of` column to fbs (safe migration, matches stage6_commit)
  - sets `duplicate_of = canonical_fb_id` on each confirmed duplicate row
  - sets `status = 'QUARANTINE'` (separate from main PASS checkpoints — query.py,
    stage6b_anytype_push.py, principle_index.py all filter status='PASS')
  - NEVER deletes a row (R-D410 safe_delete is the only destructive path, NOT used)

Reads the duplicate_of map from governance/dedup_final_apply_plan.json (the
CONSOLIDATED map = locked user-confirmed plan ∪ judge-confirmed new duplicates).
Dry-run by default; --apply requires a C13 pre-write backup + integrity gate.

Usage:
    python3 scripts/apply_dedup_marks.py              # dry-run: report what WOULD change
    python3 scripts/apply_dedup_marks.py --apply      # backup + migrate + atomic mark
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PLAN = ROOT / "governance" / "dedup_final_apply_plan.json"
DB = ROOT / "knowledge pipeline" / "maxwell.db"


def _load_duplicate_of() -> Dict[str, str]:
    d = json.loads(PLAN.read_text())
    return d.get("duplicate_of", {})


def _load_rows(ids: List[str]) -> Dict[str, Dict[str, Any]]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        ph = ",".join("?" * len(ids))
        # `duplicate_of` may not exist yet (pre-migration); tolerate its absence.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
        dup_col = "duplicate_of" if "duplicate_of" in cols else "NULL AS duplicate_of"
        rows = conn.execute(
            f"SELECT fb_id, name, status, content_type, {dup_col} FROM fbs WHERE fb_id IN ({ph})",
            ids,
        ).fetchall()
    finally:
        conn.close()
    return {r["fb_id"]: dict(r) for r in rows}


def _migrate_column(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("ALTER TABLE fbs ADD COLUMN duplicate_of TEXT")
    except sqlite3.OperationalError:
        pass  # already exists


def run(apply: bool) -> None:
    dup_of = _load_duplicate_of()
    print(f"duplicate_of entries from judge: {len(dup_of)}")

    all_ids = list(dup_of.keys()) + list(dup_of.values())
    rows = _load_rows(all_ids)
    print(f"rows found in DB: {len(rows)} / {len(set(all_ids))}")

    changes: List[tuple[str, str, str, str]] = []  # (dup_fb_id, canonical, current_status, name)
    for dup_id, canon in dup_of.items():
        r = rows.get(dup_id)
        if r is None:
            print(f"  [skip] dup fb_id not in DB: {dup_id[:16]}")
            continue
        canon_r = rows.get(canon)
        if canon_r is None:
            print(f"  [skip] canonical fb_id not in DB: {canon[:16]} (dup {r['name'][:30]})")
            continue
        already = r.get("duplicate_of") == canon and r.get("status") == "QUARANTINE"
        changes.append((dup_id, canon, r["status"], r["name"], already))

    to_mark = [c for c in changes if not c[4]]
    print(f"\nrows to mark duplicate_of + QUARANTINE: {len(to_mark)} / {len(changes)}")
    for dup_id, canon, cur_status, name, already in changes:
        mark = "already-marked" if already else "MARK"
        print(f"  [{mark}] {name[:42]:44} status={cur_status} -> QUARANTINE, duplicate_of={canon[:16]}")

    if not apply:
        print("\n[dry-run] nothing written. Re-run with --apply.")
        return

    if not to_mark:
        print("\nnothing to apply.")
        return

    # C13: pre-write backup
    bak = DB.with_name(f"maxwell.db.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_pre_dedup")
    shutil.copy2(DB, bak)
    print(f"\n[C13] backup: {bak}")

    conn = sqlite3.connect(DB)
    try:
        # integrity gate (fail-closed)
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        if qc != "ok":
            raise RuntimeError(f"PRAGMA quick_check failed: {qc!r} — refusing to write")
        _migrate_column(conn)
        for dup_id, canon, cur_status, name, already in to_mark:
            conn.execute(
                "UPDATE fbs SET duplicate_of=?, status='QUARANTINE' WHERE fb_id=?",
                (canon, dup_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"\n[done] marked {len(to_mark)} rows duplicate_of + QUARANTINE (never deleted)")

    # verify
    rows2 = _load_rows(list(dup_of.keys()))
    marked = sum(1 for r in rows2.values() if r.get("duplicate_of") and r.get("status") == "QUARANTINE")
    print(f"verification: {marked}/{len(rows2)} dup rows now QUARANTINE with duplicate_of set")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Mark confirmed dedup rows duplicate_of + QUARANTINE (never delete).")
    ap.add_argument("--apply", action="store_true", help="write marks (C13 backup + integrity gate)")
    args = ap.parse_args()
    run(apply=args.apply)
