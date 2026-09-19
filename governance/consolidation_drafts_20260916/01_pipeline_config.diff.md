# 01 — `config/pipeline_config.yaml` proposed edits (D-2637)

Targeted edits only; the file is 25 KB and mostly stage parameters, not model assignments.
`before` = current text. Comments marked NEW are additions.

## 1. `models` — make roles explicit (the keys are misnamed, D2340)

```yaml
models:
  generator:                     # S2 convergent extraction (+ DSPy target)
    model: Qwen3-Coder-30B-A3B-Instruct-MLX-4bit   # UNCHANGED. mbpp 0.68 (best), 4x faster than
                                                   # Qwen3.8 on the S2 prompt at identical routing.
    provider: omlx
    temperature: 0.0
    max_tokens: 1024

  verifier:                      # MISNOMER (D2340): this is the S4 CRIBS+classify model.
    role: s4_classifier          # NEW: explicit role label
    model: [[G2]]                # GATED. incumbent gpt-oss-20b-MXFP4-Q8 (R5-clean, ARM-4 discipline
                                 # 0.85, 30/30 valid JSON in production) vs Qwen3.8-27B (0.709/0.693
                                 # measured, but R5-blocked) vs gemma-4-E4B (R5-clean, beat gpt-oss in
                                 # voting). DECIDED BY: scripts/pipe_s4_classify_gold.py, 60 rows/model.
    provider: omlx
    temperature: 0.0
    max_tokens: 2048             # CORRECTION: production merges at 2048 (stage4.merged_call_max_tokens),
                                 # not the 512 code default.
    reasoning_off_prefix: 'Reasoning: low'
    reasoning_off_models: [gpt-oss-20b-MXFP4-Q8]
    chat_template_kwargs: {enable_thinking: false}
    thinking_budget: 256
    depth_thinking_budget: 128

  verifier_v2:                   # MISNOMER (D2340): this is the S2 fast probe.
    role: s2_probe               # NEW
    model: Phi-4-mini-instruct-8bit                # CONFIRMED KEEP. 1.3 s median, 3.99 GB, phi3
                                                   # family (R5-safe vs the Qwen generator), 6/6
                                                   # valid extraction with zero NULLs.
    provider: omlx
    temperature: 0.0

  embeddings: {model: bge-m3, provider: ollama, alternative: mlx-community/Qwen3-Embedding-0.6B-4bit-DWQ}
  nli_large: MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli   # S5 = this and nothing else (D2298)

  # NEW — the models that hold a role but had no key of their own:
  depth_classifier:  {model: gemma-4-E4B-it-MLX-4bit, provider: omlx, temperature: 0.0}
  tool_agent:        {model: Ornith-1.5-35B-A3B-REAP-19B, provider: omlx, temperature: 0.0}
  lightweight_coder: {model: Ornith-1.5-9B-MLX-8bit, provider: omlx, temperature: 0.0}
  long_context:      {model: "[[G1]]", provider: omlx, temperature: 0.0}
```

## 2. `label_vote` — align with the measured voting verdict

Measured (`governance/voting_verdict_20260916.md`, 251 human-adjudicated rows):
Qwen3.8-27B alone **0.709** @ 100 % coverage; the AVERAGE 3-combo majority is **0.541** (worse than doing nothing clever);
no local partner rescues more than **18 %** of Qwen3.8's errors; unanimity of REAP+Qwen3-Coder+Qwen3.8 = **0.915 @ 18.7 %** coverage.

