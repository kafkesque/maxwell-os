# Maxwell OS v3.0 — Comprehensive System Audit (2026-08-11)
> **Triggered by:** D2254 cross-examinations (8 LLM responses, 2 rounds)  
> **Method:** Every claim verified against actual source files — configs, scripts, governance docs, golden YAML, decision log, buglog.  
> **Standard:** No assumption. No deference. Source-ground-truth only.

---

## PART 1: MODEL AUDIT — WHAT'S ACTUALLY RUNNING

### 1A. Pipeline Models (from `config/pipeline_config.yaml`)

| Role | Config Model | Actually Running? | Notes |
|------|-------------|-------------------|-------|
| Generator (S2) | `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` | ✅ Yes | Docstring says Qwen3.6-35B — drift |
| Verifier (S4) | `gpt-oss-20b-MXFP4-Q8` | ✅ Yes | Replaced Phi-4-mini (D2249/D2250) |
| VerifierV2 (S5) | `gemma-4-E4B-it-MLX-4bit` | ✅ Yes | Not the retired Gemma-4-31B |
| Embeddings | `bge-m3` | ✅ Yes | Ollama |

### 1B. Models Claimed in Governance But NOT in Pipeline Config

| Model | Handoff/Docs Claim | Actual Status |
|-------|-------------------|---------------|
| **Phi-4-mini-instruct-8bit** | "S5 verify/gates" (HANDOFF_D2254) | ❌ NOT in pipeline models config. Only in: `smoke.fast.fast_model` (test mode), `config/model_assignments.yaml` (agent roles, not pipeline), stale `classify_model` at L1642 (v2.3 checkpoint artifact). **stage5_verify.py docstring still says "Classifier: Phi-4-mini-8bit — Stage 4 Phase 2" which is STALE since D2249.** |
| **Gemma-4-31B-it-MLX-8bit** | "Retired S4 — unload if memory pressure" (HANDOFF_D2254) | ✅ Correctly retired. Different from active Gemma-4-E4B. |

### 1C. MODEL DRIFT FINDINGS

| # | Drift | Source A | Source B | Risk |
|---|-------|----------|----------|------|
| **M1** | Generator model name | `config/pipeline_config.yaml`: Qwen3-Coder-30B | `stage2_extract.py` docstring: Qwen3.6-35B | LOW — may be same model, different naming |
| **M2** | S4 classifier model | `config/pipeline_config.yaml`: gpt-oss-20B | `stage5_verify.py` docstring: "Classifier: Phi-4-mini-8bit" | MEDIUM — stale docstring in active S5 code |
| **M3** | S5 NLI model | `config/pipeline_config.yaml`: ModernBERT primary, DeBERTa fallback | `pipeline/pipeline_paths.py` D2216: DeBERTa FEVER primary, ModernBERT fallback | **🔴 HIGH** — config overrides code, D2216 is dead code |
| **M4** | Phi-4-mini role | `HANDOFF_D2254.md`: "S5 verify/gates" | `config/pipeline_config.yaml`: Not in models section | MEDIUM — handoff claims active role with no config backing |
| **M5** | S4 classifies with what? | `stage5_verify.py` L22: "Classifier: Phi-4-mini-8bit — Stage 4 Phase 2" | `config/pipeline_config.yaml`: `verifier: gpt-oss-20b` | LOW — stale comment, but misleading |

---

## PART 2: GOLDEN SET AUDIT

### 2A. Active Golden Files

| File | Version | Count | IDs | Status |
|------|---------|-------|-----|--------|
| `stage2_fewshot_convergent.yaml` | v4.4 | 73 (55 conv, 18 non-conv) | CONV-xxx, NEG-xxx, NEG-CONV-xxx | ✅ Active S2 calibration |
| `GOLDEN-REVIEW.md` | v2.0 | 75 | LEA-xxx, STR-xxx, DES-xxx, PER-xxx, MGT-xxx | 🔴 0/225 checks completed, never calibrated |
| `stage2_fewshot_trimmed_12.yaml` | v4.1 | 12 | (subset of v4.4) | 🟡 Legacy — unclear if used |
| `evals/golden_cases.json` | — | 52 | (depth classification) | 🟡 14+ probable label errors per ChatGPT v3 audit |

### 2B. Golden Set Integrity Issues

