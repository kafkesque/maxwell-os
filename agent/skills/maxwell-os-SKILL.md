# Maxwell OS v3.0 — Skill (regenerated)

> **v3.0** · regenerated 2026-09-04 (D2552/GOV-SKILL) from `AGENTS.md` + `CONSTITUTION.md`.
> Supersedes the dead v5.0 skill (2026-04-26) whose 6 dependency paths were 100% stale.

## Purpose

Primer + entry-point index for any agent session working in this repo
(`maxwell os 2.0/`, system version v3.0). The 8-stage S0–S6 pipeline classifies
and commits Foundation Blocks (FBs) from a book/PDF corpus.

## Dependencies — read these before technical work (ALL VERIFIED LIVE)

| File | Purpose |
|---|---|
| `CONSTITUTION.md` | Single source of truth for ALL system rules (v3.0) |
| `AGENTS.md` | Agent loader — boot sequence, iron rules, delegation routing (D2549) |
| `config/decisions.yaml` | Machine decision registry (authoritative — recompute via `scripts/recompute_decision_summary.py`) |
| `DECISION-LOG.md` | Tiered human-readable decision log |
| `MASTER-TASK-REGISTER.md` | Tiered task register (MUST→SHOULD→WORTH→DONE) |
| `config/pipeline_config.yaml` | C12 config (NO hardcoded values) |
| `governance/buglog.md` | Live bug register |

## Pipeline (CONSTITUTION §2 — 8 stages)

```
stage0_convert → stage0_5_extract_metadata → stage1_chunk → stage1_3_prefilter
→ stage1_5_embed_cluster → stage2_extract → stage4_merge → stage5_verify → stage6_commit
```
(`stage3_cluster` REMOVED — D2120/D2198, replaced by cluster-before-extract.)

## Delegation routing (D2549 — ALWAYS route by this)

| Task type | Model / path |
|---|---|
| Deterministic data-repair (SQL/scripts) | Execute directly (LLM-free) |
| Code review / classification sanity / summarization WITH source | gemma-4-E4B-it-MLX-4bit |
| Single-shot code generation | Qwen3-Coder-30B (one-shot curl ONLY — never multi-turn) |
| S4 discipline/domain classification | gpt-oss-20b-MXFP4-Q8 (OMLX batch) |
| Summarization WITH source text | Phi-4-mini-instruct-8bit (never open-ended; BUG-053) |
| Research / fact-finding | shell/curl directly (NEVER delegate) |

## Standing rules (subset — full list in CONSTITUTION/AGENTS)

- temp=0.0 on all generation scripts (R7)
- Generator ≠ Verifier — different model family (R5)
- NEVER hardcode values — paths/thresholds/models → `config/*.yaml` (C12)
- Crash-safe writes: tempfile → fsync → os.replace (C6)
- NEVER delete pipeline output (R-D410)
- No silent errors — except clauses log AND raise (C16)
- Type hints on all signatures (C17); docstrings on functions >5 lines (C18)
