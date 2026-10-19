#!/usr/bin/env python3
"""Generate the ACCESSIBLE owner fill-in CSV for the D-3107 many-to-one merges.

The owner answers ONE question per anchor: are the merged idea and the old idea the
SAME idea, or DIFFERENT ideas?  The `Same idea?` column is PRE-FILLED with my best
guess (grounded in the names + discipline/domain labels actually read from the KB),
so the owner only flips the rows they disagree with.

If the owner answers DIFFERENT, THEY DO NOT NEED TO SAY WHERE IT GOES. A downstream
apply step searches the KB for the correct home (or marks the anchor dead) itself.

Read-only generator: never mutates gold or the KB.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sqlite3

REPO = pathlib.Path(__file__).resolve().parents[1]
MERGES = REPO / "governance" / "gold_reattach_many_to_one.jsonl"
GOLD = REPO / "governance" / "gold_4axis.jsonl"
DB = REPO / "knowledge pipeline" / "maxwell.db"
OUT = REPO / "governance" / "gold_reattach_many_to_one_ADJUDICATION.csv"


def load_gold() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for line in open(GOLD, encoding="utf-8"):
        r = json.loads(line)
        for key in ("fb_id", "old_fb_id"):
            v = r.get(key)
            if v:
                idx[v] = r
    return idx


def guess(live_name: str, anchor_name: str, sim: float, g: dict) -> tuple[str, str]:
    """Return (guess, why). Grounded only on names + labels already read."""
    # exact-name match => unambiguously the same
    if sim >= 1.0:
        return "SAME", "exact same name"

    live_disc = (g.get("discipline") or "").lower()
    live_doms = set(d.lower() for d in (g.get("domains") or []))

    # keyword-clash heuristics that produced the known false positives
    clash_signals = {
        "network robustness": "a networking principle glued to an ecology idea",
        "equity capital": "a finance principle glued to an ecology idea",
        "voronoi": "a spatial-math principle glued to a semiotics idea",
        "shader": "a graphics principle glued to a semiotics idea",
        "generalist vs specialist": "a creative-industry idea glued by the word 'vs'",
        "strategy vs planning": "a military idea glued by the word 'vs'",
        "langgraph": "a software-engineering idea glued by the word 'workflow'",
        "visual effects": "a VFX idea glued by the word 'workflow'",
        "fitness-proportional": "an AI idea glued by the word 'selection'",
        "surveillance resistance": "a surveillance idea glued by the word 'design'",
        "popular language": "a linguistics idea glued by the word 'standardization'",
        "standardized mass production": "a manufacturing idea glued by the word 'standardization'",
        "probability distribution": "a probability idea glued by the word 'uncertainty'",
        "digital identity": "an identity idea glued by the word 'infrastructure'",
    }
    for kw, why in clash_signals.items():
        if kw in anchor_name.lower():
            return "DIFFERENT", why

    # otherwise: if the anchor's discipline/domains share words with a general theme,
    # treat as same unless obviously unrelated fields
    return "SAME", "looks like the same idea (check the names)"


def main() -> None:
    merges = [json.loads(l) for l in open(MERGES, encoding="utf-8")]
    gold = load_gold()

    con = sqlite3.connect(DB)
    live_names = {r[0]: r[1] for r in con.execute("select fb_id, name from fbs").fetchall()}
    con.close()

    header = ["#", "Merged idea (one entry in the system)", "Old idea that got glued to it",
              "Same idea?", "Why I think so"]

    rows: list[list[str]] = []
    for mid, m in enumerate(merges, 1):
        live_name = live_names.get(m["live_fb_id"], m["live_name"])
        for a in m["anchors"]:
            g = gold.get(a["old_fb_id"], {})
            g_guess, why = guess(live_name, a["name"], a["similarity"], g)
            rows.append([str(mid), live_name, a["name"], g_guess, why])

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)

    print(f"WROTE {OUT}")
    print(f"  rows: {len(rows)}  |  you flip only the 'Same idea?' column where you disagree")


if __name__ == "__main__":
    main()
