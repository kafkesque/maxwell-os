"""
pipeline/metrics.py — Structured pipeline observability (Ponytail C18, Qwen v11.0 insight)
==========================================================================================
Minimal observability: per-stage timings, token counts, error rates → metrics.jsonl.
No heavy framework. Just structured data for debugging and calibration.
"""
import json
import time
from pathlib import Path

# D2175: Use DATA_DIR from pipeline_paths — no hardcoded paths (C12a)
from pipeline.pipeline_paths import DATA_DIR
METRICS_PATH = DATA_DIR / "metrics.jsonl"


class StageTimer:
    """Context manager for timing pipeline stages. Writes to metrics.jsonl."""

    def __init__(self, stage: str, run_id: str = "latest", metadata: dict | None = None):
        self.stage = stage
        self.run_id = run_id
        self.metadata = metadata or {}
        self.start_time: float = 0
        self.end_time: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        record = {
            "stage": self.stage,
            "run_id": self.run_id,
            "elapsed_sec": round(elapsed, 3),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "error": str(exc_val)[:200] if exc_val else None,
            **self.metadata,
        }
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(METRICS_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
        return False  # don't suppress exceptions


def log_metric(stage: str, **kwargs) -> None:
    """Fire-and-forget metric logging. Non-blocking."""
    record = {
        "stage": stage,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        **kwargs,
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_metrics(run_id: str = "latest") -> list[dict]:
    """Read all metrics for a run. Returns list of records."""
    if not METRICS_PATH.exists():
        return []
    records = []
    with open(METRICS_PATH) as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get("run_id") == run_id:
                    records.append(r)
            except json.JSONDecodeError:
                continue
    return records
