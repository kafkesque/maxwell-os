# Chunk+dedup A/B test — results & re-evaluated strategy (D-2705, 2026-09-29)

Deterministic, local, no-LLM A/B of the three "HIGH" candidates against current S1.
Raw data: `temp/ab_dedup_results.json`. Baseline = fresh `stage1_chunk/rechunk-20260929/`
(300,270 segments, exact SHA-256 dedup).

## Candidate 3 — near-dedup (norm_ws / norm_punct) + book canonicalization
| arm | what it collapses | groups | redundant |
|---|---|---|---|
| A baseline (exact SHA-256) | byte-identical text | 2,367 (prev run) | — |
| B norm_ws (lowercase + collapse whitespace) | linebreak drift | 7 | 7 |
| C norm_punct (+ strip punctuation) | typographic variants (`'`vs`’`, `"`vs`“”`, `–`vs`--`) | 333 | 334 |

- **Precision = 100%** on sampled arm-C collapses: every pair is the same sentence differing only
  in curly-vs-straight quotes / dash style, same book pair (e.g. "365 habits" vs "[Laurel_Saville…]").
- **No-loss violation: 8 of 4,660 needed segments would be removed** by arm C (non-canonical
  members) → would orphan 8 FB evidence references unless a segment_id→canonical REMAP is shipped.
- **Book canonicalization: 24 same-author/title groups, but only ~182 near-dupes** (not ~6,000 as
  first estimated). Exact dedup already collapses byte-identical content across the 2–3 files; the
  surviving chunks have DIFFERENT window boundaries (different editions/formatting), so they don't
  textually overlap. Canonicalization is LOW value; heading-alignment (below) is the better fix.

## Candidate 2 — parent-child IDs
- Verified `segment_id == sha256(text)` exactly (0 mismatch) → parent-child is **purely additive**
  (add a `parent_id = sha(section_heading | source_book)` field); flat segment_id + 4,660 resolution
  are untouched. No regression. BUT parent granularity is crippled by the heading bug (below).

## Candidate 1 — contextual retrieval
- Blocked by the heading bug: `section_heading` is empty on 94.55% of segments, so "context" would
  degrade to book-title only (weak). Not A/B-able meaningfully until the heading bug is fixed.

## ⚠️ Headline finding — the chunker's structural feature is DEAD (bug)
- **96.3% of books (905/940) contain markdown headings (83,880 heading lines total), but the current
  pipeline populates `section_heading` on only 5.45% of segments.**
- Root cause (confirmed in code): `stage1_chunk.py` calls `clean_markdown()` FIRST, which strips
  `#` markers (`text_cleaner.py:63` `re.sub(r'^#{1,6}\s+','')`); then `split_on_headings()` runs on
  heading-free text, so `SECTION_HEADING_RE` never matches → one empty-heading section per book.
- Impact: chunks are 300-word sliding windows over the whole book, NOT section-aligned (topical
  bleed across section boundaries); `section_title`/`section_heading` empty → contextual retrieval
  and parent-child IDs both crippled.

## Re-evaluated future-proof chunk + dedup strategy
1. **FIX the heading-ordering bug (highest leverage, deterministic, $0).** Split on headings FIRST
   (capture `##` markers), THEN clean each section body. Unlocks section-aligned chunks + contextual
   retrieval + parent-child in one move.
2. **Keep exact SHA-256 dedup** (it's doing its job: near-dupe residual is ~0.1%).
3. **Defer near-dedup** (arm C): only ~334 segments, and it orphans 8 references without a remap —
   not worth the cascade until (1) lands and re-chunk re-aligns duplicate editions.
4. **Defer book canonicalization**: 24 groups but ~182 near-dupes; (1) will align editions better
   than a filename-merge.

## Next critical steps (consequential order)
1. Implement + smoke A/B the heading-ordering fix (isolated re-chunk of a sample; measure heading
   coverage 5.45%→~90%+ and chunk-boundary alignment) — DO NOT swap live until verified.
2. Then re-chunk full corpus with the fix; rebuild the segment_id→FB remap; re-verify 4,660 anchors.
3. Then contextual-retrieval A/B (now meaningful) via `retrieval_benchmark`.
4. Then classify 150 locked anchors' primary_domain (closed_menu_v5).
5. Owner-ratify DROP(13)+QUARANTINE(15)+re-ground(8).
