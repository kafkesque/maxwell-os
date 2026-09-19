# Model Portfolio Consolidation — final stack, role map, deletions (D-2637)

**Date:** 2026-09-16 · Evidence: Tier A (9 models x 8 suites, oMLX, temp 0.0), voting suite (251 gold rows),
ARM-1/ARM-2/ARM-4, `governance/model_eval_report.md`, `governance/voting_verdict_20260916.md`, admin model metadata.

## 0. OPERATIONAL FIX — oMLX model registry no longer needs a GUI restart

**Root cause of every 'new model invisible / deleted model still listed' incident today:** oMLX caches the
registry at app start. The correct, supported reload path was undocumented in this repo but is exposed by the
local admin API:

```bash
curl -s -c /tmp/c -X POST -H 'Content-Type: application/json' \
     -d '{"api_key":"sk-maxwell-local"}' http://127.0.0.1:11435/admin/api/login
curl -s -b /tmp/c -X POST -H 'Content-Type: application/json' -d '{}' \
     http://127.0.0.1:11435/admin/api/reload
# -> {"status":"ok","message":"Re-discovered 10 models from 1 directory"}
```

`POST /admin/api/reload` = *'re-read model settings, re-discover models, preload pinned'*. It also activates
pending `settings.json` / `model_settings.json` changes **without** the `omlx-cli restart` duplicate-server trap
(D2455/D2456). Verified: registry 9 -> 10, `Ornith-1.5-9B-MLX-8bit` now live. Wrapper: `scripts/omlx_reload.py`.
Supersedes `scripts/_omlx_restart.py` (dead control socket).

## 1. Does S2 / S4 / S5 need an LLM?

### S2 — YES, an LLM is required. DSPy does not change that.
`pipeline/dspy_trainer.py` is an **optimizer** (MIPROv2 over a `DirectOMLXLM`), not a classifier: it tunes the
prompt of the *same* local generator (`Qwen3-Coder`). `stage2_extract.py`'s hybrid gate (D2276) is a
DSPy-*inspired deterministic* pre-filter. Neither replaces the extraction LLM. **S2 stays Qwen3-Coder-30B.**

### S4 — YES, an LLM is required. Both student-classifier routes are FALSIFIED by their own benchmarks.
| route | measured | verdict |
|---|---|---|
| ModernBERT 'flat' student (`classifier_modernbert_p5final`) | **discipline macro-F1 0.229**, domain macro-F1 **0.009**, domain micro-F1 0.017 | not viable — 3x worse than the LLM on discipline, **77x** worse on domains |
| ModernBERT 'hierarchical' | discipline macro-F1 0.175 | worse than flat (coarse gating hurts) |
| bge-m3 -> taxonomy-match (D2613, training-free) | **macro-F1 0.000**, micro-F1 0.324, subset-acc 1.3% (reranker sweep best 0.219) | not viable |
| LLM (Qwen3.8-27B) | discipline 0.709, domain F1 0.693 | the only working route |

Confidence is compressed to nothing (precision 1.0 only at 0.5% coverage) — the student cannot even abstain usefully.
**SetFit is not installed** and would train on the same 1027 unverified silver examples with 18/61 starved classes
(D2634), so there is no reason to expect it to beat 0.229. _Do not spend further time on trained students for S4
until the training set is verified and the starved classes are fed (D2607-D)._

**CRIBS:** the CRIBS enrichment and the classification are the SAME call (D2224, `merged_cribs_classify`).
ARM-2 showed Qwen3-Coder is the only reliable CRIBS-from-cluster producer (fb_rate 0.833, 0 invalid JSON,
30.8s median) while gpt-oss returned 0/6 valid in that harness (and only 3/6 fb at 52.5s when re-run without
`response_format`). But ARM-4's single-FB extract favours Qwen3.8 (6/6 valid vs 4/6). Keep merged, single call.

### S5 — NO LLM. None. Delete the S5 LLM roles.
`CONSTITUTION.md` / D2298: **S5 = DeBERTa-v3-large NLI only, fail-closed.** `models.nli_large` is the whole
verifier. `S5_VERIFIER` and `S5_FB_VERIFIER` in `config/model_assignments.yaml` are explicitly marked STALE and
must be removed (they are the main reason the file looks like an LLM is doing S5).

### The R5 constraint that decides S4's classifier
S2's generator is Qwen (`qwen3_moe`). R5/C8 (generator != verifier, different families) therefore **excludes every
Qwen-family model from the S4 classifier**: Qwen3.8 (`qwen3_5`), Ornith-9B (`qwen3_5`), REAP (`qwen3_5_moe`),
Qwen3-Coder (`qwen3_moe`). Seven of the ten local models are the Qwen family.
Eligible: **gpt-oss-20b (`gpt_oss`)**, gemma-4-E4B / gemma-4-12B (`gemma4`), Phi-4-mini (`phi3`), granite.
ARM-4's classification probe actually put **gpt-oss ahead on discipline (0.85 vs Qwen3.8's 0.80)** while losing
on domains (0.4825 vs 0.7356). So the current classifier is defensible on R5 AND competitive on discipline —
which is why the production-path run below is the gate, not the 0.709 headline.

