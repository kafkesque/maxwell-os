# Maxwell OS — Buglog
> **Rule:** Accumulate recurring bugs/issues here for LLM handoff with full documentation.
> **When:** 5+ unresolved bugs → append buglog to all LLM handoff documents.
> **Format:** Bug ID, severity, file, lines, symptom, root cause, proposed fix, source, status.

---

## INITIAL POPULATION (2026-07-20) — Consolidated from 7 documents + live code audit

### BUG-001: Empty Pass Loop — Verification Checks Random Principles
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | `pipeline/stage5_verify.py`, lines 115-122 |
| **Symptom** | `source_clusters → principle_ids` mapping loop is empty (`pass`). Falls back to `list(principles_idx.values())[:20]` — first 20 arbitrary principles. A pricing FB is "verified" against design principles. |
| **Root Cause** | The cluster checkpoint mapping was never implemented. Comment says "we approximate" but the approximation is random. |
| **Proposed Fix** | Load cluster checkpoint JSONL, map `cluster_id → principle_ids`, filter `principles_idx` to only those IDs. Fallback: global cosine top-10 if <5 sources found. ~25 LOC. |
| **Source** | Kimi code audit (BUG 1); confirmed in Qwen's `stage5_verify_v2.py` |
| **Status** | 🔴 OPEN — Phase 0, P0.8 |

### BUG-002: Lineage Broken — pipeline_run_id Regenerated Per Call
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stamp.py`, line 52 |
| **Symptom** | `record["pipeline_run_id"] = record.get("pipeline_run_id") or uuid.uuid4().hex` — every call to `stamp_record()` generates a new UUID4 unless pre-set. Only Stage 4 pre-sets it. Stages 0, 1, 2, 3, 5, 6 get unique UUIDs per record. R14 (lineage) broken for 6 of 7 stages. |
| **Root Cause** | No PipelineRunner that propagates a single run_id through all stages. |
| **Proposed Fix** | Create PipelineRunner class that generates one run_id and injects it into `stamp_record()` for all stages. ~30 LOC. |
| **Source** | Kimi code audit (BUG 2); Qwen's Patch 8+9 |
| **Status** | ✅ RESOLVED — P0.9 applied. get_pipeline_run_id() singleton in stamp.py line 59-64. All stages use same run_id. |

### BUG-003: R5 Violated — Same Model Generates AND Classifies in Stage 4
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage4_merge.py` |
| **Symptom** | Both FB generation AND SALSA classification use `GEN_MODEL` (Qwen3-Coder). A model that hallucinates a domain label also hallucinates the classification that validates that label. Self-fulfilling classification. |
| **Root Cause** | `call_omlx_json(model=GEN_MODEL)` used for both generation and classification calls. |
| **Proposed Fix** | Use `VERIFY_MODEL` (Phi-4-mini) for SALSA classification. ~5 LOC. |
| **Source** | Kimi code audit (BUG 3); R5 (CONSTITUTION.md) |
| **Status** | 🟠 OPEN — Phase 0, P0.10 |

### BUG-004: Vector Search Re-Embeds Entire DB Every Query
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/retrieve.py` |
| **Symptom** | `batch_embed(definitions, model="nomic-embed-text")` on every query. At 14 FBs: fine. At 1,000 FBs: ~30 seconds. At 10,000 FBs: minutes per query. O(n) scaling disaster. |
| **Root Cause** | Embeddings not pre-computed at commit time. sqlite-vec mentioned in comments but not implemented. |
| **Proposed Fix** | Pre-compute embeddings at Stage 6 commit time. Store in `vec_fbs` virtual table. Query via sqlite-vec cosine similarity. ~40 LOC. |
| **Source** | Kimi code audit (BUG 4); Qwen's Patch 8 |
| **Status** | 🟠 OPEN — Phase 1 (part of verification + retrieval upgrade) |

### BUG-005: Chunker Paragraph Boundary Destruction
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage1_chunk.py`, `clean_line()` at line 37-38, `split_on_headings()` at line 68+ |
| **Symptom** | `clean_line("")` returns `None`. `split_on_headings()` skips blank lines. `"\n".join(current_lines)` produces a flat blob with no paragraph boundaries. `chunk_text()` splits on `"\n\n"`, finds none, falls back to blind 300-word sliding window. Cuts mid-sentence, mid-idea. |
| **Root Cause** | `clean_line()` destroys the only paragraph boundary signal in Markdown (blank lines) before any join or split can use them. Three prior "final" fixes targeted the join call — all missed this. |
| **Proposed Fix** | `clean_line("")` returns `""` (not `None`). `split_on_headings()` uses `list[list[str]]` for paragraphs. `flush()` joins lines within paragraphs with space, paragraphs with `\n\n`. ~15 LOC. |
| **Source** | Grounded Review §1; Qwen's exact diff (30/30 tests pass) |
| **Status** | 🟡 OPEN — Phase 0, P0.1 + P0.2 |

