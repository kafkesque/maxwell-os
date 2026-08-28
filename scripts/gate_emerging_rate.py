#!/usr/bin/env python3
"""gate_emerging_rate.py — D2485 post-S4 emerging-rate gate (BUG-150).

Runs AFTER Stage 4 completes, BEFORE S5/S6, on the FRESH S4 checkpoint. Measures
the fraction of FBs whose taxonomy fell back to `emerging` and fails closed
(exit non-zero) if any rate exceeds its config threshold.

Rationale (BUG-167 lesson): do NOT promote taxonomy labels against stale data.
A high emerging rate means the taxonomy is stale/mismatched for the current
corpus — the correct response is taxonomy review / S4-C-D2440, NOT blind
promotion. This gate makes that check automatic instead of manual.

Emerging semantics (D2485):
    emerging_real      discipline == "emerging" AND raw label was a real term
                       (genuine taxonomy gap → promotion candidate).
    emerging_unmapped  discipline == "emerging" AND raw label was empty/garbage
                       (NOT a gap — a fabrication risk, must stay ~0).
    domain collapse    domains == ["emerging"] (every raw domain failed to map).

Config (config/pipeline_config.yaml → taxonomy.*):
    emerging_discipline_rate_max, emerging_domain_rate_max, emerging_unmapped_rate_max

Usage:
    python3 scripts/gate_emerging_rate.py [--checkpoint PATH] [--allow] [--json]

Exit codes:
    0  all rates within thresholds
    1  at least one rate exceeds its threshold (fail-closed)
    2  checkpoint missing/unreadable
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl
from pipeline.pipeline_paths import STAGE4_5_CHECKPOINT, STAGE4_CHECKPOINT, _CFG


def _thresholds() -> dict[str, float]:
    t = _CFG.get("taxonomy", {})
    return {
        "discipline": float(t.get("emerging_discipline_rate_max", 0.35)),
        "domain": float(t.get("emerging_domain_rate_max", 0.30)),
        "unmapped": float(t.get("emerging_unmapped_rate_max", 0.05)),
    }


def measure(fbs: list[dict]) -> dict:
    """Compute emerging rates over a list of FB dicts."""
    n = len(fbs)
    if n == 0:
        return {"total": 0, "discipline_emerging": 0, "domain_collapsed": 0,
                "unmapped": 0, "rates": {}}
    disc_emerging = sum(1 for fb in fbs if fb.get("discipline") == "emerging")
    domain_collapsed = sum(1 for fb in fbs if fb.get("domains") == ["emerging"])
    unmapped = sum(1 for fb in fbs if fb.get("taxonomy_match_method") == "emerging_unmapped")
    return {
        "total": n,
        "discipline_emerging": disc_emerging,
        "domain_collapsed": domain_collapsed,
        "unmapped": unmapped,
        "rates": {
            "discipline": round(disc_emerging / n, 4),
            "domain": round(domain_collapsed / n, 4),
            "unmapped": round(unmapped / n, 4),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="D2485 post-S4 emerging-rate gate")
    ap.add_argument("--checkpoint", type=Path, default=None,
                    help="S4 checkpoint to gate (default: STAGE4_5_CHECKPOINT else STAGE4_CHECKPOINT)")
    ap.add_argument("--allow", action="store_true",
                    help="Report only, never exit non-zero (advisory mode)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args()

    ckpt = args.checkpoint or (STAGE4_5_CHECKPOINT if STAGE4_5_CHECKPOINT.exists() else STAGE4_CHECKPOINT)
    if not ckpt.exists():
        msg = f"❌ S4 checkpoint not found: {ckpt}"
        print(msg, file=sys.stderr)
        if args.json:
            print(json.dumps({"error": "checkpoint_missing", "checkpoint": str(ckpt)}))
        return 2

    fbs = load_jsonl(ckpt, context="S4 checkpoint (emerging gate)")
    m = measure(fbs)
    thresh = _thresholds()

    if args.json:
        print(json.dumps({"checkpoint": str(ckpt), "thresholds": thresh, "measure": m}, indent=2))
    else:
        print("=" * 60)
        print("🔎 D2485 POST-S4 EMERGING-RATE GATE")
        print(f"   checkpoint: {ckpt}")
        print(f"   total FBs:  {m['total']}")
        print("-" * 60)
        for key, label in (("discipline", "discipline == 'emerging' (real gaps)"),
                           ("domain", "domains collapsed entirely to ['emerging']"),
                           ("unmapped", "empty/invalid raw label (garbage)")):
            rate = m["rates"].get(key, 0.0)
            cap = thresh[key]
            ok = rate <= cap
            flag = "✅" if ok else "🛑"
            print(f"   {flag} {label:<48} {rate:6.1%}  (max {cap:.0%})")
        print("=" * 60)

    violations = [k for k in ("discipline", "domain", "unmapped")
                  if m["rates"].get(k, 0.0) > thresh[k]]
    if violations and not args.allow:
        print(f"🛑 GATE FAILED — {', '.join(violations)} rate(s) above threshold. "
              "Do NOT promote labels (BUG-167); review taxonomy or run S4-C/D2440.",
              file=sys.stderr)
        return 1
    if not args.json:
        print("✅ Emerging rates within thresholds — S5 may proceed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
