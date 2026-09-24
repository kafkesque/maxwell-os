# ANCHOR family consolidation plan (2026-09-24)

**Why this document exists.** On 2026-09-24 the owner asked "I already did domain assignment for the 150,
why are those not present in the ANCHOR4 sheet?" The answer was: they ARE done - and they were *not* in the
sheet because the sheet had been built by COPYING the pre-consolidation raw ruler instead of DERIVING from the
consolidated artifact. The question itself is the symptom: **there was no single place that said which anchor
artifact is authoritative for which axis.** This plan creates that place and the guards that keep it true.

## 1. The registry - one authoritative writer per axis

| artifact | key | OWNS (authoritative) | DERIVES | status |
|---|---|---|---|---|
| `governance/RULER_BLIND_SHEET_20260917.csv` (ANCHOR-1 input) | item_id (sheet-local) | nothing (raw single-coder input) | - | INPUT ONLY - never cite as a value source |
| `governance/F11_ANCHOR_REVIEW_20260923.csv` + `F11_OWNER_RULING_MAP_20260922.csv` | item_id | the adjudication record | - | evidence for the consolidation |
| `governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv` (**ANCHOR-3**) | `item_id` | **content_type, discipline, extraction_type** (`*_final`) | - | FROZEN, sha256 `29393d5f...`, tier human-mixed+llm-attested, RELATIVE-ONLY (D-337) |
| `governance/ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` (**ANCHOR-4**) | `item_id` | **depth** (EMPTY until the freeze) | CT / DISC / FORM from ANCHOR-3 `*_final` | instrument, generator `scripts/consolidate_anchor4_context.py` |
| `governance/ANCHOR4_DEPTH_PREDICTION_KEY_20260924.json` | `item_id` | the pre-registered prediction set + the corpus `fb_id` bridge | - | **NEVER shown to a coder** |
| `governance/gold_4axis.jsonl` | `fb_id` | corpus axis values (234 with depth, 132 human-derived) | - | reference, ADVISORY |
| `governance/depth_vote_checkpoint.jsonl` | `fb_id` | 3-voter depth consensus (996 rows) | - | reference, ADVISORY, RELATIVE-ONLY |

**Join contract.** `item_id` (e.g. `R001`) is the anchor-family primary key. `fb_id` (64-hex, content-addressed)
is the corpus-family primary key. They are different identifier spaces: a direct join is 0/150. The bridge is
recorded explicitly in the prediction key - 22/150 rows carry a real `fb_id` (20 via
`remaining_verification_audit.csv`, 2 via `ANCHOR2_BLIND_SHEET_20260920.csv`), and 10 further rows have a
NAME-ONLY join that is labelled `identity UNVERIFIED` and must never be pooled with the verified ones.

## 2. What the consolidation changed (the numbers, derived not typed)

`scripts/consolidate_anchor4_context.py --apply` refreshed, on all 150 rows:

| column | cells refreshed | of 150 |
|---|---|---|
| `CT (1-7)` | 56 | 37 % |
| `DISC (1-62)` | 62 (28 blank -> filled, 34 superseded) | 41 % |
| `FORM (1-4)` | 142 | 95 % |
| **total** | **260 of 450 context cells (58 %)** | |

After: CT blank 0, DISC blank 0, FORM blank 5 (the 5 rows where ANCHOR-3 legitimately has no
extraction_type), DEPTH blank 150/150 (still blind), item_id set == ANCHOR-3 item_id set, 0 cells differ
from the upstream `*_final` values. A pre-refresh byte copy is kept at
`governance/backups/ANCHOR4_DEPTH_BLIND_SHEET.PRE_CONTEXT_REFRESH_20260924.csv`.

Why `FORM` moved on 142 rows: ANCHOR-3 canonicalised the ruler's raw spellings through axis-tagged aliases
(`casual mechanism` -> `causal_mechanism`), so the sheet had been showing 142 rows of SUPERSEDED label text -
the single largest source of contamination in the instrument.

## 3. The anti-drift machinery (this is the part that makes it stick)

1. **One writer per field.** ANCHOR-3 owns three axes; ANCHOR-4 derives them. The generator is the ONLY
   writer of those three columns, and it says so in its docstring. The previous build was a second writer.
2. **A manifest as the config surface** (`governance/ANCHOR4_MANIFEST_20260924.json`): every path, the
   upstream column names, the sha256 of the sheet and of the key, the provenance tier, allowed/forbidden
   uses, the bound, and the verify/regenerate commands. No path or threshold is hardcoded in the script (C12).
