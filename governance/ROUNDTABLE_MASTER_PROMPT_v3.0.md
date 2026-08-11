# Maxwell OS v3.0 — LLM Roundtable Evaluation Master Prompt
> **Version:** v3.0 (2026-08-11)
> **Purpose:** Multi-LLM cross-examination of diagnostic pipeline outputs
> **Input:** S5-verified Foundation Blocks from E2E diagnostic run
> **Output:** Quality scores, hallucination flags, golden candidate selection, DSPy candidate extraction

---

## Roundtable Setup

### Participants (cross-family, R5-compliant)
| Role | Model | Family | Purpose |
|------|-------|--------|---------|
| Reviewer A | GPT-OSS-20B-MXFP4-Q8 | OpenAI | Classification quality, depth accuracy |
| Reviewer B | Qwen3-Coder-30B-A3B | Qwen/Alibaba | Mechanism/logic coherence |
| Reviewer C | Phi-4-mini-instruct-8bit | Microsoft | Factual grounding (WITH source text only) |
| Reviewer D | Gemma-4-E4B-it-MLX-4bit | Google | Cross-reference, gap analysis |
| Arbiter | Human (you) | — | Final judgment, tie-breaking |

### Input Files
- Diagnostic report: `governance/e2e_diagnostic_YYYY-MM-DD.md`
- Diagnostic JSON: `governance/e2e_diagnostic_YYYY-MM-DD.json`
- Diagnostic DB: `data/diagnostic_{run_id}.db` (SQLite with sqlite-vec)
- Golden reference: `config/golden/stage2_fewshot_convergent.yaml`
- Constitution: `CONSTITUTION.md`
- Decision log: `DECISION-LOG.md`
- Pipeline config: `config/pipeline_config.yaml`
- Buglog: `governance/buglog.md`

---

## Phase 1: Individual FB Quality Assessment

For each S5-verified Foundation Block, each reviewer evaluates:

### 1.1 Factual Grounding (Reviewer A + Reviewer C)
- **Source alignment:** Does the definition accurately reflect the evidence passages?
- **Hallucination scan:** Any claims NOT grounded in source text? Flag with evidence.
- **Citation echo check:** Is the mechanism vacuous ("X works because it enables X")? (D2220)
- **BORP integrity:** Are the N distinct source books genuinely different books? (by SHA-256 source_id, D2185)

### 1.2 Mechanism Coherence (Reviewer B)
- **Causal chain:** Does the mechanism explain HOW, not just define WHAT?
- **Non-tautological:** Does NOT start with "because it enables/allows/helps..." (BANNED_MECHANISM_PREFIXES)
- **Mechanism length:** ≥150 chars (MECHANISM_MIN_LENGTH, D2220)
- **Boundary test:** Is the boundary specific ("fails when X") or generic?

### 1.3 Classification Accuracy (Reviewer A + Reviewer D)
- **Discipline precision:** Is the discipline the most specific correct label? "computational neuroscience" > "neuroscience"
- **Domain validity:** Are domains practical (where a practitioner APPLIES this)?
- **Depth accuracy (physicist-chef-poet test):**
  - **universal** = law of nature/math (entropy, power laws, conservation) — RARE, <5% of FBs
  - **cross-domain** = bridges 2+ DISTINCT disciplines via shared mechanism — ~10-15%
  - **domain** = operates within one field, needs context — ~60-70%
  - **specialized** = narrow sub-technique — ~10-15%
- **is_specialized flag:** Consistent with depth?

### 1.4 Completeness (Reviewer D)
- All required fields present: name, definition, mechanism, boundary, consequence
- CRIBS enrichment quality: application (prescriptive? null for descriptive?), failure_mode (specific?), elaboration (3-5 sentences?)
- Keywords: 3-5 search terms, comma-separated
- Jargon: Only truly specialized terms (NOT copied from keywords)

---

## Phase 2: Cross-FB Analysis

### 2.1 Golden Candidate Selection
Score each FB on golden worthiness (1-10):
- **Epistemic novelty:** Does this teach something non-obvious?
- **Mechanism quality:** Clear causal chain, falsifiable boundary
- **Source convergence:** 3+ distinct books confirming the same insight? (BORP ≥ 3)
- **Cross-domain potential:** Could this bridge disciplines?
- **Actionability:** Can a practitioner USE this?

**Golden candidate threshold:** Score ≥ 7 → candidate for `config/golden/stage2_fewshot_convergent.yaml`

### 2.2 DSPy Few-Shot Candidates
Identify FBs suitable for DSPy training:
- S5 PASS + high confidence_score (>0.8) → positive example
- S5 FLAG with specific fixable issue → borderline (with annotation)
- S5 QUARANTINE with clear hallucination → negative example

### 2.3 Pattern Detection
- **Recurring hallucination types:** Over-assigned "universal"? Vague mechanisms? Fake jargon?
- **Depth inflation:** % of FBs assigned "universal" or "cross-domain" vs expected distribution
- **Source contamination:** Any FB where source_books include non-existent titles?
- **Field bias:** Discipline distribution skewed toward certain fields?

---

## Phase 3: Gate Evaluation

### 3.1 Diagnostic Gate Criteria (D2261)
- **Yield rate:** {s2_fb_count} FBs / {books_sampled} books = {yield_pct}%
  - PASS: >1.0% | MARGINAL: 0.5-1.0% | FAIL: <0.5%
