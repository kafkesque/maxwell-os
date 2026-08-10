# LLM Roundtable — Master Prompt
> Evaluate Maxwell OS v3.0 convergent Foundation Blocks for golden few-shot examples and fine-tuning candidates.
> Delegated to: Qwen3-Coder-30B (primary), Gemma-4-E4B (cross-family validation), Phi-4-mini (summarization)
> Run: delegate each model independently, compare outputs, rank by consensus.

---

## ROUNDTABLE PROTOCOL

You are one of three LLM jurors evaluating Foundation Blocks (FBs) extracted from the Maxwell OS v3.0 knowledge pipeline. Your task is to assess FB quality across multiple dimensions and identify:

1. **Golden examples**: FBs suitable as few-shot examples for S2 extraction prompts
2. **Fine-tuning candidates**: FBs that represent the ideal distribution of disciplines, depths, and types
3. **Gate failures**: FBs that should be rejected or flagged

---

## EVALUATION CRITERIA

Rate each FB on 1-5 scale for each dimension:

### 1. Causal Soundness (1-5)
Does the mechanism logically explain WHY the principle works? Is the causal chain coherent?
- 5: Mechanism is tight, falsifiable, non-circular. "X causes Y because Z" is clear and testable.
- 3: Mechanism is plausible but vague, relies on correlation rather than causation.
- 1: Mechanism is circular ("it works because it works"), missing, or contradicts itself.

### 2. Abstraction Quality (1-5)
Is this a genuine convergent principle, not a summary or domain-specific fact?
- 5: Applies across ≥3 domains, names a transferable pattern, not textbook paraphrase.
- 3: Cross-domain but shallow — could be a Wikipedia definition with extra words.
- 1: Domain-specific fact, book summary, or trivial observation.

### 3. Boundary Precision (1-5)
Does the boundary/condition specify WHEN the principle FAILS, not just when it applies?
- 5: Specifies falsifiable failure conditions. "Fails when X exceeds Y threshold."
- 3: Lists application contexts but no clear failure mode.
- 1: Boundary is "applies everywhere" or missing entirely.

### 4. Evidence Grounding (1-5)
Do the cited evidence passages actually support the principle, or is the principle a leap?
- 5: Evidence directly demonstrates the causal mechanism. Multiple books converge.
- 3: Evidence is tangentially related — supports a component but not the full principle.
- 1: Evidence is irrelevant, cherry-picked, or the principle is a non-sequitur from passages.

### 5. Elaboration Depth (1-5)
Does the elaboration add genuine nuance (edge cases, exceptions, implicit assumptions) not covered by definition/mechanism/boundary/consequence?
- 5: Adds 3+ non-obvious insights — cultural factors, reverse conditions, domain-specific exceptions, historical context.
- 3: Adds reasonable but predictable nuance — restates boundary in different words.
- 1: Recycled content from definition/mechanism, or adds nothing new.

### 6. Schema Completeness (PASS/FAIL)
Are all required fields present and well-formed? (name ≥3 chars, definition ≥30 chars, mechanism non-empty, etc.)

---

## OUTPUT FORMAT

Return JSON for each FB:

```json
{
  "fb_name": "Principle Name",
  "causal_soundness": 4,
  "abstraction_quality": 5,
  "boundary_precision": 3,
  "evidence_grounding": 4,
  "elaboration_depth": 5,
  "schema_complete": true,
  "golden_candidate": true,
  "golden_rationale": "Why this FB is a strong few-shot example",
  "finetune_candidate": false,
  "finetune_rationale": "",
  "gate_recommendation": "PASS",
  "gate_concern": "",
  "overall_score": 4.2,
  "overall_comment": "One-sentence summary of quality assessment"
}
```

### Golden candidate: score ≥4.0 across all dimensions, diverse discipline, shows the model HOW to extract
### Fine-tune candidate: represents a discipline/depth/type combination underrepresented in the corpus
### Gate: PASS (ship it), FLAG (needs human review), FAIL (reject/rewrite)

---

## BATCH FB DATA FOR EVALUATION

**(Insert FBs from checkpoint here — one batch of 5 per round)**

---

## POST-EVALUATION: Cross-Juror Consensus

After all 3 models evaluate independently:
1. **High consensus** (all agree on golden/finetune): auto-promote to golden few-shot set
2. **Split decision** (2:1): flag for human review with dissenting rationale
3. **Low consensus** (all disagree): automatically rejected from golden/finetune pools

Aggregate golden examples by discipline distribution (ensure ≤3 per discipline to avoid bias).
Aggregate fine-tuning candidates to cover: 5 disciplines × 3 depths × 3 extraction types = 45 representative FBs.

