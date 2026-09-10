# CLASSIFIER CALIBRATION — p4_common (D2585 P4)

Checkpoint: `knowledge pipeline/classifier_modernbert_p4`  |  golden: `config/golden/stage4_golden_mined.yaml`

| metric | value |
|---|---|
| temperature T* | 0.4 |
| macro-F1 @T=1 | 0.2757 |
| macro-F1 @T* | 0.2757 (Δ +0.0) |
| eval accuracy @T* | 0.3689 |
| ECE @T* | 0.0583 |

## Selective macro-F1 by coverage (abstain low-confidence, @T*)

| coverage | macro-F1 |
|---|---|
| 1.0 | 0.2757374683604192 |
| 0.95 | 0.28481654957064795 |
| 0.9 | 0.28099141295862606 |
| 0.8 | 0.29988290398126466 |
| 0.7 | 0.30084805904478035 |
| 0.6 | 0.3151834504293521 |
| 0.5 | 0.3091334894613583 |

## Conformal abstention (α=0.1)

q_hat = 0.9933 | avg set size = 18.165 | empirical coverage = 0.9806
