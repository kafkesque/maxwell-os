"""
parallel.py — Book-level subprocess parallelism for pipeline stages.
====================================================================
Authority: D2120 | CONSTITUTION.md C1/C3 (local compute only)

Provides practical parallelism as a DELEGATE-001 workaround.
Each book/stage runs in an isolated subprocess — OMLX handles
concurrent requests natively. No delegate framework dependency.

Stages that benefit from parallelism:
  Stage 0:    Convert EPUB→MD (I/O bound)     → per book
  Stage 0.5:  Extract metadata (LLM bound)     → per book
  Stage 1:    Chunk MD→segments (CPU bound)    → per book
  Stage 1.3:  Prefilter segments (CPU bound)   → per batch

Stages that CANNOT be parallelized:
  Stage 1.5:  FAISS clustering (global index)
  Stage 2:    Extraction (shared OMLX, batched internally)
  Stage 4:    Merge/classify (global dedup)
  Stage 5:    Verify (global)
  Stage 6:    Commit (global)

Usage:
    from pipeline.parallel import parallel_map
    results = parallel_map(convert_book, book_list, max_workers=4)
"""

from __future__ import annotations

import multiprocessing
import os
import time
from collections.abc import Callable
from multiprocessing import Pool
from typing import Any, TypeVar

T = TypeVar("T")


class ParallelMapError(RuntimeError):
    """Raised by parallel_map() when items fail and on_error='raise' (C16/BUG-177).

    A worker timeout or exception must never be indistinguishable from a
    legitimately-processed item (the legacy None-in-results behavior). Callers
    that explicitly want best-effort collection can pass on_error='collect'.
    """


def _worker_init() -> None:
    """Initialize worker process — suppress OMLX env issues."""
    # Workers shouldn't inherit thinking mode flags
    for var in ("GOOSE_THINKING_EFFORT", "GOOSE_PROVIDER"):
        os.environ.pop(var, None)


def parallel_map(  # noqa: UP047
    func: Callable[..., T],
    items: list[Any],
    max_workers: int = 4,
    *,
    desc: str = "",
    timeout_per_item: float = 300.0,
    on_error: str = "raise",
) -> list[T]:
    """Execute func(item) in parallel across items using subprocess pool.

    Args:
        func: Function taking one argument (item) and returning T.
        items: List of items to process.
        max_workers: Number of parallel workers (default 4).
        desc: Description for progress output.
        timeout_per_item: Max seconds per item before timeout error.
        on_error: "raise" (default, C16/BUG-177) — collect failures and raise
            ParallelMapError so a dropped item is never silent; "collect" —
            legacy best-effort behavior (None in results + printed warnings).

    Returns:
        List of results in the same order as items.

    Raises:
        ParallelMapError: if any item timed out or errored and on_error='raise'.
    """
    if not items:
        return []

    if max_workers < 2 or len(items) < 2:
        # Sequential — no need for pool overhead
        return [func(item) for item in items]

    desc_str = f" [{desc}]" if desc else ""
    print(f"⚡ Parallel: {len(items)} items, {max_workers} workers{desc_str}")

    start = time.time()
    results: list[T | None] = []
    errors: list[str] = []

    with Pool(
        processes=min(max_workers, len(items)),
        initializer=_worker_init,
    ) as pool:
        # Submit all tasks asynchronously
        async_results = [
            pool.apply_async(func, (item,)) for item in items
        ]

        # Collect with timeout
        for i, ar in enumerate(async_results):
            try:
                result = ar.get(timeout=timeout_per_item)
                results.append(result)
            except multiprocessing.TimeoutError:
                print(f"   ⚠️  Item {i} timed out ({timeout_per_item}s)")
                results.append(None)
                errors.append(f"timeout: item {i}")
            except Exception as e:
                print(f"   ⚠️  Item {i} failed: {e}")
                results.append(None)
                errors.append(f"error: item {i}: {e}")

    elapsed = time.time() - start
    succeeded = sum(1 for r in results if r is not None)
    print(
        f"   ✅ {succeeded}/{len(items)} items in {elapsed:.1f}s "
        f"({elapsed / len(items):.1f}s/item avg)"
    )
    if errors:
        print(f"   ⚠️  {len(errors)} failures: " + "; ".join(errors[:3]))
        # C16/BUG-177: a dropped item must never be silent — raise unless the
        # caller explicitly opted into best-effort collection.
        if on_error == "raise":
            raise ParallelMapError(
                f"{len(errors)}/{len(items)} items failed: " + "; ".join(errors[:5])
            )

    return results


def detect_cpu_cores() -> int:
    """Auto-detect available CPU cores for parallelism (C24: hardware-adaptive).

    Returns:
        Recommended worker count (never more than physical cores - 1,
        minimum 1, maximum 8).
    """
    cpu_count = os.cpu_count() or 4
    # Reserve 1 core for OMLX server + system
    workers = max(1, min(cpu_count - 1, 8))
    return workers


def optimal_workers(
    task_type: str = "io",
    total_items: int = 1,
) -> int:
    """Determine optimal worker count based on task type and item count.

    Args:
        task_type: "io" (Stage 0), "cpu" (Stage 1), or "llm" (Stage 0.5).
        total_items: Total number of items to process.

    Returns:
        Recommended worker count.
    """
    cores = detect_cpu_cores()
    if total_items < 2:
        return 1
    if task_type == "io":
        return min(cores * 2, total_items, 8)  # I/O bound can oversubscribe
    if task_type == "cpu":
        return min(cores, total_items)  # CPU bound = 1 per core
    if task_type == "llm":
        return min(4, total_items)  # OMLX server handles concurrency
    return min(cores, total_items)
