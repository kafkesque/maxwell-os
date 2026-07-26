#!/usr/bin/env python3
"""
stage6_commit.py — Commit verified FBs to SQLite + Parquet snapshot.
=====================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 6), §2.3

Input:  Verified FBs from Stage 5 checkpoint
Output: SQLite database (data/maxwell.db) + Parquet snapshot (data/parquet/)

Process:
  1. Load verified FBs from Stage 5
  2. Create/update SQLite schema (FTS5 for full-text search)
  3. Insert FBs with upsert (ON CONFLICT REPLACE by fb_id)
  4. Export Parquet snapshot with timestamp
  5. Write checkpoint

Schema:
  fbs table: All FB fields + verification results + stamps
  fbs_fts: FTS5 virtual table on name, definition, keywords

v2.0.1: Added domains_raw, discipline_raw columns (P1.5-A Channel B fix)

Usage:
    python3 pipeline/stage6_commit.py
    python3 pipeline/stage6_commit.py --export-only   # Only export Parquet snapshot
"""

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    DB_PATH,
    PARQUET_DIR,
    STAGE5_CHECKPOINT,
    STAGE5_HUMAN_REVIEW,
    STAGE6_CHECKPOINT,
)
from pipeline.schema_accessor import (
    fb_definition,
    fb_disciplines,
    fb_disciplines_raw,
    fb_domains,
    fb_id,
    fb_name,
    fb_source_books,
    fb_source_texts,
)
from pipeline.stamp import get_pipeline_commit, stamp_record

# ── SQLite schema ──────────────────────────────────────────────────────────

CREATE_FBS_TABLE = """
CREATE TABLE IF NOT EXISTS fbs (
    fb_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,
    application TEXT,
    failure_mode TEXT,
    elaboration TEXT,
    keywords TEXT,
    jargon TEXT,
    domains TEXT NOT NULL,         -- JSON array (canonical, validated)
    domains_raw TEXT,              -- JSON array (LLM original, preserved)
    disciplines TEXT NOT NULL,     -- JSON array (D2066 multi-label, 1-3)
    disciplines_raw TEXT,          -- JSON array (LLM original, preserved)
    depth TEXT NOT NULL,
    evidence TEXT NOT NULL,
    source_clusters TEXT,          -- JSON array
    source_books TEXT,             -- JSON array
    s3_original_domain TEXT,       -- Crawl provenance: domain folder
    classification_method TEXT,
    classification_errors TEXT,    -- JSON array
    verification_results TEXT,     -- JSON array
    borp_score REAL,
    status TEXT NOT NULL,
    needs_human_review INTEGER,
    verifier_model TEXT,
    schema_version TEXT,
    gen_model TEXT,
    pipeline_commit TEXT,
    taxonomy_version TEXT,
    pipeline_run_id TEXT,          -- UUID per pipeline run (lineage)
    created_at TEXT,
    committed_at TEXT
);
"""

CREATE_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS fbs_fts USING fts5(
    name,
    definition,
    keywords,
    content='fbs',
    content_rowid='rowid'
);
"""

CREATE_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS fbs_ai AFTER INSERT ON fbs BEGIN
    INSERT INTO fbs_fts(rowid, name, definition, keywords)
    VALUES (new.rowid, new.name, new.definition, new.keywords);
END;
"""

