# llmrun.dev "16 t/s" for Qwen3.8-27B on M1 Max — ROOT CAUSE (corrected)

**Date:** 2026-10-27
**Status:** RESOLVED — this supersedes the earlier half-conclusion that "16.1 is GB, not t/s,
and the t/s figures are for datacenter GPUs". That was WRONG and is corrected here.

## The user's claim was correct

The page https://llmrun.dev/model/qwen-qwen3-8-27b#run shows a "~16" tok/s chip next to
**"MacBook Pro 16\" M1 Max (64 GB)"** (and "Mac Studio M1 Max (64 GB)"). The 16 t/s figure IS
attributed to the M1 Max — not to a datacenter GPU. Read from the page source, verbatim:

```
<span ...>MacBook Pro 16" M1 Max (64 GB)</span>
<span class="font-mono tabular-nums ...">~<!-- -->16</span>
```

## The precise mechanism (read from the page's own formula)

The page states its speed model explicitly:

> `tok/s = (bandwidth GB/s ÷ model GB) × efficiency`
> Example: NVIDIA B200 → 8000 ÷ 17.4 × 0.65 = ~299 tok/s

Plug in the M1 Max and the IQ4_XS quant for Qwen3.8-27B:

- M1 Max theoretical bandwidth = **400 GB/s** (Apple's spec-sheet peak, from the page's device row)
- IQ4_XS model footprint = **16.1 GB** (`needGb: 16.1`; `fileSizeGb: 14.93`, `vramRequiredGb: 15.68`)
- efficiency = **0.65** (the SAME constant used for the B200 example — datacenter-HBM-calibrated)

```
400 GB/s ÷ 16.1 GB × 0.65 = 16.15  →  ~16 t/s
```

So the "16.1" appears twice and is causally linked: 16.1 **GB** is the model size, and 16.1 **t/s**
is what the formula produces FROM that size. They are not a coincidence and neither is a misread —
but the t/s is a THEORETICAL ESTIMATE, not a measurement.

## Why this host measures ~9 t/s, not 16

The estimate rests on two constants that both break on Apple Silicon:

| constant | llmrun.dev assumes | reality on this M1 Max |
|---|---|---|
| bandwidth | 400 GB/s (theoretical peak) | ~240–260 GB/s sustained is the realistic ceiling; MLX/Metal decode achieves far less |
| efficiency | 0.65 (HBM datacenter-tuned) | MLX decode of a dense 27B is ~0.35 |

Empirical check, from this host's OWN measurement (governance/GGUF_MLX_AB_20261027.md):

- MLX 4-bit, 15 GiB, **9.3 t/s pure decode** → effective bandwidth = 9.3 × 15 = **~140 GB/s**
  → effective efficiency = 140 / 400 = **0.35** (vs assumed 0.65)
- GGUF Q4_K_M, 15.32 GiB, **5.31 t/s** → effective bandwidth = **~81 GB/s** → efficiency **0.20**

The page's own caveat ("Real-world results typically within ±20%") understates this gap: 16 t/s
±20% = 12.8–19.2 t/s, but the measured value is 9.3 t/s — a 42% shortfall, because the 0.65
efficiency and 400 GB/s peak are simply wrong for Apple Silicon's Metal/MLX decode path on a dense
27B model.

## Conclusion

- **There is no hardware fault and no configuration fault.** 9.3 t/s is the correct, measured
  decode rate for Qwen3.8-27B (dense, 4-bit) on this MacBook Pro 18,2 (M1 Max, 64 GB).
- The "16 t/s" is `400 ÷ 16.1 × 0.65`, a bandwidth-arithmetic estimate that treats M1 Max like a
  datacenter GPU (peak bandwidth + HBM efficiency). It does not reproduce on device (D-3036:
  vendor number = hypothesis; device-matched receipt = 9.3 t/s).
- This closes the loop on BUG-1033 / D-3164: the earlier "16.1 is GB, not t/s" framing was the
  wrong half. Both "16.1 GB" and "~16 t/s" are on the page; the t/s is derived FROM the GB via the
  formula, and it is an estimate that overstates reality by ~1.7×.

## Receipt

- Page source: https://llmrun.dev/model/qwen-qwen3-8-27b (formula + "~16" chip, fetched 2026-10-27)
- Device rows: `macbook-pro-16-m1-max-64gb` → `["Apple",64,60.5,400,20.8,"M1 Max","laptop"]`
  (bandwidth = 400)
