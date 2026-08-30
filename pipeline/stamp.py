"""
stamp.py — R14 provenance stamp decorator for pipeline objects.
=================================================================
Authority: CONSTITUTION.md R14, C10, D2282

Usage:
    from pipeline.stamp import stamp, get_git_commit

    @stamp(gen_model="Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
    def stage2_extract(segments):
        ...

    # Every dict output automatically gets:
    #   schema_version, gen_model, pipeline_commit, taxonomy_version,
    #   manifest_hash (D2282), pipeline_run_id, created_at

    # Manual stamp:
    stamped = stamp_record({"principle_text": "..."}, gen_model="Qwen3-Coder-30B-A3B")
"""

import hashlib
import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path

from pipeline.pipeline_paths import SCHEMA_VERSION, TAXONOMY_VERSION


# Memoized: the git commit never changes within a process. Caching here stops
# ~200K subprocess spawns when stamp_record() is called per cluster/singleton in
# S1.5 build_clusters (BUG-144: 27+ min silent grind). Mirrors _PIPELINE_RUN_ID
# and _MANIFEST_HASH singleton pattern.
_GIT_COMMIT: str | None = None


def get_git_commit() -> str:
    """Get current git commit hash (short). Returns 'unknown' if not in git repo.

    Memoized: git rev-parse is a subprocess (~5-10ms); stamp_record() calls
    this once per record, which in S1.5's build_clusters loop is ~200K spawns (~27 min).
    """
    global _GIT_COMMIT
    if _GIT_COMMIT is not None:
        return _GIT_COMMIT
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            _GIT_COMMIT = result.stdout.strip()
            return _GIT_COMMIT
        # C16 (D2491): non-zero exit was previously swallowed silently → R14
        # provenance stamped "unknown" with no trace.
        print(f"   ⚠️  git rev-parse exited {result.returncode}: "
              f"{result.stderr.strip()[:200]!r} — falling back to 'unknown' (C16)",
              file=sys.stderr)
    except Exception as e:
        print(f"   ⚠️  git rev-parse raised {type(e).__name__}: {e} — "
              f"falling back to 'unknown' (C16)", file=sys.stderr)
    _GIT_COMMIT = "unknown"
    return _GIT_COMMIT


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

    D2335: derive from the pipeline `run_id` (MAXWELL_RUN_ID / config default)
    instead of a fresh `uuid4()` per process. The UUID singleton was generated
    once per *process*, but every stage runs as its own subprocess — so S2, S4,
    and S6 each stamped a different `pipeline_run_id`, breaking R14 lineage
    across stages AND breaking e2e DB scoping (rows were stamped with a UUID
    while `e2e_test.py` filters `WHERE pipeline_run_id = get_run_id()`).
    """
    global _PIPELINE_RUN_ID
    if _PIPELINE_RUN_ID is None:
        from pipeline.pipeline_paths import get_run_id

        run_id = get_run_id() or ""
        # Use the named run_id so pipeline_run_id == run_id across all stage
        # subprocesses (stable lineage + scoping). Fall back to a UUID only if
        # run_id is somehow empty (config always provides `run.default_id`).
        _PIPELINE_RUN_ID = run_id if run_id else uuid.uuid4().hex
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
    except Exception as e:
        print(f"   ⚠️  stamp: pipeline_manifest unreadable ({type(e).__name__}: {e}) — empty manifest (C16)", file=sys.stderr)
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
    classify_model: str | None = None,
) -> dict:
    """Add provenance stamps to a dict record.

    Args:
        record: Dict to stamp.
        gen_model: Model that generated this record (S2 extraction).
        classify_model: Model that CLASSIFIED this record (S4 taxonomy, D2476).
            Distinct from gen_model — the classifier (gpt-oss) is a different
            family from the generator (Qwen3-Coder) per R5. Omitted (key absent)
            when the record was not classified (e.g. S2-side generation).

    Returns:
        Same dict with added stamp fields including manifest_hash (D2282).
    """
    record["schema_version"] = SCHEMA_VERSION
    record["gen_model"] = gen_model
    if classify_model is not None:
        record["classify_model"] = classify_model
    record["pipeline_commit"] = get_pipeline_commit()
    record["taxonomy_version"] = TAXONOMY_VERSION
    record["manifest_hash"] = get_manifest_hash()  # D2282: config fingerprint
    record["pipeline_run_id"] = get_pipeline_run_id()  # P0.9 FIX: singleton
    record["created_at"] = datetime.now(UTC).isoformat()
    return record


def stamp(gen_model: str | None = None):
    """Decorator: stamp every dict in the returned list.

    Usage:
        @stamp(gen_model="Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
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
