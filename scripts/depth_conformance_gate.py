#!/usr/bin/env python3
"""depth_conformance_gate.py — production depth classifier vs human-owner gold.

WHAT IT MEASURES
----------------
Conformance of the PRODUCTION S4 depth labeler of record (batch_depth_classify,
the D2611 prompt-versioned generative call) against the human-owner depth anchor
(governance/depth_anchor_conformance_<date>.json, built by D-2760 from the
owner-finalized ANCHOR-208 depths).

This is DIFFERENT from scripts/depth_pass_agreement.py, which measures the
inter-rater Krippendorff alpha OF THE PANEL (anchor reliability). This gate
measures the CLASSIFIER's fidelity to the human gold (conformance), which is the
D-274f intended use of the anchor ("a conformance set, not a training set").

STATISTIC (D-2611 — never bare accuracy on a skewed prior)
----------------------------------------------------------
The anchor is skewed (domain 67 / cross-domain 46 / specialized 34 / universal 2),
so raw agreement is dominated by the majority class. The gate reports BOTH:
  * raw agreement (accuracy) — reported, never gated
  * Cohen's kappa (chance-corrected) — the gated figure
Per-class precision/recall/F1 are reported so a class-level collapse (e.g. the
BUG-185 universal collapse) is visible even when aggregate kappa moves.

FLOOR
-----
Read from config (stage4.depth_conformance_kappa_floor, default 0.800 = the
owner-ruled operative floor in config/agreement_floor.yaml). Bands are reported,
not invented: >= operative = reliable; >= reporting (0.667) = tentative finding;
below = report the disagreement, decide nothing.

MODES (mirrors depth_pass_agreement.py)
---------------------------------------
  --dry-run   load + join + report counts + chance agreement; NO inference
  --selftest  verify cohen_kappa on fixed cases; NO inference; exit 0/1
  --limit N   run only the first N anchor FBs (live smoke)
  --gate      exit 1 when kappa is below the operative floor (CI); default is
              report-only, which never fails the aggregate rail
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DEFAULT_ANCHOR = REPO / "governance" / "depth_anchor_conformance_20261002.json"
REPORTING_FLOOR = 0.667
OPERATIVE_FLOOR = 0.800


def load_config_floor() -> tuple[float, str]:
    """Read stage4.depth_conformance_kappa_floor + path from config (C12)."""
    try:
        import yaml

        cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
        s4 = cfg.get("stage4", {})
        floor = float(s4.get("depth_conformance_kappa_floor", OPERATIVE_FLOOR))
        path = s4.get("depth_anchor_path", str(DEFAULT_ANCHOR))
        return floor, path
    except Exception as e:  # C16: surface, never silently default
        print(f"⚠️  depth conformance config unreadable ({type(e).__name__}: {e}) — floor 0.800", file=sys.stderr)
        return OPERATIVE_FLOOR, str(DEFAULT_ANCHOR)


def load_anchor(path: str) -> list[dict]:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    examples = doc.get("examples", [])
    if not examples:
        raise SystemExit(f"FAIL: depth anchor has no examples: {path}")
    declared = (doc.get("counts") or {}).get("total")
    if declared is not None and len(examples) != int(declared):
        raise SystemExit(
            f"FAIL: depth anchor drifted — {len(examples)} examples vs declared {declared} "
            f"(count-drift guard, BUG-624 class): {path}"
        )
    return examples


def cohen_kappa(gold: list[str], pred: list[str]) -> float:
    """Chance-corrected agreement (pure-Python, no numpy/scipy dependency)."""
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


def band(kappa: float) -> str:
    if kappa >= OPERATIVE_FLOOR:
        return "reliable (>= operative floor 0.800) — may gate"
    if kappa >= REPORTING_FLOOR:
        return "tentative (>= reporting floor 0.667) — reportable finding, licenses NO gate"
    return "below reporting floor — report the disagreement, decide nothing"


def run_inference(examples: list[dict], batch_size: int) -> list[str]:
    from pipeline.stage4_merged_call import batch_depth_classify

    fb_data = [
        {
            "name": e["name"],
            "definition": e["definition"],
            "mechanism": e["mechanism"],
            "extraction_type": e.get("extraction_type", ""),
        }
        for e in examples
    ]
    return batch_depth_classify(fb_data, batch_size=batch_size)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default=None, help="override the anchor JSON path")
    ap.add_argument("--dry-run", action="store_true", help="load + report only, no inference")
    ap.add_argument("--selftest", action="store_true", help="verify cohen_kappa, no inference")
    ap.add_argument("--limit", type=int, default=None, help="run only the first N FBs")
    ap.add_argument("--gate", action="store_true", help="exit 1 below the operative floor")
    ap.add_argument("--batch-size", type=int, default=None)
    args = ap.parse_args()

    floor, cfg_path = load_config_floor()
    anchor_path = args.anchor or cfg_path

    if args.selftest:
        cases = [
            (["a", "a", "b", "b"], ["a", "a", "b", "b"], 1.0, "perfect"),
            (["a", "a", "b", "b"], ["b", "b", "a", "a"], -1.0, "perfect-inverse"),
            (["a", "a", "a", "b"], ["a", "a", "a", "a"], 0.0, "majority-class-only"),
        ]
        ok = True
        for gold, pred, want, name in cases:
            got = round(cohen_kappa(gold, pred), 6)
            if abs(got - want) > 1e-6:
                print(f"  FAIL {name}: cohen_kappa={got} want={want}")
                ok = False
            else:
                print(f"  OK   {name}: cohen_kappa={got}")
        return 0 if ok else 1

    examples = load_anchor(anchor_path)
    if args.limit is not None:
        examples = examples[: args.limit]

    gold = [e["depth_label"] for e in examples]
    print(f"depth conformance anchor: {anchor_path}")
    print(f"  N = {len(examples)}")
    print(f"  gold distribution: {dict(Counter(gold))}")
    print(f"  floor (kappa): {floor}  (reporting {REPORTING_FLOOR} / operative {OPERATIVE_FLOOR})")

    if args.dry_run:
        # chance agreement if the classifier only ever emitted the majority class
        majority = Counter(gold).most_common(1)[0][0]
        base = cohen_kappa(gold, [majority] * len(gold))
        print(f"  DRY-RUN (no inference): majority-class kappa baseline = {base:.4f}")
        print("  live run:  python3 scripts/depth_conformance_gate.py [--gate] [--limit N]")
        return 0

    pred = run_inference(examples, args.batch_size or 4)
    kappa = cohen_kappa(gold, pred)
    acc = sum(1 for g, p in zip(gold, pred) if g == p) / len(gold)
    pc = per_class_metrics(gold, pred)

    print(f"  raw agreement (accuracy): {acc:.4f}   (reported, NOT gated)")
    print(f"  Cohen's kappa:            {kappa:.4f}   -> {band(kappa)}")
    print("  per-class:")
    for l in sorted(pc):
        m = pc[l]
        print(f"    {l:<14} P={m['precision']} R={m['recall']} F1={m['f1']} (gold n={m['n_gold']})")

    if args.gate and kappa < floor:
        print(f"FAIL-CLOSED: kappa {kappa:.4f} < operative floor {floor}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
