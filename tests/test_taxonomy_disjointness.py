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

from pipeline.schemas import (
    CANONICAL_DOMAINS,
    CANONICAL_DISCIPLINES,
    get_synonym_index,
    match_to_canonical,
)


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


def test_synonym_index_kind_safe() -> None:
    """BUG-200: a canonical of one kind must not leak as a synonym KEY into the
    other kind's index (D2133 `_accept` checked the TARGET, not the SOURCE alias).
    This is what caused match_to_canonical() to silently coerce 'typography' →
    'graphic design' (domain) and 'software engineering' → 'engineering practice'."""
    dom_canon = {c.lower() for c in CANONICAL_DOMAINS} - {"emerging"}
    disc_canon = {c.lower() for c in CANONICAL_DISCIPLINES} - {"emerging"}

    dom_leak = [k for k in get_synonym_index("domain") if k in disc_canon and k not in dom_canon]
    disc_leak = [k for k in get_synonym_index("discipline") if k in dom_canon and k not in disc_canon]

    assert not dom_leak, f"discipline canonicals leaked into domain index: {sorted(dom_leak)}"
    assert not disc_leak, f"domain canonicals leaked into discipline index: {sorted(disc_leak)}"


def test_match_to_canonical_no_cross_kind_coercion() -> None:
    """BUG-200: match_to_canonical must return None (→ 'emerging') when asked to
    resolve a canonical of the OPPOSITE axis, never a coerced cross-kind label."""
    for disc in CANONICAL_DISCIPLINES:
        if disc.lower() == "emerging":
            continue
        assert match_to_canonical(disc, "domain") is None, (
            f"discipline canonical {disc!r} coerced into a domain"
        )
    for dom in CANONICAL_DOMAINS:
        if dom.lower() == "emerging":
            continue
        assert match_to_canonical(dom, "discipline") is None, (
            f"domain canonical {dom!r} coerced into a discipline"
        )


if __name__ == "__main__":
    test_domain_discipline_disjoint()
    test_education_single_listed()
    test_synonym_index_kind_safe()
    test_match_to_canonical_no_cross_kind_coercion()
    print("taxonomy disjointness OK")
