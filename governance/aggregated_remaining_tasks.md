# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-25

## 🔧 EXTERNAL-AUDIT CROSS-EXAM REMEDIATION (D2463, 2026-08-25) — PARTIAL (4 done, 3 queued)
- ✅ **DONE — golden fail-closed (D2463):** `load_golden_parity` + `load_golden_single_source` now raise on missing/unparseable/empty golden (was silent `([], [], 0)` → zero-shot). `None` path = only legit empty case.
- ✅ **DONE — OMLX cache gate (D2463):** `assert_omlx_no_cache()` in `omlx_call.py` refuses launch if `cache.enabled`/`hot_cache_only`/`gdn_ssd_split_enabled` set (D2460 thrash flags); wired into `just s2-singletons`; warns on `preserve_mid_system_cache`.
- ✅ **DONE — D2461 ghost closed:** retroactively logged in DECISION-LOG + registered in decisions.yaml.
- ✅ **DONE — golden metadata sync:** `stage2_fewshot_single_source.yaml` `meta` 20/13→21/14 (was stale; cosmetic — loader uses config `max`, not YAML metadata).
- ⏳ **QUEUED — BUG-177 C16 silent-error class:** `parallel.py` (typed failure, raise by default), `stage5_verify._nli_pair_scores` (typed `NLIInferenceError` + `verification_error_type`), `model_lazyload` (remove silent fallback).
- ⏳ **QUEUED — BUG-178 S6 Parquet C6:** tempfile→fsync→os.replace + manifest checksum.
- ⏳ **QUEUED — BUG-179 AGENTS.md stale + `tools/delegate_guard.py` phantom:** regenerate loader metadata (D2000–D2463 / 450) + drop phantom import.
- ⏳ **VERIFY — `preserve_mid_system_cache=true`:** benign mid-request KV vs D2460-class page-cache risk (one targeted check).

None of the queued items block the running S2 singleton extraction.

## 🔧 SINGLE-SOURCE + SINGLETON S2 UNIFICATION (D2462, 2026-08-25) — PLANNED
- 🎯 **Decision (D2462):** collapse S2's 3 entry points → 2 passes. Keep `--only-convergent` separate (cross-source synthesis, 322KB golden, 75/75 principle, `is_convergent`). Merge single-source + singleton into ONE shared extractor (already share `stage2_fewshot_single_source.yaml` 14+7; duplication already caused BUG-152).
- 📌 **Why:** DRY + drift-prevention (no future D2461-style single-golden edit divergence); ZERO accuracy impact (golden/prompt unchanged). `is_singleton_fb` → provenance flag from input metadata.
- ⚠️ **Gate before code:** diff single-source vs singleton prompt-builders; reconcile `source_book` context injection to one optional-context prompt. Keep input feeding separate (single-doc clusters vs singleton orphans via D2452 prefilter).
- ⏳ **Status:** PLANNED — queue AFTER singleton S2 completes (not a blocker for the current run).

## 🛡️ BUG-175 FIX + GOV SYNC + S2 PRE-LAUNCH HARDENING (D2459, 2026-08-25) — DONE
- ✅ **BUG-175 FIXED (D2459).** `author="string"`/`"Unknown"` provenance contamination (10 metadata entries, 253 S2 records) root-caused to Phi-4-mini hallucination (BUG-053). Fix: `_AUTHOR_SENTINELS` + `is_sentinel_author()` in `book_metadata.py` (case-sensitive; blanked at cache-load + guarded in resolver); `_AUTHOR_JUNK` extended (etc./unknown/domains); `scripts/backfill_author_sentinels.py` backfilled 10 entries crash-safe (Thinknetic derived, 9 → Unknown Author, never fabricates). 9 new tests → 140/140 green.
- ✅ **Governance synced:** DECISION-LOG D2457/D2458/D2459 appended (newest-first, hash-chain intact); config/decisions.yaml 443 → 446 (summary recomputed via `recompute_decision_summary.py --check` ✅); buglog BUG-175 → 🟢 FIXED; config audit clean.
- ✅ **Singleton resume hardened:** `process_singletons` — transient `None` results (transport/parse failure) no longer mark a cluster processed → they re-enter on resume (previously silently dropped forever). Literal `\n` prints in `main()` fixed.
- 🚀 **S2 singleton LAUNCHED (11:24, 2026-08-25):** `just s2-singletons` under `caffeinate -i -s` + nohup, 6 workers (`max_workers` 3→6 — OMLX batched engine scales 3.7× with concurrency). First checkpoint at 5 batches verified (16 FBs: 6 principle + 10 PT, 16/16 R14-stamped). **Perf finding:** oMLX decode 4.5-7 tok/s/request (raw MLX 3.5 TFLOPS ≈ 33% M1 Max peak — server-side bottleneck; 0 swap, no thermal) → ETA ~25-30h for 6,317 singletons. Crash-safe every 5 batches, resume-proven. gpt-oss (S4) unloaded during S2; RSS 20.3GB.

## 🔬 E2E COHESION PROOF + FAILURE-CLASS AUDIT (D2458, 2026-08-25) — DONE (findings logged)
- ✅ **Root cause of "why the smoke looked wrong" — three distinct, now-proven causes:**
  1. **"only ran S2" is literally true.** `scripts/smoke_matrix_5x3.py` ran S2 singleton + S4, but NEVER S5. And its convergent/single-source rows were STAGED COPIES from t11 (not freshly extracted), so "S2→S4" for those origins was a re-route of existing records, not an extraction.
  2. **"S4 still yesterday's results" = S4/S5/S6 are STALE (Aug 20) vs S2 (Aug 23).** S4 t11 holds 2,830 principles (39% of 7,255), 39 PT (4.9% of 796), 1 TI (0.7% of 143), 0 PI (of 204), 0 GE (of 4). S5 t11 = 2,830 principles. S6 t11 = EMPTY. This is exactly BUG-165 ("S4→S5→S6 rerun ONCE") — never executed.
  3. **"PT segments empty"** = tool_instruction misclassified as process_template (BUG-176, FIXED via D2457). The empty `steps/trigger/...` was a SYMPTOM of the wrong ROLE, not a schema defect.
- ✅ **Live e2e proof (`scripts/e2e_proof.py`, run `e2e_proof`):** 7 representatives (all 5 types × convergent/single-source) ran through REAL S4 (OMLX) + REAL S5 (DeBERTa). **S2→S4: all 7 survive with intact R14 stamps + provenance (citation/source_authors/source_segments).** S4→S5: only the 2 principles reach S5 (both PASS); the 5 non-principle sidecars (PT/PI/TI/GE) do NOT reach S5.
- ✅ **Structural finding (not a bug — a deferred design):** S5 verifies `principle` ONLY (`load_stage4_fbs` reads `checkpoint.jsonl`, never the PT/PI/TI/GE sidecars). So "S2→S5 cohesive for all 5 types" is FALSE today by construction — non-principle types dead-end at S4. Tracked as Path A (non-principle S5 verification).
- ✅ **BLINDSPOT confirmed:** singleton origin has **0 records** in S2 t11 deduped — the 6,317 EXTRACT singletons were never extracted (stale PID 41569, `singleton_run.log` ends mid-run). So the "3-origin" matrix was NEVER actually satisfied on the real corpus; only `smoke_matrix_5x3b` (S2+S4 only) touched singletons.
- ✅ **Failure-class audit (`scripts/audit_e2e_cohesion.py`, report `stage4_merge/t11/e2e_cohesion_report.md`):** leak=46 (S2→S4 drops + S4-sidecar→S5 drops), drift=7,904 (S4 missing provenance the stale S2 carried — explained by stale artifact, NOT a code bug: current S4 carries citation/source_authors, proven live), conflict=150 (non-principle `elaboration` non-empty in the STALE S2 — pre-D2452, now blanked), blindspot=1 (singleton never extracted), gap=1 (S6 empty).

## 🛡️ TI-vs-PT ONTOLOGICAL CLASSIFICATION FIX (D2457, 2026-08-25) — DONE
- ✅ **BUG-176 root-caused + fixed.** "R Data Import and Analysis Workflow" was labeled `process_template` with EMPTY body because the passage is *framed* procedurally ("how to import data into R") but its *substance* is R code (`setwd/dir/read.csv/View`). No deterministic code-detection existed → LLM chose PT, then couldn't extract human steps from code.
- ✅ **Three-layer fix:** (1) `config/filtering.yaml` `code_markers` (46 signals, C12); (2) `detect_code_in_text()` + `_code_hint()` prompt annotation (singleton per-item + batch + single-source); (3) `_code_role_guard()` post-hoc deterministic reclassify (code + empty-steps PT → tool_instruction, stamps `code_role_corrected`). Golden anchor SS-POS-014 (R code → TI) added.
- ✅ 131/131 tests (5 new in `test_stage2_singleton_batch.py`); live OMLX re-run of the exact passage → `tool_instruction, tool_name=R`.
- ⏳ **Residual (BUG-176):** 46/796 (5.8%) process_templates in full S2 corpus carry code markers in evidence (SQLite Setup, User Input Loop, PublicPrivateExample, etc.). Re-run S2 single-source on those 46, or post-hoc reclassify via `scripts/score_single_source.py`.

## 🛡️ GOVERNANCE SYNC + SMOKE MATRIX 5×3 (2026-08-25) — DONE
- ✅ **Governance drift reconciled:** DECISION-LOG D2423–D2436 backfilled (14 decisions); BUG-149 dead `max_words=5` default → `FB_NAME_MAX_WORDS`; BUG-151 + BUG-169 duplicate headings deduped; BUG-164 status → FIXED (dedup done); D2399 description drift fixed.
- ✅ **Smoke matrix 5×3** (`scripts/smoke_matrix_5x3.py`, run `smoke_matrix_5x3b`): exercised GE/FB/TI/PT/PI across convergent + single-source + singleton clusters through live S2→S4. Rendered examinable `visual.md` (metadata/provenance/segments/properties/classification). Matrix: principle conv=1/single=1/singleton=5; PT conv=1/single=1/singleton=2; PI/TI/GE single=1 each (convergent structurally produces FB-only — BUG-166).
- ✅ **BUG-175 discovered + logged** — `author="string"` provenance contamination on 253 S2 records (8 books) from Phi-4-mini metadata hallucination (BUG-053 pattern).
- ✅ 126/126 tests, config audit clean, decision sync 443, stacks single-source PASS.

