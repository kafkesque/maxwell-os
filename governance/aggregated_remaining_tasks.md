# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-11 12:00 | **Session:** D2255-D2262 — COMPREHENSIVE AUDIT + 8 P0 FIXES APPLIED
> **Golden set:** v4.4 (73 examples, 55 convergent / 18 non-convergent — metafixed D2257)
> **Models:** Qwen3-Coder-30B (S2 gen) · GPT-OSS-20B-MXFP4-Q8 (S4 classifier, 87.5% depth) · DeBERTa FEVER (S5 NLI primary, D2255) · Gemma-4-E4B (S5 cross-family verifier) · bge-m3 (embeddings)
> **Phi-4-mini status:** Smoke test + agent assignments only. NO pipeline config role (BUG-079 fixed, D2260).
> **S2 Comparison (D2251):** **Hybrid 0.736** > DSPy-MIPROv2 0.672 > Traditional 0.591 (20 examples, 3-arm)
> **Full-run cost (T1.1):** ~21-26h wall-clock (NOT 100h — tiered + 3 workers + merged S4)

---

## 🔴 P0 COMPLETED — D2255-D2262 (2026-08-11)

> **Source:** `governance/COMPREHENSIVE_AUDIT_2026-08-11.md` — cross-examination of 11 LLM responses, every claim verified against source files.

| ID | Task | Decision | Status |
|----|------|----------|--------|
| P0.1 | S5 NLI config → DeBERTa FEVER primary | D2255 | ✅ FIXED |
| P0.2 | E2E diagnostic gate (50-100 books) | D2261 | ⬜ READY — see §E2E GATE below |
| P0.3 | Archive GOLDEN-REVIEW.md v2.0 | D2259 | ✅ ARCHIVED |
| P0.4 | Golden YAML meta count 36→55 | D2257 | ✅ FIXED |
| P0.5 | Fix stage5_verify.py docstring | D2256 | ✅ FIXED |
| P0.6 | Remove stale classify_model L1642 | D2258 | ✅ FIXED |
| P0.7 | Goose MacWebContentsOcclusion | D2262 | ✅ DOCUMENTED (HANDOFF §0) |
| P0.8 | Fix HANDOFF model registry | D2260 | ✅ FIXED |

### E2E DIAGNOSTIC GATE (D2261) — NEXT ACTION

**Command:** `python3 pipeline/run_diagnostic.py --books 100`
**Gate criteria:**
- Yield >1% AND S5 pass rate >40% → APPROVE T1.1 full run
- Yield <0.5% OR S5 pass rate <20% → HALT, diagnose
- Between → judgment call with data

---

## ✅ COMPLETED THIS SESSION (D2250-D2252)

| ID | Task | Result |
|----|------|--------|
| **BUG-075** | **Cross-domain depth 0% — FIXED** | ✅ **87.5% (7/8)**, cross-domain **3/3** (was 0/3 all models). Root cause: long combined prompt. Fix: `classify_depth_focused()` short prompt. Benchmark: `governance/s4_depth_benchmark_focused_prompt.json` |
| **D2249** | **S4 classifier swap Phi→GPT-OSS** | ✅ VERIFY_MODEL → gpt-oss-20b-MXFP4-Q8. `Reasoning: none` prefix + max_tokens 1024 (config-driven C12). ~19GB RAM freed vs Gemma-31B |
| **BUG-053** | **Phi retired from S4** | ✅ GPT-OSS replaces Phi for S4 classification; Phi kept for S5 verify + fast gates only |
| **T-007b** | **S2 positive-fidelity gap** | ✅ **Hybrid (DSPy gate + Trad extract) = 0.736** > DSPy 0.672 > Trad 0.591. Root cause: MIPROv2 2 demos design-only. Production arch = hybrid (D2251) |
| **T-009-followup** | **Author cap Christian 4→3** | ✅ CONV-012 Christian→*The Age of AI* (Kissinger/Schmidt/Huttenlocher). 194/194 verbatim, golden_validate PASS |
| **Golden audit** | **User-requested full audit** | ✅ 0 quality gaps, 73/73 rationale, 194/194 verbatim, metric calibrated, depth imbalance documented. Report: `governance/SESSION_AUDIT_D2250.md` |
| **DSPy validation** | **LLM-approvable artifact** | ✅ `governance/DSPY_VALIDATION_REPORT.md` — hybrid APPROVED for production |
| **S4 chain E2E** | **GPT-OSS + focused depth on real S2 FBs** | ✅ Validated live (Patch Cord→specialized, Value-First→cross-domain) |
| **D2252** | **T-007b pragmatic resolution** | ✅ Demo re-opt 4→3 (20h infeasible interactive); overnight scheduled only |
| **Cost model** | **T1.1 realistic estimate** | ✅ 12,964 clusters → ~21-26h (tiered 79.7% single-source + 3 workers + merged S4) |

