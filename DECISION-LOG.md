# Maxwell OS v2.0 — Decision Log
> **Append-only.** Newest first. Hash-chained.

---

## D2000 — v2.0 Architecture (2026-07-18)

**Summary:** Maxwell OS restarts with a clean v2.0 codebase. v1 archived in `archive/maxwell_os_v1/`. Architecture v3.0 adopted for pipeline.

**Key decisions carried forward from v1:**
- R5: Generator ≠ Verifier (different model families)
- R7: temp=0.0 on all generation
- R14: Schema stamps on all persistent output
- D150: Max 5 domains per FB
- D316: Multi-label classification
- D1057: Lazy-load OMLX models per stage
- D1058: Jargon decontamination

**New for v2.0:**
- Pipeline: 6 stages (was 8)
- Storage: SQLite + Parquet (was Anytype-first)
- Classification: SALSA inline (was 13 separate scripts)
- Folder: `pipeline/` not `tools/`
- Goal: Triad proof before scale (3 books → 10 FBs → verify → THEN scale)
- Knowledge layer defined BEFORE pipeline implementation
- Pydantic Literal types at write boundary — structural validity, not filter-based

**Files:** All of `maxwell os 2.0/`

---

## D2001 — v1 Archived, Not Deleted (2026-07-18)

**Summary:** Full v1 project preserved at `archive/maxwell_os_v1/`. No files deleted. Accessible for reference. 19,770 legacy FBs preserved. Anytype integration scripts preserved. All decisions and governance docs preserved.

**Rationale:** Clean workspace without data loss. If v2.0 needs a pattern from v1, it's in the archive.

---

## D2002 — Stress Test Results: Pipeline v2.0 End-to-End (2026-07-18)

**Summary:** Full 6-stage pipeline tested on 14 diverse books (307 segments) from 6 domains. All stages completed successfully. 14 FBs generated, 4 PASS, 10 FLAG (BORP violations — expected for single-source clusters). Full DB + Parquet commit.

**Test Configuration:**
- Books: Design (4), AI/Computing (4), Data (2), Programming (1), Self-Help (1), Cyrillic edge case (1), Systems (1)
- Models: Qwen3-Coder-30B (generator), Phi-4-mini-8bit (verifier), nomic-embed-text (embeddings)
- SALSA: Inline classification via prompt — 1 label error in 14 FBs (93% valid at first pass)
- API: OMLX with `sk-maxwell-local` key on port 11435

**Stage Results:**
| Stage | Input → Output | Time | Notes |
|-------|----------------|------|-------|
| 0 | 852 books → 849 valid .md | <1s | 3 books skipped (<100 bytes) |
| 1 | 849 .md → 2,314 segments (307 test) | 80s | Section-aware chunking + SHA-256 exact dedup |
| 2 | 307 segments → 188 principles | 13min | 31 LLM batches, ~26s avg per batch |
| 3 | 188 principles → 14 clusters | 6s | HDBSCAN, 78 noise, cohesion 0.73 |
| 4 | 14 clusters → 14 FBs | 3.5min | SALSA inline, 1 label error, 12 cross-domain |
| 5 | 14 FBs → 4 PASS + 10 FLAG | 0s | BORP ≥2 gate (10 single-source), no LLM factual |
| 6 | 14 FBs → SQLite + Parquet | 1s | FTS5 table, 41KB parquet snapshot |

**Bugs Found & Fixed During Test:**
1. `pipeline_paths.py`: .md not in supported extensions for stage 0
2. `stage1_chunk.py`: Variable shadowing `chunk_text` function with loop var
3. `stage1_chunk.py`: Shrink guard blocking incremental runs
4. `omlx_call.py`: Typo `call_omxl` → `call_omlx`
5. `omlx_call.py`: Missing API key header (`sk-maxwell-local`)
6. `pipeline_paths.py`: Wrong model name (Qwen3.6 → Qwen3-Coder)
7. `stage4_merge.py`: `jargon` field returned as dict, not string
8. `stage4_merge.py`: Missing `Optional` import
9. `stage6_commit.py`: SQLite insert failed on dict-type fields
10. `stage6_commit.py`: Parquet export failed on dict-type fields

**Assessment:** Pipeline architecture is sound. All 10 bugs were implement-level, not design-level. No changes needed to 6-stage architecture or schema contracts. Ready for production run on full book corpus.

**Remaining:** T1.17 (Maxwell human review of 14 FBs)

---

---

## D2003 — Re-Engineering Assessment: Surgical vs Full Rewrite (2026-07-20)

**Summary:** Cross-examination of 10 documents (7 temp/ LLM evaluations + 3 current-repo handoff docs) plus live code audit. The question: do we need full re-engineering, or targeted surgical fixes?

**Verdict: TARGETED RE-ENGINEERING in 4 areas. NOT a full pipeline rewrite.**

The 7-stage pipeline skeleton is architecturally sound. The individual implementations need fixes, not replacement. Here's what needs re-engineering vs what stays:

| Component | Action | Rationale |
|-----------|--------|-----------|
| **Stage 1 (chunker)** | Surgical fix (15 LOC) | Root cause is `clean_line()` returning None for blanks, not the join separator. Native fix works. |
| **Stage 3 (clustering)** | Drop-in replacement | PCA → UMAP(random_state=42). Same function signature. UMAP is deterministic when seeded. |
| **Stage 3 (embeddings)** | Drop-in replacement | nomic-embed-text → bge-m3. One config line change. |
| **Stage 5 (verification)** | Full re-engineering (~200 LOC) | Current verification is broken (Kimi BUG 1: empty pass loop). Replace with FActScore + DeBERTa NLI. |
| **Stage 1.5 (NEW)** | New stage (~80 LOC) | Semantic intent pre-filter. Doesn't exist yet. Critical for 800-book viability. |
| **Stage 0.5 (NEW)** | New pre-processing (~80 LOC) | 4-layer markdown cleaning. Additive, not re-engineering. |
| **Modular layer (NEW)** | New abstraction (~160 LOC) | InferenceProvider + StagePlugin. Future-proofing against Apple Silicon model churn. |
| **Stages 0, 2, 4, 6** | Keep as-is | Working. Fix bugs (R5 violation in S4, lineage in stamp.py) but don't restructure. |
| **7-stage pipeline** | Keep | `STAGE_CHECKPOINTS` dict + `--resume-from` logic assume 7 stages. Compression breaks resumability. |

