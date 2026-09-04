#!/usr/bin/env python3
"""scripts/build_relabel_plan.py — turn the human review marks into a relabel plan.

Parses the annotated `governance/human_review_sample.md` (5th-column marks:
relabel / keep / ? / blank + notes), joins each FB to its DB record, and emits a
machine-readable relabel plan + a reviewable Markdown summary. Does NOT mutate
the DB (plan-only). Writes via C6 safe_write.

Action taxonomy:
  deregister_domain  — remove the audited catch-all domain (discipline already correct)
  retarget           — remove the domain AND move to a specific canonical target
  keep               — no action (false alarm)
  unreviewed         — blank mark, needs a decision (proposal included)
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_MD_IN = _ROOT / "governance" / "human_review_sample.md"
_PLAN_JSON = _ROOT / "governance" / "relabel_plan.json"
_PLAN_MD = _ROOT / "governance" / "relabel_plan.md"
_TRIAGE = _ROOT / "governance" / "mislabel_triage.json"
_TAXONOMY = _ROOT / "config" / "taxonomy_v5.yaml"

# Proposed resolutions for "?" (undecided) marks — keyed by FB name.
_UNDECIDED_RESOLUTIONS = {
    "Ai-powered Sales Training Platform Development":
        ("deregister_domain", "marketing & communications", "discipline 'software engineering' is correct"),
    "Media Studies Vs. Film Studies Methodologies":
        ("deregister_domain", "marketing & communications", "discipline 'media studies' is correct"),
    "Narrative Resolution Through Humor and Reconciliation":
        ("deregister_domain", "marketing & communications", "discipline 'literary theory' is correct"),
    "Creative Motion Design Process":
        ("keep", None, "has 'motion design' domain; discipline 'motion & time' correct"),
    "Color As Emotional Narrative Cue":
        ("deregister_domain", "marketing & communications", "discipline 'motion & time' correct"),
    "Story Arc Narrative Framework":
        ("deregister_domain", "editorial & advertising", "discipline 'literary theory' correct"),
    "Commoditization As Waste Reduction":
        ("deregister_domain", "user experience", "discipline 'economics' correct"),
    "Email Communication Cost Structure":
        ("deregister_domain", "engineering & infrastructure", "keep 'business operations'; drop infrastructure/leadership/project-management"),
    "Data Literacy As Strategic Competency":
        ("deregister_domain", "engineering & infrastructure", "keep 'education'/'research & methodology'; drop infrastructure/leadership"),
    "Ai Data Ethics and Accuracy":
        ("deregister_domain", "engineering & infrastructure", "keep 'ai & agents'; discipline 'philosophy' correct"),
    "Compound Effect of Small Choices":
        ("deregister_domain", "organizational behavior", "discipline 'behavioral economics' correct"),
    "Information As a Transformative Idea":
        ("deregister_domain", "organizational behavior", "discipline 'systems thinking' correct"),
}

# Explicit retargets from the user's free-text notes (FB name -> (remove_domain, add_domain, note)).
_RETARGETS = {
    "Structural Theory Foundation": ("business operations", "design strategy", "closer to brand strategy"),
    "Community Mapping Project Coordination Challenges": ("legal & public policy", "project management", "closer to project management"),
    "Project Structure and Organization in Motion Design": ("editorial & advertising", "brand identity", "closer to branding"),
    "Figma Ai Development Tools": ("user experience", "web & ui", "rather ui"),
    "Figma Hamburger Icon Creation": ("user experience", "web & ui", "rather ui"),
    "Color As Cultural and Emotional Marker": ("user experience", "social sciences", "rather psychology and sociology"),
}

# Surveillance/social-engineering callouts (FB name -> action, note) under engineering & infrastructure.
_SOCIAL_ENG = {
    "Cambridge Analytica's Political Transformation of Surveillan": "deregister_domain",
    "Targeted Osint Platform Enumeration": "deregister_domain",
    "Orwellian Courage As Resistance to Surveillance Capitalism": "deregister_domain",
    "Surveillance Capitalism Legal and Institutional Control": "deregister_domain",
}


def _load_canonicals() -> tuple[set[str], set[str]]:
    tax = yaml.safe_load(open(_TAXONOMY, encoding="utf-8"))
    doms = {d["canonical"] for d in tax.get("domains", [])}
    discs = {d["canonical"] for d in tax.get("disciplines", [])}
    return doms, discs


def _parse_marks() -> tuple[list[dict], list[str]]:
    """Return (rows, section_labels). Each row: name, label, vote, note."""
    rows: list[dict] = []
    labels: list[str] = []
    cur_label = ""
    for line in _MD_IN.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            cur_label = line[3:].strip()
            # strip the " — N flagged FBs" suffix (keeps "domain:<label>")
            cur_label = re.sub(r"\s*—\s*\d+\s+flagged\s+FBs\s*$", "", cur_label)
            labels.append(cur_label)
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # parts = ['', name, definition, knn, gap, (comment)]
        if len(parts) < 3 or parts[1] in ("", "FB name"):
            continue
        name = parts[1]
        comment = parts[5] if len(parts) > 5 else ""
        vote, note = _normalize(comment)
        rows.append({"name": name, "label": cur_label, "vote": vote, "note": note})
    return rows, labels


def _normalize(comment: str) -> tuple[str, str]:
    c = comment.strip()
    if not c:
        return "unreviewed", ""
    low = c.lower()
    if low.startswith("relabel"):
        # extract note after 'relabel'
        rest = c[len("relabel"):].strip()
        return "relabel", rest.lstrip("-–: ").strip()
    if low.startswith("keep"):
        return "keep", ""
    if low in ("?", "??"):
        return "undecided", ""
    # single-word other (e.g. user wrote a target directly)
    return "note", c


def _label_flagged_counts() -> dict[str, int]:
    triage = json.loads(_TRIAGE.read_text(encoding="utf-8"))
    cnt: Counter[str] = Counter()
    for r in triage["triage"]:
        for a in r["nli_axes"]:
            cnt[a] += 1
    return dict(cnt)


def main() -> int:
    doms, discs = _load_canonicals()
    marks, labels = _parse_marks()
    flagged = _label_flagged_counts()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    fb_actions: list[dict] = []
    for m in marks:
        name = m["name"]
        row = conn.execute(
            "SELECT fb_id, name, discipline, domains FROM fbs WHERE name LIKE ?",
            ("%" + name[:40] + "%",),
        ).fetchone()
        if row is None:
            fb_actions.append({**m, "fb_id": None, "discipline": None,
                               "domains": None, "action": "not_found"})
            continue
        audit_domain = m["label"].split(":", 1)[1].strip() if ":" in m["label"] else ""
        domains = json.loads(row["domains"]) if row["domains"] and row["domains"].startswith("[") else []

        action = "keep"
        add_domain = None
        note = m["note"]

        if m["vote"] == "relabel":
            # explicit retarget from a note, else default deregister
            if name in _RETARGETS:
                rm, add, note = _RETARGETS[name]
                action = "retarget"
            elif name in _SOCIAL_ENG:
                action = "deregister_domain"
                note = "social engineering / surveillance content — not engineering"
            else:
                action = "deregister_domain"
            add_domain = _RETARGETS[name][1] if action == "retarget" and name in _RETARGETS else None
        elif m["vote"] == "undecided":
            if name in _UNDECIDED_RESOLUTIONS:
                act, rm, note = _UNDECIDED_RESOLUTIONS[name]
                action = act
                add_domain = None
            else:
                action = "undecided"
        elif m["vote"] == "unreviewed":
            action = "unreviewed"
        # 'keep' and 'note' pass through

        fb_actions.append({
            "fb_id": row["fb_id"],
            "name": row["name"],
            "discipline": row["discipline"],
            "domains": row["domains"],
            "audit_domain": audit_domain,
            "vote": m["vote"],
            "note": note,
            "action": action,
            "add_domain": add_domain,
        })
    conn.close()

    # Label-level verdicts
    by_label: dict[str, Counter] = defaultdict(Counter)
    for a in fb_actions:
        by_label[a["audit_domain"] or "unknown"][a["vote"]] += 1

    label_verdicts = []
    for lab in labels:
        dom = lab.split(":", 1)[1].strip() if ":" in lab else lab
        votes = by_label[dom]
        n_relabel = votes["relabel"] + votes["note"]
        n_keep = votes["keep"]
        n_und = votes["undecided"] + votes["unreviewed"]
        total = n_relabel + n_keep + n_und
        if total == 0:
            continue
        ratio = n_relabel / total
        verdict = "systematic" if ratio >= 0.75 else ("mixed" if ratio >= 0.4 else "mostly_keep")
        label_verdicts.append({
            "label": lab, "flagged_count": flagged.get(lab, 0),
            "sample_relabel": n_relabel, "sample_keep": n_keep, "sample_undecided": n_und,
            "verdict": verdict,
            "proposed_action": ("deregister_domain (remove catch-all domain from flagged FBs)"
                                if verdict == "systematic" else
                                "mixed — apply FB-level corrections only, re-sample before label-wide action"),
        })

    plan = {
        "summary": {
            "n_fb_actions": len(fb_actions),
            "n_retarget": sum(1 for a in fb_actions if a["action"] == "retarget"),
            "n_deregister": sum(1 for a in fb_actions if a["action"] == "deregister_domain"),
            "n_keep": sum(1 for a in fb_actions if a["action"] == "keep"),
            "n_unreviewed": sum(1 for a in fb_actions if a["action"] == "unreviewed"),
            "note": "Sample-level actions (8 FBs/label). Label-wide cascade pending user confirmation of per-label verdicts.",
        },
        "label_verdicts": label_verdicts,
        "fb_actions": fb_actions,
    }
    safe_write(_PLAN_JSON, json.dumps(plan, indent=2) + "\n", force_shrink=True)

    # Markdown summary
    md = [
        "# RELABEL PLAN — from human-review marks",
        "",
        "> **Plan-only — no DB mutation.** Derived from `human_review_sample.md` marks.",
        "",
        "## Label verdicts",
        "",
        "| label | flagged | relabel | keep | ?/blank | verdict | proposed action |",
        "|---|---|---|---|---|---|---|",
    ]
    for v in label_verdicts:
        md.append(f"| {v['label']} | {v['flagged_count']} | {v['sample_relabel']} | "
                  f"{v['sample_keep']} | {v['sample_undecided']} | **{v['verdict']}** | {v['proposed_action']} |")
    md += ["", "## FB-level actions", "",
           "| FB | discipline | audit domain | vote | action | add → |", "|---|---|---|---|---|---|"]
    for a in sorted(fb_actions, key=lambda x: x["action"]):
        md.append(f"| {a['name']} | {a['discipline']} | {a['audit_domain']} | {a['vote']} | "
                  f"**{a['action']}** | {a['add_domain'] or ''} |")
    md.append("")
    safe_write(_PLAN_MD, "\n".join(md), force_shrink=True)

    print(f"✅ {len(fb_actions)} FB actions → {_PLAN_JSON.name} / {_PLAN_MD.name}")
    print(f"   labels: {len(label_verdicts)} verdicts")
    print(f"   retarget={plan['summary']['n_retarget']} deregister={plan['summary']['n_deregister']} "
          f"keep={plan['summary']['n_keep']} unreviewed={plan['summary']['n_unreviewed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
