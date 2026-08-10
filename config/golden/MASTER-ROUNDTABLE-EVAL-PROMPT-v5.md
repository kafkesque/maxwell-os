# Master Roundtable Evaluation Prompt — v5.0
## Golden Set DSPy Fine-Tuning Readiness Audit

**Authority:** D2226 — Post-fix golden set v4.2 (60 examples, 37 pos + 23 neg)
**Audience:** S-tier senior RAG engineers (LLM evaluators)
**Purpose:** Evaluate whether this golden set is ready for DSPy fine-tuning before committing to the Maxwell OS S2 extraction pipeline.
**Date:** 2026-08-10

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
S5: Verify (DeBERTa NLI + Gemma-4-E4B cross-family deep check)
S6: Commit (SQLite + Parquet export)
```

### S2 Extraction Task (what DSPy will learn):
Given 2-4 source segments from different books, determine:
1. **Is this convergent?** Do multiple independent sources describe the same causal mechanism?
2. **Extract the FB**: name, definition, mechanism, boundary, consequence, evidence_passages
3. **Reject if**: single-source, platitude, false convergence (topical overlap without shared mechanism), citation echo (same author, same platitude across sources), taxonomy (not causal), tautology, speculation

### S2 Current Implementation:
- Model: Qwen3-Coder-30B-A3B-MLX-4bit (OMLX)
- Uses few-shot prompting from golden set `stage2_fewshot_convergent.yaml`
- temp=0.0 for determinism
- Generator ≠ Verifier rule: S2 (Qwen/Alibaba) ≠ S5 (Gemma/Google)

---

## THE GOLDEN SET: 60 Examples (v4.2)

**File:** `config/golden/stage2_fewshot_convergent.yaml`

### Composition:
| Category | Count | Coverage |
|----------|-------|----------|
| Convergent positives | 37 | Multi-source causal convergence |
| Hard negatives | 23 | 15 distinct failure modes |
| **Total** | **60** | |

### Extraction Type Distribution:
| Type | Count | % | Target |
|------|-------|---|--------|
| `causal_mechanism` | 25 | 68% | ≤60% |
| `descriptive_model` | 4 | 11% | 3+ ✓ |
| `normative_heuristic` | 4 | 11% | 3+ ✓ |
| `empirical_pattern` | 4 | 11% | 3+ ✓ |

### Depth Distribution:
| Depth | Count | Description |
|-------|-------|-------------|
| `cross-domain` | 20 | Bridges 2+ distinct disciplines |
| `domain` | 11 | Operates within one field |
| `universal` | 5 | Applies to all systems (physicist-chef-poet test) |
| `specialized` | 1 | Narrow sub-technique, tool-bound |

### Domain Coverage (39 unique domains):
Behavioral economics, cognitive psychology, AI alignment, education, computer graphics, medicine, law, software engineering, network science, decision theory, systems thinking, interaction design, brand strategy, economics, game theory, philosophy of language, macroeconomics, positive psychology, self-help, technology, epistemology, innovation studies, evolutionary anthropology, complex systems, strategic management, social networks, typography, and more.

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
15. Same-author echo (NEG-020)

---

## FIXES APPLIED (D2226 — 2026-08-10)

Before this audit, a cross-evaluation by Kimi, Qwen, and Claude identified 6 issues. ALL SIX are now fixed:

| # | Fix | Severity | File |
|---|------|----------|------|
| 1 | `build_classify_prompt()` now receives mechanism + boundary (was input-starved: only name+definition) | P0 | `stage4_merge.py` |
| 2 | NLI hardcoded thresholds (0.8) → config-driven (`nli_pass_threshold: 0.6`) | P0 | `stage5_verify.py` |
| 3 | Merged S4 CRIBS+Classify single call wired into `run_stage4()` (opt-in: `MAXWELL_MERGED_S4=1`) | P1 | `stage4_merge.py` |
| 4 | CONV-006: broken 1:N structure → complete single FB (Default Inertia Effect) | P0 | `stage2_fewshot_convergent.yaml` |
| 5 | CONV-012/017 depth: universal → cross-domain (fails physicist-chef-poet test) | P1 | `stage2_fewshot_convergent.yaml` |
| 6 | Extraction type diversity: +10 examples (3 descriptive, 3 normative, 3 empirical, 1 specialized) | P1 | `stage2_fewshot_convergent.yaml` |

### Live Test Results (Merged S4 Call — 20 FBs):
- 100% success rate (0 errors)
- Avg latency: 5.95s per FB
- **Depth distribution: 95% cross-domain, 5% domain, 0% universal, 0% specialized**
- Phi-4-mini (3.8B) over-assigns `cross-domain` — model is underpowered for semantic depth discrimination
- Merged call works mechanically but produces poor depth signal

---

## EVALUATION TASK

You are an S-tier senior RAG engineer evaluating whether this golden set is ready for DSPy fine-tuning of the S2 extraction stage.

### QUESTION 1: Structural Integrity [P0]

Examine `config/golden/stage2_fewshot_convergent.yaml`. For EVERY example (all 60):

a) Do all 37 positives have: `name`, `definition`, `mechanism`, `boundary`, `consequence`, `evidence_passages`, `extraction_type`, `depth`, `discipline`?
b) Are there any YAML syntax errors (duplicate keys, malformed strings, unescaped characters)?
c) Do source segment texts match evidence passages verbatim? Flag any mismatches.
d) Do `expected_fb` field values contradict `rationale` text? (e.g., rationale says "specialized" but field says "domain")
e) Is there any example whose `expected_fb` is clearly wrong (wrong depth, wrong extraction type, missing critical fields)?

### QUESTION 2: Depth Classification Accuracy [P1]

Apply the Maxwell OS depth ontology to EVERY positive example. For each, answer: is the assigned `depth` correct?

**Depth ontology:**
- `universal` = mechanism applies to ALL systems (physics, biology, social, cognitive). Test: Would a physicist, a chef, AND a poet each encounter this mechanism in their own domain WITHOUT borrowing domain-specific vocabulary?
- `cross-domain` = mechanism explicitly bridges 2+ DISTINCT disciplines via shared causal structure. Must reveal a structural isomorphism between domains.
- `domain` = mechanism applies within one field or cluster of related fields. Requires domain-specific context. If you strip ALL jargon, does the mechanism become meaningless?
- `specialized` = narrow sub-technique, tool-specific skill, or niche methodology within a sub-field. Would most practitioners IN the parent domain understand it?

**Flag ALL misclassifications.** Identify whether errors are systematic (e.g., all behavioral economics → cross-domain, all design → domain) or random.

### QUESTION 3: Extraction Type Balance [P1]

The golden set currently has: 25 causal (68%), 4 descriptive (11%), 4 normative (11%), 4 empirical (11%).

a) Is 4 examples per non-causal type sufficient for DSPy to learn the distinction? Or will the model default to `causal_mechanism` for ambiguous cases?
b) Examine CONV-031 through CONV-040 (the 10 new D2226 examples). Are their extraction types CORRECTLY assigned? Flag any misclassifications.
c) What additional examples would you add to reach DSPy-optimal balance?

### QUESTION 4: Negative Set Quality [P1]

a) Do all 23 negatives teach GENUINELY DISTINCT rejection patterns? Or are there near-duplicates that waste training signal?
b) Are any negatives CONTAMINATED — teaching rejection of what should be accepted? (This was the original NEG-007/010 problem)
c) Are there failure modes MISSING from the negative set? What would a DSPy model trained on these 23 negatives fail to reject?
d) Is the negative-to-positive ratio (23:37 = 0.62:1) appropriate for a quality-focused extraction pipeline where false positives are more costly than false negatives?

### QUESTION 5: Domain and Discipline Completeness [P2]

a) What domains are missing that would cause systematic extraction failures? (Consider: chemistry, neuroscience, linguistics, architecture, cybersecurity, ethics)
b) Are disciplines correctly assigned? Check: is every discipline a REAL, specific academic field (not "emerging", not generic)?
c) Is there author/source over-concentration? (Kahneman appears 5+ times, Clear 4+ times, Taleb 4+ times — does this risk overfitting to writing style?)

### QUESTION 6: DSPy Fine-Tuning Readiness — Ultimate Verdict [P0]

Based on ALL above:
a) Is this golden set READY, BORDERLINE, or NOT READY for DSPy fine-tuning?
b) If BORDERLINE or NOT READY: exactly what must be fixed before proceeding?
c) If READY: what monitoring metrics should be tracked during the first fine-tuning run?
d) Recommend: minimum examples needed, ideal train/test split, and validation strategy.

### QUESTION 7: S2 Model Selection [P1]

Given the hardware (M1 Max, 64 GB, ~24 GB available for models):
a) Is Qwen3-Coder-30B-A3B-MLX-4bit the correct choice for S2 extraction? What alternatives exist?
b) The S4 classifier (Phi-4-mini-3.8B) over-assigned `cross-domain` to 95% of FBs in live testing. What model should replace it for depth classification?
c) Is the Generator ≠ Verifier rule (R5: S2=Qwen, S4=Phi, S5=Gemma — three different families) correctly maintained?

### QUESTION 8: Pipeline Architecture [P2]

a) The merged S4 call (CRIBS+Classify in one Phi-4-mini call) is built but opt-in. Should it become the default? What model should it use?
b) The NLI thresholds are now config-driven (`nli_pass_threshold: 0.6` from `pipeline_config.yaml`). Are these thresholds optimal for DeBERTa-v3-base-mnli on this task?
c) Is there any architectural gap between what the golden set teaches and what the pipeline actually executes?

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

depth_accuracy:
  misclassifications: []
  systematic_bias: "description or none"

extraction_type_balance:
  assessment: "adequate|borderline|insufficient"
  causal_pct_ok: true/false
  recommendations: []

negative_set_quality:
  distinct_patterns: 0
  contaminants: []
  missing_patterns: []
  ratio_assessment: "appropriate|too_high|too_low"

dspy_readiness:
  verdict: "READY|BORDERLINE|NOT_READY"
  minimum_viable: 0  # minimum examples needed
  blocking_issues: []
  recommended_actions: []

model_selection:
  s2_recommendation: "model_name"
  s4_classifier_recommendation: "model_name"
  r5_compliant: true/false

critical_blockers: []
confidence: 0.0  # 0.0-1.0 in your assessment
```

