"""pipeline/providers — Swappable inference abstraction (C21, D2055).

Every pipeline stage resolves its provider through this layer.
No stage file touches a provider implementation directly.

Available providers:
  - MLXInferenceProvider: Direct MLX inference (no HTTP, no server)
  - Future: OMLXProvider, OllamaProvider, OpenAIProvider
"""

from pipeline.providers.mlx_provider import (
    MLXGenerationResult,
    MLXInferenceProvider,
    clear_providers,
    get_mlx_provider,
)
# D2306: OMLX + Ollama providers implement the InferenceProvider/EmbeddingProvider
# protocols (D2055). Closes the D2300 modularity gap where stages imported
# omlx_call/ollama_embed directly.
from pipeline.providers.omlx_provider import (
    OMLXGenerationResult,
    OMLXInferenceProvider,
)
from pipeline.providers.ollama_provider import OllamaEmbeddingProvider

__all__ = [
    "MLXGenerationResult",
    "MLXInferenceProvider",
    "clear_providers",
    "get_mlx_provider",
    "OMLXGenerationResult",
    "OMLXInferenceProvider",
    "OllamaEmbeddingProvider",
]
