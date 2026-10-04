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
import os
import subprocess
import sys
import tempfile
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
        manifest = _cfg.get("pipeline_manifest", {}) or {}
        # D-318/D-325: a pin is a control only if it is byte-compared IN THE RUN PATH. Folding the
        # bytes of the ruled boundary rules (and the taxonomy) into manifest_hash means an FB
        # classified under different boundary rules cannot carry the same stamp (R14).
        from pipeline.pipeline_paths import (PROJECT_ROOT, S4_BOUNDARY_INJECT_ENABLED,
                                             S4_BOUNDARY_PATH)
        if S4_BOUNDARY_INJECT_ENABLED:
            _bp = PROJECT_ROOT / S4_BOUNDARY_PATH
            if not _bp.exists():
                raise RuntimeError(
                    f"D-325: boundary_inject_enabled but {S4_BOUNDARY_PATH} is missing (fail-closed, C16)")
            manifest["_s4_boundary_rules_sha256"] = hashlib.sha256(_bp.read_bytes()).hexdigest()[:16]
        return manifest
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


# ── BUG-614 (D-2801/D-2805): config-owned stage code fingerprints ──────────
# The pipeline/** lock was re-scoped from an edit-prohibition (will_not_touch) to an
# accountability gate: R5 generator!=verifier review + D-naming + a stage code
# fingerprint. This gate replaces the stale edit prohibition with a mechanism — the
# checkpoint a stage writes is bound to the byte content of the code that produced it,
# so an uncommitted (or committed) edit invalidates a stale resume fail-closed.
# The file list is config-owned (C12: ``{stage_key}.fingerprint_files``), mirroring the
# stage5_verify.py pattern (D-330/BUG-362). An empty/missing list is refused (C16).

_STAGE_CFG: dict | None = None


def _stage_config() -> dict:
    """Load config/pipeline_config.yaml once per process (memoized), mirroring _load_manifest."""
    global _STAGE_CFG
    if _STAGE_CFG is None:
        import yaml as _yaml
        _cfg_path = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"
        with open(_cfg_path, encoding="utf-8") as _f:
            _STAGE_CFG = _yaml.safe_load(_f) or {}
    return _STAGE_CFG


def stage_code_fingerprint(stage_key: str) -> str:
    """BUG-614: content-hash a pipeline stage's producing code (config-owned file list).

    The file list lives in ``config/pipeline_config.yaml`` under
    ``{stage_key}.fingerprint_files`` (C12). An empty/missing list is refused (C16,
    fail-closed): fingerprinting nothing would silently accept ANY code. Returns a
    16-hex SHA-256 prefix over the sorted file list's byte content.
    """
    stage_cfg = _stage_config().get(stage_key) or {}
    files = list(stage_cfg.get("fingerprint_files") or [])
    if not files:
        raise RuntimeError(
            f"{stage_key}.fingerprint_files is empty — refusing to fingerprint nothing (C16)"
        )
    root = Path(__file__).resolve().parent.parent
    h = hashlib.sha256()
    for rel in sorted(files):
        f = root / rel
        if not f.exists():
            raise RuntimeError(f"{stage_key}.fingerprint_files entry missing: {rel} (C16)")
        h.update(rel.encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def stage_code_fingerprint_path(checkpoint_path) -> Path:
    """The sidecar path that stores a checkpoint's producing-code fingerprint."""
    return Path(str(checkpoint_path) + ".code_fingerprint")


def write_stage_code_fingerprint(checkpoint_path, stage_key: str) -> str:
    """Persist the current code fingerprint beside ``checkpoint_path`` (crash-safe, C6).

    Returns the persisted fingerprint id. Written via tempfile + fsync + os.replace so a
    crash never leaves a truncated sidecar that would spuriously fail a later resume.
    """
    fp = stage_code_fingerprint(stage_key)
    sidecar = stage_code_fingerprint_path(checkpoint_path)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"fingerprint_id": fp, "stage_key": stage_key}, sort_keys=True)
    fd, tmp = tempfile.mkstemp(dir=str(sidecar.parent), prefix=sidecar.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, sidecar)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return fp


def read_stage_code_fingerprint(checkpoint_path) -> str | None:
    """Return the stored code fingerprint id, or None when absent/unreadable."""
    sidecar = stage_code_fingerprint_path(checkpoint_path)
    if not sidecar.exists():
        return None
    try:
        return (json.loads(sidecar.read_text(encoding="utf-8")) or {}).get("fingerprint_id")
    except Exception:
        return None


def check_stage_code_fingerprint(checkpoint_path, stage_key: str) -> None:
    """BUG-614: refuse to resume a checkpoint whose producing code has drifted.

    Fail-closed ONLY on a mismatch — a stored fingerprint that no longer equals the
    current code. A checkpoint with NO sidecar (legacy, pre-BUG-614) is allowed to
    resume unchanged: the mechanism is introduced incrementally without forcing a
    re-run of every legacy checkpoint.
    """
    stored = read_stage_code_fingerprint(checkpoint_path)
    if stored is None:
        return
    current = stage_code_fingerprint(stage_key)
    if stored != current:
        raise RuntimeError(
            f"{stage_key} code fingerprint mismatch for {checkpoint_path}: "
            f"stored {stored} != current {current} — the producing code changed since "
            f"this checkpoint was written; re-run the stage (or --force) rather than "
            f"silently resuming a stale checkpoint (BUG-614/C16)"
        )
