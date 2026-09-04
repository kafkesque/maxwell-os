#!/usr/bin/env python3
"""scripts/correct_wrong_enrichments.py — D2566 targeted correction of wrong additions.

The Phase 2b enrichment ran BEFORE 8 LLM aliases were corrected, so ~20 FBs carry
a wrong canonical domain (added by a now-fixed alias). This script REPLACES the
wrong domain with the correct one, gated on the raw label still being present
(idempotent + safe). Only the `domains` canonical array is touched; `domains_raw`
and every other field are untouched.

Corrections (raw label -> wrong target -> correct target):
    scientific research      -> computational science & physics -> science & research
    scientific methodology   -> computational science & physics -> research & methodology
    data science & analytics -> research & methodology           -> data visualization
    statistics & data science-> research & methodology           -> data visualization

Safety (C13/C6): default DRY-RUN; --apply requires backup + integrity + atomic txn.

Usage:
  python3 scripts/correct_wrong_enrichments.py          # dry-run
  python3 scripts/correct_wrong_enrichments.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

# (raw_label_lower, wrong_target, correct_target)
_CORRECTIONS: list[tuple[str, str, str]] = [
    ("scientific research", "computational science & physics", "science & research"),
    ("scientific methodology", "computational science & physics", "research & methodology"),
    ("data science & analytics", "research & methodology", "data visualization"),
    ("statistics & data science", "research & methodology", "data visualization"),
]


def _parse(v: str | None) -> list[str]:
    if not v:
        return []
    s = v.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return [x.strip() for x in s.split("|") if x.strip()]


def _backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_enrich_correct")
    shutil.copy2(str(db_path), str(bak))
    with open(bak, "rb") as f:
        os.fsync(f.fileno())
    if db_path.stat().st_size != bak.stat().st_size:
        raise RuntimeError("backup size mismatch — aborting write")
    print(f"  🔒 Backup: {bak} ({bak.stat().st_size:,} bytes)")
    return bak


def _integrity_gate(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if qc != "ok":
        raise RuntimeError(f"integrity gate FAILED (quick_check={qc})")
    if fk:
        raise RuntimeError(f"integrity gate FAILED ({len(fk)} FK violations)")


def _compute(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT fb_id, name, domains, domains_raw FROM fbs").fetchall()
    out: list[dict] = []
    for r in rows:
        d = _parse(r["domains"])
        dr_lower = {x.lower() for x in _parse(r["domains_raw"])}
        for raw, wrong, correct in _CORRECTIONS:
            if raw in dr_lower and wrong in d and correct not in d:
                new = [correct if x == wrong else x for x in d]
                out.append({"fb_id": r["fb_id"], "name": r["name"],
                            "old": d, "new": new, "fix": f"{wrong} -> {correct}"})
                break  # one correction per FB
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="targeted enrichment correction (D2566).")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    updates = _compute(conn)
    conn.close()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} FB(s) to correct\n")
    for u in updates:
        print(f"  {u['name'][:44]:44s} {u['fix']}")
    if not args.apply:
        print("\n  (dry-run — no write. Re-run with --apply to commit.)")
        return 0

    _backup_db(DB_PATH)
    _integrity_gate(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute("UPDATE fbs SET domains=? WHERE fb_id=?",
                         (json.dumps(u["new"]), u["fb_id"]))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    print(f"\n✅ committed {len(updates)} correction(s) atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
