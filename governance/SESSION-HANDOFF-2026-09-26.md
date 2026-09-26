# SESSION HANDOFF — 2026-09-26 (sitting 2 of the D-2655 sequence)

## STATE VERIFIED AT THE END OF THIS SITTING (each line measured, not assumed)

- `just health` **rc=0**. The ladder completes; one sitting ago it was rc=1, aborting at line 51 for the BUG-542
  mechanical reason (a declared silent-repair site keyed by a LINE NUMBER that a +37-line fix had shifted).
- Bug register: **281 ids, 128 OPEN / 153 CLOSED**; `ok bug_status: register equals its re-derivation`.
  `ok buglog coverage: every heading naming a bug id is parsed`.
- `config/decisions.yaml` **UNCHANGED**: 784 records, stamp `0d7a746350d62e14`, `recompute_decision_summary.py --check`
  clean, receipt ok. NOTHING was minted (BUG-539 still blocks a mint — see D-2655 below).
- git: HEAD `96b1e9c79c441edf71b551a2f3c52e06e31f6362`, branch `main`, git dir OUT OF TREE
  (`/Users/barn/maxwell_os_gitdirs/maxwell_os_2_0.git`, BUG-500), porcelain 182.
- **NOTHING was committed** (D-381, owner-held). Every change below is on disk only.

## WHAT CHANGED THIS SITTING (2 files)

### 1. `scripts/check_silent_repair.py` — BUG-544 remedied (the rail now DECIDES, it does not raise)

PRE 195 lines -> POST **283 lines**, POST sha256
`2254fe4ecbd02a9039043a73334720c05f37557c1e63d15861db0dd094fc88f1`.

`load()` was ONE line — `yaml.safe_load(CONFIG.read_text(...))` — so an ABSENT declaration surfaced
`FileNotFoundError` and an EMPTY one returned `None` and then raised `AttributeError` out of the first `cfg.get(...)`.
Both were TRACEBACKS at `just health` line 51 instead of a verdict. Now:

| function | job |
| --- | --- |
| `declaration_text(path)` | `FileNotFoundError` / `IsADirectoryError` / `UnicodeDecodeError` / `OSError` -> a NAMED `SystemExit` |
| `parse_declaration(text, path)` | EMPTY / unparseable YAML / not a mapping / missing a REQUIRED key (`scan_roots`, `ceiling`) -> named |
| `config_path(repo)` | the `repo` argument of `load()` was **IGNORED** before (a caller asking about another repo got THIS one's policy) |

`scan()` now also **REFUSES an EMPTY `scan_roots` and a declared scan root that is not on disk**. Before,
`if not base.exists(): continue` narrowed the census to NOTHING and still printed `ok` — a rail that can never say
FAIL (BUG-492). Its sibling `scripts/check_config_defaults.py` already carried this exact guard (C16); this rail now
matches the sibling.

MEASURED (the shipped module was COPIED into `/tmp/bug544/scripts` and run against a controlled declaration — no repo
state touched): `ABSENT` 1 | `EMPTY` 1 | `UNPARSEABLE` 1 | `NOT_A_MAPPING` 1 | `MISSING ceiling` 1 |
`MISSING scan_roots` 1 | `SCAN_ROOT_ABSENT` 1 | `CONTROL_OK_CONFIG` 0 — **TRACEBACKS LEAKED = 0**.
`--selftest` 12 -> **18/18** (one known-answer control per case, asserting the NAMED sentence, because `exit != 0`
alone cannot tell a named refusal from a traceback). `--check` still rc=2 (debt 17 of ceiling 17, unknown 0).

### 2. `governance/buglog.md` — appended 4,237 B (590,438 -> 594,675)

PRE sha256 `e0ca39f8cbe68daaedac5de5c361704e35b42fa3cfe782a1d0c160d2eb32ee1b`, POST
`2235079080be54ea6e7a7d81a5090bc3aafcd59f0fc92419a8f52ef1f87f6876`. The append idiom asserted
`len(POST) == len(PRE) + len(entry)`, and exactly ONE heading was added (`## BUG-544 (MEDIUM - FIXED 2026-09-26)`) —
because a heading that names a bug id without BEING a parsed entry breaks buglog coverage, which is how the previous
sitting's own governance sync turned the ladder red within minutes.

## AUDIT FINDINGS THAT NOW BIND THE NEXT STEP (each was checked BEFORE acting)

1. **THE CENSUS HOME MUST NOT BE `governance/decisions_summary.json`.** `governance/session_plan_20260924.yaml`
   `may_touch` covers `config/*.json` but **NOT** `governance/*.json` (it names `governance/bug_status.json`,
   `governance/HANDOFFS.jsonl` and one ANCHOR4 manifest explicitly). A new `governance/*.json` sits OUTSIDE
   `may_touch`, and widening the plan so an assistant may write it is forbidden (BUG-528/BUG-445). D-2655's census
   must be born at **`config/decisions_summary.json`** — covered today by `config/*.json` — or the plan change must be
   an OWNER act, committed first.
2. **`git add config/silent_repair.yaml` IS NOT A DURABILITY FIX.** `git ls-files` is the INPUT SET of the incident
   rail (`check_repo_integrity.py`: `tracked_paths()` -> `_scan_root(...)`), so staging changes what that rail
   examines — and that is the one rail which reports the BUG-500/BUG-543 git-dir incident. Track it in **COMMIT A**
   and SEE the new row compare clean; never by a bare stage.
3. **`config/silent_repair.yaml` IS STILL UNTRACKED** (`?? `, 0 `ls-files`) — 5510 B, sha256
   `73bb29ae31e95d50dff0582d9dc043d4acbad3d1e6a64ebd22273ecff04e3671`. A declaration three rails depend on has no
   receipt and no history: a fresh clone or one more BUG-543 recurrence ends at line 51 with "the declaration is
   ABSENT" (now a sentence — that part is fixed this sitting — but still a red ladder). Durability half = a COMMIT.
4. **NO LINE-NUMBERED REGISTER KEYS THE RAIL**: `config/undeclared_encoding.yaml` names
   `scripts/check_silent_repair.py` only inside a COMMENT (line 6), and no shipped path in `config/` or `tests/`
   names the file. So the edit could not shift a declaration — the BUG-542 cascade was PROVEN absent before the edit.
5. **NEIGHBOUR CENSUS UNMOVED**: `check_config_defaults` measures 412 sites / 210 shadowed-declared / 2 undeclared,
   identical to before the edit (the new code adds no `.get(key, default)` site — the very thing that rail counts).
6. **HARNESS HAZARDS (new, cost real time this sitting)**: `${PIPESTATUS[0]}` inside a backtick command is eaten by
   the TypeScript template literal (`ReferenceError: PIPESTATUS is not defined`) — use `$?` and a file instead; and
   `set -e` truncates a probe matrix after the first non-zero exit, silently reducing an 8-case probe to 1 case.

## NEXT CRITICAL STEPS — IN CONSEQUENTIAL ORDER

1. **D-2655 HALF A (additive only, zero removal — safe by construction).** Create the census at
   `config/decisions_summary.json` from the CURRENT registry (`total_decisions`, per-state counts, `by_category`,
   `last_sync`, `decisions_sha256_16`, `written_by`, **`source_sha256`** = sha256 of the registry bytes it describes),
   and have `scripts/recompute_decision_summary.py` WRITE AND VERIFY both homes side by side. Nothing is stripped, so
   `config/decisions.yaml` bytes do not move → **the `decisions_registry` receipt is untouched** and no re-baseline is
   owed yet. Self-proving check: the JSON re-derives to 784 / `0d7a746350d62e14`.
2. **D-2655 HALF B (the removal).** Strip the derived head (lines 1-6) and the top-level `summary:` block so the
   registry holds RECORDS ONLY and extends to EOF; make a mint a **pure byte-APPEND** (that is the whole point: the
   receipt is a PREFIX rule and no position inside the file is compatible with it while a derived value changes on
   every mint); re-point `config/artifact_ownership.yaml` (`owned_by`), `config/derivations.yaml` (2 rows +
   `config_reads`), and `tests/test_decision_summary_sync.py` (read the census from its NEW home; FAIL CLOSED when the
   JSON is ABSENT — BUG-487); THEN re-baseline the receipt via `handoff.py --backfill` **in the same sitting**; verify
   with `--check`, the test, `check_derivation_homes`, `check_config_defaults`, `reconcile`, `just health`.
   Cascade to respect: `check_derivation_homes` validates a home by FUNCTION-NAME uniqueness and
   `enforcement.max_non_homed: 1` is shrink-only — the census writer must reuse the writer's existing
   `recompute`/`decisions_digest` functions rather than introduce a rival definition.
3. **MINT D-2653, D-2654, D-2655** — the first mint through the repaired path IS the end-to-end control for
   BUG-540 + BUG-539.
4. **BUG-542's REAL REMEDY**: key a declared silent-repair site by SITE CONTENT (enclosing function and/or the matched
   text), not by line number, so a refactor above a site cannot manufacture a false failure. Until then every insert
   above a declared site is a mechanical red ladder.
