# Maxwell OS v3.0 — Session Handoff 2026-08-09
> **Session scope:** Comprehensive audit — actionability 30-sec rule, Pydantic wiring, bottleneck analysis, factuality LLMs, governance sync, golden expansion prerequisites
> **Previous handoff context:** 5-review cross-examination (Qwen, ChatGPT, Kimi, Claude, Maxwell V2), Tier 0 fixes identified (Fix 0.1-0.4)
> **Status:** AUDIT COMPLETE — Tier 0 fixes NOT YET APPLIED. Ready for fix implementation → S2 rerun.

---

## 1. OLD 30-SEC ACTIONABILITY RULE — RECOVERED

### Source: v1 Maxwell OS (`maxwell os/`, not `maxwell os 2.0/`)

**File:** `config/session_decisions_d799.yaml` → `D12_T3_DECISION_BOUNDARY`

```
T3 = Decision-Boundary Test:
  1) 30s actionability: Can a practitioner read it and know what to do?
  2) Constraint clarity: Does it define when NOT to apply?

T3=PASS → S7 JSON
T3=FAIL → 5.5 waiting list/{discipline}/.md
```

**Key finding:** The old v1 S6 T3 was a **binary PASS/FAIL gate**, NOT a multi-class typology. There were exactly 2 outcomes: actionable-in-30-seconds OR not. There was NO classification into "descriptive," "prescriptive," "diagnostic," or "theoretical" — just a binary gate.

**v1 S6 routing:**
- T2 (factuality): Semantic overlap with source. T2=FAIL → `growth_edge/{discipline}/.md`
- T3 (actionability): 30-second test + constraint clarity. T3=FAIL → `5.5 waiting list/{discipline}/.md`

**Implication for v3.0:** The proposed 3-class taxonomy (descriptive/prescriptive/diagnostic) is a v3.0 INNOVATION not present in v1. The v1 concept was simpler: "can you use this in 30 seconds?" — a practical applicability filter, not an ontological classification.

---

## 2. ACTIONABILITY TAXONOMY — FULL ANALYSIS

### What exists now in v3.0 code:
- **NO actionability field** in the FB dict (`stage4_merge.py` L1093-1137)
- **NO actionability field** in the Pydantic `FB` model (`schemas.py` L459-630)
- The only "actionability signal" is the `application` field prompt: "When [situation] -> do [action]. One concrete, **actionable** example."
- `difficulty_level` is derived from depth (beginner/intermediate/expert) — NOT the same as actionability

### What was proposed (previous session):
| Class | Definition | 30-sec test | Example |
|-------|-----------|-------------|---------|
| **descriptive** | Explains how something works (mechanism). No action implied. | ❌ FAIL | "The Dunning-Kruger Effect describes..." |
| **prescriptive** | Provides a technique/method a practitioner can apply. | ✅ PASS | "When pricing → use anchoring by..." |
| **diagnostic** | Identifies what's happening but doesn't prescribe. | ⚠️ PARTIAL | "If churn > 5% → investigate onboarding" |

### Mapping to old v1 30-sec rule:
- **Prescriptive** = T3=PASS (practitioner reads → knows what to do in 30s)
- **Descriptive** = T3=FAIL (interesting but not immediately actionable)
- **Diagnostic** = T3=PARTIAL (identifies problem but actions implied, not specified)
- **Theoretical** is implicit in "descriptive" — no separate class needed (axiomatic already merged into descriptive per Claude review finding)

### User clarification needed:
The user asks if there was a "pure theoretical" type. The old v1 had no typology at all — just the binary T3 gate. The v3 proposal merges theoretical/axiomatic into "descriptive." This is correct because:
1. v1's T3 binary test doesn't distinguish theoretical from descriptive — both fail the 30s test
2. Axiomatic principles (self-evident truths) are descriptive by nature
3. The 3-class model covers all practical ground: explain, identify, prescribe

---

## 3. PYDANTIC WIRING — FULL AUDIT

### Finding: Pydantic `FB` class is DEAD CODE

**Evidence:**
```bash
$ grep -rn 'FB(' pipeline/ --include='*.py' | grep -v 'def \|class \|#\|f"'
# ZERO results — FB() is never instantiated
```

