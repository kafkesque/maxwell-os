# SPEC — Governance Faces, the CLAIM SURFACE of the register (P0)

spec_version: 1
governed: scripts/check_governance_faces.py (the rail: --selftest is its own oracle, the check is the ladder's line) · scripts/gov_sync.py (the faces' ONE writer, whose census re-cut is scoped by INV-13) · DECISION-LOG.md · MASTER-TASK-REGISTER.md · governance/buglog.md (the three faces' declared history regions AND their live regions) · config/decisions.yaml + governance/bug_status.json (the registers a claim is joined to) · config/task_register.yaml (the register that says WHO must move each task) · config/gov_sync.yaml (the declared labels and axes) · config/rail_mutations.yaml (the rules' mutation locks) · justfile#health (where the rails and their controls stand)
authority: D-2985 (the LIVE region is a claim surface - this rule) · D-2984 (the HISTORY region is a claim surface - its mirror) · D-2981/R-1 (the faces are DERIVED, never hand-appended) · D-2642 (one derived value, one home) · D-2660 (a citation is a claim about the tree at the MOMENT OF MINT) · D-405 (a declaration whose subject is absent is an assertion) · BUG-588/D-2692 (a count restated in prose is stale) · BUG-669 (the predecessor: the rail read tables and marker lines, never prose) · BUG-760 (measured: the faces told the owner a closed decision was still pending) · BUG-761 (measured: a dangling citation in a declared-history region) · BUG-762 (measured: the live region was unpoliced) · R-D410 (append-only history) · BUG-492 (a detector nobody has seen fail is not a detector) · C12/C16/C19
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

## The mirror (D-2985)

D-2984 policed everything BELOW the history marker. MEASURED 2026-10-13: the region ABOVE it — the one the
owner actually opens — was unpoliced, and it was wrong three ways at once. `DECISION-LOG.md:12` still read
`## 🔴 CURRENT OPEN / PENDING INDEX (machine-derived 2026-10-03 — the live face; history below)`: a HAND
heading, ten days stale, calling itself machine-derived and the live face, two lines above the block that
claimed the same title. A file a live claim NAMED had no checker (`config/task_register.yaml` cited
`scripts/check_gov_sync.py`, which does not exist — the D-405 class, the same class as BUG-761's dangling
`D2537`). And no face said WHO must move the work, so every face led with a standing rule and two owner-gated
tasks rendered as `MUST … open`: the owner saw three rows he had already handed over, the agent saw a gate it
could never pass, and the actionable work never appeared. The rule's mirror sentence: **a claim in the LIVE
region joins a register too — and where the register says only the OWNER can move it, the face says so, and
says it FIRST.**

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
  a claim inside it) and it is history. The id cell may carry **markdown emphasis** or a **label suffix** — the
  claim is the id the cell LEADS with (`| **D-274b** | **RESOLVED** | … |`, `| D2546 SHACL+OWL | PLANNED | … |`),
  because a claim surface the rule cannot SEE is not covered by the rule. MEASURED 2026-10-13 in the verification
  pass that followed this rule's own landing: the first version required a BARE id cell and was blind to both
  shapes; seeing them changed no verdict (both instances sat in dated sections), but the blindness was real.
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

### INV-10 — The LIVE region is a claim surface: a hand line may not claim to BE the live index
- **Correct:** the phrase that points at the current state names ONE place — the derived block. A hand heading
  above it is a tier heading or a snapshot (`## 🔴 OPEN / PENDING — tier heading (the DERIVED block below owns
  the current state)`). The label may carry a heading marker, quote markers, emphasis and an icon, and it must
  still LEAD the line.
- **Wrong:** `## 🔴 CURRENT OPEN / PENDING INDEX (machine-derived 2026-10-03 — the live face; history below)` —
  a hand line that says it IS the index, dated ten days earlier. MEASURED 2026-10-13: the FIRST version of this
  limb (D-2984) could not see it, because it required the label to lead the line WITHOUT a heading marker, so the
  one line the owner opens the file on was invisible to the rule that exists to police it.
- **Test:** `test_a_hand_line_may_not_claim_to_be_the_live_index`.

### INV-11 — A file a live claim NAMES must exist
- **Correct:** a path cited in the live region resolves (`config/gov_sync.yaml`, `scripts/gov_sync.py`).
- **Wrong:** `config/task_register.yaml` cited `scripts/check_gov_sync.py` — a rail that has never existed, in
  the header of the register of record. A citation whose subject is absent is an ASSERTION (D-405), and it was
  the same class as BUG-761's dangling `D2537`: the declaration read as a guarantee while guaranteeing nothing.
- **Test:** `test_a_citation_in_the_live_region_resolves`.

### INV-12 — The face LEADS with the OWNER lane when the register declares owner-moved work
- **Correct:** the block's first task section is `**OWNER LANE (n) — what ONLY YOU can move**` (the label is
  declared once, in config/gov_sync.yaml), and the pipeline lane follows it. The boot face (`session_seed.yaml`)
  renders `YOURS:` before `AGENT NEXT:`.
- **Wrong:** any order that puts work the owner cannot do, or the agent cannot move, above the statement of what
  the owner must decide. MEASURED 2026-10-13: the four rows at the top of every face were a standing rule, two
  owner-gated tasks and one actionable task, sorted by priority alone — which is what "the resolved items are
  still on top" was describing, session after session.
- **Test:** `test_the_face_leads_with_the_owner_lane_when_the_register_has_one`.

### INV-13 — The census re-cut has a SCOPE: the live region. History is never rewritten.
- **Correct:** scripts/gov_sync.py re-cuts every census-shaped restatement line ABOVE the history marker and
  leaves everything below it BYTE-IDENTICAL (R-D410). A historical count is scoped by the moment its line names.
- **Wrong:** re-cutting the whole file, which this writer was doing: MEASURED 2026-10-13, the two SNAPSHOT lines
  had been re-cut to TODAY's counts while still reading "as measured then" — the writer that exists to stop
  stale counts was making historical claims FALSE. That is a CONFLICT between D-2981 (every restatement is
  derived) and the faces' own declaration that everything below the marker is dating-only history; D-2985
  resolves it in favour of the declaration.
- **Test:** `test_the_census_recut_never_rewrites_history`.
