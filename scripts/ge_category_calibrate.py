#!/usr/bin/env python3
"""T10 (D-2924): calibrate the growth_edge `category` classifier against a gold set.

Measures Cohen's kappa + per-class F1 over the 4 REAL category values
(open_tension, unverified_correlation, contested_claim, capability_gap), EXCLUDING
category=emerging from the kappa denominator (D-2929 LESSON: `emerging` is an
abstention routing side-channel, never a 5th predicted class — the retired T8 3-way
macro gate died precisely because it scored an abstention+noise bucket as a positive
class). `emerging` gold rows exercise D-2898 match_to_canonical + owner gate, NOT this
classifier, so they are excluded from BOTH the gold and predicted sides of the kappa
denominator.

This script is the measurement instrument declared by config/growth_edge_ontology.yaml
`calibration` block. It mints `calibration_decision` (and optionally flips gate_mode to
`enforcing`) ONLY when kappa >= kappa_floor (0.65) AND --apply is passed. Until then the
gate stays `advisory` (D-2924: requires_gold_before_volume).

Gold contract (YAML at config/golden/ge_category_gold.yaml):
    - body: "the speculative claim text"        # the GE unit under classification
      category: open_tension                    # GOLD label (one of the 4 real values)
      predicted: unverified_correlation         # classifier output (or `emerging` = miss)
    # category == emerging rows are EXCLUDED from kappa (D-2898 routing, not this gate)

This script does NOT auto-generate gold labels (human/LLM labelling step, R5
generator != verifier); it only measures. Mirrors scripts/paraphrase_calibrate.py
(D-B) in its fail-closed ship gate.

Usage:
    python3 scripts/ge_category_calibrate.py [--gold PATH] [--kappa-floor 0.65]
        [--decision D-XXXX] [--apply]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.growth_edge_ontology import category_values, EMERGING  # noqa: E402

_REAL_VALUES = sorted(category_values() - {EMERGING})  # the 4 real classes, never emerging


def load_gold(path: Path) -> list[dict]:
    """Load + validate the GE category gold YAML (body, category[, predicted])."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = doc.get("gold") if isinstance(doc, dict) else doc
    if not isinstance(rows, list):
        raise SystemExit(f"FAIL: {path.name} must be a list or {{gold: [...]}}")
    out: list[dict] = []
    for i, r in enumerate(rows, start=1):
        if not isinstance(r, dict) or not r.get("body") or not r.get("category"):
            raise SystemExit(f"FAIL: gold:{i}: missing body/category: {r}")
        if r["category"] not in category_values():
            raise SystemExit(f"FAIL: gold:{i}: category {r['category']!r} off-vocab {sorted(category_values())}")
        out.append(r)
    return out


def _confusion(gold: list[dict]) -> tuple[dict, int, int, int]:
    """Build the 4x4 confusion matrix over the REAL values (emerging gold rows excluded).
    Returns (matrix, n_included, n_excluded, n_unlabelled)."""
    n_excl = sum(1 for r in gold if r["category"] == EMERGING)
    n_unl = sum(1 for r in gold if r["category"] != EMERGING and not r.get("predicted"))
    included = [r for r in gold if r["category"] != EMERGING and r.get("predicted")]
    mat: dict = {g: {p: 0 for p in _REAL_VALUES + [EMERGING]} for g in _REAL_VALUES}
    for r in included:
        g, p = r["category"], r.get("predicted", EMERGING)
        if p not in mat[g]:
            p = EMERGING  # any off-vocab/abstention prediction is a miss
        mat[g][p] += 1
    return mat, len(included), n_excl, n_unl


def cohen_kappa(mat: dict, n: int) -> float:
    """Cohen's kappa over the 4 REAL classes only (predicted emerging counts as a miss)."""
    if n == 0:
        return 0.0
    po = sum(mat[g][g] for g in _REAL_VALUES) / n
    row_tot = {g: sum(mat[g].values()) for g in _REAL_VALUES}
    col_tot = {g: sum(mat[r][g] for r in _REAL_VALUES) for g in _REAL_VALUES}
    pe = sum(row_tot[g] * col_tot[g] for g in _REAL_VALUES) / (n * n)
    return (po - pe) / (1 - pe) if (1 - pe) else 0.0


