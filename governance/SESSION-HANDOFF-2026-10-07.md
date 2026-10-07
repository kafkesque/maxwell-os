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