| # | Issue | Detail |
|---|-------|--------|
| **G1** | Meta vs data discrepancy | Meta says `convergent_positives: 36`, actual `is_convergent=True` count is **55**. Meta is stale or counting a subset. |
| **G2** | Two golden sets coexist | v2.0 GOLDEN-REVIEW.md (LEA/STR/DES/PER/MGT IDs) and v4.4 YAML (CONV/NEG IDs) use different ID schemes, different author pools, different calibration status. **Every LLM that read both got confused.** |
| **G3** | Depth class imbalance | universal=1, specialized=1 out of 55 convergent. Cannot calibrate 2 of 4 depth classes. |
| **G4** | Extraction type improved but causal still dominant | causal_mechanism: 24/55 (44%), descriptive_model: 12 (22%), normative_heuristic: 11 (20%), empirical_pattern: 8 (15%). D2234 rebalancing happened but causal still leads. |
| **G5** | 6 convergent examples have NO depth label | These are injected into few-shot with missing `depth` field — but depth was moved to S4 (D2241), so S2 `format_golden_fewshot()` strips depth. This is correct architecture, not a bug. |
| **G6** | No independent verification | v4.4 YAML says "calibrated_date: 2026-08-10" but has never been cross-checked by a second human. The 2 cross-examination rounds found 3 LLMs made material errors reading the same file. |
| **G7** | GOLDEN-REVIEW.md should be archived | 0/225 checks, 28 NEG-HARD references not in active YAML, different author pool. Its presence confuses every tool and reviewer. |

### 2C. Cross-Examination Claim Verification Against Golden Set

| LLM Claim | Source | Verified? | Actual |
|-----------|--------|-----------|--------|
| "55 convergent / 18 non-convergent" | POST_D2254 prompt | ✅ TRUE | is_convergent field count: 55/18 |
| "36 convergent positives" | YAML meta | ⚠️ MISLEADING | Meta says 36 but data says 55 — meta is stale |
| "CONV-039 is critical calibration failure teaching false convergence" | Qwen v3 | ❌ **FALSE** | CONV-039 has `is_convergent: False` — it's a NEGATIVE example |
| "CONV-032 Taleb+Wolfram is category error" | Qwen v3 | ⚠️ DEBATABLE | Marked `extraction_type: descriptive_model`, rationale says "NOT a causal mechanism — it's a TAXONOMY" |
| "NEG-HARD-012 calibration time bomb in active YAML" | Kimi v2 | ❌ **FALSE** | NEG-HARD only exists in GOLDEN-REVIEW.md v2.0, NOT in active v4.4 YAML |
| "Prerequisite_fbs, contradicts_fbs in CONV examples" | Kimi v2 | ❌ **FALSE** | Zero matches in active v4.4 YAML |
| "Author counts: James Clear 4+, Brené Brown 3+" | Kimi v2 | ❌ **FALSE** | From GOLDEN-REVIEW.md v2.0. Active YAML: James Clear=3, Brené Brown=0 |
| "Golden is v4.2 (60 examples)" | Qwen v3 | ❌ **FALSE** | YAML says `version: '4.4'`, 73 examples |
| "format_golden_fewshot() strips depth" | Qwen v3, ChatGPT v3 | ✅ **TRUE** | L637: "# NOTE: Depth removed from S2 (A-001/D2241)" |
| "D2234 rebalancing happened" | ChatGPT v3 | ✅ **TRUE** | YAML meta: "3 descriptive_model examples added (DM 9→12)" |
| "GOLDEN-REVIEW.md: 0/225 checks" | ChatGPT v3 | ✅ **TRUE** | Verified: 225 unchecked, 0 checked |
| "14 label errors in evals/golden_cases.json" | ChatGPT v3 | ⚠️ PROBABLE | Line-by-line audit looks rigorous but requires domain expertise to confirm |

---

## PART 3: CONFIG vs CODE vs DOCS DRIFT AUDIT

### 3A. CRITICAL DRIFTS (runtime-affecting)

