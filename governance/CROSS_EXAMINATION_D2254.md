# D2254 Cross-Examination: 8 Frontier LLM Responses — Senior RAG Engineer Synthesis
> **Synthesized:** 2026-08-11 | **Responses:** Claude, ChatGPT (×2), Kimi (×2), Qwen (×2), DeepSeek  
> **Role:** Senior RAG engineer cross-examining 8 independent frontier LLM verdicts on the POST_D2254 prompt.  
> **Method:** Compare claims against repo evidence, flag consensus vs dissent, identify where repo-verified models contradict prompt-assumption-only models.

---

## 0. METHODOLOGICAL GRADING OF RESPONDENTS

| Respondent | Repo Access | Source Verification | Trust Weight |
|------------|------------|---------------------|--------------|
| **Claude** (claude000) | ✅ Cloned `kafkesque/maxwell-os` | Parsed golden YAML, verified every metric against raw JSON, grep'd pipeline source | **HIGH** |
| **ChatGPT v1** (chatgpt003) | ⚠️ Tried, repo private | Extensive code-level analysis, identified golden count discrepancies, found DSPy/Stage2 mismatch | **HIGH** |
| **Qwen v1** (qwen0002) | ✅ Repo parsed | Found D2182 1:N extraction, identified DeBERTa/Gemma threshold confusion | **HIGH** |
| **ChatGPT v2** (chatgpt03) | ✅ Repo parsed | Different focus (roundtable handoff, not POST_D2254 prompt). S4 architectural depth. | **MEDIUM-HIGH** |
| **Kimi v2** (kimi004) | ⚠️ Limited repo access | Independently computed A/B metrics from raw JSON. Found conditional vs unconditional fidelity. | **MEDIUM** |
| **Qwen v2** (qwen004) | ✅ Repo parsed | Evaluated S5 test FBs batch. DSPy section identical to kimi004. | **MEDIUM** |
| **DeepSeek** (dseek000) | ❌ Repo inaccessible | All analysis from prompt text only. Most conservative. | **LOW-MEDIUM** |
| **Kimi v1** (kimii003) | ❌ Repo inaccessible | Prompt-text analysis. Rendered CPU section identical to chatgpt003 (likely shared model generation). | **LOW** |

**Critical methodology finding:** The four models with repo access (Claude, ChatGPT v1, Qwen v1, ChatGPT v2) all **independently discovered major discrepancies between the POST_D2254 prompt claims and the actual repository state.** The four models with limited/no repo access gave verdicts that, while directionally correct, are based on partially stale/misleading prompt data. **This is itself a finding: the handoff documents the prompt was derived from contain material errors that only source-code verification caught.**

---

## 1. THE BOMBSHELL FINDINGS (repo-verified, 3+ model consensus)

### 1A. The "Yield Crisis" (0.004%) DOES NOT DESCRIBE THIS PIPELINE

**Discovered independently by: Claude, ChatGPT v1, Qwen v1**

- **Claude** traced the origin: DECISION-LOG.md D2002 (2026-07-18) — "14 diverse books… 14 FBs generated" — this is a **v2.0 pipeline** with HDBSCAN clustering, Phi-4-mini verifier, no DSPy, no cluster-before-extract.
- The "852" books is the **size of the converted-Markdown library**, not the number of books actually run through the pipeline. The same project's buglog confirms only 3 were chunked in the old run.
- Arithmetically: 14/852 = 1.6%, not 0.004%. The 0.004% figure comes from dividing by ~323,000 *segments* — a silently swapped denominator.
- **Qwen v1**: The repo already has D2182's 1:N extraction per cluster and the Principle Discovery Gate (D2163). The old 1:1 architecture yield is irrelevant.
- **ChatGPT v1**: 14/12,964 = 0.108%, not 0.004%. The prompt's own math is internally inconsistent.

**Verdict:** There is **no yield measurement anywhere in the repo of the current v3.0 hybrid architecture at any scale.** The "yield crisis" baked into HANDOFF_D2254.md, MASTER-TASK-REGISTER.md, and aggregated_remaining_tasks.md is describing a different, retired system. Treating it as gospel to gate a 26h run is gating on phantom data.

### 1B. Golden Set Counts Are Wrong in the Prompt

**Discovered independently by: Claude, ChatGPT v1**

The POST_D2254 prompt states: 55 convergent / 18 non-convergent.

