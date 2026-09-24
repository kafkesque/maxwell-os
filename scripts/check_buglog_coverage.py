#!/usr/bin/env python3
r"""Fail closed if a buglog heading names a bug that the status parser cannot see (BUG-428).

WHY: on 2026-09-24 the parser matched `^##\s+BUG-<id>` only, so BUG-426 (HIGH, OPEN) and BUG-427 sat in the
file, in the register's own directory, invisible to the register - and were therefore missing from the C15
count and from every handoff. The guard class that fails this way is worse than no guard.

This script reuses `HEADER_RE` from bug_status.py instead of re-typing it, so the two can never diverge.
Exit 1 naming every unparsed heading.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bug_status import BUGLOG, HEADER_RE  # noqa: E402  (single source of truth for the pattern)

HEADING_RE = re.compile(r"^#{1,6}\s+.*?BUG-\d+")
# A heading that ANNOTATES a bug is not a status event and must not be forced into one (an over-strict guard
# gets disabled, which is worse than no guard): CORRECTIONS/RECEIPTS/REFINEMENTS are append-only apparatus.
ANNOTATION_RE = re.compile(r"^#{1,6}\s+(CORRECTION|RECEIPT|REFINEMENT|VERIFICATION|NOTE|APPENDIX|ERRATUM)\b")


def main() -> int:
    """Report any heading that names a bug id but is not a recognised status event."""
    unparsed: list[tuple[int, str]] = []
    for n, line in enumerate(BUGLOG.read_text(encoding="utf-8").splitlines(), start=1):
        if HEADING_RE.match(line) and not HEADER_RE.match(line) and not ANNOTATION_RE.match(line):
            unparsed.append((n, line.strip()[:110]))
    if unparsed:
        print(f"FAIL buglog coverage: {len(unparsed)} heading(s) name a bug but are not parsed:")
        for n, line in unparsed:
            print(f"  line {n}: {line}")
        return 1
    print(f"ok buglog coverage: every heading naming a bug id is parsed ({BUGLOG.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
