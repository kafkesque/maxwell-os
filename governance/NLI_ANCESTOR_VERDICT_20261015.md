# NLI / ENCODER ANCESTOR VERDICT — 2026-10-15

**Owner word (verbatim):** *"delete the tier B NLI/embedder anchestors if they dont have any current or
potential future use that can be better than current model"*.

**Method:** every candidate's name was searched in `pipeline/`, `scripts/`, `config/`, `agent/` (and the
engine's own entries read from `/v1/models/status`), because the census's buckets are derived from a
TEXT INDEX: `pipeline/model_store_census.py#declared_text()` joins every text file and `classify()` asks
`stem in refs`. That answers *"is this string written down"*, not *"does anything resolve into these
bytes"*. Both directions of that error are present in the 2026-10-15 census, which is why the sweep ran
its own test.

## The sweep: 8 repos, 18.90 GiB measured (`du -sk`, receipt `DELETION_RECEIPT_20261015b.json`)

| repo | bytes | why deletable |
|---|---|---|
| `facebook/bart-large-mnli` | 6.46 GiB | a zero-shot baseline that LOST; no config key, no code path |
| `ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli` | 3.98 GiB | ditto |
| `MoritzLaurer/bge-m3-zeroshot-v2.0` | 3.19 GiB | never referenced by any file in the repo, in any form |
| `roberta-large-mnli` | 1.33 GiB | the recorded BASELINE THAT FAILS (`DEBERTA_VERIFICATION_TEST_2026-08-09.md`) |
| `tasksource/ModernBERT-base-nli` | 1.12 GiB | the S5 fallback that D2298 REMOVED; `pipeline_paths.py:427` records the removal |
| `BAAI/bge-reranker-base` | 1.06 GiB | lost the D2511 comparison to `bge-reranker-v2-m3`; named only as a NEGATIVE verdict |
| `cross-encoder/nli-deberta-v3-small` | 0.54 GiB | the RUNNER-UP (4.8 s vs 3.5 s) — a comparison already recorded |
| `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | 0.35 GiB | superseded by the v3-large sole verifier (D2298) |

Total **18.90 GiB**. Each is an ancestor of a decision already made; the RECEIPT (the measured verdict)
is the value and it survives — in `governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md`, in
`config/decisions.yaml`, and in the files below.

## What this sweep must NOT touch, and why the check was run before the bytes moved

| repo | bytes | resolved by |
|---|---|---|
| `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` | 3.85 GiB | `config/pipeline_config.yaml#stage5.nli_model` + `models.nli_large` (D2298: the SOLE verifier) |
| `BAAI/bge-m3` | 4.25 GiB | `config/pipeline_config.yaml#stage1_5.embed_model_hf` (and the Ollama copy that serves it) |
| `BAAI/bge-reranker-v2-m3` | 2.14 GiB | `config/pipeline_config.yaml#rerank.model` + `pipeline/rerank.py` |
| `answerdotai/ModernBERT-base` | 0.56 GiB | `pipeline/student_classifier.py#BASE_MODEL_NAME` (D2607 student pre-classifier) |
| `BAAI/bge-small-en-v1.5` | 128 MiB | `pipeline/stage1_5_fastembed.py#EMBED_MODEL` (a code **default**) |
| `minishlab/potion-base-32M` | 125 MiB | `pipeline/providers/test_mlx_provider.py` (a code **default**) |

**The near-miss, stated plainly:** two of the six KEEP rows are invisible to a mention test — they are
resolved by a *default* in code. A sweep that trusted the ORPHAN bucket, or that searched only
`config/`, would have deleted the S1.5 alternative embedding backend and the student classifier's
backbone, and neither deletion would have announced itself until the next pipeline run.

**Second reading of the same flaw:** the census lists `cross-encoder/ms-marco-MiniLM-L-6-v2` as an
ORPHAN although `pipeline/stage2_relabel_extraction_type.py:21` names `ms-marco-MiniLM` — because the
test wants the full stem including `-L-6-v2`. The index is over- and under-inclusive at the same time.

## The floor (D-3018)

`config/engine.yaml#model_store.deletion_floor_bytes` = 256 MiB. Below it the *decision* costs more
attention than the bytes, and the floor is set at 2x the largest live-by-code-default encoder so no
sweep may reach one. Four repos survive the sweep by the FLOOR, not by usefulness:

`typeform/distilbert-base-uncased-mnli` (255 MiB), `cross-encoder/ms-marco-MiniLM-L-6-v2` (88 MiB),
`sentence-transformers/all-MiniLM-L6-v2` (87 MiB), `Qdrant/all-MiniLM-L6-v2-onnx` (87 MiB).

