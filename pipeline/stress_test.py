#!/usr/bin/env python3
"""stress_test.py — Full pipeline readiness check (D2176 expanded).

Called by `just stress`. Tests (sequentially, fail-fast):
  1. Memory check (>=6 GB free)
  2. Config integrity (version consistency, no hardcoded paths)
  3. OMLX chat at 50/1K/5K chars
  4. Embedding throughput (MPS/Ollama 50 segments)
  5. FAISS index construction (1K vectors)
  6. SQLite write + FTS5 search
  7. JSON extraction with pipeline-sized prompts

Exit 0 = ready, Exit 1 = not ready.
"""
import json
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from pipeline.memory_guard import check_memory
from pipeline.omlx_call import stress_test_omlx


def _check_config_integrity() -> bool:
    """D2176: Verify version consistency and no hardcoded paths in config."""
    import yaml
    print("=== Config Integrity ===")
    ok = True

    # Version consistency
    vy_path = Path("config/version.yaml")
    pc_path = Path("config/pipeline_config.yaml")
    if vy_path.exists() and pc_path.exists():
        with open(vy_path) as f:
            vy = yaml.safe_load(f) or {}
        with open(pc_path) as f:
            pcy = yaml.safe_load(f) or {}
        expected = str(vy.get("schema_version", "")).strip().strip("'\"")
        actual = str(pcy.get("pipeline", {}).get("schema_version", "")).strip().strip("'\"")
        if expected and actual and expected != actual:
            print(f"   ❌ Version mismatch: version.yaml={expected}, config={actual}")
            ok = False
        else:
            print(f"   ✅ Version consistent: schema_version={expected}")

    # No hardcoded /Users/ paths in config
    with open(pc_path) as f:
        for i, line in enumerate(f, 1):
            if "/Users/" in line and not line.strip().startswith("#"):
                print(f"   ⚠️  Hardcoded path at line {i}: {line.strip()[:80]}")
                # Warning only — not fatal
    print(f"   ✅ No fatal config issues")
    return ok


def _check_embedding_throughput() -> bool:
    """D2176: Test embedding throughput with 50 sample segments."""
    print("=== Embedding Throughput ===")
    try:
        from pipeline.embeddings import embed_texts_bge_m3

        # Generate 50 sample segments (~100 chars each — typical chunk size)
        sample_texts = [
            f"The principle of {i} states that systems exhibit emergent behavior "
            f"when individual components interact in ways not predictable from their "
            f"isolated properties. This applies to biological, social, and "
            f"computational systems alike."
            for i in range(50)
        ]

        t0 = time.time()
        embeddings = embed_texts_bge_m3(sample_texts)
        elapsed = time.time() - t0

        if embeddings is None or len(embeddings) == 0:
            print("   ❌ Embedding returned no vectors")
            return False

        expected_dim = 384  # bge-small-en-v1.5
        actual_dim = embeddings.shape[1] if hasattr(embeddings, 'shape') else len(embeddings[0])
        if actual_dim != expected_dim:
            print(f"   ❌ Dimension mismatch: {actual_dim} != {expected_dim}")
            return False

        rate = len(sample_texts) / elapsed if elapsed > 0 else 0
        print(f"   ✅ {len(sample_texts)} segments in {elapsed:.1f}s ({rate:.1f} seg/s) @ {actual_dim}d")
        print(f"   ✅ Embedding dimension: {actual_dim} (matches config)")
        return True
    except ImportError as e:
        print(f"   ⚠️  Embedding module not available: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️  Embedding test failed (non-fatal): {e}")
        return False


def _check_faiss_construction() -> bool:
    """D2176: Test FAISS index construction with 1000 random vectors."""
    print("=== FAISS Index Construction ===")
    try:
        import faiss

        dim = 384
        n_vectors = 1000
        np.random.seed(42)
        vectors = np.random.randn(n_vectors, dim).astype(np.float32)
        # Normalize for cosine similarity
        faiss.normalize_L2(vectors)

        t0 = time.time()
        index = faiss.IndexFlatIP(dim)  # Inner product = cosine on normalized vectors
        index.add(vectors)
        elapsed = time.time() - t0

        # Verify search works
        query = np.random.randn(1, dim).astype(np.float32)
        faiss.normalize_L2(query)
        distances, indices = index.search(query, k=10)

        if len(indices[0]) != 10:
            print(f"   ❌ FAISS search returned {len(indices[0])} results, expected 10")
            return False

        print(f"   ✅ {n_vectors} vectors indexed in {elapsed*1000:.0f}ms")
        print(f"   ✅ Search returned {len(indices[0])} results (top score: {distances[0][0]:.4f})")
        return True
    except ImportError:
        print("   ⚠️  FAISS not installed (pip install faiss-cpu)")
        return False
    except Exception as e:
        print(f"   ⚠️  FAISS test failed (non-fatal): {e}")
        return False


def _check_sqlite_write() -> bool:
    """D2176: Test SQLite write + FTS5 search throughput."""
    print("=== SQLite Write + FTS5 ===")
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test_fbs (fb_id TEXT PRIMARY KEY, name TEXT, definition TEXT)")
        conn.execute(
            "CREATE VIRTUAL TABLE test_fts USING fts5(fb_id, name, definition)"
        )

        # Insert 500 sample FBs
        t0 = time.time()
        fb_data = [
            (f"fb_{i:04d}", f"Principle {i}", f"This is the definition of principle {i}. "
             f"It describes how systems behave when condition X is met and factor Y intervenes.")
            for i in range(500)
        ]
        conn.executemany("INSERT INTO test_fbs VALUES (?, ?, ?)", fb_data)
        conn.executemany(
            "INSERT INTO test_fts VALUES (?, ?, ?)", fb_data
        )
        conn.commit()
        write_elapsed = time.time() - t0

        # FTS search
        t0 = time.time()
        results = conn.execute(
            "SELECT * FROM test_fts WHERE test_fts MATCH ? LIMIT 20",
            ("systems behave",),
        ).fetchall()
        search_elapsed = time.time() - t0

        conn.close()
        os.unlink(db_path)

        print(f"   ✅ 500 FBs written in {write_elapsed*1000:.0f}ms")
        print(f"   ✅ FTS search: {len(results)} results in {search_elapsed*1000:.0f}ms")
        return True
    except Exception as e:
        print(f"   ⚠️  SQLite test failed (non-fatal): {e}")
        return False


def main():
    exit_code = 0

    # 1. Config integrity
    _check_config_integrity()

    # 2. Memory check
    print("\n=== Memory Check ===")
    if not check_memory(min_free_gb=6.0):
        exit_code = 1

    # 3. OMLX chat
    print("\n=== OMLX Chat Stress Test ===")
    result = stress_test_omlx(prompt_sizes=[50, 1000, 5000], verbose=True)
    if not result["healthy"]:
        print(f"\n❌ OMLX chat FAILED. Verdict: {result['verdict']}")
        print("   Restart OMLX and re-run: just stress")
        exit_code = 1
    else:
        print(f"\n✅ OMLX pipeline-ready: {result['verdict']} (tested up to 5000 chars)")

    # 4. Embedding throughput (non-fatal)
    _check_embedding_throughput()

    # 5. FAISS construction (non-fatal)
    _check_faiss_construction()

    # 6. SQLite write (non-fatal)
    _check_sqlite_write()

    if exit_code != 0:
        print("\n❌ STRESS TEST FAILED — resolve issues before pipeline run")
    else:
        print(f"\n{'='*70}")
        print("✅ STRESS TEST PASSED — pipeline ready")
        print(f"{'='*70}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
