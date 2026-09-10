# CLASSIFIER CALIBRATION — p4_clean (D2585 P4)

Checkpoint: `knowledge pipeline/classifier_modernbert_p4_clean`  |  golden: `config/golden/stage4_golden_mined.yaml`

| metric | value |
|---|---|
| temperature T* | 0.6 |
| macro-F1 @T=1 | 0.2875 |
| macro-F1 @T* | 0.2875 (Δ +0.0) |
| eval accuracy @T* | 0.3981 |
| ECE @T* | 0.144 |

## Selective macro-F1 by coverage (abstain low-confidence, @T*)

| coverage | macro-F1 |
|---|---|
| 1.0 | 0.2875487900078064 |
| 0.95 | 0.29327821540936294 |
| 0.9 | 0.29683012797766894 |
| 0.8 | 0.28454332552693207 |
| 0.7 | 0.24242779078844653 |
| 0.6 | 0.23641686182669785 |
| 0.5 | 0.23907103825136608 |

## Conformal abstention (α=0.1)

q_hat = 0.9889 | avg set size = 16.379 | empirical coverage = 0.8932
