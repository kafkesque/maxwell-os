#!/usr/bin/env python3
"""freeze_run_manifest.py — D2440/D2439: freeze a reproducible run manifest.

A knowledge-generation run (the BUG-165 S4→S5→S6 rerun) must NOT run against a
moving target. This script captures a SHA-256 fingerprint of everything that
shapes the corpus — config, taxonomy, golden few-shot prompts, dependency
manifest, model lineup, and git HEAD — into a single `run_manifest.json`.

C12: all paths derived from repo root; no hardcoded user paths.
R14: every persistent object is stamped — this is the *run-level* stamp that
binds the whole corpus to the exact inputs that produced it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / "config"
GOLDEN_DIR = CONFIG_DIR / "golden"

# C12: the config files whose content materially shapes pipeline behaviour.
CONFIG_FILES: list[str] = [
    "pipeline_config.yaml",
    "taxonomy_v5.yaml",
    "content_types.yaml",
    "filtering.yaml",
    "synonym_map.yaml",
    "model_assignments.yaml",
    "intimacy_policy.yaml",
    "domain_anchors.yaml",
    "domain_disciplines.yaml",
    "version.yaml",
]

# Golden few-shot prompts drive S2/S4 extraction behaviour — include them.
GOLDEN_GLOBS: list[str] = [
    "stage2_fewshot_*.yaml",
]

# Dependency manifest, if present.
REQUIREMENTS_FILES: list[str] = [
    "requirements.txt",
]


def _sha256(path: Path) -> str:
    """SHA-256 of a file's bytes (stable, ignores mtime)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    """Full git commit hash (or 'unknown')."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _git_status_dirty() -> bool:
    """True if the working tree has uncommitted changes."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        return bool(out.stdout.strip())
    except Exception:
        return False


def _load_manifest() -> dict:
    """Load pipeline_manifest from config (mirrors pipeline/stamp.py D2282)."""
    import yaml
    cfg_path = CONFIG_DIR / "pipeline_config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("pipeline_manifest", {})


def build_manifest() -> dict:
    """Assemble the full frozen manifest."""
    files: dict[str, str] = {}

    for name in CONFIG_FILES:
        p = CONFIG_DIR / name
        if p.exists():
            files[f"config/{name}"] = _sha256(p)

    for glob in GOLDEN_GLOBS:
        for p in sorted(GOLDEN_DIR.glob(glob)):
            files[f"config/golden/{p.name}"] = _sha256(p)

    for name in REQUIREMENTS_FILES:
        p = REPO_ROOT / name
        if p.exists():
            files[f"{name}"] = _sha256(p)

    pipeline_manifest = _load_manifest()

    manifest = {
        "schema_version": "1.0",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_manifest": pipeline_manifest,
        "git_head": _git_head(),
        "working_tree_dirty": _git_status_dirty(),
        "file_hashes": files,
    }

    # Aggregate hash binds the whole manifest (deterministic sort_keys).
    manifest["run_fingerprint"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, default=str).encode()
    ).hexdigest()

    return manifest


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Freeze a reproducible run manifest (D2440).")
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "knowledge pipeline" / "run_manifest.json",
        help="Output path for the frozen manifest (default: knowledge pipeline/run_manifest.json)",
    )
    args = ap.parse_args()

    manifest = build_manifest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    print(f"🧊 Run manifest frozen → {args.out}")
    print(f"   git_head:      {manifest['git_head']}")
    print(f"   dirty:         {manifest['working_tree_dirty']}")
    print(f"   fingerprint:   {manifest['run_fingerprint'][:16]}…")
    print(f"   files hashed:  {len(manifest['file_hashes'])}")
    if manifest["working_tree_dirty"]:
        print("   ⚠️  WORKING TREE DIRTY — manifest is a point-in-time snapshot, not a clean freeze.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
