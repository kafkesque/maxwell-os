"""
runner.py — Unified Pipeline Runner (D2061, D2120).
====================================================
Authority: D2120 | CONSTITUTION.md §2 (8-stage pipeline)

Single entry point for the entire Maxwell OS knowledge extraction pipeline.
Handles: stage ordering, resume, progress, error recovery, configuration.

Usage:
    python pipeline/runner.py                       # Full pipeline, latest run_id
    python pipeline/runner.py --domain pricing      # Single domain
    python pipeline/runner.py --smoke               # Fast smoke test
    python pipeline/runner.py --resume-from stage2  # Resume after crash
    python pipeline/runner.py --stages 0,1,1.5      # Specific stages only
    python pipeline/runner.py --quality fast        # Quality tier (C28)
    python pipeline/runner.py --books 10            # Limit books
    python pipeline/runner.py --dry-run             # Show what would run

Architecture: 8 stages (Stage 3 REMOVED per D2120)
    Stage 0:    Convert EPUB/PDF → MD
    Stage 0.5:  Extract metadata (author, title, year)
    Stage 1:    Chunk MD → segments
    Stage 1.3:  Regex pre-filter segments
    Stage 1.5:  FAISS cosine cluster (R-NN, D2120)
    Stage 2:    Convergent extract (Qwen3-Coder-30B)
    Stage 4:    Classify + format + lightweight dedup (GPT-OSS-20B)
    Stage 5:    Verify (DeBERTa FEVER NLI + Phi-4-mini cross-family)
    Stage 6:    Commit (SQLite + Parquet)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Project root (runner.py lives in pipeline/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.pipeline_paths import (  # noqa: E402
    CHECKPOINT_DIR,
    S6_DIR,
    S13_DIR,
    STAGE1_5_CHECKPOINT,
    STAGE_CHECKPOINTS,
    get_run_id,
)

# ── Stage Registry ────────────────────────────────────────────────────────

STAGES: dict[str, dict[str, Any]] = {
    "0": {
        "name": "Convert (EPUB/PDF → MD)",
        "script": "pipeline/stage0_convert.py",
        "checkpoint": STAGE_CHECKPOINTS.get(0),
        "can_parallelize": True,
        "depends_on": None,
    },
    "0.5": {
        "name": "Extract Metadata",
        "script": "pipeline/stage0_5_extract_metadata.py",
        "checkpoint": CHECKPOINT_DIR / "book_metadata.jsonl",  # D2186: matches script's actual cache path (global, content-hash keyed)
        "can_parallelize": True,
        "depends_on": "0",
    },
    "1": {
        "name": "Chunk (MD → Segments)",
        "script": "pipeline/stage1_chunk.py",
        "checkpoint": STAGE_CHECKPOINTS.get(1),
        "can_parallelize": True,
        "depends_on": "0.5",
    },
    "1.3": {
        "name": "Regex Pre-filter",
        "script": "pipeline/stage1_3_prefilter.py",
        "checkpoint": S13_DIR / get_run_id() / "checkpoint.jsonl",  # D2134: self-contained
        "can_parallelize": False,
        "depends_on": "1",
    },
    "1.5": {
        "name": "FAISS Cluster (R-NN)",
        "script": "pipeline/stage1_5_embed_cluster.py",
        "checkpoint": STAGE1_5_CHECKPOINT,  # D2134: self-contained
        "can_parallelize": False,
        "depends_on": "1.3",
    },
    "2": {
        "name": "Convergent Extract (Qwen3-Coder-30B)",
        "script": "pipeline/stage2_extract.py",
        "checkpoint": STAGE_CHECKPOINTS.get(2),
        "can_parallelize": False,
        "depends_on": "1.5",
        "llm_bound": True,
    },
    "4": {
        "name": "Classify + Format (GPT-OSS-20B)",
        "script": "pipeline/stage4_merge.py",
        "checkpoint": STAGE_CHECKPOINTS.get(4),
        "can_parallelize": False,
        "depends_on": "2",
        "llm_bound": True,
    },
    "5": {
        "name": "Verify (DeBERTa FEVER + Phi-4-mini)",
        "script": "pipeline/stage5_verify.py",
        "checkpoint": STAGE_CHECKPOINTS.get(5),
        "can_parallelize": False,
        "depends_on": "4",
        "llm_bound": True,
    },
    "6": {
        "name": "Commit (SQLite + Parquet)",
        "script": "pipeline/stage6_commit.py",
        "checkpoint": STAGE_CHECKPOINTS.get(6),
        "can_parallelize": False,
        "depends_on": "5",
    },
    "6b": {
        "name": "Anytype Push Prep (Domain Subfolders)",
        "script": "pipeline/stage6b_anytype_push.py",
        "checkpoint": S6_DIR / get_run_id() / "anytype_push" / "push_stats.json",
        "can_parallelize": False,
        "depends_on": "6",
    },
    "6c": {
        "name": "Obsidian Export (Markdown Vault)",
        "script": "pipeline/stage6c_obsidian_export.py",
        "checkpoint": S6_DIR / get_run_id() / "obsidian_vault" / ".obsidian_export.json",
        "can_parallelize": False,
        "depends_on": "6",
    },
}

STAGE_ORDER: list[str] = ["0", "0.5", "1", "1.3", "1.5", "2", "4", "5", "6", "6b", "6c"]


# ── Resume marker ──────────────────────────────────────────────────────────

# D2184: Resume marker is now run-scoped (was global CHECKPOINT_DIR / "pipeline_resume.json")
# Each run_id gets its own resume state — no cross-run contamination.
_RESUME_MARKER: Path = CHECKPOINT_DIR / get_run_id() / "pipeline_resume.json"


def _write_resume_marker(stage_id: str, *, paused: bool = False) -> None:
    """Write pipeline resume state for crash recovery.

    Called after each successful stage and on SIGINT (paused=True).
    The runner reads this on startup to auto-resume from the last completed stage.
    """
    _RESUME_MARKER.parent.mkdir(parents=True, exist_ok=True)
    import json as _json
    state: dict[str, Any] = {
        "last_stage": stage_id,
        "paused": paused,
        "run_id": get_run_id(),
        "timestamp": time.time(),
    }
    _RESUME_MARKER.write_text(_json.dumps(state))


def _clear_resume_marker() -> None:
    """Clear resume marker after successful full run."""
    if _RESUME_MARKER.exists():
        _RESUME_MARKER.unlink()


# ── Runner ────────────────────────────────────────────────────────────────

def find_resume_point(resume_from: str | None = None) -> str | None:
    """Determine which stage to resume from.

    If resume_from is specified, use it. Otherwise scan checkpoints
    and find the first incomplete stage.
    """
    if resume_from:
        if resume_from not in STAGES:
            print(f"❌ Unknown stage: {resume_from}")
            print(f"   Valid stages: {', '.join(STAGE_ORDER)}")
            sys.exit(1)
        return resume_from

    # Auto-detect: find first stage with missing checkpoint
    for stage_id in STAGE_ORDER:
        stage = STAGES[stage_id]
        ckpt = stage.get("checkpoint")
        if ckpt and not ckpt.exists():
            return stage_id

    # All checkpoints exist — resume from last stage (re-run it)
    return STAGE_ORDER[-1]


def _get_stage_timeout(stage_id: str) -> float | None:
    """D2269: Get per-stage timeout from pipeline_config.yaml.

    Timeout keys in config match runner's STAGES dict keys (e.g., "2", "4").
    S2 extraction timeout = null (unlimited) for long full-corpus runs.
    All other stages default to 3600s (60 min) if not configured.

    Returns:
        Timeout in seconds (float), or None for unlimited.
    """
    import yaml as _yaml_timeout
    _config_path = _PROJECT_ROOT / "config" / "pipeline_config.yaml"
    try:
        with open(_config_path) as _f:
            _cfg = _yaml_timeout.safe_load(_f) or {}
        _timeouts = _cfg.get("stages", {}).get("timeouts", {})
        # Direct key lookup — config keys match STAGES dict keys (C12: no hardcoded mapping)
        return _timeouts.get(stage_id, 3600.0)
    except Exception:
        return 3600.0  # fallback default


def run_stage(
    stage_id: str,
    *,
    smoke: bool = False,
    skip_llm: bool = False,
    fast_model: str | None = None,
    domain: str | None = None,
    books: int | None = None,
    quality: str = "balanced",
    dry_run: bool = False,
) -> bool:
    """Execute a single pipeline stage via subprocess.

    Returns:
        True if stage completed successfully, False otherwise.
    """
    stage = STAGES[stage_id]
    script = _PROJECT_ROOT / stage["script"]

    if not script.exists():
        print(f"   ⚠️  Script not found: {script}")
        return False

    cmd = ["python3", str(script)]
    env = {}

    # Build environment overrides
    if smoke:
        env["MAXWELL_RUN_ID"] = "smoke"
    if skip_llm and stage.get("llm_bound"):
        env["MAXWELL_SKIP_LLM"] = "1"
    if fast_model and stage.get("llm_bound") and stage_id == "2":
        env["MAXWELL_FAST_MODEL"] = fast_model
    if domain:
        env["MAXWELL_DOMAIN"] = domain
    if books:
        env["MAXWELL_BOOK_LIMIT"] = str(books)
    if quality:
        env["MAXWELL_QUALITY"] = quality

    if dry_run:
        env_str = " ".join(f"{k}={v}" for k, v in env.items())
        print(f"   [DRY RUN] {env_str} {script.name}")
        return True

    # ── D2136: Preflight health check before LLM-bound stages ──────────
    if stage.get("llm_bound") and not skip_llm:
        print("   🔍 Preflight: checking OMLX health...")
        try:
            watchdog = _PROJECT_ROOT / "pipeline" / "omlx_watchdog.py"
            preflight = subprocess.run(
                ["python3", str(watchdog), "--pre-stage"],
                cwd=str(_PROJECT_ROOT),
                capture_output=True,
                timeout=30,
            )
            if preflight.returncode != 0:
                if stage.get("llm_bound"):
                    print(f"   ❌ OMLX DOWN — LLM-bound stage {stage_id} cannot proceed")
                    print(f"   {preflight.stderr.decode()[-200:]}")
                    sys.exit(1)
                else:
                    print(f"   ⚠️  OMLX watchdog warning (continuing — non-LLM stage): {preflight.stderr.decode()[-200:]}")
            else:
                print("   ✅ OMLX healthy")
        except Exception as e:
            if stage.get("llm_bound"):
                print(f"   ❌ Preflight check failed for LLM-bound stage {stage_id} ({e})")
                sys.exit(1)
            print(f"   ⚠️  Preflight check failed ({e}) — continuing (non-LLM stage)")

    # Run stage
    label = f"[Stage {stage_id}] {stage['name']}"
    print(f"\n{'─'*60}")
    print(f"▶ {label}")
    print(f"{'─'*60}")

    # D2269: Per-stage configurable timeout from pipeline_config.yaml
    # S2 (extraction) defaults to null (unlimited) for long full-corpus runs.
    # Other stages default to 3600s (60 min).
    stage_timeout = _get_stage_timeout(stage_id)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(_PROJECT_ROOT),
            env={**__import__("os").environ, **env},
            capture_output=False,
            timeout=stage_timeout,
        )
        elapsed = time.time() - start

        if result.returncode == 0:
            print(f"✅ {label} — {elapsed:.1f}s")
            # ── D2136: Write resume marker after successful stage ──────
            _write_resume_marker(stage_id)
            return True
        else:
            print(f"❌ {label} — FAILED (exit code {result.returncode}) — {elapsed:.1f}s")
            return False
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"⏰ {label} — TIMEOUT ({elapsed:.1f}s)")
        return False
    except KeyboardInterrupt:
        elapsed = time.time() - start
        print(f"\n⏸️  Pipeline paused at Stage {stage_id} ({elapsed:.1f}s)")
        _write_resume_marker(stage_id, paused=True)
        print(f"   Resume with: python pipeline/runner.py --resume-from {stage_id}")
        raise
    except Exception as e:
        elapsed = time.time() - start
        print(f"💥 {label} — ERROR: {e} — {elapsed:.1f}s")
        return False


def _check_version_consistency() -> None:
    """D2176: Verify all version sources agree before pipeline execution.

    version.yaml is the single source of truth for all version strings (D2169).
    This gate prevents objects from being stamped with conflicting schema_version
    values, which would break reproducibility and downstream schema validation.
    """
    import sys

    # D2182: Use _PROJECT_ROOT (not cwd) for version gate paths
    version_yaml_path: Path = _PROJECT_ROOT / "config" / "version.yaml"
    pipeline_config_path: Path = _PROJECT_ROOT / "config" / "pipeline_config.yaml"

    if not version_yaml_path.exists():
        print("⚠️  config/version.yaml not found — skipping version gate")
        return

    # Read version.yaml
    try:
        import yaml
        with open(version_yaml_path) as f:
            vy = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"⚠️  Cannot parse version.yaml ({e}) — skipping version gate")
        return

    expected_schema: str = str(vy.get("schema_version", "")).strip().strip("'\"")
    gate_enabled: bool = vy.get("version_gate_enabled", True)

    if not gate_enabled:
        print("   ℹ️  Version gate disabled in version.yaml")
        return

    if not expected_schema:
        print("⚠️  No schema_version in version.yaml — skipping version gate")
        return

    # Read pipeline_config.yaml
    violations: list[str] = []
    if pipeline_config_path.exists():
        try:
            with open(pipeline_config_path) as f:
                pcy = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️  Cannot parse pipeline_config.yaml ({e}) — skipping version gate")
            return

        cfg_schema = str(pcy.get("pipeline", {}).get("schema_version", "")).strip().strip("'\"")
        if cfg_schema and cfg_schema != expected_schema:
            violations.append(
                f"pipeline_config.yaml → schema_version: '{cfg_schema}' "
                f"(expected '{expected_schema}' from version.yaml)"
            )

    if violations:
        print("\n" + "=" * 70)
        print("❌ VERSION GATE FAILED — pipeline refuses to run")
        print("=" * 70)
        for v in violations:
            print(f"   • {v}")
        print("\n   Fix: update schema_version fields to match version.yaml")
        print("   Or set version_gate_enabled: false in config/version.yaml")
        print("=" * 70 + "\n")
        sys.exit(1)

    print(f"   ✅ Version gate passed: schema_version={expected_schema}")


def run_pipeline(
    *,
    resume_from: str | None = None,
    stages: list[str] | None = None,
    smoke: bool = False,
    skip_llm: bool = False,
    fast_model: str | None = None,
    domain: str | None = None,
    books: int | None = None,
    quality: str = "balanced",
    dry_run: bool = False,
    stop_after: str | None = None,
) -> bool:
    """Execute the full pipeline or a subset of stages.

    Args:
        resume_from: Stage ID to resume from (skips completed stages before it).
        stages: Explicit list of stage IDs to run (overrides resume_from).
        smoke: Use smoke test config (fast model, limited books).
        skip_llm: Skip LLM-bound stages (plumbing smoke).
        fast_model: Override model for LLM stages.
        domain: Filter books by domain directory.
        books: Limit number of books to process.
        quality: Quality tier (fast/balanced/maximum).
        dry_run: Print what would run without executing.
        stop_after: Stop after completing this stage.

    Returns:
        True if all stages completed successfully.
    """
    # D2176: Version gate — refuse to run if version sources disagree.
    # version.yaml is the single source of truth (D2169). If pipeline_config.yaml
    # or any other file declares a different schema_version, the pipeline halts
    # rather than producing objects with ambiguous version provenance.
    _check_version_consistency()

    # Determine stages to run
    if stages:
        stage_ids = stages
    else:
        start = find_resume_point(resume_from)
        start_idx = STAGE_ORDER.index(start)
        stage_ids = STAGE_ORDER[start_idx:]

    print("╔══════════════════════════════════════════════════════════╗")
    print("║        Maxwell OS Pipeline Runner v3.0 (D2120)          ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Run ID:    {get_run_id():<42s}║")
    print(f"║  Quality:   {quality:<42s}║")
    print(f"║  Mode:      {'DRY RUN' if dry_run else 'smoke' if smoke else 'full':<42s}║")
    print(f"║  Stages:    {', '.join(stage_ids):<42s}║")
    if domain:
        print(f"║  Domain:    {domain:<42s}║")
    if books:
        print(f"║  Books:     {books:<42d}║")
    print("╚══════════════════════════════════════════════════════════╝")

    if dry_run:
        print("\n📋 DRY RUN — no stages will be executed.\n")

    # Execute stages
    total_start = time.time()
    completed = 0
    failed = 0
    skipped = 0

    for stage_id in stage_ids:
        # Check LLM skip
        if skip_llm and STAGES[stage_id].get("llm_bound"):
            label = f"[Stage {stage_id}] {STAGES[stage_id]['name']}"
            print(f"\n⏭️  {label} — SKIPPED (LLM stages disabled)")
            skipped += 1
            continue

        success = run_stage(
            stage_id,
            smoke=smoke,
            skip_llm=skip_llm,
            fast_model=fast_model,
            domain=domain,
            books=books,
            quality=quality,
            dry_run=dry_run,
        )

        if dry_run:
            completed += 1
        elif success:
            completed += 1
        else:
            failed += 1
            print(f"\n⚠️  Stage {stage_id} FAILED. Pipeline stopped.")
            print(f"   Resume with: python pipeline/runner.py --resume-from {stage_id}")
            break

        if stop_after and stage_id == stop_after:
            print(f"\n⏸️  Stopping after Stage {stage_id} (--stop-after)")
            break

    # Summary
    total_elapsed = time.time() - total_start
    print(f"\n{'═'*60}")
    print(f"Pipeline {'preview' if dry_run else 'complete'} — "
          f"{completed} done, {failed} failed, {skipped} skipped "
          f"({total_elapsed:.1f}s)")
    print(f"{'═'*60}")

    if not dry_run and failed == 0:
        _clear_resume_marker()

    return failed == 0


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point for PipelineRunner."""
    parser = argparse.ArgumentParser(
        description="Maxwell OS Pipeline Runner v3.0 (D2120)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pipeline/runner.py                         # Full pipeline, auto-resume
  python pipeline/runner.py --smoke                 # Fast smoke test (<2min)
  python pipeline/runner.py --smoke-plumbing        # Plumbing smoke (<30s, no LLM)
  python pipeline/runner.py --resume-from stage2    # Resume after crash
  python pipeline/runner.py --domain pricing        # Pricing domain only
  python pipeline/runner.py --books 10              # Limit to 10 books
  python pipeline/runner.py --dry-run               # Show what would run
  python pipeline/runner.py --quality fast          # Fast quality tier
  python pipeline/runner.py --stages 1.5,2,4        # Specific stages only
        """,
    )

    # Mode flags
    parser.add_argument("--smoke", action="store_true",
                        help="Fast smoke test with Phi-4-mini (<2min)")
    parser.add_argument("--smoke-plumbing", action="store_true",
                        help="Plumbing smoke test, no LLM (<30s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would run without executing")

    # Stage control
    parser.add_argument("--resume-from", type=str, metavar="STAGE",
                        help="Resume from specific stage (e.g., stage2)")
    parser.add_argument("--stages", type=str,
                        help="Comma-separated stages to run (e.g., 0,1,1.5)")
    parser.add_argument("--stop-after", type=str, metavar="STAGE",
                        help="Stop after completing this stage")

    # Configuration
    parser.add_argument("--domain", type=str,
                        help="Filter books by domain directory")
    parser.add_argument("--books", type=int,
                        help="Limit number of books to process")
    parser.add_argument("--quality", type=str, default="balanced",
                        choices=["fast", "balanced", "maximum"],
                        help="Quality tier: fast/balanced/maximum (C28)")
    parser.add_argument("--fast-model", type=str,
                        default="Phi-4-mini-instruct-8bit",
                        help="Model for fast mode (default: Phi-4-mini)")
    parser.add_argument("--no-borp", action="store_true",
                        help="Disable BORP multi-source check (allow single-source FBs)")
    parser.add_argument("--run-id", type=str,
                        help="Override run_id (default: from config/env)")

    args = parser.parse_args()

    # Override run_id if specified
    if args.run_id:
        import os
        os.environ["MAXWELL_RUN_ID"] = args.run_id

    # ── D2136: Auto-resume from marker if no explicit resume-from ──────
    if not args.resume_from and _RESUME_MARKER.exists():
        import json as _json
        state = _json.loads(_RESUME_MARKER.read_text())
        if state.get("paused"):
            resume_stage = state.get("last_stage", "")
            if resume_stage in STAGES:
                print(f"⏸️  Found paused pipeline at Stage {resume_stage}")
                print("   Auto-resuming... (use --resume-from to override)")
                args.resume_from = resume_stage

    # Override BORP for single-domain test runs
    if args.no_borp:
        import os
        os.environ["MAXWELL_BORP_MIN_SOURCES"] = "1"

    # Mode resolution
    is_plumbing = args.smoke_plumbing
    is_smoke = args.smoke or is_plumbing
    skip_llm = is_plumbing
    fast_model = args.fast_model if is_smoke else None
    # Stage list
    stages_list = None
    if args.stages:
        stages_list = [s.strip() for s in args.stages.split(",")]

    success = run_pipeline(
        resume_from=args.resume_from,
        stages=stages_list,
        smoke=is_smoke,
        skip_llm=skip_llm,
        fast_model=fast_model,
        domain=args.domain,
        books=args.books,
        quality=args.quality,
        dry_run=args.dry_run,
        stop_after=args.stop_after,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
