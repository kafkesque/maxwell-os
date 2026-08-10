# Maxwell OS v3.0 — MASTER TASK REGISTER
> **Updated:** 2026-08-10 21:15 | **Decisions:** D2000-D2249 (230 decisions)
> **Active roadmap:** D2205 — RAG Architecture Roadmap (4-model cross-examination synthesis)
> **Latest session:** D2245-D2249 (GPT-OSS model research, T-009 author cap, A-002/A-004, 4-way S2 comparison)
> **Detailed tasks:** `governance/aggregated_remaining_tasks.md` (session-complete register: 3 critical, 16 high, 16 medium, 5 low)
> **Buglog:** `governance/buglog.md` (BUG-058 panic MITIGATED, BUG-074 MITIGATED, BUG-075 OPEN — cross-domain depth)
> **S2 Comparison (D2248):** DSPy-MIPROv2 **0.672** vs Traditional **0.592** on 20 examples (5/5 negatives vs 0/5)
> **S4 Depth (D2245):** GPT-OSS-20B **62.5%** @ 5.8s/call (24.9× faster than Gemma-4-31B 50%) — registered in OMLX
> **Pipeline:** S0 ✅ | S1 ✅ | S1.5 ✅ | S2 ✅ (DSPy harness T-007 DONE, 96.4% pilot) | S4 ready (GPT-OSS pending BUG-075)
> **Tier 0 fixes:** Fix 0.1-0.4 still pending (see aggregated_remaining_tasks.md T1.x)

---

## 🔥 ACTIVE — D2205 RAG ARCHITECTURE ROADMAP (2026-08-06)

> **Full spec:** `governance/D2205-rag-architecture-roadmap-2026-08-06.md` (1,091 lines)
> **Source:** Cross-examination of Kimi, DeepSeek, Qwen, ChatGPT eval13 + codebase verification
> **Verdict:** Ingestion pipeline = 8/10, Retrieval layer = 5/10 → build 4-phase bridge

### P0 — Agentic Retrieval Loop (Week 1)

| # | Task | Effort | Status |
|---|------|--------|--------|
| **D2205-P0.1** | **Retrieval evaluator** — `pipeline/retrieval_evaluator.py`. CRAG-style critique: CORRECT/PARTIAL/INCORRECT/CONTRADICTORY. Uses Phi-4-mini (local). Structured JSON output. | 0.5d | ✅ DONE (511 lines) |
| **D2205-P0.2** | **Agentic retrieval loop** — `retrieve.py:agentic_search()`. Iteration budget (3 rounds). Stop conditions: confidence≥0.85, CORRECT, or exhausted. EvidencePack output. | 0.5d | ✅ DONE (retrieve.py:613) |

### P1 — Graph Traversal Layer (Week 1-2)

| # | Task | Effort | Status |
|---|------|--------|--------|
| **D2205-P1.1** | **Graph expansion** — `retrieve.py:graph_expand()`. BFS over SQLite adjacency list. Traverses `related_fbs`, `contradicts_fbs`, `prerequisite_fbs`. Zero new deps. | 1.0d | ✅ DONE (retrieve.py:326) |
| **D2205-P1.2** | **Graph-aware search** — `retrieve.py:graph_aware_search()`. Hybrid search + graph expansion + rerank by borp×feedback×graph_centrality. | 0.5d | ✅ DONE (retrieve.py:467) |

### P2 — MCP Server (Week 2)

| # | Task | Effort | Status |
|---|------|--------|--------|
| **D2205-P2.1** | **MCP knowledge server** — `maxwell_mcp_server.py`. 3 tools: query_knowledge, get_fb_detail, get_fb_reliability. Read-only. Stateless. Stdio transport. | 1.0d | ⬜ TODO |

### P3 — Evidence Pack & Two-Axis Epistemic Model (Week 2-3)

