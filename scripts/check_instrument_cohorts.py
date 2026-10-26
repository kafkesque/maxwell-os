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
    # D-2868: `artifact` now names the domains AXIS authority (201-row rederived_v8 golden pool),
    # whose 7 emerging/noise exclusions make it a NON-superset of the 150 anchor ruler. The
    # concat-guard must compare a candidate against the full FAMILY instrument population
    # (208 rows), declared as `cohort_artifact`; fall back to `artifact` only when absent.
    p = REPO / ext.get("cohort_artifact", ext["artifact"])
    if p.exists():
        # D-2720/D-2785 repointed the domains artifact from the fb_id-keyed
        # s4_domain_verdicts.jsonl to the item_id-keyed 208-row five-axis CSV.
        # Read by declared key (C12) and by format, not by a hardcoded JSONL shape.
        key = ext.get("cohort_artifact_key", "item_id")
        if p.suffix.lower() == ".jsonl":
            import json
            other = {json.loads(l).get(key, "") for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}
        elif p.suffix.lower() == ".json":
            import json
            other = {r.get(key, "").strip() for r in json.loads(p.read_text(encoding="utf-8")).get("rows", [])}
        else:
            other = {r.get(key, "").strip() for r in csv.DictReader(p.open(encoding="utf-8"))}
    cs = {"anchor": anchor, "domains_cohort": {o for o in other if o}}
    # D-2720/D-2785 folded the 58 depth extras into the anchor family (150 -> 208), so the
    # five-axis domains view (208) is now a proper SUPERSET of the anchor ruler (150). A cohort
    # that is a proper superset of another is not a SECOND instrument: the concat-guard must
    # compare against the smallest cohort that contains a candidate, else any anchor sheet reads
    # as "spanning" two nested sets. Drop proper supersets here.
    supersets = {n for n in cs for m in cs if m != n and cs[n] > cs[m]}
    return {n: s for n, s in cs.items() if n not in supersets}


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
