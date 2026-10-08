## CURRENT STATE (2026-10-07, post-BUG-665-rails-1+2 — SUPERSEDES all below for resume)

- HEAD was f629b7f. This turn fixed BUG-665 rails 1+2 at ROOT CAUSE (D-2646/D-2644/C16/C12), never by ceiling/allow.
  * check_encoding_homes CLEAN: build_anchor_bridge_ruler_208.py write now sources `cfg["ruler_encoding"]` (C12);
    check_anchor_axis_consistency.py CSV read delegates to artifact_encoding.open_artifact (D-2646).
  * check_silent_repair OWED (2): removed errors="replace" in detect_same_work_content.py:142; converted
    pipeline/enhance_md_headers.py `lines:[182,248]` -> `match:` (BUG-542 stale coordinate).
- BUG-665 STILL OPEN (rail 3): undeclared-encoding census 161/156 (411/392, 82/74) — 5 new D-2811 files. Root-cause
  fix = REPAIR those files; a ceiling re-baseline is an OWNER-RATIFIED DECISION (D-2642 shrink-only). OWNER-GATE.
- Register **432 = 162 open / 270 closed**, highest OPEN **BUG-665** (rail 3 remainder).
- FINDING (pre-existing, NOT this turn): build_anchor_bridge_ruler_208.py --apply fails-closed on 3 ambiguous folded
  extras (R152/R192/R197 match 2 corpus rows) — owner data adjudication, not encoding.
- NEXT (priority): BUG-665 rail 3 (repair 5 files / owner re-baseline), BUG-631 (52 over-cap FBs, D-2838 writer-limb),
  D-2853 close-out (28-row referee remap + closed-menu v5->v7 + D-2859), D-2858 (or-entail recalibration).
- OWNER-GATE (do NOT cross unilaterally): referee = governance/discipline_anchor_rederived_v6_20261006d.json + 28-row remap.

## CURRENT STATE (2026-10-07, post-BUG-667-fix — SUPERSEDES all below for resume)

- HEAD was 6d08336. This turn landed the BUG-667 re-mint (authority marker) + D-2862 RATIFIED (owner-approved re-mint).
- BUG-667 FIXED (root cause): a STALE authority pin (D-382/BUG-535 class). The t11 `checkpoint_enriched.jsonl`
  sha256 pin (0ca6f0f0…) was minted before the post-S5 rewrite (C-3/BUG-376 acknowledged move) and never re-minted
  after — the marker outlived its subject (BUG-542 family). Fix: re-minted the pin to the on-disk bytes
  (3854250c…; byte size unchanged 96902142, mtime 2026-10-03T01:16) under D-2862 — a DECISION, never a quiet
  re-hash (D-382/BUG-535). verify_artifact_authority now exits 0 (2 markers, 17 files, 0 RED). The marker itself is
  gitignored (data artifact); the re-mint decision D-2862 is committed in DECISION-LOG.md + config/decisions.yaml.
- Register **432 = 162 open / 270 closed**, highest OPEN **BUG-665**. Decisions 992 (D-2862 = last).
- STILL OPEN (priority order): BUG-665 (encoding repoint to artifact_encoding.py), BUG-631 (52 over-cap FBs via
  D-2838 writer-limb), D-2853 close-out (28-row referee remap + closed-menu v5->v7 + D-2859 off-by-one).
- OWNER-GATE (do NOT cross unilaterally): referee = governance/discipline_anchor_rederived_v6_20261006d.json + 28-row remap.

# SESSION HANDOFF — 2026-10-07 (continuation: forensic audit + register-divergence reconciliation)

> **Resume:** say `continue` — this file + `governance/CONTEXT_INDEX.md` are the entry points.
> The previous handoff (D-2860 commit-frontier gate) is SUPERSEDED by this one for state and next-steps.

## CURRENT STATE (2026-10-07, post-BUG-666-fix — SUPERSEDES all below for resume)

