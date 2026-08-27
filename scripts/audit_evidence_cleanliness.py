#!/usr/bin/env python3
"""audit_evidence_cleanliness.py — BUG-181#1 pre-S5 evidence gate (2026-08-27)
==============================================================================
Scans a Stage 2/4 checkpoint JSONL and flags records whose `evidence_passages`
carry EPUB→MD conversion artifacts (CSS fragments, {=html} markers, image
placeholders, chapter anchors). These passages are NOT verbatim source text, so
S5 DeBERTa NLI would verify against garbage — the BUG-181#1 contamination class.

Usage:
    python3 scripts/audit_evidence_cleanliness.py \
        "knowledge pipeline/stage2_extract/t11/singleton_fbs.jsonl" [--limit 20] [--json]

Exit code 0 = clean, 1 = contaminated records found (CI-able).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# D2465/BUG-181#1: artifact patterns observed in the 5,254-record singleton audit.
# Kept in code (script-level constants) — C12 applies to pipeline config, this is
# a standalone audit tool with no pipeline coupling.
ARTIFACT_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("css-selector", re.compile(r"\.title-page|\.html_blurbs|#part\d|\.browsable-container|\.intended-text|\.listing-")),
    ("calibre-markers", re.compile(r"\.calibre\d|::::\s*:::|:::\s*::::")),
    ("html-inline-marker", re.compile(r"\{=html\}|\[ \]\{bgcolor|\{align=|width=\"\d+\"|height=\"\d+\"")),
    ("image-placeholder", re.compile(r"inline-image|image-container")),
    ("chapter-anchor", re.compile(r":::::?\s*\{#chapter|\.xhtml_p\d")),
    ("html-entity", re.compile(r"&#\d+;")),
    ("style-css", re.compile(r"margin-|padding-|font-|px;")),
)


def artifact_ratio(text: str) -> float:
    """Fraction of artifact-y characters in a passage (0.0 = clean)."""
    if not text:
        return 0.0
    n = len(text)
    hits = 0
    for _name, pat in ARTIFACT_PATTERNS:
        hits += sum(len(m.group(0)) for m in pat.finditer(text))
    return min(hits / max(n, 1), 1.0)


def classify_passage(text: str) -> tuple[list[str], float]:
    """Return (matched pattern names, artifact ratio) for one passage."""
    matched = [name for name, pat in ARTIFACT_PATTERNS if pat.search(text)]
    return matched, artifact_ratio(text)


def audit(path: str, limit: int, as_json: bool) -> int:
    src = Path(path)
    if not src.exists():
        print(f"❌ {src} not found", file=sys.stderr)
        return 2

    total = 0
    contaminated = 0
    severe = 0
    samples: list[dict] = []

    with open(src, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            eps = rec.get("evidence_passages") or []
            if not eps:
                continue
            for ep in eps:
                matched, ratio = classify_passage(ep)
                if matched:
                    contaminated += 1
                    if ratio > 0.15:
                        severe += 1
                    if len(samples) < limit:
                        samples.append({
                            "fb_id": rec.get("fb_id", "?"),
                            "name": str(rec.get("name", ""))[:60],
                            "content_type": rec.get("content_type", "?"),
                            "patterns": matched,
                            "artifact_ratio": round(ratio, 3),
                            "evidence_head": ep[:180],
                        })
                    break  # one flag per record

    pct = (contaminated / total * 100.0) if total else 0.0
    if as_json:
        print(json.dumps({
            "total_records": total,
            "contaminated": contaminated,
            "contaminated_pct": round(pct, 2),
            "severe": severe,
            "samples": samples,
        }, indent=2, ensure_ascii=False))
    else:
        print(f"Records scanned : {total}")
        print(f"Contaminated   : {contaminated} ({pct:.1f}%)")
        print(f"Severe (>15% artifacts): {severe}")
        for s in samples:
            print(f"  [{s['content_type']}] {s['name']!r} ratio={s['artifact_ratio']} "
                  f"patterns={s['patterns']}")
            print(f"      {s['evidence_head']!r}")

    return 0 if contaminated == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="BUG-181#1 evidence-cleanliness audit")
    parser.add_argument("path", help="checkpoint JSONL to scan")
    parser.add_argument("--limit", type=int, default=20, help="max sample records to print")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()
    return audit(args.path, args.limit, args.json)


if __name__ == "__main__":
    sys.exit(main())
