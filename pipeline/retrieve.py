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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.feedback import (
    declared as _feedback_declared,  # D-2989: the numeric policy's ONE home (C12)
)
from pipeline.feedback import mark_fb_retrieved  # D2188 (P1-2): usage tracking on retrieval
from pipeline.label_traceability import (
    traceability_of,  # noqa: E402  BUG-497/D-2640: declared label provenance
)
from pipeline.pipeline_paths import (  # D-2980: the ONE home of the candidate-pool policy (C12/C20)  # D2537: fused quality ranking (opt-in)
    FTS_STOPWORDS,  # D2561: C12 stopwords from config
    RANKING_CONFIDENCE_WEIGHT,
    RANKING_CONVERGENT_BOOST,
    RANKING_DIVERSITY_BOOST,
    RANKING_QUALITY_FIELD,  # D-2995 (BUG-776): the measure's ONE home (fail-closed read)
    RANKING_QUALITY_SCORE_ENABLED,
    RERANK_ENABLED,  # D2521 (S2): production rerank adoption gate
    RERANK_POOL_CAP,
    RERANK_POOL_FLOOR,
    RERANK_POOL_MULTIPLIER,
    RETRIEVAL_METHOD,  # D-2724: production retrieval default (C21 swappable)
    RETRIEVE_CONFIDENCE_THRESHOLD,  # D2231: C12 compliance
    RRF_LEG_POOL_CAP,
    RRF_LEG_POOL_MULTIPLIER,
    SYMMETRIC_RELATIONSHIP_TYPES,  # A2/BUG-274: undirected related_fbs types (reverse adjacency)
)

#: D-2989/T-107: the serving NEUTRAL PRIOR, READ from its declared home instead of restated as a literal in the four
#: reads below (config/feedback.yaml#serving.neutral_prior). A policy value with no home cannot be reviewed or
#: ratcheted, and the SQL and Python copies of it could disagree about what a stored 0.0 means (the BUG-499/BUG-502
#: class inside ONE function). Fail-closed at import: a missing declaration is an error, never a code default.
NEUTRAL_PRIOR: float = float(_feedback_declared("serving.neutral_prior"))
from pipeline.pipeline_paths import (  # D-2881: serving canonical-run pin
    CANONICAL_RUN,
    DB_PATH,
    canonical_run_clause,
)
from pipeline.sqlite_vec_loader import (
    load_sqlite_vec,  # D-2915: shared sqlite-vec loader (ctypes fallback)
)


def get_conn() -> sqlite3.Connection:
    """Get a read-only connection to the database.

    D2509/D-2915: loads sqlite-vec via the shared loader (extension API first,
    ctypes C-API fallback for python.org framework builds). When sqlite-vec is
    missing or unloadable, vector search degrades to FTS in search_vector (C23).
    """
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    _vec = load_sqlite_vec(conn)
    if not _vec.loaded:
        print(f"  ⚠️  vector leg disabled ({_vec.method}): {_vec.error} — FTS only (C23)")
    return conn



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


def _require_fused_ranking() -> None:
    """D-2995 (BUG-776): the fused ranking is the ONLY declared ordering — fail CLOSED when it is off.

    There is no degraded arm to fall back to. The arm this replaced ordered by a scalar that is
    constant 0.0 on every canonical row (D-2994/T-107), i.e. it served ROWID order while presenting
    itself as a quality ranking: a reader branching on a value nothing writes (the BUG-511 class).
    A config state with no declared ordering is a refusal, never a guess (C16).
    """
    if not RANKING_QUALITY_SCORE_ENABLED:
        raise RuntimeError(
            "config/pipeline_config.yaml#ranking.quality_score_enabled is false and NO degraded "
            "ordering is declared: the fused quality ranking is the ONE home of the served ORDER BY "
            "(D2537/D-2979). The previous off-arm ordered by a retired constant and was removed "
            "2026-10-14 (D-2994/BUG-776) — it must not be reintroduced as a silent fallback (C16)."
        )


def _quality_field() -> str:
    """D2537/D-2995: the MEASURE the served ordering reads.

    ONE home: config `ranking.quality_field`, read fail-closed by pipeline/pipeline_paths.py
    (RANKING_QUALITY_FIELD — no code default, D-2982/D-2644). The verified arm is the S5 NLI
    confidence_score; a retired column is not an admissible value here (BUG-776).
    """
    _require_fused_ranking()
    return RANKING_QUALITY_FIELD


