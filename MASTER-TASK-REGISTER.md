# Maxwell OS v3.0 — MASTER TASK REGISTER
> **Updated:** 2026-07-26 16:45 | **Decision:** D2120 (Phase 0 Refactor)
> **Rule:** Undone tasks at top (priority-ordered). Done tasks at bottom.
> **Buglog:** 8 open bugs | **Decision log:** 212 decisions (D2000-D2120)

---

## 🔴 PHASE 0 — CRITICAL ✅ COMPLETE (2026-07-26)

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| P0.1 | **Schema accessors** — `pipeline/schema_accessor.py` typed accessor functions | +187 | D2120 | ✅ DONE |
| P0.2 | **PipelineRunner** — `pipeline/runner.py` single entry, resume, progress | +431 | D2061, D2120 | ✅ DONE |
| P0.3 | **FAISS R-NN** — Replace union-find with reciprocal nearest neighbors in stage1_5 | +30 | BUG-049, D2120 | ✅ DONE |
| P0.4 | **Remove Stage 3** — Archive stage3_cluster.py, add cosine dedup to Stage 4 | -338/+40 | BUG-048, D2120 | ✅ DONE |
| P0.5 | **Two-tier smoke** — `just smoke-plumbing` (<30s no LLM) + `just smoke` (<2min fast model) | +60 | D2120 | ✅ DONE |
| P0.6 | **Subprocess parallelism** — `pipeline/parallel.py` book-level Stage 0/1 | +152 | DELEGATE-001, D2120 | ✅ DONE |

**Phase 0 gate:** ✅ PASSED. `just smoke-plumbing` passes <30s. `just smoke` passes <2min. Net ~560 LOC.

---

## 🟠 PHASE 1 — HIGH (Next Week, After Phase 0 Verified)

| # | Task | Effort | Source | Status |
|---|------|--------|--------|--------|
| P1.1 | **USearch benchmark** vs FAISS on 500+ segments (already installed v2.26.0) | 2h | D2118, D2120 | ✅ DONE (D2121) |
| P1.2 | **TurboVec wire-up** — Quantized FB index, Metal SIMD (already installed v0.8.0) | 1h | D2118, D2120 | ✅ DONE (D2122) |
| P1.3 | **Golden set calibration** — Convergent golden set v3.0 (7 examples) | 2h | D2103 | ✅ DONE (D2123) |
| P1.4 | **FB relationship edges** — Stage 4 emits `related_fbs` for LightRAG foundation | 2h | D2118 | ✅ DONE (2026-07-26) |
| P1.5 | **20-book E2E test** — Validate v3.0 at meaningful scale | 3h | D2113 | ⬜ TODO |
| P1.6 | **Wire schema_accessor into all 8 stages** — Remove ad-hoc .get() fallbacks | 1h | P0.1 | ✅ DONE (2026-07-26) |
| P1.7 | **Resolve D316 vs D2066** — Multi-label disciplines adopted, SALSA rejected | 1h | D2032, D2066 | ✅ DONE (2026-07-26) |

---

## 🟡 PHASE 2 — MEDIUM (Within Month)

| # | Task | Effort | Source | Status |
|---|------|--------|--------|--------|
| P2.1 | **LightRAG graph overlay** on FAISS+SQLite | 8h | D2118 | ⬜ TODO |
| P2.2 | **Cognee vs Supermemory eval** — Layer 2 agent memory | 7h | D2118 | ⬜ TODO |
| P2.3 | **IBM Agentic KG implementation** — Layer 2 orchestration blueprint | 16h | D2116 | ⬜ TODO |
| P2.4 | **MCP interface** — 8 tools, stdio transport (D2058) | ~200 LOC | D2058 | ⬜ TODO |
| P2.5 | **Config validation** — Pydantic schema (D2059) | ~80 LOC | D2059 | ⬜ TODO |
| P2.6 | **Feature flag system** (D2060) | ~40 LOC | D2060 | ⬜ TODO |
| P2.7 | **Distribution packaging** — pyproject.toml, install.sh (D2062) | ~80 LOC | D2062 | ⬜ TODO |

---

## 🟢 PHASE 3 — LATER (Evaluate When Needed)

