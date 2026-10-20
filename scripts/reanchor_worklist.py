#!/usr/bin/env python3
"""reanchor_worklist.py — surface the BUG-956 re-anchoring WORKLIST (D-3116 option 1).

The bridge joins the 208-row ruler to the canonical store by NAME (normalised
collapse_whitespace). After D-2881's rechunk-v4-20260929 re-segmentation, 195 of the 208
ruler names dangle (no casefold-exact store name). D-3116 ruled option 1 = RE-ANCHORING:
the OWNER re-adjudicates each dangling concept to the correct canonical-store name (or
declares it dropped). This script is the MECHANICAL half only — it SURFACES, per dangling
name, the top content-word-overlap store candidates for the human to judge. It NEVER
picks (D-2658: never guess; a nearest-name re-key would corrupt the anchor).

It does not write the store or the ruler. It writes a CSV worklist only.

Usage:
    python3 scripts/reanchor_worklist.py            # dry-run report
    python3 scripts/reanchor_worklist.py --apply    # write governance/ANCHOR_208_REANCHOR_WORKLIST_<date>.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import tempfile
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULER = ROOT / "governance" / "ANCHOR_208_BRIDGE_RULER_20261002.csv"
STORE_DB = ROOT / "knowledge pipeline" / "maxwell.db"
STORE_TABLE = "fbs"
CANONICAL_RUN = "rechunk-v4-20260929"
STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "and", "or", "for", "to", "with", "by", "from",
    "at", "as", "is", "are", "was", "were", "be", "into", "over", "under", "vs", "via",
}


def _content_words(name: str) -> set[str]:
    """Normalise a name to its content-word set (casefold, strip non-alpha, drop stopwords)."""
    toks = re.findall(r"[a-z0-9]+", (name or "").casefold())
    return {t for t in toks if t not in STOPWORDS and len(t) > 1}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _load_ruler() -> list[dict[str, str]]:
    with open(RULER, newline="", encoding="utf-8-sig") as fh:  # utf-8-sig strips the BOM
        return [
            {"item_id": r["item_id"].strip(), "name": (r.get("name") or "").strip()}
            for r in csv.DictReader(fh)
            if (r.get("item_id") or "").strip()
        ]


def _load_store() -> list[str]:
    db = str(STORE_DB)
    if not os.path.exists(db):
        raise SystemExit(f"store not found: {db}")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute(
        f"SELECT name FROM {STORE_TABLE} WHERE pipeline_run_id = ?", (CANONICAL_RUN,)
    ).fetchall()
    con.close()
    return [r[0].strip() for r in rows if r[0] and str(r[0]).strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="surface the BUG-956 re-anchoring worklist (candidates only, never picks)")
    ap.add_argument("--apply", action="store_true", help="write the CSV worklist")
    ap.add_argument("--top", type=int, default=5, help="candidates per dangling name (default 5)")
    args = ap.parse_args(argv)

    ruler = _load_ruler()
    store = _load_store()
    store_set = {n.casefold() for n in store}
    store_words = {n: _content_words(n) for n in store}

    dangling: list[dict[str, object]] = []
    for row in ruler:
        if row["name"].casefold() in store_set:
            continue
        rw = _content_words(row["name"])
        scored = sorted(
            ((_jaccard(rw, sw), sn) for sn, sw in store_words.items()),
            key=lambda t: (-t[0], t[1].casefold()),
        )[: args.top]
        dangling.append(
            {
                "item_id": row["item_id"],
                "ruler_name": row["name"],
                "best_jaccard": round(scored[0][0], 3) if scored else 0.0,
                "candidates": " || ".join(f"{j:.2f}:{sn}" for j, sn in scored if j > 0),
            }
        )

    dangling.sort(key=lambda r: (r["best_jaccard"], r["item_id"]))  # weakest first = adjudicate first
    print(f"ruler {len(ruler)} rows; store {len(store)} canonical names; {len(dangling)} dangling")

    if args.apply:
        out = ROOT / "governance" / f"ANCHOR_208_REANCHOR_WORKLIST_{datetime.now():%Y%m%d}.csv"
        fd, tmp = tempfile.mkstemp(dir=str(out.parent), prefix=".reanchor_", suffix=".tmp")
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["item_id", "ruler_name", "best_jaccard", "candidates"])
            w.writeheader()
            for r in dangling:
                w.writerow(r)
        os.replace(tmp, out)  # crash-safe (C6)
        print(f"worklist written: {out}")
    else:
        for r in dangling[:10]:
            print(f"  {r['item_id']} [{r['best_jaccard']:.2f}] {r['ruler_name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
