# S4 Merge Bottleneck — Validated Analysis + Peer-Reviewed Tackle Options

> **Date:** 2026-08-14 · **Author:** Maxwell OS (agent) · **Scope:** Stage 4 classify/merge throughput
> **Method:** code trace + live OMLX latency measurements (NOT estimates). All timings below
> were measured against `http://localhost:11435` on this host.

> **⚠️ CORRECTION (2026-08-14, post-publication):** this doc cites GPT-OSS focused-depth accuracy
> as **"87.5%"** (the D2249 claim). The authoritative production-path benchmark
> (`tools/benchmark_s4_depth_frugal.py`, n=8 stratified) measures **75.0%**, and the 50-FB golden
> production verify (`s4_depth_d2359_gptoss_production_verify.json`) measures **72.0%**. The "87.5%"
> figure was a governance claim that drifted from the benchmark; **do not cite it as current.**
> See `governance/S4_DEPTH_EMPIRICAL_RESULTS_2026-08-14.md`.

> **⚠️ SUPERSEDED (2026-08-15, D2366/D2367):** this doc's §6 "tackle plan" and §7 "recommendation"
> are **stale — both P0 items were benchmarked and REJECTED**. D2366 measured against the
> post-relabel golden set: **batch depth = 66.7% vs 84.4% sequential (n=45, parity 60%)** and
> **gemma-4-E4B depth = 62.5%** — both fail the ≥90% gate. **Speculative decoding (P1) is NOT
> actionable**: `_MLX_DRAFT_MODELS` (pipeline/omlx_call.py) has no draft pairing for gpt-oss.
> The **only surviving speedup is `thinking_budget=256/128`** on the merged call (X8, 1.8–1.9×),
> gated on a merged-call accuracy run and **blocked by BUG-132** (the budget is a global key
> shared with the depth call). The cost denominator is also corrected: **~3,556 FBs → ~39h,
> not 142h** (D2365/D2366). Do not resurrect batch-depth or gemma-depth from this doc.

---

## 1. TL;DR

S4 is slow because **`gpt-oss-20b-MXFP4-Q8` is a *reasoning* model** — it emits
`reasoning_content` (chain-of-thought) on **every** call *even with the `Reasoning: none`
system prefix*, which OMLX/GPT-OSS does not honor. Each call burns ~1.1k–2.7k tokens of
hidden reasoning before producing `content`, adding ~10–61 s of latency per call.

"Prior S4 was faster" is explained by **D2249/D2250 (2026-08-10)**: the S4 classifier was
swapped from `Phi-4-mini-instruct-8bit` (non-reasoning, ~1–2 s/call) to
`gpt-oss-20b-MXFP4-Q8` (reasoning, ~10–20 s/call) to lift depth-classification accuracy
(87.5% focused vs 38% long-prompt). The accuracy gain is real; the ~5–10× latency cost was
the unstated trade-off.

---

## 2. Validated measurements (2026-08-14)

| Call | Model | max_tokens | total_time | result |
|---|---|---|---|---|
| depth (one-word) | gpt-oss-20b | 64 | 4.0 s | **empty content**, `finish_reason=length` (burned all tokens on reasoning) |
| depth (one-word) | gpt-oss-20b | 1024 | 10.0 s | `"specialized"`, 1165 chars reasoning_content, 231 completion tokens |
| CRIBS batch ×4 | gpt-oss-20b | 2048 | 61.2 s | 2734 chars reasoning, 3949 chars content → **15.3 s/FB** |
| depth (one-word) | Phi-4-mini | 64 | 1.08 s | `"Causal mechanism"` — **WRONG** (echoed `extraction_type`, not depth) |
| depth (one-word) | gemma-4-E4B | 64 | 4.98 s | `"Domain"` — correct, **zero reasoning_content** |
| depth (one-word) | gemma-4-31B | 64 | 16.9 s | empty content (also a reasoning model) |

**Conclusion:** GPT-OSS always reasons. `Reasoning: none` is ignored. Non-reasoning models
(Phi 1.08 s, gemma-4-E4B 4.98 s) are 2–9× faster but vary in accuracy.

### Why the pipeline needs high `max_tokens` for GPT-OSS
`pipeline/omlx_call.py::call_omlx` reads `msg["content"]` and raises `KeyError("content
missing")` if it is `None`. A reasoning model with low `max_tokens` hits
`finish_reason=length` mid-reasoning and returns empty `content`. D2249 therefore sets
`max_tokens ≥ 1024` so the model has room to *finish* reasoning AND emit the answer. This
is why every GPT-OSS call is expensive: the reasoning tokens are mandatory overhead, not
optional.

---

## 3. Current S4 cost model (per FB)

`pipeline/stage4_merge.py::run_stage4` makes **two** GPT-OSS calls per FB:

1. **CRIBS + classification** — batched (`stage4.batch_size: 4`) via
   `batch_cribs_classify()` → ~15.3 s/FB amortized.
2. **Depth-focused classification** — **sequential**, one `classify_depth_focused()` call
   per FB (because D2247 found the *long* combined prompt degrades depth to 38%; a separate
   short prompt restores 87.5%) → ~10 s/FB.