---

## FILES FOR REFERENCE

Attach these files to the evaluation:
1. `config/golden/stage2_fewshot_convergent.yaml` — The 60-example golden set (primary evaluation target)
2. `config/golden/stage2_fewshot_trimmed_12.yaml` — Reduced 12-example set for efficient few-shot
3. `pipeline/stage4_merge.py` — S4 merge pipeline (depth classifier at `build_classify_prompt`, merged call wiring)
4. `pipeline/stage5_verify.py` — S5 verification (NLI thresholds, mechanism pre-filter)
5. `pipeline/schemas.py` — Schema definitions (DEPTH_LITERAL, EXTRACTION_TYPE_LITERAL)
6. `config/pipeline_config.yaml` — Pipeline configuration (NLI thresholds, model assignments)

---

## IMPORTANT NOTES FOR EVALUATORS

1. **Be rigorously critical.** The golden set's purpose is to train a model that extracts principles from 969 books. False positives (extracting platitudes as principles) are more costly than false negatives. The negative set quality is AS IMPORTANT as the positive set.

2. **Challenge the depth ontology.** The physicist-chef-poet test for `universal` is strict. Most principles are `domain` or `cross-domain`. If you see `universal` assigned, verify it TRULY applies to physics, cooking, AND poetry without domain borrowing.

3. **Check verbatim evidence.** The `evidence_passages` must match the `cluster_segments` EXACTLY (modulo whitespace normalization). Flag any condensation, paraphrasing, or fabrication.

4. **Verify mechanism ≠ definition.** In tautological negatives, the "mechanism" restates the definition in different words. In valid positives, the mechanism explains a causal chain that the definition names. Check every positive.

5. **Pragmatic, not pedantic.** The golden set will train a real model on real hardware under real constraints. Recommendations must be actionable within Maxwell OS's architecture and hardware limits (M1 Max, 64 GB, MLX, $0 marginal cost).
