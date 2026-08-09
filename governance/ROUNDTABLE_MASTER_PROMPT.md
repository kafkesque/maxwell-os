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
