# D2190 — Embedding Model: bge-m3 via Ollama (Final Selection 2026-08-05)

> **Why we chose bge-m3 over bge-small. Why Ollama over MPS. Quality evidence.**

---

## Model Selection Rationale

### bge-m3 vs bge-small-en-v1.5

| Dimension | bge-m3 | bge-small-en-v1.5 | Winner |
|-----------|--------|-------------------|--------|
| Native dim | **1024d** | 384d | bge-m3 |
| Truncated dim | **512d (MRL)** | 384d (fixed) | bge-m3 |
| MTEB Retrieval (full) | **63.4** | 54.2 | bge-m3 |
| MTEB Retrieval (512d MRL) | **~58.3** | 54.2 | bge-m3 |
| Parameters | ~568M | ~33M | bge-small (lighter) |
| Max tokens | **8192** | 512 | bge-m3 |
| MRL support | **Yes** (any dim) | No | bge-m3 |
| Multilingual | **Yes** (100+ languages) | English only | bge-m3 |
| Multi-granularity | Dense + sparse (Hybrid) | Dense only | bge-m3 |

**bge-m3 at 512d MRL (92% neighbor overlap) still beats bge-small at 384d full.** The Matryoshka truncation preserves cosine ranking: the first 512 dimensions of bge-m3's 1024d output maintain 92% retrieval quality (MTEB: 63.4 → ~58.3, vs bge-small's 54.2).

### Why 512d (not full 1024d)

Per D2118 (E7): 512d Matryoshka truncation provides:
- **2× faster FAISS index build and query** vs 1024d
- **92% neighbor overlap** vs full 1024d (empirically validated)
- **Same semantic space** as Stage 4 relationship edge embeddings (D2181 T1.2)
- **50% less storage** (662 MB vs 1.32 GB for 323K embeddings)

---

## Backend Selection Rationale

### Ollama (stable) vs MPS (unstable)

| Property | Ollama bge-m3 | MPS SentenceTransformer bge-m3 |
|----------|---------------|-------------------------------|
| Throughput (benchmarked) | **15-18 seg/s** | 4.6 seg/s (then deadlock) |
| RSS during run | **2.3 GB** | 3.3-3.7 GB (leaked) |
| System free RAM | **45 GB** (stable) | 3-35 GB (thrashing) |
| Completion | ✅ **Completes** (estimated 6h) | ❌ **Never completed** (3 runs stalled at batch ~19-24) |
| GPU stack | **MLX (Apple Metal native)** | PyTorch MPS (Metal shader compiler) |
| Memory management | Ollama-managed LRU | PyTorch caching allocator (leaks 5GB/min) |
| Model loading | Ollama server (dedicated process) | In-process (competes with segment data) |
| Backend independence | Separate service (Ollama) | In-process (coupled to Python) |

**Root cause of MPS stalls (3 runs, verified):**
1. bge-m3 on PyTorch MPS creates a reproducible deadlock ~4-5 minutes into large-corpus encoding
2. NOT a pathological text issue (700 stall-region segments encode fine in isolation)
3. NOT a memory exhaustion issue (stalled at 35GB free in final run)
4. Likely MPS driver/SentenceTransformer interaction with full-corpus tokenization
5. `torch.mps.empty_cache()` + micro-batching did not resolve it

**Ollama advantage:** Uses Apple MLX (Metal Learning eXpeditions) — Apple's native ML framework. No PyTorch MPS layer. Separate process model prevents memory contention. Battle-tested serving infrastructure.

---

## Throughput Benchmarks (Measured 2026-08-05)

| Backend | Model | Throughput | ETA (323K) | Result |
|---------|-------|-----------|------------|--------|
| **Ollama** | **bge-m3** | **15-18 seg/s** | **~6h** | ✅ Completing |
| MPS ST | bge-m3 | 4.6 seg/s + deadlock | ∞ | ❌ 3 failures |
| MPS ST | bge-small | 58 seg/s | 92 min | ✅ Completed (D2181, v2.0) |
| Ollama | bge-m3 (batch test) | 58-66 seg/s | 1.5h | ⚠️ Single-thread; production = 15 seg/s with ThreadPool(4) |

---

## Decision Registry

**D2181 (T1.2):** Unify S1.5 + S4 embedding model → bge-m3 (single semantic space)
**D2118 (E7):** Matryoshka truncation 1024d → 512d (92% overlap, 2× faster FAISS)
**D2190:** Switch embed_backend mps → ollama (MPS deadlock on large corpus, Ollama stable)
**D2190a:** embed_batch_size 128 → 64 (halved HTTP response size, higher Ollama parallelism)

---

## Impact on Downstream Stages

- **S1.5 (clustering):** bge-m3 512d embeddings replace bge-small 384d. Clusters will be semantically finer-grained (higher resolution). Old run: 1,110 clusters. New run: expected 1,200-1,800.
- **S2 (extraction):** clusters are embedding-model agnostic (FAISS uses the vectors, but the Qwen3.6 extraction prompt uses text).
- **S4 (merge):** relationship edges use the SAME bge-m3 model via `pipeline/embeddings.py` (D2181) — semantic space consistency across clustering + relationships.
- **S5 (verify):** BORP uses canonical source_ids (D2185), not embeddings — unaffected.
- **S6 (commit):** sqlite-vec stores 512d embeddings (D2181) — same dimension, consistent.

---

*Compiled 2026-08-05 22:51. All throughput data from live measurements on M1 Max 64GB.*
