# Chunking Market Research & Re-Chunk Verification (D-2703, 2026-09-29)

## Research verdict: KEEP current chunker (no rip-and-replace)
Maxwell stage1_chunk.py = clean_markdown -> normalize_paragraphs(30-250w) -> split ## headings
-> 300w/50-overlap fixed chunks -> SHA-256 exact dedup. This is a structural+paragraph-aware
hybrid, which the best available evidence says is the SOTA sweet spot.

Sources:
- Vectara NAACL 2025 (peer-reviewed, only study in space): fixed-size chunking
  CONSISTENTLY outperforms semantic chunking (doc/evidence retrieval + answer gen).
- Denser.ai (2026): with late chunking, fixed-window ~= semantic.
- Firecrawl (2025): RecursiveCharacterTextSplitter best at ~400 tokens (88-89% recall);
  Maxwell's 300 words ~= 400 tokens is in-range.
- MDPI Bioengineering (Nov 2025): adaptive/topic-boundary 87% vs fixed 13% (niche clinical).

Optional future enhancements (WATCH, not blockers):
1. Contextual retrieval (Anthropic): prepend section heading + book to chunk pre-embed.
2. Late chunking (Jina): embed-then-pool (bge-m3 supports 8192 tokens).
3. Parent-child / small-to-big: stable parent ids (also mitigates orphan risk).

## Re-chunk verification: WORKS
223 orphan source_segments caused by a STALE checkpoint. Re-chunking current MD with
current chunker reproduces every orphan segment_id byte-for-byte:
- R003 / R088 / R105 / R206: 4/4 reproduce.
- R141: 141/141 reproduce across its 13 source books.

## Full triage: anchor_triage_v1.json
KEEP 45 | KEEP* 1 | FIX 130 | FIX/DROP 1 | DROP 13 | QUARANTINE 15 | WAIT-ORPHAN 3
Key: DROP=noise_drop(13); QUARANTINE(15); re-ground=abstractive causal/empirical(8);
WAIT-ORPHAN(3)=R003/R088/R105; and 150 locked anchors need primary_domain classification.
