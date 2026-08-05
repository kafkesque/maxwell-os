#!/usr/bin/env python3
"""reliability.py — FB execution reliability tracking (D2015 / FOUNDATION-SPEC §2).

Authority: FOUNDATION-BLOCK-TO-SKILL-SPEC v1.1 §2, D2015, D2049.
Ports the v1 fb_reliability model to v2 using existing feedback_score +
usage_count columns as lightweight proxy until full PI execution logging
is wired (Phase 2, requires 100+ verified FBs per D2015).

Provides:
  - get_reliability(fb_id) → dict with reliability_score, tier, total_executions
  - render_stable_gate(fb_id) → str for Zone 3 STABLE GATE line
  - get_unstable_fbs() → list of FBs below threshold (review queue)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# D2175: Use DB_PATH from pipeline_paths — no hardcoded paths (C12a)
from pipeline.pipeline_paths import DB_PATH as _DB_PATH
DB_PATH: Path = _DB_PATH

# ── Thresholds (from spec §2.3) ─────────────────────────────────────────
STABLE_THRESHOLD: float = 0.85
WATCH_THRESHOLD: float = 0.50
GARBAGE_THRESHOLD: float = 0.20
MIN_EXECUTIONS_FOR_GARBAGE: int = 10
MIN_RATINGS_FOR_TIER: int = 3


def get_reliability(fb_id: str, db_path: Path | None = None) -> dict:
    """Get reliability stats for an FB.

    Returns dict:
        reliability_score: float | None  (0.0-1.0, None if no data)
        tier: str  — "STABLE" | "WATCH" | "UNSTABLE" | "GARBAGE" | "NO_DATA"
        usage_count: int
        feedback_count: int
        feedback_score: float | None
        needs_review: bool
    """
    db = db_path or DB_PATH
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT usage_count, feedback_score, feedback_count FROM fbs WHERE fb_id = ?",
            (fb_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        conn.close()
        return _no_data()
    conn.close()

    if row is None:
        return _no_data()

    usage = row["usage_count"] or 0
    fscore = row["feedback_score"]
    fcount = row["feedback_count"] or 0

    # Use feedback_score as reliability proxy until fb_reliability table exists
    reliability = fscore
    tier = _compute_tier(reliability, usage, fcount)

    return {
        "reliability_score": round(reliability, 3) if reliability is not None else None,
        "tier": tier,
        "usage_count": usage,
        "feedback_count": fcount,
        "feedback_score": reliability,
        "needs_review": tier in ("UNSTABLE", "GARBAGE"),
    }


def _compute_tier(
    reliability: float | None, usage_count: int, feedback_count: int
) -> str:
    """Compute reliability tier from score and counts (spec §2.3)."""
    if reliability is None or feedback_count < MIN_RATINGS_FOR_TIER:
        return "NO_DATA"
    if reliability >= STABLE_THRESHOLD and usage_count >= 3:
        return "STABLE"
    if reliability >= WATCH_THRESHOLD:
        return "WATCH"
    if (
        reliability < GARBAGE_THRESHOLD
        and usage_count >= MIN_EXECUTIONS_FOR_GARBAGE
    ):
        return "GARBAGE"
    return "UNSTABLE"


def _no_data() -> dict:
    return {
        "reliability_score": None,
        "tier": "NO_DATA",
        "usage_count": 0,
        "feedback_count": 0,
        "feedback_score": None,
        "needs_review": False,
    }


def render_stable_gate(fb_id: str, evidence_type: str = "cited",
                       db_path: Path | None = None) -> str:
    """Render the Zone 3 STABLE GATE line.

    Format: '✅ Stable if: cited · reliability: 0.94 (47 exec)'
             '⚠️ Watch: contradicted in 3/23 — review applicability'
    """
    rel = get_reliability(fb_id, db_path)
    tier = rel["tier"]

    if tier == "STABLE":
        line = f"✅ Stable if: {evidence_type}"
        if rel["reliability_score"] is not None:
            line += f" · reliability: {rel['reliability_score']:.2f} ({rel['usage_count']} uses)"
        return line

    elif tier == "WATCH":
        line = f"⚠️ Watch"
        if rel["reliability_score"] is not None:
            line += f": reliability {rel['reliability_score']:.2f} ({rel['feedback_count']} ratings)"
        return line

    elif tier == "UNSTABLE":
        return f"🔴 UNSTABLE — needs review ({rel['feedback_count']} ratings)"

    elif tier == "GARBAGE":
        return f"🗑️ GARBAGE — propose archive ({rel['usage_count']} uses, score {rel['reliability_score']:.2f})"

    else:
        return f"⚪ No data yet · Stable if: {evidence_type}"


def get_unstable_fbs(db_path: Path | None = None, limit: int = 50) -> list[dict]:
    """Get FBs that need human review (low feedback_score with enough ratings).

    Returns list of {fb_id, name, feedback_score, feedback_count, usage_count}.
    """
    db = db_path or DB_PATH
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT fb_id, name, feedback_score, feedback_count, usage_count
               FROM fbs
               WHERE feedback_count >= ?
                 AND (feedback_score < ? OR feedback_score IS NULL)
               ORDER BY feedback_score ASC NULLS LAST
               LIMIT ?""",
            (MIN_RATINGS_FOR_TIER, WATCH_THRESHOLD, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    conn.close()
    return [dict(r) for r in rows]


def get_top_reliable_fbs(db_path: Path | None = None, limit: int = 20) -> list[dict]:
    """Get the most reliable FBs (high feedback_score + high usage_count)."""
    db = db_path or DB_PATH
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT fb_id, name, feedback_score, feedback_count, usage_count
               FROM fbs
               WHERE feedback_count >= ? AND feedback_score >= ?
               ORDER BY feedback_score DESC, usage_count DESC
               LIMIT ?""",
            (MIN_RATINGS_FOR_TIER, STABLE_THRESHOLD, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    conn.close()
    return [dict(r) for r in rows]


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="FB Reliability (D2015)")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("unstable", help="List unstable FBs needing review")
    sub.add_parser("top", help="List top reliable FBs")

    st = sub.add_parser("gate", help="Render STABLE GATE for one FB")
    st.add_argument("fb_id")

    args = parser.parse_args()

    if args.cmd == "unstable":
        fbs = get_unstable_fbs()
        if fbs:
            print(f"{len(fbs)} FBs need review:")
            for fb in fbs:
                print(f"  {fb['fb_id'][:16]} | score={fb.get('feedback_score',0) or 0:.2f} "
                      f"({fb['feedback_count']} ratings) | {fb['name'][:50]}")
        else:
            print("All FBs above watch threshold.")

    elif args.cmd == "top":
        fbs = get_top_reliable_fbs()
        if fbs:
            print(f"Top {len(fbs)} reliable FBs:")
            for fb in fbs:
                print(f"  {fb['fb_id'][:16]} | score={fb['feedback_score']:.2f} "
                      f"({fb['feedback_count']} ratings) | {fb['name'][:50]}")
        else:
            print("No stable FBs yet.")

    elif args.cmd == "gate":
        print(render_stable_gate(args.fb_id))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
