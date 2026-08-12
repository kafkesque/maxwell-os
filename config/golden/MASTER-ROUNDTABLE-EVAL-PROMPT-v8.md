# Master Roundtable Evaluation Prompt — v8.0
## E2E Diagnostic Results + S4 Classifier Benchmark + Quality Audit

**Authority:** D2269–D2282 | Cross-examination: 4-LLM audit against Maxwell OS v3.0
**Audience:** S-tier senior RAG engineers (LLM evaluators: GPT-OSS, Qwen3.6, Phi-4-mini, Gemma-4-E4B)
**Purpose:** Evaluate diagnostic results, S5 verification quality, and classification benchmark
**Date:** 2026-08-12

---

## ⚠️ v8.0 CHANGELOG

| Change | Detail |
|--------|--------|
| **Diagnostic completed** | 100 books, 200 clusters → 188 FBs → 185 classified → 134 verified PASS (72.4%) |
| **S4 classifier benchmark** | GPT-OSS-20B vs Qwen3.5-9B-4bit framework built (`tools/benchmark_s4_classifiers.py`) |
| **BUG-080.1–080.11** | 11 bugs found and fixed during diagnostic execution |
| **Qwen3.5-9B-4bit** | Downloaded (5.7GB), loaded into OMLX, awaiting benchmark |
| **Pipeline config** | `config/pipeline_config.yaml` v3.0-D2176 → D2282 |
| **Dependency refs** | `DECISION-LOG.md` D2269–D2282, `buglog.md` BUG-080.1–080.11 |

---

## §1. DIAGNOSTIC RESULTS (GROUND TRUTH)

### Pipeline Execution (2026-08-11 → 2026-08-12)

```
Stage  Run ID                        Result
────── ────────────────────────────  ──────────────────────────────────
S1.5   diagnostic_20260811_232853   200 convergent clusters (100 books)
S2     diagnostic_20260811_232853   188 FBs extracted (51.2 min)
S4     diagnostic_20260811_232853   185 FBs classified (GPT-OSS-20B, batch D2265)
S5     diagnostic_20260811_232853   185 FBs verified → 134 PASS (72.4%)
S6     diagnostic_20260811_232853   SQLite + Parquet committed
```

### Gate Evaluation

| Gate | Threshold | Actual | Verdict |
|------|-----------|--------|---------|
| Yield (FBs / books) | >1% | 188% | ✅ PASS |
| S5 Pass Rate | >40% | **72.4%** | ✅ **STRONG PASS** |
| S5 Quarantine Rate | <60% | 27.6% | ✅ PASS |
| S5 Flag Rate | <10% | 0% | ✅ PASS |

**T1.1 GATE: ✅ PASSED — Full 750-book run authorized.**

### S5 Verification Breakdown

| Method | Count | % | Description |
|--------|-------|---|-------------|
| `nli` | 90 | 48.6% | DeBERTa FEVER NLI-only — fast gate (~0.3s/FB) |
| `nli+LLM` | 75 | 40.5% | NLI marginal → escalated to Phi-4-mini deep check |
| `nli+LLM-echo` | 9 | 4.9% | Citation echo risk → mandatory LLM escalation |
| `mech_quality` | 11 | 5.9% | Auto-quarantined — no extractable causal mechanism |

### Domain Distribution (185 FBs)

| Domain | Count |
|--------|-------|
| emerging | 149 |
| ai & agents | 22 |
| engineering practice | 19 |
| business operations | 17 |
| organizational behavior | 16 |
| semiotics & communication | 11 |
| research & methodology | 10 |
| systems & frameworks | 10 |
| Other (14 domains) | 47 |

### Depth Distribution

| Depth | Count | % |
|-------|-------|---|
| cross-domain | 158 | 85.4% |
| domain | 25 | 13.5% |
| universal | 2 | 1.1% |

### Epistemic Status

| Status | Count | % |
|--------|-------|---|
| corroborated | 134 | 72.4% |
| cross-source-unverified | 51 | 27.6% |

---

