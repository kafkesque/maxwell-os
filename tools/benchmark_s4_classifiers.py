#!/usr/bin/env python3
"""
benchmark_s4_classifiers.py — Compare S4 classification accuracy across models.

Runs the S4 CRIBS classification on the same FBs using different models
and compares domain, depth, discipline, and evidence assignments.

Usage:
    python3 tools/benchmark_s4_classifiers.py \
        --models gpt-oss-20b-MXFP4-Q8,Qwen3.5-9B-4bit \
        --fbs 50

Authority: D2282 | CONSTITUTION.md R5 (Generator ≠ Verifier ≠ Classifier)
"""

import sys, json, time, os
from pathlib import Path
from collections import Counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.stage4_merged_call import merged_cribs_classify, batch_cribs_classify, BATCH_SIZE_DEFAULT


def load_fbs(checkpoint_path: str) -> list[dict]:
    """Load classified FBs from S4 checkpoint."""
    fbs = []
    with open(checkpoint_path) as f:
        for line in f:
            if line.strip():
                fbs.append(json.loads(line))
    return fbs


def strip_enrichment(fb: dict) -> dict:
    """Remove S4 enrichment fields so re-classification starts from raw FB."""
    enrichment_keys = {
        "domains", "domains_raw", "discipline", "discipline_raw",
        "depth", "is_specialized", "evidence", "context",
        "accessibility", "intimacy_boundary", "provenance",
        "keywords", "jargon", "application", "failure_mode",
        "elaboration", "route", "content_type",
    }
    clean = {}
    for k, v in fb.items():
        if k in enrichment_keys:
            continue
        clean[k] = v
    return clean


def classify_with_model(fbs: list[dict], model: str, batch: bool = True) -> list[dict]:
    """Classify FBs using a specific model. Returns enriched FBs."""
    results = []
    if batch and len(fbs) >= BATCH_SIZE_DEFAULT:
        print(f"   ⚡ Batch classifying {len(fbs)} FBs with {model} (batch_size={BATCH_SIZE_DEFAULT})...")
        for i in range(0, len(fbs), BATCH_SIZE_DEFAULT):
            batch_fbs = fbs[i:i + BATCH_SIZE_DEFAULT]
            batch_data = [strip_enrichment(fb) for fb in batch_fbs]
            batch_results = batch_cribs_classify(batch_data, model=model)
            for j, r in enumerate(batch_results):
                if r:
                    merged = {**fbs[i+j], **r}
                else:
                    merged = {**fbs[i+j]}
                merged["_classify_model"] = model
                results.append(merged)
            print(f"      Batch {i//BATCH_SIZE_DEFAULT + 1}: {len(batch_fbs)} FBs (total: {len(results)}/{len(fbs)})")
    else:
        print(f"   Single-call classifying {len(fbs)} FBs with {model}...")
        for i, fb in enumerate(fbs):
            clean = strip_enrichment(fb)
            enriched = merged_cribs_classify(clean, model=model)
            if enriched:
                merged = {**fb, **enriched}
            else:
                merged = {**fb}
            merged["_classify_model"] = model
            results.append(merged)
            if (i+1) % 10 == 0:
                print(f"      {i+1}/{len(fbs)}")
    return results


def compare_classifications(
    baseline_fbs: list[dict],
    candidate_fbs: list[dict],
    baseline_model: str = "baseline",
    candidate_model: str = "candidate",
) -> dict[str, Any]:
    """Compare two classification runs and return agreement stats."""
    assert len(baseline_fbs) == len(candidate_fbs), "Must have same FBs"

    # Field comparison
    fields = ["domains", "depth", "discipline", "evidence"]
    results: dict[str, Any] = {
        "baseline_model": baseline_model,
        "candidate_model": candidate_model,
        "total_fbs": len(baseline_fbs),
    }

    for field in fields:
        matches = 0
        mismatches = []
        for i, (b_fb, c_fb) in enumerate(zip(baseline_fbs, candidate_fbs)):
            b_val = b_fb.get(field)
            c_val = c_fb.get(field)

            # Normalize: sort lists, strip strings
            if isinstance(b_val, list):
                b_val = sorted([str(x).strip().lower() for x in b_val])
            elif isinstance(b_val, str):
                b_val = b_val.strip().lower()
            if isinstance(c_val, list):
                c_val = sorted([str(x).strip().lower() for x in c_val])
            elif isinstance(c_val, str):
                c_val = c_val.strip().lower()

            if b_val == c_val:
                matches += 1
            else:
                mismatches.append({
                    "fb_name": b_fb.get("name", f"FB-{i}"),
                    "baseline": b_val,
                    "candidate": c_val,
                })

        agree_pct = 100 * matches / len(baseline_fbs) if baseline_fbs else 0
        results[f"{field}_agree"] = matches
        results[f"{field}_disagree"] = len(mismatches)
        results[f"{field}_agree_pct"] = round(agree_pct, 1)
        if mismatches:
            results[f"{field}_mismatches"] = mismatches[:10]  # Show first 10

    # Overall agreement (all fields must match)
    all_match = 0
    for b_fb, c_fb in zip(baseline_fbs, candidate_fbs):
        match = True
        for field in fields:
            b_val = b_fb.get(field)
            c_val = c_fb.get(field)
            if isinstance(b_val, list):
                b_val = sorted([str(x).strip().lower() for x in b_val])
            elif isinstance(b_val, str):
                b_val = b_val.strip().lower()
            if isinstance(c_val, list):
                c_val = sorted([str(x).strip().lower() for x in c_val])
            elif isinstance(c_val, str):
                c_val = c_val.strip().lower()
            if b_val != c_val:
                match = False
                break
        if match:
            all_match += 1

    results["all_fields_agree"] = all_match
    results["all_fields_agree_pct"] = round(100 * all_match / len(baseline_fbs), 1)

    return results


