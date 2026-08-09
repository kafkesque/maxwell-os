# Maxwell OS v3.0 — LLM Roundtable Master Prompt

> **Handoff for external LLM evaluation. DO NOT answer these questions yourself.**
> **This is an instruction set for OTHER LLMs to investigate, examine the repo, and return their independent verdict.**

---

## INSTRUCTIONS FOR EVALUATING LLMs

You are evaluating the Maxwell OS v3.0 knowledge pipeline — a local-first, sovereign RAG system running on Apple Silicon (64GB RAM). Your task:

1. **Clone and examine the repo**: `git@github.com:kafkesque/maxwell-os.git` (branch: `main`, commit: `d4b243e`)
2. **Read the key files** listed below
3. **Investigate the problems and proposed solutions** described below
4. **Return your independent JSON verdict** for each question — do NOT defer to the author's opinion

### Key Files to Examine

| File | Purpose |
|------|---------|
| `CONSTITUTION.md` | Architectural rules, pipeline design |
| `DECISION-LOG.md` | All architectural decisions D2000-D2216 |
| `pipeline/stage2_extract.py` | S2 convergent extraction (Q3C-30B) |
| `pipeline/stage4_merge.py` | S4 merge + classify (2 LLM calls currently) |
| `pipeline/stage5_verify.py` | S5 verification (NLI + BORP + completeness) |
| `pipeline/pipeline_paths.py` | All model/config constants |
| `pipeline/schemas.py` | FB schema, taxonomy, canonical labels |
| `config/pipeline_config.yaml` | All thresholds, models, pipeline settings |
| `governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md` | NLI model comparison results |
| `governance/ROUNDTABLE_MASTER_PROMPT.md` | Prior roundtable evaluation framework |
| `governance/COMPREHENSIVE_AUDIT_2026-08-09.md` | Full system audit |

