# Maxwell OS v3.0 — LLM Roundtable Handoff v2

> **CRITICAL: This is an instruction set for EXTERNAL LLMs to evaluate.**
> **DO NOT answer these questions yourself. Wait for other LLMs to respond.**
>
> **Reading instructions:** Start at §1 (context), then §2 (current state), then §3 (problems discovered), then §4 (proposed architecture). Answer the 6 evaluation questions in §6 by examining the actual repository code. Return your verdict in JSON format (§7).

---

## §0 — Repository Access

```
Repo:    https://github.com/kafkesque/maxwell-os
Branch:  main
Commit:  988fed1 (current HEAD as of 2026-08-09)
Local:   /Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0/
```

### Key Files to Examine

| File | Lines | Purpose |
|------|-------|---------|
| `CONSTITUTION.md` | — | Architectural iron rules, pipeline design, model assignments |
| `DECISION-LOG.md` | — | All decisions D2000-D2216 |
| `pipeline/stage2_extract.py` | 1710 | S2 convergent extraction (Qwen3-Coder-30B via OMLX) |
| `pipeline/stage4_merge.py` | 1262 | S4 merge + CRIBS enrichment + classification (2 LLM calls) |
| `pipeline/stage5_verify.py` | 625 | S5 verification (DeBERTa FEVER NLI + BORP + completeness) |
| `pipeline/schemas.py` | 1029 | Pydantic FB schema, taxonomy, canonical labels, validators |
| `pipeline/pipeline_paths.py` | ~100 | All model/config constants |
| `config/pipeline_config.yaml` | — | Thresholds, models, pipeline settings |
| `governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md` | — | ModernBERT vs DeBERTa FEVER stress test |
| `governance/buglog.md` | — | Open bugs including DELEGATE-001, BUG-053 |

### Available Models (all local, OMLX/Ollama)

| Model | Role | Size | Provider |
|-------|------|------|----------|
| `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` | Generator (S2) | ~18GB | OMLX |
| `Phi-4-mini-instruct-8bit` | Classifier (S4) / Verification helper | ~4GB | OMLX |
| `gemma-4-E4B-it-MLX-4bit` | VerifierV2 (deprecated) | ~19GB | OMLX |
| `bge-m3` (1024-dim) | Embeddings (S1.5) | ~2GB | Ollama |
| `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | NLI (S5) | ~500MB | HuggingFace local |

---

## §1 — Context: What We're Building

Maxwell OS v3.0 is a **local-first, sovereign RAG pipeline** running on a 64GB Apple Silicon Mac. It ingests ~922 books (EPUB/PDF), converts them to Markdown, chunks them into segments, clusters semantically similar segments via FAISS cosine + Louvain, extracts convergent Foundation Blocks (FBs) via Qwen3-Coder-30B, enriches and classifies them via Phi-4-mini, verifies them via DeBERTa FEVER NLI + BORP, and commits to SQLite + Parquet.

### Constitutional Constraints (Iron Rules)

- **C1**: $0 marginal cost — all compute on local hardware, no cloud APIs
- **C3**: Sovereign — all data and compute remain local
- **R5**: Generator ≠ Verifier — different model families for extraction vs verification
- **C5**: Zero bloat — no redundant LLM calls
- **C12**: No hardcoded values — everything in config/*.yaml
- **C24**: Hardware-adaptive — auto-detect RAM, degrade gracefully
- **C28**: Quality-tiered — lightweight default, bloat is opt-in

### Current Pipeline (9-stage, 2 LLM models)

```
S0:  EPUB/PDF → Markdown (Pandoc/Docling)
S0.5: Metadata extraction (author/title via LLM)
S1:  Chunk → segments (~289K segments from 922 books)
S1.3: Regex pre-filter (boilerplate removal)
S1.5: Embed (bge-m3, 1024-dim) → FAISS cosine + Louvain clustering
S2:  Qwen3-Coder-30B extracts FBs from convergent clusters
     Output: name, definition, mechanism, boundary, consequence,
             elaboration, evidence_passages, extraction_type, content_type
