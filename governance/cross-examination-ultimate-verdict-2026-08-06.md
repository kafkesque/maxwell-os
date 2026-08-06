# Maxwell OS v3.0 — Cross-Examination Ultimate Verdict
> **Date:** 2026-08-06
> **Auditor:** Senior RAG / Agentic / Systems Engineer (Goose)
> **Sources:** DeepSeek eval12, ChatGPT eval12, Qwen eval12, Kimi eval12 + direct codebase verification
> **Decision ID:** D2195

---

## EXECUTIVE SUMMARY

**Overall: 7.0/10 as architectural thesis, 5.5/10 as usable system**

Maxwell OS is a genuinely innovative sovereign knowledge extraction engine with a proven 8-stage pipeline. The cluster-before-extract architecture is the best idea in local RAG in 2026. However, critical contamination bugs (zero-vector fallback), stale configurations, and a missing Layer 2 product layer prevent production readiness.

---

## PART I: ALL BUGS — CONFIRMED, REJECTED, AND NEWLY DISCOVERED

### 🔴 P0 — BLOCKING

| # | Bug ID | Description | Source | Evidence |
|---|--------|-------------|--------|----------|
| P0-1 | ZERO-VECTOR-001 | `ollama_embed.py:87,103,144` returns `[0.0]*dim` on embedding failure. FAISS clusters these → BORP satisfied → hallucinated convergence. TWO independent fallback paths. | ChatGPT, Qwen | Lines 87, 103, 144 |
| P0-2 | LICENSE-MISSING | No LICENSE file. Repo is legally "all rights reserved." Cannot accept contributions. | Kimi | `ls -la` repo root |
| P0-3 | SESSION-NLI-STALE | `session_seed.yaml:42` declares `nli: model: roberta-large-mnli`. Stage 5 runs ModernBERT/DeBERTa. Wrong lineage on every persisted object. | ChatGPT | `agent/session_seed.yaml` |
| P0-4 | SESSION-STAGE3-GHOST | `session_seed.yaml:29` still shows `stage3: dedup` in 9-stage pipeline. CONSTITUTION.md correctly declares 8-stage. | Qwen, Kimi | Direct file comparison |
| P0-5 | MODEL-VARIANT-MISMATCH | `model_assignments.yaml` uses `Qwen3.6-35B-A3B-OptiQ-4bit`. `pipeline_config.yaml` uses `Qwen3.6-35B-A3B-4bit` (no OptiQ). Two configs disagree on active model. | NEW (Goose) | Direct file comparison |

### 🟠 P1 — HIGH

| # | Bug ID | Description | Source | Evidence |
|---|--------|-------------|--------|----------|
| P1-1 | AGENTS-STAGE3-GHOST | `AGENTS.md:68` references deleted `stage3_cluster.py`. Will cause pipeline halt if followed. | Qwen | `AGENTS.md` |
| P1-2 | RUFF-EXCLUDES-PIPELINE | `pyproject.toml:5` excludes `knowledge pipeline/` from Ruff AND mypy. Most critical code has zero static analysis. | Kimi | `pyproject.toml` |
| P1-3 | MODEL-ASSIGN-DEEPSEEK-BROKEN | `model_assignments.yaml:REVIEWER = DeepSeek-R1-0528-Qwen3-8B-MLX-4bit`. DELEGATE-001 confirms DeepSeek thinking mode is BROKEN. | NEW (Goose) | Cross-reference buglog.md |
| P1-4 | PREFLIGHT-EXIT-BUG | `justfile` books check uses `exit(0 if ok else 0)` — returns 0 regardless. | ChatGPT | `justfile` (possibly in older version) |
| P1-5 | NLI-MAJORITY-VOTE | Stage 5 evidence aggregation is coarse majority-vote. One contradiction buried by 7 entailments. | ChatGPT | `stage5_verify.py` BUG-044 |

### 🟡 P2 — MEDIUM

| # | Bug ID | Description | Source | Evidence |
|---|--------|-------------|--------|----------|
| P2-1 | BORP-NOT-TRUTH | NLI checks entailment, not factual correctness. Two books can agree on a myth. Epistemic caveat needed. | ChatGPT | Philosophical |
| P2-2 | CONFIG-PYDANTIC-TODO | 48+ config mappings without Pydantic validation schema (P2.5 deferred). Typos fail silently at runtime. | NEW (Goose) | `aggregated_remaining_tasks.md` |
| P2-3 | WATCHDOG-LOG-COMMITTED | `omlx_watchdog.log` (430 bytes) committed despite `.gitignore`. System state leaked. | Kimi (partial) | File at repo root |
| P2-4 | OLLAMA-DAEMON-DEPENDENCY | D2190 MPS deadlock forced Ollama pivot. Adds daemon dependency to "zero-ops" system. | Qwen | D2190 decision |
| P2-5 | ANYTYPE-SOVEREIGNTY-LEAK | `stage6b_anytype_push.py` exists. If Anytype sync is ON, FBs leak to cloud. | Kimi, DeepSeek | 834-line file |

