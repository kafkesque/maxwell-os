#!/usr/bin/env python3
"""Make `the depth axis is NOT load-bearing` (D-394) a rail instead of a paragraph.

WHY (BUG-462 class)
    A declaration with no consumer is a comment. D-394 says nothing may decide on the depth axis while its
    measured agreement sits below the reporting floor and two of its four declared coders have never run:
    no gate, no anchor edit, no depth head. Written in prose, that promise is invisible to every check -
    and the failure it prevents (a head trained on a 3-rater axis, a class decided by a band) would arrive
    silently, because nothing in the repo looks for it.

WHAT IT CHECKS
    Every probe is READ FROM CONFIG (config/depth_domain_contract.yaml#load_bearing), never invented here:
    a forbidden act is listed as a TRACE it would leave on disk, and this script exits 1 the moment one of
    those traces appears while `enabled: false`. When the owner flips `enabled` (after D-396 completes the
    panel and the axis clears the operative floor) the probes stop being prohibitions and become a report.

Exit: 0 no forbidden trace | 1 a forbidden trace is present (the declaration is being violated)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "config" / "depth_domain_contract.yaml"


def resolve(dotted: str) -> tuple[bool, Any]:
    """Resolve `path/to/file.yaml#a.b.c`; returns (found, value). A missing file is a defect, not a pass."""
    path_s, _, key = dotted.partition("#")
    p = REPO / path_s
    if not p.exists():
        raise SystemExit(f"FAIL depth-load-bearing: declaration cites {path_s}, which does not exist")
    doc: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    for part in [k for k in key.split(".") if k]:
        if not isinstance(doc, dict) or part not in doc:
            return False, None
        doc = doc[part]
    return True, doc


def main() -> int:
    """Report every forbidden trace that is present while the axis is declared non-load-bearing."""
    cfg = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    lb = cfg.get("load_bearing")
    if not lb:
        print("FAIL depth-load-bearing: config/depth_domain_contract.yaml declares no `load_bearing` block; "
              "the prohibition is prose again (BUG-462 class)")
        return 1
    enabled = bool(lb.get("enabled"))
    mode = "REPORTING (axis declared load-bearing)" if enabled else "PROHIBITIVE (axis declared NOT load-bearing)"
    print(f"depth load-bearing: enabled={enabled} decided={lb.get('decided')} -- {mode}")
    bad: list[str] = []
    for probe in lb.get("forbidden_traces") or []:
        kind = probe.get("kind")
        if kind == "value_must_be":
            found, got = resolve(probe["key"])
            if not found:
                bad.append(f"{probe['key']} is MISSING (expected {probe['expect']!r})")
            elif got is not probe["expect"] and got != probe["expect"]:
                bad.append(f"{probe['key']} is {got!r}, must stay {probe['expect']!r} - {probe.get('why','')}")
        elif kind == "key_absent_or_false":
            found, got = resolve(probe["key"])
            if found and got not in (False, None, "", 0, "false"):
                bad.append(f"{probe['key']} is {got!r}, must be absent or false - {probe.get('why','')}")
        elif kind == "glob_absent":
            for pat in probe["patterns"]:
                hits = sorted(str(h.relative_to(REPO)) for h in REPO.glob(pat))
                if hits:
                    bad.append(f"{pat} exists ({hits[:3]}) - {probe.get('why','')}")
        else:
            bad.append(f"undeclared probe kind {kind!r} - a probe this script cannot evaluate is not a check")
    if bad and not enabled:
        print(f"FAIL depth-load-bearing: {len(bad)} forbidden trace(s) present while the axis is declared "
              "non-load-bearing (D-394):")
        for b in bad:
            print("  ", b)
        return 1
    if bad:
        print(f"note: {len(bad)} forbidden trace(s) present, reported because the axis is declared load-bearing:")
        for b in bad:
            print("  ", b)
    else:
        print(f"ok depth-load-bearing: {len(lb.get('forbidden_traces') or [])} trace probe(s) checked, none present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
