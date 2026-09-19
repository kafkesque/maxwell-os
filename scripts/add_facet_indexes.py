#!/usr/bin/env python3
"""Add the indexes the facet filters need (D-271d). Additive and idempotent.

WHY: `sqlite_master` holds NO index on `fbs(discipline)` or `fbs(domains)`, so both retrieval facets full-scan.
Fine at 7,995 rows; not future-proof. `CREATE INDEX IF NOT EXISTS` is additive and reversible
(`DROP INDEX`), never destructive, and needs no data rewrite.

    python3 scripts/add_facet_indexes.py --check     # report only, no DDL
    python3 scripts/add_facet_indexes.py             # create the missing indexes
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from pipeline.pipeline_paths import DB_PATH  # C12: no hardcoded path

INDEXES: dict[str, str] = {
    "idx_fbs_discipline": "CREATE INDEX IF NOT EXISTS idx_fbs_discipline ON fbs(discipline)",
    "idx_fbs_status": "CREATE INDEX IF NOT EXISTS idx_fbs_status ON fbs(status)",
    "idx_fbs_duplicate_of": "CREATE INDEX IF NOT EXISTS idx_fbs_duplicate_of ON fbs(duplicate_of)",
}


def existing(conn: sqlite3.Connection) -> set[str]:
    """Return the index names already present.

    Args:
        conn: open connection.

    Returns:
        Set of index names.
    """
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}


def plan(conn: sqlite3.Connection, discipline: str) -> str:
    """Return the query plan for a discipline facet filter.

    Args:
        conn: open connection.
        discipline: label to filter on.

    Returns:
        The plan text (proves whether the index is used).
    """
    rows = conn.execute("EXPLAIN QUERY PLAN SELECT fb_id FROM fbs WHERE discipline = ?", (discipline,))
    return " | ".join(str(r[-1]) for r in rows)


def main() -> int:
    """Create the missing facet indexes (or report them with --check)."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, run no DDL")
    ap.add_argument("--discipline", default="research methodology", help="label for the plan probe")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"FAIL-CLOSED: database not found: {DB_PATH}")
        return 1
    conn = sqlite3.connect(str(DB_PATH))
    have = existing(conn)
    missing = [n for n in INDEXES if n not in have]
    print(f"database {DB_PATH.name} | indexes present {len(have)} | missing {len(missing)}: {missing}")
    print(f"plan BEFORE: {plan(conn, args.discipline)}")
    if args.check:
        print("--check: no DDL executed")
        conn.close()
        return 0
    for name in missing:
        conn.execute(INDEXES[name])
        print(f"created {name}")
    conn.commit()
    print(f"plan AFTER : {plan(conn, args.discipline)}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
