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


## 2026-09-26S - the register that points at code stops pointing at COORDINATES (BUG-542 class fix)
1. **FORENSIC AUDIT FIRST** (as asked) found the ladder itself was lying about its own reach: `just health` RC=1 at justfile line 51 for a reason UNRELATED to the R2 pin, so the R2 OWNER-OWED red below it could not be seen at all. The cause was my owed BUG-542: a declared site keyed by a LINE NUMBER, orphaned when rail 0 grew for BUG-547 (one site, two symptoms, FATAL DRIFT).
2. **FIXED AT THE CLASS**: `scripts/check_silent_repair.py` resolves a declared site by CONTENT (`match:`) or legacy `lines:`, exactly one of the two; a dead `match` is REPORTED; two entries may not claim one site. `--check` exit 2, 0 DRIFT, 0 STALE; 24/24 controls (2 anti-overreach). D-2658 minted OPEN.
3. **NEXT**: R2 pin re-mint (meter + pin + new decision in ONE commit, never a quiet re-hash, D-382/BUG-535/BUG-542 precedent); then the rails' own bodies into git (BUG-545); then the `fnmatch` tightening decision; then the owner's depth/domain ruling.


## 2026-09-26T (post-compaction) - LANDED: COMMIT A (bridge) + BUG-549 class fix + BUG-545 hook rails

STATE: HEAD 99ad83d. FOUR commits, each gated by rails 0/3/4 at the commit boundary: b560f2b (plan widening entry
17 FIRST - ef3e95b rule) -> 36c3557 (COMMIT A: the content-keyed anchor<->corpus bridge, BUG-420/D-2658) ->
91684fe (BUG-549 class fix + D-2659 + records) -> 99ad83d (BUG-545 hook rails). The installed pre-commit hook
EQUALS its re-derivation (`bash scripts/install_git_hooks.sh --check` rc=0).

THE FORENSIC AUDIT - run BEFORE the first commit as instructed - FOUND TWO DEFECTS IN THE CHANGE-SET ITSELF:
* BUG-550 (FIXED; class OWED): the D-2659 mint had CLONED D-2658's `files`, `bugs` and `rationale` - a record
  naming the wrong module and the wrong bug. Repaired IN PLACE (it had never landed, so BUG-539 is intact) and the
  summary re-derived (source_sha256 moved). MINTING STILL HAS NO HOME AND NO VALIDATOR: OWED a receipted minter
  (next free id; non-empty title/rationale; named files EXIST; named bugs EXIST; the rationale NAMES its bugs) plus
  a cloned-payload control. UNTIL THEN: every mint is read back FIELD BY FIELD before its commit.
* BUG-551 (FIXED): the bridge exited 2 on the GOLDEN side while the config declared NOTHING - the verdict claimed a
  declaration nobody made (the BUG-548 class, receiving side). `declared_golden_unjoined:` now names both ambiguous
  rows; UNDECLARED unjoined = 1, DECLARED = 2, thin why = 1, a declaration that starts JOINING = 2 (shrink-only,
  loudly). Controls 15 -> 19; the receipt now records `unjoined_detail` (cause + candidates).

MEASURED AFTER: store-authority --check exit 0 (7 declared | 0 tombstone(s) in 2 regions | 0 faults); bridge
--check exit 2 BACKED BY the declaration (150/150 anchor rows bridged: 149 exact + 1 normalised; golden 1025/1027);
plan rail 14/14; pins rail 16/16; D-2659 reads back files=[check_store_authority.py, store_authority.yaml],
bugs=[BUG-549]; register 288 ids / 127 open / 161 closed.

OWNER GATES (unchanged, one word each): (1) promote the ANCHOR-4 depth drop-in rev 3 - HIGHEST VALUE, makes depth
gradeable, flips the 3 declared reds; (2) rule A or B on the depth/domain contract - `just health-deep --strict`
stays RED until ruled; (3) data/maxwell.db delete-or-keep (19 rows = 0.24% of the truth = wrong-answer hazard);
(4) Dropbox siblings HELD vs DISCARD. scripts/definition_nli_verify.py remains OWNER-OWED red (R2 re-mint: a NEW
decision id + a re-measurement, D-382 / BUG-535 / BUG-536) - NOT laundered into any commit above.

NEXT (mine, consequential order): (1) the mint validator (BUG-550 class); (2) the pre-image RECEIPT (file + bytes
+ sha256); (3) the read-only opener helper + the shrink-only writable-connect ceiling (159 named sites);
(4) BUG-537 archive/.DS_Store control; (5) freeze_gold_sets.py -> write_guard; (6) the check_derivation_homes
path-existence DECISION; (7) A3 eval_integrity.yaml:14 SUPERSEDED; (8) A2 per-axis quadruple + the F-11 kappa floor.

## 2026-09-26T (D-2660 - the mint joins a record's OWN FIELDS)