| # | Drift | Impact |
|---|-------|--------|
| **D1** | **S5 NLI: Config hardcodes ModernBERT, D2216 promotes DeBERTa FEVER in code** | ModernBERT runs at runtime. DeBERTa FEVER bench (5 FBs) showed ModernBERT "CANNOT verify synthesized principles." D2216 is dead code. **→ All FBs fall through NLI as NEUTRAL → escalate to Gemma (73% FN) → nearly all QUARANTINE.** |
| **D2** | **S5 docstring says "Classifier: Phi-4-mini-8bit — Stage 4 Phase 2"** | Phi retired from S4 (D2249). Docstring is from pre-D2249 architecture. Misleads anyone reading the code about what model does S4 classification. |
| **D3** | **S5 docstring says "DeBERTa NLI entailment" but code loads ModernBERT primary** | Process description (line 13) contradicts actual runtime behavior. The docstring describes the code default (DeBERTa) but the config overrides to ModernBERT. |
| **D4** | **config/pipeline_config.yaml L1642: `classify_model: Phi-4-mini-instruct-8bit`** | Stale — embedded in a v2.3 schema checkpoint configuration block. Not active but present in the config file. |

### 3B. NON-CRITICAL DRIFTS (cosmetic or historical)

| # | Drift |
|---|-------|
| **D5** | stage2_extract.py docstring: "Generator: Qwen3.6-35B-A3B-4bit" vs config "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit" |
| **D6** | HANDOFF_D2254 lists 4 models including Phi-4-mini for "S5 verify/gates" — Phi has no pipeline config role |
| **D7** | HANDOFF_D2254 lists Gemma-4-31B (retired S4) but not Gemma-4-E4B (active S5) — different models |
| **D8** | `stage5_verify.py` docstring line 454: "Run Stage 5: Verify FBs with DeBERTa NLI pre-filter" — stale, runs ModernBERT |

---

## PART 4: VERIFICATION GAP AUDIT

### 4A. S4 Generates Fields S5 Never Verifies

S4 `stage4_merge.py` generates enrichment fields: `application`, `failure_mode`, `elaboration`, `keywords`, `jargon`.

S5 `stage5_verify.py`:
- **BORP check**: Verifies source diversity (≥2 distinct books) ✅
- **Completeness check**: Verifies these fields EXIST (not null) but not their CONTENT ⚠️
- **NLI check**: Compares `definition` ↔ `evidence_passages` — does NOT check application/failure_mode/elaboration ❌
- **Gemma deep check**: Sends `name`, `definition`, `mechanism`, `boundary`, `consequence` to Gemma — does NOT send application/failure_mode/elaboration ❌

**Result:** S4 can generate hallucinated application steps, incorrect failure modes, or fabricated elaboration text — and S5 will pass them as long as they're non-empty strings. The S4 prompt itself says "application: Generate ONLY if this principle is prescriptive...If descriptive/theoretical, set to null" — but if the model generates application for a descriptive principle, S5 won't catch it.

### 4B. The Schema Contradiction (ChatGPT v2 identified this)

The S4 prompt says application should be null for descriptive principles. But the S5 completeness check accepts `application` OR `mechanism` — so a descriptive FB with null application and a mechanism passes. The downstream schema (config/schemas.py?) may require application for every FB, creating pressure to fabricate. **This was flagged by ChatGPT v2 as "the biggest problem — bigger than S4 latency."**

---

## PART 5: DEPENDENCY CHAIN RISK ASSESSMENT

| Risk Chain | Severity | Why |
|------------|----------|-----|
| **S1.5 clustering → S2 yield** | 🔴 HIGH | If clustering fails to group convergent passages, no downstream LLM can recover. faiss_threshold 0.75 may be too tight. No cluster-quality diagnostic has been run. |
| **S5 NLI dead → S5 Gemma 73% FN → S6 commit** | 🔴 HIGH | NLI returns NEUTRAL for all FBs → everything escalates to Gemma → Gemma rejects 73% → knowledge base nearly empty OR S5 bypassed → unverified FBs committed. |
| **Golden depth imbalance → S4 depth classifier** | 🟠 MEDIUM | S4 claims 87.5% depth accuracy but universal=1 and specialized=1 in golden → accuracy measured only on domain/cross-domain. |
| **S4 enrichment gap → S5 no verification → S6** | 🟠 MEDIUM | application/failure_mode/elaboration generated but never verified. Silent hallucination risk. |
| **DSPy hybrid not deployed in production S2** | 🟠 MEDIUM | Comparison harness shows hybrid=0.736, but production stage2_extract.py is traditional-only. The 0.736 metric may not materialize in the full run. |
| **Golden set fragmentation (v2.0 vs v4.4)** | 🟡 LOW | Confuses reviewers and tools. Archive v2.0. |
| **Goose renderer CPU 25%** | 🟡 LOW | Steals 2-3 M1 Max cores during 26h run. Fixable: re-enable MacWebContentsOcclusion. |

