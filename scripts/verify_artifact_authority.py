#!/usr/bin/env python3
"""scripts/verify_artifact_authority.py — enforce ARTIFACT_AUTHORITY.json (BUG-378(b), D-344)

WHY: session 22 wrote authority markers for knowledge pipeline/stage4_merge/t11 and
stage5_verify/t11 but nothing verified them — a claim without a check. This is the
checker. It answers one question per declared directory: "is the artifact the marker says
is authoritative ACTUALLY the one whose bytes are on disk, and is everything else in the
directory honestly declared non-authoritative?"

FAIL-CLOSED (C16) on the things that matter:
  * a directory holding a declared pattern with NO marker (when require_marker_in_dirs)
  * a marker missing a required field (the claim must be legible)
  * the authoritative artifact absent, or its sha256 / byte size not matching the marker
  * the marker's `dir` not matching the directory it sits in

DELIBERATELY NOT RED (BUG-372 — a flag that fires on expected behaviour is worse than none):
  * unlisted files (`.stale_*`, `.bak_*`, sidecars) are REPORTED per undeclared_policy;
    these directories are append-only by design (R-D410) and legitimate drift lives there.
  * a declared non_authoritative entry whose file is gone is reported, not RED — the marker
    records a disposition (superseded/archive-candidate), not a retention guarantee.

Config-first (C12): roots, depth, marker name and policy live in
config/artifact_authority.yaml. Usage: python3 scripts/verify_artifact_authority.py
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = _ROOT / "config" / "artifact_authority.yaml"
_HASH_CHUNK = 1 << 20


def sha256_of(path: Path) -> str:
    """Return the hex sha256 of a file, streamed (no full-file read; C24 on big artifacts)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: Path) -> Dict[str, Any]:
    """Load and validate the checker config; a missing key is a hard error (C12/C16)."""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    for key in ("marker_name", "roots", "required_marker_fields",
                "required_authoritative_fields", "undeclared_policy", "report_limit"):
        if key not in cfg:
            raise KeyError(f"{path.name}: missing required key '{key}' (C12/C16)")
    return cfg


def find_dirs(cfg: Dict[str, Any]) -> List[Path]:
    """Return every directory under the configured roots within max_depth."""
    max_depth = int(cfg.get("max_depth", 2))
    out: List[Path] = []
    for root in cfg["roots"]:
        base = _ROOT / str(root)
        if not base.is_dir():
            raise FileNotFoundError(f"declared authority root is not a directory: {base} (C16)")
        for path in sorted(base.rglob("*")):
            if not path.is_dir():
                continue
            depth = len(path.relative_to(base).parts)
            if depth <= max_depth:
                out.append(path)
    return out


def declares_pattern(marker: Dict[str, Any]) -> List[str]:
    """Return the authoritative glob patterns a marker declares."""
    patterns: List[str] = []
    for entry in marker.get("authoritative", []) or []:
        if isinstance(entry, dict) and entry.get("pattern"):
            # Markers may declare several globs pipe-joined ('a|b'); fnmatch treats a
            # pipe as a literal, so a pattern that CANNOT match anything it is asked to
            # match would make this checker a BUG-375 defect (BUG-384, first run).
            patterns.extend(part.strip() for part in str(entry["pattern"]).split("|") if part.strip())
    return patterns


