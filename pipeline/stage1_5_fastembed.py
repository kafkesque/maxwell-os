#!/usr/bin/env python3
"""
stage1_5_fastembed.py — FAISS Clustering via fastembed (MLX-speed).
====================================================================
D2127r4: Replaces Ollama HTTP embedding with fastembed (ONNX-optimized).
D2178: Corrected speed estimate — measured ~47 seg/s on MPS, ~33 seg/s on Ollama.
       For 323K segments: ~115 min (MPS) or ~163 min (Ollama), not ~5 min.
Uses ONNX-optimized bge-small-en-v1.5 via fastembed library.

NOTE: The primary embedding path is now in stage1_5_embed_cluster.py which
uses sentence-transformers on MPS (~47 seg/s) as the default backend.
This file serves as the ONNX fastembed alternative path.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

# Load config
CONFIG_PATH: Path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
with open(CONFIG_PATH) as f:
    _CFG = yaml.safe_load(f)

S15 = _CFG.get("stage1_5", {})
S15_FAISS_THRESHOLD: float = float(S15.get("faiss_threshold", 0.75))
S15_EMBED_DIM: int = int(S15.get("embed_dim", 512))
S15_MIN_SOURCE_DIVERSITY: int = int(S15.get("min_source_diversity", 2))
S15_MIN_CLUSTER_SIZE: int = int(S15.get("min_cluster_size", 2))
S15_NEIGHBOR_K: int = int(S15.get("neighbor_k", 150))
S15_MAX_CLUSTER_SIZE: int = int(S15.get("max_cluster_size", 500))

from pipeline.pipeline_paths import (
    STAGE1_5_CHECKPOINT,
    STAGE1_CHECKPOINT,
)

BATCH_SIZE: int = 256
EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"

# ── Load segments ──────────────────────────────────────────────────────────

def load_segments() -> list[dict]:
    if not STAGE1_CHECKPOINT.exists():
        print(f"❌ Stage 1 checkpoint not found: {STAGE1_CHECKPOINT}")
        sys.exit(1)
    segments: list[dict] = []
    with open(STAGE1_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                segments.append(json.loads(line))
    return segments

# ── Embedding via fastembed ─────────────────────────────────────────────────

def embed_segments(segments: list[dict]) -> np.ndarray:
    from fastembed import TextEmbedding

    print(f"   Loading {EMBED_MODEL} via fastembed (ONNX)...", flush=True)
    model = TextEmbedding(model_name=EMBED_MODEL)

    texts: list[str] = [s["text"] for s in segments]
    total: int = len(texts)

    print(f"   Embedding {total:,} texts (fastembed native batching)...", flush=True)
    start: float = time.time()

    # Use fastembed's native batching — much faster than manual loop
    raw_embeddings = list(model.embed(texts, batch_size=BATCH_SIZE, show_progress_bar=True))

    elapsed = time.time() - start
    print(f"      → {len(raw_embeddings)} embeddings in {elapsed:.1f}s ({total/elapsed:.0f}/s)", flush=True)

    # Convert to numpy with dimension truncation
    all_embeddings: list[np.ndarray] = []
    for emb in raw_embeddings:
        arr = np.array(emb, dtype=np.float32)
        if S15_EMBED_DIM < len(arr):
            arr = arr[:S15_EMBED_DIM]
        all_embeddings.append(arr)

    return np.array(all_embeddings, dtype=np.float32)

# ── FAISS clustering ────────────────────────────────────────────────────────

def run_faiss_clustering(
    segments: list[dict],
    embeddings: np.ndarray,
    threshold: float,
    min_diversity: int,
) -> tuple[list[dict], list[dict]]:
    import faiss

    n, d = embeddings.shape
    print(f"\n   FAISS IndexFlatIP ({n} vectors, {d}-dim, threshold={threshold})...")

    # Normalize for cosine similarity (inner product on unit vectors)
    faiss.normalize_L2(embeddings)

    # Build index
    index = faiss.IndexFlatIP(d)
    index.add(embeddings)

    # Search: find all neighbors above threshold
    start = time.time()
    k: int = min(S15_NEIGHBOR_K, n)  # neighbor_k from config
    scores, indices = index.search(embeddings, k)

    # Union-find connected components
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    edges: int = 0
    for i in range(n):
        for j_idx in range(1, k):
            j = int(indices[i][j_idx])
            if j < 0 or j >= n:
                continue
            if scores[i][j_idx] >= threshold:
                union(i, j)
                edges += 1

    print(f"      {edges} edges above threshold {threshold}")

    # Group by root
    from collections import defaultdict
    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(i)

    # Build cluster records
    clusters: list[dict] = []
    singletons: list[dict] = []

    for root, member_indices in groups.items():
        members = [segments[i] for i in member_indices]
        source_books = list(set(m["source_book"] for m in members))
        is_conv = len(source_books) >= min_diversity

        cluster = {
            "cluster_id": f"cluster_{len(clusters):05d}",
            "segment_ids": [m["segment_id"] for m in members],
            "source_books": source_books,
            "source_diversity": len(source_books),
            "size": len(members),
            "cohesion": float(np.mean([scores[i][0] for i in member_indices])),
            "is_convergent": is_conv,
        }

        if len(members) == 1 or source_books == 1:
            # Split large single-source groups into singletons
            if len(members) > 1:
                for m in members:
                    single = {**cluster, "segment_ids": [m["segment_id"]], "size": 1}
                    singletons.append(single)
            else:
                singletons.append(cluster)
        else:
            clusters.append(cluster)

    elapsed = time.time() - start
    print(f"      → {len(clusters)} clusters, {len(singletons)} singletons ({elapsed:.1f}s)")

    return clusters, singletons

# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1.5: FAISS clustering via fastembed")
    parser.add_argument("--threshold", type=float, default=S15_FAISS_THRESHOLD,
                        help=f"Cosine similarity threshold (default: {S15_FAISS_THRESHOLD})")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit segments (for testing)")
    args = parser.parse_args()

    print("=" * 60)
    print("STAGE 1.5: FAISS Clustering (fastembed)")
    print("=" * 60)

    # Load
    segments = load_segments()
    if args.limit:
        segments = segments[:args.limit]
    print(f"   Loaded {len(segments):,} segments from Stage 1")

    # Embed
    embeddings = embed_segments(segments)

    # Cluster
    clusters, singletons = run_faiss_clustering(
        segments, embeddings, args.threshold, S15_MIN_SOURCE_DIVERSITY
    )

    # Write checkpoints
    STAGE1_5_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)

    with open(STAGE1_5_CHECKPOINT, "w") as f:
        for c in clusters:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    singleton_path = STAGE1_5_CHECKPOINT.parent / "singletons.jsonl"
    with open(singleton_path, "w") as f:
        for s in singletons:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    # Summary
    total_clustered = sum(c["size"] for c in clusters)
    print(f"\n{'=' * 60}")
    print(f"✅ Clusters:        {len(clusters)} (covering {total_clustered} segments)")
    print(f"📖 Singletons:       {len(singletons)}")
    print(f"🌐 Convergent (≥{S15_MIN_SOURCE_DIVERSITY} books): {sum(1 for c in clusters if c['is_convergent'])}")
    print(f"📋 Checkpoint:       {STAGE1_5_CHECKPOINT}")
    print(f"📋 Singletons:       {singleton_path}")

if __name__ == "__main__":
    main()