---

## PART 6: ALL NEW REVELATIONS (Mined from Both Cross-Examination Rounds)

### NEW BUGS DISCOVERED

| Bug | Source | Status |
|-----|--------|--------|
| **BUG-076**: S5 NLI config overrides D2216 DeBERTa FEVER promotion (dead code) | This audit | 🔴 OPEN — logged 2026-08-11 |
| **BUG-077**: stage5_verify.py docstring triple-stale: says DeBERTa NLI (runs ModernBERT), says Phi-4-mini classifier (retired), says ModernBERT pre-filter (config default) | This audit | 🟠 OPEN |
| **BUG-078**: config/pipeline_config.yaml L1642 contains stale `classify_model: Phi-4-mini-instruct-8bit` in v2.3 checkpoint block | This audit | 🟡 OPEN |
| **BUG-079**: HANDOFF_D2254 model registry lists Phi-4-mini for "S5 verify/gates" — no pipeline config role exists | This audit | 🟡 OPEN |

### CRITICAL MISCONCEPTIONS CORRECTED

| Old Belief | Corrected Fact |
|------------|---------------|
| "Yield crisis: 0.004%" | Number is from v2.0 pipeline on 14 books. 852 = library size, not books run. v3.0 yield never measured. |
| "55 convergent golden examples" | ✅ True (is_convergent field count). But META says 36 — discrepancy unresolved. |
| "71% causal_mechanism" | Stale. After D2234: 44% causal. Distribution improved. |
| "Depth labels missing from S2 few-shot" | By design — depth moved to S4 (D2241). `format_golden_fewshot()` strips depth. |
| "DSPy hybrid deployed in production S2" | Only in comparison harness (`tools/compare_s2_methods.py`). Production `stage2_extract.py` is traditional extraction. |
| "S5 uses DeBERTa NLI" | S5 uses ModernBERT NLI. DeBERTa FEVER is fallback, D2216 primary promotion is dead code. |
| "Phi-4-mini retired from everything" | Retired from S4 classifier. Handoff claims "retained for S5 verify + fast gates" but no pipeline config role exists. Only in smoke test mode + agent assignments. |
| "Gemma retired from pipeline" | Gemma-4-31B (31GB) retired from S4. Gemma-4-E4B (different, smaller model) still active as S5 verifier_v2. |

---

## PART 7: AGGREGATED TASK REGISTER (PRIORITY-ORDERED)

### 🔴 P0 — FIX BEFORE ANY PIPELINE RUN (cumulative ~8-12h)

| # | Task | Effort | Why |
|---|------|--------|-----|
| **P0.1** | **Fix S5 NLI config: swap `nli_model` to DeBERTa FEVER** (or document why not) | 5 min | ModernBERT documented as non-functional for synthesized FBs. D2216 already validated. Config override is the only blocker. |
| **P0.2** | **Run 50-100 book E2E diagnostic** through current v3.0 pipeline | 3-6h | Converts phantom yield crisis into real data. Only way to know if pipeline works. |
| **P0.3** | **Archive GOLDEN-REVIEW.md v2.0** — move to `archive/` | 1 min | Confuses every reviewer. Different ID scheme, different authors, 0/225 checks. |
| **P0.4** | **Fix golden YAML meta: update `convergent_positives: 36` → `55`** | 1 min | Meta disagrees with actual is_convergent field count. |
| **P0.5** | **Fix stage5_verify.py docstring**: remove "Classifier: Phi-4-mini-8bit", update NLI description to match runtime | 10 min | Triple-stale docstring misleads every reader. |
| **P0.6** | **Fix pipeline_config.yaml L1642**: remove or annotate stale `classify_model: Phi-4-mini-instruct-8bit` | 1 min | v2.3 checkpoint artifact in active config. |
| **P0.7** | **Re-enable `MacWebContentsOcclusion` in Goose** | 5 min | ~20% CPU back for OMLX during 26h run. |
| **P0.8** | **Resolve HANDOFF_D2254 model registry**: Phi-4-mini has no S5 pipeline role — correct or remove claim | 5 min | Governance doc contradicts config. |

### 🟠 P1 — FIX BEFORE FULL RUN (cumulative ~2-4 days)

