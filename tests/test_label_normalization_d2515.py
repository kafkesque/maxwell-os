#!/usr/bin/env python3
"""D2515 — Label normalization guards (NFKC dash-fold + compound decomposition).

Locks three fixes introduced for the Drift G / fragmentation / alias work:

  1. NFKC + dash-fold: unicode dash variants ("human‑computer interaction" U+2011,
     "human–computer interaction" U+2013) collapse to ASCII "human-computer
     interaction" and resolve to the canonical discipline.
  2. Compound decomposition: "marketing & advertising" resolves to its constituent
     canonicals instead of "emerging" — so it never accumulates as a fragmented
     D2399 challenger.
  3. Long-tail suppression: a compound whose parts all resolve is NOT a long-tail
     challenger (so `update_counts_from_fbs` never proposes promoting it).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.schemas import (
    match_domains_to_canonical,
    match_to_canonical,
    normalize_label,
    split_compound,
)
from pipeline.taxonomy_manager import _is_long_tail, _load_canonical_set
from pipeline.schemas import get_synonym_index


def test_normalize_label_collapses_dash_variants() -> None:
    """Drift G: NFKC + dash-fold collapses every hyphen-like dash to U+002D."""
    assert normalize_label("human\u2011computer interaction") == "human-computer interaction"
    assert normalize_label("human\u2013computer interaction") == "human-computer interaction"
    assert normalize_label("human\u2014computer interaction") == "human-computer interaction"
    assert normalize_label("e\u2011commerce") == "e-commerce"


def test_dash_variant_resolves_to_canonical_discipline() -> None:
    """Drift G: a dash-variant raw label resolves to the canonical discipline."""
    assert match_to_canonical("human\u2011computer interaction", "discipline") == "human-computer interaction"
    assert match_to_canonical("human\u2013computer interaction", "discipline") == "human-computer interaction"


def test_compound_domain_decomposes() -> None:
    """D2515: compound domain labels decompose into constituent canonicals."""
    assert set(match_domains_to_canonical(["marketing & advertising"])) == {
        "marketing & communications", "editorial & advertising",
    }
    assert set(match_domains_to_canonical(["advertising & branding"])) == {
        "editorial & advertising", "brand identity",
    }
    # A canonical compound must NOT be decomposed (direct match wins).
    assert match_domains_to_canonical(["editorial & advertising"]) == ["editorial & advertising"]


def test_split_compound_and_variants() -> None:
    """D2515: split on & and the word 'and'."""
    assert split_compound("marketing & advertising") == ["marketing", "advertising"]
    assert split_compound("marketing and advertising") == ["marketing", "advertising"]
    assert split_compound("marketing") == ["marketing"]


def test_compound_is_not_long_tail() -> None:
    """D2515: a compound whose parts all resolve is NOT a long-tail challenger."""
    canon = _load_canonical_set("domain")
    syn = get_synonym_index("domain")
    assert _is_long_tail("marketing & advertising", canon, syn) is False
    # a genuinely novel compound (no part resolves) stays long-tail
    assert _is_long_tail("zzz & yyy", canon, syn) is True


if __name__ == "__main__":
    test_normalize_label_collapses_dash_variants()
    test_dash_variant_resolves_to_canonical_discipline()
    test_compound_domain_decomposes()
    test_split_compound_and_variants()
    test_compound_is_not_long_tail()
    print("✅ D2515 label-normalization guards passed")