- HEAD **0272192**. This turn landed: 92dedbb (BUG-666 fix + drift detector), 38bee18 (BUG-666 gov sync),
  930d700 (mutation journal), 0272192 (D-2860 header RATIFIED). Tree clean.
- BUG-666 FIXED (root cause): NOT a toothless boundary — a DRIFTED DECLARATION. config/boundary_rehearsal.yaml's
  planted `will_not_touch` scenario still named `pipeline/stage5_verify.py` (a family D-2801 moved OUT of
  will_not_touch into may_touch). RAIL 4 HAS teeth (25/25 selftest fires "a will_not_touch path is FORBIDDEN");
  the rehearsal was asserting a refusal RAIL 4 no longer owed, so the planted violation LANDED rc=0. BUG-542 class
  (declaration outliving its subject) + D-2646 (family restated in a 2nd home). Fix: repoint subject to LIVE
  immutable family `governance/F11_ANCHOR_REVIEW_20260923.csv` + fail-closed `planted_will_not_touch_drift`
  detector consuming `session_plan` (the plan's ONE home). Rehearsal GREEN (2 violations REFUSED), 23/23 controls.
- D-2860 header FIXED: DECISION-LOG.md ACTIVE -> RATIFIED to match config/decisions.yaml state.
- Register **432 = 163 open / 269 closed**, highest OPEN **BUG-667**. Decisions 991.
- STILL OPEN (priority order): BUG-667 (t11 re-mint via D-2862), BUG-665 (encoding repoint to artifact_encoding.py),
  BUG-631 (52 over-cap FBs via D-2838 writer-limb), D-2853 close-out (28-row referee remap + closed-menu v5->v7 +
  D-2859 off-by-one).

## CURRENT STATE (2026-10-07, post-BUG-659-fix — SUPERSEDES all below for resume)

- HEAD **97a9fb2**. Three commits landed this turn: 403fb63 (BUG-663 + D-2853 fan-out + gov deps),
  2b7958c (BUG-659 by_rail dead-code fix + revert premature D-2853 anchor token_fix fan-out), 97a9fb2 (gov deps).
- BUG-659 FIXED (root cause): check_config_defaults `by_rail` read `measured_by` from `config_reads` but
  record_ceiling wrote it INSIDE `ceilings` (block-mapping) -> by_rail always False -> shrink-only fail-closed
  guard was dead -> ceiling silently auto-raised 221->229/2->3. Fix reads both locations; VERIFIED exit 1 + no
  write on growth. Deliberate owner-approved re-baseline 229/3 kept; 9 new keys flagged for declaration review.
- DRIFT REVERTED: anchor_workbook_fixes token_fix 'research & methodolog' -> 'research & methodology' (v5 menu
  name). The anchor workbook validates against closed_menu_v5.json (still v5), NOT the v7 taxonomy. The prior
  segment's premature v7 fan-out of this ONE token_fix broke validate_depth_domain_contract (3 RAW_REDERIVE_
  MISMATCH). Reverted; contract GREEN (hard:0 owner_blocked:0).
- Register **432 = 165 open / 267 closed**, highest OPEN **BUG-667**. Decisions 991.
- STILL OWNER-GATED (approved this turn, NOT yet implemented): BUG-660 (health read-only / --check modes),
  BUG-665 (encoding repoint), BUG-666 (write-boundary teeth), BUG-667 (t11 re-mint via D-2862),
  BUG-631 (52 over-cap FBs via D-2838), D-2853 close-out (28-row referee remap + closed-menu v5->v7 migration,
  D-2859 off-by-one).
- D-2860 header in DECISION-LOG still reads ACTIVE while config/decisions.yaml is RATIFIED (sync drift).

## CURRENT STATE (2026-10-07, post-BUG-663-fix — SUPERSEDES sections below for resume)

