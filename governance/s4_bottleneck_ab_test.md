# S4 Depth Bottleneck — A/B Test (D2354)

> Generated: 2026-08-14 14:12:02 · Model: `gpt-oss-20b-MXFP4-Q8` · max_tokens=1024 · batch_size=4 · seed=42

## Summary

| Path | Strategy | Total | Avg/FB | Accuracy vs golden | Fail-closed events |
|---|---|---|---|---|---|
| **A — existing** | sequential `classify_depth_focused()` | 67.4s | 8.4s | 75.0% | 0 |
| **B — proposed** | `batch_depth_classify()` (batch=4) | 34.8s | 4.3s | 75.0% | 0 |

- **A↔B parity:** 75.0%
- **Speedup:** 1.9×
- **Gate (≥90% parity + 0 silent failures):** ❌ FAIL

## Per-FB

| Golden | Depth | A (existing) | A time | B (proposed) | B time | Agree |
|---|---|---|---|---|---|---|
| CONV-023 | universal | universal | 5.53s | universal | 4.35s | ✅ |
| CONV-053 | domain | cross-domain | 9.27s | domain | 4.35s | ❌ |
| CONV-021 | cross-domain | cross-domain | 6.11s | cross-domain | 4.35s | ✅ |
| CONV-049 | cross-domain | cross-domain | 7.64s | domain | 4.35s | ❌ |
| CONV-040 | specialized | specialized | 4.51s | specialized | 4.35s | ✅ |
| CONV-012 | domain | domain | 18.76s | domain | 4.35s | ✅ |
| CONV-026 | cross-domain | cross-domain | 5.71s | cross-domain | 4.35s | ✅ |
| CONV-001 | domain | cross-domain | 9.86s | cross-domain | 4.35s | ✅ |

## Fail-closed events (surfaced by M1, not swallowed into `domain`)

_None — both paths returned a valid depth label for every FB._

## Verdict

Path B does **not** yet meet the gate. Do not adopt until parity ≥ 90% and zero silent failures are reproduced. Investigate the per-FB mismatches above.
