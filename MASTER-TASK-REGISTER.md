# Maxwell OS v2.1 — CONSOLIDATED MASTER TASK REGISTER
> **Generated:** 2026-07-21 20:00 | **Sources:** DECISION-LOG.md, agent/session_seed.yaml,  
> ULTIMATE-CROSS-EXAMINATION-2026-07-21.md, ULTIMATE-CROSS-EXAMINATION-HANDOFF.md,  
> temp/asad.txt, buglog.md, MASTER-TASK-REGISTER.md (git recovery)
> **Rule:** Done tasks → move to DONE section. Only undone tasks stay on top.

---

## 🔴 CRITICAL (Must do NOW)

| # | Task | Source | Effort |
|---|------|--------|--------|
| C1 | pip install umap-learn | G0.6 | ✅ DONE |
| C2 | Resolve M3: D316 (multi-label) vs D2024 (SALSA dichotomous) | D2032 | G7 DECISION |
| C3 | OMLX memory stress test (T-0.1): 5 pipeline runs, vm_stat | Gap A, D2020 | 15 min |
| C4 | Install pytest, run 12/12 chunker tests | G0.1 | ✅ DONE |
| C5 | Fix BUG-015: datasketch import must raise, not print() | BUG-015, C16 | ✅ DONE |
| C6 | Adopt C16-C20 in CONSTITUTION, AGENTS, .ponytail.yaml | Ponytail analysis | ✅ DONE |

---

## 🟠 HIGH — Phase 0.5 (Pre-Processing Quality)

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| H1 | clean_markdown() — strip formatting artifacts | 30 | asad.txt #15 | ⬜ |
| H2 | normalize_paragraphs() — 30-250 word paragraphs | 30 | asad.txt #16 | ⬜ |
| H3 | Integration wiring (Layer 4) | 20 | asad.txt #17 | ⬜ |
| H4 | Post-conversion quality check (garbled PDFs) | 15 | asad.txt #18 | ⬜ |
| H5 | Re-run 130 pricing books with fixed pipeline | — | Gap B | ⬜ |
| H6 | Run brand strategy domain (cross-domain validation) | — | Gap B/F | ⬜ |

---

## 🟢 HIGH — Phase 1 (Intent + Verification)

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| V1 | stage1_5_intent.py — semantic pre-filter | 80 | asad.txt #20, D2013 | ⬜ |
| V2 | stage5_verify_v2.py — FActScore + DeBERTa NLI | 200 | asad.txt #21, D2013 | ⬜ |
| V3 | Golden few-shot examples YAML for Stage 2/4 prompts | — | asad.txt #22, D2045 | ⬜ |
| V4 | Source-substring gate in stage2 (~30 LOC) | 30 | asad.txt #23, D2043 | ⬜ |
| V5 | --intent flag wires to semantic filter | 10 | asad.txt #24 | ⬜ |
| V6 | NLI pre-merge coherence check (DeBERTa pairwise) | ~30 | asad.txt #27, D2044 | ⬜ |
| V7 | Claim-type routing: FACT→DeBERTa, CAUSAL→Phi-4, STAT→source | ~50 | Gap E, D2023 | ⬜ |
| V8 | Author-weighted BORP (~30 LOC) | ~30 | Gap C, D2053-C | ⬜ |
| V9 | Golden FB calibration data injected into prompts | — | asad.txt #30, D2052 | ⬜ |
| V10 | SALSA test on 20 hand-labeled FBs (BL5) | — | BL5, D2046 | ⬜ |
| V11 | Source provenance verification gate (BL1) | ~30 | BL1, D2029 | ⬜ |
| V12 | DeBERTa benchmark on M1 Max (BL3) | — | BL3 | ⬜ |

---

## 🔷 MEDIUM — Phase 1.5 (Modularize)

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| M1 | Spike: Outlines/XGrammar + OMLX compatibility | — | asad.txt #25, D2041 | ⬜ |
| M2 | DFlash speculative decoding verification | — | asad.txt #26, D2042 | ⬜ |
| M3 | InferenceProvider Protocol + OMLX/Ollama impl | 40 | asad.txt #38, D2014 | ⬜ |
| M4 | StagePlugin ABC + StageRegistry | 80 | asad.txt #39 | ⬜ |
| M5 | Embedding model versioning in schema | 10 | asad.txt #40 | ⬜ |
| M6 | Prompt versioning in output metadata | 5 | asad.txt #41 | ⬜ |
| M7 | Config-driven model assignments (hardcoded→YAML) | 25 | asad.txt #42 | ⬜ |

---

