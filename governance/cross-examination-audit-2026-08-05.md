# Governance Cross-Examination Audit — 2026-08-05
> **Auditor:** Goose (S-tier RAG + Agentic Engineer)
> **Source:** 7 external LLM evaluations × actual pipeline code × all governance docs
> **Scope:** Contradictions, drift, superseded items, missing decisions, task priority

---

## 1. CONTRADICTIONS & DRIFT FOUND

### 🔴 DRIFT-1: D2118 Numbering Collision
**Two different decisions share D2118:**
- **D2118 (2026-07-26):** "Full feed.opml Research + 6 New Tool Discoveries" — line 1814
- **D2118 (2026-07-27):** "Matryoshka 512-dim Embeddings" — line 1998
- **Fix:** Renumber the second to D2138a or re-sequence from D2118 onward. D2119-D2126 also affected.

### 🔴 DRIFT-2: requirements.txt Claims v2.0
- `requirements.txt` line 1: `# Maxwell OS v2.0`
- `CONSTITUTION.md`: v3.0
- `AGENTS.md`: v3.0
- `DECISION-LOG.md`: references v3.0 throughout
- **Fix:** Update requirements.txt header to v3.0.

### 🔴 DRIFT-3: Config Embedding Model Mismatch
- `config/pipeline_config.yaml`: `embed_model: bge-m3` AND `embed_model_hf: BAAI/bge-small-en-v1.5`
- `stage1_5_embed_cluster.py` line 134: loads `S15_EMBED_MODEL_HF` (bge-small-en-v1.5, 384d)
- `stage1_5_embed_cluster.py` line 376: stamps `S15_EMBED_MODEL` (bge-m3) on output records
- **Every cluster record claims bge-m3 while vectors are actually 384d bge-small**
- **Fix:** Either unify both config values to the actually-used model, or add a mismatch detection gate.

### 🟠 DRIFT-4: Buglog Excludes 5 Code-Verified Critical Bugs
Cross-examination found 5 critical bugs NOT in `governance/buglog.md`:

| Bug | Location | Symptom |
|-----|----------|---------|
| **NLI-001** | stage5_verify.py:136 | `nli(f"{source} </s></s> {claim}")` — single string, not pair dict. Verification random. |
| **MH-001** | stage2_extract.py:765 | `_jaccard` key never populated, lambda returns 0, dedup disabled |
| **START-001** | stage2_extract.py:781-786 | `start`, `result`, `is_summary`, `name` undefined at that scope → NameError |
| **CKPT-001** | stage2_extract.py:787 | `i` from enumerate scope, checkpoint writes once at end, not every 5 |
| **THRESH-001** | stage5_verify.py | Config says 0.6, runtime uses 0.8/0.5. Three thresholds, different semantics |

### 🟠 DRIFT-5: MASTER-TASK-REGISTER Outdated
- Still claims "Phase 0 — CRITICAL ✅ COMPLETE" from 2026-07-26
- Does not reflect S1.5 full-corpus completion (2026-08-04, 1,110 clusters)
- Does not include D2148-D2150 (tiered extraction, coverage gap, content type mapping)
- Does not include the 5 critical bugs from cross-examination
- V3, V4, V6 still marked ⬜ TODO (from 2026-08-03)
- Says "8 open" bugs; actual count is higher

### 🟡 DRIFT-6: D2032 (M3 Conflict) Status Stale
- D2032 says "UNRESOLVED — Requires G7 human gate"
- D2066 RESOLVED the conflict in favor of multi-label (Option B: D316)
- D2032 should be marked "RESOLVED by D2066" or have status updated

### 🟡 DRIFT-7: Buglog Status Summary Line Stale
- `governance/buglog.md` footer says: "Bugs tracked: 37 | Resolved: 37 | Open: 2 (BUG-017, BUG-037)"
- This was from 2026-07-23. Now: BUG-056, BUG-057, BUG-058, BUG-059 are open, plus the 5 new critical bugs

---

## 2. SUPERSEDED DECISIONS

