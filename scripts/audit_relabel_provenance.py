#!/usr/bin/env python3
"""audit_relabel_provenance.py — a machine relabel must carry WHO / WHAT / HOW-MUCH.

FORENSIC FINDING F-02 (2026-09-17). The production S2 checkpoint
(`knowledge pipeline/stage2_extract/t11/checkpoint.jsonl`, 8402 rows) differs from
`checkpoint.jsonl.pre_relabel` in 4057 of 8347 extraction_type cells (causal_mechanism
3763 -> 487). NOT ONE row carries a provenance key: the strings "relabel", "judge" and
"budget" do not appear in any record (R14 violation).

The historical gap cannot be closed retroactively for those rows, so this check is
FORWARD-looking and fail-closed on the artifact instead:

  * the newest `governance/relabel_report_*.json` must exist, and
  * it must carry judge_model, judge_max_tokens, reasoning_off_prefix_applied,
    cross_family_model and a non-zero cross_attempted count - the R5/C8 cross-family
    layer must have RUN (BUG-263: a flag layer nobody executed is not a verification).

Exit 0 = provenance artifact complete. Exit 1 = the newest relabel run is unauditable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORT_GLOB = "relabel_report_*.json"
REQUIRED = (
    "judge_model",
    "judge_max_tokens",
    "reasoning_off_prefix_applied",
    "cross_family_model",
    "cross_attempted",
)


def newest_report(directory: Path) -> Path | None:
    """Return the most recently modified relabel report, or None."""
    reports = sorted(directory.glob(REPORT_GLOB), key=lambda p: p.stat().st_mtime)
    return reports[-1] if reports else None


def main() -> int:
    """Verify the newest relabel report carries the full provenance envelope."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=str(REPO / "governance"))
    args = ap.parse_args()

    path = newest_report(Path(args.dir))
    if path is None:
        print("FAIL no relabel report found in " + args.dir + " (a relabel run must emit one)")
        return 1
    report = json.loads(path.read_text())
    print("newest relabel report: " + path.name)
    for key in REQUIRED:
        print("    " + key.ljust(30) + str(report.get(key)))
    missing = [key for key in REQUIRED if key not in report]
    if missing:
        print("DRIFT: report is missing " + ", ".join(missing))
        return 1
    if int(report.get("cross_attempted") or 0) == 0:
        print("DRIFT: the cross-family verification layer did not run (BUG-263 class)")
        return 1
    print("OK: relabel provenance complete and the cross-family layer ran")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
