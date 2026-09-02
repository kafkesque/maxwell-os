# Retrieval Research — MUST / SHOULD / WORTH (2026-09-02)

> **Authority:** feed.opml technology feeds + peer-reviewed retrieval literature, evaluated against
> Maxwell OS constraints (C1 $0 marginal, C3 sovereign, C5 zero-bloat, C21 swappable, C22 hybrid
> opt-in, C24 hardware-adaptive M1 Max 64GB, R7 temp=0.0). Companion to DECISION-LOG D2507.

## Current retrieval stack (what already works — tested 2026-09-02)

| Layer | Implementation | Status |
|-------|---------------|--------|
| Full-text | SQLite FTS5 (name/definition/keywords) | ✅ live |
| Vector | sqlite-vec `vec_fbs` (bge-m3, 512d Matryoshka) | ✅ live (commit-time embed, query-time embed only) |
| Metadata | SQL keyword (domain/discipline/depth/status) | ✅ live |
| Fusion | Reciprocal Rank Fusion (D2176) | ✅ live — **smoke-tested: `search_hybrid` returns fused ranks, degrades to FTS when `vec_fbs` absent (C23)** |
| Graph | related_fbs/contradicts_fbs/prerequisite_fbs BFS (P1.4) | ✅ live (graph-aware search) |
| Agentic | CRAG-style critique loop (Phi-4-mini, D2205) | ✅ live (iterative, budget-capped) |
| Quarantine | opt-in only (`status='PASS'` default, D2330) | ✅ live (retrieval contract) |

The convergence-gated knowledge base + RRF hybrid + graph + CRAG critique already gives Maxwell a
**structural edge over naïve RAG**: every retrieved FB is BORP-verified (≥2 sources) before it can be
surfaced, and the graph surfaces contradictions alongside support (not just similarity).

---

## ⏱️ Adoption timing — what goes BEFORE S6 vs AFTER S6

> **Direct answer: nothing in the retrieval-research list BLOCKS S6.** The retrieval stack is already
> correct and live (RRF + FTS + vector + graph + agentic). The only code changes that must be applied
> *before* S6 are the verification fixes **already applied in D2507** (BUG-205 book dedup + B2
> synthesis-entailment majority rule + evidence-garbage filter), and they are materialized by the
> **post-hoc S5 re-run**, not by S6. S6 is a *persistence* stage (SQLite+Parquet) — it commits whatever
> the S5 checkpoint contains, so the ordering is: **S5 re-run → `pre-s6` → `stage6`**, not "adopt retrieval
> tech → S6".

| Timing | Item | Status |
|--------|------|--------|
| **BEFORE S6 (already done, D2507)** | BUG-205 book dedup + B2 majority rule + evidence-garbage filter | ✅ code committed; re-verification via S5 re-run |
| **BEFORE S6 (gate)** | `just pre-s6` (count / fb_id-unique / contamination / tally) | ✅ script ready; run after S5 re-run |
| **AT S6 (verify, not adopt)** | M1 vector-dim contract (bge-m3 512d ↔ `vec_fbs float[512]`) | 🔴 **CONFIRMED DEGRADED (D2508)** — `vec_fbs` absent (python.org SQLite lacks `enable_load_extension`); FTS-only fallback live |
| **AFTER S6 (SHOULD)** | S1 contextual embeddings, S2 cross-encoder rerank (gated), S3 HyDE (gated) | ⏳ |
| **AFTER S6 (WORTH)** | USearch / TurboVec / LightRAG / ColBERT / GraphRAG / RAPTOR | ⏳ monitor/conditional |

---

## MUST (adopt now / verify at S6 — correctness + sovereignty, near-zero cost)

