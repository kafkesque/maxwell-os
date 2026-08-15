# Maxwell OS — Buglog
> **Last updated:** 2026-08-15 10:11 (D2359 production-verified: 72.0% acc @ 7.2s median / 8.3s mean; D2361 default-model mismatch fixed; W7 `deathpectation` resolved = private Anytype space name)
> **Next review:** After T1.1 full S1.5→S6 run

---

## 🔴 BUG-129 — 2026-08-14 — S4 GPT-OSS `reasoning_effort`/`enable_thinking` are silent no-ops (D2359 void)
- **Symptom:** D2359 claimed `reasoning_effort: low` (~17% faster) + `enable_thinking: false` (~22% faster). Verified against the oMLX 0.5.1 request schema: `ChatCompletionRequest` (pydantic v2, `extra='ignore'`) has **no top-level `reasoning_effort` or `enable_thinking` fields** — the supported knobs are `chat_template_kwargs` (dict) and `thinking_budget` (int). The pipeline sends both as top-level payload keys → **silently dropped**. The observed "17%/22%" speedups were noise.
- **Root cause:** `pipeline/omlx_call.py` emits `payload["reasoning_effort"]` / `payload["enable_thinking"]` at top level. oMLX only reads `request.chat_template_kwargs` (merged into the chat template) and `request.thinking_budget`.
- **Verified:** (1) pydantic model dump proves top-level keys are dropped. (2) Live A/B on the production `DEPTH_FOCUSED_PROMPT`: top-level flags + `Reasoning: none` → 5.6s / 394 reasoning chars; `chat_template_kwargs={"enable_thinking": false}` + `Reasoning: low` → 4.6s / 311 chars; `thinking_budget=64` → 4.6s / 306 chars. (3) Harmony format doc confirms valid reasoning levels are only `low`/`medium`/`high` — **`Reasoning: none` is not a valid level** and is ignored.
- **Correct levers (verified):** `chat_template_kwargs={"enable_thinking": false}` AND/OR `thinking_budget: <N>` (oMLX-native), and system-prompt `Reasoning: low` (harmony). None fully eliminate reasoning (GPT-OSS is a native reasoning MoE, 21B/3.6B-active); they cap CoT length.
- **Status:** 🟢 FIXED — 2026-08-14 (D2359 implemented: `chat_template_kwargs` + `Reasoning: low`)
- **Files:** `pipeline/omlx_call.py`, `pipeline/pipeline_paths.py`, `pipeline/stage4_merged_call.py`, `config/pipeline_config.yaml`
- **Source:** live oMLX 0.5.1 schema + source inspection + empirical A/B (2026-08-14, this session)
- **A/B VERIFIED (harness, 2026-08-14, 50-FB golden set + 4 real merged CRIBS):**
  - Focused depth: A=67.3% acc / 14.2s vs **B=76.0% acc / 7.7s (1.84×)**, C(thinking_budget=128)=76.0% / 7.2s (1.97×). Zero fail-closed in B/C.
  - Merged CRIBS: A=68.3s vs **B=53.5s (1.28×)**, reasoning chars 3012→2079 (−31%), all outputs complete.
- **PRODUCTION VERIFIED (2026-08-14, 50-FB golden through real `classify_depth_focused()`):**
  - GPT-OSS focused depth: 67.3% → **72.0% acc (+4.7pt)** and 14.2s → **7.2s median / 8.3s mean (1.95× on median)**. Zero fail-closed.
  - ⚠️ The harness's 76% did NOT reproduce on the production path — the harness used its own `requests.post` with `response_format=json_object` + a fuller system message, not the production `call_omlx` path. Production truth = 72.0%.
  - **Net: `Reasoning: low` + `chat_template_kwargs={"enable_thinking":false}` is faster AND more accurate than `Reasoning: none` in production (verified).**
  - Remaining `domain→cross-domain` over-prediction (domain 9/22) is a pre-existing prompt/ontology/golden-label ambiguity, NOT a regression from these flags.

## 🟡 BUG-130 — 2026-08-14 — GPU kernel panic loading dense Qwen3.8-27B in parallel (IOGPUGroupMemory)
- **Symptom:** `panic(cpu 0): IOGPUGroupMemory.cpp:220 Assertion failed: result != kIOReturnSuccess` in `omlx-server` (Python pid) while loading `Qwen3.8-27B-MLX-4bit` (15 GB dense, 48 linear-attn + 16 full-attn layers) on a second OMLX server (:11436) concurrently with the main pipeline server + 3 research delegates.
- **Root cause:** Dense 27B model + concurrent GPU consumers exhausted the Metal driver's GPU memory (IOGPUGroupMemory assertion). Qwen3.8-27B is **dense** (not MoE) — ~15 GB weights + KV on a 64 GB M1 Max, and the two OMLX servers + delegates competed for the same GPU budget.
- **Fix:** Kill the duplicate GUI OMLX server on :11436; keep a single server (:11435). **Run research + benchmark strictly sequentially, one model at a time.** Qwen3.8 loads cleanly in isolation (0 loaded models → 18 GB single load, no panic).
- **Status:** 🟢 MITIGATED — 2026-08-14 (process discipline; no code change)
- **Files:** n/a (operational)
- **Source:** kernel panic report 2026-08-14 + successful isolated re-load

---

## 🟢 BUG-131 — 2026-08-14 — `classify_depth_focused()` default model silently diverged from production (D2361)
- **Symptom:** `classify_depth_focused(fb_data)` with `model=None` defaulted to `S4_DEPTH_MODEL` (= `gemma-4-E4B-it-MLX-4bit`, the gated FrugalGPT cheap model) unconditionally — even when `depth_frugal_enabled=false`. Any caller that omitted `model` silently ran Gemma instead of GPT-OSS (the production depth classifier).
- **Root cause:** The function's internal `if model is None` branch read `S4_DEPTH_MODEL` directly, ignoring `S4_DEPTH_FRUGAL_ENABLED`. Production (`stage4_merge.py`) passes `model=depth_model` explicitly (`S4_DEPTH_MODEL if frugal else VERIFY_MODEL`), so the mismatch was masked there — but a naive caller (or a benchmark) got the wrong model. This produced a false "production" benchmark (64% @ 2.3s = Gemma) before it was caught.
- **Fix (D2361):** default now mirrors `stage4_merge.py` routing: `S4_DEPTH_MODEL if S4_DEPTH_FRUGAL_ENABLED else VERIFY_MODEL`.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merged_call.py`
- **Source:** independent re-verification of D2359 production numbers (discovered the 64% "GPT-OSS" measurement was actually Gemma)

---

## 🟠 BUG-126 — 2026-08-14 — Legacy direct-classify path still not fail-closed (D2357 gap)
- **Symptom:** D2357 made `merged_cribs_classify()` and `batch_cribs_classify()` fail-closed, but the legacy direct path (`call_omlx_json(class_prompt)` when both batch and merged are disabled/failed) still turned a sparse response into `emerging`/`cited` via empty-raw-label mapping.
- **Fix (D2358):** the direct path now raises `SparseClassificationError` on missing `discipline`/`domains`/`evidence` and quarantines the FB (`classification_errors += 1`). `depth` is intentionally not checked there (overridden by the focused depth call). BUG-120 is now unconditional across all configs.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT re-audit (2nd pass, HIGH) + independent re-verification

## 🟡 BUG-127 — 2026-08-14 — k-means split exception silently swallowed (`except Exception: pass`)
- **Symptom:** `split_cluster_by_kmeans()` wrapped the whole embed+cluster step in `except Exception: pass`, hiding split failures (C16).
- **Fix (D2358):** log the failure (`⚠️ k-means split failed …`) while retaining the deliberate fail-safe (return the unsplit cluster).
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage2_extract.py`
- **Source:** ChatGPT re-audit (2nd pass, MEDIUM) + independent re-verification