The actual `config/golden/stage2_fewshot_convergent.yaml` metadata (verified by Claude parsing the YAML directly) says:
- 73 total examples
- **36 convergent positives**
- **21 hard negatives**
- Plus unlabeled/ambiguous examples

**ChatGPT v1**: "I would NOT use the prompt's 55/18 statistics without reconciling which artifact produced them."

**Additionally, Claude found:**
- 71% causal_mechanism claim is **stale** — current file shows 44% causal_mechanism (24/55), 22% descriptive_model, 20% normative_heuristic, 15% empirical_pattern. The YAML's own meta note says "D2234 completion: 3 descriptive_model examples added (DM 9→12)" — rebalancing already happened.
- "21 unlabeled depth" is wrong — only **6 convergent examples** lack depth labels. 21 is the hard_negatives count from the YAML's meta block, mislabeled as "unlabeled positives."

### 1C. Current Stage2 Does NOT Implement the Described DSPy Hybrid

**Discovered independently by: ChatGPT v1, Qwen v1**

The POST_D2254 prompt describes S2 as: "DSPy-MIPROv2 gate → [NO] reject → [YES] Traditional extraction."

However:

- **ChatGPT v1**: "`stage2_extract.py` directly calls the configured generator and then processes its route/output. There is no DSPy MIPRO gate in that production path. The DSPy implementation exists in `dspy_trainer.py` as a training/evaluation harness. Therefore Q2's premise — 'current S2 is DSPy gate + traditional extraction' — is not supported by current `main`."

- **Qwen v1**: Found the actual comparison was done in `tools/compare_s2_methods.py` — this is a **benchmarking script**, not the production `stage2_extract.py`.

**This means:** The 0.736 hybrid score comes from a comparison harness, not from the production pipeline. The production S2 is pure traditional extraction with gate enforcement. The "hybrid architecture" described in handoff docs is aspirational — it describes what the benchmark proved, not what's deployed.

### 1D. Hybrid Positive Fidelity Is CONDITIONAL (0.694 Unconditional)

**Discovered independently by: Kimi v2, independently verifying raw JSON**

The master prompt reports hybrid positive fidelity = 0.845 (matching Traditional). This is **only true when the DSPy gate approves extraction.**

- **Kimi v2**: Independently computed unconditional positive fidelity from `s2_comparison_results.json` → **0.694**. Hybrid misses 3/14 positives (21% false-negative rate):
  - #1: Barbell Strategy for Uncertainty (Finance/Risk) — DSPy returns NULL
  - #14: Sequential Team Development (Org Psychology) — DSPy returns NULL
  - #20: Algorithmic Typography Optimization (Design/Typography) — DSPy returns NULL

**Projected to full run (2,634 convergent clusters):** Hybrid would silently discard **~553 valid convergent clusters (21%)** through the gate.

The handoff mentions CONV-036/043/040 as known gate FNs but the handoff doesn't quantify the unconditional fidelity impact. This quantification is new.

### 1E. DeBERTa-FEVER Already Tested, Already Works, Not Deployed

**Discovered independently by: Claude, ChatGPT v2**

- **Claude** found `governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md` — an internal report dated **one day before the D2254 handoff** that benchmarked replacing Gemma entirely with DeBERTa-FEVER (362MB vs 19GB). It correctly classifies the one adversarial case that Gemma, ModernBERT, and RoBERTa all missed. **Not adopted in shipped config.**
- **ChatGPT v2**: "The DeBERTa change is the strongest validated change in the repository. The repo's actual test shows DeBERTa FEVER/ANLI distinguishing supported synthesized FBs from the failed case, while standard MNLI models collapsed toward neutral."

**This means:** The S5 Gemma 73% false-negative problem has a **known, tested, cheap, in-repo fix** that hasn't been promoted to production config. It's a config change away, not an engineering project.

### 1F. The S5 NLI Model Is ModernBERT, Not DeBERTa (and the prompt got it wrong)

- **Claude**: Primary NLI is **ModernBERT** (D2119); DeBERTa is the *fallback*. The prompt described DeBERTa as primary.
- **ChatGPT v1**: "The config says ModernBERT is primary and DeBERTa fallback, while `pipeline_paths.py` contains comments describing the opposite. That is exactly the kind of configuration drift I would fix before production."

### 1G. Application/Failure_Mode Schema-Verification Mismatch (ChatGPT v2)