**What we're NOT doing:**
- NOT compressing to 4 stages (breaks `--resume-from`)
- NOT adding LangChain dependency (50MB for a 15-line problem)
- NOT switching to BIRCH clustering (wrong tool for 2,697 principles in 64GB)
- NOT adding cloud burst (violates C1/C3 iron rules)
- NOT building a new pipeline framework (7 stages + JSONL checkpoints works)

**Risk accepted:** If UMAP+HDBSCAN doesn't fix cluster collapse, fall back to keyword bucket routing (already proven as workaround) while tuning UMAP parameters.

**References:** ULTIMATE-CROSS-EXAMINATION-HANDOFF.md — full analysis of all 10 documents.

---

## D2004 — Phase 0: 14 Foundation Fixes (2026-07-20)

**Summary:** 14 confirmed fixes required before any feature work. All are bugs verified against actual repo code. ~100 LOC net. ~10 hours.

| # | Fix | File | LOC | Bug Reference |
|---|-----|------|-----|---------------|
| P0.1 | `clean_line()` returns `""` for blanks | stage1_chunk.py | 3 | Grounded Review + Qwen |
| P0.2 | `split_on_headings()` paragraph-aware | stage1_chunk.py | 15 | Grounded Review + Qwen |
| P0.3 | Remove numbered-list from SKIP_PATTERNS | stage1_chunk.py | 2 | Qwen |
| P0.4 | Lower MIN_CHUNK_WORDS 30→10 | stage1_chunk.py | 1 | Qwen |
| P0.5 | PCA → UMAP(random_state=42) | stage3_cluster.py | 10 | Grounded Review + Qwen |
| P0.6 | nomic-embed-text → bge-m3 | pipeline_paths.py | 1 | ALL documents |
| P0.7 | HDBSCAN_MIN_CLUSTER_SIZE 3→8 | pipeline_paths.py | 1 | Grounded Review + Qwen |
| P0.8 | Fix stage5_verify.py source mapping (Kimi BUG 1) | stage5_verify.py | 25 | Kimi + Qwen |
| P0.9 | Fix stamp.py lineage (Kimi BUG 2) | stamp.py | 10 | Kimi + Qwen |
| P0.10 | Fix R5 violation in stage4_merge.py (Kimi BUG 3) | stage4_merge.py | 5 | Kimi + Qwen |
| P0.11 | Fix sqlite-vec loading | stage6_commit.py | 3 | Qwen |
| P0.12 | Fix OMLX guard PID-specific kill | omlx_guard.py | 10 | Qwen |
| P0.13 | DELETE cloud burst code | inference.py | -30 | Grounded Review + Qwen |
| P0.14 | Audit model_assignments.yaml vs actual models | config/ | 0 | Grounded Review |

**Gate:** Re-run 130 pricing books. ≥5 clusters. 0 template collapse FBs. Read 15 FBs manually.

**Kill criteria:** If re-run produces <3 clusters or >50% template collapse after fixes, escalate to full Stage 3 re-engineering.

---

## D2005 — UMAP Chosen Over BIRCH for Clustering (2026-07-20)

**Summary:** UMAP + HDBSCAN is the correct clustering stack for Maxwell OS. BIRCH rejected. PCA removed.

**Rationale:**
- UMAP with `random_state=42` IS deterministic — documented, tested, reproducible
- BIRCH is a CF-tree pre-clusterer for datasets too large for RAM — not our constraint (2,697 principles in 64GB)
- UMAP + HDBSCAN is the BERTopic standard — battle-tested on semantic clustering
- PCA is a LINEAR projection that collapses non-linear pricing subtopics by mathematical necessity
- Combined with bge-m3 (1024-dim, better discrimination than nomic-embed-text) and HDBSCAN(min_cluster_size=8), this stack is expected to produce 15-40 clusters from 2,697 principles

**Fallback:** If UMAP+HDBSCAN still collapses, tune n_neighbors (try 5, 10, 15, 30) and min_dist (try 0.0, 0.1, 0.25) before considering alternatives.

**Rejected alternatives:** BIRCH (wrong tool class), t-SNE (non-deterministic even with seed due to early exaggeration phase), PCA (linear, root cause of collapse).

---

## D2006 — No Cloud Burst. C1/C3 Are Absolute. (2026-07-20)

**Summary:** All cloud API code must be deleted. DeepSeek API, cloud_generate(), cloud burst — all violate C1 ($0 marginal cost) and C3 (sovereign).

**Rationale:**
- C1: "$0 marginal cost — all generation on local hardware" — NO exception for "extraction only"
- C3: "Sovereign — all data and compute remain local" — NO exception for batch runs
- The argument that "verification stays local so extraction can use cloud" is a distinction without constitutional basis
- If extraction is too slow on M1 Max, fix efficiency: semantic pre-filter (80% compute savings), DFlash speculative decoding (1.5-2.5x speedup), better chunking

**Trade-off:** Accepts longer extraction times on M1 Max. Mitigated by: semantic pre-filter (Phase 1), DFlash (Phase 1), and batch processing design.

---

## D2007 — bge-m3 Replaces nomic-embed-text (2026-07-20)

**Summary:** Embedding model changed from nomic-embed-text (768-dim) to bge-m3 (1024-dim). One config line change.

**Rationale:**
- nomic-embed-text produces embeddings where pricing subtopics are too close together — compounds cluster collapse
- bge-m3: 1024 dimensions, 8192 token context, higher MTEB retrieval scores
- ~2.3GB on disk via Ollama. Fits comfortably in 64GB RAM alongside Qwen3-Coder-30B (~18GB)
- ALL 7 documents that addressed embedding models converged on bge-m3

**Migration:** Re-embedding required on first run after switch. Embedding model version will be tracked in schema (Phase 1.5).

---

## D2008 — 7-Stage Pipeline Preserved (2026-07-20)

