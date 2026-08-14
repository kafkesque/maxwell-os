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
- **S4-A (batch depth) remains VERIFIED**: 1.9x (8.4s -> 4.3s/FB) at identical 75% accuracy (D2354 A/B, in repo).

## Conclusion
- Only S4-A is safe to adopt now: ~25s -> ~21s/FB (~62h -> ~52h, ~17%).
- S4-B is refuted. The earlier "62h -> 40h" projection was WRONG (it assumed gemma worked).
- S4-C (distill gpt-oss -> 3-4B non-reasoning) is the only remaining path to a large speedup.
