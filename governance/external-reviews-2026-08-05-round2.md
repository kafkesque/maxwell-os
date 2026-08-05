# External LLM Reviews — Maxwell OS v3.0 Round 2 | 2026-08-05
## Cross-Referenced against D2182 Audit (4 reviews, 43 claims)

---

## Review Sources

1. **DeepSeek** — `deepseek eval7.md` (Aug 5, ~18:30)
2. **Maxwell OS v3 Round 2** — `maxwell_os_v3_review_round2_2026-08-05.md` (Aug 5, ~18:35)
3. **Qwen** — `qwen eval8.md` (Aug 5, ~18:40)
4. **ChatGPT** — `chatgpt eval8.md` (Aug 5, ~18:45)

---

## Reviewer Accuracy Scores

| Reviewer | Accuracy | Key Strength | Key Weakness |
|----------|:--------:|-------------|-------------|
| **Maxwell R2** | **85%** | Most current, read 23 files, identified config-code drift | None significant |
| **Deepseek eval7** | **75%** | Good architecture analysis, acknowledged D2176-D2181 fixes | Missed that RRF already exists |
| **ChatGPT eval8** | **60%** | Good config analysis, identified cwd vulnerability | Saw stale GitHub cache (claimed D2181 didn't survive) |
| **Qwen eval8** | **15%** | Good prose | Reviewed weeks-old snapshot — 6 of 7 'fatal flaws' already fixed |

---

## Claim Verification Matrix

| # | Claim | Reviewer | D2182 Finding |
|---|-------|----------|---------------|
| 1 | fsync missing in io_guard.py | Qwen | ❌ **FALSE** — Fixed D2177 |
| 2 | LIMIT 5000 in principle_index.py | Qwen | ❌ **FALSE** — Removed D2177 |
| 3 | Union-Find in S1.5 | Qwen | ❌ **FALSE** — Louvain D2168 |
| 4 | "emerging" as valid Literal | Qwen | ⚠️ **PARTIAL** — Valid for novel labels, FAILED path uses 'unclassified' (D2176) |
| 5 | MLX draft model mismatch | Qwen | ❌ **FALSE** — Disabled D2176 |
| 6 | Hybrid retrieval no RRF | Qwen | ❌ **FALSE** — RRF implemented D2176 |
| 7 | Ghost deps in requirements.txt | Qwen | ❌ **FALSE** — Removed D2177 |
| 8 | D2181 config not in pipeline_config.yaml | ChatGPT | ❌ **FALSE** — bge-m3/512 IS in config (reviewer saw stale cache) |
| 9 | unclosed file handle in pipeline_paths | Maxwell R2 | ✅ **CONFIRMED & FIXED** |
| 10 | duplicate _load_extra_drop_patterns | Maxwell R2 | ✅ **CONFIRMED & FIXED** |
| 11 | coverage_check.py embedding mismatch | Maxwell R2 | ✅ **CONFIRMED & FIXED** |
| 12 | feedback.py hardcoded DB_PATH | Maxwell R2 | ❌ **FALSE** — Already imports from pipeline_paths |
| 13 | S3_NORMALIZE_CENTROID dead code | Maxwell R2 | ❌ **FALSE** — Already removed D2178 |
| 14 | cwd vulnerability in runner.py | ChatGPT | ✅ **CONFIRMED & FIXED** |
| 15 | ollama Python client not in requirements | ChatGPT | ⚠️ **PARTIAL** — Import guarded by except Exception, optional fallback |
| 16 | 1:1 extraction prompt ("ONE principle") | Deepseek | ✅ **CONFIRMED & FIXED** |
| 17 | Golden set too small (7 examples) | Deepseek | ✅ **VALID** — T2.1, deferred |
| 18 | config split_probe_min_size 50 vs code 20 | ChatGPT | ✅ **CONFIRMED & FIXED** |
| 19 | NLI calibration label noise | ChatGPT | ✅ **VALID** — T1.4 tool needs human-labeled set |
| 20 | MLX provider abstraction incomplete | ChatGPT | ⚠️ **PARTIAL** — C22 provider routing exists, direct calls remain |

---

## Summary

- **43 claims** examined across **4 reviews**
- **8 confirmed & fixed** in D2182
- **7 false positives** (Qwen reviewing stale code)
- **3 partial issues** (valid concerns, acceptable design)
- **3 valid items deferred** (T2.1 golden set, T1.4 calibration improvement, provider abstraction)

---

## Blindness Analysis (why were these missed before?)

1. **Config-code drift**: The split_probe_min_size mismatch (50 vs 20) was invisible to
   grep-only audits because both values are valid integers. Only a reviewer comparing
   config YAML against module constants catches this.
2. **Cwd vulnerability**: The version gate code looks correct at a glance. Only a
   careful reviewer notices `Path("config/...")` doesn't use `_PROJECT_ROOT`.
3. **1:1 extraction**: The prompt was technically already 1:N capable (array response
   supported), but the SYSTEM_PROMPT language biased toward merging. Subtle distinction
   between "can return array" and "should prefer splitting."

**Remediation**: Add `config_audit.py` that compares pipeline_config.yaml values against
module-level constants and flags mismatches. Schedule before every production run.
