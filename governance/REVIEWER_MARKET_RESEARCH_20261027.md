# Reviewer market research (D-3161) — is there a gemma-family reviewer that beats gpt-oss-20b under 14 GB?

**Date:** 2026-10-27 · **Question (owner):** is there a better reviewer than gpt-oss-20b in the gemma family — as light
as < 14 GB, as fast or faster, more accurate and reliable, and generally scoring higher on community benchmarks?

**Status of every number here.** This document separates three kinds of statement, and never dresses one as another
(D-3109/D-3036): **MEASURED** = produced on this device by a receipt in this repo; **CLAIM** = published by the
vendor on a model card, which is a hypothesis for this machine; **STRUCTURAL** = read from config/weights/engine
source, which is a fact but not a performance claim.

---

## 1. The criterion, stated mechanically before any candidate is ranked

A reviewer replaces gpt-oss-20b only if it passes **all** of:

| # | gate | source of truth |
|---|---|---|
| G1 | passes `reviewing_verdict_gate` — accuracy − baseline ≥ 0.15 AND false_approve ≤ 0.10, n ≥ 20 | `config/r5_review_gate.yaml`, `governance/r5_review_gate_bench.jsonl` |
| G2 | 4-bit weight footprint < 14 GB | `~/.omlx/models/<id>` after registration |
| G3 | latency per review item ≤ gpt-oss's MEASURED 8.9 s | `governance/model_eval_checkpoint.jsonl` |
| G4 | loadable by the SERVING engine (oMLX), not merely by a local Python env | `model_settings.json` + `/v1/models` |
| G5 | fits the memory-guard pool without evicting a working-set member | `/health → engine_pool` |

G1 is not negotiable and cannot be met by a vendor table. G4/G5 are where this stack has already been bitten, so they
are checked here **before** a 7–16 GB download is proposed.

## 2. The measured reference (this is the row to beat)

| model | footprint | rvv3 accuracy | margin over baseline | false_approve | false_reject | unparsed | median s/item | verdict |
|---|---|---|---|---|---|---|---|---|
| **gpt-oss-20b-MXFP4-Q8** | 11 GB | **0.9167** | **+0.4167** | **0.0000** | 0.0833 | 0 | 8.9 | **PASS — promoted (D-3168)** |
| gemma-4-E4B-it-MLX-4bit | 6.4 GB | 0.7083 | +0.2083 | 0.1250 | 0.1250 | 1 | 7.8 | REFUSED — approves 3 of 12 unambiguous defects |

MEASURED, current-fixture-only (`rvv3-*`, 24 whole scripts, 12 APPROVE-gold / 12 REJECT-gold, constant-answer
baseline exactly 0.5000). The interesting column is **false_approve**: the existing gemma does not lose on accuracy,
it loses on *disposition* — it approves defects. A replacement therefore has to fix a **calibration** failure, which
size alone does not guarantee.

**Cost context that reorders the whole question (MEASURED today, `governance/specdec_probe_receipt.jsonl`):** a
reviewer call is **prefill-bound on a dense 27B** — Qwen3.8-27B prefills at ~40–49 t/s, so a 1.7k-token script costs
≈36 s of prefill against ≈12 s of decode (75% prefill). gpt-oss-20b is a **20.9 B MoE with ~4 B active**, which is
why it reviews in 8.9 s. So the right shape for a reviewer here is **MoE with few active parameters**, and any
candidate should be judged on *active* parameters, not total footprint alone.

## 3. The gemma family, as the vendor states it (CLAIM — not evidence)

From the Gemma-4 model cards (`google/gemma-4-12B-it`, `…-26B-A4B-it`, `…-E4B-it` — one shared family table):

| benchmark | Gemma 4 31B | Gemma 4 26B A4B | Gemma 4 12B Unified | **Gemma 4 E4B** | Gemma 4 E2B | Gemma 3 27B |
|---|---|---|---|---|---|---|
| MMLU Pro | 85.2 | 82.6 | **77.2** | 69.4 | 60.0 | 67.6 |
| AIME 2026 (no tools) | 89.2 | 88.3 | **77.5** | 42.5 | 37.5 | 20.8 |
| LiveCodeBench v6 | 80.0 | 77.1 | **72.0** | 52.0 | 44.0 | 29.1 |
| Codeforces ELO | 2150 | 1718 | **1659** | 940 | 633 | 110 |
| GPQA Diamond | 84.3 | 82.3 | **78.8** | 58.6 | 43.4 | 42.4 |
| Tau2 (avg of 3) | 76.9 | 68.2 | **69.0** | 42.2 | 24.5 | 16.2 |