| Decision | Superseded By | Rationale |
|----------|---------------|-----------|
| D2024 (SALSA dichotomous) | D2066 | Multi-label classification with dynamic taxonomy |
| D2012 (4-layer cleaning) | D2071 | D2071 explicitly supersedes with H1-H4 implementation |
| D2004 (14 foundation fixes) | Multiple (D2119, D2120, D2127, D2131-D2137) | Individual fixes have been implemented and superseded |
| D2021 (cross-domain 3-domain) | S1.5 full-corpus clustering | Single-pass global FAISS replaced per-domain clustering |
| D2124 (domain-by-domain extraction) | S1.5 global clustering (2026-08-04) | Global clustering gives cross-book convergence without per-domain batching |

---

## 3. NEW DECISIONS — FROM CROSS-EXAMINATION (2026-08-05)

### D2151 — NLI Input Format Fix (S5 Verification Broken)
**Category:** BUGFIX | **State:** ACTIVE | **Priority:** 🔴 CRITICAL

**Finding:** `stage5_verify.py` line 136 calls `nli(f"{source} </s></s> {claim}")` — a single concatenated string. The transformers `text-classification` pipeline tokenizes this as ONE sequence with all token_type_ids=0. NLI models are trained on premise/hypothesis PAIRS with different token_type_ids. The `</s></s>` separator is not auto-parsed. The model cannot distinguish premise from hypothesis.

**Verified:** Code inspection confirmed. Same bug affects both ModernBERT and DeBERTa-v3 paths.

**Fix:** Change to `nli({"text": source, "text_pair": claim})`. Also normalize label casing with `.upper()`.

**Impact:** Stage 5 verification is producing random results. Every FB verified so far was verified by a broken mechanism.

**Files:** `pipeline/stage5_verify.py` line 136.

---

### D2152 — MinHash Dedup Fix (Near-Duplicate Detection Disabled)
**Category:** BUGFIX | **State:** ACTIVE | **Priority:** 🔴 CRITICAL

**Finding:** `stage2_extract.py` line 765: `minhash_cache.get("_jaccard", lambda a, b: 0)(sig, prev_sig) > 0.9`. The `_jaccard` key is NEVER populated in `minhash_cache`. `minhash_cache` only stores `sig → text` mappings (line 406: `minhash_cache[sig] = text`). The fallback lambda returns 0, and `0 > 0.9` is never true.

**Impact:** Near-duplicate detection is completely disabled. Identical principles from different clusters will be committed as separate FBs, bloating the corpus.

**Fix:** Use actual `datasketch.MinHash` objects with `.jaccard()` comparison method. Create MinHash objects from signature texts, compute Jaccard via the datasketch API.

**Files:** `pipeline/stage2_extract.py` lines 396-408, 758-765.

---

### D2153 — Fix Dead Code in run_stage2() (NameError Crash)
**Category:** BUGFIX | **State:** ACTIVE | **Priority:** 🔴 CRITICAL

**Finding:** Lines 781-786 of `stage2_extract.py` are dedented to the `run_stage2()` function scope (OUTSIDE the `for future` loop) but reference variables only defined inside `_process_cluster()`: `start`, `result`, `is_summary`, `name`. These are undefined at the `run_stage2()` scope. This code would crash with `NameError` if executed.

**Evidence:** These 5 lines appear to be copy-paste residue from the `_process_cluster()` function. Combined with the checkpoint index bug (D2154), incremental saves are non-functional.

**Fix:** Remove lines 781-786 entirely (they duplicate logging already done inside the loop at lines 770-778).

**Files:** `pipeline/stage2_extract.py` lines 781-786.

---

### D2154 — Fix Incremental Checkpoint Index (Out of Scope)
**Category:** BUGFIX | **State:** ACTIVE | **Priority:** 🔴 CRITICAL

**Finding:** Line 787: `if i % 5 == 0 or i == len(target_clusters)`. `i` comes from `for i, c in enumerate(target_clusters)` on line 721. Line 787 is OUTSIDE the `for future` loop (dedented). The checkpoint writes only once after all clusters complete, using the last `i` value. The intended "every 5 clusters" incremental save never triggers.

**Fix:** Move the checkpoint write logic INSIDE the `for future` loop, using `completed` counter (already tracked). Write checkpoint when `completed % 5 == 0`.

**Files:** `pipeline/stage2_extract.py` lines 787-800.

---

