# DOWNLOAD / DELETE ROSTER (proposal - the OWNER disposes of bytes)
Measured 2026-10-15. R-D410: nothing leaves the disk except through `pipeline/safe_delete.py`, with the
owner's word. This file is the PROPOSAL; no deletion is implied by it.

## 1. DOWNLOAD
| verdict | item | bytes | why |
|---|---|---|---|
| DONE (2026-10-15) | openbmb/MiniCPM5-2B-MLX | 1.42 GB | the only candidate the engine's own runtime approved at a price worth paying; adopted, measured 110.1 tok/s decode, released |
| HOLD | Edge0/Edge0-35B-A3B-preview | 19.69 GB | arch supported (qwen3_5_moe), apache-2.0, 3,582 likes. **Do not stack it on a full pool**: pair it with a retirement (T-139). The pool is the scarce resource, not the disk |
| REFUSE | prism-ml/Ternary-Bonsai-2-27B-mlx-2bit | 8.60 GB | `prism_hadamard_qwen35` has no module in the engine's mlx_lm; ships a private runtime/ loader |
| REFUSE | google/embeddinggemma-2 | 1.49 GB | `embedding_gemma2` unsupported by the engine runtime - and an embedder swap cascades through every stored vector |
| REFUSE | empero-ai/Qwen3.8-35B-A3B-Distill | 71.90 GB | 72 GB for 7,813 downloads; 34x the price of the candidate that won |
| REFUSE | ConwayResearch/Underdog-Saluki-27B-1.0 | 9.46 GB | config declares no model_type; not an MLX repack |
| DEFER | LiquidAI/LFM2.5-24B-A2B | 47.94 GB | loadable but a non-OSI licence ("other") and 48 GB |
| DEFER | ornith-ai/Ornith-1.5-35B-A3B-MLX-4bit | 19.51 GB | no licence declared = no grant; the family is already resident as REAP-19B |

## 2. DELETE - THE RULE
**Delete what can MISLEAD. Keep what can only WASTE.** A byte that can be loaded by accident and be wrong
is a hazard; a superseded-but-valid model is only rent, and this machine has 217 GB free, so rent is
cheap and a re-download is not.

### Tier A - HAZARD CLASS (recommended once, ~4.0 GB + 7 names)
| item | bytes | why it is a hazard |
|---|---|---|
| `models--lmstudio-community--Qwen3.8-27B-MLX-4bit` (hub) | 4.0 GB | a TRUNCATED snapshot of a repo whose served copy is a separate real 15.7 GB directory; the name resolves, the bytes do not belong to anything (BUG-814) |
| the 7 broken `_unloaded` symlinks | 0 B | names that read as "on disk" and point at nothing (BUG-808); they are what made a bench row read NA |
Command (owner act): `python3 pipeline/safe_delete.py <path> --reason "BUG-814: truncated hub snapshot, nothing resolves into it"`
For the symlinks: `pipeline/omlx_retire_model.sh --model NAME --park` removes the engine entry without
leaving a dangling link (the 2026-10-15 parked entries are the counter-example: parking produced 7 names
that lie).

### Tier B - SUPERSEDED-BUT-VALID (18.06 GB, NOT recommended now)
The 19 ORPHAN repos: bart-large-mnli (6.9 GB), Qwen2.5-7B-Instruct-4bit (4.3 GB), roberta-large-snli
(4.27 GB), roberta-large-mnli (1.4 GB), nli-deberta-v3-small (0.58 GB), distilbert-mnli (0.27 GB),
the two MiniLM embedders (0.18 GB), cross-encoder ms-marco (0.09 GB), the MMLU-Pro/MATH-500/Humaneval
datasets (4.2 MB + …). Each is superseded in FUNCTION by a LIVE or DECLARED model (DeBERTa-v3-large
NLI, bge-m3 embeddings, bge-reranker), and the census proves nothing live names them.
**Recommendation: keep.** Reason: they are the control group of past instrument decisions, the disk is
not the constraint, and a re-download to re-run one old comparison costs more than the bytes save.
Trigger to revisit: free space below 25% of the volume, or a new candidate whose bytes must come from
somewhere.

## 3. RETIREMENT CANDIDATE (the pool, not the disk)
`gemma-4-12B-it-qat-OptiQ-4bit` (8.4 GB, served): worst MEASURED non-27B decode (13.4 tok/s), and its
only live declarations are a REJECTED swap (`pipeline_config.yaml#swap_eval_candidate_model`, D-2788
"slower on BOTH axes") and an R5 candidate list. The eval report lists it under PRUNED. Its functions
are covered: routing/stability by gemma-4-E4B, quality by Qwen3.8-27B. Retiring it frees a POOL SLOT,
which is what Edge0 would need.
Command (owner act): `pipeline/omlx_retire_model.sh --model gemma-4-12B-it-qat-OptiQ-4bit --park`
then, only if the bytes are to go: `python3 pipeline/safe_delete.py <hub repo> --reason "T-139 retirement"`
Open question the owner must settle: `config/r5_review_gate.yaml` lists it as a cross-family reviewer
candidate, so retiring it removes one R5 option (gemma-4-E4B, Qwen3.8-27B and Ornith-9B remain).
