#!/usr/bin/env python3
"""Parse + validate frontier replies for the domain/depth pack (C12d: reject, never repair).

Enforces per reply: exactly one fenced CSV block, the exact header, the CLOSED domain and depth menus, no
duplicate item_ids, a non-empty evidence_quote, and only item_ids present in BLIND_INPUT_150.csv. A reply
that fails is refused whole - hand-fixing a parsed row would launder a machine error into the instrument.
Usage: python3 scripts/parse_frontier_pack.py governance/frontier_pack_20260924
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
HEADER = ["item_id", "domains", "domains_secondary", "depth", "conf_domain", "conf_depth",
          "evidence_quote", "rationale", "boundary_condition", "coder", "date"]


def menus() -> tuple[set[str], set[str]]:
    """Closed menus read from config - the authoritative surfaces, never prose."""
    dom = json.loads((REPO / "config" / "closed_menu_v5.json").read_text(encoding="utf-8"))["domains"]
    dep = yaml.safe_load((REPO / "config" / "depth_classes.yaml").read_text(encoding="utf-8"))["classes"]
    return ({(e["value"] if isinstance(e, dict) else e) for e in dom} | {"none_fits"},
            {c["label"] for c in dep} | {"none_fits"})


def main() -> int:
    """Validate every raw_<coder>_<chunk>.md under the given directory."""
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "governance/frontier_pack_20260924")
    doms, deps = menus()
    inputs = {r["item_id"] for r in csv.DictReader((root / "BLIND_INPUT_150.csv").open(encoding="utf-8"))}
    files = sorted(root.glob("raw_*.md"))
    if not files:
        print(f"no raw_*.md in {root} yet - nothing to parse")
        return 0
    seen: dict[str, str] = {}
    bad: list[str] = []
    for f in files:
        blocks = re.findall(r"```(?:csv)?\s*\n(.*?)```", f.read_text(encoding="utf-8"), re.S)
        if len(blocks) != 1:
            bad.append(f"{f.name}: expected 1 fenced CSV block, found {len(blocks)}")
            continue
        rows = list(csv.DictReader(io.StringIO(blocks[0].strip())))
        if not rows or list(rows[0].keys()) != HEADER:
            bad.append(f"{f.name}: header mismatch")
            continue
        for r in rows:
            i = r["item_id"]
            if i not in inputs:
                bad.append(f"{f.name}: unknown item_id {i}")
            if i in seen:
                bad.append(f"{f.name}: duplicate {i} (also {seen[i]})")
            seen[i] = f.name
            for v in (r["domains"] + "|" + (r["domains_secondary"] or "")).split("|"):
                if v.strip() and v.strip() not in doms:
                    bad.append(f"{f.name}:{i}: domain '{v.strip()}' outside the closed menu")
            if r["depth"].strip() not in deps:
                bad.append(f"{f.name}:{i}: depth '{r['depth'].strip()}' outside the closed menu")
            if not (r["evidence_quote"] or "").strip():
                bad.append(f"{f.name}:{i}: empty evidence_quote")
    if bad:
        print(f"FAIL parsed frontier replies: {len(bad)} problem(s)")
        for b in bad[:20]:
            print("  ", b)
        return 1
    print(f"ok parsed frontier replies: {len(files)} file(s), {len(seen)} rows validated, menus closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
