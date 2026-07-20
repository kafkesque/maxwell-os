# Maxwell OS v2.0 — Master Task Register
> **Phase 1: Triad proof. Phase 2: Scale. Phase 3: Business ops.**
> **Archive:** `archive/maxwell_os_v1/` contains all v1 history.

---

## 🔴 PHASE 1 — TRIAD (Prove the pipeline works)

**Goal:** 3 books → 10-20 FBs → verified → SQLite → retrieval test

| # | Task | Depends On | Status |
|---|------|------------|--------|
| T1.1 | Write `pipeline/stage0_convert.py` — EPUB/PDF → MD via Pandoc/Docling | — | ✅ DONE |
| T1.2 | Write `pipeline/stage1_chunk.py` — MD → segments + SHA-256 dedup | — | ✅ DONE |
| T1.3 | Write `pipeline/stage2_extract.py` — Qwen3.6 extract principles + MinHash dedup | T1.2 | ✅ DONE |
| T1.4 | Write `pipeline/stage3_cluster.py` — Embed + HDBSCAN + semantic dedup | T1.3 | ✅ DONE |
| T1.5 | Write `pipeline/stage4_merge.py` — Clusters → FBs + SALSA classify | T1.4 | ✅ DONE |
| T1.6 | Write `pipeline/stage5_verify.py` — BORP + Phi-4-mini verify + human queue | T1.5 | ✅ DONE |
| T1.7 | Write `pipeline/stage6_commit.py` — SQLite + Parquet export | T1.6 | ✅ DONE |
| T1.8 | Write `pipeline/schemas.py` — Pydantic v2 models with Literal types | — | ✅ DONE |
| T1.9 | Write `pipeline/stamp.py` — @stamp decorator for R14 | — | ✅ DONE |
| T1.10 | Write `pipeline/omlx_call.py` — Simplified OMLX wrapper with timeout | — | ✅ DONE |
| T1.11 | Write `pipeline/retrieve.py` — Hybrid search: SQL + FTS5 + sqlite-vec | T1.7 | ✅ DONE |
| T1.12 | Write `pipeline/query.py` — CLI browser for FBs | T1.7 | ✅ DONE |
| T1.13 | Write `pipeline/status.py` — Pipeline status dashboard | T1.7 | ✅ DONE |
| T1.14 | Test SALSA on OMLX (logit restriction) | — | ✅ DONE (1 class error, 93% valid) |
| T1.15 | Select 3 triad books, verify they exist in books/ | — | ✅ DONE (14 diverse books selected) |
| T1.16 | Run triad end-to-end, verify output | T1.1-T1.14 | ✅ DONE (see report below) |
| T1.17 | Maxwell reviews triad FBs (S7 human gate) | T1.16 | ⬜ TODO |

---

## 🟡 PHASE 2 — SCALE (After triad success)

| # | Task | Depends On | Status |
|---|------|------------|--------|
| T2.1 | Run pipeline on all 850+ books | Phase 1 | ⬜ BLOCKED |
| T2.2 | Train FastFit classifier on 500+ human-audited FBs | T2.1 | ⬜ BLOCKED |
| T2.3 | Add relationship extraction (supports/contradicts/extends) | T2.1 | ⬜ BLOCKED |
| T2.4 | Push verified FBs to Anytype | T2.1 | ⬜ BLOCKED |

---

## 🟠 PHASE 1.5 — PROPERTY LOGIC (Parallel with golden set building)

**Goal:** Fix Channel B contamination (data loss), wire classification infrastructure already in config/, evaluate PT/GE for pipeline integration. All of these can run in parallel with golden set building — they are infrastructure, not calibration.

### P1.5-A: Raw Label Preservation (CRITICAL — data loss bug)
| # | Task | Depends | Status |
|---|------|---------|--------|
| P1.5-A1 | Add `domain_raw`, `discipline_raw` to `schemas.py` FB model | — | ✅ DONE |
| P1.5-A2 | Update `stage4_merge.py` to preserve raw LLM output BEFORE validation, never overwrite | P1.5-A1 | ✅ DONE |
| P1.5-A3 | Update `stage6_commit.py` to handle new fields (schema, INSERT, migration, Parquet) | P1.5-A2 | ✅ DONE |
| P1.5-A4 | Backfill existing DB (14 FBs) — raw set to canonical (originals lost to Channel B) | P1.5-A3 | ✅ DONE |

### P1.5-B: Synonym-Based Canonical Matching
| # | Task | Depends | Status |
|---|------|---------|--------|
| P1.5-B1 | Load `config/synonym_map.yaml` + taxonomy `raw:` aliases into 643-entry lookup dict | — | ✅ DONE |
| P1.5-B2 | Add synonym matching to stage4 classification fallback: non-canonical label → match → canonical if found, "emerging" + raw preserved if not | P1.5-B1, P1.5-A2 | ✅ DONE |
| P1.5-B3 | Test on existing labels: "Visual Communication"→"graphic design", "DataVis"→"data visualization", etc. | P1.5-B2 | ✅ DONE |

### P1.5-C: Folder Routing
| # | Task | Depends | Status |
|---|------|---------|--------|
| P1.5-C1 | Write `pipeline/route.py` — `route_fb_folder()`, `count_raw_labels()`, `export_raw_label_report()` | P1.5-A1 | ✅ DONE |
| P1.5-C2 | Verify priority chain: canonical → raw → "emerging" works for all test cases | P1.5-C1 | ✅ DONE |

### P1.5-E: Provenance Fields (pipeline_run_id + s3_original_domain)
| # | Task | Depends | Status |
|---|------|---------|--------|
| P1.5-E1 | Add `pipeline_run_id` to `StampedRecord` (UUID, generated once per run, reused) | — | ✅ DONE |
| P1.5-E2 | Add `s3_original_domain` to `FB` schema (crawl provenance from book folder) | — | ✅ DONE |
| P1.5-E3 | Populate `s3_original_domain` in stage4 from source book path | P1.5-E2 | ✅ DONE |
| P1.5-E4 | Update stage6 SQLite schema + migration + INSERT for both new columns | P1.5-E3 | ✅ DONE |

### P1.5-F: FB → PT → Skill Orchestration Spec
| # | Task | Depends | Status |
|---|------|---------|--------|
| P1.5-F1 | Research v1 archives for PT/PI/skill/recipe/conductor-loop architecture | — | ✅ DONE |
| P1.5-F2 | Cross-examine against Goose skill system and industry standards | P1.5-F1 | ✅ DONE |
| P1.5-F3 | Write `FOUNDATION-BLOCK-TO-SKILL-SPEC.md` v1.0 for roundtable evaluation | P1.5-F2 | ✅ DONE |
| P1.5-F4 | **UPDATE:** Add FB reliability (render_recipe.py), Zone 3 STABLE GATE (render_zone.py), Project/MOC assessment | P1.5-F3 | ✅ DONE |
| P1.5-F5 | Submit to LLM roundtable (Claude, Kimi, DeepSeek, Grok, Qwen) for cross-examination | P1.5-F4 | ⬜ TODO |

