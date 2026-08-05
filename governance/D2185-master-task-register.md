# D2185 — Master Task Register & Cross-Review Aggregation (2026-08-05 20:42)

> **Aggregated from:** 14 LLM reviews (deepseek eval7/8, qwen eval8/9/10/11, chatgpt eval8/9/10, kimi eval9/10/11, round2), D2183-D2184 audits, DECISION-LOG, buglog.
> **Remote parity:** CONFIRMED at be89bdb → **7ab6387** (local = remote = GitHub main).

---

## ⚡ STATUS UPDATE — 2026-08-05 20:50 (Post-D2185 Audit)

### P0/P1 Completion Status

| ID | Task | Status | Evidence |
|----|------|--------|----------|
| **P0-1** | BORP canonical source_id | ✅ **DONE** (D2185) | `fb_source_ids()` in schema_accessor.py; check_borp uses it |
| **P0-2** | Run S1.3 + S1.5 with bge-m3 512d | ⏳ **PENDING — S1.5 BLOCKER** | S1.3 DONE (checkpoint: completed=true, 323,294). S1.5 latest/ EMPTY; old log = **bge-small 384d (STALE)** |
| **P0-3** | Vector embedding completeness | ✅ **DONE** (D2185) | stage6 prints Vector: READY/DEGRADED vs fbs count |
| **P0-4** | vec_fbs ↔ fbs rowid reconciliation | ✅ **DONE** (D2185) | Orphaned-vector detection at commit |
| **P1-1** | related_fbs graph traversal | ❌ **NOT DONE — BLOCKED** | retrieve.py: 0 refs to related_fbs; requires S2-S6 DB |
| **P1-2** | Feedback loop wiring | ⚠️ **PARTIAL — unblocked** | feedback.py has record_feedback + usage_count UPDATE; retrieve.py does NOT call them (wiring only) |
| **P1-3** | OMLX circuit breaker | ⚠️ **PARTIAL — unblocked** | Retry loop exists (MAX_RETRIES, timeout); NO circuit breaker, NO provider failover |
| **P1-4** | Golden set 7 → 200+ | ❌ **NOT DONE — unblocked** | config/golden/stage2_fewshot_convergent.yaml = 465-line few-shot prompt, NOT annotated clusters |
| **P1-5** | NLI calibration dataset | ❌ **NOT DONE — unblocked** | Only rubric_v2_calibrated.md; no 100E/100N/100C dataset |

### P1 Blocking Analysis (vs S1.3-S1.5)

| Task | Blocked by S1.5? | Reason |
|------|------------------|--------|
| P1-1 related_fbs traversal | 🔴 **BLOCKED** | Needs FBs with related_fbs edges in DB (S2→S4→S6) |
| P1-2 feedback loop wiring | 🟢 **NOT BLOCKED** | Plumbing exists in feedback.py; wiring retrieve.py→record usage can proceed now (validation needs data) |
| P1-3 OMLX circuit breaker | 🟢 **NOT BLOCKED** | Pure infrastructure — zero data dependency |
| P1-4 golden set | 🟢 **NOT BLOCKED** | Annotation task — can proceed on existing clusters |
| P1-5 NLI calibration | 🟢 **NOT BLOCKED** | Dataset construction can use source text now; threshold validation needs FBs |

**Key finding:** Only **P1-1 is hard-blocked** by S1.5. P1-2/3/4/5 are all unblocked and actionable immediately.

### 🔴 NEW CRITICAL FINDING — S1.5 Old Run is STALE

The `s15_run.log` proves the only S1.5 run used **bge-small-en-v1.5 (384d)**, NOT bge-m3 512d:

```
🧠 Embedding 323226 segments via BAAI/bge-small-en-v1.5 (MPS, 384d)...
```

Current config requires `embed_model_hf: BAAI/bge-m3`, `embed_dim: 512`. The `latest/` dir is **empty** (output superseded). **S1.5 MUST be re-run with bge-m3 512d before S2-S6.** Embed time ≈ 5,537s (92 min) for 323K segments on MPS.

### Blindspot Fix Status (B-1 → B-13)

| ID | Blindspot | Status |
|----|-----------|--------|
| B-1 | Remote-local drift | ✅ MITIGATED — remote=local at 7ab6387; CI badge (P3-9) still pending |
| B-2 | DECISION-LOG rot | ✅ MITIGATED — D2183-D2185 log real fixes; pre-commit hook (P3-10) pending |
| B-3 | Reviewers audit URLs | ✅ MITIGATED — handoffs include git rev-parse |
| B-4 | qwen eval11 stale cache | ✅ DETECTED — verified remote=local before accepting claims |
| B-5 | Component vs state-transition audit | ✅ FIXED — D2184 monotonic trust methodology |
| B-6 | grep can't detect FAILED→PASS | ✅ FIXED — D2184 classification_status persistence |
| B-7 | Code correctness ≠ agentic efficacy | ⚠️ ACKNOWLEDGED — roadmap P2-1 (agent runtime) |
| B-8 | BORP filename identity | ✅ FIXED — P0-1 (D2185) |
| B-9 | related_fbs unused in retrieval | ❌ **OPEN** — P1-1 (blocked by data) |
| B-10 | Vector fail-open | ✅ FIXED — P0-3 (D2185) |
| B-11 | OMLX single-point failure | ⚠️ PARTIAL — retry exists, no circuit breaker (P1-3) |
| B-12 | Static KB, no feedback loop | ⚠️ PARTIAL — plumbing exists, wiring pending (P1-2) |
| B-13 | schema_version schizophrenia | ✅ FIXED — D2184 |

