#!/usr/bin/env python3
"""
e2e_test.py — P1.5: 20-book end-to-end pipeline validation for Maxwell v3.0.
================================================================================
Authority: D2113, P1.5

Runs the full 8-stage pipeline on 20 books across multiple domains, validates:
  - All stages complete without crash
  - Stage 1.5 produces convergent clusters (≥2 books)
  - Stage 2 extracts convergent FBs with mechanism/boundary/consequence
  - Stage 4 multi-label classifies with relationship edges
  - Stage 5 verification passes with ≥80% PASS rate
  - Stage 6 commits to SQLite + Parquet without errors

Exit codes:
  0 — All validations passed
  1 — Pipeline stage failure
  2 — Quality thresholds not met
  3 — Configuration error

Usage:
    python3 pipeline/e2e_test.py                # Full test
    python3 pipeline/e2e_test.py --books 10     # Smaller scale
    python3 pipeline/e2e_test.py --quality fast # Fast models only
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# ── Project root ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_paths import (
    DB_PATH,
    STAGE1_5_CHECKPOINT,
    STAGE2_CHECKPOINT,
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    STAGE6_CHECKPOINT,
)

# ── Thresholds (T1.3: de-hardcoded — sourced from pipeline_config.yaml) ────
# Graceful fallback: if pipeline_paths can't provide e2e config, use defaults.
# This preserves the resilience of the original try/except pattern while
# centralizing config in pipeline_paths for the normal path.
try:
    from pipeline.pipeline_paths import (
        E2E_BORP_MIN_SOURCES,
    )
    from pipeline.pipeline_paths import (
        E2E_CONVERGENT_RATIO as _E2E_CONVERGENT_RATIO_CFG,
    )
    from pipeline.pipeline_paths import (
        E2E_MIN_FBS as _E2E_MIN_FBS_CFG,
    )
    from pipeline.pipeline_paths import (
        E2E_MIN_PASS_RATE as _E2E_MIN_PASS_RATE_CFG,
    )
    BORP_MIN_SOURCES: int = E2E_BORP_MIN_SOURCES
    E2E_MIN_PASS_RATE: float = _E2E_MIN_PASS_RATE_CFG
    E2E_MIN_FBS: int = _E2E_MIN_FBS_CFG
    E2E_CONVERGENT_RATIO: float = _E2E_CONVERGENT_RATIO_CFG
except (ImportError, AttributeError):
    BORP_MIN_SOURCES = 2
    E2E_MIN_PASS_RATE = 0.80
    E2E_MIN_FBS = 30
    E2E_CONVERGENT_RATIO = 0.25


def run_stage(stage_script: str, quality: str = "balanced", books: int = 20) -> bool:
    """Run a single pipeline stage via subprocess."""
    start = time.time()
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "pipeline" / stage_script),
            "--quality", quality,
            "--books", str(books),
        ],
        capture_output=True,
        text=True,
        timeout=600,  # 10min per stage
        cwd=str(PROJECT_ROOT),
    )
    elapsed = time.time() - start
    status = "✅" if result.returncode == 0 else "❌"
    print(f"   {status} {stage_script} ({elapsed:.1f}s, rc={result.returncode})")
    if result.returncode != 0:
        print(f"   STDERR: {result.stderr[:500]}")
    return result.returncode == 0


def validate_results() -> dict:
    """Validate pipeline outputs against quality thresholds."""
    results: dict = {"passed": True, "checks": []}

    # Check 1: Stage 1.5 convergent clusters
    if STAGE1_5_CHECKPOINT.exists():
        clusters = _load_jsonl(STAGE1_5_CHECKPOINT)
        total = len(clusters)
        convergent = sum(1 for c in clusters if len(set(c.get("source_books", []))) >= BORP_MIN_SOURCES)
        ratio = convergent / total if total else 0
        ok = ratio >= E2E_CONVERGENT_RATIO
        results["checks"].append({
            "check": "convergent_clusters",
            "value": f"{convergent}/{total} ({ratio:.0%})",
            "threshold": f"≥{E2E_CONVERGENT_RATIO:.0%}",
            "passed": ok,
        })
        if not ok:
            results["passed"] = False
    else:
        results["checks"].append({"check": "convergent_clusters", "value": "no checkpoint", "passed": False})
        results["passed"] = False

    # Check 2: Stage 2 FB count
    if STAGE2_CHECKPOINT.exists():
        fbs = _load_jsonl(STAGE2_CHECKPOINT)
        count = len(fbs)
        ok = count >= E2E_MIN_FBS
        results["checks"].append({
            "check": "fb_count",
            "value": str(count),
            "threshold": f"≥{E2E_MIN_FBS}",
            "passed": ok,
        })
        if not ok:
            results["passed"] = False

        # Check mechanism/boundary/consequence presence
        with_mechanism = sum(1 for fb in fbs if fb.get("mechanism") or fb.get("application"))
        with_boundary = sum(1 for fb in fbs if fb.get("boundary") or fb.get("failure_mode"))
        results["checks"].append({
            "check": "fb_fields",
            "value": f"mechanism={with_mechanism}/{count}, boundary={with_boundary}/{count}",
            "threshold": "≥70%",
            "passed": with_mechanism / count >= 0.7 and with_boundary / count >= 0.7,
        })
    else:
        results["checks"].append({"check": "fb_count", "value": "no checkpoint", "passed": False})
        results["passed"] = False

    # Check 3: Stage 4 multi-label + relationship edges
    if STAGE4_CHECKPOINT.exists():
        fbs = _load_jsonl(STAGE4_CHECKPOINT)
        count = len(fbs)
        with_multi = sum(1 for fb in fbs if isinstance(fb.get("disciplines"), list) and len(fb["disciplines"]) > 0)
        with_edges = sum(1 for fb in fbs if fb.get("related_fbs"))
        results["checks"].append({
            "check": "multi_label",
            "value": f"{with_multi}/{count} have disciplines list",
            "threshold": "≥90%",
            "passed": with_multi / count >= 0.9 if count else False,
        })
        results["checks"].append({
            "check": "relationship_edges",
            "value": f"{with_edges}/{count} have related_fbs",
            "threshold": ">0",
            "passed": with_edges > 0,
        })
    else:
        results["checks"].append({"check": "stage4", "value": "no checkpoint", "passed": False})
        results["passed"] = False

    # Check 4: Stage 5 pass rate
    if STAGE5_CHECKPOINT.exists():
        fbs = _load_jsonl(STAGE5_CHECKPOINT)
        count = len(fbs)
        passed = sum(1 for fb in fbs if fb.get("status") == "PASS")
        rate = passed / count if count else 0
        ok = rate >= E2E_MIN_PASS_RATE
        results["checks"].append({
            "check": "verify_pass_rate",
            "value": f"{passed}/{count} ({rate:.0%})",
            "threshold": f"≥{E2E_MIN_PASS_RATE:.0%}",
            "passed": ok,
        })
        if not ok:
            results["passed"] = False
    else:
        results["checks"].append({"check": "verify_pass_rate", "value": "no checkpoint", "passed": False})
        results["passed"] = False

    # Check 5: Stage 6 commit
    if STAGE6_CHECKPOINT.exists():
        results["checks"].append({"check": "db_commit", "value": "checkpoint written", "passed": True})
    else:
        results["checks"].append({"check": "db_commit", "value": "no checkpoint", "passed": False})
        results["passed"] = False

    # Check 6: SQLite DB has rows
    if DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        row_count = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
        conn.close()
        ok = row_count >= E2E_MIN_FBS
        results["checks"].append({
            "check": "db_rows",
            "value": str(row_count),
            "threshold": f"≥{E2E_MIN_FBS}",
            "passed": ok,
        })
        if not ok:
            results["passed"] = False
    else:
        results["checks"].append({"check": "db_rows", "value": "no database", "passed": False})
        results["passed"] = False

    return results


def _load_jsonl(path: Path) -> list[dict]:
    """Load JSONL file, return list of dicts."""
    items = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def main():
    parser = argparse.ArgumentParser(description="P1.5: 20-book E2E pipeline test")
    parser.add_argument("--books", type=int, default=20, help="Number of books (default: 20)")
    parser.add_argument("--quality", default="balanced", choices=["fast", "balanced", "maximum"])
    parser.add_argument("--dry-run", action="store_true", help="Print stages without running")
    args = parser.parse_args()

    stages = [
        "stage0_convert.py",
        "stage0_5_extract_metadata.py",
        "stage1_chunk.py",
        "stage1_3_prefilter.py",
        "stage1_5_embed_cluster.py",
        "stage2_extract.py",
        "stage4_merge.py",
        "stage5_verify.py",
        "stage6_commit.py",
    ]

    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║     Maxwell v3.0 — P1.5: {args.books}-Book E2E Test              ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║  Books:     {args.books:<43}║")
    print(f"║  Quality:   {args.quality:<43}║")
    print("║  Stages:    9 (0→0.5→1→1.3→1.5→2→4→5→6)              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    if args.dry_run:
        print("📋 DRY RUN — no stages executed.")
        for s in stages:
            print(f"   [DRY] {s}")
        return 0

    # ── Run all stages ─────────────────────────────────────────────────
    start = time.time()
    failed_stages = []

    for stage in stages:
        if not run_stage(stage, quality=args.quality, books=args.books):
            failed_stages.append(stage)
            print(f"\n   ⛔ Pipeline halted at {stage}")
            break

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"Pipeline: {len(stages) - len(failed_stages)}/{len(stages)} stages passed ({elapsed:.0f}s)")

    if failed_stages:
        print(f"❌ FAILED stages: {', '.join(failed_stages)}")
        return 1

    # ── Validate results ───────────────────────────────────────────────
    print("\n🔍 Validating output quality...")
    results = validate_results()

    print(f"\n{'─'*60}")
    all_ok = True
    for check in results["checks"]:
        icon = "✅" if check["passed"] else "❌"
        print(f"  {icon} {check['check']}: {check['value']} (need {check['threshold']})")
        if not check["passed"]:
            all_ok = False

    if all_ok:
        print(f"\n✅ E2E TEST PASSED — all {len(results['checks'])} checks green")
        return 0
    else:
        print("\n❌ E2E TEST FAILED — quality thresholds not met")
        return 2


if __name__ == "__main__":
    sys.exit(main())
