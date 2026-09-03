#!/usr/bin/env python3
"""
apply_d2399_urban_planning.py — D2517

Deterministic, LLM-free application of the human-approved D2399 candidate 1:
promote emerging domain "urban planning" (118) to canonical, displacing the
weakest canonical domain "ml systems & infrastructure" (18) — D2378 closed-loop
(domain cardinality unchanged at 43).

Re-resolves the affected committed FBs (no LLM reclassification):
  - FBs whose domains_raw contains a label resolving to "urban planning"
        -> add "urban planning" to the canonical `domains` list
  - FBs whose canonical `domains` contains the displaced "ml systems & infrastructure"
        -> removed; if the list empties, set to ["emerging"]

Steps (idempotent / crash-safe):
  1. Back up the DB (C13).
  2. Re-resolve FB domain lists (deterministic canonical match).
  3. reconcile_canonical_status(): YAML truth wins.
  4. Mark "ml systems & infrastructure" 'displaced' (D2399 semantics).
  5. update_counts_from_fbs(): full idempotent recount (Drift-F safe).
  6. Verify + report the post-approval challenger pool.

Run: PYTHONPATH=. /usr/local/bin/python3 scripts/apply_d2399_urban_planning.py
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pipeline.schemas import match_to_canonical, normalize_label
from pipeline.taxonomy_manager import (
    check_for_replacements,
    reconcile_canonical_status,
    update_counts_from_fbs,
)
from pipeline.pipeline_paths import DB_PATH

UTC = timezone.utc

PROMOTE = "urban planning"
DISPLACE = "ml systems & infrastructure"


def _parse(x):
    try:
        return json.loads(x) if isinstance(x, str) else (x or [])
    except (json.JSONDecodeError, TypeError):
        return []


def main() -> None:
    db_path = Path(DB_PATH)
    backup = db_path.with_name(f"{db_path.name}.bak_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(db_path, backup)
    print(f"✅ DB backed up -> {backup}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT fb_id, domains, domains_raw FROM fbs").fetchall()
    promoted = 0
    displaced = 0
    for r in rows:
        doms = _parse(r["domains"])
        raw = _parse(r["domains_raw"])

        has_promote = any(
            isinstance(lbl, str) and match_to_canonical(lbl, "domain") == PROMOTE
            for lbl in raw
        )

        new_doms = [d for d in doms if isinstance(d, str)]
        if has_promote and not any(normalize_label(d) == normalize_label(PROMOTE) for d in new_doms):
            new_doms = [d for d in new_doms if normalize_label(d) != "emerging"]
            new_doms.append(PROMOTE)
            promoted += 1

        before_len = len(new_doms)
        new_doms = [d for d in new_doms if normalize_label(d) != normalize_label(DISPLACE)]
        if len(new_doms) < before_len:
            displaced += 1
        if not new_doms:
            new_doms = ["emerging"]

        if new_doms != doms:
            conn.execute(
                "UPDATE fbs SET domains = ? WHERE fb_id = ?",
                (json.dumps(new_doms, ensure_ascii=False), r["fb_id"]),
            )

    print(f"FB re-resolution: +{promoted} gained urban planning, {displaced} lost ml systems & infrastructure")

    reconciled = reconcile_canonical_status(conn)
    print(f"reconcile_canonical_status: {reconciled} row(s) adjusted")

    conn.execute(
        "UPDATE taxonomy_counts SET status = 'displaced', last_updated = ? "
        "WHERE label = ? AND label_type = 'domain'",
        (datetime.now(UTC).isoformat(), DISPLACE),
    )

    changes = update_counts_from_fbs(conn)
    conn.commit()
    print(f"recount flood_warning={changes.get('flood_warning', False)}")

    print("\n=== Post-approval taxonomy_counts (relevant) ===")
    for r in conn.execute(
        "SELECT label, count, status FROM taxonomy_counts "
        "WHERE label IN (?, ?) AND label_type='domain' ORDER BY label",
        (PROMOTE, DISPLACE),
    ):
        print(f"  {r['status']:10} {r['count']:>4}  {r['label']}")

    print("\n=== Remaining D2399 candidates ===")
    for c in check_for_replacements(conn):
        print(f"  [{c['label_type']}] {c['emerging_label']} ({c['emerging_count']}) "
              f"> {c['displace_canonical']} ({c['displace_count']})")

    conn.close()
    print("\n✅ D2517 applied.")


if __name__ == "__main__":
    main()
