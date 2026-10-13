# SESSION HANDOFF — 2026-10-13 · D-2983 (the ladder's verdict is a MEASUREMENT) + BUG-759 CLOSED

## The leverage call (why this act, this order)

The previous session ended with BUG-759 open: `just health-full` had run the whole ladder for the first time and
found SEVEN red lines, every one of them already red at the parent commit. The highest-leverage item was therefore
not any one of those five remaining reds — it was the fact that a red line can hide, for longer than it has been
measured, behind a report that everybody reads as a verdict. The ladder is the instrument through which every other
measurement in this repository is certified: if it can be quietly wrong, then so is everything it certifies. So this
session fixed the INSTRUMENT first, and only then re-measured it — which is also why the four inherited faults were
NOT touched (they are T-114, and each one now has to be discharged on its own evidence, against a ladder whose
state can no longer hide).

## What landed (all in the ladder's ONE home, scripts/run_ladder.py)

| Rule | Where it lives | Seen to fire |
|---|---|---|
| a whole-set verdict is RECORDED with its coverage and age | `--collect` writes temp/ladder_receipt.json (path/recipe/budget DECLARED in config/rail_registry.yaml#ladder_receipt; C12: no key defaulted in code) | selftest controls; the live receipt below |
| a recorded red may not go quiet | `receipt_verdict` -> rc=1, faults NAMED | `a_recorded_ladder_red_is_not_silently_green`; mutation `a_recorded_ladder_red_is_load_bearing` |
| UNKNOWN is loud, owner-owed, never fatal | rc=2 + the DERIVED remedy | `a_never_measured_ladder_is_UNKNOWN`, `a_stale_record_is_UNKNOWN_by_age` |
| a different ladder is not evidence | coverage fingerprint (D-2982 one level up) | `a_changed_ladder_invalidates_its_receipt` |
| the remedy is DERIVED, and its absence is a fault | `whole_set_entry` / `remedy_for` read the ladder's bytes | `the_whole_set_entry_point_is_DERIVED_from_the_ladder`, `a_longer_recipe_name_is_not_the_entry_for_a_shorter_one` |
| ORDER: read FIRST, enforce LAST | justfile#health (banner first; `--receipt-check` last, guard PINNED tri_state) | `test_the_order_is_load_bearing` |
| the record never dirties the tree it measures | gitignored runtime state, same disposition as check_tests.py's temp/tests_rail_last_run.json | `git status` unchanged by a full scan; `test_the_record_home_is_declared_and_never_committed` |

## The measurement of record (the first run of the new path, head 673a457)

`just health-full`: 128 declaring lines, 754.0s, worst rc=1, FIVE faults, coverage **10f4df05acc8ecec**,
measured_at 2026-10-13T16:33:36Z.
1. build_anchor_store_bridge.py --check (1.7s) — the committed bridge no longer re-derives (T-114)
2. check_silent_repair.py (1.4s) — one pre-existing unknown, BELOW its inherited baseline of 4 (T-114 residual)
3. check_undeclared_encoding.py (1.4s) — over its SHRINK-ONLY ceilings (T-114)
4. check_store_columns.py (16.9s) — CODE-CENSUS-MOVED, owner-owed `--record` (T-114)
5. build_archive_index.py --check (0.1s) — archive/superseded_runs in neither the index nor the exclusions (T-114)

They are no longer invisible: `just health` now prints "a red is RECORDED for `just health` under exactly this
coverage: 5 fault(s) measured 0.1h ago …" in its FIRST two lines, and the recipe's last line exits 1 for as long as
that record stands.

## Verification (all rc=0 unless stated)

run_ladder --selftest **24/24** · tests/test_ladder_receipt_spec.py **10/10** (D-2978 pairing enforced by the
contract itself) · check_rail_registry rc=0 (129 invocations, 9 declared writers, every remedy proven) ·
check_rail_mutations **32 declared rules SEEN to red**, 1 negative control green · ruff clean on both files ·
pre-commit hook green on the 8-path implementation commit (673a457) · gov_sync --check, check_governance_faces,
check_buglog_coverage, bug_status --selftest, check_declaration_consumers, recompute_decision_summary --check: all
rc=0 · R5 APPROVE on scripts/run_ladder.py (deterministic layers PASS + ONE advisory reviewer, gemma-4-E4B-it-MLX-4bit,
verdict READ not assumed; its two concerns — code density and POSIX/env dependence — were acknowledged, not argued).

## Governance sync (the agreed clean structural order)

D-2983 minted (total **1111**, stamp 5b6ff21b86ee09a7); BUG-759 CLOSED by an APPENDED update that names the
residual and routes it (the buglog stays append-only, so its prefix receipt holds); governance/bug_status.json
re-derived (OPEN **184** / CLOSED **339** of 523); config/task_register.yaml T-114 evidence re-measured with the
re-measure discipline stated; the four faces re-derived by scripts/gov_sync.py --apply (1111 decisions / 523 bugs /
14 open tasks), so no face restates a count that a register does not hold.

## Honest limits (stated, not buried)

1. The ENFORCED half of the rule is reached only when every earlier line is green. That is the intended case (a
   session that might otherwise believe the ladder is green), and the banner carries the record for the rest.
2. The record is LOCAL: it says what THIS clone measured; a fresh clone reports UNKNOWN rather than inheriting a
   claim.
3. The 72h age budget is a DECLARED judgement, not a measurement — it is owner-tunable in ONE place, and it exists
   so that "we measured it once" cannot become a permanent licence.
4. A full scan still costs ~12.5 minutes, which is exactly why UNKNOWN is owner-owed and loud rather than fatal:
   the fix is not to run it more often, it is to never lose what it found.
5. The fault list in a banner is long (each fault is the line AS WRITTEN, comments included). Readable, and honest
   to the bytes — flag it if the owner wants it trimmed to the command.

## Delegation status (honest)

No ad-hoc delegate was used in this session: the work was a single-file contract (scripts/run_ladder.py + its
declaration, spec and contract), and splitting it would have created two writers of one rule. The ONE local-LLM call
was the ratified R5 reviewer through scripts/r5_review_gate.py, and its verdict was read in-line (APPROVE) rather
than assumed — the failure mode recorded on 2026-10-13 was a delegate whose result could not be recovered, and a
task result that cannot be read is not a measurement.

## Next critical step

**T-114 (SHOULD) — discharge the five recorded faults** (the four inherited ones above plus the silent_repair
residual), each with its own evidence, each SHRINK-ONLY ceiling LOWERED rather than raised (D-2644), and each wave
followed by a re-measure so the record matches the repaired ladder. Then **T-113** (pay the 71 keys the census
instrument revealed, in module-sized waves) and **T-101** (harden the retrieval golden set — MRR 0.919 gates the
next retrieval change; owner-signed anchors, so a HUMAN GATE).
