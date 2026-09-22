# F-11 SECOND CODER — ROUND 2 (all rows) — D-317 / D-319

## What this is
The owner has no second HUMAN coder, so the single-coder ruler sheet cannot yield inter-coder agreement on
its own. This package runs the SAME blind labelling task again, this time over **every** ruler row, so that
the rows the human left unanswered are adjudicated by the same coders instead of being dropped.

**Round 1** (governance/F11_LLM_CODER_20260921/) exported 122 of 150 rows: 28 rows lacked a human answer and
were excluded. Round 2 exports all rows. Nothing else changed.

## Provenance tier
`llm-attested`. This is NOT a second human coder and it is NOT independent of us in the strict sense. It
measures RULER RELIABILITY (human <-> LLM agreement), not human truth. It **cannot unfreeze**: F-11, the
D-300 adoption bar, or config/eval_integrity.yaml floors.

## Files
- `PROMPT.md` — paste this (verbatim) with the two attachments. Its sha256 is recorded in MANIFEST.json.
- `ROWS_BLIND.csv` — the rows to label (identity columns only; no human answers).
- `RULER_MENUS_20260917.md` — the three closed menus (authoritative). Attach it unchanged.
- `MANIFEST.json` — n_rows, input/output hashes, excluded item_ids, coder identity block.

## Step 0 — C22 hybrid sovereignty (EXPLICIT opt-in, recorded)
The rows are book-derived text. Sending them to an API model leaves the machine. Set
`coder.sovereign_opt_in: true` in `config/f11_llm_coder.yaml` **only** on the owner's explicit go.
A purely local fallback: run a different-family local model over the same `ROWS_BLIND.csv` with the same
`PROMPT.md` and score it identically — the measurement is the same, the sovereignty cost is zero.

## Steps
0. Record the coder identity card BEFORE the run (R14): `coder.model`, `coder.family`,
   `coder.prompt_sha256` = sha256 of `PROMPT.md` as actually sent. Never after.
1. Paste `PROMPT.md`, attach `RULER_MENUS_20260917.md` + `ROWS_BLIND.csv`, send.
2. Save the returned JSONL to `temp/<tag> labels.jsonl` (one object per line, one line per row).
3. Score it blind:
   `python3 scripts/f11_llm_coder.py --score "temp/<tag> labels.jsonl" --tag <tag> --model <id> --family <family>`
4. Fill in the second coder from a DIFFERENT model family, repeat 0-3.

## Where answers go
Answers go **only** in the JSONL the coder returns. `ROWS_BLIND.csv` carries a final empty fence column
headed `>>> ANSWER IN THE JSONL ONLY - DO NOT TYPE IN THIS CSV <<<` — leave it empty. Notes belong in the
per-row `note` field, never in a new column (this is the fix for BUG-368, where an emitted-but-empty column
was mistaken for free space).
