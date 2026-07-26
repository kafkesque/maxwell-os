#!/usr/bin/env python3
"""
omlx_watchdog.py — OMLX SERVER memory watchdog (M2 / D2027 + BUG-017 mitigation)
=================================================================================
The existing 3-layer defense (memory_guard.py, justfile stress test,
--memory-guard aggressive) only protects the Python PROCESS.

This watchdog monitors the OMLX SERVER process for wired memory
growth (GitHub #2184, BUG-017). When RSS exceeds threshold or grows
abnormally, it restarts the OMLX server gracefully.

BUG-017 mitigation (D2115): Progressive threshold + trend detection.
If RSS grows >2GB since last check, triggers restart even if below
absolute threshold. Prevents unbounded wired memory leak on sustained runs.

Usage:
    python3 pipeline/omlx_watchdog.py              # one-shot check
    python3 pipeline/omlx_watchdog.py --daemon 60  # poll every 60s
    python3 pipeline/omlx_watchdog.py --pre-stage  # check before pipeline stage
    python3 pipeline/omlx_watchdog.py --reset      # reset trend tracking
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# ── Config (env overridable) ──────────────────────────────────────────
OMLX_BIN = os.environ.get("OMLX_BIN", "/Applications/oMLX.app/Contents/MacOS/omlx-cli")
OMLX_PORT = int(os.environ.get("OMLX_PORT", "11435"))
RSS_THRESHOLD_GB = float(os.environ.get("OMLX_WATCHDOG_RSS_GB", "20.0"))  # D2115: 20GB for 35B model
RSS_TREND_THRESHOLD_GB = float(os.environ.get("OMLX_WATCHDOG_TREND_GB", "2.0"))  # BUG-017: restart if grew >2GB
RESTART_WAIT_SECS = int(os.environ.get("OMLX_WATCHDOG_RESTART_WAIT", "30"))
LOG_FILE = Path(os.environ.get("OMLX_WATCHDOG_LOG", "pipeline/omlx_watchdog.log"))
STATE_FILE = Path(os.environ.get("OMLX_WATCHDOG_STATE", "pipeline/.omlx_watchdog_state.json"))


def get_omlx_pid() -> int | None:
    """Find the OMLX server process PID via pgrep. Returns None if not running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "omlx.*serve"],
            capture_output=True, text=True, timeout=5
        )
        pids = [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
        # Filter out our own process
        my_pid = os.getpid()
        pids = [p for p in pids if p != my_pid]
        return pids[0] if pids else None
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return None


def get_rss_gb(pid: int) -> float:
    """Get RSS in GB for a given PID via `ps`."""
    try:
        result = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)],
            capture_output=True, text=True, timeout=5
        )
        rss_kb = int(result.stdout.strip())
        return rss_kb / (1024 * 1024)  # KB → GB
    except (subprocess.TimeoutExpired, ValueError):
        return -1.0


def log(msg: str) -> None:
    """Append timestamped message to watchdog log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(line)


def kill_omlx(pid: int) -> bool:
    """Gracefully terminate OMLX server, then force-kill if needed."""
    try:
        os.kill(pid, signal.SIGTERM)
        log(f"Sent SIGTERM to OMLX (PID {pid})")
        # Wait for graceful shutdown
        for _ in range(10):
            time.sleep(1)
            try:
                os.kill(pid, 0)  # Check if still alive
            except OSError:
                log(f"OMLX (PID {pid}) terminated gracefully")
                return True
        # Force kill
        os.kill(pid, signal.SIGKILL)
        time.sleep(2)
        log(f"OMLX (PID {pid}) force-killed after timeout")
        return True
    except OSError as e:
        log(f"Error killing OMLX: {e}")
        return False


def start_omlx() -> bool:
    """Start OMLX server in background."""
    try:
        subprocess.Popen(
            [OMLX_BIN, "serve", "--port", str(OMLX_PORT), "--memory-guard", "aggressive"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        log(f"Started OMLX on port {OMLX_PORT} with --memory-guard aggressive")
        return True
    except Exception as e:
        log(f"Failed to start OMLX: {e}")
        return False


def _load_state() -> dict:
    """Load watchdog state (previous RSS for trend detection)."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"last_rss_gb": 0.0, "restart_count": 0, "last_restart_at": None}

def _save_state(state: dict) -> None:
    """Save watchdog state atomically."""
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)

