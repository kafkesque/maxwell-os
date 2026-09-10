#!/usr/bin/env python3
"""audit_false_convergence.py — P2: detect same-author echoes in the golden set.

The convergent bar requires >=2 DISTINCT sources. `source_diversity` was already
fixed to count distinct source_ids (not filenames), but that still treats two
editions/files of the SAME author's work as "diverse". This script detects FBs
where source_diversity >= 2 but the distinct-author count is < 2 (same-author
echo / citation echo) — the failure mode the convergent few-shot is explicitly
meant to reject (citation_echo_detection / same_author_echo_negative).

Deterministic, LLM-free, read-only. Emits a flag list; does NOT re-tier (that
is a human decision — re-tier to single-source vs exclude vs in-place fix).

Usage:
    python3 scripts/audit_false_convergence.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT = ROOT / "knowledge pipeline" / "parquet" / "fbs_export_20260902_final.jsonl"
GOLDEN_LABELS = ROOT / "temp" / "golden_labels_probabilistic.jsonl"
OUT = ROOT / "governance" / "false_convergence_echoes.json"


def distinct_authors(authors_raw) -> set[str]:
    """Extract distinct author strings (handles list-of-dicts or list-of-str)."""
    out: set[str] = set()
    if not authors_raw:
        return out
    try:
        data = json.loads(authors_raw) if isinstance(authors_raw, str) else authors_raw
    except json.JSONDecodeError:
        return out
    if isinstance(data, list):
        for x in data:
            if isinstance(x, dict):
                a = (x.get("author") or "").strip()
                if a:
                    out.add(a)
            elif isinstance(x, str) and x.strip():
                out.add(x.strip())
    return out


def main() -> int:
    # golden example_id -> fb_id
    fbids: set[str] = set()
    if GOLDEN_LABELS.exists():
        with GOLDEN_LABELS.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                o = json.loads(line)
                if o.get("fb_id"):
                    fbids.add(o["fb_id"])

    echoes: list[dict] = []
    scanned = 0
    with EXPORT.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            if fbids and o.get("fb_id") not in fbids:
                continue
            scanned += 1
            sd = o.get("source_diversity")
            if not isinstance(sd, int) or sd < 2:
                continue
            authors = distinct_authors(o.get("source_authors"))
            if len(authors) < 2:
                echoes.append({
                    "fb_id": o.get("fb_id"),
                    "name": o.get("name"),
                    "source_diversity": sd,
                    "distinct_authors": len(authors),
                    "authors": sorted(authors),
                    "source_books": o.get("source_books", []),
                })

    echoes.sort(key=lambda e: -e["source_diversity"])
    OUT.write_text(json.dumps({
        "note": "same-author echoes: source_diversity>=2 but <2 distinct authors (false convergence)",
        "total_scanned": scanned,
        "echo_count": len(echoes),
        "echoes": echoes,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"scanned {scanned} golden FBs | same-author echoes: {len(echoes)}")
    print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