### D2155 — Unify NLI Threshold Configuration (C12 Violation)
**Category:** BUGFIX | **State:** ACTIVE | **Priority:** 🔴 CRITICAL

**Finding:** Config says `nli_entailment_threshold: 0.6`. Runtime uses three different thresholds:
- `>= 0.8` → PASS (skip LLM escalation)
- `>= 0.5` → FLAG (marginal, escalate to LLM)
- `< 0.5` → FAIL (escalate)

Three thresholds with different semantics, none matching the config. Violates C12 (config-first) and C20 (no magic numbers).

**Fix:** Add all three thresholds to config: `nli_pass_threshold: 0.8`, `nli_marginal_threshold: 0.5`, `nli_entailment_threshold: 0.6`. Runtime reads from config, not hardcoded.

**Files:** `pipeline/stage5_verify.py` lines 430-460, `config/pipeline_config.yaml`.

---

### D2156 — Fix Config Embedding Model Drift (Reproducibility Invalidated)
**Category:** CFG | **State:** ACTIVE | **Priority:** 🟠 HIGH

**Finding:** `config/pipeline_config.yaml` contains two conflicting embedding model specs:
```yaml
embed_model: bge-m3                    # ← Stamped on output records
embed_model_hf: BAAI/bge-small-en-v1.5  # ← Actually loaded by S1.5
```
S1.5 loads bge-small (384d) via SentenceTransformer, stamps records with bge-m3 (1024d). Every cluster record carries a lie about its embedding model.

**Fix:** Unify both config values to `BAAI/bge-small-en-v1.5` (the actually-used model). Add a runtime mismatch check: if `embed_model ≠ embed_model_hf`, warn and refuse to run.

**Files:** `config/pipeline_config.yaml`, `pipeline/stage1_5_embed_cluster.py`.

---

### D2157 — Fix requirements.txt Gaps (C5 Violation)
**Category:** INF | **State:** ACTIVE | **Priority:** 🟠 HIGH

**Finding:** `requirements.txt` does not list `faiss-cpu`, `sentence-transformers`, or `transformers`, yet all three are imported by pipeline stages. Constitution C5 requires "all imports must be in requirements.txt."

**Fix:** Add `faiss-cpu>=1.7`, `sentence-transformers>=2.2`, `transformers>=4.40` to requirements.txt.

**Files:** `requirements.txt`, `pipeline/stage1_5_embed_cluster.py`, `pipeline/stage5_verify.py`.

---

### D2158 — Fix coverage_check.py Hardcoded Model (C12 Violation)
**Category:** CFG | **State:** ACTIVE | **Priority:** 🟠 HIGH

**Finding:** `coverage_check.py` line 14: `MODEL_NAME = "BAAI/bge-small-en-v1.5"` — hardcoded, not reading from config. If S1.5 switches embedding models, the coverage check operates in a different vector space. Cosine similarities are not comparable across models, producing false positives/negatives.

**Fix:** Read `S15_EMBED_MODEL_HF` and `S15_EMBED_DIM` from `pipeline_paths.py` config.

**Files:** `pipeline/coverage_check.py` line 14.

---

### D2159 — Fix Non-Deterministic Golden Selection
**Category:** QLT | **State:** ACTIVE | **Priority:** 🟠 HIGH

**Finding:** `stage2_extract.py` lines 359-360 call `random.shuffle(all_pos)` and `random.shuffle(all_neg)` with no explicit seed. Even with `temperature=0`, the prompt composition can differ between runs, making the pipeline non-deterministic despite the temp=0 guarantee.

**Fix:** Add `golden_seed` to `config/pipeline_config.yaml`. Call `random.seed(golden_seed)` before shuffle. Persist selected example IDs with every extraction.

**Files:** `pipeline/stage2_extract.py` lines 357-366, `config/pipeline_config.yaml`.

---

### D2160 — Fix CRIBS Silent Error Swallowing (C16 Violation)
**Category:** QLT | **State:** ACTIVE | **Priority:** 🟡 MEDIUM

**Finding:** `stage4_merge.py` line 814: `except Exception: pass` — enrichment failure is silently swallowed with zero log or trace. Violates C16: "No silent errors — except clauses must log AND raise."

