#!/usr/bin/env python3
"""Export the consolidated all-axes anchor authority to a human-readable CSV.

The 208-row consolidated artifact (ANCHOR_208_CONSOLIDATED_20261007.json) is the
single document that carries every anchor with every axis (depth + discipline +
domain/primary_domain).  This exporter renders it as a CSV so the owner can open
it directly and audit all 201 domain-bearing anchors in one sheet.

Deterministic / LLM-free.  Crash-safe write (tempfile -> fsync -> os.replace).
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "governance" / "ANCHOR_208_CONSOLIDATED_20261007.json"
OUT = ROOT / "governance" / "ANCHOR_208_ALL_AXIS_VIEW_20261007.csv"

COLUMNS = [
    "item_id",
    "name",
    "depth",
    "depth_label",
    "discipline",
    "domain",
    "primary_domain",
    "has_domain",
]


def _row_to_flat(r: dict) -> dict:
    """Flatten one consolidated anchor row to the export columns."""
    has_domain = bool(r.get("domain"))
    return {
        "item_id": r.get("item_id", ""),
        "name": r.get("name", ""),
        "depth": r.get("depth", ""),
        "depth_label": r.get("depth_label", ""),
        "discipline": r.get("discipline", ""),
        "domain": r.get("domain", ""),
        "primary_domain": r.get("primary_domain", ""),
        "has_domain": "yes" if has_domain else "no",
    }


def export() -> int:
    """Write the CSV; return the number of data rows written."""
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rows = src["rows"]

    # Crash-safe write.
    fd, tmp = tempfile.mkstemp(suffix=".csv", dir=str(OUT.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS)
            w.writeheader()
            for r in rows:
                w.writerow(_row_to_flat(r))
        # fsync then atomic replace.
        with open(tmp, "rb") as fh:
            os.fsync(fh.fileno())
        os.replace(tmp, OUT)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return len(rows)


if __name__ == "__main__":
    n = export()
    print(f"wrote {OUT.name}: {n} rows")