5. **Re-point `scripts/check_revoked_references.py` fixtures to the reserved `D-9xxx` range** (BUG-523) so the owner
   can ratify D-2651/D-2652 without ever minting the SPENT fixture ids D-2650/D-2651.
6. **R2 pin (OWED, $0 local)**: re-measure `scripts/definition_nli_verify.py` (~10 min local NLI), mint a new id, and
   re-pin sha AND decision TOGETHER (D-382/BUG-535).
7. Then the ungated queue: BUG-537's control for `build_archive_index.py`; `freeze_gold_sets.py` through `write_guard`;
   store-columns `debt 9 of ceiling 9`; the everyday-task eval rail (30-50 golden tasks — the prerequisite that turns
   "faster / more accurate / less hallucinatory" into numbers); `arm_typed_head()`; grammar-constrained decoding for
   S4/menu routing; the C17 type gate; the recurrence-clustering rail; re-staging the register before commit A.

## OWNER GATES

1. **THE DURABLE BUG-543 FIX (recommend YES, unchanged)**: stop the resurrector — delete `.git` from Dropbox's cloud
   copy, or move the worktree out of the synced tree (D-366). It recurred within ~24 h; a pointer file cannot survive a
   client that still holds the old `.git` DIRECTORY.
2. **COMMIT A**: config/silent_repair.yaml must be tracked, with `check_repo_integrity` seen to compare the new row
   clean. Do NOT ack the stale register blob (the index is far behind the register).
3. **D-2655 plan question**: if the census is to live under `governance/`, the `may_touch` widening must be the OWNER's
   act, committed first. Recommended: `config/decisions_summary.json`, no plan change needed.
4. Unchanged: ANCHOR4 "Copy of" rev 3 provenance; the `scripts/*.sh` widening (Arm B recommended); BUG-532's column-lock
   fix; the D-381 two-commit ack; the depth/domain contract activation (keep it non-gating today: 38 hard + 43
   owner-blocked findings are real S4 data debt, and the green ladder is green BY DECLARED OWNER GATE).

---

## SITTING 2 RESULT - D-2655 HALF A LANDED (2026-09-26)

Step 1 of the ordered list above is DONE and the ladder is BACK TO ITS BASELINE PARITY: just health rc=0,
ok=40, FAIL=1 (the audited non-gating contract line), reconcile rc=0, check_derivation_homes rc=0 (10 rows,
9 homed, ceiling 1), check_config_defaults rc=0 (412/210/2 - UNMOVED), verify_handoffs rc=0.

FILES CHANGED THIS SITTING (4 + 1 new artifact):
- scripts/recompute_decision_summary.py - the census home and a self-healing write branch
- config/decisions_summary.json - NEW, the census (pure function of the registry bytes)
- config/derivations.yaml - one homed row (decisions.census_json)
- config/artifact_ownership.yaml - the artifact declared, with unreconciled_reason (the cover rule)
- tests/test_decision_summary_sync.py - a fourth test, the second home's oracle
UNTOUCHED ON PURPOSE: config/decisions.yaml (784 decisions, stamp 0d7a746350d62e14, receipt ok). Nothing minted,
nothing committed (D-381).

NEXT CRITICAL STEPS, UPDATED ORDER:
1. D-2655 HALF B (the removal) - strip head lines 1-6 + the summary block, mint becomes a byte-APPEND, re-point
   ownership/derivations/test, re-baseline the receipt via handoff.py --backfill IN THE SAME SITTING, then the
   full verify chain. Self-proving: 784 records and 0d7a746350d62e14 re-derive identically.
