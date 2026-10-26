#!/usr/bin/env python3
"""Close the depth menu in code (BUG-416): config and the rubric's prose must agree, coded values must be members.

Three checks, all fail-closed: (1) the four ids/labels in config/depth_classes.yaml are 1-4 and unique;
(2) every class label appears in the rubric prose, and the rubric names no class the config lacks;
(3) any DEPTH value already present in the ANCHOR-4 sheet is a member of the menu (blank is fine - the
sheet is blind until the freeze).
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
CFG = REPO / "config" / "depth_classes.yaml"
RUBRIC = REPO / "governance" / "ANCHOR4_DEPTH_RUBRIC_20260923.md"
SHEET = REPO / "governance" / "ANCHOR4_DEPTH_BLIND_SHEET_20260923.csv"


def main() -> int:
    """Assert menu closure across config, prose and any coded values."""
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    classes = cfg["classes"]
    labels = [c["label"] for c in classes]
    ids = [c["id"] for c in classes]
    bad: list[str] = []
    if ids != [1, 2, 3, 4]:
        bad.append(f"ids must be exactly [1,2,3,4], got {ids}")
    if len(set(labels)) != len(labels):
        bad.append(f"duplicate labels: {labels}")
    prose = RUBRIC.read_text(encoding="utf-8").lower()
    for lab in labels:
        if lab not in prose:
            bad.append(f"rubric does not name class '{lab}'")
    for m in re.finditer(r"(?m)^\s*([1-9])\s*=\s*([a-z-]+)", RUBRIC.read_text(encoding="utf-8")):
        if m.group(2).lower() not in labels:
            bad.append(f"rubric names a class the config lacks: {m.group(0).strip()}")
    if SHEET.exists():
        for r in csv.DictReader(SHEET.open(encoding="utf-8")):
            v = (r.get("DEPTH (1-4)") or "").strip()
            if v and v not in {str(i) for i in ids} and v.lower() not in labels:
                bad.append(f"coded DEPTH '{v}' on {r.get('item_id')} is outside the closed menu")
            if v:
                break
    if bad:
        print("FAIL depth menu:")
        for b in bad:
            print("  ", b)
        return 1
    print(f"ok depth menu: {len(classes)} classes closed in config, rubric agrees, no out-of-menu code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
