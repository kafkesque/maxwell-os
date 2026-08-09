# Maxwell OS v3.0 — Market Research: Speed & Accuracy Enhancements
## Comparable Systems & Optimization Techniques
**Date:** 2026-08-09 | **Analyst:** Senior RAG Engineer
**Updated:** After D2220-D2221 fixes (depth classifier + mechanism pre-filter)

---

## 1. COMPARABLE KNOWLEDGE EXTRACTION SYSTEMS

### 1.1 Microsoft GraphRAG
- **Repo:** microsoft/graphrag
- **Approach:** Entity extraction → community detection (Leiden) → community summarization → graph-based retrieval
- **Key Difference from Maxwell:** GraphRAG extracts entities + relationships, then SUMMARIZES communities hierarchically. Maxwell extracts CAUSAL PRINCIPLES from convergent clusters. GraphRAG is retrieval-oriented; Maxwell is knowledge-synthesis-oriented.
- **Technique Worth Adopting:** Leiden community detection for cross-cluster merging. Maxwell's cluster-before-extract creates isolated clusters — Leiden could find latent connections between clusters that share entities.
- **Not Applicable:** GraphRAG's LLM-per-node approach (each entity gets an LLM-summarized description) would balloon Maxwell's cost from 2,655 FB calls to potentially 50,000+ entity calls.
- **Action:** Monitor for community summarization quality benchmarks. If Maxwell expands to entity extraction, Leiden clustering is the gold standard.

### 1.2 LightRAG
- **Repo:** HKUDS/LightRAG
- **Approach:** Dual-level retrieval (low-level: specific entities; high-level: topic summaries) with incremental graph updates.
- **Key Difference:** LightRAG is retrieval-focused with lightweight graph construction. Maxwell's 8-stage pipeline is extraction-focused with rigorous verification (NLI + cross-family LLM).
- **Technique Worth Adopting:** Incremental graph updates. LightRAG can add new documents without rebuilding the entire graph. Maxwell currently requires full S2→S6 rerun for new books. An incremental mode would dramatically reduce update cost.
- **Action:** Track LightRAG's incremental update algorithm. Could be adapted for Maxwell Stage 2 (re-extract only affected clusters when new books added).

### 1.3 Graphify
- **Repo:** Graphify-Labs/graphify (⭐104,581)
- **Approach:** Turn any codebase/docs/SQL/PDFs into queryable knowledge graph. Claude Code/Cursor skill.
- **Key Difference:** Tool-oriented (dev tool for code understanding). Not a general knowledge extraction pipeline.
- **Not Applicable:** Maxwell targets books and research papers, not codebases. Different domain entirely.

### 1.4 Cognee / Context-Graph-Cognee
- **Approach:** Local Cognee + Ollama knowledge graph pipeline with automatic model provisioning.
- **Key Difference:** Small-scale document ingestion. Not designed for 200+ books with convergent extraction.
- **Technique Worth Adopting:** Automatic model provisioning — Cognee detects available hardware and selects appropriate model size. Maxwell could adapt this for hardware-adaptive scaling (C24).

### 1.5 Paper Knowledge Extractor
- **Repo:** vipulkumar90/paper-knowledge-extractor
- **Approach:** Marker (PDF→MD) + local LLM + Pydantic validation. Closest to Maxwell's Stage 0→2 flow.
- **Key Difference:** Single-paper extraction. No convergence across sources. No verification stage.
- **Technique Worth Adopting:** Pydantic validation at extraction boundary (already adopted in Maxwell via schemas.py).

---

## 2. INFERENCE ACCELERATION (SPEED)

### 2.1 Continuous Batching — MOST PROMISING
- **OMLX** (⭐18,552): The server Maxwell already uses supports **continuous batching & SSD caching**. This means multiple prompts can be batched into a single forward pass, sharing the model weights in GPU memory.
- **vllm-mlx** (⭐1,498): OpenAI-compatible server with **continuous batching, 400+ tok/s**, MCP tool calling. Native MLX backend.
- **Impact on Maxwell:**
  - S2: If OMLX continuous batching is enabled, multiple FB extractions can share the Qwen3-Coder model weights. Instead of 2,655 sequential calls at 18s each, batch 8-16 FBs per forward pass.
  - **Estimated speedup:** 4-8x for S2 (13.3h → 1.7-3.3h) if batching works with different prompts.
  - **Risk:** temp=0.0 may conflict with batched inference (some batching implementations use stochastic sampling). Must test determinism.
  - **Memory:** Qwen3-Coder-30B-4bit ≈ 5-8GB. Batching 16 prompts might need 2-3x context memory. On 64GB, feasible.