## 🔵 MEDIUM — Phase 1 Cross-Exam Gaps

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| G1 | Drift detection implementation (BL7, D2031) | ~50 | BL7 | ⬜ |
| G2 | Embedding migration protocol (CT1) | ~60 | CT1 | ⬜ |
| G3 | Prompt version control SHA-256 hashing (BL2, D2030) | ~40 | BL2 | ⬜ |
| G4 | UMAP fallback definition (BL6) | — | BL6 | ⬜ |
| G5 | In-memory dedup persistence (BT4) | ~10 | BT4 | ⬜ |
| G6 | ollama.stop() after Stage 3 (BT5) | ~3 | BT5 | ⬜ |
| G7 | Stage 5 bottleneck analysis (BT1) | — | BT1 | ⬜ |

---

## 🔵 Phase 2 — Layer 2 (The Product)

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| L1 | Trust Ledger schema + log execution outcomes | 25 | asad.txt #43 | ⬜ |
| L2 | fb_reliability scoring (STABLE/WATCH/UNSTABLE/GARBAGE) | 40 | asad.txt #44 | ⬜ |
| L3 | Recipe compiler: PT + consulted FBs → Goose YAML | 80 | asad.txt #45, D2049 | ⬜ |
| L4 | retrieve.py v2 with pre-computed embeddings (BUG-004) | 40 | asad.txt #46 | ⬜ |
| L5 | Hybrid search: FTS5 + sqlite-vec RRF | 40 | asad.txt #47 | ⬜ |
| L6 | 3-zone body template enforcement | 50 | asad.txt #48 | ⬜ |
| L7 | Conductor Loop: trigger→retrieve→execute→verify | 50 | asad.txt #49 | ⬜ |
| L8 | Parquet + LanceDB + DuckDB canonical storage (D2048) | — | asad.txt #50 | ⬜ |

---

## 🟠 Phase 3 — Scale + Access

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| S1 | FastAPI REST: /query, /recommend, /explain, /feedback | 150 | asad.txt #51 | ⬜ |
| S2 | MCP server wrapper (read-only tools for agents) | 80 | asad.txt #52 | ⬜ |
| S3 | Web ingestion: SearXNG + Trafilatura + Crawl4AI | 100 | asad.txt #53 | ⬜ |
| S4 | Multi-domain support (beyond pricing) | 40 | asad.txt #54 | ⬜ |
| S5 | fb_relationships table (supports/contradicts/extends) | 30 | asad.txt #55 | ⬜ |
| S6 | IP legal consult (Gap D, D2025) | — | Gap D | ⬜ |

---

## 🟤 Phase 4 — Onboard + Monetize

| # | Task | LOC | Source | Status |
|---|------|-----|--------|--------|
| O1 | Onboarding CLI: VALIDATE + DISCOVER modes | 200 | asad.txt #57 | ⬜ |
| O2 | ExtractionProfile JSON (onboarding → pipeline bridge) | 30 | asad.txt #58 | ⬜ |
| O3 | Lifetime license billing (D2050) | 50 | asad.txt #59 | ⬜ |
| O4 | Multi-tenancy (user_id, private FBs) | 50 | asad.txt #60 | ⬜ |
| O5 | Web UI (minimal) | 100 | asad.txt #61 | ⬜ |

---

## ⚫ Phase 5 — Moat

| # | Task | Source | Status |
|---|------|--------|--------|
| Z1 | Claim graph (cross-FB consistency) | asad.txt #62 | ⬜ |
| Z2 | Dynamic source reliability (author/book weighting) | asad.txt #63 | ⬜ |
| Z3 | Self-healing loop (auto-flag degrading FBs) | asad.txt #64 | ⬜ |
| Z4 | Multi-model adjudication (Critic: Qwen3-0.6B) | asad.txt #65 | ⬜ |
| Z5 | Contextual Retrieval (Anthropic 2024, D2040) | asad.txt #66 | ⬜ |
| Z6 | FastFit classifier on 500+ FBs (D2051) | asad.txt #67 | ⬜ |
| Z7 | pgvector migration path | asad.txt #68 | ⬜ |

---

## 📋 GAP REGISTER

