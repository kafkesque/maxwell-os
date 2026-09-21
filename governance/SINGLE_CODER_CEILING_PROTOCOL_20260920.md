# Single-coder ceiling — second human pass protocol (D-280, 2026-09-20)

The classifier's accuracy ceiling is **human-vs-human κ on the same closed menu** —
never "100%" (D-277). To bound that ceiling we need a SECOND independent human pass on
a subset of ANCHOR-1, blind to the first reviewer's labels.

**Sheet:** `governance/SINGLE_CODER_CEILING_SHEET_20260920.csv` (30 rows).

## Sample design

Deterministic, stratified to cover every RE-DERIVE slot (whose human κ matters most):

- discipline RE-DERIVE slots, all rows: design psychology (5), cultural studies (4),
  risk management (4), behavioral economics (4), decision making (4) → **21 rows**
- content-type RE-DERIVE slots, seeded draw: quarantine / process_template → **9 rows**

The label columns (`CT (1-7)`, `DISC (1-62)`, `FORM (1-4)`) are BLANKED (30/30 each),
so the second pass is blind.

## Procedure for the second coder

1. Open the sheet. Do NOT look at `RULER_BLIND_SHEET_20260917.csv` (it holds coder 1's
   labels) or `anchor1_frozen_20260920.json` (it holds coder 1's labels too).
2. For each row, classify from the CONTENT fields only (DEFINITION / APPLICATION /
   MECHANISM / BOUNDARY / SOURCE EXCERPT).
3. Fill three labels, all against the SAME closed menu coder 1 used:
   - **CT (1-7)** — use the D-275b decision procedure (`config/content_types.yaml` →
     `content_type_decision_procedure`): tool_instruction / growth_edge / noise_drop /
     process_template / principle / quarantine. If nothing fits, **leave the cell BLANK**
     (do NOT write `none` — coder 1 abstained by blank; the `none` value is a classifier-side
     R1 abstention, not a human-ruler value, and mixing them breaks κ).
   - **DISC (1-62)** — one of the 61 canonical disciplines in `config/taxonomy_v5.yaml`,
     or `emerging` if none fits.
   - **FORM (1-4)** — causal_mechanism / descriptive_model / normative_heuristic /
     empirical_pattern.
4. Leave a `note_codes` note only if the row is genuinely unclassifiable.

## After the pass

Run a κ/coder2 vs coder1 scorer over the 30 rows (the same inversion used by
`scripts/rescore_ruler_inverted.py`, but reference = coder 1, under-test = coder 2).
The resulting κ is the **human ceiling**: no classifier can be held to a higher
agreement than two humans reach on the same closed menu.

**Status: HUMAN GATE — sheet prepared, second pass not yet performed.**
