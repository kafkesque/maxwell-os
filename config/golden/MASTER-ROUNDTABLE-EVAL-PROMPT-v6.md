# Master Roundtable Evaluation Prompt — v6.0
## Golden Set DSPy Fine-Tuning Readiness Audit

**Authority:** D2234 — Post quality-blocker golden set v4.3 (70 examples, 72 FBs, EP:12, NH:12, DM:9)
**Audience:** S-tier senior RAG engineers (LLM evaluators)
**Purpose:** Evaluate whether this golden set is ready for DSPy fine-tuning before committing to the Maxwell OS S2 extraction pipeline.
**Date:** 2026-08-10

---

## ⚠️ D2234 CHANGELOG (2026-08-10) — What changed since v5.0

This prompt has been updated after the quality blocker sprint. D2232 changes are included below for completeness.

### D2234: Author Cap & Extraction Type Expansion

| Fix | Detail |
|-----|--------|
| **Author cap** | Kahneman 7→3, Taleb 5→3, James Clear 4→3, Gladwell 4→3. All authors ≤3. Done via surgical cluster_segment replacement (8 examples edited, none deleted). |
| **Reclassifications** | 7 FBs reclassified from `causal_mechanism`: 3→`empirical_pattern` (CONV-011, CONV-015, CONV-021), 3→`normative_heuristic` (CONV-013, CONV-016, CONV-040), 1→`descriptive_model` (CONV-028). |
| **New examples** | 10 new FBs targeting under-represented types: CONV-041 (Dunning-Kruger, EP), CONV-042 (Zipf's Law, EP), CONV-043 (Group Development, DM), CONV-044 (Johari Window, DM), CONV-045 (Eisenhower Matrix, NH), CONV-046 (Five Whys, NH), CONV-047 (Parkinson's Law, NH), CONV-048 (Rubber Duck Debugging, NH), CONV-049 (Maslow's Hierarchy, DM), CONV-050 (Hanlon's Razor, NH) |
| **Source diversity** | New authors: Barabási, Dobelli, Gary Klein, Nate Silver, Tony Robbins, Pinker, Chabris/Simons, Konnikova, Gleick, Lencioni, Coyle, Goleman, Pink, Harari, Ferriss, Newport, Patterson, Ries, Meadows |

### D2232: Post-Cross-Examination Audit (carried forward)

| Fix | Detail |
|-----|--------|
| S4 field strip | All positives: `application`, `elaboration`, `procedural_skill`, etc. removed from `expected_fb`. Golden set is **S2-only schema**. |
| Evidence verbatim | All evidence passages now match `cluster_segments` exactly (178/178, 100%). Audit tool at `tools/audit_evidence_passages.py`. |
| CONV-037 split | "Cognitive Capacity Ceiling" split into **2 FBs**: Dunbar's Number + Availability Heuristic (1:N example, `is_convergent=false`). |
| CONV-035 reclassified | `is_convergent=false` — complementary mechanisms, NOT convergent. |
| CONV-039 split | Split into 2 FBs: Incentive Frame Displacement + Planning Fallacy. |
| NEG-006/009 fixed | Contaminated negatives converted to bounded positives (Spaced Retrieval Effect, Three-Level Product Management). |
| Depth corrections | CONV-014, CONV-021, CONV-032: `universal→cross-domain`. 7 total depth fixes. |
| C12 thresholds | 6 hardcoded thresholds moved to `pipeline_config.yaml`. |
| sqlite-vec | `float[1024]→float[512]` dimension fix. |
| GoldenFB schema | `extraction_type: str` field added to Pydantic. |
| NLI config | ModernBERT primary / DeBERTa fallback. Fallback defaults fixed. |
| Versions | `taxonomy_version: v5.1` across all files; golden set `meta.version: 4.3`. |
| `format_golden_fewshot()` | Now injects `extraction_type` and `depth` into few-shot output. |
| S2 system prompt | Added `descriptive_model` definition. |

**Updated metrics (post-D2234):**
- Convergent positives: 57 (was 37)
- Total FBs: 72 (was 38)
- Extraction types: causal_mechanism=39, empirical_pattern=12, normative_heuristic=12, descriptive_model=9
- Depths: cross-domain (majority), domain, universal=2, specialized=1
- Golden set: 70 examples (was 60)
- Author concentration: ALL authors ≤3 ✅
- Evidence: 100% verbatim (178/178 passages)
- golden_validate.py: PASS
- audit_evidence_passages.py: PASS (100%)