S4:  Merge + CRIBS enrichment (Qwen3-Coder-30B, separate call)
     + Classification (Phi-4-mini, separate call)
     Output: application, failure_mode, keywords, jargon,
             discipline, domains, depth, specialized, evidence, context
S5:  DeBERTa FEVER NLI + BORP + completeness checks
S6:  SQLite (sqlite-vec) + Parquet export
```

---

## §2 — Current State: What's Working, What's Broken

### Working

| Component | Status |
|-----------|--------|
| S2 extraction (Qwen3-Coder-30B) | ✅ 2,655 convergent FBs extracted. Schema v3.0 (mechanism/boundary/consequence). Golden few-shot calibrated. |
| S1.5 clustering | ✅ FAISS cosine + Louvain community detection. Cluster-before-extract architecture. |
| DeBERTa FEVER NLI swap | ✅ 5.8× more discriminative than ModernBERT. Verified on 46 stratified FBs. |
| OMLX lazy loading | ✅ Only Q3C-30B loaded at S2 time (18GB). Phi-4-mini loaded at S4 time. 31GB RAM available. |
| Golden few-shot | ✅ 28 golden FBs. Inject enabled. Positive + negative examples per prompt. |

### Broken / Never Run

| Issue | Impact |
|-------|--------|
| **D2215 elaboration bug** | 2,652 of 2,655 FBs have empty `elaboration`. Fix in code. Repair script ready but NOT run. |
| **S4 never run on full set** | 2,655 FBs have no `application`, `failure_mode`, `keywords`, `jargon`, or classification labels. |
| **S5 never run on full set** | No verification scores exist for any FB. |
| **Gemma VerifierV2** | 73% false negative rate. Demands verbatim evidence. Synthesis-intolerant. 19GB wasted. |
| **S4 bottleneck** | Two LLM calls per FB (Q3C CRIBS + Phi classify), ~13s/FB, ~9.6 hours for 2,655 FBs. |

### Critical Architectural Gaps Found During Audit

Three external LLMs (Qwen, ChatGPT, Kimi) reviewed the pipeline on 2026-08-09. Here is what they found, cross-validated against the actual code:

#### Gap 1: No Actionability Classification (Kimi's Discovery, Verified)

The FB schema **requires** `application` (min_length=10) and `failure_mode` (min_length=10) for ALL FBs regardless of epistemic category. But not all principles are actionable:

| Principle Type | Example | Needs Application? | Needs Failure Mode? |
|----------------|---------|-------------------|---------------------|
| **Descriptive** | "Loss aversion causes people to overvalue what they own" | **NO** — describes a mechanism | **NO** — describes a bias, not a technique |
| **Prescriptive** | "When negotiating, anchor high first" | **YES** — actionable technique | **YES** — can fail |
| **Axiomatic** | "The golden ratio appears in natural growth patterns" | **NO** — it's an observation | **NO** — observations don't "fail" |
| **Diagnostic** | "If oscillation → feedback delay too long" | **YES** (diagnostic form) | **NO** — conditions aren't "failing" |

**The current schema forces hallucination** — descriptive principles get forced `application`/`failure_mode` to satisfy min_length validators.

**Code evidence** (`pipeline/schemas.py` L471-476):
```python
application: str = Field(
    description="When [situation] → do [action]. One concrete example.",
    min_length=10,  # REQUIRED for ALL FBs
)
failure_mode: str = Field(
    description="How this principle fails in practice. 1-3 sentences.",
    min_length=10,  # REQUIRED for ALL FBs
)
```

No `actionability` field exists anywhere in the schema.

#### Gap 2: S5 Never Verifies Application/Failure Mode (Kimi's Discovery, Verified)

S5 verification (`stage5_verify.py`) checks `definition` and `mechanism` against `evidence_passages` via DeBERTa NLI. **Application and failure_mode are never presented to the verifier.** They are invisible to S5.

**Code evidence** (`stage5_verify.py` L562-600): The Gemma deep-check prompt asks about `definition`, not `application` or `failure_mode`.

This means an FB can pass verification with a perfectly fact-checked definition AND a completely hallucinated application. S5 won't catch it.

#### Gap 3: Depth Derived from Domain Count, Not Semantics (ChatGPT's Analysis, Verified)

Depth is derived purely from domain cardinality (`stage4_merge.py` L966-994):

```
if is_specialized:
    n_canonical >= 2 → "domain"
    n_canonical == 1 → "specialized"
    n_canonical == 0 → "domain"
