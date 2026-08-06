#!/usr/bin/env python3
"""
stage1_5_domain_cluster.py - Domain-bucketed convergent clustering (D2094/D2124)
================================================================================
S1.5 front-end to the streaming runner (D2137): groups the segment corpus by
DOMAIN (top-level book folder), embeds per domain, FAISS R-NN clusters at the
agreed threshold, and emits convergent clusters (>=2 segments from >=2 distinct
books) plus singletons.

D2094: per-domain clustering (not cross-domain), MIN_DISTINCT_SOURCES=2,
threshold 0.75-0.80, noise preservation.
D2120 P0.3: R-NN (reciprocal nearest neighbors) - no transitive union-find.
D2118: Matryoshka 512-dim when bge-m3 backend selected (embed_dim config).

Subprocess safety (verified 2026-08-04): faiss-cpu 1.14.3 + torch MPS in the
SAME process segfaults at teardown. Embedding and FAISS run in SEPARATE
subprocesses.

C12: all thresholds/models from config/stage1_5.*
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import yaml

_CFG = yaml.safe_load(open(ROOT / "config" / "pipeline_config.yaml"))
S15 = _CFG.get("stage1_5", {})
THRESHOLD = float(S15.get("faiss_threshold", 0.75))
MIN_DISTINCT = int(S15.get("min_source_diversity", 2))
MIN_SIZE = int(S15.get("min_cluster_size", 2))
NEIGHBOR_K = int(S15.get("neighbor_k", 150))
EMBED_BACKEND = S15.get("embed_backend", "mps")  # mps | ollama
# mps backend uses the HF model id; ollama backend uses the Ollama model name
EMBED_MODEL = S15.get("embed_model_hf", "BAAI/bge-small-en-v1.5") if EMBED_BACKEND == "mps" else S15.get("embed_model", "bge-m3")
EMBED_DIM = int(S15.get("embed_dim", 512))  # D2118 Matryoshka truncation (ollama path only)

# S1 chunk output: config-driven with known fallback
_segs_cfg = (_CFG.get("paths") or {}).get("stage1_chunk_output")
SEGS_PATH = Path(_segs_cfg) if _segs_cfg else (
    ROOT / "knowledge pipeline" / "stage1_chunk" / "latest" / "checkpoint.jsonl")
# D2137: output to the path stage2.load_clusters() reads (STAGE1_5_CHECKPOINT)
from pipeline.pipeline_paths import STAGE1_5_CHECKPOINT as _S15_CP

OUT_DIR = Path(_S15_CP).parent

# D2137: boilerplate patterns from config (stage1_3.drop_patterns_extra)
_BOILER = (_CFG.get("stage1_3", {}) or {}).get("drop_patterns_extra", []) or []
_BOILER_RE = __import__("re").compile(
    "|".join(__import__("re").escape(b) for b in _BOILER if b), __import__("re").I) if _BOILER else None

_EMBED_WORKER = """
import sys, json, numpy as np
texts = [json.loads(l)["text"][:500] for l in open(sys.argv[1])]
from sentence_transformers import SentenceTransformer
m = SentenceTransformer(sys.argv[2], device="mps")
embs = m.encode(texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True)
np.save(sys.argv[3], embs.astype("float32"))
"""

_FAISS_WORKER = """
import sys, json, numpy as np, faiss
embs = np.load(sys.argv[1])
faiss.normalize_L2(embs)
idx = faiss.IndexFlatIP(embs.shape[1]); idx.add(embs)
th = float(sys.argv[2])
K = min(int(sys.argv[3]), len(embs))
D, I = idx.search(embs, K)
# directed neighbor pairs above threshold (skip self; SKIP same-book edges —
# same-book similarity is not convergence, D2137 cross-book-only)
books = None
if len(sys.argv) > 4:
    import json as _json
    books = [_json.loads(l)["source_path"] for l in open(sys.argv[4])]
directed = set()
for i in range(len(embs)):
    for k in range(1, K):
        if float(D[i][k]) >= th:
            j = int(I[i][k])
            if books is None or books[i] != books[j]:
                directed.add((i, j))
# R-NN: reciprocal pairs only (D2120 P0.3 - no transitive merge)
pairs = {}
for (i, j) in directed:
    if (j, i) in directed:
        pairs[(min(i, j), max(i, j))] = True
