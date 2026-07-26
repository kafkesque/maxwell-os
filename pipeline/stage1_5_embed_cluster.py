#!/usr/bin/env python3
"""
stage1_5_embed_cluster.py — FAISS Cosine Clustering on Raw Segments.
=====================================================================
Authority: D2094, D2101 | CONSTITUTION.md §3 (Pipeline Stage 1.5 — NEW)

Input:  Prefiltered segments from Stage 1.3 checkpoint (or Stage 1 fallback)
Output: Semantic clusters with source diversity scoring

Process:
  1. Load segments from Stage 1.3 or Stage 1
  2. Embed raw segment text via bge-m3 (Ollama, 1024-dim)
  3. FAISS IndexFlatIP cosine clustering (threshold=0.75)
  4. Union-find connected components
  5. Split large clusters via faiss.Kmeans
  6. Source diversity: flag clusters with ≥2 distinct books as "convergent"
  7. Write clusters + singletons to checkpoint JSONL

Why this stage is critical (D2094):
  - Clustering RAW segments preserves verbatim text for convergent extraction
  - Source diversity filtering prevents echo-chamber clusters (same book, same idea)
  - Only convergent clusters (≥2 books) produce full extraction in Stage 2
  - Ported from proven old project architecture (19,438 verified FBs)

Usage:
    python3 pipeline/stage1_5_embed_cluster.py
    python3 pipeline/stage1_5_embed_cluster.py --threshold 0.80
    python3 pipeline/stage1_5_embed_cluster.py --min-diversity 3
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.ollama_embed import batch_embed
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    S15_EMBED_MODEL,
    S15_FAISS_THRESHOLD,
    S15_MAX_CLUSTER_SIZE,
    S15_MIN_CLUSTER_SIZE,
    S15_MIN_SOURCE_DIVERSITY,
    S15_NEIGHBOR_K,
    STAGE1_5_CHECKPOINT,
    STAGE1_5_SINGLETONS,
    STAGE1_CHECKPOINT,
)
from pipeline.stamp import get_pipeline_commit, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
FAISS_SEED: int = 42
BATCH_SIZE: int = 64  # Segments per embedding batch


def load_segments() -> list[dict]:
    """Load segments from Stage 1.3 prefilter or Stage 1 fallback.

    Returns:
        List of segment dicts with at minimum: segment_id, text, source_book.
    """
    # Try Stage 1.3 prefilter first
    prefilter_path = CHECKPOINT_DIR / "stage1_3_filtered.jsonl"
    if prefilter_path.exists():
        print(f"   📂 Loading from Stage 1.3 prefilter: {prefilter_path}")
        checkpoint = prefilter_path
    elif STAGE1_CHECKPOINT.exists():
        print(f"   📂 Loading from Stage 1: {STAGE1_CHECKPOINT}")
        checkpoint = STAGE1_CHECKPOINT
    else:
        print("❌ No segments found. Run stage1_chunk.py (and stage1_3_prefilter.py) first.")
        sys.exit(1)

    segments: list[dict] = []
    with open(checkpoint) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            seg = json.loads(line)
            text = seg.get("text", "").strip()
            if not text or len(text) < 20:
                continue
            segments.append(seg)

    return segments


def embed_segments(segments: list[dict], model: str = S15_EMBED_MODEL) -> np.ndarray:
    """Embed segment text via bge-m3 (Ollama).

    Args:
        segments: List of segment dicts with 'text' field.
        model: Ollama embedding model name.

    Returns:
        Float32 array of shape (n_segments, 1024), normalized to unit vectors.
    """
    texts: list[str] = [seg["text"][:1500] for seg in segments]
    total: int = len(texts)

    print(f"   🧠 Embedding {total} segments via {model}...")
    start: float = time.time()

    all_embeddings: list[np.ndarray] = []
    for i in range(0, total, BATCH_SIZE):
        batch: list[str] = texts[i : i + BATCH_SIZE]
        raw: list[list[float]] = batch_embed(batch, model=model)
        for emb in raw:
            if len(emb) > 0:
                all_embeddings.append(np.array(emb, dtype=np.float32))
        if (i // BATCH_SIZE) % 10 == 0:
            print(f"      ... {min(i + BATCH_SIZE, total)}/{total}")

    elapsed: float = time.time() - start
    print(f"      → {len(all_embeddings)} embeddings in {elapsed:.1f}s")

    if len(all_embeddings) < len(segments):
        print(f"   ⚠️  {len(segments) - len(all_embeddings)} segments dropped (embedding failure)")

    embeddings: np.ndarray = np.array(all_embeddings, dtype=np.float32)
    # Normalize to unit vectors for cosine similarity via inner product
    norms: np.ndarray = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    embeddings = embeddings / norms

    return embeddings


def faiss_cluster(
    embeddings: np.ndarray,
    threshold: float,
    min_size: int,
    max_size: int,
    neighbor_k: int,
) -> tuple[dict, dict, dict]:
    """FAISS cosine clustering with reciprocal nearest-neighbor (R-NN) edges.

    R-NN eliminates the transitive ''bridge effect'' that union-find suffers from.
    Two points are connected ONLY if they are MUTUALLY in each other's top-k
    neighbors above the similarity threshold. This prevents a single weak
    bridge from merging two otherwise distinct clusters (BUG-049 root cause).

    Args:
        embeddings: Normalized float32 array (n, dim).
        threshold: Cosine similarity threshold for R-NN edge.
        min_size: Minimum members per cluster (smaller → singletons).
        max_size: Maximum before k-means split.
        neighbor_k: FAISS nearest neighbors to search.

    Returns:
        Tuple of (multi_member: dict, singletons: dict, cohesion: dict).
    """
    n: int = embeddings.shape[0]
    dim: int = embeddings.shape[1]

    # Build FAISS index
    print(f"   📐 Building FAISS IndexFlatIP ({n} vectors, {dim}d)...")
    index: faiss.IndexFlatIP = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Search nearest neighbors
    k: int = min(neighbor_k, n)
    print(f"   🔍 Searching {k} nearest neighbors...")
    sims, neigh = index.search(embeddings, k)

    # ── Reciprocal Nearest-Neighbor clustering (fixes BUG-049) ──────────
    print(f"   🔗 R-NN clustering (reciprocal cos ≥ {threshold})...")
    parent: list[int] = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Build neighbor sets for O(1) reciprocity check
    neighbor_sets: list[set[int]] = []
    for i in range(n):
        nbrs: set[int] = set()
        for j, s in zip(neigh[i], sims[i], strict=False):
            if j != i and s >= threshold:
                nbrs.add(int(j))
        neighbor_sets.append(nbrs)

    # Only union reciprocal edges
    reciprocal_edges: int = 0
    total_edges: int = 0
    for i in range(n):
        for j in neighbor_sets[i]:
            total_edges += 1
            if i in neighbor_sets[j]:  # j is also neighbor of i
                union(i, j)
                reciprocal_edges += 1

    reciprocity: float = (reciprocal_edges / total_edges * 100) if total_edges > 0 else 0.0
    print(f"      {reciprocal_edges}/{total_edges} edges reciprocal ({reciprocity:.0f}%)")

    # Collect clusters
    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)

    # Split by size
    multi: dict[str, list[int]] = {}
    single: dict[str, list[int]] = {}
    large_split_count: int = 0

    for cid, idxs in clusters.items():
        if len(idxs) < min_size:
            single[str(cid)] = idxs
        elif len(idxs) <= max_size:
            multi[str(cid)] = idxs
        else:
            # Split large cluster via faiss.Kmeans (preserves semantic boundaries)
            try:
                n_sub: int = max(2, (len(idxs) + max_size - 1) // max_size)
                sub_emb: np.ndarray = embeddings[idxs]
                kmeans = faiss.Kmeans(d=dim, k=n_sub, niter=20, seed=FAISS_SEED)
                kmeans.train(sub_emb)
                _, labels = kmeans.index.search(sub_emb, 1)
                labels = labels.flatten()
                for sub_idx in range(n_sub):
                    member_mask: np.ndarray = labels == sub_idx
                    member_idxs: list[int] = [idxs[i] for i in range(len(idxs)) if member_mask[i]]
                    if len(member_idxs) >= min_size:
                        sub_cid: str = f"{cid}_s{sub_idx}"
                        multi[sub_cid] = member_idxs
                        large_split_count += 1
            except Exception as e:
                # Fallback: sequential split
                print(f"   ⚠️  K-means split failed for cluster {cid}: {e}")
                for chunk_i in range(0, len(idxs), max_size):
                    chunk: list[int] = idxs[chunk_i : chunk_i + max_size]
                    sub_cid = f"{cid}_split_{chunk_i // max_size}"
                    multi[sub_cid] = chunk
                    large_split_count += 1

    # Compute cohesion per cluster
    cohesion: dict[str, float] = {}
    for cid, idxs in multi.items():
        member_embs: np.ndarray = embeddings[idxs]
        centroid: np.ndarray = member_embs.mean(axis=0)
        c_norm: np.ndarray = centroid / (np.linalg.norm(centroid) + 1e-10)
        e_norm: np.ndarray = member_embs / (np.linalg.norm(member_embs, axis=1, keepdims=True) + 1e-10)
        sims_arr: np.ndarray = e_norm @ c_norm
        cohesion[cid] = float(sims_arr.mean())

    if large_split_count > 0:
        print(f"   📦 {large_split_count} sub-clusters created from large cluster splits")

    return multi, single, cohesion


def build_clusters(
    segments: list[dict],
    multi: dict[str, list[int]],
    singles: dict[str, list[int]],
    cohesion: dict[str, float],
    min_diversity: int,
) -> tuple[list[dict], list[dict]]:
    """Build cluster output records with source diversity scoring.

    Args:
        segments: Original segment dicts.
        multi: Multi-member cluster indices.
        singles: Singleton cluster indices.
        cohesion: Cluster cohesion scores.
        min_diversity: Minimum distinct books for convergent flag.

    Returns:
        Tuple of (cluster_records, singleton_records).
    """
    pipeline_commit: str = get_pipeline_commit()
    cluster_records: list[dict] = []
    singleton_records: list[dict] = []

    for cid, idxs in multi.items():
        seg_ids: list[str] = [segments[i].get("segment_id", f"seg_{i}") for i in idxs]
        books: set[str] = {segments[i].get("source_book", "unknown") for i in idxs}
        book_count: int = len(books)

        cluster: dict = {
            "cluster_id": f"cluster_{cid}",
            "segment_ids": seg_ids,
            "source_books": sorted(books),
            "source_diversity": book_count,
            "is_convergent": book_count >= min_diversity,
            "is_noise": False,
            "cohesion": round(cohesion.get(cid, 0.0), 4),
            "size": len(idxs),
        }
        cluster = stamp_record(cluster, gen_model=S15_EMBED_MODEL)
        cluster["pipeline_commit"] = pipeline_commit
        cluster_records.append(cluster)

    for cid, idxs in singles.items():
        seg_ids = [segments[i].get("segment_id", f"seg_{i}") for i in idxs]
        books = {segments[i].get("source_book", "unknown") for i in idxs}

        singleton: dict = {
            "cluster_id": f"singleton_{cid}",
            "segment_ids": seg_ids,
            "source_books": sorted(books),
            "source_diversity": len(books),
            "is_convergent": False,
            "is_noise": True,
            "cohesion": 1.0,
            "size": len(idxs),
        }
        singleton = stamp_record(singleton, gen_model=S15_EMBED_MODEL)
        singleton["pipeline_commit"] = pipeline_commit
        singleton_records.append(singleton)

    return cluster_records, singleton_records


def run_stage1_5(
    threshold: float = S15_FAISS_THRESHOLD,
    min_diversity: int = S15_MIN_SOURCE_DIVERSITY,
) -> None:
    """Run Stage 1.5: Embed segments + FAISS cosine clustering.

    Args:
        threshold: Cosine similarity threshold for cluster membership.
        min_diversity: Minimum distinct books for convergent flag.
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    segments: list[dict] = load_segments()
    if not segments:
        print("❌ No segments loaded.")
        sys.exit(1)

    print(f"🔬 Stage 1.5: FAISS Cluster — {len(segments)} segments")
    print(f"   Threshold: {threshold} | Min cluster: {S15_MIN_CLUSTER_SIZE} | Max: {S15_MAX_CLUSTER_SIZE}")
    print(f"   Min source diversity: {min_diversity}")
    print(f"{'='*60}")

    # Embed
    start: float = time.time()
    embeddings: np.ndarray = embed_segments(segments)
    embed_time: float = time.time() - start

    # Cluster
    start = time.time()
    multi, singles, cohesion = faiss_cluster(
        embeddings, threshold, S15_MIN_CLUSTER_SIZE, S15_MAX_CLUSTER_SIZE, S15_NEIGHBOR_K
    )
    cluster_time: float = time.time() - start

    # Build output
    cluster_records, singleton_records = build_clusters(
        segments, multi, singles, cohesion, min_diversity
    )

    # Stats
    n_convergent: int = sum(1 for c in cluster_records if c["is_convergent"])
    n_single_source: int = len(cluster_records) - n_convergent
    sizes: list[int] = [c["size"] for c in cluster_records]

    print(f"\n{'='*60}")
    print("📊 CLUSTERING RESULTS")
    print(f"   Total clusters:         {len(cluster_records)}")
    print(f"   ├─ Convergent (≥{min_diversity} books): {n_convergent}")
    print(f"   ├─ Single-source:       {n_single_source}")
    print(f"   └─ Singletons (noise):  {len(singleton_records)}")
    if sizes:
        print(f"   Cluster size: mean={np.mean(sizes):.1f}, min={min(sizes)}, max={max(sizes)}")
    if cohesion:
        vals: list[float] = list(cohesion.values())
        print(f"   Cohesion: mean={np.mean(vals):.3f}, min={min(vals):.3f}, max={max(vals):.3f}")
    print(f"   Embed time:  {embed_time:.1f}s")
    print(f"   Cluster time: {cluster_time:.1f}s")

    # Write checkpoints
    safe_write(
        STAGE1_5_CHECKPOINT,
        "\n".join(json.dumps(c, ensure_ascii=False) for c in cluster_records) + "\n",
    )
    if singleton_records:
        safe_write(
            STAGE1_5_SINGLETONS,
            "\n".join(json.dumps(s, ensure_ascii=False) for s in singleton_records) + "\n",
        )

    print(f"\n📋 Clusters:     {STAGE1_5_CHECKPOINT}")
    if singleton_records:
        print(f"📋 Singletons:   {STAGE1_5_SINGLETONS}")

    # Gate check
    if n_convergent == 0:
        print(f"\n⚠️  WARNING: No convergent clusters (≥{min_diversity} books).")
        print(f"   Threshold {threshold} may be too strict or source diversity too low.")


def main() -> None:
    """CLI entry point."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Stage 1.5: Embed segments + FAISS cosine clustering"
    )
    parser.add_argument(
        "--threshold", type=float, default=S15_FAISS_THRESHOLD,
        help=f"Cosine similarity threshold (default: {S15_FAISS_THRESHOLD})"
    )
    parser.add_argument(
        "--min-diversity", type=int, default=S15_MIN_SOURCE_DIVERSITY,
        help=f"Minimum distinct books for convergent flag (default: {S15_MIN_SOURCE_DIVERSITY})"
    )
    args: argparse.Namespace = parser.parse_args()

    run_stage1_5(threshold=args.threshold, min_diversity=args.min_diversity)


if __name__ == "__main__":
    main()
