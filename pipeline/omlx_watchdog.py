#!/usr/bin/env python3
"""
omlx_watchdog.py — OMLX SERVER memory watchdog (M2 / D2027)
=============================================================
The existing 3-layer defense (memory_guard.py, justfile stress test,
--memory-guard aggressive) only protects the Python PROCESS.

This watchdog monitors the OMLX SERVER process for wired memory
growth (GitHub #2184). When RSS exceeds threshold, it restarts
the OMLX server gracefully.

Usage:
    python3 pipeline/omlx_watchdog.py              # one-shot check
    python3 pipeline/omlx_watchdog.py --daemon 60  # poll every 60s
    python3 pipeline/omlx_watchdog.py --pre-stage  # check before pipeline stage
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# ── Config (env overridable) ──────────────────────────────────────────
OMLX_BIN = os.environ.get("OMLX_BIN", "/opt/homebrew/opt/omlx/bin/omlx")
OMLX_PORT = int(os.environ.get("OMLX_PORT", "11435"))
RSS_THRESHOLD_GB = float(os.environ.get("OMLX_WATCHDOG_RSS_GB", "12.0"))  # restart when RSS > 12GB
RESTART_WAIT_SECS = int(os.environ.get("OMLX_WATCHDOG_RESTART_WAIT", "30"))
LOG_FILE = Path(os.environ.get("OMLX_WATCHDOG_LOG", "pipeline/omlx_watchdog.log"))


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


def check_and_restart() -> int:
    """
    Check OMLX server RSS. Restart if over threshold.
    Returns: 0=OK, 1=restarted, 2=error
    """
    pid = get_omlx_pid()
    if pid is None:
        log("OMLX server not running. Attempting start...")
        if start_omlx():
            log(f"Waiting {RESTART_WAIT_SECS}s for OMLX to initialize...")
            time.sleep(RESTART_WAIT_SECS)
            return 1
        return 2

    rss_gb = get_rss_gb(pid)
    if rss_gb < 0:
        log(f"Could not read RSS for PID {pid}")
        return 2

    if rss_gb > RSS_THRESHOLD_GB:
        log(f"WARNING: OMLX RSS {rss_gb:.1f}GB exceeds threshold {RSS_THRESHOLD_GB}GB. Restarting...")
        kill_omlx(pid)
        time.sleep(3)
        if start_omlx():
            log(f"Waiting {RESTART_WAIT_SECS}s for OMLX to initialize...")
            time.sleep(RESTART_WAIT_SECS)
            return 1
        return 2

    log(f"OMLX OK: RSS {rss_gb:.1f}GB (threshold {RSS_THRESHOLD_GB}GB)")
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

    args = parser.parse_args()

    if args.daemon:
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
