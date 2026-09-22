# Market Research — Inference Engine Evaluation vs oMLX (2026-09-22)

**Scope:** Senior inference/RAG-engineer evaluation of three candidate inference runtimes against the
incumbent oMLX 0.7, to decide **swap / adapt / integrate / reference / reject** for Maxwell OS.

**Candidates:**
1. `drumih/turbo-fieldfare` — Swift+Metal single-model runtime (Gemma 4 26B-A4B in ~2 GB RAM)
2. `ARahim3/mlx-dspark` — MLX library for DSpark/DFlash lossless speculative decoding
3. `incoai/splash` — M3+ local inference engine ("built around the model")

**Hardware anchor (unchanged):** MacBookPro18,2 · Apple **M1 Max** · 64 GB unified · 400 GB/s ·
10-core (8P+2E) · macOS 27.0 Golden Gate (26A428). M1 Max is **Metal 3** hardware.

> Do not restate a config value here — cite the path. Live oMLX state: `~/.omlx/settings.json`
> (0.7.0.dev4, `:11435`, cache thrash flags), goose provider `~/.config/goose/custom_providers/maxwell_omlx.json`.

---

## TL;DR verdict

| Candidate | Verdict | One-line reason |
|---|---|---|
| oMLX 0.7 (incumbent) | **KEEP** | Only engine that runs on M1 Max, serves Maxwell's real model catalog, and already ships lossless speculative decode (Lightning MTP). |
| `incoai/splash` | **REJECT** | Hard `M3 or newer` + Metal 4 gate excludes M1 Max; proprietary model package format (C2); "no config" (C12/C21/C24); 2-model catalog. |
| `drumih/turbo-fieldfare` | **REJECT** (as engine) / **REFERENCE** (experiment log) | Single model (Gemma 4 26B-A4B); its SSD-paging value prop is the D2460 thrash anti-pattern on 64 GB. |
| `ARahim3/mlx-dspark` | **REFERENCE / WATCH** | Same MLX foundation; speculative-decoding parity with oMLX MTP; no drafter for our generator; valuable self-calibration methodology. |

**No swap.** **No full integration.** One reference (turbo-fieldfare), one reference + conditional
watch (mlx-dspark). The near-term lever is unchanged and already planned: **D-293** (enable oMLX
Lightning MTP for Qwen3-Coder S2).

---

## The incumbent baseline — what oMLX 0.7 already provides

Before comparing, the floor to beat:

- **Foundation:** Apple MLX 0.32.2 / MLX-LM 0.31.3. Runs on M1 Max (Metal 3).
- **Catalog:** serves Maxwell's actual lineup — Qwen3-Coder-30B-A3B (S2 generator, heaviest stage),
  gpt-oss-20B-MXFP4-Q8 (S4 classifier), Phi-4-mini-instruct-8bit (S2 probe), gemma-4-E4B (review),
  Ornith-1.5-9B — plus bge-m3 embeddings via Ollama (orthogonal to the text engines).
- **Lossless speculative decode already exists:** Lightning MTP, +34–58% decode on
  Qwen3/DeepSeek/GLM, lossless at temp=0.0 (D-293 enables it for S2).
- **API + config surface:** OpenAI-compatible on `:11435`, already wired into goose
  `maxwell_omlx` provider; configurable via `settings.json` / `model_settings.json` — satisfies
  C12 (config-first), C21 (swappable), C24 (hardware-adaptive), C28 (quality-tiered).

---

## 1. `incoai/splash` — REJECT

**What it is.** A local inference engine that ships fused Metal kernels + a per-model DFlash 2 draft,
compiled for exact model shapes, with a memory plan computed at startup. Claims 2× decode on
Qwen3.8-27B vs the next-fastest engine (measured on an **M5 Pro**, 48 GB).

**Why reject — four independent, each sufficient reasons:**

1. **Hard hardware gate excludes M1 Max.** README: *"Apple M3 or newer, macOS 26.4 or later"*;
   DEVELOPMENT.md requires *"a Metal 4 compiler with `uint4b_format` tensor support."* M1 Max is
   Metal 3 → Splash will not run. This is dispositive before any feature analysis.
2. **Vendor lock-in (C2).** *"Plain MLX or Transformers checkpoints do not work"* — models must be
   converted to a proprietary Splash package format. Violates C2 (no vendor lock-in), C4 (open
   formats), C21 (swappable infra).
3. **No configuration (C12/C21/C24/C28).** *"There is no config file … nothing to configure."*
   Directly contradicts Maxwell's config-first rule (C12) and hardware-adaptive / quality-tiered
   requirements. Closed kernel agent-generated shapes = opaque, unswappable.
4. **Wrong catalog.** Serves exactly two models: `Qwen3.8-27B` and `Qwen3.6-35B-A3B`. It does not
   serve Qwen3-Coder-30B-A3B (S2), gpt-oss-20B (S4), Phi-4-mini (S2), gemma-4-E4B, or Ornith-9B.

**Note:** Splash's DFlash 2 drafter lineage is shared with `mlx-dspark` (incoai publishes
`incoai/Qwen3.8-27B-DFlash2`). Splash is the "batteries-included M3+ engine" packaging of the same
lossless speculative-decoding idea oMLX already ships as MTP.

---

## 2. `drumih/turbo-fieldfare` — REJECT (engine) / REFERENCE (experiment log)

