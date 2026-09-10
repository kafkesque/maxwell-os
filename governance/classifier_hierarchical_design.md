# Hierarchical Discipline Classifier — Design (D2607, option B)

> **Status:** IMPLEMENTED + MEASURED (2026-09-09) — see "Measured results" below. Coarse head works; masked fine re-rank falsified.
> **Companion decision:** D2607 (config/decisions.yaml) — sequence C (hybrid, done) → B (this) → targeted ingestion.

## 0. Measured results (2026-09-09)

Trained `knowledge pipeline/classifier_hierarchical` (shared ModernBERT, coarse
10-way + fine 61-way + domain 43-way) on the 1,027-ex golden set. Held-out fold
(202 ex, random_state=42):

| Head | macro-F1 | top-1 accuracy |
|---|---|---|
| coarse (10-way) | 0.461 | **0.540** |
| fine flat (61-way) | 0.214 | 0.287 |
| fine masked (hierarchical) | 0.175 | **0.248** |
| domain (43-way) | 0.008 | — |

**Findings:**
1. **Masked fine re-rank is FALSIFIED** — 24.8% top-1 < 28.7% flat. The coarse
   router's 46% error rate propagates unrecoverably: a wrong group hides the correct
   discipline, so "shrinking the confusion set 61→≤15" nets NEGATIVE. The design
   premise "realistic macro-F1 >> 0.75" for the coarse head is also false (0.461).
2. **The coarse head is the keeper** — 10-way at 54% top-1, well-calibrated
   (median confidence 0.505, max 0.918), reaches 90% precision @ 20% coverage
   (threshold 0.7). A far better student pre-classifier signal than the 61-way flat
   head (28.7% top-1, cannot reach 90% precision at any coverage).
3. **Domain head is dead** (~0.8% macro-F1) — pre-existing data-limitation, not
   caused by B. Domain labels are even more skewed than discipline.

**Revised conclusion:** B's coarse head SUCCEEDS as the structural fix for the
student; B's masked fine re-rank is a dead end. The fine 61-way head remains
data-limited — only targeted ingestion (D) lifts it.

## 1. Why hierarchical

The ModernBERT student is a **flat 61-way softmax** over 1,027 golden examples
(~17/class). The audit that motivated D2607 found the per-class skew is fatal:

- Convergent labeled pool (2,441 FBs): **29/61 disciplines <20 ex, 10/61 <5 ex**.
- Golden set (already single-source backfilled): **18/61 <10 ex, 5/61 <5 ex**
  (game design 3, design psychology 4, ecology 4, robotics 4, computational physics 4).

A flat 61-way head can never reach macro-F1 0.75 with that tail — the 0.00-F1
classes dominate the macro average. Option C (hybrid fallback) fixes *end-to-end*
accuracy; option B fixes the *standalone* student by reducing the per-head class
count so every class has enough signal.

## 2. Coarse grouping (61 → 10)

| # | Coarse group | Disciplines | Golden ex |
|---|---|---|---|
| 1 | design & visual arts | aesthetics, color theory, computer graphics, creative coding, creative process, cultural design, design psychology, design thinking, game design, generative design, motion & time, performing arts, typography, visual perception, visual semiotics | 228 |
| 2 | human & behavioral science | anthropology, behavioral economics, cognitive science, cultural studies, neuroscience, psychology, sociology | 166 |
| 3 | computing, ai & information | artificial intelligence, generative ai, human-computer interaction, information retrieval, information science, information security, machine learning, privacy & surveillance, software engineering | 148 |
| 4 | economics & business | decision making, economics, finance, organizational theory, political economy, strategic thinking | 118 |
| 5 | communication & media | communication theory, linguistics, literary theory, media studies, semiotics | 110 |
| 6 | systems & operations | complex adaptive systems, operations research, research methodology, systems engineering, systems thinking | 110 |
| 7 | philosophy & law | law, philosophy, risk management | 56 |
| 8 | engineering, math & physics | computational geometry, computational physics & simulation, computational theory, engineering, robotics, theoretical physics | 42 |
| 9 | life & health science | ecology, evolutionary biology, health & medicine | 34 |
| 10 | interdisciplinary | interdisciplinary studies, social network analysis | 15 |

Even the thinnest coarse group (interdisciplinary, 15 ex) is 3× the median
per-discipline count. A 10-way coarse head over these totals is a *much* easier
problem than 61-way over the same data — realistic macro-F1 >> 0.75.

## 3. Architecture (two-stage)

```
FB text ──► ModernBERT (shared backbone)
              ├── coarse_head: 10-way softmax  → group
              └── fine_head:   61-way softmax  → discipline (within-group re-rank)
```

- **Stage 1 (coarse):** predict the 10-way group.
- **Stage 2 (fine):** restrict the 61-way softmax to the predicted group's members
  (mask out-of-group logits), then argmax within the group. This shrinks the
  per-class confusion set from 61 → ≤15 and concentrates signal on the genuinely
  confusable siblings.
- **Abstain:** if coarse confidence or fine confidence < threshold → route to
  gpt-oss (this is option C, already wired — the two options compose cleanly).

## 4. Implementation plan

1. Add `config/taxonomy_v5.yaml` `discipline_groups` (10 groups, above mapping) — C12 config-first, single source of truth.
2. Extend `scripts/train_discipline_classifier.py` with a `--hierarchical` mode (coarse head + masked fine head), OR a separate `train_hierarchical.py`.
3. Save `label_maps.json` + `discipline_groups.json` in the checkpoint (closes the current reconstruction fragility in `pipeline/student_classifier.py`).
4. Retrain, measure: coarse macro-F1 (expect >>0.75) + fine within-group macro-F1.
5. Wire the hierarchical head into `pipeline/student_classifier.py` behind the same `student_preclassifier_enabled` flag.

## 5. Relationship to C

- **C (done)** = end-to-end accuracy via student→gpt-oss fallback (KPI: end-to-end).
- **B (this)** = standalone student accuracy via coarse→fine structure.
- **Targeted ingestion** = the only lever that raises the *fine* per-discipline
  counts for the ~18 starved disciplines (game design, ecology, design psychology,
  robotics, computational physics, theoretical physics, …).

Order of operations (D2607): **C → B → targeted ingestion**, with Tier3 (D2594)
boundary corpus running in parallel as the evaluation substrate.