## 2. What 'the production-path pipe_s4_classify run' covers

It is **not** another benchmark prompt. It calls the real `pipeline.stage4_merged_call.merged_cribs_classify()`
end-to-end on N real FBs taken from the S2/S4 checkpoint, per model, and scores the result against
`gold_4axis.jsonl`. Concretely it exercises:

1. the **real 2.4K-token `MERGED_CRIBS_CLASSIFY_SYSTEM` prompt** — CRIBS enrichment rules + discipline/domain
   disjointness (D2422 / BUG-197) + the physicist-chef-poet depth ontology — vs. my benchmark's one-line
   'You are a precise taxonomy classifier';
2. the **reasoning-suppression path** actually configured (`VERIFY_REASONING_OFF_PREFIX='Reasoning: low'`,
   `VERIFY_REASONING_OFF_MODELS`, `chat_template_kwargs.enable_thinking=false`, `thinking_budget`);
3. `call_omlx_json` — its real `max_tokens` (512 from `stage4.merged_call_max_tokens`), timeout, and retry;
4. the **fail-closed validators**: `application >= 10 chars` else `SparseClassificationError`, and
   `_validate_semantic_classification` refusing fabricated 'emerging'/'domain'/'cited' (D2355);
5. the output contract in full: `discipline, domains, depth, is_specialized, evidence, application,
   failure_mode, elaboration, keywords, jargon`.

Measured on it: valid-JSON rate, all-fields-present rate, `SparseClassificationError` rate, latency, and
**discipline accuracy + domain F1 against gold** on the same FBs.

Why it is the last table needed: prompts interact with models. My 0.709 came from a *different, simpler* prompt.
`tools/benchmark_s4_merged_production.py` and `tools/ab_test_grammar.py` already exist and did part of this
(`ab_grammar_off.json`: gpt-oss 30/30 valid JSON, 23.0s mean) — but neither scored accuracy against gold.
Until that runs, **no S4 classifier swap is justified** — not to Qwen3.8, not away from gpt-oss.

## 3. Role map — best local model per job (oMLX, temp 0.0)

| job | recommended | runner-up | evidence | confidence |
|---|---|---|---|---|
| **S2 extraction (generator)** | Qwen3-Coder-30B | — | pinned; mbpp 0.68 (best), hardcode 1.00, humaneval 0.80, 2.4s median | high (no change) |
| **S2 fast probe** | gemma-4-E4B (1.7s) | Phi-4-mini (1.3s) | E4B delegation 1.00 vs 0.50, ifeval 1.00 vs 0.92, reviewing 0.83 = 0.83 | medium — costs 0.4s |
| **S2 relabel (cross-family)** | gpt-oss-20b | gemma-4-E4B | R5-clean; 30/30 valid JSON in the production path | medium (never suite-benchmarked) |
| **S4 merged CRIBS + classify** | gpt-oss-20b (keep) | gemma-4-E4B | R5-clean; ARM-4 discipline 0.85 (n=20) >= Qwen3.8 0.80; 30/30 valid @23s | medium — pending production-path table |
| **S4 depth** | gemma-4-E4B | — | D2454/D2483 tuning already targeted gemma depth | low (not separately benchmarked) |
| **S5 verification** | **NO LLM** — DeBERTa-v3-large NLI | — | D2298, fail-closed | high |
| **Embeddings / rerank** | bge-m3 (Ollama) / bge-reranker-v2-m3 | — | — | high |
| **FAST / light coding** | **Qwen3-Coder-30B** | Phi-4-mini (fast but 0.48 mbpp) | mbpp 0.68 best, hardcode 1.00, 1.6-3.7s | high |
| **COMPLEX / hard coding** | **Qwen3.8-27B** | REAP-19B (value pick) | humaneval 0.96 best, hardcode 1.00; REAP 0.60 mbpp + 1.00 hardcode @3.4s | high |
| **Long-context analysis** | **UNKNOWN — no data** | Qwen3-Coder (only niah run: 0.667, n=9, 3 transport errors) | all models expose 131k-262k ctx; nothing measured past 24k | **none — Run B is the gate** |
| **Planning (strategic)** | **Qwen3.8-27B** | Qwen3-Coder-30B (5x faster) | delegation 1.00 vs 0.83; the `planning` suite ties 1.00 for 4 models at n=3 -> uninformative | low |
| **Tool calling / research agent** | **Ornith-1.5-35B-A3B-REAP-19B** | Qwen3.8-27B / Qwen3-Coder | toolcalling **1.00 — the only model above 0.75** @3.0s; gpt-oss 0.00 (never give it tools) | low-medium (n=4) |
| **Orchestrating** | **Qwen3.8-27B** | Qwen3-Coder | ARM-4 orchestrating 1.0 vs gpt-oss 0.5; delegation 1.00 | medium |
| **Reviewing / analysing** | **Qwen3.8-27B** | gemma-4-E4B (5x faster, 0.83) | reviewing 1.00 vs 0.83 | medium |
| **Classification / voting decider** | **Qwen3.8-27B** | nobody (no local 3rd voter exists) | voting 0.709 vs next-best 0.430 | high |

