# CLASSIFIER CALIBRATION — silver_common (D2585 P4)

Checkpoint: `knowledge pipeline/classifier_modernbert`  |  golden: `config/golden/stage4_golden_mined.yaml`

| metric | value |
|---|---|
| temperature T* | 0.66 |
| macro-F1 @T=1 | 0.225 |
| macro-F1 @T* | 0.225 (Δ +0.0) |
| eval accuracy @T* | 0.2913 |
| ECE @T* | 0.062 |

## Selective macro-F1 by coverage (abstain low-confidence, @T*)

| coverage | macro-F1 |
|---|---|
| 1.0 | 0.22498048399687745 |
| 0.95 | 0.2130497007546188 |
| 0.9 | 0.22179287015352586 |
| 0.8 | 0.2149232370543846 |
| 0.7 | 0.21647150663544104 |
| 0.6 | 0.20663544106167056 |
| 0.5 | 0.18341139734582357 |

## Conformal abstention (α=0.1)

q_hat = 0.9886 | avg set size = 17.573 | empirical coverage = 0.8835
