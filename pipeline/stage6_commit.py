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
    S15_EMBED_DIM,
    S6_MAX_FAILED_RATIO,  # D2338: fail-closed commit tolerance
    STAGE5_CHECKPOINT,
    STAGE5_HUMAN_REVIEW,
    STAGE6_CHECKPOINT,
)
from pipeline.schema_accessor import (
    fb_accessibility,
    fb_context,
    fb_definition,
    fb_depth,
    fb_discipline,
    fb_discipline_raw,
    fb_domains,
    fb_evidence_type,
    fb_id,
    fb_intimacy_boundary,
    fb_name,
    fb_provenance,
    fb_source_books,
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
    -- D2337: D2323 two-axis ontology + mechanism/boundary/consequence (was silently dropped at S4→S6)
    content_type TEXT,
    extraction_type TEXT,
    mechanism TEXT,
    boundary TEXT,
    consequence TEXT,
    taxonomy_match_method TEXT,
    keywords TEXT,
    jargon TEXT,
    -- Classification (D316: discipline singular, D150: domains multi-label)
    domains TEXT NOT NULL,         -- JSON array (canonical, 1-5)
    domains_raw TEXT,              -- JSON array (LLM original, preserved)
    discipline TEXT NOT NULL,      -- SINGULAR canonical discipline (D316)
    discipline_raw TEXT,           -- LLM original, preserved (singular)
    depth TEXT NOT NULL,
    evidence TEXT NOT NULL,
    -- v1 Anytype properties (parity)
    context TEXT,                  -- comma-separated: business,design,system,academic,personal
    accessibility TEXT,            -- self-evident | prerequisite
    intimacy_boundary TEXT,        -- public | selective | private (space routing)
    provenance TEXT NOT NULL DEFAULT 'llm_extracted_from_source',  -- C29: provenance tier
    source_text TEXT,              -- concatenated source paragraph text for verification (D2131)
    is_summary INTEGER DEFAULT 0,  -- D2089: 1=summary (not actionable), 0=principle
    -- Agentic metadata (D2130)
    difficulty_level TEXT,         -- beginner | intermediate | expert
    temporal_scope TEXT,           -- timeless | contemporary | era-specific
    confidence_score REAL,         -- from Stage 5 verification
    prerequisite_fbs TEXT,         -- JSON array of FB IDs
    procedural_skill TEXT,         -- agent tool/function name
    contradicts_fbs TEXT,          -- JSON array of conflicting FB IDs
    related_fbs TEXT,              -- JSON array of relationship edges (P1.4)
    -- Utilization tracking
    usage_count INTEGER DEFAULT 0,
    last_retrieved_at TEXT,
    feedback_score REAL,           -- aggregated agent feedback 0-1
    feedback_count INTEGER DEFAULT 0,
    fb_version INTEGER DEFAULT 1,
    -- Provenance (simplified — bloat removed per D2130)
    source_clusters TEXT,          -- JSON array (hash strings)
    source_books TEXT,             -- JSON array
    source_principle_ids TEXT,     -- JSON array (references, not embedded)
    classification_errors TEXT,    -- JSON array or NULL
    classification_status TEXT NOT NULL DEFAULT 'CLEAN',  -- D2184: CLEAN | FALLBACK | FAILED (monotonic trust)
    -- Verification (from Stage 5)
    verification_results TEXT,     -- JSON array
    borp_score REAL,
    status TEXT NOT NULL,
    needs_human_review INTEGER,
    verifier_model TEXT,
    -- Stamps (R14)
    schema_version TEXT,
    gen_model TEXT,
    pipeline_commit TEXT,
    taxonomy_version TEXT,
    pipeline_run_id TEXT,
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

# D2229: Embedding dimension read from config (D2181 Matryoshka 512d bge-m3).
# Previously hardcoded float[1024] — runtime failure when embed_dim=512.
CREATE_VEC_TABLE = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS vec_fbs USING vec0(
    definition_embedding float[{S15_EMBED_DIM}]
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
    # Add new columns if upgrading from older schema versions
    _migrate_add_column(conn, "fbs", "domains_raw", "TEXT")
    _migrate_add_column(conn, "fbs", "discipline_raw", "TEXT")  # D316: singular
    _migrate_add_column(conn, "fbs", "s3_original_domain", "TEXT")
    _migrate_add_column(conn, "fbs", "pipeline_run_id", "TEXT")
    # v1 parity columns
    _migrate_add_column(conn, "fbs", "context", "TEXT")
    _migrate_add_column(conn, "fbs", "accessibility", "TEXT")
    _migrate_add_column(conn, "fbs", "intimacy_boundary", "TEXT")
    _migrate_add_column(conn, "fbs", "provenance", "TEXT")
    _migrate_add_column(conn, "fbs", "source_text", "TEXT")  # D2131
    # D2337: D2323 two-axis ontology + mechanism/boundary/consequence (was silently dropped)
    _migrate_add_column(conn, "fbs", "content_type", "TEXT")
    _migrate_add_column(conn, "fbs", "extraction_type", "TEXT")
    _migrate_add_column(conn, "fbs", "mechanism", "TEXT")
    _migrate_add_column(conn, "fbs", "boundary", "TEXT")
    _migrate_add_column(conn, "fbs", "consequence", "TEXT")
    _migrate_add_column(conn, "fbs", "taxonomy_match_method", "TEXT")
    return conn


def _migrate_add_column(conn, table, column, col_type):
    """Add a column if it doesn't exist (safe migration)."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # Column already exists


def _get_pipeline_version() -> str:
    """Read pipeline version from config/version.yaml (D2169: single source of truth)."""
    try:
        import yaml
        vcfg = yaml.safe_load(Path("config/version.yaml").read_text())
        return str(vcfg.get("pipeline_version", "3.0"))
    except Exception:
        return "3.0"


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
    """Insert or replace an FB into the database (D2130 schema)."""
    try:
        conn.execute("""
            INSERT OR REPLACE INTO fbs (
                fb_id, name, definition, application, failure_mode,
                elaboration, content_type, extraction_type, mechanism,
                boundary, consequence, taxonomy_match_method, keywords, jargon,
                domains, domains_raw,
                discipline, discipline_raw,
                depth, evidence,
                context, accessibility, intimacy_boundary, provenance,
                source_text,
                difficulty_level, temporal_scope, confidence_score,
                prerequisite_fbs, procedural_skill,
                contradicts_fbs, related_fbs,
                usage_count, last_retrieved_at,
                feedback_score, feedback_count, fb_version,
                source_clusters, source_books, source_principle_ids,
                classification_errors,
                verification_results, borp_score, status,
                needs_human_review, verifier_model,
                schema_version, gen_model, pipeline_commit,
                taxonomy_version, pipeline_run_id,
                s3_original_domain,
                created_at, committed_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?,
                ?, ?
            )
        """, (
            _safe_str(fb_id(fb)),
            _safe_str(fb_name(fb)),
            _safe_str(fb_definition(fb)),
            _safe_str(fb.get("application"), ""),
            _safe_str(fb.get("failure_mode"), ""),
            _safe_str(fb.get("elaboration"), ""),
            _safe_str(fb.get("content_type"), ""),
            _safe_str(fb.get("extraction_type"), ""),
            _safe_str(fb.get("mechanism"), ""),
            _safe_str(fb.get("boundary"), ""),
            _safe_str(fb.get("consequence"), ""),
            _safe_str(fb.get("taxonomy_match_method"), ""),
            _safe_str(fb.get("keywords"), ""),
            _safe_str(fb.get("jargon")),
            # domains + discipline (canonical + raw) — D316: discipline singular
            _safe_json(fb_domains(fb)),
            _safe_json(fb.get("domains_raw")),
            _safe_str(fb_discipline(fb), "emerging"),
            _safe_str(fb_discipline_raw(fb)),
            # depth, evidence
            _safe_str(fb_depth(fb), "domain"),
            _safe_str(fb_evidence_type(fb), "cited"),
            # v1 Anytype properties
            _safe_str(fb_context(fb)),
            _safe_str(fb_accessibility(fb)),
            _safe_str(fb_intimacy_boundary(fb)),
            _safe_str(fb_provenance(fb), "llm_extracted_from_source"),
            # source text for verification (D2131)
            _safe_str(fb.get("source_text")),
            # agentic metadata (D2130)
            _safe_str(fb.get("difficulty_level")),
            _safe_str(fb.get("temporal_scope")),
            fb.get("confidence_score"),
            _safe_json(fb.get("prerequisite_fbs")),
            _safe_str(fb.get("procedural_skill")),
            _safe_json(fb.get("contradicts_fbs")),
            _safe_json(fb.get("related_fbs")),
            # utilization tracking
            fb.get("usage_count", 0),
            _safe_str(fb.get("last_retrieved_at")),
            fb.get("feedback_score"),
            fb.get("feedback_count", 0),
            fb.get("fb_version", 1),
            # provenance (simplified)
            _safe_json(fb.get("source_clusters", [])),
            _safe_json(fb_source_books(fb)),
            _safe_json(fb.get("source_principle_ids", [])),
            # classification errors
            _safe_json(fb.get("classification_errors")),
            # verification
            _safe_json(fb.get("verification_results", [])),
            fb.get("borp_score", 0.0),
            _safe_str(fb.get("status"), "PENDING"),
            1 if fb.get("needs_human_review") else 0,
            _safe_str(fb.get("verifier_model")),
            # stamps
            # D2169: Read schema version from config/version.yaml (single source of truth)
            _safe_str(fb.get("schema_version"), _get_pipeline_version()),
            _safe_str(fb.get("gen_model")),
            _safe_str(fb.get("pipeline_commit"), "unknown"),
            _safe_str(fb.get("taxonomy_version"), "v5.0"),
            _safe_str(fb.get("pipeline_run_id")),
            _safe_str(fb.get("s3_original_domain"), ""),
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
            "jargon", "source_principle_ids",
            "prerequisite_fbs", "contradicts_fbs", "related_fbs",
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
    # D2325: per-FB commit status — INSERTED/FAILED/SKIPPED. Replaces the blanket
    # `committed_to_sqlite = not export_only` stamp that falsely recorded a failed
    # row as committed (C16 provenance truthfulness).
    commit_status: dict[str, str] = {}

    if not export_only:
        for i, fb in enumerate(fbs, 1):
            name = fb_name(fb)[:40]
            if insert_fb(conn, fb):
                inserted += 1
                commit_status[fb["fb_id"]] = "INSERTED"
                # BUG-004 FIX: Pre-compute embedding at commit time
                definition = fb_definition(fb)
                if definition:
                    rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    insert_embedding(conn, rowid, definition)
            else:
                failed += 1
                commit_status[fb["fb_id"]] = "FAILED"
                print(f"  [{i}] Failed: {name}")

        conn.commit()

        # Count
        count = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
        print(f"  ✅ SQLite: {inserted} inserted, {failed} failed, {count} total rows")

        # ── D2185: Vector embedding completeness check (R-016) ──
        vec_count = 0
        try:
            vec_count = conn.execute("SELECT COUNT(*) FROM vec_fbs").fetchone()[0]
        except Exception:
            pass
        if vec_count == 0:
            print("  ⚠️  Vector: DEGRADED — 0 embeddings (sqlite-vec may be unavailable)")
        elif vec_count < count:
            pct = round(vec_count / count * 100, 1)
            print(f"  ⚠️  Vector: DEGRADED {vec_count}/{count} ({pct}%)")
        else:
            print(f"  ✅ Vector: READY {vec_count}/{count}")

        # ── D2185: vec_fbs ↔ fbs rowid reconciliation (R-017) ──
        try:
            orphaned = conn.execute("""
                SELECT COUNT(*) FROM vec_fbs v
                LEFT JOIN fbs f ON v.rowid = f.rowid
                WHERE f.rowid IS NULL
            """).fetchone()[0]
            if orphaned > 0:
                print(f"  ⚠️  Orphaned vector rows: {orphaned} (run reconcile)")
        except Exception:
            pass

        # ── D2066: Dynamic taxonomy post-commit (BEFORE conn.close) ──
        try:
            from pipeline.taxonomy_manager import run_post_commit_taxonomy
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

        conn.close()
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
    # D2325: per-FB INSERTED/FAILED/SKIPPED — never claim a failed row was committed.
    commit_recs = []
    for fb in fbs:
        fb_id: str = fb["fb_id"]
        if export_only:
            per_fb_status: str = "SKIPPED"
        else:
            per_fb_status = commit_status.get(fb_id, "FAILED")  # untracked → FAILED (fail-closed)
        rec = stamp_record({
            "fb_id": fb_id,
            "name": fb["name"],
            "status": fb.get("status"),
            "commit_status": per_fb_status,
            "committed_to_sqlite": per_fb_status == "INSERTED",
            "parquet_snapshot": str(parquet_path) if parquet_path else None,
        }, gen_model="python")
        rec["pipeline_commit"] = pipeline_commit
        commit_recs.append(rec)

    safe_write(
        STAGE6_CHECKPOINT,
        "\n".join(json.dumps(r, ensure_ascii=False) for r in commit_recs) + "\n",
    )

    # Summary
    print(f"\n{'='*60}")
    if export_only:
        print(f"📦 Parquet-only: {len(fbs)} FBs (SQLite SKIPPED)")
    else:
        print(f"✅ Committed to SQLite: {inserted} FBs")
        if failed:
            print(f"❌ Failed to commit:    {failed} FBs (checkpoint commit_status=FAILED)")
    print(f"🗄️  Database:  {DB_PATH}")
    if parquet_path:
        print(f"📦 Parquet:   {parquet_path}")
    print(f"📋 Checkpoint: {STAGE6_CHECKPOINT}")

    # ── D2338: fail-closed commit ───────────────────────────────────────────
    # insert_fb() returns False on exception and run_stage6() previously printed
    # the failure but exited 0 — the runner then wrote a COMPLETE manifest despite
    # permanent data loss. Now a partial commit never looks like success.
    if not export_only and len(fbs) > 0:
        failure_ratio: float = failed / len(fbs)
        if failure_ratio > S6_MAX_FAILED_RATIO:
            print(f"❌ Stage 6 FAILED: {failed}/{len(fbs)} FBs failed commit "
                  f"({failure_ratio:.1%} > max_failed_ratio={S6_MAX_FAILED_RATIO}). "
                  f"Failed inserts = permanent data loss — do NOT mark COMPLETE.")
            sys.exit(1)
        if failed > 0:
            print(f"⚠️  Stage 6 CONDITIONAL_SUCCESS: {failed} FB(s) failed within "
                  f"tolerance ({failure_ratio:.1%} ≤ {S6_MAX_FAILED_RATIO}). Re-run to retry failed FBs.")
            sys.exit(2)  # non-zero → runner does NOT auto-advance / mark COMPLETE


def main():
    parser = argparse.ArgumentParser(description="Stage 6: Commit FBs → SQLite + Parquet")
    parser.add_argument("--export-only", action="store_true",
                        help="Only export Parquet snapshot (don't modify DB)")
    args = parser.parse_args()

    run_stage6(export_only=args.export_only)


if __name__ == "__main__":
    main()
