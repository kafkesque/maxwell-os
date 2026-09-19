# Benchmark Plan v2 — model portfolio consolidation (D-2637)

Updated 2026-09-15 19:35. Supersedes the plan in the D-2637 session notes.

Harness: `tools/model_eval_suite.py` (resumable, per-item checkpoint) · fetcher:
`tools/fetch_evalsets.py` · report: `tools/model_eval_report.py`

---

## 1. Layer A — General capability (what an LLM is good at)

| Suite | Axis | Items | State |
|---|---|---|---|
| delegation | faithful implementation of a frontier-model spec (AST + execution graded) | 6 | running |
| ifeval | instruction following (Google IFEval, rule-based) | 25 | running |
| mbpp | coding, light (MBPP-sanitized, real unit tests) | 25 | 7/9 done |
| humaneval | coding, light (OpenAI HumanEval, real unit tests) | 25 | queued |
| hardcode | coding, hard (LRU, topo-sort, DP, parsing) | 4 | DONE |
| toolcalling | tool selection + argument values (JSON schema) | 4 | DONE |
| planning | strategic constraint planning | 3 | DONE (low power) |
| reviewing | seeded-bug + false-claim detection | 6 | DONE (weak grader) |
| niah | long-context retrieval @ 4k/12k/24k | 9 | queued (shortlist) |
| lc_reasoning | reasoning with facts buried at 16k | 6 | queued (shortlist) |
| stability | determinism over 3 identical repeats | 30 | DONE — all 9 models 10/10 unanimous |
| gsm8k / math500 | general math reasoning | 25 ea | not run (Tier C) |
| mmlu_pro | general knowledge | 25 | not run (LOW value — knowledge lives in the graph) |
| hotpot_qa | multi-hop synthesis (model-side research proxy) | 25 | not run |

## 2. Layer B — Pipeline-role (what THIS project needs) — NEW in v2

Every pipeline stage that calls an LLM, its current model, and whether it has ever
been benchmarked per model:

| Stage | Current model | Benchmarked? |
|---|---|---|
| S0.5 metadata (author/title) | Phi-4-mini-instruct-8bit | **NO — zero benchmarks** |
| S2 convergent extraction | Qwen3-Coder-30B (GEN_MODEL) | partial (6 clusters) |
| S2 relabel cross-family | gpt-oss-20b-Q8 | **NO** |
| S3A convergence | Qwen3-Coder-30B | shares S2 |
| S4 merged CRIBS classify | gpt-oss-20b-Q8 (+ Phi-4-mini verifier_v2) | partial, NON-PRODUCTION prompt |
| S4 depth | gemma-4-E4B | partial (gpt-oss only) |
| S4_5 enrich | gpt-oss-20b-Q8 | **NO** |
| S5 verify | DeBERTa-v3-large (NLI) | yes — not an LLM task |
| retrieval_eval | Phi-4-mini-instruct-8bit | **NO** |
| hyDE query expansion | Qwen3-Coder-30B | **NO** |
| rerank | bge-reranker-v2-m3 | yes — DEAD END (D2636) |
| dedup judge | Qwen3.8-27B | **NO** |
| suffix-duplicate judge | Qwen3.8-27B | **NO** |
| alias review | Qwen3.8-27B | **NO** |
| label_vote ensemble | deepseek-v4-pro + Qwen3.8 + Qwen3-Coder | **per-model accuracy untested** |

Proposed Layer B suites:

| Suite | What it measures | Grading |
|---|---|---|
| pipe_s4_classify | discipline acc + domain F1 through the PRODUCTION merged_cribs_classify path | vs gold_4axis (100 rows) |
| pipe_s4_depth | 4-way depth axis | vs depth gold |
| pipe_s4_content_type | principle / process_template / process_instance / tool_instruction | vs gold |
| pipe_s2_extract | convergent extraction — route AND schema validity AND distinct-author support (BUG-232) | vs frozen CRIBS gold |
| pipe_s0_5_metadata | author + title extraction from book front matter | vs known gold |
| pipe_merge_dedup | pairwise "same principle?" duplicate judging | vs adjudicated pairs |
| pipe_alias_canon | canonicalise a raw discipline string into taxonomy_v5 | exact canonical match |
| pipe_hyde | query expansion quality | retrieval recall@k downstream |
| pipe_relabel | cross-family relabel agreement | vs accepted labels |

## 3. Layer C — Voting / anchors (NEW — answers the D2618 P1 blocker)

**pipe_voting** on the 251 gold_4axis rows:
1. Run every candidate model as a voter over the SAME rows -> per-model accuracy.
2. Build the pairwise agreement matrix AND the **error-correlation** matrix.
   Correlated errors mean voting cannot help, no matter how many voters.
3. Simulate aggregation policies: majority-of-3, majority-of-5, unanimity-gated,
   confidence-gated, and best-single-model.
4. Report: does the ensemble beat the best single model, by how much, at what coverage?

This directly answers: which model is the most accurate/reliable classifier, whether
voting is worth its cost at all, and which voters to use for the 63 contested rows.

## 4. Layer D — Cross-cutting / previously forgotten

| Suite | Why it matters |
|---|---|
| abstain | fail-closed behaviour: say INSUFFICIENT when evidence does not support a claim. **Critical for S2.** |
| json_repair | repair malformed JSON into schema |
| summarise_long | long-document summarisation with fact coverage |
| multilingual | the corpus contains non-English material |
| context_stress | multi-turn agent context growth (DELEGATE-002 collapse class) |
| throughput | tok/s and peak RAM under the real concurrency |

## 5. Quant A/B (NEW)

4-bit vs 8-bit is a decision per model, not a global truth. On Apple Silicon:
- 8-bit is **more accurate** (less quant damage), **slower** (decode is bandwidth-bound;
  8-bit moves ~33% more bytes), and no different on reliability.
- Current `mlx-community/Ornith-1.5-9B-OptiQ-4bit` is already MIXED: 134 tensors at
  8-bit, 116 at 4-bit.
- Testing `ornith-ai/Ornith-1.5-9B-MLX-8bit` (official, 288k downloads) head-to-head on
  the same suites settles it empirically instead of by theory.

## 6. NOT model capabilities (separate harness, no model benchmark can answer)

| Need | Status |
|---|---|
| web search | ddgs 9.14 + oMLX built-in web_search |
| scraping/reading | trafilatura 2.0, newspaper, bs4, playwright |
| Reddit | praw 8.0.2 |
| YouTube | yt-dlp only (youtube-transcript-api MISSING) |
| X/Twitter | nothing |
| audio/video transcription | **no ASR installed** (needs Whisper/Parakeet) |
| OCR / images | no VLM. NOTE: base `ornith-ai/Ornith-1.5-9B` is tagged image-text-to-text |
