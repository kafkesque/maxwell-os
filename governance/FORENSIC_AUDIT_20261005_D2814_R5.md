# Forensic Audit — D-2814 R5 Gate (2026-10-05)

Scope: R5 verifier review of the D-2814 definition-anchored menu swap + its fixes. Flag OFF, uncommitted.

## Verdict
**NO BREAK, NO CASCADE — concrete defects found by the R5 gate and fixed; ship, flag OFF, uncommitted.**

## Findings (11-axis)
- **BREAK** — clean. py_compile clean; flag-off import byte-identical (no swap); pytest 12 passed.
- **CASCADE** — clean. All three S4 classify paths (merged, batch, direct) now consume the single `definition_anchored_block()`.
- **DRIFT** — none. No `none`-vs-`emerging` residual; abstention sourced from `render_closed_menu()["abstention"]` (no hardcode, C12).
- **BLINDSPOT** — FIXED. `BATCH_CRIBS_CLASSIFY_SYSTEM` was uncovered by D-2814 (batch_enabled:false latent); now swapped (BUG-649).
- **GAP** — FIXED. JSON schema free-gen placeholders `precise_discipline_name`/`["domain1","domain2"]` contradicted the verbatim menu; now swapped via `_apply_definition_anchored_schema`.
- **CONFLICT** — FIXED. "DO NOT use emerging" tail + "SINGLE most precise" instruction removed on all paths; abstention stated as value + per-axis independence.
- **BUG** — BUG-649 filed + fixed (schema/batch/abstention); D-2836 minted.
- **HIDDEN FAILURE** — FIXED. `'emerging'` now visible as a valid schema value (was invisible → model might never emit it).
- **ERROR LEAK** — clean. All swap anchors fail-closed (C16) on non-unique markers.
- **MISMATCH** — clean. Abstention token in menu == schema == rules == code (`if merged.get("discipline") == "emerging"`).
- **BLOAT** — unchanged (BUG-648, D-2835 prefix-cache; group-prefilter deferred).

## Residual (non-blocking)
gemma rounds 2+ = philosophy on the "ontologically AND pragmatically" criterion (D-2830). Deferred to the full-204 A/B (D-2767). Flag stays OFF.
