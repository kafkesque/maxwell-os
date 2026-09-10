#!/usr/bin/env python3
"""scripts/clean_golden_authors.py — D2585 P5 Step 2 (author cleaning).

Removes junk + alias-duplicate author values from the P5 source map so the
freeze script can enforce meaningful book/author-disjointness.

Cleaning rules:
  1. DROP junk authors: "string" (extraction artifact), "Anonymous", "Various",
     "Unknown", empty/whitespace-only.
  2. NORMALIZE degree/title suffixes: strip trailing "Ph. D.", "PhD", "M.D.",
     "Ed.D.", "Jr.", "Sr.", "III", etc. so "Marcel Danesi Ph. D." -> "Marcel
     Danesi" (aliases collapse).
  3. DEDUPE per example (order-preserving).

Read-only. Reads temp/golden_source_map.json, writes
temp/golden_source_map_clean.json and appends a cleaning report section to
governance/golden_source_map.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

_SRC = _ROOT / "temp" / "golden_source_map.json"
_OUT = _ROOT / "temp" / "golden_source_map_clean.json"
_MD = _ROOT / "governance" / "golden_source_map.md"

_JUNK = {"string", "anonymous", "various", "unknown", "n/a", "none", "null"}
_SUFFIX_RE = re.compile(
    r"\s*(?:Ph\.?\s*D\.?|M\.?\s*D\.?|D\.?\s*Phil\.?|Ed\.?\s*D\.?|"
    r"MBA|M\.?\s*Sc\.?|B\.?\s*Sc\.?|Jr\.?|Sr\.?|II{1,3}|IV|V|"
    r"\(auth\.?\)|\(editor\)|\(eds?\.?\))\s*$",
    re.IGNORECASE,
)


def _clean_author(raw: str) -> str | None:
    """Return the normalized author, or None if it is junk."""
    name = raw.strip()
    if not name:
        return None
    if name.lower() in _JUNK:
        return None
    # Strip a single trailing degree/suffix token (repeat for stacked suffixes).
    prev = None
    while prev != name:
        prev = name
        name = _SUFFIX_RE.sub("", name).strip()
    # Collapse internal whitespace, keep original case for display.
    name = re.sub(r"\s+", " ", name)
    return name or None


def main() -> int:
    rows: list[dict] = json.loads(_SRC.read_text(encoding="utf-8"))
    dropped_total = 0
    alias_merges = 0
    for r in rows:
        cleaned: list[str] = []
        seen: set[str] = set()
        for a in r.get("authors", []):
            c = _clean_author(str(a))
            if c is None:
                dropped_total += 1
                continue
            key = c.lower()
            if key in seen:
                alias_merges += 1  # duplicate after normalization
                continue
            seen.add(key)
            cleaned.append(c)
        r["authors"] = cleaned
        r["has_provenance"] = bool(r.get("books") or cleaned)

    _OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")

    n = len(rows)
    w_auth = sum(1 for r in rows if r["authors"])
    n_auth = len({a for r in rows for a in r["authors"]})
    md = _MD.read_text(encoding="utf-8") if _MD.exists() else ""
    md += "\n".join([
        "",
        "## Author cleaning (P5 Step 2)",
        "",
        f"- junk author values dropped: **{dropped_total}**",
        f"- alias duplicates merged: **{alias_merges}**",
        f"- examples with >=1 clean author: **{w_auth}/{n}**",
        f"- distinct clean authors: **{n_auth}**",
        "",
    ])
    _MD.write_text(md, encoding="utf-8")
    print(json.dumps({
        "n_examples": n,
        "junk_dropped": dropped_total,
        "alias_merges": alias_merges,
        "with_clean_author": w_auth,
        "distinct_clean_authors": n_auth,
        "out": str(_OUT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
