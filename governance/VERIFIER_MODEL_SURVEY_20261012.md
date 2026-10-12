# VERIFIER MODEL SURVEY + RULING — 2026-10-12

> Question asked (owner, 2026-10-12): *"is the verifier failing too often?"* — clarified: **not the same
> model; the most RELIABLE one, judged by community notes, benchmarks, and Hugging Face downloads/likes.**
> This file RECORDS the evidence and the ruling. It changes no pin. BUG-736 is the tracker.

## 0. What the question is really asking

Two DIFFERENT roles are both called "the verifier". They must not be answered with one model.

| role | pin | job | failure mode measured |
|---|---|---|---|
| S5 | nli_verifier_s5 = MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli | does the EVIDENCE entail the CLAIM (grounded factuality) | abstains 19.1% (1,255 neutral + 783 contra + 29 no_evidence of 6,571 eligible), fail-closed per D-2298; edge on the LIVE artifact UNMEASURED |
| R5 | reviewer_r5 = gemma-4-E4B-it-MLX-4bit | review a diff/artifact for defects | uninformative ~40-50% of passes over 7 recorded passes; **false-positives-APPLIED = 0** |

The uncertainty is therefore NOT "which LLM judges better". It is: **is there a model whose JOB is
verification, whose reliability is measured, and which is not the generator's family?**

## 1. Hugging Face adoption metrics (measured via the HF API, 2026-10-12)

Downloads and likes are ADOPTION, not accuracy. They are used here only to bound the candidate set.

| model | downloads | likes | note |
|---|---:|---:|---|
| BAAI/bge-reranker-v2-m3 | 16,000,331 | 1,242 | retrieval reranking, NOT a verifier |
| openai/gpt-oss-20b | 5,896,789 | 5,159 | highest-liked local-capable LLM in the sample |
| openai/gpt-oss-120b | 3,644,353 | 5,387 | |
| Qwen/Qwen3-32B | 3,307,050 | 761 | **generator family** — disqualified as verifier (R5) |
| facebook/bart-large-mnli | 2,498,782 | 1,625 | legacy NLI, superseded |
| Qwen/Qwen2.5-Coder-32B-Instruct | 793,989 | 2,170 | **generator family** |
| google/gemma-3-27b-it | 418,679 | 2,047 | non-Qwen judge candidate |
| Qwen/Qwen3-Coder-30B-A3B-Instruct | 386,097 | 1,279 | **the generator itself** |
| lmstudio-community/gemma-4-26B-A4B-it-QAT-MLX-4bit | 348,226 | 17 | **fielded R5 candidate** (MLX) |
| mlx-community/gpt-oss-20b-MXFP4-Q8 | 217,544 | 96 | already local (S4 classifier) |
| FacebookAI/roberta-large-mnli | 187,574 | 216 | legacy NLI |
| vectara/hallucination_evaluation_model (HHEM-2.1-Open) | 135,274 | **367** | most-liked hallucination model; Apache-2.0; flan-t5-base |
| MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli | 134,958 | 132 | **S5 incumbent** |
| cross-encoder/nli-deberta-v3-large | 126,183 | 45 | NLI |
| MoritzLaurer/mDeBERTa-v3-base-mnli-xnli | 116,076 | 319 | NLI, multilingual |
| lytang/MiniCheck-Flan-T5-Large | 27,469 | 14 | purpose-built fact-checker, 0.8B, MIT |
| tasksource/ModernBERT-large-nli | 16,428 | 16 | NLI, 8k context, Apache-2.0 |
| allenai/OLMo-2-0325-32B-Instruct | 9,575 | 147 | fully open family |
| bespokelabs/Bespoke-MiniCheck-7B | 6,587 | 89 | purpose-built fact-checker (SOTA — see §2) |
| Skywork/Skywork-Reward-Llama-3.1-8B | 824 | 32 | reward model |
| PatronusAI/Llama-3-Patronus-Lynx-8B-Instruct | 209 | 45 | RAG hallucination judge |

Source: https://huggingface.co/api/models/<id> (downloads, likes), read 2026-10-12.

**The adoption signal alone is a trap, and it is the SAME trap R5 exists to avoid:** the most-downloaded
LLMs and the most-downloaded MLX quants are Qwen — i.e. the generator's own family. A verifier chosen by
downloads would be the generator wearing a second hat.

## 2. Benchmark evidence — where the accuracy actually lives

**LLM-AggreFact (11 human-annotated grounding/hallucination datasets, average score; leaderboard read 2026-10-12):**

| model | size | average |
|---|---:|---:|
| Bespoke-MiniCheck-7B | 7B | **77.4** |
| Claude-3.5 Sonnet | — | 77.2 |
| Granite Guardian 3.3 | 8B | 76.5 |
| Mistral-Large 2 | 123B | 76.5 |
| gpt-4o-2024-05-13 | — | 75.9 |
| FactCG-DeBERTa-L | **0.4B** | 75.6 |
| Qwen2.5-72B-Instruct | 72B | 75.6 |

A **7B purpose-built fact-checker beats Claude-3.5 Sonnet and gpt-4o** at the S5 job, and a 0.4B
fact-checker matches Qwen2.5-72B. MiniCheck-Flan-T5-Large (0.8B, MIT) is the best <1B on the same
benchmark and the authors report GPT-4-level at 400x lower cost (card: huggingface.co/lytang/MiniCheck-Flan-T5-Large).