| # | Task | Effort | Status |
|---|------|--------|--------|
| **D2205-P3.1** | **Two-axis epistemic migration** — Schema: evidence_support, evidence_independence, evidence_contradiction, evidence_coverage, execution_trials, execution_successes, epistemic_state. Backfill from existing data. | 1.0d | ⬜ TODO |
| **D2205-P3.2** | **EvidencePack dataclass** — Wire through retrieve→critique→format pipeline. Every component consumes/produces same typed object. | 0.5d | ⬜ TODO |
| **D2205-P3.3** | **Migration script** — `pipeline/migrate_D2205_epistemic.py`. Crash-safe (C6). Idempotent. | 0.5d | ⬜ TODO |

### D2205 Gates

| Gate | Test | Target |
|------|------|--------|
| P0 gate | Agentic search on 10 golden queries | ≥15% recall improvement on multi-aspect queries |
| P1 gate | Graph-aware vs flat search on 10 complex queries | ≥3 additional relevant FBs via graph expansion |
| P2 gate | Goose/Claude Desktop query "what does maxwell know about X?" | All 3 tools return valid results |
| P3 gate | `PRAGMA table_info(fbs)` shows new columns | Migration verified + EvidencePack round-trip |

### D2205 Rejected Proposals (with reasons)

| Proposal | Why Rejected |
|:---------|:-------------|
| Full Self-RAG with reflection tokens | Requires training (C1). temp=0.0 blocks beam search (R7). |
| CRAG web search fallback | Data leaves machine (C3). Replaced with broader local retrieval. |
| ColBERT late interaction | Memory-prohibitive on M1 Max with other models loaded. |
| Full RAPTOR hierarchy on all chunks | 564 min for flat embedding already. Recursive = weeks. |
| vllm-mlx migration | "1 day" estimate unrealistic. Deferred to P4 backlog. |
| Multi-agent swarm | Coordination tax 39-70%. M1 Max can't run 5+ agents × models. |
| Neo4j graph database | External service (C3). SQLite adequate for 4K-6K FBs. |
| LangChain/LlamaIndex | Vendor lock-in (C2). Maxwell's pipeline is cleaner. |

---

## 🔥 TIER 0 — EMERGENCY FIXES (Session 2026-08-09)

> **Source:** 5-review cross-examination + comprehensive pipeline audit
> **Spec:** `governance/SESSION-HANDOFF-2026-08-09.md` §10
> **Decisions:** D2213-D2218

| # | Fix | File | Effort | Status |
|---|-----|------|--------|--------|
| **Fix 0.1** | Conditionalize application prompt — allow null for descriptive FBs | `stage4_merge.py` L71, L131 | 5min | ⬜ TODO |
| **Fix 0.2** | Forward mechanism/boundary/consequence to S4 output dict | `stage4_merge.py` L1093+ | 5min | ⬜ TODO |
| **Fix 0.3** | Delete dead multi-FB merge path + add assert (backup: `.backup-20260809`) | `stage4_merge.py` L65-116,172-184,872-884 | 10min | ⬜ TODO |
| **Fix 0.4** | Align NLI scoring to MAX-entailment (match governance benchmark) | `stage5_verify.py` L217-229 | 10min | ⬜ TODO |

### Post-Fix Execution
```bash
just health
python3 pipeline/stage2_extract.py --only-convergent  # ~19h async
# After S2: python3 pipeline/stage4_merge.py && python3 pipeline/stage5_verify.py
```

### New Tasks from Audit (D2213-D2218)
| # | Task | Priority |
|---|------|----------|
| N2 | Add mechanism/boundary/consequence to Pydantic FB model | 🟠 P1 |
| N3 | Add actionability field (descriptive/prescriptive/diagnostic) | 🟠 P1 |
| N6 | Swap DeBERTa FEVER to primary NLI | 🟠 P1 |
| N9 | Two-stage S4: separate classification from CRIBS | 🔵 v3.1 |
| N10 | Kimi depth confidence signal | 🔵 v3.1 |
| N14 | Profile max_workers=5 memory impact for S2 | 🟡 P2 |

---

## 🟠 TIER 1 — HIGH (This Sprint, Non-D2205)

### Pipeline Critical Path

