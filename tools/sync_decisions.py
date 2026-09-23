#!/usr/bin/env python3
"""RETIRED 2026-09-23 (BUG-402). DO NOT RUN - this tool is INVERTED and refuses.

It declared DECISION-LOG.md the single source of truth and rewrote config/decisions.yaml from it,
which is backwards: the registry carries 736 records while DECISION-LOG.md carries ~154 heading
blocks, so running it overwrites hand-curated descriptions with its "No heading in DECISION-LOG.md"
fallback and re-dumps the whole file (the BUG-409 formatting destruction). It also owned the
last_sync declaration that BUG-402 moved to a derived, checked field.

Replacement:  python3 scripts/recompute_decision_summary.py [--check]
What it never did: membership (registry ids vs log headings). That check is
scripts/check_decision_membership.py.

This file is kept as a tombstone; history is in git log -- tools/sync_decisions.py
"""
import sys

EXIT_REFUSED = 2

if __name__ == "__main__":
    print(
        "REFUSED (BUG-402): tools/sync_decisions.py is RETIRED and INVERTED - running it would "
        "re-dump config/decisions.yaml and destroy hand-curated formatting.",
        file=sys.stderr,
    )
    print("USE INSTEAD: python3 scripts/recompute_decision_summary.py [--check]", file=sys.stderr)
    sys.exit(EXIT_REFUSED)
