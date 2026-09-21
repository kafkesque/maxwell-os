"""Build a human-readable MENU REPAIR WORKSHEET from the ANCHOR-2 triage.

Turns machine triage output into a tick-list: domain slots the pipeline never emits, and
discipline pairs where the human label and the stored label disagree. No decisions are made here.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "governance" / "ANCHOR2_BLIND_SHEET_20260920.csv"
KEY = ROOT / "governance" / "ANCHOR2_KEY_20260920.json"
OUT = ROOT / "governance" / "MENU_REPAIR_WORKSHEET_20260921.md"


def load_rows() -> list:
    """Return the adjudication sheet rows joined to the pipeline labels of ANCHOR-2 key."""
    key = json.loads(KEY.read_text(encoding="utf-8"))["key"]
    rows = []
    with SHEET.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            kid = r.get("fb_id") or ""
            rows.append({"row": r["row"], "name": r["name"], "fb_id": kid,
                         "human_disc": (r.get("discipline_verdict") or "").strip(),
                         "human_domains": (r.get("domains_verdict") or "").strip(),
                         "pipe_disc": (key.get(kid) or {}).get("pipeline_discipline", ""),
                         "pipe_domains": (key.get(kid) or {}).get("pipeline_domains") or []})
    return rows


def main() -> int:
    """Write the worksheet and print the two short lists the owner has to rule on."""
    rows = load_rows()
    never: Counter = Counter()
    example: dict = defaultdict(list)
    emitted = {str(d).lower() for r in rows for d in r["pipe_domains"]}
    for r in rows:
        for d in [x.strip() for x in r["human_domains"].split(",") if x.strip()]:
            if d.lower() not in emitted:
                never[d] += 1
                example[d].append(str(r["row"]))
    pairs: Counter = Counter((r["human_disc"].lower(), r["pipe_disc"].lower()) for r in rows
                             if r["human_disc"] and r["human_disc"].lower() != r["pipe_disc"].lower())
    lines = ["# MENU REPAIR WORKSHEET - 2026-09-21", "",
             "Two short lists. Write A or B in the last column of each row. Nothing changes until you do.",
             "", "## PART 1 - domain slots the pipeline NEVER emits but your labels used",
             "", "| # | domain slot | your rows | example rows | A = ADD it to the menu | B = do NOT add |",
             "|---|---|---|---|---|---|"]
    for i, (d, n) in enumerate(never.most_common(16), 1):
        lines.append("| %d | %s | %d | %s |  |" % (i, d, n, ", ".join(example[d][:6])))
    lines += ["", "## PART 2 - disciplines where YOUR label and the STORED label disagree", "",
              "| # | your label | stored label | rows | A = SAME thing (make them aliases) | B = DIFFERENT (keep both, rewrite boundaries) |",
              "|---|---|---|---|---|---|"]
    for i, ((h, p), n) in enumerate(pairs.most_common(16), 1):
        lines.append("| %d | %s | %s | %d |  |" % (i, h, p, n))
    lines += ["", "## PART 3 - one question", "",
              "Bump config/taxonomy_v5.yaml to v6 with a migration map (old numbers stay readable)?",
              "Answer: 1 = yes / 2 = no  ->", ""]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("PART1", [(d, n) for d, n in never.most_common(16)])
    print("PART2", [((h, p), n) for (h, p), n in pairs.most_common(16)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
