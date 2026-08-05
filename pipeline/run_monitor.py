#!/usr/bin/env python3
"""
run_monitor.py — Automatic per-run metrics collector for Maxwell pipeline.
================================================================================
Authority: C16 (no silent errors), C24 (hardware-adaptive)

Hooks into every pipeline run to collect:
  - Per-stage timing (wall clock)
  - LLM call latency + token counts (via OMLX API introspection)
  - Memory pressure (psutil)
  - Error counts + classification
  - Output quality: FB count, convergent ratio, multi-label rate, edge density
  - Hardware: RAM usage, swap, CPU load

Writes to: knowledge pipeline/metrics/{run_id}.jsonl (one line per stage)
Also appends to: knowledge pipeline/metrics/run_history.jsonl (aggregate)

Usage:
    # Wrap any pipeline run:
    python3 pipeline/run_monitor.py -- just smoke
    python3 pipeline/run_monitor.py -- python3 pipeline/runner.py --books 5
    python3 pipeline/run_monitor.py --output run_report.json -- just smoke-fast
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# D2175: Use DATA_DIR from pipeline_paths — no hardcoded paths (C12a)
from pipeline.pipeline_paths import DATA_DIR
PROJECT_ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = DATA_DIR / "metrics"


def detect_hardware() -> dict:
    """Detect hardware capabilities (C24)."""
    import psutil
    mem = psutil.virtual_memory()
    return {
        "total_ram_gb": round(mem.total / (1024**3), 1),
        "available_ram_gb": round(mem.available / (1024**3), 1),
        "ram_percent": mem.percent,
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_physical": psutil.cpu_count(logical=False),
        "swap_total_gb": round(psutil.swap_memory().total / (1024**3), 1) if hasattr(psutil, 'swap_memory') else 0,
    }


def sample_omlx_metrics() -> dict | None:
    """Sample OMLX metrics from health endpoint."""
    try:
        import requests
        r = requests.get("http://localhost:11435/health", timeout=3)
        if r.status_code == 200:
            data = r.json()
            pool = data.get("engine_pool", {})
            return {
                "omlx_loaded_models": pool.get("loaded_count", 0),
                "omlx_model_memory_gb": round(pool.get("current_model_memory", 0) / (1024**3), 1),
                "omlx_ceiling_gb": round(pool.get("final_ceiling", 0) / (1024**3), 1),
            }
    except Exception:
        pass
    return None


def sample_memory() -> dict:
    """Sample current memory pressure."""
    import psutil
    mem = psutil.virtual_memory()
    proc = psutil.Process()
    return {
        "ram_used_percent": mem.percent,
        "ram_available_gb": round(mem.available / (1024**3), 1),
        "process_rss_gb": round(proc.memory_info().rss / (1024**3), 2),
        "swap_used_gb": round(psutil.swap_memory().used / (1024**3), 1) if hasattr(psutil, 'swap_memory') else 0,
        "cpu_percent": psutil.cpu_percent(interval=0.1),
    }


def analyze_stage_output(stage_name: str, run_id: str) -> dict:
    """Post-stage analysis of checkpoint quality."""
    # D2175: Use DATA_DIR from pipeline_paths — no hardcoded paths (C12a)
    checkpoint_dir = DATA_DIR / "checkpoints"
    stage_map = {
        "stage0_convert": "stage0_convert",
        "stage0_5_extract_metadata": "stage0_5_extract_metadata",
        "stage1_chunk": "stage1_chunk",
        "stage1_3_prefilter": "stage1_3_prefilter",
        "stage1_5_embed_cluster": "stage1_5_embed_cluster",
        "stage2_extract": "stage2_extract",
        "stage4_merge": "stage4_merge",
        "stage5_verify": "stage5_verify",
        "stage6_commit": "stage6_commit",
    }
    metrics: dict = {}

    for short_name, dir_name in stage_map.items():
        if short_name not in stage_name:
            continue
        checkpoint_file = checkpoint_dir / dir_name / run_id / "checkpoint.jsonl"
        if not checkpoint_file.exists():
            continue

        try:
            items = []
            with open(checkpoint_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        items.append(json.loads(line))

            if not items:
                break

            metrics["output_count"] = len(items)

            # Stage-specific metrics
            if "stage1_5" in stage_name:
                convergent = sum(1 for c in items
                                 if len(set(c.get("source_books", []))) >= 2)
                metrics["convergent_clusters"] = convergent
                metrics["convergent_ratio"] = round(convergent / len(items), 3) if items else 0

            elif "stage2" in stage_name:
                with_mechanism = sum(1 for fb in items if fb.get("mechanism") or fb.get("application"))
                with_boundary = sum(1 for fb in items if fb.get("boundary") or fb.get("failure_mode"))
                metrics["with_mechanism"] = with_mechanism
                metrics["with_boundary"] = with_boundary

            elif "stage4" in stage_name:
                multi_label = sum(1 for fb in items if isinstance(fb.get("disciplines"), list))
                with_edges = sum(1 for fb in items if fb.get("related_fbs"))
                total_edges = sum(len(fb.get("related_fbs", [])) for fb in items)
                metrics["multi_label_count"] = multi_label
                metrics["fbs_with_edges"] = with_edges
                metrics["total_edges"] = total_edges
                metrics["avg_edges_per_fb"] = round(total_edges / len(items), 2) if items else 0
                domains_per_fb = [len(fb.get("domains", [])) for fb in items]
                metrics["avg_domains_per_fb"] = round(sum(domains_per_fb) / len(domains_per_fb), 2) if domains_per_fb else 0
                depths = {}
                for fb in items:
                    d = fb.get("depth", "unknown")
                    depths[d] = depths.get(d, 0) + 1
                metrics["depth_distribution"] = depths

            elif "stage5" in stage_name:
                statuses = {}
                for fb in items:
                    s = fb.get("status", "UNKNOWN")
                    statuses[s] = statuses.get(s, 0) + 1
                metrics["verification_statuses"] = statuses
                pass_rate = statuses.get("PASS", 0) / len(items) if items else 0
                metrics["pass_rate"] = round(pass_rate, 3)
                borp_scores = [fb.get("borp_score", 0) for fb in items]
                metrics["avg_borp_score"] = round(sum(borp_scores) / len(borp_scores), 3) if borp_scores else 0

        except Exception as e:
            metrics["analysis_error"] = str(e)[:200]

        break  # Only analyze the matching stage

    return metrics


def monitor_run(cmd: list[str], run_id: str | None = None) -> dict:
    """Run a pipeline command with full instrumentation.

    Returns a dict with all collected metrics for the run.
    """
    if run_id is None:
        run_id = f"monitor-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    run_start = time.time()
    hardware = detect_hardware()
    omlx_before = sample_omlx_metrics()

    print(f"\n{'='*70}")
    print(f"  Maxwell Run Monitor — {run_id}")
    print(f"  Hardware: {hardware['total_ram_gb']}GB RAM, {hardware['cpu_count']} CPUs")
    if omlx_before:
        print(f"  OMLX: {omlx_before['omlx_loaded_models']} models, "
              f"{omlx_before['omlx_model_memory_gb']}GB / {omlx_before['omlx_ceiling_gb']}GB")
    print(f"  Cmd: {' '.join(cmd)}")
    print(f"{'='*70}\n")

    # Set run ID for pipeline stages to use
    os.environ["MAXWELL_RUN_ID"] = run_id

    # Run the command with live output
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(PROJECT_ROOT),
        bufsize=1,
    )

    stage_times: dict[str, float] = {}
    current_stage: str | None = None
    stage_start: float = time.time()
    llm_calls: int = 0
    errors_seen: int = 0
    all_output: list[str] = []

    STAGE_MARKERS = {
        "Stage 0: Convert": "stage0_convert",
        "Stage 0.5": "stage0_5",
        "Stage 1: Chunk": "stage1_chunk",
        "Stage 1.3": "stage1_3",
        "Stage 1.5": "stage1_5",
        "Stage 2: Extract": "stage2_extract",
        "Stage 4: Merge": "stage4_merge",
        "Stage 5: Verify": "stage5_verify",
        "Stage 6: Commit": "stage6_commit",
    }

    for line in proc.stdout:
        line = line.rstrip()
        all_output.append(line)
        print(line)

        # Detect stage transitions
        for marker, stage_id in STAGE_MARKERS.items():
            if marker in line and "Stage" in line[:20]:
                if current_stage and current_stage != stage_id:
                    elapsed = time.time() - stage_start
                    stage_times[current_stage] = round(elapsed, 2)
                current_stage = stage_id
                stage_start = time.time()
                break

        # Count LLM calls (🤖 emoji or "Model:" lines)
        if "🤖" in line or "call_omlx" in line.lower():
            llm_calls += 1

        # Count errors
        if any(e in line.lower() for e in ["error", "failed", "❌", "traceback", "exception"]):
            errors_seen += 1

    proc.wait()
    if current_stage:
        stage_times[current_stage] = round(time.time() - stage_start, 2)

    total_elapsed = time.time() - run_start
    omlx_after = sample_omlx_metrics()
    memory_after = sample_memory()

    # Post-run analysis
    stage_analyses: dict[str, dict] = {}
    for stage_name in stage_times:
        analysis = analyze_stage_output(stage_name, run_id)
        if analysis:
            stage_analyses[stage_name] = analysis

    # Build report
    report = {
        "run_id": run_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "total_elapsed_s": round(total_elapsed, 1),
        "hardware": hardware,
        "omlx_before": omlx_before,
        "omlx_after": omlx_after,
        "memory_after": memory_after,
        "stage_times": stage_times,
        "stage_analyses": stage_analyses,
        "llm_calls_estimated": llm_calls,
        "errors_seen": errors_seen,
    }

    # Write per-run metrics
    run_file = METRICS_DIR / f"{run_id}.json"
    with open(run_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Append to history
    history_file = METRICS_DIR / "run_history.jsonl"
    history_entry = {
        "run_id": run_id,
        "timestamp": report["timestamp"],
        "exit_code": proc.returncode,
        "total_elapsed_s": report["total_elapsed_s"],
        "stage_count": len(stage_times),
        "llm_calls": llm_calls,
        "errors": errors_seen,
        "memory_percent": memory_after.get("ram_used_percent", 0) if memory_after else 0,
        "stage_analyses_summary": {
            k: {kk: vv for kk, vv in v.items() if kk in ("output_count", "pass_rate", "convergent_ratio", "multi_label_count", "total_edges")}
            for k, v in stage_analyses.items()
        },
    }
    with open(history_file, "a") as f:
        f.write(json.dumps(history_entry, default=str) + "\n")

    # Print summary
    print(f"\n{'='*70}")
    print(f"  📊 RUN SUMMARY — {run_id}")
    print(f"  Exit: {proc.returncode} | Time: {total_elapsed:.1f}s | LLM calls: ~{llm_calls} | Errors: {errors_seen}")
    print(f"  Memory: {memory_after['ram_used_percent']}% | Process RSS: {memory_after['process_rss_gb']}GB" if memory_after else "")
    print(f"  Stage times:")
    for stage, elapsed in stage_times.items():
        analysis = stage_analyses.get(stage, {})
        extras = ""
        if "output_count" in analysis:
            extras = f" → {analysis['output_count']} items"
        if "pass_rate" in analysis:
            extras += f", {analysis['pass_rate']:.0%} PASS"
        if "multi_label_count" in analysis:
            extras += f", {analysis['multi_label_count']}/{analysis.get('output_count', 1)} multi-label"
        if "total_edges" in analysis:
            extras += f", {analysis['total_edges']} edges"
        print(f"    {stage:30s} {elapsed:>6.1f}s{extras}")
    print(f"  Report: {run_file}")
    print(f"{'='*70}\n")

    return report


def main():
    parser = argparse.ArgumentParser(description="Maxwell Run Monitor — automatic per-run metrics")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (after -- separator)")
    parser.add_argument("--run-id", help="Override run ID")
    parser.add_argument("--output", help="Save report to specific file")
    args = parser.parse_args()

    if not args.cmd:
        print("Usage: python3 pipeline/run_monitor.py -- <pipeline command>")
        print("  e.g.: python3 pipeline/run_monitor.py -- just smoke")
        sys.exit(1)

    report = monitor_run(args.cmd, run_id=args.run_id)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to: {args.output}")

    sys.exit(report["exit_code"])


if __name__ == "__main__":
    main()
