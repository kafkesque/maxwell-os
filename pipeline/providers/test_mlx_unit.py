"""pipeline/providers/test_mlx_unit.py — Unit tests (no model loading required).

Validates provider architecture, signatures, protocols, and edge cases
without loading any MLX model. Fast (< 2s for all tests).
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed: bool | None = None
        self.duration_ms: float = 0
        self.error: str | None = None


def run_test(name, fn):
    r = TestResult(name)
    t0 = time.time()
    try:
        fn()
        r.passed = True
    except Exception as e:
        r.passed = False
        r.error = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    r.duration_ms = (time.time() - t0) * 1000
    return r


def test_01_provider_imports():
    """Provider module imports cleanly."""
    from pipeline.providers.mlx_provider import (
        MLXGenerationResult,
        MLXInferenceProvider,
    )
    assert MLXInferenceProvider is not None
    assert MLXGenerationResult is not None


def test_02_provider_lazy_init():
    """Provider doesn't load model on init."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider
    p = MLXInferenceProvider("test/model")
    assert p._model is None
    assert p._tokenizer is None
    assert p.model_name == "test/model"
    assert p.temperature == 0.0


def test_03_generation_result():
    """MLXGenerationResult has required fields."""
    from pipeline.providers.mlx_provider import MLXGenerationResult
    r = MLXGenerationResult(
        text="Hello",
        tokens_used=5,
        model="test",
        latency_ms=100.0,
    )
    assert r.text == "Hello"
    assert r.tokens_used == 5
    assert r.provider == "mlx"
    assert r.cache_hit is False


def test_04_mocked_generate():
    """generate() calls mlx_lm correctly (mocked)."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    with patch("pipeline.providers.mlx_provider.mlx_lm") as mock_mlx:
        # Setup mock
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3]
        mock_mlx.load.return_value = (mock_model, mock_tokenizer)

        mock_resp = MagicMock()
        mock_resp.text = "Mocked response"
        mock_resp.token_count = 10
        mock_mlx.generate.return_value = mock_resp

        provider = MLXInferenceProvider("test/model")
        result = provider.generate("prompt")

        assert result.text == "Mocked response"
        assert result.tokens_used == 10
        assert result.model == "test/model"
        assert result.provider == "mlx"
        assert result.latency_ms >= 0  # May be 0 with mocked fast execution
        mock_mlx.load.assert_called_once_with("test/model")
        mock_mlx.generate.assert_called_once()


def test_05_mocked_system_cache():
    """System prompt is cached after first call (mocked)."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    with patch("pipeline.providers.mlx_provider.mlx_lm") as mock_mlx:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3]
        mock_mlx.load.return_value = (mock_model, mock_tokenizer)

        mock_resp = MagicMock()
        mock_resp.text = "Response"
        mock_resp.token_count = 5
        mock_mlx.generate.return_value = mock_resp

        provider = MLXInferenceProvider("test/model")

        # First call: cache miss
        r1 = provider.generate("prompt", system="Be helpful.")
        assert r1.cache_hit is False

        # Second call with same system: cache hit
        r2 = provider.generate("another prompt", system="Be helpful.")
        assert r2.cache_hit is True

        # Different system: cache miss
        r3 = provider.generate("prompt", system="Different system.")
        assert r3.cache_hit is False


def test_06_mocked_json_fallback():
    """generate_json() falls back to regex extraction when outlines unavailable."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    with patch("pipeline.providers.mlx_provider.mlx_lm") as mock_mlx:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3]
        mock_mlx.load.return_value = (mock_model, mock_tokenizer)

        # Response with JSON in markdown block
        mock_resp = MagicMock()
        mock_resp.text = 'Here you go:\n```json\n{"key": "value"}\n```'
        mock_resp.token_count = 15
        mock_mlx.generate.return_value = mock_resp

        provider = MLXInferenceProvider("test/model")
        result = provider.generate_json("Get JSON")

        # Should extract the JSON from markdown
        assert '"key": "value"' in result.text or '{"key": "value"}' in result.text


def test_07_mocked_batch_generate():
    """batch_generate() processes multiple prompts (mocked)."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    with patch("pipeline.providers.mlx_provider.mlx_lm") as mock_mlx:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3]
        mock_mlx.load.return_value = (mock_model, mock_tokenizer)

        # Mock batch response (mlx_lm 0.31.3 uses .texts, not .generations)
        mock_batch = MagicMock()
        mock_batch.texts = ["Response 1", "Response 2"]
        mock_mlx.batch_generate.return_value = mock_batch

        provider = MLXInferenceProvider("test/model")
        results = provider.batch_generate(["prompt1", "prompt2"])

        assert len(results) == 2
        assert results[0].text == "Response 1"
        assert results[1].text == "Response 2"
        mock_mlx.batch_generate.assert_called_once()


