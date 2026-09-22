# F-11 ROUND 2 — MEASUREMENT (2026-09-22/23) — decision D331

Runs the F-11 second-coder task a second time over ALL 150 ruler rows (round 1 exported only the 122 rows
where the human had answered every axis). Two attestation coders, two different families, blind, temp 0.0,
same PROMPT.md (sha256 578eaee8f60d97f7a0a2d577ce6b98208a1157a76f60c37502fca1d3f7d4c9ee) and same
ROWS_BLIND.csv (150 rows, MANIFEST n_rows 150, 0 excluded, partial false).

## Delivery integrity
Both coders returned 150/150 rows, all unique, all 9 schema fields, 0 gaps, 0 padding, 0 invented columns.
No answer was written into the CSV fence column (BUG-368 could not recur).

## 1. Human vs coder (non-blank pairs only; BUG-369 fix)
| axis | coder | n | agreement | Cohen kappa | mean conf |
|---|---|---|---|---|---|
| content_type | claude-sonnet-4.5 | 150 | 71.3% | 0.487 | 0.594 |
| content_type | kimi-k3 | 150 | 75.3% | 0.554 | 0.813 |
| discipline | claude-sonnet-4.5 | 122 | 45.9% | 0.445 | 0.539 |
| discipline | kimi-k3 | 122 | 41.8% | 0.403 | 0.703 |
| extraction_type (FORM) | claude-sonnet-4.5 | 145 | 48.3% | 0.305 | 0.590 |
| extraction_type (FORM) | kimi-k3 | 145 | 46.9% | 0.266 | 0.799 |

## 2. Coder vs coder — two independent families, all 150 rows (the round-2 payoff)
| axis | n | agreement | Cohen kappa |
|---|---|---|---|
| content_type | 150 | 88.7% | **0.758** |
| discipline | 150 | 69.3% | **0.682** |
| extraction_type (FORM) | 150 | 74.0% | **0.638** |

**The two model families agree with each other 1.6-2.4x more strongly than either agrees with the human, on
every axis.** This is the D-329 finding reproduced on the complete row set with a much larger n. The ruler's
human labels are the outlier relative to two independent attestation coders, so no eval floor can be
certified from this sheet (D-317 / D-329 stand, F-11 stays open). Absolute error rates computed against this
reference are bounded below by the reference's own reproducibility and are NOT a property of the classifier.

## 3. Where the human abstained (BUG-363) — now measured instead of guessed
* FORM, 5 rows (R012, R021, R026, R084, R140): both coders agree 5/5 (k=1.0). These rows are NOT ambiguous —
  the abstention is an oversight, not a signal. Candidate for the owner's own adjudication (or a declared
  gap-fill with the coder consensus recorded as `llm-attested`).
* DISC, 28 rows: the coders agree on only 18/28 (64%, k=0.623) while agreeing 0.682 on the rows the human DID
  label. Those 28 rows are genuinely contested (no, they are not all trivially easy), so they are declared
  **UNCERTIFIABLE** and are NOT back-filled. Any downstream use of DISC must treat them as missing, not as
  consensus. ids: R007 R012 R019 R021 R026 R028 R034 R040 R042 R046 R052 R056 R059 R060 R063 R072 R080 R082
  R084 R088 R091 R102 R106 R140 R143 R144 R147 R148.
* CT: no blank cells inside the scored 150-row set.

## 4. Bugs found while doing this
* **BUG-369 (FIXED)**: `cmd_score` appended `(_canon(human), _canon(llm))` pairs unconditionally, so a blank
  human cell became the label `""` and every such row was counted as a coder DISAGREEMENT. This deflated
  round-2 DISC agreement from 45.9% to 37.3% and made round 1 (complete cells) incomparable to round 2.
  Fix: blank-aware pairing with `n_excluded_human_blank` / `excluded_human_blank_item_ids` reported per axis.
  An unanswered cell is now never scored as an error (C16: no silent skew in either direction).

## 5. Tier and standing
`llm-attested` / advisory. Cannot unfreeze F-11, the D-300 adoption bar, or config/eval_integrity.yaml floors.
The only way to lift this is a genuinely independent HUMAN second coder (still the standing F-11 requirement).
