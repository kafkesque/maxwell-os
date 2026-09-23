# REPRESENTABILITY SWEEP — 2026-09-23 (D-343)

**Question:** which axes can a classifier separate AT ALL in the representation the
pipeline actually uses (bge-m3 512d)? **Reference:** a seeded label-permutation NULL,
which preserves label frequencies and therefore absorbs the constant-answer baseline.

| axis | effective n | modal share | kNN agreement | permutation null | lift over null | route |
|---|---|---|---|---|---|---|
| discipline | 7995 | 0.1134 | 0.2652 | 0.0398 | +22.54 pp | `classify` |
| extraction_type | 7995 | 0.3265 | 0.4165 | 0.2675 | +14.89 pp | `coarsen_or_classify_with_calibrated_abstention` |
| content_type | 7995 | 0.8161 | 0.7863 | 0.6834 | +10.28 pp | `constant_plus_human_queue` |
| depth | 6525 | 0.8193 | 0.654 | 0.4568 | +19.71 pp | `constant_plus_human_queue` |
| domains | 7995 | 0.0879 | 0.3095 | 0.0832 | +22.64 pp | `classify` |

## Worst-performing labels per axis (the coarsen/retire queue)

### discipline

| label | rows | kNN agreement | global share |
|---|---|---|---|
| theoreticalphysics | 24 | 0.0417 | 0.003 |
| riskmanagement | 57 | 0.0561 | 0.0071 |
| culturalstudies | 87 | 0.0586 | 0.0109 |
| decisionmaking | 30 | 0.0633 | 0.0038 |
| interdisciplinarystudies | 23 | 0.0696 | 0.0029 |
| computationalgeometry | 41 | 0.0878 | 0.0051 |
| engineering | 85 | 0.0953 | 0.0106 |
| complexadaptivesystems | 45 | 0.0956 | 0.0056 |
| cognitivescience | 131 | 0.1015 | 0.0164 |
| informationsecurity | 38 | 0.1026 | 0.0048 |

### extraction_type

| label | rows | kNN agreement | global share |
|---|---|---|---|
| empiricalpattern | 1513 | 0.3096 | 0.1892 |
| descriptivemodel | 2359 | 0.4131 | 0.2951 |
| normativeheuristic | 1513 | 0.4381 | 0.1892 |
| causalmechanism | 2610 | 0.4689 | 0.3265 |

### content_type

| label | rows | kNN agreement | global share |
|---|---|---|---|
| quarantine | 35 | 0.0029 | 0.0044 |
| growthedge | 30 | 0.0133 | 0.0038 |
| toolinstruction | 23 | 0.0348 | 0.0029 |
| processinstance | 139 | 0.0647 | 0.0174 |
| processtemplate | 188 | 0.1846 | 0.0235 |
| noisedrop | 1055 | 0.258 | 0.132 |
| principle | 6525 | 0.9148 | 0.8161 |

### depth

| label | rows | kNN agreement | global share |
|---|---|---|---|
| universal | 62 | 0.0355 | 0.0095 |
| specialized | 328 | 0.1784 | 0.0503 |
| crossdomain | 789 | 0.2299 | 0.1209 |
| domain | 5346 | 0.7529 | 0.8193 |

## Reading the routing table

- `classify` — the embedding separates the labels; a classifier (any model) can work here.
- `coarsen_or_classify_with_calibrated_abstention` — weak signal; only usable with a measured
  selective-risk curve, never as a silent point label.
- `constant_plus_human_queue` — no label signal in this representation at this granularity.
  Deploying a classifier here is strictly worse than emitting the constant and queueing the
  rest for review (D-275a/D-300). Fix the MENU, not the model.

## Provenance

- decision: D-343 | schema_version: 1.0
- generator: deterministic-numpy (deterministic, no LLM) | commit: 9d0964d
- corpus: knowledge pipeline/maxwell.db (7995 vectors, k=10, seed=20260923)
- reference error rate (quoted, never re-derived — BUG-342): {"content_type": {"n_scored": 150, "agrees": 97, "error": 0.3533, "wilson95": [0.2814, 0.4326], "stratum_a_error": 0.29, "stratum_b_error": 0.48}, "discipline": {"n_scored": 116, "agrees": 61, "error": 0.4741, "wilson95": [0.3856, 0.5644], "stratum_a_error": 0.4875, "stratum_b_error": 0.4444, "effective_n_note": "34 of 150 cannot be scored: 28 blank + 6 `emerging` (BUG-334: publish the effective n)"}, "extraction_type": {"n_scored": 145, "agrees": 104, "error": 0.2828, "wilson95": [0.2158, 0.3609], "stratum_a_error": 0.2551, "stratum_b_error": 0.3404}}
- control: the permutation null above IS the blinding control (R3 precedent).