- git HEAD **d3f372f**. Working tree carries the BUG-663 + D-2853 fan-out fix (uncommitted): alias_map, synonym_map,
  taxonomy v5/v7 dom-010 raw alias, pipeline/schemas.py fallthrough, pipeline_config same_axis_fallthrough,
  golden .golden_meta.json re-stamp, 2 test files, plus this sitting's governance sync + fan-out completion
  (domain_disciplines, anchor_workbook_fixes, eval_integrity, buglog, bug_status, session_seed, DECISION-LOG, MTR).
- 4 fatal rails landed in d3f372f (BUG-661/662/664/668). BUG-663 (6 test regressions) now FIXED this sitting — NOT
  ceiling-absorbed (D-2656): root cause = incomplete D-2853 v7-rename fan-out + D-2814 same-axis homonym. 45/45 pass.
- D-2853 fan-out COMPLETE over live config maps: alias_map(16), synonym_map(1), domain_disciplines(1 key),
  anchor_workbook_fixes(1), eval_integrity known_collisions entry removed. Remaining drift = 28-row A/B referee
  domain remap (OWNER-GATED) + frozen menus (v5/v6 intentional) + schemas docstrings (historical).
- Bug register **432** = **166 open / 266 closed**; highest OPEN = **BUG-667**. Decisions **991** (D-2861 = last).
- MUTATION_JOURNAL.jsonl carries 2 append-only no-op regenerate rows (BUG-660 class): COMMIT them, do NOT revert.

## HEADLINE (the audit answer, 2nd pass)

Commit **98471a3** (D-2861) re-baselined only 3 rails and declared victory without a full ladder run. A full
`run_ladder.py --collect health` this sitting is **RED with 11 fatal (rc=1) faults** + 256 measurement-drift cells.
Root cause: the ratified store change (rechunk-v4-20260929, fbs 7,995→14,574) was propagated to
`label_provenance` only, NOT to `store_columns`, the archive index, or the checkpoint authority. Do NOT build
Phase 2/3/4 on this red baseline — complete the re-baseline first.

## STATE VERIFIED (measured, not assumed)

- git HEAD **98471a3**. Working tree: `governance/METRICS.jsonl` (+3 metric records from verify_handoffs, uncommitted).
- Full ladder = **RED**: 11 fatal (rc=1) faults → BUG-661..668 filed this sitting (below). Owner-owed rc=2 unchanged.
- Bug register **432** (171 open / 261 closed; highest OPEN = BUG-668). Decisions **991** (D-2861 = last).

## THE 11 FATAL FAULTS (this sitting's finding — prior D-2861 missed all but one)

1. build_anchor_store_bridge --check prints "ok" but exits 1 (BUG-661 — verdict/exit mismatch).
2. check_store_columns 256 MEASUREMENT-DRIFT + menu_hash RESERVED-VIOLATION (BUG-662 — census not re-recorded).
3. check_tests 6 regressions (BUG-663).
4. check_domain_cardinality.py unwired (BUG-664 — rail registry + reconcile).
5. encoding debt above ceilings, 3 rails (BUG-665).
6. check_boundary_rehearsal no teeth (BUG-666).
7. verify_artifact_authority t11 checkpoint sha drift (BUG-667).
8. build_archive_index bloat_20260929 unindexed (BUG-668).
9-11. encoding-homes / silent-repair / undeclared-encoding (folded into BUG-665).

## WHAT LANDED THIS SITTING

**Reconciled `config/register_divergence.yaml` (BUG-571 shrink-only list):** removed 25 STALE pins
(BUG-099/148/151/159/160/168/169/182/222/223/224/228/229/230/231/232/234/235/236/237/238/241/242/243/267 —
all now carry a HEADER, so the pin was stale) and pinned the one NEW uncarried name
(BUG-429, first named `governance/buglog.md:8678`, no header). Ceiling `declared_max_uncarried` 63→39.
`check_register_divergence.py` now exits 0. This is STRUCTURAL (a verified fact about names-vs-headers),
not a status decision: BUG-429's actual open/closed state was **not** invented (D-2645 backfill rule).

## FORENSIC AUDIT — the 4 fatal drifts (and one meta-finding)