**Fix:** Log enrichment failure with FB name + error. Set `enrichment_status: FAILED` and `enrichment_error: str` on the FB record.

**Files:** `pipeline/stage4_merge.py` line 814.

---

### D2161 — Fix Cluster Sampling Bias (Evidence Selection)
**Category:** QLT | **State:** ACTIVE | **Priority:** 🟡 MEDIUM

**Finding:** `stage2_extract.py` lines 229-235: `sampled = seg_ids[:n_samples]` — samples only the FIRST N segments from a cluster. A 40-book cluster may have the LLM seeing passages from only 2-3 books. The LLM is told "N passages from Y books" but Y is the book count in the SAMPLE, not the cluster.

**Fix:** Stratified sampling by source book + centroid proximity. Group segments by book, sample proportionally from each, fill remaining slots with centroid-nearest segments.

**Files:** `pipeline/stage2_extract.py` lines 229-235.

---

### D2162 — R-NN Transitive Chaining Mitigation (Diameter Constraint)
**Category:** ARCH | **State:** ACTIVE | **Priority:** 🟡 MEDIUM

**Finding:** R-NN reciprocity eliminates one-hop non-reciprocal edges but union-find still creates connected components with transitive chains (A↔B, B↔C but NOT A↔C → A and C in same component). The code comments overstate the reciprocity guarantee.

**Fix:** Add post-processing: for each connected component, compute max pairwise cosine distance (diameter). If diameter > 0.65, split via k-means (k=2) or complete-link clustering. This is O(n²) per component but components are small (mean 25, max 500).

**Files:** `pipeline/stage1_5_embed_cluster.py` lines 249-290.

---

### D2163 — Principle Discovery Gate (1:N Extraction)
**Category:** ARCH | **State:** ACTIVE | **Priority:** 🟡 MEDIUM

**Decision:** Before S2 extraction, add a lightweight probe (Phi-4-mini): "How many distinct principles (0-4) are in this cluster?" If N>1, split the cluster by k-means sub-clustering (k=N) before extracting each.

**Rationale:** Consensus of all 3 competent evaluators. Current 1-FB-per-cluster constraint forces the LLM to produce Frankenstein syntheses when a cluster contains multiple distinct principles.

**Implementation:**
1. Trigger for clusters with size > 30 AND cohesion < 0.85
2. Split probe via Phi-4-mini (fast, ~1.5s per cluster)
3. K-means split by discovered principle count
4. Extract each sub-cluster independently

**Estimated yield:** ~800 FBs → ~1,200-1,800 FBs (1.5-2.25× increase). Increased recall without quality loss.

**Files:** `pipeline/stage2_extract.py` (new S2A pre-extraction gate).

---

### D2164 — Claim-Level Verification Architecture
**Category:** ARCH | **State:** PLANNED | **Priority:** 🟡 MEDIUM

**Decision:** Replace FB-level NLI verification with FActScore-style atomic claim decomposition:
1. Break FB definition into 2-8 atomic claims (Phi-4-mini)
2. Retrieve best-matching evidence passage per claim
3. NLI entailment per claim (ModernBERT, with D2151 fix applied)
4. Compute coverage score: `support_precision = passed_claims / total_claims`
5. Contradiction rate: `contradicted_claims / total_claims`

**Rationale:** FB-level NLI is too coarse — a vague definition can pass while individual claims are unsupported. Atomic verification is the only way to guarantee epistemic integrity.

**Effort:** ~200 LOC. Phase 2 (after Phase 0-1 complete).

---

### D2165 — Principle-Recall Benchmark (Mandatory Evaluation)
**Category:** QLT | **State:** PLANNED | **Priority:** 🟡 MEDIUM

**Decision:** Create a gold benchmark: manually annotate 500 principles from 20 source books. Run pipeline. Measure:
- **Principle Recall:** recovered_principles / known_principles
- **Principle Precision:** valid_principles / total_extracted
- **Mutation Rate:** principles falsely merged or altered
- **Evidence Coverage:** % of FB claims supported by evidence passages

**Gate:** Without this benchmark, the 19,438 → 800 compression story is uninterpretable. 800 FBs could mean excellent abstraction or 95% information destruction.

**Effort:** 3-4 days human annotation + 1 day benchmark harness.

