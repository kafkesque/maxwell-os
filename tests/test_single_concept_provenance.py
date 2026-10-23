#!/usr/bin/env python3
"""tests/test_single_concept_provenance.py — BUG-977: the single-concept path's ontology is DECLARED, not asserted.

WHY (MEASURED 2026-10-23). pipeline/insert_single_concept.py is the governed path for one (source, concept) pair a
tier-B owner ruling MATCHed but S2 omitted (D-3130). Its first — and only — row (f523504e, "The Kernel of Strategy")
was written with FOUR blank cells the other 7,640/7,640 rows carry: content_type_source, discipline_source,
extraction_type_source and created_at. Three defects in one write, each already named in this register:

  * a ROLE asserted as a code literal (`"content_type": "principle"`) — C12, plus BUG-712's "asserted, never
    computed" shape at a NEW site, and a claim the tool has no warrant to make;
  * a label with no AUTHORSHIP — the BUG-742 class (a provenance value true of a label the row no longer carries,
    inverted: no value at all);
  * a blank time stamp — the shape check_store_columns reads as CONSTANT-OR-BLANK on a declared `value` column
    (it went RED on it, and that RED is this bug's red loop).

THE RULES THESE CONTROLS PIN: the ontology comes from config/pipeline_config.yaml#single_concept through ONE
reader; every value is checked against its CLOSED home; the label's authorship is `deterministic` (a declared rule
authored the role — never `human_verbatim`, because the tier-B ruling sheet carries MATCH/NONE only, i.e. the owner
ruled PRESENCE and not the ROLE); and provenance-completeness is BY CONSTRUCTION, so the next 43 tier-B inserts
cannot inherit the hole. A source-level control is included because no runtime assertion can see a literal that
simply looks correct (the D-2968 precedent).
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import get_args

import pytest
import yaml

from pipeline.insert_single_concept import (
    _ONTOLOGY_KEYS,
    apply_declared_ontology,
    declared_ontology,
)
from pipeline.schemas import PROVENANCE_LITERAL

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8"))
SITE = ROOT / "pipeline" / "insert_single_concept.py"


def _cfg() -> dict:
    """A fresh deep copy: every control may mutate its own copy and never the module-level one."""
    return copy.deepcopy(CFG)


def test_the_declaration_resolves_and_is_complete() -> None:
    """Every key this path stamps is present and non-blank — a declaration that does not resolve declares nothing."""
    ontology = declared_ontology(_cfg())
    assert set(ontology) == set(_ONTOLOGY_KEYS)
    assert all(v.strip() for v in ontology.values()), ontology


def test_the_role_is_admissible_at_the_leaf() -> None:
    """D-2965: the leaf admits a ROLE only. A disposition ('noise_drop'/'quarantine') is not a content_type."""
    from pipeline.content_types import leaf_label_fault

    assert leaf_label_fault(declared_ontology(_cfg())["content_type"]) is None


def test_the_axis_values_are_members_of_their_closed_homes() -> None:
    """No axis may carry a value its own vocabulary does not declare (C12/C16)."""
    from pipeline.content_types import EXTRACTION_TYPES

    ontology = declared_ontology(_cfg())
    provenance = set(get_args(PROVENANCE_LITERAL))
    assert ontology["extraction_type"] in EXTRACTION_TYPES
    for key in ("content_type_source", "extraction_type_source", "discipline_source"):
        assert ontology[key] in provenance, key


def test_the_label_authorship_is_deterministic_never_human_verbatim() -> None:
    """BUG-742, reversed. The tier-B ruling sheet carries MATCH/NONE only (governance/
    EXTRACTION_RECALL_TIER_B_RULINGS_20261023.jsonl): the owner ruled PRESENCE, never the ROLE — so
    `human_verbatim` on this path would be a provenance LIE, and `llm_extracted_from_source` would be false too
    (no LLM emitted the label). A DECLARED RULE authored it, which is exactly `deterministic` (D-2947/D-343).
    """
    ontology = declared_ontology(_cfg())
    assert ontology["content_type_source"] == "deterministic"
    assert ontology["content_type_source"] != "human_verbatim"


def test_a_stamped_record_is_provenance_complete() -> None:
    """The four cells that were blank on the one row this path wrote are all populated BY CONSTRUCTION."""
    fb = apply_declared_ontology({}, declared_ontology(_cfg()), committed_at="2026-10-23T00:00:00+00:00")
    for cell in ("content_type", "content_type_source", "discipline_source", "extraction_type_source"):
        assert str(fb.get(cell) or "").strip(), cell
    assert fb["created_at"] == fb["committed_at"] == "2026-10-23T00:00:00+00:00"


@pytest.mark.parametrize(
    ("label", "mutate"),
    [
        ("an absent block", lambda c: c.pop("single_concept")),
        ("a missing key", lambda c: c["single_concept"].pop("origin")),
        ("a blank value", lambda c: c["single_concept"].__setitem__("depth", "  ")),
        ("a DISPOSITION used as a ROLE", lambda c: c["single_concept"].__setitem__("content_type", "noise_drop")),
        ("an undeclared role", lambda c: c["single_concept"].__setitem__("content_type", "fact")),
        ("an undeclared form", lambda c: c["single_concept"].__setitem__("extraction_type", "made_up")),
        ("an undeclared depth", lambda c: c["single_concept"].__setitem__("depth", "galactic")),
        ("a minted provenance value", lambda c: c["single_concept"].__setitem__("content_type_source", "owner_adjudication")),
    ],
)
def test_every_undeclared_shape_fails_closed(label: str, mutate) -> None:
    """D-3034/C16: the reader refuses rather than defaulting, and names what it refused."""
    cfg = _cfg()
    mutate(cfg)
    with pytest.raises(SystemExit):
        declared_ontology(cfg)


def test_the_write_site_carries_no_ontology_literal() -> None:
    """SOURCE-LEVEL, read as an AST (the D-2968 precedent): no runtime assertion can see a literal that simply looks
    correct, so the control reads the file's own syntax tree. Any DICT literal whose key is an ontology axis and
    whose value is a string constant fails here — the axis must come from the declaration, never from code. The
    tree (not the bytes) is read on purpose: the module's docstring QUOTES the old literals as history, and a
    control that cannot tell history from code would forbid its own receipt.
    """
    import ast

    tree = ast.parse(SITE.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if (isinstance(key, ast.Constant) and key.value in _ONTOLOGY_KEYS
                    and isinstance(value, ast.Constant) and isinstance(value.value, str)):
                offenders.append(f"line {getattr(value, 'lineno', '?')}: {key.value!r} = {value.value!r}")
    assert not offenders, f"an ontology LITERAL reappeared at the write site: {offenders}"


def test_the_declaration_lives_in_config_not_code() -> None:
    """C12: the values that CAN be declared MUST be — the site reads a declaration, it does not hold one."""
    source = SITE.read_text(encoding="utf-8")
    assert "declared_ontology(cfg)" in source
    assert "apply_declared_ontology(" in source
