"""CI test: single-source balanced golden (BUG-152).

The single-source/singleton S2 path must receive a role-balanced few-shot spanning
all 5 content_type roles (principle, process_template, tool_instruction,
process_instance, growth_edge) plus hard negatives. Before BUG-152, single-source
got ZERO few-shot and inherited the convergent 100%-principle bias (re-labelling
methods/tools/speculation as `principle`, and over-firing on pure facts).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage2_extract import (
    format_golden_fewshot_single_source,
    load_golden_single_source,
)
from pipeline.pipeline_paths import (
    S2_GOLDEN_SINGLE_SOURCE_MAX,
    S2_GOLDEN_SINGLE_SOURCE_NEGATIVE,
)

GOLDEN = "config/golden/stage2_fewshot_single_source.yaml"
ALL_ROLES = {"principle", "process_template", "tool_instruction", "process_instance", "growth_edge"}
NEG = S2_GOLDEN_SINGLE_SOURCE_NEGATIVE
MAXT = S2_GOLDEN_SINGLE_SOURCE_MAX


def test_single_source_golden_has_all_five_roles() -> None:
    """Every content_type role must be represented by at least one positive example."""
    pos, neg, _ = load_golden_single_source(GOLDEN, NEG, MAXT)
    roles = {e["expected_fb"]["content_type"] for e in pos}
    assert roles == ALL_ROLES, f"missing roles: {ALL_ROLES - roles}"


def test_single_source_golden_has_negatives() -> None:
    """Hard negatives (rejection training) must be present and reach the formatter."""
    pos, neg, _ = load_golden_single_source(GOLDEN, NEG, MAXT)
    assert len(neg) == NEG
    txt = format_golden_fewshot_single_source(pos, neg)
    assert "REJECTION EXAMPLES" in txt


def test_formatter_shows_content_type_and_rejection_text() -> None:
    """The few-shot must show content_type per example and the rejection passage text."""
    pos, neg, _ = load_golden_single_source(GOLDEN, NEG, MAXT)
    txt = format_golden_fewshot_single_source(pos, neg)
    # Every role is surfaced in the example headers.
    for role in ALL_ROLES:
        assert f"content_type = {role}" in txt, f"role not surfaced: {role}"
    # Rejection examples now carry the actual passage text (not just rationale),
    # which is what teaches the model the text→NULL mapping (over-fire fix).
    assert "PASSAGE:" in txt


def test_deterministic_selection() -> None:
    """Same inputs → same selection and formatting (R7 temp=0.0 analogue)."""
    a_pos, a_neg, a_n = load_golden_single_source(GOLDEN, NEG, MAXT)
    b_pos, b_neg, b_n = load_golden_single_source(GOLDEN, NEG, MAXT)
    assert [e["id"] for e in a_pos] == [e["id"] for e in b_pos]
    assert [e["id"] for e in a_neg] == [e["id"] for e in b_neg]
    assert a_n == b_n


def test_tool_instruction_has_contrastive_pair() -> None:
    """Both the clear library-call AND the ambiguous algorithm (DFS) TI examples
    must reach the few-shot. A single TI example is not enough to teach PT-vs-TI
    (BUG-147 — the DFS algorithm was mislabelled process_template)."""
    pos, neg, _ = load_golden_single_source(GOLDEN, NEG, MAXT)
    ti = [e for e in pos if e["expected_fb"]["content_type"] == "tool_instruction"]
    assert len(ti) >= 2, "must include both clear + ambiguous tool_instruction examples"


def test_body_fields_present_on_non_principle_positives() -> None:
    """Every non-principle positive must carry its type-specific body fields (P2-1),
    so the few-shot shows the agreed schema (steps/syntax/instance_text/body)."""
    from pipeline.content_types import S2_BODY_FIELDS
    pos, neg, _ = load_golden_single_source(GOLDEN, NEG, MAXT)
    for e in pos:
        ct = e["expected_fb"]["content_type"]
        if ct == "principle":
            continue
        missing = [f for f in S2_BODY_FIELDS.get(ct, []) if f not in e["expected_fb"]]
        assert not missing, f"{e['id']} ({ct}) missing body fields: {missing}"


if __name__ == "__main__":
    test_single_source_golden_has_all_five_roles()
    test_single_source_golden_has_negatives()
    test_formatter_shows_content_type_and_rejection_text()
    test_deterministic_selection()
    print("single-source golden tests OK")
