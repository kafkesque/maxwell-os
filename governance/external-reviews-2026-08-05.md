# External LLM Reviews — Maxwell OS v3.0 | 2026-08-05
## Cross-Referenced against D2178 Audit

---

## Review Sources

1. **Kimi k2** — `kimi eval6.md` (Aug 5, 17:17)
2. **Kimi k2** — `kimi eval7.md` (Aug 5, 17:44)
3. **Qwen** — `qwen eval7.md` (Aug 5, 17:41)
4. **DeepSeek** — `deeps eval 6.md` (Aug 5, 17:40)
5. **ChatGPT** — `chatgpt eval7.md` (Aug 5, 17:39)
6. **Maxwell OS v3 Review** — `maxwell_os_v3_review_2026-08-05.md` (Aug 5, 17:43)

---

## Claim Verification Matrix

| # | Claim | Source | D2178 Finding |
|---|-------|--------|---------------|
| 1 | `_process_cluster` returns list, crashes `fb.get("_null")` | Kimi7/Maxwell | ✅ **CONFIRMED & FIXED** |
| 2 | `ensure_dirs()` references undefined `S3_DIR` | Kimi7/Maxwell | ✅ **CONFIRMED & FIXED** |
| 3 | `_call_mlx_json` passes unsupported `repair_fn=` | Kimi7/Maxwell | ✅ **CONFIRMED & FIXED** (MLX path) |
| 4 | `classification_errors` scope bug (`dir()` shadowing) | Kimi7/Maxwell | ⚠️ Code smell (not active bug — same scope) **CLEANED** |
| 5 | `"emerging"` as valid Literal → silent fallback | Qwen7 | ⚠️ Exception path already fixed (D2176). Map path is legitimate. |
| 6 | Embedding model mismatch (bge-small vs bge-m3) | Kimi7/Maxwell | ✅ **CONFIRMED** — deferred to v3.1 |
| 7 | S3 dead code (`S3_NORMALIZE_CENTROID`) | Kimi7/Maxwell | ✅ **CONFIRMED & FIXED** |
| 8 | Reciprocity underreported 2× | Kimi7/Maxwell | ✅ **CONFIRMED & FIXED** |
| 9 | MinHash word-level (not n-gram) | Kimi7/Maxwell | ✅ **CONFIRMED & FIXED** |
| 10 | NLI on CPU (no MPS auto-detect) | Kimi7/Maxwell | ✅ **CONFIRMED & FIXED** |
| 11 | Union-Find still active | Kimi6 | ❌ **FALSE** — Louvain (D2168) |
| 12 | Zero-padding hack | Kimi6 | ❌ **FALSE** — ValueError (D2170) |
| 13 | Segment/embedding misalignment | Kimi6 | ❌ **FALSE** — tracking (D2172) |
| 14 | `is_noise: True` | Kimi6 | ❌ **FALSE** — `False` (D2171) |
| 15 | fsync missing in io_guard | Qwen7 | ❌ **FALSE** — present (D2177) |
| 16 | LIMIT 5000 in principle_index | Qwen7/Kimi6 | ❌ **FALSE** — removed |
| 17 | Qwen2.5 draft model mismatch | Qwen7 | ❌ **FALSE** — disabled (D2176) |
| 18 | No RRF in retrieve | Deeps/Qwen | ❌ **FALSE** — implemented (D2176) |
| 19 | No OMLX timeout | Kimi6 | ❌ **FALSE** — present |
| 20 | schema_version 2.2 | Kimi6 | ❌ **FALSE** — 3.0 |
| 21 | Hardcoded paths with spaces | Kimi6 | ⚠️ PARTIAL — deferred |
| 22 | Golden set insufficient (7 examples) | Deeps/Kimi7 | ✅ **VALID** — deferred |
| 23 | No JSON Schema validation on LLM output | Kimi6 | ✅ **VALID** — deferred |

---

## Summary

- **23 claims examined across 6 reviews**
- **10 claims already fixed** in D2168-D2177 (prior commits)
- **7 claims confirmed & fixed** in D2178 (this commit)
- **2 claims confirmed as code smells** (cleaned, not bugs)
- **4 claims deferred** to v3.1 (embedding model unification, golden set expansion, hardcoded paths, JSON schema validation)

**Key insight:** Kimi eval6 evaluated a stale codebase snapshot, producing 12 false-positive P0 bug reports. Qwen eval7 correctly identified that prior patches fixed most issues but was itself wrong about fsync and LIMIT 5000. The most accurate reviews were maxwell_os_v3_review and deeps eval6.

---

## Deferred Items (v3.1)

1. **Unify embedding model** (bge-small vs bge-m3) — requires re-embedding all segments
2. **Expand golden set** (7 → 200+ examples) — requires manual annotation
3. **JSON Schema validation** on LLM outputs — requires Pydantic model integration
4. **Singleton extraction redesign** — speculative candidates with human review
5. **Cross-run dedup** (D2067) — persistent principle index
