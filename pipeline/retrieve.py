#!/usr/bin/env python3
"""
retrieve.py — Hybrid search: SQL + FTS5 + sqlite-vec + Graph + Agentic.
========================================================================
Authority: CONSTITUTION.md §2.3, D2205 (RAG Architecture Roadmap)

Retrieval modes:
  1. Keyword: SQL query on domains, discipline, depth, status
  2. Full-text: FTS5 search on name, definition, keywords
  3. Vector: sqlite-vec cosine similarity (if available)
  4. Hybrid: FTS + vector + keyword fused via RRF (D2176)
  5. Graph-aware: Hybrid + BFS graph expansion (D2205 P1)
  6. Agentic: Iterative retrieval with critique loop (D2205 P0)

Usage:
    python3 pipeline/retrieve.py --keyword "systems thinking"
    python3 pipeline/retrieve.py --domain "ai & agents" --depth universal
    python3 pipeline/retrieve.py --fts "feedback loops"
    python3 pipeline/retrieve.py --vector "how to build resilient systems"
    python3 pipeline/retrieve.py --hybrid "decision making"  # FTS + vector + keyword
    python3 pipeline/retrieve.py --agentic "pricing strategy"  # Iterative with critique
    python3 pipeline/retrieve.py --graph-aware "systems thinking"  # Graph expansion
"""

