# R3 held-out validation - PRE-REGISTRATION (2026-09-21, D-311)

**Rule under test (R3, from D-306):** when `pairwise` (incumbent verifier) and `qwen3coder` (LLM labeler) agree ->
accept the label; when they disagree -> take the label of the arm with the higher (percent-rank) margin.

**Why a new test is required:** R3 was derived on the 116 human-labelled rows of the frozen ruler and reached
+6.0 pp on that same set. D-300 forbids adoption of a post-hoc rule on the rows it was derived from. This is the
pre-registered hold-out that decides R3/R2/R4/R1 once and for all.

**Held-out set:** the 60-row ANCHOR-1 adjudication sheet, minus every row that also appears in the frozen ruler
(2 rows: sheet row 11 / 44). `n_heldout = 58` rows, human labels from the sheet (never used to derive
R3), pipeline labels from `governance/ANCHOR1_KEY_20260920.json` for bookkeeping only.
Overlap rows excluded: ['a1efe32a3ce09a4a6543db03ddb0755b7005206af4e44ccfe9948a527282bf41', 'db9f4c89ff9f952fc7504047aed8fad73ef80e3eee211a582e46a97abdc9377d'].

**Frozen before the run (no peeking, no re-tuning):**
* metric = discipline error rate (D-275a: error rate, never "accuracy") over rows where both arms produce a label;
* acceptance bar (D-300): candidate must beat the incumbent on the held-out set by **>= 5.0 absolute pp** at
  equal-or-lower abstention, deterministic decode (temp 0), same 61-slot menu, same rows. Anything less = REJECT.
* human-coverage guard: R2 (disagree -> human queue) is judged by *queue size* and error on the auto-accepted
  remainder, not by raw error alone.
* every arm must be re-run on this sheet in the same session; no re-use of ruler margins (different rows).

**Required evidence to publish:** per-arm error, abstention, error-set Jaccard, the R1-R4 table, and the exact
command lines. Until then R3 stays PROPOSED (not adopted) and production stays on the incumbent.
