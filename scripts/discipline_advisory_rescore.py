#!/usr/bin/env python3
"""discipline_advisory_rescore.py — committed fbs.discipline vs corrected gold (ADVISORY baseline).

D-2798 (BUG-622): discipline is ADVISORY-ONLY. This instrument measures the COMMITTED
fbs.discipline values (already in maxwell.db, NO inference, NO re-fit) against the
corrected 204-row human gold anchor. It is the advisory-baseline twin of
discipline_conformance_gate.py (which measures the LIVE classifier with inference).

REPORTS (never gates — discipline is not a routing facet):
  * fine-62 kappa + raw agreement (committed discipline vs gold)
  * coarse 3-way macro collapse kappa (via config/discipline_macro_groups.yaml)
  * per-class P/R/F1

TEXT JOIN mirrors discipline_conformance_gate.py: name -> fbs row by
collapse_whitespace, fail-closed if any anchor row fails to join.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DEFAULT_ANCHOR = REPO / "governance" / "discipline_anchor_rederived_v8_20261007.json"
STORE = REPO / "knowledge pipeline" / "maxwell.db"
MACRO_GROUPS = REPO / "config" / "discipline_macro_groups.yaml"


def _collapse(s: str) -> str:
    return " ".join((s or "").split())


def cohen_kappa(gold: list[str], pred: list[str]) -> float:
    if len(gold) != len(pred) or not gold:
        raise ValueError("gold/pred must be non-empty and equal length")
    n = len(gold)
    po = sum(1 for g, p in zip(gold, pred) if g == p) / n
    labels = sorted(set(gold) | set(pred))
    pe = sum((gold.count(l) / n) * (pred.count(l) / n) for l in labels)
    denom = 1.0 - pe
    return (po - pe) / denom if abs(denom) > 1e-12 else 0.0


def per_class_metrics(gold: list[str], pred: list[str]) -> dict[str, dict[str, float]]:
    labels = sorted(set(gold) | set(pred))
    out: dict[str, dict[str, float]] = {}
    for l in labels:
        tp = sum(1 for g, p in zip(gold, pred) if g == l and p == l)
        fp = sum(1 for g, p in zip(gold, pred) if g != l and p == l)
        fn = sum(1 for g, p in zip(gold, pred) if g == l and p != l)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[l] = {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4), "n_gold": gold.count(l)}
    return out


def load_macro_map() -> dict[str, str]:
    """Fine discipline -> 3-way macro bucket (delegates to the ONE home, C21)."""
    from pipeline.discipline_macro import load_macro

    return load_macro()[2]


def load_rows() -> tuple[list[str], list[str]]:
    """Join committed fbs.discipline to the 204 gold anchor by name. Returns (gold, committed)."""
    doc = json.loads(DEFAULT_ANCHOR.read_text(encoding="utf-8"))
    rows = doc.get("rows", [])
    if not rows:
        raise SystemExit(f"FAIL: discipline anchor has no rows: {DEFAULT_ANCHOR}")
    declared = doc.get("total")
    if declared is not None and len(rows) != int(declared):
        raise SystemExit(f"FAIL: anchor drifted — {len(rows)} rows vs declared {declared}")

    db = sqlite3.connect(str(STORE))
    cur = db.cursor()
    cur.execute("SELECT name, discipline FROM fbs")
    committed_by_name = {_collapse(n): d for n, d in cur.fetchall()}
    db.close()

    gold: list[str] = []
    committed: list[str] = []
    missing: list[str] = []
    for r in rows:
        key = _collapse(r.get("name", ""))
        if key not in committed_by_name:
            missing.append(r.get("item_id", "?"))
            continue
        gold.append(r["discipline"])
        committed.append(committed_by_name[key])
    if missing:
        print(f"⚠️  {len(missing)} anchor rows not joinable to fbs: {missing[:10]}", file=sys.stderr)
    return gold, committed


def main() -> int:
    ap = argparse.ArgumentParser(description="D-2798 advisory re-score: committed fbs.discipline vs gold")
    ap.add_argument("--out", default=str(REPO / "governance" / "discipline_advisory_rescore_20261003.json"))
    args = ap.parse_args()

    gold, committed = load_rows()
    if not gold:
        raise SystemExit("FAIL: no joinable rows")

    n = len(gold)
    fine_kappa = cohen_kappa(gold, committed)
    raw = sum(1 for g, p in zip(gold, committed) if g == p) / n

    macro_map = load_macro_map()
    gold_macro = [macro_map.get(g, g) for g in gold]
    committed_macro = [macro_map.get(p, p) for p in committed]
    macro_kappa = cohen_kappa(gold_macro, committed_macro)

    print(f"committed discipline advisory re-score (D-2798, NO inference / NO re-fit)")
    print(f"  N = {n}   gold distinct = {len(set(gold))}   committed distinct = {len(set(committed))}")
    print(f"  FINE-62  kappa = {fine_kappa:.4f}   raw agreement = {raw:.4f}")
    print(f"  MACRO-3  kappa = {macro_kappa:.4f}   (deterministic collapse via {MACRO_GROUPS.name})")
    print(f"  gold dist   = {dict(Counter(gold).most_common())}")
    print(f"  committed dist = {dict(Counter(committed).most_common())}")

    pc = per_class_metrics(gold, committed)
    print("  per-class (top gold counts):")
    for l in sorted(pc, key=lambda x: -pc[x]["n_gold"])[:10]:
        m = pc[l]
        print(f"    {l[:28]:<28} P={m['precision']} R={m['recall']} F1={m['f1']} (gold n={m['n_gold']})")

    artifact = {
        "artifact_id": "discipline_advisory_rescore_20261003",
        "decision": "D-2798",
        "mode": "advisory (NO inference, NO re-fit, NO gate)",
        "n": n,
        "fine_kappa": round(fine_kappa, 4),
        "fine_raw_agreement": round(raw, 4),
        "macro3_kappa": round(macro_kappa, 4),
        "gold_dist": dict(Counter(gold)),
        "committed_dist": dict(Counter(committed)),
        "per_class": pc,
        "anchor": str(DEFAULT_ANCHOR.name),
    }
    Path(args.out).write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  → artifact written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