| Gap | Description | Gate | Status |
|-----|-------------|------|--------|
| A | OMLX kernel memory leak untested (GitHub #2184) | Stress test BEFORE Phase 0 | ⬜ |
| B | Single-domain bias (only pricing tested) | Run brand strategy after Phase 0 | ⬜ |
| C | No author diversity in BORP | Add in V8 (~30 LOC) | ⬜ |
| D | IP/copyright risk unexamined | Legal consult before Phase 3 | ⬜ |
| E | DeBERTa weak on causal/statistical claims | Claim-type routing (V7) | ⬜ |
| F | Onboarding conceptual model unresolved | Design from scratch in Phase 4 | ⬜ |

---

## 🐛 OPEN BUGS (from buglog.md)

| Bug | Severity | Symptom | Status |
|-----|----------|---------|--------|
| BUG-004 | 🟠 HIGH | Vector search re-embeds entire DB every query | Phase 1 |
| BUG-015 | 🟡 MEDIUM | Silent datasketch import failure | C5 |
| BUG-017 | 🔴 CRITICAL | OMLX kernel memory leak untested | T-0.1 / C3 |

---

## 🟢 NEW GOVERNANCE RULES (from ponytail-lite/cursor-rules analysis)

| Rule | Description | Priority |
|------|-------------|----------|
| C16 | No silent errors — all except clauses must log or raise | 🔴 CRITICAL |
| C17 | Type hints on all function signatures | 🟠 HIGH |
| C18 | Docstrings on all functions >5 lines | 🟠 HIGH |
| C19 | No dead code — _OLD files → archive/ | 🟡 MEDIUM |
| C20 | Magic numbers extracted to config or named constants | 🟡 MEDIUM |

---

## ✅ DONE

| # | Task | When |
|---|------|------|
| P0.1 | clean_line("") returns "" not None | 2026-07-21 |
| P0.2 | split_on_headings() paragraph-aware (list[list[str]]) | 2026-07-21 |
| P0.3 | Remove numbered-list from SKIP_PATTERNS | 2026-07-21 |
| P0.4 | MIN_CHUNK_WORDS 30→10 | 2026-07-21 |
| P0.5 | PCA → UMAP(random_state=42, cosine) | 2026-07-21 |
| P0.6 | nomic-embed-text → bge-m3 | 2026-07-21 |
| P0.7 | HDBSCAN min_cluster_size 3→8 | 2026-07-21 |
| P0.8 | _load_cluster_map() in stage5_verify.py | 2026-07-21 |
| P0.9 | get_pipeline_run_id() singleton in stamp.py | 2026-07-21 |
| P0.10 | VERIFY_MODEL for SALSA (R5 fix) | 2026-07-21 |
| P0.11 | sqlite_vec.load(conn) before virtual table | 2026-07-21 |
| P0.12 | omlx_watchdog.py replaces pkill guard | 2026-07-21 |
| P0.13 | Cloud code audit — none found | 2026-07-21 |
| P0.14 | Model audit — phantoms nuked, bge-m3 wired | 2026-07-21 |
| M1 | CONSTITUTION.md re-synced v2.1 | 2026-07-21 |
| M2 | OMLX server watchdog (pipeline/omlx_watchdog.py) | 2026-07-21 |
| G1 | DECISION-LOG.md: D2026-D2054 (56 decisions) | 2026-07-21 |
| G2 | agent/session_seed.yaml: rewritten v2.1 | 2026-07-21 |
| G3 | AGENTS.md: updated v2.1 (models, 7-stage, boot) | 2026-07-21 |
| G4 | LaunchAgents disabled (com.maxwell.*.plist) | 2026-07-21 |
| G5 | Knowledge pipeline consolidated | 2026-07-21 |
| G6 | Project folder unified (5 variants → 1) | 2026-07-21 |
| G7 | Buglog updated (22 bugs, 19 resolved) | 2026-07-21 |
| G8 | 29/29 pipeline .py syntax check passed | 2026-07-21 |
| G9 | umap-learn installed (v0.5.12) | 2026-07-21 |
| D1 | D2032: M3 conflict logged | 2026-07-21 |
| D2 | D2033-D2038: Session decisions logged | 2026-07-21 |
| D3 | D2039-D2053: Handoff items registered | 2026-07-21 |
| D4 | D2054: asad.txt registered | 2026-07-21 |
| B1 | BUG-018: stage1_chunk.py orphaned if → FIXED | 2026-07-21 |
| B2 | BUG-019: pipeline_paths.py missing exports → FIXED | 2026-07-21 |
| B3 | BUG-020: model_assignments.yaml phantoms → FIXED | 2026-07-21 |
| B4 | BUG-021: LaunchAgents recreating dir → FIXED | 2026-07-21 |
| B5 | BUG-022: Dropbox 5-folder variants → FIXED | 2026-07-21 |

---

*Consolidated from: DECISION-LOG.md (56 decisions), MTR (git recovery), 
ULTIMATE-CROSS-EXAMINATION-2026-07-21.md (534 lines),
ULTIMATE-CROSS-EXAMINATION-HANDOFF.md (695 lines), temp/asad.txt (462 lines),
buglog.md (325 lines), agent/session_seed.yaml (125 lines)*
*Rule: When task done → move to DONE section. Undone tasks stay on top.*
| C4 | pytest installed, 12/12 chunker tests pass | 2026-07-21 |
| C5 | BUG-015 fixed: datasketch raises ImportError (C16) | 2026-07-21 |
| C6 | C16-C20 adopted: CONSTITUTION, AGENTS, .ponytail.yaml | 2026-07-21 |