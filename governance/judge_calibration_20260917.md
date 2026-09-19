# Judge calibration — measured verdict (G3)

Sheet: `governance/JUDGE_CALIBRATION_SHEET_20260917.csv` | measured 2026-09-17T19:54:23

Human answered **first and blind**. Wording differences were normalised; a genuine third state was **not** coerced. `lift` = accuracy − the constant-answer baseline: a judge must beat it by the configured margin or it is **degenerate** (`config/eval_integrity.yaml::judge_calibration`).

## Decision

| task | verdict |
|---|---|
| `T1_dedup` | ADOPT gemma-4-E4B-it-MLX-4bit acc=1.000 vs baseline 0.571 (lift +0.429) as the verifier |
| `T2_suffix_merge` | DEGENERATE — gemma-4-E4B-it-MLX-4bit acc=0.875 vs baseline 0.875 (lift +0.000) — the judge adds no information over the constant answer 'merge'; make this task deterministic or human-owned |
| `T3_content_type` | DEGENERATE — gpt-oss-20b-MXFP4-Q8 acc=0.333 vs baseline 0.778 (lift -0.445) — the judge adds no information over the constant answer 'principle'; make this task deterministic or human-owned |
| `T6_frontier69` | DEGENERATE — gemma-4-E4B-it-MLX-4bit acc=0.778 vs baseline 0.778 (lift +0.000) — the judge adds no information over the constant answer 'justified'; make this task deterministic or human-owned |

## Accuracy vs the constant-answer baseline

| task | n | baseline | baseline label | `gemma-4-E4B-it-MLX-4bit` | `gpt-oss-20b-MXFP4-Q8` |
|---|---|---|---|---|---|
| `T1_dedup` | 7 | 0.571 | `same` | 1.000 (lift +0.43) | 0.571 (lift +0.00) |
| `T2_suffix_merge` | 8 | 0.875 | `merge` | 0.875 (lift +0.00) | 0.750 (lift -0.12) |
| `T3_content_type` | 9 | 0.778 | `principle` | 0.222 (lift -0.56) | 0.333 (lift -0.44) |
| `T6_frontier69` | 9 | 0.778 | `justified` | 0.778 (lift +0.00) | 0.778 (lift +0.00) |

## Coverage (reported, never silently dropped)

- rows total: **36**
- decisive (scored): **33**
- third state (`inbetween` etc., excluded from the denominator): **3**
- out of set: **0**

### Rows with no binary answer

- `T1_dedup` / `T1-03` — human said `inbetween`
- `T1_dedup` / `T1-06` — human said `inbetween`
- `T2_suffix_merge` / `T2-01` — human said `inbetween`

A forced binary under-describes these rows (the same signal as G2's `quarantine`). Report it; do not coerce it.

## Caveat

n is small per task (7-9 decisive rows). Treat these as **indicative**: they are enough to reject a judge that does not beat the constant answer, not enough to certify one. The proper instrument (Krippendorff alpha + a per-task n_min) is still unbuilt — market research A1/A2.