def _rank_sql() -> str:
    """D2537/D-2995: fused quality-score ORDER BY clause (config-gated, fail-closed)."""
    _require_fused_ranking()
    return (
        f"COALESCE(confidence_score, {NEUTRAL_PRIOR}) * {RANKING_CONFIDENCE_WEIGHT} "
        f"+ CASE WHEN is_convergent = 1 THEN {RANKING_CONVERGENT_BOOST} ELSE 0.0 END "
        f"+ CASE WHEN source_diversity IS NOT NULL AND source_diversity >= 2 "
        f"THEN {RANKING_DIVERSITY_BOOST} ELSE 0.0 END DESC"
    )


def _rerank_pool_size(limit: int) -> int:
    """D-2980: the served/rerank candidate-pool size. ONE home (config serving.pool).

    Both the served path (search()) and the retrieval benchmark's A/B legs read THIS
    function, so an A/B leg is CONSTRUCTED to equal the served path instead of nearly
    matching it (the harness used a literal 30 while production used 50-100, which is why
    it could not bench production - BUG-710 residual).
    """
    return min(max(limit * RERANK_POOL_MULTIPLIER, RERANK_POOL_FLOOR), RERANK_POOL_CAP)


def _rrf_leg_pool_size(limit: int) -> int:
    """D-2980: the per-leg candidate pool of the RRF path (config serving.pool).

    Shape PRESERVED from D2176 (min(limit * mult, cap), no floor) so the raw-RRF control leg
    keeps measuring the same function it always measured; the literal it used to be is gone,
    so the value is tunable in ONE place (C12/C20).
    """
    return min(limit * RRF_LEG_POOL_MULTIPLIER, RRF_LEG_POOL_CAP)


def _facet_conditions(
    domain: str = None,
    discipline: str = None,
    macro: str = None,
    depth: str = None,
    discipline_raw: str = None,
    domains_raw: str = None,
    practicality: str = None,
    content_type: str = None,
    alias: str = "",
) -> tuple[list[str], list]:
    """D273a/G12: the facet predicate as a SHARED SQL clause, used by EVERY leg.

    A facet that is not asserted on every candidate generator is not a filter
    (standing rule). This builds the exact same conditions (and params) for the
    FTS, vector and keyword legs so a facet-bearing query is answered only by
    rows that actually match the facet. `alias` qualifies the column names for
    joined queries (e.g. ``alias="f."``).
    """
    conds: list[str] = []
    params: list = []
    if discipline:
        conds.append(f"{alias}discipline = ?")
        params.append(discipline)
    if macro:
        # D-2884(a): the OPERATIVE 3-way routing facet (discipline is advisory-only).
        conds.append(f"{alias}discipline_macro = ?")
        params.append(macro)
    if domain:
        conds.append(f"{alias}domains LIKE ?")
        params.append(f"%{domain}%")
    if depth:
        conds.append(f"{alias}depth = ?")
        params.append(depth)
    if discipline_raw:
        # BUG-703 (ii): raw label blanked at S4 merge for 190 abstained rows — fall back to
        # canonical discipline when raw is empty so raw-label routing stays complete (D-2537).
        conds.append(f"LOWER(TRIM(COALESCE(NULLIF(TRIM({alias}discipline_raw), ''), {alias}discipline))) = LOWER(?)")
        params.append(discipline_raw)
    if domains_raw:
        conds.append(f"{alias}domains_raw LIKE ?")
        params.append(f"%{domains_raw}%")
    if practicality:
        conds.append(f"{alias}practicality = ?")
        params.append(practicality)
    if content_type:
        # D-2944 (D2590): the ROLE facet. Load-bearing for the non-principle tier, which is
        # QUARANTINE by design (D-2942): without it a caller cannot ask for "procedures only"
        # and is forced to ask for "everything that did not pass verification".
        conds.append(f"{alias}content_type = ?")
        params.append(content_type)
    return conds, params


def _matches_facet(
    fb: dict,
    domain: str = None,
    discipline: str = None,
    macro: str = None,
    depth: str = None,
    discipline_raw: str = None,
    domains_raw: str = None,
    practicality: str = None,
    content_type: str = None,
) -> bool:
    """Post-filter assertion: a candidate matches the facet (mirrors _facet_conditions).

    D273a/G12: the facet is ALSO asserted on the fused pool, so a violator can
    never be promoted by RRF fusion or rerank.
    """
    if discipline and fb.get("discipline") != discipline:
        return False
    if macro and fb.get("discipline_macro") != macro:
        return False
    if domain and domain not in (fb.get("domains") or ""):
        return False
    if depth and fb.get("depth") != depth:
        return False
    if discipline_raw and (fb.get("discipline_raw") or fb.get("discipline") or "").strip().lower() != discipline_raw.strip().lower():
        return False
    if domains_raw and domains_raw not in (fb.get("domains_raw") or ""):
        return False
    if practicality and (fb.get("practicality") or "") != practicality:
        return False
    if content_type and (fb.get("content_type") or "") != content_type:
        return False
    return True