**Coding and instruction-following are orthogonal** — that is the single most consequential structural finding:
gemma-4-E4B is a 1.00 delegator / 1.00 ifeval / 0.16 humaneval model; gpt-oss is 0.88 humaneval / 1.00 hardcode /
0.00 tool calling. 'Best coder' and 'best delegator' are different questions and must be different roles.

## 4. Deletions (evidence-based; nothing deleted without a recorded reason)

| model | size | case |
|---|---|---|
| **granite-4.2-8b-MLX-8bit** | 9.13 GB | Last or near-last on **every** axis; ALL 0.353, below the Phi-4-mini (0.528) it was meant to replace. Its only rationale was R5 family diversity — already supplied by gemma-4-E4B (`gemma4`) and gpt-oss (`gpt_oss`). **DELETE.** |
| **gemma-4-12B-it-qat-OptiQ-4bit** | 8.70 GB | ALL 0.448, toolcalling **0.00**, humaneval 0.36, **40.5 s/call**. No role where E4B isn't better and ~24x faster; not a unique family (shares `gemma4` with E4B). **DELETE.** |
| **Phi-4-mini-instruct-8bit** | 3.99 GB | Owns exactly one job (the 1.3s S2 probe) and loses it on task accuracy to E4B (delegation 0.50 vs 1.00). Cheap and fast, so this is a judgement call: 3.99 GB buys 0.4 s/probe. **RECOMMEND DELETE, user's call.** |
| Ornith-1.5-9B loser of the 4-bit/8-bit A/B | 6.94 or 9.30 GB | A/B running now (`governance/model_eval_ornith_ab.log`, PID 8815). Keep the winner. **PENDING.** |
| ~~Ornith-1.5-35B-A3B-REAP-19B~~ | 12.08 GB | **REVERSED — DO NOT DELETE.** 3rd overall (0.778), toolcalling 1.00, hardcode 1.00, planning 1.00, mbpp 0.60 (2nd). The earlier prune case rested on ARM-4 classification alone. |

Already deleted earlier: DeepSeek-R1-0528-Qwen3-8B-4bit (4.3 GB), and 3 models before it
(`governance/pruned_models_20260915.md`). Potential release now: **17.8 GB**, or **21.8 GB** with Phi.

## 5. Stale / phantom references found in `config/model_assignments.yaml` (must fix or the file lies)

| entry | problem |
|---|---|
| `T2_GATE`, `T3_GATE` | point at **`Phi-4-mini-instruct-4bit`, which does not exist** in the registry (only `-8bit`). Any caller gets a 404. |
| `self_critique.primary: deepseek-r1-8b` | **the model is deleted.** Dangling routing entry. |
| `ORCHESTRATOR`, `CODING_DRAFT`, `LIGHTWEIGHT_CODER`, `DRAFT_TRIAGE` | all set to Phi-4-mini; the data says orchestrating belongs to Qwen3.8 (1.0 vs 0.5) and light coding to Qwen3-Coder (0.68 vs 0.48 mbpp). |
| `S5_VERIFIER`, `S5_FB_VERIFIER` | stale by their own notes — S5 has no LLM (D2298). Remove. |
| `HIGH_CAPABILITY` fallbacks | `Qwen3-Coder` listed twice, gemma-4-26B phantom commented out. |
| `depth_reasoning.primary: qwen-max` | a **cloud** model as the primary for a pipeline role — check against C1/C3. |
| header | file is the 2026-07-08 merge of three dead registries; `# Updated:` is 2026-08-06. It needs a rewrite, not a patch. |

## 6. Research / media stack — this is harness, not model capability

No text LLM can transcribe audio, watch a video, or browse X. The model-side requirements are only
(a) tool/function calling, (b) long-context summarisation of scraped text, (c) strict-JSON structured extraction:

| need | state |
|---|---|
| RSS / `feed.opml` (67 outlines, **36 `xmlUrl`** — GitHub topic feeds, repos, YouTube channels, X sources) | **`feedparser` installed** — consumable today, no model needed to fetch |
| web scraping | `trafilatura` + `newspaper` + `bs4` + `playwright` + `requests` installed |
| Reddit | `praw` installed |
| YouTube | `yt-dlp` **CLI present, python module missing**; `youtube_transcript_api` missing. Captions are extractable without ASR — ASR only needed for captionless video |
| X / Twitter | **no client** (`tweepy`, `atproto` absent) — RSS bridge or the OPML's X sources only |
| ASR | **nothing installed** (`whisper`, `mlx_whisper`, `faster_whisper` all absent) |
| Vision / OCR | **no dedicated VLM** — but note the admin API reports `engine_type=vlm` for **Qwen3.8-27B, Ornith-REAP-19B, gemma-4-12B, gemma-4-E4B**. Four models may already accept images. **Worth a 1-image smoke test before buying any OCR stack.** |

Binding model for the research agent: **REAP-19B** (the only 1.00 tool caller), orchestrated by Qwen3.8.