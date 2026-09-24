# ANCHOR-4 DEPTH — owner pass: evaluation receipt (2026-09-24)

**Evaluated artifact (owner drop-in, NEVER rewritten):**
`governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv`
sha256 `be1a39e04c378af972bbb321f71c262eaca3252ffe72d5eb179867a6097d6fcb`, 203506 bytes, 150 rows x 16 cols,
CRLF line endings, no trailing newline, no embedded newlines. Write-locked in `config/human_instrument_locks.yaml`
(whole file + DEPTH/conf_depth/note_codes/reviewer/date).

## 1. Verdict: COMPLETE and MENU-CONFORMANT
| rubric requirement (ANCHOR4_DEPTH_RUBRIC lines 12-13) | measured |
|---|---|
| `DEPTH (1-4)` filled | **150/150**, all in {{1,2,3,4}} — 0 out-of-menu, 0 blank |
| `conf_depth` (1 guessing / 2 likely / 3 certain) | **150/150**, all in {{1,2,3}} |
| `reviewer` | 150/150 = `human` |
| `date` | 150/150 = `13.09.26` |
| `note_codes` | **0/150 (empty)** — rubric makes it optional ("free text for any hard case") |

DEPTH distribution: **3 domain 66 (44%) | 4 specialized 44 (29.3%) | 2 cross-domain 33 (22%) | 1 universal 7 (4.7%)**.
conf_depth: 2 likely 76 | 3 certain 53 | 1 guessing 21.

The four classes were coded against the CLOSED menu now declared in `config/depth_classes.yaml` (BUG-416 closure) —
every value is a legal member; nothing had to be coerced.

## 2. Pre-registered scoring (ANCHOR-4-KEY unsealed for this — see §5)
**Owner vs the 12 pre-registered reference rows: 9/12 agree (75%).**
- human-derived refs (`gold_4axis`, p5:human): **2/2** — R109 cross-domain→2 ✓, R142 domain→3 ✓
- llm-advisory name-joins (identity UNVERIFIED): 7/10. Differ: R016 ref=universal vs owner=3 (conf 3);
  R093 ref=cross-domain vs owner=3 (conf 1); R137 ref=domain vs owner=4 (conf 3).
- Only 2 of the 12 are identity-verified joins.

**Owner vs the 3-voter depth advisory (`depth_vote_checkpoint.jsonl`): 8/11 = 72.7%** on a name join, 1/1 on the
single available fb_id join. But the advisory is **joinnable on only 17/150 rows** (11 with a usable depth) —
94% of the cohort has no advisory counterpart. The incumbent depth reference therefore **cannot validate this
cohort**; it is the same structural defect as the domain side (216-row cohort vs 150-row anchor, intersection 2).
A frontier second coder is the only viable second instrument.

Interpretation: two independent machine references land at ~73-75% agreement with the owner. The disagreement is
NOT evidence of owner error — 10 of 12 references are unverified joins, and 94% of the advisory corpus cannot be
joined at all. It is a statement about the reference quality, and it is the first honest depth number this family has.

## 3. Blinding + leakage checks
- **D282 (scope is depth, never content_type): PASS.** DEPTH is not determined by the `CT (1-7)` context column —
  `principle` spreads 5/27/39/18 across D1-D4; only `tool instructions` is degenerate (8/8 D4, semantically expected).
- **FORM x DEPTH: no degenerate mapping.** `normative heuristic` and `descriptive model` each span D1-D4.
- Blinding declaration: the owner's pass does not reproduce the advisory values (7/10 on unverified joins), which is
  the expected signature of NOT copying them. Owner to confirm no gpt-oss labels / consensus / gold_4axis / key were used.

## 4. Anomalies found (all recorded, none destroys the labels)
1. **The tracked `ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` on disk is a PARTIAL save of the same pass**: DEPTH filled
   on R001-R018 only (18/150), reviewer/date on all 150, and `conf_depth` corrupted to the word `domain` on R149/R150.
   The 18 coded rows agree with the drop-in **18/18** -> same pass, interrupted. Byte-copy preserved at
   `governance/backups/ANCHOR4_DEPTH_BLIND_SHEET.OWNER_PARTIAL18_UNCOMMITTED_20260924.csv`. BUG-432.
2. **date `13.09.26`** precedes the sheet's own creation (2026-09-23) and today is 2026-09-24. OWNER QUESTION: is the
   pass really from 13 Sep (carried in from an earlier sheet) or is the date a typo?
