#!/usr/bin/env python3
"""S2 extraction watchdog — sample health and flag anomalies (D2384).

Lightweight, local-only sampler for a running (or finished) Stage 2 run. Detects the
hidden-failure signatures surfaced during the 2026-08-16 audit:

  * checkpoint frozen while the process is alive  → D2382 resume dedup self-collision
  * LLM failures / JSON-retry storms              → D2381 max_tokens truncation
  * causal_mechanism share drifting toward bias   → D2377 causal-bias fix regressing

Modes
-----
  one-shot (default)   print one health line; exit 0=ok / 1=anomaly / 2=not-running
  --loop               poll every ``watchdog.interval_secs`` until S2 exits or an
                       anomaly is detected (stall detection is active in loop mode)

Exit codes
----------
  0  healthy (or S2 finished normally in loop mode)
  1  anomaly detected (details on stderr)
  2  S2 not running and no checkpoint to watch

C12: every threshold is read from ``config/pipeline_config.yaml`` via pipeline_paths.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

# Ensure `pipeline` is importable when run as `python3 tools/watch_s2.py`
# (sys.path[0] is tools/, not the project root).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    DATA_DIR,
    S2_DIR,
    STAGE2_CHECKPOINT,
    WATCHDOG_CAUSAL_HALT_RATIO,
    WATCHDOG_CAUSAL_WARN_RATIO,
    WATCHDOG_INTERVAL_SECS,
    WATCHDOG_STALL_CHECKS,
)

_PROC_CMD = ["pgrep", "-f", "stage2_extract.py --only-convergent"]


def _is_running() -> bool:
    """Return True if an S2 ``--only-convergent`` process is alive."""
    return subprocess.run(_PROC_CMD, capture_output=True).returncode == 0


def _resolve_checkpoint() -> Path | None:
    """Return the active S2 checkpoint, auto-detecting the run-id if needed."""
    if STAGE2_CHECKPOINT.exists():
        return STAGE2_CHECKPOINT
    candidates = sorted(S2_DIR.glob("*/checkpoint.jsonl"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def _latest_log() -> Path | None:
    """Return the most recently modified ``s2_*.log`` under DATA_DIR, if any."""
    logs = sorted(DATA_DIR.glob("s2_*.log"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def _read_checkpoint(checkpoint: Path | None) -> tuple[int, float]:
    """Return ``(fb_count, causal_share)`` from the checkpoint, or ``(0, 0.0)``."""
    if checkpoint is None:
        return 0, 0.0
    try:
        fbs = [json.loads(line) for line in checkpoint.read_text().splitlines() if line.strip()]
    except (json.JSONDecodeError, OSError):
        return 0, 0.0
    c = Counter(fb.get("extraction_type", "?") for fb in fbs if not fb.get("_null"))
    causal = c.get("causal_mechanism", 0) / max(sum(c.values()), 1)
    return len(fbs), causal


def _log_markers(log: Path | None) -> dict[str, int]:
    """Count outcome markers in the S2 log (rough but useful signals)."""
    if log is None:
        return {}
    text = log.read_text(errors="replace")
    return {
        "added": text.count("→ "),
        "near_dup": text.count("near-duplicate"),
        "null": text.count("NULL/skip"),
        "llm_failed": text.count("LLM failed"),
        "json_retry": text.count("Empty JSON result"),
    }


def _sample() -> dict:
    """Collect one health sample."""
    running = _is_running()
    checkpoint = _resolve_checkpoint()
    fb_count, causal = _read_checkpoint(checkpoint)
    markers = _log_markers(_latest_log())
    return {"running": running, "fb_count": fb_count, "causal": causal, **markers}


def _anomalies(s: dict) -> list[str]:
    """Return the list of anomaly descriptions for a sample."""
    out: list[str] = []
    if s["causal"] > WATCHDOG_CAUSAL_HALT_RATIO:
        out.append(f"causal bias {s['causal']:.0%} > halt {WATCHDOG_CAUSAL_HALT_RATIO:.0%}")
    elif s["causal"] > WATCHDOG_CAUSAL_WARN_RATIO:
        out.append(f"causal drift {s['causal']:.0%} > warn {WATCHDOG_CAUSAL_WARN_RATIO:.0%}")
    if s.get("near_dup", 0) > 0:
        out.append(f"{s['near_dup']} near-duplicate rejections (dedup regression?)")
    if s.get("llm_failed", 0) > 0:
        out.append(f"{s['llm_failed']} LLM failures")
    return out


def _render(s: dict) -> str:
    """Format a one-line health summary."""
    state = "RUNNING" if s["running"] else "STOPPED"
    line = (f"[{state}] FBs={s['fb_count']} causal={s['causal']:.0%} "
            f"added={s.get('added', 0)} near_dup={s.get('near_dup', 0)} "
            f"NULL={s.get('null', 0)} LLM_failed={s.get('llm_failed', 0)} "
            f"json_retry={s.get('json_retry', 0)}")
    anom = _anomalies(s)
    return line + ("  ⚠️  " + "; ".join(anom) if anom else "")


def main() -> int:
    """Run the watchdog (one-shot or loop) and return a process exit code."""
    ap = argparse.ArgumentParser(description="S2 extraction watchdog (D2384)")
    ap.add_argument("--loop", action="store_true", help="poll until S2 exits or an anomaly")
    args = ap.parse_args()

    if not args.loop:
        s = _sample()
        print(_render(s))
        if not s["running"]:
            return 2
        anom = _anomalies(s)
        if anom:
            print("ANOMALY: " + "; ".join(anom), file=sys.stderr)
            return 1
        return 0

    # Loop mode
    stalls = 0
    last_fb: int | None = None
    while True:
        s = _sample()
        print(_render(s))
        anom = _anomalies(s)
        if anom:
            print("ANOMALY: " + "; ".join(anom), file=sys.stderr)
            return 1
        if not s["running"]:
            if s["fb_count"] > 0:
                print("S2 finished (checkpoint present) — watchdog exiting cleanly.")
                return 0
            print("S2 not running and no checkpoint — nothing to watch.", file=sys.stderr)
            return 2
        # Stall detection: frozen checkpoint while alive = D2382 data-loss signature.
        if last_fb is not None and s["fb_count"] == last_fb:
            stalls += 1
            if stalls >= WATCHDOG_STALL_CHECKS:
                print(f"STALL: checkpoint frozen at {s['fb_count']} FBs for "
                      f"{stalls} polls — possible data loss.", file=sys.stderr)
                return 1
        else:
            stalls = 0
        last_fb = s["fb_count"]
        time.sleep(WATCHDOG_INTERVAL_SECS)


if __name__ == "__main__":
    sys.exit(main())
