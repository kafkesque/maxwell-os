#!/usr/bin/env python3
"""n2_watchdog.py — every 5 min: N2 process, probe %, splits, checkpoint, OMLX, memory, stall detection.

Monitors the N2 full-corpus S2 run (PID 13137). Appends one line per check to
n2_watchdog.log. Stops itself if the N2 process dies (so the user is alerted).

Usage:
    python3 pipeline/n2_watchdog.py          # run in background via nohup
"""

import datetime
import json
import os
import re
import subprocess
import sys
import time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(PROJECT, "knowledge pipeline/stage2_extract/latest/n2_run.log")
WATCH = os.path.join(PROJECT, "knowledge pipeline/stage2_extract/latest/n2_watchdog.log")
CHECKPOINT = os.path.join(PROJECT, "knowledge pipeline/stage2_extract/latest/checkpoint.jsonl")
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 13137  # argv override (relaunch-safe)
INTERVAL = 300  # 5 minutes


def run(cmd, timeout: int = 10) -> str:
    """Run a shell command, return trimmed stdout ('' on failure)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except Exception:
        return ""


def probe_position(content: str) -> str:
    """Return the last split cluster ID from the N2 log ('' if none)."""
    ids = re.findall(r"✂️\s+(\S+):", content)
    return ids[-1] if ids else ""


def main() -> None:
    """Watch N2 every 5 minutes, append status lines, stop if process dies."""
    prev_splits: int | None = None
    prev_bytes: int | None = None
    stall_count: int = 0

    # Track probe position mapping (cluster id -> % through 2634 convergent)
    try:
        with open(os.path.join(PROJECT, "knowledge pipeline/stage1_5_embed_cluster/latest/checkpoint.jsonl")) as f:
            clusters = [json.loads(l) for l in f if l.strip()]
        conv = [c for c in clusters if c.get("is_convergent")]
        order = [c.get("cluster_id", "") for c in conv]
        total = len(order)
    except Exception:
        order, total = [], 0

    with open(WATCH, "a") as w:
        w.write(f"=== n2_watchdog started {datetime.datetime.now():%Y-%m-%d %H:%M:%S} (pid={os.getpid()}) ===\n")
        w.flush()
        while True:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Read N2 log
            try:
                with open(LOG) as f:
                    content = f.read()
                splits = len(re.findall(r"✂️", content))
                last = probe_position(content)
                bytes_now = len(content)
            except Exception as e:
                content, splits, last, bytes_now = "", -1, "?", -1
                print(f"[{ts}] LOG READ ERROR: {e}", file=sys.stderr)

            # Process status
            state = run(["ps", "-o", "state=", "-p", str(PID)])
            cputime = run(["ps", "-o", "time=", "-p", str(PID)])
            alive = state != ""

            # Checkpoint / extraction started?
            cp_lines = 0
            if os.path.exists(CHECKPOINT):
                try:
                    with open(CHECKPOINT) as f:
                        cp_lines = sum(1 for line in f if line.strip())
                except Exception as e:
                    # D2226: C16 compliance — log, don't silently swallow.
                    # Don't raise: watchdog is monitoring, not critical path.
                    # A corrupted checkpoint file shouldn't crash the watchdog.
                    print(f"   ⚠️  Watchdog: cannot read checkpoint line count: {e}", file=sys.stderr)

            # OMLX + memory
            omlx = run(["curl", "-s", "--max-time", "3", "http://localhost:11435/health"])
            omlx_status = "UP" if "healthy" in omlx else "DOWN"
            mem = run(["python3", "-c", "import psutil;print(f'{psutil.virtual_memory().available/1024**3:.1f}')"])

            # Probe % (last split's base cluster position)
            pct = "?"
            if last and order and total:
                base = re.sub(r"_sub\d+$", "", last)
                for i, cid in enumerate(order):
                    if cid == base:
                        pct = f"{100 * i / total:.1f}%"
                        break
                else:
                    pct = "? (sub-cluster)"

            # Stall detection (no log growth across 2 checks = 10+ min stuck)
            stall = ""
            if prev_splits is not None and splits == prev_splits and bytes_now == prev_bytes:
                stall_count += 1
                if stall_count >= 2:
                    stall = " ⚠️ STALLED (no progress 10+ min)"
            else:
                stall_count = 0
            prev_splits, prev_bytes = splits, bytes_now

            phase = "EXTRACTION" if cp_lines > 0 else "PROBE"
            line = (f"[{ts}] {phase} alive={'Y' if alive else 'N'} state={state or '?'} "
                    f"cpu={cputime or '?'} splits={splits} last={last} probe={pct} "
                    f"cp_lines={cp_lines} omlx={omlx_status} mem={mem}GB{stall}")
            print(line)
            w.write(line + "\n")
            w.flush()
            os.fsync(w.fileno())

            if not alive:
                w.write(f"[{ts}] ❌ N2 PROCESS {PID} DIED — check log tail and resume if needed\n")
                w.flush()
                break
            time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
