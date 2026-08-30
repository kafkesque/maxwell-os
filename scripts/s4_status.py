#!/usr/bin/env python3
"""s4_status.py — one-shot live status for the running Stage 4 (S4) merge run.

Shows process health, depth-pre-pass progress, FB checkpoint progress, and the
latest log lines + error count. Safe to run from ANY directory (absolute paths).

Why two files / two phases:
  Phase 1 (depth pre-pass, first ~6h): only `checkpoint.jsonl.depth.json` grows
        — `checkpoint.jsonl` does NOT exist yet (the main classify loop hasn't
        started). "0 FBs" here is EXPECTED, not an error.
  Phase 2 (main classify loop, ~48h): `checkpoint.jsonl` grows every 5 clusters.

Usage:
    python3 scripts/s4_status.py          # full status
    python3 scripts/s4_status.py --json   # machine-readable
    tail -f "<S4DIR>/s4_run.log"          # S4DIR derived from pipeline_paths + run_id
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# D2497/C12: derive paths from the project root + pipeline_paths (no hardcoded
# home-dir absolute paths). Safe to run from ANY directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.pipeline_paths import STAGE4_CHECKPOINT, S4_DIR, get_run_id

RUN_ID = get_run_id()
S4DIR = S4_DIR / RUN_ID
LOG = S4DIR / "s4_run.log"
DEPTH = STAGE4_CHECKPOINT.with_name(STAGE4_CHECKPOINT.name + ".depth.json")
CKPT = STAGE4_CHECKPOINT


def _jsonl_count(p: Path) -> int:
    if not p.exists():
        return -1  # absent
    return sum(1 for _ in open(p, encoding="utf-8") if _.strip())


def _depth_count() -> int:
    if not DEPTH.exists():
        return -1
    try:
        return len(json.load(open(DEPTH, encoding="utf-8")))
    except Exception:
        return -1


def _proc_info() -> dict:
    try:
        out = subprocess.run(
            ["pgrep", "-f", "Python.*stage4_merge.py"],
            capture_output=True, text=True, timeout=5,
        )
        pids = [l for l in out.stdout.split() if l.strip()]
        if not pids:
            return {"running": False, "pid": None}
        pid = pids[0]
        ps = subprocess.run(
            ["ps", "-p", pid, "-o", "etime=,%cpu=,%mem=,state="],
            capture_output=True, text=True, timeout=5,
        )
        etime, cpu, mem, state = (ps.stdout.split() + ["", "", "", ""])[:4]
        return {"running": True, "pid": int(pid), "etime": etime,
                "cpu": cpu, "mem": mem, "state": state}
    except Exception as e:
        return {"running": None, "pid": None, "err": str(e)}


def _errors() -> int:
    if not LOG.exists():
        return -1
    n = 0
    for line in open(LOG, encoding="utf-8", errors="replace"):
        low = line.lower()
        if any(k in low for k in ("error", "exception", "traceback", "failed",
                                  "quarantine", "mismatch")):
            if any(w in low for w in ("requestsdependencywarning", "urllib3", "chardet")):
                continue
            n += 1
    return n


def _tail(n: int = 6) -> list[str]:
    if not LOG.exists():
        return ["(no log yet)"]
    lines = [l.rstrip("\n") for l in open(LOG, encoding="utf-8", errors="replace")]
    return lines[-n:]


def main() -> int:
    as_json = "--json" in sys.argv
    p = _proc_info()
    d = _depth_count()
    c = _jsonl_count(CKPT)
    e = _errors()
    tail = _tail()

    if as_json:
        print(json.dumps({"process": p, "depth_classified": d, "fbs_checkpointed": c,
                          "error_lines": e, "log_tail": tail}, indent=2))
        return 0

    print("=" * 64)
    print("  S4 STATUS")
    print("=" * 64)
    if p.get("running"):
        print(f"  Process:   🟢 RUNNING  (pid {p['pid']}, {p['etime']}, "
              f"cpu {p['cpu']}%, mem {p['mem']}%, state {p['state']})")
    elif p.get("running") is False:
        print("  Process:   🔴 NOT RUNNING")
    else:
        print(f"  Process:   ⚠️  unknown ({p.get('err','')})")

    print("-" * 64)
    if d >= 0:
        print(f"  🧠 Depth pre-pass:  {d} clusters classified  (of ~7,880)")
    else:
        print("  🧠 Depth pre-pass:  not started")
    if c >= 0:
        print(f"  📦 FBs checkpointed: {c}  (main loop)")
    else:
        print("  📦 FBs checkpointed: 0  — main loop not started yet (depth pre-pass first)")
    print(f"  ❌ Error lines in log: {e}")
    print("-" * 64)
    print("  Latest log:")
    for l in tail:
        print(f"     {l}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
