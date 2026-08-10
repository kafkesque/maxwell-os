# Master Roundtable Evaluation Prompt — v7.0
## DSPy vs Traditional S2 Extraction — Quality & Speed Audit

**Authority:** D2238/D2239 — S2 comparison results + MIPROv2 validation
**Audience:** S-tier senior RAG engineers (LLM evaluators)
**Purpose:** Evaluate whether DSPy-optimized S2 extraction surpasses traditional few-shot S2, and whether Maxwell OS is ready to switch extraction methods.
**Date:** 2026-08-10

---

## ⚠️ v7.0 CHANGELOG — What's New Since v6.1

| Change | Detail |
|--------|--------|
| **D2237: DirectOMLXLM** | Custom dspy.LM subclass that bypasses litellm entirely. Works for ALL optimizers (ChainOfThought, BootstrapFewShot, MIPROv2). |
| **D2238: 3-way comparison** | Traditional (few-shot) vs DSPy CoT vs DSPy BootstrapFewShot on 3 held-out test examples. |
| **D2239: MIPROv2 validated** | MIPROv2 confirmed working with DirectOMLXLM. Full training run in progress. |
| **Depth metric fix** | Depth weight 10%→15% with explicit universal-bias penalty. |
| **Gemma-4-31B-8bit** | Downloading (3/7 shards, 11GB of 16GB). |

---

## THE COMPARISON: Traditional vs DSPy — Who Wins?

### Setup
- **Model:** Qwen3-Coder-30B-A3B-MLX-4bit (OMLX, port 11435)
- **Hardware:** Apple M1 Max, 64 GB unified memory
- **Test set:** 3 held-out positive examples (CONV-001, CONV-002, CONV-003)
- **Traditional:** SYSTEM_PROMPT + 3 positive + 1 negative few-shot examples (~6K tokens)
- **DSPy CoT:** ConvergentExtraction Signature, no few-shot examples (~1K tokens)
- **DSPy BS:** BootstrapFewShot with 3 training examples, metric_threshold=0.5

### Results (Ground Truth — From Actual Repo Execution)

```
╔══════════════════════════════════════════════════════════════════╗
║  METHOD               QUALITY   LATENCY   TYPE ACC   DEPTH ACC  ║
╠══════════════════════════════════════════════════════════════════╣
║  Traditional (fewshot)  1.00      45.0s      3/3 ✅      0/3    ║
║  DSPy ChainOfThought    0.82      45.6s      2/3         0/3    ║
║  DSPy BootstrapFewShot  0.87 ✅   50.7s      3/3 ✅      0/3    ║
╚══════════════════════════════════════════════════════════════════╝
```

### Per-Example Breakdown

| Example | Traditional | DSPy CoT | DSPy BS |
|---------|------------|----------|---------|
| CONV-001 (Asymmetric Dominance) | 1.00 (50s) | 0.77 (49s) | 0.87 (57s) |
| CONV-002 (Implementation Intentions) | 1.00 (43s) | 0.83 (46s) | 0.82 (49s) |
| CONV-003 (Metaphor Inverted-U) | 1.00 (43s) | 0.87 (42s) | 0.92 (47s) |
| **Average** | **1.00** | **0.82** | **0.87** |

---

## EVALUATION QUESTIONS

### QUESTION 1: Is Traditional's 1.00 Score Legitimate? [P0]

Traditional S2 scores a perfect 1.00 on ALL three test examples. But the few-shot examples come from the SAME golden set (`stage2_fewshot_convergent.yaml`) as the held-out test distribution.

a) Is this data leakage? The few-shot sampler uses `golden_positive: 3, golden_negative: 1` from the same YAML file that defines the test examples. The test set and few-shot set both draw from the same 73-example pool.

b) If the traditional prompt was given UNSEEN book segments from authors NOT in the golden set, would it still score 1.00?

c) Does the 1.00 score represent genuine extraction capability or memorization via prompt priming?

d) Should the few-shot examples be drawn from a DISJOINT set (authors not in the test set) for a fair comparison?

### QUESTION 2: Does DSPy's +6% Improvement Prove the Approach? [P0]

DSPy BootstrapFewShot improved from 0.82 (CoT, no training) to 0.87 (BS, 3 examples) — a +6% gain.

a) Is this statistically significant with only 3 test examples? What sample size would give confidence in the improvement?

b) DSPy BS matched Traditional on type accuracy (3/3 vs 3/3) — did the optimization learn type classification, or did it memorize from the 3 training examples?

c) If DSPy were trained on ALL 51 training examples instead of 3, what quality would you expect? Is the +6% gain from 3 examples predictive of gains from 51?

d) MIPROv2 is now running (instruction optimization). What additional improvement would you expect from optimized instructions vs BootstrapFewShot's demo selection?

### QUESTION 3: The Depth Accuracy Crisis [P1]

**0% depth accuracy across ALL methods.** The model defaults to `universal` regardless of input — even when the golden label is `domain`.

a) Is this a model capability issue (Qwen3-Coder-30B cannot learn depth classification) or a prompt/signal issue (the training signal doesn't teach depth effectively)?

b) The extraction_metric has been updated: depth weight 10%→15% with no credit for `universal` when gold is `domain`/`specialized`. Will this penalty be sufficient to train depth awareness?

c) Should depth be moved OUT of S2 entirely and kept as a Stage 4 classification task (as the original pipeline design intended)? The SYSTEM_PROMPT says "Classification (depth, domains, discipline) is Stage 4's job" — yet the DSPy Signature includes depth as an output field.

d) If depth stays in S2, how many training examples with correct depth labels are needed to break the universal default bias?

### QUESTION 4: Speed — Can DSPy Beat 45 Seconds? [P1]

