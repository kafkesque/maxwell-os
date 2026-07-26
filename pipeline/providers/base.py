"""pipeline/providers/base.py — InferenceProvider + EmbeddingProvider protocols.

Authority: CONSTITUTION.md C21 (Swappable Infrastructure), D2055.
Ratified: 2026-07-22.

These protocols define the contract that ALL inference providers must satisfy.
Pipeline stages call resolve_provider(role).generate() — never a specific provider.

Swap OMLX → Ollama → vLLM → frontier API by changing ONE config line.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class GenerationResult(Protocol):
    """Standardized generation result across all providers."""
    text: str
    tokens_used: int
    model: str
    provider: str
    latency_ms: float


@runtime_checkable
class InferenceProvider(Protocol):
    """Protocol for text generation providers.

    Every provider must implement generate().
    Optional: generate_json() for schema-constrained output.
    """

    @abstractmethod
    def generate(self, prompt: str, *, system: str = "", max_tokens: int = 2048,
                 temperature: float = 0.0, stop: list[str] | None = None) -> GenerationResult:
        """Generate text from prompt. temp=0.0 by default (C9/R7)."""
        ...

    def generate_json(self, prompt: str, *, system: str = "", max_tokens: int = 2048,
                      temperature: float = 0.0) -> GenerationResult:
        """Generate JSON output. Falls back to generate() + json_repair if provider
        lacks native JSON schema enforcement (OMLX v0.5.1 doesn't have it — D2041 deferred)."""
        return self.generate(prompt, system=system, max_tokens=max_tokens, temperature=temperature)

    @abstractmethod
    def health_check(self) -> bool:
        """Check if provider is available and model is loaded."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier (e.g. 'omlx', 'ollama', 'openai')."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for text embedding providers.

    Every provider must implement embed() and batch_embed().
    """

    @abstractmethod
    def embed(self, text: str, *, model: str | None = None) -> list[float]:
        """Embed a single text."""
        ...

    @abstractmethod
    def batch_embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        """Embed multiple texts in a single call."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if provider is available."""
        ...

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimensionality of embeddings (e.g. 1024 for bge-m3)."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...

