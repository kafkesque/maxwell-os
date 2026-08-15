# LLM Roundtable — Master Prompt
> Evaluate Maxwell OS v3.0 convergent Foundation Blocks for golden few-shot examples and fine-tuning candidates.
> **v8 (D2250-D2252, 2026-08-10):** Updated with hybrid S2 result (0.736), S4 GPT-OSS depth fix (87.5%), golden audit findings, full-run cost model.
> Delegated to: Qwen3-Coder-30B (primary), Gemma-4-E4B (cross-family validation), Phi-4-mini (summarization)
> Run: delegate each model independently, compare outputs, rank by consensus.
>
> **Latest session results to validate (D2250-D2252):**
> - S4 depth: GPT-OSS-20B + focused short prompt = **87.5% (7/8)**, cross-domain **3/3** (was 0/3 all models). Benchmark: `governance/s4_depth_benchmark_focused_prompt.json`
> - S2: **Hybrid (DSPy gate + Traditional extract) = 0.736** > DSPy 0.672 > Traditional 0.591 (20 examples, 3-arm A/B)
> - Golden pool audit: 0 quality gaps, 73/73 rationale, 194/194 evidence verbatim, author cap ≤3 (Christian 4→3 fixed)
> - Known gap: depth class imbalance — universal=1, specialized=1 (4% of 54 positives) → T-015 expansion

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

---

## HYBRID S2 ARCHITECTURE VALIDATION (D2251/D2252 — production architecture)

### F. Three-Arm A/B (20 examples, Qwen3-Coder temp 0.0)
| Metric | Traditional | DSPy-MIPROv2 | **Hybrid** |
|--------|-------------|--------------|-----------|
| Avg Quality | 0.591 | 0.672 | **0.736** |
| Avg Latency | 29.7s | 27.0s | 45.8s |
| Negatives rejected (n=6) | 0/6 | 5/6 | 5/6 |
| Positive fidelity (n=14) | 0.845 | 0.602 | 0.845 |

- **Hybrid = DSPy route gate (negative rejection) + Traditional extraction (positive fidelity).**
- DSPy alone: perfect gate, weak extractor (2 demos design-only — Cooper/Krug/Norman).
- Traditional alone: strong extractor, no gate (0/6 negatives rejected).
- **Validation check:** hybrid must match Traditional on positives AND DSPy on negatives.
  Regression → gate FN (CONV-036/043/040 pattern) or extraction fidelity loss.
- **Latency note:** hybrid 45.8s = gate (~13s) + extract (~30s); gate short-circuits
  negatives at ~13s. Full report: `governance/DSPY_VALIDATION_REPORT.md`

### G. Full-Run Cost Model (T1.1 — 12,964 clusters)

> **⚠️ SUPERSEDED by D2363 (2026-08-15).** D2362's ~90h used the batch CRIBS path; production runs merged_cribs_classify() = 32.29s/FB median. The prior "~26h / S4 = 3.9h" figure here was WRONG:
> it implied 1.08s/FB for S4, but GPT-OSS is a reasoning model whose fastest measured call is 4.0s.
> Same-day measured latency (`S4_BOTTLENECK_ANALYSIS.md`) puts S4 at ~25s/FB **serial** (no parallelism
> in `stage4_merge.py`) = **~142h for S4 alone** (merged 32.29s + depth 7.2s). Corrected T1.1 ≈ **160–200h serial**. Do not plan a
> 26h launch on this model. See D2362 + `S4_BOTTLENECK_ANALYSIS.md` for the authoritative numbers.

Naive estimate (12,964 × 28s ÷ 1 worker = 100h). Historical D2253 model (now known-stale):

| Segment | Clusters | Cost/cluster | Subtotal |
|---------|----------|-------------|----------|
| Single-source (79.7%) | 10,330 | 12s (simplified prompt) | 124,000s |
| Convergent (20.3%) | 2,634 | 28s (full synthesis + few-shot) | 73,750s |
| Split-probe (5.3%) | 683 | +6s (Phi probe + k-means) | 4,100s |
| **S2 total ÷ 3 workers** | | | **~18.7h** |
| S4 merged (D2224, ~45% faster) | ~2,634 FBs | ~16s ÷ 3 workers | ~~~3.9h~~ → **~90h measured serial** |
| S5 verify (Gemma + DeBERTa) | ~2,634 FBs | ~3s ÷ 3 workers | ~0.7h |

**Wall-clock (corrected) ≈ 160–200h** (D2363), NOT 21-26h (D2253) nor 110-140h (D2362). S2 parallelism is real
(`stage2.max_workers: 3`, ThreadPool, config-driven); S4 has **zero** parallelism (serial,
one FB per GPT-OSS call).

