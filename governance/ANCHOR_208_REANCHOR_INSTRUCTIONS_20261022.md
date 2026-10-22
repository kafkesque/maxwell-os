# T-191 / D-3116 — Re-anchor the 208-row bridge ruler (OWNER procedure)

Owner-gated. The bridge stays RED until this is done. The pipeline cannot move it (D-3035).

## Why (one line)
After D-2881 re-chunked the store to `rechunk-v4-20260929`, 195 of the 208 ruler
names no longer byte-match any store name. A mechanical nearest-name re-key would
corrupt the anchor (best word-overlap Jaccard ~0.14 = WRONG concepts), so D-3116
ruled option 1: **the owner re-adjudicates each dangling concept to its correct
canonical-store row, blind to the bridge's own guesses.**

## What you fill
The semantic candidate sheet already exists:
`governance/ANCHOR_208_REANCHOR_CANDIDATES_20261020.csv`

Each row = one dangling concept, with columns:
- `item_id` (R001…) + `ruler_name` (the OLD name, keyed to the removed t11 run)
- `cand1..cand5` — the top-5 store rows by bge-m3 cosine (name / fb_id / cos). **Advisory only.**
- `owner_ruling_fb_id` — **you fill this**
- `owner_ruling_note` — optional

Fill `owner_ruling_fb_id` for every row:
- paste ONE candidate's `fb_id` if that store row is the SAME concept, OR
- write `NONE` if no store row carries the concept any longer (it was re-segmented away).

Do NOT edit `ruler_name` or the `cand*` columns. The bridge never guesses (D-2658):
only your ruling names the row.

## Steps (copy-paste)

1. Confirm the store + candidates are current:
   ```
   python3 scripts/build_anchor_store_bridge.py --check
   ```
   Expected: `bridge: drift 195 UNDECLARED unresolved row(s): [...]` (exit 1). This is
   the RED state that T-191 clears.

2. Open the sheet and fill `owner_ruling_fb_id` on all 195 rows:
   `governance/ANCHOR_208_REANCHOR_CANDIDATES_20261020.csv`
   (If you want a freshly regenerated sheet instead, first ensure bge-m3 is up, then:
   `python3 scripts/build_reanchor_candidates.py --top-k 5` — writes a new dated sheet.)

3. Save the filled sheet (keep the filename; it is the input the applier reads).

4. Hand the filled sheet back to the agent (message: "sheet filled"). The agent then:
   - applies your rulings to re-derive a ruler keyed to `rechunk-v4-20260929`,
   - re-runs `build_anchor_store_bridge.py --check` and reports the verdict.

## If it differs
- `build_anchor_store_bridge.py --check` prints `ok …/… anchor rows bridged` (exit 0) →
  the re-anchor landed; T-191 is DONE and the bridge measures the store again.
- Any exit 2 (`owed`) or a remaining `drift` → the agent will name the unresolved rows;
  re-open the sheet only for those rows.
