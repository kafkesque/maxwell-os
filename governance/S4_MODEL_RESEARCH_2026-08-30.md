# S4 Classifier Model Research — Newer LLM Candidates (last ~1 month)

> **Date:** 2026-08-30 | **Scope:** find any local/downloadable model released in the last
> ~1 month that could be as good or better than the current S4 classifier, and whether any
> are trained/fine-tuned for the S4 classification use case. **NO S4 rerun performed.**
> **Hardware target:** Apple M1 Max, 64 GB RAM, MLX (OMLX server). **R5 constraint:** S4
> classifier must NOT be the Qwen family (S2 generator is Qwen3-Coder-30B).

## 0. Current baseline (the bar to beat)

- **S4 classifier:** `gpt-oss-20b-MXFP4-Q8` (OpenAI, 2025-08-04). 21B total / **3.6B active**
  MoE. ~11 GB on disk, ~15 GB in RAM. 128k ctx.
- **Honest per-FB latency (D2468 re-benchmark, cache-clean):** 17.71s median / 19.02s mean.
  Depth accuracy 62.5% (short focused prompt) → 87.5% (production focused path, D2250).
- **Bottleneck (already root-caused):** MoE dispatch + reasoning CoT, NOT memory. `thinking_budget`
  caps (256 merged / 128 depth) + `Reasoning: low` prefix already in place.

## 1. Frontier releases in the last ~1 month (2026-07-30 → 2026-08-30)

| Model | Org | Released | Total / Active | Fit on M1 Max 64 GB? | Verdict |
|---|---|---|---|---|---|
| **GLM-5.3-Flash** | ZAI (Zhipu) | 2026-08-25 | 320B / **18B** MoE, hybrid sparse+linear attn, MIT | ❌ (~160 GB @4-bit) | Too big; 18B active ≫ 3.6B → slower |
| **GLM-5.3** (non-flash) | ZAI | 2026-08-25 | 78-layer DSA MoE, 8 exp/tok, 1M ctx, fp8 | ❌ | Even bigger |
| MiniMax-M3 | MiniMax | 2026-06-02 (MLX quants 08-23) | 428B / 23B | ❌ | Too big; also NOT "last month" |
| Kimi K3 | Moonshot | 2026-06-13 | 896 experts, 16 active | ❌ | Too big; NOT last month |
| DeepSeek-V4-Flash | DeepSeek | 2026-04-22 | 284B / 13B | ❌ | Too big; NOT last month |
| Qwen3.8-27B / 3.8-Max | Alibaba | 2026-08 | 27B dense / larger MoE | ⚠️ | **R5-FORBIDDEN** (Qwen family) |

**Headline finding:** every *major* model released in the last month is a 100B–1.6T MoE
monolith. None run on 64 GB — even 4-bit needs 2–4× the RAM. The frontier has moved
decisively to massive sparse models that this hardware cannot serve.

## 2. Realistic R5-clean candidates (the ~20–30B tier that actually fits)

| Model | Family | Notes | Speed vs gpt-oss? |
|---|---|---|---|
| gpt-oss-20b-MXFP4-**Q4** | OpenAI (same) | **the one untried lever** — same model, lower-bit quant | ⚠️ A/B pending (download in progress this session) |
| gpt-oss-120b | OpenAI | 120B / ~12B active, 8-bit | ❌ 120B ≈ 60 GB @4-bit = marginal + 3.3× active → slower |
| gemma-4-E4B-it-MLX-4bit | Google | 4B dense (already local) | ✅ faster, but ✗ less capable (probe only, not S4 classifier) |
| gemma-4-12B/31B | Google | dense 12B/31B | ⚠️ 12B faster-but-weaker; 31B slower (MoE vs dense parity unclear); R5-clean |
| GLM-5.2 | ZAI | (2026-06) 355B-class, fp8/mxfp4 | ❌ too big |

