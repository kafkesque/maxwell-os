#!/usr/bin/env python3
"""
scripts/backfill_practicality.py — D2622 RESOLVED flip (RATIFY-2 complete).

Stage 5 computes the advisory `practicality` tier (immediately-applicable |
context-dependent | abstract) on every FB but stage6 previously DISCARDED it
(no column). This backfills the canonical run so the "~20s applicability"
judgement is queryable in the stored principle metadata.

Deterministic + LLM-free (C1); read-only on config/practicality.yaml; writes
only the `practicality` column. Fail-closed (C16): classify_practicality
raises on a missing/malformed config or an unknown backend — never a silent
mis-label. Crash-safe: one transaction; idempotent (re-run = same values).
"""
from __future__ import annotations

import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH, CANONICAL_RUN
from pipeline.practicality import classify_practicality


def main() -> int:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 30000")
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(fbs)")}
    if "practicality" not in cols:
        cur.execute("ALTER TABLE fbs ADD COLUMN practicality TEXT")
        conn.commit()

    rows = cur.execute(
        "SELECT fb_id, application, accessibility FROM fbs "
        "WHERE pipeline_run_id=? AND status IS NOT NULL",
        (CANONICAL_RUN,),
    ).fetchall()

    dist: Counter[str] = Counter()
    updated = 0
    for fb_id, application, accessibility in rows:
        fb = {
            "application": application or "",
            "accessibility": accessibility or "",
        }
        tier = classify_practicality(fb)
        dist[tier] += 1
        cur.execute(
            "UPDATE fbs SET practicality=? WHERE fb_id=?", (tier, fb_id)
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"backfilled practicality on {updated} canonical rows: {dict(dist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
