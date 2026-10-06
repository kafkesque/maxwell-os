# FORENSIC AUDIT — D-2822 Gate A(d) implementation (2026-10-05)

**Scope:** Landing the D-2822 S5 aggregation code limb (OR-entail + AND-no-contradiction) in
`pipeline/stage5_verify.py`, config-gated behind `stage5.nli_aggregation`, plus governance sync
(BUG-651 filed, D-2842 minted).

**Verdict:** NO BREAK, NO CASCADE, NO DRIFT. Additive, config-gated (default preserves current
behavior), fail-closed on unknown config. One governance drift (BUG-647 header-vs-body status)
is prose-only and non-blocking.

## Findings

- **F-01 — BREAK:** NONE. `_b2_majority_verdict` untouched; new `_or_entail_and_no_contra_verdict`
  is additive. 8 existing B2 tests + 8 new tests = 16 passed. Import sanity confirms `NLI_AGGREGATION='majority'`.
- **F-02 — CASCADE:** NONE. `nli_calibrate.py` imports only `_load_dual_encoders`/`_nli_pair_scores`,
  NOT the aggregation primitive, so its threshold sweep is unaffected. Score contract preserved (`max(entail)`).
- **F-03 — DRIFT:** NONE in code. Default `nli_aggregation: majority` means zero behavior change until
  the operator flips the flag after D-2822 recalibration (deliberate, fail-safe).
- **F-04 — BLINDSPOT:** CLOSED. The old majority rule's two failure modes (hide a supported claim;
  pass a both-entail-and-contradict claim) are now explicitly covered by tests `test_single_entail_among_neutral_passes`
  and `test_many_entail_with_one_contra_vetoes`.
- **F-05 — GAP:** RESOLVED. The D-2822 "NOT yet executed" decision now has its code limb. The flip +
  recalibration + re-run S5 remain OPERATOR steps (documented, not code gaps).
- **F-06 — CONFLICT:** NONE. Config-first (C12); unknown `nli_aggregation` value raises (C16), no silent default.
- **F-07 — BUG:** ONE GOVERNANCE DRIFT FOUND (pre-existing, not introduced here): BUG-647 header-table row
  says "FIXED (D-2833)" while its `## BUG-647 (IN PROGRESS…)` body header — the machine-read slot — says
  IN PROGRESS. `scripts/bug_status.py` correctly reads IN PROGRESS (the code is changed but pending menu-v6
  commit). Prose-only; left as-is, flagged for the next menu-v6 commit.
- **F-08 — HIDDEN FAILURE:** NONE. Fail-closed on unknown aggregation mode at import; no silent fall-through.
- **F-09 — ERROR LEAK:** NONE. The new function mirrors `_b2_majority_verdict`'s pure, exception-free contract.
- **F-10 — MISMATCH:** NONE. Decision D-2822 state=RATIFIED; D-2842 records the execution; census re-derived
  (972 decisions, stamp 109b972746d4a22c). BUG-651 filed + registered (390 bugs, 146 open).
- **F-11 — BLOAT:** NONE. ~65 lines added; one config key; no dead code, no `__pycache__`, no `_OLD` files.

## Governance sync performed
- BUG-651 filed (S5 majority aggregation wrong ontology) — header row + body section; `bug_status.py` re-derived.
- D-2842 RATIFIED (Gate A(d) code limb) via `recompute_decision_summary.py --mint --apply`.
- Census: 972 decisions / stamp `109b972746d4a22c`; bugs 390 (146 open / 244 closed).

## Next critical steps (BUG / TASK / DECISION)
See `MASTER-TASK-REGISTER.md` tail. Owner-gated ADOPT path unchanged; remaining executable work below.
