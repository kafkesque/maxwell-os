# Representability sweep receipt (2026-09-23, D-343)

Frozen copy of the measurement behind D-343. Question: which axes can a classifier separate at all in the representation the pipeline uses (bge-m3 512d)? Two references: a seeded label-permutation NULL (is there any signal?) and the constant-answer baseline (is a classifier better than always emitting the modal label?).

- **discipline**: knn 0.2652 vs constant 0.1134 (+15.18 pp) vs null 0.0398 (+22.54 pp) -> `classify`
- **extraction_type**: knn 0.4165 vs constant 0.3265 (+9.0 pp) vs null 0.2675 (+14.89 pp) -> `coarsen_or_classify_with_calibrated_abstention`
- **content_type**: knn 0.7863 vs constant 0.8161 (-2.99 pp) vs null 0.6834 (+10.28 pp) -> `constant_plus_human_queue`
- **depth**: knn 0.654 vs constant 0.8193 (-16.53 pp) vs null 0.4568 (+19.71 pp) -> `constant_plus_human_queue`
- **domains**: knn 0.3095 vs constant 0.0879 (+22.16 pp) vs null 0.0832 (+22.64 pp) -> `classify`
