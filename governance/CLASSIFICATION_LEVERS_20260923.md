# CLASSIFICATION LEVERS - which one buys accuracy with NO manual review and NO drift (2026-09-23, D-348..D-351)

Question: of the non-drifting levers, which single one raises accuracy without a human reading rows?
Answer, measured (not opined): TURN ABSTENTION INTO A MACHINE STATE. It is the only lever that is
monotone (it can only demote, never relabel), drift-free (no definition or label changes), automated
(no queue owner), and MEASURED on the frozen ruler:

| axis | metric | operating point | selective error | delta vs base |
|---|---|---|---|---|
| discipline | verifier margin (percent rank) | abstain 25% | 0.3910 | -8.3 pp (base 0.4741, n=116) |
| content_type | R2 definition-NLI support | abstain 30% | 0.3048 | -4.2 pp (base 0.3467, n=150) |

Runners-up and why they lose:

1. Definition-anchored NLI as a GATE (D-348): real on content_type only. AUC(support vs correct)
   0.6410 with flagged error 0.4483 vs unflagged 0.2826. On DISCIPLINE it is dead (AUC 0.5348, and
   flagged rows are MORE accurate than unflagged: 0.4898 vs 0.5455). It also has no extraction_type
   score (BUG-390), so it cannot answer owner call 2 at all. Verdict: use it as the content_type
   margin, never as a discipline gate.
2. Route fine-grained demand through domains (D-346): a routing answer, not a label-quality gain.
3. Hierarchical classification: new machinery, needs a re-run and a re-score -> deferred, not rejected.
4. Retiring labels / rewriting the taxonomy (D-350): measured to be a coin flip on the discipline tail
   (nearest-parent gaps 0.0017-0.0115), so it would be drift driven by taste, not evidence.
5. Human queue on the constant axes (D-346): correct as an ESCAPE HATCH, but it is exactly the manual
   review the owner is trying to avoid - hence the drain target change in D-349.

Why the drain target had to change: the old design abstained into a HUMAN repair queue, which made
queue capacity the binding constraint (config/verify_abstention.yaml, activation_gate). Routing abstains
to the existing quarantine state keeps them out of PASS while requiring nobody. That removes the capacity
blocker; ONE gate item remains (a shadow run).

What this does NOT claim: accuracy is not raised by relabelling anything. The label set, the menu and the
definitions are untouched; rows whose support is below the threshold simply stop being served as verified.
RELATIVE-ONLY (D-337).