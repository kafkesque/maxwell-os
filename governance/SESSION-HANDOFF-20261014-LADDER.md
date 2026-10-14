# SESSION HANDOFF — 2026-10-14 (T-124 limb b, first pass: "the ladder's verdict")

> **Follows:** `governance/SESSION-HANDOFF-20261014-D2995.md` (D-2995 / BUG-776 — the retired scalar).
> **This session:** pre-commit forensic audit of the RED ladder, two rails discharged, one MIS-DIAGNOSIS corrected,
> and an intake assessment of eight external sources. **Store writes: ZERO.** **Decisions minted: ZERO** (nothing here
> needed one; the next act does — see NEXT).

---

## WHAT LANDED (all measured, nothing asserted)

| # | change | file | before → after |
| --- | --- | --- | --- |
| 1 | the archive rail's own remedy, run | `archive/index.yaml` (re-derived) | `build_archive_index --check` rc 1 → **0**; `superseded_runs` INDEXED (44 entries), nothing hand-excluded |
| 2 | the last silent byte-launder in the anchor rail DELEGATED to the ONE decode home | `scripts/verify_anchor_family_registry.py::read_jsonl` | `path.open(encoding="utf-8", errors="replace")` → `artifact_encoding.open_artifact(path, REPO)` (fails CLOSED on non-UTF-8 — the artifact is valid UTF-8, so no behaviour change) |
| 3 | three entries whose debt was PAID in code were deleted instead of reported STALE forever, and the SHRINK-ONLY ceiling lowered to its measurement | `config/silent_repair.yaml` | ceiling 17 → **14**; 25 sites found / 25 declared / 0 undeclared / 0 stale; the ladder LINE returns **0** (rail rc 2 = declared debt only) |
| 4 | BUG-766 extended: the blast radius is DOUBLE what it recorded, and the register is BLIND to four more columns | `governance/buglog.md` (BUG-766 MEASURED UPDATE) | 6 → **12** fatal POPULATION-SHAPE lines; +4 columns carrying the same hollow blank with NO `outside:` key; all 1,049 rows are `QUARANTINE`/`verification_results='[]'` (the same rows T-122 owns) |
| 5 | BUG-778's causal verdict for `check_store_columns` CORRECTED | `governance/buglog.md` (BUG-778 table + STATUS) | the census moves are OWED and non-fatal; the rc=1 cause is BUG-766 defect 1, which `--record` cannot fix. The discharge table records what went green |
| 6 | tasks: T-114 retitled/updated, T-124 limb (b) discharge recorded, **T-125 opened** (BUG-766's reshape + the blind declarations) | `config/task_register.yaml` | open tasks 19 → **20** |
| 7 | the harness axis gets a standing feed | `feed.opml` | `topics/e2e-testing` + `topics/end-to-end-testing` added under the GitHub topic group |
| 8 | the external-methods assessment | `governance/INTAKE_ASSESSMENT_20261014.md` (NEW) | 8 sources, an adoption matrix by Maxwell part, the `Jev`/`Laya` identification, and the debug/speed analysis |
| 9 | gov faces re-derived | `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`, `agent/session_seed.yaml`, `governance/bug_status.{json,md}`, `governance/buglog.md` | `gov_sync.py --apply` → 4 faces equal their re-derivation; **1,123 decisions / 542 bugs (194 open) / 20 open tasks** |
| 10 | **BUG-779 found + FIXED in the same act**: the served `ORDER BY` carried a literal `0.5` where the same file reads the declared `NEUTRAL_PRIOR` — TWO homes for ONE policy value on the RANKED path | `pipeline/retrieve.py::_rank_sql` + `specs/retrieval_serving.spec.md` INV-3 | one line; the rendered SQL is **byte-identical** (the declared value IS 0.5), so the repair cannot move behaviour — proven by rebuilding the pre-fix string and comparing, not asserted |

## THE FINDING THAT MATTERS MORE THAN THE FIXES

`python3 scripts/run_ladder.py --receipt-check` → **rc 2 (UNKNOWN)**: *"the WHOLE-SET fault set of `just health` is
UNKNOWN: the ladder CHANGED since the recorded scan (128 -> 138 declaring line(s))"*. **The masking BUG-778 describes
is not a missing feature — it is an UNCOLLECTED receipt.** D-2983's whole-set measurement exists, is honest, and was
last collected 754 s over a ladder that no longer exists; so `--banner` declares UNKNOWN at the top of every
`just health`, and the recipe walks into a prefix anyway. The cheapest high-leverage act in the programme is therefore
**re-collection**, not new code: ~12 minutes, after which every run opens with the measured fault count.

**And one correction of my own record:** BUG-778 said `check_store_columns` owed `--record`. It does not. Verified by
reading the rail's own fault classification (`fatal_faults()` excludes census moves) and by re-measuring the store:
the rc=1 cause is 12 FATAL population-shape drifts owned by BUG-766. A register that names the wrong remedy is more
expensive than one that names none.

## RAIL STATE AT HANDOFF (measured individually, never as a prefix)

| rail | rc | status |
| --- | --- | --- |
| `build_archive_index.py --check` | 0 | **green** |
| `check_silent_repair.py --check` (the ladder LINE) | 0 | **green** (rail rc 2 = 14 declared sites, ceiling == measurement) |
| `check_store_columns.py --check` | 1 | **red — BUG-766** (12 fatal shape drifts; a store reshape, T-125) |
| `check_undeclared_encoding.py --check` | 1 | **red — T-114 (1)** (files 161/156, sites 405/392, writes 75/74, unresolvable 4/3; the debt is GROWING — 159/396 on 2026-10-11) |
| `build_anchor_store_bridge.py --check` | 1 | **red — BUG-777**, OWNER-GATED (T-124 limb a) |
| `check_rail_mutations.py` | 1 | **red — harness** (T-124 limb c: it reads a declared tri-state baseline as "not green") |
| the other 62 rails below the bridge | 0 | measured individually in BUG-778's triage |

## NEXT (strategically ordered, each with its gate)

1. **Collect the ladder receipt** (`python3 scripts/run_ladder.py --collect health`) and let the banner carry it. No
   code, no policy. *Done when:* `--receipt-check` reports a coverage that equals the ladder's.
2. **T-124 limb (a) — the owner's ruling** (D-2898): when an anchor row's name resolves to N corpus rows, is it
   DECLARED unresolved or RESOLVED by a rule? Recommendation on file: **declare-unresolved** (an agent may not pick a
   winner). Deliverable that makes it one pass: `governance/ANCHOR_STORE_BRIDGE_CANDIDATES_<date>.csv`
   (row id | name | N | the candidate fb_ids | one decision cell). Infrastructure: `config/anchor_family.yaml#store_bridge`,
   `scripts/build_anchor_store_bridge.py`, `governance/ANCHOR_STORE_BRIDGE_20260926.json`.
3. **T-124 limb (c)** — teach `check_rail_mutations` the tri-state it already declares (an explicit, DECLARED
   `baseline_rc` per mutation, fail-closed when absent), then T-122, T-125, T-114(1), T-123.
4. **The intake's cheapest MUSTs** (`governance/INTAKE_ASSESSMENT_20261014.md` §2): a majority baseline + human
   ceiling for the saturated T-101 ruler; the shard+falsifier hunt as a program; the typed-decision pilot on the S4
   role against the frozen ARM-2 benchmark.

## WHAT WAS *NOT* DONE (declared)
No decision was minted; no store was written; the bridge was NOT re-baselined (owner-gated); the four rail
corrections that need a policy/harness change were NOT forced; and three of four videos were NOT transcribed (429).
The `mattpocock/skills` per-document digest failed on a decode error — intake §8 declares it, and no "SHOULD" row for
that repo should be acted on before the digest is re-run.
