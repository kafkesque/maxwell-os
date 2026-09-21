# FORENSIC AUDIT — session 14 (2026-09-21)

Scope: run BEFORE any serious task, per the standing instruction. Question: has anything broken, drifted,
bound, gapped, conflicted, mismatched, silently contaminated, leaked, errored, failed, or accrued future tax?

All rows re-run live this session — no quoted history, no recalled numbers.

| check | command | result |
|---|---|---|
| tree clean / no drift | `git status --porcelain` | empty at 0e681c1 |
| version chain | `git log --oneline -6` | 0e681c1 ← cfc77fb ← 9a8fbac (expected, nothing else) |
| taxonomy bytes | `shasum -a 256 config/taxonomy_v5.yaml` | 994e056b… == the recorded v5.6 value ✔ |
| answer-space pin | menu_hash vs pin file vs ANCHOR-2 key | 73597ee2… unchanged ✔ |
| sandbox containment | `git check-ignore -v .venv_laya` | .gitignore:109 ✔ (benchmark arm untracked, D-275c) |
| backup junk | `git status --porcelain` on `config/*.bak_*` | 0 tracked; every one matches `.gitignore:101 *.bak_*` ✔ |
| pin integrity | `python3 scripts/pin_audit.py` | PINS: 5 checked, 0 failing → PASS |
| decision registry | `python3 scripts/recompute_decision_summary.py --check` | in sync (685) |
| bug register | `python3 scripts/bug_status.py` | 105 ids / 67 open / 38 closed |
| C16 silent exceptions | integrity [15] | PASS (91 pipeline files) |
| C12 hardcoded paths | integrity [14] | FAIL → **FIXED this session** (BUG-353 / D-326) |
| stage-5 | carried | **Verify = 0 — BUG-341 OPEN** (untouched this session) |
| laya isolation | no production import of `laya_mlx` | ✔ no production coupling |

## Findings
1. **No drift, no leak, no contamination, no broken bind.** Every pin green at 0e681c1 is still green; the
   only bytes that moved are the ones this session was chartered to move (plus governance records).
2. **BUG-353 FIXED** — integrity [14]: 11 shell scripts hardcoded the repo path inside a `cd` line; the fix
   stores no path at all (self-locating). The two `tools/model_eval_suite.py` hits are synthetic tool-calling
   eval fixtures, exempted with an EXPLICIT, COUNTED marker (`C12-FIXTURE:`) reported in the PASS message, so
   the exemption surface is visible rather than a hole.
3. **BUG-359 LOGGED (process, LOW):** the carried note "justfile names the wrong config_audit path" was
   stale — justfile:24 and :255 already read `pipeline/config_audit.py`. A pending note is not evidence.
4. **BUG-341 is the largest RED:** stage-5 Verify = 0, so no claim that the newest FBs are *verified* is
   currently testable. Owner-runnable (see handover).
5. **Future tax identified (not yet paid):** `manifest_hash` now folds in the boundary-rule sha256
   (D-318/D-325) and *moved to 024579b6*. Any artifact that compares manifest_hash for "same run" must be
   re-read, not assumed. Logged for the next consumer.

## Verdict
GREEN for the work done, with two explicitly carried RED/orange items (BUG-341 stage-5 Verify = 0; F-11 no
second coder). Nothing in this audit blocked the measurement run.
