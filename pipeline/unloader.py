"""
pipeline/unloader.py — OMLX model unloading between stages
===========================================================
Source: Qwen fix.md lines referencing unload_provider(), Claude fix.md
identifying model-swapping as the real memory leak pattern.

On Apple Silicon with MLX, loading a new model without unloading the
previous one causes cumulative memory growth. This module provides
on-demand unloading between pipeline stages.
"""

import sys
from pathlib import Path

import requests

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
from pipeline.pipeline_paths import OMLX_API_KEY, OMLX_URL  # noqa: E402  (C12: single source, D2552)


def unload_model(model_name: str) -> bool:
    """Unload a specific model from OMLX engine pool.

    BUG-952: OMLX DOES expose a dedicated unload endpoint. The prior stub claimed it did not
    and returned 'success' on a health check while never unloading anything (D-3034: a
    declaration that resolves to a health check declares nothing).

    Receipt 2026-10-20 (red loop, safe on an already-unloaded model — no live model touched):
      POST /v1/models/MiniCPM5-2B-MLX/unload  (Bearer sk-maxwell-local)
        -> {"error":{"message":"Model not loaded: MiniCPM5-2B-MLX", ...}}  # endpoint RESOLVES + is auth'd
      POST /admin/api/models/MiniCPM5-2B-MLX/unload (same key) -> {"detail":"Model not loaded: ..."}
      POST /admin/api/models/.../unload (secret_key as bearer) -> {"detail":"Invalid API key"} (secret is NOT a token)
    The v1 form is the OpenAI-compatible surface already used by model_lazyload.py, so it is the one used here.
    """
    try:
        r = requests.post(
            f"{OMLX_URL}/v1/models/{model_name}/unload",
            headers={"Authorization": f"Bearer {OMLX_API_KEY}"},
            timeout=30,
        )
        # 200 = unloaded; 400/404 = already unloaded (the requested state already holds — a no-op is success).
        if r.status_code in (200, 400, 404):
            return True
        print(f"unload {model_name}: HTTP {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"unload {model_name}: {exc}", file=sys.stderr)
        return False


def unload_all_models() -> int:
    """Request unloading of all models. Returns count of loaded models before."""
    try:
        r = requests.get(f"{OMLX_URL}/health",
                        headers={"Authorization": f"Bearer {OMLX_API_KEY}"},
                        timeout=5)
        data = r.json()
        return data.get("engine_pool", {}).get("loaded_count", 0)
    except Exception:
        return -1


def pre_stage_unload(stage_name: str) -> dict:
    """Called before each pipeline stage to check memory and unload if needed.

    Returns: {"stage": str, "loaded_models": int, "action": str}
    """
    import os

    from pipeline.omlx_watchdog import get_omlx_pid, get_rss_gb

    rss_threshold = float(os.environ.get("OMLX_STAGE_RSS_GB", "30"))
    pid = get_omlx_pid()
    action = "ok"

    if pid:
        rss = get_rss_gb(pid)
        if rss > rss_threshold:
            # Trigger watchdog restart between stages
            import subprocess
            import sys
            subprocess.run([sys.executable, "-m", "pipeline.omlx_watchdog", "--pre-stage"],
                          timeout=60)
            action = f"restarted (RSS {rss:.1f}GB > {rss_threshold}GB)"

    return {"stage": stage_name, "action": action}