## 🟡 BUG-128 — 2026-08-14 — Dead `_render_3zone_body_old_end()` stub + literal `MAX_PER_BOOK=2`
- **Symptom:** (1) `_render_3zone_body_old_end()` remained as a dead `pass` compatibility stub (C19). (2) `MAX_PER_BOOK: int = 2` was a local magic number while `max_probe_samples` was already config-driven (C12).
- **Fix (D2358):** removed the dead stub; added `stage2.max_probe_per_book` (config) → `S2_MAX_PROBE_PER_BOOK`.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage6b_anytype_push.py`, `pipeline/stage2_extract.py`, `pipeline/pipeline_paths.py`, `config/pipeline_config.yaml`
- **Source:** ChatGPT re-audit (2nd pass, LOW) + independent re-verification

---

## 🔴 BUG-120 — 2026-08-14 — Semantic fail-open: merged/batch classification fabricates `emerging`/`domain`/`cited` (C16)
- **Symptom:** `merged_cribs_classify()` and `batch_cribs_classify()` filled a *present-but-sparse* model response's missing `discipline`/`domains`/`depth`/`evidence` with `emerging`/`["emerging"]`/`domain`/`cited`. D2355 had made only the *missing-entry* case fail-closed; a malformed-but-present entry still became valid-looking semantic data without raising, so `max_failed_ratio: 0.0` could not catch it.
- **Root cause:** a single `defaults` dict mixed non-semantic CRIBS enrichment (`application`/`failure_mode`/`elaboration`/`keywords`) with semantic classification fields, applying the same silent-fill to both.
- **Fix (D2357):** split the defaults — CRIBS fields default safely (empty); semantic fields are validated fail-closed via `_validate_semantic_classification()` which raises `SparseClassificationError` on any missing/empty/invalid `discipline`/`domains`/`depth`/`evidence`. Callers fall back to individual classification and account the failure.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merged_call.py`
- **Source:** ChatGPT re-audit (BLOCKER #2/#3) + independent re-verification

## 🔴 BUG-121 — 2026-08-14 — Intimacy lattice not fail-safe: null/config failure resolves `public` (sovereignty)
- **Symptom:** `config/intimacy_policy.yaml` declares `null_handling: intimacy: private` and "ambiguity/NULL resolves upward (D369)", but `resolve_intimacy()` initialized at `public`, had no null-escalation, and `_load_policy()`/`_load_anchors()` swallowed load exceptions to `{}`. `route_space()` fell back to `non_private`. A policy/config failure could route an FB to public/non-private against the declared privacy floor.
- **Fix (D2357):** (1) `_load_policy()`/`_load_anchors()` now log AND record failures; (2) `resolve_intimacy()` fails closed to `private` on any config error (`R0-config-failure`) and on a wholly absent signal set (`R0-null`); (3) `route_space()` falls back to `private`, never `non_private`; (4) `LEVELS`/`space_routing` now read from YAML (C12) with a code fallback only for a missing file.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/intimacy_lattice.py`
- **Source:** ChatGPT re-audit (BLOCKER #4) + independent re-verification

## 🟠 BUG-122 — 2026-08-14 — `source_principle_ids` empty for v3 FBs (provenance gap)
- **Symptom:** S4 read only `p.get("principle_id")` to build `source_principle_ids`, but S2 v3 records emit `fb_id` (not `principle_id`), so the field was `[]` for every normal v3 FB.
- **Fix (D2357):** read `fb_id` first, retain `principle_id` as legacy fallback (matches the `fb_id or principle_id` pattern used elsewhere in S4).
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT re-audit (HIGH #5) + independent re-verification

## 🟠 BUG-123 — 2026-08-14 — Downstream FB-ID rehash fallback after S4 name normalization (identity drift)
- **Symptom:** `fb = {"fb_id": fb_data.get("fb_id") or make_hash_id(name, definition)}` re-hashed a missing-ID record from the *normalized* name, which would drift from S2's hash of the un-normalized name — breaking the D2350 invariant.
- **Fix (D2357):** missing `fb_id` is now a hard error (FB quarantined, `failed += 1`), never a silent re-hash. Removed the now-unused `make_hash_id` import.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT re-audit (HIGH #9) + independent re-verification

## 🟠 BUG-124 — 2026-08-14 — `keywords` rendered as body content; `jargon` rendered before elaboration
- **Symptom:** `content_types.yaml` moved `keywords` to `metadata.discovery` and declares `jargon` renders AFTER elaboration (D2349), but `stage6b_anytype_push.py` rendered `**KEYWORDS**` in the body and placed `jargon` in Zone 2 (before Zone 3 elaboration).
- **Fix (D2357):** `keywords` removed from body rendering and added to YAML frontmatter + JSON payload metadata; `jargon` moved after elaboration in the 3-zone body.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage6b_anytype_push.py`
- **Source:** ChatGPT re-audit (HIGH #7/#8) + independent re-verification

## 🟡 BUG-125 — 2026-08-14 — S2 hybrid-gate failure silently swallowed (`except Exception: pass`)
- **Symptom:** the D2276 pre-extraction hybrid gate wrapped its decision in `except Exception: pass`, so a gate failure was invisible (violates C16 "no silent errors").
- **Fix (D2357):** log the gate failure (`⚠️ Hybrid gate error …`) while retaining the deliberate fail-open (prefer false-positive extraction to data loss).
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage2_extract.py`
- **Source:** ChatGPT re-audit (MEDIUM #12) + independent re-verification

---

## 🔴 BUG-108 — 2026-08-14 — S4 depth inference failure silently becomes `depth="domain"` (C16 violation)
- **Symptom:** `classify_depth_focused()` returns `"domain"` on *any* exception (`except Exception: return "domain"`) and on no-match (`return "domain"`). GPT-OSS timeout, cold-reload empty content, transport error, malformed output, unexpected answer, and a *legitimate* `domain` all collapse to the same value — semantic contamination.
- **Root cause:** the focused depth call omits `Reasoning: none` (batch/merged do send it), uses `depth_max_tokens: 512` (truncates GPT-OSS reasoning), parses by substring (`for d in (...): if d in text`), and the exception handler manufactures `"domain"` instead of propagating/quarantining. `call_omlx()` raises `KeyError` when `content is None` (reasoning-model cold reload), which is exactly what the handler swallows.
- **Fix (D2351):** fail-closed — propagate failure into `classification_errors` (S4 `max_failed_ratio: 0.0` already exits non-zero); exact-token parser (accept exactly one of 4 labels); single fallback policy via `S4_DEPTH_FALLBACK_DEPTH`; send `Reasoning: none` on the focused path; bump `depth_max_tokens` to 1024.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (fail-closed depth (D2351)).
- **Files:** `pipeline/stage4_merged_call.py`, `pipeline/omlx_call.py`, `config/pipeline_config.yaml`
- **Source:** 4-LLM audit (ChatGPT depth-audit) + independent re-verification

## 🔴 BUG-109 — 2026-08-14 — `depth_max_tokens: 512` contradicts measured ~1024 GPT-OSS requirement
- **Symptom:** governance `S4_BOTTLENECK_ANALYSIS.md` live-measured GPT-OSS needs `max_tokens ≥ 1024` to emit the answer after reasoning (1024 → `"specialized"`); production config `stage4.depth_max_tokens: 512` overrides the verifier model-level `max_tokens: 1024`. The 512 budget truncates reasoning, triggering BUG-108's failure path.
- **Root cause:** config↔governance drift; the `classify_depth_focused()` docstring "512 is plenty — one word answer" is stale (contradicted by the repo's own measurement).
- **Fix (D2351):** `depth_max_tokens` 512 → 1024; correct the stale docstring.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (depth_max_tokens 1024 (D2351)).
- **Files:** `config/pipeline_config.yaml`, `pipeline/stage4_merged_call.py`
- **Source:** 4-LLM audit + independent re-verification

## 🟠 BUG-110 — 2026-08-14 — `source_segments` declared provenance but dropped at S4/S6
- **Symptom:** `config/content_types.yaml` declares `metadata.provenance: [..., source_segments, ...]`; S2 emits `source_segments`; but S4's FB record rebuild copies `source_clusters`/`source_books`/`source_principle_ids`/`evidence_passages` and **never `source_segments`**. Zero references in `stage4_merge.py`/`stage5_verify.py`/`stage6_commit.py`. Segment-level provenance is lost.
- **Fix (D2352):** carry `source_segments` into the S4 FB dict + add an S6 column.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (source_segments S4→S6 (D2352)).
- **Files:** `pipeline/stage4_merge.py`, `pipeline/stage6_commit.py`, `config/content_types.yaml`
- **Source:** 4-LLM audit (ChatGPT + Claude) + independent re-verification

## 🟠 BUG-111 — 2026-08-14 — `evidence_passages`/`evidence_passages_shown` not persisted to SQLite
- **Symptom:** S4 emits `evidence_passages` + `evidence_passages_shown`; S5 passes them through (`vfb = dict(fb)`); but S6's `fbs` schema + INSERT have no such columns — verbatim source quotes are dropped from the primary SQLite KB. (The Parquet snapshot *does* keep them via full-dict `from_pylist`; `source_text` IS a SQLite column.)
- **Fix (D2352):** add columns, OR formally document Parquet as the verbatim-evidence store.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (evidence_passages/_shown → SQLite (D2352)).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** Claude audit (Q5) + independent re-verification

## 🟠 BUG-112 — 2026-08-14 — `is_summary` declared classification but dropped end-to-end
- **Symptom:** `content_types.yaml` declares `is_summary` under `classification`; S2 emits it; but S4's FB dict omits it and S6's INSERT omits it → the `is_summary INTEGER DEFAULT 0` column is never written (always 0).
- **Fix (D2352):** persist `is_summary` through S4 → S6.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (is_summary end-to-end (D2352)).
- **Files:** `pipeline/stage4_merge.py`, `pipeline/stage6_commit.py`
- **Source:** 4-LLM audit + independent re-verification

## 🔴 BUG-113 — 2026-08-14 — Singleton S2→S4 index inconsistency (silently skipped)
- **Symptom:** `load_stage2_fbs_via_clusters()` loads singleton FBs into the `clusters` list *and* its local `principles_idx`; but `run_stage4()` discards that index and calls `load_stage2_principles()`, which reads ONLY `STAGE2_CHECKPOINT` (never `STAGE2_SINGLETON_OUTPUT`). Singleton clusters therefore have `principle_ids` absent from `principles_idx` → `if not cluster_principles: … "empty" … continue` silently skips them.
- **Root cause:** two loaders diverge — one (clusters) includes singletons, the other (principles index) does not.
- **Note:** ChatGPT initially flagged this (correct), then wrongly "retracted" it as FIXED. It is still broken.
- **Fix (D2353):** `run_stage4()` should reuse the `principles_idx` returned by `load_stage2_fbs_via_clusters()`.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (singleton index reuse (D2353)).
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT audit (Q4, then retracted) + independent re-verification

## 🟠 BUG-114 — 2026-08-14 — Batch missing-output silently becomes synthetic semantic values
- **Symptom:** `batch_cribs_classify()` fills missing FB entries with `defaults = {"depth":"domain","discipline":"emerging","domains":["emerging"],"evidence":"cited",…}` — a missing model output becomes valid-looking semantic data (same C16 hidden-error class as BUG-108).
- **Fix (D2355):** fail-closed / flag missing entries instead of manufacturing defaults.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (batch missing fail-closed (D2355)).
- **Files:** `pipeline/stage4_merged_call.py`
- **Source:** 4-LLM audit + independent re-verification

## 🟠 BUG-115 — 2026-08-14 — Depth benchmark ≠ production parser; 87.5% vs 37.5/50% drift; fallback orphaned
- **Symptom:** (1) `tools/benchmark_s4_depth_gptoss.py` uses direct `requests` + `reasoning_content` fallback; production `classify_depth_focused()` uses `call_omlx` (raises on `content=None`) + content-only — the benchmark is not a production-path test. (2) governance claims 87.5% focused vs 38% long, while the benchmark docstring still frames GPT-OSS as "third entrant after Phi 37.5% / Gemma 50%". (3) `S4_DEPTH_FALLBACK_DEPTH` is loaded but never used by the focused classifier (only the `elif` branch when `depth_focused_classification=False`).
- **Fix (D2351):** run benchmark through production `classify_depth_focused()`; make one authoritative number; route fallback through `S4_DEPTH_FALLBACK_DEPTH`.
- **Status:** 🟢 FIXED — 2026-08-14: `tools/benchmark_s4_depth_frugal.py` runs `classify_depth_focused()` through the PRODUCTION path (`call_omlx` + `_parse_depth_token`, fail-closed) for both GPT-OSS and the frugal depth model. This is now the authoritative depth benchmark (S5 closed). The old `benchmark_s4_depth_gptoss.py` remains as a historical direct-API baseline.
- **Files:** `tools/benchmark_s4_depth_frugal.py` (new), `pipeline/stage4_merged_call.py`, `pipeline/stage4_merge.py`
- **Source:** ChatGPT depth audit + independent re-verification

## 🟡 BUG-116 — 2026-08-14 — `s3_original_domain` vestigial dead column/field (bloat)
- **Symptom:** `CREATE TABLE fbs` omits `s3_original_domain` but `insert_fb()` INSERTs it (value always `""` — S4 removed it per D2130). Migrated by `_migrate_add_column()` so NOT a fresh-DB failure (ChatGPT mislabeled this as a BLOCKER). Dead column + dead INSERT field.
- **Fix (D2355):** remove from INSERT, migration, and (eventually) DB.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (s3_original_domain removed (D2355)).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** ChatGPT audit (BLOCKER claim) → corrected via independent re-verification

## 🟡 BUG-117 — 2026-08-14 — Secondary `STAGE2_CHECKPOINT` writers bypass self-verifying path
- **Symptom:** `probe_run.py:225` writes via bare `open(...).write()` (no `safe_write`, no self-verify, violates C6); `repair_elaboration.py:237` uses `safe_write` but skips the `load_jsonl` self-verify re-read. Both are reimplementations instead of calling `_write_checkpoint_jsonl()`.
- **Fix:** route both through `_write_checkpoint_jsonl()`.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (checkpoint writers unified (BUG-106 residual)).
- **Files:** `pipeline/probe_run.py`, `pipeline/repair_elaboration.py`
- **Source:** Claude audit (Q6) + independent re-verification

## 🟠 BUG-118 — 2026-08-14 — `insert_embedding()` swallows failures silently
- **Symptom:** `insert_embedding()` catches `Exception` and returns `False` with no per-FB log; S6 only reports aggregate vector degradation. A partially-unembedded committed corpus is invisible.
- **Fix (D2355):** log which FB failed; surface in commit summary.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (insert_embedding logs failures (D2355)).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** ChatGPT audit + independent re-verification

## 🟠 BUG-119 — 2026-08-14 — `jargon` (core body) excluded from FTS5
- **Symptom:** FTS5 virtual table indexes only `name, definition, keywords`; `jargon` is classified `core_body` but is not full-text searchable — body content invisible to retrieval.
- **Fix:** add `jargon` to the FTS5 index (retrieval-policy decision, not persistence loss).
- **Status:** 🟢 FIXED — implemented 2026-08-14 (jargon added to FTS5).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** Claude audit (Q2 side-finding) + independent re-verification

---

## 🟢 D2350 — 2026-08-14 — S4 fb_id drift + source_clusters semantic drift + name-collision hash pollution
- **Symptom:** Deep-audit of T1.1 canary S4 output found (1) 73 of 279 FBs would get a NEW fb_id between S2→S4 because S4 re-hashed `make_hash_id(name, definition)` AFTER `normalize_fb_name()` title-cased the name — silently breaking FB identity and `source_clusters` provenance; (2) `load_stage2_clusters()` stored the fb_id as `cluster_id`, so `source_clusters` in S4/DB held an fb_id instead of the real cluster id (`cluster_48_s1_sub1`); (3) name collisions got a raw 64-char cluster hash appended (`(Cluster <hash>)`), polluting human-readable names.
- **Root cause:** identity re-derived at merge time instead of preserved from extraction; cluster id overridden by fb_id; collision suffix used the raw hash.
- **Fix (D2350):** preserve S2 `fb_id` (`fb_data.get("fb_id") or make_hash_id(...)`); use `fb.get("source_cluster")` as `cluster_id` (convergent + singleton); short numeric probe suffix `(2)`, `(3)`, ….
- **Status:** 🟢 FIXED (2026-08-14, D2350). Simulated: 73 would-drift records now stable, 200 already stable, 5 no S2 match.
- **Files:** `pipeline/stage4_merge.py`
- **Source:** T1.1 canary deep-audit (this session)

## 🟠 BUG-107 — 2026-08-14 — 2 single-source FBs leaked into final DB despite `--only-convergent`
- **Symptom:** `Hybrid Sorting Algorithm` and `Price Reduction Profit Maximization` are single-source FBs (1 source book) yet present in the final 279-committed DB. 207 convergent parents → 339 sub-cluster targets → 280 FBs; exactly 2 are single-source.
- **Root cause:** `split_cluster_by_kmeans()` emits sub-clusters whose per-sub-cluster
  `is_convergent` is recomputed as `sub_sid_count >= 2`; a sub-cluster can drop to 1 source
  (`is_convergent=False`) yet still be appended to `expanded_targets` (fresh-probe path) —
  bypassing the `--only-convergent` filter.
- **Fix:** filter sub-clusters by `is_convergent` under `--only-convergent` (fresh-probe
  path). Cache-load path already filtered (`stage2_extract.py:1129`).
- **Status:** 🟢 FIXED (2026-08-14) — `stage2_extract.py` split-probe now drops single-source
  sub-clusters under `--only-convergent`.
- **Files:** `pipeline/stage2_extract.py`
- **Source:** T1.1 canary deep-audit (this session)

## 🟠 BUG-106 — 2026-08-14 — S2 checkpoint mixed JSONL/pretty-printed (breaks re-run/resume)
- **Symptom:** `stage2_extract/canary/checkpoint.jsonl` has 456 lines but only 274 are standalone JSONL; 102 are pretty-printed fragments (6 of 280 FB records multi-line). `load_jsonl` (D2332 fail-closed) RAISES on it. S4 loaded the 280 FBs correctly *this* run, but a re-run/resume would fail-closed.
- **Root cause:** legacy on-disk artifact. All current writers were already compact JSONL;
  the only `indent=2` in `stage2_extract.py` (`:685`) is the few-shot *prompt* builder, NOT a
  checkpoint write. The corrupt canary checkpoint was written by pre-D2332 code.
- **Fix:** `_write_checkpoint_jsonl()` — single self-verifying write path (`safe_write` +
  immediate `load_jsonl` re-read) at all `STAGE2_CHECKPOINT` write sites; quarantined the
  corrupt on-disk canary checkpoint.
- **Status:** 🟢 FIXED (2026-08-14) — self-verifying writer + corrupt artifact quarantined.
- **Files:** `pipeline/stage2_extract.py`
- **Source:** T1.1 canary post-run checkpoint format audit (this session)

## 🔴 BUG-105 — 2026-08-14 — Embedding instability: 60s timeout + keep_alive thrash (3% drop, D2275 gate exceeded)
- **Symptom:** T1.1 canary S1.5 embedding: 12 batches failed with HTTP read timeouts (`Read timed out (read timeout=60)`), 768 segments dropped = 3.07% (D2275 gate = 0.5%). A re-run stalled at ~2 seg/s with bge-m3 showing "Stopping..." (VRAM unload mid-run).
- **Root cause:** (1) `batch_embed` hardcoded `timeout=60` (C12 violation) — too short under 4-worker concurrent load (Ollama serializes `/api/embed`). (2) bge-m3 default 5-min keep_alive → unloaded between batches → cold-reload stalls.
- **Fix (D2348):** config-driven `services.ollama.embed_timeout: 180` + `embed_keep_alive: -1`. Verified: 0 failures, ~12 seg/s, 34.5 min for 25K segments (was 12 failures / 2-3 seg/s).
- **Status:** 🟢 FIXED (2026-08-14, D2348).
- **Files:** `pipeline/ollama_embed.py`, `pipeline/pipeline_paths.py`, `config/pipeline_config.yaml`
- **Source:** T1.1 canary run (this session)

---

## 🟠 BUG-104 — 2026-08-13 — sqlite-vec cannot load: `load_extension` missing on python.org Python 3.12.1
- **Symptom:** `stage6_commit.py init_db()` warns "sqlite-vec not available" on every run; the `vec_fbs` virtual table is never created (verified: current `maxwell.db` has `fbs`/`fbs_fts` but NO `vec_fbs`). Vector search has therefore silently never worked — retrieval falls back to FTS only. Masked by the broad `except (ImportError, Exception)` catch.
- **Root cause:** Python 3.12.1 (python.org framework build, `/Library/Frameworks/Python.framework/...`, SQLite 3.43.1) compiled WITHOUT `load_extension`/`enable_load_extension`. `sqlite_vec.load(conn)` internally calls `conn.load_extension(...)` → `AttributeError: 'sqlite3.Connection' object has no attribute 'load_extension'`. The BUG-012/P0.11 fix (`conn.enable_load_extension(True)` → `sqlite_vec.load(conn)`) itself fails on this build. The except prints a misleading "Install: pip install sqlite-vec" (the package IS installed).
- **Fix:** (1) Use a Python build with `load_extension` support — Homebrew Python (`brew install python@3.12`) or conda-forge Python; OR (2) improve `init_db` to distinguish `ImportError` (package missing) from `AttributeError` (load_extension unavailable) and surface the real remediation. NOT a data-loss blocker: FTS fallback works (verified by stress test).
- **Status:** 🟡 PARTIAL (2026-08-14) — code now distinguishes `ImportError` (package missing)
  from `AttributeError` (load_extension unavailable) and prints the correct remediation; the
  underlying environmental issue (python.org build lacks `load_extension`) still requires
  Homebrew/conda Python for vector search. FTS fallback continues to work.
- **Files:** `pipeline/stage6_commit.py`
- **Source:** This session — live verification of vector-search readiness during `just preflight` (BUG-012's fix assumed `enable_load_extension` exists).

---

## 🔴 BUG-102 — 2026-08-13 — S1.5 embedding-drop index misalignment (silent cluster→segment corruption)
- **Symptom:** If the Ollama embedding path drops any segment (batch fails; drop rate ≤0.5% permitted by D2275), the returned embedding array is shorter than the original segment list, but cluster records are built against the original list → embedding[i] no longer corresponds to segments[i]. Wrong segment → wrong cluster → wrong source books → wrong convergence → wrong evidence, with NO exception. Hits the principle path, not just the non-type pass.
- **Root cause:** `embed_segments()` filters `segments` locally on drop (`stage1_5_embed_cluster.py:320` — `segments = [segments[i] for i in successful_indices]`) then returns only `embeddings` (`:327`). Caller `run_stage1_5` (`:598`) receives embeddings only and passes the ORIGINAL `segments` to `build_clusters` (`:609`). The local reassignment never propagates to the caller.
- **Fix (D2346):** Return `(filtered_segments, embeddings)` from `embed_segments()` (or raise when `n_dropped > 0`). Assert `len(segments) == len(embeddings)` immediately before FAISS clustering. Add injected-drop tests (first/middle/last segment).
- **Status:** 🟢 FIXED (2026-08-13) — `embed_segments()` returns `(segments, embeddings)` on both MPS + Ollama paths; caller asserts `len(segments) == len(embeddings)` before `build_clusters()`. `just integrity` 17/17, `just preflight` stress PASS.
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Source:** ChatGPT audit (`chatgpt009.md`) Block #2 / Seat 2 / Seat 3; independently re-verified against code this session.

## 🟠 BUG-103 — 2026-08-13 — e2e convergence metric uses filename identity, not canonical source IDs
- **Symptom:** e2e reports `convergent_clusters` 24.5% (39/159) using `len(set(c["source_books"])) >= 2` (filename identity). Production S1.5 gates convergence on canonical work identity (`is_convergent` / `resolve_source_ids()` → author|title). The reported metric can be inflated by duplicate editions and is not the quantity D2336's 20% threshold was meant to calibrate.
- **Root cause:** `pipeline/e2e_test.py:167` computes convergence from `source_books` filenames, not from `is_convergent` / canonical source IDs.
- **Fix (D2347):** Compute `sum(c["is_convergent"])` as the primary metric; report filename-diversity separately as a diagnostic.
- **Status:** 🟢 FIXED (2026-08-13) — `e2e_test.py` Check 1 now gates on `is_convergent` (canonical IDs) and reports filename-diversity as a diagnostic; added a non-gating `vector_completeness` diagnostic check.
- **Files:** `pipeline/e2e_test.py`
- **Source:** ChatGPT audit (`chatgpt009.md`) Block #2 / Seat 2; independently re-verified this session.

---

## 🟠 BUG-101 — 2026-08-13 — T1.1 handoff instructs runner flags that don't exist + stale S5 calibration
- **Symptom:** `governance/aggregated_remaining_tasks.md` T1.1 handoff said `python3 pipeline/runner.py --hybrid --only-convergent`. `runner.py` argparse rejects both `--hybrid` and `--only-convergent` (they are `stage2_extract.py` flags, never forwarded by the runner — `STAGES["2"]` has no `args`). Running the handoff verbatim fails with `unrecognized arguments`. Also carried the pre-D2321 broken calibration `S5 threshold 0.10 (P=1.000, R=0.556)` and implied hybrid-gate use.
- **Root cause:** Handoff written before D2327/D2328/D2339 landed; never re-synced when the runner gained resume-validity manifest (D2329) and the calibration was corrected (D2322). The runner never forwards S2 sub-flags by design.
- **Fix (D2343):** Corrected handoff to `python3 pipeline/runner.py` (traditional-only — hybrid REJECTED per BUG-085) + stage-by-stage `stage2_extract.py` (no sub-flags); corrected S5 numbers to D2322's P=0.647/R=0.386/F1=0.484; annotated hybrid DISABLED.
- **Status:** 🟢 FIXED (2026-08-13) — handoff now matches the runner's actual interface.
- **Files:** `governance/aggregated_remaining_tasks.md`
- **Source:** tooling-alignment audit (`just` recipes + handoff) this session

---

## 🟡 BUG-100 — 2026-08-13 — integrity check [8] false-green (placeholder count never compared)
- **Symptom:** `just integrity` reported 17/17 PASS even when the S6 INSERT placeholder count diverged from the SQLite column count. Check [8] could not catch the D2337 48→54 column change.
- **Root cause (2 stacked):** (1) `re.findall(r"INSERT\s+(OR\s+REPLACE\s+)?INTO\s+fbs[^;]*", ...)` — the capturing group made `findall` return the *group* string ("" / "OR REPLACE "), so `placeholder_count = ins.count("?")` was ALWAYS 0 → the `if placeholder_count > 0` branch never fired → silent `return True`. (2) the `[^;]*` tail matched `fbs_fts` (word-prefix) and spanned past the SQL `"""` into Python code, over-counting `?`.
- **Fix (D2342):** VALUES-anchored `re.search(r"INSERT...INTO\s+fbs\b.*?VALUES\s*\(([^)]*)\)", ...)`; also enhanced check [7] key_fields to include the six D2337 fields.
- **Status:** 🟢 FIXED (2026-08-13) — check [8] now genuinely compares 54=54 and FAILED at 56≠54 in the intermediate state (proving the fix).
- **Files:** `pipeline/integrity_check.py`
- **Source:** In-depth `just integrity` alignment audit (this session)

## 🔴 BUG-095 — 2026-08-13 — Stage 6 SQLite drops D2323 axes + mechanism/boundary/consequence (data loss)
- **Symptom:** S2 produces and S4 carries `mechanism`/`boundary`/`consequence` (`stage4_merge.py:1348-1350`), but SQLite `fbs` table has no such columns — only the older `application`/`failure_mode`/`elaboration`. `content_type`/`extraction_type` (D2323) never reach ANY store; `taxonomy_match_method` is computed then discarded in S4.
- **Root cause:** `stage6_commit.py` CREATE TABLE (`:67-127`) + INSERT (`:275-345`) predate the D2323 ontology; S4 never copies `content_type`/`extraction_type`/`taxonomy_match_method` into the output FB dict (only uses `content_type` internally for routing).
- **Fix (D2337):** Add `content_type`, `extraction_type`, `mechanism`, `boundary`, `consequence` columns + INSERT + `_migrate_add_column` + round-trip test. Couples to B5 (S4 must emit the axes).
- **Status:** 🟢 FIXED (code, 2026-08-13) — S4 emits the axes, S6 persists 6 new columns, round-trip test passes. Full-corpus canary pending.
- **Files:** `pipeline/stage6_commit.py`, `pipeline/stage4_merge.py`, `pipeline/schemas.py`
- **Source:** ChatGPT audit (`chatgpt008.md`) Block #1; independently re-verified against code

## 🔴 BUG-096 — 2026-08-13 — S4/S6 fail-open: partial failure still exits 0 (no fail-closed gate)
- **Symptom:** S4 increments `failed`/`classification_errors` and prints them but never exits nonzero. S6 `insert_fb()` returns `False` on exception (`:377-379`), `run_stage6()` prints `❌ Failed to commit` (`:560-561`) but exits 0 → `runner.py` writes a `COMPLETE` manifest with failed inserts.
- **Root cause:** D2331 added fail-closed to S2 only; S4/S6 never received the equivalent `failed > permitted → exit 1` gate.
- **Fix (D2338):** `failed == 0` (or config tolerance) as exit condition in both stages; distinguish LLM-failure vs classification-failure vs intentional-skip; injected-failure test asserting nonzero exit + no COMPLETE manifest.
- **Status:** 🟢 FIXED (code, 2026-08-13) — S4/S6 `max_failed_ratio` fail-closed gates added; injected-failure (exit 1) + happy-path (exit 0) tests pass. Canary pending.
- **Files:** `pipeline/stage4_merge.py`, `pipeline/stage6_commit.py`
- **Source:** ChatGPT audit Block #2/#3; independently re-verified

## 🟠 BUG-097 — 2026-08-13 — runner `--run-id` import-ordering breaks run isolation
- **Symptom:** `runner.py --run-id corpus-X` does NOT isolate checkpoints/manifests; run-scoped paths are materialized with the default `latest` run_id before argparse runs.
- **Root cause:** `STAGE_CHECKPOINTS` (`:84,132,139`) and `_RESUME_MARKER` (`:152`) call `get_run_id()` at MODULE level; `--run-id` sets `MAXWELL_RUN_ID` only in `main()` (`:661-669`) after `pipeline_paths` cached the default.
- **Fix (D2339):** Parse args before run-scoped imports, or lazy `RunContext` in `pipeline_paths`; two-run isolation test.
- **Status:** 🟢 FIXED (2026-08-13) — `_pre_parse_run_id()` pre-parses `--run-id` before `pipeline_paths` import; verified both `--run-id X` and `--run-id=X` forms.
- **Files:** `pipeline/runner.py`, `pipeline/pipeline_paths.py`
- **Source:** ChatGPT audit Block #8; independently re-verified

## 🟡 BUG-098 — 2026-08-13 — `psutil` undeclared in `requirements.txt` (C11/C24)
- **Symptom:** `psutil` imported by 4 files (`run_monitor.py`, `memory_guard.py`, `run_diagnostic.py`, `n2_watchdog.py`) but absent from `requirements.txt`. Integrity checker's manual `KNOWN_PACKAGES` list masks it.
- **Root cause:** Dependency declared by convention, never added to the manifest.
- **Fix:** Add `psutil>=6.0` to `requirements.txt`; make the dependency audit parse the actual requirements file, not a whitelist.
- **Status:** 🟡 PARTIAL — `psutil>=6.0` added to `requirements.txt` (2026-08-13); `integrity_check.py` whitelist→requirements parsing refactor deferred.
- **Files:** `requirements.txt`, `pipeline/integrity_check.py`
- **Source:** ChatGPT audit §10; independently re-verified

## 🟠 BUG-099 — 2026-08-13 — Model registry drift: gpt-oss/Phi misnamed as "verifier" vs DeBERTa-only S5
- **Symptom:** `stage5_verify.py` = DeBERTa-only (D2298), but role keys are misleading: `pipeline_config.yaml models.verifier` = gpt-oss (actually the **S4 classifier**, D2249), `models.verifier_v2` = Phi-4-mini (actually the **S2 fast probe**, D2319 — still actively used in `stage2_extract.py:815-825`), `model_assignments.yaml S5_VERIFIER`/`S5_FB_VERIFIER` = Phi (stale; S5 = DeBERTa-only). The true S5 verifier is `models.nli_large` = DeBERTa.
- **Root cause:** D2298 removed Phi from S5 *verification* only, but the role keys were never renamed to reflect the surviving roles (classifier/probe).
- **Fix (D2340):** rename `verifier`→`classifier` (gpt-oss) + `verifier_v2`→`probe` (Phi); annotate `model_assignments.yaml` S5_* roles as removed. Naming/documentation drift — NOT broken functionality (`VERIFY_MODEL`/`VERIFY_MODEL_V2` both resolve + are consumed correctly).
- **Status:** 🟡 PARTIAL — `session_seed.yaml` renamed; `pipeline_config.yaml`/`pipeline_paths.py`/`model_assignments.yaml` rename deferred (P1, low risk)
- **Files:** `config/pipeline_config.yaml`, `config/model_assignments.yaml`, `agent/session_seed.yaml`, `pipeline/pipeline_paths.py`
- **Source:** ChatGPT audit (model attribution); independently re-verified + corrected (Phi still used as S2 probe, NOT dead)

## 🔴 BUG-094 — 2026-08-13 — S2 checkpoint pretty-printed (JSONL broken) + resume-existence coupling

- **Symptom:** S2 checkpoints on disk are pretty-printed JSON (multi-line per record), but S4/bridge loaders parse with `json.loads(line)`. Code-verified: `latest/checkpoint.jsonl` = 575 lines / 290 non-empty / **30 parseable**; `e2e/checkpoint.jsonl` = 118 / 107 / **91**. Downstream merge silently parses only self-contained lines → corrupt/empty S4 output.
- **Root cause (2 stacked layers):**
  1. Format drift — current writer (`stage2_extract.py:1461,1544,1709,1734`) emits compact single-line `json.dumps(fb)`; the on-disk pretty-printed files are a legacy/unresolved-provenance artifact (handoff "still-open #1"). Code and disk disagree.
  2. Resume keys on existence (`runner.py:185-193` `find_resume_point`) — a corrupt-but-present checkpoint is treated as a completed stage, so resume skips S2 and feeds garbage to S4.
- **Fix (D2332):** (a) fail-closed JSONL boundary assertion at every S2-checkpoint reader; (b) regenerate corrupt `latest`/`e2e` checkpoints; (c) D2329 resume-validity manifest (existence never implies validity).
- **Status:** 🟢 FIXED (D2332/D2343, 2026-08-13) — `load_jsonl` fail-closed read wired into `stage2_extract.py` resume reader (D2343) + bridge/S4 (9295ce0). Corrupt `latest/checkpoint.jsonl` already quarantined as `checkpoint.jsonl.orig_48mb`; no active `checkpoint.jsonl` remains → S2 starts fresh, never subset-parses. Resume-validity manifest (D2329) guards existence≠validity.
- **Files:** `pipeline/stage2_extract.py`, `pipeline/bridge_s2_to_s4.py`, `pipeline/stage4_merge.py`, `pipeline/runner.py`

---

### BUG-087 — 2026-08-12 — Duplicate-edition false convergence (source identity broken, 3 layers) 🔴
- **Symptom:** `Safe Withdrawal Rate`, `Transgenic Artistic Agency`, `Black Swan` all `source_diversity:2, is_convergent:true` from two filenames of the SAME work (z-library vs liber3/1lib.sk). The central `is_convergent` claim is false for these FBs.
- **Root cause (3 stacked layers):**
  1. `book_metadata.compute_source_id` = SHA-256(author|title), but stage0_5 metadata is inconsistent (subtitle presence, co-author lists, title+subtitle concatenation) → same work resolves to 2 canonical IDs.
  2. `schema_accessor.isor_score` counts RAW FILENAMES (`len(set(source_books))`), not canonical IDs → duplicate editions inflate source count.
  3. `schema_accessor._extract_author_surname` splits on `" — "` (em-dash) but corpus uses `"Title (Author) (source).md"` (parenthesis) → returns full filename → `n_authors == n_sources`.
- **Fix:** D2308 (metadata normalization + canonical work count) + D2309 (ISOR metadata-author + canonical source count).
- **Status:** ✅ FIXED (D2308+D2309, 2026-08-12) — duplicate editions collapse to one canonical work
- **Files:** `pipeline/book_metadata.py`, `pipeline/schema_accessor.py`, `pipeline/stage1_5_embed_cluster.py`
- **Source:** Roundtable adjudication 2026-08-12 — ChatGPT C1/E1, verified against probe data

### BUG-088 — 2026-08-12 — ISOR author extraction heuristic + rating precedence bug 🟠
- **Symptom:** 0/40 probe FBs rated "weak"; `n_authors == n_sources` always; `author_score` pinned at 1.0. `Data-driven Pipeline Processing` reports `n_authors=23` from 23 filenames.
- **Root cause:** `_extract_author_surname` expects `"Title — Author"` (0/268 source_books use this; 268 use parenthesis) → returns full filename as "surname". Rating condition `n_authors>=2 or n_domains>=2 and n_sources>=2` binds `and` tighter than `or` → `n_authors>=2 or (n_domains>=2 and n_sources>=2)`.
- **Fix:** D2309.
- **Status:** ✅ FIXED (D2309, 2026-08-12) — metadata author + canonical source count; "weak" reachable (5 FBs)
- **Files:** `pipeline/schema_accessor.py`
- **Source:** Roundtable adjudication 2026-08-12 — Qwen C2 / Kimi C2, root-caused

### GOLDEN-AUDIT — 2026-08-12 — Golden set validity verified after pipeline changes 🟢 (3 minor findings)
- **Verification:** `pipeline/golden_validate.py` PASSES (75 examples, all 5 checks: no dup keys, verbatim evidence, route/should_extract consistency, author diversity, meta count). All `is_convergent=True` positives have genuinely distinct sources (no post-D2308 duplicate-edition false positives). `dspy_trainer.golden_to_examples()` parses all 75 entries → 77 FB objects. Golden set is **STILL VALID and USABLE** after D2298/D2308/D2309/D2310/D2241.
- **Finding 1 — 3 examples missing `discipline`:** NEG-CONV-001/002/003 have no `discipline` field (predate the field's addition). Low risk — all are CHALLENGE negatives where discipline is irrelevant. Should backfill for schema uniformity before D2292 depth expansion.
- **Finding 2 — NEG-DUP-001/002 use `discipline: emerging`:** Both new hard negatives label discipline as `emerging` (catch-all) despite having concrete domains (finance, art). Harmless for route=NULL negatives, but lazy labeling — backfill real disciplines (finance→finance/behavioral-finance, art→art/design).
- **Finding 3 — dead `depth` field in 54 positive FBs:** D2241 moved depth classification to S4, but `expected_fb.depth` remains populated in 54 positives (0 consumers — `golden_to_examples()` ignores it). Dead data per C19; strip during D2292 golden depth expansion (BUG-084), which will reintroduce depth as a dedicated S4 benchmark.
- **Note (GAP-1, post-T1.1):** `golden_to_examples()` maps `is_convergent = should_extract AND is_convergent`, collapsing the golden set's 4 quadrants (convergent-pos / false-convergence / single-source-pos / plain-neg) onto a single bool. The `route` field preserves the distinction, so DSPy can still learn correctly, but the `is_convergent` OutputField alone is ambiguous for GOLD-B single-source positives (CONV-035/037/039 → `is_convergent=False` + `route=FB`). Reconcile semantics when wiring DSPy (GAP-1).
- **Drift fixed (this session):** `dspy_trainer.py` docstrings corrected 73→75 examples / 77 FBs, CHALLENGE 21→23, "72 examples"/"70 examples"→75.
- **Files:** `config/golden/stage2_fewshot_convergent.yaml`, `pipeline/dspy_trainer.py`

### BUG-089 — 2026-08-12 — `just eval` S2 hardcoded 600s timeout kills extraction 🔴
- **Symptom:** `just eval` (e2e_test.py) ran S0→S1.5 clean (191 clusters, 5 convergent) then `stage2_extract.py` raised `subprocess.TimeoutExpired` after exactly 600s with only 3 FBs written. Full eval could never complete.
- **Root cause:** `pipeline/e2e_test.py::run_stage()` hardcoded `timeout=600` (10min) for every stage — a C12 violation. The 30B generator (Qwen3-Coder-30B) needs far longer for S2 on 20 books (599 cluster+singleton targets). Config already had `stages.timeouts['2']=null` (D2269) for `runner.py`, but e2e_test.py ignored it.
- **Fix (D2311):** Added `_get_stage_timeout()` + `_STAGE_ID_BY_SCRIPT` to e2e_test.py, reading per-stage timeout from `config/pipeline_config.yaml` (`stages.timeouts`), mirroring `runner.py::_get_stage_timeout`. S2 now `null` (unlimited) instead of 600s.
- **Status:** ✅ FIXED (D2311, 2026-08-12) — `_get_stage_timeout('stage2_extract.py')` → None; other stages → 3600s.
- **Files:** `pipeline/e2e_test.py`
- **Source:** `just eval` run 2026-08-12 (this session)

### BUG-090 — 2026-08-12 — e2e `validate_results()` reads stale "latest" checkpoint, not the e2e run 🔴
- **Symptom:** `just eval` ran all 9 stages clean (703s, 9/9 passed) then crashed in `validate_results()` with `JSONDecodeError: line 1 column 78` loading `STAGE2_CHECKPOINT`. Validation never ran.
- **Root cause (2 layers):**
  1. `pipeline_paths` caches `run_id` at import time from `MAXWELL_RUN_ID` (default `latest`). `e2e_test.py` imports it at module top *before* `run_stage()` sets `MAXWELL_RUN_ID=e2e` for the subprocesses — so the module-level `STAGE2_CHECKPOINT` resolves to `latest/checkpoint.jsonl`.
  2. `latest/checkpoint.jsonl` is a STALE file (Aug 12 18:01 diagnostic run) containing pretty-printed JSON (not JSONL) → `_load_jsonl` raises `JSONDecodeError`.
- **Fix (D2312):** Set `os.environ.setdefault("MAXWELL_RUN_ID", "e2e")` at the top of `e2e_test.py`, BEFORE importing `pipeline_paths`. Checkpoints now resolve to `{stage}/e2e/checkpoint.jsonl` (the run that was just executed).
- **Status:** ✅ FIXED (D2312, 2026-08-12) — `STAGE2_CHECKPOINT` → `stage2_extract/e2e/checkpoint.jsonl`.
- **Files:** `pipeline/e2e_test.py`
- **Source:** `just eval` run 2026-08-12 (this session)

### BUG-091 — 2026-08-12 — e2e validation report: `db_commit` KeyError + `disciplines` field drift 🟡
- **Symptom 1:** `validate_results()` crashed with `KeyError: 'threshold'` after printing `verify_pass_rate` — the `db_commit` check dict (Check 5) lacked a `threshold` key, and the print loop did `check['threshold']`.
- **Symptom 2:** `multi_label: 0/3` always — the check read `fb.get("disciplines")` (plural list) but S4 writes `domains` (plural list) + `discipline` (singular string). Field-name drift made the check measure a nonexistent key.
- **Fix (D2313/D2314):** Added `threshold: "written"` to the `db_commit` check; made the print loop defensive via `check.get('threshold', '—')`; changed `multi_label` to read `domains` (the actual multi-label field).
- **Status:** ✅ FIXED (2026-08-12)
- **Files:** `pipeline/e2e_test.py`
- **Source:** `just eval` run 2026-08-12 (this session)

### D2315 — 2026-08-12 — Black Swan title-concat case: 3rd duplicate-edition now collapses ✅
- **Residual from G1 (BUG-087):** `The Black Swan (Taleb)` and `The Black SwanThe Impact of the Highly Improbable (Taleb)` are the same work but the camelCase-concatenated subtitle made `normalize_title` yield two different canonical titles → false divergence (source_diversity 2).
- **Root cause:** `_SUBTITLE_SPLIT` only handles explicit separators (`:—–-`); the concat case ("SwanThe") was camelCase-split but the subtitle phrase was retained.
- **Fix:** `_CONCAT_SUBTITLE_SPLIT` regex splits at the camelCase boundary preceding a subtitle-opener (`The|A|An|How|Why|What`) and drops the remainder. "The Black SwanThe Impact…" → "the black swan". Verified all 3 dup-edition cases now collapse (`resolve_source_id` equal); regression-safe on Make Bootstrapper + Speculative Everything.
- **Status:** ✅ FIXED (2026-08-12)
- **Files:** `pipeline/book_metadata.py`

### D2316 — 2026-08-12 — Domain-coherent e2e book sampling ✅
- **Symptom:** `just eval` selected the first 20 books alphabetically (a domain-diverse grab-bag) → 3% convergent clusters, 3 FBs — useless for convergence validation.
- **Fix:** `stage0_convert.find_books()` accepts a `subdir` filter via `MAXWELL_BOOK_SUBDIR`; `e2e_test.py` gained `--subdir` (default `DOMAIN 6 AI + Computing/ai+engineering+agents`, 55 coherent AI-agents books).
- **Status:** ✅ FIXED (2026-08-12)
- **Files:** `pipeline/stage0_convert.py`, `pipeline/e2e_test.py`

### G10 — 2026-08-12 — OMLX wired-memory leak stress test ✅ PASS
- **Result:** 5 rounds × 20 reqs (Qwen3-Coder-30B), wired flat 34.07→34.07 GB, cumulative growth 0.0%, 0 errors. No GitHub #2184 leak. `just wired-stress`.
- **Status:** ✅ PASS (2026-08-12)
- **Files:** `pipeline/omlx_wired_stress.py`

### D2317 — 2026-08-12 — stage2 stale-FB contamination on segids mismatch 🟡
- **Symptom:** When a new e2e run uses a different book sample, `stage2_extract.py`'s resume logic detects a segids mismatch (old cluster IDs have 0 overlap with new probe targets) and clears `processed_ids` — but `all_fbs` (already loaded from the old checkpoint) was NOT cleared. Stale FBs from the prior run would be appended to the new run's checkpoint.
- **Fix:** Added `all_fbs = []` alongside `processed_ids = set()` in the mismatch branch.
- **Status:** ✅ FIXED (2026-08-12). Note: the running coherent eval was launched before this fix, so its checkpoint may retain 3 stale diverse-run FBs (~10% of expected output) — minor, flag-only.
- **Files:** `pipeline/stage2_extract.py`

### D2319 — 2026-08-13 — S2 discovery probe used GPT-OSS (reasoning model) → PROBE ABORT (2×) 🔴
- **Symptom:** Domain-coherent `just eval` (39 convergent clusters) failed at `stage2_extract.py` rc=1 with `PROBE ABORT` — `discover_principles()` returned None for >10% of clusters (cluster_109, cluster_212, …). Diverse run (5 clusters) never crossed the threshold, masking the bug.
- **Root cause:** `discover_principles()` called `call_llm(model=VERIFY_MODEL=gpt-oss-20b)`. VERIFY_MODEL was repointed to GPT-OSS (D2249/D2250, S4 classifier) but the probe was *designed* for Phi-4-mini (fast, ~1.5s, non-reasoning). GPT-OSS is a reasoning model: during cold reload it emits only `reasoning_content` (no JSON `content`) → `call_omlx` raises "content missing" → `call_llm` returns None. A "Reasoning: none" prefix (D2318 attempt) reduced but did NOT eliminate failures — the cold-reload reasoning_content emission persists.
- **Fix:** Repoint the probe to `VERIFY_MODEL_V2` (Phi-4-mini-instruct-8bit) — the original fast probe model. Phi-4-mini is non-reasoning, JSON-mode-safe (`response_format: json_object`), and returns `{"principle_count": N}` with `finish: stop` (no `reasoning_content`). Verified via direct call.
- **Status:** ✅ FIXED (2026-08-13)
- **Files:** `pipeline/stage2_extract.py`
- **Supersedes:** D2318 (Reasoning:none prefix — necessary for stage4, insufficient for the probe)

### D2320 — 2026-08-13 — Stage4 D2072 dedup KeyError on v3.0 `fb_id` records 🔴
- **Symptom:** `stage4_merge.py` crashed `KeyError: 'principle_id'` at line 1408 after writing the 88-FB checkpoint. Triggered by the domain-coherent run producing `content_type: process_template` (3) + `tool_instruction` (1) FBs — the diverse run had none, masking the bug.
- **Root cause:** The D2072/D2073 separate-output dedup blocks (`growth_edges`, `process_templates`, `process_instances`, `tool_instructions`) read `rec["principle_id"]`, but v3.0 stage2 records use `fb_id` (no `principle_id` field).
- **Fix:** All four dedup blocks now use `rec.get("fb_id") or rec.get("principle_id", "")`.
- **Status:** ✅ FIXED (2026-08-13)
- **Files:** `pipeline/stage4_merge.py`

### BUG-092 — 2026-08-13 — S5 DeBERTa NLI fed single concatenated string (no premise/hypothesis) → 36% false pass rate 🔴
- **Symptom:** Domain-coherent eval showed `verify_pass_rate: 32/88 (36%)` — 56 FBs QUARANTINE. Manual classification of all 56 revealed ~50 are factually correct ("Sigmoid maps to (0,1)", "Transformer dim scaling", "Data Leakage Prevention", "Graceful Degradation") — a ~90% false-negative rate, the opposite of a healthy fail-closed gate.
- **Root cause (2 stacked bugs in `deberta_check()`):**
  1. **BUG-A (pairing):** `_txt = f"{_def} {_ep}"[:512]` concatenated definition+evidence into ONE string and fed it to DeBERTa as a single sequence. NLI models require `(premise=evidence, hypothesis=definition)` as two sequences; a single blob produces meaningless logits biased to NEUTRAL.
  2. **BUG-B (top-1 collapse):** `debert(_txt)` used the `text-classification` pipeline default (top-1 only). When the argmax was NEUTRAL, both `ent` and `cont` defaulted to 0.0 and the detail string mislabeled it `CONTRA` (`34x "CONTRA: ent=0.00 cont=0.00"` were actually NEUTRAL verdicts).
- **Fix (D2321):** Pass proper pair `debert({"text": premise, "text_pair": hypothesis}, top_k=3)`; read all three labels and distinguish ENTAIL / NEUTRAL / CONTRA; add config-driven truncation `nli_max_premise_chars`/`nli_max_hypothesis_chars` (256) honoring C12.
- **Impact:** Re-run of S5 on the same 88 FBs: **32/88 (36%) → 74/88 (84%)**. Remaining 14 QUARANTINE = 3 genuinely vacuous MECH-FAIL + 11 NEUTRAL cross-source syntheses (legitimate fail-closed cost; D2285 claim-decomposition is the future recovery path).
- **Note:** D2293 "calibration" (P=1.000/R=0.556/F1=0.714 on 12 FBs) was measured on this SAME broken call → calibration numbers are suspect and should be re-derived post-fix.
- **Status:** ✅ FIXED (2026-08-13)
- **Files:** `pipeline/stage5_verify.py`, `pipeline/pipeline_paths.py`, `config/pipeline_config.yaml`

### D2321 — 2026-08-13 — S5 NLI premise/hypothesis pairing + all-3-label scoring ✅
- **Fix for BUG-092:** `deberta_check()` now passes `(premise=evidence, hypothesis=definition)` as a proper two-sequence pair via `{"text": ..., "text_pair": ...}`, reads all three NLI labels (`top_k=3`), and distinguishes ENTAIL/NEUTRAL/CONTRA in both the detail string and fail-closed logic. Truncation limits moved to config (`stage5.nli_max_premise_chars`/`nli_max_hypothesis_chars`, default 256).
- **Config keys added:** `stage5.nli_max_premise_chars`, `stage5.nli_max_hypothesis_chars`; exported as `S5_NLI_MAX_PREMISE_CHARS`/`S5_NLI_MAX_HYPOTHESIS_CHARS`.
- **Status:** ✅ FIXED (2026-08-13)
- **Files:** `pipeline/stage5_verify.py`, `pipeline/pipeline_paths.py`, `config/pipeline_config.yaml`

### D2322 — 2026-08-13 — nli_calibrate.py re-derivation: 3 bugs + non-reproducible D2293 calibration 🔴
- **Task:** Re-derive the S5 NLI threshold post-BUG-092 (the D2293 "P=1.000/R=0.556/F1=0.714 at 0.10" was measured on the broken single-sequence call).
- **Found 3 bugs in `nli_calibrate.py` (same family as BUG-092):**
  1. `load_fbs_from_stage4()` read `STAGE4_OUTPUT` (`stage4_merge/e2e/fbs.jsonl`, does NOT exist) instead of `STAGE4_CHECKPOINT` (`checkpoint.jsonl`).
  2. `calibrate()` used `deberta_check()` which returned `0.0` entailment on every non-pass verdict → the threshold sweep collapsed to a binary pass/fail.
  3. Sweep range `np.arange(0.50, 0.96, 0.05)` was a stale ModernBERT-era guess that never covered the D2298 operating threshold 0.10 (DeBERTa entailment scores on paraphrase evidence cluster LOW).
- **Fix:** Repointed to `STAGE4_CHECKPOINT`; extracted `_nli_pair_scores()` (D2322) in `stage5_verify.py` returning continuous `(entail, neutral, contra)` and used it directly in `calibrate()`; extended sweep to `0.05–0.95`. `deberta_check()` now returns the continuous entailment score on non-pass (was `0.0`).
- **Honest auto-calibration result (466 pairs, 88 FBs):** at 0.10 → **P=0.647 / R=0.386 / F1=0.484**; best F1 at 0.05 (P=0.619/R=0.468/F1=0.533); best precision at 0.50 (P=0.667/R=0.180). **D2293's P=1.000 is NOT reproducible.**
- **Interpretation (IMPORTANT):** the auto-pair methodology (definition ↔ single evidence passage) measures *strict single-passage entailment*, NOT the S5 gate's real question (*is the cross-source synthesis supported by its corpus evidence?*). It is therefore a PESSIMISTIC lower bound — cross-source syntheses don't strictly entail from any single passage (D2227 paraphrase evidence). The most reliable current signal is the empirical S5 run (84% pass, ~90% manual correctness, 14 quarantine = 3 vacuous + 11 NEUTRAL).
- **Decision:** KEEP threshold 0.10 (fail-closed, empirically sound). A proper human-labeled FB-level re-calibration (D2293 methodology) is deferred — fold into D2292 golden-depth expansion or a dedicated adjudication pass post-T1.1.
- **Status:** ✅ FIXED (2026-08-13). Threshold unchanged (0.10). Docs/code now carry the honest auto-calibration numbers instead of the unreproducible D2293 P=1.0.
- **Files:** `pipeline/nli_calibrate.py`, `pipeline/stage5_verify.py`

### STALE BUGS CLOSED — 2026-08-12 (validated already-fixed; were marked OPEN in error)
- **BUG-080.4** (runner 60-min timeout) → **already fixed by D2269** (config `stages.timeouts` `'2': null`).
- **BUG-080.5** (S5 completeness substitutes application for mechanism) → **already fixed by D2298** (`check_completeness` deleted).
- **BUG-080.6** (NLI threshold validation warns only) → **already fixed by D2272** (`_validate_nli_thresholds()` raises ValueError).
- **BUG-080.7** (Ollama path missing dim assertion) → **already fixed by D2274** (ValueError on mismatch, line 296-299).
- **BUG-080.8** (dropped embeddings not gated) → **already fixed by D2275** (RuntimeError >0.5% drop rate).

### BUG-086 — 2026-08-12 — S4 batch CRIBS results silently ignored (orphaned config) 🟠
- **Symptom:** S4 CRIBS enrichment ran ~61s/FB despite `batch_enabled: true`. Batch pre-classification
  collected `_pre_classified` results but the main loop never consumed them.
- **Root cause:** `merged_call_enabled` config flag was orphaned — `_use_merged` was set from
  `os.environ.get("MAXWELL_MERGED_S4")` only, so config `true` was ignored. The
  `elif cluster_id in _pre_classified` branch was gated behind `_use_merged`, which was
  always False → batch results discarded → slow two-call path ran for every FB.
- **Fix (D2303):** Read `merged_call_enabled` from config (`_PIPELINE_CFG.get("stage4", {}).get("merged_call_enabled")`)
  in `_use_merged`; added a standalone `elif cluster_id in _pre_classified` branch so batch
  results are consumed regardless of `_use_merged`. Expected ~3× speedup (~19.4s/FB vs ~61s/FB).
- **Status:** ✅ FIXED (2026-08-12, D2303)
- **Files:** `pipeline/stage4_merge.py`
- **Source:** Senior RAG audit — CRIBS bottleneck investigation

### D2211: P0 Circuit Breaker & Error Propagation Fixes (2026-08-08)

**13 surgical fixes applied** across 3 files (~106 lines). Source: Goose Ultimate Final Verdict arbitration of spec vs Kimi peer review, all verified against live repository HEAD.

**Root Cause of Run 5 (12-hour waste):**
1. Shallow health check (`/v1/models`) missed OMLX prefill guard → all prompts rejected with HTTP 400
2. 4xx counted as breaker failures → breaker tripped prematurely
3. `call_llm` caught `CircuitOpenError` → returned `None` (silent)
4. `discover_principles`: `None` is not dict → returned 1 (no split detected)
5. `future.result()` caught generic `Exception` → continued loop (never aborted)
6. Result: 611 clusters probed → 0 splits → 2,577 clusters extracted → breaker blocks all → 9 FBs in 12 hours

**Fixes Applied:**

| # | Fix | File | Lines |
|---|------|------|-------|
| P0-1 | CB log: `OMLX_CB_FAILURE_THRESHOLD` → `_breaker._threshold` (showed 5, actual 25) | `omlx_call.py` | 1 |
| P0-2 | Import `CircuitOpenError` in stage2_extract.py (3 sites) | `stage2_extract.py` | 3 |
| P0-3 | `stress_test_omlx`: `all_ok=False` on non-200 HTTP | `omlx_call.py` | 1 |
| P0-4 | `discover_principles`: detect `call_llm` returning `None`, `error_counter` param | `stage2_extract.py` | ~12 |
| P0-5 | Probe fail-closed: mutable counter + 10% abort threshold | `stage2_extract.py` | ~10 |
| P0-6 | `call_llm`: `except CircuitOpenError: raise` before generic catch | `stage2_extract.py` | 3 |
| P0-7 | `_process_cluster`: same `CircuitOpenError` re-raise | `stage2_extract.py` | 2 |
| P0-8 | `future.result()` boundary: catch `CircuitOpenError`, cancel futures, preserve checkpoint, abort | `stage2_extract.py` | ~12 |
| P0-9 | `process_singletons` future boundary: same pattern | `stage2_extract.py` | ~11 |
| P0-10 | Health check: `check_omlx_health()` → `stress_test_omlx()` (real chat requests) | `stage2_extract.py` | ~10 |
| P0-11 | Probe cache + singleton output scoped by `_rid()` | `pipeline_paths.py` | 2 |
| P0-12 | `CircuitBreaker` thread safety: `threading.Lock` on state mutations | `omlx_call.py` | ~8 |
| P0-13 | 4xx HTTP errors excluded from breaker failure count | `omlx_call.py` | 3 |

**Verification:** Syntax check passed (3/3 files). Live stress_test against running OMLX. CircuitBreaker lock + state transitions unit-verified. Full failure chain traced: health→ST→call_llm→discover→process→future boundary.

**Deferred:** Result[T] type system → v3.1 (Kimi's architectural critique correct but ~200+ lines for P0 emergency).

**Status:** ✅ ALL FIXED (2026-08-08)

---

### D2195-D2201: Cross-Examination Ultimate Verdict — Bugs Found & Fixed (2026-08-06)

Comprehensive cross-examination of 4 LLM audits (DeepSeek, ChatGPT, Qwen, Kimi) + direct codebase verification. Full report: `governance/cross-examination-ultimate-verdict-2026-08-06.md`.

**P0 Fixes Applied:**
- ZERO-VECTOR-001: `ollama_embed.py` — removed all zero-vector fallbacks (2 paths). Replaced with `EmbeddingQuarantineError`. D2196.
- LICENSE-MISSING: Added MIT LICENSE. D2200.
- SESSION-NLI-STALE: `session_seed.yaml` NLI model corrected from `roberta-large-mnli` → `ModernBERT-large`. D2197.
- SESSION-STAGE3-GHOST: `session_seed.yaml` stage3 removed, corrected to 8-stage. D2197.
- MODEL-VARIANT-MISMATCH: `model_assignments.yaml` — documented OptiQ/non-OptiQ split, fixed REVIEWER (broken DeepSeek → gemma), fixed S5_FB_VERIFIER (Qwen→Gemma for R5 cross-family). D2199.

**P1 Fixes Applied:**
- AGENTS-STAGE3-GHOST: `AGENTS.md` stage3_cluster.py reference commented out with removal note. D2198.
- RUFF-EXCLUDES-PIPELINE: `pyproject.toml` — removed `knowledge pipeline/` from both Ruff and mypy exclusions. D2201.
- STAGE4-FUNCTION-MISNAMED: `stage4_merge.py` `load_stage3_clusters()` → `load_stage2_clusters()`. D2198.
- KNOWLEDGE-ARCHITECTURE-STALE: `KNOWLEDGE-PIPELINE-ARCHITECTURE.md` — updated to 8-stage pipeline, removed all stage3 references. D2198.
- WATCHDOG-LOG-COMMITTED: Removed `omlx_watchdog.log` and `.omlx_watchdog_state.json` from repo.

**P2 Fixes Applied (2026-08-06):**
- O1: `ollama_embed.py` — removed undeclared `import ollama`. Single-doc path now delegates to batch_embed (requests-based). D2202.
- O2: `.DS_Store` files cleaned from repository.
- D2203: `pipeline/integrity_check.py` — 17 automated checks. `just integrity` + `just integrity-quick` commands. Added to health+preflight.
- D2203: Deterministic lockfile — `requirements.lock` generated via `uv pip compile`.
- D2203: `just preflight` exit bug fixed — `exit(0 if ok else 0)` → `exit(0 if ok else 1)`.
- D2203: `stage6_commit.py` — INSERT column/placeholder mismatch fixed (49→48, added s3_original_domain, removed is_summary + classification_status).
- D2203: `.ponytail.yaml` — YAML escape character fixed (`\|` → `\\|`).

**Deferred to Future Phases:**
- Atomic evidence schema (per-passage NLI scores)
- Monotonic trust state machine
- bge-m3 to MLX-native (investigate MPS deadlock first)
- Context-conditioned reliability in Zone 3
- Graph-aware retrieval
- Agent execution safety boundary (MCP server + Pydantic AI harness)
- Modularize stage2/stage4 god modules
- Run auto-fix on 476 Ruff lint errors (322 auto-fixable)

---

### BUG-055: `related_fbs` vs `related_blocks` Field Name Mismatch Across Pipeline
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (silent data loss — relationships computed but never surfaced) |
| **Discovered** | 2026-07-28 — vibecheck after D2121-D2126 implementation |
| **Symptom** | `compute_fb_relationships()` in `stage4_merge.py` writes to dict key `related_fbs`, but `tests/full_run.py` initialized `related_blocks: None` and `stage6b_anytype_push.py` read from `related_blocks`. After calling compute, the `related_blocks` key remained `None` and `related_fbs` was populated but never displayed/serialized. |
| **Root Cause** | v1 schema used `related_blocks`. D2118/P1.4 introduced `related_fbs`. Schema migration was incomplete — test file and push script retained old field name. |
| **Impact** | Full run test: `related_blocks` always `None`, Obsidian markdown never rendered related blocks. Anytype push: `related_fbs` field missing from payload. |
| **Fix** | Standardized on `related_fbs` across all files: `tests/full_run.py` (field init + summary messages), `pipeline/stage6b_anytype_push.py` (ALL_FIELDS list, markdown render, payload function). `schema_accessor.py` already used `related_fbs`. |
| **Files** | tests/full_run.py, pipeline/stage6b_anytype_push.py |
| **Status** | ✅ FIXED (2026-07-28) |

---

### DELEGATE-001: Delegate System Broken — reasoning_content Passthrough Bug
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (blocks all delegation) |
| **Discovered** | 2026-07-26 — all 3 parallel research delegates failed identically |
| **Symptom** | `"reasoning_content in the thinking mode must be passed back to the API"` |
| **Root Cause** | DeepSeek thinking mode (`GOOSE_THINKING_EFFORT: high`) returns `reasoning_content` blocks. API requires these blocks passed back verbatim on turn N+1. Goose delegate system creates fresh context — doesn't preserve reasoning_content history. |
| **Impact** | ALL delegation is dead. Parallelism impossible. Research delegates fail 100%. |
| **Fix (Workaround)** | Use local OMLX models for all delegates: Phi-4-mini-8bit (research) or Qwen3-Coder-30B (code gen). $0 cost, sovereign, no thinking-mode issues. |
| **Long-term Fix** | Goose framework needs reasoning_content passthrough in delegate system. |
| **Files** | `temp/DELEGATE-FIX-ROOT-CAUSE-2026-07-26.md` |
| **Status** | 🟢 IMPROVED (2026-07-26) — gemma-4-E4B-it-MLX-4bit confirmed working via OMLX (0.48s response, accurate code review). Qwen3-Coder also confirmed working via curl. Workaround: use provider=maxwell_omlx with model=gemma-4-E4B-it-MLX-4bit for code review/summarization, model=Qwen3-Coder-30B-A3B-Instruct-MLX-4bit for code gen. Subprocess parallelism (pipeline/parallel.py) provides practical alternative for pipeline-level parallelism. Long-term fix still requires Goose framework reasoning_content passthrough. |

---

### BUG-053: Phi-4-mini-instruct-8bit HALLUCINATES on Factual/Research Tasks 🟡 MITIGATED
| Field | Value |
|-------|-------|
| **Discovered** | 2026-07-26 15:20 — delegate research on GitHub topics returned entirely fabricated repos |
| **Symptom** | Delegate output: fake repo names (Faiss-CMake, HnswLib from "thesynk"), wrong URLs (Weaviate→veidicate), fake star counts (16k for non-existent repos), Llama.cpp attributed to Microsoft |
| **Root Cause** | Phi-4-mini-8bit is a 4GB distilled model unsuitable for open-ended research. When asked to fetch real data, it generates plausible-sounding hallucinations instead. It does NOT call tools to fetch data — it fabricates from training distribution. |
| **Impact** | ALL research/read-only delegate tasks using Phi-4-mini produce garbage. Any decision based on delegate output is dangerously wrong. |
| **Mitigation** | NEVER use Phi-4-mini for research tasks requiring factual data retrieval. Use ONLY for summarization when SOURCE TEXT IS PROVIDED. For research: do it yourself with shell/curl OR use Qwen3-Coder with explicit tool-use instructions. |
| **D2268 (2026-08-11):** | Added STRICT guard in `stage5_verify.py` → `check_factual_llm()`: Phi-4-mini now auto-QUARANTINEs if source text is missing or <50 chars. This prevents hallucination in S5 deep-check verifier role. Phi-4-mini's S5 usage is safe because it always receives evidence_passages (verbatim source text). |
| **Status** | 🟡 MITIGATED (not "fixed" — model still hallucinates without source, but pipeline guard prevents unsafe invocation) |
| **Files** | `pipeline/stage5_verify.py` (check_factual_llm guard), `governance/buglog.md` |
| **Files** | AGENTS.md delegate_rules section |
| **Status** | ✅ MITIGATED (2026-07-26) — AGENTS.md delegate_rules updated: Phi-4-mini restricted to summarization-only with source text. Research tasks → direct shell/curl. Delegate alternative: gemma-4-E4B-it-MLX-4bit confirmed working (0.48s, accurate). |
| **D2264 update** | S5 VERIFIER (2026-08-11) — Phi-4-mini replaces Gemma-4-E4B as S5 deep check verifier. 67% vs 33% accuracy. Structured PASS/FLAG binary task — no open-ended research risk. |
| **D2250 update** | ✅ RESOLVED FOR S4 (2026-08-10) — Phi-4-mini RETIRED as S4 classifier (D2249/D2250: VERIFY_MODEL → gpt-oss-20b-MXFP4-Q8, 87.5% depth acc vs Phi 37.5%). Phi retained ONLY for S5 verify + fast gates (T2/T3 gate probes) where source text is provided and summarization is the task. S4 research/classification now GPT-OSS (OpenAI family, R5-compliant). |

---

### BUG-054: Qwen3-Coder-30B Delegate Fails — OMLX JSON Parse Error 🔴
| Field | Value |
|-------|-------|
| **Discovered** | 2026-07-26 15:30 — MTR merge delegate failed turn 1 |
| **Symptom** | `Request failed: Failed to parse JSON: error decoding response body for url (http://localhost:11435/v1/chat/completions)` |
| **Known Facts** | Qwen3-Coder-30B IS listed in OMLX /v1/models alongside Phi-4-mini. Phi-4-mini delegate completed (hallucinated, but connected). Qwen3-Coder generates non-JSON-compliant response that OMLX server rejects. |
| **Hypothesis** | Qwen3-Coder outputs contain control characters or malformed UTF-8 that break JSON serialization in OMLX v1/completions endpoint. Different from Phi-4-mini bug — this is transport-layer, not content-layer. |
| **Impact** | BOTH delegate models broken: Phi-4-mini (hallucination) and Qwen3-Coder (JSON parse). Delegation is dead — no working model for either research or code-gen delegates. |
| **Fix** | Test raw OMLX chat completions against Qwen3-Coder via curl. Check for non-JSON output. May need OMLX server config fix or different model. gemma-4-E4B-it untested for delegates. |
| **Status** | 🟢 CONFIRMED WORKING (2026-07-26) — Qwen3-Coder works fine via direct curl to OMLX (correct prime-check function generated). JSON parse error is in Goose delegate layer request formatting, not the model. For delegate use: Qwen3-Coder for code gen, gemma-4-E4B for code review. |

---

### BUG-051: `just smoke` Processes ALL 852 Books Instead of 1
| Field | Value |
|-------|-------|
| **Discovered** | 2026-07-26 15:25 — `just smoke` ran stage0_convert on 849 books, timed out at stage1_chunk |
| **Symptom** | `MAXWELL_RUN_ID=smoke` passed to pipeline stages but stage0_convert ignores it — processes entire books/ directory |
| **Root Cause** | stage0_convert.py doesn't read MAXWELL_RUN_ID to limit input. The env var is used for output path prefix only, not input filtering. |
| **Expected** | Smoke test should process 1 book only (fast E2E validation) |
| **Fix** | Add `--limit N` or respect `MAXWELL_RUN_ID=smoke` to auto-limit to 1-3 books. OR create `just quick-smoke` that picks first N books. |
| **Status** | ✅ FIXED (2026-07-26) — `--limit N` added. Auto-limits to 3 when `MAXWELL_RUN_ID=smoke`. |

---

## 2026-07-25 — E2E Pipeline Validation — New Bugs

### BUG-044: NLI Pre-Filter Used Strict ENTAILMENT (NEUTRAL = FAIL)
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (causes false negatives but NLI still runs) |
| **File** | `pipeline/stage5_verify.py`, `nli_evidence_check()` |
| **Symptom** | All evidence passages scored NEUTRAL against FB definitions (passages discuss related concepts but don't strictly entail synthesized claims). Original code treated NEUTRAL the same as CONTRADICTION → FAIL, meaning NLI pre-filter never passed. |
| **Root Cause** | NLI design assumed evidence passages logically ENTAIL the definition. In practice, extracted principles are syntheses that go beyond any single passage — NEUTRAL is the expected case for valid extractions. |
| **Proposed Fix** | Changed NLI strategy: CONTRADICTION≥50% → FAIL, ENTAILMENT≥50% → strong PASS (skip LLM), NEUTRAL → PASS (score=0.4, triggers LLM escalation). |
| **Status** | ✅ FIXED in D2113 E2E run. 3-way classification now handles NEUTRAL correctly. |
| **Source** | D2113, E2E test 2026-07-25 |

### BUG-045: Stage 2 Evidence Passages Inflated — All Cluster Segments Included
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (metadata bloat, not logical error) |
| **File** | `pipeline/stage2_extract.py` |
| **Symptom** | Convergent cluster_203 has 191 segments but LLM only saw 15. The output `evidence_passages` field includes ALL 191 segment texts as evidence, but only 15 were actually shown to the LLM. Inflates source_segments metadata and misleads verification. |
| **Root Cause** | The extraction records all `segment_ids` from the cluster in `source_segments`, but the evidence selection (which 15 of 191 were shown) is not tracked. |
| **Proposed Fix** | Track which segments were actually sampled for the LLM call. Store only those in `evidence_passages`. Add `cluster_total_segments` for context. |
| **Status** | 🟡 OPEN — Deferred. Low priority (metadata issue, not extraction quality issue). |
| **Source** | D2113, E2E test 2026-07-25 |

### BUG-046: check_factual_llm Required source_principles (Old Schema) — FIXED
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (blocks LLM verification for v3.0 FBs) |
| **File** | `pipeline/stage5_verify.py`, `check_factual_llm()` |
| **Symptom** | LLM deep check returned "No source principles — QUARANTINE" for all 7 FBs. The v3.0 schema stores evidence in `evidence_passages`, not `source_principles`. |
| **Root Cause** | `check_factual_llm` checked `fb.get("source_principles", [])` and returned immediately if empty. v3.0 convergent extraction does NOT populate `source_principles` — it uses `evidence_passages` directly. |
| **Proposed Fix** | Added `evidence_passages` as fallback. Updated `build_factual_prompt()` to use v3.0 schema fields (mechanism/boundary/consequence) with v2.x fallbacks. |
| **Status** | ✅ FIXED in D2113 E2E run. Both schemas now supported. |
| **Source** | D2113, E2E test 2026-07-25 |

### BUG-047: check_completeness Required Old Schema Fields — FIXED
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (completeness check always failed for v3.0 FBs) |
| **File** | `pipeline/stage5_verify.py`, `check_completeness()` |
| **Symptom** | All FBs scored 0.333 on completeness — missing `application`, `failure_mode`, `elaboration`, `keywords`. v3.0 schema uses `mechanism`, `boundary`, `consequence` instead. |
| **Root Cause** | `check_completeness` had hardcoded v2.x field list. No schema version detection. |
| **Proposed Fix** | Updated required fields to check both v3.0 (mechanism/boundary/consequence) and v2.x (application/failure_mode/elaboration/keywords) with fallback. |
| **Status** | ✅ FIXED in D2113 E2E run. All 7 FBs now pass completeness. |
| **Source** | D2113, E2E test 2026-07-25 |

### BUG-048: Stage 3 (HDBSCAN Clustering) Incompatible with v3.0 Architecture
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (blocks pipeline for small FB counts) |
| **File** | `pipeline/stage3_cluster.py` |
| **Symptom** | With 7 FBs and `hdbscan_min_cluster_size=15`, Stage 3 produces 0 clusters (all noise). Stage 4 then has nothing to merge. The stage was designed for the OLD architecture where Stage 2 produced 100s of raw principles needing clustering. In v3.0, Stage 2 already produces final FBs per cluster — Stage 3 clustering is redundant. |
| **Root Cause** | Architecture shift (extract-before-cluster → cluster-before-extract) made Stage 3's original purpose obsolete. It was repurposed as "semantic dedup" but the HDBSCAN params and schema expectations are incompatible with 7-FB output. |
| **Proposed Fix** | Either: 1) Rewrite Stage 3 as a lightweight semantic dedup pass (no HDBSCAN, just MinHash + embedding cosine check), or 2) Merge Stage 3 into Stage 2 (dedup during extraction), or 3) Remove Stage 3 entirely (FAISS clustering in Stage 1.5 already handles dedup). Recommended: option 3 — remove Stage 3, update pipeline to 6-stage. |
| **Workaround** | `bridge_s2_to_s4.py` bypasses Stage 3 and 4 for testing. |
| **Status** | ✅ MITIGATED (2026-07-26) — When FB count < min_cluster_size, Stage 3 bypasses HDBSCAN and creates singleton clusters. Full architectural decision (remove/replace Stage 3) deferred. |
| **Source** | D2113, E2E test 2026-07-25 |

### BUG-049: FAISS Threshold Hypersensitive — Narrow Sweet Spot
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (calibration issue, not a bug) |
| **File** | `pipeline/stage1_5_embed_cluster.py` |
| **Symptom** | With 237 segments from 3 books: threshold 0.75 → 0 convergent clusters, threshold 0.60 → 1 mega-cluster (all 237 segments), threshold 0.70 → 1 convergent cluster. The gap between "no cross-book" and "everything merges" is only 0.10. |
| **Root Cause** | Small dataset (3 books, heavily dominated by one book: 141/237=60% kaczynski2). With more diverse books, the threshold should be more forgiving. The union-find clustering is also sensitive because one low-similarity bridge can merge two otherwise separate clusters. |
| **Proposed Fix** | 1) Test with 5+ diverse books to find stable threshold. 2) Consider alternative: DBSCAN-style clustering instead of union-find (requires mutual proximity, not transitive). 3) Add cluster quality metrics to auto-tune threshold. |
| **Status** | ✅ RESOLVED (2026-07-26) — R-NN clustering in stage1_5 eliminates transitive bridge-effect. Verified: 32 clusters, 98.7% reciprocal edges at n=800 (P1.1 benchmark). during 5+ book test. Threshold 0.70 is current working value. |
| **Source** | D2113, E2E test 2026-07-25 |

### BUG-050: Only 3 of 20 Books Chunked — Insufficient for Meaningful Convergence
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (data pipeline limitation, not code bug) |
| **File** | `pipeline/stage0_convert.py`, `pipeline/stage1_chunk.py` |
| **Symptom** | 852 books available, 20 in the "Influence + Power" domain, but only 3 were chunked (kaczynski2: 141, SSRN-id2594754: 63, Epistemology In The Cloud: 33). The other 17 books were converted to MD but not chunked — old pipeline stopped after 5 books. Need to re-chunk more books for meaningful cross-source convergent extraction. |
| **Root Cause** | Old pipeline run (July 23) chunked a subset. v3.0 E2E test reused existing chunks. |
| **Proposed Fix** | Run `stage0_convert.py` + `stage1_chunk.py` on 5-10 books from the same domain to get 500-1000+ segments across diverse sources. |
| **Status** | 🟡 OPEN — Next action: chunk 5+ books for meaningful convergence test. |
| **Source** | D2113, E2E test 2026-07-25 |

---
> **Rule:** Accumulate recurring bugs/issues here for LLM handoff with full documentation.
> **When:** 5+ unresolved bugs → append buglog to all LLM handoff documents.
> **Format:** Bug ID, severity, file, lines, symptom, root cause, proposed fix, source, status.

---

## INITIAL POPULATION (2026-07-20) — Consolidated from 7 documents + live code audit

### BUG-001: Empty Pass Loop — Verification Checks Random Principles
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | `pipeline/stage5_verify.py`, lines 115-122 |
| **Symptom** | `source_clusters → principle_ids` mapping loop is empty (`pass`). Falls back to `list(principles_idx.values())[:20]` — first 20 arbitrary principles. A pricing FB is "verified" against design principles. |
| **Root Cause** | The cluster checkpoint mapping was never implemented. Comment says "we approximate" but the approximation is random. |
| **Proposed Fix** | Load cluster checkpoint JSONL, map `cluster_id → principle_ids`, filter `principles_idx` to only those IDs. Fallback: global cosine top-10 if <5 sources found. ~25 LOC. |
| **Source** | Kimi code audit (BUG 1); confirmed in Qwen's `stage5_verify_v2.py` |
| **Status** | ✅ RESOLVED (2026-08-12) — Code path removed in DeBERTa-only S5 rewrite (D2298). Old source_clusters→principle_ids mapping no longer exists. |

### BUG-002: Lineage Broken — pipeline_run_id Regenerated Per Call
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stamp.py`, line 52 |
| **Symptom** | `record["pipeline_run_id"] = record.get("pipeline_run_id") or uuid.uuid4().hex` — every call to `stamp_record()` generates a new UUID4 unless pre-set. Only Stage 4 pre-sets it. Stages 0, 1, 2, 3, 5, 6 get unique UUIDs per record. R14 (lineage) broken for 6 of 7 stages. |
| **Root Cause** | No PipelineRunner that propagates a single run_id through all stages. |
| **Proposed Fix** | Create PipelineRunner class that generates one run_id and injects it into `stamp_record()` for all stages. ~30 LOC. |
| **Source** | Kimi code audit (BUG 2); Qwen's Patch 8+9 |
| **Status** | ✅ RESOLVED — P0.9 applied. get_pipeline_run_id() singleton in stamp.py line 59-64. All stages use same run_id. |

### BUG-003: R5 Violated — Same Model Generates AND Classifies in Stage 4
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage4_merge.py` |
| **Symptom** | Both FB generation AND SALSA classification use `GEN_MODEL` (Qwen3-Coder). A model that hallucinates a domain label also hallucinates the classification that validates that label. Self-fulfilling classification. |
| **Root Cause** | `call_omlx_json(model=GEN_MODEL)` used for both generation and classification calls. |
| **Proposed Fix** | Use `VERIFY_MODEL` (Phi-4-mini) for SALSA classification. ~5 LOC. |
| **Source** | Kimi code audit (BUG 3); R5 (CONSTITUTION.md) |
| **Status** | ✅ UN-REVERTED — oMLX 0.5.3 fixes Phi-4-mini on short prompts (3/3 correct classification at ~360ms). VERIFY_MODEL restored for SALSA per R5. |

### BUG-004: Vector Search Re-Embeds Entire DB Every Query
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/retrieve.py` |
| **Symptom** | `batch_embed(definitions, model="nomic-embed-text")` on every query. At 14 FBs: fine. At 1,000 FBs: ~30 seconds. At 10,000 FBs: minutes per query. O(n) scaling disaster. |
| **Root Cause** | Embeddings not pre-computed at commit time. sqlite-vec mentioned in comments but not implemented. |
| **Proposed Fix** | Pre-compute embeddings at Stage 6 commit time. Store in `vec_fbs` virtual table. Query via sqlite-vec cosine similarity. ~40 LOC. |
| **Source** | Kimi code audit (BUG 4); Qwen's Patch 8 |
| **Status** | ✅ RESOLVED (2026-07-26) — Pre-compute embeddings at Stage 6 commit time via `insert_embedding()`. Fixed vec_fbs dimension: 768→1024 to match bge-m3. `search_vector()` in retrieve.py reads from pre-computed vec_fbs table (O(1) query time). Falls back to FTS if sqlite-vec unavailable. |

### BUG-005: Chunker Paragraph Boundary Destruction
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage1_chunk.py`, `clean_line()` at line 37-38, `split_on_headings()` at line 68+ |
| **Symptom** | `clean_line("")` returns `None`. `split_on_headings()` skips blank lines. `"\n".join(current_lines)` produces a flat blob with no paragraph boundaries. `chunk_text()` splits on `"\n\n"`, finds none, falls back to blind 300-word sliding window. Cuts mid-sentence, mid-idea. |
| **Root Cause** | `clean_line()` destroys the only paragraph boundary signal in Markdown (blank lines) before any join or split can use them. Three prior "final" fixes targeted the join call — all missed this. |
| **Proposed Fix** | `clean_line("")` returns `""` (not `None`). `split_on_headings()` uses `list[list[str]]` for paragraphs. `flush()` joins lines within paragraphs with space, paragraphs with `\n\n`. ~15 LOC. |
| **Source** | Grounded Review §1; Qwen's exact diff (30/30 tests pass) |
| **Status** | ✅ RESOLVED (P0.1) — `clean_line("")` now returns `""` (not `None`), preserving paragraph boundaries. Line 61: `return ""  # P0.1 FIX: was return None. Preserves paragraph boundary.` Verified 2026-08-05. |

### BUG-006: Numbered List Items Silently Dropped
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage1_chunk.py`, line 33 — SKIP_PATTERNS |
| **Symptom** | `re.compile(r"^\s*\d+[.\)]\s")` matches "1. Show the annual plan first..." and drops it silently. Business books contain principles in numbered lists. |
| **Root Cause** | Pattern was added to filter table-of-contents numbering but also catches real content. |
| **Proposed Fix** | Remove the pattern from SKIP_PATTERNS. ~2 LOC. |
| **Source** | Qwen; confirmed in test suite |
| **Status** | ✅ RESOLVED (P0.3) — Numbered-list SKIP_PATTERN removed. Line 49: `# P0.3 FIX: removed numbered-list pattern (contains real principles)`. Verified 2026-08-05. |

### BUG-007: PCA Collapses Non-Linear Semantic Structure
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (compounds with nomic-embed-text) |
| **File** | `pipeline/stage3_cluster.py`, `reduce_dimensions()` at line 73-80 |
| **Symptom** | PCA (linear projection) on 768-dim embeddings → 50 dims. Pricing subtopics (value-based, cost-plus, psychological, subscription) sit on a non-linear manifold. PCA collapses them into one blob. Combined with `min_cluster_size=3`: 2,597/2,697 principles → 1 cluster. |
| **Root Cause** | PCA is a linear algorithm. Semantic relationships in embedding space are non-linear. |
| **Proposed Fix** | Replace PCA with UMAP (n_neighbors=15, min_dist=0.0, metric="cosine", random_state=42). ~10 LOC. |
| **Source** | Grounded Review §3; Qwen's Patch 5 |
| **Status** | ❌ CLOSED (MOOT) — Stage 3 (PCA+HDBSCAN) removed per D2120. Current S1.5 uses FAISS cosine + Louvain, not PCA. No linear dimensionality reduction in pipeline. Verified 2026-08-05. |

### BUG-008: nomic-embed-text Poor Discrimination on Pricing
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (compounds with PCA) |
| **File** | `pipeline/pipeline_paths.py`, line 55 |
| **Symptom** | nomic-embed-text (768-dim) produces embeddings where pricing subtopics are too close together. Compounds PCA collapse. |
| **Root Cause** | Model trained on general text, not domain-specific business principles. |
| **Proposed Fix** | Switch to bge-m3 (1024-dim, 8192 token context, higher MTEB retrieval). ~1 LOC. |
| **Source** | ALL 7 documents |
| **Status** | ❌ CLOSED (MOOT) — nomic-embed-text replaced by bge-m3 (Ollama, 1024-dim) and bge-small-en-v1.5 (MPS, 384-dim) per D2156/D2111. Verified 2026-08-05. |

### BUG-009: HDBSCAN min_cluster_size=3 Too Permissive
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (compounds with PCA + nomic) |
| **File** | `pipeline/pipeline_paths.py`, line 61 |
| **Symptom** | `HDBSCAN_MIN_CLUSTER_SIZE = 3` — any 3 principles that are slightly closer to each other than to noise form a "cluster." Produces spurious micro-clusters and amplifies PCA collapse. |
| **Root Cause** | Parameter chosen for small test runs. Not tuned for 2,697 principles. |
| **Proposed Fix** | Raise to 8 as starting point. Tune after re-run with UMAP + bge-m3. ~1 LOC. |
| **Source** | Grounded Review; Qwen's Patch 7 |
| **Status** | ❌ CLOSED (MOOT) — HDBSCAN removed per D2120. Current clustering uses Louvain community detection (S1.5), not HDBSCAN. Verified 2026-08-05. |

### BUG-010: Dead pipeline_config.yaml
| Field | Value |
|-------|-------|
| **Severity** | 🟡 LOW |
| **File** | `config/pipeline_config.yaml` |
| **Symptom** | File exists in repo but is never imported by any pipeline stage. All configuration is hardcoded in `pipeline_paths.py` or read from environment variables. The YAML file is dead code. |
| **Root Cause** | Config loader was never wired. |
| **Proposed Fix** | Wire `load_config()` in pipeline runner OR delete the file. ~15 LOC if wiring. |
| **Source** | Kimi code audit (BUG 6) |
| **Status** | ✅ RESOLVED — `pipeline_config.yaml` is actively loaded by `pipeline_paths.py` (_CFG). All stages read config via `pipeline_paths.py` imports. Verified 2026-08-05. |

### BUG-011: Zero Tests
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (CRITICAL for v2+) |
| **File** | `tests/` — directory doesn't exist |
| **Symptom** | Zero test files. No `tests/` directory. No unit tests, no integration tests, no golden-file tests. CONSTITUTION mentions "Test suite gate" but there is no test suite. |
| **Root Cause** | Pipeline was built for proof-of-concept. Tests were never added. |
| **Proposed Fix** | Add `tests/test_chunker.py` (Qwen provides 30 tests). Add `tests/test_pipeline.py` (Fixed Implementation provides). ~100 LOC. |
| **Source** | Kimi code audit (BUG 7); Qwen; Fixed Implementation FILE 12 |
| **Status** | 🟡 OPEN — Phase 0 (after fixes, before re-run) |

### BUG-012: sqlite-vec Not Loaded Before CREATE VIRTUAL TABLE
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage6_commit.py` (or wherever `init_schema()` is) |
| **Symptom** | `CREATE VIRTUAL TABLE ... USING vec0(...)` runs before `sqlite_vec.load(conn)`. Raises `sqlite3.OperationalError: no such module: vec0` on first run. |
| **Root Cause** | Python's stdlib `sqlite3` has extension loading disabled by default. The correct API is `sqlite_vec.load(conn)`, not `conn.load_extension("vec0")`. |
| **Proposed Fix** | `conn.enable_load_extension(True)` → `sqlite_vec.load(conn)` → `conn.enable_load_extension(False)`. ~3 LOC. |
| **Source** | Grounded Review §3; Qwen's Patch 11 |
| **Status** | 🟠 OPEN — Phase 0, P0.11 |

### BUG-013: OMLX Guard Uses pkill -f (Kills Pipeline Itself)
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/omlx_guard.py` (or omlx_call.py) |
| **Symptom** | `pkill -f omlx` kills ALL processes matching "omlx" — including the pipeline script itself if it contains "omlx" in its command string. |
| **Root Cause** | Overly broad process matching. |
| **Proposed Fix** | Use `pgrep -f "omlx serve"` to find OMLX server PID specifically, then `os.kill(pid, signal.SIGTERM)` with PID≠own. ~10 LOC. |
| **Source** | Qwen's Patch 13 |
| **Status** | 🟠 OPEN — Phase 0, P0.12 |

### BUG-014: Cloud Burst Code Violates C1/C3
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (constitutional violation) |
| **File** | `pipeline/core/inference.py` (or wherever `cloud_generate()` lives) |
| **Symptom** | DeepSeek API endpoint, `cloud_generate()`, `deepseek_api_key` config. Ships book text to third-party API. Violates C1 ($0 marginal cost) and C3 (sovereign). |
| **Root Cause** | Extraction speed concern led to cloud fallback proposal. No constitutional exception clause exists for "extraction only." |
| **Proposed Fix** | Delete all cloud code. Fix extraction speed via semantic pre-filter + DFlash + better chunking. ~-30 LOC. |
| **Source** | Grounded Review; Qwen; CONSTITUTION.md C1/C3 |
| **Status** | ✅ RESOLVED (2026-08-12) — No cloud burst code exists anywhere in repo. Only `cloud_fallback` role in model_assignments.yaml (archived). |

### BUG-015: Silent datasketch Import Failure
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage2_extract.py` |
| **Symptom** | If `datasketch` isn't installed, MinHash near-dedup silently disables with just a `print()` statement. For unattended overnight run, near-duplicate principles reach clustering, inflating apparent "convergence." |
| **Root Cause** | Import wrapped in try/except with print, not raise or log.WARNING. |
| **Proposed Fix** | Raise ImportError or log at WARNING level with clear message. ~5 LOC. |
| **Source** | Grounded Review §4 |
| **Status** | ✅ RESOLVED — Now raises ImportError per C16 (no silent errors). Fix applied 2026-07-21 (C5). |

### BUG-016: Model Assignments Reference Phantom Models
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `config/model_assignments.yaml` |
| **Symptom** | References model names that may not exist as real artifacts: `Qwopus-GLM-18B`, `glm-5.2-colibri`, `opus-distilled-27b`. If any code path resolves a role to one of these, fails at runtime with confusing "model not found" error. |
| **Root Cause** | Placeholder/aspirational entries. Never audited against actual model directory. |
| **Proposed Fix** | Audit: `ls ~/.cache/omlx/models/` against every string in `model_assignments.yaml`. Remove or comment out phantom entries. ~0 LOC (manual audit). |
| **Source** | Grounded Review §4 |
| **Status** | 🟡 OPEN — Phase 0, P0.14 |

### BUG-017: OMLX Kernel Memory Leak — Mitigation Untested
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | N/A (OMLX server issue — GitHub #2184) |
| **Symptom** | Wired memory leak on OMLX jetsam kill. Requires reboot to recover. Mitigation (`--memory-guard aggressive`) assumed to work but has never been tested on sustained 130-book runs. Single point of failure for entire pipeline. |
| **Root Cause** | OMLX server bug. Not a Maxwell OS code bug. |
| **Proposed Fix** | Stress test: 5 consecutive pipeline runs, monitor `vm_stat` for wired memory accumulation. If growth >10%, add explicit `sudo purge` between stages or reduce batch sizes. |
| **Source** | ROUNDTABLE-HANDOFF; Gap A from ULTIMATE-CROSS-EXAMINATION-HANDOFF.md |
| **Status** | ✅ RESOLVED (2026-08-12, G10) — `pipeline/omlx_wired_stress.py` (D2020 Layer 1): 5 rounds × 20 reqs, wired flat 34.26→34.22 GB (-0.11% cumulative), 0 errors. No GitHub #2184 leak detected. Run `just wired-stress` as the pre-26h-run gate. |

---

## RESOLVED (From D2002 stress test, already fixed in live repo)

| Bug ID | Description | Fix |
|--------|-------------|-----|
| BUG-R01 | `pipeline_paths.py`: .md not in supported extensions | Added `.md` to SUPPORTED_EXTENSIONS |
| BUG-R02 | `stage1_chunk.py`: Variable shadowing `chunk_text` function | Renamed loop variable |
| BUG-R03 | `stage1_chunk.py`: Shrink guard blocking incremental runs | Adjusted threshold for append-mode runs |
| BUG-R04 | `omlx_call.py`: Typo `call_omxl` → `call_omlx` | Fixed |
| BUG-R05 | `omlx_call.py`: Missing API key header | Added `sk-maxwell-local` |
| BUG-R06 | `pipeline_paths.py`: Wrong model name | Fixed to `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` |
| BUG-R07 | `stage4_merge.py`: `jargon` field returned as dict, not string | Added string coercion |
| BUG-R08 | `stage4_merge.py`: Missing `Optional` import | Added import |
| BUG-R09 | `stage6_commit.py`: SQLite insert failed on dict-type fields | Added json.dumps() for list/dict fields |
| BUG-R10 | `stage6_commit.py`: Parquet export failed on dict-type fields | Added JSON serialization for Parquet |

---

## BUGLOG RULES

1. **When to add:** Any bug found during pipeline execution, code review, or LLM cross-examination
2. **Severity levels:** 🔴 CRITICAL (data loss, constitutional violation, pipeline failure) | 🟠 HIGH (broken feature, incorrect output) | 🟡 MEDIUM (quality degradation, scaling issue) | 🟢 LOW (cosmetic, documentation)
3. **Handoff trigger:** 5+ unresolved bugs → append full buglog to all LLM handoff documents
4. **Resolution:** Mark as RESOLVED when fix is committed and verified. Move to RESOLVED section with reference to commit hash.
5. **Ownership:** Each bug must have a proposed fix and a target phase. No bug stays "acknowledged but unassigned."

---

*Generated: 2026-07-20 | Bugs tracked: 17 open, 10 resolved | Schema version: 1.0*

---

## SESSION RESOLUTIONS (2026-07-21) — Cross-Examination + Consolidation

The following bugs were resolved during the 2026-07-21 cross-examination session. Fixes applied to pipeline code, verified via syntax check, and committed to `claude projects/maxwell os 2.0/`.

| Bug ID | Resolution | Fix Applied |
|--------|-----------|-------------|
| BUG-001 | ✅ RESOLVED | P0.8: `_load_cluster_map()` implemented in `stage5_verify.py` |
| BUG-002 | ✅ RESOLVED | P0.9: Singleton `get_pipeline_run_id()` in `stamp.py` |
| BUG-003 | ⚠️ REVERTED | P0.10: VERIFY_MODEL→GEN_MODEL reverted (Phi-4-mini broken on short prompts) |
| BUG-005 | ✅ RESOLVED | P0.1-P0.2: `clean_line("")`→`""`, paragraph-aware `split_on_headings()` |
| BUG-006 | ✅ RESOLVED | P0.3: Numbered-list pattern removed from SKIP_PATTERNS |
| BUG-007 | ✅ RESOLVED | P0.5: UMAP replaces PCA in `stage3_cluster.py` |
| BUG-008 | ✅ RESOLVED | P0.6: bge-m3 replaces nomic-embed-text in `pipeline_config.yaml` |
| BUG-009 | ✅ RESOLVED | P0.7: HDBSCAN `min_cluster_size` 3→8 in config |
| BUG-010 | ✅ RESOLVED | `pipeline_config.yaml` now wired via `pipeline_paths.py` thin loader |
| BUG-011 | ✅ RESOLVED | `tests/test_chunker.py` created (30 tests) |
| BUG-012 | ✅ RESOLVED | P0.11: `sqlite_vec.load(conn)` before virtual table in `stage6_commit.py` |
| BUG-013 | ✅ RESOLVED | P0.12: `omlx_watchdog.py` replaces pkill-based guard (M2/D2027) |
| BUG-014 | ✅ RESOLVED | P0.13: No cloud code found in pipeline — C1/C3 compliant |
| BUG-016 | ✅ RESOLVED | P0.14: Phantom models nuked, bge-m3 replaces nomic, old paths fixed |

**Still open:** BUG-004 (Phase 1), BUG-017 (needs stress test)

---

## NEW BUGS — 2026-07-21 Session

### BUG-018: Orphaned Indentation in stage1_chunk.py clean_line()
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage1_chunk.py`, line 62 |
| **Symptom** | `if len(stripped) < 10:` with no indented body. Causes `IndentationError` on import. Entire pipeline fails at Stage 1. |
| **Root Cause** | Incomplete edit during P0.4 application — the min-length filter was removed but the `if` statement header was left behind without a body. |
| **Proposed Fix** | Remove orphaned `if` line, replace with comment. ~2 LOC. |
| **Source** | Live cross-examination (2026-07-21) — found during chunker syntax verification |
| **Status** | ✅ RESOLVED — Fixed during same session |

### BUG-019: pipeline_paths.py Missing Legacy Exports
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/pipeline_paths.py` |
| **Symptom** | All 7 stage files import `CHECKPOINT_DIR`, `DB_PATH`, `OMLX_BIN` from `pipeline_paths.py`. The new thin YAML-based loader didn't export these names. `ImportError` on every stage file. |
| **Root Cause** | pipeline_paths.py was rewritten as thin YAML loader without backward-compatible aliases for the old flat-path names that stage files still use. |
| **Proposed Fix** | Add legacy aliases at end of file. ~4 LOC. |
| **Source** | Live cross-examination (2026-07-21) — found during pipeline import verification |
| **Status** | ✅ RESOLVED — D2038, aliases added |

### BUG-020: model_assignments.yaml Phantom Models
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `config/model_assignments.yaml` |
| **Symptom** | Four phantom model references: `nomic-embed-text` (replaced by bge-m3), `Qwopus-GLM-18B`, `opus-distilled-27b`, `glm-5.2-colibri`. Also two old v1 paths referencing `claude projects/maxwell os/tools/`. Runtime failures if any code path resolves to these. |
| **Root Cause** | Placeholder/aspirational entries never audited. nomic-embed-text was not updated when bge-m3 was adopted. |
| **Proposed Fix** | Replace nomic→bge-m3, comment out phantoms, disable old paths. Manual audit. |
| **Source** | P0.14 audit (2026-07-21) |
| **Status** | ✅ RESOLVED — All phantoms nuked, bge-m3 wired |

### BUG-021: LaunchAgents Recreating Deleted v1 Directory
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `~/Library/LaunchAgents/com.maxwell.memoryguardian.plist`, `com.maxwellos.watchdog.plist` |
| **Symptom** | Two active LaunchAgents ran every few minutes trying to execute deleted v1 scripts (`memory_guardian.py`, `watchdog_guard.py`). Failed with "No such file or directory" but recreated `claude projects/maxwell os/logs/` directory and wrote error logs. User saw folder reappearing after deletion. |
| **Root Cause** | v1 LaunchAgents never disabled when v2 pipeline was adopted. |
| **Proposed Fix** | `launchctl unload` both plists, rename to `.DISABLED` suffix. |
| **Source** | Live investigation (2026-07-21) |
| **Status** | ✅ RESOLVED — D2035, both plists disabled |

### BUG-022: Dropbox Sync Creates 5 Project Folder Variants
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | N/A (Dropbox filesystem) |
| **Symptom** | Five variants of "claude projects" existed in Dropbox: `claude projects`, `claude projects +`, `claude projects+`, `claude projects (clone)`, `claude projects (Klaus Beyer's conflicted copy)`. Different sessions and devices wrote to different variants. Code existed in `claude projects +` while governance docs were scattered. |
| **Root Cause** | Dropbox FileProvider sync conflicts across multiple devices. The root `claude projects` folder has `com.dropbox.attrs` xattr and cannot be permanently deleted — Dropbox recreates it from cloud sync. |
| **Proposed Fix** | Consolidate all project files into `claude projects/maxwell os 2.0/`. Delete other variants where possible. Accept that `claude projects` root folder persists via Dropbox sync. |
| **Source** | Live cross-examination (2026-07-21) |
| **Status** | ✅ RESOLVED — D2033, single project folder unified |

---

## BUGLOG RULES — AMENDED (2026-07-21, 2026-07-22)

1. **When to add:** Any bug found during pipeline execution, code review, cross-examination session, or LLM handoff evaluation
2. **Severity levels:** 🔴 CRITICAL (data loss, constitutional violation, pipeline failure) | 🟠 HIGH (broken feature, incorrect output, import failure) | 🟡 MEDIUM (quality degradation, scaling issue, phantom references) | 🟢 LOW (cosmetic, documentation)
3. **Handoff trigger:** 5+ unresolved bugs → append full buglog to all LLM handoff documents (C15)
4. **Resolution:** Mark as RESOLVED when fix is committed and verified. Move to RESOLVED section with reference to commit hash or session date.
5. **Ownership:** Each bug must have a proposed fix and a target phase. No bug stays "acknowledged but unassigned."
6. **SESSION RULE:** After every working session, accumulate all discovered bugs here. This is a standing rule for LLM handoff continuity.
7. **Format:** Bug ID (BUG-NNN), severity emoji, file path, line numbers, symptom, root cause, proposed fix, source (which review/audit/session found it), status.
8. **AUTO-LOG (2026-07-22):** Agent MUST log any bug immediately upon discovery — never defer. Only log bugs found in existing code/systems/configuration, not self-created errors in ad-hoc scripts.

---

*Updated: 2026-07-23 | Bugs tracked: 37 (17 original + 5 new + 7 audit + 7 benchmark + 1 new) | Resolved: 37 | Open: 2 (BUG-017, BUG-037) | Observations: 2 (OBS-001, OBS-002) | Schema version: 1.4*
## QWEN CROSS-EXAMINATION SESSION (2026-07-21)

### Design Observations for Pre-Implementation Testing

#### OBS-001: SALSA Cross-Domain Inflation Risk
- Severity: MEDIUM (needs production data)
- File: stage4_merge.py build_classify_prompt()
- SALSA lists 25 domains inline; LLMs may over-assign (3-5 domains per FB)
- Test: After first run, audit 50 FBs. If >30% spurious → dichotomous SALSA (D2024).
- Source: Qwen fix.md Bug #6
- Status: NEEDS TESTING — Phase 1

#### OBS-002: Author-Weighted BORP Gap
- Severity: MEDIUM
- File: stage5_verify.py check_borp()
- BORP counts books not authors. 5 books × same author = BORP 5 (false pass).
- Test: After golden set, compare weighted vs unweighted. >20% status change → implement.
- Proposed: weighted = raw_borp*0.30 + author_ratio*0.70
- Source: Qwen fix.md Bug #8
- Status: NEEDS TESTING — Phase 1 with metadata

### Qwen 15 Claims — Cross-Examination Verdict
| # | Claim | Actual | Action |
|---|-------|--------|--------|
| 1 | Phi-4-mini empty on classification | CONFIRMED | FIXED: GEN_MODEL for SALSA |
| 2 | source_clusters undefined | CONFIRMED | FIXED: fb.get() |
| 3 | EMBED_MODEL=nomic | Doc stale, code reads YAML=bge-m3 | FIXED: docstring |
| 4 | PARQUET_DIR/DATA_DIR missing | CONFIRMED | FIXED: legacy aliases |
| 5 | gemma-4-26B broken | CONFIRMED | FIXED: Qwen3-Coder |
| 6 | SALSA cross-domain | Plausible | LOGGED: OBS-001 |
| 7 | No anti-hallucination | Partial | FIXED: CRITICAL RULES |
| 8 | Author BORP | Feature gap | LOGGED: OBS-002 |
| 9 | MIN_CHUNK_WORDS import | WRONG | Not a bug |
| 10 | schemas.py spaces | WRONG | Not a bug |
| 11 | pipeline_paths Path(file) | WRONG | Not a bug |
| 12 | Unicode SyntaxError | WRONG | Not a bug |
| 13 | metrics.py Path(file) | WRONG | Not a bug |
| 14 | unloader.py URL space | WRONG | Not a bug |
| 15 | hardcoded bge-m3 | CONFIRMED | FIXED: EMBED_MODEL |
| **Hit rate:** 7/15 confirmed, 2 design obs, 6 false |
---

## BUG AUDIT SESSION — BUG-023 through BUG-029 (2026-07-21)

Cross-examined from temp/bug fix.txt audit. All entries verified against production code.

### BUG-023: source_clusters Undefined in stage5_verify.py check_factual()
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | `pipeline/stage5_verify.py`, line 175 |
| **Symptom** | `for cid in source_clusters:` — NameError on every FB verification. Stage 5 crashes. |
| **Root Cause** | Variable `source_clusters` used but never extracted from `fb` dict. |
| **Fix** | Added `source_clusters = fb.get("source_clusters", [])` before the loop. Also handles JSON-string case. ~5 LOC. |
| **Source** | Qwen fix.md, confirmed by temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — runtime test passed |

### BUG-024: PARQUET_DIR and DATA_DIR Not Exported from pipeline_paths.py
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | `pipeline/pipeline_paths.py`, `pipeline/stage6_commit.py` line 18 |
| **Symptom** | `ImportError` — stage6 imports PARQUET_DIR/DATA_DIR but neither exists in pipeline_paths.py. Pipeline won't start. |
| **Root Cause** | Legacy aliases section only defined CHECKPOINT_DIR, DB_PATH, OMLX_BIN. |
| **Fix** | Added `PARQUET_DIR` and `DATA_DIR` to the legacy aliases block. ~4 LOC. |
| **Source** | Qwen fix.md, confirmed by temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — import test passed |

### BUG-025: FTS5 Index Lost Across Pipeline Runs
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage6_commit.py`, `init_db()` |
| **Symptom** | `DELETE FROM fbs_fts` clears FTS index, then `AFTER INSERT` triggers only rebuild for rows inserted in THIS run. Second run on a subset loses FTS entries from first run. |
| **Root Cause** | DELETE + trigger-rebuild only covers newly inserted rows. |
| **Fix** | Replaced DELETE with `INSERT INTO fbs_fts(fbs_fts) VALUES('rebuild')` which rebuilds from ALL existing fbs rows. Fallback to DELETE if rebuild fails. ~8 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — syntax + content verified |

### BUG-026: stage4_merge.py Uses Fragile stamp_record({}) Pattern
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage4_merge.py`, line 285 |
| **Symptom** | `stamp_record({})["pipeline_run_id"]` creates a throwaway dict just to extract the run_id. Works (singleton) but fragile and confusing. |
| **Fix** | Import `get_pipeline_run_id` directly and call it: `pipeline_run_id = get_pipeline_run_id()`. ~2 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — syntax verified |

### BUG-027: stage2 --intent Flag Not Documented as Prompt-Level Only
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage2_extract.py`, `run_stage2()` |
| **Symptom** | `--intent` flag on Stage 2 modifies the system prompt but users might think it does chunk-level filtering. Actual chunk filter is Stage 1.5. |
| **Fix** | Added warning print when `--intent` is used: "applied as prompt-level focus only. For chunk-level semantic filtering, run stage1_5_intent.py first." ~3 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED |

### BUG-028: ollama_embed.py Hardcoded OLLAMA_URL
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/ollama_embed.py`, line 33 (original) |
| **Symptom** | `OLLAMA_URL = "http://localhost:11434/api/embed"` hardcoded — ignores `pipeline_paths.py` config. Changing port requires editing code. |
| **Fix** | Import `OLLAMA_HOST`, `OLLAMA_PORT` from pipeline_paths.py and construct URL dynamically: `f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embed"`. Old line commented. ~3 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — OLLAMA_URL matches config |

### BUG-029: metrics.py Path(file) + Trailing Spaces — FALSE POSITIVE
| Field | Value |
|-------|-------|
| **Severity** | ⬜ NOT A BUG |
| **File** | `pipeline/metrics.py` |
| **Symptom** | Bugfix file claimed `Path(file)` (no underscores) and trailing spaces in dict keys/f-strings. |
| **Investigation** | Actual code uses `Path(__file__)`. No trailing spaces found. These are **rendering artifacts** from the upload process — double underscores stripped during markdown/html rendering. Confirmed by bugfix file's own Part 3. |
| **Status** | ❌ CLOSED — false positive, rendering artifact |

---

## BUG-001 through BUG-017 — STATUS AUDIT (2026-07-21)

Cross-referenced all 17 original bugs against production code.

| Bug | Original Status | Current Status | Notes |
|-----|----------------|----------------|-------|
| BUG-001 | OPEN — P0.8 | ✅ RESOLVED | _load_cluster_map() + source_clusters fix applied |
| BUG-002 | OPEN — P0.9 | ✅ RESOLVED | get_pipeline_run_id() singleton in stamp.py |
| BUG-003 | OPEN — P0.10 | ⚠️ REVERTED | GEN_MODEL for both (Phi-4-mini broken on classification) |
| BUG-004 | OPEN — Phase 1 | 🔴 OPEN | retrieve.py still re-embeds per query. Needs sqlite-vec pre-computation. |
| BUG-005 | OPEN — P0.1/2 | ✅ RESOLVED | clean_line() returns "", paragraph boundaries preserved |
| BUG-006 | OPEN — P0.3 | ✅ RESOLVED | Numbered-list pattern removed from SKIP_PATTERNS |
| BUG-007 | OPEN — P0.5 | ✅ RESOLVED | UMAP replaces PCA (cosine metric, random_state=42) |
| BUG-008 | OPEN — P0.6 | ✅ RESOLVED | bge-m3 (1024-dim) primary, nomic-embed-text fallback |
| BUG-009 | OPEN — P0.7 | ✅ RESOLVED | hdbscan_min_cluster_size raised to 8 in config |
| BUG-010 | OPEN — Phase 0.5 | ✅ RESOLVED | pipeline_config.yaml wired via pipeline_paths.py |
| BUG-011 | OPEN — Phase 0 | ✅ RESOLVED | tests/ directory exists, 12/12 chunker tests pass |
| BUG-012 | OPEN — P0.11 | ✅ RESOLVED | sqlite_vec.load() before CREATE VIRTUAL TABLE |
| BUG-013 | OPEN — P0.12 | ✅ RESOLVED | omlx_watchdog.py with RSS monitoring, no pkill |
| BUG-014 | OPEN — P0.13 | ✅ RESOLVED | No cloud code found in pipeline |
| BUG-015 | OPEN — P0.5.5 | ✅ RESOLVED | datasketch import now raises ImportError |
| BUG-016 | OPEN — P0.14 | ✅ RESOLVED | Phantom models removed/commented in model_assignments.yaml |
| BUG-017 | OPEN — P0.0 | ✅ RESOLVED (G10) | Wired-memory stress test PASS — flat (-0.11%), no leak |

**Summary: 14/17 resolved, 1 reverted (BUG-003), 2 still open (BUG-004, BUG-017)**

---

## BENCHMARK SESSION — BUG-030 through BUG-036 (2026-07-22)

### BUG-030: DeepSeek-R1 Token Encoding Mismatch — Garbled Output
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | N/A (oMLX/MXL model loading) |
| **Symptom** | All DeepSeek-R1 output contains `Ċ` and `Ġ` character prefixes (e.g., `ĊFirst,ĠtheĠuserĠsaid:`). CoT reasoning tokens leaked into output. Model unusable. |
| **Root Cause** | Tokenizer encoding mismatch between the LM Studio community MLX port and oMLX 0.5.3. The chat_template is not correctly configured. |
| **Proposed Fix** | Replace with `mlx-community/DeepSeek-R1-Distill-Qwen-7B-MLX-4bit` (distilled, no CoT leakage). Or fix tokenizer_config.json in the model directory. |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🔴 OPEN — Remove model. Replace with distilled version. |

### BUG-031: Qwopus-GLM-18B "Thinking Process" Preamble Pollutes Output
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | N/A (model behavior) |
| **Symptom** | Every response starts with "Thinking Process:" followed by step-by-step reasoning before actual output. Not compatible with structured JSON extraction or classification. |
| **Root Cause** | Model is a reasoning/CoT variant. The chat_template exposes thinking tokens instead of hiding them (like DeepSeek-R1's intended behavior). |
| **Proposed Fix** | Remove from pipeline lineup. If reasoning is needed, use a model with hidden CoT (like Qwen3-Coder's internal reasoning). |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🔴 OPEN — Remove model. Not suitable for pipeline tasks. |

### BUG-032: gemma-4-E4B Extraction Latency Spikes to 21.95s
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | N/A (model behavior) |
| **Symptom** | Extraction latency varies wildly: 1.22s on first warm call, 21.95s on second call. 18x variance. Other tasks remain fast (classification: 0.55-1.14s). |
| **Root Cause** | Likely MLX graph recompilation or model swapping in oMLX engine pool. Extraction prompt is longer (~200 tokens) and may trigger recompilation. |
| **Proposed Fix** | Use only for short-prompt tasks (classification, verification) where it's consistently fast (0.50-1.14s). Not suitable for extraction. |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🟡 NEEDS INVESTIGATION — Test with pinned model (disable engine pool auto-swap). |

### BUG-033: gemma-4-E2B Extraction Latency Spikes to 13.20s
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | N/A (model behavior) |
| **Symptom** | Same extraction latency variance as E4B: 0.76s first call, 13.20s second call. |
| **Root Cause** | Same as BUG-032 — MLX graph recompilation on longer prompts. |
| **Proposed Fix** | Pin model in oMLX engine pool. Test with `--memory-guard aggressive` which may prevent unloading between calls. |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🟡 NEEDS INVESTIGATION |

### BUG-034: Qwen3-Coder Misclassification — "Economics" for Scarcity Principle
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | N/A (LLM behavior, Stage 4 classification) |
| **Symptom** | Qwen3-Coder classified "Scarcity increases perceived value because people want what is rare or limited" as "economics" instead of "marketing" or "psychology". 1 misclassification in 3 attempts. |
| **Root Cause** | Qwen3-Coder has broader domain associations. "Scarcity" is a term used in both economics and marketing psychology. The model chose the more academic association. |
| **Proposed Fix** | This is why R5 exists — Phi-4-mini (VERIFY_MODEL) classifies it correctly as "marketing". Generator classification should NOT be the final label. VERIFY_MODEL must always override. |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🟡 CONFIRMS NEED FOR R5 — Generator ≠ Verifier is essential. |

### BUG-035: Ornith-1.0-9B-4bit — Archive Empty, Model Not Downloaded
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `/Users/barn/.omlx/models_archive/Ornith-1.0-9B-4bit/` |
| **Symptom** | Archive directory exists but contains zero files. HF cache has lock file but no actual weights. Model was never fully downloaded. |
| **Root Cause** | Partial/incomplete download. HF lock file created but download never completed. |
| **Proposed Fix** | Re-download: `omlx-cli pull mlx-community/Ornith-1.0-9B-4bit` or delete lock file and archive. |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🟡 OPEN — Download or remove. |

### BUG-036: Qwen3.6-35B-A3B Model Directory Has Config Only, No Weights
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `/Users/barn/.omlx/models/Qwen3.6-35B-A3B-4bit/` |
| **Symptom** | Directory restored from archive contains only config files (README.md, config.json, chat_template.jinja). No safetensors/model weights. oMLX API returns "Model not found." Weights are in HF cache at `models--mlx-community--Qwen3.6-35B-A3B-4bit` but model not discoverable by oMLX. |
| **Root Cause** | Model was archived with config only, or oMLX 0.5.3 changed model discovery paths. Weights are in HF cache but need proper linking. |
| **Proposed Fix** | Re-download: `omlx-cli pull mlx-community/Qwen3.6-35B-A3B-4bit`. Or symlink weights from HF cache into oMLX models directory. |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🟡 OPEN — Re-download or fix symlinks. |

### BUG-037: Duplicate Phi-4-mini Model Cannot Be Deleted via API
| Field | Value |
|-------|-------|
| **Severity** | 🟢 LOW |
| **File** | oMLX 0.5.3 API |
| **Symptom** | `DELETE /v1/models/mlx-community--Phi-4-mini-instruct-8bit` returns 404 "Not Found". Model is listed in `GET /v1/models` but cannot be removed via API. |
| **Root Cause** | oMLX 0.5.3 may not support DELETE endpoint, or the model name format doesn't match internal ID. |
| **Proposed Fix** | Remove via oMLX GUI app: uncheck the duplicate model. Or remove from disk: delete `~/.cache/huggingface/hub/models--mlx-community--Phi-4-mini-instruct-8bit/`. |
| **Source** | 2026-07-22 benchmark session |
| **Status** | 🟢 LOW — Remove via GUI or filesystem. |


---

## SESSION RESOLUTIONS (2026-07-23) — D2069/D2070 Verification Rewrite + Bug Sweep

The following bugs were resolved during the 2026-07-23 session. Fixes applied and verified.

| Bug ID | Resolution | Fix Applied |
|--------|-----------|-------------|
| BUG-003 | ✅ RESOLVED | D2069: R5 fully restored. Stage 5 verifier → Gemma-4-E4B (cross-family). Qwen≠Phi≠Gemma. |
| BUG-004 | ✅ RESOLVED | BUG-004 FIX: `insert_embedding()` in stage6_commit.py pre-computes embeddings. `search_vector()` in retrieve.py uses sqlite-vec MATCH (O(1) not O(n)). ~55 LOC. |
| BUG-030 | ✅ RESOLVED | DeepSeek-R1 deleted from disk (~4KB stub removed). Model unusable (CoT leakage). |
| BUG-031 | ✅ RESOLVED | Qwopus-GLM-18B deleted from disk. "Thinking Process" preamble incompatible with structured output. |
| BUG-032 | ✅ RESOLVED | Gemma-4-E4B re-benchmarked on oMLX 0.5.3: 1.4s (short), 6.4s (medium), 6.9s (long). No 21s spikes. Stable. |
| BUG-033 | ✅ RESOLVED | gemma-4-E2B deleted from disk (4.1GB freed). Superseded by E4B. |
| BUG-034 | ✅ RESOLVED | R5 fix (D2069). Qwen3-Coder no longer classifies its own output. Phi-4-mini classifies, Gemma verifies. |
| BUG-035 | ✅ RESOLVED | Ornith-1.0-9B archive empty → deleted. Model never fully downloaded. |
| BUG-036 | ✅ RESOLVED | Qwen3.6-35B-A3B weights confirmed (19GB, 4 safetensors in HF cache + OMLX symlink). Model is fully functional. |
| BUG-037 | 🔴 NEEDS RESTART | OMLX registry still lists 10 models (6 deleted from disk). Requires OMLX GUI app restart to clear stale entries. Not a code bug. |
| BUG-039 | 🟡 OBSERVATION | BUG-005/006/007/008/009 root cause fixed. Text cleaner (H1-H2) strips markdown artifacts + normalizes paragraphs. Cluster collapse from PCA+nomic no longer applies (UMAP+bge-m3). |
| BUG-040 | 🟡 OBSERVATION | Cross-run dedup (C9) requires datasketch. If datasketch unavailable, MinHash near-duplicate detection silently disables (falls through to SHA-256 exact only). priint() warning on import failure. |
| BUG-016 | ✅ RESOLVED | model_assignments.yaml: all phantom models removed (Qwopus, colibri, opus-distilled, deepseek fallbacks). 4 family mismatches fixed. |

### NEW BUG — 2026-07-23

---

## 2026-07-25 — D2094 Tier 1 Implementation Session (Architecture Fix)

### BUG-040: Delegate Tool Fails with reasoning_content API Error (2 consecutive failures)
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (blocks delegated code generation) |
| **File** | N/A (Goose delegate/infrastructure layer) |
| **Symptom** | Two independent delegate calls (task 20260725_1 and 20260725_2) both failed identically with: `Request failed: Bad request (400): The reasoning_content in the thinking mode must be passed back to the API.` Both tasks completed in 20-30s with zero output. |
| **Root Cause** | The delegate infrastructure appears to use a model in "thinking mode" that emits `reasoning_content`. When the response is returned to the API, the `reasoning_content` field is not being passed back, causing a 400 Bad Request. This is likely a protocol mismatch between the delegate runner and the underlying model API. |
| **Impact** | Blocks all Tier 1 delegated code generation. Forced manual file creation (407-line stage1_5_embed_cluster.py written directly). |
| **Reproduction** | Any delegate call with `async: true` and custom instructions targeting a file write. Both attempts reproduced identically. |
| **Proposed Fix** | 1) Investigate whether delegate model supports thinking mode — if not, disable it. 2) If thinking mode is required, ensure `reasoning_content` is propagated back in subsequent API calls. 3) Add fallback: if thinking mode fails, retry without it. |
| **Source** | 2026-07-25 Tier 1 implementation session. Tasks 20260725_1, 20260725_2. |
| **Status** | 🔴 OPEN — Needs investigation at delegate/infrastructure level. Workaround: manual file writes. |

### BUG-041: No Delegation Code Review Possible — Manual Code Only
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (blocks R5 cross-family verification of generated code) |
| **File** | N/A (workflow limitation) |
| **Symptom** | The Maxwell OS constitution requires R5 (Generator ≠ Verifier — different model families). The plan was: delegate code generation to Qwen-family model, then delegate code review to Gemma/Phi-family model. BUG-040 blocks all delegation, making cross-family code review impossible via the delegate system. |
| **Root Cause** | Same as BUG-040 — delegate infrastructure cannot complete any task. |
| **Impact** | All Tier 1 code written directly without cross-family review. stage1_5_embed_cluster.py (407 LOC), stage5_verify.py fail-open flips (4 lines), stage4_merge.py noise wire (24 lines), pipeline_config.yaml, pipeline_paths.py — none received R5-compliant review. |
| **Proposed Fix** | After BUG-040 is resolved, run cross-family review on all files modified in this session: stage1_5_embed_cluster.py, stage5_verify.py (lines 245-267), stage4_merge.py (load_stage3_clusters), config/pipeline_config.yaml, pipeline/pipeline_paths.py. |
| **Source** | 2026-07-25 Tier 1 implementation session. |
| **Status** | 🟠 OPEN — Deferred until BUG-040 resolved. Manual review should be done as interim measure. |

### BUG-042: stage5_verify.py — Embedding Similarity Check Still Active (Not Yet Removed)
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (fail-open branches now fail-closed, but embedding check is still the wrong tool) |
| **File** | `pipeline/stage5_verify.py`, lines 83-149 (`embedding_similarity_check()`) |
| **Symptom** | The fail-open branches (V2-V5) have been flipped to fail-closed. However, the `embedding_similarity_check()` function still runs as the pre-filter. It measures cosine similarity between FB definition and source_principles (paraphrases), not actual NLI entailment. The code comment at line 83-96 still explains why they abandoned DeBERTa. |
| **Root Cause** | V1 (port DeBERTa NLI from old project) and V6 (remove embedding similarity) were NOT completed in this session — deferred because delegate system failed and these require significant new code (old s6_pipeline.py NLI port + new function design). |
| **Proposed Fix** | Port `nli_entailment()` function from old project's `tools/s6_pipeline.py` (lines 27-44). Replace `embedding_similarity_check()` with `nli_entailment_check()` that: 1) loads roberta-large-mnli pipeline, 2) compares FB definition against verbatim evidence_passages (not source_principles), 3) returns FAIL on CONTRADICTION, FLAG on NEUTRAL, PASS on ENTAILMENT with score ≥0.6. |
| **Source** | D2093, D2101, D2104. Cross-examination of actual stage5_verify.py. |
| **Status** | ✅ FIXED (D2113) — `nli_evidence_check()` with DeBERTa NLI replaces `embedding_similarity_check()`. |


### BUG-038: pipeline_config.yaml Pointed to Deleted Models
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | `config/pipeline_config.yaml` |
| **Symptom** | `models.generator.model: Qwen3.6-35B-A3B-OptiQ-4bit` (DELETED). `models.verifier.model: Phi-4-mini-instruct-4bit` (DELETED). Pipeline would crash on Stage 2 with model-not-found. |
| **Root Cause** | Model deletions (2026-07-22) were not synced to pipeline_config.yaml. pipeline_paths.py reads model names from this file. |
| **Proposed Fix** | Update to live models: generator → Qwen3.6-35B-A3B-4bit, verifier → Phi-4-mini-instruct-8bit. Add verifier_v2 → gemma-4-E4B-it-MLX-4bit. |
| **Source** | 2026-07-23 audit (governance cross-examination) |
| **Status** | ✅ RESOLVED — Fixed in same session. pipeline_config.yaml, pipeline_paths.py, model_assignments.yaml all updated. |

---

## 2026-07-23 — Gate-Fix Sprint (D2080-D2086) — Threat Assessment

### FIXED (v2.2)

| Bug ID | Severity | File | Symptom | Root Cause | Fix |
|--------|----------|------|---------|-----------|-----|
| D2080-B1 | 🔴 HIGH | stage3_cluster.py:101 | Clusters collapsed, principles lumped together | UMAP min_dist=0.0 forces all points into tight balls | min_dist=0.1 (configurable) |
| D2080-B2 | 🔴 HIGH | stage3_cluster.py:187 | Valid single-source principles silently lost | `continue` on noise label=-1 discards principles | Keep noise, write to cluster_noise.jsonl |
| D2080-B3 | 🟡 MED | stage3_cluster.py:196 | Centroid selection wrong for cosine space | Raw dot product on cosine-reduced embeddings | Normalize vectors before centroid |
| D2080-B4 | 🟡 MED | stage2_extract.py:409-412 | source_book="" → empty source_books → BORP fail | Fragile prefix match on LLM-returned segment_id | Exact match first, prefix fallback |
| D2080-B5 | 🟡 MED | stage2_extract.py:309-347 | Resume: in-run dedup partially broken | MinHash LSH not rebuilt from checkpoint | Rebuild LSH on resume |
| D2080-B6 | 🟡 MED | stage2_extract.py:452-460 | .segids and checkpoint desync on crash | Two-file write not atomic | Atomic tempfile→fsync→replace for .segids |
| D2080-B8 | 🟡 MED | stage2_extract.py:371-373 | Segments silently lost on OMLX failure | `except Exception: continue` | Retry once (configurable), log skipped IDs |

### OBSERVED (v2.2 — accepted)

| ID | Severity | Description | Why Accepted |
|----|----------|-------------|-------------|
| D2080-O1 | 🟢 LOW | Resume: partial batches re-sent entirely to LLM | Gate makes re-extraction cheap; partially-processed batches are rare |
| D2080-O2 | 🟢 LOW | Golden set has no version tracking | Not critical for v2.2; repo commit hash provides implicit tracking |
| D2080-O3 | 🟢 LOW | gate_basis values are opaque (a/b/c) | Documented in SYSTEM_PROMPT; self-documenting in JSON output |

### DEFERRED TO v3.0

| ID | Severity | Description | Decision |
|----|----------|-------------|----------|
| D2084-D1 | 🟡 MED | PI/TI/GE/PT not committed to DB | D2084 |
| D2084-D2 | 🟡 MED | Orphan PIs without parent PT links | D2084 |
| D2084-D3 | 🟡 MED | Growth edge quarantine no promotion | MTR |

---

## BUG-056: False Embedding-Speed Claim in stage1_5_fastembed.py
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (misleads future runs; could waste 9h on wrong route) |
| **Discovered** | 2026-08-03 — measured benchmark (2,000-seg sample, M1 Max) |
| **Symptom** | Docstring claims "~5 min" for 289K embeddings (D2127r4). Measured reality: **564 min** (9.4h) with default CPU ONNX. CoreML provider gives no speedup (9 seg/s). |
| **Root Cause** | Claim never benchmarked on this hardware before logging. |
| **Impact** | Any session trusting D2127r4 loses ~9h. |
| **Fix** | D2131 — update docstring with measured numbers; verified fastest route is sentence-transformers bge-small on MPS (45 seg/s, 106 min). |
| **Status** | 🟡 OPEN → tracked as D2131 |

## BUG-057: 16 Books Missing from Chunked Corpus (906/922)
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (silent corpus gap: 98.3% coverage, 1.7% missing with no error) |
| **Discovered** | 2026-08-03 — cross-check config books vs stage1_chunk/latest |
| **Symptom** | 16 MD files exist in `knowledge pipeline/books/` but produce zero segments. 12 have valid content (165KB–1MB); 4 are 0KB corrupt (`Mueller-Brockmann_Grid_Systems`, `Build a Multi-Agent System (MEAP)`, `Domain-Specific SLMs (MEAP)`, `Prompt Engineering for AI Systems (MEAP)`). |
| **Root Cause** | Stage 1 chunking run interrupted (memory hang) or per-file errors silently skipped. |
| **Impact** | Books like *Blink*, *Thinking with Type*, *Grid Systems* absent from knowledge base. |
| **Fix** | D2130 — re-chunk the 12 valid books; quarantine the 4 zero-byte files (source EPUBs/PDFs no longer on disk — 0 found — unrecoverable without re-acquisition). |
| **Status** | 🟡 OPEN → tracked as D2130 |

## BUG-058: Silent Classification Fallback to "emerging" on LLM Error
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (silent corruption of classification metrics — C16 violation) |
| **Discovered** | 2026-08-03 — code inspection stage4_merge.py L845-857 |
| **Symptom** | Any OMLX/classify exception in Stage 4 silently produces `{"discipline": "emerging", "domains": ["emerging"], ...}` with no log. 45% of 77-FB run mapped to `emerging` (35/77) — part genuine taxonomy gaps, part potentially silent LLM errors, indistinguishable today. |
| **Root Cause** | `except Exception: class_data = {...emerging...}` without logging (L851). |
| **Impact** | Misclassification is invisible; quality gates can't distinguish taxonomy-gap from classifier-failure. |
| **Fix** | D2134 — log warning + set `classification_errors` field, count failures in summary. |
| **Status** | 🟡 OPEN → tracked as D2134 |

---

## BUG-059: pipeline/embeddings.py Missing — Semantic Relationship Edges Silent
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (silent data loss — semantic_near edges never computed) |
| **Discovered** | 2026-08-04 — Q3 audit of full_run_streaming.py |
| **Symptom** | `stage4_merge.py:618` imports `embed_texts_bge_m3` from `pipeline.embeddings` which did NOT exist anywhere in the repo. The try/except silently degraded `compute_fb_relationships()` to domain/discipline/source edges only. The 77-FB run's `related_fbs` had NO semantic similarity edges, and no error was ever surfaced (C16 violation). |
| **Root Cause** | Embeddings module deleted/lost before D2118; import wrapped in try/except so the absence was invisible. |
| **Impact** | Graph foundation (LightRAG) missing semantic edges; near-duplicate FBs across books never linked. |
| **Fix** | D2136 — created `pipeline/embeddings.py` with `embed_texts_bge_m3()` (Ollama bge-m3, config-driven, normalized output). Verified: semantic_near edges now emitted (test: 3 FBs → 1 semantic edge). |
| **Status** | ✅ FIXED (2026-08-04, D2136) |

---

## BUG-060: mlx_provider.py Unusable - 501s Load + 556s Unconstrained Generation
| Field | Value |
|-------|-------|
| **Severity** | ORANGE HIGH (D2055 dead code - direct-MLX path broken) |
| **Discovered** | 2026-08-04 - measured benchmark (M1 Max, mlx-community/Phi-4-mini-instruct-8bit) |
| **Symptom** | MLXInferenceProvider.generate_json() -> first-use load 501s (re-downloads 12 files from HF despite cache) + single classify call 556s producing an open-ended essay, NOT the requested JSON (outlines constraint not applied). vs OMLX same model: 1.6s for identical call. |
| **Root Cause** | 1) Model cache miss (weights not in the HF cache the provider reads) -> 8+ min download on first use. 2) Outlines/JSON-schema path not constraining output - model rambles. 3) Generation defaults unverified. |
| **Impact** | Direct-MLX (D2055 speculative decoding / KV cache / outlines) is 0% used AND currently unusable. Pipeline is 100% OMLX HTTP. Any plan relying on mlx_provider would take ~9 min per call today. |
| **Fix plan** | Debug separately: verify HF cache path, cap max_tokens, unit-test outlines constraint, then benchmark speculative decoding (draft Qwen2.5-0.5B IS cached - confirmed). Deferred - OMLX is the proven path for the hybrid run. |
| **Status** | YELLOW OPEN - deferred (OMLX stays primary) |

---

## CROSS-EXAMINATION SESSION — 5 CRITICAL BUGS (2026-08-05)
> **Source:** Cross-examination of 7 external LLM evaluations against actual pipeline source code.
> **Verified:** All 5 bugs confirmed via code inspection. Stage 2 has NOT been run on full corpus yet.

### BUG-060: NLI Input Format Wrong — Stage 5 Verification Produces Random Results 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (verification layer is non-functional) |
| **File** | `pipeline/stage5_verify.py`, line 136 |
| **Symptom** | `nli(f"{source} </s></s> {claim}")` — single concatenated string. Pipeline tokenizes as ONE sequence (all token_type_ids=0). Model trained on premise/hypothesis PAIRS cannot distinguish them. |
| **Root Cause** | transformers text-classification pipeline requires `{"text": premise, "text_pair": hypothesis}` dict format for pair tokenization. Single string = single sequence. |
| **Fix** | Change to `nli({"text": source, "text_pair": claim})`. Add `.upper()` for label casing normalization. |
| **Status** | ✅ FIXED (2026-08-05) — D2151. Must fix before any production run. |

### BUG-061: MinHash Dedup Disabled — `_jaccard` Key Never Populated 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (near-duplicate detection bypassed) |
| **File** | `pipeline/stage2_extract.py`, lines 396-408, 758-765 |
| **Symptom** | `minhash_cache.get("_jaccard", lambda a, b: 0)(sig, prev_sig) > 0.9` — `_jaccard` key never populated. Lambda returns 0, 0 > 0.9 = False always. Dedup disabled. |
| **Root Cause** | `minhash_cache` only stores `sig → text` mappings at line 406. The function-call-through-cache pattern was never completed. |
| **Fix** | Use actual `datasketch.MinHash` objects with `.jaccard()` method. Create MinHash from signature texts. |
| **Status** | ✅ FIXED (2026-08-05) — D2152. Must fix before any production run. |

### BUG-062: Dead Code in run_stage2() — NameError on start/result/is_summary/name 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (pipeline crash) |
| **File** | `pipeline/stage2_extract.py`, lines 781-786 |
| **Symptom** | Lines 781-786 are dedented to run_stage2() scope (OUTSIDE for future loop) but reference `start`, `result`, `is_summary`, `name` — all undefined at that scope. Would crash with NameError. |
| **Root Cause** | Copy-paste residue from _process_cluster() function. Lines were never removed during refactor. |
| **Fix** | Remove lines 781-786. Logo is already handled inside the loop. |
| **Status** | ✅ FIXED (2026-08-05) — D2153. |

### BUG-063: Incremental Checkpoint Broken — Index Out of Scope, Writes Only Once 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (no crash-resume safety) |
| **File** | `pipeline/stage2_extract.py`, line 787 |
| **Symptom** | `if i % 5 == 0 or i == len(target_clusters)` is OUTSIDE for future loop. Checkpoint writes only once after all clusters complete. Intended "every 5 clusters" never triggers. |
| **Root Cause** | `i` from enumerate() scope used at wrong indentation level. |
| **Fix** | Move checkpoint write INSIDE for future loop, use `completed` counter. |
| **Status** | ✅ FIXED (2026-08-05) — D2154. |

### BUG-064: Three NLI Thresholds Hardcoded, Config Has One — C12 Violation 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (config drift, verification semantics undefined) |
| **File** | `pipeline/stage5_verify.py`, lines 430-460 |
| **Symptom** | Config: `nli_entailment_threshold: 0.6`. Runtime: >=0.8→PASS, >=0.5→FLAG, <0.5→FAIL. Three thresholds, different semantics. |
| **Root Cause** | Thresholds hardcoded in code, not read from config. |
| **Fix** | Add nli_pass_threshold, nli_marginal_threshold to config. Read at runtime. |
| **Status** | ✅ FIXED (2026-08-05) — D2155. |


---

### BUG-065: Union-Find Transitive Chaining — Mathematical Illusion in R-NN Clustering 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (silent cluster corruption — merges distinct semantic groups) |
| **Discovered** | 2026-08-05 — cross-examination of 7 external LLM evaluations |
| **File** | `pipeline/stage1_5_embed_cluster.py`, lines 247-279 |
| **Symptom** | Documentation claimed "R-NN eliminates the transitive bridge effect." Mathematically false: R-NN constrains edge creation (reciprocal only), but Union-Find computes connected components. If A↔B and B↔C are reciprocal, Union-Find merges A,B,C into one cluster — A and C may be semantically unrelated. Stress test: 2 groups of 150 nodes with 5 bridge edges → Union-Find merges all 300 into 1 component. |
| **Root Cause** | Union-Find finds connected components on R-NN edge graph. Transitive chaining is still 100% active. |
| **Fix** | D2168: Replace Union-Find with Louvain community detection (networkx). Louvain optimizes modularity — dense intra-community, sparse inter-community — naturally splitting chains at semantic boundaries. Same stress test: Louvain yields 4 communities with 100% purity. |
| **Status** | ✅ FIXED (2026-08-05) — D2168. |

### BUG-066: Zero-Padding Embedding Corruption — Latent Data Time-Bomb 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (silent geometry corruption if config-model mismatch) |
| **Discovered** | 2026-08-05 — cross-examination (Qwen, ChatGPT identified) |
| **File** | `pipeline/stage1_5_embed_cluster.py`, lines 140-142 (REMOVED) |
| **Symptom** | If embedding model outputs 384d but config expects 1024d, code padded last 640 dims with synthetic zeros. FAISS cosine geometry corrupted. Config was unified in D2156 but the padding hack remained as a latent time-bomb. |
| **Root Cause** | Defensive padding instead of fail-fast assertion. Violated C16. |
| **Fix** | D2170: Replace zero-padding with `ValueError` assertion. Pipeline now fails with clear message: "dimension mismatch: model output Xd ≠ config S15_EMBED_DIM=Yd". |
| **Status** | ✅ FIXED (2026-08-05) — D2170. |

### BUG-067: Segment-Embedding Index Misalignment — Silent Data Corruption 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (cluster membership becomes random on batch failure) |
| **Discovered** | 2026-08-05 — cross-examination (ChatGPT, Qwen, Kimi all identified) |
| **File** | `pipeline/stage1_5_embed_cluster.py`, Ollama fallback path |
| **Symptom** | When Ollama batch fails, `results[idx] = []` drops embeddings but does NOT filter the segments list. Subsequent clustering assumes `embedding[i] ↔ segments[i]`. After a failure, index `i` points to the wrong segment. Cluster labeled "Book A" may contain segments from "Book B." |
| **Root Cause** | Anonymous matrix indexing with no stable segment_id mapping. |
| **Fix** | D2172: Track `successful_indices` in lockstep with embeddings. Filter `segments = [segments[i] for i in successful_indices]` after embedding. |
| **Status** | ✅ FIXED (2026-08-05) — D2172. |

### BUG-068: Singletons Marked is_noise=True — Silent Knowledge Deletion 🔴
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (2,804 unique insights at risk of deletion) |
| **Discovered** | 2026-08-05 — unanimous across all 7 evaluations |
| **File** | `pipeline/stage1_5_embed_cluster.py`, line 390 (original) |
| **Symptom** | All 2,804 singletons stamped with `is_noise: True`. Any downstream filter or retrieval query respecting this flag silently drops unique, book-specific knowledge. |
| **Root Cause** | Legacy labeling conflated "single-source" with "noise." |
| **Fix** | D2171: `is_noise: False, is_singleton: True`. Preserves structural distinction without data loss. |
| **Status** | ✅ FIXED (2026-08-05) — D2171. |

### BUG-069: D2163 Discovery Probe — Positional Sampling Blind Spot 🟠
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (probe misses distinct principles, fails to split mixed clusters) |
| **Discovered** | 2026-08-05 — cross-examination (ChatGPT identified) |
| **File** | `pipeline/stage2_extract.py`, `discover_principles()` function |
| **Symptom** | Probe sampled 12 segments positionally (seg[0], seg[step], seg[2*step]...). If Principle A dominates first half and Principle B second half, probe may only see A, return count=1, and fail to split. |
| **Root Cause** | No source-book stratification in probe sampling (unlike D2161 which already stratifies extraction). |
| **Fix** | D2173: Source-stratified round-robin sampling across all books. Max 15 samples, max 2 per book. Ensures every book is represented in the probe. |
| **Status** | ✅ FIXED (2026-08-05) — D2173. |

### BUG-070: Version Schizophrenia — 5 Files, 3 Different Versions 🟠
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (non-reproducible runs) |
| **Discovered** | 2026-08-05 — cross-examination (Kimi eval4, ChatGPT identified) |
| **File** | CONSTITUTION.md (v3.0), requirements.txt (v3.0), stage6_commit.py (default "2.0"), query.py (banner "v2.0"), pipeline_config.yaml (schema 2.2) |
| **Symptom** | For a system stamping every record with `schema_version`, you cannot know which version produced which run. |
| **Root Cause** | No single source of truth for versioning. Each file independently declared its version. |
| **Fix** | D2169: Created `config/version.yaml` as single source of truth. stage6_commit.py reads `pipeline_version` from it. query.py reads `query_banner_version`. All future version bumps happen in one file. |
| **Status** | ✅ FIXED (2026-08-05) — D2169. |

### BUG-071: Dead Stage 3 Config — Ghost Configuration Risk 🟡
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (future maintainer may edit dead config believing it's active) |
| **Discovered** | 2026-08-05 — cross-examination (ChatGPT identified) |
| **File** | `pipeline/pipeline_paths.py` (lines 111-118), `config/pipeline_config.yaml` (lines 17-18, 129-137) |
| **Symptom** | Stage 3 (HDBSCAN) removed via D2120 but config still loaded S3_UMAP_*, S3_ALLOW_SINGLE_CLUSTER, etc. from pipeline_config.yaml. Ghost configuration risk. |
| **Root Cause** | Config cleanup deferred after architectural change. |
| **Fix** | D2174: Replaced live config reads with hardcoded NO-OP defaults (prevent import errors in legacy scripts). Removed stage3 section from pipeline_config.yaml. |
| **Status** | ✅ FIXED (2026-08-05) — D2174. |

### BUG-072: Hardcoded 'knowledge pipeline' Paths — C12a Violation 🟡
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (fragile paths with literal spaces, constitutional violation) |
| **Discovered** | 2026-08-05 — cross-examination (Qwen eval4 identified) |
| **File** | `pipeline/metrics.py:11`, `pipeline/reliability.py:22`, `pipeline/run_monitor.py:35,88` |
| **Symptom** | Literal string `"knowledge pipeline"` with space hardcoded in 4 locations. Fragile for shell scripting and violates C12a. |
| **Root Cause** | No central path constant. Each file independently constructed paths. |
| **Fix** | D2175: All 4 locations now use `DATA_DIR` from `pipeline_paths.py`. Centralized path resolution. |
| **Status** | ✅ FIXED (2026-08-05) — D2175. |


## BUG-059 — 2026-08-07 20:27 — N2 crash: NameError S2_MAX_WORKERS at extraction start
- **Symptom:** Probe completed (99.7%, 565 splits, +1,209 expected FBs) then `NameError: name 'S2_MAX_WORKERS' is not defined` at stage2_extract L1167 → N2 died; 2h39m probe results lost (in-memory only).
- **Root cause:** S2_MAX_WORKERS defined in pipeline_paths.py L131 and used at stage2_extract L1167, but never added to the `from pipeline.pipeline_paths import (...)` list (commit 107b1c3).
- **Impact:** Probe results lost; full restart required.
- **Status:** ✅ FIXED (import added). End-to-end preflight (real corpus, mocked LLM) proves L1167 executes.
- **Prevention:** Probe phase now persisted to probe_targets.jsonl (STAGE2_PROBE_CACHE) — crash-resumable.

## BUG-060 — 2026-08-07 20:45 — `--only-convergent` silently defeated by probe block
- **Symptom:** Run log showed `Total extraction targets: 14173 (was 12964)` under `--only-convergent` — all 10,330 single-source clusters were being added to extraction.
- **Root cause:** Probe block ran `expanded_targets.extend(single_source)` unconditionally (stage2_extract L967), overriding the only_convergent filter.
- **Impact:** N2 would have processed 14,173 targets (~23h+) instead of convergent-only (~3,200).
- **Status:** ✅ FIXED (`if not only_convergent:` guard). Preflight proves targets=2,634, not 14,173.
- **Prevention:** end-to-end preflight (real corpus + mocked LLM) is now the launch gate.

*Updated: 2026-08-07 (N2 crash audit) | Bugs tracked: 52 | Resolved: 45 | Closed (moot): 5 | Open: 2 | Schema version: 1.8*
<!-- BUG-005/006 resolved (P0.1/P0.3 fixes already in code), BUG-007/008/009 closed (Stage 3/HDBSCAN/PCA/nomic all removed), BUG-010 resolved (config actively used) -->

## BUG-061 — 2026-08-10 — C16 Violation: n2_watchdog.py Silent Exception Swallowing
- **Symptom:** `integrity_check.py` check #15 flagged `n2_watchdog.py:85: except Exception: pass` — bare except silently swallowing all errors (C16 violation).
- **Root cause:** Checkpoint line-count read wrapped in `except Exception: pass` — if the checkpoint file was corrupted or inaccessible, the watchdog would silently report 0 lines without logging the error.
- **Impact:** Watchdog could report misleading checkpoint state during N2 runs. Non-critical (watchdog is monitoring, not pipeline logic).
- **Fix:** D2226 — Log error to stderr with descriptive message. Don't raise (watchdog is monitoring — a checkpoint read failure shouldn't crash the watchdog). 
- **Status:** ✅ FIXED (2026-08-10) — D2226.
- **Files:** `pipeline/n2_watchdog.py:85`

## BUG-062 — 2026-08-10 — Merged S4 Phi-4-mini Depth Over-Assignment (95% cross-domain)
- **Symptom:** 20-FB live test with `MAXWELL_MERGED_S4=1` classified 19/20 FBs as `cross-domain`, 1 as `domain`, 0 as `universal`, 0 as `specialized`. Disciplines show inconsistent casing (`Cognitive Psychology` vs `Cognitive psychology`).
- **Root cause:** Phi-4-mini-3.8B is underpowered for 10-field JSON output including semantic depth classification (Kimi audit prediction confirmed). The model defaults to `cross-domain` as a safe middle-ground when it cannot discriminate depth levels reliably.
- **Impact:** If merged call becomes default, all FBs will be shallowly classified as `cross-domain` — depth signal lost. Pipeline S5 verification would proceed on misclassified FBs.
- **Mitigation (D2226):** Merged call kept as opt-in (`MAXWELL_MERGED_S4=1`). Default remains two-call path (CRIBS from Qwen3-35B + Classify from Phi-4-mini, now with mechanism fed to classifier). Recommendation: upgrade S4 classifier to Qwen3-8B or stronger model before making merged call the default.
- **Status:** ✅ RESOLVED (2026-08-12) — S4 classify model is `gpt-oss-20b-MXFP4-Q8` (config `models.verifier.model` → `VERIFY_MODEL`), NOT Phi-4-mini. Depth is LLM-classified semantically (D2220) via focused depth prompt (D2247). Merged call remains opt-in (D2226). BUG-062 root cause (Phi-4-mini depth over-assignment) no longer applies.

*Updated: 2026-08-10 (D2226 audit) | Bugs tracked: 54 | Resolved: 46 | Closed (moot): 5 | Open: 3 | Schema version: 1.9*

## BUG-063 — 2026-08-10 — delegate() Cannot Execute File System Tasks (Root Cause) 🔴
- **Symptom:** `delegate({provider: "maxwell_omlx", model: "..."})` fails for any task requiring project file access. Attempt 1: gemma-4-E4B returned 404 (model not loaded). Attempt 2: Qwen3-Coder-30B-A3B executed TypeScript code in Deno sandbox that couldn't access project files. Regular occurrence across sessions — "local LLMs useless for delegated tasks."
- **Root cause:** The `delegate()` function routes ALL providers through `execute_typescript` (Deno/TypeScript sandbox). The `provider` parameter changes which LLM generates the TypeScript code, but the code always executes in the sandbox. The sandbox has NO filesystem access to the project directory — it can only use registered SDK functions. For file analysis, code modifications, or any task requiring `fs` or `Deno.readTextFile`, the sandbox fails silently.
- **Impact:** Delegate is unusable for: (1) file analysis of project code, (2) YAML validation against project files, (3) pipeline code modifications, (4) any task requiring project context beyond the delegate's instructions text. Effectively reduces delegate to a chat interface with no tool access — equivalent to a simple LLM call with no grounding in project state.
- **Workaround:** Use `shell()` + `curl` to OMLX API for file analysis tasks. Pattern:
  ```bash
  curl -s http://localhost:11435/v1/chat/completions -d '{
    "model": "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit",
    "messages": [{"role": "user", "content": "...analyze these files..."}],
    "temperature": 0.0
  }'
  ```
- **Fix (D2344):** `pipeline/omlx_delegate.py` — `delegate_omlx()` function + CLI that runs in-process with REAL file access, reads the files you name (`--file`, repeatable), injects them as fenced context, and calls the local OMLX API via `pipeline.omlx_call.call_omlx` (or `call_omlx_json` with `--json`). Default model from config (`models.generator.model`); `--model` override. Verified end-to-end: `--file config/content_types.yaml` returned a correct file-grounded answer via gemma-4-E4B.
- **Status:** 🟢 FIXED (D2344, 2026-08-13) — the `delegate_omlx()` workaround is now a first-class CLI. The underlying `delegate()` sandbox limitation remains (goose framework), but it no longer blocks local-LLM file analysis — use `python3 pipeline/omlx_delegate.py` instead of `delegate()`.
- **Priority:** P1 — resolved by `pipeline/omlx_delegate.py`.

*Updated: 2026-08-10 (D2226 cleanup) | Bugs tracked: 55 | Resolved: 46 | Closed (moot): 5 | Open: 4 | Schema version: 1.10*

## BUG-064 — 2026-08-10 — S4 Field Pollution in All 37 Golden Positives (P0) 🔴
- **Symptom:** Every positive example (CONV-001 through CONV-040) contains S4 CRIBS enrichment fields inside `expected_fb`: `application`, `elaboration`, `procedural_skill`, `failure_mode`, `jargon`, `keywords`, `prerequisite_fbs`, `contradicts_fbs`, `related_fbs`, `evidence`.
- **Root cause:** Golden set was built by extracting the full FB record post-S4 enrichment instead of the S2-only output. No stage-boundary discipline was enforced during curation.
- **Impact:** DSPy fine-tuning would teach S2 to generate S4 enrichment fields — breaking the pipeline stage contract. S2 would hallucinate CRIBS enrichment, wasting tokens and creating expectation mismatch with S4.
- **Fix:** D2228 — Strip all S4 fields from expected_fb. Keep only S2 core fields. Create separate stage4_fewshot_enrichment.yaml for CRIBS training.
- **Status:** ✅ FIXED (D2228, 2026-08-13) — golden few-shot has 0 S4 enrichment fields (application/elaboration/jargon/failure_mode all absent)
- **Files:** `config/golden/stage2_fewshot_convergent.yaml`

## BUG-065 — 2026-08-10 — sqlite-vec Dimension Mismatch: 1024 vs 512 (P0) 🔴
- **Symptom:** `stage6_commit.py:146` creates vector table as `float[1024]`. `pipeline_paths.py:203` reads `embed_dim: 512` from config (bge-m3 Matryoshka, D2181).
- **Root cause:** Schema was written when embeddings were 1024-dim. D2181 reduced to 512-dim Matryoshka but the CREATE TABLE statement was never updated.
- **Impact:** `insert_embedding()` packs a 512-float blob into a 1024-float column. sqlite-vec will reject or silently corrupt. Vector search is broken at commit time.
- **Fix:** D2229 — Change `float[1024]` to `float[512]`, read `S15_EMBED_DIM` from config at schema creation.
- **Status:** ✅ FIXED (D2229, 2026-08-13) — stage6 uses float[{S15_EMBED_DIM}] (no hardcoded 1024)
- **Files:** `pipeline/stage6_commit.py:146`

## BUG-066 — 2026-08-10 — Golden Evidence Passages Are Paraphrases, Not Exact Source Spans (P0) 🔴
- **Symptom:** 19+ sampled evidence passages do NOT match any `cluster_segment.text` exactly. Example: CONV-001 passages are short excerpts like "when the decoy was present, 84% chose Print+Web" rather than the original Ariely segment text.
- **Root cause:** Evidence was manually curated from memory/paraphrase of source segments rather than copy-pasted from the canonical segment text.
- **Impact:** S2 learns "semantically relevant excerpts" rather than "exact source-grounded evidence." Creates evidence hallucination/paraphrase acceptance leak: S2 synthesizes claim → short fragment appears supportive → S5 NLI passes on fragment → FB accepted even though full segment doesn't establish the claim.
- **Fix:** D2230 — Verify all 60 examples against cluster_segments. Add source_book, segment_id, char_start, char_end, sha256 to each passage.
- **Status:** ✅ FIXED (D2230, 2026-08-13) — 177 source_book/segment_id/char_start/char_end/sha256 span fields present in golden
- **Files:** `config/golden/stage2_fewshot_convergent.yaml`

## BUG-067 — 2026-08-10 — Stage 2 Convergence Routing via Source Count Alone (P0) 🔴
- **Symptom:** `stage2_extract.py:1209`: `if is_conv or book_count >= 2:` triggers convergent extraction on ANY cluster with 2+ books, regardless of mechanism convergence.
- **Root cause:** The `book_count >= 2` clause was a heuristic shortcut. It bypasses the convergence gate (which should verify that different sources describe the SAME mechanism, not just the same topic).
- **Impact:** False convergence — two books discussing similar topics with different mechanisms get merged into a single FB. The golden negatives explicitly teach that source diversity ≠ convergence, but the code doesn't enforce this.
- **Fix:** D2231-P0-5 — Require explicit `is_conv` gate or mechanism-similarity check. Source count alone must not trigger convergent extraction.
- **Status:** ✅ FIXED (D2231, 2026-08-13) — stage2:1276 'Removed or book_count >= 2'; is_convergent gate only
- **Files:** `pipeline/stage2_extract.py:1209`

## BUG-068 — 2026-08-10 — 6 Locations Hardcode Thresholds Bypassing Config (P0 C12 Violation) 🔴
- **Symptom:** Thresholds hardcoded at module level in 6 files, bypassing `config/pipeline_config.yaml`:
  - `reliability.py`: `STABLE_THRESHOLD=0.85`, `WATCH_THRESHOLD=0.50`, `GARBAGE_THRESHOLD=0.20`
  - `stage4_merge.py`: `threshold=0.92` (dedup), `similarity_threshold=0.80` (semantic near)
  - `principle_index.py`: `MINHASH_THRESHOLD=0.90`
  - `taxonomy_manager.py`: `FLOOD_THRESHOLD_RATIO=0.20`, `REPLACEMENT_THRESHOLD_RATIO=1.1`, `EMERGING_FREQ_THRESHOLD=10`
  - `retrieve.py`: argparse default `0.85` for confidence threshold
- **Root cause:** C12 governance not enforced at code review. Thresholds were added inline without config entries.
- **Impact:** Any attempt to tune these thresholds via `pipeline_config.yaml` is silently ignored. System is not config-driven as Constitution requires.
- **Fix:** D2231-P0-6 — Move all to `pipeline_config.yaml`, read via `pipeline_paths.py`.
- **Status:** ✅ FIXED (D2231-P0-6, 2026-08-13) — all 6 thresholds read from config via pipeline_paths
- **Files:** `pipeline/reliability.py`, `pipeline/stage4_merge.py`, `pipeline/principle_index.py`, `pipeline/taxonomy_manager.py`, `pipeline/retrieve.py`, `config/pipeline_config.yaml`, `pipeline/pipeline_paths.py`

## BUG-069 — 2026-08-10 — GoldenFB Schema Missing extraction_type Field (P0) 🔴
- **Symptom:** `GoldenFB` Pydantic model at `schemas.py:915` has no `extraction_type` field. The golden set YAML includes `extraction_type` in `expected_fb`, but DSPy compilation via Pydantic validation would drop this field.
- **Root cause:** `GoldenFB` was designed post-S4 (including CRIBS fields like application, jargon, etc.) but never updated when `extraction_type` was added to the golden set for S2 training.
- **Impact:** DSPy loses the extraction_type training signal. Model cannot learn to distinguish causal_mechanism from descriptive_model from normative_heuristic from empirical_pattern.
- **Fix:** D2231-P0-4 — Add `extraction_type: str = ""` to `GoldenFB`.
- **Status:** ✅ FIXED (D2231-P0-4, 2026-08-13) — GoldenFB has extraction_type: str = '' (schemas.py:925)
- **Files:** `pipeline/schemas.py:915`

## BUG-070 — 2026-08-10 — NLI Config-Code Docstring Inversion (P1) 🔴
- **Symptom:** `config/pipeline_config.yaml` has DeBERTa as `nli_model` (primary) and ModernBERT as `nli_model_fallback`. But `stage5_verify.py:76-77` docstring claims "Primary: ModernBERT-base-nli ... Fallback: DeBERTa-v3-base-mnli-fever-anli." The CODE follows config order (DeBERTa primary at runtime), but the DOCSTRING says the opposite.
- **Root cause:** D2119 decision switched primary to ModernBERT for speed. Config was supposed to be updated but wasn't (still has DeBERTa first). Code docstring was updated to reflect D2119 intent but config wasn't aligned.
- **Impact:** Runtime uses DeBERTa (slower, 512 ctx) when D2119 intended ModernBERT (faster, 8192 ctx). Documentation ≠ behavior.
- **Fix:** D2232-P1-3 — Either update config to make ModernBERT primary OR update docstring to match config. Align all three sources.
- **Status:** ✅ FIXED (D2232-P1-3, 2026-08-13) — stage5 docstring + pipeline_paths say DeBERTa primary (D2298)
- **Files:** `config/pipeline_config.yaml`, `pipeline/stage5_verify.py`

## BUG-071 — 2026-08-10 — NLI Fallback Defaults Landmine (P1) 🔴
- **Symptom:** `pipeline_paths.py:160-162` has fallback defaults of `nli_entailment_threshold: 0.6`, `nli_pass_threshold: 0.8`, `nli_marginal_threshold: 0.5`. Config has `0.5, 0.6, 0.3`. If `_CFG` loading silently fails or key is renamed, thresholds revert to pre-D2226 broken values.
- **Root cause:** D2226 fixed the hardcoded thresholds in `stage5_verify.py` but didn't update the fallback defaults in `pipeline_paths.py`. The defaults are the OLD values, not the config values.
- **Impact:** Silent regression — if config key disappears, NLI reverts to 0.8 pass threshold, dramatically increasing false escalation rate.
- **Fix:** D2232-P1-4 — Set fallback defaults to match config values (0.6/0.5/0.3). Add runtime assertion that loaded values match config.
- **Status:** ✅ FIXED (D2232-P1-4, 2026-08-13) — NLI fallback defaults now 0.5/0.6/0.3 (match config)
- **Files:** `pipeline/pipeline_paths.py:160-162`

## BUG-072 — 2026-08-10 — Taxonomy Version Triple Drift (P1) 🔴
- **Symptom:** `config/version.yaml` (SSoT per D2169): `taxonomy_version: "v5.0"`. `config/taxonomy_v5.yaml`: `version: v5.1`, `classification_version: v5.0.1`. Three different version strings for the same artifact.
- **Root cause:** Taxonomy was independently versioned (bumped to v5.1 during edits) but version.yaml (single source of truth) was never updated.
- **Impact:** Version gate in runner.py would fail. Provenance stamps lie. Human reviewers can't tell which taxonomy is canonical.
- **Fix:** D2232-P1-5 — Align all to single version. Update version.yaml to v5.1 or roll taxonomy back.
- **Status:** ✅ FIXED (D2232-P1-5, 2026-08-13) — version.yaml v5.1 == taxonomy_v5.yaml v5.1
- **Files:** `config/version.yaml`, `config/taxonomy_v5.yaml`

## BUG-073 — 2026-08-10 — CONV-035 and CONV-037 Likely False Convergence (P1) 🔴
- **Symptom:** 
  - CONV-035 combines Clear's habit stacking + Cialdini's commitment/consistency → "cue automation + consistency drive." These are two different behavioral mechanisms that can coexist, not a single shared causal structure.
  - CONV-037 combines Dunbar's ~150 relationship limit + availability heuristic → "Cognitive Capacity Ceiling." These are distinct cognitive phenomena (social network constraint vs judgment bias), not a shared mechanism.
- **Root cause:** Attractive synthesis was mistaken for genuine mechanism convergence. The examples were curated to fill extraction-type diversity targets without rigorous convergence validation.
- **Impact:** Golden set teaches S2 that topical/conceptual similarity is sufficient for convergence — exactly what the negative set says to reject.
- **Fix:** D2232-P1-7 — Reclassify as `is_convergent: false` or strengthen mechanism evidence with explicit shared causal structure. If neither source describes the other's mechanism, they don't converge.
- **Status:** ✅ FIXED (D2232-P1-7, 2026-08-13) — CONV-035/037 now is_convergent:false with rationale
- **Files:** `config/golden/stage2_fewshot_convergent.yaml`

*Updated: 2026-08-10 (D2227 cross-examination) | Bugs tracked: 63 | Resolved: 46 | Closed (moot): 5 | Open: 12 | Schema version: 1.11*

### BUG-058: IOGPUMemory Kernel Panic — Dual GPU Clients (2026-08-10) 🔴 MITIGATED
**Symptom:** `panic: "completeMemory() prepare count underflow" @IOGPUMemory.cpp:492`
**Trigger:** mlx_lm direct-load of Gemma-4-31B-8bit (31GB) while OMLX served
Qwen3-Coder-30B + Phi-4-mini (~50GB combined GPU commit on 64GB unified memory).
**Root cause:** Two concurrent Metal GPU allocators (mlx_lm + OMLX) under memory
pressure → Apple IOGPUFamily memory prepare count underflow.
**Fix:** OMLX-only serving. Never direct-load via mlx_lm while OMLX runs.
**Status:** ✅ MITIGATED (D2243). Verified OMLX loads Gemma-31B safely with eviction.

### BUG-074 — 2026-08-10 — GPT-OSS-20B Reasoning Mode Burns Tokens at max_tokens=512 (P1) ✅ RESOLVED
- **Symptom:** S4 classify calls with GPT-OSS-20B returned EMPTY content — all 512
  max_tokens consumed by `reasoning_content` (high-reasoning default mode).
- **Root cause:** GPT-OSS is a reasoning model (OpenAI GPT-OSS series). Default
  reasoning effort is HIGH; the long CLASSIFY_SYSTEM_PROMPT triggers extended
  chain-of-thought, exhausting the token budget before `content` starts.
- **Fix (D2247):** Prepend `Reasoning: none` to the system prompt → GPT-OSS
  classifies directly (25-40s/call vs 60-182s high-reasoning) and emits JSON in
  `content`. Also raise max_tokens 512 → ≥1024 for safety.
- **Impact:** S4 classify now reliable with GPT-OSS. Also improves latency 4-6×.
- **Status:** ✅ RESOLVED (D2249, 2026-08-10) — pipeline wired: `Reasoning: none` prefix
  prepended config-driven (`models.verifier.reasoning_off_prefix` + `reasoning_off_models`),
  max_tokens 512→1024 (`models.verifier.max_tokens`). Verified live: GPT-OSS returns
  content JSON in all warm calls; hardened `omlx_call.py` to retry missing-content
  (cold-reload race, C23).
- **Files:** `config/pipeline_config.yaml`, `pipeline/pipeline_paths.py`,
  `pipeline/stage4_merge.py`, `pipeline/stage4_merged_call.py`, `pipeline/omlx_call.py`

### BUG-075 — 2026-08-10 — Cross-Domain Depth 0% Across All S4 Models (P1) ✅ FIXED
- **Symptom:** Phi-4-mini, Gemma-4-31B, AND GPT-OSS-20B all score 0% (0/3) on
  cross-domain depth classification (the dominant class: 26/50 FBs = 52%).
- **Root cause:** Not model capability — prompt structure. The LONG combined
  classify prompt (discipline+domains+depth in one call) degrades all models
  (GPT-OSS: 62.5% short-prompt → 38% long-prompt). Few-shot anchors gave mixed
  A/B results (CONV-026 regressed).
- **Impact:** The most common depth class is systematically misclassified as
  "domain" — S4 depth accuracy is capped ~50-60% until resolved.
- **Fix candidates:** (1) Split depth into its own focused short-prompt call
  (proven 62.5%); (2) dedicated few-shot with structurally-matched anchors;
  (3) Reasoning:none prefix for reasoning models.
- **Status:** ✅ FIXED (D2249, 2026-08-10) — ROOT CAUSE CONFIRMED: prompt structure, not
  model. SHORT focused depth prompt (`classify_depth_focused` in stage4_merged_call.py)
  scores **87.5% (7/8)** vs 38-62.5% long combined prompt; **cross-domain 0/3 → 3/3**.
  Wired into stage4_merge.py Stage 3 (config-gated `stage4.depth_focused_classification`),
  overrides long-prompt depth with focused-call depth (+1 fast call/FB).
- **Files:** `pipeline/stage4_merged_call.py`, `pipeline/stage4_merge.py`,
  `config/pipeline_config.yaml`, `governance/s4_depth_benchmark_focused_prompt.json`

*Updated: 2026-08-10 (D2245-D2247 session) | Open: 14*

### BUG-076 — 2026-08-11 — S5 NLI Config Overrides D2216 DeBERTa FEVER Promotion (P1) 🔴 OPEN
- **Symptom:** D2216 (2026-08-09) promoted DeBERTa FEVER as primary S5 NLI in
  `pipeline/pipeline_paths.py`, citing "5.8× more discriminative than ModernBERT
  on convergent FBs." But `config/pipeline_config.yaml` line 172 hardcodes
  `nli_model: tasksource/ModernBERT-base-nli`. The pipeline_paths.py code reads
  config first: `_CFG.get("stage5", {}).get("nli_model", "DeBERTa...")` — config
  wins. DeBERTa FEVER promotion is dead code.
- **Root cause:** Config-driven architecture (C12) means code defaults only
  activate when config key is absent. D2216 changed the code default but didn't
  update the config YAML. Config override = ModernBERT runs at runtime.
- **Evidence:** `governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md` benchmarked
  DeBERTa FEVER on 5 convergent FBs: clear binary signal (0.88-0.98 PASS vs
  0.001 FAIL). ModernBERT/RoBERTa standard MNLI: everything NEUTRAL 0.18-0.32
  — cannot verify synthesized FBs. But test was only 5 FBs — not production
  calibration.
- **Impact:** S5 NLI pre-filter is running ModernBERT, which the project's own
  test doc says "CANNOT verify synthesized principles." This means every FB
  falls through NLI as NEUTRAL → escalates to Gemma-4-E4B deep check (which
  has 73% false-negative rate). Effectively: NLI is non-functional, Gemma is
  broken → S5 produces almost all QUARANTINE.
- **Fix candidates:** (1) Swap config `nli_model` to DeBERTa FEVER. (2) Run
  larger calibration (50-100 real FBs) before adopting. (3) If DeBERTa FEVER
  was intentionally demoted after the 5-FB test, document why.
- **Status:** ✅ FIXED (D2255, 2026-08-11) — Config swapped: DeBERTa FEVER primary, ModernBERT fallback.
- **Files:** `config/pipeline_config.yaml` L172, `pipeline/pipeline_paths.py` L163-168,
  `governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md`

### BUG-077 — 2026-08-11 — stage5_verify.py Docstring Triple-Stale (P2) 🟡 FIXED
- **Symptom:** stage5_verify.py docstring claimed: (1) "DeBERTa NLI entailment" — but
  config was running ModernBERT. (2) "Classifier: Phi-4-mini-8bit — Stage 4 Phase 2" —
  Phi retired from S4 (D2249/D2250). (3) "ModernBERT NLI pre-filter" in title — stale.
- **Root cause:** Docstring not updated when D2216 promoted DeBERTa FEVER, D2249
  swapped S4 classifier to GPT-OSS, and D2255 finally activated DeBERTa FEVER.
- **Fix:** D2256 (2026-08-11) — Docstring rewritten: title says DeBERTa FEVER, R5
  section shows all 4 active families, removed Phi-4-mini references.
- **Status:** ✅ FIXED
- **Files:** `pipeline/stage5_verify.py` docstring

### BUG-078 — 2026-08-11 — Stale classify_model in v2.3 Checkpoint Block (P3) 🟡 FIXED
- **Symptom:** `config/pipeline_config.yaml` L1642 contained `classify_model: Phi-4-mini-instruct-8bit`
  embedded in a v2.3 schema checkpoint configuration block.
- **Root cause:** Historical artifact — v2.3 full-run config checkpoint was preserved
  as reference but the classify_model line was never updated/annotated.
- **Fix:** D2258 (2026-08-11) — Removed stale line, added annotation explaining v2.3
  artifact status and that Phi-4-mini was retired (D2249/D2250).
- **Status:** ✅ FIXED
- **Files:** `config/pipeline_config.yaml` L1642

### BUG-079 — 2026-08-11 — HANDOFF_D2254 Claims Phi-4-mini for S5 verify/gates (P3) 🟡 FIXED
- **Symptom:** HANDOFF_D2254 model registry listed `Phi-4-mini-instruct-8bit` with role
  "S5 verify/gates" — but Phi-4-mini has NO pipeline config role in `config/pipeline_config.yaml`.
  Phi only appears in: `smoke.fast.fast_model` (test mode), `config/model_assignments.yaml`
  (agent roles, not pipeline).
- **Root cause:** Handoff propagated stale claim about Phi's role. Prior to D2249/D2250,
  Phi may have been planned for S5 but was never actually given a pipeline config role.
- **Fix:** D2260 (2026-08-11) — HANDOFF_D2254 model registry corrected. Phi-4-mini
  listed as non-pipeline (smoke test + agent assignments only). Active pipeline models
  verified against actual config.
- **Status:** ✅ FIXED
- **Files:** `governance/HANDOFF_D2254.md` §4

### BUG-080.1 — 2026-08-12 — _save_diag_state flush/fsync outside with block (C6 violation) 🔴 FIXED
- **Symptom:** `❌ S2 FAILED: I/O operation on closed file.` at diagnostic state save after S2 completed.
  State file left as `.tmp` (never atomically renamed). S4/S5 never ran — pipeline returned early.
- **Root cause:** `_save_diag_state()` in `pipeline/run_diagnostic.py` had `f.flush()` and
  `f.fsync()` OUTSIDE the `with open()` block. File already closed → ValueError. The C6
  crash-safety function was itself not crash-safe.
- **Fix:** Moved flush/fsync inside with block. Also moved `_unload_omlx_model` to finally
  block — model unload failure must not prevent S4/S5 from running when FBs are already
  checkpointed.
- **Impact:** 2026-08-11 diagnostic: S2 produced 188 FBs (51 min) but S4/S5 never ran.
  Diagnostic restarted with fix, resuming from S4 checkpoint.
- **Status:** ✅ FIXED (2026-08-12)
- **Files:** `pipeline/run_diagnostic.py` (`_save_diag_state`, S2 finally block)

### BUG-080.2 — 2026-08-12 — model_assignments.yaml S5_FB_VERIFIER still claims Gemma (D2264 desync) 🟡
- **Symptom:** `config/model_assignments.yaml` line ~114: `S5_FB_VERIFIER: gemma-4-E4B-it-MLX-4bit`
  but `config/pipeline_config.yaml` verifier_v2 correctly shows `Phi-4-mini-instruct-8bit`
- **Root cause:** D2264 fixed pipeline_config.yaml but model_assignments.yaml was not synced.
  Precedence rule (pipeline_config.yaml wins) prevents runtime issue but the desync IS a
  documentation/configuration bug class.
- **Fix:** Update model_assignments.yaml S5_FB_VERIFIER to Phi-4-mini-instruct-8bit.
- **Status:** ✅ FIXED (2026-08-13) — model_assignments.yaml S5_FB_VERIFIER = Phi-4-mini-instruct-8bit
- **Files:** `config/model_assignments.yaml`
- **Source:** Cross-examination: ChatGPT F2, Claude External §6.1

### BUG-080.3 — 2026-08-12 — Runner docstring says `python -m pipeline.run` but file is runner.py 🔴
- **Symptom:** `pipeline/runner.py` line 11: `Usage: python -m pipeline.run` — would import
  `pipeline/run.py` which does not exist. Correct: `python pipeline/runner.py` or
  `python -m pipeline.runner`
- **Root cause:** Renamed file at some point (or never named `run.py`); docstring not updated.
- **Fix:** Change docstring to `python pipeline/runner.py`
- **Status:** ✅ FIXED (2026-08-13) — runner docstring now 'python pipeline/runner.py'
- **Files:** `pipeline/runner.py`
- **Source:** Cross-examination: ChatGPT F1

### BUG-080.4 — 2026-08-12 — Runner 60-min timeout kills S2 on full-scale runs 🔴
- **Symptom:** `pipeline/runner.py` line 284: `timeout=3600` — subprocess killed at 60 min.
  S2 takes 25-40h on full corpus → runner kills it mid-extraction.
- **Root cause:** Fixed timeout not configurable per stage. S2 runs as single subprocess.
  (Current diagnostic bypasses runner — uses run_diagnostic.py directly — so not affected.)
- **Fix:** Make timeout configurable per stage in pipeline_config.yaml; S2 = null (unlimited).
- **Status:** ✅ FIXED (2026-08-13) — runner _get_stage_timeout reads config; '2': null (unlimited)
- **Files:** `pipeline/runner.py`, `config/pipeline_config.yaml`
- **Source:** Cross-examination: ChatGPT F13

### BUG-080.5 — 2026-08-12 — S5 completeness substitutes application for mechanism 🔴
- **Symptom:** `stage5_verify.py` lines 321-323: `has_mechanism = bool(fb.get("mechanism") or fb.get("application"))`
  A generated `application` field (S4 enrichment) satisfies "has mechanism" even when no
  causal mechanism was extracted → completeness scores overly optimistic.
- **Root cause:** Legacy schema compatibility — v2 allowed field substitution; v3 has
  distinct semantics for mechanism vs application.
- **Fix:** Schema-version-specific validation: v3 requires strict mechanism/boundary/consequence
  fields; v2 allows legacy substitution.
- **Status:** ✅ FIXED (2026-08-13) — check_completeness removed; no mechanism/application substitution (D2298)
- **Files:** `pipeline/stage5_verify.py`
- **Source:** Cross-examination: ChatGPT F8

### BUG-080.6 — 2026-08-12 — NLI threshold validation only warns (should be fatal) 🔴
- **Symptom:** Invalid NLI threshold configuration (e.g., entailment > pass or out of 0-1 range)
  prints warning but pipeline continues. Verification thresholds are security-critical.
- **Root cause:** Validation code uses `print("⚠️ ...")` instead of raising error.
- **Fix:** Change to `sys.exit(1)` or `raise ValueError` — invalid verification config
  is not recoverable.
- **Status:** ✅ FIXED (2026-08-13) — pipeline_paths:210 raises ValueError (FATAL) on misordered thresholds
- **Files:** `pipeline/stage5_verify.py`, `pipeline/pipeline_paths.py`
- **Source:** Cross-examination: ChatGPT F11

### BUG-080.7 — 2026-08-12 — S1.5 Ollama path missing dimension assertion (MPS path has it) 🟠
- **Symptom:** `stage1_5_embed_cluster.py` MPS path has `if embeddings_mmap.shape[1] != S15_EMBED_DIM: raise ValueError`.
  Ollama path at line 287 only does `arr[:S15_EMBED_DIM]` (silent truncation, no assertion).
- **Root cause:** D2170 only implemented fail-fast for MPS, not Ollama.
- **Fix:** Add `assert len(emb) >= S15_EMBED_DIM, f"expected ≥{S15_EMBED_DIM}d, got {len(emb)}d"` before truncation.
- **Status:** ✅ FIXED (2026-08-13) — D2274 Ollama dim assertion present (parity with MPS)
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Source:** Cross-examination: Audit1 P0.1 (corrected finding)

### BUG-080.8 — 2026-08-12 — S1.5 dropped embeddings not gated (epistemic recall risk) 🟠
- **Symptom:** Dropped segments are printed (`n_dropped`) but pipeline happily continues.
  5% embedding failure → 95% corpus → missing convergences silently.
- **Root cause:** No hard quality gate for embedding drop rate.
- **Fix:** Add gate: if drop_rate > 0.5%, fail stage with diagnostic message.
- **Status:** ✅ FIXED (2026-08-13) — D2275 drop-rate gate raises if >0.5% dropped
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Source:** Cross-examination: ChatGPT F4

### BUG-080.9 — 2026-08-12 — S5 method tag dict missing "nli+LLM-echo" → KeyError 🔴 FIXED
- **Symptom:** `❌ S5 FAILED: 'nli+LLM-echo'` at FB #10. S5 processed 9 FBs then crashed.
- **Root cause:** D2220 added citation-echo escalation path setting `method = "nli+LLM-echo"` but
  the method→icon dict at line 716 only had `{"nli","nli+LLM","LLM","none"}`. KeyError.
- **Fix:** Added `"nli+LLM-echo": "🔍"` and `"nli-echo": "⚠️"` to the dict (D2282).
- **Status:** ✅ FIXED
- **Files:** `pipeline/stage5_verify.py:716`

### BUG-080.10 — 2026-08-12 — S5 method tag dict missing "mech_quality" → KeyError 🔴 FIXED
- **Symptom:** `❌ S5 FAILED: 'mech_quality'` at FB #13 "Leading Through Intent". Same class as BUG-080.9.
- **Root cause:** Mechanism quality auto-quarantine path sets `method = "mech_quality"` but
  the method→icon dict didn't include this key.
- **Fix:** Added `"mech_quality": "🚫"` and `"nli-only": "⚡"` to the dict (D2282).
- **Status:** ✅ FIXED
- **Files:** `pipeline/stage5_verify.py:716`

### BUG-080.11 — 2026-08-12 — Diagnostic runner reads "verification_status" but S5 writes "status" 🟡
- **Symptom:** Diagnostic report shows S5 PASS=0, Q=0 despite S5 actually running 134 PASS + 51 QUARANTINE.
  Gate incorrectly shows FAILED.
- **Root cause:** `pipeline/run_diagnostic.py:534` does `fb.get("verification_status", ...)` but
  `stage5_verify.py:684` writes `vfb["status"]`. Field name mismatch → count always 0.
- **Fix:** Changed diagnostic reader to `fb.get("status", fb.get("verification_status", "UNKNOWN"))`.
- **Status:** 🟡 FIXED (backward-compatible read)
- **Files:** `pipeline/run_diagnostic.py`

### BUG-081 — 2026-08-12 — evals/golden_cases.json is v2 format, not v3 compatible 🟡
- **Symptom:** 52 examples in old format: domains as comma-strings (not lists), no route/mechanism/
  boundary/consequence fields, 0 evidence_passages, source_file instead of source_books.
  Present in repo but not used by DSPy (dspy_trainer.py uses stage2_fewshot_convergent.yaml).
- **Root cause:** Legacy artifact from Maxwell OS v2.0. Never migrated to v3 schema.
- **Fix:** Either migrate to v3 format with manual adjudication, or archive with annotation.
- **Status:** 🟡 Migrate or archive
- **Files:** `evals/golden_cases.json`
- **Source:** Round 2 cross-examination: golden set audit

### BUG-082 — 2026-08-12 — S5 FLAG path practically unreachable (0/185 FLAGs) 🟡 CONFIRMED
- **Symptom:** Diagnostic: 134 PASS, 51 QUARANTINE, 0 FLAG. 3-outcome design with one
  branch producing zero results across 185 FBs.
- **Root cause (D2291 audit 2026-08-12):** FLAG fires on `borp_only_fail and not strict`
  (line 663-664). But S1.5 `min_source_diversity: 2` guarantees every convergent
  cluster has ≥2 canonical sources → BORP always passes for convergent FBs.
  Architecture: S1.5 filter (≥2 sources) → S2 convergent extract → S5 BORP check (≥2 sources).
  The FLAG condition (BORP fail + everything else pass) is logically reachable but
  practically impossible given upstream guarantees.
- **Options:**
  A) Document FLAG=0 as expected behavior, close as NOTABUG.
  B) Redefine FLAG to fire on marginal NLI scores (0.5-0.6) or low-confidence factual.
  C) Remove FLAG, simplify to PASS/QUARANTINE binary.
- **Recommendation:** Option B — NLI marginal scores provide a natural middle tier between
  confident PASS and confident QUARANTINE. Same architecture as the existing NLI threshold
  tiers (entailment→PASS, neutral→escalate, contradiction→QUARANTINE).
- **Status:** 🟡 CONFIRMED — design decision needed (see D2291)
- **Files:** `pipeline/stage5_verify.py` (lines 660-668), `pipeline/stage1_5_embed_cluster.py` (line 513)
- **Source:** Round 2 cross-examination: Claude External §2; D2291 audit 2026-08-12

### BUG-083 — 2026-08-12 — domain_anchors.yaml predates current corpus (80.5% "emerging") 🟠
- **Symptom:** Diagnostic: 149/185 FBs (80.5%) classified as domain="emerging" (catch-all).
  domain_anchors.yaml was built 2026-06-11 for business/design-agency focus. Diagnostic's
  #2 explicit domain is "ai & agents" (22 FBs) — taxonomy lacks anchors to discriminate it.
- **Root cause:** Corpus evolved (AI/agents books added) but taxonomy anchors were not updated.
- **Fix:** Add 3-5 AI/agent-specific anchors. Re-classify 149 "emerging" FBs to verify
  improved discrimination. Fix before T1.1 — re-anchoring after 750 books is expensive.
- **Status:** 🟠 Fix before T1.1 (D2290)
- **Files:** `config/domain_anchors.yaml`, `config/taxonomy_v5.yaml`
- **Source:** Round 2 cross-examination: Claude External §1

### BUG-084 — 2026-08-12 — Golden depth calibration: universal=1, specialized=1 🟠
- **Symptom:** stage2_fewshot_convergent.yaml: 73 examples with depth universal=1, specialized=1.
  S4 depth classifier validated at 87.5% (7/8) but 8 examples insufficient to lock ontology.
  Depth classification is uncalibratable from current goldens.
- **Root cause:** Depth was moved to S4 (D2241) and never received dedicated golden expansion.
  The existing goldens were built for S2 extraction evaluation, not depth classification.
- **Fix:** Build dedicated depth benchmark: 30 universal + 40 cross-domain + 40 domain +
  30 specialized + 30 hard negatives. Minimum 170 examples (D2292).
- **Status:** 🟠 Expand (D2292, P1)
- **Files:** `config/golden/stage2_fewshot_convergent.yaml`
- **Source:** Round 2 cross-examination: ChatGPT §10, Claude External §3

### BUG-085 — 2026-08-12 — hybrid_s2_extract() not wired to stage2_extract.py 🔴
- **Symptom:** D2251 declared hybrid S2 production architecture (0.736 avg, 5/6 negative rejection).
  But `hybrid_s2_extract()` exists ONLY in `tools/compare_s2_methods.py` (benchmark harness).
  Zero references in `pipeline/stage2_extract.py`. Running S2 today uses traditional-only (0.591).
- **Root cause:** D2252 deferred wiring. Hybrid was validated and decided but never integrated
  into the production extraction path.
- **Fix:** Wire hybrid_s2_extract() into stage2_extract.py with DSPy gate → traditional extraction
  path. T-007b-v2 scheduled for demo re-optimization but wiring itself is independent.
- **Status:** ✅ RESOLVED (2026-08-12) — A/B tested. HybridGate was wired (D2276, `--hybrid` flag) but was **broken at runtime** (`call_omlx()` has no `temperature` kwarg → 100% ERROR → fail-open FB). Fixed the kwarg. A/B test on 75 golden examples (`pipeline/hybrid_gate_ab.py`): positive recall 100% (0 FNs), but **negative rejection only 4.3%** (1/23 negatives) → net **-5.3% time** (gate costs more than it saves). Verdict: **do NOT enable `--hybrid` for T1.1 — run traditional-only.** The D2250 "perfect negative filter (5/6)" was the *DSPy* gate, NOT this heuristic HybridGate. Revisit hybrid only after GAP-1 (real DSPy fine-tuning).
- **Files:** `pipeline/stage2_extract.py`, `pipeline/hybrid_gate.py`, `pipeline/hybrid_gate_ab.py`, `tools/compare_s2_methods.py`
- **Source:** A/B test 2026-08-12 (this session)

### BUG-080: call_omlx_json returns list/str — S4 classification crashes 🔴
| Field | Value |
|-------|-------|
| **Discovered** | 2026-08-11 — Diagnostic S4 crash on FB #8 |
| **Symptom** | `'list' object has no attribute 'get'` then `'str' object has no attribute 'get'` at `class_data.get("domains")` |
| **Root Cause** | `call_omlx_json` returns `dict | list | str` but S4 classification path assumes dict. GPT-OSS occasionally wraps response in array or returns raw text. |
| **Fix** | BUG-080 guards: unwrap lists, reject non-dict types at all 5 `call_omlx_json` call sites in `stage4_merge.py` and `stage4_merged_call.py`. |
| **Status** | ✅ FIXED — Guards applied at L894, L913, L969 (stage4_merge.py), L127 (stage4_merged_call.py). S5 (L370) already guarded. |
| **Files** | `pipeline/stage4_merge.py`, `pipeline/stage4_merged_call.py` |
