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
    # ── Delegation guards (D-3020 / BUG-809, BUG-830) ──
    # research_run kept a SECOND copy of two values the guards already declare; preflight turned red
    # on them on 2026-10-15, which is how a second home is supposed to be found.
    "engine.yaml#fanout.guards.default_timeout_s": ("pipeline.research_run", "DEFAULT_TIMEOUT_S", "int"),
    "engine.yaml#fanout.guards.stall_s":           ("pipeline.research_run", "DEFAULT_STALL_S", "int"),
    "engine.yaml#model_store.census_move_ratio":   ("pipeline.model_store_census", "MOVE", "float"),
    # D-3033/BUG-838: the FLOOR now has a reader inside the instrument that OFFERS a candidate, so it can no
    # longer drift behind a second copy in the offerer. Until 2026-10-16 the only reader was a sweep script
    # in temp/, which meant the rule that decides what the owner is shown had no governed consumer.
    "engine.yaml#model_store.deletion_floor_bytes": ("pipeline.model_store_census", "FLOOR", "int"),
    # T-142/D-3034/BUG-840: the RESOLUTION RULE itself now has the same treatment as the floor. The rule that
    # decides which bytes read as DECLARED - and therefore which bytes are never offered to the owner - is read
    # from one home, so a second copy of it in code (the mention index it replaced) can be found by this rail.
    "engine.yaml#model_store.resolution_domain":   ("pipeline.model_store_census", "RESOLUTION", "dict"),
    "engine.yaml#model_store.resolution_domain.report_rows": ("pipeline.model_store_census", "REPORT_ROWS", "int"),
    "engine.yaml#model_store.redundancy":   ("pipeline.model_store_census", "REDUNDANCY", "dict"),
    "engine.yaml#model_store.sweep":        ("pipeline.model_store_sweep", "RULE", "dict"),
    # T-168/BUG-844/D-3036: the delegated-run trace reads the journal home, the end-state vocabulary, the
    # read-only token and the budget rule from ONE declared place (config/agent_surface.yaml#logging), so the
    # reader can never restate them (C12) - and every key is REQUIRED there, so a value the config lacks is
    # FATAL rather than a default (D-2644).
    "agent_surface.yaml#logging":           ("scripts.delegate_journal", "LOGGING", "dict"),
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
    "services.ollama.embed_max_chars":  ("pipeline.ollama_embed", "EMBED_MAX_CHARS", "int"),
    "services.ollama.batch_size":       ("pipeline.ollama_embed", "BATCH_SIZE", "int"),
    # ── D2304/D2307: DSPy + recall thresholds (C12) ──
    # T-206/D-3153: the constant lives in pipeline_paths, which is importable WITHOUT the optional dspy-ai
    # package. The old mapping pointed at pipeline.dspy_trainer, so on an interpreter without dspy the audit
    # could not read it and reported a false config/code mismatch.
    "s2.dspy_max_tokens":               ("pipeline.pipeline_paths", "S2_DSPY_MAX_TOKENS", "int"),
    # T-206/D-3153: the "receipt, not a work" floor is a MEANING value, so it moved to YAML (C12).
    "stage0.artifact.min_output_bytes": ("pipeline.stage0_convert", "MIN_OUTPUT_BYTES", "int"),
    # T-206/D-3153: probe read windows are measurements about this machine's containers, declared beside the
    # admission probes that use them. The binary format offsets remain FORMAT_SPEC_HARDCODED.
    "ingest_identity_gate.yaml#source_library.admission.container_integrity.probe_limits.tail_bytes":
        ("pipeline.container_integrity", "TAIL_BYTES", "int"),
    "ingest_identity_gate.yaml#source_library.admission.container_integrity.probe_limits.head_bytes":
        ("pipeline.container_integrity", "HEAD_BYTES", "int"),
    "recall.match_threshold":           ("pipeline.recall_measure", "DEFAULT_MATCH_THRESHOLD", "float"),
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
    # ── Stage 2 tuning ──
    "stage2.batch_size":                ("pipeline.pipeline_paths", "S2_BATCH_SIZE", "int"),
    "stage2.evidence_tracking":         ("pipeline.pipeline_paths", "S2_EVIDENCE_TRACKING", "bool"),
    # ── Stage 4 tuning ──
    "stage4.max_principles_per_cluster": ("pipeline.pipeline_paths", "S4_MAX_PRINCIPLES", "int"),
    "stage4.reclassify_chunk_size":       ("pipeline.reclassify_merged_axis", "CHUNK_SIZE_DEFAULT", "int"),
    "stage4.quarantine_output":           ("pipeline.pipeline_paths", "S4_QUARANTINE_OUTPUT", "str"),
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
    # delegation_economy.py — the rc VOCABULARY (0 ok / 1 breach / 2 unmeasured), which is the repo's
    # own convention (BUG-457: loud, not fatal) and not a policy value. Config-ising an exit code
    # would make the meaning of a run's result configurable, which is the opposite of C12's intent.
    "RC_OK",
    "RC_BREACH",
    "RC_UNMEASURED",
    # model_store_census.py — the same rc VOCABULARY (0 ok / 1 fault / 2 owner-owed). T-206: an exit code is
    # a language for reading a run's RESULT; making it configurable makes the result's meaning configurable.
    "RC_FAULT",
    "RC_OWNER_OWED",
    "BORP_MIN_SOURCES",      # e2e_test.py — except fallback (mirrors config default=2)
    "S4_DEPTH_MAX_TOKENS",   # stage4_merged_call.py — except fallback (mirrors stage4.depth_max_tokens=1024)
    "E2E_MIN_PASS_RATE",     # e2e_test.py — except fallback (mirrors config default=0.80)
    "E2E_MIN_FBS",           # e2e_test.py — except fallback (mirrors config default=30)
    "E2E_CONVERGENT_RATIO",  # e2e_test.py — except fallback (mirrors config default=0.25)
    "E2E_CORPUS_AWARE_PASS_RATE",       # e2e_test.py — except fallback (mirrors e2e.corpus_aware_pass_rate.enabled=false)
    "E2E_CONVERGENT_MIN_PASS_RATE",     # e2e_test.py — except fallback (mirrors e2e.corpus_aware_pass_rate.convergent_min_pass_rate=0.25)
    "E2E_SINGLE_SOURCE_MIN_PASS_RATE",  # e2e_test.py — except fallback (mirrors e2e.corpus_aware_pass_rate.single_source_min_pass_rate=0.20)
    "INTERVAL",              # n2_watchdog.py — 300s polling loop (P3: migrate to config.stage2.watchdog_interval)
    "TRADITIONAL_EXTRACT_SECONDS",  # hybrid_gate_ab.py — documented benchmark estimate, not a runtime threshold
    "POLL_S",                # research_run.py — the watch loop's CADENCE (2 s), not a policy value: the
                             # budget it serves is declared (fanout.guards), the interval is implementation
    "TEMPERATURE",           # oneshot_ask.py — R7 mandates temp=0.0 on every generation script; a
                             # CONSTITUTIONAL constant, so making it configurable would make R7 violable
}