**Summary:** Pipeline stays at 7 stages (0-6). Will NOT be compressed to 4.

**Rationale:**
- `pipeline_paths.py` has `STAGE_CHECKPOINTS = {0: ..., 1: ..., ..., 6: ...}` — individual JSONL per stage
- `status.py`, `backup_guardian.sh`, resume logic all assume 7 stages
- For a solo, part-time, crash-prone local pipeline, granular resumability > ~50 LOC boilerplate savings
- A crash at Stage 4 on 800 books should resume from Stage 4 checkpoint, not restart from Stage 0

**What IS being added:** Stage 1.5 (intent filter) — a new stage between existing 1 and 2. This is additive, not compressive.

---

## D2009 — Confidence Formula Deferred to Empirical Validation (2026-07-20)

**Summary:** The 4-term confidence formula proposed in Final Architecture is NOT adopted until validated against human judgment.

**Current formula (temporary 3-term, Phase 1):**
```
base = borp × 0.30 + factscore × 0.50 + consistency × 0.20
if overgeneralized: base *= 0.70
confidence = base - contradiction_penalty
```

**Validation gate:** Hand-label 30-50 FBs as good/mediocre/bad. Test which formula (3-term, 4-term, or simple threshold) best separates them. THEN tune weights.

**Rationale:** "Bikeshedding an uncalibrated number" (Grounded Review). Nobody has checked whether any weight scheme tracks human judgment. All 7 documents propose different formulas with different weights based on intuition, not data.

---

## D2010 — LangChain Rejected. Native Chunker Fix Adopted. (2026-07-20)

**Summary:** `RecursiveCharacterTextSplitter` from LangChain is NOT added as a dependency. The native fix (clean_line returns "" not None + paragraph-aware split_on_headings) is sufficient and verified (30/30 tests pass).

**Rationale:**
- C5: "No dependency without proven need"
- The root cause is NOT the splitter — it's that blank lines are destroyed before any splitter can use them
- Fixing the root cause (15 LOC) makes the existing chunk_text() work correctly
- LangChain adds ~50MB for a problem that doesn't need it
- Qwen's diff is battle-tested: 30/30 tests pass, confirmed end-to-end

**Reference:** qwen maxw.md — exact diff with test file.

---

## D2011 — Buglog System Established (2026-07-20)

**Summary:** All recurring bugs and issues will be accumulated in `governance/buglog.md` for LLM handoff with full documentation. This becomes a standing rule.

**Format:** Each entry includes: Bug ID, severity, file, lines, symptom, root cause, proposed fix, source document, status.

**Rule:** When accumulating 5+ unresolved bugs, the buglog must be appended to all LLM handoff documents so the next LLM has full context.

**File:** `governance/buglog.md`

**Reference:** This decision log entry. See `governance/buglog.md` for the initial population.

---

## D2012 — Phase 0.5: 4-Layer Markdown Cleaning Pipeline (2026-07-20)

**Summary:** Before re-running 130 books, add markdown pre-processing: stripping formatting artifacts, normalizing paragraphs to 30-250 words, and wiring cleaning into Stage 1. ~95 LOC.

**Rationale:**
- Directly addresses Kimi quality issues #1 (template collapse), #3 (cluster collapse), #4 (truncation), #7 (conceptually broken)
- `**Price anchoring**` and `Price anchoring` produce DIFFERENT embedding vectors because `**` tokens are in vocabulary
- 30-250 word paragraphs are what bge-m3 was trained on — single topic, complete thought, discriminative embedding
- Estimated impact: 14 FBs at 93% FLAG → 30-50 FBs at ≥60% PASS

**Layers:**
1. Fix splitter (Phase 0) — already covered
2. `clean_markdown()` — strip **, [], ``, headings, boilerplate (~30 LOC)
3. `normalize_paragraphs()` — 30-250 words, split at sentence boundaries (~30 LOC)
4. Integration wiring (~20 LOC) + post-conversion quality check (~15 LOC)

**Gate:** Re-run both pricing and brand strategy domains. Compare PASS rate vs pre-cleaning run.

---

## D2013 — Phase 1: Intent Filter + FActScore/DeBERTa Verification (2026-07-20)

**Summary:** Two highest-leverage additions: Stage 1.5 semantic pre-filter (~80 LOC) and FActScore + DeBERTa NLI verification upgrade (~200 LOC). Combined: ~280 LOC. ~1 week.

**Stage 1.5 (Intent Filter):**
- bge-m3 cosine similarity between intent query and all segments
- Soft filter: top-K% ∪ keyword safety net ∪ above threshold
- Expands intent using existing `synonym_map.yaml` (643 entries)
- 40,000 segments → ~6,000 relevant (85% reduction)
- 5 minutes embedding time → saves ~18 hours LLM extraction compute

**Stage 5 Upgrade (Verification):**
- Claim decomposition (Phi-4-mini): break FB into 2-10 atomic claims
- NLI entailment (DeBERTa-v3-base-mnli, CPU, 368MB): does source text entail each claim?
- Contradiction detection: DeBERTa MNLI — entails/neutral/contradicts
- Overgeneralization penalty: multiplicative ×0.70 for absolute language
- Claim-type routing: FACT → DeBERTa, CAUSAL → Phi-4-mini judge, STATISTICAL → source substring
- `verification_type: "source_grounding"` — honest epistemic labeling

**Reference:** qwen maxw.md for implementation; Final Architecture for 4-term formula (deferred per D2009).

---

## D2014 — Phase 1.5: Modular Architecture (2026-07-20)

**Summary:** Abstracted InferenceProvider Protocol + minimal StagePlugin framework. ~160 LOC. Future-proofing against Apple Silicon MLX model churn.

**Components:**
- `InferenceProvider` Protocol: `generate()`, `health_check()` — OMLX/Ollama providers
- `StagePlugin` ABC + `StageRegistry`: register/replace pipeline stages
- Embedding model versioning in schema
- Prompt versioning in output metadata
- Config-driven model assignments (replace hardcoded model_assignments.yaml)

