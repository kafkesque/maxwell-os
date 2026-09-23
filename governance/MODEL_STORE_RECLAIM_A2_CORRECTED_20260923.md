# A2 CORRECTED - model store reclaim, list-first (2026-09-23)
Supersedes the candidate list in governance/MODEL_STORE_RECLAIM_A2_20260923.md (see its
CORRECTION block / BUG-414). Method: RESOLUTION-first classification - readlink of every
~/.omlx/models entry, the live /v1/models list, then a config/code reference scan.
NO BYTE MOVED. Owner approval still required.

## KEEP (serving store or config/code referenced)
- hf hub as a whole (~126 GB) - it IS the store for 5 of 7 served models (symlink targets)
- ~/.omlx/models/Qwen3.8-27B-MLX-4bit 15.3 GB (real bytes)
- ~/.omlx/models_stashed/Phi-4-mini-instruct-8bit 3.9 GB (real bytes; the served probe)
- ~/.omlx/cache 92.5 GB - live runtime cache of a running server, not a store
- BAAI--bge-m3 4.4; MoritzLaurer--DeBERTa-v3-large 3.9; bge-reranker-v2-m3 2.2
- bge-reranker-base 1.1 (ref pipeline/stage2_relabel_extraction_type.py)
- ModernBERT (0.6 + 1.1) (ref config/pipeline_config.yaml, config/eval_integrity.yaml)
- mlx-community--Qwen2.5-Coder-7B-Instruct-4bit 4.1 (ref pipeline/model_lazyload.py - read first)

## CANDIDATES (no config ref, not on any serving path, not in a golden prompt)
| item | GB | note |
|---|---|---|
| models/Qwen3.6-35B-A3B-6bit | 27.1 | no config ref; THREE distinct Qwen3.6-35B variants exist on disk |
| .mtplx/models samuelfaj--Qwopus3.6-35B-v1-4bit-MTPLX | 20.6 | config/model_assignments.yaml calls it a PHANTOM that "does not exist locally"; it does |
| <gen repo>/blobs | 16.4 | internal duplicate of snapshots/main; holds 2 .incomplete files |
| facebook--bart-large-mnli | 6.6 | zero references anywhere |
| mlx-community--Qwen2.5-7B-Instruct-4bit | 4.1 | zero references anywhere |
| ynie--roberta-large-snli... | 4.1 | zero references anywhere |
| roberta-large-mnli | 1.4 | zero references anywhere |
| cross-encoder--nli-deberta-v3-small | 0.6 | zero references anywhere |
| distilbert-base-uncased-mnli | 0.3 | zero references anywhere |
| TOTAL | ~81.2 | composition differs COMPLETELY from the original list |

## DEFER (referenced only by evidence/training scripts - they reproduce measurements)
- MoritzLaurer--bge-m3-zeroshot-v2.0 3.3 (scripts/benchmark_domain_taxonomy_match.py)
- microsoft--DeBERTa-v3-base 0.4 (scripts/train_discipline_classifier.py, golden prompts)

## SAFETY (unchanged from D-369)
never rm a store; remove it from the SERVING list, restart, load from the surviving
store, confirm the model ANSWERS, then reclaim; ~/.omlx/cache is touched last with the
server stopped; owner decides the two named-vs-phantom items by knowledge, not inference.