```yaml
label_vote:
  decider: Qwen3.8-27B-MLX-4bit          # NEW: single decider, full coverage
  unanimity_gate_voters:                 # NEW: auto-accept tier only (0.915 @ 18.7 %)
    - Ornith-1.5-35B-A3B-REAP-19B
    - Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
    - Qwen3.8-27B-MLX-4bit
  majority_voting: disabled              # NEW: REJECTED by measurement (0.541 < 0.709)
  reliable_voters:                       # was [deepseek-v4-pro, Qwen3.8-27B-MLX-4bit]
    - Qwen3.8-27B-MLX-4bit               # SOLE production voter (local, C1/C3 clean)
  # RULING D1 (ACCEPTED 2026-09-16): deepseek-v4-pro is REMOVED from reliable_voters.
  # Measured head-to-head (60 discipline disagreements): DeepSeek 40 / Qwen3.8 15, but the
  # review sheet disclosed provenance to the human adjudicator (brand authority confound) —
  # blind re-adjudication still owed before that gap is treated as fact. DeepSeek stays as an
  # OFFLINE anchor-builder only (bounded labelling job, never a production labeller), because
  # a cloud model inside the production path breaks C1 ($0 marginal) and C3 (sovereignty).
  cloud_opt_in: deepseek-v4-pro          # C22 hybrid sovereignty: explicit opt-in, offline roles only
  cloud_opt_in_roles: [anchor_builder, offline_adjudication_helper]
  advisory_voters: [Qwen3-Coder-30B-A3B-Instruct-MLX-4bit]
  abstain_on_disagreement: true
  # measured basis for the exclusion below: Ornith-9B draws "A" by default
  # (mmlu_pro 3/25 = chance for BOTH quant variants; voting 0.227 / 0.116)
  never_vote: [Ornith-1.5-9B-MLX-8bit, Ornith-1.5-9B-OptiQ-4bit]   # NEW
  fail_closed_discipline: emerging
  fail_closed_depth: domain
```

## 3. `stage4` — ADD the peer-granularity guard as config (C12: it is currently a script constant)

Measured on 251 gold rows: union is a **peer-only** operator. Qwen3.8 alone 0.693; union with REAP (|P| 2.23) 0.729;
with gemma-4-E4B (|P| 3.60) 0.513; with Qwen3-Coder (|P| 6.06) 0.474; union of all six 0.398.
Gold uses 2.54 domains/row. The real reliable pair measured ratio **1.158** — which is why D2633's union was correct.

```yaml
stage4:
  # ... existing keys unchanged (merged_call_enabled: true, merged_call_max_tokens: 2048,
  #     dedup_cosine_threshold: 0.92, depth_focused_classification: true,
  #     depth_prompt_variant: v3_contrastive, golden_max_examples: 7, fb_name_max_words: 8, ...)

  domain_aggregation:                    # NEW (D-2637)
    policy: overlap_union_gated
    peer_granularity_max_ratio: 1.30     # max(mean|P|)/min(mean|P|) — above this, DO NOT union
    peer_f1_max_gap: 0.10                # companion condition; eval-time only (needs ground truth)
    on_non_peer: abstain                 # fail-closed (D2610 philosophy)

  student_preclassifier_enabled: false   # NEW, EXPLICIT — and it must stay false:
                                         # ModernBERT flat macro-F1 0.229 discipline / 0.009 domain;
                                         # bge-m3 taxonomy-match macro-F1 0.000. SetFit not implemented.
```

## 4. `stage5` — assert there is NO LLM (currently implicit)

```yaml
stage5:
  # NEW, documentary: S5 has no LLM. Any LLM key here is a bug.
  verifier_kind: nli_only                 # D2298, fail-closed
  nli_model: MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli
  llm_verifier: null
```

## 5. `retrieval_eval` / `hyde` — unchanged, but note the gap

```yaml
retrieval_eval: {model: Phi-4-mini-instruct-8bit}   # KEEP. NEVER BENCHMARKED as a stage.
hyde:           {model: Qwen3-Coder-30B-A3B-Instruct-MLX-4bit}  # KEEP. NEVER BENCHMARKED.
stage4_5:       gpt-oss-20b-MXFP4-Q8                # KEEP. NEVER BENCHMARKED.
stage2:         relabel_cross_family_model: gpt-oss-20b-MXFP4-Q8   # KEEP (R5-clean). NEVER BENCHMARKED.
rerank:         BAAI/bge-reranker-v2-m3
```

## Not edited, deliberately
- `stage1_5.*` — embeddings/clustering, no LLM.
- All threshold/parameter keys outside the model question.