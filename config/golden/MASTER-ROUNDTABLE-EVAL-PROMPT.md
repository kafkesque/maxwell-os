# Maxwell OS v3.0 — Master Roundtable Evaluation Prompt
> **Purpose:** Multi-LLM cross-examination of pipeline output for golden example injection
> **Version:** v1.0 (2026-08-09) | **Evaluators:** Qwen, ChatGPT, Kimi, Claude, Maxwell V2
> **Input files:** S2 checkpoint, S4 smoke test report, S5 verified output, existing golden set

---

## ROUNDTABLE PROTOCOL

Each LLM evaluator receives the same inputs and answers the same questions independently.
After individual evaluation, cross-examine disagreements to produce a consensus ranking.

### Input Files (attach to each evaluator):

1. **`knowledge pipeline/stage4_merge/latest/SMOKE_TEST_REPORT.md`**
   — 12 FBs with full CRIBS enrichment + classification. This is the PRIMARY evaluation target.

2. **`config/golden/stage2_fewshot_convergent.yaml`**
   — 27 existing golden examples (18 positive, 9 negative). Use as BASELINE for quality comparison.

3. **`knowledge pipeline/stage5_verify/latest/checkpoint.jsonl`**
   — S5 verification output: NLI scores, PASS/QUARANTINE status, epistemic_status.

---

## EVALUATION QUESTIONS

### Section A: Positive Golden Candidates (score each 1-10)

For each of the 3 PASS FBs (Opportunity Solution Tree Framework, Probabilistic Token Selection, Speculative Design As Social Critique):

| Criterion | Weight | Question |
|-----------|--------|----------|
| **A1. Principle Quality** | 25% | Is this a genuine PRINCIPLE (answers WHY/WHEN, not just HOW)? Does it transcend its source domain? |
| **A2. Mechanism Depth** | 20% | Does the mechanism explain the causal chain, not just restate the definition? |
| **A3. Boundary Clarity** | 15% | Does it define when the principle FAILS with specific conditions? |
| **A4. Application Actionability** | 15% | Can a practitioner read the application and know what to do in 30 seconds? (v1 T3 test) |
| **A5. Evidence Grounding** | 15% | Do the evidence passages actually support the claims? Is NLI score consistent with your assessment? |
| **A6. Classification Accuracy** | 10% | Is the discipline correct? Are domains appropriate? Is depth (universal/domain/specialized) accurate? |

### Section B: Negative Golden Candidates (score each 1-10 for "should be rejected")

For the 9 QUARANTINE FBs:

| Criterion | Weight | Question |
|-----------|--------|----------|
| **B1. Fatal Flaw** | 30% | Is there a clear reason this FB should fail? (vague mechanism, no evidence, too narrow) |
| **B2. Fix Potential** | 20% | Could this FB be fixed with better evidence or clearer mechanism? Or is the concept fundamentally flawed? |
| **B3. Classification Error** | 20% | Was the FB quarantined for the RIGHT reason? Or is the NLI/quarantine wrong? |
| **B4. Golden Utility** | 30% | Would this FB make a GOOD negative example? (teaches the model what NOT to produce) |

### Section C: Gap Analysis

| Question |
|----------|
| **C1.** What domains/disciplines are UNDERREPRESENTED in the current 27 golden examples? |
| **C2.** Which of the 12 smoke test FBs would fill those gaps? |
| **C3.** Are there any FB structures missing from golden examples? (e.g., single-source, cross-domain, diagnostic-only) |
| **C4.** Does the actionability field (Fix 0.1: null-able application) change what makes a good golden example? |

### Section D: Pipeline Calibration

| Question |
|----------|
| **D1.** Are the NLI thresholds (≥0.8 auto-PASS, ≥0.8 contra = FAIL) calibrated correctly based on these 12 FBs? |
| **D2.** Would any of the 9 QUARANTINE FBs pass with different thresholds? Should they? |
| **D3.** Is the classification (S4) producing better/worse results than the existing golden set's expected classifications? |

