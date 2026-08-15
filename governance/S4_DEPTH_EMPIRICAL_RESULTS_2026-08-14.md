# S4 Depth — Empirical Validation Results (2026-08-14 18:12)

> Ran `tools/benchmark_s4_depth_frugal.py` (production path, D2354 FrugalGPT gate).
> Raw data: `governance/s4_depth_frugal_benchmark.json`

## Verdict: S4-B (FrugalGPT gemma depth) is REFUTED

| Metric | GPT-OSS (baseline) | gemma-4-E4B (frugal) | Gate |
|---|---|---|---|
| Accuracy (n=8, stratified, seed=42) | 75.0% | **62.5%** | >=90% ❌ |
| Parity (agree with GPT-OSS) | — | 62.5% | >=90% ❌ |
| Fail-open / silent failures | 0 | 0 | 0 ✅ |
| Avg time warm | 10.0s | ~3.3s (11.2s incl. 65.6s cold-load) | — |

- **gemma-4-E4B is NOT accurate enough for depth** (62.5% vs gpt-oss 75%). Do NOT enable `depth_frugal_enabled`.
- **gpt-oss itself is only 75% on depth** — below the 87.5% claimed in D2249/S4_BOTTLENECK_ANALYSIS. Depth accuracy is a separate, unsolved problem (the 87.5% was a governance claim that drifted from the actual benchmark).
- **S4-A (batch depth) is 1.9× faster at identical 75% accuracy, but FAILS the ≥90% parity gate**
  (parity 75.0%, `gate_pass: false` in `s4_bottleneck_ab_test.json`) → **NOT adopted / unwired** per D2354.
  The speedup is real; the per-FB disagreement (CONV-053, CONV-049) is what blocks adoption.

## Conclusion
- **Neither S4-A (batch depth) nor S4-B (gemma frugal) is adoptable now.** S4-A is fast but fails
  the 90% parity gate (75%); S4-B fails the 90% accuracy gate (62.5%). D2354: both unwired.
- S4-B is refuted. The earlier "62h -> 40h" projection was WRONG (it assumed gemma worked).
- S4-C (distill gpt-oss -> 3-4B non-reasoning) is the only remaining path to a large speedup.
