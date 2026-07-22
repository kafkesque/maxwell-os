#!/usr/bin/env python3
"""
stage2_extract.py — Extract principles from segments via Qwen3.6 + MinHash dedup.
================================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 2), R5, R7, C8

Input:  Segments from Stage 1 checkpoint
Output: Principles with MinHash near-dedup, checkpoint at stage2_extract.jsonl

Process:
  1. Batch segments into groups of ~10
  2. Send each batch to Qwen3.6 with temp=0.0
  3. Parse JSON response, extract principles
  4. MinHash near-dedup: skip principles that are >90% similar to existing
  5. Write checkpoint

Generator model: Qwen3.6-35B-A3B-4bit (OMLX)
temp: 0.0 (R7)

Usage:
    python3 pipeline/stage2_extract.py
    python3 pipeline/stage2_extract.py --batch-size 15 --minhash-threshold 0.90
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    STAGE1_CHECKPOINT,
    STAGE2_CHECKPOINT,
    CHECKPOINT_DIR,
    GEN_MODEL,
    BORP_MIN_SOURCES,
)
from pipeline.stamp import stamp_record, make_hash_id, get_pipeline_commit
from pipeline.omlx_call import call_omlx_json, check_omlx_health
from pipeline.io_guard import safe_write

# ── Constants ──────────────────────────────────────────────────────────────
BATCH_SIZE = 10  # Segments per LLM call
MINHASH_THRESHOLD = 0.90  # Jaccard similarity threshold for near-dedup
MINHASH_NUM_PERM = 128  # Number of MinHash permutations

# ── Prompt templates ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a principle extraction engine. Your task is to identify reusable, 
actionable principles from text segments. 

A principle is:
- A concise, standalone statement of a concept that can be applied across contexts
- 1-3 sentences, specific enough to be useful, general enough to be reusable
- NOT a summary of the text
- NOT a fact about the specific book or author
- NOT a tool instruction ("use the + operator in Altair", "set env vars in R")
- NOT a syntax explanation ("functions take parameters with defaults")
- NOT a system design document ("retail inventory event architecture")

A principle answers WHY and WHEN, not just WHAT or HOW.

EXAMPLES OF GOOD PRINCIPLES (what to extract):
- "Descriptive references use named identifiers instead of positional indices to create robust code. Named column references survive structure changes that break positional access."
- "AI capabilities have a jagged frontier — strong on some tasks, weak on closely related ones. Map it empirically rather than assuming uniform competence."
- "Narrative framing structures user flows using story patterns (arcs, tension/release) to create emotional engagement beyond functional sequences."
- "Technologies follow S-curve logistic growth — rapid exponential improvement, then gradual slowdown as limits are approached."
- "Autoencoders learn compressed representations by forcing data through a bottleneck layer that preserves only salient features."

ANTI-PATTERNS (do NOT extract):
- "Altair's + operator layers independent marks" — this is a tool feature, not a principle
- "Function parameters allow developers to customize behavior" — this is syntax, not insight
- "RStudio's Environment tab shows loaded objects" — this is a UI description
- "Computer vision + event bus enables real-time inventory" — this is a system design doc

For each segment, extract 0-3 principles. If the segment contains no extractable principles, return an empty list.

CRITICAL RULES (non-negotiable):
- ONLY extract principles EXPLICITLY stated in the text. Never fabricate.
- If no principles are found, return an empty list: []
- Do NOT generalize beyond what the text explicitly says.
- Do NOT add numbers, statistics, or data unless verbatim in source.
- A principle must be traceable back to a specific sentence in the source.

Return ONLY a JSON array of objects with this structure:
[{"text": "The principle statement", "source_segment": "segment_id_here"}, ...]"""


def build_extraction_prompt(segments: list[dict]) -> str:
    """Build the extraction prompt for a batch of segments."""
    lines = ["Extract principles from these text segments. Return ONLY a JSON array.\n"]
    for seg in segments:
        lines.append(f"--- SEGMENT {seg['segment_id'][:12]} ---")
        lines.append(seg["text"][:1500])  # Truncate very long segments
        lines.append("")
    lines.append("---")
    lines.append("Return JSON array of principles: [{\"text\": \"...\", \"source_segment\": \"...\"}, ...]")
    return "\n".join(lines)


# ── MinHash near-dedup ─────────────────────────────────────────────────────

