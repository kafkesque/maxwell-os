# Maxwell OS — Buglog
> **D2478 (2026-08-27):** S4 parallelism A/B NEGATIVE — gpt-oss 128-expert MoE does NOT scale (1w 1.00x/100% → 2w 0.97x/75% → 3w 0.94x/75%; KV-dispatch thrash degrades discipline 25%). Parallelism is NOT quality-neutral for gpt-oss. **File-drift root cause FIXED**: `scripts/promote_cleaned.py` + integrity check #18 (`check_canonical_promotion`); promoted canonical `singleton_fbs.jsonl`→5,244 (229 empty-shell) + `checkpoint.jsonl`→8,402 (deduped+passage-cleaned). Guard verified FAIL→PASS. decisions.yaml → 466.
> **D2477 (2026-08-27):** Wired D2354 `batch_depth_classify` into stage4 (depth pre-pass, `depth_batch_enabled`). A/B (n=8): batch depth **2.69x, 100% agreement** (SHIP) vs batch CRIBS **2.67x but domain granularity degrades** (12% canonical exact-match, Jaccard 0.48) → `batch_enabled` REVERTED to false. Per-FB 27.5s→22.0s; quality-neutral ETA ≈48h. **DATA-DRIFT FINDING:** canonical `t11/checkpoint.jsonl` (8,410) + `t11/singleton_fbs.jsonl` (5,254, 446 empty-shell) were NEVER promoted from the cleaned `checkpoint.deduped.jsonl` (8,402) + `singleton_fbs.final.jsonl` (5,244, 229 empty-shell) — S4 reads the STALE files. decisions.yaml → 465.
> **D2475/D2476 (2026-08-27):** **D2475** — mechanism/boundary/consequence made PRINCIPLE-ONLY (config-first `shared_body`+`principle_only_body` in content_types.yaml; relaxed audit_s2/check_record/audit_s4_fields). Eliminates the 9-TI-skeleton false positives (3 TI × empty mechanism/boundary/consequence). **D2476** — `classify_model` stamp added (stamp_record optional param + stage4_merge stamps `classify_model=VERIFY_MODEL`; principle-only). decisions.yaml → 464.
> **D2474 (2026-08-27):** 20-residual drop/fill EXECUTED — fill 1 empty extraction_type (D2417 config default), drop 10 empty-elaboration principles (drop_manifest.jsonl), 3 TI empty-skeleton schema-fit-noted → `singleton_fbs.final.jsonl` (5,244). Empty-shell 229 singleton (70 PT empty-steps / 48 PI empty-actors / 111 TI empty-parameters) LEFT for S2 rerun (not back-filled — `parameters:[]` would falsely claim no-inputs, BUG-169). **Exhaustive conformance stress test** (`scripts/stress_test_s2_exhaustive.py`, 13,646 records × 15 cells → `stage4_merge/stress_s2_exhaustive/`): **464 hard gaps** = 225 stale single-source (pre-D2452) + 229 singleton empty-shell + 9 TI skeleton (3×3) + 1 convergent PT anomaly (BUG-166). New `scripts/audit_diverse_smoke.py` + D2452 regression guard (`test_omitted_s2_body_fields_get_typed_placeholders`). 146/146 tests green. decisions.yaml → 462.
> **D2463 (2026-08-25):** external-audit cross-exam (Qwen+ChatGPT vs commit `4aeeb6f`) → 3 remediations executed (golden fail-closed, OMLX cache gate, D2461 ghost closed) + 3 NEW bugs catalogued (BUG-177 C16 silent-error class, BUG-178 S6 Parquet C6, BUG-179 loader drift). `preserve_mid_system_cache=true` flagged UNVERIFIED (not a bug — one targeted check). None block the running S2.
> **D2463-followup (2026-08-26):** Claude external-audit cross-exam #2 (`claude0029.txt`) → 1 NEW bug (BUG-180 `mlx_provider.py` stub KV cache — dead code) + 1 NEW post-S2 lever (`singleton_batch_size` 4→8 A/B, ~17% total speedup, quality-gated). Claude claim #1 (cache-thrash) DISPROVEN for live state — cache off, 0 swap, flat 42–46/hr, ~4–7 tok/s = MoE ceiling (D2460 #2).
> **D2464 (2026-08-27):** singleton run COMPLETED (5,254 FBs / 1,018 NULL). Field-by-field schema audit → 1 NEW bug (BUG-181 singleton data-quality: evidence contamination + empty-shell non-principle + R14 non-homogeneous). MAXWELL-OS-AUDIT-RESPONSE.md (Claude audit) claim-by-claim verified: 10/12 findings confirmed TRUE, finding #4 (registry drift) now PARTIAL (D2461 fixed, D2454 still missing), finding #12 (C16 clean) superseded by BUG-177. C1/C22 precedence + CONSTITUTION date contradiction (finding #6) NOT yet tracked — logged below.
> **D2465-D2468 (2026-08-27):** BUG-181#3 FIXED (fail-closed S2 validation: empty-extraction_type repair via weakest-honest table + principle-elaboration requirement + singleton `_failed` path); BUG-181#4 DONE (singleton_run_manifest.json — 3-commit split explicit, stamps truthful); BUG-181#1 gate operationalized (scripts/audit_evidence_cleanliness.py → 515/5,254 = 9.8% contaminated); **D2454 WIRED** (pipeline/s4_golden.py + injection into all 4 S4 prompts, fail-closed); **BUG-177 FIXED** (ParallelMapError raise-by-default, NLIInferenceError + verification_error_type, model_lazyload explicit standalone); **BUG-178 FIXED** (Parquet tempfile→fsync→os.replace). 145/145 tests green. **S4 re-benchmark: 17.71s median / 19.02s mean per FB → S4-research §1 CONFIRMED (old ~30s baseline was cache-contaminated).** D2440 BLOCKED (alignscore/minicheck not installed + evals/nli_golden.jsonl missing).
> **D2469-D2470 (2026-08-27):** P1.3 gpt-oss cross-family FLAG wired into stage2_relabel_extraction_type.py (D2469, default-off, compiles + dry-run verified). G0 product scope DECIDED = filtered frontier 10,146; 176 older-commit singletons ACCEPTED (0 sentinel hits); BUG-181#1 DECIDED accept-and-flag + quarantine 29 severe; BUG-181#2 DECIDED sidecar-first (D2470). BUG-169 residual measured (31 single-source + 100 singleton TI empty parameters). decisions.yaml → 458.
> **D2473 (2026-08-27):** BUG-179 FIXED (AGENTS.md loader + MASTERPROMPT delegate_guard phantom); BUG-180 addressed (mlx_provider deprecation banner); C1/C22 precedence clarified; CONSTITUTION footer date fixed; ext-audit #5 FIXED (check_stage_order relative-order assert). decisions.yaml → 461.
> **D2472 (2026-08-27):** BUG-181#1/#2 + BUG-169 FIXED (root-cause + post-hoc). text_cleaner.py gained clean_evidence_passage() (strips Pandoc/calibre residue clean_markdown() missed) wired into stage1_3_prefilter + fix_singleton_quality.py (1,819 passages cleaned; 217 PT→principle / 11 PT→TI / 70 flagged; 100 TI flagged parameter_origin=technique). Output singleton_fbs.fixed.jsonl. 145/145 tests green. decisions.yaml → 460.
> **D2459 (2026-08-25):** BUG-175 FIXED (root cause + backfill). Phi-4-mini hallucination sentinels (`_AUTHOR_SENTINELS` in `book_metadata.py`: "string"/"Unknown"/type-names — case-sensitive so legit `Anonymous`/`Various` survive) blanked at cache-load AND guarded in `resolve_book_metadata()`; `_AUTHOR_JUNK` extended (etc./unknown/domains); `scripts/backfill_author_sentinels.py` rewrote the 10 contaminated metadata entries (crash-safe C6, never fabricates: `Thinknetic` derived, 9 → `Unknown Author`). Singleton resume HARDENED: transient `None` results no longer mark a cluster processed (re-enters on resume — previously silently dropped forever). 140/140 tests (9 new). SEE ALSO: BUG-175 entry below for full detail.
> **D2456 (2026-08-24):** Forensic audit found Ollama had the IDENTICAL dual-install clusterfuck as OMLX (homebrew 0.30.0 crash-looping on `bind: address already in use` vs app 0.32.15 serving 11434) — the exact D2455 pattern. FIXED: uninstalled homebrew ollama, archived stale plist, autoremoved orphaned brew mlx/mlx-c (pip mlx verified untouched). BLINDSPOTS fixed: status.py now reports VERSIONS (was "UP" only — drift silent); get_ollama_version added; guard generalized to `guard_stacks_single_source.py` (covers OMLX+Ollama, config-first) with a critical false-positive fix (app-owned CLI shim `/opt/homebrew/bin/omlx`→`~/.omlx/bin/omlx` is LEGIT; now only flags shims resolving into Cellar/opt). NEW `scripts/monitor_stacks.py` one-panel monitor (status+version+min_version drift+single-source) wired into `just preflight` + `just stacks`. 126/126 tests, 10/10 integrity, config audit clean. OMLX server did a GRACEFUL shutdown at 23:23:11 mid-audit (not a crash; recovered clean, no data loss, settings preserved).
> **D2455 (2026-08-24):** OMLX single-source-of-truth + permanent re-infection guard. ROOT CAUSE of the "two-version clusterfuck": TWO OMLX installs (GUI app 0.6.2 vs homebrew 0.5.1) both claimed port 11435 AND both rewrote `~/.omlx/settings.json`. The homebrew launchd agent (`com.maxwell.omlx.plist` → `/opt/homebrew/bin/omlx serve --max-concurrent-requests 3 --no-cache`) crash-looped every ~11s (`[Errno 48] Address already in use`) and clobbered scheduler settings (silently reverting `max_concurrent_requests=6`→`3`). FIXED: uninstalled homebrew omlx 0.5.1 (kept GUI app 0.6.2 as single source of truth), archived all 6 stale launchd plists, added `scripts/guard_omlx_single_source.py` (fail-loud on forbidden binary/stale agent/port conflict), wired into `just health`+`just preflight`. QUALITY: batching byte-identical to solo (temp=0.0 greedy; empirical). Ollama dual-install (`com.ollama.ollama` + stale `homebrew.mxcl.ollama`) flagged, not touched.
> **D2453 (2026-08-24):** S2 singleton crash-safety + resume. `process_singletons` wrote FBs ONLY at the end (plus circuit-breaker bailout) and declared `processed_ids`/`singleton.segids` but never read/wrote them — a kill/logout/OOM mid-run lost all in-memory FBs. FIXED: resume (load prior FBs + segids, skip processed) + `_write_singleton_checkpoint` incremental crash-safe writes every 25 batches. Live 2-run smoke: resume preserved 4/4, viable 0/4, 0 re-extraction. Also captured external-audit **#14** (OMLX "health endpoint lies": `/v1/models` returns catalog, `model_lazyload.py --status` reports 41.2GB when ground-truth RSS=20.4GB) and **#5** (`check_stage_order` doesn't verify sequence) as tracked items below. `just preflight` no longer calls deprecated `sync_decisions.py` (the bogus-"No heading" entry source).
> **D2452 (2026-08-24):** S2 singleton-readiness hardening + fail-closed schema enforcement. (1) WIRED the D2437 prefilter into `process_singletons` (was standalone — the singleton pass read all 35,122 singletons and ignored the 6,317 EXTRACT / 28,805 SKIP verdicts; now fail-LOUD if `singletons.prefiltered.jsonl` absent). (2) FIXED **BUG-173 enforcement gap** — live singleton smoke (smoke_singleton_ti_d2452) reproduced a `process_template` with 602-char `elaboration` + `steps=None`; the D2448 fix was prompt-only. Added `_blank_elaboration_for_non_principle` (builder-level) + typed s2_body_field placeholders (`[]`/`False`/`""`). Re-smoke: `elaboration:""` + `steps:[]` on non-principle. (3) FIXED latent `load_golden_single_source` truncation (pos.pop() dropped rarest roles GE/PI first → now round-robin). (4) Added `stage0_5_extract_metadata` to pipeline_config stages (external-audit #6). (5) Added `just s2-singletons` + `just s2-singletons-prefilter`. 121/121 tests green.
> **Last updated:** 2026-08-24 (D2437/D2438: S4 preflight+smoke+stress harness — 28 tests + live 7-FB OMLX smoke; `scripts/render_s4_visual.py` for human-readable S4 output; **BUG-167 taxonomy "discipline promotion" REVERTED** — added 3 labels as disciplines that already exist as domains, breaking D2422 disjointness, caught by CI `test_taxonomy_disjointness.py`; dedup + passage sweep DONE; 110/110 tests green)
> **D2439/D2440 (2026-08-24):** 6-LLM external SOTA audit (claude/qwen/chatgpt × 0021/0023/0024) claim-by-claim verified against live repo. Accept-deferred: Leiden swap (already documented D2168). Accept-P2: contextual retrieval, cross-encoder reranker after RRF, DuckDB. Reject: SetFit (category error), CRAG (contradicts D2298), ColPali/ColBERTv2 (bloat), "DSPy missing" (exists-but-unwired — see BUG-168). Single convergent action → **D2440: run AlignScore+MiniCheck through existing `calibrate.py` harness vs DeBERTa.**
> **D2441/D2442 (2026-08-24):** external-audit A+B executed. D2441: public leak redacted (929-title manifest, 1147 provenance hits → `[]`, runtime glob) + C12 hardcoded-path scanner made recursive (162 files) + 9 hardcoded paths fixed. D2442: **evidence-tier preservation** — `is_convergent`/`origin` added to schema+S4+S6+SQLite (was silently dropped → BUG-171); `scripts/freeze_run_manifest.py` + `scripts/audit_s4_fields.py`. Live smoke: 6-FB diverse batch (2 principles classified + 4 routed, 0 failures), evidence-tier lands correctly. 110/110 tests green.
> **D2443/D2444/D2445 + F2 (2026-08-24):** forensic-audit F1/F2/F3 + render fix. D2443 = provenance carry-through (citation/source_authors/source_diversity/primary_source carried S2→S4→S6 — BUG-172 FIXED). D2444 = difficulty-map "inversion" verified NOT-a-bug. D2445 = render_s4_visual.py made content-type-aware. F2 = non-principle sidecars re-stamped with S4 run traceability (routed_by_stage, gen_model preserved). Live 4-record smoke: F1 lands on FB, F2 lands on sidecars; 35 S4 tests green; integrity 15/17; audit_s4_fields clean except BUG-169 (TI parameters).
> **D2446 (2026-08-24):** divergent-5type field crosscheck vs `content_types.yaml`. FB fully compliant; non-principle sidecars carry correct shared skeleton + type-specific body + stamps + provenance (F1 verified) but are missing classification/discovery/versioning/runtime enrichment (BUG-170 expanded). Two drifts documented NOT-fixed: (1) elaboration non-empty on PT/GE (BUG-173), (2) `source_cluster` singular vs `source_clusters` plural (semantically distinct, not a bug). Verdict: NO code change now — all enrichment is gated on `commit_non_fb_types: false` (enriching uncommitted JSONL = bloat + new LLM surface); defer to post-BUG-165.
> **D2448 (2026-08-24):** S2 prompt hardening + commit-frontier verdict (factoring singleton extraction). FIXED at the prompt: `_build_body_schema_text()` now makes `elaboration` PRINCIPLE-ONLY (BUG-173) and `parameters` REQUIRED for tool_instruction (BUG-169); propagates to SINGLE_SOURCE + SINGLETON + SINGLETON_BATCH. BUG-170 reframed as a commit-frontier decision: sequenced B→A (document sidecars now, commit non-principle later) — Path A is infeasible now (no S6 tables, dead `commit_non_fb_types`, no non-principle cross-ref producer, no non-principle S5 verification).
> **D2449 (2026-08-24):** singleton-builder schema drift UNIFIED + source-filename noise sanitized. Root cause of singleton/single-source drift: `_singleton_result_to_fb` was a fork that dropped `elaboration`, bibliographic provenance (`source_authors`/`citation`/`primary_source`) and ALL R14 stamps — so singleton FBs shipped `source_authors: null` (author was in the filename) and un-stamped records. FIXED by extracting shared `_enrich_provenance()` + `_sanitize_books()` and wiring BOTH builders (BUG-174). Added `sanitize_source_book()` (config/filtering.yaml `source_noise`, C12) stripping `(z-library.sk, 1lib.sk, z-lib.sk)` / `(z-lib.org)` / `-- Anna's Archive` / `-- <32-hex>` from source_books/source_text/citation. GUARD: `tests/test_stage2_singleton_parity_d2449.py` (5 tests). `procedural_skill:null` / `prerequisite_fbs:[]` in smoke = correct pre-S4.5 defaults (S4.5 not run in smoke).
> **D2450 (2026-08-24):** golden-set PT-vs-TI contrastive expansion (task #12) + content-type conformance audit. Added 3 `tool_instruction` positives (SS-POS-007/008/009: SQLAlchemy/MongoEngine/Superlinked) — the exact framework-API patterns the singleton smoke mislabeled as `process_template` 4/4 — each with "NOT process_template" rationale (BUG-166). Fixed principle example (SS-POS-001) to non-empty `elaboration` (D2448 rule). `golden_single_source_max` 9→12. Consistency fix: `_capture_type_specific_fields` now ALWAYS emits string s2_body_fields (empty "" when absent) — previously omitted empties (PT `prerequisite` sometimes absent). New `scripts/audit_content_type_contract.py` + `tests/test_content_type_contract.py` verify all 5 content types conform to content_types.yaml (S2 + S4 contract). Result: zero structural gaps; only BUG-170 deferred enrichment remains.
> **D2451 (2026-08-24):** golden-set contrastive negatives + S4 classification golden (config-first). Added SS-POS-010 (descriptive_model principle — principle ≠ always causal, targets 4/4 causal over-claim), SS-POS-011 (HUMAN debugging method → PT NOT TI, reverse of PT-vs-TI), SS-NEG-004 (bare one-off event → NULL, over-split guard for singleton thin passages). `golden_single_source_max` 12→15, `golden_single_source_negative` 3→4; fixed formatter to show ALL negatives (was hardcoded [:3]). Authored `config/golden/stage4_golden.yaml` — first config-driven S4 classification golden (4 depth levels), replacing hardcoded inline depth examples in `CLASSIFY_SYSTEM_PROMPT`. GUARD: `tests/test_stage4_golden_contract.py` validates S4 golden against content_types.yaml + canonical taxonomy. S4 golden AUTHORED + test-validated but NOT wired into the 4 classification prompts → D2452. 121/121 tests green.
> **D2451 follow-up (2026-08-24, live OMLX smoke):** first smoke 3/7 — found TWO residual gaps the deterministic tests can't see: (1) over-split — thin events (printer/release/audit) still fabricated PI/PT despite SS-NEG-004; (2) PT-vs-TI — React frontend-component pattern still mislabeled PT. FIXED: added SS-POS-012 (React → TI) + SS-NEG-005/006/007 (deployment/audit-mention/personnel → NULL) + sharpened SS-POS-005 rationale ("PI = case study OF a method"). `golden_single_source_max` 15→19, `golden_single_source_negative` 4→7. **Re-smoke 7/7 PASS.** `DROP_THIN`/`DROP_ANECDOTE` completeness gate remains the hard backstop for over-split.
> **D2451 follow-up (2026-08-24, 50-record prefiltered smoke):** larger real-passage smoke (50 prefiltered EXTRACT singletons, seed 42) found the golden had NO "principle + normative_heuristic" example, so the model defaulted normative rules (precautionary principle, market-entry strategy) to `causal_mechanism`. FIXED: added SS-POS-013 (principle + normative_heuristic). `golden_single_source_max` 19→20. **Re-smoke: causal_mechanism 10→7 (−30%), normative principle 4→7; Precautionary Principle + Market Entry both flipped causal→normative correctly.** Conformance matrix: all 5 content_types carry every required field, zero missing/extra; self-exam issues = NONE. 121/121 tests green.
> **Prior (2026-08-23):** forensic audit: S4/S5/S6 stage-drift 2,830 vs 8,410; relabel scope = single-source-only CONFIRMED; BUG-164 = 11 records not 6; BUG-149 FIXED in code; R1.3 = 1,161 not 1,036; **BUG-146/P0.x ✅ RECOVERED** — single-source rerun already re-processed the 9,950 gated, only `cluster_11649` failing; **BUG-166** — single-source is 99.9% non-convergent & generic; **D2437** — deterministic value-filter built: `scripts/score_single_source.py` (post-hoc) + `scripts/prefilter_clusters.py` (pre-LLM, dual-use single-source+singletons) + `config/filtering.yaml`)
> **Next review:** After T1.1 full S1.5→S6 run

---

## 🟢 BUG-185 — 2026-08-28 — S4 depth classifier collapses 97.5% to "domain" — FIXED (D2483, 2026-08-28)
- **Symptom:** Live depth probe (n=40 principle FBs, `batch_depth_classify` via gpt-oss-20b) → **39 "domain", 1 "cross-domain", 0 "universal", 0 "specialized"**. The depth distribution is dominated by the "domain" default.
- **Root cause (CONFIRMED, D2483):** the depth prompt literally instructs `DEFAULT to "domain" unless the mechanism clearly transcends a single discipline.` — a decision-policy bias, not few-shot under-coverage. A/B (n=20 samples) reproduced 90% domain on V0; pure bias-removal over-corrects to 10% domain (the D2365 over-assign-cross-domain failure); the contrastive variant lands balanced (~50% domain) with a defensible boundary.
- **Fix (D2483, SHIPPED):** `stage4.depth_prompt_variant: v3_contrastive` (now the enabled default) in `config/pipeline_config.yaml` → `_apply_depth_prompt_variant()` in `stage4_merged_call.py` strips the bias + adds forced 4-way choice + contrastive boundary anchors to BOTH `DEPTH_FOCUSED_PROMPT` and `DEPTH_BATCH_SYSTEM`. A/B-verified on both paths: FOCUSED (n=20) V0=90% domain → V3=50% balanced, speed-neutral; BATCH (n=20, production `batch_depth_classify`) golden accuracy 3/5→5/5 (recovers "Feedback Loop"→cross-domain, "Backpropagation"→specialized), speed-neutral 1.88→1.95s/FB, no over-assignment (80% domain — avoids the V1 over-correction to 10% domain / D2365 failure).
- **Status:** 🟢 FIXED — enabled (`depth_prompt_variant: v3_contrastive`). 9 S4 tests green; golden contract test passes post-flip; both focused + batch paths A/B-confirmed.
- **Files:** `config/golden/stage4_golden.yaml`, `pipeline/stage4_merged_call.py`, `pipeline/pipeline_paths.py`, `config/pipeline_config.yaml`, `scripts/benchmark_s4_depth_prompt_ab.py`
- **Source:** Live probe 2026-08-28 (`temp/probe_depth_dist.py`) + A/B (`scripts/benchmark_s4_depth_prompt_ab.py`, D2483)

## 🔴 BUG-188 — 2026-08-30 — S4 `checkpoint.jsonl` truncated at 2GB: dense O(n²) `related_fbs` adjacency lost ~5,300 FBs
- **Symptom:** S4 completed (CONDITIONAL_SUCCESS, "FBs generated: 7874") but `t11/checkpoint.jsonl` is EXACTLY 2,147,483,647 bytes (2³¹−1) and ends mid-record (`…"relationships": ["do`). Only ~2,552 of 7,874 FBs survive; **~5,322 (~68%) lost**. Non-principle sidecars are intact (PT 1,701 / PI 66 / GE 13 / TI 382 — unbloated, complete).
- **Root cause:** `_compute_fb_relationships()` (`stage4_merge.py:856-953`) builds a PAIRWISE O(n²) upper-triangle adjacency. `domain_overlap` fires on the ubiquitous `emerging` fallback domain (29.4% discipline-emerging) + avg 2.4 domains/FB → the graph is near-COMPLETE: **32,335,994 edges over 7,874 FBs** (~8,200 `related_fbs` entries per FB). Each entry ≈96B → **~6.5GB total**. `_write_s4_checkpoint` builds ONE giant `"\n".join(...)` string + `safe_write` → silently truncated at the 2GB boundary, and the process still printed CONDITIONAL_SUCCESS (no exception — C16 violation).
- **Fix (P0, before S5):** (1) **cap `related_fbs`** — top-k semantic (cosine) neighbors only, NOT all domain/discipline/source overlaps; exclude `emerging` from `domain_overlap`; or write edges to a SEPARATE adjacency file rather than inline per-FB. (2) **large-file safe write** — stream JSONL (never one multi-GB string); assert post-write size == expected (fail-loud, C16). (3) **recover lost FBs** — re-run S4 (only realistic path; the incremental pre-`related_fbs` checkpoint was overwritten). The depth pre-pass (7,880) is intact and reusable to skip the ~4h depth phase.
- **Status:** ✅ FIXED (code, verified 2026-08-30) — S4 re-run required to recover ~5,322 lost FBs (depth pre-pass `checkpoint.jsonl.depth.json` reusable to skip ~4h depth phase).
- **Fix applied (D2487):** `io_guard.safe_write` now loops partial writes (`_write_all_bytes`) and asserts post-write size == expected (fail-loud `IOError`, C16); new `io_guard.safe_write_jsonl` streams records line-by-line and verifies byte AND record count (no multi-GB join); `compute_fb_relationships` bounded to O(n·k) via a per-FB top-k cap (`related_fbs_max_neighbors=20`, priority `semantic_near > source_crossover > discipline_overlap > domain_overlap`) plus `related_fbs_exclude_domains=[emerging]`. Verified by `/tmp/s4_bug188_test.py` (round-trip, partial-write loop 10×, shrink-guard, cap max_deg≤5).
- **Files:** `pipeline/stage4_merge.py` (`_compute_fb_relationships`, `_write_s4_checkpoint`), `pipeline/io_guard.py` (`safe_write`)
- **Source:** S4 post-completion forensic audit 2026-08-30

## 🟠 BUG-187 — 2026-08-29 — S4 FB record emits 7 fields not declared in `schemas.FB` + `jargon` key omission (schema drift, NON-BLOCKING)
- **Symptom:** Live-run forensic audit (t11 checkpoint, n=2,545 records) — `schemas.FB` declares 56 fields, but every S4 FB record carries 59 keys. 7 keys are NOT in the FB model: `classification_error` (singular), `classify_model`, `evidence_passages`, `evidence_passages_shown`, `is_summary`, `manifest_hash`, `source_segments`. Additionally `jargon` is OMITTED from the dict when empty (568/2,545 records) → 2 distinct key-sets across the checkpoint.
- **Root cause:** three-way misalignment between `content_types.yaml` (config-first canonical contract, D2269/D2349), `schemas.FB` (pydantic output model), and the emitters (`stamp.py`/`stage4_merge.py`/`stage2_extract.py`). All 7 extra keys are LEGITIMATE fields declared/consumed elsewhere but NOT modelled in `schemas.FB`: (a) `source_segments` + `evidence_passages` — declared in `content_types.yaml` `metadata.provenance` (and `schemas.Segment`/`schemas.GoldenFB`), consumed by S5 NLI + S6; (b) `is_summary` + `classify_model` — declared in `content_types.yaml` `classification` (D2089/D2476), consumed by S6; (c) `classification_error` (singular) — D2351 failure-reason string (distinct from the plural `classification_errors`), consumed by `stage5_verify.py:614` and persisted as a SQLite column at `stage6_commit.py:132`; (d) `evidence_passages_shown` — "subset actually shown to LLM", emitted by `stage2_extract.py:2486/2799`, read by `schema_accessor.py:78/358`; (e) `manifest_hash` — stamped by `stamp.py:158` (D2282) but absent from BOTH `content_types.yaml` `metadata.stamps` AND `schemas.FB` (double-gap; `taxonomy_version` is likewise stamped but missing from `metadata.stamps`). `jargon` (`schemas.py:200`, `str | None`) is OMITTED from the dict when `None` (intentional per `_serialize_jargon` docstring) → 2 key-sets.
- **Impact:** NON-BLOCKING — no downstream consumer validates FB against the strict pydantic model, so the extra fields are tolerated (run is clean: 0 truncated, 0 dup fb_id, 0 name collisions, 0 classification errors, checkpoint↔segids↔log in exact sync). But it is silent schema drift: `content_types.yaml` (config) and `schemas.FB` (code) disagree on the field contract, which is precisely the accumulation C27 "zero future tax" is meant to prevent.
- **Fix (post-S4, do NOT pause):** (1) ADD all 7 fields to `schemas.FB` (none are droppable — all consumed downstream): `source_segments: list[str]`, `evidence_passages: list[str]`, `is_summary: bool`, `classify_model: str | None`, `classification_error: str | None` (D2351), `evidence_passages_shown: list[str]`, `manifest_hash: str | None`; (2) ADD `taxonomy_version` + `manifest_hash` to `content_types.yaml` `metadata.stamps`; (3) always emit `jargon` (write `None` instead of omitting the key) at the `stage4_merge.py` jargon block; (4) reconcile `object_version` (content_types.yaml) ↔ `fb_version` (code).
- **Status:** 🟠 defer post-S4 (non-blocking; live run is healthy).
- **Files:** `pipeline/schemas.py`, `pipeline/stage4_merge.py`
- **Source:** S4 live-run forensic audit 2026-08-29 (n=2,545)

## 🟢 BUG-186 — 2026-08-28 — `is_specialized` is a dead classification field: Anytype consumer always False — FIXED (D2485, 2026-08-28)
- **Symptom:** S4 forensic probe (n=12 principles, `forensic_probe_0828`) → `is_specialized` absent from every FB record (0/12). Yet `stage6b_anytype_push.py` reads `fb.get("is_specialized", False)` → the Anytype product property is **always False** (silent constant).
- **Root cause:** `is_specialized` is asked-for in the classify prompt (`stage4_merge.py`), declared in `stage4_golden.yaml` (5 examples), and parsed by `stage4_merge.py`, but it is (a) NOT in `schemas.FB` (55 fields, no `is_specialized`) and (b) never written into the FB record. Depth is now a separate 4-way focused call (D2220/D2247/D2477), so the merged-call `is_specialized` is redundant and dropped.
- **Verdict (D2484):** `is_specialized` ⟺ `depth == "specialized"` (confirmed by the 5-example golden set). Best fix = **derive deterministically from `depth`** (add the field to `schemas.FB` + persist `is_specialized = (depth == "specialized")`), and **strip the redundant prompt instruction** — do NOT add it as a separately-classified field (the merged-call signal is the low-accuracy 38% path; a redundant classified field adds zero info + a new cross-field consistency invariant, the BUG-151 class).
- **Fix (D2485):** `schemas.FB` gains `is_specialized: bool` (derived, default False); `stage4_merge.py` persists `is_specialized = (depth == "specialized")` and removes the dead `class_data.get("is_specialized", ...)` read. The redundant classify-prompt instruction is intentionally left in place for this pass (stripping it changes the merged-call JSON contract → deferred, must be A/B tested, not done blind pre-launch).
- **Status:** 🟢 FIXED (D2485, 2026-08-28) — derived from depth; Anytype consumer now reads a correct value.
- **Files:** `pipeline/schemas.py`, `pipeline/stage4_merge.py`, `pipeline/stage4_merged_call.py`, `pipeline/stage6b_anytype_push.py`, `config/golden/stage4_golden.yaml`
- **Source:** Forensic S4 probe 2026-08-28 (D2484); fixed D2485

## 🟢 BUG-181 — 2026-08-27 — Singleton output schema-complete but content-incomplete + evidence contamination — CLOSED (resolved D2470/D2471/D2475, no longer blocks S4)
- **Symptom (field-by-field audit of the 5,254-record `singleton_fbs.jsonl`, run completed 2026-08-27 00:08):**
  1. **Evidence contamination:** 558/5,254 (10.6%) `evidence_passages` carry raw EPUB→MD conversion artifacts (`.title-page-contributor-primary-block} ::::`, `:::inline-image:::`, `{align="baseline" height=…}`, `{bgcol…}`); 23 severe (>15% artifact-char ratio). Record #1's evidence is 100% a title-page CSS fragment (zero semantic content). All records carry exactly 1 passage.
  2. **Empty-shell non-principle types:** 298/1,139 (26%) `process_template` have empty `steps`/`trigger`/`prerequisite`/`done_condition`/`failure_mode`; 48/97 (50%) `process_instance` missing `instance_text`/`actors`/`outcome_*`; 100/307 (33%) `tool_instruction` missing `parameters`; 6/8 `growth_edge` missing `body`/`category`/`status`/`priority`. (Keys present per D2452 — values empty; this is classification/extraction quality, NOT schema breakage.)
  3. **Skeleton gaps:** 3 `tool_instruction` with empty `mechanism`/`boundary`/`consequence`; 10 `principle` with empty `elaboration` (violates "REQUIRED for principle"); 1 record with empty `extraction_type` (`fb_id 3383e2ad…`, "Citizen Juries and Panels", PT).
  4. **R14 non-homogeneous:** 3 `pipeline_commit` values in one file (`0a0e0c3`×5,078 / `3a4b0e9`×141 / `d8ba816`×35) — resume-across-code-change, not a single homogeneous run.
- **Impact:**
  - #1 is most consequential: S5 DeBERTa NLI verifies against `evidence_passages` — garbage-in ⇒ garbage entailment scores, and "verbatim source quote" provenance is FALSE for contaminated passages.
  - #2 means ~26% of non-principle singletons are content-empty shells; ties to Path A / D2448 (43% dead-end at S4).
- **Fix (pre-S4/S5/S6):**
  - #1: pre-S5 evidence-cleanliness gate (skip/re-clean passages over an artifact-ratio threshold) OR re-clean at `stage1_3_prefilter`/`text_cleaner`.
  - #2: treat empty-shell non-principle as re-extract/relabel signal, or accept singleton thin-types as sidecar-only and stop counting them complete.
  - #3: fail-closed validation for `elaboration` (principle) + non-empty `extraction_type`.
  - #4: re-stamp the 176 older-commit records or record a `run_group` field.
- **Status:** 🟢 CLOSED (D2470 sidecar-first + D2471 root-cause + D2475 principle-only skeleton) — does NOT block S4. 48-residual empty-shell → BUG-182 (deferred, post-S4).
- **Source:** 2026-08-27 — S-tier RAG engineer singleton schema verification (field-by-field audit)
- **D2465 (2026-08-27) FIX-PROGRESS:**
  - **#3 FIXED** — fail-closed validation: `_normalize_role_fields` now repairs empty `extraction_type` via the config-driven weakest-honest table (D2417); `validate_fb_output` rejects empty `extraction_type` + principle-without-`elaboration`; singleton path returns `{"_failed"}` for principle-without-elaboration (never committed; counted + resume-safe). 145/145 tests green.
  - **#4 FIXED (documentation)** — `singleton_run_manifest.json` written next to the output; the 3 `pipeline_commit` values (0a0e0c3×5,078 / 3a4b0e9×141 / d8ba816×35) are made explicit; **not re-stamped** (R14 truthfulness); the 176 older-commit records flagged for optional provenance re-check before S4 (3a4b0e9 predates the D2459 BUG-175 fix).
  - **#1 GATE OPERATIONALIZED** — `scripts/audit_evidence_cleanliness.py` scans checkpoints for conversion artifacts (exit 1 on contamination). Re-run on singleton_fbs.jsonl: **515/5,254 (9.8%) contaminated, 29 severe**. **DECIDED (D2470):** accept-and-flag + quarantine the 29 severe (>15% artifact ratio) at S5; NOT full re-clean. Contamination = deterministic EPUB→MD converter artifacts (calibre markers / CSS selector residue / inline style), NOT hallucination — fix `text_cleaner`/`stage1_3_prefilter` for the NEXT corpus pass.
  - **#2 DECIDED (D2470) — sidecar-first.** Empty-shell non-principle (298 PT / 48 PI / 100 TI / 6 GE) documented in sidecar (skeleton + route + evidence kept); empty body fields filled later via cross-examination against existing TIs/PTs (recipe-builder workflow). No re-extraction; empty steps do NOT block S4 routing.
  - **#2 ROOT-CAUSE (D2471):** empty-shell PTs are NARRATIVE descriptions of a framework/concept mislabeled as `process_template` (evidence is story/definition text — "Dan Kennedy's irresistible offers…", "good overviews tell stories…" — not a step enumeration). Steps are genuinely ABSENT from the source passage, not dropped by the extractor; we do NOT fabricate them (provenance honesty). Two signals: (a) role mislabel (descriptive → PT), (b) singleton fragmentation (steps live in other unclustered passages). Cross-examination fills steps from VERIFIED TIs/PTs only.

## 🟢 BUG-184 — 2026-08-28 — S4 batch depth pre-classification aborts ENTIRELY on one truncated batch (intermittent gpt-oss truncation) — FIXED (2026-08-28)
- **Symptom:** full S4 run logged `⚠️ Batch depth FAILED: depth batch missing fb_index=3 (chunk start=488)` — gpt-oss-20b returned only 3 of 4 depth objects for the batch at FB index 488, and `batch_depth_classify` raised, aborting the WHOLE 7,880-FB pre-classification. `_pre_depth` stayed empty → main loop fell back to SERIAL `classify_depth_focused` for every FB.
- **Root cause (VERIFIED 3-factor):** (1) **token budget** — `batch_depth_classify` read `depth_max_tokens=1024` (single-FB budget) for a 4-FB batch, so the Nth JSON object truncated; (2) **CoT budget mismatch** — it omitted `thinking_budget`, so `call_omlx` fell back to the MERGED-call budget (256) instead of the proven depth budget (128), emitting more CoT that ate the output budget; (3) **non-resilient** — it raised `DepthClassificationError` on the FIRST missing `fb_index`, aborting the whole pre-pass.
- **Fix (committed):**
  - `config/pipeline_config.yaml` + `pipeline/pipeline_paths.py`: new `stage4.depth_batch_max_tokens: 2048` (batch headroom) → `S4_DEPTH_BATCH_MAX_TOKENS`.
  - `stage4_merged_call.batch_depth_classify`: passes `thinking_budget=VERIFY_DEPTH_THINKING_BUDGET` (128, parity with the single call); per-chunk retry (×1) then per-chunk serial `classify_depth_focused` fallback for MISSING indices only — a truncated chunk no longer aborts the pre-pass.
  - `stage4_merge.run_stage4`: depth pre-pass chunk-iterates + writes an incremental `.depth.json` checkpoint after every chunk (crash-safe, resume-aware).
- **Verified (live OMLX):** 8-FB batch → 8/8 valid depth labels, 1.99 s/FB (vs 6.23 s/FB serial = ~3.1× faster); retry path recovers a truncated chunk; persistent truncation falls back to serial ONLY for missing indices (unit-tested).
- **Impact (fixed):** depth pre-pass no longer aborts; serial fallback only for the rare still-truncated chunk.
- **Status:** 🟢 FIXED (committed; full-run relaunch pending)
- **Source:** 2026-08-28 — S4 full-run live trace (depth batch failure in `s4_run.log`)

## 🟢 BUG-183 — 2026-08-27 — S4 intra-stage resume re-loads a STALE completed checkpoint when cluster IDs overlap across a corpus change — FIXED (2026-08-28)
- **Symptom:** launching `stage4_merge.py` into a directory holding a stale COMPLETED S4 checkpoint (906MB, 2,830 FBs from Aug 20, no `.segids` — the D2424 completed-run marker) caused the D2370 resume block to reload it and treat 1,990/2,000 sampled clusters as "already processed". The run would have skipped 99.5% of clusters, emitting stale Aug-20 classification.
- **Root cause:** the D2424 "0-overlap → discard" guard only fires when processed cluster IDs DON'T overlap the new targets. But the D2434 relabel + D2479 rerun changed record *labels* without re-running S1.5 clustering, so cluster IDs are STABLE across the corpus change (1,990/2,000 overlap). The resume logic therefore cannot distinguish "crashed run to resume" from "stale completed run from a prior corpus" when IDs overlap.
- **Fix (committed):** the resume block now stores an **S2-input fingerprint** (`_s2_input_fingerprint` = sha256 of `pipeline_run_id` + S2 checkpoint + singleton file size/mtime_ns) in `.state.json`, and on resume compares it to the freshly-computed fingerprint — a mismatch (S2 corpus regenerated in place) discards the stale checkpoint AND its `.depth.json` pre-pass, regardless of cluster-ID overlap. Covers the D2479 in-place relabel that D2424's ID-overlap guard missed.
- **Verified (end-to-end):** live SIGINT → checkpoint → resume smoke test — checkpoint wrote fingerprint to `.state.json`; resume correctly skipped 2/3 processed clusters + reused the pre-computed `.depth.json`; completed run cleared all sidecars. Exit code 0, 3/3 FBs, 0 failures.
- **Status:** 🟢 FIXED (committed; full-run relaunch pending)
- **Source:** 2026-08-27 — S4 full-run launch forensic check

## 🟡 BUG-182 — 2026-08-27 — 48 singleton empty-shell deterministically re-return empty after S2 rerun — OPEN (model-level, not S4 blocker)
- **Symptom:** after the D2479 targeted S2 rerun (229 singleton empty-shell dropped + re-extracted at temp=0.0), **48 of 229 came back empty-shell again** — 32 TI empty-parameters, 11 PT empty-steps, 5 PI empty-actors. Source passages for sampled cases carry genuine content (VS Code debugger steps, text-to-SQL LangChain discussion, regex-generation, stack push/pop methods, WIMP-automation prose, "five questions" statistical-skepticism framework), so the text is NOT void — the model deterministically returns empty type-specific body fields for these passages.
- **Impact:** 48 records remain content-empty shells in `singleton_fbs.jsonl`. Not a pipeline/schema bug (fields present per D2452, values empty — the documented BUG-181#2 "narrative mislabeled as process_template" class + TI/PT thin-fragments). Does NOT block S4 routing (S4 classifies content_type + depth; empty body ≠ crash). Blocks full value for those 48 at S5/S6.
- **Root cause:** temp=0.0 ⇒ deterministic re-extraction — same prompt + same passage ⇒ same empty output. Re-running the same extractor will NOT fill them. The deeper mechanism is a **prompt collision**: D2449 says "leave fields empty when the passage does not provide them" while the same prompt says "no extractable object → route=NULL"; the model resolves the ambiguity by emitting a typed empty shell instead of NULL. The deterministic guards (`_code_role_guard` D2457 / `_narrative_role_guard` D2471) already converted 217 PT→principle + 11 PT→TI pre-rerun; the 48 are the residual.
- **Post-hoc analysis (2026-08-27, record-by-record + live guard re-run):**
  - **28/32 TI** = technique-type (empty `parameters`, non-empty `syntax`): code/DSL snippets (Max/MSP, D3.js, Processing, Argo, TouchDesigner, `toString()`) where formal named parameters genuinely do not apply — `parameters=[]` is CORRECT, not a bug (D2471). Fix = provenance stamp `parameter_origin=technique`, NOT fabrication.
  - **4/32 TI** = empty `parameters` AND empty `syntax`: 2 are evidence-passage MISMATCH ("SPSS Data Entry" whose evidence is Monster.com job-search prose; "openFrameworks Project Structure" whose evidence is RGBA-pixel concept text) → quarantine (BUG-160 relevance class); 2 are genuinely-thin (MIDI↔Max/MSP, After Effects expressions — real content the model failed to type) → accept-and-flag.
  - **11/11 PT** = `_has_step_language(evidence) == True` on ALL of them → `_narrative_role_guard` **correctly** kept them as process_template (genuine-but-fragmented: step language present, enumeration lives in other passages). NOT relabelable — the guard already did its job. Accept-and-flag per D2470 sidecar-first; fill later via cross-examination.
  - **5/5 PI** = no `_code_role_guard`/`_narrative_role_guard` applies to process_instance (a guard GAP, not a mislabel). Thin case studies (PT Cruiser, SAP Qualtrics, Monster.com) with derivable-but-unemitted `actors`. Low value — accept-and-flag; a `_pi_role_guard` is a future hardening item, not a today-fix.
- **Fix (revised, deterministic-only — NO re-extraction):** (a) DONE — `parameter_origin` now derived at the S2 builder boundary (`_capture_type_specific_fields`, shared by single-source + singleton builders): `parameters` non-empty → `"api"`; empty `parameters` + non-empty `syntax` → `"technique"`; both empty → absent. This lands on ALL future batches automatically (no post-hoc pass, no drift). (b) deterministic post-hoc sweep on the 48: stamp `parameter_origin` on all 270 TI (238 api / 28 technique / 4 absent), quarantine the 2 evidence-mismatch TIs, accept-and-flag the 11 PT + 5 PI + 2 genuinely-thin TI. (c) optional future: add "NULL-if-not-enumerable" prompt instruction + `_pi_role_guard` — deferred, non-blocking.
- **Future-batch impact:** the `parameter_origin` fix is builder-level and shared, so every future singleton/single-source run self-stamps TI provenance with zero extra model cost; no flag can be lost again (the D2472 `fix_singleton_quality.py` flag lived only in an unpromoted `.fixed.jsonl` intermediate — root cause of the BUG-169 "flag loss"). Re-running the same extractor on these 48 at temp=0.0 is provably a no-op; do not attempt it.
- **Status:** 🟡 OPEN (does not block S4; `parameter_origin` provenance fix applied in `stage2_extract.py`, 48-record post-hoc sweep scoped)
- **Source:** 2026-08-27 — D2479 targeted rerun verification + record-by-record post-hoc forensic analysis

## 🟡 BUG-180 — 2026-08-26 — mlx_provider.py system-prompt KV cache is dead stub code — OPEN (spike)
- **Symptom:** `pipeline/providers/mlx_provider.py` docstrings claim "System prompt KV caching (<50ms TTFT after first call)", but `_cache_system_prompt()` stores `self._system_caches[system] = (system_tokens, [])` — an EMPTY KV list never populated. `_build_prompt()` returns the identical full string `f"{system}\n\n{prompt}"` on cache hit AND miss; `cache_hit` is bookkeeping only, never passed as `prompt_cache=` to `mlx_lm.generate()/stream_generate()`. The comment even notes "MLX batch_generate supports prompt_caches for true KV reuse" but it is never wired.
- **Impact:** the only path that would ELIMINATE (not amortize) the golden-reprefill tax is half-built and silently no-ops. No functional harm today (direct-MLX path already deferred per D2055), but the docstring overstates capability.
- **Fix (parked):** real prefix-KV caching via `mlx_lm.models.cache.make_prompt_cache` + wire `prompt_cache=` into generate calls — gated on fixing the D2055 HF-cache-path bug + re-verifying JSON reliability. Future spike, not a today-fix.
- **Files:** pipeline/providers/mlx_provider.py
- **Status:** 🟡 OPEN (parked as spike — does not block S2)
- **Source:** 2026-08-26 — Claude external-audit cross-exam #2 (claude0029.txt claim #4, CONFIRMED)

## 🟢 BUG-177 — 2026-08-25 — C16 silent-error class (parallel.py + S5 NLI + model_lazyload fallback) — FIXED (D2467, 2026-08-27)
- **Symptom:** Three production paths swallow errors contrary to C16 ("exceptions must log AND raise"):
  1. `pipeline/parallel.py parallel_map()` catches `TimeoutError`/`Exception`, prints, appends `None`, returns the list. `None` is ambiguous downstream (looks like "processed but empty").
  2. `pipeline/stage5_verify.py _nli_pair_scores()` returns `(0.0, 0.0, 0.0)` on any exception — an infra/model error becomes indistinguishable from a genuine "not entailed" verdict.
  3. `pipeline/model_lazyload.py` falls back to hardcoded `http://localhost:11435` + `sk-maxwell-local` if importing centralized OMLX config fails (C12 + C16).
- **Impact:** silent data-quality loss (worker results dropped as `None`), observability loss (NLI runtime errors look like semantic negatives), and a silent endpoint/key swap in production.
- **Note:** the golden-loader half of this class (`load_golden_*` → `([], [], 0)`) is FIXED by D2463 (fail-closed raise).
- **Fix (queued):** (1) `parallel_map` → typed failure object only on explicit opt-in, default raise aggregate; (2) `_nli_pair_scores` → raise typed `NLIInferenceError` while keeping QUARANTINE at the stage boundary + record `verification_error_type`; (3) `model_lazyload` → remove silent fallback, add explicit `--standalone` mode.
- **Files:** pipeline/parallel.py, pipeline/stage5_verify.py, pipeline/model_lazyload.py
- **Status:** 🟢 FIXED (D2467, 2026-08-27) — `ParallelMapError` raise-by-default (`on_error="collect"` opt-in); `NLIInferenceError` + `verification_error_type`; `model_lazyload` explicit `MAXWELL_STANDALONE=1`.
- **Source:** 2026-08-25 — external-audit cross-exam (ChatGPT #4/#9/#21)

## 🟢 BUG-178 — 2026-08-25 — S6 Parquet export not crash-safe (C6) — FIXED (D2468, 2026-08-27)
- **Symptom:** `pipeline/stage6_commit.py export_parquet()` writes the snapshot directly with `pq.write_table(table, str(parquet_path), compression="snappy")` — no tempfile→fsync→os.replace. A kill mid-write leaves a partially-written/truncated `.parquet` snapshot that a downstream reader will fail on.
- **Impact:** persistent-output corruption on forced process kill (SQLite checkpoint writes are already crash-safe; Parquet is not).
- **Fix (queued):** write to a unique temp file → `fsync` → `os.replace()` into place + add a checksum/manifest entry.
- **Files:** pipeline/stage6_commit.py
- **Status:** 🟢 FIXED (D2468, 2026-08-27) — `export_parquet` tempfile→fsync→os.replace (C6), temp cleaned on failure.
- **Source:** 2026-08-25 — external-audit cross-exam (ChatGPT #17)

## 🟢 BUG-179 — 2026-08-25 — AGENTS.md loader stale + tools/delegate_guard.py phantom — FIXED (D2473, 2026-08-27)
- **Symptom:** `AGENTS.md` still declares "DECISION-LOG.md (D2000–D2310)" and "config/decisions.yaml — 299 decisions" (reality: D2463 / 450). The v2.0 loader block still imports `tools.delegate_guard` / `tools.pipeline_paths` / `tools.safe_delete` etc., but the `tools/` layout was migrated to `pipeline/` (v3.0) — `tools/delegate_guard.py` does NOT exist (the mandated preflight gate is a phantom; the real gate is `pipeline/omlx_delegate.py` D2344).
- **Impact:** agents bootstrapped from the stale loader get obsolete governance + a non-existent preflight import.
- **Fix (queued):** regenerate AGENTS.md knowledge-source metadata from canonical files (D2463 / 450 / D2000–D2463) + drop the `tools/delegate_guard` phantom from the v2.0 block. Add CI asserting documented decision count/range == DECISION-LOG/decisions.yaml.
- **Files:** AGENTS.md
- **Status:** 🟢 FIXED (D2473, 2026-08-27) — AGENTS.md loader regenerated (D2000–D2484 / 472); `tools/delegate_guard.py` phantom dropped (`tools/delegate_safe.py`).
- **Source:** 2026-08-25 — external-audit cross-exam (ChatGPT #1, Qwen #2)

## 🟢 BUG-176 — 2026-08-25 — tool_instruction misclassified as process_template (code framed procedurally) — FIXED (D2457)
- **Symptom (smoke matrix 5×3, `singleton_fbs.jsonl`):** the singleton "R Data Import and Analysis Workflow" was classified `content_type=process_template` with an **empty body** (`trigger=""`, `prerequisite=""`, `steps=[]`, `done_condition=""`, `failure_mode=""`). Its evidence is R code — `setwd("C:/...") dir() data<-read.csv("...") View(data)` — which is unambiguously a `tool_instruction`, not a human how-to method.
- **Root cause (D2457):** the passage is *framed* procedurally ("it is important for you to understand how to **import** the data into R") but its *substance* is executable code. The LLM latched onto the procedural framing and chose `process_template`, then could not extract human "steps" from code → empty PT body. There was **no deterministic code-detection signal** anywhere in the pipeline to steer code→`tool_instruction`; the PT-vs-TI prompt rule is text-only and easily overridden by "how to…" framing. Systemic scope: 46/796 (5.8%) process_templates in the full S2 corpus carry code markers in their evidence (e.g. "SQLite Setup and Configuration", "User Input Loop Control Pattern", "PublicPrivateExample").
- **Fix (D2457, three layers):** (1) `config/filtering.yaml` `code_markers` (46 R/Python/JS/SQL/CLI signals, C12); (2) `stage2_extract.py` `detect_code_in_text()` + `_code_hint()` — injects a deterministic "⚠️ CODE DETECTED → tool_instruction NOT process_template" annotation into the singleton (per-item + batch) and single-source prompts when ≥2 distinct markers match; (3) `_code_role_guard()` — post-hoc deterministic fail-safe that reclassifies a code-laden passage the model still labeled `process_template` with empty `steps`, deriving best-effort `tool_name`/`syntax`/`example` from the evidence and stamping `code_role_corrected=true`. Also added golden anchor SS-POS-014 (R data import → tool_instruction) to `stage2_fewshot_single_source.yaml`.
- **Impact:** empty-bodied process_templates = ontologically wrong objects (code stored as human method); downstream S4 routes them to `process_templates.jsonl` and they never get TI body fields.
- **Files:** config/filtering.yaml (code_markers), pipeline/stage2_extract.py (detect_code_in_text/_code_hint/_code_role_guard + wiring in both builders), config/golden/stage2_fewshot_single_source.yaml (SS-POS-014), tests/test_stage2_singleton_batch.py (5 tests).
- **Status:** ✅ FIXED — 131/131 tests; live OMLX call on the exact passage now returns `content_type=tool_instruction, tool_name=R, syntax="setwd(), dir(), read.csv(), View()"`; guard unit-test reclassifies the historical misclassification deterministically. Residual (46 PTs with code markers in full corpus) → re-run S2 single-source on those, or post-hoc reclassify via `scripts/score_single_source.py`.
- **Source:** 2026-08-25 — operator report ("R data import is not tool instruction") + smoke-matrix 5×3 singleton examination.

## 🟢 BUG-175 — 2026-08-25 — `author="string"` in provenance: Phi-4-mini metadata hallucination on 10 books (253 S2 records) — FIXED (D2459)

- **Symptom (smoke matrix 5×3, `scripts/smoke_matrix_5x3.py`, run `smoke_matrix_5x3b`):** 253 S2 records (10 distinct books) carry `source_authors[].author = "string"` and a malformed `citation` (e.g. `"string (Generative Design_ Visualize...)"`). Visible in the rendered `visual.md` under `singleton · principle — Generative Design Programming Logic` and `Data Import and Analysis Workflow`.
- **Root cause:** `config/checkpoints/book_metadata.jsonl` had 10 entries where `author` is a placeholder (`"string"` × 7, `"Unknown"` × 3), all with `extraction_method: llm:Phi-4-mini-instruct-8bit`. This is the **BUG-053 hallucination pattern** — Phi-4-mini returned a type-name `"string"` instead of a real author on open-ended filename→author extraction. The heuristic fallback (regex) never ran because the LLM path "succeeded" with a non-empty but bogus value.
- **Impact:** provenance/citation contamination on 253/8,402 S2 records (~3.0%). Affects `citation`, `source_authors`, and `primary_source` derivation downstream (S4→S6). Not an S2/S4 code defect — a stage0_5 metadata data-quality defect.
- **Fix (D2459, applied 2026-08-25):** (1) `_AUTHOR_SENTINELS` + `is_sentinel_author()` in `book_metadata.py` — type-name/placeholder set, **case-sensitive** so legit `Anonymous`/`Various` survive; blanked at cache-load (read boundary) AND guarded in `resolve_book_metadata()` (defense-in-depth) → a sentinel can never propagate again; (2) `_AUTHOR_JUNK` extended (`etc.`/`unknown`/domain suffixes) so the filename heuristic no longer derives junk authors from parens (`( etc.)`, `(ColorPsychology.org)`); (3) `scripts/backfill_author_sentinels.py` — crash-safe (C6), idempotent, dry-run-capable backfill of the 10 entries → deterministic heuristic result (`Thinknetic` for Mental Models via paren convention; `""` → `Unknown Author` at read time for the other 9; **never fabricates**); (4) singleton resume hardening in `process_singletons` — transient `None` results no longer mark a cluster processed (they re-enter on resume; previously silently dropped forever).
- **Verification:** 140/140 tests (9 new in `tests/test_book_metadata_sentinels_d2459.py`); resolver returns `Unknown Author`/`Thinknetic`, never `string`; backfill idempotent (2nd run: 0 changes); config audit clean; decisions 446 synced.
- **Residual:** the 253 S2 records in `checkpoint.deduped.jsonl` keep their baked-in provenance until an optional post-hoc re-stamp (cosmetic; blocks nothing — deferred to post-BUG-165). Phi-4-mini stays excluded from open-ended author extraction (R5/delegate-rule).
- **Files:** pipeline/book_metadata.py, scripts/backfill_author_sentinels.py, knowledge pipeline/checkpoints/book_metadata.jsonl, tests/test_book_metadata_sentinels_d2459.py, pipeline/stage2_extract.py
- **Status:** ✅ FIXED (D2459)
- **Source:** 2026-08-25 — smoke-matrix 5×3 visual examination.

## 🟢 BUG-174 — 2026-08-24 — singleton builder drops elaboration + provenance + R14 stamps (schema drift vs single-source) — FIXED (D2449)
- **Symptom:** `_singleton_result_to_fb` produced records with `source_authors: null` even when the author was embedded in the source filename ("Algorithms to Live By … (Brian Christian, Tom Griffiths)"), no `citation`/`primary_source`, no `elaboration`, and NO R14 stamps (`schema_version`/`gen_model`/`pipeline_commit`/`taxonomy_version`/`manifest_hash`/`pipeline_run_id`/`created_at`). Single-source/convergent FBs (via `_build_fb_from_result`) had all of them.
- **Root cause:** the singleton builder was a **forked** code path that never called `stamp_record`, never ran the BUG-061 author/citation enrichment, and dropped `elaboration` (the prompt requested it, the builder discarded it).
- **Fix (D2449):** extracted shared `_enrich_provenance()` + `_sanitize_books()` helpers and wired BOTH builders to them; `_singleton_result_to_fb` now emits `elaboration` + `evidence_passages_shown` + provenance + `stamp_record`. Provenance/stamping/sanitization can no longer drift between S2 paths.
- **Status:** ✅ FIXED — `tests/test_stage2_singleton_parity_d2449.py` (5 tests) asserts the full canonical core+stamp+provenance field set + de-noised source_books. Remaining: singleton path still skips `validate_fb_output` (tracked follow-up).

## 🟢 BUG-173 — 2026-08-24 — `elaboration` non-empty on PT/GE contrary to ontology ("principle-only") — FIXED (D2448, S2 prompt)
- **Symptom:** divergent-5type smoke: `process_template.elaboration` = 520 chars (render-workflow context), `growth_edge.elaboration` = 402 chars (hypothesis context). Ontology (`content_types.yaml` `core_body`) declares `elaboration` is "PRINCIPLE-ONLY (empty for PT/PI/GE/TI)". `process_instance` and `tool_instruction` were correctly empty — over-emission was PT/GE-only.
- **Root cause:** `_build_body_schema_text()` (S2) listed `elaboration` as a shared-skeleton key and only said "REQUIRED for principle" — it never told the model to leave it EMPTY for non-principle types, so the model opportunistically filled it for narrative types (PT/GE).
- **Fix (D2448):** the S2 body-schema note now says "elaboration is PRINCIPLE-ONLY … For process_template/process_instance/growth_edge/tool_instruction, elaboration MUST be empty (\"\")." Propagates to all three S2 prompts (SINGLE_SOURCE, SINGLETON, SINGLETON_BATCH) since they all append `_S2_BODY_SCHEMA`. No re-extraction needed — lands on all future runs, including singleton extraction.
- **Status:** ✅ FIXED (prompt-level, D2448) + **builder-level enforcement (D2452)** — `_blank_elaboration_for_non_principle` blanks `elaboration` for PT/PI/GE/TI in BOTH builders (`_build_fb_from_result` + `_singleton_result_to_fb`). Live singleton smoke (2026-08-24) reproduced the regression (602-char elaboration on a PT) and confirmed the builder backstop now emits `""` even when the model ignores the prompt. No longer "verify at next run" — it is now schema-guaranteed.

## 🟢 BUG-172 — 2026-08-24 — S2 provenance (citation/source_authors/source_diversity/primary_source) dropped at S4 — FIXED (D2443)
- **Symptom:** S2 emits `citation`, `source_authors`, `source_diversity`, `primary_source` on all 5,002 deduped records, but S4's FB-record builder only carried `source_books`/`source_ids`/`source_segments`/`evidence_passages`. The four bibliographic/epistemic-diversity fields were silently lost at S4→S6.
- **Root cause:** same pattern as BUG-171 — the S4 FB dict copies a fixed field list and omitted the four; `FB` schema had no such fields; S6's INSERT column map had no such columns.
- **Impact:** agents could not cite or rank sources by distinct-source count (`source_diversity`) without re-reading source books.
- **Fix (D2443):** added the 4 fields to `FB` (schemas.py), S4 FB record (stage4_merge.py), SQLite (stage6_commit.py CREATE TABLE + INSERT + `_migrate_add_column`) + Parquet `jsonlike_fields`; extended `integrity_check.py` `key_fields`; updated `content_types.yaml` `metadata.provenance`.
- **Status:** ✅ FIXED — verified 66 cols == 66 placeholders; FB pydantic constructs; init_db+insert_fb round-trip writes correct values.

## 🟢 BUG-171 — 2026-08-24 — evidence tier (is_convergent/origin) silently dropped at S4→S6 — FIXED (D2442)
- **Symptom:** `is_convergent`/`origin` were derived in the S4 cluster wrapper but never carried into the FB record, `FB` schema, or SQLite. Stale S4 checkpoint confirmed `is_convergent=None` on all 2,830 records.
- **Root cause:** the S4 FB-record builder (the dict at `stage4_merge.py` FB construction) copied structural provenance into the cluster wrapper but not the FB dict; the `FB` schema had no such field; S6's explicit INSERT column map had no such column.
- **Impact:** the keep-list strategy's convergent-vs-single-source distinction (the entire reason we chose 4,892 over 2,641) would be forfeited — retrieval could not tier "2+ sources agree" vs "1 source asserts."
- **Fix (D2442):** added `is_convergent` (bool) + `origin` (str) to schemas.py FB, carried into the S4 FB record, persisted via 2 SQLite columns (+ auto-heal migration). Live smoke verified: `is_convergent=True/origin=convergent` and `False/single_source` land correctly; S5 `vfb=dict(fb)` pass-through confirmed.
- **Status:** ✅ FIXED — live-verified end-to-end; 110/110 tests green.

## 🟡 BUG-170 — 2026-08-24 — non-principle content types (PT/PI/TI/GE) routed but NOT classified/enriched — OPEN (deferred, minor)
- **Symptom (EXPANDED by D2446 crosscheck):** the sidecar records carry the correct shared skeleton + type-specific body + stamps + provenance, but are missing the FULL metadata contract that principles get. Missing per sidecar:
  - **classification:** `depth`/`discipline`/`domains`/`evidence` (S4 routes to sidecars but skips the CRIBS classify call — only principles are classified).
  - **discovery:** `keywords` (CRIBS-only, never generated for non-principles).
  - **versioning:** `fb_version` (initialized 1 on principles, absent on sidecars).
  - **runtime:** `usage_count`/`feedback_score`/`feedback_count` (initialized 0/None/0 on principles, absent on sidecars). `last_retrieved_at` is intentionally None until first retrieval on BOTH paths (runtime layer, not S4).
  - **present & correct:** stamps (R14) + provenance (citation/source_authors/source_diversity/primary_source all carried — F1 ✅).
- **`source_cluster` singular vs `source_clusters` plural:** sidecars keep S2's `source_cluster` (singular string = the single origin cluster id); the principle FB uses `source_clusters` (plural list = clusters merged at S4). These are SEMANTICALLY DISTINCT fields, NOT a bug — normalization (origin→list) happens at commit time alongside the enrichment above.
- **Impact:** latent. `commit_non_fb_types: false` means S6 never persists sidecars, so no row lands with empty enrichment today. If flipped true WITHOUT this work, SQLite `DEFAULT` would backfill `usage_count`/`feedback_count`/`fb_version` but `domains`/`discipline`/`depth`/`evidence`/`keywords` would be NULL (data-quality gap, not a crash).
- **Reframe (D2448):** this is NOT a standalone bugfix — it is the enrichment half of a **commit-frontier decision**: do non-principle types become first-class committed KB objects, or stay documentation-only sidecars? Verified blockers to the "commit" path (Path A) that do NOT exist yet:
  - S6 has **no non-principle tables** (`fbs` + `fbs_fts` + `vec_fbs` only); `commit_non_fb_types` is **dead config** (defined in `pipeline_paths.py`, never read by `stage6_commit.py`).
  - Non-principle cross-reference fields (`consulted_fbs`, `fb_query_domain`/`fb_query_intent`, `parent_pt_id`, `parent_fb_ids`, `promoted_to_*`) have **no producer** — `stage4_5_enrich.py` derives `prerequisite_fbs`/`contradicts_fbs`/`procedural_skill` for FBs only.
  - Non-principle S5 verification (NLI) does not exist (principles-only).
  - → Path A is **infeasible now**; it requires those three pieces as one coherent work item.
- **Verdict (D2448):** sequenced **B→A** — document (sidecars) now, commit later. Trigger to revisit A: after BUG-165 (S4→S5→S6 re-run on principles) validates the principle foundation, AND the non-principle cross-ref derivation + S6 tables + S5 verification are built together. Do NOT build S6 non-principle tables on the unvalidated principle path.
- **F2 (2026-08-24):** the "stale stamps" half is now FIXED — sidecars re-stamped with S4 run traceability (`pipeline_run_id`/`pipeline_commit`/`routed_by_stage`) while preserving S2 `gen_model`. The "not classified/enriched" half stays deferred per the B→A verdict.
- **Status:** 🟡 OPEN — commit-frontier decision (D2448); enrichment deferred to post-BUG-165, atomic with the Path A build-out.
- **Files:** pipeline/stage4_merge.py (routing path), pipeline/stage6_commit.py (no non-principle tables), pipeline/stage4_5_enrich.py (FB-only edges), config/pipeline_config.yaml (`commit_non_fb_types`)

## 🟡 BUG-169 — 2026-08-24 — TI `parameters` field missing on single-source tool_instruction — FIX-APPLIED (D2448), verify at rerun
- **Symptom:** the only TI in the diverse smoke batch ("B&B booking tool", single-source) is missing `parameters` (None) — a required field in the D2323 TI `s2_body_fields`. All other TI fields (tool_name/platform/description/syntax/output/example/caveats) present.
- **Root cause:** single-source S2 extraction omitted `parameters` for this tool. Confirmed an S2 DATA gap, NOT an S4 code defect — S4 passes S2 fields through verbatim.
- **Impact:** minor; single-source content, 1 of 143 TI records. Field audit (`scripts/audit_s4_fields.py`) flags it correctly.
- **Fix (D2448):** the S2 body-schema note now makes `parameters` REQUIRED for `tool_instruction` ("extract every input/argument … emit [] ONLY if the passage clearly shows the tool takes no inputs; never omit the key"). This prevents the omission at extraction time (no re-extraction needed for future runs).
- **Status:** 🟡 FIX-APPLIED (D2448 prompt + builder typed-placeholder) — verify `parameters` present on the full 143-record TI corpus during the BUG-165 rerun.
- **Residual (2026-08-27 measured):** 31/143 (21.7%) single-source TI + 100/307 (32.6%) singleton TI still have EMPTY `parameters` (key present via typed-placeholder `[]`, value empty). D2448 made it prompt-required but the post-D2448 singleton pass still emits 33% empty — a content-completeness gap, not schema. Verify/fill at BUG-165 rerun (or accept empty-parameters TIs as code-snippet instructions).
- **Root-cause (D2471):** 73/100 (73%) empty-parameters singleton TIs have code-like evidence (def/import/class/SELECT/pip/etc.) — they are code-snippet / prompt-engineering TECHNIQUES where formal named parameters do not apply; the "how-to" lives in `syntax`. Verdict: NOT a bug — an ontology nuance (technique-type TI vs formal-API TI). Post-hoc fix = accept + document (fabricating parameters violates provenance honesty).
- **Flag-loss root cause (2026-08-27):** the D2472 `parameter_origin=technique` flag was stamped ONLY by `scripts/fix_singleton_quality.py` into an intermediate `knowledge pipeline/t11/singleton_fbs.fixed.jsonl` that was never promoted to the canonical `stage2_extract/t11/singleton_fbs.jsonl`; the D2479 in-place rerun therefore rewrote canonical without it (the flag was never there to lose). **Fix (applied):** `parameter_origin` is now derived deterministically at the S2 builder boundary in `_capture_type_specific_fields` (shared by both builders) — `parameters` non-empty → `"api"`, empty `parameters` + non-empty `syntax` → `"technique"`, both empty → absent. No model, no post-hoc pass, cannot drift again.
- **Files:** config/content_types.yaml (TI s2_body_fields), scripts/audit_s4_fields.py, pipeline/stage2_extract.py (`_capture_type_specific_fields`)

---

## 🟠 BUG-168 — 2026-08-24 — `pipeline/dspy_trainer.py` exists but is NOT wired to any stage — OPEN (built-not-wired)
- **Symptom:** the 6-LLM SOTA audit (Qwen 0022) claimed "DSPy is the missing SOTA solution." Verified FALSE: `pipeline/dspy_trainer.py` (MIPROv2 optimizer, `ConvergentExtraction` signature) already exists. But `grep dspy pipeline/stage2_extract.py pipeline/runner.py` → **0 references**. DSPy is a standalone harness, not the production extraction path.
- **Root cause:** same built-not-wired pattern as BUG-085 (hybrid gate) — the optimizer was validated standalone (D2250) but never integrated into `stage2_extract.py`.
- **Impact:** zero — no data corruption, no silent failure. It is dead/vestigial compute surface until wired. But it creates a false impression of "DSPy-optimized extraction" in external audits and wastes review attention.
- **Fix:** either (a) wire `dspy_trainer.py` output into `stage2_extract.py` as the few-shot prompt source (D2250 follow-up), or (b) archive it under `archive/` to stop external audits tripping on it. Do NOT prioritize over BUG-165.
- **Status:** 🟠 OPEN — P2, post-BUG-165.
- **Files:** `pipeline/dspy_trainer.py`, `pipeline/stage2_extract.py`, `pipeline/runner.py`
- **Source:** 6-LLM SOTA audit verification 2026-08-24 (Qwen 0022 claim cross-check).

---

## 🟢 BUG-167 — 2026-08-24 — premature taxonomy "discipline promotion" broke D2422 disjointness — FIXED (reverted)
- **Symptom:** `tests/test_taxonomy_disjointness.py` failed: domain∩discipline overlap = `{graphic design, data visualization, organizational behavior}` (in addition to `emerging`).
- **Root cause:** task #3 (BUG-150 discipline promotion) added `graphic design` / `data visualization` / `organizational behavior` as new DISCIPLINE canonicals, but all three already exist as DOMAIN canonicals (`graphic design` = Visual Practice domain, `data visualization` = Digital & Interactive domain, `organizational behavior` = Business & Strategy domain). This created dual-listing — exactly the structural ambiguity D2422/BUG-151 forbids (a model can emit the label into either field and pass validation).
- **Impact:** would have silently re-opened the BUG-151 cross-kind ambiguity; `is_valid_discipline()` and `is_valid_domain()` would both accept the same string.
- **Fix:** reverted the 3 duplicate discipline entries. Promotion remains gated on re-measuring BUG-150 `discipline=emerging` on a FRESH full-corpus S4 (per the task register — do NOT promote against the stale 2,830-record S4).
- **Status:** ✅ FIXED — domain∩discipline = `{emerging}` only; `test_taxonomy_disjointness.py` green.

## 📌 D2438 — 2026-08-24 — S4 preflight + smoke + stress test harness + visual renderer
- **What:** `tests/test_stage4_preflight_smoke_stress.py` (28 tests) exhausts S4's deterministic surface:
  - `--only-fb-ids` allow-list fail-closed (missing → exit 1, empty → exit 1, no `fb_id` field → exit 1, 0-match → exit 1).
  - content-type routing (PT/PI/GE/TI → sidecar files; explicit `content_type` beats `route` fallback).
  - taxonomy exact/synonym/emerging + cross-kind collision (`user experience design` → `user experience` domain / `human-computer interaction` discipline).
  - name normalization + collision; classification validation; difficulty/temporal/jargon derivation.
  - live OMLX smoke on a diverse 7-FB batch: 3 principles classified (depth cross-domain/domain), 4 non-principle routed, 0 failed, 0 classification errors.
- **Also fixed (D2438):** the "Non-principle cluster" log line printed CUMULATIVE PT/PI/TI counts across prior clusters (misleading) — now prints the per-cluster split.
- **Visual examinability:** `scripts/render_s4_visual.py` renders `stage4_merge/{run_id}/checkpoint.jsonl` + PT/PI/GE/TI sidecars into a readable Markdown report (`visual.md`).
- **Status:** ✅ DONE — full suite 110/110 green, config audit clean (no drift).

---

## 🟢 BUG-165 — 2026-08-23 — S4/S5/S6 stage drift: 2,830 records vs S2's 8,410 — CLOSED (moot: S4→S6 re-run against current 13,604-record S2; no longer blocking)
- **Symptom:** `stage4_merge/t11/checkpoint.jsonl` = 2,830 records, `stage5_verify/t11/checkpoint.jsonl` = 2,830, `stage6_commit/t11/` = EMPTY. S2 `checkpoint.jsonl` = 8,410 (2,649 convergent + 5,761 single-source). S4/S5 carry `pipeline_commit=b14462f` (created 2026-08-19) vs S2's `7e48f36` (2026-08-18) — an OLDER code state.
- **Root cause:** the P1.2/P1.3 relabel (D2434/D2435) rewrote `extraction_type` across the full 8,410 S2 records, but S4/S5/S6 were **never re-run** after the single-source expansion + relabel. Everything downstream of S2 is frozen at ~34% of the current corpus.
- **Impact:** the entire discipline/domain/depth classification (BUG-150's 38.4% `emerging`), name truncation (BUG-149's 176), and verification/commit layers are operating on stale data. Any downstream conclusion (discipline distribution, causal share, PASS/QUARANTINE counts) is invalid until S4→S6 is re-run on the 8,410-record S2.
- **Fix (CRITICAL, before any S4-classification work):** re-run S4→S5→S6 against current S2 checkpoint after P0.x gated recovery + R1.4 dedup. Do NOT tune BUG-150 discipline promotion against the stale 2,830-record S4 — re-measure on the full corpus.
- **Status:** 🟢 CLOSED — moot once S4→S5→S6 re-runs against current 13,604-record S2 (the fix was always "re-run downstream"; nothing else blocks).

## 🟢 BUG-166 — 2026-08-23 — single-source S2 output is ~99.9% non-convergent & largely generic — CLOSED (resolved D2470 G0 scope = filtered frontier 10,063 records; re-scope decided)
- **Symptom (measured on t11 checkpoint = 8,410 records):** convergent vs single-source split by content_type:
  - `principle`: 2,648 convergent / 4,615 single-source
  - `process_template`: **1** convergent / 795 single-source
  - `process_instance`: 0 / 204
  - `tool_instruction`: 0 / 143
  - `growth_edge`: 0 / 4
  - **Non-principle types are 99.9% single-source (1,146/1,147).** Only ONE convergent process_template exists ("Render Queue Workflow").
- **Root cause:** the single-source second pass (D2345) extracts per-book passages with no cross-source convergence requirement. `is_convergent=False` by construction; ISOR independence (D2284) does not apply.
- **Value assessment (pragmatic sample):** single-source records are mostly **book-level paraphrases** — descriptive observations ("bioRxiv Impact…", "Evergreen Magazine's Editorial Policy"), case studies ("Olive AI", "Thales' Olive Option", "Zola Marathon Reading"), and code snippets ("Angr Framework", "Loan Processing Decision Logic"). A minority are genuinely applicable ("Extreme Customer Research Method", "Render Queue Workflow"). They carry **retrieval/recall value but NOT epistemic-independence value** — the core Maxwell OS claim (cross-source convergence).
- **Impact on P0.x / BUG-146:** P0.x would recover ~5,500–6,000 MORE single-source gated clusters. The D2418 "value audit" counted *extractability* (35-40% "genuine principles"), not *epistemic value*. Since single-source output is dominated by generic paraphrase, P0.x is **low-value as a P0**. Re-scope: (a) CANCEL P0.x and run S4→S5→S6 on the existing 8,410, or (b) recover ONLY convergent gated clusters (~0 — gated clusters are single-source by nature). Recommend (a).
- **SINGLETON SMOKE (2026-08-24, live OMLX, `scripts/smoke_singleton_s2_s4.py`):** 8 spread + 4 targeted singletons extracted. Confirms the quality concern and adds two specific failure modes: (1) **`tool_instruction`→`process_template` conflation** — SQLAlchemy ORM / MongoEngine ODM / Superlinked multi-indexing were ALL labeled `process_template` (4/4 in the targeted sample) despite the prompt's explicit PT-vs-TI warning; (2) **`extraction_type` over-claim** — 4/4 labeled `causal_mechanism` for what are normative/descriptive tool patterns (tripped the 95% dominance warning); (3) **thin PT** — "Agent-Based Request Delegation System" emitted with `steps`/`trigger`/`done_condition` all None. → **TASK #12 DONE (D2450):** added 3 framework-API `tool_instruction` positives (SS-POS-007/008/009 = SQLAlchemy/MongoEngine/Superlinked) to the single-source golden with explicit "NOT process_template" rationale; `golden_single_source_max` 9→12. Remaining: completeness gate (`score_single_source.py` DROP_THIN/DROP_ANECDOTE) at commit time; `extraction_type` over-claim is a separate calibration item (D2440 S5 verifier + prompt calibration).
- **Status:** 🟢 CLOSED — decided D2470 (G0 scope = filtered frontier, 10,063 records). PT-vs-TI golden contrast DONE (D2450).

## 🟢 BUG-164 — 2026-08-23 — 3 duplicate fb_ids in S2 checkpoint (pre-existing) — FIXED (R1.4 dedup)
- **Symptom:** `stage2_extract/t11/checkpoint.jsonl` has 3 fb_ids appearing **11 times total** (Value-First Demonstration ×6, Progressive Disclosure ×3, Power-Law ×2) — i.e. 8 surplus records, NOT "6 records" as first logged. The same 3 duplicates exist in the pristine `checkpoint.jsonl.pre_relabel` backup → NOT introduced by the P1.2 relabel or P1.3 human-verdict pass.
- **Root cause:** likely a pre-D2421 resume re-extraction (cf. BUG-156 duplicate-FB path) predating the final-segids fix; `fb_id = hash(name, definition)`, so identical name+definition → identical fb_id.
- **Impact:** 3 near-duplicate groups (11/8,410 ≈ 0.13%). Fold into R1.4 near-dup dedup (38 name groups / ~80 records) before S4.
- **Status:** ✅ FIXED (2026-08-24) — `scripts/dedup_s2.py` dropped 8 surplus exact-fb_id records → `checkpoint.deduped.jsonl` (8,402); 37 near-dup name groups flagged REVIEW (not auto-dropped).

## 📌 SESSION 2026-08-23 — P1.2 relabel + P1.3 human verdicts + OMLX fixes (D2434–D2436)
- **P1.2 (D2434):** relabeled single-source/singleton `extraction_type` with gemma-4-E4B as judge (R5 cross-family; Qwen3 = 8% human agreement vs gemma 73% on the hardest 49). Promoted to production (backup `.pre_relabel`). Full-checkpoint causal_mechanism 44.8% → 5.8%.
- **⚠️ RELABEL SCOPE CONFIRMED (2026-08-23, forensic diff pre_relabel→current):** **single-source ONLY.** Convergent records: **0 changed / 2,641 unchanged**. Single-source: 4,057 changed / 1,704 unchanged (gemma sweep 4,058 + P1.3 human 14, net −1 reverted). The `--single-source-only` flag skips `is_convergent` records by design. Convergent clusters were deliberately NOT relabeled (handoff notes "Convergent cluster healthy — 11.3% causal, gemma×Qwen agreement 75%; NOT relabeled"). Log's `changed 3412 / unchanged 1348 / failed 1` (resume2 pass) under-counts the cumulative diff — the authoritative figure is the 4,057/1,704 file diff.
- **P1.3 (D2435):** applied 49 human-adjudicated verdicts → 14 corrections + 35 already-agree; 9 NONE (USER-FLAG content_type) records quarantined. Backup `.pre_p13`.
- **OMLX (D2436):** `--memory-guard safe` (eviction on) + `--no-cache` (185GB SSD thrash gone). Residual gemma prefill slowness (256 head_dim), not config-fixable.
- **Judge evidence (this session):** ladder tightening 49%→45% (rejected); mechanism-field poisoning; few-shot hurts gemma; self-reported confidence uninformative.
- **🔴 NEW — BUG-165 (stage-drift) + forensic findings:** see BUG-165 entry above. S4/S5/S6 are frozen at 2,830 records (old commit `b14462f`) while S2 holds 8,410 — downstream is stale. BUG-164 = 11 records (not 6). BUG-149 already fixed in code. R1.3 "the passage" = 1,161 records (not 1,036).

## 🟢 BUG-162 — 2026-08-22 — config/code drift: dead D2150 + dead schemas classes + field-provenance ambiguity — FIXED (D2433)
- **Symptom (forensic audit D2432):** config and code carried stale, mutually-contradicting artifacts.
- **Root cause + fix:**
  - **B1** — `EXTRACTION_TO_CONTENT_TYPE` (D2150) dead → **REMOVED** from `pipeline/content_types.py` (definition + stale docstring) and `config/content_types.yaml` (block). Zero importers confirmed. `ROUTE_TO_CONTENT_TYPE` (D2128) kept — it is live in `stage4._resolve_content_type`.
  - **B2** — `pipeline/schemas.py` `ProcessTemplate/ProcessInstance/GrowthEdge/ToolInstruction` dead pydantic classes → **REMOVED** (324 lines). Schema contract fully preserved in `content_types.yaml` (`extension_fields`/`s2_body_fields`/`zone_body`).
  - **B3** — `actors` array-vs-str mismatch → resolved by deleting the dead `ProcessInstance` class (the only `actors: str` declaration).
  - **C2** — `failure_mode` provenance → **DOCUMENTED** dual-provenance in `core_body` (S4-CRIBS for principle; S2-extracted for process_template per `s2_body_fields`).
  - **C3** — `route` not inert → **CORRECTED** the D2128 config comment + H4 task (route is a live fallback).
- **Status:** ✅ FIXED — 82 tests pass; schemas.py, content_types.py, stage4_merge import cleanly.

## 🟢 BUG-163 — 2026-08-22 — extraction_type=none singleton-only (prompt↔config enum mismatch) — FIXED (D2433)
- **Symptom (D2432 A2):** `SINGLETON_SYSTEM` offered `extraction_type ... |"none"` (a 5th value), but `config/content_types.yaml` `extraction_types` defines only 4. If a singleton emitted `none`, validation rejected it.
- **Root cause:** singleton prompt pre-dated the D2323 4-value FORM enum; the "no object" case is already handled by `route=NULL`, making `none` redundant.
- **Fix (D2433):** removed `|"none"` from the singleton `extraction_type` enum and the FORM list; rewrote the `extraction_type=none + no principle → route=NULL` bullet to "No extractable object … → route=NULL". `grep -n none pipeline/stage2_extract.py` → 0 hits; file compiles.
- **Status:** ✅ FIXED

---

## 🟢 BUG-161 — 2026-08-22 — extraction_type FORM drift: 4 divergent S2 prompt paths — FIXED (D2431/D2434); data re-label DONE
- **Symptom:** single-source/singleton causal_mechanism ≈ 60% vs convergent ≈ 11%. 5,761 single-source+singleton records carry inflated causal_mechanism.
- **Root cause (3 confirmed S2 prompt defects + golden contamination):**
  - **F1** — DECISION ORDER + CALIBRATION existed only in convergent SYSTEM_PROMPT; absent from SINGLE_SOURCE_SYSTEM / SINGLETON_SYSTEM / SINGLETON_BATCH_SYSTEM.
  - **F5** — SINGLETON_SYSTEM "MAPPING RULES" coupled FORM→ROLE (empirical_pattern→growth_edge, causal_mechanism→principle, normative_heuristic→process_template), violating D2323; inherited by SINGLETON_BATCH_SYSTEM via .replace.
  - **F6** — stage2_relabel_extraction_type.py uses GEN_MODEL=Qwen3 (same family as generator) → R5 violation if used as a *verifier*; acceptable as a *re-generator* with the fixed ladder.
  - **F3/F4** — golden single_source labels 2 tool_instruction examples as descriptive_model (conflicts D2417); hard negatives carry bogus causal_mechanism. **→ FIXED (D2433):** the 2 TI examples relabelled normative_heuristic; all 55 hard negatives across the 4 golden files stripped of extraction_type/content_type.
- **A/B test result (D2431, n=20 live):** Qwen3 + decision-order ladder = 25% causal (vs 55-60% current); gpt-oss cross-family + same ladder = 0% causal / 60% empirical_pattern. Cross-family agreement only 35% → FORM is high-ambiguity, and gpt-oss has its own empirical_pattern bias (does NOT auto-correct). "Move FORM to S4" (D2430) refuted.
- **Resolution (implemented):** fix IN S2 — added DECISION ORDER + CALIBRATION to SINGLE_SOURCE_SYSTEM and SINGLETON_SYSTEM; removed MAPPING RULES; SINGLETON_BATCH_SYSTEM inherits. File parses; MAPPING RULES=0, DECISION ORDER=3.
- **Remaining:** (1) ~~F3/F4 golden fix~~ ✅ done; (2) re-label the 5,761 existing single-source/singleton records with the fixed ladder (copy-first) — P1.2; (3) use cross-family gpt-oss as a disagreement FLAG, not an owner — P1.3.
- **Impact:** latent today — S5 (DeBERTa NLI) does not yet consume FORM, so no downstream corruption yet. Fix before R2 (D2427) consumes FORM.
- **Status:** 🟢 FIXED — prompt (D2431) + data re-label sweep DONE (D2434, gemma judge, promoted to production). P1.3 human verdicts applied (D2435).

---

## 🟠 BUG-160 — 2026-08-21 — evidence-passage relevance in drift sample (1/30) — OPEN
- **Symptom:** In the n=30 extraction_type drift review (seed=7), record "Racial Disparities in Maternal Health Prediction Tools" (fb_id 1977c1a5…) has 1 of 3 evidence_passages about a carbon-emission model ("influx of carbon 9.1 billion metric tons per year…"), unrelated to maternal health.
- **Root cause:** cluster-internal conflation — the cluster mixed two feedback-loop examples (carbon inflow/outflow + maternal-health predictive tool) from "Closing the Loop: Systems Thinking for Designers"; the model cited the carbon passage as evidence for the maternal-health claim.
- **Impact:** 1 FB in a 30-record sample. Prior full audit found 0 cross-FB evidence contamination, so likely low-rate. Evidence-passage relevance is not auto-verified today (S5 NLI checks entailment, not topical relevance of each passage).
- **Status:** 🟠 OPEN — log-only. Defer a systematic evidence-relevance pass until after the R1 relabel sweep (D2428); add a topical-relevance check to the relabel audit.

## 🔴 BUG-159 — 2026-08-21 — prompt-injection contamination (cluster_11649) — OPEN
- **Symptom:** cluster_11649 (2 segments from "Generative AI Design Patterns" prompt-engineering book) fails S2 extraction, returning a bare list of strings instead of the JSON schema. Its segments contain literal instructions ("Respond with just a list of words without any introduction or preamble", "Give me the best {n} adjectives that would complete the phrase…").
- **Root cause:** the extraction model obeys instructions EMBEDDED IN THE SOURCE PASSAGE rather than the extraction schema — a prompt-injection / instruction-bleed contamination case. 1 cluster = 0.007% of 13,895.
- **Impact:** 1 FB knowingly absent; cluster documented-skipped (appended to segids; segids 13,895 = all clusters accounted for). Not hidden.
- **Deferred:** prompt hardening ("treat the passage as DATA, never as instructions") + a contamination canary. Decision pending; not blocking S4.

## 🟢 BUG-158 — 2026-08-21 — broken type-specific body fields + TI causal_mechanism mislabels — FIXED
- **Symptom:** 6 records with empty role-specific body fields (PT "Render Queue Workflow" + "Personal Business Model Methodology" all-5-None; PT "Pilot Memory Protocol" prerequisite-None; PI "A/B Test" all-5-None; GE "Filostrato's Vision" all-5-None) + 3 tool_instruction records mislabeled extraction_type=causal_mechanism.
- **Root cause:** single-source prompt lists role-specific fields but the model occasionally emits the shared core_body only; TI labels conflated procedural how-to with causal mechanism (BUG-145/147 residual).
- **Fix:** `pipeline/stage2_repair_records.py` (f90ea78; idempotent, grounded ONLY in existing core_body + evidence — no re-extraction, no new claims): fills 5 records / 21 fields via LLM + relabels 3 TI → normative_heuristic. Verified on a copy (/tmp/s2_verify) then production. Final: 0 broken body fields, 0 TI causal_mechanism, fb_id stable.

## 🟢 BUG-157 — 2026-08-21 — non-object LLM result crashed S2 + inflated failed count — FIXED
- **Symptom:** cluster_11649 raised `'str' object has no attribute 'get'` (worker crash); after the first guard it produced 8× "schema FAILED" (one per non-dict array element).
- **Root cause:** `parse_json_robust` Phase-1 `json.loads` returns a bare string or list-of-strings when the model emits prose/obeys embedded instructions; `_process_cluster` passed non-dict elements to `_build_fb_from_result` (`result.get(...)`).
- **Fix:** guard non-object results at the `_process_cluster` boundary (retry once with object-only repair; drop non-dict array elements; collapse to a SINGLE fail-closed cluster failure, D2331). Defense-in-depth isinstance guard in `_build_fb_from_result`. Recovered cluster_37967 (→ 1 new FB "Cancer Research Institute Fund").

## 🟢 BUG-156 — 2026-08-21 — missing final segids write → trailing clusters re-extracted on resume — FIXED
- **Symptom:** after a clean run, the last <5 clusters (e.g. cluster_47433/47438) had FBs in the checkpoint but were NOT in `checkpoint.jsonl.segids` → a resume re-extracted them → duplicate FBs (same fb_id = hash(name,definition)).
- **Root cause:** segids is written only inside the `completed % 5 == 0` incremental block; the end-of-run block wrote final checkpoint + final gated_ids (D2421) but never a final segids.
- **Fix:** added a final atomic segids write mirroring the gated_ids final write (crash-safe tempfile→fsync→os.replace). Verified: segids 13,895 = all clusters; 0 orphan FB clusters.

## 🟢 BUG-155 — 2026-08-21 — single-source elaboration under-production (84% empty) — FIXED
- **Symptom:** 84.1% of single-source principles had empty `elaboration` (cluster-size correlated: 62% empty at size 2 → ~0% by size 14).
- **Root cause:** single-source prompt allowed "leave a field empty when the passage does not provide it", which Qwen3-Coder applied to `elaboration`.
- **Fix:** prompt now requires elaboration (3-5 sentences, derived from mechanism+boundary+consequence); post-hoc backfill `stage2_backfill_elaboration.py` (idempotent, grounded) filled 2,111 across two runs + 49 residual in the P0 pass. Final: 0 empty elaboration.

## 🟢 BUG-154 — 2026-08-21 — MinHash LSH key collision on resume ("The given key already exists") — FIXED
- **Symptom:** the t11 `--only-single-source --reset-single-source` rerun failed on EVERY FB-producing cluster with `❌ cluster_X: The given key already exists` (a datasketch `MinHashLSH.insert` ValueError). Only NULL/skip clusters advanced; every extractable object was lost.
- **Root cause:** `is_near_duplicate()` assigned new signatures with `f"mh_{len(minhash_cache)}"`. On resume the D2382 rebuild inserts the checkpoint FBs' *stored* signatures ("mh_0"…"mh_2642") into a fresh LSH, but those keys have a GAP (a near-dup/other FB consumed a slot without persisting → 2641 keys, max index 2642). `len(minhash_cache)` = 2641 therefore lands on the occupied "mh_2641" → `lsh.insert` raises. This was NOT specific to `--reset-single-source` — any t11 resume (`--reprocess-gated` included) would have hit it. Latent since D2382.
- **Fix (2026-08-21):** `is_near_duplicate()` now finds the next FREE index (`while f"mh_{idx}" in minhash_cache: idx += 1`) instead of assuming contiguous keys. Regression: `tests/test_stage2_minhash_resume_collision.py` (2 tests).
- **Source:** 2026-08-21 live t11 single-source rerun (first 44 clusters) + signature-gap audit of the pre-rerun checkpoint.

## 🟢 BUG-153 — 2026-08-21 — `process_singletons` references undefined `ss_few_shot_text` → NameError — FIXED
- **Symptom:** the BUG-152 singleton golden wiring left `ss_few_shot_text` referenced inside `process_singletons._process_one` (`few_shot=ss_few_shot_text if ss_few_shot_text else None`), but that name is a **local** of `run_stage2`, not a module global. `process_singletons` (a standalone function) had no such binding → the first singleton extraction would raise `NameError: name 'ss_few_shot_text' is not defined`, silently (the workers swallow exceptions into `return None`).
- **Root cause:** cross-function scope assumption — the BUG-152 wiring threaded `ss_few_shot_text` into the single-source call site inside `run_stage2`, but the singleton call site lives in a separate function whose golden-loading block was never added.
- **Impact:** `--process-singletons` was dead on arrival — 35,122 t11 singletons would produce zero FBs (or crash). Hidden failure: the worker-level `except Exception: return None` masked it as "no output" rather than a loud error (C16 violation by proximity).
- **Fix (2026-08-21):** `process_singletons` now loads the single-source golden independently (`load_golden_single_source` + `format_golden_fewshot_single_source`) and binds its own `ss_few_shot_text`, mirroring `run_stage2`. Verified by `py_compile` + scope audit (no remaining cross-function references).
- **Note (follow-up):** `process_singletons` still lacks a resume mechanism (`processed_ids` is initialized empty and `singleton.segids` is never read) — a crash partway through a 35K-singleton run would restart from scratch. Defer full singleton run until a resume skip is added.
- **Source:** 2026-08-21 preflight scope-audit of the BUG-152 golden wiring (`grep ss_few_shot_text` across function scopes).

## 🟢 BUG-152 — 2026-08-20 — S2 single-source zero-golden → re-labelling + over-fire — FIXED (single-source balanced golden wired)
- **Symptom:** A drafted mono-type prompt (`tools/s2_contamination_audit.py`) instructing "extract ONLY principle, else route=NULL" was A/B'd against the current multi-type `SINGLE_SOURCE_SYSTEM` on 8 curated passages (all 5 roles + `empirical_pattern` boundary + negative control). The mono prompt was **worse**, not better:
  - `process_template` (pilots 3-techniques) → mono emitted `principle` (normative_heuristic) instead of NULL.
  - `tool_instruction` (faiss.read_index) → mono emitted `principle` + `route=NULL` (internally inconsistent).
  - `growth_edge` (autism "what if") → mono emitted `content_type=growth_edge` despite "ALWAYS principle" instruction (structural LEAK).
  - Negative control (1950s advertising fact) → BOTH prompts overfired (baseline `process_instance`, mono `principle`); neither NULL'd a pure fact.
- **Root cause:** stripping the role vocabulary (forcing "principle or NULL") removes the model's rejection outlet. Without golden hard-negatives showing *what NULL looks like*, Qwen3-Coder defaults to re-labeling the object as a principle rather than rejecting it. The 100%-principle convergent golden is what taught "principle" as the universal fallback in the first place — so a mono-type prompt with no golden inherits the same bias.
- **Impact:** the "extract principle first, skip everything else" sequential-mono-type architecture (proposed D2345) would SILENTLY convert methods/tools/case-studies into principles — the exact principle↔non-principle contamination the user flagged. Mono-type is **not** viable as prompt-only; it needs a hard schema gate + per-type golden hard-negatives to work.
- **Fix (IMPLEMENTED + VERIFIED 2026-08-20 23:35):** kept the MULTI-type prompt (it labeled 5/6 non-principle roles correctly live), and wired a BALANCED single-source golden (`config/golden/stage2_fewshot_single_source.yaml`) into the single-source/singleton path via `S2_GOLDEN_SINGLE_SOURCE_PATH`. The golden has 5 positives (one per content_type role: principle/process_template/tool_instruction/process_instance/growth_edge) + 3 hard negatives (pure fact → NULL, platitude → NULL, unfalsifiable speculation → NULL). Rejection examples now carry the actual passage text (not just rationale) — the text→NULL mapping that fixed the over-fire.
  - New: `load_golden_single_source()` + `format_golden_fewshot_single_source()` in `stage2_extract.py`; `S2_GOLDEN_SINGLE_SOURCE_*` config keys; `tests/test_stage2_single_source_golden.py` (4 tests).
  - **Audit result (8/8 correct in wired path):** BUG-147 DFS→`process_template` → now `tool_instruction` (FIXED); negative-control over-fire → now `route=NULL` (FIXED); all 5 roles + ambiguous `empirical_pattern` correct. 64/64 tests pass; convergent golden hash unchanged.
- **Also re-confirmed live:** BUG-147 (DFS algorithm → `process_template` mislabel) reproduced on the `tool_vs_template` passage pre-fix; resolved post-fix.
- **Source:** 2026-08-20 — `tools/s2_contamination_audit.py` (read-only, production `SINGLE_SOURCE_SYSTEM` + `_normalize_role_fields` + `validate_fb_output`; emits `audit_output/*.jsonl|md`).

## 🔴 BUG-151 — 2026-08-20 — domain/discipline taxonomy structural overlap (`education` dual-listed + 267 raw-alias overlaps) — OPEN
- **Symptom:** `config/taxonomy_v5.yaml` lists `education` as canonical in BOTH `domains` (line 510) and `disciplines` (line 1561). Additionally 267 raw-alias strings appear in both a domain entry and a discipline entry (`artificial intelligence`, `brand strategy`, `clinical psychology`, `computer graphics`, …). This means the domain/discipline boundary is fuzzy for 267 concepts.
- **Root cause:** taxonomy authored as two lists without a disjointness invariant. Mapping code IS kind-aware (D2133/D2394 `_accept()` filters by canonical list; `synonym_map.yaml` is domain-only), so cross-kind *mapping* leak is already prevented — but the `education` canonical is valid in both `is_valid_domain()` and `is_valid_discipline()`, so a model can emit it in either field and pass validation.
- **Impact:** structural ambiguity only (1 canonical); the 38.4% `emerging` (BUG-150) is the larger *miss* and is distinct. A model emitting `discipline="education"` where `education`-the-domain was meant goes uncaught.
- **Fix (T1.2, D2422):** remove `education` from one list; add CI test asserting `domain_canonicals ∩ discipline_canonicals == ∅`; add validation that a discipline raw-label resolving only in the domain index re-classifies rather than silently `emerging`.
- **Source:** 2026-08-20 — taxonomy_v5.yaml canonical/raw-alias intersection audit (Python).

## 🔴 BUG-148 — 2026-08-20 — S2 `route` field is stale/uniform (`route="FB"` on ALL 2,878 records) — OPEN
- **Symptom:** every record in `stage2_extract/t11/checkpoint.jsonl` has `route="FB"` — including the 39 `process_template` and 1 `tool_instruction`. The route field no longer discriminates; it is inert noise (D2128 route→content_type mapping is never exercised in practice).
- **Root cause:** S2 prompts (convergent + single-source + singleton) emit `route: "FB" | "NULL"` as a legacy field. `_resolve_content_type()` in S4 correctly prefers `content_type`, so routing survives — but `route` itself is vestigial.
- **Impact:** low today (S4 ignores it), but a C12/C19 violation — dead field retained in every record, and any downstream code trusting `route` would silently misroute PT/PI/GE/TI into the FB bucket.
- **Fix (T1.2):** either remove `route` from S2 prompts + builder, or wire D2128 mapping so `route` is computed from `content_type` (single source of truth). Verify no consumer reads `route` first.
- **Source:** 2026-08-20 senior audit of t11 checkpoint (content_type×route cross-tab).

## 🟢 BUG-147 — 2026-08-20 — S2 over-assigns `process_template`, under-assigns `tool_instruction` (role-label precision) — FIXED (single-source path, via BUG-152 contrastive golden)
- **Symptom:** 39/40 non-principle FBs are `process_template`, only 1 is `tool_instruction`. But ~25 of the 39 "process_templates" are *code/API/algorithm descriptions* (DFS tree traversal, Point Class Constructor, Matrix Reshaping, Closure-based State Management, DoWhy causal framework, patch vertex consistency, safe string extraction). These are tool_instruction / descriptive_model / principle — NOT repeatable human how-to methods.
- **Root cause:** D2417 fixed the *field* conflation (ROLE leaking into extraction_type), but the *role-label* precision is still weak. Qwen3-Coder treats any technical/procedural prose as `process_template`, reserving `tool_instruction` almost never. The single-source prompt describes the 5 roles in one sentence with no contrastive PT-vs-TI disambiguation.
- **Impact:** if PT/TI ever become Layer-1 retrieval buckets (D2418), ~25/40 = 62% of non-principle objects would land in the wrong bucket. Tool grounding (MCP/Recipe promotion) would be starved of the very TI objects the 13-field schema was designed to capture.
- **Fix (single-source path — IMPLEMENTED + VERIFIED 2026-08-20/21):** the BUG-152 balanced single-source golden (`config/golden/stage2_fewshot_single_source.yaml`) added a SECOND `tool_instruction` contrastive positive (DFS algorithm described as steps) alongside the clear library-call TI, and `load_golden_single_source()` was changed to return ALL positives (6) so the contrastive pair is never dropped. The `SINGLE_SOURCE_SYSTEM`/`SINGLETON_SYSTEM` prompts carry an explicit "⚠️ process_template vs tool_instruction" disambiguation. `tools/s2_contamination_audit.py` `tool_vs_template` probe now emits `tool_instruction` (was `process_template`) — **8/8 audit correct**.
- **Remaining (T1.2, D2418):** re-measure the PT/TI split on the FULL single-source corpus after the t11 `--only-single-source --reset-single-source` rerun; the convergent path (principle-only by D2323 design) needs no change. Regression coverage: `tests/test_stage2_single_source_golden.py::test_tool_instruction_has_contrastive_pair`.
- **Source:** 2026-08-20 senior audit — t11 checkpoint non-principle sample (source books: Coding with ChatGPT, Graphics Shaders, Grammar of Graphics, RAG-Driven, The Self-taught Programmer).

## 🔴 BUG-150 — 2026-08-20 — S4 discipline `emerging` regression: 38.4% on full T1.1 (was 15.5% canary) — OPEN
- **Symptom:** 1088/2830 FBs (38.4%) have `discipline=emerging` (fallback), vs D2398's measured 15.5% on the canary. `domains` contains `emerging` on 2554/2830 (90.2%).
- **Root cause:** the D2394 synonym/alias fix held only on the 279-cluster design-canary. The full T1.1 corpus (940 books: business/psych/econ/ops/health/policy) is far broader than the design-centric `taxonomy_v5`. Raw labels falling back to `emerging` include `graphic design` (92!), `organizational behavior` (31), `data visualization` (27), `design studies` (23), `design thinking` (18) — note `graphic design` itself does not map to a canonical discipline, so this is a synonym/alias gap, not just corpus-mismatch.
- **Impact:** 38.4% of FBs are unclassifiable by discipline → retrieval/filtering by discipline is ~62% blind. This is the single biggest classification-quality gap.
- **Fix (T1.2):** promote `graphic design`, `data visualization`, `organizational behavior`, `design thinking`, `product design`, `ux design` to canonical disciplines (or map as aliases). Re-measure after. See D2388/D2394.
- **Source:** 2026-08-20 — t11 S4 checkpoint discipline/domains cross-tab.

## 🟢 BUG-149 — 2026-08-20 — S4 name truncation: `max_words=5` hardcoded truncates 176 FB names — FIXED in code (doc corrected 2026-08-23)
- **Symptom:** 176/2830 FB names truncated to ≤5 words by `normalize_fb_name(name, max_words=5)` (stage4_merge.py). Truncation propagated to S5.
- **Root cause:** C12 violation — `max_words=5` was a hardcoded magic number.
- **Fix (ALREADY COMMITTED, verified 2026-08-23):** `config/pipeline_config.yaml` `stage4.fb_name_max_words: 8` → `pipeline_paths.py:199` `FB_NAME_MAX_WORDS` → `stage4_merge.py:1485` `normalize_fb_name(name, max_words=FB_NAME_MAX_WORDS)`. `scripts/restore_fb_names.py` exists to patch the 176 truncated names in S4/S5 in place (no re-run). ✅ RESIDUAL RESOLVED (2026-08-25): function signature default is now `max_words: int = FB_NAME_MAX_WORDS` (config-driven, C12). `retrieval_eval.fb_name_max_chars: 200` remains a near-duplicate key consumed only by `retrieval_evaluator.py` (separate concern, no action).
- **Note (BUG-165 interaction):** the 176 truncated names live in the stale 2,830-record S4/S5 — re-running S4 on the full 8,410 S2 will re-truncate nothing (fix is in); prefer the re-run over the restore script.
- **Source:** 2026-08-20 — S2→S4→S5 name diff; 2026-08-23 forensic verify (config+code committed).

## 🟡 BUG-146 / P0.x — 2026-08-19 — S2 summary gate is content_type-blind — discards PT/PI/GE potential — ✅ RECOVERED (2026-08-23 forensic correction)
- **⚠️ SUPERSEDED (2026-08-23, verified from `single_source_rerun.log` + `retry_failed.log`):** the "9,950 summary gated" figure is **STALE** — it counts the ORIGINAL run (runner_t11_v3.log, 2026-08-19 15:56, pre-D2417). The **single-source rerun (2026-08-21, post-D2417) already re-processed all 10,812 single-source clusters with the content-type-aware gate**, which is why the final state is `13,891 processed → 8,410 FBs` and `Gate violations: 0 (self-flagged as summary)`.
- **Remaining genuinely-un-extracted work = ~1 cluster, not 9,950:** `cluster_11649` (BUG-159 contamination, schema FAILED ×8 retries) + 2 NULL (47441/47443). D2421's "183 failed" was already reduced by the auto-retry to these 3. **P0.x is NOT a multi-hour job — it is ~1 failing cluster.**
- The genuinely un-extracted population is the **35,122 singletons** (separate S1.5 file), not the gated clusters.
- **Symptom:** 6,127 clusters (63% of processed) "summary gated" — skipped wholesale. The gate keys ONLY on `is_summary` (`stage2_extract.py:1558`: `if is_summary and gate_enabled: return _gate`) with NO content_type awareness — a cluster flagged is_summary is dropped even if it could yield a process_template/process_instance/growth_edge/tool_instruction.
- **Root cause:** prompt ties `is_summary` to "without identifying a convergent mechanism" — conflates "no extractable principle" with "no extractable object of ANY type". Single-source prompt never defines is_summary beyond "(bool)".
- **Evidence:** checkpoint content_type = principle 2,778, process_template 32, tool_instruction 1, process_instance 0, growth_edge 0 (of 2,811 FBs). Pipeline is ~99% principle; the 6,127 gated clusters likely include PT/PI/GE-worthy content.
- **Fix (post-T1.1, alongside BUG-145):** content_type-aware gate (is_summary must NOT gate PT/PI/GE/TI) + prompt tightening ("is_summary=true means NO extractable object of ANY type"). **D2417 committed 2026-08-19 17:20 — but t11 S2 checkpoint mtime 15:56 predates it, so the 2,878 FBs are pre-fix. Re-extraction requires a `--reprocess-gated` flag (gated clusters ARE in processed_ids: 13,712/13,899 processed, only 187 unprocessed → `--resume-from 2` would skip the 9,842 gated silently).**
- **Value audit (D2418, 2026-08-20):** 40 gated clusters sampled → ~35-40% genuine principles, ~20% genuine PT/PI/TI, ~35-40% correctly gated noise. The gate discarded substantial extractable value (~5,500–6,000 objects).
- **⚠️ P0.x SCOPE (clarified 2026-08-23):** P0.x = the RECOVERY RUN for this bug. It includes exactly three steps:
  1. **seed gated IDs** — `scripts/seed_gated_ids.py --log "knowledge pipeline/runner_t11_v3.log" --validate-segids "…/checkpoint.jsonl.segids"`. Current `.gated_ids` has **158** entries; the runner log has **9,950** "summary gated" lines → seed writes the full ~9,950. (D2421 cites 9,842 — reconcilable off-by-~108.)
  2. **re-extract gated clusters** — `pipeline/stage2_extract.py --reprocess-gated` (content_type-aware gate, D2417/D2421) to recover PT/PI/TI/GE.
  3. **route recovered objects through S4 → S5 → S6** (NOT yet possible — see BUG-165 stage-drift).
  Plus D2421's **183 failed auto-retry** (separate from gated; those clusters are absent from `processed_ids`). ~~This is a multi-hour LLM job~~ **⚠️ CORRECTED 2026-08-23: already done by the single-source rerun; only `cluster_11649` remains failing (schema FAILED, BUG-159).**
- **Source:** live T1.1 run 2026-08-19 — audit of summary-gate behavior; 2026-08-23 forensic scope verification.

## 🟡 BUG-145 — 2026-08-18 — S2 model conflates extraction_type/content_type ('tool_instruction') — OPEN (post-T1.1 prompt fix)
- **Symptom:** ESCALATED (3 @ 16:44 → 128 @ 09:59 Aug 19): 71× `Invalid extraction_type 'tool_instruction'` + 57× `Invalid extraction_type 'process_template'` + 2× `definition too short`. Conflation spikes in the single-source phase — the model writes content_type values (tool_instruction/process_template) into extraction_type.
- **Root cause:** Qwen3-Coder emits `tool_instruction` into `extraction_type`, but that value belongs in `content_type`. `extraction_type` = epistemic form (causal_mechanism|empirical_pattern|normative_heuristic|descriptive_model|none); `content_type` = object kind (principle|process_template|process_instance|growth_edge|tool_instruction). The model flags tool-specific content but writes it into the wrong field. Systematic (not random) — all 3 in tooling clusters.
- **Impact:** 128/9618 targets (1.3%). Fail-closed gate (D2323) correctly rejects → cluster marked FAILED (D2403) → auto-retried on resume. ~128 potential FBs (~2%) missed if unfixed. Prompt fix post-T1.1 is now REQUIRED (was 'nice to have') — the single-source prompt needs explicit extraction_type/content_type disambiguation.
- **Fix (post-T1.1):** 1-line prompt tightening in S2 SYSTEM_PROMPT/SINGLETON_SYSTEM, then targeted `--resume-from 2` to retry the 3 failed clusters. No full S2 rerun.
- **Source:** live T1.1 run 2026-08-18.

## 🔴 BUG-144 — 2026-08-18 — S1.5 build_clusters ~27 min silent grind (git subprocess per record) — FIXED (D2412)
- **Symptom:** T1.1 S1.5 looked hung ~27 min after "sub-clusters created" — ~78% CPU, no log output, checkpoint not written. NOT a deadlock (CPU busy) but a pathological slowdown.
- **Root cause:** `stamp_record()` (pipeline/stamp.py:133) → `get_pipeline_commit()` → `get_git_commit()` spawned `git rev-parse --short HEAD` as a subprocess on EVERY call, with NO memoization. `build_clusters()` stamps every cluster AND every singleton (~200K records) → ~200K subprocess spawns (~10ms each ≈ 27-33 min). `_PIPELINE_RUN_ID` (P0.9) and `_MANIFEST_HASH` (D2282) were memoized; `get_git_commit` was missed.
- **Fix:** memoize `get_git_commit()` via module-level `_GIT_COMMIT` singleton. 2 calls now 12.8ms (incl. first spawn) vs ~10ms each. **Files:** pipeline/stamp.py. **Source:** live T1.1 run 2026-08-18.

## 🔴 BUG-143 — 2026-08-17 — S1 chunk + S1.5 embed runner timeouts (3600s) kill full-corpus T1.1 — FIXED (D2411)
- **Symptom:** T1.1 launch (`--run-id t11`) stopped after 1h: `[Stage 1] Chunk — TIMEOUT (3600.0s); Pipeline complete — 2 done, 1 failed`. S1 was at ~414/940 books when killed (~1.5h needed for full corpus).
- **Root cause:** `config/pipeline_config.yaml stages.timeouts.'1': 3600` and `'1.5': 3600`. D2402 nulled S2/S4 (same BUG-137 class) but missed S1 (chunk ~1.5h) and S1.5 (embed ~5h, D2409 incremental cache).
- **Fix:** `'1': null`, `'1.5': null` (unlimited, like S2/S4). **Files:** config/pipeline_config.yaml. **Source:** live T1.1 run 2026-08-17 21:24 (kill 22:28) — verify-don't-assume caught what the frontier audits missed.
- **Recovery:** `runner.py --run-id t11 --resume-from 1` — S0/S0.5 manifests COMPLETE (skipped); S1 re-runs deterministically (~1.5h). Time lost: ~1h of chunking.

## 🟢 R3 CANARY S4→S6 RERUN — COMPLETE (2026-08-17 19:22:39, ~87 min)
- **Result:** S4 279/279 FBs (0 failed clusters, 0 quarantines, 52911 edges, 0 isolated) → S5 236 PASS / 43 QUARANTINE / 0 FLAG → S6 279 committed (`pipeline_run_id=canary`), FTS 279, Parquet `fbs_snapshot_20260817_192235.parquet` (4482.4 KB), 0 taxonomy replacements.
- **Regression check:** 236/43 ≈ prior canary 235/43 → D2402–D2405 + D2408 produced no behavioral drift.
- **Validated live:** D2408 (gpt-oss-20b full responses once `response_format` skipped), D2371 fail-closed gate (0 trips), S5 classification_failed gate (0 trips). Resume/fail paths NOT exercised in-vivo (0 failures) — decision logic unit-covered (D2407, 9 tests).
- **Environment:** caffeinate -disu active throughout; OMLX lazy-loaded (only Phi-4-mini + gpt-oss-20b resident, ~69% mem free at end); `com.maxwell.omlx` launchd crash loop unloaded (BUG-142 side note).

## 🔴 BUG-142 — 2026-08-17 — `response_format={"type":"json_object"}` returns EMPTY content from gpt-oss-20b — FIXED (D2408)
- **Symptom:** canary S4→S6 rerun quarantined every FB (`Empty/short application — D2371`); `call_omlx` logged "content missing from message (reasoning-model cold reload?)". gpt-oss-20b returned 2-token/0-token responses despite being loaded.
- **Root cause:** `call_omlx_json` hardcoded `response_format={"type":"json_object"}` (D2219). This forces oMLX constrained decoding (xgrammar), which conflicts with gpt-oss-20b's Harmony reasoning format → empty content. Same family as D2392 ("grammar ON breaks gpt-oss-20b, empty content / Harmony conflict"). Reproduced: 8/8 empty WITH response_format, 10/10 full WITHOUT (model warm).
- **Fix:** skip `response_format` for models in `VERIFY_REASONING_OFF_MODELS` (gpt-oss-20b); `parse_json_robust` handles unfenced JSON. **Files:** pipeline/omlx_call.py.
- **Also cleaned this session (not a code bug):** `com.maxwell.omlx` launchd service was crash-looping on `[Errno 48] Address already in use` (86K errors) because it double-binds port 11435 against the oMLX.app server; unloaded it → CPU churn gone, gpt-oss-20b stabilized.



## 🟠 BUG-141 — 2026-08-17 — session_seed.yaml YAML parse break (boot/integrity blocker) — FIXED (D2406)
- **Symptom:** 4/10 integrity checks FAIL (YAML parse, referenced-files, vector-dimensions, version-stamps), all cascading from one parse error; boot step 2 would fail loading the session config.
- **Root cause:** unquoted `: ` (colon-space) in `phase.status` (`…live: grammar OFF…`) and the `D2402` completed-list entry (`…'4': 3600…`) → YAML treats them as nested mapping keys.
- **Fix:** quote both scalars (single-quote `status`; double-quote the `'4'`-containing list entry). **Files:** agent/session_seed.yaml. **Source:** 2026-08-17 pre-canary integrity audit.



## 🟠 BUG-137 — 2026-08-17 — S4 runner timeout '4': 3600 (1h) vs multi-hour full-corpus S4 — FIXED (D2402)
- **Symptom:** unattended T1.1 run killed at S4 after 1h; runner.py treats TimeoutExpired as stage failure and stops.
- **Root cause:** config/pipeline_config.yaml stages.timeouts.'4': 3600; '2': null intended for S2 only.
- **Fix:** '4': null. **Files:** config/pipeline_config.yaml. **Source:** frontier audit 2026-08-17 (4b55797).

## 🟠 BUG-138 — 2026-08-17 — S2 schema-invalid output rebranded as NULL + permanently processed — FIXED (D2403)
- **Symptom:** malformed Qwen output -> NULL -> checkpointed as processed -> never retried; D2331 gate misses it (C16).
- **Root cause:** _build_fb_from_result returns {"_null": True, "_schema_errors": ...} on validate_fb_output failure; caller counts total_null and adds cluster to processed_ids.
- **Fix:** 3-state FB/NULL/FAILED; schema failure = failed_clusters, not processed. **Files:** pipeline/stage2_extract.py.

## 🟠 BUG-139 — 2026-08-17 — S4 classification-failed clusters unrecoverable on resume — FIXED (D2404)
- **Symptom:** "re-run to retry failed clusters" never retries classification failures (already in processed_ids).
- **Root cause:** stage4_merge.py appends FAILED FB then unconditionally processed_ids.add(cluster_id).
- **Fix:** FAILED clusters not appended / not marked processed. **Files:** pipeline/stage4_merge.py.

## 🟠 BUG-140 — 2026-08-17 — S4 fabricates evidence="cited" + S5 can PASS classification_status=FAILED — FIXED (D2405)
- **Symptom:** classification failure -> looks like clean cited FB -> S5 can certify -> committed (Parquet/raw SQL carry FAILED-as-clean).
- **Root cause:** stage4_merge.py hardcodes "evidence": "cited" in both failure sentinels; stage5_verify.py has no classification_status gate.
- **Fix:** remove fabricated "cited"; S5 gates FAILED -> QUARANTINE. **Files:** pipeline/stage4_merge.py, pipeline/stage5_verify.py.

## 🟢 BUG-136 — 2026-08-16 — Golden set: 5 NON_VERBATIM evidence + stale meta count (77 vs 80) — FIXED (D2397)
- **Symptom:** `golden_validate.py` FAILED 6 checks: META_MISMATCH (meta `total_examples`=77, actual 80)
  + 5 NON_VERBATIM evidence passages (CONV-054, CONV-055 ×3, CONV-058).
- **Root cause:** (1) depth-mining (V8/D2369 + D2377) added 5 examples (CONV-054…058) without re-syncing
  meta counts (77→80, GOLD-A 49→54); (2) CONV-054 had a genuine paraphrase ("price of anarchy measures
  the gap…") not verbatim in source; (3) CONV-055 had 3 double-apostrophe `''` YAML-escaping bugs (literal
  `can''t`/`it''s` instead of `can't`/`it's`); (4) CONV-058 fabricated a `Generator` quote where the source
  says `Discriminator`.
- **Fix:** corrected evidence to verbatim; removed the fabricated CONV-058 passage; re-synced meta.
  Re-stamped `.golden_meta.json` (sha256 `70ff3283…`). `golden_validate` 80/80 PASS; `verify_golden_hash` PASS.
- **Files:** `config/golden/stage2_fewshot_convergent.yaml`, `config/golden/.golden_meta.json`
- **Source:** Session 2026-08-16 — pre-T1.1 golden audit.

## 🟢 BUG-135 — 2026-08-16 — Dead legacy `s3_original_domain` column (DB 61 vs 60 cols) — FIXED (D2395)
- **Symptom:** `just integrity` full → `[8] INSERT has 60 placeholders but fbs table has 61 columns`.
- **Root cause:** `s3_original_domain` (removed stage3, D2130) dropped from CREATE TABLE + INSERT
  long ago but never DROPPED from existing DBs. 370 rows held empty strings — dead weight.
- **Fix:** `_migrate_drop_column()` + drop in `init_db()`. DB 61→60 cols; integrity 17/17.
- **Files:** `pipeline/stage6_commit.py`
- **Source:** Session 2026-08-16 — integrity healthcheck + audit (D2395).

## 🟢 BUG-134 — 2026-08-16 — Synonym-index kind-filter bug: domain synonyms polluted discipline index — FIXED (D2394)
- **Symptom:** `organizational psychology`, `leadership`, `team dynamics`, `culture`,
  `behavior` mapped to the DOMAIN canonical `organizational behavior` even in the
  DISCIPLINE synonym index (`get_synonym_index('discipline')`). Consequence: wrong-kind
  canonical labels and inflated `emerging` fallback (discipline 32.0%).
- **Root cause:** `_build_synonym_index()` step 2 (synonym_map.yaml) ran UNFILTERED by
  kind. synonym_map.yaml is domain-only, but its synonyms/keywords were written into the
  DISCIPLINE index too, overwriting correct step-1 mappings. This was a D2133 regression
  (D2133 added the kind filter to step 1 but not step 2).
- **Fix:** apply the same `_accept(canonical)` kind filter in step 2. Verified:
  `organizational psychology → psychology`, `leadership → leadership` (was both →
  `organizational behavior`).
- **Files:** `pipeline/schemas.py`
- **Source:** Session 2026-08-16 — taxonomy emerging over-firing analysis (D2394).

### ⚠️ NOTE (2026-08-16) — Grammar A/B: 0.6.0 xgrammar breaks gpt-oss-20b (NOT a pipeline bug, external)
- Grammar enforcement WORKS in 0.6.0 (Phi-4-mini returns clean JSON, no `warning` header),
  but with `response_format=json_object` + gpt-oss-20b the message content is empty
  (`{"role":"assistant"}`) — xgrammar enforcement collides with the Harmony reasoning
  protocol (`GrammarMatcher rejected token 0`; `Unexpected EOS while waiting for message
  header`). OFF baseline (0.5.1) = 30/30 valid JSON. **Keep grammar OFF.** See D2392.

## 🟢 BUG-133 — 2026-08-16 — S6 schema-migration gap: `is_summary` + `classification_status` missing from DB — FIXED (D2391)
- **Symptom:** S6 `INSERT OR REPLACE INTO fbs` failed 278/278 with `table fbs has no column named is_summary`.
- **Root cause:** `is_summary` (D2089) + `classification_status` (D2184) added to `CREATE TABLE fbs`
  but never added to `_migrate_add_column()` list. `CREATE TABLE IF NOT EXISTS` can't heal an existing
  table, so the pre-existing DB (398 rows) lacked both columns. Same class as BUG-110/BUG-119
  (schema drift on existing DBs) but in the *migration* list, not the CREATE TABLE.
- **Fix:** added `_migrate_add_column` for both columns. S6 re-ran → 278 inserted / 0 failed (exit 0).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** Session 2026-08-16 — canary S6 commit audit (D2391).

### ⚠️ NEW (2026-08-16) — Vector search DEGRADED: `vec_fbs` table absent (sqlite-vec load fails)
- **Symptom:** S6 log: `⚠️ Embedding insert failed: no such table: vec_fbs` ×278, and
  `⚠️ Vector: DEGRADED — 0 embeddings`. `vec_fbs` virtual table never created.
- **Root cause:** `sqlite_vec.load(conn)` requires `conn.enable_load_extension(True)`, which raises
  `AttributeError` on the python.org framework Python build (no `enable_load_extension`). Documented
  in BUG-104; remediation = Homebrew Python (`brew install python@3.12`). FTS retrieval still works.
- **Action:** non-blocking — vector search unavailable; FTS + Parquet still serve retrieval. Revisit
  if vector search becomes a T1.1 requirement.

### ⚠️ NEW (2026-08-16) — DB contamination: 676 rows across 5 run_ids (canary accumulated)
- **Symptom:** after S6, `maxwell.db` has 676 rows: `canary` 557 (old 279 + new 278), plus 4 other
  run_ids (88+23+5+3 = 119). The two canary runs produced different `fb_id`s (content hashes changed
  after D2381/D2382 S2 fixes), so `INSERT OR REPLACE` ADDED the new 278 rather than replacing old rows.
- **Impact:** DB is NOT a clean single-run KB — stale/duplicate FBs accumulate across canary reruns.
  `pipeline_run_id` column preserves provenance, but retrieval would surface BOTH runs' FBs.
- **Action:** before final T1.1, decide DB reset policy — either reset `maxwell.db` (or use a fresh
  DB path per run) so the committed KB reflects one coherent run. Flagged for operator decision.
- **✅ RESOLVED (D2396):** fresh-DB for T1.1 (archive + empty DB); run-specific-DB tracked as G10 (P2).
  Reset executed 2026-08-16 → `knowledge pipeline/maxwell.db.pre_t11_20260816.bak` + fresh empty DB.

---

## ⚠️ NEW (2026-08-16) — S4 canary completion findings (D2386–D2390)

## ⚠️ NEW (2026-08-16) — S4 canary completion findings (D2386–D2390)

### 1. CRIBS quarantine: `cluster_6241` empty `application` (→ D2386)
- **Symptom:** `[215/279] Cluster cluster_6241 → ❌ Empty/short application (0 chars < 10) — FB QUARANTINED (D2371)`.
  FB "Human Capital Investment Drives Occupational Mobility" (causal_mechanism, 2 books)
  lost. S4 gate `max_failed_ratio=0.0` (D2338) → **Stage 4 FAILED** (1/279 = 0.4%).
- **Class:** CRIBS content-quality failure (empty `application`), NOT JSON/truncation. Model
  `gpt-oss-20b` emitted an empty application for a causal-mechanism FB.
- **Action:** operator decision pending — rerun cluster_6241 only, relax S4 gate to 0.01
  (D2381 precedent), or manual annotate. See D2386.

### 2. `is_specialized` parsed-but-not-persisted (None × 278)
- **Symptom:** `is_specialized` = None for all 278 FBs; the signal is folded into `depth` +
  `procedural_skill` instead. Schema field exists but is dead at S4.
- **Class:** provenance/schema gap (same family as BUG-110/BUG-122/D2376 R2).
- **Action:** decide whether to persist `is_specialized` or remove from schema (see D2387).

### 3. Name truncation loses specificity (21 FBs)
- **Symptom:** D2069 5-word cap truncates 21/278 names mid-thought, e.g.
  `'Cognitive Dissonance in Memory and'`, `'Margin Of Safety In Complex'`, `'Status Quo Bias With Multiple'`.
  The full name is preserved in `definition`/`elaboration`, but the searchable `name` is
  an incomplete fragment.
- **Class:** cosmetic/UX — expected by D2069, but the 5-word cap may be too aggressive for
  compound conceptual names. Non-blocking.

### 4. Taxonomy `emerging` over-firing (→ D2388)
- **Symptom:** discipline `emerging` 89/278 (32.0%); FBs with `emerging` in `domains`
  261/278 (93.9%). Raw labels correct but outside capped 35/72 taxonomy → fallback.
- **Action:** taxonomy expansion analysis on full checkpoint (D2388).

### 5. Jargon schema: string not dict (→ D2389, CORRECTED)
- **Symptom:** jargon is `str` (`"term: definition; term: definition"`), not the
  `{"term": "definition"}` dict the prompt implies. BUT — correcting a mid-run false
  positive — **0/214 jargon strings contain any keyword**; jargon is distinct + valid.
- **Action:** none required (parseable + semantically correct). Record corrected.

---

## 🟢 D2376 (2026-08-16) — `extraction_type` silent over-claim + `source_ids` dropped at S4 — FIXED
- **Symptom (over-claim):** read sites defaulted missing `extraction_type` → `"causal_mechanism"`
  (the strongest epistemic claim: "verified X→Y because Z"), while the schema default is `""`.
  Canary distribution collapsed to 97.8% causal_mechanism (270/276 S2, 176/180 S4) — descriptive/
  normative material was being silently re-branded causal.
- **Root cause:** `.get("extraction_type", "causal_mechanism")` / `getattr(..., "causal_mechanism")`
  at 9 pipeline + 8 benchmark-tool sites. Field is optional at S2 (validated vs config enum; empty passes).
- **Fix (R1):** all defaults → `""`; added a config-driven over-claim canary
  (`stage2.extraction_type_dominance_warn_ratio: 0.95`) that warns (not fails) when a single form
  dominates. `application` framing already keyed to type (D2371).
- **Symptom (provenance):** `source_ids` (canonical `sha256(author|title)` hashes, D2176) emitted by
  S1.5 + S2 (276/276) was DROPPED at S4 (0/180) and absent from the `FB` schema — only `source_books`
  filenames persisted. Same class as BUG-110/BUG-122 (provenance field dropped end-to-end).
- **Fix (R2):** added `source_ids: list[str]` to `FB`; S4 derives (S2 FB → S1.5 cluster → resolve from
  filenames) + persists; S6 adds a `source_ids` column (create + migrate + INSERT + Parquet) + read-back
  parsing (`query.py`/`retrieve.py`); `integrity_check.py` key-field.
- **Status:** 🟢 FIXED — py_compile clean, INSERT 60=60 balanced, functional canary + round-trip verified.
- **Files:** `stage2_extract.py`, `stage4_merged_call.py`, `stage4_merge.py`, `schemas.py`,
  `stage6_commit.py`, `pipeline_paths.py`, `probe_run.py`, `dspy_trainer.py`, `query.py`,
  `retrieve.py`, `integrity_check.py`, `bridge_s2_to_s4.py`, `config/pipeline_config.yaml`, `tools/*`
- **Source:** Session 2026-08-16 — R1/R2 remaining-task execution (DECISION-LOG D2376)

### ⚠️ NEW (2026-08-16) — Orphan fields: `prerequisite_fbs` / `contradicts_fbs` / `procedural_skill`
- **Finding:** these are schema-defined + committed (S6) + traversed (`retrieve.py`) but **NEVER populated
  by any stage** (`related_fbs` IS populated via P1.4). `accessibility=prerequisite` is therefore derived
  only from the `expert AND def>200` heuristic (D2132) — 0/180 FBs have `prerequisite_fbs`. Future tax:
  the dependency/conflict/tool-binding edges are dead data until a producer is added. Logged (not blocking).

---

## 🟢 BUG-132 — 2026-08-15 — `thinking_budget` was a single global key shared by merged + depth calls (blocks D2366 "adopt 256") — FIXED (D2368)
- **Symptom:** `models.verifier.thinking_budget` (`config/pipeline_config.yaml:93`) is read once into
  `VERIFY_THINKING_BUDGET` (`pipeline/pipeline_paths.py:109`) and applied unconditionally to any model in
  `VERIFY_REASONING_OFF_MODELS` (`pipeline/omlx_call.py:268-272`). Both `merged_cribs_classify()` and
  `classify_depth_focused()` use `VERIFY_MODEL` (gpt-oss-20b) → **both call sites share the SAME budget**.
- **Impact:** D2366's plan to "adopt `thinking_budget: 256` on the merged CRIBS call" is **not scopeable to
  the merged call alone** in current code — flipping the key silently re-tunes the depth-focused call too.
  The depth call's D2359 A/B tuning (budget=128 → 72.0% acc / 7.3s) and the merged call's X8 tuning
  (256 → 1.8×) cannot be set independently today.
- **Required before enabling any budget:** thread `thinking_budget` as an explicit per-call parameter through
  `call_omlx()` / `call_omlx_json()` (or add a second config key, e.g. `models.verifier.depth_thinking_budget`),
  then gate each call site separately. Found by the 5-LLM verification round (D2367); NOT in D2366.
- **Status:** 🟢 FIXED — 2026-08-15 (D2368: `thinking_budget` threaded per-call through `call_omlx`/`call_omlx_json` + `depth_thinking_budget` config key; merged vs depth now independently scopeable)

---

## ✅ DONE (2026-08-15) — S4 speedup options exhausted (D2366, X4/X6/X8/X9)

| ID | Option | Measured result | Verdict |
|----|--------|-----------------|---------|
| X4 | Frugal gemma-4-E4B depth (S4-B) | 62.5% acc, 4.5× faster (2.0s warm) | ❌ FAILS 90% gate (relabel did not rescue gemma) |
| X6 | Batch focused-depth (S4-A) | 66.7% vs 84.4% sequential (n=45), parity 60%, 1.7× | ❌ batching degrades accuracy 17.7pt |
| X8 | thinking_budget on merged CRIBS | **256 → 1.8× faster (40s→22s), valid JSON** | ✅ SOLE viable speedup (gated on accuracy) |
| X9 | Concurrency 1/2/3 workers | 43.3s/41.3s/42.2s (flat) | ❌ OMLX serializes — no benefit |

**⚠️ CORRECTION to D2365 X2:** depth accuracy is **~84% (n=45)**, NOT the 98% earlier reported. The 98%
was an over-correction (re-mapped only the 14 relabeled FBs; the relabel vote missed ~6 more gpt-oss
cross-domain over-assignments). The residual error is systematic over-assignment of `cross-domain`.

---

## ✅ RESOLVED (2026-08-15) — Cross-LLM audit X1/X2/X5 re-adjudicated (D2365)
> The three highest-priority audit items from `CROSS-LLM-AUDIT-VERDICT-2026-08-15.md` were re-derived
> from raw governance JSON. All three resolve in Maxwell's favour.

| ID | Concern | Finding (evidence) | Verdict |
|----|---------|--------------------|---------|
| X1 | D2363 golden-relabel circular (gpt-oss-led contamination) | Relabel = cross-model consensus; gpt-oss tie-break in only 3/13 (always paired with qwen); gpt-oss voted *against* relabel in CONV-033. Never sole driver. | ✅ NOT contaminated |
| X2 | Depth accuracy 72% (n=50), "quality gap > speed gap" | 72% measured vs PRE-relabel gold; 13/14 "errors" were gold errors (gpt-oss was right, later relabeled). Initial re-map read 49/50=98%, but a fresh n=45 post-relabel run (D2366) showed **~84% (38/45)** — systematic gpt-oss over-assignment of `cross-domain` (~6 more missed). | ✅ RESOLVED — true depth ~84% (no quality *crisis*, but NOT 98%) |
| X5 | 142h denominator unverified (12,964 ≠ FBs) | 12,964 = total clusters; 2,634 convergent (20.3%); 35,239 singletons. Principle-only FBs ≈ 2,634 × 1.35 yield ≈ 3,556 → **~39h** (not 142h). | ✅ 3.6× over-estimate |

**Residual (non-blocking):** 3 relabels (CONV-001/003/051) are gpt-oss-tie-broken → optional 2-family
re-adjudication (qwen+gemma). Authoritative post-relabel depth benchmark pending (replaces stale 72%/75%).

## 🟢 FIXED (2026-08-15) — C12 (X7): hardcoded S4 signal sets → config (D2364)
- **Symptom:** `stage4_merge.py` hardcoded `business/design/system/academic_signals` + `temporal_scope`
  keyword lists; `stage4_merged_call.py:_likely_universal` hardcoded `universal_signals`. C12 violation
  (Gemini's one genuine catch in the cross-LLM audit).
- **Fix (D2364):** extracted to `config/pipeline_config.yaml` → `stage4.{context,temporal,universal}_signals`;
  wired via `pipeline_paths.py` (`S4_CONTEXT_SIGNALS`/`S4_TEMPORAL_SIGNALS`/`S4_UNIVERSAL_SIGNALS`).
  Behavior-preserving (values byte-identical; verified by diff + live read-back).
- **Status:** 🟢 FIXED — `py_compile` clean, `config_audit --strict` clean, Qwen3-Coder-30B review PASS.
- **Files:** `config/pipeline_config.yaml`, `pipeline/pipeline_paths.py`, `pipeline/stage4_merge.py`,
  `pipeline/stage4_merged_call.py`

---

## 🟢 BUG-129 — 2026-08-14 — S4 GPT-OSS `reasoning_effort`/`enable_thinking` are silent no-ops (D2359 void)
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

## 🟢 BUG-130 — 2026-08-14 — GPU kernel panic loading dense Qwen3.8-27B in parallel (IOGPUGroupMemory)
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

## 🟢 BUG-126 — 2026-08-14 — Legacy direct-classify path still not fail-closed (D2357 gap)
- **Symptom:** D2357 made `merged_cribs_classify()` and `batch_cribs_classify()` fail-closed, but the legacy direct path (`call_omlx_json(class_prompt)` when both batch and merged are disabled/failed) still turned a sparse response into `emerging`/`cited` via empty-raw-label mapping.
- **Fix (D2358):** the direct path now raises `SparseClassificationError` on missing `discipline`/`domains`/`evidence` and quarantines the FB (`classification_errors += 1`). `depth` is intentionally not checked there (overridden by the focused depth call). BUG-120 is now unconditional across all configs.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT re-audit (2nd pass, HIGH) + independent re-verification

## 🟢 BUG-127 — 2026-08-14 — k-means split exception silently swallowed (`except Exception: pass`)
- **Symptom:** `split_cluster_by_kmeans()` wrapped the whole embed+cluster step in `except Exception: pass`, hiding split failures (C16).
- **Fix (D2358):** log the failure (`⚠️ k-means split failed …`) while retaining the deliberate fail-safe (return the unsplit cluster).
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage2_extract.py`
- **Source:** ChatGPT re-audit (2nd pass, MEDIUM) + independent re-verification

## 🟢 BUG-128 — 2026-08-14 — Dead `_render_3zone_body_old_end()` stub + literal `MAX_PER_BOOK=2`
- **Symptom:** (1) `_render_3zone_body_old_end()` remained as a dead `pass` compatibility stub (C19). (2) `MAX_PER_BOOK: int = 2` was a local magic number while `max_probe_samples` was already config-driven (C12).
- **Fix (D2358):** removed the dead stub; added `stage2.max_probe_per_book` (config) → `S2_MAX_PROBE_PER_BOOK`.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage6b_anytype_push.py`, `pipeline/stage2_extract.py`, `pipeline/pipeline_paths.py`, `config/pipeline_config.yaml`
- **Source:** ChatGPT re-audit (2nd pass, LOW) + independent re-verification

---

## 🟢 BUG-120 — 2026-08-14 — Semantic fail-open: merged/batch classification fabricates `emerging`/`domain`/`cited` (C16)
- **Symptom:** `merged_cribs_classify()` and `batch_cribs_classify()` filled a *present-but-sparse* model response's missing `discipline`/`domains`/`depth`/`evidence` with `emerging`/`["emerging"]`/`domain`/`cited`. D2355 had made only the *missing-entry* case fail-closed; a malformed-but-present entry still became valid-looking semantic data without raising, so `max_failed_ratio: 0.0` could not catch it.
- **Root cause:** a single `defaults` dict mixed non-semantic CRIBS enrichment (`application`/`failure_mode`/`elaboration`/`keywords`) with semantic classification fields, applying the same silent-fill to both.
- **Fix (D2357):** split the defaults — CRIBS fields default safely (empty); semantic fields are validated fail-closed via `_validate_semantic_classification()` which raises `SparseClassificationError` on any missing/empty/invalid `discipline`/`domains`/`depth`/`evidence`. Callers fall back to individual classification and account the failure.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merged_call.py`
- **Source:** ChatGPT re-audit (BLOCKER #2/#3) + independent re-verification

## 🟢 BUG-121 — 2026-08-14 — Intimacy lattice not fail-safe: null/config failure resolves `public` (sovereignty)
- **Symptom:** `config/intimacy_policy.yaml` declares `null_handling: intimacy: private` and "ambiguity/NULL resolves upward (D369)", but `resolve_intimacy()` initialized at `public`, had no null-escalation, and `_load_policy()`/`_load_anchors()` swallowed load exceptions to `{}`. `route_space()` fell back to `non_private`. A policy/config failure could route an FB to public/non-private against the declared privacy floor.
- **Fix (D2357):** (1) `_load_policy()`/`_load_anchors()` now log AND record failures; (2) `resolve_intimacy()` fails closed to `private` on any config error (`R0-config-failure`) and on a wholly absent signal set (`R0-null`); (3) `route_space()` falls back to `private`, never `non_private`; (4) `LEVELS`/`space_routing` now read from YAML (C12) with a code fallback only for a missing file.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/intimacy_lattice.py`
- **Source:** ChatGPT re-audit (BLOCKER #4) + independent re-verification

## 🟢 BUG-122 — 2026-08-14 — `source_principle_ids` empty for v3 FBs (provenance gap)
- **Symptom:** S4 read only `p.get("principle_id")` to build `source_principle_ids`, but S2 v3 records emit `fb_id` (not `principle_id`), so the field was `[]` for every normal v3 FB.
- **Fix (D2357):** read `fb_id` first, retain `principle_id` as legacy fallback (matches the `fb_id or principle_id` pattern used elsewhere in S4).
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT re-audit (HIGH #5) + independent re-verification

## 🟢 BUG-123 — 2026-08-14 — Downstream FB-ID rehash fallback after S4 name normalization (identity drift)
- **Symptom:** `fb = {"fb_id": fb_data.get("fb_id") or make_hash_id(name, definition)}` re-hashed a missing-ID record from the *normalized* name, which would drift from S2's hash of the un-normalized name — breaking the D2350 invariant.
- **Fix (D2357):** missing `fb_id` is now a hard error (FB quarantined, `failed += 1`), never a silent re-hash. Removed the now-unused `make_hash_id` import.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT re-audit (HIGH #9) + independent re-verification

## 🟢 BUG-124 — 2026-08-14 — `keywords` rendered as body content; `jargon` rendered before elaboration
- **Symptom:** `content_types.yaml` moved `keywords` to `metadata.discovery` and declares `jargon` renders AFTER elaboration (D2349), but `stage6b_anytype_push.py` rendered `**KEYWORDS**` in the body and placed `jargon` in Zone 2 (before Zone 3 elaboration).
- **Fix (D2357):** `keywords` removed from body rendering and added to YAML frontmatter + JSON payload metadata; `jargon` moved after elaboration in the 3-zone body.
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage6b_anytype_push.py`
- **Source:** ChatGPT re-audit (HIGH #7/#8) + independent re-verification

## 🟢 BUG-125 — 2026-08-14 — S2 hybrid-gate failure silently swallowed (`except Exception: pass`)
- **Symptom:** the D2276 pre-extraction hybrid gate wrapped its decision in `except Exception: pass`, so a gate failure was invisible (violates C16 "no silent errors").
- **Fix (D2357):** log the gate failure (`⚠️ Hybrid gate error …`) while retaining the deliberate fail-open (prefer false-positive extraction to data loss).
- **Status:** 🟢 FIXED — 2026-08-14.
- **Files:** `pipeline/stage2_extract.py`
- **Source:** ChatGPT re-audit (MEDIUM #12) + independent re-verification

---

## 🟢 BUG-108 — 2026-08-14 — S4 depth inference failure silently becomes `depth="domain"` (C16 violation)
- **Symptom:** `classify_depth_focused()` returns `"domain"` on *any* exception (`except Exception: return "domain"`) and on no-match (`return "domain"`). GPT-OSS timeout, cold-reload empty content, transport error, malformed output, unexpected answer, and a *legitimate* `domain` all collapse to the same value — semantic contamination.
- **Root cause:** the focused depth call omits `Reasoning: none` (batch/merged do send it), uses `depth_max_tokens: 512` (truncates GPT-OSS reasoning), parses by substring (`for d in (...): if d in text`), and the exception handler manufactures `"domain"` instead of propagating/quarantining. `call_omlx()` raises `KeyError` when `content is None` (reasoning-model cold reload), which is exactly what the handler swallows.
- **Fix (D2351):** fail-closed — propagate failure into `classification_errors` (S4 `max_failed_ratio: 0.0` already exits non-zero); exact-token parser (accept exactly one of 4 labels); single fallback policy via `S4_DEPTH_FALLBACK_DEPTH`; send `Reasoning: none` on the focused path; bump `depth_max_tokens` to 1024.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (fail-closed depth (D2351)).
- **Files:** `pipeline/stage4_merged_call.py`, `pipeline/omlx_call.py`, `config/pipeline_config.yaml`
- **Source:** 4-LLM audit (ChatGPT depth-audit) + independent re-verification

## 🟢 BUG-109 — 2026-08-14 — `depth_max_tokens: 512` contradicts measured ~1024 GPT-OSS requirement
- **Symptom:** governance `S4_BOTTLENECK_ANALYSIS.md` live-measured GPT-OSS needs `max_tokens ≥ 1024` to emit the answer after reasoning (1024 → `"specialized"`); production config `stage4.depth_max_tokens: 512` overrides the verifier model-level `max_tokens: 1024`. The 512 budget truncates reasoning, triggering BUG-108's failure path.
- **Root cause:** config↔governance drift; the `classify_depth_focused()` docstring "512 is plenty — one word answer" is stale (contradicted by the repo's own measurement).
- **Fix (D2351):** `depth_max_tokens` 512 → 1024; correct the stale docstring.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (depth_max_tokens 1024 (D2351)).
- **Files:** `config/pipeline_config.yaml`, `pipeline/stage4_merged_call.py`
- **Source:** 4-LLM audit + independent re-verification

## 🟢 BUG-110 — 2026-08-14 — `source_segments` declared provenance but dropped at S4/S6
- **Symptom:** `config/content_types.yaml` declares `metadata.provenance: [..., source_segments, ...]`; S2 emits `source_segments`; but S4's FB record rebuild copies `source_clusters`/`source_books`/`source_principle_ids`/`evidence_passages` and **never `source_segments`**. Zero references in `stage4_merge.py`/`stage5_verify.py`/`stage6_commit.py`. Segment-level provenance is lost.
- **Fix (D2352):** carry `source_segments` into the S4 FB dict + add an S6 column.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (source_segments S4→S6 (D2352)).
- **Files:** `pipeline/stage4_merge.py`, `pipeline/stage6_commit.py`, `config/content_types.yaml`
- **Source:** 4-LLM audit (ChatGPT + Claude) + independent re-verification

## 🟢 BUG-111 — 2026-08-14 — `evidence_passages`/`evidence_passages_shown` not persisted to SQLite
- **Symptom:** S4 emits `evidence_passages` + `evidence_passages_shown`; S5 passes them through (`vfb = dict(fb)`); but S6's `fbs` schema + INSERT have no such columns — verbatim source quotes are dropped from the primary SQLite KB. (The Parquet snapshot *does* keep them via full-dict `from_pylist`; `source_text` IS a SQLite column.)
- **Fix (D2352):** add columns, OR formally document Parquet as the verbatim-evidence store.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (evidence_passages/_shown → SQLite (D2352)).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** Claude audit (Q5) + independent re-verification

## 🟢 BUG-112 — 2026-08-14 — `is_summary` declared classification but dropped end-to-end
- **Symptom:** `content_types.yaml` declares `is_summary` under `classification`; S2 emits it; but S4's FB dict omits it and S6's INSERT omits it → the `is_summary INTEGER DEFAULT 0` column is never written (always 0).
- **Fix (D2352):** persist `is_summary` through S4 → S6.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (is_summary end-to-end (D2352)).
- **Files:** `pipeline/stage4_merge.py`, `pipeline/stage6_commit.py`
- **Source:** 4-LLM audit + independent re-verification

## 🟢 BUG-113 — 2026-08-14 — Singleton S2→S4 index inconsistency (silently skipped)
- **Symptom:** `load_stage2_fbs_via_clusters()` loads singleton FBs into the `clusters` list *and* its local `principles_idx`; but `run_stage4()` discards that index and calls `load_stage2_principles()`, which reads ONLY `STAGE2_CHECKPOINT` (never `STAGE2_SINGLETON_OUTPUT`). Singleton clusters therefore have `principle_ids` absent from `principles_idx` → `if not cluster_principles: … "empty" … continue` silently skips them.
- **Root cause:** two loaders diverge — one (clusters) includes singletons, the other (principles index) does not.
- **Note:** ChatGPT initially flagged this (correct), then wrongly "retracted" it as FIXED. It is still broken.
- **Fix (D2353):** `run_stage4()` should reuse the `principles_idx` returned by `load_stage2_fbs_via_clusters()`.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (singleton index reuse (D2353)).
- **Files:** `pipeline/stage4_merge.py`
- **Source:** ChatGPT audit (Q4, then retracted) + independent re-verification

## 🟢 BUG-114 — 2026-08-14 — Batch missing-output silently becomes synthetic semantic values
- **Symptom:** `batch_cribs_classify()` fills missing FB entries with `defaults = {"depth":"domain","discipline":"emerging","domains":["emerging"],"evidence":"cited",…}` — a missing model output becomes valid-looking semantic data (same C16 hidden-error class as BUG-108).
- **Fix (D2355):** fail-closed / flag missing entries instead of manufacturing defaults.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (batch missing fail-closed (D2355)).
- **Files:** `pipeline/stage4_merged_call.py`
- **Source:** 4-LLM audit + independent re-verification

## 🟢 BUG-115 — 2026-08-14 — Depth benchmark ≠ production parser; 87.5% vs 37.5/50% drift; fallback orphaned
- **Symptom:** (1) `tools/benchmark_s4_depth_gptoss.py` uses direct `requests` + `reasoning_content` fallback; production `classify_depth_focused()` uses `call_omlx` (raises on `content=None`) + content-only — the benchmark is not a production-path test. (2) governance claims 87.5% focused vs 38% long, while the benchmark docstring still frames GPT-OSS as "third entrant after Phi 37.5% / Gemma 50%". (3) `S4_DEPTH_FALLBACK_DEPTH` is loaded but never used by the focused classifier (only the `elif` branch when `depth_focused_classification=False`).
- **Fix (D2351):** run benchmark through production `classify_depth_focused()`; make one authoritative number; route fallback through `S4_DEPTH_FALLBACK_DEPTH`.
- **Status:** 🟢 FIXED — 2026-08-14: `tools/benchmark_s4_depth_frugal.py` runs `classify_depth_focused()` through the PRODUCTION path (`call_omlx` + `_parse_depth_token`, fail-closed) for both GPT-OSS and the frugal depth model. This is now the authoritative depth benchmark (S5 closed). The old `benchmark_s4_depth_gptoss.py` remains as a historical direct-API baseline.
- **Files:** `tools/benchmark_s4_depth_frugal.py` (new), `pipeline/stage4_merged_call.py`, `pipeline/stage4_merge.py`
- **Source:** ChatGPT depth audit + independent re-verification

## 🟢 BUG-116 — 2026-08-14 — `s3_original_domain` vestigial dead column/field (bloat)
- **Symptom:** `CREATE TABLE fbs` omits `s3_original_domain` but `insert_fb()` INSERTs it (value always `""` — S4 removed it per D2130). Migrated by `_migrate_add_column()` so NOT a fresh-DB failure (ChatGPT mislabeled this as a BLOCKER). Dead column + dead INSERT field.
- **Fix (D2355):** remove from INSERT, migration, and (eventually) DB.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (s3_original_domain removed (D2355)).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** ChatGPT audit (BLOCKER claim) → corrected via independent re-verification

## 🟢 BUG-117 — 2026-08-14 — Secondary `STAGE2_CHECKPOINT` writers bypass self-verifying path
- **Symptom:** `probe_run.py:225` writes via bare `open(...).write()` (no `safe_write`, no self-verify, violates C6); `repair_elaboration.py:237` uses `safe_write` but skips the `load_jsonl` self-verify re-read. Both are reimplementations instead of calling `_write_checkpoint_jsonl()`.
- **Fix:** route both through `_write_checkpoint_jsonl()`.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (checkpoint writers unified (BUG-106 residual)).
- **Files:** `pipeline/probe_run.py`, `pipeline/repair_elaboration.py`
- **Source:** Claude audit (Q6) + independent re-verification

## 🟢 BUG-118 — 2026-08-14 — `insert_embedding()` swallows failures silently
- **Symptom:** `insert_embedding()` catches `Exception` and returns `False` with no per-FB log; S6 only reports aggregate vector degradation. A partially-unembedded committed corpus is invisible.
- **Fix (D2355):** log which FB failed; surface in commit summary.
- **Status:** 🟢 FIXED — implemented 2026-08-14 (insert_embedding logs failures (D2355)).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** ChatGPT audit + independent re-verification

## 🟢 BUG-119 — 2026-08-14 — `jargon` (core body) excluded from FTS5
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

## 🟢 BUG-107 — 2026-08-14 — 2 single-source FBs leaked into final DB despite `--only-convergent`
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

## 🟢 BUG-106 — 2026-08-14 — S2 checkpoint mixed JSONL/pretty-printed (breaks re-run/resume)
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

## 🟢 BUG-105 — 2026-08-14 — Embedding instability: 60s timeout + keep_alive thrash (3% drop, D2275 gate exceeded)
- **Symptom:** T1.1 canary S1.5 embedding: 12 batches failed with HTTP read timeouts (`Read timed out (read timeout=60)`), 768 segments dropped = 3.07% (D2275 gate = 0.5%). A re-run stalled at ~2 seg/s with bge-m3 showing "Stopping..." (VRAM unload mid-run).
- **Root cause:** (1) `batch_embed` hardcoded `timeout=60` (C12 violation) — too short under 4-worker concurrent load (Ollama serializes `/api/embed`). (2) bge-m3 default 5-min keep_alive → unloaded between batches → cold-reload stalls.
- **Fix (D2348):** config-driven `services.ollama.embed_timeout: 180` + `embed_keep_alive: -1`. Verified: 0 failures, ~12 seg/s, 34.5 min for 25K segments (was 12 failures / 2-3 seg/s).
- **Status:** 🟢 FIXED (2026-08-14, D2348).
- **Files:** `pipeline/ollama_embed.py`, `pipeline/pipeline_paths.py`, `config/pipeline_config.yaml`
- **Source:** T1.1 canary run (this session)

---

## 🟡 BUG-104 — 2026-08-13 — sqlite-vec cannot load: `load_extension` missing on python.org Python 3.12.1
- **Symptom:** `stage6_commit.py init_db()` warns "sqlite-vec not available" on every run; the `vec_fbs` virtual table is never created (verified: current `maxwell.db` has `fbs`/`fbs_fts` but NO `vec_fbs`). Vector search has therefore silently never worked — retrieval falls back to FTS only. Masked by the broad `except (ImportError, Exception)` catch.
- **Root cause:** Python 3.12.1 (python.org framework build, `/Library/Frameworks/Python.framework/...`, SQLite 3.43.1) compiled WITHOUT `load_extension`/`enable_load_extension`. `sqlite_vec.load(conn)` internally calls `conn.load_extension(...)` → `AttributeError: 'sqlite3.Connection' object has no attribute 'load_extension'`. The BUG-012/P0.11 fix (`conn.enable_load_extension(True)` → `sqlite_vec.load(conn)`) itself fails on this build. The except prints a misleading "Install: pip install sqlite-vec" (the package IS installed).
- **Fix:** (1) Use a Python build with `load_extension` support — Homebrew Python (`brew install python@3.12`) or conda-forge Python; OR (2) improve `init_db` to distinguish `ImportError` (package missing) from `AttributeError` (load_extension unavailable) and surface the real remediation. NOT a data-loss blocker: FTS fallback works (verified by stress test).
- **Status:** 🟡 PARTIAL (2026-08-14) — code now distinguishes `ImportError` (package missing)
  from `AttributeError` (load_extension unavailable) and prints the correct remediation; the
  underlying environmental issue (python.org build lacks `load_extension`) still requires
  Homebrew/conda Python for vector search. FTS fallback continues to work.
- **Action (2026-08-17):** switch runtime to Homebrew Python (`brew install python@3.12`) or
  conda-forge Python to enable `vec_fbs`. Re-verified this session: `sqlite_vec` 0.1.9 IS installed,
  but `enable_load_extension`/`load_extension` are absent on the python.org 3.12.1 build (SQLite 3.43.1,
  `SQLITE_OMIT_LOAD_EXTENSION`). Non-blocking for T1.1 (FTS + Parquet serve retrieval).
- **Files:** `pipeline/stage6_commit.py`
- **Source:** This session — live verification of vector-search readiness during `just preflight` (BUG-012's fix assumed `enable_load_extension` exists).

---

## 🟢 BUG-102 — 2026-08-13 — S1.5 embedding-drop index misalignment (silent cluster→segment corruption)
- **Symptom:** If the Ollama embedding path drops any segment (batch fails; drop rate ≤0.5% permitted by D2275), the returned embedding array is shorter than the original segment list, but cluster records are built against the original list → embedding[i] no longer corresponds to segments[i]. Wrong segment → wrong cluster → wrong source books → wrong convergence → wrong evidence, with NO exception. Hits the principle path, not just the non-type pass.
- **Root cause:** `embed_segments()` filters `segments` locally on drop (`stage1_5_embed_cluster.py:320` — `segments = [segments[i] for i in successful_indices]`) then returns only `embeddings` (`:327`). Caller `run_stage1_5` (`:598`) receives embeddings only and passes the ORIGINAL `segments` to `build_clusters` (`:609`). The local reassignment never propagates to the caller.
- **Fix (D2346):** Return `(filtered_segments, embeddings)` from `embed_segments()` (or raise when `n_dropped > 0`). Assert `len(segments) == len(embeddings)` immediately before FAISS clustering. Add injected-drop tests (first/middle/last segment).
- **Status:** 🟢 FIXED (2026-08-13) — `embed_segments()` returns `(segments, embeddings)` on both MPS + Ollama paths; caller asserts `len(segments) == len(embeddings)` before `build_clusters()`. `just integrity` 17/17, `just preflight` stress PASS.
- **Files:** `pipeline/stage1_5_embed_cluster.py`
- **Source:** ChatGPT audit (`chatgpt009.md`) Block #2 / Seat 2 / Seat 3; independently re-verified against code this session.

## 🟢 BUG-103 — 2026-08-13 — e2e convergence metric uses filename identity, not canonical source IDs
- **Symptom:** e2e reports `convergent_clusters` 24.5% (39/159) using `len(set(c["source_books"])) >= 2` (filename identity). Production S1.5 gates convergence on canonical work identity (`is_convergent` / `resolve_source_ids()` → author|title). The reported metric can be inflated by duplicate editions and is not the quantity D2336's 20% threshold was meant to calibrate.
- **Root cause:** `pipeline/e2e_test.py:167` computes convergence from `source_books` filenames, not from `is_convergent` / canonical source IDs.
- **Fix (D2347):** Compute `sum(c["is_convergent"])` as the primary metric; report filename-diversity separately as a diagnostic.
- **Status:** 🟢 FIXED (2026-08-13) — `e2e_test.py` Check 1 now gates on `is_convergent` (canonical IDs) and reports filename-diversity as a diagnostic; added a non-gating `vector_completeness` diagnostic check.
- **Files:** `pipeline/e2e_test.py`
- **Source:** ChatGPT audit (`chatgpt009.md`) Block #2 / Seat 2; independently re-verified this session.

---

## 🟢 BUG-101 — 2026-08-13 — T1.1 handoff instructs runner flags that don't exist + stale S5 calibration
- **Symptom:** `governance/aggregated_remaining_tasks.md` T1.1 handoff said `python3 pipeline/runner.py --hybrid --only-convergent`. `runner.py` argparse rejects both `--hybrid` and `--only-convergent` (they are `stage2_extract.py` flags, never forwarded by the runner — `STAGES["2"]` has no `args`). Running the handoff verbatim fails with `unrecognized arguments`. Also carried the pre-D2321 broken calibration `S5 threshold 0.10 (P=1.000, R=0.556)` and implied hybrid-gate use.
- **Root cause:** Handoff written before D2327/D2328/D2339 landed; never re-synced when the runner gained resume-validity manifest (D2329) and the calibration was corrected (D2322). The runner never forwards S2 sub-flags by design.
- **Fix (D2343):** Corrected handoff to `python3 pipeline/runner.py` (traditional-only — hybrid REJECTED per BUG-085) + stage-by-stage `stage2_extract.py` (no sub-flags); corrected S5 numbers to D2322's P=0.647/R=0.386/F1=0.484; annotated hybrid DISABLED.
- **Status:** 🟢 FIXED (2026-08-13) — handoff now matches the runner's actual interface.
- **Files:** `governance/aggregated_remaining_tasks.md`
- **Source:** tooling-alignment audit (`just` recipes + handoff) this session

---

## 🟢 BUG-100 — 2026-08-13 — integrity check [8] false-green (placeholder count never compared)
- **Symptom:** `just integrity` reported 17/17 PASS even when the S6 INSERT placeholder count diverged from the SQLite column count. Check [8] could not catch the D2337 48→54 column change.
- **Root cause (2 stacked):** (1) `re.findall(r"INSERT\s+(OR\s+REPLACE\s+)?INTO\s+fbs[^;]*", ...)` — the capturing group made `findall` return the *group* string ("" / "OR REPLACE "), so `placeholder_count = ins.count("?")` was ALWAYS 0 → the `if placeholder_count > 0` branch never fired → silent `return True`. (2) the `[^;]*` tail matched `fbs_fts` (word-prefix) and spanned past the SQL `"""` into Python code, over-counting `?`.
- **Fix (D2342):** VALUES-anchored `re.search(r"INSERT...INTO\s+fbs\b.*?VALUES\s*\(([^)]*)\)", ...)`; also enhanced check [7] key_fields to include the six D2337 fields.
- **Status:** 🟢 FIXED (2026-08-13) — check [8] now genuinely compares 54=54 and FAILED at 56≠54 in the intermediate state (proving the fix).
- **Files:** `pipeline/integrity_check.py`
- **Source:** In-depth `just integrity` alignment audit (this session)

## 🟢 BUG-095 — 2026-08-13 — Stage 6 SQLite drops D2323 axes + mechanism/boundary/consequence (data loss)
- **Symptom:** S2 produces and S4 carries `mechanism`/`boundary`/`consequence` (`stage4_merge.py:1348-1350`), but SQLite `fbs` table has no such columns — only the older `application`/`failure_mode`/`elaboration`. `content_type`/`extraction_type` (D2323) never reach ANY store; `taxonomy_match_method` is computed then discarded in S4.
- **Root cause:** `stage6_commit.py` CREATE TABLE (`:67-127`) + INSERT (`:275-345`) predate the D2323 ontology; S4 never copies `content_type`/`extraction_type`/`taxonomy_match_method` into the output FB dict (only uses `content_type` internally for routing).
- **Fix (D2337):** Add `content_type`, `extraction_type`, `mechanism`, `boundary`, `consequence` columns + INSERT + `_migrate_add_column` + round-trip test. Couples to B5 (S4 must emit the axes).
- **Status:** 🟢 FIXED (code, 2026-08-13) — S4 emits the axes, S6 persists 6 new columns, round-trip test passes. Full-corpus canary pending.
- **Files:** `pipeline/stage6_commit.py`, `pipeline/stage4_merge.py`, `pipeline/schemas.py`
- **Source:** ChatGPT audit (`chatgpt008.md`) Block #1; independently re-verified against code

## 🟢 BUG-096 — 2026-08-13 — S4/S6 fail-open: partial failure still exits 0 (no fail-closed gate)
- **Symptom:** S4 increments `failed`/`classification_errors` and prints them but never exits nonzero. S6 `insert_fb()` returns `False` on exception (`:377-379`), `run_stage6()` prints `❌ Failed to commit` (`:560-561`) but exits 0 → `runner.py` writes a `COMPLETE` manifest with failed inserts.
- **Root cause:** D2331 added fail-closed to S2 only; S4/S6 never received the equivalent `failed > permitted → exit 1` gate.
- **Fix (D2338):** `failed == 0` (or config tolerance) as exit condition in both stages; distinguish LLM-failure vs classification-failure vs intentional-skip; injected-failure test asserting nonzero exit + no COMPLETE manifest.
- **Status:** 🟢 FIXED (code, 2026-08-13) — S4/S6 `max_failed_ratio` fail-closed gates added; injected-failure (exit 1) + happy-path (exit 0) tests pass. Canary pending.
- **Files:** `pipeline/stage4_merge.py`, `pipeline/stage6_commit.py`
- **Source:** ChatGPT audit Block #2/#3; independently re-verified

## 🟢 BUG-097 — 2026-08-13 — runner `--run-id` import-ordering breaks run isolation
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

## 🟡 BUG-099 — 2026-08-13 — Model registry drift: gpt-oss/Phi misnamed as "verifier" vs DeBERTa-only S5
- **Symptom:** `stage5_verify.py` = DeBERTa-only (D2298), but role keys are misleading: `pipeline_config.yaml models.verifier` = gpt-oss (actually the **S4 classifier**, D2249), `models.verifier_v2` = Phi-4-mini (actually the **S2 fast probe**, D2319 — still actively used in `stage2_extract.py:815-825`), `model_assignments.yaml S5_VERIFIER`/`S5_FB_VERIFIER` = Phi (stale; S5 = DeBERTa-only). The true S5 verifier is `models.nli_large` = DeBERTa.
- **Root cause:** D2298 removed Phi from S5 *verification* only, but the role keys were never renamed to reflect the surviving roles (classifier/probe).
- **Fix (D2340):** rename `verifier`→`classifier` (gpt-oss) + `verifier_v2`→`probe` (Phi); annotate `model_assignments.yaml` S5_* roles as removed. Naming/documentation drift — NOT broken functionality (`VERIFY_MODEL`/`VERIFY_MODEL_V2` both resolve + are consumed correctly).
- **Status:** 🟡 PARTIAL — `session_seed.yaml` renamed; `pipeline_config.yaml`/`pipeline_paths.py`/`model_assignments.yaml` rename deferred (P1, low risk)
- **Files:** `config/pipeline_config.yaml`, `config/model_assignments.yaml`, `agent/session_seed.yaml`, `pipeline/pipeline_paths.py`
- **Source:** ChatGPT audit (model attribution); independently re-verified + corrected (Phi still used as S2 probe, NOT dead)

## 🟢 BUG-094 — 2026-08-13 — S2 checkpoint pretty-printed (JSONL broken) + resume-existence coupling

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

### DELEGATE-002: Qwen3-Coder-30B agentic decode collapse — cannot run multi-turn delegate tasks 🟡 MITIGATED
| Field | Value |
|-------|-------|
| **Severity** | 🔴 HIGH (blocks multi-turn agentic delegation to Qwen3-Coder-30B) |
| **Discovered** | 2026-08-28 — delegated the S4 depth A/B (read files → write script → run gpt-oss inference) to `maxwell_omlx`/`Qwen3-Coder-30B-A3B-Instruct-MLX-4bit`; task stalled (16 turns / 9 min / 0 files written) and was cancelled. |
| **Symptom** | Delegate issued tool calls (context grew) but produced no files; turns went idle 20s→1m; "Task did not stop in time (aborted)". |
| **Root Cause** | **Monotonic decode-throughput collapse under context growth.** Server log (`~/.omlx/logs/server.log`) shows, across 8 successive turns: output tokens 258→119→53→52→51→54→51→49; throughput 6.8→3.3→1.6→1.6→0.9→0.7→0.6→**0.4 tok/s**; prompt tokens 6369→…→**19769**; per-turn wall 38s→…→110s. Qwen3-Coder-30B is a 128-expert MoE (D2360) decoding ~5-17 tok/s on M1 Max; as the agent's context accumulates tool results each turn, attention over the growing context collapses decode speed and the model's responses shrink to ~50-token stubs that make no forward progress. Aggravated by `supports_streaming: false` (full generation before return) + `max_tokens=32768` (unbounded reasoning) + a cold-load at 14:17:12 that evicted `Qwen3.8-27B` to fit the model under the 39GB admission soft target. |
| **Impact** | Multi-turn agentic delegation to Qwen3-Coder-30B is effectively unusable (death-spirals to ~0.4 tok/s). Distinct from DELEGATE-001 (reasoning_content passthrough) and BUG-053 (Phi-4-mini hallucination). |
| **Fix (Workaround)** | (1) Use Qwen3-Coder-30B ONLY for **single-shot** code generation (one prompt → one artifact), not multi-step tool orchestration. (2) Short/single-turn delegation → `gemma-4-E4B` (small, fast, confirmed working). (3) Multi-step agentic work → keep in the main agent, or decompose into single-shot sub-tasks. (4) Pipeline-level parallelism → `pipeline/parallel.py` subprocesses, NOT LLM delegates. |
| **Long-term Fix** | Cap delegate `max_tokens`/turn; enable streaming; constrain per-turn context growth; or use a smaller non-MoE model for the agent loop. |
| **Files** | `~/.omlx/logs/server.log` (14:17-14:25 window), delegate task `20260828_14` |
| **Status** | 🟡 MITIGATED (2026-08-28) — task completed by senior-agent backstop; delegation policy documented in D2483. |

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

## BUG-063 — 2026-08-10 — delegate() Cannot Execute File System Tasks (Root Cause) 🟢
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