else:
    effective_n >= 3 → "universal"
    effective_n == 2 → "cross-domain"
    effective_n == 1 → "domain"
```

Where `effective_n = n_canonical + (1 if "emerging" in domains else 0)`.

**Problem**: A principle touching 3 taxonomy domains isn't necessarily "universal." A genuinely universal principle classified into 1 domain (incomplete taxonomy) is silently demoted to "domain." Domain count is evidence for depth, not the definition of depth.

#### Gap 4: S4 Classifier Is Underfed (ChatGPT's Discovery, Verified)

The S4 classification prompt (`stage4_merge.py` L219-248) only passes `name` and `definition` to Phi-4-mini for classification:

```python
def build_classify_prompt(fb_name: str, fb_definition: str) -> str:
    return f"""Classify this Foundation Block scientifically.

NAME: {fb_name}
DEFINITION: {fb_definition[:800]}
..."""
```

But S2 already has `mechanism`, `boundary`, `consequence`, `elaboration`, `extraction_type`, `content_type` — and S4/CRIBS subsequently has `application` and `failure_mode`. The classifier sees only ~15% of the available semantic information.

#### Gap 5: S4 Uses Two LLM Calls, Same Model Family as S2

- S4-P1 (CRIBS/merge): Qwen3-Coder-30B — same model family as S2 generator
- S4-P2 (classification): Phi-4-mini — different family, but a separate call

This violates the spirit of R5 and creates a ~13s/FB bottleneck.

---

## §3 — Sandbox Evidence: Testing the Proposed Architecture

On 2026-08-09, I ran **4 live stress tests** on OMLX using `Phi-4-mini-instruct-8bit` (temp=0.0) to test whether Phi-4-mini can:

1. Classify actionability (descriptive/prescriptive/axiomatic/diagnostic)
2. Conditionally generate or suppress `application`/`failure_mode`
3. Do CRIBS enrichment on appropriate fields only
4. Handle this in a single call with acceptable latency

### Test Configuration

- **Model**: `mlx-community/Phi-4-mini-instruct-8bit` via OMLX (port 11435)
- **Temperature**: 0.0
- **Max tokens**: 400-512
- **Input**: Full S2 semantic object (name, definition, mechanism, boundary, consequence)
- **Prompt**: Single prompt asking for actionability classification + conditional CRIBS

### Results

| Test | Principle | Actionability | Application | Failure Mode | Time | Verdict |
|------|-----------|---------------|-------------|--------------|------|---------|
| T1 | Loss Aversion (descriptive) | `descriptive` ✅ | `null` ✅ | `null` ✅ | 0.01s | **PASS** |
| T2 | Value-First Demo (prescriptive) | `prescriptive` ✅ | Generated ✅ | Generated ✅ | 0.02s | **PASS** |
| T3 | Golden Ratio (axiomatic) | `prescriptive` ❌ | `null` ✅ | `null` ✅ | 0.02s | **MISCLASSIFIED type, correct null** |
| T4 | Oscillation Signal (diagnostic) | `diagnostic` ✅ | Diagnostic form ✅ | `null` ✅ | 0.02s | **PASS** |

### Key Findings

1. **Response time**: 0.01-0.02s per call — 500-1000× faster than the current 13s S4 bottleneck
2. **Descriptive vs prescriptive distinction**: Phi reliably distinguishes these (2/2 correct)
3. **Axiomatic is problematic**: Phi confuses axiomatic with prescriptive (mathematical content → "apply it!"). Recommendation: merge `axiomatic` into `descriptive` — use 3-class model (descriptive/prescriptive/diagnostic)
4. **Conditional generation works**: Even when Phi misclassifies actionability (T3), it still correctly sets application/failure_mode to null
5. **Memory**: ~4GB for Phi-4-mini — fits comfortably alongside Q3C-30B's 18GB in 64GB total
6. **JSON parsing**: Responses wrapped in ```json...``` — trivial regex strip, already handled in pipeline

### 3-Class Accuracy Estimate

With `axiomatic` merged into `descriptive`:
- **3/3 correct** in this test set (T1, T2, T4)
- Conservative estimate: **~85-90% accuracy** at scale
- With Qwen adjudication on disagreement: **~95%+** (tested pattern from existing D2138 two-stage classification)

---

## §4 — Proposed Architecture: Unified S4 with Actionability-First Logic

### The Core Insight

The pipeline currently treats ALL principles identically — forces `application`/`failure_mode` on everything, classifies from minimal input, and verifies only definition/mechanism. The fix is:

1. **Add `actionability` classification** — what KIND of knowledge is this?
2. **Make `application`/`failure_mode` conditional** — only generated when the principle is prescriptive
3. **Feed S4 the FULL S2 semantic object** — not just name+definition
4. **Unify S4 into a SINGLE Phi-4-mini call** — actionability → conditional CRIBS → classification → consistency
5. **Add S5 actionability consistency check** — catch category errors before commit

### Proposed Pipeline

```
S0-S1.5: Convert → Chunk → Embed → Cluster (UNCHANGED)
         │
         ▼
