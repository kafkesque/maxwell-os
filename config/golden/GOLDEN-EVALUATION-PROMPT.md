# Maxwell OS — Golden Set Master Evaluation Prompt
> **Version:** v2.0 (D2204)
> **Status:** REQUIRES LLM EVALUATION before calibration
> **Golden set file:** `config/golden/stage2_fewshot_convergent.yaml` (25 examples)

---

## CONTEXT FOR THE EVALUATOR

You are an expert RAG/knowledge-engineering auditor. Maxwell OS is a sovereign,
local-first knowledge extraction pipeline that converts books into **Foundation
Blocks (FBs)** — verified, convergent, executable knowledge units. The pipeline:

1. Clusters text segments from multiple books by semantic similarity
2. Extracts candidate FBs from each cluster
3. Verifies via BORP (≥2 independent sources) + cross-model NLI + fail-closed
   checks (D2093)
4. Commits only PASS status FBs to the canonical store

The **golden set** at `config/golden/stage2_fewshot_convergent.yaml` is the
few-shot training/evaluation corpus for Stage 2 (extraction). It teaches the
extraction model what a *correct* convergent FB looks like. **It is the
calibration ground truth for the entire pipeline.**

Your job: audit the golden set for correctness, completeness, consistency, and
structural integrity. Find every flaw before the pipeline is calibrated on it.

---

## THE FB SCHEMA (what a correct expected_fb contains)

Each `expected_fb` MUST contain these fields with these properties:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ | Short FB title (3-6 words, noun phrase) |
| `definition` | ✅ | 1-3 sentences: what the principle IS |
| `mechanism` | ✅ | HOW it works — the causal chain, NOT the evidence |
| `consequence` | ✅ | WHAT happens when applied (predictive, falsifiable) |
| `boundary` | ✅ | WHEN it applies / WHEN it fails (at least 3 failure conditions) |
| `evidence_passages` | ✅ | Verbatim quotes from cluster_segments supporting the FB |
| `is_summary` | ✅ | `false` for FBs; `true` for summary-only extractions |
| `route` | ✅ | `"FB"` (extract) or `"SKIP"` (reject) |
| `depth` | ⚠️ | `universal` / `cross-domain` / `domain` / `specialized` |
| `evidence` | ⚠️ | `cited` (has sources) / `axiomatic` (self-evident) |
| `jargon` | ⚠️ | List of technical terms used in the FB |
| `keywords` | ⚠️ | Search/classification keywords |
| `application` | ⚠️ | Where the FB applies (contexts) |
| `elaboration` | ⚠️ | Extended explanation / nuances |
| `prerequisite_fbs` | ⚠️ | FBs that must be known before this one |
| `contradicts_fbs` | ⚠️ | FBs that contradict this one (boundary tension) |
| `related_fbs` | ⚠️ | Related FBs (extensions, neighbors) |
| `procedural_skill` | ⚠️ | Step-by-step actionable procedure (the "executable" part) |
| `failure_mode` | ⚠️ | How the FB fails in practice |

**NOTE:** Fields marked ⚠️ are "nice-to-have" for MOST examples but MUST appear
in at least 3 examples each across the whole set (property variation coverage).

---

## EVALUATION DIMENSIONS

Evaluate the golden set across these 10 dimensions. For each, report:
**VERDICT** (PASS / FAIL / WARN), **EVIDENCE** (specific example IDs), and
**FIX** (concrete correction).

### 1. STRUCTURAL INTEGRITY
- All `expected_fb` fields conform to schema (no typos, no extra junk)
- `evidence_passages` are VERBATIM substrings of `cluster_segments` text
- `is_summary` / `route` are consistent with `is_convergent` / `should_extract`
- No empty required fields (`definition`, `mechanism`, `consequence`, `boundary`)

### 2. CONVERGENCE QUALITY (BORP)
For each `is_convergent: true` example:
- Are the sources GENUINELY INDEPENDENT (different authors, no citation chains)?
- Do the cluster_segments actually SUPPORT the extracted FB?
- Is the convergence REAL (same claim, different evidence) or surface-level
  (same words, different meanings)?
