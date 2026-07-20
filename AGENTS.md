# Maxwell OS v2.0 — Agent Loader
> **Loads at session start.** Points to CONSTITUTION.md (single source of truth).
> **v2.0:** Simplified. Pipeline-focused. No governance bloat.

<maxwell_os agent_version="2.0">

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
</iron_rules>

<!-- BOOT SEQUENCE -->
<boot>
1. Read CONSTITUTION.md
2. Load agent/session_seed.yaml
3. Run: just health
4. Run: python3 pipeline/status.py
</boot>

<!-- KNOWLEDGE SOURCES -->
<knowledge_sources>
- CONSTITUTION.md (single source of truth)
- config/decisions.yaml (active decision registry — when created)
- governance/folder_protocol.md (file creation rules)
- agent/session_seed.yaml (session-specific config)
</knowledge_sources>

<!-- PIPELINE — v3.0 Architecture -->
<pipeline>
  stage0_convert.py   → EPUB/PDF → MD (Pandoc/Docling)
  stage1_chunk.py     → MD → segments + SHA-256 dedup
  stage2_extract.py   → Segments → principles + MinHash dedup (Qwen3.6)
  stage3_cluster.py   → Embed + HDBSCAN + semantic dedup
  stage4_merge.py     → Clusters → FBs + SALSA classify (Qwen3.6)
  stage5_verify.py    → BORP + factual check (Phi-4-mini) + human queue
  stage6_commit.py    → SQLite + Parquet export
</pipeline>

<!-- PROTECTED FILES — never overwrite -->
<protected>
  CONSTITUTION.md, DECISION-LOG.md, MASTER-TASK-REGISTER.md
  AGENTS.md, .env, config/*.yaml, governance/*.md
</protected>

</maxwell_os>