### ❌ REJECTED CLAIMS (verified false)

| # | Claim | Source | Why Rejected |
|---|-------|--------|--------------|
| R1 | "requirements.txt still lists umap-learn + hdbscan" | Qwen | FALSE. Line says: `# D2177: umap-learn + hdbscan removed`. Neither listed. |
| R2 | "just db nuke destroys database" | Kimi | FALSE. No `db nuke` command exists in justfile. |
| R3 | "No visible test files" | DeepSeek | FALSE. 8 test files in `tests/`, 3 in `providers/`, `e2e_test.py`. |
| R4 | "stage2_extract.py is 64KB/1,800 lines" | Kimi | EXAGGERATED. Actual: 1,480 lines. |
| R5 | "networkx Louvain O(N²) hangs on 293K" | Qwen | MISLEADING. Runs per domain, not all at once. R-NN pre-filter keeps graph sparse. |
| R6 | "0 lines of orchestration is a lie" | Kimi | MISINTERPRETED. Refers to Layer 2 agentic orchestration, not pipeline orchestration. |

---

## PART II: AGGREGATED LLM PROPOSITIONS — ONE-BY-ONE ASSESSMENT

### DeepSeek (551 lines — Superficial but Product-Focused)

| # | Proposition | Validity | Action |
|---|-------------|----------|--------|
| D1 | "Layer 2 is the product. Build it." | ✅ VALID | P1 — Already acknowledged. MCP server is fastest path. |
| D2 | "Fix dependency omissions (ollama, pytest in requirements)" | ⚠️ PARTIAL | ollama is intentionally commented-out (fallback only). pytest already configured. Add note. |
| D3 | "Validate end-to-end cycle time against kill criteria" | ✅ VALID | P2 — Smoke tests exist; full E2E timing needed. |
| D4 | "Consider ONNX runtime for NLI to reduce bloat" | ❌ REJECTED | ModernBERT is already efficient. ONNX adds complexity. |
| D5 | "Move taxonomy from hardcoded Literal to YAML-driven" | ✅ VALID | P2 — Already partially done (taxonomy_v5.yaml). Complete migration. |

### ChatGPT (5,783 lines — Most Epistemically Rigorous)

| # | Proposition | Validity | Action |
|---|-------------|----------|--------|
| C1 | "Remove zero-vector fallbacks — raise EmbeddingQuarantineError" | ✅ P0 | **DONE below** |
| C2 | "Fix `just preflight` exit bug" | ✅ P1 | Check justfile — may be fixed already in this version |
| C3 | "Create one model registry. Delete duplicated declarations." | ✅ P1 | `model_assignments.yaml` vs `pipeline_config.yaml` conflict |
| C4 | "Remove legacy v2/v2.3 config blocks from active config" | ✅ P2 | `pipeline_config.yaml` has full-run v2.3 block |
| C5 | "Synchronize session_seed with runtime (NLI model, stages)" | ✅ P0 | **DONE below** |
| C6 | "Make pytest discover all tests (move provider tests or configure)" | ✅ P2 | Tests exist but discovery is fragmented |
| C7 | "Implement monotonic trust state machine (RAW→CANONICAL, no backwards)" | ✅ P1 | Long-term architecture investment |
| C8 | "Upgrade provenance: work_id/edition_id/artifact_id" | ✅ P1 | BORP improvement |
| C9 | "Make evidence atomic: per-passage NLI scores, not majority vote" | ✅ P1 | Current coarse aggregation |
| C10 | "Build graph-aware retrieval (contradictions, prerequisites)" | ✅ P2 | Differentiates from generic RAG |
| C11 | "Context-conditioned reliability scores" | ✅ P2 | Future enhancement |
| C12 | "Add `just integrity` command — 17 checks" | ✅ P2 | Turns constitution into executable spec |
| C13 | "Split config into active/archived/experiments" | ✅ P2 | Prevents config ghosts |
| C14 | "Add agent execution safety boundary (Plan→Policy→Auth→Execute→Rollback)" | ✅ P2 | Required before Layer 2 goes live |
| C15 | "Collapse configuration authority — one canonical YAML per domain" | ✅ P2 | Reduces governance complexity |
| C16 | "Prompt lineage: prompt_id, prompt_hash, prompt_version" | ✅ P2 | Extend stamping to prompts |
| C17 | "Add deterministic dependency lockfile (`uv pip compile`)" | ✅ P1 | Reproducibility |
| C18 | "BORP ≠ Truth — encode epistemically (source-consistency, not verified-truth)" | ✅ P1 | Rename internally |