- **S5 pass rate:** {s5_pass_rate}%
  - PASS: >40% | MARGINAL: 20-40% | FAIL: <20%
- **Verdict:** APPROVE T1.1 / MARGINAL (judgment call) / HALT

### 3.2 T1.1 Readiness Assessment
- **S2 yield:** Is the extraction producing enough FBs per book?
- **S4 quality:** Are CRIBS enrichments and classifications accurate?
- **S5 reliability:** Is verification catching hallucinations?
- **S6 integrity:** Are commits atomic and schema-valid?
- **Model performance:** Any model showing degradation after extended use?

---

## Phase 4: Recommendations

### 4.1 Immediate Actions
- FBs to promote to golden set (with rationale)
- FBs to fix and re-run (with specific issues)
- FBs to discard (with reasons)

### 4.2 T1.1 Optimization
- **Batch classification settings:** Optimal batch_size for S4 (D2265)?
- **Model assignments:** Any model swap recommended for T1.1?
- **Threshold tuning:** NLI thresholds (marginal/entailment/pass) appropriate?
- **Cluster selection:** Should T1.1 use --only-convergent or process all?

### 4.3 Golden Set v5.0 Plan
- How many new golden examples from this run?
- Which existing golden examples should be retired/re-classified?
- DSPy training readiness assessment

---

## Evaluation Rules

1. **Source text required:** Phi-4-mini (Reviewer C) MUST receive evidence_passages verbatim. If source text is missing, auto-flag (BUG-053 guard).
2. **No model reviews own output:** Cross-family design ensures S2 (Qwen3), S4 (GPT-OSS), S5 (Phi-4-mini/DeBERTa) never self-review.
3. **Fail-closed (D2093):** Any uncertainty → flag, not pass. "Maybe correct" = FLAG.
4. **Evidence-first:** Every claim about FB quality must cite specific evidence passages or FB fields.
5. **temp=0.0 on all generation (R7):** Consistent, reproducible evaluations.
6. **Config-driven thresholds (C12):** All thresholds from `config/pipeline_config.yaml` — never hardcoded.

---

## Output Format

Return a JSON object:
```json
{
  "roundtable_version": "v3.0",
  "timestamp": "ISO8601",
  "reviewers": ["GPT-OSS-20B", "Qwen3-Coder-30B", "Phi-4-mini-instruct", "Gemma-4-E4B"],
  "fb_evaluations": [
    {
      "fb_id": "...",
      "fb_name": "...",
      "reviewer_scores": {
        "factual_grounding": {"score": 0.X, "issues": [...], "reviewer": "GPT-OSS"},
        "mechanism_coherence": {"score": 0.X, "issues": [...], "reviewer": "Qwen3-Coder"},
        "classification_accuracy": {"score": 0.X, "issues": [...], "reviewer": "Gemma-4-E4B"},
        "completeness": {"score": 0.X, "issues": [...], "reviewer": "Gemma-4-E4B"}
      },
      "golden_candidate": {"score": X, "worthy": true/false, "rationale": "..."},
      "dspy_candidate": {"role": "positive|borderline|negative", "rationale": "..."},
      "overall_verdict": "PROMOTE|FIX|DISCARD",
      "specific_issues": [...]
    }
  ],
  "cross_fb_analysis": {
    "patterns": [...],
    "depth_distribution": {"universal": N, "cross-domain": N, "domain": N, "specialized": N},
    "discipline_distribution": {...},
    "recurring_hallucinations": [...]
  },
  "gate_evaluation": {
    "yield_pct": X.XX,
    "s5_pass_rate": X.XX,
    "verdict": "APPROVE|MARGINAL|HALT",
    "rationale": "..."
  },
  "recommendations": {
    "promote_to_golden": [{"fb_id": "...", "rationale": "..."}],
    "fix_and_rerun": [{"fb_id": "...", "issues": [...]}],
    "discard": [{"fb_id": "...", "reason": "..."}],
    "t1_1_optimizations": [...],
    "golden_v5_plan": "..."
  }
}
```

---

## Reference: Pipeline Architecture

```
S0 (EPUB→MD) → S1 (Chunk) → S1.5 (Cluster/Prefilter)
  → S2 (Convergent Extract: Qwen3-Coder) 
  → S4 (Merge+CRIBS+Classify+Depth: GPT-OSS-20B) 
  → S5 (DeBERTa FEVER NLI + Phi-4-mini deep check + BORP) 
  → S6 (SQLite + Parquet)
```

## Reference: Key Decision Records
- **D2261:** E2E Diagnostic Gate (yield >1% + S5 pass >40%)
- **D2264:** Phi-4-mini swapped into S5 verifier (67% accuracy vs Gemma 33%)
- **D2265:** Batch classification for S4 (GPT-OSS reasoning amortization)
- **D2266:** Process guard — PID file locking prevents multi-diagnostic
- **D2267:** Laptop sleep prevention (caffeinate)
- **D2268:** BUG-053 mitigation — S5 source text guard
- **D2220:** Citation echo detection — mechanism quality pre-filter
- **D2250:** GPT-OSS-20B as S4 classifier (replaced Phi-4-mini)
- **D2255:** DeBERTa FEVER primary NLI (replaced ModernBERT)
- **D2093:** Fail-closed verification (any uncertainty → QUARANTINE)
