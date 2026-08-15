# Master Roundtable Evaluation Prompt — v9.0
## S2 → S4 → S5 → S6 READINESS AUDIT — is the pipeline SPOTLESS and ready for the full 750-book push?

**Authority:** D2000–D2361 | Cross-examination: 4-LLM independent audit against Maxwell OS v3.0
**Audience:** S-tier senior RAG/software engineers (evaluators: GPT-OSS, Qwen3.x, Phi-4-mini, Gemma-4-E4B, Claude, ChatGPT)
**Purpose:** Verify the CURRENT S2→S4→S5→S6 pipeline is free of blindspots, gaps, conflicts, mismatches, hidden failures, errors, contamination, missing agreements, bugs, and drift — and issue a GO / NO-GO for the full push.
**Date:** 2026-08-14 (in-place refresh; filename retained for reference stability)

---

## ⚠️ v9.0 CHANGELOG (what changed since v8.0)

| Change | Detail |
|--------|--------|
| **Reframe** | v8.0 was a "S4 classifier benchmark" prompt. v9.0 is a **readiness audit** for the full S2→S4→S5→S6 push (per operator request: "spotless and ready, no blindspot/gap/conflict/mismatch/hidden-failure/contamination/drift"). |
| **Decisions** | 250 → **350** (now D2000–D2361; v8.0 stopped at D2282) |
| **Bugs** | 19 → **74 entries** (BUG-053 through BUG-131) |
| **S5 correction** | NLI threshold is **0.10** (D2298), NOT 0.5 as v8.0 claimed. S5 = **DeBERTa-v3-large NLI-only** (Phi-4-mini removed from S5 *verification*; it is now the S2 fast probe). |
| **S4 reasoning fix (D2359)** | GPT-OSS top-level `reasoning_effort`/`enable_thinking` were **silent no-ops** (oMLX pydantic `extra=ignore`). FIXED: `chat_template_kwargs={"enable_thinking":false}` + `Reasoning: low`. Production-verified: **72.0% acc / 7.3s median (1.95× vs 14.2s)**. |
| **S2 model verdict (D2360)** | Qwen3.8-27B **rejected** (2.76× slower than Qwen3-Coder, dropped 1 FB→NULL). Qwen2.5-3B **deleted**. Qwen3-Coder-30B **retained**. |
| **Model-default bug (D2361)** | `classify_depth_focused()` defaulted to Gemma (S4_DEPTH_MODEL) even when frugal was OFF. **FIXED** to mirror `stage4_merge.py` routing. |
| **GPU panic (BUG-130)** | Dense Qwen3.8-27B + parallel servers → kernel panic. MITIGATED: sequential, one model at a time. |

---

## §1. CURRENT PIPELINE STATE (GROUND TRUTH — verify against these files, do not trust v8.0)

### Active Models

| Role | Model | Notes |
|------|-------|-------|
| S2 Generator | Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | Retained (D2360). temp=0.0. |
| S2 fast probe (`verifier_v2`) | Phi-4-mini-instruct-8bit | D2319 (~1.5s). NOT the S5 verifier. |
| S4 Classifier (`verifier`) | gpt-oss-20b-MXFP4-Q8 | D2359 fix applied. 21B/3.6B-active reasoning MoE. |
| S5 Verifier | MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli | **NLI-only, threshold 0.10** (D2298). |
| Embeddings | bge-m3 | 1024-dim (Ollama). |
| FrugalGPT depth candidate | gemma-4-E4B-it-MLX-4bit | **GATED OFF** (`depth_frugal_enabled: false`); needs ≥90% parity. |
| Removed | Qwen2.5-3B (deleted), Qwen3.8-27B (rejected for S2) | D2360. |

### Stage Map

`0 Convert → 0.5 Metadata → 1 Chunk → 1.3 Prefilter → 1.5 Embed/Cluster → 2 Convergent Extract → 4 Merge/Classify → 5 Verify → 6 Commit`

(Stage 3 removed — D2120/D2198.)

### S4 Depth — verified production numbers (this session)

| Metric | Old (dropped flags) | Now (D2359 fix) |
|--------|--------------------:|----------------:|
| Focused-depth accuracy (50-FB golden) | 67.3% | **72.0%** |
| Median time / FB | ~14.2s | **7.3s (1.95×)** |
| Fail-closed errors | — | **0** |

