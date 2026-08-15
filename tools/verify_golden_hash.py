#!/usr/bin/env python3
"""Verify the golden few-shot set SHA-256 against .golden_meta.json (D2362/Grok-0011 fix).

Wires the previously-inert 12-char truncated hash into a real, consumable
provenance check. C12-compliant: the expected hash lives in .golden_meta.json
(data, not code); the golden path comes from config stage2.golden_path.

Exit codes: 0 = verified, 1 = missing/truncated/mismatch. Gate this in canary
preflight so a silently-edited golden set can never ship un-stamped.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

META_PATH = PROJECT_ROOT / "config" / "golden" / ".golden_meta.json"
SHA256_HEX_LEN = 64


def main() -> int:
    from pipeline.pipeline_paths import S2_GOLDEN_PATH

    golden_path = PROJECT_ROOT / S2_GOLDEN_PATH
    meta = json.loads(META_PATH.read_text())

    expected = meta.get("golden_sha256", "")
    actual = hashlib.sha256(golden_path.read_bytes()).hexdigest()

    print(f"golden path : {golden_path}")
    print(f"expected    : {expected}")
    print(f"actual      : {actual}")

    if not expected:
        print("FAIL: .golden_meta.json has no golden_sha256")
        return 1
    if len(expected) != SHA256_HEX_LEN:
        print(f"FAIL: stored hash is {len(expected)} chars (truncated, not full SHA-256)")
        return 1
    if expected != actual:
        print("FAIL: hash mismatch — golden set changed without re-stamping .golden_meta.json")
        return 1
    print("PASS: golden hash verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
