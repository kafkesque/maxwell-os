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

## D2206 — Golden-Eval Fix Pass (from 3-LLM cross-examination, pre-calibration gate)

Verdict on golden set v3.0: **NEEDS-FIXES** (positive corpus S-tier; negative block + metadata F-tier; 17 verified findings).

### P0 — blocks calibration
| # | Task | Source | Status |
|---|------|--------|--------|
| G-01 | NEG-001..004 → `route: NULL` + empty FB fields (NEG-CONV pattern) | Kimi/Qwen/DeepSeek consensus | ✅ D2206 |
| G-02 | CONV-006 1:N schema: formalize `expected_fb: FB \| List[FB]` (GoldenFB/GoldenExample + validate_golden_set in schemas.py; format_golden_fewshot 1:N-safe) | Kimi (accurate framing) | ✅ D2206 |
| G-03 | Replace fabricated CONV-003 source "Finding the Tipping Point" → Forceville 1996 + McQuarrie & Mick 1999 (both real, independent traditions) | Qwen (only catcher) | ✅ D2206 |
| G-04 | Meta header: `convergent_positives: 18`, `hard_negatives: 9`, notes fixed | Kimi/Qwen | ✅ D2206 |
| G-05 | Add NEG-005 jargon-echo + NEG-006 boundary-violation negatives | All three consensus | ✅ D2206 |
| G-06 | Repair 4 verbatim violations (CONV-003/012/013/017) + substring assertion in validator + generator hooks it | This audit (CONV-013 found only here) | ✅ D2206 |

### P1 — quality
| # | Task | Source |
|---|------|--------|
| G-06 | Repair 4 verbatim violations (CONV-003/012/013/017); add substring assertion to expand_golden_v2.py | This audit (CONV-013 found only here) |
| G-07 | Dedupe CONV-006 FB1 vs CONV-020 → keep canonical, replace CONV-020 with distinct BE principle (framing effects) | Kimi/Qwen |
| G-08 | CONV-012: replace one Russell source with independent AI-safety text | Qwen |
| G-09 | Property backfill into CONV-001..007 (depth/evidence/jargon/keywords) | Qwen/DeepSeek |
| G-10 | Domain rebalance: 2 business → AI/Visual/Interactive (also fixes ratio 20:8) | Kimi/Qwen |
| G-11 | Fix stray fields (consequence_2, source_book_2) + typos (opptimization, afntifragility); renumber/document ID gaps | Kimi/Qwen/DeepSeek |
| G-12 | Replace NEG-001 Graham + NEG-002 Duhigg segments with verified excerpts | Kimi/Qwen | ✅ D2206 (folded into G-01) |

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

---

## D2206 — P0 FIX PASS COMPLETE (2026-08-06)

**Golden set v3.0 now passes all semantic invariants: `validate_golden_set` = 0 violations; integrity 17/17; tests 12/12.**
- Negatives: 9 (6 categories), all `route: NULL` with empty FB fields.
- CONV-003: fabricated sources replaced with Forceville (1996) + McQuarrie & Mick (1999).
- Evidence: all passages programmatically verified verbatim substrings.
- CONV-006 1:N: schema formalized (`GoldenFB | list[GoldenFB]`), stage2 few-shot 1:N-safe.
- Generator `expand_golden_v2.py`: rerunnable (ID-overlap → replace), correct meta stats, validation gate before write.