---

## CONSENSUS OUTPUT FORMAT

After individual evaluation, produce a consensus table:

```yaml
positive_candidates:
  - fb_name: "Opportunity Solution Tree Framework"
    consensus_score: X.X
    verdict: ACCEPT / NEEDS_WORK / REJECT
    rationale: "..."

  - fb_name: "Probabilistic Token Selection"
    consensus_score: X.X
    verdict: ACCEPT / NEEDS_WORK / REJECT
    rationale: "..."

  - fb_name: "Speculative Design As Social Critique"
    consensus_score: X.X
    verdict: ACCEPT / NEEDS_WORK / REJECT
    rationale: "..."

negative_candidates:
  - fb_name: "Distributed Knowledge Architecture"
    negative_utility: X.X
    flaw_type: "citation_echo / vague_mechanism / too_narrow / overfitted"
    verdict: KEEP_AS_NEGATIVE / FIXABLE / DISCARD
    rationale: "..."

gap_recommendations:
  - domain: "..."
    missing_example_type: "..."
    candidate_from_smoke: "..."

threshold_recommendations:
  nli_entailment: X.X  # current: 0.8
  nli_contradiction: X.X  # current: 0.8
  borp_min_sources: X  # current: 2
```

---

## BASELINE: Current Golden Set Composition

| Type | Count | Domains Covered |
|------|-------|----------------|
| Convergent positives | 18 | pricing, behavioral economics, decision-making, UX, coding, strategy |
| Hard negatives | 9 | single-source rejection, platitude detection, false convergence, citation echo |
| Total | 27 | ~12 domains |

---

## SMOKE TEST DIVERSITY: 12 FBs from 13 Books

| FB | Depth | Discipline | Status | Potential Use |
|----|-------|-----------|--------|---------------|
| Distributed Knowledge Architecture | universal | information science | QUARANTINE | Negative: citation echo (54 books) |
| Opportunity Solution Tree Framework | universal | emerging | **PASS** | **Positive: structured framework** |
| Probabilistic Token Selection | domain | machine learning | **PASS** | **Positive: technical mechanism** |
| Embedding Dimensionality Tradeoff | universal | machine learning | QUARANTINE | Negative: generic mechanism |
| Speculative Design As Social Critique | domain | cultural design | **PASS** | **Positive: arts+policy cross-domain** |
| Speculative Design Critique | domain | emerging | QUARANTINE | Negative: too few sources (2) |
| Peircean Sign Classification | universal | semiotics | QUARANTINE | Borderline: strong mechanism, weak evidence |
| Synchronic Vs Diachronic Analysis | specialized | linguistics | QUARANTINE | Borderline: specialized but well-structured |
| Expressive Typography Evolution | universal | emerging | QUARANTINE | Negative: subjective domain |
| Strategic Visual Messaging | universal | communication theory | QUARANTINE | Borderline: good structure, weak evidence |
| Modular System Design | universal | software engineering | QUARANTINE | Borderline: universal principle, thin evidence |
| Identity-driven Decision Making | universal | psychology | QUARANTINE | Borderline: strong mechanism, weak NLI |

---

## INSTRUCTIONS FOR EACH EVALUATOR

1. Read the SMOKE_TEST_REPORT.md carefully — focus on mechanism/boundary/consequence/evidence quality
2. Compare against existing golden examples in stage2_fewshot_convergent.yaml
3. Score each FB on the criteria above (1-10 scale)
4. Flag any FB you believe is BETTER than existing golden examples
5. Identify structural patterns in QUARANTINE FBs that could be fixed
6. Return your evaluation in the consensus output format

**Temperature:** 0.0 (deterministic evaluation)
**Role:** You are an expert knowledge engineer auditing a sovereign RAG pipeline.
**Constraint:** Judge based on principle quality, not source popularity. A principle from 2 books can be better than one from 50.
