# Maxwell OS v2.0 — Decision Log
> **Append-only.** Newest first. Hash-chained.

---

## D2000 — v2.0 Architecture (2026-07-18)

**Summary:** Maxwell OS restarts with a clean v2.0 codebase. v1 archived in `archive/maxwell_os_v1/`. Architecture v3.0 adopted for pipeline.

**Key decisions carried forward from v1:**
- R5: Generator ≠ Verifier (different model families)
- R7: temp=0.0 on all generation
- R14: Schema stamps on all persistent output
- D150: Max 5 domains per FB
- D316: Multi-label classification
- D1057: Lazy-load OMLX models per stage
- D1058: Jargon decontamination

**New for v2.0:**
- Pipeline: 6 stages (was 8)
- Storage: SQLite + Parquet (was Anytype-first)
- Classification: SALSA inline (was 13 separate scripts)
- Folder: `pipeline/` not `tools/`
- Goal: Triad proof before scale (3 books → 10 FBs → verify → THEN scale)
- Knowledge layer defined BEFORE pipeline implementation
- Pydantic Literal types at write boundary — structural validity, not filter-based

**Files:** All of `maxwell os 2.0/`

---

## D2001 — v1 Archived, Not Deleted (2026-07-18)

**Summary:** Full v1 project preserved at `archive/maxwell_os_v1/`. No files deleted. Accessible for reference. 19,770 legacy FBs preserved. Anytype integration scripts preserved. All decisions and governance docs preserved.

**Rationale:** Clean workspace without data loss. If v2.0 needs a pattern from v1, it's in the archive.

---

## D2002 — Stress Test Results: Pipeline v2.0 End-to-End (2026-07-18)

**Summary:** Full 6-stage pipeline tested on 14 diverse books (307 segments) from 6 domains. All stages completed successfully. 14 FBs generated, 4 PASS, 10 FLAG (BORP violations — expected for single-source clusters). Full DB + Parquet commit.

**Test Configuration:**
- Books: Design (4), AI/Computing (4), Data (2), Programming (1), Self-Help (1), Cyrillic edge case (1), Systems (1)
- Models: Qwen3-Coder-30B (generator), Phi-4-mini-8bit (verifier), nomic-embed-text (embeddings)
- SALSA: Inline classification via prompt — 1 label error in 14 FBs (93% valid at first pass)
- API: OMLX with `sk-maxwell-local` key on port 11435

**Stage Results:**
| Stage | Input → Output | Time | Notes |
|-------|----------------|------|-------|
| 0 | 852 books → 849 valid .md | <1s | 3 books skipped (<100 bytes) |
| 1 | 849 .md → 2,314 segments (307 test) | 80s | Section-aware chunking + SHA-256 exact dedup |
| 2 | 307 segments → 188 principles | 13min | 31 LLM batches, ~26s avg per batch |
| 3 | 188 principles → 14 clusters | 6s | HDBSCAN, 78 noise, cohesion 0.73 |
| 4 | 14 clusters → 14 FBs | 3.5min | SALSA inline, 1 label error, 12 cross-domain |
| 5 | 14 FBs → 4 PASS + 10 FLAG | 0s | BORP ≥2 gate (10 single-source), no LLM factual |
| 6 | 14 FBs → SQLite + Parquet | 1s | FTS5 table, 41KB parquet snapshot |

**Bugs Found & Fixed During Test:**
1. `pipeline_paths.py`: .md not in supported extensions for stage 0
2. `stage1_chunk.py`: Variable shadowing `chunk_text` function with loop var
3. `stage1_chunk.py`: Shrink guard blocking incremental runs
4. `omlx_call.py`: Typo `call_omxl` → `call_omlx`
5. `omlx_call.py`: Missing API key header (`sk-maxwell-local`)
6. `pipeline_paths.py`: Wrong model name (Qwen3.6 → Qwen3-Coder)
7. `stage4_merge.py`: `jargon` field returned as dict, not string
8. `stage4_merge.py`: Missing `Optional` import
9. `stage6_commit.py`: SQLite insert failed on dict-type fields
10. `stage6_commit.py`: Parquet export failed on dict-type fields

**Assessment:** Pipeline architecture is sound. All 10 bugs were implement-level, not design-level. No changes needed to 6-stage architecture or schema contracts. Ready for production run on full book corpus.

**Remaining:** T1.17 (Maxwell human review of 14 FBs)

---

## DECISIONS CARRIED FROM v1 (for reference)

| ID | Date | Decision |
|----|------|----------|
| R5 | 2026-06-14 | Generator ≠ Verifier |
| R7 | 2026-06-14 | temp=0.0 on all generation |
| R14 | 2026-06-14 | Schema stamps on all output |
| D150 | 2026-06-15 | Max 5 domains per FB |
| D316 | 2026-06-18 | Multi-label locked |
| D1057 | 2026-07-17 | Lazy-load OMLX models |
| D1058 | 2026-07-17 | Jargon decontamination |
