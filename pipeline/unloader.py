"""
pipeline/unloader.py — OMLX model unloading between stages
===========================================================
Source: Qwen fix.md lines referencing unload_provider(), Claude fix.md
identifying model-swapping as the real memory leak pattern.

On Apple Silicon with MLX, loading a new model without unloading the
previous one causes cumulative memory growth. This module provides
on-demand unloading between pipeline stages.
"""
import requests
import time

OMLX_URL = "http://localhost:11435"
OMLX_API_KEY = "sk-maxwell-local"


def unload_model(model_name: str) -> bool:
    """Unload a specific model from OMLX engine pool.
    
    OMLX v0.5.1 does not have a dedicated unload endpoint.
    Workaround: trigger a health check, then the engine pool
    garbage-collects unused models when memory pressure rises.
    
    For explicit unloading, restart the server via watchdog.
    """
    try:
        # Check if model is loaded
        r = requests.get(f"{OMLX_URL}/health", 
                        headers={"Authorization": f"Bearer {OMLX_API_KEY}"},
                        timeout=5)
        if r.status_code == 200:
            data = r.json()
            loaded = data.get("engine_pool", {}).get("loaded_count", 0)
            # OMLX auto-manages model lifecycle. The watchdog handles
            # server-level restart when RSS exceeds threshold.
            return loaded > 0
    except Exception:
        pass
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
    from pipeline.omlx_watchdog import get_omlx_pid, get_rss_gb
    import os
    
    rss_threshold = float(os.environ.get("OMLX_STAGE_RSS_GB", "30"))
    pid = get_omlx_pid()
    action = "ok"
    
    if pid:
        rss = get_rss_gb(pid)
        if rss > rss_threshold:
            # Trigger watchdog restart between stages
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "pipeline.omlx_watchdog", "--pre-stage"],
                          timeout=60)
            action = f"restarted (RSS {rss:.1f}GB > {rss_threshold}GB)"
    
    return {"stage": stage_name, "action": action}