## §2. S4 CLASSIFIER BENCHMARK — FRAMEWORK

### Models Under Test

| Model | Size | Quantization | Role |
|-------|------|-------------|------|
| **gpt-oss-20b-MXFP4-Q8** (baseline) | 20B | Q8 (~12-14GB) | Current S4 classifier (D2249) |
| **Qwen3.5-9B-4bit** (candidate) | 9B | 4bit (~5-6GB) | Proposed replacement |

### Benchmark Design (`tools/benchmark_s4_classifiers.py`)

The benchmark runs both models on the same FBs, comparing four classification fields:

| Field | Type | What's Compared |
|-------|------|----------------|
| `domains` | list[str] | Multi-label domain assignment (e.g., ["cognitive science", "ai & agents"]) |
| `depth` | str | Depth tier: universal / cross-domain / domain / specialized |
| `discipline` | str | Academic discipline classification |
| `evidence` | str | Evidence classification: cited / inferred / speculative |

### Agreement Metrics

For each field, compute:
- **Exact match rate** — percentage where both models produce identical output
- **Domain overlap** — Jaccard similarity for multi-label domains
- **Depth agreement** — same depth tier assigned

### Speed Comparison

| Model | Est. batch time (4 FBs) | Memory | S4 ETA (750 books) |
|-------|------------------------|--------|---------------------|
| GPT-OSS-20B | ~30s | ~12-14GB | ~23 min / 185 FBs |
| Qwen3.5-9B | TBD | ~5-6GB | TBD |

### Execution Requirements

```bash
# Pre-warm models before benchmark
python3 -c "
from pipeline.omlx_call import warm_model
warm_model('gpt-oss-20b-MXFP4-Q8')
warm_model('Qwen3.5-9B-4bit')
"

# Run benchmark (50 FBs, batch mode)
python3 tools/benchmark_s4_classifiers.py \
    --models gpt-oss-20b-MXFP4-Q8,Qwen3.5-9B-4bit \
    --fbs 50 --batch \
    --output governance/s4_classifier_benchmark_2026-08-12.json
```

---

## §3. ROUNDTABLE EVALUATION PROTOCOL

### Phase 1: Individual FB Quality Assessment

Each reviewer (GPT-OSS, Qwen3.6, Phi-4-mini, Gemma-4-E4B) evaluates 10 randomly sampled FBs from the 134 PASS set on:

| Criterion | Scale | Weight |
|-----------|-------|--------|
| Definition clarity | 1–5 | 25% |
| Mechanism specificity | 1–5 | 30% |
| Boundary explicitness | 1–5 | 20% |
| Evidence grounding | 1–5 | 15% |
| Actionability | 1–5 | 10% |

**Scoring:** Sum of weighted scores ≥ 3.5 → "confirm PASS"
**Disagreement:** If score spread across reviewers >1.5, escalate to cross-review

### Phase 2: Cross-FB Analysis

Identify:
1. **Golden candidates** — FBs scoring ≥4.0 from ≥3 reviewers
2. **DSPy candidates** — FBs with high mechanism specificity but borderline completeness
3. **Pattern analysis** — domains/topics where S5 consistently flags or passes

### Phase 3: Gate Re-Evaluation

Given the 72.4% S5 pass rate, evaluate:
1. Is the NLI threshold (0.5) correctly calibrated?
2. Are the 51 QUARANTINE FBs false negatives or legitimate rejections?
3. Should the BORP ≥2 threshold be tiered by depth (D2281)?

### Phase 4: Classifier Recommendation

After the GPT-OSS vs Qwen3.5-9B benchmark completes:
1. Does Qwen3.5-9B match GPT-OSS-20B on domain accuracy?
2. Is the speed/memory tradeoff worth any accuracy loss?
3. Which model should be the production S4 classifier?

---

## §4. DEPENDENCY REFERENCES

