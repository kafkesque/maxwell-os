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
import os
import sqlite3
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    DB_PATH,
    CANONICAL_RUN,  # D-2881: canonical pipeline_run_id (D-2884a backfill scoping)
    PARQUET_DIR,
    S15_EMBED_DIM,
    S4_DIR,  # D2590: S4 run dir — home of the non-principle sidecars S6 must ingest
    S4_GE_OUTPUT,
    S4_PI_OUTPUT,
    S4_PT_OUTPUT,
    S4_QUARANTINE_OUTPUT,  # D2616: the HOLD shelf — never a commit source
    S4_TI_OUTPUT,
    S6_COMMIT_NON_FB,  # D2590: the flag that was DEAD config until this build
    S6_MAX_FAILED_RATIO,  # D2338: fail-closed commit tolerance
    S6_COMMIT_SCOPE,  # D-2933 (rule V): verification-scoped commit
    S6_S5_OWNED_COLUMNS,  # D-2933: the S5-owned provenance column set (C12)
    S6_TAXONOMY_DEPENDENT_COLUMNS,  # D-2934: column-scoped taxonomy-skew guard
    S6_VEC_REQUIRE,  # D-2717: fail-closed vec0 gate (C16)
    S6_DEDUP_GATE_ENABLED,  # D-2951 (D-2949 prevention half): commit-time dedup gate
    S6_DEDUP_GATE_MODE,  # D-2951: report | enforce — validated fail-closed in run_stage6 (C16)

    STAGE5_CHECKPOINT,
    STAGE5_HUMAN_REVIEW,
    STAGE6_CHECKPOINT,
)
from pipeline.content_types import leaf_label_fault  # D-2965: the leaf-label ADMISSION rule (one home, C21)
from pipeline.content_types import type_body_fields  # D-2943: the role->body-field ontology (C21)
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
    fb_source_ids,
)
from pipeline.serving_gate import (  # D274a/D274h: the pre-write half of the gate
    content_types_without_factual_claim,  # D-2942: the roles with no NLI factual claim (C12)
    derive_status,  # D-2942/D274h: the ONE status rule — S6 stamps its output, never a literal
    pre_write_verdict,
)
from pipeline.dedup_gate import (  # D-2951: commit-time dedup gate (D-2949 prevention half)
    CommitDedupGate,
    duplicate_marker,
    load_committed_index,
)
from pipeline.discipline_macro import macro_for  # D-2884(a): C21 single home for fine->macro collapse
from pipeline.stamp import get_pipeline_commit, stamp_record, write_stage_code_fingerprint
from pipeline.sqlite_vec_loader import load_sqlite_vec  # D-2915: shared sqlite-vec loader (ctypes fallback)
from pipeline.schemas import (  # D2616 Phase 0: runtime ontology boundary
    validate_fb_content_type,
    validate_fb_depth,
    validate_discipline_domain,  # D2620/D2626: discipline<->domain non-contamination (fail-closed)
)

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
    content_type_source TEXT,      -- C29 provenance tier for content_type (R1/D-279)
    discipline_source TEXT,        -- C29 provenance tier for discipline (R1/D-279)
    extraction_type_source TEXT,   -- C29 provenance tier for extraction_type (R1/D-279)
    menu_hash TEXT,                -- SHA-256 of closed menu at classification time (R1/D-279)
    keywords TEXT,
    jargon TEXT,
    -- Classification (D316: discipline singular, D150: domains multi-label)
    domains TEXT NOT NULL,         -- JSON array (canonical, 1-7)
    domains_raw TEXT,              -- JSON array (LLM original, preserved)
    discipline TEXT NOT NULL,      -- SINGULAR canonical discipline (D316)
    discipline_raw TEXT,           -- LLM original, preserved (singular)
    discipline_macro TEXT,         -- D-2884(a): operative 3-way macro routing facet (Technical/Human & Design/Method & Business/emerging); fine discipline is ADVISORY-only
    depth TEXT NOT NULL,
    evidence TEXT NOT NULL,
    -- v1 Anytype properties (parity)
    context TEXT,                  -- comma-separated: business,design,system,academic,personal
    accessibility TEXT,            -- self-evident | prerequisite
    intimacy_boundary TEXT,        -- public | selective | private (space routing)
    provenance TEXT NOT NULL DEFAULT 'llm_extracted_from_source',  -- C29: provenance tier
    source_text TEXT,              -- concatenated source paragraph text for verification (D2131)
    is_summary INTEGER DEFAULT 0,  -- D2089: 1=summary (not actionable), 0=principle
    -- D2439: structural evidence tier (convergence axis) — convergent|single_source|singleton
    is_convergent INTEGER DEFAULT 0,  -- 1 = cross-source convergent cluster (>=2 sources)
    origin TEXT DEFAULT 'single_source',  -- convergent | single_source | singleton
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
    source_ids TEXT,               -- JSON array (canonical SHA-256 author|title, D2176/D2376)
    citation TEXT,                 -- bibliographic citation string (S2 provenance, was dropped at S4)
    source_authors TEXT,           -- JSON array of {book, author, title, year} (S2 provenance)
    source_diversity INTEGER,      -- distinct-source count (S2 epistemic diversity)
    primary_source TEXT,           -- JSON object {book, reason} (S2 provenance)
    source_principle_ids TEXT,     -- JSON array (references, not embedded)
    source_segments TEXT,          -- JSON array of segment_ids (D2352/BUG-110 — was dropped at S4)
    evidence_passages TEXT,        -- JSON array of verbatim quotes (D2352/BUG-111)
    evidence_passages_shown TEXT,  -- JSON array (subset actually shown to the LLM)
    classification_errors TEXT,    -- JSON array or NULL
    classification_status TEXT NOT NULL DEFAULT 'CLEAN',  -- D2184: CLEAN | FALLBACK | FAILED (monotonic trust)
    classification_error TEXT,     -- D2351: failure reason when status != CLEAN
    -- Verification (from Stage 5)
    verification_results TEXT,     -- JSON array
    borp_score REAL,
    status TEXT NOT NULL,
    needs_human_review INTEGER,
    verifier_model TEXT,
    s5_reason TEXT,             -- G19/D274h: typed S5 verdict (entail|neutral|contra|no_evidence|mech_fail|vacuous|evidence_contaminated|duplicate)
    epistemic_status TEXT,      -- G19/F-43: S5 tier (corroborated|source-supported|cross-source-unverified|speculative)
    verification_method TEXT,   -- G19/F-43: S5 verification method
    isor TEXT,                  -- G19/F-43: full ISOR scores (JSON) from S5
    practicality TEXT,          -- D2622: advisory applicability tier (immediately-applicable|context-dependent|abstract)
    type_body TEXT,             -- D2590/D-2943: JSON object holding the ROLE-specific body the store has no
                                -- column for (PT trigger/prerequisite/steps/done_condition; PI instance_text/actors/
                                -- outcome_*/domain_context; TI tool_name/platform/description/syntax/parameters/
                                -- output/example/caveats; GE body/category/actionable/status/priority). NULL for a
                                -- role that declares no body beyond core_body (principle). Field list comes from
                                -- config/content_types.yaml::s2_body_fields minus core_body — never re-declared here.
    -- Stamps (R14)
    schema_version TEXT,
    gen_model TEXT,
    pipeline_commit TEXT,
    taxonomy_version TEXT,
    pipeline_run_id TEXT,
    created_at TEXT,
    committed_at TEXT,
    duplicate_of TEXT            -- D2627: canonical fb_id when this row is a dedup (NULL otherwise); QUARANTINE = separate from main checkpoints, NEVER delete
);
"""

CREATE_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS fbs_fts USING fts5(
    name,
    definition,
    keywords,
    jargon,
    content='fbs',
    content_rowid='rowid'
);
"""

