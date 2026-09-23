#!/usr/bin/env python3
"""scripts/r3_preflight.py - an arm comparison may only run against a VERIFIED reference (D-337/C-3).

R3 ranks arms against a held-out truth source. Two things can silently invalidate the ranking: the cited
authority (ANCHOR-3) drifting, or the source's pre-registered n quietly differing from the measurable n
(BUG-334). This preflight refuses to start a comparison unless both hold, and prints the citation block the
resulting report must carry. Nothing is hardcoded (C12): the source, its columns and its allowlist all come
from config/eval_integrity.yaml.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = PROJECT_ROOT / "config/eval_integrity.yaml"


def main() -> int:
    """Verify the anchor authority, the truth source and the pre-registered n. Exit 1 on any mismatch."""
    import yaml

    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    bake = cfg.get("bakeoff") or {}
    ref = bake.get("anchor_ref") or {}
    red: list[str] = []

    # 1. the cited authority must be byte-identical to its frozen manifest
    if not ref.get("manifest"):
        red.append("bakeoff.anchor_ref.manifest is not declared (C12)")
    else:
        rc = subprocess.run([sys.executable, "scripts/verify_anchor_manifest.py"],
                            cwd=PROJECT_ROOT, capture_output=True, text=True)
        if rc.returncode != 0:
            red.append("ANCHOR-3 verification failed:\n" + rc.stdout.strip())

    # 2. the truth source, its columns and its pre-registered n
    name = bake.get("arbitration", {}).get("source")
    src = (bake.get("sources") or {}).get(name)
    if not src:
        red.append(f"bakeoff.sources.{name} is not declared")
        src = {}
    sheet_rel = src.get("sheet")
    sheet = PROJECT_ROOT / str(sheet_rel)
    header: list[str] = []
    if sheet_rel and sheet.exists():
        with sheet.open(newline="", encoding="utf-8") as fh:
            header = next(csv.reader(fh))
    elif sheet_rel:
        red.append(f"source sheet missing: {sheet_rel}")
    for axis, col in (src.get("verdict_columns") or {}).items():
        if col not in header:
            red.append(f"verdict column {col!r} (axis {axis}) is not a column of {sheet_rel}")
    n_rows = 0
    al = src.get("row_allowlist_file")
    field = src.get("row_allowlist_field")
    if al and field:
        doc = json.loads((PROJECT_ROOT / al).read_text(encoding="utf-8"))
        n_rows = len(doc.get(field) or [])
        pre = src.get("pre_registered_n")
        if pre is not None and n_rows != pre:
            red.append(f"pre-registered n={pre} but the allowlist {field} carries {n_rows} rows (BUG-334)")

    print(f"R3 preflight - source {name!r}, authority {ref.get('artifact_id')!r}")
    print(f"  reference   : {sheet_rel} ({n_rows} held-out rows, pre-registered {src.get('pre_registered_n')})")
    print(f"  authority   : {ref.get('manifest')} | tier {ref.get('tier')}")
    print(f"  bound       : {ref.get('bound')}")
    print(f"  cite in the report: authority {ref.get('artifact_id')} + source {name!r}; "
          f"RELATIVE ranking only, never an absolute error floor")
    for r in red:
        print(f"  RED  {r}")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
