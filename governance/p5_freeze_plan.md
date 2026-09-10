# P5 FREEZE PLAN — GOLD-A/B/CHALLENGE (D2585 P5)

Classifier macro-F1 **0.2875** (target 0.75) — DATA-LIMITED, not model-selection.

## Tier assignment
- **GOLD-A** (high-suspicion, challenger-voted): **135**
- **GOLD-B** (statistically-cleaned silver): **892**
- **CHALLENGE** (boundary corpus): **9** (target ~150)
- Total golden: **1027**

## Data-starvation (root cause of 0.2875)
18 of 61 disciplines have <10 examples (below the mining floor). These are the 0.00-F1 classes.

| discipline | examples |
|---|---|
| game design | 5 |
| theoretical physics | 5 |
| privacy & surveillance | 5 |
| robotics | 5 |
| decision making | 5 |
| ecology | 5 |
| generative ai | 5 |
| generative design | 5 |
| computational theory | 5 |
| computational physics & simulation | 5 |
| color theory | 6 |
| creative coding | 6 |
| social network analysis | 7 |
| evolutionary biology | 7 |
| interdisciplinary studies | 7 |
| information retrieval | 8 |
| design psychology | 9 |
| computational geometry | 9 |

## Human-review queue (bounded: 69 FBs)
- 4 deferred P4 corrections (non-canonical / class-floor)
- 65 challenger-abstain high-suspicion FBs

Full per-FB detail (name + definition + mechanism + votes): `governance/p5_human_review_form.md`.
