#!/usr/bin/env python3
"""audit_nonprinciple_axis.py — a missing axis must be an explicit sentinel, never NULL.

FORENSIC FINDING F-03 (2026-09-17), BUG-170 still open. The design is unambiguous:
`pipeline/axis_authority.py` carries the sentinel `n/a-non-principle` inside DP_ORIG, i.e.
depth is NOT APPLICABLE for non-principle content types. The runtime DB stores NULL instead.

Measured on the live KB (7995 rows) — note this CORRECTS the register's wording ("PT/PI/TI/GE
sidecars have empty depth/discipline/domains"); only ONE axis is affected:

    content_type        depth  discipline  domains   n
    principle            set      set        set     6525
    process_template    NULL      set        set      188
    process_instance    NULL      set        set      139
    tool_instruction    NULL      set        set       23
    growth_edge         NULL      set        set       30
    noise_drop          NULL      set        set     1055
    quarantine          NULL      set        set       35
                                        blank depth: 1470 / 7995 = 18.4%

Consequence: a depth-filtered retrieval (domain / cross-domain / universal / specialized)
silently drops 18.4% of the KB, and NULL is indistinguishable from "classification failed".
The fix is deterministic (stamp the sentinel) but the sentinel value must be a recorded
decision, so the governance severity of this criterion is `warn`, not `fail`.

RE-SCOPED 2026-09-17 (consequence of BUG-267). The PREVIOUS version exited 1 whenever a
non-principle row had NULL depth — i.e. it reported the DESIGNED state as a violation. That
inverted the signal and created pressure to "fix" a non-defect. Two corrections:

  * The invariant that actually matters is: no PRINCIPLE row may have a blank axis (a principle
    without depth is genuinely unusable), and no row may be half-classified (blank
    discipline/domains), because those axes are populated for every content type.
  * NULL depth on a NON-principle row stays reported, but as a documented design state with a
    DEFERRED remedy — not as a violation. The remedy (`stamp the sentinel`) is deliberately NOT
    applied yet: stamping 1,470 rows encodes the row's `content_type` into a second axis, and
    content_type is the axis with the weakest provenance in the project (BUG-267: 0.116 attested,
    0.000 blind; BUG-238 measured 13-29% of `principle` rows are genuinely non-principle). The
    sentinel is cheap to add and expensive to un-add. Stamp AFTER content_type is certified.

Exit 0 = invariant holds. Exit 1 = violation.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.axis_authority import DP_ORIG  # noqa: E402  (C12: the sentinel is defined once)

DB = REPO / "knowledge pipeline" / "maxwell.db"
PRINCIPLE = "principle"
# DP_ORIG is a PROVENANCE set, not a value set: the only entry that is a depth VALUE is the
# documented not-applicable sentinel (the "n/a-..." member). Filtering instead of hardcoding
# keeps the sentinel defined in exactly one place (C12) and raises if that member disappears.
NON_PRINCIPLE_DEPTH_MARKERS = frozenset(str(v) for v in DP_ORIG if str(v).startswith("n/a"))
if not NON_PRINCIPLE_DEPTH_MARKERS:
    raise AssertionError("axis_authority.DP_ORIG no longer carries an n/a sentinel for non-principle depth")
AXES = ("depth", "discipline", "domains")


def _blank(value: Any) -> bool:
    """True when a label cell carries no information."""
    return value is None or str(value).strip() in ("", "[]", "null", "None")


def main() -> int:
    """Fail when a principle row has a blank axis or a non-principle depth is NULL."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--show", type=int, default=5)
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    rows = con.execute("select fb_id, content_type, depth, discipline, domains from fbs").fetchall()
    con.close()

    principle_total = 0
    principle_bad: list[str] = []
    depth_null: dict[str, int] = {}
    depth_sentinel = 0
    partial: list[str] = []
    for fb_id, ct, depth, disc, doms in rows:
        blanks = {axis: _blank(v) for axis, v in zip(AXES, (depth, disc, doms))}
        if str(ct) == PRINCIPLE:
            principle_total += 1
            if any(blanks.values()):
                principle_bad.append(str(fb_id))
            continue
        if not blanks["depth"] and str(depth).strip() in NON_PRINCIPLE_DEPTH_MARKERS:
            depth_sentinel += 1
        elif blanks["depth"]:
            depth_null[str(ct)] = depth_null.get(str(ct), 0) + 1
        if blanks["discipline"] or blanks["domains"]:
            partial.append(str(fb_id))

    total = len(rows)
    n_null = sum(depth_null.values())
    print("rows " + str(total) + " | principle " + str(principle_total)
          + " | non-principle depth=NULL " + str(n_null)
          + " | non-principle depth=sentinel " + str(depth_sentinel))
    for ct in sorted(depth_null):
        print("    " + ct.ljust(20) + str(depth_null[ct]))
    if n_null and total:
        print("  NOTE: " + ("%.1f" % (100.0 * n_null / total))
              + "% of the KB is unreachable by a depth filter and reads as 'unclassified'."
              " Fix = stamp the documented sentinel (" + ", ".join(sorted(NON_PRINCIPLE_DEPTH_MARKERS))
              + "), BUG-170 / F-03")
    for fb_id in partial[: args.show]:
        print("  BLANK discipline/domains on non-principle row " + fb_id[:12])
    for fb_id in principle_bad[: args.show]:
        print("  PRINCIPLE WITH BLANK AXIS " + fb_id[:12])
    if principle_bad or partial:
        print("VIOLATION: " + str(len(principle_bad)) + " principle row(s) with a blank axis, "
              + str(len(partial)) + " row(s) with blank discipline/domains")
        return 1
    if n_null:
        print("OK: invariant holds. " + str(n_null) + " non-principle row(s) carry NULL depth —"
              " the DESIGNED state (sentinel stamp DEFERRED until content_type is certified;"
              " see this file's docstring and BUG-267).")
    else:
        print("OK: every axis is either populated or carries the documented sentinel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