| # | Task | Effort | Status |
|---|------|--------|--------|
| **T1.1** | **Run S1.3→S6 pipeline** — first full run with bge-m3 512d. S0 (922 MDs) + S1 (323K segments) done. | 4h | ⬜ TODO |
| **T1.2** | **Yield crisis diagnostic** — manual extract 10 principles from 1 book vs pipeline. 14 FBs from 852 books = 0.004% yield. | 1d | ⬜ TODO |
| **T1.3** | **NLI calibration on real data** — validate thresholds (0.5/0.6/0.8) against bge-m3. `nli_calibrate.py` exists. | 2h | ⬜ TODO |

### Fixes

| # | Task | Effort | Status |
|---|------|--------|--------|
| **T1.4** | **Fix faiss_threshold mismatch** — pipeline_config.yaml:0.75 vs session_seed.yaml:0.70. Make session_seed reference config, not copy. | 0.5h | ⬜ TODO |
| **T1.5** | **Fix AGENTS.md stage count** — still says "9-stage" despite Stage 3 removal. Generate from canonical pipeline_config. | 0.5h | ⬜ TODO |
| **T1.6** | **Auto-fix Ruff lint errors** — 322 auto-fixable in pipeline/. | 1h | ⬜ TODO |
| **T1.7** | **Run LLM evaluation on golden set (25 examples)** — use 2+ LLMs. Golden set is `needs_review`. | 2h | ⬜ TODO |

### Quality

| # | Task | Effort | Status |
|---|------|--------|--------|
| **T1.8** | **Cross-encoder reranker gate** — `bge-reranker-v2-m3` ONNX between S2 and S5. Rescues yield crisis. Trade-off: 1.2GB VRAM. | 1d | ⬜ TODO |
| **T1.9** | **Source-independence graph** — model citation chains. effective_source_count for BORP. | 1d | ⬜ TODO |

---

## 🟡 TIER 2 — MEDIUM (Next Sprint)

| # | Task | Effort | Source |
|---|------|--------|--------|
| T2.1 | Execute ONE business PI with existing FBs — existential test | 2h | Qwen, Kimi |
| T2.2 | Atomic evidence schema — per-passage NLI, not majority vote | 2d | ChatGPT C9 |
| T2.3 | Monotonic trust state machine — DB-level transition constraints | 2d | ChatGPT C7 |
| T2.4 | Surface reliability scores in Zone 3 — context-conditioned | 1d | DeepSeek, Kimi |
| T2.5 | skill.md standard (Layer 2 MVP) — IBM progressive disclosure | 4h | aggregated |
| T2.6 | Hardware probe (C24) — auto-detect RAM, select model quant | 3h | aggregated |
| T2.7 | 20-book E2E test — validate v3.0 at scale | 3h | aggregated |
| T2.8 | Integration test suite — `just test` golden-file regression | 4h | aggregated |
| T2.9 | Adversarial golden set — contradiction, false convergence tests | 2d | ChatGPT §41 |
| T2.10 | RAGTruth hallucination suite — 10 adversarial test types | 1d | ChatGPT §14 |
| T2.11 | ARES component evaluation — per-component metrics | 1d | ChatGPT §40 |
| T2.12 | One pipeline authority — canonical DAG → generated docs | 1d | ChatGPT §3 |
| T2.13 | Split config into active/archived/experiments | 1d | ChatGPT C13 |
| T2.14 | Collapse config authority — one canonical YAML per domain | 1d | ChatGPT C15 |
| T2.15 | Prompt lineage stamping — prompt_id, prompt_hash, prompt_version | 1d | ChatGPT C16 |
| T2.16 | Move taxonomy from hardcoded Literal to YAML-driven | 2d | DeepSeek D5 |

---

## ⚪ TIER 3 — LOW (Backlog, 6-8 Weeks)

