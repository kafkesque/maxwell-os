# Maxwell OS v3.0 — DECISION LOG (tiered)

> **Updated:** 2026-09-10 | **Machine source of truth:** `config/decisions.yaml` (585 decisions)
> **Archive (full append-only history):** `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md`
>
> **Convention (standing rule):** OPEN/PENDING at the top (most critical first) → ACTIVE in-effect → DONE/CLOSED at the bottom. A decision is "done" only when its `state` is RESOLVED/SUPERSEDED/ARCHIVED/REJECTED.
>
> **Heading convention (D2552):** tier sections are `## 🔴 OPEN / PENDING`, `## 🟢 ACTIVE`, `## ⚪ DONE / CLOSED`. Entries use `| ID | State | Decision |` table rows. Historical `### D#### — Title` / bare `## D####` formats remain as-is (append-only history); NEW entries MUST use the table format. Reconcile `DECISION-LOG.md` ↔ `config/decisions.yaml` via `scripts/recompute_decision_summary.py`.

---

## 🔴 OPEN / PENDING — highest priority first

### New from cross-model adjudication (2026-09-03)
| ID | State | Decision |
|---|---|---|
| D2546 | PENDING | **SHACL hot-path + OWL periodic** (not OWL-DL everywhere). Formalize 105 canonicals as `sh:disjoint`/`sh:closed`/`sh:in` before Track B. |
| D2547 | PENDING | **Per-label/per-axis cost-weighted thresholds** — retire the global 5% semantic-error rule. Calibration measurement DONE (D2561): 440 labels → `governance/d2547_calibration.json`; remaining = populate per-label thresholds. |
| D2548 | PENDING | **Grammar-constrained decoding pilot** on S4 discipline/domain enums (Outlines/XGrammar) — latency A/B before adoption. |

### Pending from registry
| ID | State | Decision |
|---|---|---|
| D2345 | DRAFT | Single-source non-type second pass (`stage2_extract_nontype.py`). |
| D2399 | DEFERRED | Domain promote/demote — **FROZEN** (`d2399_promotions_frozen: true`); reopen only on full-corpus post-reclass counts. |
| D2462 | PLANNED | Unify single-source + singleton S2 into ONE extractor (2 passes). |
| D2084 | DEFERRED | PI/TI/GE/PT written to jsonl in S4 but never committed to DB (→ BUG-170). Registry has full description. |
| D2592 | DEFERRED | DSPy trainer ARCHIVED (BUG-168 wire-or-archive → ARCHIVE). Re-open gate (revised, D2594): Tier1 spotless + Tier2 statistically-clean + Tier3 ≥150 adjudicated (NOT all-1027). |

| D2611 | PLANNED | **Depth serving architecture** - the generative (S4, prompt-versioned) call stays labeler of record, the encoder becomes a regenerable selective cache; RETIRE the D2577 0.85 gate (labels self-agree only 69%, 30% unanimous -> unreachable by construction) in favour of kappa vs the frozen consensus core + coverage/precision + the 133-row core slice as CI regression; serve depth_scope broad|narrow (0.690 vs 0.645) for anything gating retrieval. |
### Sparse decisions — thin/empty descriptions in registry (reference links to full text)

`config/decisions.yaml` carries `description: "No description extracted"` for the DEFERRED INF/CLS batch (sync defect) and only a `summary` for D2164-D2166. Full decision text lives in the archived log — full path with line number:

