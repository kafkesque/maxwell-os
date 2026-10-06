# Forensic Audit — BUG-631 Reader-limb (D-2843) landing

**Date:** 2026-10-05 · **Decision:** D-2843 RATIFIED · **Files:** scripts/check_domain_cardinality.py, tests/test_domain_cardinality_reader.py

## Verdict: NO BREAK · NO CASCADE · NO DRIFT (introduced). Additive, read-only, fail-closed.

## F-01 — BREAK: none
Additive reader script. No existing module imports it; nothing in the pipeline calls it at runtime. `python3 -m pytest tests/test_domain_cardinality_reader.py` → **9 passed**. Live run exits 1 (drift) as intended.

## F-02 — CASCADE: none
The reader is a leaf: it imports `io_guard.safe_write` and `pipeline_paths.DB_PATH/MAX_DOMAINS_PER_FB` (both pre-existing, unchanged). It writes only an opt-in `--json` receipt via C6 crash-safe `safe_write`; default run touches nothing on disk.

## F-03 — DRIFT (introduced): none
Config-first: `MAX_DOMAINS_PER_FB` from `pipeline_paths.py:135` (= `pipeline_config.yaml`), `DB_PATH` from `:530` (env `db_path` override). No hardcoded path/threshold/magic number (C12/C20). Receipt schema versioned (C14-style stamp).

## F-04 — BLINDSPOT: closed
The defect class that produced BUG-631 was "count the wrong column." The reader counts ONLY canonical `domains`, never `domains_raw`, and the control test `test_measure_store_counts_only_canonical_domains` pins that. Parse-defects are NAMED (`count_domains` returns a reason), never silently zeroed (C16).

## F-05 — GAP: confirmed closed on the reader side
`scripts/check_domain_cardinality.py` was MISSING (the D-2838 "REMAINING" item). It is now present and reproduces the BUG-631 finding: **52 over-cap FBs (46@6 + 6@7) of 14,574 total (0.36%), all CLEAN.**

## F-06 — CONFLICT / MISMATCH: one pre-existing, fixed this turn
BUG-647 header-table said `FIXED (D-2833)` while its machine-read body header said `IN PROGRESS` — the body slot is what `bug_status.py` reads, so the register miscounted BUG-647 OPEN. Reconciled: body header now `FIXED`. Register re-derived: **145 open / 245 closed** (was 146/244).

## F-07 — BUG / HIDDEN FAILURE: none introduced
Exit-code contract is fail-closed: 0 = clean, 1 = drift (over-cap found), 2 = parse-defect. A mis-parse cannot read as a clean pass (returns 2, not 0).

## F-08 — ERROR LEAK: none
`except (FileNotFoundError, sqlite3.Error)` logs AND exits non-zero; no bare `except`, no swallowed failure (C16).

## F-09 — MISMATCH (stale declaration, flagged NOT fixed)
`config/store_authority.yaml` declares the authoritative store at **7,995** fbs rows (measured 2026-09-26); the store now holds **14,574** rows (rechunk-v4-20260929 landed). Flagged for refresh at the menu-v6 commit — it is a stale declaration, not a data defect, and out of scope for this read-only landing.

## F-10 — BLOAT: none
No new dependency (stdlib `sqlite3`/`json`/`argparse` only), no dead code, no `__pycache__` (C19).

## F-11 — R5 (generator ≠ verifier)
9 control tests are the verifier limb for the reader. Generator is this agent; the verifier is the pytest suite (different artifact, mechanical). C11 satisfied; no self-verification.

## Governance census (post-mint)
Decisions: **973** (D-2843 appended) · stamp `ae6db643a2f879d6` · bugs 390 (145 open / 245 closed). D-2839 remains PROPOSED (owner gate, intentionally not self-flipped).
