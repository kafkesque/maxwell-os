#!/usr/bin/env python3
"""s4_post_finish.py — crash-safe, idempotent S4-completion handler (BUG-150 guard).

Runs AFTER Stage 4 finishes to execute the post-S4 safety chain without the
operator present:
    validate → backup → dedup_fb_id → remap_emerging → gate_emerging_rate → report
It STOPS before S5/S6 (expensive downstream stages; run only after reviewing the
gate result). Everything here is idempotent and crash-safe (safe_write_jsonl =
tempfile + fsync + os.replace), so it is safe to re-run at any time.

S4 itself is already crash-safe: incremental checkpointing
(config `stage4.checkpoint_interval`) + resume via --only-fb-ids. The only
failure mode this script guards against is the post-S4 silent data loss
(fb_id collision → INSERT OR REPLACE) and the raw emerging rate tripping the
gate.

Completion is detected from S4's log markers (stage4_merge.py summary block):
    "FBs generated:"             → CLEAN        → run chain
    "CONDITIONAL_SUCCESS"        → CONDITIONAL  → stop, report
    "Stage 4 FAILED"             → FAILED       → stop, report
    (no marker + PID gone)       → INTERRUPTED  → stop, report (resume required)

Modes:
    --watch      Wait for the live S4 process to finish, then run the chain.
    --no-wait    Run the chain immediately (assume S4 already finished).
    --pid N      S4 PID to watch (default: auto-detect via pgrep stage4_merge.py).
    --advance    After a PASSING gate, also run stage5_verify + stage6_commit.

Unattended example:
    nohup python3 scripts/s4_post_finish.py --watch > logs/s4_post_finish.log 2>&1 &
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import STAGE4_CHECKPOINT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = STAGE4_CHECKPOINT.parent / "s4_post_finish_report.json"

_MARK_CLEAN = "FBs generated:"
_MARK_CONDITIONAL = "CONDITIONAL_SUCCESS"
_MARK_FAILED = "Stage 4 FAILED"


def _active_log() -> Path | None:
    """Most recently modified s4*run*.log in the run dir (mirrors s4_watch.py)."""
    d = STAGE4_CHECKPOINT.parent
    logs = sorted(d.glob("s4*run*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def _log_tail(log: Path, n: int = 400) -> str:
    try:
        with open(log, errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except OSError:
        return ""


def detect_s4_pid() -> int | None:
    """Auto-detect the live stage4_merge.py PID via pgrep."""
    try:
        out = subprocess.run(
            ["pgrep", "-f", "stage4_merge.py"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        pids = [int(p) for p in out.split() if p.isdigit()]
        return pids[0] if pids else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _proc_alive(pid: int) -> bool:
    try:
        r = subprocess.run(["ps", "-p", str(pid)], capture_output=True, text=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def classify_completion(log: Path, pid: int | None) -> str:
    """Classify S4 completion state from log markers + process liveness.

    Order matters: S4 prints the summary block ("✅ FBs generated:") BEFORE the
    fail-closed verdict ("❌ Stage 4 FAILED" / "⚠️  Stage 4 CONDITIONAL_SUCCESS"),
    so the authoritative markers must be checked FIRST — otherwise a
    CONDITIONAL_SUCCESS or FAILED run is misclassified as CLEAN.
    """
    tail = _log_tail(log)
    if _MARK_FAILED in tail:
        return "FAILED"
    if _MARK_CONDITIONAL in tail:
        return "CONDITIONAL"
    if _MARK_CLEAN in tail:
        return "CLEAN"
    if pid is not None and _proc_alive(pid):
        return "RUNNING"
    return "INTERRUPTED"


def _run_step(args: list[str]) -> int:
    """Run a subprocess step; return its exit code."""
    print(f"\n▶ {' '.join(args)}")
    r = subprocess.run([sys.executable, *args], cwd=PROJECT_ROOT)
    return r.returncode


def _backup() -> Path:
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = STAGE4_CHECKPOINT.parent / f"checkpoint_backup_{ts}.jsonl"
    shutil.copy2(STAGE4_CHECKPOINT, dst)
    print(f"💾 backed up {STAGE4_CHECKPOINT.name} → {dst.name}")
    return dst


def run_chain(advance: bool) -> dict:
    """Execute backup → dedup → remap → gate (→ S5/S6 if advance). Returns report dict."""
    report: dict = {"timestamp": _dt.datetime.now().isoformat(), "steps": {}}

    # 0. validate checkpoint
    if not STAGE4_CHECKPOINT.exists():
        print("❌ S4 checkpoint missing — cannot proceed.", file=sys.stderr)
        report["steps"]["validate"] = "missing"
        return report

    n = 0
    with open(STAGE4_CHECKPOINT) as f:
        for line in f:
            if line.strip():
                try:
                    json.loads(line)
                    n += 1
                except json.JSONDecodeError:
                    pass
    report["checkpoint_records"] = n
    print(f"✅ checkpoint readable: {n} records")

    # 1. backup
    report["steps"]["backup"] = str(_backup())

    # 2. dedup
    rc = _run_step(["scripts/dedup_fb_id.py", "--input", str(STAGE4_CHECKPOINT)])
    report["steps"]["dedup_fb_id"] = rc
    if rc != 0:
        print(f"🛑 dedup_fb_id exited {rc} — aborting chain.", file=sys.stderr)
        report["status"] = "FAILED_dedup"
        return report

    # 3. remap
    rc = _run_step(["scripts/remap_emerging.py"])
    report["steps"]["remap_emerging"] = rc
    if rc != 0:
        print(f"🛑 remap_emerging exited {rc} — aborting chain.", file=sys.stderr)
        report["status"] = "FAILED_remap"
        return report

    # 4. gate
    rc = _run_step(["scripts/gate_emerging_rate.py"])
    report["steps"]["gate_emerging_rate"] = rc
    if rc != 0:
        report["status"] = "GATE_FAILED"
        print("🛑 gate failed — do NOT advance to S5. Review taxonomy, then re-run remap.", file=sys.stderr)
        return report
    report["status"] = "GATE_PASSED"

    # 5. pre-S5 forensic audit (deterministic, fail-closed — no LLM)
    rc = _run_step(["scripts/audit_s4_final.py"])
    report["steps"]["audit_s4_final"] = rc
    if rc != 0:
        report["status"] = "AUDIT_FAILED"
        print("🛑 forensic audit failed — do NOT advance to S5.", file=sys.stderr)
        return report

    # 6. optional advance
    if advance:
        rc5 = _run_step(["pipeline/stage5_verify.py"])
        report["steps"]["stage5_verify"] = rc5
        if rc5 == 0:
            rc6 = _run_step(["pipeline/stage6_commit.py"])
            report["steps"]["stage6_commit"] = rc6
            report["status"] = "COMPLETE" if rc6 == 0 else "FAILED_stage6"

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="crash-safe S4 completion handler (BUG-150)")
    ap.add_argument("--watch", action="store_true", help="wait for S4 to finish before running")
    ap.add_argument("--no-wait", action="store_true", help="run immediately (S4 assumed done)")
    ap.add_argument("--pid", type=int, default=None, help="S4 PID to watch (default: auto-detect)")
    ap.add_argument("--advance", action="store_true", help="auto-run S5+S6 after a passing gate")
    args = ap.parse_args()

    log = _active_log()
    if log is None:
        print("❌ no s4*run*.log found — cannot classify S4 state.", file=sys.stderr)
        return 2

    pid = args.pid if args.pid is not None else detect_s4_pid()

    if args.watch or (not args.no_wait and pid is not None):
        print(f"⏳ waiting for S4 to finish (pid={pid}, log={log.name})…", flush=True)
        while pid is not None and _proc_alive(pid):
            tail = _log_tail(log, 5)
            last = tail.strip().splitlines()[-1] if tail.strip() else "(no log yet)"
            print(f"   [{_dt.datetime.now().strftime('%H:%M:%S')}] {last[-100:]}", flush=True)
            time.sleep(30)
        print("✅ S4 process finished.", flush=True)

    state = classify_completion(log, pid)
    print(f"\n🧭 S4 completion state: {state}", flush=True)

    if state in ("RUNNING", "INTERRUPTED", "CONDITIONAL", "FAILED"):
        report = {"timestamp": _dt.datetime.now().isoformat(), "state": state,
                  "status": "STOPPED", "note": "Do NOT advance. "
                  "INTERRUPTED → resume S4; CONDITIONAL → re-run to retry; FAILED → fix then re-run."}
        REPORT_PATH.write_text(json.dumps(report, indent=2))
        print(f"🛑 state={state} — stopping. See {REPORT_PATH}")
        return 1 if state != "RUNNING" else 0

    # CLEAN
    report = run_chain(args.advance)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\n📋 report written to {REPORT_PATH}")
    print(f"   final status: {report.get('status')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