1. ✅ **register divergence** — FIXED this sitting (above).
2. ❌ **check-label-provenance** — boundary population CHANGED: 7983 rows belong to declared generation runs
   `[t11, bug198_reinject, e2e]` but `config/label_provenance.yaml#boundary.measured_rows` declares 7995
   (a 12-row delta). Store change OR deliberate re-baseline required (BUG-501/D-2638). **Decision + owner.**
3. ❌ **build_anchor_store_bridge** — committed bridge (`governance/ANCHOR_STORE_BRIDGE_20260926.json`) no
   longer re-derives (a join/name/input moved since D-2813/D-2812). **Re-derive or re-baseline — decision.**
4. ❌ **verify_handoffs** — `config/decisions.yaml` declared append_only but receipted bytes are not a prefix:
   first 911661 bytes hash `8eb0167cf8bf52f8` ≠ receipted `b2145053e96128b2` — a byte inside the receipted
   region was edited in place (BUG-376 class). Likely introduced in `65339ae` (D-2826..D-2859 "rename/promote"
   batch). **Re-baseline the receipt via the declared route — decision.**

**META-FINDING (hidden failure):** running `just health` / `run_ladder.py --collect` **dirties 4 tracked
files as a side effect** — `config/derivations.yaml` (check_config_defaults auto-raises the shadowed/undeclared
ceiling 221→229 / 2→3), `governance/RECONCILIATION.json`, `governance/METRICS.jsonl`, `governance/MUTATION_JOURNAL.jsonl`.
A "health check" is not read-only. These were reverted this sitting; the ceiling raise is itself owner-owed debt
(8 new shadowed + 1 new undeclared config key since 2026-10-03) and needs review, not a silent commit.

Owner-owed (rc=2, pre-existing, NOT addressed): ANCHOR-4 context drift (BUG-431 open, owner gate), workbook
rulings RED (R001 depth_final), write_guard 7/10 writers, config-default ceiling stale.

## NEXT CRITICAL STEPS (in consequence order)

- **D-2864 (mint): re-baseline the 3 red drifts** — (a) `label_provenance.yaml#boundary.measured_rows` 7995→7983
  after confirming the 12-row delta is a legitimate store change; (b) re-derive the anchor<->corpus bridge; (c)
  re-baseline the `decisions.yaml` append-only receipt (confirm the in-place edit was intentional, then re-baseline).
  These are STRUCTURAL re-baselines but each touches a receipted boundary → one decision each, owner-ratified.
- **BUG (open):** file BUG-659 for the `check_config_defaults` ceiling auto-RAISE (221→229 shadowed / 2→3
  undeclared) — shrink-only ceiling must not be silently raised by the check; flag the 9 new keys for review.
- **BUG (open):** file BUG-660 for the health-ladder write side effects (health must be read-only, or its writes
  declared + committed as part of the run).
- **BUG-429 header:** give BUG-429 a proper HEADER (real bug "UNRESOLVED contains RESOLVED", BUG-572 family) —
  requires knowing its true status → human/owner decision, then remove the pin.
- **OWNER-GATE (unchanged, do NOT cross unilaterally):** referee =
  `governance/discipline_anchor_rederived_v6_20261006d.json` + 28-row remap → finish D-2853.
- **D-2860 ratification:** flip ACTIVE→RATIFIED after owner reads.
- **Phase 2 [D-2861]:** canonical `config/bugs.yaml` + `config/tasks.yaml` (render MD as DERIVED, C13 backup first).
- **Phase 3 [D-2862]:** cross-entity invariants in `reconciliation.yaml` + 2-3 check kinds in `reconcile.py`.
- **Phase 4 [D-2863]:** enforce `decisions.yaml` shape via Pydantic/JSON Schema (C12).
- **Pipeline (D-2859):** menu 65/44 vs taxonomy 64/43 off-by-one; D-2857 split; D-2858 recalib+flip; new A/B.

## GOV DEPENDENCIES SYNCED THIS SITTING

