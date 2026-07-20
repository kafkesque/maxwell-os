#!/usr/bin/env python3
"""
model_lazyload.py — OMLX Lazy-Load Protocol (D34-LAZY)
========================================================
Manages OMLX model lifecycle: load on demand, auto-unload when idle.

Usage:
  # Pre-warm a model (loads and keeps warm for N seconds)
  python3 tools/model_lazyload.py --load Qwen3.6-35B-A3B-4bit --warm 120

  # Unload specific model immediately
  python3 tools/model_lazyload.py --unload gemma-4-26B-A4B-it-OptiQ-4bit

  # Unload ALL non-pinned models (reset to baseline)
  python3 tools/model_lazyload.py --reset

  # Daemon mode: auto-unload idle models after N seconds
  python3 tools/model_lazyload.py --daemon --idle-timeout 300

Architecture:
  - Pinned models (Phi-4-mini, gemma-4-E2B): always hot (~8GB)
  - Big models (Qwen3.6, gemma-4-26B): loaded on first request, unloaded after idle timeout
  - Unload by calling OMLX /v1/models/{model}/unload endpoint
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from datetime import datetime

# ── Import from centralized config ────────────────────────────────────
try:
    from tools.pipeline_paths import OMLX_URL
except ImportError:
    OMLX_URL = "http://localhost:11435"

OMLX_MODELS_URL = f"{OMLX_URL}/v1/models"

# ── Pinned models (never auto-unload) ─────────────────────────────────
PINNED_MODELS = {"Phi-4-mini-instruct-8bit", "gemma-4-E2B-it-MLX-4bit"}

# ── Model memory estimates (GB, from OMLX observations) ──────────────
MODEL_SIZES = {
    "Phi-4-mini-instruct-8bit": 3.80,
    "gemma-4-E2B-it-MLX-4bit": 4.04,
    "gemma-4-E4B-it-MLX-4bit": 6.36,
    "Qwopus-GLM-18B": 8.73,
    "Ornith-1.0-9B-4bit": 4.69,
    "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit": 16.00,
    "gemma-4-26B-A4B-it-OptiQ-4bit": 18.36,
    "Qwen3.6-35B-A3B-4bit": 19.95,
    "gemma-4-31B-it-OptiQ-4bit": 22.43,
    "gemma-4-12b-coder-fable5-composer2.5-4bit": 6.30,
    "gemma-4-12b-coder-fable5-composer2.5-8bit": 12.00,
    "Qwen2.5-Coder-7B-Instruct-4bit": 4.00,
}

# ── Model last-used timestamps (in-memory, resets on restart) ────────
_last_used: dict[str, float] = {}


def _api_get(url: str) -> dict:
    """GET OMLX API, return JSON."""
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _api_post(url: str, data: dict = None) -> dict:
    """POST to OMLX API."""
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=body,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_loaded_models() -> dict[str, float]:
    """Return dict of loaded model names → estimated memory (GB)."""
    try:
        data = _api_get(OMLX_MODELS_URL)
        return {m["id"]: MODEL_SIZES.get(m["id"], 0) for m in data.get("data", [])}
    except Exception:
        return {}


def get_memory_usage() -> float:
    """Return estimated total memory used by loaded models."""
    return sum(get_loaded_models().values())


def unload_model(model: str) -> bool:
    """Unload a single model from OMLX. Returns True on success."""
    try:
        url = f"{OMLX_URL}/v1/models/{model}/unload"
        _api_post(url)
        print(f"  🔻 Unloaded: {model} ({MODEL_SIZES.get(model, '?')}GB freed)")
        if model in _last_used:
            del _last_used[model]
        return True
    except urllib.error.HTTPError as e:
        if e.code == 400:
            print(f"  ⚠️  {model} already unloaded")
        elif e.code == 507:
            print(f"  ⚠️  {model}: cannot unload (memory pressure)")
        else:
            print(f"  ❌ {model}: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  ❌ {model}: {e}")
        return False


def load_model(model: str, warm_seconds: int = 0) -> bool:
    """Pre-load a model by sending a minimal inference request."""
    try:
        url = f"{OMLX_URL}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "OK"}],
            "max_tokens": 1,
            "temperature": 0.0,
        }
        _api_post(url, payload)
        _last_used[model] = time.time()
        print(f"  🔺 Loaded: {model} ({MODEL_SIZES.get(model, '?')}GB)")
        return True
    except Exception as e:
        print(f"  ❌ Could not load {model}: {e}")
        return False


def reset_to_baseline():
    """Unload all non-pinned models."""
    loaded = get_loaded_models()
    for model in loaded:
        if model not in PINNED_MODELS:
            unload_model(model)
    print(f"\n✅ Reset complete. Baseline: {sum(MODEL_SIZES.get(m, 0) for m in loaded if m in PINNED_MODELS):.1f}GB")


def mark_used(model: str):
    """Call this after a model serves a request to update its last-used timestamp."""
    _last_used[model] = time.time()


def unload_idle(idle_timeout: int = 300):
    """Unload any non-pinned model idle longer than idle_timeout seconds."""
    now = time.time()
    loaded = get_loaded_models()
    for model in loaded:
        if model in PINNED_MODELS:
            continue
        last = _last_used.get(model, 0)
        if now - last > idle_timeout:
            print(f"  ⏰ {model}: idle for {now - last:.0f}s → unloading")
            unload_model(model)


def daemon(idle_timeout: int = 300, check_interval: int = 30):
    """Run as daemon: periodically unload idle models."""
    print(f"🔁 Lazy-load daemon started (idle_timeout={idle_timeout}s, check={check_interval}s)")
    print(f"   Pinned: {', '.join(sorted(PINNED_MODELS))}")
    try:
        while True:
            unload_idle(idle_timeout)
            time.sleep(check_interval)
    except KeyboardInterrupt:
        print("\n👋 Daemon stopped")


# ── CLI ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OMLX Lazy-Load Protocol")
    parser.add_argument("--load", help="Pre-load a model")
    parser.add_argument("--unload", help="Unload a model")
    parser.add_argument("--reset", action="store_true", help="Unload all non-pinned models")
    parser.add_argument("--status", action="store_true", help="Show current model state")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--idle-timeout", type=int, default=300,
                        help="Idle seconds before auto-unload (default: 300)")
    parser.add_argument("--check-interval", type=int, default=30,
                        help="Daemon check interval (default: 30s)")
    parser.add_argument("--warm", type=int, default=0, help="Warm seconds after load")

    args = parser.parse_args()

    if args.status:
        loaded = get_loaded_models()
        total = sum(loaded.values())
        print(f"🔥 Loaded models ({total:.1f}GB):")
        for name, size in sorted(loaded.items(), key=lambda x: x[1], reverse=True):
            pinned = "📌" if name in PINNED_MODELS else "  "
            last = _last_used.get(name, 0)
            idle = f" (idle {time.time()-last:.0f}s)" if name not in PINNED_MODELS and last else ""
            print(f"  {pinned} {name}: {size:.1f}GB{idle}")
        if not loaded:
            print("  (no models loaded)")
        sys.exit(0)

    if args.daemon:
        daemon(args.idle_timeout, args.check_interval)
        sys.exit(0)

    if args.reset:
        reset_to_baseline()
        sys.exit(0)

    if args.load:
        load_model(args.load, args.warm)
        sys.exit(0)

    if args.unload:
        unload_model(args.unload)
        sys.exit(0)

    parser.print_help()
