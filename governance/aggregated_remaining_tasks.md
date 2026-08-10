# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-10 23:45 | **Session:** D2250-D2251 (BUG-075 FIXED 87.5%, GPT-OSS live in S4, T-007b hybrid 0.736, golden audit)
> **Golden set:** v4.4 (73 examples, 75 FBs, 194 evidence passages — 100% verbatim, author cap ≤3)
> **Models:** Qwen3-Coder-30B (S2 gen) · **GPT-OSS-20B-MXFP4-Q8 (S4 classifier — D2249, 87.5% depth)** · Phi-4-mini-8bit (S5 verify + gates only) · Gemma-4-E4B (S5 cross-family)
> **S2 Comparison (D2251):** **Hybrid 0.736** > DSPy-MIPROv2 0.672 > Traditional 0.591 on 20 examples

---

## ✅ COMPLETED THIS SESSION (D2245-D2249)

| ID | Task | Result |
|----|------|--------|
| **D2245** | **Model research via llmfit** → GPT-OSS-20B-MXFP4-Q8 | 12.1GB, OpenAI MoE 3.6B active, registered in OMLX. **62.5% depth acc vs Gemma 50% / Phi 37.5%**; **24.9× faster than Gemma** (5.8s vs 143.8s/call) |
| **T-009** | Author cap ≤3 — Griffiths 5→3, Meadows 4→3 | ✅ Swap 3 books (D2234 precedent): CONV-007→Graham, CONV-042→Barabási, CONV-014→Watts. Evidence audit 194/194 verbatim, golden_validate PASS |
| **A-002** | Author-disjoint few-shot split | ✅ `_author_disjoint_fewshot()` in compare_s2_methods.py — verified 0 overlap |
| **A-004** | Expand test set 8→20 | ✅ train_frac 0.60 → 20 test examples; max_test param |
| **T-007** | DSPy harness + pilot rerun (post-A001) | ✅ **Best 96.4%** (was 44.75% pre-A001). Test eval 93.8%. Program persisted /tmp/dspy_mipro_optimized.json |
| **D2246** | 4-way S2 comparison (20-example) | ✅ **DSPy 0.672 vs Traditional 0.592** — DSPy: 5/5 negative rejection, 26.4s avg. Traditional: 0.845 positive-fidelity |
| **D2247** | S4 cross-domain A/B | ✅ Finding: `Reasoning: none` is the reliable GPT-OSS fix (60-182s → 25-40s). Few-shot anchors = weak signal |
| **D2243** | Kernel panic prevention | ✅ OMLX-only serving held (GPT-OSS loaded 12.1GB safely alongside Qwen+Phi+Gemma) |

---

## ✅ COMPLETED THIS SESSION (D2250-D2251)

| ID | Task | Result |
|----|------|--------|
| **BUG-075** | **Cross-domain depth 0% — FIXED** | ✅ **87.5% (7/8)**, cross-domain **3/3** (was 0/3 all models). Root cause CONFIRMED: long combined prompt. Fix: `classify_depth_focused()` short prompt (D2249). Benchmark: `governance/s4_depth_benchmark_focused_prompt.json` |
| **D2249** | **S4 classifier swap Phi→GPT-OSS** | ✅ VERIFY_MODEL → gpt-oss-20b-MXFP4-Q8. `Reasoning: none` prefix + max_tokens 1024 (config-driven, C12). Verified live. ~19GB RAM freed vs Gemma-31B |
| **BUG-053** | **Phi retired from S4** | ✅ Resolved for S4 (GPT-OSS replaces). Phi retained for S5 verify + fast gates |
| **T-007b** | **S2 positive-fidelity gap** | ✅ **Hybrid (DSPy gate + Trad extract) WINS: 0.736** vs DSPy 0.672 vs Trad 0.591 (D2251). Root cause: MIPROv2 2 demos design-only. Fix: demos 2→4 config + hybrid architecture |
| **T-009-followup** | **Author cap Christian 4→3** | ✅ CONV-012 Christian→The Age of AI (Kissinger/Schmidt/Huttenlocher). Evidence 194/194 verbatim, golden_validate PASS |
| **Audit** | **Golden pool + DSPy calibration** | ✅ Quality 0 gaps, 73/73 rationale, 194/194 evidence verbatim, metric weights sum 1.0. ⚠️ Depth class imbalance: universal=1, specialized=1 (4%) |