### 2.2 KV-Cache Prefix Sharing
- If S2 uses the same system prompt + golden few-shot examples across all 2,655 calls, the KV-cache for the shared prefix can be computed ONCE and reused.
- **MLX/Omlx support:** OMLX mentions "SSD caching" — this likely includes KV-cache persistence.
- **Estimated speedup for S2:** 20-30% reduction in per-call latency (prefix is ~2,000 tokens out of ~4,000 total).
- **Implementation:** Requires OMLX to support `prefix_cache_id` parameter. Check OMLX v0.5.x API.

### 2.3 Model Quantization / Smaller Models
- **Current S2 model:** Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (MoE, 3B active per token). Already 4-bit quantized.
- **Qwen3-Coder-8B:** Smaller variant exists. Would be faster but potentially lower quality.
- **Phi-4-mini-8bit** (2.4B params): Already used for S4 classification. ~7s/call.
- **Gemma-4-E4B-4bit:** Could replace Qwen3 for CRIBS enrichment. Already confirmed working (0.48s response for simple tasks).
- **Action:** A/B test Qwen3-Coder-8B vs 30B for S2 extraction quality. If quality holds, 3-4x speedup.

### 2.4 Pipeline Parallelism (Streaming)
- S2 output for FB_i is independent of S2 output for FB_j.
- Can pipeline as: S2(FB_i) → S4(FB_i) while S2(FB_i+1) runs in parallel.
- **Constraint:** OMLX can only serve one model at a time unless two instances run on different ports.
- **Two-model setup:** Port 11435 (Qwen3-Coder for S2) + Port 11436 (Phi-4-mini for S4 class).
- **Estimated speedup:** 1.4-1.8x (S4 runs concurrently with S2).
- **Memory:** Qwen3-Coder (~6GB) + Phi-4-mini (~3GB) + DeBERTa (~0.4GB) = ~10GB. Well within 64GB.

### 2.5 Merge S4 CRIBS + Classification
- Currently 2 sequential LLM calls per FB. Merge into 1 call producing all fields.
- **Already A/B tested for structured JSON (D2219):** 4.55s baseline → 4.24s structured (7% faster).
- **Merged CRIBS+Classify:** One prompt produces {application, failure_mode, elaboration, keywords, discipline, domains, depth, evidence}.
- **Estimated speedup for S4:** ~45% (one call instead of two).
- **Risk:** Deferred pending quality A/B test. Prompt complexity increases.

### 2.6 Skip CRIBS for High-Quality FBs
- If mechanism > 500 chars AND definition is detailed, CRIBS enrichment may add marginal value.
- A lightweight classifier (regex or fast model) could flag "CRIBS needed" vs "skip."
- **Estimated skip rate:** 30-50% of FBs.
- **Risk:** Some FBs would lack application/failure_mode/elaboration. Acceptable if mechanism already covers these implicitly.

---

## 3. ACCURACY ENHANCEMENTS

### 3.1 Cross-Cluster Deduplication (Leiden Community Detection)
- Maxwell's cluster-before-extract creates isolated clusters. Two clusters may extract near-identical FBs.
- **Solution:** After S2, run Leiden community detection on FB embedding space. Merge clusters that produce semantically identical FBs.
- **Impact:** Reduces FB count (2,655 → maybe 2,000-2,300) and eliminates near-duplicates.
- **Cost:** One additional embedding + clustering pass. ~5-10 minutes on 2,655 vectors.

### 3.2 Source Independence Scoring
- Current BORP checks ≥2 source books. But two books by the SAME AUTHOR on the same topic are not independent.
- **Solution:** Author-aware BORP. Check if source books share authors. Deduplicate same-author sources.
- **Also:** Check for citation relationships (Book A cites Book B as source).
- **Impact:** Catches false convergence from same-author echo chambers.

### 3.3 Weighted NLI Entailment
- Current MAX-entailment: strongest passage signal wins. Vulnerable to citation echo.
- **Alternative:** Weighted mean entailment, where each passage's weight is inverse to the number of passages from the same book.
- **Also:** Source diversity bonus — if passages come from 3+ different disciplines, boost score.
- **Impact:** More robust against high-source-count platitudes.

### 3.4 Dynamic Golden Example Selection
- Current: Static 32-example golden set for all clusters.
- **Alternative:** Embed cluster definition → retrieve top-K most similar golden examples → use those as few-shot.
- **Impact:** More relevant examples per cluster → better extraction quality.
- **Cost:** Negligible (embedding lookup is <1ms).

