# Maxwell OS v3.0 — CONSTITUTION.md
> **Ratified:** 2026-07-18 | **Last Amended:** 2026-07-26 (v3.0 cluster-before-extract + D2115 C12 fix)
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
| **C12** | NEVER hardcode ANY value — paths, thresholds, model names, magic numbers MUST live in config/*.yaml. Code reads config at runtime. Applies to BOTH human-written AND LLM-generated code (review all agent output for hardcoded values). See §0b. |
| **C13** | Backups after batch writes |
| **C14** | Session seed loaded at startup |
| **C15** | Buglog — 5+ unresolved → append to all handoffs |
| **C16** | No silent errors — all except clauses must log and raise (ponytail: fail fast) |
| **C17** | Type hints on all function signatures (ponytail: type safety) |
| **C18** | Docstrings on all functions >5 lines (ponytail: documentation) |
| **C19** | No dead code — _OLD files → archive/ or deleted (ponytail: no dead code) |
| **C20** | No magic numbers — extract to config or named constants (Zed: explicit over implicit) |

| **C21** | Swappable Infrastructure — every component (inference, storage, memory, process, agent interface, sync, distribution) MUST be behind a protocol/abstraction. No pipeline logic touches a provider directly. |
| **C22** | Hybrid Sovereignty — local-first by default (C1, C3). User MAY opt into frontier API for non-verification roles via explicit toggle. Verification (R5) MUST always be local. API opt-in must be explicit, never default. |
| **C23** | Resilient by Design — system survives component failures, model deprecations, and OS changes without data loss or re-engineering. Every component has a documented replacement path. |
| **C24** | Hardware-Adaptive — auto-detect available RAM/CPU and select appropriate model size/quant. Minimum target: 16GB RAM. Must degrade gracefully (smaller model, fewer stages), never crash with OOM. |
| **C25** | Agent-Agnostic — expose knowledge via open protocols (MCP). No agent-specific coupling. Any MCP-compatible agent must work without Maxwell-specific code. |
| **C26** | Cross-Platform — all system-level operations (memory, process, I/O) must use cross-platform libraries (psutil, pathlib). No OS-specific syscalls in core logic. Target: macOS, Linux, Windows. |
| **C27** | Zero Future Tax — every architectural decision must leave a migration path open. Protocols defined before implementations. Feature flags for experimental features. No hardcoded assumptions that block future upgrades. |
| **C28** | Quality-Tiered — user chooses priority: quality / speed / accuracy. System adjusts batch sizes, model selection, verification depth accordingly. Lightweight by default. Bloat is opt-in. |

### §0b — C12: NO HARDCODING RULE (Expanded) (D2115)

This rule applies to ALL code — human-written AND LLM/agent-generated.

| Sub-rule | Description | Enforcement |
|----------|-------------|-------------|
| **C12a** | NEVER hardcode file paths. All paths MUST come from `config/pipeline_config.yaml` → `pipeline/pipeline_paths.py`. | `grep -rn '"/Users\|/tmp/' pipeline/` must return empty in non-test code. |
| **C12b** | NEVER hardcode strings. All configurable values MUST live in `config/*.yaml`, read at runtime. | `grep -rn '"[0-9]' pipeline/*.py` → check for magic numbers. |
| **C12c** | Config-first default. If a value CAN be configurable, it MUST be in YAML. No excuses. | Manual review. When in doubt, put in YAML. |
| **C12d** | LLM/agent output REVIEW RULE. Before accepting any LLM/agent-generated code, scan for hardcoded paths/strings/values. Reject and re-prompt if found. | Review step in every agentic workflow. |

**Rationale:** Hardcoded values are the #1 cause of drift between config and code. C12 was the most-violated rule in the v2.x audit (D2115). Making it explicit and enforceable for BOTH human and agentic output is critical to Maxwell's X-over-time survival.

## §1 — DATA SAFETY
- NEVER delete Anytype objects without explicit confirmation
- ONLY delete pipeline output via safe_delete.py
- NEVER overwrite protected files (DECISION-LOG.md, MASTER-TASK-REGISTER.md, AGENTS.md, .env, config/*.yaml)

## §2 — ARCHITECTURE

3 LAYERS: Pipeline (8-stage) → Knowledge (SQLite+FTS5+sqlite-vec+LightRAG) → Orchestration (Phase 2, skill.md standard)

MODELS: Gen=Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | Classify=gpt-oss-20b-MXFP4-Q8 | Embed=bge-m3 | NLI=MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (D2298)

PIPELINE (v3.0 cluster-before-extract, D2120: 8-stage): 0-convert → 0.5-metadata → 1-chunk → 1.3-prefilter → 1.5-FAISS-RNN-cluster → 2-convergent-extract(+hybrid-gate D2276) → 4-classify+dedup(D2120: Stage 3 removed) → 5-verify(DeBERTa-v3-large-NLI-only D2298, threshold 0.10 calibrated, fail-closed D2093) → 6-commit

STORAGE: SQLite (canonical) + sqlite-vec (vectors) + Parquet (portability) | TAXONOMY: 25 domains, 47 disciplines, max 5 per FB (D2066: dynamic, raw labels can dethrone canonicals)

## §3 — KEY DECISIONS (chronological)
R5: Generator≠Verifier | R7: temp=0.0 | R14: Schema stamps | D150: Max 5 domains | D316: Multi-label → RESOLVED by D2066 (dynamic multi-label, SALSA rejected)
D2003: Targeted re-engineering | D2004: 14 foundation fixes | D2005: UMAP over BIRCH | D2006: No cloud | D2007: bge-m3
D2008: 7-stage preserved | D2009: Confidence deferred | D2010: LangChain rejected | D2011: Buglog (C15)
D2013: Intent filter+FActScore | D2014: Modular deferred to Phase 2 | D2016: Lifetime license
D2019: UMAP confirmed | D2020: 3-layer OMLX defense + watchdog | D2023: Claim-type routing | D2024: Dichotomous SALSA → SUPERSEDED by D2066 (dynamic multi-label)
D2026: M1 re-sync | D2027: M2 OMLX watchdog | D2028: Local LLM reliability | D2029: Source provenance gate
D2030: Prompt version control (partial) | D2031: Drift detection (partial)
D2032: M3 conflict D316 vs D2024 (✅ RESOLVED — D2066: D316 depth-based multi-label adopted, D2024 SALSA rejected for classification)
D2033-D2038: Session consolidation (folder unified, governance synced, buglog formalized)
D2039-D2054: Handoff items registered (cleaning pipeline, contextual retrieval, SALSA, golden FBs, etc.)
D2055-D2065: Infrastructure independence (swappable protocols, MCP, CLI, packaging, quality tiers)
D2066: Dynamic canonical taxonomy — raw labels dethrone canonical when outnumbered by principle count
D2067: Cross-run incremental extraction — persistent principle index + LSH dedup across runs
D2068: oMLX 0.5.3 stress test — Phi-4-mini restored, model audit, 5 broken models identified
D2069: Stage 5 verification rewrite — Gemma cross-family verifier + embedding pre-filter (R5: Qwen≠Phi≠Gemma)
D2070: D2068 supersession — 3-model lineup restored (Gemma-E4B functional at 14.9 tok/s)
D2071: Phase 0.5 pre-processing quality — H1 markdown cleaning, H2 paragraph normalization, H4 conversion QC
D2072: Content type ontology — principle, process_template, process_instance, tool_instruction (v1 PT schema recovered + PI added)
D2073: Growth Edge as first-class object type — 7 categories (personal_idea→theoretical_investigation), 5 statuses (open→archived), promotion path to FB/PT/Project, human-created + pipeline-extracted
D2074: Golden few-shot v2.0 — 23 examples (18% pricing, 82% non-pricing), 11 types, real book passages, 3 hard negatives, 2 multi-principle segments, --golden flag wired into stage2_extract.py
C21-C28: Infrastructure independence rules (§0: swappable, hybrid sovereignty, resilient, adaptive, agent-agnostic, cross-platform, zero future tax, quality-tiered)

### Known Modularity Gaps (D2300 — 2026-08-12 Audit)
| Level | Gap | Status | Fix |
|-------|-----|--------|-----|
| **Component (C21 violation)** | `omlx_call.py` called directly from stage2/4/5 | 🔴 No InferenceProvider protocol (D2055 unimplemented) | ~160 LOC abstraction |
| **Component (C21 violation)** | `ollama_embed.py` called directly from stage1_5 | 🔴 No EmbeddingProvider protocol | ~80 LOC abstraction |
| **Component (C21 violation)** | SQLite hardcoded in stage6_commit.py | 🔴 No StorageBackend protocol (D2056 unimplemented) | ~100 LOC abstraction |
| **JSONL (strong)** | Stage checkpoints are self-contained JSONL | ✅ Each stage reads/writes independently — fully swappable internals | — |
| **Schema (partial)** | Pydantic FB model exists (schemas.py) but never instantiated | 🟡 Dead code — actual contract is implicit dict shapes | Remove or enforce |
| **Config (strong)** | pipeline_paths.py loads all values from pipeline_config.yaml | ✅ C12 enforced | — |

## §4 — PHASES
Phase 0: 14 fixes (~10h) → ✅ DONE (14/14 — T-0.1 verified, oMLX 0.5.3 stress test passed)
Phase 0.5: 4-layer cleaning (~3h) → IN PROGRESS
Phase 1: Intent filter + FActScore/DeBERTa (~1wk) → G1: ≥70% manual pass
Phase 2: Layer 2 orchestration (100+ FBs needed)
Phase 3: IP legal + packaging
Phase 4: Launch

## §5 — STARTUP
1. Read CONSTITUTION.md  2. Load agent/session_seed.yaml  3. Run OMLX stress test
4. Verify OMLX+Ollama  5. python3 pipeline/status.py

## §6 — FOLDER STRUCTURE
See governance/folder_protocol.md — books/ for source, stage{N}_{name}/{run_id}/ for self-contained output.

*Schema: 2.1 | Commit: v2.1.1 | Amended: 2026-07-22 (M1+II)*