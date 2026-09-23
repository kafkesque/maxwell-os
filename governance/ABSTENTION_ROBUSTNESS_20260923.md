# Error bars and reference drift on the ratified abstention points (D-352)

Paired bootstrap, 2000 resamples, seed 20260923, 95% intervals. Operating points READ from governance/ABSTENTION_CALIBRATION_20260923.json.

References are NOT interchangeable: `ruler_sheet_raw` is what the D-312 curve was measured against;
`ruler_in_force` (ANCHOR-3) is the only reference allowed to rank an arm today (D-347).

## discipline | reference: ruler_sheet_raw

n=122, base error 0.5 ()

AUC(margin vs correct) 0.7275[0.6352, 0.8126]

| abstained | kept | selective error (95% CI) | delta (pp) [95% CI] | P(delta>0) | error in abstained bucket |
|---|---|---|---|---|---|
| 0% | 122 | 0.5 [0.4098, 0.582] | 0.0 [0.0, 0.0] | 0.0 | None |
| 10% | 110 | 0.4545 [0.3545, 0.5455] | 4.55 [2.46, 6.08] | 1.0 | 0.9167 |
| 25% | 92 | 0.4022 [0.3043, 0.5] | 9.78 [4.31, 14.38] | 0.999 | 0.8 |
| 50% | 61 | 0.3279 [0.2131, 0.4754] | 17.21 [6.56, 24.59] | 0.9985 | 0.6721 |

## discipline | reference: ruler_in_force

n=150, base error 0.5533 ()

AUC(margin vs correct) 0.7035[0.6204, 0.7849]

| abstained | kept | selective error (95% CI) | delta (pp) [95% CI] | P(delta>0) | error in abstained bucket |
|---|---|---|---|---|---|
| 0% | 150 | 0.5533 [0.4733, 0.6333] | -0.0 [0.0, 0.0] | 0.0 | None |
| 10% | 135 | 0.5259 [0.4444, 0.6148] | 2.74 [-0.3, 4.96] | 0.962 | 0.8 |
| 25% | 112 | 0.5 [0.4018, 0.5893] | 5.33 [1.37, 10.26] | 0.9945 | 0.7105 |
| 50% | 75 | 0.3867 [0.28, 0.52] | 16.66 [7.33, 23.33] | 0.9995 | 0.72 |

## content_type | reference: ruler_in_force

n=150, base error 0.3467 ()

AUC(margin vs correct) 0.641[0.5484, 0.7299]

| abstained | kept | selective error (95% CI) | delta (pp) [95% CI] | P(delta>0) | error in abstained bucket |
|---|---|---|---|---|---|
| 0% | 150 | 0.3467 [0.2733, 0.4267] | 0.0 [0.0, 0.0] | 0.0 | None |
| 10% | 135 | 0.363 [0.2889, 0.4519] | -1.63 [-3.93, 1.19] | 0.093 | 0.2 |
| 25% | 112 | 0.3304 [0.2321, 0.4107] | 1.63 [-2.37, 7.0] | 0.8485 | 0.3947 |
| 30% | 105 | 0.3048 [0.219, 0.4] | 4.19 [-1.81, 8.86] | 0.908 | 0.4444 |
| 50% | 75 | 0.24 [0.12, 0.3467] | 10.67 [3.33, 19.33] | 0.996 | 0.4533 |

## Findings

- content_type: the ratified operating point's gain CI includes 0 on the ruler in force [-1.81, 8.86]
- content_type: P(gain>0) = 0.908 at the ratified operating point (<0.95)
- NOT REPRODUCIBLE: the ratified discipline base error 0.4741 (n=116) cannot be reproduced on the legacy reference. On every reconstructible subset the incumbent scores 0.5 (n=122); the 116-row denominator needs 6 rows whose identity is not recorded anywhere on disk, so the ratified curve was measured on a SUBSET of the reference now in force. Re-ratify the discipline operating point on the ruler in force (D-347)

RELATIVE-ONLY (D-337). Intervals describe sampling noise on a frozen reference, not absolute accuracy.
