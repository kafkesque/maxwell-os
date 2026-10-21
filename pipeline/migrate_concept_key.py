#!/usr/bin/env python3
"""pipeline/migrate_concept_key.py — D-3118 Phase A: backfill `concept_key` for the live store.

One-time, idempotent, LLM-free (D-343). Adds the `concept_key` column if absent (the same shape as
stage6_commit._migrate_add_column) and backfills every row whose `concept_key` IS NULL from its
`name` via pipeline.dedup_identity.concept_key — the ONE derivation (C21). Deterministic: re-running
fills only NULLs, never rewrites an existing key, so a name that changes later does NOT silently
re-key a committed row.

Red-loop (D-3036): the receipt is the triple
    absent -> present -> backfilled
printed as counts, and `--check` re-reads the store and refuses (exit 2) while any row carries a
NULL key or the column is missing. C13 (backup_guardian.sh) runs BEFORE --apply; a migration that
mints identity keys is a live-store write, never silent (C16).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root for `pipeline.*` (BUG-875)

from pipeline.dedup_identity import concept_key
from pipeline.pipeline_paths import DB_PATH


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise SystemExit(f"FAIL-CLOSED: store absent at {db_path} — refusing to migrate nothing (C16)")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_column(conn: sqlite3.Connection) -> bool:
    """Add concept_key if absent; return True only when this call ADDED it (the 'absent->present' leg)."""
    if "concept_key" in _columns(conn, "fbs"):
        return False
    conn.execute("ALTER TABLE fbs ADD COLUMN concept_key TEXT")
    return True


def _backfill(conn: sqlite3.Connection) -> int:
    """Fill every NULL concept_key from name; return the number of rows filled (idempotent)."""
    rows = conn.execute("SELECT rowid, name FROM fbs WHERE concept_key IS NULL").fetchall()
    conn.executemany(
        "UPDATE fbs SET concept_key = ? WHERE rowid = ?",
        [(concept_key(name), rowid) for rowid, name in rows],
    )
    return len(rows)


def _state(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
    nulls = conn.execute("SELECT COUNT(*) FROM fbs WHERE concept_key IS NULL").fetchone()[0]
    distinct = conn.execute("SELECT COUNT(DISTINCT concept_key) FROM fbs WHERE concept_key IS NOT NULL").fetchone()[0]
    return {"total": total, "null": nulls, "distinct": distinct}


def main() -> int:
    args = sys.argv[1:]
    if "--check" in args:
        conn = _connect(DB_PATH)
        try:
            if "concept_key" not in _columns(conn, "fbs"):
                print("RED: concept_key column ABSENT — Phase A not applied")
                return 2
            s = _state(conn)
            if s["null"]:
                print(f"RED: {s['null']} row(s) still carry NULL concept_key (of {s['total']})")
                return 2
            print(f"ok concept_key: {s['total']}/{s['total']} rows keyed, {s['distinct']} distinct")
            return 0
        finally:
            conn.close()

    conn = _connect(DB_PATH)
    try:
        if "--apply" not in args:
            # dry-run default (migrate_D2205 pattern): READ-ONLY, never writes (C6/C16). The column
            # presence is READ here, never mutated — _ensure_column is reachable only under --apply.
            present = "concept_key" in _columns(conn, "fbs")
            total = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
            nulls = (conn.execute("SELECT COUNT(*) FROM fbs WHERE concept_key IS NULL").fetchone()[0]
                     if present else total)
            print(f"DRY-RUN: column {'present' if present else 'ABSENT (would add)'}; "
                  f"{nulls} of {total} rows would be backfilled")
            print("re-run with --apply to write (after C13 backup)")
            return 0

        conn.execute("BEGIN IMMEDIATE")
        added = _ensure_column(conn)
        filled = _backfill(conn)
        conn.commit()
        s = _state(conn)
        print("RECEIPT (D-3036):")
        print(f"  absent -> present : column added = {added}")
        print(f"  backfilled        : {filled} rows")
        print(f"  final             : {s['total']} total, {s['null']} NULL, {s['distinct']} distinct keys")
        if s["null"]:
            print("RED: NULL concept_key rows remain after backfill")
            return 2
        print("ok concept_key: every committed row carries a generation-invariant key")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
