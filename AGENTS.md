# Maxwell OS v2.1 — Agent Loader
> **Loads at session start.** Points to CONSTITUTION.md (single source of truth).
> **v2.1:** Updated 2026-07-21 (M1 re-sync). 7-stage pipeline. Correct models.

<maxwell_os agent_version="2.1">

<!-- IRON RULES — NEVER break -->
<iron_rules>
- $0 marginal cost — all generation on local hardware (C1)
- Sovereign — all data and compute remain local (C3)
- No vendor lock-in — open formats, multiple model families (C2, C4)
- temp=0.0 on all generation scripts (R7)
- Generator ≠ Verifier — different model family for each (R5)
- Every persistent object stamped: schema_version, gen_model, pipeline_commit (R14)
- NEVER hardcode paths — import from pipeline/pipeline_paths.py (C12)
- Crash-safe writes: tempfile → fsync → os.replace (C6)
- NEVER delete pipeline output — use pipeline/safe_delete.py (R-D410)
- Backups after batch writes: bash pipeline/backup_guardian.sh (C13)
- Buglog: 5+ unresolved → append to all handoffs (C15)
- No silent errors — except clauses must log AND raise (C16)
- Type hints on all function signatures (C17)
- Docstrings on all functions >5 lines (C18)
- No dead code — _OLD files → archive/, no __pycache__ in repo (C19)
- No magic numbers — extract to named constants or YAML config (C20)
- DRY: no code duplication across pipeline stages
- Functions <50 lines where possible
- Explicit error messages, never generic "an error occurred"
</iron_rules>

<!-- BOOT SEQUENCE -->
<boot>
1. Read CONSTITUTION.md
2. Load agent/session_seed.yaml
3. Run: python3 pipeline/omlx_watchdog.py --pre-stage
4. Run: just health
5. Run: python3 pipeline/status.py
</boot>

<!-- KNOWLEDGE SOURCES -->
<knowledge_sources>
- CONSTITUTION.md (single source of truth)
- DECISION-LOG.md (all architectural decisions D2000-D2031)
- MASTER-TASK-REGISTER.md (task tracker)
- governance/buglog.md (17 open bugs)
- governance/folder_protocol.md (file creation rules)
- agent/session_seed.yaml (session config)
</knowledge_sources>

<!-- PIPELINE — 7-stage (CONSTITUTION §2) -->
<pipeline>
  stage0_convert.py   → EPUB/PDF → MD (Pandoc/Docling)
  stage1_chunk.py     → MD → segments + SHA-256 dedup
  stage1.5            → Intent filter: semantic pre-filter (Phase 1)
  stage2_extract.py   → Segments → principles + MinHash dedup (Qwen3-Coder)
  stage3_cluster.py   → Embed (bge-m3) + UMAP + HDBSCAN
  stage4_merge.py     → Clusters → FBs + SALSA classify (Phi-4-mini, R5)
  stage5_verify.py    → FActScore + DeBERTa NLI + BORP (Phi-4-mini)
  stage6_commit.py    → SQLite (sqlite-vec) + Parquet export
</pipeline>

<!-- MODELS (CONSTITUTION §2) -->
<models>
  Generator:    Qwen3-Coder-30B-A3B-MLX-4bit (OMLX)
  Verifier:     Phi-4-mini-instruct-8bit (OMLX)
  Embeddings:   bge-m3 (Ollama, 1024-dim)
  NLI:          DeBERTa-v3-base-mnli (local)
</models>

<!-- PROTECTED FILES — never overwrite -->
<protected>
  CONSTITUTION.md, DECISION-LOG.md, MASTER-TASK-REGISTER.md
  AGENTS.md, .env, config/*.yaml, governance/*.md
</protected>

</maxwell_os>