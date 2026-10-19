# HANDOFF 2026-10-20 — THE COST LEAK NAMED: GOOSE_PLANNER override + birth-pin; D-3113 applied

> Written for a NEW goose session (start `goose run` fresh to pick up the LOCAL planner — knobs are read
> at session BIRTH, so THIS session can never show them; see BUG-877). Read
> `governance/CONTEXT_INDEX.md` first for where the long-lived registers live; this file is the
> session-scoped delta.

## THE REVELATION — "am I charged right now?" (measured, not assumed)

YES. At 2026-10-19T22:11Z the usage ledger's newest row was `deepseek-v4-pro`, session `20261019_2`
(this session), ~$0.01/call. Oct-18 $8.41 + Oct-19 $7.70 = **$16.11 over 2 days**, matching the DeepSeek
dashboard's ~$17. Lifetime real spend since May: **~$1200** ($600 May→Aug + $600 Aug→now). A **$39.35
compensation credit** (2026-10-15) offsets ~5 days at this rate — a buffer, not a fix.

TWO independent layers kept the charge running:

1. **GOOSE_PLANNER override (the fixable one).** D-3104 (owner, 2026-10-19) declared
   "active=local, escalation=cloud, **GOOSE_PLANNER stays deepseek**" — a clause that contradicted its
   own first clause. `~/.config/goose/config.yaml` carried `GOOSE_PLANNER_PROVIDER: custom_deepseek` /
   `GOOSE_PLANNER_MODEL: deepseek-v4-pro`, so the session PLANNER (which runs EVERY turn) was deepseek.
   "everyday decisions on gpt-oss-20b, $0 marginal" was therefore never achieved.
2. **Session-birth pin (BUG-877, OPEN).** A running session keeps the model it was BORN with and never
   re-reads the config mid-run. So a correct file alone is insufficient — **routing local requires a NEW
   session (`goose run`)**.

## WHAT LANDED THIS SESSION (commit `6c44b47`; tree clean)

- **Config fix (system file, backed up):** `~/.config/goose/config.yaml` lines 313-314 changed
  `custom_deepseek`/`deepseek-v4-pro` → `maxwell_omlx`/`gpt-oss-20b-MXFP4-Q8`
  (backup: `~/.config/goose/config.yaml.bak.20261020_prelocalplanner`). `active_provider` was already
  `maxwell_omlx`; YAML re-validated. Everyday loop is now local (gpt-oss-20b, $0 marginal).
- **D-3113 (RESOLVED)** in `config/decisions.yaml`: overturns D-3104's planner clause; deepseek is now an
  EXPLICIT escalation for strategic D-3xxx decisions only, never the ambient planner.
- **Census re-derived:** 1239 → **1240** decisions (resolved 334→335); stamp `0fb5f9b41e2d2d09` →
  `0c8a9e564ca3fd8d`. Faces re-cut; `gov_sync.py` GREEN (4 faces, rc 0), `check_harness_homes.py` 5/5 BOUND.
- **Hard-won mechanic (do not repeat the miss):** the decision CENSUS is `config/decisions_summary.json`,
  NOT `config/decisions.yaml`. A decision append needs the chain:
  append → `python3 scripts/recompute_decision_summary.py` → `python3 scripts/gov_sync.py --apply` →
  `python3 scripts/gov_sync.py` (must be GREEN). Skipping the middle step leaves faces at the OLD count
  (this is exactly the "4-step manual chain" drift the 2026-10-19 handoff flagged).

## FIRST THING THE NEW SESSION MUST DO (verify the switch)

1. It is already born on `maxwell_omlx`/gpt-oss-20b if started with a plain `goose run`.
2. Verify with this read (token-cheap):
   ```
   sqlite3 "file:$HOME/.local/share/goose/sessions/sessions.db?mode=ro" \
   "SELECT datetime(created_timestamp,'unixepoch'),model,round(cost,4) FROM usage_ledger ORDER BY created_timestamp DESC LIMIT 5;"
   ```
   Expected: top rows name `gpt-oss-20b-MXFP4-Q8`, cost blank/0. If they STILL say `deepseek-*`, the
   planner key is not the operative lever and BUG-877 is the sole cause — report the exact rows.
3. **Counter rule (never confuse again):** the goose COUNTER counts TOKENS across all models and rises
   even at $0 — it is NOT a cost signal. You are charged **iff the ledger row's MODEL is deepseek/cloud**;
   the dashboard balance drops only on a deepseek row.
4. Optional, since gpt-oss-20b is a 20B loop model: if its quality proves too thin for a long turn, the
   escalation path is a DELIBERATE deepseek call (e.g. `delegate` to `custom_deepseek`), never resetting
   the planner.

## NEXT CRITICAL STEPS (consequential order — highest leverage first)

1. **BUG-917 SPLIT — now urgent.** `pipeline/delegation_economy.py --check` compares LIFETIME cloud cost
   ($130.19) to a shrink-only ceiling ($130.00, D-3023). Going local STOPS the burn but does not lower the
   lifetime total, so `just health` keeps RED at that line on a historical number. Fix: windowed
   burn-rate on ACTUAL billed cost, estimate kept only as a labelled proxy. This also closes the
   "tripwire measured estimates, not dollars" blindspot (all 38,892 ledger cost rows are `estimated`).
2. **BUG-877** — append the 2026-10-20 live reading to the buglog; the defect (a governed config write not
   reaching the running session) is structural, not this session's doing.
3. **BUG-948** — highest OPEN bug (`owner_marks.rule_digest` whole-file sha256 stale-ifies the pair
   object; red-loop-first D-3036).
4. **T-187 receipt persistence** — the two-step receipt lives only in gitignored `temp/`; persist it.
5. **F-03** — confirm status (CONTEXT_INDEX: re-scoped designed state, deferred until content_type
   certified).

## CURRENT CENSUS (verified this session)

**1240 decisions** (stamp `0c8a9e564ca3fd8d`) · **713 bugs (252 open / 461 closed; highest OPEN =
BUG-948)** · 57 open tasks. BUG-941 is ALREADY RESOLVED (buglog L18787); D-3110/3111/3112 already
present. The older "consequential order" (BUG-941 close, D-3108 commit) was already done before this
session — do not redo it.

## CAREFUL / DO-NOT-DRIFT

- `config/decisions.yaml` + `governance/buglog.md` are APPEND-ONLY by convention — append, never rewrite.
- `~/.config/goose/config.yaml` is a SYSTEM file outside the repo's `config/*.yaml` protection — back up,
  re-validate YAML, and remember the running session never picks it up (birth-pin).
- The repo's protected files (CONSTITUTION.md, DECISION-LOG.md, AGENTS.md, config/*.yaml, governance/*.md)
  are untouched this session EXCEPT the gov_sync face re-cuts (DECISION-LOG.md / MASTER-TASK-REGISTER.md /
  buglog.md census lines) which gov_sync owns by design.