2. MINT D-2653, D-2654, D-2655 - the first mint through the repaired path IS the end-to-end control for
   BUG-539 + BUG-540.
3. OWNER GATE COMMIT A - track the control plane (17 untracked rails + 3 libraries + declarations), WITH
   check_repo_integrity.py seen to compare clean; do NOT stage by a bare git add. The new census is untracked
   too (the BUG-545 class).
4. BUG-542's real remedy (content-keyed sites), then check_revoked_references.py fixtures to D-9xxx (BUG-523),
   then the R2 re-measure + re-pin sha AND decision together.
5. Then the ungated queue.


## D-2655 HALF B - LANDED (2026-09-26)

**Note:** config/decisions.yaml is RECORDS ONLY: 784 records, stamp 0d7a746350d62e14, sha256 39bb05d4718abb6da3e3ab618b1e554464d0bed325d3897be055dcf386adcad7, 601712 B. Derived fields live ONLY in config/decisions_summary.json (7 keys).

**Note:** Receipt re-baselined by handoff --backfill IN THE SAME SITTING; pre-strip digest remains in the journal.

**Note:** NEXT: (1) mint D-2655 + D-2654 via scripts/recompute_decision_summary.py --mint <file> --apply, then verify_handoffs must report 'appended' - that is the BUG-539 end-to-end control; (2) COMMIT A in TWO commits (control plane first, then the registry change) after explaining the register's unexplained +1 (OPEN 129 / CLOSED 153 of 282 vs the carried 281); (3) BUG-542's real remedy (content-keyed silent-repair sites); (4) R2 re-measure + re-pin definition_nli_verify.py; (5) wire pytest into the ladder as a rail - F1 was invisible for exactly that reason.

## D-2655 COMPLETE - MINT PROVEN, the driver bug RETIRED (2026-09-26)

**What landed:** the first mint through the D-2655 HALF B path. `--mint /tmp/mint_both.yaml --apply` appended D-2654 and D-2655 in ONE invocation (registry and census written together by the same writer). Registry 601712 B / 39bb05d4718abb6d -> 606225 B / 1d96883f365819a2, DELTA 4513 B, APPEND_IS_PREFIX True, 786 records, stamp b6492f16d292eea5, top-level keys ['decisions','ratified','version'] with the records list last.

**The end-to-end control:** `ok decisions_registry: config/decisions.yaml APPENDED (prefix intact, 601712 -> 606225 bytes)`. The receipt that used to read `rewritten` on every mint now reads `appended` - the removal is proven by the rail, not by argument. The bug is FIXED in the register (closure event appended to governance/buglog.md).

**State:** `recompute --check` rc=0; `pytest tests/test_decision_summary_sync.py` 5 passed; `just health` rc=0, ok=40, FAIL=1 (the audited non-gating contract line). Census = 786 decisions, 7 keys, source_sha256 matches the registry bytes; the only buckets that moved are rejected 9 -> 10 and ratified 16 -> 17.

**Declared-but-not-minted:** D-2653 (content not settled) - do not mint blind.

