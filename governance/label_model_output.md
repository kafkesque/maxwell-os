# LABEL MODEL OUTPUT — Step 3B/3C (D2585 P2 + P4 LF-3)

## Estimated LF parameters (Dawid-Skene, 3 LF)

| LF | P(flag\|correct) θ | P(flag\|wrong) ψ |
|---|---|---|
| T-NLI contradiction | 0.0402 | 0.3884 |
| cleanlab | 0.4149 | 0.6576 |
| challenger (LF-3) | 0.6247 | 0.9458 |

P(label correct) π = 0.7616 (prior 0.8).

## Golden-set suspicion tiers (2-LF tier retained for P3-compat)

| Tier | Count |
|---|---|
| both | 101 |
| nli_only | 34 |
| cleanlab_only | 539 |
| neither | 353 |

Mean P(mislabel) = 0.2506, median = 0.1748.

**High-suspicion subset (both-flag + NLI-only) = 135 FBs** — the P3 generative-challenger / GOLD-A seed.