**Rationale:** Apple Silicon MLX model availability changes monthly. Qwen3-Coder works today. In 6-12 months, something better will exist and Qwen3-Coder may be deprecated. The abstraction means swapping models is a config change, not a code change.

**Trade-off:** 160 LOC of abstraction overhead for future-proofing. Accepted — Apple Silicon model ecosystem is genuinely volatile.

**Gate:** Swapping inference provider or embedding model requires config change only, not code change.

---

## D2015 — Layer 2 Orchestration Spec Validated, Deferred to Phase 2 (2026-07-20)

**Summary:** The FB→PT→PI→Recipe→Trust Ledger→Conductor Loop chain from FOUNDATION-BLOCK-TO-SKILL-SPEC.md v1.1 is architecturally valid and novel. BUT it requires 100+ verified FBs before it can be tested. Deferred to Phase 2.

**Novelty confirmed:**
- `fb_reliability`: execution-based principle validation — "does this claim actually work in practice?" No competitor has this.
- 3-Zone body template with STABLE GATE: standardized object lifecycle with immutability wall
- Execution outcomes (FB_VALID/IRRELEVANT/CONTRADICTED) logged per FB per PI step
- Reliability thresholds: ≥0.85 STABLE, <0.50 UNSTABLE, <0.20 GARBAGE (propose archive)

**What to build NOW (Phase 2):** fb_reliability table schema, Trust Ledger schema, 3-zone body template renderer, minimal Recipe compiler.

**What to defer:** Conductor Loop, Project/MOC objects, full PI execution logging.

---

## D2016 — Lifetime License Model Adopted (2026-07-20)

**Summary:** MISSION.md's lifetime license + upgrade engine model is adopted over SaaS recurring. More aligned with sovereignty and C3.

**Pricing tiers (Phase 4):**
- Beta Kit: 1 domain + 3-5 PTs + installation — £750-1,000
- Domain Expansion: additional domain kits — £300-500
- Major Upgrade: new features (MCP, multi-agent, etc.) — £400-600
- Custom Build: bespoke knowledge system for client domain — £5,000-15,000

**Rationale:** A tool with ongoing local compute costs and no cloud dependency doesn't justify monthly SaaS billing. Lifetime license aligns with the sovereign positioning.

**Kill criteria (any one = pivot):** No friend willing to pay after Alpha. Friends won't use it after 2 weeks. You're not using it for your own business 12 months in.

---

## D2017 — 6 Unresolved Gaps Addressed (2026-07-20)

**Summary:** All 6 gaps identified in the cross-examination are addressed with concrete actions, code snippets, and activation gates. See ULTIMATE-CROSS-EXAMINATION-HANDOFF.md Part 1.

| Gap | Solution | Phase |
|-----|----------|-------|
| A: OMLX memory leak | Stress test protocol (5 consecutive runs, monitor vm_stat) | 0 |
| B: Single data point | Run on brand strategy domain (20-30 books) in addition to pricing | 0 |
| C: No author diversity | Author-level BORP weighting (distinct authors / distinct books) | 1 |
| D: IP/copyright risk | Risk classification (LOW/MED/HIGH), cap source snippets at 50 words, pre-launch legal consult | 3 |
| E: DeBERTa causal limitation | Claim-type routing (FACT→DeBERTa, CAUSAL→Phi-4-mini, STATISTICAL→substring) | 1 |
| F: Onboarding design | Full design from first principles — VALIDATE + DISCOVER modes, ExtractionProfile JSON bridge | 4 |

---

## D2018 — Spec Tools: Pydantic-Encoded OpenSPDD for Local LLM Code Generation (2026-07-20)

**Summary:** For generating ~2,700 LOC of pipeline fixes with local LLMs (Qwen3-Coder, Phi-4-mini), adopt a rigid Pydantic-schema spec format inspired by OpenSPDD's REASONS Canvas structure.

**Format:** `ScriptSpec` Pydantic model with: script_name, purpose, inputs, outputs, functions (≤5 lines logic each), error_handling, tests (bash one-liners), constitution_rules.

**Key rules for LLM prompts:**
- If uncertain about ANY implementation detail, `raise NotImplementedError("specific message")`
- Each function ≤5 logic lines — atomically implementable
- Must pass all tests listed in the spec
- Output: ONLY the Python code, no explanation

**Rationale:** Local LLMs drift and hallucinate. A rigid, machine-verifiable spec format with "raise NotImplementedError" as the failure mode prevents hallucinated implementations.

---

## D2018 — Spec Tools: Pydantic-Encoded OpenSPDD for Local LLM Code Generation (2026-07-20)

**Summary:** For generating ~2,700 LOC of pipeline fixes with local LLMs (Qwen3-Coder, Phi-4-mini), adopt a rigid Pydantic-schema spec format inspired by OpenSPDD's REASONS Canvas structure.

**Format:** `ScriptSpec` Pydantic model with: script_name, purpose, inputs, outputs, functions (≤5 lines logic each), error_handling, tests (bash one-liners), constitution_rules.

**Key rules for LLM prompts:**
- If uncertain about ANY implementation detail, `raise NotImplementedError("specific message")`
- Each function ≤5 logic lines — atomically implementable
- Must pass all tests listed in the spec
- Output: ONLY the Python code, no explanation

**Rationale:** Local LLMs drift and hallucinate. A rigid, machine-verifiable spec format with "raise NotImplementedError" as the failure mode prevents hallucinated implementations.

---

## D2019 — Kimi vs Qwen: UMAP Wins Over BIRCH (2026-07-20)

**Summary:** Cross-examined Kimi's BIRCH+HDBSCAN claim against Qwen's UMAP+HDBSCAN with literature backing. UMAP wins.

**Kimi's claim:** "UMAP is non-deterministic even with random_state=42 due to NumPy BLAS parallelism."

**Why this is wrong:**
- UMAP's author (McInnes) explicitly states `random_state` ensures reproducible results
- NumPy BLAS affects floating-point precision (~1e-6), not cluster assignments
- BIRCH is a CF-tree for datasets too large for RAM — wrong tool for 2,697 principles
- BERTopic (15K+ stars) uses UMAP+HDBSCAN as default — production standard