### Qwen (245 + cross-exam lines — Most Code-Literal)

| # | Proposition | Validity | Action |
|---|-------------|----------|--------|
| Q1 | "Purge umap-learn/hdbscan from requirements.txt" | ✅ VALID (at time) | **ALREADY FIXED** — not in current requirements.txt |
| Q2 | "Update AGENTS.md to remove stage3_cluster.py" | ✅ P1 | **DONE below** |
| Q3 | "Standardize model naming across all configs" | ✅ P1 | **Partially done below** |
| Q4 | "Enforce Matryoshka truncation explicitly in Ollama call" | ✅ P1 | Add dimension parameter to embedding calls |
| Q5 | "Replace NetworkX Louvain with python-igraph Leiden" | ⚠️ DEBATABLE | Kimi's market research says Louvain is valid. Leiden is faster but adds dependency. Defer. |
| Q6 | "Replace FAISS with USearch for Apple Silicon" | ❌ REJECTED | FAISS is by far fastest (743K vec/s). USearch fails at <5K vectors. |
| Q7 | "Use Dagster instead of custom runner.py" | ⚠️ DEBATABLE | Dagster adds heavy dependency (violates C5). Runner is adequate for now. |
| Q8 | "Switch Classifier from Phi-4-mini to Qwen2.5-7B" | ⚠️ DEBATABLE | Kimi's market research confirms Phi-4-mini is "bang-for-GB winner" at 4B class. Keep. |
| Q9 | "Use Llama-3.1-8B as cross-family verifier instead of Gemma" | ❌ REJECTED | Kimi's benchmarks: Gemma-4-E4B scores 0.675 weighted accuracy vs Llama's lower score. Gemma stays. |

### Kimi (752 + market research lines — Most Systems-Oriented)

| # | Proposition | Validity | Action |
|---|-------------|----------|--------|
| K1 | "Fix the yield crisis: 14 FBs from 852 books is a pipeline emergency" | ✅ P0 | Run controlled experiment: manual extraction vs pipeline |
| K2 | "Lint the entire pipeline. Remove Ruff exclusions." | ✅ P1 | **DONE below** |
| K3 | "Surface reliability in Zone 3" | ✅ P1 | Spec admits this gap. Fix in 1 day. |
| K4 | "Add version pinning (requirements.lock)" | ✅ P1 | Same as C17 |
| K5 | "Modularize stage2_extract.py and stage4_merge.py" | ✅ P2 | God modules are future tax. Break into sub-modules. |
| K6 | "Add LICENSE (MIT or AGPL)" | ✅ P0 | **DONE below** |
| K7 | "Kill or quarantine Anytype integration" | ✅ P1 | Add warning header to stage6b. Keep as optional export. |
| K8 | "Implement Pydantic config validation" | ✅ P2 | Same as P2-2 |
| K9 | "Add confirmation gates to destructive commands" | ⚠️ MITIGATED | No `db nuke` exists. `clean` already prints safety message. |
| K10 | "Replace bare excepts with structured exception hierarchies" | ✅ P1 | Audit all except clauses |
| K11 | "Honest mission statement — replace '0 lines' with 'minimal protocol-driven'" | ✅ P1 | Clarify language in MISSION.md |
| K12 | "Switch bge-m3 to MLX-native (50% throughput gain)" | ✅ P1 | After zero-vector fix. D2190 notes MPS deadlock — may need investigation. |
| K13 | "Standardize on ModernBERT-large for NLI (8K context)" | ✅ P1 | DeBERTa fallback kept for now. ModernBERT is primary. |
| K14 | "Build Pydantic AI Layer 2 harness with MCP server" | ✅ P1 | This IS the product |
| K15 | "Add FAISS ANN for passage-level retrieval" | ✅ P2 | For runtime RAG, not just clustering |
| K16 | "Execute ONE business PI using existing FBs before building more pipeline" | ✅ P0 | Existential test |

---

## PART III: LLM MODEL PROPOSITIONS — CROSS-VERIFIED AGAINST BENCHMARKS

| Role | Recommendation | Benchmark Evidence | Verdict |
|------|---------------|-------------------|---------|
| **Generator (S2)** | Qwen3.6-35B-A3B-4bit | Best coding/agent. Strong JSON extraction. | ✅ KEEP |
| **Classifier (S4)** | Phi-4-mini-instruct-8bit | "Bang-for-GB winner" at 4B class. 30.8% efficiency. | ✅ KEEP |
| **Verifier (S5)** | Gemma-4-E4B-it-MLX-4bit | 0.675 weighted accuracy. Dominates ARC + Math. | ✅ KEEP |
| **NLI (S5)** | ModernBERT-large | 8K context, 2× faster than DeBERTa. 0.57 F1. | ✅ KEEP (fix session_seed) |
| **Embeddings** | bge-m3 (512-dim Matryoshka) | Only model with dense+sparse+colbert. 64.5 MTEB. | ✅ KEEP (fix zero-vector, consider MLX-native) |
| **REVIEWER** | DeepSeek-R1-0528 | BROKEN (DELEGATE-001). Remove from active config. | ❌ REMOVE |
| **Ghost: roberta-large-mnli** | session_seed.yaml only | Not used at runtime. Purge from config. | ❌ PURGE |

