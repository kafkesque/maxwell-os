#!/usr/bin/env python3
"""D-B (BUG-705): calibrate the S5 paraphrase similarity threshold.

Mirrors pipeline/nli_calibrate.py (D-2822). Sweeps the bge-m3 STS cosine threshold over a
gold set of (definition, evidence, label) triples and reports P/R/F1 per threshold. Mints the
`paraphrase_calibration` stamp {decision, threshold} ONLY when a threshold meets the ship bar
(default precision >= 0.85, matching D-2822's 0.852 bar) — the threshold is measured, never
guessed.

Gold file contract (JSONL, one object per line):
    {"definition": str, "evidence": str, "label": "paraphrase_true" | "non_paraphrase"}

A gold set is seeded from the 2,258 recoverable NEUTRAL rows (ent>=1, contra=0) labelled
`paraphrase_true`, plus a matching PASS/contra control labelled `non_paraphrase`. This script
does NOT auto-generate the gold labels (that is a human/LLM labelling step); it only measures.

Usage:
    python3 scripts/paraphrase_calibrate.py --gold PATH [--ship-precision 0.85] [--decision D-XXXX] [--apply]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pipeline.pipeline_paths import PROJECT_ROOT
from pipeline.stage5_verify import _paraphrase_similarity


def _gold_similarity(g: dict) -> float:
    """Production-equivalent similarity for one gold row (max STS over clean passages).

    Reuses stage5._paraphrase_similarity — the EXACT production primitive — so the
    calibrated threshold is measured on the same function that will run in the gate
    (max STS cosine over up to 8 clean passages). Falls back to the joined `evidence`
    string when `evidence_passages` is absent (legacy gold contract).
    """
    passages = g.get("evidence_passages") or [g["evidence"]]
    return _paraphrase_similarity(g["definition"], list(passages))


def load_gold(path: Path) -> list[dict]:
    """Read + validate the gold JSONL (definition, evidence, label)."""
    rows: list[dict] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"gold:{i}: bad JSON: {e}", file=sys.stderr)
            raise
        if not obj.get("definition") or not obj.get("evidence"):
            raise ValueError(f"gold:{i}: missing definition/evidence: {obj}")
        if obj["label"] not in ("paraphrase_true", "non_paraphrase"):
            raise ValueError(f"gold:{i}: bad label {obj.get('label')!r}")
        rows.append(obj)
    return rows


def sweep(gold: list[dict], ship_precision: float) -> tuple[float, float, float, float] | None:
    """Embed gold pairs, sweep thresholds, return the best ship-eligible (thresh, P, R, F1)."""
    print(
        f"embedding {len(gold)} definition/passage pairs via bge-m3 "
        "(max-over-passages, matching production _paraphrase_similarity) ...",
        file=sys.stderr,
    )
    sims = [_gold_similarity(g) for g in gold]
    labels = [1 if g["label"] == "paraphrase_true" else 0 for g in gold]

    best: tuple[float, float, float, float] | None = None
    print("thresh   P      R      F1     tp  fp  fn")
    for thresh in [round(0.50 + i * 0.01, 2) for i in range(50)]:
        tp = sum(1 for s, l in zip(sims, labels) if s >= thresh and l == 1)
        fp = sum(1 for s, l in zip(sims, labels) if s >= thresh and l == 0)
        fn = sum(1 for s, l in zip(sims, labels) if s < thresh and l == 1)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        flag = "  <-- ship" if precision >= ship_precision else ""
        print(f"{thresh:.2f}    {precision:.3f}  {recall:.3f}  {f1:.3f}  {tp:3d} {fp:3d} {fn:3d}{flag}")
        if precision >= ship_precision and (best is None or thresh > best[0]):
            best = (thresh, precision, recall, f1)
    return best


def apply_stamp(decision: str, threshold: float) -> None:
    """Write {decision, threshold} into stage5.paraphrase_calibration (enabled stays false)."""
    cfg_path = PROJECT_ROOT / "config" / "pipeline_config.yaml"
    text = cfg_path.read_text(encoding="utf-8")
    pattern = re.compile(r"(  paraphrase_calibration:\n    decision: )[^\n]*(\n    threshold: )[^\n]*")
    new = f"  paraphrase_calibration:\n    decision: {decision}\n    threshold: {threshold}"
    if not pattern.search(text):
        raise RuntimeError("stage5.paraphrase_calibration block not found in pipeline_config.yaml")
    cfg_path.write_text(pattern.sub(new, text), encoding="utf-8")
    print(f"wrote {decision}/{threshold} to {cfg_path.name} (enabled unchanged)")


def main() -> int:
    ap = argparse.ArgumentParser(description="D-B (BUG-705) paraphrase threshold calibration")
    ap.add_argument("--gold", required=True, type=Path, help="JSONL gold set")
    ap.add_argument("--ship-precision", type=float, default=0.85, help="min precision to ship (default 0.85)")
    ap.add_argument("--decision", type=str, default=None, help="decision id under which to mint the stamp")
    ap.add_argument("--apply", action="store_true", help="write the minted stamp to pipeline_config.yaml")
    args = ap.parse_args()

    gold = load_gold(args.gold)
    if len(gold) < 20:
        print(f"ERROR: gold set too small ({len(gold)} < 20) to calibrate reliably", file=sys.stderr)
        return 2

    best = sweep(gold, args.ship_precision)
    if best is None:
        print(f"\nERROR: no threshold meets ship bar (precision >= {args.ship_precision})", file=sys.stderr)
        return 3
    thresh, p, r, f1 = best
    print(f"\nSHIP: threshold={thresh:.2f} P={p:.3f} R={r:.3f} F1={f1:.3f}")

    if not args.decision:
        print("NOTE: --decision not supplied; stamp NOT minted. Re-run with --decision D-XXXX [--apply]")
        return 0
    print(f"MINT: paraphrase_calibration={{decision: {args.decision}, threshold: {thresh}}}")
    if args.apply:
        apply_stamp(args.decision, thresh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
