#!/usr/bin/env python3
"""scripts/verify_frozen_pair.py - a frozen pair is only citable while its bytes still match (C-3).

The C-3 lesson: a completed run whose input is rewritten in place becomes uncitable, and the discovery only
happens hours later. A frozen pair fixes that - but only if the copy itself does not drift. This re-derives
sha256 for every file listed in the frozen manifest and exits 1 on any mismatch (C16 fail-loud).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = PROJECT_ROOT / "config/eval_integrity.yaml"


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file, streamed."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    """Verify every frozen manifest declared in config/eval_integrity.yaml (C12: no path is hardcoded)."""
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    refs = ((cfg.get("eval") or {}).get("frozen_manifests")) or []
    if not refs:
        print("  ok   no frozen manifests declared yet")
        return 0
    red: list[str] = []
    checked = 0
    for rel in refs:
        man = json.loads((PROJECT_ROOT / rel).read_text(encoding="utf-8"))
        for f, meta in (man.get("files") or {}).items():
            p = PROJECT_ROOT / f
            if not p.exists():
                red.append(f"{f}: MISSING but declared frozen (C-3: an uncitable reference)")
                continue
            checked += 1
            got = sha256_file(p)
            if got != meta["sha256"] or p.stat().st_size != meta["bytes"]:
                red.append(f"{f}: drifted (frozen {meta['sha256'][:12]}..., on disk {got[:12]}...)")
    print(f"frozen pairs: {checked} file(s) verified across {len(refs)} manifest(s) - {len(red)} RED")
    for r in red:
        print(f"  RED  {r}")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
