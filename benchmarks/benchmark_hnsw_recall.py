#!/usr/bin/env python3
"""
benchmark_hnsw_recall.py — USearch/HNSW vs IndexFlatIP KNN recall harness.
===========================================================================
Authority: D2280 (Audit1 P0.2 "IndexFlatIP is brute force; HNSW is O(log N)")
           RATIFY-2 gate #1 (D-2724 / D-2725).
Constitution: C12 (config-first), C16 (fail-loud), C17 (type hints),
              C18 (docstrings), C20 (no magic numbers), C6 (crash-safe writes),
              C21 (swappable backends behind one KNN measure).

Purpose: measure whether approximate HNSW neighbor search (FAISS IndexHNSWFlat
and USearch) preserves KNN recall@k against the exact brute-force baseline
(FAISS IndexFlatIP) over the pipeline's own bge-m3 512d embeddings. This is the
ONE unbenchmarked S1.5 lever (D-2722): if HNSW recall@k >= threshold, the S1.5
neighbor search can move from O(N) brute force to O(log N) without drift.

NOT the same as:
  - benchmark_faiss_vs_usearch.py (D2120 clustering benchmark: R-NN quality)
  - pipeline/recall_measure.py (D2307 golden-set principle yield)

Embeddings are computed LIVE via pipeline.embeddings.embed_texts_bge_m3 so the
harness is self-contained (no stale S1.5 embed-checkpoint dependency).

Usage:
    python3 benchmarks/benchmark_hnsw_recall.py
    python3 benchmarks/benchmark_hnsw_recall.py --n 500
    python3 benchmarks/benchmark_hnsw_recall.py --config config/usearch_hnsw_recall.yaml
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

import faiss
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from usearch.index import Index as USearchIndex

from pipeline.embeddings import embed_texts_bge_m3

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "usearch_hnsw_recall.yaml"


# ── Config (C12) ──────────────────────────────────────────────────────────

def load_config(path: Path) -> dict:
    """Load harness config; fail-loud on missing/malformed file (C16)."""
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path} (C16)")
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"config {path} did not parse to a mapping (C16)")
    return cfg


def pipeline_commit() -> str:
    """Resolve the git HEAD commit for R14 provenance stamping (best-effort)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


# ── Data loading ──────────────────────────────────────────────────────────

def load_segments(checkpoint: str, sample_size: int, min_chars: int, seed: int) -> list[str]:
    """Deterministically sample `sample_size` usable segment texts from a checkpoint."""
    cp = PROJECT_ROOT / checkpoint
    if not cp.exists():
        raise FileNotFoundError(f"checkpoint not found: {cp} (C16)")

    texts: list[str] = []
    with open(cp) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            seg = json.loads(line)
            text = str(seg.get("text", "")).strip()
            if len(text) >= min_chars:
                texts.append(text)

    if len(texts) < sample_size:
        raise RuntimeError(
            f"only {len(texts)} usable segments (need {sample_size}); lower sample_size (C16)"
        )
    rng = random.Random(seed)
    return rng.sample(texts, sample_size)


