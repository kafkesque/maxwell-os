#!/usr/bin/env python3
"""
principle_index.py — Persistent principle index with SHA-256 + MinHash LSH dedup.
Authority: D2067, CONSTITUTION.md §3

Cross-run incremental extraction:
  1. Before Stage 2 extraction: check SHA-256 exact + MinHash near-duplicate
  2. After extraction: insert into persistent index
  3. LSH index loaded from maxwell.db on startup, queried before each extraction

Human review gates:
  - C9-G1: First 5 dedup skips per run are logged to dedup_log.json for spot-check
  - C9-G2: hdbscan.approximate_predict() noise >20% triggers cluster review
  - C9-G3: After every 5 incremental runs, cluster drift report
"""

import hashlib
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import DB_PATH
from pipeline.stamp import get_pipeline_run_id

# ── Constants ────────────────────────────────────────────────────────────

MINHASH_NUM_PERM: int = 128
MINHASH_THRESHOLD: float = 0.90  # Jaccard similarity for near-duplicate
MAX_DEDUP_LOG_SAMPLES: int = 5   # C9-G1: log first N skips per run


# ── Table init ────────────────────────────────────────────────────────────

CREATE_PRINCIPLES_INDEX = """
CREATE TABLE IF NOT EXISTS principles_index (
    principle_hash TEXT PRIMARY KEY,      -- SHA-256(principle_text + source_segment_id)
    principle_text TEXT NOT NULL,
    source_segment_id TEXT NOT NULL,
    source_book TEXT,
    minhash_blob BLOB,                    -- MinHash signature (128 perm, serialized)
    extracted_at TEXT NOT NULL,
    pipeline_run_id TEXT NOT NULL,
    skip_count INTEGER NOT NULL DEFAULT 0 -- Times this exact hash was skipped
);
"""

CREATE_INDEX_RUN_ID = """
CREATE INDEX IF NOT EXISTS idx_principles_index_run
ON principles_index(pipeline_run_id);
"""


def init_principles_index(conn: sqlite3.Connection) -> None:
    """Create the principles_index table if it doesn't exist."""
    conn.execute(CREATE_PRINCIPLES_INDEX)
    conn.execute(CREATE_INDEX_RUN_ID)
    conn.commit()


# ── MinHash helpers ───────────────────────────────────────────────────────

def _compute_minhash(text: str, num_perm: int = MINHASH_NUM_PERM) -> list[int] | None:
    """
    Compute MinHash signature for a text string.
    Returns list of 128 integers, or None if datasketch unavailable.
    """
    try:
        from datasketch import MinHash
        m = MinHash(num_perm=num_perm)
        # Tokenize into shingles (word 3-grams)
        words = text.lower().split()
        for i in range(len(words) - 2):
            m.update(words[i].encode('utf-8'))
            m.update(words[i + 1].encode('utf-8'))
            m.update(words[i + 2].encode('utf-8'))
        return m.hashvalues.tolist() if hasattr(m.hashvalues, 'tolist') else list(m.hashvalues)
    except ImportError:
        return None


def _minhash_jaccard(sig1: list[int], sig2: list[int]) -> float:
    """Estimate Jaccard similarity between two MinHash signatures."""
    if len(sig1) != len(sig2):
        return 0.0
    matches = sum(1 for a, b in zip(sig1, sig2, strict=False) if a == b)
    return matches / len(sig1)


def _serialize_minhash(sig: list[int]) -> bytes:
    """Serialize MinHash signature to blob for SQLite storage."""
    import struct
    return struct.pack(f'{len(sig)}q', *sig)


def _deserialize_minhash(blob: bytes) -> list[int]:
    """Deserialize MinHash signature from SQLite blob."""
    import struct
    n = len(blob) // 8
    return list(struct.unpack(f'{n}q', blob))


# ── Hash computation ──────────────────────────────────────────────────────

def compute_principle_hash(principle_text: str, source_segment_id: str) -> str:
    """
    SHA-256 hash of (principle_text + source_segment_id).
    Used as the primary key in principles_index.
    """
    content = f"{principle_text}|||{source_segment_id}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