| ID | State | Recovered title | Full path |
|---|---|---|---|
| D2164 | PLANNED | Claim-Level Verification: FActScore-style atomic claim decomposition | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:5725` |
| D2165 | PLANNED | Principle-Recall Benchmark: mandatory evaluation harness | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:5733` |
| D2166 | PLANNED | Semantic Chunking: rolling-window coherence detection (S1.1) | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:5739` |
| D2009 | DEFERRED | Confidence Formula deferred to empirical validation | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3216` |
| D2014 | DEFERRED | Phase 1.5: Modular Architecture | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3305` |
| D2015 | DEFERRED | Layer 2 Orchestration Spec validated, deferred to Phase 2 | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3324` |
| D2016 | DEFERRED | Lifetime License Model adopted | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3340` |
| D2049 | DEFERRED | Layer 2 Orchestration Spec (registered) | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3744` |
| D2050 | DEFERRED | Lifetime License Model (registered) | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3754` |
| D2056 | DEFERRED | Swappable Storage Backend Protocol | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3829` |
| D2057 | DEFERRED | Cross-Platform Memory + Process Protocol | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3836` |
| D2063 | DEFERRED | Hybrid Sync Protocol Stub | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3876` |
| D2064 | DEFERRED | Quality Tier System | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3883` |
| D2065 | DEFERRED | Current Architecture Future-Tax Assessment | `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md:3889` |

---

## 🟢 ACTIVE — in effect (475)

The 475 ACTIVE decisions are canonical rules in force (not "pending work"). **Machine list: `config/decisions.yaml`.** Recent critical ACTIVE decisions:

| ID | Decision |
|---|---|
| D2585 | **Label-quality architecture final verdict (roundtable adjudication + 2nd-round peer review, 2026-09-06).** RETIRE the full-corpus 3-model vote (supersedes D2582) and adopt a weak-supervision label model as the durable architecture: `gpt-oss teacher → { T-NLI + cleanlab + limited generative challenger } labeling functions → Snorkel/Dawid-Skene label model → human GOLD-A/B/CHALLENGE (300-500 stratified, book/author-disjoint) → ModernBERT-base classifier (train → temperature-scale → conformal/selective abstention)`. **MANDATORY LF-audit/dependency gate BEFORE `build_label_model.py`** (the LFs are NOT automatically independent — gpt-oss/NLI/cleanlab/challenger share correlated failure modes; alias-canonicalization is deterministic preprocessing, NOT a voter; cleanlab issue-probability is NOT a calibrated mislabel probability). Benchmarks: ΔF1 > +0.02 (label-model vs silver labels on ModernBERT) + >70% agreement on a 10% held-out flagged subset; selective prediction for the 61-way rare classes. Priority P0–P6 (P0 = train ModernBERT baseline NOW; P6 = retire `label_vote.py` to spot-checks). |
| D2587–D2600 | **Content-type ontology + 3-tier golden architecture (2026-09-08/09).** D2587 locked the 5-role `content_type` (principle/process_template/process_instance/growth_edge/tool_instruction) + 3 discriminators; D2588 roundtable adjudication; D2589 P0 injected rules into S2 + BUG-231 (convergent path = principle-by-design); D2590 `commit_non_fb_types` scoped build + P2 boundary-corpus scaffold; D2591 collision-row dispositions (noise_drop/quarantine); D2593 verification backlog (content_type only 3.9% human-verified → locked verification order); D2594 **3-tier golden architecture (Tier1 spotless / Tier2 statistically-clean / Tier3 boundary corpus)**; D2595–D2597 frontier-Qwen3.8 69-object seed + DeepSeek cross-check (depth 98.6% / discipline 97.1% / domains 98.6%); D2598 forensic audit + Qwen3.8 double-check + P1 propagation; D2599 P4 split-brain merge + P2 false-convergence audit (96 same-author echoes) + convergent=principle-by-design correction; D2600 H4 frontier-label back-propagation → golden+DB. |
| D2549 | Local-LLM delegation routing (task-type → model, enforced going forward): data-repair code-review → gemma-4-E4B-it-MLX-4bit (R5); classification → gpt-oss-20b-MXFP4-Q8; code-gen → Qwen3-Coder-30B one-shot; research → shell/curl. **AMENDED 2026-09-09 (user): R5 code-review of DB-mutating repair scripts → Qwen3.8-27B-MLX-4bit (more reliable than gemma-4-E4B); gemma stays for fast summarization/classification only.** |
| D2602 | **Label-classifier P5 freeze plan + P6 retire (2026-09-09).** `p5_freeze_plan.py` → `governance/p5_freeze_plan.{json,md}` + `p5_human_review_form.md`. macro-F1 0.2875 is DATA-LIMITED (18/61 disciplines <10 ex); tiers GOLD-A 135 / GOLD-B 892 / CHALLENGE 9; **bounded human-review queue = 69 FBs** (4 deferred + 65 challenger-abstain) = the immediate blocker. `label_vote.py` marked RETIRED-TO-SPOT-CHECK. |
| D2603 | **P5 DeepSeek adjudication of the 69-FB queue (2026-09-09).** Local-LLM challenger votes conflated domain/discipline (discredited) → `deepseek_p5_review.py` (DeepSeek-v4-pro, strict 61/43 separation + post-validation) → `governance/p5_deepseek_review.{json,md}` + `p5_human_review_deepseek.md`. **69/69, 0 contamination, 48/69 discipline changed vs silver.** DeepSeek overrides all 4 deferred local-LLM proposals (00156→systems thinking; 00423→theoretical physics; 00440→creative coding; 00602→generative design). Human remains arbiter. |
| D2605 | **P5 FINAL human adjudication applied (2026-09-09).** Arbiter ruled the A/B/C axes → `governance/p5_adjudication_final.json` + `scripts/propagate_p5_final.py`. **A content_type:** 9 noise_drop (00434/00972/00995/00984/00272/00975/00507 + already 00516/00548/00971), 4 principle kept (00423 Periodic-Table law, 00790 Virtuous-Design normative heuristic, 00278 Stigler's-Law empirical pattern, 00606 Variation-Decomposition technique), 00650 Metafont kept process_template. **B discipline:** 11 FIX_LABEL (00063→computer graphics; 00587→human-computer interaction reversing DeepSeek's sociology). **C domain:** 6 FIX_LABEL. **28 writes** → stage4_golden_mined.yaml + gold_frozen.yaml + maxwell.db (C13 backup). **FLAGGED:** 00631 domain "strategic thinking" = a DISCIPLINE (conflation) — NOT applied, needs re-decision. **AMENDED 2026-09-09:** 00631 resolved → discipline=risk management, domains=[ai & agents]; final 30 writes / 7 domain. |
| D2606 | **R5 review false-positive recorded (2026-09-09).** Qwen3.8-27B (user override D2549) REJECTED `propagate_p5_final.py` claiming sqlite3 "BEGIN within transaction" crash. Empirically false — script committed 28 rows, `integrity_check=ok`, spot checks pass; same BEGIN pattern in already-reviewed propagate scripts. APPROVED on empirical grounds; overruled as hallucinated bug. |
| D2607 | **Classifier 0.75-macro-F1 strategy (2026-09-09, data-backed).** Audit: 7,995 FBs / 2,603 convergent / 2,441 labeled; 29/61 disciplines <20 convergent ex, golden set still 18/61 <10 even after single-source backfill. P5 retrain → macro-F1 0.2036 (vs P4 0.2875) = no improvement, confirms data-limited not label-noise. **RULING:** (A) bare S2 re-run REJECTED (same corpus → same skew); (B) HIERARCHICAL head (61→~10-12 coarse groups) = structural fix; (C) LLM-HYBRID = now (ModernBERT student + gpt-oss fallback; KPI = end-to-end, not standalone); (D) targeted ingestion for ~18 starved disciplines = only genuine content fix. Sequence C→B→ingestion; Tier3 D2594 in parallel. 00631 resolved discipline=risk management, domains=[ai & agents]. **C CALIBRATION (2026-09-09, amend):** per-class selective thresholds wired (`pipeline/student_classifier.py` raw_predict + `thresholds.json`, R5 gemma-4-E4B APPROVE_WITH_CAVEATS, fixes applied) + `scripts/calibrate_student_thresholds.py`. **EMPIRICAL FALSIFICATION of C-as-is:** held-out student top-1 27.7% (wrong 72%), confidence compressed 0.05–0.39, cannot reach 90% precision at ANY coverage (best 75% @ 4%). Enabling now = wrong labels or ~always-abstain (zero savings + 596MB load). **FLAG LEFT OFF; RE-SEQUENCED: B hierarchical + targeted ingestion FIRST, then re-run calibration + enable C.** Mechanism ready — the DATA (student quality), not the code, blocks C. **B HIERARCHICAL RESULT (2026-09-09):** trained `classifier_hierarchical` (coarse 10-way + fine 61-way + domain 43-way). Held-out: coarse top-1 54.0% (macro-F1 0.46, 90% precision @ 20% coverage) vs fine-flat 28.7% vs fine-masked 24.8%. **Masked fine re-rank FALSIFIED** (coarse 46% error propagates unrecoverably); **coarse head is the keeper** — a 10-way student is a far better abstention signal than the 61-way. NEXT: wire the coarse head as the student signal; fine 61-way stays data-limited → targeted ingestion (D). **COARSE HEAD WIRED (2026-09-09):** `student_classifier.py` auto-detects flat vs hierarchical; `predict_coarse()` + coarse-gated `predict()` (emit only if coarse conf ≥0.70 AND coarse↔fine agree); config checkpoint→`classifier_hierarchical` + `coarse_threshold` 0.70 threaded via `pipeline_paths`/`stage4_merge`; R5 gemma APPROVE_WITH_CAVEATS. Flag OFF (coarse-gated predict abstains ~100% = safe). **INGESTION PLAN (2026-09-09):** `scripts/plan_targeted_ingestion.py` → `governance/targeted_ingestion_plan.{json,md}` → 18 starved = 9 CRITICAL (convergent≤3) + 8 HIGH + 1 MODERATE. **R5 QWEN3.8 RE-REVIEW (2026-09-10):** gemma overruled as unreliable; Qwen3.8-27B reviewed all 5 new scripts (`governance/r5_review_qwen38_session_2026-09-10.{jsonl,md}`) → all NEEDS_FIX; triage: C16 no-silent-errors + R14 stamps + C12 date/env-override + C18 docstrings + C20 named-constant fixed; C12/C20 module-constant findings triaged FALSE-POSITIVE (runtime config-driven at `stage4_merge`; named constants are C20-compliant). **SOURCE MAP (2026-09-10):** `feed.opml` gained a "Targeted Ingestion (D2607-D)" section (10 arXiv RSS feeds for the 9 CRITICAL disciplines) + `governance/targeted_ingestion_sources.md` (finding: prior feed.opml covered ZERO of them). |
| D2608 | **Forensic audit (2026-09-09) — R5 Qwen3.8-27B auditor + gemma-4-E4B verifier (cross-family; DeepSeek keychain blocked).** Deterministic checks clean (taxonomy 61/43, golden↔DB 1027/1027, label-map reconstruction == training logic). 6 findings all AGREE: **F1 [HIGH]** CHALLENGE boundary corpus 150/150 overlaps Tier2 training golden → BUG-233 (latent eval contamination, pending disjoint-vs-documented decision); **F2** checkpoint drift → FIXED (aligned both dirs to p5final); **F3** stale D2605 text → FIXED (amended 30/7/resolved); **F4 [HIGH]** student reconstructed label maps from live golden → FIXED (`label_maps.json` frozen with checkpoint); **F5** `_maybe_student_override` swallowed exceptions → FIXED (logger.exception + `student_override_error`); **F6** boundary source pools overlap training (subsumed in F1). |
| D2609 | **BUG-233 RESOLVED (2026-09-09) — option b+ boundary-corpus hold-out guard.** RULING: the D2587 CHALLENGE boundary corpus (150 cases) is a RULES-REGRESSION-ONLY content_type eval, NOT a model-eval benchmark; its example_ids are a HELD-OUT set any future content_type training must exclude. (a) rejected: 150/150 overlap with stage4_golden_mined is CROSS-TASK (discipline/domain TRAINING vs content_type EVAL), content_type rules-based today → zero contamination, and excluding 150 IDs would starve the data-limited discipline classifier. Plain (b) rejected as a prose latent-trap (corpus looks like a model-eval benchmark → future silent score inflation). FIX: `eval_scope=rules_regression_only` + `held_out_from_training=true` schema fields + `pipeline/boundary_holdout_guard.py` (`assert_no_training_overlap`, no-op for non-content_type). |
| D2540 | Measure-first verdict: REJECT full 7,995-FB reclassification; 0 axis leaks = structural proof only; semantic correctness is the unmeasured gap. |
| D2541 | Peer-review adoption + S4 integration (source_text/evidence injection, precision rules, batch 2×, thinking_budget 1.8×). |
| D2542 | Delegation boundary: Qwen3.8 = R5 auditor/2nd review; Qwen3-Coder = single-shot code-gen only; research NOT delegatable. |
| D2543 | Qwen3.8-27B = default research/spec/2nd-review model; invoke via **direct one-shot curl** (BUG-220: `delegate()` broken). |
| D2537 | Ranking fix + raw-label facet (opt-in). |
| D2532/D2533 | BUG-197 reclassification prep + corpus-aware pass-rate opt-in. |

> Full ACTIVE set lives in `config/decisions.yaml` — read fresh, do not trust any snapshot.

---

| D2610 | **DEPTH LABEL POLICY v2 (2026-09-10) - reliable-pair agreement, abstain instead of fabricate.** Reliable voters (DeepSeek-v4-pro + Qwen3.8-27B) must be unanimous; anything else ABSTAINS into governance/depth_review_queue.yaml; advisory voters recorded, never decisive; checkpoint upserted (BUG-234/235/236 resolved). Re-derived 996 FBs with no model calls -> 678 confirmed / 318 abstained. Controlled effect on the identical 133-row consensus slice: 0.4298 macro-F1 / 0.594 acc vs 0.4073 / 0.526 for the v1-labelled encoder, with 251 fewer train rows. Coverage cost 67%. |

## ⚪ DONE / CLOSED — bottom (84)

**RESOLVED:** D2032, D2351, D2352, D2353, D2355, D2356, D2357, D2358, D2359, D2361, D2454, D2483, D2544, D2545, D2550, D2551, D2552, D2553, D2554, D2555, D2556, D2557, D2558, D2559, D2560, D2561, D2562, D2563, D2564, D2565, D2566, D2567, D2568, D2569, D2570, D2571, D2572, D2573, D2574, D2575, D2576, D2577, D2578, D2579, D2580, D2581, D2583, D2584, D2586, D2601, D2604, D2605, D2606, D2607, D2608, D2609, D2610
**SUPERSEDED:** D2070, D2080, D2085, D2087, D2091, D2100, D2223, D2224, D2253, D2293, D2294, D2296, D2317, D2318, D2430, D2582
**ARCHIVED:** D2000, D2001, D2002, D2034, D2052, D2195, D2196, D2204
**REJECTED:** D2005, D2008, D2010, D2028, D2074, D2221, D2226, D2383

> Full titles/descriptions for all 83 are in `config/decisions.yaml` (state ∈ {RESOLVED, SUPERSEDED, ARCHIVED, REJECTED}).
