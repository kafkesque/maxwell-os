#!/usr/bin/env python3
"""
stage3_cluster.py — Embed principles + HDBSCAN semantic clustering.
===================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 3)

Input:  Principles from Stage 2 checkpoint
Output: Clusters with cohesion metrics, checkpoint at stage3_cluster.jsonl

Process:
  1. Embed all principles via Ollama nomic-embed-text
  2. Dimensionality reduction via PCA (50 dims)
  3. HDBSCAN density-based clustering
  4. Compute cohesion = mean pairwise cosine similarity per cluster
  5. Noise points (cluster=-1) are discarded
  6. Write checkpoint

Embedding model: nomic-embed-text (Ollama)
Min cluster size: 3 (from pipeline_paths)

Usage:
    python3 pipeline/stage3_cluster.py
    python3 pipeline/stage3_cluster.py --min-cluster-size 5
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    STAGE2_CHECKPOINT,
    STAGE3_CHECKPOINT,
    CHECKPOINT_DIR,
    EMBED_MODEL,
    HDBSCAN_MIN_CLUSTER_SIZE,
    CLUSTER_MIN_SIZE,
)
from pipeline.stamp import stamp_record, get_pipeline_commit
from pipeline.ollama_embed import batch_embed
from pipeline.io_guard import safe_write

# ── Constants ──────────────────────────────────────────────────────────────
PCA_DIMS = 50  # Reduce to 50 dimensions before clustering
EMBED_BATCH_SIZE = 100  # Texts per Ollama embed call


def load_stage2_principles() -> list[dict]:
    """Load principles from Stage 2 checkpoint."""
    if not STAGE2_CHECKPOINT.exists():
        print("❌ Stage 2 checkpoint not found. Run stage2_extract.py first.")
        sys.exit(1)

    principles = []
    with open(STAGE2_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                principles.append(json.loads(line))
    return principles


def compute_embeddings(principles: list[dict]) -> np.ndarray:
    """Embed all principles via Ollama batch API.

    Returns: (n_principles, 768) float32 array.
    """
    texts = [p["principle_text"] for p in principles]
    print(f"   Embedding {len(texts)} texts via {EMBED_MODEL}...")

    all_embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch_texts = texts[i:i + EMBED_BATCH_SIZE]
        print(f"     Batch {i // EMBED_BATCH_SIZE + 1}/{(len(texts) - 1) // EMBED_BATCH_SIZE + 1} "
              f"({len(batch_texts)} texts)", end=" ")
        start = time.time()
        embs = batch_embed(batch_texts, model=EMBED_MODEL)
        elapsed = time.time() - start
        all_embeddings.extend(embs)
        print(f"({elapsed:.1f}s)")

    return np.array(all_embeddings, dtype=np.float32)


def reduce_dimensions(embeddings: np.ndarray, n_dims: int = PCA_DIMS) -> np.ndarray:
    """Reduce embedding dimensions via PCA."""
    from sklearn.decomposition import PCA

    n_dims = min(n_dims, embeddings.shape[0], embeddings.shape[1])
    pca = PCA(n_components=n_dims, random_state=42)
    reduced = pca.fit_transform(embeddings)
    explained = pca.explained_variance_ratio_.sum()
    print(f"   PCA: {embeddings.shape[1]} → {n_dims} dims "
          f"({explained:.1%} variance retained)")
    return reduced


def cluster_hdbscan(embeddings: np.ndarray, min_cluster_size: int) -> np.ndarray:
    """Cluster embeddings using HDBSCAN.

    Returns: cluster labels array (noise = -1).
    """
    from hdbscan import HDBSCAN

    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=2,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels = clusterer.fit_predict(embeddings)
    return labels


def compute_cohesion(embeddings: np.ndarray, labels: np.ndarray,
                     cluster_id: int) -> float:
    """Compute mean pairwise cosine similarity within a cluster."""
    from sklearn.metrics.pairwise import cosine_similarity

    mask = labels == cluster_id
    if mask.sum() < 2:
        return 1.0
    cluster_embs = embeddings[mask]
    sim_matrix = cosine_similarity(cluster_embs)
    # Mean of upper triangle (exclude diagonal)
    n = sim_matrix.shape[0]
    if n <= 1:
        return 1.0
    triu_indices = np.triu_indices(n, k=1)
    return float(np.mean(sim_matrix[triu_indices]))


def run_stage3(min_cluster_size: int = HDBSCAN_MIN_CLUSTER_SIZE,
               pca_dims: int = PCA_DIMS):
    """Run Stage 3: Cluster principles semantically."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    principles = load_stage2_principles()
    if len(principles) < CLUSTER_MIN_SIZE:
        print(f"❌ Need at least {CLUSTER_MIN_SIZE} principles for clustering. "
              f"Got {len(principles)}.")
        sys.exit(1)

    print(f"🔗 Stage 3: Cluster — {len(principles)} principles")
    print(f"   Min cluster size: {min_cluster_size}")
    print(f"{'='*60}")

    start_total = time.time()

    # 1. Embed
    embeddings = compute_embeddings(principles)

    # 2. Reduce dimensions
    if embeddings.shape[1] > pca_dims:
        reduced = reduce_dimensions(embeddings, pca_dims)
    else:
        reduced = embeddings
        print(f"   Skipping PCA: {embeddings.shape[1]} dims ≤ {pca_dims}")

    # 3. Cluster
    print(f"   HDBSCAN clustering...", end=" ")
    start_cluster = time.time()
    labels = cluster_hdbscan(reduced, min_cluster_size)
    elapsed = time.time() - start_cluster
    unique_labels = set(labels)
    n_clusters = len(unique_labels - {-1})
    n_noise = int((labels == -1).sum())
    print(f"{n_clusters} clusters, {n_noise} noise ({elapsed:.1f}s)")

    # 4. Build cluster records
    clusters = []
    pipeline_commit = get_pipeline_commit()

    for cluster_id in sorted(unique_labels):
        if cluster_id == -1:
            continue  # Skip noise

        mask = labels == cluster_id
        member_indices = np.where(mask)[0]
        member_principles = [principles[i] for i in member_indices]
        principle_ids = [p["principle_id"] for p in member_principles]

        # Find centroid (principle closest to cluster mean)
        cluster_embs = embeddings[mask]
        centroid_idx = np.argmax(np.mean(
            np.dot(cluster_embs, cluster_embs.T), axis=1
        ))
        centroid_text = member_principles[centroid_idx]["principle_text"]

        # Cohesion
        cohesion = compute_cohesion(embeddings, labels, cluster_id)

        # Distinct books
        source_books = set()
        for p in member_principles:
            for sb in p.get("source_books", []):
                source_books.add(sb)

        cluster_rec = {
            "cluster_id": int(cluster_id),
            "principle_ids": principle_ids,
            "centroid_text": centroid_text,
            "cohesion": round(cohesion, 4),
            "size": len(member_indices),
            "distinct_books": len(source_books),
            "source_books": sorted(source_books),
        }
        cluster_rec = stamp_record(cluster_rec, gen_model="hdbscan+nomic")
        cluster_rec["pipeline_commit"] = pipeline_commit
        clusters.append(cluster_rec)

    # Sort by size descending
    clusters.sort(key=lambda c: c["size"], reverse=True)

    # Write checkpoint
    safe_write(
        STAGE3_CHECKPOINT,
        "\n".join(json.dumps(c, ensure_ascii=False) for c in clusters) + "\n",
    )

    total_elapsed = time.time() - start_total

    # Summary
    cohesion_values = [c["cohesion"] for c in clusters]
    avg_cohesion = np.mean(cohesion_values) if cohesion_values else 0
    print(f"\n{'='*60}")
    print(f"✅ Clusters:            {len(clusters)}")
    print(f"🗑️  Noise points:        {n_noise}")
    print(f"📊 Avg cohesion:        {avg_cohesion:.3f}")
    print(f"📊 Cohesion range:      {min(cohesion_values):.3f} - {max(cohesion_values):.3f}" if cohesion_values else "")
    print(f"📊 Largest cluster:     {clusters[0]['size'] if clusters else 0}")
    print(f"⏱️  Total time:          {total_elapsed:.1f}s")
    print(f"📋 Checkpoint:           {STAGE3_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(description="Stage 3: Cluster principles via HDBSCAN")
    parser.add_argument("--min-cluster-size", type=int, default=HDBSCAN_MIN_CLUSTER_SIZE,
                        help=f"Minimum cluster size for HDBSCAN (default: {HDBSCAN_MIN_CLUSTER_SIZE})")
    parser.add_argument("--pca-dims", type=int, default=PCA_DIMS,
                        help=f"PCA dimensions (default: {PCA_DIMS})")
    args = parser.parse_args()

    run_stage3(min_cluster_size=args.min_cluster_size, pca_dims=args.pca_dims)


if __name__ == "__main__":
    main()
