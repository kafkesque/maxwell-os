# SESSION HANDOFF — 2026-09-23 (session 18 continued, forensic audit + 6 steps)

## 0. C15 OBLIGATION (mandatory, mechanically re-derived)
Source: `governance/buglog.md` via `scripts/bug_status.py` -> `governance/bug_status.json`
(`c15_threshold: 5`, `c15_must_append_to_handoffs: true`).
**73 OPEN / 51 CLOSED of 124 ids.** The count is quoted from the generated
index, never from prose (BUG-342 rule). This block was MISSING from the previous handoff
(`agent/session_seed.yaml` carried 0 bug ids) — fixed 2026-09-23.

| id | status |
|---|---|
| BUG-253 | OPEN |
| BUG-254 | OPEN |
| BUG-255 | OPEN |
| BUG-257 | OPEN |
| BUG-258 | OPEN |
| BUG-259 | OPEN |
| BUG-260 | OPEN |
| BUG-261 | OPEN |
| BUG-263 | OPEN |
| BUG-264 | OPEN |
| BUG-265 | OPEN |
| BUG-266 | OPEN |
| BUG-270 | OPEN |
| BUG-273 | OPEN |
| BUG-274 | OPEN |
| BUG-275 | OPEN |
| BUG-276 | OPEN |
| BUG-277 | OPEN |
| BUG-278 | OPEN |
| BUG-279 | OPEN |
| BUG-280 | OPEN |
| BUG-281 | OPEN |
| BUG-282 | OPEN |
| BUG-283 | OPEN |
| BUG-284 | OPEN |
| BUG-285 | OPEN |
| BUG-286 | OPEN |
| BUG-287 | OPEN |
| BUG-288 | OPEN |
| BUG-289 | OPEN |
| BUG-290 | OPEN |
| BUG-292 | OPEN |
| BUG-293 | OPEN |
| BUG-294 | OPEN |
| BUG-295 | OPEN |
| BUG-296 | OPEN |
| BUG-297 | OPEN |
| BUG-298 | OPEN |
| BUG-299 | OPEN |
| BUG-300 | OPEN |
| BUG-301 | OPEN |
| BUG-302 | OPEN |
| BUG-303 | OPEN |
| BUG-304 | OPEN |
| BUG-305 | OPEN |
| BUG-306 | OPEN |
| BUG-312 | OPEN |
| BUG-314 | OPEN |
| BUG-315 | OPEN |
| BUG-316 | OPEN |
| BUG-317 | OPEN |
| BUG-318 | OPEN |
| BUG-319 | OPEN |
| BUG-326 | OPEN |
| BUG-331 | OPEN |
| BUG-333 | OPEN |
| BUG-334 | OPEN |
| BUG-336 | OPEN |
| BUG-341 | OPEN |
| BUG-343 | OPEN |
| BUG-349 | OPEN |
| BUG-351 | OPEN |
| BUG-352 | OPEN |
| BUG-354 | OPEN |
| BUG-355 | OPEN |
| BUG-356 | OPEN |
| BUG-359 | OPEN |
| BUG-360 | OPEN |
| BUG-366 | OPEN |
| BUG-367 | OPEN |
| BUG-376 | OPEN |
| BUG-377 | OPEN |
| BUG-378 | OPEN |

## 1. WHAT THIS SESSION CLOSED
* **C-1 CLOSED (D-338)**: abstention at p25 is approved IN PRINCIPLE, not activated; `enabled: false`,
  `consumers: []`, four-item `activation_gate`. Zero behaviour change.
* **F-1 CLOSED**: R030/R063 name the owner's verbatim spelling (`ALIAS_CANONICALISED:owner:discipline`).
  ANCHOR-3 re-issued, sha256 `29393d5f9d5292053a39986582578e140121d8987448648ad63f528062cd2698`.
* **NEW standing check (D-339)**: `scripts/audit_flag_consumers.py` + `config/flag_consumer_registry.yaml`,
  wired into `just health`. A flag that enforces nothing, or whose state disagrees with its decision, is RED.
* **C-2 CLOSED (BUG-374)**: `stage4.boundary_inject_enabled` went back to `false`, executing D-327, which had
  recorded the flip as done on 2026-09-21 while the flag stayed `true` and the rejected block stayed live.

## 2. WHAT THIS SESSION OPENED
* **C-3 / BUG-376 (HIGH, owner gate)**: the 7995-verdict S5 run's declared input was rewritten 65 min AFTER
  the run completed, and that byte-image is gone. S6 must not commit against the mutated input.
  `scripts/verify_declared_inputs.py` now makes an unacknowledged input move a RED.
* **BUG-375 (MED, FIXED)**: the flag audit's own unregistered scan emitted leaf keys while the registry
  registers dotted paths, so a REGISTERED flag was also reported unregistered and 40 warns were noise.
* **BUG-377 (LOW-MED, OPEN)**: a stale pidfile (`stage4_merge/t11/s4_run.pid`) whose pid was recycled by a
  live macOS XPC service; any future liveness check on a pidfile is fooled by pid reuse.

## 3. FROZEN ARTIFACTS (cite these, never bare paths)
* **ANCHOR-3**: `governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv`
  manifest `governance/ANCHOR_MANIFEST_20260923.json`; RELATIVE-ONLY (D-337), no absolute error floor.
  Verified by `scripts/verify_anchor_manifest.py` in `just health`.
* **S5 t11**: live, COMPLETE (7995 = PASS 5023 + QUARANTINE 2972), fingerprint `c2754fc6...`,
  status COMPLETE-BUT-INPUT-MOVED (see `config/eval_integrity.yaml.current_state_20260923`).