# ── Binary FORMAT constants: declared, with their source, and deliberately NOT tunable ──
# T-206/D-3153: a Palm database offset is not a policy knob. Making it configurable would let a config edit
# silently change which bytes a container probe reads, which is the opposite of C12's purpose (one DECLARED
# home, not every number made editable). Each entry names the format fact that fixes the value.
FORMAT_SPEC_HARDCODED: dict[str, str] = {
    "PALMDB_MAGIC_OFFSET": "Palm Database type/creator field is at byte 60 (PalmDOC/MOBI container format)",
    "PALMDB_HEADER_BYTES": "Palm Database record table begins at byte 78",
    "PALMDB_RECORD_ENTRY_BYTES": "Palm Database record entry is 8 bytes: 4-byte offset, 1-byte attributes, 3-byte unique id",
    "OLE_HEADER_BYTES": "OLE Compound Document header is one 512-byte sector",
}


def load_config() -> dict:
    """Load pipeline_config.yaml."""
    import yaml
    cfg_path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
    with open(cfg_path, encoding='utf-8') as f:
        return yaml.safe_load(f)


_OTHER_HOMES: dict[str, dict] = {}


def other_home(name: str) -> dict:
    """Load a DECLARED config home by file name, so a registry entry can name where a value LIVES.

    engine.yaml facts are not in pipeline_config.yaml, and copying them there to satisfy this audit
    would create the second home the audit exists to prevent (C12). A key path may therefore be
    written `engine.yaml#fanout.guards.stall_s`.
    """
    if name not in _OTHER_HOMES:
        path = Path(__file__).resolve().parent.parent / "config" / name
        if not path.exists():
            raise SystemExit(f"FATAL: the audit registry names config home {name!r}, which does not exist "
                             f"at {path} - a registry entry that cannot be checked is worse than none")
        import yaml
        _OTHER_HOMES[name] = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return _OTHER_HOMES[name]


