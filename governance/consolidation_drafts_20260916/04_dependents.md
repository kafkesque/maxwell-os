# 04 — Dependents that quote model names (D-2637)

Every file below hard-codes a model name or a model→role mapping. All were audited;
exact before/after given so the edits are mechanical.

## 4.1 `AGENTS.md` (C-protected — never overwrite; needs your explicit go)

### (a) delegate routing block, lines ~78-88

`before` (line 78):
```
  - ✅ gemma-4-E4B-it-MLX-4bit: CONFIRMED working. 0.48s response. Use for: code review, summarization, classification.
```
`after`:
```
  - ✅ gemma-4-E4B-it-MLX-4bit: CONFIRMED working. Use for: fast review/analysis, spec-following (delegation 1.00,
    ifeval 1.00), S4 depth, cross-family validation. NOT a coder (humaneval 0.16 / mbpp 0.44).
  - ✅ Ornith-1.5-35B-A3B-REAP-19B: the only 1.00 tool-caller (n=4). Use as the tool/research agent.
  - ❌ gpt-oss-20b-MXFP4-Q8: NEVER give it tools (toolcalling 0.00 on 2 independent runs). Classification/CRIBS only.
  - ⚠️ Ornith-1.5-9B (any): NEVER as a voter or classifier (discipline 0.227 max; default-'A' bias: mmlu_pro 3/25).
    Fine as a light coder (humaneval 0.80) — that is its only role.
```

`before` (line 86):
```
  - S4 discipline/domain classification → gpt-oss-20b-MXFP4-Q8 (OMLX classifier; batch via subprocess, NOT a delegate).
```
`after`:
```
  - S4 discipline/domain classification → [[G2]] (OMLX; batch via subprocess, NOT a delegate).
    Incumbent gpt-oss-20b; challenger gemma-4-E4B. Qwen3.8 is more accurate but R5-blocked.
```

`before` (line 88):
```
  - Summarization WITH source text → Phi-4-mini-instruct-8bit (never open-ended; BUG-053).
```
`after` (unchanged content, clarified because Phi is now a confirmed KEEPER):
```
  - Summarization WITH source text → Phi-4-mini-instruct-8bit (never open-ended; BUG-053).
    Also the S2 fast probe (1.3s, fastest in portfolio). KEEP — not a deletion candidate.
```

### (b) MODELS block, lines ~99-103

`before`:
```
  Generator:    Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (OMLX)
  Classifier:   gpt-oss-20b-MXFP4-Q8 (OMLX, S4 — D2249)
  Probe:        Phi-4-mini-instruct-8bit (OMLX, S2 fast probe — D2319; NOT an S5 verifier, D2298)
  Embeddings:   bge-m3 (Ollama, 512d Matryoshka)
  NLI:          MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (local, D2298)
```
`after`:
```
  Gen (S2):     Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (OMLX)   [PINNED]
  Decider:      Qwen3.8-27B-MLX-4bit (OMLX)                    [PINNED]  quant variant = [[G3]]
  S4 classify:  [[G2]] (OMLX — D2249; production-path A/B in flight)
  Tool agent:   Ornith-1.5-35B-A3B-REAP-19B (OMLX)             only 1.00 tool-caller
  Probe:        Phi-4-mini-instruct-8bit (OMLX, S2 fast probe — D2319; NOT an S5 verifier, D2298)
  Depth/rev:    gemma-4-E4B-it-MLX-4bit (OMLX)
  Light coder:  Ornith-1.5-9B-MLX-8bit (OMLX)                  won the 4bit/8bit A/B
  Embeddings:   bge-m3 (Ollama, 512d Matryoshka)
  Rerank:       BAAI/bge-reranker-v2-m3 (local)
  NLI:          MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (local, D2298)
  ⛔ S5 HAS NO LLM (D2298). R5 = family constraint: no Qwen-family model may verify/classify S2 output.
  ⛔ oMLX serves ONE resident model — never reload/swap mid-run (BUG-255).
```

### (c) pipeline block, lines ~67 and ~70

`before`: `  stage2_extract.py    → Clusters → convergent FBs (Qwen3-Coder, R5)`
`after` : `  stage2_extract.py    → Clusters → convergent FBs (Qwen3-Coder, the pinned generator)`
`before`: `  stage5_verify.py     → DeBERTa-v3-large NLI only (fail-closed, D2298)`  — UNCHANGED (already correct)

## 4.2 `agent/skills/maxwell-os-SKILL.md` lines 37-40