Total ≈ **25 s/FB ≈ 2.4 FBs/min**. (Handoff's "3.5 FBs/min" assumed the depth-focused call
was cheaper than measured.) At ~12,964 FBs that is ~142 h (D2363 — production runs merged 39.5s/FB; §3's 25s/FB assumed batch CRIBS which batch_enabled:false disables).

The depth-focused call is **redundant work**: the batch prompt already returns a `depth`
field, which is then *discarded* and recomputed serially at ~10 s/FB.

---

## 4. Why "prior S4 was faster" (root cause)

- **Pre-D2249:** S4 classifier = `Phi-4-mini-instruct-8bit` (non-reasoning). D2124 budgeted
  **~5–10 s/FB end-to-end**.
- **D2249/D2250 (2026-08-10):** classifier → `gpt-oss-20b-MXFP4-Q8` for depth accuracy
  (87.5% vs 38%). GPT-OSS is a reasoning model → ~10–20 s/call.
- **D2265 (2026-08-11):** batch CRIBS added to amortize reasoning (~19 s/FB), but the
  depth-focused call remains sequential and unbatched.

So the slowdown is **the Phi→GPT-OSS model swap**, partially offset by batching. It is not a
regression from a code bug — it is the documented cost of the D2249 accuracy decision.

---

## 5. Existing peer-reviewed solutions (adaptable + referencable)

| # | Technique | Reference | Relevance to this bottleneck |
|---|---|---|---|
| 1 | **Continuous batching / PagedAttention** | Kwon et al., *"Efficient Memory Management for LLM Serving with PagedAttention"*, SOSP 2023 (vLLM) | Increases throughput by decoding many requests concurrently; directly attacks the "one reasoning stream at a time" serialization. |
| 2 | **Speculative decoding** | Leviathan, Kalman & Matias, *"Fast Inference from Transformers via Speculative Decoding"*, ICML 2023 | Draft with a small model, verify with the big one. MLX already advertises this (`omlx_call._call_mlx` "speculative decoding 1.5–2× faster"). |
| 3 | **Grammar/constrained decoding** | Willard & Louf, *"Efficient Guided Generation for LLMs"* (Outlines) 2023; Geng et al., *"Grammar-Constrained Decoding for Structured NLP Tasks"*, EMNLP 2023 | Force JSON schema, suppress free-form CoT. Only helps if the serving stack enforces the grammar *during* generation. |
| 4 | **Distillation** | Hinton, Vinyals & Dean, *"Distilling the Knowledge in a Neural Network"* 2015 | Train a small non-reasoning model (e.g. Qwen2.5-3B / gemma-4-E4B) on GPT-OSS's labels → GPT-OSS accuracy at Phi speed. |
| 5 | **Cascade / model routing** | Chen, Zaharia & Zou, *"FrugalGPT"* 2023 | Cheap model first; escalate to expensive model only when confidence is low. Fits the depth-vs-CRIBS split exactly. |
| 6 | **Prefix / KV-cache reuse** | Zheng et al., *"SGLang: RadixAttention"* 2023 | The batch system prompt is identical across batches — reuse its KV cache instead of recomputing. |
| 7 | **Prompt compression** | Jiang et al., *"LLMLingua"* 2023 | Less relevant (inputs are small FB summaries), listed for completeness. |

These were already *identified* in D2303; the new contribution of this analysis is the
**live latency evidence** that the root cause is GPT-OSS's mandatory reasoning step, which
narrows the practical choices to #1/#2/#4/#5.

---

## 6. Tackle plan (prioritized, validated against constraints)

**C1/C3/C4/C21 constraints:** all-local, $0 marginal, no vendor lock-in, swappable infra.
**R5 constraint:** S2 generator (Qwen) ≠ S4 classifier family. Depth/discipline/domains may
use a *third* family as long as it is not the generator's.

### P0 — Batch the depth-focused call (no model change, no accuracy change)
Depth is a 4-way forced choice answered in ~1 word. Batch 8–16 depth queries per GPT-OSS
call (mirroring `batch_cribs_classify`). Drops ~10 s/FB → ~1–2 s/FB. Also **remove `depth`
from the CRIBS batch prompt** (it is discarded and recomputed anyway). Expected ~25 s/FB →
~17 s/FB with zero accuracy risk.

### P0 — Route the one-word depth call to a fast non-reasoning model
`gemma-4-E4B-it-MLX-4bit` answers the depth question correctly in ~5 s with no reasoning
(validated above), and is a *different* family from both Qwen (generator) and gpt-oss
(classifier) — R5-clean. Keep gpt-oss for the harder discipline/domains/CRIBS call. This is
a **FrugalGPT-style cascade** (ref #5): cheap model for the easy 4-way task, expensive model
only for the hard task. A benchmark (`tools/benchmark_s4_classifiers.py`) must gate this swap
on ≥90% agreement (the existing `temp/kimii005.md` already predicts Qwen3.5-9B at ≥95%).

### P1 — Distill gpt-oss classification into a small model (ref #4)
Label a few hundred FBs with gpt-oss, fine-tune a 3B–4B non-reasoning model, run S4 at ~5 s/FB
end-to-end. Highest ceiling, highest effort; schedule post-T1.1.

### P1 — Enable MLX speculative decoding for gpt-oss (ref #2)
`MAXWELL_INFERENCE_BACKEND=mlx` path already claims 1.5–2×. Verify gpt-oss supports a draft
model in the local MLX stack before relying on it.

### P2 — Continuous batching (ref #1)
Only if OMLX/MLX exposes concurrent decode for a single large model; otherwise N/A on Apple
Silicon unified memory (already constrained at ~24 GB).

---

## 7. Recommendation

For the **T1.1 full run**, do **both P0 items** (batch depth + fast-model depth) — they are
low-risk, code-only, and drop S4 from ~25 s/FB toward ~15–17 s/FB (~142 h → re-measure under D2363; the merged call — not depth — is the real bottleneck). Defer
distillation and speculative decoding to T1.2. **Do not** silently swap the classifier back
to Phi-4-mini — that re-introduces BUG-053 hallucination risk and the 38% long-prompt depth
error that D2249 fixed.
