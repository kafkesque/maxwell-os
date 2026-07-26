#!/usr/bin/env python3
"""
evaluate_classification.py — Run 50 edge-case golden tests against any LLM.
================================================================================
Authority: D2066, P1.7

Evaluates classification accuracy across all 50 edge cases defined in
tests/golden_classification_edge_cases.yaml. Outputs per-case pass/fail
with detailed mismatch diagnostics.

Usage:
    # Test against OMLX Phi-4-mini (default classifier):
    python3 tests/evaluate_classification.py

    # Test with a different model:
    python3 tests/evaluate_classification.py --model gemma-4-E4B-it-MLX-4bit

    # Test with MLX backend:
    MAXWELL_INFERENCE_BACKEND=mlx python3 tests/evaluate_classification.py

    # Output JSON report:
    python3 tests/evaluate_classification.py --output report.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import VERIFY_MODEL
from pipeline.schemas import CANONICAL_DISCIPLINES, CANONICAL_DOMAINS, is_valid_discipline, is_valid_domain
from pipeline.stage4_merge import CLASSIFY_SYSTEM_PROMPT, build_classify_prompt


def load_golden_cases() -> list[dict]:
    """Load the 50 edge-case golden test cases."""
    yaml_path = PROJECT_ROOT / "tests" / "golden_classification_edge_cases.yaml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return data["golden_cases"]


def classify_fb(fb_name: str, fb_definition: str, model: str) -> dict:
    """Classify a single FB using the specified model."""
    prompt = build_classify_prompt(fb_name, fb_definition, CANONICAL_DOMAINS, CANONICAL_DISCIPLINES)
    return call_omlx_json(
        prompt=prompt,
        model=model,
        system=CLASSIFY_SYSTEM_PROMPT,
        max_tokens=256,
    )


def normalize_disciplines(raw) -> list[str]:
    """Normalize discipline output: string → [string], ensure list."""
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(d) for d in raw]
    return []


def match_disciplines(got: list[str], expected: list[str], accept_any: list[list[str]] | None) -> bool:
    """Check if got matches expected disciplines, with optional alternatives."""
    got_set = set(got)
    expected_set = set(expected)
    if got_set == expected_set:
        return True
    if accept_any:
        for alt in accept_any:
            if got_set == set(alt):
                return True
    return False


def match_depth(got: str, expected: str, accept_any: list[str] | None) -> bool:
    """Check depth match with optional alternatives."""
    if got == expected:
        return True
    if accept_any and got in accept_any:
        return True
    return False


def match_evidence(got: str, expected: str, accept_any: list[str] | None) -> bool:
    """Check evidence match with optional alternatives."""
    if got == expected:
        return True
    if accept_any and got in accept_any:
        return True
    return False


def evaluate_case(case: dict, model: str, case_idx: int) -> dict:
    """Evaluate one golden case against the classifier."""
    fb_name = case["fb_name"]
    fb_definition = case["fb_definition"]

    start = time.time()
    try:
        result = classify_fb(fb_name, fb_definition, model)
    except Exception as e:
        return {
            "case_id": case["id"],
            "case_idx": case_idx,
            "fb_name": fb_name,
            "passed": False,
            "error": str(e)[:300],
            "latency_s": round(time.time() - start, 2),
        }

    latency = round(time.time() - start, 2)

    got_disciplines = normalize_disciplines(result.get("disciplines", result.get("discipline", [])))
    got_domains = result.get("domains", [])
    # H04 fix: .get() returns None when key exists with null value, not the default.
    # Explicitly coalesce None → default for all nullable fields.
    got_depth = result.get("depth") or ""
    got_evidence = result.get("evidence") or ""

    expected_disciplines = case.get("expected_disciplines", [])
    expected_domains = case.get("expected_domains", [])
    expected_depth = case.get("expected_depth", "")
    expected_evidence = case.get("expected_evidence", "")

    checks = {}

    # Disciplines check
    accept_any_disc = case.get("accept_any_of_disciplines")
    checks["disciplines"] = match_disciplines(got_disciplines, expected_disciplines, accept_any_disc)

    # Domains check — tiered by cardinality (Claude review fix):
    # - 1-domain case: exact match required (no false breadth)
    # - 2-domain case: ≥2 overlap (at least both)
    # - 3+ domain case: ≥75% overlap (penalizes truncation for B03-style tests)
    # - emerging: exact match or empty
    if expected_domains == ["emerging"]:
        checks["domains"] = got_domains == ["emerging"] or len(got_domains) == 0
    else:
        overlap = set(got_domains) & set(expected_domains)
        if len(expected_domains) == 1:
            checks["domains"] = len(overlap) == 1 and len(got_domains) == 1
        elif len(expected_domains) == 2:
            checks["domains"] = len(overlap) >= 2
        else:
            checks["domains"] = len(overlap) >= max(2, int(len(expected_domains) * 0.75))

    # Depth check
    accept_any_depth = case.get("accept_any_of_depth")
    checks["depth"] = match_depth(got_depth, expected_depth, accept_any_depth)

    # Evidence check
    accept_any_evidence = case.get("accept_any_of_evidence")
    checks["evidence"] = match_evidence(got_evidence, expected_evidence, accept_any_evidence)

    all_passed = all(checks.values())

    # H02/H03: Production-path checks (Claude review — test real pipeline, not get() defaults)
    raw_domains = result.get("domains", [])
    has_duplicates = isinstance(raw_domains, list) and len(raw_domains) != len(set(str(d) for d in raw_domains))
    extra_keys = set(result.keys()) - {"disciplines", "discipline", "domains", "depth", "evidence"}

    return {
        "case_id": case["id"],
        "case_idx": case_idx,
        "fb_name": fb_name,
        "description": case.get("description", ""),
        "test_property": case.get("test_property", ""),
        "passed": all_passed,
        "checks": checks,
        "got": {
            "disciplines": got_disciplines,
            "domains": got_domains,
            "depth": got_depth,
            "evidence": got_evidence,
            "raw_has_duplicates": has_duplicates,
            "raw_extra_keys": list(extra_keys),
        },
        "expected": {
            "disciplines": expected_disciplines,
            "domains": expected_domains,
            "depth": expected_depth,
            "evidence": expected_evidence,
        },
        "latency_s": latency,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate classification against 50 edge cases")
    parser.add_argument("--model", default=VERIFY_MODEL, help=f"Model to test (default: {VERIFY_MODEL})")
    parser.add_argument("--output", help="Save report to JSON file")
    parser.add_argument("--cases", help="Comma-separated case IDs to run (default: all)")
    parser.add_argument("--verbose", action="store_true", help="Print per-case details")
    args = parser.parse_args()

    cases = load_golden_cases()
    if args.cases:
        case_ids = set(args.cases.split(","))
        cases = [c for c in cases if c["id"] in case_ids]

    print(f"🧪 Classification Edge-Case Evaluation")
    print(f"   Model: {args.model}")
    print(f"   Cases: {len(cases)}")
    print(f"{'='*70}\n")

    results = []
    passed = 0
    failed = 0
    errors = 0

    for i, case in enumerate(cases, 1):
        result = evaluate_case(case, args.model, i)
        results.append(result)

        if "error" in result:
            errors += 1
            icon = "💥"
        elif result["passed"]:
            passed += 1
            icon = "✅"
        else:
            failed += 1
            icon = "❌"

        if args.verbose or not result.get("passed", False):
            print(f"  {icon} [{i:2d}/{len(cases)}] {case['id']}: {case['fb_name'][:50]}")
            if "error" in result:
                print(f"       Error: {result['error']}")
            elif not result["passed"]:
                for check_name, check_ok in result["checks"].items():
                    if not check_ok:
                        got = result["got"][check_name]
                        expected = result["expected"][check_name]
                        print(f"       ❌ {check_name}: got={got} expected={expected}")
            print(f"       Property: {case.get('test_property', '?')}")
        else:
            print(f"  {icon} [{i:2d}/{len(cases)}] {case['id']} ({result['latency_s']:.1f}s)")

    # Summary
    total = len(cases)
    baseline_total = sum(1 for r in results if r.get("case_id", "").startswith("L"))
    baseline_passed = sum(1 for r in results if r.get("case_id", "").startswith("L") and r.get("passed", False))

    print(f"\n{'='*70}")
    print(f"📊 RESULTS: {passed} passed, {failed} failed, {errors} errors ({total} total)")
    if total > 0:
        rate = passed / total * 100
        print(f"   Pass rate: {rate:.1f}%")

    if baseline_total > 0:
        baseline_rate = baseline_passed / baseline_total * 100
        print(f"\n🔰 BASELINE (Group L): {baseline_passed}/{baseline_total} passed ({baseline_rate:.0f}%)")
        if baseline_passed < baseline_total:
            print(f"   🚨 CRITICAL: {baseline_total - baseline_passed} baseline cases FAILED!")
            print(f"   The classifier may be fundamentally broken. Fix before testing edge cases.")

    # Property-level breakdown
    property_results: dict[str, list[bool]] = {}
    for r in results:
        prop = r.get("test_property", "unknown")
        if prop not in property_results:
            property_results[prop] = []
        property_results[prop].append(r.get("passed", False))

    failures_by_property = {k: sum(1 for v in vals if not v) for k, vals in property_results.items() if sum(1 for v in vals if not v) > 0}
    if failures_by_property:
        print(f"\n🔴 FAILING PROPERTIES:")
        for prop, count in sorted(failures_by_property.items(), key=lambda x: -x[1]):
            print(f"   {prop}: {count} failures")

    # Check-level breakdown
    check_failures = {"disciplines": 0, "domains": 0, "depth": 0, "evidence": 0}
    for r in results:
        if "checks" in r:
            for check_name, ok in r["checks"].items():
                if not ok:
                    check_failures[check_name] += 1
    print(f"\n📊 FAILURES BY CHECK TYPE:")
    for check_name, count in check_failures.items():
        print(f"   {check_name}: {count}")

    if args.output:
        report = {
            "model": args.model,
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "pass_rate": round(passed / total * 100, 1) if total else 0,
            "results": results,
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📋 Report: {args.output}")


if __name__ == "__main__":
    main()
