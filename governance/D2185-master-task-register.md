# D2185 — Master Task Register & Cross-Review Aggregation (2026-08-05 20:42)

> **Aggregated from:** 14 LLM reviews (deepseek eval7/8, qwen eval8/9/10/11, chatgpt eval8/9/10, kimi eval9/10/11, round2), D2183-D2184 audits, DECISION-LOG, buglog.
> **Remote parity:** CONFIRMED at be89bdb. Local = remote = GitHub main.

---

## Pipeline Status at a Glance

| Stage | Status | Notes |
|-------|--------|-------|
| S0 (convert) | ✅ DONE | 922 MDs from EPUB/PDF |
| S1 (chunk) | ✅ DONE | 323,226 segments, SHA-256 dedup |
| S1.3 (prefilter) | 🔴 NEEDS FIRST RUN | Regex pre-filter — fast, no embeddings |
| S1.5 (embed+cluster) | 🔴 NEEDS FIRST RUN | bge-m3 512d Matryoshka → FAISS R-NN → Louvain |
| S2 (extract) | 🔴 NEEDS FIRST RUN | Qwen3.6 → 1:N principles (Golden set prompt) |
| S4 (merge+classify) | 🔴 NEEDS FIRST RUN | Two-stage classification + CRIBS |
| S5 (verify) | 🔴 NEEDS FIRST RUN | ModernBERT NLI → Gemma-4-E4B → BORP |
| S6 (commit) | 🔴 NEEDS FIRST RUN | SQLite 49-col + FTS5 + sqlite-vec + Parquet |
| S6b (anytype) | 🔴 NEEDS FIRST RUN | Anytype domain subfolders |
| S6c (obsidian) | 🔴 NEEDS FIRST RUN | Obsidian Markdown vault |

**Critical path:** S1.3 → S1.5 → S2 → S4 → S5 → S6 → S6b → S6c

---

## S0-S1.5 Re-Run Analysis

**Decision: S0 and S1 do NOT need re-run.** Chunks are embedding-model agnostic.
**S1.5 MUST be run fresh** with bge-m3 512d Matryoshka (config already aligned).
**S1.3 is a fast regex pass** — run it fresh (~minutes).

**Embedding time estimate:** 323K segments × bge-m3 on MPS ≈ 106 minutes (per D2131 benchmarks).

---

## Aggregated Task Register — Prioritized by Severity

### 🔴 P0 — Fix Before 953-Book Production Run

| ID | Task | Source | Effort | Impact |
|----|------|--------|--------|--------|
| **P0-1** | Fix R-009: BORP canonical source_id (Stage 5 uses filenames, S1.5 uses SHA-256) | chatgpt eval10, kimi eval11 | 2h | Integrity — single book with 3 filenames passes BORP as "3 sources" |
| **P0-2** | Run S1.3 + S1.5 with bge-m3 512d (fresh embeddings for entire corpus) | DECISION-LOG | 2-3h unattended | Prerequisite for all downstream stages |
| **P0-3** | Stage 6 vector embedding completeness monitoring (R-016) | chatgpt eval10 | 1h | vec_fbs silently degrades to 0 embeddings on failure |
| **P0-4** | vec_fbs ↔ fbs rowid reconciliation (R-017) | chatgpt eval10 | 1h | Orphaned vectors on INSERT OR REPLACE |

### 🟠 P1 — Fix Before Scaling Beyond 1K FBs

| ID | Task | Source | Effort | Impact |
|----|------|--------|--------|--------|
| **P1-1** | Implement `related_fbs` graph traversal in retrieval (R-014) | deepseek eval7, chatgpt eval10, kimi eval11 | 1d | Unlocks multi-hop reasoning from 4 edge types already computed |
| **P1-2** | Build feedback loop: retrieval logging + usage_count/feedback_score updates | kimi eval11 | 2d | Makes KB alive — static → living system |
| **P1-3** | OMLX circuit breaker + retry with exponential backoff | kimi eval11 | 1d | Single-point failure → resilient |
| **P1-4** | Golden set expansion: 7 → 200+ annotated clusters | deepseek eval7, chatgpt eval10 | 3d | Prerequisite for any algorithm tuning |
| **P1-5** | NLI calibration dataset: 100 entail/100 neutral/100 contradiction | chatgpt eval8 | 1d | NLI thresholds currently uncalibrated |

### 🟡 P2 — Phase 2 Features (Agentic OS Layer)