### Constraints (from CONSTITUTION.md)
- **C1**: $0 marginal cost — all compute on local hardware
- **C3**: Sovereign — no cloud APIs, all data local
- **R5**: Generator ≠ Verifier — different model families
- **C12**: No hardcoded values — everything in config/*.yaml
- **C24**: Hardware-adaptive — auto-detect RAM, degrade gracefully
- **C28**: Quality-tiered — lightweight default, bloat opt-in

---

## PIPELINE OVERVIEW

```
S0: EPUB/PDF → Markdown
S1: Chunk → segments
S1.5: Embed (bge-m3/Ollama) → FAISS cosine + Louvain clustering
S2: Qwen3-Coder-30B extracts convergent Foundation Blocks (mechanism/boundary/consequence/elaboration/evidence_passages)
S3: REMOVED (D2120/D2198 — HDBSCAN dedup replaced by cluster-before-extract)
S4: MERGE (Q3C-30B generates app/failure/keywords/jargon) + CLASSIFY (Phi-4-mini-8bit labels discipline/domains)
S5: DeBERTa FEVER NLI verification + BORP source diversity + completeness check
S6: SQLite (sqlite-vec) + Parquet commit
```

**Current state**: 2,655 convergent FBs extracted. ~10,000 single-source pending.

---

## PROBLEMS DISCOVERED DURING AUDIT SESSION (2026-08-09)

### 1. Elaboration Bug (D2215)
`_build_fb_from_result` in `stage2_extract.py` was not copying `elaboration` from LLM output. **2,652 FBs have empty elaboration.** Fix applied to code. Repair script ready: `pipeline/repair_elaboration.py`. Not yet run.

### 2. ModernBERT NLI Useless for S5
ModernBERT (`tasksource/ModernBERT-base-nli`) returns NEUTRAL ~0.4 on ALL synthesized FBs — 0% pass rate, 0.26 bits entropy. Cannot discriminate between well-supported and unsupported principles. **Config swapped**: DeBERTa-v3-base-mnli-fever-anli (362MB) as primary. DeBERTa FEVER: 1.51 bits entropy, 35% pass, binary PASS/FAIL signal. 5.8× more discriminative. Tested on 46 stratified FBs.

### 3. Gemma-4-E4B Verifier 73% False Negative
Gemma-4-E4B-it-MLX-4bit (19GB) rejects synthesized principles because it demands verbatim evidence. 11/15 FBs incorrectly flagged as inconsistent. **Model is still active** as `verifier_v2` but of questionable utility. DeBERTa FEVER handles the NLI pre-filter; Gemma is only called for deep LLM escalation.

### 4. S4 Merge Bottleneck (2 LLM calls per FB)
Current S4: Q3C-30B merge (~10s) + Phi-4-mini classify (~2.5s) = ~13s per FB. For 2,655 FBs: ~9.7 hours.

**Proposed Approach D**: Eliminate Q3C merge call. Replace with:
- **Template**: application ← mechanism (regex extractive), failure_mode ← boundary (regex extractive)
- **Single Phi-4-mini call**: discipline + domains + is_specialized + keywords + jargon (when needed)
- **Heuristic v5**: Programmatic tool-signal detection overrides LLM is_specialized flag (only for explicit tool names like Max/MSP, Altair, Docker — NOT generic patterns)

**Benchmark (12 FBs)**:
| Approach | LLM calls | Time/FB | Keywords | Jargon | Depth accuracy |
|----------|----------|---------|----------|--------|---------------|
| A: 2-LLM (current) | 2 | 13.2s | 🟢 LLM | 🟢 LLM | 75% |
| D: Classify+KW+Template | 1 | ~3.0s | 🟢 LLM | 🟢 LLM | ~83% |

For 2,655 FBs: Approach D = ~2.2 hours (4.4× faster).

### 5. Depth Classification Logic
**Kimi D2139**: `depth = f(n_canonical_domains, is_specialized_flag)`
```python
if is_specialized:
    n_canonical >= 2 → domain
    n_canonical == 1 → specialized  
    n_canonical == 0 → domain
else:
    effective_n = n_canonical + (1 if "emerging" in domains else 0)
    effective_n >= 3 → universal
    effective_n == 2 → cross-domain
    effective_n <= 1 → domain
```

**Problem**: If LLM misclassifies `is_specialized` or `domains`, depth cascades into wrong value. Example: Patch Cord (Max/MSP tool technique) often classified as `is_specialized=False` → gets `cross-domain` instead of `specialized`. Heuristic v5 fixes tool-specific cases but doesn't address other classification errors.

### 6. Failed FBs — No Recovery Path
22/24 test FBs fail S5 verification (FAIL or MARGINAL). Current pipeline: FAIL → QUARANTINE → human review. **No automated correction or repair mechanism exists.**

### 7. Taxonomy Gaps
~30% of Phi-4-mini's raw domain labels have no canonical match → mapped to "emerging". The 48-discipline, ~100-domain taxonomy may need expansion.

### 8. Missing Fields in S2 Output
S2 checkpoint has `mechanism`/`boundary`/`consequence` (v3.0) but NOT `application`/`failure_mode`/`keywords`/`jargon`. These are supposed to be generated by S4 merge. S4 merge has never been run on the 2,655 FBs.

### 9. Classification Model Availability
OMLX server must have BOTH Q3C-30B (S2 extraction) and Phi-4-mini-8bit (S4 classification) loaded. Phi-4-mini was in `models_stashed/` and had to be restored. Current OMLX config: `omlx serve --port 11435 --memory-guard-gb 55 --max-concurrent-requests 3 --no-hf-cache`.

---

## ROUNDTABLE QUESTIONS FOR EVALUATING LLMs

**Examine the repo. Read the code. Then answer ALL of the following in a single JSON response.**

### Q1: S4 Architecture — Is Approach D Optimal?
Examine `pipeline/stage4_merge.py` lines 850-1150 (merge + classify flow). Compare Approach A (current 2-LLM) against Approach D (1-LLM + templates). Evaluate:
- Does template-based application/failure_mode sacrifice quality? Is the trade-off acceptable?
- Is there a BETTER architecture? (Multi-task single model? Batch classification? Fine-tuned small model? Speculative decoding?)
- What would YOU build for this specific task on Apple Silicon 64GB?

### Q2: Failed FB Correction
Examine `pipeline/stage5_verify.py` lines 440-575 (status determination). 22/24 FBs fail S5. No recovery exists. Research and recommend:
- What peer-reviewed methods exist for automatic knowledge graph extraction repair?
- Options: RAG repair, fact-check-and-remove, self-consistency voting, constrained decoding, re-extraction with improved prompt
- Which is most viable for a local-only, sovereign system with no cloud APIs?
- Should Maxwell build a repair step? If so, what design?

### Q3: Depth Classification
Examine `pipeline/stage4_merge.py` lines 967-997 (depth derivation). Evaluate Kimi D2139 logic:
- Is deriving depth from domain count the right approach, or should the LLM classify depth directly?
- What peer-reviewed methods exist for hierarchical scope/depth classification?
- Options: Zero-shot NLI, SetFit few-shot, hierarchical label trees, embedding-based, LLM direct
- Which approach adds the LEAST complexity and fewest new failure modes?

### Q4: NLI Verifier Swap
Examine `governance/DEBERTA_VERIFICATION_TEST_2026-08-09.md`. DeBERTa FEVER was swapped as primary NLI replacing ModernBERT. Evaluate:
- Is this swap justified by the benchmark data? (ModernBERT: 0% pass, 0.26 bits. DeBERTa FEVER: 35% pass, 1.51 bits)
- Should Gemma-4-E4B (19GB, 73% FN rate) remain as `verifier_v2` or be replaced?
- Is there a better verification model for a local-only pipeline?

### Q5: Fine-Tuning Strategy
Given 28 convergent golden FBs in `config/golden/stage2_fewshot_convergent.yaml`:
- Should Maxwell fine-tune a model for S4 classification? If yes, which model and how many examples needed?
- Does fine-tuning violate constitutional rules (C2: no lock-in, C4: open formats)?
- What's the minimum viable fine-tuning approach for $0 marginal cost?

### Q6: Ultimate v3.0 Architecture
Synthesize everything. What is the optimal S2-S5 pipeline for v3.0?
- What ships NOW with current code?
- What needs post-hoc fix on existing 2,655 FBs?
- What goes to v3.1 development?
- Prioritize by impact/cost ratio.

---

## OUTPUT FORMAT

```json
{
  "evaluator_model": "name of the model providing this evaluation",
  "repo_examined": true,
  "files_read": ["list of files actually examined"],
  "q1_architecture": {
    "verdict": "OPTIMAL|ADEQUATE|SUBOPTIMAL",
    "recommended_approach": "A|D|OTHER",
    "other_design": "if OTHER, describe your proposed architecture",
    "rationale": "detailed reasoning with code references"
  },
  "q2_failed_fb": {
    "best_method": "name of recommended approach",
    "implementation_design": "how to build it in Maxwell's constraints",
    "rationale": "why this method over alternatives"
  },
  "q3_depth": {
    "recommended_method": "keep_kimi_d2139|llm_direct|setfit|nli_zero_shot|embedding|other",
    "rationale": "detailed reasoning"
  },
  "q4_verification": {
    "deberta_swap_justified": true,
    "gemma_recommendation": "keep|replace|remove",
    "better_verifier": "model name or null",
    "rationale": "detailed reasoning"
  },
  "q5_finetuning": {
    "should_fine_tune": true,
    "model": "recommended model",
    "task": "classification|field_generation|both",
    "examples_needed": 0,
    "constitutional": true,
    "mvp_approach": "description",
    "rationale": "detailed reasoning"
  },
  "q6_ultimate": {
    "ship_now": ["item1", "item2"],
    "post_hoc_fixes": ["item1", "item2"],
    "v31_improvements": ["item1", "item2"],
    "architecture_diagram": "text description of optimal flow",
    "rationale": "detailed reasoning"
  },
  "most_critical_issue": "the single biggest problem to fix first",
  "overall_assessment": "1-2 paragraph summary of pipeline health and recommendations",
  "disagreements_with_author": "any points where you disagree with the proposed Approach D or other design choices"
}
```

**IMPORTANT**: Do NOT simply agree with Approach D. Challenge it if you find weaknesses. Cite specific lines of code. Propose concrete alternatives. This is an adversarial review.
