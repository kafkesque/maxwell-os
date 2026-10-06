# FORENSIC AUDIT — BUG-637 write-path (T2 delta recovery), 2026-10-05

Scope: read-only audit of `pipeline/stage4_merge.py::run_stage4` `--cluster` delta-merge
write path, to determine whether the T2 recovery (`--cluster 3776,26074,40300,26828,28517`)
is safe. Verdict: **NOT safe as-is — three concrete hazards, one corrected root cause.**

## Live state (rechunk-v4-20260929)
- S2 checkpoint: 8,217 records (7,151 principle / 774 PT / 109 TI / 156 PI / 27 GE).
- S4 checkpoint.jsonl: 6,588 principle FBs (77 MB).
- Sidecar `.expected_count.json`: `expected_fb_count=6591`, `declared_failed_count=3`,
  NO `failed_cluster_ids` (legacy, pre-T1 write).
- 6,588 + 3 = 6,591 → D-2817 gate holds today.
- S4 sidecars: GE 212 / PT 817 / PI 157 / TI 59 / quarantined 374 → total 8,207 records.
- S2 unique fb_ids 8,212 − S4 8,207 = 5 missing (3 declared-failed + 2 phantom).

## Finding 1 — FB checkpoint merge is SAFE (the "overwrite 6588→5" fear was FALSE)
`run_stage4` line 1423 `fbs.extend(load_jsonl(STAGE4_CHECKPOINT))` runs on EVERY invocation,
including `--cluster` delta mode. The resume block preserves the 6,588 existing FBs and
APPENDS the delta results; `safe_write_jsonl(STAGE4_CHECKPOINT, fbs)` at line 2398 writes
all of them. No replace hazard.

## Finding 2 — REAL hazard: `.expected_count.json` sidecar overwrite (D-2817 corruption)
`expected_fb_count` (line ~1396) and `total_clusters` (line ~1389) are computed AFTER the
`--cluster` filter (line 1366), so a delta run computes them over the DELTA SUBSET (~5),
then line 2403 overwrites the sidecar with `expected_fb_count≈5`, `declared_failed_count`
= the delta's `failed`. This DESTROYS the full-corpus invariant 6591/3. A delta merge of
only the 2 phantoms would also wrongly zero `declared_failed_count` (dropping the 3 still-
failed clusters). Fix must make the sidecar write delta-aware (merge prior receipt, not
overwrite) — see next steps.

## Finding 3 — REAL hazard: `--cluster` arg format
S2 `source_cluster` values are `cluster_N` STRINGS (`cluster_3776`, …). The old `main()`
parsed `--cluster 3776,26074` → `int` list `[3776, 26074]`, which never matches
`cluster_id='cluster_3776'` → "No clusters found" → exit 1. The buglog REMEDY command
`--cluster 3776,26074` as written could NOT have worked.
**FIXED (D-2823):** `main()` now normalizes bare digits to `cluster_{N}`.

## Finding 4 — REAL hazard: cluster_28517 still fails after BUG-635
`cluster_28517` "Planck's Constant Derivation" failed with application = 4 chars.
The BUG-635 salvage (line 1816) requires `len(_app) >= 10`; a 4-char application falls
through to `enrichment_status=FAILED` → D2371 `len(_app) < 10` → `empty_application` → still
`failed`. So the 5-cluster recovery yields **4 recovered + 1 residual failure**, not 5/5.

## Finding 5 — CORRECTED root cause: the 2 "phantoms" are D2120 cosine-dedup'd near-dups, not resume ghosts
The buglog BUG-637 hypothesis (D2424 resume `processed_ids` reconstruction) is contradicted
by the code order: `expected_fb_count` is computed BEFORE the resume filter, so a resume-skip
would still be counted (expected would be 6593, not 6591). The observed expected=6591 means
the 2 clusters were removed BEFORE expected was computed — i.e. by D2120 `dedup_fbs_by_cosine`
(line 1375, bge-m3, threshold 0.92). CONFIRMED: `cluster_3776` "Blue Ocean Strategy" (fb_id
339041cf) and on-disk `cluster_3777` "Blue Ocean Strategy" (fb_id 4cbab7f1) have near-identical
definitions — a genuine near-duplicate pair. Recovering 3776/26074 via `--cluster` (which
BYPASSES full-corpus dedup) therefore CREATES duplicate FBs that a future full re-run would
dedup away again.

## Recommendation (owner-gated, do NOT auto-run)
1. `cluster_40300`/`cluster_26828` (empty domains): recover — BUG-635 salvage now applies.
2. `cluster_3776`/`cluster_26074`: decide DEDUP (accept, expected stays 6591) vs RECOVER
   (override dedup, expected → 6593 + a dedup receipt). Low value, duplicate risk.
3. `cluster_28517` (4-char application): decide accept-as-failed (declared stays 1) vs
   manual enrichment vs drop.
The delta-merge sidecar fix (Finding 2) must land + R5 review BEFORE any recovery run.
