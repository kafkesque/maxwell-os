#!/usr/bin/env python3
"""
_ollama_embed.py — Shared OllamaEmbeddingFunction for Chromadb.
Import from here — never copy-paste into scripts.

v2.0 2026-06-05: Added batch embedding for 5-10x speedup.
                  Single-doc API still available for Chromadb compatibility.

Usage:
    from _ollama_embed import OllamaEmbeddingFunction, batch_embed
    # Chromadb-compatible (one doc at a time):
    chroma_collection.add(embeddings=OllamaEmbeddingFunction(), ...)
    # Batch mode (N docs in one API call):
    embeddings = batch_embed(texts, model="nomic-embed-text")
"""

# ── Type aliases (replaces chromadb imports) ──────────────────────────────
from collections.abc import Sequence


class EmbeddingQuarantineError(Exception):
    """Raised when embedding fails and document must be quarantined.

    D2196: Zero-vector fallback DELIBERATELY REMOVED.
    Never insert [0.0]*dim into FAISS — it creates false convergence clusters
    that satisfy BORP (multiple sources!) from network errors alone.
    """
    pass


from pipeline.pipeline_paths import (
    OLLAMA_BATCH_SIZE,
    OLLAMA_HOST,
    OLLAMA_EMBED_MAX_CHARS,
    OLLAMA_PORT,
)

OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embed"  # BUG-028 FIX

Documents = Sequence[str]
Embeddings = Sequence[Sequence[float]]


class EmbeddingFunction:
    """Simple embedding function protocol (replaces chromadb.EmbeddingFunction)."""

    def __call__(self, input: Documents) -> Embeddings:
        raise NotImplementedError


# ── Constants (T0.4: de-hardcoded — sourced from pipeline_config.yaml) ────
EMBED_MAX_CHARS: int = OLLAMA_EMBED_MAX_CHARS  # bge-m3 embed context (from config)
BATCH_SIZE: int = OLLAMA_BATCH_SIZE            # max texts per batch (from config)
# OLLAMA_URL now configured from pipeline_paths.py (was hardcoded localhost)


def batch_embed(texts: list[str], model: str = None) -> list[list[float]]:
    """Embed multiple texts in a single Ollama API call (float32, 768-dim).

    Uses Ollama's /api/embed batch endpoint — ~5-10x faster than single-doc
    embedding. Falls back to single-doc on failure.

    Args:
        texts: List of text strings to embed.
        model: Embedding model name (default: nomic-embed-text).

    Returns:
        List of embedding vectors (list[float] each), same order as input.
        Zero vectors for failed items.
    """
    if model is None:
        from pipeline.pipeline_paths import EMBED_MODEL
        model = EMBED_MODEL

    import requests

    results = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        # Truncate long texts
        truncated = [t[:EMBED_MAX_CHARS] for t in batch]
        try:
            resp = requests.post(
                OLLAMA_URL,
                json={"model": model, "input": truncated},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            batch_embs = data.get("embeddings", [])
            if len(batch_embs) == len(truncated):
                results.extend(batch_embs)
            else:
                # Partial response — pad with zeros
                results.extend(batch_embs)
                missing = len(truncated) - len(batch_embs)
                dim = len(batch_embs[0]) if batch_embs else 768
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Embedding batch partial response: {missing}/{len(truncated)} missing. Quarantining batch.")
                raise EmbeddingQuarantineError(
                    f"Batch embedding returned {len(batch_embs)}/{len(truncated)} vectors. "
                    f"{missing} documents failed. Full batch quarantined to prevent FAISS contamination."
                )
        except EmbeddingQuarantineError:
            raise
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Embedding batch failed: {e}. Quarantining batch to prevent zero-vector contamination.")
            raise EmbeddingQuarantineError(
                f"Batch embedding completely failed ({e}). "
                f"Batch of {len(truncated)} documents quarantined. "
                f"Zero-vector fallback DELIBERATELY REMOVED (D2196) — never insert synthetic vectors into FAISS."
            ) from e
    return results


class OllamaEmbeddingFunction(EmbeddingFunction):
    """Chromadb-compatible embedding function using Ollama (model from EMBED_MODEL).

    Uses batch embedding internally for speed when Chromadb sends multiple docs.
    """

    def __init__(self) -> None:
        """Required for Chromadb v0.5+ API compatibility."""
        super().__init__()
        from pipeline.pipeline_paths import EMBED_MODEL
        self._model = EMBED_MODEL

    def __call__(self, input: Documents) -> Embeddings:
        """Batch-embed all documents in one API call when possible."""
        # Chromadb calls this with list[Documents] — use batch mode
        if len(input) > 1:
            return batch_embed(list(input))

        # Single document — delegate to batch_embed (single code path).
        # D2202: Replaced `import ollama` (undeclared dependency) with delegation
        # to batch_embed which uses requests directly. The ollama Python package
        # is intentionally NOT in requirements.txt — all embedding uses HTTP API.
        return batch_embed(list(input))
