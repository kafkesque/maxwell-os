# ANCHOR adjudication workbook - NORMALIZATION RECEIPT (2026-09-25)

The owner's filled adjudication workbook was normalised. **No judgement was changed.** What changed was
encoding, separator, and 8 truncated labels; the owner's original strings are preserved column-by-column in
`domains_final_raw`, so nothing they typed is lost.

- source encoding detected: **mac_roman** (the file as saved was Mac Roman; one 0xCA byte broke UTF-8 readers)
- byte-exact raw backup: `backups/anchor_adjudication_workbook_20260924.OWNER_RAW_20260925.csv` sha256 `c49f6395db4460b7...`
- normalized file: `governance/anchor_adjudication_workbook_20260924.csv` sha256 `f2778a488610cbf1...`
- fix log: `governance/anchor_adjudication_fixlog_20260925.csv` (one row per change, statuses FIXED / UNRESOLVED-OWNER-RULING / BLANK-AS-SUBMITTED)
- written: 2026-09-25T13:12:44+00:00 | rows 148 | cells rewritten 9

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

---

## REV 2 ADDENDUM (2026-09-25 15:11) - owner re-saved; normalisation re-applied

- The owner's cloud editor saved over the normalised file at `15:02:11` (BUG-443), restoring a Mac Roman 22-column state whose only content difference from the raw submission was **R024 = `business operations`** - **the owner's own fix**, matching the canonical label. That revision is preserved byte-exact as `backups/anchor_adjudication_workbook_20260924.OWNER_REV2_20260925.csv` sha256 `c49f6395db4460b7c8f8d72f15172c2ba82824bca30df8ce41f25ae61406c179`; rev 1 (as submitted) is `...OWNER_REV1_20260925.csv` sha256 `d6413802bb849319933e1259febdea1aa6e179439c79b7136243c84e4e7c489d`. `OWNER_RAW_20260925.csv` is the **rotating pre-apply snapshot** (currently = rev 2).
- Normalisation re-applied to rev 2: **9 cells** rewritten (not 10). The declared `business,operations` -> `business operations` replacement in `config/anchor_workbook_fixes.yaml` is now **UNUSED** because the owner's own fix already landed; it is kept in the map deliberately (it is the declared rule that catches the defect if it ever reappears in a future drop-in).
- Post-normalisation statements hold unchanged: 148 rows x 25 cols, `domains_final` 147/148 (blank R140), `depth_final` 145/148 (blank R070/R080/R130), `primary_domain` 147/148, `owner_date` 25.09.26 x148, off-menu tokens remaining: R040 `emerging` (UNRESOLVED, owner ruling owed).