- Quant table (IQ4_XS): `vramRequiredGb 15.68, needGb 16.1, fileSizeGb 14.93`
- This host's measurement: governance/GGUF_MLX_AB_20261027.md (MLX 4-bit 8.98 t/s incl TTFT /
  ≈9.3 pure decode; GGUF Q4_K_M 5.31 t/s)

---

# Addendum 2: WHY decode efficiency is ~0.35–0.41, and why 1:1 is impossible

The follow-up question — "400 GB/s, why only ~9 t/s, why is efficiency so bad, why not 1:1" —
is answered by a device-matched study on IDENTICAL hardware (rajeeja/local-llm-bench-m1max,
Apple M1 Max / 64 GB / 32-core GPU / 512-bit bus — the same chip as this host).

## The two-bandwidth fact (measured, not theorised)

1. **400 GB/s is the PIN RATE — physically unreachable.** A Metal streaming-read sweep
   (`stream_bw.py`) on this chip measured **340 GB/s** (336.3 and 343.3 across two runs). That
   340 is the real ceiling: ~85% of the 400 marketing number. Any estimate that divides by 400
   (as llmrun.dev does) is already ~18% optimistic before efficiency is even considered.
2. **LLM decode extracts ~36–41% of that 340**, i.e. **123–140 GB/s effective**, on EVERY model
   tested — four architectures spanning a 7× size range:

   | model | decode t/s | bytes/token | achieved GB/s | % of 340 |
   |---|---|---|---|---|
   | Muse Glimmer 30B | 6.55 | 18.88 GB | 123.6 | 36.4% |
   | Gemma 4 31B | 6.36 | 19.58 GB | 124.5 | 36.6% |
   | Qwen3-32B | 7.02 | 19.32 GB | 135.7 | 39.9% |
   | Gemma 3n E4B | 50.45 | 2.77 GB | 139.8 | 41.1% |

   The shorthand that falls out: `tok/s ≈ (bandwidth × 0.36) ÷ model_GB`.

## This host is NOT underperforming — it is at the top of the measured range

Our MLX 4-bit decode (9.3 t/s, 15 GiB → **140 GB/s effective**) is **41% of the 340 GB/s
ceiling** — the TOP of rajeeja's measured 36–41% band. MLX is doing as well as the best
llama.cpp Metal results on this chip. There is nothing "taming" it: no throttle, no config
fault. 140 GB/s IS the practical decode ceiling for a dense 4-bit model on M1 Max.

Check against the shorthand: `(400 × 0.36) ÷ 15 = 9.6 t/s` (vs our measured 9.3) — and against
the 340 ceiling: `(340 × 0.41) ÷ 15 = 9.3 t/s`. Exact match.

## Why efficiency cannot be 1.0 (three independent reasons)

1. **The pin rate is unreachable.** 400 → 340 (85%) is the hardware limit even for a pure
   memcpy-style stream. No LLM workload beats it.
2. **Decode is not a pure stream.** Per token it also: dequantises 4-bit→fp16 (ALU work per
   byte), computes attention (softmax over the KV cache), reads the KV cache (grows with
   context), and reads one embedding row. Those compete with the weight stream, so the 85%
   drops to ~40%.
3. **This ~40% is a stable hardware constant**, not a software defect — identical across four
   architectures and two runtimes (llama.cpp Metal and MLX).

## What WOULD actually raise tokens/s (in order of leverage)

1. **Speculative decoding** (draft with a small model, verify with the big one) — 2–3×
   wall-clock tokens/s, the only lever that beats the bandwidth wall for a fixed model.
2. **Fewer bytes/token** — smaller quant (IQ3_XXS 12 GB vs Q4 15 GB ≈ 1.25×) or an MoE model
   (fewer active params: gpt-oss-20b hits 43.88 t/s because ~3.6B active, not 27B dense).
3. **Batch decode** — raises throughput (many sequences) but not single-stream latency.

A kernel tweak will NOT turn 9.3 → 16 t/s for a dense 27B Q4 on this chip: 16 t/s would need
260 GB/s effective (0.65 × 400), which exceeds the 340 GB/s measured ceiling and is 1.6× the
real ~0.40 decode efficiency. The llmrun.dev "16 t/s" is simply a wrong-efficiency estimate.