Traditional S2 takes ~45s per extraction (6K tokens: ~35s KV cache + ~12s generation).

a) DSPy CoT takes the same ~45s but with a shorter prompt (~1K tokens). Why isn't it faster? Is the ChainOfThought reasoning adding tokens that offset the prompt savings?

b) BootstrapFewShot is SLOWER (51s) because it adds bootstrapped demos to the prompt. Is the quality gain (+6%) worth the speed cost (+13%)?

c) MIPROv2 can optimize INSTRUCTIONS (not just demo selection). A MIPROv2-optimized prompt could be 1-2K tokens instead of 6K. What speed improvement would you expect from a 70% token reduction?

d) Could Gemma-4-31B-8bit be FASTER than Qwen3-Coder-30B on M1 Max? Different model architectures have different KV cache efficiencies.

### QUESTION 5: Is the Golden Set Ready for Full DSPy Training? [P0]

The golden set is v4.4: 73 examples, 75 FBs.

a) With 51 training examples, 11 dev, 13 test — is this sufficient for MIPROv2 optimization?

b) Author leakage is 9% in the stratified split. Is this acceptable for DSPy training, or does it risk overfitting to specific authors?

c) The negative:positive ratio is 21:54 (0.39:1). BootstrapFewShot failed on ALL negative examples during training. Do we need more negatives for the optimizer to learn rejection?

d) What's the minimum viable golden set size for DSPy to consistently outperform traditional few-shot?

### QUESTION 6: Architecture Decision — Stay Traditional or Switch to DSPy? [P0]

Given the current evidence:

a) Should Maxwell OS switch S2 extraction from traditional few-shot to DSPy-optimized?

b) If YES: what quality bar must DSPy clear before the switch? (e.g., "DSPy must score ≥0.90 on 10+ held-out examples")

c) If NO: what would change your mind? What evidence is missing?

d) Hybrid approach: use DSPy-optimized instructions but keep traditional few-shot examples as a safety net. Viable?

### QUESTION 7: The Gemma-4-31B Factor [P1]

Gemma-4-31B-it-MLX-8bit is downloading (Google family, 31.6B params, 16GB).

a) Gemma is a different model family from Qwen (Alibaba). R5 requires cross-family verification. If Gemma were used for S2 extraction, what model would verify (S5)?

b) Gemma-4-31B is 31.6B vs Qwen3-Coder's 30B (MoE, effectively ~3B active). Is Gemma likely to produce better or worse extraction quality?

c) Should the DSPy training be repeated on Gemma-4-31B after it finishes downloading? Or is Qwen3-Coder the right long-term S2 model?

### QUESTION 8: Regression Testing Strategy [P2]

a) The comparison framework (`tools/compare_s2_methods.py`) exists. What's the minimum regression test suite before each pipeline run?

b) How many held-out examples are needed for a statistically meaningful comparison? (Currently using 3 — is that enough?)

c) Should regression testing be automated as a pre-commit hook or CI step?

---

## VERDICT FORMAT

```yaml
auditor: "model_name"
date: "2026-08-10"
overall_verdict: "SWITCH_TO_DSPy|STAY_TRADITIONAL|NEED_MORE_DATA"

data_leakage_assessment:
  traditional_1_00_is_data_leakage: true/false
  recommended_fix: "description"
  fair_comparison_method: "description"

dspy_improvement_significance:
  plus_6_percent_real: true/false
  projected_full_training_quality: 0.0
  min_examples_for_significance: 0

depth_crisis:
  root_cause: "model_capability|signal_issue|architecture_misfit"
  recommended_fix: "move_to_S4|improve_signal|accept_limitation"
  examples_needed_for_depth_learning: 0

speed_assessment:
  can_dspy_beat_45s: true/false
  projected_mipro_speed: 0.0
  gemma_speed_advantage: "faster|slower|unknown"

golden_set_readiness:
  sufficient_for_full_training: true/false
  min_viable_size: 0
  negative_count_concern: true/false

architecture_recommendation:
  switch_now: true/false
  quality_bar: 0.0
  hybrid_approach_viable: true/false

critical_blockers: []
confidence: 0.0
```

---

## FILES FOR REFERENCE

1. `pipeline/dspy_trainer.py` — DSPy harness (720 lines): ConvergentExtraction Signature, DirectOMLXLM backend, extraction_metric, MIPROv2/BootstrapFewShot optimizers
2. `pipeline/stage2_extract.py` — Traditional S2: SYSTEM_PROMPT, format_golden_fewshot()
3. `tools/compare_s2_methods.py` — Comparison framework (327 lines): runs both methods on same test set
4. `config/golden/stage2_fewshot_convergent.yaml` — Golden set v4.4 (73 examples, 75 FBs)
5. `governance/s2_comparison_results.json` — Raw comparison data

---

## IMPORTANT NOTES

1. **Traditional's 1.00 is the elephant in the room.** If it's data leakage (few-shot = same distribution as test), then DSPy's 0.87 on true generalization might already be superior. If it's genuine (the traditional prompt is just that good), then DSPy has a long way to go.

2. **Depth is broken everywhere.** 0% accuracy across all methods. This is not a DSPy problem — it's a fundamental issue with the model's depth ontology understanding. Fix this before comparing quality metrics.

3. **Speed parity is real.** All methods take ~45-51s on M1 Max. The bottleneck is OMLX generation, not prompt construction. MIPROv2's instruction optimization is the only path to meaningful speed improvement.

4. **The golden set is 73 examples.** DSPy with 51 training examples should show significant gains. The +6% from 3 examples is promising but needs validation at scale.

5. **Gemma-4-31B is the wild card.** A different model family (Google) might have different depth understanding, different speed characteristics, and different extraction quality. Evaluate AFTER it downloads.
