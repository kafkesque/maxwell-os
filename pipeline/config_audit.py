#!/usr/bin/env python3
"""
config_audit.py — Detect config-code drift before production runs.
==================================================================
D2183: Blindness remediation — compares pipeline_config.yaml values
against module-level hardcoded constants in pipeline/*.py.

Why this exists:
  D2176 lowered split_probe_min_size from 50 → 20 in CODE but not CONFIG.
  The drift was invisible for 3 audit rounds because both values look valid.
  grep-only audits miss integer mismatches. This script catches them.

Usage:
  python3 pipeline/config_audit.py           # Full audit, exit 1 on drift
  python3 pipeline/config_audit.py --fix     # Suggest config updates
  python3 pipeline/config_audit.py --json    # Machine-readable output
  just audit                                 # Wire into preflight

Architecture:
  Maps config keys → module constants via a declarative registry.
  New hardcoded values must be registered here OR moved to YAML.
"""
import argparse
import json
import sys
from pathlib import Path

# ── Registry: config_path → (module, attr_name, type) ───────────────
# Format: "stage.section.key": ("pipeline/module.py", "CONSTANT_NAME", "type")
# Add entries here whenever a new config key is added to pipeline_config.yaml.
# This is the SINGLE ENFORCEMENT POINT — every configurable value must be registered.
CONFIG_TO_CODE: dict[str, tuple[str, str, str]] = {
    # ── Stage 2 (extraction, T0.1) ──
    "stage2.split_probe_enabled":              ("pipeline.stage2_extract", "SPLIT_PROBE_ENABLED", "bool"),
    "stage2.split_probe_min_size":             ("pipeline.stage2_extract", "SPLIT_PROBE_MIN_SIZE", "int"),
    "stage2.split_probe_max_cohesion":         ("pipeline.stage2_extract", "SPLIT_PROBE_MAX_COHESION", "float"),
    "stage2.max_cluster_samples":              ("pipeline.stage2_extract", "MAX_CLUSTER_SAMPLES", "int"),
    "stage2.max_probe_samples":                ("pipeline.stage2_extract", "S2_MAX_PROBE_SAMPLES", "int"),
    "stage2.split_probe_kmeans_random_state":  ("pipeline.stage2_extract", "SPLIT_KMEANS_RANDOM_STATE", "int"),
    # ── Stage 1.5 (embedding) ──
    "stage1_5.embed_model_hf":     ("pipeline.pipeline_paths", "S15_EMBED_MODEL_HF", "str"),
    "stage1_5.embed_dim":          ("pipeline.pipeline_paths", "S15_EMBED_DIM", "int"),
    "stage1_5.embed_backend":      ("pipeline.pipeline_paths", "S15_EMBED_BACKEND", "str"),
    "stage1_5.faiss_threshold":    ("pipeline.pipeline_paths", "S15_FAISS_THRESHOLD", "float"),
    "stage1_5.min_source_diversity": ("pipeline.pipeline_paths", "S15_MIN_SOURCE_DIVERSITY", "int"),
    "stage1_5.neighbor_k":         ("pipeline.pipeline_paths", "S15_NEIGHBOR_K", "int"),
    # ── Stage 5 (verify) ──
    "stage5.nli_model":                 ("pipeline.pipeline_paths", "S5_NLI_MODEL", "str"),
    "stage5.nli_entailment_threshold":  ("pipeline.pipeline_paths", "S5_NLI_ENTAILMENT_THRESHOLD", "float"),
    "stage5.nli_pass_threshold":        ("pipeline.pipeline_paths", "S5_NLI_PASS_THRESHOLD", "float"),
    "stage5.nli_marginal_threshold":    ("pipeline.pipeline_paths", "S5_NLI_MARGINAL_THRESHOLD", "float"),
    # ── Models ──
    "models.embeddings.model":          ("pipeline.pipeline_paths", "EMBED_MODEL", "str"),
    # ── Services (T0.2, T0.4) ──
    "services.omlx.default_timeout":    ("pipeline.omlx_call", "DEFAULT_TIMEOUT", "int"),
    "services.omlx.max_retries":        ("pipeline.omlx_call", "MAX_RETRIES", "int"),
    "services.omlx.retry_delay":        ("pipeline.omlx_call", "RETRY_DELAY", "int"),
    "services.ollama.nomic_max_chars":  ("pipeline.ollama_embed", "NOMIC_MAX_CHARS", "int"),
    "services.ollama.batch_size":       ("pipeline.ollama_embed", "BATCH_SIZE", "int"),
    # ── Coverage (T0.3) ──
    "coverage.threshold":               ("pipeline.coverage_check", "COVERAGE_THRESHOLD", "float"),
    "coverage.flag_fraction":           ("pipeline.coverage_check", "COVERAGE_FLAG_FRACTION", "float"),
    # ── Pipeline tuning (T1.1, T1.2) ──
    "pipeline.min_chunk_words":             ("pipeline.stage1_chunk", "MIN_CHUNK_WORDS", "int"),
    "pipeline.enhance_min_header_gap_chars": ("pipeline.enhance_md_headers", "MIN_HEADER_GAP_CHARS", "int"),
    # ── E2E validation (T1.3) ──
    "e2e.borp_min_sources":             ("pipeline.e2e_test", "BORP_MIN_SOURCES", "int"),
    "e2e.min_pass_rate":                ("pipeline.e2e_test", "E2E_MIN_PASS_RATE", "float"),
    "e2e.min_fbs":                      ("pipeline.e2e_test", "E2E_MIN_FBS", "int"),
    "e2e.convergent_ratio":             ("pipeline.e2e_test", "E2E_CONVERGENT_RATIO", "float"),
    # ── Pipeline tuning (T1.4: threshold/flag registration) ──
    "pipeline.chunk_size_words":        ("pipeline.pipeline_paths", "CHUNK_SIZE_WORDS", "int"),
    "pipeline.chunk_overlap_words":     ("pipeline.pipeline_paths", "CHUNK_OVERLAP_WORDS", "int"),
    "pipeline.intent_threshold":        ("pipeline.pipeline_paths", "INTENT_THRESHOLD", "float"),
    "pipeline.intent_top_k_ratio":      ("pipeline.pipeline_paths", "INTENT_TOP_K_RATIO", "float"),
    "pipeline.borp_min_sources":        ("pipeline.pipeline_paths", "BORP_MIN_SOURCES", "int"),
    # ── Stage 1.5 tuning ──
    "stage1_5.min_cluster_size":        ("pipeline.pipeline_paths", "S15_MIN_CLUSTER_SIZE", "int"),
    "stage1_5.max_cluster_size":        ("pipeline.pipeline_paths", "S15_MAX_CLUSTER_SIZE", "int"),
    "stage1_5.neighbor_k":              ("pipeline.pipeline_paths", "S15_NEIGHBOR_K", "int"),
    # ── Stage 2 tuning ──
    "stage2.batch_size":                ("pipeline.pipeline_paths", "S2_BATCH_SIZE", "int"),
    "stage2.evidence_tracking":         ("pipeline.pipeline_paths", "S2_EVIDENCE_TRACKING", "bool"),
    # ── Stage 4 tuning ──
    "stage4.max_principles_per_cluster": ("pipeline.pipeline_paths", "S4_MAX_PRINCIPLES", "int"),
    # ── Stage 5 tuning ──
    "stage5.factscore_enabled":         ("pipeline.pipeline_paths", "S5_FACTSCORE_ENABLED", "bool"),
    # ── Stage 6 tuning ──
    "stage6.commit_non_fb_types":       ("pipeline.pipeline_paths", "S6_COMMIT_NON_FB", "bool"),
    "stage6.okf_export_enabled":        ("pipeline.pipeline_paths", "S6_OKF_EXPORT_ENABLED", "bool"),
    # ── Smoke test tuning ──
    "smoke.plumbing.skip_llm":          ("pipeline.pipeline_paths", "SMOKE_PLUMBING_SKIP_LLM", "bool"),
    "smoke.fast.skip_gemma_deep_check": ("pipeline.pipeline_paths", "SMOKE_FAST_SKIP_GEMMA", "bool"),
    "smoke.fast.max_books":             ("pipeline.pipeline_paths", "SMOKE_MAX_BOOKS", "int"),
}

