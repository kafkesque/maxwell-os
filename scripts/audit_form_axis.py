#!/usr/bin/env python3
"""audit_form_axis.py — AXIS 5 (extraction_type / object type) integrity in the runtime KB.

NAMING (settled from the schema, not from memory). `config/content_types.yaml` labels its axes
itself:

    AXIS 1 — content_type:    functional ROLE  (what kind of object: FB / PT / PI / TI / GE)
    AXIS 2 — extraction_type: epistemic FORM   (how the claim is justified)

So "what kind of object it is" is already axis 1. The axis that is genuinely a FIFTH, never
adjudicated axis is **extraction_type** — the FORM. It has no entry in `gold_4axis.jsonl`
(0/251), no per-row provenance in `fbs`, and — until this script — no integrity check at all.

FINDING F-14 (2026-09-17). The store serves TWO incompatible generations of the FORM axis, both
committed 2026-09-02/03, with nothing in the row to tell them apart:

    bucket                                   n     causal_mechanism
    joinable to the relabeled checkpoint   3941     8.8%   (convergent 11.1% / single 4.6%)
    no checkpoint counterpart (legacy)     4054    55.8%   (convergent 23.9% / single 56.4%)

The post-relabel baselines are known: convergent ~11.2%, single-source ~3.4%. The legacy
single-source rows sit at 56.4% — the PRE-repair distribution (the D2427/D2432 FORM-drift repair
took single-source causal_mechanism from ~65% to ~4%). So **3987 rows (49.9% of the KB) still
serve the label the repair was built to remove**, and `classification_status = CLEAN` for all
7995 rows, so nothing flags them.

Invariant enforced here (no thresholds needed):
  * every row's extraction_type must be one of the canonical values in `config/content_types.yaml`;
  * every row must be joinable to a provenance-bearing S2 record, i.e. its FORM must be
    reproducible — a label that cannot be traced to a record is not a measurement.

Exit 0 = invariant holds. Exit 1 = violation (currently 4054 untraceable rows).
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

DB = REPO / "knowledge pipeline" / "maxwell.db"
CONTENT_TYPES_CFG = REPO / "config" / "content_types.yaml"
FALLBACK_CHECKPOINT = REPO / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.jsonl"
FORM = "extraction_type"


def canonical_forms() -> frozenset[str]:
    """Read the canonical FORM values from the ontology config (C12: never hardcode)."""
    import yaml

    cfg = yaml.safe_load(CONTENT_TYPES_CFG.read_text())
    return frozenset(str(k) for k in (cfg.get("extraction_types") or {}))


def checkpoint_path() -> Path:
    """Resolve the S2 checkpoint from pipeline_paths when importable, else the known path."""
    try:
        from pipeline.pipeline_paths import STAGE2_CHECKPOINT  # type: ignore

        return Path(str(STAGE2_CHECKPOINT))
    except Exception:
        return FALLBACK_CHECKPOINT


def load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    """Index the S2 records by fb_id (the provenance-bearing source of every FORM label)."""
    out: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return out
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            fb_id = rec.get("fb_id")
            if fb_id:
                out[str(fb_id)] = rec
    return out


def _pct(counter: collections.Counter) -> str:
    """Render a counter as `value share%` pairs, largest first."""
    total = max(1, sum(counter.values()))
    return " ".join(k + "=" + str(round(100 * v / total, 1)) + "%" for k, v in counter.most_common())


def main() -> int:
    """Measure axis-5 validity and traceability; fail on untraceable or invalid FORM labels."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--checkpoint", default=str(checkpoint_path()))
    ap.add_argument("--show", type=int, default=3)
    args = ap.parse_args()

    forms = canonical_forms()
    ckpt = load_checkpoint(Path(args.checkpoint))
    con = sqlite3.connect(args.db)
    rows = con.execute(
        "select fb_id, " + FORM + ", content_type, is_convergent from fbs"
    ).fetchall()
    con.close()

    invalid = [r[0] for r in rows if str(r[1] or "").strip() not in forms]
    traced = [r for r in rows if str(r[0]) in ckpt]
    untraced = [r for r in rows if str(r[0]) not in ckpt]

    def by_generation(rs: list[tuple], label: str) -> None:
        conv = collections.Counter(r[1] for r in rs if r[3])
        single = collections.Counter(r[1] for r in rs if not r[3])
        print("  " + label.ljust(34) + "n=" + str(len(rs)).ljust(6))
        print("      convergent: " + (_pct(conv) or "-"))
        print("      single    : " + (_pct(single) or "-"))

    print("axis 5 (extraction_type) | rows " + str(len(rows)) + " | canonical values "
          + str(len(forms)) + " | invalid " + str(len(invalid)))
    print("  provenance-bearing checkpoint: " + str(Path(args.checkpoint).name)
          + " (" + str(len(ckpt)) + " records)")
    by_generation(traced, "traceable to a checkpoint record:")
    by_generation(untraced, "UNTRACEABLE (no source record):")

    for fb_id in invalid[: args.show]:
        print("  INVALID FORM " + str(fb_id)[:12])
    for fb_id in [r[0] for r in untraced[: args.show]]:
        print("  UNTRACEABLE " + str(fb_id)[:12])

    if invalid or untraced:
        print("DRIFT: " + str(len(invalid)) + " row(s) with a non-canonical FORM, "
              + str(len(untraced)) + " row(s) whose FORM is not traceable to a source record"
              + " (F-14: " + str(round(100.0 * len(untraced) / max(1, len(rows)), 1))
              + "% of the KB may serve the pre-repair FORM distribution)")
        return 1
    print("OK: every FORM label is canonical and traceable to a source record")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
