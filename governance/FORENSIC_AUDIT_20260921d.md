# FORENSIC AUDIT — session 9 (2026-09-21 20:19) — D-315 blast radius, ruler annotation, stage5 snapshot

Scope: did anything break, drift, hide a blindspot/gap/conflict/mismatch, contaminate, leak, error or tax the future?
Verdict: **no breakage of the published numbers, no contamination, no leak, no DB write this session.** Three real
defects found and handled (F-02, F-04 regression, F-05), one of them mine (a predecessor claim that was not durable).

| # | sev | finding | status |
|---|---|---|---|
| F-01 | HIGH | `config/eval_integrity.yaml` carried corrupt accuracy figures as `accuracy` (BUG-339, prior session) | FIXED prior session |
| F-02 | MED | the canonical ruler cannot express an ABSTENTION REASON: 34 DISC nulls = 28 blank + 6 `emerging`. The committed `ruler_inverted_*` artifact was ALSO generated from the workspace path while config declares the authority (stale-by-method, not stale-by-number) | **FIXED** (BUG-340) |
| F-03 | LOW | the authority self-declares `csv_sha256 = 4d0c856a` = the byte-lost freeze CSV; the cross-link existed only in prose | FIXED (declared in config) |
| F-04 | HIGH | **BUG-311 regressed.** The live stage5 checkpoint is absent: at 18:59:42 stage5 rotated it to `.stale_20260921_185942` (input fingerprint moved) and no re-run followed. "RESOLVED" was conditional on a fingerprint that has since moved | DECLARED (BUG-341) |
| F-05 | MED | C15 was unenforceable and its hand-maintained count was WRONG (claimed 17 unresolved; the register carries RESOLVED headers for BUG-311/313 and BUG-311 has regressed) | **FIXED** (mechanical index, BUG-342) |
| F-06 | LOW | BUG-330 stale smoke assertion | **FIXED**; one further smoke failure is a missing untracked fixture (BUG-343) |
| F-07 | LOW | housekeeping debt is 78 files (46 config + 32 governance), not the 47 F-10 recorded; 0 are git-tracked | OPEN (owner) |
| F-08 | LOW | the legacy stored-side KEY had no declared sha256 although it grounds the stored side | FIXED (declared) |
| F-09 | LOW | the workspace CSV carries 4 trailing EMPTY rows (154 read vs 150 ruler rows); the scorer filters them, nothing else does | OPEN (cosmetic) |

## Checks that came back CLEAN
- authority sha256 `0ec321a7…` = declared; workspace `38323192…` = declared; the byte-lost `4d0c856a…` is in NO backup (the D-313 ruling was correct, and the bytes are genuinely gone).
- re-scoring from the authority reproduces the published numbers EXACTLY: stratum A/B 0.290/0.480 (CT), 0.487/0.444 (DISC), 0.255/0.340 (FORM); scored_n 150/116/145 unchanged after the fix.
- truth-blinding self-test PASS on all three axes (blinded_agrees = 0); the new workspace-hash drift guard FAILS CLOSED.
- `pipeline/` diff vs HEAD = 0 lines; `compileall` rc=0; 22/22 config YAML load; `decisions.yaml --check` clean.
- no DB write this session; 0 train-pool/anchor overlap re-confirmed earlier; no secret material in the touched files.
- the S-5 rotation KEPT the old bytes (crash-safe rotate, not delete): the 7995-FB snapshot survives byte-identical to its declared sha256.

## Future tax carried forward
- F-11 (OPEN): no second coder -> NO floor may be repointed; every floor is single-coder.
- F-12 (OPEN): the ruler CT axis is dead under menu `cac6e695`; never pool RULER-150 with ANCHOR-2.
- the R2 corpus meter is now pinned to the Sep-4 stage5 snapshot until stage5 is re-run on the current S4 input.
