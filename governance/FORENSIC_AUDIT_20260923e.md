# Forensic audit (e) — 2026-09-23 15:53 — pre-task gate for "the next 6 steps"

Method: 7 measured passes over git / config / registry / ledger / pins / health / hygiene. Every claim below is a
receipt, not a recollection. No production pipeline/ file was modified by this audit; the ledger was opened mode=ro.
The vec repair was proved on COPIES only (scratch removed afterwards; the run DB is byte-identical to audit (d)).

## Invariants (all HELD)
| # | invariant | receipt |
|---|---|---|
| I1 | git clean at the audit vertex | HEAD 6aae15a, porcelain 0, production pipeline/ untouched |
| I2 | config parses, flags in the ruled state | 41/41 config/*.yaml parse; boundary_inject_enabled False (D-327); mtp_enabled False; abstention enabled False (status gated) |
| I3 | decision registry sane | 724 entries, 724 unique ids, 0 duplicates, parses; D-353..D-356 present |
| I4 | vec state unchanged (no silent repair) | identical to audit (d): fbs 7995 (rowids 7997..15991); vec_fbs 7995 live/7995 orphan; vec_fbs_ctx 100% dead |
| I5 | pins | 6 pinned, 0 RED |
| I6 | health | just health exit 0; 10 controls; boundary control PASS |
| I7 | hygiene | 0 tracked __pycache__, 0 tracked temp/, 0 root .bak, 0 untracked |
| I8 | no stray compute | no stray meter/stage process; scratch copies removed |
| I9 | disk | 29 GiB free (97% used) — unchanged; the chore below is still owed |

## Findings
| # | sev | finding | state |
|---|---|---|---|
| F-e1 | MED | **My own count harness was subset-scoped.** "33 decision ids, 0 dups" came from a regex anchored at column 0, which matches only the D-319..D-356 block. The registry holds **724** entries (`^\s*- id:` over a parsed load: 724 unique, 0 dups). The duplicate-D-356 repair was still valid, the COUNT was not. Same class as the 'WIRED'-contains-'RED' counter: a harness defect reported as a finding. | recorded |
| F-e2 | MED | **The derived summary had drifted 5 counts** (total_decisions 713 vs 724, summary.total, summary.active 483 vs 494, by_category ARCHITECTURE absent vs 7, MEASUREMENT 2 vs 6). A sanctioned detector existed (`scripts/recompute_decision_summary.py --check` + `tests/test_decision_summary_sync.py`) and **no recipe ran it** — a D-355 instance (the control existed, nothing invoked it). | FIXED |
| F-e3 | MED | **A receipt claimed an artifact that does not exist.** The DECISION-LOG D-356 entry says the meter was "re-run over the frozen input into a NEW dated artifact (governance/R2_DEFINITION_NLI_20260923.json)". No such file exists; the full run timed out and only a 6-FB capability smoke completed. The ratified extraction_type curve remains owed, and extraction_type stays in refused_axes. | corrected (append-only); BUG-398 |
| F-e4 | HIGH | **The vec repair recipe handed to the owner was unrunnable as written** — three defects, none of them discoverable without running it: (a) opening a vec0 table needs the sqlite-vec extension, and neither /usr/local/bin/python3 (python.org framework build: enable_load_extension UNAVAILABLE) nor the macOS sqlite3 CLI (rejects `.load`) can open it — both fail "no such module: vec0"; only /opt/homebrew/bin/python3 (sqlite 3.53.3, loader True) works; (b) "expect 0 RED" was unreachable while vec_fbs_ctx was held to the mirror contract, because emptying it converts 7995 dead entries into 7995 MISSING rows, which the old rule also called RED; (c) it named a raw CLI delete for a store whose module could not load. | FIXED (code+config), execution still owner-gated |
| F-e5 | MED | **A 50%-dead production vector index is invisible to the health path.** stage6's in-run check is a row COUNT and printed "Vector: READY 15990/7995" while half the index was dead (D2185 R-016/R-017, still live in the commit path), and config/vec_integrity.yaml says the D-354 gate is "deliberately NOT in just health until the repair lands". Until the repair lands, nothing in `just health` can see it. | recorded, sequencing correct |
| F-e6 | LOW | **Typos: measured, closed.** The only live occurrences of "computer graphic" / "media studie" are (i) the declared alias map (config/f11_llm_coder.yaml as_written -> canonical, i.e. the fix itself), (ii) verbatim historical quotes (DECISION-LOG:379, config/decisions.yaml:7582 — append-only, R-D410), (iii) corpus source text. No canonical menu surface carries a typo. | CLOSED |
| F-e7 | LOW | MASTER-TASK-REGISTER.md header still says "Updated: 2026-09-20" while the live register is governance/aggregated_remaining_tasks.md. | superseding entry appended |

## The vec repair: what is now true (proved, not argued)
The orphan rowids are the PREVIOUS generation of the spine: fbs rowids are 7997..15991 (contiguous, the live set),
the dead vec entries are 1..7996 — vectors of a generation of fbs rows that no longer exist. vec_fbs therefore
returns half-dead k-NN slots (dilution, not starvation); vec_fbs_ctx is 100% dead and R26-forbidden for production.

Proved on a copy, then on a fresh copy end-to-end:
```
python3 scripts/repair_vec_integrity.py --db <copy>          -> plan: 15990 dead rows; dry run, nothing written
/opt/homebrew/bin/python3 scripts/repair_vec_integrity.py --db <copy> --apply --no-backup
   deleted 7995 from vec_fbs / deleted 7995 from vec_fbs_ctx
   vec_fbs: REQUIRED live=7995 orphans=0 missing=0 live_pct=100.0
   vec_fbs_ctx: DORMANT live=0 orphans=0 missing=7995
   vec integrity: 2 tables checked (1 required, 1 dormant), 0 RED      exit 0
```
On the production DB, unchanged: `2 tables checked (1 required, 1 dormant), 2 RED` (exit 1).

## What this audit does NOT claim
It does not claim the run DB is repaired (it is not — that act is owner-gated). It does not claim the
extraction_type curve exists. It does not claim the six pins cover vec integrity (vec_integrity.yaml is not a
pinned artifact). It does not re-certify any retrieval number. It does not claim the disk chore is done.
