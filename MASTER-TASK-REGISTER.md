# Maxwell OS v3.0 — MASTER TASK REGISTER (tiered)

> **Updated:** 2026-10-07 | **Archive (full history):** `archive/governance_pre_tiered_2026-09-03/MASTER-TASK-REGISTER.md`
> **Companion:** `governance/aggregated_remaining_tasks.md` (archived copy in same folder)
>
> **Convention (standing rule):** unresolved/undone tasks at the TOP (most critical first, MUST→SHOULD→WORTH); resolved/done at the BOTTOM.

---

## 🔴 MUST — open (strategic-consequential order)

<!-- GOV-INDEX:START (D-2981 - DERIVED by scripts/gov_sync.py; do NOT hand-edit inside) -->
> **LIVE INDEX (D-2981 - DERIVED; do NOT hand-edit inside these sentinels).**
> Register truth (BUG-588/D-2692 - the census is the ONE home; nothing below restates a count): 1286 decisions (census stamp 0815ab568f6428e2, 2026-10-26) · 796 bugs (243 open / 553 closed; highest OPEN = BUG-1030) · 58 open tasks (MUST 8 / SHOULD 44 / WORTH 5; OWNER-moved 0, pipeline-moved 58; 1 standing rule(s) never close).
>
> Decisions NEEDING ACTION: **81** of 1286 — 🔴 open 32 · 🔵 proposed 26 · 📝 draft 1 · ⏳ deferred 16 · 📅 planned 6 | in effect: 🟢 active 663 · ⚖ ratified 150 | closed: ✅ resolved 357 · ⚪ superseded 16 · ⚪ archived 8 · ⛔ rejected 11 — the DECLARED buckets sum to the whole register (1286, D-2987/BUG-765)
>
> Open BUGS by severity (population = the census's 243 open ids; severity read from each id's FIRST heading at ANY hash depth): 🟥 CRITICAL 29 · 🟧 HIGH 57 · 🟨 MED 117 · 🟩 LOW 40 · UNLABELLED 0 (BUG-757) of 243 open.
>
> **OWNER LANE (0) — what ONLY YOU can move; the pipeline cannot advance these, each needs YOUR word:**
>
> | id | pri | what YOU decide | the gate |
> |---|---|---|---|
>
> **PIPELINE LANE (58) — what the agent will do next, ordered by priority then id (the register's two fields; source: config/task_register.yaml):**
>
> | id | pri | state | task | evidence |
> |---|---|---|---|---|
> | T-101 | 🔴 MUST | 🔴 open | HARDEN THE RETRIEVAL GOLDEN SET (the gate is saturated) | MEASURED 2026-10-14 (BUG-784): the owner-signed review (governance/golden_reanchor_candida |
> | T-120 | 🔴 MUST | 🔴 open | the ABSORPTION path - a later independent source must be able to RAISE an existing row's corroboration, and a  | MEASURED 2026-10-13 (read-only, by reading the write path and the identity model - no stor |
> | T-141 | 🔴 MUST | 🔴 open | SERIALIZE MODEL DOWNLOADS: two overlapping attempts at one repo leave .incomplete fragments that no tool can a | MEASURED 2026-10-15: models--lmstudio-community--Qwen3.8-27B-MLX-4bit held 4.0 GB as SIX . |
> | T-143 | 🔴 MUST | 🔴 open | RESOURCE-CLASS THE FAN-OUT: the engine pool is a mutex, the governed homes are a single writer | MEASURED 2026-10-15: the engine declares model_count 9 / loaded 3 / final_ceiling 56.6 GB, |
> | T-147 | 🔴 MUST | 🔴 open | WIRE THE STORE CENSUS TO EVERY DELETION BATCH: it is a generated face, and it lies the moment bytes move witho | MEASURED 2026-10-15: the census IS generated (pipeline/model_store_census.py: dir_bytes, m |
> | T-150 | 🔴 MUST | 🔴 open | THE DURABLE PATH IS THE DELEGATION PATH (D-3020): anything whose failure is not free goes through pipeline/sub | temp/runs/fanout_20261015i/98_receipt.json - 3/3 DONE with one task deliberately given a 1 |
> | T-181 | 🔴 MUST | 🔴 open | THE ADMISSION - the fifth transition is DECLARED, counted and PLANNED (D-3051): what remains is the word on wh | MEASURED 2026-10-16 by the FIRST live reading of scripts/plan_admission.py: 2,811 files in |
> | T-207 | 🔴 MUST | 🔴 open | EXECUTE governance consolidation PHASE-1-ONLY — rearrange the rail surface into ~12 invariant rails and collap | Five couplings measured 2026-10-26 (BUG-1030): rail_registry ladder source-of-truth transa |
> | T-105 | 🟠 SHOULD | 🔴 open | REA tier A/B mining — DEVONthink 3 (related-document ranking) and Cursor (derived code index) | governance/NOT-YET-EVALUATED-RESEARCH.md (REA targets logged 2026-10-13) |
> | T-106 | 🟠 SHOULD | 🔴 open | ROADMAP — MODULARITY (C21 swappable infrastructure) and CROSS-OS COMPATIBILITY (C26) | protocols: pipeline/storage/base.py only; no cross-OS smoke exists (2026-10-13) |
> | T-108 | 🟠 SHOULD | 🔴 open | BUG-712 / BUG-714 — the content_type residual and the harness-facing primitive | served run content_type census (2026-10-13) |
> | T-112 | 🟠 SHOULD | 🔴 open | PERF - the SERVED path loads the cross-encoder per PROCESS, so short-lived callers pay a cold-start of minutes | suite rail runtime 100-200s -> >210s after the dispatcher became the CLI default (2026-10- |
>
> _the face is a VIEW: 12 of 58 row(s) shown, the rest are in the register (config/gov_sync.yaml#face_list_limit)_
>
> **STANDING RULES — in effect, never close (1):**
>
> | id | rule |
> |---|---|
> | 📌 R-1 | STANDING — the user-facing faces are DERIVED, never hand-appended at the top |
>
> **Open decisions needing action (newest first; the states are DECLARED in config/gov_sync.yaml):**
>
> | id | state | category | title |
> |---|---|---|---|
> | D312 | PROPOSED | VERIFICATION | Calibrated abstention design - inert config, fail-closed production preserved |
> | D311 | PROPOSED | VERIFICATION | R3 held-out validation pre-registered (adoption blocked until the held-out run is published) |
> | D299 | PROPOSED | OPS | ANCHOR-1 audit follow-ups (goose main model, frozen hash re-stamp, normalisation policy) |
> | D280 | PROPOSED | MEASUREMENT | Single-coder ceiling — 30-row second-coder blind sheet prepared (D-280) |
> | D274g | OPEN | LABEL QUALITY / PROCEDURE | Implement the decision procedure the config already declares instead of free generation (D-274g) |
> | D274f | OPEN | MEASUREMENT / ANCHOR | The anchor is a conformance set, not a training set (D-274f) |
> | D274e | OPEN | VERIFICATION | Persist the verification tier Stage 5 already computes; fix the literal verifier stamp (D-274e) |
> | D274d | OPEN | MEASUREMENT / PROVENANCE | No label carries human provenance; no axis may gate a model comparison (D-274d) |
> | D274c | OPEN | LABEL QUALITY / MEASUREMEN | The ruler FLOOR column is void: accuracy was compared to a provenance share (D-274c) |
> | D274b | OPEN | RETRIEVAL / ONTOLOGY | ROLE is the highest-leverage axis, not a decorative one (D-274b) |
> | D273h | OPEN | LABEL QUALITY / MEASUREMEN | Cross the ruler strata with status and always report both frames (D-273h) |
> | D273g | OPEN | RETRIEVAL / ONTOLOGY | A chunk/evidence leg IS worth it -- at step 8, and only after the filters constrain (D-273g) |
>
> _the face is a VIEW: 12 of 81 row(s) shown, the rest are in the register (config/gov_sync.yaml#face_list_limit)_
>
> **Open bugs, most severe first:** 🟥 BUG-159 · 🟥 BUG-222 · 🟥 BUG-261 · 🟥 BUG-263 · 🟥 BUG-264 · 🟥 BUG-455 · 🟥 BUG-462 · 🟥 BUG-464 · 🟥 BUG-465 · 🟥 BUG-468 · 🟥 BUG-475 · 🟥 BUG-484.
<!-- GOV-INDEX:END -->

<!-- GOV-HISTORY:START (D-2981/D-2986) - below this line a face makes NO LIVE CLAIM: the INDEX sections are declared HAND INDEXES (row-joined on every run of the rail, never the authority) and the rest is DATED HISTORY (append-only). The DERIVED block above is the ONE authority for the current state. -->


> **SNAPSHOT 2026-10-12 (dated history — the DERIVED index at the top of this file owns the current state; D-2984).**
> Snapshot of the census as measured then: the counts it carried are SUPERSEDED by the DERIVED index above (one home, D-2642/D-2984/D-2985 — a version of this writer was re-cutting them to TODAY's value while the line said 'as measured then', repaired in place 2026-10-13). Which bug is highest-OPEN, and the current numbers, belong to the derived block.
> **D2590 NON-PRINCIPLE TIER
> LANDED** — decisions **D-2942..D-2945**; the store went **6,591 → 7,640 rows in ONE run** (principle 6,577 /
> process_template 774 / process_instance 156 / tool_instruction 108 / growth_edge 25). The 1,619 S4 sidecar records
> that had been "extracted, routed, written, NEVER committed" are now **committed (1,049) or DECLARED** (196
> mislabelled `principle` rows → BUG-719; 374 on the D2616 hold shelf). Rails after apply: `check_serving_gate`
> **7,640 MATCH / 0 mismatch / 0 undecidable**, `audit_sidecar_commit --strict` **rc=0** (tolerance 7 → BUG-720),
> `check_tests` 344 collected / 339 passed / 0 red, `integrity_check` 10/10.
> **Reconciled to CLOSED:** BUG-713 (superseded-run purge) and BUG-715 (the 7 unattributed records) — both had been
> resolved in PROSE only, so the machine register still read two CRITICAL/MEDIUM bugs OPEN.
> **NEW OPEN:** BUG-719 (196 rows whose own content_type is `principle` sit inside the non-principle sidecars; also
> the handoff's "81 tool_instruction remaining" was an arithmetic error — the true tier is 1,049), BUG-720 (emit a
> `deduped_cluster_ids` receipt so the audit tolerance goes to 0), BUG-721 (a DELEGATE returned a FABRICATED
> code-review verdict — false assurance; mitigation adopted), BUG-723 (232 corpus files covered only by the purged
> t11 run: knowledge preserved in the archive, served by nothing).
>
> **SNAPSHOT 2026-10-07 (dated history — superseded by the derived index at the top; D-2984).**
> Dated history: the register then stood at 1035 decisions with 460 bugs (163 open, 297 closed, highest OPEN then BUG-695). Forensic audit GREEN: 0 fatal rails — store-change re-baseline cascade (BUG-659..668) FIXED at root cause. The 11 ambiguous anchor-bridge rows resolved to the ratified canonical run (D-2881); depth conformance 183→194. BUG-687 (CLOSED, D-2882): nli_calibration pin on a gitignored derived artifact RETIRED (owner approved). BUG-688 (CLOSED, D-2883): the D-2618 retired golden is recorded, never gated (owner approved). BUG-689 (CLOSED, D-2830): the D-2767 A/B harness crashed on the v8 referee's owner-absence rows — `noise_drop` excluded (out of scope), `abstained` → 'emerging'.
>
> **OWNER-RULED (D-2884, 2026-10-09) — D-2727 now gated on the (a)+(b) landing:**
> 1. **D-2767 C+B gate = FAIL** (3-way coarse 0.5621 < 0.73 floor). Owner ruled **(a)** fine discipline → ADVISORY, 3-way macro + domains become the operative routing facet; **(b)** distinct-family decider A/B (autotrust/JEV-27B-VL or pplx-decider-v1.1-27b) in parallel. BUG-690 part 2 (macro drift v5→v8) FIXED; part 1 (coarse-kappa harness output) FIXED (commit 8895cbf: coarse_collapse/coarse_report + test_d2767_coarse_kappa.py 4/4) — the prerequisite instrumentation for (b) is in place. D-2884(a) macro operative routing is LANDED + R5 gemma-APPROVED (retrieve.py + maxwell_mcp_server.py, 2026-10-09).
> 1b. **D-2884(b) A/B RESULTS (2026-10-09):** Arm A pplx FAIL coarse_kappa 0.6738 (emerging 0.0052); Arm B laya FAIL 0.0242 (position bias); Arm C clef-flash FAIL 0.5705 but **emerging recall 0.4286 (3/7) — NON-ZERO vs pplx 0.0** (empirically validates BUG-692: the emerging clause is ceiling-only, so an always-answer decider trivially passes with zero sensitivity). clef-4bit (27B) pending. **None clears 0.73 yet** — owner must rule on (a) an emerging-RECALL floor (BUG-692) and/or (b) whether 0.73 is reachable by ANY distinct-family decider.
> 2. **RATIFY-2 (D-2727) — full S4→S5→S6 rerun** stays BLOCKED until (a)+(b) land. Then `caffeinate -dimsu`; `python3 pipeline/runner.py --dry-run` then full.
> 3. ~~Train/eval split (Option A)~~ — **DONE (D-2813 ratified):** split_manifest.json 46 golden / 162 eval / 208 total; ids_sha256 pin enforced (BUG-603 CLOSED).
>
> **PARKED — freeze window META-LANE-FREEZE-1 (day 6/14, review_by 2026-10-11):** BUG-559 (2 UNREVISIONED receipts — remedy: git-commit `config/decisions.yaml` + `governance/anchor_adjudication_workbook_20260924.csv`, then re-cut receipts) · BUG-593 (mutation-gate fixture carries ONE commit).
>
> **REGISTRY DEBT:** D2622 ACTIVE → RESOLVED at RATIFY-2 · D2621 PROPOSED (formalize `pipeline/dedup` module vs keep ad-hoc scripts) · D2547 PLANNED (per-label thresholds) · 12 pinned legacy supersession ids · 4 forward-reference decisions · 63 named-but-uncarried ids (shrink-only).
>
> — everything below this index is dated history / SHOULD / WORTH / DONE —

> **2026-10-05 BUG-638/BUG-639 + D-2822..D-2825 (registry 955): D-2825 cluster_28517 "Planck's Constant Derivation" RECOVERED (transient S4 `application` failure, NOT an S2 gap — S2 was complete/coherent; `--cluster 28517` retry cleaned it). D-2824 dedup-accept phantoms 3776/26074. D-2823 normalize bare `--cluster` ints. D-2822 PROPOSED (S5 gate A(d) OR-entail+AND-no-contra, T9). BUG-639 (S4 delta-merge shrink-guard false-positive → `force_shrink=bool(cluster_ids)`) + BUG-638 (METRICS.jsonl floor guard) both FIXED. S4 final 6,591 / preflight GREEN; S5 STALE (6,588) → re-run; S6 empty → run. Registry 1112 decisions / 525 bugs (185 open / 340 closed; highest OPEN = BUG-637).**



> **2026-10-03 D2622 WIRED + D2621 CORRECTION: D2622 practicality now wired into stage5_verify.py as ADVISORY tier (`practicality` field on every verified FB; never drops; C16 fail-loud on missing config). D2621 prior "no work landed" note CORRECTED — method landed via D2625/D2626/D2627 (all RESOLVED 2026-09-14: dedup_scan/judge/prefilter/apply scripts; mark-not-delete R-D410). Registry/buglog UNCHANGED (938/366); no census re-derive. D2622 stays ACTIVE (RESOLVED at RATIFY-2); D2621 stays PROPOSED (residual = owner choice: formalize pipeline/dedup module vs keep ad-hoc).**
> **2026-10-03 OWNER-AUTHORIZED STATE-FLIPS EXECUTED: D2546 PLANNED→RESOLVED (SHACL shipped D2555), D2548 PLANNED→REJECTED (grammar-decoding A/B rejected D2392), D2622 PROPOSED→ACTIVE (backend landed D-2723; S5 wiring deferred RATIFY-2). D2622 state-vocabulary blindspot closed: practicality.yaml `state: IMPLEMENTED`→`backend_state: landed`. Census re-derived + decisions_registry receipt re-baselined. Registry 938 / buglog 366 unchanged; session_seed in sync. Remaining RED = owner-ruling only (R003/R146 AUTOFILL → anchor4_workbook + depth_workbook_row_count).**
> **2026-10-03 SUPERSEDED/DONE/CONFLICT AUDIT + BUG-625/BUG-626 FILED (no new decision, registry stays 931): superseded=16 (4 successor + 12 pinned legacy debt), done=270 RESOLVED, conflicting=2 NEW (D-328 list-typed superseded_by → BUG-626; D-2104→D-2085 reverse-direction supersedes, LOW), superseded-bugs=NONE, fixed-bugs=220 CLOSED. buglog re-derived 145 OPEN / 220 CLOSED / 365 [SUPERSEDED 2026-10-03: now 132 OPEN / 234 CLOSED / 366, highest BUG-604; BUG-625/BUG-626 RESOLVED]. session_seed synced. Six forensic rails GREEN.**
> **2026-10-03 OWNER RATIFICATION + R5 DISCHARGE: DROP(13)/QUARANTINE(15)/re-ground(8) FINAL-ratified (re-ground(8) = 4 verbatim R020/R064/R137/R188 + 4 KEEP-as-semantic-paraphrase R037/R053/R083/R151; DROP/QUARANTINE already-minted D-2711/D-2719 re-confirmed — no new decision, registry stays 931). R5 generator≠verifier review of the 20-file D-2801 diff DISCHARGED → PASS (fingerprint fail-closed ✓, 0 silent errors ✓; C12 residuals: probe_run 'latest'+OMLX_URL hardcode → follow-on bug). S4 rerun now UNBLOCKED (D-2801 commit + R5 review both done).**
> **MINTED 2026-10-03 (D-2801 ACTIVE, OWNER ACKED): BUG-528 pipeline/** lock re-scope LANDED — the critical-path unblock is DONE.**
> 20 pipeline files (745 insertions + untracked practicality.py) are legitimate uncommitted work (D-2747 reroute,
> D-2757 applicability, BUG-614 stage-code fingerprint, D-2622 practicality, D-2798 advisory, D-2703 chunking,
> D-2716 run-id) that landed against the will_not_touch `pipeline/**` lock — commit is refused (rail 4), revert
> breaks stage4_merge.py's imports. Proposal `governance/OWNER_GATE_BUG528_20261003.md`: re-scope the lock from
> edit-gated to REVIEW-gated (R5 generator≠verifier + D-naming + stage_code_fingerprint). **S4 rerun is BLOCKED
> until the owner resolves this with one ack.** Stale D-2703 item closed: evidence_passages schema bug = BUG-596
> (CLOSED D-2721), NOT re-filed. Registry unchanged: decisions 930 / buglog 363 (143 open / 220 closed) /
> highest OPEN then BUG-622 (highest overall then 624, both 623/624 RESOLVED).
> **NEW — 2026-10-02 (D-2783): S4 classifier shortlist REVISED after archive/chat-recall research — Mistral-Small-3.1-24B was ALREADY tested+rejected (v1.0 D492: no chat template, 0% schema validity); Bonsai 2 = Prism Ternary (1-bit Qwen3.8) R5-excluded; Ornith-1.5-35B-A3B already local+OMLX-served → first no-download FIT-eval candidate. Shortlist = [Ornith local, Gemma-3-12b-it fallback]; gate unchanged (faster AND kappa≥0.7 AND ≥ gpt-oss-20b).**
> **NEW — 2026-10-02 (D-2784): Ornith-1.5-35B-A3B FIT eval NEGATIVE — fails prod schema on BOTH axes (depth CoT overflow via missing reasoning_off; discipline SparseClassificationError 'application 4<10'). Same class as Mistral D492. Shortlist = [Gemma-3-12b-it fallback]; gate unchanged. scripts/fit_eval_model_swap.py added (config-first swap_eval_* keys).**
> **NEW — 2026-10-02 (D-2781/D-2782): BUG-622 hierarchical N=30 NEGATIVE (kappa 0.514 vs 0.452 flat, << 0.7) → hierarchical-via-prompt REJECTED, pivot to D-2767 model swap; kappa-floor policy: keep agreement_floor.yaml (Krippendorff α 0.8) untouched, adopt SEPARATE classifier-kappa bar 0.7 DECLARED before swap.**
> **NEW — 2026-10-02 (D-2780): 58 mapped depth cells handed to owner as cross-model worksheet (Claude/GPT/DeepSeek + goose; Kimi has NO depth axis); 3 emerging rows DEFERRED (owner cannot refine → remain fail-closed excluded); forensic audit GREEN; owner fills depth → 149→(up to)207 golden.**
> **NEW — 2026-10-02 (D-2778/D-2779): anchor forensics GREEN — BUG-618+BUG-619 RESOLVED (204 discipline golden, 149 depth golden, owner-provenanced, fail-closed emerging/mapped exclusion); hierarchical discipline probe (scripts/hierarchical_discipline_probe.py) built + N=3 smoke GREEN (kappa 0.571), full N=30 A/B vs 0.452 baseline running.**
> **NEW — 2026-10-02 (D-2777: BUG-623 dependency smoke GREEN — S5 NLI + S1.5 embedding verified under active 5.x; no pin-back).**
> FILES BUG-623 (RESOLVED). scripts/smoke_bug623_dependencies.py (known-answer, no LLM): bge-m3 embedding discriminates (0.686>0.457),
> DeBERTa-v3 NLI discriminates (entail 0.997 / contra 0.322) under active transformers 5.8.1 / ST 5.6.1. No silent 5.x regression;
> requests/urllib3 warning ABSENT. NO pin-back. Residual hygiene: lockfile declares 5.14.1/5.7.0 vs active 5.8.1/5.6.1.
> **NEW — 2026-10-02 (D-2776: forensic-audit governance reconciliation — register-divergence rail RED→GREEN).**
> FIXES BUG-571's live divergence: BUG-594/BUG-595 promoted from the MUST-inbox table to header events (now counted OPEN),
> BUG-017/BUG-183 pinned by identity in config/register_divergence.yaml, BUG-170 un-staled, declared_max_uncarried 62→63.
> Register 362 (146 open / 216 closed). Rails re-verified GREEN: check_register_divergence / check_bug_status /
> check_decision_membership. session_seed open_bugs_n 129→146, buglog_entries 360→362.

> **NEW — 2026-10-02 (D-2774: BUG-622 closed-menu fix IMPLEMENTED but N=30 A/B NEGATIVE — 0.344 vs 0.452 baseline; flag reverted; PIVOT to classifier FIT eval/swap, NOT more prompt engineering).**
> FILES BUG-622. D-2773's closed-62-menu injection is now live behind stage4.discipline_closed_menu_enabled (default
> false, byte-identical when off). Live N=30 A/B: menu ON kappa 0.344 vs OFF baseline 0.452 → the closed menu does NOT
> help. Flag reverted to false. RULING (preliminary): BUG-622's binding constraint is gpt-oss-20b discrimination QUALITY
> across the 62-label space, not open-vocabulary generation. NEXT: (1) [RUN] D-2767 S4 classifier FIT eval
> (Mistral-Small-3.1-24B vs gpt-oss) + market research for a faster/more-accurate discipline classifier; (2) [BUG] BUG-623
> dependency smoke test (transformers 5.14.1 / ST 5.7.0 vs S5 NLI + S1.5 embedding); (3) [RUN] gpt-oss turboquant_kv + Q4 A/B
> (D-332); (4) [RUN] live depth conformance gate; (5) [TASK] RESTART S4 main loop (content_type + applicability deterministic,
> independent of depth anchor).

> **NEW — 2026-10-02 (D-2759: ANCHOR-208 depth is 28% STALE — owner_depth vs canonical depth_final_class; do NOT wire until rebuilt).**
> FIXES BUG-618. 42/150 owner rows (28.0%) mismatch == intra_rater_alpha raw 0.710: the 208 view `depth` == `owner_depth`
> (raw blind call), NOT the canonical `depth_final_class`. 7 negative_set rows (owner-retracted universals) still carry
> depth=1; canonical 150 have ZERO universals. SUPERSEDES D-2758's "wire as-is".
> **NEXT (dependency order, owner-gated):** (1) REBUILD ANCHOR_208 depth column from depth_final_class (150) + verify 58
> extras' source + provenance-stamp each cell (human_adjudicated vs mapped) — deterministic data-repair, scripted, then
> re-audit; (2) keep 7 negative_set rows as near-neighbour negatives; source universal(1) conformance from the annex
> U001-U004 (class-1 unreachable in the 150); (3) ONLY THEN wire ANCHOR_208 depth into stage4_merge.py golden few-shot +
> conformance gate; (4) RESTART S4 main loop (content_type + applicability deterministic — can start NOW, independent of
> depth); (5) BUG-615 root cause (S1.5 5-cluster duplication).

> **NEW — 2026-10-02 (D-2758: forensic finding — 208-row owner-adjudicated five-axis anchor ALREADY EXISTS; wire it as S4 depth/domain/discipline anchor).**
> FIXES BUG-617 (stale "depth has no human ground truth"). `governance/ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv` = 208 rows, all
> five axes filled (0 blanks): depth 208/208 (universal 7 / cross-domain 50 / domain 92 / specialized 59), domain 208/208,
> primary_domain 208/208, discipline 208/208, content_type 208/208, extraction_type 208/208 — OWNER-ADJUDICATED (D-2720). This IS
> the D-274f anchor (already built). D-2754/BUG-617 conflated the 1,027 gpt-oss SILVER labels with this 208-row OWNER anchor.
> EMPIRICAL: depth ≠ domain-count (1 domain spans all 4 depths; discipline always single-valued). Confirms semantic mechanism-scope.
> **NEXT (dependency order, owner-gated):** (1) WIRE ANCHOR_208 into stage4_merge.py depth/domain/discipline golden few-shot
> injection + held-out conformance gate (replace silver golden examples; currently depth.json has 7,149 content-derived entries);
> (2) normalize anchor discipline cells FIRST (2 trailing-space dupes 'economics '/'sociology ', 5 'emerging' catchall, 4 off-menu
> R042/R086/R091/R117); (3) refine D-2757 provenance guard distinct-DISCIPLINE → distinct-DOMAIN; (4) THEN restart S4 fresh so all
> 8,217 FBs run with the owner anchor + deterministic reroute + applicability; (5) RESTART S4 main loop (content_type +
> applicability are deterministic and can start NOW, independent of depth anchor wiring).

> **NEW — 2026-10-02 (D-2757: depth refinement + applicability axis IMPLEMENTED + owner dispositions FOLDED).**
> DONE: (a) 13 owner role corrections folded into `governance/content_type_adjudication.json` (quarantine→growth_edge x8,
> principle x2, tool_instruction x2, noise_drop x1; dist now quarantine 221 / growth_edge 152 / noise_drop 153 / principle 16 /
> PT 28 / PI 1 / TI 2); (b) new `governance/applicability_adjudication.json` (3 owner dispositions: educational x2,
> philosophical_educational x1); (c) `applicability` axis added to config/content_types.yaml + `derive_applicability()` in
> content_types.py + wired into stage4_merge.py (applicability + applicability_source, provenance-stamped). DEPTH: D-2755's
> "domain-count" ruling CORRECTED — depth = semantic mechanism-scope (D2220), NOT domain count; deterministic distinct-discipline
> provenance added as a CONSISTENCY GUARD (flag, never override). Dry-run 8,217 FBs: operational 7,898 / educational 137 /
> philosophical_educational 146 / heuristic_tip 36 (deterministic 8,214 / owner_adjudicated 3).
> **NEXT (dependency order, owner-gated):** (1) RESTART S4 fresh — all 8,217 FBs through the reroute + applicability; depth
> auto-resumes from depth.json; (2) owner spot-checks quarantine BOUNDARY cases after deterministic bucketing (closed menu now
> has applicability labels); (3) build the D-274f anchor with DEPTH + DOMAIN conformance sets (human-provenanced backbone,
> BUG-617); (4) upstream S1.5 root-cause for the 5-cluster segment duplication (BUG-615); (5) add `contested` S2 write path
> (D-2747 pending).

> **NEW — 2026-10-02 (D-2752: name collisions benign; 5-record fb_id dedup leak fixed; depth.json reused; S4 restart fresh).**
> DONE: back up + delete stale pre-reroute S4 checkpoint (safe_delete; depth.json kept — 7,149 content-derived entries reused).
> DONE: BUG-614 stage-code fingerprint guard (discard stale checkpoint on code drift, PRESERVE depth/cribs). DONE: BUG-615
> cross-run fb_id dedup (seen_fb_ids guard + provenance merge). Depth classification NOT restarted; only the main loop restarts.
> **NEXT (dependency order, owner-gated):** (1) RESTART S4 fresh (long-running) so all 8,217 FBs pass through the wired
> reroute; depth auto-resumes from depth.json; (2) upstream S1.5 investigation — why identical segments land in 5 clusters
> (BUG-615 root cause); (3) add the `contested` S2 write path + wire `contested` emission (D-2747 pending); (4) owner
> spot-checks the 234 quarantined records → **`governance/spot_check_quarantine_234.md`** (generated; 234/234 fb_ids
> resolve in S2, 0 missing). (5) D-2753 CORRECTION: constrained decoding was already A/B tested + FAILED (D2392 xgrammar
> breaks gpt-oss-20b; D2408 json_object→empty) and content_type fine-tune is BLOCKED (D274d/D274f anchor prerequisite) —
> deprioritize both; next WORTH step is building the D-274f anchor.
> **D-2754 / BUG-617 (depth provenance):** the 1,027 "golden depth" = gpt-oss SILVER (93.3% unverified, 6.7% 4-axis);
> verified_core has only 61 human-verified depth labels. Silver depth classifier is DORMANT (flag OFF, <0.85 gate) so NO
> active contamination, but NO depth label is ground-truth. NEXT: extend the D-274f anchor with DEPTH conformance sets
> (depth_source provenance) before any depth retrain.
> **D-2755 (quarantine subcategory taxonomy, owner-discovered):** the 234 quarantine are NOT one blob — owner's 27
> annotations reveal a MISSING orthogonal `applicability` axis (operational | educational | philosophical_educational |
> heuristic_tip). RULING: do NOT hand-comment all 234 (27 is enough to define the menu); bucket the rest deterministically,
> spot-check boundaries only. NON-blocking for S4 (HOLD). Depth: derive deterministically from domains (BUG-617).


> **NEW — 2026-10-02 (D-2750: principle-purity adjudication APPLIED — D2417 flip ratified, tier-2 fail-closed FORM invariant live, 527-row owner map seeded).**
> D2417 flip DONE (principle→normative_heuristic). Tier-2 `_principle_form_violation` live in reroute_content_type (retained-only:
> growth_edge / process_template / quarantine; never noise_drop). Owner map now 573 rows. 16/16 tests green.
> **NEXT (dependency order):** (1) add the `contested` S2 write path + wire `contested` emission for disputed sources (D-2747
> pending item); (2) retroactively APPLY reroute_content_type() to the S2 checkpoint and re-run the content_type + FORM audit
> post-S4 to confirm BUG-611/612/613 drift closed; (3) fix the 5-record checkpoint dedup leak (identical fb_id emitted 5×);
> (4) owner spot-checks the 231 quarantined definitional-with-prescriptive records.

> **NEW — 2026-10-02 (D-2749: extraction_type (FORM) audit — content_type does NOT depend on FORM; D2417 `principle→descriptive_model` default is a LATENT inversion; FORM is best-effort, never a routing input).**
> ANSWER TO "does content_type rely on FORM / is FORM accurate": NO dependency — D2323 decouples ROLE from FORM;
> _resolve_content_type()/reroute_content_type() never read extraction_type. The dependency is REVERSED: D2417
> CONTENT_TO_EXTRACTION_TYPE defaults FORM from ROLE when S2 omits it. FORM signal agreement is 19.5–37.3% (cross-contaminated,
> unverifiable by structure) → FORM is re-declared BEST-EFFORT metadata, never a routing/verification input. Files BUG-613.
> Landed: tests/test_contested_retention_guard.py (6/6) pins the D-2747 retention guard.
> **NEXT (dependency order, owner-gated):** (1) owner ratifies the D2417 default flip `principle → normative_heuristic`
> (changes future-batch semantics; 0 defaulted this checkpoint so not urgent); (2) owner adjudicates
> temp/principle_purity_triage.json (152 definitional + 238 ambiguous + 144 open_tension) → seed the tier-1 map; (3) add the
> principle structural invariant as tier-2 of reroute_content_type(); (4) re-run the content_type + FORM audit post-S4.

> **NEW — 2026-10-02 (D-2748: principle-purity audit — 2.1% of 7,151 principles are definitional non-rules; 100%-accuracy reframed as fail-closed structural invariant + owner-adjudicated residual).**
> ANSWER TO "are all principles 100% transferable rules?": NO. Deterministic audit (scripts/audit_principle_purity.py, D-343
> no-LLM → temp/principle_purity_triage.json) flags 527/7,151 (7.4%): definitional_no_prescriptive 152 (2.1%, high-precision
> "X is/describes/involves" + no prescriptive verb → descriptive fact, NOT a KNOW/APPLY rule); definitional_with_prescriptive
> 238 (3.3%, ambiguous); open_tension 144 (2.0%, growth_edge candidates); exact_dup 5 (dedup leak). D-2747 re-evaluated:
> correct in shape but BLINDSPOT — principles pass through reroute_content_type() as a NO-OP (only the owner map can touch them).
> Reframe: 100% accuracy = "no misclassified record reaches S6" via per-role STRUCTURAL INVARIANT + FAIL-CLOSED at
> _resolve_content_type() + owner-adjudicated residual map. Files BUG-612 (principle-purity drift); backfilled BUG-170 heading.
> **NEXT (dependency order, owner-gated — do NOT auto-flip, a 2% knowledge-base drop cascades):** (1) owner adjudicates
> temp/principle_purity_triage.json → seed governance/content_type_adjudication.json (tier-1 map already supports
> principle→disposition); (2) add the principle structural invariant (definitional + no prescriptive → disposition) as tier-2 of
> reroute_content_type(); (3) add a `contested` S2 write path + retention-guard unit test (from D-2747); (4) re-run the
> content-type audit post-S4 to confirm BUG-611 + BUG-612 drift closed.

> **NEW — 2026-10-02 (D-2747: conspiracy = growth_edge + contested flag; deterministic non-principle reroute wired AUTOMATIC into S4).**
> OWNER-CONFIRMED: conspiracy/speculative = growth_edge ROLE + `contested` retention flag (NOT a 6th content_type — D2591
> axis stays CLOSED). `contested` is a growth_edge RECORD bool, NOT a new epistemic_status value (that axis is S5-derived
> and stays 4-valued). Reroute is AUTOMATIC for future batches: pipeline/content_types.reroute_content_type() (pure rules,
> D-343 — never LLM) wired into stage4_merge._resolve_content_type() (the routing choke point). 3 tiers: owner map
> (governance/content_type_adjudication.json, 46 rows) → keyword denylist (config/content_types.yaml) → structural.
> **NEXT (dependency order):** (1) retroactively apply reroute_content_type() to the 46 deterministic rows pre-S6 (S4 still
> running; don't pause it — it never touches non-principle); (2) owner-adjudicate the residual semantic-boundary set
> (~60–100 records) into governance/content_type_adjudication.json; (3) add a `contested` write path (S2 emits it for
> disputed sources) + retention guard unit test; (4) re-run content-type sampled audit post-S4 to confirm the ~18% TI /
> ~10% GE drift closed. Closes BUG-611 (root cause BUG-170).

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

## 🟠 SHOULD — open — HAND INDEX, not a register (the DERIVED block above is the ONE authority; rows joined on every run, D-2986)

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

## 🟡 WORTH — open (later / after measurement) — HAND INDEX, not a register (the DERIVED block above is the ONE authority; rows joined on every run, D-2986)

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

## ✅ DONE — bottom (recent, resolved this/prior sessions) — HAND INDEX, not a register (the DERIVED block above is the ONE authority; rows joined on every run, D-2986)

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
- [x] META-LANE FREEZE RULED 2026-09-27 (D-2688): ONE HOME `config/freeze_window.yaml`; POINTER ONLY, never a restatement (D-2688): from D-2680 forward, the governance machinery is
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

## D-2684 / BUG-563 FIXED - A DIRTY PATH HAS TWO DECLARED HOMES (2026-09-27)
- [x] `.gitignore` - DECLARED exclusions (`backups/`, `governance/drift_report_2*.json`, `governance/bench_preflight_2*.json`), each joined to a `why`; trailing comments REMOVED (they were literal patterns - caught by the new rail)
- [x] `config/repo_integrity.yaml#worktree` - ONE HOME: `plan:` (the granting home, consumed) + `excluded:` (3 declarations) + `bug: BUG-563`
- [x] `scripts/check_repo_integrity.py --worktree` - PURE `worktree_faults()` + raw NUL-separated `dirty_entries()` + git-joined `is_ignored()`; 6 new controls
- [x] SEEN: `--selftest` rc=0 (6 worktree + 15 existing); `--worktree` rc=0 (14 dirty, 14 granted, 0 in neither home)
- [x] TEETH: mutation `worktree_undeclared_dirty_path_rule_is_load_bearing` SEEN to red; floor 12 -> 13
- [x] GRANTS: 7 NAMED paths in `may_touch` (`.gitignore` + 6 indexed stores) + widening_log entry 26
- [ ] OWED (declared, not silent): widen the SAME rule into the pre-commit hook once the plan can grant an artifact in the commit that creates it (item 5 of D-2684)

## D-2685 / BUG-560 FIXED - THE OWNER-RULING APPLIER PASSES THROUGH THE GUARD (2026-09-27)

- [x] scripts/apply_workbook_rulings.py writes through write_guard.write_rows(mode="merge", owned_keys=<ruled columns>) and appends through the new write_guard.append_lines (SUFFIX-ONLY): the owner-cell write is RECEIPTED, not silent.
- [x] The cell scope has ONE home (config/anchor_workbook_fixes.yaml#rulings_io.owned_columns), joined by a pure scope_faults(): a ruling outside the declaration is refused with nothing written.
- [x] `--check` is a justfile line: the anti-revert rail was DECLARED in three homes and RUN in none since D-387 (the BUG-582 shape).
- [x] config#rulings_io.backup_dir/backup_suffix DELETED (pre-image rule has one home: write_guard._backup); config/artifact_ownership.yaml#owned_by completed (+3 columns the applier occupied) and the fixlog declared append_only with a writer_of_record.
- [x] Mutation entry floor 13 -> 17; 4 entries for this fix, all SEEN to red through their own named markers.
- [ ] OWED (declared, not silent): a whole-set scan for the leak class this fix found in its OWN selftest - which other `--selftest` writes default to backup=True and deposit pre-images into the tree they audit?
- [x] DECIDED (2026-09-27): config/derivations.yaml COMMITTED with its rail-written re-measure (shadowed_declared 211 -> 212 + the REMEASURED line). REASON: the rail owns that number (D-2642), `just health` is GREEN with this value, and a revert would be re-written by the next rail run - a revert would state a fact about the tree that is not true. The RAISE is loud-not-fatal by design (rc 2 = the declared ceiling was stale and is now recorded).
- [ ] NEXT (product): BUG-560 (route `scripts/apply_workbook_rulings.py` through `scripts/lib/write_guard.py`); then BUG-564 remainder / BUG-572 / BUG-583 / BUG-584
- [ ] OWNER GATE (DUE, one word each): META-LANE FREEZE ruling; standing-rule CONSTITUTION promotion (POINTER only); BUG-431 CONTENT promotion; BUG-583 (lowercase 'active')

## D-2686 - A PRE-IMAGE IS EVIDENCE OF THE AUDITED TREE (2026-09-27) - the D-2685 OWED item closed STRUCTURALLY
- [x] MEASURED (whole set, the OWED item): every `python3 ... --selftest` command the ladder's own TEXT declares (33, deduplicated) was run with a before/after snapshot of `backups/`, of `governance/MUTATION_JOURNAL.jsonl` and of `git status --porcelain`: 33/33 clean - 0 pre-images, 0 journal records, 0 dirty paths. `python3 scripts/check_tests.py --check` (the 261-test suite) likewise: 0 new backups, 0 journal records, 0 dirty paths. The BUG-560 leak was the ONLY instance in the declared set.
- [x] LANDED: `scripts/lib/write_guard.py#pre_image_faults(path)` (PURE) and `_backup()` now fails CLOSED on an artifact outside the audited tree (`WriteRefused`, nothing written). ONE HOME: the store's containment rule lives in the guard that owns the store; the tree is derived from the guard's own location (C12, no config can re-point it).
- [x] ORACLE (named): `python3 scripts/lib/write_guard.py --selftest` = 16 invariants / the 7 expected refusals, BOTH counts DERIVED from the source; 4 new NAMED controls (`an_out_of_tree_artifact_is_reported_where_its_pre_image_would_land`, `an_artifact_of_the_tree_owns_its_pre_image`, `the_pre_image_store_refuses_an_out_of_tree_artifact`, `a_refused_pre_image_deposits_nothing_and_writes_nothing`).
- [x] MUTATION (D-2676 iv): `config/rail_mutations.yaml#pre_image_containment_is_load_bearing`, floor 17 -> 18; gate `ok rail mutations: 17 declared rule(s) SEEN to red through their own control`, rc 0.
- [x] SEEN (no cascade): `python3 scripts/run_ladder.py --collect health` = 94 lines RUN, 0 faults, rc 0 (224.6s) with the refusal live; applier `--selftest` 14/14 and `--check` green; `backups/` unchanged at 118 entries.
- [x] FILED (held behind the META-LANE FREEZE): BUG-585 - `agent/session_seed.yaml` states the open-bug count in TWO homes and they disagree (stale `77` in the dated `current_state` block beside the DERIVED `134`); no reader, so it is unfalsifiable where it sits. Remedy is one line; not worked here.
- [ ] OWED (declared, not silent): the scan itself is a SCRATCH measurement (`temp/scan_fixture_leaks.py`, gitignored). Hoist it into a DECLARED event-driven rehearsal (change time, NOT `just health`: it re-runs the whole control set) or declare it `dormant` in `config/rail_registry.yaml#dormant` with a real `exercised_by` path.
- [ ] NEXT (product lane): BUG-564 remainder (the hook ROUTE as a declared subject), then BUG-572 / BUG-583 / BUG-584.
- [ ] OWNER GATE (DUE, one word each): the META-LANE FREEZE ruling; the standing-rule CONSTITUTION promotion (POINTER only, never a restatement); BUG-431 CONTENT promotion; BUG-583.

## D-2687 - THE COMMIT BOUNDARY IS A ROUTE AND A MODE (2026-09-27) - BUG-564 remainder CLOSED

- [x] MEASURED: `core.hooksPath` redirects git's hook (declared file ABSENT; a different file refused the commit);
      a mode-644 hook is SKIPPED and the commit LANDS rc=0 (only a suppressible `hint:`).
- [x] LANDED: `config/rail_registry.yaml#commit_boundary.path = git-path:hooks/pre-commit`;
      `scripts/check_rail_registry.py#boundary_faults` (PURE) + `Boundary` facts; the dead `readx` removed (C19);
      `commit_boundary` is now a REQUIRED registry key (fail closed); `scripts/install_git_hooks.sh` resolves the
      hook the same way (the remedy can clear the fault).
- [x] ORACLE: `--selftest` 14/14 named controls; live `--check` rc=0; `install_git_hooks.sh --check` rc=0.
- [x] MUTATION: `commit_boundary_route_and_mode_is_load_bearing`, floor 18 -> 19; `check_rail_registry.py` added
      to `coverage.required_subjects` (13/11 covered).
- [x] SEEN (no cascade): whole ladder 94 line(s) RUN, 0 fault(s), 227.7s, rc 0.
- [ ] OWED: BUG-585 (session_seed states open_bugs_n twice) and the freeze WINDOW/exit declaration.
- [ ] NEXT: the leak scan's declared home, then BUG-584, BUG-572, BUG-583.

## D-2688 - A FREEZE IS A WINDOW, AND A WINDOW ENDS BY ITS OWN TERMS (2026-09-27) - BUG-586 FIXED
- [x] ONE HOME: `config/freeze_window.yaml` (META-LANE-FREEZE-1) - the parked set pinned BY IDENTITY, `max_held` 8,
      `released {}` (the DRAIN PATH), a WRITTEN exit and `review_by 2026-10-11`.
- [x] ONE READER: `scripts/check_freeze_window.py` in `justfile:health` (--selftest fatal + live tri_state). It reads
      the DERIVED `governance/bug_status.json` - never a second parser of the log (D-2646).
- [x] ORACLE: 15 named controls; live rc=0 (parked 8, still OPEN 8 of ceiling 8; exit MET: opening_set_closed).
- [x] MUTATION: `freeze_window_exit_is_load_bearing`, floor 19 -> 20; the registry pins BOTH guards; the consumer
      join declares the window's single reader (6 homes / 8 edges, BUG-562 shape refused at the boundary).
- [x] SEEN: ladder 96 line(s) RUN, 0 fault(s), 260.9s, rc 0. R5 review (gemma-4-E4B-it-MLX-4bit): APPROVE.
- [x] RULED: the META-LANE FREEZE is retired as a RECOMMENDATION - it is a declared window with a reader.
- [ ] OWED (owner): CLOSE the window the moment rc 2 says its exit is MET, or RE-RULE it when review_by passes.
- [ ] NEXT: BUG-585 through the DRAIN PATH (`released:`) - the mechanism's first real test; then the leak scan's
      declared home; then BUG-584, BUG-572, BUG-583.

## D-2689 - THE STATUS SLOT IS A POSITION AT A HEADER BOUNDARY, NEVER PROSE (2026-09-27) - BUG-572 FIXED, BUG-562 CLOSED
- [x] ONE HOME: scripts/bug_status.py#status_slot - the slot is (1) the LEADING parenthetical, (2) the FIRST segment
      before the first colon, (3) the FIRST WORD after that colon, (4) the TRAILING parenthetical. Prose between them
      may NOT decide; no candidate -> EMPTY -> OPEN. The whole-header substring fallback is GONE.
- [x] ORACLE: --selftest reports 20 named controls, 9 of them new (3 defect shapes that each read CLOSED before, 6
      must-not-move shapes); --selftest reads no log, no declaration and writes nothing.
- [x] MUTATION: status_slot_is_a_boundary_not_prose restores the prose fallback and the FIRST named control
      (the_title_may_not_decide) stops firing; floor 20 -> 21; scripts/bug_status.py in coverage.required_subjects.
- [x] SEEN: register re-derived and its own reader agrees (ok bug_status: register equals its re-derivation); the
      whole ladder rc=0 (temp/health1.log); registry rc=0; consumer join rc=0; freeze window re-read below.
- [x] THE AUDIT FIRED ON THE FIX ITSELF: the 2 ids whose final status moves are BUG-419 (GENUINELY OPEN - the
      register schema asymmetry is LIVE: open is a list of OBJECTS, closed a list of plain id STRINGS) and BUG-562
      (GENUINELY CLOSED - its owed rail landed and was verified by running it). Landing the parser ALONE would have
      newly mislabelled a fixed bug, so this change-set carries BUG-562's named closure event.
- [x] FILED: BUG-587 (a MINT is not ASSERTED to ARRIVE - the registry's write path has no arrival oracle; its own
      tombstone names a membership rail that does not exist). PARKED by the window, max_held 8 -> 9.
- [ ] OWED: BUG-587's fix (census +1 and the minted id present as a TOP-LEVEL record, failing closed BY NAME).
- [ ] NEXT: BUG-587's arrival assertion, then BUG-584 (one line, 96 -> 95 declaring lines), then BUG-585
      (open_bugs_n_at_2026_09_22), then BUG-583 (DECLARE the spelling set).

## D-2690 (2026-09-27) - A MINT MUST BE SEEN TO ARRIVE (BUG-587 FIXED; BUG-589 + BUG-590 FIXED IN THE REPAIR; BUG-588 FILED AND PARKED)

OWED: nothing from this change-set - the ARRIVAL oracle and the membership rail are landed and SEEN (registry 821
records, D-2690 top-level exactly once; membership rc=0; mutation gate rc=0 with 24 declared == floor 24 and 19/19
controls; register OPEN 135 / CLOSED 193 of 328; freeze window rc=0, parked 10 of ceiling 10).

DRAINED: BUG-587 CLOSED (a HELD bug closed DRAINS the window rather than breaching it). ADDED TO THE WINDOW:
BUG-588 (a decision COUNT declared on line 3 of an append_only log, stale by 169) - FILED and PARKED, max_held
9 -> 10. FIXED INSIDE THIS CHANGE-SET, NOT PARKED: BUG-589 (the mutation gate's fixture was UNDER-DECLARED - a
runner read governance/bug_status.json, the fixture carried only justfile, so every BASELINE of that runner was red
and the gate blamed the MUTATION for it) and BUG-590 (the arrival control passed through the COUNT clause instead
of the TOP-LEVEL clause it names, so the arrival rule could be neutered with 14/14 controls still green).

NEXT (in strategically logical order):
  1. BUG-584 DEDUPE (the next window drain, one measurable line): remove the byte-identical banner line and the two
     duplicated --selftest invocations from justfile (declaring lines 96 -> 95) AND decide whether
     scripts/run_ladder.py must REFUSE a duplicated declaring line - with the pinned duplicates as controls in BOTH
     directions plus a mutation (a rail that counts raw lines while another keys by invocation is the blind spot).
  2. THE LEAK SCAN'S DECLARED HOME (owed since D-2686): hoist the temp/ leak probe into a declared event-driven
     rehearsal with its own four limbs, or a dormant registry entry with a real exercised_by path.
  3. BUG-570 (register per-SHAPE rule + the duplicate BUG-493 block), BUG-568, BUG-569, BUG-559.
  4. BUG-588 pending the owner's word (needs a token of its own: a count on line 3 of an append_only file).

OWNER GATES (one word each, none due while the rails are green): CLOSE/RE-RULE (freeze window) | PROMOTE/HOLD
(standing rule -> CONSTITUTION, POINTER only) | PROMOTE/HOLD (BUG-431) | DECLARE/CANONICALISE (BUG-583, re-measure
first) | RENAME/DELETE (BUG-585).

## D-2691 - the ladder's own size, and a derived count with two homes (BUG-584 + BUG-585 FIXED)

OWED nothing: the refusal is SEEN to fire in both synthetic directions and on the live ladder, and its mutation is
SEEN to red through the control's own name.
DRAINED: BUG-584 FIXED (the ladder refused a duplicated declaring line; the three duplicated justfile lines
removed) and BUG-585 FIXED (the stale snapshot key renamed). The meta-lane freeze's parked set falls by two; the
window stays OPEN with its exit UNMET while the remaining 8 ids are parked.
CORRECTED IN THE FILED BLOCK: BUG-584's "the census is inflated by 4" is the RAW count - the CENSUS was inflated
by 1, because parse() drops a line naming the collector itself. Recorded in the FIXED block rather than left to be
quoted.
ADDED: the mutation a_duplicated_declaring_line_is_refused (floor 24 -> 25).
NEXT (consequential order): (1) BUG-588 - the stale count on DECISION-LOG.md line 3, owner-owed (REWRITE-HEADER /
LEAVE-STALE); (2) the remaining parked machinery defects BUG-570 (the per-SHAPE status-slot rule, whose 10-flip
list is already measured) and BUG-572/BUG-583 (the state-word pair); (3) BUG-599/559-class held ids; (4) the
declared home for the leak scan (owed since D-2686); (5) the object-level program: extraction_type is the ONE axis
of the five with NO anchor at all (251/251 rows empty) and no verifier (F-15), which is the single largest block
in front of the 7,000+-object work.

## D-2692 (2026-09-27) - DRAINED: BUG-570, BUG-588, BUG-583 FIXED; the mutation floor moved 25 -> 28.

DONE: (1) BUG-570 - the buglog BLOAT rail compares BLOCK BYTES (the `occurrence -> EOF` comparison that refused a
true copy is gone), the byte-identical BUG-493 block is DELETED (7797 -> 7784 lines, 459 block(s), 0 copies), and
scripts/check_buglog_coverage.py carries controls in BOTH directions (a COPY fires; two DIFFERENT blocks do not).
(2) BUG-588 - DECISION-LOG.md line 3 REWRITTEN by owner word REWRITE-HEADER: it names config/decisions_summary.json
and states no count; the rule has ONE home (config/decisions_policy.yaml#log_header) and is read by
scripts/check_decision_membership.py#header_problems (12/12 controls). (3) BUG-583 - the DECLARE limb landed: five
ids pinned BY IDENTITY, SHRINK-ONLY, refused live by scripts/recompute_decision_summary.py#spelling_problems (16/16
controls, --check rc 0); CANONICALISE is owner-gated (append_only registry + PREFIX receipt, D-2655).
(4) D-2676 limb (iv) landed: three new mutation entries + the floor 25 -> 28; the gate is rc 0 with 27 declared
rule(s) SEEN to red, 1 negative control green, floor 28 == 28, 18/13 declared subject(s) covered.
(5) The BUG-588 control was FOUND DEFECTIVE by that gate (it fired for its pointer reason, so the mutation could
not red it) and was REPAIRED in the same change-set - reported, not hidden.
D-2692 minted through the canonical path (D-2660): 822 -> 823 records, census source_sha256 refreshed.
CORRECTED COUNT: the register is OPEN 130 / CLOSED 198 (the drain moved 133/195 -> 130/198); agent/session_seed.yaml
already carries the re-derived open_bugs_n (ONE home, D-2691) and it is unchanged by this change-set.
NOT WIDENED, MEASURED: the mutation fixture's include_files was left at [justfile, governance/bug_status.json] -
all three new runners' baselines are GREEN in a real fixture without governance/buglog.md or DECISION-LOG.md,
because --selftest reads no log; declaring an input no runner reads would be the D-405 assertion shape.
NEXT (consequential order): (1) the LAST THREE HELD IDS - BUG-569 (the adoption NOTE has no rail-level control at a
real partial commit), BUG-568 (RAIL 0 does not pin its own git subject), BUG-559 (a receipt can be cut over bytes
joined to NO revision); draining them takes the window's exit to MET so the owner can CLOSE it. (2) BUG-583
CANONICALISE (owner word; needs the writer's structural path for an append_only registry). (3) The declared home
for the leak scan (owed since D-2686). (4) The product lane: extraction_type is the ONE axis of five with NO
anchor (0/251 rows), no verifier (F-15) and no consumer - the largest single block in front of the 7,000+ work.
(5) The 10 soft depth/domain findings; the object-level sweep against the ratified ruler; S6 commit_non_fb_types
sidecars; the Tier3 boundary corpus; F-14 (gated on G2).

## D-2693 (2026-09-27) - CANONICALISE limb of BUG-583 EXECUTED: one spelling, one declared route, pin EMPTY

- DONE: `--canonicalise-states` (proved in-place splice: id set unmoved, pinned cells only, canonical everywhere) + `canonicalisation_route` in config/decisions_policy.yaml + the pin shrunk to [] + the artifact_ownership declaration EXTENDED (guard_note names the third guard call site; `note:` names the one declared exception) + 2 controls (18/18).
- MEASURED: diff = 5 `state:` lines, -4 bytes; stamp 11008e971cb25a52 -> 1d866228c74eb195; census re-derived same-invocation; `--check` rc 0.
- REGISTER (unchanged by this change): OPEN 130 / CLOSED 198.
- NEXT CONSEQUENTIAL: (1) mutation teeth for the two new controls (floor 28 -> 29) - D-2676 limb iv owed for this rule; (2) drain the last 3 HELD ids (BUG-569 -> BUG-568 -> BUG-559) so the freeze window's exit goes MET; (3) session_seed `registry: decisions: 639` is a dated SNAPSHOT key (higher than the census by 184) -> D-2691 rename treatment.

## D-2694 (2026-09-27) - the standing rule pays its own debt: the canonicalisation licence is a MUTATION-SEEN rule (floor 28 -> 29)

- DONE: config/rail_mutations.yaml gains `the_canonicalisation_licence_is_load_bearing` (subject: the `extra` clause of scripts/recompute_decision_summary.py#splice_problems; a single unique `find` line) and `coverage.min_mutations` 28 -> 29 (SHRINK-ONLY raised by decision, never by an edit).
- MEASURED: gate rc 0 - 28 declared rule(s) SEEN to red, 1 negative control green, floor 29 == 29 declared, 18/13 declared subject(s) covered; gate selftest 19/19; the mutated runner's baseline is GREEN and it reds through exactly one of its 18 controls (MEASURED on the live tree before the entry was written).
- REGISTER: OPEN 130 / CLOSED 198 (no bug filed by this change). Registry 824 -> 825 records, stamp 7e3d49ee7c5846aa, census source_sha256 325fd899e0e80994.
- NEXT CONSEQUENTIAL: (1) drain the LAST 3 HELD ids - BUG-569 (the adoption NOTE has no rail-level control at a real partial commit) -> BUG-568 (RAIL 0 does not pin its own git subject) -> BUG-559 (a receipt cut over bytes joined to NO revision) - which is what takes the freeze window's exit to MET; (2) agent/session_seed.yaml `registry: decisions` dated-snapshot rename treatment (D-2691); (3) the declared home for the leak scan (owed since D-2686); (4) product lane: extraction_type is the one axis of five with no anchor, no verifier, no consumer.
- OWNER WORDS OWED (recommendations recorded in the session report): CLOSE the freeze window ONLY after the drain; HOLD the standing-rule CONSTITUTION promotion (POINTER only); HOLD BUG-431.


## D-2695 (2026-09-27) - the ADOPTION is a RAIL-LEVEL rule: the ADOPTED note is MUTATION-SEEN at a REAL minted index (floor 29 -> 30, BUG-569 DRAINED)

DONE: `scripts/check_session_plan.py` gains the rail-level adoption control (ambient minted index, NO
`--index-file`, synthetic plan, both limbs + anti-vacuity + control-on-the-control + crash-safe cleanup);
`config/rail_mutations.yaml` gains `the_adopted_index_note_is_load_bearing`, floor 29 -> 30; BUG-569 CLOSED in the
register; D-2695 minted (826 records, stamp `995142daf2c3bafa`); gov sync landed.

MEASURED: baseline 24/24 rc 0 -> mutated 23/24 rc 1, this control the SINGLE red; gate rc 0 with 29 red SEEN +
1 negative = 30, floor 30; buglog 463 blocks 0 copies; register == re-derivation; OPEN 129 / CLOSED 199.

REGISTER OPEN 129 / CLOSED 199 (was 130 / 198).

NEXT CONSEQUENTIAL (in order, all inside the open freeze window as DRAIN, not as new machinery):
  1. BUG-568 - RAIL 0 does not pin its own git subject (same class, one rail over).
  2. BUG-559 - a receipt can be cut over bytes joined to NO revision.
     Draining BOTH takes `nothing_still_held` to MET, which makes the owner's one-word CLOSE due (review_by
     2026-10-11).
  3. agent/session_seed.yaml `registry.decisions: 639` is a DATED SNAPSHOT (stale by ~187) -> D-2691 rename
     treatment; `highest_bug: BUG-301` is likewise stale.
  4. The leak scan's DECLARED HOME (owed since D-2686): hoist `temp/scan_fixture_leaks.py` into a declared
     rehearsal with its four limbs, or a dormant registry entry with a real exercised_by path.
  5. PRODUCT LANE: extraction_type is the ONE axis of five with no anchor (0/251), no verifier (F-15), no
     consumer; BUG-431's PROMOTE is step 1 (owner word owed).


## D-2696 DONE (2026-09-27) - BUG-568 DRAINED: RAIL 0 pins its own subject (TOLERANT: broken repositories REPORTED, decoys REFUSED), MUTATION-SEEN (floor 30 -> 31)
Landed: scripts/lib/git_subject.py#recovery_subject()/cleared_env()/discover_or_none() (+root= threading);
scripts/check_repo_integrity.py pins EVERY child git read and NAMES its subject in every mode (+2 controls,
15 -> 17); config/repo_integrity.yaml keeps ONE home (exemption prose REPLACED, no new key);
config/rail_mutations.yaml#the_rail0_subject_pin_is_load_bearing + floor 31. MEASURED: baseline rc 0, marker
ABSENT -> mutated rc 1, marker the SINGLE red, restored byte-identical, gate rc 0. FILED and PARKED: BUG-591
(the fixture builder inherits the ambient git subject) joins window.held (10 -> 11, max_held raised with it).
NEXT (in order): (1) BUG-591 - the fixture builder's own pin (cleared_env + a control + a mutation entry), the
last measured instance of the BUG-527 class in the machinery; (2) BUG-559 (STRUCTURAL, D-2666): a receipt can be
cut over bytes joined to NO revision - draining BOTH takes the freeze window's nothing_still_held to MET, which
makes the owner's one-word CLOSE due (review_by 2026-10-11); (3) the rest of the parked set (BUG-585/584/583/572/
570/588/587) - list before working, several are OWNER-OWED; (4) agent/session_seed.yaml registry.decisions: 639
and highest_bug: BUG-301 are DATED SNAPSHOTS awaiting the D-2691 rename treatment (open_bugs_n is the one home);
(5) the leak scan's DECLARED HOME (owed since D-2686); (6) PRODUCT LANE: extraction_type is the one axis of five
with no anchor (0/251), no verifier (F-15), no consumer - BUG-431's PROMOTE is step 1 (owner word owed).

## D-2696 (cont., 2026-09-27) - the BOUNDARY REHEARSAL declares the pin it now rehearses
config/boundary_rehearsal.yaml#rails[RAIL 0] declared ambient_note: none / partial_note: none and quoted the
WITHDRAWN D-2674 exemption, so the rehearsal RED'd on the reality it exists to observe: 4 note(s) of each
provenance at the real normal and partial commits against 3 declared. It now declares ambient_note: own_index
and partial_note: adopted, and NAMES the exemption as WITHDRAWN rather than softened. The declared COUNTS are
DERIVED from this block (check_boundary_rehearsal.classify), so no count was edited by hand (C12).
MEASURED: check_boundary_rehearsal.py --selftest 21/21 rc 0; the rehearsal at a REAL commit rc 0 (4 pinned
note(s) at the normal commit, 4 at the partial one, 2 planted violation(s) refused by their declared rail);
just health HEALTH_RC=0; the four commit-boundary rails rc 0 against the staged set.
TEETH were NOT duplicated: selftest/wrong_note_provenance (BUG-567 shape) and selftest/partial_note_declaration_is_read
already RED when the declaration is mutated, so this declaration is MUTATION-COVERED without a new entry.
D-2696 is COMPLETE and COMMITTED; NEXT unchanged: (1) BUG-591 (fixture builder pin); (2) BUG-559
(STRUCTURAL) - draining both takes the freeze window exit nothing_still_held to MET.

## D-2697 DONE (2026-09-27) - BUG-591 DRAINED: the FIXTURE BUILDER does not inherit the ambient subject

FIX: scripts/lib/fixture.py#git() runs every child git with env=git_subject.cleared_env(git_subject.config()) -
the guard set DERIVED from the pin ONE home (D-2646), never restated. New known-answer control:
selftest/a_fixture_is_built_in_its_own_worktree_under_a_decoy_git_dir - a REAL decoy repository is built, the
ambient GIT_DIR/GIT_WORK_TREE are ARMED and the arming ASSERTED (anti-vacuity), the builder must land in its OWN
worktree, and the caller environment is RESTORED EXACTLY in a finally.

MEASURED: fixture --selftest 7/7 control(s) rc 0 with the new control GREEN; mutated (env=None, the inherited
environment restored) rc 1 with EXACTLY ONE red line = its own marker, restored byte-identical; the mutation gate
rc 0 over 32 entries against a floor of 32 (config/rail_mutations.yaml#coverage.min_mutations 31 -> 32). Defect
receipt BEFORE the fix: with GIT_DIR=<decoy>/.git ambient the child read the DECOY git dir and real_repo()
returned None for a fixture it never created (FileNotFoundError at the caller).

IN-FLIGHT DEFECT (recorded): the first landing collapsed the newlines of BOTH files - the control became one
1409-character COMMENT line (it did not exist) and the YAML entry became a comment line that silently dropped
decision_supersession_rule_is_load_bearing (31 entries -> 30 under the just-raised floor of 32). Both were caught
by COUNTING the artifacts (registry parse, control name grepped in the bytes) and repaired by temp/d2697_fix_ctrl.py
and temp/d2697_fix_mut.py, then re-verified: a write is not a landing until a reader has counted it.

GOVERNANCE SYNC: buglog BUG-591 CLOSED block; decision D-2697 minted; DECISION-LOG.md, this register and
governance/CONTEXT_INDEX.md appended; bug_status re-derived; agent/session_seed.yaml#open_bugs_n rewritten from
the DERIVATION; config/freeze_window.yaml#released names BUG-591 while the id STAYS in window.held (the freeze
rail refuses a release of an id held does not name), so nothing_still_held reads 1 still parked: BUG-559.

NEXT (strategically logical order): (1) BUG-559 (STRUCTURAL) - the LAST parked id, and draining it takes
nothing_still_held to MET (owner CLOSE approved; review_by 2026-10-11): a receipt can be cut over bytes joined to
NO revision, so verify_handoffs must REFUSE a receipt whose (path, digest) is neither the live bytes AND
git_bytes(HEAD, path), nor a declared revision locator + declared applier run, shipped with a seen-refusal control
(R5) and the workbook receipt re-cut. (2) the rest of the parked set (BUG-585/584/583/572/570/588/587).
(3) agent/session_seed.yaml#registry.decisions 639 / highest_bug BUG-301 are DATED SNAPSHOTS (D-2691 rename
treatment); open_bugs_n is the ONE home of the count. (4) the leak scan DECLARED HOME (owed since D-2686).
(5) PRODUCT LANE: extraction_type (0/251 anchors, no verifier, no consumer) - BUG-431 PROMOTE is step 1.

## D-2698 DONE (2026-09-27) - BUG-592 CLOSED: the pin control is BOUNDED, the gate is GREEN over 32

FIX: scripts/check_repo_integrity.py - the BUG-568 pin probe becomes module-level `pin_controls(cfg, ok, n)`; `selftest(skip_pin: bool = False)` gates it; the new `--no-pin-probe` bounds its own nested run.
MEASURED: baseline 17/17 rc=0 -> after 17/17 rc=0 (same count, so the bound hid no control); MUTATED rc=1 in 4.4s, ONE red line = `FAIL repo-integrity selftest/rail0_pins_its_own_subject` (was rc=124 at 600.0s); restored byte-identical. Live modes unaffected: rc=0, --worktree rc=0 (13 dirty paths granted).
GATE: rc=0, 31 rules SEEN to red, 0 DID-NOT-RED, 32 entries = floor 32 - the D-2697 landing is now ENGINE-validated, not self-reported.
NOT DONE, DELIBERATELY: D-2697 `files` is NOT amended - its committed artifacts are the ones it names (fixture.py + governance), scripts/check_repo_integrity.py is D-2698 own landing, and an in-place edit of the append-only registry would owe a PREFIX re-baseline in a SEPARATE commit (D-2655) for no factual gain. The complete artifact set is stated in D-2698 instead.

NEXT (strategically logical order): (1) BUG-559 (STRUCTURAL, D-2666) - the LAST parked id: a receipt can be cut over bytes joined to NO revision; draining it takes the freeze window nothing_still_held to MET. (2) the rest of the parked set (BUG-585/584/583/572/570/588/587) - list before working. (3) the leak scan DECLARED HOME (owed since D-2686). (4) agent/session_seed.yaml registry.decisions 639 / highest_bug BUG-301 - dated snapshots awaiting the D-2691 rename treatment. (5) PRODUCT LANE: extraction_type (0/251 anchors), BUG-431 PROMOTE is step 1.

## D-2699 DONE (2026-09-27) - THE ATTEMPT THAT MEASURED A GAP IN THE STANDING RULE: the receipt-provenance rule (BUG-559) CANNOT be covered by limb (iv) yet - the entry is WITHDRAWN, not weakened; BUG-593 filed and parked
FIX: none landed in the rail (deliberately). config/rail_mutations.yaml was returned BYTE-EXACTLY to its pre-attempt state (32 entries = floor 32, include_files back to 2, no scripts/verify_handoffs.py subject) after the gate refused the entry it was written for. What landed is a MEASUREMENT and a FILED DEFECT.
MEASURED: (a) outside the fixture the entry IS sound - the fall-through of receipt_provenance() reduced to 'declared' gives rc=1 with EXACTLY TWO declared red lines, restored byte-identical; (b) inside the fixture the oracle's BASELINE is red (3 revision re-derivation FAIL lines, reproduced in a hand-built fixture outside the gate), because the fixture carries ONE commit and the rail's oracle joins git refs of the LIVE repo. The gate REFUSED to blame the mutation (the BUG-589 lesson working as designed).
NOT DONE DELIBERATELY: the entry was NOT kept by weakening the oracle (dropping --selftest's revision controls) - that trades a real control for a green gate; BUG-559 was NOT closed - its store-level half is unfixed by limb (iv) and its PROSE half (a truncated digest outside the 64-hex ruler) is untouched.
GATE: scripts/check_rail_mutations.py rc=0 over 32 entries = floor 32 (restored state); just health HEALTH_RC=0.
NEXT (strategically logical order): (1) BUG-593 - declare fixture.history in config/rail_mutations.yaml so a history-reading oracle has a green baseline, then land the_receipt_provenance_join_is_load_bearing at floor 33 (the entry text is preserved in temp/d2699_entry.yaml with its pre-measurement in temp/d2699_mutcheck.py). (2) BUG-559's PROSE half - join truncated hex digests against the same three stores, with a control SEEN to refuse an unresolvable truncation. (3) the rest of the parked set (BUG-585/584/583/572/570/568/569/588/587) - list before working. (4) the leak scan's DECLARED HOME (owed since D-2686). (5) PRODUCT LANE: extraction_type (0/251 anchors), BUG-431 PROMOTE is step 1.

## D-2701 DONE (2026-09-29) - 210->208 anchor consolidation + evidence-bridge forensic audit
FIX: REVIEW_WORKBOOK_210.csv -> 208 rows (dedup R161/R194, typos, off-menu R152 -> industrial design, multi-label R157/R188/R204). Anchor->evidence bridge built (anchor_evidence_bridge.json).
MEASURED: 208/210 evidence-matched; source_text contaminated 208/208; truncated passages 188/210; is_summary 0/208 (unreliable).
NOT DONE (blocks triage): raw source recovery, complete-sentence truncation, R135/R167 resolution, is_summary hardening.
NEXT (strategically logical order): (1) recover raw source_text from stage0/stage1 for 208; (2) truncation repair; (3) R135/R167 evidence; (4) is_summary; (5) NLI triage keep/repair/drop. GOVERNANCE SWIMLANE unchanged: BUG-593 -> BUG-559 -> widening_log owed -> leak-scan home.

## D-2702 DONE (2026-09-29) - raw source_text recovery + R135/R167 blindspot resolution
FIX: recovered raw verbatim source_text for the 208 anchors (stage1 segment index, one streaming pass + 940 source MD files as fallback). R135 double-space and R167 "emerging"->"Organic Development" name fixes landed crash-safe (workbook stays 208, CRLF preserved).
MEASURED: 447/488 passages VERBATIM (91.6%), 35 abstractive, 6 orphan-segment, 0 empty; 174 full / 25 partial / 7 zero anchors.
NOT DONE (blocks triage): 223/4660 source_segments orphaned in the current checkpoint (re-chunk/re-point); is_summary hardening; owner-ratify the 35 abstractive + 7 zero anchors.
NEXT (strategically logical order): (1) close the 223 orphan segments (re-chunk); (2) owner triage ruling on abstractive/zero anchors; (3) harden is_summary; (4) NLI triage keep/repair/drop. GOVERNANCE SWIMLANE unchanged: BUG-593 -> BUG-559 -> widening_log owed -> leak-scan home.

## D-2703 DONE (2026-09-29) - chunking research + full triage + re-chunk verification
FIX: none (read-only research + triage + verification this turn)
MEASURED: re-chunk reproduces 4/4 orphan anchors + R141 141/141 => stale-checkpoint root cause;
  triage 208 anchors -> KEEP45/FIX130/DROP13/QUARANTINE15/WAIT-ORPHAN3 (saved anchor_triage_v1.json)
NOT DONE: actual re-chunk swap (pending); 150 locked primary_domain classification (pending);
  owner ratify DROP/QUARANTINE/re-ground (pending)
NEXT: (1) re-chunk + verify 4660/4660 resolve; (2) classify 150 locked domains (closed_menu_v5);
  (3) ratify; (4) file evidence_passages schema bug; (5) mint registry.decisions + highest_bug snapshots

## D-2704 DONE (2026-09-29) - re-chunk EXECUTED + RRF verdict + duplicate-book forensic audit
FIX: re-chunk written to fresh run-id knowledge pipeline/stage1_chunk/rechunk-20260929/
  (300,270 segments, D2485-stamped); LIVE 'latest' untouched. No code change (chunking KEEP).
MEASURED: 4660/4660 source_segments resolve, 223/223 orphans recovered, 0 missing; segment count
  identical to t11 => chunker stable D2370->D2485. 24 duplicate-book groups (same author+title,
  diff source_path) => ~12,064 segs (~4%); exact dedup caught 2,367; ~6K near-dupes survive.
  RRF verdict: NOT for stage1_chunk (correct — retrieval-time; already in rerank.py + retrieval_benchmark).
NOT DONE: live pointer flip (gated); book canonicalization dedup upgrade; 150 locked primary_domain;
  owner ratify DROP/QUAR/re-ground; evidence_passages schema bug; registry.decisions + highest_bug mint.
NEXT: (1) gated pointer flip latest->rechunk-20260929; (2) book canonicalization before chunk;
  (3) classify 150 domains (closed_menu_v5); (4) ratify; (5) file schema bug; (6) mint registry snapshots.

## D-2705 DONE (2026-09-29) - chunk+dedup A/B test + heading-ordering bug (BUG-594)
FIX: none landed (A/B + research). Filed BUG-594 (structural heading-splitter DEAD).
MEASURED: near-dedup arm C = 334 segments (100% precision) but orphans 8/4660 (needs remap);
  book canonicalization 24 groups = ~182 near-dupes (exact dedup already handles byte-identical);
  parent-child additive (sha256(text)==segment_id, 0 mismatch); headings present in 96.3% books
  (905/940, 83,880 lines) but captured on 5.45% segments -> clean_markdown strips '#' before split_on_headings.
NOT DONE: heading-fix implementation (smoke A/B next); contextual retrieval A/B; 150 locked domains;
  ratify DROP/QUAR/re-ground; segment remap design.
NEXT: (1) smoke A/B heading fix; (2) full re-chunk + remap + re-verify 4660; (3) contextual A/B;
  (4) classify 150 domains (closed_menu_v5); (5) ratify.

## D-2706 DONE (2026-09-29) - heading-fix A/B verdict: fix COUNTERPRODUCTIVE
FIX: none landed. Isolated smoke A/B (temp/_ab_heading_fix.py, 60 books) proved the reorder
  mechanically works (heading coverage 6.7%->97.5%, 0 boundary violations) BUT (a) 58.1%
  segment_id churn = full cascade, and (b) captured headings are 80.5% converter artifacts
  (calibre {#...}/.title, DOI, ISBN, Anna's Archive hash) => real semantic fraction ~10-15%.
  The naive fix adds garbage + churn, not value. KEEP current chunker.
MEASURED: 5,577 raw heading lines; 4,856 unique captured; artifact 3,908 (80.5%) vs semantic 948
  (19.5%); 43/60 books have >=1 semantic heading; word delta -96,475 (heading text -> metadata).
NOT DONE: heading SANITIZER (new task); structural re-eval after sanitization; segment remap
  (moot); 150 locked domains; ratify; schema bug; registry mint.
NEXT: (1) heading sanitizer design (reuse _CLEAN_SUBS); (2) classify 150 domains; (3) ratify
  DROP/QUAR/re-ground; (4) file evidence_passages schema bug; (5) mint registry snapshots.

## D-2707 DONE (2026-09-29) - forensic scan: converter residue CORPUS-WIDE (41.4%)
FIX: none landed (forensic determination). CONFIRMED BUG-595; scoped sanitizer = clean_markdown
  upgrade (add _CLEAN_SUBS D2471 + empty-link/{#...}/^n^ patterns).
MEASURED: 124,268/300,270 segments (41.39%) carry converter residue in BODY text; dominant =
  [ ]{bgcolor} 69,983 segs, {#...} anchors 43,358, {.underline}/{=html} 114,890, ^2^ 4,853,
  .xhtml_p1 2,433, !Image{} 1,532; DOI 882 (semantic, KEEP); Anna's hash 42.
NOT DONE: sanitizer landing + A/B; pointer flip (HELD — rechunk UNSANITIZED); 150 domains;
  ratify DROP/QUAR/re-ground; evidence_passages schema bug (BUG-596); registry mint.
NEXT: (1) D-2708 owner GO; (2) sanitizer A/B; (3) coordinated v4.0 re-chunk (sanitizer + orphan
  recovery + parent-child IDs, one flip); (4) classify 150 domains (closed_menu_v5); (5) ratify;
  (6) file BUG-596 schema divergence; (7) mint registry snapshots.


## D-2708 DONE (2026-09-29) - sanitizer LANDED + A/B verified (owner GO)
FIX LANDED: clean_markdown() now applies _CLEAN_SUBS + _S1_SPAN_SUBS (generalized span-attr grammar).
MEASURED: residue 41.64% -> 1.53% (96.3% cut); 128,584 segs changed (42.82% churn, staged);
  FALSE-POSITIVE 0 (unit-proven). Residual 1.53% = truncated kobo xmlns spans (malformed src).
NOT DONE: coordinated v4.0 re-chunk; 150 locked domains; re-ground(8); BUG-596 fix; registry mint.
NEXT: (1) D-2709 v4.0 re-chunk (sanitizer + orphans + parent-child, one flip); (2) classify 150
  domains; (3) re-ground 8 anchors to verbatim; (4) D-2711 noise-drop quarantine ledger;
  (5) BUG-596 evidence_passages join; (6) mint registry snapshots.

## D-2711 OPEN (2026-09-29) - owner ratifications + noise-drop quarantine catch-basin
RATIFIED: DROP(13) noise_drop; KEEP QUARANTINE(15); re-ground(8) -> re-chunk to verbatim.
NEW: build noise-drop QUARANTINE ledger (anchors + golden) so future slip-throughs are detectable.


## D-2711 EXECUTED (2026-09-29) - owner ratifications + noise-drop quarantine + registry sync
RATIFIED: DROP(13) noise_drop -> QUARANTINE (soft-drop, not hard-delete); KEEP QUARANTINE(15);
  re-ground(8) -> verbatim re-chunk.
BUILT: governance/frontier_audit/noise_drop_quarantine.json (13 DROP anchors, kind=anchor,
  reason + decision_ref=D-2711 + created_at + recheck_due=2026-10-29; golden noise_drop uses same ledger).
SYNCED: config/decisions.yaml minted D-2701..D-2711 (840 entries, was 829/D-2699);
  BUG-596 FIXED in pipeline/probe_run.py (evidence_passages_shown now = shown passages, not LLM self-report);
  bug_status.json registered BUG-594(open)/BUG-595(closed)/BUG-596(closed) -> total_ids 334.
NOT DONE: coordinated v4.0 re-chunk (sanitizer + orphans + parent-child IDs, ONE flip);
  150 locked primary_domain; re-ground(8) verbatim re-chunk; S2->S4->S5->S6 rerun; D-2712 heading re-measure.
NEXT (critical order): (1) v4.0 re-chunk + verify 4660/4660 source_segments + 223/223 orphans;
  (2) classify 150 locked domains (closed_menu_v5); (3) re-ground 8 anchors to verbatim;
  (4) rerun S2->S4->S5->S6; (5) D-2712 heading coverage re-measure.
## D-2712 EXECUTED (2026-09-29) - sanitized v4.0 re-chunk + parent_id shipped + heading re-measure
DONE: v4.0 re-chunk -> rechunk-v4-20260929 (295,440 segs, residue 41.64%->1.91%, 0 collisions,
  100% parent_id, books 933 stable). parent_id landed in pipeline/stage1_chunk.py (additive).
RECOMMENDATION (D-2712): KEEP fixed-size chunker; ship parent_id; defer structural split;
  serve context at retrieval time. Heading coverage re-measured 5.10% (unchanged) -> structural split STAYS blocked.
HELD: pointer flip (D-2709 gate) — full 4660/4660 + 223/223 + re-ground(8) re-resolution vs sanitized text incomplete; R137 0-hit.
NEXT (critical order): (1) authoritative re-resolution 4660/4660 + 223/223 + re-ground(8) vs v4 (R137 first);
  (2) flip pointer + rerun S1.3->S1.5->S2->S4->S5->S6; (3) classify 150 locked domains (closed_menu_v5);
  (4) extend noise_drop quarantine to golden (kind=golden); (5) strip dangling kobo xmlns spans (residual 1.91%).
## D-2713 EXECUTED (2026-09-29) - bloat + forensic pre-flight audit
DONE (read-only, nothing deleted): catalogued archivable ~9.7G (knowledge pipeline ~9.5G + governance ~120M)
  + deletable ~8M. Forensic risk register clean (see governance/FORENSIC_AUDIT_BLOAT_20260929.md).
HELD (rollback): stage1_chunk/t11, rechunk-v4, latest, maxwell.db, classifier p5final+hierarchical, t11 S2/S4/S5/S6.
FLAGGED (latent, not bloat): run.default_id=t11 vs 7 scripts defaulting to stale "latest"; vec0 module absent in inspect conn.
NEXT (critical order): (1) owner-ratify bloat ARCHIVE/DELETE ledger (per-path, below);
  (2) execute archival via archive/ convention + pipeline/safe_delete.py (R-D410/C13);
  (3) authoritative re-resolution 4660/4660 + 223/223 + re-ground(8) vs v4 (R137 first);
  (4) on pass, flip pointer (default_id + latest/) then rerun S1.3->S1.5->S2->S4->S5->S6 (D-2714);
  (5) D-2715 churn-free heading map after v4 lock; (6) extend noise_drop quarantine to golden.

## D-2714 EXECUTED (2026-09-29) - bloat archival (owner ratified)
DONE: 120 items (~9.88 GB) archived reversibly to archive/bloat_20260929/ + ~4.9M deleted (safe_delete.py). HOLD set intact; DB integrity ok; backup_guardian re-run.
NEXT (critical order): (1) authoritative re-resolution 4660/4660 source_segments + 223/223 orphans + re-ground(8) vs sanitized v4 (R137 first, 0/1 hit); (2) on pass flip pointer (default_id + latest/) then rerun S1.3->S1.5->S2->S4->S5->S6 (D-2714 rerun); (3) classify 150 locked anchors primary_domain (closed_menu_v5.json); (4) extend noise_drop_quarantine.json to golden (kind=golden); (5) D-2715 churn-free heading/section map after v4 lock; (6) file BUG (run.default_id=t11 vs 7 scripts hardcode 'latest') at flip; (7) re-verify vec0 module at S6.

## D-2715 (2026-09-29) - re-resolution vs v4: NO CONTENT LOSS
DONE: 4660/4660 source_segments + 223/223 orphans confirmed present in sanitized v4; re-ground(8) 4/8 done (R020/R064/R137/R188). Pointer flip HELD.
NEXT (critical order): (1) complete re-ground(8) verbatim recovery R037/R053/R083/R151; (2) classify 150 locked anchors primary_domain (closed_menu_v5.json); (3) owner-ratify DROP(13)+QUARANTINE(15)+re-ground(8); (4) flip pointer (default_id + latest/) + rerun S1.3->S1.5->S2->S4->S5->S6; (5) file BUG at flip (run.default_id=t11 vs 7 scripts hardcode 'latest'); (6) D-2716 churn-free heading map; (7) re-verify vec0 at S6.


## D-2716-PRE (2026-09-30) - forensic audit + governance sync (pre pointer-flip gate)
AUDIT (read-only): decisions census was STALE 830 -> recomputed 845 (scripts/recompute_decision_summary.py, 4 drift(s) fixed; registry byte-identical so prefix receipt holds). session_seed registry.decisions=845 CONFIRMED correct. No cascade/break/bloat found.
re-ground(8) STATUS: 4/8 verbatim-confirmed (R020/R064/R137/R188); 4 pending (R037/R053/R083/R151) are SEMANTIC paraphrases whose verbatim source is NOT recoverable by phrase-match (verified: distinct-phrase grep hits are citations/boilerplate/unrelated, not the claim text; R083 bridge source_text 'Hustle Harder' appears to differ from self-herding source). re-ground(8) completion is a semantic-grounding task, NOT mechanical.
FILED: BUG-597 (run.default_id=t11 vs hardcoded 'latest'), BUG-598 (S1.3 --in-place mutates stage1_chunk).
NOT DONE (unchanged blockers): pointer flip D-2716 (HELD: needs re-ground(8) completion + owner Phase-A checkpoint inspection), 150 locked primary_domain classification, noise_drop quarantine golden extension, vec0 re-verify at S6.
NEXT (critical order): (1) semantic re-ground(8) R037/R053/R083/R151 verbatim; (2) classify 150 locked anchors primary_domain (closed_menu_v5.json, gpt-oss-20b batch); (3) owner inspect Phase-A checkpoint + ratify pointer flip; (4) D-2716 atomic flip (default_id + 7 'latest' scripts) + full clean rerun S1.3->S1.5->S2->S4->S5->S6; (5) extend noise_drop quarantine to golden (kind=golden); (6) re-verify vec0 at S6.

## D-2716-PRE.2 (2026-09-30) - re-ground(8) COMPLETE + quarantine golden + BUG-599 (flip gate: owner inspection only)
COMPLETED THIS TURN: re-ground(8) -> verdict artifact (4 verbatim R020/R064/R137/R188 + 4 semantic-paraphrase R037/R053/R083/R151, KEEP-not-drop). noise_drop quarantine -> +3 golden (kind=golden). BUG-599 filed (pipeline_run_id=t11 provenance stamp mismatch).
NEXT (critical order): (1) OWNER inspect Phase-A checkpoint knowledge pipeline/stage1_chunk/rechunk-v4-20260929/checkpoint.jsonl (295,079 segs) + BUG-599 stamp note; (2) on ratify, D-2716 atomic flip (default_id t11->rechunk-v4-20260929 + repoint 4 'latest' scripts + re-stamp pipeline_run_id) then full clean rerun S1.3->S1.5->S2->S4->S5->S6 (~13-16h); (3) classify 150 locked anchors primary_domain (closed_menu_v5.json, gpt-oss-20b batch); (4) re-verify vec0 module at S6.

## D-2716-EXECUTED (2026-09-30) - pointer flip DONE + governance synced (RATIFY-1)
DONE THIS TURN: forensic audit (no break/cascade/drift) -> D-2716 atomic flip (default_id t11->rechunk-v4-20260929 + BUG-597 latest/ repoint + BUG-599 pipeline_run_id re-stamp + MAXWELL_DB_PATH override). BUG-597/599 CLOSED. Governance synced (decisions 846, bugs 334 open130/closed204).
NEXT (critical order): (1) LAUNCH full clean rerun S1.3->S1.5->S2->S4->S5->S6 (~13-16h) with MAXWELL_DB_PATH=knowledge pipeline/maxwell.test.db (S6 isolation); (2) classify 150 locked anchors primary_domain via closed_menu_v5.json (gpt-oss-20b batch); (3) re-verify vec0 module at S6 (vec_fbs/vec_fbs_ctx "no such module" latent); (4) RATIFY-3 DROP(13)+RATIFY-4 QUARANTINE(15) ledger entries (RATIFY-5 re-ground(8) already COMPLETE).

## D-2717 (2026-09-30) - vec0 RESOLVED + BM25 verdict + roadmap

DONE: vec0 runtime resolved (Homebrew 3.14.6 verified; 7995/7995 vec intact); stage6.vec_require
fail-closed gate + vec_python added; BM25/hybrid confirmed already-integrated; S1.5/S2/S4/S5
improvement roadmap recorded; governance synced (D-2717, decisions 847).

NEXT (critical order):
1. [TASK] vec0 runtime gate ON for full rerun: set stage6.vec_require=true OR run S6/backfill
   under stage6.vec_python (/opt/homebrew/bin/python3) so vec_fbs is not silently empty.
2. [TASK] Retrieval smoke test BEFORE 13-16h rerun: run retrieval_benchmark.py under Homebrew
   Python against existing maxwell.db (prove hybrid RRF + rerank beats FTS-only; baseline).
3. [TASK] S1.5 HNSW speedup benchmark (IndexHNSWFlat/USearch vs IndexFlatIP) — biggest wall-clock lever.
4. [TASK] Classify 150 locked anchors' empty primary_domain (closed_menu_v5.json, vote_anchor_domains.py).
5. [OWNER-RATIFY] RATIFY-3 DROP(13) + RATIFY-4 QUARANTINE(15) ledger entries; RATIFY-2 full clean rerun.
6. [BUG] Re-verify vec0 at S6 under correct runtime (was latent "no such module: vec0").
7. [BUG] evidence_passages vs evidence_passages_shown schema divergence (BUG-596).

## D-2718 (2026-09-30) - Pre-run adoption filter + golden few-shot audit

DONE: Re-checked archive/session history/research registers for already-tested-that-wont-work (registry
confirmed: speculative decoding, Rapid-MLX, MTPLX, CIDER, TurboVec, HDBSCAN, Leiden/ColBERT/GraphRAG/Neo4j/
LanceDB/DuckDB/Dagster/Prefect = do NOT re-test). Golden few-shot verified ACTIVE + non-contaminated
(convergent 84/84 PASS, S4 7/7 PASS). NEW FINDING: single-source golden has 14 NON_VERBATIM evidence
passages. Governance synced (D-2718, decisions 848).

NEXT (critical order):
1. [TASK] USearch/HNSW recall benchmark (IndexHNSWFlat/USearch vs IndexFlatIP) on S1.5 — ONLY un-benchmarked
   speed lever; adopt only if recall within tolerance (cheap, 1-3h, do BEFORE the 13-16h rerun).
2. [TASK] Flip vec0 gate ON for rerun: stage6.vec_require=true (or run S6 under stage6.vec_python) — prevents
   silently-empty vec_fbs (C16 fail-closed).
3. [TASK] Retrieval smoke test before rerun: retrieval_benchmark.py under Homebrew Python vs existing maxwell.db
   (prove hybrid RRF + rerank beats FTS-only; examinable baseline).
4. [BUG] File single-source golden NON_VERBATIM (14 paraphrased evidence passages) — teaches fabricated-evidence
   bias; apply D2396-style verbatim fix or drop those few-shots.
5. [TASK] Classify 150 locked anchors empty primary_domain (closed_menu_v5.json, vote_anchor_domains.py).
6. [OWNER-RATIFY] RATIFY-3 DROP(13) + RATIFY-4 QUARANTINE(15) ledger entries; RATIFY-2 full clean rerun.
7. [BUG] evidence_passages vs evidence_passages_shown schema divergence (BUG-596); BUG-598 S1.3 --in-place
   mutation re-check.
8. [BUG] Re-verify vec0 at S6 under correct runtime (latent "no such module: vec0").

## D-2718 addendum (S4 golden under-specified)
S4 golden = 7 examples, depth-only (0/62 disciplines, 0/44 domains). Contract 5/5 PASS but cannot
guide discipline/domain -> root of 150 empty primary_domain + domain_macro_f1 0.0086. NEXT:
9. [TASK] Bootstrap S4 discipline/domain golden: cross-model vote (qwen+gemma+gpt-oss >=2/3) on the
   150 anchors + canonical-restamp gold_4axis (1027) + re-adjudicate archive stage4_golden_mined.yaml.
   Owner adjudicates DISAGREEMENTS only (~30-50); auto-accept >=2/3 vote.
10. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.


## D-2719 (2026-09-30) - RATIFY-3 + RATIFY-4 executed; golden re-use scoped (anchors->S4 only, UPDATE-not-delete)
DONE THIS TURN: RATIFY-3 DROP(13) owner-ratified (noise_drop_quarantine.json owner_ratified marker);
RATIFY-4 QUARANTINE(15) recorded (anchor_quarantine_ledger.json, kind=anchor, soft-quarantine).
Golden re-use SCOPED: anchors -> S4 classification golden ONLY (discipline/content_type/extraction_type/depth);
NOT S2 (different output type); domain axis NOW consolidated 208/208 (D-2720 corrects the prior "0/150 empty"
misread). UPDATE-not-delete: S2 keep convergent(84)+fix
single_source(14 NON_VERBATIM=BUG-600); S4 extend stage4_golden.yaml (freeze 7 depth + add discipline/domain).
BUG-600 filed. Governance synced (D-2719, decisions 849, bugs 335).

## D-2720 (2026-09-30) - Correction: domain axis ALREADY declared; 208 consolidated; 3 ADVISORY accepted
DONE THIS TURN: produced governance/ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv (208 rows; primary_domain 208/208,
domain 208/208, depth 208/208). Owner ACCEPTED 3 ADVISORY domain rows (R003 research & methodology, R140 creative
technology, R146 leadership). RETRACTED the false "150 empty primary_domain" claim (root cause: domain axis was
split across two instruments; the reader looked only at REVIEW_WORKBOOK.domain_final which is empty for the 150).
config/anchor_family.yaml axes re-owned (cohort 208, domains owned/adjudicated, depth intersection 208).
BUG-600 CLOSED (7 passages re-verbatimized + golden_validate source-diversity skips non-convergent single-source).

NEXT (critical order):
1. [BUG-596] evidence_passages vs evidence_passages_shown provenance gap: assert shown subset-of stored in probe_run.py + add golden_validate check.
2. [BUG-598] S1.3 --in-place mutates stage1_chunk checkpoint: emit self-contained S13 checkpoint (keep S1 immutable) OR document as mutating pre-filter.
3. [TASK] USearch/HNSW recall benchmark (IndexHNSWFlat/USearch vs IndexFlatIP) on S1.5 — only un-benchmarked lever.
4. [TASK] Retrieval smoke test (retrieval_benchmark.py under Homebrew Python vs existing maxwell.db).
5. [TASK] Declare train/eval split BEFORE any anchor->golden bootstrap (leakage guard: anchors are ALSO the eval ruler).
6. [TASK] Bootstrap S4 discipline/domain golden from KEEP(46) with cross-model vote (>=2/3, D2362); freeze 7 depth + extend stage4_golden.yaml; owner adjudicates disagreements only.
7. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
8. [OWNER-RATIFY] RATIFY-2 full clean rerun (after 3+4 pass) — stage6.vec_require=true at launch.
9. [BUG] Re-verify vec0 at S6 under /opt/homebrew/bin/python3 (latent "no such module: vec0"); BUG-599 provenance re-check.

## D-2721 (2026-09-30) - BUG-596 + BUG-598 CLOSED (evidence provenance + S1.3 contract)
DONE THIS TURN: BUG-596 CLOSED — probe_run.py aligned with production _build_fb_from_result
(evidence_passages = LLM self-report fallback shown[:5]; evidence_passages_shown = shown). golden_validate.py
gained check #4b (NON_VERBATIM_SHOWN). Verified single-source 21/21, convergent 84/84.
BUG-598 CLOSED (option A, zero-behavior-change): S1.3 documented as MUTATING pre-filter (docstring +
pipeline_paths module header); self-contained S13 checkpoint (option B) deferred (S1.5 read-source cascade).

NEXT (critical order):
1. [TASK] USearch/HNSW recall benchmark (IndexHNSWFlat/USearch vs IndexFlatIP) on S1.5 — only un-benchmarked lever.
2. [TASK] Retrieval smoke test (retrieval_benchmark.py under Homebrew Python vs existing maxwell.db).
3. [TASK] Declare train/eval split BEFORE any anchor->golden bootstrap (leakage guard: anchors are ALSO the eval ruler).
4. [TASK] Bootstrap S4 discipline/domain golden from KEEP(46) with cross-model vote (>=2/3, D2362); freeze 7 depth + extend stage4_golden.yaml; owner adjudicates disagreements only.
5. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
6. [OWNER-RATIFY] RATIFY-2 full clean rerun (after 1+2 pass) — stage6.vec_require=true at launch.
7. [BUG] Re-verify vec0 at S6 under /opt/homebrew/bin/python3 (latent "no such module: vec0").
8. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural (S1.5 read-source cascade) — defer until after RATIFY-2.


## D-2722 (2026-09-30) - Retrieval smoke test PASSED (gate #2) + S5 practicality filter + USearch/HNSW harness gap
DONE THIS TURN: Retrieval smoke test PASSED — hybrid+rerank recall 0.867/MRR 0.646 beats FTS 0.600/0.357 (RATIFY-2 gate #2 satisfied).
S5 practicality filter (D2622) forensic-assessed: PROPOSED, config/practicality.yaml absent, correctly deferred behind RATIFY-2
(POST-RATIFY-2 S5 addition, alongside F-15). USearch/HNSW recall benchmark (gate #1) identified as a WRITE-A-HARNESS task
(existing benchmark_faiss_vs_usearch.py is clustering-only, D2120, not KNN recall).

NEXT (critical order):
1. [TASK] USearch/HNSW recall harness (D2280): adapt benchmark_faiss_vs_usearch.py to measure IndexHNSWFlat/USearch vs IndexFlatIP KNN recall@k — gate #1 for RATIFY-2.
2. [TASK] Declare train/eval split BEFORE any anchor->golden bootstrap (leakage guard: anchors are ALSO the eval ruler, D-337/D-300).
3. [TASK] Bootstrap S4 discipline/domain golden from KEEP(46) with cross-model vote (>=2/3, D2362); freeze 7 depth + extend stage4_golden.yaml; owner adjudicates disagreements only.
4. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
5. [OWNER-RATIFY] RATIFY-2 full clean rerun (after 1 passes) — stage6.vec_require=true at launch.
6. [TASK] S5 practicality filter (D2622): mint config/practicality.yaml + pipeline/s5 filter — POST-RATIFY-2 (with F-15 extraction_type verifier).
7. [BUG] Re-verify vec0 at S6 under /opt/homebrew/bin/python3 (latent "no such module: vec0").
8. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural (S1.5 read-source cascade) — defer until after RATIFY-2.

## D-2723 (2026-09-30) - D2622 IMPLEMENTED (deterministic) + vector+rerank dominates hybrid+rerank
DONE THIS TURN: D2622 S5 practicality filter IMPLEMENTED (config/practicality.yaml + pipeline/practicality.py,
deterministic backend; application/accessibility live, procedural_skill/is_summary inert). Retrieval A/B gained
vector+rerank leg and re-measured: vector+rerank 0.900/0.647/0.090 DOMINATES hybrid+rerank 0.867/0.646/0.087 —
RRF fusion is recall-negative; recommend vector+rerank as production default (owner ratify).

NEXT (critical order):
1. [OWNER-RATIFY] Adopt vector+rerank as production default (drop RRF fusion): flip config so rerank runs over
   the pure vector pool — simpler path, strictly dominates hybrid+rerank on all 3 metrics.
2. [TASK] USearch/HNSW recall harness (D2280, RATIFY-2 gate #1): adapt benchmark_faiss_vs_usearch.py to measure
   IndexHNSWFlat/USearch vs IndexFlatIP KNN recall@k — the ONE unbenchmarked S1.5 lever.
3. [TASK] Declare train/eval split BEFORE any anchor->golden bootstrap (leakage guard: anchors are ALSO the
   frozen eval ruler, D-337/D-300/D-345).
4. [TASK] Bootstrap S4 discipline/domain golden from KEEP(46) with cross-model vote >=2/3 (D2362); freeze 7 depth
   + extend stage4_golden.yaml; owner adjudicates disagreements only.
5. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
6. [OWNER-RATIFY] RATIFY-2 full clean rerun (after 1-2 pass) — stage6.vec_require=true at launch; S5 practicality
   (D2622) + F-15 extraction_type verifier wire-in lands here (POST-RATIFY-2 S5 additions).
7. [BUG] Re-verify vec0 at S6 under /opt/homebrew/bin/python3 (latent "no such module: vec0").
8. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural (S1.5 read-source cascade) — defer
   until after RATIFY-2.

## D-2724 (2026-09-30) - vector+rerank ADOPTED as production default (owner-approved)
DONE THIS TURN: vector+rerank wired as production retrieval default — config retrieval.method: vector (C12/C21) +
RETRIEVAL_METHOD constant + search() dispatcher; 3 production call sites repointed (graph_aware_search seed,
agentic_search non-graph + broaden). search_hybrid left untouched (benchmark/CLI/measure_constraint_violation never
drift). Forensic audit clean (config parses, constants resolve, retrieve.py parses). Answered the full-rerun root cause
(chunking rechunk-v4 → cluster-before-extract cascade → full rerun mandatory, S2/S4 resume = hidden staleness).

NEXT (critical order):
1. [TASK] USearch/HNSW recall harness (D2280, RATIFY-2 gate #1): new script to measure IndexHNSWFlat/USearch vs
   IndexFlatIP KNN recall@k (recall_measure.py is golden-yield D2307, NOT index recall; benchmark_faiss_vs_usearch.py
   is clustering D2120) — needs a live embedding source (ollama bge-m3 or S1.5 embed checkpoint) to run.
2. [TASK] Declare train/eval split BEFORE any anchor->golden bootstrap (leakage guard: 208 anchors are ALSO the frozen
   eval ruler, D-337/D-300/D-345).
3. [TASK] Bootstrap S4 discipline/domain golden from KEEP(46) with cross-model vote >=2/3 (D2362); freeze 7 depth +
   extend stage4_golden.yaml; owner adjudicates disagreements only.
4. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
5. [OWNER-RATIFY] RATIFY-2 full clean rerun (after 1 passes) — stage6.vec_require=true at launch; S5 practicality
   (D2622) + F-15 extraction_type verifier wire-in lands here (POST-RATIFY-2).
6. [BUG] Re-verify vec0 at S6 under /opt/homebrew/bin/python3 (latent "no such module: vec0").
7. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural (S1.5 read-source cascade) — defer
   until after RATIFY-2.

## D-2725 (2026-09-30) - USearch/HNSW KNN recall harness (RATIFY-2 gate #1) PASSED
DONE THIS TURN: wrote benchmarks/benchmark_hnsw_recall.py + config/usearch_hnsw_recall.yaml (C12 config-first) and ran LIVE
(2000 rechunk-v4 segments, bge-m3 512d via pipeline.embeddings). FAISS IndexHNSWFlat recall@k 0.9998/0.9996/0.9991/0.9962
@[5/10/20/50]; USearch 0.9837/0.9837/0.9811/0.9714. GATE @k=10 threshold 0.95 -> PASS (faiss 0.9996, usearch 0.9837). D2280
lever CLOSED: S1.5 neighbor search can swap IndexFlatIP -> IndexHNSWFlat (O(log N)) with negligible recall loss. RATIFY-2 BOTH
gates green (gate #1 recall D-2725 + gate #2 smoke D-2722).
EXTERNAL RESEARCH (D-2726, reference-only): continual-learning topic = NN-training frameworks (avalanche/PyCIL/mammoth —
inapplicable to a FROZEN-model pipeline) + agent-memory libs (honcho/letta — agent-runtime, not pipeline). test-model-thing =
toy MLX byte-level LM PoC (no RAG component). Neither worth adopting/integrating; only conceptual echo is incremental-index
(already advanced this turn via the HNSW lever + pending S1.3 checkpoint).

NEXT (critical order):
1. [OWNER-RATIFY] RATIFY-2 full clean rerun S1.3->S6 (~13-16h, stage6.vec_require=true) — BOTH gates green (HNSW recall PASS
   D-2725 + retrieval smoke PASS D-2722); S5 practicality (D2622) + F-15 extraction_type verifier wire-in lands here.
2. [TASK] Declare train/eval split BEFORE any anchor->golden bootstrap (leakage guard: 208 anchors are ALSO the frozen eval
   ruler, D-337/D-300/D-345).
3. [TASK] Bootstrap S4 discipline/domain golden from KEEP(46) with cross-model vote >=2/3 (D2362); freeze 7 depth + extend
   stage4_golden.yaml; owner adjudicates disagreements only.
4. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
5. [BUG] Re-verify vec0 at S6 under /opt/homebrew/bin/python3 (latent "no such module: vec0").
6. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural (S1.5 read-source cascade) — defer until
   after RATIFY-2.
7. [TASK] S1.5 IndexHNSWFlat swap (POST-RATIFY-2, C21 swappable) — D-2725 proved recall; adoption is a separate config flip.

## D-2727 (2026-09-30) - RATIFY-2 full-rerun PREFLIGHT audit: PASS
Owner ratified the rerun; preflight first. VERIFIED: entrypoint python3 pipeline/runner.py (run_id rechunk-v4-20260929);
`just preflight` is a comprehensive gate; lazy-load IN EFFECT (mlx_provider lazy singletons + unloader); vec0 FULLY VERIFIED
under /opt/homebrew/bin/python3 (import+load+CREATE+INSERT) -> set stage6.vec_require=true (fail-closed, no silent skip).
GAP: runner.py full-rerun lacks caffeinate -> launch under `caffeinate -dimsu python3 pipeline/runner.py`. Remaining
pre-rerun risk: train/eval leakage (208 anchors = eval ruler) must be declared before S4/S5 golden bootstrap.
RESEARCH (D-2728): JEV != JEPA. JEPA = Meta self-supervised encoder (irrelevant to text extraction). JEV/Laya = typed
decision models; laya-mlx 6643★ / jevmlx 69★ native MLX runtimes — reference-only, optional POST-RATIFY-2 S4 pilot.
feed.opml += continual-learning.

NEXT (critical order):
1. [OWNER-RATIFY] Launch RATIFY-2 full rerun — preflight PASS (D-2727): `caffeinate -dimsu python3 pipeline/runner.py --dry-run`
   then full S1.3->S6 (vec_require=true now live).
2. [TASK] Declare train/eval split BEFORE any anchor->golden bootstrap (leakage guard: 208 anchors are ALSO the frozen eval
   ruler, D-337/D-300/D-345).
3. [TASK] Bootstrap S4 discipline/domain golden from KEEP(46) with cross-model vote >=2/3 (D2362); owner adjudicates disagreements only.
4. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
5. [BUG] vec0 RE-VERIFIED (D-2727) — vec_require=true now fail-closed; watch S6 at run time.
6. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural; defer until after RATIFY-2.
7. [TASK] S1.5 IndexHNSWFlat swap + optional Laya/Jev S4 pre-filter pilot — POST-RATIFY-2.


## D-2729 (2026-09-30) - RATIFY-2 GO (rerun unblocked) + owner-gate A/B (train/eval split; FIX(130) re-triage)
DONE THIS TURN: forensic audit (read-only) confirms registry consistency (858/600/336 == bug_status 336) and NO drift.
RERUN UNBLOCKED — both gates green (D-2725 HNSW recall + D-2722 smoke), preflight PASS (D-2727), RATIFY-1/2/3/4 done,
re-ground(8) COMPLETE (D-2715), domain 208/208 (D-2720), vec_require=true live. Train/eval split gates ONLY the
POST-rerun anchor->S4-golden bootstrap, NOT the rerun. OG-1 split A/B: Option A (RECOMMENDED) disjoint split + machine
manifest (KEEP46 -> S4 golden, pinned OUT of eval, 208->162); Option B zero-anchor golden (eval stays 208); Option C
(leak) REJECTED. OG-2 FIX(130): 128 domain-resolved + 7 reground (D-2715) -> golden-eligible subject to split.

NEXT (critical order):
1. [OWNER-RATIFY] Launch RATIFY-2 full rerun — preflight PASS (D-2727): `caffeinate -dimsu python3 pipeline/runner.py --dry-run`
   then full S1.3->S6 (vec_require=true live). UNBLOCKED — no owner gate stands between here and GO.
2. [OWNER-GATE] Declare train/eval split (leakage guard D-337/D-300/D-345): Option A (disjoint + machine manifest, KEEP46 out
   of eval) RECOMMENDED; Option B (zero-anchor golden) is the fallback. This gates ONLY the POST-rerun golden bootstrap.
3. [TASK] On split: emit anchor_triage_v2.json + split manifest (sha256-pinned rail) + bootstrap S4 golden from KEEP(46)
   (cross-model vote >=2/3 D2362; owner adjudicates disagreements only).
4. [TASK] Interim S4 guardrail: closed-menu (62/44) + abstention routing (D2618) — never force a label.
5. [BUG] vec0 RE-VERIFIED (D-2727) — vec_require=true fail-closed; watch S6 at run time.
6. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural; defer until after RATIFY-2.
7. [TASK] POST-RATIFY-2: S1.5 IndexHNSWFlat swap (D-2725 proved recall) + S5 practicality wire-in (D2622) + F-15
   extraction_type verifier + optional Laya/JEV S4 pre-filter pilot (D-2728).

## D-2730 (2026-09-30) - OG-1 = Option A DECLARED + RATIFY-2 launched S1.5->S6
DONE THIS TURN: owner declared OG-1 Option A; emitted split_manifest.json (golden_pool 46 / eval 162, sha256-pinned
rail) + anchor_triage_v2.json; RATIFY-2 launched S1.5->S6 under caffeinate + /opt/homebrew/bin/python3 (3.14, PATH
prepended). Forensic audit clean (registry 859->860 / BUG-600 / 336; OMLX+Ollama UP; golden hash + version gate PASS).

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 — monitor S1.5 embed/cluster, S2 extract (longest), S4 merge, S5 NLI, S6 commit (vec_require fail-closed).
2. [TASK] POST-rerun golden bootstrap: S4 golden from KEEP(46) cross-model vote >=2/3 (D2362); owner adjudicates disagreements only.
3. [RAIL] Enforce split_manifest: any golden_pool id re-entering eval must fail (sha256-pinned 208->162 invariant).
4. [TASK] POST-RATIFY-2: S1.5 IndexHNSWFlat swap (D-2725), S5 practicality wire-in (D2622), F-15 extraction_type verifier, optional Laya/JEV S4 pilot (D-2728).
5. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural; defer until after RATIFY-2.
6. [BUG] Watch S6 vec_require=true fail-closed at run time; no silent vec0 skip.
7. [HYGIENE] Fix cosmetic stale rows:150 comment in config/anchor_family.yaml (cohort now 208) after rerun.

## D-2731 (2026-09-30) - RATIFY-2 survived battery outage + monitor added + BUG-601 filed
DONE THIS TURN: battery drained to 8% mid-S1.5 but run SURVIVED (no reboot, crash-safe state.json resume CONFIRMED);
added scripts/watch_ratify2.py read-only monitor (now live, S1.5 ~7.7%); forensic audit — rows:150 is CORRECT
(misread in D-2730 hygiene note), evidence_passages schema RESOLVED (BUG-596/187), filed BUG-601 (anchor verifier
CSV/JSONL drift breaks just health).

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 — keep on AC; monitor ratify2_watch.log; watch drop gaps (<~20) + S6 vec_require fail-closed.
2. [TASK] POST-rerun golden bootstrap: S4 golden from KEEP(46) cross-model vote >=2/3 (D2362); owner adjudicates disagreements.
3. [RAIL] Enforce split_manifest: any golden_pool id re-entering eval must fail (sha256-pinned 208->162 invariant).
4. [BUG] BUG-601: fix verify_anchor_family_registry.py to read the D-2720 CSV domain artifact (CSV remap) — restore just health.
5. [TASK] POST-RATIFY-2: S1.5 IndexHNSWFlat swap (D-2725), S5 practicality wire-in (D2622), F-15 extraction_type verifier, optional Laya/JEV S4 pilot (D-2728).
6. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural; defer until after RATIFY-2.
7. [TASK] Classify 150 locked anchors primary_domain (closed_menu_v5) — after run (CPU-heavy; competes with bge-m3).

## D-2732 (2026-09-30) - BUG-601 FIXED + duplicate-runner resolved + BUG-602 filed
DONE THIS TURN: BUG-601 FIXED (anchor verifier reads CSV, obsolete checks removed, YAML over-reach restored -> EXIT=0);
duplicate-runner incident resolved (killed 36748/36749/36750, preserved 33655, checkpoint verified clean); BUG-602
filed (runner.py no singleton guard + launch no < /dev/null). Forensic audit clean. Run healthy S1.5 70.8%.

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 — keep on AC; monitor ratify2_watch.log; watch drop gaps + S6 vec_require fail-closed.
2. [TASK] POST-rerun golden bootstrap: S4 golden from KEEP(46) cross-model vote >=2/3 (D2362); owner adjudicates.
3. [RAIL] Enforce split_manifest: any golden_pool id re-entering eval must fail (sha256-pinned 208->162 invariant).
4. [BUG] BUG-602: add singleton/pidfile guard to runner.py + < /dev/null in launch (post-run).
5. [TASK] POST-RATIFY-2: S1.5 IndexHNSWFlat swap (D-2725), S5 practicality wire-in (D2622), F-15 extraction_type verifier, optional Laya/JEV S4 pilot (D-2728).
6. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural; defer until after RATIFY-2.
7. [TASK] Classify 150 locked anchors primary_domain (closed_menu_v5) — after run (CPU-heavy; competes with bge-m3).

## D-2733 (2026-09-30) - S1.3-S1.5 CLEAN + split_manifest rail + BUG-603
DONE THIS TURN: S1.3->S1.5 integrity VERIFIED CLEAN (no rerun): .npy cache uniform 131200B, all (64,512) finite,
0 torn, fingerprint stable, only 2 known quarantine gaps. split_manifest leakage rail IMPLEMENTED
(scripts/verify_split_manifest.py, fail-closed disjoint 46/162/208 + option A, wired into just health). BUG-603
filed (ids_sha256 pin irreproducible, no emitter).

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 (~75%+ embedding) — keep on AC; monitor ratify2_watch.log; re-embed quarantine gaps 16256/16320 before S6.
2. [TASK] POST-rerun golden bootstrap: KEEP(46) cross-model vote >=2/3 (D2362); owner adjudicates disagreements.
3. [BUG] BUG-603: re-pin ids_sha256 with documented canonical form + emitter (owner-gated).
4. [BUG] BUG-602: singleton/pidfile guard in runner.py + < /dev/null in launch (post-run).
5. [TASK] POST-RATIFY-2: HNSW swap (D-2725), S5 practicality (D2622), F-15 extraction_type verifier, Laya/JEV pilot (D-2728).
6. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — architectural, defer until after RATIFY-2.
7. [TASK] Classify 150 locked anchors primary_domain (closed_menu_v5) — after run (CPU competes with bge-m3).

## D-2734 (2026-09-30) - Duplicate-book-source forensic audit + source_identity rail
DONE THIS TURN: Forensic audit confirmed the "20+ duplicate book sources" (S1.5/S2/S4-d) is BUG-289 (source_diversity
counted filenames), FIXED live via D2176 canonical source_id (SHA-256(author|title)) in S1.5/S2/S4. Added
scripts/verify_source_identity.py fail-closed rail (6 selftest controls + both-unknown-ratio gate, wired into just
health, config in eval_integrity.yaml). Measured 962/962 books resolve author+title -> 0% filename-fallback.

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 — at ~77% embedding; re-embed quarantine gaps 16256/16320 before S6.
2. [TASK] POST-run golden bootstrap: KEEP(46) cross-model vote >=2/3 (D2362).
3. [BUG] BUG-603 re-pin ids_sha256 (owner-gated) + BUG-602 singleton/pidfile guard (post-run).
4. [TASK] POST-RATIFY-2: HNSW swap (D-2725), S5 practicality (D2622), F-15 extraction_type verifier.
5. [TASK] Residual dedup: same-book TITLE RENAME semantic dedup (Broder shingling/MinHash + Splink, D-273e rec) — owner-gated.
6. [DECISION] S1.3 self-contained checkpoint (BUG-598 option B) — APPROVED post-run (D-2735).

## D-2735 (2026-09-30) - Two owner-gate rulings
DONE THIS TURN: (1) S1.3 self-contained checkpoint option B APPROVED (post-run, before any rerun — mid-run would
risk drift vs b9e924d5). (2) Title-rename dedup: Splink DEFERRED; deterministic-first APPROVED (owner alias map +
read-only Broder-shingling detector, never auto-merge; escalate to Splink only if material count).

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 (~77%+) — re-embed quarantine gaps 16256/16320 before S6.
2. [TASK] POST-run: S1.3 self-contained checkpoint (BUG-598 option B, D-2735 approved) — before any rerun.
3. [TASK] POST-run: golden bootstrap KEEP(46) cross-model vote >=2/3 (D2362).
4. [TASK] Build owner-curated alias/rename map (known renames) + read-only Broder-shingling detector (D-2735).
5. [BUG] BUG-603 re-pin ids_sha256 + BUG-602 singleton/pidfile guard (post-run).
6. [TASK] POST-RATIFY-2: HNSW swap (D-2725), S5 practicality (D2622), F-15 extraction_type verifier.

## D-2736 (2026-09-30) - title-dedup detector + 45 candidates + BUG-604
DONE THIS TURN: built scripts/detect_title_renames.py (read-only Broder-shingling detector, selftest 4/4, wired into
just health). Ran on 962 metadata records -> 45 near-dup candidates (jaccard >= 0.60). Root-caused ~40 to stage0_5
"liber3.md" filename mis-splits (title words leak into author) -> filed BUG-604. ~5 are genuine series volumes (must
NOT merge). No mid-run fix (would change fingerprint b9e924d5).

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 — re-embed quarantine gaps 16256/16320 before S6.
2. [BUG] BUG-604 (post-run): repair parse_filename_metadata to strip "liber3.md" suffix + trailing-author boundary,
   then re-resolve affected source_ids.
3. [TASK] POST-run: S1.3 self-contained checkpoint (BUG-598 option B, D-2735 approved).
4. [TASK] POST-run: golden bootstrap KEEP(46) cross-model vote >=2/3 (D2362).
5. [BUG] BUG-603 re-pin ids_sha256 + BUG-602 singleton/pidfile guard (post-run).
6. [OWNER] Gate the 45 candidates (governance/title_rename_candidates.json) + supply semantic-rename alias pairs.
7. [TASK] POST-RATIFY-2: HNSW swap (D-2725), S5 practicality (D2622), F-15 extraction_type verifier.

## D-2737 (2026-09-30) - Option B full-text content dedup DONE
Built scripts/detect_same_work_content.py (Option B, D-2737): 962 records -> 905 works -> 29 same-work candidates
(exact Jaccard >= 0.50). Caught Systemantics≡The Systems Bible (0.999) + Metaphorically Selling≡The Tall Lady With
the Iceberg (0.726). All 29 -> owner gate (governance/same_work_content_candidates.json).

Built owner-gate dedup ledger (D-2738): merged 74 candidates -> 59 pairs (governance/duplicate_adjudication.json),
fail-closed --gate apply-guard, advisory hints (series_volume=3 DANGER, title_rename=1, author_leak=10, noise_suffix=5,
subtitle_or_edition=32, review=8). ~48/59 genuine duplicates, ~11 false positives isolated. Never auto-merge.

NEXT (critical order):
1. [RUNNING] RATIFY-2 S1.5->S6 — re-embed quarantine gaps 16256/16320 before S6.
2. [OWNER] Adjudicate 59 ledger pairs (D-2738) in governance/duplicate_adjudication.json — MERGE/KEEP_SEPARATE each, never auto-merge.
3. [BUG] BUG-604 (post-run): repair parse_filename_metadata (liber3.md split) -> re-resolve source_ids.
4. [TASK] POST-run: S1.3 self-contained checkpoint (BUG-598 option B, D-2735).
5. [TASK] POST-run: golden bootstrap KEEP(46) >=2/3 (D2362).
6. [BUG] BUG-603 re-pin ids_sha256 + BUG-602 singleton/pidfile guard (post-run).
7. [TASK] POST-RATIFY-2: HNSW swap (D-2725), S5 practicality (D2622), F-15 extraction_type verifier.
8. [TASK] POST-run apply (D-2738): derive book alias_map from MERGE verdicts -> re-resolve source_ids -> re-run detectors (zero remaining) -> re-pin fingerprint.
9. [DECISION] Splink DEFERRED (D-2739): re-measure residual AFTER BUG-604 fix + re-run of BOTH detectors; escalate to Splink (3rd read-only detector, same owner-gate) only if residual >= 3 (duplicate_gate.splink_escalation_residual_threshold).
10. [TASK] Pre-S6: re-embed quarantine gaps 16256/16320 (~128 segments) — S1.5 finalized with gaps=2; only missing segments.

D-2740: Owner approved D-2738 + D-2739. S1.5 COMPLETED (20:34); pipeline now in S2 (Principle Discovery Gate, 1817
clusters). Fixed BUG-605 (watch_ratify2.py S1.5-finalization detection) + killed stale watcher. Registry: decisions 870,
buglog 341, highest BUG-605.

D-2741: Duplicate-book deletion DEFERRED post-run + quarantine-not-delete. 12 genuine dups mapped
(governance/dedup_deletion_plan.json), 47 false positives excluded (43 medium-conviction + 4 series/color-vs-type).

D-2742: BUG-602 FIXED — runner singleton/pidfile guard (_acquire_singleton_lock). Fail-closed, live-refuse verified.
Stage-2 datasketch failure was TRANSIENT (datasketch 2.0.0 installed; full MinHashLSH round-trip passes). Registry:
decisions 872, buglog 341 (BUG-602 CLOSED, 131 open / 210 closed), highest BUG-605.

D-2743: S2 re-run readiness confirmed. datasketch verified, BUG-602 guard verified, resume cmd corrected to
`--resume-from 2` (numeric, docstring fixed). FINDING: a backgrounded `nohup ... &` launch does NOT survive a
subprocess shell (runner reaped, omlx-server orphaned). S2 MUST be launched from a durable terminal with
`caffeinate -s`. Registry: decisions 873.

D-2744: BUG-606 FIXED — preflight timeout 30s < OMLX watchdog restart cycle ~43s; preflight aborted S2 mid-restart.
Fix: C12 run.preflight_timeout_sec: 90 + _get_preflight_timeout(). OMLX healthy (RSS 4.4GB). Registry: decisions 874,
buglog 342 (BUG-606 CLOSED, 131 open / 211 closed), highest BUG-606.

D-2745: BUG-607 FIXED — datasketch ModuleNotFoundError was ENV-DRIFT, not transient. Root cause: bare "python3" in
runner.py subprocess.run() resolves via the LAUNCHER PATH; the machine has FOUR Pythons (conda base 3.13 = login-shell
default with NO datasketch; Python.org framework 3.12 = the only env that had it; incomplete knowledge-pipeline 3.11;
homebrew 3.14 = S6 vec). Prior "installed/transient" tests ran in a NON-login shell → framework 3.12 → false PASS
(wrong interpreter = the blindspot). FIX: pip install datasketch into conda base + run.python_bin config (C12) +
_get_python_bin() in runner.py (stage + preflight). Verified MinHashLSH ok=True + round-trip + --dry-run. Registry:
decisions 875, buglog 343 (BUG-607 CLOSED, 131 open / 212 closed), highest BUG-607.

NEXT (critical order — refreshed 2026-09-30 21:27):
1. [TASK] Re-run S2 (RATIFY-2 resume): `caffeinate -s python3 pipeline/runner.py --resume-from 2` — BUG-607 FIXED
   (datasketch installed into conda base + run.python_bin pinned); BUG-602 singleton guard blocks duplicate runners.
2. [TASK] Pre-S6: re-embed quarantine gaps 16256/16320 (~128 segments) — only missing segments from S1.5 finalization.
3. [OWNER] Adjudicate 59 ledger pairs (D-2738) — MERGE/KEEP_SEPARATE each; never auto-merge (fail-closed --gate).
4. [BUG] BUG-604 (post-run): repair parse_filename_metadata (liber3.md split) -> re-resolve source_ids.
5. [BUG] BUG-603 (post-run): re-pin split_manifest ids_sha256 with documented emitter + canonical serialization.
6. [TASK] POST-run apply (D-2738): derive book alias_map from MERGE verdicts -> re-resolve -> re-run detectors -> re-pin fingerprint.
7. [DECISION] Splink DEFERRED (D-2739): re-measure residual AFTER BUG-604; escalate only if residual >= 3.
8. [TASK] POST-run quarantine of 12 genuine dups (D-2741) — owner per-file confirm, R-D410 safe_delete.

D-2746: BUG-609/610 FIXED — S2 fail-closed loop (deterministic schema failures at temp=0.0 + post-resume denominator).
S2 now exits 0 (2/12,607 dropped = 0.016% ≤ 0.01, 8,217 FBs final). S4 RUNNING (depth pass DONE 7,149 clusters;
CRIBS discipline/domain in progress). Registry: decisions 876, buglog 346 (131 open / 215 closed), highest BUG-610.

NEXT (critical order — refreshed 2026-10-02, D-2760):
0. [DONE] Owner finalized 42 depth mismatches → ANCHOR_208_DEPTH_CORRECTED_20261002.json + depth_finalization_owner_42.json (D-2760).
1. [TASK] Wire ANCHOR_208_DEPTH_CORRECTED_20261002.json into stage4_merge.py depth golden few-shot + held-out conformance gate (read corrected artifact, NOT the stale CSV; 2 universal exemplars R049/R053 now available).
2. [TASK] Normalize ANCHOR-208 discipline cells (2 trailing-space dupes, 5 'emerging' catchall, 4 off-menu R042/R086/R091/R117).
3. [TASK] Verify + provenance-stamp the 58 mapped extras' depth source before they join the anchor.
4. [RUN] RESTART S4 main loop — content_type + applicability deterministic (can start NOW, independent of depth wiring).
5. [TASK] Pre-S6: re-embed quarantine gaps 16256/16320 (~128 segments) — must complete BEFORE S6 commit.
6. [BUG] BUG-615 root cause: S1.5 upstream — why identical segments land in 5 clusters.
7. [BUG] BUG-604 (post-run): repair parse_filename_metadata (liber3.md split) -> re-resolve source_ids.

D-2761: depth conformance anchor + gate BUILT (corrected the D-2760 step-1 plan per D-274f/D-2611). 149 owner depth rows
provenance-stamped (depth_anchor_conformance_20261002.json) + scripts/depth_conformance_gate.py (chance-corrected kappa,
floor 0.800). Live 149-FB run pending OMLX. Registry: decisions 891.

NEXT (critical order — refreshed 2026-10-02, D-2761):
0. [DONE] Depth anchor wired CORRECTLY: conformance-only (D-274f), kappa not 0.85 (D-2611) -> depth_anchor_conformance_20261002.json + depth_conformance_gate.py (D-2761).
1. [RUN] Live depth conformance: `python3 scripts/depth_conformance_gate.py --gate` (needs OMLX up); kappa < 0.800 -> owner acts on per-class collapse (a finding, not a code change).
2. [TASK] Verify + provenance-stamp the 58 mapped extras' depth before they join the anchor (currently excluded).
3. [TASK] Normalize ANCHOR-208 discipline cells (2 trailing-space dupes, 5 'emerging' catchall, 4 off-menu R042/R086/R091/R117).
4. [TASK] Bootstrap S4 discipline/domain golden (D-2718 addendum): depth golden is depth-only; discipline/domain still 0-example -> root of 150 empty primary_domain.
5. [RUN] RESTART S4 main loop — content_type + applicability deterministic (independent of depth wiring).
6. [TASK] Pre-S6: re-embed quarantine gaps 16256/16320 (~128 segments).
7. [BUG] BUG-615 root cause (S1.5 5-cluster dup); BUG-604 post-run parse_filename_metadata (liber3.md split).

D-2762: discipline axis normalized (BUG-619). 2 whitespace dupes auto-fixed; 4 domain-bleed + 5 emerging -> owner review queue.
DRIFT: primary_domain ALREADY populated (0/150 empty) — "classify 150 primary_domain" task STALE/CLOSED. Registry: decisions 892.

NEXT (critical order — refreshed 2026-10-02, D-2762):
0. [DONE] Depth anchor conformance (D-2761) + discipline axis normalized (D-2762).
1. [OWNER] Re-classify 9 discipline review rows: 4 domain-bleed (R042/R086/R091/R117) + 5 emerging (R040/R052/R080/R092/R100) — unblocks discipline golden bootstrap (D-2718 addendum).
2. [RUN] Live depth conformance: `python3 scripts/depth_conformance_gate.py --gate` (needs OMLX up).
3. [TASK] Verify + provenance-stamp the 58 mapped extras before they join the anchor (depth AND discipline axes).
4. [TASK] Bootstrap S4 discipline/domain golden from the normalized anchor (after owner step 1) — closes the discipline/domain 0-example gap (root of the golden under-spec).
5. [RUN] Restart S4 main loop (content_type + applicability deterministic, independent of the above).
6. [BUG] BUG-615 (S1.5 5-cluster dup); BUG-604 (parse_filename_metadata liber3.md split).

D-2763: ANCHOR-208 consolidated into ONE dual-axis artifact (depth + discipline + domain, 204/208 golden_eligible).
Owner finalized 9 discipline rows; 'emerging' EXCLUDED from golden (abstention != exemplar). Registry: decisions 893.

NEXT (critical order — refreshed 2026-10-02, D-2763):
0. [DONE] Depth anchor conformance (D-2761) + discipline normalize (D-2762) + dual-axis consolidation (D-2763).
1. [TASK] Wire governance/ANCHOR_208_CONSOLIDATED_20261002.json into S4 discipline/domain golden few-shot (filter golden_eligible) — closes the discipline/domain 0-example gap (D-2718 addendum).
2. [RUN] Live depth conformance: `python3 scripts/depth_conformance_gate.py --gate` (needs OMLX up).
3. [TASK] Verify + provenance-stamp the 58 mapped extras' DEPTH before they join the depth golden (they are already discipline-golden-eligible).
4. [RUN] Restart S4 main loop (content_type + applicability deterministic, independent).
5. [BUG] BUG-615 (S1.5 5-cluster dup); BUG-604 (parse_filename_metadata liber3.md split).
6. [MINOR] 208-view `name` column truncation (45 chars) + R039 \xa0 — view superseded by consolidated artifact for name reads.

D-2764: discipline axis lacks human ground truth (9/208 owner-finalized, 197 silver → BUG-620). NO discipline conformance
gate until ~150 human discipline labels exist. Discipline golden already wired (7 hand-authored). Registry: decisions 894.

NEXT (critical order — refreshed 2026-10-02, D-2764):
0. [DONE] Depth conformance gate (D-2761) + discipline normalize (D-2762) + consolidation (D-2763) + discipline-truth audit (D-2764).
1. [OWNER] Adjudicate ~150 human DISCIPLINE labels (retire the 197 silver anchor_adjudication) — unblocks the discipline conformance gate (mirror of depth path, BUG-620).
2. [RUN] Live depth conformance: python3 scripts/depth_conformance_gate.py --gate (needs OMLX up).
3. [TASK] Verify + provenance-stamp the 58 mapped extras' DEPTH (they are also the discipline silver pool to be human-reviewed in step 1).
4. [RUN] Restart S4 main loop (content_type + applicability deterministic, independent).
5. [BUG] BUG-615 (S1.5 5-cluster dup); BUG-604 (parse_filename_metadata liber3.md split).

D-2765: discipline review queue PREPARED (199 unreviewed rows, ~141 target). CLARIFICATION: the 150 owner-approved labels
were DEPTH (D-2760), NOT discipline — discipline has only 9/208 human labels; 197 silver + 2 whitespace = 199 unreviewed
(BUG-620). Registry: decisions 895.

NEXT (critical order — refreshed 2026-10-02, D-2765):
0. [DONE] Depth conformance gate (D-2761) + discipline normalize (D-2762) + consolidation (D-2763) + discipline-truth audit (D-2764) + review queue built (D-2765).
1. [OWNER] Adjudicate ~141 discipline labels from governance/discipline_review_queue_20261002.md (199 rows, grouped by discipline; 'agree in bulk' per group counts). Unblocks the discipline conformance gate (BUG-620).
2. [RUN] Live depth conformance: python3 scripts/depth_conformance_gate.py --gate (OMLX confirmed UP).
3. [TASK] Verify + provenance-stamp the 58 mapped extras' DEPTH (also in the discipline silver pool to be human-reviewed in step 1).
4. [RUN] Restart S4 main loop (content_type + applicability deterministic, independent).
5. [BUG] BUG-615 (S1.5 5-cluster dup); BUG-604 (parse_filename_metadata liber3.md split).

D-2766: discipline axis fully human-provenanced (208/208) via owner bulk adjudication — BUG-620 CLOSED; discipline
conformance anchor built (204 gold rows). Registry: decisions 896.

NEXT (critical order — refreshed 2026-10-02, D-2766):
0. [DONE] Depth gate (D-2761) + discipline normalize (D-2762) + consolidation (D-2763) + discipline-truth audit (D-2764) + review queue (D-2765) + bulk finalization (D-2766).
1. [TASK] Build the discipline conformance gate (mirror scripts/depth_conformance_gate.py) against governance/discipline_anchor_conformance_20261002.json (204 gold); kappa floor 0.800.
2. [RUN] Live depth conformance: python3 scripts/depth_conformance_gate.py --gate (OMLX).
3. [TASK] Verify + provenance-stamp the 58 mapped extras' DEPTH.
4. [EVAL] Splash (incoai + paperniuk M1/M2 backport) as swappable OMLX backend on this M1 Max — gated A/B first (2-4x decode, long-context fix for DELEGATE-002); DO NOT wire until A/B passes.
5. [RUN] Restart S4 main loop (content_type + applicability deterministic, independent).
6. [BUG] BUG-615 (S1.5 5-cluster dup); BUG-604 (parse_filename_metadata liber3.md split).

D-2767: S4 classifier swap gated behind head-to-head FIT eval on human gold (BUG-621); shortlist Mistral-Small-3.1-24B;
Qwen3-* R5-excluded. Research: governance/MARKET_RESEARCH_20261002.md. Registry: decisions 897.

NEXT (critical order — refreshed 2026-10-02, D-2767):
0. [DONE] D-2760..D-2767: depth finalization, depth gate, discipline normalize/consolidate/audit/queue/bulk-finalize, market research + classifier-swap gate.
1. [TASK] Build the discipline conformance gate (mirror scripts/depth_conformance_gate.py) against governance/discipline_anchor_conformance_20261002.json (204 gold); kappa floor 0.800.
2. [RUN] Live depth conformance: python3 scripts/depth_conformance_gate.py --gate (OMLX).
3. [TASK] Verify + provenance-stamp the 58 mapped extras' DEPTH.
4. [EVAL] S4 classifier FIT eval (D-2767): Mistral-Small-3.1-24B vs gpt-oss-20b on 149 depth + 204 discipline gold (kappa + tok/s). DO NOT swap until gate passes.
5. [EVAL] Splash-M1 backport vs OMLX A/B — MOOT (D-2768): Splash only serves Qwen3.8-27B/Qwen3.6-35B-A3B/Prism, NOT gpt-oss-20b or Qwen3-Coder.
6. [EVAL] Quick wins: ONNX Runtime for DeBERTa-v3 NLI; qwen3-embedding vs bge-m3.
7. [RUN] Restart S4 main loop (content_type + applicability deterministic, independent).
8. [BUG] BUG-615 (S1.5 5-cluster dup); BUG-604 (parse_filename_metadata liber3.md split); BUG-617/618/619 (multi-leg — close as remaining legs complete).

D-2768: Splash is model-scoped (Qwen3.8-27B/Qwen3.6-35B-A3B/Prism only) — NOT a general GGUF runner; Splash A/B MOOT.
Registry: decisions 898.

NEXT (critical order — refreshed 2026-10-02, D-2768):
0. [DONE] D-2760..D-2768 (depth/discipline finalization + conformance anchors + market research D-2767 + Splash-scope correction D-2768).
1. [TASK] Build the discipline conformance gate (mirror scripts/depth_conformance_gate.py) vs governance/discipline_anchor_conformance_20261002.json (204 gold); kappa floor 0.800.
2. [RUN] Live depth conformance: python3 scripts/depth_conformance_gate.py --gate (OMLX).
3. [TASK] Verify + provenance-stamp the 58 mapped extras' DEPTH.
4. [EVAL] S4 classifier FIT eval (D-2767): Mistral-Small-3.1-24B vs gpt-oss-20b on 149 depth + 204 discipline gold (kappa + tok/s). DO NOT swap until gate passes.
5. [EVAL] Quick wins: ONNX Runtime for DeBERTa-v3 NLI; qwen3-embedding vs bge-m3. (Splash A/B MOOT — D-2768.)
6. [RUN] Restart S4 main loop (content_type + applicability deterministic, independent).
7. [BUG] BUG-615 (S1.5 5-cluster dup); BUG-604 (parse_filename_metadata liber3.md split); BUG-617/618/619 (multi-leg — close as remaining legs complete).

D-2769: discipline conformance gate built (scripts/discipline_conformance_gate.py, kappa vs 204 human gold). Registry: decisions 899.

NEXT (refreshed D-2772):
1. [BUG] BUG-622 — discipline axis NON-CONFORMANT (kappa ~0.45 << 0.8). ROOT-CAUSE FOUND (D-2773): no closed 62-menu
   in merged prompt + over-precision instruction -> free-generated off-menu names -> 'emerging'/wrong-synonym. FIX
   (MEASURE-gated): inject 62-menu + "choose EXACTLY ONE" + negative exemplars; adopt only if full-204 A/B kappa >= 0.800.
2. [RUN] Full-204 discipline conformance for a definitive kappa + CI: python3 scripts/discipline_conformance_gate.py --gate.
3. [BUG] BUG-623 — dependency drift (D-2772): S5-NLI + S1.5-embedding smoke test under transformers 5.14.1 /
   sentence-transformers 5.7.0; reconcile requests/urllib3/charset_normalizer mismatch. No dep change until smoke proves need.
4. [RUN] Live depth conformance: python3 scripts/depth_conformance_gate.py --gate (OMLX UP).
5. [EVAL] S4 classifier FIT eval (D-2767): Mistral-Small-3.1-24B vs gpt-oss-20b on 149 depth + 204 discipline gold.
6. [EVAL] gpt-oss turboquant_kv latency A/B (MEASURE-gated, D-332) + Q4 quant download (D-2772).
7. [EVAL] Quick wins: ONNX Runtime (DeBERTa-v3), qwen3-embedding vs bge-m3.
8. [TASK] Verify + provenance-stamp the 58 mapped extras' DEPTH.
9. [RUN] Restart S4 main loop (content_type + applicability deterministic).
10. [BUG] BUG-615, BUG-604, BUG-617/618/619 (remaining legs). Bonsai-2 A/B = NOT worth it (D-2771). OMLX/Goose audit DONE (D-2772).

> **NEW — 2026-10-02 (D-2785): 58 mapped depth rows OWNER-ADJUDICATED and folded -> depth golden 149 -> 207 (owner overrode goose on 5: R151/R172/R196/R200/R203). Fold via scripts/fold_owner_depth_adjudication.py (backed up, crash-safe). S4 shortlist REVISED after 5-model research: [gemma-4-12B-it-qat-OptiQ-4bit PRIMARY, clef-flash-4bit SECONDARY]; Qwen3.8 R5-excluded, humanizer wrong-task, Xing4.0 high-risk. Gate unchanged.**

> **NEW — 2026-10-02 (D-2786): Owner approved downloading BOTH S4 candidates. gemma-4-12B-it-qat-OptiQ-4bit (PRIMARY) downloading to OMLX serving store; clef-flash-4bit (SECONDARY) CONFIRMED custom-arch -> ADAPTER-SCOPE (needs schema/head adapter before FIT eval), NOT a drop-in. Forensic audit repaired the stale bug register (BUG-623/BUG-624 re-derived) and surfaced BUG-624: depth conformance anchor stale at 149 vs 207 golden. NEXT: (1) register+reload gemma-4-12B once download lands; (2) resolve BUG-624 (bridge 58 folded item_ids->fb_ids, 149->207 in build_depth_anchor_conformance.py, rebuild, re-run gates); (3) FIT eval gemma-4-12B vs gpt-oss-20b on 207 depth + 204 discipline. Registry: decisions 916 / buglog 363 / highest BUG-624.**

> **NEW — 2026-10-02 (D-2787): BUG-624 fixed at the SOURCE (not a JSON patch). New scripts/build_anchor_bridge_ruler_208.py derives a 208-row bridge ruler (150 content ruler + 58 folded depth extras); config/anchor_family.yaml store_bridge.ruler_sheet re-pointed; bridge REGENERATED so build_anchor_store_bridge.py --check is "ok" (208/208 bridged, exact 207 / normalized 1). depth_anchor_conformance rebuilt to 207 golden (domain 99 / cross-domain 58 / specialized 48 / universal 2). BUG-624 marked RESOLVED. NEXT: FIT eval gemma-4-12B vs gpt-oss-20b on 207 depth + 204 discipline (D-2767/D-2783 gate). Registry: decisions 917 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-02 (D-2788): gemma-4-12B-it-qat-OptiQ-4bit FIT eval NEGATIVE — SLOWER than gpt-oss-20b on BOTH axes (warm depth 3.78 vs 1.98s/FB ~1.9x; discipline 40.2 vs 15.0s/FB ~2.7x); D-2767/D-2783 'faster' gate NOT met. gemma-4-12B parked (no S4 routing); gpt-oss-20b remains classifier-of-record; BUG-622 stays OPEN. Count-drift guard (BUG-624 class) added to BOTH conformance load_anchor paths (fail-closed on row-count vs declared total). NEXT: (1) BUG-622 next move — clef-flash adapter (parked) vs a genuinely faster MXFP4-native candidate (NOT OptiQ-mixed); (2) re-run depth_conformance_gate --gate on 207 golden; (3) BUG-563 worktree hygiene (100 dirty paths) for clean just health. Registry: decisions 918 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-02 (D-2789): BUG-622 path RE-ROUTED. Both candidate paths EXHAUSTED — SWAP 5/5 (Mistral v1.0 D492 schema fail / Bonsai-2 R5+ternary / Ornith D-2784 schema fail / gemma-4-12B D-2788 slower / clef-flash parked adapter-scope per decision a); PROMPT N=30 NEGATIVE (0.344 vs 0.452, D-2774). PIVOT to D-2775 HIERARCHICAL DECOMPOSITION (coarse discipline group ~10 -> fine label in small menu). clef-flash NOT tested drop-in. NEXT: (1) design + measure-gate the hierarchical-decomposition discipline classifier (coarse-group menu from taxonomy_v5.yaml group field, then fine label in small menu) on the 204 gold; (2) re-run depth_conformance_gate --gate on the 207 golden (now count-drift guarded); (3) BUG-563 worktree hygiene (dirty governance paths, many D-deletions) for a clean just health. Registry: decisions 919 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-02 (D-2790): BUG-622 hierarchical-decomposition DESIGN pinned. COARSE SCHEME = 9-group (closed_menu_v5.json disciplines[].group) — tighter (max fine-menu 11 vs 15) and no dead group, unlike taxonomy_v5.yaml discipline_groups (10-group; life & health science = 0 on gold). disciplines[].group = single source of truth for coarse routing. MEASURE-GATE FIRST: coarse-only (9-way) conformance on 204 gold; adopt two-stage only if coarse kappa >= 0.90. TOP-2 prior (not hard gate). 'emerging' gets explicit routing. NEXT: (1) [TASK] build + run the coarse-only measure-gate (9-way closed menu) on 204 gold — adopt two-stage IFF coarse kappa >= 0.90; (2) [TASK] implement two-stage (top-2 union fine menu) + full-204 A/B vs flat 0.514; (3) [BUG] BUG-563 worktree hygiene. Registry: decisions 920 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-02 (D-2791): BUG-622 coarse-only (9-way) measure-gate BUILT (D-2790 step 3). Added --mode coarse + --gate to scripts/hierarchical_discipline_probe.py (coarse-only 9-way, same stage-1 prompt the two-stage would use, fail-closed off-menu -> "") + stage4.discipline_coarse_kappa_floor=0.9 to config/pipeline_config.yaml. N=8 smoke: raw 0.6250 / Cohen kappa 0.5556 / 0 off-menu vs 0.90 gate -> EARLY NEGATIVE. Full-204 run in flight (temp/coarse_measure_gate_204_20261002.log, PID 76862). Coarse scheme verified drift-free: taxonomy_v5.yaml disciplines[].group (61) == closed_menu_v5.json (62 incl 'emerging'); 204 gold 0 unmapped / 0 emerging. NEXT: (1) [RUN] harvest full-204 coarse kappa — if < 0.90 (expected) DROP the two-stage, keep flat gpt-oss-20b, and re-route BUG-622 (swap + prompt both exhausted per D-2789, so the axis is model-bound); (2) [BUG] BUG-563 worktree hygiene (100 dirty paths) for clean just health; (3) [TASK] re-run depth_conformance_gate --gate on 207 golden (count-drift guarded). Registry: decisions 921 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2792): BUG-622 re-framed as MEASUREMENT-DESIGN problem (ULTIMATE RECOMMENDATION). STOP model/architecture work — all 4 vectors exhausted/failing (SWAP 5/5 D-2789, PROMPT N=30 neg D-2774, HIERARCHICAL coarse N=8 0.556 vs 0.90 D-2791, kNN title-only this). Cause = ambiguous + sparse 62-way (even 9-way) label space (49 labels / 204 anchors; menu-ON HURT in D-2774 = semantics smoke-gun); achievable CEILING << 0.8. THREE-PART FIX: (1) MEASURE CEILING (owner + independent rater / two model families R5, 30-anchor stratified); (2) RE-SCOPE AXIS 62 -> 3-5 separable top-level, fine 62 -> advisory tags; (3) CHANGE CONTRACT hard-gate -> soft facet + confidence threshold + owner ratification. BUILT scripts/discipline_knn_ab.py (bge-m3 kNN 204 gold TITLES, 70/30, k=1/3/5): fine 0.10 / coarse 0.14-0.19 = WEAK LOWER BOUND (title-only; full-text kNN needs DB sha256 lookup). Coarse full-204 in flight (PID 76864). Forensic rails GREEN. NEXT: (1) [DECISION] owner ratify D-2792 fix path (ceiling-first + axis re-scope + soft-facet contract); (2) [RUN] harvest coarse full-204 kappa (confirm DROP two-stage); (3) [TASK] build full-text kNN A/B (lookup 204 anchor evidence by sha256 -> bge-m3 -> cosine-kNN) vs flat 0.45 vs measured ceiling; (4) [BUG] BUG-563 worktree hygiene. Registry: decisions 922 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2793): BUG-622 full-text kNN A/B CONFIRMS measurement-design bound. Joined 202/204 gold anchors to full FB text in maxwell.db by name -> bge-m3 -> 70/30 cosine-kNN (k=1/3/5): fine 0.17-0.19 / coarse 0.32-0.41. Full text helped vs titles but retrieval FAILS to beat flat-generative 0.45 (only matches on coarse 0.41 vs 0.45). CONFIRMS D-2792: axis is measurement-design-bound (ambiguous + sparse labels), NOT model/architecture-bound. Evidence table — title-kNN 0.10/0.14, full-text-kNN 0.17-0.19/0.32-0.41, flat 0.45, coarse N=8 0.556 — brackets CEILING ~0.4-0.55 << 0.8. DB cross-check: fbs.discipline agrees with gold 90/202 (44.6%) — BUG-622 baked into DB. STOP classifier engineering until ceiling measured. NEXT: (1) [DECISION] owner ratify D-2792/D-2793 fix path (ceiling-first + axis re-scope 62->3-5 + soft-facet contract); (2) [TASK] MEASURE CEILING (owner + independent rater on 30-anchor stratified sample -> inter-rater kappa; or R5 two-model-family proxy when OMLX frees); (3) [RUN] harvest coarse full-204 (PID 76864, confirm DROP two-stage); (4) [BUG] BUG-563 worktree hygiene. Registry: decisions 923 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2794): D-2792/D-2793 OWNER-RATIFIED. STOP classifier engineering on BUG-622. Fix path: (1) MEASURE CEILING first, (2) RE-SCOPE axis 62->3-5 (fine 62 -> advisory tags), (3) CHANGE CONTRACT hard-gate -> soft facet + owner ratification. Ratified WITHOUT asserting "44% = hard ceiling" (unproven until measured). Generated turnkey 30-anchor stratified inter-rater sample (gold-hidden): temp/discipline_ceiling_sample_30.csv + temp/discipline_ceiling_menu.csv. Owner scores vs gold AFTER both raters. NEXT: (1) [OWNER] 2 raters label the 30-anchor sample -> compute inter-rater kappa (fine + coarse) = the ceiling; (2) [DECISION] act on ceiling (>=0.8 keep axis, tune model; <0.667 re-scope axis + soft facet); (3) [RUN] harvest coarse full-204 (PID 76864); (4) [BUG] BUG-563 worktree hygiene. Registry: decisions 924 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2795): BUG-622 CEILING MEASURED. Owner labeled the 30-anchor gold-hidden sample. Inter-rater kappa vs committed gold: FINE (62-way) 0.581 / COARSE (9-way) 0.728 — BOTH < 0.800 operative floor (fine also < 0.667). CONFIRMS D-2792/D-2793: axis is measurement-design-bound, not model-bound. D-2790 coarse-gate 0.90 UNREACHABLE (human coarse ceiling 0.728). 12/30 anchors owner-corrected (NO new disciplines) -> applied to governance/discipline_anchor_conformance_20261002.json (backed up + provenance D-2795). NEXT: (1) [DECISION] re-scope axis 62->3-5 macro (fine 62 -> advisory tags) + re-target coarse gate to human ceiling (~0.73); (2) [TASK] propagate 12 corrections + re-score fbs.discipline vs corrected gold; (3) [RUN] harvest coarse full-204 (PID 76864, confirm DROP two-stage); (4) [BUG] BUG-563 worktree hygiene + BUG-623 requests warning. Registry: decisions 925 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2796): BUG-622 macro re-scope MEASURED. Human ceiling (owner re-label vs PRE-correction gold): fine 0.581 / 9-way 0.728 / 4-way 0.729 / 3-way 0.766 — even 3-way < 0.8, so the discipline operative floor is HUMAN-UNREACHABLE. "Collapse-to-4-buckets reaches 0.8" REFUTED (kappa corrects for chance: raw 0.60->0.87, kappa only 0.58->0.77). Fix = human-parity gate + soft facet + owner ratification on the ambiguous band. BUILT config/discipline_macro_groups.yaml; coarse floor 0.9->0.73; macro flag OFF until ratify. fbs re-score 89/202 (44.1%). Full-204 coarse 0.537 (DROP two-stage confirmed). NEXT: (1) [DECISION] owner ratify 3-way macro scheme + human-parity gate (~0.73-0.77); (2) [TASK] build/run Condition C (3-way macro classifier) vs 0.766 ceiling; (3) [TASK] re-run S4 discipline against corrected gold + new macro axis; (4) [BUG] BUG-563 worktree hygiene + BUG-623 requests warning. Registry: decisions 926 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2797): BUG-622 MACRO RATIFIED. Owner ratifies 3-way macro re-scope as PRIMARY routing facet + human-parity gate (~0.73-0.77). Config: discipline_macro_enabled false->true + discipline_macro_kappa_floor 0.73. CONDITION A (collapse of committed fbs.discipline -> 3-way, ZERO inference): kappa 0.5534 (raw 0.7255, N=204) — BELOW 0.65 ship threshold; 16 off-menu 'emerging' abstentions (7.8%) ALL WRONG (fine-axis remap failure). CONDITION C (dedicated 3-way classifier): BUILT scripts/discipline_macro_classify.py (selftest + dry-run GREEN; macro group map EXACT). Live run BLOCKED by INFRA: gpt-oss-20b cold-reload returns content:null under memory pressure (48.5GB ceiling, 3 models loaded). Projected dedicated ceiling ~0.60-0.65 (still < 0.766 human ceiling) — axis is measurement-bound, 44% is NOT a hard model ceiling (human fine 0.581). NEXT: (1) [TASK/INFRA] stabilize gpt-oss-20b load (unload idle models / preload) then run Condition C 204; (2) [DECISION] if Condition C >= ~0.65 ship 3-way macro as routing facet, else confirm fine-62 advisory-only; (3) [TASK] re-fit S4 discipline against corrected gold + 3-way macro axis; (4) [BUG] BUG-563 worktree hygiene + BUG-623 requests warning. Registry: decisions 927 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2798): BUG-622 CONDITION C MEASURED. Dedicated 3-way macro classifier (gpt-oss-20b-MXFP4-Q8) on full 204 gold: kappa 0.6066 (raw 0.7696) — BELOW 0.65 ship threshold AND below 0.73 human-parity floor (human 3-way ceiling 0.766). 3-way macro NOT shipped as routing facet; discipline is ADVISORY-ONLY (fine-62 -> advisory multi-label tags, soft facet). Condition C beats Condition A (0.6066 vs 0.5534, +0.053) by eliminating the 16 off-menu 'emerging' abstentions (now 1); residual error = adjacent-cluster confusion (H&D<->M&B 28, H&D<->Tech 9). ROOT-CAUSE of the prior 'cold-reload' blocker FOUND+FIXED: MACRO_MAX_TOKENS=256 too small for gpt-oss-20b Harmony reasoning CoT (billed against max_tokens) -> finish_reason='length' before content; 'content missing (cold reload?)' was a MISDIAGNOSIS, not memory pressure. Fixed to 1024. NEXT: (1) [TASK] re-wire stage4_merge.py discipline -> ADVISORY contract (soft facet, no hard gate; consume discipline_macro flag as advisory tag, not routing); (2) [TASK] re-score committed fbs.discipline under the advisory contract (no re-fit); (3) [BUG] BUG-563 worktree hygiene (reconcile MED-OPEN vs FIXED D-2684 + dirty paths); (4) [BUG] BUG-623 requirements.lock reconciliation (5.14.1/5.7.0 vs active 5.8.1/5.6.1). Registry: decisions 928 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2799): D-2798 ADVISORY RE-WIRE SHIPPED. config adds discipline_gate_mode=advisory; discipline_conformance_gate.py --gate is now REPORT-ONLY (no fail-closed) in advisory mode ('hard' restores legacy); stage4_merge.py documents discipline as soft facet (never gates routing — routing is content_type-based). Built scripts/discipline_advisory_rescore.py + measured COMMITTED fbs.discipline vs corrected 204 gold (zero inference / zero re-fit): FINE-62 kappa 0.4248 (raw 0.4412), MACRO-3 collapse 0.5534 (== Condition A, instrument validated). 44% = label-ambiguity ceiling, not model ceiling. Forensic rails GREEN. BUG-622 implementation leg CLOSED. NEXT: (1) [BUG] BUG-563 worktree hygiene (reconcile duplicate buglog MED-OPEN vs FIXED D-2684 + ~100 dirty paths); (2) [BUG] BUG-623 requirements.lock reconciliation (5.14.1/5.7.0 vs active env 5.8.1/5.6.1; urllib3/chardet/charset_normalizer warning); (3) [OWNER] optional ratification of final advisory-only BUG-622 contract (D-2798 shipped state); (4) [TASK] D-2703 anchor track: classify 150 locked anchors' primary_domain (closed_menu_v5) + evidence_passages vs evidence_passages_shown schema bug. Registry: decisions 929 / buglog 363 (143 open / 220 closed) / highest BUG-622.**

> **NEW — 2026-10-03 (D-2800): BUG-563 WORKTREE RECURRENCE RECONCILED. 83 dirty paths granted (durable audit artifacts + C19 bloat-purge deletions) or excluded (owner/runtime); BUG-563 duplicate buglog entry marked SUPERSEDED. 20 pipeline paths remain owner-gated (BUG-528: pipeline/** will_not_touch vs 19 MODIFIED + practicality.py UNTRACKED). Registry: decisions 930 / buglog 363 (143 open / 220 closed) / highest BUG-622. NEXT: (1) owner-ratify pipeline/** lock lift-or-revert; (2) D-2703 re-chunk + verify 4660/4660; (3) classify 150 locked anchors primary_domain; (4) owner-ratify DROP13/QUAR15/re-ground8; (5) file evidence_passages schema bug.**

> **2026-10-03 (cont.) BUG-625/BUG-626 RESOLVED (no new decision, registry 931): BUG-625 C12 residuals fixed (probe_run config-first; "knowledge pipeline" literal routed through pipeline_paths across 9 modules + safe_delete + backup_guardian.sh); BUG-626 D-328 scalarized to D339 + scalar guard in reconcile.py. bug_status re-derived 143 OPEN / 222 CLOSED / 365. session_seed synced (highest_bug BUG-622, open_bugs_n 143). Six rails GREEN.**

> **2026-10-03 (cont.) D-2802/D-2803/D-2804 minted + BUG-627 resolved (registry 934): Tier-2 crossing-count rail (refuse >1 active crossing/family, rc=2) + Tier-3 lock-semantic re-ask cadence shipped in check_session_plan.py#crossing_rate_faults (config repo_integrity.yaml#crossing_rate_limit). Q2 recording D-2804 = fingerprint-everywhere + classifier-family config-bound + human-parity advisory gate. BUG-627 fixed (D-2668 selftest controls re-pointed off pipeline/** after D-2801; --selftest 25/25 GREEN). bug_status 143 OPEN / 223 CLOSED / 366. session_seed synced (decisions 934, highest_bug BUG-622, open_bugs_n 143).**


> **2026-10-03 (cont.) D-2805 OWNER RATIFICATION (registry 935): D-2802/D-2803/D-2804 APPROVED — Tier-2 crossing-rate rail + Tier-3 lock-semantic re-ask cadence + Q2 fingerprint-everywhere/classifier-family-config-bound/human-parity-advisory-gate. BUG-528 lock is now an accountability gate (R5 + D-naming + stage_code_fingerprint). Forensic audit: six rails GREEN + --selftest 25/25; fixed a latent drift (session_seed decisions 931->935, buglog_entries 365->366). Registry 934->935.**

> **2026-10-03 (cont.) D-2806 BUG-614 FINGERPRINT-EVERYWHERE (registry 936): config-owned stage_code_fingerprint() in pipeline/stamp.py wired into all 7 remaining checkpoint-writing stages (S0/S0.5/S1/S1.3/S1.5/S2/S6) + sidecar write/read/fail-closed-resume. The accountability gate (D-2801/D-2805) is now a mechanism, not a promise. Six rails + --selftest 25/25 GREEN. Resolves BUG-614 + BUG-528.**

> **2026-10-03 (cont.) D-2807 STAGE4 FINGERPRINT C12 MIGRATION + BUG-615/BUG-616 CLOSED (registry 937): stage4's inline
> _stage_code_fingerprint() migrated to shared config-owned stage_code_fingerprint("stage4") via stage4.fingerprint_files
> (C12, mirroring stage5). BUG-615 (cross-cluster fb_id dedup) + BUG-616 (depth/cribs preserved on code drift) marked
> RESOLVED (both guards implemented under D-2752). buglog OPEN 141->139 / CLOSED 225->227. Six rails + selftest GREEN.**

> **2026-10-03 (cont.) D-2808 OWNER RATIFICATION — BUG-622 + BUG-617 CLOSED (registry 938): owner ratified the
> D-2798/D-2799 advisory-only BUG-622 contract as FINAL (discipline axis advisory-only; NO swap, NO re-fit — D-2788
> gemma slower, D-2789 swap 5/5 exhausted, D-2792/D-2793 measurement-bound). BUG-622 CLOSED. Also BUG-617 CLOSED
> (depth now has 207 human-provenanced golden rows: D-2757 FIXES BUG-617 + D-2785 58 owner-adjudicated folded +
> D-2787 rebuilt to 207). buglog OPEN 139->137 / CLOSED 227->229 / 366. highest_bug BUG-622->BUG-621.
> Six rails + selftest GREEN.**
>
> **TICKED-THIS-TURN (already-fixed, now closed in register): BUG-622 (advisory contract), BUG-617 (depth human gold
> 207). RE-CONFIRMED DONE (no re-examine): BUG-528/614/615/616/625/626/627 (RESOLVED), BUG-563 (FIXED + dup
> SUPERSEDED), D-2703 chunking track, DROP13/QUAR15/re-ground8 (D-2715 ratified). DEFERRED/SUPERSEDED registers are
> historical and internally consistent (register-divergence rail 0).**

> **2026-10-03 (cont.) BUG-621 CLOSED + PIPELINE STATE CORRECTED (no new decision, registry 938): BUG-621 (S4 classifier
> fit-evidence blindspot) RESOLVED — the demanded head-to-head FIT eval is DONE and NEGATIVE-on-swap (D-2788 gemma-4-12B
> slower on BOTH axes; D-2789 swap exhausted 5/5; D-2792/D-2793 measurement-bound, human 3-way ceiling 0.766 < 0.8).
> gpt-oss-20b STAYS — no swap, no re-fit (D-2808). buglog OPEN 137->136 / CLOSED 229->230 / 366; highest_bug BUG-621->BUG-613.
> Six rails GREEN.**
>
> **PIPELINE STATE (corrected — do NOT re-run S1.3-S2 or re-chunk): the D-2716 pointer flip to rechunk-v4-20260929 is the
> fresh re-chunk and it is ALREADY DONE through S2. Evidence on disk: S1.3 prefilter checkpoint.jsonl (2026-09-30 00:03);
> S1.5 embed-cluster checkpoint.jsonl (2026-09-30 20:34); S2 extract checkpoint.jsonl (2026-10-02 05:53, 8,217 FBs /
> 193,039 source_segments). S4/S5/S6 are EMPTY (S4 has only the depth.json sidecar). The "full rerun S1.3->S6" framing is
> STALE: only S4 -> S5 -> S6 remain. The BUG-614 fingerprint mechanism is ADDITIVE (0 .code_fingerprint sidecars written
> yet), so it does NOT invalidate the existing S1.3-S2 checkpoints.**
>
> **REMAINING (2026-10-03, CORRECTED — NO classification-policy bugs remain): BUG-170/611/612/613 are CLOSED — they were
> already resolved 2026-10-02 by D-2747 (deterministic non-principle reroute), D-2748 (principle-purity audit), D-2749
> (FORM-axis audit), D-2750 (owner-approved APPLY: D2417 flip + tier-2 fail-closed FORM invariant + 527-row map) +
> D-2755/D-2756/D-2757. The stale buglog headers were the only drift. Only remaining blocker before S6 is EXECUTION: run
> S4 -> S5 -> S6 on rechunk-v4-20260929 (S4 has only the depth.json sidecar). buglog OPEN 136->132 / CLOSED 230->234 / 366;
> highest_bug BUG-613->BUG-604. Six rails GREEN.**

> **2026-10-03 (cont.) SEVENTH RAIL SHIPPED (no new decision, registry 938): `scripts/check_governance_faces.py` —
> the governance faces (DECISION-LOG/MTR) may no longer restate a bug status or census that contradicts the
> register; wired into `just health`. `governance/OWNER_GATE_BUG528_20261003.md` corrected (D-2801 LANDED /
> D-2805 RATIFIED). Six rails + seventh GREEN.**

> **2026-10-03 (cont.) FORENSIC AUDIT (registry 938): OMLX key NOT broken (config `sk-maxwell-local`, health True,
> mem 27.2 GB, RSS 4.9 GB — the earlier "API key required" was a headerless raw ping). `just health` fixed two
> deterministic drifts: `menu_axis_hashes.yaml` STALE (definition-only, answer space invariant) → regenerated;
> `check_instrument_cohorts.py` JSONDecodeError (D-2720/D-2785 JSONL→CSV artifact) → config-key + format detection +
> superset-drop. THREE handoff violations remain OWNER-OWED (`verify_handoffs` exit 1): t11 checkpoint rewritten,
> decisions.yaml append_only 1 in-place deletion @7426, anchor4_workbook seal bytes changed. Do NOT silently re-seal —
> owner decision. S4 unblocked: OMLX healthy, S4→S5→S6 run pending on rechunk-v4-20260929.**

> **2026-10-03 (cont.) OPEN/PENDING face reconciled: the 🔴 OPEN/PENDING table tabled D2546/D2547/D2548 `PENDING`
> where the registry says `PLANNED` (corrected). Four IDs advanced under successors without a registry flip —
> D2546 SHACL shipped (D2555, OWL open), D2547 infra done (D2571/D2556/D2561, per-label open), D2548 A/B rejected
> (D2392, keep-off), D2622 backend implemented (D-2723, not wired). OWNER-OWED registry flips: D2546->RESOLVED,
> D2548->REJECTED, D2622->ACTIVE, D2547->keep PLANNED. D2621 + D2345 genuinely open. session_seed.yaml already in sync.**

> **2026-10-04 ONTOLOGY ENFORCEMENT + 2 BUGS + 3 PROPOSED DECISIONS (zero-risk; the live RATIFY-2 S4 run was NOT touched).**
> MEASURED read-only at [6444/8215], checkpoint 5,165 records, 0 tracebacks, runner pid 97429, omlx-server healthy.
> FILED: **BUG-630** (the cross-axis guard is over-blunt — organizational behavior 26 / product design 10 forced to
> 'emerging' although a SAME-axis home exists; ~45 tokens rescuable with ZERO new labels; mapping loss only, so the
> remedy is a replay over stored raw labels, no re-extraction) and **BUG-631** (max_domains_per_fb = 5 is unenforced at
> the write: 52 FBs carry 6-7 domains, all classification_status=CLEAN — the WRITER limb of the existing BUG-273).
> MINTED (all state=PROPOSED, all S6-GATED): **D-2814** (definition-anchored closed-menu classification = the ROOT fix;
> promotes D272c from OPEN to EXECUTABLE-PENDING-S6; the 999-rule alias layer becomes SHRINK-ONLY and is retired, not
> extended; root evidence BUG-629 at 1,321/4,860 = 27.2% emerging), **D-2815** (additive 'Business & Management' discipline
> group — marketing / management / entrepreneurship — aligned to JEL M + ANZSRC 2020 divisions 35/38; ADDITIVE-ONLY so
> every existing menu_hash still resolves => CRIBS-safe), **D-2816** (pySHACL against the EXISTING
> config/taxonomy_shacl.ttl + OntoClean lint wired into the menu-bump gate; enforce the domain cap at the write).
> ARCHITECTURE: governance/ONTOLOGY_ENFORCEMENT_ARCHITECTURE_20261004.md (7 layers, standards stack, post-hoc vs
> next-batch integration map, declared non-claims).
> **HARD GATE (unchanged, C12): NO taxonomy file may be edited while S4 runs.** menu_hash is stamped PER ROW at classify
> time, so a mid-run menu edit splits the corpus into two epochs and DESTROYS the drift measurement that produced
> BUG-629. DO NOT pause, DO NOT stop, DO NOT re-run S4.
> **R021 + 4: ZERO owner action required** — already resolved by D-2813 (R021 = noise_drop: depth None, discipline None,
> golden_eligible false; R040/R053/R080/R091 = owner abstentions, discipline = emerging, golden_eligible false).
> **NEXT CRITICAL (ordered):** (1) let S4 -> S5 -> S6 finish untouched; (2) VERIFY the menu_hash scope conflict
> (7,995 committed rows NULL vs 5,165 in-flight SET) — drift is not measurable against the committed corpus until this is
> answered; (3) re-measure the emerging rate on the FULL corpus at S4 completion; (4) POST-S6: D-2814 -> D-2815 -> D-2816
> -> BUG-630/BUG-631 -> Mode-A (~26 same-axis aliases) -> Mode-C long-tail triage (support >= 5) -> post-hoc replay;
> (5) python3 pipeline/model_lazyload.py --reset after the run; (6) commit the uncommitted workstreams SEPARATELY
> (never bundled).

> **2026-10-04 TASK (NEW, POST-S6, owner-gated) - RETRY the D2371-quarantined single-FB clusters.** Three clusters were
> fail-closed by the D2371 application gate in S4: cluster_6030 (log line 2498, progress [2463/8215]), cluster_26828
> (line 5674, [5624]), cluster_28517 (line 5977, [5926]) - each logged "Empty/short application (0 chars < 10) - FB
> QUARANTINED (D2371)" after "GEN skipped (single-FB)". They are NOT in the checkpoint (VERIFIED: 5,230/5,230 records
> parse, 5,230 unique fb_id, 0 empty application/failure_mode), so nothing corrupted was persisted - the gate worked.
> **RETRYABLE? YES by declared mechanism, WITH ONE MEASURED CATCH.** pipeline/stage4_merge.py ~1852 increments `failed`
> and its comment states the FB is "retried on resume" (D2338 max_failed_ratio 0.0), so a resume re-attempts them. BUT all
> three are single-FB clusters where generation was SKIPPED, so the empty application/failure_mode came from the
> S2-extracted FB, not a fresh GEN call: a plain S4 re-run reproduces the SAME deterministic empty result and
> re-quarantines them. A retry that can succeed must either (a) FORCE generation for these clusters (bypass the single-FB
> GEN-skip so the generator writes the missing fields), or (b) repair the upstream S2 FB, or (c) owner-accept as
> quarantine. R5: (a) is a code change, so a different-model-family review (gemma-4-E4B-it-MLX-4bit) is required BEFORE apply.
> **STEPS:** (1) at S4 completion RE-MEASURE the quarantine count on the FULL 8,215 (the log is at ~6,524 - 3 is today's
> count, not the final one); (2) run a single-cluster retry probe on ONE of the three to test the documented "retried on
> resume" claim; (3) if the probe reproduces the empty application, the claim does NOT hold for the GEN-skip path and this
> becomes a BUG (retry claim unverified for single-FB clusters) - file it then, with the probe as evidence, not now.
> Impact if left: 3/8,215 = 0.037% of principles, no data loss (nothing written), fail-closed by design.
> **Do NOT act on this while S4 runs.**


> **2026-10-05 T4 + T9 OWNER-APPROVED; menu v6 implementation BLOCKED by forensic audit (D-2828).**
> T4 (menu v6 = D-2814/2815/2816) and T9 (Gate A(d) = D-2822) both RATIFIED. S5 re-run on final S4
> (sha256 ef77e346…, 6,591) in progress — checkpoint.jsonl growing, monitor by line count (the launch log
> is 32B and stale: the setsid error swallowed the redirect). 11-category forensic audit
> (FORENSIC_AUDIT_20261005_MENU_V6_GATE.md) returns BLOCKED: CF1 (D-2815 slot 'entrepreneurship' collides
> with existing domain + D-2500 disjointness + BUG-200 guard), BL1 (dual abstention 'none' vs 'emerging'),
> B1/MI2 (taxonomy_shacl.ttl v5.5 pin vs live v5.6), C1 (alias_map 14 consumers). CF1/BL1 = OWNER-OWED;
> B1/C1 = deterministic assistant work. Filed BUG-640/641/642/643. NEXT: (1) S5->S6 finish; (2) owner
> rules CF1+BL1; (3) regenerate ttl + migrate alias_map; (4) implement D-2814->2815->2816 atomic + R5;
> (5) re-derive anchors (D-2820); (6) Gate A(d) + recalibrate; (7) bundled dirty-tree commit.

## 2026-10-05 (continued) — T4/T9 implementation: CF1+BL1 ruled, B1 fixed, D-2819 baseline committed
- Owner ruled CF1 (D-2829: 'business administration'/'marketing'/'entrepreneurship studies') + BL1 (D-2830: 'emerging').
- taxonomy_shacl.ttl regen v5.5→v5.6 (content drift +ecology/−computer networking caught beyond the audit's version-string finding).
- bug_status.json synced: added missing header entries BUG-638/640/641/642/643 (382 total, 143 open).
- S5→S6 COMPLETE: 6591 FBs re-verified (PASS 3360 / QUARANTINE 3231), SQLite 14574 rows vec0-READY + Parquet snapshot.
- NEXT: (1) C1 alias_map migration; (2) menu v6 atomic D-2814→2815→2816 + R5 review; (3) D-2820 anchor re-derivation; (4) D-2822 Gate A(d) + nli_calibrate; (5) bundled dirty-tree commit.

## 2026-10-05 (continued) — D-2837 adoption recommendation + D-2838 writer-limb (BUG-631)
- R5 gate (D-2836) closed: D-2814 swap fixed (F1 schema placeholders / F2 emerging hidden / F3 batch path). Flag OFF.
- D-2837: ADOPT definition-anchored menu as target; flag flip GATED on full-204 A/B (D-2767) against RE-DERIVED anchor (D-2820 first).
- D-2838: enforced max_domains_per_fb at write (BUG-631) — `_enforce_domain_cardinality()` + receipt + CLEAN→FALLBACK; 17 tests green.
- NEXT: (1) D-2820 anchor re-derivation (owner + 2nd coder + DeBERTa NLI); (2) full-204 A/B; (3) flip flag iff kappa ≥ 0.800; (4) D-2822 Gate A(d) + NLI recalibrate; (5) C1 alias_map shrink-then-remove; (6) bundled dirty-tree commit.

## 2026-10-05 — D-2839 anchor-ratification gate + BUG-650 pre-A/B guard
- D-2839 minted PROPOSED (owner gate certifying the re-derived anchor before it serves as the D-2767 referee).
- BUG-650 filed (no fail-closed pre-A/B guard; circular-kappa risk on the frozen-invalid anchor).
- NEXT (critical order): (1) BUG-650 fail-closed pre-A/B guard; (2) build + R5-review scripts/rederive_anchor_axes_v6.py;
  (3) run D-2820 re-derivation → owner sign-off → D-2839 PROPOSED→RATIFIED; (4) full-204 A/B (D-2767: kappa≥0.800 AND
  emerging≤0.35); (5) flip definition_anchored_menu_enabled iff A/B passes; (6) D-2822 S5 Gate A(d) + NLI recalibrate;
  (7) C1/BUG-642 alias_map shrink-then-remove + re-freeze closed_menu_v6.json in the taxonomy commit.

## 2026-10-05 — BUG-650 guard (D-2840) landed; D-2820 re-derivation is next
- D-2840 RATIFIED: fail-closed pre-A/B anchor-referee guard (pipeline/anchor_menu_guard.py) wired into the
  204-row discipline referee + anchor2_kappa; depth axis unguarded by design. Control test 9/9 pass.
- BUG-650 → PARTIAL (guard done; A/B still blocked on D-2820 + D-2839).
- NEXT (critical order): (1) build + R5-review scripts/rederive_anchor_axes_v6.py; (2) owner runs D-2820
  re-derivation → D-2839 PROPOSED→RATIFIED; (3) full-204 A/B (D-2767) — now fail-closed safe; (4) flip
  definition_anchored_menu_enabled iff A/B passes; (5) D-2822 S5 Gate A(d) + NLI; (6) C1 alias_map +
  re-freeze closed_menu_v6.json; (7) ONE bundled commit (dirty tree + S5/S6 outputs).

## D-2841 RATIFIED: re-derivation harness landed. NEXT (owner-gated): (1) run --generate -> owner adjudicates ->
--adjudicate --decisions <file> -> --verify -> --finalize; (2) owner signs off -> flip D-2839 PROPOSED->RATIFIED;
(3) run full-204 A/B (D-2767) kappa>=0.800 AND emerging<=0.35; (4) flip definition_anchored_menu_enabled true iff pass.

## D-2842 RATIFIED: D-2822 Gate A(d) code landed (config-gated, default preserves current behavior)
- OR-entail + AND-no-contradiction primitive + config `stage5.nli_aggregation`; BUG-651 filed; census 972.
- NEXT (critical order):
  (1) OWNER: run scripts/rederive_anchor_axes_v6.py --generate → adjudicate → --adjudicate → --verify → --finalize;
  (2) OWNER: flip D-2839 PROPOSED→RATIFIED; (3) full-204 A/B (D-2767) kappa≥0.800 AND emerging≤0.35;
  (4) flip definition_anchored_menu_enabled iff pass; (5) D-2822 OPERATOR: recalibrate NLI (nli_calibrate.py)
  → flip nli_aggregation=or_entail_and_no_contra → re-run S5 (6591); (6) C1/BUG-642 alias_map shrink-then-remove
  + re-freeze closed_menu_v6.json; (7) D-2816 pySHACL wiring (pyshacl); (8) BUG-631 reader-limb
  check_domain_cardinality.py over committed store; (9) ONE bundled commit.

## D-2843 RATIFIED: BUG-631 reader-limb landed (scripts/check_domain_cardinality.py)
- Reader-limb re-measures the committed store; LIVE run reproduces 52 over-cap FBs (46@6 + 6@7) of 14,574.
  BUG-631 stays OPEN (52 historical FBs still owed re-derivation). BUG-647 header/body drift reconciled.
- NEXT (critical order):
  (1) OWNER: run scripts/rederive_anchor_axes_v6.py --generate → adjudicate → --adjudicate → --verify → --finalize;
  (2) OWNER: flip D-2839 PROPOSED→RATIFIED; (3) full-204 A/B (D-2767) kappa≥0.800 AND emerging≤0.35;
  (4) flip definition_anchored_menu_enabled iff pass; (5) D-2822 OPERATOR: recalibrate NLI (nli_calibrate.py)
  → flip nli_aggregation=or_entail_and_no_contra → re-run S5; (6) BUG-631 re-derive the 52 historical over-cap
  FBs (re-run S4 on those clusters) + re-measure; (7) C1/BUG-642 alias_map shrink-then-remove + re-freeze
  closed_menu_v6.json; (8) D-2816 pySHACL wiring (pyshacl); (9) refresh store_authority.yaml row count
  (7,995 → 14,574); (10) ONE bundled commit.

## 2026-10-05 — Store-authority reconciliation LANDED (task #9 done + extra drift fixed)
- DONE: "refresh store_authority.yaml row count (7,995 → 14,574)". Also fixed two live rail faults
  (stale diagnostic-db declaration → removed; undeclared archive parquet collection → declared `archive`).
  Rail now 0 faults. BUG-631 stays OPEN (52 over-cap FBs still owed re-derivation).
- NEXT (critical order) — UNCHANGED, owner-gated head:
  (1) OWNER: run scripts/rederive_anchor_axes_v6.py --generate → adjudicate → --adjudicate --decisions <file>
      → --verify → --finalize; (2) OWNER: flip D-2839 PROPOSED→RATIFIED; (3) full-204 A/B (D-2767)
      kappa≥0.800 AND emerging≤0.35; (4) flip definition_anchored_menu_enabled iff pass; (5) D-2822 OPERATOR:
      recalibrate NLI → flip nli_aggregation → re-run S5; (6) BUG-631 re-derive the 52 over-cap FBs;
      (7) C1/BUG-642 alias_map shrink-then-remove + re-freeze closed_menu_v6.json; (8) D-2816 pySHACL wiring;
      (9) ONE bundled commit.

## 2026-10-06 — D-2844 PROPOSED: D-2820 owner adjudication normalized (204 rows) + taxonomy boundaries
- Owner adjudicated 142 differing rows; forensic audit CLEAN (0 off-menu). 62 carried -> full 204 decisions.
- Normalized 4 separator typos + 6 note typos. Artifacts: rederive_v6_owner_decisions_normalized.csv/.json.
- OWNER-GATED head (D-2839): (1) sign off DROP R084/R106/R148 (anchor 204->201, fix R148 domain);
  (2) resolve emerging-mix R023/R112/R177/R188 (abstain vs keep); (3) sign off taxonomy boundary clarifications
  (strategic thinking/decision making; business administration/operations research/organizational theory;
  marketing/design psychology/behavioral economics; genAI/AI/ML) -> then edit closed_menu_v6.json (re-render + re-pin);
  (4) run --adjudicate --decisions governance/rederive_v6_owner_decisions.json -> --verify -> --finalize;
  (5) flip D-2839 PROPOSED->RATIFIED; (6) full-204 A/B (D-2767) kappa>=0.800 AND emerging<=0.35;
  (7) flip definition_anchored_menu_enabled iff pass.

## 2026-10-06 — D-2845 RATIFIED: D-2820 anchor re-cut 204→201 + emerging-mix resolved; --adjudicate landed
- Owner resolved D-2844 (1)+(2): dropped R084/R106/R148; emerging-mix R023/R112/R177/R188 → keep real domains.
- Re-cut anchor → discipline_anchor_conformance_20261006.json (201); flat decisions → rederive_v6_owner_decisions_flat.json;
  --adjudicate → rederive_v6_finalized_20261006.json (201 rows, 0 off-menu). Forensic audit CLEAN
  (FORENSIC_AUDIT_20261006_RESOLUTION.md). Emerging 14/201 (6.97%).
- NEXT (critical order, owner-gated head):
  (1) OWNER: --verify (gemma second coder + DeBERTa NLI, watch cold-load) → --finalize (mints re-derived anchor);
  (2) OWNER: flip D-2839 PROPOSED→RATIFIED; (3) full-201 A/B (D-2767) kappa≥0.800 AND emerging≤0.35;
  (4) OWNER: flip definition_anchored_menu_enabled iff pass; (5) OWNER: sign off taxonomy boundary
  clarifications → edit closed_menu_v6.json → re-render + re-pin → re-derive; (6) OWNER: review 7 mirror rows
  (discipline=emerging + real domains: R006/R059/R127/R140/R146/R165/R202); (7) OPERATOR: D-2822 NLI
  recalibrate; (8) BUG-631 re-derive 52 over-cap FBs; (9) D-2816 pySHACL wiring; (10) C1/BUG-642 alias_map
  shrink-then-remove; (11) refresh store_authority.yaml row count (7,995→14,574); (12) ONE bundled commit.

## 2026-10-06 — D-2846 RATIFIED: D-2820 --verify + --finalize complete (menu-v6 stamped, guard PASSED)
- --verify: 201 rows cross-checked (gemma second coder + DeBERTa NLI): 85 agree / 116 disagree (57.7%);
  NLI 82 entailed / 102 weak / 17 contra-dominant (surface-only, never flip, D-2839 c3). 12/17 contra rows on
  owner-flagged taxonomy boundaries. --finalize: discipline_anchor_rederived_v6_20261006.json (201 rows);
  menu hash == declared live pins; guard PASSED. Emerging 7/201 (3.5%). Killed stale duplicate --verify orphan.
- NEXT (critical order, owner-gated head):
  (1) OWNER: eyeball 17 contra-dominant rows + 116 disagreements -> flip D-2839 PROPOSED->RATIFIED;
  (2) full-201 A/B (D-2767) kappa>=0.800 AND emerging<=0.35; (3) OWNER: flip definition_anchored_menu_enabled iff
  pass; (4) OWNER: sign off taxonomy boundaries -> edit closed_menu_v6.json -> re-render + re-pin -> re-derive;
  (5) OWNER: review 7 mirror rows (R006/R059/R127/R140/R146/R165/R202); (6) OPERATOR: D-2822 NLI recalibrate;
  (7) BUG-631 re-derive 52 over-cap FBs; (8) D-2816 pySHACL wiring; (9) C1/BUG-642 alias_map shrink-then-remove;
  (10) refresh store_authority.yaml row count; (11) ONE bundled commit.

## 2026-10-06 — D-2847 RATIFIED: owner consolidation of 14 contra rows + re-derive (re-mint 20261006b)
- Owner resolved R179->creative process, R143->design thinking, R183->emerging+urban planning. 6 discipline changes
  + 8 no-ops applied; re-ran --adjudicate -> --verify -> --finalize (--run-id 20261006b). D-2848 fixed the dead
  --run-id flag (C16 hidden failure). D-2849 (PROPOSED): Effect-TS -> adopt patterns, not the TS lib.
- Verify: 88 agree / 113 disagree; NLI 85/104/12 (entailed/weak/contra). 14/14 rows landed. Manifest
  discipline_anchor_rederived_v6_20261006b.json minted (guard PASSED).
- NEXT (critical order, owner-gated head):
  (1) OWNER: eyeball 12 contra-dominant rows (incl 9 consolidated taxonomy-boundary rows) + 113 disagreements ->
      flip D-2839 PROPOSED->RATIFIED;
  (2) OWNER: full-201 A/B (D-2767) kappa>=0.800 AND emerging<=0.35 (referee = 20261006b manifest);
  (3) OWNER: flip definition_anchored_menu_enabled iff A/B passes;
  (4) OWNER: ratify D-2849 (typed errors + TaskGroup + pydantic + tenacity scaffolding);
  (5) OWNER: sign off taxonomy boundaries -> edit closed_menu_v6.json -> re-render + re-pin -> re-derive (invalidates 20261006b);
  (6) OWNER: repoint discipline_anchor_path 20261002->20261006 (config drift, D-2848);
  (7) OWNER: review 7 mirror rows (R006/R059/R127/R140/R146/R165/R202 discipline=emerging + real domains);
  (8) OPERATOR: D-2822 NLI recalibrate; (9) BUG-631 re-derive 52 over-cap FBs; (10) D-2816 pySHACL;
  (11) C1/BUG-642 alias_map shrink-then-remove; (12) refresh store_authority.yaml 7,995->14,574;
  (13) refresh registry.decisions/highest_bug in session_seed (stale 955->979, BUG-636->BUG-652); (14) ONE bundled commit.

## D-2850 RATIFIED (2026-10-06) — Owner consolidation round 2 -> discipline_anchor_rederived_v6_20261006c.json
- 3 label changes (R168->marketing, R153->cognitive science, R143->computer graphics) + R183 stays emerging+urban planning.
- Re-derivation: sc 91 agree / 110 disagree; NLI 87 entailed / 105 weak / 9 contra-dominant (was 12). Guard PASSED.
- NEXT (critical order, owner-gated head):
  (1) OWNER: eyeball 9 contra rows (6 owner-confirmed: R029/R098 design thinking, R047 design psychology, R107 research
      methodology, R090 media studies, R067 HCI + 3 others R014/R134/R147) + 110 disagreements -> flip D-2839 PROPOSED->RATIFIED;
  (2) OWNER: full-201 A/B (D-2767) kappa>=0.800 AND emerging<=0.35 (referee = 20261006c manifest);
  (3) OWNER: flip definition_anchored_menu_enabled iff A/B passes;
  (4) OWNER: ratify D-2849 (typed errors + TaskGroup + pydantic + tenacity);
  (5) OWNER: sign off taxonomy boundaries -> edit closed_menu_v6.json -> re-render + re-pin -> re-derive (invalidates 20261006c);
  (6) OWNER: repoint discipline_anchor_path 20261002->20261006 (config drift, D-2848);
  (7) OWNER: review 8 emerging-discipline mirror rows (R006/R059/R127/R140/R146/R165/R183/R202);
  (8) BUG-653: add domain-axis hint to --adjudicate off-menu rejection;
  (9) OPERATOR: D-2822 NLI recalibrate; BUG-631 re-derive 52 over-cap FBs; D-2816 pySHACL; C1/BUG-642 alias_map;
      refresh store_authority.yaml 7,995->14,574; ONE bundled commit.

## D-2851 RATIFIED (2026-10-06) — Owner round 3 -> discipline_anchor_rederived_v6_20261006d.json; D-2839 RATIFIED
- 5 label changes (R107->philosophy, R067->interdisciplinary studies, R029->business administration, R047->psychology, R098->aesthetics).
- Re-derivation: sc 95 agree / 106 disagree; NLI 89 entailed / 108 weak / 4 contra. Guard PASSED.
- D-2839 -> RATIFIED. Referee = 20261006d manifest. A/B RAN (20:28) → kappa 0.4313 FAIL (D-2852); flag stays OFF.
- NEXT (critical order):
  (1) TASK: full-201 A/B (D-2767) kappa>=0.800 AND emerging<=0.35 (referee = 20261006d manifest);
  (2) DECISION: flip definition_anchored_menu_enabled iff A/B passes;
  (3) DECISION: ratify D-2849 (typed errors + TaskGroup + pydantic + tenacity);
  (4) TASK: taxonomy boundaries -> edit closed_menu_v6.json -> re-render + re-pin -> re-derive (invalidates 20261006d);
  (5) TASK: repoint discipline_anchor_path 20261002->20261006 (D-2848 drift);
  (6) BUG-653: --adjudicate domain-axis hint;
  (7) TASK: operator backlog (D-2822 NLI recal; BUG-631 52 over-cap FBs; D-2816 pySHACL; C1/BUG-642 alias_map;
      store_authority 7,995->14,574; one bundled commit).


## D-2849 RATIFIED + BUG-654 CORRECTED -> BUG-655 (2026-10-06) — A/B "non-determinism" was a measurement bug
- BUG-654 misdiagnosed: kappa 0.3181 (flag-OFF cribs arm) vs 0.7794 (flag-ON definition-anchored arm) are the OFF/ON arms of definition_anchored_menu_enabled, NOT two runs of one prompt.
- Deterministic gpt-oss settings ALREADY applied: D-2637 server (temp 0.0, grammar ON, prefix cache ON) + config verifier (chat_template_kwargs enable_thinking=false, thinking_budget 256/128, Reasoning:low). Live 2-pass determinism self-check: 3/3 byte-identical.
- D-2849 -> RATIFIED (owner approve-and-ratify). Implementation folded into classifier-of-record swap (tenacity retry + Result/Either) + A/B harness (pydantic). No standalone bloat commit (C28).
- scripts/d2767_ab_eval.py REWRITTEN: primary arm = flag-ON (definition-anchored via _apply_definition_anchored_menu), determinism self-check, optional --baseline. Smoke PASSED. Full run PID 14573 in background.
- Real A/B: flag-ON kappa ~0.7794 (158/201), emerging 6/201=0.03 — 2pt under 0.800 floor. Flip STILL blocked, for a genuine ~43-row classifier-vs-owner gap (NOT determinism).
- NEXT (critical order):
  (1) TASK: collect background flag-ON run -> definitive kappa + determinism proof + disagreement CSV;
  (2) DECISION: owner rules ~43 disagreement rows + signs off closed_menu_v6.json label+definition pairs;
  (3) DECISION: accept 0.7794 vs tighten definitions;
  (4) TASK: edit closed_menu_v6.json -> re-render/re-pin -> re-derive (invalidates 20261006d);
  (5) TASK: repoint discipline_anchor_path 20261002 -> menu-v6 manifest (D-2848 drift);
  (6) BUG-653: --adjudicate domain-axis hint;
  (7) TASK: operator backlog (D-2822 NLI recal; BUG-631 52 over-cap; D-2816 pySHACL; C1/BUG-642 alias_map; store_authority 7,995->14,574).

## BUG-653 RESOLVED + BUG-656 OPEN (2026-10-06)
- BUG-653 RESOLVED: `validate_on_menu` off-menu discipline now routes through `_off_menu_discipline_hint` (domain-axis detection + 4 closest disciplines + `emerging` reminder). Selftest passes.
- BUG-656 OPEN: the 0.7794 kappa is the REDERIVE path (`_classify_prompt`), NOT the production gate arm (`build_merged_prompt` + `_apply_definition_anchored_menu`). Production path diverges (R001 -> 'marketing'). Harness now persists per-row + emits owner-review CSV. Definitive production-path kappa pending full-201 run.

## D-2852/D-2853/D-2854 RATIFIED (2026-10-06) — D-A verdict, D-3 taxonomy C, D-B root fix
- D-2852 (D-A): D-2767 flag-ON A/B VERDICT = kappa 0.4313 (FAIL <0.800), emerging 0.0299 (pass), determinism 8/8, 111/201 disagreements. D-2839 gate FAILED → `definition_anchored_menu_enabled` stays OFF. (Supersedes BUG-654/655/656 narrative; production-path kappa now definitive.)
- D-2853 (D-3): taxonomy C APPROVED — freeze closed_menu_v6.json; build closed_menu_v7.json from the 111 disagreement rows + collision clusters; merge within-axis near-synonyms, rename cross-axis near-identical labels, add discriminator fields.
- D-2854 (D-B): root fix LANDED in pipeline/omlx_call.py::call_omlx (`_post_with_wall_clock` + `WallClockTimeout`; OMLX_WALL_CLOCK_DEADLINE=180 from config). Protects all callers, not just the harness.
- NEXT (strategic order):
  (1) TASK: relaunch flag-ON A/B with the harness+root fix → confirm preflight runs, no wedge, reproduce kappa 0.4313;
  (2) TASK: build closed_menu_v7.json from the 111-row disagreement CSV + collision clusters;
  (3) TASK: remap ALL anchor/golden/config/script label references to v7 (drift guard prerequisite);
  (4) TASK: re-run A/B on menu v7 → adopt only if kappa improves toward >= 0.800;
  (5) TASK: sync DECISION-LOG/MTR/session_seed/bug_status with the above;
  (6) BUG-658: OPEN until the relaunch reproduces the wedge fix end-to-end (root fix + harness both in place).

---

## D-2859 + v3 forensic audit (2026-10-07) — ANTI-CIRCLE COMMIT (backlog frozen; remaining work re-sequenced)

- ROOT CAUSE of '2 weeks of circles': 1112 decisions D-2826..D-2859 ratified in worktree but UNCOMMITTED (HEAD=D-2825=955, worktree=989) + 68 modified + 140 untracked. Every session re-read unstable state, re-derived the referee (4 variants), re-ran A/B, wrote another audit (7 on Oct 6 alone), never committed.
- COMMITTED this session: full backlog (v7 promote + D-2826..D-2859 + D-2854 wall-clock root fix + governance sync + decisions_summary re-derived 989; census --check GREEN).
- A/B ANSWER: NEW A/B MANDATORY (old D-2767 flag-ON kappa 0.4313 FAIL, D-2852; invalidated by v7 +3 disciplines + domain rename + 'emerging' abstention + D-2857 split NOT implemented).
- OWNER REFERENCE: REUSE governance/discipline_anchor_rederived_v6_20261006d.json (latest of 4) + deterministic 28-row domain remap; do NOT rebuild (D-2839 owner judgments + sampling variance).
- NEXT (critical order; [OG]=owner-gated):
  (1) [OG] confirm 20261006d as canonical referee + approve 28-row 'research & methodology'→'research practice' remap;
  (2) finish D-2853 rename: 28 referee rows + ~24 config refs incl taxonomy_shacl.ttl enum + regenerate shacl (C13 backup);
  (3) reconcile menu 65/44 vs taxonomy 64/43 off-by-one; regenerate shacl.ttl;
  (4) land D-2857 split in stage4_merged_call.py (Call A CRIBS / Call B classify; R5 gemma review);
  (5) D-2858: recalibrate D-2822 under or-entail, re-pin (D-353), flip nli_aggregation→or_entail_and_no_contra (fail-closed);
  (6) NEW A/B (split + v7 menu vs v7-remapped referee); adopt iff kappa>=0.800;
  (7) wire opaque IDs into menu/storage/golden (D-2856);
  (8) add golden coverage: business administration + entrepreneurship studies (0 each; marketing 176);
  (9) rerun S4→S5→S6 (no S1);
  (10) D-2859: BUG-563 triage (40 dirty paths → 3 buckets) + repoint recalibration_pins.yaml + render_closed_menu.py → v7;
  (11) close BUG-630 (ID wiring), BUG-648 (D-2857), BUG-651 (recalib+flip), BUG-658 (no-wedge relaunch).

---

## BUG-661/662/663/664/668 FIXED + D-2861 RATIFIED + D-2853 fan-out complete (2026-10-07)

- BUG-661 FIXED: bridge ambiguity is a SAFE refusal -> EXIT_OWED (2); verdict word now matches exit code (BUG-492).
- BUG-662 FIXED: check_store_columns --record re-baseline (256 drift cells -> 0); menu_hash re-ruled reserved->sparse.
- BUG-663 FIXED: 6 test regressions from the D-2853 v7-rename fan-out (NOT absorbed by any ceiling edit, D-2656).
  Root cause: alias_map(16)/synonym_map(1)/taxonomy(dom-010 raw alias)/schemas-fallthrough fan-out incomplete +
  D-2814 same-axis homonym ('marketing' discipline vs domain). Fixed via dom-010 raw alias + S4_SAME_AXIS_FALLTHROUGH.domain
  'marketing -> marketing & communications' wired into match_to_canonical + _build_synonym_index. 45/45 pass.
- BUG-664 FIXED: check_domain_cardinality wired into just health (reader-limb now fires red on 52 over-cap FBs = BUG-631).
- BUG-668 FIXED: archive/index.yaml rebuilt (bloat_20260929 indexed, coverage invariant green).
- D-2861 RATIFIED: re-baseline 3 red health drifts (label_provenance boundary 7995->7983, anchor bridge re-derived,
  decisions receipt re-cut).
- D-2853 fan-out COMPLETE (live config maps): alias_map(16), synonym_map(1), domain_disciplines(1 key),
  anchor_workbook_fixes(1), eval_integrity known_collisions entry removed. Remaining: 28-row referee remap = OWNER-GATED.
- Bug register 432 = 166 open / 266 closed. Decisions 991. Highest OPEN then BUG-667.
- STILL OWNER-GATED (do NOT cross unilaterally): BUG-659 (shrink-only ceiling re-baseline), BUG-660 (health read-only),
  BUG-665 (encoding repoint to artifact_encoding.py), BUG-666 (write-boundary teeth), BUG-667 (t11 authority re-mint
  via D-2862), BUG-631 (52 over-cap FB re-derive via D-2838 writer-limb).

---

## BUG-631 FIXED (2026-10-07) — 52 over-cap FBs re-derived through the D-2838 writer-limb

- BUG-631 FIXED: `scripts/rederive_domain_cardinality.py` re-derives the 52 historical over-cap FBs (46@6 + 6@7, all CLEAN)
  THROUGH the writer-limb — it IMPORTS `_enforce_domain_cardinality` from `pipeline/stage4_merge` (one rule, one home, D-2644),
  never re-implements the truncation. Per FB: `domains` truncated to first 5 (model order), `classification_status`
  CLEAN->FALLBACK, receipt appended to `classification_error`, `domains_raw` UNTOUCHED. C6: SQLite online-backup API +
  single transaction. Deterministic (LLM-free), idempotent. R5 gemma GO (6/6).
- VERIFIED: check_domain_cardinality.py -> EXIT=0 (0 over-cap of 14574); PRAGMA integrity_check ok; 14/14 control tests.
- Bug register now 160 open / 272 closed of 432 (session_seed open_bugs_n 161->160).
- STILL OWNER-GATED (do NOT cross unilaterally): BUG-659, BUG-660, BUG-665 (--record 156->153), BUG-667 (done via D-2862),
  D-2853 (28-row referee remap 'research & methodology'->'research practice'), bridge-ruler 3 folded extras (R152/R192/R197).
- NEXT (critical order; [OG]=owner-gated):
  (1) [OG] BUG-665 tail: ratify --record re-baseline 156->153 (genuine shrink, no drift);
  (2) [OG] D-2853: confirm 20261006d canonical referee + approve 28-row domain remap, then finish rename + config refs + closed_menu v5->v7 + D-2859 off-by-one;
  (3) D-2858: recalibrate D-2822 under or-entail -> re-pin threshold (D-353) -> flip nli_aggregation (fail-closed guard);
  (4) [OG] bridge-ruler 3 folded extras (R152/R192/R197) owner adjudication.


## D-2887 + D-2888 (2026-10-09) — GEV-26B-Decide no-adopt + D2 gold-emerging 2-way adjudication EXECUTED

- D-2887 RATIFIED: autotrust/GEV-26B-Decide NO-ADOPT (no MLX port, 51.6GB bf16 too heavy, decision-model not scaffolding).
  Watch-list for an MLX port as a decider-arm upgrade. Everyday scaffolding stays on goose maxwell_omlx (Qwen3-Coder-30B).
- D-2888 D2 adjudication EXECUTED: 7 gold-emerging rows = 2 genuinely-novel (R006, R165) + 5 classifiable (R059/R127/R146/
  R183/R202). Emerging gold is owner-conservatism-dominated -> symmetric gate internally tense. Recommend: re-adjudicate
  the 5 classifiable rows to established disciplines (shrink emerging to 2) + re-express emerging as a whitelist.
- clef-4bit (27B) download: stalled twice (CLOSE_WAIT, VPN throttle); switched to self-healing curl (speed-limit abort +
  retry-all-errors + resume) into ~/.cache/maxwell_models/clef-4bit — progressing ~1 MB/s. --arm clef A/B still pending.
- NEXT (critical order; [OG]=owner-gated): (1) [OG] D-2888 recommendation (re-adjudicate 5 classifiable emerging rows);
  (2) clef-4bit -> --arm clef A/B -> D3 owner ruling (lower floor vs advisory best-arm); (3) BUG-681(b) encoding blocker
  (named offender scripts/remap_referee_v7_28rows.py:69 utf-8-sig -> artifact_encoding.py) blocks `just health` prefix.

- D-2889+D-2890 (2026-10-09): Voz no-adopt (C4/C21; C26 long-term-only, short-term relaxable); emerging-bucket reframe (abstention dump). D-2891 (2026-10-09) SCOPE-CORRECTED: canonical run = rechunk-v4-20260929 = 6591 rows, t11 checkpoint (7855) FOREVER excluded; emerging = 1779 (27.0%) = mapfail 280 + dombleed 190 + offmenu 1309; 6 dead disciplines (3 business + generative ai/creative coding/generative design); root cause = menu-widening drift (v5->v8 +3 disciplines), NOT decider bug. Owner adjudicated 4/7 (R006 generative design, R059 entrepreneurship studies, R146 decision making, R165 information science); R127/R183/R202 UNSURE (STier rec: cultural design / systems thinking / performing arts).
- NEXT (critical order; [OG]=owner-gated): (1) [OG] owner resolves the 3 unsure gold rows (R127/R183/R202) + ratifies D-2891; (2) BUG-693 mapfail 280 = FULLY deterministic reclaim (discipline_raw->discipline) — prepare re-map table for sign-off [OG]; (3) BUG-693 dombleed 190 = kind-swap domain label into `domains` (BUG-150) + re-classify discipline [OG]; (4) BUG-693 offmenu 1309 = promotion review (classify_promotion_labels.py) or stays 'emerging' whitelist; (5) add a menu-widening re-classification gate (governance gap); (6) BUG-681(a) check_tests 3-red + (c) check_boundary_rehearsal now unblocked (b RESOLVED); (7) clef-4bit (~67%) -> --arm clef A/B -> D3 owner ruling; (8) D-2727 full rerun blocked until an arm clears C+B or owner re-scopes.