**Blindspot score: 9/13 fixed · 2 partial (B-11, B-12) · 1 open (B-9) · 1 acknowledged (B-7)**

### Pipeline Execution Status (Post-D2185 verification)

| Stage | Status | Evidence |
|-------|--------|----------|
| S0 | ✅ DONE | 922 MDs |
| S1 | ✅ DONE | 323,226 segments |
| S1.3 | ✅ DONE | checkpoint.jsonl: completed=true, total=323,294 |
| S1.5 | ❌ **STALE** | Old run = bge-small 384d; latest/ EMPTY; needs bge-m3 512d |
| S2-S6c | ❌ NOT RUN | Empty stage dirs |

---

## Original Register (Baseline)

---

## Pipeline Status at a Glance

| Stage | Status | Notes |
|-------|--------|-------|
| S0 (convert) | ✅ DONE | 922 MDs from EPUB/PDF |
| S1 (chunk) | ✅ DONE | 323,226 segments, SHA-256 dedup |
| S1.3 (prefilter) | ✅ **DONE** (2026-08-05 verify) | checkpoint.jsonl: completed=true, 323,294 |
| S1.5 (embed+cluster) | ❌ **STALE — RE-RUN REQUIRED** | Only run = bge-small 384d (log evidence). latest/ EMPTY. Must run bge-m3 512d (~92 min) |
| S2 (extract) | 🔴 NEEDS FIRST RUN | Qwen3.6 → 1:N principles (Golden set prompt) |
| S4 (merge+classify) | 🔴 NEEDS FIRST RUN | Two-stage classification + CRIBS |
| S5 (verify) | 🔴 NEEDS FIRST RUN | ModernBERT NLI → Gemma-4-E4B → BORP (canonical source_ids) |
| S6 (commit) | 🔴 NEEDS FIRST RUN | SQLite 49-col + FTS5 + sqlite-vec + Parquet + vector completeness |
| S6b (anytype) | 🔴 NEEDS FIRST RUN | Anytype domain subfolders |
| S6c (obsidian) | 🔴 NEEDS FIRST RUN | Obsidian Markdown vault |

**Critical path:** S1.3 → S1.5 → S2 → S4 → S5 → S6 → S6b → S6c

---

## S0-S1.5 Re-Run Analysis

**Decision: S0 and S1 do NOT need re-run.** Chunks are embedding-model agnostic.
**S1.3 is DONE** (verified 2026-08-05: checkpoint completed=true, 323,294 segments).
**S1.5 MUST be RE-RUN with bge-m3 512d** — the only existing run used bge-small 384d (log evidence: `Embedding 323226 segments via BAAI/bge-small-en-v1.5 (MPS, 384d)`). Config now requires `embed_model_hf: BAAI/bge-m3`, `embed_dim: 512`. The latest/ dir is empty (superseded).

**Embedding time estimate:** 323K segments × bge-m3 on MPS ≈ 5,537s (92 min, per D2131 benchmarks).
**CRITICAL:** Do NOT start S2-S6 until S1.5 bge-m3 run completes — downstream FB embeddings/edges depend on this vector space.

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

## The Highest Priority — What to Do Next (UPDATED 20:50)

### Immediate (Tonight — all unblocked)
1. **P0-2: START S1.5 bge-m3 512d run** (92 min unattended) — unblocks P1-1 and all downstream
2. **P1-3: OMLX circuit breaker** (1d) — pure infra, unblocked
3. **P1-2: Wire feedback loop** (retrieve.py → record usage_count) (2h) — plumbing ready in feedback.py

### This Week
4. **P1-4: Golden set expansion** (3d) — prerequisite for ALL algorithm tuning, unblocked
5. **P1-5: NLI calibration dataset** (1d) — build from source text, unblocked

### Blocked (waiting on S1.5→S6 data)
6. **P1-1: related_fbs graph traversal** (1d) — BLOCKED until DB has FBs with edges
7. **P1-2 validation**: end-to-end feedback test — needs committed FBs

---

## ✅ DONE in D2183-D2185 (do not re-do)

| ID | Task | Round |
|----|------|-------|
| — | feedback.py DB_PATH → pipeline_paths | D2183 |
| — | Ghost hdbscan config removed | D2183 |
| — | FB schema classification_status | D2183 |
| — | Runner preflight fails hard (llm_bound) | D2183 |
| — | classification_status persisted in SQLite | D2184 |
| — | Stage 5 FAILED → QUARANTINE monotonic trust | D2184 |
| — | Stage 0.5 content-hash cache scoping | D2184 |
| — | Runner resume + stage0.5 run-scoped | D2184 |
| — | schema defaults 2.0→3.0 | D2184 |
| — | .env.example de-personalized | D2184 |
| — | OMLX binary dynamic resolution | D2184 |
| — | BORP canonical source_id (P0-1) | D2185 |
| — | Vector completeness + reconciliation (P0-3, P0-4) | D2185 |

---

*Aggregated from 14 LLM reviews, 2 forensic audits, DECISION-LOG, and buglog.*
*Local = Remote = GitHub main at 7ab6387. All claims verified against live code.*
*Status update: 2026-08-05 20:50 — P0/P1 statuses, blocking analysis, blindspot registry refreshed.*
