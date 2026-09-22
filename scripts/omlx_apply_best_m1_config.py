#!/usr/bin/env python3
"""omlx_apply_best_m1_config.py — apply the M1 Max per-model "best config" spec.

Reads config/omlx_m1_best_config.yaml (the intent spec), applies ONLY the `apply`
class of settings to ~/.omlx/model_settings.json (crash-safe: tempfile -> fsync ->
os.replace, C6), then triggers an oMLX admin reload so the settings take effect.
`measure` and `system` classes are REPORTED, never auto-applied (D-332: adopt only
on a measured WIN; D-334 system lever needs sudo).

Usage:
    python3 scripts/omlx_apply_best_m1_config.py            # apply + report
    python3 scripts/omlx_apply_best_m1_config.py --dry-run  # report only, no write
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "config" / "omlx_m1_best_config.yaml"
SETTINGS_PATH = Path.home() / ".omlx" / "model_settings.json"


def load_spec() -> dict:
    """Load the intent spec (config-sourced, C12)."""
    with open(SPEC_PATH) as f:
        return yaml.safe_load(f)


def load_settings() -> dict:
    """Load the live oMLX per-model settings."""
    with open(SETTINGS_PATH) as f:
        return json.load(f)


def backup(settings_path: Path) -> Path:
    """Timestamped backup before any write (C13)."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = settings_path.with_suffix(f".json.bak-bestm1-{stamp}")
    shutil.copy2(settings_path, dest)
    return dest


def atomic_write(path: Path, data: dict) -> None:
    """Crash-safe write: tempfile -> fsync -> os.replace (C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def apply_spec(dry_run: bool) -> tuple[list[str], list[str]]:
    """Apply `apply` settings; return (applied, skipped_measure) change logs."""
    spec = load_spec()
    settings = load_settings()
    models = settings.get("models", {})
    applied: list[str] = []
    skipped: list[str] = []

    for name, specm in spec.get("models", {}).items():
        cfg = models.get(name)
        if cfg is None:
            skipped.append(f"{name}: NOT in model_settings.json (not discovered)")
            continue
        for key, val in (specm.get("apply") or {}).items():
            if cfg.get(key) == val:
                continue
            cfg[key] = val
            applied.append(f"{name}.{key}: {cfg.get(key)!r} -> {val!r}")

    if not dry_run and applied:
        bak = backup(SETTINGS_PATH)
        atomic_write(SETTINGS_PATH, settings)
        applied.append(f"backup: {bak.name}")
    return applied, skipped


def report_measure_and_system(spec: dict) -> None:
    """Print the measurement-gated and system-level levers (no auto-apply)."""
    print("\n[MEASURE] measurement-gated levers (run an A/B before adopting — D-332):")
    for name, specm in spec.get("models", {}).items():
        for m in specm.get("measure") or []:
            if isinstance(m, dict):
                k, v = next(iter(m.items()))
                print(f"  - {name}: {k} = {v}")
            else:
                print(f"  - {name}: {m}")
    print("\n[SYSTEM] system-level lever (needs sudo — surfaced only, D-334):")
    for lev in spec.get("system_levers", []):
        print(f"  - {lev['name']}: {lev['command']}  # {lev['reason']}")


def reload_omlx() -> None:
    """Re-read settings + re-discover models via the admin API (D-2637)."""
    import subprocess
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "omlx_reload.py")],
        capture_output=True, text=True, timeout=240,
    )
    if r.returncode != 0:
        print(f"WARN: oMLX reload returned {r.returncode}: {r.stderr.strip()[:200]}")
    else:
        print(r.stdout.strip())


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report only, do not write")
    args = ap.parse_args()

    spec = load_spec()
    applied, skipped = apply_spec(dry_run=args.dry_run)

    print(f"[APPLY] {'DRY-RUN (no write)' if args.dry_run else 'applied'}:")
    if applied:
        for line in applied:
            print(f"  {line}")
    else:
        print("  (all `apply` settings already at target — no change)")
    for line in skipped:
        print(f"  [skip] {line}")

    report_measure_and_system(spec)

    if not args.dry_run and any(a.startswith(("Qwen", "gpt", "gemma", "Phi")) for a in applied):
        print("\n[reload] re-reading oMLX settings...")
        reload_omlx()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
