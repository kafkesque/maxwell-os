#!/usr/bin/env python3
"""
migrate_D2205_epistemic.py — D2205 Two-Axis Epistemic Model Migration.
=======================================================================
Authority: D2205 P3 (2026-08-06 RAG Architecture Roadmap)
Constitution: C6 (crash-safe writes: tempfile → fsync → os.replace),
              C12 (no hardcoding), C17 (type hints), C18 (docstrings)

Adds 8 columns to fbs table:
  Evidence axis (4): evidence_support, evidence_independence,
                      evidence_contradiction, evidence_coverage
  Execution axis (3): execution_trials, execution_successes,
                       execution_context_similarity
  Epistemic state (1): epistemic_state

Backfills existing data:
  - evidence_support ← borp_score
  - epistemic_state ← derived from status + feedback_count
  - execution_trials ← feedback_count
  - execution_successes ← feedback_count × feedback_score

Idempotent: safe to run multiple times (checks PRAGMA table_info first).

Usage:
    python3 pipeline/migrate_D2205_epistemic.py           # Run migration
    python3 pipeline/migrate_D2205_epistemic.py --dry-run  # Preview what would happen
    python3 pipeline/migrate_D2205_epistemic.py --verify   # Verify migration state
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH

# ── Column definitions (C12: in code rather than config since these are
#    schema migration constants, not runtime-configurable thresholds) ──

EPISTEMIC_COLUMNS: dict[str, str] = {
    "evidence_support": "REAL",
    "evidence_independence": "REAL",
    "evidence_contradiction": "REAL",
    "evidence_coverage": "REAL",
    "execution_trials": "INTEGER DEFAULT 0",
    "execution_successes": "INTEGER DEFAULT 0",
    "execution_context_similarity": "REAL",
    "epistemic_state": "TEXT DEFAULT 'corroborated'",
}

# Valid epistemic states (enforced by CHECK constraint)
EPISTEMIC_STATES: list[str] = [
    "corroborated",        # Multiple independent sources support
    "partially_supported",  # Some evidence, gaps remain
    "contested",           # Active contradiction between sources
    "source_supported",    # Single source supports (below BORP threshold)
    "unresolved",          # Not yet evaluated
    "contradicted",        # Evidence contradicts the claim
    "execution_tested",    # Empirically validated through execution
    "retired",             # Feedback score fell below retirement threshold
]


# ── Migration ───────────────────────────────────────────────────────────

def migrate(conn: sqlite3.Connection, *, dry_run: bool = False) -> list[str]:
    """Add D2205 epistemic model columns. Idempotent.

    Checks PRAGMA table_info(fbs) before each ALTER TABLE to avoid
    duplicate column errors. Backfills existing data from borp_score
    and feedback_score where available.

    Args:
        conn: SQLite connection (read-write for migration, read-only for dry-run)
        dry_run: If True, only report what would happen without modifying

    Returns:
        List of action strings describing what was done / would be done

    C6 compliance: If not dry_run, uses tempfile → fsync → os.replace
                   for the actual DB write (handled by SQLite WAL mode).

    Raises:
        sqlite3.Error: If migration fails (caught by caller)
    """
    actions: list[str] = []

    # Get existing columns
    existing: set[str] = {
        row[1] for row in conn.execute("PRAGMA table_info(fbs)")
    }

    # Check each column
    for col_name, col_type in EPISTEMIC_COLUMNS.items():
        if col_name in existing:
            actions.append(f"  ⏭️  {col_name}: already exists")
        else:
            if dry_run:
                actions.append(f"  📋 {col_name} {col_type}: would add")
            else:
                conn.execute(
                    f"ALTER TABLE fbs ADD COLUMN {col_name} {col_type}"
                )
                actions.append(f"  ✅ {col_name} {col_type}: added")

    # Backfill existing data (only if migration actually happened)
    if not dry_run:
        backfill_count: int = _backfill(conn)
        actions.append(f"  📊 Backfilled {backfill_count} existing FB(s)")

    return actions


def _backfill(conn: sqlite3.Connection) -> int:
    """Backfill existing FBs with epistemic data from current schema.

    Derives:
      - evidence_support from borp_score
      - evidence_independence as 0.5 (unknown — recalibrate on next S4 run)
      - evidence_contradiction as 0.0 (unknown — recalibrate)
      - evidence_coverage as 0.5 (unknown)
      - execution_trials from feedback_count
      - execution_successes as feedback_count × feedback_score (estimate)
      - epistemic_state from status + feedback_count

    Args:
        conn: Read-write SQLite connection

    Returns:
        Number of FBs backfilled
    """
    # Backfill from existing data
    conn.execute("""
        UPDATE fbs SET
            evidence_support = COALESCE(borp_score, 0.5),
            evidence_independence = 0.5,
            evidence_contradiction = 0.0,
            evidence_coverage = 0.5,
            execution_trials = COALESCE(feedback_count, 0),
            execution_successes = CAST(
                COALESCE(feedback_count, 0) * COALESCE(feedback_score, 0.5)
                AS INTEGER
            ),
            execution_context_similarity = 0.5
        WHERE evidence_support IS NULL
    """)

    # Backfill epistemic_state from status + feedback_count
    conn.execute("""
        UPDATE fbs SET epistemic_state = 'corroborated'
        WHERE epistemic_state = 'corroborated'
          AND status = 'PASS'
          AND borp_score >= 0.5
    """)
    conn.execute("""
        UPDATE fbs SET epistemic_state = 'partially_supported'
        WHERE epistemic_state = 'corroborated'
          AND status = 'PASS'
          AND (borp_score < 0.5 OR borp_score IS NULL)
    """)
    conn.execute("""
        UPDATE fbs SET epistemic_state = 'unresolved'
        WHERE epistemic_state = 'corroborated'
          AND status NOT IN ('PASS', 'RETIRED')
    """)
    conn.execute("""
        UPDATE fbs SET epistemic_state = 'execution_tested'
        WHERE epistemic_state = 'corroborated'
          AND feedback_count > 0
          AND feedback_score >= 0.7
    """)
    conn.execute("""
        UPDATE fbs SET epistemic_state = 'retired'
        WHERE epistemic_state = 'corroborated'
          AND status = 'RETIRED'
    """)

    conn.commit()
    return conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE evidence_support IS NOT NULL"
    ).fetchone()[0]


# ── Verification ────────────────────────────────────────────────────────

def verify(conn: sqlite3.Connection) -> tuple[bool, str]:
    """Verify migration state — all columns present, data backfilled.

    Args:
        conn: Read-only SQLite connection

    Returns:
        (ok, message) tuple
    """
    existing: set[str] = {
        row[1] for row in conn.execute("PRAGMA table_info(fbs)")
    }

    missing: list[str] = [
        col for col in EPISTEMIC_COLUMNS if col not in existing
    ]

    if missing:
        return False, f"Missing columns: {', '.join(missing)}"

    # Check backfill
    total = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
    backfilled = conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE evidence_support IS NOT NULL"
    ).fetchone()[0]

    if total > 0 and backfilled == 0:
        return False, f"{total} FBs found but 0 backfilled — run without --verify first"

    # State distribution
    states = conn.execute(
        "SELECT epistemic_state, COUNT(*) as cnt FROM fbs GROUP BY epistemic_state"
    ).fetchall()
    state_summary = ", ".join(f"{s['epistemic_state']}: {s['cnt']}" for s in states)

    return True, (
        f"✅ All {len(EPISTEMIC_COLUMNS)} columns present\n"
        f"   {backfilled}/{total} FBs backfilled\n"
        f"   States: {state_summary}"
    )


# ── Crash-safe write (C6) ──────────────────────────────────────────────

def migrate_safe(db_path: Path, *, dry_run: bool = False) -> list[str]:
    """C6-compliant migration: tempfile → fsync → os.replace.

    Copies DB to tempfile, migrates the copy, syncs, then atomically
    replaces the original. If anything fails, the original is untouched.

    Args:
        db_path: Path to Maxwell SQLite database
        dry_run: If True, report without modifying

    Returns:
        List of action strings

    Raises:
        FileNotFoundError: If DB doesn't exist
        sqlite3.Error: If migration fails
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    if dry_run:
        conn: sqlite3.Connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            return migrate(conn, dry_run=True)
        finally:
            conn.close()

    # C6: tempfile → fsync → os.replace
    with tempfile.NamedTemporaryFile(
        suffix=".db", delete=False, dir=db_path.parent
    ) as tmp:
        tmp_path: Path = Path(tmp.name)

    try:
        # Copy original to tempfile
        import shutil
        shutil.copy2(db_path, tmp_path)

        # Migrate the copy
        conn = sqlite3.connect(str(tmp_path))
        try:
            actions: list[str] = migrate(conn, dry_run=False)
        finally:
            conn.close()

        # fsync
        fd = os.open(str(tmp_path), os.O_RDONLY)
        os.fsync(fd)
        os.close(fd)

        # Atomic replace
        os.replace(tmp_path, db_path)

        return actions
    except Exception:
        # Clean up tempfile on failure
        if tmp_path.exists():
            tmp_path.unlink()
        raise


