#!/usr/bin/env python3
"""scripts/apply_d2399_ecology_promotion.py — D2573 (D2399 closed-loop replacement).

Deterministic, LLM-free application of the USER-APPROVED D2378 closed-loop
replacement (option 1 of `governance/d2399_manual_review.md` §Ecology):

    promote  emerging discipline "ecology"        (5 FBs)  → canonical
    displace weakest canonical "computer networking" (4 FBs) → displaced

This mirrors `scripts/apply_d2399_organizational_theory.py` (D2516) exactly — the
D2378 closed-loop keeps discipline cardinality at 61 (promotion requires demotion).
The YAML (`config/taxonomy_v5.yaml`) is ALREADY updated (ecology added as canonical,
computer networking moved to `meta.displaced_canonicals`); this script applies the
corresponding DB mutation.

Steps (all idempotent / crash-safe):
  1. Back up the DB (C13).
  2. Re-resolve FB discipline slots (deterministic string match):
       - discipline='emerging' + lower(discipline_raw)='ecology'  -> 'ecology'
       - discipline='computer networking'                          -> 'emerging' (raw preserved)
  3. reconcile_canonical_status(): YAML truth wins → ecology becomes canonical,
     computer networking demoted (no longer a YAML canonical).
  4. Mark computer networking 'displaced' (D2399 semantics — never re-enters the
     challenger pool; distinct from 'emerging').
  5. update_counts_from_fbs(): full idempotent recount (Drift-F safe).
  6. Verify and report.

Run:
    python3 scripts/apply_d2399_ecology_promotion.py --dry-run
    python3 scripts/apply_d2399_ecology_promotion.py
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
from pipeline.taxonomy_manager import (  # noqa: E402
    reconcile_canonical_status,
    update_counts_from_fbs,
)

_PROMOTE_RAW = "ecology"          # emerging raw label → new canonical
_PROMOTE_TARGET = "ecology"       # canonical name
_DEMOTE_CANONICAL = "computer networking"  # displaced canonical

UTC = timezone.utc


def _backup_db(db_path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.bak_{stamp}_pre_ecology")
    shutil.copy2(db_path, backup)
    return backup


def _preview(conn: sqlite3.Connection) -> tuple[int, int]:
    promote_n = conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE discipline = 'emerging' AND lower(trim(discipline_raw)) = ?",
        (_PROMOTE_RAW,),
    ).fetchone()[0]
    demote_n = conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE lower(trim(discipline)) = ?",
        (_DEMOTE_CANONICAL,),
    ).fetchone()[0]
    return promote_n, demote_n


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

    promote_n, demote_n = _preview(conn)
    print(f"promote: {promote_n} FBs → '{_PROMOTE_TARGET}'")
    print(f"demote:  {demote_n} FBs '{_DEMOTE_CANONICAL}' → 'emerging' (raw preserved)")

    if args.dry_run:
        conn.close()
        print("\n(dry-run — no write.)")
        return 0

    backup = _backup_db(args.db)
    print(f"\n💾 DB backed up → {backup.name}")

    # 2. Re-resolve FB discipline slots (deterministic)
    cur = conn.execute(
        "UPDATE fbs SET discipline = ? "
        "WHERE discipline = 'emerging' AND lower(trim(discipline_raw)) = ?",
        (_PROMOTE_TARGET, _PROMOTE_RAW),
    )
    promoted = cur.rowcount
    cur = conn.execute(
        "UPDATE fbs SET discipline = 'emerging' WHERE lower(trim(discipline)) = ?",
        (_DEMOTE_CANONICAL,),
    )
    demoted = cur.rowcount
    print(f"FB re-resolution: +{promoted} → '{_PROMOTE_TARGET}', "
          f"{demoted} '{_DEMOTE_CANONICAL}' → 'emerging'")

    # 3. Reconcile canonical status from YAML (ecology canonical, computer networking demoted)
    reconciled = reconcile_canonical_status(conn)
    print(f"reconcile_canonical_status: {reconciled} row(s) adjusted")

    # 4. Mark displaced (D2399 semantics)
    conn.execute(
        "UPDATE taxonomy_counts SET status = 'displaced', last_updated = ? "
        "WHERE label = ? AND label_type = 'discipline'",
        (datetime.now(UTC).isoformat(), _DEMOTE_CANONICAL),
    )

    # 5. Full idempotent recount
    changes = update_counts_from_fbs(conn)
    conn.commit()
    print(f"recount flood_warning={changes.get('flood_warning', False)}")

    # 6. Verify
    print("\n=== Post-approval taxonomy_counts (relevant) ===")
    for r in conn.execute(
        "SELECT label, count, status FROM taxonomy_counts "
        "WHERE label IN (?, ?, 'evolutionary biology') AND label_type = 'discipline' ORDER BY label",
        (_PROMOTE_TARGET, _DEMOTE_CANONICAL),
    ):
        print(f"  {r['status']:12} {r['count']:>4}  {r['label']}")

    n_canon = conn.execute(
        "SELECT COUNT(*) FROM taxonomy_counts WHERE label_type = 'discipline' AND status = 'canonical'"
    ).fetchone()[0]
    print(f"\n✅ D2399 ecology promotion applied. canonical disciplines = {n_canon} (expect 61).")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
