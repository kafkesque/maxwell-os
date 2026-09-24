# ANCHOR-4 depth rubric (2026-09-23) - BLIND coding sheet for the depth axis

**Why this exists (BUG-415).** Depth is the only production axis with no anchor row, while D2577 plans a
fine-tuned 4-way depth head and D274f says nothing may be certified without an anchor. This sheet is the
missing anchor's input. It is a CONFORMANCE SET, not a training set (D274f).

**Item:** `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` - the same rows as the frozen ruler (150 data rows, item_id R001-R150; the provisional 154-row build was filtered to the 150 rows that ANCHOR-3 carries, so the 154-vs-150 provenance question in BUG-415 is RESOLVED: this sheet is row-identical to ANCHOR-3 by item_id, 150/150, zero name mismatches)
(`RULER_BLIND_SHEET_20260917.csv`), because they already carry DEFINITION / APPLICATION / MECHANISM /
BOUNDARY and are therefore answerable without re-reading the source. The ruler's CT / DISC / FORM columns
are carried over for context; they are NOT to be re-coded here.

**Task:** fill `DEPTH (1-4)`, `conf_depth` (1 = guessing, 2 = likely, 3 = certain), `note_codes` (free
text for any hard case), `reviewer`, `date`. Nothing else.

**The four classes (epistemic SCOPE, not subject matter).** The scope test: ask whether the claim survives
substitution into a DIFFERENT field with no domain-specific change.
1 = universal   - holds in every field tried; the domain context is irrelevant to its truth.
2 = cross-domain - holds in >= 2 fields but not all; at least one field resists it.
3 = domain      - holds inside one field; carrying it elsewhere needs re-derivation.
4 = specialized - holds only inside a narrow sub-specialty, an instrument, a technique or a named corpus.

Soft band (D2130, a BAND and not a hard rule - it must never be applied mechanically): universal >= 3
domains, cross-domain >= 2, domain 1..N adjacent, specialized 1. D282: scope is the depth axis and NEVER
the content_type discriminator - a 1-domain or specialized PRINCIPLE is still a principle.

**Blinding:** do not consult gpt-oss labels, the 3-voter consensus, `gold_4axis.jsonl` depth values, or any
classifier output while coding. Those are the things this anchor exists to judge.

**Protocol (do not skip step 3):**
1. code all 150 rows blind; 2. a SECOND coder codes the same 150 blind (different person, >= 2 weeks
later if the same person is unavoidable - see the same-person contamination in BUG-306); 3. measure
agreement and freeze; 4. only after the freeze, the D274f test-retest of 30 rows after >= 2 weeks - that
single-coder ceiling is what any floor on depth must be anchored to.

**What the frozen sheet may and may not be used for** (mirrors the ANCHOR-3 manifest, D-337):
allowed - arm ranking, A/B comparison, relative deltas; forbidden - an absolute error floor or an
error-rate certification for depth. The anchor is RELATIVE-ONLY, and the F-11 second-coder gate on the
other axes is already UNSATISFIABLE, so this one must not repeat that mistake: a single-coder ANCHOR-4
must never be frozen as if it were truth.

**Known limit (BUG-416):** the depth vocabulary is NOT declared in any config surface, so this rubric is
hand-written rather than generated. When the 4 classes are declared in config, this file must be
regenerated from it (C12 config-first) and the menu-closure check repointed at the same source.

## CONTEXT PROVENANCE (added 2026-09-24, BUG-421)

The `CT (1-7)` / `DISC (1-62)` / `FORM (1-4)` columns of this sheet are DERIVED, not authored: they are
generated from `governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv` (`content_type_final`,
`discipline_final`, `extraction_type_final`) by `python3 scripts/consolidate_anchor4_context.py --apply`
and guarded by `--check`. Do NOT edit them by hand; re-run the generator. Before 2026-09-24 they were a
copy of the pre-consolidation raw ruler and 260 of 450 cells were stale or blank.

**Blinding, second rule.** `governance/ANCHOR4_DEPTH_PREDICTION_KEY_20260924.json` carries the corpus
`fb_id` bridge and the depth values that already exist in `gold_4axis` / `depth_vote_checkpoint`.
A coder MUST NOT open it while coding; it is unsealed only AFTER the freeze, as a pre-registered
prediction check against the frozen anchor.
