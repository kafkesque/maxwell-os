#!/usr/bin/env python3
"""scripts/apply_relabel_plan.py — Phase 1: apply the 8 human-review relabel actions.

Reads the 8 confirmed actions from the enrichment review (1 enrich + 4 retarget +
3 deregister), looks up each FB by name, and updates ONLY the `domains` (canonical
JSON array) column — `domains_raw` is left untouched (raw provenance). Follows the
reclassify_merged_axis.py write pattern: C13 pre-write backup + integrity gate +
single atomic transaction.

Usage:
  python3 scripts/apply_relabel_plan.py              # dry-run (default): show before→after
  python3 scripts/apply_relabel_plan.py --apply      # backup + integrity + atomic write
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

# name -> (remove_domains, add_domains). Empty remove = enrich (pure add).
_ACTIONS: list[tuple[str, list[str], list[str]]] = [
    ("Color As Cultural and Emotional Marker", [], ["social sciences"]),
    ("Structural Theory Foundation", ["business operations"], ["design strategy"]),
    ("Community Mapping Project Coordination Challenges", ["legal & public policy"], ["project management"]),
    ("Figma Ai Development Tools", ["project management", "user experience"], ["web & ui"]),
    ("Figma Hamburger Icon Creation", ["user experience"], ["web & ui"]),
    ("Visual Builder Layer for Agentic Ai", ["project management"], []),
    ("Apple Design Philosophy", ["business operations", "project management"], []),
    ("Toxic Material Embedding in Electronics", ["legal & public policy", "project management"], []),
]


def _parse_domains(raw: str | None) -> list[str]:
    if not raw:
        return []
    s = raw.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return [x.strip() for x in s.split("|") if x.strip()]


def _lookup(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    row = conn.execute("SELECT fb_id, name, domains FROM fbs WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row
    # fallback: LIKE (handles plan-name vs DB-name minor drift)
    return conn.execute(
        "SELECT fb_id, name, domains FROM fbs WHERE name LIKE ? ORDER BY fb_id LIMIT 1",
        ("%" + name[:40] + "%",),
    ).fetchone()


def _backup_db(db_path: Path) -> Path:
    """C13: timestamped pre-write DB backup, fsync'd + size-verified (C6)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_relabel")
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


def _compute_updates(conn: sqlite3.Connection) -> list[dict]:
    updates: list[dict] = []
    for name, remove, add in _ACTIONS:
        row = _lookup(conn, name)
        if row is None:
            print(f"  ⚠️  NOT FOUND: {name}", file=sys.stderr)
            continue
        cur = _parse_domains(row["domains"])
        new = [d for d in cur if d not in remove]
        for d in add:
            if d not in new:
                new.append(d)
        updates.append({
            "fb_id": row["fb_id"],
            "name": row["name"],
            "old": cur,
            "new": sorted(new),
            "remove": remove,
            "add": add,
        })
    return updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 relabel apply (8 FBs).")
    parser.add_argument("--apply", action="store_true", help="Write (default = dry-run).")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    updates = _compute_updates(conn)
    conn.close()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} FB(s)\n")
    for u in updates:
        arrow = "→" if u["old"] != u["new"] else "="
        print(f"  {u['name'][:48]:48s} {arrow} {u['new']}")
        if u["remove"] or u["add"]:
            print(f"      (removed: {u['remove'] or '—'} | added: {u['add'] or '—'})")

    if not args.apply:
        print("\n  (dry-run — no write. Re-run with --apply to commit.)")
        return 0

    # C13 + C6: backup + integrity gate, then atomic write
    _backup_db(DB_PATH)
    _integrity_gate(DB_PATH)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute(
                "UPDATE fbs SET domains=? WHERE fb_id=?",
                (json.dumps(u["new"]), u["fb_id"]),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()

    print(f"\n✅ committed {len(updates)} FB domain update(s) atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
