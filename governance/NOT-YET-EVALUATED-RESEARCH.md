# Maxwell OS — Not-Yet-Evaluated Research Opportunities
> **Date:** 2026-08-09 | **Source:** feed.opml + senior RAG developer assessment
> **Status:** Fresh opportunities — none rejected, none tested

---

## 🔴 P1 — Implement Now (validated, low risk)

| # | Technology | What | Stage | Gain | Risk | Effort |
|---|-----------|------|-------|------|------|--------|
| **R-01** | Prompt trimming | Remove redundant CRIBS editing rules | S4 | 19% input tokens saved (233 chars) | ✅ NONE — same semantics | ✅ IMPLEMENTED |
| **R-02** | Structured JSON output | OMLX `response_format: json_object` | S2/S4/S5 | Fewer JSON repairs, faster parsing | ⚠️ Needs A/B test | 1h |
| **R-03** | llmfit preflight | Hardware-model fit check in `just preflight` | DevEx | Model selection quality | ✅ NONE — read-only | ✅ ADDED |

---

## 🟡 P2 — Benchmark Required

| # | Technology | What | Stage | Potential Gain | Current Status | Effort |
|---|-----------|------|-------|---------------|----------------|--------|
| **R-04** | USearch | SIMD NEON FAISS replacement | S1.5 clustering | 10x search speed | ⭐4,216 GH. Deferred T3.1. NEVER benchmarked on Maxwell corpus. | 3h |
| **R-05** | TurboVec integration | Quantized search accelerator | S1.5 k-NN, retrieval | 4-8x search speed | ✅ Installed (v0.8.0). NOT wired into pipeline. | 2h |
| **R-06** | LightRAG evaluation | Graph-based RAG, EMNLP2025 | FB retrieval | Better recall via graph traversal | ⭐37,713 GH. EMNLP2025 paper. NOT tested on Maxwell FB corpus. | 1d |
| **R-07** | Merged CRIBS+Classification | Single LLM call for both tasks | S4 | 73% token savings (2M tokens/S4 run) | ⚠️ Needs A/B quality test first | 3h |

---

## 🔵 P3 — Research / Monitor

| # | Technology | What | Stage | Why Deferred |
|---|-----------|------|-------|-------------|
| **R-08** | LEANN | 97% storage savings RAG | FB retrieval | MLsys2026. Needs benchmarking on M1 Max. |
| **R-09** | memvid | Agent memory layer (serverless) | Agent harness | ⭐15,901. Knowledge graph support. Evaluated for Maxwell agent, not pipeline. |
| **R-10** | zvec | Alibaba embedded vector DB | Persistent vectors | ⭐14,942. HNSW, embedded. May replace FAISS for storage. |
| **R-11** | SiliconScope | Apple Silicon native monitor | System diagnostics | ⭐802. ANE/Memory-bandwidth tracking. Diagnostic only. |
| **R-12** | Prompt caching | Cache system prompts across calls | S4 | ~500 tokens saved per FB | Depends on OMLX caching support. NOT verified. |
| **R-13** | Token-efficient prompt patterns | Systematic prompt optimization | All stages | 10-30% across pipeline | Requires per-stage analysis. |

---

## ❌ Already Evaluated & Rejected

| Technology | Why Rejected | Source |
|-----------|-------------|--------|
| Cloud burst (GPT-4o-mini) | C1/C3 violation | Kimi |
| LangChain/LlamaIndex | C2 vendor lock-in | D2010 |
| Microsoft GraphRAG | Cloud-native | D2118 |
| LanceDB/DuckDB | SQLite adequate (C5) | D2048 |
| Dagster/Prefect | PipelineRunner <300 LOC | D2061 |
| Full Pydantic migration | Schema accessors sufficient | D2120 |
| Leiden algorithm | Louvain adequate. Revisit at scale. | Kimi |
| OpenFActScore | Overengineered | Kimi |
| Self-RAG training | C1 + R7 temp=0.0 | D2205 |
| CRAG web search | C3 sovereignty | D2205 |
| ColBERT late interaction | M1 Max memory | D2205 |
| Multi-agent swarm | 39-70% coordination tax | D2205 |
| Neo4j graph database | C3 external service | D2205 |
| Rapid-MLX | HF network cache issue (C1/C3 violation) | feed.opml eval |
| MTPLX | M5 TensorOps required, M1 benefit minimal | feed.opml eval |
| CIDER | INT8 TensorOps only on M5+ | feed.opml eval |

---

## Implementation Log

| Date | Item | Action |
|------|------|--------|
| 2026-08-09 | R-01 (Prompt trimming) | ✅ IMPLEMENTED — 233 chars removed from CRIBS_ENRICHMENT_SYSTEM (19%) |
| 2026-08-09 | R-03 (llmfit preflight) | ✅ ADDED to just preflight |
| 2026-08-09 | R-02 (Structured JSON) | ⬜ PENDING A/B test |
| 2026-08-09 | R-07 (Merged CRIBS+Classify) | ⬜ PENDING A/B test |
