# ARM-4d — Published benchmarks vs our stack (2026-09-15)

Sources: HuggingFace model cards (fetched 2026-09-15). Gemma-4 columns attributed
from the family table header `[31B, 26B-A4B, **12B Unified**, **E4B**, E2B, Gemma3-27B]`.

## Published benchmarks

| Model | Params | MMLU-Pro | GPQA-D | AIME-2026 | LiveCodeBench v6 | SWE-bench Verified | Terminal-Bench |
|---|---|---|---|---|---|---|---|
| gemma-4-31B | 31B | 85.2 | 84.3 | 89.2 | 80.0 | — | — |
| gemma-4-26B-A4B | 26B | 82.6 | 82.3 | 88.3 | 77.1 | — | — |
| **gemma-4-12B** | 12B | **77.2** | **78.8** | **77.5** | **72.0** | — | — |
| Qwen3.8-27B *(reliable pair)* | 27B | — | **89.2** | — | **90.3** | Pro 61.7 | — |
| Ornith-1.5-35B-A3B | 35B | — | 89.2 | — | — | **79.0** | 67.8 |
| Ornith-1.5-9B | 9B | — | — | — | — | 70.6 | 46.2 |
| DeepSeek-R1-0528-Qwen3-8B | 8B | 85.0* | 81.0* | 91.4* | 73.3* | — | — |
| **gemma-4-E4B** *(current REVIEWER)* | 4B | 69.4 | 58.6 | 42.5 | 52.0 | — | — |
| **Phi-4-mini** *(current ORCH)* | 3.8B | 52.8 | 25.2 | — | — | — | — |
| gpt-oss-20b *(current S4)* | 21B / 3.6B act | — | — | — | — | — | — |

\* DeepSeek-R1-0528 numbers are the 671B parent; the 8B distill is SOTA among open
models on AIME-2024. gpt-oss-20b's card has no table (benchmarks live in the OpenAI
blog/model card); it REQUIRES the harmony response format.

## Decisive published comparisons

1. **gemma-4-12B vs gemma-4-E4B (the swap that matters)** — 12B dominates on every axis:
   MMLU-Pro **77.2 vs 69.4**, GPQA-D **78.8 vs 58.6 (+20.2)**, LiveCodeBench
   **72.0 vs 52.0 (+20)**, AIME-2026 **77.5 vs 42.5 (+35)**. The current REVIEWER
   is materially weaker on reasoning + coding.
2. **Qwen3.8-27B > gemma-4-12B on published benchmarks** — GPQA-D **89.2 vs 78.8**,
   LiveCodeBench **90.3 vs 72.0** (27B vs 12B).
3. **Phi-4-mini (current ORCHESTRATOR/probe) is the weakest** — MMLU-Pro 52.8,
   GPQA-D 25.2.
4. **Ornith-1.5-9B punches far above its 9B weight** on agentic coding (SWE-bench
   Verified 70.6), and the 35B-A3B is genuinely strong (SWE-bench Verified 79.0).

## Caveats

- Suites differ across cards; not a single-vendor leaderboard.
- Published = upstream quality, NOT our task (61-way discipline / convergent
  extraction / R5 review). Our own ARM-4 numbers govern those.