def get_config_value(cfg: dict, key_path: str):
    """Get nested config value by dotted path. Returns None if missing.

    A `FILE#dotted.path` path is resolved against that file (see other_home).
    """
    if "#" in key_path:
        home, _, rest = key_path.partition("#")
        return get_config_value(other_home(home), rest)
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


def run_audit(cfg: dict | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """Run full audit. Returns (drifts, missing_in_config, missing_in_code)."""
    cfg = load_config() if cfg is None else cfg
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


def check_hardcoded_elsewhere() -> tuple[list[dict], int]:
    """Scan for hardcoded values NOT in the registry — potential future drift.

    Returns the findings AND the number of modules actually read. The count is part of the reading: an empty
    report from a scan that never reached its own file set is not zero (BUG-1025's lesson).
    """
    import re
    unchecked = []
    py_files = sorted(Path(__file__).resolve().parent.glob("*.py"))

    known_attrs = {m[1] for m in CONFIG_TO_CODE.values() if m is not None}
    known_attrs |= ACKNOWLEDGED_HARDCODED  # Tier 1+ pending migrations
    known_attrs |= set(FORMAT_SPEC_HARDCODED)  # T-206: binary layout facts are declared, never tunable

    for fp in py_files:
        with open(fp, encoding='utf-8') as f:
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

    return unchecked, len(py_files)


def unchecked_verdict(count: int, ceiling: int) -> tuple[bool, str]:
    """PURE: the two-sided rule for the shrink-only unchecked ceiling (T-206, D-2644).

    At-or-below is green; above is a FAULT. A ceiling that refuses both directions is not a rule (BUG-492).
    """
    if count <= ceiling:
        return True, f"unchecked {count} <= ceiling {ceiling} ({ceiling - count} headroom)"
    return False, f"unchecked {count} EXCEEDS ceiling {ceiling} by {count - ceiling}"


def audit_ceiling(cfg: dict) -> int:
    """Read the declared shrink-only ceiling for unchecked hardcodes, failing closed when absent."""
    block = (cfg.get("config_audit") or {}).get("unchecked_hardcoded")
    if not isinstance(block, dict):
        raise SystemExit(
            "FATAL: config/pipeline_config.yaml#config_audit.unchecked_hardcoded is not declared - the audit's "
            "own debt needs a ceiling with a home (C12/T-206)"
        )
    if str(block.get("direction")) != "shrink_only":
        raise SystemExit(
            "FATAL: config_audit.unchecked_hardcoded.direction must be 'shrink_only' - a ceiling that can be "
            "raised by an edit is not a shrink guard (D-2644/T-206)"
        )
    try:
        ceiling = int(block["ceiling"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(
            "FATAL: config_audit.unchecked_hardcoded.ceiling is absent or not an integer (C12/T-206)"
        ) from exc
    if ceiling < 0:
        raise SystemExit("FATAL: config_audit.unchecked_hardcoded.ceiling cannot be negative (T-206)")
    return ceiling


def print_report(drifts, missing_in_config, missing_in_code, unchecked, fmt="text", *,
                 unchecked_ceiling: int | None = None, files_scanned: int | None = None):
    """Print audit report."""
    if fmt == "json":
        print(json.dumps({
            "drifts": drifts,
            "missing_in_config": missing_in_config,
            "missing_in_code": missing_in_code,
            "unchecked_hardcoded": unchecked,
            "unchecked_ceiling": unchecked_ceiling,
            "files_scanned": files_scanned,
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

    if unchecked_ceiling is not None:
        ok, msg = unchecked_verdict(len(unchecked), unchecked_ceiling)
        mark = "✅" if ok else "🔴"
        print(f"\n{mark} UNCHECKED — {len(unchecked)} hardcoded value(s) not in the registry | {msg}")
        if files_scanned is not None:
            print(f"  scanned {files_scanned} pipeline module(s)")
        for u in unchecked[:15]:
            print(f"  {u['file']}:{u['line']} {u['name']} = {u['value']}")
        if len(unchecked) > 15:
            print(f"  ... and {len(unchecked) - 15} more")
        if not ok:
            print("  ❌ classify each item (YAML / rc vocabulary / declared format spec) or lower the count - "
                  "raising the ceiling requires a named decision, not an edit (T-206/D-2644)")

    if not has_issues and (unchecked_ceiling is None or len(unchecked) <= unchecked_ceiling):
        print("\n✅ No config-code drift detected.")

    print("\n" + "=" * 70)

    return bool(drifts or missing_in_config)


def _selftest() -> int:
    """Known-answer controls for the shrink-only unchecked rule: both directions must be SEEN."""
    cases = [
        (0, 0, True, "zero at zero"),
        (1, 0, False, "one above zero"),
        (9, 9, True, "at the ceiling"),
        (10, 9, False, "one above the ceiling"),
    ]
    failed = []
    for count, ceiling, expected, label in cases:
        got, _ = unchecked_verdict(count, ceiling)
        if got != expected:
            failed.append(f"{label}: expected {expected}, got {got}")
    if failed:
        for f in failed:
            print(f"  !! {f}")
        print(f"config-audit selftest: {len(cases) - len(failed)}/{len(cases)} known-answer controls")
        return 1
    print(f"config-audit selftest: {len(cases)}/{len(cases)} known-answer controls")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Config-code drift audit")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--fix", action="store_true", help="Suggest config updates")
    parser.add_argument("--check-unchecked", action="store_true",
                        help="Also scan for unregistered hardcoded values")
    parser.add_argument("--strict", action="store_true",
                        help="Fail when the unchecked count is ABOVE its declared shrink-only ceiling")
    parser.add_argument("--selftest", action="store_true",
                        help="Run the two-sided known-answer controls for the unchecked-ceiling rule")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(_selftest())

    cfg = load_config()
    drifts, mic, mico = run_audit(cfg)
    unchecked: list[dict] = []
    files_scanned: int | None = None
    ceiling: int | None = None
    if args.check_unchecked or args.strict:
        unchecked, files_scanned = check_hardcoded_elsewhere()
        ceiling = audit_ceiling(cfg)

    fmt = "json" if args.json else "text"
    has_issues = print_report(drifts, mic, mico, unchecked, fmt,
                              unchecked_ceiling=ceiling, files_scanned=files_scanned)

    if args.fix and mic:
        print("\n💡 To fix, add these to config/pipeline_config.yaml:")
        for m in mic:
            print(f"  {m['key']}: {repr(m['code_value'])}")

    exit_code = 1 if has_issues else 0
    if args.strict:
        if files_scanned == 0:
            print("FATAL: the unchecked scan read ZERO pipeline modules - an empty report from a gate that did "
                  "not run is not zero (BUG-1025/T-206)")
            exit_code = 1
        elif ceiling is not None and len(unchecked) > ceiling:
            exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
