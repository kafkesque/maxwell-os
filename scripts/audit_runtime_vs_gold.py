#!/usr/bin/env python3
"""audit_runtime_vs_gold.py — does the runtime KB carry the adjudicated 4-axis truth?

FORENSIC FINDING F-01 (2026-09-17). The verified anchor (`governance/gold_4axis.jsonl`,
251 human/joint-vote adjudicated rows) is the project's own statement of truth for the four
axes. `scripts/propagate_content_type_decisions.py` pushed content_type into the DB (D2598)
but NOTHING propagates depth / discipline / domains. Measured on 2026-09-17:

    domains      199/251 mismatch (79.3%)
    discipline   109/251 mismatch (43.4%)
    depth         10/251 mismatch ( 4.0%)
    content_type   0/251 mismatch  <- the only axis ever propagated

The product (maxwell.db) therefore serves labels the project has already adjudicated as
wrong. This script re-derives the comparison from the filesystem on every run so the
divergence cannot silently return.

Exit 0 when every axis mismatch count is <= --max-mismatch (default 0).

D-3107 re-attachment (2026-10-19): each anchor now carries `invariant_key` (generation-invariant) and,
after scripts/apply_gold_reattach.py, either a `live_fb_id` (semantic re-attachment to the live generation)
or `disposition: dead` (owner-adjudicated removal). This script resolves a row by `live_fb_id` when present
(falling back to `fb_id`), and SKIPS dead rows — they are recorded decisions, not orphans. Missing therefore
means "an anchor that is neither re-attached nor dead", which is the true remaining drift.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
GOLD = REPO / "governance" / "gold_4axis.jsonl"
DB = REPO / "knowledge pipeline" / "maxwell.db"
AXES = ("content_type", "depth", "discipline", "domains")
DOMAIN_SEP = ","


def _s(value: Any) -> str:
    """Normalise a label cell to a comparable stripped string."""
    return "" if value is None else str(value).strip()


def _domains(value: Any) -> list[str]:
    """Parse a domains cell (JSON list, comma string, or NULL) into a sorted list."""
    if isinstance(value, list):
        return sorted(_s(v) for v in value if _s(v))
    text = _s(value)
    if text.startswith("["):
        try:
            return sorted(_s(v) for v in json.loads(text) if _s(v))
        except Exception:
            pass
    return sorted(part.strip() for part in text.split(DOMAIN_SEP) if part.strip())


def load_gold() -> list[dict[str, Any]]:
    """Read the frozen anchor rows (one JSON object per line)."""
    if not GOLD.exists():
        print("FAIL gold anchor missing: " + str(GOLD))
        sys.exit(2)
    return [json.loads(line) for line in GOLD.read_text(encoding='utf-8').splitlines() if line.strip()]


def main() -> int:
    """Compare every gold row against the runtime DB and report per-axis drift."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-mismatch", type=int, default=0, help="allowed mismatches per axis")
    ap.add_argument("--show", type=int, default=5, help="example rows to print per axis")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print("FAIL runtime DB missing: " + str(db))
        return 2
    con = sqlite3.connect(str(db))
    mismatches: dict[str, list[str]] = {axis: [] for axis in AXES}
    missing = 0
    compared = 0
    dead = 0
    reattached = 0
    for gold in load_gold():
        if gold.get("disposition") == "dead":
            dead += 1
            continue
        tid = gold.get("live_fb_id") or gold.get("fb_id")
        if "live_fb_id" in gold:
            reattached += 1
        row = con.execute(
            "select content_type, depth, discipline, domains from fbs where fb_id = ?",
            (tid,),
        ).fetchone()
        if row is None:
            missing += 1
            continue
        compared += 1
        stored = {"content_type": row[0], "depth": row[1], "discipline": row[2], "domains": row[3]}
        for axis in AXES:
            if axis == "domains":
                if _domains(gold.get("domains")) != _domains(stored[axis]):
                    mismatches[axis].append(str(gold.get("name"))[:60])
            elif _s(gold.get(axis)) != _s(stored[axis]):
                mismatches[axis].append(str(gold.get("name"))[:60])
    con.close()

    print("runtime vs gold_4axis: compared " + str(compared) + " row(s), missing from DB "
          + str(missing) + ", dead " + str(dead) + ", re-attached " + str(reattached))
    worst = 0
    for axis in AXES:
        bad = mismatches[axis]
        worst = max(worst, len(bad))
        pct = (100.0 * len(bad) / compared) if compared else 0.0
        print("  " + axis.ljust(13) + str(len(bad)).rjust(4) + " mismatch (" + ("%.1f" % pct) + "%)")
        for name in bad[: args.show]:
            print("      - " + name)
    # F-01/F-19 (BUG-944): a MISSING gold row is the strongest drift signal — the anchor
    # cannot even resolve against the runtime KB. fb_id = sha256(name|definition) is
    # generation-sensitive, so a corpus re-extraction orphans every anchor row; treating
    # missing as a no-op silently flipped this sentinel to a false "OK" (0 compared / 251
    # missing). Fail closed: any missing row above the floor is DRIFT.
    if missing > args.max_mismatch:
        print("DRIFT: " + str(missing) + " of " + str(compared + missing + dead)
              + " anchor row(s) MISSING from the runtime KB — golden anchor orphaned (F-01/F-19)")
        return 1
    if worst > args.max_mismatch:
        print("DRIFT: the runtime KB does not carry the adjudicated 4-axis labels (see F-01)")
        return 1
    print("OK: runtime KB matches the adjudicated anchor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