CREATE_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS fbs_ai AFTER INSERT ON fbs BEGIN
    INSERT INTO fbs_fts(rowid, name, definition, keywords, jargon)
    VALUES (new.rowid, new.name, new.definition, new.keywords, new.jargon);
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
    # BUG-104: distinguish ImportError (package missing) from AttributeError
    # (load_extension unavailable on python.org framework builds) — the broad
    # `except (ImportError, Exception)` masked the real remediation.
    # D-2717/D-2915: track vec0 load success for the fail-closed gate (C16).
    _vec = load_sqlite_vec(conn)
    _vec_loaded = _vec.loaded
    if not _vec.loaded:
        print(f"  ⚠️  sqlite-vec unavailable: {_vec.error}")
        print("     Vector search unavailable; FTS retrieval still works. For a")
        print("     vec0-capable interpreter see stage6.vec_python (Homebrew/conda Python).")

    if S6_VEC_REQUIRE and not _vec_loaded:
        raise RuntimeError(
            "stage6.vec_require=true but sqlite-vec/vec0 failed to load. "
            "Run this stage under a vec0-capable Python (see stage6.vec_python; "
            "Homebrew 3.14.6 verified) or set stage6.vec_require=false to accept "
            "FTS-only (non-gating, D2185)."
        )
    conn.execute(CREATE_FBS_TABLE)
    # BUG-004 FIX: Create vector embedding table (may fail if sqlite-vec not loaded)
    try:
        conn.execute(CREATE_VEC_TABLE)
    except Exception as e:
        print(f"  ⚠️  vec_fbs table not created (sqlite-vec unavailable): {e}")
    # FTS5 may not be compiled in all SQLite builds
    try:
        conn.execute(CREATE_FTS_TABLE)
        # BUG-119: FTS index now includes `jargon` (specialized terminology).
        # Existing DBs were created with a 3-column fbs_fts (name, definition,
        # keywords). CREATE IF NOT EXISTS will NOT add the jargon column, and the
        # new 5-column trigger would then fail. Detect the old shape and rebuild.
        try:
            fts_cols = {r[1] for r in conn.execute("PRAGMA table_info(fbs_fts)").fetchall()}
            if "jargon" not in fts_cols:
                conn.execute("DROP TABLE IF EXISTS fbs_fts")
                conn.execute(CREATE_FTS_TABLE)
        except Exception:
            pass  # PRAGMA unsupported on this FTS build — leave as-is
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
    _migrate_add_column(conn, "fbs", "discipline_macro", "TEXT")  # D-2884(a): operative 3-way macro routing facet
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
    # R1/D-279: closed-menu traceability + per-axis label provenance (menu_hash + *_source).
    _migrate_add_column(conn, "fbs", "content_type_source", "TEXT")
    _migrate_add_column(conn, "fbs", "discipline_source", "TEXT")
    _migrate_add_column(conn, "fbs", "extraction_type_source", "TEXT")
    _migrate_add_column(conn, "fbs", "menu_hash", "TEXT")
    # D2352: provenance/schema contract closure — segment provenance + verbatim evidence
    _migrate_add_column(conn, "fbs", "source_segments", "TEXT")
    # D2376: canonical source identity (D2176) — was dropped at S4, now persisted
    _migrate_add_column(conn, "fbs", "source_ids", "TEXT")
    # F1: S2 provenance carry-through — was dropped at S4, now persisted
    _migrate_add_column(conn, "fbs", "citation", "TEXT")
    _migrate_add_column(conn, "fbs", "source_authors", "TEXT")
    _migrate_add_column(conn, "fbs", "source_diversity", "INTEGER")
    _migrate_add_column(conn, "fbs", "primary_source", "TEXT")
    _migrate_add_column(conn, "fbs", "evidence_passages", "TEXT")
    _migrate_add_column(conn, "fbs", "evidence_passages_shown", "TEXT")
    # D2351: fail-closed observability — reason a row is not CLEAN
    _migrate_add_column(conn, "fbs", "classification_error", "TEXT")
    # D2386-fix (2026-08-16): is_summary (D2089) + classification_status (D2184) were
    # added to CREATE TABLE but NOT to the _migrate_add_column list — pre-existing DBs
    # never got them, so S6 INSERT failed 278/278 ("no column named is_summary").
    # Auto-heal both columns now.
    _migrate_add_column(conn, "fbs", "is_summary", "INTEGER DEFAULT 0")
    _migrate_add_column(conn, "fbs", "classification_status", "TEXT NOT NULL DEFAULT 'CLEAN'")
    # D2439: structural evidence tier (convergence axis) — auto-heal for pre-existing DBs
    _migrate_add_column(conn, "fbs", "is_convergent", "INTEGER DEFAULT 0")
    _migrate_add_column(conn, "fbs", "origin", "TEXT DEFAULT 'single_source'")
    # D2627: dedup marker — canonical fb_id when this row is a duplicate (NULL otherwise)
    _migrate_add_column(conn, "fbs", "duplicate_of", "TEXT")
    # G19/F-43 + s5_reason (D274h): persist the S5 verification tier that stage6 previously dropped.
    _migrate_add_column(conn, "fbs", "s5_reason", "TEXT")
    _migrate_add_column(conn, "fbs", "epistemic_status", "TEXT")
    _migrate_add_column(conn, "fbs", "verification_method", "TEXT")
    _migrate_add_column(conn, "fbs", "isor", "TEXT")
    _migrate_add_column(conn, "fbs", "practicality", "TEXT")
    # D2590/D-2943: the non-principle commit tier's role-specific body (ONE JSON column, not one
    # column per role-field). Auto-heal for pre-existing DBs, exactly like every column above.
    _migrate_add_column(conn, "fbs", "type_body", "TEXT")
    # D2395: drop dead legacy s3_original_domain (stage3 removed in D2130; the column was
    # never dropped from existing DBs). Drift → 61 DB cols vs 60 in CREATE TABLE/INSERT,
    # tripping integrity-check [8]. Dropping re-aligns; no active code reads the column.
    _migrate_drop_column(conn, "fbs", "s3_original_domain")
    return conn


def _migrate_add_column(conn, table, column, col_type):
    """Add a column if it doesn't exist (safe migration)."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass  # Column already exists


def _migrate_drop_column(conn, table, column):
    """Drop a legacy column if it exists (safe migration, SQLite >=3.35).

    D2395: dead columns left in the DB (e.g. s3_original_domain from the removed
    stage3, D2130) make the DB column count drift from CREATE TABLE/INSERT, which
    integrity-check [8] flags. Dropping the dead column re-aligns them.
    """
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
    if column in cols:
        conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")


def _backfill_discipline_macro(conn: sqlite3.Connection) -> int:
    """D-2884(a): idempotently backfill fbs.discipline_macro for the canonical run.

    The operative 3-way macro routing facet (Technical / Human & Design /
    Method & Business / emerging) is a deterministic collapse of each row's fine
    `discipline`, computed via the C21 single home (pipeline.discipline_macro.macro_for).
    Scoped to the canonical run only (D-2881): the stale non-canonical rows are never
    served (BUG-691) and correctly keep NULL rather than being imputed. Only NULL/blank
    cells are filled, so re-runs are no-ops.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    if "discipline_macro" not in cols:
        return 0
    rows = conn.execute(
        "SELECT fb_id, discipline FROM fbs "
        "WHERE pipeline_run_id = ? AND (discipline_macro IS NULL OR discipline_macro = '')",
        (CANONICAL_RUN,),
    ).fetchall()
    for fb_id, discipline in rows:
        conn.execute(
            "UPDATE fbs SET discipline_macro = ? WHERE fb_id = ?",
            (macro_for(discipline), fb_id),
        )
    return len(rows)


def _get_pipeline_version() -> str:
    """Read pipeline version from config/version.yaml (D2169: single source of truth)."""
    try:
        import yaml
        vcfg = yaml.safe_load(Path("config/version.yaml").read_text())
        return str(vcfg.get("pipeline_version", "3.0"))
    except Exception as e:
        print(f"   ⚠️  stage6: version.yaml unreadable ({type(e).__name__}: {e}) — fallback '3.0' (C16)", file=sys.stderr)
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


def fbs_rowid(conn: sqlite3.Connection, fb_id: str | None) -> int | None:
    """Return the stored fbs rowid for an fb_id, or None when it is not there yet.

    BUG-387/D-359: fbs' primary key is the TEXT `fb_id`, so `INSERT OR REPLACE`
    deletes the conflicting row and inserts a NEW one, which re-issues the
    implicit rowid. The vec store is keyed by that rowid, so a re-commit moves
    the spine and leaves the previous rowid's vector behind as a dead index
    entry. Capturing the rowid BEFORE the insert is what makes that visible.
    """
    if not fb_id:
        return None
    row = conn.execute("SELECT rowid FROM fbs WHERE fb_id = ?", (str(fb_id),)).fetchone()
    return int(row[0]) if row else None


def delete_embedding(conn: sqlite3.Connection, rowid: int) -> bool:
    """Delete one rowid's vector from vec_fbs (no-op when the rowid is absent).

    Returns False when the vec0 module is unavailable (BUG-104) or the delete
    failed — a caller performing a BUG-387 repair must not read False as success
    (C16). vec0 exposes DELETE by rowid, so this needs no vec0-specific module.
    """
    try:
        conn.execute("DELETE FROM vec_fbs WHERE rowid = ?", (int(rowid),))
        return True
    except Exception as e:
        print(f"  ⚠️  Embedding delete failed (rowid={rowid}): {e}")
        return False


def assert_vector_integrity(conn: sqlite3.Connection) -> tuple[bool, str]:
    """ROWID-level vector completeness assertion (D2185 R-016/R-017, BUG-387/D-359).

    Returns (ok, message). `ok` is False only for ORPHANS: index entries whose
    fbs row no longer exists. Those are dead k-NN slots — the index still
    answers, so retrieval looks fine while results are silently diluted, which
    is why a COUNT cannot see them (it printed "Vector: READY 15990/7995" on a
    store where half the entries were dead).

    A MISSING entry (fbs row with no vector) is reported as DEGRADED but is not
    corruption: that row still answers through FTS. An absent vec table is
    DEGRADED (sqlite-vec unavailable, BUG-104), never a silent pass.
    """
    try:
        n_fbs = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
        n_vec = conn.execute("SELECT COUNT(*) FROM vec_fbs").fetchone()[0]
        orphans = conn.execute(
            "SELECT COUNT(*) FROM vec_fbs v LEFT JOIN fbs f ON v.rowid = f.rowid "
            "WHERE f.rowid IS NULL"
        ).fetchone()[0]
        missing = conn.execute(
            "SELECT COUNT(*) FROM fbs f LEFT JOIN vec_fbs v ON v.rowid = f.rowid "
            "WHERE v.rowid IS NULL"
        ).fetchone()[0]
    except Exception as e:
        return True, f"  ⚠️  Vector: UNMEASURABLE — {e} (sqlite-vec unavailable; FTS fallback)"
    if orphans:
        return False, (
            f"  ❌ Vector: CORRUPT — {orphans} orphaned index entries (dead k-NN slots); "
            f"live={n_vec - orphans}/{n_fbs}"
        )
    if missing:
        return True, f"  ⚠️  Vector: DEGRADED — {missing} fbs rows carry no vector (FTS fallback)"
    if n_vec == 0 and n_fbs > 0:
        return True, "  ⚠️  Vector: DEGRADED — 0 embeddings (sqlite-vec may be unavailable)"
    return True, f"  ✅ Vector: READY {n_vec}/{n_fbs} (rowid-verified)"


def insert_embedding(conn: sqlite3.Connection, rowid: int, definition: str) -> bool:
    """BUG-004 FIX: Pre-compute and store embedding for vector search.

    Embeds the definition once at commit time and stores in vec_fbs.
    Eliminates O(n) re-embedding on every search_vector() query.

    D2509 (M1 fix): route through pipeline.embeddings.embed_texts_bge_m3
    (Matryoshka 512d + L2-normalized) instead of ollama_embed.batch_embed
    (raw bge-m3 1024d). The raw 1024d vector violated the vec_fbs float[512]
    dimension contract (M1, D2508) — every insert would have silently
    misranked or errored even after sqlite-vec loaded.
    """
    try:
        import struct

        from pipeline.embeddings import embed_texts_bge_m3

        arr = embed_texts_bge_m3([definition])
        if arr.size == 0:
            return False

        emb = [float(x) for x in arr[0]]
        # Pack float32 array into binary blob for sqlite-vec
        blob = struct.pack(f'{len(emb)}f', *emb)
        conn.execute(
            "INSERT INTO vec_fbs(rowid, definition_embedding) VALUES (?, ?)",
            (rowid, blob),
        )
        return True
    except Exception as e:
        # BUG-118: was silently `return False` — a per-FB embedding failure was
        # invisible. Log it (C16: no silent errors) but stay non-fatal (vector
        # search falls back to FTS).
        print(f"  ⚠️  Embedding insert failed (rowid={rowid}): {e}")
        return False  # Non-critical — vector search will fall back to FTS


# D-2934: taxonomy-skew advisories, recorded ONCE per (checkpoint, store) version pair so a
# 6,591-row batch cannot emit 6,591 identical lines (C28: no log bloat) while still being loud.
TAXONOMY_SKEW_ADVISORY: dict[tuple[str, str], int] = {}


