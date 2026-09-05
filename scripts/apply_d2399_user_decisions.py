#!/usr/bin/env python3
"""scripts/apply_d2399_user_decisions.py — D2572 (D2399 user-adjudicated actions).

Applies the HUMAN-APPROVED D2399 decisions recorded in
`governance/d2399_manual_review.md` (2026-09-05). Deterministic, LLM-free, surgical:

  A (map → discipline): 6 alias targets — 12 FBs re-resolved.
     history of philosophy   → philosophy
     financial engineering   → finance          (dual-axis: also a domain alias)
     Medical Humanities      → health & medicine
     Experimental Psychology → psychology
     Educational Measurement → research methodology
     Design Studies          → design thinking  (dual-axis: also in 'design strategy' raw[])
  B (kind-swap): 'Marketing' is a DOMAIN label (→ marketing & communications) sitting
     in the discipline slot. 4 FBs: clear discipline_raw, ensure the domain is set,
     leave discipline = 'emerging' (BUG-197 Direction B).

NOT touched here (per user's D decisions and the closed-loop):
  - Ecology (C): promotion requires demoting the weakest canonical (D2378 closed-loop,
    cardinality 61). Awaiting explicit demotion choice — see the manual-review doc §Ecology.
  - All other D labels and the 233 singletons.

Crash-safe (C6/C13): DB backed up before write; single transaction; idempotent full
recount via reconcile_canonical_status() + update_counts_from_fbs().

Run:
    python3 scripts/apply_d2399_user_decisions.py --dry-run   # preview only
    python3 scripts/apply_d2399_user_decisions.py             # apply (backup + write)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.taxonomy_manager import (  # noqa: E402
    reconcile_canonical_status,
    update_counts_from_fbs,
)

# A: raw label (case-insensitive) -> canonical discipline target.
_DISCIPLINE_MAPS: dict[str, str] = {
    "history of philosophy": "philosophy",
    "financial engineering": "finance",
    "Medical Humanities": "health & medicine",
    "Experimental Psychology": "psychology",
    "Educational Measurement": "research methodology",
    "Design Studies": "design thinking",
}

# B: raw label -> canonical domain target (kind-swap).
_KIND_SWAP: dict[str, str] = {
    "Marketing": "marketing & communications",
}

UTC = timezone.utc


def _backup_db(db_path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.bak_{stamp}_pre_d2399")
    shutil.copy2(db_path, backup)
    return backup


def _compute(conn: sqlite3.Connection) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (discipline_updates, kindswap_updates) as (fb_id, new_discipline) tuples."""
    discipline_updates: list[tuple[str, str]] = []
    for raw, target in _DISCIPLINE_MAPS.items():
        rows = conn.execute(
            "SELECT fb_id FROM fbs "
            "WHERE discipline = 'emerging' AND lower(trim(discipline_raw)) = lower(?)",
            (raw,),
        ).fetchall()
        for (fb_id,) in rows:
            discipline_updates.append((fb_id, target))

    kindswap_updates: list[tuple[str, str]] = []
    for raw, domain in _KIND_SWAP.items():
        rows = conn.execute(
            "SELECT fb_id, domains FROM fbs "
            "WHERE discipline = 'emerging' AND lower(trim(discipline_raw)) = lower(?)",
            (raw,),
        ).fetchall()
        for (fb_id, domains) in rows:
            kindswap_updates.append((fb_id, domain))
    return discipline_updates, kindswap_updates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"❌ DB not found: {args.db}")
        return 1

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row

    discipline_updates, kindswap_updates = _compute(conn)

    print(f"A (map → discipline): {len(discipline_updates)} FBs")
    for fb_id, target in sorted(discipline_updates, key=lambda t: t[1]):
        print(f"    {fb_id[:12]} -> {target}")
    print(f"B (kind-swap → domain): {len(kindswap_updates)} FBs")
    for fb_id, domain in kindswap_updates:
        print(f"    {fb_id[:12]} -> {domain} (clear discipline_raw)")

    if args.dry_run:
        conn.close()
        print("\n(dry-run — no write. Re-run with --apply.)")
        return 0

    if not discipline_updates and not kindswap_updates:
        conn.close()
        print("✅ nothing to apply (idempotent)")
        return 0

    backup = _backup_db(args.db)
    print(f"\n💾 DB backed up → {backup.name}")

    # A: re-resolve discipline slots (deterministic, case-insensitive)
    for fb_id, target in discipline_updates:
        conn.execute("UPDATE fbs SET discipline = ? WHERE fb_id = ?", (target, fb_id))

    # B: kind-swap — clear discipline_raw, ensure domain is present
    for fb_id, domain in kindswap_updates:
        conn.execute("UPDATE fbs SET discipline_raw = '' WHERE fb_id = ?", (fb_id,))
        row = conn.execute("SELECT domains FROM fbs WHERE fb_id = ?", (fb_id,)).fetchone()
        domains = json.loads(row["domains"]) if row and row["domains"] else []
        if not domains or domains == ["emerging"]:
            domains = [domain]
        elif domain not in domains:
            domains.append(domain)
        conn.execute("UPDATE fbs SET domains = ? WHERE fb_id = ?", (json.dumps(domains), fb_id))

    conn.commit()

    # Idempotent full recount (row_factory already set, required by taxonomy_manager)
    reconciled = reconcile_canonical_status(conn)
    counts = update_counts_from_fbs(conn)
    conn.commit()
    conn.close()

    print(f"✅ applied {len(discipline_updates)} discipline maps + {len(kindswap_updates)} kind-swaps")
    print(f"   reconcile: {reconciled} row(s) adjusted; flood_warning={counts.get('flood_warning', False)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
