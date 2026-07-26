#!/usr/bin/env python3
"""pipeline/providers/test_mlx_integration.py — Integration test with real MLX model.

Downloads a small model (~350MB), loads it via MLXInferenceProvider,
runs generation, streaming, and benchmarks.

Usage:
    python3 pipeline/providers/test_mlx_integration.py
    python3 pipeline/providers/test_mlx_integration.py --model mlx-community/Qwen2.5-0.5B-Instruct-4bit
    python3 pipeline/providers/test_mlx_integration.py --model lmstudio-community/gemma-4-E4B-it-MLX-4bit
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default: tiny model that downloads fast (~350MB) and loads in <5s
DEFAULT_MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"


def download_model(model_name: str) -> bool:
    """Download model if not cached. Returns True if ready."""
    from huggingface_hub import snapshot_download
    import os

    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    model_dir = model_name.replace("/", "--")
    cache_path = os.path.join(cache_dir, f"models--{model_dir}")

    if os.path.exists(cache_path) and any(
        f.endswith('.safetensors') for f in
        os.listdir(os.path.join(cache_path, 'snapshots',
            sorted(os.listdir(os.path.join(cache_path, 'snapshots')))[-1]))
        if os.path.isdir(os.path.join(cache_path, 'snapshots'))
    ):
        print(f"  Model cached: {model_name}")
        return True

    print(f"  Downloading {model_name}...")
    try:
        snapshot_download(model_name, resume_download=True)
        print(f"  Downloaded: {model_name}")
        return True
    except Exception as e:
        print(f"  Download failed: {e}")
        return False


def test_basic_generation(provider) -> dict:
    """Test basic text generation."""
    t0 = time.time()
    result = provider.generate("Say hello in exactly three words.")
    elapsed = (time.time() - t0) * 1000

    return {
        "text": result.text[:100],
        "tokens": result.tokens_used,
        "latency_ms": result.latency_ms,
        "wall_ms": round(elapsed, 1),
        "model": result.model,
        "provider": result.provider,
    }


def test_streaming(provider) -> dict:
    """Test streaming generation."""
    t0 = time.time()
    chunks = list(provider.generate_stream("Count from 1 to 5."))
    elapsed = (time.time() - t0) * 1000

    full = "".join(chunks)
    return {
        "text": full[:100],
        "chunks": len(chunks),
        "wall_ms": round(elapsed, 1),
    }


def test_json_generation(provider) -> dict:
    """Test JSON generation."""
    t0 = time.time()
    result = provider.generate_json(
        'Return a JSON object with keys "name" and "score". '
        'Example: {"name": "test", "score": 100}',
        max_tokens=100,
    )
    elapsed = (time.time() - t0) * 1000

    valid_json = False
    try:
        parsed = json.loads(result.text)
        valid_json = isinstance(parsed, dict)
    except json.JSONDecodeError:
        parsed = None

    return {
        "text": result.text[:100],
        "valid_json": valid_json,
        "parsed": str(parsed)[:80] if parsed else None,
        "latency_ms": result.latency_ms,
        "wall_ms": round(elapsed, 1),
        "provider": result.provider,
    }


def test_cache_speedup(provider) -> dict:
    """Test system prompt caching speedup."""
    system = "You are a helpful assistant. Always be concise."

    # Warm-up (compute cache)
    t0 = time.time()
    provider.generate("Hello", system=system)
    warm_ms = (time.time() - t0) * 1000

    # Cached call
    t0 = time.time()
    result = provider.generate("Hi again", system=system)
    cached_ms = (time.time() - t0) * 1000

    # Different system (no cache)
    t0 = time.time()
    provider.generate("Hello", system="You are a grumpy assistant.")
    cold_ms = (time.time() - t0) * 1000

    return {
        "warm_first_ms": round(warm_ms, 1),
        "cached_ms": round(cached_ms, 1),
        "cold_ms": round(cold_ms, 1),
        "cache_hit": result.cache_hit,
        "speedup": f"{warm_ms/cached_ms:.1f}x" if cached_ms > 0 else "N/A",
    }


def test_batch_generation(provider) -> dict:
    """Test batch generation."""
    prompts = [
        "Say hello",
        "Say goodbye",
        "Count to three",
    ]

    t0 = time.time()
    results = provider.batch_generate(prompts, max_tokens=20)
    elapsed = (time.time() - t0) * 1000

    return {
        "num_prompts": len(prompts),
        "results": [r.text[:40] for r in results],
        "total_ms": round(elapsed, 1),
        "per_prompt_ms": round(elapsed / len(prompts), 1),
        "tokens": [r.tokens_used for r in results],
    }


def test_delegate_compatibility(provider) -> dict:
    """Test that provider works in a delegate-compatible pattern."""
    # Simulate what a delegate task would do:
    # 1. Import the provider
    # 2. Create an instance
    # 3. Call generate with various parameters
    # 4. Return results

    from pipeline.providers.mlx_provider import MLXInferenceProvider

    # Test 1: Standard generate
    r1 = provider.generate("What is 2+2?", max_tokens=30)

    # Test 2: With system prompt
    r2 = provider.generate(
        "What color is the sky?",
        system="Answer in exactly two words.",
        max_tokens=20,
    )

    # Test 3: generate_json
    r3 = provider.generate_json(
        'Return: {"topic": "AI", "rating": 5}',
        max_tokens=50,
    )

    return {
        "gen_text": r1.text[:80],
        "gen_tokens": r1.tokens_used,
        "sys_text": r2.text[:80],
        "json_text": r3.text[:80],
        "all_successful": bool(r1.text and r2.text and r3.text),
    }


def main():
    parser = argparse.ArgumentParser(description="MLX Provider Integration Test")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Model to test (default: {DEFAULT_MODEL})")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip model download check")
    parser.add_argument("--delegate-only", action="store_true",
                        help="Only run delegate compatibility test")
    args = parser.parse_args()

    model_name = args.model

    print("=" * 70)
    print("MLX Provider — Integration Test (real model)")
    print(f"Model: {model_name}")
    print("=" * 70)

    # Download if needed
    if not args.skip_download:
        if not download_model(model_name):
            print("\n❌ Model download failed. Try --model with a cached model.")
            return 1

    # Load provider
    print(f"\n--- Loading {model_name} ---")
    from pipeline.providers.mlx_provider import MLXInferenceProvider

    t0 = time.time()
    try:
        provider = MLXInferenceProvider(model_name, max_tokens_default=100)
        # Force load
        provider._ensure_loaded()
        load_time = time.time() - t0
        print(f"  Loaded in {load_time:.1f}s")
        print(f"  Cache stats: {provider.cache_stats}")
    except Exception as e:
        print(f"  ❌ Load failed: {e}")
        traceback.print_exc()
        return 1

    tests = []

    if not args.delegate_only:
        tests = [
            ("Basic Generation", test_basic_generation),
            ("Streaming", test_streaming),
            ("JSON Generation", test_json_generation),
            ("Cache Speedup", test_cache_speedup),
            ("Batch Generation", test_batch_generation),
        ]

    tests.append(("Delegate Compatibility", test_delegate_compatibility))

    results = {}
    all_passed = True

    for name, fn in tests:
        print(f"\n--- {name} ---")
        try:
            result = fn(provider)
            results[name] = result
            print(f"  ✅ {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {e}")
            traceback.print_exc()
            results[name] = {"error": str(e)}
            all_passed = False

    # Summary
    print(f"\n{'='*70}")
    print("Summary")
    print(f"{'='*70}")

    for name, result in results.items():
        if "error" in result:
            print(f"  ❌ {name}: {result['error']}")
        else:
            print(f"  ✅ {name}")

    # Speed recommendations
    print(f"\n--- Speed Analysis ---")
    if "Basic Generation" in results and "error" not in results["Basic Generation"]:
        gen = results["Basic Generation"]
        tps = gen["tokens"] / (gen["latency_ms"] / 1000) if gen["latency_ms"] > 0 else 0
        print(f"  Generation: {gen['latency_ms']:.0f}ms, {tps:.1f} tok/s ({gen['tokens']} tokens)")

    if "Cache Speedup" in results and "error" not in results["Cache Speedup"]:
        cache = results["Cache Speedup"]
        print(f"  Cache speedup: {cache['speedup']} (cached: {cache['cached_ms']}ms vs warm: {cache['warm_first_ms']}ms)")

    if "Batch Generation" in results and "error" not in results["Batch Generation"]:
        batch = results["Batch Generation"]
        print(f"  Batch: {batch['per_prompt_ms']}ms/prompt ({batch['num_prompts']} prompts)")

    # Delegate readiness
    if "Delegate Compatibility" in results and "error" not in results["Delegate Compatibility"]:
        dc = results["Delegate Compatibility"]
        if dc.get("all_successful"):
            print(f"\n  ✅ Delegate-compatible: all generation patterns work")
        else:
            print(f"\n  ⚠️  Delegate compatibility: partial")

    print(f"\n  Note: For speculative decoding (1.5-2x faster), add --draft-model")
    print(f"  Example: get_mlx_provider('{model_name}', draft_model_name='mlx-community/Qwen2.5-0.5B-Instruct-4bit')")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
