# LABEL MODEL OUTPUT — Step 3B (D2585 P2)

## Estimated LF parameters (Dawid-Skene, 2 LF, weakly identified)

| LF | P(flag\|correct) θ | P(flag\|wrong) ψ |
|---|---|---|
| T-NLI contradiction | 0.0571 | 0.3641 |
| cleanlab | 0.4102 | 0.7005 |

P(label correct) π = 0.7845 (prior 0.8).

## Golden-set suspicion tiers

| Tier | Count |
|---|---|
| both | 101 |
| nli_only | 34 |
| cleanlab_only | 539 |
| neither | 353 |

Mean P(mislabel) = 0.2358, median = 0.1879.

**High-suspicion subset (both-flag + NLI-only) = 135 FBs** — the P3 generative-challenger / GOLD-A seed.
