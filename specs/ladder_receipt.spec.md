# SPEC — Ladder Receipt, the whole-set VERDICT as a measurement (P0)

spec_version: 1
governed: scripts/run_ladder.py (the ladder's whole-set collector: --collect records, --banner and --receipt-check read) · config/rail_registry.yaml#ladder_receipt (the record's declared home, recipe and age budget) · config/rail_mutations.yaml (the rule's mutation lock) · justfile#health (where the readers stand and in which ORDER)
authority: D-2680 (the whole-set rule) · D-2982 (a measurement states its coverage; a fingerprint makes two measurements comparable) · D-2660 (a citation is a claim at the moment of mint) · D-404 (a number travels with its ruler) · D-2676 (no rule without one home, a seen control, a named oracle and a mutation) · BUG-573 (a prefix read as a verdict) · BUG-759 (the ladder stood RED on seven lines and nobody knew) · BUG-457 (tri-state) · C12/C16
stamp: 2026-10-13 · deterministic authoring (no LLM gen)
status: each invariant is live-verified by tests/test_ladder_receipt_spec.py

## Purpose

Definition of correct for the ladder's RECORDED whole-set verdict. `just health` reports a PREFIX: it stops at the
first non-zero line, so every line after a red one is unread — and until now the whole-set answer existed only in
the scrollback of whoever last ran the whole set. MEASURED 2026-10-13 (BUG-759): the full ladder had stood RED on
SEVEN lines and nobody knew, because a session that MINTS cannot get past the commit-frontier rail and a session
that never runs the whole set never sees the rest. The fix is not a promise to run it more often; it is a RECORD
that outlives the run, and two readers that cannot be quiet about it.

Lifecycle (owner-approved, D-2978): this file is OVERWRITTEN IN PLACE when the contract changes — never appended,
never a new file per change. History lives in git plus the D-number that changed it.

## Invariants

### INV-1 — The record carries its COVERAGE and its AGE
- **Correct:** a record is comparable only to a measurement taken the same way: the coverage is the recipe plus
  its ORDERED declaring lines (a sha16 fingerprint), and the moment of measurement is recorded so the record can
  be aged. A record inside its declared budget and matched by coverage is the ONE state in which "the ladder is
  green" is a measurement.
- **Wrong:** a bare fault count with no line set, an unparsable or absent moment silently read as "now", or a
  coverage derived from a second census of the ladder rather than from the lines the scan itself ran.
- **Test:** `test_the_record_carries_its_coverage_and_age`.

### INV-2 — A recorded red may not go quiet
- **Correct:** when the record holds faults under exactly the coverage in force, the verdict is FATAL (rc=1) and
  it NAMES the faults. A red the whole-set scan measured stays visible until the fault is fixed AND re-measured.
- **Wrong:** a green verdict for a record that measured faults, or a fault set reported as a count with no lines —
  a number that cannot be acted on is a number that gets explained away.
- **Test:** `test_a_recorded_red_cannot_go_quiet`.

### INV-3 — UNKNOWN is loud, owner-owed and never fatal
- **Correct:** never measured here, measured against a different ladder, or older than the declared budget is
  rc=2 — loud, and NOT fatal (BUG-457), because only a full scan can clear it. The message names the DERIVED
  remedy.
- **Wrong:** "unknown" printed as "clean"; or rc=1 for a state the reader cannot fix in the moment, which trains
  everyone to bypass the line.
- **Test:** `test_unknown_is_owner_owed_and_names_the_remedy`.

### INV-4 — A record measured over another ladder is not evidence
- **Correct:** a coverage mismatch (a line added, a line reordered, another recipe) makes the record UNKNOWN and
  the message shows BOTH fingerprints.
- **Wrong:** comparing a record to a ladder it was not measured over — the D-2982 defect (a rotating debt under a
  stable count) one level up, in the instrument that measures everything.
- **Test:** `test_a_changed_ladder_invalidates_its_record`.

### INV-5 — The whole-set entry point is DERIVED, never restated
- **Correct:** the entry point named in a remedy is read from the ladder's own bytes (the recipe whose line
  invokes the collector with `--collect <recipe>`), and a ladder that declares none is REPORTED as a fault
  rather than given an invented name.
- **Wrong:** a hard-coded recipe name; a prefix match (`--collect health-deep` read as an entry for `health`);
  or a remedy naming a recipe the ladder does not declare (D-405).
- **Test:** `test_the_whole_set_entry_point_is_derived`.

### INV-6 — The record has ONE declared home, and it is held OUT of version control
- **Correct:** path, recipe and age budget live in config/rail_registry.yaml#ladder_receipt; no key is defaulted
  in code (D-2644/C12); the path is gitignored runtime state, because committing a clone-local observation would
  dress it as durable evidence.
- **Wrong:** a path literal in the collector; a code default supplying a missing key; the record tracked in git.
- **Test:** `test_the_record_home_is_declared_and_never_committed`.

### INV-7 — The record equals the measurement it took
- **Correct:** `--collect` records the line count, the coverage, the worst code, each fault with its own rc and
  cost, the elapsed time, the moment and HEAD, written crash-safely (tempfile -> fsync -> os.replace, C6) — and
  it records a RED ladder too.
- **Wrong:** a record that can drift from the run it describes, a write that can leave a partial file, or a
  record written only on success.
- **Test:** `test_the_record_equals_the_measurement`.

### INV-8 — ORDER is load-bearing at both ends of the recipe
- **Correct:** the banner (which prints the record) stands FIRST so no rail can abort before the record is read,
  and it never aborts on the record itself; the enforced check stands LAST, because a whole-set report placed
  early would hide every line it speaks for. The guard class is PINNED in the registry (class (ii) otherwise).
- **Wrong:** the check placed before the rails it speaks for, a banner that can exit non-zero, or a guard
  silently changed from tri-state to fatal.
- **Test:** `test_the_order_is_load_bearing`.

### INV-9 — The rule is mutation-locked and its controls are run by the ladder
- **Correct:** a declared mutation in config/rail_mutations.yaml reds the control that names this rule through
  its own marker (D-2676 iv), the declared find-text matches exactly one line, and `just health` runs the
  collector's `--selftest`.
- **Wrong:** a rule with no mutation, a marker no control prints, or a drift between the declared find-text and
  the bytes (D-405).
- **Test:** `test_the_rule_is_mutation_locked_and_its_controls_run`.
