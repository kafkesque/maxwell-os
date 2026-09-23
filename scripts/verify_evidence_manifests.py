#!/usr/bin/env python3
"""Verify frozen evidence receipts (D-342).

A ruling that rests on a measurement must cite a receipt artifact that cannot change
underneath it. ``governance/evidence/<ruling-id>/EVIDENCE_MANIFEST.json`` lists each
payload file with its ``sha256`` and ``bytes``; this script re-derives both from disk
and fails loud (RED + exit 1) on a missing file, a hash drift or a size drift.

Config-first (C12): roots, manifest name and ignore list come from
``config/evidence_manifest.yaml``; nothing is hardcoded here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "evidence_manifest.yaml"


def sha256_of(path: Path) -> str:
    """Return the hex sha256 of ``path``, streamed so large payloads stay cheap."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config() -> dict:
    """Load the YAML config; raise loudly if PyYAML is missing or the file is absent."""
    import yaml  # local import keeps the failure mode explicit

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"evidence manifest config missing: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def iter_manifests(roots: list[str], manifest_name: str) -> list[Path]:
    """Yield every manifest file under the configured roots, sorted for stable output."""
    found: list[Path] = []
    for root in roots:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        found.extend(sorted(base.rglob(manifest_name)))
    return found


def verify_manifest(manifest_path: Path, ignore_names: set[str]) -> tuple[list[str], int]:
    """Return (problems, checked_file_count) for one manifest."""
    problems: list[str] = []
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    receipts = manifest.get("receipts") or []
    if not receipts:
        problems.append(f"{manifest_path}: manifest declares no receipts")

    checked = 0
    declared_present: set[str] = set()
    for entry in receipts:
        rel = entry.get("file")
        if not rel:
            problems.append(f"{manifest_path}: receipt entry without a 'file' key")
            continue
        declared_present.add(Path(rel).name)
        target = manifest_path.parent / rel
        if not target.exists():
            problems.append(f"{manifest_path}: MISSING receipt payload {rel}")
            continue
        checked += 1
        observed_sha = sha256_of(target)
        if observed_sha != entry.get("sha256"):
            problems.append(
                f"{manifest_path}: DRIFT {rel} sha256 {observed_sha[:16]}… != declared {str(entry.get('sha256'))[:16]}…"
            )
        observed_bytes = target.stat().st_size
        if entry.get("bytes") is not None and observed_bytes != entry["bytes"]:
            problems.append(
                f"{manifest_path}: DRIFT {rel} bytes {observed_bytes} != declared {entry['bytes']}"
            )

    # An unlisted payload sitting next to a manifest is an undeclared receipt: it can rot unwatched.
    on_disk = {
        child.name
        for child in manifest_path.parent.iterdir()
        if child.is_file() and child.name not in ignore_names
    }
    for stray in sorted(on_disk - declared_present):
        problems.append(f"{manifest_path}: UNLISTED receipt file {stray} (declare it or remove it)")

    return problems, checked


def main() -> int:
    """CLI entrypoint: verify every evidence manifest; exit 1 when any problem is found."""
    config = load_config()
    roots = config.get("roots") or []
    manifest_name = config.get("manifest_name", "EVIDENCE_MANIFEST.json")
    ignore_names = set(config.get("ignore_names") or [])

    manifests = iter_manifests(roots, manifest_name)
    problems: list[str] = []
    total_checked = 0
    for manifest_path in manifests:
        manifest_problems, checked = verify_manifest(manifest_path, ignore_names)
        problems.extend(manifest_problems)
        total_checked += checked

    for problem in problems:
        print(f"  RED  {problem}")
    if problems:
        print(f"evidence receipts: {len(manifests)} manifest(s), {total_checked} file(s) - {len(problems)} RED")
        return 1

    print(
        f"evidence receipts: {len(manifests)} manifest(s), {total_checked} file(s) verified, 0 RED"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
