# SPEC — Config-Default Census, the INSTRUMENT (P0)

spec_version: 1
governed: scripts/check_config_defaults.py (the rail) · config/derivations.yaml#config_reads (its declared coverage and ceilings) · config/config_defaults_census.json (the receipt) · pipeline/pipeline_paths.py (the loud-read idiom `required/required_mapping/required_sequence`)
authority: D-2644 (a code default is an undeclared value) · D-2642 (one derived value, one home) · D-2982 (coverage fingerprint, debt as a SET, decision-locked rebaseline, the loud-read idiom) · BUG-504 (the class) · BUG-754 · BUG-758 · C12/C16 · BUG-660 (a rail measures, it does not write)
stamp: 2026-10-13 · deterministic authoring (no LLM gen)
status: each invariant is live-verified by tests/test_config_defaults_census_spec.py

## Purpose

Definition of correct for the rail that measures C12/D-2644 compliance. The rail is not a report about the
code — it is an INSTRUMENT, and an instrument that cannot state its own coverage produces numbers that are
compared to numbers taken a different way. This contract exists because that failure was measured: the census
could not see a config block aliased to a local name (BUG-758), and its count-only ceiling was raised seven
times in eighteen days with no raise attributable.

Lifecycle (owner-approved, D-2978): this file is OVERWRITTEN IN PLACE when the contract changes — never
appended, never a new file per change. History lives in git plus the D-number that changed it.

## Invariants

### INV-1 — The loud-read idiom cannot express a default
- **Correct:** `required`, `required_mapping` and `required_sequence` expose no parameter that supplies a value
  when a key is absent, and calling them on an absent key raises `MissingDeclaredKey`.
- **Wrong:** any signature carrying a `default=`/`fallback=` parameter, or a silent `{}`/`None` return. A helper
  that *can* default is a helper that will be defaulted with; the only rule that holds is the one that cannot be
  broken by passing an argument.
- **Test:** `test_the_idiom_cannot_express_a_default`.

### INV-2 — A missing declared value fails LOUDLY and names the remedy
- **Correct:** the raised message names the walked path, the home (`where=`) and the instruction to declare it,
  and the exception is a `KeyError` subclass so existing fail-closed `except KeyError` sites still catch it.
- **Wrong:** a bare `KeyError('key')` with no home, or a `SystemExit` deep in a library.
- **Test:** `test_a_missing_declared_value_names_the_remedy`.

### INV-3 — The instrument declares its own coverage
- **Correct:** `config_reads.coverage_fingerprint` exists and equals the fingerprint computed from the DECLARED
  coverage (rule version, receivers, config glob, scan roots, alias rule). A measurement may only be compared
  to one taken under the same fingerprint.
- **Wrong:** comparing a count measured under one rule set to a ceiling measured under another — the seven
  unattributed raises of BUG-758.
- **Test:** `test_the_instrument_declares_its_coverage`.

### INV-4 — No alias escape hatch, and no firing on honest locals
- **Correct:** a name bound EXACTLY ONCE in its scope to a config-rooted expression resolves as an alias (its
  leaf `.get(key, literal)` reads are SITEs); a name rebound in that scope, bound to a non-config expression, or
  rebound in an inner scope is NOT an alias.
- **Wrong:** the pre-2026-10-13 receiver-only rule (99 sites / 88 keys invisible), or the opposite failure: a
  census inflated by an honest `s4 = load_jsonl(...)` local.
- **Test:** `test_alias_rule_resolves_both_directions` (plus the rail's own 14 known-answer controls).

### INV-5 — The debt is a SET, and the receipt is the baseline
- **Correct:** `config/config_defaults_census.json` exists, its recorded counts equal the rail's live
  measurement, and its recorded KEY SET equals the measured set — so a debt that rotates (two keys paid, two
  new keys) cannot pass as a stable one.
- **Wrong:** a stored count with no key set, or a receipt that describes a different measurement than the tree.
- **Test:** `test_the_receipt_equals_the_measurement`.

### INV-6 — A ceiling is RAISED only by a cited decision
- **Correct:** `--rebaseline` without `--because <D-id>` exits drift; with an id absent from
  config/decisions.yaml it exits drift; and no other route can raise a ceiling (only `record_rebaseline`
  writes a ceiling without the shrink-only guard).
- **Wrong:** a flag or edit that lets a measurement above the ceiling be recorded silently.
- **Test:** `test_a_raise_needs_a_decision_that_exists`.

### INV-7 — A delta is attributed two ways: coverage vs code
- **Correct:** with the receipt's coverage held fixed, keys present now but absent from the receipt are NEW
  code debt; keys absent under the previous coverage but present now are newly VISIBLE; keys in the receipt but
  gone now are PAID.
- **Wrong:** reporting one number, which cannot distinguish a wider instrument from a bigger mess.
- **Test:** `test_the_delta_is_attributed_two_ways`.

### INV-8 — The D-2982 payment is regression-guarded
- **Correct:** the twelve keys paid by D-2982 (commit_scope, dedup_gate, growth_edge_output,
  process_instance_output, process_template_output, quarantine_output, require_both, s5_owned_columns,
  serving, symmetric_relationship_types, taxonomy_dependent_columns, tool_instruction_output) are absent from
  the measured shadowed set. A default that returns is a FAILURE, not a regression to be tolerated.
- **Wrong:** any of those keys reappearing as a shadowed-declared SITE.
- **Test:** `test_the_paid_keys_stay_paid`.

### INV-9 — The rail is exercised by the ladder, both halves
- **Correct:** the health recipe runs `--selftest` (the known-answer controls) AND the check, so a detector
  that has stopped detecting is itself detected.
- **Wrong:** a rail invoked only by hand — a detector nobody runs, or one whose controls never run.
- **Test:** `test_the_ladder_runs_both_halves`.

## Non-goals

- Paying down the 229-key baseline of pre-2026-10-12 sites. That is T-102/T-113 work, per key, because each
  key's default carries its own blast radius and deserves its own verification.
- Deciding *which* remediation a shadowed site needs. The rail measures; the owner declares (D-2644).
- Treating unreachable/probe code specially. The population is stated, not curated: curation is how a census
  becomes an opinion.

## Open items

- **T-113** pays the 71 keys the honest instrument revealed, in module-sized waves.
- **Stated limit (in the rail's docstring):** function ARGUMENTS are not collected as bindings, so an argument
  shadowing a module alias is not resolved as a shadow. Unfired in this tree as of 2026-10-13; a control must
  be added before the rule is extended.
