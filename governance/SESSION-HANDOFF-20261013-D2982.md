# SESSION HANDOFF — 2026-10-13 · D-2982 (the census is an INSTRUMENT) + BUG-759 (the ladder was RED)

## What this act was, and why it was chosen

Standing rule: go forward on the strategically most consequential item, and prove it before building. At session
start the health ladder was RED on one line (`check_config_defaults`, BUG-754) and the full-suite rail was
UNVERIFIED from the previous window. A red integrity rail is the highest-leverage item in the system, because
every other measurement passes through the ladder — so the act was to *measure the instrument itself* before
paying any number it printed. That discipline paid immediately: the number the rail was publishing (229) was
itself a 27% undercount.

## What landed (commit 42f8b76, 27 paths; + the governance discharge that follows)

**BUG-754 CLOSED — the visible debt, paid, on measurement rather than assumption.**
Bisected against `2b7958c` (the commit that last raised the ceiling): ZERO reclassifications and TWELVE new keys
over 14 sites introduced on 2026-10-12 (`0e28cffa` / `e11efc0b` / `3db009e9`) — the last of which RAISED the
ceiling to 229 in the same commit that incurred part of the debt it absorbed. Three of the twelve were FAIL-OPEN
GATES: `_CFG.get("serving", {})` (emptied the golden-anchoring contract in three modules),
`.get("dedup_gate", {})` with `enabled=False`/`mode="report"` leaves (silently DISABLED the D-2951 commit gate),
`.get("s5_owned_columns", [])` (emptied the S5 write-ownership contract).
Fixed with ONE loud-read idiom that **cannot express a default** (there is no parameter to pass):
`pipeline/pipeline_paths.required / required_mapping / required_sequence`. Every read PROVEN to return exactly
what its code default returned (`verification_scoped`; `True`/`report`; the 4 relationship types; `name_then_id`;
k=10 pool=0; `canonical_run`; `t11/e2e/bug198_reinject`) → a dedup of two homes, not a change of behaviour.
**241 → 229 keys, 486 → 461 sites, NO ceiling raised (D-2644).**

**BUG-758 CLOSED — the instrument.**
(a) The rule only saw `receiver.get(...)`, so `_SERVING = _CFG.get("serving", {})` then `_SERVING.get(k, v)`
escaped the census entirely (99 sites / 88 keys under a conservative reconstruction). Alias resolution is now
scope-aware and fires only on a name bound EXACTLY ONCE from a config-rooted expression — a reused local
(`s4 = load_jsonl(...)`) is NOT an alias, because noise is how a rail gets switched off.
(b) The ceiling was compared as a COUNT, so the ledger's SEVEN raises in eighteen days
(179-209-210-211-212-221-229) were each indistinguishable from real growth, and a debt that ROTATES passes
untouched. Now: a COVERAGE FINGERPRINT (rule version + receivers + glob + roots + alias rule) declared in
`config_reads`; TWO-WAY attribution that re-measures BOTH populations and separates newly VISIBLE (coverage) from
NEW (code); `config/config_defaults_census.json` as the receipt of the KEY SET; and **a raise is impossible
without `--rebaseline --because D-xxxx` where the id must already exist in `config/decisions.yaml`**.
6 new known-answer controls (14 total), several false-negative-proof by construction.
**Honest size of the surface: 568 sites / 300 shadowed-declared keys over 553 modules.**

**Spec-first (D-2978):** `specs/config_defaults_census.spec.md` + `tests/test_config_defaults_census_spec.py`,
10 passed, and the 1:1 pairing is enforced BY the contract (the spec names each test; the contract checks it).

## The ladder truth (BUG-759) — measured, with attribution

`just health-full`: **128 declaring lines, 755.8s, SEVEN faults.** Each was re-run at `42f8b76^` in a worktree and
**all seven were already rc=1** — none was D-2982's, and the ladder had been red longer than it had been measured.
Why nobody knew: `just health` reports a PREFIX (stops at the first non-zero line, BUG-573), and the D-2860
anti-circle rail refuses to run while governance state is uncommitted — so a session that MINTS cannot see the
rest of the ladder until it commits, and a session that never runs `--full` never sees it.

