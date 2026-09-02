#!/usr/bin/env python3
"""s4_watch.py — live S4 progress + emerging-rate trajectory (D2485 gate metrics).

One-shot snapshot by default; `--watch N` loops every N seconds (Ctrl-C to stop).
Shows the SAME emerging metrics the post-S4 gate enforces
(discipline / domain-collapse / unmapped), so the live curve is directly
comparable to the 35%/30%/5% fail-closed thresholds (config/pipeline_config.yaml).

Reads the ACTIVE log (most recently modified `s4*run*.log`) — the resume run
writes `s4_resume_run.log`, NOT the stale `s4_run.log`.

Usage:
    python3 scripts/s4_watch.py               # one snapshot
    python3 scripts/s4_watch.py --watch 30    # refresh every 30s
    python3 scripts/s4_watch.py --json        # machine-readable
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl
from pipeline.pipeline_paths import STAGE4_CHECKPOINT, S4_DIR, get_run_id
from gate_emerging_rate import measure, _thresholds

RUN_ID = get_run_id()
S4DIR = S4_DIR / RUN_ID
CKPT = STAGE4_CHECKPOINT


def _active_log() -> Path | None:
    logs = sorted(S4DIR.glob("s4*run*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def _proc() -> dict:
    try:
        out = subprocess.run(["pgrep", "-f", "Python.*stage4_merge.py"],
                             capture_output=True, text=True, timeout=5)
        pids = [l for l in out.stdout.split() if l.strip()]
        if not pids:
            return {"running": False}
        ps = subprocess.run(["ps", "-p", pids[0], "-o", "etime=,%cpu=,state="],
                            capture_output=True, text=True, timeout=5)
        parts = ps.stdout.split()
        return {"running": True, "pid": pids[0],
                "etime": parts[0] if parts else "?",
                "cpu": parts[1] if len(parts) > 1 else "?",
                "state": parts[2] if len(parts) > 2 else "?"}
    except Exception as e:
        return {"running": None, "err": str(e)}


def _progress(log: Path | None) -> str:
    if log is None or not log.exists():
        return "?"
    try:
        txt = log.read_text(encoding="utf-8", errors="replace")
        m = re.findall(r"\[(\d+)/(\d+)\]", txt)
        return f"{m[-1][0]}/{m[-1][1]}" if m else "?"
    except Exception:
        return "?"


def _errors(log: Path | None) -> int:
    """Count REAL error lines (not FB names like 'Error Handling')."""
    if log is None or not log.exists():
        return -1
    # Precise markers: colon-suffixed keywords / tracebacks / fail emojis only,
    # so principle titles containing 'Error'/'Exception'/'Mismatch' are not flagged.
    markers = ("traceback", "error:", "exception:", "❌", "🛑", "quarantine",
               "runtimeerror", "valueerror", "typeerror", "keyerror", "raise ")
    n = 0
    for line in open(log, encoding="utf-8", errors="replace"):
        low = line.lower()
        if any(m in low for m in markers):
            n += 1
    return n


def snapshot() -> dict:
    fbs = load_jsonl(CKPT, context="S4 checkpoint (live watch)")
    m = measure(fbs)
    return {"proc": _proc(), "progress": _progress(_active_log()),
            "errors": _errors(_active_log()), "measure": m,
            "thresholds": _thresholds()}


def render(s: dict) -> str:
    m = s["measure"]
    th = s["thresholds"]
    p = s["proc"]
    lines = ["=" * 66,
             "  S4 LIVE — progress + emerging trajectory (D2485 gate metrics)",
             "=" * 66]
    if p.get("running"):
        lines.append(f"  Process: 🟢 pid {p['pid']}  {p['etime']}  "
                     f"cpu {p['cpu']}%  state {p['state']}")
    elif p.get("running") is False:
        lines.append("  Process: 🔴 NOT RUNNING")
    else:
        lines.append(f"  Process: ⚠️  {p.get('err','')}")
    lines.append(f"  Clusters: {s['progress']}   FBs: {m['total']}   "
                 f"error-lines: {s['errors']}")
    lines.append("-" * 66)
    for key, label in (("discipline", "discipline == 'emerging'"),
                       ("domain", "domains collapsed to ['emerging']"),
                       ("unmapped", "empty/garbage raw (fabrication risk)")):
        rate = m["rates"].get(key, 0.0)
        cap = th[key]
        flag = "✅" if rate <= cap else "🛑"
        lines.append(f"   {flag} {label:<42} {rate:6.1%}  (max {cap:.0%})")
    lines.append("=" * 66)
    return "\n".join(lines)


def main() -> int:
    as_json = "--json" in sys.argv
    watch = None
    if "--watch" in sys.argv:
        try:
            watch = int(sys.argv[sys.argv.index("--watch") + 1])
        except (ValueError, IndexError):
            watch = 30
    while True:
        s = snapshot()
        if as_json:
            print(json.dumps(s, indent=2))
        else:
            print(render(s))
        if watch is None:
            break
        time.sleep(watch)
        print("\033c", end="")  # clear screen (ANSI) before next refresh
    return 0


if __name__ == "__main__":
    sys.exit(main())
