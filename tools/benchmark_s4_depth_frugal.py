#!/usr/bin/env python3
"""
S4 Focused-Depth Benchmark — PRODUCTION PATH (D2354 + S5/BUG-115 fix).

Two purposes:
  1. S5/BUG-115 — make the depth benchmark authoritative by running the PRODUCTION
     `classify_depth_focused()` path (call_omlx + `_parse_depth_token`), NOT the
     old direct `requests` path that drifted (87.5% governance claim vs 37.5/50%
     benchmark docstring).
  2. S3/D2354 — FrugalGPT cascade gate. Measure the cheap depth model
     (`stage4.depth_model`, default gemma-4-E4B-it-MLX-4bit) against the GPT-OSS
     focused-depth baseline. Enable `stage4.depth_frugal_enabled` ONLY if BOTH:
       * parity (agreement with GPT-OSS) >= 90%
       * held-out accuracy >= 90%
     and zero fail-open/silent failures.

SAFETY (D2243): served via OMLX API only. No direct requests bypass of the
pipeline's fail-closed call path.
"""
from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))  # allow `pipeline.*` imports from tools/
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
OUT_PATH = PROJECT_ROOT / "governance" / "s4_depth_frugal_benchmark.json"

DEPTH_ORDER = ["specialized", "domain", "cross-domain", "universal"]

PARITY_GATE = 0.90   # D2354: minimum agreement with GPT-OSS focused-depth
ACCURACY_GATE = 0.90  # D2354: minimum held-out accuracy on adjudicated depth set


def load_test_set() -> list[dict]:
    """Load FBs with depth labels from golden set (same as prior benchmarks)."""
    import yaml
    with open(GOLDEN_PATH) as f:
        d = yaml.safe_load(f)
    fbs = []
    for ex in d["examples"]:
        if not ex.get("should_extract"):
            continue
        fb = ex.get("expected_fb", {})
        if isinstance(fb, dict) and fb and fb.get("depth"):
            fbs.append({
                "name": fb.get("name", ""),
                "definition": fb.get("definition", ""),
                "mechanism": fb.get("mechanism", ""),
                "extraction_type": fb.get("extraction_type", ""),
                "gold_depth": fb["depth"],
                "golden_id": ex.get("id", "?"),
            })
    return fbs


def classify_production(fb: dict, model: str) -> tuple[str, float, str | None]:
    """Classify depth through the PRODUCTION path (fail-closed). Returns (pred, elapsed, error)."""
    from pipeline.stage4_merged_call import classify_depth_focused, DepthClassificationError
    t0 = time.time()
    try:
        pred = classify_depth_focused(fb, model=model, max_tokens=1024)
        return pred, time.time() - t0, None
    except DepthClassificationError as e:
        return "FAIL", time.time() - t0, f"DepthClassificationError: {e}"
    except Exception as e:
        return "FAIL", time.time() - t0, f"{type(e).__name__}: {e}"


