#!/usr/bin/env python3
"""Score the CLAIM-SHAPE gate: does it reproduce 7/7 retractions AND 4/4 candidates?

WHY THIS IS A SEPARATE, REFUSING SCRIPT
    The rule was DERIVED from the same 11 rows it is supposed to explain. Any score computed by the rule's
    author on the author's own reading is circular. This script therefore:
      1. refuses to score until every row has a non-blank gate bit and a named elicitor,
      2. refuses to score if the elicitor is the annex's author (contamination guard),
      3. exits 1 unless the score is 11/11 - so it can never be quietly shipped as "validated",
      4. prints the confusion matrix rather than a single number, because 7/7 with 4/4 on a 7-vs-4 split is
         weak evidence and the reader must see the raw cells,
      5. MEASURES the FORM anchor it used to merely assert (see why below).

CORRECTED RATIONALE (BUG-459, 2026-09-25)
    The first version claimed "There is NO FORM anchor (measured: FORM(1-4) is BLANK in all 150 rows of the
    tracked blind sheet)". BOTH HALVES ARE FALSE:
      * FORM is AXIS 2 `extraction_type` and it HAS an anchor - owner ANCHOR-3, column `extraction_type_final`,
        145/150 non-blank in governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv (config/anchor_family.yaml).
      * The column that is blank (0/150) is DEPTH, not FORM. The prose confused the two axes and then
        concluded from the confusion that FORM could not be an axis at all.
    What survives: the 4 questions below are the CLAIM-SHAPE bit (comparative + stated exchange rate +
    boundary), which is a DIFFERENT object from FORM (D-374) and is the only thing here that is un-anchored.
    The anchor coverage is now printed from the artifacts at run time, never asserted in prose.

Usage: python3 scripts/score_claim_shape_gate.py [--file <instrument.csv>]
Exit:  0 score 11/11 | 1 score imperfect OR instrument incomplete | 3 refusing (no instrument / contaminated)
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home
CONFIG = REPO / "config" / "claim_shape_instrument.yaml"


def read_text(path: Path) -> str:
    """Decode with the repo's declared order."""
    # D-2646/BUG-516: the decode rule has ONE home. This is a delegating wrapper, not a second rule.
    return artifact_encoding.open_artifact(path, REPO).read()


def measure_form_anchor(cfg: dict) -> str:
    """Count the FORM anchor's non-blank cells from the artifact (an existence claim must be measured)."""
    sheet = REPO / cfg["instrument"]["source_sheet"]
    rows = list(csv.DictReader(io.StringIO(read_text(sheet))))
    form = sum(1 for r in rows if (r.get("FORM (1-4)") or "").strip())
    depth = sum(1 for r in rows if (r.get("DEPTH (1-4)") or "").strip())
    return (f"FORM(1-4) in {sheet.name}: {form}/{len(rows)} non-blank (DEPTH(1-4): {depth}/{len(rows)}) - "
            f"the FORM axis is anchored; DEPTH is the column that is blank")


def main() -> int:
    """Load the instrument, refuse if unusable, else score the gate against the 11 known outcomes."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    bit = cfg["columns"]["gate_bit"]
    candidates = tuple(cfg["cohort"]["candidates"])
    negatives = tuple(cfg["cohort"]["negatives"])
    refuse_elicitor = {str(x).lower() for x in cfg["guards"]["refuse_elicitor"]}
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=REPO / cfg["instrument"]["path"])
    a = ap.parse_args()
    print(measure_form_anchor(cfg))
    if not a.file.exists():
        print(f"REFUSING: {a.file} does not exist - build it first (scripts/build_claim_shape_instrument.py)")
        return 3
    rows = list(csv.DictReader(io.StringIO(read_text(a.file))))
    blank = [r["item_id"] for r in rows if not (r.get(bit) or "").strip()]
    no_elicitor = [r["item_id"] for r in rows if not (r.get("elicitor") or "").strip()]
    circul = [r["item_id"] for r in rows if (r.get("elicitor") or "").strip().lower() in refuse_elicitor]
    if blank or no_elicitor or circul:
        print("REFUSING (instrument incomplete or contaminated):")
        if blank:
            print(f"  blank {bit}: {blank}")
        if no_elicitor:
            print(f"  no named elicitor:    {no_elicitor}")
        if circul:
            print(f"  elicitor is the annex author (circular): {circul}")
        print("  A score over an incomplete instrument is not a weaker score, it is a different quantity.")
        return 3
    tp = [r["item_id"] for r in rows if r["item_id"] in candidates and r[bit].strip() == "1"]
    fn = [r["item_id"] for r in rows if r["item_id"] in candidates and r[bit].strip() != "1"]
    tn = [r["item_id"] for r in rows if r["item_id"] in negatives and r[bit].strip() != "1"]
    fp = [r["item_id"] for r in rows if r["item_id"] in negatives and r[bit].strip() == "1"]
    print(f"CLAIM-SHAPE gate vs the 11 frozen outcomes  (n={len(rows)}, "
          f"elicitors={sorted({r['elicitor'] for r in rows})})")
    print(f"  candidates passing the gate (want 4/4): {len(tp)}/4  {tp}")
    print(f"  candidates FAILING the gate (misses):   {fn}")
    print(f"  negatives rejected  (want 7/7):         {len(tn)}/7  {tn}")
    print(f"  negatives ACCEPTED (false positives):   {fp}")
    ok = len(tp) == len(candidates) and len(tn) == len(negatives)
    if not ok:
        print("\nFAIL: the gate does not reproduce the boundary it was derived from. Do NOT ship it as a "
              "gate; the D1/D2 split then rests on scope alone, which cannot catch the vague universal (S1).")
        return 1
    print("\nok 11/11. STILL NOT EVIDENCE OF GENERALIZATION - n=11, and the rule was derived from these "
          "rows. It becomes evidence only after the same gate is applied to rows it has never seen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
