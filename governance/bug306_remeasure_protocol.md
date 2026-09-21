# BUG-306 — Single-coder ceiling re-measurement protocol

**State:** HUMAN-GATED — blocked on a genuinely different second human coder.
**Artifacts:** `governance/CEILING_REMEASURE_BLIND_SHEET_20260920.csv` (fresh, labels blanked).

## Why re-measure

The 2026-09-20 ceiling (κ CT 0.333 / DISC 1.000 / FORM 1.000) is **contaminated** (BUG-306):

1. **Intra-rater, not inter-rater** — the same person (`reviewer=human`) did both passes, so κ is
   an *upper bound* on true inter-rater agreement, not the ceiling itself.
2. **Ruleset mismatch** — coder-1 predates D-275b/D-282; coder-2 used them → κ partly measures a
   RULES CHANGE, not rater noise.
3. **Coder-1 bug leakage** — coder-1's quarantine labels encode the pre-fix "3+ domains"
   conflation (R147/R148 re-labelled principle/noise_drop by coder-2).

Until re-measured, treat κ CT = 0.333 as a **LOWER bound** and do NOT quote it as the human ceiling.

## Protocol (3 requirements)

1. **Genuinely different second human** — a person who did NOT do either 2026-09-20 pass.
2. **Both coders bound by the post-D-282 menu** — the current frozen menu
   (`config/closed_menu_v5.json`, menu_hash `cac6e695…`) + the D-275b decision procedure
   (`content_type_decision_procedure` in `config/content_types.yaml`). No "3+ domains" role test.
3. **Coder-1 re-scored FIRST** on the 30 rows under D-275b/D-282 (same person may re-score, but
   must use the post-D-282 menu), THEN the new coder-2 scores independently, blind.

## Procedure

1. Coder-1 fills `CEILING_REMEASURE_BLIND_SHEET_20260920.csv` (CT / DISC / FORM) using the current menu.
2. Coder-2 fills a FRESH copy independently (no peeking at coder-1's columns).
3. Merge → compute Cohen's κ per axis (CT / DISC / FORM) with `scripts/rescore_ruler_inverted.py`
   (blind label = ground truth, stored label = artefact under test — error rate, never "accuracy").
4. Compare the new inter-rater κ against the contaminated 0.333. Report BOTH.

## Blocked-on

- A second human coder (not "human", not the first-session reviewer).
- Nothing else is blocking: the menu is frozen, the sheet is blanked, the scorer exists.
