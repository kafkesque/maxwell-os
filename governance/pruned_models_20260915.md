# Pruned redundant models — 2026-09-15

Rationale: benchmark-only artifacts, zero production role (verified via grep of
config/ + pipeline/ + scripts/ + tools/). Re-downloadable from HF if ever needed.

| Model | HF source | Disk freed |
|---|---|---|
| gemma-4-31B-it-MLX-8bit | lmstudio-community | ~57 GB |
| gpt-oss-20b-MXFP4-Q4 | mlx-community | ~10 GB |
| Qwen3.5-9B-4bit | mlx-community | ~5.6 GB |

Production matrix after prune (5 models, all assigned):
Qwen3-Coder-30B-A3B (generator), Qwen3.8-27B (reliable pair), gpt-oss-20b-MXFP4-Q8
(classifier, retiring), gemma-4-E4B (reviewer), Phi-4-mini (probe/gate).

## Follow-up — oMLX symlink cleanup (2026-09-15 13:53)

The HF cache deletion (above) removed the actual weights, but `~/.omlx/models/`
still held **symlinks** into the deleted HF snapshots — so the oMLX UI kept
listing all three. Cleaned:
- `~/.omlx/models/gemma-4-31B-it-MLX-8bit`  (broken symlink → deleted)
- `~/.omlx/models/gpt-oss-20b-MXFP4-Q4`     (broken symlink → deleted)
- `~/.omlx/models/Qwen3.5-9B-4bit`          (already removed)

Verify: `find ~ -iname "*gemma-4-31B*" -o -iname "*gpt-oss-20b-MXFP4-Q4*" -o -iname "*Qwen3.5-9B*"` → no non-lock hits. Fully pruned.

## Prune #2 — 2026-09-15 17:05

| Model | Disk freed | Evidence | Reason |
|---|---|---|---|
| `DeepSeek-R1-0528-Qwen3-8B-4bit` (`qwen3`, 4.3 GB) | ~4.3 GB | ARM-4 in-process: discipline_acc **0.000**, only **4/30** rows parsed JSON, S2 extraction **HUNG** on thinking traces → killed | Fails every axis; also `qwen3` architecture, so it adds zero R5 family diversity. Repo is delisted from HF Hub so `hf cache rm` could not resolve it — removed directly from the cache dir. |

**Remaining under review — NOT deleted, pending explicit sign-off:**
- `Ornith-1.5-35B-A3B-OptiQ-4bit-REAP-19B` (13 GB) — Pareto-dominated by gemma-4-12B (same 1.00 capability, −20 pp discipline, half the size); also `qwen3_5_moe`.
- `Phi-4-mini-instruct-8bit` (5.4 GB) — weakest classifier (0.433/0.324) and cannot abstain; replace with `granite-4.2-8b` to preserve the R5 triad Qwen≠Phi≠Gemma.

**oMLX GUI visibility fix (2026-09-15 17:03):** oMLX only scans `~/.omlx/models/` (settings.json `model_dirs`), never the HF cache. ARM-4 downloads went to the HF cache and were never linked in, so they were invisible in the GUI. Symlinked `gemma-4-12B-it-qat-OptiQ-4bit` and `Ornith-1.5-9B-OptiQ-4bit` into `~/.omlx/models/`; removed the stray empty `~/.omlx/models/mlx-community/` dir.

## Prune #3 — 2026-09-16 15:20 (D-2637 portfolio consolidation)

| Model | Disk freed | Evidence | Reason |
|---|---|---|---|
| `granite-4.2-8b-MLX-8bit` (`granite`, 9.13 GB) | ~9.1 GB | ALL **0.353** (last of 9); delegation 0.17, hardcode 0.25, humaneval 0.24, mbpp 0.40, ifeval 0.56, toolcalling 0.50 | Last or near-last on **every** axis. Sole rationale was R5 family diversity, but after removal we still hold three non-Qwen families (gemma4, gpt_oss, phi3). No role in the final map. |
| `gemma-4-12B-it-qat-OptiQ-4bit` (`gemma4_unified`, 8.70 GB) | ~8.7 GB | ALL **0.448**; toolcalling **0.00**; humaneval 0.36; **40.5 s/call** median (worst by 4x) | No role its own family sibling does not do better and ~24x faster (gemma-4-E4B: delegation 1.00 vs 0.50, ifeval 1.00 vs 0.64). Family already represented. |

**Total freed: ~17.8 GB** (df-verified: 48 GB -> 66 GB available).

Measurement note (self-correction): the deletion script's `dirsize()` reported 36.77 GB because
`os.path.getsize()` follows the snapshot symlinks into `blobs/`, so every blob was counted twice
(once as a blob, once via its snapshot link). The registry's `estimated_size` (9.13 + 8.70) was the
accurate figure all along; `df` confirms ~18 GB. Reported here as 17.8 GB, not 36.77 GB.

