# Maxwell OS — Aggregated Remaining Tasks (Post D2205 RAG Architecture Roadmap)
> **Updated:** 2026-08-06 17:20 | **Source:** D2195-D2205 + 4-model cross-examination + all prior sessions
> **Total remaining:** 37 tasks across 4 tiers
> **Recently completed:** D2195-D2204 (12 immediate fixes), D2205 roadmap published
> **Next decision range:** D2206+

---

## 🏆 TIER 0 — CRITICAL PATH (This Week)

These tasks directly implement the D2205 RAG Architecture Roadmap. They are the **retrieval-to-agentic bridge** that turns Maxwell from a knowledge extraction engine into an evidence-grounded knowledge system.

| # | Task | Phase | Effort | Why | Status |
|---|------|-------|--------|-----|--------|
| **T0.1** | **Build retrieval evaluator** (`pipeline/retrieval_evaluator.py`) — CRAG-style critique with structured JSON output (CORRECT/PARTIAL/INCORRECT/CONTRADICTORY) | P0 | 0.5d | Single highest-impact change. Reuses Phi-4-mini. No new deps. | ⬜ TODO |
| **T0.2** | **Build agentic retrieval loop** (`retrieve.py:agentic_search()`) — iteration budget (3 rounds), stop conditions, EvidencePack output | P0 | 0.5d | Makes every query better without pipeline changes. Reuses existing retrieve.py. | ⬜ TODO |
| **T0.3** | **Build graph traversal layer** (`retrieve.py:graph_expand()`) — BFS over SQLite adjacency list for `related_fbs`, `contradicts_fbs`, `prerequisite_fbs` | P1 | 1.0d | Activates data already stored but never queried. Zero new deps. | ⬜ TODO |
| **T0.4** | **Build graph-aware search** (`retrieve.py:graph_aware_search()`) — hybrid search + graph expansion + reranking | P1 | 0.5d | Combines T0.1+T0.3. Surfaces contradictions alongside support. | ⬜ TODO |
| **T0.5** | **Run S1.3→S6 pipeline** — first full pipeline run with bge-m3 512d embeddings | — | 4h | S0 (922 MDs) + S1 (323K segments) done. S1.3–S6 need first run. | ⬜ TODO |
| **T0.6** | **Yield crisis diagnostic** — manual extract 10 principles from 1 book, compare vs pipeline output (14 FBs from 852 books = 0.004% yield) | — | 1d | Pipeline emergency. Cross-encoder reranker gate may rescue yield (Qwen proposal). | ⬜ TODO |

---

## 🟠 TIER 1 — HIGH (This Sprint)

### D2205 Roadmap Implementation (continued)

| # | Task | Phase | Effort | Why | Status |
|---|------|-------|--------|-----|--------|
| **T1.1** | **MCP server** (`maxwell_mcp_server.py`) — 3 tools: query_knowledge, get_fb_detail, get_fb_reliability | P2 | 1.0d | Immediate integration with Goose, Claude Code, Cursor. No custom agent harness needed. C25 compliance. | ⬜ TODO |
| **T1.2** | **Two-axis epistemic model** — migration: `evidence_support`, `evidence_independence`, `evidence_contradiction`, `evidence_coverage`, `execution_trials`, `execution_successes`, `epistemic_state` | P3 | 1.0d | Replaces ambiguous scalar confidence_score. Distinguishes source-backed from execution-validated. | ⬜ TODO |
| **T1.3** | **EvidencePack dataclass integration** — wire through retrieve→critique→format pipeline | P3 | 0.5d | Typed evidence reduces agentic hallucination. All components consume/produce same object. | ⬜ TODO |
| **T1.4** | **Migration script** (`pipeline/migrate_D2205_epistemic.py`) — crash-safe schema addition with backfill | P3 | 0.5d | C6: tempfile → fsync → os.replace. Idempotent. | ⬜ TODO |

### Pipeline Quality & Calibration