def search_keyword(
    conn: sqlite3.Connection,
    query: str = None,
    domain: str = None,
    discipline: str = None,
    macro: str = None,
    depth: str = None,
    status: str = "PASS",
    include_quarantine: bool = False,
    limit: int = 20,
    exclude_summaries: bool = True,
    discipline_raw: str = None,
    domains_raw: str = None,
    practicality: str = None,
    content_type: str = None,
) -> list[dict]:
    """Keyword-based SQL search. Gracefully handles missing optional columns.

    Columns is_summary and classification_status may not exist in older DBs.
    Filters for them are applied only when the columns are present.
    """
    # Check which optional columns exist in this DB
    db_cols: set[str] = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    has_class_status: bool = "classification_status" in db_cols
    has_is_summary: bool = "is_summary" in db_cols
    has_run_id: bool = "pipeline_run_id" in db_cols  # D-2881: column-aware canonical-run pin

    conditions: list[str] = []
    params: list = []

    # D-2881: serving layer must never surface non-canonical run rows (stale t11/e2e).
    if has_run_id:
        conditions.append(canonical_run_clause())
        params.append(CANONICAL_RUN)

    if include_quarantine:
        conditions.append(_status_predicate(True))
    elif status:
        conditions.append("status = ?")
        params.append(status)
    if has_class_status:
        conditions.append("(classification_status IS NULL OR classification_status != 'FAILED')")
    # D273a/G12: shared facet predicate (exact discipline / depth, substring domain).
    facet_conds, facet_params = _facet_conditions(
        domain=domain, discipline=discipline, macro=macro, depth=depth,
        discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type,
    )
    conditions.extend(facet_conds)
    params.extend(facet_params)
    # D273a/G12: the keyword leg is now QUERY-AWARE — it must also match the query
    # text, not just the facet (previously it returned facet rows in insertion
    # order with no relevance to the query, polluting the RRF fusion).
    if query:
        like = f"%{query}%"
        conditions.append("(name LIKE ? OR definition LIKE ? OR keywords LIKE ?)")
        params.extend([like, like, like])
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
             include_quarantine: bool = False,
             domain: str = None,
             discipline: str = None,
             macro: str = None,
             depth: str = None,
             discipline_raw: str = None,
             domains_raw: str = None,
             practicality: str = None,
             content_type: str = None) -> list[dict]:
    """Full-text search on name, definition, keywords. Column-aware.

    D273a/G12: accepts the same facet params as the other legs and asserts the
    facet predicate in BOTH the FTS5 and the LIKE-fallback paths.

    D2330: defaults to status='PASS' — quarantined FBs are never surfaced by
    default; pass include_quarantine=True to include them.

    Gracefully handles missing is_summary and classification_status columns
    which may not exist in older DB schemas.
    """
    db_cols: set[str] = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    has_class_status: bool = "classification_status" in db_cols
    has_is_summary: bool = "is_summary" in db_cols
    has_run_id: bool = "pipeline_run_id" in db_cols  # D-2881

    status_f: str = f"AND f.{_status_predicate(include_quarantine)}"
    summary_f: str = "AND (f.is_summary = 0 OR f.is_summary IS NULL)" if has_is_summary else ""
    class_f: str = "AND (f.classification_status IS NULL OR f.classification_status != 'FAILED')" if has_class_status else ""
    run_f: str = "AND f.pipeline_run_id = ?" if has_run_id else ""
    facet_conds, facet_params = _facet_conditions(
        domain=domain, discipline=discipline, macro=macro, depth=depth,
        discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type, alias="f.",
    )
    facet_f: str = "".join(f"AND {c} " for c in facet_conds)

    try:
        fts_params: list = [_fts_query(query), *facet_params]
        if has_run_id:
            fts_params.append(CANONICAL_RUN)
        fts_params.append(limit)
        rows = conn.execute(f"""
            SELECT f.* FROM fbs f
            JOIN fbs_fts ft ON f.rowid = ft.rowid
            WHERE fbs_fts MATCH ?
              {status_f}
              {facet_f}
              {summary_f}
              {class_f}
              {run_f}
            ORDER BY rank
            LIMIT ?
        """, tuple(fts_params)).fetchall()
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
        like_facet_conds, like_facet_params = _facet_conditions(
            domain=domain, discipline=discipline, macro=macro, depth=depth,
            discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type,
        )
        like_facet_f: str = "".join(f"AND {c} " for c in like_facet_conds)
        like_run_f: str = "AND pipeline_run_id = ?" if has_run_id else ""
        like_params: list = [like_query, like_query, like_query, *like_facet_params]
        if has_run_id:
            like_params.append(CANONICAL_RUN)
        like_params.append(limit)
        rows = conn.execute(f"""
            SELECT * FROM fbs
            WHERE (name LIKE ? OR definition LIKE ? OR keywords LIKE ?)
              {like_status}
              {like_facet_f}
              {like_summary}
              {like_class}
              {like_run_f}
            ORDER BY {_rank_sql()}
            LIMIT ?
        """, tuple(like_params)).fetchall()
        return [_row_to_dict(r) for r in rows]


