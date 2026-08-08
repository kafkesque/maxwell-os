# Maxwell OS — Aggregated Remaining Tasks (Post D2211 P0 Fixes + Full Audit)
> **Updated:** 2026-08-08 08:51 | **Source:** D2195-D2211 + Goose Ultimate Final Verdict + IMPLEMENTATION_SPEC cross-reference
> **Total outstanding findings:** 33 items (12 HIGH + 10 MEDIUM + 10 LOW), 2 fixed by D2211, 2 partially mitigated
> **Recently completed:** D2195-D2204 (12 immediate fixes), D2205 roadmap, D2205-P0.1-P1.2 (retrieval eval + agentic + graph), D2208 (N1 yield), D2209 (probe routing), **D2211 (13 P0 circuit breaker fixes)**
> **Pipeline state:** S0 (922 MDs) ✅ | S1 (323K segments) ✅ | S1.5 (12,964 clusters + 35,239 singletons) ✅ | **S2 ready to run**
> **OMLX state:** All models loaded. stress_test: ALL_PASS.
> **Loose end:** Old 21MB probe cache ✅ cleaned up via safe_delete (backed up to backup/deletions/)

### Pre-S2 Readiness Checklist (2026-08-08 08:51)
| Check | Status |
|-------|--------|
| Syntax (3 files) | ✅ |
| OMLX /v1/models | ✅ HTTP 200 |
| OMLX stress_test (chat) | ✅ ALL_PASS |
| Models loaded | ✅ All 5 |
| S1.5 clusters + singletons | ✅ 12,964 + 35,239 |
| S2 checkpoint (resume) | ✅ 9 FBs |
| Probe cache (scoped) | ❌ Fresh → probe WILL run |
| CircuitBreaker | ✅ CLOSED, thread-safe |
| Old probe cache (flat) | ✅ Cleaned (safe_delete → backup) |

---

## 🏆 TIER 0 — CRITICAL PATH (This Week)

These tasks directly implement the D2205 RAG Architecture Roadmap. They are the **retrieval-to-agentic bridge** that turns Maxwell from a knowledge extraction engine into an evidence-grounded knowledge system.

| # | Task | Phase | Effort | Why | Status |
|---|------|-------|--------|-----|--------|
| **T0.1** | **Build retrieval evaluator** (`pipeline/retrieval_evaluator.py`) — CRAG-style critique with structured JSON output (CORRECT/PARTIAL/INCORRECT/CONTRADICTORY) | P0 | 0.5d | Single highest-impact change. Reuses Phi-4-mini. No new deps. | ✅ **DONE** (511 lines) |
| **T0.2** | **Build agentic retrieval loop** (`retrieve.py:agentic_search()`) — iteration budget (3 rounds), stop conditions, EvidencePack output | P0 | 0.5d | Makes every query better without pipeline changes. Reuses existing retrieve.py. | ✅ **DONE** (retrieve.py:613) |
| **T0.3** | **Build graph traversal layer** (`retrieve.py:graph_expand()`) — BFS over SQLite adjacency list for `related_fbs`, `contradicts_fbs`, `prerequisite_fbs` | P1 | 1.0d | Activates data already stored but never queried. Zero new deps. | ✅ **DONE** (retrieve.py:326) |
| **T0.4** | **Build graph-aware search** (`retrieve.py:graph_aware_search()`) — hybrid search + graph expansion + reranking | P1 | 0.5d | Combines T0.1+T0.3. Surfaces contradictions alongside support. | ✅ **DONE** (retrieve.py:467) |
| **T0.5** | **Run S2→S6 pipeline** — `python3 pipeline/stage2_extract.py --process-singletons`. S2: 2,634 convergent → probe (Phi-4-mini, ~5min) → split → ~12,964 targets extraction (Qwen3.6, est. 3h). Then 35,239 singletons (est. 16h). Checkpoint/resume safe. Then S4→S5→S6. | P0 | 4-20h | Pipeline emergency — only 9 FBs from failed Run 5. S2 ready NOW (all pre-flight checks passed). | ⬜ **READY** |
| **T0.6** | **Yield crisis diagnostic** — manual extract 10 principles from 1 book, compare vs pipeline output (14 FBs from 852 books = 0.004% yield) | P1 | 1d | BLOCKED on S2 completion. Cross-encoder reranker gate may rescue yield. | 🔒 BLOCKED |

