"""
hybrid_gate.py — DSPy-inspired gate for S2 extraction (D2276).
===============================================================

Authority: D2251, D2276, BUG-085

A lightweight pre-extraction gate that decides whether a cluster segment batch
contains an extractable convergent principle. This is the "DSPy gate" concept
from the T-007b hybrid benchmark (0.736 vs 0.591 traditional-only), adapted
for production use without requiring a trained DSPy module.

Architecture:
  1. Build a compact gate prompt from cluster segments
  2. Call OMLX with a short FB/NULL decision prompt (cheap: ~50 tokens output)
  3. If NULL → skip extraction (saves ~28s per cluster)
  4. If FB → proceed with full convergent extraction

Gate prompt is config-driven (C12) via pipeline_config.yaml → s2.gate_prompt.
Falls back to a built-in prompt that asks: "Does this text cluster contain
a discoverable convergent principle with a clear mechanism?"

Usage (from stage2_extract.py):
    gate = HybridGate(provider="omlx")
    route = gate.decide(cluster_segments)
    if route == "NULL":
        skip  # saves ~28s extraction time
    else:
        extract  # traditional few-shot extraction
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# ── Config-driven gate prompt (C12) ──────────────────────────────────────

def _load_gate_config() -> dict[str, Any]:
    """Load gate configuration from pipeline_config.yaml."""
    try:
        import yaml as _yaml
        _cfg_path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
        with open(_cfg_path) as _f:
            _cfg = _yaml.safe_load(_f) or {}
        return _cfg.get("s2", {}).get("gate", {})
    except Exception:
        return {}


GATE_CONFIG: dict[str, Any] = _load_gate_config()

# C12: All gate parameters from config, with hardcoded fallbacks for bootstrap only
GATE_ENABLED: bool = GATE_CONFIG.get("enabled", False)
GATE_MAX_TOKENS: int = GATE_CONFIG.get("max_tokens", 64)
GATE_TEMPERATURE: float = GATE_CONFIG.get("temperature", 0.0)
GATE_MODEL: str = GATE_CONFIG.get(
    "model",
    "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit",
)
GATE_SYSTEM_PROMPT: str = GATE_CONFIG.get(
    "system_prompt",
    "You are a principle discovery gate. Answer ONLY with 'FB' or 'NULL'. No explanation.",
)
GATE_USER_PROMPT_TEMPLATE: str = GATE_CONFIG.get(
    "user_prompt_template",
    (
        "Examine these text segments from {n_sources} different books.\n\n"
        "{segments}\n\n"
        "Does this cluster contain a discoverable convergent principle — "
        "a named, reusable mechanism with a clear 'how it works' and 'when it fails'?\n"
        "Answer ONLY: FB (yes, extractable principle) or NULL (no extractable principle)."
    ),
)


class HybridGate:
    """D2276: Pre-extraction gate for S2 clusters.

    Determines whether a cluster is likely to contain an extractable
    convergent principle. Designed as a cheap pre-filter: ~50 tokens out
    vs ~28s for full traditional extraction.

    The gate is biased toward recall (better to waste extraction time
    than miss a real principle). From D2250 benchmark: DSPy gate is a
    perfect NEGATIVE filter (rejects 5/6 negatives) but weaker at positives.

    Usage:
        gate = HybridGate(provider="omlx")
        route = gate.decide(cluster_segment_text)
        if route == "NULL":
            skip_cluster()
    """

    def __init__(self, provider: str = "omlx") -> None:
        """Initialize the hybrid gate.

        Args:
            provider: "omlx" or "mlx" for the LLM backend.
        """
        self._provider = provider
        self._model = GATE_MODEL
        self._stats: dict[str, int] = {"FB": 0, "NULL": 0, "ERROR": 0}

    def decide(self, cluster_segments: str, source_books: list[str] | None = None) -> str:
        """Decide whether a cluster contains an extractable principle.

        Args:
            cluster_segments: Formatted text of all cluster segments.
            source_books: List of distinct source book identifiers (for n_sources).

        Returns:
            "FB" if the cluster likely contains a principle, "NULL" otherwise.
            "ERROR" if the gate call failed (treat as FB — fail-open for recall).
        """
        n_sources = len(source_books) if source_books else 1
        prompt = GATE_USER_PROMPT_TEMPLATE.format(
            n_sources=n_sources,
            segments=cluster_segments[:3000],  # Truncate for gate (cheap)
        )

        try:
            if self._provider == "omlx":
                route = self._call_omlx_gate(prompt)
            else:
                route = self._call_mlx_gate(prompt)

            route = route.strip().upper()
            if "FB" in route:
                self._stats["FB"] += 1
                return "FB"
            else:
                self._stats["NULL"] += 1
                return "NULL"

        except Exception:
            self._stats["ERROR"] += 1
            return "FB"  # Fail-open: gate error → extract (prefer false positive to data loss)

    def _call_omlx_gate(self, prompt: str) -> str:
        """Call OMLX for the gate decision."""
        from pipeline.omlx_call import call_omlx

        result = call_omlx(
            prompt=prompt,
            model=self._model,
            system=GATE_SYSTEM_PROMPT,
            max_tokens=GATE_MAX_TOKENS,
            temperature=GATE_TEMPERATURE,
        )
        # call_omlx returns the text directly for non-JSON calls
        if isinstance(result, dict):
            return result.get("content", str(result))
        return str(result)

    def _call_mlx_gate(self, prompt: str) -> str:
        """Call MLX for the gate decision."""
        # MLX path — fallback for local-only execution
        import subprocess as _sp
        import sys as _sys

        # Simple MLX call via subprocess
        result = _sp.run(
            [_sys.executable, "-c", f"""
import mlx_lm
response = mlx_lm.generate(
    "{GATE_MODEL}",
    prompt="{prompt[:500]}",
    max_tokens={GATE_MAX_TOKENS},
    temp={GATE_TEMPERATURE},
)
print(response)
"""],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip() or "FB"

    @property
    def stats(self) -> dict[str, int]:
        """Return gate statistics: FB/NULL/ERROR counts."""
        return dict(self._stats)


# ── Convenience functions ────────────────────────────────────────────────

def format_segments_for_gate(segments: list[dict]) -> str:
    """Format cluster segments into a compact text block for the gate.

    Args:
        segments: List of segment dicts with 'text' and optionally 'source_book'.

    Returns:
        Formatted text block (max ~3000 chars for gate efficiency).
    """
    lines: list[str] = []
    for i, seg in enumerate(segments[:8], 1):  # Max 8 segments for gate
        source = seg.get("source_book", f"Source {i}")
        text = str(seg.get("text", ""))[:350]
        lines.append(f"[{source}]\n{text}\n")
    return "\n".join(lines)[:3000]
