#!/usr/bin/env python3
"""Freeze ANCHOR-1 and derive the R5 slot-vote recommendation.

Reads the inverted re-score results (governance/ruler_inverted_20260920.json) and writes:
  governance/anchor1_frozen_20260920.json  — per-row canonical labels + CSV integrity hash
  governance/anchor1_frozen_20260920.md    — provenance + per-slot reliability + R5 vote (PROPOSED)

ANCHOR-1 = the 150 blind-human-labelled rows, human label = ground truth (D-275a). It is
immutable: future work references this artifact, never the live CSV (which the reviewer may edit).
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = json.loads((REPO / "governance" / "ruler_inverted_20260920.json").read_text(encoding="utf-8"))
KEY = {r["item_id"]: r for r in json.loads((REPO / "governance" / "ruler_sheet_key_20260917.json").read_text(encoding="utf-8"))}
SHEET = REPO / "governance" / "RULER_BLIND_SHEET_20260917.csv"

OUT_JSON = REPO / "governance" / "anchor1_frozen_20260920.json"
OUT_MD = REPO / "governance" / "anchor1_frozen_20260920.md"

results = RES["results"]
by_axis = {a: {x["item_id"]: x for x in results[a]["rows"]} for a in ("ct", "disc", "form")}
ids = sorted(by_axis["ct"].keys())

anchor_rows = []
for iid in ids:
    r = KEY[iid]
    anchor_rows.append({
        "item_id": iid,
        "stratum": r["stratum"],
        "fb_id": r["fb_id"],
        "human": {"ct": by_axis["ct"][iid]["human"], "disc": by_axis["disc"][iid]["human"],
                  "form": by_axis["form"][iid]["human"]},
        "stored": {"ct": by_axis["ct"][iid]["stored"], "disc": by_axis["disc"][iid]["stored"],
                   "form": by_axis["form"][iid]["stored"]},
        "agree": {"ct": by_axis["ct"][iid]["agree"], "disc": by_axis["disc"][iid]["agree"],
                  "form": by_axis["form"][iid]["agree"]},
    })

anchor = {
    "schema_version": "1.0",
    "frozen_at": "2026-09-20",
    "description": "ANCHOR-1: 150 blind-human-labelled ruler rows. human=ground truth, stored=under test (D-275a).",
    "csv_sha256": hashlib.sha256(SHEET.read_bytes()).hexdigest(),
    "sources": {
        "sheet": "governance/RULER_BLIND_SHEET_20260917.csv",
        "key": "governance/ruler_sheet_key_20260917.json",
        "taxonomy": "config/taxonomy.yaml",
        "inverted_report": "governance/ruler_inverted_20260920.json",
    },
    "vocabularies": {
        "content_type": ["principle", "process_template", "process_instance", "tool_instruction",
                         "growth_edge", "noise_drop", "quarantine"],
        "extraction_type": ["causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern"],
        "discipline": "61 canonicals from config/taxonomy.yaml",
    },
    "summary_error_rates": {a: results[a]["error_rates"] for a in ("ct", "disc", "form")},
    "rows": anchor_rows,
}
OUT_JSON.write_text(json.dumps(anchor, indent=1), encoding="utf-8")


def dispose(error: float, n: int) -> str:
    """Proposed R5 disposition (D-277: repair-not-demote). Zero-agreement measures
    PIPELINE failure, not slot badness — so high error => re-derive the slot's
    definition + BOUND (human review), never DEMOTE as a first move."""
    if n < 4:
        return "EXTEND-SAMPLE (n<4, insufficient evidence)"
    if error >= 0.6:
        return "RE-DERIVE + BOUND (weak: definition+include+exclude, then human review on write)"
    if error >= 0.4:
        return "BOUND (human review on write)"
    return "measure κ (no action yet)"


md: list[str] = [
    "# ANCHOR-1 — frozen blind-human label set (2026-09-20)",
    "",
    "150 rows. **human label = ground truth, stored label = under test** (D-275a).",
    f"CSV integrity: `sha256={anchor['csv_sha256'][:16]}…`",
    "",
    "This artifact is immutable. The live CSV may be re-edited by the reviewer; all downstream",
    "work (R5 slot vote, R1 closed menu, R2 definition NLI, per-slot κ) references THIS file.",
    "",
    "## Headline stored-label error rates (inverted key)",
    "",
    "| axis | stratum all | stratum A | scored |",
    "|---|---|---|---|",
]
for axis, label in (("ct", "content_type"), ("disc", "discipline"), ("form", "extraction_type")):
    e = results[axis]["error_rates"]
    md.append(f"| {label} | **{e['all']['error']:.3f}** | {e.get('A', {}).get('error', float('nan')):.3f} "
              f"| {results[axis]['scored_n']} |")
md += ["", "`A` = pre-agreed clean subset (comparable to prior FORM pass); `all` = honest bound "
       "(includes stratum B, which is non-proportional and mixes PASS/QUARANTINE — D1/D2).", ""]

# CT slot vote
ct_pc = results["ct"]["per_class"]
md += ["## R5 repair — content_type (7 = 5 roles + 2 dispositions)", "",
       "| slot | n | stored agrees | error | proposed disposition |",
       "|---|---|---|---|---|"]
for lab, v in sorted(ct_pc.items(), key=lambda kv: -kv[1]["n"]):
    md.append(f"| {lab} | {v['n']} | {v['agrees']} | {v['error']:.3f} | {dispose(v['error'], v['n'])} |")
md += ["", "**CT finding:** the old classifier treats `principle` as the default — it under-calls "
       "`quarantine` (human 18 → stored 6) and `process_template` (human 16 → stored 9), pushing "
       "them into `principle`. This is the measured signature of the D-275b guardrail gap "
       "(step-count, not procedural intent). The fix is NOT a slot demotion — it is the D-275b "
       "discriminator, which re-balances the axis.", ""]

# DISC slot vote
disc_pc = results["disc"]["per_class"]
md += ["## R5 repair — discipline (61-menu)", "",
       "| slot | n | stored agrees | error | proposed disposition |",
       "|---|---|---|---|---|"]
for lab, v in sorted(disc_pc.items(), key=lambda kv: -kv[1]["n"]):
    md.append(f"| {lab} | {v['n']} | {v['agrees']} | {v['error']:.3f} | {dispose(v['error'], v['n'])} |")
if results["disc"].get("group_near_miss"):
    g = results["disc"]["group_near_miss"]
    md += ["", f"**DISC group-level near-miss:** exact-canonical error {g['exact_error']:.3f}, "
           f"same-group error {g['group_error']:.3f} → {g['n'] - g['group_agree']} stored labels land in a "
           "DIFFERENT discipline group. Even forgiving slot-boundary disagreements, ~27% are wrong.", ""]
md += ["", "**DISC reading (D-277):** zero-agreement is evidence against the OLD PIPELINE, not necessarily",
       "against the SLOT. `design psychology`, `cultural studies`, `risk management` are the strongest",
       "RE-DERIVE + BOUND candidates — give each a clean definition+include+exclude, re-measure, and merge",
       "into the parent group only if still definitionally inseparable. `emerging_dump` (stored) absorbs",
       "3+ of these, so the old extraction silently discarded that content into `emerging`. All",
       "dispositions above are **PROPOSED — awaiting reviewer ratification** (R5).",
       "",
       "## What this enables (dependency order)",
       "",
       "1. **R5** — ratify the dispositions above; RE-DERIVE definition + include + exclude (OntoClean)",
       "   for weak slots and BOUND them (human review); merge only if inseparable — never DEMOTE first.",
       "2. **R1** — closed-menu classification rendered from `config/taxonomy.yaml` with `none`",
       "   first-class + `menu_hash` stamped.",
       "3. **R2** — definition-anchored NLI verification against the menu definitions.",
       "",
       "Provenance columns (`menu_hash`, `*_source`) remain open (C1/C2 risk register) — needed before",
       "any corpus-wide re-classification, so the `min_human_share` provenance share is satisfiable.",
       ""]

OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
print("\nwrote", OUT_JSON.name, "and", OUT_MD.name)
