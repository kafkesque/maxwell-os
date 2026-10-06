#!/usr/bin/env python3
"""register_s4_candidate.py — register a downloaded S4 candidate into the oMLX serving store.

D-2785 approved two S4 swap candidates. A model is served by oMLX ONLY when (1) its
snapshot is in the HF hub cache, (2) a symlink exists in ~/.omlx/models/<served-name>,
and (3) oMLX has (re)discovered it (scripts/omlx_reload.py, D-2637).

This script does the deterministic glue (symlink + per-model settings), copying the
gpt-oss-20b classifier entry as the template (guided_grammar_enabled=true,
enable_thinking=false, specprefill_enabled=false — the S4 classification config).
Crash-safe settings write (tempfile -> fsync -> os.replace, C6) + backup (C13).

Usage:
    python3 scripts/register_s4_candidate.py --repo mlx-community/gemma-4-12B-it-qat-OptiQ-4bit --name gemma-4-12B-it-qat-OptiQ-4bit --apply
    python3 scripts/register_s4_candidate.py ... --dry-run
Then:
    python3 scripts/omlx_reload.py
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

HOME = Path.home()
HF_HUB = HOME / ".cache" / "huggingface" / "hub"
MODELS_DIR = HOME / ".omlx" / "models"
SETTINGS = HOME / ".omlx" / "model_settings.json"
TEMPLATE = "gpt-oss-20b-MXFP4-Q8"


def find_snapshot(repo: str) -> Path:
    """Locate the latest complete snapshot dir for a hub repo (org--name)."""
    parts = repo.replace("/", "--")
    snap_root = HF_HUB / f"models--{parts}" / "snapshots"
    if not snap_root.exists():
        raise SystemExit(f"FAIL: no snapshot dir {snap_root} (download incomplete?)")
    snaps = [p for p in snap_root.iterdir() if p.is_dir()]
    if not snaps:
        raise SystemExit(f"FAIL: no snapshots under {snap_root}")
    # pick the one with the most files (complete download)
    snaps.sort(key=lambda p: sum(1 for _ in p.rglob("*") if _.is_file()), reverse=True)
    return snaps[0]


def make_symlink(name: str, snap: Path, dry: bool) -> str:
    dst = MODELS_DIR / name
    if dst.exists() or dst.is_symlink():
        return f"skip: {dst} exists (target={os.readlink(dst) if dst.is_symlink() else 'dir'})"
    if not dry:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        os.symlink(str(snap), str(dst))
    return f"symlink {name} -> {snap}"


def add_settings(name: str, dry: bool) -> str:
    """Copy the gpt-oss classifier template into a new entry (C6/C13 safe)."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    models = settings.setdefault("models", {})
    if name in models:
        return f"skip: settings already has {name}"
    tpl = models.get(TEMPLATE)
    if tpl is None:
        raise SystemExit(f"FAIL: template {TEMPLATE} missing from model_settings.json")
    entry = json.loads(json.dumps(tpl))  # deep copy
    entry["is_pinned"] = False
    entry["is_favorite"] = False
    entry["is_default"] = False
    entry["is_hidden"] = False
    models[name] = entry
    if dry:
        return f"[dry] would add settings entry {name}"
    bak = SETTINGS.with_suffix(f".json.bak-s4-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(SETTINGS, bak)
    fd, tmp = tempfile.mkstemp(dir=str(SETTINGS.parent), prefix=SETTINGS.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(settings, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, SETTINGS)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return f"settings entry {name} added (backup {bak.name})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="HF repo id, e.g. mlx-community/gemma-4-12B-it-qat-OptiQ-4bit")
    ap.add_argument("--name", required=True, help="oMLX served name (symlink name)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    snap = find_snapshot(args.repo)
    print(f"snapshot: {snap}")
    print(make_symlink(args.name, snap, args.dry_run))
    print(add_settings(args.name, args.dry_run))
    if args.dry_run:
        print("\n[dry-run] nothing written. Re-run with --apply then: python3 scripts/omlx_reload.py")
    elif not args.apply:
        print("\n(no --apply) nothing written. Re-run with --apply then: python3 scripts/omlx_reload.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