## CURRENT GEMSA GATE ISSUE (context for evaluation)

Gemma-4-E4B currently rejects 73% of convergent FBs because it demands verbatim evidence for synthesized principles. When evaluating gate_recommendation, consider: is this principle LOGICALLY supported by evidence (even if not explicitly stated), or is it fabricating claims?

## S5 VERIFICATION BENCHMARK (2026-08-09)

Tested 15 convergent FBs through full S4→S5 pipeline:

| Gate | Result |
|------|--------|
| S4 Classification | 15/15 valid (100%) — canonical mapping correct |
| S5 BORP (source diversity) | 15/15 PASS |
| S5 NLI (ModernBERT entailment) | 15/15 NEUTRAL 0.400 — expected for synthesis |
| S5 Gemma-4-E4B (cross-family) | 4/15 PASS (27%) — 73% false negative |

**Gemma rejection pattern**: Every rejection says "The Foundation Block introduces concepts... that are not verified in the evidence passages." Gemma demands verbatim evidence for synthesized abstractions — it rejects the convergent synthesis methodology itself.

**PASS FBs (deemed factually consistent by Gemma):**
1. Patch Cord Routing and Object Connection (software engineering, 600c elaboration)
2. Value-First Demonstration variant (psychology, 537c)
3. Intuitive Decision Making (psychology, 1143c)
4. Translation as Pathway to Insight (emerging, 941c)

**Verification model alternatives analyzed:**
- No dedicated verification model exists in MLX 4-bit ecosystem
- Candidates: gemma-2-9b-it-4bit (untested), Qwen2.5-7B-Instruct-4bit (untested), Mistral-Nemo-12B-4bit (untested)
- Only proven model: Qwen3-Coder-30B (understands FB synthesis but breaks R5 cross-family)
- Recommendation: use Q3C as verifier OR lower Gemma threshold to 0.3

---

## DSPy S2 OPTIMIZER VALIDATION (T-007/D2248/D2250)

When evaluating the DSPy-optimized S2 extractor (`/tmp/dspy_mipro_optimized.json`),
additionally assess:

### A. Demo Diversity (T-007b)
- MIPROv2 selects few-shot demos from the golden pool. D2248 found the 2-demo
  program selected DESIGN-ONLY books (Cooper/Krug/Norman) while the golden pool
  spans 38 domains → positive-fidelity losses on non-design examples.
- **Validation check:** list the source books of the selected demos. If any domain
  cluster (>25% of golden pool) is unrepresented, flag for T-007b (demos 2→4).

### B. Calibration (D2250 audit)
- Metric weights: convergence 0.30, type 0.20, name 0.12, mechanism 0.13,
  evidence 0.10, boundary 0.05, consequence 0.05, route 0.05 = 1.00.
- False positives capped at 0.20; false negatives partial credit 0.10.
- **Validation check:** verify perfect positive = 1.0, perfect negative = 1.0,
  FP ≤ 0.20 (run `extraction_metric` unit checks).

### C. Leakage & Contamination (A-002/A-004)
- Test set: 20 examples (train_frac 0.60), author-disjoint few-shot selection
  (`_author_disjoint_fewshot`). Golden pool: 73 entries, 194 evidence passages,
  **100% verbatim** in cluster segments (T-003 audit).
- **Validation check:** no test-example author appears in its few-shot pool
  (verify `_example_authors` disjointness).

### D. Golden Pool Requirements (user audit, D2250)
- **Quality:** 0 field gaps (name/definition/mechanism/boundary/consequence ≥ min len)
- **Accuracy:** 73/73 rationale present; 194/194 evidence verbatim
- **Author cap:** ≤3 per author by FB-mention (T-009 + D2250: Christian 4→3 fix)
- **Future/agentic-proof:** depth classes universal=1, specialized=1 — UNDER-REPRESENTED
  (4% of positives). Flag: DSPy cannot learn these classes; benchmark confidence
  on them is low. Expansion tracked as T-015.
- **Ontological accuracy:** depth distribution domain=26, cross-domain=26 (96% of
  positives). Cross-domain is the dominant real-world class — correctly captured.

### E. S4 Depth Classifier (D2245/D2250)
- GPT-OSS-20B-MXFP4-Q8 with SHORT focused prompt: **87.5% (7/8)**, cross-domain 3/3
  (was 0/3 for all models with long prompt). Benchmark:
  `governance/s4_depth_benchmark_focused_prompt.json`
- **Validation check:** depth accuracy ≥ 80% on the 8-FB stratified benchmark;
  cross-domain ≥ 2/3. Regression → re-check prompt structure (BUG-075).
