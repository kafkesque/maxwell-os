# ARM-4b — Role-based capability benchmark (2026-09-15)

Method: `scripts/arm4_capabilities.py` — 5 capabilities × 2 deterministic
checkable tasks (coding / reasoning / orchestrating / reviewing / analysing).
Greedy decode, `enable_thinking=False` for reasoning models. Read-only.

## Scores (pass rate per capability)

| Model | coding | reasoning | orchestrating | reviewing | analysing | **overall** |
|---|---|---|---|---|---|---|
| gemma-4-12B-it-qat-OptiQ-4bit | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** |
| Ornith-1.5-35B-A3B-REAP-19B | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** |
| Qwen3-Coder-30B-A3B (current GENERATOR) | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | **1.00** |
| Ornith-1.5-9B-OptiQ-4bit | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | **0.90** |
| Phi-4-mini-instruct-8bit (current ORCH/CODING_DRAFT) | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | **0.90** |
| gpt-oss-20b-MXFP4-Q8 (current S4 CLASSIFIER) | 1.00 | 1.00 | **0.00** | 1.00 | **0.00** | **0.60** |
| gemma-4-E4B-it-MLX-4bit (current REVIEWER) | LOAD FAILED (126-param arch mismatch vs installed mlx_lm) |

## Findings

1. **gemma-4-12B (1.00) > gpt-oss-20b-Q8 (0.60)** on role capabilities. gpt-oss
   scored 0.00 on orchestrating AND analysing.
2. **CAVEAT on gpt-oss**: its raw output leaks the harmony format
   (`<|channel|>analysis<|message|>…`) when loaded via raw `mlx_lm` — the answer is
   wrapped in channel markers the JSON parser can't strip. In production it is
   served via OMLX, which handles the format. So gpt-oss's 0.60 is likely an
   **undercount**, not a fair capability floor. Re-test via OMLX before acting.
3. **Reasoning discriminator**: the bat-and-ball task separated true reasoners
   from pattern-matchers — Ornith-9B answered `$0.10` and Phi-4-mini `10 cents`
   (both wrong); gemma-4-12B, Ornith-35B, Qwen3-Coder answered `$0.05`.
4. **gemma-4-E4B (current REVIEWER) could not be benchmarked** via raw mlx_lm —
   checkpoint/arch mismatch. Must be run through OMLX to get its row.
5. **Ornith-35B-REAP = 3× the size of Ornith-9B, same 1.00** — for the capability
   roles there is no win from the 35B; the 9B is the value pick at 7GB.

## Related

- ARM-4 classification/extraction: `governance/arm4_benchmark.json`
- gpt-oss classification head-to-head: `governance/arm4_gptoss_classify.json`