def _reset_state() -> None:
    """Reset trend tracking state (after manual OMLX restart)."""
    STATE_FILE.unlink(missing_ok=True)
    log("Watchdog state reset")

def check_and_restart() -> int:
    """
    Check OMLX server RSS. Restart if over threshold or growing too fast.
    BUG-017 mitigation: progressive trend detection catches memory leak
    before it hits the absolute threshold.

    Returns: 0=OK, 1=restarted, 2=error
    """
    pid = get_omlx_pid()
    if pid is None:
        log("OMLX server not running. Attempting start...")
        _reset_state()
        if start_omlx():
            log(f"Waiting {RESTART_WAIT_SECS}s for OMLX to initialize...")
            time.sleep(RESTART_WAIT_SECS)
            return 1
        return 2

    rss_gb = get_rss_gb(pid)
    if rss_gb < 0:
        log(f"Could not read RSS for PID {pid}")
        return 2

    state = _load_state()
    prev_rss = state.get("last_rss_gb", 0.0)
    rss_delta = rss_gb - prev_rss if prev_rss > 0 else 0.0

    should_restart = False
    reason = ""

    # BUG-017: Trend detection — catch progressive memory leak
    if rss_delta > RSS_TREND_THRESHOLD_GB:
        should_restart = True
        reason = f"RSS grew {rss_delta:.1f}GB since last check (trend threshold {RSS_TREND_THRESHOLD_GB}GB)"
    # Absolute threshold
    elif rss_gb > RSS_THRESHOLD_GB:
        should_restart = True
        reason = f"RSS {rss_gb:.1f}GB exceeds absolute threshold {RSS_THRESHOLD_GB}GB"

    if should_restart:
        log(f"WARNING: {reason}. Restarting OMLX...")
        kill_omlx(pid)
        time.sleep(3)
        if start_omlx():
            state["restart_count"] = state.get("restart_count", 0) + 1
            state["last_restart_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            state["last_rss_gb"] = 0.0  # Reset trend after restart
            _save_state(state)
            log(f"Waiting {RESTART_WAIT_SECS}s for OMLX to initialize...")
            time.sleep(RESTART_WAIT_SECS)
            return 1
        return 2

    # Update trend tracking
    state["last_rss_gb"] = rss_gb
    _save_state(state)
    log(f"OMLX OK: RSS {rss_gb:.1f}GB (delta +{rss_delta:.1f}GB, threshold {RSS_THRESHOLD_GB}GB, restarts: {state.get('restart_count', 0)})")
    return 0


def daemon_mode(interval_secs: int) -> None:
    """Run watchdog continuously, checking every interval_secs."""
    log(f"Watchdog daemon started (interval={interval_secs}s, threshold={RSS_THRESHOLD_GB}GB)")
    restart_count = 0
    try:
        while True:
            rc = check_and_restart()
            if rc == 1:
                restart_count += 1
                log(f"Total restarts: {restart_count}")
            elif rc == 2:
                log("ERROR state — watchdog will retry on next interval")
            time.sleep(interval_secs)
    except KeyboardInterrupt:
        log("Watchdog daemon stopped by user")


def main():
    parser = argparse.ArgumentParser(description="OMLX Server Memory Watchdog (M2)")
    parser.add_argument("--daemon", type=int, default=0, metavar="SECS",
                        help="Run continuously, polling every SECS seconds")
    parser.add_argument("--pre-stage", action="store_true",
                        help="Check before pipeline stage (exit 1 if restart needed)")
    parser.add_argument("--pid", type=int, default=0,
                        help="Check specific PID instead of auto-detecting")
    parser.add_argument("--reset", action="store_true",
                        help="Reset trend tracking state (after manual OMLX restart)")

    args = parser.parse_args()

    if args.reset:
        _reset_state()
        sys.exit(0)
    elif args.daemon:
        daemon_mode(args.daemon)
    elif args.pid:
        rss = get_rss_gb(args.pid)
        if rss > RSS_THRESHOLD_GB:
            log(f"PID {args.pid} RSS {rss:.1f}GB exceeds threshold")
            sys.exit(1)
        log(f"PID {args.pid} RSS {rss:.1f}GB OK")
    elif args.pre_stage:
        rc = check_and_restart()
        sys.exit(rc)
    else:
        rc = check_and_restart()
        sys.exit(rc)


if __name__ == "__main__":
    main()