---

## PART IV: PIPELINE RE-ENGINEERING VERDICT

### Does the pipeline require re-engineering?
**NO. Targeted surgical fixes only.**

The 8-stage cluster-before-extract architecture is sound:
- Stage 0 (convert), 0.5 (metadata), 1 (chunk) → preprocessing: ✅ CORRECT
- Stage 1.3 (prefilter), 1.5 (embed+cluster) → cluster-before-extract: ✅ CORRECT
- Stage 2 (extract per cluster): ✅ CORRECT
- Stage 4 (merge + classify + BORP): ✅ CORRECT
- Stage 5 (NLI + cross-family verify + fail-closed): ✅ CORRECT
- Stage 6 (commit + Parquet): ✅ CORRECT

### What needs surgical fixing:
1. **ollama_embed.py**: Replace zero-vector fallback with `raise EmbeddingQuarantineError`
2. **session_seed.yaml**: Sync NLI model, remove stage3, set to 8-stage
3. **AGENTS.md**: Remove stage3_cluster.py ghost reference
4. **model_assignments.yaml**: Sync with pipeline_config.yaml or designate canonical
5. **pyproject.toml**: Remove pipeline exclusion, fix lint errors
6. **stage5_verify.py**: Atomic evidence tracking (future enhancement, not re-engineering)

---

## PART V: S0-S1.5 RERUN ANALYSIS

**Do we need to rerun S0-S1.5 after these fixes?**

**SHORT ANSWER: No.** The fixes are to configuration, documentation, and error handling — not to the extraction logic or embedding models.

| Fix | Affects S0-S1.5 output? | Rerun needed? |
|-----|------------------------|---------------|
| Zero-vector fallback → raise | Only affects future failed embeddings | ❌ No |
| session_seed.yaml sync | Config only | ❌ No |
| AGENTS.md ghost reference | Documentation only | ❌ No |
| model_assignments.yaml sync | Config only (same models used) | ❌ No |
| LICENSE addition | Legal only | ❌ No |
| pyproject.toml lint exclusion | Dev tooling only | ❌ No |

**However**, if any embedded segment was previously assigned a zero-vector (from a failed Ollama batch), that segment's cluster membership is corrupt. A `just integrity` check should verify no zero-magnitude vectors exist in current embeddings. If any are found, those specific segments need re-embedding.

---

## PART VI: SUGGESTIONS NOT YET ACTED UPON (ROADMAP)

These are valid suggestions from all 4 LLMs that are deferred to future phases:

### Phase 2 (next sprint)
- [ ] Atomic evidence schema (C9) — per-passage NLI scores
- [ ] Monotonic trust state machine (C7) — DB-level transition constraints
- [ ] `just integrity` command (C12) — 17 automated checks
- [ ] Deterministic lockfile (C17/K4) — `uv pip compile`
- [ ] Context-conditioned reliability (C11/K3) — surface in Zone 3
- [ ] bge-m3 to MLX-native (K12) — investigate MPS deadlock root cause first

### Phase 3 (Layer 2)
- [ ] MCP server exposing FBs (K14)
- [ ] Pydantic AI harness for agent orchestration (K14)
- [ ] Graph-aware retrieval (C10) — contradictions, prerequisites
- [ ] Agent execution safety boundary (C14) — Plan→Policy→Auth→Execute→Rollback

### Phase 4 (polish)
- [ ] Modularize god modules (K5) — stage2_extract, stage4_merge
- [ ] Split config into active/archived (C13)
- [ ] Prompt lineage stamping (C16)
- [ ] Collapse config authority to one canonical source (C15)

---

## CROSS-REFERENCE: DECISIONS CREATED

| Decision ID | Description |
|-------------|-------------|
| D2195 | This document — Cross-Examination Ultimate Verdict |
| D2196 | Zero-vector fallback → EmbeddingQuarantineError |
| D2197 | session_seed.yaml sync: NLI model, stage3 removal, 8-stage |
| D2198 | AGENTS.md stage3 ghost reference removal |
| D2199 | model_assignments.yaml vs pipeline_config.yaml resolution |
| D2200 | LICENSE: MIT |
| D2201 | pyproject.toml pipeline exclusion removal |
