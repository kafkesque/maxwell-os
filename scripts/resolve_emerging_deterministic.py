#!/usr/bin/env python3
"""scripts/resolve_emerging_deterministic.py — D2566 deterministic emerging resolution.

Resolves ``discipline = 'emerging'`` FBs whose ``discipline_raw`` ALREADY maps to a
canonical discipline through the synonym index (taxonomy_v5 raw + synonym_map +
alias_map discipline_aliases). No LLM — this is the zero-cost, zero-risk first pass
of Track B; the LLM re-classifier (reclassify_merged_axis.py) only needs to see the
remaining genuinely-unmapped/empty-raw rows afterward.

Kind-safety (D2133): a raw label that maps to a canonical DOMAIN is NOT resolved here
(it belongs to the domain axis and is handled by bug197_kind_swap.py). Only a raw
label resolving to a canonical DISCIPLINE is lifted.

Safety (C13/C6/C12): default DRY-RUN; ``--apply`` requires a timestamped DB backup +
integrity gate and commits in a single atomic transaction.

Usage:
  python3 scripts/resolve_emerging_deterministic.py          # dry-run
  python3 scripts/resolve_emerging_deterministic.py --apply  # backup + integrity + write
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
from pipeline.schemas import match_to_canonical  # noqa: E402


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
    bak = Path(str(db_path) + f".bak_{ts}_pre_emerging_resolve")
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
    rows = conn.execute(
        "SELECT fb_id, name, discipline, discipline_raw FROM fbs WHERE discipline='emerging'"
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        disc = None
        for raw in _parse(r["discipline_raw"]):
            m = match_to_canonical(raw, "discipline")
            if m and m != "emerging":
                disc = m
                break
        if disc:
            out.append({
                "fb_id": r["fb_id"], "name": r["name"],
                "old": r["discipline"], "new": disc, "raw": r["discipline_raw"],
            })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="deterministic emerging resolution (D2566).")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    updates = _compute(conn)
    conn.close()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} emerging FB(s) deterministically resolvable\n")
    for u in updates[:40]:
        print(f"  {u['name'][:44]:44s} emerging -> {u['new']}  (raw={u['raw'][:40]!r})")
    if len(updates) > 40:
        print(f"  … and {len(updates) - 40} more")

    if not args.apply:
        print("\n  (dry-run — no write. Re-run with --apply to commit.)")
        return 0

    _backup_db(DB_PATH)
    _integrity_gate(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute("UPDATE fbs SET discipline=?, taxonomy_match_method='synonym' WHERE fb_id=?",
                         (u["new"], u["fb_id"]))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    print(f"\n✅ committed {len(updates)} deterministic emerging resolutions atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
