"""pipeline/providers/ollama_provider.py — Ollama embedding provider.

Authority: CONSTITUTION.md C21 (Swappable Infrastructure), D2055, D2306.
Ratified: 2026-08-12.

Implements the EmbeddingProvider protocol from pipeline/providers/base.py
for the Ollama HTTP server. This closes the D2300 modularity gap where
`ollama_embed.py` was imported directly from stage1_5 instead of through
a swappable provider abstraction.

The provider delegates to `pipeline.ollama_embed.batch_embed` (single source
of truth for the batch /api/embed call + quarantine-on-failure logic) so there
is exactly one embedding HTTP code path.

Usage:
    from pipeline.providers.ollama_provider import OllamaEmbeddingProvider

    provider = OllamaEmbeddingProvider()
    vec = provider.embed("Some text.")
    vecs = provider.batch_embed(["a", "b"])
"""

from __future__ import annotations

from pipeline.ollama_embed import batch_embed


class OllamaEmbeddingProvider:
    """Ollama HTTP server adapter implementing the EmbeddingProvider protocol.

    Delegates to ollama_embed.batch_embed for all HTTP work (batch endpoint,
    EmbeddingQuarantineError on failure). Protocol method signatures match
    base.py exactly.
    """

    def __init__(self, model: str | None = None) -> None:
        """Initialize an Ollama embedding provider.

        Args:
            model: Embedding model name. None → read EMBED_MODEL from config (C12).
        """
        from pipeline.pipeline_paths import EMBED_MODEL

        self.model_name: str = model or EMBED_MODEL

    def embed(self, text: str, *, model: str | None = None) -> list[float]:
        """Embed a single text (delegates to batch path for one code path)."""
        vecs = self.batch_embed([text], model=model)
        return vecs[0] if vecs else []

    def batch_embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        """Embed multiple texts via Ollama /api/embed batch endpoint."""
        return batch_embed(texts, model=model or self.model_name)

    def health_check(self) -> bool:
        """Check Ollama server availability via a trivial embedding call.

        A 1-token probe embed is the only reliable liveness signal —
        Ollama has no /health endpoint that guarantees the embedding model
        is loaded. Returns False on any exception (fail-closed, C23).
        """
        try:
            vecs = self.batch_embed(["health"])
            return bool(vecs) and len(vecs[0]) > 0
        except Exception:
            return False

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of embeddings.

        bge-m3 → 1024. Derived lazily from a probe embed (C12: no hardcoded
        magic number; dimension is model-dependent and must not drift).
        """
        try:
            vecs = self.batch_embed(["dim"])
            return len(vecs[0]) if vecs else 0
        except Exception:
            return 0

    @property
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        return f"ollama:{self.model_name}"