⚠️ **Known residual bias:** `domain → cross-domain` over-prediction (domain 9/22 = 41%, cross-domain 25/26 = 96%). This is a **prompt/ontology/golden-label ambiguity**, NOT a regression from D2359. Evaluators must judge whether the golden labels or the ontology definitions are at fault.

---

## §2. READINESS CHECKLIST — cross-examine EVERY item

The full push is authorized ONLY if every item below passes. Report any item that fails, is unverifiable, or is "pass-by-accident".

### 2.1 Blindspots (unexamined code paths)
1. Is the legacy **direct-classify path** in `stage4_merge.py` fail-closed under ALL configs (not just batch/merged)? (BUG-126)
2. Is `classify_depth_focused()` model default now identical to `stage4_merge.py` routing? (D2361/BUG-131)
3. Is the **S4 batched depth** path (`batch_depth_classify`, D2354) actually wired, or still dormant behind the <90% parity gate?
4. Are there any callers of `call_omlx` / `call_omlx_json` for a reasoning model that do NOT apply `VERIFY_REASONING_OFF_PREFIX`?

### 2.2 Gaps (missing coverage)
1. Does `source_segments` survive S4 → S6 end-to-end? (BUG-110/M3)
2. Is `is_summary` persisted end-to-end? (BUG-112/M4)
3. Are `evidence_passages` / `_shown` persisted to SQLite (or documented as Parquet-verbatim)? (BUG-111/S1)

### 2.3 Conflicts & mismatches (two places that disagree)
1. `config/pipeline_config.yaml` `verifier` vs `verifier_v2` roles — is each consumed by the stage its comment claims? (D2340 "MISNAMED")
2. `S4_DEPTH_MODEL` (Gemma) vs `VERIFY_MODEL` (GPT-OSS) — does any path run the gated cheap model when frugal is OFF?
3. `config/model_assignments.yaml` vs `pipeline_config.yaml` — any model-registry drift? (D2341)
4. Does the roundtable prompt's own model list match the OMLX `/v1/models` registry?

### 2.4 Hidden failures (silent swallowing / fabricated data)
1. Any `except Exception: pass` remaining in S2/S4/S5/S6? (C16; BUG-127)
2. Any place a missing semantic field (`discipline`/`domains`/`depth`/`evidence`) is silently defaulted to `emerging`/`cited`/`domain`? (D2355/BUG-114)
3. Does `max_failed_ratio: 0.0` actually catch every fail-closed path?

### 2.5 Errors & contamination (data integrity)
1. Golden set drift: `config/golden/stage2_fewshot_convergent.yaml` version vs what the prompt/benchmarks reference. (v8.0 qwen0003 finding: "phantom dataset" risk)
2. Is the 50-FB golden depth set the same one every benchmark used, or have labels drifted?
3. Any stale run-ID checkpoints mixed into the current run? (D2339 runner run-id isolation)

### 2.6 Missing agreements applied
1. D2359 fix — is it applied in ALL FOUR S4 classification paths (merged CRIBS, batch CRIBS, focused depth, batched depth), or only some?
2. D2358 hygiene — are the dead-stub removals actually merged, or re-introduced?
3. Is the Hybrid Gate still DISABLED for T1.1 (BUG-085 net-negative), and is that decision documented?

### 2.7 Bugs & drift (regression surface)
1. BUG-129 (reasoning flags) — RESOLVED? Confirm `chat_template_kwargs` + `Reasoning: low` is live, `Reasoning: none` is gone.
2. BUG-131 (default model) — RESOLVED? Confirm no caller silently hits Gemma.
3. Are any decisions marked RESOLVED/VERIFIED in `decisions.yaml` but not actually implemented in code (or vice versa)?

---

## §3. KNOWN OPEN ITEMS (do not re-litigate; verify their CURRENT status)

| Item | Status | Gate |
|------|--------|------|
| S4 batched depth (D2354) | **NOT wired** — 75% parity < 90% gate | Do not assume it speeds up S4 |
| S5 benchmark-through-production | Open | Verify S5 is actually fail-closed end-to-end |
| W7 `deathpectation` literal | ✅ RESOLVED (2026-08-15) — private Anytype space name | Hygiene |
| FrugalGPT depth cascade (gemma-4-E4B) | Gated off | Needs ≥90% parity + ≥90% held-out |
| Hybrid Gate (BUG-085) | Disabled for T1.1 | Net-negative on A/B |

---