---

## 🔴 OPEN — CRITICAL (next execution order)

| # | Task | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| **T-007b v2** | Re-optimize MIPROv2 with demos 2→4 — close DSPy gate FN gap (CONV-036/043/040) | 🟠 P1 | 1h | D2250 config `s2.dspy_max_labeled_demos: 4`; re-run + hybrid A/B to verify gate FN fixed |
| **T1.1** | Full S1.3→S6 run — NEEDS RERUN (existing S2 checkpoint is old v2.3 schema, 0 overlap with current 12,964 clusters) | 🟠 P1 | ~100h runtime | Production job: `stage2_extract.py` resume-aware; schedule in batches |

---

## 🟠 OPEN — HIGH

| # | Task | Priority | Source |
|---|------|----------|--------|
| T-007b | ✅ RESOLVED via hybrid (D2251) — see completed table | — | D2248 |
| T1.1 | Run S1.3→S6 pipeline — first full run with bge-m3 512d | 🟠 P1 | MTR |
| T1.2 | Yield crisis diagnostic — 14 FBs from 852 books = 0.004% | 🟠 P1 | MTR |
| T1.3 | NLI calibration on real data (0.5/0.6/0.8 vs bge-m3) | 🟠 P1 | MTR |
| T1.4 | Fix faiss_threshold mismatch (0.75 vs 0.70) | 🟠 P1 | MTR |
| T1.5 | Fix AGENTS.md stage count (9-stage → canonical) | 🟠 P1 | MTR |
| T1.6 | Auto-fix Ruff lint (322 auto-fixable) | 🟠 P1 | MTR |
| T1.7 | LLM evaluation on golden set (25 ex, 2+ LLMs) | 🟠 P1 | MTR |
| T1.8 | Cross-encoder reranker gate (bge-reranker-v2-m3 ONNX) | 🟠 P1 | MTR |
| T1.9 | Source-independence graph (effective_source_count for BORP) | 🟠 P1 | MTR |
| Fix 0.1-0.4 | Tier-0 emergency fixes (null application, S4 forward, dead path, NLI MAX-entail) | 🟠 P1 | MTR D2213-18 |
| N2/N3/N6 | mechanism/boundary in Pydantic FB, actionability field, ModernBERT NLI | 🟠 P1 | MTR audit |

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
CRITICAL: ░░░░░░░░░░ 0 OPEN — S4 chain FIXED (BUG-075 87.5%, D2249 done, BUG-053 retired for S4)
HIGH:     ██████████ T-007b v2 (gate FN) + T1.1 (full run ~100h) + T1.2-T1.9
MEDIUM:   ██████████ 16 items (T2.x)
LOW:      ███░░░░░░░ 5 items
────────────────────────────────────
Session progress: D2250-D2251 — 6 tasks DONE (BUG-075, D2249, BUG-053, T-007b, T-009-fup, audit)
```

## 🔗 NEXT EXECUTION ORDER

```
1. T-007b v2  → Wait for MIPROv2 re-opt (demos 4) → hybrid A/B verify gate FN closed
2. T1.1       → Full S1.3→S6 run (100h, schedule in batches — S2 resume-aware)
3. T1.2       → Yield crisis diagnostic (14 FBs / 852 books = 0.004%)
4. T1.3       → NLI calibration on real data
5. T1.4       → faiss_threshold mismatch (0.75 vs 0.70)
```

## 🔗 NEXT EXECUTION ORDER

```
1. BUG-075  → Split S4 depth into short focused prompt (Reasoning:none, max_tokens 1024)
2. D2249    → Flip VERIFY_MODEL to gpt-oss-20b-MXFP4-Q8 + prompt changes
3. BUG-053  → Confirm Phi retired from S4; keep for S5 verify
4. T-007b   → Close positive-fidelity gap (more demos / metric reweight / hybrid)
5. T1.1     → First full S1.3→S6 pipeline run (with GPT-OSS in S4)
6. T1.2     → Yield crisis diagnostic
```
