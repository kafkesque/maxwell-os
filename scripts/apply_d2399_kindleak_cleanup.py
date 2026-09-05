#!/usr/bin/env python3
"""scripts/apply_d2399_kindleak_cleanup.py — D2574 (D2399 kind-leak cleanup).

Deterministic, LLM-free cleanup of the 33 remaining KIND-LEAK FBs: FBs where
`discipline = 'emerging'` and a non-empty `discipline_raw` resolves to a DOMAIN
canonical only (a domain label that leaked into the discipline slot — BUG-197,
Direction B). For each such FB the domain is ALREADY present in `domains` and the
raw label already in `domains_raw` (verified 33/33), so the only mutation is:

    discipline_raw := ''      (clear the mis-placed domain label; keep discipline='emerging')

This is the honest "open-world" state for a domain-only FB: `emerging` discipline
with no discipline raw, while the domain axis carries the real classification.

Scope is strictly the 33 kind-leaks (NOT the opposite Direction A leaks). Ecology
promotion (D2573) already moved those 5 FBs out of this population.

Crash-safe (C6/C13): DB backed up before write; single transaction; idempotent
recount via reconcile_canonical_status() + update_counts_from_fbs().

Run:
    python3 scripts/apply_d2399_kindleak_cleanup.py --dry-run
    python3 scripts/apply_d2399_kindleak_cleanup.py
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import match_to_canonical  # noqa: E402
from pipeline.taxonomy_manager import (  # noqa: E402
    reconcile_canonical_status,
    update_counts_from_fbs,
)

UTC = timezone.utc


def _backup_db(db_path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.bak_{stamp}_pre_kindleak")
    shutil.copy2(db_path, backup)
    return backup


def _find_kindleaks(conn: sqlite3.Connection) -> list[str]:
    """Return fb_ids of kind-leak FBs (emerging + non-empty raw → domain-only)."""
    rows = conn.execute(
        "SELECT fb_id, discipline_raw FROM fbs "
        "WHERE discipline = 'emerging' AND discipline_raw IS NOT NULL "
        "AND TRIM(discipline_raw) <> '' AND discipline_raw <> '[]'"
    ).fetchall()
    out: list[str] = []
    for r in rows:
        dom = match_to_canonical(r["discipline_raw"], "domain")
        disc = match_to_canonical(r["discipline_raw"], "discipline")
        if dom is not None and disc is None:
            out.append(r["fb_id"])
    return out


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

    fb_ids = _find_kindleaks(conn)
    print(f"kind-leak FBs to clean (clear discipline_raw): {len(fb_ids)}")

    if args.dry_run:
        conn.close()
        print("\n(dry-run — no write.)")
        return 0

    if not fb_ids:
        conn.close()
        print("✅ nothing to clean (idempotent)")
        return 0

    backup = _backup_db(args.db)
    print(f"\n💾 DB backed up → {backup.name}")

    for fb_id in fb_ids:
        conn.execute("UPDATE fbs SET discipline_raw = '' WHERE fb_id = ?", (fb_id,))
    conn.commit()

    reconcile_canonical_status(conn)
    update_counts_from_fbs(conn)
    conn.commit()

    remaining = conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE discipline = 'emerging' "
        "AND discipline_raw IS NOT NULL AND TRIM(discipline_raw) <> '' AND discipline_raw <> '[]'"
    ).fetchone()[0]
    conn.close()

    print(f"✅ cleared {len(fb_ids)} kind-leak discipline_raw slots")
    print(f"   remaining gap population (emerging + non-empty raw): {remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
