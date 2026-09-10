#!/usr/bin/env python3
"""calibrate_student_thresholds.py — D2609 (C): per-class selective thresholds
for the ModernBERT student pre-classifier.

The student's value is NOT standalone accuracy (macro-F1 ~0.20 — data-limited)
but COST SAVINGS: emit a discipline prediction only when confident enough that
the emitted prediction is correct (precision >= target), and abstain -> gpt-oss
fallback otherwise. A single flat threshold (0.35) over-abstains because the raw
softmax is under-confident (max-prob ~0.02-0.15, vs 1/56 ~= 0.018 uniform).

This script derives PER-CLASS thresholds (with a global fallback) from the SAME
held-out fold the checkpoint was evaluated on (random_state=42 stratify split,
test_size=0.2) — i.e. examples the checkpoint did NOT train on. It writes
thresholds.json into the checkpoint dir (C6 atomic), which
pipeline/student_classifier.py loads at inference.

R5 (generator != verifier): thresholds.json is a DERIVED artifact — review it
against the checkpoint BEFORE enabling student_preclassifier_enabled.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import yaml
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# R14 stamps (single source of truth: pipeline_paths).
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

# C12: paths overridable via env (same convention as train_discipline_classifier).
GOLDEN = Path(os.environ.get("GOLDEN_YAML", ROOT / "config" / "golden" / "stage4_golden_mined.yaml"))
CHECKPOINT = Path(os.environ.get(
    "CHECKPOINT_DIR",
    ROOT / "knowledge pipeline" / "classifier_modernbert_p5final",
))
STUDENT_BASE_MODEL = "answerdotai/ModernBERT-base"  # R14 gen_model stamp for thresholds.json

# Mirror scripts/train_discipline_classifier.py so the held-out fold is identical.
MIN_EXAMPLES_PER_CLASS: int = 5
RANDOM_STATE: int = 42
TEST_SIZE: float = 0.2

TARGET_PRECISION: float = 0.90
MIN_CAL_PER_CLASS: int = 3  # min held-out predictions for a class to get its own threshold
MIN_EMIT: int = 3  # min emitted predictions required before a threshold is trusted


def _fb_text(ex: Dict[str, Any]) -> str:
    """Reconstruct the student's input text exactly as stage4_merge does."""
    fb = ex.get("input_fb") or {}
    return " ".join(
        str(fb.get(k, "")) for k in ("name", "definition", "mechanism", "boundary")
    ).strip()


def load_trainable_examples() -> List[Dict[str, Any]]:
    """Load golden, drop <min-per-class disciplines (same as training)."""
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8")) or {}
    flat: List[Dict[str, Any]] = []
    for ex in data.get("examples", []):
        ec = ex.get("expected_classification") or {}
        if not ec.get("discipline"):
            continue
        flat.append({
            "id": ex.get("id"),
            "discipline": ec["discipline"],
            "text": _fb_text(ex),
        })
    counts = Counter(e["discipline"] for e in flat)
    return [e for e in flat if counts[e["discipline"]] >= MIN_EXAMPLES_PER_CLASS]


def _threshold_for(items: List[Tuple[float, bool]], target_precision: float,
                   min_emit: int = MIN_EMIT) -> float:
    """Return the lowest-confidence cutoff whose top-k prefix has precision >= target.

    Args:
        items: (confidence, is_correct) pairs.
        target_precision: Minimum required precision on the emitted prefix.
        min_emit: Minimum emitted predictions required before a threshold is trusted.

    Returns:
        Confidence threshold, or 1.0 if no prefix (of >= min_emit) meets target
        (i.e. abstain everything for this class).
    """
    if len(items) < min_emit:
        return 1.0
    ordered = sorted(items, key=lambda x: -x[0])
    best_idx = -1
    correct = 0
    for i, (_, ok) in enumerate(ordered):
        correct += 1 if ok else 0
        if (i + 1) >= min_emit and correct / (i + 1) >= target_precision:
            best_idx = i
    if best_idx == -1:
        return 1.0
    return ordered[best_idx][0]


