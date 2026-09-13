#!/usr/bin/env python3
"""normalize_provenance.py — D2618 P0.2: normalize non-canonical p5:* provenance.

Fixes the non-canonical provenance strings that made human-verified counts
non-deterministic (Claude's "20 vs 21" discrepancy):

  p5:claud+human  -> p5:claude+human
  p5:claude+guman -> p5:claude+human   (guman = typo for human)
  p5:claude+juman -> p5:claude+human   (juman = typo for human)

Targets the upstream source governance/golden_synced_4axis.jsonl (the 3 typo
rows are NOT in the 443-core, so verified_core.jsonl is already clean). Also
re-normalizes (defensively) the tier files emitted by build_4axis_tiers.py.

Deterministic, LLM-free, idempotent. C13 backup + C6 atomic write + R14 manifest.

Usage:
  python3 scripts/normalize_provenance.py            # dry-run: report, write nothing
  python3 scripts/normalize_provenance.py --apply    # backup + normalize
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_SYNCED = ROOT / "governance" / "golden_synced_4axis.jsonl"
TIER_FILES = [
    ROOT / "governance" / "gold_4axis.jsonl",
    ROOT / "governance" / "pending_4axis.jsonl",
    ROOT / "governance" / "silver_4axis.jsonl",
]
MANIFEST = ROOT / "governance" / "provenance_normalization_manifest.json"

PROVENANCE_TYPOS: Dict[str, str] = {
    "p5:claud+human": "p5:claude+human",
    "p5:claude+guman": "p5:claude+human",
    "p5:claude+juman": "p5:claude+human",
}
AXES = ("content_type_source", "depth_source", "discipline_source", "domains_source")

SCHEMA_VERSION = "3.0"
GEN_MODEL = "normalize_provenance.py (deterministic; no generation)"
PIPELINE_COMMIT = "v3.0-D2618-p0"


def _normalize(row: Dict[str, Any]) -> int:
    """Normalize a row's provenance axes in place; return number of cells changed."""
    changed = 0
    for ax in AXES:
        v = row.get(ax)
        if isinstance(v, str) and v in PROVENANCE_TYPOS:
            row[ax] = PROVENANCE_TYPOS[v]
            changed += 1
    return changed


def _load(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def _atomic_write(path: Path, rows: List[Dict[str, Any]]) -> None:
    content = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    d = path.parent
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".jsonl")
    import os
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize non-canonical p5:* provenance (D2618 P0.2).")
    ap.add_argument("--apply", action="store_true", help="backup + normalize (default: dry-run)")
    args = ap.parse_args()

    report: Dict[str, Any] = {}
    total_changed = 0
    for path in [GOLDEN_SYNCED] + TIER_FILES:
        if not path.exists():
            continue
        rows = _load(path)
        n_changed = sum(_normalize(r) for r in rows)
        total_changed += n_changed
        report[str(path.relative_to(ROOT))] = n_changed
        print(f"{path.relative_to(ROOT)}: {n_changed} cells changed")

    print(f"TOTAL cells to normalize: {total_changed}")

    if not args.apply:
        print("[dry-run] nothing written. use --apply.")
        return

    # C13 backup of golden_synced (the upstream source).
    if GOLDEN_SYNCED.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(GOLDEN_SYNCED, GOLDEN_SYNCED.with_name(f"golden_synced_4axis.jsonl.bak_{ts}"))

    for path in [GOLDEN_SYNCED] + TIER_FILES:
        if not path.exists():
            continue
        rows = _load(path)
        _normalize_rows = sum(_normalize(r) for r in rows)
        if _normalize_rows:
            _atomic_write(path, rows)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canonicalization_map": PROVENANCE_TYPOS,
        "cells_changed": report,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest written: {MANIFEST}")


if __name__ == "__main__":
    main()
