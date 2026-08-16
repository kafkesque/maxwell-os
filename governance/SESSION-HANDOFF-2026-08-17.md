# Session Handoff — 2026-08-17 (continues 2026-08-16)

> **Phase:** Phase 1 (v3.0 architecture validation) — **T1.1 GO** (D2398)
> **Branch:** `main` | session commits: `793fd26` (pipeline), `fcca197` (gov D2397), `47e0f99` (gov D2398), + final gov commit (D2399/D2400)

## Session outcomes

### Decisions ratified (this session)
| # | Decision | State |
|---|---|---|
| D2396 | DB reset — fresh DB for T1.1 (676-row DB archived); run-specific DB = G10 (P2) | ✅ |
| D2397 | Commit working tree `793fd26` + golden verbatim fix (5 NON_VERBATIM → verbatim; meta 77→80) | ✅ |
| D2398 | S4 reval confirms D2393 (depth) + D2394 (taxonomy) **live** | ✅ |
| D2399 | Domain promote/demote **defer to post-T1.1+D2345 full-corpus counts** (NOT canary) | ✅ |
| D2400 | Field-production contract: **S4 = producer, S6 = persistence-only** | ✅ |

### What was done
1. **DB reset** — archived 676-row/5-run-id DB → fresh empty DB (0 rows, 60 cols).
2. **Golden set fixed** — 5 NON_VERBATIM evidence passages corrected (CONV-054 paraphrase, CONV-055 3× double-apostrophe, CONV-058 fabricated `Generator` quote) + meta 77→80; `golden_validate` 80/80 PASS; hash re-stamped.
3. **Working tree committed** — `pipeline_commit` now truthfully resolves to HEAD (was stale `7cbbc2a`).
4. **S4 reval** re-ran on 279 canary clusters → **D2393 + D2394 re-validated live**:
   - depth cross-domain **86.3% → 21.6%**, domain **12.6% → 77.0%**
   - discipline `emerging` **32.0% → 15.5%**
5. **All gates green**: integrity 17/17, config-audit strict (no hardcode/drift), golden_validate 80/80, `just preflight` + OMLX stress (40 seg/s embed, FAISS+FTS+SQLite OK).

### T1.1 readiness: **GO**
Everything validated. The only thing blocking launch is an operator go/no-go (multi-day ~39h run — not auto-launched).

## Remaining / next-session priorities

1. **T1.1 full launch** (multi-day, ~39h) — `MAXWELL_RUN_ID=t11`, reuse `latest` S1.5 clusters (12,964), run S2→S6. See `tools/canary_rerun_s2onward.sh` for the launch pattern (caffeinate + preflight gates).
2. **G3 domain promotion** (post-T1.1 **+ D2345**, D2399) — run `check_for_replacements()` on FULL-corpus `taxonomy_counts`, NOT the canary preview.
3. **D2345** — single-source non-type second pass (`stage2_extract_nontype.py`, reuse S1.5 clusters).
4. **BUG-104 (action)** — switch runtime to Homebrew Python (`brew install python@3.12`) or conda-forge to enable `sqlite-vec`/`vec_fbs`. Non-blocking (FTS fallback).
5. **F1 (future tax, D2400)** — build post-S4 producers for `prerequisite_fbs`/`contradicts_fbs`/`procedural_skill` (fold into D2345, NOT S6, NOT inline-S4).
6. **G10 (P2)** — run-specific DB (`DB_PATH` scoping by run_id + active-KB pointer).

## Key file changes
- `pipeline/stage4_merged_call.py` (D2393 depth prompt) · `pipeline/schemas.py` (D2394 synonym kind-filter) · `pipeline/stage6_commit.py` (D2391/D2395) · `config/taxonomy_v5.yaml` (D2394 aliases) · `config/golden/stage2_fewshot_convergent.yaml` (D2397 verbatim) · `config/decisions.yaml` (387 decisions).

## Non-blocking audit findings (feed next session)
- **Domain-synonym gap**: LLM emits `public policy` (52×) which doesn't map to canonical `legal & public policy` → feeds G3 (same class D2394 fixed for disciplines).
- **`check_for_replacements` flagged "legal & public policy" (already canonical) as `emerging`** — possible double-count/normalization bug to investigate during G3.

## Resume seed
- This file · `DECISION-LOG.md` (D2396–D2400) · `governance/domain_taxonomy_promotion_preview.md` · `governance/aggregated_remaining_tasks.md` · `agent/session_seed.yaml`.
