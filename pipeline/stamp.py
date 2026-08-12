"""
stamp.py — R14 provenance stamp decorator for pipeline objects.
=================================================================
Authority: CONSTITUTION.md R14, C10, D2282

Usage:
    from pipeline.stamp import stamp, get_git_commit

    @stamp(gen_model="Qwen3.6-35B-A3B-4bit")
    def stage2_extract(segments):
        ...

    # Every dict output automatically gets:
    #   schema_version, gen_model, pipeline_commit, taxonomy_version,
    #   manifest_hash (D2282), pipeline_run_id, created_at

    # Manual stamp:
    stamped = stamp_record({"principle_text": "..."}, gen_model="Qwen3.6")
"""

import hashlib
import json
import subprocess
import uuid
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

from pipeline.pipeline_paths import SCHEMA_VERSION, TAXONOMY_VERSION


def get_git_commit() -> str:
    """Get current git commit hash (short). Returns 'unknown' if not in git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def get_pipeline_commit() -> str:
    """Get pipeline commit — uses git if available, else pipeline_paths default."""
    commit = get_git_commit()
    if commit == "unknown":
        from pipeline.pipeline_paths import PIPELINE_COMMIT
        return PIPELINE_COMMIT
    return commit


# Singleton: generated once per process, reused across all calls (P0.9 FIX)
_PIPELINE_RUN_ID: str | None = None


def get_pipeline_run_id() -> str:
    """Return the current pipeline run ID (created once, reused).
    P0.9 FIX: was regenerated per call, breaking R14 lineage for 6 of 7 stages."""
    global _PIPELINE_RUN_ID
    if _PIPELINE_RUN_ID is None:
        _PIPELINE_RUN_ID = uuid.uuid4().hex
    return _PIPELINE_RUN_ID


# D2282: Manifest hash — frozen config fingerprint embedded in every checkpoint.
# Computed once per process from pipeline_manifest section + runtime git_commit.
_MANIFEST_HASH: str | None = None


def _load_manifest() -> dict:
    """D2282: Load pipeline_manifest from config/pipeline_config.yaml."""
    import yaml as _yaml
    _cfg_path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
    try:
        with open(_cfg_path) as _f:
            _cfg = _yaml.safe_load(_f) or {}
        return _cfg.get("pipeline_manifest", {})
    except Exception:
        return {}


def get_manifest_hash() -> str:
    """D2282: Compute frozen config manifest hash.

    Combines pipeline_manifest from config with runtime git_commit.
    Returns the same hash for all records in a single pipeline run.
    Any config change → different hash → FB provenance is auditable.
    """
    global _MANIFEST_HASH
    if _MANIFEST_HASH is None:
        manifest = _load_manifest()
        # Add runtime git commit (not in static config)
        manifest["_git_commit"] = get_git_commit()
        # Canonical JSON serialization for deterministic hashing
        manifest_json = json.dumps(manifest, sort_keys=True, default=str)
        _MANIFEST_HASH = hashlib.sha256(manifest_json.encode()).hexdigest()[:16]
    return _MANIFEST_HASH


def stamp_record(
    record: dict,
    gen_model: str | None = None,
) -> dict:
    """Add provenance stamps to a dict record.

    Args:
        record: Dict to stamp.
        gen_model: Model that generated this record.

    Returns:
        Same dict with added stamp fields including manifest_hash (D2282).
    """
    record["schema_version"] = SCHEMA_VERSION
    record["gen_model"] = gen_model
    record["pipeline_commit"] = get_pipeline_commit()
    record["taxonomy_version"] = TAXONOMY_VERSION
    record["manifest_hash"] = get_manifest_hash()  # D2282: config fingerprint
    record["pipeline_run_id"] = get_pipeline_run_id()  # P0.9 FIX: singleton
    record["created_at"] = datetime.now(UTC).isoformat()
    return record


def stamp(gen_model: str | None = None):
    """Decorator: stamp every dict in the returned list.

    Usage:
        @stamp(gen_model="Qwen3.6-35B-A3B-4bit")
        def extract_principles(segments: list[dict]) -> list[dict]:
            ...

    The decorated function should return a list[dict]. Each dict gets stamped.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, list):
                return [stamp_record(r, gen_model=gen_model) if isinstance(r, dict) else r for r in result]
            elif isinstance(result, dict):
                return stamp_record(result, gen_model=gen_model)
            return result
        return wrapper
    return decorator


def make_hash_id(*fields: str) -> str:
    """Create a SHA-256 content-based ID from one or more fields.

    Usage:
        fb_id = make_hash_id(name, definition)
        segment_id = make_hash_id(text)
        principle_id = make_hash_id(principle_text)
    """
    combined = "|".join(fields)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()