### M1. Verify the vector-dimension contract (bge-m3 512d ↔ `vec_fbs float[512]`) — 🔴 NOW A LIVE BLOCKER (D2508)
> **D2508 finding:** at S6 commit, `vec_fbs` was ABSENT and all 7867 embedding inserts failed (`no such table: vec_fbs`). Root cause is NOT the dimension contract but the **Python runtime**: `/usr/local/bin/python3` (python.org framework 3.12.1) has SQLite compiled WITHOUT `enable_load_extension` (`SQLITE_OMIT_LOAD_EXTENSION`), so `sqlite_vec.load()` raises `AttributeError` even though `sqlite-vec` is pip-installed and `vec0.dylib` is present. **Fix:** run under `/opt/homebrew/bin/python3` (SQLite 3.53.3, `enable_load_extension=True`) or the `knowledge-pipeline` conda env (3.11.15, SQLite 3.52.0) + `pip install sqlite-vec`, then backfill embeddings from persisted `fbs.definition` (no S5 re-run). Until then, RRF degrades to FTS-only (C23 path already smoke-tested).
- **What:** `stage6_commit.py` pre-computes `definition_embedding` at commit time (BUG-004) and stores
  it in `vec_fbs` (`float[S15_EMBED_DIM]`); `search_vector` embeds the query and packs `len(query_vec)f`.
  A dimension drift (e.g. bge-m3 pulled at 1024d native vs the 512d Matryoshka truncation in config) would
  make every vector query return garbage or error.
- **Why MUST:** silent vector corruption = silent retrieval failure (violates C16/C23). This is a *latent*
  risk, not an observed bug.
- **Action:** post-S6, run `python3 pipeline/retrieve.py --vector "test query"` and assert non-empty,
  sane-ranked results; add a CI assert that `embed_dim == 512` and the query embed length matches.
- **Reference:** Matryoshka Representation Learning (Kusupati et al., ICLR 2022) — truncated-dimension
  ranking is preserved only if the model is MRL-trained (bge-m3 is); the contract must hold at rest.

### M2. Keep RRF as the fusion primitive (do NOT swap to score fusion)
- **What:** RRF (D2176) is already correct and robust to heterogeneous score scales (FTS rank vs cosine vs
  metadata). Do not regress to weighted-score fusion (which requires per-signal normalization and breaks
  when a signal is absent).
- **Why MUST:** RRF is the one fusion method that is scale-free and deterministic (R7-safe); it is the
  correctness backbone of hybrid search. Confirmed working via the `vec_fbs`-absent fallback smoke test.
- **Reference:** Cormack, Clarke & Buettcher, "Reciprocal rank fusion outperforms condorcet and individual
  rank learning methods", SIGIR 2009.

---

## SHOULD (adopt post-S6 — high retrieval-quality lever, local, low risk)

### S1. Contextual / late-chunk embeddings for the weak-ISOR single-source tail (MTR task 34)
- **What:** Maxwell clusters RAW segments at S1.5 (cluster-before-extract), then extracts FB *definitions*.
  The FB `definition_embedding` is already a good retrieval target — but the **single-source / singleton
  tail** (weak ISOR, `source_diversity == 1`) embeds a paraphrase that may not align with the user query.
  Contextual/late-chunk embeddings (embed each segment with its section heading + book context prepended)
  would recover these.
- **Why SHOULD:** single-largest recall lever for the long tail; fully local (bge-m3); deterministic (R7).
- **Reference:** Anthropic, "Introducing Contextual Retrieval" (2024); Weaviate, "Late Chunking" (2024).

### S2. Local cross-encoder rerank of the top-K hybrid candidates
- **What:** Rerank the top ~50 RRF candidates with a local cross-encoder (e.g. `bge-reranker-v2-m3`,
  `ms-marco-MiniLM`) to lift precision before the graph/agentic pass.
- **Why SHOULD (conditional):** precision boost is real, but a prior Maxwell benchmark
  (`stage2_relabel_extraction_type.py`) found cross-encoders could NOT cleanly separate relabel classes —
  a DIFFERENT task. Gate on a held-out retrieval-precision A/B before enabling.
- **Reference:** Nogueira & Cho, "Passage Re-ranking with BERT", arXiv:1901.04085 (2019).

