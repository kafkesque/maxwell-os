#!/usr/bin/env python3
"""RAIL 2 (BUG-430): refuse to build or adopt a sheet whose item set is a UNION of cohorts.

Concatenating two instruments yields a third instrument: 216 + 150 = 364 rows of which 148 lack a domain
axis and 214 lack CT/DISC/ET. It looks like a merge and it is a new object nobody adjudicated. Rail: a
candidate sheet must be a subset of exactly ONE registered cohort.
Usage: python3 scripts/check_instrument_cohorts.py <sheet.csv> [--key item_id] [--apply-check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "config" / "anchor_family.yaml"


def cohort_sets() -> dict[str, set[str]]:
    """Registered cohorts as item-id sets: the anchor family and the colliding external cohort."""
    cfg = yaml.safe_load(REG.read_text(encoding="utf-8"))
    anchor = {r["item_id"] for r in csv.DictReader((REPO / cfg["anchor"]["sheet"]).open(encoding="utf-8"))}
    ext = cfg["axes"]["domains"]
    other: set[str] = set()
    p = REPO / ext["artifact"]
    if p.exists():
        import json
        other = {json.loads(l).get("out_id", "") for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}
    return {"anchor": anchor, "domains_cohort": {o for o in other if o}}


def main() -> int:
    """Assert the candidate's items come from one cohort only."""
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("--key", default="item_id")
    a = ap.parse_args()
    rows = list(csv.DictReader((REPO / a.sheet).open(encoding="utf-8")))
    ids = {(r.get(a.key) or "").strip() for r in rows} - {""}
    cs = cohort_sets()
    pure = [n for n, s in cs.items() if ids and ids <= s]
    partial = {n: len(ids & s) for n, s in cs.items() if ids & s}
    if len(pure) == 1 and len(partial) <= 1:
        print(f"ok cohorts: {a.sheet} -> {len(ids)} items, cohort '{pure[0]}' only")
        return 0
    print(f"FAIL cohorts: {a.sheet} item set spans {len(partial)} registered cohorts "
          f"({ {k: v for k, v in partial.items()} }) - concatenating instruments is not a merge")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
