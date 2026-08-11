# D2254 Cross-Examination v2: 3 New LLM Responses vs. Actual Maxwell OS Source Files
> **Synthesized:** 2026-08-11 11:30 | **Responses:** Kimi v2, Qwen v3, ChatGPT v3  
> **Method:** Every factual claim checked against actual repo files on disk. No assumption. No deference.  
> **Standard:** Senior RAG + LLM engineer, evidence-only verdict.

---

## 0. METHODOLOGICAL GRADING (v2)

| Respondent | Repo Access | Files Actually Read | Accuracy Grade |
|------------|------------|---------------------|----------------|
| **Qwen v3** (qwen0003) | ✅ Yes | stage2_extract.py, stage5_verify.py, pipeline_config.yaml, golden YAML | **C+** — 2 critical factual errors (CONV-039 status, golden version) |
| **Kimi v2** (kimii004) | ⚠️ Partial — YAML truncated at CONV-030 | stage2_fewshot_convergent.yaml (partial), trimmed_12, GOLDEN-REVIEW.md | **C** — 4 claims contradicted by source files |
| **ChatGPT v3** (chatgpt004) | ✅ Yes | stage2_fewshot_convergent.yaml, GOLDEN-REVIEW.md, evals/golden_cases.json, evals/promptfooconfig.yaml, dspy_trainer.py | **A-** — 1 minor error, otherwise source-verified |

### The Pattern:
**The two models with partial/truncated repo access (Kimi v2, Qwen v3) made the most material errors.** Their errors are not random — they systematically misinterpreted the golden YAML structure. ChatGPT v3, despite being the longest response, was the most accurate because it read MULTIPLE artifacts (golden YAML, GOLDEN-REVIEW.md, evals/, pipeline files) and cross-referenced them.

---

## 1. CLAIM-BY-CLAIM VERIFICATION AGAINST SOURCE FILES

### 1A. THE CRITICAL ERROR: CONV-039 IS ALREADY MARKED FALSE

**Qwen v3 claimed:**
> "CONV-039: 'Incentive Frame Reversal' (The Planning Fallacy Error). The golden set claims that the Day-Care Fine and the Planning Fallacy converge...This is factually incoherent...You are teaching the LLM that if it clusters two 'behavioral economics' concepts, it should hallucinate a fake 'incentive' link between them."

**Source file verification:**
```yaml
# config/golden/stage2_fewshot_convergent.yaml
CONV-039:
  is_convergent: False      # ← ALREADY MARKED AS NON-CONVERGENT
  should_extract: True       # Still extracted as a negative example
```

**Verdict: ❌ FALSE.** CONV-039 is **already a negative calibration example** showing that Day-Care Fine and Planning Fallacy do NOT converge. The reviewer saw the CONV- prefix and assumed it was a positive example. The YAML explicitly teaches the model to REJECT this convergence, exactly as the reviewer recommends. The reviewer's entire analysis of CONV-039 as a "critical calibration failure" is based on misreading the `is_convergent` flag.

### 1B. CONV-032: Taleb + Wolfram — NOT CLEAR-CUT ERROR

**Qwen v3 claimed:**
> "CONV-032: 'System Fragility Taxonomy' (The Wolfram Category Error). Merges Taleb's Fragile/Robust/Antifragile with Wolfram's Class 1–4 Cellular Automata...This is a fundamental category error."

**Source file verification:**
```yaml
CONV-032:
  is_convergent: True
  extraction_type: descriptive_model    # ← explicitly NOT causal_mechanism
  rationale: "DESCRIPTIVE MODEL — classification taxonomy of system responses. Taleb's 
    fragile/robust/antifragile and Wolfram's four behavioral classes both describe 
    CLASSIFICATION SCHEMES for system behavior. They converge on the insight that systems 
    can be meaningfully categorized by their response to perturbation. This is NOT a causal 
    mechanism — it's a TAXONOMY..."
```

**Verdict: ⚠️ DEBATABLE, NOT CLEAR-CUT ERROR.** The golden set explicitly classifies this as a descriptive_model (taxonomy), not a causal_mechanism. The rationale anticipates the objection. Whether Taleb's and Wolfram's taxonomies "converge" is a philosophical question, not a factual error. The extraction is self-aware about what it's doing. Qwen v3's framing as a "category error" is a design opinion, not a bug.

