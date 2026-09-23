# FORENSIC AUDIT 2026-09-23 (b) - the abstention re-rate, the wiring claim, and the dangling inputs

Scope: everything written by D-348..D-353 plus the governance dependencies that quote the superseded figures.
Method: run the checks, re-score the artifacts, and read the wiring itself (never the diff that was supposed to contain it).
Invariant held: **no production code touched** (pipeline/ diff empty), no LLM, no new inference, no label/menu/definition change.

| # | sev | finding | state |
|---|---|---|---|
| F1 | HIGH | `just health` did NOT run verify_menu_routing.py or verify_menu_policy.py - 5 verify lines, no recipe mentioned them; the D-346/D-350 claim "wired as the 12th health check" was contradicted by the artifact (BUG-393) | FIXED - all three checkers wired with || exit 1; health must be RUN, not diffed, to verify wiring |
| F2 | HIGH | The ratified abstention points were superseded by D-352 (0.4741/116 unreconstructible; discipline -8.3pp -> -5.33pp; content_type gain CI [-1.81,8.86]) | RE-RATIFIED as D-353 by the lower-CI-bound rule; discipline adopted at 25%, content_type rejected at 30% |
| F3 | HIGH | Floors and artifacts still quote the superseded 0.4741: config/eval_integrity.yaml:341, config/incumbent_ruler_score.yaml:45, config/knn_arm.yaml:14, governance/REPRESENTABILITY_SWEEP_20260923.md:76, governance/R3_HELDOUT_RESULT_20260921.md:36,40 | POINTER RECORDED, floors deliberately NOT rewritten (protected file, owner call G4a) |
| F4 | MED | Dangling references: ANCHOR1_BLIND_SHEET_20260920.csv / ANCHOR1_KEY_20260920.json are cited by 7 artifacts (ARTIFACT_REGISTRY.md, R3_HELDOUT_PREREG/RESULT, the anchor2 bakeoff spec) and do not exist | OPEN - blocks the R3 held-out run |
| F5 | MED | The ANCHOR-3 consolidation inputs (temp/LLM_LABELS_R2_ALL150.jsonl, temp/kimi3 labels01.md) are referenced by the ruler artifact but temp/ has 509 files and 0 tracked in git | OPEN - the ruler cannot be reproduced from a clone (future tax) |
| F6 | MED | content_type: the floor file quotes error 0.3533 (97/150) while the R2-label re-score gives 0.3467 (98/150) | NOT DRIFT - different measurement objects (arm prediction vs assigned-label paraphrase support); recorded so nobody reconciles it by hand (BUG-342) |
| F7 | INFO | `/Users/barn` absolute paths remain in config/decisions.yaml and pipeline/integrity_check.py (C26) | OPEN - LOW |
| F8 | INFO | __pycache__ present in scripts/ and pipeline/ but gitignored and untracked (C19 clean) | OK |
| F9 | HIGH | BUG-387 doubled vector store (15990 = 2x7995 rows, 7995 orphans) - the production store is unreconciled, so no served-stream claim is verifiable | OPEN - repair instructions below; NOT applied (production code untouched this session) |
| F10 | MED | BUG-388 export_parquet crashes on mixed bool/int (is_summary/is_convergent) - no parquet snapshot exists | OPEN - instructions below |
| F11 | LOW | BUG-390 extraction_type still has no per-row score, so that axis has no abstention point (declared refused, not transplanted) | OPEN - ~150 inference pairs to close |
| F12 | LOW | verify_menu_policy residual WARN: config/taxonomy_v5.yaml exposes no machine-readable depth list, so 3 depth queue labels are existence-unverified | OPEN - LOW |
| F13 | INFO | Disk 97% full, 29 GiB free; .stale_* checkpoints and archive/ remain the safest reclaim | OPEN - user chore |
| F14 | MED | services.omlx.mtp_enabled is set but read by nothing in the repo (unregistered flag) | OPEN - one-line owner call |
| F15 | INFO | New: config/recalibration_pins.yaml + scripts/verify_recalibration_pins.py close the BUG-391 class (a measurement surviving a change to its own reference) | DONE |

## Hand-off: BUG-387 (apply only with owner authorisation)

1. In pipeline/stage6_commit.py replace the append-only `INSERT INTO vec_fbs(rowid, definition_embedding)` that follows `last_insert_rowid()` with a rowid-preserving upsert (DELETE FROM vec_fbs WHERE rowid = ? then INSERT, or `INSERT OR REPLACE` when the rowid is supplied explicitly).
2. Replace the count-only completeness check (it printed "Vector: READY 15990/7995") with a rowid-level assertion: count(*) and count(distinct rowid) must both equal the number of source FBs, and `SELECT count(*) FROM vec_fbs f LEFT JOIN fbs b ON b.rowid = f.rowid WHERE b.rowid IS NULL` must be 0.
3. Reconcile the 7995 orphans with a NEW script (pipeline/backup_guardian.sh first; no pipeline/safe_delete.py - BUG-261), dry-run the row counts, then re-run stage6.

## Hand-off: BUG-388

Coerce the declared boolean keys (is_summary, is_convergent) at load in the parquet export path and fail loud on mixed types (C16), then re-run only the export to produce the missing snapshot. The commit is not atomic as a unit: fbs+vec_fbs are written before the parquet step.

## What is NOT claimed

- No label, menu, definition, pipeline artifact or DB row was changed by D-348..D-353.
- RELATIVE-ONLY (D-337): no absolute error floor is certified anywhere in this session.
- The served stream at the adopted point is still ~50% wrong against an advisory (single-human-coded) reference.