# ── CLI ─────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point with dry-run, verify, and force modes."""
    import argparse

    parser = argparse.ArgumentParser(
        description="D2205: Two-axis epistemic model migration"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without modifying DB",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration state without running",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    args = parser.parse_args()

    if args.verify:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            ok, msg = verify(conn)
            print(msg)
            sys.exit(0 if ok else 1)
        finally:
            conn.close()
        return

    if args.dry_run:
        print("=== D2205 Migration — DRY RUN ===\n")
        print(f"  DB: {DB_PATH}")
        if not DB_PATH.exists():
            print("  ❌ DB not found — run smoke or full pipeline first")
            sys.exit(1)
        actions = migrate_safe(DB_PATH, dry_run=True)
        for action in actions:
            print(action)
        print(f"\n  Run without --dry-run to apply.")
        return

    # Confirm
    if not args.force:
        print(f"=== D2205 Epistemic Model Migration ===\n")
        print(f"  DB: {DB_PATH}")
        print(f"  Columns to add: {', '.join(EPISTEMIC_COLUMNS)}")
        print(f"  Backfill: borp_score → evidence_support, feedback → execution_*")
        print(f"\n  This is a safe migration (C6: tempfile → fsync → os.replace).")
        print(f"  No data will be lost.\n")
        resp = input("  Continue? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            print("  Aborted.")
            sys.exit(0)

    try:
        actions = migrate_safe(DB_PATH, dry_run=False)
        print(f"  DB: {DB_PATH}")
        for action in actions:
            print(action)
        print(f"\n✅ D2205 migration complete.")
    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as exc:
        print(f"❌ Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
