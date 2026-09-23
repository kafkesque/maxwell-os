# Forensic audit (f) - 2026-09-23 16:08 - pre-task gate for "the next 4 steps"

Method: measured passes over git / config / registry / pins / health / hygiene, plus the three surfaces the four steps
touch (the stage6 commit path, the R2 meter, the dead defaults). Every claim below is a receipt. No production run was
executed; the ledger was opened read-only; the only DB writes were throwaway test fixtures under temp/.

## Invariants
| # | invariant | receipt |
|---|---|---|
| I1 | git clean at the audit vertex | HEAD d2a7faa, porcelain 0 |
| I2 | config parses, no code/config drift | 50/50 config yaml parse; config_audit --check-unchecked --strict: 0 drift |
| I3 | registry sane | 725 entries, 725 unique ids, 0 dups; recompute --check in sync |
| I4 | vec state unchanged | production gate still "2 tables checked (1 required, 1 dormant), 2 RED" - no silent repair |
| I5 | pins | 6 pinned, 0 RED |
| I6 | health | just health exit 0, 13 controls + status/integrity |
| I7 | hygiene | 0 tracked pycache, 0 root .bak, 0 untracked |
| I8 | no stray compute | no stray stage/meter process (the ruler meter finished and exited) |
| I9 | disk | 29 GiB free (97%) - the chore is still owed |

## Findings
| # | sev | finding | state |
|---|---|---|---|
| F-f1 | MED | The new vec contract test SKIPPED under every interpreter that can run pytest (framework python cannot load vec0; the homebrew python that can has no pytest and numpy/pytest absent), so "5 skipped" read like coverage. | FIXED: the test self-runs (__main__), 5/5 PASS on /opt/homebrew/bin/python3 |
| F-f2 | MED | The ruler meter artifact was produced under menu_hash d2fc500c..., the corpus artifact (v2) under 73597ee2... The menu changed after the corpus run, so an axis score from one artifact may NOT be compared with the other; a curve over the ruler is only valid within its own artifact. | recorded (provenance note on the artifact) |
| F-f3 | MED | BUG-387 was OPEN in the commit path: the R-016 completeness check was still a COUNT and the R-017 orphan COUNT printed a warning nobody acts on. A count cannot see a half-dead index. | FIXED code-side (D-359 PROPOSED); R5 review + scratch rehearsal owed |
| F-f4 | LOW | BUG-397(a): the classifier golden default resolved to a retired path (silent). | FIXED to the archived path |
| F-f5 | LOW | BUG-397(b): dspy_program_path is absent in config AND hardcoded as its own fallback in pipeline_paths.py:186 - a one-site fix would not fix it. | OPEN, two-site fix handed over |
| F-f6 | MED | The 50%-dead production vector index is still invisible to just health. Deliberate sequencing (the D-354 gate would RED the whole panel for a known, owner-gated act), but it means the defect is visible only in governance, not on the panel. | sequencing unchanged; gate wired the moment the repair lands |

## What this audit does NOT claim
That the run DB is repaired (it is not - owner-gated). That the extraction_type curve exists (the artifact exists; the
CURVE - a gate measurement over it - does not). That the stage6 change is verified (it is unit-verified, not
run-verified, and it has not been applied to any run). That the disk chore is done. That health sees the vec defect.
