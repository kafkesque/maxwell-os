#!/usr/bin/env python3
"""build_anchor_v8_remap_csv.py — deterministic domain remap CSV for the v8 menu (D-2865).

Reads the two LIVE anchor artifacts (the A/B referee and the 4-axis golden pool) and emits
an owner-sign-off CSV of every row whose DOMAIN label list contains a label removed by the
v8 taxonomy edit ('science & research' merged, 'social sciences' demoted). Remap target is
deterministic and LLM-free (D-2864 pattern): BOTH removed labels -> 'research practice',
then dedupe. owner_decision is PRE-FILLED 'research practice' — the owner signs off, does
not re-decide. Discipline axis is NEVER touched.

Output: governance/anchor_v8_domain_remap_20261007.csv
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFEREE = ROOT / "governance" / "discipline_anchor_rederived_v7_20261007.json"
GOLD4 = ROOT / "governance" / "gold_4axis.jsonl"
OUT = ROOT / "governance" / "anchor_v8_domain_remap_20261007.csv"

REMOVED = ("science & research", "social sciences")
TARGET = "research practice"


def remap(domains: list[str]) -> tuple[list[str], list[str]]:
    removed = [d for d in domains if d in REMOVED]
    new = []
    for d in domains:
        new.append(TARGET if d in REMOVED else d)
    # dedupe preserving order
    seen, out = set(), []
    for d in new:
        if d in seen:
            continue
        seen.add(d)
        out.append(d)
    return removed, out


def main() -> int:
    rows: list[dict] = []

    # 1. A/B referee
    ref = json.loads(REFEREE.read_text(encoding="utf-8"))
    for r in ref["rows"]:
        doms = r.get("domains") or []
        removed, new = remap(doms)
        if removed:
            rows.append({
                "source": "ab_referee_v7",
                "item_id": r.get("item_id"),
                "name": r.get("name"),
                "discipline": r.get("discipline"),
                "current_domains": json.dumps(doms, ensure_ascii=False),
                "removed": ";".join(removed),
                "proposed_domains": json.dumps(new, ensure_ascii=False),
                "owner_decision": TARGET,
                "note": "v8 merge(demote): science & research / social sciences -> research practice",
            })

    # 2. gold_4axis.jsonl
    for line in GOLD4.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        doms = r.get("domains") or []
        removed, new = remap(doms)
        if removed:
            rows.append({
                "source": "gold_4axis",
                "item_id": r.get("example_id") or r.get("item_id"),
                "name": r.get("name"),
                "discipline": r.get("discipline"),
                "current_domains": json.dumps(doms, ensure_ascii=False),
                "removed": ";".join(removed),
                "proposed_domains": json.dumps(new, ensure_ascii=False),
                "owner_decision": TARGET,
                "note": "v8 merge(demote): science & research / social sciences -> research practice",
            })

    fields = ["source", "item_id", "name", "discipline", "current_domains",
              "removed", "proposed_domains", "owner_decision", "note"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    c = Counter(r["source"] for r in rows)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} rows  {dict(c)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