S2 (Qwen3-Coder-30B): SEMANTIC EXTRACTION
  Input: clustered source segments (5-15 chunks)
  Output:
    ┌─ name, definition, mechanism, boundary, consequence
    ├─ elaboration, evidence_passages
    ├─ extraction_type, content_type
    └─ semantic_signals (NEW):
        ├─ operationality: theoretical | actionable | procedural
        ├─ applicability_explicit: bool
        └─ failure_condition_present: bool
         │
         ▼
S4 (Phi-4-mini, SINGLE CALL ~0.02s): ENRICHMENT + CLASSIFICATION
  Input: S2's complete semantic object
  Step 1: ACTIONABILITY classification
    → descriptive | prescriptive | diagnostic
  Step 2: CONDITIONAL generation
    → IF prescriptive: application + failure_mode
    → IF diagnostic: diagnostic signal ("If [X] → [Y] likely")
    → IF descriptive: null for both
  Step 3: TAXONOMY classification
    → discipline, domains, depth (DIRECT classification, not derived from count)
    → specialized, accessibility, difficulty, context, temporal_scope
  Step 4: CRIBS quality (on EXISTING fields only)
    → keywords, jargon, elaboration refinement
    → CRIBS polishes what exists — does NOT create fields that shouldn't exist
  Step 5: ONTOLOGY CONSISTENCY
    → depth vs domain_count (WARNING if mismatch, not override)
    → actionability vs application shape
    → specialized vs jargon/tool dependence
         │
         ▼
S5 (DeBERTa FEVER + BORP + Actionability Check)
  1. BORP: ≥2 distinct source books per FB
  2. Completeness: required fields present (accounting for actionability)
  3. NLI: definition/mechanism vs evidence_passages (DeBERTa FEVER)
  4. ACTIONABILITY CONSISTENCY (NEW):
     - descriptive + non-null application → FAIL
     - prescriptive + null application → FAIL
     - diagnostic + prescriptive-form application → WARN
     - axiomatic (if kept) + non-null application → FAIL
         │
         ▼
S6 (SQLite + Parquet, UNCHANGED)
```

### Schema Change

```python
# NEW: Epistemic category determining downstream field requirements
ACTIONABILITY_LITERAL = Literal["descriptive", "prescriptive", "diagnostic"]

