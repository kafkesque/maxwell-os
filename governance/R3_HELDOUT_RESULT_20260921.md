# R3 HELD-OUT RESULT — 2026-09-21 (D-311 evidence; D-275a: error rate, never "accuracy")

**Verdict: R3 is REJECTED. The +6.0 pp in-sample gain did NOT replicate — held-out gain is 0.00 pp.**
No combine rule (R1–R4) clears the pre-registered D-300 bar. **Do not adopt R3. Recommend closing D-311 as
MEASURED-REJECTED** (owner ratification) and keeping the incumbent pairwise verifier unchanged.

## What was measured
- Source: `bakeoff.sources.anchor1` (D-312) — the human verdicts come from
  `governance/ANCHOR1_BLIND_SHEET_20260920.csv`; the pipeline labels come from
  `governance/ANCHOR1_KEY_20260920.json` keyed by `fb_id`. Same closed menu (menu_hash stamped on the
  artifact), same rows for every arm, deterministic decode (temp 0.0), all declared in config.
- Rows: allowlist = 58 pre-registered held-out ids (`ANCHOR1_HELDOUT_SET_20260921.json`);
  **n_scored = 57** — one row (sheet row 15, fb_id `38c529d5…`) carries an EMPTY human verdict and cannot be
  scored (D-275a: an unlabelled row cannot be "wrong"). Effective n is therefore 57, not 58 (BUG-334).
- Axis: discipline. Adapter verified for truth-leakage by a mechanical blinding test (below).

## Results (n=57)
| arm / rule | decided | queue | errors | error rate | gain vs incumbent |
|---|---|---|---|---|---|
| constant (triviality floor) | 57 | 0 | 48 | **0.8421** | — |
| **pairwise (incumbent, R1)** | 57 | 0 | 29 | **0.5088** | 0.00 pp |
| qwen3coder (standalone, R4) | 57 | 0 | 34 | 0.5965 | −8.77 pp |
| R2 agree→accept, disagree→human | 14 | 43 (75.4%) | 6 | 0.4286 | +8.02 pp |
| **R3 agree→accept, disagree→higher margin** | 57 | 0 | 29 | **0.5088** | **0.00 pp** |

Agreement coverage: agree 14 / 57 (24.6%), disagree 43; both_wrong 14, either_wrong 49 (headroom 35).

## Interpretation (why R3 died)
1. **The two arms almost never agree on held-out rows** (24.6%; 39.7% on the derivation rows). Arbitration can
   only pay off where arms disagree AND the tie-break is informative. Here disagreement is 43/57 and the
   tie-break resolved to the incumbent almost everywhere → R3 degenerates to R1 exactly (0.5088 = incumbent).
2. **R2 clears the error bar but violates the abstention clause.** It wins only by auto-deciding 14 rows and
   queueing 43 (75.4%) to a human, versus the incumbent's 0% abstention. D-300 requires the gain at
   equal-or-lower abstention, so R2 is REJECTED as a deploy candidate (it is, however, a legitimate
   *human-triage* configuration if the owner ever wants to buy accuracy with a 75% review queue).
3. **The challenger is not competitive on either row set** — ruler 0.5259 vs incumbent 0.4741;
   held-out 0.5965 vs 0.5088. It is not a viable standalone labeller.
4. Effect sizes are inside noise for n=57 (±1 SE ≈ 6.6 pp), so R2's +8.02 pp should not be read as a real
   improvement either — and the incumbent's own held-out rate (0.5088) sits 3.5 pp above its ruler rate
   (0.4741), i.e. the incumbent is stable across row sets while the rules built on top of it are not.

## Leakage / integrity evidence (mandatory before publishing)
- **Truth-blinding test (mechanical, decisive):** the harness arms were re-run with the human truth dict
  EMPTY and the stored `pipeline_label` withheld — qwen3coder produced **0 label differences over 12 rows**
  vs the artifact, and pairwise abstained on **all** rows (`labels={None}`), proving both arms read only
  their declared inputs and never the truth. Reviewed via R5: `governance/R5_REVIEW_R3_ADAPTER_20260921.md`.
- **R5 caveat (BUG-333):** the gemma-4-E4B review returned a schema-shaped rubber stamp ("yes"/NONE on every
  line, including inverted-polarity questions) and is therefore NOT accepted as sufficient evidence on its
  own; the mechanical blinding test above is what actually certifies the adapter.
- No production code, DB or pipeline artifact was written by the measurement itself.

## Config-first audit of the new code (C12/R5)
- Fixed: `scripts/anchor1_arbitration.py` claimed config-first while hardcoding the arm names and artifact
  paths; the new `scripts/r3_heldout_eval.py` reads arms, rules, thresholds and margin scale from
  `config/eval_integrity.yaml` (`bakeoff.arbitration`). The R3 helper is retained only as the *derivation*
  record and is superseded by this held-out report.

## What the owner must now decide (nothing here is auto-adopted)
- Ratify D-314: R3 NOT adopted, D-311 closed as measured-rejected (administrative — the evidence is in).
- Nothing else changes: `serving_gate` remains the single deploy gate, the incumbent pairwise verifier stays,
  and the abstention operating point (separate gate) stays `enabled: false`.

<!-- s7-sync 2026-09-21 -->

## Evidence (machine-written, not transcribed)
```
artifact   governance/bakeoff_typed_decision_anchor1_20260921.json  sha256 d56c3931858887fe083afc6dd0db4d211b7aff01ea059ad390c22756e2420696
sheet      governance/ANCHOR1_BLIND_SHEET_20260920.csv              sha256 a91f9c859a998d4d27d7ce91939c4ccf4c23e3e9d20aa0cb34ccadcb294ee821
key        governance/ANCHOR1_KEY_20260920.json                     sha256 20a4a437eab902fc703a210bad26b8d3220c7c2574852fb9b97b01baf567526c
allowlist  governance/ANCHOR1_HELDOUT_SET_20260921.json            sha256 c4413a6841e811bbe77b0a16ddc486c7964a5f5b431a4ac367f27114f6f05f10
menu_hash  73597ee2b1bb1eb92edb08e743ffa0654c1e5994edcd3535d814c7942a89df6f   (== frozen config/closed_menu_v5.sha256, three-way agreement)
n_scored   57 of 58 pre-registered rows
report     governance/r3_heldout_20260921.json
run        python3 scripts/bakeoff_typed_decision.py --source anchor1 --arm constant --arm pairwise --arm qwen3coder
score      python3 scripts/r3_heldout_eval.py
```
