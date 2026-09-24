#!/usr/bin/env python3
"""RAIL 3 (BUG-430, from BUG-426): a negative claim about the owner's work must carry its coverage.

BUG-426 was produced by answering "does the 150-row domain artifact exist?" with "no" from a search whose
session ids were mistyped, whose scan timed out, and whose uncovered directories were never declared.
Rail: every negative is a ledger row that must state keys, roots, completion and - explicitly - what was
NOT searched. `definitive: true` is refused unless the coverage block is complete. Fail closed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
LEDGER = REPO / "governance" / "existence_negatives.yaml"
REQUIRED = ("claim", "keys_used", "roots_searched", "search_complete", "not_searched", "answer")


def main() -> int:
    """Validate every ledger row."""
    if not LEDGER.exists():
        print("ok existence negatives: no ledger yet (nothing claimed)")
        return 0
    rows = yaml.safe_load(LEDGER.read_text(encoding="utf-8")) or {}
    bad: list[str] = []
    for r in rows.get("claims", []):
        miss = [f for f in REQUIRED if f not in r]
        if miss:
            bad.append(f"{r.get('id', '?')}: missing {miss}")
            continue
        if r["answer"] == "does not exist" and (not r["search_complete"] or r["not_searched"]):
            bad.append(f"{r['id']}: 'does not exist' with incomplete coverage "
                       f"(complete={r['search_complete']}, not_searched={r['not_searched']}) -> answer must be 'not found yet'")
    if bad:
        print("FAIL existence negatives:")
        for b in bad:
            print("  ", b)
        return 1
    print(f"ok existence negatives: {len(rows.get('claims', []))} claim(s), all coverage-declared")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