def main() -> None:
    from pipeline.pipeline_paths import VERIFY_MODEL, S4_DEPTH_MODEL

    print("=" * 66)
    print("S4 FOCUSED-DEPTH BENCHMARK — PRODUCTION PATH (D2354 FrugalGPT gate)")
    print(f"GPT-OSS baseline : {VERIFY_MODEL}")
    print(f"Frugal candidate : {S4_DEPTH_MODEL}")
    print(f"Gate             : parity>={PARITY_GATE:.0%} AND accuracy>={ACCURACY_GATE:.0%}")
    print("=" * 66)

    test_fbs = load_test_set()
    print(f"\n📊 Golden set: {len(test_fbs)} FBs")
    depth_dist = Counter(fb["gold_depth"] for fb in test_fbs)
    for d in DEPTH_ORDER:
        print(f"   {d}: {depth_dist.get(d, 0)}")

    random.seed(42)
    stratified = {d: [] for d in DEPTH_ORDER}
    for fb in test_fbs:
        stratified[fb["gold_depth"]].append(fb)
    sampled = []
    for d in DEPTH_ORDER:
        n = min(len(stratified[d]), 3)
        sampled.extend(random.sample(stratified[d], n))
    random.shuffle(sampled)
    print(f"📊 Benchmark sample: {len(sampled)} FBs (stratified, seed=42)")

    results = []
    for i, fb in enumerate(sampled):
        gpt_pred, gpt_t, gpt_err = classify_production(fb, VERIFY_MODEL)
        frug_pred, frug_t, frug_err = classify_production(fb, S4_DEPTH_MODEL)
        results.append({
            "fb": fb["golden_id"],
            "gold": fb["gold_depth"],
            "gptoss": gpt_pred,
            "gptoss_err": gpt_err,
            "gptoss_t": round(gpt_t, 2),
            "frugal": frug_pred,
            "frugal_err": frug_err,
            "frugal_t": round(frug_t, 2),
        })
        agree = gpt_pred == frug_pred
        print(f"  {i+1:2d}/{len(sampled)} gold={fb['gold_depth']:15s} "
              f"gptoss={gpt_pred:15s} frugal={frug_pred:15s} "
              f"{'✅agree' if agree else '❌DIVERGE'} ({gpt_t:.1f}s vs {frug_t:.1f}s)")

    n = len(results)
    gpt_acc = sum(1 for r in results if r["gptoss"] == r["gold"]) / n if n else 0
    frug_acc = sum(1 for r in results if r["frugal"] == r["gold"]) / n if n else 0
    parity = sum(1 for r in results if r["gptoss"] == r["frugal"]) / n if n else 0
    gpt_failures = sum(1 for r in results if r["gptoss"] == "FAIL")
    frug_failures = sum(1 for r in results if r["frugal"] == "FAIL")
    gpt_avg_t = sum(r["gptoss_t"] for r in results) / n if n else 0
    frug_avg_t = sum(r["frugal_t"] for r in results) / n if n else 0

    print("\n" + "=" * 66)
    print("📊 RESULTS")
    print("=" * 66)
    print(f"  GPT-OSS  n={n:2d}  acc={gpt_acc:.1%}  failures={gpt_failures}  avg={gpt_avg_t:6.1f}s")
    print(f"  Frugal   n={n:2d}  acc={frug_acc:.1%}  failures={frug_failures}  avg={frug_avg_t:6.1f}s")
    print(f"  Parity   {parity:.1%}  (gate {PARITY_GATE:.0%})")
    speedup = gpt_avg_t / frug_avg_t if frug_avg_t else None
    if speedup:
        print(f"  Speedup  {speedup:.1f}×")

    gate_pass = (
        parity >= PARITY_GATE
        and frug_acc >= ACCURACY_GATE
        and frug_failures == 0
        and gpt_failures == 0
    )
    print(f"\n  🚦 GATE (parity≥{PARITY_GATE:.0%} + accuracy≥{ACCURACY_GATE:.0%} "
          f"+ 0 fail-open): {'✅ PASS — enable depth_frugal_enabled' if gate_pass else '❌ FAIL — keep GPT-OSS depth'}")

    out = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n": n,
        "gptoss_model": VERIFY_MODEL,
        "frugal_model": S4_DEPTH_MODEL,
        "gptoss_accuracy": gpt_acc,
        "frugal_accuracy": frug_acc,
        "parity": parity,
        "gptoss_failures": gpt_failures,
        "frugal_failures": frug_failures,
        "gptoss_avg_time_s": round(gpt_avg_t, 2),
        "frugal_avg_time_s": round(frug_avg_t, 2),
        "speedup_x": round(speedup, 1) if speedup else None,
        "gate": {
            "parity_min": PARITY_GATE,
            "accuracy_min": ACCURACY_GATE,
            "passed": gate_pass,
        },
        "results": results,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