**The speed↔capability tension is fundamental here:** gpt-oss-20b is already near the floor
for a 20B-total MoE at 3.6B active. "Faster" ⇒ fewer active params ⇒ less capable; "more
capable" ⇒ more active params ⇒ slower. There is no free lunch in this tier.

## 3. Classification/fine-tune-specific models (the second question)

- Searched HF for `text-classification`, `zero-shot classification`, `taxonomy classification`
  sorted by recency. **Result: nothing relevant.**
- The only `text-classification` hits in the last month are tiny BERT fine-tunes for
  narrow domains (food, Korean legal, etc.). **Zero** `taxonomy classification` matches.
- This is expected: S4's task (4-way depth × canonical discipline/domain taxonomy) is a
  **bespoke ontology** specific to Maxwell OS. No public model is trained/fine-tuned for it.
  A "drop-in fine-tuned classifier" does not exist and never will without local fine-tuning
  on this project's golden set (that is what `dspy_trainer.py` / MIPROv2 is for — gated off,
  D2482).

## 4. Recommendations (unchanged from prior research, re-confirmed)

1. **Do NOT swap the S4 classifier.** No last-month model is both runnable and better.
2. **The one untried speed lever = Q4/Q2-vs-Q8 quant A/B** of the *same* gpt-oss-20b
   (memory-bandwidth-bound long-context classification can improve MAP@3/latency at lower
   precision). Q4 variant = `mlx-community/gpt-oss-20b-MXFP4-Q4` (11.2 GB) — downloading.
   **Q2 does NOT exist** for gpt-oss-20b in MLX (nearest is `NexVeridian/gpt-oss-20b-3bit`);
   Q4 is the floor that matters.
3. **If a swap is ever forced by capability needs:** GLM-5.x small tier or gemma-4-12B would
   be the R5-clean shortlist — each needs an MLX port + golden A/B (config/golden/stage4_golden.yaml)
   before any production change. No action taken this session.
4. **Classification-specific model:** none exists; the correct path is local fine-tuning via
   the already-built (gated) DSPy harness, not a public download.

## 4b. Q4-vs-Q8 A/B RESULT (run 2026-08-30, live OMLX, golden depth set)

`scripts/benchmark_s4_quant_ab.py`, n=16 stratified golden depth FBs (seed 42), same prompt,
`enable_thinking=false` on both, one warmup call each. Production path = depth-focused short prompt.

| Quant | median | mean | min–max | Accuracy | throughput |
|---|---|---|---|---|---|
| **Q8** (current, MXFP4-Q8) | **5.09s** | 6.50s | 3.5–15.7s | **15/16 = 93.8%** | 11.8 FB/min |
| Q4 (MXFP4-Q4) | 14.41s | 16.49s | 7.0–27.9s | 10/16 = 62.5% | 4.2 FB/min |

**Verdict: Q4 is ~2.8× SLOWER and 31 points LESS accurate.** The memory-bandwidth hypothesis
("lower-bit quant improves long-context classification latency") is **REFUTED for gpt-oss-20b on M1 Max**.
Q4 also drifts off the one-word label more often (emits "behavior.", "it's", "the" — reasoning leakage),
so the drop is a real instruction-following/reliability regression, not a parse artifact.

**Conclusion: keep `gpt-oss-20b-MXFP4-Q8`. There is NO faster-or-equal quant, and no last-month
model that fits 64 GB and beats it.** Q4 model retained on disk (~11 GB) + registered in OMLX for
reference; can be removed if disk is a concern.

## 5. What was DONE this session (no S4 rerun)

- BUG-189 fixed (archived 3 dead `tools.pipeline_paths` phantom-import tools).
- BUG-190 fixed (OMLX `/health` vs `/v1/models` catalog lie in `model_lazyload.py --status`).
- BUG-191 fixed (`check_stage_order()` counting `timeouts` as a stage).
- `get_space_id` confirmed NOT needed by stage6b (uses `intimacy_lattice.route_space()`).
- gpt-oss Q4 download initiated for the Q4-vs-Q8 speed A/B (pending completion).
