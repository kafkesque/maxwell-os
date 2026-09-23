# Gate A2 — model-store reclaim list (NO DELETION PERFORMED)
Generated 2026-09-23. Authority: owner acceptance of Gate A2 (2026-09-23). Method: config-reference
classification — a store entry is KEEP only if `config/model_assignments.yaml` or
`config/pipeline_config.yaml` names it (or its backend). Nothing here has been moved or deleted.

## Why NOT Gate A
Gate A moved ~16.5 GB in-repo archive payload to an external volume: ~2% of the 28 GB deficit, and
no external volume was mounted. Gate A2 targets the stores that actually hold the bytes.

## Deficit
`/System/Volumes/Data` 874 GiB used / 926 GiB (97%), **28 GiB available**. Model stores = ~280 GB.

## KEEP (config-referenced — never touch)
| store | entry | size | named by |
|---|---|---|---|
| hf hub | Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | 32.8 GB | pipeline_config models.generator |
| hf hub | gemma-4-E4B-it-MLX-4bit | 13.1 GB | model_assignments REVIEWER/RESIDENT_BRAIN/L2_VALIDATOR/S3A_VERIFIER |
| hf hub | gpt-oss-20b-MXFP4-Q8 | 11.5 GB | pipeline_config models.verifier (D2249) |
| hf hub | Phi-4-mini-instruct-8bit | 5.5 GB | S2 fast probe (D2319) |
| hf hub | BAAI/bge-m3 | 4.4 GB | model_assignments EMBEDDINGS (ollama) |
| hf hub | Qwen3.8-27B-MLX-4bit | 4.1 GB | R5 deep auditor (D2543/D2556) |
| hf hub | DeBERTa-v3-large-mnli-fever-anli-ling-wanli | 3.9 GB | S5 NLI, sole verifier (D2298) |
| hf hub | BAAI/bge-reranker-v2-m3 | 2.2 GB | pipeline_config reranker |
| ollama | .ollama/models | 12.9 GB | bge-m3 serving store |
| omlx | .omlx/cache | 92.5 GB | the LIVE serving cache of the running server |

`~/.omlx/cache` is content-addressed (2-hex-char blob dirs, 21 top-level dirs) — **no names, so it
cannot be pruned by config reference.** It is the serving cache of a running process. Do not prune it
while oMLX runs; it can only be reclaimed by removing models from the server's own model list.

## RECLAIM CANDIDATES (not named by any config; ~78 GB)
| store | entry | size | class |
|---|---|---|---|
| hf hub | lmstudio-community--Qwen3-Coder-30B... **dup of KEEP** | 32.8 GB | **VERIFY FIRST — duplicate of the generator** |
| hf hub | mlx-community--Ornith-1.5-35B-A3B-OptiQ-4bit-REAP-19B | 13.1 GB | laya/bench-only (DEFER per D-2593 class) |
| hf hub | ornith-ai--Ornith-1.5-9B-MLX-8bit | 9.1 GB | laya/bench-only (DEFER) |
| hf hub | facebook--bart-large-mnli | 6.6 GB | superseded NLI experiment |
| hf hub | mlx-community--Qwen2.5-Coder-7B-Instruct-4bit | 4.1 GB | superseded |
| hf hub | mlx-community--Qwen2.5-7B-Instruct-4bit | 4.1 GB | superseded |
| hf hub | ynie--roberta-large-snli_mnli_fever_anli... | 4.1 GB | superseded NLI experiment |
| hf hub | MoritzLaurer--bge-m3-zeroshot-v2.0 | 3.3 GB | superseded |
| hf hub | roberta-large-mnli | 1.4 GB | superseded |
| hf hub | BAAI--bge-reranker-base | 1.1 GB | superseded reranker |
| hf hub | tasksource--ModernBERT-base-nli | 1.1 GB | superseded |
| hf hub | answerdotai--ModernBERT-base | 0.6 GB | base weights of the depth encoder line |
| hf hub | cross-encoder--nli-deberta-v3-small | 0.6 GB | superseded |
| hf hub | MoritzLaurer--DeBERTa-v3-base-mnli-fever-anli | 0.4 GB | superseded |
| hf hub | typeform--distilbert-base-uncased-mnli | 0.3 GB | superseded |
| hf hub | mlx-community--Qwen3-Embedding-0.6B-4bit-DWQ | 0.3 GB | superseded |
| models | Qwen3.6-35B-A3B-6bit | 27.1 GB | **not named anywhere; no role** |
| mtplx | samuelfaj--Qwopus3.6-35B-A3B-v1-4bit-MTPLX... | 20.6 GB | **config calls Qwopus a PHANTOM that "does not exist locally" — it DOES** |

## Two findings that must be resolved BEFORE any byte moves
1. **The first candidate row is a probable duplicate of the KEEP set.** `hf hub` holds 37 repos
   (126.2 GB) but the largest single repo is 32.8 GB — the same size as the generator. Confirm by
   digest, never by name, before considering either.
2. **`~/models/Qwen3.6-35B-A3B-6bit` (27.1 GB) has no role, and `~/models` contains nothing else.**
   It is either a model about to be adopted or 27 GB of orphan — the owner knows which.

## Safety rules carried from the standing decisions
- Never `rm` a model store. Remove a model from the SERVING list, restart, load from the surviving
  store and confirm the model ANSWERS, then reclaim.
- `~/.omlx/cache` is not prunable by name and is live. Touch it last, server stopped.
- The KEEP set above is the floor: 84 GB of the 280 GB is genuinely in use.
