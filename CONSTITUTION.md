# Maxwell OS v2.1 — CONSTITUTION.md
> **Ratified:** 2026-07-18 | **Last Amended:** 2026-07-21 (M1 re-sync)
> **Authority:** Single source of truth for ALL system rules.

## §0 — HARD CONSTRAINTS

| # | Rule |
|----|------|
| **C1** | $0 marginal cost — all generation on local hardware. NO cloud. |
| **C2** | No vendor lock-in — every component has open-source replacement path |
| **C3** | Sovereign — all data and compute remain local |
| **C4** | Future-proof — no single-provider dependency |
| **C5** | Zero bloat — no dependency without proven need |
| **C6** | Crash-safe writes: tempfile → fsync → os.replace |
| **C7** | Checkpoint every stage — resumable |
| **C8** | Generator ≠ Verifier (R5) — different model families |
| **C9** | temp=0.0 on all generation (R7) |
| **C10** | Every persistent object stamped (R14) |
| **C11** | All imports ⊂ requirements.txt |
| **C12** | NEVER hardcode paths — all from config/pipeline_config.yaml |
| **C13** | Backups after batch writes |
| **C14** | Session seed loaded at startup |
| **C15** | Buglog — 5+ unresolved → append to all handoffs |
| **C16** | No silent errors — all except clauses must log and raise (ponytail: fail fast) |
| **C17** | Type hints on all function signatures (ponytail: type safety) |
| **C18** | Docstrings on all functions >5 lines (ponytail: documentation) |
| **C19** | No dead code — _OLD files → archive/ or deleted (ponytail: no dead code) |
| **C20** | No magic numbers — extract to config or named constants (Zed: explicit over implicit) |

## §1 — DATA SAFETY
- NEVER delete Anytype objects without explicit confirmation
- ONLY delete pipeline output via safe_delete.py
- NEVER overwrite protected files (DECISION-LOG.md, MASTER-TASK-REGISTER.md, AGENTS.md, .env, config/*.yaml)

## §2 — ARCHITECTURE

3 LAYERS: Pipeline (7-stage) → Knowledge (SQLite+FTS5+sqlite-vec) → Orchestration (Phase 2)

MODELS: Gen=Qwen3-Coder-30B-A3B-MLX-4bit | Verify=Phi-4-mini-8bit | Embed=bge-m3 | NLI=DeBERTa-v3-mnli

PIPELINE (7 stages): 0-convert → 1-chunk → 1.5-intent-filter → 2-extract → 3-cluster(UMAP+HDBSCAN) → 4-merge(SALSA) → 5-verify(FActScore+DeBERTa) → 6-commit

STORAGE: SQLite (canonical) + sqlite-vec (vectors) + Parquet (portability) | TAXONOMY: 25 domains, 47 disciplines, max 5 per FB

## §3 — KEY DECISIONS (chronological)
R5: Generator≠Verifier | R7: temp=0.0 | R14: Schema stamps | D150: Max 5 domains | D316: Multi-label (M3 under review)
D2003: Targeted re-engineering | D2004: 14 foundation fixes | D2005: UMAP over BIRCH | D2006: No cloud | D2007: bge-m3
D2008: 7-stage preserved | D2009: Confidence deferred | D2010: LangChain rejected | D2011: Buglog (C15)
D2013: Intent filter+FActScore | D2014: Modular deferred to Phase 2 | D2016: Lifetime license
D2019: UMAP confirmed | D2020: 3-layer OMLX defense + watchdog | D2023: Claim-type routing | D2024: Dichotomous SALSA
D2026: M1 re-sync | D2027: M2 OMLX watchdog | D2028: Local LLM reliability | D2029: Source provenance gate
D2030: Prompt version control | D2031: Drift detection

## §4 — PHASES
Phase 0: 14 fixes (~10h) → G0: 130 books ≥5 clusters
Phase 0.5: 4-layer cleaning (~3h)
Phase 1: Intent filter + FActScore/DeBERTa (~1wk) → G1: ≥70% manual pass
Phase 2: Layer 2 orchestration (100+ FBs needed)
Phase 3: IP legal + packaging
Phase 4: Launch

## §5 — STARTUP
1. Read CONSTITUTION.md  2. Load agent/session_seed.yaml  3. Run OMLX stress test
4. Verify OMLX+Ollama  5. python3 pipeline/status.py

## §6 — FOLDER STRUCTURE
See governance/folder_protocol.md — books/ for source, stage{N}_{name}/{run_id}/ for self-contained output.

*Schema: 2.1 | Commit: v2.1-Phase0 | Amended: 2026-07-21 (M1)*