3. **`note_codes` empty on all 21 conf=1 ("guessing") rows.** Uncertainty is concentrated on D3: conf=1 x D3 = 14/21.
   The D2/D3 boundary is the dispute core; the second coder and adjudication should sample that boundary deliberately.
4. **Context-column defect (BUG-431)**: the `FORM (1-4)` column in this sheet holds `extraction_type_ruler_raw`
   (owner's verbatim spellings, 10 distinct values, only 3 strictly on-menu), not the `extraction_type_final` menu the
   rubric declares. Did not affect DEPTH coding (D282 check passes) but the column is unusable as a code.

## 5. Governance effects
- **ANCHOR-4-KEY was UNSEALED for §2** (read-only; the key file itself is untouched). Declared so this peek cannot be
  laundered later as a pre-registered result: after this date the key is scorable, not pre-registered.
- The owner's drop-in is write-locked; the partial state is backed up; neither the ANCHOR-4 sheet nor any F-11
  instrument was modified by this evaluation (session plan `will_not_touch`).
- **Not yet a freeze.** A freeze needs a second coder (frontier pack) + owner adjudication of the dispute set, then
  sha256 + provenance tier into a manifest. This receipt makes the owner's pass coder-A evidence, not anchor truth.

## 6. Context integrity — CORRECTION to §1 (found after §1 was written)
The tracked sheet the owner's drop-in descends from was **clobbered at 13:39 by an out-of-band writer** back to the
PRE-consolidation content (committed consolidated at 10:40, e7da35b). Measured consequences:
- the coding context the owner saw was **260/450 context cells stale** (142 FORM / 62 DISC / 56 CT) vs ANCHOR-3;
- the judged row text is **identical except R147's DEFINITION** (1 row);
- `CT`/`DISC`/`FORM` staleness cannot legalise a depth value under D282 (scope, not content_type) and the measured
  leak check passes, so **the labels stand** — but the staleness must be declared in the freeze manifest.
Verified by two independent fail-closed guards, which is why this was caught at all:
`consolidate_anchor4_context.py --check` -> 5 drifts including `DEPTH already filled on R001 - the sheet is no longer
blind` and `sheet sha256 b47114d4 != manifest 14ee0d7a`; `verify_anchor_family_registry.py` -> blank-count 150 declared
vs 132 measured. New ids: BUG-433 (the clobber) and BUG-432 INSTANCE 2 (staleness). Clobbered bytes preserved at
`governance/backups/ANCHOR4_DEPTH_BLIND_SHEET.OWNER_PARTIAL18_UNCOMMITTED_20260924.csv`.

## 7. Supersession (2026-09-24 15:23) — the owner fixed the date; this receipt stays bound to rev 1
`governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` was edited **in place** after §1–§6 were written:
- rev 1 sha256 `be1a39e04c378af972bbb321f71c262eaca3252ffe72d5eb179867a6097d6fcb` — the bytes this receipt was measured
  on, committed byte-exact at 075ae65;
- rev 2 sha256 `bc1cc956cbd07fd7b3d622a42d9f6f96f5fe9584fe6cb9252c73a3cda7e150e4`, mtime 2026-09-24 15:23:32,
  **same byte count** 203506.

Cell-level diff rev 1 → rev 2: `date` 150 cells `13.09.26` → `24.09.26`. **Nothing else.** `DEPTH (1-4)` `e35247a8…`,
`conf_depth` `c9047a09…`, `note_codes` `5c7c9765…` and `reviewer` `3adf424c…` column hashes are byte-identical to the
ones locked against rev 1, and `scripts/check_human_instruments.py` reports exactly one rewritten column, `::date`.

**Consequences.** §1 (COMPLETE, menu-conformant), §2 (9/12 vs the pre-registered key; 2/2 human-derived), §3
(blinding + D282) and §4 (anomalies) all **STAND unchanged** — they rest on the label columns, which did not move.
What does change: the instrument's `date` is now the correct coding date, so the D274f 30-row test-retest clock runs
from **2026-09-24**. Which hash is bound where: the write lock now binds rev 2 and keeps rev 1 as a declared
`superseded` revision; this receipt deliberately documents rev 1. The outstanding owner question about the date is
answered (it was a carried-over date, now corrected).
