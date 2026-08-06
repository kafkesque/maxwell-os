# Maxwell OS — Aggregated Task Register (2026-08-06)
> **Source:** D2195-D2204 decisions + all 4 LLM evals (DeepSeek, ChatGPT, Qwen, Kimi)
> **Priority:** Recalibrated after golden set analysis

---

## 🏆 TOP PRIORITY — THE CRITICAL PATH (this week)

| # | Task | Why Critical | Effort | Blocked By |
|---|------|-------------|--------|-----------|
| **1** | **Run LLM evaluation on expanded golden set** (25 examples) | Golden set is `needs_review` — pipeline must NOT be calibrated on unverified ground truth. Use `config/golden/GOLDEN-EVALUATION-PROMPT.md` with 2+ LLMs. | 2h | — |
| **2** | **Calibrate golden set after eval** — fix flaws, set thresholds (NLI entailment, BORP min sources) | Calibration gate for Stage 2 quality | 4h | #1 |
| **3** | **Execute ONE business PI with existing FBs** | Existential test: can FBs produce a useful action? | 2h | — |
| **4** | **Yield crisis diagnostic** — manual extract 10 principles from 1 book, compare vs pipeline | 14 FBs from 852 books = 1.6% yield is a pipeline emergency (Kimi P0) | 1 day | #1 (need calibrated S2) |

---

## 🟠 P1 — HIGH (this sprint)

| # | Task | Effort | Source |
|---|------|--------|--------|
| 5 | Atomic evidence schema — per-passage NLI scores (not majority vote) | 2 days | ChatGPT C9 |
| 6 | Auto-fix 322 Ruff lint errors in pipeline/ (154 manual after) | 1h | D2201 |
| 7 | Monotonic trust state machine — DB-level transition constraints | 2 days | ChatGPT C7 |
| 8 | bge-m3 to MLX-native — investigate D2190 MPS deadlock root cause first | 1 day | Kimi K12 |
| 9 | Surface reliability scores in Zone 3 | 1 day | Kimi K3 |

---

## 🟡 P2 — MEDIUM (next sprint)

| # | Task | Effort | Source |
|---|------|--------|--------|
| 10 | MCP server exposing FBs (Layer 2 product start) | 3 days | Kimi K14 |
| 11 | Graph-aware retrieval (contradictions + prerequisites traversal) | 3 days | ChatGPT C10 |
| 12 | Context-conditioned reliability (domain-scoped scores) | 2 days | ChatGPT C11 |
| 13 | Pydantic AI harness for agent orchestration | 1 week | Kimi K14 |
| 14 | Agent execution safety boundary (Plan→Policy→Auth→Execute→Rollback) | 3 days | ChatGPT C14 |
| 15 | Modularize stage2_extract (1,480 lines) + stage4_merge (1,260 lines) | 3 days | Kimi K5 |
| 16 | Split config into active/archived/experiments (prevent config ghosts) | 1 day | ChatGPT C13 |
| 17 | Prompt lineage stamping (prompt_id, prompt_hash) | 1 day | ChatGPT C16 |
| 18 | Move taxonomy from hardcoded Literal to YAML-driven | 2 days | DeepSeek D5 |
| 19 | Add `just integrity` to CI (when CI exists) | 30m | ChatGPT C12 |

---

## ⚪ P3 — LOW (backlog)

| # | Task | Source |
|---|------|--------|
| 20 | Evaluate vLLM-mlx for concurrent multi-agent execution | Kimi |
| 21 | Consider LanceDB as unified vector+metadata store | Kimi |
| 22 | Collapse config authority to one canonical YAML per domain | ChatGPT C15 |
| 23 | Leiden clustering via python-igraph (defer — Louvain adequate) | Qwen Q5 |
| 24 | ONNX runtime for NLI (only if ModernBERT too heavy) | DeepSeek D4 |

---

## ✅ COMPLETED (D2195-D2204)