### Key Findings from v1 Archive Research

**FB Reliability System** (`tools/render_recipe.py`, 1070 lines):
- `fb_reliability` table tracks every FB across every PI execution
- Outcomes: FB_VALID, FB_IRRELEVANT, FB_CONTRADICTED, FB_INSUFFICIENT, FB_UNVERIFIED
- reliability_score = valid_count / total_executions
- Thresholds: ≥0.85 STABLE, <0.50 UNSTABLE, <0.20 GARBAGE (propose archive)

**3-Zone Body Template** (`tools/render_zone.py`, 532 lines):
- Zone 1: RELATIONS (metadata)
- Zone 2: BODY (definition, application, failure mode, jargon)
- Zone 3: STABLE GATE — "Stable if: cited" with source, BORP-gated
- Gap identified: Zone 3 doesn't surface reliability_score from DB

**Project Object** (from ultimate architecture spec):
- 7 fields: id, name, goal_statement, status, last_touched, next_action, owner_vs_delegated, est_hours_per_week
- Connects PTs via parent_project property
- Enables Coordinator Recipe (daily cross-project triage)
- Verdict: VIABLE, not bloat

**MOC (Map of Content)**:
- Navigational structure linking FBs/PTs in a domain
- Built via recurring PT ("build MOC for domain X")
- Human navigation layer (agents use vector search)
- Verdict: VIABLE, not bloat — but only if MOC-building is automated

**Industry Gap Confirmed:**
- No existing system does "practical knowledge applicability testing" the way fb_reliability does
- Citation tracking (Semantic Scholar) ≠ execution outcome tracking
- Groundedness detection (Azure) ≠ contextual applicability
- Maxwell's cumulative execution monitoring is novel

### P1.5-D: PT/GE Extraction Evaluation
| # | Task | Depends | Status |
|---|------|---------|--------|
| P1.5-D1 | Evaluate: can stage2 extract "step-by-step procedures" (PT candidates) from books? Run extraction with PT-specific prompt on 3 books, count hits. | — | ⬜ TODO |
| P1.5-D2 | Evaluate: can stage2 extract "experiential/open-tension" principles (GE candidates, including singletons)? GE can also come from singletons. | — | ⬜ TODO |
| P1.5-D3 | If P1.5-D1 or P1.5-D2 yield ≥3 candidates each, write `schemas.py` models for `ProcessTemplate` and `GrowthEdge` (share classification with FB per D385) | P1.5-D1, P1.5-D2 | ⬜ TODO |
| P1.5-D4 | Write `pipeline/render_zone.py` — ZONE body renderer for FB/PT/GE (port from v1 `tools/render_zone.py`, strip Anytype-specific fields, keep ZONE 1/2/3 structure) | P1.5-D3 | ⬜ TODO |
| P1.5-D5 | Wire PT/GE into pipeline: stage5 classifies output type (FB vs PT vs GE), stage6 stores in DB with type discriminator | P1.5-D4 | ⬜ TODO |

**Decision:** EVALUATE FIRST, THEN BUILD FRESH IF VIABLE. PT/GE are the most complex to port. v1's `render_zone.py` is ~600 lines with Anytype-specific code. v1's GE had a contested history (D384: "book singletons → NOT GE", but Maxwell clarified GE CAN be singletons). A clean v2 implementation would be ~200 lines focused on the ZONE body format without Anytype coupling. Risk: medium (new output types add complexity to stage5/6), but additive — doesn't break existing FB pipeline.

---

## 📊 DECISION: BUILD FRESH vs PORT FROM V1

| Component | Strategy | Rationale |
|-----------|----------|-----------|
| Raw label preservation | **BUILD FRESH** | ~50 lines. v1 code is tangled with S3a converge. Cleaner to write new. |
| Synonym matching | **BUILD FRESH** | ~60 lines. v1 never did this. Net-new capability using existing config. |
| Folder routing | **BUILD FRESH** | ~40 lines. Consolidate 8-file scattering into 1 function. |
| PT/GE schemas | **BUILD FRESH** (after eval) | ~100 lines. v1 schemas carry Anytype baggage. Start clean. |
| render_zone.py | **BUILD FRESH** (port ZONE format) | Port the ZONE 1/2/3 structure (proven correct), strip Anytype fields, rebuild lean (~200 lines vs 600). |
| `classify_domains.py` / `classify_disciplines.py` | **DO NOT PORT** | v1's multi-pass classification was built for a different pipeline (S3a→S5→S6). v2 does single-pass SALSA in stage4. |
| `domain_canonical_multi` | **DEFER** | Multi-label for cross-domain FBs. Not needed until we have cross-domain FBs at scale. |
| `s3_original_domain` | **DEFER** | Crawl provenance. Not needed until we run per-domain batches. |
| Decision contracts / auto-enforcement | **BUILD FRESH** (Phase 2) | v1's `decision_contracts.py` + `guard.py` Ring 4 are 800+ lines. For v2: a lightweight `~100 line` contract checker. |

---

## 🔧 AUTO-ENFORCEMENT GAP (2026-07-19 audit)

**Finding:** v2 has NO automatic decision enforcement. The governance docs describe the process (`governance/decision_lifecycle.yaml` with states, traceability, hashes) but:

- No `config/decisions.yaml` — the decision registry doesn't exist
- No `tools/decision_contracts.py` or equivalent — no machine-checkable contracts
- No `tools/guard.py` — no Ring 0-4 enforcement
- No `tools/implementation_guard.py` — no LIVING vs IMPLEMENTED vs PHANTOM checks
- `config/pipeline_config.yaml` exists but is NOT wired to `pipeline/pipeline_paths.py` — the pipeline_paths.py hardcodes most values that should come from pipeline_config.yaml

**Result:** Pipeline config and pipeline code can drift silently. v1 had 22 contracts, 14 gates, and 3-layer protections (D729-D760). v2 has zero. This is intentional for Phase 1 (lean), but the gap should be logged.

**Proposed:** Phase 2 task — build lightweight contract checker (~100 lines) that validates:
1. Pipeline checkpoint files exist for completed stages
2. Schema version consistency across checkpoints
3. All domains/disciplines in DB match taxonomy_v5.yaml
4. BORP min-2-sources enforced at commit time

---

## 🟢 PHASE 3 — BUSINESS OPS (After scale)

