"""
runner.py — Unified Pipeline Runner (D2061, D2120).
====================================================
Authority: D2120 | CONSTITUTION.md §2 (8-stage pipeline)

Single entry point for the entire Maxwell OS knowledge extraction pipeline.
Handles: stage ordering, resume, progress, error recovery, configuration.

Usage:
    python -m pipeline.run                          # Full pipeline, latest run_id
    python -m pipeline.run --domain pricing         # Single domain
    python -m pipeline.run --smoke                  # Fast smoke test
    python -m pipeline.run --resume-from stage2     # Resume after crash
    python -m pipeline.run --stages 0,1,1.5         # Specific stages only
    python -m pipeline.run --quality fast           # Quality tier (C28)
    python -m pipeline.run --books 10               # Limit books
    python -m pipeline.run --dry-run                # Show what would run

Architecture: 8 stages (Stage 3 REMOVED per D2120)
    Stage 0:    Convert EPUB/PDF → MD
    Stage 0.5:  Extract metadata (author, title, year)
    Stage 1:    Chunk MD → segments
    Stage 1.3:  Regex pre-filter segments
    Stage 1.5:  FAISS cosine cluster (R-NN, D2120)
    Stage 2:    Convergent extract (Qwen3.6 per cluster)
    Stage 4:    Classify + format + lightweight dedup (Phi-4-mini)
    Stage 5:    Verify (DeBERTa NLI + Gemma cross-family)
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
        "checkpoint": CHECKPOINT_DIR / "stage0_5_metadata.jsonl",
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
        "checkpoint": CHECKPOINT_DIR / "stage1_3_filtered.jsonl",
        "can_parallelize": False,
        "depends_on": "1",
    },
    "1.5": {
        "name": "FAISS Cluster (R-NN)",
        "script": "pipeline/stage1_5_embed_cluster.py",
        "checkpoint": CHECKPOINT_DIR / "stage1_5_clusters.jsonl",
        "can_parallelize": False,
        "depends_on": "1.3",
    },
    "2": {
        "name": "Convergent Extract (Qwen3.6)",
        "script": "pipeline/stage2_extract.py",
        "checkpoint": STAGE_CHECKPOINTS.get(2),
        "can_parallelize": False,
        "depends_on": "1.5",
        "llm_bound": True,
    },
    "4": {
        "name": "Classify + Format (Phi-4-mini)",
        "script": "pipeline/stage4_merge.py",
        "checkpoint": STAGE_CHECKPOINTS.get(4),
        "can_parallelize": False,
        "depends_on": "2",
        "llm_bound": True,
    },
    "5": {
        "name": "Verify (DeBERTa + Gemma)",
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
}

STAGE_ORDER: list[str] = ["0", "0.5", "1", "1.3", "1.5", "2", "4", "5", "6"]


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


def run_stage(
    stage_id: str,
    *,
    smoke: bool = False,
    skip_llm: bool = False,
    fast_model: str | None = None,
    skip_gemma: bool = False,
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
    if skip_gemma and stage_id == "5":
        env["MAXWELL_SKIP_GEMMA"] = "1"
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

    # Run stage
    label = f"[Stage {stage_id}] {stage['name']}"
    print(f"\n{'─'*60}")
    print(f"▶ {label}")
    print(f"{'─'*60}")

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(_PROJECT_ROOT),
            env={**__import__("os").environ, **env},
            capture_output=False,
            timeout=600,  # 10 min max per stage
        )
        elapsed = time.time() - start

        if result.returncode == 0:
            print(f"✅ {label} — {elapsed:.1f}s")
            return True
        else:
            print(f"❌ {label} — FAILED (exit code {result.returncode}) — {elapsed:.1f}s")
            return False
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"⏰ {label} — TIMEOUT ({elapsed:.1f}s)")
        return False
    except KeyboardInterrupt:
        print(f"\n⏸️  Pipeline interrupted at Stage {stage_id}")
        raise
    except Exception as e:
        elapsed = time.time() - start
        print(f"💥 {label} — ERROR: {e} — {elapsed:.1f}s")
        return False


def run_pipeline(
    *,
    resume_from: str | None = None,
    stages: list[str] | None = None,
    smoke: bool = False,
    skip_llm: bool = False,
    fast_model: str | None = None,
    skip_gemma: bool = False,
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
        skip_gemma: Skip Gemma deep check in Stage 5.
        domain: Filter books by domain directory.
        books: Limit number of books to process.
        quality: Quality tier (fast/balanced/maximum).
        dry_run: Print what would run without executing.
        stop_after: Stop after completing this stage.

    Returns:
        True if all stages completed successfully.
    """
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
            skip_gemma=skip_gemma,
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
            print(f"   Resume with: python -m pipeline.run --resume-from {stage_id}")
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

    return failed == 0


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point for PipelineRunner."""
    parser = argparse.ArgumentParser(
        description="Maxwell OS Pipeline Runner v3.0 (D2120)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m pipeline.run                           # Full pipeline, auto-resume
  python -m pipeline.run --smoke                   # Fast smoke test (<2min)
  python -m pipeline.run --smoke-plumbing          # Plumbing smoke (<30s, no LLM)
  python -m pipeline.run --resume-from stage2      # Resume after crash
  python -m pipeline.run --domain pricing          # Pricing domain only
  python -m pipeline.run --books 10                # Limit to 10 books
  python -m pipeline.run --dry-run                 # Show what would run
  python -m pipeline.run --quality fast            # Fast quality tier
  python -m pipeline.run --stages 1.5,2,4          # Specific stages only
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
    parser.add_argument("--skip-gemma", action="store_true",
                        help="Skip Gemma deep check in Stage 5")
    parser.add_argument("--run-id", type=str,
                        help="Override run_id (default: from config/env)")

    args = parser.parse_args()

    # Override run_id if specified
    if args.run_id:
        import os
        os.environ["MAXWELL_RUN_ID"] = args.run_id

    # Mode resolution
    is_plumbing = args.smoke_plumbing
    is_smoke = args.smoke or is_plumbing
    skip_llm = is_plumbing
    fast_model = args.fast_model if is_smoke else None
    skip_gemma = args.skip_gemma or is_smoke

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
        skip_gemma=skip_gemma,
        domain=args.domain,
        books=args.books,
        quality=args.quality,
        dry_run=args.dry_run,
        stop_after=args.stop_after,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
