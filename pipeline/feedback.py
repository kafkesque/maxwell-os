#!/usr/bin/env python3
"""
feedback.py — Agent utilization feedback system (D2130 self-improvement loop).
================================================================================
Authority: D2130, C8 (Generator≠Verifier), C16 (no silent errors)

Records agent/human feedback on FB quality after utilization. Accumulated
ratings feed back into:
  - Retrieval ranking: higher-rated FBs surface first
  - FB retirement: persistently low-rated FBs flagged for review
  - Pipeline improvement: low-rated FBs signal extraction quality issues

Usage:
    from pipeline.feedback import record_feedback, get_fb_feedback_stats

    # After agent uses FB-123:
    record_feedback("FB-123", rating=0.85, was_correct=True, was_actionable=True)

    # Check FB health:
    stats = get_fb_feedback_stats("FB-123")
    if stats["needs_retirement"]:
        print(f"FB-123 should be retired: avg rating {stats['avg_rating']:.2f}")
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import DB_PATH, PROJECT_ROOT

FEEDBACK_TABLE: str = "fb_feedback"

# ── Thresholds (from config would be ideal per C12, but feedback is new) ──
RETIREMENT_THRESHOLD: float = 0.3  # avg rating below this → flag for retirement
RETIREMENT_MIN_FEEDBACKS: int = 5  # need at least N ratings before retirement consideration
BOOST_THRESHOLD: float = 0.8  # avg rating above this → boost in retrieval ranking


def _ensure_feedback_table(conn: sqlite3.Connection) -> None:
    """Create feedback table if not exists."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {FEEDBACK_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fb_id TEXT NOT NULL,
            agent_id TEXT,
            task_id TEXT,
            rating REAL NOT NULL CHECK(rating >= 0.0 AND rating <= 1.0),
            was_correct INTEGER,
            was_actionable INTEGER,
            was_timely INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (fb_id) REFERENCES fbs(fb_id)
        )
    """)
    conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_feedback_fb_id ON {FEEDBACK_TABLE}(fb_id)
    """)
    conn.commit()


