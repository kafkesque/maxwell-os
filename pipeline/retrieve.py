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
) -> list[dict]:
    """Keyword-based SQL search."""
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

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM fbs WHERE {where} ORDER BY borp_score DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def search_fts(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[dict]:
    """Full-text search on name, definition, keywords."""
    try:
        rows = conn.execute("""
            SELECT f.* FROM fbs f
            JOIN fbs_fts ft ON f.rowid = ft.rowid
            WHERE fbs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
        return [_row_to_dict(r) for r in rows]
    except sqlite3.OperationalError:
        # FTS5 may not be available — fall back to LIKE
        like_query = f"%{query}%"
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
    """Vector similarity search using sqlite-vec (if available)."""
    try:
        # Try to use sqlite-vec
        import requests
        from pipeline.ollama_embed import batch_embed

        # Embed the query
        embeddings = batch_embed([query], model="nomic-embed-text")
        if not embeddings or not embeddings[0]:
            print("  ⚠️  Embedding failed, falling back to FTS")
            return search_fts(conn, query, limit)

        query_vec = embeddings[0]

        # sqlite-vec requires the extension to be loaded
        # For now, fall back to loading all and computing cosine similarity
        rows = conn.execute(
            "SELECT * FROM fbs WHERE status = 'PASS'"
        ).fetchall()

        # Embed all definitions (in-memory, not ideal for large DBs)
        definitions = [r["definition"] for r in rows]
        def_embeddings = batch_embed(definitions, model="nomic-embed-text")

        # Compute cosine similarity
        import numpy as np
        query_vec = np.array(query_vec)
        similarities = []
        for i, emb in enumerate(def_embeddings):
            if emb and len(emb) == len(query_vec):
                sim = np.dot(query_vec, np.array(emb)) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(np.array(emb)) + 1e-8
                )
                similarities.append((float(sim), i))

        similarities.sort(key=lambda x: x[0], reverse=True)
        top_indices = [s[1] for s in similarities[:limit]]
        return [_row_to_dict(rows[i]) for i in top_indices]

    except ImportError:
        print("  ⚠️  numpy not available, falling back to FTS")
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


def format_fb(fb: dict, index: int = None) -> str:
    """Format an FB for display."""
    lines = []
    if index is not None:
        lines.append(f"─── #{index} ───────────────────────────────────────")
    lines.append(f"📌 {fb.get('name', 'unnamed')}")
    lines.append(f"   Discipline: {fb.get('discipline', 'N/A')} | "
                  f"Depth: {fb.get('depth', 'N/A')} | "
                  f"Status: {fb.get('status', 'N/A')}")
    lines.append(f"   Domains: {', '.join(fb.get('domains', []))}")
    lines.append(f"   Definition: {fb.get('definition', 'N/A')[:200]}...")
    if fb.get("keywords"):
        lines.append(f"   Keywords: {fb.get('keywords')}")
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