### 3.5 Iterative Refinement for Contentious FBs
- FBs flagged by S5 (marginal NLI, LLM uncertain) could be sent back to S2 with refinement instructions.
- **"Your extraction was flagged. Here's why. Try again with more specific mechanism."**
- **Impact:** Higher yield of quality FBs from borderline clusters.
- **Cost:** 2x LLM calls for ~30% of FBs. Currently these just go to QUARANTINE.

### 3.6 Contradiction-Aware Verification
- Already partially implemented: contradiction ≥ 0.8 → fail regardless of entailment.
- **Enhancement:** If ANY passage contradicts while others entail, this is a RED FLAG — the FB may be over-generalizing. Escalate to human review.
- **Impact:** Catches boundary violations (like Spaced Retrieval Universality negative example).

---

## 4. OMLX/MLX ECOSYSTEM DEVELOPMENTS

### 4.1 OMLX v0.5.x (Current)
- Continuous batching support (needs verification for temp=0.0)
- SSD caching for KV-cache
- OpenAI-compatible API

### 4.2 vllm-mlx
- 400+ tok/s on Apple Silicon
- Continuous batching with MCP tool calling
- Multimodal support (vision + language)
- Could serve as OMLX alternative if OMLX batching has issues

### 4.3 mlx-manager
- KV cache optimization
- Parallel processing support
- Smaller project (⭐14) but focused on the exact use case

### 4.4 Upcoming MLX Features to Track
- **Speculative decoding on MLX:** Not yet available, but would enable 2-3x speedup for autoregressive generation
- **Model parallelism across multiple Apple Silicon devices:** Not relevant for single-machine 64GB
- **FlashAttention-3 for MLX:** Would reduce memory for large context windows

---

## 5. RECOMMENDED ACTIONS (PRIORITIZED)

| Priority | Action | Speedup | Quality Risk | Effort |
|----------|--------|---------|-------------|--------|
| **P0** | Enable OMLX continuous batching for S2 | 4-8x | Low (if temp=0.0 compatible) | Medium |
| **P0** | KV-cache prefix sharing for S2 system prompt | 20-30% | None | Low |
| **P0** | Pipeline parallelism (S2 + S4 concurrent) | 1.4-1.8x | None | Medium |
| **P1** | Merge S4 CRIBS + Classification (1 call) | 45% of S4 | Needs A/B test | Low |
| **P1** | A/B test Qwen3-Coder-8B vs 30B for S2 | 3-4x | Unknown | Medium |
| **P1** | Author-aware BORP (source independence) | N/A (accuracy) | None | Low |
| **P2** | Cross-cluster dedup via Leiden | ~15% fewer FBs | Low | Medium |
| **P2** | Dynamic golden example selection | N/A (accuracy) | None | Low |
| **P2** | Weighted NLI entailment | N/A (accuracy) | Low | Low |
| **P3** | Skip CRIBS for high-quality FBs | 30-50% of S4 CRIBS | Needs A/B test | Low |
| **P3** | Iterative refinement for contentious FBs | N/A (yield) | Low | Medium |

## 6. TOTAL POTENTIAL SPEEDUP

| Scenario | S2 | S4 | S5 | Total | % of Current |
|----------|----|----|----|----| ---|
| Current | 13.3h | 14.8h | 2.1h | 30.2h | 100% |
| + Batching (4x S2) | 3.3h | 14.8h | 2.1h | 20.2h | 67% |
| + KV Cache (25% S2) | 2.5h | 14.8h | 2.1h | 19.4h | 64% |
| + Pipeline Parallel (1.5x) | — | — | — | 12.9h | 43% |
| + Merge CRIBS+Classify (45% S4) | 2.5h | 8.1h | 2.1h | 8.5h | 28% |
| + Smaller S2 model (3x) | 0.8h | 8.1h | 2.1h | 6.8h | 23% |
| **Conservative (no model swap):** | | | | **~8.5h** | **28%** |
| **Aggressive (all optimizations):** | | | | **~6.8h** | **23%** |

**Bottom line:** From 30h → ~8h is achievable with existing tools (OMLX batching + pipeline parallelism + merged calls). The 6.8h aggressive target requires validating Qwen3-Coder-8B quality parity.

---

## 7. KEY RISKS & VERIFICATION

1. **OMLX continuous batching + temp=0.0:** Must verify deterministic outputs with batched inference. Some batching implementations introduce non-determinism from parallel scheduling.
2. **Qwen3-Coder-8B quality:** The 30B MoE model has 3B active params — the 8B dense model might actually be MORE capable for structured extraction. Must A/B test.
3. **Merged CRIBS+Classify prompt complexity:** 10 output fields in one JSON. Risk of field confusion or omission. Structured JSON output (D2219) mitigates this.
4. **Pipeline parallelism race conditions:** S4 must wait for S2 to finish on the SAME FB. Queue management needed.