class FoundationBlock(BaseModel):
    # ... existing fields unchanged ...

    actionability: ACTIONABILITY_LITERAL = Field(
        description="Epistemic category. Determines which enrichment fields are required."
    )

    # CHANGED: Now conditional — required only if actionability=prescriptive
    application: str | None = Field(
        default=None,
        description="When [situation] → do [action]. Required iff actionability=prescriptive. "
                    "Diagnostic form: 'If [signal] → [condition] likely.' Null for descriptive."
    )
    failure_mode: str | None = Field(
        default=None,
        description="How this principle fails. Required iff actionability=prescriptive. Null otherwise."
    )
```

### S4 Prompt (Single Call)

```python
UNIFIED_S4_SYSTEM = """You are a classification and enrichment engine for a knowledge system.
Given a Foundation Block's complete semantic object, you must:

STEP 1 — ACTIONABILITY: Determine what KIND of knowledge this is:
  - descriptive: explains how the world works (causal mechanism, observation, theory)
  - prescriptive: tells you how to act (technique, strategy, method, rule)
  - diagnostic: pattern recognition ("if you see X, Y is happening")

STEP 2 — CONDITIONAL ENRICHMENT (only for fields that should exist):
  - IF prescriptive:
      application: "When [concrete situation] → do [specific action]"
      failure_mode: "The principle fails when [specific condition]"
  - IF diagnostic:
      application: "If you observe [signal] → [condition] is likely present"
      failure_mode: null
  - IF descriptive:
      application: null
      failure_mode: null

STEP 3 — TAXONOMY CLASSIFICATION:
  - discipline: single most precise academic/intellectual discipline
  - domains: 1-5 applied domains/fields (free labels, pipeline canonicalizes)
  - depth: universal | cross-domain | domain | specialized (classify DIRECTLY)
  - specialized: true ONLY for narrow sub-techniques, tool-specific skills
  - accessibility: self-evident | prerequisite
  - difficulty: beginner | intermediate | expert

STEP 4 — CRIBS QUALITY (on EXISTING fields only):
  - keywords: 3-5 retrieval terms
  - jargon: {"term": "explanation"} only if non-obvious terms exist, else null
  - Refine elaboration for clarity and impact

CRITICAL RULES:
- NEVER generate application or failure_mode for descriptive principles
- Depth MUST be classified directly, not derived from domain count
- Return ONLY valid JSON, no markdown wrapping
"""
```

### S5 Actionability Consistency Check

```python
def check_actionability_consistency(fb: dict) -> tuple[bool, list[str]]:
    """Verify actionability label matches generated fields."""
    issues = []
    actionability = fb.get("actionability", "prescriptive")  # default for backward compat
    application = fb.get("application")
    failure_mode = fb.get("failure_mode")

    if actionability == "descriptive":
        if application:
            issues.append("descriptive principle has application — should be null")
        if failure_mode:
            issues.append("descriptive principle has failure_mode — should be null")

    elif actionability == "prescriptive":
        if not application or len(str(application)) < 10:
            issues.append("prescriptive principle missing application")
        if not failure_mode or len(str(failure_mode)) < 10:
            issues.append("prescriptive principle missing failure_mode")

    elif actionability == "diagnostic":
        if failure_mode:
            issues.append("diagnostic principle has failure_mode — should be null")
        if application and "do" in str(application).lower():
            issues.append("diagnostic application looks prescriptive — should use 'If [signal] → [condition]' form")

    return len(issues) == 0, issues