---

---

## 🔴 CROSS-REFERENCE: IMPLEMENTATION_SPEC Findings vs D2211 Fixes (2026-08-08 Audit)

D2211 addressed 2 of 33 findings. Below is the complete re-audit against live repository HEAD.

### 0.2 HIGH — Prevent Data Loss / Quality Degradation (12 findings)

| ID | Finding | D2211 Fix? | Status | Recommendation |
|----|---------|-----------|--------|----------------|
| **F-H1** | `process_singletons` no resume — 35,239 items × ~4s = ~39h at risk | ❌ | 🔴 **STILL BROKEN** | Implement singleton resume with deterministic cluster IDs. 35K items without resume = massive vulnerability. |
| **F-H2** | `process_singletons` plain `open(..., "w")` — crash corrupts output (line 1592) | ⚠️ Partial | 🟠 **STILL VALID** | D2211 added safe_write in CircuitOpenError boundary, but final write still uses plain open(). |
| **F-H3** | `process_singletons` shallow health check | ✅ **YES** | ✅ FIXED | D2211 P0-10: replaced with stress_test_omlx() |
| **F-H4** | MPS `NameError`: `del raw` when variable is `mb_raw` (`stage1_5_embed_cluster.py:212`) | ❌ | 🔴 **STILL BROKEN** | Will crash on M1/M2/M3 Macs. 1-line fix: `del raw` → `del mb_raw`. Must fix before S1.5 rerun. |
| **F-H5** | `split_cluster_by_kmeans` loads SentenceTransformer on EVERY call | ✅ | ✅ **FIXED (D2212)** — module-level `_st_model_cache` dict + `_get_st_model()`. 500MB model loaded once, reused across all ~611 probe calls. Saves ~25 min S2 runtime. | |
| **F-H6** | MLX `generate_json()` caps ALL JSON output at 512 tokens — silent truncation | ❌ | 🟠 **MLX-ONLY** — no impact on default OMLX path. Fix if MLX provider is ever used for extraction. |
| **F-H7** | MLX path silently falls back to OMLX on error — user's provider choice overridden | ❌ | 🟠 **STILL VALID** | Line 583-588: `except Exception` → `# Fall through to OMLX`. Violates user intent. |
| **F-H8** | Watchdog hardcoded paths + PID 13137 default (`n2_watchdog.py:23-26`) | ❌ | 🟠 **STILL VALID** | Hardcoded `"knowledge pipeline/stage2_extract/latest/..."` paths. |
| **F-H9** | Watchdog reads S1.5 from hardcoded `latest/` (`n2_watchdog.py:50`) | ❌ | 🟠 **STILL VALID** | Ignores `get_run_id()`. Same file. |
| **F-H10** | Evidence passages truncated at 300-400 chars before LLM sees them (lines 377, 464, 758) | ❌ | 🟠 **STILL VALID** | Hardcoded `[:300]` and `[:400]` truncation. LLM sees truncated evidence. |
| **F-H11** | MinHash race condition — `is_near_duplicate` called from ThreadPoolExecutor, mutates datasketch state | ✅ | ✅ **FIXED (D2212)** — `threading.Lock` wraps all `lsh.insert()` and `minhash_cache` access in `_build_fb_from_result` + post-collection dedup. | |
| **F-H12** | MinHash LRU evicts cache but not LSH index — inconsistency | ❌ | 🟠 **STILL VALID** | LRU eviction of `minhash_cache` doesn't remove from LSH index. Negligible for single run (~1.2MB at 10K entries). |

### 0.3 MEDIUM — Operational / Performance (11 findings)

