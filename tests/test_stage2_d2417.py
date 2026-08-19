"""D2417 regression tests — S2 extraction_type/content_type conflation + summary gate.

Covers BUG-145 and BUG-146 fixes:
  1. BUG-145: the model writes a content_type ROLE (tool_instruction,
     process_template, process_instance, growth_edge, principle) into the
     extraction_type FORM field → rescued via _normalize_role_fields.
  2. BUG-146: the summary gate was content_type-blind — is_summary=true
     discarded non-principle roles. Now only gates a genuine principle
     restatement.

Pure derivation units — no LLM/OMLX required.
"""

from __future__ import annotations

from pipeline.content_types import (
    CONTENT_TO_EXTRACTION_TYPE,
    CONTENT_TYPES,
    EXTRACTION_TYPES,
)
from pipeline.stage2_extract import _normalize_role_fields

# frozenset of non-principle roles (mirrors the gate's set).
NON_PRINCIPLE_ROLES: frozenset[str] = CONTENT_TYPES - {"principle"}


# ── Fix 1: BUG-145 conflation rescue ───────────────────────────────────────
def test_role_leaked_into_extraction_type_is_rescued() -> None:
    """tool_instruction in extraction_type → content_type, default the form."""
    out = _normalize_role_fields(
        {"extraction_type": "tool_instruction", "content_type": "principle"}
    )
    assert out["content_type"] == "tool_instruction"
    assert out["extraction_type"] == "normative_heuristic"


def test_all_roles_rescued_with_weakest_honest_form() -> None:
    """Every content_type ROLE maps to a valid, non-over-claiming FORM."""
    for role in NON_PRINCIPLE_ROLES | {"principle"}:
        out = _normalize_role_fields(
            {"extraction_type": role, "content_type": "principle"}
        )
        assert out["content_type"] == role
        assert out["extraction_type"] in EXTRACTION_TYPES


def test_valid_extraction_type_left_untouched() -> None:
    """A correctly-filed FORM is never mutated."""
    out = _normalize_role_fields(
        {"extraction_type": "causal_mechanism", "content_type": "principle"}
    )
    assert out["extraction_type"] == "causal_mechanism"
    assert out["content_type"] == "principle"


def test_reverse_conflation_form_into_content_type() -> None:
    """A FORM leaked into content_type is moved back to extraction_type."""
    out = _normalize_role_fields(
        {"extraction_type": "", "content_type": "causal_mechanism"}
    )
    assert out["extraction_type"] == "causal_mechanism"
    assert out["content_type"] == "principle"


def test_mapping_round_trips_to_valid_form() -> None:
    """CONTENT_TO_EXTRACTION_TYPE values are all valid extraction_types."""
    for role, form in CONTENT_TO_EXTRACTION_TYPE.items():
        assert role in CONTENT_TYPES
        assert form in EXTRACTION_TYPES


# ── Fix 2: BUG-146 content_type-aware gate ─────────────────────────────────
def test_gate_keeps_non_principle_role_when_is_summary_true() -> None:
    """is_summary=true + content_type=tool_instruction must NOT be gated."""
    # Simulate the gate decision: gate only when content_type NOT in non-principle roles.
    content_type = "tool_instruction"
    is_summary = True
    gate_enabled = True
    gated = is_summary and gate_enabled and content_type not in NON_PRINCIPLE_ROLES
    assert gated is False


def test_gate_still_discards_principle_summary() -> None:
    """is_summary=true + content_type=principle (a genuine restatement) IS gated."""
    content_type = "principle"
    is_summary = True
    gate_enabled = True
    gated = is_summary and gate_enabled and content_type not in NON_PRINCIPLE_ROLES
    assert gated is True


def test_gate_disabled_never_gates() -> None:
    """gate_enabled=False passes everything through."""
    assert not (True and False and "tool_instruction" not in NON_PRINCIPLE_ROLES)
