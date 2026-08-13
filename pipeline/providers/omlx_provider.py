"""pipeline/providers/omlx_provider.py — OMLX HTTP inference provider.

Authority: CONSTITUTION.md C21 (Swappable Infrastructure), D2055, D2306.
Ratified: 2026-08-12.

Implements the InferenceProvider protocol from pipeline/providers/base.py
for the OMLX HTTP server. This closes the D2300 modularity gap where
`omlx_call.py` was imported directly from stage2/4/5 instead of through
a swappable provider abstraction.

The provider delegates to `pipeline.omlx_call.call_omlx` (single source of
truth for retry/circuit-breaker/cold-reload logic) so there is exactly one
HTTP code path — no drift between direct calls and protocol calls.

Usage:
    from pipeline.providers.omlx_provider import OMLXInferenceProvider

    provider = OMLXInferenceProvider("Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
    result = provider.generate("Extract principles...", system="Be concise.")
    result.text  # str
    result.latency_ms  # float
"""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.omlx_call import call_omlx, call_omlx_json, check_omlx_health


@dataclass
class OMLXGenerationResult:
    """GenerationResult-compatible result from the OMLX provider (D2055)."""
    text: str
    tokens_used: int
    model: str
    provider: str = "omlx"
    latency_ms: float = 0.0


class OMLXInferenceProvider:
    """OMLX HTTP server adapter implementing the InferenceProvider protocol.

    Delegates to omlx_call for all HTTP work (retry, circuit breaker,
    cold-reload recovery). The protocol method signatures match base.py
    exactly so this provider is drop-in swappable with MLXInferenceProvider.
    """

    def __init__(self, model: str | None = None, *, max_tokens_default: int = 2048) -> None:
        """Initialize an OMLX provider.

        Args:
            model: OMLX model name. None → read GEN_MODEL from config (C12).
            max_tokens_default: Default max_tokens for generate() calls.
        """
        from pipeline.pipeline_paths import GEN_MODEL

        self.model_name: str = model or GEN_MODEL
        self.max_tokens_default: int = max_tokens_default

    def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int | None = None,
        temperature: float = 0.0,
        stop: list[str] | None = None,
    ) -> OMLXGenerationResult:
        """Generate text via OMLX HTTP (temp=0.0 enforced by omlx_call, R7).

        Args:
            prompt: User prompt.
            system: Optional system message.
            max_tokens: Max tokens (default: self.max_tokens_default).
            temperature: Sampling temperature (ignored — omlx_call enforces 0.0, R7).
            stop: Stop sequences (OMLX HTTP path does not currently forward stop;
                  accepted for protocol compatibility).

        Returns:
            OMLXGenerationResult with text, tokens_used (approximation), model, latency_ms.
        """
        import time

        max_tokens = max_tokens if max_tokens is not None else self.max_tokens_default
        t0 = time.time()
        text = call_omlx(
            prompt=prompt,
            model=self.model_name,
            system=system or None,
            max_tokens=max_tokens,
        )
        elapsed = (time.time() - t0) * 1000.0

        # tokens_used is an approximation (no token metadata exposed by OMLX HTTP path).
        # Use ~4 chars/token heuristic — good enough for observability, not billing.
        tokens_used = max(1, len(text) // 4)
        return OMLXGenerationResult(
            text=text,
            tokens_used=tokens_used,
            model=self.model_name,
            latency_ms=elapsed,
        )

    def generate_json(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> OMLXGenerationResult:
        """Generate JSON via OMLX with json_repair fallback (D2041)."""
        import time

        max_tokens = max_tokens if max_tokens is not None else self.max_tokens_default
        t0 = time.time()
        data = call_omlx_json(
            prompt=prompt,
            model=self.model_name,
            system=system or None,
            max_tokens=max_tokens,
        )
        elapsed = (time.time() - t0) * 1000.0

        import json as _json
        text = _json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)
        tokens_used = max(1, len(text) // 4)
        return OMLXGenerationResult(
            text=text,
            tokens_used=tokens_used,
            model=self.model_name,
            latency_ms=elapsed,
        )

    def health_check(self) -> bool:
        """Check OMLX server availability (delegates to omlx_call)."""
        return check_omlx_health()

    @property
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        return f"omlx:{self.model_name}"