## What this deletion COSTS (the honest ledger)

`scripts/test_matryoshka_nli.py` cannot run offline afterwards: its inputs are
`tasksource/ModernBERT-base-nli` (1.12 GiB) and `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`
(0.35 GiB). Its VERDICT is recorded, so this is a re-download away and not a lost finding — but it is a
cost and it is written down rather than discovered.

## Edge0: the recommendation is DEFER, with a named trigger

`Edge0/Edge0-35B-A3B-preview` is real, popular and permissively licensed (apache-2.0, 3,582 likes,
57,485 downloads, `mlx` + `safetensors` + `qwen3_5_moe` tags, 4-bit affine gs64 with 8-bit gates).
It is **not** a new capability for this machine:

1. Its `base_model` is `Qwen/Qwen3.6-35B-A3B` and its `model_type` is `qwen3_5_moe` — the class the
   engine ALREADY serves as `Ornith-1.5-35B-A3B-OptiQ-4bit-REAP-19B` (same `model_type`, 13 GB). The
   scarce resource is the POOL (ceiling 52.7 GB, 8 declared models, `max_parallel: 3`), not disk.
2. The role it was proposed for, `AGENT_EDIT_LONG_CONTEXT`, is not blocked on bytes. It is blocked on
   MEASUREMENT: T-137 (cache A/B) and BUG-805 (decode at class context size) are open, and the routing
   table in `config/agent_context.yaml` currently says only `gemma-4-E4B-it-MLX-4bit` is routable for a
   loop at the declared 60 s budget. A second same-class model would not change that reading.
3. Fetching it before T-141 would repeat BUG-814 exactly: the download lock did not exist until today,
   and the 4.0 GB of unassemblable fragments it left behind were deleted this morning.
4. Its `config.json` nests the model under a `language_model.` prefix, unlike the served Ornith. Engine
   loadability of that SHAPE is UNVERIFIED — the arch is supported, the key layout has not been tried.

**Trigger that turns DEFER into FETCH** (any one): the incumbent A3B fails `agent_loop` on the prefill
bill after T-137 pins it; or BUG-805 measures the 27B/A3B decode such that no served model satisfies a
class the owner actually wants to run; or a named job appears that only a 35B-A3B MoE with a pre-router
can do. Then: `pipeline/hf_fetch_model.py --repo Edge0/Edge0-35B-A3B-preview` ONCE (the lock is now
enforced), verify, measure, and only then retire a loser — retire the NAME first (D-3013).

`Edge0/Edge0-8B-A1B-preview` (95 likes, apache-2.0) is the more interesting sibling for the FAST tier
(8B total / 1B active): if a measurement shows a harness loop needs more than `gemma-4-E4B` can hold,
it is the cheaper candidate. Same rule: measure the incumbent first.

## Zed: a REVIEW SURFACE, not a delegate target (D-3019)

`/Applications/Zed.app` is installed (Zed 1.9.0) and its CLI (`Contents/MacOS/cli`) OPENS paths —
`zed path:line:column`, `--wait`, `--add`, `-n`, `--foreground`. There is no headless task mode and no
server: **goose cannot delegate work into Zed**, so Zed is excluded from the delegate registry and from
`config/engine.yaml#harnesses.jobs`. It is not an engine-wired client (D-3016) and it holds no model
binding.

What it IS worth: the human review surface. After a batch, open the evidence at the exact line —
`zed governance/NLI_ANCESTOR_VERDICT_20261015.md:1` — so the owner reviews where they will do the
interactive long-context edit. The CLI is not on `PATH`; the one-line install is
`ln -s /Applications/Zed.app/Contents/MacOS/cli ~/.local/bin/zed` (owner action, no supply chain).

The repo already carries `AGENTS.md` (7,396 B) as the agent-instruction home. Whether Zed reads it, and
whether its agent panel can host one of the two installed harnesses, is **UNVERIFIED this session** —
recorded as evidence-owed, not asserted.

## Harness deployment (D-3017)

Deploy for a NAMED job class, never for a mood. `omlx launch TOOL` wires the env for a harness already
on `PATH`; it never installs one. Both `claude` and `pi` are installed and headless. The measured
per-invocation cost is the whole decision: goose one-shot 0.4 s, `pi` 28.2 s, `claude` 104.7 s.

```
eval "$(python3 pipeline/harness_env.py --print)"      # bind the contract
python3 pipeline/harness_env.py --job agent_loop       # which harness this class earns, and the command
```

A class with `harness: null` is not an omission: it says the harness LOSES there.