Read against the model this stack already refuses: the **12B Unified** is 7.8 points of MMLU-Pro, 20.2 points of
GPQA-Diamond and 20 points of LiveCodeBench above the **E4B** that failed the gate — on the vendor's own table, the
biggest accuracy step available inside the 14 GB budget.

## 4. Candidate register — every candidate classified with its reason (D-3038)

| candidate | 4-bit footprint (MEASURED from the repo's blob sizes) | arch | classification | reason (recorded so it cannot be re-proposed from memory) |
|---|---|---|---|---|
| `mlx-community/gemma-4-12B-it-qat-4bit` | **10.99 GB** | `gemma4_unified` | **ADAPT — highest-value candidate** | Only candidate that is inside 14 GB **and** materially above E4B on every vendor row (§3). QAT (quantisation-aware) weights are the closest thing to "4-bit without the loss". Costs 10.99 GB of a 14.9 GB pool headroom, so it fits without eviction. |
| `lmstudio-community/gemma-4-12B-it-MLX-4bit` | 6.74 GB | `gemma4_unified` | **ADAPT — same model, cheaper quant** | Prefer this one if the QAT variant fails G1 or G5: 6.74 GB leaves 8 GB of headroom. Same architecture gate as above. |
| `lmstudio-community/gemma-4-26B-A4B-it-QAT-MLX-4bit` | **15.61 GB** | `gemma4` | **SKIP (owner constraint + pool)** | Exceeds the owner's < 14 GB bound, and `/health` shows 41.0 GB in use against a 55.9 GB ceiling = **14.9 GB headroom**, so admitting it forces an eviction of a working-set model. Its MoE shape would be the fastest of the family — recorded so the trade-off is visible if the owner ever relaxes the bound. |
| `google/gemma-4-31B-it` / `google/gemma-3-27b-it` | ~16–17 GB / ~15 GB | `gemma4` | **SKIP** | Over the 14 GB bound; and dense 27B+ is exactly the prefill-bound shape that made the 27B reviewer the wrong choice (§2). |
| `google/gemma-4-E2B-it` (5.12 B) | ~3 GB | `gemma4` | **SKIP** | Strictly weaker than E4B on every vendor row (MMLU-Pro 60.0 vs 69.4), and E4B already fails G1. A smaller sibling of a failing reviewer is not a candidate. |
| `gemma-4-E4B-it-MLX-4bit` (incumbent fast tier) | 6.4 GB | `gemma4` | **REFERENCE** | MEASURED REFUSED on false_approve 0.1250. Stays as the fast-tier reviewer and as the R5 partner for a Qwen generator; never the deep tier. |
| NVIDIA/RedHat `NVFP4`, `FP8`, `AWQ`, `GPTQ` gemma derivatives | n/a | n/a | **SKIP (runtime-locked)** | NVFP4 targets Blackwell tensor cores and FP8 targets Hopper-class; AWQ/GPTQ are not loadable by MLX at all. These appear high in HF download rankings and are **not runnable on this device** — the exact trap a download-count ranking walks into. |
| `mlx-community/gemma-3-12b-it-qat-4bit` | ~7 GB | `gemma3` | **WATCH** | Previous-generation 12B; the vendor table shows Gemma 3 27B *below* Gemma 4 E4B on AIME (20.8 vs 42.5) and Tau2 (16.2 vs 42.2), so the family step matters more than the parameter count. Only measure it if the Gemma-4-12B path fails. |

**Nothing here is ADOPT yet.** ADOPT requires G1, and G1 requires a measurement on this device. The classification is
a *download order*, not a promotion.

## 5. The D-3161 comparison row (measured vs claimed, cell by cell)

| capability | reference implementation | its runtime + quant | claimed rate | OUR rate | our runtime + quant | delta | what would close it |
|---|---|---|---|---|---|---|---|
| cross-family code review of whole scripts | gpt-oss-20b-MXFP4-Q8 | MLX, MXFP4 (~4.5 bpw) | none claimed by vendor for this task | **0.9167 acc / 0.0 false_approve / 8.9 s per item** | MLX 0.32.3.dev8 (oMLX engine), 11 GB | baseline | — (this is the row to beat) |
| same, gemma family | gemma-4-E4B-it | MLX 4-bit | MMLU-Pro 69.4 (CLAIM) | **0.7083 acc / 0.125 false_approve / 7.8 s** | MLX, 6.4 GB | −0.208 accuracy, +0.125 false_approve | a bigger gemma: 12B Unified claims +7.8 MMLU-Pro, +20.2 GPQA |
| same, gemma-4 12B Unified | `gemma-4-12B-it-qat-4bit` | MLX 4-bit QAT | MMLU-Pro 77.2, GPQA 78.8, LCB 72.0 (CLAIM) | **none — not measured** | — | unknown | register + rvv3 run (~24 items × ≤10 s) + gate |
| decode throughput (context for the reviewer choice) | Qwen3.8-27B-MLX-4bit | MLX 4-bit | 16.15 t/s (llmrun.dev, ESTIMATE at 400 GB/s pin rate) | **7.54–7.58 t/s decode; 35–40 t/s prefill** | MLX 0.31.3 + oMLX 0.32.3.dev8, 15 GB | −53% vs estimate | physically bounded — see SPECULATIVE_DECODING_M1 §7 |

## 6. Conflicts that would otherwise become future tax

1. **Two MLX environments, two architecture surfaces (STRUCTURAL, verified today).** The serving engine is
   `/Applications/oMLX.app/…/python3.11/site-packages/` with **mlx_lm 0.32.3.dev8 + mlx_vlm 0.7.10**, whose
   `MODEL_REMAPPING` includes `gemma4_unified → gemma4` and which ships `mlx_vlm/models/gemma4_unified`. The repo's
   in-process tools run on **miniforge `mlx_lm` 0.31.3, no mlx-vlm**, which has **no such remap**. Consequence:
   `gemma-4-12B-it` is **servable by oMLX** but **not loadable in-process** — an in-process benchmark would fail with
   `ValueError: Model type gemma4_unified not supported` and that failure would be misread as "the model is bad"
   (BUG-257's shape). Any measurement of this candidate MUST go through the server, or through an aligned env.
2. **The pool has a budget, and it is 78% spent.** `/health` MEASURED today: `model_count 16, loaded_count 4,
   current_model_memory 40,987,864,821 B (41.0 GB), final_ceiling 55,901,503,640 B (55.9 GB)` → **14.9 GB free**.
   A 10.99 GB reviewer fits; a 15.61 GB one does not. Registering a candidate without this arithmetic is how a
   "harmless" download starts evicting the working set mid-run (BUG-255/BUG-803).
3. **Fixture-author confound (methodological, unresolved).** The `rvv3` fixture and the scoped reviewer clause were
   both authored by this agent, and the same agent then promotes on the result. That is a real self-grading risk, and
   the fix is a **held-out fixture authored from a different source** (e.g. scripts that already carry an owner
   verdict in the repo), not a second run of the same one.
4. **No re-measure channel.** `tools/model_eval_suite.py` accepts only `--models/--models-file/--suites/--limit`;
   `_done_keys()` skips any `(model, suite, id)` already present without an error, so an identical second run reports
   "0 new results" and looks like a pass while measuring nothing. Stability therefore cannot be re-measured
   mechanically today → registered as **BUG-1041**, not worked around with a second truth.
5. **A larger reviewer is not free at the call site.** Even a passing 12B reviewer pays ~1.6× gpt-oss's per-token
   weight reads on decode and is dense, so its prefill on a 2k-token script will be far worse than gpt-oss's MoE
   prefill. G3 (≤8.9 s/item) is therefore the gate most likely to reject it, and it must be measured, not assumed.

## 7. CLARIFICATION (owner question, 2026-10-27) — nothing gemma is in the R5 seat, and this register never applied one

**Q: "have we used gemma-4-12B-it so far for the R5 reviewer, or not?" — NO, on all three readings.**
1. The `mlx-community/gemma-4-12B-it-qat-4bit` and `lmstudio-community/gemma-4-12B-it-MLX-4bit` rows in §3 are
   **ADAPT**, i.e. registered with a reason and left unpromoted. Neither is downloaded, neither is registered in
   `~/.omlx/model_settings.json`, neither has a `reviewing_verdict_gate` run. `ls ~/.omlx/models/` at 2026-10-27 has
   exactly one gemma: `gemma-4-E4B-it-MLX-4bit`.
2. The **E4B** that IS on disk was measured and REFUSED: `pass=False n=24 acc=0.7083 margin=+0.2083
   false_approve=0.1250` — reason `false_approve=0.1250 > 0.10`. It is not in the seat either.
3. The seat is `gpt-oss-20b-MXFP4-Q8`: `pass=True n=24 acc=0.9167 margin=+0.4167 false_approve=0.0000
   false_reject=0.0833`. It is the only model that has ever passed the gate on the current fixture.

**So "don't advise what we already applied" is answered: nothing gemma was applied.** What follows is the full
in-family sweep with the classification rule of D-3038 (a rejected candidate is recorded WITH its reason).

### 7.1 Every gemma that could conceivably take the seat, classified
| candidate | footprint (MEASURED from repo blobs) | gate status | class | reason |
|---|---|---|---|---|
| `google/gemma-4-12B-it` (base) → `mlx-community/gemma-4-12B-it-qat-4bit` | 10.99 GB | not run | **ADAPT** | only in-14 GB gemma claiming a material step over the refused E4B (+7.8 MMLU-Pro, +20.2 GPQA-D, +20.0 LiveCodeBench, vendor CLAIMS); arch `gemma4_unified` |
| `lmstudio-community/gemma-4-12B-it-MLX-4bit` | 6.74 GB | not run | **ADAPT** | same model, 4.25 GB cheaper quant → the cheaper way to run the SAME gate test; try this one FIRST |
| `google/gemma-4-12B-it-qat-w4a16-ct` | not measured this sitting | not run | **WATCH** | w4a16 weights-only quant of the same 12B; a second format to test only if the first two fail |
| `google/gemma-4-12B-it-qat-q4_0-gguf` | not measured this sitting | not run | **SKIP (runtime)** | a GGUF — needs llama.cpp; this host measured GGUF losing to MLX on every axis (5.31 vs 9.3 t/s) |
| `google/gemma-4-26B-A4B-it` (MoE, 26B total / 4B active) | 15.61 GB | not run | **SKIP** | over the 14 GB owner bound AND over the MEASURED pool headroom (41.0 GB in use of 55.9 GB ceiling = 14.9 GB); the right *shape* for prefill-bound work, the wrong size for this pool |
| `google/gemma-4-31B-it` | ~62 GB bf16 class | not run | **SKIP** | over the bound by 4x; wrong (dense-large) prefill shape |
| `gemma-3-27b-it` + AWQ/int4 derivatives | 15+ GB | not run | **SKIP** | over the bound, dense 27B = the shape that made the 27B reviewer wrong by construction, and AWQ is not MLX-loadable |
| `google/gemma-4-E2B-it` | ~2.9 GB | not run | **SKIP** | strictly weaker than the E4B this OS REFUSES on every vendor row |
| NVFP4 / FP8 / AWQ / GPTQ gemma derivatives (`nvidia/Gemma-4-26B-A4B-NVFP4`, `RedHatAI/…-FP8-dynamic`, `QuantTrio/…-AWQ`) | n/a | not run | **SKIP** | runtime-locked to Blackwell/Hopper (NVFP4) or unloadable by MLX (AWQ/GPTQ) — high download counts, zero applicability here |
| `google/gemma-4-E4B-it` (on disk) | 6.4 GB | **REFUSED** | **SKIP** | `false_approve=0.1250 > 0.10` on the current fixture; not revisitable without a new fixture |
| `mlx-community/gemma-3-12b-it-qat-4bit` | not measured this sitting | not run | **WATCH** | older family; only worth a run if the 12B-4 fails and a *cheaper* candidate is needed |
| ADOPT | — | — | **NONE** | a gemma may only be promoted by a PASSING `reviewing_verdict_gate` run on this device |

### 7.2 The honest bottom line on "better than gpt-oss"
There is **no published evidence that any gemma beats gpt-oss-20b at THIS gate**, because this gate is local, small
(n=24) and source-scoped: it measures a specific failure mode (`false_approve`) on a specific fixture. Vendor
benchmark tables are CLAIMS (D-3161) and the only gemma in that table inside the 14 GB bound that claims a material
step is the 12B Unified. So the correct statement is not "gemma is better" or "gpt-oss is better" — it is:

- **UNMEASURED**: the 6.74 GB `gemma-4-12B-it-MLX-4bit`. It is the single highest-value open measurement in the
  reviewer question, it costs one download and one gate run, and it MUST be run through the serving engine (the
  `gemma4_unified` mapping exists in the engine's mlx_lm 0.32.3.dev8 + mlx_vlm 0.7.10 and NOT in the repo's 0.31.3,
  so an in-process run fails as "Model type gemma4_unified not supported" — a harness artifact, not a model fact).
- **BLOCKED**: promoting ANY second reviewer needs a held-out fixture (the fixture-author confound in §6.3) and a
  re-measure channel (BUG-1041). Both are open, and neither is resolved by finding a better model.
- **A LARGER REVIEWER IS NOT FREE AT THE CALL SITE**: G3 (<= 8.9 s/item, gpt-oss's MEASURED rate) is the gate a 12B
  is most likely to fail, because prefill on this chip is ~52 t/s and a cold reviewer call is ~75% prefill.
