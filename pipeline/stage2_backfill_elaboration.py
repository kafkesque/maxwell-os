#!/usr/bin/env python3
"""Post-hoc backfill of empty `elaboration` on single-source principles.

BUG-155 (elaboration under-production): the single-source S2 prompt allowed
"leave a field empty when the passage does not provide it", which Qwen3-Coder
applied to `elaboration` on ~84% of single-source principles. The prompt is now
fixed (elaboration REQUIRED, derived from mechanism/boundary/consequence), but
already-extracted records still carry empty elaboration.

This script regenerates `elaboration` for those records, grounded ONLY in their
existing extracted fields (name/definition/mechanism/boundary/consequence) — no
re-extraction from source passages, no new factual claims. Convergent principles
are untouched (they already carry elaboration).

Resumable + idempotent + crash-safe (tempfile → fsync → os.replace). Re-running
skips records that already have non-empty elaboration.

Usage:
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_backfill_elaboration.py
    python3 -u pipeline/stage2_backfill_elaboration.py --checkpoint PATH [--limit N] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write
from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import GEN_MODEL, STAGE2_CHECKPOINT


SYSTEM_PROMPT: str = "You are a precise JSON generator. Return ONLY valid JSON. No markdown."


def _is_empty(val: object) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return not val.strip()
    if isinstance(val, list):
        return len(val) == 0
    return False


def _build_prompt(rec: dict) -> str:
    return (
        "Given this extracted principle, write a 3-5 sentence \"elaboration\": "
        "deeper nuance — edge cases, exceptions, and how the mechanism behaves "
        "under different conditions.\n"
        "Derive it ONLY from the provided fields; do NOT introduce new factual "
        "claims unsupported by them. Do not restate the definition.\n"
        "Return JSON with exactly one key: {\"elaboration\": \"...\"}\n\n"
        f"name: {rec.get('name', '')}\n"
        f"definition: {rec.get('definition', '')}\n"
        f"mechanism: {rec.get('mechanism', '')}\n"
        f"boundary: {rec.get('boundary', '')}\n"
        f"consequence: {rec.get('consequence', '')}\n"
    )


def _generate(rec: dict) -> str | None:
    """Return the new elaboration string, or None on failure (record left as-is)."""
    try:
        result = call_omlx_json(
            prompt=_build_prompt(rec),
            model=GEN_MODEL,
            system=SYSTEM_PROMPT,
            max_tokens=1024,
        )
        # call_omlx_json returns a dict, or [] on parse failure.
        if isinstance(result, dict):
            elab = result.get("elaboration", "")
            if isinstance(elab, str) and elab.strip():
                return elab.strip()
        elif isinstance(result, list) and result:
            # Some models return a list wrapping the object.
            first = result[0]
            if isinstance(first, dict):
                elab = first.get("elaboration", "")
                if isinstance(elab, str) and elab.strip():
                    return elab.strip()
        return None
    except Exception as e:
        print(f"      ⚠️  elaboration gen failed for {rec.get('fb_id', '?')[:12]}: {type(e).__name__}: {e}",
              file=sys.stderr, flush=True)
        return None


def backfill(checkpoint_path: str, limit: int | None, workers: int) -> dict:
    checkpoint_path = str(Path(checkpoint_path))
    records = load_jsonl(checkpoint_path, context="backfill checkpoint")

    # Identify single-source principles with empty elaboration.
    targets: list[tuple[int, dict]] = []
    for idx, rec in enumerate(records):
        if rec.get("is_convergent"):
            continue
        if rec.get("content_type") != "principle":
            continue
        if _is_empty(rec.get("elaboration")):
            targets.append((idx, rec))

    total: int = len(targets)
    print(f"🎯 Backfill targets: {total} single-source principles with empty elaboration "
          f"(of {len(records)} total records)")
    if limit is not None:
        targets = targets[:limit]
        print(f"   (limited to {limit})")

    filled: int = 0
    failed: int = 0
    t0: float = time.time()

    def _persist() -> None:
        content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        safe_write(checkpoint_path, content)

    if workers <= 1:
        for i, (idx, rec) in enumerate(targets, 1):
            new_elab = _generate(rec)
            if new_elab:
                rec["elaboration"] = new_elab
                filled += 1
            else:
                failed += 1
            if i % 100 == 0 or i == total:
                _persist()
                rate = (time.time() - t0) / max(i, 1)
                print(f"   💾 {i}/{total} — filled {filled}, failed {failed} "
                      f"({rate:.2f}s/rec, ETA {rate * (total - i):.0f}s)", flush=True)
    else:
        # Parallel backfill; assign results by index to preserve order.
        def _work(item):
            i, (idx, rec) = item
            return i, idx, _generate(rec)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_work, (i, item)): i for i, item in enumerate(targets)}
            for done in as_completed(futures):
                i, idx, new_elab = done.result()
                if new_elab:
                    records[idx]["elaboration"] = new_elab
                    filled += 1
                else:
                    failed += 1
                if (filled + failed) % 25 == 0:
                    done_n = filled + failed
                    rate = (time.time() - t0) / max(done_n, 1)
                    print(f"   {done_n}/{total} — filled {filled}, failed {failed} "
                          f"({rate:.2f}s/rec, ETA {rate * (total - done_n):.0f}s)", flush=True)

    # Write back the full checkpoint, atomically + crash-safe.
    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    safe_write(checkpoint_path, content)
    # Self-verify (fail-closed on any corruption).
    load_jsonl(checkpoint_path, context="backfill self-check")

    elapsed = time.time() - t0
    print(f"✅ Backfill complete: filled {filled}, failed {failed} in {elapsed:.0f}s "
          f"({elapsed / max(filled, 1):.2f}s/fill)")
    return {"targets": total, "filled": filled, "failed": failed, "elapsed": elapsed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default=str(STAGE2_CHECKPOINT),
                        help="Path to the S2 checkpoint JSONL to backfill")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only backfill the first N empty-elaboration principles (for testing)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Number of parallel LLM workers (default 4)")
    args = parser.parse_args()

    result = backfill(args.checkpoint, args.limit, args.workers)
    sys.exit(0 if result["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
