# Maxwell OS v3.0 — E2E Diagnostic Report
> **Run ID:** `diagnostic_20260811_155958`
> **Date:** 2026-08-11
> **Books sampled:** 100
> **Seed:** 42
> **Gate criteria (D2261):** Yield >1% + S5 pass >40% → approve T1.1

## 1. Pipeline Summary

| Stage | Result | Time |
|-------|--------|------|
| S2 Extract | ❌ [Errno 2] No such file or directory: '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0/knowledge pipeline/checkpoints/stage2_extract/diagnostic_20260811_155958/tmpmg926hjn.tmp' | ?s |
| S4 Merge+Classify | 0 FBs | ?s |
| S5 Verify | 0 FBs (PASS=0, QUARANTINE=0, FAIL=0) | ?s |
| S6 Commit | ✅ ? | ?s |

## 2. Gate Decision (D2261)

- **Yield:** 0 FBs / 100 books = **0.0%**
- **S5 Pass Rate:** 0.0% (0/0)

### 🛑 GATE FAILED — HALT AND DIAGNOSE
Reasons: Yield 0.0% below 0.5% minimum; S5 pass rate 0.0% below 20% minimum.
Do NOT launch T1.1. Investigate root cause.

## 3. S5 Verification Detail

| Status | Count | % |
|--------|-------|---|
| PASS | 0 | 0.0% |
| QUARANTINE | 0 | 0.0% |
| FAIL/FLAG | 0 | 0.0% |

## 4. All Foundation Blocks (0 total)