| # | Task | Effort | Source | Status |
|---|------|--------|--------|--------|
| P3.1 | **Cross-platform memory/process** — psutil for Linux/Windows (D2057) | ~110 LOC | D2057 | ⬜ TODO |
| P3.2 | **Hybrid sync protocol** — Multi-machine KB sharing stub (D2063) | ~30 LOC | D2063 | ⬜ TODO |
| P3.3 | **Semantica eval** — Graph-native infrastructure (1,440★) | 2h | D2118 | ⬜ TODO |
| P3.4 | **Neo4j llm-graph-builder eval** — Graph construction from unstructured data | 2h | D2118 | ⬜ TODO |
| P3.5 | **LEANN eval** — 97% storage savings RAG (12,732★) | 2h | D2118 | ⬜ TODO |

---

## ❌ REJECTED — Will Not Implement

| # | Task | Why Rejected | Source |
|---|------|-------------|--------|
| R1 | Cloud burst (GPT-4o-mini) | Violates C1/C3 | Kimi review |
| R2 | LangChain dependency | 50MB for problem we don't have (C5) | D2010 |
| R3 | GraphRAG (Microsoft) | Heavy, cloud-native | D2118 |
| R4 | LanceDB/DuckDB storage | SQLite works, no proven need (C5) | D2048 |
| R5 | Dagster/Prefect orchestration | Heavy, PipelineRunner <300 LOC | D2061 |
| R6 | Full Pydantic migration | Breaks checkpoints, schema accessors sufficient | D2120 |
| R7 | Leiden algorithm | Premature optimization | Kimi review |
| R8 | OpenFActScore | Overengineered | Kimi review |

---

## ✅ DONE (Pre-Phase 0)

| # | Task | Date |
|---|------|------|
| C1 | Delegate system workaround (local OMLX) | 2026-07-26 |
| C2 | Governance sync (115 decisions) | 2026-07-26 |
| C4 | CONSTITUTION NLI mismatch fix | 2026-07-26 |
| C5 | DELEGATE-001 logged to buglog | 2026-07-26 |
| C6 | BUG-053 logged (Phi-4-mini hallucination) | 2026-07-26 |
| C7 | BUG-054 logged (Qwen3-Coder parse error) | 2026-07-26 |
| H1 | BUG-051 fix (smoke limit) | 2026-07-26 |
| H4 | BUG-048 fix (HDBSCAN bypass) | 2026-07-26 |
| — | v3.0 architecture (D2094-D2113) | 2026-07-25 |
| — | 14 foundation fixes (Phase 0 original) | 2026-07-21 |
| — | GitHub backup (v3.0 checkpoint, commit 245d737) | 2026-07-26 |

---

## 📋 OPEN BUGS (3)

| Bug | Severity | Status |
|-----|----------|--------|
| DELEGATE-001 | 🔴 CRITICAL | 🟢 IMPROVED — gemma-4-E4B + Qwen3-Coder confirmed working via OMLX. Subprocess parallel.py for pipeline. |
| BUG-017 | 🔴 CRITICAL | 🟡 MONITOR — OMLX watchdog enhanced, needs stress test |
| BUG-050 | 🟡 MEDIUM | ⬜ TODO — Need 5+ book chunk run (→ P1.5: 20-book E2E test) |

---

## ✅ DONE (Post-Phase 0)

| # | Task | Date |
|---|------|------|
| P0.1-P0.6 | Phase 0 refactor (schema_accessor, runner, R-NN, Stage 3 removal, smoke, parallel) | 2026-07-26 |
| P1.1 | USearch benchmark (D2121: FAISS+R-NN wins) | 2026-07-26 |
| P1.2 | TurboVec backend (D2122: 4-bit quantized, 8× compression) | 2026-07-26 |
| P1.3 | Convergent golden set v3.0 (D2123: 7 examples) | 2026-07-26 |
| P1.4 | FB relationship edges (domain/discipline/source/semantic) | 2026-07-26 |
| P1.6 | schema_accessor wired into stage4/5/6 | 2026-07-26 |
| P1.7 | D316 vs D2066 resolved: multi-label disciplines adopted, SALSA rejected | 2026-07-26 |
| C1 | Delegate system workaround (local OMLX) | 2026-07-26 |
| C2 | Governance sync (115 decisions) | 2026-07-26 |
| C4 | CONSTITUTION NLI mismatch fix | 2026-07-26 |

---

*Register synchronized with D2120. Phase 0 begins immediately.*