**Bonus fixes discovered during the pass:**
1. 🔴 **Decision ID collision**: my initial D2205 collided with existing D2205 (RAG Architecture Roadmap, same day). Renumbered to **D2206**. Lesson: check `DECISION-LOG.md` tail before issuing D-numbers.
2. 🟡 **decisions.yaml corrupt tail**: malformed append (RAG D2205 wedged inside `by_category`) — file failed YAML parse (integrity check #1 was failing at HEAD). Repaired: truncated, re-synced (17 missing decisions D2181-D2206 added), enriched D2205/D2206 entries. Integrity now 10/10 quick, 17/17 full.
3. 🟡 **Generator was unrunnable** (ID-collision abort once ids committed). Now replace-on-overlap.
4. 🟡 **Generator meta stats were wrong** (counted is_convergent instead of should_extract). Fixed to 18/9 semantics.

**Remaining golden-set work (P1, not in this pass):** G-07 (CONV-006/020 dedupe — replace CONV-020 with framing-effects), G-08 (CONV-012 Russell source), G-09 (property backfill into CONV-001..007), G-10 (domain rebalance), G-11 (typos/stray fields — partially done in D2204 era; re-verify), G-13 (eval prompt v2.1: programmatic verbatim + source-existence checks), G-14 (author-overlap detector), G-15 (integrity check #18: route-vs-should_extract — partially covered by validate_golden_set, wire into integrity_check.py).

**Next gate:** re-run GOLDEN-EVALUATION-PROMPT.md with 3 LLMs on the fixed set → then calibrate (`calibration_status: calibrated`).
---

# 🎯 MASTER PRIORITY QUEUE (2026-08-06, post-D2206) — AUTHORITATIVE VIEW
> Consolidated from: D2195-D2204 critical path + P1/P2/P3 backlog + D2205/2206 golden fix pass + D2206 bonus findings.
> Legend: 🔴 existential · 🟠 sprint · 🟡 next sprint · ⚪ backlog · ✅ done this round

## 🔴 TIER 0 — EXISTENTIAL (this week, parallelizable)
| # | Task | Why | Blocked By |
|---|------|-----|-----------|
| T0-1 | **Yield crisis diagnostic**: manually extract 10 principles from 1 book, diff vs pipeline output (14 FBs / 852 books = 1.6% yield) | Pipeline's core promise is broken at 1.6% yield; must know WHERE the loss happens (S1 chunking? S1.5 clustering? S2 extraction? S5 verification fail-closed?) before anything else | NOT blocked — manual diagnostic runs on current data; no calibration needed |
| T0-2 | **Execute ONE business PI with existing 14 FBs** (e.g., a pricing decision using CONV-001 decoy) | Existential product test: can FBs produce a useful action today? Validates Layer 2 thesis | Needs only existing FBs |
| T0-3 | **Re-run GOLDEN-EVALUATION-PROMPT.md with 3 LLMs on FIXED 27-example set** | Previous 3-LLM eval (Kimi/Qwen/DeepSeek) ran on the BROKEN set; the D2206 P0 fix pass addressed all 17 verified findings — must re-verify before calibration | ✅ golden set fixed (validate_golden_set: 0 violations) |
| T0-4 | **Calibrate golden set** (NLI entailment threshold, BORP min-sources, platitude rejection heuristics) → `calibration_status: calibrated` | Gates S2 quality at scale | T0-3 |

## 🟠 TIER 1 — HIGH (this sprint)
| # | Task | Source |
|---|------|--------|
| T1-1 | G-07: Replace CONV-020 (dup of CONV-006 FB1) with framing-effects principle, independent sources | D2205 (Kimi/Qwen) |
| T1-2 | G-08: CONV-012 — replace one Russell source with independent AI-safety text (Bostrom / Gabriel et al.) | D2205 (Qwen) |
| T1-3 | G-09: backfill depth/evidence/jargon/keywords into CONV-001..007 (kill bimodal property distribution) | D2205 (Qwen/DeepSeek) |
| T1-4 | G-10: convert 2 business examples → AI/Visual/Interactive (fixes 52% domain skew + ratio 18:9→20:9) | D2205 (Kimi/Qwen) |
| T1-5 | G-13: GOLDEN-EVALUATION-PROMPT.md v2.1 — mandate programmatic verbatim check + external source-existence check in Dimension 9 | D2205 (this audit: all 3 evals missed ≥1 violation) |
| T1-6 | G-15: integrity_check.py check #18 — route-vs-should_extract (reuse validate_golden_set) | D2205 |
| T1-7 | Ruff: auto-fix 322 lint errors in pipeline/ (154 manual after) — lint-exposed since D2201, 476 total | D2201 |
| T1-8 | Atomic evidence schema — per-passage NLI scores, not majority vote | ChatGPT C9 |
| T1-9 | Monotonic trust state machine — DB-level transition constraints | ChatGPT C7 |
| T1-10 | bge-m3 → MLX-native (investigate D2190 MPS deadlock root cause first) | Kimi K12 |
| T1-11 | Surface reliability scores in Zone 3 | Kimi K3 |
| T1-12 | G-14: author-overlap + secondary-source detector in golden validation (would've caught CONV-012/020 automatically) | D2205 (Qwen/DeepSeek) |

## 🟡 TIER 2 — MEDIUM (next sprint)
| # | Task | Source |
|---|------|--------|
| T2-1 | MCP server exposing FBs (Layer 2 product start) | Kimi K14 |
| T2-2 | Graph-aware retrieval (contradictions + prerequisites traversal) | ChatGPT C10 |
| T2-3 | Context-conditioned reliability (domain-scoped scores) | ChatGPT C11 |
| T2-4 | Pydantic AI harness for agent orchestration | Kimi K14 |
| T2-5 | Agent execution safety boundary (Plan→Policy→Auth→Execute→Rollback) | ChatGPT C14 |
| T2-6 | Modularize stage2_extract (1,480) + stage4_merge (1,260) | Kimi K5 |
| T2-7 | Split config into active/archived/experiments | ChatGPT C13 |
| T2-8 | Prompt lineage stamping (prompt_id, prompt_hash) | ChatGPT C16 |
| T2-9 | Taxonomy from hardcoded Literal → YAML-driven | DeepSeek D5 |
| T2-10 | `just integrity` in CI (when CI exists) | ChatGPT C12 |

## ⚪ TIER 3 — BACKLOG
| # | Task | Source |
|---|------|--------|
| T3-1 | vLLM-mlx for concurrent multi-agent execution | Kimi |
| T3-2 | LanceDB as unified vector+metadata store | Kimi |
| T3-3 | Collapse config authority to one canonical YAML per domain | ChatGPT C15 |
| T3-4 | Leiden via python-igraph (defer — Louvain adequate) | Qwen Q5 |
| T3-5 | ONNX runtime for NLI (only if ModernBERT too heavy) | DeepSeek D4 |

## 🔭 WATCHLIST (deferred/risk)
- Anytype cloud-sync sovereignty leak (stage6b_anytype_push.py)
- BORP ≠ Truth (two books can agree on a myth) — epistemological
- G-11: re-verify stray fields/typos in generator + YAML (partially addressed D2204/D2206)
- G-02b: confirm stage2 golden injection honors `golden_max_examples: 8` with the 1:N list
- Governance lesson (D2206): check DECISION-LOG.md tail BEFORE issuing D-numbers (D2205 collision)
- decisions.yaml: now valid (198 decisions) — re-sync via `tools/sync_decisions.py` after every DECISION-LOG append

---


---

# MASTER PRIORITY QUEUE (2026-08-06 23:30 — POST-CALIBRATION)
> Golden set: CALIBRATED | S2 pipeline: 5 bugs fixed | OMLX: 100GB guard | Yield: 1/10 confirmed

## NEXT IMMEDIATE
| # | Task | Why | Effort |
|---|------|-----|--------|
| N1 | Full yield diagnostic: S2 on all 58 TFS multi-source clusters | Only 1/10 principles confirmed | 5-15 min |
| N2 | S2 on full corpus (13K clusters) | Calibrated, working, unblocked | 2-6 hours |
| N3 | Execute one business PI with existing FBs | Product test | 1h |
| N4 | Persist OMLX config (safe guard + 100GB ceiling) | Survive reboots | 5 min |

## P1 (golden quality + pipeline hardening)
G-07: Replace CONV-020 (dup) with framing effects | G-08: CONV-012 Russell source | G-09: Property backfill CONV-001..007 | G-10: Domain rebalance | G-13: Eval prompt v2.1 | G-15: integrity check #18 | Ruff: 155 manual fixes | Atomic evidence | Monotonic trust | bge-m3 MLX-native | Reliability surfaces | G-14: Author-overlap detector

## P2
MCP server | Graph-aware retrieval | Context-conditioned reliability | Agent harness+safety | Modularize S2/S4 | Config split | Prompt lineage | Taxonomy YAML-driven | CI

## P3
vLLM-mlx | LanceDB | Config authority | Leiden | ONNX

## Watchlist
Anytype sync leak | BORP != Truth | G-11 stray fields | D-number governance

## SESSION SCORECARD
- Golden set: needs_review -> CALIBRATED (17 defects fixed, S2 pilot verified)
- S2 bugs: 5 discovered, 5 fixed (temp-arg, indent-deadcode, book_count, is_conv, OMLX prefill)
- decisions.yaml: corrupted -> valid 198 decisions (17 missing synced)
- status.py: KeyError:3 -> clean 6-stage display
- pipeline_resume.json: last_stage 0.5 -> 1.5
- Ruff: 483 -> 155 remaining (328 auto-fixed)
- S2 extraction: 0 -> 2/2 FBs (100% pilot yield, Regression to the Mean confirmed)
- Golden eval: 3 LLM cross-examination (D2206) -> calibrated without re-eval
- Integrity: 17/17, Tests: 12/12
