"""CI test: domain/discipline canonical disjointness (D2422 / BUG-151).

Guarantees no canonical label is valid in BOTH lists (except the shared
'emerging' catch-all). Prevents the structural ambiguity where a model can
emit e.g. 'education' into either field and pass validation.

Run: python3 -m pytest tests/test_taxonomy_disjointness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES


def test_domain_discipline_disjoint() -> None:
    """Canonical domains and disciplines must not overlap (except 'emerging')."""
    overlap: set[str] = set(CANONICAL_DOMAINS) & set(CANONICAL_DISCIPLINES)
    unexpected: set[str] = overlap - {"emerging"}
    assert unexpected == set(), (
        f"Canonical overlap between domains and disciplines: {sorted(unexpected)}"
    )


def test_education_single_listed() -> None:
    """D2422: 'education' must be canonical in exactly ONE list (was dual-listed)."""
    in_domains: bool = "education" in CANONICAL_DOMAINS
    in_disciplines: bool = "education" in CANONICAL_DISCIPLINES
    assert in_domains != in_disciplines, (
        "'education' must be in exactly one list (BUG-151 dual-listing)"
    )


if __name__ == "__main__":
    test_domain_discipline_disjoint()
    test_education_single_listed()
    print("taxonomy disjointness OK")
