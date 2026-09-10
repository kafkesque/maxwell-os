#!/usr/bin/env python3
"""scripts/build_p5_review_pack.py — D2585 P5 Step 3 (human-review bridge).

Generates the ADJUDICATION REVIEW PACK: one record per high-suspicion FB
(tier both/nli_only = the 135 challenger-voted FBs) with the full evidence a
human reviewer needs, plus BLANK answer fields.

The human fills in the blank fields (final_discipline / final_domains /
reviewer / confidence / notes) and saves the file AS
``temp/p5_human_adjudication.jsonl`` — the exact artifact
scripts/freeze_gold_sets.py --adjudication expects:
  {"example_id", "final_discipline", "final_domains"?, "reviewer", "confidence"}

Read-only. Writes temp/p5_review_pack.jsonl (editable workbook) and
governance/p5_review_pack.md (read-only summary).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

_GOLDEN = _ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
_LABEL_MODEL = _ROOT / "temp" / "golden_labels_probabilistic.jsonl"
_VOTES = _ROOT / "temp" / "label_vote_high_suspicion.jsonl"
_OUT_JSONL = _ROOT / "temp" / "p5_review_pack.jsonl"
_OUT_MD = _ROOT / "governance" / "p5_review_pack.md"

import yaml  # noqa: E402


def main() -> int:
    golden = yaml.safe_load(_GOLDEN.read_text(encoding="utf-8")) or {}
    by_id = {e["id"]: e for e in golden.get("examples", [])}

    lm = {r["example_id"]: r for r in (
        json.loads(l) for l in _LABEL_MODEL.read_text(encoding="utf-8").splitlines()
        if l.strip())}
    votes = {r["fb_id"]: r for r in json.loads(_VOTES.read_text(encoding="utf-8"))}

    # High-suspicion targets in a deterministic order (tier, then example id).
    targets = sorted(
        (r for r in lm.values() if r["tier"] in ("both", "nli_only")),
        key=lambda r: (r["tier"], r["example_id"]),
    )
    rows: list[dict] = []
    for t in targets:
        eid = t["example_id"]
        ex = by_id.get(eid, {})
        fb = ex.get("input_fb") or {}
        v = votes.get(eid, {})
        rows.append({
            # evidence (read-only)
            "example_id": eid,
            "tier": t["tier"],
            "p_mislabel": t["p_mislabel"],
            "lf_votes": t["lf_votes"],
            "silver_discipline": t["silver_discipline"],
            "silver_domains": t["silver_domains"],
            "name": fb.get("name", ""),
            "definition": (fb.get("definition") or "")[:600],
            "mechanism": (fb.get("mechanism") or "")[:200],
            "challenger_votes": {
                m: (vv.get("discipline"), vv.get("domains"))
                for vv in v.get("votes", []) if (m := vv.get("model"))
            },
            "challenger_consensus_discipline": (v.get("consensus") or {}).get("discipline"),
            "proposed_correction": t.get("challenger_correction"),
            "is_backfill": t.get("is_backfill", False),
            # blank answer fields (human fills these in)
            "final_discipline": None,
            "final_domains": None,
            "reviewer": None,
            "confidence": None,  # high / medium / low
            "notes": None,
        })

    _OUT_JSONL.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    md = [
        "# P5 HUMAN ADJUDICATION REVIEW PACK (D2585 P5 Step 3)",
        "",
        f"**{len(rows)} high-suspicion FBs** (tier both/nli_only) with evidence.",
        "Fill the blank fields in `temp/p5_review_pack.jsonl`, then save as "
        "`temp/p5_human_adjudication.jsonl` (freeze script input).",
        "",
        "| example_id | tier | silver | challenger consensus | proposed correction | p_mislabel |",
        "|---|---|---|---|---|---|",
        *[
            f"| {r['example_id']} | {r['tier']} | {r['silver_discipline']} | "
            f"{r['challenger_consensus_discipline']} | {r['proposed_correction'] or '-'} | "
            f"{r['p_mislabel']} |"
            for r in rows
        ],
        "",
    ]
    _OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({
        "review_pack_size": len(rows),
        "by_tier": {t: sum(1 for r in rows if r["tier"] == t) for t in ("both", "nli_only")},
        "with_challenger_majority_correction": sum(
            1 for r in rows if r["proposed_correction"]),
        "fail_closed_no_majority": sum(
            1 for r in rows if r["challenger_consensus_discipline"] == "emerging"),
        "workbook": str(_OUT_JSONL),
        "human_output_target": "temp/p5_human_adjudication.jsonl (rename after filling)",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
