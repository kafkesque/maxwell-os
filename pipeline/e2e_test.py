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
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Project root ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# D2312: pipeline_paths caches run_id at import time (default "latest").
# The e2e stages write to {stage}/e2e/ (MAXWELL_RUN_ID=e2e in run_stage), but
# validate_results() reads the module-level checkpoints — which would point at
# the stale "latest" dir. Set the run_id BEFORE importing pipeline_paths so the
# checkpoints resolve to the e2e run that was just executed.
os.environ.setdefault("MAXWELL_RUN_ID", "e2e")

from pipeline.pipeline_paths import (
    DB_PATH,
    STAGE1_5_CHECKPOINT,
    STAGE2_CHECKPOINT,
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    STAGE6_CHECKPOINT,
    get_run_id,
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
    from pipeline.pipeline_paths import (
        E2E_CORPUS_AWARE_PASS_RATE as _E2E_CORPUS_AWARE_PASS_RATE_CFG,
    )
    from pipeline.pipeline_paths import (
        E2E_CONVERGENT_MIN_PASS_RATE as _E2E_CONVERGENT_MIN_PASS_RATE_CFG,
    )
    from pipeline.pipeline_paths import (
        E2E_SINGLE_SOURCE_MIN_PASS_RATE as _E2E_SINGLE_SOURCE_MIN_PASS_RATE_CFG,
    )
    BORP_MIN_SOURCES: int = E2E_BORP_MIN_SOURCES
    E2E_MIN_PASS_RATE: float = _E2E_MIN_PASS_RATE_CFG
    E2E_MIN_FBS: int = _E2E_MIN_FBS_CFG
    E2E_CONVERGENT_RATIO: float = _E2E_CONVERGENT_RATIO_CFG
    E2E_CORPUS_AWARE_PASS_RATE: bool = _E2E_CORPUS_AWARE_PASS_RATE_CFG
    E2E_CONVERGENT_MIN_PASS_RATE: float = _E2E_CONVERGENT_MIN_PASS_RATE_CFG
    E2E_SINGLE_SOURCE_MIN_PASS_RATE: float = _E2E_SINGLE_SOURCE_MIN_PASS_RATE_CFG
except (ImportError, AttributeError):
    BORP_MIN_SOURCES = 2
    E2E_MIN_PASS_RATE = 0.80
    E2E_MIN_FBS = 30
    E2E_CONVERGENT_RATIO = 0.25
    E2E_CORPUS_AWARE_PASS_RATE = False
    E2E_CONVERGENT_MIN_PASS_RATE = 0.25
    E2E_SINGLE_SOURCE_MIN_PASS_RATE = 0.20


# D2311/C12: per-stage timeout from pipeline_config.yaml (no hardcoded 600s).
# Mirror runner.py's _get_stage_timeout (D2269). S2 extraction = null (unlimited)
# because the 30B generator needs far more than 10min on 20 books.
_STAGE_ID_BY_SCRIPT = {
    "stage0_convert.py": "0",
    "stage0_5_extract_metadata.py": "0.5",
    "stage1_chunk.py": "1",
    "stage1_3_prefilter.py": "1.3",
    "stage1_5_embed_cluster.py": "1.5",
    "stage2_extract.py": "2",
    "stage4_merge.py": "4",
    "stage5_verify.py": "5",
    "stage6_commit.py": "6",
}

# D2327: mirror runner.py — S1.3 prefilter defaults to dry-run; pass --in-place
# so structural garbage is actually filtered before S1.5 (was a silent no-op in e2e).
_STAGE_EXTRA_ARGS: dict[str, list[str]] = {
    "stage1_3_prefilter.py": ["--in-place"],
}


def _get_stage_timeout(stage_script: str) -> float | None:
    """D2311: Read per-stage timeout from config; fall back to 3600s.

    Returns None for unlimited (S2 `null`), matching runner.py semantics.
    """
    stage_id = _STAGE_ID_BY_SCRIPT.get(stage_script, "0")
    try:
        import yaml as _yaml_timeout
        _cfg_path = PROJECT_ROOT / "config" / "pipeline_config.yaml"
        with open(_cfg_path) as _f:
            _cfg = _yaml_timeout.safe_load(_f) or {}
        _timeouts = _cfg.get("stages", {}).get("timeouts", {})
        return _timeouts.get(stage_id, 3600.0)
    except Exception:
        return 3600.0


def run_stage(stage_script: str, quality: str = "balanced", books: int = 20, subdir: str | None = None) -> bool:
    """Run a single pipeline stage via subprocess.

    Stages are configured via MAXWELL_* env vars, NOT CLI flags (matches the
    smoke-fast justfile target). The stage scripts do NOT accept --quality/--books;
    those map to MAXWELL_RUN_ID / MAXWELL_BOOK_LIMIT / MAXWELL_FAST_MODEL.
    """
    start = time.time()
    env = dict(os.environ)
    env["MAXWELL_RUN_ID"] = "e2e"
    env["MAXWELL_BOOK_LIMIT"] = str(books)  # read by stage0 / stage0_5 / stage1_chunk
    if subdir:
        env["MAXWELL_BOOK_SUBDIR"] = subdir  # D2316: domain-coherent book sampling
    if quality == "fast":
        # D2120 smoke-fast pattern. NOTE: MAXWELL_FAST_MODEL is currently
        # set-but-not-consumed (fast-model wiring gap, see BUG-085 audit) — harmless
        # here, retained for forward-compat with runner.py's smoke path.
        env["MAXWELL_FAST_MODEL"] = "Phi-4-mini-instruct-8bit"
        env["MAXWELL_SKIP_GEMMA"] = "1"
    stage_timeout = _get_stage_timeout(stage_script)
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "pipeline" / stage_script), *_STAGE_EXTRA_ARGS.get(stage_script, [])],
        capture_output=True,
        text=True,
        timeout=stage_timeout,  # D2311: config-driven (S2=null/unlimited)
        cwd=str(PROJECT_ROOT),
        env=env,
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
    # D2347: convergence gates on canonical work identity (`is_convergent`, computed
    # by resolve_source_ids() → author|title), NOT filename diversity. Filename
    # diversity can be inflated by duplicate editions and is reported only as a
    # diagnostic alongside the canonical metric.
    if STAGE1_5_CHECKPOINT.exists():
        clusters = _load_jsonl(STAGE1_5_CHECKPOINT)
        total = len(clusters)
        convergent = sum(1 for c in clusters if c.get("is_convergent") is True)
        by_filename = sum(1 for c in clusters if len(set(c.get("source_books", []))) >= BORP_MIN_SOURCES)
        ratio = convergent / total if total else 0
        ok = ratio >= E2E_CONVERGENT_RATIO
        results["checks"].append({
            "check": "convergent_clusters",
            "value": f"{convergent}/{total} canonical ({ratio:.1%}; {by_filename}/{total} by-filename)",
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
        with_multi = sum(1 for fb in fbs if isinstance(fb.get("domains"), list) and len(fb["domains"]) > 0)
        with_edges = sum(1 for fb in fbs if fb.get("related_fbs"))
        results["checks"].append({
            "check": "multi_label",
            "value": f"{with_multi}/{count} have domains list",
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
        if E2E_CORPUS_AWARE_PASS_RATE:
            # D2531: corpus-aware gate — each origin tier vs its own observed floor.
            # origin == "convergent" (or is_convergent True) is the NLI-verifiable
            # tier; single_source FBs are structurally less entailable (weak/absent
            # cross-source evidence), so they get a lower floor. This is OPT-IN:
            # the legacy single-threshold path below remains the default.
            conv = [fb for fb in fbs if fb.get("origin") == "convergent" or fb.get("is_convergent") is True]
            ss = [fb for fb in fbs if fb not in conv]

            def _rate(items: list[dict]) -> float:
                return sum(1 for fb in items if fb.get("status") == "PASS") / len(items) if items else 0.0

            conv_rate = _rate(conv)
            ss_rate = _rate(ss)
            conv_ok = conv_rate >= E2E_CONVERGENT_MIN_PASS_RATE
            ss_ok = ss_rate >= E2E_SINGLE_SOURCE_MIN_PASS_RATE
            ok = conv_ok and ss_ok
            results["checks"].append({
                "check": "verify_pass_rate",
                "value": (
                    f"{passed}/{count} overall ({rate:.1%}); "
                    f"convergent {_rate(conv):.1%} (≥{E2E_CONVERGENT_MIN_PASS_RATE:.0%} "
                    f"{'✓' if conv_ok else '✗'}); "
                    f"single-source {_rate(ss):.1%} (≥{E2E_SINGLE_SOURCE_MIN_PASS_RATE:.0%} "
                    f"{'✓' if ss_ok else '✗'})"
                ),
                "threshold": "corpus-aware (D2531, opt-in)",
                "passed": ok,
            })
        else:
            ok = rate >= E2E_MIN_PASS_RATE
            results["checks"].append({
                "check": "verify_pass_rate",
                "value": f"{passed}/{count} ({rate:.1%})",
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
        results["checks"].append({"check": "db_commit", "value": "checkpoint written", "threshold": "written", "passed": True})
    else:
        results["checks"].append({"check": "db_commit", "value": "no checkpoint", "threshold": "written", "passed": False})
        results["passed"] = False

    # Check 6: SQLite DB has rows (D2330: scoped to the current run_id —
    # a global COUNT(*) would count historical rows from prior runs, not this one).
    if DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        row_count = conn.execute(
            "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id = ?",
            (get_run_id(),),
        ).fetchone()[0]
        conn.close()
        ok = row_count >= E2E_MIN_FBS
        results["checks"].append({
            "check": "db_rows",
            "value": f"{row_count} (run_id={get_run_id()})",
            "threshold": f"≥{E2E_MIN_FBS}",
            "passed": ok,
        })
        if not ok:
            results["passed"] = False

        # Check 7: D2337 ontology round-trip — the D2323 axes + mechanism must
        # survive S4→S5→S6 into SQLite. A commit that silently drops these would
        # pass db_rows yet still be a degraded (lossy) corpus.
        conn = sqlite3.connect(str(DB_PATH))
        populated = conn.execute(
            "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id = ? "
            "AND (content_type IS NOT NULL AND content_type != '') "
            "AND (extraction_type IS NOT NULL AND extraction_type != '')",
            (get_run_id(),),
        ).fetchone()[0]
        conn.close()
        ontology_ok = row_count > 0 and populated >= row_count * 0.9
        results["checks"].append({
            "check": "db_ontology_roundtrip",
            "value": f"{populated}/{row_count} rows carry content_type+extraction_type",
            "threshold": "≥90%",
            "passed": ontology_ok,
        })
        if not ontology_ok:
            results["passed"] = False

        # Check 8 (diagnostic, non-gating): vector completeness — sqlite-vec must
        # not silently degrade (D2185). Reports vec_fbs coverage for the current
        # run; vector search falls back to FTS when vec_fbs is missing/partial.
        # NOT a data-loss gate (ChatGPT Seat 2 finding: degradation vs data loss).
        conn = sqlite3.connect(str(DB_PATH))
        try:
            vec_covered = conn.execute(
                "SELECT COUNT(*) FROM vec_fbs v "
                "JOIN fbs f ON v.rowid = f.rowid "
                "WHERE f.pipeline_run_id = ?",
                (get_run_id(),),
            ).fetchone()[0]
        except Exception:
            vec_covered = 0
        conn.close()
        results["checks"].append({
            "check": "vector_completeness",
            "value": f"{vec_covered}/{row_count} rows have vectors",
            "threshold": "diagnostic (FTS fallback if <100%)",
            "passed": True,  # diagnostic only — not a hard gate
        })
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
    parser.add_argument(
        "--subdir",
        default="DOMAIN 6 AI + Computing/ai+engineering+agents",
        help="Domain-coherent book subdirectory under books/ (D2316). "
             "Restricts the sample to one topic so cross-book convergence is meaningful.",
    )
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
    print(f"║  Subdir:    {args.subdir:<43}║")
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
        if not run_stage(stage, quality=args.quality, books=args.books, subdir=args.subdir):
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
        print(f"  {icon} {check['check']}: {check['value']} (need {check.get('threshold', '—')})")
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