**Qwen provides:** Literature reference (McInnes et al. 2018), synthetic validation test proving UMAP separates non-linear clusters PCA collapses.

**Result:** UMAP stays. D2005 confirmed and strengthened.

---

## D2020 — 3-Layer OMLX Memory Defense Adopted (2026-07-20)

**Summary:** Qwen's 3-layer memory defense replaces the simpler stress test from Gap A.

**Layer 1:** Bash stress test with `vm_stat` wired memory monitoring (not RSS). 5 consecutive pipeline runs. Kill criteria: >10% wired growth cumulative.

**Layer 2:** Python `MemoryGuard` context manager. `gc.collect()` + `mlx.core.clear_cache()` between batches. Monitors wired memory, raises `MemoryError` if growth exceeds threshold. Drop-in module: `pipeline/memory_guard.py`.

**Layer 3:** Process isolation via `multiprocessing.Process`. Each book extraction runs in a child process. When child exits, ALL wired memory reclaimed by kernel. Nuclear option for long runs.

**Status:** Replaces Gap A's single stress test. Phase 0, P0.0.

---

## D2021 — Cross-Domain Validation Protocol Adopted (2026-07-20)

**Summary:** Qwen's stratified 3-domain comparison replaces simpler Gap B methodology.

**Protocol:** Run pipeline on 3 domains (pricing, brand_strategy, negotiation). Gate: ≥2 of 3 must show ≥5 clusters AND <50% noise AND no single cluster >40% of items.

**Metrics collected:** n_books, n_chunks, n_extractions, n_clusters, noise_pct, largest_cluster_pct, pass_rate, sample FB titles.

**Status:** Phase 0 gate. After fixes re-run, execute on brand_strategy + negotiation in addition to pricing.

---

## D2022 — DeBERTa Threshold Calibration Protocol (2026-07-20)

**Summary:** Hand-label 50 FBs (SUPPORTED/CONTRADICTED/NEUTRAL) after first post-fix pipeline run. Compute optimal entailment threshold via F1 maximization across [0.45, 0.50, 0.55, 0.60, 0.65, 0.70].

**Current default:** 0.55 (from earlier documents). This is an educated guess. Calibration replaces guesswork with data.

**Status:** Phase 1. Run after pipeline produces 50+ verified FBs.

---

## D2023 — Claim-Type Detection Without LLM (2026-07-20)

**Summary:** Qwen's `detect_claim_type()` function classifies claims as FACT/CAUSAL/STATISTICAL/INFERENCE/OPINION using regex patterns before falling back to Phi-4-mini. Saves LLM compute.

**Rules:**
- STATISTICAL: contains numbers or percentages (`\d+%`, `\d+ percent`)
- CAUSAL: contains causal language (`because`, `causes`, `leads to`, `results in`, `due to`)
- INFERENCE: contains uncertainty markers (`probably`, `may`, `could`, `suggests`)
- OPINION: contains value judgments (`best`, `worst`, `should`, `ought`)
- FACT: everything else (default)

**Status:** Adopted into Phase 1 verification. Reduces DeBERTa calls by routing non-factual claims away.

---

## D2024 — Dichotomous SALSA Adopted (2026-07-20)

**Summary:** Kimi's binary-tree SALSA classification replaces single-call multi-label. Prevents cross-domain inflation (Kimi issue #5: 17/17 FBs labeled "cross-domain").

**How it works:** Series of YES/NO questions: "Is this tool-bound?" → "Is this about business?" → "Is this about design?" → ... → "Is this cross-domain?" → "Is this universal?" → Map to depth + domains.

**Status:** Adopted into Phase 1 (P1.7). Replaces inline SALSA prompt in `stage4_merge.py`.

---

## D2025 — IP Legal Framework Reference Added (2026-07-20)

**Summary:** Qwen's US/UK fair use analysis provides legal context for Gap D mitigations: Feist v. Rural (1991) — facts/ideas not copyrightable, only expression. Principles are ideas, not expression.

**Risk profile:** Purpose (transformative, commercial) = LOW-MEDIUM. Nature (non-fiction factual) = LOW. Amount (≤50 word snippets) = LOW. Market effect (cannot substitute book) = LOW.

**Status:** Reference incorporated into Gap D documentation. Does not replace legal consult (Phase 3).

| ID | Date | Decision |
|----|------|----------|
| R5 | 2026-06-14 | Generator ≠ Verifier |
| R7 | 2026-06-14 | temp=0.0 on all generation |
| R14 | 2026-06-14 | Schema stamps on all output |
| D150 | 2026-06-15 | Max 5 domains per FB |
| D316 | 2026-06-18 | Multi-label locked |
| D1057 | 2026-07-17 | Lazy-load OMLX models |
| D1058 | 2026-07-17 | Jargon decontamination |

---

## D2026 — M1: Constitution Re-Synced (2026-07-21)

**Summary:** CONSTITUTION.md updated to v2.1 to reflect all D2003–D2031 decisions, correct models (Qwen3-Coder, bge-m3, DeBERTa), 7-stage pipeline, UMAP+HDBSCAN, FActScore verification, and Phase 0–4 roadmap. Was 12 decisions behind.

**Changes:** Updated §0 model names, §2 architecture (3 layers, 7 stages), §3 decisions list, §4 phases, §5 startup (added OMLX stress test).

**Status:** ✅ DONE — Committed to conflicted-copy project directory.

---

## D2027 — M2: OMLX Server Watchdog Created (2026-07-21)

**Summary:** Existing 3-layer memory defense (memory_guard.py, justfile stress test, --memory-guard aggressive) only protects the Python process, not the OMLX server process itself. The OMLX server's wired memory growth (GitHub #2184) requires a separate server-level watchdog.

**Implementation:** `pipeline/omlx_watchdog.py` — monitors RSS via `ps aux`, restarts OMLX server when threshold exceeded. Pre-stage hook in pipeline runner.

**Status:** ✅ DONE — See `pipeline/omlx_watchdog.py`.

---

## D2028 — Local LLM Reliability Protocol (2026-07-21)

