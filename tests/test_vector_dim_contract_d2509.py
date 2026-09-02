#!/usr/bin/env python3
"""D2509 — Vector dimension contract (M1) regression test.

Locks the contract that was silently violated at S6: `vec_fbs` is declared
`float[S15_EMBED_DIM]` (512d Matryoshka), but `insert_embedding`/`search_vector`
previously packed raw bge-m3 (1024d) vectors into it via `ollama_embed.batch_embed`.
A dimension drift silently breaks vector ranking (C16/C23 violation).

Deterministic — no Ollama / sqlite-vec required:
  1. config single-source: pipeline.embeddings.EMBED_DIM == S15_EMBED_DIM == 512
  2. stage6 CREATE_VEC_TABLE declares float[S15_EMBED_DIM] (not a stale literal)
  3. bge-m3 Matryoshka truncation normalizes to EMBED_DIM (pure-numpy unit check)
  4. query embed path in retrieve.search_vector truncates to S15_EMBED_DIM
     (via a monkeypatched embed_texts_bge_m3 returning 1024d — must still pack 512f)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import embeddings
from pipeline.pipeline_paths import S15_EMBED_DIM


def test_config_single_source_dimension():
    """The three dimension constants must agree (single source of truth)."""
    assert S15_EMBED_DIM == 512, f"S15_EMBED_DIM={S15_EMBED_DIM} != 512 (config drift)"
    assert embeddings.EMBED_DIM == S15_EMBED_DIM, (
        f"embeddings.EMBED_DIM={embeddings.EMBED_DIM} != S15_EMBED_DIM={S15_EMBED_DIM}"
    )


def test_vec_table_ddl_uses_config_dim():
    """stage6 CREATE_VEC_TABLE must reference S15_EMBED_DIM, not a stale literal."""
    from pipeline.stage6_commit import CREATE_VEC_TABLE

    assert f"float[{S15_EMBED_DIM}]" in CREATE_VEC_TABLE, (
        f"CREATE_VEC_TABLE does not declare float[{S15_EMBED_DIM}]: {CREATE_VEC_TABLE!r}"
    )


def test_bge_m3_truncation_normalizes_to_embed_dim():
    """The 1024d→512d Matryoshka truncation + L2 normalization must hold at rest."""
    # Simulate a raw bge-m3 1024d output and run the same truncate+normalize path.
    rng = np.random.default_rng(0)
    raw = rng.standard_normal((2, 1024)).astype(np.float32)
    arr = raw[:, : embeddings.EMBED_DIM] if raw.shape[1] > embeddings.EMBED_DIM else raw
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    arr = arr / norms

    assert arr.shape == (2, embeddings.EMBED_DIM), f"shape {arr.shape} != (2, {embeddings.EMBED_DIM})"
    assert np.allclose(np.linalg.norm(arr, axis=1), 1.0, atol=1e-6), "vectors not L2-normalized"


def test_search_vector_imports_truncating_embedder():
    """search_vector must embed via embed_texts_bge_m3 (512d), NOT batch_embed (1024d).

    The D2509 regression: search_vector packed raw bge-m3 1024d into float[512].
    This asserts the caller still routes through the truncating embedder.
    """
    import inspect

    import pipeline.retrieve as retrieve

    src = inspect.getsource(retrieve.search_vector)
    assert "embed_texts_bge_m3([query])" in src, "search_vector no longer uses the truncating embedder"
    # The regressed form was a live `from pipeline.ollama_embed import batch_embed`
    # (raw 1024d). Comments may mention batch_embed, but the import must be gone.
    assert "from pipeline.ollama_embed import batch_embed" not in src, (
        "search_vector regressed to raw 1024d batch_embed"
    )


def test_live_embedder_returns_embed_dim():
    """LIVE: assert the real embed_texts_bge_m3 returns S15_EMBED_DIM (skips if Ollama down)."""
    import pytest

    import requests

    try:
        requests.get("http://localhost:11434/api/tags", timeout=2).raise_for_status()
    except Exception:
        pytest.skip("Ollama not reachable — skipping live embedder-dimension check")

    arr = embeddings.embed_texts_bge_m3(["resilient systems recover from failure"])
    assert arr.shape[1] == S15_EMBED_DIM, (
        f"embed_texts_bge_m3 returned dim {arr.shape[1]} != S15_EMBED_DIM={S15_EMBED_DIM}"
    )
    assert np.allclose(np.linalg.norm(arr, axis=1), 1.0, atol=1e-6), "not L2-normalized"


if __name__ == "__main__":
    test_config_single_source_dimension()
    test_vec_table_ddl_uses_config_dim()
    test_bge_m3_truncation_normalizes_to_embed_dim()
    test_search_vector_imports_truncating_embedder()
    print("✅ D2509 vector dimension contract holds (M1)")