| # | Task | Depends On | Status |
|---|------|------------|--------|
| T3.1 | Build FB retrieval MCP server for Goose | Phase 2 | ⬜ BLOCKED |
| T3.2 | Build automation loops (trigger → retrieve → reason → act → verify) | T3.1 | ⬜ BLOCKED |
| T3.3 | Build business operation skills (marketing, sales, content, project mgmt) | T3.2 | ⬜ BLOCKED |

---

## 📜 KEPT FROM v1 (copied, not rewritten)

| File | Purpose |
|------|---------|
| `pipeline/io_guard.py` | Crash-safe writes (C6) |
| `pipeline/doc_guard.py` | Protected file access (R-D824) |
| `pipeline/protect.py` | File protection |
| `pipeline/safe_delete.py` | Safe deletion (R-D410) |
| `pipeline/model_lazyload.py` | Lazy model loading (D1057) |
| `pipeline/ollama_embed.py` | Low-level embedding calls |
| `pipeline/json_repair.py` | JSON repair for LLM output |
| `pipeline/nuke_anytype.py` | Emergency only (R-D413b) |
| `pipeline/backup_guardian.sh` | Backups (C13) |
| `pipeline/validate_book_structure.py` | Book validation |
| `pipeline/pipeline_paths.py` | Path definitions (C12) |

## 📋 CONFIG FILES PRESENT BUT NOT WIRED (2026-07-19 audit)

| File | Lines | Purpose | Wired To |
|------|-------|---------|----------|
| `config/synonym_map.yaml` | 743 | Domain label → synonyms, keywords, patterns | **NOWHERE** — no pipeline stage imports |
| `config/domain_disciplines.yaml` | 960 | Per-domain discipline whitelists | **NOWHERE** |
| `config/domain_anchors.yaml` | ~500 | Domain anchor examples | **NOWHERE** |
| `config/pipeline_config.yaml` | ~200 | Model assignments, paths, credentials | **NOT WIRED** — pipeline_paths.py hardcodes values instead of reading this |
| `governance/domain_labelling.md` | ~400 | D1055-FIX field semantics | **SPEC ONLY** — schemas.py doesn't implement `domain_raw`/`canonical` fields |
| `governance/decision_lifecycle.yaml` | ~100 | Decision states, traceability, enforcement | **PROCESS ONLY** — no `config/decisions.yaml`, no enforcement scripts |

## 📋 V1 ARTIFACTS NOT PORTED (NOT in v2, stays in archive)

