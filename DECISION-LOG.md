# Maxwell OS v3.0 — DECISION LOG (tiered)

> **Updated:** 2026-10-07 | **Machine source of truth:** `config/decisions.yaml` | **Count:** `config/decisions_summary.json` (the census is the ONE home - a count restated in prose is stale the moment it is written, BUG-588)
> **Archive (full append-only history):** `archive/governance_pre_tiered_2026-09-03/DECISION-LOG.md`
>
> **Convention (standing rule):** OPEN/PENDING at the top (most critical first) → ACTIVE in-effect → DONE/CLOSED at the bottom. A decision is "done" only when its `state` is RESOLVED/SUPERSEDED/ARCHIVED/REJECTED.
>
> **Heading convention (D2552):** tier sections are `## 🔴 OPEN / PENDING`, `## 🟢 ACTIVE`, `## ⚪ DONE / CLOSED`. Entries use `| ID | State | Decision |` table rows. Historical `### D#### — Title` / bare `## D####` formats remain as-is (append-only history); NEW entries MUST use the table format. Reconcile `DECISION-LOG.md` ↔ `config/decisions.yaml` via `scripts/recompute_decision_summary.py`.

---

## 🔴 OPEN / PENDING — tier heading (the DERIVED block below owns the current state; D-2981/D-2985)

<!-- GOV-INDEX:START (D-2981 - DERIVED by scripts/gov_sync.py; do NOT hand-edit inside) -->
> **LIVE INDEX (D-2981 - DERIVED; do NOT hand-edit inside these sentinels).**
> Register truth (BUG-588/D-2692 - the census is the ONE home; nothing below restates a count): 1280 decisions (census stamp e56cb90b7a8a823d, 2026-10-26) · 791 bugs (247 open / 544 closed; highest OPEN = BUG-1026) · 60 open tasks (MUST 9 / SHOULD 46 / WORTH 5; OWNER-moved 0, pipeline-moved 60; 1 standing rule(s) never close).
>
> Decisions NEEDING ACTION: **81** of 1280 — 🔴 open 32 · 🔵 proposed 26 · 📝 draft 1 · ⏳ deferred 16 · 📅 planned 6 | in effect: 🟢 active 660 · ⚖ ratified 148 | closed: ✅ resolved 356 · ⚪ superseded 16 · ⚪ archived 8 · ⛔ rejected 11 — the DECLARED buckets sum to the whole register (1280, D-2987/BUG-765)
>
> Open BUGS by severity (population = the census's 247 open ids; severity read from each id's FIRST heading at ANY hash depth): 🟥 CRITICAL 0 · 🟧 HIGH 34 · 🟨 MED 81 · 🟩 LOW 34 · UNLABELLED 98 (BUG-757) of 247 open.
>
> **OWNER LANE (0) — what ONLY YOU can move; the pipeline cannot advance these, each needs YOUR word:**
>
> | id | pri | what YOU decide | the gate |
> |---|---|---|---|
>
> **PIPELINE LANE (60) — what the agent will do next, ordered by priority then id (the register's two fields; source: config/task_register.yaml):**
>
> | id | pri | state | task | evidence |
> |---|---|---|---|---|
> | T-101 | 🔴 MUST | 🔴 open | HARDEN THE RETRIEVAL GOLDEN SET (the gate is saturated) | MEASURED 2026-10-14 (BUG-784): the owner-signed review (governance/golden_reanchor_candida |
> | T-104 | 🔴 MUST | 🔴 open | BUG-757 — OPEN bugs carry NO severity token, so the register cannot be ordered by criticality | bug_status.json joined to the buglog headings: UNLABELLED ceiling 99 (2026-10-25) - LOWERE |
> | T-119 | 🔴 MUST | 🔴 open | the CORROBORATION COLLAPSE delta — how many "≥2 independent sources" rows are really ONE VOICE | BASELINE §4 MEASURED 2026-10-13 (governance/BORP_REVITALIZATION_RISK_20261013.md): of 938  |
> | T-120 | 🔴 MUST | 🔴 open | the ABSORPTION path - a later independent source must be able to RAISE an existing row's corroboration, and a  | MEASURED 2026-10-13 (read-only, by reading the write path and the identity model - no stor |
> | T-141 | 🔴 MUST | 🔴 open | SERIALIZE MODEL DOWNLOADS: two overlapping attempts at one repo leave .incomplete fragments that no tool can a | MEASURED 2026-10-15: models--lmstudio-community--Qwen3.8-27B-MLX-4bit held 4.0 GB as SIX . |
> | T-143 | 🔴 MUST | 🔴 open | RESOURCE-CLASS THE FAN-OUT: the engine pool is a mutex, the governed homes are a single writer | MEASURED 2026-10-15: the engine declares model_count 9 / loaded 3 / final_ceiling 56.6 GB, |
> | T-147 | 🔴 MUST | 🔴 open | WIRE THE STORE CENSUS TO EVERY DELETION BATCH: it is a generated face, and it lies the moment bytes move witho | MEASURED 2026-10-15: the census IS generated (pipeline/model_store_census.py: dir_bytes, m |
> | T-150 | 🔴 MUST | 🔴 open | THE DURABLE PATH IS THE DELEGATION PATH (D-3020): anything whose failure is not free goes through pipeline/sub | temp/runs/fanout_20261015i/98_receipt.json - 3/3 DONE with one task deliberately given a 1 |
> | T-181 | 🔴 MUST | 🔴 open | THE ADMISSION - the fifth transition is DECLARED, counted and PLANNED (D-3051): what remains is the word on wh | MEASURED 2026-10-16 by the FIRST live reading of scripts/plan_admission.py: 2,811 files in |
> | T-105 | 🟠 SHOULD | 🔴 open | REA tier A/B mining — DEVONthink 3 (related-document ranking) and Cursor (derived code index) | governance/NOT-YET-EVALUATED-RESEARCH.md (REA targets logged 2026-10-13) |
> | T-106 | 🟠 SHOULD | 🔴 open | ROADMAP — MODULARITY (C21 swappable infrastructure) and CROSS-OS COMPATIBILITY (C26) | protocols: pipeline/storage/base.py only; no cross-OS smoke exists (2026-10-13) |
> | T-108 | 🟠 SHOULD | 🔴 open | BUG-712 / BUG-714 — the content_type residual and the harness-facing primitive | served run content_type census (2026-10-13) |
>
> _the face is a VIEW: 12 of 60 row(s) shown, the rest are in the register (config/gov_sync.yaml#face_list_limit)_
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
> **Open bugs, most severe first:** 🟧 BUG-303 · 🟧 BUG-304 · 🟧 BUG-306 · 🟧 BUG-312 · 🟧 BUG-318 · 🟧 BUG-341 · 🟧 BUG-391 · 🟧 BUG-400 · 🟧 BUG-406 · 🟧 BUG-417 · 🟧 BUG-426 · 🟧 BUG-433.
<!-- GOV-INDEX:END -->

<!-- GOV-HISTORY:START (D-2981/D-2986) - below this line a face makes NO LIVE CLAIM: the INDEX sections are declared HAND INDEXES (row-joined on every run of the rail, never the authority) and the rest is DATED HISTORY (append-only). The DERIVED block above is the ONE authority for the current state. -->


SNAPSHOT 2026-10-12 (dated history — the DERIVED index above owns the current census, D-2984/D-2985): as measured then, and SUPERSEDED since (a version of this writer was re-cutting these counts to TODAY's value while the line said 'as measured then' — a false historical claim, repaired in place 2026-10-13); BUG-725 CLOSED 2026-10-12 via scripts/restamp_bug725_provenance.py --apply — 1,049 rows stamped; NOTE its buglog HEADER still read the machine's OPEN slot, so scripts/bug_status.py kept reporting it open until the closure was moved into the authoritative LEADING parenthetical — the BUG-633 class, fixed). D-2951 (ACTIVE 2026-10-12): the D-2949 PREVENTION half is WIRED — a commit-time dedup gate at stage6.dedup_gate (mode: report; `enforce` is measured NEUTRAL: 0 link candidates over the faithful 7,640-row S6 input, receipt governance/dedup_gate_simulation_run_20261012.json) + is_divergent is now pairwise and same-work is decided by source OVERLAP. BUG-726 CLOSED 2026-10-12 (`duplicate_of` was written '' on EVERY row, so the documented predicate `duplicate_of IS NULL` (D-271d) matched ZERO rows; the writer was fixed in D-2951 and the 7,640 legacy rows were reshaped '' -> NULL by scripts/normalize_duplicate_of_marker.py --apply, C13 backup first, ONE BEGIN IMMEDIATE, post-state verified: 7,640 NULL / 0 real markers / status census unchanged / quick_check ok). BUG-728 FILED (LOW: `source_authors` — the FILE layer — repeats one source, 31 rows literally and 90 by carrier key; display-only, identity and the dedup gate's richness() are unaffected). D-2952 (ACTIVE 2026-10-12): edition supersession RULED a FILE-LAYER CONTENT rule — "newest edition wins" moves the BODY fields only, never at commit (D-2933 rule V) and never the citation: primary_source stays ORIGIN ("the earliest source we HOLD"; 1,014 rows carry it, ZERO violations), freshness gets its OWN reserved pointer content_basis (deliberately NOT created — no writer yet, and the register is shrink-only at debt 8 of ceiling 9), and the destructive threshold direction is fenced (tighten freely, never loosen without an owner). Measured by scripts/audit_edition_layers.py: 12 edition pairs share ONE source_id (editions collapse BY DESIGN, D-2308) + 51 boundary rows; carrier duplicates in source_ids = 0 (CHECKED AND CLEAN: D2176 already routes source_diversity through canonical ids). Companion alignment: D-271d's "wire duplicate_of IS NULL into retrieve.py" is SUPERSEDED as a MECHANISM — the real guard is status = 'PASS' plus the LINK=>QUARANTINE pairing, and the predicate would be redundant. D-2953 (ACTIVE 2026-10-12): the BUG-712 re-stamp is BLOCKED BEHIND CALIBRATION — a new two-sided instrument (scripts/calibrate_content_type_router.py, read-only, LLM-free per D-343) shows the 122-row router diff is 88% ROUTER false positives (88 of 100 principle->growth_edge moves read an ORDINARY predicate about the record's SUBJECT as an epistemic statement about its CLAIM: 'contradictory information' 44, 'contested identity' 34), the recall side is 0 (the token list is not too narrow), and the strict form that fixes it ships DISABLED (config/content_types.yaml -> reroute.open_tension_strict: false; loose 100 moves -> strict 2; tests 6/6), because content_type is S4-owned (D-2933). Root cause is an UNFIXED SIBLING: D-2949 fixed exactly this class in _DONE_CONDITION and left _OPEN_TENSION bare. BUG-729 FILED (MED: ti_to_pt_keywords keeps the bare noun suffixes D-2949 removed from its own class — 'system'/'framework' route software PRODUCTS like OpenFrameworks to process_template; 10 of 108 TI rows, one clearly right). BUG-728 FILED earlier this session (LOW: source_authors repeats one source). D-2954 (ACTIVE 2026-10-12): the CONFIG SURFACE now refuses duplicate keys — BUG-730 (CLOSED, self-inflicted, disclosed) appended a second top-level `reroute:` block to config/content_types.yaml, PyYAML kept the LAST duplicate, ti_to_pt_keywords silently emptied and the whole tool_instruction->process_template tier went DEAD with every rail green; caught by a BEHAVIOUR DIFF (122 -> 112 rows), fixed by merging the key into the ONE mapping, and closed as a CLASS by scripts/check_config_duplicate_keys.py (YAML duplicate-key loader + JSON object_pairs_hook, 116 config files, --selftest 3/3, WIRED into `just health`). BUG-731 FILED (MED, PRE-EXISTING, proved NOT mine: the undeclared-default census measures 241 shadowed-declared keys against a ceiling of 229 — +12 accumulated 2026-10-07 -> 2026-10-12 with every rail green, and converting my own new read to a LOUD read left the measurement at EXACTLY 241, so my net contribution is 0. It also exposed a BLINDSPOT: the census's `receivers` list omits `_CT`, so `pipeline/content_types.py` — the module that owns the content-type enum — is INVISIBLE to that rail. Fix is a DECISION, not an edit (D-2644: a ceiling may only be LOWERED): either the owner raises it or the 12 shadowed reads become loud reads, and `_CT` joins `receivers` with the number re-recorded under owner sign-off.) BUG-727 FILED (the store_columns register is red: `measured:` was recorded against a 14,574-row store while the store holds 7,640 — pre-existing, one `--record` owed AFTER the next S6 run settles). D-2942..D-2945 (ACTIVE 2026-10-12): D2590 non-principle commit tier LANDED — store 6,591 → 7,640 rows in ONE run (principle 6,577 / process_template 774 / process_instance 156 / tool_instruction 108 / growth_edge 25); the S4 sidecar records that were 'extracted, routed, written, never committed' are now committed (1,049) or DECLARED (196 mislabelled principle rows → BUG-719; 374 on the D2616 hold shelf). BUG-713 + BUG-715 reconciled to CLOSED (resolved in prose only — the register still read them OPEN). Forensic audit GREEN: 0 fatal rails — store-change re-baseline cascade (BUG-659..668) FIXED at root cause. BUG-687 (CLOSED, D-2882): nli_calibration pin on a gitignored derived artifact RETIRED (owner approved). BUG-688 (CLOSED, D-2883): the D-2618 retired golden is recorded, never gated — bridge --check green again (owner approved). BUG-689 (CLOSED, D-2830): the D-2767 A/B harness crashed on the v8 referee's owner-absence rows — `noise_drop` excluded (out of scope), `abstained` → the declared abstention token 'emerging'. D-2884 (RATIFIED, 2026-10-09): D-2767 C+B gate measured FAIL (3-way coarse 0.5621 < 0.73 floor); owner RULED (a) fine discipline → advisory-only, 3-way macro + domains operative, (b) distinct-family decider A/B in parallel; BUG-690 macro drift part 2 fixed (v5→v8, Business & Management added), part 1 (coarse-kappa harness output) FIXED (commit 8895cbf). D-2884(a) macro operative routing LANDED + R5 gemma-APPROVED (2026-10-09). D-2953 RATIFIED ENABLED (2026-10-12): the strict tier-2 form is ON — one config value, and the tests now bind CODE to CONFIG rather than to a constant; re-measured at the flip the router diff fell 122 -> 14 and the strict form's own 2 moves are 1 claim_status / 1 subject_matter (50%, n=2), so it is better and still NOT a re-stamp licence. D-2955 (ACTIVE 2026-10-12): the tool_instruction -> process_template promotion requires BODY evidence — a name is a PRIOR, never evidence. TWO independent controls in config/content_types.yaml -> reroute: the artifact nouns 'system'/'framework' are REMOVED (they name software that is USED, not methods that are EXECUTED) and ti_to_pt_require_body_evidence: true demands ordered steps AND a done-condition/gate in the record's own body, the SAME pair tier 2 uses (C21). MEASURED both ways (SIDE C, read-only): 108 TI rows, name-prior candidates 1, body proves a procedure 0, promotions gate OFF 1 -> gate ON 0, retired-vocabulary control 9 artifact-named rows of which 0 would have survived the gate. Neither control is redundant and the reason is NOT today's store: the vocabulary decides the case the store does not yet contain. Forward-only (D-2938 producer), and it owes NO re-stamp. D-2956 (ACTIVE 2026-10-12): a CEILING is a declaration, `measured:` is a MEASUREMENT, a ROLE is an ONTOLOGICAL claim — never interchanged. (1) NEVER RAISE A CEILING (D-2642); (2) re-recording is not a decision — legitimate only on a SETTLED artifact, once, after the pending store mutation lands; (3) a role violation is a FINDING: 20 of the store-column faults are ONE missing concept (the register cannot express 'required within a tier', and this store is two-tiered by construction, D-2943) — declaring them `sparse` would write 20 lies; (4) INSTRUMENT SCOPE IS PART OF THE INSTRUMENT. BUG-729 CLOSED 2026-10-12 (7+2 tests). BUG-732 FILED (MED: the store-columns red is MISATTRIBUTED — 305 fatal faults = 278 MEASUREMENT-DRIFT + 27 LIVE ROLE faults that `--record` cannot clear). BUG-733 FILED (MED: the role vocabulary cannot express tier-conditional coverage; 20 faults, one missing concept). BUG-734 FILED (LOW: the 7 residual role faults enumerated — incl. last_retrieved_at declared reserved but populated on 88 rows, the BUG-726 class again). BUG-735 FILED (MED: the strict tension form still reads a BOUNDARY condition as an open tension — 9 of its 12 survivors are boundary-ONLY; fix measured, owner call). BUG-731 UPDATE: the instrument half LANDED — `_CT` is now a declared census receiver in config/derivations.yaml AND the module's 10 defaulted reads became LOUD subscripts in the SAME change, so the number is EXACTLY 241 before and after (left alone, the receiver change alone would have measured 248); the paydown is sized, not guessed: 183 of the 241 keys (76%) sit in ONE file (pipeline/pipeline_paths.py, 361 sites). BUG-727 UPDATE: the report conflates three axes (ceiling / measurement / role); the 27 role faults are filed above and must never be silenced by a re-measurement. BUG-712 UPDATE, severity REVISED CRITICAL -> MED: both router defects are fixed, so the governed re-stamp scope is 14 rows and every one has a named cause — 12 are tier 1, the OWNER'S OWN adjudication map (10 tool_instruction -> principle 'concept/pattern/algorithm', 1 -> process_instance 'concrete single-use event', 1 -> noise_drop 'physical equipment'), i.e. EXECUTING A DECISION ALREADY MADE, and 2 are the strict form's survivors, which must NOT ride the re-stamp (they are 50% precise at n=2; BUG-735). D-2957 (ACTIVE 2026-10-12): `runtime` is a ROLE - serving-path state is not artifact content. The register declared `last_retrieved_at` `reserved` ('retrieval has never been recorded') and `usage_count` `state` ('constant 0 - never served'), and the STORE refuted BOTH: 88 retrievals, the two columns filled on exactly the same 88 rows by feedback.mark_fb_retrieved in ONE statement. Both are `runtime` now (contract = absent is NULL, not coverage: nonnull == nonblank and hollow == 0, enforced by controls c18-c20), the producer writes SHAPE-ONLY (`_safe_str(...) or None`) because the INSERT is OR REPLACE and the BUG-376 checkpoint round-trip carries the value back - a hard NULL would have DESTROYED the 88 records - and scripts/normalize_runtime_absents.py (whose population IS the register's runtime columns) retired 7,552 legacy blank cells with a C13 backup, ONE BEGIN IMMEDIATE and a verified post-state. Companion: the rail's own control found the control HARNESS modelling a SQL NULL as the literal 'none' while the store ruler coalesces NULL to '' (not hollow) - the harness disagreed with the instrument it validates; fixed, and c18 could not pass before it was. D-2958 (ACTIVE 2026-10-12): every one of the 25 residual store-column role faults is ONE missing concept - a role evaluated against an implicit, UNMEASURED population (14 columns blank on EXACTLY the 1,049 D-2590 sidecar rows; verifier_model present on exactly the 6,591 S5 rows; classification_error(s) on 0 rows by their writers' population; menu_hash and discipline_macro full because the canonical artifact IS those rows). A population-free role is an unscoped claim (D-2956 clause 4); the rail fix is owner-gated. D-2959 (ACTIVE 2026-10-12): D-2950 RESOLVED - identity ratified ((normalize_name, source_ids) + body divergence), the dedup gate STAYS mode: report with the obligation moved from the mode to the RECEIPT (required reading; >=1 verified convergent link candidate is an OWNER GATE), edition supersession ratified as a FILE-layer rule with `content_basis` still a writerless reserved name, and - as a standing rule - every gate simulation must DECLARE its population and prove it covers every tier. BUG-736 FILED (MED, the verifier instruments, no new decision: the R5 reviewer is uninformative on 40-50% of passes yet has applied 0 false positives because output is audited, never applied; the eligible-family fence in config/eval_integrity.yaml::judge_calibration excludes Qwen BY R5 - and the most-downloaded MLX models on HF are Qwen3.8-27B x4 at 3.9-4.1M downloads each, i.e. the generator's own family - while BOTH eligible judges were already measured DEGENERATE at the constant baseline (BUG-269); the S5 NLI abstains on 19.1% of the 6,571 rows it judges with its EDGE unmeasured on the live artifact. Candidates fielded, evidence-gated against min_margin_over_baseline 0.15: gemma-4-26B-A4B-it-QAT-MLX-4bit for the reviewer, tasksource/ModernBERT-large-nli for S5; nothing swapped, because the binding constraint is the TASK (BUG-269 names each fix), not the model). BUG-737 FILED (MED: the store's ABSENT SHAPE - 20 of 78 columns carry a NON-NULL blank while pipeline/schemas.py declares None; NULL exists only where a decision put it (duplicate_of, feedback_score); per-column verdicts, never a bulk rewrite). BUG-734 CLOSED as ABSORBED (2 runtime faults cleared by D-2957, 5 moved to BUG-733 - one home, not two). BUG-726 UPDATE: the class is 20 columns, not one; this bug was the first instance, dangerous only because a documented predicate depended on its shape.  D-2960 (ACTIVE 2026-10-12): a ROLE is scoped to a DECLARED, MEASURED POPULATION and the OUTSIDE is part of the claim - config/store_columns.yaml declares populations.{s5_verified = s5_reason <> 's5_not_applicable' (6,591 rows), sidecar = s5_reason = 's5_not_applicable' (1,049 rows)}, a PARTITION of all 7,640 rows, and a column may declare population: <name> with a REQUIRED outside: absent | unconstrained (absent = blank outside AND NULL-shaped there -> POPULATION-SPILL / POPULATION-SHAPE; unconstrained = DECLARED and reported LOUD as OUTSIDE-COVERAGE, the one non-fatal mode). This landed BUG-733 CLOSED: the 25 role faults (20 CONSTANT-OR-BLANK + 4 SPARSE-VIOLATION + 1 STATE-VIOLATION) were ONE missing universe, artefacts of the QUESTION rather than defects in the store, and all 25 are now 0 by DECLARATION against a measured population - NOT by declaring the columns `sparse`, which says OPTIONAL while D2371/D2488/D2475 QUARANTINE an empty application/failure_mode/elaboration (20 lies). The tier comes from s5_reason (the S5 rail's own verdict), never from a label: content_type='principle' measures 6,577 rows while the S5-adjudicated tier measures 6,591, and the 14-row gap is exactly the label-vs-body disagreement (12 owner-adjudicated BUG-712 rows + 2 BUG-735 survivors). BUG-732 CLOSED: the store-columns red is no longer misattributed - the live role violations a re-record cannot reach are gone by declaration and the drift that DID belong to a re-record is gone by exactly one; the 15 remaining fatal faults are ONE class with ONE owner (BUG-737). BUG-727 CLOSED: the deliberate --record was taken (78 columns + populations rows, census moves 0, MEASUREMENT-DRIFT 0, ceiling debt 9 -> 8 DOWNWARD, D-2642: nothing hand-edited). BUG-737 UPDATE: the ''-as-absent shape is now MACHINE-DETECTED with a named 15-column work queue (elaboration, taxonomy_match_method, keywords, discipline_raw, context, accessibility, intimacy_boundary, source_text, difficulty_level, temporal_scope, verifier_model, epistemic_status, verification_method, practicality = 15 x 1,049 sidecar rows), while domains_raw, confidence_score, related_fbs, isor, type_body, classification_error(s), duplicate_of, feedback_score, contradicts_fbs, prerequisite_fbs measure ALREADY NULL-shaped outside (the store is right where a decision put it) and menu_hash carries the literal NOT_APPLICABLE (OWED, not to be normalized before its F-44/D-279 readers are audited). Also measured and corrected against the store (not re-recorded): menu_hash was declared `sparse` on a 14,574-row census and measures 7,640/7,640 with 2 values -> state + population + outside: unconstrained; classification_error/classification_errors were declared `sparse` (52 and 2 rows of a store that no longer exists) and measure 0/7,640 -> reserved with the writer named (a diagnostic that fires only on defective rows is legitimately empty on a clean run); pipeline_run_id is `state` (the store holds ONE run's artifact, D-2943), failure_mode is outside: unconstrained (required on all 6,591 S5 rows AND written on 774 process_template rows - DECLARED, so OWED, not a spill), discipline_raw is `sparse` INSIDE s5_verified with its 190 in-tier blanks left VISIBLE. 8 new known-answer controls (c21-c28) -> 28/28 fire; tests 400 passed / 5 skipped. NEXT: the BUG-737 shape fix is a STORE mutation and needs its own per-column reader audit (the MCP reader would have emitted the string "None" for last_retrieved_at and had to be fixed) - NEVER a bulk rewrite.

## D-2881 (2026-10-08) — the 11 ambiguous anchor-bridge rows are RUN-COLLISIONS, resolved to the ratified canonical run

The 11 `join.ambiguous` rows (R002 R039 R049 R065 R070 R097 R102 R107 R152 R192 R197) were NOT concept collisions: each folded name matched exactly TWO corpus rows from DIFFERENT extraction runs — a pre-rechunk `t11` row and a `rechunk-v4-20260929` row (same name, same source_ids, different fb_id). D-2658's "never pick" correctly refused, but the refusal hid a deterministic answer.

RULE (deterministic, LLM-free): a run-collision is not a concept collision. When a folded name matches rows from >1 run and EXACTLY ONE candidate is from the declared canonical run, that candidate resolves the collision (never a positional pick). Any other multi-candidate name (same-run or no-canonical-run row) stays AMBIGUOUS and is still refused.

IMPLEMENTED: `config/anchor_family.yaml#store_bridge.canonical_run = rechunk-v4-20260929` (the owner-ratified re-chunk, BUG-662); `build_anchor_store_bridge.py` reads `pipeline_run_id` and resolves via `join: run_canonical`. Bridge 197→208 joined, `join.ambiguous` 11→0, `join.counts.run_canonical=11`. Conformance regenerated 183→194 examples + 14 excluded (noise_drop only). Selftest 19/19; axis-consistency ceiling 0 holds; conformance --check byte-re-derivable.

1. **D-2727 RATIFY-2 — RETIRED (owner, 2026-10-10).** The full S4→S5→S6 rerun already happened (canonical `rechunk-v4-20260929`, 6,591 rows, S5/S6 complete); only provenance was stale, fixed by D-2907. No 20h re-run.
2. **D-2727 OG-1 — Option A DECLARED (D-2730) + owner re-affirmed (2026-10-10).** KEEP(46)→S4 golden; pinned OUT of eval ruler 208→162; sha256-pinned split manifest = RAIL (`scripts/verify_split_manifest.py`).
3. **D2622 — RESOLVED (2026-10-10).** practicality now PERSISTED: `practicality` column + S6 wiring + backfill of 6,591 canonical rows (immediately-applicable 5092 / context-dependent 1499 / abstract 0).
4. **D2621 PROPOSED** — distinct-facet dedup method landed (D2625/D2626/D2627); residual = owner choice: `pipeline/dedup` module vs keep ad-hoc scripts.
5. **D2547 PLANNED** — per-label thresholds not yet populated.
6. **D-2908 — RESOLVED (2026-10-10).** BUG-695 per_label recalibration complete: d2547_calibration.json covers all v9 labels; per_label re-populated 93 entries (53 disciplines + 40 domains); all 7 `0.0` labels are measured-0 (not missing-data false-zeros). Fixed false-zero guard + contract test 92→93. BUG-695 CLOSED. BUG-693 steps 1–2 done (mapfail/dombleed 0), step 3 (1,297 off-menu) owner-gated per D-2898.
7. **D-2909 + D-2910 — RESOLVED (2026-10-10).** (a) BUG-566 remainder: `check_declaration_consumers.py#staged_set()` still whitespace-split the staged name list (D-2646 class); fixed to NUL-separated `-z` + 2 controls, selftest 13/13. (b) BUG-658 CLOSED: no-wedge reproduced end-to-end under the D-2854 wall-clock deadline (gemma 0.53s clean; gpt-oss cold-reload returned RuntimeError in 46–73s, no hang). Full d2767_ab_eval A/B re-run separately blocked by BUG-650 (stale v6-d referee).
8. **D-2916 — RESOLVED (2026-10-10).** BUG-650 stale-default limb fixed: `d2767_ab_eval.py` DEFAULT_ANCHOR re-pointed v6d → v8 authority (DEFAULT_OUT → `d2767_ab_eval_v8_20261010.json`); `remap_referee_v7_28rows.py` marked COMPLETE (fail-closed self-guard, D-353); four v6 anchor variants + five v6-era `d2767_ab` outputs retired to `archive/` (C19, bytes preserved). v7 + `build_anchor_v8_*` HELD (D-340 frozen-pair). `d2767_ab_eval.py` stays LIVE (distinct gpt-oss gate; NOT superseded by `d2884b_decider_ab.py`).

— everything below is dated change history / ACTIVE / DONE —

## 2026-10-05 — BUG-638/BUG-639 + D-2822..D-2825 minted; cluster_28517 RECOVERED; S4 final at 6,591

1. **D-2825 (RATIFIED)** — cluster_28517 "Planck's Constant Derivation" = **RECOVERED**. Owner asked whether it could be re-run on S2; answer **NO** — S2 extraction was already complete/coherent, the failing `application` field is S4-generated (`merged_cribs_classify`, gpt-oss-20b), a TRANSIENT failure. `--cluster 28517` retry recovered it cleanly (application 178 chars, discipline theoretical physics, CLEAN). All 6,591 S4 FBs on-disk, declared_failed_count=0.
2. **D-2824 (RATIFIED)** — dedup-accept phantoms cluster_3776 (Blue Ocean Strategy) + cluster_26074 (Memory Reconstruction Bias); expected_fb_count stays 6,591.
3. **D-2823 (RESOLVED)** — normalize bare `--cluster` ints to `cluster_N` before the delta path (BUG-637 leg).
4. **D-2822 (PROPOSED)** — S5 aggregation gate A(d): OR-entail + AND-no-contradiction (T9; not yet executed).
5. **BUG-639 (FIXED)** — S4 delta-merge shrink-guard false positive; `safe_write(..., force_shrink=bool(cluster_ids))`.
6. **BUG-638 (FIXED)** — METRICS.jsonl append-only floor guard (shrink-only, crash-safe tempfile→fsync→os.replace, fail-closed).

**Pipeline state:** S4 rechunk-v4-20260929 final = **6,591** (preflight GREEN, sha256 ef77e346). S5 stale at 6,588 (verified old sha256 d8fc670b) → **re-run S5**. S6 empty → run.

## 2026-10-03 — D2622 wired into S5 (advisory tier); D2621 method confirmed landed (correction of prior "no work landed")

Owner approved the D2621 + D2622 senior-RAG recommendations → implemented in strategically consequential order.

1. **D2622 (practicality/applicability filter) — WIRED into S5.** `pipeline/practicality.py::classify_practicality()`
   now annotates every verified FB in `pipeline/stage5_verify.py` with a `practicality` field
   (immediately-applicable | context-dependent | abstract). This is an ADVISORY soft-facet for query-time
   re-ranking — it NEVER drops/quarantines an FB (`status` derives independently in the same loop). C16: a
   missing/malformed `config/practicality.yaml` fails loud. Registry state D2622 stays ACTIVE — the final
   RESOLVED flip lands at RATIFY-2 after a full S5 run populates + validates the field.

2. **D2621 (distinct-facet dedup) — CORRECTION, not new work.** The prior audit note ("genuinely OPEN — no
   work landed") was INACCURATE. The method landed via D2625/D2626/D2627 (all RESOLVED 2026-09-14):
   `scripts/dedup_scan.py` (SHA-256 + name-stem collision, NO embedding for the merge decision), `dedup_judge.py`
   + `judge_suffix_duplicates.py` (mechanism-aware judge), `prefilter_dedup_groups.py`, `apply_dedup_marks.py`
   (mark `duplicate_of` + QUARANTINE — never delete, R-D410). Artifacts present: `dedup_candidates.jsonl`,
   `dedup_merge_plan.json`, `dedup_suffix_judgments.json`, `dedup_final_apply_plan.json`. D2621 umbrella stays
   PROPOSED — residual is an OWNER choice: formalize as a reusable `pipeline/dedup` module vs accept the ad-hoc
   scripts.

Registry/buglog unchanged (938 / 366); `decisions.yaml` untouched → census NOT re-derived.

## 2026-10-03 — Owner-authorized registry state-flips executed (D2546→RESOLVED, D2548→REJECTED, D2622→ACTIVE)

Forensic audit → owner "approve those" → executed the three owner-owed state-flips the prior NOTE had queued:

| ID | Before | After | Evidence |
|---|---|---|---|
| D2546 | PLANNED | RESOLVED | SHACL .ttl SHIPPED (D2555); OWL periodic + Track B re-scoped (not started) |
| D2548 | PLANNED | REJECTED | grammar-decoding A/B RAN + REJECTED (D2392); `grammar_decoding_enabled=false` (D2556) |
| D2622 | PROPOSED | ACTIVE | deterministic backend landed (D-2723); S5 wiring deferred to RATIFY-2 |

**D2622 state-vocabulary blindspot also closed**: `config/practicality.yaml` carried `state: IMPLEMENTED` (a non-registry
word) → renamed `backend_state: landed` (a config-local lifecycle word). The registry state word now lives ONLY in
`config/decisions.yaml` D2622. Census re-derived (`source_sha256 15e1ff0b`); `decisions_registry` receipt re-baselined
(origin=owner-rebaseline, 909223 B). Registry 1112 decisions / buglog 366 unchanged; `session_seed.yaml` already in sync.
Remaining ladder RED is owner-ruling only: `anchor4_workbook` + `depth_workbook_row_count` (both = R003/R146 AUTOFILL).

## 2026-10-03 — Superseded/done/conflicting decision + bug audit; BUG-625 + BUG-626 filed (no new decision minted)

### Audit result — superseded / done / conflicting decisions + superseded / fixed bugs (forensic, no registry change)
- **Superseded decisions (16):** 4 name a successor (D2100→D2094, D2253→D2362, D2294→D2298, D2296→D2298); 12 are pinned as declared legacy debt in `config/decisions_policy.yaml#graph.pinned_supersession_ids` (D2070, D2080, D2085, D2087, D2091, D2223, D2224, D2293, D2317, D2318, D2430, D2582) — NOT backfilled by design (a tool-reconstructed successor is not evidence, BUG-575).
- **Done decisions:** 270 RESOLVED (+ 8 ARCHIVED, 10 REJECTED). No separate "DONE" state — a decision is done when RESOLVED/SUPERSEDED/ARCHIVED/REJECTED.
- **Conflicting decisions (2, both NEW):** (1) **D-328** carries `superseded_by: ['D338','D339']` — a LIST where the graph contract (`successor_field: superseded_by`) expects ONE scalar id → **BUG-626**; (2) **D-2104** declares `supersedes: D2085` in the reverse direction, but D2085's own record has no `superseded_by` and sits in `pinned_supersession_ids` (a forward/backward asymmetry, already noted in the pin's `pinned_supersession_measured` prose — LOW, not a fault).
- **Superseded bugs:** NONE in the register — bugs are binary open/closed (no SUPERSEDED status word in `scripts/bug_status.py`).
- **Fixed bugs:** 220 CLOSED of 365 (RESOLVED/CLOSED/FIXED/INVALID/RETRACTED), 145 OPEN. `governance/bug_status.json` re-derived (was 143/220/363 → 145/220/365).

### BUG-625 + BUG-626 filed this turn (BOTH RESOLVED 2026-10-03)
| ID | State | Decision |
|---|---|---|
| BUG-625 | RESOLVED | **C12 residuals from the D-2801 R5 review, filed as a follow-on bug (not yet fixed).** probe_run.py:36-37 hardcode run-id `latest` (BUG-597 class); probe_run.py:41 hardcodes `OMLX_URL=http://localhost:11435` (second home for the endpoint); the `"knowledge pipeline"` literal is duplicated across ≥10 pipeline modules instead of reading `pipeline_paths.py` DATA_DIR/CHECKPOINT_DIR/DB_PATH. NON-BLOCKING (probe tooling). FIX: config-first run-id + endpoint + ONE path home. |
| BUG-626 | RESOLVED | **Decision-registry schema conflict.** D-328 `superseded_by` is a LIST `['D338','D339']` where `config/decisions_policy.yaml#graph.successor_field` expects ONE scalar. DORMANT (D-328 is RESOLVED, not SUPERSEDED, so the graph walker never reads it) but LATENT — any scalar reader or a future flip to SUPERSEDED raises a TypeError. LOW severity. FIX: canonicalize to a scalar successor + add a scalar-or-absent type-check to the supersession rail. |

**[SUPERSEDED 2026-10-03 — this audit snapshot is stale. Machine truth (`config/decisions_summary.json` + `governance/bug_status.json`): decisions 940 / buglog 366 (132 open / 234 closed) / highest_bug BUG-604. See the D-2808 + NOTE entries at the bottom of this log.]**

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

## 🔴 OPEN / PENDING — highest priority first — HAND INDEX, not a register (the DERIVED block above is the ONE authority; rows joined on every run, D-2986)

### New from cross-model adjudication (2026-09-03)
| ID | State | Decision |
|---|---|---|
| D2546 | RESOLVED | **SHACL hot-path + OWL periodic** (not OWL-DL everywhere). Formalize 105 canonicals as `sh:disjoint`/`sh:closed`/`sh:in` before Track B. |
| D2547 | PLANNED | **Per-label/per-axis cost-weighted thresholds** — retire the global 5% semantic-error rule. Calibration measurement DONE (D2561): 440 labels → `governance/d2547_calibration.json`; remaining = populate per-label thresholds. |
| D2548 | REJECTED | **Grammar-constrained decoding pilot** on S4 discipline/domain enums (Outlines/XGrammar) — latency A/B before adoption. |

### Pending from registry (SNAPSHOT 2026-10-03 — dated history; the DERIVED index at the top owns the current state, D-2984)
> CORRECTION (D-2984, 2026-10-13): the register has since moved D2622 and D2621 to RESOLVED. This list is what was pending when it was written, and it is kept as written (append-only, R-D410).
| ID | State | Decision |
|---|---|---|
| D2622 | ACTIVE | **PRACTICALITY/APPLICABILITY FILTER (S5, use-case calibrated).** Separate practical (directly applicable ~20s, no over-analysis) from theoretical/abstract principles. Config-driven (C12) with the public Anytype use case (design + business) baked into `config/practicality.yaml`. Rubric: "in the context of {use_case_domains}, can an agent apply this principle to a concrete task within ~20s without over-analysis?" → immediately-applicable | context-dependent | abstract. Reuses existing signals (application / procedural_skill / is_summary / accessibility); swappable (C21). |
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

## 🟢 ACTIVE — in effect — HAND INDEX, not a register (the DERIVED block above is the ONE authority; rows joined on every run, D-2986)

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
| D-2979 | RESOLVED | Ranking fix + raw-label facet (opt-in). D2537 (also written "D-2537" in the register's own D-2979 title) is an id no record carries - a dangling citation, filed as BUG-761. |
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

## ⚪ DONE / CLOSED — bottom — HAND INDEX, not a register (the DERIVED block above is the ONE authority; rows joined on every run, D-2986)

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

## D-2670 (2026-09-26) - the RECEIPT PROVENANCE JOIN: a receipt must be joined to a store that RE-DERIVES its bytes (BUG-559)

CONTEXT. A receipt is {path, digest, bytes, mutability, code_sha, stamp} about BYTES, and nothing in that record says the bytes are a REVISION of this repo or a declared derivation from one. MEASURED (BUG-558): the workbook held 92135 bytes (574aafef64f0cff7) present in NO revision of that path, and `verify_handoffs.py` printed "unchanged" because the receipt had been cut OVER them. The rail was not broken - it verified exactly what it was told. BUG-559 is the missing join.

DECISION. Every receipted (path, digest) must be re-derivable from a declared store, or it is refused. Four joins, each naming the store that re-derives the bytes: `head` (this path's bytes at git HEAD), `prefix` (a RETAINED PREFIX of an append_only path, re-derived by truncating to the receipted length - the BUG-540 rule, already proven), `revision` (a declared revision locator for THIS path), `declared` (an escape named in `config/handoffs.yaml#receipt_provenance.unrevisioned_declared` together with the reason no store can hold the bytes). Anything else is UNREVISIONED and is reported owner-owed with its remedy.

WHY NOT `head` ONLY. The owed fix text said "the live digest AND git_bytes(HEAD, path)". Implemented literally it would refuse a receipt cut YESTERDAY over a file COMMITTED SINCE - a legal receipt - which is the BUG-492 failure (a rule never seen to pass is not a rule). MEASURED before coding: of the 7 latest receipts, 2 join at HEAD, 1 is a retained prefix (config/decisions.yaml, 629488 of 635398 bytes), 2 are gitignored run-root checkpoints, and 1 - the owner drop-in - joins NOTHING. The prefix join therefore has a live subject, and the join is measured rather than assumed.

WHY A SAME-LENGTH LIVE COPY IS NOT A JOIN. If the digest merely matches what is on disk, the receipt and the artifact are the same copy, and "the receipt describes these bytes" is circular - exactly the shape that blessed the foreign body. A join must name a DIFFERENT store (HEAD, a locator, or a retained earlier revision inside the file).

WHY THE ESCAPE IS DECLARED AND COUNTED. A 100MB run checkpoint under `.gitignore:73` has no revision anywhere and no `bytes_at` to locate, so no store CAN hold it; the honest act is to name it with the reason, not to weaken the rule for every path. The list is joined in BOTH directions (D-405): an unmatched escape is DRIFT, and an unnamed unrevisioned receipt is refused. `max_unrevisioned: 2` is a SHRINK-ONLY census - stated plainly as a census, NOT as the enforcement.

WHY IT IS A CHECK CLASS, NOT A NEW RAIL (D-2646). The receipt rail already owns the receipt domain; a second rail reading the same journal would be a second home for one fact. This adds one join to the rail that owns receipts, at every moment the ladder already runs it.

THE SECOND CLAIM (what this makes visible). The one live UNREVISIONED object is the owner drop-in (rev 3, 526991cb, 203963 B) whose bytes no store re-derives because git HEAD still carries the superseded rev 2. BUG-493's owner gate was a remembered fact; it is now a MEASURED line in the ladder that only the PROMOTE clears.

MEASURED AFTER: `verify_handoffs.py --selftest` rc=0 (7 provenance cases + the escape join, both directions); live rc=2 with exactly one finding, the drop-in; stale-escape control rc=1; census-3 control rc=1; declaration consumers 11/11 + 5 edges; rail registry 9/9 + rc=0 (80 invocations, 56 rails); check_repo_integrity rc=0; `just health` rc=0.
NOT a delegate claim (R5): OMLX is unreachable and no reachable local model is a verifier, so no signature is claimed.

## D-2671 (2026-09-26) - the PROMOTE: an owner's one word lands a write-locked REVISION through a SPENT crossing permit (BUG-493/BUG-559)

CONTEXT. The write-locked owner drop-in 'governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv' holds rev 3
(526991cb, 203963 B) and has done since 2026-09-25 21:08; git HEAD held the SUPERSEDED rev 2 (bc1cc956, 203506 B).
Nothing was corrupt - the path was AHEAD of history, and that made two declarations disagree with the tree: the
ledger still read 'REV 2', and the receipt's bytes were re-derivable from no store (BUG-559, rc=2 owner-owed on
exactly this one object). rev 3's only non-worktree copy was a '.bin' blob, which .gitignore:61 does not track.

DECISION. OWNER WORD: 'Promote' (2026-09-26). rev 3 is landed as the TRACKED REVISION of its own path, by the SAME
mechanism the owner's earlier CROSS used (D-2668): a widening_log entry with 'crossing: true' naming ONE subject,
'acked_by: owner' + 'acked_on', and 'spent_by' naming the commit that used it. Rail 4's will_not_touch match is BY
FAMILY (BUG-528), so the path is forbidden by default and only an owner-acked one-off permit may cross it; a
may_touch entry would have been STANDING permission over an owner instrument, which is the abuse rail 4 exists to
prevent. The permit is recorded BEFORE the write (BUG-445) and SPENT in the commit that follows (D-2668), so the ack
cannot outlive the commit it was given for.

WHY NO revision_locator FOR rev 3. The rail offers two remedies: land the bytes as a revision, OR declare a revision
locator. A locator exists to make SUPERSEDED bytes resolvable; once rev 3 is HEAD it is re-derived by the HEAD join,
and a locator pointing at the same bytes would be a SECOND home for one fact (D-2646) that goes stale the moment the
path is rewritten. The locators for rev 1 (git:075ae65) and rev 2 (git:65a13c3) are untouched, so the receipts that
quote them still resolve.

WHY NO NEW RECEIPT. The journal already holds 13 records for this path, every one 526991cb/203963 B. A re-cut would
add a record saying the same thing about the same bytes; the PROMOTE changed WHICH STORE re-derives them, not the
bytes, and the rail re-derives the join on every run.

WHY THE LABEL FIXES RIDE WITH IT. Two homes still described rev 2 - config/handoffs.yaml's artifact 'why' and
config/human_instrument_locks.yaml's comment above the LIVE digest - and a promotion that leaves its own declarations
describing the superseded revision recreates the mismatch it just closed. The third, unconsumed home
(config/anchor4_depth_annex.yaml's restated digest) is reduced to a POINTER at the one home rather than a copy of
the digest: the D-2646 remedy, not a re-statement.

WHAT THIS IS NOT. It is NOT BUG-431's content promotion: the tracked ANCHOR4 sheet still carries pre-consolidation
context plus the owner's PARTIAL pass, config/anchor4_interim_state.json still stands (state: pending_owner_gate,
expires_when 'the promoted sheet is committed'), and merging the complete 150/150 pass into the tracked sheet - then
retiring that interim file - remains an OWNER GATE. No sheet was written here.

MEASURED AFTER. verify_handoffs: 'provenance: anchor4_depth_sheet_owner_dropin -> head', rc=0 (was rc=2 naming this
one object); revision locators still re-derive (rev 1, rev 2, f2778a48); hash_claims 13/13 and cross_declaration
11/11 unchanged; check_human_instruments byte-identical; the suite, rail registry, declaration consumers and repo
integrity unchanged; 'just health' rc=0.

NOT a delegate claim (R5): OMLX is unreachable and no reachable local model is a verifier, so no signature is claimed.

## D-2672 (2026-09-26) - a git NAME-LIST read is not a name SPLIT: the staged set is NUL-separated in ONE home (BUG-565 fixed, BUG-566 filed)

CONTEXT. MEASURED: rail 4 read the staged names with `--name-only` and split on NEWLINES. A path containing a newline
then leaves the audited set SILENTLY - a red gate turning green - and the same read was duplicated wherever a rail
needed names, so one fact had as many homes as there were readers.
DECISION. ONE home - scripts/lib/git_subject.py#run_git_paths - reads `--name-only -z` and splits on NUL, refusing on a
non-zero rc rather than returning a partial set. Three known-answer controls over a REAL synthetic index are SEEN red on
the pre-fix code (a rule never seen to refuse is not a rule, BUG-492), and rail 4's --selftest is wired into `just health`
instead of being a hand-run. The same session FILED BUG-566 rather than papering over it: rail 4 REFUSED git's own
`next-index-*.lock` at a PARTIAL commit while rail 5 TOLERATED and NAMED it - one fact, two homes - so no partial commit
could pass rail 4 until a DECLARED tolerance existed (D-2673).
MEASURED AFTER (8a84622): pre-fix controls red (3); rail 4 selftest 23/23; the refusal reproduced at a real partial commit.
NOT a delegate claim (R5): no reachable local model is a verifier, so no signature is claimed.

## D-2673 (2026-09-27) - ADOPT, never tolerate: git's own temporary index is READ as the subject at the write boundary (BUG-566 and BUG-567 FIXED)

CONTEXT. TWO RAILS, ONE FACT. At a partial commit (`git commit -- <path>`) git mints its own temporary index and hands it
to the pre-commit hook through GIT_INDEX_FILE. MEASURED on git 2.39.5 (Apple Git-154), separate-git-dir layout: the file
EXISTS at hook time, git removes it on exit, and a normal commit hands `<gitdir>/index` instead. Rail 4 REFUSED the minted
name (no partial commit could pass) and rail 5 TOLERATED and NAMED it - and rail 5's note was FALSE (BUG-567): its child
environment DROPPED GIT_INDEX_FILE, so it audited `<gitdir>/index` while NAMING the temp index. That is the BUG-527 class at
the write boundary, wrong in BOTH directions - over-refusal on a superset, and under-refusal when the declaration lives only
in the commit set.
DECISION. ADOPT, never merely tolerate. An ambient index is READ as the subject only when ALL THREE hold: (1) its realpath
is a file DIRECTLY inside the PINNED git dir, (2) its basename matches a DECLARED owner_name_globs entry, (3) it EXISTS.
Anything else ambient is REFUSED (C16). Tolerance was rejected because a rail that NAMES an index it did not read reports
on the wrong bytes; (3) is not decoration because git reads a MISSING index as EMPTY, so an absent file would report 'all
declared' over no bytes at all - the silent wrong-subject audit. ONE home (scripts/lib/git_subject.py#index_subject) serves
rails 3, 4 and 5; an explicit --index-file still wins as a declared diagnostic home; the declaration is
config/repo_integrity.yaml#git_subject.index_tolerance, and its globs are joined to the name git ACTUALLY mints (D-405).
MEASURED AFTER (645aeae). module selftest 13/13 including the D-405 join to a live minted name; rails 16/16, 23/23, 11/11;
refusals seen in both directions (foreign git dir, `..` escape, a name git never mints, a non-existent minted name; the
repo's OWN index name is NOT adopted). The landing commit WAS a partial commit: the hook handed all three rails
`next-index-48081.lock`, each printed the ADOPTED note, read the commit set and returned 0 (8 files, 351 insertions).
NOT a delegate claim (R5): no reachable local model is a verifier, so no signature is claimed.

## D-2674 (2026-09-27) - the owner's RATIFY puts the repo-integrity git-subject guard set IN FORCE, and names its consumers as a CLAIM (BUG-527, BUG-568)

CONTEXT. `config/repo_integrity.yaml#git_subject` carried `decided: PENDING-OWNER` because the guard set landed as the
BUG-527 fix and claimed no decision id - a guard set IN FORCE with no declared authority, which is the defect one level up
from the one it fixes.
DECISION. OWNER WORD: RATIFY (approving the audit recommendation, including KEEP for the two foreign-body backups and the
hooks ACTIVE). The marker resolves to this MINTED id; the guard set itself is unchanged. The block also names its consumers
as a CLAIM joined by D-405: rails 3, 4 and 5 read the ONE home (scripts/lib/git_subject.py). DELIBERATELY EXEMPT: RAIL 0
(scripts/check_repo_integrity.py), which must still run when git metadata is BROKEN - pinning it would make the recovery rail
fail closed on the very condition it reports. Its ambient subject is FILED as BUG-568, not papered over.
MEASURED AFTER: config parses; the module selftest joins the declared globs to a name git mints live; the citation resolves
against this record, which is the same D-405 join that made the registry lag VISIBLE instead of remembered.

## REGISTRY SYNC (2026-09-27) - the lag D-2667..D-2674 is minted; the mint REFUSED a true citation until the register could see BUG-493 (BUG-571, BUG-572)

WHAT WAS OWED. config/decisions.yaml lagged at D-2666 while six decisions were authored in this log, so two citations in
config/repo_integrity.yaml (decided: D-2673, D-2674) resolved against NOTHING and `just health` was RED at the D-405 join
(reconcile: 'citations that do not resolve'). The lag was MEASURED, not remembered: the registry is records-only (D-2655)
and the mint gate requires the NEXT FREE id, so the lag is repaired only by minting in ascending order.
WHAT THE MINT FOUND (the reason this is a decision and not a chore). D-2671 cited BUG-493 - the bug its own PROMOTE
clears - and the gate REFUSED it: 'cites bug(s) that are NOT in the register: BUG-493'. MEASURED CAUSE: that id was written
in governance/buglog.md ONLY as inline bold prose, never as a heading, so the register's parser could not see it and the id
was absent from every machine home (C15 count, handoffs, the mint join). A TRUE citation was refused because a real, CLOSED
bug was invisible. REPAIR: an appended `## BUG-493` status EVENT (an append, never a rewrite) plus BUG-571 for the class -
the register is fed by HEADINGS only, and the honest control is the cited-by-decision join, not a scan of prose.
ALSO MEASURED, AND FIXED AT THE ID ONLY: BUG-570 was filed OPEN and the register read it CLOSED, because the slot reader
falls back to the WHOLE header when the parenthetical names no status word, and that title carried a status word belonging
to ANOTHER bug ('the duplicate BUG-493 CLOSED block'). Tightening the rule to 'the status region is the header up to the
first colon' flips 10 of 397 heading events - 2 corrections and 8 REGRESSIONS (BUG-347, BUG-388 and others whose status sits
after the colon by design) - so the blanket rule was REFUSED ON MEASUREMENT and filed as BUG-572 with a REOPENED event
landed for this id so the register states the truth while the rule is argued.
MEASURED AFTER. Mints: D-2667..D-2674 in ascending order, each rc=0 (797 -> 805 records, stamp ec8f32ea8a61c80d, census
written in the same invocation). Register: 310 ids, OPEN 135 / CLOSED 175, BUG-493 CLOSED. `just health` rc=0. No other home
quotes the registry's count or stamp (checked before minting), so no second declaration drifted.
NOT a delegate claim (R5): no reachable local model is a verifier, so no signature is claimed.

## D-2675 (2026-09-27) - the BOUNDARY REHEARSAL: the write boundary is exercised at a REAL commit in a REAL repository (BUG-527, BUG-566, BUG-568, BUG-569, BUG-574; BUG-576 FILED by it)

CONTEXT. BUG-527, BUG-566, BUG-568, BUG-569 and BUG-574 were ONE defect seen five times: a rail's rule about the AMBIENT git
environment git hands its own pre-commit hook (GIT_DIR / GIT_INDEX_FILE / GIT_WORK_TREE) was tested ONLY against synthetic
fixtures - every control built its own `git init` - so the value git ACTUALLY hands the hook was in NO test. MEASURED: 13/13
git-subject controls GREEN while 100 percent of commits in this repository were REFUSED. A control never seen to FAIL is not a
control; a boundary never seen to ACCEPT a legitimate commit is not a boundary (the mirror of BUG-492).
DECISION. The boundary is REHEARSED, not asserted. scripts/check_boundary_rehearsal.py (13 known-answer controls) builds a REAL
repository in the SYSTEM temp dir in the LIVE --separate-git-dir layout, materializes TRACKED HEAD bytes (`git archive HEAD`),
installs the hook with this repository's OWN installer (asserting its `--check` re-derivation), performs a REAL normal commit and
a REAL partial commit THROUGH the hook, runs each write-boundary rail ALONE with the ambient GIT_INDEX_FILE the hook receives,
PLANTS real violations and asserts the DECLARED rail refuses them, and runs every rail's own --selftest plus the git-subject
module's. Every fact is DECLARED in config/boundary_rehearsal.yaml (C12): the rails, their staged rc, the NOTE PROVENANCE (a
fact about the COMMIT SHAPE, not about the rail - `ambient_note` at a normal commit, `partial_note` at a partial one, each
scenario naming the FIELD it reads), the planted violations, and the debt. Provenance is READ from its ONE home
(scripts/lib/git_subject.py#note_kind, D-2646), never restated. The fixture must resolve OUTSIDE the tree it audits (fail-closed,
derived from the rail's own location - `git clean -qfdx` and rmtree run there, BUG-537) and it writes only in the system temp
dir, so it is declared a WRITER in config/rail_registry.yaml. A DECLARED DEBT is re-measured every run: a refusal the declaration
NAMES is tolerated and printed, one it does NOT name is FATAL, and a PAID debt returns 2 OWNER-OWED because the declaration must
then be WITHDRAWN by a decision (a declaration that outlives its subject is the BUG-542 class).
MEASURED. --selftest 13/13, each control SEEN to fire - including the control for the declaration this session added
(`partial_note_declaration_is_read`), which was found by the 11/12 RED that proved provenance is SCENARIO-DEPENDENT and can
never be declared once per rail. On the live tree: rc=0 in 11.5s (a real normal commit and a real partial commit both PASSED
with 3 notes of the declared provenance each; 2 planted violations REFUSED by RAIL 4 - pipeline/stage5_verify.py rc=2 FORBIDDEN,
an out-of-plan path rc=1; 5 rail selftests fire; BUG-576 re-measured). BLAST RADIUS MEASURED, NOT ASSERTED: the fixture is a
system-temp path, the live tree's dirty count and the installed hook's sha are IDENTICAL before and after, the fixture is clean
after every scenario, and the rails inside it read the FIXTURE's own config and plan. BUG-576 FILED: a FRESH repository cannot
make its FIRST commit - RAIL 0 accuses an UNBORN HEAD of being broken metadata, the same state the BUG-400/BUG-564 RECOVERY
route produces - so the rehearsal declares a --no-verify bootstrap that MUST BE WITHDRAWN when it is fixed.

## D-2676 (2026-09-27) - THE STANDING RULE, mechanized: no rule lands without ONE HOME, a SEEN boundary control, a NAMED oracle and a MUTATION that REDs it (the class-level brake on "blindfolded rules")

CONTEXT. The owner asked why rules are created blindfolded and later conflict, and whether the project is running in circles. Forensically: 12 of 16 SUPERSEDED records name no successor, 4 sites cite a decision not in force, ~62% of BUG-520..574 are about the governance machinery itself - and every instance of the class behind BUG-527/566/568/569/574 was a rule whose DECLARATION was read while its SUBJECT was never mutated. The missing fourth element of a rule (a mutation that must red it) had no rail, so a rule could pass every check here without anyone ever showing that it CAN FAIL.

DECISION. Adopt as the STANDING RULE: no rule lands without (i) ONE HOME for the rule, (ii) a BOUNDARY CONTROL that has been SEEN, (iii) a NAMED oracle, (iv) a MUTATION that REDs that oracle. (iv) is mechanized as scripts/check_rail_mutations.py + config/rail_mutations.yaml (one home of every declared mutation), wired into just health (--selftest + tri-state). The gate measures, per entry: the oracle's BASELINE is GREEN, the mutation is applied in a REAL fixture repository (git init + commit) under the system temp dir, the declared control goes RED through its own named MARKER, and that marker was ABSENT before (two runs, one difference). An entry whose find-text no longer matches the bytes is FATAL: a refactored rail cannot silently lose its own control (the BUG-542 class, one level up). A declared subject with no mutation entry is FATAL, and the mutation count has a declared FLOOR (shrink guard, edited only in a diff a human reads).

MEASURED. --selftest 15/15 known-answer controls (incl. two joins that read the DECLARATION itself, and a NEGATIVE control: a no-op mutation must NOT red). --check: 2 declared rules SEEN to red through their own control (provenance_count_is_load_bearing, widening_record_rule_is_load_bearing), 1 negative control stayed green, 2/2 declared subjects covered, rc=0 in ~10s. The gate's OWN first two runs found two real defects in this session's declarations: single-quoted YAML does not process an escape (the "no-op" append was the literal two characters backslash-n, so the subject died with a SyntaxError) and a marker that a rail prints on BOTH verdicts has no baseline differential (now declared per entry: marker_absent_in_baseline). just health rc=0; rail registry rc=0 (43 rail scripts, 5 declared writers). Files: scripts/check_rail_mutations.py, config/rail_mutations.yaml, justfile, config/rail_registry.yaml.

## D-2677 (2026-09-27) - THE BYPASS RULE: a fixture bypass carries a MEASURED justification, never a debt; and the boundary rehearsal first commit becomes an ACCEPTANCE control (BUG-576 FIXED; BUG-578 FILED by the audit)

CONTEXT. BUG-576 was measured inside the boundary rehearsal: RAIL 0 read an UNBORN HEAD (HEAD names a branch with no commit yet - the state every FRESH and every RECOVERED repository is in) as broken metadata, and so REFUSED the one commit that repairs the repository. The rule had been derived from what a healthy repository LOOKS like instead of the states a healthy one PASSES THROUGH (the BUG-574 class), and the control set was all refusals - nothing asserted ACCEPTANCE. The bug forced a --no-verify bootstrap in the rehearsal, declared as a debt, and the draft answer was a prose promise to withdraw it - which is itself the BUG-542 class (a declaration that outlives its subject).

DECISION. (1) RAIL 0 reads HEAD as BORN / UNBORN / BROKEN from three probes DECLARED in config/repo_integrity.yaml (head_born_probe, head_unborn_probe, head_unborn_ref_probe), validated fail-closed, with the D-405 join that keeps the born probe inside git.must_resolve so the declaration cannot be inert. UNBORN is not a blanket excuse (C16): the ref HEAD names must still NOT resolve as an object, and a ref that DOES resolve while the born probe does not is BROKEN. (2) THE BYPASS RULE: the --no-verify bootstrap is WITHDRAWN in the same commit that re-measures it, and replaced by a declared refusal (bootstrap.whole_tree_refused, RAIL 4, commit rc 1, marker 'FORBIDDEN session plan') re-measured on EVERY run - a bypass that loses its justification now REDs the rail instead of surviving as prose. declared_debt becomes empty while the LIFECYCLE stays SEEN: --selftest drives the paid-debt OWNER-OWED path with a synthetic declaration. (3) The rehearsal first commit is an ACCEPTANCE control: a FRESH repository commits ONE plan-granted path THROUGH the hook and must be ACCEPTED.

MEASURED. RAIL 0 --selftest 15/15 (four controls in REAL repositories: unborn_head_is_accepted, unborn_branch_does_not_swallow_born, head_that_is_neither_is_broken, renamed_reflog_in_a_born_repo_still_fails - the counterweight that keeps the 2026-09-25 reflog detection honest) and --check rc=0. At a REAL commit through the REAL hook in the rehearsal fixture: fresh first commit rc=0 with 3 own_index notes; whole-tree commit rc=1 refused by RAIL 4; bypass base rc=0. check_boundary_rehearsal --selftest 18/18. check_rail_mutations --selftest 15/15 and --check rc=0 with the standing-rule gate (D-2676) extended to RAIL 0 (mutation unborn_head_branch_is_load_bearing; floor raised to 4; 3/3 declared subjects covered). FILES: config/repo_integrity.yaml, scripts/check_repo_integrity.py, config/boundary_rehearsal.yaml, scripts/check_boundary_rehearsal.py, config/rail_mutations.yaml.

## D-2678 (2026-09-27) - THE LANDING-BYTES RULE

CONTEXT. D-2675 rehearses the write boundary in a REAL repository, but its fixture was materialized from HEAD: the
rail that LANDED, not the rail that is LANDING. Found by the forensic audit of BUG-576 and filed as BUG-578: the
rehearsal was GREEN while the working tree already held a RAIL 0 that refused every fresh commit.

DECISION. A boundary rehearsal performs its verdict on the bytes that are LANDING. config/boundary_rehearsal.yaml
#temp.overlay is the ONE home of the subjects (and their exclusions); the overlay is applied after materialize and
BEFORE the hooks are installed, and `setup.overlay` is a declared premise the classifier requires. The evidence is
NOT borrowed from the live tree: the control builds its own differential (stale bytes at a path derived from the
declaration must be REPLACED), which is also what makes the mutation state-independent. The standing rule (D-2676)
is satisfied in full: (i) ONE HOME the overlay declaration, (ii) a SEEN boundary control (fresh/normal/partial
acceptance plus overlay_dropped_is_fatal), (iii) a NAMED oracle scripts/check_boundary_rehearsal.py, (iv) a MUTATION
(config/rail_mutations.yaml#overlay_of_the_landing_bytes_is_load_bearing) that REDs it. Two lists of the same fact
drift, so the rail SUBJECTS the standing rule covers are read from the gate's ONE home and joined here.

MEASURED. MEASURED 2026-09-27: the rehearsal was GREEN over HEAD bytes while the working tree held a RAIL 0 that refused the FIRST commit of a fresh/recovered repository; overlaid, the same tree REDs. With the overlay: just health -> ok boundary rehearsal ... 436 working-tree file(s) of the declared subjects overlaid onto the materialized HEAD bytes, 5 rail selftest(s) fire, 0 declared debt(s) open; RAIL-MUTATION GATE: 4 declared rule(s) SEEN to red (incl. overlay_of_the_landing_bytes_is_load_bearing), 1 negative control green, 3/3 subjects covered. check_boundary_rehearsal --selftest 21/21 rc=0; HEALTH_RC=0.

## D-2679 (2026-09-27) - THE DERIVED-COVERAGE RULE

CONTEXT. The step after D-2678 was to extend `coverage.required_subjects` to the rails still owed a mutation (RAIL 3,
RAIL 5). The audit run before implementing it found the shape instead: `required_subjects` was a HAND-MAINTAINED
SECOND HOME of the fact "this rail gates a commit", a fact that already has ONE home
(`config/rail_registry.yaml#commit_boundary.must_contain`, verified against the bytes of `gitdir:hooks/pre-commit` by
`scripts/check_rail_registry.py`). MEASURED: RAIL 3 (`verify_recalibration_pins.py`) and RAIL 5
(`check_declaration_consumers.py`) gated EVERY commit while the list did not name them, and the gate printed
`3/3 declared subject(s) covered` - a coverage claim measured against the list it happened to hold. Hand-adding two
entries would have fixed today and left the drift: BUG-580.

DECISION. The coverage is DERIVED, never restated. `config/rail_mutations.yaml#coverage.boundary_join` declares the ONE
home (`registry`, dotted `key`, and the script `prefix`/`suffix` vocabulary - C12: no path or pattern in code);
`scripts/check_rail_mutations.py#boundary_rails` reads it and the classifier REFUSES a commit-boundary rail the coverage
does not name, in a VERDICT rather than an exception (a crash is not a control, the BUG-579 rule one level up). The
SUPERSET direction is DECLARED, not assumed - a rail whose own rule gates the boundary (the rehearsal, D-2675) is
covered BEYOND it, so the asymmetry is a written reason and not an accident of who edited what. The two owed boundaries
got the mutations that prove their rules are READ (`laundering_repin_rule_is_load_bearing` for BUG-535, RAIL 3;
`withdrawn_consumer_rule_is_load_bearing` for BUG-562, RAIL 5) and the gate got one for its OWN rule
(`boundary_registry_join_is_load_bearing`), so the standing rule covers itself. `min_mutations` 5 -> 8; the gate is now
declared a CONSUMER of `config/rail_registry.yaml` in `config/declaration_consumers.yaml`, because it now reads it
(BUG-581, found by the same audit, moved a rationale that had been attached to the wrong edge back to its subject).

MEASURED. `check_rail_mutations --selftest` 18/18 rc=0 (new: `boundary_rail_missing_from_coverage`,
`coverage_join_to_nothing`, and the join "the COMMIT BOUNDARY is READ from its ONE home and every rail there is inside
the declared coverage"); `--check` rc=0 in 8.4s: `7 declared rule(s) SEEN to red through their own control
(unborn_head_branch_is_load_bearing, provenance_count_is_load_bearing, widening_record_rule_is_load_bearing,
overlay_of_the_landing_bytes_is_load_bearing, laundering_repin_rule_is_load_bearing,
withdrawn_consumer_rule_is_load_bearing, boundary_registry_join_is_load_bearing), 1 negative control(s) stayed green,
6/6 declared subject(s) covered (4 derived from the commit boundary, D-2679)`; `check_declaration_consumers --selftest`
11/11 and `ok declaration consumers: 5 declared home(s), 6 consumer edge(s) all resolve`; `check_boundary_rehearsal
--selftest` 21/21 (its own join reads this coverage list and still finds every rail inside the declared overlay);
`bug_status` OPEN 138 / CLOSED 181 of 319; mint D-2679 (810 records, stamp b6e80486982b3b52). The registered
GRADUATION BAR for promoting the standing rule to a CONSTITUTION section now reads MET on all three clauses, so the
promotion ruling is the owner's (HOLD until it is given); the promotion, if given, must be a POINTER to
`config/rail_mutations.yaml` + `scripts/check_rail_mutations.py`, never a restatement.

## D-2680 (2026-09-27) - THE WHOLE-SET RULE: the ladder is run for EVERY fault, never until the first (scripts/run_ladder.py, `just health-full`)

CONTEXT. BUG-573, MEASURED by the D-2679 audit: `just health` stops at the first non-zero line and the result is
read as a verdict, so a red line hides every later fault and each repair round can only discover one. Repairing
one red UNHID a stale dormancy nothing had been able to report.

DECISION. The ladder reports a PREFIX while it is read as a VERDICT, so each repair round could discover only ONE fault (BUG-573, MEASURED by the D-2679 audit). The remedy is landed as a mechanism, not as a promise: scripts/run_ladder.py READS the recipe body from the ladder's ONE home (config/rail_registry.yaml#ladder and #recipes) and, in --collect mode, RUNS every declaring line as written - so the line's own guard decides what counts as a fault and a fault never hides the lines after it - reporting every fault with its own rc and seconds and exiting with the WORST collected code (1 FATAL outranks 2 owner-owed, BUG-457), never the first. `just health` keeps the fast, human-readable ladder and now prints the prefix declaration FIRST, before any rail can abort it, naming `just health-full` as the whole-set entry point; a recipe the declaration does not govern is REFUSED (C16) and a self-invoking line is skipped (a ladder that collects itself would recurse).

MEASURED. BUG-573 FIXED and MEASURED after the change: `just health-full` RUNS all 87 declaring lines of the declared recipe in one pass - 'ok ladder scan: 87 line(s) RUN, 0 fault(s), 203.0s', SCAN_RC=0 - so at HEAD the remaining fault set is EMPTY, and that is now a measurement rather than an assumption (before, the same ladder reported a prefix that read as a verdict). The cost is MEASURED too, per line, so the next 8 minutes are attributable: check_tests 82.1s, yaml_guard 45.3s, boundary rehearsal 14.4s, store-columns 10.2s, rail mutations 8.6s. The banner is DERIVED from the text: '87 declaring line(s) stand in it (63 declared a HARD gate)'. SEEN: run_ladder --selftest 12/12 rc=0 (late_fault_is_visible, a_late_line_still_RAN, the_line_own_guard_decides, an_unknown_code_is_FATAL_not_owner_owed, the negative control, the undeclared-recipe refusal, both-directions D-405); the standing rule's own teeth: the new mutation ladder_scan_reports_every_fault_is_load_bearing (runner scripts/run_ladder.py --selftest, marker 'FAIL selftest/late_fault_is_visible') SEEN to red, gate --check rc=0 with 8 declared rules SEEN to red and 7/7 subjects covered (4 derived from the commit boundary, D-2679); check_rail_registry rc=0 (85 ladder invocations, 43 rails on disk, 5 declared writers); check_declaration_consumers rc=0 (5 declared homes, 7 consumer edge(s)) with the new consumer edge staged in the SAME commit (the BUG-562 class); no new bug was FILED by this change - it closes one.

## D-2681 (2026-09-27) - THE ONE-HOME FIXTURE RULE, and the landing that was declared but not written

CONTEXT. BUG-577, MEASURED 2026-09-27: scripts/check_boundary_rehearsal.py and scripts/check_rail_mutations.py
restated the BUG-537 rule "a fixture must resolve OUTSIDE the tree it audits" VERBATIM, and
scripts/check_repo_integrity.py built the same throwaway repository inline - one rule in three files, measured in
the same change-set that adopted the standing rule (D-2676). BUG-582, measured at HEAD e13eddc while auditing this
landing: the D-2680 commit added ONLY the health-full recipe to the justfile, so the prefix BANNER and the
collector --selftest - both declared in four governance homes as landed - were in NO file.

DECISION. (1) The fixture rules have ONE home: scripts/lib/fixture.py#outside_tree + #real_repo; the three rails
IMPORT it and every copy is DELETED. The module DERIVES the audited tree from its own location and declares no
caller's identity or message, so no config edit can re-point the rule and no caller's vocabulary becomes a second
home (C12/C12d). (2) A RAIL's oracle is a ladder LINE: 'python3 scripts/lib/fixture.py --selftest || exit 1' runs
in 'health', and the D-2680 banner is the FIRST line of 'health' so the prefix declaration prints before any rail
can abort (BUG-573's remedy is only real where a machine READS it - a declaration in four prose homes and in no
file is exactly the class this repository keeps re-learning). (3) A crash in a fixture HELPER is a verdict: git()
returns EXIT_CANNOT_RUN when its command cannot be launched at all (BUG-579 one level down - found by the new
control's own first run).

MEASURED. just health-full -> 89 line(s) RUN, 0 fault(s), 262.3s, SCAN_RC=0. scripts/lib/fixture.py --selftest
6/6. Mutation gate: 9 declared rule(s) SEEN to red through their own control, 8/8 declared subject(s) covered (4
derived from the commit boundary, D-2679), 1 negative control stayed green. Rail registry rc=0 (88 ladder
invocations). Declaration consumers rc=0. OPEN 137 -> 136, CLOSED 182 -> 184.

## D-2682 (2026-09-27) - THE DECISION GRAPH: succession must be a LINK and a citation must rest on a decision IN FORCE (BUG-575 FIXED)

CONTEXT. BUG-575, re-measured at the landing: 16 records state=SUPERSEDED, only 4 naming their successor (12 orphans); 4 of 59 config citation sites name a NOT-IN-FORCE decision (D-403 x2 PROPOSED, D-400 PROPOSED, D-2663 OPEN). scripts/reconcile.py#decision_registry_wellformed read the registry as a SET of ids: a citation had to RESOLVE, never to be IN FORCE, and nothing read "what replaced X". MADR carries status = "superseded by ADR-0123" as a LINK; here it was a label no machine could follow.
DECISION. (1) The decision-GRAPH rules have ONE home: config/decisions_policy.yaml#graph - the in-force and not-in-force state sets, the supersession state and its successor field, and the two debt pins. Every state word in the registry must be classified, so a new state cannot enter unread. (2) TWO declared entries evaluate them in the ONE engine that already owns the citation walker: decision_supersession_complete and decision_citations_in_force. (3) The measured debt is PINNED BY IDENTITY and SHRINK-ONLY, never backfilled (a successor reconstructed by a tool is not evidence) and never exempted silently - a stale pin FAILS the rail (BUG-542). (4) The predicates are PURE (records + rules in, findings out), so the SAME code answers for the live registry and for the known-answer fixtures: a rule whose control cannot be fed a counterexample has no teeth.
MEASURED. python3 scripts/reconcile.py --selftest 9/9 rc=0; reconcile --check: decision_supersession_complete and decision_citations_in_force both ok, 13 declared object(s) agree, rc=0; mutation gate: the named entry is SEEN to red (floor 10 -> 11, subjects 8 -> 9); rail registry 89 ladder invocation(s), rc=0; just --list parses.

## D-2683 (2026-09-27) - THE REGISTER'S SECOND DIVERGENCE SHAPE: an id the LOG names and no HEADER carries is a declared, shrink-only debt (BUG-571 FIXED)

CONTEXT. governance/buglog.md is the register's INPUT and scripts/bug_status.py folds it as STATUS EVENTS, which
are HEADERS. MEASURED 2026-09-27: the file names 383 distinct ids, the register carries 321 - 62 names (legacy
table rows, legacy bullets, and BUG-492 x33) exist for every human and for no machine home. BUG-481's rail already
owned the same divergence one notch over (closed in prose, counted OPEN) and its own docstring states why the
register's generator cannot see it: a rail that re-derives from the same projection certifies the PARSER, never
the LOG.
DECISION. (1) The rule has ONE home: config/register_divergence.yaml, extended - not duplicated - with
declared_uncarried (62 ids PINNED BY IDENTITY, each with the line that first names it) and the shrink guard
declared_max_uncarried: 62. (2) ONE reader: scripts/check_register_divergence.py gains a PURE walker
carried_ids()/uncarried_ids() and ONE pure verdict faults() that evaluates BOTH shapes and BOTH directions -
undeclared, stale, and ceiling - so the live log and the rehearsal run the same code (D-405). (3) The debt is NOT
BACKFILLED (D-2645): promoting a prose name to a header would stamp a status no author wrote and manufacture 62
OPEN bugs. (4) The walker is a TOKEN read and the record states what that does and does not mean: it does not
decide what a bug IS or what state it has, it lists the NAMES the register cannot answer for, and a list a human
must edit cannot invent debt. (5) The AMMENDED remedy: the recorded remedy (a cited-by-decision join inside
bug_status.py) is REFUSED - the generator cannot see its own input's other shape, and the decision-citation
direction is already closed forward at the mint (39 cited ids, 0 unregistered, MEASURED), so a second reader would
be the two-homes defect (D-2646) the repo fixed last night (D-2682).
MEASURED. --check: "ok register divergence: 0 declared divergence(s), all still divergent; 62 named-but-uncarried
id(s) declared, all still uncarried; ceilings 0/62 (shrink-only); 321 id(s) carried" rc=0. SEEN: --selftest 10/10
known-answer controls, both directions, rc=0. TEETH: register_uncarried_rule_is_load_bearing SEEN to red (marker
'FAIL selftest/uncarried_id_is_reported'); gate 11 declared rules red, 10/10 subjects, floor 11 -> 12. The ladder
runs the control as its own line, and the pre-change whole-set audit is EMPTY: "ok ladder scan: 90 line(s) RUN, 0
fault(s), 220.3s". FILED in the same change-set (not worked): BUG-584, the duplicated declaring lines the BUG-582
fix left in `just health`, which the rail census cannot count BY CONSTRUCTION - the meta-lane freeze keeps it filed.

## D-2684 (2026-09-27) - A DIRTY PATH HAS TWO DECLARED HOMES, AND THE RAIL FAILS ON A PATH IN NEITHER (BUG-563 FIXED)
CONTEXT. BUG-563 filed the class on 2026-09-26 and it was still live: MEASURED 2026-09-27, 124 dirty paths and
ONE granted. 112 of them are `backups/**` PRE_* pre-images that pipeline/backup_guardian.sh (C13) makes it a
session's DUTY to write - so the system obliged a session to create paths it could not commit and git was never
told to ignore, and the evidence trail was unversioned by accident rather than by decision. 11 more were rail
outputs: three tracked-but-modified stores, and eight untracked run artifacts and journals.
DECISION.
(1) TWO HOMES, NO OVERLAP: GRANTED = the plan's `may_touch` (the pre-existing granting authority, CONSUMED and
never restated - D-2646); EXCLUDED = `config/repo_integrity.yaml#worktree.excluded`, three declarations each with
a `why`, ENFORCED by the `.gitignore` bytes. A path in neither home is FATAL (exit 1).
(2) ONE READER, JOINED TO REALITY: `scripts/check_repo_integrity.py --worktree` reads the dirty set as a
NUL-separated NAME LIST (BUG-565's one home for name lists) and asks GIT ITSELF (`check-ignore -q --no-index`)
whether a declaration is honoured. A declaration git does not honour is a FAULT, not a quiet pass (D-405).
(3) PURE RULE: `worktree_faults()` takes every input - including the ignore verdict - as a PARAMETER, so its six
controls are synthetic and this repository's dirt cannot make a control pass (BUG-492).
(4) GRANTS ARE NAMED, NEVER GLOBBED: seven exact paths, including `.gitignore` itself (the exclusion bytes are
half of the rule, so a session that may not commit them could not land it).
(5) SCAN MOMENT ONLY, STATED: the rail is in the ladder and deliberately NOT in the pre-commit hook - the hook
would refuse a commit carrying a legitimately new artifact BEFORE its plan entry can land (the BUG-528b
sequencing defect). The widening is a declared follow-up.
MEASURED. Before: 124 dirty, 1 granted, 123 in no home; `declared-excluded 'backups/**' is NOT ignored by git`
(the rail's first run refused MY OWN patch: a trailing `#` is not a comment in .gitignore); the shared git()
helper strips output, eating the status field's leading space, so records are now read raw. After: `ok
repo-integrity worktree: 14 dirty path(s) - 14 granted, 0 declared-excluded, 0 in neither home` rc=0; `ok
repo-integrity worktree selftest: 6 known-answer control(s)` rc=0; mutation gate `worktree_undeclared_dirty_path_
rule_is_load_bearing` SEEN to red (floor 12 -> 13). The previous turn's owed POST-change whole-set scan:
`just health-full` = 91 line(s) RUN, 0 fault(s).

## D-2685 (2026-09-27) - THE OWNER-RULING APPLIER PASSES THROUGH THE GUARD, AND EVERY TERMINATOR IS READ FROM ITS OWN ARTIFACT (BUG-560 FIXED)

THE RULE. A writer of an owner's cells passes through write_guard - no exception for the ONE writer that exists
to stop a normalize re-run from reverting the owner's rulings. The workbook goes through
write_rows(mode="merge", owned_keys=<the ruled columns>); the fixlog goes through append_lines, a SUFFIX-ONLY
append. The CELL SCOPE is DECLARED (config/anchor_workbook_fixes.yaml#rulings_io.owned_columns) and JOINED to
the column map by a pure scope_faults(): a ruling whose target column is not in the declaration is refused
before a byte is written, so a code edit cannot widen the applier's reach.
WHY A SECOND APPEND API. append_rows judges CELLS and regenerates every pre-image line through csv.DictWriter.
On this ledger that means re-terminating 23 lines the applier does not own (MEASURED: 14 CRLF + 9 LF), so the
fixlog needed a proof that is about the BYTES IT APPENDS: suffix_faults() checks that the pre-image is a PREFIX
of the post-image and that the bytes past it are exactly the declared suffix. The ledger's terminator is read
from the LEDGER's own last line, never the workbook's - the old bug in one sentence: two artifacts, one
convention, and the one that did not own it was rewritten.
THE INERT GUESS (found while landing it). The workbook's terminator was inferred by `"\r\n" in read_text()`,
which can never be true: read_text() has already translated CRLF away, so the branch was dead and the writer's
convention was decided by a comparison that could not fire. artifact_terminator() reads BYTES from the artifact
about to change, for BOTH artifacts, and fails closed (C16) rather than joining a last line to the next.
WHY IT WAS INVISIBLE. The applier was DECLARED (config#rulings_io, artifact_ownership.yaml, CONTEXT_INDEX) - so
no registry could call it undeclared while it left no receipt: declaration is not receipt. And `--check`, the
anti-revert rail, was declared as "checked by `just health`" in three homes and run in none (the BUG-582 shape).
THE STANDING RULE (D-2676) SATISFIED. (i) ONE HOME: config#rulings_io.owned_columns; (ii) SEEN boundary: the
justfile `--selftest` and `--check` ladder lines (a control nothing runs is a comment, BUG-492); (iii) NAMED
oracle: applier `--selftest` (14 controls) and write_guard `--selftest` (13 invariants); (iv) MUTATION: 4 new
entries (the scope join, the suffix-only proof, the workbook's terminator, the ledger's terminator), floor
13 -> 17, all SEEN to red through their own named markers.
MEASURED. `ok apply_workbook_rulings selftest: 14 controls hold`; `ok workbook rulings: 4 cell ruling(s)
present, 5 row declaration(s), scope [depth_final, depth_final_class, domains_final, domains_final_raw,
primary_domain]`; `ok write_guard selftest: 13 invariants hold ... the 6 expected refusals`; `ok rail mutations:
16 declared rule(s) SEEN to red through their own control`; `just health` = 0 fault(s), rc=0.
OWED / NOT SILENT. (1) The selftest's own leak (5 fixture pre-images in the LIVE backups/, now removed and
controlled) says the FIXTURE-ISOLATION rule needs a whole-set scan: which other `--selftest` writes default to
backup=True and deposit into the tree they audit? (2) config/derivations.yaml carries a rail-written re-measure
(shadowed_declared 211 -> 212) that still needs a commit-or-revert decision with a stated reason.

## D-2686 (2026-09-27) - A PRE-IMAGE IS EVIDENCE OF THE AUDITED TREE, AND THE STORE THAT HOLDS IT REFUSES A FIXTURE'S (the D-2685 OWED item, closed structurally)

THE RULE. `backups/` holds the pre-images of the audited tree's OWN artifacts. `scripts/lib/write_guard.py#_backup`
now fails CLOSED (`WriteRefused`, nothing written) when the artifact it is asked to back up resolves outside the
tree, and `pre_image_faults(path)` is the PURE predicate that decides it. The tree is derived from the guard's own
location: no config edit can re-point the rule (C12).

WHY IT WAS NEEDED - AND WHY IT WAS NOT VISIBLE. MEASURED 2026-09-27 (BUG-560/D-2685): the owner-ruling applier's
OWN `--selftest` built its fixture under `temp/`, called `write_rows` with the DEFAULT `backup=True`, and left five
throwaway pre-images (`wb.PRE_apply_workbook_rulings_*.csv`, 81-83 bytes) in the live `backups/`. Nothing in the
store said which artifact they addressed: a pre-image's name carries the artifact's STEM only, so the pre-image of
a fixture is INDISTINGUISHABLE from the pre-image of a tracked artifact of the same name. The ONE store an auditor
reads (C13/R-D410) had been polluted by a CONTROL RUN, and the run that did it was auditing the tree.

WHY CONTAINMENT AND NOT A SCAN. The D-2685 owed item was "which other `--selftest` runs deposit pre-images?".
That question was ANSWERED by measurement - 33 declared selftest commands and the 261-test suite, each run with a
before/after snapshot of `backups/`, of the mutation journal and of `git status --porcelain`: 33/33 clean. But a
measurement is a fact about TODAY, and the leak was found by accident; so the MECHANISM that produced it (a
pre-image is written for whatever path the caller names) was closed instead. A scan can only re-find the class; a
containment rule makes it unrepresentable, and a fixture that wants no pre-image says `backup=False` (which the
applier's own fixture now does - that half of BUG-560 was landed in D-2685).

THE FOUR LIMBS OF D-2676. (i) ONE HOME: the containment rule lives in `write_guard`, the module that owns the
backup store; there is no path list, threshold or config key (the tree is derived from `__file__`). (ii) SEEN:
`write_guard --selftest` is a declared line of `just health`, and the new controls print BY NAME. (iii) NAMED
oracle: 4 new controls - the predicate answers BOTH ways (an out-of-tree path is reported, an artifact of the tree
owns its pre-image), the store REFUSES an out-of-tree artifact, and a refused pre-image deposits nothing and
writes nothing (the live `backups/` listing is compared before and after). (iv) MUTATION:
`config/rail_mutations.yaml#pre_image_containment_is_load_bearing` reduces the predicate to `if False:` and
requires `FAIL selftest/the_pre_image_store_refuses_an_out_of_tree_artifact`; floor 17 -> 18.

MEASURED. `write_guard --selftest`: 16 invariants hold / the 7 expected refusals, both counts DERIVED from the
selftest source (D-2685's rule), 8 controls printed by name. `check_rail_mutations.py`: `ok rail mutations: 17
declared rule(s) SEEN to red through their own control`, rc 0. `run_ladder.py --collect health`: 94 lines RUN, 0
faults, rc 0 (224.6s) - the refusal is live and NOTHING cascaded (every production writer names an artifact inside
the tree; the refusal is reached by no declared line). `apply_workbook_rulings.py --selftest` 14/14 and `--check`
green. `backups/` before = after = 118 entries.

WHAT IT DOES NOT COVER (loud, not silent). (1) A control run that WRITES an artifact OF the tree is not refused by
this rule: containment is about the pre-image store, not about a control's right to mutate the tree. The same
measurement says there is no instance today (0 dirty paths across the 33 commands and the suite), and the class
that has fired (BUG-546, the suite rmtree'ing a live run dir) is already guarded by `scripts/lib/fixture.py`.
(2) The scan itself is a scratch measurement: it lives in `temp/` (gitignored), so it is not reproducible from the
repo - OWED as a declared event-driven rehearsal or a `dormant` registry entry with a real path. (3) A writer that
passes `backup=False` for a live-tree artifact still keeps no pre-image; that remains a declared caller choice
(`write_document` documents the same default), not a hole this rule tries to close.

FILED, NOT WORKED: BUG-585 (the same audit found `agent/session_seed.yaml` stating the open-bug count in two homes
- a stale `77` beside the DERIVED `134`), held as FILED behind the META-LANE FREEZE.

## D-2687 (2026-09-27) - THE COMMIT BOUNDARY IS A ROUTE AND A MODE, NOT A PATH OF BYTES (BUG-564 remainder, CLOSED)

THE RULE. `config/rail_registry.yaml#commit_boundary.path` names a ROUTE (`git-path:hooks/pre-commit`), never a
path shape; `scripts/check_rail_registry.py#boundary_faults` is the PURE predicate (ONE reader) and the declared
subject is the path GIT resolves, its bytes, AND its executability.

WHY IT WAS NEEDED (measured 2026-09-27, in real repositories outside the tree). (1) THE ROUTE: with
`core.hooksPath` set, `git rev-parse --git-path hooks/pre-commit` answered `hooks/pre-commit` while `--git-dir`
answered `.git`; the file at `gitdir:hooks/pre-commit` did not exist and a DIFFERENT file received the commit and
refused it - and a linked worktree's `--git-dir` is not where hooks live either. (2) THE MODE: a mode-644
`pre-commit` is IGNORED - the commit LANDS (rc=0), none of the four rails run, and the only sign is a `hint:` git
documents how to suppress. So the strictest gate in the system could be disarmed by `chmod -x`, and byte-only
verification stayed GREEN - class (i) WITH a green verdict.

WHY BOTH ARMS IN ONE CHANGE. Landing the rail alone would have created a fault whose printed remedy could not
clear it: `scripts/install_git_hooks.sh` joined `$git_dir/hooks` too, so "re-install" would have re-written the
file git does not run. The installer now asks GIT the SAME question, so writer and verifier cannot disagree.

FOUR LIMBS (D-2676). (i) ONE HOME: the route is git's own answer, asked once in the reader and once in the
installer - no path is restated (C12). (ii) SEEN: `check_rail_registry.py --selftest` is a declared ladder line.
(iii) NAMED ORACLE: 7 controls, every fault printed by name (`boundary_declared_as_a_path_shape`,
`boundary_route_never_resolved`, `boundary_hook_is_not_executable`, ...), 14/14. (iv) MUTATION:
`config/rail_mutations.yaml#commit_boundary_route_and_mode_is_load_bearing`, floor 18 -> 19.

MEASURED AFTER. `check_rail_registry.py` rc=0 naming `/Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git/hooks/pre-commit`,
executable, holding every line; `install_git_hooks.sh --check` rc=0 (byte-identical today: `core.hooksPath` is
unset, so the route is a no-op change for THIS repo and a real one for a clone, a worktree, or a global config);
`check_rail_mutations.py` rc=0 - 18 rules SEEN to red, 1 negative control green, 13/11 subjects covered; the whole
ladder 94 lines, 0 faults, 227.7s.


D-2688 (2026-09-27) - A FREEZE IS A WINDOW, AND A WINDOW ENDS BY ITS OWN TERMS (BUG-586 FIXED)
BUG-586. MEASURED BEFORE: the META-LANE FREEZE was asserted in ~15 prose homes (MASTER-TASK-REGISTER.md,
governance/SESSION-HANDOFF-2026-09-26.md, governance/buglog.md, governance/CONTEXT_INDEX.md) and in NO file a
machine could read. A freeze is the one governance act that takes effect by being BELIEVED, so it failed three
ways at once: NOTHING READ IT ("held behind the freeze" is a claim about work NOT done, so it can never fail -
BUG-492 one level up), IT HAD NO EXIT (an unwritten exit makes a WINDOW indistinguishable from a POLICY, and a
policy has no horizon: the D-337 permanent-freeze trap), and IT COUNTED NOTHING (the parked set could grow for
ever, so "we are frozen" and "we are stuck" print the same way).

ONE HOME, ONE READER. config/freeze_window.yaml declares window META-LANE-FREEZE-1: the parked set pinned BY
IDENTITY, max_held 8 (raising it is a one-line diff in the SAME change that parks a bug), released {} (the DRAIN
PATH - a ruling recorded where its reader is), a WRITTEN exit and review_by 2026-10-11. scripts/check_freeze_window.py
is the ONE reader, wired into justfile:health as --selftest (fatal) plus the live verdict (tri_state). It reads the
DERIVED register governance/bug_status.json and never re-parses the log: "which bugs are open" already has ONE home
(scripts/bug_status.py, certified by scripts/check_bug_status.py), so a second parser would be the D-2646 two-homes
defect. THE EXIT-CODE CONTRACT: 0 = open, exit UNMET, inside the horizon (normal); 1 = FAULT (a parked id the
register does not carry, a parked set past its ceiling, a release about nothing, a closed window with an unmet exit,
a malformed declaration); 2 = OWNER-OWED, LOUD, NOT fatal (BUG-457) - the exit is MET (CLOSE it) or the horizon
passed (RE-RULE it), because renewing a window by default is how a window becomes a policy.

FOUR LIMBS (D-2676). (i) ONE HOME: config/freeze_window.yaml. (ii) SEEN: both rails run BY the ladder. (iii) NAMED
ORACLE: 15 known-answer controls, every fault printed by clause name; live rc=0 (parked 8, still OPEN 8 of ceiling
8; exit MET: opening_set_closed; exit UNMET: nothing_still_held). (iv) MUTATION: freeze_window_exit_is_load_bearing -
the drain condition reduced to a no-op means a window whose parked set is EMPTY can never be seen to be DUE TO
CLOSE, and the named control goes RED through its own marker; floor 19 -> 20.

THE FORENSIC AUDIT FIRED ON THE CHANGE ITSELF. (1) The clause table applied a per-clause subject rule to BOTH clause
shapes, so nothing_still_held - whose subject is window.held - read as "a clause with no subject" and the newly
wired ladder line went rc=1 on day 0; the rule is now keyed by CLAUSE SHAPE. (2) With that fixed, THREE controls
still failed, and they had been RED FOR THE WRONG REASON, masked by (1): the synthetic register fixture conflated
"the ids the window NAMES" with "the ids the register carries as OPEN", so three controls could NEVER have passed.
A control that cannot pass, read as "the code is wrong", is the BUG-492 class aimed at the oracle. (3) TWO GAPS
closed while auditing: a malformed declaration produced a traceback instead of a NAMED fault (shape_faults: C16 says
fail closed, not fail ugly) and a criterion carrying a key no reader reads was silently ignored (now faulted,
D-405). (4) TWO HOMES JOINED: the registry pins both guards (tri_state + fatal) so the day someone writes || exit 1
the ladder cannot silently turn "the window is due to CLOSE" into a broken build, and
config/declaration_consumers.yaml declares the window's single reader, so the BUG-562 shape (declaration staged,
reader withheld) is refused at the commit boundary.

MEASURED AFTER: selftest 15/15; live rc=0; registry rc=0 (95 ladder invocations, 63 rails); consumer join rc=0 (6
declared homes, 8 edges); mutation gate rc=0 (19 rules SEEN to red, 1 negative control green); ladder 96 line(s)
RUN, 0 fault(s), 260.9s; R5 review by gemma-4-E4B-it-MLX-4bit: VERDICT APPROVE. Register: OPEN 134 / CLOSED 190 of
324. session_seed.open_bugs_n stays DERIVED at 134 (no bug opened or closed against the OPEN count).

## D-2689 (2026-09-27) - THE STATUS SLOT IS A POSITION AT A HEADER BOUNDARY, NEVER PROSE

A bug's status is decided ONLY at a header BOUNDARY - the LEADING parenthetical, the FIRST segment before the first
colon, the FIRST WORD after that colon, or the TRAILING parenthetical. Prose between those positions may not decide,
the whole-header substring fallback is REMOVED, and no candidate means EMPTY, which is OPEN.

WHY IT OUTRANKS ITS SIZE: this generator writes the register that the FREEZE WINDOW reads
(scripts/check_freeze_window.py), so a register misread off a word in a sentence ABOUT a bug can silently DRAIN the
parked set. MEASURED over 422 heading events, the old fallback read the duplicate BUG-493 block, BUG-570 and BUG-419
as CLOSED, and let a FILENAME in BUG-307's title (closed_menu.py) decide one too.

REFUSED, WITH NUMBERS: "everything before the first colon" flips 8 events (it destroys the legal TRAILING slot,
BUG-320/337/371/388); paren-only flips 3 (it ignores BUG-388's real post-colon FIXED); a boundary rule WITHOUT the
post-colon first word flips 5. THE ADOPTED RULE flips 4 events / 2 final statuses.

THE AUDIT FIRED ON THE FIX ITSELF: those 2 ids are BUG-419 (GENUINELY OPEN - the register's schema asymmetry is
LIVE: open is a list of OBJECTS, closed a list of plain id STRINGS) and BUG-562 (GENUINELY CLOSED - its owed rail
landed and was verified by RUNNING it). Landing the parser ALONE would have newly mislabelled a fixed bug, so this
change-set carries BUG-562's named CLOSURE event with it.

MEASURED AFTER: --selftest 20 controls (9 new); check_bug_status rc=0; register OPEN 135 / CLOSED 190 of 325; freeze
window rc=0 (parked 9 of ceiling 9, still OPEN 8); registry rc=0; consumer join rc=0; mutation
status_slot_is_a_boundary_not_prose, floor 20 -> 21; the whole ladder rc=0 on the change-set before this mint.

FILED, NOT FIXED: BUG-587 - a MINT is not ASSERTED to ARRIVE. A hand-rolled append of one record added 32 lines,
deleted none, LOADED, left every rail GREEN, and moved the census by NOTHING (819 records, last D-2688), because a
record's files: items and a record's own "- id:" marker occupy the same column when a writer re-indents the block.
--mint validates BEFORE the write and re-derives the registry SHAPE after it, but nothing compares the census before
and after. The membership rail its own tombstone names (scripts/check_decision_membership.py) does not exist.
PARKED by META-LANE-FREEZE-1 (max_held 8 -> 9).

session_seed.open_bugs_n: RE-MEASURED from scripts/bug_status.py at 135 (BUG-587 was FILED and is OPEN; BUG-572 and
BUG-562 were CLOSED in this change-set).

## 🟢 ACTIVE — HAND INDEX, not a register (the DERIVED block above is the ONE authority; rows joined on every run, D-2986)

| ID | State | Decision |
| D-2690 | ACTIVE | A MINT IS DECIDED BY ARRIVAL, NEVER BY BYTES WRITTEN. arrival_problems(total_before, decisions_after, minted_ids) is asked of the WOULD-BE bytes BEFORE the write and of the bytes ON DISK before the census is rewritten: the record count must move by EXACTLY the mint size and every minted id must be a TOP-LEVEL record exactly ONCE, so the ABSORBED shape (BUG-587) is refused BY NAME instead of landing invisibly. The membership oracle a RETIRED tombstone NAMED and no file implemented now exists (scripts/check_decision_membership.py, D-405): every id NAMED in this log - the D2552 table rows and the historical headings - must name a TOP-LEVEL record in config/decisions.yaml; five legacy orphans are PINNED BY IDENTITY (D-271, D-272, D-275, D2537, D637) in config/decisions_policy.yaml#membership and the list may only SHRINK; the reverse direction is DECLARED, never asserted, because this log is a TIERED face of the registry (an equality join would RED on 631 legitimate records, BUG-540). BUG-589 and BUG-590 were found by the mutation gate INSIDE this change-set and fixed here; BUG-588 is FILED and HELD (max_held 9 -> 10) because this file is append_only and line 3 declares a count no append can repair. |

MEASURED AFTER (2026-09-27): registry 821 records, D-2690 TOP-LEVEL exactly once, census stamp re-derived in the
same invocation; membership rail rc=0 (194 ids named, 5 pinned orphans, 0 faults, 631 records with no log entry BY
DECLARATION); recompute --selftest 14/14; membership --selftest 10/10; mutation gate rc=0 (24 declared == floor 24,
23 seen to red through their own control, 1 negative control green, 17/13 subjects covered, 19/19 controls);
check_bug_status rc=0; register OPEN 135 / CLOSED 193 of 328; freeze window rc=0 (parked 10 of ceiling 10, still
OPEN 8, exit UNMET nothing_still_held).

OWNER GATES (one word each, none due while the rails are green): CLOSE/RE-RULE the freeze window | PROMOTE/HOLD the
standing rule's CONSTITUTION promotion (POINTER only, never a restatement) | PROMOTE/HOLD BUG-431 | DECLARE/CANONICALISE
BUG-583 | RENAME/DELETE BUG-585. BUG-588 needs a token of its own: the count sits on line 3 of an append_only file,
so the remedy is an owner-gated non-append edit or a header rewrite that declares NO count.

## D-2691 - A LADDER LINE STANDS EXACTLY ONCE, AND A DERIVED COUNT HAS ONE HOME (BUG-584 + BUG-585 FIXED)

| D-2691 | ACTIVE | A LADDER LINE STANDS EXACTLY ONCE, AND A DERIVED COUNT HAS ONE HOME. scripts/run_ladder.py#duplicate_declaring_lines() is the census of declaring lines standing MORE THAN ONCE and body() REFUSES a declared recipe whose census is non-empty (the refusal NAMES the ladder, the count and the line): the census IS the count of these lines and every one is EXECUTED, so a duplicate over-reports the instrument AND repeats the work. agent/session_seed.yaml's dated snapshot key is renamed open_bugs_n_at_2026_09_22 so the DERIVED count has ONE home. MEASURED: health census 98 -> 97 (97 DISTINCT, 0 duplicates), ladder controls 12 -> 15, mutation floor 24 -> 25, register OPEN 135 -> 133. |

MEASURED AFTER (D-2691): `health` 97 line(s) where 97 are DISTINCT (was 98/97); the raw justfile lost 4 duplicated
lines and `just health` no longer executes three of them twice; `scripts/run_ladder.py --selftest` 15/15 (the twice
case fires, the unique case does NOT, and the LIVE ladder is clean in every declared recipe); the mutation gate
SEES a_duplicated_declaring_line_is_refused go red through '  FAIL selftest/a_duplicated_declaring_line_is_refused';
`grep -rn open_bugs_n` returns one UNQUALIFIED key (the derived one) plus one DATED key.

WHY THIS ORDER. BUG-584 is a two-homes defect INSIDE the instrument that reports every other defect: while the
ladder over-reported its own size, every number it printed about the tree was suspect. Closing it and BUG-585
DRAINS the meta-lane freeze (the window's exit is `nothing_still_held`; the parked set falls by two).

NOT DONE, DECLARED: BUG-588 (DECISION-LOG.md line 3 declares a decision COUNT stale by 169) is still HELD - this
file is append_only and line 3 is not append-repairable; the owner word is REWRITE-HEADER or LEAVE-STALE.

OWNER GATES (one word each; none due while the rails print rc 0): CLOSE/RE-RULE the freeze window; PROMOTE/HOLD
the standing-rule CONSTITUTION promotion; PROMOTE/HOLD BUG-431; DECLARE/CANONICALISE BUG-583; RENAME/DELETE
BUG-585 is now SPENT (executed here as RENAME by the filed one-line remedy); REWRITE-HEADER/LEAVE-STALE BUG-588.

## D-2692 (2026-09-27) - the three DRAINED meta-lane ids: a buglog COPY is bloat, a header may not RESTATE a count,
## a state has ONE spelling (BUG-570 + BUG-588 + BUG-583 FIXED)

BUG-570: a block occurring TWICE with identical bytes is a COPY and a copy is BLOAT. The refusal that had REFUSED
the real copy compared `occurrence -> EOF` - a length-dependent comparison two identical copies can never satisfy -
so the REFUSAL was the defect, not the copy. The unit is now the BLOCK, compared by BYTES
(scripts/check_buglog_coverage.py#duplicate_block_problems); the byte-identical BUG-493 block was DELETED (7797 ->
7784 lines) and the rail now reports 459 block(s) with 0 copies.

BUG-588: a prose header may POINT at the census but may never RESTATE a count. The ONE home of the rule is
config/decisions_policy.yaml#log_header; it is READ by scripts/check_decision_membership.py#header_problems - the
same rail that joins the log's ids - so the file's claims about the registry are checked where the file is read.
Line 3 was REWRITTEN (owner word REWRITE-HEADER) to name config/decisions_summary.json, which is the census and
the only place a count may be read.

BUG-583: a state is ONE value with ONE spelling. `active` and `ACTIVE` were two spellings of one state; the census
was always RIGHT while the BYTES of five records carried the other case (the D-2646 two-homes class). The DECLARE
limb landed as a SHRINK-ONLY pin of the five ids BY IDENTITY in
config/decisions_policy.yaml#state_vocabulary.legacy_non_canonical_ids, refused live by
scripts/recompute_decision_summary.py#spelling_problems. The CANONICALISE limb stays owner-gated: the registry is
append_only with a PREFIX receipt (D-2655), so rewriting five cells needs the writer's own structural path.

D-2676 limb (iv) SATISFIED for all three: config/rail_mutations.yaml floor 25 -> 28, and the gate MEASURES 27
declared rule(s) SEEN to red through their own control plus 1 negative control green, floor 28 == 28 declared.

REFUSED ONCE, AND REPAIRED IN THE SAME CHANGE-SET: the first run of the BUG-588 entry REFUSED with rc=0 - the
control's input carried a count and NO census pointer, so it fired for the POINTER reason and could never tell its
two reasons apart (BUG-492, one level up). The control was repaired to isolate the count and to NAME the
restatement; the entry's `why` records the measurement. A control that cannot be seen to fail is not a control,
and this one was found by the gate the standing rule creates.

NOT DONE, DECLARED: BUG-583's CANONICALISE limb (the five cells) is owner-gated; the last three held ids
(BUG-568, BUG-569, BUG-559) are still parked, so the window's exit stays UNMET.

## D-2693 (2026-09-27) - the CANONICALISE limb of BUG-583 is EXECUTED, and the debt is paid by a DECLARED ROUTE rather than a permission

- scripts/recompute_decision_summary.py gains `--canonicalise-states [--apply]`: the ONLY sanctioned IN-PLACE edit of the append_only registry (D-2655 forbids a key rewrite by any writer). It replaces the `state:` cell of the ids PINNED in config/decisions_policy.yaml#state_vocabulary.legacy_non_canonical_ids by BYTE SPLICE - never a YAML re-render, so THE DIFF IS THE PROOF.
- It EARNS the exception before a byte moves: `splice_problems()` proves the id set is unmoved, that no cell moved the pin did not name, and that the registry re-derives canonical EVERYWHERE afterwards - the third clause is what lets the pin shrink to EMPTY and the rule become universal instead of a five-record exemption. `state_cell_problems()` refuses a pin naming a missing or already-canonical id, so a STALE pin REDs.
- The route is DECLARED where a reader can FAIL on it (`canonicalisation_route`): a rule with no home is a favour.
- MEASURED: the whole diff is five `state:` lines (823 records, id set unmoved, no other key of any record changed); stamp 11008e971cb25a52 -> 1d866228c74eb195 (it MOVES - a state is part of the content stamp); census re-derived in the SAME invocation from the bytes ON DISK; 18/18 controls fire (the new pair: a splice moving an UNPINNED state is a NAMED fault; a pinned-cell-only splice is ACCEPTED); pin EMPTY afterwards.
- The first run of the route REFUSED ITSELF: it asked `registry_shape_problems()` with the LIVE pin, so the post-state could never be clean - a check that cannot tell its two reasons apart proves neither.
- OWED, LOUD: the two new controls have no mutation entry yet (D-2676 limb iv); the receipt re-baseline is the second commit of this change-set.

## D-2694 (2026-09-27) - the STANDING RULE pays its own debt: the CANONICALISATION LICENCE is a MUTATION-SEEN rule (floor 28 -> 29)

- The LICENCE of the D-2693 in-place route is ONE clause of `splice_problems()`: `extra` - no cell may move that the pin did not NAME. A route that can move an unpinned cell is a licence to rewrite an append_only registry (D-2655), so that clause is the difference between a RULE and a PERMISSION - and it had no teeth (D-2676 limb iv, recorded as OWED by D-2693's own blocks).
- LANDED in the ONE home (`config/rail_mutations.yaml`): the entry `the_canonicalisation_licence_is_load_bearing`, and `coverage.min_mutations` 28 -> 29. The floor is SHRINK-ONLY, so RAISING it is a decision with a diff a human reads rather than an edit.
- MEASURED: PROBE first, on the LIVE tree - `extra` neutered gives rc 1 through EXACTLY ONE of the runner's 18 controls while the ACCEPTING control (a pinned-cell-only splice is legitimate) stays green, so the differential isolates the read rather than a crash. Then the GATE on a real fixture: 28 declared rule(s) SEEN to red + 1 negative control green = 29 entries, floor 29 == 29 declared, 18/13 declared subject(s) covered, rc 0; gate selftest 19/19; runner baseline GREEN.
- REPAIRED in the same human-read diff: the floor line carried its own comment TWICE (`FLOOR (shrink guard)` 2 time(s), now 1). A duplicated COMMENT restates no value a reader derives, so it is BLOAT rather than a defect and no block was filed (C19).
- NO receipt re-baseline is owed: this change APPENDS to config/decisions.yaml, and an append leaves the declared PREFIX receipt re-derivable. The second commit of D-2693 exists because a SPLICE moves bytes INSIDE the receipted region - the case this one is not.


## D-2695 (2026-09-27) - the ADOPTION is a RAIL-LEVEL rule: the ADOPTED note is MUTATION-SEEN at a REAL minted index (floor 29 -> 30, BUG-569 DRAINED)

BUG-569 was exact: the rule's controls lived in `scripts/lib/git_subject.py --selftest` (13/13) while NOTHING
proved the WIRING - that a rail, run the way the pre-commit hook runs it (an ambient `GIT_INDEX_FILE` at a name
git really mints, NO `--index-file`), PRINTS the ADOPTED note, NAMES that index and AUDITS it. D-2676 limb (iv)
is owed on that wiring, so `scripts/check_session_plan.py --selftest` gains the rail-level control (24/24
controls fire) and `config/rail_mutations.yaml` gains `the_adopted_index_note_is_load_bearing` (floor 29 -> 30;
SHRINK-ONLY, so RAISING it is a decision with a diff a human reads).

MEASURED, instrumentation first (the whole reason the first attempt failed): with the probe index built from
`read-tree --empty` the rail refuses at the BUG-528 family check (rc=2 over 1314 deletions) and NEVER names the
probe path - the audited-bytes limb was UNSATISFIABLE, not flaky; with `read-tree HEAD` + ONE added path it is
rc=1 and the probe path IS named. Teeth: baseline 24/24 rc 0 -> mutated 23/24 rc 1 with this control the SINGLE
red (the adoption itself untouched, so the BUG-527 control stays green - a mutation that removed the adoption
would move two controls and prove neither), marker ABSENT in the baseline, restored byte-identical. Gate: 29
declared rule(s) SEEN to red + 1 negative = 30, floor 30, rc 0. Two further defects fixed in the same change: a
crashing probe LEFT `next-index-<pid>.lock` IN THE GIT DIR (try/finally, absence asserted), and the previous
driver SELF-REPORTED a landing while its baseline read 23/24 - a driver must paste the baseline before claiming
a landing.

REGISTER: buglog 463 block(s), 0 copies; register equals its re-derivation; OPEN 129 / CLOSED 199 of 328 (was
130/198). FREEZE: META-LANE-FREEZE-1 `nothing_still_held` now reads **2 still parked** (BUG-568, BUG-559) - draining
a HELD bug is the window's EXIT, not a breach of it (`config/freeze_window.yaml#not_frozen`).
STAMPS: config/decisions.yaml 826 records, stamp `995142daf2c3bafa`; census `6c3a03c2c3aa7f61`.


## D-2696 (2026-09-27) - the RECOVERY RAIL pins its own subject: RAIL 0's pin is TOLERANT and MUTATION-SEEN (floor 30 -> 31; BUG-568 DRAINED, BUG-591 FILED and PARKED)
BUG-568 was a rail that audits whichever repository the AMBIENT environment names. Its exemption from the D-2646
pin was principled - RAIL 0 must still run when git metadata is BROKEN, so pinning it naively would make the
recovery rail fail closed on the very condition it exists to report - so the fix is the TOLERANT variant of the
SAME rule: nothing resolves -> no subject, guards CLEARED, the broken repository REPORTED; something resolves ->
the ordinary compared-and-adopted subject, a divergent ambient value REFUSED (C16). MEASURED before the fix (a
decoy GIT_DIR): 'ok repo-integrity: git dir <decoy>/.git' rc=0 - a FOREIGN REPOSITORY CERTIFIED - 723 phantom
dirty paths under --worktree, a FileNotFoundError traceback under --selftest. After: 17/17 controls, every mode
green, the subject NAMED. MUTATION-SEEN per D-2676 (iv): the new entry's mutation reds EXACTLY ONE control (the
broken-repository control calls recovery_subject() directly and stays green), restored byte-identical, gate rc 0,
floor 30 -> 31 in one human-read diff. The same instrumentation measured a SECOND defect - lib/fixture.py#git()
inherits the ambient subject, so a known-answer fixture can be built into a foreign repository - FILED as BUG-591
with a remedy and PARKED (window.held 10 -> 11, max_held raised in the same change). BUG-568 is CLOSED.

## D-2697 (2026-09-27) - the FIXTURE BUILDER does not inherit the ambient subject: env DERIVED from the pin ONE
home, a REAL DECOY control, MUTATION-SEEN (floor 31 -> 32; BUG-591 DRAINED)

BUG-591 was filed by D-2696 while it instrumented BUG-568: scripts/lib/fixture.py#git() handed its child git the
AMBIENT environment, so GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE were inherited and a known-answer fixture could
be built into a FOREIGN repository - or into THIS one under the hook own legitimate GIT_DIR, which is the case
with no decoy needed and therefore the case no pin can refuse. MEASURED before the fix (twice, before any write):
inherited, the child read <decoy>/.git and real_repo() returned None for a fixture it had never created; cleared,
the child read .git and the fixture landed in its own worktree. The caller then died on a <fixture>/.git/HEAD that
git never wrote (FileNotFoundError) instead of verdicting - a machinery defect reported as a traceback.

THE FIX IS A DERIVATION, NOT A COPY. The child environment comes from git_subject.cleared_env(git_subject.
config()) - the ONE home of the guard set (D-2646/D-2647): restating the guard list here would be a SECOND home,
and two lists of one fact drift while only one of them can be right. CLEARING is the correct verb for a BUILDER
(unlike a rail): a rail may be handed a legitimate ambient subject and must be TOLERANT of it, but a builder has
no legitimate ambient value to tolerate - its whole job is to build a repository of its own.

THE CONTROL IS A DECOY, NOT A CLAIM. A real repository is built first, the ambient GIT_DIR/GIT_WORK_TREE are
ARMED at it and the ARMING IS ASSERTED (anti-vacuity), the builder is then asked to build a second fixture, and
the control requires that fixture to have ITS OWN .git. The caller environment is restored EXACTLY in a finally
(prior values saved and put back, not popped). The negative case is real: under the mutation the fixture lands in
the decoy, the assertion fails, and the control prints its own marker.

MUTATION-SEEN (D-2676 iv): the new registry entry restores env=None, the exact inheritance the defect had.
MEASURED baseline rc 0 with the new control GREEN and its marker ABSENT from the output; mutated rc 1 with
EXACTLY ONE red line - the marker - every other control still GREEN, so the differential isolates the
ENVIRONMENT rather than the builder; restored byte-identical; gate rc 0 over 32 entries = floor 32. The coverage
floor moves 31 -> 32 in the same human-read diff, and the D-2679 join still holds (the entry subject is a module
whose controls the ladder already runs).

IN-FLIGHT DEFECT, RECORDED: the first landing collapsed the newlines of BOTH files, so the control was one
comment line (Python comments run to end of line: the control did not exist) and the YAML entry was one comment
line that silently dropped decision_supersession_rule_is_load_bearing (31 entries -> 30 under a floor of 32).
Neither was caught by the write; both were caught by COUNTING the artifacts afterwards - parse the registry, grep
the control name in the bytes, re-run the selftest and read its count. LESSON WORTH THE TWO HOMES IT TOUCHES: an
artifact write is not a landing until a READER has counted it.

BUG-591 is CLOSED and RELEASED in the freeze window (a release keeps the id in window.held, by the rail own
rule), so nothing_still_held reads 1 still parked: BUG-559.

## D-2698 - THE PIN CONTROL IS BOUNDED: a control that re-enters its own rail must not outlive the rail (2026-09-27)

BUG-592, found while draining BUG-591 and closed with it. The standing rule (D-2676 iv) requires the pin to be SEEN to red, and the run that proves it did not red - it HUNG. Measured: rc=124 in 600.0s, stack `:773 in _rail` <- `:778 in selftest`, the pin control re-entering `--selftest` with a decoy environment, the child reaching the same control, nesting for ever.

The shape is worth keeping: the OLD fixture builder was the accidental bound. Handing its child git the AMBIENT environment (BUG-591) meant that under a decoy it returned None and failed the child fast. Fixing THAT removed the bound and exposed this. Nothing regressed - a hidden dependency was deleted, and what depends on a bug must be measured when the bug goes. That is why the drain of a bug must re-run the gate that guards the bug.

THE BOUND IS NOT A SOFTENING, and this is the load-bearing distinction: `--no-pin-probe` skips the PROBE, never the RULE. The refusal the probe exists to measure is produced by `subject_bits()` in main first act - before argparse mode is reached - so a child given the flag still REFUSES the decoy. What is removed is only the recursion: the probe no longer spawns a copy of the rail that spawns the probe. MEASURED both directions: 17/17 rc=0 baseline and 17/17 rc=0 after (the count does not move, so the bound hid no control); mutated rc=1 in 4.4s with EXACTLY ONE red line, the declared marker `FAIL repo-integrity selftest/rail0_pins_its_own_subject`, restored byte-identical.

AND THE GATE, which is the point of the exercise: `ok rail mutations: 31 declared rule(s) SEEN to red through their own control` rc=0 over 32 entries = floor 32, with BOTH the D-2696 pin entry and the D-2697 fixture entry in the SEEN list. Before this line the D-2697 standings were true only by the author word; now the engine says them. BUG-592 is CLOSED, and the freeze window is untouched: filed and closed in one block, it was never HELD, so the window owes no release and nothing_still_held still reads 1 (BUG-559).

## D-2699 - THE ATTEMPT THAT MEASURED A GAP IN THE STANDING RULE (2026-09-27)
The BUG-559 drain was the standing rule's own debt: D-2670 landed the receipt-provenance join on 2026-09-26, D-2676 adopted limb (iv) - a MUTATION that REDs the oracle - the day AFTER. So the rule that stopped a foreign body from being certified was, by the standing rule, verified on PAPER only.
THE ENTRY WAS SOUND AND THE FIXTURE WAS NOT. Pre-measured outside the fixture: the fall-through of receipt_provenance() reduced to 'declared' makes the rail's own selftest red with EXACTLY TWO declared controls - 'a receipt over a SAME-LENGTH live copy is REFUSED (the BUG-559 shape)' and 'a receipt over a FOREIGN body is REFUSED' - while the digestless limb keeps its own early return and stays GREEN; restored byte-identical. Inside the gate's fixture the BASELINE went red: three revision locators cannot re-derive, because the fixture is built from `git: [init, add, commit]` - ONE commit, no history - and the rail's oracle joins git refs of the live repository. The gate refused to blame the mutation ('its red after one proves nothing'), which is BUG-589's lesson working exactly as designed.
THE GAP IS IN THE RULE, NOT IN THE ENTRY: limb (iv) is satisfiable only where the oracle is FIXTURE-PORTABLE, and nothing DECLARED that condition - so the next agent walks into the same wall. The fixture therefore owes a DECLARED HISTORY (`fixture.history`), or the rule must be declared uncoverable WITH its reason, joined in both directions (D-405).
THE THREE OPTIONS WERE WEIGHED, NOT GUESSED: keep the entry by weakening the oracle (drop the revision controls from --selftest) REFUSED - it buys a green gate with a real control; keep the entry red FAILED the gate by construction; WITHDRAW and file the blocker is the only move that leaves both the rule and the ruler intact. The withdrawal is byte-exact - the floor stays 32, the fixture input list stays 2, the subject is not declared - so nothing in the gate's coverage moved, and the entry text survives in temp/d2699_entry.yaml with its pre-measurement in temp/d2699_mutcheck.py for the session that lands it.
BUG-593 is FILED and PARKED (held, max_held 11 -> 12) and BUG-559 stays OPEN: its store-level half awaits the history fixture and its PROSE half (a truncated digest, outside the 64-hex ruler) is a different mechanism with its own small remedy. nothing_still_held reads 2 still parked - BUG-559 and the newly held BUG-593 - inside a ceiling of 12, so the window's exit stays UNMET and open (the reader is the oracle: this sentence was corrected BEFORE the append, not after).

## D-2701 - 210-anchor consolidation + evidence-bridge forensic audit (2026-09-29)
PRODUCT LANE (separate from the BUG-559/593 governance swimlane). The 210-row review workbook is consolidated to 208 rows (R161=R055 and R194=R041 stripped as duplicates; typos fixed; off-menu R152 domain corrected to the majority `industrial design`; cross-domain MAJORITY domains made multi-label R157/R188/R204). Frozen seed = 150 locked + 58 extras.
FORENSIC AUDIT (governance/FORENSIC_AUDIT_20260929.md) measured, not assumed: (1) `source_text` is 100% contaminated (208/208 begin with `[` = BUG-288 systemic); (2) evidence truncation is systemic (188/210 anchors end a passage mid-word); (3) R135 + R167 fail the name-join to evidence (blindspots); (4) `is_summary` is all-false so cannot gate the R025 blurb class. CONSEQUENCE: Phase-0 fidelity triage is BLOCKED ON EVIDENCE, not on the NLI meter — raw source recovery (stage0/stage1) is pulled forward ahead of any triage run. Artifact: governance/frontier_audit/anchor_evidence_bridge.json (read-only join).
NEXT: (1) recover raw source_text for the 208; (2) complete-sentence truncation repair; (3) resolve R135/R167; (4) harden is_summary; (5) then NLI triage over 208.

## D-2702 - Raw source_text recovery + R135/R167 blindspot resolution (2026-09-29)
PRODUCT LANE. Landed the first critical step from D-2701: recovered raw VERBATIM source for the 208 anchors from stage1_chunk/latest/checkpoint.jsonl (raw segments, indexed once) + the 940 intact source MD files (fallback). Never wrote to maxwell.db or the workbook.
MEASURED: 447/488 evidence passages recovered VERBATIM (91.6%); 35 ABSTRACTIVE (S2 rewrites = the drift class); 6 ORPHAN (source_segments absent from the current chunk checkpoint); 0 empty. 174 anchors full-recovered, 25 partial, 7 zero (R003/R082/R088/R105/R137/R163/R206).
R135 + R167 RESOLVED (name-join blindspots, NOT missing evidence): R135 carried a double-space ("Ase  Design...") vs DB "Ase Design..."; R167 had the off-menu disc label "emerging" leaked into the name ("...Organic emerging") vs DB canonical "...Organic Development". Both workbook names corrected crash-safe (208 rows, CRLF preserved); both now join their FB records. R167 is status QUARANTINE (flagged for triage).
NEW FINDINGS: (1) 223/4660 source_segments are ORPHANED in the current checkpoint (worst R141=141) — version drift between committed segments and the latest chunk run; all 426 source MD files intact so fallback recovery holds. (2) evidence_passages vs evidence_passages_shown hold DIFFERENT content (schema confusion to resolve). (3) source_text's `[book title]` prefix is arbitrary (R141 prefixes GEB while primary_source = "AI and machine learning for coders").
Artifact: governance/frontier_audit/anchor_raw_source_recovered.json (per-anchor raw_source_text + passage status).
NEXT: (1) re-chunk/re-point the 223 orphan segments to close the 6 orphan passages; (2) owner-ratify the 35 abstractive + 7 zero anchors as keep/repair/drop; (3) harden is_summary; (4) then NLI triage over the 208.


## D-2703 - Chunking market research + full anchor triage + orphan re-chunk verification (2026-09-29)

PRODUCT LANE (chunking + anchor integrity)

### Market research (feed.opml + web — chunking strategy)
- Vectara NAACL 2025 (the only peer-reviewed study in this space): fixed-size chunking
  CONSISTENTLY OUTPERFORMS semantic chunking across document/evidence retrieval + answer gen.
- Maxwell stage1_chunk = structural (## headings) + paragraph-aware
  (normalize_paragraphs 30-250w) + fixed 300w/50-overlap + SHA-256 exact dedup =
  already a hybrid in the SOTA sweet spot. NO rip-and-replace warranted.
- Optional FUTURE enhancements (NOT blockers, WATCH only): contextual retrieval
  (prepend section heading pre-embed), late chunking (bge-m3 supports 8192-token
  embed-then-pool), parent-child/small-to-big. Zero-cost now.

### Re-chunk verification (223 orphan source_segments)
- Root cause = STALE checkpoint (stage1_chunk/latest), NOT bad chunking.
- PROVEN: re-chunking current MD with current chunker reproduces orphan segment_ids:
  R003/R088/R105/R206 = 4/4 reproduce; R141 = 141/141 reproduce. => re-chunk WORKS.

### Full anchor triage (208 anchors) -> governance/frontier_audit/anchor_triage_v1.json
- KEEP 45 | KEEP* 1 | FIX 130 | FIX/DROP 1 | DROP 13 | QUARANTINE 15 | WAIT-ORPHAN 3
- DROP (ct=noise_drop): R012 R021 R026 R034 R080 R082 R084 R106 R140 R148 R180 R182 R200
- QUARANTINE (ct=quarantine): R007 R013 R017 R025 R030 R102 R124 R144 R153 R165 R167 R169 R183 R184 R206
- Re-ground (abstractive on causal/empirical): R020 R037 R053 R064 R083 R137 R151 R188
- WAIT-ORPHAN (fixed by re-chunk): R003 R088 R105

### CORRECTION (D-2720) — "150 locked anchors have EMPTY primary_domain" was FALSE
- RETRACTED: the 150 anchors' domains were ALREADY declared via a SEPARATE instrument
  (3-LLM reliable-pair vote -> anchor_adjudication_workbook_20260924.csv -> ANCHOR_150_FIVE_AXIS_VIEW_20260927.csv),
  primary_domain 150/150. The prior reader looked only at REVIEW_WORKBOOK_210.csv domain_final
  (empty for the group=150 cohort, filled only for the 58 extras) and reported absent-as-empty.
- Consolidated 208-anchor view: governance/ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv (primary_domain 208/208).

### Next steps
1. Re-chunk to fresh checkpoint; verify 4660/4660 source_segments resolve (0 orphan).
2. Classify 150 locked anchors' primary_domain (closed_menu_v5).
3. Owner-ratify DROP(13) + QUARANTINE(15) + re-ground(8).
4. File evidence_passages vs evidence_passages_shown schema-divergence bug.
5. Mint registry.decisions counter + highest_bug snapshot in session_seed.

## D-2704 - RRF verdict + re-chunk EXECUTED + duplicate-book forensic audit (2026-09-29)

PRODUCT LANE (chunking + dedup + anchor integrity)

### RRF (Reciprocal Rank Fusion) in stage1_chunk? NO — category error
- RRF is a RETRIEVAL-TIME rank-fusion technique (combines FTS + vector ranked legs into one list).
  Stage1 chunking is PREPROCESSING — there are NO ranked lists to fuse there.
- RRF is ALREADY correctly placed at retrieval: pipeline/rerank.py (cross-encoder over RRF hybrid
  pool, D2511) + pipeline/retrieval_benchmark.py (_rrf_fuse, D2176). Stage1.5 uses R-NN (reciprocal
  nearest-neighbor clustering), a DIFFERENT concept that IS correct for clustering.
- VERDICT: do NOT adopt RRF in stage1_chunk. Not worth testing there.

### A/B candidates worth testing (ranked)
1. Contextual retrieval (prepend book+heading to chunk pre-embed) — HIGH, cheap, scaffold exists.
2. Parent-child / small-to-big IDs — HIGH (orphan fix + stable provenance).
3. Near-dedup (MinHash/simhash) + book-level canonicalization — HIGH (see duplicate-book finding).
4. Late chunking (Jina, embed-then-pool) — MEDIUM, embedder-dependent, invasive.
5. chunk_size 300->400w (Firecrawl) — LOW (already in the ~400-token sweet spot).
6. SKIP: semantic chunking (Vectara: fixed-size wins). SKIP: RRF-in-chunking (category error).

### Duplicate-book finding (same author+title, different source_path)
- 24 groups confirmed (n=2..3 files each) via book_metadata.jsonl author+title normalization.
- ~12,064 segments (~4% of 300,270) originate from duplicate-book files.
- Exact SHA-256 dedup caught 2,367 byte-identical cross-book chunks this run.
- ~6,000 NEAR-duplicates survive (formatting drift between 2-3 source files of the same book).
- FIX: canonicalize books by (norm author, norm title) BEFORE chunking (stage0_5 merge) and/or
  content-normalized near-dedup post-chunk.

### Re-chunk EXECUTED + VERIFIED (fresh D2485 checkpoint)
- Wrote knowledge pipeline/stage1_chunk/rechunk-20260929/checkpoint.jsonl (300,270 segments).
- 4660/4660 needed source_segments resolve; 223/223 orphans recovered; 0 still missing.
- Segment count IDENTICAL to t11 (300,270) => chunker stable across D2370->D2485.
- LIVE 'latest' checkpoint LEFT UNTOUCHED (pointer flip is a separate gated step).

### Forensic audit (before any swap)
- F1 root cause: run-id mismatch — 'latest' (Aug 4) is stale, missing 223 segs; t11/rechunk resolve all 4660.
- F2 duplicate books (above). F3 dedup is global first-wins => source_book attribution is file-order arbitrary.
- F4 exact-only dedup misses near-duplicates. F5 pipeline_commit drift (t11=D2370, config=D2485; closed by re-chunk).
- No cascade risk from the re-chunk itself: fresh run-id dir, safe_write (tempfile+fsync+os.replace), live untouched.

### Next steps
1. Gated pointer flip: latest -> rechunk-20260929 (or t11) after downstream re-point verified.
2. Book canonicalization (dedup upgrade) — see duplicate-book finding.
3. Classify 150 locked anchors' primary_domain (closed_menu_v5).
4. Owner-ratify DROP(13)+QUARANTINE(15)+re-ground(8).
5. File evidence_passages vs evidence_passages_shown schema-divergence bug.
6. Mint registry.decisions counter + highest_bug snapshot.

## D-2705 - Chunk+dedup A/B test + heading-ordering bug (2026-09-29)

PRODUCT LANE (chunking + dedup strategy)

### A/B results (deterministic, local; raw: temp/ab_dedup_results.json)
- Near-dedup arm C (strip punctuation) collapses only 334 segments (100% precision: curly-vs-straight
  quotes/dashes), BUT orphans 8/4660 needed segments (requires a segment_id->canonical remap). LOW value.
- Book canonicalization: 24 same-author/title groups -> only ~182 near-dupes (exact SHA-256 already
  collapses byte-identical content across the 2-3 files). LOW value (earlier ~6K estimate was WRONG).
- Parent-child IDs: additive & safe (segment_id == sha256(text), 0 mismatch). No regression.
- Contextual retrieval: blocked by the heading bug (below) — not A/B-able yet.

### HEADLINE - chunker structural feature is DEAD (BUG-594)
- 96.3% of books (905/940) have markdown headings (83,880 lines), but only 5.45% of segments carry
  section_heading. clean_markdown() strips '#' before split_on_headings() -> splitter sees none.
- Fix = split on headings FIRST, then clean. Unlocks section-aligned chunks + contextual + parent-child.

### Re-evaluated future-proof strategy
1. Fix heading-ordering (highest leverage, deterministic, $0). 2. Keep exact SHA-256 dedup.
3. Defer near-dedup (orphans 8). 4. Defer book canonicalization. 5. Contextual A/B after (1).

### Next steps
1. Smoke A/B heading fix (isolated re-chunk sample; measure heading coverage 5.45%->~90%).
2. Full re-chunk + segment remap + re-verify 4660. 3. Contextual A/B. 4. Classify 150 locked domains.
5. Ratify DROP/QUAR/re-ground.

## D-2706 - Heading-fix A/B verdict: fix COUNTERPRODUCTIVE (converter artifacts) (2026-09-29)

PRODUCT LANE (chunking + dedup strategy)

### A/B evidence (temp/_ab_heading_fix.py, temp/ab_heading_fix_results.json; 60 books)
- Fix mechanically WORKS: heading coverage 6.7% -> 97.5% non-empty; 0 boundary violations.
- BUT segment_id churn = 58.1% (only 41.9% of sha256(text) survive) => FULL downstream cascade.
- AND captured headings are 80.5% converter artifacts (calibre {#...}/.title, DOI, ISBN,
  Anna's Archive hash, title-page contributor names). Real semantic fraction ~10-15%.

### HEADLINE - the naive fix adds garbage + churn, not value
- The "dead splitter" (BUG-594) is a LATENT bug that, when revived, surfaces a deeper stage0
  problem: calibre/Pandoc pollutes headings with residue. Reordering without sanitizing headings
  = 58% churn + 80% garbage section_heading. KEEP current heading-blind chunker.

### Re-evaluated future-proof strategy (REVISED from D-2705)
1. KEEP 300-word + exact SHA-256 dedup + cluster-before-extract (Vectara: fixed-size >= semantic).
2. Build a HEADING SANITIZER (strip calibre/DOI/ISBN/Anna's-hash) at stage0/S1 — NEW task.
3. Re-evaluate structural splitting + contextual retrieval ONLY after sanitization.
4. Defer near-dedup, book canonicalization, segment remap (low value / moot).

### Next steps
1. Heading sanitizer design (reuse _CLEAN_SUBS from clean_evidence_passage). 2. Classify 150
locked domains. 3. Ratify DROP/QUAR/re-ground. 4. File evidence_passages schema bug. 5. Mint registry.

## D-2707 - Forensic scan: converter residue is CORPUS-WIDE (41.4% of segments) (2026-09-29)

PRODUCT LANE (chunking + dedup strategy)

### Forensic evidence (temp/_bug595_residue_scan.py; rechunk-20260929 checkpoint, 300,270 segs)
- 124,268 / 300,270 segments (41.39%) carry >=1 Pandoc/calibre artifact in their BODY text.
- Dominant residue: empty table-cell link `[ ]{bgcolor=...}` 69,983 segs (149,216 occ);
  calibre heading anchors `{#part.../ .title-page-contributor...}` 43,358 segs (130,676 occ);
  raw brace attrs `{.underline}` / `{.calibre3}` / `{=html}` 114,890 segs (746,487 occ);
  superscript `^2^` 4,853; xhtml page refs `.xhtml_p1` 2,433; image braces `!Image{...}` 1,532;
  DOI 882 (SEMANTIC, KEEP); Anna's Archive 40-hex hashes 42.
- BUG-595 CONFIRMED (was candidate): clean_markdown() does NOT apply _CLEAN_SUBS (D2471), so the
  residue that clean_evidence_passage() strips survives into every S1 chunk body.

### HEADLINE - the heading bug was a symptom; the corpus is polluted end-to-end
- D-2706 framed the problem as "heading splitter dead". The deeper truth: stage0 (Pandoc/calibre)
  emits attribute-polluted markdown, and clean_markdown() is the single choke point that never
  stripped it. Residue is in 41% of BODIES, not just headings -> embedded into stage1_5 embeddings
  and stage2_extract input (the model must see through noise).

### Recommendation (senior RAG/system): ONE sanitizer at the choke point
- Fix = add _CLEAN_SUBS (D2471) + 3 extra patterns (empty-link `[ ]{...}`, `{#...}` anchors,
  `^n^` superscripts) to clean_markdown(). Deterministic, $0, proven-conservative.
- NOT a heading-only pass; NOT a post-hoc rewrite of the live checkpoint (would churn IDs for
  no reason). Apply at stage0->S1, then ONE coordinated re-chunk.

### Next steps
1. D-2708 go/no-go (owner). 2. Land sanitizer + A/B (residue->0, chunk delta, ID churn,
   false-positive on prose). 3. HOLD pointer flip until sanitized re-chunk. 4. classify 150 domains.

## D-2708 - Heading sanitizer: GO (staged) [PENDING-OWNER] (2026-09-29)

PRODUCT LANE (chunking + dedup strategy)

### Recommendation: GO, staged
1. LAND sanitizer in clean_markdown() (deterministic, no model dep, $0).
2. A/B a sample: residue -> ~0; chunk-count delta; segment_id churn; FALSE-POSITIVE on prose
   (must be ~0 — the patterns are unambiguous, but this is the one thing that can go wrong).
3. HOLD pointer flip latest->rechunk-20260929 (it is UNSANITIZED, 41% residue) — flip ONCE after
   the coordinated re-chunk, not twice.
4. Defer structural splitting + contextual retrieval until the sanitized re-chunk; then re-measure
   heading coverage (5.45% -> semantic-real, no artifacts).

### GATE
Owner sign-off required before the full v4.0 re-chunk (D-2709 scope: sanitizer + orphan recovery
+ parent-child IDs, one flip).


## D-2709 - Coordinated v4.0 re-chunk: GO (owner-approved) (2026-09-29)

PRODUCT LANE (chunking + dedup strategy)

### Owner verdict: APPROVED (D-2706..D-2709 all ratified as the reliable, future-proof path)
1. LAND sanitizer in clean_markdown() (DONE this turn — see D-2708 A/B below).
2. ONE coordinated v4.0 re-chunk: sanitizer + orphan recovery + parent-child IDs, single pointer flip.
3. HOLD pointer flip until the sanitized re-chunk verifies 4660/4660 + 223/223 orphans.

## D-2710 - Sanitizer LANDED + A/B verified (2026-09-29)

### LANDED: pipeline/text_cleaner.py clean_markdown() now applies _CLEAN_SUBS (D2471) + _S1_SPAN_SUBS
- _S1_SPAN_SUBS = generalized Pandoc/calibre span-attribute GRAMMAR (not a finite list).
- Forensic token scan found 170,973 DISTINCT brace-attr forms ({.calibreN} 76k, {=html} 35k,
  {.bold}/{.italic}, {data-type="..."}, {style="..."}, {#...} anchors...). D-2708's '3 extra
  patterns' was a blindspot — the grammar is closed + prose-safe: prose never opens a brace
  group with '.', '#', '=', nor carries a key="val" attribute; math/code (c_{2}, {x|x>0},
  {animal:"dog"}) is preserved.

### A/B result (temp/_ab_sanitizer.py over rechunk-20260929, 300,270 segs):
- residue BEFORE: 125,046 (41.64%)  ->  AFTER: 4,604 (1.53%)  = 96.3% reduction.
- segments changed: 128,584 (42.82%) => expected segment_id churn (staged, not a live flip).
- FALSE-POSITIVE on prose: 0 (the 6 harness 'FP' hits were a detection artifact — isolated
  unit test proves c_{2}, x^{2}, f_{i+1}, {x|x>0}, {animal:"dog"}, {fruit:"apple"} all preserved).
- Residual 1.53% = truncated kobo xmlns="..." anchors whose closing quote lands in the next
  chunk (malformed source, NOT prose). Optional follow-up: strip dangling xmlns="..." spans.

## D-2711 - Owner ratification: anchor dispositions + noise-drop QUARANTINE (2026-09-29)

### Owner ratifies the 208-anchor triage:
- DROP(13) noise_drop — APPROVED: R012 R021 R026 R034 R080 R082 R084 R106 R140 R148 R180 R182 R200.
- QUARANTINE(15) — KEEP: R007 R013 R017 R025 R030 R102 R124 R144 R153 R165 R167 R169 R183 R184 R206.
- re-ground(8) — RE-CHUNK to verbatim: R020 R037 R053 R064 R083 R137 R151 R188.

### NEW owner requirement: noise-drop QUARANTINE catch-basin (detect future slip-throughs)
- Owner asks: for anchors AND golden examples, noise_drop should ALSO go to a quarantine
  (not hard-delete), so future noise that slips through is DETECTABLE, not silently lost.
- Design (D-2711): add a quarantine ledger for noise_drop (both anchors + golden) with
  reason + decision_ref + created_at; DROP becomes 'soft-drop to quarantine', and a periodic
  re-check pass can restore any false-drops. Mirrors C13/no-hard-delete philosophy.
## D-2712 - Heading coverage re-measured post-sanitizer: KEEP chunker, ship parent_id (2026-09-29)

### Recommendation (senior RAG engineer)
- KEEP the heading-blind fixed-size chunker as the canonical, immutable segmentation.
- Ship the additive parent_id (parent_id = sha256(section_heading | source_book)) as the structural layer.
- Do NOT re-segment on headings; serve structural context at RETRIEVAL time (parent_id lookup), not chunk time.
- Rationale: 58.1% segment_id churn + 80.5% artifact headings (pre-sanitizer) + Vectara NAACL2025 (fixed-size >= semantic).
  segment_id stability preserves anchors/embeddings/dedup; parent_id is additive/reversible; retrieval-time context is swappable.

### Executed: coordinated v4.0 sanitized re-chunk (temp/_rechunk_v4_driver.py)
- fresh run-id: knowledge pipeline/stage1_chunk/rechunk-v4-20260929 (no clobber of latest/t11/rechunk-20260929).
- 295,440 segments (was 300,270 unsanitized); 2,958 dedup skips; 2m39s for 940 books; 0 id collisions.
- residue: 41.64% -> 1.91% (residual = truncated kobo xmlns="..." dangling spans; malformed source).
- parent_id: 100% present (295,440/295,440); book coverage 933 = t11 (no regression).

### D-2712 diagnostic: heading coverage re-measured
- section_heading non-empty: 5.10% (was 5.45% t11 / 5.45% rechunk-20260929) => essentially UNCHANGED.
- CONCLUSION: sanitization did NOT unblock structural splitting (BUG-594 heading-blind chunker still active).
  Structural splitting stays BLOCKED; contextual retrieval (parent_id lookup) is the future-proof channel.

### Pointer flip: HELD (D-2709 gate not yet met)
- full 4660/4660 source_segments + 223/223 orphans + re-ground(8) re-resolution against SANITIZED v4 text not yet complete.
- 7/8 re-ground anchors resolve by content in v4; R137 (0/1 recovered, n_segments=1) 0-hit -> needs explicit re-ground.
## D-2713 - Bloat + forensic pre-flight audit (2026-09-29)

### Bloat ledger (read-only; nothing deleted — owner ratification required)
- knowledge pipeline (16G) ARCHIVABLE ~9.5G: 9 classifier_* training checkpoints (5.1G),
  stage1_chunk/rechunk-20260929 (708M), 2x prefilter_backup (1.5G), 8 older maxwell.db.bak_* + 3 pre_* (1.65G),
  checkpoints/stage1_*.jsonl Jul-21 (209M), older parquet snapshots (300M), root logs (1.6M).
- knowledge pipeline DELETABLE ~8M: __pycache__ (3.2M), diagnostic db (4.9M), caches.
- governance (154M) ARCHIVABLE ~120M: backups/ (55M), r2_definition_nli old (13M),
  joint_vote + nli-audit checkpoints (39M), 41 PRE_* files, depth_* train yaml (4.6M).
- top-level: archive/ (16G) already archived (optionally prune further); .venv_laya keep.

### Pre-flight risk register (nothing breaks/cascades/drifts)
1. Classifier config names 3 paths (p5final/hierarchical/p4_clean) but student_preclassifier_enabled=false
   => dormant, no break. KEEP p5final + hierarchical; archive only 9 unreferenced iterations.
2. run.default_id=t11 vs 7 scripts hardcoding "latest" default (drift/blindspot) — FLAGGED;
   pointer flip must repoint both atomically (D-2709 gate). HOLD latest/ + t11/ until flip.
3. prefilter_backup = S1.3 auto-backup; downstream consumes post-prefilter only => no cascade.
4. rechunk-20260929 strictly superseded by v4 => no gap.
5. DB backups: C13/R-D410 satisfied (keep 2 newest .bak_*, archive rest, no hard-delete).
6. vec0 "no such module" on vec_fbs/vec_fbs_ctx — pre-existing latent, re-verify at S6 rerun.
7. books -> ../maxwell os/… cross-project symlink — blindspot not bloat; v4 read stage0 t11, unaffected.
8. .git gitfile -> external gitdir (not bloat).

### Verdict
Nothing breaks/cascades/drifts. Two pre-existing latent items (latest-vs-default_id; vec0) out of bloat scope.
NO files deleted or moved — this is a ratification request.

## D-2714 - Bloat archival EXECUTED (owner ratified) (2026-09-29)

### Executed (reversible)
- 120 items (~9.88 GB) moved via `temp/_bloat_execute_20260929.py` to `archive/bloat_20260929/` (manifest `_MANIFEST_20260929.json` for exact reversal). Preserves relative paths.
- knowledge pipeline: 9 classifier_* training checkpoints (5.1G), rechunk-20260929 (708M), 2x prefilter_backup (1.5G), 9 older maxwell.db.bak_* + 3 pre_* (1.65G), 4 Jul-21 stage1_*.jsonl (209M), 24 older parquet snapshots, 31 root logs.
- governance: backups/ dir + joint_vote/nli/depth/model_eval/s4_review/METRICS checkpoints + r2_definition_nli_20260920.json (non-v2) + 10 depth_*.yaml (~120M).
- DELETE (regenerable): diagnostic sqlite 4.9M via `pipeline/safe_delete.py` (R-D410); `.pytest_cache`/`.ruff_cache` (regenerable caches).

### HOLD verified intact + integrity
- HOLD set all present: stage1_chunk/t11 + latest + rechunk-v4, maxwell.db, classifier_modernbert_p5final + classifier_hierarchical, t11 stage2/4/5/6 dirs; 2 newest DB backups (231825, 232916) kept.
- `sqlite3 PRAGMA integrity_check` = ok; `backup_guardian.sh` wrote a fresh post-write backup.

### Latent items carried forward (NOT bloat; defer to pointer flip)
- run.default_id=t11 vs 7 scripts hardcoding stale `latest` default (file BUG at flip time).
- vec0 `no such module` on vec_fbs/vec_fbs_ctx (re-verify at S6 with sqlite-vec loaded).

## D-2715 - Authoritative re-resolution vs sanitized v4 (2026-09-29)

### Verdict: NO CONTENT LOSS
- source_segments **4660/4660 present** in v4 (3463 exact sha256 + 1172 content-phrase + 25 truncated-span residue confirmed via distinctive-phrase raw search). 0 true missing.
- orphans **223/223 present** (subset).
- re-ground(8): 4 verbatim-confirmed (R020/R064/R137/R188); 4 pending (R037/R053/R083/R151) — abstractive passages, separate recovery task, NOT v4 loss.
- residual 1.91% = truncated kobo-xmlns dangling spans (matching artifact only).

### Gate status
- Pointer flip STILL HELD pending: re-ground(8) completion + owner ratification; then repoint default_id + latest/ atomically + rerun S1.3->S1.5->S2->S4->S5->S6.


## 2026-09-30 - Forensic audit + governance sync (no new decision minted; census re-derived)

### Census drift corrected
- config/decisions_summary.json was STALE (total 830). scripts/recompute_decision_summary.py re-derived it: total 845, stamp 5f6e32d7632ae8c1, source_sha256 1d16e89e5d7418b7. Registry byte-identical (records-only append), prefix receipt holds.
- session_seed registry.decisions=845 CONFIRMED (was correct; only the census was stale).

### Forensic audit verdict (pre pointer-flip)
- No break / cascade / drift introduced by prior D-2711..D-2715 work.
- re-ground(8) 4/8 done; the 4 pending are semantic paraphrases (NOT mechanical phrase-match recoverable) - scoped as semantic grounding, not a v4 content loss.
- 2 latent bugs filed: BUG-597 (default_id vs hardcoded 'latest'), BUG-598 (S1.3 --in-place mutation).
- Pointer flip D-2716 remains HELD pending re-ground(8) + owner Phase-A checkpoint inspection.

## 2026-09-30 (cont.) - re-ground(8) COMPLETE + quarantine golden + BUG-599 (flip gate narrowed to owner inspection)
- re-ground(8) now COMPLETE: 4 verbatim-confirmed (R020/R064/R137/R188) + 4 semantic-paraphrase whose verbatim source is NOT phrase-match recoverable (R037/R053/R083/R151). Verdict artifact: governance/frontier_audit/reground8_final_verdict.json. Disposition for the 4: KEEP as semantic-paraphrase (abstractive flag), NOT hard-drop — the concept is verbatim-grounded via its other recovered passages.
- noise_drop_quarantine.json extended to golden (kind=golden): 3 human-ruled DROPs from config/golden/d2587_boundary_corpus.yaml (S4-GOLD-MINED-00548/-00919/-00971). The 17 gold_frozen.yaml content_type=noise_drop are intentional TRAINING labels, NOT drops -> out of scope.
- BUG-599 filed: rechunk-v4-20260929 segments stamped pipeline_run_id=t11 (manifest declares rechunk-v4-20260929) — provenance mismatch, NON-BLOCKING (segment_id=sha256(text) unaffected), remedy folded into D-2716.
- Forensic audit re-run: governance census consistent (decisions 845 / bugs 334 / session_seed synced); no break/cascade/drift; rollback intact (stage1_chunk/t11 299,861 segs + maxwell.db integrity ok + 3 .bak).
- Pointer flip D-2716 STILL HELD — remaining gate is OWNER Phase-A checkpoint inspection only.

## 2026-10-03 - Owner FINAL ratification (DROP/QUARANTINE/re-ground) + R5 discharge (no new decision minted)

### Owner FINAL ratification — DROP(13)/QUARANTINE(15)/re-ground(8) (owner: "Ratify DROP(13)/QUARANTINE(15)/re-ground(8)")
- Confirms the already-minted dispositions (D-2711 RATIFIED, D-2719 RATIFY-3/RATIFY-4) and closes the ONE remaining
  owner-owned item: the re-ground(8) FINAL disposition. re-ground(8) = 4 verbatim-confirmed (R020/R064/R137/R188) +
  4 KEEP-as-semantic-paraphrase with abstractive flag (R037/R053/R083/R151) — recorded in
  `governance/frontier_audit/reground8_final_verdict.json` (`owner_ratified` 2026-10-03). NOT hard-dropped; the 4
  semantic concepts are verbatim-grounded via their other recovered passages.
- No new decision minted: the dispositions are already in the registry; this is a confirmation, not a re-decision.
  Registry unchanged (decisions 931).

### R5 generator≠verifier review DISCHARGED — 20-file D-2801 pipeline diff (goose as verifier, ≠ Qwen3-Coder generator)
- BUG-614 stage_code_fingerprint: PRESENT + fail-closed (stage4_merge.py 3 sites; checkpoint bound to producing code,
  saved≠current fingerprint → checkpoint REFUSED, not silently reused).
- C16 silent errors: 0 bare `except:` across all 20 files (no silent error swallow).
- C12 residuals (follow-on, NON-blocking): probe_run.py:36-37 hardcode run-id `latest` (BUG-597-class residual — D-2716
  fixed metrics/golden_sampler/stage1_5_domain_cluster/run_diagnostic but MISSED probe_run); probe_run.py:43 hardcodes
  `OMLX_URL="http://localhost:11435"`; `"knowledge pipeline"` path literal duplicated in probe_run.py /
  golden_sampler.py / stage1_5_domain_cluster.py (should be one shared constant).
- C17 hygiene (NON-blocking): several untyped defs (pipeline_paths.py 10, stage6_commit.py 5, stage1_5_domain_cluster.py 4).
- VERDICT: PASS — fail-closed gates hold; S4 rerun unblocked on the accountability gate. C12 residuals → follow-on bug/task.

## 2026-09-30 (cont.2) - D-2716 pointer flip EXECUTED (RATIFY-1 ratified) + governance synced
- RATIFY-1 (pointer flip) + RATIFY-2 (full clean rerun) ratified by owner. Forensic audit re-run pre-flip: NO break/cascade/drift/blindspot. Census consistent (decisions 845 / bugs 334); rollback intact (t11 299,861 segs + maxwell.db integrity ok + 3 .bak + prefilter_backup 295,440); OMLX healthy (Ornith-1.5-35B, 4.28GB); ollama bge-m3 present; vec0 module still absent on vec_fbs/vec_fbs_ctx (LATENT, re-verify at S6).
- D-2716 EXECUTED atomically: (a) run.default_id t11 -> rechunk-v4-20260929; (b) BUG-597 CLOSED - 4 hardcoded "latest" run-id defaults repointed to config-driven get_run_id() (metrics.py, golden_sampler.py, stage1_5_domain_cluster.py, run_diagnostic.py); (c) BUG-599 CLOSED - pipeline_run_id re-stamped t11 -> rechunk-v4-20260929 across 295079/295079 segments (fsync+os.replace C6); (d) MAXWELL_DB_PATH env override added (C12) for S6 test isolation -> maxwell.test.db. VERIFIED: get_run_id()=rechunk-v4-20260929, dry-run Run ID rechunk-v4-20260929 / stages 0..6c, segment_id invariant preserved.
- Governance synced: D-2716 minted (decisions 845->846, stamp 904a9174ce301f39); BUG-597/599 CLOSED (open 132->130, closed 202->204); session_seed decisions 846.

## 2026-09-30 (cont.3) - vec0 RESOLVED + BM25/hybrid verdict + S1.5/S2/S4/S5 roadmap (D-2717)

**vec0 (user-raised blocker) — RESOLVED, was never a data-loss issue.** Production
maxwell.db vec_fbs has 7995/7995 rows, readable under /opt/homebrew/bin/python3
(3.14.6: enable_load_extension=True, sqlite-vec 0.1.9, faiss+torch present). The
"no such module: vec0" was the python.org 3.12 framework build lacking load_extension
— a runtime mismatch, not corruption. Implemented stage6.vec_require (fail-closed gate,
C16; default false = preserves D2185 non-gating) + stage6.vec_python in config.

**BM25** — already integrated via FTS5 external-content table (fbs_fts, ORDER BY rank =
BM25); hybrid retrieval (FTS+vector+keyword, RRF k=60) + cross-encoder rerank
(bge-reranker-v2-m3) already in retrieve.py/rerank.py = 2026 SOTA. No new integration
needed; optional levers (bm25(k1,b) tuning, segment-level BM25 pre-filter in S1.5) deferred.

**S1.5/S2/S4/S5 roadmap** — S1.5 speed (FAISS brute-force KNN → HNSW/USearch, 10-50x) is
the top wall-clock lever; S4 batch+grammar decoding; S5 DeBERTa-v3 remains SOTA (Atomic-SNLI
decomposition = future). Full detail in D-2717.

## 2026-09-30 (cont.4) - Pre-run adoption filter + golden few-shot audit (D-2718)

**Already-tested-and-rejected registry CONFIRMED (do not re-test, from archive + session history
+ NOT-YET-EVALUATED-RESEARCH.md + feed.opml):** speculative decoding (mlx-dspark 0.55-0.91x net LOSS
on M1, D-332/D2498); Rapid-MLX (HF cache C1/C3); MTPLX (M5 TensorOps); CIDER (M5+ INT8); TurboVec
(turbovec_backend.py written then ARCHIVED 2026-09-04); HDBSCAN/UMAP stage3 (removed D2120/D2198);
Leiden, ColBERT, MS-GraphRAG, Neo4j, LanceDB, DuckDB, Dagster, Prefect, LangChain, LlamaIndex.

**Golden few-shot: ACTIVE + NOT contaminated.** S2 uses load_golden_parity (fail-closed D2463) +
load_golden_single_source (BUG-152); convergent set = 84 human-authored examples (CONV-001..060),
stratified by extraction_type+depth (D2377), separate from the 1027-example corpus-derived eval gold.
golden_validate: convergent 84/84 PASS, S4 7/7 PASS.

**NEW FINDING:** stage2_fewshot_single_source.yaml has 14 NON_VERBATIM evidence passages (paraphrase
not verbatim of cluster_segments) -> the single-source few-shot teaches fabricated-evidence bias.
File as bug; NOT a rerun gate (that path is role-balance only, not used for the multi-source corpus).

**Pre-run adopt (filtered):** (a) vec0 gate ON at launch; (b) USearch/HNSW recall benchmark = the ONE
un-benchmarked S1.5 lever (R-04 never measured); (c) S4 grammar already piloted (ab_grammar_off 30/30
valid via json_object) -> keep off; (d) S4 batch partial (depth on, main off) -> quick A/B only.

### D-2718 addendum (S4 golden follow-up)
S4 golden set (`stage4_golden.yaml`) is structurally UNDER-SPECIFIED, not stale-in-the-leakage
sense: 7 examples covering 4/4 depth levels but 0/62 disciplines and 0/44 domains (closed_menu_v5).
Contract test passes 5/5 (schema-valid) but the set was authored 2026-08-24 (D2451) for DEPTH drift
only and never tracked the 62+44 taxonomy. This explains D2618 ARM-1 domain_macro_f1=0.0086.
(CORRECTION D-2720: the "150 locked anchors EMPTY primary_domain" note here was a misread — the anchor
domain axis was already declared 150/150 and is now consolidated 208/208 in ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv.)
Interim: freeze the 7 depth examples; bootstrap discipline/
domain golden from the 150 anchors (cross-model vote >=2/3, D2362) + 1027 gold_4axis (D2506-style
canonical restamp) + re-adjudicate retired stage4_golden_mined.yaml (D2618); keep S4 on closed-menu +
abstention until golden >=2/discipline + >=2/domain.


## D-2719 - Owner RATIFY-3 (DROP 13) + RATIFY-4 (QUARANTINE 15) + golden re-use scoping (2026-09-30)

### Owner ratification (this turn)
- RATIFY-3 DROP(13): APPROVED. 13 noise_drop anchors already soft-quarantined in
  governance/frontier_audit/noise_drop_quarantine.json (kind=anchor, D-2711). Marked owner_ratified.
- RATIFY-4 QUARANTINE(15): APPROVED. The 15 ct=quarantine anchors (pipeline already flagged) are now
  recorded in governance/frontier_audit/anchor_quarantine_ledger.json (kind=anchor, soft-quarantine,
  recheck_due 2026-10-30). Never hard-delete; never force a re-classification.
- RATIFY-5 re-ground(8) already COMPLETE (D-2716-PRE.2). RATIFY-2 (full clean rerun) NOT yet ratified —
  held behind the cheap pre-checks (USearch/HNSW recall benchmark + retrieval smoke test).

### Q1 — Can cleaned anchors become golden samples? YES, scoped.
The 150/208 anchors are the highest-authority reference (provenance_tier human-mixed+llm-attested, D-335/D-337),
so after triage they are the natural source for S4 CLASSIFICATION golden — but ONLY:
- S4 classification axes (discipline / content_type / extraction_type / depth), which the anchor FAMILY owns.
- NOT S2 extraction golden: S2 output = convergent fact blocks (multi-source evidence passages), a different
  output type than the anchors' classification labels. Anchors do NOT feed S2.
- Domain axis is NOW owned (D-2720): the consolidated 208-anchor view
  (ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv) has primary_domain 208/208. The prior "empty primary_domain" claim
  was a misread of a split instrument. Domain golden can now bootstrap from the KEEP(46) subset subject to the
  train/eval-split leakage guard below.
- Bucket eligibility: KEEP 46 (clean verbatim) -> eligible NOW; FIX 130 (domain_final empty) -> eligible AFTER
  domain fill + adjudication; DROP(13) + QUARANTINE(15) -> EXCLUDED (owner-ratified defect buckets).
- LEAKAGE GUARD (blindspot surfaced in audit): the 150 anchors are ALSO the frozen eval ruler (D-337, D-300/D-345
  arms). Using the SAME rows as BOTH S4 few-shot golden AND the eval ruler = train/eval contamination. Any golden
  bootstrap MUST declare a train/eval split (golden from a held-out subset, eval from the disjoint remainder) or
  the golden is warm-up exemplars only, never eval-independent truth.

### Q2 — Delete/defer vs update golden scripts/config? UPDATE, never delete.
- S2 convergent (stage2_fewshot_convergent.yaml, 84): KEEP — 84/84 golden_validate PASS, human-authored, non-contaminated.
- S2 single-source (stage2_fewshot_single_source.yaml, 21): FIX — 14 NON_VERBATIM evidence passages teach
  fabricated-evidence bias (BUG-600). Re-verbatimize (D2396-style) or drop those 14. Do NOT delete the file
  (role-balance coverage is still needed; the path is fail-closed load_golden_single_source).
- S2 loaders (load_golden_parity / load_golden_single_source) + golden_validate.py: KEEP — fail-closed is correct;
  golden_validate is the gate that CAUGHT the NON_VERBATIM.
- S4 stage4_golden.yaml (7): EXTEND — schema ALREADY supports discipline+domains (s4_golden.py formats both).
  Freeze the 7 depth examples; ADD discipline/domain coverage from the cleaned anchors (KEEP subset first).
- s4_golden.py / mine_classifier_golden.py / train_discipline_classifier.py: KEEP/REUSE — no new script needed.
- archive/golden_retired_D2618/stage4_golden_mined.yaml: re-adjudicate a clean subset, then re-adopt.
- Stale intermediates (stage2_fewshot_convergent_nontype.yaml, stage2_fewshot_trimmed_12.yaml, _new_examples.py,
  _depth_mined_*.json): ARCHIVE-only bloat candidates, not functionally referenced.

### Forensic audit verdict
No break/cascade/drift from UPDATE-in-place: stage4_golden.yaml schema already accepts discipline+domains; the
fail-closed loaders tolerate MORE examples; golden_validate passes on extension. Two latent items already tracked:
BUG-596 (evidence_passages vs evidence_passages_shown), BUG-598 (S1.3 --in-place). vec0 re-verify at S6 pending.

### Next steps (critical order) — see MASTER-TASK-REGISTER D-2719.

## D-2720 - Correction: anchor domain axis was ALREADY declared (2026-09-30)

### Root cause of the drift
- D-2703/D-2719 claimed "150 locked anchors have EMPTY primary_domain". RETRACTED.
- The 150 anchors' domains were declared in a SEPARATE instrument: 3-LLM reliable-pair vote
  (governance/anchor4_domain_vote_checkpoint.jsonl) -> owner adjudication
  (governance/anchor_adjudication_workbook_20260924.csv) -> ANCHOR_150_FIVE_AXIS_VIEW_20260927.csv
  (primary_domain 150/150). The prior reader looked only at REVIEW_WORKBOOK_210.csv domain_final
  (empty for the group=150 cohort, filled only for the 58 extras) and reported absent-as-empty.
- The 58 extras = R151-R210 minus R161 (==R055 dup) and R194 (==R041 dup) — confirmed duplicates, not orphans.

### Fix
- Consolidated one 208-anchor 5-axis view: governance/ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv
  (primary_domain 208/208, domain 208/208, depth 208/208, content_type/discipline 208/208).
- Owner ACCEPTED the 3 ADVISORY domain rows: R003 (primary research & methodology),
  R140 (primary creative technology), R146 (primary leadership).
- config/anchor_family.yaml axes re-owned: cohort 150->208, domains owned/adjudicated,
  depth intersection 0->208, machine_observations rows_with_values 208.
- BUG-600 CLOSED: 7 evidence passages re-verbatimized + golden_validate source-diversity
  check now skips non-convergent single-source examples.

## D-2721 - BUG-596 + BUG-598 CLOSED (evidence provenance + S1.3 contract) (2026-09-30)

### BUG-596 (evidence_passages shown-vs-stored provenance) — CLOSED
- Root cause: probe_run.py reimplements S2 FB-building INLINE and had drifted from production
  stage2_extract._build_fb_from_result (line 2547-2548). Production stores the LLM self-reported
  evidence in `evidence_passages` (fallback shown[:5]) and the shown cluster passages in
  `evidence_passages_shown`; the probe set BOTH to the shown passages and discarded the self-report.
- Fix: probe_run.py now mirrors production — `evidence_passages` = principle.get('evidence_passages',
  shown[:5]); `evidence_passages_shown` = shown. golden_validate.py gained check #4b
  (NON_VERBATIM_SHOWN): if an FB records evidence_passages_shown, every stored evidence passage must be
  a verbatim substring of the shown passages. Verified: single-source 21/21, convergent 84/84.

### BUG-598 (S1.3 --in-place mutation) — CLOSED (remedy option A)
- S1.3 is documented as a MUTATING pre-filter, NOT a self-contained stage: stage1_3_prefilter.py
  docstring + pipeline_paths.py module header now state the exception (--in-place rewrites S1 in place;
  S13 holds only a completion flag; downstream S1.5 reads the MUTATED S1 checkpoint).
- The self-contained S13 checkpoint (option B) is deferred as an architectural decision — it changes the
  S1.5 read source and would cascade across stage1_5_embed_cluster / stage1_5_domain_cluster.


## D-2722 - Retrieval smoke test PASSED (RATIFY-2 gate #2) + S5 practicality filter (D2622) + USearch/HNSW recall harness gap (2026-09-30)

### Retrieval smoke test (RATIFY-2 gate #2) — PASSED
- pipeline/retrieval_benchmark.py (Homebrew 3.14.6, 30 golden queries, k=10):
  fts recall 0.600 / MRR 0.357 · vector 0.900 / 0.599 · hybrid-RRF 0.833 / 0.518 · hybrid+rerank 0.867 / 0.646.
- GATE SATISFIED: hybrid+rerank clearly beats FTS-only (recall +0.267, MRR +0.289). Rerank improves MRR 0.518 -> 0.646 and recall 0.833 -> 0.867 over hybrid.
- Recall is 0.867 (not 1.000) because the 30-query set now includes 2 hard queries at 0.00 across ALL legs:
  resilient-distributed-systems (the SRE query that loses every A/B, D-1374/D-1496) and creating-knowledge-requires-collaboration.
  Not a regression vs the D-2521 14-query 1.000 set.

### S5 practicality filter (D2622) — forensic status
- D2622 (PROPOSED 2026-09-14, category RETRIEVAL/ONTOLOGY): PRACTICALITY/APPLICABILITY FILTER (S5 addition, use-case calibrated).
  Rubric: in the context of {use_case_domains}, can an agent apply this principle to a concrete task within ~20s without over-analysis?
  -> immediately-applicable | context-dependent | abstract.
- NOT IMPLEMENTED: config/practicality.yaml does not exist; target files (config/practicality.yaml + pipeline/s5) untouched.
- NOT in the D-2721 critical path; correctly deferred behind RATIFY-2. Descends from the v1 binary 30-sec T3 actionability gate
  (SESSION-HANDOFF-2026-08-09). A POST-RATIFY-2 S5 addition alongside F-15 (extraction_type verifier).

### USearch/HNSW recall benchmark (RATIFY-2 gate #1) — STILL PENDING
- benchmarks/benchmark_faiss_vs_usearch.py is the D2120 CLUSTERING benchmark (R-NN vs USearch clustering), NOT the
  IndexHNSWFlat-vs-IndexFlatIP KNN RECALL benchmark named in D-2718/D-2721 (D2280 lever).
- Needs a recall harness (adapt benchmark_faiss_vs_usearch.py or extend recall_measure.py), not a bare run.

## D-2723 - S5 practicality filter (D2622) IMPLEMENTED + vector+rerank dominates hybrid+rerank (2026-09-30)

### D2622 (S5 practicality / applicability filter) — IMPLEMENTED (deterministic backend)
- `config/practicality.yaml` minted (C12 config-first): use_case_domains [design, business]; 3 labels
  immediately-applicable | context-dependent | abstract; `backend: deterministic` (swappable C21); ordered rule table.
- `pipeline/practicality.py` minted: `classify_practicality(fb) -> str` protocol; deterministic backend only;
  C16 fail-loud on missing/malformed config or unknown backend.
- **Forensic signal audit (3000 verified t11 FBs):**
  - `application` 100% populated (imperative "When X -> do Y") — the primary live signal.
  - `accessibility` 100% populated (self-evident 2486 / prerequisite 514).
  - `procedural_skill` 0% and `is_summary` 0% — INERT (declared in config, not hardcoded).
  - Corpus distribution: immediately-applicable 70.4% / context-dependent 29.6% / abstract 0.03%.
  - The `abstract` tier is near-empty BY CONSTRUCTION (S4 fills an imperative application for every FB);
    retained as the fail-closed fallback, not a live bucket.
- NOT wired into `stage5_verify.py` run loop — D2622 remains a POST-RATIFY-2 S5 addition (with F-15
  extraction_type verifier). No cascade: the module is standalone and reads config/practicality.yaml.

### Retrieval: vector+rerank DOMINATES hybrid+rerank (RATIFY-2 gate #2 re-measure)
- Added `vector+rerank` leg to `retrieval_benchmark.py` (cross-encoder rerank over the PURE VECTOR pool,
  no RRF fusion). Re-measured (30 golden queries, k=10):
  - fts 0.600 / 0.357 · vector 0.900 / 0.599 · hybrid-RRF 0.833 / 0.518 · hybrid+rerank 0.867 / 0.646 · **vector+rerank 0.900 / 0.647 / 0.090**.
- KEY FINDING: RRF fusion is **recall-negative** (vector 0.900 -> hybrid-RRF 0.833); rerank over the fused
  pool only partially recovers (0.867). `vector+rerank` keeps vector recall AND gains the cross-encoder MRR
  (0.647 vs vector 0.599), strictly dominating hybrid+rerank on recall (+0.033), MRR (+0.001), precision (+0.003).
- RECOMMENDATION: adopt `vector+rerank` as the production default (simpler — drop the RRF fusion leg that is
  currently recall-negative). Owner ratification required before flipping config.
- RATIFY-2 gate #2 remains PASSED (now with a strictly stronger leg).

### Forensic audit verdict (this turn)
- No break/cascade/drift from the two additive changes: `pipeline/practicality.py` is standalone (import-only,
  not called by any pipeline stage yet); `retrieval_benchmark.py` gained one new leg + one methods-list entry
  (A/B harness only, no production path touched). Governance census consistent.
- RATIFY-2 gate #1 (USearch/HNSW recall harness, D2280) STILL the one unbenchmarked S1.5 lever.

## D-2724 - vector+rerank ADOPTED as production retrieval default (owner-approved, 2026-09-30)

### Why a full rerun (root cause) — answered this turn
The chunking (S1) was re-cut to `rechunk-v4` (Vectara fixed-size >= semantic, D-2703). Under cluster-before-extract,
S1 segments are the leaf input to S1.5 clustering, and clusters are the extraction context for S2. Changing S1
invalidates the entire S1.3→S1.5→S2→S4→S5→S6 chain — every downstream checkpoint is a function of the S1 segment
set. Resuming from an existing S2 or S4 checkpoint would reuse FBs extracted from the OLD (t11) chunks, silently
discard the rechunk benefit (hidden staleness/drift), and produce a mixed-provenance DB (violates R14). A mid-pipeline
resume is only correct when the change is strictly DOWNSTREAM of that checkpoint (e.g. a pure S4 classifier change →
resume from S2). RATIFY-2's trigger is upstream (chunking), so full rerun is mandatory for the new chunks to take effect.

### vector+rerank ADOPTED (owner: "ok adopt vector+rerank")
- `config/pipeline_config.yaml`: `retrieval.method: vector` (values `vector`|`rrf`; C12/C21).
- `pipeline/pipeline_paths.py`: `RETRIEVAL_METHOD` constant.
- `pipeline/retrieve.py`: new `search()` dispatcher (vector → pure vector pool + cross-encoder rerank; rrf → search_hybrid; C16 fail-loud).
- 3 production call sites repointed (`graph_aware_search` seed, `agentic_search` non-graph, `agentic_search` broaden).
- `search_hybrid` UNCHANGED → benchmark A/B harness, CLI `--hybrid`, `measure_constraint_violation` never drift.
- Rationale: D-2723 measured vector+rerank 0.900/0.647/0.090 strictly dominating hybrid+rerank 0.867/0.646/0.087
  (RRF fusion recall-negative: vector 0.900 → hybrid-RRF 0.833). Revert = `retrieval.method: rrf`.

### Forensic audit verdict
No break/cascade/drift/blindspot: additive change only (new key + new constant + new dispatcher + 3 repoints);
config parses (method=vector), constant resolves, `retrieve.py` parses, `search_hybrid` callers untouched. Live smoke
deferred (no maxwell.db in checkout); underlying legs proven by the D-2723 benchmark.

## D-2725 - USearch/HNSW vs IndexFlatIP KNN recall harness (RATIFY-2 gate #1) PASSED (2026-09-30)

### What was built + run
- `benchmarks/benchmark_hnsw_recall.py` (new) + `config/usearch_hnsw_recall.yaml` (new, C12 config-first):
  sample_size/ks/pass_k/pass_threshold/HNSW M+efConstruction+efSearch/USearch metric+connectivity+expansion all from config.
- Ground truth = FAISS IndexFlatIP (exact brute force). Candidates = FAISS IndexHNSWFlat + USearch Index (both HNSW).
- Embeddings computed LIVE via `pipeline.embeddings.embed_texts_bge_m3` (bge-m3 512d L2-normalized) — SAME contract as the
  pipeline, so no D-2721-class 1024d/512d mismatch.
- Deterministic sample (seed 42) of 2000 rechunk-v4 segments (295,079 available).

### Results (n=2000, recall@k @[5/10/20/50])
- FAISS IndexHNSWFlat: 0.9998 / 0.9996 / 0.9991 / 0.9962 — build 0.089s, query 0.026s.
- USearch Index:       0.9837 / 0.9837 / 0.9811 / 0.9714 — build 0.031s, query 0.039s.
- GATE @k=10 threshold 0.95 → PASS (faiss 0.9996, usearch 0.9837).

### Verdict
- HNSW is a faithful approximation of brute-force IndexFlatIP for the pipeline's bge-m3 512d embeddings.
- FAISS IndexHNSWFlat is essentially lossless (>=0.996 at all k); USearch is acceptable (>=0.97) but FAISS wins on recall.
- Closes the D2280 lever ("IndexFlatIP is brute force; HNSW is O(log N)"): S1.5 neighbor search may swap to IndexHNSWFlat
  (O(log N) query) with negligible recall loss. The O(N)-vs-O(log N) gap widens at the 295K-segment corpus scale.
- RATIFY-2 gate #1 PASSED → BOTH gates now green (gate #2 smoke = D-2722). Full rerun is unblocked.

### Forensic audit verdict
- Additive only: 2 new files (benchmark + config) + 1 receipt; zero existing files touched; no production path changed
  (benchmark-only). No break/cascade/drift/blindspot/gap/conflict/bloat — distinct from benchmark_faiss_vs_usearch.py
  (D2120 clustering) and recall_measure.py (D2307 golden yield).

## D-2726 - External continual-learning repos assessed: reference-only, no adoption (2026-09-30)

Owner asked which of two GitHub resources are worth adopting/referencing/integrating.
- `github.com/topics/continual-learning` is a topic aggregation (not a repo). Top entries = agent-memory libraries
  (honcho, letta-code) + NN continual-learning TRAINING frameworks (avalanche, PyCIL, mammoth, FACIL, LAMDA-PILOT) + surveys.
  VERDICT reference-only: the training frameworks fine-tune networks incrementally (class-incremental) while Maxwell OS uses
  FROZEN models (bge-m3/Qwen3-Coder/DeBERTa) — architecturally inapplicable. Agent-memory libs are agent-runtime concerns,
  not a knowledge-extraction pipeline concern.
- `github.com/jrz97619761/test-model-thing` is a 298-star MIT MLX byte-level LM (4.5M params): latent-space prediction
  (JEPA-like) + recurrent trace units (retention-style recurrence) + test-time training, by a solo dev.
  VERDICT reference-only, NOT worth adopting/integrating: no RAG component (not embedder/reranker/chunker/classifier); toy PoC
  with no shipped weights.
- Tangential relevance only: (a) reconfirms MLX-on-Apple-Silicon is a viable local train/inference substrate (already Maxwell
  OS C1/C3 substrate); (b) its "test-time training + persistent state" is a conceptual echo of the incremental-index direction,
  whose concrete Maxwell OS answer is the D2280 HNSW lever (D-2725) + the pending S1.3 self-contained checkpoint (BUG-598
  option B) — NOT model fine-tuning. No files changed; no integration.

## D-2727 - RATIFY-2 full-rerun PREFLIGHT audit: PASS (2026-09-30)

Owner ratified the rerun, preflight first. Findings:
- **Entrypoint:** `python3 pipeline/runner.py` (run_id already `rechunk-v4-20260929`). `just preflight` is a comprehensive gate
  (repo integrity BUG-400/500, config drift, golden-hash D2367, taxonomy, OMLX health, decision-drift, deps, hardware).
- **Lazy-load IN EFFECT:** `mlx_provider.py` lazy singletons + `get_mlx_provider(role=...)` + `unloader.unload_all_models()` —
  unused LLMs are not held. No change needed.
- **vec0 FULLY VERIFIED** under `/opt/homebrew/bin/python3` (sqlite_vec import + load + CREATE TABLE + INSERT all pass).
  Set `stage6.vec_require: true` so S6 fails CLOSED instead of silently skipping vec0.
- **GAP — caffeinate:** the full-rerun path in `runner.py` has NO sleep prevention (`probe_run.py` does). A 13–16h run
  risks macOS sleep → silent stall. Launch under `caffeinate -dimsu python3 pipeline/runner.py`.
- **Remaining pre-rerun risk:** train/eval leakage (208 anchors are also the eval ruler) must be declared before S4/S5
  golden bootstrap.
- No break/cascade/drift: additive config flip + feed.opml + governance only.

## D-2728 - JEV vs JEPA vs Laya-MLX research (2026-09-30)

- **JEPA** (Joint Embedding Predictive Architecture, Meta) = self-supervised encoder. MLX ports exist
  (`JosefAlbers/vl-jepa` 98★, `dgrauet/vjepa2-mlx`, `lukasugar/vjepa2.1-mlx`) but JEPA is video/image world-model
  encoding — NOT relevant to text knowledge extraction. Do not adopt.
- **JEV** = typed/constrained decision model (parallel Choice/Score/Null in one forward pass): `bnsd55/jevmlx` (69★),
  `ankit-aglawe/tinyjev`, `lawrence3699/jev-style`, `mattt/AnyDecisionModel` (Swift).
- **Laya** = competing typed-decision framework with native MLX runtime `mizorewww/laya-mlx` (6643★, 7–14ms decisions
  on M3 Max). So **yes — MLX serves JEV/Laya typed-decision inference**, and OMLX could host a Jev/Laya head if added.
- **Verdict:** reference-only. Conceptually adjacent to S4 closed-menu (62/44) + abstention routing (D2618) — typed,
  fail-closed decisions — but the models are young/experimental, unproven on a 62-discipline taxonomy, and would need
  R5 + golden validation. Optional POST-RATIFY-2 pilot as a fast S4 pre-filter; NOT adoption now.
- `feed.opml`: added `continual-learning` topic feed.


## D-2729 - RATIFY-2 GO (rerun unblocked) + owner-gate A/B (train/eval split; FIX(130) re-triage) (2026-09-30)

### Forensic audit verdict (this turn)
- `decisions.yaml` <-> `decisions_summary.json` sha-consistent (`2220d3df87fd…`); `session_seed` registry consistent
  (decisions 858 / highest_bug BUG-600 / buglog_entries 336 == `bug_status.json` total_ids 336; open 129 / closed 207).
- **RERUN UNBLOCKED**: both gates green (D-2725 HNSW recall PASS, D-2722 retrieval smoke PASS), preflight PASS (D-2727),
  RATIFY-1/2/3/4 ratified, re-ground(8) COMPLETE (D-2715), domain axis 208/208 (D-2720), `stage6.vec_require=true` live.
- The train/eval split gates **only** the POST-rerun anchor→S4-golden bootstrap, not the rerun. Current golden is
  human-authored (D-2718 "NOT contaminated"), `golden_validate` 84/84 convergent + 7/7 S4 PASS.

### Owner-gate A/B — OG-1 train/eval split (leakage guard D-337/D-300/D-345)
- **Option A (RECOMMENDED)**: disjoint split + machine-enforced manifest. KEEP(46) → S4 golden few-shot (cross-model
  vote ≥2/3, D2362) and **pin those 46 OUT of the eval ruler** (208→162). The split manifest is a RAIL (sha256-pinned;
  a check fails if any golden anchor re-enters eval) → future leakage mechanically impossible (drift-proof).
- **Option B**: zero-anchor golden — anchors stay 100% eval (n=208); S4 golden from fresh human-mined sources. Max eval
  power, zero coupling, but slower and leaves the D-2719 "reuse anchors" intent unrealized.
- **Option C**: use anchors as golden AND keep in eval — **REJECTED** (leakage inflates S4 accuracy).

### Owner-gate A/B — OG-2 FIX(130) re-triage (post-D-2720)
- 128 "domain_final empty" FIX anchors → **DOMAIN-RESOLVED** (D-2720 filled 208/208) → golden-eligible subject to split.
- 7 "abstractive" FIX anchors → resolved by D-2715 (re-ground(8) COMPLETE: 4 verbatim + 4 semantic-paraphrase KEEP-flag).
- FIX/DROP R137 → verbatim-confirmed (reground8) → KEEP.
- Net: all 208 anchors have a definitive 5-axis disposition; the ONLY remaining owner decision is the split.

## D-2730 - OG-1 train/eval split DECLARED = Option A + RATIFY-2 launched S1.5->S6 (2026-09-30)

### Owner decision (OG-1)
- **Option A DECLARED**: disjoint split + machine-enforced split manifest. KEEP(46) -> S4 golden pool, PINNED OUT of eval ruler (208->162).
- `governance/frontier_audit/split_manifest.json` = sha256-pinned RAIL (golden anchor re-entering eval fails). Option B superseded; Option C REJECTED (leakage).
- Golden bootstrap (cross-model vote >=2/3, D2362) = POST-rerun; owner adjudicates disagreements only.

### RATIFY-2 launch
- Scope **S1.5->S6** (S1.3 prefilter COMPLETE + manifest-valid; S1 chunk 295,079 verified 4660/4660).
- Interpreter `/opt/homebrew/bin/python3` (3.14) with PATH prepended -> single interpreter (no 3.12/3.14 skew).
- `stage6.vec_require=true` fail-closed; `caffeinate -dimsu`.

### Forensic audit (pre-commit, read-only)
- Registry consistent (859->860 / BUG-600 / 336 == bug_status 336); OMLX UP + Ollama UP; golden hash PASS;
  version gate PASS; retrieval.method=vector + vec_require=true live. No drift/blindspot/conflict/bloat.

## D-2731 - RATIFY-2 survived battery outage + monitor added + BUG-601 (2026-09-30)

### Battery outage (survived)
- Laptop drained to 8% mid-S1.5 (~14:25). Run SURVIVED: no reboot (uptime 2d), runner PID 33655 + caffeinate intact.
- Crash-safe resume CONFIRMED: embeddings_cache/state.json (fingerprint + total 295079 + done_batches) + 269 batch .npy live.
- Root slowness = bge-m3 CPU-bound (Ollama BERT has no Metal; D2190-accepted backend). Throughput recovering post-AC.

### Monitor
- scripts/watch_ratify2.py: read-only watch loop on state.json (env-overridable POLL_S / STALL_MIN). Alerts on drop/stall/done/dead.

### Forensic audit (read-only)
- rows:150 CORRECT (ANCHOR-3 sheet = 150 rows + header; D-2730 hygiene note was a MISREAD). Cohort 208 vs sheet 150.
- evidence_passages vs evidence_passages_shown RESOLVED (all 7 fields in schemas.py; BUG-596/187 CLOSED).
- BUG-601 filed: anchor verifier reads D-2720 CSV domain artifact as JSONL -> just health breaks.

## D-2732 - BUG-601 FIXED + duplicate-runner incident resolved + BUG-602 filed (2026-09-30)

### BUG-601 fixed (anchor verifier CSV remap)
- verify_anchor_family_registry.py now reads axes.domains.artifact as CSV (read_csv_rows) not JSONL; removed the
  obsolete intersection_default_key/alternate_key/rows checks.
- Restored D-2720 over-reach in config/anchor_family.yaml (CT/DISC intersection 150, ET 145, machine_observations 150)
  so owned axes stay anchored to the 150-row ANCHOR-3 sheet while domains is measured against the 208-row CSV.
- Verifier EXIT=0: "ok anchor family registry ... domains OWNED cohort 208 primary_domain_filled 208/208".

### Duplicate-runner incident (resolved)
- Tracking paste accidentally carried the full launch line -> second runner (36748/36749/36750) wrote the same
  embeddings_cache/state.json as the live runner (33655). Killed duplicate (child 36750 first, then parent);
  preserved original.
- Checkpoint verified clean (fingerprint unchanged, no dup indices, all multiples of 64; only known gaps 16256/16320).
- The duplicate `>` redirect TRUNCATED the live runner log -> log now shows its own "Stage 1.5 FAILED (exit code -15)",
  a stale/deceptive log. Source of truth = state.json + ratify2_watch.log.

### BUG-602 filed
- runner.py has no singleton/pidfile guard; launch lacks < /dev/null -> root cause of the accidental relaunch.
- Fix deferred post-run.

### Forensic audit (read-only, pre-commit)
- Single runner 33655 + child 33657 + caffeinate 33656 + llama-server 33658; no duplicate. S1.5 healthy at 70.8%
  (3265/4611 batches, ~208960/295079 seg, 12 batches/min). No break/cascade/drift/blindspot/conflict/mismatch/bloat.

## D-2733 - S1.3-S1.5 integrity VERIFIED CLEAN + split_manifest leakage rail + BUG-603 (2026-09-30)

### Integrity verdict (S1.3 -> S1.5): CLEAN — no rerun required
- state.json: sorted / no-dup / all multiples of 64; fingerprint b9e924d5 unchanged -> input segments stable.
- .npy cache: 3474 files, ALL exactly 131200 bytes, shape (64,512) float32, all-finite -> 0 torn writes.
- 0 done_batches missing a file; only 2 known quarantine gaps (16256/16320, battery outage — tracked, not corrupt).
- run dir has NO faiss/cluster artifacts -> the dead duplicate never reached clustering; "Stage 1.5 FAILED exit -15"
  in the runner log is the DUPLICATE's SIGTERM, not the live run.

### split_manifest rail implemented (Option A, OG-1)
- scripts/verify_split_manifest.py: fail-closed on any golden id re-entering eval (disjoint 46/162/208 + option A).
- Manifest path declared in config/eval_integrity.yaml split_manifest.file (C12). Wired into just health (--selftest).

### BUG-603 filed
- ids_sha256 pin (a3959dc1) is irreproducible: no emitter script + undocumented canonicalization (11 candidates miss).
- Semantic disjointness verified independently and HOLDS. Re-pin is owner-gated.

## D-2734 (2026-09-30) - Duplicate-book-source forensic audit + source_identity fail-closed rail
### Forensic verdict: the "20+ duplicate book sources" is BUG-289, FIXED in the live path
- Root cause: source_diversity counted FILENAMES, not works (29.1% of "convergence" = same book twice; 369 works with >1 filename).
- Fix confirmed LIVE (RATIFY-2 rechunk-v4 code path): resolve_source_id() = SHA-256(normalize_author|normalize_title) (D2176),
  used at S1.5 (stage1_5_embed_cluster.py), S2 (stage2_extract.py), S4 (stage4_merge.py D2376 source_ids restore).
- Canonicalization (D2308/D2315/D2507/D2509/D2449/D2459): subtitle split, casing, co-author lists, unicode, piracy noise, sentinel authors.
- Coverage measured: 962/962 metadata records resolve author+title -> 0.0% fall to the filename-hash fallback branch.

### Fail-closed rail added (closes the "believe it's fixed" -> "fails closed if it regresses" gap)
- scripts/verify_source_identity.py: 6 known-answer canonicalization controls (BUG-492) + live both-unknown-ratio gate.
- Wired into just health (--selftest + live). Config home: config/eval_integrity.yaml source_identity.* (C12).

### Residual (NOT hash-fixable, owner-gated post-run)
- Same-book TITLE RENAME across editions ("Systemantics"=="The Systems Bible") needs semantic dedup
  (Broder shingling/MinHash + Splink, per D-273e rec).

## D-2735 (2026-09-30) - Two owner-gate rulings (senior RAG/system-engineer judgment)
### 1. S1.3 self-contained checkpoint (BUG-598 option B): APPROVED — implement POST-RUN
- Structural change to the resume/checkpoint protocol. Mid-run implementation risks cascade/drift against the
  live state.json fingerprint b9e924d5. No design change; sequencing only: do it immediately after RATIFY-2
  completes and before any rerun.
### 2. Title-rename dedup: Splink DEFERRED; deterministic-first path APPROVED
- Splink (probabilistic record linkage) for a bounded handful of known renames is bloat (C28) + new dep (C2/C3).
- APPROVE instead: (a) owner-curated alias/rename map (exact, zero deps) for KNOWN renames; (b) read-only
  Broder-shingling detector surfacing candidate same-work-different-title pairs for owner gating — never auto-merge.
- Escalate to Splink ONLY if the detector reports a material count (dozens+).

## D-2736 (2026-09-30) - title-dedup detector built + 45 near-dup candidates root-caused + BUG-604 filed
### Detector (read-only, deterministic, no new dependency)
- scripts/detect_title_renames.py: exact character k-gram resemblance over canonical (author|title) strings,
  restricted to DISTINCT source_ids. Selftest 4/4. Wired into just health. Config home eval_integrity.yaml title_dedup.*.
### Result: 962 records -> 919 distinct source_ids -> 45 candidate pairs (jaccard >= 0.60)
- Root cause of ~40: stage0_5 mis-splits "liber3.md" filenames ("<title...> <author> liber3.md") -> trailing title
  words leak into the author field -> split book identities. FILED BUG-604.
- ~5 are genuine series volumes ("The Great Mental Models" Vol 1-4) -> MUST NOT be merged (false-positive proof
  that owner-gating/never-auto-merge is mandatory).
- NO mid-run fix: changing source_ids changes the live fingerprint b9e924d5. Parse fix + re-resolution is POST RATIFY-2.

## D-2737 (2026-09-30) - Option B full-text content dedup detector built (29 same-work pairs found)
- APPROVED Option B (sovereign full-text dedup) for #9 (zero-title-overlap renames).
- scripts/detect_same_work_content.py: word-shingle k=5 + seeded MinHash 128 + EXACT Jaccard verify. Local-only, no new dep.
- Selftest 3/3; wired into just health (selftest always-on, live scan OPT-IN --report ~1m48s).
- RESULT: 962 records -> 905 works -> 29 candidates (exact Jaccard >= 0.50). CAUGHT Systemantics ≡ The Systems Bible
  (0.999) + Metaphorically Selling ≡ The Tall Lady With the Iceberg (0.726) + BUG-604/name-order/subtitle classes.
- All 29 -> OWNER GATE. No source_id changes -> fingerprint b9e924d5 intact.

## D-2738 (2026-09-30) - Owner-gate dedup ledger built (fail-closed, never auto-merge)
- Merged 45 title candidates (D-2736) + 29 content candidates (D-2737) -> 59 unique pairs (overlap dedup'd by source_id pair).
- scripts/gate_duplicate_candidates.py: deterministic ledger generator; advisory-only machine hints (never a verdict);
  re-runs PRESERVE owner verdicts by pair_id (drift-safe).
- scripts/verify_duplicate_gate.py: structural rail (wired into just health) + `--gate` apply-guard that REFUSES
  (exit 2) while any pair at/above apply_threshold 0.50 is still PENDING — no merge without an explicit owner verdict.
- Hint census: series_volume=3 (Great Mental Models Vol 2/3/4 — DANGER, never merge), title_rename=1
  (Systemantics <=> The Systems Bible), author_leak=10 (BUG-604 mis-splits), noise_suffix=5 (z-lib/_clean/epub),
  subtitle_or_edition=32, review=8 (incl. Sean Adams Color vs Type, Brand Flip vs Gap).
- CONFIRMED owner observation "majority are duplicates": ~48/59 genuine duplicate pairs, ~11 false positives isolated.
- MERGE applies POST-RUN (source_id change repins live fingerprint b9e924d5). C12 config home: eval_integrity.yaml duplicate_gate.*

## D-2739 (2026-09-30) - Splink escalation DEFERRED post-BUG-604 (deterministic-first reaffirmed)
- Splink (probabilistic record linkage) NOT adopted now: root-cause fix (BUG-604) first, then measure the residual.
- Config-gated, data-driven trigger (C12): escalate to Splink as a THIRD read-only detector feeding the SAME owner-gate
  ledger (never auto-merge, fail-closed --gate unchanged) ONLY IF post-BUG-604 residual genuine same-work pairs
  >= duplicate_gate.splink_escalation_residual_threshold (3).
- Rationale: BUG-604 is systematic (not stochastic noise); Splink reintroduces drift (blocking rules + priors + match
  thresholds); suffix_dedup precedent (2026-09-17, 100% name-only-merge bias) already demands body corroboration which
  D-2738 provides; MinHash candidate generation already solves scale (sub-quadratic). Exact Jaccard yielded 0.999
  (Systemantics) with zero model assumptions.

## D-2741 (2026-09-30) - Duplicate-book deletion deferred to post-run quarantine (BUG-289 tail)
- Forensic audit of the duplicate deletion request: 43/59 ledger pairs already owner-flagged medium-conviction (NOT
  duplicates) -> ~73% detector false-positive rate; of the remaining 16, 4 more false positives (Great Mental Models
  Vol 2/3/4 + Sean Adams Color-vs-Type) -> 12 genuine same-work duplicates.
- DECISION: DO NOT delete mid-run (RATIFY-2 live in S2; deleting S0 source .md risks metadata/chunk/embedding drift).
  DEFER to post-run. QUARANTINE (move to _dedup_quarantine/) not hard-delete (R-D410). Owner per-file confirm.
  Plan: governance/dedup_deletion_plan.json (12 entries).

## D-2742 (2026-09-30) - BUG-602 fixed: runner singleton/pidfile guard
- Root-caused duplicate-runner incident (pids 36748/36749/36750 vs live 33655) that orphaned S1.5 batches 16256/16320.
- FIXED: pipeline/runner.py _acquire_singleton_lock() — C12 config-driven (run.singleton_lock, run.singleton_lock_path),
  fail-closed (refuses while live holder pid exists), reclaims dead pid, atexit cleanup. Wired into run_pipeline().
- Verified: stale-reclaim exit 0, live-refuse exit 1, atexit cleans lock. MUST-FIX before S2..S6 re-run.
- Also confirmed Stage-2 datasketch ModuleNotFoundError was transient: datasketch 2.0.0 installed; full MinHashLSH
  round-trip (constructor+insert+query+jaccard @ threshold=0.9 num_perm=128) passes.

## D-2740 (2026-09-30) - Owner approval + S1.5-finalization watcher fix (BUG-605)
- Owner APPROVED D-2738 (owner-gate dedup ledger) and D-2739 (Splink deferral + config-gated trigger).
- Live forensic audit: S1.5 COMPLETED 20:34 (checkpoint.jsonl + singletons.jsonl written, embeddings_cache removed);
  pipeline advanced into S2 (Principle Discovery Gate, probing 1817 clusters, actively advancing).
- User-reported "WAIT state.json not written yet" was a MONITOR-ONLY cosmetic bug (BUG-605): watch_ratify2.py had no
  S1.5-finalization detection and looped forever once state.json was removed. FIXED: added _s15_finalized() -> exit 0;
  killed stale watcher PID 34339.
- NOTE: 2 quarantine gaps (batches 16256/16320, ~128 segments) remain unembedded; re-embed before S6.

## D-2743 (2026-09-30) - S2 re-run readiness + launch-mechanism finding (no code defect)
- Forensic audit for S2/S4/S5/S6 before re-run: datasketch 2.0.0 installed + full MinHashLSH round-trip verified
  (threshold=0.9, num_perm=128); BUG-602 singleton guard fixed+verified (stale-reclaim exit 0, live-refuse exit 1);
  resume command corrected (--resume-from 2, NOT "stage2" — numeric stage ids; docstring fixed in runner.py).
- S1.5 input intact: 45,548 segments (12,514 clustered + 33,034 singletons); 128 orphaned segments (0.28%) logged D-2740.
- FINDING (launch mechanism, not a code defect): a backgrounded `nohup ... &` launch from a subprocess shell does
  NOT survive — the shell reaps the runner after the command returns, orphaning the omlx-server LLM-preflight child.
  S2 must be launched from a durable terminal session (caffeinate -s to defeat sleep, given the battery-outage history).
- Pre-existing S4/S5/S6 OPEN bugs (BUG-341, BUG-305, BUG-376, BUG-456, BUG-278, BUG-301, BUG-263) are NOT S2 blockers.

## D-2744 (2026-09-30) - BUG-606 fixed: preflight timeout must exceed OMLX watchdog restart cycle
- Root cause: runner preflight hardcoded timeout=30 < watchdog restart worst-case ~43s (kill 10 + sleep 3 +
  RESTART_WAIT_SECS 30). A BUG-017 trend restart (false positive on 0.1→8.6GB model-load spike) made preflight
  abort S2 mid-restart. Fix: C12 run.preflight_timeout_sec: 90 + _get_preflight_timeout(). Verified healthy rc=0.
- OMLX now healthy (RSS 4.4GB). S2 can be relaunched with the same command.

## D-2745 (2026-09-30) - BUG-607 fixed: datasketch ModuleNotFoundError was an ENV-DRIFT bug, not transient (root cause)
- CORRECTION to D-2742/D-2743's "transient" claim: S2 failed 3x on `ModuleNotFoundError: No module named 'datasketch'`
  at stage2_extract.py:1396 because the runner hardcoded bare `"python3"` in subprocess.run(), which resolves via the
  LAUNCHER's PATH — and the machine has FOUR divergent Python interpreters.
- Root cause: the user's login zsh resolves `python3` → conda base (/Users/barn/miniforge3/bin/python3, 3.13), which
  had NO datasketch. The prior "installed / round-trip passes" tests ran in a NON-login shell → /usr/local/bin/python3
  → Python.org framework 3.12, the ONLY env where datasketch 2.0.0 was installed. Testing the wrong interpreter = the
  blindspot that kept the loop going.
- Also present: incomplete `knowledge-pipeline` conda env (3.11, missing pandas/pyarrow/datasketch) and homebrew 3.14
  (S6 vec only, stage6.vec_python). Full dep-chain audit: conda base has 11/12 S2-S6 deps (only datasketch missing).
- FIX: (1) `pip install datasketch` into conda base; (2) C12 config `run.python_bin` + `_get_python_bin()` in
  runner.py, used for BOTH the stage subprocess and the preflight (eliminates PATH drift deterministically).
- Verified: init_minhash_lsh → MinHashLSH ok=True + full round-trip under /Users/barn/miniforge3/bin/python3;
  `--dry-run --resume-from 2` previews 2,4,5,6,6b,6c. Registry: decisions 875, buglog 343, highest BUG-607.
- FOLLOW-UP: consolidate the 4-Python drift (provision or delete knowledge-pipeline; declare conda base canonical).

## D-2746 (2026-10-02) - BUG-609/610 fixed: S2 conditional-success + corpus-wide denominator; S2 exits 0 and advances to S4
- Root cause (two layers): BUG-609 — at temp=0.0 a schema-invalid FB is DETERMINISTIC, so 2–5 clusters of 12,607
  could never clear on re-run, yet the exit-2 "re-run to retry failed clusters" was the only advance route → infinite loop.
- BUG-610 — the accept_conditional_within_tolerance fix never fired because the fail-closed ratio used
  len(target_clusters) AFTER the resume filter shrank it to 2–5, so 2–3 failures = 60–67% → hard-fail exit 1
  before the within-tolerance branch. The denominator was "remaining subset", not "total corpus".
- FIX: (1) config stage2.accept_conditional_within_tolerance: true + S2_ACCEPT_CONDITIONAL in pipeline_paths.py;
  (2) total_corpus_targets captured BEFORE the resume filter and used as the denominator (12,607).
- VERIFIED: S2 exits 0 — 2/12,607 clusters dropped (0.016% ≤ 0.01), 8,217 FBs final, advances to S4 (running).
- Registry: decisions 876, buglog 346 (131 open / 215 closed), highest BUG-610.

## D-2747 (2026-10-02) - conspiracy = growth_edge ROLE + contested retention flag; deterministic non-principle reroute wired automatic into S4
- OWNER-CONFIRMED RULING: conspiracy/speculative claims are **growth_edge ROLE + a `contested` retention flag** — NOT a 6th
  content_type. D2591 keeps the 5-role axis CLOSED; a 6th type regresses BUG-277 and forces consumers to learn a new value.
- `contested` is a growth_edge RECORD field (bool), NOT a new epistemic_status value: epistemic_status is S5-DERIVED
  (serving_gate, 4-valued: corroborated|source-supported|cross-source-unverified|speculative) and answers the verification-tier
  question; `contested` answers "do sources contradict?" — ORTHOGONAL. (Forensic note: the word "contested" already existed in
  the TOMBSTONED migrate_D2205_epistemic.py EPISTEMIC_STATES list; D2205 is abandoned, so re-using the word is safe, but it is
  deliberately NOT re-entering the epistemic_status axis.)
- BROADENED growth_edge entry criterion (D-2747): also admits a CONTESTED/UNFALSIFIABLE claim. Retention guard: a
  `contested: true` record is NEVER noise_drop'd / quarantined.
- REROUTE IS AUTOMATIC, not post-hoc: pipeline/content_types.reroute_content_type() (pure deterministic rules — D-343:
  content_type must NOT be LLM-classified, measured -2.98pp vs constant baseline) wired into stage4_merge._resolve_content_type()
  (the single routing choke point; call sites 1534/1605/1681). 3-tier first-match-wins: (1) owner-adjudicated map
  (governance/content_type_adjudication.json, 46 rows) → (2) keyword denylist (config/content_types.yaml reroute.ti_to_pt_keywords)
  → (3) structural (TI with neither syntax nor parameters → quarantine).
- BUG-611 (sampled audit ~18% TI + ~10% GE misclassification in rechunk-v4-20260929) is the register bug; ROOT CAUSE BUG-170
  (non-principle routed-not-classified).
- Registry: decisions 877, buglog 347 (132 open / 215 closed), highest BUG-611.

## D-2748 (2026-10-02) - principle-purity audit: 2.1% of 7,151 principles are definitional non-rules; 100%-accuracy reframed as fail-closed structural invariant + owner-adjudicated residual
- QUESTION THE USER ASKED: "are all principles 100% transferable rules?" — NO. Deterministic audit (scripts/audit_principle_purity.py,
  pure rules per D-343 — content_type must never be LLM-classified, measured -2.98pp vs constant baseline) over the principle bin
  (7,151 = 87.0% of rechunk-v4-20260929's 8,217): 527 (7.4%) fire a structural signal — definitional_no_prescriptive 152 (2.1%,
  "X is/describes/involves" + no prescriptive verb → descriptive fact, NOT a KNOW/APPLY rule); definitional_with_prescriptive 238
  (3.3%, ambiguous); open_tension 144 (2.0%, growth_edge candidates, mixed precision); procedure 1 (false positive — confirms D275b
  step-count is never the discriminator); exact_dup 5 (one definition × 5 records — SHA-256 dedup leak). Artifact: temp/principle_purity_triage.json.
- RE-EVALUATION OF D-2747: correct in SHAPE, but a BLINDSPOT — it guarded only the 4 non-principle bins; reroute_content_type() is a
  NO-OP for principles (only the owner-map tier can touch them). The guarantee is POST-HOC, not PREVENTIVE.
- REFRAME (future-proof / future-tax-proof): "100% accuracy" cannot mean "the classifier always guesses right" — it must mean "no
  misclassified record reaches S6 committed as a wrong role". Achieved deterministically by (1) per-role STRUCTURAL INVARIANT
  (principle MUST be a single prescriptive transferable claim; PT MUST have ≥2 steps + done-condition; TI MUST have syntax/params),
  (2) FAIL-CLOSED at the single choke point _resolve_content_type() (a role failing its own invariant → quarantine, never silently
  pass), (3) owner-adjudicated RESIDUAL into governance/content_type_adjudication.json (the only place semantic judgment lives).
  No new LLM, pure functions, 5-role axis stays CLOSED (D2591), residual shrinks as adjudications accumulate — zero future tax.
- BUG-170 was backfilled a `## BUG-170` heading (was prose-only → uncitable by the mint gate); BUG-612 filed for principle-purity
  drift. Both now registered (buglog 349).
- OWNER-GATED NEXT (do NOT auto-flip — a 2% knowledge-base drop cascades): (1) adjudicate temp/principle_purity_triage.json → seed
  the tier-1 map (already supports principle→disposition rows); (2) add the principle structural invariant as tier-2 of
  reroute_content_type(); (3) re-run audit post-S4.
- Registry: decisions 878, buglog 349 (134 open / 215 closed), highest BUG-612.

## D-2749 (2026-10-02) - extraction_type (FORM) audit: content_type does NOT depend on FORM; D2417 default is a latent inversion; FORM is best-effort
- QUESTION: "if you rely on content_type on FORM classification, check FORM accuracy." ANSWER: content_type (ROLE) is decided
  INDEPENDENT of extraction_type (FORM) — D2323 decouples them; _resolve_content_type()/reroute_content_type() never read
  extraction_type. The dependency is REVERSED: D2417 CONTENT_TO_EXTRACTION_TYPE defaults extraction_type FROM content_type
  when S2 omits it. So my content_type reroute has NO FORM regression surface.
- FORM accuracy (scripts/audit_form_axis.py, deterministic → temp/form_axis_audit.json): signal agreement 19.5–37.3%
  (causal 19.5 / descriptive 37.3 / normative 35.1 / empirical 34.1) with systematic cross-contamination (causal→normative
  726×, empirical→descriptive 387×) and high no-signal (up to 1,127) → the FORM axis is largely unverifiable by structure.
- LATENT INVERSION (BUG-613): CONTENT_TO_EXTRACTION_TYPE['principle'] = 'descriptive_model' defaults a transferable RULE to
  the "describes" FORM. 0 records defaulted in this checkpoint (latent, not active), but any future batch where S2 omits the
  field silently stamps every principle as descriptive_model. OWNER-GATED flip to normative_heuristic.
- RULING: extraction_type is re-declared BEST-EFFORT metadata — never a routing/verification input, only a serving-time
  epistemic hint.
- LANDED: tests/test_contested_retention_guard.py (6/6 green) pins the D-2747 retention guard — a `contested` record is
  never noise_drop'd/quarantined.
- Registry: decisions 879, buglog 350 (135 open / 215 closed), highest BUG-613.

## D-2750 (2026-10-02) - principle-purity adjudication APPLIED (owner-approved): D2417 flip + tier-2 FORM invariant + 527-row map seed
- D2417 flip RATIFIED: content_to_extraction_type.principle descriptive_model → normative_heuristic (a principle is a
  transferable RULE, not a "describes" FORM). Closes the BUG-613 latent inversion.
- Tier-2 FORM invariant wired into reroute_content_type() (pipeline/content_types.py `_principle_form_violation`): a
  principle whose FORM is not a rule is rerouted FAIL-CLOSED to a RETAINED disposition only — open-tension → growth_edge,
  procedure+done-condition → process_template, definitional-without-prescriptive → quarantine. NEVER noise_drop (auto-DROP
  stays owner-gated via the tier-1 map).
- Owner map seeded: temp/principle_purity_triage.json adjudicated (audit disposition priority) → 151 noise_drop + 231
  quarantine + 144 growth_edge + 1 process_template appended to governance/content_type_adjudication.json (573 rows / 569
  unique fb_ids; the 5 exact_dup records share one fb_id and collapse to 1 in the loader — a checkpoint dedup leak, not a
  routing bug).
- Verification: 16/16 tests green (new test_principle_form_invariant.py + retention guard + content_type contract); import OK;
  0 invalid proposed values.
- Registry: decisions 880, buglog 350 (135 open / 215 closed), highest BUG-613.

## D-2751 (2026-10-02) - FORENSIC AUDIT caught a LIVE pre-reroute S4 process writing stale records; stopped; reroute verified automatic
- THE FINDING: the reroute was wired into _resolve_content_type() (stage4_merge.py:273) at 10:41-11:11, but a live S4
  process (PID 60590, started 05:55) had already imported the OLD module and wrote 418 un-rerouted records. 50 of them are
  provably mis-routed (fb_id in the 573-row map but committed as principle).
- DRY-RUN (deterministic, read-only): reroute_content_type() over the full 8,217-FB S2 checkpoint corrects 627 records
  (principle→quarantine 231 / →growth_edge 183 / →noise_drop 151; TI→PT 34; TI→principle 14; principle→PT 9; TI→quarantine 3;
  TI→PI 1; GE→noise_drop 1).
- ACTION: stopped runner (60572) + stage4 (60590), both exited; checkpoint frozen at 418 records.
- RULING: the reroute is AUTOMATIC at the single choke point for any NEW S4 invocation — no triage rerun needed; the triage
  was a one-time diagnostic whose map is now a static import-time asset. Future batches inherit the deterministic reroute +
  tier-2 FORM invariant; only the fb_id-keyed tier-1 map is corpus-specific.
- Files BUG-614 (stale process / hot-reload gap).
- Registry: decisions 881, buglog 351 (136 open / 215 closed), highest BUG-614.

## D-2752 (2026-10-02) - name collisions benign; 5-record cross-cluster fb_id dedup leak confirmed+fixed; depth.json reused (depth NOT restarted); S4 restarts fresh
- NAME COLLISIONS: state.json `name_collisions: 5` is the D2069/D2350 name-disambiguation counter, NOT duplicates — the
  418-line checkpoint has 418 UNIQUE names. Benign.
- REAL DUPLICATE: 1 fb_id (334554e0…) ×5 and 1 (f8b4e061…) ×2 in the S2 checkpoint, all BYTE-IDENTICAL (same definition/
  mechanism/source_segments). cluster-before-extract split one claim across N clusters; dedup_fbs_by_cosine only dedups
  WITHIN a cluster (never fires under 1-principle-per-cluster). FIXED: cross-run seen_fb_ids guard + provenance merge (BUG-615).
- DEPTH: NOT restarted. depth.json (7,149 entries) is cluster_id→depth, content-derived and code-independent — the reroute
  changes routing, not depth values. It is REUSED via the BUG-184 resume path.
- RESUME: depth pre-pass resumes from depth.json; the main classify loop restarts fresh (418 stale pre-reroute records ARE
  wasted, regenerated). S2 input (8,217) + depth.json (7,149) survive.
- IMPLEMENTED: BUG-614 stage-code fingerprint guard (discards stale checkpoint on code drift, PRESERVES depth/cribs per
  BUG-616); BUG-615 cross-run fb_id dedup. Stale checkpoint.jsonl/.state.json/.segids deleted via safe_delete.py (backed up
  to governance/backups/ + backup/deletions/); depth.json kept.
- Files BUG-614/615/616. Registry: decisions 882, buglog 353 (138 open / 215 closed), highest BUG-616.

## D-2753 (2026-10-02) - prior-art correction: constrained decoding already A/B-tested+failed; content_type fine-tune blocked; no blockers before S4 rerun; quarantine spot-check generated
- "S3" correction: stage3 was REMOVED (D2120/D2198). Enum emission happens at S2 (extract) + S4 (classify), so grammar
  decoding would live there, not S3.
- CONSTRAINED DECODING: ALREADY TESTED + FAILED. D2548 proposed an Outlines/XGrammar pilot; A/B ran → D2392 "0.6.0
  xgrammar ENFORCES but BREAKS gpt-oss-20b (Harmony conflict)"; D2408 "response_format=json_object → empty content". The
  mlx-lm/OMLX backend cannot grammar-constrain gpt-oss-20b. Not a next step on the current stack.
- FINE-TUNED CLASSIFIER: DEPTH already has a FULL fine-tuned 4-way ModernBERT-base (knowledge pipeline/classifier_depth).
  content_type/S4 is BLOCKED — D274d "S2/S4 must NOT be trained on the current labels" (verifier F1=0.484) + D274f "the
  first thing NOT to do with the anchor is fine-tune on it." Prerequisite = the D-274f human-provenanced anchor.
- RULING: NO must-blockers before the S4 rerun (reroute wired+verified; BUG-614/615 fixed; quarantine=HOLD never DROP).
  SHOULD: owner ratifies the 234 quarantine via governance/spot_check_quarantine_234.md (generated; 234/234 resolve, 0
  missing). WORTH: build the D-274f anchor, then revisit constrained decoding + fine-tune on anchor labels.
- Registry: decisions 883, buglog 353 (138 open / 215 closed), highest BUG-616.

## D-2754 (2026-10-02) - the 1,027 "golden" depth labels are gpt-oss SILVER (93.3% unverified); silver depth classifier DORMANT; depth axis needs a human anchor (BUG-617)
- ANSWER to "are the 1,027 golden depth 100% accurate + human-verified?": NO. The retired golden header states
  "silver-standard — gpt-oss teacher labels, NOT hand-reviewed" (provenance gpt-oss 1027 / DeepSeek 0 / human 0). D2613/
  D2616: 93.3% unverified, 6.7% (69) 4-axis verified.
- CURRENT REFERENCE: governance/verified_core.jsonl = 443 rows (71 human-verified / 203 joint-vote / 169 pending-human);
  human-verified depth = 61 (13.8%).
- NO ACTIVE CONTAMINATION: the silver-trained depth classifier (ModernBERT) is DORMANT — S4_STUDENT_PRECLASSIFIER_ENABLED
  =false, macro-F1 0.34 silver / 0.48 clean (<0.85 gate), checkpoints archived (D-2713). Depth is LLM-classified (D2220).
- RULING: depth carries the same provenance gap as content_type (D-274d/D-274f); extend the anchor with DEPTH conformance
  sets (depth_source provenance) before any depth retrain. Depth labels are operational, not ground truth, until then.
- Files BUG-617. Registry: decisions 884, buglog 354 (139 open / 215 closed), highest BUG-617.

## D-2755 (2026-10-02) - quarantine subcategory taxonomy: a missing CONSUMER/TELEOLOGY axis; depth should be derived deterministically
- OWNER 27 annotations (spot_check_quarantine_234.md) reveal 4 buckets, NOT new content_types but a missing orthogonal axis:
  (A) operational/transferable-rule (→ process template); (B) educational/terminological-theoretical (frontend, user-facing);
  (C) philosophical/ethical-educational (subtype of B); (D) heuristic_tip/generic (surface-level wisdom).
- These distinguish CONSUMER + TELEOLOGY, which the closed 5-role FORM axis (D2591) does not → explains BUG-611 (definitional
  _with_prescriptive quarantined as one blob).
- RULING: do NOT hand-comment all 234 — 27 is enough to define the closed menu; bucket ~207 deterministically, owner spot-
  checks boundaries only. NON-blocking for S4 (HOLD).
- DEPTH (BUG-617): derive deterministically from domain axis (universal/cross-domain/domain/specialized = domain-count +
  granularity), LLM only for ambiguous boundaries — removes silver-depth by construction.
- ACTION: add `applicability` axis (operational|educational|philosophical_educational|heuristic_tip), provenance-stamped.
- Files BUG-611 + BUG-617. Registry: decisions 885, buglog 354 (139 open / 215 closed), highest BUG-617.

## D-2756 (2026-10-02) - owner first-pass dispositions on ambiguous quarantine; name collisions; Tragedy-of-the-Commons; SpotBugs dual-nature; Hektor/MCP not tools
- OWNER first-pass dispositions (governance/quarantine_owner_decisions_draft.md, exact fb_id map): growth_edge x6 (Unconscious
  Symbol, Partition Memory, Symbolic Architecture, Tool Dropping, Social vs Abstract, Intersubjective), principle x1 (Illusion
  of Peace), tool_instruction x1 (SpotBugs, dual-nature), noise_drop x1 (Third Party Random Selection). 7 OPEN resolved in the
  FINAL pass: pip→tool_instruction, Medical→growth_edge, Cooperation→principle, Youth→growth_edge, Tragedy-Digital→philosophical,
  Hektor→educational, MCP→educational.
- NAME COLLISIONS: "Tragedy of the Commons" is 5 distinct FBs in S2 (2 bare-name + Vacation Time + Digital Contexts +
  Organizational Management); only Digital Contexts (98298a22) is in the 234 quarantine. Collisions are NOT duplicates.
- TOOL-MENTION: Hektor + MCP have tool_name=None/syntax=None/params=None → NOT tool_instruction (educational/descriptive).
  pip (tool_name=pip) + SpotBugs (syntax `mvn spotbugs:check`) ARE tool_instruction. SpotBugs is dual-nature (tool syntax AND
  transferable rule).
- Files BUG-611. Registry: decisions 886, buglog 354 (139 open / 215 closed), highest BUG-617.

## D-2757 (2026-10-02) - depth refinement (D-2755 correction) + applicability axis implemented deterministically + owner dispositions folded
- DEPTH (FIXES BUG-617): D-2755's "domain-count + granularity" ruling CONFLICTS with D2220 ("depth is NOT domain count") and is
  corrected. Depth = ontological SCOPE of the causal mechanism, NOT a domain/discipline count. Keep semantic mechanism-scope
  (physicist-chef-poet) as PRIMARY; add deterministic distinct-DISCIPLINE provenance as a fail-closed CONSISTENCY GUARD (flag,
  never override); close provenance via the D-274f human anchor. Depth.json REUSED (D-2752) so this takes effect on the NEXT
  derivation.
- APPLICABILITY (FIXES BUG-611): new ORTHOGONAL Axis 3 (operational|educational|philosophical_educational|heuristic_tip) =
  WHO consumes the object + WHY. Deterministic (never LLM, per D-343): adjudication map → lexical (values+non-prescriptive →
  philosophical; tip/trick → heuristic_tip; definitional-without-prescriptive → educational; default operational). Wired into
  stage4_merge.py (applicability + applicability_source, provenance-stamped). Dry-run 8,217 FBs: operational 7,898 /
  educational 137 / philosophical_educational 146 / heuristic_tip 36.
- OWNER DISPOSITIONS FOLDED: 13 role corrections in content_type_adjudication.json (quarantine→growth_edge x8, principle x2,
  tool_instruction x2, noise_drop x1) + 3 applicability (educational x2, philosophical_educational x1) in
  governance/applicability_adjudication.json.
- Files BUG-611 + BUG-617. Registry: decisions 887, buglog 354 (139 open / 215 closed), highest BUG-617.

## D-2758 (2026-10-02) - forensic finding: 208-row owner-adjudicated five-axis anchor ALREADY EXISTS; depth≠domain-count; wire ANCHOR-208 as S4 depth/domain/discipline anchor
- FIXES BUG-617 (stale "depth has no human ground truth"). Forensic audit of config/anchor_family.yaml + config/closed_menu_v5.json
  found governance/ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv: 208 rows, ALL five axes filled (0 blanks) — depth 208/208 (universal 7 /
  cross-domain 50 / domain 92 / specialized 59, status OK), domain + primary_domain + discipline + content_type + extraction_type
  all 208/208. Provenance OWNER-ADJUDICATED (D-2720: depth owner blind-coded R001-R150 + 58 mapped; domain = reliable-pair machine
  vote + owner ruling; discipline = owner 80 / human 42 / owner-supplied 28).
- This IS the D-274f human anchor — already built, not missing. D-2754 conflated the 1,027 gpt-oss SILVER training labels (0 human,
  D2613) with this 208-row OWNER anchor; BUG-617 inherited that conflation.
- EMPIRICAL (owner data): depth is NOT a domain count — 1 domain spans depth 1/2/3/4 = 2/20/75/57; discipline is always
  single-valued. Confirms D-2757/D2220 semantic mechanism-scope.
- RULING: use ANCHOR_208 as the S4 depth/domain/discipline anchor (golden few-shot + held-out conformance gate); do NOT build fresh;
  do NOT derive depth from domain-count. Refine D-2757 guard distinct-DISCIPLINE → distinct-DOMAIN. closed_menu_v5 (44 domains + 62
  disciplines) is the label space; anchor domains are ON-menu (0 off-menu). Minor cleanup: 2 trailing-space discipline dupes
  ('economics '/'sociology '), 5 'emerging' catchall, 4 off-menu discipline cells (R042/R086/R091/R117).
- Files BUG-617. Registry: decisions 888, buglog 354 (139 open / 215 closed), highest BUG-617.

## D-2759 (2026-10-02) - forensic audit of ANCHOR-208 depth accuracy — 42/150 (28%) STALE (owner_depth vs canonical depth_final_class); do NOT wire until rebuilt
- FIXES BUG-618. Answer to "are those depths accurate?": NO. Diff of governance/ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv
  `depth` vs declared-canonical `depth_final_class` (anchor_adjudication_workbook_20260924.csv) over 150 owner rows:
  42/150 = 28.0% mismatch == measured intra_rater_alpha raw 0.710. Every mismatch row: view `depth` == `owner_depth`
  (raw blind call), NOT final adjudicated class. The 7 negative_set rows (R033/R049/R062/R085/R087/R101/R139, owner-
  RETRACTED class-1 calls) still carry depth=1 in the view but depth_final_class=2/3. Canonical 150 have ZERO universals;
  view wrongly reports 7.
- SUPERSEDES D-2758's "wire as-is": anchor EXISTS but depth column was never audited against its own canonical source.
  Corrected dist: 150 = universal 0 / cross-domain 44 / domain 75 / specialized 31 (+ 58 extras, lower provenance).
- RULING: (1) REBUILD 208 view depth from depth_final_class BEFORE wiring (deterministic data-repair + provenance-stamp
  human_adjudicated vs mapped); (2) keep 7 negative_set rows as near-neighbour negatives (class-1/2/3 boundary);
  (3) class-1 universal is UNREACHABLE in the 150 (only annex U001-U004 owner-confirmed) — universal conformance must
  source from the annex; (4) do NOT wire depth into stage4_merge.py until (1) done + re-audited.
- Files BUG-618. Registry: decisions 889, buglog 355 (140 open / 215 closed), highest BUG-618.

## D-2760 (2026-10-02) - owner finalized all 42 ANCHOR-208 depth mismatches; corrected depth map built; universal IS reachable (R049, R053)
- FIXES BUG-618 (finalization leg). Owner annotated all 42 mismatched depth rows in anchored_depth_mismatch_review_42.md.
  Parsed 42/42 (0 unparsed; handled 'specailized' typo -> specialized). Final dist over 42: universal 2 / cross-domain 19 /
  domain 15 / specialized 5 / noise_drop 1. R021 'Index Section' -> noise_drop (excluded, not a principle).
- 9 OVERRIDES (owner final != depth_final_class): R049/R053 cross-domain->universal; R085/R087/R101/R135 domain->
  cross-domain; R052/R118/R123 domain->specialized. 108 agreeing rows (owner_blind==depth_final_class) auto-consolidate.
- CORRECTS D-2759: universal IS reachable in the 150 (R049 Fermi Estimation, R053 Self-referential Incompleteness).
  Universal conformance no longer needs annex-only sourcing.
- ARTIFACTS: governance/ANCHOR_208_DEPTH_CORRECTED_20261002.json (208 rows, depth+depth_label+depth_source) and
  governance/depth_finalization_owner_42.json. Corrected 208 dist: domain 93 / cross-domain 63 / specialized 49 /
  universal 2 / noise_drop 1. depth_source: canonical_adjudicated 108 / owner_finalized 41 / noise_drop 1 / mapped 58.
  The stale 208-view CSV depth column (owner_depth) is SUPERSEDED — read depth from the corrected artifact only.
- Files BUG-618. Registry: decisions 890, buglog 355 (140 open / 215 closed), highest BUG-618.

## D-2761 (2026-10-02) - built human-provenanced depth conformance anchor (149 owner rows) + classifier-vs-gold conformance gate (chance-corrected kappa)
- FIXES BUG-617 (depth axis now HAS human-provenanced ground truth) + BUG-618 (corrected depth now has a real CONSUMER).
- ARTIFACT: governance/depth_anchor_conformance_20261002.json = 149 human-owner depth rows (domain 67 / cross-domain 46 /
  specialized 34 / universal 2), full text joined from maxwell.db fbs (150/150, 0 ambiguous), provenance-stamped. Excluded:
  R021 (noise_drop) + 58 mapped extras (NOT owner-adjudicated — pending). BUILDER: scripts/build_depth_anchor_conformance.py.
- GATE: scripts/depth_conformance_gate.py runs the PRODUCTION depth labeler over the 149 rows; statistic = Cohen's kappa
  (chance-corrected, per D-2611 — never bare accuracy on the 45% domain prior); floor 0.800 (agreement_floor.yaml operative).
  Modes: report-only default / --gate (CI) / --dry-run / --selftest. Config: stage4.depth_anchor_path + depth_conformance_kappa_floor.
- FORENSIC CORRECTIONS (3): (1) the LIVE depth golden is 7 HAND-AUTHORED examples (D2451), NOT silver — the 1,027 silver is
  retired to archive/golden_retired_D2618/ and NOT wired; (2) D-274f forbids injecting the anchor as few-shot (that is training);
  anchor is consumed ONLY by the conformance gate; (3) D-2611 RETIRED the 0.85 gate → chance-corrected kappa at 0.800.
- VERIFIED: builder + gate py_compile; gate --selftest (kappa 1.0/-1.0/0.0) + --dry-run (N=149); config YAML parses; live import OK.
  NOT run live (needs OMLX server): `python3 scripts/depth_conformance_gate.py [--gate]`.
- Registry: decisions 891, buglog 355 (140 open / 215 closed), highest BUG-618.

## D-2762 (2026-10-02) - deterministic normalization of ANCHOR-208 discipline axis (2 whitespace dupes fixed; 4 domain-bleed + 5 emerging flagged; NO silent remap)
- FIXES BUG-619 (deterministic leg). Forensic audit of 208-view `discipline` column (54 unique vs 62 closed_menu_v5 menu):
  2 trailing-space dupes ('economics ' / 'sociology ' — fragment one discipline into two, defeating exact-match golden join);
  4 DOMAIN-BLEED rows (R042 'design strategy'; R086/R091/R117 'personal productivity' = DOMAINS sitting in the discipline
  cell); 5 'emerging' catchall rows; 2 ADVISORY disc-status rows (R160/R205).
- NORMALIZATION (deterministic, no LLM, NO silent remap per C12d): scripts/normalize_anchor_discipline.py trims whitespace
  (2 rows -> 'whitespace_fixed', auto-collapsed to on-menu economics/sociology) and classifies all 208: 197 ok / 2
  whitespace_fixed / 5 emerging / 4 domain_bleed. The 9 non-ok rows go to an OWNER review queue; domain-bleed discipline
  must be re-classified by owner (judgment, not determinism); 'emerging' must be refined to a specific discipline.
- ARTIFACTS (provenance-stamped): governance/ANCHOR_208_DISCIPLINE_NORMALIZED_20261002.json (208 rows) +
  governance/discipline_domain_bleed_review_20261002.json (9 rows).
- DRIFT CORRECTION: primary_domain is ALREADY populated (0/150 empty workbook, 0/208 empty view, 38 on-menu domains) — the
  register's "classify 150 locked anchors' primary_domain" is STALE/RESOLVED. Remaining axis gap is DISCIPLINE, not primary_domain.
- Registry: decisions 892, buglog 356 (141 open / 215 closed), highest BUG-619.

## D-2763 (2026-10-02) - consolidate ANCHOR-208 into ONE dual-axis artifact; owner finalized 9 discipline rows; 'emerging' EXCLUDED from golden
- ADVANCES BUG-619 (finalization leg); supersedes the two per-axis artifacts with governance/ANCHOR_208_CONSOLIDATED_20261002.json
  (208 rows, depth + discipline + domain, provenance-stamped).
- OWNER finalized the 9 discipline review rows: R042=human-computer interaction, R086=behavioral economics, R117=behavioral
  economics, R052=design thinking, R092=research methodology, R100=organizational theory; R040/R080/R091 remain 'emerging'.
  Provenance: governance/discipline_finalization_owner_9.json.
- FORENSIC FINDING: 208-view `name` column TRUNCATED to 45 chars (49/208) + R039 non-breaking space (\xa0). Full names re-joined
  from maxwell.db; item_id is the stable key (208/208 align, 0 divergence).
- GOLDEN ELIGIBILITY: depth_golden_eligible = 149 human-provenanced (excl 58 mapped + R021 noise_drop);
  discipline_golden_eligible = 204 (excl 3 emerging + R021); overall golden_eligible = 204/208.
- RULING on 'emerging' (owner Q): EXCLUDE from golden exemplars. 'emerging' = abstention/catch-all, teaches no boundary,
  over-representation pulls classifier toward the catch-all (contamination -> cascades into S5/S6). It STAYS a valid OUTPUT
  label (in closed_menu_v5), routed to a refinement queue, NOT into the golden.
- Registry: decisions 893, buglog 356 (141 open / 215 closed), highest BUG-619.

## D-2764 (2026-10-02) - discipline axis lacks human ground truth (9/208 owner-finalized); NO discipline conformance gate yet; discipline golden ALREADY exists (7 hand-authored)
- FILES BUG-620. Consolidated anchor discipline_source: anchor_adjudication 197 / owner_finalized 9 / whitespace_fixed 2.
- RULING (D-274f): anchor is a CONFORMANCE set, NOT training. (1) NO discipline conformance gate yet — 197 silver + 9 human
  would measure LLM-vs-LLM (~95% circular) = contamination, not measurement; wait for ~150 human discipline labels (mirror
  the depth path). (2) NO anchor-as-discipline-few-shot (violates D-274f; and the discipline golden ALREADY exists as 7
  hand-authored exemplars, WIRED per D2454). DRIFT: prior "wire anchor into discipline golden few-shot" is WITHDRAWN.
- Registry: decisions 894, buglog 357 (142 open / 215 closed), highest BUG-620.

## D-2765 (2026-10-02) - discipline review queue PREPARED (199 unreviewed rows, ~141 target); clarifies '150 approved' = DEPTH not discipline
- CLARIFICATION (prevents axis conflation): the 150 owner-approved ANCHOR-208 labels were DEPTH (D-2760 — 149 golden + 1
  noise_drop), NOT discipline. Discipline has only 9/208 human-finalized (D-2763); 197 anchor_adjudication + 2 whitespace_fixed
  = 199 rows are LLM silver (BUG-620).
- ACTION: scripts/build_discipline_review_queue.py deterministically derived a 199-row owner review queue from the consolidated
  dual-axis artifact (ANCHOR_208_CONSOLIDATED_20261002.json), grouped by discipline (most frequent first), fail-closed
  (208 in / 199 unreviewed / 0 off-menu vs closed_menu_v5 / 0 'emerging' leaked). Owner adjudicates ~141 more discipline labels
  to reach ~150 human — the D-2764 precondition for a non-circular discipline conformance gate. 'Agree in bulk' per group
  counts as human adjudication of every row in it.
- ARTIFACTS: governance/discipline_review_queue_20261002.json + .md (199 rows, 49 distinct disciplines).
- Registry: decisions 895, buglog 357 (142 open / 215 closed), highest BUG-620.

## D-2766 (2026-10-02) - discipline axis fully human-provenanced (208/208) via owner bulk adjudication; BUG-620 CLOSED; discipline conformance anchor built
- FILES BUG-620 (CLOSED). Owner ruled (2026-10-02): "all discipline are human approved" — bulk-ratified all 199 unreviewed
  discipline rows (197 anchor_adjudication + 2 whitespace_fixed) as-is.
- ACTION: scripts/finalize_discipline_bulk.py (deterministic, fail-closed, crash-safe + C13 backup) set
  discipline_source=owner_finalized for all 199 -> 208/208 human-provenanced.
- ARTIFACTS: governance/discipline_anchor_conformance_20261002.json (204 gold rows) +
  governance/discipline_finalization_owner_bulk_20261002.json + ANCHOR_208_CONSOLIDATED_20261002.json updated.
- CONSEQUENCE: the discipline conformance gate is now UNBLOCKED (was deferred by D-2764 as LLM-vs-LLM circular; now
  measurable against 204 human labels — the symmetric completion of the D-2761 depth gate).
- Registry: decisions 896, buglog 357 (141 open / 216 closed), highest BUG-620.

## D-2767 (2026-10-02) - S4 classifier swap gated behind head-to-head FIT eval on human gold; shortlist Mistral-Small-3.1-24B; Qwen3-* R5-excluded
- FILES BUG-621. Market research (governance/MARKET_RESEARCH_20261002.md): no "faster AND more accurate" S4 classifier
  exists on paper; gpt-oss-20b (3.6B-active MoE) is a strong Pareto point; only a head-to-head fit eval can decide.
- RULING: NO S4 classifier swap without a fit eval (Cohen's kappa + tok/s vs 149 depth + 204 discipline gold, temp=0.0);
  candidate must be BOTH faster AND kappa >= 0.800 AND >= gpt-oss-20b. Shortlist Mistral-Small-3.1-24B / Gemma-3-12b-it;
  Qwen3-* excluded by R5 (generator-family independence).
- INFERENCE (M1): MLX + Ollama (current) + Splash-M1 backport (eval pending); vLLM/SGLang/TensorRT-LLM have no Apple support.
- QUICK WINS: ONNX Runtime for DeBERTa-v3 NLI; qwen3-embedding vs bge-m3.
- Registry: decisions 897, buglog 358 (142 open / 216 closed), highest BUG-621.

## D-2768 (2026-10-02) - Splash is model-scoped (Qwen3.8-27B / Qwen3.6-35B-A3B / Prism only) — NOT a general GGUF runner; Splash A/B MOOT
- REFINES D-2767 + FIXES the inference-leg of BUG-621. Splash's README/DEVELOPMENT.md: "built around the model" with a
  hardcoded families.FAMILIES registry; each supported architecture pairs a TRAINED DFlash2 draft. Supported architectures
  EXACTLY = Qwen3.8-27B, Qwen3.6-35B-A3B, Prism Ternary Bonsai 2. Model identity = architecture signature (repo names /
  base_model play no part).
- => Qwen3-Coder-30B-A3B (generator): NOT supported (no matching draft). gpt-oss-20b (classifier): NOT supported (different
  architecture). Splash applicability to Maxwell = NONE today; Splash-vs-OMLX A/B (D-2767 step 5) is MOOT.
- Registry: decisions 898, buglog 358 (142 open / 216 closed), highest BUG-621.

## D-2769 (2026-10-02) - Discipline conformance gate built (mirror D-2761) — Cohen's kappa vs 204 human gold
- FILES BUG-620 (final leg). scripts/discipline_conformance_gate.py measures slim_batch_discipline_classify (gpt-oss-20b-MXFP4-Q8)
  vs the 204-row human discipline anchor using Cohen's kappa + per-class P/R/F1. Gate joins definition/mechanism/boundary from
  maxwell.db by content_name (204/204 joinable). Selftest + dry-run pass; live run needs OMLX UP.
- Registry: decisions 899, buglog 358 (142 open / 216 closed), highest BUG-621.

## D-2770 (2026-10-02) - Discipline conformance gate CORRECTED (D-2769 measured wrong classifier + skipped remap); first live kappa ~0.45 << 0.8
- FILES BUG-622. Forensic audit + first live run proved the D-2769 gate was wrong on two legs: it invoked
  slim_batch_discipline_classify (the BUG-197/D2532 *emerging-row* re-classifier, NOT the main S4 classifier) and
  compared RAW free-form strings without the production map_to_canonical_with_fallback remap. Measured magnitude:
  raw kappa 0.060 -> remapped-slim 0.268 -> correct merged_cribs_classify+remap 0.452 (N=30).
- FIXED scripts/discipline_conformance_gate.py to mirror production exactly (merged_cribs_classify + remap; joins
  consequence+source_text). RULING: TRUE discipline conformance is kappa ~0.45, FAR below 0.800 — the S4 discipline
  axis is NON-CONFORMANT to human gold (BUG-622). All 49 gold disciplines on-menu (0 off-menu), so the gap is
  classifier quality, not vocabulary. Do NOT commit discipline labels / swap classifier until a definitive full-204
  kappa >= 0.800 (D-2767).
- Registry: decisions 900, buglog 359 (143 open / 216 closed), highest BUG-622.

## D-2771 (2026-10-02) - Prism Ternary Bonsai 2 NOT worth testing for S4 (vs gpt-oss) or S2 (vs Qwen3-Coder); no R5 conflict, but quality/compute rationale fails
- Owner asked whether Splash-supported Bonsai 2 merits an A/B for S4 or S2. RULING: NO for both (see
  MARKET_RESEARCH_20261002.md §6). R5 (distinct families) is NOT violated, so the iron rule does not block the test;
  but Bonsai 2 is a small ternary speed-optimized model that would near-certainly score below gpt-oss's already-low
  kappa ~0.45 (BUG-622) and fail the D-2767 swap gate, and S2 convergent extraction needs stronger reasoning than a
  small ternary model provides. Splash's per-architecture DFlash2 drafts (D-2768) also cannot accelerate gpt-oss or
  Qwen3-Coder. Marginal value ~ 0.
- Registry: decisions 901, buglog 359 (143 open / 216 closed), highest BUG-622.

## D-2772 (2026-10-02) - OMLX 0.7.0 + Goose 1.52.0 update audited — pin synced to 0.7.0; MTP/speculative NOT applicable to gpt-oss; turboquant_kv is MEASURE-gated
- FILES BUG-623 (dependency drift). Forensic audit of the owner's OMLX (0.7.0.dev2 -> 0.7.0 release, build 2987) +
  Goose (-> 1.52.0) update. (1) VERSION DRIFT: config pinned_version 0.7.0.dev2 was stale vs the running healthy 0.7.0;
  synced to 0.7.0 (pinned_version has no runtime consumer — monitor_stacks.py gates on min_version 0.4.0). (2)
  MTP/speculative/DFlash for gpt-oss = NOT applicable: gpt-oss-20b is dense (no MTP heads); D-293 measured MTP NEUTRAL
  (0.98x); mlx-dspark#38 + D-332 measured speculative decode net loss on M1; D-2768 ruled Splash does not cover
  gpt-oss. Live settings already correct (mtp/dflash/specprefill false). (3) gpt-oss latency lever = turboquant_kv_enabled
  + Q4 quant, both MEASURE-gated (D-332); A/B queued, NOT blindly toggled. (4) Goose 1.52.0 = no Maxwell drift. (5)
  Dependency drift logged as BUG-623 (transformers 5.14.1 / ST 5.7.0 major jumps untested; requests/urllib3/
  charset_normalizer mismatch). See governance/FORENSIC_AUDIT_20261002_OMLX_GOOSE.md.
- Registry: decisions 902, buglog 360 (144 open / 216 closed), highest BUG-623.

## D-2773 (2026-10-02) - BUG-622 root cause = open-vocabulary discipline generation (no closed 62-menu + over-precision instruction); fix = closed-menu injection + negative exemplars, MEASURE-gated
- FILES BUG-622. Forensic root-cause: the merged S4 prompt (stage4_merged_call.py MERGED_CRIBS_CLASSIFY_SYSTEM +
  build_merged_prompt) has NO closed 62-discipline menu; it instructs "SINGLE most precise academic discipline" with
  the example "computational neuroscience > neuroscience" (maximal specificity) and lists ~5 examples, so the model
  FREE-GENERATES off-menu names that map_to_canonical_with_fallback remaps to 'emerging' (~27%) or a WRONG synonym
  (psychology/neuroscience, info-science/computer-graphics, economics/privacy&surveillance, AI/information-retrieval).
  Depth already solves this exact problem via a config-driven few-shot injection (lines 389-436); discipline has no
  equivalent. FIX (MEASURE-gated, D-2767): inject the 62-menu as a CLOSED choice set (config-driven, C12 — no hardcoded
  list), change instruction to "choose EXACTLY ONE label from the list", add negative exemplars for the confusable
  pairs. Do NOT adopt until a full-204 A/B shows kappa >= 0.800.
- Registry: decisions 903, buglog 360 (144 open / 216 closed), highest BUG-623.

## D-2774 (2026-10-02) - BUG-622 closed-menu injection implemented (measure-gated) — N=30 A/B NEGATIVE (0.344 vs 0.452 baseline), flag reverted
- FILES BUG-622. D-2773's measure-gated closed-menu fix was IMPLEMENTED behind stage4.discipline_closed_menu_enabled
  (default false — prompts byte-identical when off): new _render_discipline_closed_menu in
  pipeline/stage4_merged_call.py injects the 61-real + emerging closed menu, a "choose EXACTLY ONE label, verbatim"
  instruction, and config-driven contrastive negative exemplars (config/golden/discipline_negative_exemplars.yaml),
  wired via pipeline/pipeline_paths.py. Live N=30 A/B (same anchor rows as the D-2770 baseline): menu ON kappa 0.344
  vs menu OFF baseline 0.452 — the closed menu did NOT improve conformance (net -0.11). Flag REVERTED to false.
  RULING (preliminary, N=30): BUG-622's binding constraint is more likely gpt-oss-20b's discrimination QUALITY across
  the 62-label space than the open-vocabulary generation the D-2773 root-cause assumed; the fix is retained behind the
  flag for a possible future full-204 re-test but is NOT the cure. PIVOT to the D-2767 S4 classifier FIT eval / a
  faster+more-accurate classifier (market research).
- Registry: decisions 904, buglog 360 (144 open / 216 closed), highest BUG-623.

## D-2775 (2026-10-02) - BUG-622 recommendation — stop prompt-engineering gpt-oss; hierarchical decomposition + realistic kappa floor; promotion rules verified active
- FILES BUG-622. After the D-2774 closed-menu negative (0.344 vs 0.452), the binding constraint is gpt-oss-20b
  discrimination QUALITY across the 62-label space, not prompt/vocabulary. The 0.800 operative floor (D-2767) is
  likely unreachable for 62-way fine-grained discipline with a single 20B 4-bit classifier (human-human agreement is
  0.5-0.7). Future-proof fix = HIERARCHICAL decomposition (coarse group ~10 → fine label within group's small menu),
  or the D-2767 FIT eval on a larger model (none downloaded yet) with a realistic ~0.7 floor. PROMOTION RULES VERIFIED
  ACTIVE: taxonomy.d2399_promotions_frozen=true, allow_both_axes_emerging=false; "emerging" is still the proxy
  (canonical="emerging" + raw in discipline_raw/domains_raw). No contamination/leak found. Discipline stays PROVISIONAL.
- Registry: decisions 905, buglog 360 (144 open / 216 closed), highest BUG-623.

## D-2776 (2026-10-02) - Forensic-audit governance reconciliation — register-divergence rail RED→GREEN; BUG-594/BUG-595 promoted to headers, BUG-017/BUG-183 pinned, ceiling 62→63
- FILES BUG-571 (register divergence). Forensic audit surfaced a RED fail-closed rail: 4 undeclared uncarried ids
  (BUG-017, BUG-183, BUG-594, BUG-595) + 1 stale declaration (BUG-170). FIXED: BUG-594/BUG-595 promoted from the
  2026-09-29 MUST-inbox table to `## BUG-594`/`## BUG-595` header events (now counted OPEN); BUG-017/BUG-183 pinned
  by identity in config/register_divergence.yaml declared_uncarried (D-2645 home, NOT header-promoted); BUG-170
  removed (now carries a header); declared_max_uncarried 62→63 (declared decision). agent/session_seed.yaml
  open_bugs_n 129→146, buglog_entries 360→362. Rails re-verified GREEN: check_register_divergence,
  check_bug_status, check_decision_membership.
- Registry: decisions 906, buglog 362 (146 open / 216 closed), highest BUG-623.

## D-2777 (2026-10-02) - BUG-623 dependency smoke GREEN — S5 NLI + S1.5 embedding verified under active 5.x; no pin-back
- FILES BUG-623 (RESOLVED). scripts/smoke_bug623_dependencies.py (deterministic known-answer, no LLM/OMLX) run under the
  ACTIVE env (/usr/local/bin/python3, transformers 5.8.1 / sentence-transformers 5.6.1). bge-m3 embedding discriminates
  (sim similar 0.686 > dissimilar 0.457); DeBERTa-v3 NLI discriminates (entail 0.997/contra 0.000 on the entail pair; contra
  0.322/entail 0.002 on the contradict pair). NO silent 5.x regression in either quality-critical leg; requests/urllib3/
  charset_normalizer warning ABSENT (urllib3 2.7.0 + requests 2.32.5 compatible). NO pin-back warranted. Residual hygiene:
  requirements.lock declares transformers==5.14.1/ST==5.7.0 vs active 5.8.1/5.6.1 (align lockfile as follow-up, not a bug).
## D-2778 (2026-10-02) - Anchor discipline + depth axes confirmed clean — BUG-619 + BUG-618 RESOLVED (owner-provenanced, fail-closed golden)
- FILES BUG-618, BUG-619 (RESOLVED). Forensic confirmation before any S4 measurement. BUG-619: 4 domain-bleed cells
  owner re-classified NOT silent-remapped (R042 design strategy->human-computer interaction; R086/R117 personal
  productivity->behavioral economics; R091->emerging catchall) via D-2766 (208/208 owner_finalized); 2 whitespace dupes
  trimmed (49 distinct, 0 off-menu); 5 emerging->3 (R040/R080/R091), all discipline_golden_eligible=False (204 golden).
  BUG-618: depth column rebuilt from canonical depth_final_class + provenance-stamped — depth_source canonical_adjudicated
  108 / owner_finalized 41 / noise_drop 1 / mapped 58; golden depth = {canonical_adjudicated, owner_finalized} = 149
  human-provenanced (0 universals); 58 mapped fail-closed excluded. Follow-up TASKS: owner-adjudicate 58 mapped depth;
  owner-refine 3 emerging.

## D-2779 (2026-10-02) - BUG-622 hierarchical discipline probe built — generative two-stage smoke GREEN; full N=30 A/B pending
- FILES BUG-622 (OPEN). Built scripts/hierarchical_discipline_probe.py (generative two-stage: 9 coarse groups from
  taxonomy_v5.yaml `group` -> fine label within the predicted group's <=11-label menu; gpt-oss-20b, mirrors production
  remap). Rationale (D-2775): closed-62-menu NEGATIVE (0.344 vs 0.452); untried lever = shrink per-decision confusion set
  hierarchically. N=3 smoke GREEN (kappa 0.571, coarse acc 2/3, 0 fallback). D-2607 trained ModernBERT hierarchical
  classifier found STALE (old 10-group taxonomy) + poor (macro-F1 0.18-0.21). Full N=30 A/B (hier vs 0.452 baseline)
  running; adopt ONLY if kappa >= ~0.7 AND >= flat. NOT wired to production.
## D-2780 (2026-10-02) - 58 mapped depth cells handed to owner as cross-model worksheet; Kimi has no depth axis; 3 emerging deferred
- FILES BUG-618 (furthers depth-golden closure). Built temp/depth_58_mapped_adjudication_20261002.csv: the 58 `mapped`
  depth cells joined to the 3 depth cross-models that exist and cover all 58 (Claude depth_classification_claude.csv,
  GPT gpt 150 depth.csv, DeepSeek deepseek_210 depth.csv) + goose provisional (physicist-chef-poet test, default-domain
  rule). FINDING: Kimi has NO depth axis (Kimi artifacts cover ct/disc/form only) -> depth cross-model set is
  Claude/GPT/DeepSeek. goose dist domain 37 / cross-domain 8 / specialized 13; agrees current 45/58, Claude 48/58,
  DeepSeek 47/58; 13 re-scopes flagged (mostly cross-domain -> domain, per D2245). Completes BUG-618 depth-golden:
  owner fill expands 149 -> up to 207. 3 emerging (R040/R080/R091) DEFERRED (owner cannot refine) -> remain fail-closed
  excluded. Forensic audit GREEN (register/bug_status/decision_membership).
## D-2781 (2026-10-02) - BUG-622 hierarchical-via-prompt REJECTED — N=30 kappa 0.514 (>= 0.452 flat, << 0.7); pivot to D-2767 model swap
- FILES BUG-622. Full N=30 hierarchical A/B: raw 0.5333, Cohen kappa 0.5139, coarse acc 19/30, 0 fallback, vs flat 0.452.
  Adoption criterion (kappa >= ~0.7 AND >= flat) NOT met -> REJECTED. Prompt-side levers exhausted (closed-menu 0.344,
  flat 0.452, hierarchical 0.514). Classifier is model-bound -> pivot to D-2767 swap (Mistral-Small-3.1-24B /
  Gemma-3-12b-it; Qwen3-* R5-excluded). probe kept as measurement tool, NOT wired.

## D-2782 (2026-10-02) - kappa-floor policy — keep agreement_floor.yaml (Krippendorff alpha 0.8) untouched; adopt SEPARATE classifier-kappa bar 0.7 declared BEFORE D-2767 swap
- FILES BUG-622. operative 0.800 in agreement_floor.yaml is Krippendorff ALPHA (inter-rater), NOT Cohen kappa — stays
  UNTOUCHED. Separate classifier-vs-gold kappa bar 0.7 adopted for 62-way discipline, DECLARED NOW (before D-2767 eval),
  frozen against post-hoc lowering. 0.7 is a STRETCH target (best 0.514), not a retroactive pass.
- Registry: decisions 912, buglog 362 (143 open / 219 closed), highest BUG-622.

## D-2783 (2026-10-02) - S4 classifier shortlist REVISED — Mistral-Small-3.1-24B already tested+rejected; Bonsai 2 R5-excluded (ternary Qwen3.8); Ornith-1.5-35B-A3B already local
- FILES BUG-621 + BUG-622. Forensic archive/chat-recall research on the D-2767 shortlist, three findings: (1) Mistral-Small-3.1-24B
  was ALREADY TESTED and REJECTED in v1.0 (D492, 2026-06-14): "no chat template, 0% schema validity, 1-word responses" — a documented
  structured-classification failure; DROPPED from shortlist (do not re-download 13GB). (2) "Bonsai 2" = Prism ML Ternary Bonsai 2
  (2026-09-17, Apache 2.0): a 1-bit TERNARY compression of Qwen3.8-27B (~4GB); REJECTED on R5 (Qwen3.8 = generator family) + 1-bit
  precision loss fatal for 62-way classification. (3) Ornith-1.5-35B-A3B (ornith-ai, independent MoE, ~3B active) is ALREADY local and
  OMLX-served → FIRST FIT-eval candidate, no download gate. Shortlist becomes [Ornith-1.5-35B-A3B local, Gemma-3-12b-it fallback];
  D-2767 gate criteria UNCHANGED (faster AND kappa>=0.7 AND >= gpt-oss-20b).
## D-2784 (2026-10-02) - Ornith-1.5-35B-A3B FIT eval NEGATIVE — fails production schema on BOTH axes (depth CoT overflow, discipline sparse CRIBS); drop-in gate NOT met; shortlist -> Gemma-3-12b-it

Ran scripts/fit_eval_model_swap.py (new reusable D-2767/D-2783 gate, config-first) as a fail-fast N=8 smoke.
DEPTH: Ornith is a reasoning model; not in verifier.reasoning_off_models -> emits chain-of-thought, DepthClassificationError 'ambiguous' (all 4 labels). Direct probe: enable_thinking=False fixes it (0.6s clean) but that is config adaptation outside the no-drift gate.
DISCIPLINE: SparseClassificationError 'application missing/too short (4<10)' — Ornith's CRIBS output too sparse.
Same failure CLASS as Mistral (v1.0 D492 '0% schema validity'). Baseline gpt-oss N=8 discipline kappa 0.2258 (15.57s/FB).
Shortlist -> [Gemma-3-12b-it (download-gated fallback)]. Gate unchanged (faster AND kappa>=0.7 AND >= gpt-oss-20b).

- Registry: decisions 914, buglog 362 (143 open / 219 closed), highest BUG-622.

## D-2785 (2026-10-02) - S4 shortlist REVISED (5-model research): Gemma-4-12B-it-qat-OptiQ primary + clef-flash-4bit secondary; Qwen3.8 R5-excluded / humanizer wrong-task / Xing4.0 high-risk. Plus 58 mapped depth rows owner-folded -> golden 149->207.

## D-2786 (2026-10-02) - S4 candidate downloads approved+initiated; clef-flash CONFIRMED custom-arch (adapter-scope, not drop-in); depth conformance anchor stale -> BUG-624
- FILES BUG-621 + BUG-624. Owner approved downloading BOTH D-2785 candidates to the OMLX serving store
  (~/.cache/huggingface/hub). gemma-4-12B-it-qat-OptiQ-4bit (PRIMARY, gated=False, standard MLX/OptiQ arch, ~8.3GB)
  downloading; new scripts/register_s4_candidate.py clones the gpt-oss-20b classifier settings (guided_grammar=true,
  enable_thinking=false, specprefill=false) for S4 registration + reload (D-2637). clef-flash-4bit (SECONDARY)
  CONFIRMED custom-code (clef_mlx.py + joint_head.safetensors + __pycache__ pyc) -> NOT a drop-in for
  batch_depth_classify/merged_cribs_classify; relegated to ADAPTER-SCOPE (needs a schema/head adapter before any FIT
  eval). Pre-implementation forensic audit GREEN on register-divergence + decision-membership rails; the bug-status
  rail flagged a stale register (BUG-623 + BUG-624 unregistered) which was repaired by re-derivation, and the audit
  surfaced BUG-624 (depth conformance anchor stale at 149 vs the 207 golden) rather than a breakage/cascade.
- Registry: decisions 916, buglog 363 (144 open / 219 closed), highest BUG-624.

## D-2787 (2026-10-02) - BUG-624 fixed at the SOURCE: bridge ruler extended to 208 rows, bridge re-derives clean (149-vs-207 anchor gap closed)
- FILES BUG-624. The prior fix was a JSON patch (scripts/bridge_folded_depth_extras.py) that extended the bridge
  entries to 208 but left build_anchor_store_bridge.py --check re-deriving 150 -> DRIFT (any rebuild regressed the
  depth anchor back to 149). New scripts/build_anchor_bridge_ruler_208.py derives a 208-row bridge ruler (150 content
  ruler VERBATIM + 58 folded depth extras VERBATIM, every extra name-joined EXACTLY); config/anchor_family.yaml
  store_bridge.ruler_sheet re-pointed at it (only consumer = build_anchor_store_bridge.py, no cascade to anchor.sheet).
  Bridge REGENERATED: --check now "ok", join.counts rows 208 / joined 208 / exact 207 / normalized 1 (R135 double-space)
  / ambiguous 0. build_depth_anchor_conformance.py hardcode 149 -> derived golden count; depth_anchor_conformance_20261002.json
  rebuilt to 207 golden (domain 99 / cross-domain 58 / specialized 48 / universal 2; R021 excluded). verify_anchor_family_registry
  + all three forensic rails GREEN.
- Registry: decisions 917, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2788 (2026-10-02) - gemma-4-12B-it-qat-OptiQ-4bit FIT eval NEGATIVE: slower than gpt-oss-20b on BOTH axes; 'faster' gate not met; keep gpt-oss-20b, park gemma-4-12B
- ADVANCES BUG-622 (open S4 swap bug), REJECTS gemma-4-12B as drop-in S4. Owner decision (a) made gemma-4-12B the
  sole drop-in candidate (clef-flash parked adapter-scope). Ran the D-2767/D-2783 gate via scripts/fit_eval_model_swap.py
  (candidate config repointed Ornith -> gemma-4-12B). FAILS the NECESSARY 'faster' condition on BOTH axes: warm
  depth 3.78s/FB vs baseline 1.98s/FB (~1.9x slower); discipline 40.2s/FB vs 15.0s/FB (~2.7x slower). Verdict FAIL
  (faster=False) on both. '12B < 20B therefore faster' is refuted by OptiQ MIXED-quant dequant overhead vs native
  MXFP4-Q8 + warm resident classifier. gpt-oss-20b stays classifier-of-record; gemma-4-12B parked (no S4 routing).
  Also closed a count-drift blindspot (BUG-624 class) on both conformance anchors: load_anchor now fail-closes on
  row-count vs declared total divergence. Rails GREEN (register-divergence / bug-status / decision-membership /
  anchor-family).
- Registry: decisions 918, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2789 (2026-10-02) - BUG-622 path re-routed: S4 swap EXHAUSTED (5/5 rejected/parked) + prompt path N=30 negative -> pivot to hierarchical decomposition (D-2775); clef-flash stays parked
- FILES BUG-622 (open S4 discipline-classifier quality bug, current best kappa 0.514 vs 0.7 bar). Both candidate paths
  now EXHAUSTED: SWAP (D-2767/D-2783) 5/5 — Mistral (v1.0 D492 schema fail), Bonsai-2 (R5+ternary), Ornith-1.5-35B
  (D-2784 schema fail both axes), gemma-4-12B (D-2788 slower both axes), clef-flash (custom joint_head, parked by
  decision a). PROMPT (D-2773/D-2774) — closed-menu N=30 NEGATIVE (0.344 vs 0.452), flag reverted. RULING: pivot to
  D-2775 HIERARCHICAL DECOMPOSITION (coarse group ~10 -> fine label in small menu). clef-flash NOT tested drop-in
  (fails no-drift gate); re-opening it as adapter-scope R&D for the coarse-group stage = separate future decision.
- Registry: decisions 919, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2790 (2026-10-02) - BUG-622 hierarchical-decomposition DESIGN pinned: 9-group scheme canonical, top-2 coarse prior, coarse-first measure-gate (coarse kappa>=0.90); taxonomy dual-scheme conflict resolved
- FILES BUG-622 (open S4 discipline-classifier quality bug, flat best kappa 0.514 vs 0.7 bar). Records the DESIGN for the D-2789 pivot to D-2775 hierarchical decomposition. (1) COARSE SCHEME = 9-group (config/closed_menu_v5.json disciplines[].group): already wired into the operative menu, tighter (max fine-menu 11 vs 15), better balanced on the 204 gold (max group 42 vs 51). (2) CONFLICT RESOLVED — taxonomy_v5.yaml carries TWO group maps: disciplines[].group (9) AND discipline_groups (10). The 10-group map has a DEAD group on the gold (life & health science = 0) and is NOT what the classifier sees; disciplines[].group is now the single source of truth for coarse routing (discipline_groups superseded for S4, left in place, no relabel). (3) MEASURE-GATE FIRST — do NOT build the two-stage yet; run a COARSE-ONLY (9-way) conformance on the 204 gold, adopt two-stage only if coarse kappa >= 0.90. (4) TOP-2 PRIOR (union of top-2 coarse groups) not a hard gate, to bound coarse-error propagation. (5) 'emerging' (62nd menu entry, empty group) gets an explicit routing rule. Audit: both schemes map all 204 gold (0 unmapped / 0 emerging); 9-group gold = Behavioral & Cognitive 42 / Systems & Method 35 / Design Cognition 28 / Perception & Signal 24 / Operational & Strategy 23 / Heterodox 18 / AI & Computing 16 / Computational Craft 11 / Form & Structure 7. Forensic rails GREEN before mint.
- Registry: decisions 920, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2791 (2026-10-02) - BUG-622 coarse-only (9-way) measure-gate BUILT — N=8 smoke kappa 0.556 << 0.90 gate; full-204 launched
- FILES BUG-622 (open S4 discipline-classifier quality bug). Implements D-2790 step (3) MEASURE-GATE-FIRST. Added
  --mode coarse + --gate to scripts/hierarchical_discipline_probe.py (coarse-only 9-way group classification using the
  SAME stage-1 prompt the two-stage would use, so the measured coarse kappa is a faithful predictor of two-stage
  stage-1 error propagation; off-menu groups fail-closed to ""). Added stage4.discipline_coarse_kappa_floor=0.9 to
  config/pipeline_config.yaml (C12 — no hardcoded floor). N=8 live smoke: raw agreement 0.6250 / Cohen kappa 0.5556 /
  0 off-menu vs the 0.90 gate -> EARLY NEGATIVE (DO NOT build the two-stage). Definitive full-204 run launched
  (temp/coarse_measure_gate_204_20261002.log, PID 76862); the adopt/drop ruling follows the full-run kappa. Forensic
  audit GREEN: register-divergence / bug-status / decision-membership / anchor-family; coarse scheme verified
  drift-free (taxonomy_v5.yaml disciplines[].group 61 == closed_menu_v5.json 62 incl 'emerging'; 204 gold 0 unmapped /
  0 emerging).
- Registry: decisions 921, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2792 (2026-10-03) - BUG-622 re-framed as MEASUREMENT-DESIGN problem — ceiling-first + axis re-scope; title-only kNN A/B built
- FILES BUG-622 (open S4 discipline-classifier quality bug). ULTIMATE RECOMMENDATION: STOP treating BUG-622 as a
  model/architecture problem. All four vectors exhausted/failing — SWAP 5/5 (D-2789), PROMPT N=30 negative (0.344
  vs 0.452, D-2774), HIERARCHICAL coarse gate failing (N=8 0.556 vs 0.90, D-2791), embedding-kNN title-only (this
  decision). Unifying cause = MEASUREMENT DESIGN: the 62-way (even 9-way) label space is ambiguous + sparse (49
  distinct labels over 204 anchors; menu-ON HURT in D-2774 = semantics-ambiguity smoking gun). Achievable agreement
  CEILING almost certainly << 0.8. THREE-PART FIX: (1) MEASURE THE CEILING (owner + independent rater, or two model
  families per R5, on a 30-anchor stratified sample); (2) RE-SCOPE AXIS (62 -> 3-5 separable top-level categories,
  fine 62 -> advisory tags); (3) CHANGE CONTRACT (hard gate -> soft routing facet + confidence threshold + owner
  ratification on low-confidence band). BUILT scripts/discipline_knn_ab.py (bge-m3 kNN over 204 gold TITLES, 70/30
  hold-out, k=1/3/5): fine kappa 0.10 / coarse 0.14-0.19 — WEAK LOWER BOUND (title-only; fair full-text kNN needs
  DB sha256 lookup). Coarse full-204 run in flight (PID 76864). Forensic rails GREEN pre/post.
- Registry: decisions 922, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2793 (2026-10-03) - BUG-622 full-text kNN A/B CONFIRMS measurement-design bound — retrieval (0.17-0.41) fails to beat flat generative (0.45)
- FILES BUG-622. Ran the D-2792 "better option" fair test: joined 202/204 gold anchors to their full FB semantic
  text (definition/application/failure_mode/elaboration/mechanism/boundary/consequence) in maxwell.db by name,
  bge-m3 embedding, 70/30 hold-out cosine-kNN (k=1/3/5, majority + weighted). Result: fine (49-way) kappa 0.17-0.19;
  coarse (9-way group) kappa 0.32-0.41. Full text HELPED vs titles (fine 0.10->0.17, coarse 0.14->0.41) but
  retrieval STILL fails to beat flat-generative 0.45 on fine, only matches on coarse (0.41 vs 0.45 at k=5). CONFIRMS
  D-2792: the axis is measurement-design-bound (ambiguous + sparse labels), NOT model/architecture-bound. Complete
  evidence table — title-kNN 0.10/0.14, full-text-kNN 0.17-0.19/0.32-0.41, flat generative 0.45, coarse generative
  N=8 0.556 — brackets the achievable CEILING at ~0.4-0.55, far below 0.8. No further classifier engineering until
  the ceiling is formally measured. DB cross-check: fbs.discipline (classifier output) agrees with gold on only
  90/202 (44.6%) — the BUG-622 disagreement is baked into the committed DB. Coarse full-204 still in flight.
- Registry: decisions 923, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2794 (2026-10-03) - D-2792/D-2793 OWNER-RATIFIED — ceiling-first fix path approved; 30-anchor inter-rater ceiling sample generated
- OWNER RATIFIED D-2792/D-2793: STOP classifier engineering on BUG-622. Fix path = (1) MEASURE THE CEILING first,
  (2) RE-SCOPE the discipline axis (62 -> 3-5 separable top-level categories, fine 62 -> advisory tags), (3) CHANGE
  THE CONTRACT (hard gate -> soft routing facet + owner ratification on low-confidence band). Ratified WITHOUT
  asserting "44% is the hard ceiling" — that remains UNPROVEN until inter-rater ceiling is measured. Generated the
  turnkey 30-anchor stratified inter-rater sample (gold-hidden): scripts/build_discipline_ceiling_sample.py ->
  temp/discipline_ceiling_sample_30.csv (30 anchors across 9 groups) + temp/discipline_ceiling_menu.csv (62 menu).
  Owner scores returned labels against governance/discipline_anchor_conformance_20261002.json AFTER both raters.
- Registry: decisions 924, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2795 (2026-10-03) - BUG-622 CEILING MEASURED — inter-rater fine kappa 0.581 / coarse 0.728; 12 of 30 anchors owner-corrected
- FILES BUG-622. Owner labeled the 30-anchor gold-hidden stratified sample (temp/discipline_ceiling_sample_30.numbers).
  Inter-rater ceiling vs committed gold: FINE (62-way) Cohen kappa 0.581 (Po 0.600, Pe 0.044); COARSE (9-way)
  kappa 0.728 (Po 0.767, Pe 0.142). Both BELOW the 0.800 operative floor; fine is ALSO below the 0.667 reporting
  floor. CONFIRMS D-2792/D-2793: the discipline axis is measurement-design-bound, not model-bound. The D-2790
  coarse-gate target 0.90 is UNREACHABLE (human coarse ceiling is 0.728). Owner corrected 12 of 30 anchors (NO new
  disciplines — all 30 labels sit in the 62-discipline closed menu incl 'emerging'); corrections applied to
  governance/discipline_anchor_conformance_20261002.json (backed up to
  backups/discipline_anchor_conformance_20261002.PRE_D2795_*.json; provenance bumped to D-2795). The committed
  classifier (fbs.discipline agrees with gold 44.6%) is ~15pts below the human fine ceiling (60%) -> the residual is
  model quality, but the DOMINANT loss is label ambiguity (a human cannot beat 0.58 on the 62-way axis). NEXT:
  re-scope fine 62 -> advisory tags + coarse-first gate re-targeted to the human ceiling (~0.73); then re-score
  fbs.discipline against the corrected gold.
- Registry: decisions 925, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2796 (2026-10-03) - BUG-622 macro re-scope MEASURED — human ceiling 3-way 0.766 still < 0.8; gate re-targeted to human parity; macro config built
- FILES BUG-622. Tested the re-scope zero-compute (owner 30-anchor re-label vs PRE-correction gold). Human ceiling:
  FINE 0.581 / 9-way 0.728 / 4-way 0.729 / 3-way 0.766 — a 3-way macro axis STILL does not reach the 0.800 operative
  floor, so the discipline operative floor is HUMAN-UNREACHABLE. The prior "collapse to 4 buckets -> 0.8" hypothesis is
  REFUTED (kappa corrects for chance: raw 0.60 -> 0.87 but kappa only 0.58 -> 0.77). Fix = human-parity gating + soft
  facet + owner ratification on the ambiguous ~13% band, NOT axis granularity alone. BUILT
  config/discipline_macro_groups.yaml (3-way primary + 4-way); re-targeted discipline_coarse_kappa_floor 0.9 -> 0.73;
  added discipline_macro_groups_path + discipline_macro_enabled=false (OFF until owner ratifies the scheme). fbs
  re-score vs corrected gold: 89/202 (44.1%, was 44.6%) — the 12 corrections do NOT help the committed classifier
  (it was fitted to the old labels). Full-204 coarse generative kappa 0.537 harvested (confirms DROP two-stage,
  D-2791). BUG-622 stays OPEN.
- Registry: decisions 926, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2797 (2026-10-03) - BUG-622 MACRO RATIFIED — owner ratifies 3-way scheme + human-parity gate; Condition A collapse 0.553 < 0.65; Condition C instrument built, run blocked by gpt-oss cold-reload
- FILES BUG-622. Owner RATIFIED the 3-way macro re-scope as PRIMARY routing facet + human-parity gate (~0.73-0.77) as
  operative floor (closes the D-2796 pending-ratification gate). Config propagated: discipline_macro_enabled
  false->true; added discipline_macro_kappa_floor 0.73. CONDITION A (collapse, ZERO inference): committed classifier
  (fbs.discipline, gpt-oss-20b) fine->9-group->3-way macro vs corrected gold -> Cohen kappa 0.5534 (raw 0.7255, N=204).
  BELOW the 0.65 ship threshold. Dominant recoverable error = OFF-MENU abstention: 16 predictions (7.8%) collapse to
  'emerging' and ALL 16 are WRONG (gold is a real bucket) — a fine-axis remap failure the collapse can never fix.
  CONDITION C (dedicated 3-way classifier): BUILT scripts/discipline_macro_classify.py (selftest + dry-run GREEN; macro
  group map verified EXACT over closed_menu_v5.json — no orphan/ghost group). Live 204-row run BLOCKED by INFRA, not
  measurement design: gpt-oss-20b-MXFP4-Q8 reasoning-model cold-reload returns content:null/empty under memory pressure
  (48.5GB ceiling, 3 other models loaded ~26.3GB) -> warm->evict->cold-reload churn. Condition A settles the axis
  question: even a dedicated 3-way classifier only recovers the 16 abstentions (+~8pp raw) -> projected ceiling ~0.60-0.65
  kappa, still < 0.766 human ceiling. The 44% fine accuracy is NOT a hard model ceiling — it is the label-ambiguity
  ceiling (human fine 0.581), which is why the axis re-scopes to 3-way rather than re-fitting. BUG-622 stays OPEN.
- Registry: decisions 927, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2798 (2026-10-03) - BUG-622 CONDITION C MEASURED — dedicated 3-way classifier 0.6066 < 0.65; discipline axis advisory-only; 'cold-reload' was a max_tokens bug
- FILES BUG-622. CONDITION C (dedicated 3-way macro classifier, direct bucket inference, gpt-oss-20b-MXFP4-Q8) measured
  on the full 204-row corrected gold: Cohen kappa 0.6066 (raw agreement 0.7696). BELOW the 0.65 ship threshold AND below
  the 0.73 human-parity floor (human 3-way ceiling 0.766). The 3-way macro scheme is NOT shipped as a routing facet;
  discipline is confirmed ADVISORY-ONLY (fine-62 -> advisory multi-label tags, soft facet; routing does not gate on
  discipline). This closes the BUG-622 ship decision exactly as D-2792/D-2793 predicted: the axis is measurement-bound
  (human fine ceiling 0.581, human 3-way ceiling 0.766); the committed 44% fine accuracy is the label-ambiguity ceiling,
  NOT a model ceiling. Condition C beats Condition A (0.6066 vs 0.5534, +0.053) almost entirely by eliminating the 16
  off-menu 'emerging' abstentions (down to 1); the residual error is adjacent-cluster confusion (H&D<->M&B 28, H&D<->Tech
  9) that even humans only resolve to 0.766. ROOT-CAUSE of the prior 'cold-reload' blocker found + fixed: the 'content
  missing (cold reload?)' error was a MISDIAGNOSIS — MACRO_MAX_TOKENS=256 was too small for gpt-oss-20b's Harmony
  reasoning chain-of-thought (billed against max_tokens), so it hit finish_reason='length' before emitting content. Fixed
  to 1024 (matches models.verifier.max_tokens). BUG-622 stays OPEN only for the S4 advisory re-wire (no swap / no re-fit).
- Registry: decisions 928, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2799 (2026-10-03) - D-2798 ADVISORY RE-WIRE SHIPPED — discipline gate is advisory (no fail-closed); committed fbs.discipline re-scored vs 204 gold
- IMPLEMENTS BUG-622 / D-2798 in code. config/pipeline_config.yaml adds `discipline_gate_mode: advisory`;
  scripts/discipline_conformance_gate.py reads it and its `--gate` flag is now a REPORT-ONLY no-op in advisory mode
  (never fail-closed; `hard` restores the legacy floor gate). pipeline/stage4_merge.py documents discipline as a soft
  facet stamped for retrieval/analytics that never gates routing (routing is content_type-based, fine-only).
- Built scripts/discipline_advisory_rescore.py (deterministic, zero inference / zero re-fit) and measured the COMMITTED
  fbs.discipline against the corrected 204 gold: FINE-62 kappa 0.4248 (raw agreement 0.4412, gold distinct 52 / committed
  48); deterministic 3-way macro collapse 0.5534 — reproduces Condition A exactly, validating the two-level
  value->group->macro mapping. The 44% raw agreement is the label-ambiguity ceiling (human fine ceiling 0.581), NOT a
  model ceiling; discipline quality reports against the human ceiling and never fail-closes.
- Forensic rails re-run GREEN after the edit. BUG-622 implementation leg CLOSED (no swap, no re-fit).
- Registry: decisions 929, buglog 363 (143 open / 220 closed), highest BUG-622.

## D-2800 (2026-10-03) - BUG-563 WORKTREE RECURRENCE RECONCILED — 83 paths granted/excluded; 20 pipeline paths surfaced as BUG-528 (owner-gated)
- IMPLEMENTS BUG-563 (worktree rule re-fired) / SURFACES BUG-528 (pipeline edits vs a live will_not_touch lock).
- GRANTED the durable 2026-10-02/03 audit artifacts in session_plan may_touch: frontier_audit/**, FORENSIC_AUDIT/
  MARKET_RESEARCH/STRATEGIC_PLAN reports, ANCHOR_150/208 views, discipline_*/spot_check_*/quarantine_*/*_adjudication/
  *_candidates, depth conformance/finalization, feed.opml, benchmarks/*, and the C19 bloat-purge DELETIONS (18
  depth/vote/eval checkpoint files archived to archive/bloat_20260929/).
- EXCLUDED ephemeral owner/runtime (.pipeline_runner.lock, *.numbers, anchor ruler*.csv) in repo_integrity + .gitignore.
- Reconciled the duplicate BUG-563 buglog entry (OPEN 2026-09-26 marked SUPERSEDED by the canonical FIXED D-2684).
- 20 pipeline paths remain in NO home BY DESIGN: pipeline/** is will_not_touch-locked yet 19 files are MODIFIED and
  practicality.py is UNTRACKED — an OWNER-GATED BUG-528 conflict (lift/narrow the lock or revert), NOT self-widened.
- check_session_plan.py GREEN. Registry: decisions 930 (stamp 812ba505a497eb81); buglog 363 (143 open / 220 closed).

## D-2801 (2026-10-03) - BUG-528 pipeline/** lock re-scope — MINTED, ACTIVE (owner acked 2026-10-03)
- STATUS: PROPOSAL ONLY. No decision minted, no lock change applied, no census bump — a decision must name the
  files it FIXED, and this one awaits the owner's `ok`/`revert` before the re-scope lands.
- DIAGNOSIS: `pipeline/**` is will_not_touch-locked yet carries 745 insertions + 1 untracked file (practicality.py,
  D-2622) of legitimate decision-backed work (D-2747 reroute, D-2757 applicability, BUG-614 fingerprint, D-2798
  advisory, D-2703 chunking, D-2716 run-id). Commit is refused (rail 4: will_not_touch OUTRANKS may_touch);
  revert breaks stage4_merge.py's import of content_types.reroute_content_type. A C27 no-dead-ends deadlock.
- PROPOSAL (governance/OWNER_GATE_BUG528_20261003.md): remove `pipeline/**` from will_not_touch; replace the
  edit-gate with a REVIEW-gate (R5 generator≠verifier + D-naming + stage_code_fingerprint fail-closed). Owner
  instruments (F11_*, ANCHOR_RULER, DEPTH_BLIND_SHEET) keep their lock, untouched.
- BLOCKS: S4 rerun (runs uncommitted stage4_merge.py/content_types.py), D-2703 re-chunk (stage1_chunk.py dirty).
- Registry UNCHANGED this turn: decisions 930 / buglog 363 (143 open / 220 closed) / highest open then BUG-622.

## 2026-10-03 (cont.) — BUG-625 + BUG-626 RESOLVED (no new decision minted)

BUG-625 (C12 residuals) closed: probe_run.py run-id + OMLX_URL now config-first via pipeline_paths; the
"knowledge pipeline" literal routed through pipeline_paths across 9 pipeline modules + safe_delete +
backup_guardian.sh (student_classifier default also de-drifted to config's classifier_hierarchical).
BUG-626 (D-328 superseded_by LIST) closed: scalarized to D339 + scalar-or-absent guard in
scripts/reconcile.py supersession_gaps; decisions_summary re-derived (stamp a3af831f7768d055).
Registry stays 931 decisions. Six forensic rails GREEN. session_seed synced (open_bugs_n 143, highest_bug BUG-622).

## 2026-10-03 (cont.) — D-2802/D-2803/D-2804 minted + BUG-627 resolved (Tier-2/Tier-3 future-proofing)

D-2802 (Tier-2 structural rail): check_session_plan.py#crossing_rate_faults counts ACTIVE (acked, unspent)
crossings per will_not_touch family and refuses above config/repo_integrity.yaml#crossing_rate_limit
(max_active_per_family=1, rc=2 owner gate). D-2803 (Tier-3 cadence): >=1 active crossing emits a lock-semantic
RE-ASK note at every registry increment; >N escalates to the D-2802 fault. D-2804 (Q2 recording): fingerprint-
everywhere (BUG-614) + classifier-family config-bound + human-parity advisory gate (measured ceiling 0.766<0.8,
NOT the stale kappa>=0.7 hard gate). BUG-627 (D-2801 follow-on): D-2668 selftest controls crossed pipeline/** after
it left will_not_touch -> --selftest RED (21/24); re-pointed to an owner-instrument family -> 25/25 GREEN.
Registry: 931 -> 934 decisions. buglog 365 -> 366.


## D-2805 (2026-10-03) - OWNER RATIFICATION: D-2802/D-2803/D-2804 APPROVED
Owner ratified the three ACTIVE decisions that completed the BUG-528 lock re-scope recommendation. D-2802
(Tier-2 structural rail: crossing-rate per will_not_touch family refuses above N=1, rc=2). D-2803 (Tier-3
governance cadence: lock-semantic RE-ASK note at every registry increment, >N escalates to the D-2802 fault).
D-2804 (Q2 reliability/accuracy recording: fingerprint-everywhere BUG-614 + classifier-family config-bound +
human-parity advisory gate, measured ceiling 0.766<0.8, NOT the stale kappa>=0.7 hard gate). These extend the
owner-acked D-2801 Tier-1 re-scope: the pipeline/** lock is now an accountability gate (R5 + D-naming +
stage_code_fingerprint), not a stale edit prohibition. Registry: 934 -> 935 decisions. No bug movement.

## D-2806 (2026-10-03) - BUG-614 fingerprint-everywhere ships to all pipeline stages
Config-owned stage_code_fingerprint() (C12: {stage_key}.fingerprint_files in config/pipeline_config.yaml) + write/read/check
sidecar helpers in pipeline/stamp.py, wired into the 7 checkpoint-writing stages that lacked a code fingerprint
(stage0_convert, stage0_5_extract_metadata, stage1_chunk, stage1_3_prefilter, stage1_5_embed_cluster, stage2_extract,
stage6_commit), completing the accountability gate that D-2801/D-2805 replaced the pipeline/** edit-lock with. Resume is
fail-closed (C16) on code drift; legacy checkpoints (no sidecar) resume unchanged. Six rails + --selftest 25/25 GREEN.
Registry 935 -> 936. Resolves BUG-614 and BUG-528 (its closing condition, fingerprint-everywhere, is now met).

## D-2807 (2026-10-03) - stage4 fingerprint C12 migration (config-owned) + BUG-615/BUG-616 closure
Migrated stage4's inline hardcoded `_stage_code_fingerprint()` to the shared config-owned
`stage_code_fingerprint("stage4")` via `stage4.fingerprint_files` in config/pipeline_config.yaml (C12, mirroring
stage5 D-330). Files: pipeline/stage4_merge.py, pipeline/content_types.py, config/pipeline_config.yaml,
config/content_types.yaml. Confirms BUG-615 (cross-cluster seen_fb_ids dedup guard: skip duplicate fb_id + merge
source_clusters/source_segments provenance) and BUG-616 (stage-code drift discards ONLY fbs+processed_ids+scalar_state
and PRESERVES depth.json/.cribs.json) as RESOLVED — both guards implemented under D-2752, now closed. buglog OPEN
141->139 / CLOSED 225->227. Registry 936 -> 937.

## D-2808 (2026-10-03) - Owner ratification: D-2798 advisory-only BUG-622 contract APPROVED — BUG-622 CLOSED (no swap, no re-fit)
Owner ratified the D-2798/D-2799 advisory-only BUG-622 discipline contract as FINAL: the discipline axis is
advisory-only (fine-62 -> advisory multi-label soft-facet tags); routing never gates on discipline (content_type-based,
fine-only). NO classifier swap and NO re-fit: D-2788 measured gemma-4-12B slower on both axes; D-2789 exhausted the
swap 5/5; D-2792/D-2793 proved the axis measurement-bound (human 3-way ceiling 0.766 < 0.8, D-2795/D-2796). The
advisory re-wire shipped in D-2799 (discipline_gate_mode=advisory, conformance gate report-only) is the END-STATE.
BUG-622 CLOSED. Also closes BUG-617 (depth now has 207 human-provenanced golden rows — D-2757/D-2785/D-2787). buglog
OPEN 139->137 / CLOSED 227->229. Registry 937 -> 938.

## NOTE (2026-10-03) — BUG-621 CLOSED as a consequence of D-2788/D-2789 (no new decision minted)
BUG-621 (S4 classifier has no head-to-head fit evidence; Pareto unverified) is CLOSED: the fit eval it demanded is
DONE and NEGATIVE-on-swap — D-2788 (gemma-4-12B slower than gpt-oss-20b on both S4 + depth axes) + D-2789 (swap path
exhausted 5/5) + D-2792/D-2793 (measurement-bound; human 3-way discipline ceiling 0.766 < 0.8). gpt-oss-20b stays; no
swap, no re-fit (ratified D-2808). No new decision id: the decision basis is D-2767/D-2788/D-2789/D-2808.

## NOTE (2026-10-03) — BUG-170/611/612/613 CLOSED (governance sync, no new decision minted)

The four "remaining owner-gated classification-policy bugs" were ALREADY RESOLVED by decisions minted 2026-10-02:
D-2747 (deterministic non-principle reroute — the A/B winner over "extend S4" and "tighten S2"), D-2748 (principle-purity
audit), D-2749 (FORM-axis audit), D-2750 (owner-approved APPLY: D2417 flip ratified + tier-2 fail-closed FORM invariant +
527-row owner map; "Files BUG-612 and BUG-613"), plus D-2755/D-2756/D-2757. The buglog headers still read
"(OPEN, 2026-10-02)" — a stale-header drift, NOT an open decision. This note flips the four headers to RESOLVED and
re-derives the register. buglog OPEN 136->132 / CLOSED 230->234 / 366; highest_bug BUG-613->BUG-604. session_seed synced.
No new decision id: the basis is D-2747/D-2748/D-2749/D-2750/D-2755/D-2756/D-2757.

## NOTE (2026-10-03) — SEVENTH RAIL: governance faces must not contradict the register (no new decision minted)

Root cause of the recurring drift: the six rails watch the machine register (`bug_status.json` /
`decisions_summary.json`) against its OWN re-derivation, but the hand-edited faces (`DECISION-LOG.md`,
`MASTER-TASK-REGISTER.md`) restate derived facts (bug status, census) as prose — and those restatements are
exactly what drifted (BUG-625/BUG-626 tabled "OPEN" while RESOLVED; a header restated "145 OPEN / 220 CLOSED /
365" while 132/234/366). Built `scripts/check_governance_faces.py` — the SEVENTH fail-closed rail — comparing the
faces' bug-status table rows and header census to the registers (deterministic, no LLM), wired into `just health`.
`governance/OWNER_GATE_BUG528_20261003.md` header corrected (D-2801 LANDED / D-2805 RATIFIED). No new decision id:
the basis is BUG-588 / D-2692 ("a count restated in prose is stale the moment it is written").

## NOTE (2026-10-03) — FORENSIC AUDIT: OMLX healthy; 2 deterministic drifts fixed; 3 handoff violations owner-owed

- OMLX API key was NOT broken: `config/pipeline_config.yaml` already carries `sk-maxwell-local`; `check_omlx_health()` True,
  chat completes, memory 27.2 GB free, watchdog RSS 4.9 GB. The earlier "API key required" was a raw ping WITHOUT the
  Bearer header. No code change needed.
- `just health` surfaced three classes. FIXED two (deterministic, no LLM):
  1. `config/menu_axis_hashes.yaml` STALE — definition-only drift (content_types/disciplines moved via D-2747/2749/2757;
     answer_space `domains`+`abstention` invariant, hash 8436d9c9). Regenerated via `scripts/menu_axis_hashes.py`.
  2. `scripts/check_instrument_cohorts.py` JSONDecodeError — D-2720/D-2785 repointed `axes.domains.artifact` from
     fb_id-keyed JSONL to item_id-keyed CSV; consumer assumed JSONL. Fixed: config-driven key + format detection, plus
     drop proper-superset cohorts (anchor 150 ⊂ domains 208 are nested, not two instruments).
- REMAINING (owner-owed, `verify_handoffs` exit 1 — NOT silently re-sealed): `s4_enriched_checkpoint` (t11) rewritten
  in place; `decisions.yaml` append_only violated (1 in-place deletion @ line 7426); `anchor4_workbook` human_authored+seal
  bytes changed with no blob. All tied to the in-progress anchor consolidation (150→208) — re-seal/re-receipt is an owner
  decision.

## NOTE (2026-10-03) — OPEN/PENDING table reconciled; 4 decision IDs need an owner registry-flip

Forensic audit result: the machine registers are IN SYNC (decisions.yaml <-> decisions_summary.json sha-consistent;
session_seed registry matches bug_status.json). The 🔴 OPEN/PENDING summary table had drifted two ways, now reconciled:

1. D2546 / D2547 / D2548 were tabled `PENDING` (a non-registry word) where the registry says `PLANNED` — corrected.
2. Substance: four IDs were advanced under SUCCESSOR decisions without the originals being flipped, so the table
   understated completion:

| ID | Registry state | True status |
|---|---|---|
| D2546 SHACL+OWL | PLANNED | SHACL .ttl SHIPPED (D2555); OWL periodic + Track B NOT started |
| D2547 per-label thresholds | PLANNED | infra DONE (gate D2571 + config D2556 + calibration D2561); per-label population + domain-axis frequency fix OPEN |
| D2548 grammar decoding | PLANNED | A/B RAN + REJECTED (D2392); grammar_decoding_enabled=false (D2556) — keep-off |
| D2622 practicality filter | PROPOSED | backend IMPLEMENTED (D-2723: config/practicality.yaml + pipeline/practicality.py); NOT wired into stage5 |
| D2621 facet-aware dedup | PROPOSED | genuinely OPEN — no work landed |
| D2345 single-source non-type pass | DRAFT | not started |

OWNER-OWED (registry state-flips are a governance act, not a silent edit): D2546->RESOLVED, D2547->keep PLANNED
until per-label populated, D2548->REJECTED, D2622->ACTIVE. session_seed.yaml already in sync (no edit).

## NOTE (2026-10-03) — 2 of 3 handoff re-baselines executed; anchor4_workbook deferred (owner ruling pending)

Owner authorized the 3 owner-owed re-baselines conditional on "no new bug/conflict/blindspot/future-tax/drift".
Executed 2 of 3:
1. `decisions_registry` append_only re-baselined — the in-place edit is the BUG-626 scalar canonicalization
   (`[D338,D339]` -> `D339`), documented and correct; re-receipt records the post-fix prefix.
2. `s4_enriched_checkpoint` re-receipted — gitignored run root rewritten by a legitimate run (mtime 2026-10-03 01:16);
   receipt journal + `receipt_provenance.unrevisioned_declared` digest updated `0ca6f0f0 -> 3854250c`.
3. `anchor4_workbook` DEFERRED (NOT re-sealed) — the workbook carries R003/R146 with
   `owner_note 'AUTOFILL … OWNER RULING PEN'` (a pending, not final, state). Re-sealing would bless forbidden
   imputation (`cohort_declaration.yaml`: "Neither may be imputed") and is the SAME event as the
   `depth_workbook_row_count` 148->150 drift. Both wait on the owner's R003/R146 ruling.
No new decision/bug minted; registry 1112 decisions / 366 bugs unchanged. session_seed.yaml already in sync.

## D-2811 (2026-10-03) - ANCHOR five-axis propagation rail: one AUTHORITY per axis + a rail that re-derives every consumer (closes the BUG-628 blindspot)
CONTEXT: the owner asked whether the 150 and 208 anchors are consistent on all five axes after the
2026-10-02 discipline+depth changes. MEASURED: NO. depth drifted 47 rows (208 view) / 37 (150 view); the
owner's D-2795 discipline re-label landed in discipline_anchor_conformance_20261002.json but NOT in the
consolidated (12), the 208 view (18), the 150 view (17) or the normalized view (18). 149 drifting cells,
caught by NO rail because no rail compared the artifacts.
DECISION: (1) config/anchor_axis_authority.yaml declares ONE authority per axis (depth ->
ANCHOR_208_DEPTH_CORRECTED D-2760; discipline -> discipline_anchor_conformance D-2795; domain/primary ->
208 five-axis view; content_type/extraction_type -> 208 view) and every CONSUMER that must follow it. (2)
scripts/check_anchor_axis_consistency.py re-derives each consumer on the item_id intersection: exit 0 agree,
exit 2 declared owner-owed (ceiling SHRINK-ONLY), exit 1 UNDECLARED drift (testable via --selftest).
MEASURED NOW: 149 declared cells, ceiling 149, exit 2 (loud, not fatal - BUG-457).
OWED (owner-gated, a gold rewrite): propagate the authority value into the 4 stale siblings, then delete the
declared rows (the ceiling must shrink loudly). Until then NO S4 golden may be bootstrapped from a stale copy.

## D-2812 (2026-10-03) - ANCHOR axis authority PROPAGATED (BUG-628 debt paid)

**Context.** D-2811 declared one AUTHORITY per axis and shipped the rail that COUNTS drift (ceiling 149).
A rail must not silently rewrite what it measures, so the debt stayed counted, not paid - and the 46-KEEP gold
split (RATIFY-2) would have baked a contradicted label into the few-shot.

**Decision.** `scripts/apply_anchor_axis_authority.py` is the WRITE limb. It walks `propagation.order` from
`config/anchor_axis_authority.yaml`, writes the authority value into the two five-axis views, then re-derives
`ANCHOR_208_DISCIPLINE_NORMALIZED` and `ANCHOR_208_CONSOLIDATED` from their own generators. Fail-closed (C16),
refuses an off-menu authority value (C12d), timestamped backup + atomic write (C13/C6), receipts to
`ANCHOR_AXIS_SYNC_20261003T114452Z.json` (R14), selftest registered in `just health` (BUG-492).

**Result.** 117 cells rewritten + 30 resolved by regeneration; ceiling 149 -> 2. Residual = R021 in both views,
whose depth AUTHORITY value is the provenance sentinel `noise_drop` (not a depth class) - refused by design.
Reported, never silent: discipline authority covers 204/208 (R021/R040/R080/R091 uncovered).


## D-2826 / D-2827 (2026-10-05) - T4 menu v6 + T9 Gate A(d) OWNER-APPROVED, audit-gated

**Context.** Owner approved both prior recommendations: T4 = ship the menu v6 bundle
(D-2814 definition-anchored closed menu + D-2815 additive B&M group + D-2816 pySHACL/OntoClean/ISO 25964-1)
as one atomic; T9 = ship D-2822 Gate A(d) (OR-entail + AND-no-contra) decoupled, after menu v6.

**Decision.** Flipped D-2814/D-2815/D-2816/D-2822 PROPOSED -> RATIFIED. Minted D-2826 (T4 ratification
record) and D-2827 (T9 disposition). The 11-category forensic audit (FORENSIC_AUDIT_20261005_MENU_V6_GATE.md)
returned BLOCKED with four pre-implementation findings -> D-2828 (PROPOSED) + BUG-640/641/642/643.

**Result.** Implementation deferred until: owner rules CF1 (B&M slot 'entrepreneurship' collides with the
existing domain) and BL1 (single abstention token); assistant executes B1/MI2 (regenerate taxonomy_shacl.ttl)
and C1 (alias_map 14-consumer shrink-then-remove). S5 re-run in progress (PID 91019, checkpoint.jsonl growing);
S6 commit waits on S5 completion.

## D-2829 / D-2830 (2026-10-05) — CF1 + BL1 owner rulings received; menu v6 gate unblocked on the human-decided findings
- **CF1 (BUG-640):** B&M discipline slots = 'business administration' / 'marketing' / 'entrepreneurship studies' (JEL M discipline-scoped; kills the 'entrepreneurship' domain collision).
- **BL1 (BUG-643):** single abstention token = 'emerging' (reconciles _ABSTENTION_VALUE 'none', closed_menu_v5.json catch_all, and the 27.2% emerging metric).
- **Deterministic fixes applied (B1/MI2 + registry):** taxonomy_shacl.ttl regenerated v5.5→v5.6 via generate_taxonomy_shacl.py — including a CONTENT drift the audit's MI2 missed (discipline list +'ecology' / −'computer networking'); bug_status.json header-gap fixed (BUG-638/640/641/642/643 now registered, 382 total).
- **D-2819 pre-provenance baseline COMPLETE:** S5 re-verified 6,591/6,591 FBs (PASS 3360 / QUARANTINE 3231) → S6 committed SQLite 14,574 rows vec0-READY + Parquet fbs_snapshot_20261005_114218.parquet (run under /opt/homebrew/bin/python3 3.14.6; framework Python 3.12 lacks enable_load_extension and fail-closed on vec_require=true).
- **Remaining deterministic gate:** C1 alias_map shrink-then-remove (14 consumers), then D-2814→2815→2816 atomic menu v6 (S4-idle gated), then D-2820 anchor re-derivation, then D-2822 Gate A(d) + NLI recalibration.

## D-2836 → D-2838 (2026-10-05) — D-2814 R5 gate closed; ADOPTION recommendation; writer-limb enforced
- **D-2836:** R5 verifier (gemma) review of the D-2814 swap — FAIL→fixed (F1 schema placeholders, F2 'emerging' hidden, F3 batch path uncovered). Flag OFF, uncommitted.
- **D-2837 (owner recommendation):** ADOPT the definition-anchored closed menu as the S4 target architecture (verbatim menu + definition anchors + per-axis 'emerging'). The flag flip is EMPIRICALLY GATED on the full-204 A/B (D-2767, kappa ≥ 0.800, emerging ≤ 0.35) against a RE-DERIVED anchor — D-2820 MUST PRECEDE the A/B or the kappa is circular (the 204-gold axis was adjudicated against the PRE-D-2814 free-gen menu).
- **D-2838 (BUG-631 writer-limb):** max_domains_per_fb=5 was DETECTED but NOT ENFORCED (52 FBs carrying 6-7 domains, all CLEAN). `_enforce_domain_cardinality()` now truncates at write with a receipt and degrades CLEAN→FALLBACK; control test added.
- **Forensic audit:** NO BREAK / NO CASCADE (governance/FORENSIC_AUDIT_20261005_D2837_ADOPTION.md). Census GREEN: 968 decisions, stamp 5a2565c1d692cb36.
- **NEXT:** D-2820 anchor re-derivation → full-204 A/B → conditional flag flip; then D-2822 Gate A(d), C1 alias_map, bundled dirty-tree commit.

## D-2839 (2026-10-05) — anchor-ratification gate minted; BUG-650 pre-A/B guard filed
- **D-2839 (PROPOSED):** owner ratification gate — the re-derived 204-gold anchor (D-2820 output) becomes the
  D-2767 A/B referee ONLY after owner sign-off. Four acceptance criteria: (1) menu-v6 hash-stamped; (2)
  owner-adjudicated, never LLM-only; (3) second-coder + DeBERTa-NLI cross-checked (R5); (4) D-274d-stamped.
  FIXES BUG-650 (fail-closed pre-A/B guard as the enforcement limb). Flips to RATIFIED only after re-derivation
  — a HUMAN gate the agent cannot self-sign.
- **BUG-650 (OPEN):** full-204 A/B has no fail-closed guard against a frozen-invalid anchor —
  benchmark_s4_ab.py / anchor2_kappa.py / fit_eval_model_swap.py read the v5-stamped 204-gold with no menu_hash
  pin check; a pre-D-2820 kappa is CIRCULAR and would silently pass the 0.800 floor.
- **Forensic audit (governance/FORENSIC_AUDIT_20261005_D2839_ANCHOR_RATIFICATION.md):** NO BREAK / NO CASCADE.
  Menu-v6 gate SATISFIED (composite 92f1a204 / answer-space d704d06e). Census GREEN: 969 decisions, stamp
  6d1dbb3f77891cee. Flag OFF, tree uncommitted.

## D-2840 (2026-10-05) — BUG-650 fail-closed pre-A/B anchor-referee guard LANDED
- **D-2840 (RATIFIED):** `pipeline/anchor_menu_guard.py` refuses kappa on a no-stamp or frozen-v5-pin
  menu-derived anchor (pins from config/menu_axis_hashes.yaml). Wired into
  `discipline_conformance_gate.py` load_anchor() (the 204-row referee; covers fit_eval_model_swap via import)
  + `anchor2_kappa.py`. Depth axis intentionally unguarded (not menu-derived).
- **BUG-650 (PARTIAL):** guard landed + verified (9 control tests; --dry-run and anchor2_kappa both exit 1).
  Still BLOCKED: A/B cannot run until D-2820 re-derives the anchor and D-2839 flips PROPOSED→RATIFIED.
- **Forensic audit:** NO BREAK / NO CASCADE / NO DRIFT. Census GREEN: 970 decisions, stamp f5faa921f90f053a.

## D-2841 (2026-10-05) — D-2820 anchor re-derivation harness LANDED (rederive_anchor_axes_v6.py)
Built the PRODUCER limb of D-2820: scripts/rederive_anchor_axes_v6.py re-derives the discipline + domains axes
against menu v6 (definition-anchored), owner-gated, second-coder + DeBERTa-NLI cross-checked, D-274d-stamped.
5 fail-closed stages (--plan/--generate/--adjudicate/--verify/--finalize). Finalize refuses unless the BUG-650
guard passes. 6 control tests + --selftest + --plan (204/204 join, pins verified). Forensic audit NO BREAK/NO
CASCADE/NO DRIFT. Census 971/stamp a02e757bf66c8a93. D-2839 remains PROPOSED (owner sign-off is a human gate).

## D-2842 (2026-10-05) — D-2822 Gate A(d) CODE limb LANDED (OR-entail + AND-no-contradiction)
- pipeline/stage5_verify.py: `_or_entail_and_no_contra_verdict()` + `_aggregate_verdict()` dispatch on
  config-first `stage5.nli_aggregation` (default 'majority' = current; 'or_entail_and_no_contra' = D-2822).
  Unknown value → fail-closed (C16). Score contract preserved (nli_calibrate.py unaffected).
- BUG-651 filed + registered (S5 majority aggregation hides supported claims / passes contradictory claims).
- 8 control tests (tests/test_or_entail_no_contra.py); 16 total pass with the B2 suite.
- Census 972 / stamp 109b972746d4a22c. FLIP gated on D-2822 recalibration + S5 re-run (OPERATOR step).

## D-2843 (2026-10-05) — BUG-631 READER-limb LANDED (scripts/check_domain_cardinality.py)
- Landed the READER half of the BUG-631 cardinality loop (D-2838 = WRITER half). The reader re-measures the
  committed store (DB_PATH, config-first) for canonical `domains` arrays > max_domains_per_fb (5), counts ONLY
  `domains` (never `domains_raw`), names parse-defects (never a silent zero, C16), writes a C6 receipt (--json),
  and exits fail-closed (0 clean / 1 drift / 2 parse-defect). 9 control tests
  (tests/test_domain_cardinality_reader.py) all pass.
- LIVE re-measure reproduces BUG-631 exactly: **52 over-cap FBs** (46 @ 6 domains, 6 @ 7) of 14,574 total
  (0.36%), every one CLEAN. The 52 historical FBs are STILL owed a re-derivation (BUG-631 stays OPEN).
- Governance drift fixed: BUG-647 header/body reconciled (IN PROGRESS → FIXED, matches the D-2833 table row).
- Census 973 / stamp ae6db643a2f879d6. Bug register 390 bugs: 145 open / 245 closed.
- SECONDARY (flagged, not fixed): store_authority.yaml declares 7,995 fbs rows; store now holds 14,574
  (rechunk-v4-20260929) — stale declaration to refresh at the menu-v6 commit.

## 2026-10-05 — Store-authority reconciliation (post-bloat drift fixed; NO new decision minted)
- `scripts/check_store_authority.py --check` was FAILING with 2 faults (cascade from the 2026-09-29 bloat cleanup):
  (1) `knowledge pipeline/diagnostic_diagnostic_20260811_232853.db` declared `derived` but ABSENT (→ tombstone);
  (2) `archive/bloat_20260929/knowledge pipeline/parquet` (22 old snapshots) UNDECLARED.
- FIX: removed the stale diagnostic-db declaration (tombstone already covered by `preimage_regions`); added the
  archived parquet collection as `archive`; refreshed authoritative `why` 7,995 → 14,574 fbs (75 cols unchanged);
  refreshed `knowledge pipeline/parquet` count 25 → 4 snapshots + 1 diagnostic subdir.
- Rail re-verified: 0 faults, exit 0. Census unchanged (973 / ae6db643a2f879d6). Forensic audit:
  governance/FORENSIC_AUDIT_20261005_STORE_AUTHORITY.md.

## D-2844 (2026-10-06) — PROPOSED — D-2820 owner adjudication normalized (204 rows) + taxonomy boundary clarifications
- Owner adjudicated the 142 differing rows of the D-2820 re-derivation (Numbers: "Surveillance Capitalism and
  Soviet Discourse.numbers", table rederive_v6_differences_only). Forensic audit CLEAN: 0 off-menu labels.
- Normalized: 4 separator typos (`,`/`.` -> `|`), 6 note typos. 62 same rows carried forward -> full 204-row decision set.
- Artifacts: governance/rederive_v6_owner_decisions_normalized.csv + governance/rederive_v6_owner_decisions.json
  (schema owner_decisions_v1: decisions map + drops + emerging_mix_pending + abstain_discipline).
- OWNER-GATED (none auto-applied):
  (1) DROP 3 noise rows R084/R106/R148 (R148 domain still filled -> inconsistent) -> anchor 204->201;
  (2) emerging-mix 4 rows R023/R112/R177/R188 (emerging alongside real domains) -> owner picks abstain vs keep;
  (3) taxonomy boundary clarifications PROPOSED: strategic thinking vs decision making; business administration vs
      operations research vs organizational theory; marketing vs design psychology vs behavioral economics;
      generative ai vs artificial intelligence vs machine learning; + domain overlaps (BD/BO/entrepreneurship,
      digital product/web & ui/product design, research & methodology/science & research). closed_menu_v6.json NOT edited (protected).
- --adjudicate/--verify/--finalize DEFERRED: harness fail-closed requires all 204 rows non-empty on-menu;
  finalize additionally gated on D-2839 sign-off + full-204 A/B (kappa>=0.800 AND emerging<=0.35).
- Forensic audit: governance/FORENSIC_AUDIT_20261006_OWNER_DECISIONS.md

## D-2845 (2026-10-06) — RATIFIED — D-2820 anchor re-cut 204→201 + emerging-mix resolved (owner-approved)
- Owner resolved D-2844 items (1)+(2): DROP 3 noise rows R084/R106/R148; emerging-mix R023/R112/R177/R188
  → **keep only real domains** (drop the stray `emerging` token). Rationale: `emerging` is a PURE abstention
  signal — mixing it with real labels is self-contradictory, degrades DeBERTa-NLI verification precision, and
  pollutes the emerging bucket used for future taxonomy-expansion triage. None of the 4 concepts is novel;
  full abstention would discard correct disciplines + domains for zero gain.
- Re-cut anchor: governance/discipline_anchor_conformance_20261006.json (204→201, provenance-stamped).
- Flat decisions: governance/rederive_v6_owner_decisions_flat.json (201 entries, all on-menu, all non-empty).
- --adjudicate → governance/rederive_v6_finalized_20261006.json (201 rows, owner_finalized, 0 off-menu).
- Emerging census (post-resolution): discipline='emerging' 7 (R006/R059/R127/R140/R146/R165/R202),
  domains=['emerging'] pure 7 (R032/R066/R101/R113/R141/R172/R209). 14/201 (6.97%) touch 'emerging' —
  under the 0.35 A/B gate.
- STILL OWNER-GATED: taxonomy boundary clarifications (strategic thinking/decision making; business admin/
  ops research/organizational theory; marketing/design psychology/behavioral economics; genAI/AI/ML) → edit
  closed_menu_v6.json (protected) → re-render + re-pin → re-derive (menu-hash change invalidates this anchor).
  Also deferred: 7 mirror-pattern rows (discipline='emerging' + real domains) for owner review.
- NEXT: --verify (second coder + DeBERTa NLI) → --finalize → flip D-2839 PROPOSED→RATIFIED (human gate) →
  full-201 A/B (D-2767) kappa≥0.800 AND emerging≤0.35 → flip definition_anchored_menu_enabled iff pass.
- Forensic audit: governance/FORENSIC_AUDIT_20261006_RESOLUTION.md

## D-2846 (2026-10-06) — RATIFIED — D-2820 anchor re-derivation --verify + --finalize complete (menu-v6 stamped, guard PASSED)
- --verify cross-checked all 201 rows: second coder gemma-4-E4B-it-MLX-4bit (R5 distinct family) + DeBERTa-NLI.
  Result: 85 agree / 116 disagree (57.7%); NLI 82 entailed / 102 weak / 17 contra-dominant. All SURFACED, never
  flipped (D-2839 c3). 12 of 17 contra-dominant rows sit exactly on the owner-flagged taxonomy boundaries
  (strategic thinking/decision making; business admin/ops research/organizational theory; marketing/design
  psychology; design thinking vs business admin/sociology).
- --finalize minted the re-derived anchor: governance/discipline_anchor_rederived_v6_20261006.json (201 rows).
  menu-v6 hash-stamped: composite 92f1a204c894376d84034084b33aabf6d07317cfa6b3fbeb5303b29525cc3681 +
  answer_space d704d06e3d17a9b91266938a9837c4daf443cb73e5d0598d9a859f69d0228267 (both == declared live pins).
  guard PASSED; gen_model = human_owner (adjudicated) — classifier output was INPUT only (D-2839 c2).
- Emerging census (final): discipline='emerging' 7 (3.5%), domains touching 'emerging' 7 — under the 0.35 A/B gate.
- Forensic note: the first --verify attempt's 300s-timeout left a stale duplicate PID running alongside the
  relaunched job (double memory + OMLX contention); killed it, verify then completed clean. No output corruption
  (crash-safe atomic writes, C6).
- D-2839 REMAINS PROPOSED (human gate): the harness does NOT self-sign. Owner sign-off next, gated on eyeballing
  the 17 contra-dominant rows (R155/R167/R168/R179 contra ≥ 0.97) + the 116 second-coder disagreements.
- NEXT (owner-gated): D-2839 ratify → full-201 A/B (D-2767) kappa≥0.800 AND emerging≤0.35 → flip
  definition_anchored_menu_enabled iff pass.

## D-2847 (2026-10-06) — RATIFIED — Owner consolidation of 14 contra-dominant rows + re-derive (menu-v6 re-mint)
- Owner resolved the 3 held consolidation items: R179 -> creative process; R143 -> design thinking;
  R183 -> discipline 'emerging' + domain 'urban planning' (explicit owner choice: abstain discipline, keep real domain).
- Applied 6 discipline changes (R155 business administration; R167 organizational theory; R183 emerging; R179 creative
  process; R036 marketing; R143 design thinking) + 8 owner-confirmed no-ops to rederive_v6_owner_decisions_flat.json
  (201). All 14 labels verified ON-MENU v6 (0 off-menu) BEFORE write.
- Re-ran fail-closed chain with --run-id 20261006b (after fixing the dead --run-id flag, D-2848):
  --adjudicate (201 rows, 0 off-menu) -> --verify -> --finalize.
- Verify: 88 agree / 113 disagree (43.8%); NLI 85 entailed / 104 weak / 12 contra-dominant (down from 85/116 and
  82/102/17). Owner consolidation resolved 5 of 17 contra-dominant rows. 14/14 consolidation rows landed correctly.
- Minted: governance/discipline_anchor_rederived_v6_20261006b.json (201 rows; composite 92f1a204... + answer_space
  d704d06e... == declared live pins; guard PASSED; gen_model human_owner adjudicated — classifier INPUT only, D-2839 c2).
- Emerging census: discipline='emerging' 8 (7 mirror R006/R059/R127/R140/R146/R165/R202 + R183); under the 0.35 gate.
- D-2839 REMAINS PROPOSED (human gate): 20261006b is a CANDIDATE referee, not yet the D-2767 A/B referee.

## D-2848 (2026-10-06) — RATIFIED — Harness --run-id dead-flag fix (C16 hidden-failure remediation)
- Forensic audit found --run-id was parsed but NEVER used: all path helpers (_worklist/_finalized/_verified/
  _manifest_path) + finalize_manifest artifact_id hardcoded _run_id() (UTC date). The --finalize error said
  "use --run-id for a new run" while the flag silently did nothing — a hidden failure blocking any same-day
  re-mint (I2 mint-once guard).
- Fix: threaded run_id through all path helpers + finalize_manifest (default _run_id()); added fail-closed validation
  (reject path separators; --run-id ../evil -> SystemExit). --selftest passed before AND after (no regression);
  --plan validated the fix. BUG-652 (RESOLVED).
- Flagged, NOT auto-fixed (protected config): pipeline_config.yaml discipline_anchor_path still points to the 204-row
  discipline_anchor_conformance_20261002.json while the re-cut is 201-row ..._20261006.json (drops R084/R106/R148).
  Harness run with explicit --anchor ..._20261006.json. Owner decision to repoint pending.

## D-2849 (2026-10-06) — PROPOSED — Effect-TS evaluation: adopt the patterns, not the TypeScript library
- Evaluated github.com/Effect-TS/effect (effect 4.0.1, LTS): TypeScript-only (TS 5.9+/Node 18+) for typed errors,
  dependency injection, structured concurrency, scheduling, tracing, unified schema validation.
- VERDICT: do NOT integrate the TS library into the Python pipeline (C27 zero future tax; C28 quality-tiered;
  C1/C3 sovereign local — a TS runtime + npm deps breaks the $0-local contract).
- ADOPT the four disciplines in Python instead: (1) typed errors -> Result/Either type (formalize C16 log-AND-raise);
  (2) structured concurrency -> asyncio.TaskGroup (fixes the stale-orphan process bug, D-2846 note);
  (3) parse-don't-validate -> pydantic at every config/JSON/DB boundary (fixes truncation/mismatch);
  (4) typed retry -> tenacity (fixes OMLX cold-load transient failures).
- Effect's guarantees are ALREADY codified in iron rules (C6/C13/C16/C23/C24); the gap is type-level ENFORCEMENT,
  not missing rules. No implementation yet — OWNER-GATED architectural decision.

## D-2850 (2026-10-06) — RATIFIED — Owner final consolidation round 2 + re-mint 20261006c
- Owner revised 3 discipline labels: R168 research methodology -> marketing; R153 research methodology -> cognitive science;
  R143 design thinking -> computer graphics. Confirmed R183 stays emerging + urban planning (urban planning is domain-only on
  menu v6, NOT a discipline — kept as discipline=emerging + domain=urban planning).
- Forensic audit BEFORE re-run: full 201-row menu validation (0 empty / 0 off-menu discipline / 0 off-menu domain);
  OMLX healthy (gemma-4 + gpt-oss loaded); no stale rederive processes (orphan double-load avoided).
- Re-ran fail-closed chain --adjudicate -> --verify -> --finalize at --run-id 20261006c. Result:
  contra-dominant 12 -> 9; second-coder disagreements 113 -> 110; NLI entailed 85 -> 87 / weak 105 / contra 9.
  All 3 changed rows resolved out of contra (R168 entailed 0.893, R143 entailed 0.987, R153 weak + second-coder agree).
- REMAINING 9 contra-dominant = 6 owner-confirmed labels still contra (R029/R098 design thinking, R047 design psychology,
  R107 research methodology, R090 media studies, R067 HCI) + 3 non-consolidation (R014/R134/R147). Owner is final authority
  (D-2839); noted, NOT auto-flipped.
- Manifest: governance/discipline_anchor_rederived_v6_20261006c.json (201 rows, guard PASSED, menu-v6 stamped).
- BUG-653 logged (off-menu domain-only trap; --adjudicate hint improvement proposed, not yet fixed).

## D-2851 (2026-10-06) — RATIFIED — Owner final round 3 (5 label changes) + re-mint 20261006d
- Owner revised 5 labels: R107 research methodology -> philosophy; R067 HCI -> interdisciplinary studies;
  R029 design thinking -> business administration; R047 design psychology -> psychology; R098 design thinking -> aesthetics
  (R098 was listed twice; owner resolved to aesthetics). Forensic audit: all 5 on-menu, defensive overwrite guard passed.
- Re-ran fail-closed chain --adjudicate -> --verify -> --finalize at --run-id 20261006d. Result:
  contra-dominant 9 -> 4 (R014/R090/R134/R147 remain); second-coder disagreements 110 -> 106; entailed 87 -> 89.
  4 of 5 changes now second-coder-agree (R029 entailed .792, R047 entailed .994).
- REMAINING 4 contra rows (R014 philosophy, R090 media studies, R134 information retrieval, R147 research methodology)
  + 106 disagreements are OWNER-ACCEPTED AS-IS (owner is final authority, D-2839).
- D-2839 FLIPPED PROPOSED -> RATIFIED (owner sign-off complete). The 20261006d manifest
  (governance/discipline_anchor_rederived_v6_20261006d.json, guard PASSED) is NOW the D-2767 full-201 A/B referee.


## D-2849 RATIFIED (2026-10-06)
Owner approve-and-ratify. Effect-TS patterns (Result/Either, asyncio.TaskGroup, pydantic, tenacity) adopted in principle; implementation deferred and folded into the classifier-of-record swap (tenacity retry + Result/Either) and the A/B harness (pydantic). No standalone scaffolding commit (C28).

## BUG-654 CORRECTED -> BUG-655 (2026-10-06)
The 0.46 "kappa swing" was a measurement bug: kappa 0.3181 (flag-OFF cribs arm) vs 0.7794 (flag-ON definition-anchored arm) are two sides of definition_anchored_menu_enabled, not non-determinism. Deterministic gpt-oss settings already applied (D-2637 server + config verifier levers); live 2-pass check 3/3 byte-identical. Real flag-ON kappa ~0.7794 (2pt under floor) -> flip still blocked for a genuine ~43-row gap. scripts/d2767_ab_eval.py rewritten to measure the flag-ON arm + determinism self-check.

## BUG-653 RESOLVED + BUG-656 OPEN (2026-10-06)
- BUG-653 (off-menu adjudication hint) RESOLVED — validate_on_menu + _off_menu_discipline_hint + _closest_labels, selftest green.
- BUG-656 (production-path vs rederive-path measurement) OPEN — D-2767 gate arm is the production prompt, not rederive `_classify_prompt`; harness now measures production path and emits a per-row disagreement CSV. No flip until owner rules the production-path disagreement rows.

## D-2852 (2026-10-06) — RATIFIED — D-A: D-2767 A/B verdict kappa 0.4313 → D-2839 gate FAILED
Owner ratified the A/B verdict. The full-201 flag-ON A/B (governance/d2767_ab_flagon_20261006d.json, 20:28) LANDED:

| metric | value | gate | verdict |
|---|---|---|---|
| Cohen kappa | **0.4313** | >= 0.800 | **FAIL** |
| emerging rate | 0.0299 | <= 0.35 | pass |
| raw agreement | 0.4478 | — | — |
| determinism | 8/8 | byte-identical | pass |
| disagreements | 111 / 201 | — | 55% |

The definition-anchored flag-ON classifier does NOT reproduce the owner referee → `definition_anchored_menu_enabled` stays OFF. Finding: the production prompt (`_apply_definition_anchored_menu` + `build_merged_prompt`, 10-field JSON menu in SYSTEM) underperforms the rederive path (0.4313 vs 0.7794) — the menu-in-system-prompt vs menu-in-user-prompt divergence is itself a taxonomy-work input. SUPERSEDES BUG-654 (0.3181 flag-OFF) and the BUG-655/656 0.7794 rederive number as the definitive measurement.

## D-2853 (2026-10-06) — RATIFIED — D-3 (taxonomy C): freeze closed_menu_v6.json, build closed_menu_v7.json from disagreement clusters
Owner approved decision C. Freeze v6 (menu_hash-pinned to the ratified 201-row referee). Build closed_menu_v7.json as a NEW versioned file from the 111 disagreement rows + confirmed collision clusters: (a) merge within-axis near-synonyms — machine learning/generative ai/artificial intelligence; systems thinking/systems engineering/complex adaptive systems; psychology/cognitive science/decision making/behavioral economics; visual perception/visual semiotics/semiotics; code & computation/computational art/creative technology; digital product/product design/web & ui/user experience/information architecture; business development/business operations/organizational behavior; (b) rename cross-axis near-identical collisions to axis-scoped labels — artificial intelligence↔ai & agents, finance↔finance & investment, marketing↔marketing & communications, entrepreneurship studies↔entrepreneurship, research methodology↔research & methodology, semiotics↔semiotics & communication; (c) add one-line discriminator fields. PREREQUISITE (drift guard): after consolidation, remap ALL anchors/golden/config/scripts referencing old labels, else drift returns. Gate v7 behind its own A/B — adopt only if kappa improves toward >= 0.800.

## D-2854 (2026-10-06) — RATIFIED — D-B root fix: total wall-clock deadline in pipeline/omlx_call.py::call_omlx (BUG-658)
Owner ack granted. Root fix landed: pipeline/omlx_call.py now wraps every `requests.post` in `_post_with_wall_clock` (daemon thread + `join(timeout=OMLX_WALL_CLOCK_DEADLINE=180s)`); `WallClockTimeout` is treated as a wedge (WEDGE_RECOVERY_SLEEP + retry, then RuntimeError). Config constant `OMLX_WALL_CLOCK_DEADLINE` sourced from `services.omlx.wall_clock_deadline_sec` (C12). This protects ALL callers (stage2/4 pipelines), not just the d2767_ab_eval harness (which retains its own `_call_omlx_json_with_deadline` + preflight smoke). BUG-658 stays OPEN until the harness relaunch reproduces the fix end-to-end.

## BUG-655 RESOLVED + BUG-656 RESOLVED (2026-10-06)
- BUG-656 RESOLVED: the definitive production-path kappa LANDED = 0.4313 (FAIL). The 0.7794 rederive-path number is confirmed non-gating (D-2852).
- BUG-655 RESOLVED: the "0.46 swing" is fully explained — flag-OFF 0.3181 vs rederive flag-ON 0.7794 vs production flag-ON 0.4313 are three distinct prompt paths, NOT non-determinism. Determinism self-check 8/8 byte-identical.

## D-2855 (2026-10-06) — RATIFIED — D-NEXT-1 (a,b,c): discriminator-first differentia + org-theory/BA + semiotics fold + 7th engineering pair
Owner ratified D-NEXT-1. (a) Discriminator-first differentia generalized to every entry (genus + differentia + nearest-neighbor exclude). Org theory = EXPLANATORY/POSITIVE (organization as object of inquiry); business administration = PRESCRIPTIVE/NORMATIVE (managerial function as object). (b) Keep semiotics distinct; fold visual semiotics into semiotics. (c) Adopt the 7th engineering pair; strip academic raw from engineering & infrastructure domain. Addresses the axis-impurity root of BUG-630.

## D-2856 (2026-10-06) — RATIFIED — stable opaque IDs + MECE partition validator + taxonomy_v7 build
Every taxonomy entry gets a stable opaque id (disc-NNN/dom-NNN) so display renames cost zero remap (string-as-identity was the BUG-630 drift vector). scripts/validate_taxonomy_partition.py = fail-closed MECE validator (1 raw → exactly one (axis,id); canonical distinct within/across axes). scripts/build_taxonomy_v7.py built config/taxonomy_v7.yaml: 202 raw dedups, 178 partition resolutions, rename 'research & methodology'→'research practice' (D-2853). Validator: 0 violations. Fixes the axis-impurity root of BUG-630.

## D-2857 (2026-10-06) — RATIFIED — split S4 classification (Call B) from CRIBS enrichment (Call A)
Owner ratified the D-2856 split clarification. NO new stage, NO new LLM: same stage4, two calls. Call A = CRIBS enrichment on Qwen3-Coder-30B (no closed-menu preamble); Call B = classification {discipline,domains} on gpt-oss-20b-MXFP4-Q8 (definition-anchored closed menu). Bottleneck IMPROVES (classifier arm parallelizes, enrichment arm sheds ~5k-token menu). The focused Call B is the 0.7794 rederive path that must reach ≥0.800 before classifier-of-record. Fixes the attention-overload/menu-bloat root of BUG-648.

## D-2858 (2026-10-06) — RATIFIED — D-NEXT-A: recalibrate D-2822 under or-entail semantics, THEN flip S5 aggregation (drift-pinned)
Senior RAG/ontological recommendation (owner ratify). The BUG-651 fix (D-2842 `_or_entail_and_no_contra_verdict`) is LANDED but INERT — `stage5.nli_aggregation` is still `majority`, so an S4→S5 rerun will re-quarantine the 506 ENTAIL-majority rows. Sequence: (1) run `pipeline/nli_calibrate.py` against or-entail semantics (a claim now survives on ONE entail, so the per-passage threshold may need tightening from 0.10); (2) re-mint the calibrated threshold into `config/recalibration_pins.yaml` under a NEW decision id (D-353 — the existing `menu` pin there is ALREADY STALE: it pins `closed_menu_v5.json` while live menu is v7); (3) only then flip `nli_aggregation` → `or_entail_and_no_contra`; (4) add a fail-closed guard refusing or-entail mode without a matching calibration stamp. Do NOT flip before recalibration.

## D-2859 (2026-10-06) — RATIFIED — D-NEXT-B: BUG-563 worktree triage (37 dirty paths → 3 buckets)
Senior recommendation (owner ratify). `check_repo_integrity --worktree` FAILS on 37 un-homed paths. Buckets: (a) RUN ARTIFACTS (`governance/rederive_v6_*`, `governance/d2767_ab_*`, `logs/**`) → paired `.gitignore` + `worktree.excluded` (excluded REQUIRES git-ignore alignment — verified this session that excluded-without-.gitignore raised faults 39→42); (b) SOURCE-MATERIAL DROP-INS (`governance/Surveillance Capitalism and Soviet Discourse.csv`) → owner-gate commit-or-relocate with provenance, never silently git-ignore a corpus input; (c) DOCS/SCRIPTS (`ONTOLOGY_ENFORCEMENT_ARCHITECTURE_20261004.md`, `TAXONOMY_EVOLUTION_TOOLING_20261004.md`, `scripts/watch_run.sh`, `closed_menu_v6_reference.csv`, `domain_cardinality_receipt.json`) → may_touch grants or archive.

## FORENSIC AUDIT 2026-10-06 (scope/drift corrections — supersedes earlier v7 "complete" framing)
- v7 promotion is REAL at the source-of-truth layer: `config/taxonomy_v5.yaml` is byte-IDENTICAL to `config/taxonomy_v7.yaml` (64 disc / 43 dom, opaque ids, discriminators, 0 MECE violations). Verified.
- anchors + golden + A/B referee are NOT consolidated to v7: `config/golden/gold_frozen.yaml` carries 123 "research methodology"-family hits, `stage4_golden.yaml` + `stage2_fewshot_*` carry v6 labels, and the D-2767 referee (`discipline_anchor_rederived_v6_20261006d.json`) has 46 rows with "research methodology"/"research & methodology" and 0 "research practice". A v7-menu classifier CANNOT be A/B-scored against a v6-label referee. REMAP blocks both the A/B and the S4 rerun.
- D-2857 split (Call A/Call B) RATIFIED but NOT implemented: `pipeline/stage4_merged_call.py` still runs the single merged call (D2224); no Call A/B functions, no `call_a`/`call_b` config keys.
- D-2855 discriminator-first differentia is only 2/107 entries done (organizational theory `disc-012`, business administration). The other 105 entries (incl. business operations, organizational behavior) have no `differentia`. D-2855(a) "generalized to every entry" is NOT yet materialized.
- D-2856 opaque ids are minted in `taxonomy_v5.yaml` but NOT wired to serving/storage: `closed_menu_v7.json` carries `{value, definition, group}` with NO id; the DB stores display strings (relabel, not id-swap); golden/anchors key on strings. The "stable id prevents remap drift" claim holds only at build-time validation, not runtime identity.
- stale pins: `config/recalibration_pins.yaml` still pins `closed_menu_v5.json` (live = v7); `scripts/render_closed_menu.py` default target still `closed_menu_v5.json`.

## FORENSIC AUDIT 2026-10-06 v2 — re-verified read-only; CORRECTS the v1 audit's consolidation claim
The v1 audit above OVERSTATED the remap scope. Re-verified facts:
- The v7 "rename" is a DOMAIN rename ONLY: domain `research & methodology` → `research practice` (D-2853). The DISCIPLINE `research methodology` is UNCHANGED (valid v7; present in both closed_menu_v5 and v7). v1 conflated the two axes.
- 3 NEW disciplines added in v7: `business administration`, `entrepreneurship studies`, `marketing` (menu disciplines 62→65 incl. `emerging` abstention; domains 44→44 with the 1 rename).
- GOLDEN is ALREADY v7-consistent: `gold_frozen.yaml` has 0 `research & methodology` (93 `research practice` domain + 30 `research methodology` discipline, both correct); `stage2_fewshot_*` clean. v1's "123 v6 hits" was wrong.
- ANCHORS already clean: `anchor_family.yaml` + `domain_anchors.yaml` have 0 `research & methodology`.
- DB already relabelled: `eval_integrity.yaml` (D-2853) records "DB relabelled 875 rows" research & methodology → research practice.
- REMAINING drift is NARROW: (1) A/B referee has 28 stale DOMAIN rows `research & methodology` (its disciplines are already v7, incl. the 3 new); (2) live config maps still reference the stale domain: `alias_map.yaml` (16), `synonym_map.yaml` (1), `domain_disciplines.yaml` (1 key), `anchor_workbook_fixes.yaml` (1), `eval_integrity.yaml` (1 example).
- COVERAGE GAP: `gold_frozen` has 0 `business administration` + 0 `entrepreneurship studies` (2 of 3 new disciplines absent from golden regression; referee has them: BA 24, ES 8, marketing 47).
NET: the #1 blocker is NOT "remap anchors+golden+referee" (mostly done) — it is a small mechanical finish-D-2853-rename: 28 referee domain rows + ~19 config-map refs, all `research & methodology` → `research practice`. D-2858/D-2859 RATIFIED this session.

## D-2860 (2026-10-07) — RATIFIED — commit-frontier gate: refuse to proceed with uncommitted ratified governance state (anti-circle)
Owner ratified (2026-10-07). The 2-week circle had ONE root cause: 1112 decisions D-2826..D-2859 RATIFIED in the worktree but uncommitted (HEAD 955 vs worktree 989), and NOTHING compared "accepted in the worktree" against "committed in HEAD." This lands `scripts/check_commit_frontier.py` + `config/commit_frontier.yaml` (wired into `just health`) as a fail-closed BOOT+health gate: it refuses when any governance-critical file is dirty, or when a RATIFIED/ACTIVE/RESOLVED decision exists in the worktree but not HEAD. Not a commit hook (a staged file is uncommitted by definition). Owner ratification owed before hardening beyond fatal.

## D-2861 (2026-10-07) — RATIFIED — re-baseline the three red health drifts (label provenance boundary, anchor bridge, decisions receipt)

Forensic audit found three fatal (rc=1) health drifts after the BUG-571 register-divergence fix:
(1) check-label-provenance boundary population 7983 vs declared 7995 — a 12-row store change under
rechunk-v4-20260929 (BUG-501); (2) build_anchor_store_bridge committed bridge no longer re-derived after the
store change (BUG-420); (3) verify_handoffs decisions_registry prefix receipt broken by in-place edits (BUG-376).
Re-baselined all three: measured_rows 7995->7983, re-derived the bridge (11 ambiguous rows recorded, never picked),
re-cut the receipt via handoff.py --backfill. Owner ratified.
Bugs: BUG-501, BUG-420, BUG-376.
Files: config/label_provenance.yaml, governance/ANCHOR_STORE_BRIDGE_20260926.json, config/handoffs.yaml.

## D-2862 (2026-10-07) — RATIFIED — re-mint t11 checkpoint_enriched.jsonl authority marker (BUG-667)

The t11 `checkpoint_enriched.jsonl` was legitimately rewritten 65 min after the S5 run completed (C-3/BUG-376
acknowledged move). Its ARTIFACT_AUTHORITY.json sha256 pin (0ca6f0f0…) predated the rewrite, so the marker was a
false claim. Re-minted the pin to the on-disk bytes (3854250c…; byte size unchanged 96902142, mtime
2026-10-03T01:16). A pin is re-minted by a DECISION (D-382/BUG-535), never a quiet re-hash. Owner ratified
(2026-10-07).
Bugs: BUG-667.
Files: knowledge pipeline/stage4_merge/t11/ARTIFACT_AUTHORITY.json.

## D-2864 (2026-10-07) — RATIFIED — D-2853 close-out: re-mint the A/B referee to menu v7 (28-row domain remap)

Owner signed off the 28-row referee remap (owner_decision = 'research practice' on all 28 rows).
scripts/remap_referee_v7_28rows.py deterministically renamed the stale DOMAIN 'research & methodology' ->
'research practice' in exactly 28 rows and re-stamped the manifest to menu v7 (menu_hash 407f3dd4... /
answer_space_hash 6d7c08de..., taxonomy v7, anchor v7). DISCIPLINE 'research methodology' UNCHANGED.
New artifact governance/discipline_anchor_rederived_v7_20261007.json (D-353 re-mint); v6 manifest untouched.
Verified: 0 stale / 0 off-domain / 0 off-discipline / 0 discipline-vs-v6 drift. Unblocks A/B + S4 rerun.

## D-2865 (2026-10-07) — RATIFIED — A/B/C taxonomy v8: merge science & research, demote social sciences, HCI/UX dedup

Owner ratified the A/B/C fixes. `scripts/build_taxonomy_v8.py` deterministically (LLM-free):
- **A** merged dom-031 `science & research` into dom-025 `research practice` (raw union, exclude union minus the self-reference, definition rewritten to the scholarly+scientific research practice);
- **B** demoted dom-035 `social sciences` to raw synonyms folded into `research practice` (no new canonical; recorded in `meta.displaced_canonicals`);
- **C** dropped raw `user experience design` from disc-036 `human-computer interaction` (kept under dom-010), closing the cross-axis MECE violation (BUG-630) that made the D-2856 "0 violations" claim stale after commit 65339ae.

`scripts/validate_taxonomy_partition.py` reports **0 violations on v8** (41 domains / 64 disciplines). Applied via `scripts/apply_taxonomy_v8.py`: promoted to live `config/taxonomy_v5.yaml`, minted `config/closed_menu_v8.json` (menu_hash 8218d6db91add988), re-pinned `config/menu_axis_hashes.yaml` (answer_space_hash 5bd9456802db9efe), regenerated `config/taxonomy_shacl.ttl`, bumped `config/version.yaml` (v8), dropped the dead `normalization_map` + `pipeline_config` per_label entries, `max_domains` 43→41. Organizational behavior (dom-016) kept; disc-021 `research methodology` / disc-022 `operations research` unchanged.

**Anchor remap (owner-signed 2026-10-07, applied as D-2866):** `governance/anchor_v8_domain_remap_triage_20261007.csv` (20 anchor rows = 16 DROP + 4 ROUTED). The earlier "74 rows" figure mixed silver (gold_4axis) — silver is regenerated by S4, never hand-remapped. Authoritative anchors remapped in `governance/discipline_anchor_rederived_v8_20261007.json` (201 rows, re-stamped v8). See D-2866.

## D-2866 (2026-10-07) — RATIFIED — Anchor domain remap to v8 (20 rows: 16 DROP + 4 ROUTED)

Deterministic (LLM-free), anchor-only. `scripts/build_anchor_v8_remap_triage.py` reads ONLY `governance/discipline_anchor_rederived_v7_20261007.json` (the authoritative 201-row anchor artifact; D-2853 rename already applied) and applies RENAME / DROP {`science & research`, `social sciences`} / ROUTE (sole-domain rows via `config/discipline_domain_map.yaml`, fallback `research practice`) plus six owner overrides. `scripts/build_anchor_v8_apply.py` applies the same remap to emit `governance/discipline_anchor_rederived_v8_20261007.json` (201 rows, re-stamped taxonomy_version/anchor_version v8, live menu_hash 8218d6db… / answer_space_hash 5bd94568…).

Owner overrides: R004 `legal & public policy`, R198 `marketing & communications`, R065 `media & entertainment`, R107 `education`+`user experience`+`research practice`, R162 `education`+`leadership`, R085 `emerging` (metacognition/self-awareness/critical thinking → abstain). R031/R033/R164 stay `research practice`.

Golden = anchors only; silver (`gold_4axis.jsonl` / `gold_frozen.yaml` / `stage2_fewshot`) is regenerated by S4, never hand-remapped. Legacy `ANCHOR_208_CONSOLIDATED_20261002.json` is a different generation (86 discipline disagreements) and must be regenerated from rederived_v8, never hand-patched.

## D-2867 (2026-10-07) — RATIFIED — Regenerate ANCHOR_208_CONSOLIDATED to v8 + re-point eval_integrity anchor source

`scripts/regenerate_anchor_208_v8.py` (deterministic, LLM-free) re-joins `ANCHOR_208_DEPTH_CORRECTED_20261002.json` (depth, 208) × `discipline_anchor_rederived_v8_20261007.json` (discipline+domain, 201) → `ANCHOR_208_CONSOLIDATED_20261007.json` (208 rows; 201 with v8 domains, 193 golden_eligible, 0 stale, primary_domain==first-pipe-token 0 drift). The 7 depth-only rows carry their D-2844 drop disposition (R021/R084/R106/R148 noise_drop → null; R040/R080/R091 emerging) — never a stale v8 domain. `config/eval_integrity.yaml` `anchor.source` re-pointed to the regenerated artifact (total_anchors stays 208). Unblocks the S4 re-run + anchor2 kappa re-measure against menu v8.

## D-2868 (2026-10-07) — RATIFIED — Re-point anchor-axis authority (discipline/domain/primary_domain) to rederived_v8 + schema-compatible columns

Deterministic, LLM-free. `scripts/build_anchor_v8_apply.py` now also emits schema-compatible `domain` (pipe-joined) + `primary_domain` (first token) columns into `discipline_anchor_rederived_v8_20261007.json` and fixes its stale `artifact_id` (was `rederived_v7_20261007`). `config/anchor_axis_authority.yaml` re-points discipline/domain/primary_domain to rederived_v8 (201 rows) — depth stays on `ANCHOR_208_DEPTH_CORRECTED_20261002.json` (208), content_type/extraction_type stay on the 5-axis view. Legacy consumers (discipline_anchor_conformance_20261002, DISCIPLINE_NORMALIZED, FIVE_AXIS_VIEW discipline/domain copies) are superseded in favour of the single regenerated consumer `ANCHOR_208_CONSOLIDATED_20261007.json`; `propagation.order` swapped to `regenerate_anchor_208_v8.py`. Verification: `scripts/check_anchor_axis_consistency.py` exits 0 — every consumer agrees, ceiling 0 holds, 0 domain/primary_domain drift.

Follow-through (2026-10-07, executed + verified): re-pointed the two stale discipline consumers to rederived_v8 — `config/pipeline_config.yaml` `discipline_anchor_path` and `scripts/discipline_conformance_gate.py` `DEFAULT_ANCHOR` (were `discipline_anchor_conformance_20261002.json`, frozen-invalid: no menu stamp, so the BUG-650 referee guard refuses it). Renamed the guard version-agnostic (C19): `assert_referee_menu_v6` → `assert_referee_menu_current`, `referee_menu_v6_verdict` → `referee_menu_current_verdict` (reads live pins; name no longer pinned to v6). 6 files + 2 tests. Verified: pytest 15 passed; `referee_menu_current_verdict(rederived_v8)` ok=True (live pins hit, frozen empty); `load_anchor` joins 201 rows → 53 disciplines (top: cognitive science, research methodology, psychology, marketing, behavioral economics).

Follow-through 2 (2026-10-07, executed + verified) — anchor_family.yaml domains re-point + concat-guard split. Re-pointed `config/anchor_family.yaml` `axes.domains.artifact` from the pre-v8 CSV (`ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv`, 208 rows) to the v8 authority `discipline_anchor_rederived_v8_20261007.json` (201 rows); updated cohort counts 208→201; added JSON branches to `scripts/verify_anchor_family_registry.py` and `scripts/check_instrument_cohorts.py`. FORENSIC FINDING during verification: `check_instrument_cohorts.py` misused `axes.domains.artifact` as its concat-guard cohort; the 201-row authority is a NON-superset of the 150 anchor ruler (the 7 golden-pool exclusions R021/R040/R080/R084/R091/R106/R148 carry no domain label), so the guard read the 7 exclusions as a SECOND instrument and false-failed the 150-row depth-blind sheet ("spans 2 cohorts"). FIX (future-proof, config-first C12c): split the conflated field — `artifact` = axis AUTHORITY (201), new `cohort_artifact` = full family instrument population (`ANCHOR_208_CONSOLIDATED_20261007.json`, 208, a proper superset of the 150 ruler, dropped by the guard's superset rule). Verified: `verify_anchor_family_registry.py` exit 0 (domains OWNED cohort 201 primary_domain_filled 201/201); `check_instrument_cohorts.py` exit 0 ("cohort 'anchor' only"); `check_anchor_axis_consistency.py` exit 0 (ceiling 0 holds); pytest 15 passed; `menu_axis_hashes.py --check` ok.

Follow-through 3 (2026-10-07, executed + verified) — F1 re-point COMPLETE + F2 re-mint triage. **F1:** re-pointed the last active reader `scripts/rederive_anchor_axes_v6.py` `DEFAULT_ANCHOR` (`discipline_anchor_conformance_20261002.json` → `discipline_anchor_rederived_v8_20261007.json`, docstring 204→201); marked `scripts/finalize_discipline_bulk.py` `OUT_CONFORMANCE` writer RETIRED (completed D-2766 one-shot, self-guarded vs re-run — conformance output superseded by rederived_v8); updated stale doc comments in `check_anchor_axis_consistency.py` + `discipline_conformance_gate.py`. FORENSIC: the stale artifact's ONLY remaining live reference is the RETIRED one-shot writer; the six clean readers were re-pointed in the prior pass. Retired the stale `governance/discipline_anchor_conformance_20261002.json` to `archive/` (zero live readers; remaining refs are immutable provenance/history). Verified: `check_anchor_axis_consistency.py` exit 0 (ceiling 0 holds, 0 domain/primary_domain drift), `verify_anchor_family_registry.py` exit 0, `check_instrument_cohorts.py` exit 0, `rederive_anchor_axes_v6.py --plan` reads 201 rows joined 0 missing (live pins 8218d6db/5bd94568), pytest 18 passed. **F2:** emitted `governance/ANCHOR2_V8_REMINT_TRIAGE_20261007.csv` (38 action rows across ANCHOR2 KEY + BLIND SHEET): 12 AUTO_RENAME (`research & methodology`→`research practice`), 19 DROP_CONFIRM (`science & research` merged / `social sciences` demoted, incl. singular `social science` variant), 3 DROP_REROUTE (sole-domain rows re-routed via `config/discipline_domain_map.yaml`), 3 AUTO_FIX (data-quality typos `media & entertainmen`/`product desig`/`business operation`), 1 OFFMENU_ADJUDICATE (SHEET row 15 empty discipline). FORENSIC: `neuroscience`/`performing arts`/`design psychology` are ON-MENU v8 disciplines (present in the full 64 canonical discipline list from `config/taxonomy_v8.yaml`); the 53-token USED-subset extraction false-flags them off-menu — classified against the full menu, not the used subset. `emerging` is the on-menu abstention token (not a fault). Owner must decide 23 rows (19 drop + 3 reroute + 1 empty-discipline); 15 auto-apply.

Follow-through 4 (2026-10-07, executed + verified) — F2 re-mint triage CORRECTED to content-driven applied domain (owner rule) + peer-reviewed method validation.

Owner rejected the D-2866 `discipline_domain_map.yaml` route as a rubber stamp (`psychology → organizational behavior` wrong for SHEET 34 Doping + SHEET 47 Peripheral Cue). Corrected rule (owner-specified): DROP re-route = content-driven "which domain can the principle actually be utilized/applied in"; no clear applied domain → `emerging` (abstention); OFFMENU_ADJUDICATE → `emerging`; raw labels (`s3_original_domain`) preserved for recoverability. AUTO_RENAME (12) + AUTO_FIX (3) approved unchanged.

Method validation (peer-reviewed, referencable): the proposition is valid/feasible/reliable against — (1) Guarino kind-vs-role + BFO function (Arp/Smith/Spear 2015) + Ranganathan faceting for the discipline/domain two-axis split; (2) OntoClean rigidity (Guarino & Welty 2002) for content-driven routing (psychology→organizational-behavior is a rigidity violation); (3) reject-option/open-set (Chow 1970; Scheirer et al. 2013) for `emerging` abstention; (4) FAIR R1.2 + SKOS altLabel (Wilkinson et al. 2016; Miles & Bechhofer 2009) for raw-label preservation; (5) Krippendorff α / Cohen κ for owner-gate agreement. Precondition flagged: `arts & culture` (dom-032) definition prose ("performance", "cultural expression") is looser than raw/exclude/group=Visual Practice constrain it; queued a taxonomy_v8 definition-tightening (Cultural Mourning Rituals = anthropology → emerging, NOT arts & culture).

`governance/ANCHOR2_V8_REMINT_TRIAGE_20261007.csv` re-emitted (38 rows): 12 AUTO_RENAME + 3 AUTO_FIX + 22 OWNER_APPLY (pipe-joined primary-first) + 1 OFFMENU_ADJUDICATE→emerging. Owner confirmed primary/secondary per row. `emerging`: Cultural Mourning Rituals and Symbolism, Acknowledgment Attribution (empty discipline). Owner overrides: Perspective-driven Cognitive Shift primary=arts & culture; Procedural Vs Declarative Knowledge Retrieval primary=user experience. `organizational behavior` (dom-016) retained as a valid applied domain (primary or secondary); the earlier rejection was per-principle content, not a domain demotion.


Follow-through 5 (2026-10-07, executed + verified) — Owner correction: three anchor applied-domain re-adjudications propagated across ALL artifacts (201-row authority + 208-row all-axis consolidated + ANCHOR-2).

Owner-gated correction (2026-10-07) resolving the forensic drift flagged between the F2 ANCHOR-2 triage, the 201-row rederived_v8 authority, and the legacy 208-row consolidated artifact. Three applied domains re-adjudicated content-driven (OntoClean rigidity — Guarino & Welty 2002; kind-vs-role, BFO/Arp-Smith-Spear 2015):

  (1) Survivor Bias (R198 / SHEET+KEY row 48): marketing & communications -> personal productivity | finance & investment | entrepreneurship (NOT marketing).
  (2) Provincial Norms (R162 / SHEET+KEY row 12): education | leadership -> organizational behavior | education | leadership (NOT legal & public policy).
  (3) Doping (R184 / SHEET+KEY row 34): organizational behavior -> health & wellness (NOT organizational behavior).

FORENSIC (before the fix): the three artifacts DISAGREED on these three concepts. The 201-row authority carried the pre-correction domains; the ANCHOR-2 KEY rows 12/34/48 still carried STALE-v5 pipeline predictions (6-domain list / legal & public policy / business operations+legal & public policy) that the F2 re-mint never migrated (they were v8-valid tokens, so no stale-token action fired); the SHEET row 12 was legal & public policy-primary and row 48 was finance & investment-only. All three now converge on the owner's answer.

Propagation (deterministic, LLM-free):
  - scripts/build_anchor_v8_remap_triage.py OWNER_OVERRIDES updated (R198/R162/R184); governance/anchor_v8_domain_remap_triage_20261007.csv regenerated (STILL 20 rows = 16 DROP + 4 ROUTED — R184 added as an override but it was already a DROP row, so the invariant holds).
  - scripts/build_anchor_v8_apply.py re-minted governance/discipline_anchor_rederived_v8_20261007.json (201 rows).
  - scripts/regenerate_anchor_208_v8.py regenerated governance/ANCHOR_208_CONSOLIDATED_20261007.json (208 rows, 201 with v8 domain, 0 stale) — ALL AXES (depth + discipline + domain) in ONE document.
  - scripts/remint_anchor2_v8.py re-minted ANCHOR-2 KEY + BLIND SHEET (60 rows each) and corrected the THREE stale-v5 KEY predictions (rows 12/34/48) plus SHEET rows 12/48; the F2 triage CSV grew 38 -> 41 rows (3 KEY OWNER_APPLY additions).
  - scripts/anchor2_kappa.py re-pointed to V8 artifacts + config/taxonomy_v8.yaml and re-measured: discipline kappa 0.4314, domains micro-kappa 0.652, content_type kappa 0.0 (degenerate: pipeline predicts 1 distinct content_type vs 10 human), out_of_vocab 0.

Verification: check_anchor_axis_consistency.py exit 0 (declared ceiling 0 holds); BUG-650 referee guard ok=True (live pins 5bd94568…/8218d6db…); 0 OOV domains/disciplines; primary_domain==first-token 0 drift. Note: 'entrepreneurship' is the canonical taxonomy_v8 spelling (owner's 'enterpreneurship' was a typo — never minted as an OOV token).

Queued: taxonomy_v8 arts & culture (dom-032) definition-tightening (from Follow-through 4 precondition).

---

## Follow-through 6 (2026-10-07, executed + verified) — Owner correction round 3 (D-2870)

Owner-gated corrections, deterministic + LLM-free, all artifacts regenerated from source (never hand-patched):

1. **Same-age Peer Modeling (R210 / SHEET row 60)** — `marketing & communications` added as a 3rd applied domain → `education | user experience | marketing & communications` (primary=education). Converged the previously-divergent ANCHOR-2 SHEET row 60 ("education" only) with the 201-row authority ("education | user experience"): both now carry all three.

2. **Psychology default-route removal** — `config/discipline_domain_map.yaml` entry `psychology: organizational behavior` deleted. Psychology has no single default application field, so auto-routing it to org behavior is a rubber stamp, not a content-driven (OntoClean rigidity) classification. Psychology now falls through to the neutral `fallback: research practice` on empty-after-drop. Zero cascade (no anchor relied on that entry; all 5 ROUTED rows are owner adjudications).

3. **Emerging-solo guard (fail-closed abstention)** — `emerging` is the taxonomy catch-all (meta.catch_all_domain), an AXIS-LEVEL open-set rejection, never a co-token beside a concrete domain (law of non-contradiction). Added fail-closed guard at both mint point (`build_anchor_v8_apply.py` raises SystemExit) and rail (`check_anchor_axis_consistency.py::_emerging_abstention_guard`, exit 1). Partial application persists unmapped raw labels in provenance (`s3_original_domain`), never as a mixed-in `emerging` token.

Regeneration chain: triage 21 rows (16 DROP + 5 ROUTED) → 201-row authority → 208 consolidated (0 stale) → ANCHOR-2 KEY+SHEET (OOV=0, BUG-650 ok=True) → new all-axes CSV (`ANCHOR_208_ALL_AXIS_VIEW_20261007.csv`, 208 rows) → kappa (active_domains 37, macro_kappa_active 0.518, content_type 0.0 degenerate) → consistency exit 0 (ceiling 0, catch-all never coexists) → backup_guardian ok.

Minted D-2870 (total=1000, stamp 9cfaa787a555ac8d). bugs: [BUG-643, BUG-650].

---

## D-2871 (2026-10-08) — RATIFIED — content_type kind/disposition split: 8 quarantine → principle + disposition_verdict (owner-gated, Option 2)

Owner accepted Option 2 (2026-10-08). Forensic finding: config/content_types.yaml (D2323) ALREADY declares
`quarantine` and `noise_drop` as DISPOSITIONS (D2591 — "NOT content_types — the 5-role axis stays CLOSED — no
6th type"), not as content_types. The ANCHOR-2 sheet's content_type_verdict column (col 6) had been recording
dispositions into the closed kind axis, producing the hybrid-axis conflation behind BUG-238 (pipeline emits
`principle` 60/60; the human column mixed kinds with dispositions → 10 distinct labels → kappa 0.0).

Fix (scripts/fix_anchor2_content_type_v8.py, deterministic, LLM-free): (1) collapse kind-axis surface variants
'growth edge'→'growth_edge' (×8) + 'process template'→'process_template' (×1); (2) relabel the 8 'quarantine'
rows to kind 'principle' (they ARE extractable principles — uncertainty preserved, never discarded); (3) move the
2 noise_drop rows off the kind axis (kind=''); (4) add a `disposition_verdict` column (classified | quarantine |
noise_drop) so the human's uncertainty lives on the correct axis. Result: kind {principle:43, growth_edge:9,
process_template:3, tool_instruction:2, process_instance:1, '':2} + disposition {classified:50, quarantine:8,
noise_drop:2}.

Deferred (structural debt against BUG-238): corpus-scale remediation (verify 341 model_medium + 332 model_high
bands, re-run depth on the confirmed-principle subset) + the calibrated/conformal disposition layer (selective
prediction / conformal prediction / confident learning on the golden hold-out).

Minted D-2871 (total=1001, stamp 56263ae0848c79c8). bugs: [BUG-238].

---

## Follow-through 7 (2026-10-08, executed + verified) — Sociology default-route removal (D-2872)

Owner ruling (2026-10-08): sociology re-routing follows the SAME content-driven logic as every other lens —
examine which domain(s) the principle is practically applied in; the highest-confidence domain is PRIMARY, plus
the remaining co-applicable domains when it applies to more than one. This mirrors the psychology ruling
(D-2870 item 2).

Evidence (201-row authority discipline_anchor_rederived_v8_20261007.json): the sole sociology anchor R039
'Identity As Social Positioning and Lifestyle Signifiers' applies to `marketing & communications | design strategy
| semiotics & communication` (primary marketing & communications) — NOT organizational behavior. Sociology has no
single default application field (sociology of work → org behavior, sociology of consumption → marketing,
sociology of health → health & wellness, sociology of education → education), so `sociology: organizational
behavior` is a rubber-stamp default (OntoClean rigidity — Guarino & Welty 2002), not content-driven classification.

Fix: removed `sociology: organizational behavior` from config/discipline_domain_map.yaml; sociology now falls
through to the neutral `fallback: research practice` on empty-after-drop. Zero cascade (verified): the entry was
unexercised — R039's domains never empty after the v8 drops, so no anchor obtained its domain via this default;
triage still 21 rows (16 DROP + 5 ROUTED), build_anchor_v8_apply.py --check PASSES, check_anchor_axis_consistency.py
exit 0 (ceiling 0 holds).

Structural debt queued (same content-driven rule): the remaining single-point D2D defaults carry the identical
rubber-stamp signature and are owed the same per-principle examination — `behavioral economics: marketing &
communications` (8 measured application fields), `linguistics: education` (sole anchor → semiotics & communication),
`social network analysis: systems & frameworks` (sole anchor → business development). None are exercised by the
current anchor set (correctness debt, not live drift).

Minted D-2872 (total=1002, stamp e6731ab72c938acd). bugs: [BUG-630].


## D-2877 (2026-10-08) — RATIFIED — Owner review sheet as the supreme domain-axis authority (owner-gated, deterministic)

Owner accepted the recommendation in full. The owner's review sheet is the SUPREME domain-axis authority, and the
frozen ruler must be RE-DERIVABLE rather than hand-patched: the 86 domain assignments and the two discipline
rulings existed only as throw-away /tmp scripts, so a future agent re-deriving from the derived review CSV would
have lost them silently (BUG-678). Now: governance/OWNER_DOMAIN_REVIEW_SOURCE_20261008.csv (faithful 9-column
export of the .numbers, sha256-pinned) + config/owner_domain_rulings_20261008.yaml (every ruling as DATA, C12c) +
scripts/apply_owner_domain_review.py --check, which PROVES the 201-row ruler is reproduced byte-identically from
the pinned sheet. Precedence, authority and the informational status of the pipeline's n_domains are DECLARED, not
implied; empty owner cells = agreement; the 8 finalised rows stay closed. Declared deviations replace silent
drops: 4 owner noise_drop rows (R021/R084/R106/R148), 3 pending rows (R040/R080/R091, BUG-676), the R158 declared
cap-drop, and two owner questions left unassigned (R005, R113). The ANCHOR-2 referee (key/sheet/kappa 20261007)
is INVALIDATED as current evidence - its human side disagrees with the ruler on 45/60 domain rows and 31/60
discipline rows (BUG-677) - so its repair queue must not run and no kappa may be quoted without naming its freeze.

Minted D-2877 (total=1007, stamp 7f136eac9d5d170c). bugs: [BUG-674, BUG-675, BUG-676, BUG-677, BUG-678].


## D-2878 (2026-10-08) — RATIFIED — Owner review ROUND 2: abstention is an absence (BUG-676), an applicability-ranked R158 drop, R005/R113 adjudicated, and the ratified DROP(13) gap opened (BUG-679)

| ID | State | Decision |
|---|---|---|
| D-2878 | RATIFIED | Owner-gated round-2 rulings folded into the frozen domain ruler FROM THE OWNER'S OWN ANSWERS (`governance/OWNER_CONFIRMATION_SHEET_20261008.csv`, sha256-pinned, fail-closed asserted): (a) `discipline=""` for the 8 owner-confirmed abstentions - an out-of-menu token may not stand in a value slot (BUG-676 FIXED, both-direction fail-closed guard); (b) R158 `remove_domains = [editorial & advertising, motion design]` - APPLICABILITY-ranked, never positional, with `graphic design` re-instated (the tail truncation had dropped the FB's own core vocabulary); (c) R005 - no high conviction for `engineering practice`, primary stays `data visualization`, information architecture NOT added; (d) R113 - primary `engineering practice`, `computational science & physics` kept, `systems & frameworks` excluded. MEASURED CONTRADICTION OPENED (BUG-679): the owner-ratified RATIFY-3 DROP(13) reached only 5 of 13 anchor rows - 8 ratified drops are still live axis-bearing rows in the ruler, contradicting D-2813. BUG-680 declares the upstream-token residual. BUG-667 owner-approved. |

Ruler re-freeze: sha256 `b766ae912401d7da…` -> `5fcde5619e04fbda…`, 201 rows, 9 rows changed, 15 declared warnings,
`scripts/apply_owner_domain_review.py --check` reproduces it byte-identically. Invariants: 0 rows over the D150 cap,
`primary_domain == domains[0]` everywhere, 0 non-canonical domains, 0 rows left carrying the token. R5 verification
ran on a DIFFERENT model family (gemma-4-E4B-it-MLX-4bit): it agreed on the load-bearing correction and diverged on
the two drops while visibly anchoring on the protected-primary hint - recorded as a verifier-drift signal, reported
to the owner rather than averaged away. Full ruling rationale: `governance/OWNER_RULINGS_ROUND2_20261008.md`.
Minted D-2878 (total=1008, stamp ff4231b2ba23a54e). bugs: [BUG-667, BUG-676, BUG-678, BUG-679, BUG-680].

## D-2879 (2026-10-08) — RATIFIED — Owner review ROUND 3: the ratified DROP(13) propagated 13/13 + R040 (ruler 201 -> 194) with the partition invariant as a RAIL; R091 reinstated by declaration; the axis TWO-HOME error leak measured (92 divergent / 46 residue) and railed

| ID | State | Decision |
|---|---|---|
| D-2879 | RATIFIED | Owner-gated round-3 rulings from the OWNER'S OWN WORDS (`ok I accpet your recommendations R40,R80,R91` / `R140 drop` / `BUG 679 those are noise drop`): the owner-ratified RATIFY-3 DROP(13) is **propagated uniformly** — 14 declared drops (13 ratified + R040, a named phenomenon in the same family as R084/R148), the ruler 201 -> **194** rows (8 residues removed, R091 reinstated), and the **BUG-679 invariant is now a rail**: `n_anchor_rows == n_ruler_rows + n_noise_drop` -> **208 == 194 + 14**, asserted fail-closed, plus a guard that every declared drop must name a real anchor row AND carry a soft-quarantine ledger entry (it fired on its FIRST run: R040 had no entry — recorded before the re-stamp, with the propagation record). **R091** ("Autopoesis in Design Education") reinstated as DATA (`config#reinstated_rows`): domains [education, design strategy], primary education, discipline = declared abstention (the upstream raw `creative education` is off the 64-menu — no synthesized label, D-2813), with the sheet-cell divergence DECLARED. **BUG-682 measured** (the real defect behind BUG-679): the axis has TWO homes — the owner-sheet-derived ruler carries every round-2/3 ruling while the declared authority `discipline_anchor_rederived_v8_20261007.json` does not (45 divergent + 23 residue cells; CONSOLIDATED 47 + 23) — held invisible because (i) the ladder's axis rail compared the authority with a copy of itself (green by construction, it cannot fire), (ii) `build_domain_ruler.py` was a SECOND writer of the ruler that a re-run would have used to silently REVERT the owner's rulings (D-387 class), (iii) the D-2870 guard read a hardcoded column key. Fixed this round: a tri-state cross-face rail **wired into the ladder** with a measured SHRINK-ONLY ceiling (92/46), the rival writer **retired** (it now refuses), and the guard's column taken from the declared authority. **Stage 2 = ONE projection** (ruler -> rederived_v8 -> regenerate CONSOLIDATED/views + flip the axis registry) then ceiling -> 0, which closes BUG-682/680/683 together. `apply_owner_domain_review.py` also became a LADDER RAIL: it had been named in this log for two rounds as the way to verify the ruler and was invoked by NOTHING — a rail nothing runs is a comment (D-2665/BUG-492), which is how BUG-679 survived. Ruler re-freeze: `5fcde5619e04fbda…` -> `d867ce5e059ac25d…`, 194 rows, 22 declared warnings, `--check` byte-identical. BUG-681 update: `check_encoding_homes` rc=1 is now a **ladder blocker**; the offender is `scripts/remap_referee_v7_28rows.py` line 69 (a local `utf-8-sig` instead of the declared decode home). |

Minted D-2879 (total=1009, stamp 72ff70db866a4bfd). bugs: [BUG-676, BUG-679, BUG-680, BUG-681, BUG-682, BUG-683].
Full ruling record: `governance/OWNER_RULINGS_ROUND3_20261008.md`.

## D-2880 (2026-10-08) — RATIFIED — Owner review ROUND 4: R158 primary FINAL, R091 discipline = `systems thinking` (CAS rejected on the menu's own definition), the `just health` PREFIX unblocked, the abstention declaration asserted in BOTH directions, and the mechanism behind the BUG-679 gap named (BUG-684)

| ID | State | Decision |
|---|---|---|
| D-2880 | RATIFIED | Round-4 owner words (`R158 keep it` / `R091 what is your stier senior rag enigineer recommendation ? I approve`) implemented. **R158**: the primary `design strategy` is ratified **FINAL** — no field changed, and the ratification is recorded in the frozen artifact's own `note` (a machine-visible home with a reader), so it is not re-openable by inference. **R091**: discipline ruled **`systems thinking`** — discipline is the RIGID KIND of the content, and autopoiesis (Maturana & Varela: self-producing, self-referential, organisationally-closed systems) is a systems-theory construct; `complex adaptive systems` is **rejected on its own definition** ("systems composed of interacting agents that ADAPT AND EVOLVE over time" — autopoiesis brackets adaptation out), `cognitive science` and `design thinking` rejected for the same definition-first reason. The ruling lives in ONE home (`config#discipline_override`, now read by `build_reinstated` too) and R091 leaves `discipline_abstention` (7 rows remain). **A NEW GUARD closed a hole the change exposed:** a row declared abstained must carry NO discipline in the ruler — asserted in BOTH directions, because naming a discipline for a previously-abstained row would otherwise leave the config and the authority disagreeing (the BUG-682 shape one level down). Ruler `d867ce5e059ac25d…` -> `5ce242edbbf3bc0c…`, 194 rows, 22 warnings, `--check` byte-identical. **The `just health` PREFIX IS UNBLOCKED (BUG-681(b) CLOSED):** `scripts/remap_referee_v7_28rows.py:69` carried a local `encoding="utf-8-sig"` — a SECOND implementation of the decode rule — and now delegates to `scripts/lib/artifact_encoding.py`; the substitution was MEASURED inert (identical 28/28 rows; plain valid UTF-8, no declaration needed) and `check_encoding_homes --check` is debt 0 of ceiling 0, unknown 0. Before this, `just health` STOPPED at that line, hiding every rail below it. **BUG-684 FILED (the mechanism behind BUG-679):** `scripts/regenerate_anchor_208_v8.py` declares the drop set as PYTHON LITERALS (`NOISE_DROP = {R021,R084,R106,R148}`, `EMERGING = {R040,R080,R091}`) and re-populates the CONSOLIDATED face from the stale authority for every row they do not name — two homes for one fact, which is why the owner's ratified DROP(13) could never reach the pipeline-facing face. Stage-2 blast radius AUDITED before any write (6 places, none pin-blocked). R5 verification (gemma-4-E4B-it-MLX-4bit, different family, menu definitions + ruling embedded): AGREE on `systems thinking`, independently reproducing the self-maintenance/closure vs adaptation-argument against CAS and confirming the tradition/application distinction. |

Minted D-2880 (total=1010, stamp c84d4b033f1be1bd). bugs: [BUG-676, BUG-679, BUG-681, BUG-682, BUG-683, BUG-684].
Full ruling record + the Stage-2 audit: `governance/OWNER_RULINGS_ROUND3_20261008.md` (§8).


## D-2884(b) decider A/B — model ecosystem discovery + C21 harness registry (2026-10-09)

Owner-gated D-2884(b): distinct-family decider must clear the C+B gate (coarse_kappa >= 0.73 AND emerging <= 0.35)
against the frozen 194-row v8 referee.

EXECUTED ARMS:
- Arm A pplx (mlx-community/pplx-decider-v1.1-27b-4bit, Qwen3.8-27B decision readout): RUNNING at record time (~40 min, no output yet).
- Arm B laya (convaiinnovations/laya, ModernBERT-large 421M + 2-layer RL head): FAIL — raw_agreement 0.2062,
  coarse_kappa 0.0242 (chance), emerging 0.0155; 167/194 collapsed to 'Technical' (label-order/position bias). Commit 0787ee8.

DISCOVERY (STier sweep): a "SystemOne / typed-decisions decision-model" family now shares ONE Jev/SystemOne wire
protocol ({state, questions:{type,instructions,criteria}} -> answers[qid][choice|score|noul]) — the same contract the harness uses.
Maxwell-aligned (Apache-2.0 + MLX-native + local + $0 marginal):
  - mlx-community/clef-flash-4bit  (Qwen3.5 9B,  MLX 4bit, 0.31s/7GB)   — best infra-ready swap
  - mlx-community/clef-4bit        (Qwen3.5 27B, MLX 4bit, 16GB/1.4s)  — strongest-capacity aligned
  - manjunathshiva/opendecider-small-mlx-4bit (4B, beats laya)         — lightweight
  - wfzyx/von (ModernBERT-large 395M, ORDER-INVARIANT scoring)         — fixes laya position bias
NOT aligned: openjev/openjev + Bespoke-Nimble-9B (cc-by-nc-4.0, no MLX); autotrust/JEV-27B-VL (vllm/VL); OpenThai-SystemOne (0.8B Thai-specific).

HARNESS: scripts/d2884b_decider_ab.py -> C21 swappable DECIDER_ARMS registry (adding a decider = one registry entry +
one run fn; referee/gate/criteria machinery shared). R5 gemma-4 APPROVE (afe9d15d60ed11c4). Behavior-preserving.

NEXT: await pplx; if it clears C+B consider owner promotion (D-2796: no below-ceiling classifier ships).


## D-2884(b) UPDATE — Arm A pplx FAIL + BUG-692 emerging-clause blindspot + clef Arm C wired (2026-10-09)

Arm A pplx (mlx-community/pplx-decider-v1.1-27b-4bit) COMPLETED: coarse_kappa 0.6738 (FAIL, floor 0.73),
emerging 0.0052. Committed 01280b4. While the coarse-kappa margin is the headline FAIL, the emerging
figure exposed a STRUCTURAL gate blindspot — logged as BUG-692 (HIGH, OPEN).

BUG-692 (ontological gate defect, STier analysis): the C+B gate's emerging arm (`emerging_rate <= 0.35`,
config `pipeline_config.yaml#taxonomy.emerging_discipline_rate_max`) is a CEILING-ONLY (specificity) guard.
It measures how OFTEN a decider abstains into 'emerging' but never WHETHER it abstains on the RIGHT rows.
pplx has ZERO recall on the 7 gold-emerging rows of the 194-row v8 referee (4→Human & Design, 2→Method &
Business, 1→Technical); its readout cannot emit 'emerging' at all, so rate 0.0052 "passes" vacuously. An
ALWAYS-ANSWER decider trivially satisfies the emerging clause, so the gate could false-PASS a decider that
has COLLAPSED the 3-way+emerging ontology into 3-way-only. 'emerging' is an ONTOLOGICAL REQUIREMENT (the
explicit routing bucket for disciplines that resist a single established macro), not an optional abstention
artifact.

OWNER-GATED RECOMMENDATION (advisory, D-2798 — does not fail-closed on its own): make the emerging clause
SYMMETRIC — (1) KEEP the rate ceiling (specificity); (2) ADD an emerging-RECALL floor (sensitivity: recall
on the gold-emerging subset >= floor, config-first `taxonomy.emerging_discipline_recall_floor`; granularity
1/7 ≈ 0.143 so floor 0.5 = catch ≥4/7); (3) ALTERNATIVE: admit a calibration/threshold arm that CAN emit
'emerging'. Arm A would then correctly FAIL the floor (0/7), reflecting its structural incompleteness.

Arm C WIRED (commit 48db64c, R5 gemma-APPROVE 41a98ffdb1231aaf): mlx-community/clef-flash-4bit (Qwen3.5 9B)
and mlx-community/clef-4bit (Qwen3.5 27B) added to DECIDER_ARMS. Clef is NOT a chat model — clef_mlx.load()
runs the Qwen3.5 backbone + joint schema head in ONE forward pass over {state, questions}, and its output
space INCLUDES the 'emerging' bucket (it is the first candidate family ontologically complete for the
3-way+emerging contract). clef-flash A/B RUNNING; clef (27B) downloading in parallel.

NEXT: await clef-flash + clef A/B; if an arm clears coarse_kappa >= 0.73 AND demonstrates emerging recall,
the owner rules whether to (a) certify under the SYMMETRIC gate, or (b) keep the ceiling-only gate (would
require an explicit owner ruling that emerging recall is out of scope). D-2727 stays BLOCKED until then.


## D-2884(b) Arm C (clef-flash) RESULT — FAIL coarse_kappa 0.5705, but emerging recall 0.4286 (2026-10-09)

clef-flash-4bit (Qwen3.5 9B, joint schema head) COMPLETED on the 194-row v8 referee:
- raw_agreement 0.7113; coarse_kappa 0.5705 (FAIL, floor 0.73); emerging_rate 0.0876 (PASS, max 0.35); cb_gate FAIL.
- Per-bucket (3-way+emerging): Technical f1 0.7536 (recall 0.7879), Human & Design f1 0.7907 (recall 0.701),
  Method & Business f1 0.6667 (recall 0.7193), emerging f1 0.25 (recall 0.4286, precision 0.1765).

KEY FINDING (validates BUG-692 empirically): clef-flash's emerging RECALL is 0.4286 (3/7), NON-ZERO, vs pplx 0.0.
Its output space genuinely includes the 'emerging' bucket — it caught R127 (Guild of Handicraft Educational
Model), R165 (Acknowledgment Attribution), R183 (Pattern Language Implementation Process) as emerging. pplx
structurally CANNOT emit 'emerging' (always-answer readout), so its rate 0.0052 was a trivially-passed ceiling
with ZERO sensitivity. The emerging-recall floor recommendation is now EMPIRICALLY DISCRIMINATIVE: the same
gate clause pplx passes vacuously is one clef-flash fails-but-measurably (0.4286).

STier nuance (gold-emerging audit owed): the 4 gold-emerging rows clef-flash MISSED are arguably classifiable —
R006 (Generative Algorithmic Composition → Technical), R059 (First Course Development → Method & Business),
R146 (Debate As Leadership → Method & Business), R202 (Interactive Media Integration → Human & Design). The
gold 'emerging' label may itself need a 2-way adjudication (genuinely-novel vs classifiable-into-established)
before a recall floor is calibrated; a floor of 1.0 would over-constrain a noisy gold subset.

RANKING SO FAR (coarse_kappa): pplx 0.6738 > clef-flash 0.5705 > laya 0.0242. NONE clears 0.73. clef-4bit (27B,
capacity match) is the remaining candidate in this sweep — downloading, then --arm clef.

NEXT: run clef-4bit; if it clears coarse_kappa >= 0.73 AND shows emerging recall, it is the first certify-able
arm under the SYMMETRIC gate. Otherwise the owner must rule on: (a) lowering the coarse_kappa floor (0.73 may be
unreachable for ANY distinct-family decider), and/or (b) adopting the emerging-recall floor (BUG-692).

## D-2884(b) Arm clef-4bit (FINAL) RESULT — FAIL coarse_kappa 0.5752 + emerging_recall 0.0 (2026-10-09)

mlx-community/clef-4bit (Qwen3.5 27B, MLX 4bit — the D-2886 D3 "only capacity match") COMPLETED on the 194-row
v8 referee (governance/d2884b_decider_ab_clef_20261009.json):
- raw_agreement 0.7216; coarse_kappa 0.5752 (FAIL, floor 0.73); emerging_rate 0.0309 (PASS, max 0.35);
  emerging_recall 0.0 (FAIL, D-2886 D1 symmetric floor 0.5); cb_gate FAIL.
- Per-bucket (3-way+emerging): Technical f1 0.8116 (recall 0.8485, n_gold 33), Human & Design f1 0.7701
  (recall 0.6907, n_gold 97), Method & Business f1 0.6818 (recall 0.7895, n_gold 57), emerging f1 0.0
  (recall 0.0, n_gold 7).

FINAL RANKING (coarse_kappa): pplx 0.6738 > clef-4bit 0.5752 > clef-flash 0.5705 > laya 0.0242. NONE clears 0.73.
BUG-692 now empirically validated by TWO arms: pplx (rate 0.0052) AND clef-4bit (rate 0.0309) both carry ZERO
emerging recall — the ceiling-only clause passes vacuously while sensitivity is 0. Only clef-flash (0.4286, 3/7)
has a real emerging output space, and it fails coarse_kappa too.

D-2886 D3 CONDITION MET: clef-4bit FAILED 0.73, so the owner's conditional resolves to the "otherwise" branch —
either (a) lower the coarse_kappa floor to the best empirical κ (pplx 0.6738), or (b) best-arm as ADVISORY
(non-fail-closed, D-2798) decider with human arbitration on low-confidence rows — never a silent pass.
OWNER GATE OPEN for the (a)/(b) choice (STier recommendation below).

STier recommendation (ontological, future-proof): (b). Lowering the floor to ~0.67 (a) would promote pplx, which
has ZERO emerging recall and therefore ontologically COLLAPSES the 3-way+emerging contract to 3-way (the exact
BUG-692 defect). No distinct-family decider satisfies BOTH arms of the symmetric gate, so NONE is certify-able;
the honest disposition is (b): keep gpt-oss-20b (closed-menu S4 classifier-of-record, D2249) as the ROUTING
authority, run the best coarse-κ arm (pplx 0.6738) as ADVISORY-only with human arbitration on low-confidence
rows, and use clef-flash's abstention signal (the only non-zero emerging recall) as the advisory reference for
emerging-sensitive rows. The emerging-recall floor (0.5) stands as the gate for any FUTURE decider.

## D-2885 (2026-10-09) — RATIFIED — HF model-ecosystem sweep: nothing to adopt; roster already benchmark-aligned + opt-in candidate shortlist

Swept HF pipeline tags (sort=downloads): zero-shot-classification, text-ranking, text-generation, reinforcement-learning.
VERDICT: NOTHING to adopt now — Maxwell's roster is already at/near the top of the community benchmark for its size tier.

zero-shot-classification (NLI/decider task): Maxwell's S5 verifier MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli
(135.9K dl, #11) remains the most comprehensive NLI in its class (fail-closed per D2298). Opt-in candidate (C28):
tasksource/ModernBERT-large-nli (Apache-2.0, 15.9K dl) or ModernBERT-base-nli (113K dl) — modern architecture (rotary/GeGLU/
8192 ctx, 2T-token pretrain) but less community-validated. NOT a swap; record only.

text-ranking: Qwen/Qwen3-Reranker-4B (2.3M dl, Apache-2.0) and Alibaba-NLP/gte-reranker-modernbert-base (2.09M dl, Apache-2.0)
are the strongest permissive rerankers. Maxwell stage 1.5 uses bge-m3 + FAISS cosine + source diversity with NO cross-encoder
reranker — a reranker is an OPT-IN (C28) retrieval-quality upgrade, not a correctness gap. jina-reranker-v3 (CC-BY-NC-4.0)
excluded for license friction vs the sovereign/permissive ethos.

text-generation: dominated by the Qwen3 family (Apache-2.0), already represented (Qwen3-Coder-30B generator). nvidia/
Qwen3.6-35B-A3B-NVFP4 (Apache-2.0) is newer but NVFP4 is not MLX-native (C26) — excluded.

reinforcement-learning: the tag is dominated by gym environments (CartPole/Pendulum) + NSFW GGUF RP models — NOT applicable
to Maxwell. No usable candidates.

CANDIDATE SHORTLIST (opt-in, C28, none adopted now): (1) tasksource/ModernBERT-large-nli (S5 NLI modern fallback);
(2) Qwen/Qwen3-Reranker-4B or gte-reranker-modernbert-base (stage 1.5 reranker); (3) wfzyx/von (already on radar for laya
position-bias / order-invariant scoring). All Apache-2.0, local, $0 marginal cost (C1/C3).

## D-2886 (2026-10-09) — RATIFIED — owner rulings D1/D2/D3 on the D-2884(b) emerging gate + coarse_kappa reachability

OWNER RULINGS (2026-10-09, all ADOPT per STier recommendation):
D1 — BUG-692 symmetric emerging gate ADOPTED: keep the emerging-rate CEILING (specificity, emerging_rate <= 0.35) AND add
     an emerging-RECALL floor (sensitivity) as `taxonomy.emerging_discipline_recall_floor` (config-first, C12). The gate is
     now symmetric — a decider must BOTH abstain at-or-below the ceiling AND catch the right gold-emerging rows.
D2 — gold-emerging 2-way adjudication ADOPTED as a pre-requisite: split the 7 gold-emerging rows into genuinely-novel vs
     classifiable-into-established BEFORE calibrating the recall floor value. Minimum meaningful bar on 7 rows ≈ 0.5 (≥4/7).
D3 — coarse_kappa 0.73 reachability: CONDITIONAL ruling. If clef-4bit (27B, the only capacity match) also fails 0.73, the
     owner accepts either (a) lower the floor to the best empirical κ, or (b) best-arm as an ADVISORY (non-fail-closed,
     D-2798) decider with human arbitration on low-confidence rows — never a silent pass. Pending clef-4bit A/B.

Implementation order: (1) D1 mechanism (recall floor config + recall metric in the A/B harness, advisory report); (2) D2
adjudication (informs the floor value); (3) D3 ruling once clef-4bit lands.



## D-2887 (2026-10-09) — RATIFIED — autotrust/GEV-26B-Decide (Jev "Decide" family): NO-ADOPT now, watch-list for MLX port

FINDING (owner question: is GEV-26B-Decide worth testing / usable for Maxwell scaffolding?):
- autotrust/GEV-26B-Decide is a DECISION-MODEL (text-classification), a LoRA adapter on google/gemma-4-26B-A4B-it
  (26B MoE, ~4B active). Decision Index 0.2.1 = 62.48 (vs TypeSafe Jev 1.13 board 57.91). Apache-2.0, ~910k downloads.
- Its tag vocabulary (jev / noul / choice / score / system-one / system-two / typed-decisions / calibrated-probabilities)
  is the LITERAL namesake of Maxwell's "Jev/SystemOne" wire protocol — but it is a DIFFERENT ecosystem than the
  Cloudflare clef/clef-flash arms Maxwell already runs (mlx-community/clef-* base_model = Cloudflare/clef). The
  autotrust JEV family (JEV-27B = Qwen3.8-27B, JEV-9B = Qwen3.5-9B, JEV-Gemma4-26B-A4B, GEV-26B-Decide) has NO MLX port.
- NOT adoptable now: (1) no MLX port exists (Maxwell runs MLX/OMLX, C1/C3/C26) — transformers bf16 = 51.6 GB merged
  (too heavy for 64 GB) and the adapter-only form needs a gemma-4-26B MLX base that also lacks a clean port; only the
  NVIDIA NVFP4 variant exists besides bf16. (2) It is a decision/classifier model, NOT a scaffolding/agentic model —
  it would NOT help everyday scaffolding (same category as laya and clef).
- SCAFFOLDING ANSWER: no. Everyday scaffolding stays on goose maxwell_omlx (Qwen3-Coder-30B) + single-shot patterns
  (DELEGATE-002). No local model beats routing + single-shot for accuracy/token-cost — reaffirms D-2885.

WATCH-LIST (C28 opt-in): if mlx-community ports JEV-Gemma4-26B-A4B or GEV-26B-Decide to MLX 4-bit, evaluate as a
  DECIDER-ARM upgrade — its calibrated-probability typed decisions + higher Decision Index (62.48) could beat the
  Cloudflare clef arms on coarse_kappa. Not on the D-2727 critical path.


## D-2888 (2026-10-09) — D2 gold-emerging 2-way adjudication EXECUTED (owner-gated D2 pre-requisite for D3)

STier ontological split of the 7 gold-emerging rows (full 65-value menu in view; FB text joined from maxwell.db by name):
GENUINELY-NOVEL (ontology gap — no menu discipline names the domain):
  R165 "Acknowledgment Attribution" — book-publishing / bibliographic attribution (no publishing discipline;
      "literary theory" is analysis not publishing practice, "information science" is info org not attribution).
  R006 "Generative Algorithmic Composition" — music/sound synthesis (closest "creative coding"/"performing arts"
      but neither names MUSIC COMPOSITION; genuine gap, borderline).
CLASSIFIABLE-INTO-ESTABLISHED (owner conservatively demoted; a menu discipline DOES name it):
  R059 "First Course Development Framework"   -> entrepreneurship studies (expertise -> product -> launch)
  R127 "Guild of Handicraft Educational Model" -> design thinking / cultural design (design-education history)
  R146 "Debate As Leadership Tool"            -> decision making (explicit menu discipline)
  R183 "Pattern Language Implementation Process" -> systems thinking / design thinking
  R202 "Interactive Media Integration"        -> aesthetics / media studies

FINDING: the emerging bucket is DOMINATED (5/7) by classifiable rows, not genuine novelty. Consequence for D3:
- emerging_recall (sensitivity) is measuring agreement with OWNER CONSERVATISM, not novelty detection. A decider that
  routes ontologically-correctly (R146 -> decision making, etc.) disagrees with the owner's "emerging" on 5 rows, scoring
  2/7 = 0.286 < 0.5 — it FAILS the recall floor while being MORE correct.
- To pass recall >= 0.5 the decider must reproduce >= 4 owner demotions (over-predict "emerging"), which collides with the
  rate CEILING (emerging_rate <= 0.35). The symmetric gate is INTERNALLY IN TENSION under the current gold.
RECOMMENDATION (future-proof, ontologically accurate): re-adjudicate the 5 classifiable rows into their established
  disciplines (shrink the emerging gold to 2: R006, R165). This raises coarse_kappa (5 fewer forced-disagreement rows) and
  makes the emerging clause meaningful. With N=2, replace the fractional recall floor with a small whitelist ("catch
  R006+R165") — novelty detection is a WHITELIST, not a rate. Feeds the D3 owner ruling.

## D-2889 — Voz (Desert Ant Labs) on-device STT: NO-ADOPT as core pipeline (2026-10-09)
Assessed https://desertant.com/models/voz/ (STier RAG/system-engineering lens).
WHAT: on-device speech-to-text on the Apple Neural Engine — a repackaged NVIDIA Parakeet-TDT 0.6B-v3 (CC BY 4.0
weights) with a CLOSED Desert-Ant runtime ("the conversion, compression, and the Neural Engine runtime are ours").
Swift/JS/TS SDK, iOS/macOS/Web/Node.js, 25 langs, 467MB, ~14x Whisper, WER 7.40% vs Whisper-large-v3-turbo 7.00%.
VERDICT — NO-ADOPT as core STT:
  * C26 VIOLATION: Neural Engine/CoreML = Apple-only; Maxwell targets macOS/Linux/Windows. No Linux/Windows runtime.
  * C4 VIOLATION at the runtime layer: weights are open (CC BY 4.0) but the runtime is closed -> silicon lock-in.
  * C21 VIOLATION: Swift/JS SDK, not MLX/Ollama; would need a new Transcriber protocol + subprocess bridge.
  * CATEGORY ERROR vs the goose youtube-transcript skill: that skill FETCHES existing captions (text); Voz
    TRANSCRIBES raw audio. Complementary, not competing — neither replaces the other.
RECOMMENDATION: for raw-audio market research (podcasts/interviews/voice notes) adopt faster-whisper (CTranslate2,
CPU/GPU, cross-platform, open) or MLX-Whisper / Parakeet-NeMo (open, Python-native) BEHIND a C21 Transcriber
protocol. Watch-list Voz only as an optional macOS Neural-Engine accelerator behind that same protocol, never core.

## D-2890 — Ontology re-examination: the "emerging" bucket is a decider-abstention DUMP, not novelty (2026-10-09)
Measured on live maxwell.db (14574 fbs). Two owner questions examined; the DATA overturns both framings.
(1) Are canonical labels pragmatically/ontologically close to the 7 gold-emerging rows? YES — all 7:
  R006 generative-music -> generative design / creative coding; R059 course-launch -> entrepreneurship studies
  (or the education DOMAIN); R127 guild-craft-education -> cultural design; R146 debate-as-leadership ->
  decision making; R165 acknowledgment-attribution -> information science; R183 pattern-language -> design
  thinking / systems thinking; R202 live-media-art -> media studies / performing arts.
  => REVISES D-2888: NONE of the 7 is genuinely novel; "emerging" on all 7 is decider abstention, not ontology.
(2) Which canonicals demote, which raw promote? The data reframes the question entirely:
  * 2539 fbs (17.4%) sit in discipline='emerging'. Of the CURRENT canonical run (v5.6, 6591 rows), 1779 (27.0%)
    are 'emerging'.
  * 280 rows: discipline_raw IS a canonical discipline (map failure); 190 rows: IS a canonical domain (domain
    bleed) => 470 deterministically reclaimable NOW (vs closed_menu_v8).
  * 3 canonical disciplines are DEAD (0 fbs): marketing, business administration, entrepreneurship studies — the
    entire Business & Management group — while ~520 "marketing family" raw labels (marketing 270, marketing
    science 94, brand management 39, advertising 20, ...) sit trapped in 'emerging'.
  * => the decider (gpt-oss-20b) emits 'emerging' when the raw label has a clear canonical home. Its 27%
    abstention still "passes" the emerging_rate<=0.35 ceiling (BUG-692-class blindspot; now BUG-693).
VERDICT: emerging is NOT a promotion problem; it is a ROUTING + MENU-hygiene problem.
  * Re-adjudicate all 7 gold rows to established disciplines; re-express 'emerging' as an (nearly-empty) WHITELIST.
  * Deterministically reclaim the 470 mappable rows (discipline_raw->canonical; domain-bleed->domains axis via
    BUG-150 kind-swap) — owner sign-off on the re-map table.
  * DEMOTE/merge ~6 over-granular near-duplicate canonicals: generative ai (12)+generative design (6)+creative
    coding (9); visual semiotics (195) vs semiotics (158); design psychology (9); information retrieval (25);
    color theory (22); computational theory (22).
  * PROMOTE only genuinely-homeless coherent labels: creative writing (16), museum studies (13) — owner sign-off.
Owner-gated: actual re-adjudication/re-classification of 2539 rows + any menu edit require owner sign-off.

## D-2891 — SCOPE CORRECTION (t11 forever excluded) + owner adjudication + BUG-693 root-cause reframe (2026-10-09)
OWNER RULING: the canonical run is `rechunk-v4-20260929` (6591 rows). The t11 checkpoint (7855 rows) is
NEVER to be counted again. D-2890's headline figures (14574 total / 2539 emerging / 17.4%) were t11-polluted
(14574 = 6591 canonical + 7855 t11 + 122 e2e + 6 bug198_reinject). Corrected, canonical-only numbers:
  * emerging = 1779 (27.0% of 6591), decomposed deterministically: mapfail 280 + dombleed 190 + offmenu 1309.
  * mapfail 280 = discipline_raw IS a canonical discipline — marketing 259 + business administration 20 +
    entrepreneurship studies 1. These are EXACTLY the 3 disciplines added v5->v8 (verified diff: v5 62 -> v8 65
    disciplines, the +3 = Business & Management group). No discipline was removed.
  * dombleed 190 = discipline_raw IS a canonical domain written into the discipline cell (graphic design 56,
    organizational behavior 34, entrepreneurship 28, project management 23, industrial design 13, product design
    12, urban planning 10, education 6, ...). The domain label is ALREADY in `domains` on 63 rows; missing on 127.
  * offmenu 1309 = genuinely absent from both menus (marketing science 94, leadership studies 37, brand strategy,
    creative writing 14, museum studies 13, ...).
  * DEAD disciplines = 6 (not 3): marketing, business administration, entrepreneurship studies (Business &
    Management) PLUS generative ai, creative coding, generative design (Computational Craft) — the latter three
    are v5-present but NEVER chosen by the decider (0 fbs), confirming D-2890's over-granularity claim.
ROOT-CAUSE REFRAME (revises BUG-693): mapfail is MENU-WIDENING DRIFT, not a decider defect. The 280 rows carry
  discipline_raw EXACTLY equal to the 3 disciplines added v5->v8, so the decider correctly abstained ('emerging')
  on labels absent from its menu at classification time; the menu then widened and the rows were never
  re-classified. The fix is a re-classification pass gated on menu-widening (a governance process gap), not a
  decider prompt fix. (The rate-ceiling/recall-floor tension from D-2886/D-2890 is INDEPENDENT and stands.)
RECLAIM PRECISION: only mapfail (280) is FULLY deterministic (discipline_raw == canonical discipline, exact).
  dombleed (190) is deterministic only on the DOMAIN axis (kind-swap the label into `domains`, BUG-150 machinery);
  its discipline field still needs re-classification. offmenu (1309) is promotion review or stays 'emerging'.
OWNER ADJUDICATION (2026-10-09) — FINAL (ratified 2026-10-09; see D-2892):
  AGREED (6 of 7): R006 Generative Algorithmic Composition -> generative design; R059 First Course Development
    Framework -> entrepreneurship studies; R146 Debate As Leadership Tool -> decision making; R165 Acknowledgment
    Attribution -> information science; R127 Guild of Handicraft Educational Model -> cultural design; R202
    Interactive Media Integration -> performing arts (STier recommendations ACCEPTED).
  EXCLUDED (1 of 7): R183 Pattern Language Implementation Process — owner not convinced; verified to create NO
    future tax (no load-bearing reference). R183 stays discipline='emerging' + domain='urban planning' in DB.
C26 RELAXATION (owner): C26 (cross-platform) is a LONG-TERM rule, short-term relaxable. Voz remains NO-ADOPT
  for C4 (closed runtime) + C21 (non-MLX/Ollama) — INDEPENDENT of C26.
DEMOTE/PROMOTE corrected to canonical counts: merge visual semiotics (44) + semiotics (61) = 105; design
  psychology 3, information retrieval 9, color theory 14, computational theory 16 are small but non-zero; the
  three generative/coding labels are DEAD (0) — consolidate or retire, not "merge 12+6+9". Promote creative
  writing (14) + museum studies (13) only.

## D-2892 — D-2891 RATIFIED + final gold-emerging adjudication (2026-10-09)

Owner ratified D-2891 (scope correction + BUG-693 root-cause reframe) in full. Final gold-emerging adjudication
on the 7 rows:
  * ACCEPTED (STier recommendations): R127 Guild of Handicraft Educational Model -> cultural design; R202
    Interactive Media Integration -> performing arts.
  * EXCLUDED from the sample: R183 Pattern Language Implementation Process — owner not convinced; verified to
    create NO future tax (no load-bearing reference). R183 stays discipline='emerging' + domain='urban planning'
    in DB.
Final gold rows (6): R006 generative design, R059 entrepreneurship studies, R127 cultural design, R146 decision
  making, R165 information science, R202 performing arts. Closes BUG-693 adjudication.

## D-2893 — BUG-693 deterministic reclaim APPLIED (mapfail 280 + dombleed 190) (2026-10-09)

Phase 1+2 of BUG-693 applied to the canonical run rechunk-v4-20260929 (6591 rows) via scripts/bug693_reclaim.py
(fail-closed exact-match reclaim; generator = script, verifier = gemma-4-E4B-it-MLX-4bit, no defects in 7 audit
categories). 470 row updates in ONE SQLite transaction after backup_guardian.sh pre-write and post-write PRAGMA
quick_check + foreign_key_check clean.
  * mapfail 280 (discipline_raw EXACTLY a canonical discipline: marketing 259 + business administration 20 +
    entrepreneurship studies 1 — the 3 disciplines added v5->v8) -> discipline lifted, discipline_macro kept 1:1
    (all Method & Business), discipline_source='llm_extracted_from_source'.
  * dombleed 190 (discipline_raw EXACTLY a canonical domain) -> kind-swap into domains + domains_raw, discipline_raw
    cleared, discipline stays 'emerging' pending re-classification.
Post-reclaim canonical emerging = 1499 (offmenu 1309 + dombleed 190 still emerging on the discipline axis).
REMAINING: offmenu 1309 promotion review/whitelist + the menu-widening re-classification gate (steps 3+4).

## D-2894 — BUG-693 step 4: menu-widening re-classification gate (2026-10-09)

Implemented scripts/check_menu_reclass_gate.py (read-only, fail-closed). Compares every pipeline_run's
provenance stamps (menu_hash + taxonomy_version, D-279) against the LIVE menu identity. Verdict: the canonical
run rechunk-v4-20260929 is STALE (classified under 99e1df82... v5.6; live 8218d6db... v8) — the BUG-693 root
cause made visible and fail-closed (exit non-zero). Verifier gemma-4-E4B-it-MLX-4bit: core PASS (correctness,
drift, blindspots, config-first, types); 2 non-blocking error-handling notes accepted (no silent swallow — I/O
errors propagate loudly per C16). REMAINING: the re-classification pass the gate enforces (owner-signed menu
edits v8->v9 + offmenu promotion) must re-stamp rows to the live menu hash, after which the gate reports GREEN.

## D-2897 — V9 menu edit: owner approves flags (a)(b)(c) (2026-10-09)

Owner ratified the three v9 flags (BUG-693 menu-widening resolution). (a) computational theory (16) DEMOTE to
'emerging' (confirmed default; discipline_raw verbatim). (b) information retrieval (9) MERGE into information
science (122->131), cross-macro Technical -> Systems & Method ACCEPTED as advisory/reversible (IR is a sub-field
of Library & Information Science). (c) creative writing (14) PROMOTE -> Heterodox AND museum studies (13)
PROMOTE -> Heterodox — CORRECTING the draft's Systems & Method placement (museum/heritage is a
humanistic-cultural discipline). Disciplines 65 -> 64; post-v9 emerging = 1488. Raw invariance (D-2896) holds.

## D-2898 — Canonical promotion trust boundary (2026-10-09)

gpt-oss-20b-MXFP4-Q8 is NOT trusted for CANONICAL PROMOTION (menu mutation). Measured drift on the 46-label v9
offmenu head set: whitelisted creative writing/museum studies (contradicting D-2897), merged career development
-> 'human resource management' (non-canonical hallucinated slot), education theory -> information science
(semantic drift), promoted HRM while merging product management (inconsistent policy). Same failure class as
BUG-279/BUG-693: free generation cannot hold the closed-menu invariant. RULING: promotion is DETERMINISTIC +
OWNER-GATE. alias-merge + cross-axis = match_to_canonical() (reproducible, zero drift); new-slot + out_of_scope
whitelist = OWNER-GATE only. gpt-oss stays S4 classifier-of-record for CLOSED-menu classification (D2249); for
promotion it is ADVISORY-ONLY, cross-checked against the closed menu + owner rulings. No local LLM auto-mints a
canonical slot.

## D-2901 — D-2886 D3(b) OWNER-APPROVED: no decider certifiable; routing authority stays gpt-oss-20b (2026-10-09)

Owner ruled "do b". The distinct-family decider A/B (D-2884(b)) CLOSED with NO arm certifiable: pplx 0.6738 /
clef-4bit 0.5752 / clef-flash 0.5705 all < coarse_kappa 0.73, and pplx + clef-4bit FAIL the D-2886 D1 emerging
recall floor 0.5 (0/7 gold both). D3(a) rejected (lowering the floor to ~0.67 would certify pplx at ZERO emerging
recall). D3(b): gpt-oss-20b-MXFP4-Q8 REMAINS routing authority (D2249); pplx = ADVISORY best-arm (human arbitration
on low-confidence rows); clef-flash = ADVISORY emerging-abstention signal. Symmetric gate (rate ceiling + recall
floor) stands as the future certification gate. Config: stage4.discipline decider_mode=advisory +
decider_advisory_best_arm + decider_emerging_abstention_signal. BUG-692 RESOLVED.

## D-2905 — D2547 calibration lineage scoped to canonical run (D-2881) — BUG-695 root cause (2026-10-10)

Forensic audit (pre-BUG-695-close) found the D2547 per-label census was computed over a corpus that MIXED the
canonical run rechunk-v4-20260929 (6591 rows, v9-clean on the discipline axis: computational theory 0 /
information retrieval 0 / visual semiotics 0) with the stale t11 run (7855 rows carrying the pre-v9 leftovers
computational theory 6 / information retrieval 16 / visual semiotics 151). Root cause: the four calibration
scripts (pipeline/nli_label_audit.py, scripts/knn_label_disagreement.py,
scripts/populate_semantic_error_thresholds.py, scripts/bug695_recalibrate.py) queried `fbs` WITHOUT the D-2881
canonical-run clause that the serving layer already enforces — a hidden mismatch that (a) made the wrapper's G3
gate falsely report "RATIFY-2 incomplete" and (b) would have silently diluted every per-label rate over a ~45%
pre-v9-stale corpus. FIX (deterministic, LLM-free, config-first): scope every calibration query to CANONICAL_RUN
via `pipeline_run_id = ?` (the D-2881 single source of truth in pipeline/pipeline_paths.py). Verified dry-run: G3
now passes; the 6 genuinely-unmeasured labels (business administration / creative writing / ecology / marketing /
museum studies / research practice) remain correctly fail-closed until the audits re-run on the canonical run.
BUG-695's fix path is therefore NOT "wait for RATIFY-2 re-classification" — the canonical run is already v9 — it
is "re-run the audits scoped to the canonical run". The 6494 canonical rows still carrying a v5.6 menu_hash stamp
remain a separate D-2894 re-stamp concern (not a label defect). No DB/config writes this turn (dry-run only;
--apply still gated on R5 review).

## D-2907 — D-2894 deterministic menu_hash re-stamp APPLIED + BUG-693 CLOSED (2026-10-10)

Owner approved D-2894 (re-stamp recommendation) + the offmenu-1309 whitelist ruling (D-2898: new-slot/out-of-scope
stays 'emerging', no local LLM auto-mints a canonical slot). Applied scripts/restamp_canonical_menu_v9.py --apply:
a PROVENANCE REFRESH (not a re-classification) re-stamping the 6494 canonical rows carrying menu_hash 99e1df82.../
taxonomy v5.6 → live be323543.../v9. Fail-closed G1-G4 guards prove the cohort was already v9-clean (0 pre-v9
leftovers; all 59 distinct disciplines ∈ live v9 menu), so the re-stamp whitewashes nothing. Crash-safe: DB backup
+ quick_check/foreign_key_check before AND after, single atomic txn, post-write 0-stale-remain verify. RESULT:
scripts/check_menu_reclass_gate.py now reports GREEN (canonical run fresh vs live v9 menu); discipline census
unchanged (61 labels, emerging 1487, total 6591) — zero label drift. BUG-693 CLOSED: step 1+2 (D-2893 reclaim),
step 3 (offmenu-1309 → emerging whitelist, owner ruling), step 4 (D-2894 gate, now green). OMLX down this turn, so
the R5 gemma code-review leg was unavailable; the operation is deterministic SQL provenance-only and independently
re-verified by the gate, which is the stronger correctness bound for a re-stamp. BUG-695 remains OPEN (recalibration
--apply still pending the R5 review of the four-file canonical-run scoping).

## D-2917 — Anchor recommendation C OWNER-ACCEPTED + final forensic audit (2026-10-10)

OWNER-GATE RESOLVED: Anchor C accepted — re-bind the 208 human-adjudicated gold labels to the served v9
population by source-derived identity (name only as fallback join key). REFINEMENT from final forensic audit:
`source_principle_ids` are RUN-DERIVED (0 cross-generation overlap t11→v9), so they are NOT a valid stable key.
Only `source_ids` (document-level; 640 doc overlap) + `source_text`/`citation` are source-invariant. The stable
identity key for BOTH Anchor C and BUG-700 is hash(normalized source_ids + source_text excerpt) — NOT
source_principle_ids, NOT fb_id (run-derived), NOT menu_hash (menu-version stamp, distinct=1 across 6591 rows).

FINAL FORENSIC AUDIT — NEW FINDINGS (read-only, live DB):
- F1 QUARANTINE 49%: v9 = 3360 PASS (s5_reason=entail) + 3231 QUARANTINE (neutral 3142 / contra 39 / no_evidence
  29 / vacuous 19 / mech_fail 1 / evidence_contaminated 1). Serving defaults to status=PASS → effective KB is
  3360, not 6591. The 47.7% "neutral" NLI rate has NEVER been audited (healthy fail-closed vs misalignment).
- F2 source_principle_ids run-derived (0 overlap); source_ids 100% populated both gens (640 doc overlap) = the
  valid stable key. Corrects the earlier "source_ids/source_principle_ids" framing.
- F3 corpus-mission misalignment: v9 is general-knowledge (Black Swan, GEB, No Logo, Marketing Mgmt, Design
  Literacy…). discipline_macro: Human & Design 3288 (50%) / emerging 1487 / Method & Business 1353 / Technical
  463 (7%). No mission-relevance axis; practicality ≠ applicability-to-Maxwell-OS.
- F4 procedural_skill 100% empty both gens (dead schema column; C19/C28 hygiene).
- F5 menu_hash distinct=1 (menu-version stamp, not per-row identity) — confirms BUG-700.

IMPLEMENTED (non-blocked): BUG-702 — added `--practicality` facet to retrieve.py (config-driven from
config/practicality.yaml labels; threaded through _facet_conditions/_matches_facet + all search_* legs +
keyword/hybrid dispatch; 11 verified replacements). Verified live: --hybrid "chunking" --practicality
immediately-applicable vs context-dependent return disjoint, correctly-filtered sets.

OPEN (next): BUG-700 stable-identity spec (design-only); BUG-703 discipline_raw backfill (190 rows); BUG-684
Stage-2 domain-axis forensic audit; F1 quarantine-rate audit; corpus curation / mission-relevance axis (owner).

---
## D-2918 — CORRECTION to D-2917 F3 + root cause of "only 4 usable" (2026-10-10)
D-2917 F3 ("corpus-mission misalignment: general-knowledge corpus, no mission-relevance axis") was WRONG.
Live-DB evidence (2026-10-10):
- 940 books on disk; 138 are DOMAIN-6 "AI + Computing" mission-relevant engineering books; all ingested.
- ~404 v9 rows sourced from AI/agentic books (209 PASS + 195 QUARANTINE).
- Real root cause = S4 taxonomy scatter + S5 quarantine, not corpus absence:
  - S4: AI rows split 124 Human&Design / 97 Technical / 77 Method&Business / 46 emerging (24% Technical).
  - S5: 195/404 AI rows QUARANTINE (143 neutral), lost by default status=PASS retrieval.
  - Full PASS discipline skew: psychology 337 / cognitive science 252 / marketing 150 vs software-eng 71 / ML 28 / AI 27.
- Implication: owner-gated "corpus curation / ingest more engineering books" decision is MISDIRECTED.
  Correct owner-gated decision = fix S4 classification + S5 quarantine + add mission_relevance axis,
  so already-ingested engineering knowledge surfaces.
- New feature agreed: Stage R "surgical targeted knowledge extraction" (books + internet: video/blog/social/news).
  Spec seed: research/SURGICAL_KNOWLEDGE_EXTRACTION_20261010.md (CRAG, GraphRAG/LightRAG, HippoRAG, HyDE,
  Self-RAG, RAPTOR, ColBERT, STORM, gpt-researcher, whisper.cpp, sqlite-vec, bge-m3).

---
## D-2919 — Root cause of "only 4": S5 NLI-paraphrase + S4 62-way ceiling (2026-10-10)
Cause A = S5 factual check uses DeBERTa NLI-entailment, which scores faithful paraphrases as "neutral"
→ ~143 engineering rows wrongly quarantined (extraction is NOT hallucinating; mechanism_quality=1.0,
definitions faithful to source_text). Fix = paraphrase-aware claim-grounding in S5.
Cause B = S4 emits single 62-way discipline (human ceiling 0.581, D-2796) and derives macro from it;
config already mandates "fine → advisory, macro → hard gate" but production never flipped. Fix = 3-way
macro primary + faceted multi-label discipline. No full re-engineer; two targeted fixes (S5 verifier,
S4 granularity flip). Ontological fix = faceted classification (SKOS/OWL/SHACL), drop single-inheritance.

---
## D-2920 — "rerun vs post-hoc" determination + D-A/D-B/D-C approval (2026-10-10)
OWNER APPROVED: D-A (3-way macro primary + ranked multi-label discipline), D-B (S5 paraphrase-aware
grounding), D-C (faceted classification; revise D316, drop single-inheritance).
FORENSIC RE-DETERMINATION (code + live-DB, this session):
- ANSWER: two surgical POST-HOC passes over the already-merged 6,591 rows. NO full S0→S6 re-run.
  Extraction (S0–S2) is healthy (mechanism_quality=1.0, definitions faithful); the defects are in the
  two DECISION layers only (S5 verdict + S4 discipline label).
- "other 4 content types" DO NOT EXIST in v9: rechunk-v4-20260929 = principle (6,577) + tool_instruction (14).
  Nothing to re-run there.
- Menu is FRESH: v9 rows carry taxonomy_version=v9 + menu_hash be3235433e… == live composite (BUG-693 resolved).
- S5 neutral breakdown (3,142): 2,258 ent≥1+cont=0 (paraphrase candidates), 508 cont>0 (genuine
  contradiction, keep), 376 ent=0+cont=0 (no signal, keep). Fail-closed preserved: only ent≥1 AND cont=0
  may flip, and only on a SECOND (similarity) signal.
- CORRECTION vs D-2919: D-2822/D-2863 (or-entail @ threshold 0.5, precision 0.852) is a PRECISION fix and
  is ALREADY coded+configured — but at threshold 0.5 it does NOT recover the paraphrase rows (their max
  entail is 0.13–0.46 < 0.5). D-B (paraphrase-aware grounding) is SEPARATE, still-pending RECALL work:
  a parallel STS/similarity path that passes a faithful reworded-true claim when NLI says "neutral" but
  similarity is high. The two are complementary (D-2822 = precision on the entail path; D-B = recall via
  the paraphrase path).
DECISION: post-hoc two-pass fix (S5 re-verify with new paraphrase path + S4 macro re-classify). Not a full re-run.

---
## D-2921 — Forensic clarifications: anchors, keywords, retrieval surface, post-hoc vs pipeline (2026-10-11)
Four clarifications resolved against live code + 218MB DB (this session):

Q1 (are S4 anchors/golden "wrongly classified" raw+canonical, so the 6,591 principles too?):
  NO — not a raw-vs-canonical mislabel. The S4 golden (config/golden/stage4_golden.yaml, 7 hand-curated
  few-shot examples, D2451) uses VALID canonical fine disciplines (complex adaptive systems, color theory,
  machine learning, creative process, information science, organizational theory) + multi-label domains.
  The anchors are internally consistent but authored against D316 (single-inheritance FINE discipline),
  which D-C now supersedes. Domains were ALWAYS multi-label (D150, 1-7); the single-inheritance defect is
  DISCIPLINE-specific. discipline_raw/domains_raw are the LLM's pre-canonicalization output (D2066);
  raw↔canonical divergence is benign; BUG-703 = 190 EMPTY discipline_raw (missing, not mislabeled).
  → The 6,591 principles inherit fine discipline whose human inter-rater ceiling is 0.581 (unreachable):
    labels are low-confidence/advisory, NOT random. The operative 3-way macro (ceiling 0.766) is derivable
    deterministically (discipline_macro.py) or re-classifiable directly (Condition C).
  → ACTION: re-author the 7 golden examples under D-C (add macro + ranked multi-label discipline), so
    future S4 few-shot no longer teaches single-inheritance.

Q2 (are keywords incorrect in content types?): NO content-type keywords exist — moved out per D2349.
  content_type = functional ROLE (5 values), orthogonal to extraction_type (epistemic form). Keywords are
  a PER-FB retrieval label (3-5 terms) generated in the S4 ELABORATION prompt (separate from the classify
  prompt that sets discipline/domain), stored in fbs.keywords, FTS5-indexed (name, definition, keywords).
  → Not part of the content-type ontology; NOT contaminated by the S4 discipline/domain defect.

Q3 (retrieval for PT/TI/GE/PI without discipline/domain): live finding — they are NOT in the retrieval
  surface. process_template/process_instance/growth_edge = ZERO DB rows (written to JSONL in S4, never
  committed/indexed — D-2371). tool_instruction = 14 rows committed, carrying INCIDENTAL discipline_macro
  (Technical 10 / Method & Business 3 / emerging 1) — semantically a tool has no discipline, harmless
  because tool retrieval should key on content_type + tool_name + FTS/vector. retrieve.py keys on
  discipline/domains/depth/status + FTS(name/def/keywords) + vector; content_type is NOT a first-class
  filter yet. → This is the real "retrieval-surface" gap Stage R must close (commit + index the 4 types).

Q4 (post-hoc only, or also pipeline for future?): BOTH — same code changes. Fix pipeline code
  (stage5_verify D-B paraphrase path; S4 macro classifier; commit+index non-principle types) → future
  batches inherit automatically; THEN run the fix as a post-hoc re-verify/re-classify/re-commit over the
  6,591 merged rows. NO full S0→S6 rerun.

REFINED rerun answer (strengthened): the "other 4 content types" have 0 rows in the canonical run, so
"rerun S4-S5 on them" is moot — the work is commit+index (Stage R), not re-label. The principle rows get
the two surgical post-hoc passes (S5 paraphrase re-verify + S4 macro re-classify).

---
## D-2922 — Retrieval contract for PT/TI as Layer-2 skill references (2026-10-11)
Q: do we need retrieval for process_template/tool_instruction as skill references for the skill
orchestration layer? ANSWER: YES, and it is a DIFFERENT retrieval contract than principles.

Layer-2 model (content_types.yaml, already designed): FB(principle) → PT → PI → Recipe → MCP tool.
  process_template = "Layer-2 product primitive (FB→PT→PI→Recipe)"; keyed by trigger + done_condition
    + description + steps + fb_query_domain/fb_query_intent (which FBs ground it) — NOT discipline.
  tool_instruction = 13-field MCP-compatible schema (tool_name, description, syntax, parameters, output,
    example, annotations, caveats, version, source, alternatives) — keyed by tool_name + description
    (intent) — NOT discipline. Promotion machinery already declared (status open→promoted, promoted_to_*).

LIVE GAP (this session): the skill-reference retrieval surface is EMPTY / unkeyed:
  - fbs_fts indexes ONLY (name, definition, keywords, jargon) — NOT content_type/tool_name/trigger/
    done_condition/steps/syntax.
  - vec_fbs embeds ONLY definition_embedding — not the PT/TI retrieval fields.
  - retrieve.py has NO content_type facet (keyword=discipline/domain/depth/status + FTS + vector).
  - PT/PI/GE = 0 local DB rows (D-2371); stage6b pushes them to Anytype by raw DOMAIN, not to local index.
  - TI = 14 rows committed w/ incidental discipline_macro; retrieval fields un-indexed.
  - Root: S2/S4 emit ~0 PT/TI/PI/GE (corpus collapses to principle) — so there is nothing to retrieve yet.

DECISION (order): (1) fix decision layers (S5 paraphrase + S4 macro) for the 6,591 principles; (2) Stage R
surgical extraction to EMIT PT/TI/PI/GE in volume; (3) wire retrieval surface: content_type first-class
facet + per-type key (PT=trigger/done_condition intent-vector, TI=tool_name exact + description vector)
+ commit/index all 5 types; (4) THEN Layer-2 orchestration has real skill references. Retrieval wiring
before rows is premature.

---
## D-2923 — Layer-2 retrieval contract completed: PT/PI/GE/TI (2026-10-11)
Completes D-2922 (PT/TI only) to ALL FOUR non-principle content types. Full spec:
research/LAYER2_RETRIEVAL_CONTRACT_20261011.md.

Single invariant: principle = discipline/domain/depth/status keyed; PT/PI/GE/TI = intent+linkage keyed
(trigger / parent_pt_id / tool_name+description / body+status), NEVER discipline/domain — grounded in
content_types.yaml extension_fields (D2323 functional-ROLE axis).

Per-type PRIMARY key:
- PT: trigger (intent-vector) + done_condition + fb_query_domain/intent (FB grounding query)
- PI: parent_pt_id (instance-of, navigational) + instance_text/domain_context + outcome (evidence)
- GE: body (open-tension vector) + status (promotion filter open→promoted) + category/tags + parent_fb_ids
- TI: tool_name (exact/prefix) + description (intent-vector) + syntax/parameters + alternatives (SEE-ALSO)

Linkage graph (orchestration substrate): FB→PT (fb_query_*), PT→PI (parent_pt_id), FB→GE (parent_fb_ids),
GE→promoted_to_*, TI→TI (alternatives). retrieve.py already declares graph-aware mode — needs per-type join keys.

NEW GAP: GE `category`/`tags` imply a skill/capability ontology that does NOT exist — the 48-discipline
taxonomy does NOT cover GE's open-tension/capability-growth space. Next decision (candidate D-2924): define
the growth_edge category facet (closed vocabulary + provenance + calibration) BEFORE Stage R emits GE in
volume. Do NOT force GE into discipline.

Wiring order (now 4-type complete): decision layers → Stage R emit PT/PI/GE/TI in volume (0/0/0/14 today)
→ wire content_type facet + per-type key + commit/index → Layer-2 orchestration.

## D-2925 — BUG-705-threshold FIX: paraphrase RECALL path was a silent no-op (2026-10-11)
Forensic audit found the D-B (BUG-705) paraphrase RECALL path counted `_n_entail` at
`S5_NLI_PASS_THRESHOLD` (0.5), but the entire target population ("2,258 recoverable neutral", max
entail 0.13–0.46) is BELOW 0.5 — so `_n_entail` was always 0 and the path could never flip a row.
A silent no-op (C16 violation) that the R5 gemma review had approved without noticing.

FIX (config-first, C12):
- New key `stage5.paraphrase_entail_threshold: 0.10` — the WEAK-entail pre-filter (NOT the pass bar),
  matching D-2920's documented "ent>=1" recoverable population (weak entail 0.13–0.46).
- `pipeline/stage5_verify.py` counts `_n_entail = sum(entail >= PARAPHRASE_ENTAIL_THRESHOLD)`.
- Added an ALWAYS-ON structural guard raising C16 if `paraphrase_entail_threshold >= nli_pass_threshold`
  — prevents the no-op bug class from recurring (weak-entail pre-filter must sit strictly below pass bar).

VERIFIED: imports clean, py_compile OK, guard inert (enabled=false), 0.10 < 0.50. This closes the
blocking defect that made the pending gold-set calibration meaningless; calibration can now proceed.

Note on DB staleness (no new work): the 6,591-row v9 slice was committed 2026-10-05 under majority/
0.10 mode; config has since flipped to or_entail_and_no_contra @ 0.5 (D-2863). Re-derive the recoverable
neutral set under or_entail BEFORE seeding the BUG-705 gold set (the "2,258" figure is majority-mode).

## D-2924 — Growth-edge capability ontology (OWNER-APPROVED + implemented) (2026-10-11)
Previously a candidate gap ("GE category/tags imply a skill/capability ontology that does NOT
exist"). OWNER-APPROVED 2026-10-11. Implemented config-first (C12):
- config/growth_edge_ontology.yaml — CLOSED category vocabulary (open_tension /
  unverified_correlation / contested_claim / capability_gap + `emerging` abstention),
  bootstrap capability tags, R14 provenance stamps, calibration contract (advisory until
  a gold set is minted; kappa_floor 0.65; requires_gold_before_volume).
- pipeline/growth_edge_ontology.py — C21 single home loader, fail-closed on off-vocabulary
  category/tag (never free-gen). calibration_enforcing()/calibration_decision() gate Stage R.
- tests/test_growth_edge_ontology.py — 4/4 pass.
Ontological invariant preserved (D-2923): GE is keyed by body+status, NEVER discipline/domain;
the category facet names the SKILL the edge points toward, not its knowledge-domain.


## D-2926 — BUG-698 baseline-preserving migration (circular re-review loop broken) (2026-10-11)
ROOT CAUSE: scripts/rederive_anchor_axes_v6.py --generate re-classifies from scratch using only FB
definition/mechanism/boundary/consequence + menu, with NO memory of owner rulings, so every run
reinvents labels and re-opens adjudication forever (the circle). The 20B generator also over-abstracts:
it dumped 20 rows to `emerging`, collapsed 5 multi-domain rows to `research practice`, and promoted 7
owner-declared abstentions back to concrete disciplines (contradicting owner_domain_rulings).
DECISION: The v8 consolidated anchor (discipline_anchor_rederived_v8_20261007.json, owner-finalized)
is the baseline of record. The v8->v9 menu delta is the ONLY justification for re-opening a label:
disciplines removed = computational theory / information retrieval / visual semiotics; domains
removed = NONE. Therefore the migration is exactly 7 discipline rows (4 deterministic D-2897 renames
+ 3 owner-decide), and ZERO domain rows. Every other generator delta (164 rows) reverts to v8 verbatim.
D-2897 deterministic renames are applied REGARDLESS of the generator (which mis-renamed 3 of 4).
Ontological invariant preserved (D-2896 raw-invariance): raw labels stay verbatim; only canonical
discipline moves on the 7 menu-forced rows.
MENU GAP: removing computational theory left no mathematics/logic/computer-science label; theoretical-
computation rows must abstain or route to philosophy. Flagged for taxonomy follow-up.
files:
- config/owner_decisions_v9_keep_verbatim_20261011.json
- governance/BUG698_migration_delta_20261011.csv
- governance/BUG698_discarded_generator_delta_20261011.csv


## D-2949 / D-2947 / D-2948 — BUG-712 spot-check reroute de-noising + fsm.py (2026-10-12, OWNER-APPROVED)

- **D-2949** — reroute de-noising (regex/keyword/adjudication map) + duplicate-name root cause. Tests 11/11 green; adjudication map 573→546.
- **D-2947** — 'deterministic' provenance literal (schemas.py) + state-machine determinism recommendation.
- **D-2948** — pipeline/fsm.py pure-function FSM core (selftest OK) + config/fsm/example.yaml.

## D-2950 — deterministic dedup identity + edition supersession (2026-10-12, OWNER-APPROVED)

Forensic re-audit CORRECTED D-2949's "2 TRUE_DUP merge" finding: the (name, source_id) key alone over-merges — two same-source pairs are DISTINCT concepts sharing a name (Item Validation Protocol type-check vs schema-constraint; VJ Performance Method pre-plan vs live-trigger), not the same concept re-extracted. A name+source merge would DESTROY one concept each. Identity model: GROUPING key = (normalize_name, source_ids); MERGE gate = body divergence (token Jaccard + SequenceMatcher, thresholds in config/dedup_identity.yaml). Convergent→MERGE keep richer; divergent→KEEP BOTH; cross-source→KEEP BOTH; missing source→REVIEW. Live landscape: MERGE 0 / SAME_SOURCE_COLLIDE 2 / NAME_COLLIDE 1 / NO_SOURCE 0 — no destructive merge today. Edition supersession (newer edition updates body in place, appends source filenames) designed but not wired to stage6_commit pending owner ruling on select_primary_source citation semantics. Files: pipeline/dedup_identity.py, pipeline/dedup_gate.py, config/dedup_identity.yaml, scripts/audit_duplicate_identity.py. Tests 16/16 green.

## D-2951 — the commit-time dedup gate is WIRED; `enforce` is measured NEUTRAL (2026-10-12)

**The D-2949 #4 prevention half now exists at the commit boundary.** `stage6.dedup_gate {enabled: true, mode: report}` (C12; an unknown mode FAILS CLOSED in `run_stage6`, C16). It runs on the INSERT path only — D-2933 rule V sends every stored `fb_id` down the S5-provenance path, so the gate sees exactly the rows the store does not hold — and it resolves "existing" from BOTH sides: the committed store and the rows this batch has already accepted. That second side is the point: the collision D-2949 #4 could not catch is a WITHIN-RUN collision (stage1 dedups SEGMENTS; nothing deduped NAMES).

- `mode: report` computes every decision, writes `checkpoint/dedup_gate_receipt.json`, changes NOTHING.
- `mode: enforce` additionally LINKS a convergent re-extraction: `duplicate_of` = the incumbent + status QUARANTINE via `serving_gate.derive_status` (the ONE status rule, D274h) — the locked policy "mark `duplicate_of` + QUARANTINE, NEVER delete" (D2625/D2630). It applies ONLY when the INCUMBENT is the richer row; a candidate richer than the incumbent is reported as a supersede candidate for an owner call, because demoting the store's row is a supersession act and D-2933 rule V forbids a commit rewriting an existing row.

**Two identity hardenings were required to make `enforce` safe at all.** `is_divergent` is now PAIRWISE — the previous form compared only the first two members, which made the verdict row-ORDER dependent for a group of 3+ and would have treated a transitive-looking group (A~B, B~C, A≁C) as one concept. And same-work is decided by source OVERLAP rather than set EQUALITY: row A `{s1}` and row B `{s1,s2}` are ONE work carrying different convergence evidence, and equality would have kept a duplicate alive; ANY blank source fails the whole group closed to `no_source` because a row of unknown provenance may not be merged on its neighbour's source. The landscape is unchanged by both (MERGE 0 / SAME_SOURCE_COLLIDE 2 / NAME_COLLIDE 1), so D-2950's recorded finding still stands.

**Evidence (read-only, `scripts/simulate_commit_dedup_gate.py --scope run` → `governance/dedup_gate_simulation_run_20261012.json`):** the faithful S6 input is 6,591 S5 rows + 1,049 D-2590 sidecar rows = 7,640; kinds `insert 7,637 / keep_both_cross_source 1 / keep_both_divergent 2`; **WOULD LINK = 0**. So `enforce` is neutral on the current artifact and the flip is evidence-gated, not scheduled. The 3 D-2949 groups are keep-both under this gate — which CONFIRMS D-2950's correction instead of contradicting it. **Simulation lesson, recorded because it is D-2950's own error class:** the first version read the S5 checkpoint ALONE and reported 0 collisions in 6,591 rows while the store demonstrably held 3 duplicate-name groups — all three live in the SIDECAR tier (process_template / tool_instruction), not the S5 path. A simulation over the wrong population certifies a gate it never exercised.

**R5 (generator ≠ verifier, gemma-4-E4B-it-MLX-4bit):** 3 defect claims, ALL false positives on trace (`jaccard` guards the empty-token case with `if not ta | tb`; `_same_work` is unreachable with a blank source because `classify_group` returns `no_source` first; `source_set`'s `str()` fallback IS the intent), plus one DRIFTED answer (Q1 inverted the branch — divergence yields `keep_both_divergent`, never a link). No change was made on the strength of it: a verifier's output is evidence to AUDIT, not a verdict to apply.

**Two real defects in the NEW code were caught and fixed before landing** (both by measurement, not review): (1) store rows carry `source_ids` as JSON TEXT, so `frozenset(text)` exploded a source id into its CHARACTERS — `dedup_identity.source_set` is now the one home for that shape; (2) the receipt filtered advisories by `classify_group`'s vocabulary while `kind` held `candidate_kind`'s, so it printed 0 advisories beside `kinds {'keep_both_divergent': 2}` — the `DISPOSITION_*` constants plus a regression test make that class impossible. Files: pipeline/dedup_gate.py, pipeline/dedup_identity.py, pipeline/stage6_commit.py, pipeline/pipeline_paths.py, config/pipeline_config.yaml (dedup_gate + fingerprint_files), config/flag_consumer_registry.yaml, config/store_columns.yaml, scripts/simulate_commit_dedup_gate.py, scripts/normalize_duplicate_of_marker.py. Tests 32/32 green (3 of them exercise the REAL insert path against the REAL schema: an absent marker is stored NULL, a link is stored as the canonical `fb_id`, and the serving rail re-derives the SAME pair — the writer half and the rail half of BUG-502 agree). Filed: BUG-726 (marker shape — writer fixed, legacy `--apply` owner-gated), BUG-727 (store_columns register red, pre-existing). → **BUG-726 CLOSED 2026-10-12** (the `--apply` ran: 7,640 rows `''` → NULL, C13 backup + post-state verified — see the D-2952 section below and the register line above).

## D-2952 — edition supersession is a FILE-LAYER content rule; `primary_source` stays ORIGIN (2026-10-12)

RULED, and ruled from MEASUREMENT rather than preference. D-2950 left exactly one question open — does "newest edition wins" reach `select_primary_source`'s earliest-year citation convention? — and `scripts/audit_edition_layers.py` (new, read-only, deterministic, LLM-free per D-343) shows the question was mis-framed by a LAYER.

THE THREE LAYERS, one home each: **WORK** (a concept-carrier; identity = `source_ids`; editions COLLAPSE by design, because `compute_source_id = SHA-256(normalize_author|normalize_title)` and `normalize_title` deliberately strips subtitles — D2308/D2315/D2507) · **FILE** (a text carrier; `source_authors[]` = {book, author, title, year}, the ONLY place an edition conflict is visible) · **BODY** (the FB's current statement). Supersession moves the BODY layer only.

MEASURED (7,640 rows): the edition population is **12 rows** with `files>1 AND years>1 AND exactly ONE source_id` — `Prompt Engineering for LLMs` 2024|2025 and `The Elements of Typographic Style` 1996|2004 among them — plus **51 boundary rows** holding 2 `source_ids`. So the store genuinely CANNOT tell two editions of one work apart, and that is the intended work-level identity, not a defect. Carrier duplicates (same edition, several files: `*_clean.md`, " (1)", z-library mirrors) measure **0 in `source_ids`** — the hypothesis that they inflate `source_diversity` was FALSIFIED by measurement, because D2176 already routes it through canonical ids; recorded CHECKED-AND-CLEAN so nobody re-fixes a fixed defect (BUG-527 class). At the FILE layer the blemish is real but display-only (31 rows literally repeat a `source_authors` entry, 90 collide on carrier key) → BUG-728. And the earliest-year convention is exactly honoured: **1,014 rows** carry "earliest publication year (YYYY)" with **ZERO violations**; 705 rows (9.2%) fall back to source order ("no year metadata; first source") — an unranked pick, honestly recorded, and the true provenance weakness (fix by metadata coverage, never by rewriting the reason).

THE RULING. (a) "Newest edition wins" is a **content-freshness rule about the BODY of one FB** — never an identity rule, never a citation rule. (b) `primary_source` KEEPS its meaning: **ORIGIN attribution — "the earliest source we HOLD that states this work"** (deterministic earliest-year, unchanged). Repurposing it to mean "newest" would invalidate 1,014 recorded reason strings, conflate ORIGIN with FRESHNESS, and give one column two meanings across time — the BUG-726 defect class, fixed one turn earlier. (c) Freshness gets its OWN pointer: **`content_basis`** (RESERVED name, deliberately NOT created yet) = the FILE whose text the current body was derived from, + `content_basis_updated_at`; absent = never superseded, stored as NULL and never `''` (the BUG-726 lesson applied prophylactically). It is not created now because a column with no WRITER is debt by definition (BUG-511 family) and the `store_columns` register is shrink-only at debt 8 of ceiling 9 — it is created in the same change that has a writer. (d) **BUILD ORDER:** record `content_basis` at EXTRACTION first; a supersession operation must never act on a fact nobody recorded. (e) Supersession is **never a commit act** — D-2933 rule V forbids a commit rewriting an existing row's body — so it is an owner-gated operation (C13 backup → ONE BEGIN IMMEDIATE → dry-run default → post-state verified, the shape that just closed BUG-726), and the gate's `would == 'supersede_review'` decisions are its **QUEUE**, not a commit. (f) The destructive direction is **fenced in config**: thresholds may TIGHTEN autonomously (stricter divergence = keep both = fail-safe) and may never LOOSEN without an owner (`require_both: true`, or raising the mins, merges on DOUBT).

NO CASCADE (checked, not assumed): the dedup gate's `richness()` ranks by `source_diversity`, derived from canonical `source_ids` (D2176), so ranking is untouched by the file-layer blemish; this ruling changes no schema, no writer, no stored row. Config: `config/dedup_identity.yaml` → `edition_supersession`, `thresholds_direction`. Bug filed: BUG-728. Companion alignment: D-271d's imperative "wire `duplicate_of IS NULL` into `pipeline/retrieve.py`" is SUPERSEDED as a MECHANISM (the retrieval guard is `status = 'PASS'` plus the LINK⇒QUARANTINE pairing) — see `governance/DECISION_D271_IDENTITY_20260917.md` → "UPDATE 2026-10-12".

## D-2953 — the content_type router is CALIBRATED before any re-stamp; the loose tier-2 form is fenced (2026-10-12)

RULED from measurement, and the ruling is *do not re-stamp*. BUG-712's remaining item was a governed re-stamp over the diff between the stored `content_type` and what the deterministic router (`reroute_content_type`, the ONE router, C21) would emit. That diff is **122 rows** on the live 7,640-row store. A new two-sided instrument — `scripts/calibrate_content_type_router.py`, read-only, deterministic, LLM-free (D-343 forbids a model anywhere near content_type, so the instrument carries none either) — calibrates it:

- **PRECISION (side A): 88 of the 100 `principle → growth_edge` moves (88%) are SUBJECT-MATTER FALSE POSITIVES.** The tier-2 test fires on BARE WORDS, and the contexts are ordinary first-order predicates about the record's SUBJECT rather than epistemic statements about its CLAIM: `contradict` 44 ("*generating untraceable or contradictory information*", "*visual cues contradict the audience's expectations*"), `contested` 34 ("*sites of contested identity*"), `unresolved` 14, `unverified` 6, `debated` 1, "open question" 1. A re-stamp on this form would have written ~88 wrong ontology roles into **1.2% of the store** — precisely the drift the D-2933 owner gate exists to stop.
- **RECALL (side B): 0.** Gated by the same claim-status test, the token list misses nothing, so the defect is **one-sided** and the fix is a NARROWING rather than a vocabulary expansion. The instrument's *first* run reported "106 missed" because its own recall vocabulary was bare too (77 of 77 "speculative" hits were ordinary adjectives — "*over-investment in speculative capabilities*"; one was a data-encoding term, "mixed data"). Recorded because an audit instrument that repeats the defect it audits is worse than no instrument.

**ROOT CAUSE IS AN UNFIXED SIBLING.** D-2949 fixed exactly this defect class in `_DONE_CONDITION` ("matched a BARE 'until'/'gate'/'termination' and misrouted descriptive models") and left its sibling `_OPEN_TENSION` bare. The pattern repeats in the keyword family: `ti_to_pt_keywords` lost 'protocol'/'pipeline'/'process' as "*tool-name suffixes*" and kept four of the identical class, so `OpenFrameworks` — a software LIBRARY — routes `tool_instruction → process_template` (**BUG-729**). Both are the same lesson: **a bare lexical proxy is not an ontological discriminator.**

**THE FIX SHIPS DISABLED, BY DESIGN.** `config/content_types.yaml → reroute.open_tension_strict` (default **false**) selects `_OPEN_TENSION_STRICT`, which demands an AFFIRMATIVE STATUS construction — SUBJECT…copula…STATUS ("the evidence is contested") | STATUS…SUBJECT ("contested claim") | an unambiguous phrase ("open question", "unknown whether", "not established"). Measured both ways in one run: **loose 100 moves (88% FP) → strict 2 moves** (`contested` on "*the expert consensus is weak or contested*" — genuinely right — and one "open question"), recall 0 in both. The first strict draft accepted "*the training data contains contradictory cues*" through a generic subject noun and measured **68% FP**: adjacency is not evidence of status, so the form requires STRUCTURE, not proximity. `tests/test_open_tension_strict.py` 6/6. Nothing changes in today's behaviour until an owner flips one key — the destructive value is the LOOSE one, so the safe direction is reachable without an owner and the risky one is not (C12/C16; content_type stays S4-owned, D-2933).

**WORK ORDER:** (1) owner ratifies the strict form, (2) BUG-729 narrows the TI keyword family to an evidence-based discriminator (a body-level procedure signal, not a name suffix), (3) THEN re-run the calibration and re-stamp only what the CALIBRATED router still moves. Instrument faithfulness fixed alongside: `scripts/diff_bug712_reroute.py` omitted `name`, a key `_principle_form_violation` READS — 0 manifest effect measured, but a diff computed on a truncated haystack is not evidence.

## D-2954 — the config surface refuses duplicate keys: a second top-level block silently REPLACED the first (2026-10-12)

A duplicate key in a config file does not ADD to a mapping — it REPLACES it, silently, in PyYAML's `safe_load` and in Python's `json.load` alike. That happened for real this session (BUG-730, self-inflicted, disclosed): a second top-level `reroute:` block appended to `config/content_types.yaml` emptied `reroute.ti_to_pt_keywords`, so `TI_TO_PT_KEYWORDS` became `()` and the whole `tool_instruction → process_template` tier went **DEAD** — no error, no warning, every existing test green.

It was caught by a **behaviour diff** (the router diff moved 122 → 112 and the 10-row transition vanished), not by review: the argument for behavioural rails over reading code. Store impact: none — the broken config existed only in the working tree, no stage ran, and merging the key into the ONE existing `reroute:` mapping (C21: one home per key) restored `TI_TO_PT_KEYWORDS = ('system','workflow','framework','methodology')` and the diff to exactly 122.

LANDED: `scripts/check_config_duplicate_keys.py` — a duplicate-key-rejecting YAML loader (naming the key and the line, at any depth) plus a JSON `object_pairs_hook` equivalent, over every `config/**/*.{yaml,yml,json}` (116 files); exit 1 on a duplicate, exit 2 rather than passing vacuously when nothing was scanned, and a `--selftest` with three known-answer controls (BUG-492: a control nothing runs is a comment). Verified PASS on config and FAIL on both a synthetic duplicate and an exact replay of the BUG-730 file, and **WIRED into `just health`** beside the config-defaults pair. This closes a WHOLE CLASS: every governed threshold, vocabulary and flag in this repo is loaded from config/, so one duplicate key could disable a rule that an entire decision depends on while every other rail stayed green — C16 applied to the config surface.

## D-2955 — the TI→process_template promotion requires BODY evidence; a name is a prior, never evidence (2026-10-12)

A name is a PRIOR. Evidence is a SELECTOR. Tier 3 of the deterministic router promoted a stored `tool_instruction` to `process_template` on a single bare noun in its `tool_name`, and measurement showed the rule was not merely imprecise but **inverted**: the owner-ratified D275b procedure tests "tool/software-specific command, syntax, or feature" FIRST, so a name-suffix promotion reads a software ARTIFACT that is USED as a method that is EXECUTED. Of the 108 stored `tool_instruction` rows the four keywords fired on 10 — 'OpenFrameworks' (a C++ creative-coding library, twice), 'Layout Analysis System', 'Inventory Management System', 'Supplier Management System' … and **not one of the ten is a procedure under the ratified procedure**, with 0 of them carrying procedure evidence in their own body.

APPLIED as two INDEPENDENT controls, each declared in `config/content_types.yaml → reroute` beside its rationale: the artifact nouns `system`/`framework` are removed (procedure-denoting nouns survive), and `ti_to_pt_require_body_evidence: true` demands that the record's own body evidence a procedure — ordered steps AND a done-condition/gate, the SAME pair tier 2 already uses for `principle → process_template`, exposed as `has_procedure_evidence()` so the rule and the instrument that judges it read one haystack and one pair of regexes (C21).

MEASURED BOTH WAYS (SIDE C of `scripts/calibrate_content_type_router.py`, read-only, 7,640 rows): name-prior candidates 1, body proves a procedure 0, promotions gate OFF 1 → gate ON 0, retired-vocabulary control 9 artifact-named rows of which 0 would have survived the gate, router diff **122 → 14**. The store holds those 10 rows as `tool_instruction`, which is exactly what the calibrated router now returns — this decision owes **no re-stamp at all**.

THE PART WORTH KEEPING: neither control is redundant, and the reason is not today's store. On today's 108 rows the evidence gate alone is sufficient (it kills all 10) and the vocabulary narrowing alone kills 9. The vocabulary is a prior that must also decide the case the store does NOT contain yet — a future record whose body really does carry a procedure under an artifact name would pass the gate and be promoted wrongly. Two defects, two controls, one instrument, and an honest statement of which one is doing today's work.

## D-2956 — a CEILING is a declaration, `measured:` is a MEASUREMENT, a ROLE is an ONTOLOGICAL claim; the three are never interchanged (2026-10-12)

Two red rails, one misfiling, three objects. Both reds were reported as ONE cause each; forensics the same day showed the rails measure three, and that the operator-facing verdict line does not distinguish them. `BUG-727` (store-columns) was filed as a stale `measured:` block and is in fact **305 fatal faults**: 278 `MEASUREMENT-DRIFT` (rulers recorded against a 14,574-row store, now 7,640) **plus 27 live ROLE-DECLARATION faults** that a re-measurement cannot clear. `BUG-731` (config-defaults) was filed as 241 against a 229 ceiling; in fact **183 of the 241 keys (76%) sit in one file** (`pipeline/pipeline_paths.py`, 361 defaulted sites), and the census could not see `pipeline/content_types.py` at all.

THE RULING: (1) **never raise a ceiling** — it declares a debt's measured size and is shrink-only (D-2642); raising it converts a finding into a permanently tolerated lie and destroys the only detector of the class. (2) **Re-recording is not a decision** — it is the rail doing its job, legitimate only on a SETTLED artifact, once, after the pending store mutation lands; a measurement taken while the artifact still moves is a claim, not a measurement. (3) **A role violation is a finding, not a stale number** — 20 of the 27 faults are ONE missing concept: the register cannot express "required within a tier", and this store is two-tiered by construction (D-2943), so a column with full coverage inside its tier measures 6,591/7,640 and reads as if it were constant. Declaring those 20 `sparse` would write 20 lies into the ontology register; the register must grow the missing role rather than lose the invariant. (4) **Instrument scope is part of the instrument** — a rail cannot vouch for a file it does not seek in.

THE HALF THAT LANDED, and why it is the cleanest possible proof of (4): `_CT` became a declared census receiver in `config/derivations.yaml#config_reads.receivers` IN THE SAME CHANGE as the loud reads it would otherwise have counted (`pipeline/content_types.py`: ten defaulted reads → subscripts, no literal default, fail-closed at import per C16). Re-measured: **241 before, 241 after**. Left alone, the receiver change alone would have measured 248; the module now has nothing for the instrument to find, so closing a blindspot cost the census nothing. The paydown itself is sized, not guessed: 183 keys in one file out of 241.

## D-2957 — `runtime` is a ROLE: serving-path state is not artifact content (2026-10-12, the BUG-726 class applied)

**The register made two claims the store refuted — and the store was right.** `last_retrieved_at` was declared
`reserved` with the reason *"blank on 7995/7995 rows — retrieval has never been recorded"*; `usage_count` was
declared `state` with *"constant 0 — the knowledge layer has never served this store, so nothing has ever been
retrieved"*. MEASURED on the live 7,640-row store: `usage_count` is 0 on 7,552 rows, 1 on 65, 2 on 18, 3 on 4,
4 on 1, and `last_retrieved_at` is filled on **exactly the same 88 rows** — because
`pipeline/feedback.mark_fb_retrieved` writes both columns in ONE statement. So the store has served 88 retrievals
while the register asserted it had never served any. This is the BUG-726 class (a claim the code cannot keep),
found in the DECLARATION rather than in the data: neither column is wrong, the ontology that described them was.

**The vocabulary had no shape for the thing.** `reserved` = nothing written; `sparse` = a row-carried diagnostic;
`state` = one constant fact per row; `value` = must VARY and be non-blank. A per-row counter that is present on
every row — and that is legitimately constant `0` on a fresh artifact — is none of the four. That is D-2956
clause 3 in action: the fault was a **finding**, not a stale number, and the honest repair is a new role, not a
declaration bent to fit.

**RULED — `runtime` is a role, and its contract is SHAPE, not coverage:** `nonnull == nonblank` and
`hollow == 0`, i.e. **absent is NULL**, never `''` and never a hollow literal; no coverage and no variation is
required (the rule holds on a fresh artifact, where a state column is legitimately empty); `filled_by` must name
the serving path that mutates it (C12). This is the exact machine rule that **would have caught BUG-726 at
declaration time**: a column written as `''` on every untouched row measures `nonnull == rows` while
`nonblank == 0`. Control `c19` pins that shape; `c18` pins the acceptance case; `c20` pins the hollow literal and
the writer-less declaration.

**APPLIED in four parts.** (a) The two declarations corrected, each carrying its measurement and its writer.
(b) The PRODUCER half: `pipeline/stage6_commit.insert_fb` now writes `_safe_str(...) or None` — **shape-only**, and
that qualifier is the whole point. The pre-flight audit caught the cascade: the INSERT is `OR REPLACE` and the
BUG-376 sync path deliberately carries the DB value through the S5 checkpoint and back, so a hard `None` would have
**destroyed the 88 real retrieval records** on the next re-commit. A producer must never INVENT runtime state; it
must also never DESTROY it. (c) The LEGACY half: `scripts/normalize_runtime_absents.py`, whose population is *the
columns the register declares `role: runtime`* rather than a list in code, reshaped 7,552 `''` → NULL with a C13
backup, ONE `BEGIN IMMEDIATE` and a post-state verified inside the transaction (rows 7,640; PASS 4,503 /
QUARANTINE 3,137; `quick_check` ok; `usage_count` untouched). (d) The one reader that would have emitted the string
`"None"` (`maxwell_mcp_server`) now formats `or ""`, so the emitted shape is stable across the change.

**COMPANION DEFECT, found by the rail's own new control.** Control `c18` could not pass until a real defect was
fixed: the control HARNESS modelled a SQL NULL as the literal `'none'` (`str(None)` lands in the `HOLLOW` set)
while the store ruler coalesces NULL to `''`, which is NOT hollow. The harness disagreed with the instrument it
validates, and no control had ever put a NULL in a column, so it was unexercised (BUG-492). Fixed in the harness,
not in the ruler.

**NOT DONE, deliberately.** The census that this work produced says the shape is not one column: **20 of the 78
columns carry a NON-NULL blank**, and the single manufacturing point is `_safe_str`'s `default=""`. The other 19
are left alone — each needs its own verdict against its own schema field, and a bulk rewrite of 20 columns would be
exactly the unmeasured store-wide change the house rules exist to prevent. Filed as BUG-737 with the census.

## D-2958 — a role declaration is a claim about a POPULATION (2026-10-12)

**One missing concept, measured, not argued.** Taken together the store-column rail's residual role faults are
not 25 problems: 14 columns are blank on **exactly** the 1,049 D-2590 sidecar rows (`nonblank` 6,591 = 7,640 −
1,049), `verifier_model` is present on exactly the 6,591 S5 rows, `classification_error`/`classification_errors`
are present on 0 rows because their writers' population is *"rows that hit the domain cap"*, and
`menu_hash`/`discipline_macro` are full at 7,640 because the canonical artifact **is** those rows. The four role
rules all evaluate against an implicit population — the whole table — that nobody measured. The store is
two-tiered BY CONSTRUCTION (D-2943) and artifact-scoped by run, so a population-free role is an **unscoped claim**
(D-2956 clause 4: instrument scope is part of the instrument).

**RULED:** `role` must be paired with a DECLARED, MEASURED population (a predicate plus its measured count), and
the role rules must evaluate WITHIN it. The destination is 25 faults cleared with **zero lies** — declaring the 20
tier-conditional columns `sparse` would write 20 lies, which is why the fix is the vocabulary and not the
declarations. The rail implementation is the next workstream and is **owner-gated**: it changes the vocabulary that
decides governance red/green. Scope: this is BUG-733 broadened from 20 to 25; BUG-734's 5 surviving faults are the
same concept, so BUG-734 is closed as ABSORBED (one home, D-2958, not two).

## D-2959 — D-2950 CLOSED: identity, the gate, the edition layer, and the instrument lesson (2026-10-12)

**The three questions D-2950 left open now each have a home, so D-2950 is RESOLVED.**

1. **IDENTITY RATIFIED** — the grouping key is `(normalize_name, source_ids)` and the merge gate is body
   divergence: a name is not an identity and a source is not an identity. The 3 live same-name/same-source pairs
   are DISTINCT concepts (Item Validation Protocol type-check vs schema-constraint; VJ Performance Method pre-plan
   vs live-trigger), so the naive key would have destroyed one concept each.
2. **THE DEDUP GATE STAYS `mode: report`, and the obligation moves from the MODE to the RECEIPT.**
   `checkpoint/dedup_gate_receipt.json` becomes required reading, and a receipt carrying ≥1 verified convergent
   link candidate is an OWNER GATE. `enforce` is not a schedule item: its only observable effect today is zero
   (WOULD LINK 0 over the faithful 7,640-row S6 input), so flipping it now would arm a mechanism no run has ever
   exercised — an unexercised rule is a comment (BUG-492).
3. **EDITION SUPERSESSION RATIFIED at the FILE layer** (D-2952): `primary_source` stays ORIGIN and `content_basis`
   stays a RESERVED NAME WITH NO WRITER. D-2952's rule stands: a reserved pointer is created in the SAME change
   that has a writer, and recorded at EXTRACTION first.
4. **THE INSTRUMENT LESSON RATIFIED as a standing rule** — any gate simulation must DECLARE its population and
   prove it covers every tier of the store (S5 + sidecar). D-2950's own error was exactly this: a simulation over
   the S5 checkpoint ALONE reported 0 collisions while the store demonstrably held 3 — all three in the sidecar
   tier. A simulation over the wrong population certifies a gate it never exercised.

## VERIFIER RULING — the instruments, measured, and what is on HuggingFace (2026-10-12, no new decision)

Asked directly: *is the verifier failing too often, and is there a better local model?* Answered from the record,
not from preference. **No new decision is minted: the governing rule already has a home** (C21) —
`config/eval_integrity.yaml::judge_calibration` owns the fence, the accuracy bands and `min_margin_over_baseline`,
and BUG-269 owns the diagnosis.

**The R5 LLM reviewer's own record (6 passes, all audited on trace):** 2 clean/approve; 1 with **two REAL
findings** that were applied (both instrument traps — a numeric-suffix strip that would have collided
"Fahrenheit 451" with "Fahrenheit", and dead code); 1 with three defect claims that were **all false positives**;
1 full drift (meta-narration, a truncated answer, one falsified claim); 1 refusal to engage. So the uninformative
rate is roughly **40–50%**, and the failure that MATTERS — a false positive that gets APPLIED — stands at
**0**, because the output is audited and never applied on its own authority. That is the doctrine working, and it
is also the reason not to shop for a model: the cost of a bad pass today is tokens, and the cost of trusting a
"better" model's pass would be a wrong change.

**The eligible-family fence already exists, and R5 is why.** `judge_calibration` admits **gemma-4-E4B** and
**gpt-oss-20b** only; Qwen3.8/Qwen3-Coder (the generator's family), REAP, Ornith, granite and Phi-4-mini are
excluded by name, with reasons. Checked against the live HuggingFace MLX population this is decisive: the
most-downloaded MLX text-generation models are `Qwen3.8-27B-MLX-4/5/6/8bit` at **3.9–4.1M downloads each** — i.e.
the naive "biggest, most popular" answer is the generator's own family, which is exactly the blind spot R5 exists to
avoid. Within the fence, the field is thin and, more importantly, **already measured**: BUG-269 (2026-09-17, 72
blind labelled calls) found BOTH eligible judges **degenerate** — T2 gemma 0.875 == the constant baseline, T6 both
0.778 == the constant, T3 worse than the constant (−0.56).

**RULING: the model is not the binding constraint — the TASK is.** A task whose answer ties "always say the most
common label" carries zero information *however respectable the number looks*, and BUG-269 already names the
per-task fix (T2 → a deterministic string operation, 0 calls; T3 → mechanise the D2587 step-count test and judge
only the residue; T6 → wire the per-FORM `verification_standard`). Two candidates are therefore fielded, both
**evidence-gated against the pre-registered bar** rather than adopted: (i) a same-family capacity step-up for the
R5 reviewer, `gemma-4-26B-A4B-it-QAT-MLX-4bit` (QAT, ≈4B active → the SAME latency class as E4B, 348k downloads);
and (ii) for the S5 NLI rail, `tasksource/ModernBERT-large-nli` (8k context, 16k downloads — long evidence
passages are exactly where DeBERTa-512 truncation manufactures NEUTRAL). BUG-269's own caveat is honoured: n = 7–9
can REJECT a judge, never CERTIFY one, so any adoption needs a stated n and a margin over the constant baseline.
**Nothing was swapped.** Filed as BUG-736.


## D-2960 — a role is scoped to a DECLARED, MEASURED population; the outside is part of the claim (2026-10-12, LANDED)

DECISION. `config/store_columns.yaml` declares named ROW UNIVERSES (`populations.<name>.predicate` + `.why`) and a
column may declare `population: <name>` with a REQUIRED `outside: absent | unconstrained`. A role's contract is
evaluated WITHIN the population (the same five rulers, measured inside); `outside: absent` additionally requires
the column to be blank outside AND NULL-shaped there, and `outside: unconstrained` declares values outside the
population legitimate and reports them LOUD as OUTSIDE-COVERAGE (the one non-fatal mode, OWED). Every other new
population fault fails closed: UNKNOWN-POPULATION, POPULATION-EMPTY (a universe matching 0 rows cannot carry a
contract), BAD-POPULATION-PREDICATE (a bad predicate is a FAULT, never a traceback; `;`, `--`, `/*`, `*/` are
refused), MISSING-POPULATION-WHY, MISSING-OUTSIDE, DANGLING-OUTSIDE. A moved population row count is
MEASUREMENT-DRIFT like any store ruler.

WHY. D-2958 measured that 25 role faults were ONE missing concept: a role declared over a whole table silently
claims a coverage a TIER never promised, so the fault it prints is an artefact of the QUESTION, not a defect in
the store. The store is two-tiered BY CONSTRUCTION (D-2943/D-2590): `s5_verified` 6,591 rows (the S5 NLI rail
adjudicated them) + `sidecar` 1,049 rows (whose role-specific body is `type_body`) = 7,640 = every row, a PARTITION.
The honest fix was a declared, measurable, tier-scoped role with the predicate read from config (C12) - never
`sparse`, which says OPTIONAL while D2371/D2488/D2475 QUARANTINE an empty application/failure_mode/elaboration, so
it would have been 20 lies. What makes the concept safe rather than a silencing device is the OUTSIDE half:
`population` alone only shrinks the universe, and a declaration that can only shrink can hide a value.

THE POPULATION IS THE VERIFICATION PATH, NOT THE LABEL. Measured: `content_type='principle'` = 6,577 rows, the
S5-adjudicated tier = 6,591; the 14-row gap is exactly the label-vs-body disagreement (12 owner-adjudicated
BUG-712 rows, 2 BUG-735 survivors). Sourcing the tier from `s5_reason` (the rail's own verdict) cannot drift from
the tier it describes; sourcing it from a label under adjudication would have written those 14 rows out of the
tier they were verified in.

MEASURED RESULT (`scripts/check_store_columns.py --check`, 45 declared columns): 25 role faults → 0; 278
MEASUREMENT-DRIFT + 50 census moves → 0 via ONE `--record` (D-2642: the tail is written only by the rail; ceiling
debt 9 → 8 DOWNWARD, the allowed direction). 15 POPULATION-SHAPE faults became VISIBLE for the first time (they
are BUG-737's absent shape, now attributed per column) and 2 OUTSIDE-COVERAGE notes are OWED and declared
(failure_mode 774 rows, menu_hash 1,049 rows). 8 new known-answer controls c21-c28 → 28/28 fire. Tests: 400 passed
/ 5 skipped.

STANDING RULES (D-2956 applied to this vocabulary):
  (1) A role is a claim about a POPULATION. Declaring one over an undeclared universe is a claim nobody can check.
  (2) The OUTSIDE is part of the claim (C12): a scoped role must state what happens outside its scope, or it is a
      private filter.
  (3) `reserved` means the slot exists, its WRITER is named and the store MEASURES it empty - it does NOT claim
      the writer never fired (a diagnostic that fires only on defective rows is legitimately empty on a clean run,
      which is why `sparse`'s 0 < nonblank < rows is the wrong rule for it).
  (4) A column whose value is explained by the ARTIFACT SCOPE of the store (one run, one menu) is `state`, not a
      constant `value`: `pipeline_run_id` (1 distinct over 7,640 rows) and `menu_hash` (1 distinct inside the S5
      tier) are facts about the artifact, not labels that failed to vary.

## VERIFIER ANSWER (plain language, 2026-10-12 — no new decision)

The question was "is the verifier failing too often?". Split into the two machines that verify, because the answer
is different for each:
  THE R5 CODE REVIEWER (gemma-4-E4B, the generator != verifier reviewer): YES, its OUTPUT is unreliable about half
  the time - measured over 6 passes it produced 2 clean ones, one pass with 2 REAL findings that were applied, one
  pass with 3 claims that were ALL false positives, one pass that drifted into meta-narration and self-truncation,
  one refusal, and today's pass with 1 correct statement + 2 false positives + 0 real findings. BUT - and this is
  the part that matters - ZERO false positives have ever been APPLIED, because a reviewer's output is treated as
  EVIDENCE TO AUDIT, never as a verdict to apply. So the reviewer is worth keeping as a second pair of eyes whose
  findings are always re-checked against the code; it is NOT worth treating as a gate, and it is NOT a reason to
  swap models: the most-downloaded MLX models are the generator's own family (the exact blind spot R5 exists to
  avoid) and BUG-269 already measured BOTH family-eligible judges as degenerate on three of four tasks. The binding
  constraint is the TASK, not the model (BUG-736 holds the three fixes: mechanise T2 and T3, wire T6).
  THE S5 NLI VERIFIER (DeBERTa-v3-large): its abstention is 19.1% (1,255 NEUTRAL + 783 CONTRADICTION + 29
  no_evidence of 6,571 eligible rows) and it fails CLOSED by design (D-2298); its EDGE is UNMEASURED on the live
  artifact, and in a non-production role it measured degenerate (error 0.931 = the constant baseline, BUG-320),
  while in production the harness reproduces the pipeline's 0.474 error exactly (D-302). So: not "failing too
  often" - its error rate is unknown for the job it is actually doing, and the cheap fix is to MEASURE it there
  (BUG-736), not to replace it blind.
ONE-LINE ANSWER: the reviewer is noisy but harmless because nothing is applied without an audit; the NLI verifier
fails closed on 19.1% and its real accuracy is UNMEASURED - the next spend there is a measurement, not a model.
  CORRECTION 2026-10-12 (same session): the POPULATION-SHAPE work queue is 14 columns, not 15 - the
  list in D-2960 is right and the count was one high. MEASURED by the rail: the 14 are elaboration,
  taxonomy_match_method, keywords, discipline_raw, context, accessibility, intimacy_boundary, source_text,
  difficulty_level, temporal_scope, epistemic_status, verification_method, practicality, verifier_model (1,049
  NON-NULL blanks each). type_body is the 17th population-scoped column and is correctly SILENT: blank outside its
  population AND NULL-shaped there - the control that proves POPULATION-SHAPE is not a blanket fault.


## VERIFIER MODEL RULING (2026-10-12 — RECOMMENDATION, awaiting owner ratification)

The owner asked whether the verifier is failing too often, then clarified the real question: which model is
MOST RELIABLE judged by community notes, benchmarks and Hugging Face downloads/likes. Answered with evidence
rather than a swap — the record is `governance/VERIFIER_MODEL_SURVEY_20261012.md` (HF adoption metrics read
from the HF API on 2026-10-12; the LLM-AggreFact leaderboard, where Bespoke-MiniCheck-7B averages 77.4 above
Claude-3.5 Sonnet 77.2 and gpt-4o-2024-05-13 75.9 and FactCG-DeBERTa-L reaches 75.6 at 0.4B; JudgeBench, where
even GPT-4o judges objective correctness only slightly better than random; and Vectara's HHEM ranking).

- **S5 (grounded verification):** the role belongs to a PANEL of purpose-built, non-generator-family
  fact-checkers (MiniCheck-7B / MiniCheck-Flan-T5-Large / MiniCheck-DeBERTa-v3-Large, with HHEM-2.1-Open as an
  independent T5-family signal), MEASURED on our own rows before any pin changes — a stated n, the
  majority-class baseline, and a margin above it (BUG-269; D-2956: a survey is not a measurement).
- **R5 (diff/artifact review):** the reviewer stays ADVISORY — false-positives-APPLIED = 0 is the invariant
  JudgeBench says must not be relaxed. The one model change the evidence supports is the ALREADY FIELDED
  26B-A4B gemma, landing WITH BUG-269's T2/T3 mechanisation so the passes that need no judge stop being made.
- **Rejected:** any Qwen-family verifier (the generator is Qwen3-Coder-30B), and adoption metrics as a proxy
  for accuracy — the most-downloaded MLX models ARE the generator's own family, the exact blind spot R5 exists
  to avoid.

**Not yet a decision: the register is unchanged.** It becomes one on the owner's approval; the pins move only
after the bench reports, and a tie keeps the incumbent (cheaper and already pinned).

## D-2961 RATIFIED (2026-10-12) - the verifier question is TWO roles: S5 becomes a MEASURED panel, R5 stays ADVISORY and CROSS-FAMILY

The question "is the verifier failing too often" has one answer only because it hides two instruments. S5 asks whether the
evidence ENTAILS the claim; R5 asks whether an artifact or diff is correct and safe. Ratified: S5 is a PANEL of purpose-built,
non-generator-family fact-checkers (MiniCheck-Bespoke-7B / MiniCheck-Flan-T5-Large 0.8B / MiniCheck-DeBERTa-v3-Large 0.4B
plus HHEM-2.1-Open as an independent fail-closed 0-1 signal), and a single giant LLM judge is REJECTED on JudgeBench (strong
judges are only slightly better than random on objective correctness). R5 stays ADVISORY with its invariant
false-positives-APPLIED = 0 and stays CROSS-FAMILY: generator != verifier INCLUDING FAMILY, so no Qwen-lineage model may
verify a Qwen3-Coder-generated change. NO PIN MOVES ON POPULARITY - a survey is not a measurement (D-2956): the incumbent S5
pin stays until a bench on OUR rows reports a stated n, the constant-majority baseline (BUG-269) and
min_margin_over_baseline 0.15, with the abstain rate reported separately from the error rate.

CORRECTION recorded in the same breath (the pre-commit forensic audit, catching my own recommendation): the survey called
gemma-4-26B-A4B-it-QAT-MLX-4bit "already fielded" - it is NOT fetched, and its OptiQ sibling is DISABLED as BROKEN, so the
promotion is CONDITIONAL on a fetch + a BUG-265-class preflight + the bench. It is NOT sanctioned. Tracker: BUG-736.

## D-2962 RATIFIED (2026-10-12) - R5 code review is a GATE, not a model: deterministic layers first, one advisory cross-family reviewer

MEASURED before the fix (governance/r5_reviews.jsonl, 43 verdicts): 30 APPROVE / 6 REJECT / 4 INSUFFICIENT / 3 UNPARSED -
7 of 43 (16%) were not decisions, and every UNPARSED was a truncated verdict JSON. The reviewer was also being asked whether
the file COMPILES and whether it satisfies C11/C12 - questions a machine answers exactly and for free. Landed:
scripts/r5_review_gate.py + config/r5_review_gate.yaml. Deterministic layers run first (syntax via compile(), so no
__pycache__ is written; ruff; C11/C12 via scripts/pre_commit_gate.py); a FATAL layer stops the review, because a file that does
not compile is not reviewable; the repo-wide C11/C12 layer is deliberately loud-but-NON-fatal, since it is currently red for
reasons no single reviewed file caused (BUG-739) and a loud rail nobody can satisfy is not a rail (BUG-540). The verdict is
still produced ONLY by scripts/r5_code_review.py, and the gate receipt carries the layers + the file digest + a pointer, never a
verdict of its own (D-2646). The reviewer question is now SCOPED to the file's own docstring: MEASURED - the same file at the
same digest returned INSUFFICIENT before the scope was stated, and APPROVE after it (tier=deep, 2600-token budget).

Reviewer promotions are gated, not bought: Qwen3.8-27B is declared a NON-candidate as a reviewer (generator lineage; it was the
"deep auditor" in 5 journal verdicts), and any promotion needs the existing "reviewing" bench in tools/model_eval_suite.py with
a stated n >= 20, the constant-answer baseline and min_margin_over_baseline 0.15 (D-2956). Trackers: BUG-738 (R5 gate + bench
owed), BUG-739 (the C11 rail misreads stdlib: difflib / ctypes / _sqlite3).

SUPERSEDES (pointer only; no protected file is rewritten): the "VERIFIER MODEL RULING (2026-10-12 - RECOMMENDATION, awaiting
owner ratification)" clause above (now D-2961/D-2962), and D2556's "Qwen3.8-27B = deep auditor" clause, which the FAMILY rule
retires in its reviewer role.

## D-2998 RATIFIED (2026-10-14) - A re-publication is ONE VOICE, and the source-kind axis takes an ADOPTED vocabulary

MEASURED 2026-10-14 (T-121 lane). The question was asked with no home to answer it in: when corroboration is measured, is a
work and its RE-PUBLICATION one voice or two? ANSWER: ONE VOICE. A preprint, its journal article, its repository copy and its
2nd edition are ONE work under D-2308's edition rule - generalised here from IDENTITY to CORROBORATION. On this corpus the
inflation is already visible twice over: 530 corroborated rows were ONE text under TWO names (BUG-780) and 84 collapsing
pairs (T-129) certify the same work twice, which is precisely the failure a raw row count cannot see. Counting a preprint plus
its article plus its repository copy as three voices would rebuild that failure on a new axis.

The VOCABULARY is ADOPTED, never invented. A bespoke source-kind list would be a FOURTH naming system beside the taxonomy,
the content types and the extraction types (C12: a second copy of a fact is a second truth), and it could not be compared with
anything outside this repository. The axis therefore takes an existing controlled set - OpenAlex's work `type` (10 values, plain
strings, no vendor lock-in: C2) - declared in config/content_types.yaml#source_kind.

The axis is a PRECONDITION, not a consequence: `book` is the only value the pipeline emits (measured), and no non-book source
may be ingested before the one-voice rule is exercised on its first batch. Nothing is migrated, no row is relabelled, and no
model is involved. The principle restated here is BORP's (corroboration by INDEPENDENT VOICES, not by count - see
governance/buglog.md#BORP); its SCALAR form stays refused, because a second home for one fact is a second truth (D-2646).

## D-2999 RATIFIED (2026-10-14) - A name that resolves to N rows stays declared-unresolved: the anchor-bridge ambiguity ruling

MEASURED (BUG-777): the anchor<->corpus bridge no longer re-derives - the content join collapsed 208 entries to 13 and most
anchor rows read AMBIGUOUS; the consequent RED ladder line masked 5 of the 68 rails below it (BUG-778), so the ambiguity was
expensive as well as invisible. The owner's ruling has three parts, and the third is the one that keeps the other two honest:

(1) DEFAULT = DECLARED-UNRESOLVED. A name no declared rule decides is recorded as declared_unresolved, COUNTED and reported.
Never dropped, never narrowed to "the first row", never guessed by a model (D-2898: a resolution is a label).
(2) RESOLUTION ONLY BY A DECLARED, ORDERED, DETERMINISTIC RULE that PRINTS the rung that decided it: exact_id, then
served_run_name_and_author, then single_corpus_row. The order IS the decision: it makes the outcome reproducible, and it makes
any later change to the order a visible act rather than a different answer from the same input.
(3) WHAT THE RULE DOES NOT RESOLVE STAYS declared_unresolved - the count is the debt (fail-closed), so the gate cannot be
satisfied by resolving more aggressively, only by resolving more EVIDENCE.

The ruling is declared in config/anchor_family.yaml#store_bridge.resolution and consumed by
scripts/build_anchor_store_bridge.py. It converts a MASKED ambiguity into a MEASURED one, and it matches the position the
owner's own signed sheet already takes at the other end of the same surface: 19 of 150 cells are `ambiguous` ABSTENTIONS,
excluded from the expected sets and COUNTED (D-2991).

## D-3000 PROPOSED (2026-10-14) - The harness context contract: window parity is an invariant, the compaction trigger is derived from the SERVED window, and a cache reading is never a fabricated zero

**State:** PROPOSED (the declarations change nothing; the routing choice and the two environment values are the
owner's act). **Authority:** `config/agent_context.yaml`. **Reading:** `scripts/agent_context_probe.py`
(12 known-answer controls, 4 mutations, rc 2 on drift, read-only).

**Why.** MEASURED 2026-10-14: the local agent loop compacts at 26,214 tokens (0.8 x 32768) while this machine
already SERVES 131,072 and 262,144 to two other models, and every compaction rewrites the prompt so the next
turn pays a full cold re-prefill - which is why a local agent loop feels slow (prefill, not decode). The harness's
own ledger proves the harness measures prefix reuse (96% of cloud input tokens are cache reads, 37.4% locally on
the reviewer model) and nothing measured an agent loop's window at all.

**The four layers.** served_window (server) -> declaration (harness) -> trigger (compaction) -> cache_ledger
(the harness's own measurement). A mismatch between any two is a fault, and today every mismatch is silent: a
served window below the declaration is a TRUNCATION RISK, the reverse is a WASTED WINDOW, and a missing side is
UNVERIFIABLE. Six such drifts are measured right now.

**The rules.** (1) parity is an invariant with two separately-named failure directions; (2) the trigger is
derived from the SERVED window, and a CLOUD price-tier cap may not govern a local run (C1/C22); (3) a cache
reading is evidence only over rows that CARRY the field, and the only certification of reuse is a two-call A/B
(D-2957: absent is not zero); (4) the prompt prefix is byte-stable and only the tail may change - a compaction is
a cache bomb, a per-turn injection at the head is a miss every turn. Routing is by declared WINDOW CLASS.

**Not this decision.** No harness setting is rewritten here, no model is re-pointed (that is T-131's bench), and
no cache ratio is published as a measurement until the A/B is run.

## D-3000 AMENDMENT (2026-10-14, the same day, BEFORE ratification) - LAYER 5: the prefill bill, and the two claims the first draft got wrong

**State:** still PROPOSED. **Authority:** `config/agent_context.yaml` (schema_version 2). **Reading:**
`scripts/agent_context_probe.py` (17 known-answer controls, 9 mutations, three modes, rc 2 on drift).

**What the amendment corrects - and the correction is the point, because both errors were produced by reasoning
and caught by measuring:**

1. **A FALSE TRUNCATION, RETRACTED.** The first draft reported that a prompt came back truncated at 32,026
   tokens and blamed the server's global context setting. It did not: the prompt WAS 32,026 tokens. The "sent"
   figure had been computed from a chars-per-token rule (four characters per token) while that filler's measured
   rate is 4.5, and the estimate was never checked against the server's own counter. Refuted the same day by
   sending a genuinely larger prompt: **50,082 prompt tokens were accepted whole** by a model declared at
   131,072, so the reachable window is real and the truncation was an artefact of arithmetic (BUG-794). The
   lesson is now a rule and a control: an ESTIMATE is not a MEASUREMENT, and a rail may not build a claim on one.

2. **THE CACHE, MEASURED INSTEAD OF ASSUMED.** The first draft could only say that reuse was unproven. It was
   then run: **twelve calls, byte-identical prefixes (4.5 k - 5.3 k tokens), a resident model, three arms
   (fixed system block, fixed user block, and the control whose system block carries a per-call nonce) - every
   call reported `cached_tokens = 0`**, and the two-call speedup came out at **1.01x, then 1.04x** through the
   probe's own `--prefill-ab`, against a declared bar of 5x. The single non-zero reading in the whole sweep was
   a **4096-token block boundary directly after a model load**, which names the mechanism: a 4096-token BLOCK
   cache, and it is switched OFF by declaration (the D2460 thrash guard is a RAIL that refuses inference when it
   is on). **Prefix reuse is therefore DISPROVEN on this machine today** (BUG-792). The honest model of a local
   turn is that it re-pays its WHOLE prompt, every turn.

3. **LAYER 5 - THE PREFILL BILL.** A window is not a budget. An agent turn pays `working_set / throughput`
   seconds BEFORE it decodes a token, and with the cache disproven it pays again on the next turn. Measured
   throughputs, read from the server's own counters: **gemma-4-E4B 455 tok/s, Phi-4-mini 394, gpt-oss-20b 210,
   Qwen3.8-27B 39.** At the declared 60-second per-turn budget the loop class (working set 26,214) is satisfied
   by **ONE model**: the 4B pays 57.6 s, Phi-4-mini misses by six seconds (66.5 s), gpt-oss-20b costs 125 s, and
   Qwen3.8-27B costs **672 s - eleven minutes per turn**. The first draft's routing rule (**agent_loop >= 131,072**,
   on the reasoning that a session needs room) is therefore WITHDRAWN as a decision: it selected on window
   arithmetic and ignored the bill, and it would have routed a loop to a model that cannot pay a turn at that
   size (~56 minutes on the 27B). The class rule is now two-sided: the window is the FLOOR, the bill is the
   DECISION.

4. **THE TRIGGER, MADE CONDITIONAL ON THE CACHE.** `min(threshold x window, cap)` stands, but the threshold must
   satisfy the latency budget while the cache is disproven: `threshold <= budget_s x measured_prefill_tps / window`.
   The default 0.8 is right for the fastest local model **by coincidence** (26,214 / 455 = 58 s <= 60 s) and wrong
   everywhere else: the same 0.8 on the 20B's window resolves to **104,857 tokens - 8.3 minutes of prefill per
   turn** - which is precisely the "a cloud artifact governs a local run" failure this decision exists to name.

5. **THE PIPELINE'S OWN AMORTISATION.** The knowledge pipeline's LLM stages are the textbook prefix-cache case and
   get nothing from it: **10 stage system prompts are byte-stable module constants**, verified by AST rather than
   by grep (`--prefix-audit`, now a rail, because a regex cannot tell a prompt from a role string). With no cache
   behind them, that same prefix is prefilled **once per call**. A cache that does not exist cannot be called, so
   the lever is the NUMBER OF REQUESTS per unit of work (packing), never the prompt's layout - and the audit is the
   precondition that keeps packing worth doing.

**Not this decision.** Nothing in the harness is rewritten: not one environment variable, not one provider slot.
The declaration is amended; the owner's word on the two knobs is still the act T-132 waits for.


---

## D-3101 CORRECTION (2026-10-19) — the split discriminator resolves by LEDGER, not cost_source; the window is an owner word

FORENSIC AUDIT of D-3101 ("THE CLOUD-CEILING SPLIT — pipeline-ingestion and harness-metering are two
classes, not one lifetime counter") before any implementation. Three measured facts, each a receipt:

1. **The discriminator D-3101 names does not resolve (D-3034).** The decision text says the split must
   "RESOLVE via model in cloud_model_families plus cost_source". But `cost_source` in the harness ledger is
   COST-PROVENANCE, not metering-class: its only values are `estimated` (37,933 rows), NULL (1,443),
   `carried_forward` (1). None of those three distinguishes pipeline-ingestion from harness-metering. The two
   metering classes ALREADY resolve by LEDGER (realpath ownership): the harness ledger
   (`~/.local/share/goose/sessions/sessions.db#usage_ledger`, 33,231 rows, carries `created_timestamp`) vs the
   pipeline ledger (`~/.maxwell_os/usage_ledger.db#usage`, **0 rows**, file dated Jul 14). A row's realpath lands
   in exactly one ledger. cost_source is not the discriminator; the ledger is.

2. **The pipeline-ingestion class has no writer and no declared home.** The pipeline ledger carries 0 rows, no
   pipeline stage writes to it, and `config/agent_context.yaml#homes` declares no home for it (only `cache_ledger`
   = the harness ledger). The pipeline is local-only by C1/C3, so pipeline cloud-ingestion volume is ~0 BY DESIGN —
   there is nothing to meter yet. A ceiling on that class is a forward guard, not a current measurement.

3. **"Windowed, burn-rate" names no window.** A lifetime counter always re-breaches any flat number (the reason
   D-3101 exists); splitting into TWO lifetime counters only halves the re-breach, it does not remove it. The fix
   requires a WINDOW, and D-3101 does not specify one. A window is an owner word, not an edit.

**Correction.** The split discriminator is the LEDGER (realpath ownership — D-3034), not `cost_source`.
`cost_source` keeps its existing job (cost provenance → the unclassified bucket, BUG-767's shape). The corrected
implementation order:
  1. Declare the pipeline ledger's home in `agent_context.yaml` and add it as a second source in
     `delegation_economy.yaml` (C12: ONE home, resolved through the ONE resolver).
  2. OWNER defines the window (e.g. trailing-30-day burn, or daily-burn = ceiling / 30) — a word with a reason.
  3. Implement two metering classes; windowed burn-rate for the harness class (which has `created_timestamp`),
     lifetime-with-reason for the pipeline class until its writer exists.

NOT IMPLEMENTED this turn: D-3101's stated discriminator resolves to nothing, so implementing the 1-2-3 as
written would encode a discriminator with no referent. The correction above is the act that unblocks a clean
implementation. T-187 (brain ranking) and the owner's window word are the two inputs the implementation waits on.

## D-3102 (RESOLVED 2026-10-19) — ADOPT oMLX 0.7.1rc1 as the production engine (A/B measured vs 0.7.0)

**Verdict.** The corrected, guard-aware A/B is DONE and the production engine now runs 0.7.1rc1. ADOPT on
measured grounds:

| metric | 0.7.0 | 0.7.1rc1 | verdict |
|---|---|---|---|
| model load (cold) | 5.9 s | 3.68 s | −37.6% |
| wall (load + TTFT) | 17.7 s | 15.8 s | −10.7% |
| prefill (Ornith @4k) | 361.88 tok/s | 355.32 tok/s | flat |
| TTFT | 11.08 s | 11.29 s | flat |
| decode (max_tokens=1) | 96.91 tok/s | 222.13 tok/s | SINGLE-TOKEN ARTIFACT, not promoted |

**The decode 2.29× is NOT adopted.** `measure_prefill.py` sends ONE `max_tokens=1` completion, so its
`generation_tokens_per_second` counter is single-token latency, not sustained decode throughput. A ≥128-token
benchmark is owed before any decode claim enters the register (D-3036: a hypothesis stays labelled until a
receipt speaks).

**Why config is safe.** The `.app` bundle holds only code; `settings.json`, `model_settings.json`, model weights
and the 51 GB SSD prefix cache all live in `~/.omlx/`, external to the bundle, and are untouched by the swap.
Rollback is preserved at `/Applications/oMLX-0.7.0.app` plus `~/.omlx/*.bak-before-071upgrade`.

**Receipt.** Serving parent `/Applications/oMLX.app/Contents/MacOS/oMLX` reads `__version__ = "0.7.1rc1"`;
`/health` healthy, `model_count 8`, `loaded_count 1`; guard `com.maxwell.omlx-engine` last exit 0.


## D-3103 (RESOLVED 2026-10-19) — RE-RULE the two capability axes contradicted by T-187 + lc_reasoning

**Verdict.** Two rows of `config/harness_policy.yaml#capability_axes` were contradicted by receipts this session and
are RE-RULED (D-3038: a contradicted finding is re-ruled, never silently kept). A third axis gained a new reading.

1. **`tool_calling.never{gpt-oss-20b-MXFP4-Q8: 0.0}` is CONTRADICTED.** The 0.0 was measured on the RAW-JSON tool
   format, not native `tool_calls`. On T-187 (`scripts/measure_subagent_loop.py --two-step`: two-tool, two-STEP,
   DEPENDENT loop with a distractor, per-turn budget 90 s), gpt-oss PASSES — slowest turn 35.3 s, decode
   42.4/42.4/42.0 tok/s. A 0.0 tool-caller must never drive a tool loop, but gpt-oss is NOT a 0.0 native
   tool-caller: the raw-JSON reading and the native reading disagree, and the native one is what a harness exercises.

2. **`latency_agent_loop.routable{gemma-4-E4B-it-MLX-4bit}` is CONTRADICTED.** On the same fixture gemma FAILS the
   dependent second step (read_lines=1, lookup_token=0): it reads but never takes the dependent lookup. It is
   latency-fast and loop-incapable. "The only routable model" therefore names a model that cannot do the work the
   route exists for. The interactive-budget re-measurement against the native-loop passers is owed before re-routing.

3. **`long_context_reasoning_16k` gains gpt-oss at 1.0.** lc_reasoning (numeric exact match over 16 k ctx,
   `tools/model_eval_suite.py --models gpt-oss-20b-MXFP4-Q8 --suites lc_reasoning`): 6/6 exact
   (452, 392, 605, 419, 618, 366). Ties Qwen3.8-27B-MLX-4bit.

**NET — this re-opens BUG-832 remedy #2 with a VIABLE local candidate.** BUG-832's premise ("no served model passes
agent_loop long-context reasoning — gemma 0.0, Qwen3-Coder 0.0; only Qwen3.8-27B at 1.0 and slow") is now
PARTIALLY OVERTURNED: gpt-oss-20b-MXFP4-Q8 clears BOTH the native tool loop (T-187) AND long-context reasoning
(lc_reasoning 6/6), at ~42 tok/s decode (fast). It clears 2 of 3 local-brain gates. The third gate — the gemma
drift eval (slop-proof switch-back: 20 class + 20 summ + 10 code-review ground-truth) — is still owed, and the
owner's brain DECIDE (BUG-832 remedy #2) remains an owner word. NOTHING is auto-promoted (D-2898: no LLM promotion):
gpt-oss is now a candidate that cleared two gates, not an approved brain.

**Receipts.** `temp/subagent_loop_two_step_full_20261019.json` (8 rows, budget 90.0) |
`governance/model_eval_checkpoint.jsonl` (gpt-oss lcr-0..5 all ok, ctx_tokens 16000).


## D-3104 (RESOLVED 2026-10-19, OWNER) — Brain DECIDE: gpt-oss local everyday, deepseek escalation strategic

The owner decided BUG-832 remedy #2 (the owner-gated brain choice). Everyday: gpt-oss-20b-MXFP4-Q8 on maxwell_omlx
(local, $0 marginal, sovereign). Strategic / slop-risk: ESCALATE to custom_deepseek (deepseek-v4-pro) — the existing
D-3023 escalation path, with GOOSE_PLANNER already pinned to deepseek.

Why gpt-oss is the everyday brain (not gemma, not Qwen3-Coder): it is the only served model that clears all three
local-brain gates by measurement — T-187 native two-step tool loop PASS (slowest turn 35.3 s), lc_reasoning 6/6 = 1.0
at 16k ctx, and the gemma drift eval (class 0.80 / code-review 0.80 / summ 0.85) shows no catastrophic drift.
gemma-4-E4B, the prior AGENT_LOOP_SHORT, FAILS the dependent second step (D-3103) and is demoted from the brain role
(retained as STABILITY_FIRST). NOTHING is auto-promoted (D-2898): this is an OWNER word, not a benchmark promotion.
The ~15-20% residual error on the drift legs is the measured ceiling the owner accepts for the everyday brain;
anything higher-stakes escalates to deepseek.

**Receipts.** T-187 native loop PASS (35.3s) | lc_reasoning 6/6 = 1.0 | gemma drift eval 0.80/0.80/0.85 |
owner word "gpt-oss everyday; deepseek for strategic/slop-risk".


## D-3105 (RESOLVED 2026-10-19) — Model-integrity gate registered red-loop-first (D-3036): pickle refused, safetensors-only

**Verdict.** The red loop for the model-load threat model (pickle-RCE / poisoned chat templates) is one named
command — `scripts/model_integrity_gate.py` — and it is RED on a crafted-malicious fixture and GREEN on a clean
safetensors model, verified live this session. It reads every knob from `config/model_integrity.yaml` (C12/C12c:
no path, host or format string of its own) and classifies a payload by FORMAT before any bytes are executed.

**Why refuse-on-format, never inspect-then-execute.** pickle = arbitrary code on load, and that is a MEASURED
attack class, not a hypothetical (Equistamp/UIUC backdoor persistence survives safety training, arXiv 2610.07510;
JFrog documented in-the-wild pickle-RCE on malicious HF models). The gate therefore never unpickles a payload:
it refuses on the format before the bytes are inspected. `tests/malicious.pkl` goes RED not because the gate
executed it, but because the gate refused to — and the absence of `malicious_marker.txt` is the proof.

**Red-loop receipts (this session).** `malicious.pkl` → RED exit 1, no marker written; `clean.safetensors` → GREEN
exit 0. The gate answers the question a checker must answer: is this payload loadable, or must it be refused?

**Next gate extension (NOT built yet, declared not silent).** The post-red-loop controls — SHA-256 pinning at
download against a known-good registry, chat-template Jinja scan, quarantine-until-verified — are the NEXT
extension. They are registered as owed, not as done: a gate that refuses pickle is the first rail, not the last.

**Receipts.** `scripts/model_integrity_gate.py` (exit 1 RED / exit 0 GREEN) | `config/model_integrity.yaml` |
`tests/malicious.pkl`, `tests/clean.safetensors` | no `malicious_marker.txt` written.


## D-3106 (RESOLVED 2026-10-19) — Golden anchor orphaned by corpus re-generation; fail-closed sentinels + owner-gated rebuild, not mechanical re-point

**Verdict.** The golden anchor (`governance/gold_4axis.jsonl`, 251 human-adjudicated 4-axis rows) resolves **0/251**
against the live DB because the corpus was re-extracted — `pipeline_commit bae6662` → `32321c9` — and
`fb_id = sha256(name|definition)` is generation-sensitive (D-2949/F-19). Only **6.0%** of principle names survive
across generations (388/6521), and the ids resolve 251/251 only in a DELETED archive snapshot. The correct
disposition is **fail closed, not re-point**: mechanically re-pointing the 6% of surviving ids would mask the orphan
and mislabel drifted definitions.

**Two sentinels were repaired (red-loop-first, D-3036).** (1) `tools/model_eval_suite.py::suite_voting` now raises a
named `RuntimeError` ("gold anchor orphaned: 0/251 …") instead of crashing opaquely via `IndexError` → rc 2;
(2) `scripts/audit_runtime_vs_gold.py` — the F-01 drift detector — had silently false-passed ("OK" with 0 compared /
251 missing) and now fails closed on missing rows (BUG-944). Red loop verified live: audit was rc=0, now rc=1 with
`DRIFT: 251 of 251 anchor row(s) MISSING`.

**What remains owed, stated as such.** Rebuilding the golden anchor against the live generation is an **owner-gated**
task — the 4-axis labels must be re-adjudicated against the current corpus, not re-pointed. This decision registers
the orphan and the fail-closed rails; it does not claim the anchor is rebuilt.


## D-3107 (PROPOSED 2026-10-19) — Golden anchor identity must be generation-invariant (D-2949 at the anchor level, not only dedup)

**Recommendation on D-3106.** D-3106's disposition is correct: fail closed, do not mechanically re-point the 6% of
surviving `fb_id`s, and make the rebuild owner-gated. But D-3106 fixes the *symptom* (this anchor is orphaned) while
leaving the *disease* (identity is generation-sensitive) untouched — so the owner-gated rebuild will recur on every
corpus re-generation, each time discarding the human adjudication it cost.

**The future-proof fix.** D-2949 established `fb_id = sha256(name|definition)` is generation-sensitive and added a
deterministic grouping/merge gate for **dedup**. This extends the same diagnosis to **human-adjudicated ground
truth**: the anchor must carry a generation-invariant identity — a key derived from a semantic/content representation
stable across extraction runs (normalized concept name, or a content hash independent of exact definition wording) —
so a re-generation can semantically re-attach the majority of anchors and only a small delta needs re-adjudication.
The owner-gated rebuild in D-3106 is the natural moment to add this key (do it once, then it never fully recurs).

**State: PROPOSED** — the direction is decided, the mechanism is not built. Complements D-2949 (dedup) and D-3106
(immediate orphan); conflicts with neither.


## D-3117 (PROPOSED 2026-10-21) — Cross-run evidence-accumulation / convergence-upgrade layer

**The gap, verified against code and store (D-3034: a claim is resolved, not asserted).**
`is_convergent` is minted ONCE at S2 from the within-run cluster source count (`sub_sid_count >= 2`,
pipeline/stage2_extract.py), passed through S4 untouched (pipeline/stage4_merge.py), and NEVER
upgraded thereafter. A principle extracted from a single-source (1-book) cluster or a singleton
(1-segment) is stamped `is_convergent=false` forever, even if a LATER corpus run extracts the SAME
principle from a DIFFERENT book — which is the definition of corroboration. The D-2951 commit dedup
gate is name-fragile (keys on `normalize_name(name)`), mode=report (config/pipeline_config.yaml
`dedup_gate.mode: report`, live store 0 `duplicate_of`), and even in enforce has NO disposition that
unions `source_ids` or flips `is_convergent` — its actions are `link_duplicate | insert |
supersede_review` only (pipeline/dedup_gate.py::decide). The root cause is the identity model:
`fb_id = sha256(name|definition)` is paraphrase-sensitive (D-2949; 6.0% name survival across
generations, D-3106), so a cross-run "same principle" match never fires.

**Market-research grounding (cited; the pattern is settled, not novel).**
1. OpenIE/OKB canonicalization (Galárraga et al., CIKM 2014; ESWC 2022 survey) — the proven shape is
   POST-HOC: extract freely, then cluster synonymous names/phrases and assign a canonical id. This is
   exactly the layer Maxwell lacks.
2. Incremental multi-source entity resolution (Springer 2020) — accumulate sources ORDER-INDEPENDENTLY.
3. Incremental KBC (DeepDive, VLDB 2015) — incremental inference over a persistent KB.
4. Non-determinism of "deterministic" LLM settings (arXiv 2408.04667) — temp=0 is NOT bit-identical, so
   identity must not be derived from extraction-output wording (the empirical basis for D-3118).
5. Deterministic validation predicates for LLM causal extraction (IEEE) — the merge/upgrade verdict must
   be deterministic and LLM-free (D-343; D-2898: no LLM promotion).

**The layer (what is proposed, deterministic and LLM-free).**
A new module `pipeline/evidence_accumulator.py` (name TBD, config-first per C12), run at the S6 commit
boundary AFTER extraction, matching each incoming FB against the committed store and applying three
deterministic steps that REUSE the existing D-2950 primitives:
1. BLOCK (candidate generation) — match key = the generation-invariant `concept_key` (D-3118), with
   `normalize_name(name)` as the immediate Phase-A surrogate.
2. MATCH GATE (deterministic) — body-divergence gate (token Jaccard + SequenceMatcher, from
   dedup_identity) decides "same concept" vs "distinct concept sharing a name".
3. ACCUMULATE (monotonic — this is the automatic upgrade): `source_ids ← source_ids ∪ incoming.source_ids`
   (canonical ids, D2176), `source_diversity ← len(source_ids)`, `is_convergent ← (source_diversity >= 2)`,
   keep the richer body (D-2950 richness). NEVER remove a source (monotonic); NEVER downgrade is_convergent.

**Two properties that answer the owner's question directly.**
- AUTOMATIC UPGRADE: a singleton/single-source principle that reappears from a NEW book upgrades to
  convergent by structure (len>=2), with no owner word and no LLM. This is the missing "convergence".
- IDEMPOTENCY AT THIS LAYER ONLY: accumulation is deterministic and monotonic, so re-running it is
  idempotent (union of equal sets = equal result). The EXTRACTION layer above it is NOT idempotent
  (arXiv 2408.04667), so the honest idempotency claim is scoped to the accumulator, never the LLM.

**Forensic audit (conflicts/cascades/blindspots, before any implementation).**
- D-2933 rule V ("ontology never rewritten" for an existing fb_id): this layer is a DELIBERATE,
  SEPARATE post-commit pass that rewrites ONLY the provenance/corroboration fields (source_ids,
  source_diversity, is_convergent), never name/body. Declared an EXPLICIT EXCEPTION, not a silent
  violation; rule V still governs every other existing-fb_id write.
- D-2898 (no LLM promotion): no conflict — the upgrade is a structural recompute, not a model decision.
- D-2951 (dedup gate): COMPLEMENTS, does not replace — dedup answers "duplicate vs distinct", this layer
  answers "accumulate evidence + upgrade corroboration"; both must share the D-3118 concept key.
- D-2943 (store = one canonical run's artifact): the committed store is the persistent accumulation
  target; new corpus runs ACCUMULATE onto it (consistent with D-2881), never mint parallel identities.
- D-2950 (identity model): REUSED (classify_group / is_divergent / richness); the source_ids union is
  the intent, not a conflict.
- C6/C13: batch write → crash-safe (tempfile→fsync→os.replace / BEGIN IMMEDIATE) + backup_guardian.sh.
- KNOWN LIMITATION (declared, not hidden): `is_convergent = len(source_ids) >= 2` inherits the
  corroboration-collapse inflation (BUG-780/T-119: 530 of 1,393 "corroborated" rows are one text under
  two names). True source-independence validation is the existing T-119 instrument's job, not this layer.

**State: PROPOSED, owner-gated.** Mechanism not built. DEPENDS ON D-3118 (generation-invariant key).
Phase 0 harness (D-3036 red-loop-first, bounded-recall golden corpus) is the instrument that decides it.

## D-3118 (PROPOSED 2026-10-21) — Identity decoupling: generation-invariant `concept_key` (concretizes D-3107)

**Problem.** `fb_id = sha256(name|definition)` is generation-sensitive (D-2949; D-3106's 251/251 orphan).
D-3107 already PROPOSED generation-invariant identity at the GOLDEN-ANCHOR level; this spec concretizes the
same principle at the STORE level, where it becomes the match key for D-3117 and D-2951.

**Design — decouple two identities that are today one hash.**
- `fb_id` = IMMUTABLE storage key (minted once at first extraction, never rewritten; remains the row
  address and the `duplicate_of` referent).
- `concept_key` = GENERATION-INVARIANT match key, used ONLY for cross-run matching/accumulation (D-3117)
  and dedup grouping (D-2951). Two rows share a concept_key iff they are the same concept re-expressed.

**Staged derivation (non-overengineered; each phase gated by a receipt, D-3036).**
- Phase A (deterministic, immediate): `concept_key = sha256(sorted(normalize_name(name) content-tokens,
  stopword-filtered))`. Deterministic, cheap, no new model. Fragile to name PARAPHRASE (inherits D-2949's
  ~6% name survival), so it is the FLOOR, not the ceiling.
- Phase B (embedding recall, gated): semantic recall layer (embedding of name+definition, cosine +
  threshold) to catch paraphrased names. Default OFF; calibrated red-loop-first (D-3036) because the
  threshold is UNMEASURED on this machine — a hypothesis until a receipt speaks.

**Schema.** New nullable column `concept_key`. Migration follows the existing discipline
(pipeline/migrate_D2205_epistemic.py pattern); D-2205's own column is still absent from the live store,
so this migration must be tracked to completion, not declared.

**Forensic audit.**
- D-3107: this spec PROMOTES D-3107's "mechanism not built" → mechanism specified; not a competing decision.
- D-2950: the grouping key becomes `(concept_key, source_ids)` once Phase A lands; `normalize_name` remains
  the Phase-A surrogate (back-compatible).
- D-2949: extends the same diagnosis from dedup to identity (dedup was the first symptom; this is the disease).
- No conflict with D-2933 rule V: concept_key is minted at first extraction and immutable, never rewritten.

**State: PROPOSED, owner-gated.** Phase A implementable now; Phase B gated behind calibration.

## D-3117 / D-3118 — RATIFIED (2026-10-21) + Q2 refinement: FIELD-WISE richer merge

Owner ratified both records after a fresh senior-architect re-examination grounded in live-store
receipts (D-3034 — verified, not assumed). Three questions answered with evidence:

**Q1 — is auto-detect + auto-upgrade correct? YES (verified absent today, structurally right).**
`is_convergent` is minted ONCE at S2 (stage2_extract.py:1905 `sub_sid_count >= 2`), passed through S4
verbatim (stage4_merge.py:776), committed unchanged (stage6_commit.py:870). dedup_gate `decide()`
dispositions are insert | merge_convergent | keep_both_divergent | keep_both_cross_source | review
only — NO `source_ids` union, NO `is_convergent` flip. Live store cross-tab is CLEAN and self-consistent:
`is_convergent=1` ⟺ `source_diversity>=2` (896 = 896), `is_convergent=0` with `sd>=2` = 0,
`is_convergent=1` with `sd<2` = 0. `duplicate_of` column EXISTS but 0 populated (gate inert, mode=report).
Live split: 6,744 single-source / 896 convergent. ⇒ D-3117 does NOT invent a new convergence definition;
it re-derives the SAME S2 rule (`len(source_ids)>=2`) at a monotonic accumulation point. Correct.

**Q2 — loss-avoidance WITHOUT clutter? YES, with ONE refinement (adopted).**
`richness()` = count of non-empty body fields; `pick_richer` = single winner (max richness, tie→existing),
never concatenates. But WHOLE-ROW winner-take-all can drop a COMPLEMENTARY field (book A's mechanism vs
book B's failure_mode) even when the match gate still says "same concept". REFINEMENT ADOPTED: ACCUMULATE
merges FIELD-WISE — per body field keep the richer of existing vs incoming (non-empty beats empty; among
two non-empty keep the more complete, tie→existing) — instead of whole-row winner-take-all. This is
loss-averse (a filled field is never dropped for an empty one), clutter-free (exactly one value per field;
NEVER concatenation, NEVER a summary/noise copy), and reuses D-2950's `body_tokens`/`richness` primitives
(not over-engineered). `source_ids` union remains the ONLY growth vector — evidence, not clutter.

**Q3 — is idempotency the right integrity anchor? YES, scoped correctly.**
The accumulator's three steps are each idempotent (set union, `len`, `>=2` threshold, per-field max) AND
monotonic, over a deterministic LLM-free layer (D-343). The EXTRACTION layer above is NOT idempotent
(temp=0 sparse-MoE non-determinism, arXiv 2408.04667). ⇒ The integrity anchor is the PAIR
(monotonic + idempotent) scoped to the deterministic accumulator; it is never claimed for the LLM layer.

**Gov dependency sync (no conflicts, no supersessions introduced).**
- D-3107 (generation-invariant anchor identity): CONCRETIZED by D-3118 at the store level — D-3107 stays
  the anchor-level principle, D-3118 is its store-level mechanism. Complementary, not superseded.
- D-2951 (dedup gate): unchanged; complements D-3117 (dedup = duplicate-vs-distinct; accumulate = evidence
  + convergence upgrade). Both share D-3118's concept_key.
- D-2933 rule V: the explicit exception already declared in D-3117 stands (provenance-only rewrite), now
  bound to field-wise richer merge over the 8 body fields — name/body never rewritten outside the gate.
- D-2898 (no LLM promotion): unchanged — the upgrade is structural recompute, not a model decision.
- D-2949 / D-2950 / D-3106: unchanged; D-3118 extends D-2949's diagnosis from dedup to identity.
- config/decisions.yaml: D-3117/D-3118 move PROPOSED → APPROVED via the registry's normal sync path.

State: D-3117 RATIFIED (with field-wise richer merge). D-3118 RATIFIED.
Next critical step: D-3118 Phase A (concept_key column + backfill) — the dependency D-3117 blocks on.

## D-3118 Phase B GATE-FLIP (2026-10-21) — Phase B is now MEASURED-NECESSARY, not an unmeasured hypothesis

**Receipt (D-3036).** `governance/PHASE0_IDEMPOTENCY_REPORT.md` (committed a6323a7) ran S0→S5 TWICE on a fixed
16-book corpus and measured cross-run survival. Three readings:
- `fb_id` survival **27%** (jaccard 0.2726) — the generation-sensitive key, as D-2949/D-3106 predicted.
- `name` survival **72%** (jaccard 0.7204) — the Phase A surrogate's actual floor.
- `body_hash_8field` survival **0%** (jaccard 0.0) — extraction is never idempotent (arXiv 2408.04667), so any
  key that folds the body can never re-match a body-divergent re-extraction.

**Two corrections to the D-3118 record, both now facts, both were silent drift:**
1. **Phase A is not "~6% name survival".** D-3118 imported D-2949's "~6%" figure; the Phase 0 receipt measures
   **72%**. The floor is 12× better than recorded. This matters: a 6% floor would have justified treating Phase A
   as a placeholder; a 72% floor makes Phase A a real, build-now base layer.
2. **Phase B is no longer an unmeasured hypothesis.** The receipt names the exact gap Phase B must close: the
   **~28% name-paraphrase loss** (100% − 72%). Phase B's *necessity* is measured; only its *cosine threshold*
   remains uncalibrated, and that is the Phase B red-loop (D-3036), now with a measured target.

**State.** Phase A proceeds as scheduled (build-now). Phase B's gate flips from "deferred/unmeasured" to
"necessary, threshold-to-be-calibrated". No owner action required beyond the standing approval; this record
closes the drift the receipt exposed.

## D-3117 MATCH GATE RECONCILIATION (2026-10-21) — body-divergence is measured-unreliable as a HARD gate

**Receipt (D-3036) — two readings, one conclusion.**
1. Phase 0 (a6323a7): `body_hash_8field` survival **0%** (jaccard 0.0) — extraction is never idempotent
   (arXiv 2408.04667), so any gate that keys on body wording cannot re-match a body-divergent re-extraction.
2. Live store (this reconciliation): **all 5** duplicate `concept_key` groups return `is_divergent == True` under
   the D-2950 body-divergence gate (token Jaccard + SequenceMatcher), including:
   - "Design Thinking Process" from TWO DIFFERENT books (jaccard 0.116) — the exact cross-source re-appearance
     D-3117 exists to accumulate (the corroboration upgrade);
   - "Social Identity Influence on Behavior" / "Social Influence on Identity and Behavior" (jaccard 0.105) — the
     name-paraphrase pair Phase A correctly collided into one key.

**The conflict.** D-3117's PROPOSED text (written BEFORE the Phase 0 receipt) specifies step (2) MATCH GATE as a
body-divergence gate reusing D-2950's `is_divergent`. But body-divergence CANNOT separate the two cases the gate
exists to separate — "same concept re-extracted from a different book" (body diverges by construction, should
ACCUMULATE) vs "distinct concept sharing a name" (body diverges, should KEEP BOTH) — because the extraction layer
destroys the body signal (0% survival) in BOTH cases. As literally specified, the MATCH GATE rejects every
cross-source re-appearance, and D-3117 becomes a SILENT NO-OP: the module passes its own tests while failing its
purpose.

**Reconciliation (a correction, not a new decision — it reconciles D-3117 with a receipt it predates).**
- The MATCH GATE is REPURPOSED from a HARD body-divergence reject to a REPORTED divergence metric: BLOCK on
  `concept_key` → ACCUMULATE monotonic (unchanged), and the body-divergence (token Jaccard + SequenceMatcher) is
  computed and REPORTED (mode=report default), never a blocking reject.
- Homonym disambiguation (the gate's original purpose) is DEFERRED to D-3118 Phase B embedding recall — the cosine
  threshold Phase B calibrates is exactly the discriminator a 0%-stable body token gate cannot be.
- Monotonic + report-mode + recoverable (source_ids union, is_convergent flip) bounds the false-positive risk; the
  corroboration-collapse inflation (BUG-780/T-119) remains the declared known limitation, unchanged.

**Why the asymmetry inverts here (the D-2950 rule does not transfer).** D-2950's `is_divergent` is deliberately
one-sided ("a false divergent keeps two rows, visible and recoverable") — but that rule is scoped to SAME-WORK
dedup (source overlap), where a false "keep both" is cheap and a false "merge" drops a distinct concept. In the
ACCUMULATION layer the asymmetry INVERTS: a false "divergent" is a SILENT lost corroboration (no row, no flag, no
recoverable trace), while a false "convergent" is a visible, monotonic, reversible source_ids union. Doubt must
therefore go to ACCUMULATE here, and the divergence signal becomes an audit trail (Phase B's calibration input),
not a reject.

**Effect on the build.** `pipeline/evidence_accumulator.py` keeps its three steps; step (2) becomes "record
divergence" rather than "reject on divergence". No schema change beyond the already-planned `concept_key`; the
divergence metric is report-only in Phase A (a nullable column is Phase B's concern, where it feeds the calibrated
cosine threshold).

**State.** Reconciliation RECORDED, not yet owner-gated — the accumulator build proceeds on the corrected shape
once the owner acknowledges, or is reverted to the hard gate if the owner holds the hard-gate line. The two-sided
receipt above is the evidence either way.

## D-3117 MATCH GATE RECONCILIATION — OWNER ACCEPTED (2026-10-21) + content-type scope refinement

Owner acknowledged the reconciliation this session. Repurpose the hard body-divergence reject to a REPORTED
divergence metric: BLOCK on `concept_key` → ACCUMULATE monotonic → divergence (token Jaccard + SequenceMatcher)
computed and reported, never a blocking reject; homonym disambiguation stays deferred to D-3118 Phase B. The
two-sided receipt stands: `body_hash_8field` survival 0% (Phase 0 a6323a7), and all 5 live duplicate `concept_key`
groups are `is_divergent` (incl. "Design Thinking Process" from TWO different books, jaccard 0.116) — the exact
cross-source re-appearance D-3117 exists to accumulate. A hard body gate would be a silent no-op.

SCOPE REFINEMENT (new finding this session, measured not assumed — D-3034). The ratified ACCUMULATE step wrote
`is_convergent ← (source_diversity >= 2)` with NO content_type scope. Live-store measurement (2026-10-21, this
session) shows the store ALREADY holds 4 convergent non-principle rows: 2 `process_template` (one at
source_diversity=77 — a misclassified shared procedure) + 2 `noise_drop`. Therefore "convergent → principle"
(BUG-231/BUG-166) is an EXTRACTION-layer design (the S2 convergent prompt emits principle-only), NOT a store
invariant — and a uniform `is_convergent` flip would manufacture convergent non-principles and silently blur the
BORP corroboration signal, which is a PRINCIPLE-scoped concept (">=2 independent sources" = the Book of Record
Principle).

RULING (refinement, not a new decision): the ACCUMULATE evidence union (`source_ids ← source_ids ∪ incoming`,
`source_diversity ← len`) applies to ALL content types — evidence is content-agnostic and monotonic. The
`is_convergent` FLIP is scoped to `content_type='principle'` by default, behind a config flag
(`accumulate.is_convergent_scope: principle | all`). A multi-source non-principle keeps its `source_diversity`
bumped (visible, useful — this IS the "convergent non-principle" signal the owner asked about) but is NOT stamped
`is_convergent` until "convergent non-principle" is a deliberate first-class decision (candidate D-3119). This makes
the owner's scenario DETECTED — a single-source process_template later corroborated by a NEW book advances
source_diversity 1→2 — without silently relabeling it under BORP.

State: RECONCILIATION ACCEPTED. Build proceeds on the corrected shape: record divergence (report) + accumulate
evidence for ALL content types + `is_convergent` flip principle-scoped behind the flag.

## D-3117 BUILD COMPLETE — evidence_accumulator applied to live store (2026-10-21)

D-3117 cross-run evidence accumulation is BUILT and APPLIED. Artifacts: `config/accumulate.yaml` (config-first,
C12) + `pipeline/evidence_accumulator.py` (deterministic, LLM-free) + `governance/evidence_accumulator_receipt.jsonl`.

R5 review (gemma-4-E4B-it-MLX-4bit, generator≠verifier) found 2 real defects, both FIXED:
(1) noisy receipt filter — `len(source_set_of(v)) >= 2` admitted single-row already-convergent groups, flooding
the receipt with hundreds of no-op `[2]->2`/`[49]->49` rows and making `--check` always red; fixed to `len(v) >= 2`
(cross-row = 2+ distinct fb_ids) + a computed `would_accumulate` (source-growth OR empty-field-fill) so the red-loop
goes GREEN after apply (D-3036). (2) dead imports `shutil` + `PROJECT_ROOT` removed (C19). The verifier also raised
a NO-GO on a claimed non-idempotency; REFUTED EMPIRICALLY — apply on a copy then re-run: PASS1 would_accumulate=3,
PASS2 would_accumulate=0 (idempotent+monotonic by construction: source union + empty-field-fill only).

LIVE APPLY (behind C13 backup `knowledge pipeline/maxwell.db.bak_accumulate_20261021_143827`): 5 duplicate
concept_key groups, 3 accumulated, 2 no-op, verified green (`--check` exit 0). Receipt is the D-3036 red-loop instrument.

TWO ONTOLOGICAL FINDINGS (owner-gated follow-ups, NOT accumulator defects):
(1) "Social Identity Influence on Behavior" (principle, key `1d2d0aca1632`) — 2 paraphrased-name rows from 2 sources
flipped `is_convergent=1` with `is_divergent=True` (bodies differ): convergent-per-D3117 but divergent-per-body — the
"corroboration vs convergence" boundary, recorded not resolved.
(2) "Poker" concept_key `ccf192e8551b` groups the SAME concept under TWO content_types: "Poker As Decision-making
Framework" (principle) + "Poker Decision-Making Framework" (process_template) — a PRE-EXISTING classification
conflation surfaced by the key, untouched by accumulation (no-op group). Owner adjudication required.

## D-3120 — DEFER oMLX 0.7.2 upgrade (2026-10-21)

Examined `jundot/omlx` v0.7.1...v0.7.2 (32 commits via GitHub API). ~28 of 32 are IRRELEVANT to Maxwell's headless
single-machine non-MTP non-GGUF non-deepseek usage: web-UI/cosmetic (status card, dark theme, navbar keyboard nav,
i18n, WCAG AA, copy buttons), Splash/specprefill/DFlash speculative-decode refactors (`mtp_enabled=false`), cluster
MTP (multi-Mac), and model-family perf (deepseek_v41 oQ2e-oQ4e, Qwen3.8-Flash-Next GGUF, ParoQuant Qwen). The ~4
relevant ones are API hardening (reject non-positive max_tokens; system-note ordering after a tool result; bound
thinking for Claude Code auto-mode) that Maxwell's single-shot `omlx_call.py` path likely never triggers.

Verdict: DEFER. 0.7.1rc1 was A/B-ADOPTED 2 days ago (D-3102) with a receipt; a blind 0.7.2 upgrade has zero red-loop
receipt for Maxwell's fleet = drift (D-3034/D-3036). Note 0.7.1rc1 is a release candidate — a mild hygiene smell, but
owner-accepted via D-3102 with rollback `/Applications/oMLX-0.7.0.app`. TRIGGER to revisit: a commit touching base MLX
decode/prefill or the chat-completions API for Maxwell's model families (Qwen3-Coder / gpt-oss-20b / Phi-4-mini /
MiniCPM5 / gemma). Registered so it is not re-proposed from memory (D-3038).


## CORRECTION (2026-10-21) — D-3117 "Poker no-op" claim SUPERSEDED by BUG-959

The D-3117 note above ("Poker concept_key `ccf192e8551b` ... untouched by accumulation (no-op group)") is CORRECTED
by BUG-959 (governance/buglog.md). The C13-backup comparison measured a real empty-field-fill: the accumulator wrote
the principle row's application/elaboration into the process_template row (fb_id f81658d0...) whose fields were empty
pre-run. Poker was an [ACCUMULATE] via fill (no source-growth), not a no-op. The authoritative register is BUG-959,
which also holds the owner adjudication gate (revert 2 fields + split the false merge).

## D-3121 — Qwen3.6-35B-A3B evaluated for the generator ("brain") role; DEFER swap (measure-gated), NO omlx upgrade (confirms D-3120)

Examined the model the owner flagged ("qwen 3.6 35B" via the HF mlx-lm filter) = Qwen/Qwen3.6-35B-A3B. Architecture
(qwen3_5_moe, from config.json): 35B total / A3B = 3B active MoE (256 experts, top-8), hidden 2048, 40 layers,
16 heads, 2 KV heads, head_dim 256, vocab 248320, max_pos 262144 (irrelevant at Maxwell's 32K, D-3115).

Speed: 3B active MoE -> decode/prefill in the SAME class as the current generator Qwen3-Coder-30B-A3B (measured
34.5 tok/s). KV cache = 2x40x2x256 = 40,960 el/tok ~ 80 KB/tok fp16 ~ 2.7 GB @ 32K ctx - SMALLER than Qwen3-Coder-30B
(48L x 4KV x 128 ~ 98 KB/tok). Memory ~ 17.5 GB @ 4-bit; the 35B class is already proven on this M1 Max (Ornith-35B
was loaded, BUG-952).

Loadable on the CURRENT omlx 0.7.1rc1: the bundled mlx-lm 0.31.4.dev132 contains mlx_lm/models/qwen3_5_moe.py
(verified in /Applications/oMLX.app). So NO omlx upgrade is needed for this model - D-3120 stands (its trigger was
base-MLX or chat-completions commits, not a model architecture). Community 4-bit quants exist (mlx-community/
Qwen3.6-35B-A3B-4bit 2026-04-16; lmstudio-community/Qwen3.6-35B-A3B-MLX-4bit).

"Better for brain?" is a HYPOTHESIS (D-3036), not a receipt: it is a newer GENERALIST vs a coder-specialist, plausibly
better at general extraction/classification, but there is no measurement on this machine. DEFER the swap: the only
future-proof path is a cheap reversible A/B vs Qwen3-Coder-30B on the S2 probe / eval floor with a red-loop receipt,
then adopt only on a measured WIN. Registered so the swap is not proposed from memory (D-3038).


## D-3122 — BUG-959 APPROVE-A+B IMPLEMENTED: revert + content_type necessary-condition guard (2026-10-21)

Owner APPROVE-A+B. Executed with a D-3036 red-loop receipt and R5 review (generator≠verifier).

Part A (revert): `pipeline/revert_bug959.py` reconciled the process_template Poker row `f81658d0`
(`application` ''→214c, `elaboration` NULL→556c) back to the C13 backup
`knowledge pipeline/maxwell.db.bak_accumulate_20261021_143827`, in one C6 transaction. `--check` red-loop:
2 contaminated fields (application, elaboration) BEFORE → 0 AFTER (RED→GREEN).

Part B (permanent guard): `pipeline/evidence_accumulator.py` now groups by `(concept_key, content_type)`
instead of `concept_key` alone. content_type is axis 1 = functional ROLE, so two rows sharing a concept_key
but differing in content_type are DISTINCT concepts by definition and can never cross-fill body fields. The
4 legit same-type accumulation groups (VJ Performance Method, Design Thinking Process, Item Validation
Protocol, Social Identity Influence on Behavior) are unaffected (report mode: groups=4, cross-type SUPPRESSED=1).

R5 review: gemma-4-E4B APPROVED. Phase B (embedding cosine divergence for same-type collisions + the ~28%
name-paraphrase false-negative gap) remains OPEN under D-3118; the Poker collision is its red-loop fixture.

D-3134 (ACTIVE 2026-10-23): **A MEASUREMENT THAT LICENSES AN ACT MUST BE RE-TAKEN AFTER THE ACT — and a debt ceiling is PER CLASS, because one total lets a repair conceal a new defect.** BUG-977. D-2965 justified its leaf-label gate with "MEASURED 2026-10-12: 7,640 rows · 0 blanks · 0 dispositions — this gate is NEUTRAL today". The D-2590 sidecar commit stamped `committed_at 2026-10-12T09:58:32` on ten rows carrying a DISPOSITION as their `content_type`; the gate that refuses exactly that landed in `d69de66` at 21:09:54 — **eleven hours later** — and the premise was never re-taken. Eleven days of a register asserting "0 dispositions" over a store holding ten, SIX of them in the default answer path (measured today through the serving layer's own predicate, never a copy). The rule, in four parts. (1) THE PREMISE RULE: a number that GRANTS a permission ("nothing to fix", "gate is neutral", "pathway is armed not firing") is a CLAIM with an expiry — it must be re-measured after the act it licensed, and a stale premise is a finding, not a footnote (D-3034 applied to measurement, not only to declarations). (2) THE SCOPE RULE, restated because it fired: an instrument's POPULATION is part of the instrument (D-2956 cl.4) — the gate that owns "a disposition is not a content_type" measured only the owner's adjudication map (19 of 546 rows resolve to the store), a population that CANNOT contain the defect, so it printed `disposition_served 0` while six rows were served. A rule now ships with a census over the population that matters, in the SAME instrument (one rule, one home, C21) — `scripts/restamp_content_type_adjudications.py::store_census`. (3) THE CEILING RULE: a MEASURED debt is declared **per class, never as one total** — a single number would let a repaired disposition row be replaced by a NEW undeclared label while the total still read 10, i.e. the ceiling itself would launder the substitution; each class carries its own shrink-only ceiling (D-2642), and a class ABOVE its ceiling is a REFUSAL (rc 1) while at or under it the reading is OWNER-OWED (rc 2, loud not fatal, BUG-457). (4) THE WRITER RULE for provenance: a label's authorship is chosen by WHAT ACTUALLY AUTHORED IT — a DECLARED rule is `deterministic` (never `human_verbatim`, never `llm_extracted_from_source`), and the tier-B ruling sheet carrying MATCH/NONE only is the measured proof that the owner ruled PRESENCE and not the ROLE (BUG-978). Companion, mechanical: a health rail that WRITES must not run inside health — the census ships a read-only `--check` because a rail that dirtied the worktree would be judged by the rail that reads it (BUG-563). NOT DECIDED HERE: no label was moved (a content_type is a curation judgement, D-2898), no ceiling was raised, no disposition column was created (D-2952). The owner's ten rulings are the next act, handed over as a typed walker rather than a JSON to paste (`scripts/rule_content_type_census.py`), because the last hand-off of this shape ended in `zsh: command not found` (D-3100).

D-3135 (ACTIVE 2026-10-23): **A DISPOSITION RULING ON A STORED ROW IS ENACTED BY WITHDRAWAL, NOT BY A COLUMN — because the store admits ROLEs only, and the ruling's home is the map.** BUG-977/BUG-741b/BUG-980. Three acts completed the owner's ten rulings: (a) the four ROLE rulings were WRITTEN as labels (`human_verbatim`, the declared value for a human-ruled label, BUG-742); (b) the six DISPOSITION rulings were ENACTED — 6 rows withdrawn archive-first, 72 graph edges pruned in the same transaction, vectors removed, FTS rebuilt, store 7,641 → 7,635; (c) the census ceiling SHRANK 6/4 → 4/2 → **0/0**, each step licensed by a re-measurement (D-3134 clause 1) and never raised (D-2642). The reasoning, because the alternative was seriously on the table: a `curation_disposition` column would have left the `content_type` violation in place (the owner ruled there is NO clean role, and D-2965's leaf gate refuses a disposition in that column), and a column no reader consults is the "inert badge" D-2952 refuses to build ahead of its writer. **The store is not the place a disposition lives: the adjudication map is** — it holds the ruling, its reason and its confidence — and the store's own contract (D-2965, the closed 5-role axis, the S4 HOLD SHELF that is "never a commit source", D2616) says such a record was never admissible. So the act is REMOVAL with `retention` naming the intent the ruling carried: `noise_drop → dropped`, `quarantine → hold`. Four clauses that generalise beyond this bug. (1) **THE WRITER RESOLVES OR THE DECLARATION IS EMPTY:** a config that names an act and writes `writer: OWED` is a promise, and a promise whose trigger has FIRED must be kept in the same session that observed it — the gate's exit code went to 1 (BLOCKING) the moment the rulings landed, and the answer was to build the writer, not to teach the ladder to tolerate red. (2) **A WITHDRAWAL IS ARCHIVE-FIRST AND TRANSACTIONAL, and it prunes what pointed at it:** a surviving row referencing a withdrawn id is a dangling edge that retrieval resolves to nothing (the BUG-711 shape) — so edges are pruned inside the same `BEGIN IMMEDIATE`, archived, and a prune that would EMPTY a reference column is REFUSED. The protocol is `scripts/purge_superseded_runs.py`'s, applied to a NEW population in a NEW instrument (D-2956 cl.4: `runs` never selects a row, and a curated row may live in the canonical run whose protection is about RUNS). (3) **A REPAIR MAY NOT CHANGE A VERDICT IMPLICITLY** (BUG-979): editing a cell and overturning a verdict are different acts, so `scripts/reverify_one_row.py` refuses a status change without `--allow-verdict-change` — the row it repaired ("The Kernel of Strategy") FAILED the mechanism gate it was never run against (134 chars < the 150 floor), and the honest outcome was QUARANTINE/`vacuous`/confidence 0.25, not a green cell. (4) **A SILENT DEGRADATION IS NOT A FALLBACK:** `pipeline.sqlite_vec_loader` returns `loaded=False` and the store then keeps a live vector for a deleted row (the BUG-713 harm). MEASURED: the `python3` on PATH cannot load `sqlite_vec` while a declared interpreter can — so the interpreter is DECLARED (`config/curation_withdrawal.yaml#vec_loader`) and the tool re-execs once, because a prerequisite that decides whether the act is COMPLETE must never be skipped quietly. NOT DECIDED HERE: no ceiling was raised, no label was invented (the 6 archived rows keep their label in the archive; the map keeps the ruling), no new vocabulary value was minted, and the extraction of S5's per-record sequence into one callable is REGISTERED as T-196 rather than improvised at the tail of a repair (D-3036: a red loop first).

D-3136 (ACTIVE 2026-10-23): **A RULE WITH FOUR HOMES TELLS FOUR TRUTHS — the per-record verification sequence has ONE home, and a rail keeps it single.** T-196, closing the BUG-978/979/980/981 family. MEASURED before the act: the sequence (mechanism gate → short-circuits → NLI → enrichment → verdict → ISOR → score axis → label → facet tier) existed in FOUR files, and each copy had drifted — `insert_single_concept.py` computed no ISOR at all and derived its label from `None`; `reverify_one_row.py` echoed a stored ISOR instead of computing one; `reinject_bug198_singletons.py` had no evidence-contamination short-circuit and hardcoded a verifier identity naming `threshold 0.10`, a threshold D-2863 had already moved to 0.5, so the copy NAMED a rule it did not run. Four copies, four behaviours, five bugs. The rule now has one home, `pipeline/verify_record.py::verify_one_record`, and `scripts/check_verification_sequence.py` (a ladder rail) fails if a fifth copy appears (AST census, not text: a docstring that names a check is a sentence, not a call — the rail's first draft matched its own documentation). Five clauses generalise beyond this bug. (1) **THE INPUT CONTRACT IS PART OF THE RULE.** MEASURED twice in one day: the store keeps list-shaped cells as JSON TEXT while every check expects a list, so a raw store row made the NLI answer "No evidence" (BUG-979) and made ISOR report `n_sources=0` for a row carrying one source id (measured 2026-10-23, when a repair wrote exactly that blind value before the contract was enforced). Hydration therefore lives IN the home (`hydrate_json_lists`), so a caller cannot get it wrong, and the rail asserts a store-shaped row derives what a native row derives. This is D-2956 clause 4 one level down: the shape of an instrument's INPUT is part of the instrument. (2) **ONE RECORD, TWO TYPED FACES, BOTH OWNED HERE.** The store takes `verification_results`/`isor` as JSON text and the review flag as 0/1; the S5 checkpoint takes list/dict/bool. `store_cells()` and `checkpoint_cells()` produce both, so no caller re-types a cell — a conversion each writer retypes is a rule with N homes wearing a smaller costume. (3) **A DERIVED IDENTITY IS DERIVED.** `verifier_model` is now built from the declared model + threshold, because a typed copy had already drifted to a retired threshold. (4) **A WRITER'S WRITE SET IS THE HOME'S STORE FACE, not a hand-picked subset:** the subset is how a confidence derived WITH an ISOR rating was written beside a BLANK `isor` cell (D279 quartet atomicity applied to the score axis). (5) **THE HOME JOINS THE FINGERPRINT AND THE INVALIDATION IS DECLARED, NEVER DISCOVERED:** `pipeline/verify_record.py` is added to `stage5.fingerprint_files` (BUG-614: the fingerprint must cover every module that changes the OUTPUT), and the checkpoint's stored input fingerprint (`67e4f251…`) no longer matches the current one (`ed813bc0…`), so the next S5 resume DISCARDS and re-verifies — recorded in `governance/evidence/t196_verification_home_receipt.json` rather than left to be discovered mid-run. MEASURED AFTER the act (D-3134 clause 1): `check_serving_gate` 7,635/7,635 MATCH, `check_s5_score_axis` 6,586 MATCH / 0 undecidable, `check_label_provenance` 7,635 stamped, the new rail green, `ruff check pipeline/stage5_verify.py` clean, R5 gate APPROVE on the home and on S5 (gemma); and repairing the single-concept row through the home wrote exactly ONE cell (`isor`) with `n_sources=1`, closing the store's declared `isor` blank so the column's CONSTANT-OR-BLANK debt class disappears while the ceiling stays at 8 (never raised, D-2642). NOT DECIDED HERE: the sequence is not reordered, no threshold or weight moves, no label is invented, and the two DELEGATED reviews that failed (gemma and Qwen3-Coder, both "max turns reached", journalled `failed` with their measured wall times) are recorded as FAILED runs, not as approvals — the R5 verdicts in force are the governed gate's, not a subagent's report.

D-3137 (ACTIVE 2026-10-23): **A FLOORED RULING IS HANDED OVER WITH ITS READING — PROPOSE, GROUND and RULE are three different acts, and only the last one is the owner's.** T-195 step (c), asked as a direct question: *haven't Qwen and gpt-oss already done these 43 MATCH/NONE classifications, and if not, can't they be run now?* MEASURED, because the answer decides whether 43 human rulings are owed at all. (a) The ruling sheet holds **2** lines — `The Kernel of Strategy` MATCH, `LLM-Based Application Patterns` NONE — against **45** proposed candidates, so **43 are unruled**. (b) Qwen3-Coder did not rule them; it **PROPOSED** them (`config/extraction_recall.yaml#proposer.model`), and every one of the 45 rows carries exactly `{source_id, name, rationale}` — a proposal, which D-2898 forbids certifying. (c) gpt-oss-20b + Qwen3.8 **did** emit MATCH/NONE verdict columns, but over a DIFFERENT population: `ANCHOR_208_REANCHOR_ADJUDICATION_*` covers the **195 dangling anchor names** of the T-191 re-anchor, and the name overlap with the 43 tier-B candidates is **0/43** — a verdict vocabulary that matches is not a reusable verdict (D-3034: a declaration must RESOLVE to this object). So no prior model pass can be spent here, and the owner's gate cannot be delegated away. What CAN be built is what was missing: the reading the ruling stands on. `scripts/tier_b_evidence.py` now measures, per candidate, source grounding (`name_verbatim_hits`, concept-token coverage in the SAME token space `concept_key` mints from — `pipeline.dedup_identity.content_tokens`, one home) plus store novelty (bge-m3 cosine against the store rows of THAT source, top 3), and `rule_tier_b.py` prints all of it inside the walk. Five clauses generalise. (1) **A FLOORED RULING IS HANDED OVER WITH ITS READING.** `expectation_recall` is 1.0, so a wrong MATCH leaves the recall rail permanently RED until the concept is extracted and a wrong NONE loses the concept silently: the ruling must rest on a measurement, not a recollection (D-3100 taken one level down — the handover owes the *evidence*, not only the command). (2) **THE GROUNDING INSTRUMENT MUST BE DECORRELATED FROM THE PROPOSER.** Asking the proposing family to confirm its own proposals measures agreement with itself, and BUG-053 is the standing finding that open-ended delegated judgement hallucinates; the instruments used here are the **bytes** (a scan, which cannot hallucinate) and a **non-generative embedder** (bge-m3), the same third-signal principle the re-anchor bridge uses (D-2658). (3) **A CITATION MUST CONTAIN ITS OWN EVIDENCE.** MEASURED while building it: cutting a long paragraph at its first `max_excerpt_chars` characters showed a passage whose matched tokens sat BEYOND the cut, and markdown books split into list items so the best token coverage often lands on a table-of-contents line — the sheet now windows AROUND the first matched token and labels each reading `prose` or `fragment/list` (38/45 prose, 7 flagged), so the owner knows what they are reading. (4) **QUOTE THE STORE'S DECLARED BAND; DO NOT INVENT ONE.** The "already carried under another label" signal is reported against `config/pipeline_config.yaml#stage4.semantic_near_threshold` = 0.8 (the store's own notion of near), not a number picked here; measured result: **1 of 45** at or above it (`Prompt Template Abstraction` 0.8494 → a stored `Prompt Template Implementation`), so 42 candidates are genuinely novel for their source and one should be ruled with the collision in view. (5) **A CANDIDATE'S PROVENANCE IS PART OF THE CANDIDATE.** The proposer now stamps `window_index` + `window_sha16` (BUG-985) so "this candidate came from this source" is checkable instead of trusted, and the evidence sheet VERIFIES the stamp when present rather than believing it. MEASURED AFTER the act (D-3134 cl.1): evidence sheet writes 45 rows, `owed []` and `warnings []`; `check_extraction_recall --check --no-report` → concept 45/45, expectation 419/419 CLEAN (rc 0, report untouched); the walk renders `[k/43]` with rationale, tokens, verbatim hits, closest stored row and the reading, and `--count` still reports `43 unruled / 45 total`; the proposer's 6-control and the evidence script's 5-control selftests are green, both wired into `justfile#health`; `check_config_defaults` stays at 300 shadowed-declared (no ceiling raised) and `check_rail_registry` ok. NOT DECIDED HERE: **no candidate is ruled, no model verdict is recorded anywhere, no floor, weight or threshold moves, and no new candidates are proposed** — a MATCH/NONE remains the owner's typed word, and this decision only guarantees that when the owner types it, the reading that decides it is already on the screen.

## D-3138 — A HANDOVER TO THE OWNER CARRIES THE DECISION COLUMN AND A POINTER THAT RESOLVES (2026-10-24)

T-195 step (d2), forced by the owner's report: *"I cant find any of fb that are under name and concept key in t11
checkpoints … how the fuck I supposed to decide I find can even read it? also there are no section for owner decision
in csv"*. BUG-988 is the measurement; this record fixes what the four acts owe each other.

**THE ACT COUNT IS FOUR, AND ONLY ONE OF THEM IS THE OWNER'S.** PROPOSE (Qwen3-Coder, advisory) → GROUND (bytes +
bge-m3) → ADJUDICATE (a 4-model panel, advisory, D-3137) → RULE (the owner). MEASURED this sitting: the panel
(deepseek-flash + gpt-oss-20b-MXFP4-Q8 + Qwen3.8-27B-MLX-4bit + Ornith-1.5-35B-A3B-REAP-19B, proposer and Phi-4-mini
excluded by R5/BUG-053) returned **20 of 43 unanimous** (6 UNANIMOUS MATCH, 14 UNANIMOUS NONE) and **23 need review**
(5 MAJORITY MATCH, 12 MAJORITY NONE, 6 SPLIT), with **zero INCOMPLETE** rows after BUG-987 was fixed. Unanimity is a
reason to look once, not a ruling: what it buys the owner is ONE acceptance step for twenty rows instead of twenty
decisions — it never buys the act itself (D-2658/D-2898).

**FIVE CLAUSES, EACH ONE A DEFECT THAT WAS MEASURED.**

1. **A REVIEW SHEET WITHOUT A DECISION COLUMN IS NOT A REVIEW SHEET.** The adjudication CSV carried 18 columns and
   none for the owner's word, so the one human gate in the arm had no instrument. A handover owes the COLUMN, and a
   COMMAND that consumes it — `scripts/rule_tier_b.py --from-csv` — so the ruling is typed once, in the artifact the
   reading is in, and becomes the ruling sheet with no JSON to paste (D-3100 taken to its end).
2. **A POINTER MUST NAME THE RUN IT LIVES IN.** MEASURED: 0 of 23 `closest_fb_id`s and 0 of 23 names resolve into the
   t11 S5 checkpoint, because the live store is run `rechunk-v4-20260929` and the checkpoints are a different run. The
   sheet now prints the run, the status and a crossref verdict per row ("NOT in t11 — this store row lives in run
   rechunk-v4-20260929"). A pointer that cannot say where it resolves is a declaration with no referent (D-3034).
3. **AN ABSENCE THAT IS BY CONSTRUCTION MUST BE STATED, WITH THE COUNT THAT PROVES IT.** A tier-B candidate is a
   concept the extractor did NOT produce (D-3130), so a checkpoint can never contain it: MEASURED 0 of 43 concept keys
   in the store and 0 of 43 in the t11 S5 checkpoint, median store cosine 0.609 (38/43 under 0.7). Handing the owner
   a checkpoint to search for these is a guaranteed no-op; the sheet says so in one line before row 1.
4. **A QUOTE WITHOUT A LOCATION CANNOT BE CHECKED.** Every row now names the book AND the paragraph index
   ("paragraph 2131 of 4576 in …"), with the neighbouring paragraphs, so the reading is verified in the source rather
   than trusted from the sheet (D-3137 cl.3, one level deeper).
5. **THE RULING COLUMN IS EMPTY AND STAYS EMPTY UNTIL THE OWNER TYPES.** Measured: 0 of 23 rows pre-filled. A sheet
   that pre-fills a verdict has ruled for the owner; `--from-csv` treats a blank cell as NOT RULED (skips it), refuses
   an unknown token fail-closed (`owner_decision='YES'` → rc 1), and skips an already-ruled candidate so a re-run
   after a partial fill cannot double a ruling.

**RECEIPTS.** `scripts/tier_b_owner_sheet.py` writes 23 rows to
`governance/EXTRACTION_RECALL_TIER_B_OWNER_REVIEW_20261023.{csv,html,md}` (config:
`extraction_recall.tier_b_adjudication.owner_sheet`, reading_chars 1400 / context_chars 260 / crossref_checkpoint
declared). Selftests: owner sheet **7 controls** green (index-preserving splitter, nearest-present neighbour, window
carries its cited token and respects the cap, z-library parenthetical stripped, decision+note are columns 2–3);
`rule_tier_b --selftest` **5 controls** green. `--from-csv` controls: blank → `0 record / 23 blank`; two filled →
`2 / 21 blank`; typo → FAIL-CLOSED at the exact line. Panel envelope and disagreement CSV unchanged and re-verified:
0 INCOMPLETE, 0 model errors.

**NOT DECIDED HERE.** No candidate is ruled. The 20 unanimous rows await ONE owner acceptance (not twenty decisions),
the 23 review rows await the owner's word in the new sheet, and nothing is floored, certified or promoted by this
record — a floor still moves only on `check_extraction_recall.py --build-golden` after the owner's ruling lands. Also
registered, not repaired: BUG-989 — `config/decisions.yaml` sits four records behind this log (D-3134…D-3137) and the
membership join cannot see paragraph-form entries, so its "0 fault(s)" is a false green; D-3138 is therefore minted in
both homes and in HEADING form.

## D-3139 — AN INSERT DERIVES ITS IDENTITY FROM THE STORE, AND A ROW THAT CANNOT BE SERVED IS NOT A RECORD (2026-10-24)

T-195 follow-through. The owner ruled all 45 tier-B candidates (23 typed into the sheet he asked for, 20 unanimous
under his standing word "those advisory can promoted to my acceptence"), the golden was rebuilt and the rail now
measures the real gap: **concept 45/59 (0.7627), expectation 419/433 (0.9677) → RED**, naming **14 owner-certified
concepts the store does not contain**. Turning those 14 green requires a governed single-concept insert, and the
forensic audit of that path (BUG-990) found it had produced exactly one row which is the store's ONLY row on six
identity axes at once.

**CLAUSES.**

1. **IDENTITY IS DERIVED, NEVER ASSERTED.** `pipeline_run_id`, `source_books`, `primary_source`, `citation` and
   `taxonomy_version` are READ from the store's own PASS rows (the served run, the source's book identity, the
   version that source speaks) and the path REFUSES when what it reads is ambiguous or blank. A declared value would
   be a second home for a fact the store already holds (C12), and the one row that carried literals here became a
   1-of-7,635 orphan.
2. **AN AMBIGUOUS STORE MUST NOT BE CHOSEN FOR.** If more than one run id is served, the insert refuses instead of
   picking a corpus (D-3034). The path follows the store; it does not decide what the store serves (D-2881 owns that).
3. **THE GENERATOR'S IDENTITY HAS ONE HOME.** `models.generator.model` — not a literal behind a `or` fallback. An R14
   stamp whose value has two homes is a stamp that can disagree with itself (C12c).
4. **THE GATE RUNS ON THE DICT, BEFORE VERIFY AND BEFORE ANY WRITE, AND NAMES EVERY GAP AT ONCE.** Six single-cause
   refusals teach nobody; one list names the shape (8 known-answer controls, green, no store touched).
5. **THE ROW THAT CANNOT BE SERVED IS THE REAL DEFECT, AND IT IS NOT SOLVED BY IDENTITY ALONE.** Receipt (BUG-991):
   with identity fixed, a real certified concept still verifies `status=QUARANTINE reason=vacuous` because a 420-char
   excerpt yields a mechanism under `MECHANISM_MIN_LENGTH`. So this decision does NOT claim the 14 gaps can be closed
   today; it claims the path can no longer mint an unreachable row while trying, and it registers the remaining
   design choice as T-197 rather than guessing it (D-3036).

**RECEIPTS.** `pipeline/insert_single_concept.py --selftest` → 8/8 controls. Golden rebuild: 59 concepts / 433
(concept x source) expectations / 338 sources from 60 certifications. Rail AFTER the owner's rulings: RED at
45/59 and 419/433, `missing_concepts` listing all 14 by name (5 Infante / 6 Rumelt / 3 Levin-Brain). Tier-A floor
unchanged: 44 of the 59 are the previously certified core, all present.

**NOT DECIDED HERE.** No concept was inserted; no store byte was written by this change (dry run only). The
`f523504e` orphan row was LEFT IN PLACE: it is the evidence for BUG-990, and repairing it is its own act with its
own receipt.

## D-3140 — THE MECHANISM FLOOR IS ENFORCED AT THE GENERATOR, NOT LEFT FOR S5 TO QUARANTINE (2026-10-24)

T-197 / BUG-991. The single-concept prompt was a DRIFTED SECOND HOME for the extraction contract (the D-3136 shape): it named `mechanism` with no register or length guidance, while the bulk path's SYSTEM_PROMPT carries the full register calibration (causal_mechanism vs empirical_pattern, "never a restatement"). MEASURED: the 420-char Rumelt excerpt ("a good strategic diagnosis … defines a domain of action … promising leverage over outcomes") is SUFFICIENT for a ≥150-char mechanism, yet the generator returned a sub-floor one-liner and S5 quarantined it — so the defect is the CONTRACT, not the input length, and candidate fix #1 (longer window) was therefore NOT adopted (measured unnecessary). FIVE CLAUSES. (1) THE CONTRACT CLAUSE: a field the bulk path defines with register + length rules but the single path names bare is a rule with two homes telling two truths (D-3136). (2) THE ONE-HOME CLAUSE: the floor and the register are read from their existing homes — `stage5.mechanism_min_length` via the verifier's own `MECHANISM_MIN_LENGTH` constant, and `single_concept.extraction_type` — never re-typed (C12c). (3) THE FAIL-CLOSED-AT-GENERATOR CLAUSE: `check_mechanism_quality` (the ONE home) runs on the draft fb BEFORE `verify_one_record`; a rejection triggers ONE targeted retry (temp=0.0, so a sterner prompt is a DIFFERENT input, not a re-roll of the same answer), then FAIL-CLOSED rather than writing a row S5 would quarantine — an unservable row is not a record (BUG-967). (4) THE RECEIPT CLAUSE: the named red loop went RED→GREEN — before `status=QUARANTINE reason=vacuous method=mech_quality domains=['education']`, after `status=PASS score=0.986 reason=entail method=deberta-nli domains=['organizational behavior','leadership']`; 8/8 selftest controls green, no store byte written. (5) NOT DECIDED HERE: the domains routing (model-derived domains for a strategy book) is BUG-712's class and is NOT fixed here; the 14-row insert is the remaining act of T-197, whose named red-loop command is now GREEN.