def search_vector(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    include_quarantine: bool = False,
    vec_table: str = "vec_fbs",
    domain: str = None,
    discipline: str = None,
    macro: str = None,
    depth: str = None,
    discipline_raw: str = None,
    domains_raw: str = None,
    practicality: str = None,
    content_type: str = None,
) -> list[dict]:
    """Vector similarity search using pre-computed sqlite-vec embeddings.

    BUG-004 FIX: Embeddings are pre-computed at Stage 6 commit time and stored
    in vec_fbs. Only the query is embedded at search time (O(1) not O(n)).
    Falls back to FTS if vec_fbs is not available.

    D2511 (S1): `vec_table` lets callers query an alternate index (e.g.
    `vec_fbs_ctx` built by backfill --contextual) for A/B without touching the
    production vec_fbs.
    """
    db_cols: set[str] = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    has_run_id: bool = "pipeline_run_id" in db_cols  # D-2881: canonical-run pin
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
        # D273a/G12: when a facet is present, oversample MORE — the KNN top-k is
        # computed BEFORE the facet/status filters, so a rare facet starves the
        # candidate pool otherwise (same reason the status filter oversamples).
        has_facet = bool(domain or discipline or macro or depth or discipline_raw or domains_raw or practicality or content_type)
        knn_k = max(limit * (15 if has_facet else 5), 200 if has_facet else 100)
        facet_conds, facet_params = _facet_conditions(
            domain=domain, discipline=discipline, macro=macro, depth=depth,
            discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type, alias="f.",
        )
        facet_f: str = "".join(f"AND {c} " for c in facet_conds)
        run_f: str = "AND f.pipeline_run_id = ?" if has_run_id else ""
        vec_params: list = [query_blob, *facet_params]
        if has_run_id:
            vec_params.append(CANONICAL_RUN)
        vec_params.append(limit)
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
                  {facet_f}
                  {run_f}
                ORDER BY v.distance
                LIMIT ?
            """, tuple(vec_params)).fetchall()

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
    macro: str = None,
    depth: str = None,
    limit: int = 20,
    include_quarantine: bool = False,
    rerank: bool | None = None,
    discipline_raw: str = None,
    domains_raw: str = None,
    practicality: str = None,
    content_type: str = None,
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
    POOL_SIZE: int = _rrf_leg_pool_size(limit)  # D-2980: per-leg pool policy (config-first)

    # 1. Collect ranked candidates from all three methods (D2330: quarantine opt-in).
    # D273a/G12: the facet predicate is passed to EVERY leg — FTS and vector now
    # assert it too (previously only the query-blind keyword leg did).
    fts_results: list[dict] = search_fts(
        conn, query, limit=POOL_SIZE, include_quarantine=include_quarantine,
        domain=domain, discipline=discipline, macro=macro, depth=depth,
        discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type,
    )
    vector_results: list[dict] = search_vector(
        conn, query, limit=POOL_SIZE, include_quarantine=include_quarantine,
        domain=domain, discipline=discipline, macro=macro, depth=depth,
        discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type,
    )
    # D2511 (BUG — RRF keyword-leg pollution): the "metadata/keyword" leg is only
    # meaningful when the caller actually filters by domain/discipline/depth.
    # With NO filter, search_keyword() returned the legacy `ORDER BY <a constant quality
    # column> DESC` (D2511/BUG-710; the retired scalar is named in the decision record, not
    # here) — a constant column collapses to ROWID order, i.e. a CONSTANT list
    # (e.g. "High Contrast Visual Design") injected into every query's RRF fusion.
    # That diluted the real FTS+vector signal and made hybrid WORSE than vector.
    # D273a/G12: it is also now QUERY-AWARE (receives the query text).
    kw_results: list[dict] = []
    if domain or discipline or macro or depth or discipline_raw or domains_raw or practicality or content_type:
        kw_results = search_keyword(
            conn, query=query, domain=domain, discipline=discipline, macro=macro, depth=depth, limit=POOL_SIZE,
            include_quarantine=include_quarantine,
            discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type,
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

    # 3b. D273a/G12: ASSERT the facet on the FUSED pool (defense-in-depth). Even
    # though every leg now applies the predicate, a post-filter guarantees a
    # violator can never be promoted by RRF fusion or the rerank pool.
    if domain or discipline or macro or depth or discipline_raw or domains_raw or practicality or content_type:
        ranked_ids = [
            fid for fid in ranked_ids
            if _matches_facet(fb_map[fid], domain=domain, discipline=discipline, macro=macro, depth=depth,
                              discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type)
        ]

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
            pool_size = _rerank_pool_size(limit)  # D-2980: the served pool policy
            pool = [dict(fb_map[fid]) for fid in ranked_ids[:pool_size]]
            results = rerank_candidates(query, pool, top_k=limit)
        except Exception as e:  # C24: degrade gracefully but loudly (no silent error)
            print(f"  ⚠️  rerank unavailable ({e}); returning unfused RRF list")

    return results


def search(
    conn: sqlite3.Connection,
    query: str,
    domain: str | None = None,
    discipline: str | None = None,
    macro: str | None = None,
    depth: str | None = None,
    limit: int = 20,
    include_quarantine: bool = False,
    rerank: bool | None = None,
    discipline_raw: str | None = None,
    domains_raw: str | None = None,
    practicality: str | None = None,
    content_type: str | None = None,
    method: str | None = None,
) -> list[dict]:
    """D-2724: config-driven production retrieval entry point (C21 swappable).

    Routes on `retrieval.method` (overridable per-call via `method`):
      - "vector" -> pure vector pool + optional cross-encoder rerank. With
        `rerank.enabled` (the default) this is **vector+rerank** — the D-2723
        recommendation, because RRF fusion is recall-negative (vector 0.900 ->
        hybrid-RRF 0.833 on the 30-query golden set).
      - "rrf"    -> search_hybrid (RRF fusion of FTS + vector + keyword; the
        legacy hybrid / hybrid+rerank path).

    `search_hybrid` remains the pure-RRF implementation (used by the retrieval
    benchmark A/B harness and the CLI --hybrid), so those callers never drift.
    C16: an unknown method raises (fail-loud, never silently FTS).

    Args mirror `search_hybrid` so this is a drop-in for production call sites.
    """
    m: str = method if method is not None else RETRIEVAL_METHOD
    if m == "vector":
        should_rerank = RERANK_ENABLED if rerank is None else rerank
        pool_size: int = _rerank_pool_size(limit)  # D-2980: the served pool policy
        pool = search_vector(
            conn, query, limit=pool_size, include_quarantine=include_quarantine,
            domain=domain, discipline=discipline, macro=macro, depth=depth,
            discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type,
        )
        if should_rerank:
            try:
                from pipeline.rerank import rerank_candidates
                return rerank_candidates(query, pool, top_k=limit)
            except Exception as e:  # C24: degrade gracefully but loudly
                print(f"  ⚠️  rerank unavailable ({e}); returning pure vector list")
        return pool[:limit]
    if m == "rrf":
        return search_hybrid(
            conn, query, domain=domain, discipline=discipline, macro=macro, depth=depth,
            limit=limit, include_quarantine=include_quarantine, rerank=rerank,
            discipline_raw=discipline_raw, domains_raw=domains_raw, practicality=practicality, content_type=content_type,
        )
    raise ValueError(f"unknown retrieval method {m!r} (C16)")


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to dict, parsing JSON fields."""
    d = dict(row)
    for field_name in ["domains", "source_clusters", "source_books", "source_ids",
                       "verification_results", "classification_errors"]:
        if field_name in d and isinstance(d[field_name], str):
            try:
                d[field_name] = json.loads(d[field_name])
            except json.JSONDecodeError:
                pass
    # BUG-497 / D-2640: the DECLARED traceability of this row's label provenance. menu_hash and the
    # *_source tiers are empty for the whole pre-boundary corpus, and an empty stamp read as "no menu"
    # is indistinguishable from a broken stamp. Every SQL leg of this module maps rows through here, so
    # all four legs carry the field, and a consumer that needs a traceable label filters on
    # label_traceability == "stamped" instead of inferring it from an empty column.
    d["label_traceability"] = traceability_of(d)
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

    lines.append(f"   Macro: {fb.get('discipline_macro') or 'emerging'} | "
                  f"Discipline: {fb.get('discipline', 'N/A')} | "
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

def _reverse_adjacency(
    conn: sqlite3.Connection,
    symmetric_types: frozenset[str],
    run_clause: str,
    run_params: tuple,
) -> dict[str, list[tuple[str, list[str]]]]:
    """A2/BUG-274: incoming-edge index for symmetric related_fbs relationship types.

    The store materialises related_fbs under a per-FB top-k neighbour cap
    (BUG-188), so a weak overlap edge may survive on only ONE side — a one-way
    link. Following ONLY forward edges makes reachability asymmetric. This
    index lets the read-side traversal also follow INCOMING edges of the
    symmetric types (semantic_near / source_crossover / discipline_overlap /
    domain_overlap — all overlap/similarity signals, inherently undirected)
    WITHOUT mutating the store (backfilling the pruned direction would
    fabricate adjacency the cap intentionally dropped — D-277).

    Args:
        conn: Read-only SQLite connection.
        symmetric_types: Related_fbs relationship types treated as undirected.
        run_clause: Canonical-run SQL fragment (``"AND pipeline_run_id = ?"``
            or empty when the table has no run column).
        run_params: Parameters bound to ``run_clause``.

    Returns:
        ``{target_fb_id: [(source_fb_id, [symmetric relationship types]), ...]}``.
    """
    reverse: dict[str, list[tuple[str, list[str]]]] = {}
    rows = conn.execute(
        f"SELECT fb_id, related_fbs FROM fbs "
        f"WHERE related_fbs IS NOT NULL AND related_fbs != '' {run_clause}",
        run_params,
    ).fetchall()
    for row in rows:
        src: str = row["fb_id"]
        raw = row["related_fbs"]
        try:
            rels: list = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        for rel in rels:
            tgt: str | None = rel.get("fb_id") if isinstance(rel, dict) else rel
            if not tgt:
                continue
            rtypes: list = rel.get("relationships", []) if isinstance(rel, dict) else []
            sym: list[str] = [r for r in rtypes if r in symmetric_types]
            if sym:
                reverse.setdefault(tgt, []).append((src, sym))
    return reverse


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
    db_cols: set[str] = {r[1] for r in conn.execute("PRAGMA table_info(fbs)")}
    has_run_id: bool = "pipeline_run_id" in db_cols  # D-2881: canonical-run pin
    run_clause: str = f"AND {canonical_run_clause()}" if has_run_id else ""
    run_params: tuple = (CANONICAL_RUN,) if has_run_id else ()
    visited: set[str] = set(fb_ids)
    frontier: deque[str] = deque(fb_ids)
    result: dict[str, dict] = {
        fid: {"related": [], "contradicts": [], "prerequisites": []}
        for fid in fb_ids
    }
    current_hop: int = 0
    # A2/BUG-274: symmetric related_fbs types are traversed undirected (reverse
    # adjacency) to restore reachability symmetry dropped by the BUG-188 cap.
    symmetric_types: frozenset[str] = frozenset(SYMMETRIC_RELATIONSHIP_TYPES)
    reverse_adj: dict[str, list[tuple[str, list[str]]]] = (
        _reverse_adjacency(conn, symmetric_types, run_clause, run_params)
        if symmetric_types
        else {}
    )

    while frontier and current_hop < hops:
        level_size: int = len(frontier)
        for _ in range(level_size):
            current_id: str = frontier.popleft()

            # Fetch edges from DB
            row = conn.execute(
                f"""SELECT fb_id, related_fbs, contradicts_fbs, prerequisite_fbs
                   FROM fbs WHERE fb_id = ? {run_clause}""",
                (current_id, *run_params),
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
                            f"SELECT fb_id, name, definition, domains "  # D-2995 (BUG-776): the false quality scalar LEFT this payload; a NEW served field would be its own contract change
                            f"FROM fbs WHERE fb_id = ? {run_clause}",
                            (rel_id, *run_params),
                        ).fetchone()
                        if current_id not in result:
                            result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                        result[current_id]["related"].append(
                            dict(rrow) if rrow else {"fb_id": rel_id}
                        )

            # ── Reverse adjacency (A2/BUG-274): follow INCOMING symmetric edges ──
            # The store's per-FB neighbour cap (BUG-188) can drop one direction of
            # an inherently-symmetric overlap edge, leaving a one-way link. Follow
            # the stored reverse direction so reachability is symmetric WITHOUT
            # backfilling the store (backfill would fabricate adjacency — D-277).
            for src_id, _sym_types in reverse_adj.get(current_id, ()):
                if src_id not in visited:
                    visited.add(src_id)
                    frontier.append(src_id)
                    rrow = conn.execute(
                        f"SELECT fb_id, name, definition, domains "  # D-2995 (BUG-776): the false quality scalar LEFT this payload; a NEW served field would be its own contract change
                        f"FROM fbs WHERE fb_id = ? {run_clause}",
                        (src_id, *run_params),
                    ).fetchone()
                    if current_id not in result:
                        result[current_id] = {"related": [], "contradicts": [], "prerequisites": []}
                    result[current_id]["related"].append(
                        dict(rrow) if rrow else {"fb_id": src_id}
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
    macro: str | None = None,
    depth: str | None = None,
    content_type: str | None = None,
) -> list[dict]:
    """D2205 P1: Hybrid search + graph expansion pipeline.

    Pipeline:
      1. search_hybrid → top-N seed FBs (RRF fusion of FTS + vector + keyword)
      2. graph_expand → 1-2 hop graph traversal over related/contradicts/prerequisite edges
      3. Deduplicate by fb_id
      4. Rerank by: <ranking.quality_field> × (1.0 + feedback_score) × graph_closeness
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
    # 1. Seed retrieval via production search (config retrieval.method; D-2724)
    seeds: list[dict] = search(
        conn, query,
        limit=limit,
        domain=domain,
        discipline=discipline,
        macro=macro,
        depth=depth,
        content_type=content_type,  # D-2944: the seed leg must assert it too
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
    run_filter_gas: str = "AND pipeline_run_id = ?" if "pipeline_run_id" in db_cols_gas else ""
    placeholders: str = ",".join("?" * len(all_fb_ids))
    gas_params: list = list(all_fb_ids)
    if run_filter_gas:
        gas_params.append(CANONICAL_RUN)
    rows = conn.execute(
        f"""SELECT *,
            COALESCE({_quality_field()}, {NEUTRAL_PRIOR}) AS _quality,
            COALESCE(feedback_score, {NEUTRAL_PRIOR}) AS _feedback
            FROM fbs
            WHERE fb_id IN ({placeholders})
            {class_filter_gas}
            {run_filter_gas}
            ORDER BY _quality DESC, _feedback DESC""",
        gas_params,
    ).fetchall()

    results: list[dict] = [dict(r) for r in rows]

    # 5. Attach graph metadata and compute graph-aware score
    for fb in results:
        fid: str = str(fb.get("fb_id", ""))
        is_seed: bool = fid in seed_ids
        fb["_graph"] = graph.get(fid, {"related": [], "contradicts": [], "prerequisites": []})
        fb["_is_seed"] = is_seed

        # Graph-aware score: boost seed FBs, penalize distant ones
        quality: float = float(fb.get(_quality_field(), NEUTRAL_PRIOR) or NEUTRAL_PRIOR)
        feedback: float = float(fb.get("feedback_score", NEUTRAL_PRIOR) or NEUTRAL_PRIOR)
        graph_boost: float = 1.2 if is_seed else 0.9  # D2205: seed bias
        fb["_graph_score"] = quality * (1.0 + feedback) * graph_boost

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
    macro: str | None = None,
    depth: str | None = None,
    content_type: str | None = None,
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
                macro=macro,
                depth=depth,
                content_type=content_type,
            )
        else:
            results = search(
                conn, current_query,
                limit=limit,
                domain=domain,
                discipline=discipline,
                macro=macro,
                depth=depth,
                content_type=content_type,
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
            broader = search(
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


def _macro_choices() -> list[str]:
    """D-2884(a): valid operative 3-way macro routing buckets, from C21 config (no hardcode)."""
    from pipeline.discipline_macro import load_macro
    _, buckets, _ = load_macro()
    return sorted(buckets.keys())


def _content_type_choices() -> list[str]:
    """D-2944: the CLI's role choices, read from the content-type ontology (C12) - the
    request-side list must never be a hand-typed copy of the store-side enum."""
    from pipeline.content_types import CONTENT_TYPES

    return sorted(CONTENT_TYPES)


def _practicality_choices() -> list[str]:
    """BUG-702: S5 practical-applicability vocabulary, from C12 config (no hardcode)."""
    from pipeline.practicality import _load_config
    return list(_load_config()["labels"])


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
    parser.add_argument("--discipline", help="Filter by discipline (ADVISORY provenance facet)")
    parser.add_argument("--macro", choices=_macro_choices(),
                        help="D-2884(a): filter by OPERATIVE 3-way macro routing facet")
    parser.add_argument("--depth", help="Filter by depth")
    parser.add_argument("--discipline-raw", help="D2537: filter by raw discipline label (surgical facet)")
    parser.add_argument("--domains-raw", help="D2537: filter by raw domain label (surgical facet)")
    parser.add_argument("--practicality", choices=_practicality_choices(),
                        help="BUG-702: filter by S5 practical-applicability (immediately-applicable/context-dependent)")
    parser.add_argument("--content-type", choices=_content_type_choices(),
                        help="D-2944: filter by content ROLE (principle/process_template/"
                             "process_instance/tool_instruction/growth_edge). The non-principle "
                             "roles are QUARANTINE by design (D-2942), so pair it with e.g. "
                             "--status QUARANTINE to reach them.")
    parser.add_argument("--status", default="PASS", help="Filter by status (default: PASS)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-track", action="store_true",
                        help="D2188: disable usage tracking (read-only query)")
    parser.add_argument("--list-domains", action="store_true",
                        help="List all domains in DB")
    parser.add_argument("--list-macros", action="store_true",
                        help="D-2884(a): list operative macro routing buckets + counts")
    args = parser.parse_args()

    conn = get_conn()

    if args.list_domains:
        rows = conn.execute(
            "SELECT DISTINCT discipline, depth, status FROM fbs WHERE pipeline_run_id = ?",
            (CANONICAL_RUN,),
        ).fetchall()
        for r in rows:
            print(f"  {r['discipline']:30s} | {r['depth']:15s} | {r['status']}")
        conn.close()
        return

    if args.list_macros:
        rows = conn.execute(
            "SELECT discipline_macro, COUNT(*) as cnt FROM fbs WHERE pipeline_run_id = ? "
            "GROUP BY discipline_macro ORDER BY cnt DESC",
            (CANONICAL_RUN,),
        ).fetchall()
        for r in rows:
            print(f"  {r['discipline_macro'] or 'emerging':20s} {r['cnt']:>6}")
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
            macro=args.macro,
            depth=args.depth,
            content_type=args.content_type,
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
            macro=args.macro,
            depth=args.depth,
            content_type=args.content_type,
        )
    elif args.keyword or (args.domain or args.discipline or args.macro or args.depth or args.discipline_raw or args.domains_raw or args.practicality or args.content_type):
        results = search_keyword(
            conn,
            domain=args.domain,
            discipline=args.discipline,
            macro=args.macro,
            depth=args.depth,
            status=args.status,
            limit=args.limit,
            discipline_raw=args.discipline_raw,
            domains_raw=args.domains_raw,
            practicality=args.practicality,
            content_type=args.content_type,
        )
    elif args.fts:
        results = search_fts(conn, args.fts, limit=args.limit, macro=args.macro)
    elif args.vector:
        results = search_vector(conn, args.vector, limit=args.limit, macro=args.macro)
    elif args.hybrid:
        results = search_hybrid(
            conn, args.hybrid,
            domain=args.domain,
            discipline=args.discipline,
            macro=args.macro,
            depth=args.depth,
            limit=args.limit,
            discipline_raw=args.discipline_raw,
            domains_raw=args.domains_raw,
            practicality=args.practicality,
            content_type=args.content_type,
        )
    elif args.query:
        # D-2980: the DEFAULT query path routes through the DISPATCHER (D-2724 adoption). It
        # called search_hybrid() directly until D-2980, so the human surface served the
        # superseded RRF path while config declared retrieval.method=vector. The explicit leg
        # switches (--fts/--vector/--hybrid) stay, and they are now DECLARED in
        # config/serving_call_sites.yaml (INV-5) instead of being invisible.
        results = search(conn, args.query, limit=args.limit, macro=args.macro)
    else:
        # No query: show recent
        results = search_keyword(conn, status=args.status, limit=args.limit, macro=args.macro)

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