`config/register_divergence.yaml` (BUG-571 list reconciled) · this handoff. No decision minted, so
`decisions.yaml` / `decisions_summary.json` / `DECISION-LOG.md` / census unchanged (990).


## 2026-10-08 ADDENDUM — D-2878 owner review ROUND 2 (supersedes the register figures above)

Register (derived, never hand-typed): **1008 decisions · 444 bugs (163 open / 281 closed; highest OPEN = BUG-680)**.

C15 (5+ unresolved -> carry them in every handoff): this handoff carries **163 unresolved ids** - the register is the only list of truth
(`scripts/bug_status.py`); do not restate counts anywhere else (BUG-588/D-2692).

WHAT LANDED THIS TURN (D-2878, RATIFIED): the owner's round-2 answers
(`governance/OWNER_CONFIRMATION_SHEET_20261008.csv`, sha256-pinned, asserted fail-closed) were folded into the frozen domain
ruler: (a) 8 owner-confirmed discipline abstentions now declare `discipline=""` - BUG-676 FIXED (an out-of-menu token may not stand
in a value slot; the guard now fires in BOTH directions); (b) R158 domain drop re-ranked BY APPLICABILITY (`editorial & advertising`,
`motion design` out; `graphic design` RE-INSTATED); (c) R005 - `engineering practice` cannot be primary with high conviction, primary
stays `data visualization`; (d) R113 - primary `engineering practice`, `computational science & physics` kept, `systems & frameworks`
excluded. Ruler re-stamped: 201 rows, 9 rows changed, 15 declared warnings, `--check` reproduces it byte-identically.

NEW OPEN DEFECTS: **BUG-679** - the owner-RATIFIED RATIFY-3 DROP(13) (D-2711/D-2719) reached only 5 of 13 anchor rows; 8 ratified
drops (R012 R026 R034 R082 R140 R180 R182 R200) are STILL live axis-bearing rows in the frozen ruler, contradicting D-2813
("for a noise_drop row depth and discipline do NOT apply"). OWNER GATE: propagate (201 -> 193) or supersede RATIFY-3.
**BUG-680** - the two upstream anchor faces still carry the out-of-menu token in the discipline slot (BUG-676 residual; fix belongs in
the consolidation chain, never a hand edit).

STILL OWNER-GATED (do not proceed without a written word): R040 and R091 dispositions (evidence + recommendations in
`governance/OWNER_RULINGS_ROUND2_20261008.md`); R140 (ratified drop vs round-2 abstain); whether to move R158's primary
(the agreed primary `design strategy` ranks low on intrinsic applicability); the DROP(13) propagation; and the RATIFY-2 full
S4 -> S5 -> S6 rerun (D-2727).

NEXT CONSEQUENTIAL WORK: BUG-679 propagation (one owner word), then D-2879 = the ANCHOR-2 authority-aligned sheet + key re-mint +
kappa re-measurement (BUG-677; mint ONLY after the run carries measured numbers), then BUG-680's consolidation-chain fix, then the
optional student domain_confidences provenance in `_maybe_student_override`.

---

## 2026-10-08 ADDENDUM 2 — D-2879 owner review ROUND 3 (the drop propagation + the axis TWO-HOME finding)

**C15 CARRIED FORWARD: 165 unresolved ids** (register re-derived: **1009 decisions · 447 bugs, 165 open / 282 closed;
highest OPEN = BUG-683**). Full open-id list: `governance/bug_status.json` (machine-derived from `governance/buglog.md`).

