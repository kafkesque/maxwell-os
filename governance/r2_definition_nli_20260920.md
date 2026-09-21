# R2 — definition-anchored NLI (D-281, 2026-09-20)

R2 verifies a proposed label against its own **closed-menu definition**, with the R5
repaired definitions (`config/r5_slot_repair.yaml`) taking precedence for the weak
slots. This replaces the flat `"This text is about {label}."` hypothesis, which
under-entails on broad labels (D2571 anomaly-C).

**Script:** `scripts/definition_nli_verify.py`

## Mechanics

For each FB and each proposed label (discipline + domains + content_type):

- **premise** = FB definition (truncated to `S5_NLI_MAX_PREMISE_CHARS`)
- **hypothesis** = the label's menu definition (R5 override first, else taxonomy)

The S5 NLI pair scorer (`stage5_verify._nli_pair_scores`) returns entail / neutral /
contra.

- `contra` ≥ the S5 threshold → **hard mislabel signal** (definition contradicts the FB).
- `neutral` / low-entail → **weak signal** (definition not entailed).

This is **Mechanism B (a meter)** per D-277: it calibrates confidence and triggers
human review / abstention. It NEVER flips a label by itself.

## Status

- `--selfcheck` is green: the closed menu + R5 overrides load (content_type 2,
  discipline 7), and every re-derived slot resolves to a definition.
- The **corpus-wide NLI run is the next action** — a long local inference over the
  stage5 checkpoint (`python3 scripts/definition_nli_verify.py --input <checkpoint>`).
  Not executed in this batch.

## Output

`governance/r2_definition_nli_20260920.json` — per-FB, per-label entail/neutral/contra
scores + a count of contradiction-level mislabel signals.