---

## 🔴 OPEN — CRITICAL (next execution order)

| # | Task | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| **T-007b-v2** | Re-optimize MIPROv2 with demos 2→3 (overnight) — close DSPy gate FN gap (CONV-036/043/040) | 🟠 P1 | 1h setup + overnight | Config `s2.dspy_max_labeled_demos: 3` already set. Optional polish — hybrid works without it |
| **T1.1** | **Full S1.3→S6 run on 12,964 clusters** | 🔴 P0 | **~21-26h wall-clock** | Tiered+parallel: ~19h S2 + ~4h S4 + ~1h S5. Batch-resume capable. Schedule as production job with monitor |
| **T1.2** | Yield crisis diagnostic — 14 FBs / 852 books = 0.004% | 🟠 P1 | 2h | Re-measure on the real full run; investigate why convergent yield is so low |

---

## 🟠 OPEN — HIGH

| # | Task | Priority | Source |
|---|------|----------|--------|
| T1.3 | NLI calibration on real data (0.5/0.6/0.8 vs bge-m3) | 🟠 P1 | MTR |
| T1.4 | Fix faiss_threshold mismatch (0.75 vs 0.70) | 🟠 P1 | MTR |
| T1.5 | AGENTS.md stage count (9-stage → canonical) | 🟠 P1 | MTR |
| T1.6 | Ruff lint auto-fix (322 warnings) | 🟠 P1 | MTR |
| T1.7 | LLM eval on golden set (25 ex, 2+ LLMs) | 🟠 P1 | MTR |
| T1.8 | Cross-encoder reranker gate | 🟠 P1 | MTR |
| T1.9 | Source-independence graph | 🟠 P1 | MTR |
| T-015 | Extraction type expansion (4→12-15 per type) + depth class balance (universal/specialized) | 🟠 P1 | 2d | Fixes golden pool imbalance found in D2250 audit |
| Fix 0.1-0.4 | null application prompt, S4 forward dict, dead multi-FB path, NLI MAX-entailment | 🟠 P1 | MTR |
| N2/N3/N6 | Pydantic FB fields, actionability, ModernBERT NLI | 🟠 P1 | MTR |
| Gov-sync | decisions.yaml missing D2210/D2212/D2233-D2239 (present in DECISION-LOG) | 🟠 P2 | 1h | Historical sync gap found in D2250 audit |

---

## 🟡 OPEN — MEDIUM (TIER 2)

