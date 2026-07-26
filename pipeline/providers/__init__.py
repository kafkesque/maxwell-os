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

__all__ = [
    "MLXGenerationResult",
    "MLXInferenceProvider",
    "clear_providers",
    "get_mlx_provider",
]