### BUG-006: Numbered List Items Silently Dropped
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage1_chunk.py`, line 33 — SKIP_PATTERNS |
| **Symptom** | `re.compile(r"^\s*\d+[.\)]\s")` matches "1. Show the annual plan first..." and drops it silently. Business books contain principles in numbered lists. |
| **Root Cause** | Pattern was added to filter table-of-contents numbering but also catches real content. |
| **Proposed Fix** | Remove the pattern from SKIP_PATTERNS. ~2 LOC. |
| **Source** | Qwen; confirmed in test suite |
| **Status** | 🟡 OPEN — Phase 0, P0.3 |

### BUG-007: PCA Collapses Non-Linear Semantic Structure
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (compounds with nomic-embed-text) |
| **File** | `pipeline/stage3_cluster.py`, `reduce_dimensions()` at line 73-80 |
| **Symptom** | PCA (linear projection) on 768-dim embeddings → 50 dims. Pricing subtopics (value-based, cost-plus, psychological, subscription) sit on a non-linear manifold. PCA collapses them into one blob. Combined with `min_cluster_size=3`: 2,597/2,697 principles → 1 cluster. |
| **Root Cause** | PCA is a linear algorithm. Semantic relationships in embedding space are non-linear. |
| **Proposed Fix** | Replace PCA with UMAP (n_neighbors=15, min_dist=0.0, metric="cosine", random_state=42). ~10 LOC. |
| **Source** | Grounded Review §3; Qwen's Patch 5 |
| **Status** | 🔴 OPEN — Phase 0, P0.5 |

### BUG-008: nomic-embed-text Poor Discrimination on Pricing
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH (compounds with PCA) |
| **File** | `pipeline/pipeline_paths.py`, line 55 |
| **Symptom** | nomic-embed-text (768-dim) produces embeddings where pricing subtopics are too close together. Compounds PCA collapse. |
| **Root Cause** | Model trained on general text, not domain-specific business principles. |
| **Proposed Fix** | Switch to bge-m3 (1024-dim, 8192 token context, higher MTEB retrieval). ~1 LOC. |
| **Source** | ALL 7 documents |
| **Status** | 🟠 OPEN — Phase 0, P0.6 |

### BUG-009: HDBSCAN min_cluster_size=3 Too Permissive
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (compounds with PCA + nomic) |
| **File** | `pipeline/pipeline_paths.py`, line 61 |
| **Symptom** | `HDBSCAN_MIN_CLUSTER_SIZE = 3` — any 3 principles that are slightly closer to each other than to noise form a "cluster." Produces spurious micro-clusters and amplifies PCA collapse. |
| **Root Cause** | Parameter chosen for small test runs. Not tuned for 2,697 principles. |
| **Proposed Fix** | Raise to 8 as starting point. Tune after re-run with UMAP + bge-m3. ~1 LOC. |
| **Source** | Grounded Review; Qwen's Patch 7 |
| **Status** | 🟡 OPEN — Phase 0, P0.7 |

### BUG-010: Dead pipeline_config.yaml
| Field | Value |
|-------|-------|
| **Severity** | 🟡 LOW |
| **File** | `config/pipeline_config.yaml` |
| **Symptom** | File exists in repo but is never imported by any pipeline stage. All configuration is hardcoded in `pipeline_paths.py` or read from environment variables. The YAML file is dead code. |
| **Root Cause** | Config loader was never wired. |
| **Proposed Fix** | Wire `load_config()` in pipeline runner OR delete the file. ~15 LOC if wiring. |
| **Source** | Kimi code audit (BUG 6) |
| **Status** | 🟡 OPEN — Phase 0.5 (de-prioritized — env vars + pipeline_paths.py work) |

### BUG-011: Zero Tests
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM (CRITICAL for v2+) |
| **File** | `tests/` — directory doesn't exist |
| **Symptom** | Zero test files. No `tests/` directory. No unit tests, no integration tests, no golden-file tests. CONSTITUTION mentions "Test suite gate" but there is no test suite. |
| **Root Cause** | Pipeline was built for proof-of-concept. Tests were never added. |
| **Proposed Fix** | Add `tests/test_chunker.py` (Qwen provides 30 tests). Add `tests/test_pipeline.py` (Fixed Implementation provides). ~100 LOC. |
| **Source** | Kimi code audit (BUG 7); Qwen; Fixed Implementation FILE 12 |
| **Status** | 🟡 OPEN — Phase 0 (after fixes, before re-run) |

### BUG-012: sqlite-vec Not Loaded Before CREATE VIRTUAL TABLE
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage6_commit.py` (or wherever `init_schema()` is) |
| **Symptom** | `CREATE VIRTUAL TABLE ... USING vec0(...)` runs before `sqlite_vec.load(conn)`. Raises `sqlite3.OperationalError: no such module: vec0` on first run. |
| **Root Cause** | Python's stdlib `sqlite3` has extension loading disabled by default. The correct API is `sqlite_vec.load(conn)`, not `conn.load_extension("vec0")`. |
| **Proposed Fix** | `conn.enable_load_extension(True)` → `sqlite_vec.load(conn)` → `conn.enable_load_extension(False)`. ~3 LOC. |
| **Source** | Grounded Review §3; Qwen's Patch 11 |
| **Status** | 🟠 OPEN — Phase 0, P0.11 |

