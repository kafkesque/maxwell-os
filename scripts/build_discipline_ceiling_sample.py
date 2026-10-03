#!/usr/bin/env python3
"""Build the 30-anchor stratified sample for the BUG-622 inter-rater ceiling
measurement (D-2792/D-2793 step 1, D-2794).

Produces a BLANK labeling sheet (gold discipline HIDDEN) + a closed-menu
reference so two independent raters can label the same 30 anchors. The owner
scores the returned labels against the gold key
(governance/discipline_anchor_conformance_20261002.json) AFTER both raters
finish — never before, to avoid anchoring. Deterministic (seed 42). No model,
$0 marginal cost (C1).
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent

DEFAULT_ANCHOR: str = "governance/discipline_anchor_conformance_20261002.json"
DEFAULT_MENU: str = "config/closed_menu_v5.json"
DEFAULT_DB: str = "knowledge pipeline/maxwell.db"
DEFAULT_N: int = 30
SEED: int = 42


def load_group_map(menu_path: str) -> dict[str, str]:
    menu = json.loads(Path(menu_path).read_text(encoding="utf-8"))["disciplines"]
    return {d["value"]: (d.get("group") or "emerging") for d in menu}


def load_menu_rows(menu_path: str) -> list[dict]:
    return json.loads(Path(menu_path).read_text(encoding="utf-8"))["disciplines"]


def load_texts(db_path: str) -> dict[str, dict[str, str]]:
    con = sqlite3.connect(db_path)
    q = "SELECT name, definition, elaboration, evidence, source_text FROM fbs"
    out: dict[str, dict[str, str]] = {}
    for name, definition, elaboration, evidence, source_text in con.execute(q):
        out[str(name)] = {
            "definition": (definition or "").strip(),
            "elaboration": (elaboration or "").strip(),
            "evidence": (evidence or "").strip(),
            "source_text": (source_text or "").strip(),
        }
    con.close()
    return out


def excerpt(s: str, n: int = 500) -> str:
    return s if len(s) <= n else s[:n] + "…"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor", default=DEFAULT_ANCHOR)
    ap.add_argument("--menu", default=DEFAULT_MENU)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--n", type=int, default=DEFAULT_N)
    ap.add_argument("--out", default=str(REPO / "temp" / "discipline_ceiling_sample_30.csv"))
    args = ap.parse_args()

    group_map = load_group_map(args.menu)
    rows = json.loads(Path(args.anchor).read_text(encoding="utf-8"))["rows"]
    gold = [r for r in rows if r["discipline"] in group_map]
    for r in gold:
        r["group"] = group_map[r["discipline"]]
    texts = load_texts(args.db)
    gold = [r for r in gold if r["name"] in texts]

    # stratified proportional allocation (largest remainder), min 1 per group
    rng = np.random.default_rng(SEED)
    groups = sorted({r["group"] for r in gold})
    n_groups = len(groups)
    frac = {g: sum(1 for r in gold if r["group"] == g) for g in groups}
    base = {g: max(1, int(np.floor(frac[g] / len(gold) * args.n))) for g in groups}
    remaining = args.n - sum(base.values())
    order = sorted(groups, key=lambda g: -(frac[g] / len(gold) * args.n - base[g]))
    i = 0
    while remaining > 0:
        base[order[i % n_groups]] += 1
        remaining -= 1
        i += 1
    while sum(base.values()) > args.n:
        base[max(groups, key=lambda g: base[g])] -= 1

    sampled: list[dict] = []
    for g in groups:
        pool = [r for r in gold if r["group"] == g]
        rng.shuffle(pool)
        sampled.extend(pool[: base[g]])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "name", "definition", "elaboration", "evidence_excerpt", "rater_discipline"])
        for r in sampled:
            t = texts[r["name"]]
            w.writerow([r["item_id"], r["name"], t["definition"], t["elaboration"], excerpt(t["evidence"]), ""])

    menu_path = Path(args.out).with_name("discipline_ceiling_menu.csv")
    with menu_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["discipline", "group", "definition"])
        for d in load_menu_rows(args.menu):
            w.writerow([d["value"], d.get("group") or "emerging", d.get("definition", "")])

    print(f"sampled {len(sampled)}/{args.n} anchors (gold-hidden) -> {out_path}")
    print(f"menu -> {menu_path}")
    print("stratification:", dict(sorted(Counter(r["group"] for r in sampled).items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