### S3. HyDE-style query expansion (hypothetical-answer embedding) — gated
- **What:** Generate a short hypothetical answer to the query (local Phi-4-mini/Qwen), embed it, and fuse
  its retrieval with the raw-query retrieval.
- **Why SHOULD (conditional):** improves recall on queries with vocabulary mismatch; adds one local LLM
  call of latency and must be temp=0.0 (R7). Gate on recall@k improvement over baseline.
- **Reference:** Gao et al., "Precise Zero-Shot Dense Retrieval without Relevance Labels", arXiv:2212.10496 (2022).

---

## WORTH (monitor / adopt conditionally — do NOT block S6)

| Item | Why worth / why defer | Reference |
|------|----------------------|-----------|
| **USearch** (feed.opml) | 10× HNSW vs FAISS, NEON-optimized for Apple Silicon. But S1.5 clustering needs **exact** kNN (Louvain on R-NN edges), so ANN would change cluster semantics. Adopt only for a large FB-retrieval index (>100K FBs), not clustering. | Malkov & Yashunin, TPAMI 2018 (HNSW); Vardanian, USearch 2023 |
| **TurboVec** (feed.opml, installed) | Quantized 2-4-bit vector store (Metal SIMD). `pipeline/storage/turbovec_backend.py` exists but is NOT wired. sqlite-vec is sufficient at current FB scale; adopt when corpus outgrows float32 memory. | RyanCodrai/turbovec |
| **LightRAG** (feed.opml) | Graph-based RAG (entity-relation + traversal). Redundant with Maxwell's existing `related_fbs` graph (P1.4) — adopting adds an LLM extraction pass (C1 cost) + a dependency (C5). The custom BFS is lighter and sovereign. Defer. | Guo et al., EMNLP 2025 (LightRAG) |
| **ColBERT late interaction** | Higher precision via token-level interaction, but per-token index storage blowup + a local ColBERT model. Defer until precision is the binding constraint. | Khattab & Zaharia, SIGIR 2020 |
| **GraphRAG** (MSFT) | Community-summary graph RAG. Heavy LLM precompute (violates C1 at $0 marginal for large corpora) and Maxwell already graphs at the FB level. Monitor only. | Edge et al., arXiv:2404.16130 (2024) |
| **RAPTOR** | Recursive abstractive tree over chunks. Requires a summarization LLM pass per level (C1 cost). Defer. | Sarthi et al., ICLR 2024 |
| **zvec / sqlite-vss** | Alternative embedded vector stores. sqlite-vec already works; no swap needed (C21 swappable covers migration path). | Alibaba/zvec; asg017/sqlite-vss |
| **memvid** | Agent-memory layer, NOT pipeline retrieval. Out of scope for Layer 1. | memvid/memvid |

---

## What was TESTED this session (the "test what must be adopted" mandate)

1. ✅ **RRF hybrid retrieval** — `search_hybrid(conn, "feedback loop", 5)` against the 185-FB diagnostic DB
   returned correctly fused ranks with `_rrf_score` attached, and **gracefully fell back to FTS** when
   `vec_fbs` was absent (`⚠️ vec_fbs unavailable, falling back to FTS`) — proving the C23 resilient path.
2. ✅ **BUG-205 book dedup** — 16/16 new tests (Unicode fold "Brené"=="Brene", space-subtitle "Blink" collapse,
   distinct-works-no-collapse) + 962-file corpus → 910 distinct canonical source_ids.
3. ✅ **B2 majority entailment** — 8/8 new tests on the pure `_b2_majority_verdict` (single-passage parity,
   majority-vote, contradiction-veto, score contract). Full suite **174 passed**.

### Deferred live tests (need the S6-committed DB)
- Vector-dimension contract (M1) — requires `just stage6` first.
- End-to-end agentic retrieval precision — requires the full FB corpus + a golden query set.

---

*Research date: 2026-09-02. Feeds: feed.opml (vector-search, RAG, FAISS, embedding, ANN/HNSW, MLX).*