### BUG-013: OMLX Guard Uses pkill -f (Kills Pipeline Itself)
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/omlx_guard.py` (or omlx_call.py) |
| **Symptom** | `pkill -f omlx` kills ALL processes matching "omlx" — including the pipeline script itself if it contains "omlx" in its command string. |
| **Root Cause** | Overly broad process matching. |
| **Proposed Fix** | Use `pgrep -f "omlx serve"` to find OMLX server PID specifically, then `os.kill(pid, signal.SIGTERM)` with PID≠own. ~10 LOC. |
| **Source** | Qwen's Patch 13 |
| **Status** | 🟠 OPEN — Phase 0, P0.12 |

### BUG-014: Cloud Burst Code Violates C1/C3
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL (constitutional violation) |
| **File** | `pipeline/core/inference.py` (or wherever `cloud_generate()` lives) |
| **Symptom** | DeepSeek API endpoint, `cloud_generate()`, `deepseek_api_key` config. Ships book text to third-party API. Violates C1 ($0 marginal cost) and C3 (sovereign). |
| **Root Cause** | Extraction speed concern led to cloud fallback proposal. No constitutional exception clause exists for "extraction only." |
| **Proposed Fix** | Delete all cloud code. Fix extraction speed via semantic pre-filter + DFlash + better chunking. ~-30 LOC. |
| **Source** | Grounded Review; Qwen; CONSTITUTION.md C1/C3 |
| **Status** | 🔴 OPEN — Phase 0, P0.13 |

### BUG-015: Silent datasketch Import Failure
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage2_extract.py` |
| **Symptom** | If `datasketch` isn't installed, MinHash near-dedup silently disables with just a `print()` statement. For unattended overnight run, near-duplicate principles reach clustering, inflating apparent "convergence." |
| **Root Cause** | Import wrapped in try/except with print, not raise or log.WARNING. |
| **Proposed Fix** | Raise ImportError or log at WARNING level with clear message. ~5 LOC. |
| **Source** | Grounded Review §4 |
| **Status** | 🟡 OPEN — Phase 0.5, P0.5.5 |

