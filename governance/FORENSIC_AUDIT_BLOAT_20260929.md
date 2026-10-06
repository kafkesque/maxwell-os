# FORENSIC AUDIT — BLOAT + PRE-FLIGHT (2026-09-29)

Scope: read-only. NO deletions performed (owner ratification required). All sizes from `du`/`ls` on 2026-09-29.
Whole project = 33G. Biggest consumers: `knowledge pipeline/` 16G, `archive/` 16G, `.venv_laya` 259M, `governance/` 154M.

## 1. Bloat ledger

### 1a. knowledge pipeline/ (16G active tree)
| Path | Size | Class | Reason |
|---|---|---|---|
| classifier_depth, _clean, _cleanC, _core, _silver, _silverC (6 dirs) | 3.4G | ARCHIVE | depth training iterations, macro-F1 0.479 < 0.85 gate; depth now served by gpt-oss-20b (D2549/D3259) |
| classifier_modernbert, _p4, _p4_clean (3 dirs) | 1.7G | ARCHIVE | intermediate auto-sorter runs; superseded by classifier_modernbert_p5final |
| stage1_chunk/rechunk-20260929/ | 708M | ARCHIVE | unsanitized re-chunk (300,270 segs), fully superseded by rechunk-v4-20260929 |
| stage1_chunk/{t11,latest}/checkpoint.jsonl.prefilter_backup | 1.5G | ARCHIVE | S1.3 auto-backups; post-prefilter checkpoint is the consumed artifact |
| maxwell.db.bak_* (8 older of 10) | ~1.2G | ARCHIVE | keep 2 newest (20260929_231825, 20260929_230650); move rest to archive/db_backups/ |
| maxwell.db.pre_* (3 files) | ~450M | ARCHIVE | pre-operation snapshots |
| checkpoints/stage1_chunk_full/filtered/nuke/tight.jsonl | ~209M | ARCHIVE | Jul-21 superseded checkpoints |
| parquet/fbs_snapshot_*.parquet (older) | ~300M | ARCHIVE | keep final + 2 newest |
| root *.log (31 files) | 1.6M | ARCHIVE | canary_rerun_*, runner_t11_*, s2_refix*, s4_retry*, etc. |
| __pycache__ (6 dirs) | 3.2M | DELETE | regenerable (C19) |
| diagnostic_diagnostic_20260811_232853.db* | 4.9M | DELETE | diagnostic sqlite |

**Recoverable ≈ 9.5G** (archive) + ~8M (delete).

### 1b. governance/ (154M)
| Path | Size | Class | Reason |
|---|---|---|---|
| backups/ (joint_vote_checkpoint_*.jsonl) | 55M | ARCHIVE/DELETE | runtime artifacts, gitignored, regenerable |
| r2_definition_nli_20260920.json (non-v2) | 13M | ARCHIVE | superseded by _v2 |
| joint_vote_production_checkpoint.jsonl + .dedup | 24M | ARCHIVE/DELETE | runtime checkpoint, regenerable |
| nli_label_audit.json + .checkpoint.jsonl | 15M | ARCHIVE/DELETE | audit artifact; .checkpoint gitignored |
| depth_vote_checkpoint.jsonl, model_eval_checkpoint.jsonl, s4_review_queue.jsonl, METRICS.jsonl | ~4.7M | ARCHIVE/DELETE | runtime checkpoints |
| 41 × PRE_* files | small | ARCHIVE | pre-op snapshots |
| depth_*_train/twin/silver*.yaml | ~4.6M | ARCHIVE | training-set snapshots, superseded by golden |

**Recoverable ≈ ~120M.**

### 1c. top-level
- `archive/` 16G — already archived; optionally prune bak_sweep (11G) + session_20260923/scratch/backup (5.3G) further.
- `.venv_laya` 259M — keep (venv). `.pytest_cache` 52K + `.ruff_cache` 196K — DELETE (regenerable).

## 2. Pre-flight risk register (does anything break/cascade/drift?)

1. **Classifier config names 3 paths (conflict) — SAFE.** `pipeline_config.yaml:29` (classifier_training → p5final), `:352` (student_preclassifier_checkpoint → hierarchical), `student_classifier.py:44` DEFAULT (p5final). BUT `student_preclassifier_enabled: false` ⇒ both dormant; S4 uses gpt-oss-20b fallback. Archiving the 9 unreferenced iterations breaks nothing. KEEP p5final + hierarchical.
2. **run.default_id=t11 vs 7 scripts hardcoding "latest" (drift/blindspot) — FLAGGED.** run_diagnostic.py, metrics.py, n2_watchdog.py, probe_run.py, golden_sampler.py, stage1_5_domain_cluster.py all default to `latest/`; config says `t11`. `latest/` is STALE (Aug 4, unsanitized). Pointer flip MUST repoint BOTH default_id AND latest/ atomically (D-2709 gate). HOLD latest/ + t11/ until then.
3. **prefilter_backup (1.5G) — no cascade.** S1.3 auto-backup; downstream consumes post-prefilter checkpoint only.
4. **rechunk-20260929 vs v4 — no gap.** v4 (295,440 sanitized) is the canonical baseline; rechunk-20260929 is a strict superset-lossy predecessor.
5. **DB backups — C13/R-D410 satisfied.** Keep 2 newest .bak_*; archive older; all archival via archive/ convention + pipeline/safe_delete.py (no hard-delete of pipeline output).
6. **vec0 "no such module" on vec_fbs/vec_fbs_ctx — pre-existing latent, NOT bloat-induced.** Re-verify at S6 rerun with sqlite-vec loaded.
7. **books → ../maxwell os/… (hidden cross-project symlink) — blindspot, NOT bloat.** v4 re-chunk read from stage0 t11 checkpoint, not this symlink, so rerun is unaffected. Note as fragility.
8. **.git is a gitfile → /Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git — external gitdir.** Not bloat; audit artifact.
9. **No error leak (C16).** All sync writes atomic (tempfile → fsync → os.replace); script raises on any guard mismatch.

## 3. HOLD (rollback safety per D-2713)
stage1_chunk/t11 (1.4G), stage1_chunk/rechunk-v4-20260929 (693M), stage1_chunk/latest (1.4G, flip target), maxwell.db (156M), classifier_modernbert_p5final + classifier_hierarchical (referenced), stage2/4/5/6 t11 dirs (2.5G).

## 4. Verdict
Nothing breaks, cascades, or drifts from the proposed archival. Two latent items (latest-vs-default_id drift; vec0 module) are pre-existing and out of bloat scope — carry into next steps. NO files were deleted or moved; this is a ratification request.
