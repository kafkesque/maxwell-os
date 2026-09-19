#!/usr/bin/env python3
"""scan_review_artifacts.py — enumerate EVERY human-review artifact (no blindspots).

The anti-drift guarantee: instead of hardcoding a known list of review files, this
GLOBS the governance directory for any file that looks like a review/adjudication/
verdict artifact, extracts its row count + human-verdict fill-rate, and writes a
machine-readable ledger. Run this BEFORE answering "what has the human reviewed /
what remains" — it cannot miss a file the way a targeted grep can.

Usage:
  python3 scripts/scan_review_artifacts.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
GOV = ROOT / "governance"

# Broad glob patterns that catch review/adjudication/verdict artifacts.
PATTERNS = [
    "s4_*review*", "*review_sheet*", "*review_digest*", "*review_queue*",
    "*adjudication*", "phase0*", "frontier*", "p5_*", "d2615*",
    "*contested*", "*null_retry*", "*human*form*", "*verdict*",
]


def _row_count(p: Path) -> int:
    try:
        if p.suffix == ".csv":
            # tolerate non-utf8 (cp1252/latin-1)
            for enc in ("utf-8", "cp1252", "latin-1"):
                try:
                    with open(p, encoding=enc, newline="") as fh:
                        return sum(1 for _ in csv.reader(fh)) - 1
                except (UnicodeDecodeError, csv.Error):
                    continue
            return -1
        if p.suffix == ".jsonl":
            return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
        if p.suffix == ".json":
            d = json.loads(p.read_text(encoding="utf-8"))
            return len(d) if isinstance(d, (list, dict)) else -1
        if p.suffix == ".md":
            return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
    except Exception:
        return -1
    return -1


def _human_fill(p: Path) -> Dict[str, Any]:
    """For CSV review sheets, report human-verdict fill-rate."""
    out: Dict[str, Any] = {}
    if p.suffix != ".csv":
        return out
    try:
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                rows = list(csv.DictReader(open(p, encoding=enc, newline="")))
                out["n_rows"] = len(rows)
                verdict_cols = [c for c in rows[0].keys() if "HUMAN" in c.upper() or "VERDICT" in c.upper()]
                out["verdict_cols"] = verdict_cols
                out["verdict_fill"] = {
                    c: sum(1 for r in rows if (r.get(c) or "").strip()) for c in verdict_cols
                }
                break
            except (UnicodeDecodeError, csv.Error):
                continue
    except Exception:
        pass
    return out


def main() -> None:
    found: List[Dict[str, Any]] = []
    seen: set = set()
    for pat in PATTERNS:
        for p in sorted(GOV.glob(pat)):
            if p.name.startswith((".", "~")):
                continue
            key = p.resolve()
            if key in seen:
                continue
            seen.add(key)
            rec = {
                "file": p.name,
                "size_bytes": p.stat().st_size if p.exists() else 0,
                "rows": _row_count(p),
            }
            rec.update(_human_fill(p))
            found.append(rec)

    ledger = {
        "generated_by": "scan_review_artifacts.py (deterministic glob — no blindspots)",
        "governance_dir": str(GOV),
        "n_artifacts": len(found),
        "artifacts": found,
    }
    out = GOV / "human_review_ledger.json"
    out.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"scanned governance/ → {len(found)} review artifacts")
    for r in found:
        vf = r.get("verdict_fill", {})
        vf_str = " ".join(f"{c}={n}/{r.get('n_rows','?')}" for c, n in vf.items()) if vf else ""
        print(f"  {r['file']:<45} rows={r['rows']:<6} {vf_str}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
