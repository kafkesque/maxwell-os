#!/usr/bin/env python3
"""
benchmark_faiss_vs_usearch.py — FAISS vs USearch clustering benchmark (P1.1).
=============================================================================
Authority: D2120 Phase 1.1 | CONSTITUTION.md C24 (hardware-adaptive)

Compares FAISS+R-NN clustering against USearch built-in clustering on real
pipeline segments. Measures: cluster quality, speed, memory, and stability.

Usage:
    python3 benchmarks/benchmark_faiss_vs_usearch.py
    python3 benchmarks/benchmark_faiss_vs_usearch.py --n 2000 --threshold 0.70
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import faiss
import numpy as np
from usearch.index import Index as USearchIndex

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.ollama_embed import batch_embed
from pipeline.pipeline_paths import CHECKPOINT_DIR

# ── Data Loading ──────────────────────────────────────────────────────────

def load_segments(max_n: int = 1000) -> list[dict]:
    """Load sample segments from checkpoint."""
    checkpoint = CHECKPOINT_DIR / "stage1_chunk.jsonl"
    if not checkpoint.exists():
        print(f"❌ No checkpoint at {checkpoint}")
        sys.exit(1)

    segments: list[dict] = []
    with open(checkpoint) as f:
        for line in f:
            line = line.strip()
            if not line or len(segments) >= max_n:
                break
            seg = json.loads(line)
            text = seg.get("text", "").strip()
            if text and len(text) >= 40:
                segments.append(seg)

    print(f"📂 Loaded {len(segments)} segments from checkpoint")
    return segments


# ── FAISS + R-NN Clustering (our current approach) ──────────────────────

def faiss_rnn_cluster(
    embeddings: np.ndarray,
    threshold: float = 0.70,
    min_size: int = 2,
    neighbor_k: int = 50,
) -> tuple[dict, float]:
    """FAISS IndexFlatIP + Reciprocal Nearest-Neighbor clustering."""
    n, dim = embeddings.shape
    start = time.time()

    # Build FAISS index
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    build_time = time.time() - start

    # Search k-NN
    k = min(neighbor_k, n)
    sims, neigh = index.search(embeddings, k)
    search_time = time.time() - start - build_time

    # R-NN: build neighbor sets
    neighbor_sets: list[set[int]] = []
    for i in range(n):
        nbrs = {int(neigh[i, j]) for j in range(k) if neigh[i, j] != i and sims[i, j] >= threshold}
        neighbor_sets.append(nbrs)

    # Union-find on reciprocal edges only
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    reciprocal = 0
    total_edges = 0
    for i in range(n):
        for j in neighbor_sets[i]:
            total_edges += 1
            if i in neighbor_sets[j]:
                union(i, j)
                reciprocal += 1

    # Collect clusters
    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    # Filter by min_size
    result = {
        str(cid): idxs
        for cid, idxs in clusters.items()
        if len(idxs) >= min_size
    }

    singletons = n - sum(len(v) for v in result.values())
    total_time = time.time() - start

    metrics = {
        "build_s": build_time,
        "search_s": search_time,
        "clustering_s": total_time - build_time - search_time,
        "total_s": total_time,
        "n_clusters": len(result),
        "n_singletons": singletons,
        "avg_cluster_size": np.mean([len(v) for v in result.values()]) if result else 0,
        "reciprocal_pct": (reciprocal / total_edges * 100) if total_edges else 0,
    }
    return result, metrics


# ── USearch Clustering ────────────────────────────────────────────────────

def usearch_cluster(
    embeddings: np.ndarray,
    threshold: float = 0.70,
    min_size: int = 2,
) -> tuple[dict, float]:
    """USearch HNSW index + built-in clustering."""
    n, dim = embeddings.shape
    start = time.time()

    # Build USearch index
    idx = USearchIndex(ndim=dim, metric="cos")
    keys = np.arange(n, dtype=np.uintp)
    idx.add(keys, embeddings)
    build_time = time.time() - start

    # Built-in clustering
    try:
        clustering = idx.cluster(
            vectors=embeddings,
            min_count=min_size,
            max_count=n,
            threads=4,
        )
    except Exception as e:
        print(f"   ⚠️  USearch cluster() failed: {e}")
        return {}, {"error": str(e), "total_s": time.time() - start}

    # Parse clustering result
    cluster_time = time.time() - start - build_time
    result: dict[str, list[int]] = defaultdict(list)

    # USearch clustering returns (centroids, assignments) or similar
    if hasattr(clustering, "assignments"):
        for i, cid in enumerate(clustering.assignments):
            result[str(cid)].append(i)
    elif hasattr(clustering, "labels"):
        for i, cid in enumerate(clustering.labels):
            result[str(cid)].append(i)
    elif isinstance(clustering, np.ndarray):
        for i, cid in enumerate(clustering):
            result[str(cid)].append(i)
    else:
        # Fallback: try iterating
        for i, cid in enumerate(clustering):
            result[str(cid)].append(i)

    total_time = time.time() - start
    singletons = n - sum(len(v) for v in result.values())

    return dict(result), {
        "build_s": build_time,
        "clustering_s": cluster_time,
        "total_s": total_time,
        "n_clusters": len(result),
        "n_singletons": singletons,
        "avg_cluster_size": np.mean([len(v) for v in result.values()]) if result else 0,
    }


# ── Quality Metrics ──────────────────────────────────────────────────────

def evaluate_clusters(
    clusters: dict[str, list[int]],
    segments: list[dict],
) -> dict:
    """Compute cluster quality metrics."""
    if not clusters:
        return {"error": "no clusters"}

    sizes = [len(v) for v in clusters.values()]
    source_diversity_scores = []

    for idxs in clusters.values():
        books = set()
        for i in idxs:
            if i < len(segments):
                books.add(segments[i].get("source_book", "unknown"))
        diversity = len(books)
        source_diversity_scores.append(diversity)

    return {
        "n_clusters": len(clusters),
        "total_clustered": sum(sizes),
        "mean_size": float(np.mean(sizes)),
        "median_size": float(np.median(sizes)),
        "min_size": int(np.min(sizes)) if sizes else 0,
        "max_size": int(np.max(sizes)) if sizes else 0,
        "size_std": float(np.std(sizes)),
        "mean_source_diversity": float(np.mean(source_diversity_scores)),
        "clusters_with_diversity_ge2": sum(1 for d in source_diversity_scores if d >= 2),
    }


# ── Main Benchmark ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="FAISS vs USearch clustering benchmark (P1.1)")
    parser.add_argument("--n", type=int, default=1000, help="Number of segments (default 1000)")
    parser.add_argument("--threshold", type=float, default=0.70, help="Cosine similarity threshold")
    parser.add_argument("--min-size", type=int, default=2, help="Min cluster size")
    parser.add_argument("--skip-embed", action="store_true", help="Use random embeddings (faster)")
    args = parser.parse_args()

    print("=" * 60)
    print("FAISS vs USearch Clustering Benchmark (P1.1)")
    print("=" * 60)
    print(f"  Segments: {args.n}  |  Threshold: {args.threshold}  |  Min size: {args.min_size}")

    # Load or generate embeddings
    if args.skip_embed:
        print("\n⚠️  Using random embeddings (--skip-embed)")
        np.random.seed(42)
        embeddings = np.random.randn(args.n, 1024).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        segments = [{"text": f"seg_{i}", "source_book": f"book_{i % 5}"} for i in range(args.n)]
    else:
        segments = load_segments(args.n)
        # Embed
        print(f"🧠 Embedding {len(segments)} segments via bge-m3...")
        texts = [s["text"][:1500] for s in segments]
        start = time.time()
        raw = batch_embed(texts, model="bge-m3")
        emb_time = time.time() - start
        embeddings = np.array([np.array(e, dtype=np.float32) for e in raw if len(e) > 0])
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embeddings = embeddings / norms
        print(f"   {len(embeddings)} embeddings in {emb_time:.1f}s")

    # ── FAISS + R-NN ──
    print(f"\n{'─'*40}")
    print("🔵 FAISS + R-NN Clustering")
    print(f"{'─'*40}")
    faiss_clusters, faiss_metrics = faiss_rnn_cluster(
        embeddings, threshold=args.threshold, min_size=args.min_size
    )
    faiss_quality = evaluate_clusters(faiss_clusters, segments)
    for k, v in faiss_metrics.items():
        print(f"   {k}: {v:.3f}" if isinstance(v, float) else f"   {k}: {v}")

    # ── USearch ──
    print(f"\n{'─'*40}")
    print("🟠 USearch Clustering")
    print(f"{'─'*40}")
    usearch_clusters, usearch_metrics = usearch_cluster(
        embeddings, threshold=args.threshold, min_size=args.min_size
    )
    usearch_quality = evaluate_clusters(usearch_clusters, segments)
    for k, v in usearch_metrics.items():
        print(f"   {k}: {v:.3f}" if isinstance(v, float) else f"   {k}: {v}")

    # ── Comparison ──
    print(f"\n{'='*60}")
    print("📊 COMPARISON")
    print(f"{'='*60}")
    print(f"{'Metric':<30} {'FAISS+R-NN':>12} {'USearch':>12}")
    print(f"{'─'*30} {'─'*12} {'─'*12}")

    comparisons = [
        ("n_clusters", "n_clusters"),
        ("mean_cluster_size", "mean_size"),
        ("median_cluster_size", "median_size"),
        ("source_diversity_ge2", "clusters_with_diversity_ge2"),
        ("total_time (s)", "total_s"),
    ]

    # Map quality metrics for FAISS
    fq = faiss_quality
    uq = usearch_quality
    fm = faiss_metrics
    um = usearch_metrics

    for label, key in comparisons:
        f_val = fq.get(key, fm.get(key, "N/A"))
        u_val = uq.get(key, um.get(key, "N/A"))
        f_str = f"{f_val:.1f}" if isinstance(f_val, float) else str(f_val)
        u_str = f"{u_val:.1f}" if isinstance(u_val, float) else str(u_val)
        print(f"{label:<30} {f_str:>12} {u_str:>12}")

    # Winner
    faiss_time = fm.get("total_s", 999)
    usearch_time = um.get("total_s", 999)
    faiss_n = fq.get("n_clusters", 0)
    usearch_n = uq.get("n_clusters", 0)

    print("\n📋 Verdict:")
    if faiss_time < usearch_time:
        print(f"   ⚡ FAISS faster: {faiss_time:.1f}s vs {usearch_time:.1f}s ({(usearch_time/faiss_time - 1)*100:+.0f}%)")
    else:
        print(f"   ⚡ USearch faster: {usearch_time:.1f}s vs {faiss_time:.1f}s ({(faiss_time/usearch_time - 1)*100:+.0f}%)")

    if faiss_n > usearch_n:
        print(f"   🎯 FAISS more clusters: {faiss_n} vs {usearch_n}")
    elif usearch_n > faiss_n:
        print(f"   🎯 USearch more clusters: {usearch_n} vs {faiss_n}")


if __name__ == "__main__":
    main()
