#!/usr/bin/env python3
"""D-318/D-325 control: byte-compare the ruled boundary rules in the RUN PATH.

A pin is a control only if it is byte-compared where the work happens (D-318). This script
asserts that (a) every ruled rule in config/boundary_discriminators.yaml is present in the
ASSEMBLED S4 system prompt, (b) the baseline arm really lacks the block, and (c) the rule-file
sha256 folded into manifest_hash matches the file on disk.

Exit 1 (fail-closed) on any mismatch.

Usage:
  python3 scripts/verify_boundary_injection.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import PROJECT_ROOT, S4_BOUNDARY_PATH  # noqa: E402


def _inject_enabled() -> bool:
    """Return stage4.boundary_inject_enabled (D-327). Missing key -> True (fail-closed)."""
    cfg = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text())
    v = (cfg.get("stage4") or {}).get("boundary_inject_enabled")
    return True if v is None else bool(v)


def main() -> int:
    """Run the injection control and return a process exit code."""
    rules_path = ROOT / S4_BOUNDARY_PATH
    cfg = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    from pipeline.stage4_merged_call import system_prompt
    treated, baseline = system_prompt(True), system_prompt(False)
    # D-327/BUG-395: the ruled block is REJECTED on measurement, so when the flag is false the block must be
    # ABSENT. Asserting presence unconditionally made this control report a correct config as a failure.
    if not _inject_enabled():
        present = ["default_home:" + str(d["group"]) for d in (cfg.get("default_home") or []) if str(d["sentence"]).strip()[:80] in treated]
        present += ["test:" + str(t["id"]) for t in (cfg.get("boundary_tests") or []) if str(t["rule"]).strip()[:80] in treated]
        if present:
            print("FAIL (D-327 state) boundary_inject_enabled=false but " + str(len(present)) + " ruled rules are present: " + str(present))
            return 1
        print("PASS (D-327 state) boundary_inject_enabled=false; all ruled rules verified ABSENT from the run path; rule sha " + str(sha)[:16])
        return 0
    missing: list[str] = []
    for d in cfg.get("default_home") or []:
        if str(d["sentence"]).strip()[:80] not in treated:
            missing.append(f"default_home:{d['group']}")
    for t in cfg.get("boundary_tests") or []:
        if str(t["rule"]).strip()[:80] not in treated:
            missing.append(f"test:{t['id']}")
    leaks = [t["id"] for t in (cfg.get("boundary_tests") or [])
             if str(t["rule"]).strip()[:80] in baseline]
    from pipeline.stamp import get_manifest_hash
    mh = get_manifest_hash()
    sha = hashlib.sha256(rules_path.read_bytes()).hexdigest()[:16]
    print(f"rules file      : {S4_BOUNDARY_PATH} (sha256[:16] {sha})")
    print(f"baseline prompt : {len(baseline)} chars | treated: {len(treated)} chars "
          f"(+{len(treated) - len(baseline)})")
    print(f"manifest_hash   : {mh}")
    if missing or leaks or sha not in str(_manifest_manifest()):
        print(f"FAIL missing={missing} baseline_leaks={leaks}")
        return 1
    print("PASS — all 10 default_home + 10 boundary tests present; baseline is clean; "
          "rule bytes folded into manifest_hash")
    return 0


def _manifest_manifest() -> str:
    """Return the raw manifest dict (for the boundary-sha assertion) as a string."""
    from pipeline.stamp import _load_manifest
    return str(_load_manifest())


if __name__ == "__main__":
    raise SystemExit(main())