Method follows the established precedent: remove the `~/.omlx/models/` symlink first (so oMLX prunes
the registry entry), then `rm -rf` the HF cache dir. `pipeline/safe_delete.py` governs *pipeline output*
(R-D410), not model weights. No live process referenced either model at deletion time (BUG-255 discipline).

Files updated: `governance/eval_models.txt` (granite and gemma-4-12B removed).

**Portfolio after Prune #3 (8 models, pending the Ornith A/B loser):**
Qwen3-Coder-30B-A3B (pinned), Qwen3.8-27B (pinned, +OptiQ under A/B), Ornith-REAP-19B (tool calling),
gpt-oss-20b-Q8 (S4 classifier), gemma-4-E4B (depth/reviewer/R5-gemma), Ornith-1.5-9B x2 (A/B in flight,
keep one), Phi-4-mini (S2 fast probe).

## Prune #4 — 2026-09-16 17:05 (D-2637)

| Model | Disk freed | Evidence | Reason |
|---|---|---|---|
| `Ornith-1.5-9B-OptiQ-4bit` (`qwen3_5`, 6.94 GB) | df +5 GB (registry estimate 6.94 GB) | Lost the head-to-head A/B vs the 8-bit: composite **0.642 vs 0.682**, coding composite **0.677 vs 0.773**, delegation **0.667 vs 1.00**. Won only reviewing (−0.167 for the 8-bit), stability (−0.100), mbpp (−0.040), math500 (−0.040). | Uniform-4/8-bit mixed quantisation lost to uniform 8-bit on every decision-relevant axis; the 8-bit is kept as the lightweight coder. Method: symlink removed first, then HF cache dir. No live process referenced it. |

**Portfolio after Prune #4 (7 models — the target stack):**
Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (pinned S2 generator), Qwen3.8-27B-MLX-4bit (pinned decider),
Ornith-1.5-35B-A3B-REAP-19B (tool agent), gpt-oss-20b-MXFP4-Q8 (S4 classifier incumbent),
gemma-4-E4B-it-MLX-4bit (depth/fast review), Ornith-1.5-9B-MLX-8bit (light coder),
Phi-4-mini-instruct-8bit (S2 probe).

Total freed across Prunes #3+#4: **~22.8 GB** (df 48 GB -> 71 GB available).

## Prune #5 — Qwen3.8-27B-OptiQ-4bit (mixed 4/8-bit, 20.68 GB) — RETIRED BY MEASUREMENT 2026-09-16

**Gate:** [[G3]] (the Qwen3.8 quant decision, D-2637). Resolved on 128 of 251 voting rows — enough to
close early, because the failure was not marginal.

| | uniform 4-bit (KEPT) | OptiQ 4/8-bit (RETIRED) |
|---|---|---|
| voting accuracy, same 128 rows | **0.727** | 0.445 (wins 5, loses 41, ties 82) |
| output-contract failures | **0 / 128** | **40 / 128 = 31%** (`detail='no json'`) |
| median latency, voting | **16.5 s/row** | 75.9 s/row (4.6x) |
| disk | 16.08 GB | 20.68 GB (+28.6%) |

**Root cause of the failures (diagnosed, not assumed):** OptiQ does not answer directly — its stored
predictions open with reasoning prose ("We need answer user's request. Need classify principle
into...") and the JSON that follows is cut mid-string. The eval harness sends `max_tokens=512` and no
thinking-control parameter, so a model that reasons first runs out of budget before it emits the
object the grader needs. The uniform 4-bit answers directly and is 0 format failures in the same
harness with the same prompt.

**Honest scope of the claim:** this is a measured *output-contract* failure, not a clean statement
that the quant is less intelligent. It could be the quant degrading instruction-following, or a
different chat template/reasoning default in that repo. It does not matter for the decision: a
fail-closed pipeline (SparseClassificationError on short/absent application text, strict JSON
contracts) cannot absorb a 31% malformed-output rate, and the same model at 4.6x latency and +28.6%
disk buys nothing. The decided action is therefore: keep the uniform 4-bit.

**Consequences applied:**
- `RETIRED_MODELS` guard added to `tools/model_eval_suite.py` and `scripts/pipe_s4_classify_gold.py`,
  so any future run naming a retired model skips it instead of burning requests on 404s and writing
  rows that read as model failures.
- Step 6 (S4 on OptiQ) and step 8's OptiQ block cancelled — an S4 run on it would have measured the
  format failure, not accuracy.
- Vision probe (step 7) retired in the same pass by user ruling; `scripts/vision_probe.py` is now a
  no-op, implementation preserved at `archive/vision_probe.py`.
- OptiQ added to `PRUNED_MODELS` in `tools/model_eval_report.py` so its 128 voting rows cannot be
  quoted as a candidate.

**Files NOT yet deleted (deliberate):** oMLX still held the model resident when it was retired, and
deleting a loaded model's weights mid-run risks taking the server down in the middle of step 8. The
20.68 GB is to be reclaimed after the chain reports ALL DONE and oMLX has evicted it.
