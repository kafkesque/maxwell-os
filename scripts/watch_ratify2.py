#!/usr/bin/env python3
"""RATIFY-2 watch loop — polls S1.5 embedding progress and alerts on stall/drop.

Read-only monitor for the in-flight `pipeline/runner.py` run. Every POLL_SECONDS
it reads the S1.5 incremental embedding manifest (state.json) and emits one
status line, raising ALERT lines on:

  * DROP   — a new missing batch index (embedding timeout/quarantine) appears.
  * STALL  — no new batch completed within STALL_MINUTES (wedged, or the machine
             went to sleep / ran out of battery).
  * DONE   — S1.5 reached completion (done >= total batches).
  * DEAD   — the runner process is gone while S1.5 is still incomplete.

It only READS pipeline artifacts; it never writes into pipeline I/O, so it is
safe to run alongside the pipeline. Thresholds are overridable via env:
MAXWELL_WATCH_POLL_S (default 120), MAXWELL_WATCH_STALL_MIN (default 15).

Usage (from the project root):
    nohup /opt/homebrew/bin/python3 -u scripts/watch_ratify2.py \
        >> "knowledge pipeline/logs/ratify2_watch.log" 2>&1 &
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure `pipeline.*` is importable when this script is run directly from scripts/.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

POLL_SECONDS = int(os.environ.get("MAXWELL_WATCH_POLL_S", "120"))
STALL_MINUTES = int(os.environ.get("MAXWELL_WATCH_STALL_MIN", "15"))


def _now() -> str:
    """Local timestamp for log lines."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _state_path() -> Path:
    """Resolve the S1.5 embedding manifest via the canonical path module."""
    from pipeline.pipeline_paths import S15_DIR, get_run_id

    return Path(S15_DIR) / get_run_id() / "embeddings_cache" / "state.json"


def _runner_alive() -> bool:
    """True if a pipeline runner process is still present."""
    proc = subprocess.run(
        ["pgrep", "-f", "pipeline/runner.py --stages"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def _read_state() -> dict | None:
    """Read state.json, or None if not yet written / unreadable."""
    path = _state_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _s15_finalized() -> bool:
    """True once S1.5 has finalized: the incremental state.json is removed and
    the stage's final checkpoint.jsonl is written into the run directory."""
    from pipeline.pipeline_paths import S15_DIR, get_run_id

    run_dir = Path(S15_DIR) / get_run_id()
    return (run_dir / "checkpoint.jsonl").exists()


def _fmt_pct(done_segments: int, total: int) -> str:
    """Format a progress percentage, guarding divide-by-zero."""
    return f"{done_segments * 100.0 / total:.2f}%" if total else "?"


def main() -> int:
    """Run the watch loop until interrupted or the run finishes."""
    last_done: int | None = None
    last_gap_count: int | None = None
    last_tick = time.time()
    last_progress = time.time()

    while True:
        state = _read_state()
        ts = _now()

        if state is None:
            if _s15_finalized():
                print(
                    f"[{ts}] S1.5 COMPLETE — state finalized (incremental cache removed). "
                    f"Monitor S2+ via the main run log.",
                    flush=True,
                )
                return 0
            print(f"[{ts}] WAIT state.json not written yet", flush=True)
            time.sleep(POLL_SECONDS)
            continue

        total = int(state.get("total", 0))
        dim = int(state.get("dim", 0))
        done_batches = sorted(int(x) for x in state.get("done_batches", []))
        done = len(done_batches)
        total_batches = (total + 63) // 64

        # Missing batch indices at or below the highest completed batch = drops.
        max_done = done_batches[-1] if done_batches else -64
        expected = set(range(0, max_done + 64, 64)) if max_done >= 0 else set()
        gaps = sorted(expected - set(done_batches))

        now = time.time()
        rate = 0.0
        if last_done is not None and now > last_tick:
            rate = (done - last_done) / (now - last_tick) * 60.0  # batches/min

        done_segments = done * 64
        print(
            f"[{ts}] S1.5 done={done}/{total_batches} batches "
            f"({_fmt_pct(done_segments, total)}, ~{min(done_segments, total)}/{total} seg, "
            f"{rate:.1f} batches/min, gaps={len(gaps)}, dim={dim})",
            flush=True,
        )

        # New drop: a fresh missing batch index appeared since the last poll.
        if last_gap_count is not None and len(gaps) > last_gap_count:
            preview = gaps[:5]
            suffix = "..." if len(gaps) > 5 else ""
            print(
                f"[{ts}] ALERT DROP: {len(gaps)} missing batches "
                f"(up from {last_gap_count}): {preview}{suffix}",
                flush=True,
            )

        # Stall: no new completed batch for STALL_MINUTES while still incomplete.
        if done and done < total_batches:
            if last_done is not None and done == last_done:
                idle_min = (now - last_progress) / 60.0
                if idle_min > STALL_MINUTES:
                    print(
                        f"[{ts}] ALERT STALL: no new batch for {idle_min:.1f} min "
                        f"(done={done}, gaps={len(gaps)})",
                        flush=True,
                    )
            else:
                last_progress = now

        # Completion.
        if done_segments >= total:
            print(
                f"[{ts}] ALERT DONE: S1.5 embedding complete ({done} batches).",
                flush=True,
            )
            if not _runner_alive():
                print(f"[{ts}] RUN FINISHED — runner exited cleanly.", flush=True)
                return 0

        # Dead: runner gone while S1.5 is still incomplete.
        if not _runner_alive():
            print(
                f"[{ts}] ALERT DEAD: runner process gone with S1.5 incomplete "
                f"({_fmt_pct(done_segments, total)}).",
                flush=True,
            )
            return 1

        last_done = done
        last_gap_count = len(gaps)
        last_tick = now
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    sys.exit(main())