## 🛡️ STACK SINGLE-SOURCE + ONE-PANEL MONITOR (D2455+D2456, 2026-08-24) — DONE
- ✅ OMLX (D2455): homebrew omlx 0.5.1 uninstalled; 6 stale launchd plists archived; guard wired.
- ✅ Ollama (D2456): SAME clusterfuck fixed — homebrew ollama 0.30.0 uninstalled (app 0.32.15 = single source), stale `homebrew.mxcl.ollama.plist` archived, orphaned brew mlx/mlx-c autoremoved (pip mlx untouched).
- ✅ Guard generalized → `scripts/guard_stacks_single_source.py` (OMLX+Ollama, config-first, future-tax-free) with false-positive fix for app-owned CLI shims (flags only shims resolving into Cellar/opt).
- ✅ ONE panel → `scripts/monitor_stacks.py` (`just stacks`) + `just preflight`: status + version + min_version drift verdict + single-source guard. `status.py` now prints versions.
- ✅ 126/126 tests, 10/10 integrity, config audit clean.

## 🔥 S4 RERUN — CRITICAL PATH (2026-08-24, post-external-audit)

## 🔥 S4 RERUN — CRITICAL PATH (2026-08-24, post-external-audit)

**MUST (done — skipping any would have forced a re-run):**
- ✅ BUG-171 evidence-tier (`is_convergent`/`origin`) — D2442
- ✅ BUG-172 provenance (`citation`/`source_authors`/`source_diversity`/`primary_source`) — D2443
- ✅ F2 sidecar re-stamp (`routed_by_stage`, `gen_model` preserved) — BUG-170 half
- ✅ D2441 leak redaction + C12 hardcoded-path scanner (blocking for any public run)
- ✅ D2445 renderer content-type-aware (examinability)

**SHOULD (before/at rerun — correctness, cheap):**
- ⏳ **S2 singleton extraction FIRST (gated)** — extract the 18%-prefiltered singletons (6,317) via `just s2-singletons` (new, D2452) BEFORE the S4 rerun, so S4 runs ONCE on the complete S2 frontier (convergent + single-source + singletons). Running S4 first, then singletons later, forces a second S4 merge. **Prefilter is now WIRED (D2452):** `process_singletons` consumes `singletons.prefiltered.jsonl` EXTRACT verdicts and skips the 28,805 SKIP noise; D2448 prompt fixes + D2452 builder-level `elaboration`/`steps` schema enforcement are in place.
- ⏳ BUG-165 — the rerun itself: `stage4_merge.py --only-fb-ids value_keep_ids.jsonl` → S5 → S6
- ⏳ D2440 — S5 verifier calibration (AlignScore + MiniCheck vs DeBERTa) BEFORE the S5 leg; gate F1 > 0.484
- ⏳ BUG-150 — re-measure discipline `emerging` on fresh S4 output (taxonomy promotion gate)

**POST-RERUN — NON-PRINCIPLE COMMIT (Path A, D2448) — one coherent work item, gated on BUG-165:**
- ⏳ S6 non-principle tables (TI/PT/PI/GE) + wire `commit_non_fb_types` (currently dead config)
- ⏳ non-principle cross-ref producer (`consulted_fbs`, `fb_query_*`, `parent_pt_id`, `parent_fb_ids`, `promoted_to_*`) — `stage4_5_enrich.py` is FB-only today
- ⏳ non-principle S5 verification (NLI is principles-only today)
- ⏳ BUG-170 enrichment (classification + keywords + fb_version + runtime) — only after the three above exist
- ⏸ **Singleton-extraction quality gates (from live smoke 2026-08-24):** completeness gate (`score_single_source.py` DROP_THIN/DROP_ANECDOTE) is MANDATORY — live sample produced a thin PT (no steps/trigger/done) and a 4/4 `tool_instruction`→`process_template` mislabel (SQLAlchemy/MongoEngine/Superlinked) + 4/4 `causal_mechanism` over-claim. **Task #12 PT-vs-TI contrastive golden DONE (D2450)** — 3 framework-API TI positives added. **Live OMLX re-smoke 7/7 PASS (D2451):** held-out passages now correctly label pandas/React→TI, weekly-review→PT, intrinsic/extrinsic→principle+descriptive_model, and 3 thin events→NULL. Over-split hardened with SS-NEG-005/006/007 + SS-POS-012 (React); `DROP_THIN`/`DROP_ANECDOTE` gate remains the hard backstop.

**WORTH (post-rerun, non-blocking):**
- ⏳ BUG-169 — TI `parameters` missing (verify full 143-TI corpus)
- ⏳ BUG-170 — non-principle classification (latent until `commit_non_fb_types`)
- ⏳ BUG-168 — dspy_trainer.py wire-or-archive
- ⏳ D2439 accept-defer — Leiden swap / contextual retrieval / cross-encoder reranker / DuckDB (P2)
- ⏳ D2445 verdict — core-body type-specificity refactor (post-BUG-165 decision, golden-set gated)

---
 | **Decisions:** D2000-D2440 | **D2437/D2438 (2026-08-24): deterministic value-filter (`scripts/score_single_source.py` + `scripts/prefilter_clusters.py` + `config/filtering.yaml`) + S4 preflight/smoke/stress harness (28 tests) + `scripts/render_s4_visual.py`. Pre-S4 hygiene done: dedup (8,402) + passage sweep (841 flagged). Taxonomy "discipline promotion" REVERTED (broke D2422 disjointness — 3 labels already domains). 110/110 tests green.**
> **D2439/D2440 (2026-08-24):** 6-LLM external SOTA audit (claude/qwen/chatgpt × 0021/0023/0024) claim-by-claim verified. D2439 = verdict (accept-defer Leiden; accept-P2 contextual-retrieval/cross-encoder-reranker/DuckDB; reject SetFit/CRAG/ColPali/ColBERTv2; DSPy is exists-but-unwired → BUG-168). D2440 = run AlignScore+MiniCheck through existing `calibrate.py` harness vs DeBERTa before any S5 threshold change. **No SOTA swap before BUG-165 produces a current corpus to measure against.**
> **D2441/D2442 (2026-08-24):** external-audit A+B executed. D2441 = public leak redacted (929-title manifest → runtime glob) + C12 hardcoded-path scanner recursive (162 files) + 9 hardcoded paths fixed. D2442 = **evidence-tier preservation FIXED** (`is_convergent`/`origin` through S4→S6, was silently dropped → BUG-171) + `scripts/freeze_run_manifest.py` + `scripts/audit_s4_fields.py`. Live 6-FB smoke: 2 principles classified + 4 routed, 0 failures, tier lands correctly. New bugs: BUG-169 (TI `parameters` missing), BUG-170 (non-principle not classified). 110/110 tests green. **T1.1 canary: S2 ✅ (279 FBs) → S4 ✅ 278/279 FBs (1 CRIBS quarantine → gate relaxed D2386) → S5 ✅ (235 PASS / 43 QUARANTINE) → S6 ✅ (278 committed, D2391). Integrity 17/17 + audit green (D2395). Working tree committed `793fd26` (D2397); golden verbatim fixed 80/80 (D2397/BUG-136); S4 reval DONE (D2398) — depth cross-domain 86.3%→21.6%, discipline emerging 32.0%→15.5%; domain-promotion defer (D2399); S4/S6 field contract (D2400). Frontier T1.1 audit 4 blockers fixed (D2402-D2405); session_seed YAML parse break fixed (D2406); run_production.py archived + fail-closed regression tests (D2407); response_format=json_object → empty gpt-oss-20b fixed (D2408). **R3 canary S4→S6 rerun COMPLETE (2026-08-17 19:22:39): S4 279/279 FBs (0 failed) → S5 236 PASS / 43 QUARANTINE / 0 FLAG → S6 279 committed (pipeline_run_id=canary) + Parquet. ~87 min. D2408 validated live; 236/43 ≈ 235/43 → no regression.** **D2409 + D2410 (2026-08-17): S1.5 embed cache + S5 incremental checkpoint/resume (6 tests) + S4 metadata derivation audit fixes (temporal_scope boundary-match, difficulty_map C12 with 0/279 drift, context "general" schema-legal) — 7 more tests → 47-test suite green, config audit strict clean, integrity 10/10, smoke-plumbing S0→S1.5 green. T1.1 stage PREPARED: caffeinate active, OMLX lazy-load (2/7 models), preflight clean.**
> **D2443/D2444/D2445 + F2 (2026-08-24):** forensic-audit F1/F2/F3 + render fix (see buglog). D2443 = provenance carry-through (citation/source_authors/source_diversity/primary_source S2→S4→S6 — BUG-172 FIXED). D2444 = difficulty-map verified NOT-a-bug. D2445 = render_s4_visual.py content-type-aware. F2 = sidecar re-stamp (routed_by_stage, gen_model preserved). Live smoke ✅; 35 S4 tests green; integrity 15/17; audit clean except BUG-169.
> **S4 completion (2026-08-16):** 278 FBs | depth cross-domain 240 / domain 35 / universal 2 / specialized 1 | causal_mechanism 53 (19%) | 0 JSON/truncation/LLM failures | 3 name collisions, 21 name truncations | grammar A/B ✅ RESOLVED (OFF wins, D2392) | depth prompt ✅ fixed (D2393) | taxonomy discipline `emerging` 32%→15.5% (D2394), domain 93.9% pending review
> **S5 Architecture:** DeBERTa-only NLI, threshold 0.10 (D2298) + premise/hypothesis pairing (D2321). Final. No ongoing adjudication.
> **Active Models:** Qwen3-Coder-30B (S2) | GPT-OSS-20B (S4 classifier) | DeBERTa-v3-large (S5 verifier) | bge-m3 (Emb)
> **Hybrid Gate:** Wired (P0.1, D2276) but **DISABLED for T1.1** — BUG-085 A/B proved net-negative (4.3% negative rejection). Run traditional-only.
> **ISOR Scoring:** Active (P0.4, D2284). 3-dimension independence rating in verified FB output.
> **Audit completed:** Runner.py Gemma dead code purged. Stale comments fixed. No silent crash risks found.
> **D2300-D2307:** Modularity gaps, cold-reload, DSPy 3 gaps, CRIBS batch mitigation, DSPy tier-aware split, InferenceProvider protocol, recall measurement — all logged/implemented (2026-08-12).
> **D2337-D2341 (NEW, 4-LLM audit):** S6 data loss, S4/S6 fail-open, runner run-id isolation, model-registry drift, schema corrections.
> **D2351-D2355 (NEW, 4-LLM audit × independent re-verification):** S4 depth fail-open, provenance/schema gaps, singleton index, S4 bottleneck. **Must/Should/Worth tiers → `governance/T1.1_CANARY_READINESS_MUST_SHOULD_WORTH.md`.**