### H. Golden Pool Audit Results (D2250 — user-requested)
- **Quality:** 0 field gaps; **Accuracy:** 73/73 rationale; **Verbatim:** 194/194 evidence
- **Author cap:** ≤3 by FB-mention (T-009 + D2250 Christian 4→3 via CONV-012→Age of AI)
- **Leakage:** author-disjoint few-shot (A-002) verified 0 overlap
- **Metric calibration:** weights sum 1.00; FP ≤0.20; FN = 0.10; perfects = 1.0
- **⚠️ Depth imbalance:** universal=1, specialized=1 (4%) — under-represented; benchmark
  confidence on these classes is low → T-015 expansion tracked

---

## AUDIT FOCUS (2026-08-15 — post-D2363, for external LLM re-audit)

You are re-auditing Maxwell OS v3.0 for residual bugs, blindspots, gaps, conflicts,
contradictions, hidden failures, and drift. VERIFY against actual code/config — do not assume.
Focus areas, highest-value first:

1. **S4 cost model (D2363):** merged_cribs_classify() = 32.29s/FB median (n=6, high variance 30-72s).
   Re-measure at n≥20; confirm the focused-depth call (~7.2s) is truly additive (not already in the
   merged output). Verify T1.1 ≈ 160-200h.
2. **S4 speedup gates:** S4-A batch depth (75% parity) and S4-B gemma cascade (62.5% accuracy) both
   fail the ≥90% gate → dormant (batch_enabled:false, depth_frugal_enabled:false). Confirm no path
   silently activates them.
3. **Golden hash (NEW):** .golden_meta.json full SHA-256 + tools/verify_golden_hash.py. Confirm it is
   wired into canary/T1.1 preflight (currently a standalone tool, not yet gated).
4. **Depth-bias relabel (NEW):** 13 golden FBs relabeled via 3-model vote
   (governance/depth_bias_relabel_vote.json). Audit whether any of the 13 should revert.
5. **Golden set defects (unresolved):** universal=1, specialized=1 (imbalanced); CONV-037/CONV-039
   list-form expected_fb missing depth.
6. **Decisions registry drift:** DECISION-LOG.md (source of truth) stops at D2350; D2351-D2363 exist
   only in config/decisions.yaml. Reconcile.
7. **Buglog header/body mismatch:** ~29 entries have header status emoji contradicting body status.
8. **Model registry drift:** model_assignments.yaml stale S5 verifier / cloud entries.

Report findings as (file, line, claim, evidence, verdict). Do not mutate code — flag only.


---

# SESSION 2026-08-15 — S4 Bottleneck Speedup Roundtable (D2366)

> **Question:** can the S4 bottleneck (merged CRIBS 32s + focused depth 7s = ~39.5s/FB) be
> further improved WITHOUT breaking quality?
> **Method:** I (goose) independently verified X4/X6/X8/X9 against post-relabel gold, then
> delegated the same exhaustive review to Qwen3-Coder-30B (roundtable) and compared.

## My verified findings (presented to the roundtable)
1. Depth accuracy ~84% (n=45) — systematic gpt-oss cross-domain over-assignment.
2. X4 frugal gemma-4-E4B depth = 62.5% (4.5× faster) → FAILS 90% gate.
3. X6 batch focused-depth = 66.7% vs 84.4% sequential (n=45), parity 60% → REJECTED.
4. X8 thinking_budget=256 on merged = 1.8× faster, valid JSON → SOLE viable speedup.
5. X9 concurrency = flat (OMLX serializes) → no benefit.
6. Market research (llmfit 1.1.6): no ≤4B R5-clean model hits ≥90% depth.

## Roundtable (Qwen3-Coder-30B) response
- **Agreed with all 6 findings.**
- Added: (a) thinking_budget=128 (deeper cap), (b) quantize gpt-oss Q8→Q4_K_M, (c) LoRA fine-tune.
- ⚠️ Its "use Qwen3.6-35B/Qwen3.8-27B as proxy" suggestions violate R5 (S2 generator = Qwen family) — rejected.

## Verification of the roundtable's additions
- **thinking_budget=128: VERIFIED — 17.6s (vs 33.9s null, 21.9s @256), valid JSON** (reasoning 609 chars).
  Risk: only 609 reasoning chars → may truncate on complex FBs; budget=256 (1218 chars) is the safer default.
- Quantization Q4_K_M + LoRA: NOT yet benchmarked (deferred; requires re-quantized weights download).

## Comparison verdict
Roundtable CONFIRMS my findings and correctly identifies thinking_budget=128 as a deeper lever (now verified).
Its quantization/LoRA suggestions are legitimate but deferred; its Qwen-family proxies are R5-invalid.
**Net: thinking_budget (128–256) is the only safe S4 speedup; gated on merged-call accuracy validation.**
