# Maxwell OS v3.0 — Comprehensive Smoke Test & Golden Evaluation Prompt v2
> **Purpose:** Multi-LLM cross-examination of diverse pipeline output for golden example injection
> **Date:** 2026-08-09 | **Evaluators:** Qwen, Kimi, ChatGPT, Claude, Maxwell V2

---

## FILES TO ATTACH (exactly these 2):

### 1. `knowledge pipeline/stage4_merge/latest/SMOKE_TEST_REPORT.md`
Smoke Test v1: 12 FBs with full S4→S5 output. Covers initial golden evaluation.

### 2. `knowledge pipeline/stage4_merge/latest/SMOKE_TEST_V2_REPORT.md`  
Smoke Test v2: 20 gap-filling FBs — citation echo, taxonomy negatives, specialized positives, null-application candidates, strong positives, diverse fill.

### 3. `config/golden/stage2_fewshot_convergent.yaml`
27 existing golden examples — BASELINE comparison.

**All 3 files needed for complete evaluation. The v1 and v2 reports together cover 32 diverse FBs across all structural categories.**

---

## CHANGES SINCE LAST ROUNDTABLE

1. **Fix 0.1:** Application is now NULL-ABLE. Descriptive principles (taxonomies, mechanisms) should have `application: null`. Golden examples must now include null-application positives.
2. **Fix 0.2:** mechanism/boundary/consequence now flow from S2→S4→S5. No more fallback to application/failure_mode/elaboration.
3. **Fix 0.4:** MAX-entailment NLI scoring (not proportion-based). Strongest passage signal wins.
4. **Fix 0.3:** Multi-FB merge path deleted. All clusters have exactly 1 principle.
5. **Golden field fix:** All 27 golden examples now have `elaboration`, `extraction_type`, `content_type`.

---

## PRIOR ROUNDTABLE CONSENSUS

### Qwen (Evaluator 1):
- **ACCEPT all 3 PASS FBs** (OST 8.5, Probabilistic Token 9.0, Speculative Design 8.0)
- All 9 QUARANTINE FBs are valid negatives
- Missing: taxonomy_not_principle, engineering_tradeoff not in golden set

### Kimi (Evaluator 2):
- **ACCEPT Speculative Design only** (7.05)
- **NEEDS_WORK:** OST (5.45), Probabilistic Token (5.55)
- **PROMOTE TO POSITIVE after fix:** Peircean Sign (3.4), Modular System Design (3.2), Identity-driven Decision Making (3.2)
- **FIXABLE:** Synchronic/Diachronic (too narrow but legitimate specialized)
- **NLI 0.8 threshold too strict for axiomatic evidence**

### Divergence to resolve:
| FB | Qwen | Kimi | Resolution needed |
|----|------|------|-------------------|
| OST Framework | ACCEPT 8.5 | NEEDS_WORK 5.45 | Is it a principle or a framework description? |
| Probabilistic Token | ACCEPT 9.0 | NEEDS_WORK 5.55 | Descriptive mechanism or prescriptive principle? |
| Peircean Signs | Negative 4.0 | PROMOTE 3.4 | Taxonomy or legitimate principle? |
| Modular Design | Negative 4.5 | PROMOTE 3.2 | Axiomatic evidence: valid or not? |

---

## ROUNDTABLE v2 QUESTIONS

### Section A: Resolve Prior Divergence

For each of the 4 contentious FBs above, state your position with specific evidence:

| Q | FB | Question |
|---|----|----------|
| **A1** | OST Framework | Is this a GENUINE PRINCIPLE (answers WHY/WHEN) or a FRAMEWORK DESCRIPTION (answers WHAT/HOW)? If the latter, can it be reframed? |
| **A2** | Probabilistic Token | Should descriptive technical mechanisms be accepted as golden positives, or only prescriptive principles? Does null-able application change your answer? |
| **A3** | Peircean Signs | Taxonomies = classify, principles = predict/explain. Does the icon/index/symbol mechanism constitute a causal explanation, or is it structural classification? |
| **A4** | Modular Design | 39 sources, axiomatic evidence, NLI-failed. Is this a genuine universal principle with poor evidence presentation, or a generic truism? |

### Section B: New Structural Questions

| Q | Question |
|----|----------|
| **B1** | Should the golden set include `application: null` examples? If yes, which smoke test FBs qualify? |
| **B2** | Should `specialized` depth ever be a positive? (Qwen says no, Kimi says Synchronic/Diachronic should be) |
| **B3** | Should `extraction_type: causal_mechanism` vs `empirical_pattern` vs `normative_heuristic` be included in golden examples? |
| **B4** | What is the minimum source count for a golden positive? (Kimi flagged Speculative Design at 2 books — is 2 enough?) |

### Section C: Regression Testing Needs

| Q | Question |
|----|----------|
| **C1** | How many FBs are needed for a statistically valid regression test? (Minimum, recommended) |
| **C2** | What distribution of PASS/FLAG/QUARANTINE should a regression sample have? |
| **C3** | Should regression samples include FBs from ALL depth levels (universal, domain, specialized)? |
| **C4** | Should regression include edge cases: single-source, null-application, axiomatic evidence? |

---

## CONSENSUS OUTPUT FORMAT v2

```yaml
resolved_positives:  # FBs we ALL agree belong in golden set
  - fb_name: "..."
    consensus_score: X.X
    conditions: "Add 3rd source" or "Fix evidence" or "None"

resolved_negatives:  # FBs we ALL agree are good negative examples
  - fb_name: "..."
    flaw_type: "citation_echo | vague_mechanism | taxonomy_not_principle | ..."
    utility: X.X

contentious:  # FBs we DISAGREE on — escalate to human
  - fb_name: "..."
    positions: {Qwen: ACCEPT, Kimi: NEEDS_WORK}
    recommendation: "..."

structural_recommendations:
  null_application_examples: ["FB names"]
  specialized_positives: ["FB names"]
  regression_sample_size: {minimum: N, recommended: N}
  regression_composition: "X PASS, Y FLAG, Z QUARANTINE"
  minimum_source_count: N
```