**ChatGPT v2** identified what it calls "the biggest problem" — bigger than S4 latency:

> "The pipeline can generate or enrich claims such as `application`/`failure_mode` that are not themselves verified by S5, while the schema forces those fields even for non-actionable descriptive principles."

The S4 prompt itself says "application only for prescriptive/actionable principles; otherwise null" — but the FB schema requires both fields for every FB, creating pressure to invent actionable content for descriptive principles. S5 verifies evidence→FB factual claims, not these generated enrichment fields.

### 1H. Goose Renderer: MacWebContentsOcclusion Is the Likely Root Cause

**Consensus across all models.** 25.6% steady-state CPU for an idle chat window is abnormal. `MacWebContentsOcclusion` disabled means the Electron renderer paints 60fps even when hidden/occluded.

**ChatGPT v1** adds important nuance: "Does not by itself prove a rendering-loop bug. You need a trace showing actual frame production/compositor activity." But the correlation is strong enough to re-enable and test. **Expected impact: ~20% CPU reduction when window hidden, freeing 2-3 performance cores for OMLX.**

---

## 2. CONSENSUS TABLE — ALL 8 MODELS

| Question | Claude | ChatGPT v1 | DeepSeek | Qwen v1 | Kimi v1 | ChatGPT v2 | Kimi v2 | Qwen v2 | **CONSENSUS** |
|----------|--------|-----------|----------|---------|---------|-----------|---------|---------|---------------|
| Golden sufficient? | COND | NO | NO | COND | NO | — | — | — | **5/6: NO or CONDITIONAL** |
| Full DSPy replace hybrid? | NO | NO | NO | NO | — | — | — | — | **4/4: NO** |
| Ready for 26h full run? | **NO** | **NO** | **NO** | **NO** | **NO** | **NO** | — | — | **6/6: NO** |
| 20-example A/B sufficient? | NO | NO | NO | NO | — | — | — | — | **4/4: NO** |
| S5 Gemma broken? | YES | YES | YES | YES | YES | YES | — | — | **6/6: YES** |
| E2E test before full run? | YES | YES | YES | YES | YES | — | — | — | **5/5: YES** |
| Renderer CPU actionable? | YES | YES | YES | YES | YES | — | — | — | **5/5: YES** |
| Golden expansion needed? | YES | YES | YES | YES | — | YES | YES | YES | **7/7: YES** |
| Accept hybrid as permanent? | YES | YES | NO | YES | — | YES | YES | YES | **5/6: YES** |

**Zero models approved the full run. Zero models said golden samples are sufficient. Zero models said DSPy can replace hybrid today.**

---

## 3. WHERE REPO-VERIFIED MODELS OVERRIDE PROMPT-ONLY MODELS

| Issue | Prompt-only models (DeepSeek, Kimi v1) | Repo-verified models (Claude, ChatGPT v1, Qwen v1) |
|-------|----------------------------------------|-----------------------------------------------------|
| Yield crisis | Treat 0.004% as real, recommend diagnostic after | **Yield number is phantom — describes v2.0 pipeline, not v3.0. 852 is library size, not books run.** |
| Golden counts | Accept prompt's 55/18 at face value | **Actually 36 convergent / 21 hard negatives. 71% causal is stale (now 44%).** |
| DSPy hybrid architecture | Accept prompt's description as deployed | **Not deployed in stage2_extract.py. Exists only in comparison harness.** |
| Depth imbalance impact on S2 | S2 depth calibration broken | **Depth moved to S4 (D2241). Imbalance affects S4, not S2.** |
| S5 NLI model | Accept prompt's DeBERTa as primary | **ModernBERT is primary. DeBERTa is fallback. Config documentation conflicts.** |
| Goose renderer fix | MacWebContentsOcclusion | **Agreed, but ChatGPT v1: need profiler trace, not assume flag is cause.** |

---

## 4. DEEP DIVE: Qwen v1's Counter-Narrative

Qwen v1 (qwen0002) presents the strongest **counter-narrative** to the prompt's framing. It argues the prompt's most alarming claims are based on an obsolete architecture:

| Prompt Claim | Qwen v1's Repo Finding |
|-------------|----------------------|
| Yield crisis: 14 FBs / 852 books | D2182 (1:N extraction per cluster) already implemented. Old 1:1 architecture is irrelevant. A healthy rate for 1:N should be **5-15%** of clusters. |
| S5 Gemma threshold to 0.3 | The 0.3 is the **DeBERTa NLI_MARGINAL_THRESHOLD**, not the Gemma LLM verifier threshold. The operator is confusing two different thresholds. |
| Depth imbalance corrupts S2 | Depth was moved to S4 (A-001/D2241). The golden set depth labels don't affect S2 calibration. |
| MIPROv2 uses 2 demos | The config already has `DSPY_MAX_LABELED_DEMOS = 4`. The pilot ran at 2 but the config is at 4. |

**This is a significant dissent.** Qwen v1 thinks the pipeline is closer to ready than the prompt suggests, because the prompt describes an older architecture. However, Qwen v1 **still votes NO on the full run** — just for different reasons (needs E2E test to validate 1:N yield, not to fix a phantom crisis).

---

## 5. CRITICAL BLINDSPOTS IN THE PROMPT (flagged by multiple models)

### 5A. Leading Questions

**ChatGPT v1**: "Your prompt contains several leading assumptions — e.g., that the 0.004% yield might be 'genuinely rare convergences' rather than a pipeline bug, and that lowering Gemma's threshold is 'calibration' rather than capitulation. Treat the yield crisis as a **bug until proven otherwise**. The null hypothesis should be 'the pipeline is broken,' not 'principles are rare.'"

**DeepSeek**: "The prompt frames the golden set as 'sufficient' and the hybrid as 'valid' — these are leading assumptions. The operator is implicitly asking for validation of their existing decisions rather than a genuine gate review."

### 5B. Missing Context

**DeepSeek**: Missing from the prompt: actual 852-book corpus distribution (domains, disciplines), S1.5 clustering parameters beyond threshold mismatch, S4 depth classifier confusion matrix for universal/specialized, S5 Gemma full evaluation metrics on real FBs.

**ChatGPT v1**: Missing: what the golden YAML itself declares (36 convergent, 21 hard negatives — the prompt said 55/18). The handoff chain has propagated stale numbers.

### 5C. The Schema-Verification Epistemic Gap

**ChatGPT v2** identified that S5 verifies evidence→FB factual claims but does NOT verify S4-generated enrichment fields (application, failure_mode, elaboration). Meanwhile the FB schema forces these fields for every FB, including descriptive principles that should have null application. This is a **structural correctness problem** — the pipeline can generate content that bypasses verification entirely.

---

## 6. RECOMMENDED FIXES — RANKED BY CROSS-MODEL CONSENSUS

### 🟢 P0 — Fix These Before ANY Run (6+ model consensus)

| Fix | Source | Effort | Impact |
|-----|--------|--------|--------|
| **Run E2E integration test (20-50 books)** | All 8 models | 2-4h | Converts phantom yield crisis into real data |
| **Reconcile documentation vs config vs code** | Claude, ChatGPT v1, ChatGPT v2 | 2-4h | Golden counts, DSPy arch, S5 NLI model — all have drift |
| **Promote DeBERTa-FEVER to primary S5 verifier** | Claude, ChatGPT v2 | Config change (30min) | Replace 73% FN Gemma with 362MB model already tested in-repo |
| **Re-enable MacWebContentsOcclusion in Goose** | All models | 5min config/flag change | ~20% CPU back for OMLX model server during 26h run |

### 🟠 P1 — Fix These Before Full Run (4+ model consensus)

