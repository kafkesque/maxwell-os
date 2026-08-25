# S4 Bottleneck Propositions

> Status: **PROPOSED — not yet tested.** Queue these for the S4 classification/merge pass
> AFTER singleton S2 completes. Do not execute against the live S2 run.

## Context

S4 runs `gpt-oss-20b-MXFP4-Q8` (OMLX), `model_type=gpt_oss`, 20B MoE with 4 active
experts (`num_experts_per_tok=4`), 24 layers, `vocab_size=201088`. It is **decode-bound**.
Current S4 golden is only 4 examples (6.4KB) and is **NOT injected** into prompts
(D2454 quality gap). Estimated decode floor ~4-6h at current config.

## Priority 1 — correctness / quality gates (do these FIRST, before any speed work)

1. **Wire S4 golden into prompts (D2454).** `config/golden/stage4_golden.yaml` (4
   examples) is currently not injected. This is a *quality* gap, not a speed lever —
   fix it before optimizing speed, otherwise you are tuning an unrepresentative prompt.
   Measure the prefill-cost delta once wired.

2. **Baseline measurement (quality + speed).** Before any speed change, capture:
   per-record wall-clock, decode tok/s, prefill time, and a human-scored
   classification-accuracy sample (~100 FBs) as the quality floor. Every later speed
   lever must A/B against this floor with **zero** accuracy loss.

## Priority 2 — safe speed levers (lossless by construction)

3. **Verify `gpt-oss-20b` runs with `--no-cache` (`cache.enabled=false`) in oMLX.**
   Same thrash class as D2460. Confirm `~/.omlx/settings.json` cache is disabled for
   the S4 model and `store_cache_main_dispatch` stays flat. If S4 was previously run
   with SSD paging, this is a free 5-10x decode win with zero quality impact.

4. **Find optimal concurrency for `gpt-oss-20b`.** A 4-active-expert MoE serializes
   very differently from Qwen3-Coder's 128-expert MoE. Benchmark 1/2/3/4 workers on
   real S4 batches; pick the throughput max that keeps per-record latency stable (no
   KV-store dispatch thrash). Concurrency does not change per-record output.

5. **Check for `gpt_oss`-specific oMLX kernels / speculative-prefill draft.** Inspect
   oMLX `custom_kernels/` and `model_settings.json` for a `gpt_oss` ANE-prefill / MTP /
   SpecPrefill path. If a same-vocab draft exists, A/B verify **lossless** (identical
   output) before enabling. If none exists, skip — do not force a foreign draft.

## Priority 3 — evaluate only with an explicit quality A/B gate

6. **TurboQuant KV for S4.** Conflicts with `--no-cache`; only worth testing if S4
   contexts are long. S4 classification prompts are likely short — skip unless
   profiling shows KV pressure.

7. **Model-rightsizing S4 (e.g., Phi-4-mini for classification).** Only consider if the
   `gpt-oss-20b` decode floor is genuinely unacceptable AND a ~100-record A/B shows no
   classification-accuracy loss. Touches R5 / D2264 / D2323 — must go through Maxwell
   (human-in-the-loop) and the decision registry first. Do NOT swap without approval.

## Method notes

- `temp=0.0` → deterministic; A/B comparisons are meaningful.
- All speed levers must preserve: `content_type` classification accuracy,
  `extraction_type` form accuracy, R14 stamps, and provenance fields.
- Keep `generator != verifier` (R5) intact — do not collapse S4 into the S2 model family.
