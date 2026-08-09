# Maxwell OS v3.0 — Master Roundtable Evaluation Prompt v3
## Bottleneck Mitigation + Full Pipeline Audit

**Date:** 2026-08-09
**Evaluator Role:** S-tier Senior RAG Engineer & Knowledge Architecture Expert
**Context:** Maxwell OS is an 8-stage knowledge extraction pipeline processing 2,655 Foundation Blocks from ~200 books. All generation runs locally (Apple Silicon, 64GB RAM, OMLX). temp=0.0 on all generation.

---

## INSTRUCTIONS

You are evaluating the Maxwell OS knowledge extraction pipeline as an S-tier senior RAG engineer. You have full access to:

1. **Smoke Test v1 Report:** `SMOKE_TEST_REPORT.md` (12 FBs, S4→S5 output)
2. **Smoke Test v2 Report:** `SMOKE_TEST_V2_REPORT.md` (20 FBs, S4→S5 output)
3. **Golden Examples:** `stage2_fewshot_convergent.yaml` (32 examples: 19 pos + 13 neg)
4. **S4 Merge Code:** `pipeline/stage4_merge.py` (with D2220 depth classifier fix)
5. **S5 Verify Code:** `pipeline/stage5_verify.py` (with D2220 mechanism quality pre-filter)
6. **Previous Roundtable v2:** Your prior evaluation + Qwen/Kimi consensus

---

## PART A: BOTTLENECK MITIGATION (NEW — PRIMARY FOCUS)

The pipeline currently takes ~30h for 2,655 FBs. The breakdown:

| Stage | Time | % | Model | Notes |
|-------|------|---|-------|-------|
| S2 Convergent Extraction | 13.3h | 44% | Qwen3-Coder 30B | 1 LLM call per FB |
| S4 CRIBS Enrichment | 9.6h | 32% | Qwen3 35B | Application, failure_mode, elaboration, keywords |
| S4 Classification | 5.2h | 17% | Phi-4-mini 8bit | Discipline, domains, depth, evidence |
| S5 DeBERTa NLI | 0.3h | 1% | DeBERTa-v3 (local) | MAX-entailment scoring |
| S5 LLM Deep Check | 1.8h | 6% | Gemma-4-E4B 4bit | Only ~30% of FBs escalate |
| S6 SQLite Commit | 0.0h | 0% | sqlite-vec | I/O bound |

**Constraints:**
- All models run locally (OMLX on Apple Silicon M-series, 64GB RAM)
- No cloud API usage — $0 marginal cost is an IRON RULE (C1)
- temp=0.0 on all generation — cannot use speculative decoding or beam search
- Generator ≠ Verifier — different model families required (R5)
- Pipeline is currently SEQUENTIAL (one FB at a time, one model at a time)

### A1: S2 Extraction Speed (44% of total — 13.3h)

**Current:** Qwen3-Coder-30B-A3B-Instruct-MLX-4bit processes each FB individually. Each call takes ~18s (prompt construction + inference + JSON parse).

**Questions:**

1. **Prompt caching:** Does OMLX/MLX support KV-cache reuse for repeated system prompts? If each S2 call uses the same system prompt + golden few-shot examples, can the prefix be cached and shared across 2,655 calls? Estimate speedup.

2. **Batch inference:** Can MLX run batch inference (multiple prompts → multiple outputs in one forward pass)? If S2 prompts differ only in the cluster text, can we batch N FBs into a single call? What are the memory implications on 64GB?

3. **Model swap:** Qwen3-Coder 30B → Qwen3-Coder-8B? The 30B model has ~30B parameters but is MoE (only ~3B active per token). Is there a smaller model that preserves extraction quality? What's the quality-speed Pareto frontier?

4. **Prompt trimming:** How much can the S2 system prompt + golden examples be trimmed without degrading extraction quality? The current golden set is 19 positives + 13 negatives (~2500 lines YAML). What's the minimum effective few-shot size?