`before`:
```
| Code review / classification sanity / summarization WITH source | gemma-4-E4B-it-MLX-4bit |
| Single-shot code generation | Qwen3-Coder-30B (one-shot curl ONLY — never multi-turn) |
| S4 discipline/domain classification | gpt-oss-20b-MXFP4-Q8 (OMLX batch) |
| Summarization WITH source text | Phi-4-mini-instruct-8bit (never open-ended; BUG-053) |
```
`after`:
```
| Fast review / analysis / spec-following | gemma-4-E4B-it-MLX-4bit (delegation 1.00, ifeval 1.00, 1.7s) |
| Deep review / analysis / planning | Qwen3.8-27B-MLX-4bit (reviewing 1.00, delegation 1.00) |
| Single-shot code generation | Qwen3-Coder-30B (one-shot curl ONLY — never multi-turn) |
| Complex coding | Qwen3.8-27B-MLX-4bit (humaneval 0.96) |
| Light coding / drafting | Ornith-1.5-9B-MLX-8bit (humaneval 0.80, best small coder) |
| Tool calling / research agent | Ornith-1.5-35B-A3B-REAP-19B (toolcalling 1.00) |
| S4 discipline/domain classification | [[G2]] (OMLX batch) |
| Summarization WITH source text | Phi-4-mini-instruct-8bit (never open-ended; BUG-053) |
| NEVER | gpt-oss with tools (0.00) · Ornith-9B or Phi as voters |
```

## 4.3 `agent/session_seed.yaml`