**What it is.** A Swift 6.2 + Metal 4 runtime for **one model**: Gemma 4 26B-A4B (MoE, ~3.88B active
per token). Keeps the 1.35 GB shared core + FP16 KV in RAM, streams routed experts from SSD per
token → runs a 26B model in ~2 GB. Apache-2.0. 6.8k stars. Curated inventory of **103 measured
experiments** across kernels/caching/I-O/prefill/decode.

**Why reject as an engine:**
- **Model-specific, not a general engine.** It is explicitly *"model-specific rather than a wrapper
  around MLX or llama.cpp."* It cannot serve Qwen3-Coder, gpt-oss, Phi-4-mini, or anything Maxwell
  runs. It is not a swap candidate for a 5-model pipeline.
- **Its core innovation is irrelevant — and the exact anti-pattern we must avoid.** SSD-paging MoE
  experts is a *low-RAM* technique (8 GB Macs). Maxwell has 64 GB; the 14.3 GB model fits in RAM.
  Worse, this is precisely the D2460 failure mode already diagnosed on Maxwell: SSD-backed cache
  thrash crashed decode to ~4–7 tok/s. `assert_omlx_no_cache` exists because of this.
- **Thin integration surface.** Experimental loopback OpenAI server only; no goose/tool-calling
  path; no embedding, no classifier, no grammar support.
- **M1 caveat.** Text-only inference *does* run on M1 (image tower needs M2+), so hardware is not
  the blocker — the single-model catalog is.

**What to reference (cheap, high-signal):** the `docs/experiments/EXPERIMENT_INVENTORY.md` + the
benchmark/optimization-journey docs are a genuinely good public record of MoE expert residency,
Metal kernel fusion, prefill/decode split, and I/O scheduling. Worth citing as design reference for
any future MoE-kernel work — but nothing to adopt on 64 GB M1 Max.

---

## 3. `ARahim3/mlx-dspark` — REFERENCE / WATCH (not swap, not integrate)

**What it is.** MIT, Python ≥3.10, `pip install mlx-dspark` (installs mlx ≥0.32.0). Ports DeepSeek
**DSpark** (EAGLE-family semi-autoregressive) and z-lab **DFlash** (block diffusion) speculative
decoding natively on MLX, plus a stdlib OpenAI **and** Anthropic API server on one port. Lossless by
construction (target verifies every drafted token). Claims 1.1×–4.3× speedups across a registry of
~16 consumer targets, measured on an M4 Pro.

**Why not swap:** it is **not a full serving engine** — it is a *drafter library + thin server on
top of MLX*, i.e. the same foundation oMLX already uses. It has no parity with oMLX's multi-model
management, settings surface, grammar/guided decoding, or the goose integration Maxwell depends on.

**Why not integrate now:**
- **Drafter coverage misses our models.** The auto-resolve registry covers Qwen3-8B/14B, Qwen3.8-27B,
  Qwen3.6-35B-A3B, Gemma-4, Ornith-1.0, Nemotron, LFM2.5, Muse-Glimmer, MiniCPM5, Nanbeige4.2,
  ternary Bonsai — **not Qwen3-Coder-30B-A3B** (our S2 generator), **not gpt-oss-20B** (S4),
  **not Phi-4-mini**. `--mode auto` gives drafter-free *lookup* speculation against any model, but
  that is a weaker form of the lossless MTP oMLX already applies to the actual Qwen3 family.
- **Redundant capability.** Lossless speculative decode is already in oMLX 0.7 (Lightning MTP,
  D-293). Adding a second Python MLX drafter stack = a second dependency, a second tuning surface,
  for a capability we already own. C5 (zero bloat) argues against.

**What to reference (the one genuinely valuable thing):** its **self-calibration methodology** —
*"with no `--max-draft`, mlx-dspark measures **your** machine's verify/drafter cost curves once
(~5 s, cached per model+quant+mlx version) and derives the draft cap from them — an M1 or an M5 gets
its own optimum."* This is exactly the right pattern for Maxwell's D-293 MTP enablement: **do not
hardcode a draft cap for this M1 Max; derive it from this machine's measured bandwidth.** C12-encode
the cap as a derived value, not a literal.

**Conditional watch:** if a published DSpark/DFlash drafter ships for Qwen3-Coder-30B-A3B or
gpt-oss-20B, re-open the A/B (lossless drafters are drop-in speed, temp=0.0-safe). Until then, no
action.

---

## Recommendation (strategic, sequenced)

1. **KEEP oMLX** as the serving engine. No swap is justified: every candidate either cannot run on
   M1 Max (splash), serves the wrong model (turbo-fieldfare), or is a redundant sub-component of the
   same MLX stack (mlx-dspark).
2. **D-293 (unchanged) is the highest-leverage move.** Enable oMLX Lightning MTP for Qwen3-Coder
   S2 — this captures the same lossless-speculative-decode upside all three candidates promise,
   on the engine that already serves Maxwell's models.
3. **Adopt mlx-dspark's self-calibration idea into the MTP tuning step.** Measure this M1 Max's
   verify/drafter cost curve; derive the draft cap; record it in `config/pipeline_config.yaml`
   (C12 — derived value, never a hardcoded literal).
4. **Reference** turbo-fieldfare's 103-experiment inventory for MoE/Metal kernel design notes only.
5. **Reject** splash outright (hardware + C2 + no-config); **do not** re-evaluate unless the M1 Max
   is replaced by an M3+ machine, at which point re-check on C2/C12 grounds alone.

**Bottom line:** the three candidates validate that *lossless speculative decoding* is the dominant
inference-speed lever for 2026 Apple-silicon runtimes — and oMLX 0.7 already has it (MTP). Maxwell
should take the technique, not the engines.
