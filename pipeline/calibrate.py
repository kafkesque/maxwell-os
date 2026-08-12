#!/usr/bin/env python3
"""D2293 Human Calibration Tool — Dual-Encoder S5
=================================================
Review each FB, read the evidence, pick your verdict.
Tracks answers and computes precision/recall at the end.

Usage:
    python3 pipeline/calibrate.py
    python3 pipeline/calibrate.py --resume   # Continue from last session
"""

import json
import os
import sys

WORKBOOK = "governance/calibration_D2293_workbook.json"
PROGRESS = "governance/calibration_D2293_progress.json"

def load_workbook():
    with open(WORKBOOK) as f:
        return json.load(f)

def load_progress():
    if os.path.exists(PROGRESS):
        with open(PROGRESS) as f:
            return json.load(f)
    return {}

def save_progress(progress):
    with open(PROGRESS, "w") as f:
        json.dump(progress, f, indent=2)

def display_fb(fb, index, total):
    """Display one FB for adjudication."""
    print(f"\n{'='*70}")
    print(f"FB {index}/{total} — {fb['category']}")
    print(f"{'='*70}")
    print(f"NAME: {fb['fb_name']}")
    print(f"S5 status: {fb['s5_status']} | Dual verdict: {fb['dual_verdict']}")
    print(f"DeBERTa entail: {fb['d_entail']:.3f} | RoBERTa entail: {fb['r_entail']:.3f}")
    print("\n─── DEFINITION ───")
    print(fb['definition'][:800])
    print("\n─── MECHANISM ───")
    print(fb['mechanism'][:400])
    print("\n─── EVIDENCE PASSAGES ───")
    for i, ep in enumerate(fb.get('evidence_passages', [])[:5]):
        print(f"\n  [{i+1}] {ep[:500]}")

def get_verdict():
    """Get user verdict."""
    print("\n─── YOUR VERDICT ───")
    print("  [1] TP — The FB is CORRECT, dual-encoder was RIGHT to PASS it")
    print("  [2] FP — The FB is WRONG, dual-encoder should have REJECTED it")
    print("  [3] TN — The FB is WRONG, dual-encoder was RIGHT to QUARANTINE it")
    print("  [4] FN — The FB is CORRECT, dual-encoder should have PASSED it")
    print("  [5] SKIP — Come back to this one later")
    print("  [q] QUIT — Save progress and exit")

    while True:
        choice = input("  Your choice [1-5/q]: ").strip().lower()
        if choice == '1': return 'TP'
        if choice == '2': return 'FP'
        if choice == '3': return 'TN'
        if choice == '4': return 'FN'
        if choice == '5': return 'SKIP'
        if choice == 'q': return 'QUIT'
        print("  Invalid choice. Try again.")

def compute_metrics(progress):
    """Compute precision/recall from verdicts."""
    tp = sum(1 for v in progress.values() if v == 'TP')
    fp = sum(1 for v in progress.values() if v == 'FP')
    tn = sum(1 for v in progress.values() if v == 'TN')
    fn = sum(1 for v in progress.values() if v == 'FN')
    total = tp + fp + tn + fn

    if total == 0:
        return {}

    return {
        'total_reviewed': total,
        'TP': tp, 'FP': fp, 'TN': tn, 'FN': fn,
        'precision': round(tp / (tp + fp), 3) if (tp + fp) > 0 else 0,
        'recall': round(tp / (tp + fn), 3) if (tp + fn) > 0 else 0,
        'accuracy': round((tp + tn) / total, 3) if total > 0 else 0,
        'fpr': round(fp / (fp + tn), 3) if (fp + tn) > 0 else 0,
        'fnr': round(fn / (fn + tp), 3) if (fn + tp) > 0 else 0,
    }

def main():
    workbook = load_workbook()
    progress = load_progress()

    # Resume from last session
    resume = '--resume' in sys.argv
    if not resume:
        progress = {}
        save_progress(progress)

    pending = [fb for fb in workbook if fb['fb_name'] not in progress]
    done = len(workbook) - len(pending)

    print("\n🔬 D2293 DUAL-ENCODER CALIBRATION")
    print(f"   {len(workbook)} FBs total | {done} done | {len(pending)} pending")
    print(f"   Progress saved to: {PROGRESS}")

    if not pending:
        print("\n✅ ALL DONE! Computing final metrics...")
        metrics = compute_metrics(progress)
        print(f"\n{'='*50}")
        print("FINAL METRICS")
        print(f"{'='*50}")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
        return

    for i, fb in enumerate(pending, done + 1):
        display_fb(fb, i, len(workbook))
        verdict = get_verdict()

        if verdict == 'QUIT':
            print("\n💾 Progress saved. Resume with: python3 pipeline/calibrate.py --resume")
            break

        if verdict == 'SKIP':
            continue

        progress[fb['fb_name']] = verdict
        save_progress(progress)

        # Show interim metrics
        metrics = compute_metrics(progress)
        if metrics:
            print(f"\n📊 Interim: P={metrics['precision']} R={metrics['recall']} "
                  f"FPR={metrics['fpr']} ({metrics['total_reviewed']}/{len(workbook)} reviewed)")

    # Final report
    metrics = compute_metrics(progress)
    if metrics:
        print(f"\n{'='*50}")
        print(f"CALIBRATION COMPLETE — {metrics['total_reviewed']}/{len(workbook)} FBs")
        print(f"{'='*50}")
        print(f"  Precision:  {metrics['precision']:.3f}  (of dual PASSes, how many are correct)")
        print(f"  Recall:     {metrics['recall']:.3f}  (of correct FBs, how many did dual find)")
        print(f"  Accuracy:   {metrics['accuracy']:.3f}  (overall correct rate)")
        print(f"  FPR:        {metrics['fpr']:.3f}  (false positive rate)")
        print(f"  FNR:        {metrics['fnr']:.3f}  (false negative rate)")
        print(f"\n  TP={metrics['TP']} FP={metrics['FP']} TN={metrics['TN']} FN={metrics['FN']}")

if __name__ == '__main__':
    main()