## §4. SPOTLESS ACCEPTANCE CRITERIA (GO / NO-GO)

Issue **GO for full push** ONLY if ALL hold:

1. Every stage (S2, S4, S5, S6) has **zero** fail-open paths (any inference/parse failure raises and is counted by `max_failed_ratio`, never silently defaulted).
2. Every semantic field is either **present-and-valid** or **fail-closed**; no fabricated `emerging`/`cited`/`domain`.
3. Model routing is **deterministic and config-driven** (no hardcoded model name, no default-model mismatch).
4. The depth classifier's residual `domain→cross-domain` bias is **acknowledged and bounded** (either golden labels corrected, or ontology clarified), not silently accepted.
5. Golden sets used for any benchmark are **version-pinned** and match the active `config/golden/*.yaml`.
6. `decisions.yaml` state (RESOLVED/VERIFIED) matches actual code.
7. No `except: pass`, no dead stubs, no `__pycache__`, no stale run-ID artifacts.

---

## §5. CROSS-EXAMINATION PROTOCOL

Each evaluator independently:
1. **Read** the files in §4 Dependency References (below) — do not trust this prompt's claims; re-derive from source.
2. **Run** (read-only where possible): `python3 -m py_compile pipeline/*.py`; `python3 -c "import yaml; yaml.safe_load(open('config/decisions.yaml'))"`.
3. **Check** the §2 checklist item by item.
4. **Issue** a GO / CONDITIONAL-GO / NO-GO with a list of violations, each tagged `[blindspot|gap|conflict|mismatch|hidden_failure|error|contamination|missing_agreement|bug|drift]`.

---

## §6. DEPENDENCY REFERENCES (source of truth — read these, not v8.0)

### Pipeline
- `pipeline/stage2_extract.py` — S2 convergent extraction (Qwen3-Coder-30B)
- `pipeline/stage4_merge.py` — S4 merge + classify (GPT-OSS, fail-closed D2357)
- `pipeline/stage4_merged_call.py` — S4 CRIBS/depth logic (D2359/D2361 fixes here)
- `pipeline/omlx_call.py` — shared OMLX call (chat_template_kwargs/thinking_budget)
- `pipeline/stage5_verify.py` — S5 DeBERTa NLI (threshold 0.10, D2298)
- `pipeline/stage6_commit.py` — S6 SQLite+Parquet commit
- `pipeline/pipeline_paths.py` — config → constants

### Configuration
- `config/pipeline_config.yaml` — v3.0 (verifier/verifier_v2, depth_frugal gated off)
- `config/decisions.yaml` — **350 decisions** (D2000–D2361)
- `config/golden/stage2_fewshot_convergent.yaml` — golden set (verify version)

### Governance
- `CONSTITUTION.md` — v3.0, C1–C28
- `DECISION-LOG.md` — D2000–D2361
- `governance/buglog.md` — BUG-053 through BUG-131
- `governance/aggregated_remaining_tasks.md` — prioritized task register (M/S/W tiers)

### Recent empirical artifacts (this session)
- `governance/s4_depth_d2359_gptoss_production_verify.json` — **72.0% / 7.3s** (the authoritative production number)
- `governance/s4_depth_d2359_ab_benchmark.json` — harness A/B (76% is harness-only, NOT production)
- `governance/s2_qwen38_vs_coder_benchmark.json` — S2 model verdict (Qwen3.8 rejected)

---

## §7. OUTPUT FORMAT

```json
{
  "evaluator_model": "…",
  "evaluator_family": "…",
  "verdict": "GO | CONDITIONAL-GO | NO-GO",
  "violations": [
    {"id": "V-01", "tag": "hidden_failure", "stage": "S4", "file": "pipeline/stage4_merge.py", "detail": "…"}
  ],
  "open_items_confirmed": ["S4 batched depth still dormant", "…"],
  "spotless_criteria": {"fail_open_free": true, "semantic_fail_closed": true, "routing_deterministic": true, "depth_bias_bounded": false, "golden_pinned": true, "decisions_match_code": true, "no_dead_code": true},
  "overall_confidence": 0.0
}
```

---

*Prompt version: v9.0 | Date: 2026-08-14 | Decisions: D2000–D2361 (350) | Bugs: BUG-053–BUG-131*
*Previous: v8.0 (S4 classifier benchmark, D2269–D2282) | This refresh: readiness audit (in-place, filename retained)*
