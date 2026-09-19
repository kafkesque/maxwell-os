# Blind D1 re-adjudication — 60 rows, ~30 minutes

## Why
The first pass on these 60 rows let the adjudicator see WHICH MODEL produced which label
(`discipline_A_deepseek` / `discipline_B_qwen38`), so "DeepSeek wins 40:15" could just be brand
authority. This sheet hides provenance. Your answer here is the one that settles whether
`deepseek-v4-pro` earns a place in the pipeline at all.

## Do NOT open this until you are finished
`KEY_do_not_open_until_finished.json` — it maps every row to its models. Opening it first destroys
the whole point of the exercise.

## How
1. Open `governance/d1_blind_review_20260916/BLIND_D1_sheet.csv` (Numbers, Excel, or any editor).
2. For each of the 60 rows, read the `definition` (the actual principle text) and decide which of
   `candidate_1` / `candidate_2` is the better **discipline** label for that principle.
3. Fill `YOUR_PICK` with exactly one of: `1`, `2`, or `neither`.
   - `1` = candidate_1 is the better label
   - `2` = candidate_2 is the better label
   - `neither` = both are wrong (say what it should be in `YOUR_NOTE`, optional)
4. Save as CSV, keeping the same filename and the same column names.
5. Run: `python3 governance/d1_blind_review_20260916/score_blind.py`

Notes
- Judge the label against the definition, NOT against the current silver/gold label — the silver
  label is deliberately hidden so it cannot anchor you.
- `candidate_1` is NOT always the same model. The sides were flipped at random (seeded), so do not
  try to infer a pattern; just answer each row on its merits.
- Ties are allowed and meaningful (`neither`). Do not force a pick.
- Domains are NOT part of this task: the domain head-to-head measured a dead tie (28 vs 29 of 172
  disagreements), so the open question is discipline only.
