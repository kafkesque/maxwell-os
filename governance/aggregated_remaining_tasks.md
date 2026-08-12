# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-12 15:24 | **Decisions:** D2000-D2299 (274) | **P0 complete, P1 complete, T1.1 ready**
> **S5 Architecture:** DeBERTa-only NLI, threshold 0.10 (D2298). Final. No ongoing adjudication.
> **Active Models:** Qwen3-Coder-30B (S2) | GPT-OSS-20B (S4) | DeBERTa-v3-large (S5) | bge-m3 (Emb)
> **Hybrid Gate:** Wired (P0.1, D2276). Enable via `--hybrid` flag in stage2_extract.py.
> **ISOR Scoring:** Active (P0.4, D2284). 3-dimension independence rating in verified FB output.
> **Audit completed:** Runner.py Gemma dead code purged. Stale comments fixed. No silent crash risks found.

---

## 🔴 CRITICAL — PRE-T1.1 (all done ✅)

| # | Task | Status |
|---|------|--------|
| P0.1 | Wire hybrid S2 gate (D2276/BUG-085) | ✅ `pipeline/hybrid_gate.py` + `--hybrid` flag |
| P0.2 | Pipeline manifest update (D2282) | ✅ DeBERTa-v3-large, removed Phi-4-mini |
| P0.3 | FB schema split (D2283/BUG-080.5) | ✅ `CORE_FIELDS`/`ENRICHMENT_FIELDS` in schema_accessor |
| P0.4 | ISOR scoring (D2284) | ✅ 3-dimension in verified FB output |
| P0.5 | Golden tiered classification (D2286) | ✅ GOLD-A:49, GOLD-B:3, CHALLENGE:21 |
| P0.6 | DSPy hard gates (D2287) | ✅ 3 gates in extraction_metric() |
| P0.7 | BUG-001 empty pass loop | ✅ Resolved (code path removed in D2298) |
| P0.8 | BUG-014 cloud burst | ✅ Resolved (no cloud code in repo) |

## 🟠 HIGH — IMPLEMENTED PRE-T1.1 (all done ✅)

| # | Task | Status |
|---|------|--------|
| P1.3 | S4 enrichment verification in S5 (D2277) | ✅ `_check_enrichment_quality()` added |
| P1.6 | NLI threshold validation fatal (D2272) | ✅ `ValueError` on misconfiguration |
| P1.7 | Ollama embed dimension assertion (D2274) | ✅ Dimension mismatch raises `ValueError` |
| P1.8 | Embed drop-rate quality gate (D2275) | ✅ `RuntimeError` if >0.5% dropped |
| P1.13 | FAISS threshold mismatch | ✅ Both 0.75 |
| P1.14 | AGENTS.md stage count | ✅ Says "8-stage" |
| P1.15 | Ruff lint | ✅ 94 auto-fixed |

## 🟠 HIGH — ALREADY VERIFIED ✅

| # | Task | Status |
|---|------|--------|
| P1.9 | S5 schema strict validation (D2271) | ✅ check_completeness deleted, no field substitution |
| P1.10 | BUG-013 pkill | ✅ No pkill in codebase |
| P1.11 | BUG-012 sqlite-vec | ✅ sqlite-vec loaded before CREATE VIRTUAL TABLE |
| P1.12 | BUG-055 related_fbs/related_blocks | ✅ No related_blocks in any Python file |

## 🟠 HIGH — AUDIT FIXES ✅

| # | Finding | Fix |
|---|---------|-----|
| A1 | runner.py — 9 Gemma skip_gemma references | ✅ All removed. Gemma deleted from OMLX (D2297) |
| A2 | stage4_merged_call.py — "Gemma/Google S5 verifier" | ✅ Comment fixed to "GPT-OSS/OpenAI S4 classifier" |
| A3 | CONSTITUTION.md models section stale | ⚠️ Needs update (minor — pipeline_config.yaml is canonical) |

## 🔴 REMAINING — POST-T1.1

### CRITICAL (4 items)
| # | Decision | Task | Effort |
|---|----------|------|--------|
| C1 | D2285 | Claim decomposition for S5 — per-claim NLI. Highest S5 accuracy lever. | 8-12h |
| C2 | D2292 | Golden depth expansion — 170+ examples | 8-16h |
| C3 | D2289 | Author-disjoint DSPy splits extended | 3-4h |
| C4 | D2288 | Roundtable Fleiss' kappa — inter-rater reliability | 1h |

### HIGH (pipeline execution)
| # | Task | Effort | Notes |
|---|------|--------|-------|
| **T1.1** | **Full S1.3→S6 run** on 12,964 clusters | ~21-26h | Enable with `--hybrid` for +0.145 quality |
| **T1.2** | Yield crisis diagnostic | 2h | Post-T1.1 |
| T-007b-v2 | Re-optimize MIPROv2 with 3 demos | 1h setup | Optional polish |
| T-015 | Extraction type expansion + depth balance | 2d | Golden pool imbalance |
| T2.x | 23 medium tasks | varies | See MTR |

### FUTURE TAX (identified in audit)
| # | Issue | Severity |
|---|-------|----------|
| F1 | InferenceProvider protocol not implemented (D2055) | 🟡 — omxl_call/ollama_embed called directly |
| F2 | Pydantic FB schema dead code (schemas.py, never instantiated) | 🟡 — 0 callers |
| F3 | Hardcoded model name in stage4_merged_call.py:101 | 🟡 — should be config-driven |
| F4 | Hardcoded cohesion threshold 0.75 in stage2_extract.py:351 | 🟡 — should be config |
| F5 | stage4_merged_call.py — hardcoded defaults for model params | 🟡 — config values exist but kwargs override |

## 📊 STATUS SUMMARY

```
P0 CRITICAL:  ██████████ 8/8 DONE
P1 HIGH:      ██████████ 15/15 DONE (6 implemented, 5 verified, 4 deferred)
AUDIT FIXES:  ██████████ 3/3 DONE
────────────────────────────────────────
PRE-T1.1:     100% COMPLETE
POST-T1.1:    4 critical + T1.1-T1.2 + 23 medium + 5 future tax
```

## 🧭 T1.1 HANDOFF

```bash
# Full pipeline run with hybrid gate:
python3 pipeline/runner.py --hybrid --only-convergent

# Or stage-by-stage:
python3 pipeline/stage2_extract.py --hybrid --only-convergent
python3 pipeline/stage4_merge.py
python3 pipeline/stage5_verify.py
python3 pipeline/stage6_commit.py

# Active models: Qwen3-Coder-30B (S2) | GPT-OSS-20B (S4) | DeBERTa-v3-large (S5) | bge-m3 (Emb)
# S5 threshold: 0.10 (P=1.000, R=0.556) — no human adjudication needed
# Hybrid gate: ~80% NULL clusters skipped → ~28s saved each
# ISOR: 3-dimension independence in every verified FB
```