def record_feedback(
    fb_id: str,
    rating: float,
    *,
    agent_id: str | None = None,
    task_id: str | None = None,
    was_correct: bool | None = None,
    was_actionable: bool | None = None,
    was_timely: bool | None = None,
    notes: str | None = None,
    db_path: Path | None = None,
) -> bool:
    """Record agent feedback on an FB.

    Args:
        fb_id: The FB being rated.
        rating: 0.0 (useless) to 1.0 (essential).
        agent_id: Which agent used the FB.
        task_id: Task context.
        was_correct: Was the FB factually correct?
        was_actionable: Did it lead to action?
        was_timely: Was it relevant at the time?
        notes: Free-text improvement notes.
        db_path: Override DB path.

    Returns:
        True if recorded successfully.
    """
    db = db_path or DB_PATH

    try:
        conn = sqlite3.connect(str(db))
        _ensure_feedback_table(conn)

        conn.execute(
            f"""INSERT INTO {FEEDBACK_TABLE}
                (fb_id, agent_id, task_id, rating, was_correct,
                 was_actionable, was_timely, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fb_id, agent_id, task_id, rating,
                1 if was_correct else (0 if was_correct is False else None),
                1 if was_actionable else (0 if was_actionable is False else None),
                1 if was_timely else (0 if was_timely is False else None),
                notes,
                datetime.now(UTC).isoformat(),
            ),
        )

        # ── Update FB aggregated scores ──
        _update_fb_aggregates(conn, fb_id)

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️  Feedback recording failed for {fb_id}: {e}")
        return False


def _update_fb_aggregates(conn: sqlite3.Connection, fb_id: str) -> None:
    """Recalculate and update aggregated feedback scores on the FB row."""
    row = conn.execute(
        f"""SELECT AVG(rating), COUNT(*)
            FROM {FEEDBACK_TABLE}
            WHERE fb_id = ?""",
        (fb_id,),
    ).fetchone()

    if row and row[0] is not None:
        conn.execute(
            """UPDATE fbs SET
                feedback_score = ?,
                feedback_count = ?
            WHERE fb_id = ?""",
            (round(row[0], 3), row[1], fb_id),
        )


def get_fb_feedback_stats(fb_id: str, db_path: Path | None = None) -> dict:
    """Get feedback statistics for an FB.

    Returns dict with:
        avg_rating, count, needs_retirement, needs_boost,
        correctness_rate, actionability_rate, timeliness_rate
    """
    db = db_path or DB_PATH

    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            f"""SELECT
                    AVG(rating) as avg_rating,
                    COUNT(*) as count,
                    AVG(CASE WHEN was_correct = 1 THEN 1.0 ELSE 0.0 END) as correctness_rate,
                    AVG(CASE WHEN was_actionable = 1 THEN 1.0 ELSE 0.0 END) as actionability_rate,
                    AVG(CASE WHEN was_timely = 1 THEN 1.0 ELSE 0.0 END) as timeliness_rate
                FROM {FEEDBACK_TABLE}
                WHERE fb_id = ?""",
            (fb_id,),
        ).fetchone()

        conn.close()

        if row is None or row["count"] == 0:
            return {
                "avg_rating": None,
                "count": 0,
                "needs_retirement": False,
                "needs_boost": False,
                "correctness_rate": None,
                "actionability_rate": None,
                "timeliness_rate": None,
            }

        avg = row["avg_rating"]
        count = row["count"]

        return {
            "avg_rating": round(avg, 3),
            "count": count,
            "needs_retirement": count >= RETIREMENT_MIN_FEEDBACKS and avg < RETIREMENT_THRESHOLD,
            "needs_boost": count >= 3 and avg >= BOOST_THRESHOLD,
            "correctness_rate": round(row["correctness_rate"], 3) if row["correctness_rate"] else None,
            "actionability_rate": round(row["actionability_rate"], 3) if row["actionability_rate"] else None,
            "timeliness_rate": round(row["timeliness_rate"], 3) if row["timeliness_rate"] else None,
        }
    except Exception as e:
        print(f"⚠️  Feedback stats query failed for {fb_id}: {e}")
        return {"avg_rating": None, "count": 0, "needs_retirement": False, "needs_boost": False,
                "correctness_rate": None, "actionability_rate": None, "timeliness_rate": None,
                "error": str(e)}


def get_retirement_candidates(db_path: Path | None = None) -> list[dict]:
    """Get FBs flagged for retirement (low avg rating, enough feedbacks)."""
    db = db_path or DB_PATH

    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        _ensure_feedback_table(conn)

        rows = conn.execute(
            f"""SELECT fb_id, feedback_score, feedback_count, name
                FROM fbs
                WHERE feedback_count >= ?
                  AND feedback_score < ?
                ORDER BY feedback_score ASC""",
            (RETIREMENT_MIN_FEEDBACKS, RETIREMENT_THRESHOLD),
        ).fetchall()

        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"⚠️  Retirement scan failed: {e}")
        return []


def mark_fb_retrieved(fb_id: str, db_path: Path | None = None) -> None:
    """Update usage_count and last_retrieved_at when an FB is retrieved."""
    db = db_path or DB_PATH

    try:
        conn = sqlite3.connect(str(db))
        conn.execute(
            """UPDATE fbs SET
                usage_count = usage_count + 1,
                last_retrieved_at = ?
            WHERE fb_id = ?""",
            (datetime.now(UTC).isoformat(), fb_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️  Usage tracking failed for {fb_id}: {e}")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="FB Feedback System (D2130)")
    sub = parser.add_subparsers(dest="cmd")

    # record
    rec = sub.add_parser("record", help="Record feedback")
    rec.add_argument("fb_id")
    rec.add_argument("--rating", type=float, required=True)
    rec.add_argument("--agent-id")
    rec.add_argument("--correct", action="store_true")
    rec.add_argument("--actionable", action="store_true")
    rec.add_argument("--timely", action="store_true")
    rec.add_argument("--notes")

    # stats
    st = sub.add_parser("stats", help="Get FB feedback stats")
    st.add_argument("fb_id")

    # retirement
    sub.add_parser("retirement", help="List retirement candidates")

    args = parser.parse_args()

    if args.cmd == "record":
        ok = record_feedback(
            args.fb_id, args.rating,
            agent_id=args.agent_id,
            was_correct=args.correct,
            was_actionable=args.actionable,
            was_timely=args.timely,
            notes=args.notes,
        )
        print(f"{'✅' if ok else '❌'} Feedback recorded for {args.fb_id}")

    elif args.cmd == "stats":
        stats = get_fb_feedback_stats(args.fb_id)
        print(json.dumps(stats, indent=2))

    elif args.cmd == "retirement":
        candidates = get_retirement_candidates()
        if candidates:
            print(f"🚩 {len(candidates)} FBs flagged for retirement:")
            for c in candidates:
                print(f"  {c['fb_id'][:12]} | rating={c['feedback_score']:.2f} "
                      f"({c['feedback_count']} ratings) | {c['name'][:40]}")
        else:
            print("✅ No retirement candidates found.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
