# Maxwell OS v3.0 — DECISION LOG (tiered)

> **Updated:** 2026-09-20 | **Machine source of truth:** `config/decisions.yaml` (651 decisions)
> **Archive (full append-only history):** `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md`
>
> **Convention (standing rule):** OPEN/PENDING at the top (most critical first) → ACTIVE in-effect → DONE/CLOSED at the bottom. A decision is "done" only when its `state` is RESOLVED/SUPERSEDED/ARCHIVED/REJECTED.
>
> **Heading convention (D2552):** tier sections are `## 🔴 OPEN / PENDING`, `## 🟢 ACTIVE`, `## ⚪ DONE / CLOSED`. Entries use `| ID | State | Decision |` table rows. Historical `### D#### — Title` / bare `## D####` formats remain as-is (append-only history); NEW entries MUST use the table format. Reconcile `DECISION-LOG.md` ↔ `config/decisions.yaml` via `scripts/recompute_decision_summary.py`.

---

## 2026-09-22 — D-332 (community-benchmark-first rule + mlx-dspark M1 net-loss + on-device sweep) — RESOLVED

| ID | State | Decision |
|---|---|---|
| D-332 | RESOLVED | **STANDING RULE — community benchmarks outrank vendor claims.** Weight community results on *matching hardware* above vendor numbers measured on newer chips (use both). Evidence: `ARahim3/mlx-dspark#38` on the exact M1 Max 64 GB shows speculative decode is a **NET LOSS** (0.55–0.91×; round cost ~2.4× a decode step, verify compute-bound on the old GPU). mlx-dspark *runs* on M1 but does not help. **Consequence: D-293 (oMLX MTP) re-scoped to measure-before-adopt**; D-294 (oQ4e/oQe quant) + D-292 (cache fix) outrank it (M1 Max is bandwidth-bound). On-device sweep (topics `on-device-ai`/`on-device-llm`): TinyChatEngine REFERENCE (AWQ+Metal, M1), LiteRT-LM WATCH (mobile-first), needle/cactus WATCH (121M tool-call/extraction head), BigMoeOnEdge/PrismML-Bonsai WATCH/REJECT. **No engine out-serves oMLX on M1 Max.** Artifacts: `governance/MARKET_RESEARCH_20260922_M1.md`, `feed.opml` (+2 topics, +6 evaluated engines). |

## 2026-09-22 — D-333 (MTP A/B instrument + knowledge-pipeline & skill-orchestration sweep) — RESOLVED

| ID | State | Decision |
|---|---|---|
| D-333 | RESOLVED | **(1) D-293 re-scope instrument** — `scripts/mtp_ab.py` drafted + compiles: toggles `mtp_enabled` in `~/.omlx/model_settings.json` (crash-safe + .bak, C6/C13) → `omlx_reload`, measures decode tok/s on a frozen batch (stream=True ttft split, non-stream fallback), appends labelled JSONL, `--compare A B` prints WIN/LOSS/NEUTRAL (adopt MTP only if WIN on this M1 Max, D-332). temp=0.0 (R7), model/URL from config (C12). **(2) Knowledge pipeline & skill orchestration sweep** (`governance/MARKET_RESEARCH_20260922_PIPELINE.md`): MUST-REFERENCE nano-graphrag (local GraphRAG) + GraphRAG/HippoRAG/RAPTOR papers + MCP patterns (github-mcp-server, context7); SHOULD-REFERENCE fastembed-rs local reranker (rerank after bge-m3); ADAPT LightRAG + skill.md schema; WATCH Graphify/sibila/n8n; REFERENCE-only microsoft/graphrag, instructor/outlines, LangGraph/CrewAI (no new deps, C2/C5). No tool displaces S0–S6 + goose-recipe design. |

## 2026-09-22 — D-293 RESOLVED (MTP A/B executed on M1 Max)