def _precision_at(preds: List[Tuple[float, bool]], tau: float) -> Tuple[float, int]:
    """Return (precision, emitted_count) for predictions with confidence >= tau."""
    emitted = [ok for conf, ok in preds if conf >= tau]
    if not emitted:
        return 1.0, 0
    return sum(emitted) / len(emitted), len(emitted)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write thresholds.json (else dry-run)")
    ap.add_argument("--target-precision", type=float, default=TARGET_PRECISION)
    ap.add_argument("--min-cal-per-class", type=int, default=MIN_CAL_PER_CLASS)
    ap.add_argument("--min-emit", type=int, default=MIN_EMIT)
    ap.add_argument("--limit", type=int, default=0, help="cap calibration examples (0 = all)")
    args = ap.parse_args()

    examples = load_trainable_examples()
    disciplines = sorted({e["discipline"] for e in examples})
    label_map = {d: i for i, d in enumerate(disciplines)}
    labels = np.array([label_map[e["discipline"]] for e in examples])

    _, test_idx = train_test_split(
        np.arange(len(examples)),
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels,
    )
    cal_examples = [examples[i] for i in test_idx]
    if args.limit:
        cal_examples = cal_examples[: args.limit]
    print(f"calibration set: {len(cal_examples)} held-out examples "
          f"({len(disciplines)} trainable disciplines)")

    # Run the SAME student the production path uses (CPU, frozen label maps).
    from pipeline.student_classifier import StudentClassifier
    student = StudentClassifier(checkpoint_dir=str(CHECKPOINT), golden_path=str(GOLDEN))

    # (predicted_discipline, confidence, is_correct) over the held-out fold.
    preds: List[Tuple[str, float, bool]] = []
    skipped_pad = 0
    failed = 0
    for ex in cal_examples:
        try:
            r = student.raw_predict(ex["text"])
        except (OSError, ValueError, RuntimeError) as exc:
            # C16: log AND continue (a single bad row must not abort calibration);
            # if everything fails the empty-preds guard below raises loudly.
            print(f"[warn] raw_predict failed for {ex.get('id', '?')}: {exc}", file=sys.stderr)
            failed += 1
            continue
        disc = r["discipline"]
        if disc is None:
            skipped_pad += 1
            continue
        preds.append((disc, r["confidence"], disc == ex["discipline"]))

    if failed:
        print(f"[warn] {failed} calibration examples failed raw_predict", file=sys.stderr)
    if not preds:
        raise SystemExit("no usable held-out predictions — cannot calibrate")

    global_tau = _threshold_for([(c, ok) for _, c, ok in preds], args.target_precision,
                                args.min_emit)
    g_prec, g_emit = _precision_at([(c, ok) for _, c, ok in preds], global_tau)

    per_class: Dict[str, float] = {}
    by_class: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)
    for disc, conf, ok in preds:
        by_class[disc].append((conf, ok))
    for disc, items in by_class.items():
        if len(items) >= args.min_cal_per_class:
            per_class[disc] = _threshold_for(items, args.target_precision, args.min_emit)

    # Effective abstention rate: per-class threshold where present, else global.
    emitted = 0
    for disc, conf, _ in preds:
        tau = per_class.get(disc, global_tau)
        if conf >= tau:
            emitted += 1
    coverage = emitted / len(preds)

    out = {
        "calibration_source": "held-out val fold (random_state=42, stratify, test_size=0.2)",
        "n_calibration": len(cal_examples),
        "n_predicted": len(preds),
        "n_skipped_pad": skipped_pad,
        "n_failed": failed,
        "target_precision": args.target_precision,
        "global_threshold": round(global_tau, 6),
        "global_estimated_precision": round(g_prec, 4),
        "global_estimated_coverage": round(g_emit / len(preds), 4),
        "per_class_thresholds": {k: round(v, 6) for k, v in sorted(per_class.items())},
        "n_per_class": len(per_class),
        "estimated_coverage": round(coverage, 4),
        "estimated_abstention": round(1.0 - coverage, 4),
        # R14 stamps (persistent artifact traceability).
        "schema_version": SCHEMA_VERSION,
        "gen_model": STUDENT_BASE_MODEL,
        "pipeline_commit": PIPELINE_COMMIT,
        "created": datetime.now(timezone.utc).isoformat(),
    }

    print(json.dumps({
        "global_threshold": out["global_threshold"],
        "global_precision": out["global_estimated_precision"],
        "global_coverage": out["global_estimated_coverage"],
        "n_per_class": out["n_per_class"],
        "estimated_coverage": out["estimated_coverage"],
        "estimated_abstention": out["estimated_abstention"],
        "per_class_sample": dict(list(out["per_class_thresholds"].items())[:10]),
    }, indent=2))

    if not args.apply:
        print("\nDRY-RUN — re-run with --apply to write thresholds.json.")
        return 0

    payload = json.dumps(out, indent=2, sort_keys=False)
    fd, tmp = tempfile.mkstemp(dir=str(CHECKPOINT), suffix=".json")
    with os.fdopen(fd, "w") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CHECKPOINT / "thresholds.json")
    print(f"\n✅ wrote thresholds.json to {CHECKPOINT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
