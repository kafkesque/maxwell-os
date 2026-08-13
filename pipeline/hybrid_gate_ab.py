#!/usr/bin/env python3
"""
hybrid_gate_ab.py — A/B test: S2 hybrid gate ON vs OFF (BUG-085 / D2276 decision).

Authority: D2276, D2250/D2251, BUG-085.

Purpose: Decide whether T1.1 should enable the HybridGate pre-extraction filter
(`stage2_extract.py --hybrid`). The gate is a cheap (~1-2s) FB/NULL pre-filter that
skips non-principle clusters before the expensive (~28s) traditional extraction.

A/B framing:
  - Method A (hybrid OFF = traditional): extracts EVERY cluster. 100% recall, but
    spends ~28s on every non-principle cluster (negative) — pure waste.
  - Method B (hybrid ON): gate decides FB/NULL first. Ideal if it rejects negatives
    (saves ~28s each) WITHOUT rejecting positives (no recall loss).

This harness evaluates the gate against the 75-example golden set:
  - positives (should_extract=True)  → gate SHOULD return FB  (recall)
  - negatives (should_extract=False) → gate SHOULD return NULL (rejection)

Kill criteria for adopting hybrid (from D2250: gate is a "perfect negative filter"):
  - Positive recall (TP/(TP+FN)) must be ~1.0 — no missed principles.
  - Negative rejection (TN/(TN+FP)) should be high — time saved.

Usage:
    python3 pipeline/hybrid_gate_ab.py            # full 75-example run (~2-3 min)
    python3 pipeline/hybrid_gate_ab.py --limit 20 # quick subset
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml

from pipeline.hybrid_gate import HybridGate, format_segments_for_gate

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "config" / "golden" / "stage2_fewshot_convergent.yaml"
# D2250/D2276: traditional extraction ~28s per cluster (probe-measured). Config-adjacent
# constant — the actual S2 cost is not a config value; this is a documented estimate for
# time-savings projection only, not a runtime threshold.
TRADITIONAL_EXTRACT_SECONDS = 28.0


def _expected_route(example: dict) -> str:
    """Map golden ground truth to the route the gate should produce."""
    should_extract = example.get("should_extract")
    return "FB" if should_extract is True else "NULL"


def run_ab(limit: int | None = None, verbose: bool = False) -> dict:
    """Run the hybrid gate against the golden set and return a structured report."""
    with open(GOLDEN_PATH) as f:
        golden = yaml.safe_load(f) or {}
    examples: list[dict] = golden.get("examples", [])
    if limit:
        examples = examples[:limit]

    gate = HybridGate(provider="omlx")

    # Confusion matrix relative to the gate's recall-biased objective.
    tp = tn = fp = fn = 0  # FB→FB, NULL→NULL, FB→NULL(error->FB), NULL→FB
    rows: list[dict] = []
    total_gate_time = 0.0

    for ex in examples:
        expected = _expected_route(ex)
        seg_text = format_segments_for_gate(ex.get("cluster_segments", []))
        source_books = ex.get("source_books", [])

        t0 = time.time()
        actual = gate.decide(seg_text, source_books)
        elapsed = time.time() - t0
        total_gate_time += elapsed

        if expected == "FB" and actual == "FB":
            tp += 1
        elif expected == "NULL" and actual == "NULL":
            tn += 1
        elif expected == "FB" and actual == "NULL":
            fn += 1  # recall loss — worst outcome
        else:  # expected NULL, actual FB (or ERROR→FB)
            fp += 1

        rows.append({
            "id": ex.get("id"),
            "tier": ex.get("tier"),
            "expected": expected,
            "actual": actual,
            "elapsed_s": round(elapsed, 2),
        })
        if verbose:
            mark = "✅" if expected == actual else "❌"
            print(f"  {mark} {ex.get('id'):16s} expected={expected:4s} actual={actual:4s} ({elapsed:.1f}s)")

    n_pos = tp + fn
    n_neg = tn + fp
    recall = (tp / n_pos * 100.0) if n_pos else 0.0
    rejection = (tn / n_neg * 100.0) if n_neg else 0.0
    accuracy = ((tp + tn) / len(rows) * 100.0) if rows else 0.0

    # Time projection: Method A (no gate) = all clusters × 28s.
    # Method B = all clusters × gate_time + (clusters passing FB) × 28s.
    method_a_seconds = len(rows) * TRADITIONAL_EXTRACT_SECONDS
    method_b_seconds = total_gate_time + (tp + fp) * TRADITIONAL_EXTRACT_SECONDS
    time_saved_pct = (1.0 - method_b_seconds / method_a_seconds) * 100.0 if method_a_seconds else 0.0

    return {
        "n": len(rows),
        "positives": n_pos,
        "negatives": n_neg,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "recall_pct": round(recall, 1),
        "rejection_pct": round(rejection, 1),
        "accuracy_pct": round(accuracy, 1),
        "avg_gate_s": round(total_gate_time / len(rows), 2) if rows else 0.0,
        "method_a_s": round(method_a_seconds, 1),
        "method_b_s": round(method_b_seconds, 1),
        "time_saved_pct": round(time_saved_pct, 1),
        "rows": rows,
        "gate_stats": gate.stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid gate A/B test (BUG-085 / D2276)")
    parser.add_argument("--limit", type=int, default=None, help="Limit to first N examples")
    parser.add_argument("--verbose", action="store_true", help="Print per-example results")
    args = parser.parse_args()

    r = run_ab(limit=args.limit, verbose=args.verbose)

    print("\n" + "=" * 70)
    print("   HYBRID GATE A/B TEST — golden set vs should_extract")
    print("=" * 70)
    print(f"   Examples:  {r['n']} ({r['positives']} positive, {r['negatives']} negative)")
    print(f"   Confusion: TP={r['tp']}  TN={r['tn']}  FP={r['fp']}  FN={r['fn']}")
    print(f"   Positive recall (FB→FB):      {r['recall_pct']}%   ← must be ~100%")
    print(f"   Negative rejection (NULL→NULL): {r['rejection_pct']}%   ← time saved")
    print(f"   Overall accuracy:              {r['accuracy_pct']}%")
    print(f"   Avg gate latency:              {r['avg_gate_s']}s")
    print()
    print(f"   Method A (no gate):  {r['method_a_s']}s  (extract all {r['n']} clusters)")
    print(f"   Method B (hybrid):   {r['method_b_s']}s  (gate + extract {r['tp']+r['fp']} FB)")
    print(f"   ⏱  Time saved:        {r['time_saved_pct']}%")
    print(f"   Gate stats:           {r['gate_stats']}")
    print("=" * 70)

    if r["recall_pct"] < 90.0:
        print("\n❌ VERDICT: hybrid gate DROPS positives (recall <90%) — do NOT enable for T1.1")
        return 1
    if r["rejection_pct"] < 50.0:
        print("\n⚠️  VERDICT: hybrid gate safe (high recall) but low time savings — optional")
    else:
        print("\n✅ VERDICT: hybrid gate safe (high recall) + saves time — ENABLE --hybrid for T1.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
