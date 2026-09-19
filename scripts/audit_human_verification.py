#!/usr/bin/env python3
"""audit_human_verification.py — definitive per-axis provenance of verified_core.

Answers: "what has the human actually reviewed, and what still needs a verdict?"
Builds a per-row × per-axis provenance map across ALL adjudication artifacts and
emits a CSV of rows that still need action (reliable-pair vote / nothing).

Read-only. Deterministic. No model calls, no DB writes.
"""
from __future__ import annotations

import ast
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Set

ROOT = Path(__file__).resolve().parent.parent
GOV = ROOT / "governance"

VC = GOV / "verified_core.jsonl"
P1 = GOV / "discipline_domain_vote_checkpoint.jsonl"
Q59 = GOV / "queue_59_vote_checkpoint.jsonl"
D2615 = GOV / "d2615_human_adjudication.jsonl"
F69 = GOV / "frontier69_final_adjudication.json"
P5 = GOV / "p5_adjudication_final.json"
REVIEW = GOV / "s4_discipline_review_sheet.utf8.csv"

AXES = ("content_type", "depth", "discipline", "domains")


def _literal(v: Any) -> Any:
    if isinstance(v, str) and v.strip().startswith(("{", "[")):
        try:
            return ast.literal_eval(v)
        except Exception:
            return v
    return v


def _load_jsonl(p: Path) -> list:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    vc = _load_jsonl(VC)
    by_fb = {r["fb_id"]: r for r in vc}
    by_ex = {r["example_id"]: r for r in vc if r.get("example_id")}

    # human-source per (fb_id, axis)
    human: Dict[str, Dict[str, str]] = defaultdict(dict)

    # frontier69 (example_id → 4 axes)
    f69 = json.loads(F69.read_text(encoding="utf-8"))
    for exid, rec in f69.items():
        fb = by_ex.get(exid, {}).get("fb_id")
        if not fb:
            continue
        for ax in AXES:
            if rec.get(ax):
                human[fb][ax] = "frontier69"

    # d2615 (fb_id → content_type OR depth)
    for r in _load_jsonl(D2615):
        if r.get("source") == "human" and r.get("axis") in AXES:
            human[r["fb_id"]][r["axis"]] = "d2615"

    # 63 contested discipline review
    if REVIEW.exists():
        for row in csv.DictReader(open(REVIEW, encoding="utf-8")):
            v = (row.get("HUMAN_discipline_VERDICT") or "").strip()
            if v and row.get("fb_id") in by_fb:
                human[row["fb_id"]]["discipline"] = "s4-review"

    # 216-row DOMAIN review sheet (cp1252; fb_id is the blank first column)
    dom_sheet = GOV / "s4_domain_review_sheet.csv"
    if dom_sheet.exists():
        for row in csv.DictReader(open(dom_sheet, encoding="cp1252")):
            fb = row.get("") or row.get(" ")  # blank first-column header
            if not fb or fb not in by_fb:
                continue
            if (row.get("HUMAN_domain_VERDICT") or "").strip():
                human[fb]["domains"] = "s4-domain-review"
            if (row.get("discipline_human") or "").strip():
                human[fb]["discipline"] = "s4-domain-review"

    # P5 (fb_id → axes with FIX_LABEL)
    p5 = json.loads(P5.read_text(encoding="utf-8"))
    p5_items = p5.get("items") or p5.get("verdicts") or []
    for it in p5_items:
        fb = it.get("fb_id") or it.get("example_id")
        if isinstance(fb, str) and fb in by_fb:
            for ax in AXES:
                if it.get(ax) or it.get(f"final_{ax}"):
                    human[fb][ax] = "p5"
    # P5 meta may carry a flat dict of fixes; best-effort
    for k, v in p5.items():
        if isinstance(v, dict) and (v.get("fb_id") or v.get("example_id")):
            fb = v.get("fb_id") or v.get("example_id")
            if isinstance(fb, str) and fb in by_fb:
                for ax in AXES:
                    if v.get(ax):
                        human[fb][ax] = "p5"

    # reliable-pair vote per (fb_id, axis)
    vote: Dict[str, Dict[str, str]] = defaultdict(dict)
    for r in _load_jsonl(P1):
        fb = r["fb_id"]
        v = r.get("votes", {})
        disc = {m.get("discipline") for m in v.values() if isinstance(m, dict) and m.get("discipline")}
        doms = [m.get("domains") for m in v.values() if isinstance(m, dict) and m.get("domains")]
        if len(disc) == 1 and None not in disc:
            vote[fb]["discipline"] = "p1-pair"
        if len(doms) == 2 and all(doms) and set(map(tuple, map(sorted, doms))):
            vote[fb]["domains"] = "p1-pair"
    for r in _load_jsonl(Q59):
        fb = r["fb_id"]
        for ax, flag in (("depth", "depth_agreed"), ("discipline", "discipline_agreed"), ("domains", "domains_agreed")):
            if r.get(flag) and r.get(ax):
                vote[fb][ax] = "d2631-pair"

    # classify every row
    rows_out = []
    n_complete = n_missing = 0
    for r in vc:
        fb = r["fb_id"]
        missing = []
        for ax in AXES:
            src = r.get(f"{ax}_source")
            is_human = fb in human and ax in human[fb]
            is_vote = fb in vote and ax in vote[fb]
            is_auth = src is not None and src not in ("golden-silver",)  # non-empty, non-silver
            if is_human or is_vote or (is_auth and src not in ("golden-silver", "p5:claude")):
                pass
            else:
                missing.append(ax)
        status = "complete" if not missing else "incomplete"
        if not missing:
            n_complete += 1
        else:
            n_missing += 1
        rows_out.append({
            "fb_id": fb,
            "name": r.get("name", ""),
            "verification_status": r.get("verification_status"),
            "content_type": r.get("content_type"),
            "depth": r.get("depth"),
            "discipline": r.get("discipline"),
            "domains": ",".join(r.get("domains") or []),
            "missing_axes": ",".join(missing),
            "status": status,
            "action": "" if not missing else "reliable-pair vote (depth+discipline+domains)",
        })

    incomplete = [r for r in rows_out if r["status"] == "incomplete"]
    # separate stale-label (complete but verification_status == pending-human)
    stale = [r for r in rows_out if r["status"] == "complete" and r["verification_status"] == "pending-human"]

    out = GOV / "remaining_verification_audit.csv"
    cols = ["fb_id", "name", "verification_status", "content_type", "depth", "discipline", "domains", "missing_axes", "status", "action"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows_out:
            w.writerow({c: r[c] for c in cols})

    print(f"verified_core rows: {len(vc)}")
    print(f"  complete (all 4 axes authoritative): {n_complete}")
    print(f"  incomplete (>=1 axis missing): {n_missing}")
    print(f"  stale-label (complete but still 'pending-human'): {len(stale)}")
    print(f"  human-reviewed rows (any axis): {len(human)}")
    print(f"  reliable-pair-voted rows (any axis): {len(vote)}")
    from collections import Counter
    miss = Counter(r["missing_axes"] for r in incomplete)
    print("  incomplete missing-axis patterns:")
    for k, v in miss.most_common():
        print(f"    {v:4d}  missing={k}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