---

### D2166 — Semantic Chunking (S1.1 Pre-Chunk Stage)
**Category:** ARCH | **State:** PLANNED | **Priority:** 🟢 LOW

**Decision:** Before fixed-size chunking, run a rolling-window semantic coherence detector. Embed 3-sentence sliding windows (bge-small, MPS). If cosine similarity between adjacent windows drops below 0.65, insert a chunk boundary. This ensures chunks contain semantically coherent content.

**Rationale:** Current chunking likely slices principles in half. A principle split across two chunks becomes two singletons or two weakly connected clusters. Semantic chunking would improve cluster quality more than any clustering algorithm change.

**Effort:** ~60 LOC. Phase 1+ (after Phase 0-1 complete).

---

## 4. RE-RUN ANALYSIS

### Do S0–S1.5 need re-running after Phase 0 bug fixes?

**NO.** Here's why:

| Stage | Affected by Bugs? | Re-run Required? | Rationale |
|-------|-------------------|------------------|-----------|
| **S0** (convert) | No | ❌ | EPUB→MD conversion is independent of S2/S5 code bugs |
| **S0.5** (metadata) | No | ❌ | Author/title extraction is independent |
| **S1** (chunk) | No | ❌ | SHA-256 chunking is independent. Semantic chunking (D2166) would require re-chunking but that's Phase 1+ |
| **S1.3** (prefilter) | No | ❌ | Regex patterns are independent. Output already verified (376 drops of 289,498 → 289,122 segments) |
| **S1.5** (embed+cluster) | No | ❌ | **Embeddings are correct.** bge-small-en-v1.5 (384d) was the model actually used. The config stamp bug (D2156) is a metadata issue — the vectors are valid for the model that produced them. Clustering is valid: 0.886 mean cohesion, 99.1% segment coverage, 953/953 books covered. R-NN transitive chaining (D2162) is a design improvement, not a correctness bug. |

**The S1.5 checkpoint at `knowledge pipeline/stage1_5_embed_cluster/latest/checkpoint.jsonl` with 1,110 clusters and 2,804 singletons is PRODUCTION-READY.**

### Do golden samples need re-running?

**NO — but they need expansion.** The 7 golden examples in `config/golden/stage2_fewshot_convergent.yaml` are well-constructed. They were not affected by the NLI/MinHash/Start bugs since S2 hasn't run yet. However:

1. **Coverage:** Only 3 domains (pricing, behavioral change, advertising). Need 30+ across 10+ domains for dynamic selection
2. **Validation:** After Phase 0 fixes, re-validate golden examples against the fixed SYSTEM_PROMPT to ensure no schema drift
3. **Format:** No changes needed for Phase 0 fixes. Format change needed when D2163 (principle discovery gate) is implemented

---

## 5. AGGREGATED PRIORITIZED TASK LIST

### 🔴 PHASE 0 — STOP THE BLEEDING (Today, ~2 hours)
*Fix the 5 code-verified critical bugs. Do NOT run S2 before these are fixed.*

| # | ID | Bug | File | Line | Effort |
|---|-----|-----|------|------|--------|
| P0.1 | D2151 | NLI input format — single string instead of pair dict | stage5_verify.py | 136 | 5 min |
| P0.2 | D2152 | MinHash dedup disabled — `_jaccard` never populated | stage2_extract.py | 765 | 20 min |
| P0.3 | D2153 | Dead code — `start`/`result`/`is_summary` undefined | stage2_extract.py | 781-786 | 2 min |
| P0.4 | D2154 | Checkpoint index out of scope — only writes once | stage2_extract.py | 787-800 | 15 min |
| P0.5 | D2155 | Three NLI thresholds, config says one | stage5_verify.py | 430-460 | 10 min |
| P0.6 | D2156 | Config embed mismatch — bge-m3 stamped, bge-small used | config/pipeline_config.yaml | — | 30 min |
| P0.7 | D2159 | Non-deterministic golden selection — no seed | stage2_extract.py | 359-360 | 5 min |
| P0.8 | D2160 | CRIBS `except: pass` — silent error swallowing | stage4_merge.py | 814 | 5 min |
| P0.9 | D2157 | requirements.txt gaps — missing 3 packages | requirements.txt | — | 5 min |
| P0.10 | D2158 | coverage_check hardcoded model | coverage_check.py | 14 | 10 min |

