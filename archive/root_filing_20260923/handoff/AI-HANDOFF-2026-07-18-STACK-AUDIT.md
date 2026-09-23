# Maxwell OS — Stack Audit: What Survives v3.0
> **Date:** 2026-07-18 | **Basis:** Architecture v3.0 + Research Response cross-examination
> **Purpose:** Map every tool/config/dependency against v3.0 requirements, identify redundancy

---

## §1 — CURRENT STACK INVENTORY

| Category | Count | Total LOC |
|----------|-------|------------|
| Python scripts (.py) | ~175 | 93,313 |
| Shell scripts (.sh) | ~55 | — |
| Config files (.yaml/.json) | 37 | — |
| Governance docs (.md) | 20 | — |
| Prompt templates | 12 | — |
| **Total tools/** | **248 files** | — |

---

## §2 — WHAT v3.0 ACTUALLY NEEDS

### 2.1 Pipeline Scripts (6 stages)

| Stage | v3.0 Name | What It Does | Lines Estimate |
|-------|-----------|-------------|----------------|
| 0 | `convert.py` | EPUB/PDF → Markdown via Pandoc/Docling | ~200 |
| 1 | `chunk.py` | Markdown → segments, SHA-256 dedup | ~300 |
| 2 | `extract.py` | Segments → raw principles (Qwen3.6), MinHash near-dedup | ~500 |
| 3 | `cluster.py` | Embed principles, HDBSCAN cluster, semantic dedup | ~400 |
| 4 | `merge_classify.py` | Clusters → FBs (Qwen3.6 merge + SALSA classify) | ~600 |
| 5 | `verify.py` | BORP check, factual consistency (Phi-4-mini), human audit queue | ~400 |
| 6 | `commit.py` | Write to SQLite + Parquet export, stamp, validate schema | ~300 |
| **Total** | | | **~2,700** |

### 2.2 Supporting Scripts

| Script | Purpose | Lines |
|--------|---------|-------|
| `schemas.py` | Pydantic models with Literal types | ~300 |
| `retrieve.py` | Hybrid search: SQL + FTS5 + sqlite-vec | ~300 |
| `query_kb.py` | CLI for Maxwell to browse FBs | ~200 |
| `pipeline_config.py` | Paths, model assignments, taxonomy | ~200 |
| **Total** | | **~1,000** |

### 2.3 Config Files

| File | Purpose |
|------|---------|
| `config/taxonomy_v5.yaml` | 25 domains + 47 disciplines **(KEEP)** |
| `config/model_assignments.yaml` | Model → stage mapping **(KEEP but simplify)** |
| `config/pipeline_config.yaml` | Paths, thresholds, batch sizes **(REWRITE)** |

### 2.4 Total v3.0 Footprint

**~3,700 lines of Python + 3 config files.** Everything else is under review.

---

## §3 — COMPLETE TOOL AUDIT

Legend:
- ✅ **KEEP** — directly usable in v3.0 with no or minor changes
- 🔧 **REWRITE** — concept is right but implementation is tied to old pipeline
- 🗑️ **REDUNDANT** — function is replaced by v3.0's simpler approach
- 💀 **DEAD** — phantom, never worked, or obsolete
- 📦 **DEFER** — useful later (post-MVP), not needed for triad

---

### 3.1 — PIPELINE CORE (S1→S8)

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `s1_extractive.py` | 17,735 | 🗑️ REDUNDANT | v3.0 Stage 2 replaces extraction with Qwen3.6 direct principle extraction, not embedding-based. Different paradigm entirely. |
| `s1_chunking.py` | 15,082 | 🔧 REWRITE | Chunking logic is salvageable (section-aware splitting). Needs SHA-256 dedup added, output format changed to JSONL. Reduce from 15K to ~300 lines. |
| `s1p5_cluster.py` | 22,415 | 🗑️ REDUNDANT | FAISS-based clustering replaced by HDBSCAN (Stage 3). Different algorithm, different input format. |
| `s3_converge_local.py` | 81,207 | 🗑️ REDUNDANT | This 81K-line behemoth is the core of all the problems. Replaced by v3.0 Stage 4 (merge + classify). The complexity came from trying to do inline classification with schema enforcement mid-generation. v3.0 separates extraction from classification. |
| `s3_domain_lookup.py` | 2,987,027 | 💀 DEAD | 3MB lookup table. Already obsolete per D1055-FIX. Remove. |
| `s3a_ab_test.py` | 19,781 | 🗑️ REDUNDANT | A/B testing framework for old S3a. v3.0 has no A/B testing in MVP. |
| `s3a_runner.py` | 20,876 | 🗑️ REDUNDANT | Runner for old S3a process. v3.0 Stage 4 is a single script. |
| `s3c_verify.py` | 16,219 | 🔧 REWRITE | Verification concept is right (cross-family model). But old format expects S3a output schema. Rewrite for v3.0 Stage 5 — BORP check, factual consistency against evidence table. |
| `s5_bridge.py` | 26,321 | 🗑️ REDUNDANT | Bridge between S3a and S5. v3.0 has no bridge — merge+classify is a single stage. |
| `s5_bridge.py.bak_d1055` | 21,623 | 💀 DEAD | Backup of old version. Remove. |
| `s5_generate_local.py` | 56,820 | 🗑️ REDUNDANT | FB generation via Gemma-4. v3.0 Stage 4 merges principles into FBs using Qwen3.6, with separate classification pass. Different model, different flow. |
| `s6_pipeline.py` | 111,486 | 🔧 REWRITE | Validation logic is salvageable (name normalization, BORP counting, stamping). But 111K lines for validation is insane. v3.0 Stage 5 is ~400 lines. Keep the algorithms, discard the architecture. |
| `s6_export_resume.py` | 9,800 | 🗑️ REDUNDANT | Export/resume logic for old S6. v3.0 Stage 6 commits directly to SQLite — no export step needed. |
| `s6a_override.py` | 30,455 | 🗑️ REDUNDANT | Override mechanism for S6. v3.0 schema has revision tracking built into the database — no override scripts needed. |
| `pipeline_gate.py` | 58,007 | 🔧 REWRITE | Gate concept is good but 58K lines for gate checks is bloated. v3.0 needs: BORP ≥ 2 check, schema validation (Pydantic), stamp verification. ~200 lines. |
| `pipeline_io.py` | 8,141 | 🗑️ REDUNDANT | I/O utilities for old pipeline format. v3.0 uses JSONL checkpoints. |
| `pipeline_health.py` | 9,303 | 📦 DEFER | Pipeline health monitoring. Useful after MVP but not needed for triad. |
| `pipeline_status.py` | 7,967 | 🔧 REWRITE | Currently reads old pipeline directories. Rewrite to read SQLite counts. |
| `pipeline_resilience.py` | 13,757 | 📦 DEFER | Resilience wrappers for LLM calls. v3.0 Stage 2/4 needs some retry logic, but 13K lines of resilience framework is overkill for MVP. |

**Pipeline core subtotal: 21 scripts → 0 keep, 4 rewrite, 13 redundant, 2 dead, 2 defer**

---

### 3.2 — CLASSIFICATION SCRIPTS

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `classify_domains.py` | 15,167 | 🗑️ REDUNDANT | Replaced by SALSA (Stage 4). Already deprecated per D1055. |
| `classify_disciplines.py` | 15,034 | 🗑️ REDUNDANT | Same. |
| `classify_domains_multi.py` | 13,385 | 🗑️ REDUNDANT | Same — and D1055 already removed multi-classify as separate step. |
| `classify_metadata.py` | 11,498 | 🗑️ REDUNDANT | Metadata classification for old schema. v3.0 schema is self-contained. |
| `fix_domain_discipline.py` | 12,439 | 🗑️ REDUNDANT | Fix script for contamination. v3.0 Pydantic Literal types make contamination structurally impossible — no fix scripts needed. |
| `fix_domain_discipline_llm.py` | 5,375 | 🗑️ REDUNDANT | LLM-based fix for wrong labels. v3.0 has no "wrong labels" to fix — classification happens at generation time. |
| `reclassify_context_bulk.py` | 7,125 | 🗑️ REDUNDANT | Bulk reclassification. Not needed once classification is correct at source. |
| `reclassify_fb_domains.py` | 21,894 | 🗑️ REDUNDANT | Largest reclassification script. The entire reclassification category vanishes with v3.0. |
| `reclassify_fb_domains.py.bak` | 21,138 | 💀 DEAD | Backup. Remove. |
| `init_classification_fields.py` | 10,359 | 🗑️ REDUNDANT | Field initialization for old pipeline. v3.0 generates complete FBs from Stage 4 — no init needed. |
| `apply_cross_domain.py` | 8,150 | 🗑️ REDUNDANT | Cross-domain application logic. v3.0 multi-label classification is built into SALSA dichotomic prompting. |
| `domain_discipline_router.json` | — | ✅ KEEP | 14,899 byte routing table. Still needed for domain→discipline mapping in Stage 4. |
| `taxonomy_triage.py` | 40,118 | 🗑️ REDUNDANT | Triage for taxonomy issues. v3.0 doesn't have taxonomy drift by design (Pydantic Literal enforcement). |

**Classification subtotal: 13 scripts → 1 keep, 0 rewrite, 11 redundant, 1 dead**

---

### 3.3 — GOVERNANCE & GUARDS

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `guard.py` | 28,606 | 📦 DEFER | Ring 0-4 guard. Useful for production but overkill for triad. Keep file, don't invoke during MVP runs. |
| `governance.py` | 27,280 | 📦 DEFER | In-process decision enforcement. v3.0 pipeline is too simple to need runtime governance. Useful after MVP. |
| `constitution_enforcer.py` | 6,384 | 📦 DEFER | Verifies constitution rules are enforceable. Not needed during triad — no constitution changes expected. |
| `phantom_guard.py` | 8,207 | 📦 DEFER | Detects phantom file claims. Useful after MVP when tools multiply again. |
| `decision_auditor.py` | 5,632 | 📦 DEFER | Validates decision registry. Useful when pipeline is stable and decisions accumulate. |
| `delegate_guard.py` | 30,623 | 📦 DEFER | Guards delegate() calls. Not needed — v3.0 MVP uses zero delegates. Single-script pipeline. |
| `agent_guard.py` | 19,035 | 📦 DEFER | Agent behavior guard. No agents in pipeline execution. |
| `change_guard.py` | 4,732 | 📦 DEFER | Tracks changes. Useful after MVP. |
| `unified_guard.py` | 17,312 | 📦 DEFER | Consolidated guard. Same as guard.py — defer. |
| `implementation_guard.py` | 5,444 | 📦 DEFER | Verifies LIVING decisions. Not needed until decisions accumulate. |
| `enforce_decisions.py` | 8,511 | 📦 DEFER | Decision enforcement. Defer. |
| `drift_gate.py` | 1,976 | 🗑️ REDUNDANT | Drift detection. v3.0 has temp=0.0 + pinned models + taxonomy_version stamping. Drift is structurally prevented, not detected. |
| `compression_gate.py` | 9,412 | 🗑️ REDUNDANT | Compression quality gate. v3.0 doesn't use compression stage. |
| `factcheck_gate.py` | 16,543 | 🔧 REWRITE | Factual consistency check. Salvage the cross-reference logic for v3.0 Stage 5 (verify). |
| `safety_gate.py` | 11,627 | 📦 DEFER | Content safety. Not needed for business book extraction. |
| `io_guard.py` | 5,371 | ✅ KEEP | Crash-safe writes (tempfile → fsync → os.replace). Required by CONSTITUTION.md C6. Used in v3.0 Stage 6. |
| `doc_guard.py` | 7,852 | ✅ KEEP | Protected file access. Required by CONSTITUTION.md R-D824. |
| `mcp_doc_guard.py` | 8,757 | 📦 DEFER | MCP version of doc guard. Defer. |
| `protect.py` | 3,246 | ✅ KEEP | File protection utilities. |

**Governance subtotal: 19 scripts → 3 keep, 1 rewrite, 2 redundant, 13 defer**

---

### 3.4 — ANYTYPE INTEGRATION

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `push_anytype.py` | 74,318 | 📦 DEFER | Push FBs to Anytype. Still needed — but AFTER SQLite is populated. Not in triad. v3.0 treats Anytype as presentation layer. |
| `anytype_write.py` | 20,397 | 📦 DEFER | Anytype write utilities. Defer until post-MVP push phase. |
| `space_router.py` | 7,983 | 📦 DEFER | Routes FBs to Anytype spaces. Defer. |
| `refresh_anytype_token.sh` | 1,887 | 📦 DEFER | Token refresh. Defer. |
| `push_diverse.sh` | 924 | 💀 DEAD | Old push script. Remove. |
| `push_space_test.sh` | 1,410 | 💀 DEAD | Push test. Remove. |
| `master_push_all.sh` | 4,033 | 📦 DEFER | Master push orchestrator. Defer. |
| `cross_space_sidecar.py` | 23,962 | 📦 DEFER | Cross-space FB management. Defer. |
| `anytype_tags_*.json` | ~20 files | 📦 DEFER | Tag definitions for Anytype spaces. Keep but don't use in triad. |
| `nuke_anytype.py` | 7,282 | ✅ KEEP | Protected by R-D413b — NEVER delete without Maxwell's permission. Keep for emergency use only. |

**Anytype subtotal: 30+ files → 1 keep (nuke_anytype.py), 0 rewrite, 0 redundant, 2 dead, 27+ defer**

---

### 3.5 — PHASE 0-6 INFRASTRUCTURE (The 9,837 LOC of Over-Engineering)

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `ipc_server.py` | 17,221 | 🗑️ REDUNDANT | Unix socket JSON-RPC server. v3.0 is a single-script pipeline — no IPC needed. |
| `unified_guard.py` | 17,312 | 📦 DEFER | Already counted in governance. |
| `resource_monitor.py` | 10,147 | 📦 DEFER | RAM/CPU tracking. Useful for monitoring long pipeline runs — but triad takes 3.5 hours. Defer. |
| `knowledge_hook.py` | 13,089 | 🗑️ REDUNDANT | FB knowledge injector with SQLite FTS. v3.0 has FTS5 built into maxwell.db — no hook needed. |
| `llm_observe.py` | 16,304 | 📦 DEFER | LLM observability (LangFuse traces). Overkill for triad. Useful for production debugging. |
| `circuit_breaker.py` | 17,424 | 📦 DEFER | Circuit breaker for LLM calls. v3.0 has simple retry — full circuit breaker is overkill for 3 books. |
| `semantic_cache.py` | 14,992 | 🗑️ REDUNDANT | Embedding cache. v3.0 uses sqlite-vec — different caching strategy, embedded in Stage 3. |
| `intent_router.py` | 11,739 | 🗑️ REDUNDANT | Routes user intents to models. No user intents in pipeline — it's a batch process. |
| `escalation.py` | 13,860 | 🗑️ REDUNDANT | Five-level escalation. v3.0 has one level: fail → log → continue. |
| `parallel_consensus.py` | 14,093 | 🗑️ REDUNDANT | Multi-agent fan-out. v3.0 uses single-model per stage with cross-family verify (R5). No parallel consensus needed. |
| `consensus_voting.py` | 15,392 | 🗑️ REDUNDANT | Six voting strategies. Not needed. |
| `dual_memory.py` | 14,233 | 🗑️ REDUNDANT | Agent memory system. No agents in pipeline. |
| `model_manager.py` | 10,773 | 📦 DEFER | Memory-budget model loading. Useful for ensuring Qwen3.6 + Phi-4-mini don't OOM. But v3.0 Stage 4 loads Qwen3.6, Stage 5 loads Phi-4-mini — sequential, not concurrent. |
| `self_healing.py` | 26,986 | 🗑️ REDUNDANT | Error classifier with recovery strategies. v3.0 is simple enough that errors are obvious. |
| `monitor_dashboard.py` | 23,487 | 🗑️ REDUNDANT | Health dashboard. v3.0 has one script running at a time — no dashboard needed. |
| `security_check.py` | 25,961 | 📦 DEFER | Security audit. Keep for production. |
| `guardian_daemon.py` | 33,910 | 🗑️ REDUNDANT | Background self-healing daemon. Nothing to heal if the pipeline is 6 simple scripts. |
| `doc_scanner.py` | 18,248 | 🗑️ REDUNDANT | Documentation scanner (169 tools, 69K LOC). Won't need scanning when 80% of tools are gone. |
| `triage_waiting.py` | 17,658 | 🗑️ REDUNDANT | Triage for waiting FBs. No waiting FBs in v3.0 — FBs are committed immediately. |
| `maxwell_tui.py` | 27,125 | 📦 DEFER | Terminal UI. Cool but not needed for triad. |

**Infrastructure subtotal: 21 scripts → 0 keep, 0 rewrite, 15 redundant, 6 defer**

---

### 3.6 — KNOWLEDGE & RETRIEVAL

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `build_knowledge_db.py` | 13,057 | 🔧 REWRITE | Builds knowledge DB from FBs. v3.0 Stage 6 writes directly to SQLite — this becomes `commit.py`. |
| `duckdb_knowledge.py` | 21,558 | 🔧 REWRITE | DuckDB knowledge layer. Good foundation. Rewrite for v3.0 schema and sqlite-vec integration. |
| `hybrid_search.py` | 9,052 | 🔧 REWRITE | Hybrid search. Rewrite for v3.0's SQL + FTS5 + sqlite-vec stack. |
| `query_kb.py` | 9,875 | 🔧 REWRITE | CLI query tool. Rewrite for new SQLite schema. |
| `query_knowledge.py` | 10,092 | 🗑️ REDUNDANT | Duplicate of query_kb.py essentially. Merge into one. |
| `vector_query.py` | 8,356 | 🗑️ REDUNDANT | Vector-only query. v3.0 uses hybrid search — separate vector query is unnecessary. |
| `embed_fbs.py` | 4,808 | 🔧 REWRITE | Embed FBs for vector search. v3.0 Stage 3 embeds during clustering, Stage 6 stores embeddings in sqlite-vec. |
| `embed_kb.py` | 12,994 | 🗑️ REDUNDANT | Knowledge base embedding. Replaced by Stage 3 + Stage 6. |
| `batch_embed.py` | 4,864 | 🗑️ REDUNDANT | Embedding batch processor. Replaced. |
| `batch_embed_ollama.py` | 5,874 | 🗑️ REDUNDANT | Ollama-specific batch embedder. Replaced. |
| `mcp_fb_server.py` | 17,601 | 📦 DEFER | FB MCP server for agent retrieval. Critical for business ops — but AFTER FBs exist in SQLite. |
| `mcp_pipeline.py` | 11,420 | 🗑️ REDUNDANT | MCP pipeline server. v3.0 pipeline is too simple to need MCP. |
| `turbovec_store.py` | 20,338 | 🗑️ REDUNDANT | Turbovec vector store. Currently down. Replaced by sqlite-vec. |
| `_ollama_embed.py` | 4,775 | ✅ KEEP | Low-level Ollama embedding calls. Still needed — Stage 3 uses nomic-embed-text via Ollama. |
| `run_embed.py` | 4,205 | 🗑️ REDUNDANT | Embedding runner. Replaced by Stage 3. |

**Knowledge/retrieval subtotal: 15 scripts → 1 keep, 5 rewrite, 8 redundant, 1 defer**

---

### 3.7 — VALIDATION & QUALITY

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `validate_fb.py` | 44,124 | 🔧 REWRITE | Comprehensive FB validation. Salvage BORP check, schema validation, stamp verification. Reduce from 44K to ~200 lines (Pydantic handles most of this). |
| `validate_pipeline.py` | 8,172 | 🗑️ REDUNDANT | Pipeline-wide validation. v3.0 validates at each stage via checkpoint schema checks — no central validator needed. |
| `validate_export.py` | 6,565 | 🗑️ REDUNDANT | Export validation. v3.0 commits to SQLite directly — no export to validate. |
| `validate_book_structure.py` | 10,345 | ✅ KEEP | Validates canonical book folder names. Still needed for Stage 0 input validation. |
| `validate_domain_books.py` | 13,651 | 🔧 REWRITE | Domain book validation. Simplify for v3.0 domain structure. |
| `validate_s7_spec.py` | 14,175 | 🗑️ REDUNDANT | S7 spec validation. No S7 in v3.0 — human audit is Stage 5. |
| `validate_eval_loop.py` | 3,010 | 🗑️ REDUNDANT | Eval loop validation. No eval loop in v3.0. |
| `eval_loop.py` | 53,037 | 🗑️ REDUNDANT | Main eval loop. 53K lines. Replaced by Stage 5 verify step (BORP check + Phi-4-mini). |
| `fb_lint.py` | 23,253 | 🔧 REWRITE | FB linting. Salvage name normalization rules, jargon checks. Reduce to ~100 lines. |
| `fb_label_audit.py` | 19,832 | 🗑️ REDUNDANT | Label audit. v3.0 Pydantic Literal types make label auditing unnecessary — invalid labels can't exist. |
| `check_extractiveness.py` | 12,954 | 🗑️ REDUNDANT | Extractiveness quality check. v3.0 uses Qwen3.6 for extraction — different quality metric. |
| `source_grounding.py` | 7,167 | 🔧 REWRITE | Source grounding check. Salvage for v3.0 Stage 5 BORP verification. |
| `dedup_check.py` | 11,927 | 🗑️ REDUNDANT | Dedup verification. v3.0 three-tier dedup is built into pipeline — no separate check needed. |
| `precheck_borp.py` | 33,163 | 🔧 REWRITE | BORP pre-check. Salvage BORP counting logic for Stage 5. Reduce from 33K to ~100 lines. |

**Validation subtotal: 14 scripts → 1 keep, 6 rewrite, 7 redundant**

---

### 3.8 — INGEST & INTAKE

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `intake.py` | 21,897 | 📦 DEFER | Book intake pipeline. Not needed for triad (manual book selection). Useful for scaling to 863 books. |
| `auto_intake.py` | 7,345 | 📦 DEFER | Automatic inbox detection. Defer. |
| `place_quarantine.py` | 10,856 | 📦 DEFER | Quarantine placement. Defer. |
| `sync_education_to_pipeline.py` | 5,362 | 📦 DEFER | MD sync to pipeline. Defer. |
| `sync_all_formats.py` | 6,107 | 📦 DEFER | Cross-format sync. Defer. |
| `sync_docs.py` | 7,938 | 📦 DEFER | Doc sync. Defer. |
| `merge_inbox_books.py` | 6,954 | 📦 DEFER | Inbox merging. Defer. |
| `merge_per_domain.py` | 4,939 | 🗑️ REDUNDANT | Per-domain merging. v3.0 doesn't have domain-based merging — HDBSCAN clusters across domains. |
| `restructure_books.py` | 19,174 | ✅ KEEP | Book library restructuring. Already used. Keep for maintenance. |
| `reorganize_books.py` | 698 | 🗑️ REDUNDANT | Simple reorganizer. Superseded by restructure_books.py. |

**Ingest subtotal: 10 scripts → 1 keep, 0 rewrite, 2 redundant, 7 defer**

---

### 3.9 — SESSION & MEMORY

| Script | LOC | Verdict | Why |
|--------|-----|---------|-----|
| `session_episodes.py` | 34,135 | 📦 DEFER | Session state machine. Useful for Goose sessions. Not used by pipeline. |
| `session_state.py` | 6,150 | 📦 DEFER | Session state. Defer. |
| `session_boot.py` | 4,414 | 📦 DEFER | Session bootstrap. Defer. |
| `session_start.py` | 997 | 📦 DEFER | Session start. Defer. |
| `session_end.py` | 1,530 | 📦 DEFER | Session end. Defer. |
| `session_audit.py` | 8,452 | 📦 DEFER | Session audit. Defer. |
| `memory_consolidation.py` | 11,026 | 📦 DEFER | Memory consolidation. Defer. |
| `memory_mcp_server.py` | 23,302 | 📦 DEFER | Memory MCP server. Defer. |
| `trust_ledger.py` | 7,054 | 📦 DEFER | Skill trust tiers. Defer. No skills in v3.0 pipeline. |
| `pi_execution_db.py` | 8,849 | 📦 DEFER | PI execution database. Defer. |
| `pi_execution_schema.sql` | — | 📦 DEFER | PI schema. Defer. |
| `dual_memory.py` | 14,233 | 🗑️ REDUNDANT | Already counted. |
| `context_reset.py` | 12,289 | 🗑️ REDUNDANT | Context reset. Not needed for batch pipeline. |
| `state.py` | 9,458 | 📦 DEFER | State management. Defer. |

**Session subtotal: 14 scripts → 0 keep, 0 rewrite, 2 redundant, 12 defer**

---

### 3.10 — UTILITY SCRIPTS (miscellaneous)

| Script | Verdict | Why |
|--------|---------|-----|
| `bloatcheck.py` | 📦 DEFER | Dependency checker. Useful for C5 compliance but not in triad. |
| `cost_tracker.py` | 📦 DEFER | Cost tracking. All $0 in v3.0 — no costs to track. |
| `token_tracker.py` | 📦 DEFER | Token tracking. Not needed for batch pipeline. |
| `backup_guardian.sh` | ✅ KEEP | Required by C13. Backup after batch writes. |
| `safe_delete.py` | ✅ KEEP | Required by R-D410. Safe file deletion. |
| `json_repair.py` | 🔧 REWRITE | JSON repair for LLM output. Still needed for Stage 2/4 Qwen3.6 output. Keep, simplify. |
| `omxl_token_wrapper.py` / `omlx_token_wrapper.py` | 🔧 REWRITE | OMLX call wrappers. Keep timeout logic. Drop circuit breaker, heartbeat, watchdog — too complex for MVP. |
| `schemas.py` | 29,609 | 🔧 REWRITE | Massive schema file for old pipeline. Rewrite as Pydantic v2 models with Literal types. Reduce from 29K to ~300 lines. |
| `pipeline_paths.py` | 19,670 | 🔧 REWRITE | Path definitions. Keep for C12 compliance. Simplify — v3.0 has far fewer paths. |
| `pipeline_config.py` | 5,307 | 🔧 REWRITE | Pipeline configuration. Rewrite for v3.0 stages. |
| `resolve_model.py` | 9,111 | 📦 DEFER | Model resolution. v3.0 uses fixed model per stage — no resolution logic needed. |
| `model_router.py` | 12,263 | 🗑️ REDUNDANT | Model routing. v3.0 has fixed model assignments per stage. No routing. |
| `model_lazyload.py` | 8,179 | ✅ KEEP | Lazy-load models per stage. Required by D1057. Still needed — Stage 4 loads Qwen3.6, Stage 5 loads Phi-4-mini. |
| `model_prune.py` | 4,276 | 📦 DEFER | Model pruning. Defer. |
| `run_full_pipeline.sh` | 2,955 | 🗑️ REDUNDANT | Old pipeline runner. Replaced by v3.0 orchestrator. |
| `run_s1s8_e2e.sh` | 1,518 | 🗑️ REDUNDANT | Old end-to-end runner. Replaced. |
| `run_s1s8_test.sh` | 759 | 🗑️ REDUNDANT | Old test runner. Replaced. |
| `run_pipeline_after_embed.py` | 8,662 | 🗑️ REDUNDANT | Post-embed pipeline runner. No separate embed step in v3.0. |
| `e2e_final.sh` | 1,536 | 💀 DEAD | Old E2E script. Remove. |
| `e2e_run3.sh` | 1,627 | 💀 DEAD | Old E2E variant. Remove. |
| `run_540_audit.sh` | 1,994 | 📦 DEFER | Audit runner. Defer. |
| `run_classify.sh` | 2,827 | 🗑️ REDUNDANT | Classification runner. No separate classification step. |

Plus ~30 more utility scripts: `analyze_*`, `benchmark_*`, `fable_judge.py`, `skill_*`, `stress_test.py`, `render_*`, `daily_brief.py`, etc. — all 📦 DEFER or 🗑️ REDUNDANT.

---

## §4 — SUMMARY: WHAT SURVIVES

### 4.1 Keep (no changes): 8 scripts

| Script | Why |
|--------|-----|
| `io_guard.py` | Crash-safe writes (C6) |
| `doc_guard.py` | Protected file access (R-D824) |
| `protect.py` | File protection |
| `nuke_anytype.py` | Protected emergency tool (R-D413b) |
| `_ollama_embed.py` | Low-level embedding calls |
| `validate_book_structure.py` | Book validation |
| `restructure_books.py` | Library maintenance |
| `model_lazyload.py` | Lazy loading (D1057) |
| `backup_guardian.sh` | Backups (C13) |
| `safe_delete.py` | Safe deletion (R-D410) |
| `domain_discipline_router.json` | Routing table |

### 4.2 Rewrite (simplified): 14 scripts

| Script | New Name | Target LOC |
|--------|----------|------------|
| `s1_chunking.py` | `chunk.py` | 300 |
| `s3c_verify.py` | `verify.py` | 400 |
| `s6_pipeline.py` | (merged into verify.py) | — |
| `pipeline_gate.py` | (merged into verify.py) | — |
| `factcheck_gate.py` | (merged into verify.py) | — |
| `validate_fb.py` | (Pydantic in schemas.py) | — |
| `fb_lint.py` | `lint.py` | 100 |
| `source_grounding.py` | (merged into verify.py) | — |
| `precheck_borp.py` | (merged into verify.py) | — |
| `build_knowledge_db.py` | `commit.py` | 300 |
| `duckdb_knowledge.py` | `retrieve.py` | 300 |
| `hybrid_search.py` | (merged into retrieve.py) | — |
| `query_kb.py` | `query.py` | 200 |
| `json_repair.py` | `json_repair.py` | 150 |
| `omxl_token_wrapper.py` | `omlx_call.py` | 150 |
| `schemas.py` | `schemas.py` | 300 |
| `pipeline_paths.py` | `pipeline_paths.py` | 200 |
| `pipeline_config.py` | `pipeline_config.py` | 200 |
| `pipeline_status.py` | `status.py` | 150 |

### 4.3 New (v3.0 only): 4 scripts

| Script | Purpose | Target LOC |
|--------|---------|------------|
| `convert.py` | Stage 0: EPUB/PDF → MD | 200 |
| `extract.py` | Stage 2: Principles extraction | 500 |
| `cluster.py` | Stage 3: HDBSCAN clustering | 400 |
| `merge_classify.py` | Stage 4: FB merge + SALSA classify | 600 |

### 4.4 Total v3.0 Footprint

| Category | Count | LOC |
|----------|-------|-----|
| Pipeline scripts (6 stages) | 6 | ~2,700 |
| Supporting scripts | 5 | ~1,000 |
| Keep (existing) | ~10 | ~3,000 |
| Rewrite (simplified) | ~12 | ~2,450 |
| **Total active** | **~33** | **~9,150** |

### 4.5 What Goes Away

| Fate | Count | LOC Freed |
|------|-------|-----------|
| 🗑️ REDUNDANT | ~80 scripts | ~65,000 |
| 💀 DEAD | ~15 scripts | ~5,000 |
| 📦 DEFER | ~100 scripts | ~20,000 |
| **Total removed/deferred** | **~195 scripts** | **~90,000** |

### 4.6 Config Files

| File | Verdict |
|------|---------|
| `taxonomy_v5.yaml` | ✅ KEEP |
| `model_assignments.yaml` | 🔧 REWRITE (simplify for 3 models) |
| `pipeline_config.yaml` | 🔧 REWRITE (simplify for 6 stages) |
| `domain_anchors.yaml` | ✅ KEEP |
| `domain_disciplines.yaml` | ✅ KEEP |
| `synonym_map.yaml` | ✅ KEEP |
| `decisions.yaml` | 📦 DEFER (not used in pipeline) |
| All other 30 config files | 📦 DEFER |

### 4.7 Dependencies (requirements.txt)

**Remove (no longer needed by pipeline):**
- `chromadb` — replaced by sqlite-vec
- `lancedb` — replaced by sqlite-vec
- `lance-namespace` — unused
- `rdflib` — not used in v3.0 (no RDF)
- `langfuse` — no LLM observability in MVP
- `pydantic-ai` — not used
- Any delegate/subagent packages

**Add:**
- `datasketch` — MinHash LSH for near-dedup
- `hdbscan` — clustering (scikit-learn-contrib)

**Keep:**
- `duckdb` — for Parquet export and analytics
- `pyarrow` — for Parquet
- `sqlite-vec` — vector search
- `sentence-transformers` — embeddings (if switching from Ollama)
- `faiss-cpu` — not needed but harmless
- `ollama` / `openai` (for OMLX compatibility)
- `pyyaml` — config files

---

## §5 — SPEC TOOLS FOR LOCAL LLMS

### 5.1 The Problem

v3.0 needs ~2,700 lines of new pipeline code written by local LLMs (Qwen3.6, Phi-4-mini, Gemma-4). These models are "not smart" compared to frontier models — they drift, hallucinate implementations, and lose context in long prompts. They need tightly constrained specs.

### 5.2 Contenders

| Tool | Stars | Approach | Local LLM Fit |
|------|-------|----------|---------------|
| **OpenSPDD** | ~500 | REASONS Canvas (7-part rigid template), method-level detail, bidirectional sync | ⚠️ Authors say "don't use with local LLMs" — but the rigid structure is exactly what weak models need |
| **Spec-Kit** | 39K | Markdown spec.md → plan.md → tasks.md, free-text templates | ✅ Agent-agnostic, but free-text gives weak models room to improvise |
| **Outlines** | 12K | Constrained decoding — guarantees JSON schema compliance | ✅ Not a spec tool, but the missing layer. Add to either OpenSPDD or Spec-Kit to guarantee output structure. |
| **Instructor** | 8K | Pydantic-enforced LLM output with automatic retry | ✅ Similar to Outlines — guarantees structure. Simpler API. |

### 5.3 My Take

For Maxwell's use case (local LLMs implementing ~300-line Python scripts with precise requirements):

**Neither OpenSPDD nor Spec-Kit alone is sufficient.** Both rely on the model following free-text instructions. For Qwen3.6 and Phi-4-mini, you need **constrained output** — the model must output valid code, not prose about code.

**The pragmatic combination:**

1. **Spec format: OpenSPDD's REASONS Canvas structure** — but stripped down. The rigid 7-part template (Requirements, Entities, Actions, Safeguards, Outcomes, Norms, Sequence) forces a specific structure that reduces improvisation. Use the structure, not the tool.

2. **Output enforcement: Write the spec as a Pydantic model.** The LLM generates a structured object with field constraints:
   ```python
   class ScriptSpec(BaseModel):
       script_name: str
       purpose: str  # 1 sentence
       inputs: list[InputSpec]
       outputs: list[OutputSpec]
       functions: list[FunctionSpec]  # name, params, return, logic (≤5 lines each)
       error_handling: list[str]  # specific error → specific action
       tests: list[str]  # bash one-liners that verify the script works
   ```

3. **Implementation prompt:**
   ```
   Write {script_name}.py that:
   - Takes these inputs: {inputs}
   - Produces these outputs: {outputs}
   - Has these functions: {functions}
   - Handles errors like this: {error_handling}
   - Must pass these tests: {tests}
   
   Rules:
   - temp=0.0
   - import paths from pipeline_paths.py (never hardcode)
   - Use @stamp decorator for all output
   - Write to tempfile → fsync → os.replace
   - Max 400 lines
   - If uncertain about anything, raise NotImplementedError with a clear message
   ```

**Why this works for local LLMs:**
- The spec is rigid — no room for "creative interpretation"
- Each function is ≤5 lines of logic — small enough for a weak model to handle correctly
- Tests are bash one-liners — the LLM can verify its own output
- "If uncertain, raise NotImplementedError" prevents hallucinated implementations
- No dependency on OpenSPDD or Spec-Kit tools — just a Pydantic model and a prompt

### 5.4 Recommendation

**Don't adopt either OpenSPDD or Spec-Kit as a tool.** Adopt OpenSPDD's REASONS Canvas *structure* as a spec template, encode it as a Pydantic model, and use it as the prompt format for local LLMs. Add Outlines for constrained decoding if the LLM struggles with JSON structure.

This is lighter, cheaper, and more effective for "not-smart" models than either full framework.

---

## §6 — CONSEQUENCES OF v3.0 ADOPTION

### 6.1 What Must Be Rewritten

| Artifact | From | To | Effort |
|----------|------|-----|--------|
| Pipeline core | 8-stage, 14 scripts, ~500K LOC | 6-stage, 6 scripts, ~2,700 LOC | Major rewrite |
| Classification | 13 scripts, ~180K LOC | Embedded in Stage 4, ~300 LOC | Eliminated |
| Validation | 14 scripts, ~250K LOC | Stage 5 verify.py, ~400 LOC | Collapsed |
| Storage | Anytype (proprietary) | SQLite + Parquet (open) | Architecture change |
| Schemas | schemas.py, 29K LOC | Pydantic v2 Literal types, ~300 LOC | Rewritten |
| Config | 37 files | 5 files | Simplified |

### 6.2 What Becomes Redundant

- **All 13 classification scripts** — replaced by SALSA inline + FastFit later
- **All governance/guard runtime checks** — Pydantic Literal types make them structurally unnecessary
- **All Phase 0-6 infrastructure** (guardian, IPC, consensus, self-healing, TUI) — single-script pipeline needs none of it
- **All reclassification/fix scripts** — no "wrong" labels to fix when labels are type-enforced
- **All eval loop / gate scripts** — replaced by simple BORP check + Phi-4-mini verify
- **All model routing / resolution scripts** — fixed model per stage, no routing needed

### 6.3 What Configs Become Redundant

- `channel_gate_config.yaml` — no channels to gate
- `enforcement.yaml` — Pydantic is the enforcement
- `intimacy_policy.yaml` — not in MVP
- `context_definitions.yaml` — simplified schema
- `space_routing.yaml` — Anytype deferred
- `anytype_*.json` — Anytype deferred
- `depth_disagreements.json` — no depth disagreements when classification is at source

### 6.4 Dependencies Removed

- `chromadb`, `lancedb`, `lance-namespace`, `rdflib` — replaced by sqlite-vec
- `langfuse`, `pydantic-ai` — no observability/agent framework needed
- Multiple model/router packages — fixed model assignments

### 6.5 Risk: What v3.0 Doesn't Address

| Gap | Risk | Mitigation |
|-----|------|------------|
| No SALSA implementation exists in codebase | Stage 4 classification is unproven | Triad Step 0 tests SALSA on OMLX before committing |
| No FastFit training pipeline | Classification quality at scale is unknown | Planned for 500+ labels — not in triad |
| No relationship extraction | FB graph (supports/contradicts) is empty | Deferred to post-MVP |
| No multi-modal ingestion | Only text pipeline exists | Schema supports media_refs — add later |
| No retrieval API | MCP server for agent queries not built | Deferred — need FBs first |
| 19,770 legacy FBs may be salvageable | Wasted extraction if principle_text survived | Check before triad (30 min) |

---

*Generated by: Goose | Schema: N/A | Pipeline commit: N/A*
