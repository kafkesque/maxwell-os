# Maxwell OS v4.1 — Golden Set Fine-Tuning Readiness Evaluation
## Master Roundtable Prompt v4

**Date:** 2026-08-09
**Evaluator Role:** S-tier Senior RAG Engineer with DSPy fine-tuning expertise
**Context:** Maxwell OS has a 50-example golden set (27 positives + 23 negatives) for training the S2 convergent extraction model. We need to determine if this set is production-ready for DSPy fine-tuning.

---

## INSTRUCTIONS

Evaluate whether the attached 50-example golden set (`stage2_fewshot_convergent.yaml`, v4.1) is ready for DSPy fine-tuning of the S2 extraction model (Qwen3-Coder-30B-A3B-MLX-4bit, temp=0.0).

### Attached Files
1. `config/golden/stage2_fewshot_convergent.yaml` — Full 50-example golden set (27 pos + 23 neg)
2. `config/golden/stage2_fewshot_trimmed_12.yaml` — 12-example trimmed few-shot for comparison
3. `pipeline/stage4_merge.py` — S4 merge with D2220 depth classifier fix
4. `pipeline/stage5_verify.py` — S5 verify with D2220 mechanism pre-filter
5. `pipeline/stage4_merged_call.py` — NEW: Merged CRIBS+Classify single-call (D2224)

### Known Changes Since v4.0

- ALL 27 positives now have `depth` and `discipline` fields populated (fixed bimodal training signal)
- NEG-007 replaced: original segments (Senge/McChrystal/Surowiecki — distinct mechanisms) → genuine citation echo (Covey/Carnegie/Sinek — "communication is key" with zero mechanism)
- NEG-010 replaced: original segments (Morgan/Neumeier/Hanlon — genuine brand mechanisms) → genuine platitude (Collins/Sinek/Coyle — "culture/alignment drives success" with zero mechanism)
- NEG-008 fixed: removed Saussure from source_books (was listed but had no segment)
- CONV-022: depth set to `domain` (was missing), extraction_type set to `descriptive_model`
- 18 new examples added covering: hard science (physics, biology), medicine, law, software engineering, normative heuristics, empirical patterns, engineering tradeoffs, historical observations, correlation≠causation, mechanism disagreement, domain best practices, non-falsifiable claims, speculation vs principle, same-author echo
- 4 extraction types now represented: causal_mechanism, descriptive_model, normative_heuristic, empirical_pattern
- 3 depth levels represented: universal, cross-domain, domain (note: no genuine `specialized` positive after CONV-022 reclassified to `domain`)

### Key Questions

**A. STRUCTURAL READINESS**

1. Are all 50 examples internally consistent? Check:
   - Every positive has depth, discipline, extraction_type populated
   - Every positive's mechanism is non-tautological (test: does "because" explain causal chain or restate definition?)
   - Every negative's segments genuinely exhibit the claimed failure mode (not a different failure mode)
   - Source/segment counts match (no missing segments for listed sources)

2. Is the 12-example trimmed set (`stage2_fewshot_trimmed_12.yaml`) a valid subset? Does it preserve coverage of all extraction types, depths, and failure modes? Which 12 would YOU select?

3. Any bimodal training signals remaining? (fields present in some examples but not others)

**B. DSPy FINE-TUNING READINESS**

4. Minimum viable examples for DSPy: Some say 50, some say 100, some say 200. Given that this is structured JSON extraction with extensive negative examples (23 negatives out of 50 = 46% negative ratio), is 50 sufficient?

5. Domain coverage: We have behavioral economics, psychology, physics, biology, medicine, law, software engineering, network science, statistics, design, marketing, AI. What critical domains are still missing that would cause systematic extraction failures?

6. Extraction type balance: 23 causal_mechanism, 1 descriptive_model, 1 normative_heuristic, 1 empirical_pattern. Is this skewed toward causal mechanisms in a way that would bias the model against non-causal principles?

7. Negative-to-positive ratio: 23 negatives, 27 positives = 0.85:1. Is this optimal? Too many negatives can make a model overly conservative; too few can make it extract platitudes.

**C. HARDWARE REALITY CHECK**

8. Qwen3-Coder-8B does NOT exist. The smallest Coder variant is the 30B-A3B MoE (already loaded). Qwen3-Coder-Next has 512 experts and may be larger, not smaller. For a smaller/faster S2 model, viable alternatives are Phi-4-mini (3.8B, Microsoft family) or Gemma-4-E4B (4B, Google family) — neither is Coder-tuned. If we fine-tune Phi-4-mini on the golden set for S2 extraction, does the smaller model capacity risk quality degradation on complex multi-source convergence?

9. Is the merged S4 CRIBS+Classify call (`stage4_merged_call.py`) architecturally sound? Does single-call JSON output risk field confusion? Does Phi-4-mini have sufficient capacity for 10-field structured output?

**D. VERIFICATION — CHALLENGE EVERYTHING**

10. Find at least ONE example in the 50-example set that is incorrectly classified (wrong depth, wrong extraction_type, or segments that don't match the claimed failure mode). If you find none, explain why.

11. Is there a `specialized` depth positive anywhere in the set? CONV-022 was reclassified to `domain`. Is this gap acceptable for DSPy training, or should we add a genuinely tool-bound principle (e.g., a specific software workflow)?

12. What's the single most damaging gap or error in this golden set that would poison DSPy training?

---

## OUTPUT FORMAT

```yaml
structural_audit:
  total_consistency_score: "X/10"
  errors_found: [{example_id: "...", issue: "...", severity: "P0/P1/P2"}]
  bimodal_signals: ["...", "..."]

dspy_readiness:
  overall_verdict: "READY / NOT READY / READY WITH FIXES"
  minimum_examples_needed: N
  current_sufficiency: "sufficient / borderline / insufficient"
  domain_gaps: ["...", "..."]
  extraction_type_balance: {assessment: "...", risk: "low/medium/high"}
  negative_ratio_assessment: "..."

hardware_reality:
  s2_model_options: [{model: "...", feasibility: "high/medium/low", risk: "..."}]
  merged_s4_call_viability: "sound / needs revision / flawed"
  s4_phi4_mini_capacity: "sufficient / borderline / insufficient"

critical_findings:
  misclassified_examples: [{example_id: "...", actual: "...", assigned: "..."}]
  missing_specialized_positive: {impact: "low/medium/high", recommendation: "..."}
  most_damaging_gap: "..."

recommended_actions:
  immediate: ["...", "..."]
  before_dspy: ["...", "..."]
  post_dspy: ["...", "..."]
```