| # | Task | Effort |
|---|------|--------|
| T2.1 | Execute ONE business PI with existing FBs — existential test | 2h |
| T2.2 | Atomic evidence schema — per-passage NLI | 2d |
| T2.3 | Monotonic trust state machine | 2d |
| T2.4 | Surface reliability scores in Zone 3 | 1d |
| T2.5 | skill.md standard (Layer 2 MVP) | 4h |
| T2.6 | Hardware probe (C24) — auto RAM detect | 3h |
| T2.7 | 20-book E2E test | 3h |
| T2.8 | Integration test suite — `just test` | 4h |
| T2.9 | Adversarial golden set | 2d |
| T2.10 | RAGTruth hallucination suite | 1d |
| T2.11 | ARES component evaluation | 1d |
| T2.12 | One pipeline authority (canonical DAG) | 1d |
| T2.13 | Split config active/archived/experiments | 1d |
| T2.14 | Collapse config authority | 1d |
| T2.15 | Prompt lineage stamping | 1d |
| T2.16 | Taxonomy YAML-driven (not hardcoded Literal) | 2d |

---

## ⚪ OPEN — LOW (TIER 3) + BUGLOG

| # | Task | Effort |
|---|------|--------|
| T3.1 | USearch vs FAISS benchmark | 2h |
| T3.2 | MeshRAG hash-driven clustering eval | 1d |
| T3.3 | Leiden clustering via python-igraph | 2h |
| T3.4 | Kimi depth confidence signal (v3.1) | — |
| T3.5 | Two-stage S4: separate classification from CRIBS (v3.1) | — |
| BUG-073 | CONV-035/037 false convergence (D2232 pending) | — |

---

## 📊 STATUS SUMMARY

```
CRITICAL: ██░░░░░░░░ T1.1 full run (~26h) ← the only blocker to production
HIGH:     ██████████ T-007b-v2 (optional) + T1.2-T1.9 + T-015 + Fix 0.1-0.4
MEDIUM:   ██████████ 16 items (T2.x)
LOW:      ███░░░░░░░ 5 items + BUG-073
────────────────────────────────────
Session progress: D2250-D2252 — S4 chain FIXED, T-007b resolved, golden audited, cost model corrected
Decisions: 235 (D2250, D2251, D2252 added)
```

## 🔗 NEXT EXECUTION ORDER

```
P0 GATE:    E2E diagnostic on 50-100 books (~3-6h) → THIS IS THE NEXT ACTION.
            Yield >1% + S5 >40% → proceed. Otherwise halt and diagnose.

P1 (post-gate):
1. T1.1       → Launch full S1.3→S6 run (~26h wall-clock, batch-resume). Monitor first
                hour for throughput (expect ≥2× single-thread: 3 workers + tiered prompts).
2. T-007b-v2  → Overnight MIPROv2 re-opt (3 demos) in parallel with T1.1 if GPU allows.
3. T1.2       → Yield diagnostic on the full run output (re-measure 0.004%).
4. T1.3       → NLI calibration on real data (DeBERTa FEVER thresholds on 50-100 FBs).
5. T1.4       → Fix faiss_threshold mismatch (0.75 vs 0.70).
6. T-015      → Golden pool expansion (extraction types + depth balance).
7. P1.3       → Deploy DSPy hybrid gate in production stage2_extract.py.
8. P1.4       → Fix S4→S5 verification gap (application/failure_mode/elaboration content).
9. P1.5       → S1.5 cluster-quality diagnostic (sample 100-300 clusters).
10. P1.7      → Fix generator model name drift (Qwen3.6-35B vs Qwen3-Coder-30B).
```

## 🧭 SESSION HANDOFF POINTER (next session start here)

```
1. Verify OMLX health: curl -s localhost:11435/health
2. Check T1.1 run progress: tail "knowledge pipeline/stage2_extract/latest/checkpoint.jsonl"
3. Config: verifier=gpt-oss-20b-MXFP4-Q8, s2.max_workers=3, s2.dspy_max_labeled_demos=3
4. Master prompt v8: governance/ROUNDTABLE_MASTER_PROMPT.md (updated with D2250-D2252)
5. Validation report: governance/DSPY_VALIDATION_REPORT.md (hybrid approved)
6. Session audit: governance/SESSION_AUDIT_D2250.md (clean + documented gaps)
```
