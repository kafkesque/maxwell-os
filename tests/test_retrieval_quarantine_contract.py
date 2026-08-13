#!/usr/bin/env python3
"""D2330 — Quarantine retrieval contract test.

Proves the tier semantics as an EXECUTABLE contract (not just schema doc):
  - PASS       → retrievable by default
  - QUARANTINE → retrievable ONLY with include_quarantine=True; never by default

Uses an in-memory SQLite DB so no external corpus / FTS5 / sqlite-vec infra is
required. search_fts is exercised via its LIKE fallback (the status filter is
applied identically in both the FTS5 and LIKE paths).
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.retrieve import _status_predicate, search_keyword, search_fts


def _make_db() -> sqlite3.Connection:
    """Build an in-memory fbs table with one PASS and one QUARANTINE FB."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE fbs (
            fb_id TEXT, name TEXT, definition TEXT, keywords TEXT,
            status TEXT, domains TEXT, discipline TEXT, depth TEXT,
            borp_score REAL, is_summary INTEGER, classification_status TEXT,
            source_clusters TEXT, source_books TEXT,
            verification_results TEXT, classification_errors TEXT
        )
    """)
    conn.execute("""
        INSERT INTO fbs (fb_id, name, definition, keywords, status, domains, discipline, depth, borp_score)
        VALUES ('pass_1', 'Habit Loop', 'A cue-routine-reward cycle that drives repeated behavior',
                'habit', 'PASS', 'psychology', 'behavior', 'domain', 0.9)
    """)
    conn.execute("""
        INSERT INTO fbs (fb_id, name, definition, keywords, status, domains, discipline, depth, borp_score)
        VALUES ('quar_1', 'Habit Quarantine', 'An unverified habit claim pending human review',
                'habit', 'QUARANTINE', 'psychology', 'behavior', 'domain', 0.5)
    """)
    return conn


def _ids(results: list[dict]) -> set[str]:
    return {r["fb_id"] for r in results}


def main() -> int:
    conn = _make_db()
    failures: list[str] = []

    def check(desc: str, cond: bool):
        if cond:
            print(f"  ✅ {desc}")
        else:
            failures.append(desc)
            print(f"  ❌ {desc}")

    # 1. Status predicate — the contract's single source of truth
    check(
        "_status_predicate(False) == 'status = \\'PASS\\''",
        _status_predicate(False) == "status = 'PASS'",
    )
    check(
        "_status_predicate(True) == 'status IN (\\'PASS\\', \\'QUARANTINE\\')'",
        _status_predicate(True) == "status IN ('PASS', 'QUARANTINE')",
    )

    # 2. search_keyword — default excludes QUARANTINE
    ids = _ids(search_keyword(conn, discipline="behavior"))
    check("search_keyword default returns PASS", "pass_1" in ids)
    check("search_keyword default excludes QUARANTINE", "quar_1" not in ids)

    # 3. search_keyword — include_quarantine=True returns both
    ids = _ids(search_keyword(conn, discipline="behavior", include_quarantine=True))
    check("search_keyword include_quarantine returns both", ids == {"pass_1", "quar_1"})

    # 4. search_fts — default excludes QUARANTINE
    ids = _ids(search_fts(conn, "habit"))
    check("search_fts default returns PASS", "pass_1" in ids)
    check("search_fts default excludes QUARANTINE", "quar_1" not in ids)

    # 5. search_fts — include_quarantine=True returns both
    ids = _ids(search_fts(conn, "habit", include_quarantine=True))
    check("search_fts include_quarantine returns both", ids == {"pass_1", "quar_1"})

    print()
    if failures:
        print(f"❌ FAILED {len(failures)} contract check(s):")
        for f in failures:
            print(f"   - {f}")
        return 1
    print("✅ Quarantine retrieval contract verified (D2330)")
    print("   PASS retrievable by default; QUARANTINE only via include_quarantine=True")
    return 0


if __name__ == "__main__":
    sys.exit(main())