- Would this pass BORP (≥2 independent sources)?

### 3. MECHANISM QUALITY
For each FB:
- Is `mechanism` a CAUSAL explanation, not just restated evidence?
- Does the mechanism explain WHY, not just WHAT?
- Is it specific enough to be tested?

### 4. BOUNDARY QUALITY
For each FB:
- Does `boundary` state ≥3 concrete failure conditions?
- Are the boundaries SPECIFIC (not "doesn't work sometimes")?
- Does the boundary match real-world scope of the principle?

### 5. NEGATIVE QUALITY
For each non-convergent example (NEG-*):
- Is it a DISTINCT rejection category? (single-source / platitude / false
  convergence / citation echo / boundary violation)
- Would the pipeline actually REJECT it?
- Is the `rationale` explaining WHY it's rejected?

### 6. PROPERTY COVERAGE
- Are `prerequisite_fbs`, `contradicts_fbs`, `related_fbs`,
  `procedural_skill`, `failure_mode` each present in ≥3 examples?
- Are `depth`, `evidence`, `jargon`, `keywords`, `application`,
  `elaboration` present in ≥5 examples?
- Is the property distribution BALANCED (not all in one domain)?

### 7. DOMAIN COVERAGE
- Do examples cover ALL 7 domain groups?
  (Visual Practice / Business & Strategy / AI & Computing /
  Digital & Interactive / Illustration & Craft /
  Systems, Semiotics & Knowledge / Computational Art & Code)
- Is each domain group represented by ≥1 example?
- Do disciplines map correctly to domains?

### 8. HARD NEGATIVE EDGE CASES
The set must include (and you must verify) these rejection categories:
- [ ] Single-source non-convergence (1 book, should reject)
- [ ] Platitude / truism (motivational, no mechanism)
- [ ] False convergence (same word, different meaning across books)
- [ ] Citation echo (same author / book cites itself = pseudo-independence)
- [ ] Jargon echo (shared vocabulary ≠ shared claim)
- [ ] Boundary violation (FB claimed universally but only true in narrow scope)

### 9. HALLUCINATION / FACTUAL CHECK
For each example:
- Are the source_books REAL, well-known books?
- Are the attributed ideas CORRECT for those books?
- Are the cluster_segments FAITHFUL to the source (no fabrication)?
- Would a knowledgeable reader recognize each claim as belonging to its source?

### 10. CALIBRATION READINESS
- Is the set ready to serve as few-shot training for Stage 2 extraction?
- Are examples DISTINCT (no near-duplicates)?
- Is the convergent:negative ratio sensible (roughly 3:1 to 4:1)?
- Is the ordering sensible (positives first, negatives distributed)?

---

## OUTPUT FORMAT

Return a structured report:

```
# Golden Set Evaluation — [YOUR NAME]

## Summary
- Total examples: 25
- Overall verdict: READY / NEEDS-FIXES / BROKEN
- Critical flaws: N
- Recommended actions: [...]

## Dimension Results
### 1. Structural Integrity — PASS/FAIL/WARN
...
(one section per dimension 1-10)

## Example-by-Example Findings
| ID | Issue | Severity (CRIT/HIGH/MED/LOW) | Fix |
|----|-------|------------------------------|-----|

## Recommended Calibration Notes
- Threshold adjustments (e.g., NLI entailment threshold, BORP min sources)
- Examples to split / merge / remove
- Properties to strengthen
```

---

## GRADING RUBRIC

| Score | Meaning |
|-------|---------|
| **READY** | 0 critical flaws, ≤2 high, all properties covered, all edge cases present |
| **NEEDS-FIXES** | 1-3 critical flaws OR missing edge case OR property gap |
| **BROKEN** | >3 critical flaws, structural errors, fabricated content |

**Be BRUTAL.** A false-positive in the golden set teaches the pipeline to emit
hallucinated FBs. A false-negative teaches it to reject valid convergence.
Either error propagates to every FB the pipeline ever produces.