Prepend one header comment (the file's convention is an `# Updated:` log at the top):
```
# Updated: 2026-09-16 (D-2637 MODEL PORTFOLIO CONSOLIDATION. Deleted granite-4.2-8b + gemma-4-12B
#   (Prune #3, 17.8 GB, df-verified). Ornith 4bit/8bit A/B COMPLETE -> keep Ornith-1.5-9B-MLX-8bit
#   (composite 0.682 vs 0.642; coding 0.773 vs 0.677; delegation 1.00 vs 0.667), delete the 4-bit
#   (pending sign-off). Phi-4-mini KEPT (fastest 1.3s, smallest, phi3 family, owns the S2 probe).
#   Voting verdict: Qwen3.8-27B is the decider (0.709); MAJORITY VOTING REJECTED (mean 3-combo 0.541);
#   unanimity gate REAP+Qwen3-Coder+Qwen3.8 = auto-accept tier only (0.915 @ 18.7%); no local 3rd
#   voter exists; Ornith-9B/Phi must NEVER vote. Domain union gated on peer granularity
#   (ratio<=1.30, D-2637) - verified byte-identical on the D2633 sets (ratio 1.158).
#   ModernBERT student + bge-m3 domain routes FALSIFIED (0.229/0.009 and 0.000 macro-F1); SetFit
#   never implemented. S5 = NLI only, NO LLM. oMLX single-resident: never reload mid-run (BUG-255);
#   use scripts/omlx_reload.py. New: abstain suite (108 rows), pipe_s4_classify_gold.py,
#   scripts/vision_probe.py, the |P| guard. DRAFTS in governance/consolidation_drafts_20260916/.)
```

## 4.4 `config/decisions.yaml` + `DECISION-LOG.md` — proposed entries

```yaml
- id: D2637
  category: MODELS / CONSOLIDATION
  state: IN_FLIGHT
  description: 'MODEL PORTFOLIO CONSOLIDATION. Full benchmark campaign (Tier A 9 models x 8 suites,
    voting 251 gold rows, ARM-1/2/4, production-path S4) -> target 7-model stack. Prune #3 deleted
    granite-4.2-8b (ALL 0.353, last on every axis) + gemma-4-12B (toolcalling 0.00, 40.5s/call, family
    already covered by E4B) = 17.8 GB. Ornith-1.5-9B 4bit vs 8bit A/B: 8-bit wins (composite 0.682 vs
    0.642; coding 0.773 vs 0.677; delegation 1.00 vs 0.667; neither can vote: 0.227/0.116). Phi-4-mini
    KEPT (fastest 1.3s, 3.99GB, phi3 family, 6/6 valid extraction zero NULLs). Latency correction:
    bytes/token does NOT predict latency for reasoning models - 8-bit was FASTER on mbpp (5.6 vs 8.7s)
    and hardcode (15.6 vs 24.0s) because thinking-token count dominates. 3 gates remain: [[G1]]
    LONG_CONTEXT (Run B), [[G2]] S4 classifier (production path), [[G3]] Qwen3.8 quant variant.'
  champion: goose
  target_files: [config/model_assignments.yaml, config/pipeline_config.yaml, CONSTITUTION.md,
    governance/model_portfolio_consolidation.md, governance/pruned_models_20260915.md]
  created: '2026-09-16'
- id: D2638
  category: MODELS / POLICY
  state: RESOLVED
  description: 'CLASSIFICATION ENSEMBLE POLICY (2026-09-16). Measured on 251 human-adjudicated rows
    with 6 local voters. Qwen3.8-27B alone = 0.709 discipline @ 100% coverage. (a) MAJORITY VOTING
    REJECTED: average 3-combo majority 0.541, majority>=50% of 6 = 0.656 - both BELOW the single best
    voter. (b) UNANIMITY GATE = AUTO-ACCEPT TIER ONLY: REAP+Qwen3-Coder+Qwen3.8 = 0.915 @ 18.7% coverage;
    unanimity is a SELECTION EFFECT (rare + correlated with easy rows); route the rest to review.
    (c) NO LOCAL THIRD VOTER EXISTS: rescue rate of Qwen3.8 errors - gemma-4-E4B 13/73 (0.178),
    Qwen3-Coder 13/73 (0.178), gpt-oss 12/73 (0.164), REAP 7/73 (0.096), Ornith-9B 1/73 (0.014).
    (d) NEVER vote: Ornith-9B (0.116, default-A bias: mmlu_pro 3/25 = chance) and Phi-4-mini (D2577).
    RANKING identical across ALL/CIRCULAR/HUMAN subsets, so the ordering and ~2x margin are robust.
    Also RETRACTED the earlier error-Jaccard framing: Jaccard is dominated by base rates when
    accuracies differ hugely; rescue rate is the honest test.'
  champion: goose
  target_files: [governance/voting_verdict_20260916.md, config/pipeline_config.yaml, tools/voting_report.py]
  created: '2026-09-16'
- id: D2639
  category: MODELS / POLICY
  state: RESOLVED
  description: 'DOMAIN AGGREGATION = PEER-ONLY UNION (2026-09-16, extends D2633). D2633 ruled
    overlap->union for the reliable pair and was CORRECT there: the pair''s measured granularity
    ratio is 1.158 (DeepSeek 2.644 vs Qwen3.8 2.284 domains/row), i.e. a peer pair. But union is NOT
    a general operator: measured against 251 gold rows, union with an over-labeller destroys precision
    - Qwen3.8 alone 0.693; +REAP (|P| 2.23) 0.729; +gemma-4-E4B (3.60) 0.513; +Qwen3-Coder (6.06)
    0.474; all six voters 0.398; exact-set unanimity would abstain on ~71% of serviceable rows (the
    anchor itself matches the human set only 29.1% of the time). GUARD IMPLEMENTED in
    scripts/aggregate_domain_votes.py: union permitted only when max(mean|P|)/min(mean|P|) <= 1.30;
    otherwise union_blocked_granularity -> abstain (fail-closed). Regression-verified byte-identical
    on both existing sets (148/216, 34/59). PEER_F1_MAX_GAP=0.10 documented as eval-time only.'
  champion: goose
  target_files: [scripts/aggregate_domain_votes.py, governance/domain_aggregation_policy_v2.md]
  created: '2026-09-16'
- id: D2640
  category: INFRA / OMLX
  state: RESOLVED
  description: 'oMLX MODEL REGISTRY RELOAD (BUG-254/255). The registry is cached at app start, so a
    newly symlinked model was invisible (REAP scored 0.0 on 43/43 calls, HTTP 404) and a deleted one
    still listed. FIX: POST /admin/api/login {api_key} then POST /admin/api/reload - documented as
    "re-read model settings, re-discover models, preload pinned". Wrapped as scripts/omlx_reload.py;
    supersedes the dead control socket (scripts/_omlx_restart.py) and avoids the omlx-cli restart
    duplicate-server trap (D2455/D2456). CAUTION (BUG-255): reload PRELOADS PINNED models, so on a
    single-resident server it EVICTS the model a running benchmark is using and wedges the client
    with no server-side trace (active_requests:0, idle_seconds growing). RULE: never reload during a
    run; reload only between runs.'
  champion: goose
  target_files: [scripts/omlx_reload.py, governance/buglog.md]
  created: '2026-09-16'
- id: D2641
  category: QUALITY / EVAL
  state: RESOLVED
  description: 'FAIL-CLOSED IS A MEASURED AXIS (2026-09-16). Added the `abstain` suite: 108 rows
    adjudicated by D2629 (59 principle / 49 not: 39 process_template, 4 noise_drop, 4 tool_instruction,
    1 growth_edge, 1 process_instance), text from maxwell.db, grounded in content_type_reverify_108.json.
    Metric = fail-closed behaviour: a model that fabricates a principle from a how-to FAILS, regardless
    of accuracy elsewhere. Rationale: the S4 classifier was being selected on accuracy alone while the
    pipeline''s stated posture is abstain-else-escalate. Also added tools/fetch_abstain_set.py to freeze
    the set (drift-proof, offline). Total per-model suite now 602 items.'
  champion: goose
  target_files: [tools/fetch_abstain_set.py, governance/evalsets/abstain.jsonl, tools/model_eval_suite.py]
  created: '2026-09-16'
- id: D2642
  category: MODELS / RETIREMENT
  state: RESOLVED
  description: 'PRUNE #3 (2026-09-16): granite-4.2-8b-MLX-8bit + gemma-4-12B-it-qat-OptiQ-4bit deleted,
    ~17.8 GB freed (df-verified 48->66 GB). granite: last or near-last on EVERY axis (ALL 0.353, delegation
    0.17, hardcode 0.25, humaneval 0.24, mbpp 0.40); its only rationale was R5 family diversity, still
    satisfied by gemma4 + gpt_oss + phi3 after removal. gemma-4-12B: ALL 0.448, toolcalling 0.00,
    humaneval 0.36, 40.5s/call worst-by-4x; no role E4B does not do better ~24x faster. MEASUREMENT
    NOTE: the deletion script first reported 36.77 GB because os.path.getsize follows snapshot symlinks
    into blobs/, double-counting every blob; corrected to 17.8 GB. Also REFUTED the earlier claim that
    deleted models are pruned from the oMLX registry live - they persist until a reload.'
  champion: goose
  target_files: [governance/pruned_models_20260915.md, governance/eval_models.txt]
  created: '2026-09-16'
```

## 4.5 `MASTER-TASK-REGISTER.md` — prepend a phase block

```
> **D-2637 MODEL PORTFOLIO CONSOLIDATION (2026-09-16).** Full evidence-driven consolidation.
> Tier A: 9 models x 8 suites. Voting: 251 human-adjudicated rows. ARM-1/2/4 + production-path S4.
> DELETED: granite-4.2-8b + gemma-4-12B (Prune #3, 17.8 GB). Ornith 4bit/8bit A/B -> keep the 8-bit.
> KEPT: Phi-4-mini (fastest/smallest, owns the S2 probe). Target stack = 7 models.
> REJECTED by measurement: majority voting (0.541 < 0.709 single voter); ModernBERT student
> (0.229/0.009 macro-F1); bge-m3 domain taxonomy-match (0.000); SetFit (never implemented).
> NEW: abstain suite (108 rows), pipe_s4_classify_gold.py, |P| peer-granularity guard,
> scripts/omlx_reload.py (BUG-254), vision_probe.py, scripts/audit_final_chain.py.
> 3 GATES OPEN: [[G1]] long-context (Run B), [[G2]] S4 classifier (production path),
> [[G3]] Qwen3.8 quant variant. **3 USER RULINGS ACCEPTED 2026-09-16:**
> [[D1]] deepseek-v4-pro OUT of reliable_voters, kept as an offline anchor-builder under cloud_opt_in
> (blind re-adjudication of the 60 rows still owed), [[D2]] three live R5 violations fixed
> (S6_VALIDATOR → deterministic, S3A_CONVERGENCE + BOUNDARY_VERIFIER → gemma-4-E4B),
> [[D3]] R5 exception for S4 granted conditionally on [[G2]] >5 points, with S5 NLI as the
> independent gate + gemma-4-E4B as permanent spot-auditor. Drafts:
> governance/consolidation_drafts_20260916/. DECLARED GAPS: reasoning axes deferred (Tier-2);
> R5 correlation risk unquantifiable (single gen_model across all 7,995 FBs); 4 stages never
> benchmarked (S0.5/S2-relabel/S4_5/retrieval_eval/hyDE); S0 conversion fidelity unmeasured.
```

## 4.6 Already updated this cycle (no action needed)

| file | change |
|---|---|
| `governance/eval_models.txt` | regenerated from the live registry; granite + gemma-4-12B removed (8 models) |
| `governance/eval_models_longctx.txt` | v2 — keepers only (granite/gemma-4-12B removed, REAP added) |
| `scripts/arm4_benchmark.py`, `scripts/arm4_download.py` | DeepSeek-R1 entry removed so it cannot be resurrected |
| `scripts/_omlx_restart.py` | SUPERSEDED by `scripts/omlx_reload.py` |
| `governance/buglog.md` | BUG-253..256 (256 retracted with reasoning) |
| `scripts/aggregate_domain_votes.py` | peer-granularity guard (D2639) |
| `tools/model_eval_suite.py` | abstain suite + ungradable-gold guards + BUG-253 error-retry |

## 4.7 Verification to run after applying

```bash
just health                                   # 10/10 expected
python3 pipeline/integrity_check.py           # taxonomy + model-role consistency
python3 scripts/guard_stacks_single_source.py # no duplicate OMLX servers (D2455/D2456)
python3 -c "import yaml; yaml.safe_load(open('config/model_assignments.yaml'))"   # YAML parses
grep -rn 'Phi-4-mini-instruct-4bit\|deepseek-r1-8b' config/ pipeline/ | wc -l   # expect 0
```

Then, only after [[G1]]/[[G2]]/[[G3]] land: replace the placeholders and re-run the three checks above.