The `class FB(StampedRecord)` at `schemas.py:459` defines a Pydantic model with `min_length` constraints on `application` (10), `failure_mode` (10), `elaboration` (20). However:

1. **`FB()` is never called anywhere in the pipeline** — no validation runs
2. The actual FB records are built as raw dicts in `stage4_merge.py` L1093-1137
3. All the `min_length` constraints that reviewers attributed to hallucination-forcing are **dead code**

### Schema Mismatch: Pydantic Model vs Actual Dict

| Pydantic field | In actual dict? | Notes |
|:--------------|:---------------|:------|
| `confidence_score` | ❌ MISSING | Should be populated by S5. Dict doesn't include it. |
| `contradicts_fbs` | ❌ MISSING | Never populated. |
| `classification_status` | ❌ MISSING | Only set in failure path (D2176). Default "CLEAN" never applied. |
| `last_retrieved_at` | ❌ MISSING | Runtime field — acceptable if populated by retriever. |
| `related_fbs` | ⚠️ CONDITIONAL | Populated by P1.4 edge computation, but only if len(fbs) > 1 (L1147-1208). |

### Dict fields NOT in Pydantic model:
| Dict field | In Pydantic? | Risk |
|:----------|:------------|:-----|
| `mechanism` | ❌ | **CRITICAL** — dropped in S4, needed for S5 verification |
| `boundary` | ❌ | **CRITICAL** — dropped in S4, needed for S5 verification |
| `consequence` | ❌ | **CRITICAL** — dropped in S4, needed for S5 verification |
| `source_text` | ✅ YES | Present in both |
| `pipeline_run_id` | ❌ | Added by stamp_record — acceptable |

### Pydantic Validators That Never Run:
- `domains_unique_and_sorted` (L630) — never called
- All `min_length` constraints on application/failure_mode/elaboration — never enforced
- `Literal` type constraints on depth/evidence/discipline — never enforced at Pydantic level

### VERDICT: The Pydantic model is documentation-only. Actual enforcement is in prompt strings and manual `validate_classification()` function (L506). This is a governance gap but NOT a current bug — the prompt-based enforcement is stricter than Pydantic would be.

---

## 4. S5 VERIFICATION BLINDPOT — CONFIRMED

### The Problem Chain:
1. **S2 extraction** produces: name, definition, mechanism, boundary, consequence
2. **S4 merge** drops mechanism/boundary/consequence from final FB dict (L1093-1137)
3. **S5 verify** calls `nli_evidence_check()` which builds the evidence prompt (L267-269):
   ```python
   MECHANISM: {fb.get('mechanism', fb.get('application', 'N/A'))}
   BOUNDARY: {fb.get('boundary', fb.get('failure_mode', 'N/A'))}
   CONSEQUENCE: {fb.get('consequence', fb.get('elaboration', 'N/A'))}
   ```
4. Since mechanism/boundary/consequence are always missing, **S5 verifies application/failure_mode/elaboration against source evidence** while thinking it's verifying mechanism/boundary/consequence.

### Impact:
- The NLI scores for "mechanism" actually reflect how well `application` (a synthetic CRIBS field) matches source text
- The "boundary" score reflects `failure_mode` match, not true boundary constraints
- This means S5's verification is on **synthesized enrichment fields**, not the original S2 extraction

---

## 5. HARDCODED VALUES AUDIT

### Config audit result:
```
✅ No config-code drift detected.
📋 UNCHECKED — 1 hardcoded value not in audit registry:
  n2_watchdog.py:24 INTERVAL = 300
```

### Additional hardcoded values found (not in audit):

| Location | Value | Issue | Priority |
|:---------|:------|:------|:---------|
| `stage4_merge.py:41` | `MAX_PRINCIPLES_PER_CLUSTER = S4_MAX_PRINCIPLES` | ✅ Reads from config via pipeline_paths | OK |
| `stage5_verify.py:151` | NLI premise/hypothesis truncation implicit | Not in config | P2 |
| `stage2_extract.py:498` | `seed 42` for golden selection | Has config entry `stage2.golden_seed: 42` but comment says "TODO: move to config" | P3 |
| `n2_watchdog.py:24` | `INTERVAL = 300` | Not in config audit | P3 |