| ID | Finding | D2211 Fix? | Status |
|----|---------|-----------|--------|
| **F-M1** | `enforce_gate` defined (line 247) but NEVER called — dead code | ❌ | 🟡 Remove or wire in |
| **F-M2** | 6 dead/ghost config items in pipeline_paths.py | ❌ | 🟡 Clean up |
| **F-M3** | Probe burst-submits 611 calls simultaneously | ⚠️ | 🟢 MITIGATED (ThreadPoolExecutor with max_workers=S2_MAX_WORKERS limits concurrency to 3-5) |
| **F-M4** | Stress test prompt sizes [50, 1000, 5000] don't match actual workload (6000+ chars) | ❌ | 🟡 Add 6000-char test |
| **F-M5** | `validate_fb_output` allows empty mechanism/boundary/consequence (min_len check skipped at line 123-124) | ❌ | 🟡 Enforce min_len for structural fields |
| **F-M6** | Probe cache no content hash → stale cache risk | ⚠️ | 🟢 PARTIALLY FIXED (D2211 P0-11: run_id scoping prevents cross-run contamination. Corpus-change detection still missing.) |
| **F-M7** | `_build_fb_from_result` imports inside hot loop (line 1214 area) | ❌ | 🟡 Hoist to module level |
| **F-M8** | Watchdog phase detection ambiguous (PROBE vs EXTRACTION) | ❌ | 🟡 Parse log for phase transitions |
| **F-M9** | Watchdog stall detection ignores checkpoint growth | ❌ | 🟡 Monitor checkpoint size |
| **F-M10** | `call_omlx` breaker check at entry only — not re-checked inside retry loop | ❌ | 🟡 Re-check breaker between retries (breaks are sub-second now with lock, low priority) |
| **F-M11** | `run_monitor.py:68` — `except Exception: pass` (silent swallow) | ❌ | 🟡 Log the error |

### 0.4 LOW — Hygiene / Future Tax (10 findings)

| ID | Finding | Status |
|----|---------|--------|
| **F-L1** | `random.seed(42)` hardcoded despite `golden_seed: 42` in config | 🟡 Use config value |
| **F-L2** | D2xxx placeholder decision numbers in comments | ⚠️ Some fixed by D2211 |
| **F-L3** | BUG-061 ID collision (3 issues share same ID) | 🟡 Re-number |
| **F-L4** | Session seed 19+ days stale (2026-07-26) | 🟡 Update |
| **F-L5** | 105 bare `except Exception` blocks across pipeline/*.py | 🟡 Gradual C16 compliance |
| **F-L6** | Constitution says both "9-stage" (line 59) and "8-stage" (line 63) | 🟡 Fix line 59 |
| **F-L7** | JSON repair `_salvage_array_objects` returns None placeholders | 🟡 Filter None |
| **F-L8** | D2177 citation mismatch in comment | 🟡 Fix comment |
| **F-L9** | `stage0_convert.py:285` — `except Exception: pass` | 🟡 Log the error |
| **F-L10** | `stage1_3_prefilter.py:76-77` — `except Exception: return []` | 🟡 Log the error |

### 📊 Summary

| Category | Total | Fixed (D2211+D2212) | Mitigated | Still Outstanding |
|----------|-------|---------------------|-----------|-------------------|
| 0.2 HIGH | 12 | 3 (F-H3, F-H5, F-H11) | 1 (F-H2 partial) | **8** |
| 0.3 MEDIUM | 11 | 0 | 2 (F-M3, F-M6) | **9** |
| 0.4 LOW | 10 | 0 | 1 (F-L2) | **9** |
| **TOTAL** | **33** | **3** | **4** | **26** |

**D2212 (2026-08-08):** Two pre-S2 fixes applied:
1. **F-H11** MinHash race condition — `threading.Lock` protecting datasketch LSH + minhash_cache. Was the ONLY finding that could crash/corrupt S2.
2. **F-H5** SentenceTransformer cache — module-level singleton saves ~25 min of S2 probe runtime (500MB model loaded once instead of ~611 times).

### 🟢 Beneficial-but-Deferred to MTR (won't crash S2, but would improve quality/perf)

| ID | What | Why Deferred | Priority for MTR |
|----|------|-------------|------------------|
| **F-H10** | Evidence truncated 300-400 chars before LLM | Could cause OMLX prefill guard rejections if increased. Needs memory guard testing first. | P1 — test after S2 run |
| **F-H1** | Singleton resume logic | First run has nothing to resume. Only matters if S2 crashes mid-singletons. | P1 — implement after first successful S2 |
| **F-H2** | Singleton `safe_write` for final output | CircuitOpenError path already safe. Marginal for first run. | P2 |
| **F-M5** | `validate_fb_output` allows empty mechanism | Would reject more FBs → lower yield. Needs yield impact testing first. | P2 |
| **F-H12** | MinHash LRU doesn't evict from LSH | LSH grows ~1.2MB at 10K entries. Negligible for single run. | P3 |

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
