#!/usr/bin/env python3
"""
stage3_cluster.py — Embed principles + HDBSCAN semantic clustering.
===================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 3), D2081

Input:  Principles from Stage 2 checkpoint
Output: Semantic clusters with centroids, noise preserved

Process:
  1. Embed principles via bge-m3 (Ollama, 1024-dim)
  2. Dimensionality reduction via UMAP (configurable params, cosine metric)
  3. HDBSCAN density-based clustering
  4. Centroid extraction (normalized for cosine space — D2081 fix)
  5. Noise points preserved as singletons (D2081 fix — was: silently discarded)

D2081 fixes:
  - UMAP min_dist = 0.1 (was 0.0 — collapsed clusters)
  - Noise points preserved → cluster_noise.jsonl (was: continue/silent discard)
  - Centroid normalized for cosine similarity (was: raw dot product)

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

from pipeline.io_guard import safe_write
from pipeline.ollama_embed import batch_embed
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    EMBED_MODEL,
    HDBSCAN_MIN_CLUSTER_SIZE,
    S3_ALLOW_SINGLE_CLUSTER,
    S3_KEEP_NOISE,
    S3_NOISE_OUTPUT,
    S3_NORMALIZE_CENTROID,
    S3_UMAP_METRIC,
    S3_UMAP_MIN_DIST,
    S3_UMAP_N_COMPONENTS,
    S3_UMAP_N_NEIGHBORS,
    STAGE2_CHECKPOINT,
    STAGE3_CHECKPOINT,
)
from pipeline.stamp import get_pipeline_commit, stamp_record


def load_principles() -> list[dict]:
    """Load principles from Stage 2 checkpoint. Only returns 'principle' type —
    non-FB types (PT/PI/GE/TI) are routed directly to staging by S2 type-aware router.

    D2080: Non-FB types written to stage2_non_fb.jsonl, bypass S3 entirely.
    """
    if not STAGE2_CHECKPOINT.exists():
        print("❌ Stage 2 checkpoint not found. Run stage2_extract.py first.")
        sys.exit(1)

    principles = []
    skipped_types: dict[str, int] = {}
    with open(STAGE2_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                p = json.loads(line)
                ct = p.get("content_type") or p.get("route", "principle")
                if ct in ("principle", "FB", "fb"):
                    principles.append(p)
                else:
                    skipped_types[ct] = skipped_types.get(ct, 0) + 1

    if skipped_types:
        print(f"   ℹ️  Skipped non-FB types (routed to staging): {skipped_types}")

    return principles


def reduce_dimensions(
    embeddings: np.ndarray,
    n_dims: int = S3_UMAP_N_COMPONENTS,
    n_neighbors: int = S3_UMAP_N_NEIGHBORS,
    min_dist: float = S3_UMAP_MIN_DIST,
    metric: str = S3_UMAP_METRIC,
) -> np.ndarray:
    """Reduce dimensions via UMAP. Preserves non-linear structure.

    D2081 fix: min_dist defaults to 0.1 (was 0.0).
    """
    import umap

    reducer = umap.UMAP(
        n_neighbors=min(n_neighbors, len(embeddings) - 1),
        n_components=n_dims,
        min_dist=min_dist,
        metric=metric,
        random_state=42,
    )
    reduced = reducer.fit_transform(embeddings)
    print(
        f"   UMAP: {embeddings.shape[1]} → {reduced.shape[1]} dims "
        f"(cosine, neighbors={n_neighbors}, min_dist={min_dist})"
    )
    return reduced


def cluster_embeddings(
    embeddings: np.ndarray,
    min_cluster_size: int = HDBSCAN_MIN_CLUSTER_SIZE,
    allow_single_cluster: bool = S3_ALLOW_SINGLE_CLUSTER,
) -> np.ndarray:
    """Cluster embeddings using HDBSCAN.

    Returns: cluster labels array (noise = -1).
    """
    from hdbscan import HDBSCAN

    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        allow_single_cluster=allow_single_cluster,
        metric="euclidean",  # UMAP output is in Euclidean space after reduction
    )
    labels = clusterer.fit_predict(embeddings)
    return labels


def find_centroid(member_embeddings: np.ndarray, normalize: bool = S3_NORMALIZE_CENTROID) -> int:
    """Find the centroid index — the principle closest to the cluster mean.

    D2081 fix: normalize vectors before computing centroid for cosine space.
    Previously used raw dot product which is inappropriate for cosine metric.
    """
    if len(member_embeddings) == 0:
        return 0

    if normalize and len(member_embeddings) > 0:
        # Normalize to unit vectors for cosine similarity
        norms = np.linalg.norm(member_embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # Avoid division by zero
        normalized = member_embeddings / norms
        mean_vec = np.mean(normalized, axis=0)
        # Cosine similarity: dot product of normalized vectors
        similarities = np.dot(normalized, mean_vec)
        centroid_idx = int(np.argmax(similarities))
    else:
        # Legacy: raw dot product (euclidean centroid)
        mean_vec = np.mean(member_embeddings, axis=0)
        similarities = np.dot(member_embeddings, mean_vec)
        centroid_idx = int(np.argmax(similarities))

    return centroid_idx


def run_stage3(min_cluster_size: int = HDBSCAN_MIN_CLUSTER_SIZE, keep_noise: bool = S3_KEEP_NOISE):
    """Run Stage 3: Cluster principles.

    Args:
        min_cluster_size: Minimum cluster size for HDBSCAN.
        keep_noise: If True, preserve noise points as singletons (D2081 fix).
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    principles = load_principles()
    if not principles:
        print("❌ No principles found. Run stage2_extract.py first.")
        sys.exit(1)

    print(f"🧩 Stage 3: Semantic Clustering — {len(principles)} principles")
    print(f"   Embedding model: {EMBED_MODEL} | HDBSCAN min_cluster={min_cluster_size}")
    print(f"   UMAP min_dist={S3_UMAP_MIN_DIST} | Keep noise: {keep_noise}")
    print(f"{'=' * 60}")

    # Embed all principles
    print(f"   Embedding {len(principles)} principles...", end=" ")
    start = time.time()
    # D2094: Support both old (principle_text) and v3.0 (definition) schemas
    texts = [p.get("definition") or p["principle_text"] for p in principles]
    raw_embeddings = batch_embed(texts, model=EMBED_MODEL)

    # Filter out failed embeddings
    valid_indices = [i for i, e in enumerate(raw_embeddings) if len(e) > 0]
    embeddings = np.array([raw_embeddings[i] for i in valid_indices])
    valid_principles = [principles[i] for i in valid_indices]
    elapsed = time.time() - start
    print(f"{len(embeddings)} valid embeddings ({elapsed:.1f}s)")
    print(f"   ⚠️  {len(principles) - len(valid_principles)} principles dropped (embedding failure)")

    if len(embeddings) < 5:
        print("❌ Too few valid embeddings to cluster.")
        sys.exit(1)

    # ── BUG-048: Bypass HDBSCAN for small FB counts ─────────────────────
    # When FB count < min_cluster_size, HDBSCAN produces 0 clusters (all noise).
    # In v3.0 cluster-before-extract, Stage 2 already produces final FBs —
    # Stage 3's role is semantic dedup, not primary clustering.
    # For small runs: bypass HDBSCAN, treat each FB as its own singleton cluster.
    bypass_hdbscan = len(embeddings) < min_cluster_size
    if bypass_hdbscan:
        print(f"   ⚠️  BUG-048 bypass: {len(embeddings)} FBs < min_cluster_size={min_cluster_size}")
        print("   → Each FB treated as singleton cluster (HDBSCAN skipped)")
        reduced = embeddings  # Skip UMAP — not needed for singleton clusters
        # Fake labels: each embedding is its own cluster
        labels = np.arange(len(embeddings), dtype=np.int32)
    else:
        # Reduce dimensions
        reduced = reduce_dimensions(embeddings)

        # Cluster
        print("   HDBSCAN clustering...", end=" ")
        start = time.time()
        labels = cluster_embeddings(reduced, min_cluster_size=min_cluster_size)
        elapsed = time.time() - start

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())
    if not bypass_hdbscan:
        print(f"{n_clusters} clusters, {n_noise} noise ({elapsed:.1f}s)")
    else:
        print(f"{n_clusters} singleton clusters ({n_noise} noise)")

    # Build cluster output
    clusters = []
    noise_points = []
    pipeline_commit = get_pipeline_commit()

    for cluster_id in range(n_clusters):
        member_indices = [i for i, label in enumerate(labels) if label == cluster_id]
        if not member_indices:
            continue

        member_principles = [valid_principles[i] for i in member_indices]
        member_embs = embeddings[member_indices]

        # Find centroid
        centroid_idx = find_centroid(member_embs)
        centroid_text = (
            member_principles[centroid_idx].get("definition")
            or member_principles[centroid_idx]["principle_text"]
        )

        # Collect source data
        source_segments: list[str] = []
        source_books: set[str] = set()
        for p in member_principles:
            for seg in p.get("source_segments", []):
                source_segments.append(seg)
            for book in p.get("source_books", []):
                source_books.add(book)

        cluster = {
            "cluster_id": f"c{cluster_id:04d}",
            "size": len(member_principles),
            "centroid_text": centroid_text,
            "principle_ids": [p.get("fb_id") or p["principle_id"] for p in member_principles],
            "source_segments": list(set(source_segments)),
            "source_books": sorted(source_books),
            "cohesion": float(
                np.mean([np.dot(reduced[i], reduced[centroid_idx]) for i in member_indices])
            ),
        }
        cluster = stamp_record(cluster, gen_model=EMBED_MODEL)
        cluster["pipeline_commit"] = pipeline_commit
        clusters.append(cluster)

    # ── D2081 fix: Keep noise points ──────────────────────────────────
    if keep_noise:
        noise_indices = [i for i, label in enumerate(labels) if label == -1]
        for idx in noise_indices:
            p = valid_principles[idx]
            noise_point = {
                "principle_id": p.get("fb_id") or p["principle_id"],
                "principle_text": p.get("definition") or p["principle_text"],
                "content_type": p.get("content_type") or p.get("route", "principle"),
                "source_segments": p.get("source_segments", []),
                "source_books": p.get("source_books", []),
                "evidence_type": p.get("evidence_type", "axiomatic"),
                "cluster_label": -1,
                "reason": "noise — did not cluster with any group",
            }
            noise_point = stamp_record(noise_point, gen_model=EMBED_MODEL)
            noise_point["pipeline_commit"] = pipeline_commit
            noise_points.append(noise_point)

        # Write noise to separate file
        if noise_points:
            noise_path = STAGE3_CHECKPOINT.parent / S3_NOISE_OUTPUT
            safe_write(
                noise_path,
                "\n".join(json.dumps(n, ensure_ascii=False) for n in noise_points) + "\n",
            )

    # Write cluster checkpoint
    safe_write(
        STAGE3_CHECKPOINT,
        "\n".join(json.dumps(c, ensure_ascii=False) for c in clusters) + "\n",
    )

    # Summary
    print(f"\n{'=' * 60}")
    print(f"✅ Clusters:              {len(clusters)}")
    print(f"🔊 Noise points preserved: {len(noise_points)}")
    if noise_points:
        noise_path = STAGE3_CHECKPOINT.parent / S3_NOISE_OUTPUT
        print(f"📋 Noise checkpoint:       {noise_path}")
    print(f"📋 Cluster checkpoint:     {STAGE3_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(description="Stage 3: Cluster principles via HDBSCAN")
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=HDBSCAN_MIN_CLUSTER_SIZE,
        help=f"Minimum cluster size (default: {HDBSCAN_MIN_CLUSTER_SIZE})",
    )
    parser.add_argument(
        "--discard-noise",
        action="store_true",
        help="Discard noise points instead of preserving them (legacy behavior)",
    )
    args = parser.parse_args()

    run_stage3(
        min_cluster_size=args.min_cluster_size,
        keep_noise=not args.discard_noise,
    )


if __name__ == "__main__":
    main()
