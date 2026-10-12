#!/usr/bin/env python3
"""tests/test_content_type_authorship.py - D-2968/BUG-712: the label and its AUTHORSHIP share one computation.

WHY. D-2938 made S4 persist the ROUTER's resolved content_type instead of the raw S2 label, but the write
site kept stamping llm_extracted_from_source on EVERY row. The next S2->S6 run would therefore write ~100
labels the DETERMINISTIC router authored (D-343/D-2747) while claiming an LLM authored them - the BUG-742
class (a provenance value TRUE of the label the row no longer carries) and the SAME defect shape D-2938
itself fixed: a computed fact, discarded at the write site. These controls pin the rule, the closed
vocabulary it chooses from, and the removal of the literal at the site itself.
"""
from __future__ import annotations

from pathlib import Path
from typing import get_args

import pipeline.stage4_merge as s4
from pipeline.schemas import PROVENANCE_LITERAL

ROOT = Path(s4.__file__).resolve().parent.parent


def test_a_router_authored_label_is_stamped_deterministic() -> None:
    assert s4.content_type_source("growth_edge", "principle", True) == "deterministic"


def test_a_surviving_s2_label_keeps_the_llm_stamp() -> None:
    """The router AGREED with S2, so the LLM did author the persisted value: behaviour is unchanged there."""
    assert s4.content_type_source("principle", "principle", True) == "llm_extracted_from_source"
    assert s4.content_type_source("principle", " principle ", True) == "llm_extracted_from_source"


def test_the_legacy_persist_path_keeps_the_llm_stamp() -> None:
    """With the persist flag OFF the RAW label is written, so a deterministic stamp would be the lie."""
    assert s4.content_type_source("growth_edge", "principle", False) == "llm_extracted_from_source"


def test_every_returned_value_is_a_member_of_the_closed_vocabulary() -> None:
    """The function CHOOSES between declared values; it never mints one (C29, a closed Pydantic Literal)."""
    members = set(get_args(PROVENANCE_LITERAL))
    for resolved, raw, persist in (("growth_edge", "principle", True), ("principle", "principle", True),
                                   ("growth_edge", "principle", False), ("quarantine", "principle", True)):
        assert s4.content_type_source(resolved, raw, persist) in members


def test_the_write_site_derives_the_stamp_instead_of_literalising_it() -> None:
    """A source-level control (no runtime assertion can see a literal that looks correct): re-hardcoding
    llm_extracted_from_source at this site would silently reintroduce the provenance lie for every routed row."""
    body = (ROOT / "pipeline/stage4_merge.py").read_text(encoding="utf-8")
    assert '"content_type_source": content_type_source(' in body
    assert '"content_type_source": "llm_extracted_from_source"' not in body
