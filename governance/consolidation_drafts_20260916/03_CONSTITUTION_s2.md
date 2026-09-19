# 03 — `CONSTITUTION.md` §2 proposed replacement (D-2637)

Current §2 is 5 lines. Proposed: same shape, corrected facts, plus the two invariants the
portfolio work established. `[[G1]]`/`[[G2]]`/`[[G3]]` resolve when the running chain lands.
**D1/D2/D3 are ACCEPTED (user ruling 2026-09-16)** and are written in full below — no longer
placeholders: D1 = deepseek-v4-pro out of `reliable_voters`, kept as offline anchor-builder
only; D2 = the three R5 violations fixed (S6 deterministic, S3A + BOUNDARY_VERIFIER → gemma-4-E4B);
D3 = R5 exception for S4 GRANTED, conditional on `[[G2]]` showing Qwen3.8 materially ahead, with
the unmeasured family-correlation caveat recorded in DECISION-LOG.

## INVARIANT — EVERY ROLE CLAIM IS CITED (proposed 2026-09-16, gate: `scripts/validate_role_claims.py`)

No model may be assigned to a stage, and no role may be described as best/most accurate, without an
`evidence:` citation naming an artifact, a date and a sample size. `scripts/validate_role_claims.py`
exits non-zero while any role is uncited, so this can gate the freeze.

Why it exists: on 2026-09-16 the draft assigned `S4_DEPTH` to gemma-4-E4B with no citation, and the
claim was repeated in conversation as if measured. The repo already contained
`governance/S4_DEPTH_EMPIRICAL_RESULTS_2026-08-14.md`: gemma 62.5% vs gpt-oss 75.0% depth accuracy
(n=8, production path), parity 62.5%, gate ≥0.90 FAILED — verdict **"gemma-4-E4B is NOT accurate
enough for depth. Do NOT enable depth_frugal_enabled"**. `depth_frugal_enabled` is **false**, so the
live depth model is gpt-oss, not gemma. Independently confirmed 2026-09-16 on 60 production rows:
gpt-oss 0.450 / Qwen3.8 0.467 / gemma 0.433, paired p ≥ 0.815 — no measurable difference, so no
model may be called "the best depth classifier" at this sample size.

The failure mode was not a wrong benchmark; it was **inheritance without citation**. Roles were
copied forward from a config that was itself tuned against a model later refuted, and prose does not
stop that. A validator does.

## BEFORE

```
## §2 — ARCHITECTURE

3 LAYERS: Pipeline (8-stage) → Knowledge (SQLite+FTS5+sqlite-vec+LightRAG) → Orchestration (Phase 2, skill.md standard)

MODELS: Gen=Qwen3-Coder-30B-A3B-Instruct-MLX-4bit | Classify=gpt-oss-20b-MXFP4-Q8 | Embed=bge-m3 | NLI=MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (D2298)

PIPELINE (v3.0 cluster-before-extract, D2120: 8-stage): 0-convert → 0.5-metadata → 1-chunk → 1.3-prefilter → 1.5-FAISS-RNN-cluster → 2-convergent-extract(+hybrid-gate D2276) → 4-classify+dedup(D2120: Stage 3 removed) → 5-verify(DeBERTa-v3-large-NLI-only D2298, threshold 0.10 calibrated, fail-closed D2093) → 6-commit

STORAGE: SQLite (canonical) + sqlite-vec (vectors) + Parquet (portability) | TAXONOMY: 43 domains, 61 disciplines (+1 "emerging" each), max 5 per FB (D2066: dynamic, raw labels can dethrone canonicals; D2540 corrected counts)
```

## AFTER (proposed)

