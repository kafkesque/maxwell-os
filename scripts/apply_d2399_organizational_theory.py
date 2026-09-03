#!/usr/bin/env python3
"""
apply_d2399_organizational_theory.py — D2516

Deterministic, LLM-free application of the human-approved D2399 candidate 2:
promote emerging discipline "organizational theory" (19) to canonical, and
displace the weakest canonical discipline "social engineering" (1) — the
D2378 closed-loop (promotion requires demotion, cardinality stays 61).

Also re-resolves the affected committed FBs (no LLM reclassification):
  - 19 FBs with discipline='emerging', discipline_raw='organizational theory'
        -> discipline='organizational theory'
  - 1 FB  with discipline='social engineering' (raw 'intelligence analysis')
        -> discipline='emerging'  (raw label is preserved as long-tail)

Steps (all idempotent / crash-safe):
  1. Back up the DB (C13).
  2. Re-resolve FB discipline slots (deterministic string match).
  3. reconcile_canonical_status(): YAML truth wins -> organizational theory
     becomes canonical, social engineering demoted.
  4. Mark social engineering 'displaced' (D2399 semantics, distinct from
     'emerging' so it never re-enters the challenger pool).
  5. update_counts_from_fbs(): full idempotent recount (Drift-F safe).
  6. Verify and report the post-approval challenger pool.

Run: /usr/local/bin/python3 scripts/apply_d2399_organizational_theory.py
"""
from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pipeline.taxonomy_manager import (
    check_for_replacements,
    reconcile_canonical_status,
    update_counts_from_fbs,
)
from pipeline.pipeline_paths import DB_PATH

UTC = timezone.utc


def _backup_db(db_path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup = db_path.with_name(f"{db_path.name}.bak_{stamp}")
    shutil.copy2(db_path, backup)
    return backup


def main() -> None:
    db_path = Path(DB_PATH)
    backup = _backup_db(db_path)
    print(f"✅ DB backed up -> {backup}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # ── 2. Re-resolve FB discipline slots ──
    cur = conn.execute(
        "UPDATE fbs SET discipline = 'organizational theory' "
        "WHERE discipline = 'emerging' AND lower(trim(discipline_raw)) = 'organizational theory'"
    )
    promoted_n = cur.rowcount
    cur = conn.execute(
        "UPDATE fbs SET discipline = 'emerging' "
        "WHERE lower(trim(discipline)) = 'social engineering'"
    )
    displaced_n = cur.rowcount
    print(f"FB re-resolution: +{promoted_n} discipline->organizational theory, "
          f"{displaced_n} discipline social engineering -> emerging")

    # ── 3. Reconcile canonical status from YAML ──
    reconciled = reconcile_canonical_status(conn)
    print(f"reconcile_canonical_status: {reconciled} row(s) adjusted")

    # ── 4. Mark social engineering displaced (D2399 semantics) ──
    conn.execute(
        "UPDATE taxonomy_counts SET status = 'displaced', last_updated = ? "
        "WHERE label = 'social engineering' AND label_type = 'discipline'",
        (datetime.now(UTC).isoformat(),),
    )

    # ── 5. Full idempotent recount ──
    changes = update_counts_from_fbs(conn)
    conn.commit()
    print(f"recount flood_warning={changes.get('flood_warning', False)}")

    # ── 6. Verify ──
    print("\n=== Post-approval taxonomy_counts (relevant) ===")
    for r in conn.execute(
        "SELECT label, count, status FROM taxonomy_counts "
        "WHERE label IN ('organizational theory','social engineering','human factors engineering') "
        "AND label_type='discipline' ORDER BY label"
    ):
        print(f"  {r[2]:10} {r[1]:>4}  {r[0]}")

    print("\n=== Remaining D2399 candidates ===")
    cands = check_for_replacements(conn)
    if not cands:
        print("  (none)")
    for c in cands:
        print(f"  [{c['label_type']}] {c['emerging_label']} ({c['emerging_count']}) "
              f"> {c['displace_canonical']} ({c['displace_count']})")

    conn.close()
    print("\n✅ D2516 applied.")


if __name__ == "__main__":
    main()
