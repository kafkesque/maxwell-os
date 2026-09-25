# ANCHOR adjudication workbook - NORMALIZATION RECEIPT (2026-09-25)

The owner's filled adjudication workbook was normalised. **No judgement was changed.** What changed was
encoding, separator, and 8 truncated labels; the owner's original strings are preserved column-by-column in
`domains_final_raw`, so nothing they typed is lost.

- source encoding detected: **mac_roman** (the file as saved was Mac Roman; one 0xCA byte broke UTF-8 readers)
- byte-exact raw backup: `backups/anchor_adjudication_workbook_20260924.OWNER_RAW_20260925.csv` sha256 `d6413802bb849319...`
- normalized file: `governance/anchor_adjudication_workbook_20260924.csv` sha256 `cb7d75cbb5c786ee...`
- fix log: `governance/anchor_adjudication_fixlog_20260925.csv` (one row per change, statuses FIXED / UNRESOLVED-OWNER-RULING / BLANK-AS-SUBMITTED)
- written: 2026-09-25T12:55:55+00:00 | rows 148 | cells rewritten 10

## Rows the owner LEFT BLANK - declared, not filled

`domains_final`: R140
`depth_final`: R070, R080, R130

A blank is a fact about the review. Nothing automatic may fill it.

## Awaiting the owner

- `emerging` (off-menu, matches no canonical label by any defensible edit distance)

## The rule this pass adopts

**The FIRST domain token is the PRIMARY domain** (owner ruling 2026-09-25). It is now materialised in the
`primary_domain` column of every row, so the primary no longer has to be inferred from list order by whoever
reads this file next.