| # | Task | Decision |
|---|------|----------|
| ✅ | Zero-vector fallback → EmbeddingQuarantineError | D2196 |
| ✅ | LICENSE (MIT) | D2200 |
| ✅ | session_seed.yaml sync (NLI, stage3, 8-stage) | D2197 |
| ✅ | model_assignments.yaml sync (REVIEWER, S5_FB_VERIFIER, OptiQ) | D2199 |
| ✅ | stage6_commit INSERT 49→48 column fix | D2203 |
| ✅ | AGENTS.md + architecture docs stage3 purge | D2198 |
| ✅ | Ruff/mypy pipeline exclusion removed | D2201 |
| ✅ | ollama import removed → batch_embed delegation | D2202 |
| ✅ | just preflight exit bug fixed | D2203 |
| ✅ | integrity_check.py 17 checks (17/17 pass) | D2203 |
| ✅ | requirements.lock deterministic | D2203 |
| ✅ | .ponytail.yaml YAML escape fix | D2203 |
| ✅ | watchdog log + .DS_Store purged | D2203 |
| ✅ | Golden set 10→25 (full properties, 21 domains, 5 negatives) | D2204 |
| ✅ | Master LLM eval prompt v2.0 | D2204 |

---

## 🔥 REMAINING CRITICAL RISKS (after this round)

| Risk | Severity | Status |
|------|----------|--------|
| Golden set uncalibrated (25 examples need LLM review) | 🔴 HIGH | #1 priority |
| Yield crisis (14 FBs from 852 books) undiagnosed | 🔴 HIGH | #4 priority |
| Layer 2 orchestration = 0 lines (product missing) | 🔴 HIGH | P2 #10-14 |
| 476 Ruff errors in pipeline (was lint-blind for months) | 🟡 MED | P1 #6 |
| Anytype cloud-sync sovereignty leak | 🟡 MED | Deferred |
| BORP ≠ Truth (two books can agree on a myth) | 🟡 MED | Epistemic, deferred |

---

## D2205 — Golden-Eval Fix Pass (from 3-LLM cross-examination, pre-calibration gate)

Verdict on golden set v3.0: **NEEDS-FIXES** (positive corpus S-tier; negative block + metadata F-tier; 17 verified findings).

### P0 — blocks calibration
| # | Task | Source |
|---|------|--------|
| G-01 | NEG-001..004 → `route: NULL` + empty FB fields (NEG-CONV pattern) | Kimi/Qwen/DeepSeek consensus |
| G-02 | CONV-006 1:N schema: formalize `expected_fb: FB \| List[FB]` in schemas.py | Kimi (accurate framing) |
| G-03 | Replace fabricated CONV-003 source "Finding the Tipping Point" (verified real alt: McQuarrie & Mick 1999; Phillips & McQuarrie 2004); verify Mostafa | Qwen (only catcher) |
| G-04 | Meta header: `convergent_positives: 18`, `hard_negatives: 7`, fix notes | Kimi/Qwen |
| G-05 | Add NEG-005 jargon-echo + NEG-006 boundary-violation negatives | All three consensus |

### P1 — quality
| # | Task | Source |
|---|------|--------|
| G-06 | Repair 4 verbatim violations (CONV-003/012/013/017); add substring assertion to expand_golden_v2.py | This audit (CONV-013 found only here) |
| G-07 | Dedupe CONV-006 FB1 vs CONV-020 → keep canonical, replace CONV-020 with distinct BE principle (framing effects) | Kimi/Qwen |
| G-08 | CONV-012: replace one Russell source with independent AI-safety text | Qwen |
| G-09 | Property backfill into CONV-001..007 (depth/evidence/jargon/keywords) | Qwen/DeepSeek |
| G-10 | Domain rebalance: 2 business → AI/Visual/Interactive (also fixes ratio 20:8) | Kimi/Qwen |
| G-11 | Fix stray fields (consequence_2, source_book_2) + typos (opptimization, afntifragility); renumber/document ID gaps | Kimi/Qwen/DeepSeek |
| G-12 | Replace NEG-001 Graham + NEG-002 Duhigg segments with verified excerpts | Kimi/Qwen |

### P2 — process hardening
| # | Task | Source |
|---|------|--------|
| G-13 | GOLDEN-EVALUATION-PROMPT.md v2.1: mandate programmatic verbatim check + external source-existence check in Dimension 9 | This audit (gap: all 3 evals missed ≥1 violation) |
| G-14 | Author-overlap + secondary-source detector in golden validation (would've caught CONV-012/020) | Qwen/DeepSeek |
| G-15 | integrity_check.py check #18: route-vs-should_extract consistency | This audit |

### Evaluator meta-record (for future eval selection)
- Qwen: strongest overall (best fact-check; 3 false micro-claims)
- Kimi: strongest structure (missed positive-source fabrication)
- DeepSeek: most lenient (would've let contaminated set calibrate — hallucination PASS overruled)
- **Rule: never calibrate on single-evaluator verdict; tri-party eval = golden-set lifecycle (R5/BORP applied to the eval loop itself)**