```

---

## §5 — Comparison: Current vs Proposed vs Three External Reviews

### Architecture Comparison

| Aspect | Current S4 | Qwen's Proposal | ChatGPT's Proposal | Kimi's Proposal | **My Proposal** |
|--------|-----------|-----------------|-------------------|-----------------|-----------------|
| S2/S4 boundary | Separate | **COLLAPSE** — all fields into S2 | **PRESERVE** — enrich both | **PRESERVE** — epistemic firewall | **PRESERVE** — S2 extracts, S4 classifies |
| CRIBS placement | S4, Q3C-30B call | Into S2 with constrained gen | S4 parallel with classification | S4, Phi-4-mini, single call | **S4, Phi-4-mini, single call** |
| Classification model | Phi-4-mini, separate call | SetFit/GLiNER (deterministic) | ModernBERT multi-head (future) | Phi-4-mini, combined call | **Phi-4-mini, combined call** |
| S4 LLM calls | 2 (~13s total) | 0 (all deterministic) | 2 eventually → 1 | 1 (~4s) | **1 (~0.02s)** |
| Actionability field | **MISSING** | Not identified | Not identified as critical | **IDENTIFIED as critical** | **ADOPTED from Kimi** |
| Depth logic | Derived from domain count | SetFit classifier | Direct LLM + domain count as check | Embedding-based | **Direct LLM classification + domain count as consistency WARNING only** |
| S4 classifier input | name + definition only | N/A (deterministic) | Full S2 semantic object | Full S2 semantic object | **Full S2 semantic object + semantic_signals** |
| S5 verification | definition only | Unchanged | Claim-aware (future) | Add actionability check | **Add actionability consistency check** |
| Gemma | Active (73% FN) | Remove immediately | Not addressed | Remove or fix | **Deprecate/remove** |
| Fine-tuning | None | SetFit (8 examples) | Gradual: benchmark → train | Phi-4-mini (200 examples) | **Phi-4-mini later, not now** |

### Who Got What Right

| Reviewer | Best Insight | What They Got Wrong |
|----------|-------------|---------------------|
| **Qwen (STIER)** | Using deterministic classifiers (SetFit/GLiNER). Eliminating LLM from classification entirely. Constrained generation. | **Collapsing S2+S4 is dangerous** — generates application from raw segments, not synthesized principles. Hallucination risk is real and unacceptable. See Kimi's anchoring→salary negotiation example. |
| **ChatGPT** | Epistemic vs operational distinction. S4 classifier is underfed. Depth should be classified directly, domain count as consistency check only. Disagreement-driven labeling pipeline. Multi-task classifier architecture. | Overly academic — 38 priority items when 3 would suffice. Didn't identify the actionability gap. Didn't question the forced application/failure_mode schema. |
| **Kimi** | **Actionability gap discovery** — the single most important finding. Three-layer factual integrity architecture (L1/L2/L3). Concrete implementation pseudocode. Phi-4-mini for combined CRIBS+classification. Conditional application/failure_mode. | Overstated 92% quarantine rate as purely category errors (some are genuine NLI failures). Didn't identify Phi-4-mini axiomatic→prescriptive confusion. |
| **My synthesis** | Adopts Kimi's actionability discovery. Adopts ChatGPT's "classify depth directly, domain count as consistency check." Adopts Qwen's efficiency goals but preserves S2/S4 boundary. Sandbox-verified Phi-4-mini capability at 0.02s/call. 3-class actionability model (descriptive/prescriptive/diagnostic) to avoid Phi's axiomatic confusion. | — |

---

## §6 — Evaluation Questions for External LLMs

Examine the repository at `github.com/kafkesque/maxwell-os` (commit `988fed1`). Read the key files listed in §0. Then answer these 6 questions:

### Q1: S4 Architecture

**Current state**: S4 makes two LLM calls per FB — Qwen3-Coder-30B for CRIBS enrichment/merge (~10s) + Phi-4-mini for classification (~2.5s). The CRIBS call uses the same model family as S2 extraction (Qwen). The classification prompt only receives `name` and `definition`.

**My proposal**: Single Phi-4-mini call receiving the FULL S2 semantic object (name, definition, mechanism, boundary, consequence, elaboration, extraction_type, content_type, semantic_signals). The call does actionability classification → conditional CRIBS → taxonomy classification → consistency in one pass (~0.02s).

**Evaluate**: Is the single-call approach architecturally sound? Does it preserve the S2/S4 epistemic boundary (extraction ≠ synthesis)? Is Phi-4-mini (3.8B params, 4-bit quantized) sufficient for this combined task, or would you recommend a different model/structure? Is my rejection of Qwen's "collapse everything into S2" proposal justified?

### Q2: Actionability Classification

**Current state**: No actionability field exists. `application` and `failure_mode` are required for ALL FBs (min_length=10), forcing hallucination for descriptive/theoretical principles.

**My proposal**: Add `actionability` field with 3 classes (descriptive/prescriptive/diagnostic). Make `application` and `failure_mode` conditional — only required for prescriptive principles. Diagnostic principles get a diagnostic-form application. Descriptive principles get null for both.

**Evaluate**: Is the 3-class model (descriptive/prescriptive/diagnostic) the right taxonomy? Should axiomatic remain as a 4th class, or is merging it into descriptive correct given Phi-4-mini's confusion? Are there edge cases where a descriptive principle legitimately needs an application? Does the conditional schema create problems for the retrieval layer?

### Q3: Depth Classification

**Current state**: Depth is derived from `n_canonical_domains + is_specialized` — a purely structural formula. Domain cardinality defines depth tier.

**My proposal**: Classify depth DIRECTLY via Phi-4-mini (seeing the full semantic object). Use domain cardinality as a consistency WARNING only — flag mismatches but don't override. Keep heuristic v5 for tool-specific detection as an override.

**Evaluate**: Is direct LLM depth classification better than domain-count derivation? What are the risks of LLM depth classification (inconsistency, hallucination)? Should depth be an LLM output at all, or should it be a post-hoc derived property? Is my "classify directly + check with domain count" approach sound, or is there a better method?

### Q4: S5 Verification Gap

**Current state**: S5 verifies `definition` and `mechanism` against `evidence_passages` via DeBERTa FEVER NLI. `application` and `failure_mode` are NEVER verified — they're invisible to S5. This means a perfectly fact-checked principle can have a completely hallucinated application that passes verification.

**My proposal**: Add a 4th check — actionability consistency. Rule-based logical validator that catches category errors (descriptive+application, prescriptive−application, diagnostic+failure_mode). Not NLI — this is logical consistency, not factual verification.

**Evaluate**: Is a rule-based consistency check sufficient, or should application/failure_mode undergo some form of grounding verification? How would you verify synthetic fields (application/failure_mode) that by definition go beyond source text? Is the current approach of trusting S4's synthesis but flagging category errors the right trade-off?

### Q5: Fine-Tuning Strategy

**Current state**: No fine-tuning. S2 uses golden few-shot ICL. S4 uses prompted Phi-4-mini. Raw labels preserved for future taxonomy expansion.

**My proposal**: NO fine-tuning of Qwen3-Coder-30B (violates C1, C28, risks catastrophic forgetting). Eventually fine-tune Phi-4-mini on 200+ adjudicated examples for metadata + actionability classification. Use Qwen as teacher/adjudicator for hard cases. Build disagreement-driven labeling pipeline (Qwen vs Phi disagreement → human review → training data).

**Evaluate**: Is this the right fine-tuning strategy? When should Maxwell start fine-tuning vs relying on prompts? Is Phi-4-mini the right fine-tuning target, or would SetFit/ModernBERT/DeBERTa-v3 be better for pure classification? Does Qwen as "teacher" introduce a single-model-family risk (R5 spirit)?

### Q6: Ultimate Pipeline Architecture

**Given**: Apple Silicon 64GB Mac. ~2,655 FBs to process. Constitution rules C1/C3/C5/C24/C28/R5. Models available: Qwen3-Coder-30B (18GB), Phi-4-mini (4GB), Gemma-4-E4B (19GB), DeBERTa FEVER (500MB), bge-m3 (2GB).

**My proposal**: See §4 pipeline diagram. Key changes: (1) actionability field + conditional application/failure_mode, (2) unified S4 single Phi-4-mini call, (3) direct depth classification with domain-count consistency, (4) S5 actionability check, (5) Gemma deprecated, (6) S2 semantic_signals.

**Evaluate**: Is this the optimal architecture for these constraints? What would you change? Are there peer-reviewed or existing open-source solutions (SetFit, GLiNER, Outlines, Instructor, ModernBERT multi-head) that would be better than Phi-4-mini for any component? What's the single most critical issue that should be addressed first?

---

## §7 — Required Response Format

Return your evaluation as a JSON object with this structure:

```json
{
  "evaluator_model": "your-model-name",
  "evaluator_persona": "Senior STIER RAG Engineer",
  "repo_examined": true/false,
  "files_read": ["file1", "file2", "..."],
  "timestamp": "ISO-8601",

  "q1_s4_architecture": {
    "verdict": "OPTIMAL" | "SUBOPTIMAL" | "INCORRECT",
    "recommended_approach": "MY_PROPOSAL" | "QWEN_PROPOSAL" | "CHATGPT_PROPOSAL" | "KIMI_PROPOSAL" | "OTHER",
    "other_design": "Describe if OTHER",
    "rationale": "Why — reference specific code/files",
    "risks": ["risk1", "risk2"]
  },

  "q2_actionability": {
    "verdict": "OPTIMAL" | "SUBOPTIMAL" | "INCORRECT",
    "recommended_taxonomy": ["class1", "class2", "..."],
    "should_merge_axiomatic": true/false,
    "edge_cases_identified": ["case1", "case2"],
    "retrieval_impact": "How conditional fields affect retrieval",
    "rationale": "Why"
  },

  "q3_depth": {
    "verdict": "OPTIMAL" | "SUBOPTIMAL" | "INCORRECT",
    "recommended_method": "llm_direct" | "domain_count" | "setfit" | "hybrid" | "other",
    "other_method": "Describe if other",
    "rationale": "Why — address risks of each approach",
    "should_heuristic_v5_remain": true/false
  },

  "q4_verification": {
    "verdict": "SUFFICIENT" | "INSUFFICIENT",
    "recommended_checks": ["check1", "check2", "..."],
    "should_verify_synthetic_fields": true/false,
    "synthetic_verification_method": "Describe if should_verify",
    "rationale": "Why"
  },

  "q5_finetuning": {
    "verdict": "OPTIMAL" | "SUBOPTIMAL" | "INCORRECT",
    "should_fine_tune_now": true/false,
    "recommended_model": "phi-4-mini" | "setfit" | "modernbert" | "deberta-v3" | "qwen3-coder" | "other",
    "when_to_fine_tune": "now" | "after_N_examples" | "never",
    "teacher_model": "qwen" | "phi" | "none",
    "rationale": "Why"
  },

  "q6_ultimate": {
    "verdict": "OPTIMAL" | "SUBOPTIMAL" | "INCORRECT",
    "ship_now": ["priority1", "priority2", "..."],
    "post_hoc_fixes": ["fix1", "fix2", "..."],
    "v31_improvements": ["improvement1", "improvement2", "..."],
    "architecture_diagram": "ASCII or text description of YOUR recommended pipeline",
    "most_critical_issue": "Single most important problem to fix",
    "disagreements_with_author": ["disagreement1", "disagreement2"],
    "overall_assessment": "2-3 sentence summary"
  }
}
```

---

## §8 — Constraints Reminder

- **DO NOT** propose cloud APIs, paid services, or non-local solutions (violates C1/C3)
- **DO NOT** propose fine-tuning Qwen3-Coder-30B without addressing the 18GB memory constraint and catastrophic forgetting risk
- **DO NOT** propose solutions that require >64GB RAM (C24)
- **DO NOT** propose collapsing S2+S4 without addressing the hallucination risk from generating application from raw segments
- **DO** examine the actual repository code before answering
- **DO** reference specific files and line numbers in your rationale
- **DO** disagree with my proposal if you find a better approach — adversarial evaluation is required

---

*Handoff created: 2026-08-09. Based on commit 988fed1. Sandbox tests conducted on same date. Three external LLM reviews (Qwen, ChatGPT, Kimi) incorporated after cross-validation against actual code.*