3. **A machine guard with a proven failure mode**: `python3 scripts/consolidate_anchor4_context.py --check`
   exits 1 on (a) any context cell differing from ANCHOR-3, (b) item_id set mismatch or duplicates,
   (c) a non-blank DEPTH cell (the sheet stopped being blind), (d) a key item_id absent from the sheet,
   (e) a sheet sha256 that disagrees with the manifest. The guard was TESTED BY DRIFT INJECTION, not assumed:
   flipping one cell made it exit 1 with the exact cell named, and restoring it returned exit 0.
4. **Idempotency by test** (BUG-418 rule): `--apply` was run twice; the second run reported
   `cells refreshed: none (already in sync)`. The first version of the script FAILED this test in a subtle
   way - its second run erased the change record (`cells_refreshed: {}`) - which is recorded below and fixed.
5. **Counts are derived, never typed** (BUG-402 rule): the manifest's `cells_refreshed` is computed by
   DIFFING the backup against the sheet (`diff_against_backup`), so it cannot drift from the artefacts.
6. **Blinding is structural**: the `fb_id` bridge and the 12 pre-existing depth references live in a
   sidecar KEY, not on the sheet. Putting `fb_id` on the coding sheet (as earlier proposed in BUG-420)
   would have let a coder look the row up in `gold_4axis.jsonl` and would have destroyed the anchor.
7. **The key is a PRE-REGISTERED PREDICTION SET, not a label source.** R109 (`cross-domain`) and R142
   (`domain`) are human-derived (`p5:human-d2615`); 10 further rows (R016, R053, R075, R080, R088, R093,
   R106, R111, R114, R137) have advisory 3-voter consensus values with 2/3 reliable voters. After the blind
   coding freezes, disagreement on those rows is a direct measurement of the advisory references' error rate
   on this row family - the thing no one has ever measured. They are NOT to be read while coding.

## 4. The plan for finishing the depth axis

| step | act | gate |
|---|---|---|
| 0 | context consolidation + guards | **DONE** (this document, generator, manifest, key, guard) |
| 1 | declare the 4 depth classes in a config surface (BUG-416) and repoint the menu check + the rubric at it | C12 config-first; the coder must not work from prose |
| 2 | blind coding of all 150 rows (DEPTH, conf_depth, note_codes, reviewer, date) from the rubric only | owner |
| 3 | a SECOND coder on the same 150, blind | mirror the ANCHOR-3 pattern: 2 model coders (claude + kimi) + owner adjudication, because the F-11 second-HUMAN gate is UNSATISFIABLE and ANCHOR-3 already accepted this provenance tier |
| 4 | measure agreement, adjudicate, freeze; record sha256 + tier in a manifest | tier will be human-mixed+llm-attested -> RELATIVE-ONLY (D-337) |
| 5 | unseal the prediction key and score the advisory references against the frozen anchor | first honest error rate for depth on this family |
| 6 | D274f test-retest of 30 rows after >= 2 weeks | single-coder ceiling |
| 7 | only then: the D2577 4-way depth head may be trained/evaluated against the anchor | D274d: no S4 training on the current labels before this |

**Not permitted at any step:** editing `CT/DISC/FORM` by hand (they are derived; run the generator),
reading the prediction key while coding, adding depth values to the sheet before the freeze, or treating a
single-coder result as truth.

## 5. Self-review findings recorded from this consolidation

- MY DEFECT (fixed): the first `--apply` recorded `cells_refreshed` correctly, but a second (no-op) run
  overwrote it with `{}` - a no-op path erasing evidence, the BUG-418 class one level down. Fixed by
  deriving the record with `diff_against_backup` and never overwriting a populated record with an empty one.
- MY DEFECT (fixed): the first `build_key` only carried depth references reachable through `fb_id`, silently
  dropping the 10 advisory rows reachable only by name. Fixed by adding a clearly separated
  `depth_ref_namejoin*` field with `identity UNVERIFIED` in its source string.
- MY DEFECT (process): during measurement I reported "28 of the 150 rows have NO discipline" from the
  ANCHOR-4 sheet's copied column instead of from ANCHOR-3, the authoritative artifact. The truth is
  150/150 disciplines with tier owner-adjudicated 80 / human-ruled 42 / owner-supplied 28. This was the
  fifth instance of the same class this session: a claim about a missing signal that was measured on the
  wrong artifact. Filed as BUG-422.
- Counter discrepancy explained: an ad-hoc scan said 265 stale cells, the generator said 260. The 5-cell
  difference was the FORM rows whose upstream value is legitimately blank (already blank in the sheet). The
  generator's number is authoritative because there is now exactly ONE counter. The ad-hoc scan is deleted.
