# Dropbox Selective-Sync Execution List — Maxwell OS

> **Date:** 2026-08-28 · **Author:** governance (D2482 session)
> **Purpose:** stop Dropbox from continuously syncing ~5.5 GB of intermediate
> pipeline churn (which causes I/O contention + stale-file drift during long
> S2/S4/S5 runs) **without losing offsite backup of the high-value source files.**

## TL;DR — do NOT switch Dropbox off. Exclude the churny dirs below.

---

## 1. EXCLUDE from sync (churn / regenerable — safe to un-sync)

| Path | Size | Why exclude |
|---|---|---|
| `knowledge pipeline/stage1_chunk/` | 2.9 GB | chunked segments — regenerable from books |
| `knowledge pipeline/stage5_verify/` | 880 MB | NLI verification output — intermediate |
| `knowledge pipeline/stage2_extract/` | 824 MB | S2 checkpoints — rewritten every run |
| `knowledge pipeline/checkpoints/` | 220 MB | crash-recovery checkpoints — high write churn |
| `knowledge pipeline/stage1_5_embed_cluster/` | 144 MB | FAISS/embeddings — regenerable |
| `knowledge pipeline/stage4_merge/` | 40 MB | S4 output — rewritten every run |
| `knowledge pipeline/parquet/` | 19 MB | S6 export — regenerable from SQLite |
| `knowledge pipeline/stage0_convert/` | 1.5 MB | converted MD — regenerable from books |
| `temp/` | 2 MB | scratch/probes — disposable |
| `.git/` | 54 MB | redundant — Git remote already backs this up |
| `**/__pycache__/` | — | Python bytecode — regenerable |

**Total excluded: ~5.5 GB** (≈98% of the churn).

## 2. KEEP synced (small + high-value = your actual intellectual property)

| Path | Size | Why keep |
|---|---|---|
| `config/` | small | ontology, golden sets, pipeline config |
| `pipeline/` | small | all source code |
| `governance/` | small | buglog, decisions, tasks |
| `DECISION-LOG.md`, `CONSTITUTION.md`, `MASTER-TASK-REGISTER.md`, `AGENTS.md` | small | single source of truth |
| `agent/` | small | session seed, session config |
| `tests/`, `scripts/`, `justfile`, `.env` | small | reproducible build/test |
| `knowledge pipeline/books/` | 493 MB | **source corpus — irreplaceable, keep** |
| `feed.opml` | small | research feeds |

## 3. Execution steps (Dropbox macOS)

1. **Dropbox app → Preferences → Sync → Selective Sync** (or right-click the
   Dropbox folder in Finder → "Make online-only" per-folder).
2. Uncheck **each path in §1** (one by one, or the parent `knowledge pipeline/`
   then re-check `books/` if you want finer granularity).
3. Keep **§2 paths** checked (local + synced).
4. Alternatively, for a **temporary** pause during a long S4/DSPy run:
   **Dropbox menu bar → Pause syncing** (resume after the run).

## 4. Verification

- [ ] `du -sh "knowledge pipeline"` still shows ~5.5 GB but Dropbox status shows
      "up to date" without a spinning/uploading state.
- [ ] After a full S2/S4 run, Dropbox is NOT re-uploading `stage2_extract/`,
      `stage5_verify/`, `checkpoints/`, `stage4_merge/`.
- [ ] `books/`, `config/`, `pipeline/`, `governance/`, `DECISION-LOG.md` still
      show the green ✓ sync badge.

## 5. Risk notes

- **Backup gap:** excluded dirs are *not* cloud-backed. They are **regenerable**
  (chunks/embeddings/checkpoints/exports), except confirm `books/` is KEPT.
- **If you need remote access** to excluded dirs, re-enable them on demand —
  nothing is deleted, only un-synced.