WHAT LANDED THIS TURN (D-2879, RATIFIED, stamp 72ff70db866a4bfd): the owner's round-3 words — `ok I accpet your
recommendations R40,R80,R91` / `R140 drop` / `BUG 679 those are noise drop` — implemented deterministically.

* **BUG-679 FIXED.** The owner-ratified RATIFY-3 DROP(13) now reaches **13/13** (+ R040) = **14 declared drops**; the
  owner-derived ruler is **194 rows** (201 − 8 residues + 1 reinstatement). The invariant that would have caught it is
  now a **RAIL**: `n_anchor_rows == n_ruler_rows + n_noise_drop` → **208 == 194 + 14**, asserted on every run, plus a
  guard that every declared drop must name a real anchor row AND carry a soft-quarantine ledger entry (it fired on its
  first run: R040 had no entry → recorded in `governance/frontier_audit/noise_drop_quarantine.json` BEFORE the re-stamp).
* **R091 REINSTATED by declaration** (`config#reinstated_rows`, data not code): domains [education, design strategy],
  primary education, discipline = **declared abstention** (upstream `creative education` is off the 64-menu; no
  synthesized label). **DECLARED DIVERGENCE:** the owner's sheet CELL said `noise drop`; the owner's later written word
  (accepting the KEEP recommendation) governs — recorded, not silently resolved.
* **BUG-676** rule unchanged, the SET changed: R140 left the abstention set (now a drop — an abstention for a dropped row
  is a category error, asserted fail-closed), R091 entered it.
