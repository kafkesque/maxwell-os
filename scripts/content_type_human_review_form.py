#!/usr/bin/env python3
"""content_type_human_review_form.py — self-contained model-proposal + human-verify form.

The OLD version made the human classify cold (7 boxes). This version shows the
model's PROPOSED label + confidence + reason as a NON-BINDING hint, so the human
only has to AGREE or DISAGREE (R5: generator != verifier). Definition is inline —
no cross-referencing to YAML/checkpoint.

Bands (priority order, most-uncertain first):
    model_low, model_medium  -> have a model proposal (fast AGREE/DISAGREE)
    unlabeled                -> NO proposal yet (7-box cold) — generate local proposals first
    model_high               -> model confident — verify later / sample only

Usage:
    python3 scripts/content_type_human_review_form.py --band model_medium --limit 30
    python3 scripts/content_type_human_review_form.py --band model_low   --limit 13
    python3 scripts/content_type_human_review_form.py --band unlabeled   --limit 30
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_MINE = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
BACKLOG = ROOT / "governance" / "content_type_verification_backlog.json"
OUT = ROOT / "governance" / "content_type_human_review_FORM.md"

CHOICES = [
    ("principle", "general truth / reusable rule"),
    ("process_template", "step-by-step method (2+ steps + done-condition)"),
    ("process_instance", "specific NAMED case / execution"),
    ("growth_edge", "open / unproven / speculative or correlation"),
    ("tool_instruction", "command / API for a specific tool"),
    ("noise_drop", "just describes a fact / history / summary"),
    ("quarantine", "carries SOME value, no clean role — hold"),
]


def load_definitions() -> Dict[str, Dict[str, str]]:
    d = yaml.safe_load(GOLDEN_MINE.read_text())
    rows = d["examples"] if isinstance(d, dict) and "examples" in d else d
    out: Dict[str, Dict[str, str]] = {}
    for r in rows:
        fb = r.get("input_fb") or {}
        out[r["id"]] = {"name": fb.get("name", ""), "definition": fb.get("definition", "")}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--band", required=True,
                    choices=["unlabeled", "model_low", "model_medium", "model_high", "reswept"],
                    help="verification band to emit")
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()

    defs = load_definitions()
    backlog = json.loads(BACKLOG.read_text())["backlog"]
    rows = [r for r in backlog if r["status"] == args.band][: args.limit]

    lines: List[str] = []
    lines.append("# Content-Type Review Form (model proposes, you verify)")
    lines.append("")
    lines.append(f"**Band:** `{args.band}`  |  **Rows:** {len(rows)}")
    lines.append("")
    lines.append("**How to work:** read the definition, look at the MODEL hint (if any), then tick")
    lines.append("**AGREE** or **DISAGREE**. If you DISAGREE, write the correct label in one word.")
    lines.append("The model hint is NON-BINDING — your judgment wins.")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in rows:
        eid = r["example_id"]
        meta = defs.get(eid, {})
        name = meta.get("name", r.get("name", ""))
        definition = meta.get("definition", "").strip()
        prop = r.get("content_type")
        conf = r.get("confidence")
        reason = r.get("reason", "")

        lines.append(f"## {eid} — {name}")
        lines.append("")
        lines.append(f"**Definition:** {definition}")
        lines.append("")
        if prop:
            lines.append(f"**MODEL hint (non-binding):** `{prop}` (confidence: `{conf}`) — {reason}")
            lines.append("")
            lines.append(f"- [ ] **AGREE** → `{prop}`")
            lines.append("- [ ] **DISAGREE** → correct label: `______`")
        else:
            lines.append("**No model hint.** Pick one:")
            lines.append("")
            for label, hint in CHOICES:
                lines.append(f"- [ ] **{label}** — {hint}")
        lines.append("")
        lines.append("---")
        lines.append("")

    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT.name}: {len(rows)} rows (band={args.band})")


if __name__ == "__main__":
    main()