**Evaluator note:** The `is_convergent=false` examples (CONV-035, CONV-037, CONV-039) are INTENTIONAL — they teach S2 that multi-source clusters may require splitting. The `descriptive_model` examples teach that taxonomies and classification systems are valid FBs distinct from causal mechanisms. Both DM at 9 and NH at 12 are within target range.

---

## CONTEXT: Maxwell OS v3.0 Knowledge Extraction Pipeline

Maxwell OS is a sovereign, local-first knowledge extraction pipeline that converts 969 books (EPUB/PDF → MD → segments → clusters → Foundation Blocks). It runs entirely on Apple M1 Max (64 GB, MLX 0.32.0). $0 marginal cost. No vendor lock-in.

### Pipeline Architecture (8 stages, Stage 3 removed):
```
S0: Convert (EPUB/PDF → MD)
S0.5: Extract metadata (author/title)
S1: Chunk (MD → segments + SHA-256 dedup)
S1.3: Prefilter (regex)
S1.5: Embed + Cluster (bge-m3 512d + FAISS cosine + source diversity)
S2: Extract (LLM: clusters → convergent FBs) ← DSPy fine-tuning TARGET
S4: Merge (CRIBS enrichment + classification: discipline, domains, depth)
S5: Verify (DeBERTa NLI + Gemma cross-family deep check)
S6: Commit (SQLite + Parquet export)
```

### S2 Extraction Task (what DSPy will learn):
Given 2-4 source segments from different books, determine:
1. **Is this convergent?** Do multiple independent sources describe the same causal mechanism?
2. **Extract the FB**: name, definition, mechanism, boundary, consequence, evidence_passages, extraction_type, depth
3. **Reject if**: single-source, platitude, false convergence (topical overlap without shared mechanism), citation echo (same author, same platitude across sources), taxonomy (not causal), tautology, speculation

### S2 Current Implementation:
- Model: Qwen3-Coder-30B-A3B-MLX-4bit (OMLX)
- Uses few-shot prompting from golden set `stage2_fewshot_convergent.yaml`
- temp=0.0 for determinism
- Generator ≠ Verifier rule: S2 (Qwen/Alibaba) ≠ S5 (Gemma/Google)

---

## THE GOLDEN SET: 70 Examples (v4.3)

**File:** `config/golden/stage2_fewshot_convergent.yaml`

### Composition:
| Category | Count | Coverage |
|----------|-------|----------|
| Convergent positives | 57 | Multi-source causal convergence |
| Hard negatives | 13 | 15 distinct failure modes |
| **Total** | **70** | |

### Extraction Type Distribution:
| Type | Count | % | Target |
|------|-------|---|--------|
| `causal_mechanism` | 39 | 54% | ≤60% ✓ |
| `empirical_pattern` | 12 | 17% | 12-15 ✓ |
| `normative_heuristic` | 12 | 17% | 12-15 ✓ |
| `descriptive_model` | 9 | 13% | 12-15 (close) |

### Author Concentration (all ≤3):
| Author | Count | Status |
|--------|-------|--------|
| Kahneman | 3 | ✓ |
| Taleb | 3 | ✓ |
| James Clear | 3 | ✓ |
| Gladwell | 3 | ✓ |
| Ariely, Duhigg, Thaler, Dan Heath | 3 each | ✓ |
| All others | ≤2 | ✓ |

### Depth Distribution:
| Depth | Count | Description |
|-------|-------|-------------|
| `cross-domain` | ~40 | Bridges 2+ distinct disciplines |
| `domain` | ~25 | Operates within one field |
| `universal` | 2 | Passes physicist-chef-poet test |
| `specialized` | 1 | Narrow sub-technique, tool-bound |

### Domain Coverage (45+ unique domains):
Behavioral economics, cognitive psychology, AI alignment, education, computer graphics, medicine, law, software engineering, network science, decision theory, systems thinking, interaction design, brand strategy, economics, game theory, philosophy of language, macroeconomics, positive psychology, self-help, technology, epistemology, innovation studies, evolutionary anthropology, complex systems, strategic management, social networks, typography, linguistics, organizational behavior, productivity, problem solving, interpersonal communication, time management, debugging methodology, motivation theory, and more.