import argparse
import json
import re
import sqlite3
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.pipeline_paths import RETRIEVE_CONFIDENCE_THRESHOLD  # D2231: C12 compliance
from pipeline.pipeline_paths import RERANK_ENABLED  # D2521 (S2): production rerank adoption gate
from pipeline.pipeline_paths import FTS_STOPWORDS  # D2561: C12 stopwords from config
from pipeline.pipeline_paths import (  # D2537: fused quality ranking (opt-in)
    RANKING_QUALITY_SCORE_ENABLED,
    RANKING_CONFIDENCE_WEIGHT,
    RANKING_CONVERGENT_BOOST,
    RANKING_DIVERSITY_BOOST,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.feedback import mark_fb_retrieved  # D2188 (P1-2): usage tracking on retrieval
from pipeline.pipeline_paths import DB_PATH


def get_conn() -> sqlite3.Connection:
    """Get a read-only connection to the database.

    D2509 (M1 fix): loads sqlite-vec into the connection so vec_fbs MATCH
    queries work. Gracefully no-ops (vector leg falls back to FTS in
    search_vector) when sqlite-vec is missing OR the Python build lacks
    enable_load_extension (python.org framework build).
    """
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    _try_load_sqlite_vec(conn)
    return conn


def _try_load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec into a connection if available (D2509).

    Non-fatal by design: when sqlite-vec is missing or the Python build lacks
    enable_load_extension, vector search degrades to FTS (C23 resilient path).
    Returns True only when the vec0 module is registered.
    """
    try:
        import sqlite_vec
    except ImportError:
        return False
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        return False



def _status_predicate(include_quarantine: bool) -> str:
    """D2330: quarantine is opt-in — never surfaced by default.

    PASS is always retrievable. QUARANTINE is only retrievable when the caller
    explicitly opts in via include_quarantine=True. This is the retrieval
    contract that keeps quarantined (unverified/contradicted) FBs out of the
    default answer path.
    """
    if include_quarantine:
        return "status IN ('PASS', 'QUARANTINE')"
    return "status = 'PASS'"


def _quality_field() -> str:
    """D2537: the verified-populated quality signal vs the dead borp_score.

    borp_score is ~all 0.0 (verified 3,310/3,310 PASS rows), so any `ORDER BY
    borp_score` degenerates to rowid order. When RANKING_QUALITY_SCORE_ENABLED,
    use S5 NLI confidence_score (avg 0.917, fully populated) instead.
    """
    return "confidence_score" if RANKING_QUALITY_SCORE_ENABLED else "borp_score"


def _rank_sql() -> str:
    """D2537: fused quality-score ORDER BY clause (config-gated)."""
    if not RANKING_QUALITY_SCORE_ENABLED:
        return "borp_score DESC"
    return (
        f"COALESCE(confidence_score, 0.5) * {RANKING_CONFIDENCE_WEIGHT} "
        f"+ CASE WHEN is_convergent = 1 THEN {RANKING_CONVERGENT_BOOST} ELSE 0.0 END "
        f"+ CASE WHEN source_diversity IS NOT NULL AND source_diversity >= 2 "
        f"THEN {RANKING_DIVERSITY_BOOST} ELSE 0.0 END DESC"
    )


def search_keyword(
    conn: sqlite3.Connection,
    domain: str = None,
    discipline: str = None,
    depth: str = None,
    status: str = "PASS",
    include_quarantine: bool = False,
    limit: int = 20,
    exclude_summaries: bool = True,
    discipline_raw: str = None,
    domains_raw: str = None,
) -> list[dict]:
    """Keyword-based SQL search. Gracefully handles missing optional columns.

    Columns is_summary and classification_status may not exist in older DBs.
    Filters for them are applied only when the columns are present.
    """
    # Check which optional columns exist in this DB
    db_cols: set[str] = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    has_class_status: bool = "classification_status" in db_cols
    has_is_summary: bool = "is_summary" in db_cols

    conditions: list[str] = []
    params: list = []

    if include_quarantine:
        conditions.append(_status_predicate(True))
    elif status:
        conditions.append("status = ?")
        params.append(status)
    if has_class_status:
        conditions.append("(classification_status IS NULL OR classification_status != 'FAILED')")
    if domain:
        conditions.append("domains LIKE ?")
        params.append(f"%{domain}%")
    if discipline:
        conditions.append("discipline = ?")
        params.append(discipline)
    if depth:
        conditions.append("depth = ?")
        params.append(depth)
    # D2537: raw-label facets (surgical precision — finer grain than canonical buckets)
    if discipline_raw:
        conditions.append("LOWER(TRIM(discipline_raw)) = LOWER(?)")
        params.append(discipline_raw)
    if domains_raw:
        conditions.append("domains_raw LIKE ?")
        params.append(f"%{domains_raw}%")
    if exclude_summaries and has_is_summary:
        conditions.append("(is_summary = 0 OR is_summary IS NULL)")

    where: str = " AND ".join(conditions) if conditions else "1=1"
    query: str = f"SELECT * FROM fbs WHERE {where} ORDER BY {_rank_sql()} LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def _fts_query(query: str) -> str:
    """Build an FTS5 OR/prefix MATCH query from a natural-language query (D2554/BUG-221).

    FTS5 default semantics treat a multi-word MATCH as implicit AND (every term
    must appear), which returns 0 hits on full-sentence queries. This converts
    the query into OR'd prefix terms (stopwords removed) so any matching term
    contributes a hit. If every token is a stopword, fall back to the raw
    quoted query.
    """
    tokens: list[str] = []
    for tok in re.findall(r"[A-Za-z0-9]+", query.lower()):
        if tok in FTS_STOPWORDS:
            continue
        tokens.append(f"{tok}*")
    if not tokens:
        return f'"{query.lower().strip()}"'
    return " OR ".join(tokens)


def search_fts(conn: sqlite3.Connection, query: str, limit: int = 20,
             exclude_summaries: bool = True,
             include_quarantine: bool = False) -> list[dict]:
    """Full-text search on name, definition, keywords. Column-aware.

    D2330: defaults to status='PASS' — quarantined FBs are never surfaced by
    default; pass include_quarantine=True to include them.

    Gracefully handles missing is_summary and classification_status columns
    which may not exist in older DB schemas.
    """
    db_cols: set[str] = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    has_class_status: bool = "classification_status" in db_cols
    has_is_summary: bool = "is_summary" in db_cols

    status_f: str = f"AND f.{_status_predicate(include_quarantine)}"
    summary_f: str = "AND (f.is_summary = 0 OR f.is_summary IS NULL)" if has_is_summary else ""
    class_f: str = "AND (f.classification_status IS NULL OR f.classification_status != 'FAILED')" if has_class_status else ""

    try:
        rows = conn.execute(f"""
            SELECT f.* FROM fbs f
            JOIN fbs_fts ft ON f.rowid = ft.rowid
            WHERE fbs_fts MATCH ?
              {status_f}
              {summary_f}
              {class_f}
            ORDER BY rank
            LIMIT ?
        """, (_fts_query(query), limit)).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        # FTS5 may not be available — fall back to LIKE.
        # C16: log the reason loudly instead of silently swallowing the error
        # (matches the search_vector degradation convention).
        print(f"  ⚠️  FTS5 MATCH failed ({e}); falling back to LIKE")
        like_query: str = f"%{query}%"
        like_status: str = f"AND {_status_predicate(include_quarantine)}"
        like_summary: str = "AND (is_summary = 0 OR is_summary IS NULL)" if (has_is_summary and exclude_summaries) else ""
        like_class: str = "AND (classification_status IS NULL OR classification_status != 'FAILED')" if has_class_status else ""
        rows = conn.execute(f"""
            SELECT * FROM fbs
            WHERE (name LIKE ? OR definition LIKE ? OR keywords LIKE ?)
              {like_status}
              {like_summary}
              {like_class}
            ORDER BY {_rank_sql()}
            LIMIT ?
        """, (like_query, like_query, like_query, limit)).fetchall()
        return [_row_to_dict(r) for r in rows]


def search_vector(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    include_quarantine: bool = False,
    vec_table: str = "vec_fbs",
) -> list[dict]:
    """Vector similarity search using pre-computed sqlite-vec embeddings.

    BUG-004 FIX: Embeddings are pre-computed at Stage 6 commit time and stored
    in vec_fbs. Only the query is embedded at search time (O(1) not O(n)).
    Falls back to FTS if vec_fbs is not available.

    D2511 (S1): `vec_table` lets callers query an alternate index (e.g.
    `vec_fbs_ctx` built by backfill --contextual) for A/B without touching the
    production vec_fbs.
    """
    try:
        import struct

        from pipeline.embeddings import embed_texts_bge_m3

        # Embed the query (D2509: 512d Matryoshka + L2-normalized to match
        # vec_fbs float[512]. Was raw bge-m3 1024d via batch_embed — a
        # dimension mismatch that broke vector search even when vec_fbs existed.)
        arr = embed_texts_bge_m3([query])
        if arr.size == 0:
            print("  ⚠️  Embedding failed, falling back to FTS")
            return search_fts(conn, query, limit)

        query_vec = [float(x) for x in arr[0]]
        query_blob = struct.pack(f'{len(query_vec)}f', *query_vec)

        # D2509 (M1 fix): sqlite-vec requires the `k` constraint on a top-level
        # vec0 KNN query — `definition_embedding MATCH ?` in a JOIN breaks its
        # constraint detection (returns 0 rows). Use a KNN subquery + outer
        # JOIN, and OVERSAMPLE (`k = limit*5`, floor 100) because the KNN top-k
        # is computed BEFORE the status filter and QUARANTINE dominates the
        # corpus (58%) — filtering top-k=limit directly starves PASS to 0.
        knn_k = max(limit * 5, 100)
        # C12/D2511: vec_table is a caller-supplied identifier (validated, not
        # user-freeform) — sqlite-vec table names cannot be parameterized, and
        # f-string interpolation is safe here because vec_table is an internal
        # constant, never raw user input.
        try:
            rows = conn.execute(f"""
                SELECT f.*, v.distance
                FROM (
                    SELECT rowid, distance
                    FROM {vec_table}
                    WHERE definition_embedding MATCH ?
                      AND k = {int(knn_k)}
                ) v
                JOIN fbs f ON f.rowid = v.rowid
                WHERE f.{_status_predicate(include_quarantine)}
                ORDER BY v.distance
                LIMIT ?
            """, (query_blob, limit)).fetchall()

            if rows:
                return [_row_to_dict(r) for r in rows]
        except Exception:
            pass  # vec_fbs not available — fall through to FTS

        # Fallback: FTS on definition
        print("  ⚠️  vec_fbs unavailable, falling back to FTS")
        return search_fts(conn, query, limit)

    except ImportError:
        print("  ⚠️  numpy/struct not available, falling back to FTS")
        return search_fts(conn, query, limit)
    except Exception as e:
        print(f"  ⚠️  Vector search error: {e}, falling back to FTS")
        return search_fts(conn, query, limit)


def search_hybrid(
    conn: sqlite3.Connection,
    query: str,
    domain: str = None,
    discipline: str = None,
    depth: str = None,
    limit: int = 20,
    include_quarantine: bool = False,
    rerank: bool | None = None,
    discipline_raw: str = None,
    domains_raw: str = None,
) -> list[dict]:
    """D2176: True hybrid retrieval with Reciprocal Rank Fusion (RRF).

    OLD: concatenated FTS + keyword, deduplicated by fb_id. Vector search
    existed but was never fused — "hybrid" was lexical-only.
    NEW: FTS + vector + keyword candidates, fused via RRF scores.
    Score(d) = 1/(k + rank_fts) + 1/(k + rank_vector) + 1/(k + rank_metadata)

    Falls back gracefully if vector search is unavailable (pre-computed
    vec_fbs table may not exist).

    D2521 (S2): `rerank` controls the cross-encoder post-pass. None follows the
    config `rerank.enabled` gate; True forces it; False disables it (so the
    benchmark's raw-RRF "hybrid" baseline stays a clean A/B control).
    """
    RRF_K: int = 60  # RRF constant — higher = smoother rank blending
    POOL_SIZE: int = min(limit * 5, 100)  # Candidate pool per method

    # 1. Collect ranked candidates from all three methods (D2330: quarantine opt-in)
    fts_results: list[dict] = search_fts(conn, query, limit=POOL_SIZE, include_quarantine=include_quarantine)
    vector_results: list[dict] = search_vector(conn, query, limit=POOL_SIZE, include_quarantine=include_quarantine)
    # D2511 (BUG — RRF keyword-leg pollution): the "metadata/keyword" leg is only
    # meaningful when the caller actually filters by domain/discipline/depth.
    # With NO filter, search_keyword() returned `ORDER BY borp_score DESC` — and
    # with borp_score ~all 0.0 that collapses to ROWID order, i.e. a CONSTANT list
    # (e.g. "High Contrast Visual Design") injected into every query's RRF fusion.
    # That diluted the real FTS+vector signal and made hybrid WORSE than vector.
    kw_results: list[dict] = []
    if domain or discipline or depth or discipline_raw or domains_raw:
        kw_results = search_keyword(
            conn, domain=domain, discipline=discipline, depth=depth, limit=POOL_SIZE,
            include_quarantine=include_quarantine,
            discipline_raw=discipline_raw, domains_raw=domains_raw,
        )

    # 2. Build RRF score map: fb_id → cumulative RRF score
    rrf_scores: dict[str, float] = {}
    fb_map: dict[str, dict] = {}  # fb_id → best row data

    for rank, r in enumerate(fts_results, 1):
        fid: str = r["fb_id"]
        rrf_scores[fid] = rrf_scores.get(fid, 0.0) + 1.0 / (RRF_K + rank)
        if fid not in fb_map:
            fb_map[fid] = r

    for rank, r in enumerate(vector_results, 1):
        fid = r["fb_id"]
        rrf_scores[fid] = rrf_scores.get(fid, 0.0) + 1.0 / (RRF_K + rank)
        if fid not in fb_map:
            fb_map[fid] = r

    for rank, r in enumerate(kw_results, 1):
        fid = r["fb_id"]
        rrf_scores[fid] = rrf_scores.get(fid, 0.0) + 1.0 / (RRF_K + rank)
        if fid not in fb_map:
            fb_map[fid] = r

    # 3. Sort by fused RRF score (descending)
    ranked_ids: list[str] = sorted(rrf_scores, key=lambda fid: rrf_scores[fid], reverse=True)

    # 4. Return top-N with RRF scores attached
    results: list[dict] = []
    for fid in ranked_ids[:limit]:
        fb: dict = dict(fb_map[fid])
        fb["_rrf_score"] = round(rrf_scores[fid], 6)
        results.append(fb)

    # D2521 (S2): cross-encoder re-rank over a slightly wider RRF pool. None
    # defers to config `rerank.enabled`; True/False are explicit (benchmark A/B).
    should_rerank = RERANK_ENABLED if rerank is None else rerank
    if should_rerank and ranked_ids:
        try:
            from pipeline.rerank import rerank_candidates
            pool_size = min(max(limit * 5, 20), 100)
            pool = [dict(fb_map[fid]) for fid in ranked_ids[:pool_size]]
            results = rerank_candidates(query, pool, top_k=limit)
        except Exception as e:  # C24: degrade gracefully but loudly (no silent error)
            print(f"  ⚠️  rerank unavailable ({e}); returning unfused RRF list")

    return results


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to dict, parsing JSON fields."""
    d = dict(row)
    for field in ["domains", "source_clusters", "source_books", "source_ids",
                  "verification_results", "classification_errors"]:
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except json.JSONDecodeError:
                pass
    return d


def format_fb(fb: dict, index: int = None, compact: bool = False) -> str:
    """Format an FB for display (Tier-1 agent card).

    Args:
        fb: FB dict from DB row.
        index: Optional display index.
        compact: If True, only show Tier-1 core fields (def+mech+app+fail+boundary).
    """
    lines = []
    if index is not None:
        lines.append(f"─── #{index} ───────────────────────────────────────")

    # Summary flag (D2089: is_summary = not actionable)
    if fb.get("is_summary"):
        lines.append(f"⚠️ SUMMARY FB — not actionable | {fb.get('name', 'unnamed')}")
    else:
        lines.append(f"📌 {fb.get('name', 'unnamed')}")

    lines.append(f"   Discipline: {fb.get('discipline', 'N/A')} | "
                  f"Depth: {fb.get('depth', 'N/A')} | "
                  f"Status: {fb.get('status', 'N/A')}")
    lines.append(f"   Domains: {', '.join(fb.get('domains', []))}")
    definition = fb.get("definition", "")
    if definition:
        lines.append(f"   Definition: {definition[:200]}{'...' if len(definition) > 200 else ''}")
    mechanism = fb.get("mechanism", "")
    if mechanism:
        lines.append(f"   Mechanism: {mechanism[:200]}{'...' if len(mechanism) > 200 else ''}")
    application = fb.get("application", "")
    if application:
        lines.append(f"   Application: {application[:150]}{'...' if len(application) > 150 else ''}")
    failure_mode = fb.get("failure_mode", "")
    if failure_mode:
        lines.append(f"   Failure Mode: {failure_mode[:150]}{'...' if len(failure_mode) > 150 else ''}")
    boundary = fb.get("boundary", "")
    if boundary:
        lines.append(f"   Boundary: {boundary[:150]}{'...' if len(boundary) > 150 else ''}")
    # Reliability stats
    fb_score = fb.get("feedback_score")
    usage = fb.get("usage_count", 0)
    if fb_score is not None:
        lines.append(f"   Reliability: {fb_score:.2f} ({usage} uses)")
    elif usage > 0:
        lines.append(f"   Retrieved: {usage}×")
    if fb.get("keywords") and not compact:
        lines.append(f"   Keywords: {fb.get('keywords')}")
    if fb.get("citation") and not compact:
        lines.append(f"   Source: {fb.get('citation')}")
    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# D2205 P1 — Graph Expansion Layer
# ═══════════════════════════════════════════════════════════════════════

def graph_expand(
    conn: sqlite3.Connection,
    fb_ids: list[str],
    hops: int = 2,
    include_contradictions: bool = True,
    include_prerequisites: bool = True,
) -> dict[str, dict]:
    """D2205 P1: BFS graph expansion over SQLite adjacency list.

    Traverses related_fbs (undirected semantic edges), contradicts_fbs
    (bidirectional warning edges), and prerequisite_fbs (directed dependency
    edges) stored in the fbs table.

    No external graph DB. No Cypher. No Neo4j. Pure SQLite + in-memory BFS.
    No new dependencies. Uses fields already populated by Stage 4 merge.

    Memory: O(V+E) for BFS frontier. Typical: 20 seed FBs × 2 hops
            ≈ 100-200 FBs in memory. Negligible on 64GB (M1 Max).

    Args:
        conn: Read-only SQLite connection
        fb_ids: Seed FB IDs to expand from
        hops: Maximum BFS depth (1 = direct neighbors, 2 = neighbors of neighbors)
        include_contradictions: Whether to traverse contradicts_fbs edges
        include_prerequisites: Whether to traverse prerequisite_fbs edges (upstream)

    Returns:
        Dict keyed by fb_id, each value:
        {fb_id: {"related": [...], "contradicts": [...], "prerequisites": [...]}}

        Related entries include full FB dicts from DB.
        Contradicts/prerequisites are fb_id strings (fetch detail separately).
    """
    visited: set[str] = set(fb_ids)
    frontier: deque[str] = deque(fb_ids)
    result: dict[str, dict] = {
        fid: {"related": [], "contradicts": [], "prerequisites": []}
        for fid in fb_ids
    }
    current_hop: int = 0

    while frontier and current_hop < hops:
        level_size: int = len(frontier)
        for _ in range(level_size):
            current_id: str = frontier.popleft()

            # Fetch edges from DB
            row = conn.execute(
                """SELECT fb_id, related_fbs, contradicts_fbs, prerequisite_fbs
                   FROM fbs WHERE fb_id = ?""",
                (current_id,),
            ).fetchone()

            if not row:
                continue

            # ── Expand related_fbs (undirected semantic edges) ──────────
            if row["related_fbs"]:
                try:
                    related_raw = row["related_fbs"]
                    related: list = (
                        json.loads(related_raw)
                        if isinstance(related_raw, str)
                        else related_raw
                    )
                except (json.JSONDecodeError, TypeError):
                    related = []

                for rel in related:
                    rel_id: str | None = None
                    if isinstance(rel, dict):
                        rel_id = rel.get("fb_id")
                    elif isinstance(rel, str):
                        rel_id = rel
                    if rel_id and rel_id not in visited:
                        visited.add(rel_id)
                        frontier.append(rel_id)
                        # Fetch FB details for the related entry
                        rrow = conn.execute(
                            "SELECT fb_id, name, definition, domains, borp_score "
                            "FROM fbs WHERE fb_id = ?",
                            (rel_id,),
                        ).fetchone()
                        if current_id not in result:
                            result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                        result[current_id]["related"].append(
                            dict(rrow) if rrow else {"fb_id": rel_id}
                        )

            # ── Expand contradicts_fbs (bidirectional warning) ─────────
            if include_contradictions and row["contradicts_fbs"]:
                try:
                    contradicts_raw = row["contradicts_fbs"]
                    contradicts: list = (
                        json.loads(contradicts_raw)
                        if isinstance(contradicts_raw, str)
                        else contradicts_raw
                    )
                except (json.JSONDecodeError, TypeError):
                    contradicts = []

                for cid in contradicts:
                    cid_str: str = str(cid) if not isinstance(cid, dict) else str(cid.get("fb_id", cid))
                    if cid_str and cid_str not in visited:
                        visited.add(cid_str)
                        frontier.append(cid_str)
                        if current_id not in result:
                            result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                        result[current_id]["contradicts"].append(cid_str)
                        # Record reciprocal contradiction
                        if cid_str not in result:
                            result[cid_str] = {"related": [], "contradicts": [current_id], "prerequisites": []}
                        elif current_id not in result[cid_str]["contradicts"]:
                            result[cid_str]["contradicts"].append(current_id)

            # ── Expand prerequisite_fbs (directed — upstream only) ──────
            if include_prerequisites and row["prerequisite_fbs"]:
                try:
                    prereqs_raw = row["prerequisite_fbs"]
                    prereqs: list = (
                        json.loads(prereqs_raw)
                        if isinstance(prereqs_raw, str)
                        else prereqs_raw
                    )
                except (json.JSONDecodeError, TypeError):
                    prereqs = []

                for pid in prereqs:
                    pid_str: str = str(pid) if not isinstance(pid, dict) else str(pid.get("fb_id", pid))
                    if pid_str and pid_str not in visited:
                        visited.add(pid_str)
                        frontier.append(pid_str)
                        if current_id not in result:
                            result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                        result[current_id]["prerequisites"].append(pid_str)

        current_hop += 1

    return result


def graph_aware_search(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    graph_hops: int = 2,
    domain: str | None = None,
    discipline: str | None = None,
    depth: str | None = None,
) -> list[dict]:
    """D2205 P1: Hybrid search + graph expansion pipeline.

    Pipeline:
      1. search_hybrid → top-N seed FBs (RRF fusion of FTS + vector + keyword)
      2. graph_expand → 1-2 hop graph traversal over related/contradicts/prerequisite edges
      3. Deduplicate by fb_id
      4. Rerank by: borp_score × (1.0 + feedback_score) × graph_closeness
         (seed FBs weighted higher than 2-hop neighbors)
      5. Return top-k with _graph metadata attached

    Result: Retrieves FBs that are semantically close AND structurally
    connected, not just semantically similar. Surfaces contradictions
    alongside supporting evidence.

    Args:
        conn: Read-only SQLite connection
        query: Natural language search query
        limit: Max seed FBs from hybrid search
        graph_hops: BFS depth for graph expansion (1-2 recommended)
        domain: Optional domain filter
        discipline: Optional discipline filter
        depth: Optional depth filter

    Returns:
        List of FB dicts with _graph and _is_seed metadata attached
    """
    # 1. Seed retrieval via hybrid search
    seeds: list[dict] = search_hybrid(
        conn, query,
        limit=limit,
        domain=domain,
        discipline=discipline,
        depth=depth,
    )

    if not seeds:
        return []

    seed_ids: list[str] = [
        str(s.get("fb_id", s.get("id", "")))
        for s in seeds
        if s.get("fb_id") or s.get("id")
    ]

    # 2. Graph expansion
    graph: dict[str, dict] = graph_expand(
        conn, seed_ids,
        hops=graph_hops,
        include_contradictions=True,
        include_prerequisites=True,
    )

    # 3. Collect all unique FB IDs (seeds + expanded)
    all_fb_ids: set[str] = set(seed_ids)
    for fid, edges in graph.items():
        all_fb_ids.add(fid)
        for rel in edges.get("related", []):
            rid: str | None = None
            if isinstance(rel, dict):
                rid = rel.get("fb_id")
            elif isinstance(rel, str):
                rid = rel
            if rid:
                all_fb_ids.add(rid)
        for cid in edges.get("contradicts", []):
            all_fb_ids.add(str(cid))
        for pid in edges.get("prerequisites", []):
            all_fb_ids.add(str(pid))

    # 4. Fetch all FBs with scores (column-aware — classification_status may not exist)
    db_cols_gas: set[str] = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    class_filter_gas: str = (
        "AND (classification_status IS NULL OR classification_status != 'FAILED')"
        if "classification_status" in db_cols_gas else ""
    )
    placeholders: str = ",".join("?" * len(all_fb_ids))
    rows = conn.execute(
        f"""SELECT *,
            COALESCE({_quality_field()}, 0.5) AS _borp,
            COALESCE(feedback_score, 0.5) AS _feedback
            FROM fbs
            WHERE fb_id IN ({placeholders})
            {class_filter_gas}
            ORDER BY _borp DESC, _feedback DESC""",
        list(all_fb_ids),
    ).fetchall()

    results: list[dict] = [dict(r) for r in rows]

    # 5. Attach graph metadata and compute graph-aware score
    for fb in results:
        fid: str = str(fb.get("fb_id", ""))
        is_seed: bool = fid in seed_ids
        fb["_graph"] = graph.get(fid, {"related": [], "contradicts": [], "prerequisites": []})
        fb["_is_seed"] = is_seed

        # Graph-aware score: boost seed FBs, penalize distant ones
        borp: float = float(fb.get(_quality_field(), 0.5) or 0.5)
        feedback: float = float(fb.get("feedback_score", 0.5) or 0.5)
        graph_boost: float = 1.2 if is_seed else 0.9  # D2205: seed bias
        fb["_graph_score"] = borp * (1.0 + feedback) * graph_boost

    # Re-sort by graph-aware score
    results.sort(key=lambda fb: fb.get("_graph_score", 0.0), reverse=True)

    return results[:limit]


# ═══════════════════════════════════════════════════════════════════════
# D2205 P0 — Agentic Retrieval Loop
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class EvidencePack:
    """D2205 P3: Typed evidence package for agentic retrieval.

    Every Maxwell component consumes/produces this object instead of
    passing arbitrary dicts around — reduces agentic hallucination.

    Attributes:
        query: Original user query
        fbs: Retrieved Foundation Blocks (deduplicated across iterations)
        critique: Retrieval quality assessment (from retrieval_evaluator)
        iterations: Number of retrieval rounds executed
        exhausted: True if iteration budget was exhausted without CORRECT
        contradictions_surfaced: Contradicting FB pairs found during graph expansion
        total_fbs_found: Unique FBs across all iterations
    """
    query: str
    fbs: list[dict] = field(default_factory=list)
    critique: object | None = None  # CritiqueResult (lazy import to avoid circular)
    iterations: int = 1
    exhausted: bool = False
    contradictions_surfaced: list[dict] = field(default_factory=list)
    total_fbs_found: int = 0


def agentic_search(
    conn: sqlite3.Connection,
    query: str,
    max_iterations: int = 3,
    confidence_threshold: float = RETRIEVE_CONFIDENCE_THRESHOLD,  # D2231: from config (was hardcoded 0.85)
    limit: int = 20,
    domain: str | None = None,
    discipline: str | None = None,
    depth: str | None = None,
    graph_aware: bool = True,
) -> EvidencePack:
    """D2205 P0: Agentic retrieval with structured critique and iteration budget.

    Implements the iterative retrieval loop with:
      1. Retrieve → Critique → Decide (continue/stop)
      2. Hard iteration cap with explicit exhaustion flag
      3. Structured critique JSON from retrieval_evaluator

    Stop conditions (evaluated in order):
      1. critique.confidence >= confidence_threshold → return
      2. critique.retrieval_quality == "CORRECT" → return
      3. iteration == max_iterations → return with exhausted=True
      4. critique.retrieval_quality == "INCORRECT" → broaden search, then return

    Adapted from Self-RAG + CRAG for Maxwell constraints:
      - No web search fallback (C3: sovereign) → broader local retrieval
      - No tree-decoding / beam search (R7: temp=0.0) → deterministic scoring
      - No training required (C1: $0 marginal cost) → Phi-4-mini evaluator

    Iteration budget: 3 rounds maximum (Agentic RAG 2026 best practice).
    Token overhead: ~3× single-shot cost on PARTIAL queries, ~1× on CORRECT.

    Args:
        conn: Read-only SQLite connection
        query: Natural language search query
        max_iterations: Maximum retrieval rounds (default 3 from config)
        confidence_threshold: Stop if critique confidence exceeds this
        limit: Max FBs per retrieval pass
        exclude_summaries: (REMOVED — search_hybrid doesn't support this param)
        domain: Optional domain filter
        discipline: Optional discipline filter
        depth: Optional depth filter
        graph_aware: Whether to use graph-aware search (default True)

    Returns:
        EvidencePack with all FBs, critique, iteration metadata
    """
    # Lazy import to avoid circular dependency at module level
    from pipeline.retrieval_evaluator import evaluate_retrieval

    current_query: str = query
    all_fbs: dict[str, dict] = {}  # Deduplicate across iterations by fb_id
    final_critique = None
    contradictions: list[dict] = []

    for i in range(max_iterations):
        # 1. Retrieve
        if graph_aware:
            results: list[dict] = graph_aware_search(
                conn, current_query,
                limit=limit,
                domain=domain,
                discipline=discipline,
                depth=depth,
            )
        else:
            results = search_hybrid(
                conn, current_query,
                limit=limit,
                domain=domain,
                discipline=discipline,
                depth=depth,
            )

        # Track FBs across iterations (dedup by fb_id)
        for fb in results:
            fid: str = str(fb.get("fb_id", fb.get("id", "")))
            if fid and fid not in all_fbs:
                all_fbs[fid] = fb

        # Collect contradictions from graph metadata
        for fb in results:
            g = fb.get("_graph", {})
            for cid in g.get("contradicts", []):
                contradictions.append({
                    "fb_a": fb.get("fb_id", ""),
                    "fb_b": cid,
                    "iteration": i + 1,
                })

        # 2. Critique
        fbs_list: list[dict] = list(all_fbs.values())
        critique = evaluate_retrieval(query, fbs_list)
        final_critique = critique

        # 3. Decide: stop conditions
        if critique.confidence >= confidence_threshold:
            return EvidencePack(
                query=query,
                fbs=fbs_list,
                critique=critique,
                iterations=i + 1,
                contradictions_surfaced=contradictions,
                total_fbs_found=len(all_fbs),
            )

        if critique.retrieval_quality == "CORRECT":
            return EvidencePack(
                query=query,
                fbs=fbs_list,
                critique=critique,
                iterations=i + 1,
                contradictions_surfaced=contradictions,
                total_fbs_found=len(all_fbs),
            )

        if critique.retrieval_quality == "INCORRECT":
            # Broaden search: drop domain/discipline/depth filters
            broader = search_hybrid(
                conn, query,
                limit=limit * 2,
            )
            for fb in broader:
                fid = str(fb.get("fb_id", fb.get("id", "")))
                if fid and fid not in all_fbs:
                    all_fbs[fid] = fb
            return EvidencePack(
                query=query,
                fbs=list(all_fbs.values()),
                critique=critique,
                iterations=i + 1,
                exhausted=True,
                contradictions_surfaced=contradictions,
                total_fbs_found=len(all_fbs),
            )

        # 4. Continue: refine query for next iteration
        if critique.proposed_next_query and i < max_iterations - 1:
            current_query = critique.proposed_next_query
        # else: loop exits naturally

    # Exhausted iteration budget
    return EvidencePack(
        query=query,
        fbs=list(all_fbs.values()),
        critique=final_critique,
        iterations=max_iterations,
        exhausted=True,
        contradictions_surfaced=contradictions,
        total_fbs_found=len(all_fbs),
    )


def main():
    parser = argparse.ArgumentParser(description="D2205: Hybrid + Graph + Agentic FB retrieval")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--keyword", "-k", help="Keyword search")
    parser.add_argument("--fts", "-f", help="Full-text search")
    parser.add_argument("--vector", "-v", help="Vector similarity search")
    parser.add_argument("--hybrid", help="Hybrid (FTS + vector + keyword) search")
    parser.add_argument("--agentic", action="store_true",
                        help="D2205 P0: Iterative retrieval with critique loop")
    parser.add_argument("--graph-aware", action="store_true",
                        help="D2205 P1: Hybrid search + graph expansion")
    parser.add_argument("--graph-hops", type=int, default=2,
                        help="Graph expansion depth (default: 2, only with --graph-aware)")
    parser.add_argument("--max-iterations", type=int, default=3,
                        help="Max retrieval rounds for --agentic (default: 3)")
    parser.add_argument("--confidence", type=float, default=RETRIEVE_CONFIDENCE_THRESHOLD,
                        help=f"Confidence threshold for --agentic (default: {RETRIEVE_CONFIDENCE_THRESHOLD})")
    parser.add_argument("--domain", "-d", help="Filter by domain")
    parser.add_argument("--discipline", help="Filter by discipline")
    parser.add_argument("--depth", help="Filter by depth")
    parser.add_argument("--discipline-raw", help="D2537: filter by raw discipline label (surgical facet)")
    parser.add_argument("--domains-raw", help="D2537: filter by raw domain label (surgical facet)")
    parser.add_argument("--status", default="PASS", help="Filter by status (default: PASS)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-track", action="store_true",
                        help="D2188: disable usage tracking (read-only query)")
    parser.add_argument("--list-domains", action="store_true",
                        help="List all domains in DB")
    args = parser.parse_args()

    conn = get_conn()

    if args.list_domains:
        rows = conn.execute(
            "SELECT DISTINCT discipline, depth, status FROM fbs"
        ).fetchall()
        for r in rows:
            print(f"  {r['discipline']:30s} | {r['depth']:15s} | {r['status']}")
        conn.close()
        return

    # ── Determine search mode ──────────────────────────────────────
    results: list[dict] = []
    evidence_pack: EvidencePack | None = None

    if args.agentic:
        # D2205 P0: Agentic retrieval with critique loop
        query_text: str = args.query or args.hybrid or ""
        if not query_text:
            print("❌ --agentic requires a query", file=sys.stderr)
            conn.close()
            sys.exit(1)
        evidence_pack = agentic_search(
            conn, query_text,
            max_iterations=args.max_iterations,
            confidence_threshold=args.confidence,
            limit=args.limit,
            domain=args.domain,
            discipline=args.discipline,
            depth=args.depth,
            graph_aware=True,
        )
        results = evidence_pack.fbs
    elif args.graph_aware:
        # D2205 P1: Graph-aware search
        query_text = args.query or args.hybrid or ""
        if not query_text:
            print("❌ --graph-aware requires a query", file=sys.stderr)
            conn.close()
            sys.exit(1)
        results = graph_aware_search(
            conn, query_text,
            limit=args.limit,
            graph_hops=args.graph_hops,
            domain=args.domain,
            discipline=args.discipline,
            depth=args.depth,
        )
    elif args.keyword or (args.domain or args.discipline or args.depth or args.discipline_raw or args.domains_raw):
        results = search_keyword(
            conn,
            domain=args.domain,
            discipline=args.discipline,
            depth=args.depth,
            status=args.status,
            limit=args.limit,
            discipline_raw=args.discipline_raw,
            domains_raw=args.domains_raw,
        )
    elif args.fts:
        results = search_fts(conn, args.fts, limit=args.limit)
    elif args.vector:
        results = search_vector(conn, args.vector, limit=args.limit)
    elif args.hybrid:
        results = search_hybrid(
            conn, args.hybrid,
            domain=args.domain,
            discipline=args.discipline,
            depth=args.depth,
            limit=args.limit,
            discipline_raw=args.discipline_raw,
            domains_raw=args.domains_raw,
        )
    elif args.query:
        # Default: hybrid search
        results = search_hybrid(conn, args.query, limit=args.limit)
    else:
        # No query: show recent
        results = search_keyword(conn, status=args.status, limit=args.limit)

    conn.close()

    # D2188 (P1-2): Usage tracking
    if results and not args.no_track:
        tracked: int = 0
        for fb in results:
            fid = fb.get("fb_id")
            if fid:
                mark_fb_retrieved(fid)
                tracked += 1
        if tracked and not args.json:
            print(f"   📈 Usage tracked: {tracked} FB(s) (--no-track to disable)")

    # ── Output ─────────────────────────────────────────────────────
    if args.json:
        output: dict = {"results": results}
        if evidence_pack:
            output["agentic"] = {
                "iterations": evidence_pack.iterations,
                "exhausted": evidence_pack.exhausted,
                "total_fbs_found": evidence_pack.total_fbs_found,
            }
            if evidence_pack.critique:
                c = evidence_pack.critique
                output["critique"] = {
                    "retrieval_quality": getattr(c, "retrieval_quality", "?"),
                    "confidence": getattr(c, "confidence", 0.0),
                    "answered_aspects": getattr(c, "answered_aspects", []),
                    "missing_aspects": getattr(c, "missing_aspects", []),
                    "rationale": getattr(c, "rationale", ""),
                }
            if evidence_pack.contradictions_surfaced:
                output["contradictions"] = evidence_pack.contradictions_surfaced
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if evidence_pack:
            c = evidence_pack.critique
            quality: str = getattr(c, "retrieval_quality", "?") if c else "?"
            conf: float = getattr(c, "confidence", 0.0) if c else 0.0
            rationale: str = getattr(c, "rationale", "") if c else ""
            print(f"\n🤖 Agentic Search: {evidence_pack.iterations} iteration(s)")
            print(f"   Quality: {quality} | Confidence: {conf:.0%}")
            if rationale:
                print(f"   Rationale: {rationale}")
            if evidence_pack.exhausted:
                print("   ⚠️  Iteration budget exhausted — results may be incomplete")
            if evidence_pack.contradictions_surfaced:
                print(f"   ⚡ {len(evidence_pack.contradictions_surfaced)} contradiction(s) surfaced")
        print(f"\n🔍 Found {len(results)} results\n")
        for i, fb in enumerate(results, 1):
            # D2205: Show graph metadata in compact mode
            if fb.get("_graph"):
                g = fb["_graph"]
                fb["_graph_summary"] = (
                    f"🔗 {len(g.get('related', []))} related"
                    + (f" ⚡ {len(g.get('contradicts', []))} contradicts" if g.get("contradicts") else "")
                    + (f" 📋 {len(g.get('prerequisites', []))} prereqs" if g.get("prerequisites") else "")
                )
            prefix = "⭐ " if fb.get("_is_seed") else "   "
            print(prefix + format_fb(fb, i))

    if not results:
        print("  (no results found)")


if __name__ == "__main__":
    main()
