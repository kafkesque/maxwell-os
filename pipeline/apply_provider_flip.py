#!/usr/bin/env python3
"""apply_provider_flip.py -- governed, backup-first edit of ~/.config/goose/config.yaml.

Implements the D-3023/D-3024 provider inversion in the SAFE order. There is no
silent partial write: every edit is an exact-string replacement that must match
exactly once, the file is backed up before the first write, and --rollback
restores the newest backup. Default is --dry-run (no writes).

Phases:
  now  (safe, no flip): disable nvidia.enabled, lower GOOSE_THINKING_EFFORT.
  flip (AFTER T-137):   pin maxwell_omlx.model -> gemma-4-E4B-it-MLX-4bit, then
                        flip active_provider -> maxwell_omlx.

Usage:
  python3 apply_provider_flip.py                 # dry-run: print plan, write nothing
  python3 apply_provider_flip.py --apply-now     # steps 3+4 only (safe)
  python3 apply_provider_flip.py --apply-flip    # steps 1+2 only (requires T-137)
  python3 apply_provider_flip.py --apply-all     # steps 1..4 in order
  python3 apply_provider_flip.py --rollback      # restore newest backup
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

CFG = Path(os.environ.get("GOOSE_CONFIG", Path.home() / ".config" / "goose" / "config.yaml"))

# (label, exact_old_block, exact_new_block, phase)
EDITS: list[tuple[str, str, str, str]] = [
    (
        "pin maxwell_omlx.model -> gemma-4-E4B-it-MLX-4bit",
        "  maxwell_omlx:\n    enabled: true\n    model: Qwen3-Coder-30B-A3B-Instruct-MLX-4bit\n",
        "  maxwell_omlx:\n    enabled: true\n    model: gemma-4-E4B-it-MLX-4bit\n",
        "flip",
    ),
    (
        "flip active_provider -> maxwell_omlx",
        "active_provider: custom_deepseek\n",
        "active_provider: maxwell_omlx\n",
        "flip",
    ),
    (
        "disable nvidia.enabled -> false",
        "  nvidia:\n    enabled: true\n",
        "  nvidia:\n    enabled: false\n",
        "now",
    ),
    (
        "lower GOOSE_THINKING_EFFORT -> medium",
        "GOOSE_THINKING_EFFORT: high\n",
        "GOOSE_THINKING_EFFORT: medium\n",
        "now",
    ),
]


def _newest_backup() -> Path | None:
    """Return the newest config.yaml.bak.* file, or None."""
    backups = sorted(CFG.parent.glob(f"{CFG.name}.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return backups[0] if backups else None


def _backup() -> Path:
    """Copy the current config to a timestamped .bak and return its path."""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    dst = CFG.parent / f"{CFG.name}.bak.{stamp}"
    dst.write_bytes(CFG.read_bytes())
    return dst


def _crash_safe_write(content: str) -> None:
    """tempfile -> fsync -> os.replace (C6 crash-safe write)."""
    fd, tmp = tempfile.mkstemp(dir=str(CFG.parent), prefix=f"{CFG.name}.tmp.")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, CFG)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _apply(edits: list[tuple[str, str, str, str]], dry_run: bool) -> int:
    if not CFG.exists():
        print(f"FATAL: {CFG} does not exist.", file=sys.stderr)
        return 1
    content = CFG.read_text()
    plan: list[tuple[str, str]] = []
    for label, old, new, _phase in edits:
        n = content.count(old)
        if n != 1:
            print(f"FATAL: edit '{label}' matched {n} time(s), expected exactly 1. "
                  f"Refusing to write (config may have drifted).", file=sys.stderr)
            return 1
        plan.append((label, old))
    if dry_run:
        print(f"DRY-RUN on {CFG}: would apply {len(plan)} edit(s):")
        for label, _old in plan:
            print(f"  - {label}")
        return 0
    backup = _backup()
    print(f"backup: {backup}")
    for label, old, new, _phase in edits:
        content = content.replace(old, new, 1)
        print(f"applied: {label}")
    _crash_safe_write(content)
    print(f"OK: {len(plan)} edit(s) applied to {CFG}.")
    return 0


def _rollback() -> int:
    backup = _newest_backup()
    if backup is None:
        print("FATAL: no backup found to roll back to.", file=sys.stderr)
        return 1
    _crash_safe_write(backup.read_text())
    print(f"OK: restored {CFG} from {backup}.")
    return 0


def _warn_flip() -> None:
    print("WARNING: the FLIP phase requires T-137 to be GREEN first:", file=sys.stderr)
    print("  1. maxwell_omlx.model pinned to gemma-4-E4B-it-MLX-4bit", file=sys.stderr)
    print("  2. tiered cache A/B proven (declared bar 5.0x)", file=sys.stderr)
    print("  3. R5 cross-family review of pipeline/delegation_economy.py", file=sys.stderr)
    print("Without these, multi-turn decode may collapse (DELEGATE-002).", file=sys.stderr)


def main(argv: list[str]) -> int:
    mode = argv[0] if argv else "--dry-run"
    if mode == "--rollback":
        return _rollback()
    if mode == "--apply-now":
        return _apply([e for e in EDITS if e[3] == "now"], dry_run=False)
    if mode == "--apply-flip":
        _warn_flip()
        return _apply([e for e in EDITS if e[3] == "flip"], dry_run=False)
    if mode == "--apply-all":
        _warn_flip()
        return _apply(EDITS, dry_run=False)
    if mode in ("--dry-run", "-h", "--help"):
        print("DRY-RUN / usage:")
        print("  --apply-now   steps 3+4 (safe, no flip)")
        print("  --apply-flip  steps 1+2 (requires T-137)")
        print("  --apply-all   steps 1..4 in order")
        print("  --rollback    restore newest backup")
        return _apply(EDITS, dry_run=True)
    print(f"FATAL: unknown mode '{mode}'.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
