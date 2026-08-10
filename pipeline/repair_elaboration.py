#!/usr/bin/env python3
"""D2215: Elaboration repair pass — add missing elaboration field to existing FBs.

Batch processing: 5 FBs per LLM call, 3 parallel workers via ThreadPoolExecutor.
Crash-safe: writes progress to repair_checkpoint.jsonl every 5 batches.

Usage:
    python3 pipeline/repair_elaboration.py [--dry-run] [--batch-size 5]
"""
from __future__ import annotations

import concurrent.futures
import io
import json
import sys
import time
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Force unbuffered output
_sys = sys
_sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, write_through=True, line_buffering=True)

from pipeline.io_guard import safe_write
from pipeline.json_fixer import parse_json_robust
from pipeline.omlx_call import CircuitOpenError, call_omlx
from pipeline.pipeline_paths import STAGE2_CHECKPOINT

# Config
BATCH_SIZE: int = 5
MAX_WORKERS: int = 3
MODEL: str = "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit"
MAX_TOKENS: int = 1024
TIMEOUT: int = 300
REPAIR_CHECKPOINT: Path = STAGE2_CHECKPOINT.parent / "checkpoint.jsonl.repaired"

SYSTEM_PROMPT: str = (
    "You are a precise JSON generator. Return ONLY valid JSON. No markdown, no explanation."
)


def build_batch_prompt(fbs: list[dict]) -> str:
    """Build a batch prompt for 5 FBs."""
    items: list[str] = []
    for i, fb in enumerate(fbs):
        evidence_text: str = " | ".join(fb.get("evidence_passages", [])[:2])[:600]
        items.append(
            f"### FB {i + 1}\n"
            f"name: {fb['name']}\n"
            f"definition: {fb.get('definition', '')}\n"
            f"mechanism: {fb.get('mechanism', '')}\n"
            f"boundary: {fb.get('boundary', '')}\n"
            f"consequence: {fb.get('consequence', '')}\n"
            f"evidence: {evidence_text}"
        )

    prompt: str = (
        "For each of the 5 principles below, write an \"elaboration\" field: "
        "3-5 sentences of deeper nuance that the definition/mechanism/boundary/consequence "
        "do NOT already cover — edge cases, exceptions, implicit assumptions, cross-domain "
        "applications, or known caveats. Do NOT repeat content from existing fields.\n\n"
        + "\n\n".join(items)
        + "\n\nReturn JSON array of exactly 5 objects, in order:\n"
        '[{"name": "<exact name from FB 1>", "elaboration": "<3-5 sentences>"}, ...]'
    )
    return prompt


def process_batch(batch: list[dict], batch_idx: int) -> list[dict] | None:
    """Process one batch of 5 FBs. Returns updated FBs or None on failure."""
    prompt: str = build_batch_prompt(batch)
    cid: str = f"batch_{batch_idx}"

    for attempt in range(2):
        try:
            raw: str = call_omlx(
                prompt=prompt,
                model=MODEL,
                system=SYSTEM_PROMPT,
                max_tokens=MAX_TOKENS,
                timeout=TIMEOUT,
            )
            result = parse_json_robust(raw)

            if not isinstance(result, list) or len(result) < len(batch):
                print(f"   ⚠️  {cid}: expected list[{len(batch)}], got {type(result).__name__} "
                      f"(len={len(result) if isinstance(result, list) else 'N/A'}) — retry {attempt + 1}/2")
                continue

            # Apply elaborations to FBs
            updated: list[dict] = []
            for i, fb in enumerate(batch):
                fb_copy: dict = dict(fb)
                if i < len(result) and isinstance(result[i], dict):
                    elaboration: str = result[i].get("elaboration", "").strip()
                    if elaboration:
                        fb_copy["elaboration"] = elaboration
                    else:
                        fb_copy["elaboration"] = ""
                else:
                    fb_copy["elaboration"] = ""
                updated.append(fb_copy)
            return updated

        except CircuitOpenError:
            print(f"   ❌ {cid}: Circuit breaker open — aborting repair")
            raise
        except Exception as e:
            print(f"   ❌ {cid}: {type(e).__name__}: {e} — retry {attempt + 1}/2")
            time.sleep(2)

    return None  # Failed after 2 attempts


