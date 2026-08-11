#!/usr/bin/env python3
"""
run_diagnostic.py — E2E Diagnostic Gate (D2261).
=================================================
Runs S2→S6 on a random sample of N books through the FULL v3.0 pipeline:
  S2: Convergent extraction (DeBERTa FEVER NLI active, D2255)
  S4: Merge + classify + depth (GPT-OSS-20B, D2250)
  S5: Verify (DeBERTa FEVER NLI + Phi-4-mini + BORP, D2264)
  S6: Commit (SQLite + Parquet export)

Output: governance/e2e_diagnostic_YYYY-MM-DD.md — human-readable report
with every FB's full properties (definition, mechanism, boundary, consequence,
elaboration, application, failure_mode, keywords, jargon, metadata).

Gate criteria (D2261):
  - Yield >1% AND S5 pass rate >40% → APPROVE T1.1 full run
  - Yield <0.5% OR S5 pass rate <20% → HALT, diagnose
  - Between → judgment call

Usage:
  python3 pipeline/run_diagnostic.py --books 100
  python3 pipeline/run_diagnostic.py --books 50 --run-id diag_quick
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Resolve project root BEFORE any Maxwell imports ─────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

# ── Load pipeline config for defaults (before Maxwell imports) ─────────
import yaml as _yaml
_CFG_PATH = PROJECT_ROOT / "config" / "pipeline_config.yaml"
with open(_CFG_PATH) as _f:
    _PIPELINE_CFG = _yaml.safe_load(_f)
_DIAG_CFG = _PIPELINE_CFG.get("e2e", {}).get("diagnostic", {})
_DEFAULT_BOOKS = _DIAG_CFG.get("default_books", 100)
_QUICK_CLUSTERS = _DIAG_CFG.get("quick_clusters", 50)

# ── Parse args early (before pipeline_paths import) ────────────────────
parser = argparse.ArgumentParser(description="E2E diagnostic gate (D2261)")
parser.add_argument("--books", type=int, default=None,
                    help=f"Number of books to sample (default: {_DEFAULT_BOOKS} from config)")
parser.add_argument("--run-id", type=str, default=None,
                    help="Diagnostic run ID (default: auto-generated with timestamp)")
parser.add_argument("--seed", type=int, default=42,
                    help="Random seed for book sampling (default: 42)")
parser.add_argument("--only-convergent", action="store_true",
                    help="Only process convergent clusters (faster, ~20% of total)")
parser.add_argument("--max-clusters", type=int, default=None,
                    help="Cap total clusters processed (limits runtime)")
parser.add_argument("--quick", action="store_true",
                    help=f"Quick mode: {_QUICK_CLUSTERS} convergent clusters only (~30min).")
parser.add_argument("--no-probe", action="store_true",
                    help="Skip split probe (faster, ~50% less S2 time)")
parser.add_argument("--s4-limit", type=int, default=None,
                    help="Limit FBs through S4/S5/S6 (faster eval, default: all)")
parser.add_argument("--dry-run", action="store_true",
                    help="Show what would run without executing")
args = parser.parse_args()

# ── Set run_id before Maxwell imports (pipeline_paths reads it at import) ──
RUN_ID = args.run_id or f"diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.environ["MAXWELL_RUN_ID"] = RUN_ID

# Now safe to import Maxwell modules
from pipeline.pipeline_paths import (
    S15_DIR,
    CHECKPOINT_DIR,
    DATA_DIR,
    PROJECT_ROOT as _PR,
)

# ── Checkpoint/Resume Infrastructure ─────────────────────────────────────
# D2264: The diagnostic MUST survive interruption. State is tracked in
# governance/diagnostic_state.json. On restart, completed stages are skipped.
_DEFAULT_RUN_ID = _PIPELINE_CFG.get("run", {}).get("default_id", "latest")
_DIAG_STATE_FILE = PROJECT_ROOT / "governance" / "diagnostic_state.json"

def _get_diag_state_path() -> Path:
    """Get run-specific diagnostic state file path."""
    return PROJECT_ROOT / "governance" / f"diagnostic_state_{RUN_ID}.json"

# ── Process Guard (D2266): PID file locking prevents multiple diagnostics ──
_PID_FILE = PROJECT_ROOT / ".diagnostic_pid"
_CAFFEINATE_PID_FILE = PROJECT_ROOT / ".caffeinate_pid"

def _acquire_process_lock() -> bool:
    """Acquire PID file lock. Returns True if lock acquired, False if another
    diagnostic is already running. Auto-clears stale locks (dead PIDs).

    D2266: Prevents 5+ simultaneous diagnostic processes that congest OMLX,
    corrupt checkpoints, and waste hours of compute.
    """
    import os as _ospid
    if _PID_FILE.exists():
        try:
            old_pid = int(_PID_FILE.read_text().strip())
            # Check if old process is still alive
            try:
                _ospid.kill(old_pid, 0)  # Signal 0 = check existence
                print(f"🛑 ANOTHER diagnostic is already running (PID {old_pid}).")
                print(f"   Kill it first: kill {old_pid}")
                print(f"   Or remove stale lock: rm {_PID_FILE}")
                return False
            except (OSError, ProcessLookupError):
                # Stale lock — old process is dead, clean up
                print(f"🧹 Cleaning up stale PID file (PID {old_pid} is dead)")
                _PID_FILE.unlink(missing_ok=True)
        except (ValueError, FileNotFoundError):
            _PID_FILE.unlink(missing_ok=True)

    # Write current PID
    _PID_FILE.write_text(str(_ospid.getpid()))
    return True

def _release_process_lock() -> None:
    """Release the PID file lock. Called on normal exit."""
    import os as _ospid2
    try:
        if _PID_FILE.exists():
            stored = int(_PID_FILE.read_text().strip())
            if stored == _ospid2.getpid():
                _PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass

def _kill_stale_diagnostics() -> int:
    """Find and kill any other run_diagnostic processes (not this one).
    Returns count of killed processes.

    D2266: Safety net — if PID file is missing but diagnostic processes exist,
    kill them to prevent OMLX congestion.
    """
    import os as _ospid3, subprocess as _sp2
    killed = 0
    my_pid = _ospid3.getpid()
    try:
        result = _sp2.run(
            ["pgrep", "-f", "run_diagnostic.py"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            pid_str = line.strip()
            if pid_str and pid_str.isdigit():
                pid = int(pid_str)
                if pid != my_pid:
                    try:
                        _ospid3.kill(pid, 9)
                        killed += 1
                        print(f"🧹 Killed stale diagnostic process: PID {pid}")
                    except Exception:
                        pass
    except Exception:
        pass
    return killed

def _start_caffeinate() -> bool:
    """Start caffeinate to prevent laptop sleep/screensaver during diagnostic.

    D2267: On macOS, `caffeinate -i -d -s` prevents:
      -i: idle sleep
      -d: display sleep
      -s: system sleep
    Stores PID for cleanup on exit.
    Returns True if caffeinate started successfully.
    """
    import subprocess as _sp3, os as _ospid4
    if _ospid4.name != "posix" or not _ospid4.path.exists("/usr/bin/caffeinate"):
        return False
    try:
        proc = _sp3.Popen(
            ["/usr/bin/caffeinate", "-i", "-d", "-s"],
            stdout=_sp3.DEVNULL, stderr=_sp3.DEVNULL,
        )
        _CAFFEINATE_PID_FILE.write_text(str(proc.pid))
        print(f"☕ Caffeinate started (PID {proc.pid}) — laptop will NOT sleep")
        return True
    except Exception as e:
        print(f"⚠️ Could not start caffeinate: {e}")
        return False

def _stop_caffeinate() -> None:
    """Stop caffeinate after diagnostic completes."""
    import os as _ospid5
    try:
        if _CAFFEINATE_PID_FILE.exists():
            pid = int(_CAFFEINATE_PID_FILE.read_text().strip())
            _ospid5.kill(pid, 9)
            _CAFFEINATE_PID_FILE.unlink(missing_ok=True)
            print("☕ Caffeinate stopped — laptop may sleep normally")
    except Exception:
        pass

def _register_signal_handlers() -> None:
    """Register cleanup handlers for SIGINT (Ctrl+C) and SIGTERM.

    On Ctrl+C: saves diagnostic state as 'paused', cleans up PID/caffeinate.
    On restart with same --run-id: resumes from last completed stage.
    """
    import signal as _sig
    def _cleanup_handler(signum, frame):
        print(f"\n{'='*60}")
        print(f"⏸️  PAUSED — received signal {signum}")
        # Save pause state for resume awareness
        _ds = _load_diag_state()
        _ds["paused"] = True
        _ds["paused_at"] = datetime.now().isoformat()
        _save_diag_state(_ds)
        print(f"   State saved to governance/diagnostic_state.json")
        print(f"   Resume with: python3 pipeline/run_diagnostic.py --run-id {RUN_ID} --only-convergent --max-clusters {args.max_clusters or 'N'} --no-probe")
        print(f"   Already completed stages will be skipped automatically.")
        print(f"{'='*60}")
        _stop_caffeinate()
        _release_process_lock()
        sys.exit(0)
    _sig.signal(_sig.SIGINT, _cleanup_handler)
    _sig.signal(_sig.SIGTERM, _cleanup_handler)

def _load_diag_state() -> dict:
    """Load diagnostic checkpoint state for current run_id. Returns empty dict if no state exists."""
    import json as _json
    _path = _get_diag_state_path()
    if _path.exists():
        with open(_path) as f:
            return _json.load(f)
    return {}

def _save_diag_state(state: dict) -> None:
    """Atomically save diagnostic checkpoint state for current run_id (C6: crash-safe write)."""
    import json as _json, os as _os2
    _path = _get_diag_state_path()
    tmp = str(_path) + ".tmp"
    with open(tmp, "w") as f:
        _json.dump(state, f, indent=2, default=str)
    f.flush()
    _os2.fsync(f.fileno())
    _os2.replace(tmp, str(_path))

# Resolve the REAL S1.5 and S1 checkpoint paths using the default run_id
_REAL_S15_CHECKPOINT = S15_DIR / _DEFAULT_RUN_ID / "checkpoint.jsonl"
_S1_DIR = PROJECT_ROOT / _PIPELINE_CFG["stages"]["stage1_chunk"]
_S1_PROD_DIR = _S1_DIR / _DEFAULT_RUN_ID

# D2261 gate thresholds from config (C12: never hardcode)
_GATE_YIELD_PASS = _DIAG_CFG.get("yield_pct_pass", 1.0)
_GATE_YIELD_FAIL = _DIAG_CFG.get("yield_pct_fail", 0.5)
_GATE_S5_PASS = _DIAG_CFG.get("s5_pass_rate_pass", 0.40)
_GATE_S5_FAIL = _DIAG_CFG.get("s5_pass_rate_fail", 0.20)
from pipeline.stage2_extract import (
    load_golden_parity,
    format_golden_fewshot,
    S2_GOLDEN_PATH,
    S2_GOLDEN_POSITIVE,
    S2_GOLDEN_NEGATIVE,
    S2_GOLDEN_MAX,
    S2_GOLDEN_INJECT,
)
import pipeline.stage2_extract as s2
import pipeline.stage4_merge as s4
import pipeline.stage5_verify as s5
import pipeline.stage6_commit as s6

# ── Constants ───────────────────────────────────────────────────────────
OUTPUT_DIR = PROJECT_ROOT / "governance"
DIAGNOSTIC_S15_CHECKPOINT = S15_DIR / RUN_ID / "checkpoint.jsonl"


def _load_real_clusters() -> list[dict]:
    """Load clusters from the REAL S1.5 checkpoint (before run_id override)."""
    real_path = _REAL_S15_CHECKPOINT
    if not real_path.exists():
        print(f"❌ Real S1.5 checkpoint not found: {real_path}")
        sys.exit(1)
    clusters: list[dict] = []
    with open(real_path) as f:
        for line in f:
            line = line.strip()
            if line:
                clusters.append(json.loads(line))
    return clusters


def sample_books(n_books: int, seed: int) -> tuple[set[str], list[dict], list[dict]]:
    """Randomly sample N books from real clusters, return filtered convergent + single-source."""
    all_clusters = _load_real_clusters()

    # Collect all unique source books
    all_books: set[str] = set()
    for c in all_clusters:
        for b in c.get("source_books", []):
            all_books.add(b)

    print(f"📚 Total unique books in clusters: {len(all_books)}")

    # Sample N books
    rng = random.Random(seed)
    sampled = set(rng.sample(sorted(all_books), min(n_books, len(all_books))))
    print(f"🎲 Sampled {len(sampled)} books (seed={seed})")

    # Filter clusters whose source_books overlap with sampled books
    convergent: list[dict] = []
    single_source: list[dict] = []
    noise_count = 0

    for c in all_clusters:
        c_books = set(c.get("source_books", []))
        if not (c_books & sampled):
            continue
        if c.get("is_noise", False):
            noise_count += 1
            continue
        if c.get("is_convergent", False):
            convergent.append(c)
        else:
            single_source.append(c)

    # Count affected books
    affected_books: set[str] = set()
    for c in convergent + single_source:
        affected_books.update(c.get("source_books", []))

    print(f"📊 Clusters touching sampled books: {len(convergent)} convergent + {len(single_source)} single-source "
          f"({noise_count} noise skipped)")
    print(f"   These clusters span {len(affected_books)} unique books (convergent clusters are multi-book by definition)")

    return sampled, convergent, single_source


def write_diagnostic_clusters(convergent: list[dict], single_source: list[dict]) -> int:
    """Write filtered clusters to diagnostic S1.5 checkpoint."""
    # Safety: verify run_id is confirmed before writing (never overwrite production "latest")
    diag_path = DIAGNOSTIC_S15_CHECKPOINT
    if diag_path.parent.name == _DEFAULT_RUN_ID:
        raise RuntimeError(
            f"REFUSING: diagnostic run_id '{RUN_ID}' matches production default '{_DEFAULT_RUN_ID}'. "
            f"Would overwrite production checkpoint at {diag_path}. Use --run-id to specify a different ID."
        )
    diag_path.parent.mkdir(parents=True, exist_ok=True)
    all_filtered = convergent + single_source
    with open(diag_path, "w") as f:
        for c in all_filtered:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"💾 Wrote {len(all_filtered)} clusters to {DIAGNOSTIC_S15_CHECKPOINT}")
    return len(all_filtered)


def _unload_omlx_model(model_name: str) -> None:
    """Unload a model from OMLX to free memory for next stage."""
    import urllib.request
    try:
        req = urllib.request.Request(
            f"http://localhost:11435/v1/models/{model_name}/unload",
            method="POST",
            headers={"Authorization": "Bearer sk-maxwell-local"},
        )
        urllib.request.urlopen(req, timeout=10)
        print(f"   🗑️  Unloaded {model_name}")
    except Exception as e:
        print(f"   ⚠️  Could not unload {model_name}: {e}")


def run_diagnostic() -> dict:
    """Run S2→S6 on the diagnostic clusters. Checkpoint-resume: skips completed stages."""
    results: dict = {
        "run_id": RUN_ID,
        "started": datetime.now().isoformat(),
        "books_sampled": args.books,
        "seed": args.seed,
        "only_convergent": args.only_convergent,
    }
    
    _s2_ckpt = CHECKPOINT_DIR / "stage2_extract" / RUN_ID / "checkpoint.jsonl"
    _s4_ckpt = CHECKPOINT_DIR / "stage4_merge" / RUN_ID / "checkpoint.jsonl"
    _s5_ckpt = CHECKPOINT_DIR / "stage5_verify" / RUN_ID / "checkpoint.jsonl"

    # ═══ S2: Convergent Extraction ══════════════════════════════════════
    if _s2_ckpt.exists():
        s2_fbs = []
        with open(_s2_ckpt) as f:
            for line in f:
                if line.strip():
                    s2_fbs.append(json.loads(line))
        results["s2_fb_count"] = len(s2_fbs)
        results["s2_elapsed_s"] = 0
        print(f"\n{'='*60}\n🔬 STAGE 2: RESUMED — {len(s2_fbs)} FBs from checkpoint\n{'='*60}")
    else:
        print(f"\n{'='*60}\n🔬 STAGE 2: Convergent Extraction\n{'='*60}")
        t0 = time.time()
        try:
            s2.STAGE2_CHECKPOINT = _s2_ckpt
            s2.STAGE2_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
            s2.CHECKPOINT_DIR = s2.STAGE2_CHECKPOINT.parent
            if args.no_probe:
                s2.SPLIT_PROBE_ENABLED = False
                s2.S2_SPLIT_PROBE_ENABLED = False
                print("⚡ Split probe DISABLED — faster extraction")
            s2.run_stage2(provider="omlx", only_convergent=args.only_convergent,
                          gate_enabled=True, gate_strict=False)
            s2_elapsed = time.time() - t0
            results["s2_elapsed_s"] = round(s2_elapsed, 1)
            s2_fbs = []
            if s2.STAGE2_CHECKPOINT.exists():
                with open(s2.STAGE2_CHECKPOINT) as f:
                    for line in f:
                        if line.strip():
                            s2_fbs.append(json.loads(line))
            results["s2_fb_count"] = len(s2_fbs)
            print(f"✅ S2 complete: {len(s2_fbs)} FBs in {s2_elapsed:.1f}s")
            # Persist state for crash recovery
            _ds = _load_diag_state()
            _ds["s2_completed"] = True
            _ds["s2_fb_count"] = len(s2_fbs)
            _save_diag_state(_ds)
            # D2263: merged call uses GPT-OSS only — unload Qwen3-Coder
            _unload_omlx_model("Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
        except Exception as e:
            results["s2_error"] = str(e)
            print(f"❌ S2 FAILED: {e}")
            return results

    # ═══ S4: Merge + Classify + Depth ════════════════════════════════════
    if _s4_ckpt.exists():
        s4_fbs = [json.loads(l) for l in open(_s4_ckpt) if l.strip()]
        print(f"\n{'='*60}\n🧩 STAGE 4: RESUMED — {len(s4_fbs)} FBs from checkpoint\n{'='*60}")
        results["s4_fb_count"] = len(s4_fbs)
        results["s4_elapsed_s"] = 0
        # Persist resume state for cross-process crash recovery
        _diag_state = _load_diag_state()
        _diag_state["s4_completed"] = True
        _diag_state["s4_fb_count"] = len(s4_fbs)
        _save_diag_state(_diag_state)
    else:
        print(f"\n{'='*60}\n🧩 STAGE 4: Merge + Classify + Depth\n{'='*60}")
        t0 = time.time()
        try:
            s4.STAGE4_CHECKPOINT = _s4_ckpt
            s4.STAGE4_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
            s4.CHECKPOINT_DIR = s4.STAGE4_CHECKPOINT.parent
            s4.STAGE2_CHECKPOINT = _s2_ckpt
            # S4 limit: truncate S2 checkpoint for faster eval
            if args.s4_limit and s4.STAGE2_CHECKPOINT.exists():
                _limited = s4.STAGE2_CHECKPOINT.parent / "checkpoint_limited.jsonl"
                _n = 0
                with open(s4.STAGE2_CHECKPOINT) as fin, open(_limited, "w") as fout:
                    for _n, line in enumerate(fin):
                        if _n >= args.s4_limit:
                            break
                        fout.write(line)
                s4.STAGE2_CHECKPOINT = _limited
                print(f"🔢 S4 limited to {min(args.s4_limit, _n)} FBs")
            # D2226/D2263: merged call via config (C12)
            import os as _os4
            if _PIPELINE_CFG.get("stage4", {}).get("merged_call_enabled"):
                _os4.environ["MAXWELL_MERGED_S4"] = "1"
            s4.run_stage4(cluster_ids=None)
            s4_elapsed = time.time() - t0
            results["s4_elapsed_s"] = round(s4_elapsed, 1)
            s4_fbs = []
            if s4.STAGE4_CHECKPOINT.exists():
                with open(s4.STAGE4_CHECKPOINT) as f:
                    for line in f:
                        if line.strip():
                            s4_fbs.append(json.loads(line))
            results["s4_fb_count"] = len(s4_fbs)
            print(f"✅ S4 complete: {len(s4_fbs)} FBs in {s4_elapsed:.1f}s")
            # Persist state for crash recovery
            _ds = _load_diag_state()
            _ds["s4_completed"] = True
            _ds["s4_fb_count"] = len(s4_fbs)
            _save_diag_state(_ds)
            # Unload GPT-OSS — S5 uses Phi-4-mini (D2264), free S4 model memory
            _unload_omlx_model("gpt-oss-20b-MXFP4-Q8")
        except Exception as e:
            results["s4_error"] = str(e)
            print(f"❌ S4 FAILED: {e}")
            return results

    # ═══ S5: Verify ══════════════════════════════════════════════════════
    if _s5_ckpt.exists():
        s5_fbs = [json.loads(l) for l in open(_s5_ckpt) if l.strip()]
        s5_pass = sum(1 for fb in s5_fbs if fb.get("verification_status") == "PASS")
        s5_quarantine = sum(1 for fb in s5_fbs if fb.get("verification_status") == "QUARANTINE")
        s5_fail = len(s5_fbs) - s5_pass - s5_quarantine
        results.update({"s5_fb_count": len(s5_fbs), "s5_pass": s5_pass,
                        "s5_quarantine": s5_quarantine, "s5_fail": s5_fail,
                        "s5_pass_rate": round(s5_pass / max(len(s5_fbs), 1), 3),
                        "s5_elapsed_s": 0})
        print(f"\n{'='*60}\n🔍 STAGE 5: RESUMED — {len(s5_fbs)} FBs (PASS={s5_pass}, Q={s5_quarantine})\n{'='*60}")
        # Persist resume state
        _diag_state = _load_diag_state()
        _diag_state["s5_completed"] = True
        _diag_state["s5_fb_count"] = len(s5_fbs)
        _save_diag_state(_diag_state)
    else:
        print(f"\n{'='*60}\n🔍 STAGE 5: Verify (DeBERTa FEVER + Phi-4-mini + BORP)\n{'='*60}")
        # Pre-warm Phi-4-mini for S5 (D2264 verifier) — avoids cold-load timeout on first call
        print("   🔥 Pre-warming Phi-4-mini...")
        from pipeline.model_lazyload import load_model
        load_model("Phi-4-mini-instruct-8bit", warm_seconds=2)
        t0 = time.time()
        try:
            s5.STAGE5_CHECKPOINT = _s5_ckpt
            s5.STAGE5_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
            s5.CHECKPOINT_DIR = s5.STAGE5_CHECKPOINT.parent
            s5.STAGE4_CHECKPOINT = _s4_ckpt
            s5.run_stage5(strict=False, skip_nli=False)
            s5_elapsed = time.time() - t0
            results["s5_elapsed_s"] = round(s5_elapsed, 1)
            s5_fbs = []; s5_pass = s5_fail = s5_quarantine = 0
            if s5.STAGE5_CHECKPOINT.exists():
                with open(s5.STAGE5_CHECKPOINT) as f:
                    for line in f:
                        if line.strip():
                            fb = json.loads(line)
                            s5_fbs.append(fb)
                            s = fb.get("verification_status", "UNKNOWN")
                            if s == "PASS": s5_pass += 1
                            elif s == "QUARANTINE": s5_quarantine += 1
                            else: s5_fail += 1
            results.update({"s5_fb_count": len(s5_fbs), "s5_pass": s5_pass,
                            "s5_quarantine": s5_quarantine, "s5_fail": s5_fail,
                            "s5_pass_rate": round(s5_pass / max(len(s5_fbs), 1), 3)})
            print(f"✅ S5 complete: {len(s5_fbs)} FBs (PASS={s5_pass}, Q={s5_quarantine}) in {s5_elapsed:.1f}s")
            # Persist state for crash recovery
            _ds = _load_diag_state()
            _ds["s5_completed"] = True
            _ds["s5_fb_count"] = len(s5_fbs)
            _ds["s5_pass"] = s5_pass
            _save_diag_state(_ds)
        except Exception as e:
            results["s5_error"] = str(e)
            print(f"❌ S5 FAILED: {e}")
            return results

    # ═══ S6: Commit ══════════════════════════════════════════════════════
    print(f"\n{'='*60}\n💾 STAGE 6: Commit (SQLite + Parquet)\n{'='*60}")
    t0 = time.time()
    try:
        s6.STAGE6_CHECKPOINT = CHECKPOINT_DIR / "stage6_commit" / RUN_ID / "checkpoint.jsonl"
        s6.STAGE6_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
        s6.CHECKPOINT_DIR = s6.STAGE6_CHECKPOINT.parent
        s6.STAGE5_CHECKPOINT = _s5_ckpt
        s6.DB_PATH = DATA_DIR / f"diagnostic_{RUN_ID}.db"
        s6.PARQUET_DIR = DATA_DIR / "parquet" / RUN_ID
        _prod_db = DATA_DIR / "maxwell.db"
        if s6.DB_PATH.resolve() == _prod_db.resolve():
            raise RuntimeError(f"REFUSING: DB_PATH still points to production DB")
        print(f"   💾 Diagnostic DB: {s6.DB_PATH}")
        s6.run_stage6(export_only=False)
        s6_elapsed = time.time() - t0
        results["s6_elapsed_s"] = round(s6_elapsed, 1)
        results["s6_db_path"] = str(s6.DB_PATH)
        print(f"✅ S6 complete in {s6_elapsed:.1f}s")
    except Exception as e:
        results["s6_error"] = str(e)
        print(f"❌ S6 FAILED: {e}")

    results["completed"] = datetime.now().isoformat()
    return results

def generate_report(summary: dict, s5_fbs: list[dict]) -> str:
    """Generate a detailed human-readable markdown report."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = []

    lines.append(f"# Maxwell OS v3.0 — E2E Diagnostic Report")
    lines.append(f"> **Run ID:** `{summary.get('run_id', '?')}`")
    lines.append(f"> **Date:** {date_str}")
    lines.append(f"> **Books sampled:** {summary.get('books_sampled', '?')}")
    lines.append(f"> **Seed:** {summary.get('seed', '?')}")
    lines.append(f"> **Gate criteria (D2261):** Yield >1% + S5 pass >40% → approve T1.1")
    lines.append("")

    # ── Pipeline summary ────────────────────────────────────────────────
    lines.append("## 1. Pipeline Summary")
    lines.append("")
    lines.append("| Stage | Result | Time |")
    lines.append("|-------|--------|------|")
    s2_info = f"{summary.get('s2_fb_count', 0)} FBs" if "s2_error" not in summary else f"❌ {summary['s2_error']}"
    s4_info = f"{summary.get('s4_fb_count', 0)} FBs" if "s4_error" not in summary else f"❌ {summary['s4_error']}"
    s5_info = (f"{summary.get('s5_fb_count', 0)} FBs "
               f"(PASS={summary.get('s5_pass', 0)}, "
               f"QUARANTINE={summary.get('s5_quarantine', 0)}, "
               f"FAIL={summary.get('s5_fail', 0)})") if "s5_error" not in summary else f"❌ {summary['s5_error']}"
    s6_info = f"✅ {summary.get('s6_db_path', '?')}" if "s6_error" not in summary else f"❌ {summary['s6_error']}"

    lines.append(f"| S2 Extract | {s2_info} | {summary.get('s2_elapsed_s', '?')}s |")
    lines.append(f"| S4 Merge+Classify | {s4_info} | {summary.get('s4_elapsed_s', '?')}s |")
    lines.append(f"| S5 Verify | {s5_info} | {summary.get('s5_elapsed_s', '?')}s |")
    lines.append(f"| S6 Commit | {s6_info} | {summary.get('s6_elapsed_s', '?')}s |")
    lines.append("")

    # ── Gate decision ───────────────────────────────────────────────────
    lines.append("## 2. Gate Decision (D2261)")
    lines.append("")
    s5_pass_rate = summary.get("s5_pass_rate", 0)
    n_books = summary.get("books_sampled", 0)
    s2_count = summary.get("s2_fb_count", 0)
    yield_pct = round(s2_count / max(n_books, 1) * 100, 2)

    lines.append(f"- **Yield:** {s2_count} FBs / {n_books} books = **{yield_pct}%**")
    lines.append(f"- **S5 Pass Rate:** {s5_pass_rate:.1%} ({summary.get('s5_pass', 0)}/{summary.get('s5_fb_count', 0)})")

    if yield_pct > _GATE_YIELD_PASS and s5_pass_rate > _GATE_S5_PASS:
        lines.append("")
        lines.append("### ✅ GATE PASSED — APPROVE T1.1 FULL RUN")
        lines.append(f"Yield {yield_pct}% > {_GATE_YIELD_PASS}% threshold AND "
                     f"S5 pass rate {s5_pass_rate:.1%} > {_GATE_S5_PASS:.0%} threshold.")
    elif yield_pct < _GATE_YIELD_FAIL or s5_pass_rate < _GATE_S5_FAIL:
        lines.append("")
        lines.append("### 🛑 GATE FAILED — HALT AND DIAGNOSE")
        reasons = []
        if yield_pct < _GATE_YIELD_FAIL:
            reasons.append(f"Yield {yield_pct}% below {_GATE_YIELD_FAIL}% minimum")
        if s5_pass_rate < _GATE_S5_FAIL:
            reasons.append(f"S5 pass rate {s5_pass_rate:.1%} below {_GATE_S5_FAIL:.0%} minimum")
        lines.append(f"Reasons: {'; '.join(reasons)}.")
        lines.append("Do NOT launch T1.1. Investigate root cause.")
    else:
        lines.append("")
        lines.append("### ⚠️ GATE MARGINAL — JUDGMENT CALL")
        lines.append("Yield or S5 pass rate is in the marginal zone. Review FBs below before deciding.")
    lines.append("")

    # ── S5 verification detail ──────────────────────────────────────────
    lines.append("## 3. S5 Verification Detail")
    lines.append("")
    lines.append(f"| Status | Count | % |")
    lines.append(f"|--------|-------|---|")
    total = max(summary.get("s5_fb_count", 0), 1)
    lines.append(f"| PASS | {summary.get('s5_pass', 0)} | {summary.get('s5_pass', 0)/total:.1%} |")
    lines.append(f"| QUARANTINE | {summary.get('s5_quarantine', 0)} | {summary.get('s5_quarantine', 0)/total:.1%} |")
    lines.append(f"| FAIL/FLAG | {summary.get('s5_fail', 0)} | {summary.get('s5_fail', 0)/total:.1%} |")
    lines.append("")

    # ── FB detail — every FB with full properties ───────────────────────
    lines.append(f"## 4. All Foundation Blocks ({len(s5_fbs)} total)")
    lines.append("")

    for i, fb in enumerate(s5_fbs, 1):
        name = fb.get("name") or fb.get("fb_name") or "(unnamed)"
        status = fb.get("verification_status", "UNKNOWN")
        status_icon = {"PASS": "✅", "QUARANTINE": "🚫", "FLAG": "⚠️", "FAIL": "❌"}.get(status, "❓")

        lines.append(f"### {status_icon} FB-{i}: {name}")
        lines.append("")
        lines.append(f"**Status:** {status}")
        lines.append("")

        # Metadata
        lines.append("| Property | Value |")
        lines.append("|----------|-------|")
        for key in ["fb_id", "principle_id", "source_books", "source_diversity",
                     "is_convergent", "extraction_type", "depth", "discipline",
                     "gen_model", "pipeline_commit", "schema_version"]:
            val = fb.get(key)
            if val is not None:
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val[:5])
                    if len(fb.get(key, [])) > 5:
                        val += f" ... (+{len(fb[key]) - 5} more)"
                lines.append(f"| {key} | {val} |")

        # NLI scores
        nli_score = fb.get("nli_score")
        nli_label = fb.get("nli_label")
        if nli_score is not None:
            lines.append(f"| nli_score | {nli_score:.3f} ({nli_label}) |")
        lines.append("")

        # Body segments
        for field in ["definition", "mechanism", "boundary", "consequence",
                       "elaboration", "application", "failure_mode"]:
            val = fb.get(field)
            if val:
                label = field.replace("_", " ").title()
                lines.append(f"**{label}:** {val}")
                lines.append("")

        # Keywords and jargon
        keywords = fb.get("keywords")
        if keywords:
            if isinstance(keywords, list):
                keywords = ", ".join(keywords)
            lines.append(f"**Keywords:** {keywords}")
            lines.append("")

        jargon = fb.get("jargon")
        if jargon and isinstance(jargon, dict):
            lines.append("**Jargon:**")
            for term, explanation in list(jargon.items())[:10]:
                lines.append(f"- **{term}:** {explanation}")
            lines.append("")

        # Evidence passages (truncated)
        evidence = fb.get("evidence_passages") or fb.get("evidence", [])
        if evidence:
            lines.append(f"**Evidence Passages ({len(evidence)}):**")
            for j, ep in enumerate(evidence[:3]):
                ep_text = str(ep)[:500]
                lines.append(f"{j+1}. \"{ep_text}...\"")
            if len(evidence) > 3:
                lines.append(f"  ... and {len(evidence) - 3} more")
            lines.append("")

        # Verification details
        for vk in ["nli_label", "nli_score", "verifier_model",
                    "verification_method", "borp_score", "epistemic_status"]:
            vv = fb.get(vk)
            if vv is not None:
                lines.append(f"- **{vk}:** {vv}")
        # Include verification detail from results array
        for vr in fb.get("verification_results", []):
            cn = vr.get("check_name", "?")
            cd = vr.get("detail", "")
            if cd:
                lines.append(f"- **{cn}:** {cd[:200]}")
        lines.append("")
        lines.append("---")
        lines.append("")

    report = "\n".join(lines)
    return report


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = OUTPUT_DIR / f"e2e_diagnostic_{date_str}.md"
    summary_path = OUTPUT_DIR / f"e2e_diagnostic_{date_str}.json"

    # Resolve defaults before any use
    if args.quick:
        args.only_convergent = True
        args.max_clusters = _QUICK_CLUSTERS
        args.no_probe = True
    if args.books is None:
        args.books = _DEFAULT_BOOKS

    # ── D2266: Process guard — prevent multiple simultaneous diagnostics ─
    if not _acquire_process_lock():
        sys.exit(1)

    # ── Register signal handlers for clean exit on Ctrl+C ──────────────
    _register_signal_handlers()

    # ── D2266: Kill any stale diagnostic processes (belt + suspenders) ──
    _stale_killed = _kill_stale_diagnostics()
    if _stale_killed > 0:
        print(f"🧹 Cleaned up {_stale_killed} stale diagnostic process(es)")

    # ── D2267: Prevent laptop sleep during diagnostic ───────────────────
    _caffeinate_started = _start_caffeinate()

    # ── Resume status: show what's already been done ────────────────────
    _prev_state = _load_diag_state()
    _resumed = False
    if _prev_state:
        _paused = _prev_state.get("paused", False)
        _done = []
        for _stg in ("s2", "s4", "s5"):
            if _prev_state.get(f"{_stg}_completed"):
                _done.append(f"{_stg.upper()}({_prev_state.get(f'{_stg}_fb_count', '?')} FBs)")
        if _done:
            _resumed = True
            _status = "PAUSED — resuming" if _paused else "CRASHED — recovering"
            print(f"\n🔄 {_status}: {' → '.join(_done)} already completed")
            print(f"   Will skip completed stages and continue from last checkpoint.")
        elif _paused:
            print(f"\n⏸️  Previous run was paused but no stages completed. Starting fresh.")

    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║  Maxwell OS v3.0 — E2E Diagnostic Gate (D2261)              ║")
    print(f"║  Run ID: {RUN_ID:<50}║")
    print(f"║  Books: {args.books:<54}║")
    print(f"║  Seed: {args.seed:<55}║")
    if args.quick:
        print(f"║  Mode: QUICK ({_QUICK_CLUSTERS} convergent clusters){' ' * 22}║")
    if args.max_clusters:
        print(f"║  Max clusters: {args.max_clusters:<46}║")
    if _caffeinate_started:
        print(f"║  ☕ Laptop sleep: DISABLED (caffeinate active){' ' * 21}║")
    print(f"╚══════════════════════════════════════════════════════════════╝")

    # ── Step 1: Sample books and filter clusters ─────────────────────────
    if args.quick:
        print(f"⚡ Quick mode: {_QUICK_CLUSTERS} convergent clusters only (~30min)")

    sampled_books, convergent, single_source = sample_books(args.books, args.seed)

    # Apply --max-clusters cap (convergent first, then single-source)
    if args.max_clusters and args.max_clusters > 0:
        if len(convergent) > args.max_clusters:
            convergent = convergent[:args.max_clusters]
            single_source = []
        else:
            remaining = args.max_clusters - len(convergent)
            single_source = single_source[:remaining]
        print(f"🔢 Capped at {args.max_clusters} clusters: {len(convergent)} convergent + {len(single_source)} single-source")

    total_clusters = len(convergent) + len(single_source)

    if args.dry_run:
        # Estimate runtime: convergent ~28s, single-source ~12s, with 3 workers
        est_s = (len(convergent) * 28 + len(single_source) * 12) / 3
        est_min = est_s / 60
        est_h = est_s / 3600
        time_str = f"{est_h:.1f}h" if est_h >= 1 else f"{est_min:.0f}min"
        print(f"\n🔍 DRY RUN — would process {total_clusters} clusters touching {len(sampled_books)} sampled books")
        print(f"   Convergent: {len(convergent)} (~28s each)")
        print(f"   Single-source: {len(single_source)} (~12s each)")
        print(f"   Estimated S2 runtime: ~{time_str} (with 3 workers)")
        print(f"   + S4 (~{total_clusters * 0.3:.0f}s) + S5 (~{total_clusters * 0.5:.0f}s) + S6")
        print(f"   Run ID: {RUN_ID}")
        print(f"   Output: {report_path}")
        return

    if total_clusters == 0:
        print("❌ No clusters found for sampled books. Try a larger --books value.")
        sys.exit(1)

    # ── Step 2: Symlink S1 chunks (read-only, only exists in production) ──
    _s1_diag = _S1_DIR / RUN_ID
    _needs_symlink = True
    if _s1_diag.exists():
        if _s1_diag.is_symlink() and _s1_diag.resolve() == _S1_PROD_DIR.resolve():
            _needs_symlink = False
        else:
            if _s1_diag.is_symlink():
                _s1_diag.unlink()
            else:
                import shutil as _shutil
                _shutil.rmtree(str(_s1_diag))
    if _needs_symlink:
        _s1_diag.symlink_to(_S1_PROD_DIR.resolve())
        print(f"🔗 S1 chunks: {RUN_ID} → {_DEFAULT_RUN_ID}")

    # S1.5: Write filtered clusters to diagnostic checkpoint
    write_diagnostic_clusters(convergent, single_source)

    # ── Step 3a: Check available memory (M1 Max 64GB, need ~22GB for models) ─
    try:
        import psutil as _psutil
        _mem = _psutil.virtual_memory()
        _free_gb_mem = _mem.available / (1024**3)
        _min_free_gb_mem = 8  # minimum free GB to start (models need ~22GB peak)
        print(f"🧠 RAM free: {_free_gb_mem:.1f} GB (min: {_min_free_gb_mem} GB)")
        if _free_gb_mem < _min_free_gb_mem:
            print(f"⚠️  WARNING: Only {_free_gb_mem:.1f} GB RAM free. Models may OOM.")
            print(f"   Consider closing other applications before proceeding.")
    except ImportError:
        print("⚠️  psutil not installed — skipping memory check")

    # ── Step 3b: Check disk space (prevent mid-run ENOSPC) ───────────
    _min_free_gb = 5  # minimum free GB before starting
    import shutil as _shutil2
    _disk_usage = _shutil2.disk_usage(str(PROJECT_ROOT))
    _free_gb = _disk_usage.free / (1024**3)
    print(f"💾 Disk free: {_free_gb:.1f} GB (min: {_min_free_gb} GB)")
    if _free_gb < _min_free_gb:
        print(f"🛑 INSUFFICIENT DISK SPACE: {_free_gb:.1f} GB < {_min_free_gb} GB minimum.")
        print(f"   Free up space before running diagnostic to avoid mid-run crash.")
        _release_process_lock()
        sys.exit(1)

    # ── Step 3: Verify OMLX health (host:port from config, C12) ────────
    _omlx_cfg = _PIPELINE_CFG.get("services", {}).get("omlx", {})
    _omlx_host = _omlx_cfg.get("host", "localhost")
    _omlx_port = _omlx_cfg.get("port", 11435)
    print(f"\n🔍 Checking OMLX health ({_omlx_host}:{_omlx_port})...")
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", f"{_omlx_host}:{_omlx_port}/health"],
            capture_output=True, text=True, timeout=5
        )
        print(f"   OMLX: {result.stdout.strip()}")
    except Exception as e:
        print(f"   ⚠️  OMLX health check failed: {e}")
        print("   Continuing anyway — S2 will fail if OMLX is unreachable.")

    # ── Step 4: Run the pipeline ────────────────────────────────────────
    summary = run_diagnostic()

    # ── Step 5: Collect S5 FBs for report ───────────────────────────────
    s5_fbs: list[dict] = []
    s5_checkpoint = CHECKPOINT_DIR / "stage5_verify" / RUN_ID / "checkpoint.jsonl"
    if s5_checkpoint.exists():
        with open(s5_checkpoint) as f:
            for line in f:
                line = line.strip()
                if line:
                    s5_fbs.append(json.loads(line))
    if not s5_fbs:
        # Try S4 if S5 failed
        s4_checkpoint = CHECKPOINT_DIR / "stage4_merge" / RUN_ID / "checkpoint.jsonl"
        if s4_checkpoint.exists():
            print("⚠️  S5 produced no output — using S4 FBs for report")
            with open(s4_checkpoint) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        s5_fbs.append(json.loads(line))
    if not s5_fbs:
        s2_checkpoint = CHECKPOINT_DIR / "stage2_extract" / RUN_ID / "checkpoint.jsonl"
        if s2_checkpoint.exists():
            print("⚠️  S4/S5 produced no output — using S2 FBs for report")
            with open(s2_checkpoint) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        s5_fbs.append(json.loads(line))

    summary["fb_count_in_report"] = len(s5_fbs)

    # ── Step 6: Generate report ─────────────────────────────────────────
    print(f"\n📝 Generating report: {report_path}")
    report = generate_report(summary, s5_fbs)

    with open(report_path, "w") as f:
        f.write(report)

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

    # ── Step 7: Print summary ───────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"📊 DIAGNOSTIC SUMMARY")
    print(f"{'='*60}")
    print(f"   Books sampled: {args.books}")
    print(f"   Clusters: {total_clusters} ({len(convergent)} convergent + {len(single_source)} single)")
    print(f"   S2 FBs: {summary.get('s2_fb_count', 'FAILED')}")
    print(f"   S4 FBs: {summary.get('s4_fb_count', 'FAILED')}")
    print(f"   S5 FBs: {summary.get('s5_fb_count', 'FAILED')} "
          f"(PASS={summary.get('s5_pass', 0)}, Q={summary.get('s5_quarantine', 0)})")
    s5_pr = summary.get("s5_pass_rate", 0)
    n_books = summary.get("books_sampled", 1)
    s2_count = summary.get("s2_fb_count", 0)
    yield_pct = round(s2_count / max(n_books, 1) * 100, 2)

    print(f"\n   📈 Yield: {yield_pct}% ({s2_count} FBs / {n_books} books)")
    print(f"   🔍 S5 Pass Rate: {s5_pr:.1%}")

    if yield_pct > _GATE_YIELD_PASS and s5_pr > _GATE_S5_PASS:
        print(f"\n   ✅ GATE PASSED — T1.1 full run APPROVED")
    elif yield_pct < _GATE_YIELD_FAIL or s5_pr < _GATE_S5_FAIL:
        print(f"\n   🛑 GATE FAILED — Do NOT run T1.1")
    else:
        print(f"\n   ⚠️  MARGINAL — Review report before deciding")

    print(f"\n   📄 Full report: {report_path}")
    print(f"   📊 Summary JSON: {summary_path}")
    print(f"   💾 Diagnostic DB: {summary.get('s6_db_path', 'N/A')}")

    # ── D2266/D2267: Cleanup ────────────────────────────────────────────
    _stop_caffeinate()
    _release_process_lock()


if __name__ == "__main__":
    main()
