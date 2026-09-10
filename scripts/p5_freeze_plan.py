#!/usr/bin/env python3
"""p5_freeze_plan.py — D2585 P5: freeze GOLD-A/B/CHALLENGE + human-review queue.

The ModernBERT discipline/domain classifier is stuck at macro-F1 0.2875 (target
0.75). This is DATA-LIMITED, not model-selection: P4 applied 59 challenger
corrections and moved F1 0.2757 -> 0.2875 (temperature-scaling Delta=0.0). The
only lever to 0.75 is a hand-verified stratified golden set (P5), NOT more
calibration.

This script (deterministic, read-only) emits:
  1. `governance/p5_freeze_plan.{json,md}` — tier assignment (GOLD-A 135
     high-suspicion / GOLD-B 892 / CHALLENGE 9 boundary) + discipline
     stratification (data-starved classes = the F1 blockers).
  2. `governance/p5_human_review_form.md` — the BOUNDED human-verification queue
     (4 deferred P4 corrections + 65 challenger-abstain high-suspicion FBs).
     Each entry carries the object's **name + definition + mechanism + current
     label + model vote splits** so a human can adjudicate WITHOUT opening any
     other file.

Usage:
    python3 scripts/p5_freeze_plan.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_P4 = ROOT / "config" / "golden" / "stage4_golden_mined_p4.yaml"
LABEL_MODEL = ROOT / "temp" / "golden_labels_probabilistic.jsonl"
CHALLENGER = ROOT / "temp" / "label_vote_high_suspicion.jsonl"
P4_MANIFEST = ROOT / "temp" / "p4_corrections_manifest.json"
BOUNDARY = ROOT / "config" / "golden" / "d2587_boundary_corpus.yaml"
OUT_JSON = ROOT / "governance" / "p5_freeze_plan.json"
OUT_MD = ROOT / "governance" / "p5_freeze_plan.md"
REVIEW_FORM = ROOT / "governance" / "p5_human_review_form.md"

MIN_PER_CLASS = 10  # D2579 stratification floor (config mining floor)
MECH_MAX = 420  # C20: cap mechanism echo in the form (definition stays full)


def load_golden() -> list[dict]:
    d = yaml.safe_load(GOLDEN_P4.read_text(encoding="utf-8")) or {}
    return d.get("examples", [])


def discipline_of(ex: dict) -> str:
    return str((ex.get("expected_classification") or {}).get("discipline") or "emerging")


def domains_of(ex: dict) -> list[str]:
    return list((ex.get("expected_classification") or {}).get("domains") or [])


def content_of(ex: dict) -> dict:
    """Extract the human-adjudicable content (name/definition/mechanism/boundary)."""
    ib = ex.get("input_fb") or {}
    return {
        "name": str(ib.get("name") or "").strip(),
        "definition": str(ib.get("definition") or "").strip(),
        "mechanism": str(ib.get("mechanism") or "").strip(),
        "boundary": str(ib.get("boundary") or "").strip(),
    }


def load_label_model() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not LABEL_MODEL.exists():
        return out
    with LABEL_MODEL.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            out[o.get("example_id", "")] = o
    return out


def load_challenger() -> dict[str, dict]:
    raw = json.loads(CHALLENGER.read_text(encoding="utf-8"))
    return {r["fb_id"]: r for r in raw if isinstance(r, dict)}


def load_deferred() -> list[dict]:
    m = json.loads(P4_MANIFEST.read_text(encoding="utf-8"))
    return m.get("deferred", [])


def load_boundary_count() -> int:
    d = yaml.safe_load(BOUNDARY.read_text(encoding="utf-8")) or {}
    cases = d.get("cases", []) if isinstance(d, dict) else []
    return len(cases)


def main() -> int:
    golden = load_golden()
    golden_by_id = {ex.get("id"): ex for ex in golden}
    lm = load_label_model()
    ch = load_challenger()
    deferred = load_deferred()
    boundary_n = load_boundary_count()

    # Tier assignment by example_id.
    gold_a: list[dict] = []
    gold_b: list[dict] = []
    for ex in golden:
        row = lm.get(ex.get("id", ""))
        if row and row.get("tier") in ("both", "nli_only"):
            gold_a.append(ex)
        else:
            gold_b.append(ex)

    # Discipline stratification over the full P4-corrected training set.
    disc_counts = Counter(discipline_of(ex) for ex in golden)
    data_starved = {d: c for d, c in disc_counts.items() if c < MIN_PER_CLASS}
    zero_f1_candidates = sorted(data_starved.items(), key=lambda x: x[1])

    # Human review queue: 4 deferred + 65 abstain high-suspicion challenger cases.
    # Every entry carries name+definition+mechanism+current label so the human
    # can adjudicate from the form alone.
    review_queue: list[dict] = []
    for d in deferred:
        ex = golden_by_id.get(d["example_id"], {})
        c = content_of(ex)
        review_queue.append({
            "example_id": d["example_id"],
            "source": "p4_deferred",
            "name": c["name"],
            "definition": c["definition"],
            "mechanism": c["mechanism"],
            "current_discipline": d.get("old"),
            "current_domains": domains_of(ex),
            "proposed": d.get("proposed"),
            "reason": d.get("reason"),
            "votes": None,
        })
    for ex in gold_a:
        eid = ex.get("id", "")
        row = lm.get(eid, {})
        if row.get("lf_votes", {}).get("challenger") is not None:
            continue  # already has a concrete challenger vote (agree/disagree)
        rec = ch.get(eid, {})
        votes = None
        if rec:
            votes = [
                {"model": v.get("model"), "discipline": v.get("discipline"),
                 "domains": v.get("domains")}
                for v in rec.get("votes", [])
            ]
        c = content_of(ex)
        review_queue.append({
            "example_id": eid,
            "source": "challenger_abstain",
            "name": c["name"],
            "definition": c["definition"],
            "mechanism": c["mechanism"],
            "current_discipline": discipline_of(ex),
            "current_domains": domains_of(ex),
            "proposed": None,
            "reason": "3-model challenger did not reach 2/3 majority (consensus emerging/None)",
            "votes": votes,
        })

    doc = {
        "note": "P5 freeze plan — GOLD-A/B/CHALLENGE + data-starvation root cause",
        "macro_f1_current": 0.2875,
        "macro_f1_target": 0.75,
        "tiers": {
            "gold_a_high_suspicion": len(gold_a),
            "gold_b_cleaned": len(gold_b),
            "challenge_boundary": boundary_n,
            "total_golden": len(golden),
        },
        "data_starved_disciplines": len(data_starved),
        "data_starved": {d: c for d, c in zero_f1_candidates},
        "human_review_queue": {
            "n": len(review_queue),
            "n_deferred": len(deferred),
            "n_challenger_abstain": len(review_queue) - len(deferred),
        },
        "review_queue": review_queue,
    }
    OUT_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [
        "# P5 FREEZE PLAN — GOLD-A/B/CHALLENGE (D2585 P5)",
        "",
        f"Classifier macro-F1 **0.2875** (target 0.75) — DATA-LIMITED, not model-selection.",
        "",
        "## Tier assignment",
        f"- **GOLD-A** (high-suspicion, challenger-voted): **{len(gold_a)}**",
        f"- **GOLD-B** (statistically-cleaned silver): **{len(gold_b)}**",
        f"- **CHALLENGE** (boundary corpus): **{boundary_n}** (target ~150)",
        f"- Total golden: **{len(golden)}**",
        "",
        f"## Data-starvation (root cause of 0.2875)",
        f"{len(data_starved)} of 61 disciplines have <{MIN_PER_CLASS} examples "
        f"(below the mining floor). These are the 0.00-F1 classes.",
        "",
        "| discipline | examples |",
        "|---|---|",
    ]
    for d, c in zero_f1_candidates:
        md.append(f"| {d} | {c} |")
    md += [
        "",
        f"## Human-review queue (bounded: {len(review_queue)} FBs)",
        f"- {len(deferred)} deferred P4 corrections (non-canonical / class-floor)",
        f"- {len(review_queue) - len(deferred)} challenger-abstain high-suspicion FBs",
        "",
        "Full per-FB detail (name + definition + mechanism + votes): `governance/p5_human_review_form.md`.",
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    # Human review form — full adjudicable content inline.
    rf = [
        "# P5 HUMAN REVIEW FORM — GOLD-A freeze (bounded queue)",
        "",
        f"**{len(review_queue)} FBs** to adjudicate. Each carries name + definition + mechanism "
        "so you can decide the canonical discipline/domains without opening any other file.",
        "",
        "**Decision you are making (discipline/domain only — depth is separate):** "
        "is the current discipline right, or does the object clearly belong to a different canonical "
        "discipline? For the 4 deferred, the proposed correction is shown; for the 65 abstain, the "
        "3-model vote split is shown (the challenger failed to reach 2/3 agreement).",
        "",
        "---",
        "",
        "## A. Deferred P4 corrections (4)",
        "",
    ]
    for r in review_queue:
        if r["source"] != "p4_deferred":
            continue
        rf += _render_entry(r)
    rf += ["---", "", "## B. Challenger-abstain high-suspicion (65)", ""]
    for r in review_queue:
        if r["source"] != "challenger_abstain":
            continue
        rf += _render_entry(r)
    REVIEW_FORM.write_text("\n".join(rf), encoding="utf-8")

    print(f"tiers: GOLD-A {len(gold_a)} / GOLD-B {len(gold_b)} / CHALLENGE {boundary_n}")
    print(f"data-starved disciplines: {len(data_starved)} of 61")
    print(f"human review queue: {len(review_queue)} (4 deferred + {len(review_queue)-len(deferred)} abstain)")
    print(f"wrote {OUT_JSON.name}, {OUT_MD.name}, {REVIEW_FORM.name}")
    return 0


def _render_entry(r: dict) -> list[str]:
    """Render one review entry with full adjudicable content."""
    doms = ", ".join(r.get("current_domains") or []) or "(none)"
    lines = [
        f"### {r['example_id']} — {r['name']}",
        "",
        f"- **current discipline:** `{r['current_discipline']}` | **domains:** {doms}",
    ]
    if r.get("proposed"):
        lines.append(f"- **proposed discipline:** `{r['proposed']}`")
        lines.append(f"- **reason:** {r['reason']}")
    if r.get("votes"):
        lines.append("- **model votes (no 2/3 majority):**")
        for v in r["votes"]:
            vdoms = ", ".join(v.get("domains") or []) or "(none)"
            lines.append(f"  - {v['model']}: `{v['discipline']}` — {vdoms}")
    lines += [
        "",
        f"> **definition:** {r['definition']}",
        "",
    ]
    mech = (r.get("mechanism") or "").strip()
    if mech:
        if len(mech) > MECH_MAX:
            mech = mech[:MECH_MAX] + "…"
        lines += [f"> **mechanism:** {mech}", ""]
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