def normalize_rows(embeddings: np.ndarray) -> np.ndarray:
    """L2-normalize rows so inner product == cosine (defensive; embed fn already normalizes)."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return (embeddings / norms).astype(np.float32)


# ── Index construction (C21: swappable backends) ──────────────────────────

def build_flat_ip(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """Exact brute-force inner-product index — the ground-truth baseline."""
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def build_faiss_hnsw(embeddings: np.ndarray, M: int, ef_construction: int, ef_search: int) -> faiss.IndexHNSWFlat:
    """FAISS approximate HNSW index (inner product over normalized vectors)."""
    index = faiss.IndexHNSWFlat(embeddings.shape[1], M, faiss.METRIC_INNER_PRODUCT)
    index.hnsw.efConstruction = ef_construction
    index.hnsw.efSearch = ef_search
    index.add(embeddings)
    return index


def build_usearch(embeddings: np.ndarray, metric: str, connectivity: int,
                  expansion_add: int, expansion_search: int) -> USearchIndex:
    """USearch approximate HNSW index (metric 'ip' over normalized vectors == cosine)."""
    n, dim = embeddings.shape
    index = USearchIndex(ndim=dim, metric=metric, connectivity=connectivity,
                         expansion_add=expansion_add, expansion_search=expansion_search)
    index.add(keys=np.arange(n, dtype=np.int64), vectors=embeddings)
    return index


# ── Neighbor retrieval (self-excluded) ────────────────────────────────────

def exact_neighbors(embeddings: np.ndarray, k_max: int) -> tuple[np.ndarray, float]:
    """Exact top-(k_max) neighbors per query from IndexFlatIP; self excluded. Returns (n, k_max) + build time."""
    t0 = time.perf_counter()
    index = build_flat_ip(embeddings)
    build_s = time.perf_counter() - t0
    _, idxs = index.search(embeddings, k_max + 1)  # +1 to skip self at position 0
    return idxs[:, 1:], build_s


def faiss_hnsw_neighbors(embeddings: np.ndarray, k_max: int, M: int,
                         ef_construction: int, ef_search: int) -> tuple[np.ndarray, float, float]:
    """Top-(k_max) neighbors from FAISS IndexHNSWFlat; self excluded. Returns (n, k_max), build, query time."""
    t0 = time.perf_counter()
    index = build_faiss_hnsw(embeddings, M, ef_construction, ef_search)
    build_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    _, idxs = index.search(embeddings, k_max + 1)
    query_s = time.perf_counter() - t0
    return idxs[:, 1:], build_s, query_s


def usearch_neighbors(embeddings: np.ndarray, k_max: int, metric: str, connectivity: int,
                      expansion_add: int, expansion_search: int) -> tuple[np.ndarray, float, float]:
    """Top-(k_max) neighbors from USearch; self excluded. Returns (n, k_max), build, query time."""
    t0 = time.perf_counter()
    index = build_usearch(embeddings, metric, connectivity, expansion_add, expansion_search)
    build_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    matches = index.search(embeddings, k_max + 1)
    query_s = time.perf_counter() - t0
    keys = np.asarray(matches.keys, dtype=np.int64)  # n × (k_max + 1)
    return keys[:, 1:], build_s, query_s


# ── Recall measurement ────────────────────────────────────────────────────

def recall_at_k(ground_truth: np.ndarray, candidate: np.ndarray, k: int) -> float:
    """Mean overlap of candidate top-k vs exact top-k (self already excluded upstream)."""
    if k > ground_truth.shape[1]:
        raise ValueError(f"k={k} exceeds neighbor depth {ground_truth.shape[1]} (C16)")
    hits = 0
    for i in range(ground_truth.shape[0]):
        hits += len(set(candidate[i, :k].tolist()) & set(ground_truth[i, :k].tolist()))
    return hits / (ground_truth.shape[0] * k)


# ── Orchestration ─────────────────────────────────────────────────────────

def run(cfg: dict, n_override: int | None) -> dict:
    """Embed a sample of segments, build exact + approximate indices, measure recall@k."""
    data_cfg = cfg["data"]
    recall_cfg = cfg["recall"]
    faiss_cfg = cfg["faiss_hnsw"]
    usearch_cfg = cfg["usearch"]

    sample_size = n_override or int(data_cfg["sample_size"])
    ks: list[int] = [int(k) for k in recall_cfg["ks"]]
    k_max = max(ks)

    print(f"📂 Sampling {sample_size} segments from {data_cfg['checkpoint']} …")
    texts = load_segments(
        data_cfg["checkpoint"], sample_size,
        int(data_cfg["min_text_chars"]), int(data_cfg["random_seed"]),
    )

    print("🧮 Embedding live via pipeline.embeddings.embed_texts_bge_m3 (bge-m3 512d) …")
    t0 = time.perf_counter()
    raw = embed_texts_bge_m3(texts)
    embed_s = time.perf_counter() - t0
    embeddings = normalize_rows(raw)
    n, dim = embeddings.shape
    print(f"   {n} × {dim} embeddings in {embed_s:.1f}s ({n / embed_s:.0f} seg/s)")

    # Ground truth: exact brute-force
    print("🎯 Building ground truth (IndexFlatIP, exact) …")
    gt, gt_build_s = exact_neighbors(embeddings, k_max)

    result: dict = {
        "schema_version": 1,
        "gen_model": "BAAI/bge-m3 (ollama, 512d, L2-normalized)",
        "pipeline_commit": pipeline_commit(),
        "n_segments": n,
        "dim": dim,
        "embed_seconds": round(embed_s, 2),
        "embed_rate_seg_per_s": round(n / embed_s, 1),
        "ks": ks,
        "ground_truth": {
            "backend": "faiss.IndexFlatIP",
            "build_seconds": round(gt_build_s, 4),
            "note": "exact brute force O(N); recall@k baseline",
        },
        "candidates": [],
    }

    # Candidate A: FAISS IndexHNSWFlat
    faiss_hnsw, fb, fq = faiss_hnsw_neighbors(
        embeddings, k_max, int(faiss_cfg["M"]),
        int(faiss_cfg["ef_construction"]), int(faiss_cfg["ef_search"]),
    )
    result["candidates"].append({
        "backend": "faiss.IndexHNSWFlat",
        "params": {"M": int(faiss_cfg["M"]),
                   "ef_construction": int(faiss_cfg["ef_construction"]),
                   "ef_search": int(faiss_cfg["ef_search"])},
        "build_seconds": round(fb, 4),
        "query_seconds": round(fq, 4),
        "recall_at_k": {str(k): round(recall_at_k(gt, faiss_hnsw, k), 4) for k in ks},
    })

    # Candidate B: USearch
    usearch, ub, uq = usearch_neighbors(
        embeddings, k_max, usearch_cfg["metric"],
        int(usearch_cfg["connectivity"]), int(usearch_cfg["expansion_add"]),
        int(usearch_cfg["expansion_search"]),
    )
    result["candidates"].append({
        "backend": "usearch.Index",
        "params": {"metric": usearch_cfg["metric"],
                   "connectivity": int(usearch_cfg["connectivity"]),
                   "expansion_add": int(usearch_cfg["expansion_add"]),
                   "expansion_search": int(usearch_cfg["expansion_search"])},
        "build_seconds": round(ub, 4),
        "query_seconds": round(uq, 4),
        "recall_at_k": {str(k): round(recall_at_k(gt, usearch, k), 4) for k in ks},
    })

    # Gate verdict (D-2280/RATIFY-2 gate #1)
    pass_k = int(recall_cfg["pass_k"])
    threshold = float(recall_cfg["pass_threshold"])
    faiss_r = result["candidates"][0]["recall_at_k"][str(pass_k)]
    usearch_r = result["candidates"][1]["recall_at_k"][str(pass_k)]
    result["gate"] = {
        "pass_k": pass_k,
        "pass_threshold": threshold,
        "faiss_hnsw_recall": faiss_r,
        "usearch_recall": usearch_r,
        "verdict": "PASS" if (faiss_r >= threshold and usearch_r >= threshold) else "FAIL",
    }

    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="USearch/HNSW vs IndexFlatIP KNN recall harness (D2280)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--n", type=int, default=None, help="override sample_size")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    result = run(cfg, args.n)

    # Console report
    print("\n" + "=" * 72)
    print("RECALL@k — exact IndexFlatIP vs approximate HNSW (bge-m3 512d)")
    print("=" * 72)
    for c in result["candidates"]:
        r = "  ".join(f"@{k}={v:.4f}" for k, v in c["recall_at_k"].items())
        print(f"{c['backend']:<24} build={c['build_seconds']:>7.4f}s "
              f"query={c['query_seconds']:>7.4f}s  {r}")
    g = result["gate"]
    print("-" * 72)
    print(f"GATE @k={g['pass_k']} threshold={g['pass_threshold']}: "
          f"faiss={g['faiss_hnsw_recall']:.4f} usearch={g['usearch_recall']:.4f} "
          f"→ {g['verdict']}")

    # Crash-safe write (C6): tempfile → fsync → os.replace
    out_path = PROJECT_ROOT / cfg["output"]["path"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    with open(tmp_path, "w") as f:
        json.dump(result, f, indent=2)
        f.flush()
        import os
        os.fsync(f.fileno())
    os.replace(tmp_path, out_path)
    print(f"\n📄 receipt written: {out_path}")


if __name__ == "__main__":
    main()
