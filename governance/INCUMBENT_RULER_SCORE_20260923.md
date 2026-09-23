# Incumbent re-score on the consolidated ruler — 2026-09-23 (D-347)

**Question:** every "the arm loses to the incumbent" verdict quotes an incumbent agreement
measured on the ANCHOR-1 ruler (2026-09-20). The consolidated ruler changed 50 human cells
and added owner-supplied labels. Has the incumbent ever been scored against the ruler that
is actually in force?

**Answer: no — until now.** Generator: `scripts/incumbent_ruler_score.py` (deterministic,
no LLM) from `config/incumbent_ruler_score.yaml`. Artifact: `INCUMBENT_RULER_SCORE_20260923.json`.

| axis | ANCHOR-1 quoted (2026-09-20) | live store vs ruler `_human` | live store vs ruler `_final` (owner-adjudicated) | Δ (current truth − previous) |
|---|---|---|---|---|
| content_type | 0.6467 (97/150) | **0.5933** (n=150) | **0.6533** (n=150) | **+0.66 pp** |
| discipline | 0.5259 (61/116) | 0.5172 (n=116, same subset) | **0.4400** (n=150) | **−8.59 pp** |
| extraction_type | 0.7172 (104/145) | 0.7172 (n=145) | 0.7172 (n=145) | 0.00 pp |

## What the two comparisons separate

- **Ruler change** (previous-ruler column → current-ruler column, store fixed):
  content_type **+6.00 pp**, discipline **−5.18 pp**, extraction_type 0.00 pp. The owner's
  adjudication *helped* the incumbent on content_type (9 overrules moved `quarantine` →
  `principle`, the store's own default) and *hurt* it on discipline.
- **Store change** (ANCHOR-1 number → live store on the ruler's original human cells):
  content_type **−5.34 pp** (8 rows), discipline **−0.87 pp** (1 row), extraction_type 0.00 pp.
  The content_type move is material and is NOT a subset artifact (150/150 scorable both times).

## Consequence

1. The headline incumbent numbers in circulation are **stale in both directions**: too
   pessimistic on content_type, too optimistic on discipline.
2. **D-345 survives the correction.** The k-NN arm (discipline 0.2600, content_type 0.6000,
   extraction_type 0.4667) loses to the incumbent under *every* reference in the table above,
   so the rejection was not an artifact of the stale baseline.
3. Any floor or gate that reads `ruler_measurement.measured_error_rate` is quoting a ruler
   that no longer exists. Re-point it (G4a) or mark it superseded — do not silently keep using it.

**Qualifier (D-337):** RELATIVE-ONLY. The ruler is `human-mixed+llm-attested`; this is an
agreement delta between two references, not an accuracy claim and not an error floor.