### Pipeline Architecture
- `pipeline/stage2_extract.py` — S2 convergent extraction (Qwen3-Coder-30B-A3B)
- `pipeline/stage4_merge.py` — S4 merge + classify (GPT-OSS-20B, batch D2265)
- `pipeline/stage4_merged_call.py` — S4 CRIBS classification logic
- `pipeline/stage5_verify.py` — S5 DeBERTa FEVER + Phi-4-mini verification
- `pipeline/stage6_commit.py` — S6 SQLite+Parquet commit
- `pipeline/run_diagnostic.py` — E2E diagnostic runner (D2261)
- `pipeline/runner.py` — Production pipeline runner (D2061)
- `tools/benchmark_s4_classifiers.py` — S4 classifier benchmark (D2282)

### Configuration
- `config/pipeline_config.yaml` — v3.0-D2176, batch_enabled, verifier_v2 = Phi-4-mini
- `config/model_assignments.yaml` — Agent role registry (S5_FB_VERIFIER = gemma → needs sync)
- `config/decisions.yaml` — 250 decisions (D2269–D2282 added 2026-08-12)

### Governance
- `CONSTITUTION.md` — v3.0, C1–C28 constraints
- `DECISION-LOG.md` — D2000–D2282, all architectural decisions
- `governance/buglog.md` — 19 bugs (BUG-053 through BUG-080.11)
- `governance/CROSS-EXAMINATION-IMPLEMENTATION-SPEC-2026-08-12.md` — 68 findings, 14 bugs, 13 decisions
- `MASTER-TASK-REGISTER.md` — Task tracker

### Data Artifacts
- `knowledge pipeline/checkpoints/stage2_extract/diagnostic_20260811_232853/checkpoint.jsonl` — 188 S2 FBs
- `knowledge pipeline/checkpoints/stage4_merge/diagnostic_20260811_232853/checkpoint.jsonl` — 185 S4 classified FBs
- `knowledge pipeline/checkpoints/stage5_verify/diagnostic_20260811_232853/checkpoint.jsonl` — 185 S5 verified FBs
- `knowledge pipeline/diagnostic_diagnostic_20260811_232853.db` — SQLite diagnostic DB
- `governance/e2e_diagnostic_2026-08-12.md` — Human-readable diagnostic report

### Models Available
| Model | Location | Role |
|-------|----------|------|
| Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | OMLX | S2 Generator |
| gpt-oss-20b-MXFP4-Q8 | OMLX | S4 Classifier |
| Phi-4-mini-instruct-8bit | OMLX | S5 Deep Verifier |
| Qwen3.5-9B-4bit | OMLX (new) | S4 Candidate |
| gemma-4-E4B-it-MLX-4bit | OMLX | Reviewer |
| gemma-4-31B-it-MLX-8bit | OMLX | High-capability fallback |
| Qwen2.5-3B-Instruct-4bit | OMLX | Lightweight tasks |

---

## §5. OUTPUT FORMAT

Each roundtable evaluator produces a JSON report:

```json
{
  "evaluator_model": "gpt-oss-20b-MXFP4-Q8",
  "evaluator_family": "openai",
  "evaluated_fbs": 10,
  "individual_scores": [
    {
      "fb_id": "abc123...",
      "name": "Efficiency-over-identity Tradeoff",
      "definition_clarity": 4,
      "mechanism_specificity": 3,
      "boundary_explicitness": 4,
      "evidence_grounding": 5,
      "actionability": 3,
      "weighted_score": 3.75,
      "verdict": "confirm_pass",
      "notes": "Strong evidence, weak mechanism. Still correct."
    }
  ],
  "golden_candidates": ["fb_id_1", "fb_id_2"],
  "dspy_candidates": ["fb_id_3"],
  "threshold_assessment": {
    "nli_0.5_calibrated": true,
    "borp_tiering_recommended": true,
    "false_negative_estimate": "5-8 of 51 quarantine"
  },
  "classifier_recommendation": null,
  "overall_confidence": 0.85
}
```

---

*Prompt version: v8.0 | Date: 2026-08-12 | Diagnostic run: diagnostic_20260811_232853*
*Previous: v7.0 (DSPy comparison) | Next: v9.0 after S4 classifier benchmark*