| Artifact | Reason Not Ported |
|----------|-------------------|
| `tools/render_zone.py` | Anytype-specific ZONE body renderer. Will rebuild lean for v2. |
| `tools/classify_domains.py` / `classify_disciplines.py` | Multi-pass classification for old pipeline. v2 does single-pass SALSA. |
| `tools/guard.py` + Ring 0-4 contracts | 800+ lines of v1-specific enforcement. v2 is Phase 1 — lean. |
| `tools/decision_contracts.py` | 22 v1-specific contracts. Will rebuild lightweight version in Phase 2. |
| `tools/implementation_guard.py` | LIVING/IMPLEMENTED/PHANTOM tracking. Not needed at 14-FB scale. |
| `tools/s3_converge_local.py` + S3a infrastructure | Old pipeline architecture. v2 is 6-stage (0-6). |
| `knowledge pipeline/` tree | v1 output structure. v2 uses flat `data/` structure. |
| `tools/cost_tracker.py` + DeepSeek fallback | v2 is OMLX-only ($0 marginal cost, C1). |
| All 100+ tools/*.py not listed above | v1 bloat. v2 keeps only what pipeline stages need. |

---

## 📋 STRATEGY — Goose Product Analysis (2026-07-19)

**Question:** Is Maxwell OS desirable, feasible, viable? Is the implementation order SMART?

### Desirability: YES — with qualification
Demand exists for verifiably grounded AI that doesn't hallucinate. The solopreneur market (70M+ globally) buys tools that replace employees. The gap: everyone builds agents, nobody builds **verifiably grounded knowledge for agents to reference.** Maxwell OS fills that gap.

BUT: "100% factual" is a liability. One error and trust collapses. The honest positioning is stronger: **"Every claim is sourced, cross-referenced, and verifiable."**

### Feasibility: YES — pipeline works, remaining layers are engineering
- 6-stage pipeline proven: 14 books → 188 principles → 14 FBs (3 PASS, 10 FLAG, 1 QUARANTINE)
- 852 books available. v1 proved scale: 25,667 principles from 9 domains.
- OMLX on M1 Max, $0 marginal cost.
- Classification architecture (raw + canonical + synonym matching) just landed.
- Missing: multimodal extraction, knowledge layer at scale, skill orchestration, business ops loops.

### Viability: YES — IF vertical slice before universal layer
Building all 4 layers before testing market demand = 17-33 months to first customer. Too long.

**Recommendation: Vertical Slice MVP for ONE domain first.**

| Layer | Universal Scope (current path) | Vertical Slice Scope (proposed) |
|-------|-------------------------------|--------------------------------|
| 0. Extraction | 850+ books, all domains | 20 marketing/strategy books → 100-200 FBs |
| 1. Reference layer | Universal taxonomy, relationships | Marketing-specific relationships |
| 2. Skill orchestration | All business domains | 5-10 marketing skills |
| 3. Business ops | Universal loops | Marketing automation loop |
| 4. Product | Platform for all solopreneurs | "Sovereign Marketing AI" |
| **Time to market** | **17-33 months** | **14-22 weeks** |

### Dependency Chain Validation
The layer order IS logically consequential (extraction → reference → skills → ops → product). You can't skip layers. But SCOPE can be narrowed at each layer without changing the architecture.

### Kill Criteria (gap in original analysis — adopted from Kim cross-exam)
| Gate | Pass | Kill |
|------|------|------|
| Alpha Kit | 3/3 buyers report value | <2/3 by Week 6 |
| Kit Expansion | 5+ kit sales in 60 days | <3 in 90 days |
| Service Layer | 2+ clients, both renewing | 0 renewals in 6 months |
| Product | £1K+ MRR, <20% churn | <£500 MRR at 6 months |

### Language Guardrails
| Never Say | Always Say |
|-----------|------------|
| 100% accurate | Grounded, cited, uncertainty-flagged |
| Hallucination-proof | Never fabricated. Always cited. |
| AI OS | Sovereign Knowledge System |
| Beta | Alpha Cohort / Founding Kit |
| For solopreneurs | For trust-sensitive solo operators |

---

## 📋 REFERENCE — Ultimate Classification Pipeline Spec (2026-07-19)

**Source:** `temp/maxwell_os_ultimate_spec (1).md` — Model2Vec + FastFit cascade + Taxonomy Governance Layer

### Spec Summary

**Classification Cascade (replaces SALSA as primary):**
- Tier 0: Pydantic Literal types (0ms — already in schemas.py)
- Tier 1: Model2Vec + FastFit (~0.5ms per FB, handles ~85%)
- Tier 2: NLI Entailment (~500ms, fallback for creative text)
- Tier 3: SALSA-LoRA (~2.5s, after 500+ cleaned examples)
- Escalation: Conformal prediction + S7 human gate

**Taxonomy Governance (Seed + Candidate + Audit):**
- Hard cap: 25 canonical domains
- Unlimited candidate tracking (raw labels preserved)
- Audit every 100 books or quarterly
- Stability metrics: TStab (Jaccard), TTC (NPMI), TTS (smoothness)
- Proposals: PROMOTE / DEMOTE / MERGE / SPLIT with user approval

**Schema Additions:**
- `pipeline_run_id` — lineage across runs
- `classifier_tier` — which tier classified this FB
- `conformal_prediction_set` — mathematical confidence
- `s3_original_domain` — crawl provenance (add back)
- REMOVE `jargon` — spec claims "LLM returns {} always"

**Structured Output:** Toolio or Outlines (token-level constraint, not JSON mode)

**Performance Targets:** 5,000x faster classification, 30MB classifier (vs 14GB)

---

## 🔍 CROSS-EXAM — Current Pipeline vs. Ultimate Spec

### Alignment (already done or compatible)

| Spec Requirement | Current v2 Status | Verdict |
|-----------------|-------------------|---------|
| Pydantic Literal types (Tier 0) | ✅ Implemented — `DOMAIN_LITERAL`, `DISCIPLINE_LITERAL` enforce at construction | **ALIGNED** |
| Raw label preservation | ✅ P1.5-A implemented — `domains_raw`, `discipline_raw` | **ALIGNED** |
| Synonym matching | ✅ P1.5-B implemented — 643-entry index, wired to stage4 | **ALIGNED** (spec doesn't mention this but it's additive) |
| Candidate tracking | 🟡 Foundation exists — `domains_raw` + `count_raw_labels()` in route.py. DB tables (candidate_labels, taxonomy_audits) not yet built. | **FOUNDATION READY** |
| Taxonomy version stamp | ✅ Already in schemas — `taxonomy_version: v5.0` | **ALIGNED** |
| Hard cap 25 domains | ✅ Current taxonomy has 25 domains + "emerging" | **ALIGNED** |

### Gaps (not yet implemented)

| Spec Requirement | Current v2 Status | Gap | Priority |
|-----------------|-------------------|-----|----------|
| **Model2Vec + FastFit (Tier 1)** | ❌ Uses single-pass SALSA (Qwen3-Coder-30B, 2-8s per FB) | FastFit needs 500+ S7-cleaned FBs to train. We have 14. **BLOCKED until more FBs exist.** | Phase 2 |
| **NLI Entailment (Tier 2)** | ❌ Not implemented | DeBERTa-v3-base-zeroshot-v1. Could add now but low ROI at 14 FB scale. ~100 lines. | Phase 2 |
| **SALSA-LoRA (Tier 3)** | ❌ Not implemented | Same blocker as Tier 1 — needs training data. | Phase 2+ |
| **Conformal prediction** | ❌ Not implemented | Mathematical confidence sets. Needs calibration data. | Phase 2+ |
| **Structured output (Toolio/Outlines)** | 🟡 Uses `response_format: {"type": "json_object"}` — model goodwill, not token-level constraint | Spec says this is "model goodwill" enforcement. True, but it works (93% valid on triad). Toolio/Outlines would be stricter. | Phase 1.5 |
| **`pipeline_run_id`** | ❌ Not in schemas | Additive — one field, stamp at pipeline run start. ~5 lines. | Phase 1.5 |
| **`classifier_tier`** | 🟡 Partially — `classification_method: SALSA` exists but is a string, not a tier enum | Rename/expand to track which tier classified. | Phase 2 |
| **`conformal_prediction_set`** | ❌ Not in schemas | Only useful with conformal prediction. **DEFER until Tier 1-3 exist.** | Phase 2+ |
| **`s3_original_domain`** | ❌ Not in schemas | Crawl provenance. Spec says ADD BACK. Useful when running per-domain batches. ~1 field. | Phase 1.5 |
| **Candidate labels DB table** | ❌ Not built | Schema exists in spec. Additive — doesn't change pipeline flow. | Phase 2 |
| **Taxonomy audit system** | ❌ Not built | Full audit engine (TStab, TTC, TTS, proposals). ~300-500 lines. Needs 100+ FBs to be meaningful. | Phase 2+ |
| **Jargon removal** | 🟡 Spec says REMOVE — I disagree | `_serialize_jargon()` fixed the dict issue. 14 FBs have valid jargon. Removal would be data loss. | **DISAGREE — KEEP** |
| **Inference server identity** | 🟡 Spec says Ollama vs OMLX crisis | Our OMLX on port 11435 works. `call_omlx()` succeeds. The spec may be confused about our actual stack. | **VERIFY, NOT BLOCKING** |

### Verdict on Spec Claims

| Spec Claim | Assessment |
|------------|------------|
| "5,000x faster classification" | True for FastFit vs SALSA inference time. BUT requires 500+ training examples we don't have. **Not actionable now.** |
| "30MB classifier vs 14GB" | True for Model2Vec. Massive memory savings. **Valuable at scale, irrelevant at 14 FBs.** |
| "Jargon field always broken — remove" | **Wrong for v2.** We fixed the dict→string bug via `_serialize_jargon()`. 14 FBs have valid jargon. Spec was written against v1's broken state. |
| "Structured output is model goodwill, not enforcement" | **Technically correct.** Our JSON mode is soft enforcement. But at 93% validity on triad, the ROI of Toolio/Outlines is low right now. |
| "OMLX vs Ollama identity crisis" | **May be spec confusion.** Our OMLX server works on port 11435. `call_omlx()` succeeds. Verify, don't assume crisis. |

### What to Do Now vs. Defer

| Action Now (Phase 1) | Defer to Phase 2+ |
|----------------------|-------------------|
| ✅ Pydantic Literal types (already done) | ⏳ Model2Vec + FastFit (needs training data) |
| ✅ Raw label preservation (P1.5-A done) | ⏳ NLI fallback (low ROI at 14 FBs) |
| ✅ Synonym matching (P1.5-B done) | ⏳ SALSA-LoRA (needs 500+ FBs) |
| ✅ Folder routing (P1.5-C done) | ⏳ Conformal prediction (needs calibration) |
| 🔜 Add `pipeline_run_id` to schemas (~5 lines) | ⏳ Candidate labels DB tables |
| 🔜 Add `s3_original_domain` to schemas (~3 lines) | ⏳ Full taxonomy audit engine |
| 🔜 Run Alpha Kit: 3 pricing books → FBs → PT → test | ⏳ Structured output (Toolio/Outlines) |

### Bottom Line

The Ultimate Spec is a **Phase 2-3 target architecture**, not a Phase 1 blocker. It assumes 500+ S7-cleaned FBs and hundreds of processed books. At 14 FBs, the current SALSA pipeline is appropriate. The spec correctly identifies the long-term direction (FastFit cascade, taxonomy governance, conformal prediction) and the foundation we're building (raw preservation, synonym matching, Pydantic enforcement) is exactly what the spec requires as prerequisites.

---

## 🔬 CROSS-EXAMINATION #2: MODEL/STACK ANALYSIS ("UNTITLED 4") vs. KIMI vs. GOOSE (2026-07-19)

### Source
- `temp/Untitled 4.txt` — model-selection-focused rebuttal. Self-corrects from earlier draft that called Qwen3-Coder-30B "weak." Validates current stack as optimal. Proposes 3-week Phase 0.

### Core Thesis
> Qwen3-Coder-30B-A3B is the optimal generator. No model switch to Gemma-4 or Mistral Small 3.1 is justified. The stack is correct. Spike Outlines, build bridge, stop procrastinating.

### Convergence With Previous Roundtable

| Area | Kimi | Untitled 4 | Goose |
|------|------|-----------|-------|
| Layer 2 is critical path | ✅ | ✅ | ✅ |
| Bridge must be built | ✅ | ✅ | ✅ |
| Outlines needs evaluation | Adopt now | Spike first | **Spike first** — aligned with Untitled 4 |
| Qwen3-Coder stays | Yes | **Emphatic yes** | ✅ |
| Phi-4-mini stays as verifier | Yes | **Yes** | ✅ |
| No model switch | Partial (considered Gemma-4) | **Absolute** | **Agree with Untitled 4** |

### Where Untitled 4 Is Stronger Than Kimi

| Finding | Why It Matters |
|---------|---------------|
| Qwen3-Coder-30B is **coding-optimized** — structured JSON extraction IS a coding task | Kimi never made this connection. JSON generation benefits from "Coder" variant. |
| Gemma-4 MLX support is **"QAT only"** — not native weights | Real risk of broken inference. Kimi never flagged this. |
| Mistral Small 3.1 is **2-3× slower** than Qwen3-Coder | At 852 books, this is hundreds of hours difference. |
| Self-correction: "I was wrong about Qwen3-Coder-30B being weak" | Methodology humility. Credibility signal. |

### Where Untitled 4 Is Weaker

| Gap | Why It Matters |
|-----|---------------|
| No business model | Kimi wins here. |
| No taxonomy governance | Our P1.5 work (raw labels, synonym matching, folder routing, provenance) unaddressed. |
| No fb_relationships table | Flat FB schema bottleneck not acknowledged. |
| No Project/MOC objects | Container objects for skill orchestration missing. |
| No dynamic Zone 3 rendering | Zone 3 shows BORP only, not reliability_score. |
| 3-week Phase 0 timeline | Too compressed. Realistic: 8 weeks (Alpha Kit + Bridge + Integration). |
| Bridge before FB corpus | Same error as Kimi. Alpha Kit must come first. |
| Phi-4-mini TruthfulQA 0.990 | Likely MC2, not MC1. Number inflated. Model still sufficient though. |

### Merged Verdict: The Three-Analyst Consensus

| Question | Kimi | Untitled 4 | **Goose (Ultimate)** |
|----------|------|-----------|---------------------|
| Change models? | Consider Gemma-4 | **NO** | **NO CHANGE** |
| Docling primary? | Yes | Keep Pandoc | **Format-routed: Pandoc EPUB, Docling PDF** |
| Adopt Outlines? | Immediately | Spike first | **Spike first** |
| Critical path? | render_recipe.py v2 | render_recipe.py v2 | **Alpha Kit → render_recipe.py v2** |
| Business model? | Lifetime license + upgrades | Not addressed | **Kimi's model, Goose's tiers** |
| Timeline? | 4 weeks | 3 weeks | **8 weeks (realistic)** |

### Action Items From This Round

| # | Action | Source | Priority |
|---|--------|--------|----------|
| 1 | **No model changes.** Qwen3-Coder-30B + Phi-4-mini stays. | Untitled 4 | **DECIDED** |
| 2 | Spike: Outlines/XGrammar + OMLX compatibility | Both | HIGH |
| 3 | Alpha Kit: 3 pricing books → pipeline → 30-50 FBs | Goose | **NEXT** |
| 4 | Add `fb_relationships` table after Alpha Kit | Goose + Kimi | HIGH |
| 5 | Build `render_recipe.py` v2 after Alpha Kit validates | All three | **CRITICAL** |
| 6 | Dynamic Zone 3 rendering from reliability scores | Goose | MEDIUM |
| 7 | Lifetime license pricing: Beta Kit £750-1,000 | Kimi + Goose | MEDIUM |

### The Final Word

> Three independent analyses. One conclusion: the models are right, the pipeline is right, the bridge is missing. Stop evaluating. Start building. Alpha Kit first. Bridge second. Everything else is commentary.

---

## 🔬 CROSS-EXAMINATION: KIMI ANALYSIS vs. CURRENT ARCHITECTURE vs. GOOSE PROPOSITIONS (2026-07-19)

### Sources
- Kimi: `temp/kimii.txt` (27KB — industry benchmarking, stack optimization, business plan, roadmap)
- Goose: `KNOWLEDGE-PIPELINE-ARCHITECTURE.md` (674 lines), `FOUNDATION-BLOCK-TO-SKILL-SPEC.md v1.1`
- Pipeline: 7,299 lines, 6 stages, 14 FBs, property logic hardened
- `MISSION.md` (rewritten v2.0 post-cross-examination)

### Convergence

| Area | Kimi | Goose | Verdict |
|------|------|-------|---------|
| Layer 2 is critical path | "Missing half of organism" | "THE product. Build the bridge." | **ALIGNED** |
| fb_relationships table | SQLite-based, lightweight | Acknowledged gap (§13) | **ALIGNED** — adopt Kimi's schema |
| Lifetime license + upgrades | £500-1,500 kits | Same model | **ALIGNED** — Kimi's tiering more specific |
| Dogfooding as validation | Phase 2: live in system | Product analysis | **ALIGNED** |
| MCP server wrapper | Phase 2 | Future-proofing | **ALIGNED** |
| SALSA correct for <500 FBs | "Right choice" | Architecture §13 | **ALIGNED** |
| BORP verification is novel | "No competitor" | Same | **ALIGNED** |

### Divergence (Goose Pushes Back)

| Area | Kimi | Goose | Rationale |
|------|------|-------|-----------|
| **Docling primary** | Replace Pandoc | Format-routed: Pandoc EPUB, Docling PDF | 852 books majority EPUB. Pandoc handles natively. |
| **1 FB/book is bug** | Debug Stage 2 yield | Domain-diversity artifact | Triad used DIFFERENT domains. Same-domain books converge. |
| **Bridge before FBs** | Phase 0: render_recipe.py v2 in 4 wks | Alpha Kit FIRST, THEN bridge | 3 PASS FBs can't test recipe rendering. |
| **4-week Phase 0** | Weeks 1-4 | 8 weeks | Alpha Kit (2wk) + bridge (4wk) + integration (2wk) |
| **Outlines now** | Adopt immediately | Spike first | OMLX compatibility unproven. Kimi's own kill criteria agree. |

### What Kimi Missed (Goose Already Built/Spec'd)

- **Raw label preservation** (P1.5-A): `domains_raw`, `discipline_raw` for taxonomy evolution
- **Synonym matching** (P1.5-B): 643-entry index, bridges LLM → canonical
- **Folder routing** (P1.5-C): canonical → raw → emerging priority chain
- **Provenance fields** (P1.5-E): `pipeline_run_id`, `s3_original_domain`
- **FB reliability as novel differentiator**: No competitor tracks "does this principle work in practice?"
- **3-Zone Body Template**: Zone 1 (metadata), Zone 2 (immutable), Zone 3 (STABLE GATE + dynamic reliability)
- **Project/MOC viability**: Assessed. Both viable, not bloat.
- **Additional kill criteria**: Pipeline yield, friend retention, willingness-to-pay, false positive rate

### Adopted from Kimi

| # | Adoption | Priority | Action |
|---|---------|----------|--------|
| K1 | `fb_relationships` table | **HIGH** | ~50 lines. `schemas.py` + `stage6_commit.py` |
| K2 | "7,299 pipeline, 0 orchestration. Build the bridge." | **HIGH** | Adopted in MISSION.md framing |
| K3 | Pricing tiers refined | **MEDIUM** | Beta Kit £750-1,000, Expansion £300-500, Custom £5K-15K |
| K4 | Binary gate: "2/3 friends pay £500+?" | **HIGH** | Go/no-go metric |
| K5 | Phase structure | **MEDIUM** | Modified sequencing: Alpha Kit BEFORE bridge |
| K6 | Outlines/XGrammar spike | **MEDIUM** | Test OMLX compat. If yes, adopt. If no, JSON mode OK for <500 FBs. |

### Rejected/Modified from Kimi

| # | Rejection | Why |
|---|----------|-----|
| R1 | Docling primary | Pandoc correct for EPUB corpus. Format-routed, not blanket-primary. |
| R2 | Bridge before FB corpus | Alpha Kit first. Need FBs to test bridge. |
| R3 | 4-week Phase 0 | 8 weeks realistic. |
| R4 | Stage 2 yield bug | Domain-diversity artifact. Same-domain = convergence. |
| R5 | Custom Build £2K-5K | Too low. Bespoke knowledge extraction = consulting. £5K-15K. |

### Ultimate Verdict

| Question | Answer |
|----------|--------|
| Kimi's analysis valid? | **85% valid.** Strong on industry, business, competitive. Weak on corpus-specific engineering. |
| Business plan viable? | **Yes, with sequencing corrections.** Lifetime license + upgrades. Kill criteria protect downside. |
| Architecture aligned? | **Layer 0-1: yes. Layer 2: spec'd, unbuilt — and that's everything.** |
| Mission changes? | **MISSION.md rewritten (v2.0)** — WHY + moat + kill criteria + business model + bridge thesis. |

---

## 🎯 UNIFIED PRIORITIZED TASK LIST (2026-07-19)

**Aggregated from:** Phase 1, Phase 1.5, Phase 2, Phase 3, Kimi Cross-Examination, Untitled 4 Cross-Examination  
**Principle:** "Alpha Kit first. Bridge second. Everything else is commentary."

---

### ⬛ CRITICAL — Blocking All Progress (Do These First, In Order)

| # | Task | Depends On | Est. | Status |
|---|------|-----------|------|--------|
| **C1** | **Alpha Kit:** Run pipeline on 3 pricing books (E-Myth, Profit First, $100 Startup) → 30-50 convergent FBs | — | 1-2 wks | ⬜ TODO |
| **C2** | Maxwell reviews Alpha Kit FBs (S7 human gate) — validates pipeline quality for domain-convergent extraction | C1 | 3-5 days | ⬜ TODO |
| **C3** | Build `render_recipe.py` v2: port from v1 (1,070 lines), decouple Anytype, PT + FB corpus → Goose Recipe YAML | C1 (needs FBs to test) | 2-3 wks | ⬜ TODO |
| **C4** | Build `verify_step.py`: cross-family verification (R5) for recipe output — checks each step's FB citations | C3 | 3-5 days | ⬜ TODO |
| **C5** | Port `fb_reliability.py` from v1: standalone module + PI execution logging + reliability_score lifecycle (STABLE/WATCH/UNSTABLE/GARBAGE) | C3 | 2-3 days | ⬜ TODO |
| **C6** | Integration test: end-to-end — book → FB → PT → Recipe → Execution → Reliability update | C3 + C4 + C5 | 1-2 wks | ⬜ TODO |

---

### 🟥 HIGH — Needed Soon, Can Parallelize

| # | Task | Depends On | Est. | Status |
|---|------|-----------|------|--------|
| **H1** | **T1.17: Maxwell reviews existing triad FBs** (14 FBs, 3 PASS, 10 FLAG, 1 QUARANTINE) — S7 human gate | — | 2-4 hrs | ⬜ TODO |
| **H2** | Spike: Outlines/XGrammar + OMLX compatibility test for schema-constrained generation | — | 1 day | ⬜ TODO |
| **H3** | Add `fb_relationships` table to schemas.py + stage6_commit.py (supports/contradicts/extends/applies_to) | C1 (needs FBs to relate) | 2-3 days | ⬜ TODO |
| **H4** | Build `retrieve.py` v2: add convergence-weighting + reliability-ranked retrieval | C1 + C5 | 3-5 days | ⬜ TODO |
| **H5** | Submit `FOUNDATION-BLOCK-TO-SKILL-SPEC.md` v1.1 + `KNOWLEDGE-PIPELINE-ARCHITECTURE.md` to LLM roundtable (Claude, Kimi, DeepSeek, Grok, Qwen) | — | — | ⬜ TODO |
| **H6** | Evaluate PT/GE extraction: run stage2 with PT-specific prompt on 3 books, count hits (P1.5-D1) | — | 2-3 days | ⬜ TODO |

---

### 🟨 MEDIUM — After Critical + High

| # | Task | Depends On | Est. | Status |
|---|------|-----------|------|--------|
| **M1** | Dynamic Zone 3 rendering: pull `reliability_score` + `total_executions` from DB, append to STABLE GATE | C5 | 1-2 days | ⬜ TODO |
| **M2** | Wire `config/pipeline_config.yaml` to `pipeline/pipeline_paths.py` — eliminate hardcoded values | — | 1-2 days | ⬜ TODO |
| **M3** | Wire `config/domain_disciplines.yaml` (960 lines) into classification validation | — | 1-2 days | ⬜ TODO |
| **M4** | Build lightweight contract checker (~100 lines): validate checkpoints, schema consistency, taxonomy alignment, BORP enforcement | — | 2-3 days | ⬜ TODO |
| **M5** | Evaluate PT/GE schemas: if H6 yields ≥3 PT candidates, write `ProcessTemplate` + `GrowthEdge` Pydantic models (P1.5-D3) | H6 | 2-3 days | ⬜ TODO |
| **M6** | Build `pipeline/render_zone.py` — ZONE body renderer for FB/PT/GE (port ZONE 1/2/3 from v1, strip Anytype, ~200 lines) (P1.5-D4) | M5 | 2-3 days | ⬜ TODO |
| **M7** | Wire PT/GE into pipeline: stage5 classifies output type (FB vs PT vs GE), stage6 stores with type discriminator (P1.5-D5) | M6 | 3-5 days | ⬜ TODO |

---

### 🟩 LOW / DEFERRED — Phase 2+

| # | Task | Why Deferred | When |
|---|------|-------------|------|
| **L1** | Run pipeline on all 850+ books (T2.1) | Needs Alpha Kit validation + bridge working | Phase 2 |
| **L2** | Train Model2Vec + FastFit classifier on 500+ S7-cleaned FBs (T2.2) | Needs 500+ FBs | Phase 2 |
| **L3** | NLI Entailment fallback (DeBERTa-v3-base-zeroshot-v1) | Low ROI at 14 FB scale | Phase 2 |
| **L4** | SALSA-LoRA fine-tuning | Needs 500+ training examples | Phase 2+ |
| **L5** | Conformal prediction (MAPIE) | Needs calibration data | Phase 2+ |
| **L6** | Full taxonomy audit engine (TStab, TTC, TTS, proposals) | Needs 100+ FBs | Phase 2+ |
| **L7** | Candidate labels DB tables | Additive, not blocking | Phase 2 |
| **L8** | Push verified FBs to Anytype (T2.4) | Depends on scale | Phase 2 |
| **L9** | Build FB retrieval MCP server for Goose (T3.1) | Needs working skills first | Phase 3 |
| **L10** | Build automation loops (T3.2) | Needs MCP server | Phase 3 |
| **L11** | Build business operation skills (T3.3) | Needs automation loops | Phase 3 |
| **L12** | MCP server wrapper for skills | Needs working skills | Phase 2 |
| **L13** | A2A protocol support | Multi-agent coordination | Phase 3 |
| **L14** | Multimodal extraction (Docling v2 vision) | Text-only sufficient for Phase 0-2 | Phase 2 |
| **L15** | Project/MOC objects (projects table, MOC-building PT, Coordinator Recipe) | After 50+ FBs | Phase 2 |
| **L16** | Trust ledger integration (auto/queue/watch tiers) | Needs reliability scores + multiple PI executions | Phase 2 |
| **L17** | Build `config/decisions.yaml` + decision enforcement scripts | Lean Phase 1 approach | Phase 2 |

---

### ✅ COMPLETED

| # | Task |
|---|------|
| — | 6-stage pipeline: convert, chunk, extract, cluster, merge+classify, verify, commit (T1.1-T1.7) |
| — | schemas.py (Pydantic v2, Literal types, synonym index) + stamp.py + omlx_call.py (T1.8-T1.10) |
| — | retrieve.py (277 lines) + query.py (285 lines) + status.py (201 lines) (T1.11-T1.13) |
| — | SALSA on OMLX: 93% classification validity (T1.14) |
| — | Triad end-to-end: 14 books → 188 principles → 14 FBs, 3 PASS (T1.15-T1.16) |
| — | Raw label preservation: `domains_raw`, `discipline_raw` in schemas + stage4 + stage6 (P1.5-A) |
| — | Synonym matching: 643-entry lookup from taxonomy + synonym_map.yaml (P1.5-B) |
| — | Folder routing: `route.py` 140 lines, canonical→raw→emerging priority chain (P1.5-C) |
| — | Provenance fields: `pipeline_run_id` + `s3_original_domain` in schemas + stamp + stage4 + stage6 (P1.5-E) |
| — | `FOUNDATION-BLOCK-TO-SKILL-SPEC.md` v1.1 written: FB reliability, 3-Zone template, Project/MOC (P1.5-F1-F4) |
| — | `KNOWLEDGE-PIPELINE-ARCHITECTURE.md` (674 lines) — comprehensive reference for roundtable evaluation |
| — | `MISSION.md` v2.0 rewritten — WHY + moat + kill criteria + business model + bridge thesis |
| — | Cross-examination #1: Kimi analysis logged + adopted (fb_relationships, pricing, binary gate) |
| — | Cross-examination #2: Untitled 4 analysis logged + adopted (no model changes, coding-optimization argument) |
| — | Governance: `domain_labelling.md` — v2 applicability banner added |
| — | Governance: `decision_lifecycle.yaml` — v2 status note added |
| — | **💰 PRICING PIPELINE RUN (2026-07-19): 130 books → 136 segments → 58 principles → 3 clusters → 3 FBs, all PASS** |
| — | `pipeline/pipeline_paths.py` — added `MAXWELL_BOOKS_DIR` env var override for targeted runs |

---

## 💰 PRICING PIPELINE RUN — RESULTS (2026-07-19)

**Goal:** Extract convergent principles from ALL pricing/pricing-strategy/business-finance books to bootstrap business financial planning.

### Run Stats

| Metric | Value |
|--------|-------|
| Books selected | 130 (from DOMAIN 4 Business + strategy/brand + marketing/growth + practice/economics) |
| Segments (Stage 1) | 136 |
| Principles (Stage 2) | 58 |
| Clusters (Stage 3) | 3 |
| FBs (Stage 4) | 3 |
| PASS (Stage 5) | **3/3 (100%)** |
| FLAG / QUARANTINE | 0 |
| Classification errors | 0 |

### Extracted FBs

| FB | Domains | Discipline | Depth | Sources | BORP |
|----|---------|-----------|-------|---------|------|
| **Strategic Brand-Driven Innovation** | brand identity, digital product, user experience, business operations | design strategy | cross-domain | 8 books | 1.0 |
| **Transformative Business Architecture** | business operations, systems & frameworks, engineering practice, organizational behavior | strategic thinking | cross-domain | 6 books | 1.0 |
| **Empathetic Sales Framework** | business operations, user experience, organizational behavior | marketing | cross-domain | 2 books | 1.0 |

### Yield Analysis

| Factor | Assessment |
|--------|-----------|
| **FB yield (3/130 books)** | **Low.** Comparable to triad (14 books → 14 FBs = 1.0 FB/book vs 130 books → 3 FBs = 0.02 FB/book). Root cause identified. |
| **Root cause: Chunker `\n\n` bug** | `split_on_headings()` consumes paragraph boundaries — joins lines with `\n`, then `chunk_text()` splits on `\n\n` which no longer exist. Sections with no `##` headings become giant single-chunks, limiting principle extraction granularity. |
| **Fix required** | Preserve `\n\n` in `split_on_headings()` or change `chunk_text()` fallback to work on large single-paragraph sections. Logged as **P1.5-G1**. |
| **Expected yield after fix** | 130 books with proper chunking → ~3,000-5,000 segments → ~500-1,000 principles → ~20-50 FBs. |
| **Quality despite low yield** | All 3 FBs cross-domain, BORP 1.0, 0 classification errors. What WAS extracted is solid. |

### Key Pricing Books Processed

| Book | Relevance |
|------|-----------|
| Profit First (Mike Michalowicz) | Core — cash management, profit allocation |
| How to Price Your Platypus | Core — pricing strategy and tactics |
| Pricing Creativity (Blair Enns) | Core — value-based pricing for creatives |
| Pricing Design (Dan Mall) | Core — pricing for design services |
| The Pricing Roadmap (Ulrik Lehrskov-Schmidt) | Core — B2B SaaS pricing models |
| Pricing with Confidence (Reed K. Holden) | Core — 10 rules for profitable pricing |
| Monetizing Innovation | Core — product-price design |
| Value-Based Fees (Alan Weiss) | Core — charging what you're worth |
| Graphic Artists Guild Handbook: Pricing & Ethical Guidelines | Core — industry pricing standards |
| $100M Offers (Alex Hormozi) | Core — offer construction and pricing |
| Zero to Sold (Arvid Kahl) | Core — bootstrapped business pricing |
| Blue Ocean Strategy (2 editions) | Strategy — market positioning, value innovation |
| Good Strategy Bad Strategy (Rumelt) | Strategy — strategic thinking framework |
| Playing to Win (Lafley/Martin) | Strategy — where-to-play/how-to-win |
| Business Model Generation / You / Navigator | Business model — value proposition design |
| Built to Sell / Company of One | Business structure — scalable vs intentional small |
| Oversubscribed / Purple Cow | Marketing — demand generation, differentiation |
| The Positioning Manual for Indie Consultants | Positioning — niche strategy for solopreneurs |

### ⚠️ Known Issue: Stage1 Chunker `\n\n` Bug (P1.5-G)

| # | Task | Status |
|---|------|--------|
| P1.5-G1 | Fix `split_on_headings()` to preserve `\n\n` paragraph boundaries OR add `chunk_text()` fallback for large single-paragraph sections | ⬜ TODO |
| P1.5-G2 | Re-run pricing pipeline after fix → expect ~20-50 FBs | ⬜ BLOCKED by P1.5-G1 |

---

## 📊 GOLDEN FB CALIBRATION — PRIORITY ASSESSMENT (2026-07-19)

**Question:** How high is golden FB calibration (T1.17 — Maxwell reviews triad FBs) in priority?

### Assessment

| Factor | Analysis |
|--------|----------|
| **What is it?** | T1.17: Maxwell manually reviews the 14 triad FBs (3 PASS, 10 FLAG, 1 QUARANTINE) to calibrate pipeline quality — the S7 human gate. |
| **What does it unlock?** | Confidence that the pipeline produces human-validated FBs. Without it, we don't know if "PASS" FBs are actually good. |
| **What does it NOT unlock?** | New capability. Pipeline already runs. Classification already functions (93% valid). BORP verification already works. |
| **Blocking anything?** | **No.** Alpha Kit (C1) doesn't need Maxwell's review — it's automated. render_recipe.py v2 (C3) needs FBs to test with — but can use Alpha Kit FBs, not triad FBs. |
| **Can it parallelize?** | **Yes.** Run Alpha Kit (C1) while Maxwell reviews triad FBs (H1). Alpha Kit takes 1-2 weeks of compute. Maxwell's review is 2-4 hours of focused work. |

### Verdict: HIGH but NOT CRITICAL

**Position in priority: H1** — first HIGH task, below only the Critical path (C1-C6).

**Reasoning:**
- It doesn't block Alpha Kit (C1) — Alpha Kit runs on its own.
- It doesn't block bridge (C3) — bridge can use Alpha Kit FBs, not triad FBs.
- It DOES validate that the pipeline produces quality output before we invest 2-3 weeks building the bridge.
- It's 2-4 hours of Maxwell's time vs. potentially weeks of building on bad FBs.

**Recommended sequencing:**
```
Week 1-2:  [Alpha Kit runs] ← automated, no Maxwell time
           [Maxwell reviews 14 triad FBs] ← 2-4 hrs, can do anytime in this window

Week 2:    Alpha Kit done → 30-50 pricing FBs
           Maxwell reviews Alpha Kit FBs ← 3-6 hrs

Week 3:    Combined calibration: 44-64 FBs reviewed
           → Confidence to build bridge (C3) on validated FBs
```

### Risk of Skipping vs. Risk of Waiting

| Scenario | Risk |
|----------|------|
| **Skip T1.17 entirely** | Build bridge on potentially garbage FBs. Discover quality issue after 3 weeks of bridge work. |
| **Wait for T1.17 before Alpha Kit** | Lose 1-2 weeks. Alpha Kit could have been running. |
| **Do T1.17 in parallel with Alpha Kit** | **Zero risk.** Alpha Kit runs without Maxwell. Review happens during compute time. Pipeline quality validated before bridge construction begins. |

### Bottom Line

**Priority: H1.** Do it in parallel with Alpha Kit. The 14 existing triad FBs are from diverse domains — useful for calibration. But the Alpha Kit's domain-convergent FBs (30-50 pricing FBs) are what the bridge actually needs. Don't let review block automation.

