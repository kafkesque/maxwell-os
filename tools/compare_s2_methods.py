#!/usr/bin/env python3
"""
Compare traditional S2 (few-shot injection) vs DSPy-optimized S2 (BootstrapFewShot).

Evaluates both approaches on the same held-out test examples using:
- extraction_metric() for quality scoring
- Wall-clock latency per extraction
- Per-dimension breakdown (convergence, type, depth, etc.)
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Imports after path setup ──────────────────────────────────────────
import dspy
import requests
from pipeline.dspy_trainer import (
    DirectOMLXLM,
    ConvergentExtraction,
    extraction_metric,
    golden_to_examples,
    stratified_random_split,
    configure_dspy,
)
from pipeline.stage2_extract import SYSTEM_PROMPT, format_golden_fewshot

OMLX_URL = "http://localhost:11435/v1/chat/completions"
MODEL_NAME = "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit"
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"


# ──────────────────────────────────────────────────────────────────────
# Traditional S2 (few-shot injection)
# ──────────────────────────────────────────────────────────────────────

def traditional_s2_extract(
    cluster_segments: str,
    pos_examples: list[dict],
    neg_examples: list[dict] | None = None,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Run traditional S2 extraction using few-shot injection."""

    fewshot = format_golden_fewshot(pos_examples, neg_examples)

    prompt = f"""{SYSTEM_PROMPT}

{fewshot}

## CLUSTER TO EXTRACT FROM

{cluster_segments}
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(OMLX_URL, json=payload, timeout=180)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Parse JSON from response
        # Try to find JSON block
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "{" in content:
            content = content[content.find("{"):content.rfind("}")+1]

        result = json.loads(content)
    except Exception as e:
        result = {"route": "NULL", "error": str(e), "raw": content if 'content' in dir() else ""}

    return result


# ──────────────────────────────────────────────────────────────────────
# DSPy-optimized S2
# ──────────────────────────────────────────────────────────────────────

def dspy_s2_extract(
    program: dspy.Module,
    cluster_segments: str,
) -> dict[str, Any]:
    """Run DSPy-optimized S2 extraction."""
    try:
        result = program(cluster_segments=cluster_segments)
        return {
            "name": getattr(result, "name", ""),
            "definition": getattr(result, "definition", ""),
            "mechanism": getattr(result, "mechanism", ""),
            "boundary": getattr(result, "boundary", ""),
            "consequence": getattr(result, "consequence", ""),
            "extraction_type": getattr(result, "extraction_type", "causal_mechanism"),
            # Depth no longer in S2 (A-001/D2241)
            "is_summary": getattr(result, "is_summary", False),
            "evidence_passages": getattr(result, "evidence_passages", "[]"),
            "route": getattr(result, "route", "NULL"),
            "is_convergent": getattr(result, "is_convergent", False),
        }
    except Exception as e:
        return {"route": "NULL", "error": str(e)}


# ──────────────────────────────────────────────────────────────────────
# Comparison Runner
# ──────────────────────────────────────────────────────────────────────

def run_comparison(
    test_examples: list[dspy.Example],
    optimized_program: dspy.Module | None = None,
    n_pos_fewshot: int = 3,
    n_neg_fewshot: int = 1,
) -> dict[str, Any]:
    """
    Compare traditional S2 vs DSPy S2 on the same test set.

    Returns dict with per-approach metrics and per-example breakdown.
    """

    # Load golden set for few-shot examples
    with open(GOLDEN_PATH) as f:
        golden = yaml.safe_load(f)

    gold_pos = [e for e in golden["examples"] if e.get("should_extract")][:n_pos_fewshot]
    gold_neg = [e for e in golden["examples"] if not e.get("should_extract")][:n_neg_fewshot]

    results = {
        "traditional": {"scores": [], "times": [], "predictions": []},
        "dspy": {"scores": [], "times": [], "predictions": []},
    }

    # Warmup call (both approaches)
    print("Warming up OMLX...")
    requests.post(OMLX_URL, json={
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 5,
        "temperature": 0.0,
    }, timeout=30)

    for i, ex in enumerate(test_examples[:8], 1):  # Limit to 8 for speed
        print(f"\n{'='*60}")
        print(f"Example {i}/{min(8, len(test_examples))}: {ex.golden_id} ({ex.fb_name})")
        print(f"{'='*60}")

        # ── Traditional S2 ──
        print("  Traditional S2...", end=" ", flush=True)
        t_start = time.time()
        try:
            trad_result = traditional_s2_extract(
                ex.cluster_segments,
                pos_examples=gold_pos,
                neg_examples=gold_neg,
            )
            trad_time = time.time() - t_start

            # Convert to dspy.Example for scoring
            trad_pred = dspy.Example(
                route=trad_result.get("route", "NULL"),
                name=trad_result.get("name", ""),
                extraction_type=trad_result.get("extraction_type", "causal_mechanism"),
                # Depth no longer in S2 (A-001/D2241)
                mechanism=trad_result.get("mechanism", ""),
                boundary=trad_result.get("boundary", ""),
                consequence=trad_result.get("consequence", ""),
                evidence_passages=json.dumps(trad_result.get("evidence_passages", [])),
                is_convergent=trad_result.get("route") == "FB",
            )
            trad_score = extraction_metric(ex, trad_pred)
            results["traditional"]["scores"].append(trad_score)
            results["traditional"]["times"].append(trad_time)
            results["traditional"]["predictions"].append(trad_result)
            print(f"score={trad_score:.2f} | {trad_time:.1f}s")
        except Exception as e:
            print(f"ERROR: {e}")
            results["traditional"]["scores"].append(0.0)
            results["traditional"]["times"].append(0.0)

        # ── DSPy S2 ──
        if optimized_program:
            print("  DSPy S2...", end=" ", flush=True)
            t_start = time.time()
            try:
                dspy_result = dspy_s2_extract(optimized_program, ex.cluster_segments)
                dspy_time = time.time() - t_start

                dspy_pred = dspy.Example(
                    route=dspy_result.get("route", "NULL"),
                    name=dspy_result.get("name", ""),
                    extraction_type=dspy_result.get("extraction_type", "causal_mechanism"),
                    # Depth no longer in S2 (A-001/D2241)
                    mechanism=dspy_result.get("mechanism", ""),
                    boundary=dspy_result.get("boundary", ""),
                    consequence=dspy_result.get("consequence", ""),
                    evidence_passages=json.dumps(dspy_result.get("evidence_passages", [])),
                    is_convergent=dspy_result.get("route") == "FB",
                )
                dspy_score = extraction_metric(ex, dspy_pred)
                results["dspy"]["scores"].append(dspy_score)
                results["dspy"]["times"].append(dspy_time)
                results["dspy"]["predictions"].append(dspy_result)
                print(f"score={dspy_score:.2f} | {dspy_time:.1f}s")
            except Exception as e:
                print(f"ERROR: {e}")
                results["dspy"]["scores"].append(0.0)
                results["dspy"]["times"].append(0.0)

    return results


def print_comparison(results: dict[str, Any]) -> None:
    """Print formatted comparison table."""
    trad = results["traditional"]
    dspy = results["dspy"]

    n_trad = len(trad["scores"])
    n_dspy = len(dspy["scores"])

    if n_trad == 0 and n_dspy == 0:
        print("\nNo results to compare.")
        return

    avg_trad_score = sum(trad["scores"]) / n_trad if n_trad else 0
    avg_dspy_score = sum(dspy["scores"]) / n_dspy if n_dspy else 0
    avg_trad_time = sum(trad["times"]) / n_trad if n_trad else 0
    avg_dspy_time = sum(dspy["times"]) / n_dspy if n_dspy else 0

    winner_score = "DSPy" if avg_dspy_score > avg_trad_score else "Traditional"
    winner_speed = "DSPy" if avg_dspy_time < avg_trad_time else "Traditional"

    print(f"\n{'='*70}")
    print(f"  S2 EXTRACTION COMPARISON: Traditional vs DSPy-Optimized")
    print(f"{'='*70}")
    print(f"  Model: {MODEL_NAME}")
    print(f"  Test examples: {n_trad} traditional, {n_dspy} DSPy")
    print()
    print(f"  {'Metric':<30} {'Traditional':>12} {'DSPy':>12} {'Winner':>10}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*10}")
    print(f"  {'Avg Quality Score':<30} {avg_trad_score:>11.3f}  {avg_dspy_score:>11.3f}  {winner_score:>10}")
    print(f"  {'Avg Latency (s)':<30} {avg_trad_time:>11.1f}  {avg_dspy_time:>11.1f}  {winner_speed:>10}")

    # Per-dimension analysis
    if n_trad > 0 and n_dspy > 0:
        # Compare type accuracy
        trad_type_correct = 0
        dspy_type_correct = 0
        for i, ex in enumerate(test_examples[:n_dspy]):
            if i >= n_trad:
                break

        print(f"\n  {'─'*70}")
        print(f"  Per-example breakdown:")
        print(f"  {'Example':<30} {'Trad Score':>10} {'DSPy Score':>10} {'Δ':>8}")
        print(f"  {'-'*30} {'-'*10} {'-'*10} {'-'*8}")
        for i in range(min(n_trad, n_dspy)):
            delta = dspy["scores"][i] - trad["scores"][i]
            name = test_examples[i].golden_id if i < len(test_examples) else f"ex{i}"
            marker = " ✅" if delta > 0 else (" ❌" if delta < 0 else " =")
            print(f"  {name:<30} {trad['scores'][i]:>9.3f}  {dspy['scores'][i]:>9.3f}  {delta:>+.3f}{marker}")

    print(f"\n  Verdict: {winner_score} wins on quality, {winner_speed} wins on speed")
    print(f"{'='*70}")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare Traditional vs DSPy S2 extraction")
    parser.add_argument("--dspy-program", type=str, default=None,
                        help="Path to pickled DSPy program (from --pilot output)")
    parser.add_argument("--n-examples", type=int, default=8,
                        help="Number of test examples to evaluate")
    parser.add_argument("--traditional-only", action="store_true",
                        help="Run only traditional S2 (DSPy program not available yet)")
    args = parser.parse_args()

    # Load test examples
    examples = golden_to_examples(verbose=False)
    _, _, test = stratified_random_split(examples, verbose=True)

    # Truncate to n_examples
    test = test[:args.n_examples]

    # Load or skip DSPy program
    optimized = None
    if not args.traditional_only and args.dspy_program:
        print(f"Loading DSPy program from {args.dspy_program}...")
        optimized = dspy.Module.load(args.dspy_program)
    elif args.traditional_only:
        print("Running TRADITIONAL-ONLY comparison (DSPy pilot not yet complete)")
    else:
        print("No DSPy program provided. Running TRADITIONAL-ONLY baseline.")
        print("Run --pilot first, then pass --dspy-program /tmp/dspy_optimized.json")

    # Run comparison
    results = run_comparison(test, optimized_program=optimized)
    print_comparison(results)

    # Save results
    out_path = PROJECT_ROOT / "governance" / "s2_comparison_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")