# ── Acknowledged hardcoded values (resilient fallbacks in except blocks) ──
# These are inside try/except blocks as graceful degradation when config is unavailable.
# They mirror the config defaults in pipeline_paths.py — NOT drift risks.
ACKNOWLEDGED_HARDCODED: set[str] = {
    "BORP_MIN_SOURCES",      # e2e_test.py — except fallback (mirrors config default=2)
    "E2E_MIN_PASS_RATE",     # e2e_test.py — except fallback (mirrors config default=0.80)
    "E2E_MIN_FBS",           # e2e_test.py — except fallback (mirrors config default=30)
    "E2E_CONVERGENT_RATIO",  # e2e_test.py — except fallback (mirrors config default=0.25)
    "INTERVAL",              # n2_watchdog.py — 300s polling loop (P3: migrate to config.stage2.watchdog_interval)
}


def load_config() -> dict:
    """Load pipeline_config.yaml."""
    import yaml
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f)


def get_config_value(cfg: dict, key_path: str):
    """Get nested config value by dotted path. Returns None if missing."""
    parts = key_path.split(".")
    val = cfg
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p)
        else:
            return None
    return val


def get_code_value(module_name: str, attr_name: str):
    """Get module-level constant value. Returns None if not importable."""
    # Ensure project root is in sys.path (needed when script is run directly)
    _project_root = str(Path(__file__).resolve().parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    try:
        import importlib
        mod = importlib.import_module(module_name)
        return getattr(mod, attr_name, None)
    except Exception:
        return None


def run_audit() -> tuple[list[dict], list[dict], list[dict]]:
    """Run full audit. Returns (drifts, missing_in_config, missing_in_code)."""
    cfg = load_config()
    drifts = []
    missing_in_config = []
    missing_in_code = []

    for key_path, mapping in CONFIG_TO_CODE.items():
        if mapping is None:
            continue
        module, attr, typ = mapping

        config_val = get_config_value(cfg, key_path)
        code_val = get_code_value(module, attr)

        if config_val is None and code_val is not None:
            missing_in_config.append({
                "key": key_path,
                "code_value": code_val,
                "code_source": f"{module}.{attr}",
                "type": typ,
            })
        elif config_val is not None and code_val is None:
            missing_in_code.append({
                "key": key_path,
                "config_value": config_val,
                "expected_source": f"{module}.{attr}",
            })
        elif config_val is not None and code_val is not None:
            # Normalize types for comparison
            try:
                if typ == "int":
                    config_val = int(config_val)
                    code_val = int(code_val)
                elif typ == "float":
                    config_val = float(config_val)
                    code_val = float(code_val)
                elif typ == "bool":
                    config_val = bool(config_val)
                    code_val = bool(code_val)
            except (ValueError, TypeError):
                pass

            if config_val != code_val:
                drifts.append({
                    "key": key_path,
                    "config_value": config_val,
                    "code_value": code_val,
                    "config_type": type(config_val).__name__,
                    "code_type": type(code_val).__name__,
                    "code_source": f"{module}.{attr}",
                })

    return drifts, missing_in_config, missing_in_code


def check_hardcoded_elsewhere() -> list[dict]:
    """Scan for hardcoded values NOT in the registry — potential future drift."""
    import re
    unchecked = []
    py_files = sorted(Path(__file__).resolve().parent.glob("*.py"))

    known_attrs = {m[1] for m in CONFIG_TO_CODE.values() if m is not None}
    known_attrs |= ACKNOWLEDGED_HARDCODED  # Tier 1+ pending migrations

    for fp in py_files:
        with open(fp) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            m = re.match(
                r"^([A-Z][A-Z_0-9]{2,})\s*=\s*(-?\d+\.?\d*|True|False)(?:\s+#.*)?$",
                line.strip(),
            )
            if not m:
                continue
            name = m.group(1)
            if name in known_attrs:
                continue
            # Skip if file is config-aware
            if "_CFG" in line or ".get(" in line:
                continue
            unchecked.append({
                "file": str(fp.relative_to(Path(__file__).resolve().parent)),
                "line": i,
                "name": name,
                "value": m.group(2),
            })

    return unchecked


def print_report(drifts, missing_in_config, missing_in_code, unchecked, fmt="text"):
    """Print audit report."""
    if fmt == "json":
        print(json.dumps({
            "drifts": drifts,
            "missing_in_config": missing_in_config,
            "missing_in_code": missing_in_code,
            "unchecked_hardcoded": unchecked,
        }, indent=2, default=str))
        return

    has_issues = drifts or missing_in_config or missing_in_code

    print("=" * 70)
    print("CONFIG AUDIT — config-code drift detection")
    print("=" * 70)

    if drifts:
        print(f"\n🔴 DRIFT — {len(drifts)} config values don't match code:")
        for d in drifts:
            print(f"  {d['key']}")
            print(f"    config: {repr(d['config_value'])} ({d['config_type']})")
            print(f"    code:   {repr(d['code_value'])} ({d['code_type']})")
            print(f"    source: {d['code_source']}")

    if missing_in_config:
        print(f"\n🟠 CODE-ONLY — {len(missing_in_config)} values in code but not config:")
        for m in missing_in_config:
            print(f"  {m['key']}: {repr(m['code_value'])} (from {m['code_source']})")

    if missing_in_code:
        print(f"\n🟡 CODE HARDCODED (not reading from config) — {len(missing_in_code)} values:")
        for m in missing_in_code:
            print(f"  {m['key']}: {repr(m['config_value'])} (expected at {m['expected_source']})")

    if unchecked:
        print(f"\n📋 UNCHECKED — {len(unchecked)} hardcoded values not in audit registry:")
        shown = 0
        for u in unchecked[:15]:
            print(f"  {u['file']}:{u['line']} {u['name']} = {u['value']}")
            shown += 1
        if len(unchecked) > 15:
            print(f"  ... and {len(unchecked) - 15} more")

    if not has_issues:
        print("\n✅ No config-code drift detected.")

    print("\n" + "=" * 70)

    return bool(drifts or missing_in_config)


def main():
    parser = argparse.ArgumentParser(description="Config-code drift audit")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--fix", action="store_true", help="Suggest config updates")
    parser.add_argument("--check-unchecked", action="store_true",
                        help="Also scan for unregistered hardcoded values")
    parser.add_argument("--strict", action="store_true",
                        help="Fail if ANY unregistered hardcoded values exist (enforcement mode)")
    args = parser.parse_args()

    drifts, mic, mico = run_audit()
    unchecked = check_hardcoded_elsewhere() if (args.check_unchecked or args.strict) else []

    fmt = "json" if args.json else "text"
    has_issues = print_report(drifts, mic, mico, unchecked, fmt)

    if args.fix and mic:
        print("\n💡 To fix, add these to config/pipeline_config.yaml:")
        for m in mic:
            print(f"  {m['key']}: {repr(m['code_value'])}")

    # --strict: unchecked hardcoded values also cause failure
    exit_code = 1 if has_issues else 0
    if args.strict and unchecked:
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