5. **Early exit / speculation:** If the extracted FB name + definition is clearly low-quality (e.g., < 50 chars), can we abort the full extraction and skip CRIBS? What % of FBs would this catch?

6. **Parallel subprocess:** Since each FB is independent (cluster-before-extract), can we run multiple OMLX instances in parallel subprocesses? What's the memory ceiling? 64GB / (model_size + overhead)?

### A2: S4 CRIBS + Classification (49% of total — 14.8h)

**Current:** Two separate LLM calls per FB: CRIBS enrichment (Qwen3 35B, ~13s) + Classification (Phi-4-mini, ~7s).

**Questions:**

1. **Merge CRIBS + Classification into ONE call:** The FB already has name, definition, mechanism, boundary, consequence from S2. Can one prompt produce {application, failure_mode, elaboration, keywords, jargon, discipline, domains, depth, is_specialized, evidence}? What's the token cost and quality impact? This was deferred pending A/B test — how would you design the A/B test?

2. **Lighter CRIBS model:** Phi-4-mini-8bit is fast (~7s) but Qwen3-35B is slow (~13s). Can CRIBS enrichment run on Phi-4-mini or Gemma-4-E4B instead? What quality degradation is expected?

3. **Skip CRIBS for certain FBs:** If mechanism length > 500 chars AND definition is detailed, is CRIBS enrichment actually adding value? Can we run a classifier to decide "CRIBS needed" vs "CRIBS skipped"? What % of FBs would skip?

4. **Classification batching:** The classification prompt is short (~200 tokens). Can Phi-4-mini process batched classifications? N FBs → 1 call with structured JSON array output?

### A3: Overall Pipeline Architecture

**Questions:**

1. **Pipeline parallelism:** S2 output for FB_i is independent of S2 output for FB_j. Can we pipeline S2→S4→S5 as a streaming flow? FB finishes S2 → immediately starts S4 while next FB starts S2? What's the theoretical max throughput?

2. **Model multiplexing:** Can OMLX load two models simultaneously (e.g., Qwen3-Coder for S2 + Phi-4-mini for S4 Classify)? On 64GB with 4-bit quantized models (~5-8GB each), is this feasible?

3. **Precomputation:** Probe cache already exists (14,168 targets). Can we precompute embeddings for all clusters? Precompute classification for known disciplines? Pre-filter obvious non-convergent clusters before S2?

4. **Hardware-adaptive scaling:** On 64GB M-series, what's the optimal concurrent model count? What degrades first — memory bandwidth, compute, or context window?

---

## PART B: ACCURACY OPTIMIZATION (ZERO-REGRESSION)

### B1: Depth Classification (D2220 fix applied)

The depth classifier was just moved from structural derivation (n_domains → depth) to semantic LLM classification (physicist-chef-poet test). The previous method had ~55% error rate.

**Questions:**
1. What's the expected accuracy of LLM-classified depth? How would you validate it?
2. Should depth classification use a DIFFERENT model family than the CRIBS model? (R5 compliance)
3. If classification confidence is low, should we escalate to a second model? At what cost?

### B2: NLI Gate Calibration (D2220 mechanism pre-filter applied)

The new mechanism quality pre-filter catches tautologies and citation echoes before NLI. The MAX-entailment scoring (strongest passage wins) is still vulnerable when source count is high.

**Questions:**
1. Should we switch from MAX-entailment to MEAN-entailment or WEIGHTED-entailment (by source independence)?
2. Can we detect citation echo automatically? Same author across books, shared publisher, shared year?
3. The current NLI threshold is 0.8 for PASS. What's the optimal threshold? How would you measure precision/recall at different thresholds?
4. Should we add a contradiction-override: if ANY passage contradicts with high confidence, fail regardless of entailment scores? (Already partially implemented — contradiction ≥ 0.8 = fail)

### B3: Golden Set Coverage

**Current:** 32 examples (19 pos + 13 neg). Both prior evaluators recommended 50+ for robust few-shot.

