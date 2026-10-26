# HANDOFF — 2026-10-26 — BUG-1015 (lint gate that cannot fail) + the ROOT-CAUSE answer

> Supersedes the 2026-10-23 handoff (BUG-965 closed). This session answered the owner's root-cause question and
> landed the highest-leverage fix: BUG-1015, the lint gate that could never fail.

## §1 The root-cause answer (the deliverable the owner asked for first)

**Why do more bugs appear each time, with no visible progress?** Measured today, not guessed:

- `just audit` ran `python3 -m ruff check pipeline/ 2>&1 | tail -5` under `@` — the exit status is TAIL's, always 0.
  Real count on 2026-10-26: **2462 findings (exit 1)**, of which **252 are the F (pyflakes) correctness family**.
  The gate printed "✅ Audit complete" while 2462 defects sat there unseen.
- The sovereignty rail (pre-BUG-1029) read the CONFIG's `active_provider`, not the session's own row — said "local"
  while the live session ran on `custom_deepseek` (20.5M tokens billed upstream).
- `just health` (the "certified green" ladder) did NOT run `config_audit` — two disjoint certified sets.
- The ladder fingerprint hashed the LINE SET, not the line bodies.

**The single root cause, four disguises:** every instrument was born ONE-SIDED — it could be seen to PASS but never
to FAIL — and it read a DECLARATION (config) instead of a FACT (disk/session). That is BUG-492 ("a control that
cannot be seen to fire both ways is not a control") and D-3034 ("a declaration must resolve to a referent"), violated
by the instruments themselves. Each fix added a rail; the rail was born unverifiable, so the NEXT bug was always "the
rail I just built can't actually fire / reads the wrong source". The surface of instrumentation grew, the guarantee
did not — hence compounding.

**The reframe:** you ARE progressing — 548 of 793 bugs are CLOSED, governance faces reconcile, the ladder is green.
The reason it feels like no progress is the bug: the instruments that would SHOW the progress were themselves
drifting, so old debt becoming visible read as "new bugs appearing faster than we fix them".

**The reliable, future-proof fix (not new work — apply the discipline you already codified, to the instruments):**
one meta-rule — before any control lands, it must be BORN TWO-SIDED (prove RED on a known-bad input AND GREEN on a
known-good input) and read a FACT, not a declaration; and it counts against a SHRINK-ONLY ceiling so it can never
silently grow. That stops the minting of new bugs because the thing that mints them (an unverified guard passing
while the referent drifts) is itself retired.

## §2 What landed this session

- **BUG-1015 FIXED.** New `scripts/lint_gate.py`: certified lint = F family (pyflakes correctness), counted against
  a shrink-only ceiling declared in `config/pipeline_config.yaml#lint_gate` (ceiling 252, baseline 252, direction
  shrink_only, scope pipeline/+scripts/). `--selftest` 5 known answers (RED at ceiling+1, GREEN at ceiling and below,
  refuses a loosened direction). `--check` fails on GROWTH. `--report` names the 2462-total style debt (non-failing,
  D-3038). The `just audit` recipe no longer pipes ruff through `tail`.
- **config_audit joined into `just health`.** The drift audit (previously preflight/audit-only, a disjoint set) now
  runs inside the certified ladder: 194 -> 198 declaring lines.
- **D-2989 re-record.** The new file moved the config-defaults census 647 -> 648 modules; the census-parity contract
  caught it and `--record` re-derived the receipt (debt unchanged: 300 shadowed / 3 undeclared).

## §3 Final receipt (MEASURED GREEN)

`python3 scripts/run_ladder.py --collect health` — **198 declaring lines, 0 faults, worst rc=0, 554.7s,
head_at_start == head_at_end == 8e625a7, fingerprint 239c21931d651901, receipt-check rc=0.** Worktree clean.
Gov faces green (1283 decisions / 793 bugs: 245 open / 548 closed / 0 divergent). Commits: 5e4f19a (BUG-1015 +
config_audit join) and 8e625a7 (D-2989 re-record).

## §4 Ordered next steps (highest-leverage first, each with a red loop)

1. **Drive the certified lint debt 252 -> 0** (the F family). 182 are auto-fixable (`ruff check --select F --fix`),
   the rest manual. Delegate per-file/rule-group in PARALLEL to local LLMs per D-3155 (name the tool, artifact = RESULT
   not a rule). Lower the `lint_gate.ceiling` as it falls (shrink-only). Red loop: `python3 scripts/lint_gate.py --check`
   prints the count; it must shrink, never grow.
2. **Fix the ladder fingerprint to hash LINE BODIES, not just the line set** (T-204 residual). Today an edit that
   changes a line's content does NOT move the fingerprint — the integrity proof doesn't prove content integrity.
3. **BUG-1028** — delegate failure reports say `Other`; need a cause vocabulary or documented harness limit + a
   mandatory `--cause` slot in delegate_journal with a two-sided control.
4. **BUG-1027** — the declared app-side hf_endpoint rail is still NOT BUILT: admin settings write must REFUSE a
   non-empty non-http(s) hf_endpoint (two-sided: `{"hf_endpoint":"hf_..."}` -> 400, `{"hf_endpoint":"https://..."}` -> 200).
5. **T-202 / T-204 / BUG-1021 / T-203** instrument-honesty items; then **T-101/T-116** retrieval golden set (saturated
   at recall@10=1.000).

## §5 Manual owner steps

None required this session — all changes are automated and certified. The live conversation remains born on the
ESCALATION provider `custom_deepseek` (billed upstream), which `goose_profile.py --check` reports rc2 OWNER-OWED loud
non-fatal — that is correct and expected (D-3023), not a defect.

## §6 CONTINUE HERE

Resume at §4 step 1 (drive 252 -> 0), or answer any further owner question. After each landing run
`python3 scripts/gov_sync.py --apply` then `--check`, and finish with a FOREGROUND `python3 scripts/run_ladder.py
--collect health`.
