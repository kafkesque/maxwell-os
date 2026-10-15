# THE ENGINE VERDICT — swap, borrow, or configure

**Measured 2026-10-15. Answers block I. Supersedes nothing; it is the reasoning behind `config/decisions.yaml#D-3002`.**

## The question, stated exactly

Three answers were possible and the earlier session left them tangled:

1. **SWAP** — replace oMLX with Magnitude (or TensorFold) for some task.
2. **BORROW** — keep oMLX and obtain the candidate's advantage without swapping.
3. **ELSE** — neither, because the advantage is already present, or is a configuration question.

## What each engine actually is (READ, from its own README)

| | oMLX (jundot/omlx, installed) | magnitudedev/magnitude | ashhart/TensorFold |
|---|---|---|---|
| Backend | MLX (`mlx-lm` BatchGenerator) + its own fused kernels | its own kernels over `llama-cpp-rs` + `tilelang` (`.gitmodules`), autotuned per machine | Zig, Metal on Apple Silicon |
| Endpoints | OpenAI + Anthropic drop-in; **embeddings**; vision; audio | OpenAI-compatible `/inference/v1` **and** Anthropic `/inference/anthropic` on port 10100 | OpenAI chat/completions + Responses + Anthropic Messages on 8080 |
| Arbitrary local weights | **yes** — `model_dirs` (`~/.omlx/models`) | curated/popular families ("kernels written only for popular families") | experimental ("Living Weights") |
| Cache / prefill controls | **tiered KV cache (hot RAM + cold SSD)**, prefix sharing, CoW; memory guard tiers; prefill progress; `--paged-ssd-cache-dir` | prefill/decode settings documented, not a tiered SSD KV cache | `--parallel`, `--context`, `--no-thinking` |
| Embeddings | **yes** (this is how `bge-m3` is served) | no | no |
| NLI / classifier role | holds the S4 classifier slot today | no | no |

## VERDICT 1 — a swap is *impossible* for the pipeline's full role, and *unmeasured* for the generation role

- **Impossible, for the whole role.** The pipeline needs embeddings (S1.5 clustering) and the S4 classifier. Magnitude and TensorFold are **inference-only, text-generation** servers. They cannot hold those slots at all, so neither can replace oMLX. At best one could serve the *generation* slot beside oMLX.
- **Unmeasured, for that one slot.** Magnitude's headline is *"2x faster than Ollama"* — and **our incumbent is not Ollama**. The claim is aimed at a different baseline, so it says nothing about oMLX on this machine. Adopting an engine on a comparison to an engine we do not run is exactly the category error the standing rule forbids.

## VERDICT 2 — there is nothing to BORROW that oMLX lacks, for our model families

Read from oMLX's own upstream README:

- *"oMLX persists KV cache across a hot in-memory tier and cold SSD tier — even when context changes mid-conversation"* — the tiered cache is **already in the engine we run**.
- *"for GLM-5.2 the fused DSA prefill is roughly 30x faster with the kernels"* — oMLX **already ships fused/tuned kernels** for named families; that is the same class of artefact Magnitude autotunes.
- *"One-click benchmarking from the admin panel. Measures prefill (PP) and text generation (TG) tokens per second, with partial prefix cache hit testing"* — oMLX **already has the instrument** this project built by hand as `temp/prefill_bench_20261015.py`.

Magnitude's genuine differentiator is *autotuning for arbitrary families*. That only pays for a family oMLX has no kernels for — and every model we serve today is a family oMLX already serves. **Borrowing is therefore a non-question: there is no gap to close.**

## VERDICT 3 — the real wins are three CONFIGURATION levers, and one of them is already mis-set

Read from `~/.omlx/settings.json` (the live install, 0.7.0):

1. **`cache.enabled: false`** while upstream documents the tiered KV cache as its reason to exist, alongside `hot_cache_max_size: 8GB`, `ssd_cache_dir: null`. **F6/BUG-792 is a configuration question before it is an engine question.** ⚠️ Upstream's documented example path is literally `~/.omlx/cache` — the very directory the owner cleaned on 2026-10-15. Enabling the SSD tier there would mix KV blocks with a transient store; the declared fix is a **distinct** `ssd_cache_dir`.
2. **`memory_guard_tier: aggressive`** with 8 resident models. The bench's `agent_loop` reading (54.7 s against a 60 s budget) was taken while `adaptive_prefill_throttle` was evicting a resident model mid-request — **the margin is a residency artefact (BUG-803)**, not a model property.
3. **`scheduler.chunked_prefill: false`** — relevant to Qwen3.8-27B's prefill anomaly (BUG-793).

## VERDICT 4 — the harnesses in the question are CLIENTS, not alternatives

This resolves the part of the question that kept returning ("can oMLX, Codex, Claude Code, OpenClaw, Hermes, DeepSeek Harness, Pi be utilized?"). Read from oMLX upstream:

> *"Set up OpenClaw, OpenCode, Codex, Hermes Agent, Copilot, Pi, Mistral Vibe, and DeepSeek Harness directly from the admin dashboard with a single click."*

Every named harness is a **front-end that talks to a local OpenAI/Anthropic-compatible URL**. So:

- oMLX is the **server**; the others are **drivers** of the same server. They are interchangeable, which is exactly why none may be load-bearing (C21/C25, D-3001/D-3002).
- This is also the answer for parallelism (block III): parallel work comes from partitioning **files** and from `pipeline/parallel.py` subprocesses — not from running many harnesses against one engine. The **engine pool is the serial resource**; the bench caught it at 8 models / 46.88 GB against a 55 GB guard.
- For the intake (block II): any of them can *drive* a session; the intake itself must be a script + declared config + a receipt.

## What would change this verdict

`config/decisions.yaml#D-3002` stands. A candidate engine is admitted **only** by the T-131 preflight, into the `agent_probe` slot first, and only after three questions are answered **by measurement**, not by reading:

1. Can it serve **our exact model set** — in particular an arbitrary already-downloaded MLX directory — or only its own curated list?
2. Does it expose cache/prefill controls **comparable to `settings.json`**, or fewer?
3. Is the tuned artefact **reproducible offline** (no account, no vendor call) — C2/C4/C22?

Until those are measured, the honest reading is: **the engine is not our bottleneck; three configuration levers are.**

## Refused on evidence

- **`prism-ml/Ternary-Bonsai-2-27B-mlx-2bit`** — refused as a *download*: the card states this pack *"requires the loader bundled in `runtime/`"* and that *"Ordinary MLX loaders skip the activation transform"*, i.e. it needs the `PrismML-Eng/mlx` **fork**. oMLX runs stock `mlx-lm`; an 8.6 GB pack that cannot load is worth 0 GB.
- **A second engine installed today** — refused: it would add a second boot agent, a second port and a second model-format question while the incumbent's own cache tier sits switched off.
