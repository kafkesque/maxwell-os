# R2 definition-anchored NLI as a monotone precision gate (D-348)

Reference: governance/r2_definition_nli_20260920_v2.json (7995 FBs, existing artifact, no new inference) x governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv (150 joined rows).

flag if any assigned-label score has contra >= contra_threshold, OR assigned-label support (max entail) < weak_entail

## content_type

n=150 (skipped 0) base error 0.3467; AUC(support vs correct) 0.641; mean support correct 0.4693 vs wrong 0.229

gate: flag rate 0.3867, error on flagged 0.4483 vs unflagged 0.2826

| retained coverage | kept | selective error | delta vs base (pp) |
|---|---|---|---|
| 1.0 | 150 | 0.3467 | 0.0 |
| 0.95 | 142 | 0.3592 | 1.25 |
| 0.9 | 135 | 0.363 | 1.63 |
| 0.85 | 128 | 0.3516 | 0.49 |
| 0.8 | 120 | 0.3333 | -1.33 |
| 0.75 | 112 | 0.3304 | -1.63 |
| 0.7 | 105 | 0.3048 | -4.19 |
| 0.6 | 90 | 0.2667 | -8.0 |
| 0.5 | 75 | 0.24 | -10.67 |

## discipline

n=137 (skipped 13) base error 0.5255; AUC(support vs correct) 0.5348; mean support correct 0.39 vs wrong 0.3442

gate: flag rate 0.3577, error on flagged 0.4898 vs unflagged 0.5455

| retained coverage | kept | selective error | delta vs base (pp) |
|---|---|---|---|
| 1.0 | 137 | 0.5255 | 0.0 |
| 0.95 | 130 | 0.5154 | -1.02 |
| 0.9 | 123 | 0.4959 | -2.96 |
| 0.85 | 116 | 0.5086 | -1.69 |
| 0.8 | 110 | 0.5182 | -0.74 |
| 0.75 | 103 | 0.5243 | -0.13 |
| 0.7 | 96 | 0.5312 | 0.57 |
| 0.6 | 82 | 0.5122 | -1.34 |
| 0.5 | 68 | 0.4853 | -4.03 |

## Declared unmeasurable

- extraction_type: no R2 score exists for this axis. An operating point here may NOT be transplanted from another axis (ABSTENTION_DESIGN: role/axis specific).
- domains: no ruler truth column exists.

RELATIVE-ONLY (D-337). Gate discrimination on a frozen ruler, not an absolute accuracy floor.