def _record_taxonomy_skew(checkpoint_taxonomy: str, store_taxonomy: str) -> None:
    """Record (loudly, once) that provenance from one menu version is landing on a row stamped
    with another. The skew is immaterial for the S5-owned columns (D-2934) but must never be
    silent: it is printed on the first occurrence and carries the row count in the summary.

    Args:
        checkpoint_taxonomy: the taxonomy_version carried by the S5 checkpoint.
        store_taxonomy: the taxonomy_version already stamped on the row in the store.
    """
    key = (checkpoint_taxonomy, store_taxonomy)
    if key not in TAXONOMY_SKEW_ADVISORY:
        print(f"  ⚠️  taxonomy skew: checkpoint {checkpoint_taxonomy!r} vs store {store_taxonomy!r} — "
              f"no menu-derived column is written (D-2934); recording the skew, not refusing.")
    TAXONOMY_SKEW_ADVISORY[key] = TAXONOMY_SKEW_ADVISORY.get(key, 0) + 1


S5_COLUMN_COERCERS: dict[str, str] = {
    "status": "str", "s5_reason": "str", "verifier_model": "str", "verification_method": "str",
    "epistemic_status": "str", "practicality": "str", "committed_at": "str",
    "verification_results": "json", "isor": "json", "needs_human_review": "bool",
}


def _coerce_s5_value(column: str, value: object) -> object:
    """Coerce an S5-owned column to its storage shape (C12: shape declared once, above).

    Args:
        column: the target column name.
        value: the raw checkpoint value.

    Returns:
        The value in storage shape.

    Raises:
        RuntimeError: an S5-owned column has no declared coercer (fail-closed, C16).
    """
    kind = S5_COLUMN_COERCERS.get(column)
    if kind is None:
        raise RuntimeError(
            f"stage6: S5-owned column {column!r} has no declared coercer — refusing to write it "
            "blind (C16). Add it to S5_COLUMN_COERCERS and to stage6.s5_owned_columns."
        )
    if kind == "json":
        return _safe_json(value if value is not None else [])
    if kind == "bool":
        return 1 if value else 0
    return _safe_str(value)


def audit_stale_store_labels(conn: sqlite3.Connection, run_id: str) -> tuple[int, dict[str, int]]:
    """D-2933/D2620 scope: report (loudly, never silently) stale ontology already IN the store.

    In verification-scoped mode S6 writes no ontology at all, so the D2620
    discipline<->domain non-contamination gate has nothing of its own to reject — the guard's
    invariant ("S6 never persists a non-canonical label") is preserved by construction. What
    remains is a PRE-EXISTING store defect (BUG-711: D-2866 remapped anchors only and excluded
    silver), which must stay visible rather than be quietly inherited. This function reports it
    as a counted advisory; it does NOT block the commit, because the commit cannot cause it and
    refusing to write provenance would leave the store strictly less correct.

    Args:
        conn: open SQLite connection.
        run_id: the run being committed.

    Returns:
        (number of affected rows, {retired_label: token_count}).
    """
    import yaml as _yaml  # noqa: PLC0415

    taxonomy = _yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "taxonomy.yaml").read_text())
    retired = set(taxonomy.get("meta", {}).get("displaced_canonicals", []))
    affected = 0
    tally: dict[str, int] = {}
    for domains, discipline in conn.execute(
        "SELECT domains, discipline FROM fbs WHERE pipeline_run_id = ?", (run_id,)
    ):
        tokens = _safe_json(domains) if domains else []
        if not isinstance(tokens, list):
            tokens = []
        stale = [t for t in [*tokens, discipline] if t in retired]
        if stale:
            affected += 1
            for token in stale:
                tally[token] = tally.get(token, 0) + 1
    return affected, tally


def update_s5_provenance(conn: sqlite3.Connection, fb: dict) -> bool:
    """D-2933 (rule V): write ONLY the S5-owned provenance columns onto an existing row.

    Why this exists: `INSERT OR REPLACE` re-writes all 77 columns from the S5 checkpoint,
    including the S4-owned ontology (name, definition, domains, discipline, content_type…).
    When the checkpoint predates a ratified taxonomy repair its labels are STALE, so the
    "replace" REGRESSES the store (BUG-709: 770/6591 rows differ; 466 rejected by D2620,
    ~304 would have silently reverted). A commit can never be more correct than the store
    it overwrites, so this path narrows the write to the columns S5 actually owns.

    Invariants enforced here (all fail-closed — the row is simply not written):
      * unknown commit scope is rejected before any write (C16, no silent fail-open);
      * only columns PRESENT in the checkpoint are written, so a field the checkpoint does
        not carry can never be default-injected over a live value (e.g. borp_score);
      * the stored `definition` must equal the checkpoint's, so a scoped write can never sit
        on top of diverged S4 content (fb_id is a content hash → they must match);
      * D274a/D274h (pre_write_verdict) still gates the write — it validates exactly the S5
        fields being written, so it remains a true precondition, not a formality;
      * the taxonomy version is asserted before the write, so a version-skewed checkpoint
        cannot stamp provenance from the wrong menu.

    Called by run_stage6() only for a fb_id that already exists AND only when
    `stage6.commit_scope == verification_scoped`. No vector work is needed: an UPDATE keeps
    the rowid, so the k-NN slot cannot go stale (this class of BUG-387 cannot occur here),
    and the embedding is derived from `definition`, which is not written.

    Args:
        conn: open SQLite connection inside the batch transaction.
        fb: one S5 checkpoint record.

    Returns:
        True when the row was written; False when a guard rejected it (counted as failed).
    """
    fb_id = fb.get("fb_id")
    name = fb.get("name", fb_id)
    if S6_COMMIT_SCOPE not in ("verification_scoped", "full_upsert"):
        print(f"   ❌ update_s5_provenance: unknown commit_scope {S6_COMMIT_SCOPE!r} — REJECTED (C16)")
        return False
    storable, complaint = pre_write_verdict(fb)
    if not storable:
        print(f"   ❌ update_s5_provenance: {complaint} on {name!r} — REJECTED (fail-closed, D274a)")
        return False
    stored = conn.execute("SELECT definition, taxonomy_version FROM fbs WHERE fb_id = ?",
                          (fb_id,)).fetchone()
    if stored is None:
        raise RuntimeError(f"stage6: update_s5_provenance called for absent fb_id {fb_id!r} (C16)")
    stored_definition, stored_taxonomy = stored[0], stored[1]
    if _safe_str(fb.get("definition")) != _safe_str(stored_definition):
        print(f"   ❌ update_s5_provenance: S4 content diverged on {name!r} — REJECTED (fail-closed, D-2933)")
        return False
    payload = {c: _coerce_s5_value(c, fb[c]) for c in S6_S5_OWNED_COLUMNS if c in fb}
    payload["committed_at"] = datetime.now(UTC).isoformat()
    if not payload:
        raise RuntimeError("stage6: stage6.s5_owned_columns is empty — nothing would be written (C16)")
    # D-2934: the taxonomy-skew guard is COLUMN-SCOPED. The checkpoint is permanently stamped
    # v5.6 (its menu_hash proves it) while the store is v9 (D-2899), so a row-scoped guard would
    # refuse every row forever — blocking on a stale stamp rather than on a real risk. The real
    # risk is narrow: writing a MENU-DERIVED value from the v5.6 menu onto a v9 row. Every column
    # in this payload is a function of (definition, evidence) or the write clock, and definition
    # drift is 0/6591, so the skew cannot propagate. Fail-closed if that ever stops being true.
    checkpoint_taxonomy = _safe_str(fb.get("taxonomy_version"))
    if checkpoint_taxonomy and checkpoint_taxonomy != _safe_str(stored_taxonomy):
        dependent = sorted(c for c in payload if c in S6_TAXONOMY_DEPENDENT_COLUMNS)
        if dependent:
            print(f"   ❌ update_s5_provenance: taxonomy skew on {name!r} "
                  f"(checkpoint {checkpoint_taxonomy!r} vs store {stored_taxonomy!r}) would write "
                  f"menu-derived column(s) {dependent} — REJECTED (fail-closed, C16)")
            return False
        _record_taxonomy_skew(checkpoint_taxonomy, _safe_str(stored_taxonomy))
    assignments = ", ".join(f"{c} = ?" for c in payload)
    conn.execute(f"UPDATE fbs SET {assignments} WHERE fb_id = ?", (*payload.values(), fb_id))
    return True


# ── D-2965 (BUG-712/BUG-741/BUG-726): the leaf-label gate's run-scoped REFUSAL LEDGER ────────
# A refusal must be NAMEABLE after the run — BUG-743's lesson (evidence not captured at the moment of
# the act is not evidence). Run-scoped: one stage6 run per process.
_LEAF_LABEL_REFUSALS: list[dict] = []