| ID | Task | Source | Effort | Impact |
|----|------|--------|--------|--------|
| **P2-1** | Agent runtime: goal → decompose → retrieve → act → observe | kimi eval11, chatgpt eval9 | 2-4w | The "OS" layer — what makes Maxwell agentic |
| **P2-2** | MCP server implementation (C25 compliance) | deepseek eval7, CONSTITUTION.md | 1w | Agent interoperability |
| **P2-3** | Cross-encoder re-ranker (MiniLM or local) for top-30 retrieval | kimi eval11 | 2d | Retrieval quality boost |
| **P2-4** | S2 Map-Reduce extraction for mega-clusters (>100 segments) | qwen eval10, qwen eval11 | 3d | Eliminates 15-segment sampling blind spot |
| **P2-5** | Semantic edge generation between FBs (S6-Graph) | qwen eval10, qwen eval11 | 3d | FB → subject-predicate-object triples |

### 🟢 P3 — Polish & Optimization

| ID | Task | Source | Effort | Impact |
|----|------|--------|--------|--------|
| **P3-1** | Query expansion (HyDE or sub-query generation) | kimi eval11 | 3d | Retrieval recall |
| **P3-2** | Dynamic clustering threshold tuning (per-domain calibration) | deepseek eval7 | 1w | Cluster quality optimization |
| **P3-3** | Book depth classification (universal/cross-domain/domain/specialized) | kimi eval9, memory #21 | 2d | Framework MOC generation |
| **P3-4** | Source independence model (work-level/edition-level) — R-013 | chatgpt eval10 | 3d | BORP epistemic accuracy |
| **P3-5** | pyproject.toml project metadata + uv.lock | chatgpt eval8 | 2h | Reproducible environment |
| **P3-6** | Query embedding cache (LRU) in retrieve.py | round2 | 1h | Reduce Ollama load |
| **P3-7** | Stage 6 batch embeddings (not 1 HTTP call per FB) | round2 | 1h | Speed optimization |
| **P3-8** | book_metadata title normalization (strip subtitles/editions) | round2 | 1h | Source diversity accuracy |
| **P3-9** | CI parity badge (local=remote verification) | D2183 | 1h | Process fix |
| **P3-10** | Pre-commit hook: verify DECISION-LOG claims match committed files | kimi eval10 | 2h | Prevent governance rot |

---

## Blindspot Registry — Categorized by Type

### Process Blindspots

| ID | Blindspot | Discovered By | Mitigation |
|----|-----------|---------------|------------|
| **B-1** | Remote-local drift (60 commits) | D2183, kimi eval9/10 | Push after every fix batch. CI parity badge (P3-9) |
| **B-2** | DECISION-LOG documents fixes absent from code | kimi eval10 | Pre-commit hook (P3-10) |
| **B-3** | Reviewers audit URLs, not files | D2183 | Include git rev-parse in all handoff docs |
| **B-4** | qwen eval11 scraped stale GitHub cache | This audit | Verify remote=local before accepting review claims |

### Audit Methodology Blindspots

| ID | Blindspot | Discovered By | Mitigation |
|----|-----------|---------------|------------|
| **B-5** | Component auditing misses state-transition gaps | chatgpt eval10 | D2184 invariant audit methodology |
| **B-6** | `grep`/`compile()` can't detect FAILED→PASS silent transitions | D2184 | Trace record lifecycle across all stages |
| **B-7** | Code correctness ≠ Agentic efficacy | qwen eval10 | Separate pipeline quality from agentic utility metrics |

### Architecture Blindspots

| ID | Blindspot | Discovered By | Mitigation |
|----|-----------|---------------|------------|
| **B-8** | BORP uses filename identity, not canonical source_id | chatgpt eval10 | P0-1 |
| **B-9** | related_fbs computed but never used in retrieval | kimi eval11 | P1-1 |
| **B-10** | Stage 6 vector indexing fails open (0 embeddings = "success") | chatgpt eval10 | P0-3 |
| **B-11** | OMLX single-point-of-failure (no circuit breaker) | kimi eval11 | P1-3 |
| **B-12** | Pipeline is static KB — no feedback loop | kimi eval11 | P1-2 |
| **B-13** | schema_version schizophrenia (2.0 defaults → 3.0 — fixed D2184) | kimi eval9, chatgpt eval10 | D2184 fix verified ✅ |

---

## Decision Registry — All Architectural Decisions Referenced

