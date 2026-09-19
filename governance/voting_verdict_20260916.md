# Voting verdict — which model should vote (D2637, 2026-09-16)

Run: 6 voters x 251 gold_4axis rows, oMLX temperature 0.0, uniform prompt
(`Reasoning: low` prefix, 250 max_tokens budgeted at 512). 1506 graded rows,
zero transport failures. `governance/model_eval_checkpoint.jsonl` (suite=voting).
Report tool: `python3 tools/voting_report.py`.

## 1. Per-voter accuracy (discipline, exact match)

| model | ALL (251) | CIRCULAR (164) | HUMAN-contested (87) | dom micro-F1 | median s/call |
|---|---|---|---|---|---|
| **Qwen3.8-27B** | **0.709** | 0.854 | **0.437** | **0.693** | 16.5 |
| Qwen3-Coder-30B | 0.430 | 0.500 | 0.299 | 0.412 | 2.3 |
| gemma-4-E4B | 0.422 | 0.482 | 0.310 | 0.357 | 2.8 |
| gpt-oss-20B | 0.339 | 0.372 | 0.276 | 0.261 | 13.2 |
| REAP-19B | 0.283 | 0.323 | 0.207 | 0.244 | 12.6 |
| Ornith-9B | 0.116 | 0.146 | 0.057 | 0.095 | 24.4 |

**Provenance caveat.** 164/251 gold discipline labels were produced by the reliable
pair AGREEING (circular); 87/251 are that pair's human-adjudicated DISAGREEMENTS
(biased hard). So Qwen3.8's true accuracy lies between 0.437 and 0.854. **The
RANKING is identical on all three subsets**, so the ordering and the roughly 2x
margin are robust even though the absolute figure is not.

## 2. Error correlation (Jaccard of error sets)

Qwen3.8 vs any partner: 0.323-0.385. Partners among themselves: 0.526-0.696.
Note: when accuracies differ this much, errJaccard is dominated by base rates and
is NOT a good discriminator. The rescue rate below is the honest test.

## 3. Rescue rate — the decisive number

Of Qwen3.8's 73 errors, how often does a partner get it right:

| partner | rescues | own acc | oracle-fused upper bound |
|---|---|---|---|
| gemma-4-E4B | 0.178 (13/73) | 0.422 | 0.761 |
| Qwen3-Coder-30B | 0.178 (13/73) | 0.430 | 0.761 |
| gpt-oss-20B | 0.164 (12/73) | 0.339 | 0.757 |
| REAP-19B | 0.096 (7/73) | 0.283 | 0.737 |
| Ornith-9B | 0.014 (1/73) | 0.116 | 0.713 |

**No partner rescues more than 18% of the primary's errors.** The oracle upper
bound is +5.2 points over Qwen3.8 alone, and that requires knowing in advance which
of the two is right.

## 4. Do the ensembles beat the best single voter?

Best single voter: **Qwen3.8-27B, 0.709 at 100% coverage.**

| roster | policy | acc | coverage |
|---|---|---|---|
| REAP + Qwen3-Coder + Qwen3.8 | majority | 0.804 | 0.590 |
| REAP + gemma-4-E4B + Qwen3.8 | majority | 0.786 | 0.614 |
| average over all 3-combos | majority | 0.541 | 0.701 |
| REAP + Qwen3-Coder + Qwen3.8 | unanimity | **0.915** | 0.187 |
| gpt-oss + REAP + gemma-4-E4B + Qwen3.8 | unanimity | 0.957 | 0.092 |

Majority voting only beats Qwen3.8 alone when the roster is chosen well, and even
then it abstains on ~41% of rows. The average 3-combo is far WORSE (0.541).
**A badly chosen roster actively harms accuracy.**

The unanimity numbers look excellent but are selection effects: unanimity is rare
and correlates with easy rows, so ANY roster looks good. Do not read 0.957 as a
capability score.

## 5. Recommendation

1. **Primary voter and decider: Qwen3.8-27B.** Nothing local is close; the next best
   is 28 points behind and rescues <18% of its errors.
2. **Do NOT adopt majority voting for classification.** It is worse than Qwen3.8
   alone unless carefully rostered, and it was the D2618 hypothesis under test.
3. **DO adopt a unanimity gate as an auto-accept tier**, not as the decider:
   REAP + Qwen3-Coder + Qwen3.8 unanimous = 0.915 @ 18.7% coverage. Route the rest
   to review.
4. **For the 63 contested rows**, use Qwen3.8 + gemma-4-E4B (or Qwen3-Coder) and
   escalate disagreements to a human. There is no local "3rd reliable voter".
5. **Never use Ornith-9B as a voter.** 0.116 accuracy, rescues 1 of 73 errors.

## 6. Implications for D2618 P1

- "3rd reliable voter as tie-break" is **disproven**: no local model is within 28
  points of Qwen3.8, and none rescues more than 18% of its errors.
- The observed anomaly "silver agrees with the reliable pair only 40%" is explained:
  silver is a much weaker voter, not a bad tie-breaker. Disagreement is mostly the
  weaker voter being wrong.
- The **domain aggregation policy** decision (exact-set vs union) remains open, but
  the same asymmetry applies to domains (Qwen3.8 dom-F1 0.693 vs next best 0.412).
