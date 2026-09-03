#!/usr/bin/env python3
"""
scripts/rederive_demoted_fbs.py — Drift C data re-derivation (D2512).
=====================================================================
After the config demotion (scripts/demote_disciplines_to_domains.py moves 9
applied-practice labels discipline→domain), the 851 committed FBs whose
`discipline` was one of those labels now carry a NON-canonical discipline.

This script deterministically (LLM-free, idempotent) fixes each:
  1. `discipline` → 'emerging'  (their discipline_raw were aliases of the demoted
     labels, so they no longer resolve to any remaining discipline — verified 0/851
     recoverable before this script).
  2. `domains`   → adds the new domain canonical:
        marketing            → 'marketing & communications'  (merged)
        <other 8 demoted>    → its own name (now a domain canonical)

Also updates taxonomy_counts via the SAME code path as S6 post-commit
(reconcile_canonical_status + update_counts_from_fbs) so D2399 sees correct counts.

Crash-safe (C6): backs up the SQLite DB before the first write, then updates in
a single transaction. Idempotent: re-running finds 0 FBs to fix.

Usage:
    /opt/homebrew/bin/python3 scripts/rederive_demoted_fbs.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH

DEMOTE = [
    "marketing", "product design", "design strategy", "project management",
    "leadership", "personal productivity", "industrial design",
    "information architecture", "design systems",
]
# mapping from old discipline → new domain canonical
DISCIPLINE_TO_DOMAIN = {
    "marketing": "marketing & communications",
}
# the other 8 map to themselves (their canonical name is now a domain)


def _to_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return [value]
    return list(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-derive FBs whose discipline was demoted (D2512)")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = args.db
    if not db.exists():
        print(f"  ❌ DB not found: {db}")
        return 1

    # Build the WHERE clause for the 9 demoted disciplines (case-insensitive)
    placeholders = ",".join("?" for _ in DEMOTE)
    sql = f"SELECT rowid, discipline, domains FROM fbs WHERE lower(discipline) IN ({placeholders})"
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, DEMOTE).fetchall()
    print(f"  📊 {len(rows)} FBs to re-derive (discipline ∈ demoted set)")

    if args.dry_run:
        by_disc: dict[str, int] = {}
        for r in rows:
            by_disc[r["discipline"]] = by_disc.get(r["discipline"], 0) + 1
        for k in sorted(by_disc, key=lambda x: -by_disc[x]):
            print(f"    {k}: {by_disc[k]}")
        conn.close()
        print("  🔍 --dry-run: no writes")
        return 0

    if not rows:
        conn.close()
        print("  ✅ nothing to re-derive (idempotent)")
        return 0

    # Backup DB before write (C6)
    backup = db.with_suffix(db.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(db, backup)
    print(f"  💾 DB backed up → {backup.name}")

    updated = 0
    for r in rows:
        discipline = (r["discipline"] or "").lower().strip()
        new_domain = DISCIPLINE_TO_DOMAIN.get(discipline, discipline)
        domains = _to_list(r["domains"])
        # add new domain canonical (dedupe, preserve order)
        if new_domain not in domains:
            domains.append(new_domain)
        conn.execute(
            "UPDATE fbs SET discipline = 'emerging', domains = ? WHERE rowid = ?",
            (json.dumps(domains), r["rowid"]),
        )
        updated += 1

    conn.commit()

    # Reconcile + recount taxonomy_counts (same path as S6 post-commit, D2512)
    from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
    reconcile_canonical_status(conn)
    changes = update_counts_from_fbs(conn)

    conn.close()
    print(f"  ✅ {updated} FBs re-derived (discipline→emerging + domain added)")
    print(f"  ✅ taxonomy_counts reconciled + recounted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
