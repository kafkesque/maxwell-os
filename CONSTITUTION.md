# Maxwell OS v2.0 — CONSTITUTION.md
> **Ratified:** 2026-07-18 | **Supersedes:** v1.2.1
> **Authority:** Single source of truth for ALL system rules.
> **Amendment:** Requires G7 human gate + decision log entry.

---

## §0 — HARD CONSTRAINTS

| # | Rule | Check |
|----|------|-------|
| **C1** | $0 marginal cost — all generation runs on local hardware | OMLX + Ollama only |
| **C2** | No vendor lock-in — every component has open-source replacement path | SQLite + Parquet over proprietary DBs |
| **C3** | Sovereign — all data and compute remain local | No cloud APIs for core pipeline |
| **C4** | Future-proof — no single-provider dependency | Open formats, multiple model families |
| **C5** | Zero bloat — no dependency added without proven need | Test suite gate |
| **C6** | Crash-safe writes: tempfile → fsync → os.replace | `pipeline/io_guard.py` |
| **C7** | Checkpoint every stage — resumeable | `data/checkpoints/` per stage |
| **C8** | Generator ≠ Verifier — different model family for each (R5) | Qwen3.6 generates, Phi-4-mini verifies |
| **C9** | temp=0.0 on all generation scripts (R7) | Enforced in `pipeline/omlx_call.py` |
| **C10** | Every persistent object stamped: schema_version, gen_model, pipeline_commit (R14) | `pipeline/stamp.py` decorator |
| **C11** | All imports ⊂ requirements.txt | Pre-commit check |
| **C12** | NEVER hardcode paths — import from `pipeline/pipeline_paths.py` | Pre-commit check |
| **C13** | Backups after batch writes | `bash pipeline/backup_guardian.sh` |
| **C14** | Session seed loaded at startup | `agent/session_seed.yaml` |

## §1 — DATA SAFETY

| # | Rule |
|---|------|
| **R-D413** | NEVER delete Anytype objects without Maxwell's explicit written confirmation |
| **R-D410** | ONLY delete pipeline output via `pipeline/safe_delete.py` |
| **R-D413b** | NEVER run `pipeline/nuke_anytype.py` without Maxwell's explicit permission |
| **R-D824** | NEVER overwrite protected files (DECISION-LOG.md, MTR, AGENTS.md, .env, config/*.yaml) |

## §2 — ARCHITECTURE

### 2.1 Three-Layer Model

```
3. LOOPS      — Agentic automation cycles (post-MVP)
2. FRAMEWORK  — FBs in SQLite with hybrid retrieval (post-triad)
1. PIPELINE   — 6-stage extraction: Convert → Chunk → Extract → Cluster → Merge → Verify → Commit
```

### 2.2 Model Assignments

| Role | Model | Stage |
|------|-------|-------|
| Generator | Qwen3.6-35B-A3B-4bit (OMLX) | Stages 2, 4 |
| Verifier | Phi-4-mini-instruct-8bit (OMLX) | Stage 5 |
| Embeddings | nomic-embed-text (Ollama) | Stage 3 |
| Fallback | Gemma-4-26B-A4B (OMLX) | Cross-family verify (R5) |

### 2.3 Storage

| Layer | Technology | Format |
|-------|-----------|--------|
| Canonical | SQLite | `data/maxwell.db` |
| Vectors | sqlite-vec | Embedded in SQLite |
| Portability | Parquet | `data/fbs_snapshot_*.parquet` |
| Relationships | SQLite | `relationships` table |
| Presentation | Anytype | Post-MVP push |

## §3 — PIPELINE (6 STAGES)

| Stage | Script | Model | Input → Output |
|-------|--------|-------|----------------|
| 0 | `stage0_convert.py` | Pandoc/Docling | EPUB/PDF → MD |
| 1 | `stage1_chunk.py` | Python | MD → segments + SHA-256 dedup |
| 2 | `stage2_extract.py` | Qwen3.6 | Segments → principles + MinHash dedup |
| 3 | `stage3_cluster.py` | nomic-embed-text + HDBSCAN | Principles → clusters |
| 4 | `stage4_merge.py` | Qwen3.6 + SALSA | Clusters → FBs + classify |
| 5 | `stage5_verify.py` | Phi-4-mini + Human | FBs → verified FBs |
| 6 | `stage6_commit.py` | Python | Verified FBs → SQLite + Parquet |

## §4 — TAXONOMY

- 25 domains (see `config/taxonomy_v5.yaml`)
- 47 disciplines (see `config/taxonomy_v5.yaml`)
- Max 5 domains per FB, unranked (D150)
- Multi-label, content-based classification (D316)

## §5 — KEY DECISIONS CARRIED FORWARD

| ID | Decision |
|----|----------|
| **R5** | Generator ≠ Verifier |
| **R7** | temp=0.0 on all generation |
| **R14** | Schema stamps on all output |
| **D150** | Max 5 domains per FB |
| **D316** | Multi-label locked |
| **D1057** | Lazy-load OMLX models per stage |
| **D1058** | Jargon decontamination |

## §6 — STARTUP SEQUENCE

1. Read CONSTITUTION.md
2. Load `agent/session_seed.yaml`
3. Verify OMLX + Ollama running
4. Run `python3 pipeline/status.py`

## §7 — FOLDER STRUCTURE

See `governance/folder_protocol.md`

---

*Schema version: 2.0 | Pipeline commit: v2.0-init | Ratified: 2026-07-18*