def init_minhash_lsh():
    """Initialize MinHash LSH index for near-dedup. Falls back gracefully."""
    try:
        from datasketch import MinHash, MinHashLSH
        lsh = MinHashLSH(threshold=MINHASH_THRESHOLD, num_perm=MINHASH_NUM_PERM)
        return lsh, True
    except ImportError as e:
        # C16: No silent errors — log AND raise. Near-dedup is critical for quality.
        import logging
        logging.error("datasketch not installed. Near-dedup REQUIRED. Install: pip install datasketch")
        raise ImportError(
            "datasketch is required for MinHash near-dedup. "
            "Install: pip install datasketch"
        ) from e


def make_minhash(text: str, num_perm: int = MINHASH_NUM_PERM):
    """Create a MinHash for a text string."""
    from datasketch import MinHash
    mh = MinHash(num_perm=num_perm)
    for word in text.lower().split():
        mh.update(word.encode("utf-8"))
    return mh


def is_near_duplicate(text: str, lsh, minhash_cache: dict) -> tuple[bool, Optional[str]]:
    """Check if a principle is a near-duplicate of any existing principle.

    Returns (is_dup: bool, signature: str|None).
    """
    if lsh is None:
        return False, None

    from datasketch import MinHash
    mh = make_minhash(text)

    # Query LSH for near-duplicates
    results = lsh.query(mh)
    if results:
        return True, None

    # Store in LSH
    sig = f"mh_{len(minhash_cache)}"
    lsh.insert(sig, mh)
    minhash_cache[sig] = text
    return False, sig