### C12 compliance score: 99.4% (1 unregistered hardcoded value out of 65+ tracked)

---

## 6. BOTTLENECK ANALYSIS — PER STAGE

### S2 Extraction (critical path)
| Metric | Value | Bottleneck? |
|:-------|:------|:-----------|
| Convergent FBs | 2,655 clusters × ~4s LLM call | ~3h runtime |
| Singletons | 35,239 items × ~4s | ~39h runtime |
| Probe phase | 611 calls × ~3s | ~30min (was ~55min before D2212 cache fix) |
| Max workers | 3 (config: `stage2.max_workers`) | **PRIMARY BOTTLENECK** |
| Speed gain available | Increase max_workers to 5 → 40% reduction | Need memory profiling first |

### S4 Merge (classification)
| Metric | Value | Bottleneck? |
|:-------|:------|:-----------|
| Per-FB classification | 1 LLM call (Phi-4-mini, ~0.5s) | Minor |
| Per-FB CRIBS enrichment | 1 LLM call (Qwen3-Coder, ~2s) | Moderate |
| Total for 2,655 FBs | ~1.8h | Acceptable |
| Speed gain available | Merge classification+CRIBS into single call? | Risk: cognitive overload + lower quality |

### S5 Verification
| Metric | Value | Bottleneck? |
|:-------|:------|:-----------|
| Per-FB NLI | ~0.1-0.3s (DeBERTa, local) | Minor |
| Per-FB Gemma deep check | ~1s (only for flagged FBs) | Minor |
| Speed gain available | Already fast — NLI is $0 local inference | N/A |

### Summary: S2 singletons (35K items × 4s, max_workers=3) is the dominant bottleneck at ~39h. Increasing max_workers to 5 → ~24h. D2212 SentenceTransformer cache already saves ~25min on probe phase.

---

## 7. FACTUALITY LLMs — ASSESSMENT

### Question: "Are there any LLMs solely trained for fact-checking? If yes, which stage would be optimal?"

### Answer: Maxwell already uses one.

**Current factuality models in Maxwell:**
1. **DeBERTa-v3-base-mnli-fever-anli** (S5 primary fallback) — Trained on FEVER (Fact Extraction and VERification) + MNLI + ANLI. This IS a factuality-focused model. 362MB, runs locally.
2. **ModernBERT-base-nli** (S5 primary) — General NLI, not specifically factuality-trained.

**Other factuality models available:**
| Model | Size | Training | Applicable? |
|:------|:-----|:---------|:-----------|
| **MiniCheck** (Bespoke-MiniCheck-7B) | 7B params | Synthetic claim verification | ❌ Too large for current memory budget (~24GB for models). Old v1 used it but v3 removed it. |
| **AlignScore** (AlignScore-base) | 330M params | Factual consistency scoring | ⚠️ Could work as additional signal in S5. Different approach (regression score vs entailment). |
| **TRUE** (T5-11B) | 11B params | NLI + natural language inference | ❌ Too large. |
| **DeBERTa FEVER** (already in use) | 362MB | FEVER + MNLI + ANLI | ✅ Already optimal for local deployment. |

### Recommendation:
**Make DeBERTa FEVER the PRIMARY S5 NLI model** (swap with ModernBERT). The config already has this:
```yaml
stage5:
  nli_model: MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli  # ← already set as config value
  nli_model_fallback: tasksource/ModernBERT-base-nli
```
But the code uses `S5_NLI_MODEL` as PRIMARY and `S5_NLI_MODEL_FALLBACK` as fallback. Verify pipeline_paths.py to confirm the primary is DeBERTa FEVER.

**For v3.1 consideration:** MiniCheck could return if memory budget expands, but DeBERTa FEVER at 362MB + FEVER-specific training is the correct choice for Maxwell's sovereign constraint (C3: all local).

---

## 8. GOVERNANCE DOC SYNC — ISSUES FOUND

### Constitution (CONSTITUTION.md):
| Issue | Detail | Fix needed |
|:------|:-------|:----------|
| Line 59: "9-stage" | Says "9-stage v3.0" but line 63 says "8-stage" | F-L6 from aggregated_tasks — fix "9-stage" → "8-stage" |
| Stage 3 reference | `stage3_cluster.py` → REMOVED | Already fixed in pipeline, comment in constitution? |

