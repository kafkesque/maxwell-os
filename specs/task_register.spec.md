# SPEC — The Task Register, its AXES and its face contract (P0)

spec_version: 1
governed: config/task_register.yaml (the register) · scripts/gov_sync.py#task_faults (its schema, fail-closed, C16) · scripts/gov_sync.py#severity_census (the one population for OPEN-ness) · scripts/gov_sync.py#render_block + #render_seed_status (the face contract) · config/gov_sync.yaml (the declared axes, the owner-lane label, the ceiling) · MASTER-TASK-REGISTER.md + DECISION-LOG.md + governance/buglog.md + agent/session_seed.yaml (the faces) · config/rail_mutations.yaml (the rules' mutation locks)
authority: D-2985 (this rule) · D-2981 (the faces are DERIVED from this register) · D-2642 (one derived value, one home) · D-2660 (a citation is a claim at the MOMENT OF MINT) · BUG-588/D-2692 (a count restated in prose is stale) · D-2644 (a ceiling may only be LOWERED) · BUG-757 (the severity gap) · BUG-762/BUG-763 (measured: the face led with work nobody could move, and one count had three answers) · C12 (no undeclared value) · C16 (fail closed) · D-2676 (mutation-locked)
stamp: 2026-10-13 · deterministic authoring (no LLM gen)
status: each invariant is live-verified by tests/test_task_register_spec.py

## Purpose

Definition of correct for the register the faces are DERIVED from, and for the two questions the owner asks of
it: **what is open** and **who must move it**. MEASURED 2026-10-13 (BUG-762): one word covered three different
situations. `R-1` was a STANDING RULE that can never close; `T-101` and `T-103` were gated on an owner word the
pipeline cannot supply; `T-104` was the only actionable MUST. All four were registered `state: open`, sorted by
priority alone, and printed at the top of every face - so the owner read three obligations he had already handed
over, the agent read a gate it could never pass, and the actionable work never appeared at all. The census even
said `gate 1` while three entries named an owner gate. The register had a priority axis and no MOVER axis.

Lifecycle (owner-approved, D-2978): this file is OVERWRITTEN IN PLACE when the contract changes — never
appended, never a new file per change. History lives in git plus the D-number that changed it.

## Invariants

### INV-1 — A standing RULE is not a task
- **Correct:** an `R-<n>` id carries `state: rule` — in effect, never closes — and is rendered in its own
  STANDING RULES section. The register-truth line counts open TASKS separately from rules.
- **Wrong:** `R-1` registered `state: open`, which sorted it FIRST in the MUST list in every face, forever:
  a rule cannot be closed, so a rule registered as a task is a row that can never leave the top. That is what
  the owner was looking at when he said the fixed items were still on top.
- **Test:** `test_a_standing_rule_is_not_a_task`.

### INV-2 — Every entry declares WHO must move it
- **Correct:** `mover: owner | pipeline`, REQUIRED on every entry, one of the movers declared in
  config/gov_sync.yaml. There is no default: C12 forbids a code-side default for a declared value, and an
  inferred mover would be a guess about the owner's intent.
- **Wrong:** no mover at all — the state of the register before D-2985, where a face could not distinguish an
  obligation of the OWNER from work the pipeline would do next, which is the distinction the owner actually
  needs to act.
- **Test:** `test_every_entry_declares_who_must_move_it`.

### INV-3 — An owner gate is a MOVER, never a state
- **Correct:** `state: gate` is RETIRED. Gatehood is `mover: owner` plus a `gate` that names the OWNER's word;
  a task the pipeline can still advance is `mover: pipeline` with `gate: none`, or with a rail-shaped
  dependency named in `gate`.
- **Wrong:** `mover: owner` with `gate: none` (gated on a person who is never told what to decide), or
  `mover: pipeline` with a gate that names the owner (the two fields disagree). MEASURED: `T-101` was
  `state: open` while its own gate read "owner-signed anchors for the new queries", so the census reported
  `gate 1` for three gated entries. Both directions FAIL CLOSED (C16).
- **Test:** `test_an_owner_gate_is_a_mover_never_a_state`.

### INV-4 — A count a register owns has ONE home
- **Correct:** `title` and `why` state the WORK; a measurement lives in `evidence`, with the date it was taken
  (D-2660). The census the faces derive from is the one home for every count of register objects.
- **Wrong:** a count restated in the printed line. MEASURED: `T-104`'s title said "108 of 185 open bugs" while
  the block's own census line said 125 and the joined truth was 101; `T-103`'s title said "457 rows"; `T-108`'s
  `why` quoted a served-run row count. A count restated in prose is stale the moment it is written (BUG-588/
  D-2692), and a face that contradicts itself three lines apart cannot be read at all.
- **Test:** `test_a_count_a_register_owns_has_one_home`.

### INV-5 — OPEN-ness is the census's, and the severity line PARTITIONS the open count
- **Correct:** the population is the ids `governance/bug_status.json` calls OPEN (one home, D-2642); the
  severity is read from each id's FIRST heading at ANY hash depth. The parts therefore SUM to the open count,
  which is what makes the line checkable. The shrink-only ceiling is a FLOOR-guard that may only be LOWERED
  (D-2644) and is re-measured when the population changes.
- **Wrong:** re-deriving OPEN-ness from a heading's state token, and reading only `^## ` headings. MEASURED
  2026-10-13: the parts summed to 255 for a population of 185 — 88 bugs the register calls CLOSED were counted
  open, and 18 open ids written with three hashes were invisible (the BUG-426/427 class, recorded in the buglog
  and never propagated to this reader). The ceiling came down 125 -> 101.
- **Test:** `test_open_ness_is_the_census_s_and_the_severity_line_partitions_it`.

### INV-6 — The rule is mutation-locked and its controls RUN
- **Correct:** config/rail_mutations.yaml carries an entry for the mover axis and for the census re-cut's
  scope, both expected RED, and the ladder runs `scripts/gov_sync.py --selftest` before the check, so every
  control is SEEN to fire (D-2676 iv). A register that breaks the schema FAILS CLOSED (rc 2, not a quiet
  rewrite).
- **Wrong:** a rule whose oracle is never run, or a declared `find` text that no longer matches the bytes — a
  declaration that drifted from reality is FATAL, never a quiet pass.
- **Test:** `test_the_rule_is_mutation_locked_and_its_controls_run`.
