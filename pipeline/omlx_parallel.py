#!/usr/bin/env python3
"""
omlx_parallel.py — Parallel OMLX caller for continuous batching (D2225)
======================================================================
Authority: D2225 — Forks OMLX sequential calling pattern into parallel
requests to exploit OMLX server's continuous batching capability.

OMLX server (mlx-lm) supports continuous batching: multiple concurrent
requests are interleaved at the prefill/decode level, sharing model
weights in GPU memory. The pipeline's sequential omlx_call.py can't
exploit this. This module provides a drop-in parallel replacement.

Hardware: Tested on M1 Max 64GB with Qwen3-Coder-30B-A3B-4bit.
Max concurrent: 3-4 (model ~15-18GB loaded, 3 instances ~45-54GB).
For 8B-equivalent models (Phi-4-mini, Gemma-4-E4B): 6-8 concurrent.

Usage:
    from pipeline.omlx_parallel import call_omlx_batch

    prompts = [prompt1, prompt2, prompt3, ...]
    results = call_omlx_batch(prompts, model="Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
"""

import concurrent.futures

from pipeline.omlx_call import call_omlx


def call_omlx_batch(
    prompts: list[str],
    model: str,
    system: str = None,
    max_tokens: int = 1024,
    timeout: int = 120,
    max_workers: int = 3,
) -> list[str]:
    """Call OMLX with multiple prompts in parallel (D2225).

    Uses ThreadPoolExecutor to make concurrent HTTP requests to the
    OMLX server, exploiting its continuous batching capability. Each
    worker thread calls the standard call_omlx() function.

    Args:
        prompts: List of prompt strings to send.
        model: Model name (must be loaded on OMLX server).
        system: Optional system prompt (same for all calls).
        max_tokens: Max output tokens per call.
        timeout: Per-call timeout in seconds.
        max_workers: Max concurrent requests (default 3 for 30B model).

    Returns:
        List of response strings in the same order as prompts.
        Failed calls return empty string.
    """
    results: list[str] = [""] * len(prompts)

    def _call_one(idx: int, prompt: str) -> tuple[int, str]:
        """Single OMLX call with error handling."""
        try:
            result = call_omlx(
                prompt=prompt,
                model=model,
                system=system,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return idx, result
        except Exception as e:
            return idx, f"ERROR[{idx}]: {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_call_one, i, prompt): i
            for i, prompt in enumerate(prompts)
        }
        for future in concurrent.futures.as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    return results


def call_omlx_json_batch(
    prompts: list[str],
    model: str,
    system: str = None,
    max_tokens: int = 1024,
    timeout: int = 120,
    max_workers: int = 3,
    response_format: dict = None,
) -> list[dict]:
    """Call OMLX with multiple prompts, returning parsed JSON (D2225).

    Same as call_omlx_batch but each response is parsed as JSON.
    Failed parses return {"_error": "parse_failed", "_raw": "..."}.
    """
    from pipeline.omlx_call import call_omlx_json

    results: list[dict] = [{}] * len(prompts)

    def _call_one_json(idx: int, prompt: str) -> tuple[int, dict]:
        try:
            result = call_omlx_json(
                prompt=prompt,
                model=model,
                system=system,
                max_tokens=max_tokens,
                timeout=timeout,
                response_format=response_format,
            )
            return idx, result
        except Exception as e:
            return idx, {"_error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_call_one_json, i, prompt): i
            for i, prompt in enumerate(prompts)
        }
        for future in concurrent.futures.as_completed(futures):
            idx, result = future.result()
            results[idx] = result

    return results


def estimate_optimal_workers(
    model_size_gb: float = 15.0,
    total_ram_gb: float = 64.0,
    context_tokens: int = 4096,
) -> int:
    """Estimate optimal max_workers based on available RAM.

    D2225: Conservative estimate accounting for:
    - Model weights (already loaded by OMLX server, shared across requests)
    - KV cache per concurrent request (~1.5GB at 4K context for 30B model)
    - OS/GPU buffer (~8GB)

    Args:
        model_size_gb: Loaded model size in GB.
        total_ram_gb: Total system RAM.
        context_tokens: Context window size.

    Returns:
        Recommended max_workers.
    """
    kv_cache_per_worker = (context_tokens / 4096) * 1.5  # GB per worker
    os_buffer = 8.0
    available = total_ram_gb - model_size_gb - os_buffer
    max_workers = int(available / kv_cache_per_worker)
    return max(1, min(max_workers, 4))  # Cap at 4 for stability


# ── Benchmark ────────────────────────────────────────────────────────────────

def benchmark_parallel(
    n_prompts: int = 10,
    model: str = "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit",
    max_workers: int = 3,
) -> dict:
    """Benchmark sequential vs. parallel OMLX calling (D2225).

    Sends n_prompts identical requests and measures wall-clock time
    for sequential and parallel execution.
    """
    import time

    prompt = "Extract: name, definition, mechanism, boundary, consequence from: 'The system processes input through layered transformations.'"

    # Sequential
    t0 = time.time()
    for _ in range(n_prompts):
        call_omlx(prompt=prompt, model=model, max_tokens=128, timeout=60)
    t_seq = time.time() - t0

    # Parallel
    prompts = [prompt] * n_prompts
    t1 = time.time()
    call_omlx_batch(prompts, model=model, max_tokens=128, timeout=120, max_workers=max_workers)
    t_par = time.time() - t1

    return {
        "n_prompts": n_prompts,
        "max_workers": max_workers,
        "sequential_s": round(t_seq, 1),
        "parallel_s": round(t_par, 1),
        "speedup": round(t_seq / t_par, 1),
        "per_prompt_seq_s": round(t_seq / n_prompts, 2),
        "per_prompt_par_s": round(t_par / n_prompts, 2),
    }
