# HANDOFF — 2026-10-23 (BUG-965 closed; next-critical-step map)

> To continue in a fresh session: say **"continue"** (or paste this file's `## CONTINUE HERE` block).
> Every number below was READ from disk on 2026-10-23 ~14:35 +02:00 — not remembered.

## STATE (resolved from disk)

- **HEAD** `37d3f55` — `fix(BUG-965): a single wedged OMLX call no longer aborts the adjudication batch (C23/C16)`.
- Working tree **clean**.
- `gov_sync --check`: **GREEN** — `ok gov-sync: 4 face(s) equal their re-derivation (1259 decisions / 738 bugs / 58 open tasks)`.
- Bugs: **OPEN 259 / CLOSED 479 of 738** (BUG-965 just flipped MED 84→83; highest OPEN = BUG-972).
- Recall rail: **CLEAN** — concept 44/44 = 1.0, expectation 418/418 = 1.0, tier B 0 proposed.
- Commit gates all green (repo-integrity, recalibration pins 0 RED, declaration consumers 11/14, session plan all declared).

## WHAT LANDED THIS SESSION (3 commits, newest first)

| commit | what |
|---|---|
| `37d3f55` | **BUG-965 FIXED** — `scripts/adjudicate_reanchor_two_model.py`: `run_one` now catches a RAISED `call_omlx`, records `{"ok": false, "error": ...}` to the raw JSONL AND stderr (C16), and lets the batch continue (C23). Summary prints `N done / M errored`. Red-loop `--selftest` (no-server fixture, first call raises) passes. R5: gemma APPROVE. |
| `52a195e` | **T-195 step (a)** — tier-B completeness arm: `check_extraction_recall.py` reads `config/extraction_recall.yaml#golden.tier_b_sheet` (JSONL, currently `null`), reports PROPOSED-but-unruled candidates SEPARATE from the tier-A floor, never floors/auto-certifies them. Selftest control #7 proves tier-B omission is CLEAN not RED. |
| `015f673` | **BUG-973 closed** (limb 3: 241/241 disposed; silent-dead-disposition root cause fixed in `dispose_admission.py`). |

## OWNER-ONLY MANUAL TASKS (D-3100 — copy-paste, expected output, and the "if it differs" branch)

There are **2 owner-moved open tasks** (the GOV-INDEX "OWNER LANE (2)"): **T-195** and **T-183**.

### 1. T-195 — pick the pilot sources (the ONLY blocking owner word)

The tier-B arm's instrument is live but inert until you name pilot sources. Do this:

1. Read the tier-A certified core list to pick sources that ALREADY have certified concepts
   (the gate says "start where a certified core already exists, so a proposal can be checked against a known answer"):
   ```bash
   python3 -c "import json; d=json.load(open('governance/EXTRACTION_RECALL_GOLDEN_20261023.json')); print('\n'.join(sorted({r['source_id'] for r in d['rows']})))"
   ```
   *Expected:* ~338 source_ids. *If it errors or prints nothing:* the golden is stale — re-run
   `python3 scripts/check_extraction_recall.py --build-golden --apply` first.

2. Reply to the agent with a short list of source_ids you want as the pilot (e.g. 2–5). That is the whole word.

3. The agent then writes T-195 step (b) (the proposer: a local model emits advisory candidate concepts per source into the `tier_b_sheet` JSONL). You will then rule each candidate MATCH/NONE into that sheet, and the agent rebuilds the golden + `--check` through the SAME rail (no second instrument). **Tier B is never auto-certified.**

### 2. T-183 — the next admission cycle (recurring; the signed scope is exhausted)

The prior acceptance (`governance/ADMISSION_ACCEPTED_20261018T192457Z.yaml`) is EXHAUSTED (106 decided, 3 outstanding, 109→107 candidates). The next cycle is three commands, in order:

```bash
just admit-plan                       # re-derive the plan (expect: "candidates N", a fresh digest)
just admit-sign "<your name>"         # pin your identity + sign the scope (expect: a NEW ADMISSION_ACCEPTED_<ts>.yaml)
just admit-apply --limit 10           # first tranche (dry-run first if you want: just admit-apply --dry-run)
```
*Expected after `--limit 10`:* a `DECIDED … applied / already_applied / failed` line and no traceback.
*If a row fails:* the plan's `refused[]` names the class and its remedy (corrupt container, name-repair-first → T-176 rename, not-in-kind-folder → T-184). The failure leaves NOTHING in the corpus (BUG-887 fix holds).

> The 241 asset dispositions that used to block this are **DONE** (BUG-973). The remaining refusal words ride on **T-176** (185 name-repair rows) and **T-184** (53 not-in-kind-folder rows) — both are now **pipeline-moved** (owner word given 2026-10-17), not owner-lane.

## NEXT CRITICAL STEP (agent-side, unblocked) — my senior recommendation

Take **BUG-966 (MED)** next — the highest-severity remaining OPEN bug:
> "two governance faces asserted an UNEXECUTED gate whose receipt was committed and already ratified" — a vacuous-pass / truth-in-recordings defect (the BUG-967/BUG-492 "a control nothing runs is a comment" class).

Then, in leverage order:
1. **BUG-972 (LOW)** — `r5_code_review.py --out <path outside repo>` writes the verdict then dies with a traceback (same deterministic-fix shape as BUG-965 just proved; cheap red-loop).
2. **T-195 step (b)** — the proposer script (needs the owner's pilot source list from §1 above; write it to take source_ids from `config/extraction_recall.yaml`).
3. **BUG-967 (LOW)** — S0.5 reports "identical" over two EMPTY sets (instrument repair).
4. **BUG-964 (LOW)** — gpt-oss-20b determinism (UPDATE #1: the flip is REAL but RARE, 1/40 = 2.5%, gpt-oss against ITSELF).

**Pre-implementation discipline (unchanged):** forensic audit → label hypotheses until a receipt speaks (D-3036) → red-loop FIRST → implement → selftest → R5 review to gemma-4-E4B-it-MLX-4bit (`maxwell_omlx`) → sync gov (`buglog safe-append` → `scripts/bug_status.py` → `scripts/gov_sync.py --apply`) → commit (gates run automatically).

## KNOWN LOOSE ENDS (observed, not blocking)

- **C11 `mobi` import**: `scripts/pre_commit_gate.py` flags `stage0_convert.py: imports mobi — not in stdlib/local/known deps`. Pre-existing, unrelated to this session's work; no pre-commit hook is installed so it does not block commits, but `mobi` (Kindle parser) should be declared in requirements if it isn't already a known dependency.
- `scripts/adjudicate_reanchor_two_model.py` `--workers 1` workaround is now **correctness-obsolete** (superseded by the BUG-965 fix); `--workers` remains a throughput knob only.

## CONTINUE HERE

```bash
cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
git log --oneline -1                     # expect 37d3f55
python3 scripts/gov_sync.py --check      # expect "ok gov-sync: ... 4 face(s) equal"
python3 scripts/check_extraction_recall.py --check   # expect CLEAN 44/44, 418/418
python3 scripts/adjudicate_reanchor_two_model.py --selftest   # expect ✅ selftest passed (BUG-965 red-loop)
```
Then begin **BUG-966** (or ask the owner for the T-195 pilot source list if you prefer to advance the recall arm).