### Negative Failure Modes Covered (15 distinct):
1. Single-source rejection (NEG-CONV-001)
2. Platitude detection (NEG-CONV-002)
3. False convergence — topical overlap, no shared mechanism (NEG-CONV-003)
4. Citation echo — multi-source same platitude (NEG-007)
5. Taxonomy, not principle (NEG-008)
6. Tautology detection (NEG-001)
7. Depth over-elevation (NEG-009)
8. Jargon echo — same word, different mechanism (NEG-005)
9. Engineering tradeoff, not principle (NEG-011)
10. Historical observation, not principle (NEG-012)
11. Correlation ≠ causation (NEG-013)
12. Mechanism disagreement — same outcome, different causes (NEG-014)
13. Domain best practice, not principle (NEG-015)
14. Non-falsifiable claim (NEG-018)
15. Same-author echo (NEG-020 — Pinker trilogy)

---

## EVALUATION TASK

You are an S-tier senior RAG engineer evaluating whether this golden set is ready for DSPy fine-tuning of the S2 extraction stage.

### QUESTION 1: Structural Integrity [P0]

Examine `config/golden/stage2_fewshot_convergent.yaml`. For EVERY example (all 70):

a) Do all 57 positives have: `name`, `definition`, `mechanism`, `boundary`, `consequence`, `evidence_passages`, `extraction_type`, `depth`, `discipline`?
b) Are there any YAML syntax errors (duplicate keys, malformed strings, unescaped characters)?
c) Do source segment texts match evidence passages verbatim? (178/178 verified by `audit_evidence_passages.py` — re-verify any that look suspicious.)
d) Do `expected_fb` field values contradict `rationale` text? (e.g., rationale says "specialized" but field says "domain")
e) Is there any example whose `expected_fb` is clearly wrong (wrong depth, wrong extraction type, missing critical fields)?
f) **NEW (D2234):** Do all reclassified FBs (CONV-011, CONV-013, CONV-015, CONV-016, CONV-021, CONV-028, CONV-040) have extraction_types consistent with their content?
g) **NEW (D2234):** Do the 10 new examples (CONV-041–050) meet the same quality bar as existing examples?

### QUESTION 2: Depth Classification Accuracy [P1]

Apply the Maxwell OS depth ontology to EVERY positive example. For each, answer: is the assigned `depth` correct?

**Depth ontology:**
- `universal` = mechanism applies to ALL systems (physics, biology, social, cognitive). Test: Would a physicist, a chef, AND a poet each encounter this mechanism in their own domain WITHOUT borrowing domain-specific vocabulary?
- `cross-domain` = mechanism explicitly bridges 2+ DISTINCT disciplines via shared causal structure. Must reveal a structural isomorphism between domains.
- `domain` = mechanism applies within one field or cluster of related fields. Requires domain-specific context. If you strip ALL jargon, does the mechanism become meaningless?
- `specialized` = narrow sub-technique, tool-specific skill, or niche methodology within a sub-field. Would most practitioners IN the parent domain understand it?

**Flag ALL misclassifications.** Identify whether errors are systematic (e.g., all behavioral economics → cross-domain, all design → domain) or random.

### QUESTION 3: Extraction Type Balance [P1]

The golden set now has: 39 causal (54%), 12 empirical (17%), 12 normative (17%), 9 descriptive (13%).

a) Is 12 examples each for empirical and normative sufficient for DSPy to learn the distinction? What about descriptive at 9?
b) **NEW (D2234):** Examine the 10 new examples (CONV-041–050). Are their extraction types CORRECTLY assigned?
c) **NEW (D2234):** Examine the 7 reclassified examples. Were the reclassifications correct?
d) What additional examples would bring descriptive_model to 12+?

### QUESTION 4: Negative Set Quality [P1]

The golden set has 13 negatives covering 15 distinct failure modes (post D2226/D2232 cleanups).

a) Do all 13 negatives teach GENUINELY DISTINCT rejection patterns?
b) Are any negatives CONTAMINATED — teaching rejection of what should be accepted?
c) Are there failure modes MISSING from the negative set?
d) Is the negative-to-positive ratio (13:57 = 0.23:1) appropriate? Note: this drifted from the pre-D2232 ratio of 23:37 (0.62:1) because we added 20 positives and removed/repurposed 10 negatives. Is this a problem for DSPy?

### QUESTION 5: Domain and Discipline Completeness [P2]

a) What domains are missing that would cause systematic extraction failures?
b) Are disciplines correctly assigned?
c) **NEW (D2234):** Author concentration is now capped at ≤3. Is the source diversity sufficient?

### QUESTION 6: DSPy Fine-Tuning Readiness — Ultimate Verdict [P0]

