# Taxonomy v6 migration record (2026-09-21)

Trigger: ANCHOR-1 repair triage (owner-approved PART1 A).

## Added domains

## Unchanged
- every v5.5 canonical is preserved; no slot was removed or renamed,
  so all pre-v6 kappa / contra numbers stay readable.

## Normalisation (not menu changes)
- media & entertainmen -> media & entertainment
- product desig -> product design
- business operation -> business operations
- marketing & communications" -> marketing & communications
- "leadership" -> leadership
- social science -> social sciences
- human-computer interaction -> human computer interaction

## Not yet applied
- the 16 discipline boundary pairs (PART2 B) are reviewed one at a time;
  see MENU_REPAIR_QUEUE_20260921.md. Pipeline output is unchanged until they are settled.

## CORRECTION (same day, before any pipeline use)

Verified against the taxonomy: EXIST = ['systems & frameworks', 'web & ui', 'social sciences', 'illustration', 'code & computation', 'environmental design', 'motion design', 'design systems'] ; ABSENT = []

The v6 bump therefore added ZERO new slots. The 60-row sheet shows what the pipeline CHOSE, not what the menu OFFERS.
So the 8 are an ASSIGNMENT/EMISSION problem (slots exist, never selected), not an ontology gap: no new labels,
no kappa re-basing. PART1 B normalisation (config/normalization_map.yaml) is real and measurable: domain
observed agreement 0.3938 -> 0.4385. PART2 B pairs stay queued for one-at-a-time boundary review.