| # | Task | Effort | Source |
|---|------|--------|--------|
| T3.1 | USearch vs FAISS benchmark | 2h | aggregated |
| T3.2 | MeshRAG hash-driven clustering eval | 1d | DeepSeek |
| T3.3 | Leiden clustering via python-igraph | 2h | Qwen |
| T3.4 | Schema migration scripts — v2.x → v3.0, recover v1 FBs | 3h | aggregated |
| T3.5 | HyDE for abstract queries | 1d | ChatGPT §20 |
| T3.6 | Multi-perspective retrieval (STORM-inspired) | 1d | ChatGPT §32 |
| T3.7 | ColBERT benchmark on Maxwell corpus | 1d | ChatGPT §22 |
| T3.8 | Pydantic AI harness for agent orchestration | 1w | Kimi |
| T3.9 | Agent execution safety boundary — Plan→Policy→Auth→Execute→Rollback | 3d | ChatGPT C14 |
| T3.10 | Dry-run mode on all stages | 4h | aggregated |
| T3.11 | Modularize stage2_extract (1,480 lines) + stage4_merge (1,260 lines) | 3d | Kimi |

---

## 🔵 TIER 4 — RESEARCH (Ongoing, from D2116 feed.opml)

| # | Foundation | Status |
|---|-----------|--------|
| R1 | Typed Graph Storage — Zep/Graphiti eval | ⬜ DEFERRED |
| R2 | Edge Type Ontology — 10-15 types, machine-checkable | ⬜ DEFERRED |
| R3 | Skill Subgraph Templates — graduate when 50+ skills | ⬜ DEFERRED |
| R4 | Constitutional Constraint Graph — C1-C28 as graph invariants | ⬜ DEFERRED |
| R5 | Self-Observation Protocol — agent queries own graph | ⬜ DEFERRED |
| R6 | IBM course transcript for Layer 2 | ⬜ DEFERRED |
| R7 | GAAMA 4-node memory — episodes+facts+reflections+concepts | ⬜ DEFERRED |
| R8 | awesome-agent-skills repo eval | ⬜ DEFERRED |
| R9 | caveman prompt framework — local-first S2 prompts | ⬜ DEFERRED |
| R10 | vLLM-mlx for multi-agent — deferred, OMLX adequate | ⬜ DEFERRED |
| R11 | LanceDB unified store — only if sqlite-vec hits limits | ⬜ DEFERRED |
| R12 | ONNX runtime for NLI — only if ModernBERT too heavy | ⬜ DEFERRED |

---

## 🔴 OPEN BUGS (from buglog.md)

| Bug ID | Severity | Description | Status |
|--------|----------|-------------|--------|
| BUG-001 | 🔴 CRITICAL | Empty pass loop — verification checks random principles | 🔴 OPEN |
| BUG-053 | 🔴 CRITICAL | Phi-4-mini HALLUCINATES on open-ended research | 🔴 OPEN — Mitigated in D2205 P0 (classification only) |
| BUG-054 | 🔴 CRITICAL | Qwen3-Coder delegate fails — OMLX JSON parse error | 🔴 OPEN |
| BUG-055 | 🔴 CRITICAL | `related_fbs` vs `related_blocks` field name mismatch | 🔴 OPEN — Blocks delegation |
| BUG-051 | 🟡 MED | `just smoke` processes ALL 852 books instead of 1 | 🟡 OPEN |
| BUG-045 | 🟡 MED | Stage 2 evidence passages inflated | 🟡 OPEN — Deferred |
| BUG-046 | 🟡 MED | Stage 4 merge complexity for v3.0 | 🟡 OPEN |
| BUG-050 | 🟡 MED | Only 3 of 20 books chunked — insufficient convergence | 🟡 OPEN |

---

## ✅ COMPLETED — D2211 (2026-08-08 P0 Circuit Breaker & Error Propagation Fixes)

