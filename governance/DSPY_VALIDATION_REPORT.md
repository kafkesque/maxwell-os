# DSPy S2 Optimizer — Validation Report (D2250-D2252)
> **Purpose:** Independent LLM validation of the DSPy-optimized S2 extractor before full-pipeline approval.
> **Status:** ✅ HYBRID APPROVED FOR PRODUCTION — see verdict below.

## 1. What was validated (20-example 3-arm A/B, Qwen3-Coder temp 0.0)

| Metric | Traditional | DSPy-MIPROv2 | Hybrid (D2251) |
|--------|-------------|--------------|----------------|
| Avg Quality | 0.591 | 0.672 | **0.736** |
| Avg Latency | 29.7s | 27.0s | 45.8s |
| Negatives rejected (n=6) | 0/6 | 5/6 | 5/6 |
| Positive-fidelity (n=14) | 0.845 | 0.602 | 0.845 |

## 2. DSPy calibration audit
- **Metric weights sum to 1.00**: convergence .30, type .20, name .12, mechanism .13,
  evidence .10, boundary .05, consequence .05, route .05 (A-001 removed depth weight).
- **Verified**: perfect positive = 1.0, perfect negative = 1.0, FP capped ≤0.20, FN = 0.10.
- **Reproducibility**: Traditional 0.591/0.592, DSPy 0.672 identical across two runs.

## 3. LLM handoff audit (DSPy demos vs Claude/Kimi curated pool)
- **Finding**: MIPROv2 (2 demos) selected DESIGN-ONLY books (Cooper/Krug/Norman) while
  the golden pool spans 38 domains. The hand-curated pool WINS positive fidelity
  (0.845 vs 0.602); DSPy adds the negative gate (5/6 rejects, its proven strength).
- **Verdict**: Neither alone is sufficient → hybrid architecture is production.

## 4. Golden pool requirements audit
- **Quality**: 0 field gaps (name/definition/mechanism/boundary/consequence ≥ min len)
- **Accuracy**: 73/73 rationale present; **194/194 evidence passages verbatim** (T-003)
- **Author cap**: ≤3 per author by FB-mention (T-009 + D2250 Christian 4→3 fix)
- **Leakage**: author-disjoint few-shot (A-002) — 0 test-author overlap in few-shot pool
- **Known imbalance**: universal=1, specialized=1 (4%) — under-represented, tracked T-015

## 5. S4 depth classifier (D2249/D2250)
- GPT-OSS-20B-MXFP4-Q8 + SHORT focused prompt: **87.5% (7/8)**, cross-domain **3/3**
  (was 0/3 for all models). Benchmark: `governance/s4_depth_benchmark_focused_prompt.json`

## 6. Remaining gaps for FULL-RUN approval
| # | Gap | Status |
|---|-----|--------|
| 1 | DSPy gate false-negatives (CONV-036/043/040) | T-007b-v2: overnight re-opt (3 demos) |
| 2 | Full S1.3→S6 run on 12,964 clusters (~100h) | T1.1: scheduled batch production job |
| 3 | Depth class imbalance (universal/specialized) | T-015 expansion |
| 4 | NLI calibration on real data | T1.3 |

## 7. Verdict
**APPROVE hybrid S2 for production** (DSPy gate + Traditional extraction, 0.736 avg,
5/6 negative rejection, 0.845 positive fidelity). DSPy standalone approved for
convergence-routing only. Full-pipeline approval gated on T1.1 (full run) + T-007b-v2.
