# Maxwell OS — Aggregated Task Register
> **Updated:** 2026-08-10 17:50 | **Source:** D2240-D2241 (json_repair fix + cross-examination audit)
> **P0:** 8/8 DONE ✅ | **P1:** 7/8 (1 pending) | **P2:** 4/4 DONE ✅
> **Golden set:** v4.4 (73 examples, 75 FBs, 52 pos / 21 neg)
> **DSPy:** MIPROv2 pilot RE-RUNNING (json_repair fix applied, D2240)
> **Model:** gemma-4-31B-it-MLX-8bit — 7/7 shards linked (25GB), ready for OMLX config

---

## 🔴 P0 — BLOCKING (All complete)

| ID | Task | Status |
|----|------|--------|
| T-001 | Strip S4 CRIBS fields (169 instances) | ✅ DONE |
| T-002 | Fix sqlite-vec 1024→512 | ✅ DONE |
| T-003 | Evidence passages 190/190 verbatim | ✅ DONE |
| T-004 | extraction_type in GoldenFB schema | ✅ DONE |
| T-005 | Fix convergence routing | ✅ DONE |
| T-006 | 6 C12 thresholds → config | ✅ DONE |
| **T-007** | **DSPy harness (720 lines) + MIPROv2 pilot** | ✅ CODE DONE — pilot **RE-RUNNING** with json_repair fix |
| T-007b | json_repair name collision (D2240) | ✅ DONE — renamed → json_fixer.py |

---

## 🟡 P1 — QUALITY BLOCKERS

| ID | Task | Status |
|----|------|--------|
| T-008 | Fix 3 depth misclassifications | ✅ DONE |
| T-009 | Cap author concentration at 3 max | ⚠️ Griffiths (5), Meadows (4) still >3. Kahneman/Clear/Heath/Sunstein/Taleb/Gladwell all at ≤3. 2 offenders remain. |
| T-010 | Fix NLI model inversion (ModernBERT primary) | ✅ DONE |
| T-011 | Fix NLI fallback defaults | ✅ DONE (bundled T-006) |
| T-012 | Align taxonomy v5.1 | ✅ DONE |
| T-013 | Golden set version v4.2 | ✅ DONE |
| T-014 | Fix CONV-035/037 false convergence | ✅ DONE |
| T-015 | Extraction type expansion (CM/NH/DM/EP) | ✅ DONE — all 4 types populated |

---

## 🟢 P2 — TECHNICAL DEBT (All complete)

| ID | Task | Status |
|----|------|--------|
| T-016 | NOMIC_MAX_CHARS → EMBED_MAX_CHARS | ✅ DONE |
| T-017 | Remove HDBSCAN dead code | ✅ DONE |
| T-018 | Update schemas.py v2.0→v3.0 | ✅ DONE |
| T-019 | Update MISSION.md v2.0→v3.0 | ✅ DONE |

---

## 🔵 NEW — POST-AUDIT FINDINGS (D2241)

| ID | Finding | Priority | Action |
|----|---------|----------|--------|
| **A-001** | **Remove depth from S2 DSPy Signature** — SYSTEM_PROMPT says S4's job. 0% accuracy proves model can't do it. DSPy ConvergentExtraction forces it. | P0 | Strip `depth` from Signature output fields + `format_golden_fewshot()`. Let S4 classify depth. |
| **A-002** | **Traditional S2 data leakage** — `compare_s2_methods.py` draws few-shot + test from same YAML. Scores inflated. | P1 | Disjoint author split for few-shot vs test. |
| **A-003** | **MIPROv2 pilot re-run** — Was crashing on json_repair.loads. Fixed via D2240. Now running. | P0 | Monitor pilot. Run 4-way comparison when done. |
| **A-004** | **N=6 comparison insufficient** — Statistical significance requires N≥30. | P1 | Expand test set to 20+ held-out examples. |
| **A-005** | **Gemma-4-31B downloaded** — 7/7 shards, 25GB. Ready for OMLX config. | P1 | Configure OMLX, test extraction quality vs Qwen3-Coder. Use for S5 verification (R5), not S2. |
| **A-006** | **Dead code in extraction_metric** — `score += 0.0` at line 383 is a no-op. Not buggy (code works correctly), just dead. | P2 | Remove or comment as intentional. |

---

## 📋 EXECUTION SEQUENCE

### NOW: MIPROv2 pilot running (~15-20 min remaining)
```bash
# Monitor: tail -f /tmp/dspy_mipro_pilot2.log
# Expected: 10 MIPROv2 trials, scores should be >0.0 (previously all 0.0)
```

### AFTER PILOT:
1. **A-001**: Remove depth from DSPy Signature (5 min) — unblocks fair S2 comparison
2. **Run 4-way comparison**: Traditional, DSPy CoT, BS, MIPROv2 on held-out test set
3. **A-005**: Configure Gemma-4-31B in OMLX, test extraction quality
4. **T-009**: Replace 2 Griffiths + 1 Meadows examples with diverse authors
5. **A-002**: Fix few-shot sampling to be author-disjoint
6. **A-004**: Expand test set to 20+ examples

### PUSH CYCLE:
- Current: `f59de87` (D2240: json_repair fix) — pushed
- Next: D2241 governance + pilot results + comparison data

---

## STATUS SUMMARY

```
P0: ████████████████████ 8/8 (100%)
P1: ████████████████░░░░ 7/8 (87%) — T-009: 2 author offenders
P2: ████████████████████ 4/4 (100%)
NEW: ░░░░░░░░░░░░░░░░░░░░ 0/6 (0%)  — Post-audit findings
──────────────────────────────────
TOTAL: ████████████████░░░░ 19/25 (76%)
```
