# Calibrated abstention - design + measurement (2026-09-21, D-312)

## Principle (must not weaken D-2298)

`stage5_verify.py` is **fail-closed**: an unverifiable claim is dropped, never silently accepted. A calibrated
abstention therefore turns the verifier's *margin* into an explicit routing decision:

```
margin(m)  <  t_low   -> abstain  -> repair queue (human/next-pass), label NOT committed silently
t_low <= m < t_high   -> accept but FLAG (sampled re-verification)
m >= t_high           -> accept
```

* abstention = MORE work routed to the repair queue, never fewer labels checked;
* no threshold may be enabled without (a) a measured curve on the frozen ruler, (b) a chosen operating point,
  (c) a decision row. Until then `config/verify_abstention.yaml` ships with `enabled: false` and **no production
  code reads it** (inert by construction - zero cascade risk).

## Measured curve (incumbent `pairwise` verifier, frozen ruler, n=116, discipline)

| abstained | error on remainder (D-302/D-303 measurement) |
|---|---|
| 0% | 0.474 |
| 10% | 0.423 |
| 25% | 0.391 |
| 50% | 0.328 |

Monotone, i.e. the margin is informative **in the verifier's own role only**; the same sweep on the zero-shot
labelling role was flat (0.931 -> 0.942), so abstention claims are role-specific and must never be transplanted.

## Recommended operating point (PROPOSED, not adopted)

* `t_low` = margin percentile that abstains ~25% of rows (error 0.391, i.e. -8.3 pp vs 0.474) **if and only if**
  the repair queue can absorb ~25% of rows. Queue budget is the binding constraint, not accuracy.
* `t_high` = the 10% cut (0.423) as the "accept but flag" band.
* Derivation must use the frozen ruler margins only (no ANCHOR-1 tuning), and adoption needs its own decision row.

## Open items before this can be enabled

1. margin semantics per arm (the pairwise margin is a percent-rank; it must be stated in the artifact schema);
2. repair-queue capacity + routing owner (currently shared with the F-06/F-17 queue);
3. interaction with the arbitration rules R2/R3 (a row can be abstained by the margin rule *and* disputed by
   disagreement - one queue, one de-dup key = fb_id);
4. re-measure the curve on the held-out set (governance/R3_HELDOUT_PREREG_20260921.md) before any production flip.

## CLOSURE (2026-09-21, BUG-327 closed invalid) - the curve IS re-derivable; open item 1 above is retracted

arms[arm].predictions[fb_id] = [label, margin] is persisted for every arm, so the sweep needs no model re-run.
Re-measured on the incumbent pairwise arm over the 116 human-labelled ruler rows (abstain the lowest-margin rows):

| abstained | error on remainder | margin threshold (percentile) |
|---|---|---|
| 0% | 0.4741 | - |
| 10% | 0.4231 | t = -0.0528 (p10 = -0.1111) |
| 25% | **0.3908** | t = -0.0040 (p25 = -0.0060) |
| 50% | 0.3276 | t = +0.0011 (p50 = 0.0004) |

Independent re-derivation reproduces the D-302 sweep (0.474 / 0.423 / 0.391 / 0.328) from a second code path, so the
numbers are cross-validated. Same sweep on qwen3coder is much flatter (0.5259 -> 0.4904 -> 0.4713 -> 0.4310): the
margin only carries signal inside the verifier role, confirming the role-specificity warning.

**Proposed operating point (still NOT enabled):** t_low = p25 (-0.006, abstains 25%, error 0.391 i.e. -8.3 pp) and
t_high = p10 (accept-but-flag). Binding constraint is repair-queue budget, which is an owner decision.
