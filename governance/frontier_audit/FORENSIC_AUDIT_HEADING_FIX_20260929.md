# Forensic Audit — Heading-Ordering Fix (BUG-594) Smoke A/B

Date: 2026-09-29
Scope: Isolated smoke A/B of the proposed "split-on-headings FIRST, then clean" fix.
Decision: D-2706 (verdict below).
Artifacts: `temp/_ab_heading_fix.py`, `temp/ab_heading_fix_results.json`.

## Verdict (one line)

**Do NOT ship the naive heading-ordering fix.** The fix mechanically works (heading
coverage 6.7% → 97.5%) but the captured headings are ~80% converter artifacts (calibre
`{...}` residue, DOIs, ISBNs, Anna's Archive hashes, title-page contributor names), and
the fix causes **58.1% segment_id churn** = a full downstream cascade for ~10–15% semantic
value. The current heading-blind 300-word sliding window is correct for the current corpus.

## Audit dimensions (F1–F7)

| # | Dimension | Finding |
|---|-----------|---------|
| F1 | root cause | CONFIRMED. `clean_markdown()` (`text_cleaner.py:63` `re.sub(r'^#{1,6}\s+','')`) strips `#` markers BEFORE `split_on_headings()` runs → `SECTION_HEADING_RE` never matches → one empty-heading section per book. |
| F2 | cascade | **58.1% segment_id churn** (only 41.9% of `sha256(text)` IDs survive). Re-chunk with the fix changes >half of all segment IDs → 4,660 + 208 + 150 locked anchors all reference old IDs → S1.3→S6 full re-run + anchor re-grounding. NOT a surgical patch. |
| F3 | field consumers | `section_heading`/`section_title` have **ZERO downstream consumers** (grep across `pipeline/`+`scripts/` → none outside `stage1_chunk.py`). Populating them is additive/safe from a consumer standpoint — but the boundary re-anchoring is NOT safe (F2). |
| F4 | hidden failure | **The captured headings are 80.5% converter artifacts** (3908/4856). The "96.3% of books have headings" stat overstates semantic availability — most of those 83,880 lines are DOI/ISBN/Anna's-hash/calibre residue. Real semantic fraction ≈10–15%. |
| F5 | bloat/mismatch | `section_heading` stores the raw `#` marker + calibre `{...}` residue (e.g. `'# What Others Have Said {#part0002.html_calibre_pb_0 .title}'`). `clean_markdown` does NOT strip `_CLEAN_SUBS` calibre residue (that lives only in `clean_evidence_passage`, D2471) → residue would leak into section metadata. |
| F6 | drift | `pipeline_commit` = git HEAD (memoized `get_git_commit`), fallback `v3.0-D2485`. Re-chunk records carry git hash, not the `D2485` label — provenance divergence (minor, by design). |
| F7 | blindspot | Heading detection has no semantic filter: DOIs (`00913367.2014.920283`), ISBNs (`0321934695`), Anna's Archive hashes, `{#...}` calibre attributes, title-page contributor names all match `^#{1,6}\s+`. |

## A/B evidence (60 books, 5,577 raw heading lines)

- heading coverage: **6.7% → 97.5%** non-empty (fix works mechanically)
- boundary violations: **0** (fixed bodies contain no raw `#` heading lines)
- unique headings captured: 4,856 (of 5,577 raw lines — remainder have empty bodies after clean)
- **segment_id churn: 58.1%** (overlap 41.9%)
- body-word delta: **−96,475** (heading text moves body → metadata; ~20 words/heading)
- artifact/semantic split of captured headings: **80.5% / 19.5%**; 43/60 books have ≥1 semantic heading

## Conclusion — strategic re-scope

The "dead heading splitter" (BUG-594) is a **latent bug that, when revived, surfaces a
deeper stage0 problem**: the calibre/Pandoc converter pollutes headings with residue. The
correct future-proof path is NOT a reorder — it is a **heading sanitizer** that strips
calibre `{#...}`/`.title`/`.title-page-*` attributes, DOIs, ISBNs, Anna's Archive hashes,
and page numbers, keeping only real semantic section titles. Only after sanitization can
structural splitting (and the contextual-retrieval / parent-child enhancements it enables)
be re-evaluated for value.

Until then: **KEEP current chunker** (300-word + 50-word overlap + exact SHA-256 dedup +
cluster-before-extract). This is consistent with the market research (Vectara NAACL2025:
fixed-size ≥ semantic chunking) and now additionally with the A/B (the "fix" adds garbage + churn).

## Next steps (re-scoped)

1. Heading sanitizer (strip calibre/DOI/ISBN/Anna's-hash from headings) — NEW task.
2. Re-evaluate structural splitting + contextual retrieval AFTER sanitization.
3. Defer segment remap (D-2707) — moot until a sanitized structural re-chunk is green-lit.
4. Carry-forward (unchanged): classify 150 locked domains; ratify DROP/QUAR/re-ground;
   file evidence_passages schema bug; mint registry snapshots.