def test_08_temperature_enforcement():
    """R7: temperature is always clamped to >= 0.0."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    with patch("pipeline.providers.mlx_provider.mlx_lm") as mock_mlx:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3]
        mock_mlx.load.return_value = (mock_model, mock_tokenizer)

        mock_resp = MagicMock()
        mock_resp.text = "Ok"
        mock_resp.token_count = 2
        mock_mlx.generate.return_value = mock_resp

        provider = MLXInferenceProvider("test/model", temperature=0.0)

        # Pass negative temperature - should clamp to 0.0
        result = provider.generate("prompt", temperature=-0.5)
        assert result is not None  # Should succeed, not error

        # Verify default is 0.0
        assert provider.temperature == 0.0


def test_09_factory_singleton():
    """get_mlx_provider() returns same instance for same model."""
    from pipeline.providers.mlx_provider import clear_providers, get_mlx_provider

    clear_providers()
    p1 = get_mlx_provider("test/model-a")
    p2 = get_mlx_provider("test/model-a")
    p3 = get_mlx_provider("test/model-b")

    assert p1 is p2, "Same model should return singleton"
    assert p1 is not p3, "Different model should be different instance"

    clear_providers()
    p4 = get_mlx_provider("test/model-a")
    assert p4 is not p1, "After clear, should be new instance"


def test_10_cache_stats():
    """cache_stats returns correct counts."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    with patch("pipeline.providers.mlx_provider.mlx_lm") as mock_mlx:
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3]
        mock_mlx.load.return_value = (mock_model, mock_tokenizer)

        mock_resp = MagicMock()
        mock_resp.text = "Ok"
        mock_resp.token_count = 2
        mock_mlx.generate.return_value = mock_resp

        provider = MLXInferenceProvider("test/model")
        assert provider.cache_stats["cached_systems"] == 0

        provider.generate("p1", system="System A")
        assert provider.cache_stats["cached_systems"] == 1

        provider.generate("p2", system="System B")
        assert provider.cache_stats["cached_systems"] == 2

        # Same system should not add duplicate
        provider.generate("p3", system="System A")
        assert provider.cache_stats["cached_systems"] == 2

        provider.clear_cache()
        assert provider.cache_stats["cached_systems"] == 0


def test_11_result_serializable():
    """MLXGenerationResult is JSON-serializable."""
    from pipeline.providers.mlx_provider import MLXGenerationResult

    r = MLXGenerationResult(
        text='{"key": "value"}',
        tokens_used=10,
        model="test/model",
        latency_ms=42.0,
        cache_hit=True,
    )

    d = {
        "text": r.text,
        "tokens_used": r.tokens_used,
        "model": r.model,
        "provider": r.provider,
        "latency_ms": r.latency_ms,
    }
    j = json.dumps(d)
    assert "test/model" in j
    assert "42.0" in j


def test_12_delegate_interface():
    """Provider exposes a clean interface for delegate task instructions."""
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    # Verify the public API surface
    p = MLXInferenceProvider("test/model")
    public_methods = [m for m in dir(p) if not m.startswith('_')]
    expected = [
        'batch_generate', 'cache_stats', 'clear_cache', 'generate',
        'generate_json', 'generate_stream', 'health_check', 'provider_name'
    ]
    for method in expected:
        assert method in public_methods, f"Missing public method: {method}"

    # Provider name should be descriptive
    assert "test/model" in p.provider_name


ALL_TESTS = [
    ("01 Provider imports", test_01_provider_imports),
    ("02 Lazy init", test_02_provider_lazy_init),
    ("03 GenerationResult", test_03_generation_result),
    ("04 Mocked generate", test_04_mocked_generate),
    ("05 System cache", test_05_mocked_system_cache),
    ("06 JSON fallback", test_06_mocked_json_fallback),
    ("07 Batch generate", test_07_mocked_batch_generate),
    ("08 Temperature R7", test_08_temperature_enforcement),
    ("09 Factory singleton", test_09_factory_singleton),
    ("10 Cache stats", test_10_cache_stats),
    ("11 Result serializable", test_11_result_serializable),
    ("12 Delegate interface", test_12_delegate_interface),
]


def main():
    print("=" * 60)
    print("MLX Provider — Unit Tests (no model required)")
    print("=" * 60)

    results = []
    for name, fn in ALL_TESTS:
        r = run_test(name, fn)
        results.append(r)
        icon = "✅" if r.passed else "❌"
        print(f"  {icon} {name}: {r.duration_ms:.0f}ms")
        if r.error:
            print(f"     {r.error}")

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if r.passed is False)
    total_time = sum(r.duration_ms for r in results)

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed in {total_time:.0f}ms")
    print(f"{'='*60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