# BUG-004 FIX: Pre-compute embeddings at commit time for O(1) vector search.
CREATE_VEC_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS vec_fbs USING vec0(
    definition_embedding float[1024]
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database with schema."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    # P0.11 FIX: Load sqlite-vec extension BEFORE creating virtual tables.
    # Was: missing entirely, causing "no such module: vec0" on first run.
    try:
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except (ImportError, Exception) as e:
        print(f"  ⚠️  sqlite-vec not available: {e}")
        print("     Vector search will not be available. Install: pip install sqlite-vec")

    conn.execute(CREATE_FBS_TABLE)
    # BUG-004 FIX: Create vector embedding table (may fail if sqlite-vec not loaded)
    try:
        conn.execute(CREATE_VEC_TABLE)
    except Exception as e:
        print(f"  ⚠️  vec_fbs table not created (sqlite-vec unavailable): {e}")
    # FTS5 may not be compiled in all SQLite builds
    try:
        conn.execute(CREATE_FTS_TABLE)
        # BUG-025 FIX: Rebuild FTS from ALL existing fbs rows (was DELETE which lost history)
        try:
            conn.execute("INSERT INTO fbs_fts(fbs_fts) VALUES('rebuild')")
        except Exception:
            conn.execute("DELETE FROM fbs_fts")  # Fallback: clear + rebuild via triggers
        conn.executescript(CREATE_FTS_TRIGGERS)
    except sqlite3.OperationalError as e:
        print(f"  ⚠️  FTS5 not available: {e}")
        print("     Full-text search will not be available.")
    # Add new columns if upgrading from v2.0.0 (which lacked raw fields)
    _migrate_add_column(conn, "fbs", "domains_raw", "TEXT")
    _migrate_add_column(conn, "fbs", "disciplines_raw", "TEXT")   # D2066: was discipline_raw
    _migrate_add_column(conn, "fbs", "s3_original_domain", "TEXT")
    _migrate_add_column(conn, "fbs", "pipeline_run_id", "TEXT")
    return conn


def _migrate_add_column(conn, table, column, col_type):
    """Add a column if it doesn't exist (safe migration)."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # Column already exists


def _safe_str(val, default=""):
    """Convert a value to string. Handles dicts, lists, None."""
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    if not isinstance(val, str):
        return str(val)
    return val


def _safe_json(val, default=None):
    """Serialize to JSON string if dict/list, else return as-is."""
    if val is None:
        if default is not None:
            return json.dumps(default, ensure_ascii=False)
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return val


def insert_embedding(conn: sqlite3.Connection, rowid: int, definition: str) -> bool:
    """BUG-004 FIX: Pre-compute and store embedding for vector search.

    Embeds the definition once at commit time and stores in vec_fbs.
    Eliminates O(n) re-embedding on every search_vector() query.
    """
    try:
        import struct

        from pipeline.ollama_embed import batch_embed

        embeddings = batch_embed([definition])
        if not embeddings or not embeddings[0]:
            return False

        emb = embeddings[0]
        # Pack float32 array into binary blob for sqlite-vec
        blob = struct.pack(f'{len(emb)}f', *emb)
        conn.execute(
            "INSERT INTO vec_fbs(rowid, definition_embedding) VALUES (?, ?)",
            (rowid, blob),
        )
        return True
    except Exception:
        return False  # Non-critical — vector search will fall back to FTS


def insert_fb(conn: sqlite3.Connection, fb: dict) -> bool:
    """Insert or replace an FB into the database."""
    try:
        conn.execute("""
            INSERT OR REPLACE INTO fbs (
                fb_id, name, definition, application, failure_mode,
                elaboration, keywords, jargon,
                domains, domains_raw,
                disciplines, disciplines_raw,
                depth, evidence, source_clusters, source_books,
                s3_original_domain,
                classification_method, classification_errors,
                verification_results, borp_score, status,
                needs_human_review, verifier_model,
                schema_version, gen_model, pipeline_commit,
                taxonomy_version, pipeline_run_id,
                created_at, committed_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?
            )
        """, (
            _safe_str(fb_id(fb)),
            _safe_str(fb_name(fb)),
            _safe_str(fb_definition(fb)),
            _safe_str(fb.get("application"), ""),
            _safe_str(fb.get("failure_mode"), ""),
            _safe_str(fb.get("elaboration"), ""),
            _safe_str(fb.get("keywords"), ""),
            _safe_str(fb.get("jargon")),
            # domains (canonical + raw)
            _safe_json(fb_domains(fb)),
            _safe_json(fb.get("domains_raw")),
            # disciplines (canonical + raw) — D2066 multi-label
            _safe_json(fb_disciplines(fb)),
            _safe_json(fb_disciplines_raw(fb)),
            # depth, evidence, provenance
            _safe_str(fb_depth(fb), "domain"),
            _safe_str(fb_evidence_type(fb), "cited"),
            _safe_json(fb.get("source_clusters", [])),
            _safe_json(fb_source_books(fb)),
            # provenance
            _safe_str(fb.get("s3_original_domain")),
            # classification
            _safe_str(fb.get("classification_method"), ""),
            _safe_json(fb.get("classification_errors", [])),
            # verification
            _safe_json(fb.get("verification_results", [])),
            fb.get("borp_score", 0.0),
            _safe_str(fb.get("status"), "PENDING"),
            1 if fb.get("needs_human_review") else 0,
            _safe_str(fb.get("verifier_model")),
            # stamps
            _safe_str(fb.get("schema_version"), "2.0"),
            _safe_str(fb.get("gen_model")),
            _safe_str(fb.get("pipeline_commit"), "unknown"),
            _safe_str(fb.get("taxonomy_version"), "v5.0"),
            _safe_str(fb.get("pipeline_run_id")),
            _safe_str(fb.get("created_at"), ""),
            datetime.now(UTC).isoformat(),
        ))
        return True
    except Exception as e:
        print(f"  ❌ Insert failed: {e}")
        return False


def export_parquet(fbs: list[dict], parquet_dir: Path) -> Path:
    """Export FBs to Parquet snapshot."""
    parquet_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parquet_path = parquet_dir / f"fbs_snapshot_{timestamp}.parquet"

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        # Flatten JSON arrays/dicts to strings for Parquet compatibility
        rows = []
        jsonlike_fields = {
            "domains", "domains_raw", "source_clusters", "source_books",
            "verification_results", "classification_errors",
            "jargon",
        }
        for fb in fbs:
            row = dict(fb)
            for field in jsonlike_fields:
                val = row.get(field)
                if isinstance(val, (list, dict)):
                    row[field] = json.dumps(val, ensure_ascii=False)
                elif val is None and field not in ("jargon", "domains_raw", "discipline_raw"):
                    row[field] = "[]"
            rows.append(row)

        table = pa.Table.from_pylist(rows)
        pq.write_table(table, str(parquet_path), compression="snappy")
        return parquet_path
    except ImportError:
        print("  ⚠️  pyarrow not installed. Skipping Parquet export.")
        print("     Install: pip install pyarrow")
        return None


def load_stage5_fbs() -> list[dict]:
    """Load verified FBs from Stage 5 checkpoint."""
    if not STAGE5_CHECKPOINT.exists():
        print("❌ Stage 5 checkpoint not found. Run stage5_verify.py first.")
        sys.exit(1)

    fbs = []
    with open(STAGE5_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                fbs.append(json.loads(line))
    return fbs


def run_stage6(export_only: bool = False):
    """Run Stage 6: Commit FBs to SQLite + Parquet."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    fbs = load_stage5_fbs()

    print(f"💾 Stage 6: Commit — {len(fbs)} verified FBs")
    print(f"{'='*60}")

    pipeline_commit = get_pipeline_commit()

    # SQLite
    conn = init_db(DB_PATH)
    inserted = 0
    failed = 0

    if not export_only:
        for i, fb in enumerate(fbs, 1):
            name = fb_name(fb)[:40]
            if insert_fb(conn, fb):
                inserted += 1
                # BUG-004 FIX: Pre-compute embedding at commit time
                definition = fb_definition(fb)
                if definition:
                    rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    insert_embedding(conn, rowid, definition)
            else:
                failed += 1
                print(f"  [{i}] Failed: {name}")

        conn.commit()

        # Count
        count = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
        print(f"  ✅ SQLite: {inserted} inserted, {failed} failed, {count} total rows")
    else:
        count = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
        print(f"  ℹ️  SQLite: {count} existing rows (--export-only)")

    conn.close()

    # Parquet export
    parquet_path = export_parquet(fbs, PARQUET_DIR)
    if parquet_path:
        size_kb = parquet_path.stat().st_size / 1024
        print(f"  ✅ Parquet: {parquet_path.name} ({size_kb:.1f} KB)")

    # Write checkpoint (commit record)
    commit_recs = []
    for fb in fbs:
        rec = stamp_record({
            "fb_id": fb["fb_id"],
            "name": fb["name"],
            "status": fb.get("status"),
            "committed_to_sqlite": not export_only,
            "parquet_snapshot": str(parquet_path) if parquet_path else None,
        }, gen_model="python")
        rec["pipeline_commit"] = pipeline_commit
        commit_recs.append(rec)

    safe_write(
        STAGE6_CHECKPOINT,
        "\n".join(json.dumps(r, ensure_ascii=False) for r in commit_recs) + "\n",
    )

    # ── D2066: Dynamic taxonomy post-commit ──────────────────────────
    if not export_only:
        try:
            from pipeline.taxonomy_manager import run_post_commit_taxonomy
            # Write human review files alongside Stage 5 review artifacts
            human_review_dir = STAGE5_HUMAN_REVIEW.parent
            taxonomy_review = run_post_commit_taxonomy(conn, human_review_dir)
            if taxonomy_review:
                print(f"\n⏸️  TAXONOMY REVIEW REQUIRED (C8-G1): {taxonomy_review}")
                print("   Review the candidates, set 'approved': true/false, then run:")
                print(f"   python3 pipeline/taxonomy_manager.py --apply {taxonomy_review}")
                print("   C8-G2: After applying, review the generated taxonomy YAML before activating.")
            else:
                print("\n✅ No taxonomy replacements needed.")
        except Exception as e:
            print(f"\n⚠️  Taxonomy post-commit hook failed (non-fatal): {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Committed: {len(fbs)} FBs")
    print(f"🗄️  Database:  {DB_PATH}")
    if parquet_path:
        print(f"📦 Parquet:   {parquet_path}")
    print(f"📋 Checkpoint: {STAGE6_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(description="Stage 6: Commit FBs → SQLite + Parquet")
    parser.add_argument("--export-only", action="store_true",
                        help="Only export Parquet snapshot (don't modify DB)")
    args = parser.parse_args()

    run_stage6(export_only=args.export_only)


if __name__ == "__main__":
    main()