### 1C. GOLDEN VERSION: v4.4, NOT v4.2

**Qwen v3 claimed:**
> "The active config/golden/stage2_fewshot_convergent.yaml in the repo is v4.2 (60 examples)."

**Source file verification:**
```yaml
# Line 2 of config/golden/stage2_fewshot_convergent.yaml
version: '4.4'
```
Total examples: 73 (verified by Python parse).

**Verdict: ❌ FALSE.** The active golden YAML is v4.4 with 73 examples. Qwen v3 may have been looking at the trimmed_12.yaml or a cached version. The v4.2 claim is wrong.

### 1D. CONV-001: SYSTEM 1/2 IS FROM THE SOURCE BOOK

**Kimi v2 claimed:**
> "The source segments mention 'dominance relationship makes choices easier' and 'preference shifts.' They do NOT mention 'System 1 (intuitive) reasoning' or 'System 2 (deliberative) reasoning.' The mechanism injects Kahneman's theoretical framework that is not present in the provided cluster segments."

**Source file verification:**
One of the three source books for CONV-001 is **Thinking, Fast and Slow — Daniel Kahneman**. This is literally the book that introduced System 1/System 2 to behavioral economics. The mechanism field uses Kahneman's own theoretical framework from the source book. The segment text shown to the LLM is truncated (the YAML stores compressed segments), but the source material IS Kahneman.

**Verdict: ❌ FALSE.** The mechanism references System 1/2 from the source book's author's own framework. This is not "injecting" foreign theory — it's using the explanatory framework of one of the converged sources. The reviewer didn't check the source_books field.

### 1E. NEG-HARD-012: IN GOLDEN-REVIEW.md, NOT ACTIVE YAML

**Kimi v2 claimed:**
> "I found a calibration time bomb in the repo: NEG-HARD-012 (plausible-principle-with-noise test) has the following rationale: 'This is a deliberate false-negative calibration. In production, a passage with this signal-to-noise ratio SHOULD be extracted...'"

**Source file verification:**
- `config/golden/stage2_fewshot_convergent.yaml`: **NO NEG-HARD examples exist.** Uses CONV-/NEG-CONV-/NEG- prefixes.
- `config/golden/GOLDEN-REVIEW.md` (v2.0, 75 examples, LEA-/STR-/DES-/PER-/MGT- prefixes): **28 references to NEG-HARD.** The quoted text EXISTS in GOLDEN-REVIEW.md.

**Verdict: ⚠️ PARTIALLY TRUE, WRONG TARGET.** The NEG-HARD-012 content exists in GOLDEN-REVIEW.md (v2.0), which is a historical/alternative golden set with a completely different ID scheme. It does NOT exist in the active v4.4 YAML used by S2. The reviewer conflated two different golden files. However, the CONTENT of the concern is valid — the older golden set does contain a deliberate false-negative calibration that trains conservatism. The question is: is the v2.0 set still used anywhere?

### 1F. SCHEMA DRIFT: EXTRA FIELDS NOT IN ACTIVE YAML

**Kimi v2 claimed:**
> "The v4.4 examples (e.g., CONV-012, CONV-017) contain fields not mentioned in your prompt schema (prerequisite_fbs, contradicts_fbs, related_fbs, procedural_skill, failure_mode, jargon, keywords, application)."

**Source file verification via Python parse:**
Searched all 73 examples in the active YAML for `prerequisite_fbs`, `contradicts_fbs`, `related_fbs`, `procedural_skill`, `failure_mode`, `jargon`, `keywords`, `application` in the `expected_fb` dict. **Zero matches across all examples.** These fields do not exist in the active v4.4 YAML.

**Verdict: ❌ FALSE.** The reviewer may have been looking at GOLDEN-REVIEW.md (which has a different, richer schema) or the truncated portion of the YAML was misinterpreted. The active S2 golden YAML is clean — it only contains the fields the S2 prompt expects.

### 1G. AUTHOR COUNTS INFLATED

**Kimi v2 claimed:**
> "James Clear: 4+ examples, Brené Brown: 3+ examples, Steven Pressfield: 3 examples, Donis A. Dondis: 5+ examples, George Bokhua: 4+ examples, Peter Drucker: 3 examples"

