#!/usr/bin/env python3
"""
S4 depth-classifier QUANT A/B — Q8 vs Q4 (and any other MLX quant) of gpt-oss-20b.

D2496-followup (2026-08-30): the one untried S4 speed lever is lower-bit quant of the
SAME model (memory-bandwidth-bound long-context classification can improve MAP@3/latency
at lower precision). This harness measures BOTH per-call latency AND golden depth accuracy
through the OMLX API, so the A/B is a real speed↔quality comparison, not a latency-only
wall-clock race.

Usage:
    python3 scripts/benchmark_s4_quant_ab.py --model gpt-oss-20b-MXFP4-Q8 --label Q8
    python3 scripts/benchmark_s4_quant_ab.py --model gpt-oss-20b-MXFP4-Q4 --label Q4

Model is C12-config-free here by design: the whole point is to compare quant VARIANTS that
the production config does not (yet) know about. The production model stays VERIFY_MODEL
(gpt-oss-20b-MXFP4-Q8) until/unless an A/B passes a golden gate.
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OMLX_URL = "http://localhost:11435/v1/chat/completions"
DEPTH_ORDER = ["specialized", "domain", "cross-domain", "universal"]

DEPTH_PROMPT = """Classify the DEPTH of this Foundation Block (a convergent principle from multiple books).

ONTOLOGY:
- specialized: Requires technical expertise in one narrow field. (e.g., optical kerning in typography)
- domain: Applies broadly within one discipline only. (e.g., price anchoring in behavioral economics)
- cross-domain: Same principle applies across multiple disciplines. (e.g., feedback loops in biology AND orgs)
- universal: A law of nature or mathematics — applies everywhere. (e.g., entropy, power laws)

FB:
Name: {name}
Definition: {definition}
Mechanism: {mechanism}
Type: {extraction_type}

Answer EXACTLY ONE WORD: specialized, domain, cross-domain, or universal. No reasoning."""


def load_test_set() -> list[dict]:
    """Load depth-labelled FBs from the convergent golden set (same source as D2245)."""
    import yaml
    with open(PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml") as f:
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


def classify_via_omlx(model: str, prompt: str, max_tokens: int = 512) -> tuple[str, float]:
    """Classify via OMLX API. Returns (prediction, elapsed_seconds)."""
    import requests
    from pipeline.pipeline_paths import OMLX_API_KEY
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    headers = {"Authorization": f"Bearer {OMLX_API_KEY}"}
    t0 = time.time()
    try:
        resp = requests.post(OMLX_URL, json=payload, headers=headers, timeout=300)
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        elapsed = time.time() - t0
        content = msg.get("content", "").strip().lower()
        reasoning = msg.get("reasoning_content", "").strip().lower()
        if not content and reasoning:
            content = reasoning.split()[-1] if reasoning.split() else ""
        return content, elapsed
    except Exception as e:
        return f"ERROR: {e}", time.time() - t0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--n", type=int, default=None,
                        help="sample size (default: all golden FBs)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--warmup", action="store_true",
                        help="issue one throwaway call first (absorbs cold model load)")
    args = parser.parse_args()
    label = args.label or args.model

    test_fbs = load_test_set()
    random.seed(args.seed)
    if args.n:
        test_fbs = random.sample(test_fbs, min(args.n, len(test_fbs)))

    print("=" * 66)
    print(f"S4 DEPTH CLASSIFIER QUANT A/B — {label} ({args.model})")
    print(f"golden sample: {len(test_fbs)} FBs (seed={args.seed})")
    print("=" * 66)

    if args.warmup and test_fbs:
        print("warmup (absorbing cold model load) ...")
        t0 = time.time()
        classify_via_omlx(args.model, DEPTH_PROMPT.format(**test_fbs[0]))
        print(f"  warmup {time.time() - t0:.1f}s (discarded)")

    times: list[float] = []
    correct = 0
    for fb in test_fbs:
        pred, dt = classify_via_omlx(args.model, DEPTH_PROMPT.format(**fb))
        times.append(dt)
        is_correct = pred.strip() == fb["gold_depth"]
        correct += int(is_correct)
        print(f"  {fb['golden_id']:<10} {dt:6.2f}s  gold={fb['gold_depth']:<12} "
              f"pred={pred:<12} {'✓' if is_correct else '✗'}")

    print("=" * 66)
    if times:
        acc = correct / len(times)
        print(f"median {statistics.median(times):.2f}s/call   mean {statistics.mean(times):.2f}s/call "
              f"   min {min(times):.2f}s  max {max(times):.2f}s")
        print(f"ACCURACY: {correct}/{len(times)} = {acc:.1%}")
        print(f"throughput: {60 / statistics.median(times):.2f} FBs/min (median)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