```
## §2 — ARCHITECTURE

3 LAYERS: Pipeline (8-stage) → Knowledge (SQLite+FTS5+sqlite-vec+LightRAG) → Orchestration (Phase 2, skill.md standard)

MODELS (D-2637, 2026-09-16 — 7 models, each with a measured justification):
  Gen (S2)      Qwen3-Coder-30B-A3B-Instruct-MLX-4bit   [PINNED]
  Decider       Qwen3.8-27B-MLX-4bit                    [PINNED]  [[G3]] = uniform 4-bit | OptiQ mixed 4/8-bit
  S4 classify   [[G2]]
  Tool agent    Ornith-1.5-35B-A3B-REAP-19B
  Probe (S2)    Phi-4-mini-instruct-8bit
  Depth/review  gemma-4-E4B-it-MLX-4bit
  Light coder   Ornith-1.5-9B-MLX-8bit
  Embed=bge-m3 | Rerank=BAAI/bge-reranker-v2-m3 | NLI=MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli

INVARIANT — S5 HAS NO LLM. S5 = DeBERTa-v3-large NLI only, fail-closed (D2298). Any LLM
assigned to S5 is a configuration bug. This is also why S5 is architecturally independent
of the generator's family, and why the R5 concern that applies to S4 LABELLING does not
apply to S5 TRUTH VERIFICATION.

INVARIANT — R5 IS A FAMILY CONSTRAINT, NOT A MODEL CONSTRAINT. S2's generator is Qwen, so
no Qwen-family model (Qwen3-Coder, Qwen3.8-27B, Ornith-9B, Ornith-REAP) may hold an S2
verification/probe/classification role. Seven of ten local models were Qwen before the
D-2637 prune; this is the binding constraint on every future model choice, and the portfolio's
principal structural risk.

PIPELINE (v3.0 cluster-before-extract, D2120: 8-stage): 0-convert → 0.5-metadata → 1-chunk → 1.3-prefilter → 1.5-FAISS-RNN-cluster → 2-convergent-extract(+hybrid-gate D2276) → 4-classify+dedup(D2120: Stage 3 removed) → 5-verify(DeBERTa-v3-large-NLI-only D2298, threshold 0.10 calibrated, fail-closed D2093) → 6-commit

STORAGE: SQLite (canonical) + sqlite-vec (vectors) + Parquet (portability) | TAXONOMY: 43 domains, 61 disciplines (+1 "emerging" each), max 5 per FB (D2066: dynamic, raw labels can dethrone canonicals; D2540 corrected counts)

CLASSIFICATION POLICY (D-2637, measured on 251 human-adjudicated rows):
  - Decider = Qwen3.8-27B alone, full coverage (discipline 0.709, domain F1 0.693).
  - MAJORITY VOTING IS REJECTED: average 3-combo majority 0.541 < 0.709 single-model.
  - Unanimity of REAP+Qwen3-Coder+Qwen3.8 is an AUTO-ACCEPT TIER ONLY (0.915 @ 18.7% coverage).
  - No local third reliable voter exists; Ornith-9B and Phi-4-mini must NEVER vote.
  - DOMAIN UNION IS PEER-ONLY: max(mean|P|)/min(mean|P|) <= 1.30, else abstain (fail-closed).
    Measured: union with a peer 0.729; with an over-labeller 0.474; all six voters 0.398.

FAIL-CLOSED IS MEASURED, NOT ASSUMED. Abstain-else-escalate is a tested axis
(`abstain` suite, 108 adjudicated rows, 49 of them non-principle). A model that fabricates
a principle from a process template fails, regardless of its accuracy elsewhere.

INFERENCE: oMLX is the ONLY production inference path (in-process mlx_lm is research-only and
its numbers must never be mixed with oMLX numbers). oMLX serves ONE resident model — never
reload or swap while a run is in flight (BUG-255); use scripts/omlx_reload.py between runs.
```

## Why these additions

| addition | reason |
|---|---|
| per-model role list with `[[G*]]` | the roster is now evidence-derived; the placeholders make the pending gates explicit rather than silently guessed |
| S5-has-no-LLM invariant | the prior config assigned an LLM to S5 in two role keys, and it was stale by its own annotation |
| R5-as-family-constraint | this is the constraint that actually eliminated candidates this cycle; 7 of 10 models were Qwen |
| classification policy block | turns four hard-won measurements into an invariant instead of leaving them in a governance doc |
| fail-closed-is-measured | closes the gap that we were selecting classifiers on accuracy alone |
| inference block | records the BUG-255 lesson where it will be read before someone swaps a model mid-run |