**Summary:** Local LLMs (Qwen3-Coder, Phi-4-mini) fail at architecture-from-scratch tasks due to 5 root causes: grounding problem (no code in context), hallucination amplifier (no rejection training), expertise gap (can't cross-reference), non-determinism (even at temp=0), verification paradox (hallucinated verifier). Mitigations: code-in-context, stateless extraction, golden examples, adversarial pairs, deterministic verifiers.

**Roundtable:** See `temp/LLM-RELIABILITY-ROUNDTABLE-HANDOFF.md` for 6 questions posed to other LLMs.

**Status:** ✅ DOCUMENTED — Mitigations adopted into handoff protocol.

---

## D2029 — Source Provenance Gate (2026-07-21)

**Summary:** Every decision, code patch, and review claim must trace to a specific source document (Kimi audit, Qwen patch, Grounded Review, Roundtable) or live code audit. No unattributed claims accepted. Gate enforced on all handoff evaluations.

**Status:** ✅ ACTIVE — Enforced in ULTIMATE-CROSS-EXAMINATION-2026-07-21.md.

---

## D2030 — Prompt Version Control (2026-07-21)

**Summary:** All LLM prompts (extraction, classification, verification) versioned alongside pipeline code. Prompt changes require decision log entry. Prompt fingerprint (SHA-256) stamped in output meta for reproducibility.

**Implementation:** Prompt strings in pipeline stages include version comment. Stage meta YAML includes `prompt_fingerprint` field.

**Status:** 🟡 PARTIAL — Version comments added. SHA-256 fingerprint not yet auto-generated (Phase 0.5).

---

## D2031 — Drift Detection Protocol (2026-07-21)

**Summary:** After any model swap, prompt change, or embedding model change, run golden-set comparison: 14-FB golden set → re-run pipeline → compare output distribution. Flag any deviation >15% in cluster assignments, domain labels, or verification pass rate.

**Thresholds:** Cluster Jaccard <0.85 → investigate. Domain label mismatch >15% → rollback. Verification pass rate ±10% → recalibrate thresholds.

**Status:** 🟡 DEFINED — Golden set exists (14 FBs). Automated comparison script deferred to Phase 0.5.
---

## D2032 — M3: D316 (Multi-Label) vs D2024 (Dichotomous SALSA) Conflict — UNRESOLVED (2026-07-21)

**Summary:** Two adopted decisions directly contradict each other. D316 (2026-06-18): "Multi-label locked" — FBs can be assigned to multiple disciplines. D2024 (2026-07-20): "Dichotomous SALSA adopted" — binary-tree classification forces EXACTLY ONE discipline per FB.

**Current state:** `pipeline/stage4_merge.py` implements D2024 (SALSA with VERIFY_MODEL, single-discipline output). CONSTITUTION.md §4 references D316 as "Multi-label (M3 under review)." Buglog does not track this as a bug because it's a constitutional conflict, not a code bug.

**Cross-examination verdict (ULTIMATE-CROSS-EXAMINATION-2026-07-21.md):** "Resolve: keep multi-label with threshold enforcement, reject dichotomous tree."

**Impact if not resolved:** Every SALSA-classified FB is forced into exactly one discipline. Cross-domain principles (e.g., "systems thinking" which spans business + design + engineering) get incorrectly narrowed. The knowledge graph loses multi-disciplinary edges.

**Required:** Maxwell (human gate G7) must decide:
- **Option A:** Keep D2024 (SALSA, single-discipline). Amend D316 to remove multi-label.
- **Option B:** Revert to D316 (multi-label). Replace SALSA with multi-label classifier. ~40 LOC change in stage4_merge.py.
- **Option C:** Hybrid — SALSA for primary discipline + secondary labels from cosine similarity against canonical set.

**Status:** 🔴 UNRESOLVED — Requires G7 human gate decision before Phase 1.
---

## D2033 — Project Folder Unified: 5 Variants → 1 (2026-07-21)

**Summary:** Dropbox sync conflicts had created 5 variants of "claude projects" in the Dropbox root. Cross-examination session consolidated all into a single project folder: `claude projects/maxwell os 2.0/`.

**Variants resolved:**
| Variant | Action |
|---------|--------|
| `claude projects +` | Source of real code — merged into main |
| `claude projects (Klaus Beyer's conflicted copy)` | Wrongly populated by previous session — nuked |
| `claude projects (clone)` | Stale copy — nuked |
| `claude projects+/maxwell os/` | Old v1 — nuked |
| `claude projects/maxwell os/` | Old v1 shell — nuked, but Dropbox recreates |

**Root cause of proliferation:** Dropbox FileProvider sync conflicts across devices. The `claude projects` folder itself cannot be deleted because Dropbox FileProvider keeps it alive via `com.dropbox.attrs` xattr and sync from other devices.

**Status:** ✅ RESOLVED — Single project folder at `/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0/`.

---

## D2034 — Knowledge Pipeline as Single Data Directory (2026-07-21)

**Summary:** All pipeline stage outputs, checkpoints, database, parquet snapshots, source books, and archives consolidated under `knowledge pipeline/` within the project folder. No data lives at root level.

**Structure:** `knowledge pipeline/{stage0_convert,stage1_chunk,...,stage6_commit}/{run_id}/output`. Each stage self-contained with checkpoint + log + meta per run.

**Config:** `config/pipeline_config.yaml` updated to prefix all stage paths with `knowledge pipeline/`. `pipeline/pipeline_paths.py` resolves all paths through the YAML config.

**Status:** ✅ DONE — `pipeline_config.yaml` and `pipeline_paths.py` both updated.

---

## D2035 — LaunchAgent Cleanup (2026-07-21)

**Summary:** Two legacy LaunchAgents from v1 were actively running every few minutes, trying to execute deleted scripts and recreating the `claude projects/maxwell os/logs/` directory:
- `com.maxwell.memoryguardian.plist` → `memory_guardian.py` (deleted v1 script)
- `com.maxwellos.watchdog.plist` → `watchdog_guard.py` (deleted v1 script)

**Fix:** Both plists unloaded via `launchctl unload` and renamed to `.DISABLED` suffix. Replaced by v2.0's `pipeline/omlx_watchdog.py` (on-demand, not daemonized).

**Status:** ✅ DONE — No more ghost log files or directory recreation.

---

## D2036 — Governance Docs Rewritten for v2.1 (2026-07-21)

**Summary:** Four governance documents were stale and referencing v1 paths, models, or incomplete v2.0 state. All rewritten during cross-examination session:

| Doc | Before | After |
|-----|--------|-------|
| `agent/session_seed.yaml` | 1797 lines of v1 cruft (old tools, old domains, S3A system) | 125 lines v2.1 — correct models, 7-stage, UMAP, bge-m3, watchdog |
| `AGENTS.md` | Wrong models (Qwen3.6, nomic), 6-stage, dead `config/decisions.yaml` ref | v2.1 — Qwen3-Coder, bge-m3, DeBERTa, 7-stage+1.5, watchdog boot step |
| `MASTER-TASK-REGISTER.md` | No Phase 0 tracking, no BL/BT gaps | Appended: 14 P0 tasks, 11 BL/BT gaps, 8 governance fixes, M3 conflict |
| `DECISION-LOG.md` | 27 decisions, D2025 last entry | 34 decisions, D2000-D2032, M3 conflict logged as D2032 |

**Status:** ✅ DONE — All four docs synced with v2.1 reality.

---

## D2037 — Buglog Accumulation Rule Formalized (2026-07-21)

**Summary:** Standing rule formalized and added to buglog protocol: whenever recurring bugs and issues accumulate during a session, they MUST be gathered in `governance/buglog.md` with full documentation (severity, file, symptom, root cause, proposed fix, source). This enables LLM handoff with complete context.

**Trigger:** After any code review, pipeline run, or cross-examination session, accumulate all discovered bugs.

**Handoff trigger:** 5+ unresolved bugs → append full buglog to all LLM handoff documents (C15).

**Status:** ✅ ACTIVE — Buglog updated with 22 bugs (17 original + 5 from this session). 16 of 17 original bugs now RESOLVED. BUG-017 (OMLX memory leak) remains open pending stress test.

---

## D2038 — pipeline_paths.py Legacy Alias Fix (2026-07-21)

**Summary:** The new thin YAML-based `pipeline_paths.py` did not export three names that all 7 pipeline stage files import: `CHECKPOINT_DIR`, `DB_PATH`, `OMLX_BIN`. Stage files failed at import time.

**Fix:** Added legacy aliases at end of `pipeline_paths.py`:
- `CHECKPOINT_DIR = PROJECT_ROOT / "knowledge pipeline" / "checkpoints"`
- `DB_PATH = PROJECT_ROOT / "knowledge pipeline" / "maxwell.db"`
- `OMLX_BIN = _CFG["services"]["omlx"]["bin"]`

**Status:** ✅ DONE — All 29 pipeline .py files pass syntax check.

---

## D2039 — 4-Layer Markdown Cleaning Pipeline (Phase 0.5) — Registered 2026-07-21

**Summary:** From ULTIMATE-CROSS-EXAMINATION-HANDOFF.md item #1. 80 LOC. Directly addresses Kimi issues #1, #3, #4, #7. Highest-leverage quality improvement per line of code. Strips formatting artifacts, normalizes paragraphs to 30-250 words, wires cleaning into Stage 1.

**Source:** Final Architecture proposal, Kimi code audit. Originally logged as D2012, now re-registered with full sequencing.

**Status:** ⬜ TODO — Phase 0.5 (after Phase 0 fixes verified).

---

## D2040 — Contextual Retrieval (Anthropic 2024 Pattern) — Registered 2026-07-21

**Summary:** From handoff item #2. Before embedding each chunk, prepend 1-2 sentences of book/chapter context. For a corpus finding CONVERGENT principles, this distinguishes "both about anchoring" from "both generically about pricing." Worth a Phi-4-mini pass at ingestion.

**Source:** Grounded Review, Anthropic contextual retrieval paper (Sept 2024).

**Status:** ⬜ TODO — Phase 5 (scale phase, after 500+ FBs).

---

## D2041 — Outlines Constrained Decoding — Registered 2026-07-21

**Summary:** From handoff item #3. Guarantees JSON schema compliance from Qwen3-Coder via token-level constraint. Eliminates json_repair.py (391 LOC). Stage 2/4 output becomes structurally guaranteed. Requires OMLX compatibility spike first.

**Source:** Final Architecture, Fixed Implementation spec. MTR references as "Outlines/XGrammar spike (H2)."

**Status:** ⬜ TODO — Phase 1 (spike first; if OMLX-compatible, adopt).

---

## D2042 — DFlash Speculative Decoding — Registered 2026-07-21

**Summary:** From handoff item #4. OMLX 0.4.4+ speculative decoding. ~1.5-2.5x speedup for extraction. ~400MB draft model. On M1 Max, cuts Stage 2 from hours to minutes.

**Source:** Final Architecture proposal. Mentioned in D2006/D2013 context.

**Status:** ⬜ TODO — Phase 1 (requires OMLX 0.4.4+ verification).

---

## D2043 — Source-Substring Gate — Registered 2026-07-21

**Summary:** From handoff item #5. Every extracted principle MUST contain a substring from the source text. Prevents hallucinated domain labels and fabricated principles. ~30 LOC in stage2_extract.py.

**Source:** Final Architecture, Kimi code audit.

**Status:** ⬜ TODO — Phase 1.

---

## D2044 — NLI Pre-Merge Coherence Check — Registered 2026-07-21

**Summary:** From handoff item #6. Before merging principles into an FB, DeBERTa checks for pairwise contradictions. Prevents Kimi issue #7 (conceptually broken FBs where contradictory principles get merged).

**Source:** Final Architecture, Qwen patches.

**Status:** ⬜ TODO — Phase 1.

---

## D2045 — Golden Few-Shot Examples — Registered 2026-07-21

**Summary:** From handoff item #7. 2-3 hand-crafted FBs injected into Stage 4 prompt as YAML file. Directly addresses template collapse (Kimi issue #1). Uses real calibration data from 14-FB triad run + 17-FB pricing run.

**Source:** Final Architecture, Kimi code audit, ROUNDTABLE-HANDOFF.

**Status:** ⬜ TODO — Phase 1.

---

## D2046 — SALSA Dichotomous Prompting — Registered 2026-07-21

**Summary:** From handoff item #8. Classification via series of binary choices ("Is this about pricing OR not?"), not single multi-label call. Prevents cross-domain inflation (Kimi issue #5: 17/17 FBs labeled cross-domain). Already partially implemented in stage4_merge.py. See also D2024 and D2032 (M3 conflict).

**Source:** Stack Audit, ROUNDTABLE-HANDOFF. Originally D2024.

**Status:** ⚠️ PARTIAL — Implemented in code but conflicts with D316 (M3 unresolved). See D2032.

---

## D2047 — Spec Tools: Pydantic-Encoded OpenSPDD — Registered 2026-07-21

**Summary:** From handoff item #9. Rigid Pydantic-schema template prevents local LLMs from hallucinating implementations. Critical for generating ~2,700 LOC of fixes with local models. See also D2018 (earlier spec tools decision).

**Source:** Stack Audit, AI-HANDOFF-2026-07-18-STACK-AUDIT.md.

**Status:** ✅ ADOPTED — Used for this session's code generation. Template format defined.

---

## D2048 — Knowledge Layer: Parquet + LanceDB + DuckDB — Registered 2026-07-21

**Summary:** From handoff item #10. Canonical storage architecture from handoff docs. Parquet readable in 10 years (no vendor lock-in). LanceDB for vector storage. DuckDB for SQL analytics. Anytype = presentation layer only, not canonical storage.

**Source:** AI-HANDOFF-2026-07-18-KNOWLEDGE-LAYER-ARCHITECTURE.md. Currently using SQLite + sqlite-vec as Phase 0.

**Status:** ⬜ TODO — Phase 2 (requires 100+ FBs before migration).

---

## D2049 — Layer 2 Orchestration Spec — Registered 2026-07-21

**Summary:** From handoff item #11. FB→PT→PI→Recipe→Trust Ledger→Conductor Loop chain. 3-zone body template, fb_reliability scoring. Spec'd in FOUNDATION-BLOCK-TO-SKILL-SPEC.md v1.1. 0 lines built. THIS IS THE PRODUCT — the pipeline is just the factory.

**Source:** FOUNDATION-BLOCK-TO-SKILL-SPEC.md. Originally D2015 (validated, deferred).

**Status:** ⬜ TODO — Phase 2 (requires 100+ verified FBs).

---

## D2050 — Lifetime License Model — Registered 2026-07-21

**Summary:** From handoff item #12. More aligned with sovereignty than SaaS. £750-1,000 Beta Kit. Domain expansions £300-500. Major upgrades £400-600. From MISSION.md.

**Source:** MISSION.md. Originally D2016.

**Status:** ✅ ADOPTED — Defined in MISSION.md. Implementation Phase 4.

---

## D2051 — FastFit Classification at Scale — Registered 2026-07-21

**Summary:** From handoff item #13. Trains lightweight classifier from 500+ LLM-labeled FBs. Not needed for triad (14 FBs), essential for 800 books. Model2Vec embeddings + FastFit inference at ~0.5ms per FB.

**Source:** Stack Audit, AI-HANDOFF-2026-07-18-STACK-AUDIT.md. MTR T2.2.

**Status:** ⬜ TODO — Phase 5 (blocked until 500+ S7-cleaned FBs exist).

---

## D2052 — Golden FB Calibration Data — Registered 2026-07-21

**Summary:** From handoff item #14. Real calibration data: 14 FBs from triad run (Maxwell-reviewed: 3 PASS, 10 FLAG, 1 QUARANTINE) + 17 FBs from pricing batch (Kimi-reviewed: 4 ARCHIVE, 8 KEEP WITH NOTE, 4 KEEP, 1 EXILE). Inject as few-shot examples into Stage 4 prompt per D2045.

**Source:** ROUNDTABLE-HANDOFF, Kimi code audit, temp/test output/.

**Status:** ⬜ TODO — Phase 1 (data exists, needs injection into prompt).

---

## D2053 — 6 Unresolved Gaps Registered — Registered 2026-07-21

**Summary:** All 6 gaps from ULTIMATE-CROSS-EXAMINATION-HANDOFF.md Part 1 formally registered:

| Gap | Description | Decision |
|-----|-------------|----------|
| A | OMLX kernel memory leak untested | D2020 (stress test protocol defined) |
| B | Single-domain bias (only pricing tested) | D2053-B (run brand strategy domain after Phase 0) |
| C | Author-weighted BORP | D2053-C (~30 LOC, Phase 1) |
| D | IP/copyright risk unexamined | D2025 (mitigations: 50-word cap, hashing, transformation check) |
| E | DeBERTa weak on causal/statistical claims | D2023 (claim-type routing: FACT→DeBERTa, CAUSAL→Phi-4-mini, STATISTICAL→source check) |
| F | Cross-domain validation missing | D2021 (stratified 3-domain comparison protocol) |

**Status:** ⬜ All 6 gaps sequenced in MASTER-TASK-REGISTER with activation gates.

---

## D2054 — asad.txt Revised Cross-Examination Registered (2026-07-21)

**Summary:** temp/asad.txt (462 lines) is a revised cross-examination that provides a 52-item granular roadmap with LOC estimates per item, sources, and activation gates across Phase 0–5. Was missed during initial cross-examination consolidation. Now fully imported into MASTER-TASK-REGISTER.md as the canonical task list.

**Key sections:**
1. Modular Architecture — re-evaluated as MORE important (Apple Silicon model churn justification)
2. Intent-Based Filtering — deep examination of semantic vs keyword pre-filter
3. 4-Layer Cleaning Pipeline — most rigorously argued proposal across all documents
4. FActScore + DeBERTa NLI Verification — endorsed by every evaluation
5. Full 52-item roadmap with LOC per item and sources
6. 6 gaps (A-F) with specific mitigations

**Status:** ✅ IMPORTED — 69 items now tracked in MASTER-TASK-REGISTER.md (14 Phase 0 ✅, 55 remaining across Phase 0.5–5).
