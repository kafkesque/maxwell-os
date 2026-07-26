#!/usr/bin/env python3
"""
status.py — Pipeline status dashboard for Maxwell OS v2.0.
============================================================
Authority: CONSTITUTION.md §6 (Startup Sequence)

Displays:
  - Pipeline stage status (which stages have checkpoints)
  - Record counts per stage
  - Database summary
  - Model health (OMLX, Ollama)

Usage:
    python3 pipeline/status.py
    python3 pipeline/status.py --json   # Machine-readable output
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.omlx_call import check_omlx_health
from pipeline.pipeline_paths import (
    BOOKS_DIR,
    DB_PATH,
    PARQUET_DIR,
    SCHEMA_VERSION,
    STAGE_CHECKPOINTS,
)


def count_jsonl(path: Path) -> int:
    """Count records in a JSONL checkpoint file."""
    if not path.exists():
        return 0
    count = 0
    with open(path) as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def count_parquet_snapshots() -> int:
    """Count Parquet snapshots."""
    if not PARQUET_DIR.exists():
        return 0
    return len(list(PARQUET_DIR.glob("*.parquet")))


def get_db_stats(db_path: Path) -> dict:
    """Get summary statistics from the SQLite database."""
    stats = {"total_fbs": 0, "pass": 0, "flag": 0, "quarantine": 0}
    if not db_path.exists():
        return stats

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        row = conn.execute("SELECT COUNT(*) as cnt FROM fbs").fetchone()
        if row:
            stats["total_fbs"] = row["cnt"]

        for status in ["PASS", "FLAG", "QUARANTINE"]:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM fbs WHERE status = ?", (status,)
            ).fetchone()
            if row:
                stats[status.lower()] = row["cnt"]

        conn.close()
    except sqlite3.OperationalError:
        pass

    return stats


def check_ollama_health() -> bool:
    """Check if Ollama is running."""
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def count_books() -> int:
    """Count available books (recursively)."""
    if not BOOKS_DIR.exists():
        return 0
    count = 0
    for ext in ["*.epub", "*.pdf", "*.md"]:
        count += len(list(BOOKS_DIR.rglob(ext)))
    return count


def get_status(json_output: bool = False) -> dict:
    """Gather full pipeline status."""
    stage_counts = {i: count_jsonl(STAGE_CHECKPOINTS[i]) for i in range(7)}
    db_stats = get_db_stats(DB_PATH)
    parquet_count = count_parquet_snapshots()
    book_count = count_books()
    omlx_ok = check_omlx_health()
    ollama_ok = check_ollama_health()

    status = {
        "schema_version": SCHEMA_VERSION,
        "books_available": book_count,
        "stages": {
            "0_convert": stage_counts[0],
            "1_chunk": stage_counts[1],
            "2_extract": stage_counts[2],
            "3_cluster": stage_counts[3],
            "4_merge": stage_counts[4],
            "5_verify": stage_counts[5],
            "6_commit": stage_counts[6],
        },
        "database": db_stats,
        "parquet_snapshots": parquet_count,
        "services": {
            "omlx": "UP" if omlx_ok else "DOWN",
            "ollama": "UP" if ollama_ok else "DOWN",
        },
    }

    if json_output:
        return status

    # Pretty print
    print("╔══════════════════════════════════════════════╗")
    print("║   Maxwell OS v2.0 — Pipeline Status         ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    # Services
    omlx_icon = "✅" if omlx_ok else "❌"
    ollama_icon = "✅" if ollama_ok else "❌"
    print(f"  Services:  OMLX {omlx_icon}  |  Ollama {ollama_icon}")
    print(f"  Books:     {book_count} available in books/")
    print()

    # Pipeline stages
    print("  ┌─ Pipeline Stages ──────────────────────────┐")
    stage_names = {
        0: "0. Convert  ",
        1: "1. Chunk    ",
        2: "2. Extract  ",
        3: "3. Cluster  ",
        4: "4. Merge    ",
        5: "5. Verify   ",
        6: "6. Commit   ",
    }
    for i in range(7):
        count = stage_counts[i]
        bar = _bar(count, max(max(stage_counts.values()), 1), 20)
        name = stage_names[i]
        print(f"  │ {name} │ {bar} │ {count:>6} │")
    print("  └────────────────────────────────────────────┘")
    print()

    # Database
    print(f"  Database:  {DB_PATH}")
    print(f"    Total FBs:    {db_stats['total_fbs']}")
    print(f"    PASS:         {db_stats['pass']}")
    print(f"    FLAG:         {db_stats['flag']}")
    print(f"    QUARANTINE:   {db_stats['quarantine']}")
    print(f"    Snapshots:    {parquet_count} Parquet files")
    print()

    return status


def _bar(value: int, max_value: int, width: int = 20) -> str:
    """Draw a simple ASCII bar."""
    if max_value == 0:
        return "─" * width
    filled = int(value / max_value * width)
    return "█" * filled + "─" * (width - filled)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline status dashboard")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.json:
        status = get_status(json_output=True)
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        get_status()


if __name__ == "__main__":
    main()