Based on ALL above:
a) Is this golden set READY, BORDERLINE, or NOT READY for DSPy fine-tuning?
b) If BORDERLINE or NOT READY: exactly what must be fixed before proceeding?
c) If READY: what monitoring metrics should be tracked during the first fine-tuning run?
d) Recommend: minimum examples needed, ideal train/test split, and validation strategy.
e) **NEW (D2234):** Now that the golden set is 70 examples with 72 FBs, is the size adequate for a DSPy pilot? Or does the 13:57 negative:positive ratio create issues?

### QUESTION 7: S2 Model Selection [P1]

Given the hardware (M1 Max, 64 GB, ~24 GB available for models):
a) Is Qwen3-Coder-30B-A3B-MLX-4bit the correct choice for S2 extraction? What alternatives exist via llmfit?
b) The S4 classifier over-assigned `cross-domain` to 95% of FBs in live testing with Phi-4-mini. What model should replace it? Gemma-4-31B-it-MLX-4bit is available via llmfit.
c) Is the Generator ≠ Verifier rule (R5) correctly maintained?

### QUESTION 8: Pipeline Architecture [P2]

a) The merged S4 call (CRIBS+Classify in one call) is opt-in. Should it become default?
b) NLI thresholds: `nli_pass_threshold: 0.6` from config. Optimal for DeBERTa-v3-base-mnli?
c) Any architectural gap between what the golden set teaches and what the pipeline executes?

---

## VERDICT FORMAT

Return a YAML verdict:

```yaml
auditor: "model_name"
date: "2026-08-10"
overall_verdict: "READY|BORDERLINE|NOT_READY"

structural_integrity:
  score: "X/10"
  errors_found: []
  verifications_passed: 0
  new_examples_quality: "assessment"

depth_accuracy:
  misclassifications: []
  systematic_bias: "description or none"

extraction_type_balance:
  assessment: "adequate|borderline|insufficient"
  causal_pct_ok: true/false
  reclassifications_correct: true/false
  recommendations: []

negative_set_quality:
  distinct_patterns: 0
  contaminants: []
  missing_patterns: []
  ratio_assessment: "appropriate|too_low|too_high"
  ratio_concern: "description"

dspy_readiness:
  verdict: "READY|BORDERLINE|NOT_READY"
  minimum_viable: 0
  blocking_issues: []
  recommended_actions: []
  pilot_ready: true/false

model_selection:
  s2_recommendation: "model_name"
  s4_classifier_recommendation: "model_name"
  r5_compliant: true/false

critical_blockers: []
confidence: 0.0
```

---

## FILES FOR REFERENCE

Attach these files to the evaluation:
1. `config/golden/stage2_fewshot_convergent.yaml` — The 70-example golden set (v4.3, primary evaluation target)
2. `config/golden/stage2_fewshot_trimmed_12.yaml` — Reduced 12-example set for efficient few-shot
3. `pipeline/stage2_extract.py` — S2 extraction (system prompt, `format_golden_fewshot()`, convergence routing)
4. `pipeline/stage4_merge.py` — S4 merge pipeline (depth classifier, merged call)
5. `pipeline/stage5_verify.py` — S5 verification (NLI thresholds, mechanism pre-filter)
6. `pipeline/schemas.py` — Schema definitions (DEPTH_LITERAL, EXTRACTION_TYPE_LITERAL, GoldenFB)
7. `config/pipeline_config.yaml` — Pipeline configuration (NLI thresholds, model assignments, C12 thresholds)
8. `tools/audit_evidence_passages.py` — Evidence verbatim audit tool
9. `pipeline/golden_validate.py` — Golden set structural validator

---

## IMPORTANT NOTES FOR EVALUATORS

1. **Be rigorously critical.** The golden set's purpose is to train a model that extracts principles from 969 books. False positives (extracting platitudes as principles) are more costly than false negatives.

2. **Challenge the depth ontology.** The physicist-chef-poet test for `universal` is strict. Most principles are `domain` or `cross-domain`.

3. **Check verbatim evidence.** `audit_evidence_passages.py` already verified 178/178 (100%). But re-check any that look suspicious — trust but verify.

4. **Verify mechanism ≠ definition.** In tautological negatives, the "mechanism" restates the definition. In valid positives, the mechanism explains a causal chain.

5. **Evaluate the negative:positive ratio.** 13:57 = 0.23:1 is lower than the original 0.62:1. Is this sufficient for DSPy to learn rejection? Should we add more negatives?

6. **New examples (CONV-041-050).** These were generated programmatically. Evaluate whether they meet the same quality bar as hand-crafted examples.

7. **Pragmatic, not pedantic.** Recommendations must be actionable within Maxwell OS's architecture and hardware limits (M1 Max, 64 GB, MLX, $0 marginal cost).
