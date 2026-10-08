#!/usr/bin/env python3
"""build_domain_ruler.py — RETIRED as a writer (D-2879). It refuses to write. Use the ONE derivation.

WHY (BUG-682, the anti-REVERT limb). Until 2026-10-08 this script materialized
governance/DOMAIN_RULER_FROZEN_20261008.json from governance/ANCHOR_208_CONSOLIDATED_20261007.json -
a face that had NOT received the owner's round-2/round-3 rulings. So the artifact had TWO writers with
TWO different derivations: scripts/apply_owner_domain_review.py (the pinned owner-sheet derivation, which
carries every owner ruling) and this script (a copy of the stale consolidated face). Nothing asserted they
agreed, so a re-run of THIS script would have SILENTLY REVERTED the owner's rulings - the D-387 class
("a normalize re-run must never revert an owner ruling"), one level up: a re-derivation that reverts the
OWNER's own words.

THE RULE NOW: the ruler has ONE derivation and ONE writer -
    config/owner_domain_rulings_20261008.yaml + the pinned owner sheets
      -> scripts/apply_owner_domain_review.py --apply -> governance/DOMAIN_RULER_FROZEN_20261008.json
      -> scripts/apply_owner_domain_review.py --check  (re-derivation proof) / --check-faces (cross-face)

This module is kept (rather than deleted) so that any older reference resolves to an EXPLANATION instead of
a silent revert, and it exits non-zero so an automated re-run fails loudly (C16: no silent errors).
Also note the cross-check that caught it: --check-faces reports the divergence between the ruler and the
face the pipeline reads, with a SHRINK-ONLY ceiling (BUG-682).
"""
from __future__ import annotations

import sys


def main() -> int:
    """Refuse to write: name the single derivation and the rail that proves it."""
    print("REFUSED: build_domain_ruler.py is RETIRED as a writer (D-2879/BUG-682).")
    print("  It derived the ruler from the CONSOLIDATED face, which does NOT carry the owner's")
    print("  round-2/round-3 rulings - a re-run would silently revert them (D-387 class).")
    print("  The ONE derivation is: python3 scripts/apply_owner_domain_review.py --apply")
    print("  Proof/no-drift:        python3 scripts/apply_owner_domain_review.py --check")
    print("  Cross-face divergence: python3 scripts/apply_owner_domain_review.py --check-faces")
    return 1


if __name__ == "__main__":
    sys.exit(main())
