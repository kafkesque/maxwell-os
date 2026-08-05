#!/usr/bin/env python3
"""
retrieve.py — Hybrid search: SQL + FTS5 + sqlite-vec.
========================================================
Authority: CONSTITUTION.md §2.3

Three retrieval modes:
  1. Keyword: SQL query on domains, discipline, depth, status
  2. Full-text: FTS5 search on name, definition, keywords
  3. Vector: sqlite-vec cosine similarity (if available)

Usage:
    python3 pipeline/retrieve.py --keyword "systems thinking"
    python3 pipeline/retrieve.py --domain "ai & agents" --depth universal
    python3 pipeline/retrieve.py --fts "feedback loops"
    python3 pipeline/retrieve.py --vector "how to build resilient systems"
    python3 pipeline/retrieve.py --hybrid "decision making"  # FTS + keyword
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH


def get_conn() -> sqlite3.Connection:
    """Get a read-only connection to the database."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def search_keyword(
    conn: sqlite3.Connection,
    domain: str = None,
    discipline: str = None,
    depth: str = None,
    status: str = "PASS",
    limit: int = 20,
    exclude_summaries: bool = True,
) -> list[dict]:
    """Keyword-based SQL search. Excludes summary FBs by default."""
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if domain:
        conditions.append("domains LIKE ?")
        params.append(f"%{domain}%")
    if discipline:
        conditions.append("discipline = ?")
        params.append(discipline)
    if depth:
        conditions.append("depth = ?")
        params.append(depth)
    if exclude_summaries:
        conditions.append("(is_summary = 0 OR is_summary IS NULL)")

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM fbs WHERE {where} ORDER BY borp_score DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def search_fts(conn: sqlite3.Connection, query: str, limit: int = 20,
             exclude_summaries: bool = True) -> list[dict]:
    """Full-text search on name, definition, keywords. Excludes summaries by default."""
    try:
        rows = conn.execute("""
            SELECT f.* FROM fbs f
            JOIN fbs_fts ft ON f.rowid = ft.rowid
            WHERE fbs_fts MATCH ?
              AND (f.is_summary = 0 OR f.is_summary IS NULL)
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.OperationalError:
        # FTS5 may not be available — fall back to LIKE
        like_query = f"%{query}%"
        if exclude_summaries:
            rows = conn.execute("""
                SELECT * FROM fbs
                WHERE (name LIKE ? OR definition LIKE ? OR keywords LIKE ?)
                  AND (is_summary = 0 OR is_summary IS NULL)
                ORDER BY borp_score DESC
                LIMIT ?
            """, (like_query, like_query, like_query, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM fbs
                WHERE name LIKE ? OR definition LIKE ? OR keywords LIKE ?
                ORDER BY borp_score DESC
                LIMIT ?
            """, (like_query, like_query, like_query, limit)).fetchall()
        return [_row_to_dict(r) for r in rows]


def search_vector(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Vector similarity search using pre-computed sqlite-vec embeddings.

    BUG-004 FIX: Embeddings are pre-computed at Stage 6 commit time and stored
    in vec_fbs. Only the query is embedded at search time (O(1) not O(n)).
    Falls back to FTS if vec_fbs is not available.
    """
    try:
        import struct

        import numpy as np

        from pipeline.ollama_embed import batch_embed

        # Embed the query
        embeddings = batch_embed([query])
        if not embeddings or not embeddings[0]:
            print("  ⚠️  Embedding failed, falling back to FTS")
            return search_fts(conn, query, limit)

        query_vec = embeddings[0]
        query_blob = struct.pack(f'{len(query_vec)}f', *query_vec)

        # Try sqlite-vec similarity search on pre-computed embeddings
        try:
            rows = conn.execute("""
                SELECT fbs.*, vec_fbs.distance
                FROM vec_fbs
                JOIN fbs ON fbs.rowid = vec_fbs.rowid
                WHERE fbs.status = 'PASS'
                    AND definition_embedding MATCH ?
                    AND k = ?
                ORDER BY distance
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
) -> list[dict]:
    """Hybrid: FTS + keyword combined."""
    fts_results = search_fts(conn, query, limit=limit * 2)
    kw_results = search_keyword(
        conn, domain=domain, discipline=discipline, depth=depth, limit=limit * 2
    )

    # Merge and deduplicate by fb_id
    seen: set[str] = set()
    merged = []
    for r in fts_results:
        if r["fb_id"] not in seen:
            seen.add(r["fb_id"])
            merged.append(r)
    for r in kw_results:
        if r["fb_id"] not in seen:
            seen.add(r["fb_id"])
            merged.append(r)

    return merged[:limit]


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert sqlite3.Row to dict, parsing JSON fields."""
    d = dict(row)
    for field in ["domains", "source_clusters", "source_books",
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


def main():
    parser = argparse.ArgumentParser(description="Hybrid FB retrieval")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--keyword", "-k", help="Keyword search")
    parser.add_argument("--fts", "-f", help="Full-text search")
    parser.add_argument("--vector", "-v", help="Vector similarity search")
    parser.add_argument("--hybrid", help="Hybrid (FTS + keyword) search")
    parser.add_argument("--domain", "-d", help="Filter by domain")
    parser.add_argument("--discipline", help="Filter by discipline")
    parser.add_argument("--depth", help="Filter by depth")
    parser.add_argument("--status", default="PASS", help="Filter by status (default: PASS)")
    parser.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--list-domains", action="store_true", help="List all domains in DB")
    args = parser.parse_args()

    conn = get_conn()

    if args.list_domains:
        rows = conn.execute("SELECT DISTINCT discipline, depth, status FROM fbs").fetchall()
        for r in rows:
            print(f"  {r['discipline']:30s} | {r['depth']:15s} | {r['status']}")
        conn.close()
        return

    # Determine search mode
    results = []
    if args.keyword or (args.domain or args.discipline or args.depth):
        results = search_keyword(
            conn,
            domain=args.domain,
            discipline=args.discipline,
            depth=args.depth,
            status=args.status,
            limit=args.limit,
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
        )
    elif args.query:
        # Default: try hybrid
        results = search_hybrid(conn, args.query, limit=args.limit)
    else:
        # No query: show recent
        results = search_keyword(conn, status=args.status, limit=args.limit)

    conn.close()

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"\n🔍 Found {len(results)} results\n")
        for i, fb in enumerate(results, 1):
            print(format_fb(fb, i))

    if not results:
        print("  (no results found)")


if __name__ == "__main__":
    main()
