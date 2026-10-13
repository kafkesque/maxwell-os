# SPEC — Governance Faces, the CLAIM SURFACE of the register (P0)

spec_version: 1
governed: scripts/check_governance_faces.py (the rail: --selftest is its own oracle, the check is the ladder's line) · DECISION-LOG.md · MASTER-TASK-REGISTER.md · governance/buglog.md (the three faces' declared history regions) · config/decisions.yaml (the register a claim is joined to) · config/rail_mutations.yaml (the rule's mutation lock) · justfile#health (where the rail and its controls stand)
authority: D-2984 (this rule) · D-2981/R-1 (the faces are DERIVED, never hand-appended) · D-2642 (one derived value, one home) · D-2660 (a citation is a claim about the tree at the MOMENT OF MINT) · D-405 (a declaration whose subject is absent is an assertion) · BUG-588/D-2692 (a count restated in prose is stale) · BUG-669 (the predecessor: the rail read tables and marker lines, never prose) · BUG-760 (measured: the faces told the owner a closed decision was still pending) · BUG-492 (a detector nobody has seen fail is not a detector) · C16
stamp: 2026-10-13 · deterministic authoring (no LLM gen)
status: each invariant is live-verified by tests/test_governance_faces_spec.py

## Purpose

Definition of correct for what a governance FACE is allowed to CLAIM. Each face declares, with a
`<!-- GOV-HISTORY:START -->` marker, that everything below it is "DATED HISTORY: append-only, NOT a register".
MEASURED 2026-10-13 (BUG-760): that declaration was never enforced, so the region beside the derived block could
make live claims — and did. MASTER-TASK-REGISTER.md carried a second `CURRENT OPEN INDEX ... the live face` and a
restated census saying `highest OPEN = BUG-750` while the register's own answer was BUG-757; DECISION-LOG.md listed
`| D2622 | ACTIVE |` and `| D2621 | PROPOSED |` under a heading reading "OPEN / PENDING — highest priority first"
while config/decisions.yaml said RESOLVED; a row cited `D2537`, an id the register does not carry. The derived block
was right every time. The hand prose beside it was wrong every time, and the rail's four surfaces (bug-status table
rows, header census, live census, buglog tiers) read tables and marker lines — never prose, never a decision row.

The rule is one sentence: **a claim is either JOINED to the register, or it DECLARES THE MOMENT it speaks about
(D-2660).** There is no third state — an unmoored present-tense claim is the defect, whether it is true today or not,
because nothing can tell the difference later.

Lifecycle (owner-approved, D-2978): this file is OVERWRITTEN IN PLACE when the contract changes — never appended,
never a new file per change. History lives in git plus the D-number that changed it.

## Invariants

### INV-1 — A live-claim LABEL has one home, and it is the derived block
- **Correct:** the phrase that points at the current state (`CURRENT OPEN INDEX`, `the live face`) names exactly one
  place, the machine-derived block above the history marker. Two pointers are two homes (D-2642).
- **Wrong:** a line below the marker that LEADS with the label and calls itself the live index — which is how a
  snapshot of 2026-10-12 read as the register's present answer.
- **Boundary (measured):** the phrase also appears in PROSE THAT DISCUSSES the faces (buglog.md's BUG-669 entry).
  The label must lead the line; a rule that fires on a discussion of a pointer is not a rule about pointers.
- **Test:** `test_the_live_claim_label_has_one_home`.

### INV-2 — A LIVE census marker may not stand in a region declared "NOT a register"
- **Correct:** a census inside the declared history region names its moment and is a snapshot ("as measured then").
  The live census lives in the derived block, which the marker never contains.
- **Wrong:** a `Register truth: …` marker inside the region. It cannot be rescued by a date it does not carry,
  because the marker IS the live one by definition; a live claim inside history contradicts the declaration itself.
- **Test:** `test_the_live_census_marker_may_not_stand_in_history`.

### INV-3 — A decision ROW is a claim about the register
- **Correct:** `| D<id> | <state> | … |` agrees with config/decisions.yaml, or its SECTION declares its moment (the
  date on the nearest preceding heading, bounded by the marker so a live tier label above the region can never date
  a claim inside it) and it is history.
- **Wrong:** a row claiming ACTIVE for a decision the register holds RESOLVED, or citing an id the register does not
  carry (D-405: a citation whose subject is absent is an assertion).
- **Test:** `test_a_decision_row_joins_to_the_register`.

### INV-4 — A transition row is read by the state it ENDED in
- **Correct:** `| D2546 | PLANNED | RESOLVED | the ship |` is the same kebab as a three-column row whose claim is
  RESOLVED. One parser reads both, because the claim is the LAST cell that names a register state and nothing else.
- **Wrong:** a second parser for the four-column form, or a long prose cell that merely discusses "resolved" being
  read as a state claim.
- **Test:** `test_a_transition_row_is_read_by_its_last_state`.

### INV-5 — The highest-OPEN field is DERIVED and states its moment on its own line
- **Correct:** `highest OPEN then BUG-695` — a claim about a moment, which stays true while the register moves on.
- **Wrong:** `highest OPEN = BUG-750` in a hand line with no moment at all, while the register's own answer was
  BUG-757. The field has one home; an entry stamp one line above is not enough, because the VALUE is what moved.
- **Test:** `test_the_highest_open_field_states_its_moment`.

### INV-6 — A present-tense OPEN assertion about a bug joins, unless its entry names the moment
- **Correct:** `BUG-539 still OPEN` inside a dated entry is history and needs no edit — MEASURED: all nine such
  claims in buglog.md sit under dated entries, so the rule reports zero faults there and NO history byte was rewritten.
- **Wrong:** the same assertion in an undated scope, where it reads as a claim about now. The id and the claim must
  be ADJACENT: a line that names a closed bug beside a claim about another one is not a claim about it.
- **Test:** `test_a_present_tense_open_assertion_declares_its_moment`.

### INV-7 — Every fault NAMES ITS REPAIR, and history is never rewritten
- **Correct:** each fault carries the remedy in the message: relabel the snapshot, name the moment, date-scope the
  row, or correct it. The repairs applied under this rule were 8 lines of a 2,250-line register — the ones that
  claimed a state the register contradicts.
- **Wrong:** a fault that reports a contradiction and leaves the reader to invent the remedy (D-405), or a remedy
  that deletes a historical claim to make the rail green (R-D410: append-only).
- **Test:** `test_every_fault_names_its_repair`.

### INV-8 — The derived block stands ABOVE the history marker in every face
- **Correct:** the block's own census line is inside the `GOV-INDEX` sentinels above the marker, so the claim
  surface never judges it — the ordering is load-bearing, not cosmetic.
- **Wrong:** a face where the marker precedes the block, which would put the derived bytes inside the region declared
  to be history and make the rail fire on its own output.
- **Test:** `test_the_derived_block_stands_above_the_history_marker`.

### INV-9 — The rule is mutation-locked and its controls RUN
- **Correct:** config/rail_mutations.yaml carries the entry that makes a decision row's disagreement read as
  agreement, and the ladder runs the rail's `--selftest` before the check, so the control is SEEN to fire (D-2676 iv).
- **Wrong:** a rule whose oracle is never run, or a mutation whose declared `find` text no longer matches the bytes
  (a declaration that drifted from reality is FATAL, never a quiet pass).
- **Test:** `test_the_rule_is_mutation_locked_and_its_controls_run`.
