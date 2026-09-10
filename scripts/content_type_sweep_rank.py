#!/usr/bin/env python3
"""content_type_sweep_rank.py — consolidate the D2587 content_type verification state.

Builds a single ranked backlog of the entire golden universe (stage4_golden_mined.yaml,
1027 rows) against every content_type verdict artifact produced so far, so the human
reviewer knows EXACTLY what is verified vs. unverified vs. model-guessed.

Ranking (most urgent first):
    0 unlabeled      — no content_type verdict at all (never looked at)
    1 model_low      — model verdict with confidence == "low"
    2 model_medium   — model verdict with confidence == "medium"
    3 reswept_low    — re-swept with confidence <= 0.7 (borderline, needs human tiebreak)
    4 retriaged      — D2587 flip applied, not yet human-confirmed
    5 model_high     — model verdict with confidence == "high" (trust-but-verify)
    6 human_confirmed — human/adjudicator already settled

Output: governance/content_type_verification_backlog.{json,md}

Deterministic, LLM-free, reuses existing artifacts. No DB mutation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_MINE = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
OA_JOINED = ROOT / "temp" / "ct818_oa_joined_partial.json"       # 728 model verdicts (content_type+confidence+reason)
RETRIAGE = ROOT / "temp" / "p5_ct_retriage_result.json"           # 40 D2587 flips (flag_flips 32 + manifest_flips 8)
RESWEEP = ROOT / "temp" / "p5_ct_resweep_descriptive.json"        # 31 re-swept verdicts (label+confidence+reason)
BOUNDARY = ROOT / "config" / "golden" / "d2587_boundary_corpus.yaml"  # 9 human-adjudicated seed cases + 4 confirmed flips
LEDGER = ROOT / "governance" / "content_type_human_decisions.jsonl"   # canonical append-only human verdicts

OUT_JSON = ROOT / "governance" / "content_type_verification_backlog.json"
OUT_MD = ROOT / "governance" / "content_type_verification_backlog.md"


def load_golden_universe() -> Dict[str, Dict[str, Any]]:
    d = yaml.safe_load(GOLDEN_MINE.read_text())
    rows = d["examples"] if isinstance(d, dict) and "examples" in d else d
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        eid = r.get("id")
        out[eid] = {
            "name": (r.get("input_fb") or {}).get("name", ""),
            "discipline": (r.get("expected_classification") or {}).get("discipline", ""),
        }
    return out


def main() -> None:
    universe = load_golden_universe()

    # model verdicts (728)
    oa = json.loads(OA_JOINED.read_text())
    # re-triage flips (40)
    rt = json.loads(RETRIAGE.read_text())
    flag_flips: Dict[str, Dict[str, Any]] = rt.get("flag_flips", {})
    manifest_flips: Dict[str, Any] = rt.get("manifest_flips", {})
    retriaged: Dict[str, Dict[str, Any]] = {}
    for eid, v in flag_flips.items():
        retriaged[eid] = {"from": v.get("from"), "to": v.get("to"), "reason": v.get("reason")}
    for eid, v in manifest_flips.items():
        if isinstance(v, list) and len(v) >= 2:
            retriaged[eid] = {"from": v[0], "to": v[1], "reason": "manifest flip"}
    # re-swept (31)
    rs = json.loads(RESWEEP.read_text())
    reswept: Dict[str, Dict[str, Any]] = rs.get("verdicts", {})
    # human-confirmed (9 cases + 4 flips)
    bc = yaml.safe_load(BOUNDARY.read_text())
    human_cases: Dict[str, Dict[str, Any]] = {
        c["example_id"]: {"name": c.get("name", ""), "disposition": c.get("disposition") or c.get("content_type_derived")}
        for c in bc.get("cases", [])
    }
    human_flips = set(bc.get("confirmed_principle_flips", []))
    human_confirmed: Dict[str, Dict[str, Any]] = dict(human_cases)
    for eid in human_flips:
        human_confirmed.setdefault(eid, {"name": "", "disposition": "principle"})

    # canonical append-only human ledger (highest authority) overrides the seed cases
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            eid = rec.get("example_id")
            if eid:
                human_confirmed[eid] = {
                    "name": rec.get("name", ""),
                    "disposition": rec.get("content_type"),
                    "note": rec.get("note", ""),
                }

    backlog: List[Dict[str, Any]] = []
    for eid, meta in universe.items():
        if eid in human_confirmed:
            status, rank = "human_confirmed", 6
            ct = human_confirmed[eid].get("disposition", "principle")
            conf = None
            reason = human_confirmed[eid].get("note") or "human/adjudicator settled"
        elif eid in reswept:
            v = reswept[eid]
            conf = v.get("confidence")
            ct = v.get("label")
            reason = v.get("reason", "")
            status = "reswept"
            rank = 3 if (conf is not None and conf <= 0.7) else 4  # borderline reswept still needs tiebreak
        elif eid in retriaged:
            v = retriaged[eid]
            ct = v.get("to")
            conf = None
            reason = f"flip {v.get('from')}->{v.get('to')}: {v.get('reason', '')}"
            status, rank = "retriaged", 4
        elif eid in oa:
            v = oa[eid]
            ct = v.get("content_type")
            conf = v.get("confidence")
            reason = v.get("reason", "")
            conf_map = {"low": 1, "medium": 2, "high": 5}
            rank = conf_map.get(conf, 5)
            status = f"model_{conf or 'unknown'}"
        else:
            status, rank = "unlabeled", 0
            ct = None
            conf = None
            reason = "NO content_type verdict — never assessed"

        backlog.append({
            "example_id": eid,
            "name": meta.get("name", "") or human_confirmed.get(eid, {}).get("name", ""),
            "discipline": meta.get("discipline", ""),
            "status": status,
            "rank": rank,
            "content_type": ct,
            "confidence": conf,
            "reason": reason,
        })

    backlog.sort(key=lambda r: (r["rank"], r["example_id"]))

    counts: Dict[str, int] = {}
    for r in backlog:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    result = {
        "note": "content_type verification backlog (D2587/D2591). Rank: 0 unlabeled > 1 model_low > 2 model_medium > 3 reswept_low > 4 retriaged > 5 model_high > 6 human_confirmed.",
        "total": len(backlog),
        "counts": counts,
        "backlog": backlog,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # human-readable markdown
    lines: List[str] = []
    lines.append("# Content-Type Verification Backlog (D2587 / D2591)")
    lines.append("")
    lines.append(f"**Total golden:** {result['total']}  |  **counts:** " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    lines.append("")
    lines.append("Rank: `0 unlabeled` (never assessed) → `1 model_low` → `2 model_medium` → `3 reswept_low` (borderline) → `4 retriaged` → `5 model_high` → `6 human_confirmed`.")
    lines.append("")
    lines.append("**Priority for human sweep = ranks 0,1,2,3** (unlabeled + low/medium model + borderline reswept).")
    lines.append("")
    lines.append("| rank | example_id | name | discipline | status | content_type | conf | reason |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in backlog:
        name = (r["name"] or "")[:40]
        disc = (r["discipline"] or "")[:24]
        conf = "" if r["confidence"] is None else str(r["confidence"])
        reason = (r["reason"] or "")[:60]
        lines.append(f"| {r['rank']} | {r['example_id']} | {name} | {disc} | {r['status']} | {r['content_type'] or ''} | {conf} | {reason} |")
    lines.append("")
    OUT_MD.write_text("\n".join(lines))

    print(f"wrote {OUT_JSON.name} + {OUT_MD.name}")
    print("counts:", json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
