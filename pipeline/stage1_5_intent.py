#!/usr/bin/env python3
"""
stage1_5_intent.py — Semantic intent pre-filter for focused extraction
=========================================================================
Authority: CONSTITUTION.md §3 (Stage 1.5), D2013, D2043
Source: temp/stage1_5_intent_v6_1.py (prototype), Kimi review L178 (threshold-based)

Purpose: Before Stage 2 extraction, filter chunks by semantic similarity to the
extraction intent. Only relevant chunks proceed to expensive LLM extraction.
Saves ~80% compute on focused runs (marketing-only, pricing-only, etc.).

Input:  Stage 1 chunks checkpoint (stage1_chunk.jsonl)
Output: Filtered chunks → Stage 2 only processes relevant content

Usage:
    python3 pipeline/stage1_5_intent.py --intent "pricing strategy, anchoring, value-based pricing"
    python3 pipeline/stage1_5_intent.py --intent "marketing" --threshold 0.35 --top-k 0.30
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.metrics import StageTimer, log_metric
from pipeline.pipeline_paths import (
    EMBED_MODEL,
    INTENT_THRESHOLD,
    INTENT_TOP_K_RATIO,
    OLLAMA_URL,
    STAGE1_CHECKPOINT,
    STAGE1_OUTPUT,
)
from pipeline.stamp import get_pipeline_run_id

# ── Embedding helper ──────────────────────────────────────────────────

def embed_texts(texts: list[str], model: str = None) -> list[list[float]]:
    """Batch-embed texts via Ollama. Returns list of embedding vectors."""
    if model is None:
        model = EMBED_MODEL
    embeddings = []
    for text in texts:
        try:
            r = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": model, "prompt": text[:8192]},  # bge-m3: 8192 token context
                timeout=30,
            )
            if r.status_code == 200:
                embeddings.append(r.json()["embedding"])
            else:
                embeddings.append([])
        except Exception:
            embeddings.append([])
    return embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    a_np = np.array(a)
    b_np = np.array(b)
    dot = np.dot(a_np, b_np)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


# ── Intent filter ────────────────────────────────────────────────────

def filter_chunks(
    chunks: list[dict],
    intent: str,
    threshold: float = 0.35,
    top_k_ratio: float = 0.30,
) -> tuple[list[dict], dict]:
    """Filter chunks by semantic similarity to intent.

    Args:
        chunks: List of chunk dicts with 'text' field
        intent: Description of extraction intent (e.g., "pricing strategy")
        threshold: Minimum cosine similarity to keep a chunk
        top_k_ratio: Keep at least this fraction of chunks (overrides threshold)

    Returns:
        (filtered_chunks, stats_dict)
    """
    if not chunks:
        return [], {"total": 0, "kept": 0, "ratio": 0.0}

    # Embed intent once
    intent_emb = embed_texts([intent])[0]
    if not intent_emb:
        print("   ⚠️  Intent embedding failed. Passing all chunks through.")
        log_metric("stage1_5", error="intent_embed_failed", total=len(chunks))
        return chunks, {"total": len(chunks), "kept": len(chunks), "ratio": 1.0}

    # Extract text from chunks
    texts = [c.get("text", c.get("body", "")) for c in chunks]

    # Embed all chunks (batch if needed)
    chunk_embs = embed_texts(texts)

    # Score each chunk
    scored = []
    for i, emb in enumerate(chunk_embs):
        score = cosine_similarity(emb, intent_emb) if emb else 0.0
        scored.append((score, chunks[i]))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Apply threshold + top-k
    top_k = max(1, int(len(scored) * top_k_ratio))
    kept = []
    for score, chunk in scored:
        if score >= threshold or len(kept) < top_k:
            kept.append(chunk)

    stats = {
        "total": len(chunks),
        "kept": len(kept),
        "ratio": round(len(kept) / max(len(chunks), 1), 3),
        "threshold": threshold,
        "top_k_ratio": top_k_ratio,
        "intent": intent,
        "mean_score": round(float(np.mean([s for s, _ in scored])), 4) if scored else 0.0,
    }

    return kept, stats


# ── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Stage 1.5: Semantic intent pre-filter")
    parser.add_argument("--intent", type=str, required=True,
                       help="Extraction intent description (e.g., 'pricing strategy, anchoring')")
    parser.add_argument("--threshold", type=float, default=INTENT_THRESHOLD,
                       help=f"Minimum cosine similarity (default: {INTENT_THRESHOLD})")
    parser.add_argument("--top-k", type=float, default=INTENT_TOP_K_RATIO,
                       help=f"Keep at least this fraction of chunks (default: {INTENT_TOP_K_RATIO})")
    parser.add_argument("--chunk-limit", type=int, default=0,
                       help="Limit chunks for testing (0 = all)")
    args = parser.parse_args()

    run_id = get_pipeline_run_id()

    with StageTimer("stage1_5", run_id, {"intent": args.intent}):
        # Load chunks from Stage 1
        if not STAGE1_CHECKPOINT.exists():
            print(f"❌ Stage 1 checkpoint not found: {STAGE1_CHECKPOINT}")
            sys.exit(1)

        chunks = []
        with open(STAGE1_CHECKPOINT) as f:
            for line in f:
                try:
                    chunks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if args.chunk_limit:
            chunks = chunks[:args.chunk_limit]

        print(f"   Loaded {len(chunks)} chunks from Stage 1")
        print(f"   Intent: {args.intent}")
        print(f"   Embedding model: {EMBED_MODEL}")

        # Filter
        filtered, stats = filter_chunks(
            chunks, args.intent,
            threshold=args.threshold,
            top_k_ratio=args.top_k,
        )

        print(f"   Kept {stats['kept']}/{stats['total']} chunks ({stats['ratio']:.1%})")
        print(f"   Mean similarity: {stats['mean_score']:.4f}")

        # Write filtered output
        output_path = STAGE1_OUTPUT.parent / "stage1_5_filtered.jsonl"
        safe_write(filtered, output_path)
        print(f"   Wrote filtered chunks → {output_path}")

        # Log metrics
        log_metric("stage1_5", **stats)


if __name__ == "__main__":
    main()