**JudgeBench (objective-correctness judging over knowledge/reasoning/math/coding pairs):**
"many strong models (e.g., GPT-4o) perform just slightly better than random guessing."
=> LLM-judge unreliability is a STRUCTURAL limit of the judge paradigm, not a model-selection problem.
It is exactly why R5 output must stay EVIDENCE-TO-AUDIT and never a verdict (the design that makes
false-positives-APPLIED = 0 possible). Source: arxiv.org/abs/2410.12784.

**Vectara hallucination leaderboard (ranked by HHEM-2.3; read 2026-10-12):** the open-model top of the
table includes gemma-4-26b-a4b-it at 5.2% hallucination / 94.8% factual consistency, gemma-3-12b-it 4.4%/95.6%,
qwen3-14b 4.8%/95.2%. HHEM-2.1-Open is the open variant of the model that produces this ranking.

## 3. RULING — S5 (grounded verification)

1. **S5 is not "failing too often"; it is failing CLOSED without a measured edge.** Abstention is the
   rail's contract (D-2298). The defect is that its accuracy on OUR artifact was never measured, so
   nobody can say whether a better model would change a single verdict.
2. **The right shape for S5 is a PANEL of purpose-built, non-generator-family fact-checkers**, not a
   bigger LLM judge. The fielded candidate set, in adoption/accuracy order:
   - **Bespoke-MiniCheck-7B** (77.4 on LLM-AggreFact; base internlm2_5-7b-chat — family is neither Qwen nor Gemma)
   - **MiniCheck-Flan-T5-Large** (0.8B, MIT, best <1B; T5 family — a SECOND, independent family)
   - **MiniCheck-DeBERTa-v3-Large** (0.4B — same size/architecture as the incumbent, purpose-trained)
   - **HHEM-2.1-Open** (Apache-2.0, flan-t5-base, 367 likes, 0-1 consistency score with a threshold = fail-closed by construction) as an independent second signal
3. **No pin changes on popularity.** The incumbent stays pinned until a bench on OUR rows says the panel
   is better: stated n, reported against the majority-class baseline (BUG-269), and
   min_margin_over_baseline 0.15. A survey is not a measurement (D-2956).
4. **Rejected:** any Qwen-family verifier (the generator is Qwen3-Coder-30B); a single giant LLM judge
   for S5 (JudgeBench); swapping models because they are downloaded more.

## 4. RULING — R5 (artifact/diff review)

1. **The reviewer stays ADVISORY.** JudgeBench says no judge is strong enough to apply automatically;
   the invariant that keeps R5 free is false-positives-APPLIED = 0, and it must stay.
2. **The reviewer model should move from the 4B gemma to the already-fielded 26B-A4B gemma** (NOT fielded - see the CORRECTION at the end)
   (lmstudio-community/gemma-4-26B-A4B-it-QAT-MLX-4bit, 348k downloads; its family sits at 94.8%
   factual consistency in Vectara's ranking). This is the ONE model change the ecosystem evidence
   supports — and it must land WITH BUG-269's task fixes (T2 deterministic string op = 0 LLM calls;
   T3 mechanise the step-count test and judge only the residue), because mechanising removes the passes
   that an LLM judge should never have been asked to make.
3. **Rejected:** swapping to gpt-oss-20b purely on likes (5,159) without a bench — high adoption,
   unmeasured here, and its failure mode on OUR diff-review task is unknown.

## 5. The measurement that decides it (BUG-736, owed)

A single harness run, one artifact snapshot, all candidates scored on the SAME n:
- rows: the S5-eligible tier (6,591) — nothing derived from a table-wide ruler (D-2642)
- baselines: constant-majority AND the incumbent pin, both reported (BUG-269)
- margin: min_margin_over_baseline 0.15, stated n, and the abstain rate reported separately from the error rate
- no candidate is adopted on a margin inside the noise; a tie keeps the incumbent (cheaper, already pinned)
- R5: the 7-pass tally keeps accumulating (2 clean, 1 with 2 REAL findings applied, 1 with 3 false
  positives, 1 full drift, 1 refusal, 1 uninformative) with a 26B-A4B gemma arm added for comparison

**CORRECTION (2026-10-12, found by the pre-commit forensic audit - this is the audit catching my own recommendation):**
the 26B-A4B gemma named in §4.2 is NOT fielded and NOT fetched. config/model_assignments.yaml DISABLES
gemma-4-26B-A4B-it-OptiQ-4bit as BROKEN ("Goose stress test: 5/5 calls fail"), the local HF cache holds no 26B, and
governance/eval_models.txt (the live oMLX registry, 7 models) lists none. The QAT MLX-4bit artifact is a DIFFERENT
quantization from the broken OptiQ one, so it is a CANDIDATE: it needs a fetch, a BUG-265-class preflight, and then the
§5 bench before it may review anything. NO PIN MOVES on this survey. Also recorded: Qwen3.8-27B-MLX-4bit is NOT a
cross-family reviewer (same Qwen lineage as the generator) and is declared not_candidates in config/r5_review_gate.yaml.

**Owner-approved 2026-10-12 -> D-2961** (S5 panel + R5 advisory + the cross-family rule); the reviewer promotion stays
CONDITIONAL. The R5 gate that carries the deterministic layers is **D-2962** (scripts/r5_review_gate.py, BUG-738).