def per_class_f1(mat: dict) -> dict:
    """Per-class F1 over the 4 REAL values (emerging predictions are misses, not a class)."""
    f1: dict = {}
    for g in _REAL_VALUES:
        tp = mat[g][g]
        fp = sum(mat[r][g] for r in _REAL_VALUES if r != g)
        # fn MUST include emerging predictions: an abstention/miss on a real-class row is a
        # false negative (D-2929 lesson — never let emerging silently escape the denominator).
        fn = sum(mat[g][p] for p in mat[g] if p != g)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1[g] = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return f1


def apply_stamp(decision: str, kappa: float) -> None:
    """Mint calibration_decision + flip gate_mode to enforcing (D-2924 fail-closed)."""
    cfg_path = ROOT / "config" / "growth_edge_ontology.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    text = text.replace("gate_mode: advisory", "gate_mode: enforcing")
    text = text.replace("calibration_decision: null", f"calibration_decision: {decision}")
    # record the measured kappa next to the floor for the audit trail
    if "measured_kappa:" not in text:
        text = text.replace(
            "  calibration_decision: ",
            f"  measured_kappa: {kappa:.4f}\n  calibration_decision: ",
        )
    else:
        import re
        text = re.sub(r"measured_kappa: [\d.]+", f"measured_kappa: {kappa:.4f}", text)
    cfg_path.write_text(text, encoding="utf-8")
    print(f"minted {decision} (kappa={kappa:.4f}), gate_mode=enforcing in {cfg_path.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description="T10 GE category classifier calibration")
    ap.add_argument("--gold", type=Path, default=ROOT / "config" / "golden" / "ge_category_gold.yaml")
    ap.add_argument("--kappa-floor", type=float, default=0.65)
    ap.add_argument("--decision", type=str, default=None)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not args.gold.exists():
        print(f"FAIL: gold set {args.gold} does not exist yet (D-2924: build + label it first)", file=sys.stderr)
        return 3

    gold = load_gold(args.gold)
    mat, n_inc, n_excl, n_unl = _confusion(gold)
    if n_inc < 20:
        print(f"FAIL: only {n_inc} non-emerging labelled rows (< 20) — cannot calibrate reliably", file=sys.stderr)
        return 2

    kappa = cohen_kappa(mat, n_inc)
    f1 = per_class_f1(mat)
    print(f"gold rows: {len(gold)} | included (real 4): {n_inc} | emerging-excluded: {n_excl} | unlabelled: {n_unl}")
    print(f"Cohen's kappa (4 REAL classes, emerging excluded): {kappa:.4f}  [floor {args.kappa_floor}]")
    print("per-class F1:")
    for g in _REAL_VALUES:
        print(f"  {g:24s} F1={f1[g]:.4f}")
    print("confusion (rows=gold, cols=predicted):")
    header = "  " + "".join(f"{p[:16]:>16s}" for p in _REAL_VALUES + [EMERGING])
    print(header)
    for g in _REAL_VALUES:
        print(f"  {g[:16]:<16s}" + "".join(f"{mat[g][p]:>16d}" for p in _REAL_VALUES + [EMERGING]))

    if kappa < args.kappa_floor:
        print(f"\nFAIL-CLOSED: kappa {kappa:.4f} < floor {args.kappa_floor} — gate stays advisory", file=sys.stderr)
        return 4
    print(f"\nSHIP: kappa {kappa:.4f} >= floor {args.kappa_floor}")

    if not args.decision:
        print("NOTE: --decision not supplied; stamp NOT minted. Re-run with --decision D-XXXX [--apply]")
        return 0
    print(f"MINT: calibration_decision={args.decision} (kappa={kappa:.4f})")
    if args.apply:
        apply_stamp(args.decision, kappa)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
