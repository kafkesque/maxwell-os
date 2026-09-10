# R5 Code Review — Qwen3.8-27B (session 2026-09-10)

> User overruled the default gemma first-pass reviewer as unreliable for this pass.
> Reviewer: **Qwen3.8-27B-MLX-4bit** (deep auditor, D2543), temp=0.0 (R7), one-shot per file.
> Scope: the 5 new scripts from this session (D2607 B/C/D + D2609).
> Raw machine output: `governance/r5_review_qwen38_session_2026-09-10.jsonl`.

## Verdicts

| File | Verdict |
|---|---|
| pipeline/boundary_holdout_guard.py | NEEDS_FIX (2) |
| scripts/calibrate_student_thresholds.py | NEEDS_FIX (5) |
| scripts/plan_targeted_ingestion.py | NEEDS_FIX (4) |
| pipeline/student_classifier.py | NEEDS_FIX (5) |
| scripts/train_hierarchical_classifier.py | NEEDS_FIX (4) |

## Triage — fixes APPLIED (genuine findings)

1. **C16 no-silent-errors** (the only real robustness gap class):
   - `boundary_holdout_guard.py`: `yaml.safe_load` now wrapped → clear `ValueError`.
   - `calibrate_student_thresholds.py`: `raw_predict` loop wrapped per-example → log + count + continue (empty-preds guard still raises).
   - `plan_targeted_ingestion.py`: golden YAML read + sqlite query wrapped → `ValueError` with context.
   - `student_classifier.py`: `_load_frozen_label_maps` / `_load_coarse_maps` / `_build_label_maps` /
     `_ensure_loaded(torch.load)` all wrapped → observable fallback or `RuntimeError`.
2. **R14 stamps** on every newly-written persistent artifact (`thresholds.json`,
   `targeted_ingestion_plan.json`, hierarchical `label_maps.json` + `discipline_groups.json`,
   depth `label_maps.json` + `metrics.yaml`): `schema_version` / `gen_model` / `pipeline_commit`
   from `pipeline.pipeline_paths`.
3. **C12**: hardcoded `created` date → `datetime.now(timezone.utc).isoformat()`; added
   `GOLDEN_YAML` / `CHECKPOINT_DIR` / `MAXWELL_DB` / `BOUNDARY_CORPUS` / `TAXONOMY_YAML`
   env overrides (same convention as `train_discipline_classifier.py`).
4. **C18**: docstrings added to `DisciplineClassifier.forward`, `HierarchicalClassifier.forward`,
   `StudentClassifier._encode`.
5. **C20**: gradient-clip `1.0` → `GRAD_CLIP_NORM` named constant.

## Triage — FALSE-POSITIVES (documented, intentionally NOT changed)

- **C12 "hardcoded module constants"** (`BASE_MODEL_NAME`, `MAX_LENGTH`, `DEFAULT_*`,
  `DOMAIN_SIGMOID_THRESHOLD`): these mirror `train_discipline_classifier.py` by design so the
  runtime student stays byte-consistent with the trained checkpoint. Runtime values are ALREADY
  config-driven — `stage4_merge.py` passes `checkpoint_dir` / `threshold` / `coarse_threshold`
  from `config/pipeline_config.yaml`. The module constants are fallbacks.
- **C20 "magic-number thresholds"** (`TARGET_PRECISION`, `MIN_EMIT`, `MIN_GOLDEN_TARGET`,
  `CRITICAL_CONVERGENT`, …): named constants ARE C20-compliant ("extract to named constants OR
  YAML config"). The reviewer applied a stricter config-only reading than the iron rule allows.
- **C16 "training scripts crash without try/except"**: a training script failing with a traceback
  is loud by definition (not a silent error); the atomic-write helpers already prevent partial
  checkpoint writes.

## Verification after fixes

- All 5 files + `scripts/train_depth_classifier.py` pass `py_compile`.
- `boundary_holdout_guard.py` re-verified: 150 held-out ids; `content_type` overlap raises
  `ValueError`; `discipline` overlap no-ops.
- `student_classifier.py` re-verified: hierarchical checkpoint loads; coarse group
  `computing, ai & information` (conf 0.542) + `predict()` abstains (conf < 0.70) = safe.