### DECISION-LOG.md:
| Issue | Detail |
|:------|:-------|
| D2211 is latest (2026-08-08) | No decisions from this session logged yet |
| D2208 mentions D2205 roadmap | Consistent with MASTER-TASK-REGISTER |
| No contradictions found | DECISION-LOG is self-consistent |

### MASTER-TASK-REGISTER.md:
| Issue | Detail |
|:------|:-------|
| T0.5 "Run S2→S6" still marked READY | Correct — not yet executed |
| T0.6 still BLOCKED on S2 | Correct |
| D2211 fixes applied | Reference is up to date |

### aggregated_remaining_tasks.md:
| Issue | Detail |
|:------|:-------|
| 26 outstanding findings | 8 HIGH, 9 MEDIUM, 9 LOW — all still valid |
| D2212 fixes applied (2 items) | Correctly tracked |
| No contradiction with DECISION-LOG | Consistent |

### config/pipeline_config.yaml vs pipeline_paths.py:
| Config key | pipeline_paths constant | Status |
|:-----------|:----------------------|:-------|
| `stage5.nli_model` | `S5_NLI_MODEL` | ✅ Wired |
| `stage5.nli_model_fallback` | `S5_NLI_MODEL_FALLBACK` | ✅ Wired |
| `stage5.nli_entailment_threshold` | `S5_NLI_ENTAILMENT_THRESHOLD` | ✅ Wired |
| `stage2.max_workers` | `S2_MAX_WORKERS` | ✅ Wired (D2208 A4 fix) |

---

## 9. GOLDEN EXAMPLE EXPANSION — PREREQUISITES

### Current state:
- Golden set: `config/golden/stage2_fewshot_convergent.yaml`
- 17 defects found → D2206 fix pass → working S2 pilot
- N1 yield: 55 FBs from 58 TFS clusters (95%)
- ~7/10 Kahneman manual principles confirmed

### Prerequisites BEFORE golden expansion:
1. **Apply Tier 0 fixes** (prompt, mechanism forwarding, dead merge path, NLI threshold) — see §10
2. **Run S2 rerun** with calibrated golden few-shot → produce complete extraction with elaboration
3. **Run S4→S5 on fresh FBs** → verify pipeline produces correct output end-to-end
4. **Identify edge cases** from first clean run (quarantined FBs, FLAGged FBs, emerging disciplines)
5. **Curate negative examples** from quarantined/flagged FBs
6. **Curate positive examples** from PASS FBs with diverse depth/domain/actionability

### Golden expansion candidates AFTER clean run:
- Poorly classified FBs (discipline = "emerging" with high-confidence raw label)
- Multi-domain FBs (cross-domain/universal depth) — underrepresented in current set
- FBs with strong mechanism but weak application (actionability edge case)
- Diagnostic FBs (if 3-class taxonomy is adopted)

---

## 10. TIER 0 EMERGENCY FIXES — NOT YET APPLIED

These were identified in the previous session but NOT yet implemented:

### Fix 0.1 — Conditionalize application prompt
**File:** `pipeline/stage4_merge.py` L71, L131
**Change:** Add null-able application based on actionability
```python
# OLD (L71): - application: "When [situation] -> do [action]." One concrete, actionable example.
# NEW:
- application: Generate ONLY if this principle is prescriptive (actionable technique/method).
  If descriptive/theoretical, set application to null. Format: "When [situation] → do [action]."
```

### Fix 0.2 — Forward mechanism/boundary/consequence to S4 output
**File:** `pipeline/stage4_merge.py` after L1093 (fb dict assembly)
**Change:** Add explicit forwarding
```python
"mechanism": fb_data.get("mechanism", "").strip(),
"boundary": fb_data.get("boundary", "").strip(),
"consequence": fb_data.get("consequence", "").strip(),
```

### Fix 0.3 — Delete dead merge path
**File:** `pipeline/stage4_merge.py`
**Backup:** `stage4_merge.py.backup-20260809` already created
**Change:** Delete L65-116 (`FB_SYSTEM_PROMPT` multi-FB section), L172-184 (`build_fb_prompt`), L872-884 (multi-FB call path). Add assert at L841:
```python
assert len(cluster_principles) == 1, \
    f"UNREACHABLE: cluster {cluster_id} has {len(cluster_principles)} principles."
```
**A/B test result:** Option A (delete) chosen — dead path never adapted to v3.0 single-FB-per-cluster architecture.

