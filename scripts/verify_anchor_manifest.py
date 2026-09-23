#!/usr/bin/env python3
"""scripts/verify_anchor_manifest.py - the frozen anchor is only citable if its BYTES still match.

ANCHOR-3 is the reference every arm comparison cites. A citation is worthless if the artifact can be
regenerated silently (a re-run of the consolidator, a review-sheet edit, an alias change). This check
re-derives sha256/bytes/rows/columns from the artifact on disk and compares them with the values the
manifest froze; any drift is RED and exits 1, so ``just health`` fails loudly (C16).

The manifest path is read from ``config/f11_llm_coder.yaml`` (consolidation.anchor_manifest) - no path
is hardcoded here (C12).
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = PROJECT_ROOT / "config/f11_llm_coder.yaml"


def main() -> int:
    """Verify the frozen anchor manifest against the artifact on disk."""
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    rel = (cfg.get("consolidation") or {}).get("anchor_manifest")
    if not rel:
        print("RED  consolidation.anchor_manifest is not declared in config/f11_llm_coder.yaml (C12)")
        return 1
    mpath = PROJECT_ROOT / rel
    if not mpath.exists():
        print(f"RED  manifest missing: {rel}")
        return 1
    man = json.loads(mpath.read_text(encoding="utf-8"))
    art = PROJECT_ROOT / man["path"]
    if not art.exists():
        print(f"RED  frozen artifact missing: {man['path']}")
        return 1
    raw = art.read_bytes()
    with art.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    actual = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
              "rows": len(rows) - 1, "columns": len(rows[0])}
    bad = [f"{k}: frozen {man[k]!r} != on-disk {v!r}" for k, v in actual.items() if man.get(k) != v]
    if bad:
        print(f"RED  {man['artifact_id']} has DRIFTED from its frozen manifest ({rel}):")
        for b in bad:
            print(f"       {b}")
        print("     The anchor is the reference for every arm ranking; re-freeze deliberately "
              "(new manifest + a recorded decision), never silently.")
        return 1
    print(f"  ok   {man['artifact_id']} frozen and byte-identical "
          f"({actual['rows']} rows x {actual['columns']} cols, {actual['bytes']} bytes, "
          f"sha256 {actual['sha256'][:16]}..., tier {man['artifact_provenance_tier']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