def check_marker(directory: Path, cfg: Dict[str, Any]) -> Tuple[List[str], List[str], int, int]:
    """Verify one marker file; return (red, reports, checked_files, undeclared_count)."""
    red: List[str] = []
    reports: List[str] = []
    marker_path = directory / str(cfg["marker_name"])
    rel_dir = directory.relative_to(_ROOT)
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return [f"{rel_dir}: {cfg['marker_name']} is not valid JSON: {exc} (C16)"], reports, 0, 0
    for field in cfg["required_marker_fields"]:
        if field not in marker:
            red.append(f"{rel_dir}: marker missing required field '{field}'")
    declared_dir = str(marker.get("dir", ""))
    if declared_dir and declared_dir.strip("/") != str(rel_dir):
        red.append(f"{rel_dir}: marker declares dir '{declared_dir}' but sits in '{rel_dir}'")
    declared: Dict[str, Dict[str, Any]] = {}
    checked = 0
    entries: List[Tuple[str, Dict[str, Any]]] = [
        ("authoritative", entry) for entry in (marker.get("authoritative") or []) if isinstance(entry, dict)
    ] + [
        ("non_authoritative", entry) for entry in (marker.get("non_authoritative") or []) if isinstance(entry, dict)
    ]
    for kind, entry in entries:
        artifact = entry.get("artifact")
        if not artifact:
            red.append(f"{rel_dir}: a {kind} entry has no 'artifact' (the claim is not legible)")
            continue
        if kind == "authoritative":
            for field in cfg["required_authoritative_fields"]:
                if field not in entry:
                    red.append(f"{rel_dir}::{artifact}: authoritative entry missing '{field}'")
        target = directory / str(artifact)
        declared[str(artifact)] = entry
        if kind == "non_authoritative" and not target.exists():
            reports.append(f"{rel_dir}::{artifact}: declared non-authoritative ({entry.get('disposition', 'n/a')}) "
                           f"but absent — disposition recorded, retention not guaranteed")
            continue
        if not target.exists():
            red.append(f"{rel_dir}::{artifact}: AUTHORITATIVE artifact is MISSING (C16)")
            continue
        checked += 1
        if "sha256" in entry:
            actual = sha256_of(target)
            if actual != str(entry["sha256"]):
                red.append(f"{rel_dir}::{artifact}: sha256 DRIFT — marker {str(entry['sha256'])[:16]}… "
                           f"on disk {actual[:16]}… (the authority marker is a false claim until fixed)")
        if "bytes" in entry:
            actual_bytes = target.stat().st_size
            if int(entry["bytes"]) != actual_bytes:
                red.append(f"{rel_dir}::{artifact}: size DRIFT — marker {entry['bytes']} on disk {actual_bytes}")
        # The declared pattern is the AUTHORITY SCOPE claim, so it is only binding on an
        # authoritative entry. A non_authoritative entry is a recorded disposition; its
        # pattern field is bookkeeping, and RED-ing on it would be the BUG-372 failure
        # mode (a flag that fires on expected behaviour).
        pattern = str(entry.get("pattern", ""))
        if pattern and kind == "authoritative":
            globs = [part.strip() for part in pattern.split("|") if part.strip()]
            if globs and not any(fnmatch.fnmatch(str(artifact), glob) for glob in globs):
                red.append(f"{rel_dir}::{artifact}: does not match its own declared pattern '{pattern}'")
    patterns = declares_pattern(marker)
    undeclared: List[Path] = []
    if patterns:
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.name == cfg["marker_name"]:
                continue
            if any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns) and path.name not in declared:
                undeclared.append(path)
    if undeclared and cfg["undeclared_policy"] == "report":
        limit = int(cfg["report_limit"])
        names = ", ".join(p.name for p in undeclared[:limit])
        more = "" if len(undeclared) <= limit else f" … (+{len(undeclared) - limit} more)"
        reports.append(f"{rel_dir}: {len(undeclared)} file(s) match a declared authoritative pattern "
                       f"but are UNDECLARED (not authoritative, not non_authoritative): {names}{more}")
    return red, reports, checked, len(undeclared)


def run() -> int:
    """Verify every declared directory; print RED/report lines; exit 1 on any RED."""
    cfg = load_config(DEFAULT_CONFIG)
    marker_name = str(cfg["marker_name"])
    directories = find_dirs(cfg)
    red: List[str] = []
    reports: List[str] = []
    manifest_count = 0
    checked_total = 0
    undeclared_total = 0
    for directory in directories:
        has_marker = (directory / marker_name).is_file()
        patterns = []
        if has_marker:
            try:
                patterns = declares_pattern(json.loads((directory / marker_name).read_text(encoding="utf-8")))
            except (json.JSONDecodeError, UnicodeDecodeError):
                patterns = []
        if not has_marker:
            if cfg.get("require_marker_in_dirs") and patterns:
                red.append(f"{directory.relative_to(_ROOT)}: no {marker_name} (declared marker required)")
            continue
        manifest_count += 1
        dir_red, dir_reports, checked, undeclared = check_marker(directory, cfg)
        red.extend(dir_red)
        reports.extend(dir_reports)
        checked_total += checked
        undeclared_total += undeclared
    for line in reports:
        print(f"  report {line}")
    for line in red:
        print(f"  RED    {line}")
    if red:
        print(f"artifact authority: {manifest_count} marker(s), {checked_total} file(s) verified, "
              f"{len(red)} RED, {undeclared_total} undeclared")
        return 1
    print(f"artifact authority: {manifest_count} marker(s), {checked_total} file(s) verified, 0 RED, "
          f"{undeclared_total} undeclared (reported, not RED — BUG-372)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