| # | Task | Effort | Why | Status |
|---|------|--------|-----|--------|
| **T1.5** | **NLI calibration on real data** — validate thresholds (0.5/0.6/0.8) against bge-m3 embeddings | 2h | `nli_calibrate.py` exists. Thresholds unvalidated on current embedding model. | ⬜ TODO |
| **T1.6** | **Cross-encoder reranker gate** — insert `bge-reranker-v2-m3` (ONNX) between Stage 2 and Stage 5 to rescue yield | 1d | Qwen proposal: reranker score > 0.75 → proceed to Stage 5. Trade-off: 1.2GB VRAM. Unload embed model during reranking. | ⬜ TODO |
| **T1.7** | **Run LLM evaluation on expanded golden set (25 examples)** — use `config/golden/GOLDEN-EVALUATION-PROMPT.md` with 2+ LLMs | 2h | Golden set is `needs_review` — pipeline must NOT calibrate on unverified ground truth. | ⬜ TODO |
| **T1.8** | **Calibrate golden set after eval** — fix flaws, set thresholds (NLI entailment, BORP min sources) | 4h | Calibration gate for Stage 2 extract quality. | ⬜ TODO |

### Fixes & Integrity

| # | Task | Effort | Why | Status |
|---|------|--------|-----|--------|
| **T1.9** | **Fix faiss_threshold mismatch** — `pipeline_config.yaml:0.75` vs `session_seed.yaml:0.70`. Make session_seed REFERENCE pipeline_config, not copy. | 0.5h | Two semantic definitions of cluster similarity = silent corruption. | ⬜ TODO |
| **T1.10** | **Fix AGENTS.md stage count** — still says "9-stage" despite Stage 3 removal (D2120). Generate from canonical pipeline_config. | 0.5h | Agent-control-plane integrity defect. Different docs = different instructions to agents. | ⬜ TODO |
| **T1.11** | **Auto-fix Ruff lint errors in pipeline/** — 322 auto-fixable, ~154 manual remaining | 1h | D2201 removed exclusion but errors weren't fixed. | ⬜ TODO |
| **T1.12** | **Source-independence graph** — model citation chains (A cites B) → `effective_source_count` for BORP | 1d | ChatGPT §8: 4 books citing 1 source = 1 source family, not 4 independent sources. | ⬜ TODO |

---

## 🟡 TIER 2 — MEDIUM (Next Sprint)

### Agentic & Execution Infrastructure

| # | Task | Effort | Why | Source |
|---|------|--------|-----|--------|
| **T2.1** | **Execute ONE business PI with existing FBs** — existential test: can FBs produce a useful action? | 2h | Qwen's "test the bridge" mandate. If FBs can't close a deal or write a proposal, nothing else matters. | Qwen, Kimi |
| **T2.2** | **Atomic evidence schema** — per-passage NLI scores instead of majority vote aggregation | 2d | ChatGPT C9: one contradiction on a critical condition should force CONTESTED even if 6 other passages support. | ChatGPT C9 |
| **T2.3** | **Monotonic trust state machine** — DB-level transition constraints: RAW→PARSED→CHUNKED→CLUSTERED→EXTRACTED→VERIFIED→CANONICAL→RELIABLE→RETIRED | 2d | ChatGPT C7, Kimi P5: prevents BUG class where FAILED→PASS via lost classification_status. SQLite CHECK constraints. | ChatGPT C7 |
| **T2.4** | **Surface reliability scores in Zone 3** — context-conditioned reliability: `reliability(domain, company_size, market)` | 1d | DeepSeek §4.5: FB may work in B2B SaaS but fail in enterprise. Scalar masks this. | DeepSeek, Kimi K3 |
| **T2.5** | **Implement skill.md standard (Layer 2 MVP)** — IBM production-proven progressive disclosure | 4h | Foundation for procedure templates (PT) and process instances (PI). | aggregated |
| **T2.6** | **Hardware probe (C24)** — auto-detect RAM/CPU, select model quant dynamically | 3h | M1 Max 64GB is current target but must degrade gracefully on 16GB/32GB. | aggregated |

### Testing & Quality

| # | Task | Effort | Why | Source |
|---|------|--------|-----|--------|
| **T2.7** | **20-book E2E test** — validate v3.0 at scale | 3h | Thresholds configurable via e2e.* config. | aggregated |
| **T2.8** | **Integration test suite** — `just test` golden-file regression tests | 4h | Prevents retrieval regressions. | aggregated |
| **T2.9** | **Adversarial golden set** — contradiction tests, false convergence tests, same-source duplicates, citation-chain duplicates | 2d | ChatGPT §41: clusterer should not produce "Discounting increases conversion" from conflicting sources. | ChatGPT §41 |
| **T2.10** | **RAGTruth-inspired hallucination suite** — unsupported claim, partial support, contradictory evidence, source laundering, causal leap tests | 1d | ChatGPT §14: 18,000 manually annotated responses show RAG ≠ hallucination solution. | ChatGPT §14 |
| **T2.11** | **ARES-style component evaluation** — context relevance, answer faithfulness, answer relevance with human-calibrated automated judges | 1d | ChatGPT §40: evaluate each component independently. | ChatGPT §40 |

### Configuration & Governance

| # | Task | Effort | Why | Source |
|---|------|--------|-----|--------|
| **T2.12** | **One pipeline authority** — machine-readable canonical DAG → generated AGENTS.md, session_seed.yaml, diagrams | 1d | ChatGPT §3: different documents are instructions to agents. Must derive from one source. | ChatGPT §3 |
| **T2.13** | **Split config into active/archived/experiments** — prevent config ghosts | 1d | `pipeline_config.yaml` has legacy v2.3 blocks. | ChatGPT C13 |
| **T2.14** | **Collapse config authority** — one canonical YAML per domain | 1d | Current: pipeline_config.yaml + model_assignments.yaml + session_seed.yaml + config/*.yaml. Redundant. | ChatGPT C15 |
| **T2.15** | **Prompt lineage stamping** — prompt_id, prompt_hash, prompt_version on all LLM calls | 1d | Enables "which prompt produced this FB?" traceability. | ChatGPT C16 |
| **T2.16** | **Move taxonomy from hardcoded Literal to YAML-driven** | 2d | Complete the migration started with taxonomy_v5.yaml. C12 compliance. | DeepSeek D5 |

---

## ⚪ TIER 3 — LOW (Backlog, 6-8 Weeks)

### Efficiency & Scale

| # | Task | Effort | Why | Source |
|---|------|--------|-----|--------|
| **T3.1** | **Benchmark USearch vs FAISS** — 10x faster on Apple Silicon per feed.opml | 2h | Clustering bottleneck if corpus grows. | aggregated |
| **T3.2** | **Evaluate MeshRAG hash-driven clustering** — LSH hash collisions replace FAISS similarity | 1d | ACL 2026: 10,000+ chunks in minutes, no GPU. Directly addresses embedding bottleneck. | DeepSeek §4.4 |
| **T3.3** | **Leiden clustering via python-igraph** — replace NetworkX Louvain ($O(N^2)$) | 2h | Qwen: Leiden is seconds vs hours for Louvain on dense graphs. | Qwen Q5 |
| **T3.4** | **Schema migration scripts** — v2.x FBs → v3.0 schema. Recover v1's 19,863 FBs. | 3h | Lost knowledge from v1 pipeline. | aggregated |

### Advanced Retrieval

| # | Task | Effort | Why | Source |
|---|------|--------|-----|--------|
| **T3.5** | **HyDE for abstract queries** — generate hypothetical document, embed, use neighborhood for retrieval | 1d | ChatGPT §20: useful for abstract conceptual queries. NOT for exact lookup. | ChatGPT §20 |
| **T3.6** | **Multi-perspective retrieval** — generate retrieval perspectives (economic, behavioral, operational, risk, counterexample), merge at evidence level | 1d | ChatGPT §32: STORM-inspired. Critical: merge at evidence level, not conclusion level. | ChatGPT §32 |
| **T3.7** | **ColBERT benchmark** — late interaction vs dense+reranker on Maxwell's actual corpus | 1d | ChatGPT §22: only adopt if recall ↑ and latency acceptable on M1 Max. | ChatGPT §22 |

### Layer 2 Foundation

| # | Task | Effort | Why | Source |
|---|------|--------|-----|--------|
| **T3.8** | **Pydantic AI harness** — agent orchestration framework | 1w | Alternative to building custom agent harness. Pydantic AI has built-in MCP client. | Kimi K14 |
| **T3.9** | **Agent execution safety boundary** — Plan→Policy→Auth→Execute→Rollback | 3d | Required before Layer 2 goes live. Sandbox execution. | ChatGPT C14 |
| **T3.10** | **Dry-run mode on all stages** — "Would process X books → Y chunks → Z clusters → N LLM calls" | 4h | Operator visibility before committing compute. | aggregated |
| **T3.11** | **Modularize stage2_extract (1,480 lines) + stage4_merge (1,260 lines)** — split into typed components | 3d | Maintainability. God modules accumulate bugs. | Kimi K5 |

---

## 🔵 TIER 4 — RESEARCH (Ongoing)

These are from weekly research synthesis (D2116 feed.opml) and advanced architecture exploration.

| # | Foundation | Weekly Research Refinement | Status |
|---|-----------|---------------------------|--------|
| **R1** | Typed Graph Storage | Evaluate Zep/Graphiti for temporal provenance. Neo4j only if SQLite adjacency list hits scale limit. | ⬜ DEFERRED |
| **R2** | Edge Type Ontology | 10-15 edge types with formal properties (transitivity, symmetry). Machine-checkable. | ⬜ DEFERRED |
| **R3** | Skill Subgraph Templates | Start with skill.md (T2.5). Graduate to graph when 50+ skills. | ⬜ DEFERRED |
| **R4** | Constitutional Constraint Graph | C1-C28 as graph invariants. `validate_all_constraints(graph)` → violations. | ⬜ DEFERRED |
| **R5** | Self-Observation Protocol | OBSERVATION nodes. Agent queries own graph. "Forgetting is an engineering problem." | ⬜ DEFERRED |
| **R6** | Study IBM course transcript for Layer 2 | 3-module structure maps 1:1 to Maxwell needs | ⬜ DEFERRED |
| **R7** | Implement GAAMA 4-node memory | Episodes + facts + reflections + concepts | ⬜ DEFERRED |
| **R8** | Evaluate `awesome-agent-skills` repo | Accelerates skill.md adoption | ⬜ DEFERRED |
| **R9** | Evaluate `caveman` prompt framework | Local-first prompt engineering for Stage 2 | ⬜ DEFERRED |
| **R10** | Evaluate vLLM-mlx for multi-agent execution | Continuous batching on Apple Silicon. Deferred: OMLX is adequate for single-agent. | ⬜ DEFERRED |
| **R11** | Consider LanceDB as unified vector+metadata store | If sqlite-vec hits scale limits. | ⬜ DEFERRED |
| **R12** | ONNX runtime for NLI | Only if ModernBERT proves too heavy. Current memory: ~500MB, acceptable. | ⬜ DEFERRED |

---

## OPEN BUGS (from buglog.md)

| Bug ID | Severity | Description | Status |
|--------|----------|-------------|--------|
| BUG-001 | 🔴 CRITICAL | Empty pass loop — verification checks random principles | 🔴 OPEN — Phase 0, P0.8 |
| BUG-053 | 🔴 CRITICAL | Phi-4-mini-instruct-8bit HALLUCINATES on open-ended research tasks | 🔴 OPEN — Mitigated in D2205 P0 by using classification only (text provided) |
| BUG-054 | 🔴 CRITICAL | Qwen3-Coder-30B delegate fails — OMLX JSON parse error | 🔴 OPEN |
| BUG-055 | 🔴 CRITICAL | `related_fbs` vs `related_blocks` field name mismatch across pipeline | 🔴 OPEN — Blocks all delegation |
| BUG-051 | 🟡 MED | `just smoke` processes ALL 852 books instead of 1 | 🟡 OPEN |
| BUG-045 | 🟡 MED | Stage 2 evidence passages inflated — all cluster segments included | 🟡 OPEN — Deferred, metadata issue |
| BUG-046 | 🟡 MED | Stage 4 merge complexity for v3.0 | 🟡 OPEN |
| BUG-050 | 🟡 MED | Only 3 of 20 books chunked — insufficient for meaningful convergence | 🟡 OPEN — Next: chunk 5+ books |
| — | 🟡 MED | Anytype cloud-sync sovereignty leak (`stage6b_anytype_push.py` exists) | ⬜ ACKNOWLEDGED |
| — | 🟡 MED | `omlx_watchdog.log` (430 bytes) committed despite .gitignore | ✅ FIXED (D2203) |

---

## IMMEDIATE NEXT ACTIONS

```bash
# 1. Fix threshold mismatch (T1.9)
# Edit agent/session_seed.yaml: change threshold: 0.70 → reference pipeline_config.yaml

# 2. Fix AGENTS.md stage count (T1.10)
# Edit AGENTS.md: "9-stage" → "8-stage" (or generate from pipeline_config.yaml)

# 3. Run preflight
just preflight

# 4. Build retrieval evaluator (T0.1)
# Create pipeline/retrieval_evaluator.py per D2205 spec

# 5. Run first full pipeline (T0.5)
python3 pipeline/runner.py --from-stage 1_3

# 6. Build agentic + graph retrieval (T0.2-T0.4)
# Add agentic_search(), graph_expand(), graph_aware_search() to retrieve.py
```

---

## COMPLETED (D2195-D2204)

| # | Task | Decision |
|---|------|----------|
| ✅ | Zero-vector fallback → EmbeddingQuarantineError | D2196 |
| ✅ | LICENSE (MIT) | D2200 |
| ✅ | session_seed.yaml sync (NLI, stage3, 8-stage) | D2197 |
| ✅ | model_assignments.yaml sync (REVIEWER, S5_FB_VERIFIER) | D2199 |
| ✅ | stage6_commit INSERT 49→48 column fix | D2203 |
| ✅ | AGENTS.md + architecture docs stage3 purge | D2198 |
| ✅ | Ruff/mypy pipeline exclusion removed | D2201 |
| ✅ | ollama import removed → batch_embed delegation | D2202 |
| ✅ | just preflight exit bug fixed | D2203 |
| ✅ | integrity_check.py 17 checks (17/17 pass) | D2203 |
| ✅ | requirements.lock deterministic | D2203 |
| ✅ | watchdog log + .DS_Store purged | D2203 |
| ✅ | Golden set 10→25 (full properties, 21 domains, 5 negatives) | D2204 |
| ✅ | Master LLM eval prompt v2.0 | D2204 |
| ✅ | D2205 RAG Architecture Roadmap published | D2205 |

---

## TOKEN BUDGET NOTE (D2205 Agentic Loop)

```
Agentic retrieval overhead vs classic:
- CORRECT retrieval:    1× tokens (single pass + critique)
- PARTIAL retrieval:    2-3× tokens (2-3 iterations)
- INCORRECT retrieval:  2× tokens (fallback to broader search)
- CONTRADICTORY:        2× tokens (surface both sides)

Best practice (Agentic RAG 2026):
- Apply agentic retrieval on complex, multi-hop, or ambiguous queries
- Use single-shot search_hybrid for simple factual lookups
- Hard cap at 3 iterations with explicit exhausted flag
```
