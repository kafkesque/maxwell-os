# Consolidation drafts — D-2637 (2026-09-16)

**Status: DRAFTS ONLY.** Nothing here has been written to a protected file.
`CONSTITUTION.md`, `config/*.yaml` and the loader/skill files are C-protected (never overwrite),
so these are proposed contents for review. On your sign-off I apply them, then run
`just health` + integrity + `guard_stacks_single_source.py`.

## Files

| file | target |
|---|---|
| `01_pipeline_config.diff.md` | `config/pipeline_config.yaml` (targeted edits, not a rewrite — 25 KB file) |
| `02_model_assignments.yaml.draft` | `config/model_assignments.yaml` (full rewrite — the 2026-07-08 merge is unrecoverable) |
| `03_CONSTITUTION_s2.md` | `CONSTITUTION.md` §2 |
| `04_dependents.md` | `AGENTS.md`, `agent/skills/maxwell-os-SKILL.md`, `agent/session_seed.yaml`, `config/decisions.yaml`, `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md` |

## GATED PLACEHOLDERS — 3 remaining (was 4)

| id | what | resolving run | current reading |
|---|---|---|---|
| **`[[G1]]`** | LONG_CONTEXT role holder | Run B (in flight) | Qwen3.8-27B niah **1.000** @ 147 s/item; Qwen3-Coder **0.500** with 6 transport errors — Qwen3.8 leads on accuracy, loses badly on latency |
| **`[[G2]]`** | S4 classifier (merged CRIBS+classify) | production-path table (in flight) | incumbent gpt-oss-20b; challengers Qwen3.8-27B (best benchmark 0.709/0.693 but **R5-blocked**) and gemma-4-E4B (R5-clean; beat gpt-oss in voting 0.422/0.357 vs 0.339/0.261) |
| **`[[G3]]`** | Qwen3.8 quant variant → the `model_id` written everywhere | quant A/B (queued) | uniform 4-bit (16.08 GB, installed) vs **OptiQ mixed 4/8-bit** (20.68 GB, downloaded) |

**`[[G4]]` — RESOLVED 2026-09-16: keep `Ornith-1.5-9B-MLX-8bit`, delete `Ornith-1.5-9B-OptiQ-4bit`.**
The 8-bit wins the composite **0.682 vs 0.642**, the coding composite **0.773 vs 0.677** (humaneval 0.80 vs 0.72,
hardcode 1.00 vs 0.75) and delegation **1.00 vs 0.667**; it loses reviewing (−0.167), stability (−0.100),
mbpp (−0.040), math500 (−0.040) at +2.36 GB. Neither variant can vote (0.227 / 0.116 vs Qwen3.8's 0.709).
**Pending your sign-off:** the 4-bit OptiQ deletion (6.94 GB) — evidence complete, not yet executed.

## Gated by a user ruling, not by data

- **`[[D1]]` — ACCEPTED (2026-09-16):** `deepseek-v4-pro` is **out of `reliable_voters`**. It stays as an **offline anchor-builder only** (bounded labelling job — never a production labeller), registered under `cloud_opt_in` with `cloud_opt_in_roles`. Rationale: a cloud model in the production path breaks C1 ($0 marginal) and C3 (sovereignty). Caveat recorded: the 0.643 vs 0.269 head-to-head is confounded (the review sheet disclosed provenance → brand authority), so the **blind re-adjudication of the 60 disagreement rows is still owed** before the gap is quoted as fact. Local decider = Qwen3.8-27B.
- **`[[D2]]` — ACCEPTED (2026-09-16):** the three live R5 violations are fixed. **S6_VALIDATOR → deterministic** (no LLM: schema/taxonomy validation + the D2620 fail-closed guard; an R5 violation cannot exist where there is no model). **S3A_CONVERGENCE → gemma-4-E4B**, **BOUNDARY_VERIFIER → gemma-4-E4B** (distinct gemma4 family, reviewing 0.83, ifeval 1.00 / delegation 1.00 — the strongest spec-follower).
- **`[[D3]]` — ACCEPTED (2026-09-16), conditional:** R5 exception for S4 labelling **granted if `[[G2]]` shows Qwen3.8 materially ahead** (>5 points). Three guards are mandatory: (1) S5 stays the independent DeBERTa NLI truth gate; (2) gemma-4-E4B is a permanent independent spot-auditor on a sample, with the disagreement rate as a running bias monitor; (3) the unmeasured family-correlation caveat goes into DECISION-LOG. Measured basis for accepting: Qwen3-Coder does not generate **labels**, only FB content, so the S4 label choice cannot change the principle text; and shared-error correlation follows training lineage, not nominal family (Qwen3-Coder 0.300 vs Ornith distill 0.727-1.000). If the gap is ≤5 points, stay R5-clean. **NEVER** use REAP/Ornith-9B/any Qwen3.8-distilled model for S4 or voting.

## Known gaps that will be DECLARED, not hidden, at freeze

1. **Reasoning axes unmeasured** for Qwen3.8 / Qwen3-Coder / REAP / OptiQ (mmlu_pro, gsm8k, math500, hotpot_qa). No gated decision depends on them — LEVER 2 deferred them to `run_completeness_tier2.sh`.
2. **R5 correlation risk is unquantifiable on the current corpus**: all **7,995** FBs and all **251** gold rows have a single `gen_model` (Qwen3-Coder), so there is no generator contrast to test whether Qwen3.8 favours Qwen-generated artifacts.
3. **S4 student classifiers are falsified** (ModernBERT flat discipline macro-F1 0.229, domain 0.009; bge-m3 taxonomy-match macro-F1 0.000) and **SetFit was never implemented** (zero references in the codebase). Both stay off.
4. **Four pipeline LLM stages never benchmarked**: S0.5 metadata, S2 relabel, S4_5 enrich, retrieval_eval, hyDE.
5. **S0 conversion fidelity** has zero benchmarks.