def load_stage1_segments() -> list[dict]:
    """Load segments from Stage 1 checkpoint."""
    if not STAGE1_CHECKPOINT.exists():
        print("❌ Stage 1 checkpoint not found. Run stage1_chunk.py first.")
        sys.exit(1)

    segments = []
    with open(STAGE1_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                segments.append(json.loads(line))
    return segments


def run_stage2(batch_size: int = BATCH_SIZE,
               minhash_threshold: float = MINHASH_THRESHOLD,
               intent: str = None):
    """Run Stage 2: Extract principles from segments.

    If intent is provided, focuses extraction on that domain (e.g.
    'pricing strategy, cost modeling, revenue, financial planning').
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # Health check — stress-test chat, not just ping
    from pipeline.omlx_call import stress_test_omlx, check_omlx_health
    if not check_omlx_health():
        print("❌ OMLX server is not responding. Start OMLX first.")
        sys.exit(1)
    stress = stress_test_omlx(model=GEN_MODEL, prompt_sizes=[50, 1000, 5000], verbose=True)
    if not stress["healthy"]:
        print(f"❌ OMLX chat check FAILED: {stress['verdict']}")
        print("   The server responds to health checks but chat completions are broken.")
        print("   Restart OMLX and re-run.")
        sys.exit(1)

    # Build system prompt with optional domain intent
    system_prompt = SYSTEM_PROMPT
    if intent:
        system_prompt += f"\n\nFOCUS: Extract ONLY principles related to: {intent}. "
        system_prompt += "Ignore principles unrelated to these topics. "
        system_prompt += "If a segment contains no principles about these topics, return []."

    segments = load_stage1_segments()
    print(f"🧠 Stage 2: Extract Principles — {len(segments)} segments")
    print(f"   Model: {GEN_MODEL} | temp=0.0 | batch_size={batch_size}")
    if intent:
        print(f"   Intent: {intent}")
        print(f"   ⚠️  Intent is prompt-level focus only. For chunk-level semantic filtering, run stage1_5_intent.py first.")
    print(f"{'='*60}")

    lsh, minhash_ok = init_minhash_lsh()
    minhash_cache: dict = {}
    all_principles: list[dict] = []
    total_extracted = 0
    total_skipped = 0
    pipeline_commit = get_pipeline_commit()

    # Process in batches
    batches = [segments[i:i + batch_size] for i in range(0, len(segments), batch_size)]

    # Load existing checkpoint for resume
    processed_seg_ids: set[str] = set()
    segids_file = str(STAGE2_CHECKPOINT) + ".segids"
    if STAGE2_CHECKPOINT.exists() and os.path.exists(segids_file):
        try:
            with open(STAGE2_CHECKPOINT) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_principles.append(json.loads(line))
            with open(segids_file) as f:
                processed_seg_ids = set(json.load(f))
            print(f"   📋 Resuming: {len(processed_seg_ids)} segments processed → {len(all_principles)} principles so far")
        except Exception:
            all_principles = []
            processed_seg_ids = set()

    # Track total so batch numbering is correct
    initial_principle_count = len(all_principles)

    for batch_idx, batch in enumerate(batches, 1):
        # Skip batches where ALL segments are already processed
        batch_seg_ids = {s.get("segment_id", "") for s in batch}
        if batch_seg_ids and batch_seg_ids.issubset(processed_seg_ids):
            continue  # Skip silently

        print(f"  [{batch_idx}/{len(batches)}] Batch of {len(batch)} segments", end=" ")

        start = time.time()
        try:
            prompt = build_extraction_prompt(batch)
            result = call_omlx_json(
                prompt=prompt,
                model=GEN_MODEL,
                system=system_prompt,
                max_tokens=4096,
            )
        except Exception as e:
            print(f"→ ❌ OMLX error: {e}")
            continue

        # Parse results
        if not isinstance(result, list):
            print(f"→ ⚠️  Unexpected response type: {type(result).__name__}")
            continue

        batch_principles = 0
        for item in result:
            if not isinstance(item, dict):
                continue
            principle_text = item.get("text", "").strip()
            source_segment = item.get("source_segment", "")
            if not principle_text or len(principle_text) < 20:
                continue

            # MinHash near-dedup
            is_dup, sig = is_near_duplicate(principle_text, lsh, minhash_cache)
            if is_dup:
                total_skipped += 1
                continue

            # Collect source books from source segment
            source_book = ""
            for seg in batch:
                if seg["segment_id"].startswith(source_segment[:12]):
                    source_book = seg.get("source_book", "")
                    break

            principle = {
                "principle_id": make_hash_id(principle_text),
                "principle_text": principle_text,
                "source_segments": [source_segment] if source_segment else [],
                "source_books": [source_book] if source_book else [],
                "batch_index": batch_idx,
                "minhash_signature": sig,
            }
            principle = stamp_record(principle, gen_model=GEN_MODEL)
            principle["pipeline_commit"] = pipeline_commit
            all_principles.append(principle)
            batch_principles += 1

        elapsed = time.time() - start
        total_extracted += batch_principles
        print(f"→ {batch_principles} principles ({elapsed:.1f}s)")

        # Incremental checkpoint — write every 5 batches to avoid data loss on crash
        if batch_idx % 5 == 0 or batch_idx == len(batches):
            seen_ids: set[str] = set()
            deduped = []
            for p in all_principles:
                if p["principle_id"] not in seen_ids:
                    seen_ids.add(p["principle_id"])
                    deduped.append(p)
            safe_write(
                STAGE2_CHECKPOINT,
                "\n".join(json.dumps(p, ensure_ascii=False) for p in deduped) + "\n",
            )
            # Track processed segment IDs for resume
            processed_ids = set()
            for p in deduped:
                for seg in p.get("source_segments", []):
                    processed_ids.add(seg)
            with open(str(STAGE2_CHECKPOINT) + ".segids", "w") as f:
                json.dump(list(processed_ids), f)

    # Deduplicate by principle_id (exact duplicates that slipped through)
    seen_ids: set[str] = set()
    deduped = []
    for p in all_principles:
        if p["principle_id"] not in seen_ids:
            seen_ids.add(p["principle_id"])
            deduped.append(p)

    # Write checkpoint
    safe_write(
        STAGE2_CHECKPOINT,
        "\n".join(json.dumps(p, ensure_ascii=False) for p in deduped) + "\n",
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Principles extracted:  {total_extracted}")
    print(f"🗑️  Near-duplicates:       {total_skipped}")
    print(f"🔑 Unique after dedup:    {len(deduped)}")
    print(f"📋 Checkpoint:            {STAGE2_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(description="Stage 2: Extract Principles via Qwen3.6")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help=f"Segments per LLM call (default: {BATCH_SIZE})")
    parser.add_argument("--minhash-threshold", type=float, default=MINHASH_THRESHOLD,
                        help=f"MinHash Jaccard threshold (default: {MINHASH_THRESHOLD})")
    parser.add_argument("--intent", type=str, default=None,
                        help="Domain-specific extraction focus (e.g. 'pricing strategy, cost modeling, revenue generation, financial planning')")
    args = parser.parse_args()

    run_stage2(batch_size=args.batch_size, minhash_threshold=args.minhash_threshold, intent=args.intent)


if __name__ == "__main__":
    main()