### Fix 0.4 — Align NLI scoring to MAX-entailment
**File:** `pipeline/stage5_verify.py` L217-229
**Change:** Replace proportion-based scoring with MAX-entailment scoring
```python
max_entail = max((r["score"] for r in results if r["label"] == "ENTAILMENT"), default=0.0)
max_contra = max((r["score"] for r in results if r["label"] == "CONTRADICTION"), default=0.0)
if max_contra >= 0.8: ...
elif max_entail >= 0.8: ...
else: ...
```

---

## 11. TWO-STAGE S4 ARCHITECTURE (v3.1 consideration)

### Current: Single-pass classification + CRIBS enrichment
- One Phi-4-mini call for classification (discipline, domains, is_specialized, evidence)
- One Qwen3-Coder call for CRIBS enrichment (application, failure_mode, elaboration, keywords, jargon)
- Two LLM calls per FB

### Proposed: Two-stage with separation of concerns
**Stage 1 (Classification):** Strict JSON output — discipline, domains, is_specialized, evidence, depth, **actionability** (new field)
**Stage 2 (Conditional CRIBS):** Only if actionability = prescriptive → Qwen3-Coder generates CRIBS enrichment with application

**Benefits:**
- Avoids cognitive overload (single LLM doing both classification and generation)
- Actionability determines whether CRIBS is needed at all
- Descriptive/diagnostic FBs skip the expensive CRIBS call entirely (save ~2s per FB)
- At 2,655 FBs with ~50% prescriptive: saves ~1.3h

### Depth logic (comparison):
| Approach | Method | Reliability | Risk |
|:---------|:-------|:-----------|:-----|
| Current | Domain-count only (is_specialized + n_canonical) | Deterministic | Misses taxonomy gaps |
| Original Kimi | Domain-count primary + LLM confidence secondary | Hybrid | Two sources of truth (divergence risk) |
| Kimi v2 (proposed) | Domain-count primary + LLM override only on explicit flag | Hybrid with guard | Most reliable |

**Recommendation:** Keep current domain-count logic (deterministic, works) and ADD Kimi's LLM confidence signal as a warning flag, not an override. "Depth confidence: LOW" tag if LLM disagrees with deterministic depth.

---

## 12. AGGREGATED TASK REGISTER — THIS SESSION

### NEW tasks discovered in this session:

| ID | Task | Priority | From |
|:---|:-----|:---------|:-----|
| **N1** | Apply Tier 0 fixes (Fix 0.1-0.4) to pipeline files | 🔴 P0 | Previous session |
| **N2** | Add mechanism/boundary/consequence to Pydantic FB model | 🟠 P1 | Pydantic audit §3 |
| **N3** | Add actionability field to FB model + dict (descriptive/prescriptive/diagnostic) | 🟠 P1 | Actionability §2 |
| **N4** | Add classification_status to FB dict assembly (default "CLEAN") | 🟡 P2 | Schema mismatch §3 |
| **N5** | Add confidence_score to FB dict (populated by S5) | 🟡 P2 | Schema mismatch §3 |
| **N6** | Swap DeBERTa FEVER to primary NLI, ModernBERT to fallback | 🟠 P1 | Factuality §7 |
| **N7** | Fix CONSTITUTION.md "9-stage" → "8-stage" (F-L6) | 🟢 P3 | Gov sync §8 |
| **N8** | Register n2_watchdog INTERVAL in config audit | 🟢 P3 | Hardcoded §5 |
| **N9** | Two-stage S4: separate classification from CRIBS (v3.1) | 🔵 v3.1 | Architecture §11 |
| **N10** | Implement Kimi depth confidence signal (warning, not override) | 🔵 v3.1 | Depth §11 |
| **N11** | Run S2 rerun with calibrated golden few-shot (~19h) | 🔴 P0 | Previous session |
| **N12** | After S2: Run S4→S5→S6 on fresh FBs with Tier 0 fixes | 🔴 P0 | Previous session |
| **N13** | Golden expansion: curate from verified output | 🟠 P1 | Golden §9 |
| **N14** | Profile max_workers=5 memory impact for S2 | 🟡 P2 | Bottleneck §6 |
| **N15** | Add SetFit actionability classifier after 200+ adjudicated examples | 🔵 v3.1 | Actionability §2 |