# ── Core operations ───────────────────────────────────────────────────────

def check_duplicate(
    conn: sqlite3.Connection,
    principle_text: str,
    source_segment_id: str,
    minhash_sig: list[int] | None = None,
) -> tuple[bool, str]:
    """
    Check if a principle is a duplicate (exact or near-duplicate) of any previously extracted.

    Args:
        conn: SQLite connection to maxwell.db
        principle_text: The candidate principle text
        source_segment_id: Source segment identifier
        minhash_sig: Pre-computed MinHash signature (optional, computed if not provided)

    Returns:
        (is_duplicate, reason) where reason is one of:
        - 'exact_match' — SHA-256 identical
        - 'near_duplicate' — MinHash Jaccard ≥ threshold
        - '' — not a duplicate
    """
    # 1. Exact SHA-256 match
    phash = compute_principle_hash(principle_text, source_segment_id)
    existing = conn.execute(
        "SELECT principle_hash FROM principles_index WHERE principle_hash = ?",
        (phash,)
    ).fetchone()

    if existing:
        # Update skip count
        conn.execute(
            "UPDATE principles_index SET skip_count = skip_count + 1 WHERE principle_hash = ?",
            (phash,)
        )
        conn.commit()
        return True, 'exact_match'

    # 2. MinHash near-duplicate
    if minhash_sig is None:
        minhash_sig = _compute_minhash(principle_text)

    if minhash_sig is not None:
        # Load existing signatures for comparison (limit to recent runs for performance)
        existing_sigs = conn.execute(
            """SELECT principle_hash, minhash_blob, principle_text
               FROM principles_index
               WHERE minhash_blob IS NOT NULL
               ORDER BY extracted_at DESC LIMIT 5000"""
        ).fetchall()

        for _ex_hash, ex_blob, _ex_text in existing_sigs:
            if ex_blob is None:
                continue
            try:
                ex_sig = _deserialize_minhash(ex_blob)
            except Exception:
                continue

            jaccard = _minhash_jaccard(minhash_sig, ex_sig)
            if jaccard >= MINHASH_THRESHOLD:
                return True, 'near_duplicate'

    return False, ''


