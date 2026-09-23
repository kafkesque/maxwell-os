#!/usr/bin/env python3
"""D-318/D-325 control: byte-compare the ruled boundary rules in the RUN PATH.

A pin is a control only if it is byte-compared where the work happens (D-318). This script
asserts that (a) every ruled rule in config/boundary_discriminators.yaml is present in the
ASSEMBLED S4 system prompt, (b) the baseline arm really lacks the block, and (c) the rule-file
sha256 folded into manifest_hash matches the file on disk.

BUG-395 (2026-09-23): the assertion follows the CONFIGURED state. When
stage4.boundary_inject_enabled is false (D-327 rejected the block on measurement) the SAME
rules must be ABSENT from both arms - a hardcoded "must be present" premise is a check that
cannot resolve the state it exists to check (BUG-375 class).

Exit 1 (fail-closed) on any mismatch in either state.

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

from pipeline.pipeline_paths import (  # noqa: E402
    S4_BOUNDARY_INJECT_ENABLED,
    S4_BOUNDARY_PATH,
)


def main() -> int:
    """Run the state-aware injection control and return a process exit code."""
    rules_path = ROOT / S4_BOUNDARY_PATH
    cfg = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    from pipeline.stage4_merged_call import system_prompt
    enabled = S4_BOUNDARY_INJECT_ENABLED
    treated, baseline = system_prompt(True), system_prompt(False)
    all_rules: list[tuple[str, str]] = [
        (f"default_home:{d['group']}", str(d["sentence"]).strip()[:80])
        for d in (cfg.get("default_home") or [])
    ] + [
        (f"test:{t['id']}", str(t["rule"]).strip()[:80])
        for t in (cfg.get("boundary_tests") or [])
    ]
    in_treated = [name for name, text in all_rules if text in treated]
    in_baseline = [name for name, text in all_rules if text in baseline]
    from pipeline.stamp import get_manifest_hash
    mh = get_manifest_hash()
    sha = hashlib.sha256(rules_path.read_bytes()).hexdigest()[:16]
    print(f"rules file      : {S4_BOUNDARY_PATH} (sha256[:16] {sha})")
    print(f"boundary_inject_enabled : {enabled}  (D-327 rejected the block -> expect False)")
    print(f"baseline prompt : {len(baseline)} chars | treated: {len(treated)} chars "
          f"(+{len(treated) - len(baseline)})")
    print(f"rules in treated/baseline : {len(in_treated)}/{len(in_baseline)} of {len(all_rules)}")
    print(f"manifest_hash   : {mh}")
    if enabled:
        missing = [name for name, _ in all_rules if name not in in_treated]
        if missing or in_baseline:
            print(f"FAIL missing={missing} baseline_leaks={in_baseline}")
            return 1
        state = f"PRESENT ({len(in_treated)} of {len(all_rules)} ruled rules, baseline clean)"
    else:
        if in_treated or in_baseline:
            print(f"FAIL boundary_inject_enabled=False but ruled rules are in the prompt: "
                  f"treated={in_treated} baseline={in_baseline}")
            return 1
        if len(treated) != len(baseline):
            print(f"FAIL boundary_inject_enabled=False but the arms differ: "
                  f"baseline {len(baseline)} chars vs treated {len(treated)} chars")
            return 1
        state = f"ABSENT from both arms (flag off; all {len(all_rules)} ruled rules withheld)"
    # D-318/D-325: the rule bytes are folded into the stamp IFF they were consumed by the
    # assembled prompt (stamp.py folds them in the enabled branch only). The control must
    # assert exactly that, otherwise it is a check that cannot resolve its own state.
    manifest_raw = str(_manifest_manifest())
    if enabled:
        if f"_s4_boundary_rules_sha256': '{sha}'" not in manifest_raw:
            print(f"FAIL rules sha256[:16] {sha} is not folded into manifest_hash (D-318)")
            return 1
        receipt = "rule-file bytes folded into manifest_hash"
    else:
        if "_s4_boundary_rules_sha256" in manifest_raw:
            print("FAIL boundary_inject_enabled=False but the stamp claims a boundary rule sha: "
                  "the prompt was not built from those bytes, so the stamp must not say it was")
            return 1
        receipt = "no boundary sha claimed in the stamp (ruled bytes were not consumed)"
    print(f"PASS - boundary rule block {state}; {receipt}")
    return 0


def _manifest_manifest() -> str:
    """Return the raw manifest dict (for the boundary-sha assertion) as a string."""
    from pipeline.stamp import _load_manifest
    return str(_load_manifest())


if __name__ == "__main__":
    raise SystemExit(main())
