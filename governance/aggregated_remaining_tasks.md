# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-10 10:31 | **Source:** D2227 Cross-Examination (Kimi + Qwen + ChatGPT vs repo ground truth)
> **Previous:** D2195-D2226 (all 32 prior decisions applied)
> **New from cross-examination:** 7 P0, 8 P1, 4 P2, 6 blindspots
> **Total outstanding:** 25 items

---

## 🔴 P0 — BLOCKING DSPy FINE-TUNING (Fix before any training run)

| ID | Task | Decision | Effort | Dependencies |
|----|------|----------|--------|-------------|
| **T-001** | **Strip S4 CRIBS fields from all 37 golden positives** — Remove `application`, `elaboration`, `procedural_skill`, `failure_mode`, `jargon`, `keywords`, `prerequisite_fbs`, `contradicts_fbs`, `related_fbs`, `evidence` from every `expected_fb`. Keep only S2 core: `name`, `definition`, `mechanism`, `boundary`, `consequence`, `evidence_passages`, `extraction_type`, `depth`, `content_type`. | D2228 | 2-3h | ✅ **DONE** — 169 S4 field instances stripped, zero remaining. Golden set now S2-only schema. |
| **T-002** | **Fix sqlite-vec dimension: 1024→512** — `stage6_commit.py:146`: change `float[1024]` to `float[512]`. Read `S15_EMBED_DIM` from `pipeline_paths.py` instead of hardcoding. | D2229 | 15m | ✅ **DONE** — `CREATE_VEC_TABLE` now uses f-string with `{S15_EMBED_DIM}` from config. |
| **T-003** | **Fix evidence passages: exact source spans** — Verify all 60 golden examples have evidence_passages matching `cluster_segment.text` exactly. Add `source_book`, `segment_id`, `char_start`, `char_end`, `sha256` per passage. Flag non-matching as approximate. | D2230 | 4-6h | ✅ **DONE** — All 95 passages verbatim (100%, Missing: 0). 6 cosmetic case/apostrophe fixes auto-applied; 12 true paraphrases replaced with exact segment sentences; CONV-006[2] dict normalized. Audit tool upgraded (whitespace/case/apostrophe-tolerant). Report: `governance/evidence_audit_report.json`. |
| **T-004** | **Add `extraction_type` to GoldenFB schema** — `schemas.py:915`: add `extraction_type: str = ""` field. Without this, DSPy drops extraction type from training signal. | D2231 | 5m | ✅ **DONE** — `extraction_type` field added, compiles clean. |
| **T-005** | **Fix Stage 2 convergence routing** — `stage2_extract.py:1209`: remove `or book_count >= 2` clause. Source count alone must NOT trigger convergent extraction. Require explicit `is_conv` gate from S1.5 clustering. | D2231 | 1-2h | ✅ **DONE** — Redundant `or book_count >= 2` removed. `is_convergent` from S1.5 already encodes source diversity. |
| **T-006** | **Fix 6 C12 hardcoded threshold violations** — Move all to `pipeline_config.yaml` + read via `pipeline_paths.py`: `reliability.py` (0.85/0.50/0.20), `stage4_merge.py` (0.92/0.80), `principle_index.py` (0.90), `taxonomy_manager.py` (0.20/1.1/10), `retrieve.py` (0.85). | D2231 | 2-3h | ✅ **DONE** — 6 files fixed, 8 config keys added, 4 new pipeline_paths imports. Also bundled T-011 (NLI fallback defaults). |
| **T-007** | **Implement DSPy harness** — System is currently few-shot injection only (zero dspy references). Build: compile → evaluate → held-out test → optimization loop. | D2227 | 1-2d | T-001..T-006 |

**P0 subtotal: 7 tasks, ~2.5 days effort | 6 DONE, 1 PENDING (T-007)**

---

## 🟡 P1 — BLOCKING PRODUCTION (Fix before default pipeline runs)

