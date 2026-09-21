# ANCHOR-1 — frozen blind-human label set (2026-09-20)

150 rows. **human label = ground truth, stored label = under test** (D-275a).
CSV integrity: `sha256=4d0c856a045aeab5…`

This artifact is immutable. The live CSV may be re-edited by the reviewer; all downstream
work (R5 slot vote, R1 closed menu, R2 definition NLI, per-slot κ) references THIS file.

## Headline stored-label error rates (inverted key)

| axis | stratum all | stratum A | scored |
|---|---|---|---|
| content_type | **0.353** | 0.290 | 150 |
| discipline | **0.474** | 0.487 | 116 |
| extraction_type | **0.283** | 0.255 | 145 |

`A` = pre-agreed clean subset (comparable to prior FORM pass); `all` = honest bound (includes stratum B, which is non-proportional and mixes PASS/QUARANTINE — D1/D2).

## R5 repair — content_type (7 = 5 roles + 2 dispositions)

| slot | n | stored agrees | error | proposed disposition |
|---|---|---|---|---|
| principle | 89 | 71 | 0.202 | measure κ (no action yet) |
| quarantine | 18 | 1 | 0.944 | RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write) |
| process_template | 16 | 6 | 0.625 | RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write) |
| noise_drop | 13 | 9 | 0.308 | measure κ (no action yet) |
| tool_instruction | 8 | 6 | 0.250 | measure κ (no action yet) |
| process_instance | 3 | 2 | 0.333 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| growth_edge | 3 | 2 | 0.333 | EXTEND-SAMPLE (n<4, insufficient evidence) |

**CT finding:** the old classifier treats `principle` as the default — it under-calls `quarantine` (human 18 → stored 6) and `process_template` (human 16 → stored 9), pushing them into `principle`. This is the measured signature of the D-275b guardrail gap (step-count, not procedural intent). The fix is NOT a slot demotion — it is the D-275b discriminator, which re-balances the axis.

## R5 repair — discipline (61-menu)

| slot | n | stored agrees | error | proposed disposition |
|---|---|---|---|---|
| operations research | 8 | 5 | 0.375 | measure κ (no action yet) |
| psychology | 7 | 5 | 0.286 | measure κ (no action yet) |
| design thinking | 7 | 4 | 0.429 | BOUND (human review on write) |
| research methodology | 6 | 5 | 0.167 | measure κ (no action yet) |
| human-computer interaction | 5 | 5 | 0.000 | measure κ (no action yet) |
| organizational theory | 5 | 3 | 0.400 | BOUND (human review on write) |
| design psychology | 5 | 0 | 1.000 | RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write) |
| cultural studies | 4 | 0 | 1.000 | RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write) |
| risk management | 4 | 0 | 1.000 | RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write) |
| behavioral economics | 4 | 1 | 0.750 | RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write) |
| typography | 4 | 3 | 0.250 | measure κ (no action yet) |
| decision making | 4 | 1 | 0.750 | RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write) |
| semiotics | 3 | 2 | 0.333 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| strategic thinking | 3 | 3 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| creative process | 3 | 1 | 0.667 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| information science | 3 | 3 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| privacy & surveillance | 2 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| political economy | 2 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| computer graphics | 2 | 2 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| generative design | 2 | 2 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| information retrieval | 2 | 1 | 0.500 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| engineering | 2 | 1 | 0.500 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| visual perception | 2 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| finance | 2 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| software engineering | 2 | 2 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| philosophy | 2 | 2 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| artificial intelligence | 2 | 1 | 0.500 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| media studies | 2 | 2 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| cultural design | 2 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| systems engineering | 1 | 1 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| sociology | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| neuroscience | 1 | 1 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| performing arts | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| cognitive science | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| linguistics | 1 | 1 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| economics | 1 | 1 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| communication theory | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| machine learning | 1 | 1 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| computational geometry | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| generative ai | 1 | 1 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| information security | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| computational physics & simulation | 1 | 1 | 0.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| literary theory | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |
| color theory | 1 | 0 | 1.000 | EXTEND-SAMPLE (n<4, insufficient evidence) |

**DISC group-level near-miss:** exact-canonical error 0.430, same-group error 0.271 → 29 stored labels land in a DIFFERENT discipline group. Even forgiving slot-boundary disagreements, ~27% are wrong.


**DISC reading (D-277):** zero-agreement is evidence against the OLD PIPELINE, not necessarily
against the SLOT. `design psychology`, `cultural studies`, `risk management` are the strongest
RE-DERIVE + BOUND candidates — give each a clean definition+include+exclude, re-measure, and merge
into the parent group only if still definitionally inseparable. `emerging_dump` (stored) absorbs
3+ of these, so the old extraction silently discarded that content into `emerging`. All
dispositions above are **PROPOSED — awaiting reviewer ratification** (R5).

## What this enables (dependency order)

1. **R5** — ratify the dispositions above; RE-DERIVE definition + include + exclude (OntoClean)
   for weak slots and BOUND them (human review); merge only if inseparable — never DEMOTE first.
2. **R1** — closed-menu classification rendered from `config/taxonomy_v5.yaml` with `none`
   first-class + `menu_hash` stamped.
3. **R2** — definition-anchored NLI verification against the menu definitions.

Provenance columns (`menu_hash`, `*_source`) remain open (C1/C2 risk register) — needed before
any corpus-wide re-classification, so the `min_human_share` provenance share is satisfiable.