## 4. OWNER GATES (nothing below runs without a GO)
| # | Gate | Say this | Effect |
|---|---|---|---|
| 1 | S5/S6 provenance | `S5 REVERIFY` or `S5 FREEZE` | re-verify 7995 (~1.3 h) / freeze the pair and cite it |
| 2 | BUG-326 repair | `BUG-326 GO` | R5 review then `--apply` (403 raw->canonical, 147 both-axes, 703 no-domain) |
| 3 | R3 held-out run | `R3 GO` | 58 frozen rows, ~10 min, relative ranking only |
| 4 | laya benchmark | `laya benchmark GO` | pinned rev, benchmark-only licence |
| 5 | 40 unregistered flags | `REGISTER FLAGS` | same blindspot class as C-1/C-2, warn tier only |
| 6 | boundary block intent | `BOUNDARY ON` | reverses D-327 -> needs a new decision, not a comment |
*Generated 2026-09-23 by the session-18 forensic audit (append-only, R-D410).*


## Session 22 addendum — 2026-09-23 (forensic audit + owner's 'do your recommendation')

**Findings (all re-derived from the generators, never hand-counted — BUG-342):**
- **BUG-326 repair is NOT APPLICABLE** and always was: `governance/BUG326_REPAIR_SCOPING_20260921.md` (2026-09-21) closed it
  because 403/147/703 DO NOT REPRODUCE (757 'non-canonical' are all the legitimate catch-all `emerging`; 0 alias-map hits;
  65 mixed-axis; 0 domain-less). The handoff/register/gate list still carried 'BUG-326 GO' → an assistant recommendation
  (mine, prior turn) was based on a stale row. Fixed: BUG-380, gate withdrawn.
- **BUG-381 (NEW, HIGH, OPEN)**: terminal-store vintage mismatch. `maxwell.db` (mtime 09-19T21:47) says PASS 3299 /
  QUARANTINE 4696, while the S5 t11 run (09-22) computed PASS 5023 / QUARANTINE 2972 over the same 7995 rows. The
  committed store does not carry the verdicts of the run the status report shows. **Owner gate.**
- **BUG-379 (NEW, FIXED)**: D-327's A/B receipt existed only as root scratch (`ab_off.json`/`ab_on.json`). Filed as
  `governance/evidence/D327_BOUNDARY_AB_20260921/`; class rule minted as **D-342**.
- **BUG-382 (NEW, OPEN)**: registry dotted paths break on dotted model names (3rd instance of the BUG-375 class).
- `probe_output/` + `handoff/` filed to `archive/root_filing_20260923/` (docstring-only refs, verified before moving).
- Authority markers written for `stage4_merge/t11` and `stage5_verify/t11` (BUG-378(b) resolved at the instance level).

**Minted:** D-341 (S5 t11 cited from the frozen pair + mandatory qualifier; live path is never a citation surface) and
D-342 (a measurement-backed ruling must cite a frozen receipt artifact). Registry now **710 decisions, in sync**.
**New control:** `scripts/verify_evidence_manifests.py` (+`config/evidence_manifest.yaml`) — 9th fail-loud health check.
**Flags:** 44 registered under D-339; deferred residue + owner calls in `governance/FLAG_HYGIENE_TASKS_20260923.md`.
**Not run:** R3 held-out (preflight green, 58/58) — the run is staged; command below. S5 REVERIFY not run (not blocking).

## Session 23 addendum — 2026-09-23 (owner approved the classification recommendation)
- **D-343 MINTED + MEASURED**: representability sweep over all 7995 FBs (7.8 s). discipline and domains are SEPARABLE (+15.2 pp / +22.2 pp over the constant-answer baseline); extraction_type is WEAK (+9.0 pp); **content_type (−2.98 pp) and depth (−16.5 pp) LOSE to the constant** and must not be classified. Receipt: governance/evidence/REPRESENTABILITY_SWEEP_20260923/. Corrects the earlier blanket "retrieval is dead for discipline" claim: it is dead as a MISLABEL detector (D2575), not as a representation.
- **D-344 MINTED**: scripts/verify_artifact_authority.py enforces the ARTIFACT_AUTHORITY.json markers (10th just health check); 2 markers, 17 files verified, 0 RED.
- **BUG-383 FIXED** (167 gitignored __pycache__ dirs / 31 MB invisible to C19; purged) and **BUG-384 FIXED** (the new checker's own pipe-joined-glob defect, BUG-375 class, caught on its first run).
- pipeline/ untouched; no new owner gate created by this session.

## C15 BLOCK (2026-09-23, session 21) - unresolved bugs travel with every handoff

**92 open / 72 closed of 164 ids** (threshold for this block is 5). Full machine-readable list with events:
`governance/bug_status.json` (regenerate: `python3 scripts/bug_status.py`).

Regenerated 2026-09-23 18:57 (session 22) from the parser after the BUG-418 dedup - this line is GENERATED,
not typed (a hand-typed count is a second clock for one artifact - the BUG-402 failure mode).

Highest-consequence open ids: BUG-400 (Dropbox File Provider owns the served store - owner action), BUG-403
(stage4.depth_model hardcoded default names the refuted depth route), BUG-341 (live stage5 checkpoint absent),
BUG-376 (a completed S5 run's declared input was rewritten after the run), BUG-391 (the ratified abstention
point does not reproduce on the ruler in force), BUG-381 (terminal-store vintage mismatch), BUG-326 (repair
target numbers do not reproduce on the live DB), BUG-406 (temp auto-purge guard), BUG-415 (no depth anchor),
BUG-416 (depth is not a menu). Owner-gated: BUG-400, BUG-403/405, BUG-381, BUG-376, and A2 execution.

Carried rule (C15): no handoff is complete while this block is absent, and no bug may be closed by inference
- a closure needs a receipt (D-339).