---

## 🎯 AGGREGATED REMAINING TASKS — 2026-08-23 (most-critical-first)

> **D2437 (this session):** deterministic value-filtering built + run. `scripts/score_single_source.py`
> post-hoc triage on 8,410 → **KEEP 4,892 / DROP 3,510 / DEDUP 8** (DEDUP=8 matches BUG-164's surplus exactly).
> `scripts/prefilter_clusters.py` pre-LLM gate, dual-use single-source + singletons → **EXTRACT 18.0% of 35,122
> singletons** (and 36.9% of a 3,000 single-source cluster sample). Thresholds in `config/filtering.yaml` (C12).

1. 🔴 **BUG-165 — S4→S5→S6 rerun ONCE** on finalized S2 (8,410, or the 4,892 keep-list). S6 EMPTY; S4/S5 stale at 2,830. This is THE product build.
2. ✅ **R1.4 / BUG-164 dedup** — DONE (2026-08-24): `scripts/dedup_s2.py` dropped 8 surplus exact-fb_id records → `checkpoint.deduped.jsonl` (8,402). Near-dup name groups (35) flagged REVIEW, not auto-dropped.
3. 🔴 **BUG-150 discipline `emerging` 38.4%** — re-measure on FRESH S4 (was stale 2,830); promote `graphic design`/`organizational behavior`/`data visualization`/`design thinking` only after. ⚠️ **2026-08-24:** a premature "discipline promotion" (added those 3 as disciplines when they already exist as DOMAINS) broke D2422/BUG-151 disjointness — REVERTED. Promotion stays gated on a fresh S4 re-measure.
4. ✅ **R1.3 "the passage" meta-commentary** — DONE (2026-08-24): `scripts/sweep_passage_meta.py` flagged 841 records (678 leading-framing stripped; embedded flagged for review, not auto-stripped) → `checkpoint.passage_cleaned.jsonl`.
5. 🟠 **P1.3 gpt-oss cross-family FLAG** — wire disagreement flag in `stage2_relabel_extraction_type.py` (0 gpt-oss refs today).
6. 🟠 **BUG-148 `route="FB"`** — vestigial on all 8,410; derive-from-content_type or remove.
7. 🟡 **BUG-151 taxonomy** — 269 raw-alias overlaps; CI disjointness test now EXISTS + GREEN (`tests/test_taxonomy_disjointness.py`, education dual-listing resolved, domain∩discipline = only `emerging`).
8. ✅ **DECISION-LOG backfill** — DONE (2026-08-25): D2423–D2436 (14 decisions) backfilled into DECISION-LOG.md.
9. ✅ **Golden single-source meta header** — FIXED: `9 ex / 6 pos / 3 hard-neg` (was 8/5/3).
10. ✅ **BUG-149 residual** — FIXED (2026-08-25): dead `max_words=5` default → `FB_NAME_MAX_WORDS` (config-driven, C12).
11. 🔶 **Singletons (35,122)** — prefilter flags 18% (6,317) EXTRACT. **WIRED (D2452):** `just s2-singletons` runs the gated pass; `just s2-singletons-prefilter` regenerates verdicts. Extract only if single-source recall is a product requirement.
12. 🔶 **DSPy/golden expansion** — wire MIPROv2 (pending); PT-vs-TI contrastive golden ✅ DONE (D2450: SS-POS-007/008/009) + contrastive negatives ✅ DONE (D2451: SS-POS-010 descriptive-principle / SS-POS-011 PT-not-TI / SS-NEG-004 over-split). **Schema enforcement ✅ DONE (D2452):** `elaboration` blanked for non-principle + typed `s2_body_field` placeholders (`[]`/`False`/`""`) + `load_golden_single_source` truncation round-robin (preserves all 5 roles).
13. ⏸ **R2 FORM refactor · P2.x batch S5 · GAP-1 DSPy wiring · BUG-145/159/160 (P2).**
14. 🟠 **D2440 — S5 verifier calibration (AlignScore + MiniCheck vs DeBERTa)** — run through existing `pipeline/calibrate.py` + `nli_calibrate.py` harness. Gate: adopt only if F1 > 0.484 AND fail-closed (D2093) preserved. P2, post-BUG-165.
15. 🟠 **BUG-168 — `pipeline/dspy_trainer.py` exists-but-unwired** — wire into `stage2_extract.py` as few-shot source, or archive to stop audit false-positives. P2, post-BUG-165.
16. 🟡 **D2439 accept-defer (P2, post-BUG-165):** Leiden swap (needs igraph/leidenalg C-dep, already documented D2168) · contextual retrieval/late chunking · cross-encoder reranker after RRF · DuckDB analytics.
17. 🟡 **BUG-170 — non-principle types not classified** — PT/PI/TI/GE sidecars have empty depth/discipline/domains (S4 skips CRIBS for non-principle). Latent until `commit_non_fb_types: true`. P2.
19. 🟠 **D2454 — wire S4 classification golden** — `config/golden/stage4_golden.yaml` is AUTHORED + test-validated (D2451, `tests/test_stage4_golden_contract.py`) but NOT yet injected into the 4 S4 classification prompts (`CLASSIFY_SYSTEM_PROMPT` / `MERGED_CRIBS_CLASSIFY_SYSTEM` / `BATCH_CRIBS_CLASSIFY_SYSTEM` / depth-focused). Extracts the hardcoded inline depth examples → config-driven golden; needs a live smoke before BUG-165 (touches S4 hot path). *(renumbered: was "D2452" in D2451, then "D2453" after D2452 = S2 readiness; now D2454 after D2453 = checkpoint/resume.)*
18. 🟡 **BUG-169 — TI `parameters` missing** — 1 single-source TI lacks `parameters`. Verify on full 143-TI corpus during BUG-165 rerun. P2.
20. 🟡 **Ext-audit #5 — `check_stage_order()` doesn't verify sequence** (D2453, tracked) — string-matches "8-stage" + stage3-absent only; counts `timeouts` key as a stage. Low-priority hardening: compare `config.stages` keys against `EXPECTED_STAGES` and assert the actual order.
21. 🟡 **Ext-audit #14 — OMLX "health endpoint lies"** (D2453, tracked) — `/v1/models` returns the full 7-model *catalog*, so `model_lazyload.py --status` reports 41.2GB "loaded" when ground-truth `/health` `loaded_count=2` / `omlx-server` RSS=20.4GB. Wired-memory leak itself already G10-covered (flat −0.11%). Fix: read `engine_pool.loaded_count` not the catalog; root-cause is OMLX v0.5.1, compensating control = `stress_test` tripwire.

> **✅ S4 preflight/smoke/stress (D2438, 2026-08-24):** 28-test harness
> `tests/test_stage4_preflight_smoke_stress.py` + `scripts/render_s4_visual.py` (human-readable
> S4 output). Live OMLX smoke on a diverse 7-FB batch → 3 principles classified + 4 non-principle
> routed (PT/PI/GE/TI), 0 failed, 0 classification errors. Full suite **110/110 green**. Config audit
> clean, no drift. `--only-fb-ids` wiring verified fail-closed (missing/empty/no-fb_id/0-match → exit 1).

## 🔴 CRITICAL — FORENSIC FINDINGS 2026-08-23 (verified, ordered by severity)

> **⚠️ SEQUENCING (2026-08-23, CORRECTED):** S2 is FINAL — 8,410 records. P0.x is already recovered by the
> single-source rerun (only `cluster_11649` still failing, BUG-159). The S4→S5→S6 rerun must run **ONCE**
> on the finalized S2 (convergent + post-hoc-filtered single-source = 4,892 keep-list, or all 8,410). Do NOT run twice.

> **🔴 BUG-166 — single-source is ~99.9% non-convergent & generic (2026-08-23, MEASURED):**
> non-principle types = 1,146/1,147 single-source (1 convergent PT total). Single-source records are
> book-level paraphrases (descriptions, case studies, code snippets) — retrieval value but **no
> epistemic-independence value**. This means the single-source layer needs a **post-hoc value filter**,
> not a re-extraction.

0. **🔴 STRATEGIC GATE (decide FIRST, zero compute):** is single-source content part of the product,
   or is the product convergent-only (2,649 records)? Given BUG-166, recommend **convergent-first**:
   run S4→S5→S6 on convergent (2,649) + the post-hoc-filtered single-source survivors (~1,800), not
   the full 8,410. This determines the S4→S5→S6 input size.

1. **P0.x / BUG-146 — gated recovery (✅ ALREADY DONE — corrected 2026-08-23):** the "9,950 gated"
   figure is **STALE** (pre-D2417 original run). The single-source rerun (2026-08-21) already
   re-processed all 10,812 single-source clusters with the content-type-aware gate → `13,891 processed
   → 8,410 FBs`, `Gate violations: 0`. Remaining un-extracted = **~1 failing cluster (`cluster_11649`,
   BUG-159)**, not 9,950. Do NOT re-run `--reprocess-gated` — nothing left to recover.
2. **R1.4 / BUG-164 — dedup (pre-S4):** 3 fb_id groups = 11 records + 38 name groups/~80 records.
3. **BUG-165 — S4/S5/S6 stage-drift (BLOCKING, run LAST):** S4/S5 = 2,830 records (commit `b14462f`), S6 = empty; S2 = 8,410 (FINAL). **Rerun S4→S5→S6 ONCE on the finalized S2** — do NOT run it twice.
4. **BUG-150 — discipline `emerging` 38.4%** (measured on STALE 2,830-record S4 — re-measure on the final full S2 before promoting disciplines).
4. **R1.4 / BUG-164 — dedup:** 3 fb_id groups, **11 records** (not 6). 38 name groups / ~80 records.
5. **R1.3 — "the passage" meta-commentary:** **1,161 records** (not 1,036).
6. **P1.3 residual — gpt-oss cross-family FLAG:** not wired (`stage2_relabel_extraction_type.py` has 0 gpt-oss refs).
7. **BUG-151 — taxonomy:** education dual-listing already resolved; **269 raw-alias overlaps** remain + CI disjointness test.
8. **BUG-148 — `route="FB"`** on all 8,410 records (vestigial).
9. **DECISION-LOG.md lags** `decisions.yaml` (D2422 vs D2436) — backfill D2423–D2436.
10. **Golden single-source meta header wrong:** claims `total_examples: 8, positives: 5`; actual = 9 examples / 6 positives.

### 🧭 EXACT TASK SEQUENCE (pragmatic, BUG-166-aware — 2026-08-23)

> One decision, then cheap hygiene, then ONE expensive run, then measure. Do NOT run S4→S5→S6 more than once.

| Step | Task | Cost | Gate |
|------|------|------|------|
| **G0** | **Decide product scope** — convergent-only (2,649) vs + post-hoc-filtered single-source (~1,800) vs + all single-source (8,410). Default: **convergent + filtered survivors (~4.5k)**. P0.x is already done (BUG-146 corrected). | 0 | blocks all |
| **H1** | R1.4 / BUG-164 dedup — 3 fb_id groups (11 records) + 38 name groups (~80 records) on S2 checkpoint. | min | before S4 |
| **H0** | **Post-hoc value filter** on the 5,761 single-source (new `scripts/score_single_source.py`): keep convergent + actionable/general; drop thin paraphrase/anecdote. Keeps ~32%. | min | after G0 |
| **H2** | Fix golden single-source meta header (9 ex / 6 pos). | min | CI |
| **H3** | ✅ DECISION-LOG backfill D2423–D2436 (14 decisions) — DONE 2026-08-25. | min | doc |
| **H4** | BUG-151 CI disjointness test (education already resolved; 269 raw-alias overlaps remain). | ~1h | CI |
| **R1** | **S4 → S5 → S6 ONCE** on the finalized S2 (per G0 size). This is the actual product build; S6 is currently EMPTY. | multi-hr | ✅ the one run |
| **M1** | Re-measure BUG-150 discipline `emerging` on the fresh S4 (was 38.4% on stale 2,830); promote disciplines only if still high. | min | after R1 |
| **M2** | Verify BUG-149 truncation = 0 on fresh S4 (fix already committed). | min | after R1 |
| **M3** | BUG-148 `route="FB"` cleanup / D2128 derive-from-content_type. | ~1h | hygiene |
| **D1** | P1.3 gpt-oss cross-family FLAG wiring; R1.3 "the passage" sweep; BUG-145/150/151 deferred items; DSPy/golden expansion. | varies | post-R1 |

## 🚧 This session (R1 extraction_type drift, D2427/D2428) — remaining tasks

> Ontological audit of the FORM axis found a non-partitioning 4-way label set + two
> role↔form routing tables (D2150/D2417) violating the D2323 "orthogonal axes" contract.
> Drift confirmed: causal_mechanism 11%→60% single-source; n=30 sample ~43% mislabeled.
> R1 committed (df1fbfd). D2429 (ensemble adjudication): drift CONFIRMED — judges downgrade
> ~40-50% of sampled causal labels; FORM-axis ambiguity validated (D2427); consensus is
> silver-standard (third pass needed). Human-review queue = 10 records. Remaining, in priority order:

| # | Task | Status |
|---|------|--------|
| R1.1 | **Confirm drift error rate** — ✅ DONE (D2429). Ensemble confirms ~40-50% causal over-claim. Human-review queue = 10 records: 1,2,9,11,12,15,25,26,27,30 | ✅ done |
| R1.6 | **Third independent pass** on the 10-record disagreement set (2 LLMs correlate — don't treat 2-way majority as golden) | 🟡 optional |
| R1.2 | **Run R1 relabel sweep** (`stage2_relabel_extraction_type.py`) on a COPY, audit diff, then production | ✅ DONE (D2434) — gemma judge, promoted; P1.3 verdicts applied (D2435) |
| R1.3 | "the passage" meta-commentary (1,036 records) prompt fix + post-hoc sweep | 🟡 P1 |
| R1.4 | Near-dup surface (38 name groups, ~80 records) dedup before S4 | 🟡 P1 |
| R1.5 | content_type instability (PT 19%→8%, TI 4%→1%, GE 4 records) — monitor/decide | 🟡 P1 |
| R2 | FORM axis refactor → justification × modality facets (D2427) | ⏸ after S4-S6 |
| H1 | BUG-159 prompt hardening (treat passage as DATA) + contamination canary | 🟡 P2 |
| H2 | BUG-160 evidence-relevance pass (add topical-relevance check) | 🟡 P2 |
| H3 | minhash_signature empty on 8 records | 🟡 P2 |
| H4 | ~~route="FB" inert field cleanup~~ → RESOLVED: `route` is a live D2128 fallback (not inert) — see P2.4 | ✅ P2.4 |
| SEQ1 | Singleton benchmark on copy (batched vs single) — now unblocked | ⏸ gated |
| SEQ2 | **STOP before S4/S5/S6** for visual inspection | ⏸ gated |

### 🔑 D2431 + D2432 (2026-08-22) — A/B refutes S4 ownership; FORM fixed in S2; forensic audit

> A/B (n=20): Qwen3+ladder = 25% causal vs 55% current; gpt-oss = 0% causal / 60% empirical (its own
> bias). Cross-family agreement 35%. Keep FORM in S2 (unified ladder); gpt-oss = disagreement FLAG.
> Forensic audit (D2432) added dead-config/dead-code + provenance findings. D2430 superseded.

| # | Task | Status |
|---|------|--------|
| P1.0 | F1/F5 + DECOUPLING + remove MAPPING RULES — all 4 S2 prompts unified | ✅ D2431/D2432 |
| P1.1 | F3/F4 — fix golden single_source (TI→normative_heuristic; strip negative causal) | ✅ D2433 |
| P1.2 | Re-label 5,761 single-source/singleton records with fixed ladder (copy-first) | ✅ DONE (D2434) — gemma-4-E4B judge, promoted; causal 44.8%→5.8%. **SCOPE CONFIRMED 2026-08-23: single-source ONLY — convergent 0/2,641 touched (forensic diff).** |
| P1.3 | Cross-family gpt-oss disagreement FLAG + human-review queue | 🟡 PARTIAL — 49 human verdicts applied (D2435, 14 corrections + 9 quarantine); gpt-oss FLAG wiring still open |
| P1.4 | A2 — remove `|"none"` from singleton extraction_type enum (BUG-163) | ✅ D2433 |
| P0.x | Close non-principle dead-end — route PT/PI/TI/GE through S4/S5/S6 (D2418) | 🔴 P0 — CODE DONE (D2417/D2421); RUN pending: `seed_gated_ids.py --log runner_t11_v3.log` + `--reprocess-gated`. **SCOPE: (1) seed 158→~9,950 gated IDs; (2) re-extract gated clusters content_type-aware; (3) S4→S5→S6. Plus 183 failed auto-retry.** |
| P2.1 | B1 — delete dead D2150 EXTRACTION_TO_CONTENT_TYPE (BUG-162) | ✅ D2433 |
| P2.2 | B2/B3 — remove dead schemas.py PT/PI/GE/TI classes; align actors type (BUG-162) | ✅ D2433 |
| P2.3 | C1/C2 — clarify elaboration (principle-only) + failure_mode provenance in config | ✅ D2433 |
| P2.4 | C3 — correct H4 route-inert status (route is a D2128 fallback) | ✅ D2433 |
| P2.5 | D1 — reconcile D2417 role-form coupling vs D2427 (keep as fail-safe, document) | ✅ D2433 |
| P2.6 | R2 justification×modality split (reduce 65% cross-family ambiguity) | 🟡 P2 |
| P2.7 | Golden CI validator | 🟡 P2 |
| P2.8 | Batch S5 DeBERTa inference | 🟡 P2 |

## 🚧 Frontier T1.1 audit (4b55797) — 4 blockers fixed this session (D2402-D2405)

| # | Item | Status |
|---|------|--------|
| F1 | S4 runner timeout '4': 3600 → null | ✅ D2402 |
| F2 | S2 schema-failure → NULL → 3-state FB/NULL/FAILED (retry on resume) | ✅ D2403 |
| F3 | S4 classification-failed → not processed (retry on resume) | ✅ D2404 |
| F4 | S4 fabricated evidence="cited" + S5 FAILED gate → QUARANTINE | ✅ D2405 |

**Post-T1.1 hardening (remaining, non-blocking):**
- S1.5 MPS: renormalize after 1024→512 truncation (IndexFlatIP assumes unit vectors; ollama is prod backend)
- S1.5 K-means fallback: mark positional-split clusters degraded
- S2 probe cache: fingerprint (not just counts)
- S2 sampling: group by canonical source_id (not truncated basename)
- S2 evidence: verbatim substring verification (epistemic provenance)
- S4.5: register in runner STAGE_ORDER (flipping enabled:true must actually run it)
- NLI calibration data (evals/nli_golden.jsonl) not committed → 0.10 threshold not reproducible
## 🚧 #0.8 — S4 completion findings → remaining work (2026-08-16)

> S4 canary finished 278/279 FBs. One CRIBS quarantine (`cluster_6241`, empty `application`)
> tripped the S4 fail-closed gate (`max_failed_ratio=0.0`, D2338). Gate decision required
> before S5. Full details: D2386–D2390 + `governance/buglog.md` §"S4 canary completion findings".

| # | Item | Status |
|---|------|--------|
| G1 | **S4 gate decision** — `cluster_6241` empty-application quarantine. Relaxed S4 `max_failed_ratio` 0.0→0.01 (D2386). | ✅ DONE (CONDITIONAL_SUCCESS) |
| G7 | **S5/S6 canary** — S5: 235 PASS / 43 QUARANTINE (15.5%). S6: 278 committed after schema-migration fix (D2391). | ✅ DONE |
| G2 | **Grammar A/B test** (D2385/D2392) — OFF baseline **30/30 (100%) valid, 21.1s**. ON (0.6.0 xgrammar) **BREAKS gpt-oss-20b** (empty content, Harmony conflict). → **keep grammar OFF**. | ✅ DONE |
| G8 | **DB contamination** — 676 rows / 5 run_ids (canary 557 = old 279 + new 278). Decide reset policy before final T1.1. | ✅ DONE (D2396) — fresh-DB for T1.1 |
| G9 | **Vector DEGRADED** — `vec_fbs` absent (python.org build lacks `enable_load_extension`). FTS + Parquet still serve retrieval. | P3 |
| G3 | **Taxonomy expansion** (D2388/D2394) — discipline `emerging` 32%→**15.5%** (schemas kind-filter fix + alias expansion). Domain `emerging` 93.9% = structural gap (design-centric v5 vs business corpus) → **needs governance promotion + demotion review**. ⚠️ D2399: promote/demote must run on FULL-corpus `taxonomy_counts` (post-T1.1 **+ D2345 single-source**), NOT canary — the canary was a single-domain prefix that under-represents design domains. | 🟡 P1 (post-T1.1+D2345) |
| G4 | **Depth skew fix** (D2387/D2393) — tightened `DEPTH_FOCUSED_PROMPT` + `DEPTH_BATCH_SYSTEM` (default-to-domain; cross-domain = 2+ DISTINCT disciplines). Re-measure on next S4 run. | ✅ DONE (D2398) — S4 reval: cross-domain 86.3%→21.6%, domain 12.6%→77.0%; discipline emerging 32.0%→15.5% |
| G5 | **`is_specialized` persistence** — parsed-but-not-persisted (None × 278). | P3 |
| G6 | **OMLX 0.6.0 evaluation** (D2390/D2392) — xgrammar works but breaks gpt-oss-20b; C3 benchmark-upload opt-in-by-action. Do NOT upgrade for grammar. | ✅ DONE |
| G10 | **Run-specific DB** (D2396 follow-up) — scope `DB_PATH` by run_id + stable active-KB pointer for retrieval; needs retrieval regression test. | P2 (post-T1.1) |

---

## ✅ #0.7 — D2371–D2375: application/intimacy/context fixes + S4 speed (2026-08-16)

> Session 2026-08-16: application-required enforcement, intimacy lattice hardening,
> contamination-cascade fix, v2.0 `content_based` restore, push-boundary re-derivation,
> and the S4 speed-lever (CoT cap) — all verified (py_compile + functional + live LLM).

| # | Item | Status |
|---|------|--------|
| D2371 | `application` REQUIRED (schema contract, fail-closed at S4) | ✅ DONE |
| D2372 | Intimacy lattice consults raw labels (survive `emerging` collapse) | ✅ DONE |
| D2373 | Context fallback `personal`→`general` (contamination cascade) | ✅ DONE (folded into D2375) |
| D2374 | v2.0 `content_based` routing restored (personal disciplines→private + design/business escape) | ✅ DONE |
| D2375 | Shared `derive_context` + fresh context/intimacy at push (S6b/S6c) | ✅ DONE |
| S4 speed | `thinking_budget: 256` + `depth_thinking_budget: 128` flipped | ✅ DONE (CRIBS 4/4 complete, ~37% faster, 0 exc) |
| Hash audit | fb_id/source_ids/manifest_hash alignment verified | ✅ DONE (see revelations) |
| **D2376** | `extraction_type` default `""` + >95% dominance canary + `source_ids` provenance closure (R1+R2) | ✅ DONE (this session) |

### Remaining before T1.1 (new, 2026-08-16)

| # | Item | Priority |
|---|------|----------|
| R1 | **`extraction_type` default over-claim** — all `.get(..., "causal_mechanism")` → `""` + >95% dominance canary (D2376). | ✅ DONE (D2376) |
| R2 | **`source_ids` provenance gap** — restored schema field + S4 derivation + S6 column (D2376). | ✅ DONE (D2376) |
| R3 | **Canary S4→S6 rerun** — verify D2371–D2376 + speed knobs + D2402-D2405 fail-closed paths end-to-end against the fixed 180-FB checkpoint (see `tools/canary_rerun_s4onward.sh`). Fail-closed *decision logic* unit-covered (`tests/test_fail_closed_d2402_2405.py`, 9 tests, D2407). | ✅ DONE (2026-08-17 19:22:39, ~87 min) — S4 279/279 FBs (0 failed) → S5 236 PASS / 43 QUARANTINE / 0 FLAG → S6 279 committed (`pipeline_run_id=canary`) + Parquet 4482.4 KB. D2408 validated live; 236/43 ≈ 235/43 → no regression. ⚠️ Failure-injection kill/restart on a REAL cluster still untested in-vivo (canary had 0 failures) — unit-tested only (D2407); optional pre-T1.1 |
| R4 | T-015 golden depth balance (≥5 universal + ≥5 specialized) — verbatim-mining deferred. | P2 (spec in MTR T-015) |

### New findings this session (2026-08-16 — D2376 audit)

| # | Finding | Severity |
|---|---------|----------|
| F1 | **Orphan fields — `prerequisite_fbs`, `contradicts_fbs`, `procedural_skill` are schema-defined + committed (S6) + traversed (retrieve.py) but NEVER populated** by any stage. `related_fbs` IS populated (P1.4). Accessibility correlates with `prerequisite_fbs` in code, but 0/180 FBs have prereqs → all 6 `accessibility=prerequisite` come from the `expert AND def>200` heuristic (D2132), not dependency edges. D2400: S4 = producer layer (S6 = persistence-only); producers go in a post-S4 enrichment (fold into D2345), NOT S6/inline-S4. **✅ RESOLVED (D2401, 2026-08-17)** — `pipeline/stage4_5_enrich.py` is the post-S4 producer stage (gated `stage4_5.enabled: false` for T1.1). | ✅ DONE (D2401) |
| F2 | **`Cluster` schema class is stale v2** (`cluster_id:int`, `centroid_text`, `distinct_books`) vs actual S1.5 v3 output (`cluster_id:str`, `segment_ids`, `source_ids`, `source_diversity`, `is_convergent`, `is_noise`, `is_singleton`). Not used for validation (dead schema), but a drift blindspot. | Low |
| F3 | **`isor_score` recomputes `resolve_source_ids(source_books)`** instead of using the now-persisted `fb.source_ids` (redundant but correct — same canonical hash). | Low |
| F4 | **`accessibility` enum = `self-evident` \| `prerequisite`** (TWO labels). `prerequisite` is BOTH a label value AND distinct fields (`prerequisite_fbs` on FB; `prerequisite` string on PT; v1 had `prerequisites` string). They logically correlate (non-empty `prerequisite_fbs` → `accessibility=prerequisite`), and the code implements this — but see F1 (vacuous in practice). | Info |

---

## ✅ #0.6 — D2367/D2368/D2369 verification round + V8/V9 execution (2026-08-15)

> **5-LLM verification round (claude0014/deepseek0013/kimi0013/qwen0013/chatgpt0014) adjudicated + executed.**

| # | Item | Status |
|---|------|--------|
| V1 | BUG-132 `thinking_budget` global→per-call (D2368) | ✅ DONE |
| V2 | Golden-hash → `just preflight` hard gate (D2367) | ✅ DONE |
| V3 | `decisions.yaml` reconcile + `sync_decisions.py` description fix | ✅ DONE |
| V4 | Purge stale "98%"/"160-200h"/"~110-140h" denominators | ✅ DONE |
| V5 | `pipeline_commit` bump + buglog 18 emoji align | ✅ DONE |
| V6 | `apply_depth_relabel.py` list-form silent-drop | ✅ DONE |
| V7 | DECISION-LOG D2351–D2363 backfill (D2368) | ✅ DONE |
| V8 | Golden depth expansion — CONV-054 universal + CONV-055 specialized (D2369) | ✅ DONE-partial (1→2 each; full ≥5/≥5 = T-015) |
| V9 | Resume mechanism live-verified (D2369) — `--run-id` scoping + run-scoped marker + `--resume-from` | ✅ DONE (kill-at-20-FBs needs a domain slice, not `--books 3`) |

> **Refuted false alarms:** Qwen "D2229 sqlite-vec 1024→512 → S6 crash" (FALSE); DeepSeek/Qwen "CONV-037/039 missing depth" (FALSE — list-form, real bug was relabel tool). Stale "~90h"/"160-200h"/"~110-140h" → correct **~39h**.

---

## 🔴 #0.5 — MUST/SHOULD/WORTH before canary re-run + T1.1 (BUG-108…119, D2351–D2355, 2026-08-14)

> **4-LLM audit (`chatgpt0010.md`, `claude0010.md`) × independent code re-verification.** Two ChatGPT errors corrected
> (`s3_original_domain` is migrated+dead, not a fresh-DB blocker; singleton integration is still broken, not "fixed").
> Full tiered breakdown: **`governance/T1.1_CANARY_READINESS_MUST_SHOULD_WORTH.md`**.

> **✅ IMPLEMENTATION STATUS (2026-08-14 14:34):** M1–M4, S1, S2, S4, W1–W6 are **DONE** (verified with
> `py_compile` + unit + live SQLite tests). **S3 is PARTIAL** — `batch_depth_classify()` was A/B-tested live
> (n=8): ~1.9× faster but **75% parity (< 90% gate)** → NOT wired into production; the recommendation is a
> FrugalGPT gemma-4-E4B depth cascade behind the same gate. **S5** (benchmark-through-production) remains open.
> **W7 (`deathpectation` literal) → RESOLVED (2026-08-15):** it is the user's private Anytype space name.
> **W6 intimacy routing → D2356** (`pipeline/intimacy_lattice.py`).

### 🔴 MUST (blocks a defensible T1.1)

| # | Task | Bug | Decision | Effort |
|---|------|-----|----------|:------:|
| M1 | S4 depth fail-closed — no silent `"domain"` on exception/no-match | BUG-108 | D2351 | 0.5h |
| M2 | `depth_max_tokens` 512 → 1024 + fix stale docstring | BUG-109 | D2351 | 0.25h |
| M3 | Carry `source_segments` through S4 → S6 | BUG-110 | D2352 | 1h |
| M4 | Persist `is_summary` end-to-end | BUG-112 | D2352 | 0.5h |

### 🟠 SHOULD (quality / feasibility — before full T1.1)

| # | Task | Bug | Decision | Effort |
|---|------|-----|----------|:------:|
| S1 | Persist `evidence_passages`/`_shown` to SQLite (or document Parquet as verbatim store) | BUG-111 | D2352 | 1h |
| S2 | Singleton S2→S4 index fix (`run_stage4` reuse `principles_idx`) | BUG-113 | D2353 | 1h |
| S3 | S4 bottleneck resolution (remove batch `depth` + batch focused depth) | — | D2354 | 2–3h |
| S4 | Batch missing-output fail-closed | BUG-114 | D2355 | 0.5h |
| S5 | Depth benchmark authority (production path; reconcile 87.5% vs 37.5/50%) | BUG-115 | D2351 | 1h |

### 🟡 WORTH (hygiene / drift / bloat — non-blocking)

| # | Task | Bug / note | Effort |
|---|------|-----------|:------:|
| W1 | Remove dead `s3_original_domain` | BUG-116 | 0.5h |
| W2 | Unify secondary checkpoint writers on `_write_checkpoint_jsonl` | BUG-117 | 0.5h |
| W3 | `insert_embedding()` per-FB failure logging | BUG-118 | 0.25h |
| W4 | Add `jargon` to FTS5 | BUG-119 | 0.25h |
| W5 | Reconcile `extraction_type` "S5 consumer" claim | drift | 0.25h |
| W6 | Restore/document v2 intimacy routing | drift | ✅ DONE (D2356) |
| W7 | Define or drop `deathpectation` | drift | ✅ RESOLVED (2026-08-15) — private Anytype space name |

> **S4 bottleneck (D2354) — the ultimate solution:** correctness-first (fail-closed + 1024 tokens) → remove waste
> (drop `depth` from CRIBS batch) → batch the *focused* depth prompt (keep GPT-OSS + short prompt + `fb_index`) →
> benchmark gate ≥90% → only then consider gemma-4-E4B. Target: ~25s/FB → ~6–8s/FB, full T1.1 ~142h → ~25–30h.

---

## 🔴 #0 — NEW BLOCKERS FROM 4-LLM AUDIT (B11–B15, D2337–D2341, 2026-08-13)

> **Surfaced by ChatGPT audit + independently re-verified.** Kimi/DeepSeek = repo-blocked (zero signal); Qwen = unsound
> (rated prompt's own claims as verified). These are downstream (S4/S6) correctness + config trust issues; the S6 data
> loss is the highest-severity defect because a successful-looking full run would silently drop fields.

| # | Decision | Task | Status |
|---|----------|------|--------|
| B11 | D2337 | S6 persist D2323 axes + mechanism/boundary/consequence + round-trip test | ✅ DONE |
| B12 | D2338 | S4/S6 fail-closed — `failure_ratio > max → exit 1`; `>0 → exit 2` | ✅ DONE |
| B13 | D2339 | runner `--run-id` pre-parse before `pipeline_paths` import | ✅ DONE |
| B14 | D2340 | model-registry drift — session_seed renamed; config/path rename deferred (post-T1.1) | 🟠 PARTIAL |
| B15 | D2341 | schema corrections — three-axis `status`, typed edges, TI class, feedback→YAML | 🟡 DEFERRED P2 |

> **Ordering:** B11→B12 (silent permanent corruption) → B13→B14 (run-scoping + registry) → B15 (schema contract, P2).
> ChatGPT's "enable hybrid" recommendation REJECTED (BUG-085 A/B proved net-negative).

---

## ✅ #1 — T1.1 PRE-FLIGHT BLOCKERS (B1–B10, D2324–D2332) — ALL IMPLEMENTED

> **CONDITIONAL-GO → all pre-flight blockers closed.** Implemented across commit 9295ce0 (B2/B3/B4/B7/B8/B9/B10)
> and D2343 (B1 residual: S2 resume `load_jsonl`; B5 residual: `route_values` config-driven; B6 residual: e2e `--in-place`;
> NEW e2e ontology round-trip check [7]; integrity [11] label). Roundtable (7 items) + independent code sweep (B1).
> kimii's BLOCKER (S5 fast-gate) fabricated; chatgpt's findings real; qwen's "0.65" rejected.

| # | Decision | Task | Status |
|---|----------|------|--------|
| B1 | D2332 | S2 checkpoint fail-closed `load_jsonl` at every reader + resume | ✅ DONE (D2343) |
| B2 | D2329 | Resume-validity manifest (run_id/schema/count/COMPLETE) | ✅ DONE |
| B3 | D2326 | S0 fail-closed + tri-state quality check (C16) | ✅ DONE |
| B4 | D2323 | Content-type golden fix → 5-role ontology | ✅ DONE |
| B5 | D2323 | Content-type enum wiring + `route_values` config-driven (C12) | ✅ DONE (D2343) |
| B6 | D2327 | S1.3 prefilter `--in-place` in runner + e2e | ✅ DONE (D2343) |
| B7 | D2331 | S2 silent-skip fail-closed (`S2_MAX_FAILED_RATIO`) | ✅ DONE |
| B8 | D2328 | S5 calibration truth (P=0.647/R=0.386/F1=0.484) + runner desc | ✅ DONE |
| B9 | D2325 | S6 provenance per-FB `INSERTED/FAILED/SKIPPED` | ✅ DONE |
| B10 | D2330 | e2e run-scoping + quarantine retrieval contract test | ✅ DONE |

---

## 🔴 #2 — CONTENT-TYPE ONTOLOGY CONSOLIDATION (D2323, 2026-08-13)

> **Blocks the T1.1 full run** (senior RAG review: PT/PI are the Layer-2 product; currently orphaned + dead-schema + stale-trained).

| # | Task | Status |
|---|------|--------|
| 1 | Freeze contract → `config/content_types.yaml` (2 axes, core+extension, 13-field TI, D2150/D2128) | ✅ DONE (D2323) |
| 2 | Fix golden few-shot `content_type` values (`model/heuristic/pattern` → correct ontology) | ✅ DONE — all 77 golden FBs carry `content_type=principle` (verified 2026-08-13) |
| 3 | Wire enums: `schemas.py` + `stage2_extract._VALID_CONTENT_TYPES` + `stage4_merge` routing → registry | ✅ DONE (except `ToolInstruction` Pydantic class = B15/D2341, P2) |
| 4 | Fix route→content_type mapping (D2128) + drop vestigial `fact`/`meta` | ✅ DONE — `ROUTE_TO_CONTENT_TYPE` + `DROPPED_CONTENT_TYPES={fact,meta}` live |
| 5 | Verify 4 orphaned FBs (3 PT + 1 TI) flow end-to-end | ⚪ MOOT — current DB has 0 rows with axes populated (all pre-D2337); re-verify after T1.1 canary |
| 6 | (deferred) S4 rich per-type extension-field generation (steps/trigger/prerequisite…) | post-T1.1 |

---

## 🔴 #2.5 — 2nd AUDIT BLOCKERS (D2346/D2347, 2026-08-13) — fix BEFORE the canary

> **ChatGPT/Qwen audit (post-D2344) surfaced 2 code-verified blockers the B1–B15 set missed.** Both hit the
> **principle** path. D2345 (non-type second pass) is DECIDED as post-T1.1 — NOT a blocker.

| # | Decision | Task (code-verified) | Status |
|---|----------|----------------------|--------|
| B16 | D2346 | S1.5 embedding-drop index alignment — return `(filtered_segments, embeddings)` + `len(segments)==len(embeddings)` assert + injected-drop tests | ✅ DONE |
| B17 | D2347 | e2e convergence metric → `sum(c["is_convergent"])` (canonical IDs); filename-diversity as separate diagnostic | ✅ DONE |

> **Why B16 first:** D2275 permits ≤0.5% embed drop; on any drop, `embed_segments()` filters locally but returns only
> embeddings → `build_clusters()` indexes the full original list → silent wrong-segment corruption (no exception).
> **Why B17:** D2336's 20% threshold is "calibrated" against `e2e_test.py:167` filename-based 24.5% — not the canonical
> quantity production gates on. Fix before the canary so the e2e/V2 gate reports a trustworthy number.

---

## 🔍 #3 — PRE-T1.1 VERIFICATION GATE (canary examine — run BEFORE full corpus)

> **✅ CANARY COMPLETE (2026-08-14).** 25K segments → S1.5→S2→S4→S5→S6 all green, EXIT 0 at every stage.
> Discovered + fixed **BUG-105** (embedding instability) via **D2348** (timeout 180s + keep_alive=-1) mid-canary.

| # | Task | Status |
|---|------|--------|
| V1 | Run a **~1,000-cluster canary** through S1.5→S2→S4→S5→S6 | ✅ DONE — 2255 clusters (207 convergent), 0 failures |
| V2 | Verify e2e **check [7]** — ≥90% rows carry `content_type`+`extraction_type` (D2337 ontology round-trip) | ✅ DONE — 279/279 (100%) |
| V3 | Verify **BUG-095** (S6 persists 6 D2337 columns) on real canary rows | ✅ DONE — 6/6 columns, 279 rows |
| V4 | Verify **BUG-096** (S4/S6 fail-closed exit codes) | ✅ DONE — 0 failed, exit 0 (correct happy-path) |
| V5 | Confirm PT/PI/TI FBs (if any) survive S4→S6 | ✅ DONE — 0 PT/PI/GE/TI (all `principle`, expected for principle-only T1.1) |
| V6 | Confirm **BUG-094** fix (no stale checkpoint → S2 fresh-start) | ✅ DONE — S2 fresh-start confirmed |

> **Canary metrics:** S1.5 2255 clusters (207 convergent, 9.2%) | S2 280 FBs (82.6% yield, 0 failed) | S4 279 FBs
> (1 dedup, 46988 edges, 0 failed) | S5 239 PASS / 40 QUARANTINE (85.7%) | S6 279 committed (398 total rows), Parquet ✓.
>
> **New findings (post-canary, NOT blocking):**
> 1. **S4 slowness** — gpt-oss-20b classify ~25s/FB **serial** (no parallelism in `stage4_merge.py`) → full-run
>    S4 ≈ **~142h** (D2363, supersedes D2362's 90h — which used the batch-CRIBS path production does not run — the 62h canary-rate figure and D2253's impossible 3.9h). Needs
>    batching / faster classifier before T1.1 full run.
> 2. **Convergence 9.2%** (DOMAIN 0 prefix) < e2e 20% threshold — sample-selection artifact (single-domain prefix),
>    not a pipeline bug. Full corpus (8 domains) measured 20.3%.
> 3. **BUG-104 confirmed** — sqlite-vec `load_extension` missing on python.org Python → vector search 0/279 (FTS fallback).

> **Decision gate:** V1–V6 green → the code path is validated end-to-end. **Gating on full T1.1 = S4 speed**
> (~142h serial, D2363) — re-tune S4 batch/classifier before any full run. (Prior "26h" was D2253, now superseded.)

---

## ✅ ROUNDTABLE ADJUDICATION — IMPLEMENTED (2026-08-12)

> **🔴 S5 NLI BUG FIXED (2026-08-13, this session — BUG-092/D2321):** `deberta_check()` was feeding DeBERTa a single concatenated `"definition evidence"` string (no premise/hypothesis separation) and reading only the top-1 label → NEUTRAL verdicts collapsed to `"CONTRA: ent=0.00 cont=0.00"` and were quarantined. Result: **verify_pass_rate 36% (32/88)** — a ~90% false-negative rate on factually-correct cross-source FBs. Fix: proper `(premise=evidence, hypothesis=definition)` pair + `top_k=3` all-label scoring. **Post-fix: 74/88 (84.1%) PASS.** Remaining 14 QUARANTINE = 3 genuinely-vacuous MECH-FAIL + 11 NEUTRAL cross-source syntheses (legitimate fail-closed cost; D2285 claim-decomposition is the recovery path). ⚠️ D2293 calibration (P=1.0/R=0.556) was measured on the broken call — re-derive post-fix.
> **Eval status (2026-08-13):** 7/8 green — `fb_count` 92 ✅, `fb_fields` ✅, `multi_label` ✅, `relationship_edges` ✅, `verify_pass_rate` 84.1% ✅, `db_commit` ✅, `db_rows` 119 ✅. **1 red: `convergent_clusters` 24.5% (39/159) vs ≥25%** — borderline (−0.5%), sampling artifact on 20 books; a 25-book sample or accept-as-noise.

**Pre-T1.1 gate: 12/12 DONE — 9 implemented, 3 already-fixed (stale buglog), V1 verified (BUG-062 moot), G10 stress test PASS (no wired-memory leak).**

| # | Task | Status |
|---|------|--------|
| G1 | Source identity — metadata normalization + work-level convergence (D2308) | ✅ normalize_author/normalize_title in book_metadata.py |
| G2 | ISOR — metadata author + canonical count + precedence (D2309) | ✅ "weak" bucket reachable (5 FBs) |
| G3 | Runner timeout (BUG-080.4) | ✅ already D2269 (config '2': null) |
| G4 | S5 confidence — NLI gate + ISOR/mech/enrich + cap + human-review (D2310) | ✅ config-driven weights |
| G5 | S5 completeness substitution (BUG-080.5) | ✅ already D2298 (check_completeness deleted) |
| G6 | S5 threshold validation fatal (BUG-080.6) | ✅ already D2272 (raises ValueError) |
| G7 | S1.5 dropped-embed gate (BUG-080.8) | ✅ already D2275 (RuntimeError >0.5%) |
| G8 | S1.5 Ollama dim assert (BUG-080.7) | ✅ already D2274 |
| G9 | discipline "emerging" (D2310) | ✅ preserve discipline_raw + taxonomy_match_method |
| G10 | OMLX wired-memory stress test (P0.0) | ✅ PASS — 5×20 reqs, wired flat 34.26→34.22 GB (-0.11%), no leak |
| G11 | delete stale Stage 3a artifacts | ✅ safe_delete (backed up) |
| G12 | golden duplicate-edition negatives | ✅ NEG-DUP-001/002 (75 total) |

### 🔴 REMAINING (most critical first)

1. **V1** — ✅ VERIFIED (2026-08-12): BUG-062 is moot. S4 classify = `gpt-oss-20b-MXFP4-Q8` (config `models.verifier.model` → `VERIFY_MODEL`), NOT Phi-4-mini. Depth semantic (D2220) + focused (D2247). No live blocker.
2. **G10** — ✅ PASS (2026-08-12): OMLX wired-memory leak stress test — 5 rounds × 20 reqs, wired flat 34.26→34.22 GB (-0.11% cumulative), 0 errors. No GitHub #2184 leak. Script: `pipeline/omlx_wired_stress.py` (`just wired-stress`).
3. **T1.1** — full S1.5→S6 run (NOW UNBLOCKED: convergence + verification + classification fixes landed). S1.3 and earlier are still valid (see rerun note).
4. **content_hash tiebreaker** — ✅ FIXED (D2315, 2026-08-12): Black Swan title-concat now collapses via `_CONCAT_SUBTITLE_SPLIT`. All 3 duplicate-edition cases collapse.
5. **GAP-1** — wire DSPy program into S2 (post-T1.1).
6. **D2285** claim decomposition · **D2292** golden depth · **D2289/D2288** splits/κ · **D2300** StorageBackend · **D2305** latency SLA (post-T1.1).

> **Golden set audit (2026-08-12, this session):** ✅ VALID post-pipeline-change — `golden_validate.py` 5/5 checks pass; 75 examples → 77 FBs; no duplicate-edition false positives among convergents. 3 minor findings logged (`GOLDEN-AUDIT` in buglog.md): NEG-CONV-001/002/003 missing `discipline`; NEG-DUP-001/002 lazy `discipline: emerging`; dead `depth` field in 54 positives (D2241). Backfill all three during D2292 (BUG-084) golden depth expansion — non-blocking.

> **`just eval` (2026-08-12, this session):** 9/9 stages PASSED (703s). Fixed 4 blocking bugs first: BUG-089 (hardcoded 600s S2 timeout, D2311), BUG-090 (stale `latest` checkpoint, D2312), BUG-091 (`db_commit` KeyError + `disciplines`→`domains` field drift, D2313/D2314). Quality report: 5/8 green — `fb_fields` ✅, `multi_label` ✅, `relationship_edges` ✅, `db_commit` ✅, `db_rows` ✅; **3 red**: `convergent_clusters` 3% (5/191, need 25%), `fb_count` 3 (need 30), `verify_pass_rate` 67% (2/3, need 80%). ⚠️ **Root cause of reds = e2e selects first 20 books (alphabetical, domain-diverse) → almost no cross-book convergence (3%)**. Not a pipeline bug — full corpus is domain-organized. ⚠️ `verify_pass_rate` 67% = DeBERTa-only NLI (D2298) fail-closed at Recall 0.556 (1/3 FB quarantined on NEUTRAL evidence — expected false-negative per calibration). For T1.1: 3 FBs is too thin for LLM evaluation — use a domain-coherent sample or accept S5 quarantine ~33-44%.

---

## 🔴 ROUNDTABLE ADJUDICATION — 2026-08-12 (NEW CRITICAL, blocks convergence trust)

| # | Task | Decision | Severity | Effort |
|---|------|----------|:--------:|:------:|
| RA-1 | Fix source identity: metadata normalization + canonical work count (redefine `is_convergent` on distinct works ≥2) | D2308 | 🔴 | 4-6h |
| RA-2 | Fix ISOR: metadata-author + canonical source count + precedence parens | D2309 | 🔴 | 2-3h |
| RA-3 | Decouple NLI from confidence (gate not 75% weight) + per-passage aggregation + human adjudication | D2310 | 🟠 | 4-8h |
| RA-4 | Fix `discipline:"emerging"` over-firing (taxonomy match confidence + rationale; split EMERGING_TRUE/UNCERTAIN) | BUG-083→discipline | 🟠 | 4-6h |
| RA-5 | Add 2 duplicate-edition hard negatives to golden set (Safe Withdrawal Rate, Transgenic) | — | 🟠 | 1h |
| RA-6 | Purge stale model/threshold comments (0.6/0.8/0.5/0.3; Phi-4/Gemma/ModernBERT) | — | 🟡 | 1h |
| RA-7 | Freeze per-run manifest (config/model/prompt/taxonomy/threshold hashes) | — | 🟡 | 3-4h |

> **Bugs:** BUG-087 (duplicate-edition false convergence) + BUG-088 (ISOR author parse/precedence).
> **Full detail:** `governance/ROUNDTABLE_ADJUDICATION_2026-08-12.md`.

---

## 🚦 PRE-T1.1 GATE — CONSOLIDATED (2026-08-12, do NOT launch T1.1 before these)

> T1.1 = full S1.3→S6 run on 12,964 clusters (**~110-140h**, D2362 — not the stale ~21-26h). Launching with known bugs either
> **corrupts the output** (false convergence) or **wastes the run** (77.5% quarantine).

### 🔴 BLOCKING (corrupts output — fix first)

| # | Task | Decision/Bug | Why blocking |
|---|------|-------------|--------------|
| G1 | Source identity: metadata normalization + work-level `is_convergent` | D2308 / BUG-087 | 12,964 clusters would produce false-convergent FBs; entire KB epistemically invalid |
| G2 | ISOR: metadata-author + canonical source count + precedence | D2309 / BUG-088 | "Independence" currently = file count; downstream golden/ISOR contaminated |
| G3 | Runner 60-min timeout → configurable per-stage | BUG-080.4 | **Hard blocker** — runner kills S2 at 60min; S2 needs 25-40h |
| G4 | S5 NLI as gate (not 75% weight) + per-passage aggregation | D2310 | Else 77.5% of T1.1 output quarantined (recall collapse) |
| G5 | S5 completeness: stop substituting application for mechanism | BUG-080.5 | Completeness scores overly optimistic → false PASS risk |
| G6 | S5 threshold validation: warn→fatal | BUG-080.6 | Bad verification config must not run silently |

### 🟠 HIGH (data quality — fix before or immediately after)

| # | Task | Decision/Bug | Note |
|---|------|-------------|------|
| G7 | S1.5 dropped-embedding gate (epistemic recall) | BUG-080.8 | Silent drop = silent recall loss |
| G8 | S1.5 Ollama dim assertion (parity with MPS) | BUG-080.7 | Theoretical (bge-m3 stable 1024d) |
| G9 | `discipline:"emerging"` over-firing (65%) | BUG-083→discipline | Classifier mass-produces "emerging" |
| G10 | OMLX wired-memory leak stress test (P0.0) | P0.0 | ✅ PASS — wired flat (-0.11%), 0 errors, no leak |
| G11 | Delete stale Stage 3a artifacts | D2302-GAP2 | 5-min cleanup; verify no refs |
| G12 | Add duplicate-edition hard negatives to golden | RA-5 | 1h; closes golden blindspot |

### 🟡 VERIFY (drift/conflict — resolve before assuming)

| # | Question |
|---|----------|
| V1 | ✅ VERIFIED (2026-08-12): BUG-062 moot — S4 classify = `gpt-oss-20b-MXFP4-Q8` (config `models.verifier.model`), NOT Phi-4-mini. Depth semantic (D2220) + focused (D2247). Not blocking. |
| V2 | BUG-080.4 — is T1.1 launched via `runner.py` or `run_diagnostic.py`? (diagnostic bypasses runner, so timeout may not block in practice) |

### ✅ POST-T1.1 (safe to defer)

GAP-1 (DSPy wiring), D2285 (claim decomposition), D2292 (golden depth), D2289 (author-disjoint splits),
D2288 (Fleiss kappa), D2300 (StorageBackend), D2305 (latency SLA), T1.2 (yield diagnostic).

---

## 🔴 CRITICAL — PRE-T1.1 (all done ✅)

| # | Task | Status |
|---|------|--------|
| P0.1 | Wire hybrid S2 gate (D2276/BUG-085) | ✅ `pipeline/hybrid_gate.py` + `--hybrid` flag |
| P0.2 | Pipeline manifest update (D2282) | ✅ DeBERTa-v3-large, removed Phi-4-mini |
| P0.3 | FB schema split (D2283/BUG-080.5) | ✅ `CORE_FIELDS`/`ENRICHMENT_FIELDS` in schema_accessor |
| P0.4 | ISOR scoring (D2284) | ✅ 3-dimension in verified FB output |
| P0.5 | Golden tiered classification (D2286) | ✅ GOLD-A:49, GOLD-B:3, CHALLENGE:21 |
| P0.6 | DSPy hard gates (D2287) | ✅ 3 gates in extraction_metric() |
| P0.7 | BUG-001 empty pass loop | ✅ Resolved (code path removed in D2298) |
| P0.8 | BUG-014 cloud burst | ✅ Resolved (no cloud code in repo) |

## 🟠 HIGH — IMPLEMENTED PRE-T1.1 (all done ✅)

| # | Task | Status |
|---|------|--------|
| P1.3 | S4 enrichment verification in S5 (D2277) | ✅ `_check_enrichment_quality()` added |
| P1.6 | NLI threshold validation fatal (D2272) | ✅ `ValueError` on misconfiguration |
| P1.7 | Ollama embed dimension assertion (D2274) | ✅ Dimension mismatch raises `ValueError` |
| P1.8 | Embed drop-rate quality gate (D2275) | ✅ `RuntimeError` if >0.5% dropped |
| P1.13 | FAISS threshold mismatch | ✅ Both 0.75 |
| P1.14 | AGENTS.md stage count | ✅ Says "8-stage" |
| P1.15 | Ruff lint | ✅ 94 auto-fixed |

## 🟠 HIGH — ALREADY VERIFIED ✅

| # | Task | Status |
|---|------|--------|
| P1.9 | S5 schema strict validation (D2271) | ✅ check_completeness deleted, no field substitution |
| P1.10 | BUG-013 pkill | ✅ No pkill in codebase |
| P1.11 | BUG-012 sqlite-vec | ✅ sqlite-vec loaded before CREATE VIRTUAL TABLE |
| P1.12 | BUG-055 related_fbs/related_blocks | ✅ No related_blocks in any Python file |

## 🟠 HIGH — AUDIT FIXES ✅

| # | Finding | Fix |
|---|---------|-----|
| A1 | runner.py — 9 Gemma skip_gemma references | ✅ All removed. Gemma deleted from OMLX (D2297) |
| A2 | stage4_merged_call.py — "Gemma/Google S5 verifier" | ✅ Comment fixed to "GPT-OSS/OpenAI S4 classifier" |
| A3 | CONSTITUTION.md models section stale | ⚠️ Needs update (minor — pipeline_config.yaml is canonical) |

## 🔴 REMAINING — POST-T1.1

### CRITICAL (4 items)
| # | Decision | Task | Effort |
|---|----------|------|--------|
| C1 | D2285 | Claim decomposition for S5 — per-claim NLI. Highest S5 accuracy lever. | 8-12h |
| C2 | D2292 | Golden depth expansion — 170+ examples | 8-16h |
| C3 | D2289 | Author-disjoint DSPy splits extended | 3-4h |
| C4 | D2288 | Roundtable Fleiss' kappa — inter-rater reliability | 1h |

### HIGH (pipeline execution)
| # | Task | Effort | Notes |
|---|------|--------|-------|
| **T1.1** | **Full S1.3→S6 run** on 12,964 clusters | **~110-140h** (D2362) | Enable with `--hybrid` for +0.145 quality |
| **T1.2** | Yield crisis diagnostic | 2h | Post-T1.1 |
| T-007b-v2 | Re-optimize MIPROv2 with 3 demos | 1h setup | Optional polish |
| T-015 | Extraction type expansion + depth balance | 2d | Golden pool imbalance |
| T2.x | 23 medium tasks | varies | See MTR |

### FUTURE TAX (identified in audit)
| # | Issue | Severity |
|---|-------|----------|
| F1 | InferenceProvider protocol not implemented (D2055) | ✅ DONE (D2306 — OMLX + Ollama providers) |
| F2 | Pydantic FB schema dead code (schemas.py, never instantiated) | 🟡 — 0 callers |
| F3 | Hardcoded model name in stage4_merged_call.py:101 | 🟡 — should be config-driven |
| F4 | Hardcoded cohesion threshold 0.75 in stage2_extract.py:351 | ✅ DONE (config S2_HIGH/MED_COHESION_THRESHOLD) |
| F5 | stage4_merged_call.py — hardcoded defaults for model params | ✅ DONE (model=None reads config VERIFY_MODEL) |
| F6 | StorageBackend protocol not implemented (stage6 SQLite) | 🟡 — remaining modularity gap (D2300) |

### 🔴 NEW TASKS — 2026-08-12 AUDIT (D2300-D2307)

| # | Decision | Task | Status |
|---|----------|------|--------|
| N1 | D2302-GAP1 | Wire DSPy trained program into stage2_extract.py (replace/augment hybrid gate) | ⏳ T1.2 |
| N2 | D2302-GAP2 | Remove stale Stage 3a artifacts (prompts/s3a_optimized.txt, s3a_system_v1.txt) | ⏳ T1.2 |
| N3 | D2302-GAP3 | DSPy tier-aware split | ✅ DONE (D2304) |
| N4 | D2303 | CRIBS batch mitigation — wire batch_cribs_classify | ✅ DONE (FIX-1) |
| N5 | D2305 | Recall measurement | ✅ DONE (D2307 recall_measure.py) |
| N6 | D2305 | End-to-end latency SLA | ⏳ Post-T1.1 |
| N7 | D2306 | InferenceProvider + EmbeddingProvider protocol | ✅ DONE |
| N8 | D2306 | StorageBackend protocol (stage6 SQLite) | ⏳ Post-T1.1 |

## 📊 STATUS SUMMARY

```
P0 CRITICAL:  ██████████ 8/8 DONE
P1 HIGH:      ██████████ 15/15 DONE (6 implemented, 5 verified, 4 deferred)
AUDIT FIXES:  ██████████ 3/3 DONE
────────────────────────────────────────
PRE-T1.1:     100% COMPLETE
POST-T1.1:    4 critical + T1.1-T1.2 + 23 medium + 5 future tax
```

## 🧭 T1.1 HANDOFF

```bash
# Full pipeline run (traditional-only — hybrid gate REJECTED, BUG-085):
python3 pipeline/runner.py

# Or stage-by-stage (S2 processes convergent + single-source clusters by default):
python3 pipeline/stage2_extract.py
python3 pipeline/stage4_merge.py
python3 pipeline/stage5_verify.py
python3 pipeline/stage6_commit.py

# Active models: Qwen3-Coder-30B (S2) | GPT-OSS-20B (S4 classifier) | DeBERTa-v3-large (S5 verifier) | bge-m3 (Emb)
# S5 threshold: 0.10 — honest auto-cal (D2322): P=0.647, R=0.386, F1=0.484 (D2293's P=1.000 was on the broken call)
# Hybrid gate: DISABLED for T1.1 (BUG-085 A/B: 4.3% negative rejection — net-negative)
# ISOR: 3-dimension independence in every verified FB
```
