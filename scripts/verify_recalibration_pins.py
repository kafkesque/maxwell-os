#!/usr/bin/env python3
"""scripts/verify_recalibration_pins.py - the recalibration trigger (D-353).

Every artifact the abstention / classification measurement depends on is digest-pinned. If one changes
without a new decision id in config/decisions.yaml, the measurement on disk is stale and this goes RED
with exit 1. This is the trigger whose absence caused BUG-391 (a ratified point measured on a reference
that then moved). Read-only, deterministic, no LLM.
"""
from __future__ import annotations

import hashlib, pathlib, re, sys

import yaml

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PINS = _ROOT / "config" / "recalibration_pins.yaml"
_DECISIONS = _ROOT / "config" / "decisions.yaml"


def digest(rel: str) -> str:
    """sha256 of a repo-relative file."""
    return hashlib.sha256((_ROOT / rel).read_bytes()).hexdigest()


def main() -> int:
    """Compare every pin to disk and to the decision registry; exit 1 on any RED."""
    cfg = yaml.safe_load(_PINS.read_text())
    ids = set(re.findall(r"^- id: (D-\d+)", _DECISIONS.read_text(), re.M))
    red = []
    for name, pin in cfg["pins"].items():
        p = _ROOT / pin["path"]
        if not p.exists():
            red.append(name + ": pinned path is missing: " + pin["path"])
            continue
        if digest(pin["path"]) != pin["sha256"]:
            red.append(name + ": " + pin["path"] + " CHANGED since it was pinned - re-run the measurement and mint a new decision (this is the BUG-391 class)")
        if pin["decision"] not in ids:
            red.append(name + ": pinned to decision " + pin["decision"] + " which is not in config/decisions.yaml")
    for line in red:
        print("RED  " + line)
    print("recalibration pins: " + str(len(cfg["pins"])) + " pinned, " + str(len(red)) + " RED")
    return 1 if red else 0


if __name__ == "__main__":
    raise SystemExit(main())