State: the BUG-550 class is CLOSED at the mint. scripts/recompute_decision_summary.py --mint now joins the record to the tree BEFORE a byte is written: the next FREE id (a skip is a hole indistinguishable from a deletion), bugs that EXIST in governance/bug_status.json, a payload that NAMES at least one of its own bugs (the BUG-550 tell), files that EXIST (and a list, not a comma-joined blob), and a whole-payload CLONE refused by name. 10 known-answer controls, incl. the control record itself having to PASS; wired into just health as --selftest. The fix is INSIDE the existing mint home on purpose: a second minter would be the D-2646/BUG-502 defect the register exists to prevent. FORWARD-ONLY and DECLARED: 559/790 landed records carry no title and 26 file citations do not resolve, so the rule never rewrites history (BUG-539) and the historical vector is NOT a ceiling (its only way down would be rewriting landed history). ORDER: bug registered and the register regenerated BEFORE the decision that cites it - the gate enforces it. D-2660 minted through itself (dogfood); registry stamp moved 790 -> 791 with --check green.

## 2026-09-26T (D-2661 - the COORDINATE join: existence + membership, delegated, never value)

DONE. config/derivations.yaml declares 10 derived values, each with `table:`/`column:` - and NO rail read either
field, so a row could cite a coordinate that exists nowhere while `just health` printed ok (BUG-553; the BUG-550
class a second time). scripts/check_derivation_homes.py now joins every cited coordinate to the census home its
`table` declares under `coordinate_homes:` - `document` kind (path exists, parses, `column` is a top-level key,
declared `producer_key` resolves) or `store_census` kind (DELEGATED to check_store_columns' register: rail exists,
declared table EQUALS the row's, `column` in the membership map at the DECLARED `membership:` path). A table with no
declared census home fails CLOSED. DELIBERATELY NOT DONE: no store open (vec0 makes `no such module: vec0` fatal),
no value parity (that is each row's parity_rail), no second column census (D-2646).

MEASURED: rail rc=0 - "10 registered derivation(s) ... 9 homed, 1 not homed (declared ceiling 1, shrink-only); 10
cited coordinate(s) joined to 2 declared census home(s)". Controls 7 -> 23, wired as --selftest. 3 negatives SEEN
to fire on LIVE bytes and the registry restored byte-identical (sha256 verified). CASCADE HANDLED BEFORE THE EDIT:
config/silent_repair.yaml keyed this rail's own repair site by `lines: [78]`; the edit inserts above it, which would
have reported ONE site twice (STALE + FATAL DRIFT) and aborted the ladder - re-keyed to `match:` FIRST (D-2658 on
its own register). Also corrected: the stale prose count in derivations.yaml ("9 rows, 8 homed" -> the rail measures
10 rows / 9 with a home) - the BUG-521 class. BUG-553 registered BEFORE the citing decision minted (D-2660
ordering); D-2661 minted THROUGH the gate (792 records, stamp 24223a6951829361).

OWED / NEXT: the owner's one-word SCOPE ratification is no longer blocking (the rail is in force and green); the
larger owner gates are unchanged (ANCHOR-4 rev 3 promotion; the A/B depth/domain contract ruling; data/maxwell.db
delete-or-keep; Dropbox siblings HELD/DISCARD). MY NEXT: the R2 pin re-mint; BUG-537's archive control;
freeze_gold_sets.py -> write_guard.

## 2026-09-26T (D-2662 - the PARITY join: existence + the ladder that runs it, never value)

NEXT. The derivation registry now joins three declared fields to reality: home (the one-home rule), table:/column:
(D-2661's coordinate census), and parity_rail (D-2662 - exists AND invoked by the declared ladder). The REMAINING
unjoined surfaces are OUTSIDE this registry: the R2 pin re-mint (OWNER-OWED: the meter's sha moved, and a moved pin
needs a NEW decision id WITH the measurement), BUG-537's archive control, and freeze_gold_sets.py's undeclared write.

OWNER GATES (unchanged, one word each): the depth/domain contract A/B ruling; the ANCHOR-4 depth drop-in rev 3; the
data/maxwell.db disposition (19 rows, 0.24% of truth, same table name); Dropbox siblings HELD vs DISCARD; ratify
D-2661/D-2662.

## 2026-09-26T (D-2663 - the R2 pin re-mint: certified by measurement, and the audit that found BUG-555 first)

- **WHY THIS ORDER**: the pin was the last non-owner red in the tree (scan rc=2, `OWED r2_meter`). Closing it is
  what unblocks the R2 -> S5 evidence chain, and it concerns the VERIFIER itself.
- **WHAT CHANGED**: `coder_coverage()` + `selftest()` replace the substring provenance rule and the dead
  `_read_input_text` reader; `_provenance` takes the counts from the single scoring pass; `--selftest` added and
  run by `--selfcheck`; the pin now reads e2ced5fa.../D-2663; `config/recalibration_pins.yaml`'s `rule:` prose
  states the tri-state the code actually implements (it said "RED", the rail says "OWED" - a mismatch in one record).
- **EVIDENCE**: A/B identical results sha a4c9a1d6f37433a1 (231 pairs / 21 contra / 0 errors) over HEAD ca91c520...
  vs final e2ced5fa...; controls 4/4; legacy substring rule True on the live input vs 0/40 rows with a coder key.
- **NOT DONE, DECLARED**: the scored-axis list in `label_source.column` is still prose (D-2646 second home) -
  left out so the measurement certifies exactly what it measured.

## 2026-09-26T (D-2664 - the archive rail reports its exclusions; the audit corrected its own buglog block)

WHY THIS ORDER: BUG-537 was the smallest remaining mine-owned defect, and it is the class the owner keeps paying
for - a fix whose own remedy creates the next blindspot. So the audit ran FIRST and asked the buglog's claim to
reproduce itself. It did not: the pre-image the block NAMES (`ecfe29517a941e1b...`) disproves both its numbers and its
attribution.
WHAT CHANGED: `scripts/build_archive_index.py` (`excluded` census, coverage invariant, shadowed-rule conflict,
7 controls, `--selftest`, two self-caught nits fixed), `config/archive_index.yaml` (one home for the excluded
class; `-(wal|shm|journal)$`), `justfile` (controls before the verdict), `archive/index.yaml` (regenerated,
`.DS_Store` reported as a declared exclusion, body `47532fca72a9ab9a...`).
EVIDENCE: `--selftest` 7/7 | `--check` ok (32 entries, 1 declared exclusion, 17.3 GB) | A/B
files 3/135528448 B/2026-09-19 vs files 1/135495680 B/2026-09-17 | pre-image -> now 12 deletions / 31 insertions,
which IS the fix | `just health` rc=0, i.e. the ladder that mutates the `-shm` no longer moves the index.
SIGNED REVIEW (R5): gemma-4-E4B-it-MLX-4bit, provider maxwell_omlx. Verdict: VERDICT: APPROVE (gemma-4-E4B-it-MLX-4bit, provider maxwell_omlx, 2026-09-26) - none found (read-only review of scripts/build_archive_index.py, config/archive_index.yaml, `git diff -- justfile`) - selftest: "archive-index controls: 7/7 known-answer control(s) fire" - check: "ok archive index in sync (32 entries, 1 declared exclusion(s), 17.3 GB, dispositions {'external_move_candidate': 5, 'keep': 6, 'keep_append_only': 21})" NOTE (recorded by the author, NOT by the verifier): the reviewer is a 4B-class local model; its "none found" is a signature, not a proof. The binding evidence for this pat
NOT DONE, DECLARED: the writer is still not routed through `write_guard` (it writes `archive/index.yaml` only,
declared in `config/archive_index.yaml`).
NEXT: the RAIL REGISTRY meta-rail (class i/ii/iii: a rail nothing runs, a rail whose verdict and exit code
disagree, a rail whose remedy or INPUT is uncontrolled - BUG-537 and BUG-556 are both class iii); then the R2
meter's ordered-axis list folded to ONE home; then the fnmatch tightening in `check_session_plan.py`;
`freeze_gold_sets.py` through `write_guard`; then the owner's one-word depth/domain contract ruling, which
unblocks the object-level (7,000-object / S0-S6) work.

### D-2666 - RATIFY executed (the ruler is active, the gold is the certified generation, the ladder is GREEN)

The owner ruled RATIFY on the depth/domain contract's owner gate. Executing it surfaced the real defect one layer down, and both were closed:

1. `status: proposed` -> `active` + owner_gate. The validator is gating; its 38 findings are the work list; the 7,000+ object depth/domain program is no longer measuring against an unratified ruler.
2. BUG-558 (HIGH, FIXED): the live workbook was a FOREIGN BODY - 92135 B, matching no revision of its path, 43 domain + 42 depth answers SHORT of HEAD, 38 hard findings that were really un-normalized comma-joined owner cells. Restored from `git show HEAD:` atomically, owner rulings re-applied through the sanctioned applier, foreign bytes preserved to backups/ (R-D410). The declaration had been reconciled TO the foreign body (`mac_roman`, measured off its own 0xCA byte) - all three homes now say `utf-8` with the reason; the D-2649 join REFUSED the disagreement first, which is the control working.
3. The receipt is honest again (`--backfill`, origin=backfill by design) and the pre-ruling image is a declared sealed revision locator, so the intermediate state re-derives from git rather than living in prose.
4. Ceiling 3 -> 0 (SHRINK-ONLY). `just health` rc=0, `just health-deep --strict` rc=0, 261 collected / 256 passed / 0 failed.

NEXT (in order): BUG-559 (refuse a receipt whose bytes join to no revision - with a control seen to refuse one) -> BUG-560 (the applier through write_guard) -> re-cut the workbook's receipt against the committed revision -> HEAD reconciliation with receipts -> the SEALED REVIEW PACK. OWNER: PURGE vs KEEP the two foreign-body backups; the Dropbox siblings HELD vs DISCARD decision; hooks ACTIVE.

## D-2667 + D-2668 (2026-09-26, session close) - CROSS implemented; the reconciliation landed; BUG-561 corrected

**Landed (HEAD = 11c0fe4)**
1. `6166a3d` D-2667 plan revision (entries 21-22; the two owner-gold grants NAMED, never globbed).
2. `68be49a` D-2668 permit: an owner-acked `crossing: true` is now a PERMIT with a SUBJECT, an ACK and a SPEND,
   consumed by `verdicts()` in BOTH places it must be (the FORBIDDEN set and the outside-the-plan set).
   Controls 14 -> 20, all on a synthetic baseline; a `may_touch` widening was rejected as standing permission.
3. `e3f94f4` the RECONCILIATION: 62 paths (the plan's grants + the 8 `pipeline/**` subjects of entry 23).
   `config/serving_gate.yaml` lands WITH its consumer `pipeline/serving_gate.py` and its test -> BUG-562 closed by
   construction (D-405 can no longer be violated by a COMMIT SET for this pair).
4. `11c0fe4` the crossing SPENT.

**Repaired (my own cascade, found by the ladder)**
`governance/Copy of ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv` had been reverted last session to HEAD = rev 2, which
made the write-locked rev 3 (526991cb) an ORPHAN: `verify_handoffs` rc=1, `just health` RED at justfile line 49.
MEASURED cause: the "clobber" was the DECLARED rev 3 (10 receipts sealed 526991cb/203963 B at 08:46, 08:59, 10:34 -
the bytes never changed; only mtime moved) and its delta is 3 unnamed trailing columns per row, which is why every
LINE differed from HEAD. Restored from the R-D410 backup. rev 3 exists in NO git ref: that backup was the only copy.

**Open / next**
(a) the BUG-562 PAIRING RAIL (a control SEEN to refuse a commit set whose granted artifact's consumer is withheld);
(b) BUG-559 then BUG-560; (c) BUG-563 (`backups/**` neither granted nor ignored) + the unversioned receipt ledger;
(d) the D-2667/D-2668 mints; (e) the owner drop-in rev 3 promotion (BUG-493, owner-gated).

## 2026-09-27 - D-2675 LANDED: the BOUNDARY REHEARSAL (and BUG-576 filed by it)

WHAT LANDED. `scripts/check_boundary_rehearsal.py` + `config/boundary_rehearsal.yaml`: the write boundary is exercised at a
REAL commit in a REAL repository (system temp dir, live `--separate-git-dir` layout, TRACKED HEAD bytes via `git archive HEAD`,
the hook installed by this repository's OWN installer). A real NORMAL commit and a real PARTIAL commit must both PASS through
the hook; each in-place PLANTED violation must be REFUSED by its DECLARED rail; every write-boundary rail's `--selftest` and
the git-subject module's must fire. 13/13 controls, rc=0 in 11.5s, wired into `just health` (`--selftest || exit 1` and
`|| [ $? -eq 2 ]`) and declared a WRITER in `config/rail_registry.yaml`.
WHY IT IS THE CLASS CLOSURE. BUG-527/566/568/569/574 were ONE defect: a rule about the value git HANDS its own pre-commit hook,
tested ONLY in fixtures that built their own `git init`. MEASURED: 13/13 git-subject controls GREEN while 100 percent of
commits in this repository were REFUSED. Control 12 was left RED for one session rather than papered over, and it FOUND that
provenance is SCENARIO-DEPENDENT (the same rail prints `ambient_note` at a normal commit and `partial_note` at a partial one),
which the config had declared once per rail; the fix is a declared per-rail `partial_note` plus a scenario-declared
`note_field`, with a NEW control (`partial_note_declaration_is_read`) so the declaration itself is seen to be load-bearing.
FORENSIC AUDIT (before landing, as instructed): blast radius MEASURED - the fixture is a system-temp path, the live tree's
dirty count (117) and the installed hook's sha (fc4baec26489c0f6) are IDENTICAL before and after; the fixture is clean after
every scenario; the rails inside it read the FIXTURE's own config and plan; no pinned artifact was staged. One finding was
hardened on the spot: the fixture must resolve OUTSIDE the tree it audits, fail-closed and derived from the rail's own
location, because `git clean -qfdx` and rmtree run there.
FILED BY THE REHEARSAL: **BUG-576** - a FRESH repository cannot make its FIRST commit (RAIL 0 reads an UNBORN HEAD as broken
metadata; the same state the BUG-400/BUG-564 recovery route produces). The rehearsal carries a declared `--no-verify`
bootstrap that MUST BE WITHDRAWN when BUG-576 is fixed.
GOV SYNC: D-2675 minted (806 records, stamp 3e277d4070884474); register re-derived (314 ids, OPEN 138 / CLOSED 176);
session_plan entry 25 recorded with NOTHING WIDENED; DECISION-LOG.md, MASTER-TASK-REGISTER.md, agent/session_seed.yaml and this
RECALL MAP updated in the same change-set.
OPEN / NEXT (in consequential order): (1) BUG-576 - teach RAIL 0 to tell an UNBORN HEAD from broken metadata, then WITHDRAW
the bootstrap declaration; (2) BUG-575 - supersession COMPLETENESS + IN-FORCE for cited decisions (16 measured findings);
(3) BUG-573 - the ladder must collect EVERY fault before it exits, so one RED cannot hide the next; (4) the MUTATION GATE:
`config/rail_mutations.yaml`, one declared mutation per rail and the control that must go RED under it; (5) the standing rule
this session recommends: **no new rule lands without (i) one home, (ii) a boundary control, (iii) a named oracle, (iv) a
mutation that reds it.**

## 2026-09-27 (cont.) - D-2676 AUDITED, MINTED, COMMITTED; BUG-577 filed BY the audit

FORENSIC AUDIT BEFORE THE COMMIT (the owner's standing instruction): breaks / cascade / drift / blindspot / gap / conflict / hidden
failure / error leak / mismatch / bloat.
- FIXED IN THE LANDING: (1) the gate's own selftest RESTATED the boundary rehearsal's control count (13/13) - a second home of a declared
  fact (D-2646) inside the rail that enforces C12; (2) measure()'s docstring claimed the SUBJECT's bytes are restored while the code
  restores the FIXTURE copy - a declaration/reality mismatch in the artifact about declaration/reality joins.
- FILED: **BUG-577** - outside_tree (the BUG-537 rule) is ONE rule in TWO rails; remedy = ONE HOME scripts/lib/fixture.py + a refusal
  known-answer control + a mutation entry that reds it.
- THE MISSING MINT IS CLOSED: last session's --apply never landed, so DECISION-LOG carried D-2676 while config/decisions.yaml did not.
  MEASURED now: 807 records, stamp 9090685c33a0f103, --check green, D-2676 present. The mint's OWN refusal (a record may cite only
  REGISTERED bugs, D-2660) is what surfaced the finding below. BLINDSPOT, DECLARED: nothing in the ladder REDs on a DECISION-LOG entry with
  no registry record - the mint is the only join, and it is run by hand.
- MEASURED, NOT NEW: BUG-492 is cited 32 times in the buglog yet is NOT in the register - evidence for BUG-571's remedy.
- DECLARED DEBT, DELIBERATELY NOT COMMITTED: coverage.required_subjects names 2 rails while the standing rule covers every rule;
  governance/*.jsonl + drift_report_* + bench_preflight_* + backups/** are untracked RAIL OUTPUTS with no GRANTED or DECLARED-EXCLUDED home
  (BUG-563). The commit is SELECTIVE; bench_preflight_latest.json, human_review_ledger.json and remaining_verification_audit.csv stay DIRTY
  because no may_touch entry grants them (RAIL 4 would refuse them).
- JUDGED ACCEPTABLE, NOT FIXED: a 200-character message truncation (presentation, not a fact about the world); the fixture copies all of
  scripts/ + config/ (~725 files, ~10s) so a rail's own imports resolve; the gate NEVER writes the live tree.
- TOOLING DEFECT THAT COST TWO SESSIONS, NOW NAMED: wrapping an SDK object return in String() throws 'Cannot convert object to primitive
  value', so a call that DID land reports as failed - the exact reason D-2676's mint looked unlanded. Verify by READING, never by the wrapper.
BASELINE + FINAL: just health rc=0 BEFORE and AFTER (rail-mutation controls 15/15 in both runs).
COMMIT: the commit that CARRIES this line (re-derive with git log -1 --format=%h); D-2675 and D-2676 land together.
NEXT (consequential): (1) BUG-576 - the standing rule's FIRST APPLICATION: teach RAIL 0 to tell an UNBORN HEAD from broken metadata, land it
WITH a boundary control and a mutation entry that reds it, then WITHDRAW the declared --no-verify bootstrap in config/boundary_rehearsal.yaml
(a paid debt returns 2 OWNER-OWED until withdrawn). (2) BUG-577 - one home for outside_tree. (3) BUG-575 - supersession COMPLETENESS +
IN-FORCE for cited decisions. (4) BUG-573 - the ladder must collect EVERY fault before it exits. (5) extend coverage.required_subjects to
RAIL 0 and the write-boundary rails.


## 2026-09-27 (cont.) - D-2677 LANDED / BUG-576 FIXED

BUG-576 FIXED (RAIL 0 BORN/UNBORN/BROKEN from three DECLARED probes; 4 new real-repository controls; selftest
15/15). The --no-verify bootstrap is WITHDRAWN and replaced by THE BYPASS RULE (D-2677): `temp.bootstrap.refusal`
is re-measured every run, `declared_debt` is EMPTY, and the rehearsal's first commit is an ACCEPTANCE control
(18/18). The standing-rule gate now covers RAIL 0 (`unborn_head_branch_is_load_bearing`, floor 4, 3/3 subjects).
MINTED D-2677 (808 records, stamp 80c07d4142d20208). NEXT, in order: (1) BUG-578 - the rehearsal rehearses HEAD,
so overlay the WORKING TREE bytes of the declared subjects into the fixture BEFORE installing the hooks (measured:
'bash scripts/install_git_hooks.sh --check' rc=0 after the overlay), with a control that REDs if the overlay is
dropped; (2) BUG-577 - ONE home for outside_tree (scripts/lib/fixture.py) plus a refusal control and a mutation,
and move the nested RAIL 0 fixture builder there; (3) BUG-575 supersession completeness; (4) BUG-573 the ladder
must collect EVERY fault; (5) BUG-571 the cited-by-decision join.

## 2026-09-27 (cont.) - D-2678 LANDED / BUG-578 + BUG-579 FIXED

The rehearsal now rehearses the bytes that LAND. `just health` HEALTH_RC=0 with the strongest evidence to date:
`ok boundary rehearsal: ... 436 working-tree file(s) of the declared subjects overlaid onto the materialized HEAD
bytes, 5 rail selftest(s) fire, 0 declared debt(s) open` and `ok rail mutations: 4 declared rule(s) SEEN to red
through their own control, 1 negative control(s) stayed green, 3/3 declared subject(s) covered`.
ORDERED NEXT: (1) coverage.required_subjects -> RAIL 3/4/5; (2) BUG-577 outside_tree ONE home + refusal control +
mutation; (3) BUG-575 supersession completeness (24 pinned legacy_debt_ids); (4) BUG-573 the ladder must collect
EVERY fault; (5) BUG-571 the cited-by-decision join (BUG-492 live case). OWNER GATE: CONSTITUTION promotion of the
standing rule stays HOLD; BUG-431 CONTENT promotion is the one open gate.

## 2026-09-27 (cont.) - D-2679 LANDED / BUG-580 + BUG-581 FIXED

STRONGEST MEASURED EVIDENCE: `check_rail_mutations --check` rc=0 -> "7 declared rule(s) SEEN to red through their own
control (unborn_head_branch_is_load_bearing, provenance_count_is_load_bearing, widening_record_rule_is_load_bearing,
overlay_of_the_landing_bytes_is_load_bearing, laundering_repin_rule_is_load_bearing,
withdrawn_consumer_rule_is_load_bearing, boundary_registry_join_is_load_bearing), 1 negative control(s) stayed green,
6/6 declared subject(s) covered (4 derived from the commit boundary, D-2679)", 8.4s; `--selftest` 18/18;
`check_boundary_rehearsal --selftest` 21/21; `check_declaration_consumers --selftest` 11/11; mint D-2679 (810 records,
stamp b6e80486982b3b52); bug_status OPEN 138 / CLOSED 181 of 319.

WHAT LANDED: the coverage of the standing rule is DERIVED from the ONE home of the commit boundary
(`config/rail_registry.yaml#commit_boundary`), declared under `coverage.boundary_join` and joined in
`scripts/check_rail_mutations.py#boundary_rails`; a commit-boundary rail that is not covered is FATAL. RAIL 3 and RAIL 5
got the mutations proving their rules are read; the gate got one for its own rule; `min_mutations` 5 -> 8; the gate is
now a declared consumer of the rail registry. BUG-581 fixed a rationale attached to the wrong edge.

ORDERED NEXT: (1) BUG-577 (ONE home `scripts/lib/fixture.py#outside_tree` + refusal control + mutation - the same
fixture family); (2) BUG-575 supersession completeness (24 pinned legacy_debt_ids); (3) BUG-573 (the ladder must collect
EVERY fault: one RED currently hides the next); (4) BUG-571 (the cited-by-decision join; BUG-492 is its live case);
(5) TASK: declared homes for the 3 dirty rail outputs + `backups/**` (BUG-563), and BUG-560 (write_guard route).
OWNER GATE: the standing-rule promotion ruling is now DUE (the bar is met; any promotion must be a POINTER to
`config/rail_mutations.yaml` + `scripts/check_rail_mutations.py`); BUG-431 CONTENT promotion remains the other gate.

## 2026-09-27 (cont.) - D-2680 LANDED / BUG-573 FIXED (THE WHOLE-SET RULE)

STRONGEST MEASURED EVIDENCE. `just health-full` -> **87 line(s) RUN, 0 fault(s), 203.0s**, SCAN_RC=0. For the
first time the question "what is left in the ladder?" has a measured answer instead of a prefix: EMPTY. Cost is
attributable per line (check_tests 82.1s, yaml_guard 45.3s, boundary rehearsal 14.4s, rail mutations 8.6s).

WHAT LANDED. scripts/run_ladder.py (collector + derived banner + 12 known-answer controls, no fixture, no
writer); justfile#health gains the banner (printed BEFORE any rail can abort) and the collector's --selftest;
justfile#health-full is the whole-set entry point; config/rail_registry.yaml stays the ONE home of the line list;
config/rail_mutations.yaml floor 8 -> 9 and subjects 6 -> 7 with the new mutation SEEN to red; the new consumer
edge (run_ladder reads the registry) staged in the SAME commit (BUG-562 class); BUG-573 closed - NO new bug was
filed by this change.

ORDERED NEXT. (1) BUG-577 ONE home scripts/lib/fixture.py#outside_tree (+ refusal control + mutation);
(2) BUG-575 supersession completeness (24 pinned legacy_debt_ids); (3) BUG-571 cited-by-decision join (BUG-492
its live case); (4) PRODUCT (default lane): BUG-563 declared homes for the 3 dirty rail outputs + backups/**,
then BUG-560 write_guard route.

OWNER GATE (DUE). The standing-rule promotion ruling (bar MET; a promotion must be a POINTER, never a
restatement) and BUG-431 CONTENT promotion. RECOMMENDATION: rule the META-LANE FREEZE now - the machinery has
spent ~37 of the last 40 bugs on itself, and it has just proven the ladder is clean in one pass, which is the
precondition for switching to product work.

## 2026-09-27 (cont.) - D-2681 LANDED / BUG-577 FIXED + BUG-582 FIXED (THE ONE-HOME FIXTURE RULE)

STRONGEST MEASURED EVIDENCE. just health-full -> 89 line(s) RUN, 0 fault(s), 262.3s, SCAN_RC=0. scripts/lib/
fixture.py --selftest 6/6. Mutation gate: 9 declared rule(s) SEEN to red, 8/8 subjects covered (4 derived from the
commit boundary), 1 negative control green. Rail registry rc=0, declaration consumers rc=0.

WHAT LANDED. (1) BUG-577: ONE home scripts/lib/fixture.py (outside_tree + real_repo), three callers import it,
the inline copies DELETED - the module declares nothing from config (C12) and no caller's vocabulary (C12d).
(2) BUG-582: the D-2680 justfile landing was PARTIAL - the banner line and the collector --selftest were declared
in four governance homes and present in NO file; both are now in 'health', banner FIRST.

ORDERED NEXT. (1) BUG-575 supersession completeness (24 pinned legacy_debt_ids, D-2645); (2) BUG-571 the
cited-by-decision join (BUG-492 cited 32x and unregistered is its live case) - the DECISION LAYER is the least
railed surface, and until these two land a decision is declared, not gated; (3) PRODUCT (default lane): BUG-563
declared homes for the 3 dirty rail outputs + backups/**, then BUG-560 (write_guard route).

OWNER GATE (DUE). (a) rule the META-LANE FREEZE; (b) the standing-rule CONSTITUTION promotion (bar MET, POINTER
never a restatement); (c) BUG-431 CONTENT promotion.

## 2026-09-27 (cont. 2) - D-2682 LANDED / BUG-575 FIXED (THE DECISION GRAPH: succession is a LINK, force is READ)
STRONGEST MEASURED EVIDENCE. python3 scripts/reconcile.py --selftest -> 9/9 known-answer control(s), both directions, rc=0. python3 scripts/reconcile.py --check -> 'decision_supersession_complete: every SUPERSEDED record names a resolvable successor in 812 record(s); 12 pinned legacy id(s) still owed' and 'decision_citations_in_force: 59 citation site(s) all name a decision IN FORCE; 4 declared forward reference(s) still owed; every state word in the registry is classified' -> rc=0. Mutation gate: config/rail_mutations.yaml#decision_supersession_rule_is_load_bearing SEEN to red through its own marker; floor 10 -> 11, subjects 8 -> 9. Rail registry: 89 ladder invocation(s), rc=0.
WHAT LANDED. config/decisions_policy.yaml#graph (the RULES, one home); scripts/reconcile.py (two declared check kinds + PURE predicates + the NAMED oracle --selftest, reusing the existing citation walker); config/reconciliation.yaml (two entries); config/rail_mutations.yaml (the teeth); justfile (the selftest is its OWN declaring line, so the boundary control is SEEN, D-2676 ii).
ORDERED NEXT. (1) BUG-571 - the cited-by-decision join (a decision citing an unregistered bug must become an owner-owed RED LINE; BUG-492, cited 32x and unregistered, is the live case) - after which the META LANE CLOSES; (2) PRODUCT (default lane): BUG-563 then BUG-560; (3) BUG-583 (LOW, filed here).
OWNER GATE (DUE). (a) rule the META-LANE FREEZE; (b) the standing-rule CONSTITUTION promotion (bar MET, POINTER never a restatement); (c) BUG-431 CONTENT promotion.

## 2026-09-27 (cont. 3) - D-2683 LANDED / BUG-571 FIXED / THE META LANE IS CLOSED

STRONGEST MEASURED EVIDENCE. `just health-full` (pre-change, owed from the previous turn): "ok ladder scan: 90
line(s) RUN, 0 fault(s), 220.3s" - the whole fault set in ONE pass, and it is EMPTY. check_register_divergence
--check: "ok register divergence: 0 declared divergence(s), all still divergent; 62 named-but-uncarried id(s)
declared, all still uncarried; ceilings 0/62 (shrink-only); 321 id(s) carried" rc=0. --selftest 10/10 rc=0.
Mutation gate rc=0: 11 declared rule(s) SEEN to red, 10/10 subjects covered, floor 11 -> 12. Rail registry rc=0 (90
ladder invocation(s), 43 rails, 2 dormant, 5 declared writers). Declaration consumers rc=0. yaml-guard --check rc=2
= 4 declared owner-owed artifacts (unchanged, loud, not fatal).
WHAT LANDED. The register's SECOND divergence shape: 62 ids the LOG names and no HEADER carries are now a declared,
identity-pinned, shrink-only debt in the SAME home that already owned the first shape (config/register_divergence
.yaml), evaluated by ONE pure verdict, SEEN by 10 synthetic controls, and given teeth by a mutation. Nothing was
backfilled (D-2645). The recorded remedy (a join inside bug_status.py) was AMENDED, not silently dropped.
ALSO MEASURED (filed, not worked - the freeze). BUG-584: the BUG-582 fix added 4 justfile lines where 2 were
intended (justfile:7 == justfile:8 byte-identical), so three lines RUN TWICE and the ladder over-reports its own
size - invisible to every rail, because check_rail_registry.py keys its census by invocation (a set) while
run_ladder.py counts raw lines.
ORDERED NEXT (product lane, default). BUG-563 (declared homes for governance/bench_preflight_latest.json,
governance/human_review_ledger.json, governance/remaining_verification_audit.csv + backups/**), then BUG-560
(scripts/apply_workbook_rulings.py through scripts/lib/write_guard.py).
OWNER GATE (DUE). The META-LANE FREEZE ruling (its one exception is spent); the standing-rule CONSTITUTION
promotion (POINTER only); BUG-431 CONTENT promotion; BUG-583 (5 lowercase 'active' spellings vs a declared rule).

## 2026-09-27 (cont. 4) - D-2684 LANDED / BUG-563 FIXED / A DIRTY PATH HAS TWO DECLARED HOMES
STRONGEST MEASURED EVIDENCE. `just health-full` (the POST-change whole-set scan owed from cont. 3): **91 line(s)
RUN, 0 fault(s)** - the fault set is EMPTY in one pass. BUG-563 before: 124 dirty paths, 1 granted, 123 in NO
declared home (112 `backups/**` pre-images C13 obliges, 3 modified stores, 8 untracked artifacts). After: `ok
repo-integrity worktree: 14 dirty path(s) - 14 granted by governance/session_plan_20260924.yaml, 0
declared-excluded, 0 in neither home` rc=0; `--selftest` 6+15 controls rc=0; mutation gate SEEN red, floor 12 ->
13.
WHAT LANDED. `.gitignore` declared exclusions; `config/repo_integrity.yaml#worktree` (the ONE HOME: the granting
home is CONSUMED, the three exclusions are declared with a why); `scripts/check_repo_integrity.py --worktree`
(PURE `worktree_faults()`, raw NUL-separated dirty read, git-joined `is_ignored()`), wired into the ladder; 7
NAMED grants in the plan (`.gitignore` + 6 indexed stores, incl. the R-D410 receipt ledger) + widening_log entry
26.
ALSO MEASURED (the rail refusing ITS OWN patch, first run). A trailing `#` is NOT a comment in `.gitignore`, so
the three lines I first wrote were literal patterns matching nothing: the rail answered `declared-excluded
'backups/**' is NOT ignored by git (probe 'backups/x')`. And the shared `git()` helper STRIPS output, eating the
leading space of the status field (" M .gitignore" -> path "gitignore"); `dirty_entries()` now reads raw bytes.
ORDERED NEXT. (1) product lane: BUG-560 (write_guard routing for apply_workbook_rulings.py); (2) the declared
follow-up: the hook moment for the BUG-563 rule once a plan entry can land WITH the artifact it grants; (3) the
frozen background (BUG-564 remainder, BUG-572, BUG-583, BUG-584, BUG-559).
OWNER GATE (DUE). META-LANE FREEZE ruling; the standing-rule CONSTITUTION promotion (POINTER only); BUG-431
CONTENT promotion; BUG-583 (canonicalise the 5 lowercase 'active' spellings vs declare the rule).

## 2026-09-27 (later) - BUG-560 FIXED (D-2685): the owner-ruling applier passes through write_guard

LANDED. scripts/apply_workbook_rulings.py writes the workbook through write_guard.write_rows(mode="merge",
owned_keys=<the ruled columns>) and appends the fixlog through the new write_guard.append_lines (SUFFIX-ONLY).
The CELL SCOPE has ONE home (config/anchor_workbook_fixes.yaml#rulings_io.owned_columns) joined by a pure
scope_faults(); config#rulings_io.backup_dir/backup_suffix DELETED; config/artifact_ownership.yaml#owned_by
completed (+3 columns) and the fixlog declared append_only with a writer_of_record.
STANDING RULE (D-2676) SATISFIED: ONE HOME (config#rulings_io.owned_columns); SEEN boundary (justfile --selftest
+ --check - both DECLARED in three homes since D-387 and RUN in none, the BUG-582 shape on the anti-revert rail);
NAMED oracle (applier --selftest 14 controls; write_guard --selftest 13 invariants / 6 refusals, both counts now
DERIVED from the source that ran); MUTATION (4 entries, floor 13 -> 17, all SEEN to red).
FOUND IN THE PRE-COMMIT AUDIT OF THIS CHANGE-SET (two defects of my own): the fixlog control's expectation named
ONE line while the ruling writes TWO cells; and the selftest deposited 5 fixture pre-images in the LIVE
backups/ (write_rows backs up by default) - removed through pipeline/safe_delete.py, and a NAMED control now
asserts nothing under backups/ appears.
MEASURED. applier --selftest 14/14; --check green (4 cell rulings, 5 row declarations, scope 5 columns);
write_guard --selftest green; `just health` rc=0; mutation gate `ok rail mutations: 16 declared rule(s) SEEN`
(floor 17); write_guard --audit 7/10 declared writers guarded (ceiling 3, owner-owed, not fatal).
NEXT. (1) product lane: BUG-564 remainder (the hook ROUTE as a declared subject), BUG-572, BUG-583, BUG-584;
(2) OWED: a whole-set scan for the leak class this fix found in its OWN selftest (which `--selftest` writes
deposit pre-images into the tree they audit?); (3) DECIDE config/derivations.yaml (rail re-measure 211 -> 212);
(4) the frozen background is unchanged. OWNER GATE (DUE): META-LANE FREEZE ruling; the standing-rule CONSTITUTION
promotion (POINTER only); BUG-431 CONTENT promotion; BUG-583.
