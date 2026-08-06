#!/usr/bin/env python3
"""
nli_calibrate.py — NLI Threshold Calibration for Stage 5 Verification.
======================================================================
D2181: T1.4 — Calibrates entailment/neutral/contradiction thresholds
for ModernBERT NLI pre-filter in stage5_verify.py.

Problem: Current thresholds (0.6 entailment, 0.8 pass, 0.5 marginal)
are guesses. Uncalibrated thresholds cause false positives (weak
evidence passes as "verified") or false negatives (good FBs quarantined).

Approach:
  1. Load FBs from Stage 4 output (or a labeled calibration file)
  2. For each FB, run NLI on definition vs each evidence passage
  3. Compute precision/recall at threshold candidates [0.5, 0.55, ..., 0.95]
  4. Report optimal thresholds that balance precision and recall

Two modes:
  --auto: Use FB evidence passages as "should-entail" positives and
          random unrelated pairs as "should-not-entail" negatives.
  --labeled PATH: Use a hand-labeled JSONL file with explicit labels.

Usage:
  python3 pipeline/nli_calibrate.py --auto        # Auto-calibrate from FBs
  python3 pipeline/nli_calibrate.py --labeled evals/nli_golden.jsonl
  python3 pipeline/nli_calibrate.py --auto --dry-run  # Test without loading model
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from pipeline.pipeline_paths import S5_NLI_MODEL
from pipeline.stage5_verify import _get_nli, nli_entailment


def load_fbs_from_stage4() -> list[dict]:
    """Load FBs from Stage 4 checkpoint."""
    from pipeline.pipeline_paths import STAGE4_OUTPUT
    if not STAGE4_OUTPUT.exists():
        print(f"❌ Stage 4 output not found at {STAGE4_OUTPUT}")
        sys.exit(1)
    fbs = []
    with open(STAGE4_OUTPUT) as f:
        for line in f:
            line = line.strip()
            if line:
                fbs.append(json.loads(line))
    print(f"📂 Loaded {len(fbs)} FBs from Stage 4")
    return fbs


def build_auto_pairs(fbs: list[dict]) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Build calibration pairs automatically from FB evidence.

    Positive pairs: definition ↔ its own evidence_passages (should ENTAIL or NEUTRAL)
    Negative pairs: definition ↔ random evidence from OTHER FBs (should CONTRADICT or NEUTRAL)

    Returns (labeled_pairs, passages) where each pair is
    (definition, evidence, expected_label).
    Labels are "POSITIVE" (same FB) or "NEGATIVE" (different FB).
    """
    import random
    random.seed(42)

    pairs: list[tuple[str, str, str]] = []

    for fb in fbs:
        definition = fb.get("definition", "")
        if not definition:
            continue

        # Evidence passages from this FB (positive examples)
        evidence = fb.get("evidence_passages", [])
        if isinstance(evidence, list):
            for ev in evidence[:3]:  # Max 3 per FB
                ev_text = ev if isinstance(ev, str) else str(ev)
                if len(ev_text) > 50 and len(definition) > 50:
                    pairs.append((definition, ev_text, "POSITIVE"))

    # Build negative pairs: definition ↔ random evidence from OTHER FBs
    all_evidence = []
    for fb in fbs:
        evidence = fb.get("evidence_passages", [])
        if isinstance(evidence, list):
            for ev in evidence:
                ev_text = ev if isinstance(ev, str) else str(ev)
                if len(ev_text) > 50:
                    all_evidence.append(ev_text)

    neg_count = min(len(pairs), len(all_evidence) * 2)
    for _ in range(neg_count):
        fb = random.choice(fbs)
        definition = fb.get("definition", "")
        ev = random.choice(all_evidence)
        if definition and ev:
            pairs.append((definition, ev, "NEGATIVE"))

    print(f"🧪 Auto-calibration: {len([p for p in pairs if p[2]=='POSITIVE'])} positive, "
          f"{len([p for p in pairs if p[2]=='NEGATIVE'])} negative pairs")
    return pairs, all_evidence


def load_labeled_pairs(path: str) -> list[tuple[str, str, str]]:
    """Load hand-labeled NLI calibration pairs from JSONL.

    Expected format per line:
    {"definition": "...", "evidence": "...", "label": "ENTAILMENT|NEUTRAL|CONTRADICTION"}
    """
    pairs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rec = json.loads(line)
            pairs.append((
                rec["definition"],
                rec["evidence"],
                rec.get("label", "NEUTRAL"),
            ))
    print(f"📂 Loaded {len(pairs)} hand-labeled pairs from {path}")
    return pairs


