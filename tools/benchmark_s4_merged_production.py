#!/usr/bin/env python3
"""Measure merged_cribs_classify() per-FB latency — the REAL production S4 path.

D2362 next-action #1: production runs the individual merged_cribs_classify()
path (stage4.batch_enabled=false), whose per-FB cost was UNMEASURED in any
committed artifact. Closes that gap by timing the production call on a
stratified golden sample. C12: model comes from config (VERIFY_MODEL); sample
size / extrapolation target are CLI args (no hardcoded totals).
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DEPTH_ORDER = ["specialized", "domain", "cross-domain", "universal"]


def load_test_set() -> list[dict]:
    """Load depth-labelled FBs from the golden set (same source as prior benchmarks)."""
    import yaml
    from pipeline.pipeline_paths import S2_GOLDEN_PATH
    with open(PROJECT_ROOT / S2_GOLDEN_PATH) as f:
        d = yaml.safe_load(f)
    fbs = []
    for ex in d["examples"]:
        if not ex.get("should_extract"):
            continue
        fb = ex.get("expected_fb", {})
        if isinstance(fb, dict) and fb and fb.get("depth"):
            fb["_golden_id"] = ex.get("id", "?")
            fb["_gold_depth"] = fb.get("depth")
            fbs.append(fb)
    return fbs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=8, help="sample size (stratified)")
    parser.add_argument("--total-fbs", type=int, default=None,
                        help="optional: extrapolate to N FBs (e.g. 12964)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--warmup", action="store_true",
                        help="issue one throwaway call first (absorbs cold model load)")
    args = parser.parse_args()

    from pipeline.pipeline_paths import VERIFY_MODEL
    from pipeline.stage4_merged_call import merged_cribs_classify

    test_fbs = load_test_set()
    random.seed(args.seed)
    stratified = {d: [] for d in DEPTH_ORDER}
    for fb in test_fbs:
        stratified[fb["_gold_depth"]].append(fb)
    sampled: list[dict] = []
    for d in DEPTH_ORDER:
        n = min(len(stratified[d]), max(1, args.n // 4))
        sampled.extend(random.sample(stratified[d], n))
    random.shuffle(sampled)

    print("S4 merged_cribs_classify() — production-path benchmark (D2362)")
    print(f"model   : {VERIFY_MODEL}")
    print(f"sample  : {len(sampled)} FBs (stratified, seed={args.seed})")
    print("=" * 66)

    if args.warmup and sampled:
        print("warmup call (absorbing cold load) ...")
        t0 = time.time()
        try:
            merged_cribs_classify(sampled[0])
        except Exception as e:
            print(f"  warmup error: {type(e).__name__}: {e}")
        print(f"  warmup took {time.time() - t0:.1f}s (discarded)")

    times: list[float] = []
    for fb in sampled:
        t0 = time.time()
        err = None
        try:
            merged_cribs_classify(fb)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        dt = time.time() - t0
        times.append(dt)
        print(f"  {fb['_golden_id']:<10} {dt:6.2f}s  gold={fb['_gold_depth']:<12}"
              f"{'  ERR ' + err if err else ''}")

    print("=" * 66)
    if times:
        median = statistics.median(times)
        mean = statistics.mean(times)
        print(f"median {median:.2f}s/FB   mean {mean:.2f}s/FB   "
              f"min {min(times):.2f}s  max {max(times):.2f}s")
        print(f"throughput: {60 / median:.2f} FBs/min (median)")
        if args.total_fbs:
            print(f"extrapolated: {args.total_fbs} FBs * {median:.2f}s = "
                  f"{args.total_fbs * median / 3600:.1f}h (median)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