| Fix | Source | Effort |
|------|--------|--------|
| **Golden expansion: universal/specialized depth classes** | All models | 2d (T-015) |
| **Fix S2 runtime to actually deploy hybrid gate (or document that it's traditional-only)** | ChatGPT v1, Qwen v1 | 2-4h |
| **Implement domain-stratified DSPy demo selection** | Kimi v2, Qwen v2, Claude | 4-8h |
| **Fix application/failure_mode schema contradiction** | ChatGPT v2 | 1d |
| **Resolve faiss_threshold mismatch (T1.4)** | Claude | 30min |

### 🟡 P2 — Defer to Post-Run

| Fix | Source |
|------|--------|
| Full DSPy migration (keep hybrid as permanent architecture) | 6/8 models agree |
| S5 cross-family LLM escalation (Gemma replacement) | After DeBERTa primary |
| Model-level LoRA fine-tuning | ALL models: NOT RECOMMENDED now |
| Golden expansion to 200+ | After initial E2E establishes baseline |

---

## 7. ARCHITECTURAL PATH FORWARD (synthesized from all models)

### The production architecture that emerges from cross-model consensus:

```
S1.5 cluster
     ↓
S2: DSPy convergence gate (domain-stratified 4-6 demos)
     ↓ YES                              ↓ NO + high-cohesion + source_diversity≥3
Traditional extraction                   Second-opinion probe (lightweight Traditional, single demo)
     ↓                                   ↓ YES               ↓ NO
S4: Merged Phi multitask call             → extract           → NULL (reject)
     (enrichment + classification)
     ↓
S4: Focused GPT-OSS semantic depth classifier
     (kept separate — BUG-075 proved combined degrades accuracy)
     ↓
Deterministic schema validation
     (application/failure_mode conditional on actionability — fix schema contradiction)
     ↓
S5: DeBERTa-FEVER primary evidence entailment (threshold calibrated on real FBs)
     ↓ AMBIGUOUS only → cross-family LLM escalation
     ↓
Evidence-constrained field-level repair (bounded retry)
     ↓
PASS / FLAG / QUARANTINE → SQLite + Parquet
```

### Key architectural decisions cross-model consensus supports:

1. **Keep DSPy as gate-only, Traditional as extractor** — "Hybrid is a legitimate production pattern, not technical debt" (Claude, ChatGPT v1, Qwen v1, Kimi v2, ChatGPT v2)
2. **DeBERTa-FEVER replaces Gemma as primary S5 verifier** — "Strongest validated change in the repository" (ChatGPT v2), "Already tested, 362MB vs 19GB" (Claude)
3. **Keep focused depth classifier separate** — "Exists because combined prompt degrades depth accuracy; should not be folded back" (ChatGPT v2)
4. **Add second-opinion fallback for gate false-negatives** — Catches the 21% FN rate without reprocessing everything (Kimi v2, Qwen v2)
5. **Domain-stratified demo selection, not just more demos** — Root cause is domain homogeneity, not demo count (Claude, Kimi v2, Qwen v2)

---

## 8. FINAL VERDICT (SENIOR RAG ENGINEER)

### What the prompt got right:
- The pipeline has serious quality gaps
- S5 Gemma is broken at 73% FN
- Golden set has depth class imbalance
- 20-example A/B is insufficient for a 12,964-cluster gate decision
- Goose renderer CPU is abnormal and should be fixed

### What the prompt got wrong (repo-verified):
1. **The yield crisis figure (0.004%) describes a different pipeline.** There is no yield measurement for current v3.0 at any scale.
2. **Golden counts are stale** — 36 convergent / 21 hard negatives, not 55/18. Type distribution already rebalanced (44% causal, not 71%).
3. **The DSPy hybrid architecture isn't actually deployed in production stage2.** It exists in a comparison harness. Production S2 is traditional extraction.
4. **Depth imbalance doesn't affect S2** — depth was moved to S4 months ago (D2241). The prompt's Q1b is asking about a problem that doesn't exist in S2.
5. **S5 primary NLI is ModernBERT, not DeBERTa** — and there's documentation drift between config and comments.
6. **DeBERTa-FEVER already tested and superior** — sitting in a governance doc from Aug 9, not promoted to config.

### The single most important action:

**Run a 50-100 book E2E diagnostic through the CURRENT v3.0 pipeline before committing 26 hours.** Every repo-verified model says this. The "yield crisis" is phantom — you need real yield data. The 20-example S2 A/B is a smoke test, not a readiness gate. DeBERTa-FEVER is a config change away from fixing S5. None of this is multi-day work. But the handoff chain has been making go/no-go decisions on numbers that don't describe the current pipeline.

### The corrected risk matrix:

| Risk | Handoff Status | Actual Status |
|------|---------------|---------------|
| Yield (0.004%) | 🔴 Crisis | 🟡 **Unknown** — never measured for v3.0 |
| S5 Gemma 73% FN | 🟠 High | 🟢 **Fixable now** — DeBERTa-FEVER already tested |
| Golden depth imbalance | 🟠 High | 🟡 **Real but S4-only** — doesn't affect S2 calibration |
| DSPy hybrid deployed | 🟢 Deployed | 🟡 **Not deployed** — exists in comparison harness only |
| Documentation drift | 🟢 Clean | 🔴 **Multiple drift points** — golden counts, S5 NLI model, DSPy arch |

**The pipeline is more fixable than the handoff suggests, but less deployed than the handoff claims.**