### 🟠 PHASE 0.5 — GOVERNANCE DRIFT (Today, ~1 hour)

| # | Drift | Fix | Effort |
|---|-------|-----|--------|
| G1 | DRIFT-1 | Renumber duplicate D2118 | 10 min |
| G2 | DRIFT-2 | Update requirements.txt to v3.0 | 2 min |
| G3 | DRIFT-3 | Unify config embed values | Covered by P0.6 |
| G4 | DRIFT-4 | Add 5 critical bugs to buglog.md | 15 min |
| G5 | DRIFT-5 | Update MASTER-TASK-REGISTER with S1.5 results + D2148-D2150 | 20 min |
| G6 | DRIFT-6 | Mark D2032 as RESOLVED by D2066 | 2 min |
| G7 | DRIFT-7 | Update buglog status footer | 2 min |
| G8 | — | Append D2151-D2166 to DECISION-LOG.md | 15 min |
| G9 | — | Sync decisions.yaml with D2151-D2166 | 10 min |

### 🟡 PHASE 1 — PREVENT THE 291:1 BOTTLENECK (3-5 days)

| # | ID | Task | Effort |
|---|-----|------|--------|
| P1.1 | D2161 | Fix cluster sampling bias — stratified by book | 2h |
| P1.2 | D2162 | R-NN diameter constraint post-processing | 2-3h |
| P1.3 | D2163 | Principle discovery gate (1:N extraction) | 1 day |
| P1.4 | — | Fix S5 NLI threshold mismatch (P0.5 config wiring) | 30 min |
| P1.5 | — | 20-book E2E test (validate fixes) | 3h |
| P1.6 | — | Golden set expansion: 7 → 30+ examples across 10+ domains | 2h (manual review) |
| P1.7 | — | Run S2 on full corpus (1,110 clusters) | 60-90 min |
| P1.8 | — | Run S2 --process-singletons (2,804 singletons) | ~30 min |
| P1.9 | — | Run coverage_check.py post-S2 | ~20 min |
| P1.10 | D2166 | Implement semantic chunking (S1.1) — highest ROI architectural improvement | 1 day |

### 🟢 PHASE 2 — CLAIM-LEVEL VERIFICATION + GRAPH (2-3 weeks)

| # | ID | Task | Effort |
|---|-----|------|--------|
| P2.1 | D2164 | Claim-level verification (FActScore-style) | 4-5 days |
| P2.2 | — | Typed relationship edges (S4.5) — prerequisite, contradicts, enables, refines | 1 week |
| P2.3 | D2165 | Principle-recall benchmark (mandatory) | 3-4 days |
| P2.4 | — | Cross-run dedup — prevent duplicate FBs across pipeline runs | 1 day |
| P2.5 | — | Cross-run relationship merge — connect graph islands | 1 day |

### 🔵 PHASE 3 — AGENTIC READINESS (4-8 weeks)

| # | Task |
|---|------|
| P3.1 | MCP interface — 8 tools, stdio transport (D2058) |
| P3.2 | Agentic trigger fields — trigger_condition, anti_pattern, application_context |
| P3.3 | Hybrid retrieval — FTS + dense + graph traversal + reranking |
| P3.4 | Query decomposition — subquestion-based retrieval planning |

---

## 6. IMMEDIATE NEXT ACTION

```bash
# 1. Fix Phase 0 bugs (D2151-D2160) — ~2 hours
# 2. Fix governance drift (G1-G9) — ~1 hour
# 3. Restart OMLX: python3 pipeline/omlx_watchdog.py
# 4. Run S2: python3 pipeline/stage2_extract.py
#    (with fixed NLI, MinHash, checkpoint, thresholds)
# 5. Run coverage: python3 pipeline/coverage_check.py
# 6. Run S4 → S5 → S6 (sequential)
```

**Gate before S2:** All Phase 0 bugs fixed AND OMLX healthy.
**Gate before S4:** S2 output validated (≥500 FBs, ≤5% NULL, ≤10% gate violations). 
**S0-S1.5:** Do NOT re-run. Existing checkpoint is production-ready.
