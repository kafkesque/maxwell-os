#!/usr/bin/env python3
"""dedup_judge.py — Phase B mechanism-aware duplicate judge (D2621, stage 3).

For each candidate group from dedup_scan.py, ask Qwen3.8 (mechanism-aware) to
partition members into TRUE-duplicate clusters (same definition + mechanism +
application -> merge) vs DISTINCT facets (different mechanism -> keep).

D2621 rule: name-stem collision OVER-GROUPS. The judge is what separates
"Squash and Stretch" (3 -> 1, same mechanism) from "Iterative * Refinement"
(9 members, ~3 generic + 6 distinct: Prompt/Timeline/Keyword/Hypothesis/Design).

Read-only + plan-only: emits governance/dedup_merge_plan.json (duplicate_of map),
never mutates the DB (dedup = mark, not delete; R-D410 safe_delete is the only
destructive path and is NOT invoked here).

Usage:
    python3 scripts/dedup_judge.py --groups squah,responsible,foot,iterative
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.omlx_call import call_omlx_json  # noqa: E402

CAND = ROOT / "governance" / "dedup_candidates.jsonl"
OUT_PLAN = ROOT / "governance" / "dedup_merge_plan.json"

MODEL = "Qwen3.8-27B-MLX-4bit"
MAX_TOKENS = 2048

CONFIRMED_STEMS = frozenset({
    "squash and stretch", "responsible ai", "foot-in-the-door", "iterative refinement",
})


def _load_candidates() -> List[Dict[str, Any]]:
    return [json.loads(l) for l in CAND.read_text().splitlines() if l.strip()]


def _stem_of(name: str) -> str:
    n = name.lower()
    for cs in ("squash and stretch", "responsible ai", "foot-in-the-door", "iterative refinement"):
        if cs in n:
            return cs
    return n.split(" ")[0]


def _judge_group(group: Dict[str, Any]) -> Dict[str, Any]:
    members = group["members"]
    member_text = "\n\n".join(
        f"[{i}] Name: {m['name']}\nDefinition: {m['definition']}\nMechanism: {m['mechanism']}\n"
        f"Application: {m['application'] or ''}"
        for i, m in enumerate(members)
    )
    prompt = (
        "You are deduplicating Foundation Blocks (reusable design principles) in a RAG "
        "knowledge base. Two FBs are TRUE duplicates ONLY if they share the SAME mechanism "
        "AND application (different wording of the same principle). They are DISTINCT facets "
        "if the MECHANISM differs (e.g. 'Iterative Prompt Refinement' vs 'Iterative Timeline "
        "Refinement' are DIFFERENT — one refines prompts, the other refines timelines).\n\n"
        "Return ONLY JSON (no markdown):\n"
        '{"duplicate_clusters": [[1, 3], ...], "distinct": [0, 2, ...]}\n'
        "where duplicate_clusters lists INDEX groups to merge (keep the first index as the "
        "canonical), and distinct lists indices to keep separate.\n\n"
        "Members:\n" + member_text
    )
    raw = call_omlx_json(prompt, model=MODEL, max_tokens=MAX_TOKENS)
    if not isinstance(raw, dict):
        return {"error": f"non-dict response: {type(raw).__name__}", "members": members}
    return {"raw": raw, "members": members}


def judge(stems: List[str]) -> None:
    cands = _load_candidates()
    selected = [g for g in cands if _stem_of(g["members"][0]["name"]) in stems]
    print(f"groups selected: {len(selected)}")

    plan: Dict[str, Any] = {"duplicate_of": {}, "merged_into": {}, "distinct_kept": []}
    for g in selected:
        members = g["members"]
        name0 = members[0]["name"]
        print(f"\n=== group: {name0[:50]} ({len(members)} members) ===")
        res = _judge_group(g)
        if "error" in res:
            print(f"  ERROR: {res['error']}")
            continue
        raw = res["raw"]
        clusters = raw.get("duplicate_clusters") or []
        distinct = raw.get("distinct") or []
        print(f"  duplicate_clusters: {clusters}")
        print(f"  distinct: {distinct}")
        for cl in clusters:
            if not isinstance(cl, list) or len(cl) < 2:
                continue
            canon = members[cl[0]]["fb_id"]
            plan["merged_into"][canon] = [members[i]["name"] for i in cl]
            for i in cl[1:]:
                plan["duplicate_of"][members[i]["fb_id"]] = canon
        for i in distinct:
            plan["distinct_kept"].append(members[i]["fb_id"])

    OUT_PLAN.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
    print(f"\nwrote {OUT_PLAN}")
    print(f"  duplicate_of entries: {len(plan['duplicate_of'])}")
    print(f"  distinct kept: {len(plan['distinct_kept'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Phase B mechanism-aware duplicate judge (D2621).")
    ap.add_argument("--stems", default=",".join(sorted(CONFIRMED_STEMS)),
                    help="comma-separated stems to judge")
    args = ap.parse_args()
    judge([s.strip() for s in args.stems.split(",") if s.strip()])
