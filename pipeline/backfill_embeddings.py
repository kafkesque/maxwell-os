#!/usr/bin/env python3
"""
backfill_embeddings.py — Backfill vec_fbs from persisted fbs.definition.
========================================================================
D2509 (M1 fix). Two independent failures made vector search dead at D2508/S6:

  1. **Env:** `/usr/local/bin/python3` (python.org framework 3.12.1) compiled
     SQLite WITHOUT `enable_load_extension` (`SQLITE_OMIT_LOAD_EXTENSION`), so
     `sqlite_vec.load()` raised `AttributeError` and `vec_fbs` was never created.
  2. **Dimension contract (M1):** `insert_embedding`/`search_vector` used
     `ollama_embed.batch_embed` (raw bge-m3 **1024d**) against a `vec_fbs
     float[512]` table — a silent dimension mismatch that would misrank even
     after the env was fixed.

This script re-embeds every committed `fbs.definition` (bge-m3 → Matryoshka
**512d** → L2-normalized) and populates `vec_fbs`. It MUST run under a Python
build with `enable_load_extension`:

    /opt/homebrew/bin/python3 pipeline/backfill_embeddings.py
    /opt/homebrew/bin/python3 pipeline/backfill_embeddings.py --limit 50   # smoke

Idempotent: clears `vec_fbs` and re-inserts. No S5 re-run — reads committed
`fbs` rows directly (single source of truth).

Usage:
    python3 pipeline/backfill_embeddings.py [--db PATH] [--limit N] [--batch-size N] [--dry-run]
"""

from __future__ import annotations

import argparse
import sqlite3
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH, S15_EMBED_DIM
from pipeline.schema_accessor import fb_definition  # noqa: F401  (kept for clarity of the contract)


CREATE_VEC_TABLE = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS vec_fbs USING vec0(
    definition_embedding float[{S15_EMBED_DIM}]
);
"""


def _load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load sqlite-vec into the connection. Returns False (and logs) on failure."""
    try:
        import sqlite_vec
    except ImportError:
        print("  ❌ sqlite-vec not installed in this Python. Run: pip install sqlite-vec")
        return False
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except AttributeError as e:
        print(f"  ❌ This Python build lacks enable_load_extension ({e}).")
        print("     Use /opt/homebrew/bin/python3 or the knowledge-pipeline conda env.")
        return False
    except Exception as e:
        print(f"  ❌ sqlite-vec failed to load: {e}")
        return False


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch via pipeline.embeddings (bge-m3 → 512d → L2-normalized)."""
    from pipeline.embeddings import embed_texts_bge_m3

    arr = embed_texts_bge_m3(texts)
    if arr.shape[1] != S15_EMBED_DIM:
        raise RuntimeError(
            f"embed_texts_bge_m3 returned dim {arr.shape[1]} != S15_EMBED_DIM={S15_EMBED_DIM}"
        )
    return [[float(x) for x in row] for row in arr]


def backfill(
    db_path: Path,
    limit: int | None,
    batch_size: int,
    dry_run: bool,
    contextual: bool = False,
    vec_table: str = "vec_fbs",
) -> int:
    """Backfill a vec table from fbs (definition or contextual text).

    D2511 (S1): `contextual=True` embeds context-prefixed text (discipline/domains/
    name + definition) into a SEPARATE table (`vec_fbs_ctx` by default) so the
    production vec_fbs is untouched — enabling a clean A/B in retrieval_benchmark.

    Returns number of rows embedded.
    """
    if not db_path.exists():
        print(f"  ❌ DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row

    if not _load_sqlite_vec(conn):
        conn.close()
        sys.exit(1)

    # Create the vec table (may already exist — IF NOT EXISTS is safe)
    conn.execute(CREATE_VEC_TABLE.replace("vec_fbs", vec_table))

    # Clear any stale rows so we never mix 1024d (pre-fix) with 512d (post-fix)
    # vectors in the same table. Idempotent re-run replaces the whole index.
    conn.execute(f"DELETE FROM {vec_table}")

    # Read rows (single source of truth: committed fbs rows). For contextual mode
    # we also need discipline/domains/name to build the context prefix.
    select_cols = "rowid, definition"
    if contextual:
        select_cols += ", discipline, domains, name"
    sql = f"SELECT {select_cols} FROM fbs"
    if limit:
        sql += f" ORDER BY rowid LIMIT {int(limit)}"
    rows = conn.execute(sql).fetchall()
    total = len(rows)
    mode = "contextual (S1)" if contextual else "definition"
    print(f"  🧠 Backfilling {total} {mode} embeddings "
          f"(bge-m3 → {S15_EMBED_DIM}d, batch={batch_size}, table={vec_table})")

    if dry_run:
        print("  🔍 --dry-run: would embed (no writes).")
        conn.close()
        return total

    if contextual:
        from pipeline.embeddings import contextualize_text

    done = 0
    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        if contextual:
            texts = [contextualize_text(dict(r)) for r in batch]
        else:
            texts = [r["definition"] or "" for r in batch]
        try:
            embs = _embed(texts)
        except Exception as e:
            # C16: no silent errors — fail loudly, do not write a partial index
            # that would look complete.
            conn.rollback()
            conn.close()
            print(f"  ❌ Embedding batch {i}:{i + len(batch)} failed: {e}")
            sys.exit(1)
        for r, emb in zip(batch, embs):
            blob = struct.pack(f"{len(emb)}f", *emb)
            conn.execute(
                f"INSERT INTO {vec_table}(rowid, definition_embedding) VALUES (?, ?)",
                (r["rowid"], blob),
            )
        done += len(batch)
        if done % (batch_size * 5) == 0 or done == total:
            print(f"    {done}/{total} embedded")

    conn.commit()

    vec_count = conn.execute(f"SELECT COUNT(*) FROM {vec_table}").fetchone()[0]
    orphaned = conn.execute(
        f"SELECT COUNT(*) FROM {vec_table} v LEFT JOIN fbs f ON v.rowid = f.rowid "
        "WHERE f.rowid IS NULL"
    ).fetchone()[0]
    conn.close()

    print(f"  ✅ {vec_table}: {vec_count} rows, {orphaned} orphaned")
    if vec_count == total:
        print("  ✅ Vector index READY (matches fbs count)")
    else:
        print(f"  ⚠️  {vec_table}={vec_count} vs fbs subset={total} (expected on --limit runs)")
    return vec_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill vec_fbs from fbs.definition (D2509)")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite DB path")
    parser.add_argument("--limit", type=int, default=None, help="Only embed first N rows (smoke)")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    parser.add_argument("--contextual", action="store_true",
                        help="S1: embed context-prefixed text into a separate vec_fbs_ctx table")
    parser.add_argument("--vec-table", default="vec_fbs",
                        help="Target vec table name (default vec_fbs; contextual → vec_fbs_ctx)")
    args = parser.parse_args()

    vec_table = args.vec_table
    if args.contextual and vec_table == "vec_fbs":
        vec_table = "vec_fbs_ctx"
    backfill(args.db, args.limit, args.batch_size, args.dry_run, args.contextual, vec_table)


if __name__ == "__main__":
    main()