| # | line | before | after | verdict |
|---|---|---|---|---|
| 1 | `audit_flag_consumers` | rc=1 | **rc=0** | FIXED — a real D-339/D-2979 decision-vs-artifact conflict, resolved as a documented state change |
| 2 | `write_guard --audit` | rc=1 | **rc=2** (declared, tolerated) | FIXED — D-2981's lazy `importlib` guard import was invisible to the audit, and its fallback wrote UNGUARDED |
| 3 | `check_silent_repair` | unknown 7 (parent 4) | unknown **1** | IMPROVED — `errors="replace"` laundered undecodable bytes of the declared surface; reads are strict now |
| 4 | `check_undeclared_encoding` | rc=1 | rc=1 | INHERITED, **D-2982 added ZERO** (counts identical: 159/156, 396/392, 75/74, 4/3) |
| 5 | `check_store_columns` | rc=1 | rc=1 | INHERITED — CODE-CENSUS-MOVED; remedy is an owner-owed `--record` |
| 6 | `build_anchor_store_bridge` | rc=1 | rc=1 | INHERITED — the committed bridge no longer re-derives |
| 7 | `build_archive_index` | rc=1 | rc=1 | INHERITED — `archive/superseded_runs` in neither the index nor the declared exclusions |

Also measured this session: full suite at HEAD **457 collected / 452 passed / 0 declared red / 5 skipped** (the
previous window's unverified rail, now discharged), and all nine governance rails GREEN.

## Deliberate non-actions (each would have been a drift)

- No ceiling raised (D-2644). No test edited, skipped or weakened. No buglog history deleted (the new records were
  APPENDED, which is also what keeps that append-only receipt a prefix). The 229-key baseline was NOT swept in this
  change — it is T-102/T-113 work, per key, because each default carries its own blast radius. Pre-existing ruff
  E-rule findings in `pipeline_paths.py` (30 at HEAD) were left alone: fixing them is an unrequested sweep in a
  module with 215 importers.

## Delegation status (parallel, verified)

Two read-only audits ran in parallel to feed **T-106** (modularity/C21 + cross-OS/C26, the roadmap items the owner
asked to be recorded): a cross-OS/POSIX call-site census and a swappability/protocol census. Both completed. Their
claims are NOT yet folded into T-106 — the rule is that a delegate's output is examined, not trusted, so their
numbers must be spot-verified against the tree before they enter the register. This is the first item of the next
act, not a pending claim.

## Next critical step (in strategic order)

1. **T-101 (MUST)** — harden the retrieval golden set. Recall@10 is SATURATED at 1.000 (D-2980), so MRR (0.919) is
   the metric that gates the next retrieval change; the golden set is the thing to harden, and the anchors are
   owner-signed (D-2898/D-2939), i.e. a HUMAN GATE.
2. **T-114 (SHOULD)** — discharge the four inherited ladder faults. Two are owner-owed re-records, two are
   index/re-derive acts, and each SHRINK-ONLY ceiling must be LOWERED rather than raised (D-2644).
3. **T-113 (SHOULD)** — pay the 71 keys the honest instrument revealed, in module-sized waves, each with its own
   verification (the same discipline D-2982 used on 12).
4. **T-103 / T-104** — the owner-gated ontology items (BUG-749 residual; the 125 unlabelled open headings).
5. **T-106** — fold the two parallel audits in, after spot-verification, and name the cross-OS degradation
   behaviour.

## Honest limits of this act

- The alias rule does not collect function ARGUMENTS as bindings: an argument shadowing a module alias is not
  resolved as a shadow. Stated in the rail's docstring; unfired in this tree as of 2026-10-13, and a control must
  be added before the rule is extended (`specs/config_defaults_census.spec.md` records this).
- The two-way attribution was demonstrated in the live rebaseline (which reported `0 newly VISIBLE / 0 NEW /
  0 PAID`, correctly, since the receipt's coverage matched) and is exercised directly by INV-7 against synthetic
  receipts. A REAL coverage change has not yet been observed in production — the next rule change will be the
  first honest demonstration.
- `just health` can still only be seen in full by running `just health-full` AFTER a commit. That ordering trap is
  the root cause of BUG-759 and is not yet fixed; it is a candidate for the next governance act.
