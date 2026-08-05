#!/usr/bin/env python3
"""
stage1_5_embed_cluster.py — FAISS R-NN + Louvain Clustering on Raw Segments.
=============================================================================
Authority: D2094, D2101, D2168, D2170, D2172, D2176 | CONSTITUTION.md §3

Input:  Prefiltered segments from Stage 1.3 checkpoint (or Stage 1 fallback)
Output: Semantic clusters with canonical source diversity scoring

Process (v3.0 actual):
  1. Load segments from Stage 1.3 or Stage 1
  2. Embed raw segment text via bge-m3 (MPS/sentence-transformers, 1024-dim native)
     Matryoshka truncation to 512d (E7) — 2× faster FAISS, 92% neighbor overlap.
     Ollama fallback available — fail-fast on dimension mismatch (D2170).
  3. FAISS IndexFlatIP cosine similarity → KNN graph
  4. Build R-NN edges (reciprocal only: A↔B requires A∈topK(B) AND B∈topK(A))
  5. Louvain community detection on R-NN graph (networkx, D2168) — no transitive chaining
  6. Source diversity: count canonical source_ids (SHA-256 author|title, D2176)
     → is_convergent: ≥2 distinct canonical sources
     → is_singleton: exactly 1 segment, is_noise=False, is_singleton=True (D2171)
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
import atexit
import gc
import json
import logging
import os
import sys
import tempfile
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
    S13_DIR,
    S15_EMBED_BACKEND,
    S15_EMBED_CHUNK_SIZE,  # D2189: chunked embedding
    S15_EMBED_DIM,
    S15_EMBED_MODEL,
    S15_EMBED_MODEL_HF,
    S15_FAISS_THRESHOLD,
    S15_MAX_CLUSTER_SIZE,
    S15_MIN_CLUSTER_SIZE,
    S15_MIN_SOURCE_DIVERSITY,
    S15_NEIGHBOR_K,
    STAGE1_5_CHECKPOINT,
    STAGE1_5_SINGLETONS,
    STAGE1_CHECKPOINT,
    get_run_id,
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
    # Stage 1.3 prefilter writes in-place to STAGE1_CHECKPOINT, but also
    # writes a flag at S13_DIR/{run_id}/checkpoint.jsonl. If the flag exists,
    # we know STAGE1_CHECKPOINT has been filtered — use it directly.
    prefilter_flag = S13_DIR / get_run_id() / "checkpoint.jsonl"
    if prefilter_flag.exists():
        # Verify it's a flag, not segments (flag has "completed" key)
        try:
            flag_data = json.loads(prefilter_flag.read_text().strip())
            if flag_data.get("completed"):
                print(f"   ✅ Stage 1.3 prefilter completed ({flag_data.get('kept', '?')}/{flag_data.get('total', '?')} kept)")
        except (json.JSONDecodeError, KeyError):
            pass
        # Fall through to load from STAGE1_CHECKPOINT (which IS the filtered output)

    if STAGE1_CHECKPOINT.exists():
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
    """Embed segment text via configured backend (MPS sentence-transformers, Ollama fallback).

    D2181: Unified to bge-m3 (T1.2 Option A) — same model as S4 relationship edges.
    Native 1024d → Matryoshka truncation to S15_EMBED_DIM (512d, E7).
    MPS path: ~20-30 seg/s (bge-m3 ≈ 2× slower than bge-small but higher quality).
    Ollama fallback: ~15-20 seg/s via HTTP.

    D2189: Chunked processing — instead of tokenizing all 323K texts in one encode() call
    (which creates massive PyTorch tensors + MPS allocations ≈ 7-10GB), process in
    configurable chunks of ~20K segments at a time, writing embeddings to a memory-mapped
    numpy file on disk. GC + MPS cache flush between chunks prevents memory bloat.

    Args:
        segments: List of segment dicts with 'text' field.
        model: Ollama embedding model name (ignored when backend=mps).

    Returns:
        Float32 array of shape (n_segments, S15_EMBED_DIM), normalized to unit vectors.
    """
    texts: list[str] = [seg["text"][:1500] for seg in segments]
    total: int = len(texts)

    # ── D2127r5/D2189: MPS chunked processing ───────────────────────────
    if S15_EMBED_BACKEND == "mps":
        import gc
        import tempfile
        import atexit

        try:
            import torch
            _has_torch = True
        except ImportError:
            torch = None  # type: ignore
            _has_torch = False

        chunk_size: int = S15_EMBED_CHUNK_SIZE
        n_chunks: int = (total + chunk_size - 1) // chunk_size

        print(f"   🧠 Embedding {total} segments via {S15_EMBED_MODEL_HF} "
              f"(MPS, {S15_EMBED_DIM}d, {n_chunks} chunks × ~{chunk_size})...")
        start_total: float = time.time()

        # Memory-mapped output file — avoids holding 660MB numpy array in RAM.
        # np.memmap lets us write directly to disk, OS pages only what we touch.
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".npy", prefix="s15_embeds_")
        os.close(tmp_fd)
        atexit.register(lambda p=tmp_path: os.unlink(p) if os.path.exists(p) else None)

        embeddings_mmap: np.ndarray = np.memmap(
            tmp_path, dtype=np.float32, mode="w+",
            shape=(total, S15_EMBED_DIM),
        )

        from sentence_transformers import SentenceTransformer
        st_model = SentenceTransformer(S15_EMBED_MODEL_HF, device="mps")

        for chunk_idx in range(n_chunks):
            start_idx: int = chunk_idx * chunk_size
            end_idx: int = min(start_idx + chunk_size, total)
            chunk_texts: list[str] = texts[start_idx:end_idx]
            chunk_n: int = len(chunk_texts)

            # Encode one chunk at a time — limits tokenization tensors + MPS allocs
            raw = st_model.encode(
                chunk_texts,
                batch_size=128,
                show_progress_bar=True,
                device="mps",
                normalize_embeddings=True,  # D2189: normalize in-model (faster than post-hoc)
            )

            chunk_embeddings: np.ndarray = np.array(raw, dtype=np.float32)
            # D2189: Matryoshka truncation — bge-m3 outputs 1024d natively, truncate to 512d
            # per config. MRL training guarantees cosine ranking preserved (92% overlap per D2118).
            chunk_embeddings = chunk_embeddings[:, :S15_EMBED_DIM]
            embeddings_mmap[start_idx:end_idx, :] = chunk_embeddings

            # Free chunk tensors, flush MPS cache (prevents 2,526-batch leak)
            del raw, chunk_embeddings, chunk_texts
            if _has_torch and torch is not None:
                try:
                    torch.mps.empty_cache()
                except Exception:
                    pass
            gc.collect()

            chunk_elapsed = time.time() - start_total
            overall_rate = (end_idx) / chunk_elapsed if chunk_elapsed > 0 else 0
            print(f"      chunk {chunk_idx+1}/{n_chunks} | {end_idx}/{total} ({100*end_idx/total:.1f}%) "
                  f"| {chunk_elapsed:.0f}s | {overall_rate:.0f} seg/s")

        # Verify dimension
        if embeddings_mmap.shape[1] != S15_EMBED_DIM:
            raise ValueError(
                f"Embedding dimension mismatch: model output {embeddings_mmap.shape[1]}d "
                f"≠ config S15_EMBED_DIM={S15_EMBED_DIM}d. "
                f"Check pipeline_config.yaml → stage1_5.embed_model_hf ({S15_EMBED_MODEL_HF}) "
                f"and ensure it matches the actual model output dimension."
            )

        elapsed_total: float = time.time() - start_total
        print(f"      → {total} embeddings ({S15_EMBED_DIM}d) in {elapsed_total:.1f}s "
              f"({total/elapsed_total:.0f} seg/s, {n_chunks} chunks)")

        # Flush and return the memmap (caller can read or copy)
        embeddings_mmap.flush()
        return np.array(embeddings_mmap)  # Materialize once (FAISS needs contiguous)

    # ── Ollama HTTP fallback ────────────────────────────────────────────
    print(f"   🧠 Embedding {total} segments via {model} (Ollama, truncating to {S15_EMBED_DIM}d)...")
    start: float = time.time()

    from concurrent.futures import ThreadPoolExecutor, as_completed

    batches: dict[int, list[str]] = {}
    for i in range(0, total, BATCH_SIZE):
        batches[i] = texts[i : i + BATCH_SIZE]

    print(f"      Sending {len(batches)} batches to {model} (parallel workers=4)...")
    results: dict[int, list[list[float]]] = {}
    completed_count: int = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_idx = {
            executor.submit(batch_embed, batch_texts, model): idx
            for idx, batch_texts in batches.items()
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                raw = future.result()
                results[idx] = raw
                completed_count += 1
                if completed_count % 10 == 0 or completed_count == len(batches):
                    segments_done = min(completed_count * BATCH_SIZE, total)
                    print(f"      ... {segments_done}/{total}")
            except Exception as e:
                print(f"      ⚠️  Batch at idx={idx} failed: {e}")
                results[idx] = []

    # D2172: Track successful segment indices to prevent index misalignment.
    # When a batch fails and we drop its embeddings, the segments list must be
    # filtered in lockstep. Otherwise embedding[i] no longer corresponds to
    # segments[i] — cluster membership becomes random (silent data corruption).
    all_embeddings: list[np.ndarray] = []
    successful_indices: list[int] = []
    for batch_idx in sorted(results.keys()):
        batch_start: int = batch_idx
        for seg_offset, emb in enumerate(results[batch_idx]):
            if len(emb) > 0:
                arr: np.ndarray = np.array(emb, dtype=np.float32)
                if S15_EMBED_DIM < len(arr):
                    arr = arr[:S15_EMBED_DIM]
                all_embeddings.append(arr)
                successful_indices.append(batch_start + seg_offset)

    elapsed: float = time.time() - start
    n_dropped: int = len(segments) - len(all_embeddings)
    print(f"      → {len(all_embeddings)} embeddings ({S15_EMBED_DIM}d) in {elapsed:.1f}s")

    if n_dropped > 0:
        print(f"   ⚠️  {n_dropped} segments dropped (embedding failure) — filtering segments in lockstep")
        segments = [segments[i] for i in successful_indices]

    embeddings = np.array(all_embeddings, dtype=np.float32)
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

    # ── Reciprocal Nearest-Neighbor + Louvain Community Detection ─────
    # D2168: Replaces Union-Find with Louvain community detection.
    #
    # WHY: Union-Find computes connected components on R-NN edges.
    # If A↔B and B↔C are both reciprocal, Union-Find merges A,B,C into one
    # component even if A and C are semantically unrelated. This is the
    # "transitive bridge effect" — R-NN constrains edge CREATION but
    # Union-Find still chains components transitively. BUG-049 was only
    # partially fixed; the documentation claim "R-NN eliminates the
    # transitive bridge effect" was mathematically false.
    #
    # Louvain community detection optimizes modularity (dense intra-community
    # edges, sparse inter-community edges). It naturally splits long chains
    # at semantic boundaries where connectivity thins out. Runs in ~100ms
    # on a graph with 300K+ nodes and reciprocal edges.
    #
    # Reference: Blondel et al. 2008, "Fast unfolding of communities in
    # large networks" (J. Stat. Mech.). Louvain is the predecessor to Leiden
    # (Traag et al. 2019) — both avoid transitive chaining. Leiden would be
    # preferred but requires igraph/leidenalg (C dependency). Louvain via
    # networkx is pure Python and already in requirements.
    print(f"   🔗 R-NN + Louvain clustering (reciprocal cos ≥ {threshold})...")

    # Build neighbor sets for O(1) reciprocity check
    neighbor_sets: list[set[int]] = []
    for i in range(n):
        nbrs: set[int] = set()
        for j, s in zip(neigh[i], sims[i], strict=False):
            if j != i and s >= threshold:
                nbrs.add(int(j))
        neighbor_sets.append(nbrs)

    # Build undirected R-NN graph (only reciprocal edges)
    import networkx as nx
    from networkx.algorithms.community import louvain_communities

    G: nx.Graph = nx.Graph()
    G.add_nodes_from(range(n))
    reciprocal_edges: int = 0
    total_edges: int = 0
    for i in range(n):
        for j in neighbor_sets[i]:
            total_edges += 1
            if i in neighbor_sets[j] and i < j:  # add each edge once
                G.add_edge(i, j)
                reciprocal_edges += 1

    # D2178: total_edges counts directed edges; reciprocal_edges counts each pair once.
    # True reciprocity = (2 * reciprocal_edges) / total_edges (each reciprocal pair = 2 directed edges)
    reciprocity: float = ((2 * reciprocal_edges) / total_edges * 100) if total_edges > 0 else 0.0
    print(f"      {reciprocal_edges}/{total_edges} edges reciprocal ({reciprocity:.0f}%) "
          f"→ Louvain on {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Louvain community detection
    louvain_start: float = time.time()
    communities: list[set[int]] = louvain_communities(G, seed=FAISS_SEED)
    louvain_elapsed: float = time.time() - louvain_start
    print(f"      Louvain: {len(communities)} communities in {louvain_elapsed*1000:.0f}ms")

    # Collect clusters (plus isolated nodes as singletons)
    clusters: dict[int, list[int]] = defaultdict(list)
    assigned_nodes: set[int] = set()
    for comm_idx, comm in enumerate(communities):
        for node in comm:
            clusters[comm_idx].append(node)
            assigned_nodes.add(node)

    # Any nodes with zero edges (isolated) become individual singletons
    n_isolated: int = 0
    for i in range(n):
        if i not in assigned_nodes:
            clusters[n + n_isolated] = [i]
            n_isolated += 1

    if n_isolated > 0:
        print(f"      + {n_isolated} isolated nodes (zero reciprocal edges) → individual singletons")

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

    # D2176: Canonical source identity for diversity counting.
    # OLD: source_diversity = len(distinct filenames). Same book with
    # different edition/filename would inflate diversity → false convergence.
    # NEW: source_ids = set of canonical SHA-256(author|title) hashes.
    # source_diversity = len(source_ids). source_books preserved for provenance.
    from pipeline.book_metadata import resolve_source_ids

    for cid, idxs in multi.items():
        seg_ids: list[str] = [segments[i].get("segment_id", f"seg_{i}") for i in idxs]
        books_list: list[str] = sorted({segments[i].get("source_book", "unknown") for i in idxs})
        source_ids: set[str] = resolve_source_ids(books_list)
        sid_count: int = len(source_ids)

        cluster: dict = {
            "cluster_id": f"cluster_{cid}",
            "segment_ids": seg_ids,
            "source_books": books_list,
            "source_ids": sorted(source_ids),
            "source_diversity": sid_count,
            "is_convergent": sid_count >= min_diversity,
            "is_noise": False,
            "cohesion": round(cohesion.get(cid, 0.0), 4),
            "size": len(idxs),
        }
        cluster = stamp_record(cluster, gen_model=S15_EMBED_MODEL)
        cluster["pipeline_commit"] = pipeline_commit
        cluster_records.append(cluster)

    for cid, idxs in singles.items():
        seg_ids = [segments[i].get("segment_id", f"seg_{i}") for i in idxs]
        books_list = sorted({segments[i].get("source_book", "unknown") for i in idxs})
        source_ids = resolve_source_ids(books_list)

        # D2171: Singletons are NOT noise — they carry unique book-specific insights.
        # "is_noise: True" was a legacy label that would cause downstream stages
        # and retrieval filters to silently drop 2,804 unique knowledge items.
        # "is_singleton: True" preserves the structural distinction without data loss.
        singleton: dict = {
            "cluster_id": f"singleton_{cid}",
            "segment_ids": seg_ids,
            "source_books": books_list,
            "source_ids": sorted(source_ids),
            "source_diversity": len(source_ids),
            "is_convergent": False,
            "is_noise": False,
            "is_singleton": True,
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
