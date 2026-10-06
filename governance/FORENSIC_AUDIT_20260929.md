# FORENSIC AUDIT — anchor→evidence bridge (2026-09-29)

> Read-only audit before any Phase-0 triage implementation. No pipeline writes,
> no generation. Findings below are the gate: **the triage cannot run faithfully
> yet**, because the evidence layer itself is broken.

## Method
Built `governance/frontier_audit/anchor_evidence_bridge.json`: every anchor
(150 via `cells_to_classify.csv`↔`temp/ruler_input_20260923.jsonl`, 60 via
`temp/_extra60_fulltext.json`↔`knowledge pipeline/maxwell.db` `fbs`) joined to its
`evidence_passages`, `source_text`, `is_summary`, `fb_id` by name.

## Findings (severity-ordered)

1. **`source_text` is 100% contaminated (208/208).** Every matched anchor's
   `source_text` begins with `[` — the "[book title] + definition echo" pattern
   (BUG-288). Not one raw verbatim source survives in the field. → The fidelity
   triage must **not** trust `source_text` as ground truth.

2. **Evidence truncation is systemic (188/210 anchors).** ≥1 `evidence_passages`
   entry ends mid-word (no terminal punctuation). R017 was the spot-check
   example; it is the norm, not the outlier. → Complete-sentence truncation
   repair is corpus-wide, not per-row.

3. **2 anchors have no evidence mapping (blindspots).** R135 (150 group) and
   R167 (60 group) fail name-join. → Triage would silently skip them.

4. **`is_summary` is all-false (0/208) — unreliable.** R025 is a known
   bibliographic blurb yet carries `is_summary=false`. → The flag cannot be used
   as a blurb/over-claim detector as-is.

5. **Workbook clobbering (recurring).** `REVIEW_WORKBOOK_210.csv` reverted to
   210 rows + all typos once this session (Dropbox/owner-instrument write, cf.
   BUG-500/BUG-528). Fixes were re-applied (→208 rows) but the writer is live.

6. **Confirmed drift anchors are the "thin evidence" class.** R013/R017/R025 each
   have exactly **1** passage, truncated, contaminated source_text.

## Consequence for the plan

Phase 0 triage (definition-vs-evidence NLI) is **blocked on evidence**, not on
the meter. The correct next step is to **recover raw verbatim source from
stage0/stage1 for the 208 anchors first** (Phase 1's `source_text` + truncation
repair pulled forward), *then* triage. Running NLI now would score definitions
against truncated passages and contaminated source_text — a meter on a broken
floor.

## No breaks / cascades / conflicts observed
The bridge is a pure read-join; it writes only `anchor_evidence_bridge.json` and
touches nothing else. No pipeline, config, or registry was modified.

## Next critical steps (ranked)
1. Resolve R135 + R167 name mismatches (recover their fb_id/evidence).
2. Recover raw `source_text` from stage0/stage1 for the 208 (kills BUG-288 at the seed).
3. Re-truncate evidence to complete sentences (kills the 188).
4. Harden `is_summary` (R025 class).
5. Then run the NLI triage over the 208 → keep / keep-and-repair / drop.

## Recovery results (D-2702) — appended 2026-09-29
Raw source recovery ran READ-ONLY (never wrote maxwell.db or the workbook). 447/488 passages recovered verbatim
(91.6%), 35 abstractive, 6 orphan-segment, 0 empty. 174 anchors full, 25 partial, 7 zero.
The 7 zero-recovery anchors split cleanly: 4 ORPHAN-SEGMENT (R003/R088/R105/R206 — their single source_segment sits
among the 223 orphaned from the current chunk checkpoint) and 3 ABSTRACTIVE (R082/R137/R163 — S2 rewrites; R163's
passage even leads with a book-title header, the blurb-drift class). 223/4660 source_segments are orphaned in
stage1_chunk/latest (worst R141=141); all 426 source MD files are intact so fallback recovery holds.
R135 + R167 RESOLVED: both were name-join blindspots, not missing evidence. R135 carried a double-space; R167 had the
off-menu disc label "emerging" leaked into the name (canonical = "Innocent Brand Identity Through Organic Development").
R167 is QUARANTINE status — flag for the keep/repair/drop triage.
Two schema findings carried forward: evidence_passages vs evidence_passages_shown hold DIFFERENT content, and
source_text's `[book title]` prefix is arbitrary (R141 prefixes GEB while primary_source = "AI and machine learning for
coders"). No breaks/cascades: recovery is a pure read-join that emits only anchor_raw_source_recovered.json.