def calibrate(pairs: list[tuple[str, str, str]], dry_run: bool = False) -> dict:
    """Run NLI on all pairs and compute threshold recommendations.

    Args:
        pairs: List of (definition, evidence, expected_label) tuples.
        dry_run: If True, skip model loading (syntax check only).

    Returns:
        Dict with threshold_candidates, best_thresholds, and raw scores.
    """
    if dry_run:
        print("🔍 DRY RUN — skipping NLI model load")
        return {"dry_run": True, "pair_count": len(pairs)}

    # Load NLI pipeline (lazy, cached)
    print(f"🧠 Loading NLI model: {S5_NLI_MODEL}...")
    _ = _get_nli()  # Pre-load
    print(f"   Running {len(pairs)} NLI inferences...")

    scores: list[dict] = []
    start = time.time()
    for i, (definition, evidence, label) in enumerate(pairs):
        if i % 50 == 0 and i > 0:
            elapsed = time.time() - start
            rate = i / elapsed
            eta = (len(pairs) - i) / rate
            print(f"   [{i}/{len(pairs)}] {rate:.1f}/s, ETA {eta:.0f}s")

        result = nli_entailment(definition, evidence)
        scores.append({
            "definition": definition[:100],
            "evidence": evidence[:100],
            "expected_label": label,
            "nli_label": result.get("label", "NEUTRAL"),
            "nli_score": result.get("score", 0.0),
            "entailment_score": result.get("entailment_score", 0.0),
            "neutral_score": result.get("neutral_score", 0.0),
            "contradiction_score": result.get("contradiction_score", 0.0),
        })

    elapsed = time.time() - start
    print(f"   ✅ {len(pairs)} pairs in {elapsed:.0f}s ({len(pairs)/elapsed:.1f}/s)")

    # Analyze threshold candidates
    thresholds = np.arange(0.50, 0.96, 0.05)
    results = []

    for t in thresholds:
        # Binary classification: entailment_score >= t → POSITIVE prediction
        tp = fp = tn = fn = 0
        for s in scores:
            pred_positive = s["entailment_score"] >= t
            actual_positive = s["expected_label"] == "POSITIVE"

            if pred_positive and actual_positive:
                tp += 1
            elif pred_positive and not actual_positive:
                fp += 1
            elif not pred_positive and not actual_positive:
                tn += 1
            else:
                fn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        results.append({
            "threshold": round(float(t), 2),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        })

    # Find best threshold by F1 (balanced) and by precision (fail-closed)
    best_f1 = max(results, key=lambda r: r["f1"])
    best_precision = max(
        [r for r in results if r["precision"] >= 0.85],
        key=lambda r: r["recall"],
        default=results[len(results)//2],
    )

    return {
        "pair_count": len(pairs),
        "threshold_candidates": results,
        "best_f1_threshold": best_f1,
        "best_precision_threshold": best_precision,
        "raw_scores": scores,
    }


def print_report(calibration: dict) -> None:
    """Print calibration report with threshold recommendations."""
    if calibration.get("dry_run"):
        print(f"\n🔍 DRY RUN — {calibration['pair_count']} pairs would be processed")
        return

    print("\n" + "=" * 70)
    print("NLI THRESHOLD CALIBRATION REPORT")
    print("=" * 70)

    candidates = calibration["threshold_candidates"]
    print(f"\n{'Threshold':>10} {'Prec':>7} {'Recall':>7} {'F1':>7} {'TP':>5} {'FP':>5} {'TN':>5} {'FN':>5}")
    print("-" * 60)
    for r in candidates:
        marker = ""
        if r == calibration["best_f1_threshold"]:
            marker = " ← best F1"
        elif r == calibration["best_precision_threshold"]:
            marker = " ← best precision (fail-closed)"
        print(f"{r['threshold']:>10.2f} {r['precision']:>7.3f} {r['recall']:>7.3f} "
              f"{r['f1']:>7.3f} {r['tp']:>5} {r['fp']:>5} {r['tn']:>5} {r['fn']:>5}{marker}")

    print("\n📊 RECOMMENDED THRESHOLDS:")
    best_f1 = calibration["best_f1_threshold"]
    best_prec = calibration["best_precision_threshold"]
    print(f"   NLI_ENTAILMENT_THRESHOLD = {best_f1['threshold']:.2f}  (F1={best_f1['f1']:.3f})")
    print(f"   NLI_PASS_THRESHOLD      = {best_prec['threshold']:.2f}  (precision={best_prec['precision']:.3f})")
    print(f"   NLI_MARGINAL_THRESHOLD  = {max(0.40, best_f1['threshold'] - 0.10):.2f}  (lower bound)")

    # Compare with current defaults
    print("\n📋 CURRENT DEFAULTS (pipeline_config.yaml):")
    print("   NLI_ENTAILMENT_THRESHOLD = 0.60")
    print("   NLI_PASS_THRESHOLD      = 0.80")
    print("   NLI_MARGINAL_THRESHOLD  = 0.50")

    drift = abs(best_f1["threshold"] - 0.60)
    if drift > 0.10:
        print(f"\n⚠️  THRESHOLD DRIFT: recommended NLI_ENTAILMENT_THRESHOLD "
              f"differs from default by {drift:.2f}. Update pipeline_config.yaml.")

    # Save raw scores for analysis
    out_path = Path("knowledge pipeline/metrics/nli_calibration.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(calibration, f, indent=2, default=str)
    print(f"\n💾 Full results saved to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="NLI Threshold Calibration")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-calibrate from Stage 4 FB evidence passages")
    parser.add_argument("--labeled", type=str,
                        help="Path to hand-labeled JSONL calibration file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate inputs without loading NLI model")
    parser.add_argument("--output", type=str, default="knowledge pipeline/metrics/nli_calibration.json",
                        help="Output path for calibration results")

    args = parser.parse_args()

    if args.auto:
        fbs = load_fbs_from_stage4()
        if len(fbs) < 3:
            print("❌ Need ≥3 FBs for auto-calibration. Run S2+S4 first.")
            sys.exit(1)
        pairs, _ = build_auto_pairs(fbs)
    elif args.labeled:
        pairs = load_labeled_pairs(args.labeled)
    else:
        print("❌ Specify --auto or --labeled PATH")
        sys.exit(1)

    if len(pairs) < 10:
        print(f"❌ Need ≥10 calibration pairs, got {len(pairs)}")
        sys.exit(1)

    calibration = calibrate(pairs, dry_run=args.dry_run)
    print_report(calibration)


if __name__ == "__main__":
    main()