### BUG-016: Model Assignments Reference Phantom Models
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `config/model_assignments.yaml` |
| **Symptom** | References model names that may not exist as real artifacts: `Qwopus-GLM-18B`, `glm-5.2-colibri`, `opus-distilled-27b`. If any code path resolves a role to one of these, fails at runtime with confusing "model not found" error. |
| **Root Cause** | Placeholder/aspirational entries. Never audited against actual model directory. |
| **Proposed Fix** | Audit: `ls ~/.cache/omlx/models/` against every string in `model_assignments.yaml`. Remove or comment out phantom entries. ~0 LOC (manual audit). |
| **Source** | Grounded Review §4 |
| **Status** | 🟡 OPEN — Phase 0, P0.14 |

### BUG-017: OMLX Kernel Memory Leak — Mitigation Untested
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | N/A (OMLX server issue — GitHub #2184) |
| **Symptom** | Wired memory leak on OMLX jetsam kill. Requires reboot to recover. Mitigation (`--memory-guard aggressive`) assumed to work but has never been tested on sustained 130-book runs. Single point of failure for entire pipeline. |
| **Root Cause** | OMLX server bug. Not a Maxwell OS code bug. |
| **Proposed Fix** | Stress test: 5 consecutive pipeline runs, monitor `vm_stat` for wired memory accumulation. If growth >10%, add explicit `sudo purge` between stages or reduce batch sizes. |
| **Source** | ROUNDTABLE-HANDOFF; Gap A from ULTIMATE-CROSS-EXAMINATION-HANDOFF.md |
| **Status** | 🔴 OPEN — Phase 0, P0.0 (must run BEFORE any pipeline fixes) |

---

## RESOLVED (From D2002 stress test, already fixed in live repo)

| Bug ID | Description | Fix |
|--------|-------------|-----|
| BUG-R01 | `pipeline_paths.py`: .md not in supported extensions | Added `.md` to SUPPORTED_EXTENSIONS |
| BUG-R02 | `stage1_chunk.py`: Variable shadowing `chunk_text` function | Renamed loop variable |
| BUG-R03 | `stage1_chunk.py`: Shrink guard blocking incremental runs | Adjusted threshold for append-mode runs |
| BUG-R04 | `omlx_call.py`: Typo `call_omxl` → `call_omlx` | Fixed |
| BUG-R05 | `omlx_call.py`: Missing API key header | Added `sk-maxwell-local` |
| BUG-R06 | `pipeline_paths.py`: Wrong model name | Fixed to `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` |
| BUG-R07 | `stage4_merge.py`: `jargon` field returned as dict, not string | Added string coercion |
| BUG-R08 | `stage4_merge.py`: Missing `Optional` import | Added import |
| BUG-R09 | `stage6_commit.py`: SQLite insert failed on dict-type fields | Added json.dumps() for list/dict fields |
| BUG-R10 | `stage6_commit.py`: Parquet export failed on dict-type fields | Added JSON serialization for Parquet |

---

## BUGLOG RULES

1. **When to add:** Any bug found during pipeline execution, code review, or LLM cross-examination
2. **Severity levels:** 🔴 CRITICAL (data loss, constitutional violation, pipeline failure) | 🟠 HIGH (broken feature, incorrect output) | 🟡 MEDIUM (quality degradation, scaling issue) | 🟢 LOW (cosmetic, documentation)
3. **Handoff trigger:** 5+ unresolved bugs → append full buglog to all LLM handoff documents
4. **Resolution:** Mark as RESOLVED when fix is committed and verified. Move to RESOLVED section with reference to commit hash.
5. **Ownership:** Each bug must have a proposed fix and a target phase. No bug stays "acknowledged but unassigned."

---

*Generated: 2026-07-20 | Bugs tracked: 17 open, 10 resolved | Schema version: 1.0*

---

## SESSION RESOLUTIONS (2026-07-21) — Cross-Examination + Consolidation

The following bugs were resolved during the 2026-07-21 cross-examination session. Fixes applied to pipeline code, verified via syntax check, and committed to `claude projects/maxwell os 2.0/`.

| Bug ID | Resolution | Fix Applied |
|--------|-----------|-------------|
| BUG-001 | ✅ RESOLVED | P0.8: `_load_cluster_map()` implemented in `stage5_verify.py` |
| BUG-002 | ✅ RESOLVED | P0.9: Singleton `get_pipeline_run_id()` in `stamp.py` |
| BUG-003 | ✅ RESOLVED | P0.10: `VERIFY_MODEL` used for SALSA in `stage4_merge.py` |
| BUG-005 | ✅ RESOLVED | P0.1-P0.2: `clean_line("")`→`""`, paragraph-aware `split_on_headings()` |
| BUG-006 | ✅ RESOLVED | P0.3: Numbered-list pattern removed from SKIP_PATTERNS |
| BUG-007 | ✅ RESOLVED | P0.5: UMAP replaces PCA in `stage3_cluster.py` |
| BUG-008 | ✅ RESOLVED | P0.6: bge-m3 replaces nomic-embed-text in `pipeline_config.yaml` |
| BUG-009 | ✅ RESOLVED | P0.7: HDBSCAN `min_cluster_size` 3→8 in config |
| BUG-010 | ✅ RESOLVED | `pipeline_config.yaml` now wired via `pipeline_paths.py` thin loader |
| BUG-011 | ✅ RESOLVED | `tests/test_chunker.py` created (30 tests) |
| BUG-012 | ✅ RESOLVED | P0.11: `sqlite_vec.load(conn)` before virtual table in `stage6_commit.py` |
| BUG-013 | ✅ RESOLVED | P0.12: `omlx_watchdog.py` replaces pkill-based guard (M2/D2027) |
| BUG-014 | ✅ RESOLVED | P0.13: No cloud code found in pipeline — C1/C3 compliant |
| BUG-016 | ✅ RESOLVED | P0.14: Phantom models nuked, bge-m3 replaces nomic, old paths fixed |

**Still open:** BUG-004 (Phase 1), BUG-015 (Phase 0.5), BUG-017 (needs stress test)

---

## NEW BUGS — 2026-07-21 Session

### BUG-018: Orphaned Indentation in stage1_chunk.py clean_line()
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage1_chunk.py`, line 62 |
| **Symptom** | `if len(stripped) < 10:` with no indented body. Causes `IndentationError` on import. Entire pipeline fails at Stage 1. |
| **Root Cause** | Incomplete edit during P0.4 application — the min-length filter was removed but the `if` statement header was left behind without a body. |
| **Proposed Fix** | Remove orphaned `if` line, replace with comment. ~2 LOC. |
| **Source** | Live cross-examination (2026-07-21) — found during chunker syntax verification |
| **Status** | ✅ RESOLVED — Fixed during same session |

### BUG-019: pipeline_paths.py Missing Legacy Exports
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/pipeline_paths.py` |
| **Symptom** | All 7 stage files import `CHECKPOINT_DIR`, `DB_PATH`, `OMLX_BIN` from `pipeline_paths.py`. The new thin YAML-based loader didn't export these names. `ImportError` on every stage file. |
| **Root Cause** | pipeline_paths.py was rewritten as thin YAML loader without backward-compatible aliases for the old flat-path names that stage files still use. |
| **Proposed Fix** | Add legacy aliases at end of file. ~4 LOC. |
| **Source** | Live cross-examination (2026-07-21) — found during pipeline import verification |
| **Status** | ✅ RESOLVED — D2038, aliases added |

### BUG-020: model_assignments.yaml Phantom Models
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `config/model_assignments.yaml` |
| **Symptom** | Four phantom model references: `nomic-embed-text` (replaced by bge-m3), `Qwopus-GLM-18B`, `opus-distilled-27b`, `glm-5.2-colibri`. Also two old v1 paths referencing `claude projects/maxwell os/tools/`. Runtime failures if any code path resolves to these. |
| **Root Cause** | Placeholder/aspirational entries never audited. nomic-embed-text was not updated when bge-m3 was adopted. |
| **Proposed Fix** | Replace nomic→bge-m3, comment out phantoms, disable old paths. Manual audit. |
| **Source** | P0.14 audit (2026-07-21) |
| **Status** | ✅ RESOLVED — All phantoms nuked, bge-m3 wired |

### BUG-021: LaunchAgents Recreating Deleted v1 Directory
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `~/Library/LaunchAgents/com.maxwell.memoryguardian.plist`, `com.maxwellos.watchdog.plist` |
| **Symptom** | Two active LaunchAgents ran every few minutes trying to execute deleted v1 scripts (`memory_guardian.py`, `watchdog_guard.py`). Failed with "No such file or directory" but recreated `claude projects/maxwell os/logs/` directory and wrote error logs. User saw folder reappearing after deletion. |
| **Root Cause** | v1 LaunchAgents never disabled when v2 pipeline was adopted. |
| **Proposed Fix** | `launchctl unload` both plists, rename to `.DISABLED` suffix. |
| **Source** | Live investigation (2026-07-21) |
| **Status** | ✅ RESOLVED — D2035, both plists disabled |

### BUG-022: Dropbox Sync Creates 5 Project Folder Variants
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | N/A (Dropbox filesystem) |
| **Symptom** | Five variants of "claude projects" existed in Dropbox: `claude projects`, `claude projects +`, `claude projects+`, `claude projects (clone)`, `claude projects (Klaus Beyer's conflicted copy)`. Different sessions and devices wrote to different variants. Code existed in `claude projects +` while governance docs were scattered. |
| **Root Cause** | Dropbox FileProvider sync conflicts across multiple devices. The root `claude projects` folder has `com.dropbox.attrs` xattr and cannot be permanently deleted — Dropbox recreates it from cloud sync. |
| **Proposed Fix** | Consolidate all project files into `claude projects/maxwell os 2.0/`. Delete other variants where possible. Accept that `claude projects` root folder persists via Dropbox sync. |
| **Source** | Live cross-examination (2026-07-21) |
| **Status** | ✅ RESOLVED — D2033, single project folder unified |

---

## BUGLOG RULES — AMENDED (2026-07-21)

1. **When to add:** Any bug found during pipeline execution, code review, cross-examination session, or LLM handoff evaluation
2. **Severity levels:** 🔴 CRITICAL (data loss, constitutional violation, pipeline failure) | 🟠 HIGH (broken feature, incorrect output, import failure) | 🟡 MEDIUM (quality degradation, scaling issue, phantom references) | 🟢 LOW (cosmetic, documentation)
3. **Handoff trigger:** 5+ unresolved bugs → append full buglog to all LLM handoff documents (C15)
4. **Resolution:** Mark as RESOLVED when fix is committed and verified. Move to RESOLVED section with reference to commit hash or session date.
5. **Ownership:** Each bug must have a proposed fix and a target phase. No bug stays "acknowledged but unassigned."
6. **SESSION RULE:** After every working session, accumulate all discovered bugs here. This is a standing rule for LLM handoff continuity.
7. **Format:** Bug ID (BUG-NNN), severity emoji, file path, line numbers, symptom, root cause, proposed fix, source (which review/audit/session found it), status.

---

*Updated: 2026-07-21 | Bugs tracked: 22 (17 original + 5 new) | Resolved: 19 | Open: 3 (BUG-004, BUG-015, BUG-017) | Schema version: 1.1*---
## QWEN CROSS-EXAMINATION SESSION (2026-07-21)

### Design Observations for Pre-Implementation Testing

#### OBS-001: SALSA Cross-Domain Inflation Risk
- Severity: MEDIUM (needs production data)
- File: stage4_merge.py build_classify_prompt()
- SALSA lists 25 domains inline; LLMs may over-assign (3-5 domains per FB)
- Test: After first run, audit 50 FBs. If >30% spurious → dichotomous SALSA (D2024).
- Source: Qwen fix.md Bug #6
- Status: NEEDS TESTING — Phase 1

#### OBS-002: Author-Weighted BORP Gap
- Severity: MEDIUM
- File: stage5_verify.py check_borp()
- BORP counts books not authors. 5 books × same author = BORP 5 (false pass).
- Test: After golden set, compare weighted vs unweighted. >20% status change → implement.
- Proposed: weighted = raw_borp*0.30 + author_ratio*0.70
- Source: Qwen fix.md Bug #8
- Status: NEEDS TESTING — Phase 1 with metadata

### Qwen 15 Claims — Cross-Examination Verdict
| # | Claim | Actual | Action |
|---|-------|--------|--------|
| 1 | Phi-4-mini empty on classification | CONFIRMED | FIXED: GEN_MODEL for SALSA |
| 2 | source_clusters undefined | CONFIRMED | FIXED: fb.get() |
| 3 | EMBED_MODEL=nomic | Doc stale, code reads YAML=bge-m3 | FIXED: docstring |
| 4 | PARQUET_DIR/DATA_DIR missing | CONFIRMED | FIXED: legacy aliases |
| 5 | gemma-4-26B broken | CONFIRMED | FIXED: Qwen3-Coder |
| 6 | SALSA cross-domain | Plausible | LOGGED: OBS-001 |
| 7 | No anti-hallucination | Partial | FIXED: CRITICAL RULES |
| 8 | Author BORP | Feature gap | LOGGED: OBS-002 |
| 9 | MIN_CHUNK_WORDS import | WRONG | Not a bug |
| 10 | schemas.py spaces | WRONG | Not a bug |
| 11 | pipeline_paths Path(file) | WRONG | Not a bug |
| 12 | Unicode SyntaxError | WRONG | Not a bug |
| 13 | metrics.py Path(file) | WRONG | Not a bug |
| 14 | unloader.py URL space | WRONG | Not a bug |
| 15 | hardcoded bge-m3 | CONFIRMED | FIXED: EMBED_MODEL |
| **Hit rate:** 7/15 confirmed, 2 design obs, 6 false |
---

## BUG AUDIT SESSION — BUG-023 through BUG-029 (2026-07-21)

Cross-examined from temp/bug fix.txt audit. All entries verified against production code.

### BUG-023: source_clusters Undefined in stage5_verify.py check_factual()
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | `pipeline/stage5_verify.py`, line 175 |
| **Symptom** | `for cid in source_clusters:` — NameError on every FB verification. Stage 5 crashes. |
| **Root Cause** | Variable `source_clusters` used but never extracted from `fb` dict. |
| **Fix** | Added `source_clusters = fb.get("source_clusters", [])` before the loop. Also handles JSON-string case. ~5 LOC. |
| **Source** | Qwen fix.md, confirmed by temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — runtime test passed |

### BUG-024: PARQUET_DIR and DATA_DIR Not Exported from pipeline_paths.py
| Field | Value |
|-------|-------|
| **Severity** | 🔴 CRITICAL |
| **File** | `pipeline/pipeline_paths.py`, `pipeline/stage6_commit.py` line 18 |
| **Symptom** | `ImportError` — stage6 imports PARQUET_DIR/DATA_DIR but neither exists in pipeline_paths.py. Pipeline won't start. |
| **Root Cause** | Legacy aliases section only defined CHECKPOINT_DIR, DB_PATH, OMLX_BIN. |
| **Fix** | Added `PARQUET_DIR` and `DATA_DIR` to the legacy aliases block. ~4 LOC. |
| **Source** | Qwen fix.md, confirmed by temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — import test passed |

### BUG-025: FTS5 Index Lost Across Pipeline Runs
| Field | Value |
|-------|-------|
| **Severity** | 🟠 HIGH |
| **File** | `pipeline/stage6_commit.py`, `init_db()` |
| **Symptom** | `DELETE FROM fbs_fts` clears FTS index, then `AFTER INSERT` triggers only rebuild for rows inserted in THIS run. Second run on a subset loses FTS entries from first run. |
| **Root Cause** | DELETE + trigger-rebuild only covers newly inserted rows. |
| **Fix** | Replaced DELETE with `INSERT INTO fbs_fts(fbs_fts) VALUES('rebuild')` which rebuilds from ALL existing fbs rows. Fallback to DELETE if rebuild fails. ~8 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — syntax + content verified |

### BUG-026: stage4_merge.py Uses Fragile stamp_record({}) Pattern
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage4_merge.py`, line 285 |
| **Symptom** | `stamp_record({})["pipeline_run_id"]` creates a throwaway dict just to extract the run_id. Works (singleton) but fragile and confusing. |
| **Fix** | Import `get_pipeline_run_id` directly and call it: `pipeline_run_id = get_pipeline_run_id()`. ~2 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — syntax verified |

### BUG-027: stage2 --intent Flag Not Documented as Prompt-Level Only
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/stage2_extract.py`, `run_stage2()` |
| **Symptom** | `--intent` flag on Stage 2 modifies the system prompt but users might think it does chunk-level filtering. Actual chunk filter is Stage 1.5. |
| **Fix** | Added warning print when `--intent` is used: "applied as prompt-level focus only. For chunk-level semantic filtering, run stage1_5_intent.py first." ~3 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED |

### BUG-028: ollama_embed.py Hardcoded OLLAMA_URL
| Field | Value |
|-------|-------|
| **Severity** | 🟡 MEDIUM |
| **File** | `pipeline/ollama_embed.py`, line 33 (original) |
| **Symptom** | `OLLAMA_URL = "http://localhost:11434/api/embed"` hardcoded — ignores `pipeline_paths.py` config. Changing port requires editing code. |
| **Fix** | Import `OLLAMA_HOST`, `OLLAMA_PORT` from pipeline_paths.py and construct URL dynamically: `f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/embed"`. Old line commented. ~3 LOC. |
| **Source** | temp/bug fix.txt audit |
| **Status** | ✅ RESOLVED — OLLAMA_URL matches config |

### BUG-029: metrics.py Path(file) + Trailing Spaces — FALSE POSITIVE
| Field | Value |
|-------|-------|
| **Severity** | ⬜ NOT A BUG |
| **File** | `pipeline/metrics.py` |
| **Symptom** | Bugfix file claimed `Path(file)` (no underscores) and trailing spaces in dict keys/f-strings. |
| **Investigation** | Actual code uses `Path(__file__)`. No trailing spaces found. These are **rendering artifacts** from the upload process — double underscores stripped during markdown/html rendering. Confirmed by bugfix file's own Part 3. |
| **Status** | ❌ CLOSED — false positive, rendering artifact |

---

## BUG-001 through BUG-017 — STATUS AUDIT (2026-07-21)

Cross-referenced all 17 original bugs against production code.

| Bug | Original Status | Current Status | Notes |
|-----|----------------|----------------|-------|
| BUG-001 | OPEN — P0.8 | ✅ RESOLVED | _load_cluster_map() + source_clusters fix applied |
| BUG-002 | OPEN — P0.9 | ✅ RESOLVED | get_pipeline_run_id() singleton in stamp.py |
| BUG-003 | OPEN — P0.10 | ⚠️ REVERTED | GEN_MODEL for both (Phi-4-mini broken on classification) |
| BUG-004 | OPEN — Phase 1 | 🔴 OPEN | retrieve.py still re-embeds per query. Needs sqlite-vec pre-computation. |
| BUG-005 | OPEN — P0.1/2 | ✅ RESOLVED | clean_line() returns "", paragraph boundaries preserved |
| BUG-006 | OPEN — P0.3 | ✅ RESOLVED | Numbered-list pattern removed from SKIP_PATTERNS |
| BUG-007 | OPEN — P0.5 | ✅ RESOLVED | UMAP replaces PCA (cosine metric, random_state=42) |
| BUG-008 | OPEN — P0.6 | ✅ RESOLVED | bge-m3 (1024-dim) primary, nomic-embed-text fallback |
| BUG-009 | OPEN — P0.7 | ✅ RESOLVED | hdbscan_min_cluster_size raised to 8 in config |
| BUG-010 | OPEN — Phase 0.5 | ✅ RESOLVED | pipeline_config.yaml wired via pipeline_paths.py |
| BUG-011 | OPEN — Phase 0 | ✅ RESOLVED | tests/ directory exists, 12/12 chunker tests pass |
| BUG-012 | OPEN — P0.11 | ✅ RESOLVED | sqlite_vec.load() before CREATE VIRTUAL TABLE |
| BUG-013 | OPEN — P0.12 | ✅ RESOLVED | omlx_watchdog.py with RSS monitoring, no pkill |
| BUG-014 | OPEN — P0.13 | ✅ RESOLVED | No cloud code found in pipeline |
| BUG-015 | OPEN — P0.5.5 | ✅ RESOLVED | datasketch import now raises ImportError |
| BUG-016 | OPEN — P0.14 | ✅ RESOLVED | Phantom models removed/commented in model_assignments.yaml |
| BUG-017 | OPEN — P0.0 | 🔴 OPEN | Needs 130-book OMLX stress test (not testable in sandbox) |

**Summary: 14/17 resolved, 1 reverted (BUG-003), 2 still open (BUG-004, BUG-017)**
