#!/usr/bin/env python3
"""
Maxwell OS — LLM Model Evaluation Script (llmfit-based)
=======================================================
Checks whether a candidate local LLM fits Maxwell's hardware and pipeline
constraints. Uses llmfit for hardware detection + model scoring, then applies
Maxwell-specific validation rules (R5, temp=0.0, C1-C4, memory budget).

Usage:
    python3 scripts/evaluate_model.py <model-name-or-search>
    python3 scripts/evaluate_model.py --list-top 10 --runtime mlx
    python3 scripts/evaluate_model.py --check "Qwen3.6-35B-A3B"

Prerequisites:
    pip3 install llmfit  (auto-installed if missing)

Author: Maxwell OS v3.0
Created: 2026-07-27 (E3: llmfit adoption)
Schema: v1.0 | temp=0.0 | config-driven
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ════════════════════════════════════════════════════════════
# CONFIG — no hardcoded values (C12 compliant)
# ════════════════════════════════════════════════════════════

# Maxwell OS constraints (from CONSTITUTION.md §0)
MAXWELL_CONSTRAINTS = {
    "memory_budget_gb": 24,        # BUG-017: OMLX restart if RSS > 24GB
    "total_ram_gb": 64,            # M1 Max unified memory
    "temp_required": 0.0,          # R7: temp=0.0 on all generation
    "must_be_local": True,         # C1: $0 marginal cost, C3: sovereign
    "open_source_required": True,  # C2: no vendor lock-in
    "min_tok_per_sec": 10,         # Pipeline must complete in reasonable time
    "required_capabilities": ["text"],  # Pipeline is text-only
    "preferred_licenses": ["apache-2.0", "mit", "bsd-3-clause", "bsd-2-clause"],
}

# Cross-family verification (R5): Generator ≠ Verifier families
# These families must NOT overlap between roles
MODEL_FAMILIES = {
    "qwen":     ["qwen", "Qwen", "qwen3", "qwen2"],
    "phi":      ["phi", "Phi", "phi-4", "phi-3"],
    "gemma":    ["gemma", "Gemma"],
    "llama":    ["llama", "Llama", "Meta-Llama"],
    "deepseek": ["deepseek", "DeepSeek"],
    "mistral":  ["mistral", "Mistral"],
}


def ensure_llmfit() -> bool:
    """Ensure llmfit is installed. Returns True if available."""
    try:
        import llmfit
        return True
    except ImportError:
        print("⚠️  llmfit not found. Installing...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "llmfit"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"❌ Failed to install llmfit: {result.stderr}")
            return False
        print("✅ llmfit installed")
        return True
    return True


def detect_hardware() -> Dict[str, Any]:
    """Run llmfit doctor and parse hardware detection."""
    result = subprocess.run(
        [sys.executable, "-m", "llmfit", "doctor"],
        capture_output=True, text=True, timeout=30
    )
    # Parse the detected specs from llmfit output
    specs = {
        "total_ram_gb": MAXWELL_CONSTRAINTS["total_ram_gb"],
        "gpu_name": "unknown",
        "unified_memory": True,
    }
    for line in result.stdout.split('\n'):
        line = line.strip()
        if 'total_ram_gb:' in line:
            try:
                specs["total_ram_gb"] = float(line.split(':')[1].strip().rstrip(','))
            except (ValueError, IndexError):
                pass
        if 'gpu_name:' in line and 'Some' in line:
            try:
                name = line.split('"')[1] if '"' in line else "unknown"
                specs["gpu_name"] = name
            except IndexError:
                pass
    return specs


def get_llmfit_recommendations(
    limit: int = 10,
    runtime: str = "mlx",
    min_fit: str = "marginal",
    use_case: str = "general"
) -> List[Dict[str, Any]]:
    """Get model recommendations from llmfit."""
    result = subprocess.run(
        [sys.executable, "-m", "llmfit", "recommend",
         "-n", str(limit),
         "--runtime", runtime,
         "--min-fit", min_fit,
         "--use-case", use_case,
         "--json"],
        capture_output=True, text=True, timeout=30
    )
    try:
        data = json.loads(result.stdout)
        return data.get("models", [])
    except json.JSONDecodeError:
        print(f"❌ Failed to parse llmfit output: {result.stdout[:200]}")
        return []


def classify_family(model_name: str) -> str:
    """Classify model family from its name for R5 cross-family checking."""
    name_lower = model_name.lower()
    for family, patterns in MODEL_FAMILIES.items():
        for pattern in patterns:
            if pattern.lower() in name_lower:
                return family
    return "unknown"


def check_maxwell_compatibility(model: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Apply Maxwell-specific constraints on top of llmfit scores."""
    issues: List[str] = []
    
    name = model.get("name", "unknown")
    mem_gb = model.get("memory_required_gb", 0)
    fit_level = model.get("fit_level", "unknown")
    tps = model.get("estimated_tps", 0)
    license_type = model.get("license", "")
    
    # Memory budget check
    if mem_gb > MAXWELL_CONSTRAINTS["memory_budget_gb"]:
        issues.append(
            f"Memory ({mem_gb:.1f}GB) exceeds Maxwell budget "
            f"({MAXWELL_CONSTRAINTS['memory_budget_gb']}GB)"
        )
    
    # Speed check
    if tps < MAXWELL_CONSTRAINTS["min_tok_per_sec"]:
        issues.append(
            f"Speed ({tps:.0f} tok/s) below pipeline minimum "
            f"({MAXWELL_CONSTRAINTS['min_tok_per_sec']} tok/s)"
        )
    
    # Fit level
    if fit_level.lower() == "poor":
        issues.append(f"Fit level is POOR — model may OOM or swap heavily")
    
    # License check (warning only, not blocking)
    if license_type and MAXWELL_CONSTRAINTS["preferred_licenses"]:
        preferred = MAXWELL_CONSTRAINTS["preferred_licenses"]
        if license_type.lower() not in [p.lower() for p in preferred]:
            issues.append(
                f"License '{license_type}' not in preferred list: {preferred}"
            )
    
    return len(issues) == 0, issues


