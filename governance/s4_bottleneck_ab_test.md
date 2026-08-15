# S4 Depth Bottleneck — A/B Test (D2354)

> Generated: 2026-08-15 16:10:28 · Model: `gpt-oss-20b-MXFP4-Q8` · max_tokens=1024 · batch_size=4 · seed=42

## Summary

| Path | Strategy | Total | Avg/FB | Accuracy vs golden | Fail-closed events |
|---|---|---|---|---|---|
| **A — existing** | sequential `classify_depth_focused()` | 308.0s | 6.8s | 84.4% | 0 |
| **B — proposed** | `batch_depth_classify()` (batch=4) | 180.9s | 4.0s | 66.7% | 0 |

- **A↔B parity:** 60.0%
- **Speedup:** 1.7×
- **Gate (≥90% parity + 0 silent failures):** ❌ FAIL

## Per-FB

| Golden | Depth | A (existing) | A time | B (proposed) | B time | Agree |
|---|---|---|---|---|---|---|
| CONV-011 | cross-domain | cross-domain | 8.52s | domain | 4.02s | ❌ |
| CONV-040 | specialized | specialized | 4.46s | specialized | 4.02s | ✅ |
| CONV-039 | domain | cross-domain | 6.17s | domain | 4.02s | ❌ |
| CONV-045 | cross-domain | domain | 9.26s | domain | 4.02s | ✅ |
| CONV-031 | cross-domain | cross-domain | 7.72s | domain | 4.02s | ❌ |
| CONV-014 | cross-domain | cross-domain | 8.25s | cross-domain | 4.02s | ✅ |
| CONV-048 | cross-domain | cross-domain | 6.11s | cross-domain | 4.02s | ✅ |
| CONV-034 | cross-domain | cross-domain | 9.25s | cross-domain | 4.02s | ✅ |
| CONV-044 | cross-domain | cross-domain | 6.4s | domain | 4.02s | ❌ |
| CONV-015 | cross-domain | cross-domain | 5.09s | cross-domain | 4.02s | ✅ |
| CONV-023 | universal | universal | 4.29s | universal | 4.02s | ✅ |
| CONV-027 | cross-domain | cross-domain | 4.36s | cross-domain | 4.02s | ✅ |
| CONV-042 | cross-domain | cross-domain | 4.21s | cross-domain | 4.02s | ✅ |
| CONV-001 | cross-domain | cross-domain | 6.02s | domain | 4.02s | ❌ |
| NEG-009 | domain | domain | 6.14s | domain | 4.02s | ✅ |
| CONV-012 | domain | cross-domain | 5.4s | domain | 4.02s | ❌ |
| CONV-024 | cross-domain | cross-domain | 11.01s | universal | 4.02s | ❌ |
| CONV-050 | cross-domain | cross-domain | 6.47s | domain | 4.02s | ❌ |
| CONV-004 | cross-domain | cross-domain | 6.36s | domain | 4.02s | ❌ |
| CONV-037 | domain | cross-domain | 7.22s | domain | 4.02s | ❌ |
| CONV-003 | cross-domain | cross-domain | 6.89s | specialized | 4.02s | ❌ |
| CONV-053 | domain | domain | 6.39s | specialized | 4.02s | ❌ |
| CONV-049 | cross-domain | cross-domain | 8.16s | cross-domain | 4.02s | ✅ |
| NEG-006 | domain | domain | 12.0s | cross-domain | 4.02s | ❌ |
| CONV-047 | cross-domain | cross-domain | 6.68s | cross-domain | 4.02s | ✅ |
| CONV-026 | cross-domain | cross-domain | 4.13s | cross-domain | 4.02s | ✅ |
| CONV-051 | domain | domain | 6.83s | domain | 4.02s | ✅ |
| CONV-006 | cross-domain | cross-domain | 8.33s | cross-domain | 4.02s | ✅ |
| CONV-017 | cross-domain | cross-domain | 6.26s | cross-domain | 4.02s | ✅ |
| CONV-013 | cross-domain | cross-domain | 5.25s | domain | 4.02s | ❌ |
| CONV-002 | domain | cross-domain | 14.17s | domain | 4.02s | ❌ |
| CONV-016 | domain | cross-domain | 7.45s | domain | 4.02s | ❌ |
| CONV-005 | domain | domain | 8.42s | domain | 4.02s | ✅ |
| CONV-030 | cross-domain | cross-domain | 6.17s | cross-domain | 4.02s | ✅ |
| CONV-046 | cross-domain | cross-domain | 6.88s | cross-domain | 4.02s | ✅ |
| CONV-038 | cross-domain | cross-domain | 6.48s | universal | 4.02s | ❌ |
| CONV-043 | domain | domain | 12.42s | domain | 4.02s | ✅ |
| CONV-041 | cross-domain | cross-domain | 7.2s | cross-domain | 4.02s | ✅ |
| CONV-022 | domain | specialized | 4.82s | specialized | 4.02s | ✅ |
| CONV-018 | cross-domain | cross-domain | 4.48s | cross-domain | 4.02s | ✅ |
| CONV-028 | cross-domain | cross-domain | 5.52s | cross-domain | 4.02s | ✅ |
| CONV-052 | domain | domain | 5.25s | domain | 4.02s | ✅ |
| CONV-021 | cross-domain | cross-domain | 6.18s | cross-domain | 4.02s | ✅ |
| CONV-020 | cross-domain | cross-domain | 3.66s | domain | 4.02s | ❌ |
| CONV-032 | cross-domain | cross-domain | 5.27s | cross-domain | 4.02s | ✅ |

## Fail-closed events (surfaced by M1, not swallowed into `domain`)

_None — both paths returned a valid depth label for every FB._

## Verdict

Path B does **not** yet meet the gate. Do not adopt until parity ≥ 90% and zero silent failures are reproduced. Investigate the per-FB mismatches above.