def print_comparison(results: dict[str, Any]) -> None:
    """Pretty-print comparison results."""
    print(f"\n{'='*60}")
    print(f"📊 Classification Benchmark: {results['baseline_model']} vs {results['candidate_model']}")
    print(f"{'='*60}")
    print(f"   Total FBs: {results['total_fbs']}")
    print()
    for field in ["domains", "depth", "discipline", "evidence"]:
        agree = results.get(f"{field}_agree", 0)
        disagree = results.get(f"{field}_disagree", 0)
        pct = results.get(f"{field}_agree_pct", 0)
        bar = "█" * int(pct/5) + "░" * (20 - int(pct/5))
        print(f"   {field:<12} {agree}/{agree+disagree} agree ({pct:.1f}%)  {bar}")
        if disagree > 0 and f"{field}_mismatches" in results:
            for m in results[f"{field}_mismatches"][:3]:
                b_str = str(m['baseline'])[:40]
                c_str = str(m['candidate'])[:40]
                print(f"      ↳ {m['fb_name'][:30]}")
                print(f"         Baseline:  {b_str}")
                print(f"         Candidate: {c_str}")
    print()
    all_agree = results.get("all_fields_agree", 0)
    all_pct = results.get("all_fields_agree_pct", 0)
    bar = "█" * int(all_pct/5) + "░" * (20 - int(all_pct/5))
    print(f"   FULL MATCH  {all_agree}/{results['total_fbs']} ({all_pct:.1f}%)  {bar}")
    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark S4 classifiers across models")
    parser.add_argument("--models", default="gpt-oss-20b-MXFP4-Q8,Qwen3.5-9B-4bit",
                        help="Comma-separated model names to compare")
    parser.add_argument("--fbs", type=int, default=50,
                        help="Number of FBs to benchmark (default: 50)")
    parser.add_argument("--checkpoint",
                        default="knowledge pipeline/checkpoints/stage4_merge/diagnostic_20260811_232853/checkpoint.jsonl",
                        help="S4 checkpoint to load FBs from")
    parser.add_argument("--output", default=None,
                        help="Output JSON file for results")
    parser.add_argument("--batch", action="store_true", default=True,
                        help="Use batch classification (default: True)")
    parser.add_argument("--no-batch", action="store_false", dest="batch")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",")]
    if len(models) < 2:
        print("Need at least 2 models to compare")
        sys.exit(1)

    # Load FBs
    print(f"📂 Loading FBs from {args.checkpoint}")
    all_fbs = load_fbs(args.checkpoint)
    if args.fbs < len(all_fbs):
        import random
        random.seed(42)
        fbs = random.sample(all_fbs, args.fbs)
    else:
        fbs = all_fbs
    print(f"   Selected {len(fbs)} FBs for benchmark")

    # Classify with each model
    model_results: dict[str, list[dict]] = {}
    for model in models:
        print(f"\n🧠 Classifying with {model}...")
        t0 = time.time()
        # Strip enrichment from baseline too so it's a fair comparison
        clean_fbs = [strip_enrichment(fb) for fb in fbs]
        classified = classify_with_model(clean_fbs, model, batch=args.batch)
        elapsed = time.time() - t0
        print(f"   ✅ {len(classified)} FBs in {elapsed:.0f}s ({elapsed/len(classified):.1f}s/FB)")
        model_results[model] = classified

    # Compare each pair (first model = baseline)
    baseline_model = models[0]
    baseline_fbs = model_results[baseline_model]

    for candidate_model in models[1:]:
        candidate_fbs = model_results[candidate_model]
        results = compare_classifications(
            baseline_fbs,
            candidate_fbs,
            baseline_model=baseline_model,
            candidate_model=candidate_model,
        )
        print_comparison(results)

        if args.output:
            out_path = Path(args.output)
            with open(out_path, "w") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"📄 Results saved to {out_path}")

    # Speed comparison
    print(f"\n⏱️  Speed Comparison (batch_size={BATCH_SIZE_DEFAULT if args.batch else 1}):")
    for model in models:
        n = len(model_results[model])
        if n > 0:
            # Approximate speed from batch timing
            print(f"   {model}: {n} FBs classified")


if __name__ == "__main__":
    main()