| Decision | Topic | Status | Source Review |
|----------|-------|--------|---------------|
| D2066 | Dynamic canonical taxonomy | ✅ ACTIVE | All |
| D2080 | Regex pre-filter (S1.3) | ✅ ACTIVE | — |
| D2093 | Fail-closed verification | ✅ ACTIVE | qwen eval8 |
| D2118 | bge-m3 512d Matryoshka | ✅ ACTIVE (config) | chatgpt eval8, round2 |
| D2120 | Stage 3 removed → cluster-before-extract | ✅ ACTIVE | deepseek eval7 |
| D2138 | Two-stage classification (free→canonical→depth) | ✅ ACTIVE | kimi eval11 |
| D2149 | Coverage gap detection | ✅ ACTIVE | deepseek eval7 |
| D2151 | NLI text/text_pair format fix | ✅ FIXED | kimi eval9 |
| D2152 | MinHash dedup fix | ✅ FIXED | kimi eval9 |
| D2163 | Principle discovery gate (split-probe) | ✅ ACTIVE | deepseek eval7 |
| D2168 | Louvain replaces union-find | ✅ FIXED | qwen eval8 |
| D2176 | RRF hybrid retrieval | ✅ ACTIVE | deepseek eval7, round2 |
| D2177 | fsync + LIMIT removal + dead deps | ✅ FIXED | all |
| D2181 | bge-m3 embedding unification | ✅ FIXED | chatgpt eval8 |
| D2183 | Cross-review forensic audit | ✅ DONE | This session |
| D2184 | System integrity hardening | ✅ DONE | This session |
| D2185 | Master task register (this doc) | ✅ DONE | This session |

---

## Review Quality Assessment

| Review | Valid Findings | Invalid Claims | Technical Precision | Value to Maxwell |
|--------|---------------|----------------|---------------------|------------------|
| deepseek eval7 | S2 1:N, RRF, golden set | — | High — specific line refs | **A** — pragmatic roadmap |
| round2 (23 files) | 5 valid P0-P1 | 13 phantom bugs (stale remote) | High — file-by-file | **A-** — best forensic pass, wrong target |
| qwen eval8 | 7 "unpatched flaws" | All 7 already fixed locally | High — code specific | **D** — useful methodology, wrong state |
| chatgpt eval8 | Config authority gaps | resolved by D2181 | High — GitHub refs | **B+** — config drift correctly diagnosed |
| kimi eval9 | 50 decisions vs code | All 50 were local, not remote | High — systematic | **B** — governance rot correctly identified |
| qwen eval9 | Architecture inversion | "compression death spiral" overstated | Medium — design opinions | **C** — architectural debate, not bugs |
| chatgpt eval9 | v3.1 hardening direction | — | High — system-level thinking | **A-** — correct roadmap |
| deepseek eval8 | Stage existence verification | Files reported "missing" exist locally | High — thorough | **B** — thorough but stale |
| kimi eval10 | Remote-local drift severity | STAGE_ORDER missing 6b/6c (false) | High — meta-audit | **A-** — confirmed D2183 finding |
| qwen eval10 | Extract-then-cluster alternative | "Compression death spiral" (S2 1:N fixed) | Medium — design opinions | **C+** — valid alternative, not a fix |
| chatgpt eval10 | State-transition integrity (P0-P1) | — | **S-tier** — invariant analysis | **A+** — most valuable single review |
| kimi eval11 | Agentic OS vs RAG pipeline gap | — | High — architectural clarity | **A** — honest architecture assessment |
| qwen eval11 | Map-Reduce extraction, S6-Graph | Louvain "missing from remote" (false) | Medium — scraped stale cache | **B** — good roadmap, wrong state |

---

## The Highest Priority — What to Do Next

### Immediate (Tonight)
1. **P0-1: Fix BORP canonical source_id** (2h) — last remaining P0
2. **P0-3: Stage 6 vector completeness monitoring** (1h)
3. **P0-4: vec_fbs rowid reconciliation** (1h)

### Tomorrow
4. **P0-2: Run S1.3 + S1.5** with bge-m3 512d (start it, runs unattended ~2h)
5. **P1-1: related_fbs graph traversal in retrieval** (1d)

### This Week
6. **P1-4: Golden set expansion** (3d) — prerequisite for ALL algorithm tuning
7. **P1-3: OMLX circuit breaker** (1d)

---

*Aggregated from 14 LLM reviews, 2 forensic audits, DECISION-LOG, and buglog.*
*Local = Remote = GitHub main at be89bdb. All claims verified against live code.*
