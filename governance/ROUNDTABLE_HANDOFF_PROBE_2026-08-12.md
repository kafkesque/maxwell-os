# Roundtable Handoff — Clean Probe Evaluation (40 FBs, v3.0-D2298)

**Date:** 2026-08-12
**Audience:** Independent LLM evaluators (Kimi, Claude, DeepSeek, Qwen, GPT-OSS)
**Purpose:** Evaluate S2→S4→S5 output quality, identify golden examples, audit pipeline state
**Authority:** Maxwell OS v3.0 | DeBERTa-only S5 (D2298) | ISOR scoring (D2284) | Hybrid gate (D2276)

---

## 0. What You're Evaluating

A clean 50-cluster probe run through the full pipeline. 40 Foundation Blocks (FBs) produced.
Each FB is a "convergent principle" — a named, reusable mechanism extracted from 2+ source books
where the same idea appears independently (convergence = higher confidence of universality).

**Files to evaluate** (all JSONL, one JSON object per line):
- `probe_output/stage2_fbs.jsonl` — raw extraction (S2: name, definition, mechanism, boundary, consequence, evidence_passages)
- `probe_output/stage4_fbs.jsonl` — classified + enriched (adds: application, failure_mode, elaboration, depth, discipline, domains)
- `probe_output/stage5_fbs.jsonl` — verified (adds: status, epistemic_status, isor, confidence_score)

**Readable summaries:** `probe_output/stage{2,4,5}_visual.md`

---

## 1. Schema Reference

| Field | Stage | Meaning |
|-------|-------|---------|
| `name` | S2 | Short label |
| `definition` | S2 | WHAT the principle is (1-3 sentences) |
| `mechanism` | S2 | HOW it works (causal chain) |
| `boundary` | S2 | WHEN it fails / limits |
| `consequence` | S2 | downstream effects |
| `evidence_passages` | S2 | verbatim source quotes |
| `application` | S4 | WHEN to use (prescriptive) |
| `failure_mode` | S4 | HOW it fails |
| `elaboration` | S4 | non-obvious implications |
| `depth` | S4 | universal / cross_domain / domain / specialized |
| `discipline` | S4 | academic field |
| `domains` | S4 | application domains |
| `status` | S5 | PASS or QUARANTINE |
| `epistemic_status` | S5 | corroborated / source_supported / cross_source_unverified / speculative |
| `isor.rating` | S5 | strong / medium / weak (source independence) |
| `confidence_score` | S5 | 0.15·mechanism + 0.75·NLI + 0.10·enrichment |

---

## 2. Evaluation Task A — FB Quality (rate each FB 1-5)

For each of the 40 FBs, rate these 5 dimensions:

1. **Definition clarity** (1-5): Is the definition precise, standalone, non-redundant?
   - 5 = crisp, self-contained, defines WHAT without HOW
   - 1 = vague, circular, or repeats the mechanism
2. **Mechanism quality** (1-5): Does it explain HOW with a causal chain?
   - 5 = concrete causal mechanism ("X causes Y because Z")
   - 1 = tautological ("works because it's effective") or just restates definition
3. **Boundary specificity** (1-5): Are limits concrete and falsifiable?
   - 5 = specific conditions ("fails when X > threshold")
   - 1 = vague ("sometimes", "it depends", missing)
4. **Evidence fidelity** (1-5): Does the definition match `evidence_passages`?
   - 5 = definition is directly supported by cited passages
   - 1 = definition contradicts or extrapolates beyond evidence
5. **Convergence genuineness** (1-5): Is this truly convergent across 2+ independent sources?
   - 5 = same idea independently in multiple books
   - 1 = single-source echo or obvious/trivial ("good design is important")

**Output format:**
```
FB name | def_clarity | mechanism | boundary | evidence | convergence | overall | notes
```

---

## 3. Evaluation Task B — Classification Accuracy (S4)

For each FB, check:
1. Is `depth` correct? (universal = applies everywhere; cross_domain = shared across fields; domain = one field; specialized = narrow niche)
2. Is `discipline` correct?
3. Are `domains` appropriate (not too broad, not too narrow)?
4. Is `application` genuinely prescriptive ("When X → do Y")?
5. Is `failure_mode` specific (describes HOW it fails, not just "fails sometimes")?

---

## 4. Evaluation Task C — Factuality + Verification (S5)

For each FB:
1. Is the PASS/QUARANTINE verdict correct? (Should a QUARANTINE have been PASS, or vice versa?)
2. Is `epistemic_status` correct given the ISOR rating and NLI result?
3. Flag any FB where the NLI entailment score (or ISOR) seems wrong.

**Context on S5 calibration:** DeBERTa-v3-large NLI at threshold 0.10 (precision 1.000, recall 0.556 on 12 human-adjudicated FBs). It's fail-closed: QUARANTINE is not "wrong", it's "not yet proven". High recall means some true principles get QUARANTINE'd (evidence mismatch, D2227).

---

## 5. Evaluation Task D — Golden Example Identification

**MOST VALUABLE OUTPUT.** Identify which FBs would make good golden examples:

**Positive golden candidates** (should be a positive example in the training set):
- High-quality definition + mechanism + boundary (score 4-5 on all dimensions)
- Multi-source convergence (ISOR strong/medium)
- Non-obvious (NOT "good design is important")
- Clean evidence alignment

**Negative golden candidates** (should be a hard-negative in the training set):
- Tautological mechanism ("works because it works")
- Vague boundary ("fails under certain conditions")
- Single-source echo (all evidence from one book)
- Obvious/trivial principle
- Definition-mechanism redundancy (mechanism just restates definition)

For each candidate, give: `FB name | pos/neg | reason (1 line)`.

---

## 6. Evaluation Task E — Pipeline Audit (senior RAG engineer POV)

From your external perspective, evaluate the pipeline for:
1. **Gaps** — what's missing that a production RAG/knowledge system needs?
2. **Conflicts/contradictions** — any schema or logic inconsistencies you observe in the output?
3. **Bloat tax** — redundant fields or over-engineering?
4. **Future tax** — architectural decisions that will be painful later?
5. **Blindspots** — quality dimensions not measured?
6. **Bottlenecks** — where's the cost?
7. **Hidden failures** — silent data loss risks?
8. **Drift** — inconsistency between stages?

**Be specific and pragmatic.** Reference actual FBs where possible. Don't assume — verify against the JSONL.

---

## 7. Evaluation Task F — Pipeline Viability

Compare against known solutions (GraphRAG, LightRAG, HippoRAG, Naive RAG + LLM rerank, DSPy pipelines, RAPTOR):

1. Is the cluster-before-extract + convergent principle + NLI verification approach sound?
2. What's the unique value? What's redundant with existing solutions?
3. What would you change first if you inherited this codebase?

---

## 8. Output Format (consolidated)

Submit one document with:
1. **Task A**: 40-row quality table
2. **Task B**: classification errors (if any) with corrections
3. **Task C**: verification errors (if any) with corrections
4. **Task D**: golden candidates (pos + neg) — prioritized
5. **Task E**: pipeline audit findings (numbered, severity-tagged)
6. **Task F**: viability verdict + top 3 changes

Tag findings with severity: 🔴 critical / 🟠 high / 🟡 medium / ⚪ low.
