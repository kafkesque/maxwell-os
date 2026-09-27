# Maxwell OS v3.0 — MASTER TASK REGISTER (tiered)

> **Updated:** 2026-09-20 | **Archive (full history):** `archive/governance_pre_tiered_2026-09-03/MASTER-TASK-REGISTER.md`
> **Companion:** `governance/aggregated_remaining_tasks.md` (archived copy in same folder)
>
> **Convention (standing rule):** unresolved/undone tasks at the TOP (most critical first, MUST→SHOULD→WORTH); resolved/done at the BOTTOM.

---

## 🔴 MUST — open (strategic-consequential order)

> **NEW — 2026-09-27 (D-2676: THE STANDING RULE, mechanized).** Adopted: no rule lands without (i) ONE HOME, (ii) a SEEN boundary control, (iii) a NAMED oracle, (iv) a MUTATION that REDs it. (iv) is now a rail: scripts/check_rail_mutations.py + config/rail_mutations.yaml, wired into just health (15/15 controls; 2 rules SEEN to red at a real mutation; 1 negative control stayed green; rc=0). THE FORENSIC AUDIT BEFORE THE COMMIT found a THIRD defect in the gate itself (its selftest restated the boundary rehearsal's control count - a SECOND HOME of a declared fact, D-2646) plus a docstring claiming the SUBJECT's bytes are restored where the code restores the FIXTURE copy; both fixed and cited in the D-2676 record, and the audit FILED BUG-577 (one rule, two homes). Its own first runs had already found two real defects in this session's declarations (single-quoted YAML does not process an escape; a marker printed on both verdicts has no baseline differential). NEXT: apply the rule to its first subject — BUG-576 (RAIL 0 unborn HEAD) must land WITH a boundary control and a mutation entry that reds it, and the declared --no-verify bootstrap in config/boundary_rehearsal.yaml must then be WITHDRAWN.
>
> **NEW — 2026-09-27 (D-2675: the BOUNDARY REHEARSAL, the class-level closure of BUG-527/566/568/569/574).**
> The write boundary is now exercised at a REAL commit in a REAL repository built in the system temp dir (live
> `--separate-git-dir` layout, hook installed by this repository's OWN installer): a real NORMAL commit and a real
> PARTIAL commit must both PASS, each in-place PLANTED violation must be REFUSED by its DECLARED rail, and every
> write-boundary rail's own `--selftest` must fire — 13/13 controls, rc=0 in 11.5s, wired into `just health`.
> MEASURED, and the reason it exists: 13/13 git-subject controls were GREEN while 100 percent of commits were REFUSED.
> **OWED, FILED AS BUG-576:** a FRESH repository cannot make its FIRST commit — RAIL 0 reads an UNBORN HEAD as broken
> metadata (the exact state the BUG-400/BUG-564 RECOVERY route produces). The rehearsal carries a declared `--no-verify`
> bootstrap that MUST BE WITHDRAWN by a decision the moment BUG-576 is fixed.

> **⚠️ SUPERSEDING ENTRY — 2026-09-21 (D-290..D-296: M1 Max / oMLX 0.7 / goose runtime optimisation).** Parallel workstream to the R2/ANCHOR path, scoped to the **runtime + agent layer** — see `governance/MARKET_RESEARCH_20260921.md`. Phase 0 ✅: goose UI core-steal fixed (`defaults write com.electron.goose NSWindowOcclusionDetectionEnabled -bool false`; D3251/D2262). Phase 1 IN-FLIGHT: (a) pin oMLX `0.7.0.dev2` + enable Lightning MTP for Qwen3-Coder S2 (D-291/D-293); (b) re-assert `assert_omlx_no_cache` — live `~/.omlx/settings.json` has `cache.enabled=true` + `gdn_ssd_split_enabled=true` (D-292, D2460 thrash flags); (c) oQ4e quant A/B under A10 (D-294); (d) switch goose `active_provider` off `custom_deepseek` → `maxwell_omlx` (D-295); (e) `scripts/bakeoff_typed_decision.py` drafted → gemma-4-E4B R5 review (D-296). Phase 2: typed-decision bake-off vs DeBERTa NLI on the 150-row ruler. Hard limits (not configurable on M1 Max): NAX, neural accelerator, CED, Cluster v2, Apple AFM weights.

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (D-289 RESOLVED → cognitive science de-negated → full r5 collapse → R2 re-run).** **(1) D-289 RESOLVED** — user chose Option A (widen definition). Cognitive-science definition de-negated in r5 + taxonomy in lockstep (removed "NO design/persuasion/economic-application intent" + "as pure cognition … in itself"). Targeted re-score: **contra 126/133 (94%) → 6/133 (4%)**. Menu re-rendered (menu_hash cac6e695→**73597ee2**). **(2) FULL r5 COLLAPSE DONE** — 4 non-core discipline defs (cultural studies / risk management / decision making / organizational theory) folded into taxonomy_v5.yaml; dead r5 content_type overrides (4) dropped (arm C bypasses them). r5 now = 9 discipline include/exclude OntoClean boundaries only. **(3) R2 corpus NLI RE-RUN** in progress (v2 report, new menu_hash + r5_hash). **NEXT critical path: (1) finish R2 v2 + confirm final contra numbers; (2) adjudicate contra-flagged cases → build ANCHOR-1; (3) per-slot κ vs ANCHOR-1 (M2 pivot); (4) BUG-312 fix: DB→JSONL export + re-meter for exactness; (5) FINAL r5 empty (move include/exclude into taxonomy or drop — resolve the 5 British/American spelling-variant "drifts" by removing the now-redundant r5 `definition` fields).**

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (BUG-311 RESTORED → BUG-312 drift → R2 corpus NLI DONE → BUG-313 cognitive-science anomaly).** **(1) BUG-311 RESOLVED** — stage5 checkpoint restored crash-safe (7995 FBs, 0 malformed). **(2) BUG-312 NEW (provenance drift)** — three divergent snapshots: stage5 (Sep 4) < stage4 (Sep 11; 14% disc / 30% domain diffs) < maxwell.db (Sep 19; 2.9% disc / 4.4% domain diffs); no JSONL matches the DB. **(3) R2 corpus NLI DONE** (arm C, option B, ~27 min) — **31,525 pairs, 5,438 contra (17.3%), 0 errors** → `governance/r2_definition_nli_20260920.json`. Per-axis: discipline 9%, domains 18%, content_type principle 21%. **(4) BUG-313 NEW (HIGH)** — **cognitive science 94% contra (126/133)** after D-285 sharpening ("pure cognition, NO design/persuasion/economic intent") vs corpus FBs that are design/learning-applied; other core disciplines clean (psychology 0%, behavioral economics 5%, design thinking 12%). **NEXT critical path: (1) HUMAN decide BUG-313** — widen cognitive-science definition vs re-label 133 FBs (→ D-289); **(2) adjudicate contra-flagged cases → build ANCHOR-1** (priority: cognitive science 133 + high-contra domains engineering&infra 67% / finance 62% / urban planning 45% / personal productivity 44% / media&entertainment 40% / design strategy 42% / education 36%); **(3) per-slot κ vs ANCHOR-1** (M2 pipeline-vs-user agreement); **(4) BUG-312 fix**: DB→JSONL export + re-meter for exactness; **(5) full r5 collapse** (fold 4 non-core discipline overrides + drop dead r5 content_type definitions bypassed by arm C).**

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (BUG-310 RESOLVED → both axes 0 cross-listings; R2 arm C smoke-tested; BUG-311 checkpoint MISSING).** **(1) BUG-310 RESOLVED** — user "approve all 37"; `scripts/fix_bug310_domains.py` applied (caught + fixed a case-variant dedup bug). **0 raw-alias cross-listings on BOTH discipline and domain axes.** **(2) R2 arm C smoke-tested** — ran `definition_nli_verify.py` on the 40-FB probe: 95 label pairs, 14 contra, 0 errors; report stamps paraphrase + menu_hash + r5_hash. CAVEAT: probe has 0 content_type labels, so the content_type paraphrase arm is code-correct but not corpus-validated. **(3) BUG-311 NEW (HIGH)** — the full stage5 checkpoint `knowledge pipeline/stage5_verify/t11/checkpoint.jsonl` is MISSING (only 12 `.bak_*` backups ~100MB, most recent `checkpoint.jsonl.bak_20260904_152319`). **NEXT critical path: (1) restore the stage5 checkpoint** from backup (or re-run stage5 to get a fresh corpus WITH content_type labels) — this unblocks the full R2 corpus run; **(2) full R2 corpus NLI run** (arm C) over the restored checkpoint; **(3) per-slot κ vs ANCHOR-1** (pipeline-vs-user agreement, since M2 no-second-human); **(4) full r5 collapse** (fold 4 non-core discipline overrides + drop dead r5 content_type definitions).

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (M1 applied → discipline cross-listings 0; M2 BLOCKED no-second-human; BUG-310 domain cross-listings NEW).** **(1) BUG-309 FULLY RESOLVED** — user M1 rulings applied via `scripts/fix_m1_rulings.py` (Color Psychology→color theory, Computational Models of Social Life→complex adaptive systems, Decision Science→decision making, Simulation→computational physics & simulation, Rhetoric→linguistics, persuasion-split of the behavioural-economics compound, macroeconomics→economics). **Discipline raw-alias cross-listings = 0.** **(2) BUG-306 PERMANENTLY BLOCKED** — the user is the only human ("no second person"); a self re-score is intra-rater, not inter-rater, so κ CT 0.333 is the FINAL number (contaminated intra-rater). PIVOT: measure pipeline-vs-user agreement (the user's labels ARE the ground truth for a solo project) instead of inter-rater ceiling. **(3) BUG-310 NEW** — the domain axis has **37 raw-alias cross-listings** (the BUG-309 sweep only covered disciplines); exclude-signal is unreliable on domains, so ALL 37 batched → `governance/bug310_domain_crosslistings.md` (recommendation table). **NEXT critical path: (1) HUMAN batch-ratify BUG-310** (37 domain cross-listings → I fold + re-render menu); **(2) R2 corpus NLI run** (arm C meter is ready + provenance-stamped; ceiling re-measure no longer blocks it); **(3) re-measure per-slot κ vs ANCHOR-1** (mechanical, frozen anchor — pipeline-vs-user agreement); **(4) full r5 collapse** (fold 4 non-core discipline overrides + drop dead r5 content_type definitions).

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (arm C ADOPTED; BUG-309 7/11 resolved + 4+2 batch; BUG-306 prepped).** **(1) Arm C is now LIVE** — `scripts/definition_nli_verify.py` builds the content_type hypothesis from a per-role PARAPHRASE content-claim (`config/content_types.yaml` `nli_paraphrase`, single source also read by `r2_ab_harness.py`); discipline/domains keep the definition hypothesis; R2 report stamps `content_type_hypothesis: paraphrase` + `menu_hash` + `r5_hash`. **(2) BUG-309 7/11 resolved** via `scripts/fix_bug309_unambiguous.py` (economic theory/microeconomics→economics, software architecture→SWE, systems design→systems engineering, strategic decision making→strategic thinking, large language models→generative ai, computer vision→machine learning); **4 ambiguous + 2 misplacements → `governance/bug309_batch_ratification.md`** (color psychology, computational models of social life, decision science, simulation, rhetoric, behavioural economics+persuasion — need human call). **(3) BUG-306 re-measurement prepped** — fresh blind sheet `governance/CEILING_REMEASURE_BLIND_SHEET_20260920.csv` + `governance/bug306_remeasure_protocol.md` (blocked on a genuinely different second human). **NEXT critical path (dependency order): (1) HUMAN batch-ratify BUG-309** (4+2 above) + fold rulings → re-render menu; **(2) HUMAN: BUG-306 second coder** (re-measure κ, replace the contaminated 0.333); **(3) THEN R2 corpus NLI run** over the stage5 checkpoint (meter = arm C paraphrase, now provenance-stamped); **(4) re-measure per-slot κ → lift BOUND / merge only if inseparable**; **(5) full r5 collapse** (fold the 4 non-core discipline overrides + drop r5 content_type `definition` now that arm C bypasses them).

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (D-285/D-283 RATIFIED + alias conflicts resolved + fold done; BUG-307 resolved; BUG-309 new).** The user ratified **D-285 (discipline boundaries)** and **D-283 (CT boundaries)**. Execution completed: **(1) D-285 raw-alias cross-listings resolved** via `scripts/fix_d285_alias_conflicts.py` (surgical, text-preserving): cognitive ergonomics + cognitive psychology → cognitive science; behavioral psychology + creative psychology + psychology of creativity → psychology; persuasion → design psychology; problem solving → cognitive science; canonical-name self-collisions fixed (color theory ⇢ visual-perception raw, economics ⇢ political-economy raw, clinical psychology ⇢ health-&-medicine raw — each already excluded the true home). **(2) Strengthened definitions FOLDED into canonical** — 5-core taxonomy_v5.yaml definitions now semantically match r5; content_types.yaml principle description lost the BUG-305 "NOT a procedure you EXECUTE" self-negating phrase (now epistemic STATUS). New **menu_hash cac6e69546f0dd7f**. **(3) BUG-307 RESOLVED** — dead `_R5_REPAIR_PATH` removed; R2 report now stamps `menu_hash` + `r5_hash`. **(4) BUG-309 NEW** — 11 NON-core raw-alias cross-listings remain (color psychology, computational models of social life, computer vision, decision science, economic theory, large language models, microeconomics, simulation, software architecture, strategic decision making, systems design) + 2 adjacent misplacements (rhetoric, behavioural economics+persuasion); OUT of D-285 scope → batch-ratify (D-286). **NEXT critical path (dependency order): (1) adopt arm C** — rewrite `scripts/definition_nli_verify.py` hypothesis construction to per-role paraphrase content-claims (D-284 verdict); **(2) batch-ratify BUG-309** (11 non-core cross-listings + rhetoric/compound); **(3) re-measure ceiling properly** (BUG-306 — different second human, both on post-D-282 menu); **(4) R2 corpus NLI run** over stage5 checkpoint; **(5) re-measure per-slot κ → lift BOUND / merge only if inseparable**; **(6) full r5 collapse** (fold the 4 non-core discipline overrides + remove r5 `definition` fields so override layer disappears).

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (D-285 / BUG-308 — discipline boundary re-derivation + "3+ domains" sweep).** Two further corrections. **(A) D-282 was INCOMPLETELY applied (BUG-308):** the "a filter across 3+ domains" role test still lived in 8 prompt/form files (`stage2_extract.py`, `build_ruler_sheet.py`, `build_joint_vote_set.py`, `deepseek_frontier_audit.py`, `reverify_content_type_108.py`, `RULER_MENUS_20260917.md`, 3 adjudication forms) + a leftover "(1/2/3+ domains)" in the r5 quarantine/principle defs + the dead `depth_test_domains_threshold: 3`. ALL swept to "self-contained transferable filter at ANY scope (depth is the separate axis, never a role test)". **(B) Discipline boundaries re-derived (D-285)** per user direction: design psychology = EXPLOITATION of cognitive biases to persuade/manipulate; cognitive science = pure cognition (memory/reasoning/cognitive-load DEFAULT); psychology = behaviour/emotion beyond computation; behavioral economics = descriptive economic bias; design thinking = innovation process. Five mutually exclusive (symmetric excludes verified); taxonomy + r5 in lockstep; menu_hash re-rendered 14540ec3… Pending: **ratify D-285 + D-283**.

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (D-283 / D-284 / BUG-307 — CT boundary sharpening + R2 A/B verdict).** The "R2 is broken" blocker (BUG-305) is **LARGELY RESOLVED**. The universal-contra was NOT fundamental — it was the OLD principle meta-definition's self-negating phrasing ("NOT a procedure you EXECUTE"). The new r5 principle definition (**D-283**, SHARPEN + BOUND, pending ratification) dropped principle-class false-contra **~1.0 → 0.27**. The R2 A/B harness (**D-284**, `scripts/r2_ab_harness.py`) measured: **paraphrase (arm C) beats definition (arm B) as a mislabel detector** (wrong-contra 91% vs 55%; false-contra 0.233 vs 0.267) → **KEEP NLI on content_type (reject drop-CT), adopt paraphrase**. New remaining critical path (dependency order): **(1) HUMAN RATIFY the D-283 boundary sharpening** (principle↔growth_edge↔process_template) in `config/r5_slot_repair.yaml`; **(2) adopt arm C** — rewrite `scripts/definition_nli_verify.py` hypothesis construction to per-role paraphrase content-claims + stamp an `r5_hash` on the R2 report (BUG-307); **(3) re-measure the ceiling properly** (BUG-306 — a genuinely different second human + both coders on the post-D-282 menu); **(4) THEN the R2 corpus NLI run**; **(5) re-measure per-slot κ → lift BOUND / merge only if inseparable**.

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (BUG-305 / BUG-306 — drift test + human-gate evaluation).** Two NEW blockers above everything below. **(A) R2 is BROKEN — do NOT run the R2 corpus NLI yet.** The D-282 drift test ran the real R2 NLI: premise=object DEFINITION, hypothesis=label's menu definition → the `principle` hypothesis produced **entail 0.00–0.05 / contra 0.97–0.99 on EVERY object** (incl. pure specialized principles "chess opening", "typography leading"). Root cause: NLI entailment cannot test category membership — a category meta-definition is never entailed by its own instance (BUG-305). The depth fix itself HOLDS (static config clean; 0 specialized-principle→quarantine drift in the human pass), but the mechanism meant to enforce it is a broken meter. **(B) The single-coder ceiling κ is contaminated and must be re-measured** (BUG-306): κ(coder1,coder2) = CT 0.333 / DISC 1.000 / FORM 1.000, but (1) the SAME person did both passes (intra-rater test-retest, an upper bound on inter-rater); (2) coder 1 predates D-275b/D-282, coder 2 uses them → κ partly measures a rules change; (3) coder 1's 12/30 quarantine labels leak the pre-fix "3+ domains" conflation. 17/30 rows carry "not sure if…" notes → the CT axis (principle↔growth_edge↔process_template) is under-specified, independent of depth.

> **⚠️ SUPERSEDING ENTRY — 2026-09-20 (D-278..D-282). Add this ABOVE everything below.** The R5 repair definitions, single-coder ceiling sheet, R1 closed menu + `menu_hash` + `*_source` provenance columns, and R2 definition-anchored NLI are now **IMPLEMENTED and verified**. Remaining critical path (dependency order): **(1) HUMAN RATIFY the R5 definitions** in `config/r5_slot_repair.yaml` (definition + include + exclude for the 7 weak slots — approval is what lifts BOUND); **(2) SECOND-CODER PASS** — a second independent human fills `governance/SINGLE_CODER_CEILING_SHEET_20260920.csv` (30 rows, label columns blanked) to bound the human ceiling κ(coder1, coder2); **(3) R2 CORPUS NLI RUN** — `python3 scripts/definition_nli_verify.py --input <stage5 checkpoint>` over the corpus; **(4) re-measure per-slot κ** against ANCHOR-1 with the repaired definitions; **(5) lift BOUND / merge only if definitionally inseparable**. D-282 fixed a depth-vs-role conflation: "3+ domains" is the universal-DEPTH threshold, NOT the principle-ROLE discriminator — a domain/specialized principle (1–2 domains) is still a principle.
>
> **⚠️ SUPERSEDING ENTRY — 2026-09-19 (D-274a–h, BUG-295–BUG-301, F-38–F-46). Add this ABOVE everything below; the entries after it were written before the serving gate was understood.** Read first: governance/ROUNDTABLE_CROSSEXAM_20260919.md and governance/SESSION-HANDOFF-2026-09-19.md.
>
> **THE CRITICAL FINDING: the serving gate is a LABEL, not a verification verdict.** scripts/apply_phase1_finalize.py:18 sets status = 'PASS' if content_type == 'principle' else 'QUARANTINE' and writes it at :163 (apply_phase1_adjudication.py and repass_pair_agreed.py also move rows across the gate on label grounds). The live DB matches that rule on **4,745/4,745 PASS rows and 0/1,470 non-principle rows**. Consequences, measured against verification_results (populated on 7,995/7,995 rows): **2,447 rows (30.6%) disagree with their own persisted factual.passed**; **1,941** served rows failed their own verification (**138 NLI CONTRA-majority**, 1,514 NEUTRAL, 278 with all evidence flagged non-evidence fragments, 11 MECH/artifact); **506 ENTAIL-majority rows are hidden**. An honest gate moves PASS **4,745 → 3,310**. => **ROLE is the highest-leverage axis, not decorative; D6 / BUG-280 / D272g are INVERTED.** The gating axis has **lift −0.010 over a constant answer**.
>
> **REVISED CRITICAL PATH — 0a/0b/0c ✅ DONE 2026-09-19 (later session). The remaining path is (1) → (2) → (3), in that order.**
> **(0a) ✅ DONE** — `scripts/apply_serving_gate.py` re-derives status from `verification_results[factual].passed` + typed `s5_reason` (new `fbs.s5_reason` column); one writer; label-derived status writes are hard errors; CI invariant PASS ⟹ factual.passed. Applied PASS 4,745 → 3,299 (de-served 1,941 + 11 duplicates; restored 506); 0 invariant violations. Also closed BUG-276 (DB backup), BUG-299, BUG-302. → **G17**
> **(0b) ✅ DONE** — facet predicate pushed into EVERY leg (FTS, vector, keyword) via shared `_facet_conditions` + asserted on the fused pool via `_matches_facet`; keyword leg is now query-aware. Constraint-violation rate **0.5911 → 0.0000** over 470 probes. Closed BUG-285, BUG-300. → **G12**
> **(0c) ✅ DONE** — write guard split: `validate_discipline_domain()` (row guard, fail-closed on illegal labels only) vs `lint_discipline_domain_vocabulary()` (reports DECLARED collisions, never rejects). `research methodology` (D-271a) now passes the write boundary. Closed BUG-286. → **G18**
> **(1)** persist the tier stage 5 already computes (epistemic_status / isor / verification_method — stage6 has NO columns for them) and de-literal the verifier stamp (stage5_verify.py:898). → **G19**
> **(2)** correct the ruler estimand: the FLOOR column compares stored-label **accuracy** to min_human_share, a **provenance share** (score_ruler_labels.py:136/184 vs eval_integrity.yaml:28-31). All STOPPED/CONTINUE verdicts are **withdrawn**; only the constant-baseline lift stands (ROLE −0.010, discipline +0.422, FORM +0.472). **G4a is WITHDRAWN.**
> **(3)** R5 → R1, driven by the decision procedure config/content_types.yaml ALREADY declares (content_type_rules / D2587), with none as a first-class outcome.
>
> **DO NOT (priority-excluded):** re-label the corpus; buy ~85 more stratum-A rows (value-of-information ≈ 0); **train/fine-tune or swap S2/S4 on the current labels** (no provenance column exists anywhere, so min_human_share is unsatisfiable and no axis may gate a model comparison — a model fitted here learns the script's gate and a verifier whose own calibration is P 0.647 / R 0.386 / F1 0.484); extend the alias map; adopt ACORN; re-cut the 61/43 ontology; re-derive FORM on the pocket (the F-14 contrast is **statistically null** — BUG-296); add the chunk leg / vec_fbs_ctx / contextual embeddings / weighted RRF before 0a–0b; run R2 before R5/R1; delete the junk rows. **The D-2637 model-eval workstream is NOT on the critical path.**
>
> **Answer to "do we need a clean anchor to train S2/S4, or a different approach":** the anchor is a **versioned human-adjudicated CONFORMANCE set** (ANCHOR-1 = the frozen 150 blind rows with their 51 abstentions; ANCHOR-2 ≈ 100 fresh rows drawn AFTER the vocabulary freeze; a 30-row test–retest as the single-coder ceiling; per-axis positive/near-neighbour/OOV/contradiction sets; must-link/cannot-link pairs for work identity; known-item queries derived from source_segments, NOT from live search output). **Not a training set.** The different approach is not a different model — it is removing the LLM's authority over what the rules already decide (D274g).

> **PHASE A COMPLETE (2026-09-14, D2619/D2620/D2623/D2624/D2625).** Anchor frozen at **216 principle** (214 spotless + 1 emerging + 1 abductive-duplicate); 9 locked discipline/depth rulings + abductive merge applied (`p5:human-locked`); 108 d2615-principle rows emitted to `governance/expansion_queue_108.jsonl` (NOT folded); re-tiered → **gold_4axis 231 (214 principle) / pending 189 / silver 23**. Non-contamination guard `validate_discipline_domain()` wired + CI-tested (D2620).
>
> **PHASE B + FORENSIC FOLLOW-UP (2026-09-14, D2626–D2630).** (1) D2626: authority sets consolidated into `pipeline/axis_authority.py` (single source of truth — drift bug class eliminated); D2620 guard wired fail-closed into S4 (`stage4_merge.validate_classification`) + S6 (`stage6_commit.insert_fb`). (2) D2627: 32 `(N)`-suffix name-collision pairs judged mechanism-aware via Qwen3.8 (10 dup + 22 distinct → `governance/dedup_suffix_judgments.json`); remaining 269 name-stem groups pre-filtered deterministically → **0 pairs with def+mech Jaccard ≥ 0.35 (pure name-stem collisions, no judge run warranted)**. (3) D2628: domain-aggregation policy formalized (human-curated; reliable-pair votes advisory only). (4) D2629: 108-queue content_type re-verify → **49/108 = 45.4% NOT principle** (39 process_template + 4 noise_drop + 4 tool_instruction + 1 growth_edge + 1 process_instance); 59 remain principle. (5) D2630: `apply_dedup_marks.py` added `fbs.duplicate_of` + marked 17 rows duplicate_of + QUARANTINE (never delete; PASS 4762→4745 / QUARANTINE 3233→3250, integrity ok). REMAINING MUST (in order): **(a)** re-vote depth+discipline+domains for the 59 queue rows that REMAIN principle (grow anchor beyond 216 by at most +59) → **✅ DONE (D2631): 59/59 voted, 34 accepted under D2633 union → 20 full 4-axis rows into `gold_4axis` (214→234 principle; 14 depth-abstained + 23 contested-discipline + 2 disjoint stay pending-human)**; **(b)** A/B harness ARM-1/2/3 (D2618, gated on gold_4axis as frozen eval) → **ARM-1 DONE (D2632): FLAT beats HIERARCHICAL (discipline macro-F1 0.229 vs 0.175); domain head near-useless both (macro-F1 ~0.007-0.009)**; **(c)** resolve the OPEN domain-aggregation auto-policy (exact-set unanimity vs overlap/union) for the 148 auto-acceptable rows → **✅ RESOLVED (D2633): user ruled overlap→union (B), always including DeepSeek's classification; `scripts/aggregate_domain_votes.py` → 148/216 accepted**.

> **3-MUST EXECUTION (2026-09-14, D2631–D2634).** (a) D2631 QUEUE-59 re-vote **✅ DONE** (59/59 voted; D2633 union → 34 accepted; `apply_queue_59_anchor.py` → 20 full-4axis rows into `gold_4axis`, anchor 214→234 principle; 14 depth-abstained + 23 contested + 2 disjoint remain pending-human). (b) D2632 A/B harness ARM-1 built + run on frozen `gold_4axis` (214 principle): **FLAT classifier wins discipline macro-F1 0.229 vs hierarchical 0.175** (coarse-gating hurts on the verified core); domain head near-useless (43-way multi-label starved → confirms D2613 bge-m3 taxonomy-match); confidence compressed (no ≥90% precision at useful coverage). (c) D2633 domain-aggregation auto-policy **RESOLVED — user ruled overlap→union (B), always incl. DeepSeek**; `aggregate_domain_votes.py` → 148/216 accepted. (d) D2634 accuracy-dependence analysis: accuracy is driven by per-class TRAINING data + label quality (NOT anchor size/architecture); training set = retired gpt-oss SILVER (1027 ex, 93.3% unverified) — too small AND unverified; domain → bge-m3 taxonomy-match; targeted ingestion for the 18 starved disciplines (9 CRITICAL + 8 HIGH + 1 MODERATE).

1. **VERIFIED-CORE FREEZE (D2613, 2026-09-11) — ✅ DONE through Phase A (see note above).** The "golden" set is silver: all 1,027 examples in `stage4_golden_mined.yaml` = "gpt-oss teacher labels … NOT hand-reviewed" (gpt-oss 1027 / DeepSeek 0 / human 0). Only **69 examples (frontier69) are verified on all 4 axes** (content_type+depth+domain+discipline); content_type 314, domain/discipline 138, depth 133+69 — disjoint subsets, intersection 69. **Phase 0 ✅ DONE (D2616, 2026-09-13):** the mechanical stop-the-bleeding fixes are applied — `commit_non_fb_types:true`, route deprecated (missing ct→quarantine), 1,365 vote-confirmed non-principle rows demoted in DB, Pydantic runtime boundary wired. **Phase 1 ✅ DONE (D2617, 2026-09-13):** `scripts/build_verified_core.py` (deterministic) froze the sole eval target `governance/verified_core.jsonl` = **443 unique rows** (149-core + 298-sample; 4 fb_id overlap). R14-stamped, `verification_status` honest: human-verified 28 / joint-vote-verified 121 / **pending-human 294** (the 298-sample D2615 boundary batch, still awaiting human adjudication). The 1,027 `stage4_golden_mined.yaml` is demoted to a silver candidate pool — **BUG-241 retired at the data level**. **Phase 1b (REMAINS):** (a) human-adjudicate the 294 pending-human rows; (b) run a DeepSeek+Qwen3.8 **domain/discipline** verification pass on the verified principle rows — the ONLY axis the pair has never voted (spotless recount: ct+depth cross-checked 702, strict 4-axis 153, disc/dom non-silver 209/1027). Corrected canonical counts: **43 domains / 61 disciplines** (taxonomy_v5.yaml; prior drift cited 35/75). The joint vote (D2612) is TRANSITIONAL 2-model silver — strictly better than current, but not verified truth. **Phase 1c (A/B-GATED, D2618, 2026-09-13):** three frontier auditors diverged on classifier architecture (Claude hierarchical ModernBERT+SetFit+conformal / Qwen RAC / GPT contract-first). RULING: A/B-test the ARCHITECTURE; do NOT A/B the correctness prerequisites. P0 (0 LLM, deterministic): split `verified_core.jsonl`→immutable `gold_4axis/pending_4axis/silver_4axis`; normalize `p5:*` provenance; re-PASS the 1,750 wrongly-quarantined pair-agreed rows (verify vs live DB); reconcile 25 missing review-queue fb_ids; wire `gold_4axis` into all `train_*.py` `load_golden_set()` + archive `stage4_golden_mined.yaml` from eval. A/B HARNESS (reuse D2577/D2610 fixed-split on frozen gold_4axis held-out): ARM-1 classifier (hierarchical vs RAC vs flat+conformal, $0 local); ARM-2 CRIBS (gpt-oss vs Qwen3-Coder on frozen D2293 benchmark); ARM-3 abstention (raw threshold vs conformal/selective vs SetFit). NO architecture committed until arms report. Unconditional fixes: `_masked_fine_pred` -inf flat-logit fallback; S5 char→token truncation; remove dead `route=FB`; S5 classification-entailment. Honest guarantee = fail-closed prevention of silent acceptance, NOT semantic 100%.

---

## 🟠 SHOULD — open

0. **ANCHOR-EVAL COVERAGE (logged 2026-09-14, D2634 follow-up).** Grow the verified anchor (`gold_4axis`) to **≥10–20 verified examples per discipline** so macro-F1 measurement stops bouncing. Currently **35/57 disciplines have ≤3 eval rows** — with 1–3 examples a class's F1 is 0/33/67/100% (coin-flip), so the macro-F1 average is unstable *even if the classifier doesn't change*. This is an **EVAL-TRUST task (trustworthy grade), NOT an accuracy task** — growing the anchor doesn't make the classifier smarter, it makes the score meaningful. Sources to seed it: the 190 incomplete rows (`scripts/audit_human_verification.py` → `governance/remaining_verification_audit.csv`: 135 depth+disc+dom, 33 disc+dom, 14 depth, 8 other) + 106 stale-label rows (complete but `verification_status` still "pending-human"), the 59 queue re-vote (D2631, now partially applied), and targeted-ingestion output (D2607-D). Target ≈ 10–20 ex/discipline × 61 ≈ **600–1,200 verified principle rows** (today: 234 rows / 57 disciplines).

1. **CLASSIFIER** — TRAINING SCRIPT WRITTEN (D2571: `scripts/train_discipline_classifier.py`, deberta-v3-base + LoRA + 2 heads). REVISED (D2577): switch base → answerdotai/ModernBERT-base (139M, 8192 ctx, ~2x faster), FULL fine-tune (drop LoRA — peft dep + invalid q_proj/value_proj target_modules bug both vanish; DeBERTa disentangled attention made LoRA a silent no-op). Heads kept: softmax-61 discipline + sigmoid-43 domain + abstain→emerging. CORRECTED PLAN: depth is NOT a classifier target — drop depth stratification. Mine ~750–1000 CONVERGENT FBs stratified by discipline (min 10/max 30, all 61 covered) + domain coverage. Use `is_convergent` as a soft quality signal, backfill single-source only if a discipline has <10 convergent. ✅ TRAINED RUN #1 (D2578): macro-F1 0.2621 (target 0.75) — data-limited (silver labels + ~20 ex/discipline), NOT a model-selection failure. ✅ BACKFILLED (D2579): mined set 1000→1026 ex, 61/61 covered, trainable 50→58; stratification truncation bug fixed (floor + round-robin). ✅ DATA-ABSENT RESOLVED (D2584): the 3 disciplines were NOT missing content — they had unresolved domain axes (`domains=["emerging"]` despite real `domains_raw`). Fixed via alias-map extension (19 robotics/autonomous-systems + theoretical-CS labels → `engineering & infrastructure` / `computational science & physics`) + `scripts/resolve_data_absent_domains.py` re-derivation. Result: computational theory 4→5, ecology 4→5, robotics 1→5; golden set 1026→1027 ex; 61/61 disciplines trainable (was 58). Also applied `bug197_kind_swap` (D2583 next-step): 400 FBs (2 discipline + 35 domain recovered). NEXT (D2585 — roundtable verdict 2026-09-06): the 3-model vote is RETIRED as the ultimate label-quality solution (D2582 → SUPERSEDED); durable path = weak-supervision label model. ✅ P0 DONE (baseline macro-F1 0.1845, 61/61 trainable, 33 data-starved, confusion matrix saved). ✅ P1 DONE (LF-audit: T-NLI vs cleanlab near-INDEPENDENT phi=0.09 → Dawid-Skene independence defensible; cleanlab is uncalibrated recall). ✅ P2 DONE (`build_label_model.py`: Dawid-Skene EM π=0.785, 135 high-suspicion golden FBs = challenger/GOLD-A seed). ✅ P3 CHALLENGER DONE (2026-09-06): 135/135 high-suspicion FBs voted (3-model cross-family) → `temp/label_vote_high_suspicion.jsonl`. ✅ P4 RETRAIN DONE: `build_p4_training_set.py` applied **59 challenger corrections** (4 deferred to P5 human GOLD — non-canonical / class-floor) → `stage4_golden_mined_p4.yaml` → retrained `classifier_modernbert_p4_clean`. **RESULT macro-F1 0.2875 (target 0.75) — DATA-LIMITED, NOT model-selection**: temperature-scaling Δ=0.0, conformal coverage 0.89–0.98, but 15+ disciplines sit at 0.00 per-class F1 (data-starved, ~17 ex/discipline avg, silver labels). **The ONLY lever to 0.75 is P5 (hand-verified stratified golden), NOT more calibration.** ✅ P5 FREEZE PLAN DONE (2026-09-09): `scripts/p5_freeze_plan.py` → `governance/p5_freeze_plan.{json,md}` + `p5_human_review_form.md` — tiers GOLD-A 135 / GOLD-B 892 / CHALLENGE 9; root cause quantified: **18/61 disciplines <10 ex** (game design / theoretical physics / privacy & surveillance / robotics / decision making / ecology / generative ai at 5). ✅ P6 DONE: `label_vote.py` marked RETIRED-TO-SPOT-CHECK. ✅ 69-FB QUEUE ADJUDICATED + APPLIED (D2603→D2605, 2026-09-09): DeepSeek-v4-pro adjudication (69/69, 0 contamination) → v4-flash cross-verify (66/69 discipline, 68/69 domain) → human arbiter final ruling → `scripts/propagate_p5_final.py` applied 28 writes (A content_type: 9 noise_drop + 4 principle; B: 11 discipline; C: 6 domain) → stage4_golden_mined.yaml + gold_frozen.yaml + maxwell.db (C13 backup). ✅ 00631 RESOLVED (2026-09-09): discipline=risk management (human re-decision; "strategic thinking" was a discipline mislabel, NOT a domain) → propagated to golden + DB (29 writes incl. this). ✅ P5 RETRAIN DONE (2026-09-09): `classifier_modernbert_p5final` on the 28-corrected golden set → **macro-F1 0.2036** (vs P4 0.2875) — NO improvement, CONFIRMS data-limited: 12 discipline + 6 domain corrections on a 61-way head are immaterial; run-to-run variance (±0.05) dominates. NEXT: (1) Tier3 boundary corpus 9→~150 (D2594); (2) depth 4-way classifier (task #2); (3) commit_non_fb_types (D2590). POLICY FLAG: 0.75 macro-F1 is unreachable with a flat 61-way head on 1027 ex (~17/class, 18/61 <10 ex) — needs a decision: hierarchical head vs ~3-5k mined examples vs LLM-hybrid. ✅ D2607 STRATEGY DECIDED (2026-09-09): audit 2,441 convergent-labeled but 29/61 <20 ex; bare S2 re-run REJECTED (same skew). RULING: C LLM-hybrid (DONE — `pipeline/student_classifier.py` + `stage4.student_preclassifier_*` flag, off-by-default, abstain→gpt-oss; smoke-tested) + B HIERARCHICAL (TEE'D UP — `governance/classifier_hierarchical_design.md`, 61→10 groups) + targeted ingestion (deferred). Tier3 (D2594) DONE: `scripts/build_boundary_corpus.py` grew boundary corpus 9→150 (88 GE / 22 PT / 10 TI / 10 PI / 9 noise_drop / 5 quarantine / 3 noise / 2 neg / 1 — pending 2-of-3 adjudication). NEXT: (1) R5 review + enable student flag (raw 0.35 softmax abstains ~always → needs per-class selective/conformal calibration before real cost-savings); (2) B hierarchical implementation; (3) depth 4-way classifier (task #2); (4) commit_non_fb_types (D2590). ✅ D2609 BUG-233 RESOLVED (2026-09-09, option b+): boundary corpus (150) ruled RULES-REGRESSION-ONLY content_type eval (NOT model-eval); example_ids HELD-OUT from future content_type training via `pipeline/boundary_holdout_guard.py`; (a) rejected as cross-task+data-starvation, plain (b) rejected as prose latent-trap. ✅ C CALIBRATION (2026-09-09): per-class selective thresholds wired + `scripts/calibrate_student_thresholds.py` (R5 gemma APPROVE_WITH_CAVEATS). RESULT: held-out student top-1 27.7%, cannot hit 90% precision at any coverage (best 75%@4%) → C FLAG LEFT OFF (enabling = wrong labels or ~0 savings). RE-SEQUENCED NEXT: (1) B HIERARCHICAL head (structural — now the critical path to a usable student); (2) targeted ingestion ~18 starved disciplines; (3) depth 4-way classifier (task #2); (4) commit_non_fb_types (D2590); then re-run calibration + enable C. ✅ B HIERARCHICAL DONE + MEASURED (2026-09-09): `scripts/train_hierarchical_classifier.py` + `classifier_hierarchical` checkpoint (coarse 10-way + fine 61-way + domain 43-way). Held-out: coarse top-1 54.0% (macro-F1 0.46, 90% precision @ 20% coverage) vs fine-flat 28.7% vs **fine-masked 24.8% (FALSIFIED — coarse 46% error propagates)**. **COARSE HEAD = KEEPER** (10-way student ≫ 61-way as abstention signal). NEXT: (1) wire coarse head as the student pre-classifier signal; (2) targeted ingestion (~18 starved disciplines) to lift fine 61-way. ✅ COARSE HEAD WIRED (2026-09-09): `student_classifier.py` auto-detects hierarchical vs flat checkpoint; added `predict_coarse()` + coarse-gated `predict()` (emit only if coarse confidence ≥0.70 AND coarse↔fine agree); config `student_preclassifier_checkpoint`→`classifier_hierarchical` + `coarse_threshold` 0.70 threaded via `pipeline_paths`/`stage4_merge`; R5 gemma APPROVE_WITH_CAVEATS. Flag stays OFF (fine head under-confident → coarse-gated predict abstains ~100% = safe). ✅ INGESTION PLAN (2026-09-09): `scripts/plan_targeted_ingestion.py` + `governance/targeted_ingestion_plan.{json,md}` → 18 starved = 9 CRITICAL (convergent≤3) + 8 HIGH + 1 MODERATE. NEXT (blocked on new source content): acquire sources for the 9 CRITICAL disciplines → run S0-S2 → mine → retrain. ✅ R5 QWEN3.8 RE-REVIEW (2026-09-10): gemma overruled (unreliable); Qwen3.8-27B reviewed all 5 new scripts → `governance/r5_review_qwen38_session_2026-09-10.{jsonl,md}` (all NEEDS_FIX). FIXED: C16 no-silent-errors, R14 stamps, C12 date+env-override, C18 docstrings, C20 named-constants; C12/C20 module-constants triaged FALSE-POSITIVE (runtime config-driven at `stage4_merge`). ✅ INGESTION SOURCE MAP (2026-09-10): `feed.opml` + `governance/targeted_ingestion_sources.md` → 10 arXiv RSS feeds for the 9 CRITICAL (finding: prior feed.opml covered ZERO of them). NEXT: pull new sources → S0-S2 → mine → retrain hierarchical.
2. **DEPTH-ACCURACY AUDIT** — ✅ AUDITED (D2576): depth is NOT accurate for the rare categories — it OVER-ASSIGNS universal/cross-domain (the OPPOSITE of the documented collapse-to-domain). Cross-family 3-way (gpt-oss origin vs Qwen3.8 + DeepSeek verifiers): gpt-oss agreement 33% (universal 10/30) and 20% (cross-domain 4/20); the two verifiers AGREE with each other (67%) while disagreeing with gpt-oss (33%). Projected: universal 81→~27, cross-domain 713→~143 (~624 over-assigned → should be domain). gpt-oss empirical depth = 75% (not the drifted 87.5% claim). POLICY DECIDED (D2577): depth → dedicated 4-way ModernBERT-base classifier (full fine-tune, no LoRA), SEPARATE from CRIBS+discipline/domain; do NOT patch the ~624 over-assigned now (blanket downgrade lossy) — re-run depth with the classifier post-gate. NEXT: 3-model vote (Qwen3.8-27B + DeepSeek-v4-pro + gemma) on 81 universal + 713 cross-domain + ~200 controls → training set (keep >=2/3 agree, fail-closed to domain); fine-tune; A/B vs gpt-oss generative call (gate macro-F1 >= 0.85). ✅ BUG-224 mitigation applied (D2581: wedge-recovery in `call_omlx`) — UNBLOCKED; still use small single-FB Qwen3.8 calls (workload shaping). ✅ DEPTH BASELINE TRAINED (2026-09-10): `scripts/train_depth_classifier.py` (dedicated 4-way ModernBERT-base, ontology from `pipeline.schemas.DEPTH_LITERAL`) → `knowledge pipeline/classifier_depth`. Golden-silver-label baseline macro-F1 **0.4796** (gate 0.85): universal 0.000 / cross-domain 0.437 / domain 0.815 / specialized 0.667. DATA-NOISE-LIMITED (universal=18 ex, gpt-oss over-assigns ~2/3 wrong per D2576). ✅ DEPTH VOTE EXECUTED (2026-09-10): `scripts/build_depth_vote_set.py` voted 996 FBs with **DeepSeek-v4-pro + Qwen3.8-27B + Qwen3-Coder-30B** (Phi-4-mini/gemma ruled unreliable). First pass compromised (DeepSeek HTTP 402 Insufficient Balance on 781/996 → 78% degraded to 2-voter); recovered the key from shell history + added `--retry-failures`/`--workers` → **982/996 full 3-voter coverage, 915 agreed**. Clean dist: domain 501 / cross-domain 384 / universal 65 / specialized 46. ✅ CONTROLLED EXPERIMENT: `scripts/eval_depth_classifier.py` on a fixed 796/200 split — **clean labels 0.4790 vs silver 0.3409** on the identical test set (**+0.138 / +40% relative**; domain 0.252→0.564). Naive per-set macro-F1 was confounded by class proportion. **VERDICT: vote materially improves depth labels but still below the 0.85 gate → depth is annotation-limited.** NEXT: decide whether 0.85 is the right gate for a 139M encoder, or fold depth into the S4 gpt-oss generative call with the vote set as a calibration/eval reference. D2610 LABEL POLICY v2 EXECUTED (2026-09-10): reliable voters must be unanimous, everything else ABSTAINS (no fabricated domain label); advisory voters non-deciding; checkpoint upserted. Re-derived 996 FBs with no model calls -> 678 confirmed / 318 abstained -> governance/depth_review_queue.yaml. Controlled effect on the identical 133-row consensus slice: 0.4298 macro-F1 / 0.594 acc vs 0.4073 / 0.526 (v1 labels) with 251 FEWER train rows; selective prediction 0.712 acc at 50% coverage. D2611 RECOMMENDATION RECORDED (PLANNED): generative labeler of record + encoder as regenerable cache, retire the 0.85 gate (governance/depth_path_recommendation_2026-09-10.md). ✅ D2612 (2026-09-11): content_type adjudicated — 217 unlabeled golden-mined rows human-adjudicated + DeepSeek-v4-pro R5 second-opinion on FULL text → 201/217 = 92.6% agreement, 16 contested (governance/content_type_contested_16_form.md); frozen non-principle 15.7-16.6%, confirmed-principle 178/217 = 82.0%. BUG-239 FIXED (form generator dropped boundary 217/217 + truncated mechanism 185/217). D2610 policy PORTED to scripts/label_vote.py (reliable-pair unanimity + abstain + provider-aware deepseek routing; was 2-of-3 fail-closed). SCOPE RULING: relabel depth on the CONFIRMED-PRINCIPLE subset (~6,600-6,900 rows), NOT 7,995 (BUG-238: true non-principle 12.7-16.6%, not 0.4%). NEXT: (a) resolve the 16 contested rows (form), (b) relabel depth on confirmed-principle under D2610 (BUG-237), (c) grow the depth eval to >=100 rows/class, (d) add the depth contract test to CI.
3. **D2547** — GATE SCRIPT WRITTEN (D2571: `scripts/apply_cost_weighted_thresholds.py`, cost = n/median). REMAINING: (a) domain-axis frequencies (script queries `discipline` only → domain labels get n=0); (b) cost-model calibration (policy decision); (c) re-derive per-label rates with definition-bearing hypotheses (D2571 finding).
4. **D2548** — grammar-constrained decoding pilot on S4 enums. Outlines/XGrammar NOT installed; gate added (`stage4.grammar_decoding_enabled=false`, D2556). BLOCKED on dependency.
5. **T-OWL** — OWL/SKOS axiom spec for 105 canonicals (D2541).
6. **D2399 (BUG-150 tail)** — FULLY ADJUDICATED 2026-09-05 (D2572+D2573+D2574). 292 gaps = 42 kind-leaks + 250 true-gaps. APPLIED: 6 discipline aliases (12 FBs, D2572); Marketing kind-swap (5 FBs, D2572); **Ecology promoted** + `computer networking` displaced (5+4 FBs, D2573, closed-loop 61→61); **33 kind-leaks cleaned** (D2574). REMAINING: **241 true-gaps** (long-tail open-world labels) — leave as `emerging` unless a label accumulates ≥5 stable FBs for a future closed-loop promotion.
7. **BUG-151** — taxonomy structural overlap (177 raw-alias cross-axis; kind-safe-guarded).
8. **BUG-148** — S2 `route` field stale (`route="FB"` on all 2,878). ✅ CLOSED D2616 (2026-09-13): route deprecated as ontology carrier, missing content_type → quarantine (never principle).
9. **BUG-182** — 48 singleton empty-shells deterministic.
10. **BUG-170** — non-principle types (PT/PI/TI/GE) not classified/enriched.
11. **BUG-159** — prompt-injection contamination (cluster_11649, 0.007%).
12. **GOV-GOLDEN** — archive 8/9 versioned `MASTER-ROUNDTABLE-EVAL-PROMPT-*` + 2 dead golden files.
13. **D2462** — unify single-source + singleton S2 into one extractor.
14. **D2345** — single-source non-type second pass.
15. **BUG-195-code** — S4 cross-cluster dedup + S6 duplicate-fb_id fail-loud guard (post-hoc done; CODE fix for future batches).
17. **C12-ROUTE** — extract `route.py` hardcoded 10%/5% promotion thresholds → config (C12).
18. **P1-6** — config-read fallbacks promote from log to raise (C16 observability).
19. **FINGERPRINT** — S5 input fingerprint load/write fail-closed (P1-1/P1-2).
20. **DEEPSEEK-PROVIDER** — goose `active_provider=custom_deepseek` (deepseek-v4-pro) is LIVE+AUTHENTICATED (Keychain internet-password `https://api.deepseek.com/v1`; live `goose serve → api.deepseek.com:443` connection). NOT dead (D2560 CORRECTED 2026-09-04). Real issue = remote CLOUD API → C1 ($0) + C3 (sovereignty) violation BY DESIGN. Switch `active_provider` → `maxwell_omlx` in `~/.config/goose/config.yaml` (user decision — affects the goose runtime itself).

---

21. **D2440** — S5 verifier calibration experiment (AlignScore 355M + MiniCheck EMNLP-2024 vs DeBERTa-v3-large via `pipeline/calibrate.py` + `nli_calibrate.py`). BLOCKED: `evals/nli_golden.jsonl` not committed → threshold non-reproducible. Adopt only if F1 materially > 0.484 AND fail-closed (D2093) preserved.

## 🟡 WORTH — open (later / after measurement)

22. **T-S1** — S1 contextual embeddings adopt-vs-gate decision.
23. **T-S3** — S3 HyDE A/B run.
24. **D2399** — domain promote/demote (frozen — reopen post-reclass).
25. **D2164/D2165/D2166** — sparse architectural planning (see DECISION-LOG reference links).
26. **D2009…D2084** — 15 legacy DEFERRED infra/CLS items (see DECISION-LOG reference links).
27. **BUG-160** — systematic evidence-passage topical-relevance pass (log-only today).
28. **BUG-169** — verify TI `parameters` at rerun (technique-type vs API TI ontology nuance).
29. **TEST-CLEANUP** — gut/rename `tests/test_stage4_d2138.py` + `test_stage4_exhaustive.py` (0 `test_*` fns).
30. **T-STS** — tautological-mechanism STS (def↔mech cosine; weak signal measured).
31. **T-015/D2292** — golden depth expansion ≥5 universal + ≥5 specialized (BUG-083/084).
32. **BUG-081** — `evals/golden_cases.json` v2 format migration.
33. **BUG-073** — CONV-035/037 false convergence (D2232).
34. **GAP-2** — remove stale Stage 3a artifacts (`prompts/s3a_*.txt`).
35. **SLA** — end-to-end latency SLA (D2305).
36. **B15/D2341** — schema corrections: TI class, three-axis `status`, typed edges, feedback→YAML.
37. **T2.x** — Business PI, atomic evidence, trust state machine.

---

## ✅ DONE — bottom (recent, resolved this/prior sessions)

- **0a/0b/0c — SERVING GATE + RETRIEVAL FACET + WRITE-GUARD SPLIT (2026-09-19, later session)** — (0a) `scripts/apply_serving_gate.py` is the single writer for `status` (derived from `verification_results[factual].passed` + typed `s5_reason` in new `fbs.s5_reason` column; label-derived status writes removed from the 4 label scripts; CI invariant in `pipeline/serving_gate.py` + 15 tests). Applied PASS 4,745 → 3,299 (de-served 1,941 + 11 duplicates; restored 506); 0 invariant violations; duplicates hard-quarantined (`duplicate_of` → QUARANTINE/`duplicate`). (0b) facet predicate in every retrieval leg + asserted on the fused pool (`_facet_conditions`/`_matches_facet` in `pipeline/retrieve.py`); constraint-violation rate **0.5911 → 0.0000**. (0c) write guard split into row guard (`validate_discipline_domain`) + vocabulary lint (`lint_discipline_domain_vocabulary`); `research methodology` now writes clean. Closed BUG-276/285/286/299/300/302; gates G12/G17/G18. ✅
- **BUG-276 — DB backup restored (2026-09-19)** — `pipeline/backup_guardian.sh` repointed at the SQLite DB (consistent `.backup` + integrity-check), was rsync-ing non-existent markdown dirs. ✅
- **BUG-302 — residual status writers routed through the serving gate (2026-09-19)** — `apply_dedup_marks.py`, `reinject_bug198_singletons.py`, `stage5_verify.py` now call `pipeline/serving_gate.derive_status()`. ✅

- **D2636 BGE-RERANKER DOMAIN THRESHOLD SWEEP — DEAD END (2026-09-15)** — `scripts/benchmark_domain_taxonomy_match.py --reranker-only --sweep` on 234 gold_4axis rows vs 43 domains: threshold calibration does NOT help (best micro-F1 0.219 @ tau=0.15 vs top-k=3 baseline 0.324; **macro-F1 0.0 at every threshold** — cross-encoder collapses onto few domains). Confirms D2613/D2634: 43-way domain head is **training-data-limited, not model-limited**; bge-reranker-v2-m3 is not a viable domain classifier even calibrated. ✅

- **D2635 ARM-2 CRIBS + GPT-OSS GENERATOR RETIREMENT (2026-09-15)** — gpt-oss-20b-MXFP4-Q8 vs Qwen3-Coder-30B on the frozen 6-cluster S2 benchmark. Naive run: gpt-oss 6/6 empty-content (`response_format: json_object` → OMLX returns only `role`). Fair re-run (`scripts/arm2_gptoss_fair.py`, no response_format): gpt-oss 2/6 schema-valid vs Qwen3-Coder 6/6 (route agreement 1.0, 30.8s avg). **gpt-oss RETIRED as generator** (non-viable, two complementary failure modes). Classifier role (Q8) REMAINS until ModernBERT student + ARM-3 abstention gate. Pruned 3 benchmark-only models (gemma-4-31B 57GB, gpt-oss-Q4 10GB, Qwen3.5-9B 5.6GB) → `governance/pruned_models_20260915.md`. ✅

- **D2616 S2/S4/S5 FORENSIC AUDIT ADJUDICATION + PHASE 0 EXECUTED (2026-09-13)** — 4 frontier auditors (Claude/GPT/GPT-5.6-Luna/Qwen) forensically audited S2/S4/S5; goose + Qwen3.8-27B verified every claim deterministically (see `governance/ROUNDTABLE_ADJUDICATION_S2S4S5_FORENSIC_2026-09-13.md`). Rejected Qwen's "38% corrupted" (real = 93.3% unverified) + "retire gpt-oss now + Snorkel". **PHASE 0 APPLIED:** `commit_non_fb_types:true` (D2590); route deprecated as ontology carrier (missing content_type→quarantine, `quarantined.jsonl` sidecar, BUG-148 CLOSED); `scripts/apply_phase0_relabels.py` demoted 1,365 vote-confirmed non-principle rows (content_type+depth+status) with C13 backup + R14 manifest + integrity_check ok → fbs content_type: principle 7,966→6,601 / noise_drop 1,054 / process_template 179 / process_instance 121 / tool_instruction 16 / growth_edge 17 / quarantine 7; Pydantic runtime boundary (`validate_fb_content_type`/`validate_fb_depth`) wired fail-closed into S6 `insert_fb`. BUG-243 logged (DeepSeek empty-content on open-ended prompts). 199 tests green. **NEXT (Phase 1):** human-adjudicate the 149-core + 298-sample (~435 verified rows) as sole eval target; Phase 2 local label stack; Phase 3 gated gpt-oss retirement; Phase 4 rebuild store once + 11-mode invariant gates. ✅
- **D2612 JOINT VOTE PRODUCTION COMPLETE (2026-09-13)** — full 7,966-row reliable-pair vote (DeepSeek-v4-pro + Qwen3.8-27B) on content_type+depth finished and hardened. Distribution: principle 4,920 / abstain 1,681 / noise_drop 1,037 / process_template 177 / process_instance 120 / tool_instruction 15 / growth_edge 16; depth-among-principle: domain 3,113 / cross-domain 733 / universal 22 / specialized 4 / abstain 1,048. **needs_review 2,729 (34.3%) = honest epistemic uncertainty** (reliable-pair disagreement), not a defect. Post-run recovery: 21 DeepSeek empty-content rows re-voted via `--retry-failures` → **voter_error_rows 0**; checkpoint compacted 9,555→7,966 lines (one per fb_id, `scripts/compact_checkpoint_lastwins.py`, atomic tempfile+fsync+os.replace); pre/post backups in `governance/backups/`; DB untouched (vote-only). ✅
- **D2614 REJECTED (2026-09-11)** — bge-m3 domain-cosine deterministic depth tie-breaker is non-discriminative (calibration `scripts/calibrate_depth_tiebreak.py`: max cosine ~0.54-0.58, top1-top2 gap ~0.02 across all 4 depth classes; count-above-threshold accuracy ~20% < random 25%; collapses 145/148 → universal). Depth abstain is honest epistemic uncertainty; the fix is Phase-0 human adjudication, not a deterministic hack. ✅
- **PHASE-0 149-CORE ADJUDICATION FORM + LEDGER BUILT (2026-09-11)** — `scripts/build_phase0_adjudication_form.py` → `governance/phase0_149core_adjudication_form.md` (100 flagged / 49 clean) + `governance/phase0_adjudication_ledger.jsonl` (149 rows, R14-stamped). Deterministic `differs` flag (does NOT trust self-reported `*_verdict`, per BUG-242) + depth N/A for non-principle. This is the D2613 human+DeepSeek-verified core adjudication surface. ✅
- **BUG-242 LOGGED (2026-09-11)** — frontier69_v2 + extension80 audit `*_verdict` fields are LLM self-reports (claim `override` even when values equal silver); non-principle rows carry a spurious 4-way depth label (violates D2612). Fixed deterministically in the form builder. ✅
- **BUG-168 RESOLVED (D2592, 2026-09-08; moved from SHOULD)** — `dspy_trainer.py` wire-or-archive → ARCHIVED; re-open gate deferred to tier-based (D2594), not all-1027. ✅

- **BUG-232 FALSE-CONVERGENCE FIXED (2026-09-09)** — `scripts/fix_false_convergence.py` (Qwen3.8-27B R5-reviewed, APPROVE): re-tiered **96 same-author echoes** (source_diversity≥2 but <2 distinct authors) → `is_convergent=0` + `source_diversity=1` (author-floored) in `maxwell.db` (C13 backup `maxwell.db.bak_20260909_162749_pre_falseconv`; integrity ok). Manifest `governance/false_convergence_fix_manifest.{json,md}` ✅
- **CONTENT-TYPE TIER1 GOLDEN + FRONTIER LABELS (D2596–D2600, 2026-09-08/09)** — 69 frontier-Qwen3.8 objects human-adjudicated 4-axis (58 principle / 6 noise_drop / 2 quarantine / 2 process_template / 1 tool_instruction); DeepSeek-v4-pro cross-check (depth 98.6% / discipline 97.1% / domains 98.6%); ledger `content_type_human_decisions.jsonl` = 97 unique (last-wins, incl. 12 boundary-corpus); P1 `propagate_content_type_decisions.py` → golden YAML + DB; H4 `propagate_frontier_labels.py` → depth/discipline/domains back-propagated to 69 objects (1 non-canonical domain kind-leak dropped) ✅

- **P0 baseline + confusion matrix (D2586)** — `scripts/train_discipline_classifier.py` enhanced (per-class F1 + `confusion_matrix.npy`) + trained: macro-F1 **0.1845** (61/61 trainable; 33 data-starved; nonzero-mean 0.402). Checkpoint in `knowledge pipeline/classifier_modernbert/` ✅ (2026-09-06)
- **P1 LF-dependency audit (D2586)** — `scripts/lf_dependency_audit.py` → `governance/lf_dependency_audit.{json,md}`: T-NLI vs cleanlab **near-independent** (phi=0.093, kappa=0.062) ✅ (2026-09-06)
- **P2 label model (D2586)** — `scripts/build_label_model.py` (Dawid-Skene EM): π=0.785, **135 high-suspicion golden FBs** (challenger/GOLD-A seed) → `governance/label_model_output.{json,md}` + `temp/golden_labels_probabilistic.jsonl` ✅ (2026-09-06)
- **P3 challenger prep (D2586)** — residency fix (unload non-pinned voter) + `--high-suspicion` filter + gemma-4-E4B path validated live; full 135-FB run pending ✅ (2026-09-06)

- **Roundtable vote-model verdict (D2585)** — 3 independent auditors (Claude/ChatGPT/Qwen at pinned commit `436fabc`) + adjudication + 2nd-round peer review (ChatGPT `chatgpt0052`, Qwen `QWEN0052`) → **RETIRE full-corpus 3-model vote**; adopt weak-supervision label model (gpt-oss teacher → {T-NLI + cleanlab + challenger} LFs → Snorkel/Dawid-Skene → GOLD-A/B/C → ModernBERT + calibrate + conformal abstention) with a MANDATORY LF-audit gate. D2582 → SUPERSEDED. 5 handoff factual errors corrected (pinned floor 3.80 GB, k-NN deprecated D2575, D2243 not D2317, run_wall_budget=AGENTS.md D2496, BUG-224≠DELEGATE-002) ✅ (2026-09-06)
- **D2584 data-absent disciplines resolved** — computational theory / ecology / robotics were NOT missing content; they had unresolved domain axes (`domains=["emerging"]` despite real `domains_raw`). Fixed deterministically (19 robotics/autonomous-systems + theoretical-CS aliases → `engineering & infrastructure` / `computational science & physics` + `scripts/resolve_data_absent_domains.py`); **no FB fabrication**. Golden set 1026→1027 ex; 61/61 disciplines trainable (was 58) ✅ (2026-09-06)
- **bug197_kind_swap (D2583 next-step)** — 400 FBs kind-swapped (2 discipline + 35 domain recovered); net discipline=emerging 761→759; DB backed up `maxwell.db.bak_20260906_080236` ✅ (2026-09-06)

- **DEF-BEARING-NLI control (D2571)** — `pipeline/nli_definition_control.py` (500-FB sample): definition-bearing hypothesis is a LABEL-SPECIFIC confound fix, not uniform (anthropology 0.004→0.44, evolutionary biology 0.024→0.41, cognitive science 0.01→0.31; overall mean entail flat 0.27→0.24, pass rate up 0.37→0.42). Per-label rates must be re-derived with definitions, not blanket-switched ✅ (2026-09-05)
- **Cleanlab Confident Learning (D2571)** — `scripts/cleanlab_label_audit.py` (TF-IDF + 5-fold CV-LR): 3424/7026 flagged (48.7%; top behavioral economics 150, philosophy 133). Third instrument wired. CAVEAT: TF-IDF weak — bge-m3 embeddings upgrade = follow-up ✅ (2026-09-05)
- **P1 ontology definition layer (D2570)** — added `definition`+`exclude` to all 104 canonicals (43 domains + 61 disciplines) in `config/taxonomy_v5.yaml`; authored by Qwen3.8-27B (single-shot, temp 0), cross-family verified by gemma-4-E4B (0/25 flagged wrong), applied additively via ruamel round-trip (canonical/group/raw/meta byte-identical; 199/199 tests green). Unblocks the definition-bearing NLI hypothesis control (anomaly C). ✅ (2026-09-05)
- **C12-CHUNK (D2570)** — `pipeline/reclassify_merged_axis.py` `CHUNK_SIZE_DEFAULT=200` hardcode → config `stage4.reclassify_chunk_size=200` + `CONFIG_TO_CODE` registry entry; `config_audit.py --check-unchecked --strict` now clean ✅ (2026-09-05)
- **C16 review_aliases (D2570)** — `scripts/review_aliases.py` `_load_checkpoint` silent `except (json.JSONDecodeError, KeyError, ValueError)` → logs to stderr + continue (matches `nli_label_audit.py` pattern) ✅ (2026-09-05)
- **per_label round-trip test (D2570)** — `tests/test_per_label_threshold_contract.py` (5 tests) guards the 96-entry `per_label` block: canonical keys only, numeric [0,1], 43/43 domains present, YAML round-trip type-safe ✅ (2026-09-05)
- **Forensic audit + integrity (D2570)** — integrity 18/18, config-audit clean, decision-sync 545→546, DB integrity ok / 0 FK / 0 non-canonical / 0 null R14; 199/199 tests green ✅ (2026-09-05)
- **D2569 baseline committed+pushed** — `2c866c3` (14 files + corrected handoff v2) ✅ (2026-09-05)
- **BUG-223 logged (D2570)** — 54 `emerging` FBs store `discipline_raw='[]'` literal-array instead of `''`/NULL (minor hygiene; empty-test must handle `'[]'`) ✅ (2026-09-05)
- **Governance drift sync (D2569)** — removed D2544/D2545 double-listing from DECISION-LOG OPEN section; re-surfaced D2440 into MTR SHOULD #20; flipped D2454/D2483 ACTIVE→RESOLVED ✅ (2026-09-05)
- **BUG-215 residual fix (D2569)** — `scripts/fix_bug215_residual.py --apply`: 66 FBs (discipline≠emerging + empty raw + stale `emerging_real`) → **24 verified alias restore** (Information Systems/Health Informatics → information science) + **42 reverted to emerging** (raw label doesn't resolve to the assigned discipline — `Marketing`→finance, `music education`→psychology, `Applied Mathematics`→theoretical physics, plus an information-science catch-all over-assignment). NET discipline=emerging 927→969; 0 residual; integrity ok, 0 FK ✅ (2026-09-05)
- **P0 #2 NLI full population (D2569)** — `pipeline/nli_label_audit.py` now persists `results` (23,364 full-population records) alongside the flagged contradicts/weak lists → downstream stats are full-population means, not flag-rate proxies ✅ (2026-09-05)
- **P0 #1 contradict/weak split (D2569)** — `scripts/build_mislabel_triage.py` outputs `nli_total`/`nli_contradict`/`nli_weak` (no conflated union); `scripts/populate_semantic_error_thresholds.py` uses `nli_contradict` + made idempotent → **project management 0.9425→0.3914** (true contradiction 245/626, not the 590/626 flag union) ✅ (2026-09-05)

- **Cascade deregistration (D2568)** — `scripts/cascade_deregister_domains.py --apply`: 615 FB domain deregistrations across the 3 SYSTEMATIC catch-all domains (project management 257 / business operations 202 / legal & public policy 156) from the k-NN∩T-NLI flagged set; 75 single-domain FBs → honest "emerging"; counts 879/1756/806 → 622/1554/650. Fixed a double-flag overwrite bug (24 FBs) by unioning all flagged catch-all domains per FB. C13 backup + integrity gate + atomic + recount ✅ (2026-09-04)
- **Alias review + correction (D2568)** — `scripts/review_aliases.py` (Qwen3.8-27B re-reviewed 927 single-value aliases → 76 flags) + DeepSeek-v4-pro cross-family verify → `scripts/apply_alias_corrections.py --apply`: **66 corrections** (49 domain + 17 discipline), 9 kept, 1 no-op. Protected D2567 corpus-dependent fixes (`video production`→motion design, `statistics & data science`→data visualization) ✅ (2026-09-04)
- **BUG-150 promotion (D2568)** — (a) `bug197_kind_swap.py` re-run: 1,235 FBs (56 discipline + 140 domain recovered); (b) `scripts/resolve_emerging_promotion.py`: 54 FBs deterministic (suffix-strip + compound-split, curated exclusion of `graph theory`→data-viz false-positives); (c) LLM promotion 24 FBs (`Information Systems` + `Health Informatics` → `information science` discipline, Qwen3.8×DeepSeek agreement). NET discipline=emerging **1,010→927** (−83), domains∋emerging 716→772 ✅ (2026-09-04)
- **Re-audit (D2568)** — re-ran k-NN + T-NLI after mass reclassification: k-NN mean agreement **41.2%→40.7%** (FLAT — the metric tracks topical diversity, not label accuracy; audited pairs 12,667→14,334 as more FBs gained canonicals); T-NLI contradict rate **21.5%→19.9%** (−1.6pp) + domain mean entail **0.248→0.265** (improved). `build_mislabel_triage.py` → 526 calibration rows + 2,142 triage FBs ✅ (2026-09-04)
- **Per-label thresholds (D2568)** — `scripts/populate_semantic_error_thresholds.py --apply`: 96 per-label NLI-contradiction rates → `taxonomy.semantic_error_rate_max.per_label` (flag-rate proxy; cost-weighting + gate consumer pending) ✅ (2026-09-04)
- **D2544 k-NN audit** — full 7,995-FB run executed (k=10): mean neighbor-label agreement **41.2%**, 6,211 low-agreement pairings (49.03%) → `governance/knn_label_disagreement.json`. First fixed a latent domain-comparison bug (`.split("|")[0]` on JSON column) → JSON-parse + set-intersection (D2557) ✅ (2026-09-04)
- **T-NLI audit** — `pipeline/nli_label_audit.py` created (D2542 target, was never written) + Qwen3.8-27B-reviewed (APPROVE); full run COMPLETE: 20,929 pairings, mean entail 0.332/0.248, **4,497 contradict-label** (21.5%), 8,978 weak (D2558) ✅ (2026-09-04)
- **C16 search_fts** — silent `sqlite3.OperationalError`→LIKE fallback now logs loudly (D2559) ✅ (2026-09-04)
- **DeepSeek API verify** — `custom_deepseek` is LIVE+auth (Keychain `https://api.deepseek.com/v1`; live conn to api.deepseek.com:443), NOT dead; remote-cloud → C1/C3 violation → recommend `maxwell_omlx` (D2560, CORRECTED 2026-09-04) ✅ (2026-09-04)
- **D2547 calibration** — `scripts/build_mislabel_triage.py` → `governance/d2547_calibration.json` (440 per-label entail/agreement stats) (D2561) ✅ (2026-09-04)
- **Mislabel triage queue** — 1,989 FBs flagged by BOTH k-NN (6,211) + T-NLI (4,497), ranked by contra−entail gap → `governance/mislabel_triage.json/.md` (D2561) ✅ (2026-09-04)
- **Forensic audit + fixes** — Qwen3.8-27B + DeepSeek cross-verify: 6 real C6/C12/C16 findings FIXED (knn safe_write+config constants, nli log+fsync, retrieve stopwords→config), 2 false-positives rejected (D2562) ✅ (2026-09-04)
- **Relabel plan built** — human-review marks (64 FBs / 8 labels) → `governance/relabel_plan.json/.md` (PLAN-ONLY): 3 systematic (project management/business operations/legal & public policy), 5 retarget + 40 deregister + 14 keep + 5 unreviewed (D2563) ✅ (2026-09-04)
- **Enrichment plan** — cross-disciplinary retrievability: 11 FBs classified (1 enrich + 4 retarget + 6 deregister); backlog 1,926 immediate-enrich + 3,177 Track-B-emerging → `governance/enrichment_plan.md` (D2564) ✅ (2026-09-04)
- **Phase 1 relabel applied** — 8 human-review FBs (1 enrich + 4 retarget + 3 deregister) via `scripts/apply_relabel_plan.py` (C13 backup + atomic) (D2565) ✅ (2026-09-04)
- **Phase 2a enrichment applied** — 75 safe cross-domain additions via `scripts/apply_enrichment.py` (non-catch-all); mapping gap found: 2,139 unmapped raw labels → ~1,850 FBs still blocked (D2565) ✅ (2026-09-04)
- **Alias extension (D2566)** — `scripts/extend_alias_index.py`: deterministic (self/fold/compound/suffix) + LLM bulk-map (Qwen3.8 generator × gpt-oss verifier, cross-family R5, agreement-only) → **618 domain + 151 discipline aliases** added to `config/alias_map.yaml` (add-only; 201 existing preserved). Wired alias_map.yaml into `pipeline/schemas.py` synonym index (step 3) ✅ (2026-09-04)
- **Phase 2b enrichment re-run (D2566)** — `scripts/apply_enrichment.py` rewritten (full domain index: taxonomy + synonym_map SYNONYMS-only + alias_map + canonical-self + compound split; keywords excluded) → **727 FBs enriched** (vs 75 in Phase 2a) ✅ (2026-09-04)
- **Deterministic emerging resolution (D2566)** — `scripts/resolve_emerging_deterministic.py`: **354 emerging FBs → canonical discipline** (no LLM, kind-safe) ✅ (2026-09-04)
- **Track B slim re-classification (D2567)** — `pipeline/reclassify_merged_axis.py --slim --apply`: 1,488 discipline=emerging FBs → **478 resolved + 981 raw-corrected** (~1.4s/FB); harvested `temp/trackb_slim.jsonl`; checkpoints re-synced ✅ (2026-09-04)
- **Domain-axis emerging resolution (D2567)** — `scripts/resolve_domains_emerging.py --apply`: **846 FBs with domains ∋ emerging → real domains** ✅ (2026-09-04)
- **Alias quality correction (D2567)** — 7 wrong LLM aliases fixed (`video analytics`→data viz, `scientific research`→science & research, …) + 1 reverted; `scripts/correct_wrong_enrichments.py` fixed 19 inherited wrong domains. Net emerging: discipline 1,842→1,010, domains∋emerging 1,562→716 ✅ (2026-09-04)
- **BUG-104** — sqlite-vec unblocked: Homebrew Python (`/opt/homebrew/bin/python3`) → vector leg recall@k **1.000**, hybrid 0.900 (D2556) ✅ (2026-09-04)
- **D2547 config** — `taxonomy.semantic_error_rate_max` (default 0.05, per_axis, per_label) added (D2556) ✅ (2026-09-04)
- **D2548 gate** — `stage4.grammar_decoding_enabled=false` added; Outlines/XGrammar not installed (D2556) ✅ (2026-09-04)
- **Code-review benchmark** — all 4 local models 5/5, 0 hallucination (gemma not inferior; D2556) ✅ (2026-09-04)
- **Qwen3.8 forensic audit** — verdict CONCERNS, 8 legit C12/C20 findings fixed (D2556) ✅ (2026-09-04)
- **BUG-221** — FTS5 OR/prefix tokenization fix (D2554): recall@k **0.000→0.667** verified ✅ (2026-09-04)
- **D2546** — SHACL formalization of 104 canonicals → `config/taxonomy_shacl.ttl` (D2555) ✅ (2026-09-04)
- **MEASURE-DEBERTA follow-up** — S5_NLI char caps 256→1500/500 (D2554); re-measured 0% truncation ✅ (2026-09-04)
- **D2544 script** — k-NN audit script written + smoke-tested (D2555) ✅ (2026-09-04)
- **MEASURE-DEBERTA** — DeBERTa 512-token exposure measured: 0% exceed window (max 498 tokens) ✅ (2026-09-04)
- **GOV-SKILL** — `agent/skills/maxwell-os-SKILL.md` v3.0 regenerated (6/6 dead paths fixed) ✅ (2026-09-04)
- **GOV-TURBO** — `turbovec_backend.py` archived; `mlx_provider.py` KEPT + flagged UNUSED ✅ (2026-09-04)
- **GOV-SQLITE** — `storage/base.py` docstring fixed (false "Default: sqlite_backend.py" removed) ✅ (2026-09-04)
- **GOV-CI** — `.pre-commit-config.yaml` + `scripts/pre_commit_gate.py` (C11+C12) added ✅ (2026-09-04)
- **GOV-VERSION** — `classification_version` v5.0.1→v5.5; filename = major-version marker ✅ (2026-09-04)
- **GOV-SENTINEL** — `sk-maxwell-local` consolidated 6 code copies → `OMLX_API_KEY` ✅ (2026-09-04)
- **GOV-HEADINGS** — DECISION-LOG heading convention codified ✅ (2026-09-04)
- **BUG-098** — `psutil>=6.0` confirmed declared in `requirements.txt` ✅ (2026-09-04)
- **BUG-220** — `delegate()` Qwen breakage standardized on one-shot OMLX curl (D2543/D2549) ✅ (2026-09-04)
- **BUG-220-MCP** — MCP `delegate_local` hardened (model allowlist + caps + path-containment) ✅ (2026-09-04)
- **F-03** — MCP `depth` enum fixed → canonical 4 values ✅ (2026-09-04)
- **MEASURE-DIM** — bge-m3 512-d contract VERIFIED ✅ (2026-09-04)
- **BUG-215** — 1,097 empty `discipline_raw` repaired (Track B + T-311 + kind-swap) ✅ (2026-09-04)
- **T-311** — 311-row deterministic repair ✅ (2026-09-04)
- **T-TRACKB** — Track B reclassification complete: 1,172/1,172 ✅ (2026-09-03)
- **T-TRACKB-RELAUNCH (D2583)** — 661 empty-raw emerging FBs (re-introduced by D2399 demotions) re-classified full mode: **195 resolved + 466 raw-corrected, 0 failed**; net emerging 956→761; 0 empty-raw remaining; harvest `temp/trackb_full_20260905.jsonl` ✅ (2026-09-05)
- **kind-swap re-run** — BUG-197 post-TrackB: 544 FBs ✅ (2026-09-04)
- **FTS rebuild** — `fbs_fts` rebuilt (7,995 rows) ✅ (2026-09-04)
- **BUG-219** — integrity-check #4 FP fixed ✅
- **BUG-216** — 28 FBs `domains_raw` backfilled ✅
- **BUG-217** — `taxonomy_version` unified v5.1→v5.5 ✅
- **BUG-218** — 9 sidecar empty-shells ACCEPTED ✅
- **D2545** — C12 config-first de-hardcoding + CONSTITUTION taxonomy ✅
- **D2399 human review** — both candidates REJECTED + promotions frozen.
- **S2 rerank enable** — ENABLED (`rerank.enabled: true`).
- **S3 HyDE harness** — implemented (`--hyde`).
- **BUG-198** — 6 singleton principles re-injected.
- **BUG-197** — deterministic kind-swap (3,694 FBs; 0 residual axis leaks).
- **Checkpoint drift** — S4 checkpoint re-synced (7,873, 0 drift).
- **Forensic audit** — clean (0 null/empty/leak/invalid).

> Full task history: `archive/governance_pre_tiered_2026-09-03/MASTER-TASK-REGISTER.md` + `…/aggregated_remaining_tasks.md`.

> **⚠️ 2026-09-21 — Phase 3 EXECUTED + bake-off scaffold repointed (exec D-295/D-296).** goose active_provider→maxwell_omlx; custom_deepseek disabled. bakeoff repointed to frozen 150-row ruler (DEFAULT_SHEET=RULER_BLIND_SHEET_20260917.csv, DEFAULT_KEY=anchor1_frozen_20260920.json), AXIS→discipline, load_ground_truth parses rows.
> **KNOWN GAP (arm layer, do not forget):** ruler CSV keys by `item_id` (R001..), `fb_id` lives only in frozen JSON; columns are `DISC (1-62)`/`FORM (1-4)`/`DEFINITION`, not `discipline`/`extraction_type`/`definition`. arm_constant/arm_deberta/arm_qwen3coder need item_id→fb_id join + column-name map before running. arm_constant must also compute modal over HUMAN labels (load_ground_truth), not the sheet column.
> **Phase 4 (KV-cache quant / 70B sizing):** no conflict with ruler sheet or unimplemented Phase 2/3; defer per plan gate (only if accuracy demands).
> **NEXT: (1) user finishes 60-row κ sheet; (2) compute per-axis κ; (3) wire arms + item_id→fb_id join; (4) R5 gemma review of bakeoff; (5) BUG-312 DB→JSONL re-meter; (6) run bakeoff on 150-row ruler.**
> **ANCHOR-1 R2 kappa + bake-off arm layer - 2026-09-21 (D-298, exec D-296/D-297).** discipline kappa 0.4395 (n=59, po=0.4746, error 0.5254); contra 0.4193 / clean 0.4578; domains micro-kappa 0.5765 (contra 0.5953 / clean 0.5477), mean Jaccard 0.4515, exact set 9/60; content_type kappa 0.0 with pipeline_distinct=1 (pipeline predicts ONE class).
> Constant baseline on the frozen ruler (discipline) = error 0.931 / n=116 (F-17 reference bar).
> Repair queue: 55/60 rows disagree on >=1 axis -> governance/anchor1_kappa_20260921.md (per-row human vs
> pipeline with the reviewer rationale note attached). KNOWN ARM-LAYER GAP IS CLOSED (item_id->fb_id join +
> column-name map, config-first; arm_constant scores modal HUMAN label).
> Forensic audit of the changes: 0 leaks (blind sheet + frozen key never written), 0 cascades (bake-off
> writes only its own artifact), 4 findings logged: BUG-314 frozen-CSV hash drift (cosmetic, fails closed),
> BUG-315 hardcoded oMLX key, BUG-316 goose main-model conflict, normalisation-debt note.
> **NEXT (sequential):** (1) ratify D-299; (2) read back the background bake-off (deberta + qwen3coder,
> 150 rows) vs the 0.931 constant bar; (3) BUG-312 DB->JSONL export + re-meter (last R2 provenance gap);
> (4) rebuild the R2 contra meter on the DB snapshot; (5) triage the 55-row repair queue into
> boundary re-derivation candidates (D-285/D-289 style).
> **BAKE-OFF RESULT v1 (2026-09-21, frozen ruler, discipline, n=116 human rows):**
> constant 0.931 error (108/116) · DeBERTa zero-shot menu arm **0.931 - identical**, error-set Jaccard 0.862 => DEGENERATE (F-17 strongest form) · Qwen3-Coder arm abstained 116/116 => INVALID (BUG-319).
> **Root cause of v1's uselessness: role mismatch.** S5 verifies a STORED label pairwise; v1 ranked 61 hypotheses zero-shot. Arm matrix v2 = pairwise verifier + menu labeler + calibration score (see governance/BAKEOFF_PROTOCOL_20260921.md).
> **Open:** BUG-319 (LLM arm parse masking) · arm_qwen3coder must separate "model abstained" from "we failed to parse".
> **Next:** BUG-312 exactness -> repair-queue triage (menu/boundary fixes) -> Gate-0 paper audit for laya-mlx -> v2 arm matrix with the D-300 >=5pp rule.
> **ARM VERDICTS v2 (2026-09-21, frozen ruler 150, discipline, n=116) — D-300 RATIFIED by owner:**
> incumbent (pairwise verifier, production role) **err 0.474** · LLM labeler (qwen3coder, 404 bug fixed) **err 0.526 → REJECT (-5.2 pp)** · error-set Jaccard 0.468-0.482 => **complementary failures => arbitration/ensemble is the live hypothesis, not substitution** · abstention: NLI margin best at 10% (0.423 vs 0.471), tie at 25%, LLM confidence best at 50% (0.259 vs 0.328).
> **Guardrails hardened:** artifact merge-at-write (BUG-323), report warns when the incumbent arm is absent, per-row margins persisted (BUG-321), degenerate-arm + decided<50% guards (BUG-320), reason taxonomy on every LLM decision (BUG-319).
> **Gate-0 PASSED for laya-mlx** (Apache-2.0, pip, MLX-native, **caller-supplied criteria = our 61-label menu passed directly, no projection layer**). Residual: 61-way criteria untested at scale, use the multilingual checkpoint, pin the HF revision + checkpoint licence.
> **NOT DONE (deliberate):** menu repair implementation · abstention operationalisation in the production verifier (stage5, fail-closed routing to the repair queue) · BUG-312 re-scope (the sheet harness is NOT the DB meter) · Phase 1/3 leftovers (recipe temp 0.0, goose main model, omlx pinned_version, MTP, cache preflight) · Phase 4 (gated).
> **ARBITRATION (2026-09-21, D-306):** agreement 39.7% / error on agreed 0.103 / oracle ceiling 0.293 (vs incumbent 0.474). R3 = 0.414 (+6.0 pp, post hoc) and R4 = 0.448 (+2.6 pp): promising, **not adopted** - D-300 requires held-out validation. Next: pre-register R3, validate on held-out labels, and only then consider adoption.

> **SYNC + AUDIT 2026-09-21 (D-307/D-308/D-309, BUG-325)** - menu repair CLOSED: PART1 B normalisation is wired
> and domain-scoped (domains micro-kappa 0.5765 -> 0.5931, mean Jaccard 0.4515 -> 0.4737; discipline unchanged
> 0.4395); PART1 A disproved (zero slots added); all 16 discipline boundary pairs settled DIFFERENT.
> Taxonomy v6.0 audit marker REVERTED to v5.5 (no phantom version; stamp source unified with config).
> BUG-325 fixed: the normalisation map leaked across axes. NEXT: assignment/emission diagnosis (why existing
> slots are never selected), R3 held-out validation, calibrated abstention, BUG-312 DB->JSONL re-meter.
> **CORRECTION (D-310, 2026-09-21):** the 'the pipeline never selects existing slots' reading was a
> sampling artifact of the contra-stratified 60-row ANCHOR-1 sample. Whole-corpus measurement: ALL 61
> discipline + 43 domain slots are emitted (min 6 rows, median 85); 58.7% of the corpus is QUARANTINE.

> **SESSION-6 FORENSIC AUDIT (2026-09-21, D-313) — 4 defects, 2 HIGH.**
> (1) **BUG-328 closed by landing** — the uncommitted production set was coherent and already in force
> in the DB (gate dry-run 0/7,995 writes) but its new modules `pipeline/serving_gate.py` and
> `pipeline/closed_menu.py` were untracked, so a fresh checkout raised ImportError in S4/S5 instead of
> silently reverting. (2) **BUG-329 HIGH** — the frozen ruler has three versions and the HEAD-vs-working
> diff is substantive (41 CT / 7 DISC / 62 FORM label cells); BUG-314's "cosmetic only" is corrected.
> (3) BUG-330 pre-existing stale assertion. (4) BUG-331 the serving-gate DB write has no R5 record.
> **Blocked-by-owner**: ruler version (GATE 4). **R3 is not config-only runnable** — the harness reads
> key['rows'][*]['stored'] while the ANCHOR-1 key is an fb_id dict; a pre-registered adapter is needed.
> Report: governance/FORENSIC_AUDIT_20260921b.md.

<!-- s7-sync 2026-09-21 -->

### Session 7 — 2026-09-21 (R3 held-out run)
- [x] D-312 adapter: `bakeoff.active_source` + `bakeoff.sources.anchor1` + `bakeoff.arbitration` (config-first).
- [x] **R3 held-out run** (57 scored of 58 pre-registered): incumbent 0.5088 | R3 0.5088 (0.00 pp) | R2 0.4286
      at 75.4% queue | R4 0.5965 | constant floor 0.8421. **R3 REJECTED — do not adopt.**
- [x] Truth-blinding leakage test (0 diffs / pairwise abstains) + R5 review recorded (with its insufficiency).
- [x] BUG-328 CLOSED; BUG-332 FIXED; BUG-333/334/335 logged (333, 334 OPEN).
- [ ] BUG-326 repair (403 raw->canonical, 147 both-axes, 703 no-domain): dry-run script + mechanical
      verification required first (R5 is now known-degraded, BUG-333).
- [x] GATE 4 CLOSED 2026-09-21 (D-315, owner-ratified): canonical ruler = `governance/anchor1_frozen_20260920.json`
      (`0ec321a7`). Workspace = the CSV; `2d456720` = superseded draft; `4d0c856a` = byte-lost/label-verified.
      Re-score from the authority reproduces CT 0.3533 / DISC 0.4741 / FORM 0.2828 exactly. Blinding test PASS.
- [ ] GAP F-11 (OPEN, methodological): the ruler declares `second_coder_required_before_repointing: true` and no
      second coder exists -> NO floor may be repointed. Diagnosis is unblocked; floor repointing is NOT.
- [ ] Gates: laya-mlx benchmark-only install; abstention operating point t_low=p25; ratify R3 rejection.
- [x] BUG-326 repair is **BLOCKED, not applied**: the target numbers (403/147/703) do not reproduce on the live
      DB (757 all-`emerging` catch-all labels / 65 mixed-axis / 0 domain-less). Re-scoped in
      `governance/BUG326_REPAIR_SCOPING_20260921.md`; new standing rule BUG-336.
- [x] Session 9 (2026-09-21): D-316 one-answer-key rule; ruler annotation loss FIXED (BUG-340); C15 mechanical (BUG-342, 60 open); BUG-330 FIXED.
- [ ] BUG-341 (OPEN, HIGH): re-run stage5 on the current S4 input (hours) to stop borrowing the Sep-4 snapshot for the R2 meter.
- [ ] BUG-343 (OPEN): capture the smoke subprocess stderr so the failure is diagnosable.


- [x] Session 10 (2026-09-21): D-317 human attestation SIGNED by owner (config-first, hash-cited); owner gates 3 -> 2; BUG-344 (declared pins not enforced) FIXED.
- [ ] BUG-341 (OPEN, HIGH): re-run stage5 on the current S4 input (hours) -- until then the R2 corpus meter borrows the Sep-4 snapshot.
- [ ] BUG-343 (OPEN): capture the smoke subprocess stderr so the failure is diagnosable.
- [ ] F-11 (OPEN, methodological): recruit a SECOND coder on the 150 rows -- until then no floor may be repointed.
- [ ] MENU_REPAIR_WORKSHEET_20260921.md (OWNER, 13 + N rows, A/B): untouched (0 answers) -- blocks the menu repair apply.

- [x] Session 10 (2026-09-21): BUG-344 (pins never enforced) + BUG-345 (pin typo at index 34) FIXED; D-318 RATIFIED; BUG-346 (second scorer) retired; BUG-333 partially fixed; scripts/pin_audit.py added.
- [ ] Wire scripts/pin_audit.py into the pre-flight/CI path so pin drift fails a run automatically (not just on request).

> **SUPERSEDING ENTRY - 2026-09-23 (session 21 / audit (e)).** Live register: governance/aggregated_remaining_tasks.md. State: HEAD 6aae15a green (just health exit 0, 10 controls, 0 RED), pins 6/0 RED, decision registry 724 entries with its derived summary now recomputed and its drift detector (scripts/recompute_decision_summary.py --check) wired into just health as control 11 (BUG-399). D-355 minted (a control must assert the state it is in) with the && corollary; D-356 minted (the R2 meter speaks extraction_type - capability, ratified curve still owed, BUG-398); D-357 minted (the vec integrity contract is per table, a dormant store must be EMPTY). BUG-395 FIXED and wired; BUG-388 FIXED code-side; BUG-390 capability CLOSED. OPEN OWNER GATES: (1) the vec repair against the run DB (BUG-394) - the recipe is now a proven script, dry-run by default (scripts/repair_vec_integrity.py); (2) the coverage SLA number, the one gate before the adopted 25% discipline abstention point can be flipped after one shadow run; (3) the parquet export re-run (BUG-388); (4) the v6 menu merge adopt/drop; (5) the R3 held-out go/defer; (6) the physical disk chore (29 GiB free). Strategy unchanged: abstention is a risk control worth ~5 pp - the real lever is upstream (labeler/reference quality, D-343 routing, the measured merge).

> **SUPERSEDING ENTRY - 2026-09-23 (session 22 / audit f).** HEAD d2a7faa green; registry 725 -> 727 (D-359 PROPOSED, D-360 RESOLVED). EXECUTED: the owed R2 artifact now EXISTS over the frozen ruler (governance/R2_EXTRACTION_TYPE_RULER_20260923.json; 150 FBs, 728 scores, 135 contra, 0 errors, extraction_type 150/150, menu_hash d2fc500c - NOT comparable with the corpus artifact's 73597ee2, D-360); BUG-387 fixed code-side (D-359: rowid-preserving commit + rowid-level assertion, tests/test_vec_rowid_contract.py 5/5 PASS); BUG-397(a) repointed to the archived golden. OWED: the extraction_type curve (a gate measurement over the new artifact) before any operating point on that axis; the R5 review + scratch rehearsal for D-359; BUG-397(b) two-site dspy fix. OPEN OWNER GATES unchanged: (1) the vec repair against the run DB; (2) the coverage SLA number; (3) the parquet re-run (BUG-388); (4) the v6 menu merge adopt/drop; (5) R3 held-out go/defer; (6) the disk chore.

> **SUPERSEDING ENTRY - 2026-09-23 (session 23).** HEAD c2cb33d green at entry; registry 727 -> 731; the 6 open owner gates
> became 5. EXECUTED THIS SESSION (owner-authorized): (1) D-354 VEC REPAIR - 15990 dead vec rows deleted, fbs untouched, 0 RED,
> gate now CHAINED into just health (D-361) with fail-loud on an absent DB; (2) coverage_sla = 0.75 recorded (D-362) - the
> smallest withholding whose bootstrap lower bound is above zero; the discipline lever stays legal, the shadow run is the last item;
> (3) BUG-388 re-run done - fbs_snapshot_20260923_164926.parquet (42.4 MB, 7995 FBs) plus a recorded caveat that the export
> sources the S5 checkpoint, not a dump of the store; (4) BUG-397(b) two-site fix (D-364) plus the dangling citation reconciled;
> (5) v6 menu merge DROPPED and R3 held-out DEFERRED (D-363). EVIDENCE: the pin control fired on the SLA edit and was honoured
> (mint D-362 + re-pin), not bypassed. STILL OWNER-GATED: the disk chore (16.5 GB movable, do not move archive/golden_retired_D2618);
> the abstention shadow run (mine, no gate, now the last step before a flip). STILL OWED BY ME: the D-359 R5 review + scratch
> re-commit rehearsal before D-359 leaves PROPOSED.

> **SESSION 23 CORRECTION - 2026-09-23 (audit).** The disk-chore owner gate as written could not execute and is
> herewith SUPERSEDED. The owner ran it and it failed on the placeholder (`<EXTERNAL>`) - and, decisively, **no
> external volume is mounted on this machine** (`/Volumes` = Data, Macintosh HD, Recovery only; `df` shows two APFS
> volumes on `/dev/disk3`: 926Gi, 874Gi used, 28Gi free, 97%). Nothing moved: `archive/bak_sweep_20260923` is 11G
> and `archive/session_20260923/scratch` is 5.3G, both intact, tree clean at b6f0bd1.
>
> **THE REAL NUMBERS (measured, session 23).** The project is **30G of 874G**. The debt is elsewhere:
> `~/.cache/huggingface` 127G, `~/.omlx/cache` 92G, `~/Library/CloudStorage/Dropbox` 296G (the repo is inside it),
> `~/models` 27G, `~/.mtplx/models` 21G, `~/Library/Application Support/Zed` 14G, `~/.ollama` 13G,
> `~/Downloads` 10G, `~/Documents` 7.6G, `~/.cache/uv` 6.4G, `~/Databases` 5.3G, `/Applications` 58G,
> `/Library` 27G. No local Time Machine snapshots exist, so none of it is purgeable. Model stores+caches
> (`huggingface` + `omlx` + `mtplx` + `ollama`) total ~279G and are the only lever with a meaningful size.
>
> **NEW OWNER GATE (replaces the old one): BUG-400 - the repo is a Dropbox File Provider domain.** `com.dropbox.attrs`
> is on `CONSTITUTION.md`, `config/decisions.yaml`, `pipeline/stage6_commit.py` and `knowledge pipeline/maxwell.db`;
> 794 dropbox attribute lines in a 400-file sample; two Dropbox conflict copies already exist under
> `knowledge pipeline/stage1_5_embed_cluster/`. The sovereign store is cloud-replicated with no decision authorising
> it (C3/C22) and a live SQLite file under a sync client can be restored stale elsewhere. Fix = exclude the folder
> from Dropbox sync, or move the repo out of `~/Library/CloudStorage`.
>
> **STILL OWED (mine, no gate):** the R5 bounded re-review of D-364 and D-359 (the first attempt returned NO VERDICT,
> recorded in the buglog as owed); the D-359 scratch re-commit rehearsal; the abstention shadow run (the last
> activation item); the extraction_type curve (`--config` argument for `scripts/r2_gate_measure.py`).

---

## 2026-09-26R - regulatory: the rails' own gate was the thing blocking the landing

- **BUG-547 (HIGH, FIXED)**: rail 0 was saturated by its own archive - 30 of 36 owner-owed rows were conflict
  copies already filed into the DECLARED archive, so the exit-2 commit gate had no dynamic range left to signal a
  NEW divergence. Root cause: D-2647 taught the RESOLVER the fixed-point rule and never the RAIL (one rule, two
  consumers). Fixed; controls 9 -> 10, two-sided.
- **6 Dropbox siblings VAULTED**, nothing deleted, sha256 + manifest; 1 of them is a measured Dropbox REVERT of
  pipeline state that the owner must re-derive.
- **WIDENED `may_touch` by 5 named paths** so the record-keeping surface every session must write is inside the
  contract, instead of being recorded as OWED session after session. Commit the plan FIRST.
- **OWED**: the three-commit landing; the `DECISION-LOG.md` narratives D-2650..D-2656; the owner's ruling on the
  depth/domain contract (3 red tests are a PAID red on an owner gate, not a defect).

## 2026-09-26S - regulatory: the plan's own record was the last thing that could lie (BUG-548)

- **BUG-548 (HIGH, FIXED)**: `widening_log` recorded 15 widenings and FOUR were never granted by `may_touch`.
  Nothing read the log, so it was a record with no consumer. FIXED at the class: the rail now CHECKS every
  `widened:` / `additions[*].pattern` against `may_touch` (5 new controls, 2 anti-overreach), the four paths are
  GRANTED as NAMED paths (entry 16), the `scripts/*.sh` glob is WITHDRAWN for the exact path, and the two
  owner-acked `pipeline/**` crossings are declared `crossing: true`.
- **D-2657 (OPEN, minted)**: a widening_log entry is not a permission until it is IN `may_touch`.
- **OWED (mine)**: tighten the `fnmatch` matcher (SUB-FINDING above) as its own decision, AFTER measuring which
  live paths it would forbid; **R2 pin re-mint** (sha AND decision together, D-382/BUG-535) - the pin still names
  `e9070635...` while the worktree holds `fbfd62f3...`, so it describes a file that does not exist.


## 2026-09-26S - a register that points at code no longer points at COORDINATES (BUG-542 class fix)
- **BUG-542 FIXED (class, third occurrence)**: rail 0's repair site was declared as `lines: [280]`; the site moved to 306 → the register reported ONE site twice (STALE 280 + DRIFT 306) and the FATAL DRIFT **aborted `just health` at line 51**, hiding ~20 rails below it. Keyed by CONTENT now (`match:`); 24/24 controls, 0 DRIFT, 0 STALE, exit 2 (declared debt only).
- **D-2658 minted, state OPEN** (owner ratify): a declared site is keyed by content, never by a coordinate.
- **OWED (mine)**: R2 pin re-mint (meter + pin + new decision in ONE commit); the rails' own bodies into git (BUG-545 - the gate still executes uncommitted code); the `fnmatch` tightening decision (BUG-548 sub-finding).
- **OWED (owner)**: the depth/domain contract ruling (A ratify+S4 re-derivation / B withdraw) - the only remaining red that a shrink-only ceiling may not clear.

---

## 2026-09-26T - the registry's THIRD unjoined field (BUG-554 / D-2662)

- **BUG-554 (MED, FIXED)**: parity_rail was read by NO machine - a row could cite a script that exists nowhere, or
  one the ladder never runs, and just health printed ok. Now: EXISTS + the declared ladder INVOKES it + a homed row
  may not leave it null (two fields of one record, the BUG-550 class). Controls 23 -> 32; 4 negatives fired on live
  bytes. Cascade checked BEFORE the edit: silent-repair 17/17 (the new reader returns a STATE, never repairs) and
  config-defaults rc=0.
- **D-2662 minted, state OPEN** (owner ratify).
- **OWED (mine)**: R2 pin re-mint (the meter + the pin + a NEW decision id in ONE commit; scripts/definition_nli_verify.py
  is edited in the worktree and OWNER-OWED under BUG-536); BUG-537 archive/.DS_Store control; freeze_gold_sets.py
  through write_guard; the fnmatch tightening decision after measuring.
- **OWED (owner)**: the depth/domain contract ruling (A ratify + S4 re-derivation / B withdraw) - the only red a
  shrink-only ceiling may not clear; the ANCHOR-4 depth drop-in rev 3; data/maxwell.db disposition.

---

## 2026-09-26T - the R2 pin re-mint, done by measurement (BUG-555 / D-2663)

- **The pin debt is CLOSED, not laundered.** `scripts/definition_nli_verify.py` -> sha256 e2ced5fa... and
  `r2_meter.decision` moved e9070635/D-382 -> e2ced5fa/D-2663 in the SAME commit; the scan is now
  `6 pinned, 0 DRIFT, 0 OWNER-OWED` (rc=0). D-382's digest named a version that existed nowhere.
- **BUG-555 (MED, FIXED)**: the provenance field asked a SUBSTRING question (`"coder" in <whole file text>`) and
  answered true on 400/400 live records where 0 records declare a coder - the BUG-528 class inside the BUG-450
  block. Now a membership test on the parsed rows, `coder_key_present` = present on EVERY scored row, counts
  reported, third 102 MB read gone, `_read_input_text` deleted (C19). Controls 0 -> 4 (`--selftest`, no NLI).
- **CERTIFIED BY MEASUREMENT, not by prose** (this is the lesson of D-382): same frozen probe under HEAD bytes
  ca91c520... and final bytes -> results sha a4c9a1d6f37433a1 BOTH, counts 231/21/0 BOTH, delta = `provenance` only.
- **OWED (mine)**: the scored-axis list is restated in prose inside the provenance block
  (`label_source.column`) while `run()` builds it in code - two homes for one fact (D-2646); folding it into one
  constant would touch the scoring path, so it is deliberately OUT of this measurement, not forgotten.
- **OWED (owner)**: unchanged - the depth/domain contract ruling (A ratify + S4 re-derivation / B withdraw), the
  ANCHOR-4 depth drop-in rev 3, data/maxwell.db disposition.

## 2026-09-26T - the archive index reports its exclusions, and the rail stops reading its own ladder's side effects (BUG-537 corrected / BUG-556 / D-2664)

- **BUG-537 FIXED, and its own record CORRECTED.** The block blamed the remedy run; the pre-image it named
  (`/tmp/index_yaml_pre.yaml`, body `ecfe29517a941e1b...`) proves the index had ALREADY de-listed `.DS_Store` before it,
  and the committed HEAD index (`07e8e3559727bc99...`, 2026-09-24T10:40:37) still carried it - so the de-listing is the
  BUG-469 ignore landing. The block's "25 insertions / 26 deletions" was computed against the commit, not the
  pre-image it named.
- **BUG-556 (HIGH, FIXED), found by chasing that field**: the rail's input moves when the ladder opens
  `archive/db_backups/*.db`. A/B: `files 3 / 135528448 B / 2026-09-19` counted vs `files 1 / 135495680 B /
  2026-09-17` declared excluded. Class: BUG-469, incompletely fixed.
- **Controls 0 -> 7** (`--selftest`, no NLI, no live-tree write): silent de-listing, absent bytes, shadowed rule,
  live-config shadow census, transient sidecar, fail-closed claim, clean case.
- **OWED (mine)**: any rail that OPENS `archive/db_backups/*.db` still moves bytes (`-shm` regrows). Harmless now
  (the class is declared and reported), but such a rail should be DECLARED as doing so - the RAIL REGISTRY's job.
- **OWED (owner)**: unchanged - the depth/domain contract ruling (A ratify + S4 re-derivation / B withdraw), the
  ANCHOR-4 depth drop-in rev 3, `data/maxwell.db` disposition.

## D-2666 (RATIFY) - DONE 2026-09-26: the ruler is active, the workbook is the certified generation, and the ladder is GREEN

- DONE: `config/depth_domain_contract.yaml` status proposed -> active + owner_gate block (owner ruling RATIFY, 2026-09-26).
- DONE (BUG-558): foreign body preserved (R-D410) -> backups/*.PRE_CLAUDER_RESTORE_20260926T202715Z; certified bytes restored from `git show HEAD:` (C6 atomic) -> f2778a488610cbf1; owner rulings re-applied through the sanctioned applier -> live 972def3224a1abba; pre-ruling image declared as a revision locator AND sealed (f2778a...bin) so it re-derives from git:44c249b on every run.
- DONE: the encoding declaration corrected in ALL THREE homes (config/reconciliation.yaml) - `mac_roman` there had been measured off the foreign body. The D-2649 two-homes join fired on this disagreement in production before the fix: the control is PROVEN, not presumed.
- DONE: honest receipt via `scripts/lib/handoff.py --backfill` (origin=backfill claims what the bytes ARE now, by design) -> verify_handoffs rc=0.
- DONE: suite ceiling 3 -> 0 in config/test_isolation.yaml, with the reason replaced by the measured truth (the 3 ids were red ONLY because the ruler was unratified; they now pass). SHRINK-ONLY, at floor.
- MEASURED: `just health` rc=0; `just health-deep --strict` rc=0; 261 collected / 256 passed / 0 failed / 0 declared red / 5 skipped.
- OWED (mine, next): BUG-559 - refuse a receipt whose bytes join to no revision, with a control SEEN to refuse one; then re-cut the workbook receipt against the committed revision.
- OWED (mine, next): BUG-560 - route scripts/apply_workbook_rulings.py through write_guard (owned_keys = the ruled columns) so the one writer that defends the owner's rulings is receipted.
- OWED (mine): the truncated prose digest in governance/ANCHOR_ADJUDICATION_NORMALIZATION_20260925.md (`f2778a488610cbf1...`) is a claim no reader can join; the full digest now resolves as a revision locator, so the prose can be pointed at it without rewriting a protected record.
- RULED (owner, one word: KEEP, 2026-09-26 - 6th owner gate answered): the two foreign-body copies
  (backups/anchor_adjudication_workbook_20260924.csv.PRE_CLAUDER_RESTORE_20260926T202715Z + its fixlog sibling)
  are KEPT - the only surviving bytes of the body a receipt once certified (574aafef64f0cff7, BUG-559), so PURGE
  would delete the specimen and leave the rule with nothing to re-derive against. Nothing deleted (R-D410).
- OWED (mine): HEAD reconciliation with receipts (the certified tree and the reviewed tree are NOT the same bytes while 42 tracked files sit uncommitted).

- **D-2667 (2026-09-26) - plan revision + the PAIRING rule.** DONE: session plan restored from git and re-written escape-free (entries 21/22; may_touch widened by TWO NAMED paths, never a glob); the protected-family rewrite reverted after preservation (BUG-561); commit 1 (plan) landed. OWED: (a) the reconciliation commit - BLOCKED by BUG-562 (config/serving_gate.yaml granted vs pipeline/serving_gate.py will_not_touch) -> owner pipeline/** crossing ack or per-path pairing split; (b) the mint of D-2667; (c) BUG-561 DEEPER: the tracked sync-client rename of the owner blind sheet must be REMOVED from the repo (plan revision + owner gate); (d) BUG-559 / BUG-560 remain OPEN; (e) MUTATION_JOURNAL.jsonl (100 KB) and INSTRUMENT_CONTROLS.jsonl are UNTRACKED and NOT granted - the receipt ledger is unversioned.

- **D-2668 (2026-09-26) - the CROSS permit + the reconciliation.** DONE: `crossing: true` is now a PERMIT the rail
  consumes (subject + ack + spend; controls 14 -> 20, `--selftest` 20/20). DONE: plan entry 23 (8 NAMED
  `pipeline/**` subjects, acked by owner 2026-09-26, SPENT by e3f94f4). DONE: the reconciliation - 62 paths landed,
  HEAD now names the tree every rail measured (before: 163 dirty entries and a `git checkout` of HEAD would have
  deleted passed work). DONE: BUG-561 CORRECTED (the "clobber" was the declared rev 3; the REVERT orphaned a
  write-locked digest and was restored from the R-D410 backup - rev 3 exists in NO git ref). DONE: BUG-562's
  INCIDENT (config/serving_gate.yaml + pipeline/serving_gate.py + tests/test_serving_gate.py in ONE commit).
  OWED: (a) the BUG-562 PAIRING RAIL - nothing yet REFUSES a commit set whose granted artifact's consumer is
  withheld; the property now holds only because a session looked; (b) BUG-563 - `backups/**` is neither GRANTED nor
  IGNORED (92 dirty entries) and the rail output stores are in the same class (the R-D410 receipt ledger
  `governance/MUTATION_JOURNAL.jsonl` is unversioned); (c) the owner drop-in rev 3 remains owner-gated (BUG-493) and
  its bytes exist in exactly one non-worktree copy; (d) the D-2667 + D-2668 mints; (e) BUG-559 then BUG-560.
  RISK: committing 8 `pipeline/**` files was the owner-acked crossing, and the reconciliation is what makes
  declarations and implementations land together - the pairing rail is what makes that a property instead of an act.

### D-2669 DONE / OWED (2026-09-26)

DONE. (1) BUG-562 CLOSED BY CONSTRUCTION: check_declaration_consumers.py --staged refuses a commit set that withholds
a declared declaration's consumer (11 controls, incl. the exact incident shape). (2) config/declaration_consumers.yaml
= the ONE home (4 edges). (3) RAIL 5 installed from scripts/install_git_hooks.sh and declared in
config/rail_registry.yaml#commit_boundary, with check_rail_registry.py verifying the hook's TEXT (BUG-564).
OWED. (a) the hook ROUTE is not yet a declared subject (a re-created git dir or a hand-installed hook is invisible);
(b) BUG-559 then BUG-560; (c) BUG-563; (d) the D-2667 + D-2668 + D-2669 mints; (e) rev-3 promotion (owner word).
RISK NOTE. PROMOTE is the highest future-tax item: HEAD carries the SUPERSEDED rev 2 of a write-locked instrument
while the declared rev 3 is re-derivable from no git ref; its only other copy is a byte-exact (203963 B) blob under
governance/handoffs/blobs/, which is covered by a .bin ignore rule - so a worktree clean destroys BOTH copies.

### D-2670 DONE / OWED (2026-09-26)
DONE: BUG-559's owed fix is LANDED as the `provenance` check class in `scripts/verify_handoffs.py` (four joins: head/prefix/revision/declared; a same-length live copy, a foreign body and a digestless receipt are each SEEN refused) with its ONE declaration home `config/handoffs.yaml#receipt_provenance` (rule + `unrevisioned_declared` + SHRINK-ONLY census `max_unrevisioned: 2`) and its consumer edge registered in `config/declaration_consumers.yaml` (D-2669). MEASURED: selftest rc=0; live rc=2 naming exactly ONE object - the owner drop-in at 526991cb (203963 B); stale escape rc=1; census 3 rc=1; consumers 11/11; rail registry 9/9; repo integrity rc=0.
OWED (mine, next in order):
  (a) **BUG-559's live line: the PROMOTE** - land rev 3 (526991cb, 203963 B) as the tracked revision and declare its `revision_locator`, which turns the rail's single owner-owed finding into `head` and closes BUG-493; the rail is now the gate that proves it landed.
  (b) a receipt over an EARLIER COMMITTED revision still reads unrevisioned (remedy = a declared revision locator); no live subject today - measured, not assumed.
  (c) BUG-560 (`apply_workbook_rulings.py` outside write_guard), BUG-563 (backups/** + rail output stores neither granted nor declared excluded), BUG-564 remainder (the hook ROUTE as a declared subject).
  (d) MINT D-2667, D-2668, D-2669 AND D-2670 into `config/decisions.yaml` (D-2670 is written in DECISION-LOG.md only).
RISK NOTE: the highest future-tax item is unchanged - PROMOTE (a write-locked owner instrument whose only other copy is a gitignored `*.bin` blob).

### D-2671 DONE / OWED (2026-09-26)
DONE: the owner's one word 'Promote' LANDED rev 3 (526991cb, 203963 B) of the write-locked drop-in as the TRACKED
revision of its own path, through a ONE-OFF owner-acked crossing permit (widening_log entry 24) that is SPENT by the
commit - NOT through a may_touch widening (rail 4 matches by FAMILY, BUG-528). Staged bytes MEASURED == 526991cb
(no eol/filter normalisation: i/crlf w/crlf, no .gitattributes rule). The rail flipped from rc=2 owner-owed on
exactly ONE object to 'provenance: anchor4_depth_sheet_owner_dropin -> head', rc=0 - BUG-493 closed and BUG-559's
live line cleared. Labels that still described rev 2 (config/handoffs.yaml, config/human_instrument_locks.yaml) are
corrected in the same commit, and the unconsumed second home config/anchor4_depth_annex.yaml is reduced to a POINTER
(D-2646). ALSO DONE: the 6th owner gate is ANSWERED - KEEP the two foreign-body backups (recorded in the buglog).
OWED (mine, next in order):
  (a) BUG-431's CONTENT promotion - merge the owner's complete 150/150 pass INTO the tracked ANCHOR4 sheet and retire
      config/anchor4_interim_state.json; still an OWNER GATE (it writes an owner instrument and deletes a declared home).
  (b) BUG-560 (apply_workbook_rulings.py outside write_guard), BUG-563 (backups/** + rail output stores declared),
      BUG-564 remainder (the hook ROUTE as a declared subject).
  (c) MINT D-2667, D-2668, D-2669, D-2670 AND D-2671 into config/decisions.yaml.
  (d) a receipt over an EARLIER COMMITTED revision still reads unrevisioned (remedy = a declared revision locator).
RISK NOTE: the highest future-tax item is now CLOSED - before this commit a worktree clean destroyed BOTH copies of a
write-locked owner instrument (HEAD carried rev 2; rev 3 lived only in the tree and in a gitignored *.bin blob).

### D-2671 / D-2672 DONE / OWED (2026-09-26)
DONE (8a84622): **BUG-565 FIXED** - a git name-list read is NUL-separated; one home
(`scripts/lib/git_subject.py#run_git_paths`), rail 4 consumes it, three controls over a REAL synthetic index are
SEEN red pre-fix, and RAIL 4's `--selftest` is wired into `just health`. MEASURED: 23/23 controls.
DONE (fe239df): **THE PROMOTE - owner word 'Promote'.** rev 3 (526991cb, 203963 B) is the TRACKED revision of
`governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv`, landed through the owner-acked ONE-OFF crossing
permit (session_plan widening_log entry 24), SPENT in this same commit-set. MEASURED AFTER:
`provenance: anchor4_depth_sheet_owner_dropin -> head`, `verify_handoffs` rc=0 (was rc=2). **BUG-493 CLOSED.**
OWED: (1) **BUG-566** - rail 4 refuses git's OWN next-index at a partial commit while rail 5 tolerates it: a
declared tolerance in `config/repo_integrity.yaml#git_subject` + two controls; (2) BUG-565 remainder (rail 3's
`_staged_paths`, git_subject's differential control); (3) **BUG-431's CONTENT promotion** - OWNER GATE; (4) mints
D-2671/D-2672; (5) BUG-560 -> BUG-563 -> BUG-564 remainder.
RISK NOTE (now retired): before fe239df a worktree clean destroyed BOTH copies of a write-locked owner instrument.

## 2026-09-27 - D-2667..D-2674 MINTED; the mint refused a TRUE citation (BUG-571); ONE word received (RATIFY)

- [x] DONE: the registry lag is repaired - D-2667, D-2668, D-2669, D-2670, D-2671, D-2672, D-2673, D-2674 minted in
      ascending order (797 -> 805 records, stamp ec8f32ea8a61c80d, census carried in the same invocation). `just health`
      rc=0; it had been RED at reconcile's D-405 join ('citations that do not resolve: config/repo_integrity.yaml:decided=D-2673
      / D-2674').
- [x] DONE (owner gate): RATIFY received -> D-2674 puts the repo-integrity git-subject guard set IN FORCE (it carried
      decided: PENDING-OWNER) and names rails 3/4/5 as consumers of ONE home, with RAIL 0 exempt so the recovery rail still
      runs on a broken repository (BUG-568 filed, not papered over).
- [x] DONE: BUG-493 is now VISIBLE to the register (an appended heading; it had existed only as inline prose, so the mint
      gate REFUSED D-2671's true citation). Class filed as BUG-571.
- [x] DONE: BUG-570's status is truthful again (REOPENED event) after measuring that the parser lets a status word in a
      heading's TITLE decide the status: tightening the rule flips 10 of 397 events, 2 corrections and 8 regressions ->
      REFUSED on measurement, filed as BUG-572.
- [ ] NEXT (mine): BUG-560 - route scripts/apply_workbook_rulings.py through scripts/lib/write_guard.py (owned_keys = the
      ruled columns) with a control REFUSING an out-of-scope column.
- [ ] NEXT (mine): BUG-571 - the cited-by-decision join in scripts/bug_status.py (owner-owed, not silent).
- [ ] NEXT (mine): BUG-568 - a git-subject pin for RAIL 0 DERIVED from the same home, tolerant of an already-broken repo.
- [ ] OWNER GATE (unchanged): BUG-431 CONTENT promotion (merge the 150/150 pass into the tracked sheet, retire
      config/anchor4_interim_state.json).
- [ ] OWED (housekeeping): the two foreign-body backups are KEPT by owner word; hooks ACTIVE; `just health-deep` stays
      honestly RED until the owner rules on the depth/domain contract.

## D-2677 / BUG-576 LANDED (2026-09-27)

- [x] BUG-576 FIXED: RAIL 0 reads HEAD as BORN / UNBORN / BROKEN from three DECLARED probes (config/repo_integrity.yaml,
      validated fail-closed incl. the D-405 join) - an UNBORN HEAD is now INTACT, so a FRESH or RECOVERED repository
      can make its first commit. Four new controls build REAL repositories: unborn_head_is_accepted,
      unborn_branch_does_not_swallow_born, head_that_is_neither_is_broken, renamed_reflog_in_a_born_repo_still_fails
      (the counterweight). --selftest 15/15, --check rc=0.
- [x] D-2677 THE BYPASS RULE: a fixture bypass carries a MEASURED justification, never a debt. The --no-verify
      bootstrap is WITHDRAWN and replaced by a declared `refusal` (bootstrap.whole_tree_refused, RAIL 4, rc 1,
      marker FORBIDDEN session plan) that is re-measured on EVERY run; declared_debt is empty and the paid-debt
      OWNER-OWED lifecycle stays SEEN via a synthetic declaration. The rehearsal's fresh first commit is now an
      ACCEPTANCE control. --selftest 18/18.
- [x] Standing-rule gate (D-2676) covers RAIL 0: mutation unborn_head_branch_is_load_bearing, min_mutations 4,
      3/3 declared subjects covered, --check rc=0 (3 rules SEEN to red, 1 negative control green).
- [ ] NEXT (mine): BUG-578 - the rehearsal rehearses HEAD, so it cannot gate the change that LANDS; overlay the
      WORKING TREE bytes of the declared subjects before installing the hooks (measured: install_git_hooks --check rc=0).
- [ ] NEXT (mine): BUG-577 - ONE home for outside_tree (scripts/lib/fixture.py) + a refusal control + a mutation.
- [ ] NEXT (mine): BUG-575 supersession completeness (24 pinned legacy_debt_ids); BUG-573 the ladder must collect
      EVERY fault; BUG-571 the cited-by-decision join (BUG-492 cited 32x, unregistered, is its first live case).
- [ ] OWNER GATE (unchanged): BUG-431 CONTENT promotion; `just health-deep` stays honestly RED until the owner
      rules on the depth/domain contract; hooks ACTIVE.

## D-2678 / BUG-578 + BUG-579 LANDED (2026-09-27)

- [x] BUG-578 FIXED: the rehearsal holds the LANDING bytes (declared overlay, 436 file(s) overlaid; `setup.overlay`
      is a required premise; an inert overlay fails closed, D-405). SEEN: 21/21 controls, gate 4/4 rules red.
- [x] BUG-579 FIXED (found by the audit): a crash in the fixture builder is now a FATAL verdict, not a traceback.
- [x] D-2678 THE LANDING-BYTES RULE minted; the standing-rule join now reads the gate's ONE home for subjects.
- [ ] NEXT: extend coverage.required_subjects to EVERY write-boundary rail (RAIL 0 done, RAIL 3/4/5 owed).
- [ ] NEXT: BUG-577 (ONE home for outside_tree in scripts/lib + a refusal control + a mutation), then BUG-575,
      BUG-573, BUG-571; TASK: declare homes for the 3 dirty rail outputs + backups/** (BUG-563).
- [ ] OWNER GATE: CONSTITUTION promotion of the standing rule stays HOLD at the registered graduation bar;
      BUG-431 CONTENT promotion remains the one open owner gate.

## D-2679 / BUG-580 + BUG-581 LANDED (2026-09-27)

- [x] BUG-580 FIXED: the standing rule's coverage is DERIVED from `config/rail_registry.yaml#commit_boundary` (declared
      in `coverage.boundary_join`), joined in `scripts/check_rail_mutations.py#boundary_rails`, and REFUSES a
      commit-boundary rail that is not covered. RAIL 3 and RAIL 5 got the mutations that prove their rules are read
      (BUG-535 laundering re-pin; BUG-562 withdrawn consumer); the gate got one for its own rule. `min_mutations` 5 -> 8.
- [x] BUG-581 FIXED: the rail-registry rationale under the `config/handoffs.yaml` edge moved back to its own subject.
- [x] D-2679 THE DERIVED-COVERAGE RULE minted (810 records, stamp b6e80486982b3b52).
- [x] GRADUATION BAR (i) every commit-boundary rail covered - MET, by DERIVATION; (ii) >=3 rules landed under the
      standing rule with a SEEN mutation - MET (7 entries); (iii) the gate caught >=1 real declaration defect - MET (it
      caught its own single-quoted-escape no-op, the marker-printed-on-both-verdicts entry, and BUG-580).
- [ ] NEXT: BUG-577 (ONE home `scripts/lib/fixture.py#outside_tree`, imported by both fixture rails, plus a refusal
      control and a mutation) - it is the same fixture family D-2678/D-2679 just hardened.
- [ ] NEXT: BUG-575 (supersession completeness, 24 pinned `legacy_debt_ids`) -> BUG-573 (the ladder must collect EVERY
      fault) -> BUG-571 (the cited-by-decision join; BUG-492 is its live case).
- [ ] NEXT (product): the 3 dirty rail outputs + `backups/**` need a declared home (BUG-563); BUG-560 write_guard route.
- [ ] OWNER GATE: the standing-rule promotion ruling is now DUE (bar met; a promotion must be a POINTER, never a
      restatement); BUG-431 CONTENT promotion remains the other open owner gate.

## D-2680 / BUG-573 FIXED - THE WHOLE-SET RULE (2026-09-27)

- [x] BUG-573 FIXED: scripts/run_ladder.py (the collector) + `just health-full`; the ladder's fast path now
      DECLARES its own prefix in the ladder's own units, before any rail can abort it.
- [x] MEASURED: `just health-full` -> 87 line(s) RUN, 0 fault(s), 203.0s, SCAN_RC=0. The remaining fault set at
      HEAD is EMPTY - the first time that claim is measured rather than assumed.
- [x] Standing rule satisfied for the new rule: (i) ONE home config/rail_registry.yaml#ladder + #recipes;
      (ii) a SEEN control (--banner printed by the ladder itself, run in every `just health`); (iii) the NAMED
      oracle scripts/run_ladder.py --selftest; (iv) the MUTATION ladder_scan_reports_every_fault_is_load_bearing
      SEEN to red (floor 8 -> 9, subjects 6 -> 7).
- [x] NO new bug filed by this change (BUG-573 closed, OPEN 138 -> 137).
- [ ] NEXT (meta, in order - the freeze target): BUG-577 (ONE home scripts/lib/fixture.py#outside_tree), then
      BUG-575 (supersession completeness: 24 pinned legacy_debt_ids), then BUG-571 (the cited-by-decision join;
      BUG-492 cited 32x is its live case).
- [ ] META-LANE FREEZE (recommended, needs one owner word): from D-2680 forward, the governance machinery is
      touched ONLY to close a bug already registered - a NEW governance bug may be filed but NOT worked until the
      three named bugs above are closed and the product lane has produced a build artifact. Rationale MEASURED:
      ~37 of the last 40 filed bugs are about the machinery itself.
- [ ] NEXT (product lane, the DEFAULT): BUG-563 declared homes for the 3 dirty rail outputs + backups/**, then
      BUG-560 (write_guard route). These are what stand between the ladder and BUILDING.
- [ ] OWNER GATE (DUE): the standing-rule CONSTITUTION promotion (bar MET on all three clauses; any promotion must
      be a POINTER to config/rail_mutations.yaml + scripts/check_rail_mutations.py, never a restatement);
      BUG-431 CONTENT promotion.

## D-2681 / BUG-577 + BUG-582 FIXED - THE FIXTURE RULE HAS ONE HOME (2026-09-27)

- [x] BUG-577 FIXED: scripts/lib/fixture.py - outside_tree (BUG-537) + real_repo (BUG-576) in ONE home;
      scripts/check_boundary_rehearsal.py, scripts/check_rail_mutations.py, scripts/check_repo_integrity.py now
      IMPORT it and every inline copy is DELETED (no third home).
- [x] The module is config-free by construction: the audited tree is DERIVED from its own location, so no config
      edit can re-point the rule; the builder declares no caller's identity/message (C12/C12d).
- [x] BUG-582 FIXED (filed + fixed here): the D-2680 justfile landing was PARTIAL - the banner and the collector
      --selftest were declared in MTR/DECISION-LOG/CONTEXT_INDEX/handoff and present in NO file. Both are now in
      'health', the banner FIRST so no rail can abort ahead of it.
- [x] Standing-rule satisfaction (D-2676): (i) ONE home scripts/lib/fixture.py; (ii) SEEN control
      scripts/lib/fixture.py --selftest as its OWN ladder line; (iii) NAMED oracle --selftest (6/6);
      (iv) MUTATION fixture_outside_tree_rule_is_load_bearing (floor 9 -> 10, subjects 7 -> 8).
- [x] MEASURED: just health-full -> 89 line(s) RUN, 0 fault(s), 262.3s; gate 9 rules SEEN to red, 8/8 subjects.
- [x] NO new bug hidden: BUG-582 was FOUND and CLOSED in this change-set (OPEN 137 -> 136, CLOSED 182 -> 184).
- [ ] NEXT (meta, in order - the freeze target): BUG-575, then BUG-571; the META LANE IS THEN CLOSED.
- [ ] NEXT (product, the DEFAULT lane): BUG-563 (the 3 dirty rail outputs + backups/**), then BUG-560.
- [ ] OWNER GATE (DUE): META-LANE FREEZE ruling; standing-rule CONSTITUTION promotion (POINTER only);
      BUG-431 CONTENT promotion.

## D-2682 / BUG-575 FIXED - THE DECISION GRAPH IS A GRAPH (2026-09-27)
- [x] config/decisions_policy.yaml#graph - ONE HOME: in_force_states [ACTIVE, RESOLVED, RATIFIED], not_in_force_states (7 more), supersession_state, successor_field, pinned_supersession_ids (12), pinned_forward_citations (4), both with a measured note.
- [x] scripts/reconcile.py - two new check kinds + PURE predicates + --selftest (9 known-answer controls, both directions). The citation walker is REUSED, never restated (BUG-577/D-2646).
- [x] config/reconciliation.yaml - decision_supersession_complete + decision_citations_in_force (both GREEN at the landing).
- [x] MEASURED: selftest 9/9 rc=0; reconcile --check rc=0; mutation entry SEEN to red (floor 10 -> 11, subjects 8 -> 9); rail registry rc=0; ladder 89 -> 90 declaring line(s).
- [x] NO new bug hidden: the lowercase-'active' spelling (5 of 812) is filed as BUG-583 (LOW), NOT folded into this landing.
- [ ] NEXT (meta, in order): BUG-571 (the cited-by-decision join) - then the META LANE IS CLOSED.
- [ ] NEXT (product, the DEFAULT lane): BUG-563 (declared homes for the 3 dirty rail outputs + backups/**), then BUG-560.
- [ ] OWNER GATE (DUE): META-LANE FREEZE ruling; standing-rule CONSTITUTION promotion (POINTER only); BUG-431 CONTENT promotion; BUG-583 (the lowercase state spelling - census or canonicalise).

## D-2683 / BUG-571 FIXED - THE SECOND DIVERGENCE SHAPE IS DECLARED (2026-09-27)

- [x] config/register_divergence.yaml - ONE HOME extended: declared_uncarried (62 ids, pinned BY IDENTITY, each with
      the line that first names it) + declared_max_uncarried: 62 (shrink guard; raising it needs a decision).
- [x] scripts/check_register_divergence.py - PURE carried_ids()/uncarried_ids()/faults(): BOTH divergence shapes,
      BOTH directions (undeclared / stale / ceiling), one code path for the live log and the rehearsal (D-405).
- [x] NOT BACKFILLED (D-2645): 62 prose names are debt, not bugs - a tool must not manufacture 62 OPEN bugs.
- [x] RECORDED REMEDY AMENDED: no cited-by-decision join inside bug_status.py (the generator cannot see the log's
      other shape; the mint already closes that direction; a second reader is the D-2646 two-homes defect).
- [x] SEEN: --selftest 10/10 rc=0 (both directions) + --check rc=0 (0 divergence; 62 pinned, all still uncarried;
      321 carried) + the control wired as its own ladder line.
- [x] TEETH: mutation register_uncarried_rule_is_load_bearing SEEN to red; floor 11 -> 12, subjects 9 -> 10.
- [x] NO new bug hidden: the duplicated declaring lines found by the owed whole-set audit are FILED as BUG-584 (LOW).
- [ ] NEXT (meta): NONE - BUG-571 was the LAST registered meta bug; the META LANE IS CLOSED.
- [ ] NEXT (product, the DEFAULT lane): BUG-563 (declared homes for the 3 dirty rail outputs + backups/**), then
      BUG-560 (route scripts/apply_workbook_rulings.py through scripts/lib/write_guard.py).
- [ ] NEXT (filed, behind the freeze): BUG-584 (the ladder refuses a duplicated declaring line), BUG-583, BUG-572,
      BUG-570, BUG-568/569, BUG-566, BUG-564 remainder, BUG-559.
- [ ] OWNER GATE (DUE): the META-LANE FREEZE ruling (the exception it needed - 575 -> 571 before product work - is
      now SPENT); the standing-rule CONSTITUTION promotion (POINTER only); BUG-431 CONTENT promotion; BUG-583.