* **BUG-682 OPENED (the real defect behind BUG-679): the axis had TWO homes, now MEASURED.** The owner's round-2/3 rulings
  exist only in the owner-sheet-derived ruler; the DECLARED authority `discipline_anchor_rederived_v8_20261007.json`
  still carries the pre-ruling values. Measured: **45 divergent + 23 drop-residue** cells there, **47 + 23** in
  `ANCHOR_208_CONSOLIDATED` → **92 / 46**. It stayed invisible because (i) the ladder's axis rail declared
  authority=rederived_v8 and consumer=CONSOLIDATED, which is **regenerated from** rederived_v8 — it compared an artifact
  with its own copy and **cannot fire**; (ii) `build_domain_ruler.py` was a **SECOND writer** of the ruler deriving from
  the stale face — a re-run would have SILENTLY REVERTED the owner's rulings (D-387 class); (iii) the D-2870 guard read a
  **hardcoded column key** (it would scan 0 rows and print green the day the authority's column changes).
  **FIXED this round:** the tri-state cross-face rail (`apply_owner_domain_review.py --check-faces`) is **in the ladder**
  with a measured SHRINK-ONLY ceiling (92/46); the rival writer is **retired** (it now refuses, rc=1); the guard's column
  comes from the declared authority.
* **`scripts/apply_owner_domain_review.py` became a LADDER RAIL** (`--selftest` 9 known-answer controls, `--check`,
  `--check-faces`). It had been named in DECISION-LOG.md for two rounds as the way to verify the ruler and was invoked by
  **NOTHING** — a rail nothing runs is a comment (D-2665/BUG-492). That is how BUG-679 survived two rounds.
* **BUG-683 OPENED:** `apply_owner_domain_rulings_v8.py` is a rival writer of the **authority** whose input contract no
  longer exists (it reads `config[...]["rows"]`, removed in the round-2 rewrite) → `KeyError` if run, and nothing runs it.
* **BUG-681 UPDATE:** `check_encoding_homes --check` is now rc=1 (a DRIFT, not the tolerated owner-owed rc=2), so
  `just health` **stops there** and everything below it is invisible in the prefix (BUG-573's failure mode). Offender
  diagnosed with a line number: `scripts/remap_referee_v7_28rows.py` **line 69** (a local `utf-8-sig` instead of the
  declared decode home `scripts/lib/artifact_encoding.py`).

**NEXT CRITICAL STEPS (strategic order):** (1) **BUG-682 Stage 2 = ONE projection**: ruler → rederived_v8
(discipline/domain/primary_domain; 14 dropped rows cleared on all three axes + stamped `noise_drop`; abstained rows stamped
`discipline:""` + `discipline_status: abstained`) → regenerate `ANCHOR_208_CONSOLIDATED` + the five-axis views → **flip the
axis registry** (the owner-derived ruler becomes the DOMAIN-axis authority) → ceilings to **0**. Closes BUG-682/680/683
together. (2) **BUG-681(b)**: delegate the remap CSV read to the declared decode home + declare that CSV's encoding
(unblocks the whole ladder prefix). (3) **BUG-677 / D-2880**: the ANCHOR-2 authority-aligned sheet + key re-mint + kappa
re-measurement (mint ONLY once the run carries measured numbers). (4) RATIFY-2 full S4→S5→S6 rerun remains the only
owner-gated RUNTIME action (D-2727).

**OWNER MICRO-GATES (nothing blocking; one word each):** (a) R091's discipline — name a canonical from the 64-menu or
confirm the abstention; (b) R158's primary — `design strategy` ranks 8/9 on intrinsic applicability, move it or keep it.

---

## 2026-10-08 ADDENDUM 3 — D-2880 owner review ROUND 4 (both micro-gates closed; the ladder prefix unblocked; the BUG-679 mechanism named)

**C15 CARRIED FORWARD: 166 unresolved ids** (register re-derived: **1010 decisions · 448 bugs, 166 open / 282 closed;
highest OPEN = BUG-684**). Machine-derived open-id list: `governance/bug_status.json`.

OWNER RULINGS IMPLEMENTED (D-2880, stamp c84d4b033f1be1bd): **R158 primary ratified FINAL** (`design strategy`;
nothing changed, recorded in the artifact's own `note` so it cannot be re-opened by inference). **R091 discipline =
`systems thinking`** (owner-approved on the senior recommendation; ontology: discipline = RIGID KIND, and
autopoiesis is Maturana & Varela's systems-theory construct — `complex adaptive systems` REJECTED because its own
menu definition is about systems that ADAPT AND EVOLVE, which autopoiesis deliberately is not; `cognitive science`
and `design thinking` rejected on the same definition-first test). R091 left `discipline_abstention` (7 rows
remain). A NEW GUARD now asserts the abstention declaration in BOTH directions. Ruler `d867ce5e…` -> `5ce242ed…`.

**THE `just health` PREFIX IS UNBLOCKED** (BUG-681 limb (b) CLOSED, and it was the highest-value fix available):
`scripts/remap_referee_v7_28rows.py:69` carried a second implementation of the decode rule; it now delegates to the
ONE home and the substitution was MEASURED inert (identical 28/28 rows). Before this, the ladder stopped there and
every rail below was invisible — the ladder's own observability is a control.

**BUG-684 FILED — the mechanism behind BUG-679, in code:** `scripts/regenerate_anchor_208_v8.py` carries the drop
set as PYTHON LITERALS (`NOISE_DROP = {R021,R084,R106,R148}`, `EMERGING = {R040,R080,R091}`) and re-populates the
PIPELINE-FACING face from the stale authority for every row they do not name. Two homes, one fact: that is why the
owner's ratified drop could never reach the face that matters.

**NEXT CRITICAL STEP (Stage 2, blast radius audited, no pin blocks it — 6 places):** (1) fix BUG-684 (config-driven
sets + project from the ruler); (2) project `discipline_anchor_rederived_v8_20261007.json`'s three axis columns
(drops cleared + stamped `noise_drop`; abstentions stamped `discipline:""` + `discipline_status: abstained`);
(3) update `config/anchor_family.yaml`'s cohort declarations (201 -> the projected set) and drop R140 from
`advisory_rows_accepted_20260930`; (4) clear depth for the 8 newly-dropped rows in the DEPTH authority (D-2813);
(5) regenerate the five-axis views; (6) flip the axis registries to the owner-derived ruler and lower
`ceiling_divergence`/`ceiling_drop_residue` to **0** — which closes BUG-680, BUG-682, BUG-683 and BUG-684 together.
Then: `check_tests` (3 pre-existing red contract tests) and `check_boundary_rehearsal` (a whole-tree commit is
refused for a reason OTHER than the declared marker — never hand-edit the declaration). RATIFY-2 full S4->S5->S6
rerun remains the only owner-gated RUNTIME action (D-2727).
