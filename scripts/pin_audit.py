#!/usr/bin/env python3
"""pin_audit.py — byte-exact audit of every sha256 pin declared in config/eval_integrity.yaml.

BUG-345 (2026-09-21): the declared ruler pin carried a ONE-CHARACTER typo
(`...e15d32d4...` vs the real `...e15e32d4...`, index 34). Every prior "pin verified" check compared a
16-char PREFIX, so the pin passed for two sessions while pinning nothing. A control that cannot fail is
not a control: this audit compares FULL hashes, names every mismatch, and exits non-zero on drift.

Usage:  python3 scripts/pin_audit.py [--json]
Exit:   0 = every declared pin byte-matches; 1 = drift/missing; 2 = config unreadable.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
CFG = REPO / "config" / "eval_integrity.yaml"

# (config path to the hash, config path to the file it pins) — explicit, never inferred by proximity:
# inferring "the nearest filename" is how a pin silently ends up pointing at the wrong artifact.
PINS: tuple[tuple[str, str], ...] = (
    ("ruler_authority.authority_sha256", "ruler_authority.authority_json"),
    ("ruler_authority.workspace_sha256_at_head", "ruler_authority.human_workspace"),
    ("ruler_authority.annotation_sha256", "ruler_authority.annotation_source"),
    ("ruler_authority.key_sha256", "ruler_authority.key_file"),
    ("label_snapshots.stage5_t11.surviving_sha256", "label_snapshots.stage5_t11.surviving_path"),
)


def dig(cfg: dict, dotted: str) -> str:
    """Return the value at a dotted config path as a string ('' when absent)."""
    node: object = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return ""
        node = node[part]
    return str(node)


def main() -> int:
    """Compare every declared pin against the full sha256 of the file it names."""
    try:
        cfg = yaml.safe_load(CFG.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 - fail loudly, never silently (C16)
        print(f"FAIL: cannot read {CFG.name}: {exc}")
        return 2
    rows, bad = [], 0
    for hash_path, file_path in PINS:
        declared, target = dig(cfg, hash_path), dig(cfg, file_path)
        if not declared or not target:
            rows.append({"pin": hash_path, "status": "UNDECLARED", "declared": declared, "file": target})
            bad += 1
            continue
        f = REPO / target
        if not f.exists():
            rows.append({"pin": hash_path, "status": "MISSING_FILE", "declared": declared, "file": target})
            bad += 1
            continue
        actual = hashlib.sha256(f.read_bytes()).hexdigest()
        ok = actual == declared  # FULL equality (BUG-345)
        bad += 0 if ok else 1
        rows.append({"pin": hash_path, "status": "OK" if ok else "DRIFT",
                     "declared": declared, "actual": actual, "file": target,
                     "first_diff": None if ok else next((i for i, (x, y) in enumerate(zip(declared, actual)) if x != y), "length")})
    if "--json" in sys.argv:
        print(json.dumps({"pins": rows, "drift_n": bad}, indent=1))
    else:
        for r in rows:
            mark = {"OK": "OK  ", "DRIFT": "DRIFT", "MISSING_FILE": "MISS", "UNDECLARED": "NONE"}[r["status"]]
            extra = f" first_diff@{r['first_diff']}" if r["status"] == "DRIFT" else ""
            print(f"{mark} {r['pin']:52s} {r['declared'][:16]}{extra}")
        print(f"\nPINS: {len(rows)} checked, {bad} failing -> {'FAIL' if bad else 'PASS'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