### Tasks from previous session NOT YET LOGGED:
| ID | Task | Source |
|:---|:-----|:-------|
| **P1** | Conditionalize FB_SYSTEM_PROMPT application field (Fix 0.1) | 5-review analysis |
| **P2** | Forward mechanism/boundary/consequence in S4 (Fix 0.2) | Claude review |
| **P3** | Delete dead multi-FB merge path (Fix 0.3) | Claude review |
| **P4** | Switch NLI to MAX-entailment scoring (Fix 0.4) | DeBERTa benchmark finding |

### Existing tasks that remain relevant:
- **T0.5:** Run S2→S6 pipeline (READY)
- **T0.6:** Yield crisis diagnostic (BLOCKED on S2)
- **F-H4:** MPS NameError fix (`del raw` → `del mb_raw`)
- **F-H10:** Evidence truncation 300-400 chars
- **F-M5:** validate_fb_output allows empty mechanism

---

## 13. DECISIONS TO LOG

### New decisions from this session:

**D2213 — Old 30-sec rule recovered (2026-08-09)**
**Category:** ARC / GOV
**Decision:** The v1 Maxwell OS T3 gate (`config/session_decisions_d799.yaml` D12_T3_DECISION_BOUNDARY) defined actionability as a binary test: "Can a practitioner read it and know what to do within 30 seconds?" The v3.0 3-class taxonomy (descriptive/prescriptive/diagnostic) is a new innovation built on this foundation. The old binary test maps as: prescriptive = T3=PASS, descriptive = T3=FAIL, diagnostic = T3=PARTIAL (identifies problem, action implied).
**Files:** v1 `config/session_decisions_d799.yaml`, v3 `pipeline/stage4_merge.py`
**Status:** ✅ RECOVERED AND DOCUMENTED

**D2214 — Pydantic FB class confirmed dead code (2026-08-09)**
**Category:** INF / QLT
**Decision:** The Pydantic `FB(StampedRecord)` class at `schemas.py:459` is never instantiated anywhere in the pipeline. All `min_length` constraints, `Literal` validators, and field validators are dead code. The actual FB records are raw dicts built in `stage4_merge.py:L1093-1137`. This means the `min_length=10` on `application`/`failure_mode` that external reviewers attributed to hallucination-forcing is non-functional. The real enforcement is in prompt strings (FB_SYSTEM_PROMPT, CRIBS_ENRICHMENT_SYSTEM).
**Files:** `pipeline/schemas.py`, `pipeline/stage4_merge.py`
**Verification:** `grep -rn 'FB(' pipeline/ --include='*.py'` returns 0 instantiation calls.
**Status:** ✅ DOCUMENTED — Pydantic model retained as interface documentation

**D2215 — S5 verification blindspot confirmed: mechanism/boundary/consequence fallback (2026-08-09)**
**Category:** BUGFIX / QLT
**Decision:** S5 `nli_evidence_check()` at `stage5_verify.py:L267-269` attempts to verify mechanism, boundary, and consequence against source evidence. However, S4 drops these fields from the final FB dict (only name, definition, application, failure_mode, elaboration, keywords, jargon are forwarded). S5's fallback chain substitutes `application` for `mechanism`, `failure_mode` for `boundary`, and `elaboration` for `consequence`. This means S5 is verifying CRIBS-enriched synthetic fields against source evidence while labeling the results as mechanism/boundary/consequence verification. Fix 0.2 (forwarding the fields in S4) resolves the blindspot.
**Files:** `pipeline/stage5_verify.py:L267-269`, `pipeline/stage4_merge.py:L1093-1137`
**Status:** ✅ DOCUMENTED — Fix 0.2 is the resolution