def insert_fb(conn: sqlite3.Connection, fb: dict) -> bool:
    """Insert or replace an FB into the database (D2130 schema).

    NOTE (D-2933, rule V): this is the FULL upsert — it rewrites S4-owned ontology too.
    run_stage6() only reaches it for a row absent from the store, or when
    `stage6.commit_scope: full_upsert` is explicitly configured.
    """
    # D-2965 (BUG-712/BUG-741/BUG-726): the LEAF-LABEL admission gate fires FIRST, before any DB
    # use, because the D2616 guard below is fail-closed on an INVALID value but fail-OPEN on the two
    # SILENT shapes: an ABSENT label (tolerated here as '', a shape the store ruler cannot see —
    # BUG-726) and a DISPOSITION (it validates against CONTENT_TYPES_ALL = 5 roles + 2 dispositions,
    # BUG-741). Those two are exactly how a COMPUTED label can be discarded without a trace — the
    # D-2938/BUG-712 defect class. Rule home: pipeline.content_types.leaf_label_fault (C21).
    ct_fault = leaf_label_fault(fb.get("content_type"))
    if ct_fault is not None:
        print(f"   ❌ insert_fb: content_type REFUSED [{ct_fault}] on "
              f"{fb.get('name', fb.get('fb_id', '?'))!r} — not written (fail-closed, D-2965)")
        _LEAF_LABEL_REFUSALS.append({"fb_id": fb_id(fb), "fault": ct_fault})
        return False
    # D2616 Phase 0: runtime ontology boundary (BUG-148 + C6 fail-closed).
    # A hallucinated content_type or depth is rejected here instead of being
    # silently persisted. `None` = invalid; `""` = empty — for `content_type` that
    # tolerance is now UNREACHABLE BY CONSTRUCTION (the D-2965 gate above refuses it);
    # for `depth` it stands. The DB defaults (fb_depth→"domain", content_type→"")
    # must NOT re-introduce a fabricated enum, so a *present* but invalid value fails
    # closed before the INSERT.
    ct = fb.get("content_type")
    if ct is not None and ct != "" and validate_fb_content_type(ct) is None:
        print(f"   ❌ insert_fb: invalid content_type {ct!r} on {fb.get('name', fb.get('fb_id', '?'))!r} — REJECTED (fail-closed, D2616)")
        return False
    dp = fb.get("depth")
    if dp is not None and dp != "" and validate_fb_depth(dp) is None:
        print(f"   ❌ insert_fb: invalid depth {dp!r} on {fb.get('name', fb.get('fb_id', '?'))!r} — REJECTED (fail-closed, D2616)")
        return False
    # D2620/D2626: discipline<->domain non-contamination guard (fail-closed).
    # A discipline that is a canonical DOMAIN, or a discipline inside the domain
    # set, is a hard labeling error (D2422/BUG-151). Reject before INSERT so a
    # crossed label can never be persisted silently.
    dd_flags = validate_discipline_domain(fb_discipline(fb), fb_domains(fb))
    if dd_flags:
        print(f"   ❌ insert_fb: discipline<->domain contamination {dd_flags} on "
              f"{fb.get('name', fb.get('fb_id', '?'))!r} — REJECTED (fail-closed, D2620)")
        return False
    # D274a / D274h (BUG-502): the WRITER half of the serving-gate invariant. The rail evaluates STORED
    # rows after the fact; this refuses the row BEFORE the INSERT, through the SAME comparator
    # (pipeline.serving_gate.store_verdict) the rail uses - so a status that the row's own verification
    # record does not derive can never reach the governed store, and the rail stays a backstop rather
    # than the only detector. MEASURED 2026-09-25: all 7,995 stored rows satisfy this predicate.
    storable, complaint = pre_write_verdict(fb)
    if not storable:
        print(f"   ❌ insert_fb: {complaint} on {fb.get('name', fb.get('fb_id', '?'))!r} — REJECTED (fail-closed, D274a)")
        return False
    try:
        conn.execute("""
            INSERT OR REPLACE INTO fbs (
                fb_id, name, definition, application, failure_mode,
                elaboration, content_type, extraction_type, mechanism,
                boundary, consequence, taxonomy_match_method,
                content_type_source, discipline_source, extraction_type_source, menu_hash,
                keywords, jargon,
                domains, domains_raw,
                discipline, discipline_raw, discipline_macro,
                depth, evidence,
                context, accessibility, intimacy_boundary, provenance,
                source_text, is_summary,
                is_convergent, origin,
                difficulty_level, temporal_scope, confidence_score,
                prerequisite_fbs, procedural_skill,
                contradicts_fbs, related_fbs,
                usage_count, last_retrieved_at,
                feedback_score, feedback_count, fb_version,
                source_clusters, source_books, source_ids, citation, source_authors,
                source_diversity, primary_source, source_principle_ids, source_segments,
                evidence_passages, evidence_passages_shown,
                classification_errors, classification_status, classification_error,
                verification_results, borp_score, status,
                needs_human_review, verifier_model,
                s5_reason, epistemic_status, verification_method, isor,
                practicality,
                type_body,
                schema_version, gen_model, pipeline_commit,
                taxonomy_version, pipeline_run_id,
                created_at, committed_at,
                duplicate_of
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?,
                ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?
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
            _safe_str(fb.get("content_type_source")),
            _safe_str(fb.get("discipline_source")),
            _safe_str(fb.get("extraction_type_source")),
            _safe_str(fb.get("menu_hash")),
            _safe_str(fb.get("keywords"), ""),
            _safe_str(fb.get("jargon")),
            # domains + discipline (canonical + raw) — D316: discipline singular
            _safe_json(fb_domains(fb)),
            _safe_json(fb.get("domains_raw")),
            _safe_str(fb_discipline(fb), "emerging"),
            _safe_str(fb_discipline_raw(fb)),
            _safe_str(fb.get("discipline_macro"), "emerging"),
            # depth, evidence
            _safe_str(fb_depth(fb), "domain"),
            _safe_str(fb_evidence_type(fb), "cited"),
            # v1 Anytype properties
            _safe_str(fb_context(fb)),
            _safe_str(fb_accessibility(fb)),
            _safe_str(fb_intimacy_boundary(fb)),
            _safe_str(fb_provenance(fb), "llm_extracted_from_source"),
            # source text for verification (D2131) + summary/principle gate (D2352)
            _safe_str(fb.get("source_text")),
            1 if fb.get("is_summary") else 0,
            # D2439: structural evidence tier (convergence axis)
            1 if fb.get("is_convergent") else 0,
            _safe_str(fb.get("origin"), "single_source"),
            # agentic metadata (D2130)
            _safe_str(fb.get("difficulty_level")),
            _safe_str(fb.get("temporal_scope")),
            fb.get("confidence_score"),
            _safe_json(fb.get("prerequisite_fbs")),
            _safe_str(fb.get("procedural_skill")),
            _safe_json(fb.get("contradicts_fbs")),
            _safe_json(fb.get("related_fbs")),
            # utilization tracking
            # D-2957: `last_retrieved_at` is RUNTIME state (config/content_types.yaml -> runtime), owned by the
            # serving path (pipeline/feedback.mark_fb_retrieved). A producer never INVENTS one - but this INSERT
            # is `OR REPLACE`, so it must not DESTROY one either: the BUG-376 sync path carries the DB value
            # through the S5 checkpoint and back, and that carriage is preserved here. What is fixed is the
            # ABSENT SHAPE: `_safe_str`'s '' (the other shape for "absent", the BUG-726 class) becomes NULL,
            # which is what pipeline/schemas.py declares (`str | None = Field(default=None)`) and what the
            # register declares (`role: runtime`, D-2957). Legacy rows: scripts/normalize_runtime_absents.py.
            fb.get("usage_count", 0),
            _safe_str(fb.get("last_retrieved_at")) or None,
            fb.get("feedback_score"),
            fb.get("feedback_count", 0),
            fb.get("fb_version", 1),
            # provenance (simplified) + segment provenance (D2352)
            _safe_json(fb.get("source_clusters", [])),
            _safe_json(fb_source_books(fb)),
            _safe_json(fb_source_ids(fb)),
            _safe_str(fb.get("citation")),
            _safe_json(fb.get("source_authors")),
            fb.get("source_diversity"),
            _safe_json(fb.get("primary_source")),
            _safe_json(fb.get("source_principle_ids", [])),
            _safe_json(fb.get("source_segments", [])),
            # verbatim evidence (D2352)
            _safe_json(fb.get("evidence_passages", [])),
            _safe_json(fb.get("evidence_passages_shown", [])),
            # classification errors + fail-closed status (D2351)
            _safe_json(fb.get("classification_errors")),
            _safe_str(fb.get("classification_status"), "CLEAN"),
            _safe_str(fb.get("classification_error")),
            # verification
            _safe_json(fb.get("verification_results", [])),
            fb.get("borp_score", 0.0),
            _safe_str(fb.get("status"), "PENDING"),
            1 if fb.get("needs_human_review") else 0,
            # D-2957/BUG-737: absent must be NULL, never a blank. pipeline/schemas.py declares
            # verifier_model as str | None with default None, and config/store_columns.yaml declares
            # outside: absent for the s5_verified population - so a row no verifier judged (the
            # D-2590 sidecar tier) must read as NULL, otherwise count(verifier_model) claims 1,049
            # rows the column does not actually carry a value on.
            _safe_str(fb.get("verifier_model")) or None,
            _safe_str(fb.get("s5_reason")),
            _safe_str(fb.get("epistemic_status")),
            _safe_str(fb.get("verification_method")),
            _safe_json(fb.get("isor")),
            _safe_str(fb.get("practicality")),
            # D2590/D-2943: the role-specific body (JSON text, or a TRUE NULL for a role that declares
            # none). Deliberately NOT `_safe_str(...)`: that maps None to "" and a store where "no body"
            # and "empty body" are the same bytes cannot be audited. One type only (text) so SQLite and
            # the Parquet snapshot agree and pyarrow cannot infer a struct column (BUG-388 class).
            fb.get("type_body"),
            # stamps
            # D2169: Read schema version from config/version.yaml (single source of truth)
            _safe_str(fb.get("schema_version"), _get_pipeline_version()),
            _safe_str(fb.get("gen_model")),
            _safe_str(fb.get("pipeline_commit"), "unknown"),
            _safe_str(fb.get("taxonomy_version"), "v5.0"),
            _safe_str(fb.get("pipeline_run_id")),
            _safe_str(fb.get("created_at"), ""),
            datetime.now(UTC).isoformat(),
            # D-2951: `duplicate_marker` is the ONE shape for this cell, and it keeps the truth of
            # this column's own comment ("NULL otherwise") that `_safe_str` had broken — it wrote
            # '' on EVERY row, so the D-271d predicate `duplicate_of IS NULL` matched zero rows.
            duplicate_marker(fb.get("duplicate_of")),  # D2627: canonical fb_id for a dedup row
        ))
        return True
    except Exception as e:
        print(f"  ❌ Insert failed: {e}")
        return False


PARQUET_BOOLEAN_FIELDS: tuple[str, ...] = ("is_summary", "is_convergent")


def _coerce_parquet_booleans(row: dict) -> None:
    """BUG-388: normalise declared boolean keys in place, failing loud on anything else.

    The S5 checkpoint mixes Python bool with SQLite-style int 0/1 for the same key, which
    made pa.Table.from_pylist() infer a column type from the first rows and then raise
    ArrowInvalid on a later row. Only the exact ints 0/1 are coerced; any other type raises
    (C16 - no silent coercion, no guessing what a mixed column means).
    """
    for field in PARQUET_BOOLEAN_FIELDS:
        if field not in row:
            continue
        val = row[field]
        if val is None:
            row[field] = False
        elif isinstance(val, bool):
            continue
        elif isinstance(val, int) and val in (0, 1):
            row[field] = bool(val)
        else:
            raise ValueError(
                f"BUG-388: {field}={val!r} ({type(val).__name__}) for fb "
                f"{row.get('fb_id') or row.get('id')!r} is neither bool nor a 0/1 int; "
                "refusing to export a mixed-type column (C16)"
            )


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
            "domains", "domains_raw", "source_clusters", "source_books", "source_ids",
            "source_authors", "primary_source",
            "verification_results", "classification_errors",
            "jargon", "source_principle_ids", "source_segments",
            "evidence_passages", "evidence_passages_shown",
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
            _coerce_parquet_booleans(row)
            rows.append(row)

        table = pa.Table.from_pylist(rows)
        # BUG-178 (2026-08-27): crash-safe write — tempfile → fsync → os.replace.
        # A kill mid-write previously left a truncated .parquet snapshot that
        # downstream readers fail on (C6). Write to a temp in the SAME directory
        # (so os.replace is atomic on the same filesystem), fsync, then swap.
        fd, tmp_path = tempfile.mkstemp(dir=str(parquet_dir), suffix=".parquet.tmp")
        os.close(fd)
        try:
            pq.write_table(table, tmp_path, compression="snappy")
            with open(tmp_path, "rb") as _f:
                os.fsync(_f.fileno())
            os.replace(tmp_path, parquet_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
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


def _assert_fb_id_unique(fbs: list[dict]) -> None:
    """BUG-195/D2505: fail-loud guard against duplicate fb_id BEFORE the upsert.

    `INSERT OR REPLACE INTO fbs` (fb_id TEXT PRIMARY KEY) silently overwrites the
    earlier row on any fb_id collision — the exact BUG-195 silent-data-loss class.
    The post-hoc `dedup_fb_id.py` made THIS run's fb_ids unique, but a duplicate
    reaching S6 would mean permanent silent loss. Abort instead of overwriting.
    """
    from collections import Counter

    dupes = sorted(fid for fid, k in Counter(fb.get("fb_id") for fb in fbs).items() if k > 1)
    if dupes:
        raise RuntimeError(
            f"{len(dupes)} duplicate fb_id in S5 checkpoint — refusing to commit "
            f"(INSERT OR REPLACE would silently overwrite). First duplicates: {dupes[:5]}"
        )


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# D2590 / D-2942 / D-2943 — THE NON-PRINCIPLE (procedural + episodic) COMMIT TIER
# ══════════════════════════════════════════════════════════════════════════════════════════════════
# WHY THIS EXISTS (measured 2026-10-12, run rechunk-v4-20260929): S4 ROUTES non-principle objects into
# sidecar JSONL files, and S6 ingested ONLY checkpoint.jsonl. So 1,049 extracted records (PT 774 /
# PI 156 / TI 94 / GE 25) sat on disk — extracted, routed, written, NEVER committed, NEVER indexed,
# NEVER retrievable — while the store reported a complete 6,591 rows. That silence is the defect
# (C16/C23): the corpus read as "knowledge only, no procedures" when the procedures had been
# extracted months earlier. The three rules below are the whole fix, and each is config- or
# ontology-driven (C12), fail-loud (C16) and receipted (no silent drop).
#
#   RULE 1 — SELECT BY THE ROW'S OWN `content_type`, never by the file it happens to sit in.
#            Measured: growth_edges.jsonl holds 187 `principle` rows and process_templates.jsonl
#            holds 9; a whole-file ingest would commit mislabelled, unverified rows as non-FB objects.
#   RULE 2 — THE QUARANTINE SHELF IS NEVER A SOURCE (D2616): quarantined.jsonl is a HOLD shelf.
#   RULE 3 — IDEMPOTENT (C23): the WRITE is skipped for an fb_id the store already holds (the caller
#            records ALREADY_STORED) and a repeated fb_id inside a sidecar keeps its first occurrence.
#            Measured today: 0 internal duplicates, so rule 3 removes nothing NOW — it exists for the
#            NEXT run, and the dry run proves a second pass inserts 0 rows.
#   RULE 4 — THE TIER IS A PROPERTY OF THE RUN, NOT OF THE STORE'S HISTORY: a record already stored is
#            STILL returned, because the S6 checkpoint and the Parquet snapshot must describe the run
#            identically on every pass. MEASURED: omitting them made a re-run's checkpoint shrink
#            13.8% and io_guard's SHRINK GUARD refused the write — the guard was right, and the fix
#            belongs here, not in a force flag.
#
# The rows carry NO S5 pass, because S5 verifies TRUTH CLAIMS and these roles carry none. Their
# disposition is therefore NOT invented here: `serving_gate.derive_status(None, content_type=...)`
# answers (QUARANTINE, s5_not_applicable) — NOT-APPLICABLE, not undecidable and never PASS (a
# promotion would manufacture trust, R5/D2298) — and the pre-write comparator in `insert_fb` still
# refuses any pair that is not the rule's own output (D-2942). Consequence, stated plainly: D2590
# makes this knowledge PERSISTENT and EXPLICITLY retrievable (include_quarantine=True + the
# `content_type` facet), not default-served. Default-serving it is a VERIFICATION-DESIGN question
# (how IS a tool instruction verified?) and remains owner-gated (BUG-714 contract, A1/A3).


def _non_fb_sidecar_files() -> dict[str, str]:
    """The role → sidecar filename map, read from config (C12) — code names no file literal."""
    return {
        "process_template": S4_PT_OUTPUT,
        "process_instance": S4_PI_OUTPUT,
        "growth_edge": S4_GE_OUTPUT,
        "tool_instruction": S4_TI_OUTPUT,
    }


def _run_id_for_commit() -> str:
    """The run S6 is committing, taken from the S5 checkpoint PATH (run-scoped, D-2938).

    Deliberately NOT `CANONICAL_RUN`: the sidecars must belong to the same run as the checkpoint
    whose rows are being committed, or S6 would fuse two generations into one store — the D-2937
    defect this pipeline just paid to remove.
    """
    return STAGE5_CHECKPOINT.parent.name


def _stored_fb_ids(db_path: Path) -> set[str]:
    """The fb_ids already in the store (rule 3). READ-ONLY; an absent DB or table is simply empty."""
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='fbs'"
        ).fetchone()
        if not has_table:
            return set()
        return {str(r[0]) for r in conn.execute("SELECT fb_id FROM fbs")}
    finally:
        conn.close()


def _legacy_type_body_null(db_path: Path, run_id: str) -> dict:
    """Declare the rows this build does NOT back-fill (F5.4), so the gap is visible, not silent.

    The 14 `tool_instruction` rows already in the store predate the `type_body` column. They are the
    BUG-714 mislabels (code snippets, not tool instructions) and are slated for retype; back-filling
    them here would entangle THIS change with that decision. Counted and reported instead.
    """
    if not db_path.exists():
        return {"count": 0, "content_types": {}}
    roles = sorted(content_types_without_factual_claim())
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        has_table = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='fbs'"
        ).fetchone()
        if not has_table:
            return {"count": 0, "content_types": {}}
        columns = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
        placeholders = ",".join("?" for _ in roles)
        if "type_body" not in columns:
            # Pre-migration store: the column does not exist yet, so EVERY row of these roles is
            # un-backfilled. Reported as such instead of crashing or silently reporting zero.
            rows = list(conn.execute(
                f"SELECT content_type, COUNT(*) FROM fbs WHERE content_type IN ({placeholders}) GROUP BY 1",
                roles,
            ))
            note = ("type_body column absent (pre-migration): every row of these roles is "
                    "un-backfilled (BUG-714 retype owns them)")
        else:
            rows = list(conn.execute(
                f"SELECT content_type, COUNT(*) FROM fbs "
                f"WHERE content_type IN ({placeholders}) AND (type_body IS NULL OR type_body = '') "
                f"GROUP BY 1",
                roles,
            ))
            note = ("pre-dates the type_body column; BUG-714 retype owns them "
                    "(governance/FORENSIC_AUDIT_D2590_20261012.md F5.4)")
    finally:
        conn.close()
    return {"count": sum(r[1] for r in rows), "content_types": {r[0]: r[1] for r in rows}, "note": note}


def build_type_body(fb: dict) -> str | None:
    """The role-specific body as a JSON object string (D-2943); None when the role declares none.

    The field list comes from the ONTOLOGY (`config/content_types.yaml::s2_body_fields` minus
    `core_body`, via `pipeline.content_types.type_body_fields`) — it is never re-declared here (C12).
    Only fields PRESENT on the record are kept: an absent key must not become a fabricated "" (that is
    exactly how slop enters a store — a field nobody extracted reading as extracted).

    FAIL-LOUD: a role being committed that declares no body fields is a config/ontology regression,
    not an empty body (C16).
    """
    content_type = str(fb.get("content_type") or "")
    fields = type_body_fields(content_type)
    if not fields:
        raise RuntimeError(
            f"type_body: content_type {content_type!r} declares no s2_body_fields outside core_body — "
            "refusing to commit a role whose body contract the ontology does not declare (C12/C16). "
            "Fix config/content_types.yaml, do not invent a body here."
        )
    body = {f: fb[f] for f in fields if fb.get(f) not in (None, "")}
    return json.dumps(body, ensure_ascii=False, sort_keys=True) if body else None


def stamp_non_fb_disposition(fb: dict) -> None:
    """Stamp the D-2942 disposition in place, as the output of the ONE rule (D274h).

    `epistemic_status` is deliberately LEFT NULL: the D2284 label is co-derived from a verification
    record that does not exist for this tier, and stamping its fallback ("speculative") on a tool's
    syntax would be a MANUFACTURED label — the thing the co-derivation ontology forbids.
    """
    status, reason = derive_status(None, content_type=fb.get("content_type"))
    fb["status"] = status
    fb["s5_reason"] = reason
    fb["verification_results"] = []


def load_non_fb_sidecars(run_id: str, stored_ids: set[str]) -> tuple[list[dict], set[str], dict]:
    """Load, filter, dispose and receipt the non-principle sidecar rows of a run (D2590).

    Returns (rows, already_stored_ids, receipt). `rows` is the RUN's whole non-principle tier — every
    sidecar record whose own content_type is a commit role — and `already_stored_ids` names the subset
    the store already holds, so the caller writes only what is new while the S6 checkpoint and the
    Parquet snapshot stay run-stable (rule 4).

    Every other row is COUNTED in the receipt: the failure mode being repaired is a silent drop, so
    no branch may be silent (C16).

    The commit-role set is `serving_gate.content_types_without_factual_claim` — a RULE, not a list:
    the rows S6 may commit without an S5 pass are exactly the roles S5 is not applicable to. The
    declared sidecar files must cover that set exactly, and a divergence is a hard failure rather
    than a silently narrower ingest (C12/C16).

    S5-owned columns (D-2933) are STRIPPED from every top-level row before commit, so the governed
    verification axis keeps its single writer. That stripping is also what resolves the growth_edge
    `status` NAME COLLISION: the GE epistemic state (open|speculative|conceptual) survives inside
    `type_body.status`, while the `status` COLUMN is written only by stamp_non_fb_disposition.
    """
    roles = sorted(content_types_without_factual_claim())
    files = _non_fb_sidecar_files()
    if sorted(files) != roles:
        raise RuntimeError(
            f"D2590: the declared sidecar files {sorted(files)} do not cover the roles with no factual "
            f"claim {roles} — a divergence would silently narrow the ingest (C12/C16)"
        )

    receipt: dict = {
        "run_id": run_id,
        "roles": roles,
        "source_files": [],
        "tier_rows": 0,
        "new_rows": 0,
        "already_stored_in_tier": 0,
        "by_role": {},
        "by_role_new": {},
        "disposition_reason": derive_status(None, content_type=roles[0])[1],
        "excluded": {
            "not_a_commit_role": 0,
            "not_a_commit_role_by_content_type": {},
            "duplicate_within_sidecars": 0,
        },
        "quarantine_shelf_records": 0,
        "quarantine_shelf_is_never_a_source": S4_QUARANTINE_OUTPUT,
        "s5_owned_columns_stripped": sorted(S6_S5_OWNED_COLUMNS),
        "rule_4_run_not_history": (
            "the returned tier is the RUN's: a record already in the store is still part of it, so the "
            "S6 checkpoint and the Parquet snapshot describe the run and do NOT shrink on a re-run "
            "(weakening the io_guard shrink guard would hide that signal). Stage 6 skips the WRITE for "
            "those rows and records commit_status=ALREADY_STORED."
        ),
    }
    rows: list[dict] = []
    seen: set[str] = set()
    stored_in_tier: set[str] = set()
    for role in roles:
        path = S4_DIR / run_id / files[role]
        if not path.exists():
            raise RuntimeError(
                f"D2590: {path} does not exist — run {run_id!r} has no {role} sidecar. Refusing to "
                "commit a partial non-principle tier (C16); re-run S4 for this run or disable "
                "stage6.commit_non_fb_types."
            )
        receipt["source_files"].append(path.name)
        with path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"D2590: {path.name}:{lineno} is not standalone JSON ({exc}) — fix the sidecar "
                        "before committing it (C16)."
                    ) from exc
                content_type = str(rec.get("content_type") or "")
                if content_type not in roles:
                    receipt["excluded"]["not_a_commit_role"] += 1
                    breakdown = receipt["excluded"]["not_a_commit_role_by_content_type"]
                    breakdown[content_type or "<none>"] = breakdown.get(content_type or "<none>", 0) + 1
                    continue
                rec_fb_id = str(rec.get("fb_id") or "")
                if not rec_fb_id:
                    raise RuntimeError(
                        f"D2590: {path.name}:{lineno} carries no fb_id — an unidentifiable row cannot "
                        "be receipted or de-duplicated (C16)."
                    )
                if rec_fb_id in seen:
                    # RULE 3 — a repeated fb_id WITHIN the sidecars: the first occurrence wins and the
                    # second is counted, so no duplicate can ever be committed twice (C23).
                    receipt["excluded"]["duplicate_within_sidecars"] += 1
                    continue
                seen.add(rec_fb_id)
                if rec_fb_id in stored_ids:
                    stored_in_tier.add(rec_fb_id)
                row = dict(rec)
                for column in S6_S5_OWNED_COLUMNS:
                    row.pop(column, None)
                row["type_body"] = build_type_body(rec)  # from the ORIGINAL record (GE status survives)
                row["pipeline_run_id"] = run_id
                row["source_sidecar"] = f"{path.name}:{lineno}"
                stamp_non_fb_disposition(row)
                rows.append(row)
                receipt["by_role"][content_type] = receipt["by_role"].get(content_type, 0) + 1
                if rec_fb_id not in stored_ids:
                    receipt["by_role_new"][content_type] = receipt["by_role_new"].get(content_type, 0) + 1
    receipt["tier_rows"] = len(rows)
    receipt["already_stored_in_tier"] = len(stored_in_tier)
    receipt["new_rows"] = len(rows) - len(stored_in_tier)
    shelf = S4_DIR / run_id / S4_QUARANTINE_OUTPUT
    if shelf.exists():
        with shelf.open(encoding="utf-8") as fh:
            receipt["quarantine_shelf_records"] = sum(1 for line in fh if line.strip())

    # ── Measured declarations (never asserted from prose): what this tier does NOT carry. ──
    # A receipt that only lists successes is how a gap becomes invisible; these two counts are the
    # known limits of the non-principle tier as committed, and both are computed from the rows.
    from pipeline.schema_accessor import fb_discipline, fb_domains  # local: avoid import cycles

    receipt["taxonomy_unlabelled"] = sum(
        1 for r in rows if not fb_domains(r) and str(fb_discipline(r) or "") in ("", "emerging")
    )
    receipt["taxonomy_unlabelled_note"] = (
        "rows with no domain and no resolved discipline: the S4 taxonomy facets were never produced "
        "for the non-principle sidecars (deferred with the cross-ref producer, D2590(d)), so a "
        "domain/discipline-faceted query cannot reach them; `depth` falls back to the store default. "
        "Measured at commit time, not assumed."
    )
    ge_rows = [r for r in rows if r.get("content_type") == "growth_edge"]
    if ge_rows:
        from pipeline.growth_edge_ontology import calibration_enforcing, category_values

        vocab = category_values()
        cats = [json.loads(r["type_body"]).get("category") for r in ge_rows if r.get("type_body")]
        off = sorted({str(c) for c in cats if c not in vocab})
        receipt["ge_category_vocabulary"] = {
            "enforcing": bool(calibration_enforcing()),
            "rows": len(cats),
            "off_vocabulary_rows": sum(1 for c in cats if c not in vocab),
            "distinct_off_vocabulary_values": off,
            "note": ("D-2924 remains ADVISORY (no calibration gold set minted): the closed vocabulary is "
                     "NOT enforced on commit, and no category is rewritten here — normalising the values "
                     "is an owner-gated ontology act (D-2898). This block is the evidence the D-2924 "
                     "calibration needs."),
        }
    return rows, stored_in_tier, receipt


def run_stage6(export_only: bool = False):
    """Run Stage 6: Commit FBs to SQLite + Parquet."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    fbs = load_stage5_fbs()

    # ── D2590: the non-principle commit tier (flag-gated — S6_COMMIT_NON_FB was DEAD config) ──
    # Loaded BEFORE the uniqueness assert so a collision between the checkpoint and a sidecar is
    # caught by the same fail-loud guard rather than overwriting silently (BUG-195/D2505).
    non_fb_receipt: dict | None = None
    non_fb_already_stored: set[str] = set()
    if S6_COMMIT_NON_FB:
        commit_run = _run_id_for_commit()
        non_fb_rows, non_fb_already_stored, non_fb_receipt = load_non_fb_sidecars(
            commit_run, _stored_fb_ids(DB_PATH)
        )
        non_fb_receipt["legacy_type_body_null"] = _legacy_type_body_null(DB_PATH, commit_run)
        # RULE 4: the WHOLE tier stays in `fbs` so the S6 checkpoint and the Parquet snapshot describe
        # the RUN rather than the store's history; only the un-stored rows are written below.
        fbs.extend(non_fb_rows)
        print(f"➕ D2590 non-principle tier: {len(non_fb_rows)} row(s) from the S4 sidecars of "
              f"{commit_run} — {non_fb_receipt['by_role']}")
        print(f"   {non_fb_receipt['new_rows']} new to insert, "
              f"{non_fb_receipt['already_stored_in_tier']} already in the store (skipped, ALREADY_STORED)")
        print(f"   disposition: {non_fb_receipt['disposition_reason']} (D-2942: S5 verifies truth "
              f"claims; these roles carry none — QUARANTINE, never PASS)")
        print(f"   excluded: {non_fb_receipt['excluded']['not_a_commit_role']} not-a-commit-role "
              f"{non_fb_receipt['excluded']['not_a_commit_role_by_content_type']} (the row's own "
              f"content_type decides), {non_fb_receipt['excluded']['duplicate_within_sidecars']} "
              f"duplicate; {non_fb_receipt['quarantine_shelf_records']} on the D2616 hold shelf "
              f"(never a source)")
    else:
        print("⏭️  D2590 non-principle tier SKIPPED (stage6.commit_non_fb_types=false) — the S4 "
              "sidecars stay uncommitted and unreachable; run scripts/audit_sidecar_commit.py "
              "to see the gap")

    # BUG-195/D2505: fail-loud duplicate guard (runs before any INSERT).
    _assert_fb_id_unique(fbs)

    # D-2884(a): stamp the operative 3-way macro routing facet on every FB from the
    # C21 single home (pipeline.discipline_macro). Fine discipline stays ADVISORY;
    # routing gates on the macro + domains. Stamped BEFORE the export_only branch so
    # both the SQLite INSERT and the Parquet snapshot carry it (R14 self-describing).
    for fb in fbs:
        fb["discipline_macro"] = macro_for(fb_discipline(fb))

    print(f"💾 Stage 6: Commit — {len(fbs)} verified FBs")
    print(f"{'='*60}")

    pipeline_commit = get_pipeline_commit()

    # SQLite
    conn = init_db(DB_PATH)

    # ── D-2951: COMMIT-TIME DEDUP GATE (the prevention half of D-2949 #4) ──
    # D-2949 #4 measured 3 near-duplicate name groups and root-caused them to "stage1 SHA-256
    # EXACT-dedup + no name-level uniqueness at commit". Stage1 dedups SEGMENTS; nothing deduped
    # NAMES, so two extractions of the same concept produced two fb_ids and both landed. Built
    # BEFORE the loop so the index is one snapshot, and consulted ONLY on the INSERT path (the
    # verification_scoped branch above already took every fb_id the store holds). Deterministic
    # and LLM-free (D-343). `report` changes nothing and writes the receipt; `enforce` additionally
    # LINKS a convergent re-extraction (duplicate_of + QUARANTINE — D2625/D2630 "mark, never delete").
    dedup: CommitDedupGate | None = None
    if S6_DEDUP_GATE_ENABLED:
        if S6_DEDUP_GATE_MODE not in CommitDedupGate.MODES:
            raise RuntimeError(
                f"stage6: unknown stage6.dedup_gate.mode {S6_DEDUP_GATE_MODE!r} — expected "
                f"{CommitDedupGate.MODES}. Refusing to commit (C16 fail-closed)."
            )
        dedup = CommitDedupGate(load_committed_index(conn), mode=S6_DEDUP_GATE_MODE)
        print(f"  🧬 dedup gate: mode={S6_DEDUP_GATE_MODE} · {dedup.stored_rows} committed row(s) "
              f"over {dedup.stored_names} normalized name(s) (D-2950 identity model)")
    else:
        print("  ⏭️  dedup gate DISABLED (stage6.dedup_gate.enabled=false) — no name-level "
              "uniqueness check at commit; D-2949 #4 stays open")

    inserted = 0
    updated = 0  # D-2933 (rule V): rows written through the verification-scoped path
    failed = 0
    # BUG-708: a batch that breaches S6_MAX_FAILED_RATIO is ROLLED BACK, never committed.
    # Tracked here so the tail summary cannot claim a commit that was undone.
    rolled_back = False
    # D2325: per-FB commit status — INSERTED/FAILED/SKIPPED. Replaces the blanket
    # `committed_to_sqlite = not export_only` stamp that falsely recorded a failed
    # row as committed (C16 provenance truthfulness).
    commit_status: dict[str, str] = {}

    if not export_only:
        # D-2933 (rule V): never let a typo in config silently select the legacy
        # overwrite-everything path (C16: no silent fail-open).
        if S6_COMMIT_SCOPE not in ("verification_scoped", "full_upsert"):
            raise RuntimeError(
                f"stage6: unknown stage6.commit_scope {S6_COMMIT_SCOPE!r} — expected "
                "'verification_scoped' (D-2933 rule V) or 'full_upsert'. Refusing to commit."
            )
        if S6_COMMIT_SCOPE == "verification_scoped" and not S6_S5_OWNED_COLUMNS:
            raise RuntimeError(
                "stage6: commit_scope=verification_scoped but stage6.s5_owned_columns is empty — "
                "a scoped commit would write nothing. Fix config/pipeline_config.yaml (C16)."
            )
        if S6_TAXONOMY_DEPENDENT_COLUMNS & set(S6_S5_OWNED_COLUMNS):
            raise RuntimeError(
                "stage6: a column is declared BOTH s5_owned AND taxonomy_dependent — the D-2934 "
                "column-scoped skew guard could then never permit a skewed checkpoint to commit. "
                "Resolve config/pipeline_config.yaml:stage6 before committing (C16)."
            )
        print(f"  🔒 commit scope: {S6_COMMIT_SCOPE} "
              f"({len(S6_S5_OWNED_COLUMNS)} S5-owned column(s); S4-owned ontology is never rewritten)")
        TAXONOMY_SKEW_ADVISORY.clear()  # per-run advisory census (D-2934)
        if S6_COMMIT_SCOPE == "verification_scoped" and fbs:
            stale_rows, stale_tally = audit_stale_store_labels(conn, fbs[0].get("pipeline_run_id", ""))
            if stale_rows:
                detail = ", ".join(f"{k} x{v}" for k, v in sorted(stale_tally.items()))
                print(f"  ⚠️  BUG-711 ADVISORY: {stale_rows}/{len(fbs)} canonical row(s) already carry a "
                      f"DISPLACED canonical label in the STORE ({detail}). This commit does NOT write "
                      f"ontology, so it neither causes nor hides it; re-home with "
                      f"scripts/repair_displaced_canonical_domains.py "
                      f"(triage: governance/displaced_domain_repair_triage_20261011.csv).")
        # D-2884(a): idempotent backfill of the operative macro facet on the canonical
        # run (fills NULL cells only; re-runs are no-ops). Stale non-canonical rows
        # correctly keep NULL (never served, BUG-691).
        backfilled = _backfill_discipline_macro(conn)
        if backfilled:
            print(f"  ♻️  backfilled discipline_macro on {backfilled} canonical row(s)")

        for i, fb in enumerate(fbs, 1):
            name = fb_name(fb)[:40]
            # D2590 RULE 3: a non-principle row the store ALREADY holds is part of the run's tier
            # (rule 4: the artifacts stay run-stable) but must NOT be written again — re-running the
            # S5-provenance update on it would be 1,049 pointless writes per pass. The row is
            # recorded as ALREADY_STORED, never as INSERTED (D2325: no false commit claim).
            if non_fb_receipt is not None and fb.get("fb_id") in non_fb_already_stored:
                commit_status[fb["fb_id"]] = "ALREADY_STORED"
                continue
            # D-2933 (rule V): VERIFICATION-SCOPED COMMIT. An fb_id that already exists in the
            # store receives ONLY the S5-owned provenance columns (update_s5_provenance); the
            # S4-owned ontology is never rewritten from a possibly-stale checkpoint (BUG-709).
            # A fb_id absent from the store still takes the full INSERT path below, because a
            # genuinely new row has no ratified ontology to protect. `full_upsert` (explicit
            # config) restores the legacy behaviour for a store known to be behind the artifact.
            if S6_COMMIT_SCOPE == "verification_scoped" and fbs_rowid(conn, fb.get("fb_id")) is not None:
                if update_s5_provenance(conn, fb):
                    updated += 1
                    commit_status[fb["fb_id"]] = "UPDATED"
                else:
                    failed += 1
                    commit_status[fb["fb_id"]] = "FAILED"
                    print(f"  [{i}] Failed (provenance): {name}")
                continue
            # ── D-2951: the dedup gate answers ONE question for this incoming row ──
            # Is it a re-extraction of a concept the store (or this batch) already holds? Only a
            # CONVERGENT body under the SAME name and the SAME work is the D-2949 duplicate. That
            # row is LINKED, not dropped and not deleted: duplicate_of -> the incumbent's fb_id and
            # status QUARANTINE through derive_status — the ONE status rule (D274h) — so the pair
            # written here is exactly the pair the serving rail re-derives (D274a/request BUG-502).
            # Every other kind is inserted unchanged and merely RECORDED in the receipt: divergent
            # same-name rows are keep-both, and renaming them is owner-gated (D-271a). A candidate
            # RICHER than the incumbent is never linked — demoting the store's richer row is a
            # supersession act, reported for an owner call (D-2933 rule V).
            if dedup is not None:
                gate_decision = dedup.decide(fb)
                if gate_decision["action"] == "link_duplicate":
                    fb["duplicate_of"] = gate_decision["canonical_fb_id"]
                    fb["status"], fb["s5_reason"] = derive_status(
                        None, duplicate_of=gate_decision["canonical_fb_id"]
                    )
                    gate_decision["status_out"] = fb["status"]
                    gate_decision["s5_reason_out"] = fb["s5_reason"]

            # BUG-387/D-359: capture the rowid the fb_id holds BEFORE the insert.
            # `INSERT OR REPLACE` re-issues a new rowid for an existing fb_id, and
            # the vec store is keyed by rowid — so the old rowid's vector must be
            # retired in the same transaction or it survives as a dead k-NN slot.
            stale_rowid = fbs_rowid(conn, fb.get("fb_id"))
            if insert_fb(conn, fb):
                inserted += 1
                commit_status[fb["fb_id"]] = "INSERTED"
                if dedup is not None:
                    # D-2951: the row IS in the store now, so a later candidate in this same
                    # batch must see it — the within-run collision D-2949 #4 could not catch.
                    dedup.observe(fb)
                # BUG-004 FIX: Pre-compute embedding at commit time
                definition = fb_definition(fb)
                if definition:
                    rowid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    if stale_rowid is not None and stale_rowid != rowid:
                        if not delete_embedding(conn, stale_rowid):
                            # Fail loud: an unrepaired stale vector is exactly the
                            # BUG-387 defect, and continuing would hide it.
                            raise RuntimeError(
                                f"stage6: could not retire stale vector rowid={stale_rowid} "
                                f"for {fb.get('fb_id')!r} (BUG-387/D-359)"
                            )
                    insert_embedding(conn, rowid, definition)
            else:
                failed += 1
                commit_status[fb["fb_id"]] = "FAILED"
                print(f"  [{i}] Failed: {name}")

        # ── BUG-708: the tolerance gate drives the COMMIT DECISION, not just the exit
        # code. Committing first and evaluating S6_MAX_FAILED_RATIO afterwards made an
        # over-tolerance batch DURABLE while the stage still reported FAILED — observed
        # live 2026-10-11: 466 rows rejected by the D2620 discipline<->domain gate, so a
        # completed run would have left the store holding a mix of re-verified rows and
        # stale rows with no record of which. An over-tolerance batch is ROLLED BACK, so
        # the store is never left half-migrated (C16/C23).
        failure_ratio: float = (failed / len(fbs)) if fbs else 0.0
        if failure_ratio > S6_MAX_FAILED_RATIO:
            rolled_back = True
            conn.rollback()
            print(f"  ⛔ ROLLED BACK: {failed}/{len(fbs)} rejected "
                  f"({failure_ratio:.1%} > max_failed_ratio={S6_MAX_FAILED_RATIO}) — store UNCHANGED (BUG-708)")
        else:
            conn.commit()

        # Count
        count = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
        if rolled_back:
            print(f"  ⛔ SQLite: nothing committed — {failed}/{len(fbs)} rejected, transaction rolled back "
                  f"({count} rows, store intact)")
        else:
            print(f"  ✅ SQLite: {inserted} inserted, {updated} provenance-updated, "
                  f"{failed} failed, {count} total rows")
            for (ck_tax, st_tax), n in sorted(TAXONOMY_SKEW_ADVISORY.items()):
                print(f"  ⚠️  taxonomy skew advisory: {n} row(s) carry S5 provenance from {ck_tax!r} "
                      f"onto a {st_tax!r}-stamped row — immaterial for the written columns (D-2934)")

        # ── D2185 R-016/R-017 completeness check, repaired by BUG-387/D-359 ──
        # A COUNT is not verification. The old check compared counts and printed
        # "Vector: READY 15990/7995" on a store where 7995 index entries were
        # already dead. The assertion is ROWID-level and fails LOUD (C16).
        vec_ok, vec_msg = assert_vector_integrity(conn)
        print(vec_msg)
        if not vec_ok:
            raise RuntimeError(
                "stage6: the vector store violates its rowid contract — refusing to "
                "report a successful commit. Run scripts/repair_vec_integrity.py and "
                "re-verify with scripts/verify_vec_integrity.py (BUG-387/D-354/D-359)."
            )

        # ── D2066: Dynamic taxonomy post-commit (BEFORE conn.close) ──
        # BUG-708: this hook WRITES to the store (taxonomy_counts), so it must not run
        # after a rollback — there is no commit for it to be the post-commit of.
        if rolled_back:
            print("\n⏭️  Taxonomy post-commit hook SKIPPED — no commit was made (BUG-708).")
        else:
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
        elif rolled_back:
            # BUG-708: nothing was written, so no row may be recorded as committed.
            per_fb_status = "ROLLED_BACK"
        else:
            per_fb_status = commit_status.get(fb_id, "FAILED")  # untracked → FAILED (fail-closed)
        rec = stamp_record({
            "fb_id": fb_id,
            "name": fb["name"],
            "status": fb.get("status"),
            "commit_status": per_fb_status,
            # D2590: ALREADY_STORED is still IN the store — the flag answers "is this row in the
            # DB", not "did this pass write it". Claiming otherwise would under-report the store.
            "committed_to_sqlite": per_fb_status in ("INSERTED", "ALREADY_STORED"),
            "parquet_snapshot": str(parquet_path) if parquet_path else None,
        }, gen_model="python")
        rec["pipeline_commit"] = pipeline_commit
        commit_recs.append(rec)

    safe_write(
        STAGE6_CHECKPOINT,
        "\n".join(json.dumps(r, ensure_ascii=False) for r in commit_recs) + "\n",
    )
    write_stage_code_fingerprint(STAGE6_CHECKPOINT, "stage6")  # BUG-614: bind checkpoint to producing code

    # ── D2590 receipt: the non-principle tier's audit trail (C16 — no silent drop, remembered).
    # Written even when the commit ROLLED BACK, so a rolled-back ingest is as auditable as a landed one.
    if non_fb_receipt is not None:
        non_fb_receipt["rolled_back"] = rolled_back
        non_fb_receipt["invoked_with"] = "--export-only" if export_only else "commit"
        receipt_path = CHECKPOINT_DIR / "non_fb_commit_receipt.json"
        receipt_rec = stamp_record(non_fb_receipt, gen_model="python")
        receipt_rec["pipeline_commit"] = pipeline_commit
        safe_write(receipt_path, json.dumps(receipt_rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        print(f"🧾 D2590 receipt: {receipt_path}")

    # ── D-2951 receipt: the dedup gate's audit trail (C16 — no silent verdict, and a declined
    # enforcement is as auditable as an applied one). Written even for --export-only and after a
    # ROLLBACK, because "the gate looked and decided nothing" is itself the evidence a reviewer
    # needs before flipping mode to `enforce`.
    if dedup is not None:
        dedup_receipt = dedup.receipt()
        dedup_receipt["rolled_back"] = rolled_back
        dedup_receipt["invoked_with"] = "--export-only" if export_only else "commit"
        dedup_rec = stamp_record(dedup_receipt, gen_model="python")
        dedup_rec["pipeline_commit"] = pipeline_commit
        dedup_path = CHECKPOINT_DIR / "dedup_gate_receipt.json"
        safe_write(dedup_path, json.dumps(dedup_rec, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        counts = dedup_receipt["actions"]
        print(f"🧬 D-2951 dedup gate receipt: {dedup_path}")
        print(f"   mode={dedup_receipt['mode']} · {dedup_receipt['candidates']} candidate(s): "
              f"{counts.get('insert', 0)} insert, {counts.get('link_duplicate', 0)} linked duplicate "
              f"— kinds {dedup_receipt['kinds']}")

    # Summary
    print(f"\n{'='*60}")
    if export_only:
        print(f"📦 Parquet-only: {len(fbs)} FBs (SQLite SKIPPED)")
    else:
        if rolled_back:
            print(f"⛔ SQLite commit ROLLED BACK: 0 of {len(fbs)} FBs written (store unchanged, BUG-708)")
        else:
            print(f"✅ Committed to SQLite: {inserted} FBs")
            print(f"   (scope={S6_COMMIT_SCOPE}: {inserted} inserted as NEW rows, "
                  f"{updated} existing row(s) updated with S5 provenance only)")
        if failed:
            print(f"❌ Failed to commit:    {failed} FBs (checkpoint commit_status=FAILED)")
    print(f"🗄️  Database:  {DB_PATH}")
    if parquet_path:
        print(f"📦 Parquet:   {parquet_path}")
    print(f"📋 Checkpoint: {STAGE6_CHECKPOINT}")

    # ── D-2965: the leaf-label gate's refusals are named, never absorbed ─────
    if _LEAF_LABEL_REFUSALS:
        print(f"❌ Stage 6 leaf-label gate (D-2965): {len(_LEAF_LABEL_REFUSALS)} row(s) REFUSED")
        print("   an absent/blank content_type or a DISPOSITION is not a ROLE — nothing was written.")
        for _ref in _LEAF_LABEL_REFUSALS[:10]:
            print(f"   · {_ref['fb_id']}  [{_ref['fault']}]")
        if len(_LEAF_LABEL_REFUSALS) > 10:
            print(f"   · … {len(_LEAF_LABEL_REFUSALS) - 10} more (full ledger: _LEAF_LABEL_REFUSALS)")

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
            if rolled_back:
                print("   ⛔ The SQLite transaction was ROLLED BACK — the store is unchanged "
                      "(BUG-708: no partial/half-migrated write).")
            sys.exit(1)
        if failed > 0:
            print(f"⚠️  Stage 6 CONDITIONAL_SUCCESS: {failed} FB(s) failed within "
                  f"tolerance ({failure_ratio:.1%} ≤ {S6_MAX_FAILED_RATIO}). Re-run to retry failed FBs.")
            sys.exit(2)  # non-zero → runner does NOT auto-advance / mark COMPLETE


def selftest() -> int:
    """Known-answer controls for the D-2965 leaf-label admission gate (BOTH directions).

    A rail that accepts everything is not a rail (BUG-739's lesson), so these controls must SEE the
    gate refuse every silent shape AND admit every declared role, must SEE the verdict follow the
    DECLARATION rather than a constant, and must SEE a missing declaration fail closed at load.

    Returns:
        0 when every control held, 1 when any control failed (fail-closed, never an approval).
    """
    from pipeline import content_types as _ct

    failures: list[str] = []
    checks: list[tuple[str, object, object]] = []

    # (1) DIRECTION A — the refusal shapes.
    for _label, _value in (("blank string", ""), ("whitespace only", "   "), ("None", None)):
        checks.append((f"REFUSED as absent: {_label}", leaf_label_fault(_value), "absent"))
    for _disp in sorted(_ct.CONTENT_TYPE_DISPOSITIONS):
        checks.append(
            (f"REFUSED as disposition: {_disp}", leaf_label_fault(_disp), f"disposition:{_disp}")
        )
    checks.append(
        ("REFUSED as undeclared: 'fact' (the cemetery, dropped_content_types)",
         leaf_label_fault("fact"), "undeclared:fact")
    )

    # (2) DIRECTION B — every declared ROLE is admitted (the store's own 5 values).
    for _role in sorted(_ct.CONTENT_TYPES):
        checks.append((f"ADMITTED role: {_role}", leaf_label_fault(_role), None))

    # (3) THE SCOPE SPLIT IS ASSERTED, not assumed: the S2/pre-classification validator keeps the
    # FULL vocabulary by design, so the leaf gate is the ONLY narrowing — if someone narrows the
    # shared validator instead, this control fires and the reasoning must be re-decided.
    checks.append(("scope split: validate_fb_content_type('quarantine') stays ACCEPTED (S2 layer)",
                   validate_fb_content_type("quarantine"), "quarantine"))
    checks.append(("scope split: the leaf gate refuses the SAME value",
                   leaf_label_fault("quarantine"), "disposition:quarantine"))

    for _name, _got, _want in checks:
        if _got != _want:
            failures.append(f"{_name}: got {_got!r}, want {_want!r}")

    # (4) THE CONTROL BINDS CODE TO THE DECLARATION (D-2953's lesson): flipping the declared flags
    # must FLIP the verdict. A gate hardcoded to True would pass (1)-(2) and fail exactly here.
    _saved = _ct.LEAF_ADMISSION
    try:
        _ct.LEAF_ADMISSION = {"require_role": False, "refuse_dispositions": False}
        if leaf_label_fault("") is not None:
            failures.append("declaration not bound: require_role:false still refused a blank")
        if leaf_label_fault("quarantine") is not None:
            failures.append("declaration not bound: refuse_dispositions:false still refused a disposition")
        if leaf_label_fault("fact") != "undeclared:fact":
            failures.append("an UNDECLARED value must stay refused at ANY declaration (not switchable)")
    finally:
        _ct.LEAF_ADMISSION = _saved

    # (5) DIRECTION C — a MISSING declaration FAILS CLOSED AT LOAD (the "silently disabled control"
    # direction: the dangerous one, because it looks green).
    for _bad, _why in ((None, "missing block"), ({}, "empty block"),
                       ({"require_role": True}, "missing refuse_dispositions"),
                       ({"require_role": True, "refuse_dispositions": "yes"}, "non-bool")):
        try:
            _ct._validate_admission(_bad)
        except SystemExit:
            pass
        else:
            failures.append(f"a {_why!r} commit_gate must FAIL CLOSED at load, not default")

    # (6) THE ENFORCEMENT POINT: assert the gate is the FIRST thing insert_fb does. conn=None is
    # deliberately unusable — a refusal must return False WITHOUT touching the connection, so if the
    # gate ever moves below the DB use these raise instead of returning False.
    for _label, _fb in (("blank", {"fb_id": "selftest", "name": "selftest", "content_type": ""}),
                        ("disposition", {"fb_id": "selftest", "name": "selftest", "content_type": "quarantine"}),
                        ("undeclared", {"fb_id": "selftest", "name": "selftest", "content_type": "fact"})):
        _before = len(_LEAF_LABEL_REFUSALS)
        try:
            _verdict = insert_fb(None, _fb)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001 — the point is that NOTHING may be touched
            failures.append(f"insert_fb({_label}) reached the DB before refusing: {type(exc).__name__}")
            continue
        if _verdict is not False:
            failures.append(f"insert_fb({_label}) returned {_verdict!r}, want False")
        if len(_LEAF_LABEL_REFUSALS) != _before + 1:
            failures.append(f"insert_fb({_label}) did not record a NAMED refusal")

    total = len(checks) + 4 + 3
    print(f"stage6 leaf-label gate (D-2965) selftest: {total} control(s)")
    if failures:
        for _f in failures:
            print(f"   ❌ {_f}")
        print(f"   {len(failures)} FAILED — the gate is NOT trustworthy (fail-closed)")
        return 1
    print("   ✅ all controls held — refusal shapes REFUSED, roles ADMITTED, verdict bound to the "
          "DECLARATION, missing declaration FAIL-CLOSED, refusals recorded before any DB use")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Stage 6: Commit FBs → SQLite + Parquet")
    parser.add_argument("--export-only", action="store_true",
                        help="Only export Parquet snapshot (don't modify DB)")
    parser.add_argument("--selftest", action="store_true",
                        help="Run the D-2965 leaf-label gate's known-answer controls and exit")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())

    run_stage6(export_only=args.export_only)


if __name__ == "__main__":
    main()
