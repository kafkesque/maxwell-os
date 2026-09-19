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
    _axis_contract,
    CANONICAL_DISCIPLINES,
    get_synonym_index,
    match_to_canonical,
    validate_discipline_domain,
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


def test_validate_discipline_domain_guard() -> None:
    """D2620 — the always-on non-contamination guard must flag any cross-axis
    emission (domain-as-discipline OR discipline-as-domain) and stay silent on
    correct assignments. Locks the two confirmed rulings:
      - psychology / design psychology  → discipline-only
      - marketing & communications       → domain-only
    """
    # Disputed labels are canonically placed exactly once.
    assert "psychology" in CANONICAL_DISCIPLINES and "psychology" not in CANONICAL_DOMAINS
    assert "design psychology" in CANONICAL_DISCIPLINES and "design psychology" not in CANONICAL_DOMAINS
    assert (
        "marketing & communications" in CANONICAL_DOMAINS
        and "marketing & communications" not in CANONICAL_DISCIPLINES
    )

    # Contamination cases → non-empty flags (fail-closed).
    assert validate_discipline_domain("marketing & communications", None) == [
        "domain-as-discipline: 'marketing & communications'"
    ]
    assert validate_discipline_domain(None, ["psychology"]) == [
        "discipline-as-domain: 'psychology'"
    ]
    assert validate_discipline_domain("psychology", ["user experience"]) == []

    # Correct cross-axis pairing (discipline + genuine domains) stays clean.
    assert validate_discipline_domain("cultural design", ["marketing & communications"]) == []
    assert validate_discipline_domain("design psychology", ["digital product"]) == []


def test_vocabularies_disjoint_under_normalisation() -> None:
    """The disjointness claim must hold NORMALISED, not just by exact string (2026-09-17).

    The exact-string test above was satisfied while `research methodology` (a canonical
    DISCIPLINE) and `research & methodology` (a canonical DOMAIN) coexisted on 909 live rows —
    the same concept differing only in punctuation. Every normalised collision must now be
    DECLARED in `config/eval_integrity.yaml::label_axes`, and undeclared ones are hard errors.
    """
    import re

    contract = _axis_contract()
    shared = {re.sub(r"[^a-z0-9]", "", x.lower()) for x in (contract.get("shared_labels") or [])}
    declared = {
        (re.sub(r"[^a-z0-9]", "", str(c.get("discipline", "")).lower()),
         re.sub(r"[^a-z0-9]", "", str(c.get("domain", "")).lower()))
        for c in (contract.get("known_collisions") or [])
    }
    assert contract, "label_axes contract could not be read — the guard would fail open"

    def norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower())

    dom_norm = {norm(d) for d in CANONICAL_DOMAINS}
    undeclared = [
        d for d in CANONICAL_DISCIPLINES
        if norm(d) in dom_norm and norm(d) not in shared
        and not any(norm(d) == a and norm(d) == b for a, b in declared)
    ]
    assert undeclared == [], (
        "Canonical label(s) valid on BOTH axes and NOT declared in label_axes: "
        + str(sorted(undeclared))
    )


def test_guard_detects_punctuation_hidden_collision() -> None:
    """The runtime guard must catch a collision that differs only by punctuation."""
    flags = validate_discipline_domain("research methodology", ["research & methodology"])
    assert flags, "guard returned clean for a live cross-axis collision"
    # 2026-09-19: a DECLARED collision now carries a "DECLARED: " prefix and the ruling text read
    # from config, so a caller can tell a decided question from an open defect (D271a). The guard
    # still returns a non-empty list, so every fail-closed call site keeps failing closed.
    assert all(f.startswith("DECLARED: declared-axis-collision") for f in flags), flags


if __name__ == "__main__":
    test_domain_discipline_disjoint()
    test_education_single_listed()
    test_synonym_index_kind_safe()
    test_match_to_canonical_no_cross_kind_coercion()
    test_validate_discipline_domain_guard()
    test_vocabularies_disjoint_under_normalisation()
    test_guard_detects_punctuation_hidden_collision()
    print("taxonomy disjointness OK")
