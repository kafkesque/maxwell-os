#!/usr/bin/env python3
"""
pipeline/embeddings.py — Text embedding service (bge-m3 via Ollama).
====================================================================
D2136 (2026-08-03): RESTORES semantic edges in compute_fb_relationships().

Previously `pipeline/embeddings.py` did not exist — stage4_merge.py imported
`embed_texts_bge_m3` inside try/except, so semantic_near edges were NEVER
computed (silent fallback to domain/discipline/source edges only). This is a
C16 violation fix: the module now exists and the import resolves.

C12: model + endpoint from config/pipeline_config.yaml (models.embeddings).
C3:  all embedding compute stays local (Ollama on localhost).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

# Allow direct execution (python3 pipeline/embeddings.py) and package import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Config (C12: no hardcoded values) ──────────────────────────────────────
import yaml

from pipeline.pipeline_paths import OLLAMA_URL

_CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
with open(_CFG_PATH) as f:
    _CFG = yaml.safe_load(f)

EMBED_MODEL: str = _CFG["models"]["embeddings"]["model"]
EMBED_DIM: int = int(_CFG["stage1_5"].get("embed_dim", 1024))
BATCH_SIZE: int = 32
TIMEOUT_S: int = 120


def embed_texts_bge_m3(texts: list[str], batch_size: int = BATCH_SIZE) -> np.ndarray:
    """Embed a list of texts using bge-m3 via the local Ollama endpoint.

    Args:
        texts: List of strings to embed (e.g. FB definitions).
        batch_size: Number of texts per HTTP request.

    Returns:
        np.ndarray of shape (len(texts), embed_dim), float32.

    Raises:
        RuntimeError: if the embedding endpoint is unreachable or returns
            malformed data (fail-visible — callers may catch and degrade).
    """
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)

    endpoint = f"{OLLAMA_URL}/api/embed"
    embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = json.dumps({"model": EMBED_MODEL, "input": batch}).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # C16: no silent errors — caller decides
            raise RuntimeError(
                f"embed_texts_bge_m3 failed (batch {i}:{i + len(batch)}): {e}"
            ) from e

        batch_embs = data.get("embeddings")
        if not batch_embs:
            raise RuntimeError(
                f"embed_texts_bge_m3: no 'embeddings' in response for batch "
                f"{i}:{i + len(batch)}"
            )
        embeddings.extend(batch_embs)

    arr = np.asarray(embeddings, dtype=np.float32)
    # Normalize rows for cosine similarity (matches stage4 usage of dot product)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    arr = arr / norms
    return arr


def embed_single(text: str) -> np.ndarray:
    """Embed one text (convenience wrapper)."""
    return embed_texts_bge_m3([text])[0]


if __name__ == "__main__":
    # Smoke test (no LLM, verifies endpoint + model)
    t0 = time.time()
    out = embed_texts_bge_m3([
        "Rational decisions weigh expected costs against benefits.",
        "Visual hierarchy guides the reader's attention through a layout.",
    ])
    print(f"✅ embed_texts_bge_m3: shape={out.shape} in {time.time() - t0:.1f}s")
    sim = float(np.dot(out[0], out[1]))
    print(f"   cosine(sample1, sample2) = {sim:.3f} (should be << 1.0)")
