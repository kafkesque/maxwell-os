#!/usr/bin/env python3
"""scripts/build_human_review.py — generate a human-review sample report.

Joins the triaged mislabel queue (governance/mislabel_triage.json) with FB
definition text from the DB, grouped by the WORST-offending labels, so a human
reviewer can diagnose SYSTEMIC mislabeling (per-label) instead of reading
1,989 FBs one-by-one.

Read-only w.r.t. the DB. Writes governance/human_review_sample.md via C6 safe_write.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_TRIAGE = _ROOT / "governance" / "mislabel_triage.json"
_OUT = _ROOT / "governance" / "human_review_sample.md"
_TOP_LABELS = 8   # C20: how many worst labels to cover
_SAMPLES_PER = 8  # C20: sample FBs per label
_DEF_MAX = 180    # C20: truncate definition in the report


def main() -> int:
    triage = json.loads(_TRIAGE.read_text(encoding="utf-8"))
    rows = triage["triage"]

    # Determine worst labels by total flagged-FB count (from the nli axes).
    label_count: Counter[str] = Counter()
    for r in rows:
        for a in r["nli_axes"]:
            label_count[a] += 1
    worst = [lab for lab, _ in label_count.most_common(_TOP_LABELS)]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Group triage rows by label (nli axis) and pick sample fb_ids per label.
    by_label: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        for a in r["nli_axes"]:
            if a in worst:
                by_label[a].append(r)

    lines = [
        "# HUMAN-REVIEW SAMPLE — triaged mislabel candidates (per label)",
        "",
        "> Generated from `governance/mislabel_triage.json` (1,989 FBs flagged by "
        "BOTH the k-NN neighbor-disagreement audit AND the T-NLI entailment audit).",
        "> **How to use:** for each label below, read the sample FB names/definitions "
        "and answer ONE question — *is the label right, or should these FBs be "
        "relabeled/merged/split?* You do NOT need to review all 1,989 one-by-one.",
        "",
    ]

    for lab in worst:
        recs = by_label[lab]
        # strongest contradiction gap first
        recs.sort(key=lambda r: -r["nli_max_contra_gap"])
        samples = recs[:_SAMPLES_PER]
        axis, name = lab.split(":", 1)
        lines += [f"## {lab} — {len(recs)} flagged FBs", ""]
        lines.append("| FB name | definition | knn agree | contra gap |")
        lines.append("|---|---|---|---|")
        for s in samples:
            row = conn.execute(
                "SELECT name, definition FROM fbs WHERE fb_id = ?", (s["fb_id"],)
            ).fetchone()
            if row is None:
                continue
            fb_name = (row["name"] or "?")[:60]
            defn = (row["definition"] or "").replace("\n", " ")[:_DEF_MAX]
            lines.append(
                f"| {fb_name} | {defn} | {s['knn_min_agreement']} | "
                f"{s['nli_max_contra_gap']} |"
            )
        lines.append("")
    conn.close()

    safe_write(_OUT, "\n".join(lines), force_shrink=True)
    print(f"✅ wrote {_OUT.name}: {_TOP_LABELS} worst labels, "
          f"{_SAMPLES_PER} samples each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