**Questions:**
1. What's the minimum effective golden set size for S2 few-shot learning? Diminishing returns point?
2. Which gap categories are most critical to fill next?
3. Should golden examples be DYNAMIC — selected per-cluster based on domain similarity rather than a static set?

---

## PART C: MARKET RESEARCH — COMPARABLE SYSTEMS

As an S-tier RAG engineer who follows the field closely:

1. **What production knowledge extraction pipelines exist that are comparable to Maxwell OS?** (cluster-before-extract, local-only, causal mechanism focus)

2. **What techniques from GraphRAG, LightRAG, or similar systems could accelerate Maxwell?** Community summarization, Leiden clustering, etc.

3. **What's the state of the art in LLM-based knowledge graph construction?** Are there papers/techniques we should be tracking?

4. **OMLX/MLX ecosystem:** Any upcoming features that could help (KV-cache, batch inference, model parallelism)?

---

## PART D: VERIFICATION — CHALLENGE EVERYTHING

This is a verification exercise. Do not assume anything is correct.

1. **Verify the depth classifier fix (D2220):** Does the new CLASSIFY_SYSTEM_PROMPT correctly define the ontological boundaries between universal/cross-domain/domain/specialized? Would you modify the definitions?

2. **Verify the mechanism quality pre-filter (D2220):** Are the banned tautological patterns comprehensive? Are there false positives (legitimate mechanisms that happen to start with "because it enables...")?

3. **Verify the golden set expansion (D2221):** Are all 8 new examples correctly classified? Do any have issues you'd flag?

4. **Identify anything we missed:** What critical bug, gap, or optimization opportunity exists that has NOT been addressed in D2220-D2221?

---

## OUTPUT FORMAT

```yaml
bottleneck_mitigation:
  s2_extraction:
    prompt_caching: {feasible: true/false, speedup_estimate: "X%", rationale: "..."}
    batch_inference: {feasible: true/false, speedup_estimate: "X%", rationale: "..."}
    model_swap: {recommended_model: "...", quality_impact: "low/medium/high", speedup: "X%"}
    prompt_trimming: {min_effective_fewshot: N, speedup: "X%"}
    parallel_subprocess: {max_concurrent: N, memory_per_instance: "X GB", speedup: "X%"}
    recommended_sequence: ["...", "..."]
    total_potential_speedup: "X%"

  s4_cribs_classify:
    merge_calls: {feasible: true/false, quality_impact: "low/medium/high", speedup: "X%"}
    lighter_model: {recommended_model: "...", quality_impact: "low/medium/high"}
    skip_cribs: {skip_percentage: "X%", quality_impact: "low/medium/high"}
    batch_classify: {feasible: true/false, batch_size: N}
    total_potential_speedup: "X%"

  architecture:
    pipeline_parallelism: {feasible: true/false, theoretical_max_throughput: "X FBs/min"}
    model_multiplexing: {feasible: true/false, max_concurrent_models: N}
    precomputation: {opportunities: ["...", "..."], speedup: "X%"}

  overall_eta_reduction:
    current: "30h"
    after_all_optimizations: "Xh"
    without_quality_degradation: "Xh"

accuracy_optimization:
  depth_classifier_accuracy: {expected: "X%", validation_method: "..."}
  nli_threshold_optimal: {value: 0.XX, rationale: "..."}
  golden_set_size: {minimum_effective: N, diminishing_returns_at: N}
  critical_gaps: ["...", "..."]

market_research:
  comparable_systems: ["...", "..."]
  relevant_techniques: [{name: "...", applicability: "high/medium/low", rationale: "..."}]
  papers_to_track: ["...", "..."]
  omlx_ecosystem: {upcoming_features: ["..."], recommendations: ["..."]}

critical_findings:
  bugs_found: [{severity: "P0/P1/P2", description: "...", fix: "..."}]
  missed_opportunities: ["..."]
  structural_concerns: ["..."]
```
