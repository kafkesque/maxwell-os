# Re-chunk Execution + Duplicate-Book Forensic Audit (D-2704, 2026-09-29)

## Executed re-chunk
- Driver: `temp/_rechunk_driver.py` — redirects stage1 input to `stage0_convert/t11` and output to a
  fresh run-id `stage1_chunk/rechunk-20260929/`, at the CURRENT pipeline commit (D2485). Live `latest`
  and `t11` checkpoints were NOT touched.
- Result: **300,270 segments**, 2,367 exact-duplicate chunks skipped, 0 duplicate segment_ids.
- Timing: ~2.5 min for 940 books (30-book smoke = 2.8s).

## Verification (decisive)
| metric | result |
|---|---|
| needed source_segments (208 anchors) | 4,660 |
| resolved in fresh checkpoint | 4,660 / 4,660 |
| orphan segments recovered (missing-in-latest) | 223 / 223 |
| still missing | 0 |
| segment count vs t11 (D2370) | identical (300,270) → chunker stable |

## Duplicate-book finding (same author + title, different source_path)
- Normalizing `book_metadata.jsonl` (962 records) on (author, title) with Anna's-Archive/hash-suffix
  stripping yields **24 groups** of 2–3 files each that are the SAME book.
- These files contribute ~12,064 segments (~4% of corpus). Exact SHA-256 dedup caught 2,367
  byte-identical cross-book chunks; ~6,000 near-duplicates survive because the 2–3 source files differ
  in formatting (e.g. `by Author` vs `-- Author -- hash -- Anna's Archive` vs `_clean`).
- Impact: corpus bloat + FB evidence double-counting + domain misattribution (some dupes sit in TWO
  domain folders, e.g. Blink in DOMAIN 0 and DOMAIN 5).

## Forensic audit findings (F1–F5)
- **F1 (root cause of 223 orphans):** run-id mismatch. `stage1_chunk/latest` (Aug 4) is stale and missing
  223 segments; `t11` (Aug 18) and the fresh `rechunk-20260929` both resolve all 4,660. Downstream must
  point at the fresh checkpoint, not `latest`.
- **F2:** 24 duplicate-book groups (above).
- **F3:** dedup is global first-wins → a chunk shared by 2 books is attributed to whichever book iterates
  first (alphabetical/arbitrary). Provenance ambiguity for cross-book quotes/definitions.
- **F4:** exact-only (SHA-256) dedup misses near-duplicates (formatting drift).
- **F5:** pipeline_commit drift — `t11` was built at D2370, config is now D2485. The re-chunk closes this.

## No cascade / crash risk from this work
- Fresh run-id dir (no clobber), atomic `safe_write` (tempfile + fsync + os.replace), live checkpoints
  and the production DB untouched. Pointer flip is a separate, gated step (not performed this turn).
