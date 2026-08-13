# Maxwell OS v3.0 — Agent Loader
> **Loads at session start.** Points to CONSTITUTION.md (single source of truth).
> **v3.0:** Updated 2026-07-26 (cluster-before-extract, C12 enhanced, D2116 feeds).

<maxwell_os agent_version="3.0">

<!-- IRON RULES — NEVER break -->
<iron_rules>
- $0 marginal cost — all generation on local hardware (C1)
- Sovereign — all data and compute remain local (C3)
- No vendor lock-in — open formats, multiple model families (C2, C4)
- temp=0.0 on all generation scripts (R7)
- Generator ≠ Verifier — different model family for each (R5)
- Every persistent object stamped: schema_version, gen_model, pipeline_commit (R14)
- NEVER hardcode ANY value — paths, thresholds, model names, magic numbers → config/*.yaml (C12)
- ⚠️ C12 REVIEW-RULE: Before accepting any LLM/agent output, scan for hardcoded strings. Reject and re-prompt if found (C12d)
- Config-first default: if a value CAN be configurable, it MUST be in YAML. No excuses. (C12c)
- Crash-safe writes: tempfile → fsync → os.replace (C6)
- NEVER delete pipeline output — use pipeline/safe_delete.py (R-D410)
- Backups after batch writes: bash pipeline/backup_guardian.sh (C13)
- Buglog: 5+ unresolved → append to all handoffs (C15)
- No silent errors — except clauses must log AND raise (C16)
- AUTO-LOG BUGS: log to governance/buglog.md immediately upon discovery — never defer
- Type hints on all function signatures (C17)
- Docstrings on all functions >5 lines (C18)
- No dead code — _OLD files → archive/, no __pycache__ in repo (C19)
- No magic numbers — extract to named constants or YAML config (C20)
- Swappable Infrastructure — every component behind a protocol/abstraction (C21)
- Hybrid Sovereignty — local-first, API opt-in explicit (C22)
- Resilient by Design — survives component failures without data loss (C23)
- Hardware-Adaptive — auto-detect RAM, degrade gracefully (C24)
- Agent-Agnostic — expose via MCP, no agent-specific coupling (C25)
- Cross-Platform — psutil + pathlib, target macOS/Linux/Windows (C26)
- Zero Future Tax — protocols first, feature flags, no dead ends (C27)
- Quality-Tiered — lightweight default, bloat is opt-in (C28)
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
- CONSTITUTION.md (single source of truth, v3.0)
- DECISION-LOG.md (all architectural decisions D2000-D2310)
- MASTER-TASK-REGISTER.md (task tracker)
- config/decisions.yaml (auto-synced decision registry — 299 decisions)
- governance/buglog.md (8 open items including DELEGATE-001)
- governance/aggregated_remaining_tasks.md (prioritized task register)
- governance/folder_protocol.md (file creation rules)
- agent/session_seed.yaml (session config)
- feed.opml (technology feed sources for weekly research)
</knowledge_sources>

<!-- PIPELINE — 8-stage v3.0 (CONSTITUTION §2) -->
<pipeline>
  stage0_convert.py    → EPUB/PDF → MD (Pandoc/Docling)
  stage0_5_extract_metadata.py → MD → author/title (LLM)
  stage1_chunk.py      → MD → segments + SHA-256 dedup
  stage1_3_prefilter.py → regex pre-filter (D2080)
  stage1_5_embed_cluster.py → FAISS cosine + source diversity (cluster-before-extract)
  stage2_extract.py    → Clusters → convergent FBs (Qwen3-Coder, R5)
  # stage3_cluster.py  → REMOVED (D2120/D2198) — HDBSCAN dedup replaced by cluster-before-extract
  stage4_merge.py      → FBs → classified + formatted
  stage5_verify.py     → DeBERTa-v3-large NLI only (fail-closed, D2298)
  stage6_commit.py     → SQLite (sqlite-vec) + Parquet export
</pipeline>

<!-- DELEGATE RULES (DELEGATE-001 workaround verified 2026-07-26) -->
<delegate_rules>
- ALWAYS specify provider and model: delegate({provider: "maxwell_omlx", model: "..."})
- ⚠️ DELEGATION STATUS (2026-07-26, CONFIRMED):
  - ✅ gemma-4-E4B-it-MLX-4bit: CONFIRMED working. 0.48s response. Use for: code review, summarization, classification.
  - ✅ Qwen3-Coder-30B-A3B-Instruct-MLX-4bit: CONFIRMED working via curl. Use for: code generation.
  - ⚠️ Phi-4-mini-instruct-8bit: HALLUCINATES on open-ended research (BUG-053). Only for summarization WITH source text.
  - ❌ NEVER use custom_deepseek: reasoning_content passthrough bug (DELEGATE-001).
  - For research/fact-finding: use shell/curl directly. Do NOT delegate open-ended research.
- Memory budget: ~24GB of 64GB for all models combined
- Pipeline parallelism: use subprocess (pipeline/parallel.py), NOT delegates
</delegate_rules>

<!-- MODELS (CONSTITUTION §2 v3.0) -->
<models>
  Generator:    Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (OMLX)
  Verifier:     gpt-oss-20b-MXFP4-Q8 (OMLX)
  VerifierV2:   Phi-4-mini-instruct-8bit (OMLX, R5 cross-family, D2264)
  Embeddings:   bge-m3 (Ollama, 1024-dim)
  NLI:          MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (local, D2298)
</models>

<!-- PROTECTED FILES — never overwrite -->
<protected>
  CONSTITUTION.md, DECISION-LOG.md, MASTER-TASK-REGISTER.md
  AGENTS.md, .env, config/*.yaml, governance/*.md
</protected>

</maxwell_os>