**Source file verification (active YAML, author frequency):**
```
Eric Ries: 4
Donella Meadows: 4
Dan Ariely: 3
Daniel Kahneman: 3
James Clear: 3       ← not 4+
Charles Duhigg: 3
Chip & Dan Heath: 3
Jim Collins: 3
Alan Cooper: 3
Malcolm Gladwell: 3
```
**Brené Brown, Steven Pressfield, Donis A. Dondis, George Bokhua, Peter Drucker: ZERO in active YAML.**

**Verdict: ❌ FALSE.** These author counts come from GOLDEN-REVIEW.md (v2.0, LEA/STR/DES/PER/MGT prefixes), not the active v4.4 YAML. The reviewer conflated the two golden files. The active YAML has a completely different author distribution.

### 1H. S5 NLI: CODE ALREADY PROMOTED DeBERTa FEVER PRIMARY

**All models + prompt claimed ModernBERT is primary DeBERTa is fallback.**

**Source file verification:**
```python
# pipeline/pipeline_paths.py lines 163-168
# D2216 (2026-08-09): DeBERTa FEVER primary. ModernBERT is fallback.
# DeBERTa FEVER: 5.8× more discriminative than ModernBERT on convergent FBs.
S5_NLI_MODEL = _CFG.get("stage5", {}).get("nli_model", 
    "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")  # D2216
S5_NLI_MODEL_FALLBACK = _CFG.get("stage5", {}).get("nli_model_fallback", 
    "tasksource/ModernBERT-base-nli")  # D2216
```

BUT `config/pipeline_config.yaml` line 172:
```yaml
nli_model: tasksource/ModernBERT-base-nli
```

AND `stage5_verify.py` docstring line 3:
```
stage5_verify.py — Verify FBs via ModernBERT NLI pre-filter + Gemma-4-E4B deep check.
```

**Verdict: ⚠️ CODE ALREADY FIXED, CONFIG + DOCS STALE.** The code (`pipeline_paths.py`) already promotes DeBERTa FEVER as primary (D2216, Aug 9 — one day before D2254 handoff). The config YAML still says ModernBERT. The docstring is stale. This means Claude's finding from the previous batch was correct — the fix exists in code but the config hasn't been updated to match. This is a config drift bug, not a missing feature.

### 1I. GENERATOR MODEL DRIFT

**ChatGPT v3 flagged:**
> "stage2_extract.py's module documentation now says Qwen3.6-35B. That is configuration/documentation drift."

**Source file verification:**
```
# pipeline/stage2_extract.py line 28:
Generator: Qwen3.6-35B-A3B-4bit (OMLX or MLX)

# config/pipeline_config.yaml line 53:
generator:
    model: Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
```

**Verdict: ✅ CONFIRMED.** Docstring says Qwen3.6-35B; config says Qwen3-Coder-30B. These may or may not be the same model under different naming conventions. Either way, it's documentation drift.

### 1J. GOLDEN-REVIEW.md: 0/225 CHECKS COMPLETED

**ChatGPT v3 claimed:**
> "GOLDEN-REVIEW.md has 0/225 review checks completed, 74 placeholder feedback fields, and final sign-off unchecked."

**Source file verification:**
```bash
$ grep -c '\[ \]' config/golden/GOLDEN-REVIEW.md
225
$ grep -c '\[x\]' config/golden/GOLDEN-REVIEW.md
0
```

**Verdict: ✅ CONFIRMED.** 225 unchecked boxes, 0 checked. This is the v2.0 golden set with LEA/STR/DES/PER/MGT ID prefixes — NOT the active v4.4 YAML. The v2.0 set was never calibrated.

### 1K. D2234 REBALANCING CONFIRMED

**ChatGPT v3 claimed golden distribution was rebalanced in D2234.**

**Source file verification:**
```yaml
# YAML meta
notes: 'D2234 completion: 3 descriptive_model examples added (DM 9→12)'
```
Actual type distribution (verified from is_convergent=True examples):
```
causal_mechanism: 24 (44%)  ← not 71% as prompt claimed
descriptive_model: 12 (22%)
normative_heuristic: 11 (20%)
empirical_pattern: 8 (15%)
```

