# k-NN arm vs the incumbent — REJECTED (2026-09-23)

**Verdict: the k-NN label arm is REJECTED on all three routed axes.** Frozen ruler
`governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv` (150 rows, tier human-mixed+llm-attested),
store `maxwell.db` vec shadow (7995 rows, 512d bge-m3), k=10.

| axis | k-NN agreement | incumbent (stored) | delta | constant baseline | ties→miss |
|---|---|---|---|---|---|
| discipline | 0.26 | 0.5259 | **-26.59 pp** | 0.06 | 31/150 |
| content_type | 0.6 | 0.6467 | **-4.67 pp** | 0.5933 | 1/150 |
| extraction_type | 0.4667 | 0.7172 | **-25.05 pp** | 0.3333 | 9/150 |

RELATIVE-ONLY (D-337). No absolute error floor. k-NN here measures representation separability on the ruler rows, not deployable accuracy (D2575: it is not a mislabel detector).

## What this changes

D-343 established that discipline and domains are *separable* — a neighbourhood agrees with
itself well above a seeded permutation null and above the constant. This run shows that
separability is **necessary but not sufficient**: the neighbourhood is coherent around
boundaries that are NOT the human's. Coherence is not correctness (D2575, now quantified), so
D-343 licenses a *learnable* arm, not a *nearest-neighbour* arm.

Two corroborations: `content_type` k-NN 0.6 vs constant
0.5933 confirms F-17 (the axis is a constant, +0.7 pp over
guessing the mode), and `discipline`'s 31/150 ties are a
21% abstention rate *before* any accuracy is claimed — the arm cannot even produce a label a
fifth of the time.

**Consequence:** the incumbent LLM labeler stands on all three axes; no k-NN arm is built.
