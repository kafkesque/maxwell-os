# Maxwell OS v3.0 — MASTER TASK REGISTER
> **Updated:** 2026-08-03 22:00 | **Decisions:** D2129–D2135 (7 new, verified fixes)
> **Rule:** Undone tasks at top (priority-ordered). Done tasks at bottom.
> **Buglog:** 8 open + BUG-056/057/058 (3 new) | **Decision log:** 132 decisions (D2000-D2135)

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

## 🔴 PHASE 0.5 — VERIFIED BOTTLENECK FIXES (2026-08-03, D2129-D2134)

| # | Task | Effort | Source | Status |
|---|------|--------|--------|--------|
| V1 | **Streaming per-book production run** — `tests/full_run_streaming.py`; chunk→extract→classify→persist→free per book; resume checkpoint; smoke-tested (3 books → 9 FBs) | 2h | D2129, BUG-02 (hang) | ✅ DONE (2026-08-03) |
| V2 | **Re-chunk 12 missing books** + quarantine 4 zero-byte corrupt files — resolved by V1 design (iterates all 922 config books; auto-quarantine) | 30m | D2130, BUG-057 | ✅ DONE (via V1) |
| V3 | **Correct embedding speed claim** in stage1_5_fastembed.py (measured 564 min ≠ "~5 min") | 15m | D2131, BUG-056 | ⬜ TODO |
| V4 | **Repoint/remove dead `books` symlink** + smoke assertion ≥900 MD | 15m | D2132 | ⬜ TODO |
| V5 | **Expand canonical taxonomy** — +26 disciplines/+10 domains; kind-aware synonym index; measured 35/77→0/77 discipline collapse | 3h | D2133 | ✅ DONE (2026-08-03) |
| V6 | **Fail-visible classification fallback** — log + `classification_errors` field, count failures | 30m | D2134, BUG-058 | ⬜ TODO |



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
| **D2121** | **C12 De-Hardcoding:** 19 values from tests/full_run.py → config/pipeline_config.yaml | 2026-07-28 |
| **D2122** | **Anytype Push Complete Payload:** 42-field payloads, 3-zone body, PT/PI/GE/TI export | 2026-07-28 |
| **D2123** | **Session Agreements Formalized:** Citation format, jargon body-only, body-only fields, related_blocks mandatory | 2026-07-28 |
| **D2124** | **Extraction Strategy:** Domain-by-domain sequential (Design→AI→Systems→Substrate→Art→Business→Personal→Influence) | 2026-07-28 |
| **D2125** | **Pipeline Throughput Estimate:** 5-10s per FB (~6.0s weighted avg), well under 30s threshold | 2026-07-28 |
| **D2126** | **ModernBERT NLI Confirmed Active:** Live in stage5_verify, DeBERTa fallback | 2026-07-28 |

---

## 🟢 EXTRACTION STRATEGY (D2124) — 2026-07-28

**Domain-by-Domain Sequential Extraction** is the recommended production start.

### Extraction Order:
| # | Domain | Rationale | Est. FBs |
|---|--------|-----------|----------|
| 1 | **Design** (DOMAIN 2) | Largest, most diverse: comm design, UX, brand, typography | 200-400 |
| 2 | **AI + Computing** (DOMAIN 6) | PT-rich: engineering patterns, agent architecture, ML ops | 150-300 |
| 3 | **Systems + Decision** (DOMAIN 0) | Universal principles: systems thinking, decision theory | 100-200 |
| 4 | **Substrate** (DOMAIN 1) | Mind, math, meaning: semiotics, cognition, philosophy | 100-200 |
| 5 | **Art + Comp. Media** (DOMAIN 3) | Specialized: glitch, computational art, media theory | 100-150 |
| 6 | **Business** (DOMAIN 4) | Strategy, entrepreneurship, marketing | 100-200 |
| 7 | **Personal Practice** (DOMAIN 5) | Productivity, creativity, learning | 80-150 |
| 8 | **Influence + Power** (DOMAIN 7) | Negotiation, persuasion, politics | 80-150 |

### After All Domains:
- Cross-domain re-classification pass (many domain FBs will become cross-domain/universal)
- Full PT/PI/GE/TI commitment to database
- LightRAG graph construction from `compute_fb_relationships()` edges

### Expected Throughput (D2125):
- ~5-10s per FB end-to-end
- Domain 2 (~300 FBs): ~25-50 minutes
- Full corpus (~1400 FBs): ~2-4 hours

---

*Register synchronized with D2121-D2126. Session agreements enforced.*

---

## 🟢 PHASE 1.5 — ENHANCEMENTS (2026-07-27)

| # | Task | Effort | Source | Status |
|---|------|--------|--------|--------|
| **E7** | **Matryoshka 512-dim** — Truncate bge-m3 embeddings, 2× faster FAISS, 92% neighbor overlap | 0.5h | D2118 | ✅ DONE |
| **E6a** | **ModernBERT NLI** — Replace DeBERTa-v3 in stage5_verify, 2× faster with 8192 ctx | 1h | D2119 | ⏳ TESTED |
| **E6b** | **ModernBERT threshold calibration** — Recalibrate NLI_ENTAILMENT_THRESHOLD for ModernBERT scores | 0.5h | D2119 | 📋 TODO |
| **E6c** | **ModernBERT fallback config** — Add NLI model toggle in pipeline_config.yaml | 0.3h | D2119, C12 | 📋 TODO |
| **OKF1** | **Stage 6b OKF export** — `pipeline/stage6_okf_export.py` FBs → .okf/ bundle | 2h | D2120 | 📋 PLANNED |
| **OKF2** | **OKF index.md generator** — Domain-driven hierarchy, progressive disclosure map | 1h | D2120 | 📋 PLANNED |
| **OKF3** | **OKF CI gate** — Add `okf validate .okf/ && okf lint .okf/` to justfile | 0.5h | D2120 | 📋 PLANNED |

### Enhancement Summary (2026-07-27)

| Improvement | Speed Gain | Quality Impact | Risk | Status |
|------------|:----------:|:--------------:|:----:|:------:|
| bge-m3 512-dim Matryoshka | 2.0× search | Neutral (92% overlap) | LOW | ✅ DONE |
| ModernBERT-base-nli | 2.0× NLI | Neutral (90% = 90%) | LOW | ⏳ TESTED |
| OKF export (stage 6b) | N/A | Better agent consumption | NONE | 📋 PLANNED |

### Model Inventory Update

| Model | Role | Size | Speed | Context | Status |
|-------|------|------|:-----:|:-------:|:------:|
| Qwen3.6-35B-A3B-4bit | Generator | ~18GB | 30 tok/s | 262K | ✅ Active |
| Phi-4-mini-instruct-8bit | Verifier | ~8GB | 32 tok/s | 128K | ✅ Active |
| gemma-4-E4B-it-MLX-4bit | VerifierV2 | ~6GB | 27 tok/s | 128K | ✅ Active |
| bge-m3 → 512-dim | Embeddings | ~2GB | 2s/embed | N/A | ✅ Upgraded |
| DeBERTa-v3 → ModernBERT | NLI | 571MB | 64ms/check | 512→8192 | ⏳ Switching |
