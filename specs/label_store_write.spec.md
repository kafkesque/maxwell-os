# SPEC — The LICENSED store write for OWNER-RULED labels (T-103)

spec_version: 1
governed: scripts/apply_relabel_store_write.py (the ONE writer) · config/relabel_rulings.yaml#store_write_license (the ONE home of the owner word) · config/label_store_write_receipt.json (the measurement) · scripts/apply_relabel_rulings.py (the plan applier that publishes the OWED half) · config/rail_mutations.yaml (the rules' mutation locks)
authority: D-2988 (this rule) · D-2977 (the owner's class rulings) · D-2898 (no agent mints a LABEL) · D-2830 (the declared absence) · D-2884a (the fine→macro collapse home) · D-2642 (one derived value, one home) · D-2644 (a ceiling may only be LOWERED) · D-2660 (a citation is a claim at the MOMENT OF MINT) · D-279/C29 (the provenance tier vocabulary) · BUG-749 (the re-derivation gap) · BUG-751 (a positional ordinal re-points) · C6 (crash-safe writes) · C12 (no undeclared value) · C13 (backup after batch writes) · C16 (fail closed) · C19 (a declaration nothing reads is bloat) · R14 (reproducible provenance) · D-2676 (mutation-locked)
stamp: 2026-10-13 · deterministic authoring (no LLM gen)
status: each invariant is live-verified by tests/test_label_store_write_spec.py

## Purpose

A class ruling says WHICH WAY a mapping must go. It does not license a WRITE, because rewriting a row's canonical
discipline is a store mutation and D-2898 forbids an agent minting a LABEL. This spec defines the instrument that
closes that gap: the write that EXECUTES an owner ruling which already exists, and nothing else.

MEASURED before it existed (2026-10-13): the plan applier rendered five units as OWED — 4 CORRECT (103 rows) and
1 ABSTAIN (60 rows) — while the only writer that could discharge them was an ad-hoc `UPDATE fbs SET discipline`
among the twenty-odd call sites already in scripts/ and pipeline/. The gap between "the owner ruled" and "the store
agrees" had NO instrument, no ceiling, no receipt, and no way to refuse.

WHAT THE WRITE IS, ONTOLOGICALLY. Not a re-classification: it copies the PRODUCTION MAPPER's own answer into the
store for rows an owner ruling already reaches, so the stored canonical becomes REPRODUCIBLE from the row's own raw
label (R14). It therefore never invents a label — a row whose mapper answer, owner target and recorded packet answer
disagree is REFUSED rather than resolved, because choosing between three authorities is exactly the act D-2898
reserves for the owner.

## Invariants

### INV-1 — The owner word is the whole authority for the write
- **Correct:** `config/relabel_rulings.yaml#store_write_license` names `decision`, `granted`, `units`, `row_cap`,
  `provenance_tier`; with no license block the runner refuses and writes NOTHING (exit 2).
- **Wrong:** a documented convention that a ruled row "may be written" — an authority carried by nothing a machine
  reads, which is how the twenty existing `UPDATE fbs SET discipline` sites came to exist.
- **Test:** `test_no_license_no_write`.

### INV-2 — The write EXECUTES a ruling, it never MINTS one
- **Correct:** a LICENSED unit whose effective ruling is not CORRECT/ABSTAIN (ESCALATE, CONFIRM, LEAVE, or a HELD
  word) is a fault named `scope/not-ruled`, and no operation is emitted for it.
- **Wrong:** sweeping an ESCALATE unit into the write because it sits in the same cause — that is a LABEL minted by
  script, the exact act D-2898 forbids.
- **Test:** `test_a_licensed_unit_without_a_ruling_is_refused`.

### INV-3 — The license may not be NARROWER than the rulings
- **Correct:** a unit whose effective ruling is CORRECT/ABSTAIN that the license does not name is a fault named
  `scope/not-licensed`: a ruled row left owed is a silence, not a conservative choice.
- **Wrong:** a license that silently omits a ruled unit, so the OWED half of the plan never drains and no line reports it.
- **Test:** `test_an_unlicensed_ruled_unit_is_a_fault`.

### INV-4 — The target is TRIPLY agreed, and the scope never widens
- **Correct:** for every row, `mapper(discipline_raw) == owner target == packet's live_mapper_says`; the plan can
  emit an operation only for a LICENSED `unit_key`, and the emitted `to` is the mapper's answer.
- **Wrong:** the applier picking a target from a table of its own, or writing a row of an unlicensed unit because the
  predicate "matched".
- **Test:** `test_the_target_is_triply_agreed`.

### INV-5 — The scope is by IDENTITY; a stale surface is refused
- **Correct:** rows are selected by `fb_id` from the packet's own row-level surface; a row whose stored value is not
  the value the packet reviewed, or a packet whose per-unit `n_rows` disagrees with its segments file, is a fault
  named `surface/stale` (the surface moved under the write), and nothing is written.
- **Wrong:** a predicate over `discipline_raw` (which sweeps in rows no owner saw), or writing against a packet that
  has since been rebuilt.
- **Test:** `test_a_stale_surface_is_refused`.

### INV-6 — The ceiling is SHRINK-ONLY and the tier must be DECLARED
- **Correct:** `row_cap` is a ceiling the plan may not exceed (`cap/exceeded`, D-2644: a wider write needs a NEW owner
  word); `provenance_tier` must be a member of the C29 vocabulary read from its ONE home (`tier/undeclared`).
- **Wrong:** raising the cap to cover a wider surface, or stamping a tier nothing declares — a manufactured claim.
- **Test:** `test_the_cap_and_the_tier_are_declared`.

### INV-7 — The write is MEASURED, never claimed
- **Correct:** `--apply` takes a timestamped size-verified backup, passes a `PRAGMA` integrity gate, writes in ONE
  transaction, re-reads every written row, records the store's `menu_hash` SET before and after, and writes a
  receipt (config/label_store_write_receipt.json) carrying each input's sha256, `changed`/`verified`/`planned`, and
  a `fault` flag when the two disagree.
- **Wrong:** a rowcount from the `UPDATE` believed as a verdict, or a receipt that states the outcome without the
  bytes it consumed (D-2660).
- **Test:** `test_the_receipt_records_a_measurement`.

### INV-8 — The RAW is never touched and the derived columns come from their ONE home
- **Correct:** the applier's write set is exactly `discipline`, `discipline_macro`, `discipline_source`,
  `taxonomy_match_method`; `discipline_raw` never appears in it; the macro is `pipeline.discipline_macro.macro_for`
  (imported, D-2884a) and the counts recount is `pipeline.taxonomy_manager.update_counts_from_fbs` (imported).
- **Wrong:** writing the raw (destroying provenance), restating the fine→macro map in the applier, or leaving
  `taxonomy_counts` stale so the store's own label counts contradict its rows.
- **Test:** `test_the_raw_and_the_macro_home_are_untouched`.

## Measured outcome of the first licensed write (2026-10-13, D-2988)

- plan: 163 rows across 5 units — `marketing science → marketing` (94), `entrepreneurial studies →
  entrepreneurship studies` (4), `marketing strategy → marketing` (4), `market research → marketing` (1),
  `computer science → emerging` (60); `changed=163 verified=163 planned=163`, the store's menu SET unmoved.
- store: `marketing` 259 → 358, `entrepreneurship studies` 1 → 5, `software engineering` 167 → 107,
  `emerging` +60, `discipline_source = 'deterministic'` on exactly the 163 written rows.
- the instrument that publishes the debt: the plan applier now renders CORRECT 0 / ABSTAIN 0 / ESCALATE 72
  (the ruled-but-owed half is DISCHARGED); the re-derivation gap the owner's ruling named fell 457 → 294 rows
  (the packet's own subject line, before and after).