| # | Task | Decision |
|---|------|----------|
| ✅ | 13 P0 fixes: health check, 4xx exclusion, CircuitOpenError propagation, probe fail-closed, future boundary abort, thread safety, run scoping | D2211 |
| ✅ | `stress_test_omlx` non-200 set `all_ok=False` | D2211 |
| ✅ | `CircuitBreaker` thread safety (`threading.Lock`) | D2211 |
| ✅ | Probe cache + singleton output scoped by `_rid()` | D2211 |
| ✅ | Full failure chain verified end-to-end (syntax + live stress_test + breaker unit test) | D2211 |
| ✅ | **MinHash race condition** — `threading.Lock` protecting datasketch LSH + minhash_cache across ThreadPoolExecutor workers (the ONLY S2-blocking fix from IMPLEMENTATION_SPEC audit) | D2212 |
| ✅ | **SentenceTransformer cache** — module-level `_st_model_cache` prevents 500MB model reload per `split_cluster_by_kmeans` call (~611 calls, ~25 min saved) | D2212 |

### 🔜 DEFERRED to MTR (beneficial for S2 quality but not crash-blocking)

| # | Task | When | Why Deferred |
|---|------|------|-------------|
| **F-H10** | Evidence truncation 300→600 chars | After OMLX memory guard test | Could trigger prefill guard. Needs testing. |
| **F-H1** | Singleton resume logic | After first successful S2 | Nothing to resume on first run. |
| **F-H2** | Singleton `safe_write` final output | P2 | CircuitOpenError path already safe. |
| **F-M5** | Enforce non-empty mechanism/boundary | After yield impact test | Would increase rejections — needs data. |
| **F-H12** | MinHash LRU evict from LSH | P3 | Negligible at single-run scale (~1.2MB). |

## ✅ COMPLETED — D2195-D2204 (2026-08-05/06 Immediate Fixes)

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
| ✅ | Golden set 10→25 (full properties, 21 domains, 5 negatives) | D2204 |
| ✅ | Master LLM eval prompt v2.0 | D2204 |

## ✅ COMPLETED — D2184-D2186 (2026-08-05 De-hardcoding)

| # | Task | Decision |
|---|------|----------|
| ✅ | T0.1-T0.7: All 14 hardcoded tuning values → config | D2184 |
| ✅ | C16: batch_convert_epubs.py + fix_remaining.py bare excepts | D2186 |
| ✅ | Config audit: 48 mappings, --strict flag, preflight integration | D2184/D2186 |
| ✅ | T1.1-T1.5: chunk, headers, e2e, NLI, config audit expansion | D2185/D2186 |

## ✅ COMPLETED — Phase 0-1.5 (2026-07-26/28)

| # | Task | Date |
|---|------|------|
| ✅ | P0.1-P0.6: schema_accessor, runner, R-NN, Stage 3 removal, smoke, parallel | 2026-07-26 |
| ✅ | P1.1-P1.7: USearch, TurboVec, golden set, relationship edges, schema wiring | 2026-07-26 |
| ✅ | D2121-D2126: De-hardcoding, Anytype, session agreements, extraction strategy | 2026-07-28 |
| ✅ | Matryoshka 512-dim, ModernBERT NLI tested, OKF export planned | 2026-07-27 |

---

## ❌ REJECTED — Will Not Implement

| # | Task | Why Rejected | Source |
|---|------|-------------|--------|
| R1 | Cloud burst (GPT-4o-mini) | Violates C1/C3 | Kimi |
| R2 | LangChain dependency | Vendor lock-in (C2) | D2010 |
| R3 | Microsoft GraphRAG | Heavy, cloud-native | D2118 |
| R4 | LanceDB/DuckDB storage | SQLite adequate (C5) | D2048 |
| R5 | Dagster/Prefect orchestration | PipelineRunner <300 LOC | D2061 |
| R6 | Full Pydantic migration | Schema accessors sufficient | D2120 |
| R7 | Leiden algorithm (for now) | Louvain adequate. Revisit at scale. | Kimi |
| R8 | OpenFActScore | Overengineered | Kimi |
| — | Self-RAG reflection token training | C1 (cost) + R7 (temp=0.0) | D2205 |
| — | CRAG web search fallback | C3 (sovereignty) | D2205 |
| — | ColBERT late interaction | M1 Max memory | D2205 |
| — | Multi-agent swarm | Coordination tax 39-70% | D2205 |
| — | Neo4j graph database | External service (C3) | D2205 |