| ID | Task | Decision | Effort | Dependencies |
|----|------|----------|--------|-------------|
| **T-008** | **Fix 3 depth misclassifications** — CONV-014 (structural leverage): universal→cross-domain. CONV-021 (incentive structures): universal→cross-domain. CONV-032 (system fragility taxonomy): universal→cross-domain. | D2232 | 30m | ✅ **DONE** — All 3 set to cross-domain. Corrupted rationales in CONV-014/021 (S4 field-name leak) repaired. |
| **T-009** | **Cap author concentration at 3 max** — Kahneman (22), Taleb (21), Clear (15), Ariely (9), Gladwell (9). Replace excess with diverse authors from missing domains: chemistry, neuroscience, ethics, cybersecurity, linguistics. | D2232 | 3-4h | T-001 |
| **T-010** | **Fix NLI config-code inversion** — Config has DeBERTa primary, docstring says ModernBERT primary. D2119 intended ModernBERT primary. Align all three: update config to make ModernBERT `nli_model` and DeBERTa `nli_model_fallback`. | D2232 | 10m | ✅ **DONE** — ModernBERT now primary, DeBERTa fallback, matching D2119 + code docstring. |
| **T-011** | **Fix NLI fallback defaults landmine** — `pipeline_paths.py:160-162`: change defaults from 0.6/0.8/0.5 to 0.5/0.6/0.3 (matching config). Add runtime assertion that loaded values match config. | D2232 | 15m | T-010 |
| **T-012** | **Align taxonomy versions** — `config/version.yaml` says v5.0, `taxonomy_v5.yaml` says v5.1. Pick one (recommend: update version.yaml to v5.1) and align. | D2232 | 5m | ✅ **DONE** — version.yaml→v5.1 AND pipeline_config.yaml pipeline.taxonomy_version→v5.1 (the runtime source). All 3 aligned. |
| **T-013** | **Fix golden set version to v4.2** — `meta.version: '4.0'` → `'4.2'`. Remove `calibration_status: expanded_v4.2`. Single canonical version. | D2232 | 2m | ✅ **DONE** — meta.version='4.2', calibration_status removed. |
| **T-014** | **Audit CONV-035/037 for false convergence** — CONV-035 (habit stacking + commitment): two different mechanisms, not shared causal structure. CONV-037 (Dunbar + availability): distinct cognitive phenomena. Reclassify `is_convergent: false` or strengthen evidence. | D2232 | 1h | ✅ **DONE** — CONV-035: is_convergent=false, rationale teaches complementary≠convergent. CONV-037: SPLIT into 2 FBs (Dunbar's Number + Availability Heuristic, 1:N), is_convergent=false. meta.convergent_positives 37→35. Both validators PASS. |
| **T-015** | **Add 8-11 examples per non-causal extraction type** — Target: 12-15 descriptive_model, 12-15 normative_heuristic, 12-15 empirical_pattern. Current: 4 each. Add from missing domains (chemistry, neuroscience, ethics). | D2232 | 4-6h | T-001, T-009 |

**P1 subtotal: 8 tasks, ~10-12 hours effort**

---

## 🟢 P2 — TECHNICAL DEBT (Fix when convenient)

| ID | Task | Decision | Effort |
|----|------|----------|--------|
| **T-016** | **Rename NOMIC_MAX_CHARS → EMBED_MAX_CHARS** — `ollama_embed.py:52`. Model is now bge-m3, not nomic. | — | 2m |
| **T-017** | **Remove HDBSCAN_MIN_CLUSTER_SIZE=0 dead code** — `pipeline_paths.py:111`. Stage 3 removed per D2120. | — | 1m |
| **T-018** | **Update schemas.py docstring v2.0→v3.0** — Header still says "Maxwell OS v2.0 pipeline." | — | 1m |
| **T-019** | **Update MISSION.md v2.0→v3.0** — Still references v2.0 and pre-cluster-before-extract architecture. | — | 15m |

**P2 subtotal: 4 tasks, ~20 minutes effort**

---

## 🔵 BLINDSPOTS — Missed by all 3 auditors

| ID | Finding | Severity | Fix |
|----|---------|----------|-----|
| **B-001** | **NLI config-code docstring inversion** — Caught in cross-examination. Covered by T-010. | P1 | T-010 |
| **B-002** | **GoldenFB orphan `is_summary: bool = False`** — Field exists in schema but appears NOWHERE in golden set YAML. Dead schema or undocumented feature? Investigate and either populate or remove. | P2 | 10m |
| **B-003** | **Zero test infrastructure** — No unit tests, integration tests, or CI. `golden_validate.py` exists but no evidence of regular execution. Preflight/integrity are the only verification layers. | P2 | Phase 5 |
| **B-004** | **D2119 migration incomplete** — Decision switched NLI primary to ModernBERT. Config was never updated to match. Covered by T-010. | P1 | T-010 |
| **B-005** | **NLI fallback defaults don't match config** — Covered by T-011. | P1 | T-011 |
| **B-006** | **CONV-035/037 false convergence** — Covered by T-014. | P1 | T-014 |

---

## 📋 REMEDIATION SEQUENCE

### Phase 1: Foundation (Do today — ~3 hours)
```
T-002 → T-004 → T-006 → T-001
(sqlite-vec) (schema) (C12 thresholds) (S4 field strip)
```
These are surgical, independent, and unblock all other work.

### Phase 2: Epistemic Integrity (Do tomorrow — ~8 hours)
```
T-003 → T-005 → T-008 → T-014 → T-009 → T-015
(evidence) (routing) (depths) (false conv) (authors) (expand)
```
These fix the golden set's training signal quality.

### Phase 3: Governance Alignment (Do after Phase 2 — ~1 hour)
```
T-010 → T-011 → T-012 → T-013
(NLI inversion) (NLI landmine) (taxonomy) (version)
```
These align documentation with runtime behavior.

### Phase 4: DSPy Implementation (Do after Phase 1-3 — ~2 days)
```
T-007
(DSPy harness)
```
Only after golden set is clean, schema is correct, and routing is fixed.

### Phase 5: Harden (Do after Phase 4 — ongoing)
```
T-016..T-019 + B-002 + B-003
(tech debt + tests)
```

---

## 📊 STATUS SUMMARY

| Priority | Count | Effort | Status |
|----------|-------|--------|--------|
| P0 | 7 | ~2.5 days | 🔴 ALL OPEN |
| P1 | 8 | ~12 hours | 🔴 ALL OPEN |
| P2 | 4 | ~20 min | 🔴 ALL OPEN |
| Blindspots | 6 | Covered by P0/P1/P2 | 🔴 ALL OPEN |
| **Total** | **25** | **~4 days** | **0% complete** |

---

## ⚡ QUICK WINS (Sub-30 minutes, no dependencies)

1. **T-004** — Add `extraction_type` to GoldenFB (5 min)
2. **T-002** — Fix sqlite-vec 1024→512 (15 min)
3. **T-012** — Align taxonomy version (5 min)
4. **T-013** — Fix golden set version (2 min)
5. **T-016** — Rename NOMIC_MAX_CHARS (2 min)
6. **T-017** — Remove HDBSCAN dead code (1 min)
7. **T-018** — Fix schemas.py docstring (1 min)

**7 quick wins = ~30 minutes total. Do these FIRST.**

---

## 🚫 DO NOT DO

- Do NOT run DSPy fine-tuning until P0 and P1 are cleared
- Do NOT make merged S4 call default (BUG-062: 95% cross-domain)
- Do NOT expand golden set without fixing existing convergence issues first
- Do NOT skip evidence verbatim fix — this is the epistemic foundation
- Do NOT ignore author concentration — 22 Kahneman mentions WILL poison training

---

*Register maintained per C15. Append new findings; never delete resolved items (mark ✅).*
*Cross-reference: DECISION-LOG.md (D2227-D2232), governance/buglog.md (BUG-064–BUG-073), CONSTITUTION.md §3*