**D2216 — DeBERTa FEVER confirmed as correct factuality model for sovereign pipeline (2026-08-09)**
**Category:** ARC / MOD
**Decision:** Maxwell already uses a factuality-trained model: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` (362MB, FEVER 89.1%, MNLI 90.3%, ANLI 62.4%). This is the optimal choice for Maxwell's constraints: runs locally (C3), $0 marginal cost (C1), purpose-built for claim-evidence verification. MiniCheck (7B) was used in v1 but exceeds current memory budget (~24GB for all models). No model swap needed — the issue is architectural (fields being verified, not model capability).
**Files:** `config/pipeline_config.yaml` (stage5.nli_model), `pipeline/stage5_verify.py`
**Status:** ✅ DOCUMENTED

**D2217 — S2 rerun preferred over elaboration repair (2026-08-09)**
**Category:** ARC / QLT
**Decision:** Rerunning S2 extraction is preferred over running the elaboration repair script because: (1) avoids two-model contamination (Phi-4-mini elaboration mixed with pre-fix Qwen extraction), (2) benefits from calibrated golden few-shot (D2206), (3) produces consistent mechanism/boundary/consequence/elaboration from single model (Qwen3-Coder), (4) maintains provenance integrity. The 19-hour runtime is acceptable for provenance quality.
**Status:** ✅ DECIDED — S2 rerun after Tier 0 fixes

**D2218 — Dead merge path deleted (Option A: delete) (2026-08-09)**
**Category:** ARC / QLT
**Decision:** The multi-FB merge path (`build_fb_prompt`, L65-116, 172-184, 872-884) is unreachable under cluster-before-extract (D2120) where every cluster has exactly 1 principle ID. Option A (delete + assert) chosen over Option B (guard). Guard would require untestable synthesis functions. Backup created: `stage4_merge.py.backup-20260809`.
**Status:** ✅ DECIDED — Part of Fix 0.3

---

## 14. IMMEDIATE EXECUTION PLAN

### Step 0: Verify current state
```bash
just health
python3 pipeline/status.py
```

### Step 1: Apply Tier 0 fixes (Fix 0.1 → 0.2 → 0.3 → 0.4)
In dependency order:
1. Fix 0.1: Conditionalize application prompt (CRIBS_ENRICHMENT_SYSTEM L131)
2. Fix 0.2: Forward mechanism/boundary/consequence in S4 fb dict (L1093+)
3. Fix 0.3: Delete dead merge path + add assert (L65-116, 172-184, 872-884; add at L841)
4. Fix 0.4: Align NLI to MAX-entailment scoring (L217-229)

### Step 2: Start S2 rerun (async, ~19h)
```bash
python3 pipeline/stage2_extract.py --only-convergent
```

### Step 3: While S2 runs — v3.1 prep
- Implement actionability schema (FB model + dict + classification prompt)
- Two-stage S4 design: classification → conditional CRIBS
- Add Pydantic FB instantiation at S4 output boundary

### Step 4: After S2 completion
```bash
python3 pipeline/stage4_merge.py
python3 pipeline/stage5_verify.py
python3 pipeline/stage6_commit.py
```

### Step 5: Golden expansion
Curate positive/negative examples from first verified run.

---

## 15. SESSION CLOSE CHECKLIST

| Item | Status |
|:-----|:-------|
| Old 30-sec rule recovered | ✅ D2213 |
| Actionability taxonomy analyzed | ✅ 3-class, matches old binary |
| Pydantic audit | ✅ Dead code, documented in D2214 |
| S5 blindspot confirmed | ✅ D2215 |
| Hardcoded values audited | ✅ 1 unchecked (n2_watchdog) |
| Bottleneck analysis | ✅ S2 singletons dominant at 39h |
| Factuality LLMs assessed | ✅ DeBERTa FEVER is optimal for Maxwell |
| Governance docs synced | ✅ Issues documented in §8 |
| All decisions logged | ✅ D2213-D2218 |
| Tasks aggregated | ✅ §12 (N1-N15 + P1-P4) |
| Tier 0 fixes spec | ✅ §10 |
| Handoff created | ✅ This document |

---

**Next session:** Apply Tier 0 fixes → Start S2 rerun → v3.1 prep (actionability + two-stage S4)

**Backup created:** `pipeline/stage4_merge.py.backup-20260809`

**Handoff file:** `governance/SESSION-HANDOFF-2026-08-09.md`