**Next owner act (the two-commit landing):** (1) the CONTROL PLANE - the untracked rails + scripts/lib/*.py + their declarations + config/decisions_summary.json; (2) the registry/D-2655 change. Never a bare `git add`; re-stage the stale register blob (HEAD's register carried 189 ids against 282 on disk); and NEVER `git checkout` the writer or the registry.

**Owed after that:** wire pytest into the ladder as a rail (the false witness was invisible for want of it); the content-keyed silent-repair site remedy; the R2 pin re-measure plus re-mint; the report-only candidate that the derivations rail never validates the table or column a row names.

## D-2656 COMPLETE - the SUITE is a RAIL, and a destructive test is retired (2026-09-26)

**Delivered:** `scripts/check_tests.py` (rail, 11 known-answer controls) wired into `just health` as
`--selftest` + `--check`, and into `health-deep` as `--check --strict` (D-390 revised: health MEASURES the
suite, health-deep demands it green). Ceiling declared in config/test_isolation.yaml (`suite_rail:`): 3 known
red ids, min_collected 261, SHRINK-ONLY.

**Measured before/after:** the suite at HEAD = 3 failed / 253 passed / 261 collected / 114s while `just health`
was GREEN (invisible red). Rail verdict: `ok tests: 261 collected (floor 261), 253 passed, 3 declared red,
0 new, 5 skipped`.

**BUG-546 FIXED:** tests/test_stage4_preflight_smoke_stress.py hand-built the production stage root and
`shutil.rmtree`'d a run dir inside the LIVE tree (deleted the S4 smoke dirs + their Dropbox conflicted siblings;
391 -> 376 stage rows). conftest TOLERATED it via the declared `smoke_*` glob - a scratch tolerance silently
covering a recursive delete. Now: paths from pipeline_paths (`_stage_run_dir`) and the delete REFUSED for any
run id not declared test scratch (`_rmtree_declared_test_run`).

**Recorded trap:** MAXWELL_PIPELINE_ROOT is NOT a suite sandbox (17 vs 3 failures) - config/ and books/DB also
resolve under PROJECT_ROOT. A sandbox must copy the CODE.

**Not done, deliberately:** the 3 declared red tests are NOT touched - they belong to the depth/domain contract
whose status is 'proposed' (owner gate). `--strict` (health-deep) stays RED until the owner rules.

## 2026-09-26R - the commit sitting (audit -> fix -> vault -> widen)

**State: NOTHING COMMITTED at the time of writing; HEAD 96b1e9c; index reset to 0.**

1. FORENSIC AUDIT before any commit found three real blockers: (a) rail 0 saturated by its own archive
   (BUG-547, FIXED, controls 9->10); (b) 6 live Dropbox siblings stopping the gate (MEASURED and VAULTED, no
   byte deleted); (c) rail 4 refusing the control-plane commit because `may_touch` predates the record-keeping
   surface. My own re-stage harness also over-captured (90 paths staged instead of the 42 verified ones) - the
   index was RESET before anything else was attempted.
2. RECOMMENDATION (approved by the owner this turn): WIDEN `may_touch` by FIVE NAMED PATHS (widening_log
   entry 15) - never globs - and commit the plan FIRST, which is rail 4's own declared remedy. The five:
   `DECISION-LOG.md`, `MASTER-TASK-REGISTER.md`, `agent/session_seed.yaml`, `governance/RECONCILIATION.json`,
   `governance/ROOT_CAUSE_AND_DRIFT_ARCHITECTURE_20260925.md`.
3. GOV SYNC: BUG-547 + the vault disposition appended to the buglog; `bug_status` re-derived (284 ids / OPEN
   128 / CLOSED 156, `ok bug_status`); CONTEXT_INDEX row; this block; MTR entry; `session_seed` numbers.
4. OWED: the commit sequence itself (COMMIT 0 = plan, 1 = control plane, 2 = D-2655/D-2656 + gov sync) and the
   D-2649..D-2656 narratives in `DECISION-LOG.md` (the log currently carries D-2649 only; the registry carries
   all 787 records). NEXT CODE STEP: `check_derivation_homes.py` must validate that a cited PATH-shaped
   table/column EXISTS on disk - a row can cite a nonexistent one and stay green.

## 2026-09-26S - the plan's own record was the last thing that could lie

1. **FORENSIC AUDIT FIRST** (as instructed), and it found three real things naive committing would have hit:
   (a) the R2 pin names `e9070635acdec985...` while the worktree holds `fbfd62f326d26611...` and HEAD holds
   `ca91c520791aa3f0...` - THREE digests, so the pin certifies a file that does not exist; (b) the pre-commit
   hook executes `scripts/verify_recalibration_pins.py` and `scripts/check_session_plan.py` from the WORKING TREE
   while BOTH are uncommitted (` M`) - the gate runs code that has no history (the BUG-545 class); (c) the plan
   recorded four widenings `may_touch` never granted (BUG-548).
2. **BUG-548 FIXED and made a RAIL** - the record is now checked, not remembered.
3. **NEXT**: (i) R2 pin re-mint (sha AND decision TOGETHER; new id; the meter's scoring path is byte-identical in
   behaviour, so the report is regenerated or explicitly not - never silently re-hashed); (ii) land the rails'
   own bodies so the gate stops executing uncommitted code; (iii) tighten the fnmatch matcher as its own decision;
   (iv) BUG-542 content-keyed silent-repair sites; (v) `check_derivation_homes.py` on-disk path validation.