| # | Task | Effort | Source |
|---|------|--------|--------|
| **P1.1** | **Golden depth expansion**: add ≥10 universal + ≥10 specialized examples | 2d | T-015. 1 example per class is uncalibratable. |
| **P1.2** | **Run DeBERTa FEVER calibration on 50-100 real FBs** | 4h | 5-FB benchmark is proof-of-concept. Need production thresholds. |
| **P1.3** | **Deploy DSPy hybrid gate in production stage2_extract.py** | 4-8h | Currently only in comparison harness. The 0.736 metric requires the hybrid path. |
| **P1.4** | **Fix S4→S5 verification gap**: extend S5 to verify application/failure_mode/elaboration content, or make schema conditional on actionability | 1d | ChatGPT v2: "biggest problem — bigger than S4 latency." |
| **P1.5** | **S1.5 cluster-quality diagnostic**: sample 100-300 clusters, measure real convergence rate | 2h | Before 26h run, validate that clustering surfaces convergences. |
| **P1.6** | **Resolve faiss_threshold mismatch** (T1.4) | 30 min | 0.75 vs 0.70 reported mismatch. |
| **P1.7** | **Fix generator model name drift**: reconcile Qwen3.6-35B vs Qwen3-Coder-30B across config and docstrings | 30 min | |
| **P1.8** | **Implement domain-stratified DSPy demo selection** | 4-8h | Root cause of DSPy positive-fidelity gap. Current 2 demos all DESIGN. |

### 🟡 P2 — DEFER TO POST-RUN

| # | Task |
|---|------|
| P2.1 | evals/golden_cases.json label audit (14 probable errors from ChatGPT v3 audit) |
| P2.2 | Full DSPy extraction migration (keep hybrid as permanent architecture — 6/8 LLMs agree) |
| P2.3 | Model-level LoRA fine-tuning (ALL LLMs: NOT RECOMMENDED with current data volume) |
| P2.4 | Expand golden to 150-250 examples |
| P2.5 | Replace or recalibrate Gemma-4-E4B as S5 deep verifier |

---

## PART 8: EXECUTION ORDER (NEXT 48 HOURS)

```
HOUR 0-1:   P0.1 (S5 NLI config fix, 5min)
            P0.3 (Archive GOLDEN-REVIEW.md, 1min)
            P0.4 (Fix golden meta, 1min)
            P0.5 (Fix stage5_verify.py docstring, 10min)
            P0.6 (Fix stale config L1642, 1min)
            P0.7 (Re-enable MacWebContentsOcclusion, 5min)
            P0.8 (Fix HANDOFF model registry, 5min)
            → All P0 config/doc fixes complete in <1h

HOUR 1-3:   P1.6 (faiss_threshold, 30min)
            P1.7 (Model name drift, 30min)
            P1.2 START (DeBERTa calibration on 50-100 FBs — can run overnight)
            → Config hygiene complete

HOUR 3-9:   P0.2 (50-100 book E2E diagnostic, 3-6h)
            → THIS IS THE GATE. Real yield data, real S5 behavior, real cluster quality.
            → If yield >1% and S5 pass rate >40%, approve P1.1-P1.8 and schedule full run.
            → If yield <0.5% or S5 <20%, halt and diagnose before scaling.

HOUR 9+:    If E2E diagnostic passes:
            P1.5 (Cluster-quality diagnostic, 2h)
            P1.1 START (Golden depth expansion, 2d — can run in parallel)
            P1.3 (Deploy DSPy hybrid in production, 4-8h)
            P1.8 (Domain-stratified DSPy demos, 4-8h)
            P1.4 (S4→S5 verification gap, 1d)
            → Then schedule T1.1 full run (~26h)
```

---

## BOTTOM LINE

The pipeline is **not broken — it's undocumented.** The two cross-examination rounds revealed that the handoff chain (HANDOFF_D2254 → MASTER-TASK-REGISTER → aggregated_remaining_tasks) propagates stale claims about yield (phantom), golden composition (stale), model architecture (DSPy not deployed), and verification (NLI dead). But the actual code is more mature than the docs suggest: S4 depth works, hybrid S2 is benchmarked at 0.736, DeBERTa FEVER fix exists but is config-blocked.

**The P0 fixes take under 1 hour total.** The E2E diagnostic is the only way to get real data. Everything else flows from that.