**Verdict: ✅ CONFIRMED.** The prompt's 71% causal_mechanism figure is stale. Current YAML is 44% causal with better balance. D2234 added examples.

---

## 2. UNVERIFIED BUT PLAUSIBLE CLAIMS

These claims require human judgment or access to runtime state I can't reproduce:

| Claim | Source | Assessment |
|-------|--------|------------|
| faiss_threshold 0.75 is "astronomically high" and root cause of yield | Qwen v3 | **⚠️ Debatable.** 0.75 cosine for 1024-dim bge-m3 embeddings on 300-word chunks is tight but not unreasonable. The yield crisis itself is a phantom number (proven in v1 cross-examination). |
| 14 label errors in evals/golden_cases.json | ChatGPT v3 | **⚠️ Plausible, requires domain expertise to adjudicate.** The line-by-line audit shows systematic cross-domain/domain confusion. |
| "Universal" golden claims are epistemically dangerous | ChatGPT v3 | **✅ Reasonable concern.** Claims with "all systems," "any system," "impossible" as golden examples risk teaching the model that lexical universalism = semantic universality. |
| DSPy gate should be separated into hard gate metric | ALL 3 | **✅ Strong engineering consensus.** |
| 20-example A/B insufficient for 12,964 clusters | ALL 3 | **✅ Unanimous, and statistically correct.** |

---

## 3. WHAT EACH MODEL GOT RIGHT (despite errors)

### Qwen v3 STRENGTHS:
- ✅ Correctly identified that `format_golden_fewshot()` strips depth (verified)
- ✅ Correctly identified author leakage in dspy_trainer.py (verified)
- ✅ CONV-030 (same-author echo) is a valid negative example
- ✅ CONV-037 (1:N split) is valid calibration
- Raised important questions about CONV-032 and CONV-033 synthesis quality (even if debatable)

### Kimi v2 STRENGTHS:
- ✅ Correctly identified the multiple golden files problem
- ✅ Correctly identified the META discrepancy (36 convergent positives vs 55 is_convergent)
- ✅ The NEG-HARD-012 concern DOES exist in GOLDEN-REVIEW.md (just wrong file)
- ✅ Identified author concentration risk (right concern, wrong counts)
- ✅ Correctly flagged the "calibration time bomb" concept (conservatism training)
- ✅ Correctly identified that hybrid unconditional fidelity is 0.694, not 0.845

### ChatGPT v3 STRENGTHS:
- ✅ **Most accurate overall.** Read multiple artifacts and cross-referenced.
- ✅ 51-case line-by-line depth golden audit (evals/golden_cases.json)
- ✅ Identified D2103's explicit call for convergent multi-passage examples
- ✅ Identified generator model drift (Qwen3.6 vs Qwen3-Coder)
- ✅ Identified D2234 distribution rebalancing
- ✅ Correctly distinguished evals/golden_cases.json (depth) from GOLDEN-REVIEW.md (extraction)
- ✅ Correctly identified the S5 config/code drift
- ✅ Called out the prompt's stale premises explicitly

---

## 4. THE FUNDAMENTAL ISSUE: TWO GOLDEN SETS, NEITHER FULLY CALIBRATED

The most important finding that spans all three reviews:

| Golden Set | Version | Examples | IDs | Status | Used By |
|-----------|---------|----------|-----|--------|---------|
| `stage2_fewshot_convergent.yaml` | v4.4 | 73 (55 conv) | CONV-xxx, NEG-xxx, NEG-CONV-xxx | ✅ Active, meta says "calibrated" | S2 few-shot injection |
| `GOLDEN-REVIEW.md` | v2.0 | 75 | LEA-xxx, STR-xxx, DES-xxx, PER-xxx, MGT-xxx | 🔴 0/225 checks, never calibrated | Unclear — possibly historical |
| `stage2_fewshot_trimmed_12.yaml` | v4.1 | 12 | (subset of v4.4) | Legacy | Unknown |
| `evals/golden_cases.json` | — | 52 | (depth classification) | 🟡 14+ likely label errors | S4 depth eval (promptfoo) |

**NONE of these are independently validated.** The v4.4 YAML is the most mature but has never been cross-checked by a second human. The v2.0 set was explicitly abandoned uncalibrated. The depth golden cases have documented label errors. The trimmed set is a subset with unknown authority.