def insert_principle(
    conn: sqlite3.Connection,
    principle_text: str,
    source_segment_id: str,
    source_book: str = "",
) -> str | None:
    """
    Insert a newly extracted principle into the persistent index.

    Returns the principle_hash on success, None on failure.
    """
    phash = compute_principle_hash(principle_text, source_segment_id)
    minhash_sig = _compute_minhash(principle_text)
    minhash_blob = _serialize_minhash(minhash_sig) if minhash_sig else None
    now = datetime.now(UTC).isoformat()
    run_id = get_pipeline_run_id()

    try:
        conn.execute(
            """INSERT OR REPLACE INTO principles_index
               (principle_hash, principle_text, source_segment_id, source_book,
                minhash_blob, extracted_at, pipeline_run_id, skip_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (phash, principle_text, source_segment_id, source_book,
             minhash_blob, now, run_id)
        )
        conn.commit()
        return phash
    except sqlite3.Error:
        return None


def get_index_stats(conn: sqlite3.Connection) -> dict:
    """Return statistics about the principles_index for reporting."""
    total = conn.execute("SELECT COUNT(*) FROM principles_index").fetchone()[0]
    with_minhash = conn.execute(
        "SELECT COUNT(*) FROM principles_index WHERE minhash_blob IS NOT NULL"
    ).fetchone()[0]
    total_skips = conn.execute(
        "SELECT COALESCE(SUM(skip_count), 0) FROM principles_index"
    ).fetchone()[0]
    runs = conn.execute(
        "SELECT COUNT(DISTINCT pipeline_run_id) FROM principles_index"
    ).fetchone()[0]

    return {
        "total_principles": total,
        "with_minhash": with_minhash,
        "total_skips": total_skips,
        "pipeline_runs": runs,
    }


# ── Dedup logging for human review (C9-G1) ─────────────────────────────────

class DedupLogger:
    """Logs first N dedup skips per run for human spot-check (C9-G1)."""

    def __init__(self, log_dir: Path, max_samples: int = MAX_DEDUP_LOG_SAMPLES):
        self.log_dir = log_dir
        self.max_samples = max_samples
        self.samples: list[dict] = []
        self.total_skipped = 0
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def record(self, principle_text: str, source_segment_id: str, reason: str) -> None:
        """Record a dedup skip. Only logs first max_samples."""
        self.total_skipped += 1
        if len(self.samples) < self.max_samples:
            self.samples.append({
                "principle_text": principle_text[:200],
                "source_segment_id": source_segment_id,
                "reason": reason,
                "timestamp": datetime.now(UTC).isoformat(),
            })

    def flush(self) -> Path:
        """Write dedup log to disk. Returns path."""
        log_path = self.log_dir / "dedup_log.json"
        data = {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_skipped": self.total_skipped,
            "sample_size": len(self.samples),
            "samples": self.samples,
            "instructions": (
                "C9-G1 HUMAN REVIEW: Spot-check these skipped principles. "
                "Verify they are genuinely duplicates, not distinct principles with similar phrasing. "
                "If >20% are false positives, lower MINHASH_THRESHOLD (currently 0.90) in principle_index.py."
            ),
        }
        safe_write(log_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        return log_path


# ── Incremental clustering support (C9-G2/G3) ─────────────────────────────

def check_cluster_drift(
    conn: sqlite3.Connection,
    new_principle_count: int,
    noise_count: int,
) -> dict | None:
    """
    Check if new principles are forming too much noise (C9-G2).
    If noise > 20% of new principles, return a drift report.

    Returns:
        Drift report dict if noise exceeds threshold, None otherwise.
    """
    if new_principle_count == 0:
        return None

    noise_ratio = noise_count / new_principle_count
    if noise_ratio <= 0.20:
        return None

    stats = get_index_stats(conn)
    return {
        "warning": "C9-G2: High noise ratio in incremental clustering",
        "noise_ratio": round(noise_ratio, 3),
        "noise_count": noise_count,
        "new_principle_count": new_principle_count,
        "total_indexed": stats["total_principles"],
        "pipeline_runs": stats["pipeline_runs"],
        "recommendation": (
            "Consider one of: (a) accept noise as-is, "
            "(b) trigger full re-clustering, "
            "(c) lower HDBSCAN min_cluster_size for this run."
        ),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def should_full_recluster(conn: sqlite3.Connection, runs_since_last: int) -> bool:
    """
    C9-G3: After every 5-10 incremental runs, recommend full re-clustering.

    Args:
        conn: SQLite connection
        runs_since_last: Number of incremental runs since last full recluster

    Returns:
        True if full reclustering is recommended.
    """
    return runs_since_last >= 5


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Persistent Principle Index Manager (D2067)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="Initialize principles_index table")
    sub.add_parser("stats", help="Show index statistics")
    check_p = sub.add_parser("check", help="Check if a principle text is a duplicate (stdin)")
    check_p.add_argument("source_segment_id", type=str, help="Source segment ID")

    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        if args.command == "init":
            init_principles_index(conn)
            print("✅ principles_index table created.")

        elif args.command == "stats":
            init_principles_index(conn)
            stats = get_index_stats(conn)
            print(json.dumps(stats, indent=2))

        elif args.command == "check":
            init_principles_index(conn)
            text = sys.stdin.read().strip()
            if not text:
                print("ERROR: No text provided on stdin", file=sys.stderr)
                sys.exit(1)

            is_dup, reason = check_duplicate(conn, text, args.source_segment_id)
            if is_dup:
                print(f"DUPLICATE: {reason}")
                sys.exit(1)
            else:
                print("UNIQUE")
                sys.exit(0)

        else:
            parser.print_help()

    finally:
        conn.close()
