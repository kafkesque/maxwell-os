#!/usr/bin/env python3
"""prefilter_dedup_groups.py — deterministic high-cosine subset for the 269 groups.

D2621/D2626: the 273 dedup candidate groups are NAME-STEM collisions (bucketed by
first token), NOT concept duplicates. Running the mechanism-aware judge over all
273 would mostly return "distinct" and waste local compute. This pre-filter
surfaces ONLY the groups whose members actually overlap on definition+mechanism
(Jaccard >= threshold), i.e. the subset worth a judge's attention.

Read-only. Outputs governance/dedup_judge_subset.json (fb_id pairs + overlap).

Usage:
    python3 scripts/prefilter_dedup_groups.py
    python3 scripts/prefilter_dedup_groups.py --threshold 0.35
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CAND = ROOT / "governance" / "dedup_candidates.jsonl"
OUT = ROOT / "governance" / "dedup_judge_subset.json"

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "of", "in", "for", "to", "with", "by", "on", "as",
    "or", "from", "through", "vs", "into", "using", "via", "at", "is", "are",
})
_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")


def _tokens(s: str) -> frozenset:
    s = (s or "").lower()
    s = _SUFFIX_RE.sub("", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return frozenset(t for t in re.sub(r"\s+", " ", s).strip().split() if t and t not in _STOPWORDS)


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def prefilter(threshold: float) -> None:
    groups: List[Dict[str, Any]] = [json.loads(l) for l in CAND.read_text().splitlines() if l.strip()]
    subset: List[Dict[str, Any]] = []
    for g in groups:
        members = g["members"]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                dj = _jaccard(_tokens(a["definition"]), _tokens(b["definition"]))
                mj = _jaccard(_tokens(a["mechanism"]), _tokens(b["mechanism"]))
                # D2621: true dup needs BOTH definition and mechanism overlap.
                if dj >= threshold and mj >= threshold:
                    subset.append({
                        "group_id": g["group_id"],
                        "a_fb_id": a["fb_id"], "a_name": a["name"],
                        "b_fb_id": b["fb_id"], "b_name": b["name"],
                        "def_jaccard": round(dj, 3),
                        "mech_jaccard": round(mj, 3),
                    })

    OUT.write_text(json.dumps({
        "threshold": threshold,
        "total_groups": len(groups),
        "subset_pairs": len(subset),
        "pairs": subset,
    }, indent=2, ensure_ascii=False) + "\n")

    print(f"total candidate groups: {len(groups)}")
    print(f"pairs with def+mech Jaccard >= {threshold}: {len(subset)}")
    for p in subset[:30]:
        print(f"  {p['def_jaccard']:.2f}/{p['mech_jaccard']:.2f}  {p['a_name'][:38]:40} <-> {p['b_name'][:38]}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Deterministic high-cosine pre-filter for dedup groups (D2621/D2626).")
    ap.add_argument("--threshold", type=float, default=0.5, help="Jaccard threshold for def+mech overlap")
    args = ap.parse_args()
    prefilter(args.threshold)
