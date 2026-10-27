#!/usr/bin/env python3
"""List (and optionally prune) phantom model entries in the oMLX model registry.

A PHANTOM is a model id that the oMLX server still advertises but whose bytes no
longer resolve anywhere on disk (D-3034: a declaration whose realpath lands nowhere).
Two forms resolve:

  * canonical name  ->  <model_dir>/<name>  (a symlink or a real dir)
  * HF-cache alias  ->  ~/.cache/huggingface/hub/models--<name>  (the name already
     carries the `org--repo` separator, so the hub dir is `models--` + name)

This is the same resolution rule the BUG-1037 phantom check must apply in
tools/bench_preflight.py: an inventory id whose bytes do not resolve is UNSAFE.

Reads its paths from config/engine.yaml (engine.model_dir) and falls back to the
documented defaults under Path.home(). No model name is hardcoded here (C12).

Usage:
    python3 scripts/list_model_phantoms.py            # list phantoms, no writes
    python3 scripts/list_model_phantoms.py --apply    # back up + prune (crash-safe)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_ENGINE_YAML = _REPO / "config" / "engine.yaml"

DEFAULT_SETTINGS = Path.home() / ".omlx" / "model_settings.json"
DEFAULT_MODEL_DIR = Path.home() / ".omlx" / "models"
DEFAULT_HUB = Path.home() / ".cache" / "huggingface" / "hub"


def _load_yaml(path: Path) -> dict:
    """Load a YAML file fail-closed (a missing config must not pass silently, C16)."""
    import yaml  # local import: keeps the tool usable even where yaml is absent

    if not path.is_file():
        raise RuntimeError(f"missing config: {path}")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _engine_paths() -> tuple[Path, Path]:
    """Return (model_dir, settings) from config/engine.yaml, else documented defaults."""
    model_dir = DEFAULT_MODEL_DIR
    settings = DEFAULT_SETTINGS
    if _ENGINE_YAML.is_file():
        eng = _load_yaml(_ENGINE_YAML).get("engine") or {}
        if eng.get("model_dir"):
            model_dir = Path(os.path.expanduser(str(eng["model_dir"])))
        if eng.get("settings") and Path(os.path.expanduser(str(eng["settings"]))).name == "model_settings.json":
            settings = Path(os.path.expanduser(str(eng["settings"])))
    return model_dir, settings


def _resolves(name: str, model_dir: Path, hub: Path) -> bool:
    """Return True if the model id's bytes resolve on disk (canonical dir or HF alias)."""
    if "--" in name:
        return (hub / f"models--{name}").exists()
    return (model_dir / name).exists()


def list_phantoms(model_dir: Path, settings: Path, hub: Path) -> list[str]:
    """Return model ids in the registry whose bytes do not resolve."""
    with settings.open(encoding="utf-8") as handle:
        data = json.load(handle)
    models = data.get("models") or {}
    return [name for name in models if not _resolves(name, model_dir, hub)]


def _crash_safe_write(path: Path, data: dict) -> None:
    """Write JSON via tempfile + fsync + os.replace (C6), preserving file mode."""
    serialized = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _backup(path: Path) -> Path:
    """Copy the registry to a timestamped .bak before any prune (C13)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(path.name + f".bak-phantom-prune-{stamp}")
    shutil.copy2(path, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    """Discover phantoms; with --apply, back up and prune them."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="back up and prune phantom entries")
    parser.add_argument("--settings", type=Path, default=None, help="override model_settings.json path")
    args = parser.parse_args(argv)

    model_dir, settings = _engine_paths()
    if args.settings is not None:
        settings = args.settings
    hub = DEFAULT_HUB

    if not settings.is_file():
        print(f"ERR registry missing: {settings}", file=sys.stderr)
        return 1

    phantoms = list_phantoms(model_dir, settings, hub)
    if not phantoms:
        print("no phantoms: every registered model id resolves")
        return 0

    print(f"{len(phantoms)} phantom(s) — registered id whose bytes do not resolve:")
    for name in phantoms:
        print(f"  - {name}")

    if not args.apply:
        return 0

    backup = _backup(settings)
    print(f"backup: {backup}")
    with settings.open(encoding="utf-8") as handle:
        data = json.load(handle)
    models = data.get("models") or {}
    for name in phantoms:
        models.pop(name, None)
    _crash_safe_write(settings, data)
    print(f"pruned {len(phantoms)} phantom(s) from {settings}")
    print("NEXT: python3 scripts/omlx_reload.py   # re-discover models WITHOUT a full restart (D-2637)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