def main() -> None:
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Elaboration repair pass")
    parser.add_argument("--dry-run", action="store_true", help="Don't write checkpoint")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Batch size")
    parser.add_argument("--start", type=int, default=0, help="Start from batch index (resume)")
    args = parser.parse_args()

    batch_size: int = args.batch_size
    dry_run: bool = args.dry_run

    # Load FBs
    checkpoint_path: Path = Path(STAGE2_CHECKPOINT)
    if not checkpoint_path.exists():
        print(f"❌ Checkpoint not found: {checkpoint_path}")
        sys.exit(1)

    all_fbs: list[dict] = []
    with open(checkpoint_path) as f:
        for line in f:
            line = line.strip()
            if line:
                all_fbs.append(json.loads(line))

    total: int = len(all_fbs)
    need_repair: list[tuple[int, dict]] = [
        (i, fb) for i, fb in enumerate(all_fbs) if not fb.get("elaboration")
    ]
    have_elab: int = total - len(need_repair)

    print(f"📋 Loaded {total} FBs — {have_elab} with elaboration, {len(need_repair)} need repair")
    if not need_repair:
        print("✅ All FBs have elaboration. Nothing to do.")
        return

    # Batch them
    batches: list[list[tuple[int, dict]]] = [
        need_repair[i : i + batch_size] for i in range(0, len(need_repair), batch_size)
    ]
    # Apply start offset for resume
    batches = batches[args.start :]
    print(f"⚡ Processing {len(batches)} batches (size={batch_size}) with {MAX_WORKERS} workers...")

    total_batches: int = len(batches)
    completed: int = args.start
    repaired: int = 0
    failed: int = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures: dict = {}
        # Submit first batch
        for b in batches[:MAX_WORKERS]:
            idx: int = completed
            fbs_only: list[dict] = [fb for _, fb in b]
            futures[executor.submit(process_batch, fbs_only, idx)] = (idx, b)

        while futures:
            done_futures: set = concurrent.futures.wait(
                futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED
            ).done

            for future in done_futures:
                idx, batch = futures.pop(future)
                completed += 1

                try:
                    updated = future.result()
                except CircuitOpenError:
                    print(f"   ❌❌ Circuit breaker open at batch {completed}/{total_batches} — aborting")
                    executor.shutdown(wait=False, cancel_futures=True)
                    # Save progress before exit
                    _save_checkpoint(all_fbs, dry_run)
                    sys.exit(1)
                except Exception as e:
                    print(f"   ❌ Batch {completed}/{total_batches}: {e}")
                    failed += len(batch)
                    continue

                if updated is None:
                    print(f"   ❌ Batch {completed}/{total_batches}: failed after retries")
                    failed += len(batch)
                    continue

                # Apply updates to all_fbs
                for j, (orig_idx, _) in enumerate(batch):
                    if j < len(updated):
                        all_fbs[orig_idx] = updated[j]
                repaired += len(batch)

                name_sample: str = updated[0].get("name", "?")[:40] if updated else "?"
                elab_len: int = len(updated[0].get("elaboration", "")) if updated else 0
                print(f"  [{completed}/{total_batches}] ✅ {name_sample}... "
                      f"+{len(batch)} FBs (elab: {elab_len}c)")

                # Submit next batch if any remain
                next_idx: int = completed + len(futures)
                if next_idx < len(batches):
                    next_batch: list[tuple[int, dict]] = batches[next_idx]
                    next_fbs: list[dict] = [fb for _, fb in next_batch]
                    futures[executor.submit(process_batch, next_fbs, next_idx)] = (next_idx, next_batch)

                # Crash-safe checkpoint every 5 batches
                if completed % 5 == 0:
                    _save_checkpoint(all_fbs, dry_run)

    # Final save
    _save_checkpoint(all_fbs, dry_run)
    print(f"\n✅ Done. {repaired} FBs repaired, {failed} failed, {total - repaired - failed} already had elaboration.")
    print(f"   Checkpoint: {checkpoint_path}")


def _save_checkpoint(all_fbs: list[dict], dry_run: bool) -> None:
    """Write checkpoint (crash-safe)."""
    if dry_run:
        print("   [dry-run] Would write checkpoint")
        return

    content: str = "\n".join(json.dumps(f, ensure_ascii=False) for f in all_fbs) + "\n"
    safe_write(STAGE2_CHECKPOINT, content, force_shrink=True)


if __name__ == "__main__":
    main()