| ID | State | Decision |
|---|---|---|
| D-293 | RESOLVED | **Lightning MTP measured on THIS M1 Max — NEUTRAL, not adopted.** `scripts/mtp_ab.py` A/B (frozen 8-prompt S2 batch, stream=True ttft split, temp=0.0): **MTP OFF 7.93 tok/s vs MTP ON 7.74 tok/s = 0.98×** (median 7.94 vs 7.80, n=8 each). Slightly negative, within noise. Confirms community evidence (mlx-dspark#38): speculative decode is a net loss on M1 Max (D-332). Vendor +34-58% targets LONG decode; S2 emits short JSON (31–50 tok) where verify overhead can't amortize. `mtp_enabled` restored to `false` (production state). Instrument fixed to send API-key auth (oMLX has 401 auth enabled). Remaining M1 Max levers: D-294 (oQ4e/oQe quant A/B) + D-292 (cache fix). |

## 2026-09-22 — D-334 (Metal cap) + M1 Max "best config" applied

| ID | State | Decision |
|---|---|---|
| D-334 | ACTIVE | **Metal wired-memory cap below oMLX ceiling.** `omlx.process_memory_enforcer` logs Metal cap 48–51.8 GB < oMLX 56 GB ceiling (`iogpu.wired_limit_mb` unset). Raise with `sudo sysctl iogpu.wired_limit_mb=57344` to wire more of 64 GB for weights/KV. Surfaced only (sudo). |

**M1 Max "community best config" (oMLX 0.7 profile/template system):** wrote `config/omlx_m1_best_config.yaml` (per-model intent spec) + `scripts/omlx_apply_best_m1_config.py` (apply/measure/system classes). Dry-run confirms all `apply` settings are **already at target** — the live config is already M1-appropriate (mtp/dflash/ANE-prefill/SSD-offload all off; guided_grammar on for extraction/classifier; thinking off). Measurement-gated levers (D-294): `turboquant_kv_enabled` (KV-cache quant → decode bandwidth) and `specprefill_enabled` on Qwen3-Coder; `turboquant_kv` on gpt-oss. Quant *variant* A/B (oQ4e/oQe/Q4) needs a download (only single variants present locally). `scripts/omlx_lever_ab.py` = generic per-model flag A/B harness (compiles).

## 2026-09-22 — D-294 lever A/B: turboquant_kv = LOSS on S2 (keep false)

| ID | State | Decision |
|---|---|---|
| D-294 | ACTIVE (partial) | **turboquant_kv_enabled A/B on Qwen3-Coder S2 — 0.65x LOSS (median 0.81x), NOT adopted.** `scripts/omlx_lever_ab.py` (6-prompt frozen batch, stream ttft split, temp=0.0): kv_off mean 161 tok/s vs kv_on 105 tok/s (median 122.7 vs 99.4). Restored to `false`. Caveat: high variance (outputs 45–2161 tok; different length distributions per arm) — median is the robust signal. Expected result: KV-cache quant only helps LONG context; S2 emits short JSON so quant overhead > bandwidth saving. Remaining D-294 levers: specprefill (Qwen3-Coder), turboquant_kv on gpt-oss (LONG-context S4 = the meaningful KV-quant test), quant-variant A/B (needs download). |

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
| D2622 | PROPOSED | **PRACTICALITY/APPLICABILITY FILTER (S5, use-case calibrated).** Separate practical (directly applicable ~20s, no over-analysis) from theoretical/abstract principles. Config-driven (C12) with the public Anytype use case (design + business) baked into `config/practicality.yaml`. Rubric: "in the context of {use_case_domains}, can an agent apply this principle to a concrete task within ~20s without over-analysis?" → immediately-applicable | context-dependent | abstract. Reuses existing signals (application / procedural_skill / is_summary / accessibility); swappable (C21). |
| D2621 | PROPOSED | **DISTINCT-FACET-AWARE SEMANTIC DEDUP.** SHA-256 + cluster-before-extract dedup is within-cluster only; S4 HDBSCAN cross-cluster dedup was REMOVED (D2120/D2198) → cross-cluster paraphrases survive. bge-m3 cosine scan of 6,525 pool: 1,381 pairs >0.80 (33 >0.90). KEY: embedding cosine OVER-MERGES distinct facets — Visual-Hierarchy-Through-[Contrast/Spacing/Proximity/…] are 9 DISTINCT mechanisms, NOT duplicates. Correct signal = same MECHANISM + definition + application → merge; different mechanism → keep. Method: MinHash LSH → SemDeDup-style cluster-then-dedup → mechanism-aware reliable-pair judge → human review. |
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

## 🟢 ACTIVE — in effect (477)

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
| D2612 | **CONTENT-TYPE ADJUDICATION + DEPTH RELABEL SCOPE (2026-09-11).** 217 unlabeled golden-mined rows human-adjudicated then R5-verified by DeepSeek-v4-pro on full text (definition+mechanism+boundary). Agreement 201/217 = 92.6% (up from 79.3% first pass); 16 contested -> governance/content_type_contested_16_form.md. Frozen non-principle rate 15.7-16.6%, confirmed-principle 82.0%. BUG-239 FIXED (form generator dropped boundary 217/217 + truncated mechanism 185/217). RULING: depth relabel scoped to confirmed-principle subset, NOT 7,995. **CORRECTED by D2613: production principle = 61.0% (pilot), not 82.0%.** D2610 policy ported to scripts/label_vote.py. |
| D2613 | **GOLDEN-SET TRUST GAP + VERIFIED-CORE INVENTORY (2026-09-11).** The 1,027-example "golden" set is gpt-oss teacher silver — every rationale says "NOT hand-reviewed" (provenance gpt-oss 1027 / DeepSeek 0 / human 0). Verified labels: content_type 314, domain/discipline 138, depth 133+69; **4-axis intersection = 69 (frontier69) = 6.7%**. Canonical counts corrected to 43 domains / 61 disciplines. RULING: freeze a human+DeepSeek-verified core (69→~150) as the sole eval target, demote the 1,027 to silver pool, no further classification/voting until the verified core exists. Joint-vote pilot: production principle 61.0%, relabel target ~3,800-4,900 rows. Strategy: object type at S2 (S4 trusts), depth = reliable-pair + encoder cache, domain/discipline = bge-m3→taxonomy-match, one-model end state via weak-supervision seeded from the verified core. |
| D2615 | **S4 ACTIVE-LEARNING STRATIFICATION (2026-09-13).** The 2,729 needs_review rows are honest abstains (pair disagreed), not errors — no automated resolver exists (3rd-voter 44.7%, bge-m3 20%, ModernBERT 27.7%, Snorkel/Dawid-Skene 48.7%). Bulk-reviewing all 2,729 is the anti-pattern active learning avoids. RULING: stratify by (axis, disagreement-pair) — depth abstain 79% domain↔cross-domain (827), content_type abstain 68% noise_drop↔principle (1,148) — sample a boundary batch (target 300, per-stratum floor 3), human-adjudicate only that, remainder → persistent abstain review queue (never fabricate). IMPLEMENTED: config/s4_active_learning.yaml + scripts/build_active_learning_sample.py → governance/s4_active_learning_sample.{jsonl,md} (298: 190 content_type + 108 depth) + s4_review_queue.jsonl (2,431) + s4_active_learning_report.json. Deterministic (seed 0), vote-only, C6 atomic. The human sample seeds the future free fine-tune (retire DeepSeek per D2607/D2611). |
| D2616 | **S2/S4/S5 FORENSIC AUDIT ADJUDICATION + ULTIMATE SOLUTION + PHASE 0 EXECUTED (2026-09-13).** Four frontier auditors (Claude/GPT/GPT-5.6-Luna/Qwen) forensically audited S2/S4/S5 at commit 6e295d4; goose + Qwen3.8-27B verified every claim deterministically. VERIFIED: commit_non_fb_types:false discards 1,147/8,410 (13.6%) non-principle; route=FB→principle fallback (BUG-148 third drift); golden 1,027 = 93.3% unverified silver (69 = 6.7% 4-axis verified); schemas.py Pydantic never instantiated. REJECTED: Qwen's "38% corrupted" (real number = 93.3% unverified) + "retire gpt-oss now + Snorkel" (Dawid-Skene already 48.7% false-flag). ULTIMATE SOLUTION (4 phases): P0 stop bleeding → P1 freeze ~435 verified rows → P2 local $0 label stack (weak-sup + hierarchical ModernBERT + SetFit + conformal + S5 classification-entailment) → P3 gated gpt-oss retirement → P4 rebuild once + 11-mode invariant gates. DeepSeek unusable for open-ended adjudication (BUG-243). **PHASE 0 EXECUTED:** commit_non_fb_types:true; route deprecated (missing ct→quarantine, never principle; quarantined sidecar); scripts/apply_phase0_relabels.py applied 1,365 relabels (principle 7,966→6,601; noise_drop 1,054 / PT 179 / PI 121 / TI 16 / GE 17) with C13 backup + R14 manifest + integrity_check ok; Pydantic runtime boundary (validate_fb_content_type/depth) wired fail-closed into S6 insert_fb. 199 tests green. |
| D2617 | **VERIFIED-CORE FREEZE + PHASE-1 FINALIZE + SPOTLESS RECOUNT (2026-09-13).** Phase 1 COMPLETE: `scripts/build_verified_core.py` (deterministic, LLM-free) froze the sole eval target `governance/verified_core.jsonl` = **443 unique rows** (149-core + 298-sample; 4 fb_ids overlap → 149+298=447 additive). R14-stamped; `verification_status` honest — **human-verified 28 / joint-vote-verified 121 / pending-human 294** (the 298-sample D2615 boundary batch is NOT yet human-adjudicated; carried with `disagreement_pair`, never re-branded verified). Retires BUG-241 "93.3% unverified silver" AT THE DATA LEVEL: the 1,027 `stage4_golden_mined.yaml` is demoted to a silver candidate pool; eval must use `verified_core.jsonl`. Also applied the 149-core finalize: #85 Iterative Design Refinement depth domain→cross-domain (human); `scripts/apply_phase1_finalize.py` materialized 88 DB state changes (8 content_type flips, 49 depth flips, 66 PASS / 22 QUARANTINE) + blanked the 21 residual non-principle depth rows (29→0); C13 backup + R14 manifest + integrity_check ok; post-finalize fbs 7,995 = PASS 3,012 / QUARANTINE 4,983, non-principle-with-depth = 0. **SPOTLESS RECOUNT** (deterministic on `golden_synced_4axis.jsonl`): content_type+depth DeepSeek+Qwen/human cross-checked = **702** (561 principle + 141 non-principle); strict 4-axis (ct+depth verified AND discipline/domains non-silver p5:*) = **153** (111 + 42); discipline/domains non-silver total = **209/1,027** (the binding constraint — DeepSeek+Qwen have NEVER voted domain/discipline, only content_type+depth, so "4-axis DeepSeek approval" is not yet claimable). VERDICT: the verified set is far too small to beat gpt-oss on the 61/43 taxonomy (61 disciplines ≈ 16.8 ex/class, 19 classes <10); it is sufficient only for a local coarse 7-way content_type + 4-way depth gate and as the frozen eval core. |

| D2618 | **A/B-GATED S4 ARCHITECTURE ADOPTION (2026-09-13).** Three frontier auditors produced three divergent classifier architectures — Claude: hierarchical ModernBERT + SetFit rare-leaves + conformal; Qwen: RAC (bge-m3 cosine-to-definitions + SetFit, rejecting the brittle `_masked_fine_pred` hierarchy); GPT: contract-first (4-axis gold as authority, classifier replaceable) + flat+conformal. **RULING: A/B-test the ARCHITECTURE choices; do NOT A/B the CORRECTNESS prerequisites** (deterministic, already cross-adjudicated). **(1) NON-NEGOTIABLE P0 (0 LLM):** split `verified_core.jsonl` → immutable `gold_4axis/pending_4axis/silver_4axis` (never re-merge tiers); normalize `p5:*` provenance (`p5:claude+guman`/`+juman`/`claud+human` → `p5:claude+human`); re-PASS the 1,750 pair-agreed high-confidence principle rows wrongly quarantined (verify count vs live DB, C13+R14); reconcile the 25 fb_ids missing from review queue; wire `gold_4axis.jsonl` into all `train_*.py` `load_golden_set()` + archive `stage4_golden_mined.yaml` from eval. **(2) A/B HARNESS (reuse D2577/D2610 fixed-split):** frozen gold_4axis held-out, identical metrics (macro-F1, coverage@precision, abstain rate). ARM-1 classifier = hierarchical vs RAC vs flat+conformal ($0 local); ARM-2 CRIBS = gpt-oss vs Qwen3-Coder on frozen D2293 benchmark (retain gpt-oss until replacement WINS); ARM-3 abstention = raw 0.35/0.70 vs conformal/selective vs SetFit calibration. NO architecture committed until arms report. **(3) UNCONDITIONAL FIXES:** `_masked_fine_pred` all-`-inf` flat-logit fallback; S5 char→token truncation (DeBERTa WordPiece); remove dead `route=FB` from S2; S5 classification-entailment. **HONEST GUARANTEE:** 100% prevention of silent acceptance outside the confidence envelope, NOT semantic 100% accuracy. |

**D2618 P0 EXECUTED (2026-09-13, commit 31be38f):** (1) `scripts/build_4axis_tiers.py` split `verified_core.jsonl` (443) → immutable `gold_4axis.jsonl` (76: 52 principle + 24 non-principle) / `pending_4axis.jsonl` (294) / `silver_4axis.jsonl` (73, dominated by disc/dom `golden-silver` 59 + depth-silver 10). Strict content_type authority = {human, joint-vote, 298-human} (excludes the `golden`/`none` silver-family sources) — 76 not the earlier 80. (2) `scripts/normalize_provenance.py` canonicalized 6 cells (3 rows × disc+dom) in `golden_synced_4axis.jsonl`. (3) `scripts/repass_pair_agreed.py` re-PASSed **exactly 1,750** pair-agreed clean principle rows (status QUARANTINE→PASS + 381 depth syncs; C13 backup + R14 manifest) → PASS 3,012→4,762, principle-QUARANTINE 3,513→1,763. (4) `scripts/reconcile_review_queue.py` deduped the checkpoint (25 dup fb_ids → union-abstain sidecar) + appended the 25 missing abstains to `s4_review_queue.jsonl` → 0 missing. (5) `train_*.py` gained `load_gold_4axis()` (JSONL + DB text-join) wired as the `GOLDEN_EVAL` held-out split; `stage4_golden_mined.yaml` git-mv'd to `archive/golden_retired_D2618/` (silver = train-only, never eval). post-P0 `just health` 10/10, integrity ok, non-principle-with-depth=0. **P1 LAUNCHED (in-flight):** `scripts/build_discipline_domain_vote.py` votes discipline+domain (the only axes the pair never voted) on the 216 principle rows of the verified core via DeepSeek-v4-pro + Qwen3.8, reliable-pair unanimous else abstain. FIRST FINDING: discipline unanimous ≈ 4/5 but domain EXACT-set unanimous ≈ 1/5 — multi-label domains disagree on granularity even when both models agree on the core (e.g. {ai & agents} vs {ai & agents, code & computation}), so strict-set unanimity over-abstains domains. ETA ~3.5h serial (OMLX ~48s/row prefill-bound on the ~2.4K-token taxonomy prompt). **P1 VOTE COMPLETE (2026-09-14):** 216/216 principle rows voted discipline+domain, zero voter errors, checkpoint-only (no DB writes). Review sheet `governance/s4_discipline_review_sheet.csv` (63 contested) + retry sheet `governance/s4_discipline_null_retry.csv` (5 Qwen null-discipline). **P1 FOLLOW-THROUGH COMPLETE (2026-09-14, D2633/D2634):** all 63 contested human-adjudicated (62 + Mythic-Cosmogonic→`cultural studies` user-ruled); 5 null rows resolved (D2623/D2624); domain-aggregation ruled **overlap→union incl. DeepSeek** (D2633) + re-aggregated via `scripts/aggregate_domain_votes.py` → 148/216 accepted. |

| D2619 | **4-AXIS ANCHOR CONSOLIDATION (2026-09-14, RESOLVED + EXECUTED).** Merge the 5 scattered adjudication files (verified_core 443 / d2615 298 / frontier69 69 / p5 29 / s4 discipline 63 + domain 216 verdicts) into `verified_core.jsonl` **gap-fill-only**. TRUE principle count ≈ 324 (216 stale core + 108 hidden principles in d2615). **Anchor FROZEN at 216** = 200 canonical-spotless + 1 emerging (Law of Truly Large Numbers) + 15 single-model/null stragglers (4 content_type `golden` + 10 depth `golden-silver` + 5 null discipline). The **108 d2615-principle rows** (content_type-only, no depth/disc/dom) are a SEPARATE expansion queue — NOT merged into the frozen anchor (content_type re-verify first; a ~10% sample shows methods/case-studies mislabeled principle). Human discipline rulings locked: Leverage-Points→systems-thinking, Value-first/Value-vs-Goodness→strategic-thinking, Visual-Effects-Workflow→computer-graphics, Aesthetic-Symbol-Substitution→aesthetics, Counterculture-Marketing→cultural-design; abductive pair → keep convergent (merge single-source restatement). **EXECUTED (scripts/merge_4axis_adjudication.py):** 443 rows → 216 principle (215 non-duplicate + 1 abductive duplicate), 6 locked rulings applied as `p5:human-locked` overrides (they CONFLICTED with the reliable-pair vote: e.g. Leverage Points vote=decision-making → user=systems-thinking), 108 emitted to `governance/expansion_queue_108.jsonl`. Two bugs fixed in the merge: (1) content_type gap-fill was folding the 108 into the 216 (dry-run "principle 324" → now 216); (2) spotless metric rejected `p5:human-frontier69`/`p5:human-d2615` as non-authoritative (undercount). |
| D2620 | **DISCIPLINE↔DOMAIN NON-CONTAMINATION GUARDRAIL (2026-09-14, RESOLVED + user-confirmed).** Formalizes D2512-D2516 (demote 9 applied-practice pseudo-disciplines → domains; 66→61 disciplines). The 61 disciplines and 43 domains are DISJOINT vocabularies (verified: 0 overlap, only shared `emerging` catch-all); crossing them is a HARD error → fail-closed. `validate_discipline_domain()` added to `pipeline/schemas.py` (shared, always-on) + CI test `tests/test_taxonomy_disjointness.py::test_validate_discipline_domain_guard`. **CONFIRMED: `psychology` / `design psychology` = discipline-only; `marketing & communications` = domain-only.** Wire into merge/relabel/S4 on every label write. Reference error caught: `marketing & communications` (domain) proposed as a discipline. |

| D2623 | **STRAGGLER RE-VOTE (2026-09-14, RESOLVED).** `scripts/revote_stragglers.py` re-voted the 6 post-merge stragglers via the reliable pair (D2610 unanimous-else-abstain). 3 RESOLVED → gold: Dynamic-System-Contextual-Dependency depth=universal, Feminist-Data-Visualization discipline=visual-semiotics, Infrastructure-As-Creative-Medium discipline=cultural-design (source `p5:reliable-pair-D2619-revote`). Fixed DeepSeek empty-content bug (max_tokens 512→2048; v4-pro burns reasoning tokens). Final tiers: **gold_4axis 228 (211 principle + 17 non-principle) / pending 190 / silver 25**. |
| D2624 | **STRAGGLERS RESOLVED (2026-09-14, RESOLVED).** User ruled the 3 non-unanimous stragglers: Historical-Thinking-Approach-in-Engineering → discipline=**engineering** (NOT DeepSeek's "systems-thinking" — a reliable-pair false-positive: it's a method-for-engineering, not a systems field); Semiospheric-Limitation → depth=**cross-domain**; Simplicity-Through-Constraint → depth=**universal**. Applied as `p5:human-locked`. **Anchor now 214 spotless + 1 emerging (Law-of-Truly-Large-Numbers) + 1 abductive duplicate = 216.** |
| D2625 | **FORENSIC AUDIT (2026-09-14, RESOLVED) — 5 findings, all fixed.** (1) D2620 guard was DEFINED+TESTED but NOT WIRED (blindspot) → now fail-closed in the merge. (2) AUTHORITY-SET DRIFT: `p5:reliable-pair-D2619-revote`/`p5:human-locked` in tiers but not merge → a re-run would undo re-votes. Fixed (sets MATCH, import-compared). (3) DEDUP PLAN ERRORS: judge over-merged "Iterative Design Refinement" (distinct) + missed "Iterative Prompt Refinement (2)" (name collision). Corrected. (4) 273 candidate groups are NAME-STEM collisions (first-token "design"/"iterative"), NOT concept-duplicates — 269 unjudged. (5) 35 "(N)"-suffix name-collision rows = highest-confidence dup signal (32 with live base). DEDUP POLICY LOCKED: mark `duplicate_of` + QUARANTINE, NEVER delete. |
| D2626 | **AUTHORITY-SET CONSOLIDATION + GUARD WIRING (2026-09-14, RESOLVED).** The authoritative-provenance sets were duplicated across merge + tiers (D2625 finding #2 drift class). Fixed: `pipeline/axis_authority.py` = single source of truth (import-time subset assert); both consumers import it. Verified byte-identical output (tiers 231/189/23; merge 214 spotless/1 straggler/108 queue). D2620 guard now ALSO wired fail-closed into S4 (`stage4_merge.validate_classification`) + S6 (`stage6_commit.insert_fb`). |
| D2627 | **DEDUP EXECUTION — 32 "(N)"-SUFFIX JUDGE + 269 PRE-FILTER (2026-09-14, RESOLVED).** (1) 32 name-collision `(N)` pairs judged mechanism-aware via Qwen3.8: `(N)` suffix is NOT auto-duplicate — only same mechanism+application merges. Verdicts → `governance/dedup_suffix_judgments.json`. (2) Remaining 269 name-stem groups pre-filtered deterministically: **0** pairs have def+mech Jaccard ≥ 0.35 → pure name-stem collisions, no judge run warranted. Policy locked: mark `duplicate_of` + QUARANTINE, never delete. |
| D2628 | **DOMAIN-AGGREGATION POLICY FORMALIZED (2026-09-14, RESOLVED).** The policy was implicit in human verdicts (216/216 `p5:human`) but never recorded. Measured: reliable-pair votes are ADVISORY; final set is human-curated (union 94 / intersection 22 / one-voter 38 / hand-curated 62). NO mechanical union/unanimity rule. Future auto-aggregation (148 rows): exact-set unanimity (19.5%) vs overlap/union = STILL an OPEN user decision (flagged, not resolved here). |
| D2629 | **108-QUEUE CONTENT_TYPE RE-VERIFY (2026-09-14, RESOLVED).** The 108 d2615-principle rows kept out of the frozen anchor were re-verified on content_type via Qwen3.8 (D2587 7-way). MEASURED: **49/108 = 45.4% NOT principle** (39 process_template + 4 noise_drop + 4 tool_instruction + 1 growth_edge + 1 process_instance); only 59 remain principle. FAR higher than the forensic ~10% sample — the queue was majority methods/case-studies (Naumburg Scribble Technique, Customer Discovery Method, N-gram Token Prediction, Grounded Theory). Verdicts → `governance/content_type_reverify_108.json` (read-only). Follow-up: depth+discipline+domains re-vote for the 59 principle rows. |
| D2630 | **DEDUP APPLY — duplicate_of + QUARANTINE (2026-09-14, RESOLVED, never delete).** `scripts/apply_dedup_marks.py` added `fbs.duplicate_of` (safe migration) + marked **17 rows** duplicate_of + QUARANTINE (separate from PASS). 17 = 7 locked user-confirmed (4 stems) + 10 judge-confirmed `(N)`-suffix duplicates. 22 `(N)` pairs ruled DISTINCT (name collision, different mechanism). 1 conflict: judge said "Iterative Prompt Refinement (2)" DISTINCT, locked plan (D2625 #3) says DUPLICATE → LOCKED WINS. DB PASS 4762→4745 / QUARANTINE 3233→3250, 0 deleted, integrity ok. |
| D2631 | **QUEUE-59 3-AXIS RE-VOTE (2026-09-14, RESOLVED).** `scripts/revote_queue_59.py` voted **depth + discipline + domains** (3 axes in ONE prompt) on the 59 principle rows remaining after D2629 content_type re-verify (49/108 non-principle). Reliable pair (DeepSeek-v4-pro + Qwen3.8-27B), D2610 unanimous-else-abstain per axis (never fabricate). **59/59 voted**: depth unanimous 36 / discipline 36 / domains 14. D2633 union aggregation (`aggregate_domain_votes.py`) → **34 accepted**; `apply_queue_59_anchor.py` (C13 backup + R14 manifest + re-tier) → **20 full 4-axis rows into `gold_4axis` (214→234 principle)**; 14 depth-abstained + 23 contested-discipline + 2 disjoint stay pending-human. |
| D2632 | **A/B HARNESS ARM-1 FIRST RESULT (2026-09-14, RESOLVED).** `scripts/ab_harness_arm1.py` evaluated **flat** (`classifier_modernbert_p5final`) vs **hierarchical** (`classifier_hierarchical`) on the FROZEN `gold_4axis` eval split (214 principle rows, D2618 P0.5 contract-first). RESULT: **FLAT discipline macro-F1 0.229 BEATS hierarchical 0.175** (coarse-gating hurts on the verified core — consistent with D2607 masked-fine falsification); **domain head near-useless for BOTH** (macro-F1 0.009 flat / 0.007 hier — 43-way multi-label starved, confirms D2613 that domain needs bge-m3 taxonomy-match, not the sigmoid head); **confidence compressed** (precision 1.0 only at ~0.5% coverage). Latent mismatch surfaced: `label_maps.json` n_discipline=56 vs model `discipline_head`=61 (harness infers true head size from state_dict). Output → `governance/ab_harness_arm1.json`. |
| D2633 | **DOMAIN-AGGREGATION AUTO-POLICY (2026-09-14, RESOLVED — user ruling).** Deterministic from the 216 P1 votes: discipline unanimous **150/216 (69.4%)**; domains EXACT-set unanimous **42/216 (19.4%)**; overlap 116; disjoint 2 (among unanimous); **auto-acceptable 148/216 (68.5%)**. **USER RULING: overlap→union (B) — final domain set = sorted union of both reliable voters, ALWAYS including DeepSeek's classification; disjoint → abstain.** `scripts/aggregate_domain_votes.py` (deterministic, LLM-free) → `governance/p1_domain_aggregation.json`: **148 accepted** (42 exact + 106 union), 2 discipline-unanimous disjoint → domain-abstain, 66 contested discipline. Same policy applies to the 59 queue rows (D2631). |
| D2634 | **CLASSIFICATION-ACCURACY DEPENDENCE (2026-09-14, RESOLVED analysis, CORRECTED).** Question: can discipline/domain accuracy be increased, or does it need a bigger anchor? **MEASURED ANSWER: accuracy is dominated by per-class TRAINING-sample count + label quality, NOT anchor size or architecture.** Training set = the **RETIRED gpt-oss SILVER pool** (`archive/golden_retired_D2618/stage4_golden_mined.yaml`, 1027 ex, **93.3% unverified** per D2616; retired D2618 P0.5, train-only): 61 disciplines avg 16.8 ex/class, 18/61 <10; 43 domains avg 2.22 labels/row, 11 domains <20 positives. ARM-1 (D2632): flat 0.229 vs hierarchical 0.175 discipline macro-F1; domain head near-zero 0.009. The anchor (gold_4axis, 214 rows) is the **EVAL/measurement** set — growing it improves measurement trust (35/56 eval classes ≤3 rows), **NOT accuracy**. To increase accuracy: (1) targeted ingestion of the 18 starved disciplines (D2607-D: 9 CRITICAL convergent≤3 + 8 HIGH + 1 MODERATE); (2) clean labels via reliable-pair relabel (D2610) or weak-sup seeded from the verified core (D2585); (3) **domain → bge-m3→taxonomy-match (D2613, training-free), NOT the sigmoid head.** **ROOT CAUSE: the classifier trains on UNVERIFIED silver — the verified core (214 rows) is too small to train a 61-way head, so the silver pool is both too small AND unverified.** |

## ⚪ DONE / CLOSED — bottom (97)

**RESOLVED:** D2032, D2351, D2352, D2353, D2355, D2356, D2357, D2358, D2359, D2361, D2454, D2483, D2544, D2545, D2550, D2551, D2552, D2553, D2554, D2555, D2556, D2557, D2558, D2559, D2560, D2561, D2562, D2563, D2564, D2565, D2566, D2567, D2568, D2569, D2570, D2571, D2572, D2573, D2574, D2575, D2576, D2577, D2578, D2579, D2580, D2581, D2583, D2584, D2586, D2601, D2604, D2605, D2606, D2607, D2608, D2609, D2610, D2612, D2613, D2619, D2620, D2623, D2624, D2625, D2626, D2627, D2628, D2629, D2630, D2631, D2632, D2633, D2634, D2635, D2636
**SUPERSEDED:** D2070, D2080, D2085, D2087, D2091, D2100, D2223, D2224, D2253, D2293, D2294, D2296, D2317, D2318, D2430, D2582
**ARCHIVED:** D2000, D2001, D2002, D2034, D2052, D2195, D2196, D2204
**REJECTED:** D2005, D2008, D2010, D2028, D2074, D2221, D2226, D2383, D2614

> Full titles/descriptions for all 92 are in `config/decisions.yaml` (state ∈ {RESOLVED, SUPERSEDED, ARCHIVED, REJECTED}).

---

## 2026-09-17 — D-271 identity rulings (see governance/DECISION_D271_IDENTITY_20260917.md)

**D-271a — RESOLVED.** The `research methodology` (discipline, 261 rows) vs `research & methodology`
(domain, 648 rows) collision is ruled **TWO CONCEPTS**: sharpen both definitions and add each to the other's
`exclude`; the 167 rows carrying both go to human gate G8. Feasibility evidence: collapsing the discipline
costs 261 relabels, forces 94 rows into the `emerging` fail-closed catch-all and destroys the exact-match
facet key that `depth: cross-domain` depends on (789 rows); collapsing the domain costs 648 rows of recall
and leaves 150 rows with zero domains. Option A costs 0 migrations and 167 adjudications, and is reversible.
Rationale for treating discipline as the primary retrieval facet: it is single-valued (1.00 labels/row,
100% coverage, exact `=` filter) while domains fan out 1..7 per row.

**D-271b — RESOLVED.** LINK supersedes MERGE. Measured: the production identity rule can produce only
**6 name-identical clusters / 12 rows (0.15% of the KB)**; the algorithmically flagged set is 273 groups /
662 rows, of which a MERGE would delete **389 rows**. LINK loses 0 rows and duplicates nothing in retrieval
once `duplicate_of IS NULL` is honoured. D2627 had already ruled this; it was never wired up.

**D-271c — RESOLVED.** Adopt a stable `concept_id` (minted once, never recomputed) with authority control
(prefLabel/altLabel) and re-key the 164,202 internal edges to it; demote `fb_id` to an alias. A/B test:
S1 alone FAILS (164,202 edges keep the stale content hash), S2 alone FAILS (5 labels carry >1 concept),
S1+S2+S3 PASSES (0 broken edges, 0 rows lost, 0 ambiguous labels). Measured cost of the status quo: one
rename of the highest-degree marked object orphans 320 edges.

**D-271d — RESOLVED (no human needed).** Wire `duplicate_of IS NULL` into `pipeline/retrieve.py`, replace
the `domains LIKE` substring match with JSON-aware membership, and index `fbs(discipline)`/`fbs(domains)`
(BUG-275).

**Interim rule in force (part of D-271c):** NO renames — object names, discipline, domain or content_type —
until the identity layer exists. Cost 0; it prevents the only irreversible event in the taxonomy.


## 2026-09-19 — D-272 / D-273 / D-274 rulings (see governance/ROUNDTABLE_CROSSEXAM_20260919.md)

| ID | State | Decision |
|---|---|---|
| D-272a | RESOLVED | **The ruler is certified.** 150 blind human labels (100 proportional stratum A + 50 forced-minority B), no stored-label column exposed. Valid: confirmation of everything downstream. |
| D-272b | ACTIVE | **THE AXIS INVERSION** — retrieval facets ranked inversely to measured reliability: FORM 0.831 unused, discipline 0.506 the primary exact filter, ROLE 0.740 with lift −0.010. |
| D-272c | RESOLVED | **Constrained, definition-anchored classification supersedes D2138 free generation** — the free-generation prompt (stage4_merge.py:345/468 with the :13 docstring claiming the opposite) is the root cause of the 999-rule alias map. |
| D-272d | OPEN | Split QUARANTINE into UNVERIFIED | CONTRADICTED. |
| D-272e | OPEN | Relevance becomes its own axis (relational, per Saracevic 2007). |
| D-272f | RESOLVED | **Instrument repair, NOT re-engineering.** The ontology is structurally sound; 5 bounded repairs. |
| D-272g | **WITHDRAWN 2026-09-19** | F-14 was retargeted to ROLE on a pocket contrast that is **statistically null** (BUG-296). The action survives for a different reason: FORM is already the best-measured axis. **Do not quote the retarget.** |
| D-273a | RESOLVED | Facet predicates in EVERY retrieval leg + assert on the fused pool (implemented 2026-09-19; constraint-violation 0.5911 → 0.0000). → G12 ✅ |
| D-273b | RESOLVED | Write-guard SPLIT into row guard vs vocabulary lint (implemented 2026-09-19; `research methodology` writes clean). → G18 ✅ |
| D-273c | OPEN | Graph expansion must propagate/report the neighbour's OWN tier. |
| D-273d | OPEN | Index what is already in the DB (body fields into FTS; evidence_passages as a leg). → G15 |
| D-273e | OPEN | Work-identity dedup at ingestion (source_diversity counts filenames: 29.1% of "convergence" is one book twice). → G14 |
| D-273f | OPEN | emerging must stop being a facet value (447 PASS discipline rows, 744 domain rows). |
| D-273g | OPEN | Chunk/evidence leg at step 8 (the join is 100%: 205,813/205,813; ~214k vectors). → G16 |
| D-273h | OPEN | Cross the ruler strata with status; report both frames. |
| **D-274a** | **RESOLVED 2026-09-19** | **The serving gate is a function of the verification record.** `scripts/apply_serving_gate.py` is the single writer: status := `verification_results[factual].passed` + typed `s5_reason`; PASS 4,745 → 3,299; CI invariant 0 violations; duplicates hard-quarantined. → **G17 ✅** |
| **D-274b** | **RESOLVED** | **ROLE is the highest-leverage axis, not decorative — D6 / BUG-280 are INVERTED.** The gating axis has lift −0.010 over a constant; ~a quarter of served rows are not principles by a human reading (13 false positives in the served set, 29 true principles hidden). |
| D-274c | RESOLVED | **The ruler FLOOR column is void** — an accuracy was compared to a provenance share. All STOPPED/CONTINUE verdicts withdrawn; only the constant-baseline lift stands. **G4a WITHDRAWN.** |
| D-274d | RESOLVED | **No label carries human provenance** (no content_type_source / discipline_source column). min_human_share is unsatisfiable ⇒ **no axis may gate a model comparison** ⇒ S2/S4 must not be trained or swapped on the current labels. |
| D-274e | OPEN | Persist the tier stage 5 already computes (epistemic_status / isor / verification_method) and compute the verifier stamp from config. → G19 |
| D-274f | OPEN | **The anchor is a conformance set, not a training set** (ANCHOR-1 frozen 150 + 51 abstentions; ANCHOR-2 ~100 fresh rows after the vocabulary freeze; 30-row test–retest; per-axis positive/near-neighbour/OOV/contradiction sets; must-link pairs; known-item queries from source_segments). |
| D-274g | OPEN | **Implement the decision procedure the config already declares** (content_type_rules / D2587 + route_to_content_type / D2128) instead of free generation; allow none; render menus from config with a menu_hash stamp. |
| D-274h | RESOLVED | **One writer for the serving gate** (implemented 2026-09-19: `pipeline/serving_gate.derive_status()`; dedup/reinject/stage5 routed through it; `duplicate` reason declared in config). → G20 ✅ |


## 2026-09-21 — D-290..D-296 rulings (M1 Max hardware optimisation → oMLX 0.7 runtime → goose → typed-decision)

See `governance/MARKET_RESEARCH_20260921.md`. Hardware anchor: MacBookPro18,2 · M1 Max · 64 GB ·
400 GB/s · macOS 27 Golden Gate · oMLX.app **0.7.0.dev4**.

| ID | State | Decision |
|---|---|---|
| D-290 | RESOLVED | **M1 Max optimisation program.** Decode is bandwidth-good; prefill/TTFT is the binding constraint. Levers: MTP, oQ4e, hot-RAM prompt cache, KV quant, wired memory. Hard limits: no NAX / neural accelerator / CED-relevance / Cluster v2; Apple AFM weights closed (C2/C3). Pipeline priority: S2 (top) → S4 → S5. |
| D-291 | RESOLVED | **Pin oMLX 0.7.0.dev2** (dev4 has a documented external-server/no-auth startup bug; Maxwell exposes external server_aliases with no auth) or enable API-key auth. |
| D-292 | ACTIVE | **D2460 cache-thrash re-check.** Live `~/.omlx/settings.json` has `cache.enabled=true` + `gdn_ssd_split_enabled=true` — the exact thrash flags. Re-assert `assert_omlx_no_cache`. |
| D-293 | ACTIVE | **Lightning MTP for Qwen3-Coder (S2).** +34–58% decode, lossless at temp=0.0 (R7-safe). |
| D-294 | ACTIVE | **oQ4e/oQe quant A/B (S2/S4)** under the A10 instrument. |
| D-295 | RESOLVED | **goose→oMLX already wired** (`maxwell_omlx.json`); the bug is `active_provider: custom_deepseek` (DELEGATE-001). Switch to `maxwell_omlx`; pin recipe temp 0.0. |
| D-296 | ACTIVE | **Typed-decision bake-off (S5)** — benchmark laya-mlx/jevmlx vs DeBERTa-v3 NLI + constant on the 150-row ruler (ADAPT D-275c). |
| D-297 | RESOLVED | **Phase 3 executed + bake-off scaffold repointed (exec D-295/D-296)** — goose active_provider custom_deepseek→maxwell_omlx; custom_deepseek disabled. bakeoff DEFAULT_SHEET→150-row ruler, DEFAULT_KEY→anchor1_frozen, AXIS→discipline, load_ground_truth parses frozen rows. Revealed arm-layer gap: ruler CSV keys by item_id (not fb_id) + DISC/FORM col names ≠ axis keys → item_id→fb_id join + col-name map required before arms run. Phase 4 assessed: no ruler-sheet conflict; defer per plan gate. |

Phase 0 DONE: `defaults write com.electron.goose NSWindowOcclusionDetectionEnabled -bool false`
(live bundle id — the legacy `com.block.goose` in D2262/D3251 is stale).

## 2026-09-20 — D-275..D-285 rulings (ruler inversion → R5/R1/R2 → CT-boundary + A/B → discipline boundaries)

| ID | State | Decision |
|---|---|---|
| D-275a | RESOLVED | **Ruler key inversion** — blind human label = ground truth; stored label = artefact under test; report error rate, never "accuracy"; abstentions kept, never imputed. |
| D-275b | RESOLVED | **Content-type guardrail** — principle/process_template discriminated by procedural INTENT + done-condition, not step count. |
| D-275c | RESOLVED | **System One / Jev (TypeSafe AI) REJECT** as pipeline dependency; ADAPT the calibrated-decision + typed-abstention framing. |
| D-276 | RESOLVED | **Full-axis inverted re-score** — stored error CT 0.353 / DISC 0.474 / FORM 0.283; 8 zero-agreement discipline slots. |
| D-277 | RESOLVED | **Three clarifications** — R5 is repair-not-demote; raw AND canonical are both post-hoc model stamps (corpus has zero human labels); the error rate is a meter, never a label-picker. |
| D-278 | RESOLVED | **R5 repair execution** — OntoClean definition + include + exclude drafted for the 7 weak slots (never demoted). |
| D-279 | RESOLVED | **R1 closed menu + menu_hash + *_source provenance columns** — traceable labels (`min_human_share` prerequisite). |
| D-280 | PROPOSED | **Single-coder ceiling** — 30-row second-coder blind sheet prepared (human gate). |
| D-281 | RESOLVED | **R2 definition-anchored NLI** — verify a label against its menu definition (R5 override first). |
| D-282 | RESOLVED | **Depth-vs-role conflation fix** — "3+ domains" is the universal-DEPTH threshold, not the principle-ROLE discriminator. |
| D-283 | RESOLVED | **CT boundary sharpening** — principle↔growth_edge↔process_template SHARPEN + BOUND (epistemic STATUS + procedural INTENT, NOT scope); ratified 2026-09-20. |
| D-284 | RESOLVED | **R2 A/B verdict** — paraphrase (arm C) beats definition as mislabel detector (91% vs 55% wrong-contra); keep NLI on content_type, adopt paraphrase. |
| D-285 | RESOLVED | **Discipline boundary re-derivation** — cognitive science / design psychology / psychology / behavioral economics / design thinking made mutually exclusive (symmetric excludes); ratified 2026-09-20. |
| D-286 | RESOLVED | **D-285/D-283 execution** — raw-alias cross-listings among the 5 core resolved + definitions folded into canonical (menu_hash cac6e695…); BUG-309 resolved; BUG-307 r5_hash stamping. |
| D-287 | RESOLVED | **Domain raw-alias cross-listing resolution** — 37 rulings applied (BUG-310); 0 cross-listings on both discipline + domain axes. |
| D-288 | RESOLVED | **R2 corpus NLI source selection + provenance drift** — run arm-C meter over stage4 (freshest checkpoint labels, option B); BUG-312 documents the three-snapshot drift (stage5 Sep4 < stage4 Sep11 < DB Sep19). |
| D-289 | RESOLVED | **Cognitive-science boundary post-D-285 (BUG-313)** — widen the definition (Option A): de-negated in r5 + taxonomy; contra 94% → 4%; menu_hash → 73597ee2. |
| D-298 | RESOLVED | **ANCHOR-1 R2 kappa computed + bake-off arm layer wired (exec D-296/D-297)** - discipline kappa 0.4395 (n=59, po=0.4746, error 0.5254); contra 0.4193 / clean 0.4578; domains micro-kappa 0.5765 (contra 0.5953 / clean 0.5477), mean Jaccard 0.4515, exact set 9/60; content_type kappa 0.0 with pipeline_distinct=1 (pipeline predicts ONE class). Repair queue 55/60 rows (>=1 axis). Arm layer now config-first (config/eval_integrity.yaml bakeoff: block): item_id->fb_id join, column-name map (DISC (1-62)/FORM (1-4)/CT (1-7)), constant arm scores the modal HUMAN label. Constant baseline on the frozen ruler discipline axis = **error 0.931 (n=116)** - the bar every arm must beat. Artifacts: governance/anchor1_kappa_20260921.json/.md, governance/bakeoff_typed_decision_20260921.json. |
| D-299 | PROPOSED | **Three follow-ups from the ANCHOR-1 audit (ratify in one pass)** - (a) BUG-316: point goose providers.maxwell_omlx.model at gemma-4-E4B-it-MLX-4bit for agentic turns and keep Qwen3-Coder for one-shot generation only (DELEGATE-002); (b) BUG-314: re-stamp the frozen ruler csv_sha256 + record the normalisation map so byte verification stops failing closed; (c) normalisation policy: same-spelling alias resolution at read time (already implemented in scripts/anchor1_kappa.py) is the sanctioned path - never edit a blind sheet. |
| D-300 | RATIFIED (2026-09-21, owner) | **Typed-head (Jev-clone) adoption rule for S5/decision layer** - benchmark-only, never a dependency (D-275c, C1/C2). Gate 0 PAPER AUDIT (licence, weights downloadable, native schema, tokenizer, MLX, training-data provenance) before any install; champion = mizorewww/laya-mlx (ModernBERT encoder + decision head, MLX, architecture-matched to the incumbent so any delta is attributable to the training objective); second = Zefan-Cai/Open-Jev single-scalar head tested ONLY as an abstention/rerank score on the incumbent output, never as a label source; bnsd55/jevmlx third; daseinlabs/open-jev REJECT (unlicensed, do not vendor). Pre-registered margin: deploy only if the frozen 150-row ruler error rate (116 human discipline rows) improves by >=5pp vs the incumbent (0.474 -> <=0.424) at equal-or-lower abstention, deterministic decode, same 61-slot menu. Label SEMANTICS stay frozen: a head whose schema differs may only be projected (mapping layer) or used as a score, because swapping the schema invalidates D-285/D-289 boundary repairs + the kappa frame (C4). Arms already registered in scripts/bakeoff_typed_decision.py (arm_typed_head stub). |
| D-301 | RESOLVED | **Bake-off report layer + validity guards; role-matched arm matrix v2 (exec D-300)** - ran deberta+qwen3coder arms on the frozen ruler: deberta error 0.931 = constant baseline (108/116 errors, error-set Jaccard 0.862 -> degenerate, F-17 strongest form); qwen3coder abstained 116/116 (BUG-319, parse masking -> INVALID). Added scripts/bakeoff_report.py (local metric recomputation, DEGENERATE flag, abstention sweep, D-300 verdict) + margin persistence (BUG-321) + config-driven report block. v1 arm matrix benchmarked the incumbent OUTSIDE its production role (61-way zero-shot ranker) - v2 must test the verifier pairwise and the labeler on the menu. Protocol pre-registered: governance/BAKEOFF_PROTOCOL_20260921.md. |
| D-302 | RESOLVED | **Arm matrix v2 (role-matched) + calibrated abstention + repair triage (exec D-300/D-301)** - new arm_pairwise reproduces the incumbent's PRODUCTION role (verify the stored label): error 0.4741 (55/116) == the independently known pipeline discipline error 0.474 (harness cross-validated). Calibrated abstention on the verifier margin is monotone and useful: 0.474 -> 0.423 (10% abstained) -> 0.391 (25%) -> 0.328 (50%); the same sweep on the zero-shot framing was flat/noise (0.931 -> 0.942), so abstention claims are role-specific. Repair triage of the 60-row anchor: 31 boundary, 44 domain under-prediction, 36 over-prediction; systematic never-emitted menu gaps = social sciences (8), personal productivity (6), research & methodology (5), systems & frameworks (4); falsely-emitted = marketing & communications (6), business operations (6), legal & public policy (4). Also fixed the report verdict reference (BUG-322: incumbent, not the constant floor). |
| D-303 | RESOLVED | **BUG-319 root-caused (LLM arm 404), harness now emits real LLM decisions (exec D-300/D-302)** - arm built OMLX_URL + /chat/completions while OMLX_URL carries no /v1 => HTTP 404 on every row, recorded as an abstention. Fixed config-first (bakeoff.omlx_path=/v1/chat/completions) + diagnostic reason taxonomy (ok/model_abstained/unresolved_choice/parse_error/http_error). Audit: all production callers already use /v1 => defect contained to the harness, no cascade. Post-fix proof: 10/10 rows decided. Full 150-row arm relaunched. |
| D-304 | RESOLVED | **D-300 RATIFIED (owner, 2026-09-21) + first real verdicts: no candidate labeler beats the incumbent** - pairwise (incumbent, production role) err 0.474; qwen3coder LLM labeler err 0.526 => gain -5.2 pp => **REJECT** (adoption condition not met, production unchanged). Error-set Jaccard vs incumbent 0.468-0.482 => the two labelers fail on largely DIFFERENT rows: the promising direction is arbitration/ensemble, not substitution. Abstention: NLI verifier margin better at 10% (0.423 vs 0.471), tie at 25%, LLM confidence better at 50% (0.259 vs 0.328). Harness artifact now merges at write and the report warns when the incumbent arm is absent (BUG-323). |
| D-305 | RESOLVED | **Gate-0 paper audit PASSED for laya-mlx (exec D-300)** - Apache-2.0, pip-distributed, MLX-native (no PyTorch/Transformers), HF weights 421M/322M multilingual, **caller-supplied criteria vocabulary => our 61-label menu is passed directly, no projection layer, no label-semantics conflict**, 0 output tokens, ~690-945 MiB peak. Residual: 61-way criteria untested at scale, multilingual checkpoint required, HF revision + checkpoint licence must be pinned (R14). jevmlx schema check still open. |
| D-306 | RESOLVED | **Arbitration analysis: agreement is a high-precision filter; a post-hoc rule beats the incumbent (needs held-out validation, NOT adopted)** - incumbent 0.474 (script cross-validated on the same number). Labelers agree on 39.7% of rows (46/116) where error is only 0.103; oracle headroom = 48 rows (perfect arbitration would reach 0.293 vs 0.474). Rule R2 (agree->accept, disagree->human) = 10.3% error on 40% coverage, 70-row human queue. Rule R3 (disagree->higher-confidence arm) = 0.414 => +6.0 pp vs incumbent (above the 5 pp bar) and R4 = 0.448 => +2.6 pp: both discovered POST HOC on the same 116 rows, so D-300 forbids adoption until validated on held-out labels. |
| D-307 | RESOLVED | PART1 B normalisation applied (config/normalization_map.yaml) -> domain observed agreement 0.3938 -> 0.4385. PART1 A premise DISPROVED: all 8 gap domains already exist in v5.5, so no slot was added; the defect is that the pipeline never SELECTS existing slots (assignment/emission problem, not ontology gap). PART2 B item 1 settled by owner = DIFFERENT (boundary: mechanism vs behaviour); 15 pairs remaining, one at a time. |
| D-308 | RESOLVED | **Normalisation map wired into the kappa layer - and a cross-axis leak caught before it shipped.** Ablation on identical taxonomy bytes separates the effects: WITHOUT the map domains micro-kappa 0.5765 / mean Jaccard 0.4515 / OOV 3; WITH the map 0.5931 / 0.4737 / OOV 2 - i.e. the whole D-307 -> D-308 delta is the map itself, no confound, both figures reproducible on demand. BUG-325: the map was first merged into the SHARED alias dict, so it also rewrote DISCIPLINE tokens (`human-computer interaction` -> `human computer interaction`, rows 25/46) and depressed discipline kappa to 0.4051; it is now domain-scoped, so discipline stays 0.4395. CORRECTED (D-310, S3 audit): slot reachability measured on the whole corpus - knowledge pipeline/maxwell.db 7,995 rows emits ALL 61 discipline and ALL 43 domain slots (min 6 rows, median 85; 13/61 disciplines below 20 rows). The earlier 'these slots are never selected' reading came from the contra-stratified 60-row ANCHOR-1 sample (covers only 23/61 disciplines, 33/43 domains), i.e. a sampling artifact, not a global assignment failure. Real signal: 4,696/7,995 rows (58.7%) sit in QUARANTINE and the top-6 disciplines hold 38.2% of the corpus. |
| D-309 | RESOLVED | **Phantom taxonomy version removed - v6.0 -> v5.5.** `apply_menu_repair_v6.py` bumped the ontology file to v6.0 while `config/version.yaml` + `config/pipeline_config.yaml` stayed v5.5, and `TAXONOMY_VERSION` (v5.5) is what gets STAMPED on every FB (R14) - one ontology, two version strings, and the stamp was the stale one. Forensic audit: the bump was content-safe (parsed tree identical to `.bak_v5_5` minus the version strings and two meta keys; the alias/exclude churn vs git HEAD is the documented Sep-20 D-285/D-286/D-289 work). v6 added ZERO slots, so the honest state is v5.5; the marker now lives as `meta.menu_repair_20260921_*`. |
| D-310 | RESOLVED | **Assignment path measured - the "never selects existing slots" premise is CORRECTED.** Whole corpus (`knowledge pipeline/maxwell.db`, 7,995 rows): ALL 61 discipline + ALL 43 domain slots are emitted (min 6 rows, median 85; 13/61 disciplines < 20 rows), top-6 disciplines = 38.2%, QUARANTINE 58.7% / PASS 41.3%. The old reading came from the contra-stratified 60-row ANCHOR-1 sample (23/61 disciplines, 33/43 domains). Mechanism: labels are chosen against the FULL closed menu; `candidate_pool/top_k` belong to `retrieval_benchmark.py`, not to the classification path. Real defects (deterministic meter): 403 FBs raw-without-canonical (BUG-150 class), 354 emerging+empty raw, 147 both-axes, 703 without domain, 0 unknown labels. Standing rule: whole-corpus measurement before any "never emits" claim. |
| D-311 | PROPOSED | **R3 held-out validation pre-registered.** R3 (+6.0 pp) was derived on the 116 ruler rows, so D-300 blocks adoption; the held-out set (ANCHOR-1 60 rows minus the 2 ruler overlaps, n=58) is frozen with metric, bar (>= 5.0 pp, equal-or-lower abstention, deterministic decode) and the R2 queue rule written down BEFORE any run. |
| D-312 | PROPOSED | **Calibrated abstention designed, not enabled.** margin -> t_low (abstain to repair queue) / t_high (accept + flag); measured incumbent curve 0.474 -> 0.423 -> 0.391 -> 0.328 is monotone but role-specific (flat in the zero-shot role). `config/verify_abstention.yaml` ships `enabled: false` and is read by no production code - stage5_verify stays fail-closed (D-2298), zero behaviour change. |

| D-313 | RESOLVED | **Frozen-artifact provenance rule + BUG-328 landing** — an artifact grounding a published number must be committed and cited by sha256; a freeze-time hash matching no repo version is a FAIL-CLOSED abort (BUG-329: ruler v0 `4d0c856a` lost / HEAD `2d456720` / working `38323192`, substantive drift 41 CT / 7 DISC / 62 FORM cells — BUG-314 corrected). Landed the reviewed G19/D274h + R1/D-279 + D275b/D282/D283 + D-291/D-293 set (audit: py_compile clean, 200/201 tests, gate dry-run 0/7,995 writes, menu_hash match). New: BUG-330, BUG-331. |

<!-- s7-sync 2026-09-21 -->

### D-314 (RESOLVED, 2026-09-21) — R3 arbitration REJECTED on held-out data
The R3 combine rule (+6.0 pp in-sample) gains **0.00 pp** on the pre-registered 58-row held-out set
(n_scored=57) at equal abstention; R2 clears the error bar only by queueing 75.4% of rows (violates the D-300
abstention clause); R4 is −8.77 pp. **Not adopted** — incumbent pairwise verifier and `serving_gate` unchanged.
Evidence: `governance/R3_HELDOUT_RESULT_20260921.md`, `governance/r3_heldout_20260921.json`,
`governance/R5_REVIEW_R3_ADAPTER_20260921.md`. D-311 stays PROPOSED (its run happened; the answer is REJECT).
Also D-312: label sources are config objects and bake-off artifacts never merge across sources (BUG-332).

## D-315 (2026-09-21, RATIFIED) — The canonical ruler is the frozen authority JSON; the CSV is a workspace
**Context.** BUG-329 left the ruler in three versions and made "which ruler?" undecidable from filenames, while the
`ANCHOR-1` name was shared by a second, unrelated 60-row instrument (BUG-337).
**Decision.** `governance/anchor1_frozen_20260920.json` (`sha256 0ec321a7…`) is THE ruler — authority for the 150
blind human labels AND for the measurement. `RULER_BLIND_SHEET_20260917.csv` (HEAD `38323192…`) is the human
editing **workspace** and the only record of *why* a cell abstained; it is never the answer key. `2d456720…`
(commit `986fbc4`) is a **superseded draft** — adopting it would silently move 41 content_type + 7 substantive
discipline HUMAN labels and re-baseline every floor. `4d0c856a…` is **byte-lost / label-verified-identical**; D-313's
fail-closed trigger is answered by this explicit ruling, not by an abort on a lost file. The 60-row instrument is
**ANCHOR-2** (`73597ee2`), a separate instrument that may never be pooled or concatenated with the ruler.
**Rule added.** An artifact is authority only if it is committed, immutable and sha256-cited; a CSV a human still
edits is a workspace, and a scorer must read truth from the authority (C21). An evaluation *output* is never a label
record — the authority's stored side carries the scorer sentinel `emerging_dump`, which is now a declared mapping
(BUG-338). Untested blind-ness is not blind-ness: the ruler scorer carries `--self-test-blinding`.
**Evidence / verification.** Re-scoring from the authority reproduces the published numbers exactly — CT 0.3533 /
DISC 0.4741 / FORM 0.2828 — identical to the workspace path, so the ruling moves **no published number**; blinding
self-test PASS 3/3; `config/eval_integrity.yaml:ruler_authority` declares all paths, hashes, the menu hash,
`truth_source` and the pooling rule. Audit: `governance/FORENSIC_AUDIT_20260921c.md` (F-01..F-12).
**Also ratified as administrative:** D-314 (R3 not adopted; D-311 closed as measured-rejected).
**Not closed by this decision:** the second-coder gap (F-11) — no floor may be repointed on a single coder.
## D-316 (2026-09-21, RATIFIED) — The answer key is one artifact; an annotation may come from a second, hash-pinned one
**Context.** D-315 made governance/anchor1_frozen_20260920.json the canonical ruler. Session 9 found the cost:
the authority stores a human abstention as JSON null, so `blank` (a datum, never imputed) and `emerging` (an
explicit abstention) are indistinguishable in it (34 DISC nulls = 28 + 6), and a re-score driven only by the
authority silently rewrote the published annotation line to `{blank: 34}`.
**Decision.** The authority remains the only ANSWER KEY. The abstention REASON is restored from the human
workspace, whose sha256 is declared in config, and ONLY where the authority cell is empty; declared drift is a
fail-closed abort (C16/D-313), never a silent fallback. Numbers are invariant to the overlay (verified: CT
0.3533 / DISC 0.4741 / FORM 0.2828, scored_n 150/116/145, blinding self-test PASS).
**Rule added.** D-316: an evaluation artifact may read at most ONE answer key; any additional read must be
hash-pinned, single-purpose (annotation, never truth) and fail-closed on drift. A canonical artifact that cannot
express a distinction the measurement uses must say so in config, and the surviving provenance of that
distinction must be named.
**Also recorded.** BUG-341: the stage5 snapshot rotation means a "restored checkpoint" is not a durable state;
the live path is absent and the bytes are preserved as `.stale_20260921_185942` (2c206a25…), declared in
config:label_snapshots. Deliberately NOT copied back: that would re-arm a silent resume from pre-repair labels.
**Not closed.** F-11 (no second coder), BUG-312 (three divergent label snapshots), BUG-343.


## D-317 (2026-09-21, RATIFIED) — The human attestation is SIGNED: "human-anchored" is now EVIDENCE

**Context.** Every model-accuracy number in this repo is measured against 150 blind human labels
(`governance/anchor1_frozen_20260920.json`, `0ec321a7…`). The labels were human-blind *by construction* and the
label conversion was verifiable (0 CT diffs, 0 substantive DISC/FORM diffs vs the workspace), but the link between
the labels and a human author rested on reconstruction. A signed, scoped, hash-cited statement was the one missing
element — and it was the reason no claim here could honestly be called "attested".

**Decision.** The owner signed the reserved line on 2026-09-21:

> `human_attestation: "these 150 labels are mine, made blind to pipeline output."`

It is recorded machine-readably in `config/eval_integrity.yaml:ruler_authority.human_attestation` together with the
scope (n=150, 100 stratum A + 50 stratum B), the signer and the date, and the sha256 of the artifact it attests
(`governance/anchor1_frozen_20260920.json`, `0ec321a7…`).

**What it converts.** "human-anchored" moves from *verified-by-reconstruction* to **ATTESTED**. The owner gate that
reserved the line is CLOSED. Live owner gates drop from three to two: (1) the benchmark-only laya-mlx install in an
isolated venv with a pinned revision; (2) the abstention operating point `t_low = p25` (`enabled: false`).
No published number moves: re-scoring from the authority reproduces CT 0.3533 / DISC 0.4741 / FORM 0.2828 exactly.

**What it does NOT convert.** Attestation is not independence. `second_coder_required_before_repointing: true` still
has no second coder behind it (F-11), so NO floor may be repointed: every floor in this repo is single-coder, and is
now single-coder-*attested* rather than single-coder-unattested. The gap is smaller; it is not closed.

**Rule added.** D-317: an attestation is a **dated, scoped, hash-cited record** naming the exact artifact it
attests, and it lives machine-readably (config-first, C12). Prose may say "attested" only when such a record exists;
a bare quoted sentence is not an attestation. Corollary: when a human gate is closed, the artifact that recorded the
gate must be updated in the same session — a gate left "open" in config after it was answered is a governance
contradiction, not a conservative default.

**Not closed.** F-11 (no second coder), BUG-312 (three divergent label snapshots), BUG-341 (live stage5 checkpoint
absent), BUG-343 (smoke test cannot show its own failure output), BUG-344 (declared pins were not enforced in the
scorer run path — see below).

**Also recorded (same session).** BUG-344: `authority_paths()` never read the `*_sha256` fields declared in
`config/eval_integrity.yaml`, so the annotation drift guard shipped as a config declaration that the run path did
not enforce — the artifact cited an EMPTY `annotation_sha256`. Fixed by wiring the declared pins into the run path
fail-closed (C16); the artifact is regenerated and now cites the hash it actually consumed.

| D-319 | RESOLVED | **The ANCHOR-2 domain disagreement is emission coverage + surface spelling, not an ontology gap (BUG-348 fix).** The first worksheet generator compared cells with a bare `.lower()`, never consulted the alias layer, and showed the owner `most_common(16)` — so it reported 2 stray-quote artifacts and 4 surface variants as MENU GAPS, and truncated PART 2 at 16 rows. Corrected reading: 7 slots UNEMITTED_EXISTING (the real Emission defect), 4 surface variants already resolved by `config/normalization_map.yaml` (D-307) + `raw` aliases, 2 sheet artifacts, **NOVEL = 0**. PART 2 is 26 pairs / 31 rows, each now carrying its `definition` excerpt. The corrected artifact is a NEW file (the ruled worksheet is evidence, R-D410) and is stamped with the sha256 of every input it read (D-318). **NOVEL=0 means no floor may be repointed and no kappa may be re-based on menu grounds.** Two defects logged on the way: BUG-354 (the shared resolver rejects the catch-all on both axes) and BUG-355 (a dead entry in the `domains:` block of normalization_map; the flat index makes one surface string resolve to two canonicals). **Not applied:** nothing was wired into the classifier prompt — a settled pair is a ruling, not behaviour. |

| D-320 | RESOLVED | **Owner rulings 2026-09-21 (four): normalization_map pruned; PART 2 boundary items 24/26 REJECTED; `behavioral economics` re-read from the taxonomy; laya + repair-queue recommendations recorded.** (1) The owner pruned the dead `human-computer interaction: human computer interaction` entry from `config/normalization_map.yaml` -> **BUG-355(b) CLOSED**, and the prune is **inert by measurement**: `scripts/anchor2_kappa.py` re-run produces a byte-identical `governance/anchor2_kappa_20260921.json` (domain 0.4385, macro_kappa_active 0.4906, jaccard 0.4426, active_domains 39 unchanged), so no published number moves; BUG-355(a) (flat index / `kind=None` order dependence) stays OPEN. (2) Owner **rejected** boundary items 24 and 26 because the `behavioral economics` terminology was mis-stated; the re-read (from the taxonomy text, not memory) gives BE three load-bearing requirements — **R1 object** (an economic decision: price, purchase, demand, incentive, market), **R2 mechanism** (psychological cause: heuristic, framing, affect, social norms), **R3 stance** (descriptive, never prescriptive) — with `excludes` = economics, psychology, cognitive science, design psychology, decision making. Items 24 and 26 dropped R1 and mis-read `incentive/price/uncertainty` as BE when that is `economics`, which BE excludes. Corrected definition-anchored tests **24'/26'** are drafted in `governance/BOUNDARY_DISCRIMINATORS_20260921.md` **Part D** (the rejected text stays visible: R-D410). (3) The re-read exposed a real **ontology defect, BUG-357**: BE's written definition is **narrower than its operational denotation** — row 60 (*Same-age Peer Modeling*, no economic object) is labelled BE while the definition string licenses `psychology`, which is what the pipeline answered. A classifier whose only BE evidence is the definition string must reproduce that error, so **no boundary rule can fix it**. Owner gate: (i) widen the `definition:` string to name the mechanism class + behaviour-change object (**recommended**) or (ii) keep it and re-label row 60. No slot moves either way (denotation, never spelling). (4) **laya-mlx**: recommendation recorded — approve a narrow **benchmark-only feasibility arm** (isolated `.venv_laya`, revision + checkpoint licence pinned in config, zero production imports, measuring the one untested question: 61-way `criteria` degradation), but hold the full D-300 A/B until a **second coder** exists on the ruler, because a >=5 pp win measured against single-coder attested labels (F-11/D-317) cannot license adoption; `arm_typed_head` stays a stub meanwhile. (5) **repair_queue**: recommendation recorded — **do not create** `governance/REPAIR_QUEUE.md`; declare the write-path + `fb_id` de-dup key + owner instead (BUG-358), since the queue's only writer (the abstention rule) does not exist, so a file created today could never receive a row (an Emission-class artifact) and an empty queue would assert "no repairs pending". **Not applied:** nothing wired into any prompt, no menu slot added, no canonical renamed, taxonomy bytes unchanged. |

| D-321 | RESOLVED | **`behavioral economics` definition widened — the ontology fix for BUG-357 (owner-ruled, option i).** `config/taxonomy_v5.yaml` `definition:` now names the mechanism class (heuristics, framing, affect, social norms, peer influence) and the second object class (behaviour-change interventions), keeping "describes the bias; does not exploit it to design persuasion" and all five excludes (`economics`, `psychology`, `cognitive science`, `design psychology`, `decision making`); `raw` aliases untouched; **0 slots added** (43/61 unchanged). Because the definition is what the classifier reads, this is a **denotation** change: bytes `8d3c90e9…` -> `994e056b5e04ef1f37d350c0faae87e344da5cf85da2e405a8825d1f8f840312`, and `version`/`classification_version` -> **v5.6** with `taxonomy_version: v5.5 -> v5.6` synced in `config/version.yaml` + `config/pipeline_config.yaml` so the stamped `TAXONOMY_VERSION` (R14) distinguishes the two emission behaviours — otherwise two classifiers would share one stamp (D-309 was a phantom bump because it added zero slots; this one changes denotation, so the bump is required). The answer-space pin `config/closed_menu_v5.sha256` is UNCHANGED (the menu was not touched). Effect on row 60 is **predicted, not measured** until the boundary wiring + an S4 run happen. |
| D-322 | RESOLVED | **laya-mlx Phase A (benchmark-only feasibility sandbox) EXECUTED; Phase B held (owner-approved recommendation).** `pip install laya-mlx` 0.1.0 into an isolated `.venv_laya` (gitignored, zero production imports, D-275c). API inspected: `Agent.predict` / `Router.predict` / `presets` / `load` + `detect_language`/`is_english` (multilingual), and the menu plumbed as **62 caller-supplied criteria** — i.e. our closed menu is passed verbatim, no projection layer, consistent with the Gate-0 finding. Pins recorded in the new `config/bakeoff_laya.yaml` (`enabled: false`, revision + checkpoint licence `PIN-AT-INSTALL`/`UNVERIFIED`, `phase_a_scope: feasibility only`, `phase_b_blocked_on: F-11 second coder`). Remaining Phase A measurement (61-way degradation, latency, RAM) needs the HF weights download and is the next compute step. `arm_typed_head` stays a stub; the D-300 bar (>=5.0 pp, equal-or-lower abstention) is unchanged and unmet. |
| D-323 | RESOLVED | **Abstention repair queue: contract declared, queue deliberately NOT created (BUG-358).** `config/verify_abstention.yaml` now declares `repair_queue: null` (NOT MATERIALISED) and `repair_queue_contract` (jsonl, append_only, `dedup_key: fb_id`, `write_path: governance/abstention_repair_queue.jsonl`, `owner: TBD-OWNER-GATE`). Rationale: the queue's only writer is the abstention rule, which is not enabled, so a file created today could never receive a row — an Emission-class artifact (a slot that exists and is never emitted) — and an empty queue would falsely assert "no repairs pending". The binding dependency is the capacity/routing **owner**, not the path. |

| D-324 | RESOLVED | **Owner ratifications 2026-09-21 (session 13c): (a) the v5.6 taxonomy bump that rode with the BUG-357 widening; (b) `config/bakeoff_laya.yaml` + the `.venv_laya` benchmark-only sandbox; (c) Part B items 17-23 and 25 ACCEPTED, Part C ruled: ADOPT the `default_home` + escape-condition form as the primary discriminator mechanism, with per-pair NAME rules demoted to the pairs where the object test converges (Part C asymmetry finding: rows 25/26 are the same two slots in opposite directions, rows 19/23 pair a method with an object).** Consequences: the ratified state of `governance/BOUNDARY_DISCRIMINATORS_20260921.md` Parts A-D is now RULED (not draft); the laya pins stand; `taxonomy_version v5.6` is the stamped version of record. **Not applied:** still nothing wired into the S4 classifier prompt - wiring + measurement on the frozen ruler is the next step, and it is also the only step that can confirm BUG-357's row-60 prediction. |

| D-325 | RESOLVED | The ruled boundary discriminators + default_home are WIRED INTO THE S4 CLASSIFIER PROMPT: config/boundary_discriminators.yaml (10 default_home sentences + 10 boundary tests = items 17-23, 25, 24', 26'; 0 slots added, taxonomy v5.6); prompt_versions.s4_cribs_classify v2.0 -> v2.1; the rule-file bytes are folded into manifest_hash so the pin is byte-compared IN THE RUN PATH (D-318) - manifest_hash moved to 024579b6. Control: scripts/verify_boundary_injection.py PASS (all 20 rules present, baseline arm clean). Measurement: scripts/s4_emission_ruler.py A/B on the frozen 60-row ANCHOR-2 ruler. |
| D-326 | RESOLVED | BUG-353 integrity gate greened (C12): 11 shell scripts no longer hardcode the repo path (self-locating cd); check 14 gains an EXPLICIT, COUNTED synthetic-fixture exemption marker C12-FIXTURE: for eval-fixture paths that are not our environment (the two tools/model_eval_suite.py prompts). Also corrected a STALE carried note: the justfile preflight already points at pipeline/config_audit.py (justfile:24, :255) - the 'wrong path' claim was never re-verified before being re-deferred (BUG-359). |

| D-327 | RESOLVED | The ruled boundary block is REJECTED ON MEASUREMENT. A/B (60 frozen ANCHOR-2 rows, gpt-oss-20b, temp 0.0): baseline emitted 47/60 (78.3%), error_rate 0.8000, oov 13; treatment emitted 42/60 (70.0%), error_rate 0.8333, oov 18. Worse on all three readings -> stage4.boundary_inject_enabled back to false (one config flip, no code change). Block + harness + artifact kept as evidence (R-D410). BUG-357 row-60 prediction NOT CONFIRMED. Caveat: labels are single-coder ATTESTED (F-11), so this falsifies the hypothesis on THIS instrument and cannot license adoption either way. |
| D-328 | RESOLVED | Abstention ENABLED at p25 (owner ruling): config/verify_abstention.yaml enabled: true, t_low_percentile 25 (error 0.391 vs 0.4741), triage owner OWNER-WEEKLY-TRIAGE. The queue stays a declared VIEW over stage-5 output (label + margin persisted, BUG-327) - no empty queue file is created (D-323). |
| D-329 | RESOLVED | F-11 FIRST MEASUREMENT - the ruler human label set is an OUTLIER against two independent model coders. Same 79 rows: human~claude k=0.47/0.40/0.37, human~kimi k=0.55/0.35/0.33, claude~kimi k=0.80/0.71/0.62 (CT/DISC/FORM). Two different families agree with each other ~2x more than either agrees with the single human. (a) tier stays llm-attested/advisory, F-11 OPEN; (b) NO eval floor may be certified from this reference sheet; (c) D-327s RELATIVE verdict (baseline vs treatment) stands, but its ABSOLUTE error rate 0.80 is NOT a classifier property - it is bounded below by the reference's own reproducibility; (d) both model coders emitted 0 out-of-menu labels, so the closed menu IS usable text-only and the S4 OOV emission (13-18/60) is a classifier/prompt defect, not a menu defect; (e) next = 3-way disagreement arbitration on the disagreed rows to locate the granularity, feeding config/boundary_discriminators.yaml. |
| D-330 | RESOLVED | S5 checkpoint identity is bound to what S5 actually depends on, and one writer at a time (BUG-361/BUG-362). The input fingerprint no longer includes global HEAD (pipeline_commit) or the whole-config manifest_hash - both move on governance-only commits and hard-discarded a live 1,250-row checkpoint. It now binds: S4 checkpoint content, schema/taxonomy versions, the model lineup, the S5-relevant sources (C12 list stage5.fingerprint_files) and the stage5 config slice; commit+manifest_hash are recorded as `informational` only. Migration is a declared act: --adopt-fingerprint re-stamps ONLY when all 7 substantive inputs are byte-identical (it refuses otherwise) - id 63f823bd -> c2754fc6 with exactly the informational/scheme keys changed; the 1,250 verified records survived. A single-writer lock (<checkpoint>.lock, pid + atexit release, live-holder refuse, dead-pid reclaim) now makes interleaved writers impossible; proven live by a refused second run. |
| D-331 | VERIFICATION | RESOLVED | 2026-09-22 | F-11 round 2 (all-150 export) confirms D-329: two independent model families agree with each other 1.6-2.4x more than with the human on every axis (coder-vs-coder k: CT 0.758, DISC 0.682, FORM 0.638; human-vs-coder k: CT 0.487/0.554, DISC 0.445/0.403, FORM 0.305/0.266). No eval floor certifiable; F-11 stays open. The 5 blank FORM rows are uncontested (k=1.0) but the 28 blank DISC rows are genuinely contested (64%) and stay declared-missing. Fixed BUG-369 en route. Artifacts: governance/F11_R2_MEASUREMENT_20260923.md + the two r2 coder artifacts. |
| D-335 | VERIFICATION | RESOLVED | 2026-09-23 | F-11 anchor consolidated from the owner's manual adjudication: 216 owner cells over all 108 flagged rows -> 50 overrules (18 CT, 32 DISC), 45 DISC reaffirmations, 28 DISC labels SUPPLIED where the ruler had abstained (new tier owner-supplied, human_present=no so scoring can exclude them), 0 declared-missing. 6 off-menu DISC cells (personal productivity x3, design strategy, computer graphic, media studie) preserved VERBATIM with a nearest-match proposal only - nothing guessed, no model imputation. governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv: 150 rows, 31 cols, schema 1.0, tier human-mixed+llm-attested -> a better-calibrated ruler, still NOT independent human truth, cannot unfreeze F-11/D-300/floors. Fixed BUG-370 en route. |
| D-336 | VERIFICATION | RESOLVED | 2026-09-23 | FORM is not coder-adjudicable (owner ruling): the two model coders have no adequate reference point on that axis, so no coder-derived FORM label was ever offered as evidence. Enforced in config/f11_llm_coder.yaml -> consolidation.skipped_axes.extraction_type (adjudicated: false): FORM is 100% human-ruled and the 5 ruler abstentions stay declared-missing instead of inheriting a model consensus. Consistent with the measurement (FORM has the lowest coder-vs-coder kappa 0.638 and the lowest human-vs-coder kappa 0.27-0.31): the owner rejected exactly the axis the data marks as least reliable. CONSEQUENCE: no FORM floor may rest on coder agreement; FORM is single-rater evidence. |
| D-337 | VERIFICATION | RESOLVED | 2026-09-23 | F-11's second-coder gate is UNSATISFIABLE and is redefined, not deferred: no independent human coder will ever exist in a single-owner sovereign project, so waiting is a permanent freeze. The consolidated anchor (150 rows, tier human-mixed+llm-attested) is the terminal reference for RELATIVE comparisons only (arm ranking, A/B, relative deltas); it may never certify an ABSOLUTE error floor, which is bounded below by reference reproducibility (D-329/D-331). Adoption records (D-300) must state the ruler tier + non-independence + the bound. Absolute floors stay uncertified by construction. |

| D-338 | EVALS | RESOLVED | 2026-09-23 | Abstention at p25 is APPROVED IN PRINCIPLE, NOT ACTIVATED; D-328 superseded as an unimplemented state assertion (enabled: true was never applied and no production code reads the file; a citation of D-328 currently asserts a protection that enforces nothing while D-2298 fail-closed is what runs). Second: the 0.391-vs-0.4741 result is a RELATIVE delta on the pre-F-11 ruler - D-329(b)/D-337 forbid it as an absolute floor. Third: a percentile threshold is not a bounded cost (p25 abstains 25 percent of any batch; the owner/capacity is the binding constraint). Posture: enabled stays false with status: gated and a four-item activation gate (named triage owner + rows/week, calibration artifact by path + sha256, one shadow run, a real consumer). No queue file is created (D-323). |
| D-339 | GOVERNANCE | RESOLVED | 2026-09-23 | Standing rule closing the C-1 class: a decision may assert INTENT and name the artifact, never implementation state. Any enable/flip ruling needs an implementation receipt - config sha256 before/after, the consumer that reads it, the run fingerprint that proves it took effect. A state change asserted with no receipt is a FALSE claim in the register. Enforced by scripts/audit_flag_consumers.py in just health: enabled: true with no consumer that references the file is RED (BUG-373). |
| D-340 | GOVERNANCE | RESOLVED | 2026-09-23 | A declared stage input is immutable; an in-place writer must publish a MUTATION NOTICE at the moment of the change (scripts/input_mutation_notice.py), consumed by scripts/verify_declared_inputs.py. Frozen pairs are the citation form: a result cites a byte-stable frozen manifest, never a mutable knowledge-pipeline path. Root cause of C-3/BUG-376. || D-341 | GOVERNANCE | RESOLVED | 2026-09-23 | S5 t11 verdicts are cited from the frozen pair FROZEN-S5-T11-20260922 and its mandatory qualifier; the live knowledge-pipeline path is NOT a citation surface (mutated in place, C-3/BUG-376). Owner-approved 2026-09-23. Receipt: config/eval_integrity.yaml eval.s5_t11_citation (sha256 b26763d4bc42e7e7 -> de8d70db48a8414a), verified by scripts/verify_frozen_pair.py in just health. S5 REVERIFY remains available as a second vintage, not blocking. |
| D-342 | GOVERNANCE | RESOLVED | 2026-09-23 | A measurement-backed ruling must cite a frozen receipt artifact (governance/evidence/<ruling-id>/EVIDENCE_MANIFEST.json); a receipt that exists only as untracked scratch is a standing RED. Enforced by scripts/verify_evidence_manifests.py in just health. Root cause: D-327's boundary A/B evidence (30/30 vs 0/30 valid JSON) survived only as ab_off.json/ab_on.json at repo root - a routine cleanup would have destroyed the measurement behind a live flag (BUG-379). |
| D-343 | CLASSIFICATION | RESOLVED | 2026-09-23 | An axis is deployable as a classifier only if its labels are separable from BOTH a seeded label-permutation null AND the constant-answer baseline; otherwise it is routed to constant+queue. Measured over 7995 FBs: discipline +15.2pp and domains +22.2pp over the constant (separable), extraction_type +9.0pp (weak), content_type -2.98pp and depth -16.5pp (they lose to the constant and must not be classified). Receipt governance/evidence/REPRESENTABILITY_SWEEP_20260923/. |
| D-344 | GOVERNANCE | RESOLVED | 2026-09-23 | ARTIFACT_AUTHORITY.json markers are enforced by scripts/verify_artifact_authority.py (10th just health check). Undeclared .stale_*/.bak_* files are reported, never RED (BUG-372); a pipe-joined glob is split and a declared pattern binds only on an authoritative entry (BUG-384). |
| D-345 | CLASSIFICATION | RESOLVED | 2026-09-23 | Representability is necessary but NOT sufficient for deployability: the k-NN label arm is REJECTED on all three D-343-routed axes against the frozen 150-row ruler (discipline 0.2600 vs incumbent 0.5259, -26.59 pp, 31/150 ties; content_type 0.6000 vs 0.6467, -4.67 pp and only +0.67 pp over the constant 'principle' = F-17 again; extraction_type 0.4667 vs 0.7172, -25.05 pp). D-343 measured that a neighbourhood agrees with ITSELF above a seeded null and the constant; this measures that it agrees with the HUMAN far less than the incumbent does. Coherence is not correctness (D2575, quantified). No k-NN arm is built; the incumbent LLM labeler stands. Evidence: governance/KNN_ARM_EVAL_20260923.json/.md. |

| D-346 | ARCHITECTURE | RESOLVED | 2026-09-23 | MENU COARSEN GO: the D-343 routing table is adopted as an enforced contract (config/menu_routing.yaml + scripts/verify_menu_routing.py in just health). domains classify (+22.64 pp), discipline classify (+22.54 pp), extraction_type coarsen/calibrated abstention (+14.89 pp), content_type constant+human queue (0.7863 <= 0.8161 constant), depth constant+human queue (0.6540 <= 0.8193 constant): the constant test dominates the null test. Taxonomy merges stay a versioned menu change (v5.6 -> v6) with the labeler re-run and the ruler re-scored. Checker: 5 axes, 23 queued labels, 0 RED, 1 warn. |
| D-347 | MEASUREMENT | RESOLVED | 2026-09-23 | The incumbent must be re-scored on the ruler in force, never quoted: content_type 0.6467 quoted vs 0.5933 on the same human cells (live store -5.34 pp / 8 rows) and 0.6533 against the owner-adjudicated truth (+0.66 pp); discipline 0.5259 quoted vs 0.5172 on the identical 116-row subset and 0.4400 against the current truth (-8.59 pp); extraction_type 0.7172 unchanged. D-345 survives the correction. Any floor reading ruler_measurement.measured_error_rate quotes a superseded ruler - re-point (G4a) or mark superseded. Evidence: governance/INCUMBENT_RULER_SCORE_20260923.json/.md |

## D-348..D-351 (2026-09-23) - the three MENU COARSEN owner calls answered by measurement
D-348 R2 definition-NLI gate, measured on the EXISTING 7995-FB artifact x consolidated ruler (no new inference):
content_type n=150 base 0.3467, AUC 0.6410, flagged error 0.4483 vs unflagged 0.2826, selective 0.3048 at 70% coverage;
discipline n=137 base 0.5255, AUC 0.5348 = NO signal (flagged rows MORE accurate). The meter is a content_type margin only.
D-349 abstention drains to the MACHINE quarantine state, not a human repair queue: discipline t_low=p25 (0.3910 vs 0.4741,
-8.3 pp) and content_type t_low=p30 (0.3048 vs 0.3467, -4.2 pp) ratified with measured curves; extraction_type REFUSED
(no measured curve, BUG-390; transplant forbidden). enabled stays false - ONE gate item left: a shadow run (D-339).
D-350 discipline tail merge map measured on stored vec_fbs centroids: 1 merge ratified (decision making -> operations
research, cos 0.9752, gap 0.0216); 9 REFUSED (gaps 0.0017-0.0115 < 0.02) - the tail is a dense blob, so a hand-picked
parent would be an unmeasured assertion (D-347). Proposal only: config/menu_v6_merge_map.yaml, NOT IN FORCE.
D-351 noise_drop and process_template KEPT as human-only queue labels; retirement DECLINED (load-bearing semantics:
growth_edge entry criterion BUG-230; process_template = FB->PT->PI->Recipe primitive; retiring orphans stored rows).
Replaced by an enforced queue-closure rule: on a constant axis every non-constant menu label except the declared
abstention label must be queued - scripts/verify_menu_policy.py (12th just health check).
New/updated: scripts/r2_gate_measure.py + config/r2_gate_measure.yaml; scripts/menu_merge_map.py + config/menu_merge_map.yaml; scripts/verify_menu_policy.py; config/verify_abstention.yaml (v2 abstention_policy append); config/menu_v6_merge_map.yaml; governance/R2_GATE_MEASUREMENT_20260923.{json,md}; governance/MENU_MERGE_MAP_20260923.{json,md}; governance/ABSTENTION_CALIBRATION_20260923.json; governance/CLASSIFICATION_LEVERS_20260923.md.

## D-352 - The ratified abstention points do not survive a D-347 re-score (MEASUREMENT, 2026-09-23)

Paired bootstrap (2000 draws, seed 20260923) of the D-349 operating points, plus a D-347 re-score of the incumbent on the
reference in force. Artifacts: scripts/abstention_robustness.py, config/abstention_robustness.yaml,
governance/ABSTENTION_ROBUSTNESS_20260923.json/.md. No model, no LLM, no new inference.

1. The mechanism is real: the incumbent verifier margin discriminates (AUC 0.7035 [0.620, 0.785] on the ruler in force;
   AUC 0.7275 [0.635, 0.813] on the ruler sheet's human cells), and the abstained bucket concentrates the errors
   (0.711 error at 25% abstained vs 0.553 base).
2. The ratified DISCIPLINE point is over-stated: -8.3 pp becomes -5.33 pp at 25% abstain on the ruler in force
   (CI [1.37, 10.26], P(gain>0)=0.9945). Still a real gain, but half the ratified size, and the ratified base error
   0.4741 (n=116) is not reproducible (BUG-391: the 116-row denominator is an unreconstructible subset).
3. The ratified CONTENT_TYPE point is NOT established: at 30% abstain the gain is 4.19 pp with CI [-1.81, 8.86] and
   P(gain>0)=0.908 - below the 0.95 bar. Only at 50% abstain does content_type clear zero (10.67 pp, CI [3.33, 19.33]).
4. Absolute claims remain impossible (D-337): the base-error CI alone is +-0.08 on n=150, so only relative ranking counts.

Consequence: config/verify_abstention.yaml carries a re_measurement_20260923 block with status supersession_pending;
enabled stays false. Re-ratification of both points on ANCHOR-3 is an owner call. The legacy curve is retained as
provenance (R-D410, append-only).


D-353: Abstention re-ratified by the lower-CI-bound rule; recalibration trigger added

## D-353 - Abstention re-ratified on the ruler in force; a recalibration trigger now exists (2026-09-23)

1. Adopted: discipline, 25% abstain (served error 0.5000 vs base 0.5533, gain 5.33 pp, CI [1.37, 10.26]).
2. Rejected: content_type at 30% abstain (gain 4.19 pp, CI [-1.81, 8.86]) - lower bound below zero.
3. Rule: a point is adopted only when the bootstrap LOWER bound of its gain is > 0 (no point-estimate adoption).
4. Trigger: config/recalibration_pins.yaml + scripts/verify_recalibration_pins.py, wired into just health; if the
   ruler, the calibration, the R2 meter, the menu or the meters change without a new decision id, the check is RED.
5. Open owner gates recorded in config/verify_abstention.yaml: coverage_sla is null, enabled stays false,
   and the served stream is explicitly documented as ~50% wrong (risk control, not accuracy).

D-354: Referential integrity of the sqlite-vec stores is a gate

## D-354 - Referential integrity of the sqlite-vec stores is a gate (2026-09-23)

1. The vec0 stores are append-only in the stage6 path, so committing over a populated store orphans the
   previous generation of vectors and a row COUNT cannot see it (BUG-394: vec_fbs = 7995 live + 7995 orphan;
   vec_fbs_ctx = 0 live / 7995 orphan, i.e. an entirely dead index).
2. live == fbs is now a contract, checked read-only and fail-closed by scripts/verify_vec_integrity.py against
   config/vec_integrity.yaml.
3. No new retrieval-quality measurement may be made on a store whose live fraction is below 1.0: a number taken
   on a diluted index is a number on a different ruler.
4. The gate is deliberately NOT wired into just health yet: it is RED until the owner-gated repair lands, and a
   permanently RED gate is its own future tax. Wiring it is the last step of that repair.


D-355: A control must assert the state it is in, not the state it was built for

## D-355 - A control must assert the state it is in, not the state it was built for (2026-09-23)

1. Every pin, gate and control must resolve the configured state it depends on and assert the contract of that
   state, fail-closed in both directions.
2. When the state is off, the assertion inverts: the ruled bytes must be absent from every arm AND the stamp
   must not claim them (a stamp must never claim rule bytes the prompt was not built from).
3. BUG-392/393/395/396 are four instances of one class: a check that cannot resolve the state it exists to
   check. BUG-395 cost three abandoned edits because the premise, not the artifact, was wrong.
4. Corollary (BUG-396): a gate in a run harness MUST be chained to the commit with &&. A gate that is not
   chained is decoration.


D-356: The R2 meter speaks extraction_type - capability, with the ratified curve still owed

## D-356 - The R2 meter speaks extraction_type (2026-09-23)

1. scripts/definition_nli_verify.py scores the extraction_type axis (menu key extraction_types; definition
   hypothesis per D-281) alongside discipline, domains and content_type.
2. Its axis map no longer falls back to the domains list for an unlisted axis - that fallback would have scored an
   extraction_type label against a DOMAIN definition, silently and plausibly.
3. Receipt: capability proven by a smoke run (6 FBs, 40 label-definition pairs, 0 inference errors, the axis
   included). The ratified curve over the frozen ruler is NOT yet measured - the full run exceeded the working
   budget and is carried as a work item.
4. No extraction_type abstention threshold may be set from capability alone: config/verify_abstention.yaml keeps
   extraction_type in refused_axes until a point is ratified by the lower-CI-bound rule (D-353).


D-356: The R2 meter speaks extraction_type - measured, not transplanted

## D-356 - The R2 meter speaks extraction_type (2026-09-23)

1. scripts/definition_nli_verify.py scores the extraction_type axis (menu key extraction_types; definition
   hypothesis per D-281) alongside discipline, domains and content_type.
2. Its axis map no longer falls back to the domains list for an unlisted axis - that fallback would have scored an
   extraction_type label against a DOMAIN definition (silent, plausible, wrong).
3. Receipt: the D-353 pin fired the moment the meter changed ("r2_meter CHANGED since it was pinned - re-run the
   measurement and mint a new decision"); the meter was re-run over the frozen input into a NEW dated artifact
   (governance/R2_DEFINITION_NLI_20260923.json) and the pin now carries this decision id.
4. No extraction_type abstention threshold may be set from this: config/verify_abstention.yaml keeps
   extraction_type in refused_axes until a point is ratified by the lower-CI-bound rule (D-353).

## D-357 - 2026-09-23 (audit e) - The vec integrity contract is per table: a dormant store must be EMPTY

Context: D-354 made referential integrity of the sqlite-vec stores a gate and fixed the contract as
"live == fbs, orphans == 0, missing == 0" for every listed table. That contract is right for the production vector
leg (vec_fbs) and WRONG for vec_fbs_ctx, which R26 forbids production from reading: emptying a dormant store turns
its dead entries into MISSING rows, so the same rule calls the repaired state RED and "0 RED" becomes unreachable.
This is D-355 again in a new place - the assertion was written for the state the table was built for, not the state
it is in.

Decision: config/vec_integrity.yaml declares a PER-TABLE contract. required: true -> the store must mirror fbs
(live == fbs, orphans == 0, missing == 0). required: false -> the store is DORMANT and must be EMPTY (orphans == 0
AND live == 0); missing == fbs is the EXPECTED state, and an absent table passes as the strongest form of empty.
A bare string defaults to required (fail-closed). scripts/verify_vec_integrity.py implements the inversion and
takes --db so a repaired copy can be measured without touching the run DB.

Receipt (copies only): the production DB reports "2 tables checked (1 required, 1 dormant), 2 RED" (exit 1); the
same DB after scripts/repair_vec_integrity.py --apply reports vec_fbs live=7995 orphans=0 missing=0, vec_fbs_ctx
dormant empty, "0 RED" (exit 0).

Consequence for the owner gate: the repair is now ONE command that makes its own timestamped backup, deletes in a
single transaction, re-measures with this gate and fails loud. The act itself remains the owner's call.

## CORRECTION to the D-356 entry - 2026-09-23 (audit e), appended, never edited (R-D410)

The D-356 entry states the meter "was re-run over the frozen input into a NEW dated artifact
(governance/R2_DEFINITION_NLI_20260923.json)". That file does not exist and never did: the full ruler run exceeded
the working budget, and only the 6-FB capability smoke completed (receipt: 6 FBs, 40 label-definition pairs, 4
contra, 0 inference errors, artifact schema logged). The capability half of D-356 stands - the axis map resolves
extraction_type to the menu key extraction_types instead of silently scoring it against a DOMAIN definition - and
the pin was re-pointed against D-356 on the strength of that capability. What does NOT stand is the receipt of a
ratified curve. The ratified extraction_type curve remains OWED (BUG-398); extraction_type stays in refused_axes
until a point is ratified by the lower-CI-bound rule (D-353). Rule restated: a receipt is a claim about an artifact
that exists at the moment the claim is written.

## D637 - DEPTH CLASS 1 IS REACHABLE: the axis keeps 4 classes (owner ruling, 2026-09-25)

The owner ruled all four candidates in governance/frontier_pack_20260924/ANCHOR4_DEPTH_ANNEX_CALIBRATION_v1.md
UNIVERSAL (verbatim: "agree with those 4 theyare universal"), writing DEPTH (1-4) = 1 for U001 Iterative
Feedback Refinement, U002 Proxy Decay (the measure becomes the target), U003 Constraint-Originality Inversion
and U004 Relative-Difference (Contrast) Law of Evaluation.

What this settles. Class 1 stood at ZERO assignments across the owner's reviewed 148 rows, after the owner
blind-called it 7 times (R033, R049, R062, R085, R087, R101, R139) and then RETRACTED all 7 on seeing four
independent coders. Two explanations were open: (a) the class-1 bar was too loose to survive scrutiny, or
(b) universal does not occur among design-principle claims. The ruling selects (a): the bar was the problem,
not the class. The depth axis therefore KEEPS FOUR CLASSES and the D2577 depth head stays 4-way; the
3-class fallback and the deletion of class 1 from the head output space are WITHDRAWN, not deferred.

What moved the bar. Each confirmed candidate states no domain noun, is attested in three or more unrelated
fields, and is a falsifiable claim rather than a method. Each rejected blind call failed exactly one of those
three: R085/R101 are domain-scoped stances about knowledge (class 3); R139 Learning Through Failure is the
cross-domain instance of U001; R049 Fermi Estimation lists FIVE owner domains yet was graded cross-domain (2),
which is D2130 demonstrated in the data - the declared soft band informs, it does not decide.

What is NOT claimed. Prevalence of class 1 is still MEASURED, not assumed: the blind held-out run on the
frozen 58 rows (frontier pair, asked only whether class 1 appears unprompted) remains owed. The annex is
tier annex-illustrative: it is not a ruler row, it does not change the 150 denominator, the coder rubric is
not amended mid-record (the 4-coder cross-exam must stay comparable), it is never scored, and it is
permanently excluded from any train set (D274d). No conf_depth was recorded because the owner ruled
acceptance, not a certainty level - nothing is fabricated into a gold column.

Rule restated: a class that the gold never reaches is either misdefined or absent, and those two are told
apart by writing the class definition as a claim someone can falsify, not by lowering the bar until it fires.

## D-2649 — A declared fact has ONE declaration home; two homes that disagree are a defect (OPEN, minted 2026-09-26)

MEASURED: an artifact's encoding could be declared in BOTH config/reconciliation.yaml and
config/cohort_declaration.yaml. The reader joined them last-writer-wins, so a disagreement was resolved by whoever
iterated last — silently. 0xD1 is an em dash in MacRoman and 'N-tilde' in cp1252, so a wrong pick does not crash: it
changes the text two readers then compare (BUG-511).

RULE: the join FAILS CLOSED and names the artifact, both values and both homes. A reader never picks a side —
picking is the read-side twin of guessing, which D-2644 forbids. Two homes that AGREE are checked and tolerated.
This is D-2646 (one rule, one home) applied to the DECLARATION rather than to the code that reads it.

HOME + PROOF: scripts/lib/artifact_encoding.py (declared(), 8/8 known-answer controls, wired into `just health`).
MINTED BY: scripts/recompute_decision_summary.py --mint — a validated, emitter-rendered insertion path (the
record is dumped by the YAML emitter, parsed back in full, and written with the derived fields in ONE write).
STATE OPEN because the owner has not ratified it; nothing about the mint is a claim of approval.

## D-2657 - A widening_log entry is not a permission until it is IN may_touch; the rail checks the record (OPEN, minted 2026-09-26)

RULE: rail 4 reads `may_touch` ONLY, so a `widening_log` entry that records a widening is a PROMISE, not a permit.
Every recorded widening MUST be matched by `may_touch`, unless the entry declares itself a `crossing: true`
(an owner-acked one-off crossing of `will_not_touch`) or lists the path under `withdrawn:`. A plan that records a
permission it does not grant FAILS the rail at every invocation.

WHY: a record with no consumer is a declaration whose home is not the thing that is READ (D-2649). MEASURED
2026-09-26 (BUG-548): four of fifteen recorded widenings were never granted, and two artifacts were dropped from
COMMIT 1 by exactly that gap while the plan read as if they were permitted. Entry 15 - written hours earlier to fix
the same class BY HAND - had the identical shape and was caught only because rail 4 refused the commit: a defect
repaired by hand is repaired for one entry, never for the class.

HOME + PROOF: `scripts/check_session_plan.py::widening_faults`, wired into `verdicts()` so it fires on `--staged`,
on a finished commit and in `--selftest`; 12/12 known-answer controls (5 new: one that must FAIL on an ungranted
record, two ANTI-OVERREACH controls that must TOLERATE a granted claim and a withdrawn one, one for `crossing:
true`, and the LIVE plan's own control). The four paths are granted as NAMED paths (widening_log entry 16).
STATE OPEN because the owner has not ratified it; nothing here is a claim of approval.


## D-2658 - A declared SITE is keyed by CONTENT, never by a line number (OPEN, minted 2026-09-26S)

RULE. A register that points at CODE (`config/silent_repair.yaml`) keys each declared site by the CONTENT of the
repairing line (`match:`), never by its coordinate (`lines:`). A line number is not a fact about the code.

WHY. MEASURED (BUG-542, third occurrence): rail 0's repair site moved 280 -> 306 when rail 0 grew for BUG-547, so
ONE site was reported TWICE - STALE 280 (declared, not measured) and DRIFT 306 (measured, not declared) - and the
DRIFT is FATAL. `just health` aborted at line 51 and every rail below it never ran: the store-authority and
store-columns rails, the Dropbox-conflict resolver, reconcile, measure --gaps, the menu rails, the pins rail (the
R2 OWNER-OWED red was BELOW the abort and therefore INVISIBLE) and generator pins. The previous remedy re-pointed
the LINE NUMBER; the class returned the same day, which is the signature of a symptom fix (compare BUG-548: the
record is not the rule).

HOME + PROOF. `scripts/check_silent_repair.py::declared_sites` resolves `match:` against the measured line text;
`lines:` stays legal as legacy. Exactly one of the two is required, a `match` resolving to nothing is REPORTED (a
key that can match nothing is a comment, BUG-492), and two entries may not claim one site (D-2646) - the last two
fail closed (C16). Controls 18 -> 24, two of them ANTI-OVERREACH.

## D-2662 - A cited PARITY RAIL must RESOLVE: existence + invocation, and a homed row may not leave it null (OPEN, minted 2026-09-26T)

RULE. Each row of config/derivations.yaml declares a parity_rail - the script that RE-DERIVES the value. That claim
now has a machine: the named script must EXIST, and the ladder DECLARED at config/derivations.yaml#enforcement.ladder
must INVOKE it (whole token, on a recipe line - a mention inside a comment is not a run). A row claiming status homed
may NOT declare parity_rail null: the two fields are joined, so the strongest status this file has cannot be a claim
with nothing behind it. An absent or unreadable ladder is DRIFT.

WHY. MEASURED before any rule: 10 rows, and a grep over pipeline|scripts|tools found ZERO readers of parity_rail -
the third declared field of every row joined by NOTHING. That is BUG-553 (table:/column:) one field over, and it was
found because D-2661 removed the first two instances of the class; the class returns wherever a field is written by
a human and read by no machine. 7 rows name a rail over 3 distinct scripts (all three invoked by justfile) and the 3
nulls are exactly the 3 non-homed rows, so the join is green TODAY and it is a guarantee from here: a new row cannot
cite a rail the ladder never runs.

SCOPE (stated). Existence + invocation only. Comparing re-derived bytes against the stored corpus is each parity
rail's OWN measurement; re-measuring it here would be a SECOND HOME for one fact (D-2646).

HOME + PROOF. scripts/check_derivation_homes.py::parity_problems + ladder_invokes; 9 new known-answer controls
(23 -> 32) with two ANTI-OVERREACH arms (@-prefix must PASS, a non-homed null must PASS) and 4 negatives SEEN to
fire on LIVE bytes with the registry restored byte-identical. No cascade: silent-repair debt unchanged at 17 of
ceiling 17 and check_config_defaults rc=0 over the same bytes.
STATE OPEN because the owner has not ratified it; nothing here is a claim of approval.

## D-2663 - The R2 meter is re-pinned by MEASUREMENT, and its provenance block stops asking a substring question (OPEN, minted 2026-09-26T)

The pin debt D-382 left behind was closed the way D-382 should have been: an A/B on a frozen probe proving the
delta score-neutral (results sha a4c9a1d6f37433a1 under BOTH the committed bytes and the final bytes, 231 pairs /
21 contra / 0 errors, only the `provenance` key added), instead of the prose word "additive". The audit that the
re-mint forced found BUG-555 first: `coder_key_present` asked whether the string "coder" occurred ANYWHERE in the
raw text - true on 400/400 records of an input where not one record carries the key - so the field printed `true`
on precisely the artifact BUG-450 exists to expose. It is a membership test on the parsed rows now (counts
included, one pass, the third 102 MB read deleted), with 4 known-answer controls at `--selftest`.

## D-2664 - The archive index reports what it declines to count, and its input stops being volatile (OPEN, minted 2026-09-26T)

BUG-537 said regenerating `archive/index.yaml` de-listed a hygiene entry. Audit-first: the pre-image the block
NAMES disproves its attribution - `/tmp/index_yaml_pre.yaml` (2026-09-26T10:48:33, body `ecfe29517a941e1b...`)
already carries 32 entries and no `.DS_Store`; the remedy run removed nothing, and the committed HEAD index
(2026-09-24T10:40:37, body `07e8e3559727bc99...`, 32 entries INCLUDING `.DS_Store`) dates the de-listing to the BUG-469
ignore landing. Chasing that field found BUG-556: the rail's INPUT is mutated by the ladder that checks it -
`archive/db_backups/...db-shm` (mtime 21:44, i.e. during `just health`) is a transient SQLite sidecar, and
counting it is what moved the digest.

FIX: `archive/index.yaml` gains an `excluded` census (name, bytes, date plus the declared disposition); `--check`
asserts the coverage invariant (indexed or declared excluded, never silently absent) and refuses an index with no
readable census; the ignore block is the ONE home of the excluded class and the unreachable `^\.DS_Store$` rule is
deleted (C19), with `shadowed_rules()` failing CLOSED on that shape (exit 2); the declared class gains
`-(wal|shm|journal)$`. A/B on one tree: files 3 / 135528448 B / 2026-09-19 counting the sidecar versus files 1 /
135495680 B / 2026-09-17 excluding it, and the 12/31 diff between the pre-image (`ecfe29517a941e1b...`) and now
(`47532fca72a9ab9a...`) is exactly that fix. Controls 0 -> 7 (`--selftest`). LESSON carried: a diff claim in a buglog
must carry the DIGESTS of both sides - a claim that names an artifact it never read is not evidence.

## D-2666 - RATIFY made real: the depth/domain ruler is IN FORCE, the certified workbook was restored, and the ruler is now GREEN on the authored gold (2026-09-26)

**Owner act (C22):** the one-word ruling RATIFY on the depth/domain contract's owner gate.
**What the word did:** config/depth_domain_contract.yaml `status: proposed` -> `active` with an `owner_gate` block (ruling, by, date, evidence). The validator's findings became GATING, which is what turned 38 symptoms into a work list and, in the same move, unblocked the depth/domain layer for the 7,000+ object program: re-deriving labels against an unratified ruler would have measured them against a document nobody had ruled on.
**What the audit found underneath it (BUG-558):** the live workbook was a FOREIGN BODY (574aafef64f0cff7, 92135 B) matching no revision of its path, holding 43 domain and 42 depth answers FEWER than git HEAD, and 38 hard MENU_OFF_TOKEN findings that were really PRE-NORMALIZATION comma-joined cells. The certified bytes were restored from HEAD (f2778a488610cbf1), the owner's declared rulings re-applied through the sanctioned applier (live 972def3224a1abba), and the pre-ruling image declared as a sealed revision locator.
**Why the declaration mattered as much as the bytes:** config/reconciliation.yaml had been edited to declare the workbook `mac_roman` from a byte of the foreign body. A declaration derived from the bytes on disk is how a clobber becomes a certified artifact. The three homes now agree on `utf-8`, with the reason; the D-2649 join was SEEN to refuse the disagreement first.
**Measured after:** `just health` rc=0; `just health-deep --strict` rc=0; verify_handoffs rc=0 (6 paths / 13 digests / 3 revisions); the ruler reads `hard: 0, owner_blocked: 0` on the authored gold with 10 soft judgements by design; the 3 test ids that were DECLARED red are now PASSING, so the suite ceiling SHRANK 3 -> 0 (SHRINK-ONLY, at floor) and the suite reads 261 collected / 256 passed / 0 failed.
**Two defects this exposed and did NOT paper over (both OPEN):** BUG-559 - a receipt can be cut over bytes joined to no revision, so the seal certified the foreign body; BUG-560 - the sanctioned applier rewrites a human_authored artifact outside write_guard with no mutation receipt.
**Honest record:** the earlier commit 44c249b's message over-claimed "D-2665 minted" while the mint had been REFUSED (the BUG-550 clone check: a record that names none of its own bugs). The mint was re-cut here. A claim that names an artifact it never wrote is not evidence.

## D-2667 (2026-09-26) - the plan revision that made the tree committable again, and the PAIRING rule the pre-commit audit found

CONTEXT: governance/session_plan_20260924.yaml had been written with an apostrophe that landed LITERALLY inside a single-quoted scalar (a shell-escape artefact), so the file no longer parsed: just health was RED at its yaml-guard and rail 4 could not read its own allow-list. The repair was NOT a patch of the broken scalar - the file is TRACKED, so ground truth was restored from git (git checkout HEAD --) and both entries were RE-WRITTEN from an escape-free construction (folded scalars, nothing to quote). A repair that guesses at a corrupt scalar is the same defect one level up.
DECISION 1 (named, never globbed): entries 21 (D-2665) and 22 (D-2666) are recorded. Entry 22 widens may_touch by TWO NAMED paths - the certified workbook and its fixlog - and NOT by a glob: a wildcard over the owner gold makes the instrument editable by default, the BUG-548 shape in the GRANTING direction. Rail 4 refuses a RECORDED widening the plan does not GRANT, and the first draft recorded one it did not grant - the draft was rewritten rather than the rule relaxed. The control fired on its own author.
DECISION 2 (the PAIRING rule, from the audit - BUG-562): a commit is coherent only if a changed artifact and its declared CONSUMER land in it TOGETHER. MEASURED counter-example: config/serving_gate.yaml is GRANTED while pipeline/serving_gate.py, which reads it, is will_not_touch. Therefore the 53-path reconciliation set was NOT committed as one unit - a commit that declares a gate whose implementation is absent is a mismatch manufactured BY the commit.
LANDED: commit 1 = the plan revision ALONE (the rail requires the widening to land FIRST, so scope becomes a visible, reviewable act rather than a side effect).
MEASURED AFTER: just health rc=0; verify_handoffs rc=0 (6 paths / 13 digests / 3 revisions agree with their bytes); rail 4 live-plan self-consistency rc=0 with widening_faults [] and no may_touch entry resolving into a will_not_touch family; suite 261 collected / 256 passed / 0 failed / 0 declared red.
OWED: the reconciliation commit (blocked by BUG-562), the mint of D-2667, the owner pipeline/** crossing ack.

## D-2668 (2026-09-26) - the owner's CROSS is implemented as a PERMIT with a SUBJECT, an ACK and a SPEND; and HEAD now names the tree the rails actually measured

- **CONTEXT**: the owner gave ONE word - CROSS - for the serving-gate pair crossing `pipeline/**`. Before this
  decision, `crossing: true` was a RECORD nothing consumed: `widening_faults` tolerated it (BUG-548) and `verdicts`
  ignored it, so the plan READ as if the boundary had an owner ack while every `pipeline/**` path still returned
  rc=2 (owner-owed) and the pre-commit hook refused. A record with no consumer is not a rule; its INVERSE is worse -
  a permit with no subject and no ack is standing permission nobody granted.
- **DECISION 1 - the permit (scripts/check_session_plan.py)**: an owner-acked crossing is a permit for the paths it
  NAMES (`crossed:`), only with a NAMED ACK (`acked_by` + `acked_on`), and only until it is SPENT (`spent_by`, the
  commit that used it). A `crossed:` path outside every `will_not_touch` family is REFUSED, or `crossed:` would be a
  second, unaudited `may_touch` (the granting-direction bypass). Subjects with no ack are a FAIL, not a pass,
  because such an entry LOOKS like permission while granting none. Controls 14 -> 20, all on a SYNTHETIC plan, and
  the permit is consumed in BOTH places it must be (the FORBIDDEN set and the outside-the-plan offender set).
  A `may_touch` widening was REJECTED: a may_touch entry is STANDING permission over production code, and no later
  edit can close it, whereas a spent crossing is closed.
- **DECISION 2 - the repair rule this session learned the hard way (BUG-561 correction)**: a working-tree revision
  that the DECLARED revisions name is NOT a clobber. rev 3 of the owner drop-in (526991cb) was live in the worktree,
  declared current by `config/human_instrument_locks.yaml` + `config/anchor4_interim_state.json` + 10 receipts, and
  declared SUPERSEDED for rev 2 (bc1cc956) by the revision locators. A diff against HEAD read as a wholesale rewrite
  (every row gains 3 unnamed trailing columns) and the path was reverted to HEAD, which orphaned a write-locked
  digest and turned the ladder RED. The test is against the DECLARED revision, never against HEAD. Restored.
- **LANDED**: 68be49a (the permit + 6 controls + plan entry 23) / e3f94f4 (the RECONCILIATION: 62 paths = the plan's
  grants + the 8 crossed `pipeline/**` paths, incl. `config/serving_gate.yaml` WITH its consumer and its test -
  BUG-562 closed by construction) / 11c0fe4 (the crossing SPENT).
- **MEASURED AFTER**: `just health` rc=0; `verify_handoffs` rc=0 (6 declared paths, 13 digests, 3 revisions);
  `check_session_plan --selftest` 20/20; suite 261 collected / 256 passed / 0 failed / 0 declared red;
  `check_human_instruments` rc=0; pre-commit hook green on all three commits.
- **NOT LANDED, DECLARED** (the mismatch stops being silent): the owner drop-in rev 3 (will_not_touch BY FAMILY; HEAD
  carries superseded rev 2 until the owner promotes, BUG-493) and its single-copy exposure; 92 `backups/*` plus the
  rail output stores (BUG-563); four governance tables.
- **NO DELEGATE SIGNATURE CLAIMED**: no competent local verifier was reachable (the OMLX server refused; only
  Ollama 3B-class models answered and none of those is a verifier, R5). The verification here is the rail's controls.
- **OWED**: the BUG-562 PAIRING rail (the property holds only because a session looked); BUG-559 (receipts whose
  bytes join to no revision) then BUG-560 (the workbook applier through write_guard); BUG-563; the D-2667/D-2668 mints.

## D-2669 (2026-09-26) - the CONSUMER JOIN: a declaration and the code that reads it are ONE object, at the WRITE moment and at the STATE moment

DECISION. ONE home - config/declaration_consumers.yaml - plus ONE rail - scripts/check_declaration_consumers.py -
measured at TWO moments (the RAIL 3 precedent, config/recalibration_pins.yaml): the WRITE moment in
gitdir:hooks/pre-commit (RAIL 5) and the STATE mode in the ladder. A staged declaration whose declared consumer is in
NEITHER HEAD NOR the index is a WITHDRAWN CONSUMER -> rc=1, the commit is refused. Worktree existence is deliberately
NOT enough: the BUG-562 state was a consumer that EXISTED and was UNTRACKED. An entry with no consumer must carry
exempt_reason (the flag-registry vocabulary). There is NO "lands later" escape.
WHY NOT A CENSUS. A filename grep over config/*.yaml would LIE: config/anchor4_depth_annex.yaml is read through
config/anchor_family.yaml#anchor4_depth_annex (a KEY, not a path) - measured, then rejected as an orphan. 4 edges are
declared, each naming the line of its reader; growth is an edit with a reason.
WHY NOT A may_touch PERMIT (D-2668's lesson): a standing grant over production code cannot be closed; a rail that
refuses the SPLIT is a property and it can be closed.
THE SECOND CLAIM (BUG-564). config/rail_registry.yaml#commit_boundary declares the hook's REQUIRED TEXT;
check_rail_registry.py verifies it against the bytes: a dormancy claim said WHICH file exercises a rail, it could not
say the file still DOES.
MEASURED AFTER. consumers 11/11 controls, write moment rc=0 and state rc=0 on the live tree; registry 9/9 + live rc=0
(80 ladder invocations, 56 rails invoked, 41 on disk); hook dry-run rc=0 with all four commit rails; just health rc=0;
check_repo_integrity rc=0. The hand-edit of the hook was REFUSED by the ladder until the line was declared in its
tracked source scripts/install_git_hooks.sh - the repo's own control, seen to fire.
NO DELEGATE SIGNATURE IS CLAIMED (R5): no local verifier of the required capability was reachable this session.