### The Meta vs is_convergent Discrepancy:

The YAML meta block says `convergent_positives: 36` but the actual `is_convergent=True` count is 55. This means:
- The meta is counting only a subset (possibly the EXPLICITLY VERIFIED convergent positives from the review process)
- OR the meta is stale and wasn't updated when examples were added
- 55 - 36 = 19 examples marked convergent in the field but not counted in the meta

**This is itself a data integrity issue.** The meta and the actual data disagree.

---

## 5. ULTIMATE TAKE (Senior RAG + LLM Engineer Verdict)

### WHAT THE LLMs GOT RIGHT:
1. **ALL 3 agree: DO NOT RUN the 26-hour full run.** This is correct — the pipeline needs an E2E diagnostic first.
2. **ALL 3 agree: Golden set needs expansion** (especially universal/specialized depth, balanced extraction types).
3. **ALL 3 agree: DSPy should remain gate-only, not full extraction.**
4. **ALL 3 agree: S5 verification needs fixing** (though the fix — DeBERTa FEVER — is already in code, just not in config).
5. **ALL 3 agree: Hybrid architecture is the correct production pattern.**

### WHAT THE LLMs GOT WRONG:
1. **Qwen v3**: CONV-039 is already marked `is_convergent: False` — the "critical calibration failure" claim is based on misreading the flag. Golden version is v4.4, not v4.2.
2. **Kimi v2**: Conflated GOLDEN-REVIEW.md (v2.0) with the active YAML (v4.4). Author counts are from the wrong file. Schema drift fields don't exist in active YAML. NEG-HARD-012 is in the wrong golden set.
3. **ChatGPT v3**: The most accurate, but the "0/225 checks" applies to GOLDEN-REVIEW.md v2.0, not the active v4.4 YAML. The v4.4 YAML was created as a REPLACEMENT for the uncalibrated v2.0 set, so the 0/225 finding, while technically true, doesn't invalidate the active golden set.

### THE SINGLE MOST IMPORTANT FINDING:
**The two golden sets (v2.0 GOLDEN-REVIEW.md and v4.4 YAML) have completely different ID schemes, author distributions, and calibration status.** Every model that read only one of them made errors about the other. The project has a golden set fragmentation problem — it's unclear whether GOLDEN-REVIEW.md is historical or still authoritative. If both are considered "golden," they contradict each other on author distribution, example selection, and calibration philosophy.

### WHAT I WOULD DO (in order):

1. **Deprecate GOLDEN-REVIEW.md** — Archive it. The v4.4 YAML is the active golden set. The v2.0 set with 0/225 checks adds confusion, not calibration.

2. **Fix the meta vs is_convergent discrepancy** — Either update the meta to reflect actual counts (55 convergent) or explain what "convergent_positives: 36" means vs 55 is_convergent=True examples.

3. **Promote DeBERTa FEVER in pipeline_config.yaml** — The code already does it (pipeline_paths.py D2216). The config YAML still says ModernBERT. This is a 1-line config fix.

4. **Fix generator model drift** — stage2_extract.py docstring says Qwen3.6-35B; config says Qwen3-Coder-30B. Reconcile to one canonical name.

5. **Run 50-100 book E2E diagnostic** — The single highest-leverage action. Converts phantom yield crisis into real data.

6. **Audit evals/golden_cases.json labels** — ChatGPT v3's line-by-line audit found 14 probable label errors. Before using this for S4 depth calibration, validate the labels.

7. **Add 10+ universal and 10+ specialized depth examples** — Both to the golden YAML AND to evals/golden_cases.json. The 1-example-per-class situation is uncalibratable.

### BOTTOM LINE:
The pipeline is in better shape than the handoff suggests (phantom yield crisis, already-rebalanced golden set, DeBERTa fix in code), but worse shape than the v4.4 golden YAML's "calibrated" label implies (no independent verification, meta/data discrepancy, depth class imbalance). **The 26-hour run should wait for an E2E diagnostic.** The DSPy hybrid architecture is correct. The goose renderer CPU is a real but secondary concern. The golden set fragmentation (v2.0 vs v4.4) should be resolved by archiving v2.0.
