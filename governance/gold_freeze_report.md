# GOLD FREEZE REPORT (D2585 P5 v1)

- frozen size: **400** (target 400)
- CHALLENGE (test): **61** | GOLD-B (dev): **58** | GOLD-A (train-safe): **281** | TRAIN_POOL: **627**
- residual book overlap frozen-vs-pool: **793** (0 = fully disjoint)
- residual author overlap frozen-vs-pool: **669**
- min per-class in frozen: **1** | min per-class in pool: **1**

## Usage

    GOLDEN_YAML=config/golden/gold_frozen.yaml GOLDEN_TEST_IDS=<CHALLENGE example ids> python3 scripts/train_discipline_classifier.py