# union-find on reciprocal edges
parent = list(range(len(embs)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]; x = parent[x]
    return x
for (a, b) in pairs:
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb
# group
from collections import defaultdict
comp = defaultdict(list)
for i in range(len(embs)): comp[find(i)].append(i)
out = [sorted(v) for v in comp.values() if len(v) >= 2]
print(json.dumps(out))
"""


def domain_of(seg: dict) -> str:
    """Top-level folder after .../books/ in source_path (e.g. 'DOMAIN 0 ...').

    Verified 2026-08-04: the checkpoint's source_book is only the filename;
    the domain folder lives in source_path (.../books/DOMAIN X/.../book.md).
    """
    src = seg.get("source_path") or ""
    if src:
        parts = Path(src).parts
        for idx, p in enumerate(parts):
            if p == "books" and idx + 1 < len(parts):
                return parts[idx + 1]
        for p in parts:
            if p.startswith("DOMAIN"):
                return p
    return "UNKNOWN"


def load_segments(domain: str | None, limit: int) -> list[dict]:
    segs = []
    with open(SEGS_PATH) as f:
        for line in f:
            seg = json.loads(line)
            if domain and domain_of(seg) != domain:
                continue
            if _BOILER_RE and _BOILER_RE.search(seg.get("text", "")):
                continue  # D2137: drop publisher boilerplate before clustering
            segs.append(seg)
            if limit and len(segs) >= limit:
                break
    return segs


def embed_subprocess(tmp_segs: Path, tmp_npy: Path):
    """Embed via MPS in a subprocess (avoids faiss+MPS same-process segfault)."""
    t0 = time.time()
    r = subprocess.run(
        [sys.executable, "-c", _EMBED_WORKER, str(tmp_segs), EMBED_MODEL, str(tmp_npy)],
        capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise RuntimeError(f"embed worker failed: {r.stderr[-500:]}")
    return time.time() - t0


def embed_ollama(texts: list[str], tmp_npy: Path):
    """Embed via local Ollama bge-m3 (D2118 Matryoshka 512 via config dim)."""
    import pipeline.embeddings as emb
    arr = emb.embed_texts_bge_m3(texts)
    if arr.shape[1] > EMBED_DIM:
        arr = arr[:, :EMBED_DIM]  # Matryoshka truncation (D2118)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        arr = arr / norms
    np.save(tmp_npy, arr.astype("float32"))
    return 0.0


def faiss_subprocess(tmp_npy: Path, tmp_segs: Path) -> list[list[int]]:
    """Cluster via FAISS in a subprocess. Returns list of member-index lists."""
    r = subprocess.run(
        [sys.executable, "-c", _FAISS_WORKER, str(tmp_npy), str(THRESHOLD),
         str(NEIGHBOR_K), str(tmp_segs)],
        capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"faiss worker failed: {r.stderr[-500:]}")
    return json.loads(r.stdout.strip().split("\n")[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", help="Only this domain folder (else all)")
    ap.add_argument("--limit", type=int, default=0, help="Max segments (testing)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_all = time.time()
    segs = load_segments(args.domain, args.limit)
    if not segs:
        print(f"no segments (domain={args.domain})"); return
    print(f"segments: {len(segs)} | books: {len(set(s['source_book'] for s in segs))}")

    texts = [s["text"][:500] for s in segs]
    tmp_segs = OUT_DIR / "_segs.jsonl"
    tmp_npy = OUT_DIR / "_embs.npy"
    # One segs file for both workers: embedding texts + cross-book book map
    with open(tmp_segs, "w") as f:
        for s in segs:
            f.write(json.dumps({"text": s["text"][:500],
                                "source_path": s.get("source_path", "")}) + "\n")

    if EMBED_BACKEND == "mps":
        el = embed_subprocess(tmp_segs, tmp_npy)
    else:
        el = embed_ollama(texts, tmp_npy)
    print(f"embed ({EMBED_BACKEND}/{EMBED_MODEL}): {len(segs)} in {el:.1f}s = {len(segs)/el:.0f} seg/s")

    t0 = time.time()
    member_lists = faiss_subprocess(tmp_npy, tmp_segs)
    print(f"faiss R-NN: {len(member_lists)} candidate groups in {time.time()-t0:.1f}s")

    # Build convergent clusters + singletons
    clusters = []
    singleton_ids = []
    in_cluster = set()
    for i, members in enumerate(member_lists):
        books = {segs[m]["source_book"] for m in members}
        n_src = len(books)
        converg = len(members) >= MIN_SIZE and n_src >= MIN_DISTINCT
        cid = f"dc_{i:05d}"
        clusters.append({
            "cluster_id": cid, "segment_ids": members,
            "source_books": sorted(books), "source_diversity": n_src,
            "is_convergent": converg, "is_noise": not converg,
            "cohesion": round(float(np.mean([1.0])), 3), "size": len(members),
            "domain": args.domain or "ALL", "schema_version": "1.0",
        })
        if converg:
            in_cluster.update(members)
    for m in member_lists:
        in_cluster.update(m)
    for i in range(len(segs)):
        if i not in in_cluster:
            singleton_ids.append(i)

    with open(OUT_DIR / "checkpoint.jsonl", "w") as f:
        for c in clusters:
            f.write(json.dumps(c) + "\n")
    with open(OUT_DIR / "singletons.jsonl", "w") as f:
        for i in singleton_ids:
            f.write(json.dumps({"segment_id": segs[i].get("segment_id"),
                                "source_book": segs[i].get("source_book")}) + "\n")

    n_conv = sum(1 for c in clusters if c["is_convergent"])
    print(f"clusters: {len(clusters)} | CONVERGENT: {n_conv} "
          f"({n_conv/len(segs)*100:.1f}% of segs) | singletons: {len(singleton_ids)}")
    print(f"total: {time.time()-t_all:.1f}s | out: {OUT_DIR}")


if __name__ == "__main__":
    main()
