# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-10 21:15 | **Session:** D2245-D2249 (model research, T-009, A-002/A-004, T-007 comparison)
> **Golden set:** v4.4 (73 examples, 50 FBs, 194 evidence passages — 100% verbatim)
> **Models:** Qwen3-Coder-30B (S2 gen) · Phi-4-mini-8bit (S4 cls) · **GPT-OSS-20B-MXFP4-Q8 (NEW, S4 depth — D2245)** · Gemma-4-31B-8bit (S5/R5 verifier)
> **S2 Comparison:** DSPy-MIPROv2 **0.672** vs Traditional **0.592** on 20 examples (D2248)

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

## 🔴 OPEN — CRITICAL (next execution order)

| # | Task | Priority | Effort | Notes |
|---|------|----------|--------|-------|
| **BUG-075** | **Cross-domain depth 0% across all models** | 🔴 P0 | 4h | Dominant class (26/50 = 52%). Root cause = long combined classify prompt. Fix: split depth into short focused call (proven 62.5%) + Reasoning:none + max_tokens≥1024 |
| **D2249** | **S4 classifier swap Phi→GPT-OSS** | 🔴 P0 | 2h | Blocked by BUG-075. Flip VERIFY_MODEL + prompt changes in stage4_merge.py (classify call: max_tokens 512→1024, Reasoning:none prefix). Frees ~19GB RAM |
| **BUG-053** | **Phi-4-mini hallucination on research** | 🔴 P0 | 1h | Resolution path: GPT-OSS replaces Phi for S4 depth (D2245); Phi retained only for S5 verify + fast gates |

---

## 🟠 OPEN — HIGH

| # | Task | Priority | Source |
|---|------|----------|--------|
| T-007b | S2 positive-fidelity gap: DSPy 0.60 vs Traditional 0.845 on both-scored positives. Options: max_labeled_demos 2→4, mechanism-weighted metric, hybrid DSPy-gate + Traditional-extract | 🟠 P1 | D2248 |
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
CRITICAL: ████░░░░░░ 3 OPEN (BUG-075, D2249, BUG-053)  ← S4 classifier chain
HIGH:     ██████████ 16 items (T1.x + T-007b + audit)
MEDIUM:   ██████████ 16 items (T2.x)
LOW:      ███░░░░░░░ 5 items
────────────────────────────────────
Session progress: P0 6/6 → 9/9 DONE tasks, 3 critical items identified with clear paths
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