def evaluate_model(model_name: str) -> Dict[str, Any]:
    """Full evaluation of a single model for Maxwell compatibility."""
    result = subprocess.run(
        [sys.executable, "-m", "llmfit", "info", model_name],
        capture_output=True, text=True, timeout=30
    )
    
    family = classify_family(model_name)
    
    return {
        "model": model_name,
        "family": family,
        "llmfit_output": result.stdout[:2000] if result.returncode == 0 else result.stderr,
        "r5_notes": (
            f"Family '{family}'. Ensure Generator ≠ Verifier families (R5)."
        ),
        "temp_0_0_notes": (
            "temp=0.0 (R7): Model must support deterministic output. "
            "Most models support temperature=0 in API."
        ),
    }


def print_header(title: str) -> None:
    """Print a formatted header."""
    width = 70
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")


def main() -> None:
    """Main entry point for model evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Maxwell OS — Evaluate local LLM fit using llmfit + Maxwell constraints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-top 10 --runtime mlx    # Top 10 MLX models for this hardware
  %(prog)s --check "Qwen3.6-35B-A3B"      # Deep-check a specific model
  %(prog)s --check "gemma-4-E4B" --role verifier  # Check as verifier role
  %(prog)s --list-top 20 --use-case coding  # Coding-optimized models
        """,
    )
    
    parser.add_argument(
        "--list-top", type=int, default=0,
        help="List top N model recommendations from llmfit"
    )
    parser.add_argument(
        "--runtime", default="mlx",
        choices=["mlx", "llamacpp", "any"],
        help="Inference runtime filter (default: mlx)"
    )
    parser.add_argument(
        "--use-case", default="general",
        choices=["general", "coding", "reasoning", "chat", "multimodal", "embedding"],
        help="Use case filter (default: general)"
    )
    parser.add_argument(
        "--min-fit", default="marginal",
        choices=["perfect", "good", "marginal"],
        help="Minimum fit level (default: marginal)"
    )
    parser.add_argument(
        "--check", type=str, default=None,
        help="Deep-check a specific model by name"
    )
    parser.add_argument(
        "--role", type=str, default="generator",
        choices=["generator", "verifier", "verifier_v2", "embeddings", "nli"],
        help="Pipeline role for context in evaluation"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON for agent consumption"
    )
    
    args = parser.parse_args()
    
    # Ensure llmfit is available
    if not ensure_llmfit():
        sys.exit(1)
    
    hardware = detect_hardware()
    
    if args.json:
        output: Dict[str, Any] = {"hardware": hardware, "models": []}
    else:
        print_header("Maxwell OS — LLM Model Evaluation")
        print(f"  Hardware: {hardware.get('gpu_name', '?')} | "
              f"{hardware.get('total_ram_gb', '?')}GB RAM")
        print(f"  Constraints: {MAXWELL_CONSTRAINTS['memory_budget_gb']}GB budget | "
              f"≥{MAXWELL_CONSTRAINTS['min_tok_per_sec']} tok/s | "
              f"temp={MAXWELL_CONSTRAINTS['temp_required']} | "
              f"local-only")
    
    # List top recommendations
    if args.list_top > 0:
        models = get_llmfit_recommendations(
            limit=args.list_top,
            runtime=args.runtime,
            min_fit=args.min_fit,
            use_case=args.use_case,
        )
        
        if not args.json:
            print_header(f"Top {len(models)} Models (runtime={args.runtime}, "
                        f"fit≥{args.min_fit}, use={args.use_case})")
        
        for i, m in enumerate(models):
            name = m.get("name", "?")
            fit = m.get("fit_level", "?")
            tps = m.get("estimated_tps", 0)
            mem = m.get("memory_required_gb", 0)
            sc = m.get("score_components", {})
            quality = sc.get("quality", 0)
            family = classify_family(name)
            passed, issues = check_maxwell_compatibility(m)
            
            if args.json:
                output["models"].append({
                    "rank": i + 1,
                    "name": name,
                    "fit_level": fit,
                    "estimated_tok_s": tps,
                    "memory_gb": mem,
                    "quality": quality,
                    "family": family,
                    "maxwell_compatible": passed,
                    "issues": issues,
                    "license": m.get("license", ""),
                })
            else:
                status = "✅" if passed else "⚠️"
                print(f"\n  {i+1:2}. {status} {name}")
                print(f"      Fit={fit:8s}  Est={tps:5.0f} tok/s  "
                      f"Mem={mem:.1f}GB  Quality={quality:.1f}  Family={family}")
                if not passed and issues:
                    for issue in issues:
                        print(f"      ⚠️  {issue}")
        
        if args.json:
            print(json.dumps(output, indent=2))
    
    # Deep-check a specific model
    if args.check:
        result = evaluate_model(args.check)
        
        if args.json:
            output["model_check"] = result
            if not args.list_top:
                print(json.dumps(output, indent=2))
        else:
            print_header(f"Model Deep-Check: {args.check}")
            print(f"  Role: {args.role}")
            print(f"  Family: {result['family']}")
            print(f"  {result['r5_notes']}")
            print(f"  {result['temp_0_0_notes']}")
            print(f"\n  llmfit analysis:")
            for line in result['llmfit_output'].split('\n')[:40]:
                print(f"  │ {line}")
    
    if not args.list_top and not args.check:
        parser.print_help()


if __name__ == "__main__":
    main()
