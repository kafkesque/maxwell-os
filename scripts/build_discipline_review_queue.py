#!/usr/bin/env python3
"""build_discipline_review_queue.py — deterministic owner review queue for the
ANCHOR-208 DISCIPLINE axis.

WHY (D-2764 / BUG-620)
----------------------
The discipline axis of ANCHOR-208 has only 9 human-finalized labels; the other
197 are LLM silver (`anchor_adjudication`) plus 2 whitespace-fixed dupes.  A
discipline conformance gate cannot be built on LLM-vs-LLM agreement (circular =
contamination, D-274f).  To mirror the depth path (149 human-provenanced rows,
D-2760/D-2761), the owner must adjudicate ~141 more discipline labels.

WHAT THIS PRODUCES
------------------
  * governance/discipline_review_queue_<date>.json  — machine-readable, provenance-stamped
  * governance/discipline_review_queue_<date>.md    — human review sheet, grouped by discipline

It is a READ-ONLY derivation of the consolidated dual-axis artifact
(governance/ANCHOR_208_CONSOLIDATED_<date>.json).  It mutates nothing and is
trivially regenerable.  Fail-closed on any invariant violation (C12d / C16).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONSOLIDATED = REPO / "governance" / "ANCHOR_208_CONSOLIDATED_20261002.json"
MENU = REPO / "config" / "closed_menu_v5.json"
OUT_JSON = REPO / "governance" / "discipline_review_queue_20261002.json"
OUT_MD = REPO / "governance" / "discipline_review_queue_20261002.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def build() -> dict:
    consolidated = json.loads(CONSOLIDATED.read_text())
    rows = consolidated["rows"]
    menu = {x["value"] for x in json.loads(MENU.read_text())["disciplines"]}

    # Invariants — fail closed.
    assert len(rows) == 208, f"expected 208 consolidated rows, got {len(rows)}"
    unreviewed = [r for r in rows if r.get("discipline_source") != "owner_finalized"]
    assert len(unreviewed) == 199, f"expected 199 unreviewed, got {len(unreviewed)}"
    offmenu = [r for r in unreviewed if r.get("discipline") not in menu]
    assert not offmenu, f"off-menu disciplines: {[(r['item_id'], r['discipline']) for r in offmenu]}"
    # No 'emerging' may survive into the review queue (the 3 emerging are owner-finalized).
    emerging = [r for r in unreviewed if r.get("discipline") == "emerging"]
    assert not emerging, f"'emerging' leaked into review queue: {[r['item_id'] for r in emerging]}"

    by_status = Counter(r.get("discipline_status") for r in unreviewed)
    assert by_status == {"ok": 197, "whitespace_fixed": 2}, f"unexpected status split: {dict(by_status)}"

    queue_rows = [
        {
            "item_id": r["item_id"],
            "name": r["name"],
            "discipline": r["discipline"],
            "discipline_status": r["discipline_status"],
            "discipline_source": r["discipline_source"],
            "domain": r.get("domain"),
            "primary_domain": r.get("primary_domain"),
        }
        for r in unreviewed
    ]

    artifact = {
        "schema_version": "1.0",
        "artifact_id": "discipline_review_queue_20261002",
        "generated_by": "scripts/build_discipline_review_queue.py",
        "gen_model": "none",  # deterministic; no LLM
        "pipeline_commit": git_commit(),
        "maxwell_schema_version": consolidated.get("_provenance", {}).get("schema_version", "1.0"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authority": [
            "D-2764 (discipline axis lacks human ground truth: 9/208 owner-finalized, 197 silver)",
            "D-2763 (dual-axis consolidation; 'emerging' excluded from golden)",
            "D-274f (anchor is a conformance set, NOT a training set)",
            "BUG-620 (discipline ground truth gap)",
        ],
        "inputs": {
            "consolidated": f"{CONSOLIDATED.name} ({sha256(CONSOLIDATED)})",
            "menu": f"{MENU.name} ({sha256(MENU)})",
        },
        "counts": {
            "total_unreviewed": len(queue_rows),
            "anchor_adjudication_silver": sum(1 for r in queue_rows if r["discipline_source"] == "anchor_adjudication"),
            "whitespace_fixed": sum(1 for r in queue_rows if r["discipline_source"] == "whitespace_fixed"),
            "already_owner_finalized": 9,
            "human_target_approx": 150,
            "still_needed_approx": 150 - 9,
            "distinct_disciplines": len(set(r["discipline"] for r in queue_rows)),
        },
        "rows": queue_rows,
    }
    return artifact


def write_md(artifact: dict) -> str:
    rows = artifact["rows"]
    by_disc: dict[str, list[dict]] = {}
    for r in rows:
        by_disc.setdefault(r["discipline"], []).append(r)

    # Most frequent discipline first (highest leverage to review).
    ordered = sorted(by_disc.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    lines: list[str] = []
    lines.append("# ANCHOR-208 Discipline Review Queue — 2026-10-02")
    lines.append("")
    lines.append("## What this is")
    lines.append("")
    lines.append(
        "The discipline axis has only **9** human-finalized labels (already locked in "
        "`ANCHOR_208_CONSOLIDATED_20261002.json`).  The other **197** are LLM silver "
        "(`anchor_adjudication`) + **2** whitespace-fixed dupes = **199** rows below."
    )
    lines.append("")
    lines.append(
        "To mirror the depth path (149 human-provenanced rows) you must adjudicate "
        "**~141** more discipline labels.  Review group-by-group; only flag rows whose "
        "discipline is WRONG.  'Agree in bulk' for a whole group is fine — that counts "
        "as human adjudication of every row in it."
    )
    lines.append("")
    lines.append(f"- Total rows in queue: **{artifact['counts']['total_unreviewed']}**")
    lines.append(f"- Silver (`anchor_adjudication`): {artifact['counts']['anchor_adjudication_silver']}")
    lines.append(f"- Whitespace-fixed: {artifact['counts']['whitespace_fixed']}")
    lines.append(f"- Already owner-finalized (NOT re-listed): **9**")
    lines.append(f"- Human target ≈ 150 → ~**{artifact['counts']['still_needed_approx']}** more verdicts")
    lines.append(f"- Distinct disciplines: {artifact['counts']['distinct_disciplines']}")
    lines.append("")
    lines.append("## Review queue (grouped by discipline, most common first)")
    lines.append("")

    for disc, group in ordered:
        lines.append(f"### {disc} ({len(group)})")
        for r in sorted(group, key=lambda x: x["item_id"]):
            flag = " [whitespace-fixed]" if r["discipline_status"] == "whitespace_fixed" else ""
            lines.append(f"- `{r['item_id']}` — {r['name']}  `domain={r['domain']}`{flag}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    artifact = build()
    OUT_JSON.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
    OUT_MD.write_text(write_md(artifact))
    print(f"wrote {OUT_JSON.name} ({len(artifact['rows'])} rows)")
    print(f"wrote {OUT_MD.name}")
    print(f"counts: {json.dumps(artifact['counts'], sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
