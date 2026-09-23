# MENU MERGE MAP — discipline tail labels, measured (D-348)

Reader: scripts/knn_arm_eval.py over knowledge pipeline/maxwell.db (vec_fbs, dim 512, 15990 rows). Candidates: 51 closed-menu disciplines. Rule: parent = nearest stored-row centroid; merge proposed only if it beats the runner-up by >= 0.02.

| tail label | rows | proposed parent | cos | runner-up | cos | gap | action | group |
|---|---|---|---|---|---|---|---|---|
| theoretical physics | 26 | - | 0.9269 | systems engineering | 0.9221 | 0.0048 | keep_label | - |
| risk management | 52 | - | 0.9687 | systems engineering | 0.9578 | 0.0109 | keep_label | - |
| cultural studies | 91 | - | 0.9667 | media studies | 0.965 | 0.0017 | keep_label | - |
| decision making | 22 | operations research | 0.9752 | research methodology | 0.9535 | 0.0216 | merge_into_parent | Systems & Method |
| interdisciplinary studies | 25 | - | 0.9279 | political economy | 0.9164 | 0.0115 | keep_label | - |
| computational geometry | 41 | - | 0.9274 | operations research | 0.9187 | 0.0087 | keep_label | - |
| engineering | 88 | - | 0.963 | systems engineering | 0.9585 | 0.0045 | keep_label | - |
| complex adaptive systems | 36 | - | 0.9693 | systems engineering | 0.9661 | 0.0032 | keep_label | - |
| cognitive science | 133 | - | 0.9692 | design thinking | 0.9621 | 0.007 | keep_label | - |
| information security | 41 | - | 0.9423 | artificial intelligence | 0.9347 | 0.0076 | keep_label | - |

1 of 10 tail labels have an unambiguous measured parent; the rest are returned keep_label rather than forced (C16: no invented parent).

RELATIVE-ONLY (D-337). A merge proposal from centroid separability, not an accuracy claim.
