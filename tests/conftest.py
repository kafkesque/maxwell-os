"""tests/conftest.py — the executable form of the BUG-473 standing rule.

    A TEST MAY NOT WRITE OUTSIDE A TMP DIR.

WHY THIS EXISTS (BUG-473, severity 1, evidence on disk)
------------------------------------------------------
`python3 -m pytest tests -q` renamed
`knowledge pipeline/stage5_verify/t11/checkpoint.jsonl` (1.03 GB — the LIVE S5
state of the 7995-FB run) to `checkpoint.jsonl.stale_20260925_182629` at
18:26:29, because `run_stage5()` resolves the production checkpoint path and the
D2507 stale-archive branch renames whatever it finds there. `just health` then
went RED (`AUTHORITATIVE artifact is MISSING (C16)`) with no pipeline run active.

The per-test fix closes the known instance. This guard closes the CLASS: it
snapshots the production stage trees before the session and refuses to let the
session pass if the suite moved an UNDECLARED artifact.

Declarations live in `config/test_isolation.yaml` (C12 — no path and no glob is
hardcoded here). An artifact under a DECLARED test run id (`smoke_*`) is
tolerated but still REPORTED, so a tolerated write can never become invisible
(BUG-462 class). Anything else fails the session and names the paths.

Cost: one stat pass over the stage dirs. No writes, ever.
"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

import yaml

_REPO = Path(__file__).resolve().parents[1]
_ISOLATION_CFG = _REPO / "config" / "test_isolation.yaml"
_SKIP_DIRS = {"__pycache__", ".git"}
_SKIP_NAMES = {".DS_Store", "Thumbs.db"}
_STAGE_CONSTANTS = ("S0_DIR", "S1_DIR", "S13_DIR", "S15_DIR", "S2_DIR", "S4_DIR", "S5_DIR", "S6_DIR")


def _cfg() -> dict[str, Any]:
    """Load the isolation declarations; an unreadable config means FAIL CLOSED (C16)."""
    return yaml.safe_load(_ISOLATION_CFG.read_text()) or {}


def _stage_dirs() -> list[Path]:
    """Production stage directories, resolved from pipeline_paths — never hardcoded."""
    try:
        from pipeline import pipeline_paths as pp
    except Exception:  # pragma: no cover - an import failure is not this guard's business
        return []
    return [getattr(pp, n) for n in _STAGE_CONSTANTS if isinstance(getattr(pp, n, None), Path)]


def _snapshot(dirs: list[Path]) -> dict[str, tuple[int, int]]:
    """Map every production artifact path -> (bytes, mtime_ns)."""
    out: dict[str, tuple[int, int]] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if not p.is_file() or p.name in _SKIP_NAMES or any(part in _SKIP_DIRS for part in p.parts):
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            out[str(p)] = (st.st_size, st.st_mtime_ns)
    return out


def _run_id_of(path_str: str, dirs: list[Path]) -> str:
    """Return the run id (the component directly under the stage dir) of a snapshot path."""
    p = Path(path_str)
    for d in dirs:
        try:
            rel = p.relative_to(d)
        except ValueError:
            continue
        if rel.parts:
            return rel.parts[0]
    return ""


def _tolerated(path_str: str, dirs: list[Path], globs: list[str]) -> bool:
    """True when the artifact lives under a declared test run id."""
    return any(fnmatch.fnmatch(_run_id_of(path_str, dirs), g) for g in globs)


def pytest_sessionstart(session) -> None:
    """Snapshot the production stage trees before any test runs."""
    if os.environ.get("MAXWELL_TEST_ISOLATION_GUARD", "1") == "0":
        session.config._maxwell_stage_snapshot = None
        return
    dirs = _stage_dirs()
    session.config._maxwell_iso_dirs = dirs
    session.config._maxwell_stage_snapshot = _snapshot(dirs)


def pytest_sessionfinish(session, exitstatus) -> None:
    """Fail the session if the suite moved an UNDECLARED production artifact (BUG-473)."""
    before = getattr(session.config, "_maxwell_stage_snapshot", None)
    dirs = getattr(session.config, "_maxwell_iso_dirs", [])
    if before is None:
        return
    after = _snapshot(dirs)

    changed: dict[str, list[str]] = {
        "CREATED": sorted(set(after) - set(before)),
        "DELETED": sorted(set(before) - set(after)),
        "MODIFIED": sorted(k for k in set(before) & set(after) if before[k] != after[k]),
    }
    globs = list(_cfg().get("allowed_run_id_globs") or [])

    violations = {label: [p for p in paths if not _tolerated(p, dirs, globs)] for label, paths in changed.items()}
    tolerated = {label: [p for p in paths if _tolerated(p, dirs, globs)] for label, paths in changed.items()}

    n_tolerated = sum(len(v) for v in tolerated.values())
    if n_tolerated:
        print(
            f"\n[tests/conftest.py] test-isolation: {n_tolerated} declared smoke-run artifact(s) touched "
            f"(tolerated, reported — config/test_isolation.yaml). "
            f"Not yet isolated; see BUG-473/BUG-475."
        )

    if not any(violations.values()):
        return

    def _show(label: str, paths: list[str]) -> str:
        head = "\n".join(f"    {p}" for p in paths[:5])
        more = f"\n    ... +{len(paths) - 5} more" if len(paths) > 5 else ""
        return f"  {label} ({len(paths)}):\n{head}{more}"

    lines = [
        "",
        "=" * 78,
        "TEST ISOLATION VIOLATION (BUG-473) — the suite wrote outside a tmp dir.",
        "A test resolved a PRODUCTION artifact path. The live 1.03 GB t11 checkpoint",
        "was renamed this way on 2026-09-25 and `just health` went RED for ~10 minutes.",
        "",
        *[_show(label, paths) for label, paths in violations.items() if paths],
        "",
        "FIX: redirect the path into tmp_path (monkeypatch.setattr on the module constant),",
        "as tests/test_checkpoint_resume_d2409.py does for S5 — remember S5_LOCK_PATH (BUG-475).",
        "Declare a test-owned run id in config/test_isolation.yaml ONLY if it is test scratch.",
        "=" * 78,
    ]
    print("\n".join(lines))
    session.exitstatus = 1
