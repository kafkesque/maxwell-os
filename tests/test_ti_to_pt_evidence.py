#!/usr/bin/env python3
"""tests/test_ti_to_pt_evidence.py — D-2955 (BUG-729): the TI->process_template promotion needs BODY
evidence, and the name vocabulary denotes PROCEDURES only.

WHY. Tier 3 promoted a `tool_instruction` to `process_template` on a single bare noun in the tool
name. MEASURED 2026-10-12 over the 108 stored TI rows: the four keywords fired on 10 rows and NOT ONE
is a procedure under the ratified D275b procedure, which tests "tool/software-specific command,
syntax, or feature" FIRST — 'OpenFrameworks' (a C++ creative-coding LIBRARY), 'Layout Analysis
System', 'Inventory Management System' are software ARTIFACTS that are USED, not methods that are
EXECUTED. A name is a PRIOR; the BODY must evidence a procedure — ordered steps AND a
done-condition/gate, the SAME pair tier 2 already uses for principle->process_template.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from pipeline import content_types as ct

_CFG = yaml.safe_load(
    (Path(ct.__file__).resolve().parent.parent / "config" / "content_types.yaml").read_text(encoding="utf-8")
)


def _ti(**over: object) -> dict:
    """A minimal tool_instruction-shaped record; every body field defaults to empty."""
    base: dict = {
        "fb_id": "ti-probe",
        "name": "Probe",
        "content_type": "tool_instruction",
        "definition": "",
        "mechanism": "",
        "boundary": "",
        "consequence": "",
        "elaboration": "",
        "tool_name": "",
        "syntax": "",
        "parameters": [],
    }
    base.update(over)
    return base


# The shape of the 10 MEASURED wrong promotions: a software artifact — syntax, parameters, a code
# example — and no procedure anywhere in the body.
ARTIFACT: dict = {
    "tool_name": "Inventory Management System",
    "syntax": "can_transfer(item, qty, force)",
    "parameters": [{"name": "item"}],
    "description": "Methods for validating, calculating and executing inventory transfers",
    "example": "can_transfer('prod_123', 50, True) -> True",
}

# A genuine procedure in the body: ordered steps AND a termination condition.
PROCEDURE: dict = {
    "tool_name": "Kaizen Cycle Workflow",
    "syntax": "kaizen_cycle(team)",
    "parameters": [{"name": "team"}],
    "description": (
        "First identify the bottleneck, then run the countermeasure experiment, then measure the "
        "effect. Repeat until the defect rate converges below the target."
    ),
    "example": "kaizen_cycle(team)",
}


def test_the_evidence_gate_is_the_configured_policy() -> None:
    """C12: the gate is a CONFIG value — bind code to config, never to a constant."""
    assert ct.TI_TO_PT_REQUIRE_BODY_EVIDENCE is bool(_CFG["reroute"]["ti_to_pt_require_body_evidence"])
    assert ct.TI_TO_PT_REQUIRE_BODY_EVIDENCE is True, "D-2955 (BUG-729): the body must evidence a procedure"


def test_the_vocabulary_is_procedure_denoting_only() -> None:
    """BUG-729, pinned: 'system'/'framework' name ARTIFACTS and must not return by edit."""
    assert ct.TI_TO_PT_KEYWORDS == tuple(_CFG["reroute"]["ti_to_pt_keywords"])
    assert "system" not in ct.TI_TO_PT_KEYWORDS, "an artifact noun is not evidence of a method"
    assert "framework" not in ct.TI_TO_PT_KEYWORDS, "a library is USED, not EXECUTED"
    assert "workflow" in ct.TI_TO_PT_KEYWORDS, "the procedure-denoting prior survives"


def test_a_software_artifact_does_not_move_even_when_named_like_a_system() -> None:
    """The measured defect, pinned: this is the exact shape of the 10 wrong promotions."""
    record = _ti(**ARTIFACT, name="Inventory Transfer Logic")
    assert ct.has_procedure_evidence(record) is False
    assert ct.reroute_content_type(record) == "tool_instruction"


def test_a_procedure_denoting_name_with_body_evidence_still_moves() -> None:
    """Recall is preserved — the narrowing must not kill the promotion it exists for."""
    record = _ti(**PROCEDURE, name="Kaizen Cycle")
    assert ct.has_procedure_evidence(record) is True
    assert ct.reroute_content_type(record) == "process_template"


def test_steps_without_a_done_condition_do_not_move() -> None:
    """D275b: a template needs a GATE, not merely a sequence (the D-2949 discipline, reused)."""
    no_gate = dict(PROCEDURE, description="First identify the bottleneck, then run the experiment, then measure the effect.")
    record = _ti(**no_gate, name="Kaizen Cycle")
    assert ct.has_procedure_evidence(record) is False
    assert ct.reroute_content_type(record) == "tool_instruction"


def test_the_override_measures_both_sides_without_editing_config() -> None:
    """The calibration's lever: the name-only form is reachable, and measured wrong.

    NOTE the lever governs the EVIDENCE gate only — the vocabulary is a SEPARATE, independently
    measured defect, so the probe record needs a PROCEDURE-denoting name for the historical side to
    fire at all. That separation is the point: two defects, two controls, one instrument.
    """
    record = _ti(**{**ARTIFACT, "name": "Transfer Execution", "tool_name": "Transfer Execution Workflow"})
    assert ct.reroute_content_type(record, require_body_evidence=False) == "process_template"
    assert ct.reroute_content_type(record, require_body_evidence=True) == "tool_instruction"


def test_a_procedure_named_but_evidence_less_ti_still_reaches_tier_4() -> None:
    """Q3, pinned: narrowing tier 3 must NOT make tier 4 unreachable.

    A name prior alone is no longer enough, so an underspecified TI keeps falling through to the
    structural check instead of being promoted out of it.
    """
    record = _ti(name="Zorp Workflow", tool_name="Zorp Workflow", syntax="", parameters=[], description="")
    assert ct.has_procedure_evidence(record) is False
    assert ct.reroute_content_type(record) == "quarantine"


def test_a_procedure_under_a_non_procedure_name_is_left_alone() -> None:
    """Q2, pinned as a KNOWN, MEASURED LIMIT: the gate only ever REMOVES promotions.

    This record's body DOES evidence a procedure, so the evidence gate is not what holds it back —
    the NAME PRIOR is, and that is unchanged behaviour: the tier fired on a name before this change
    and fires on a name plus evidence after it. A procedure whose name carries no procedure noun was
    never this tier's business (D-2747: tier 1, the owner map, is the authority for that case).
    """
    record = _ti(**{**PROCEDURE, "tool_name": "Snapz"})
    assert ct.has_procedure_evidence(record) is True
    assert ct.reroute_content_type(record) == "tool_instruction"


def test_the_evidence_gate_is_a_PROXY_not_proof_of_execution() -> None:
    """The KNOWN residual limit (raised by R5 2026-10-12), pinned rather than hidden.

    The gate is two regexes, so a tool manual that DESCRIBES someone else's procedure in prose —
    documentation OF a workflow rather than a tool's own usage — satisfies it. The verifier called
    this correctly: a marker is not proof of execution. It is still the best DETERMINISTIC signal
    available (D-343 forbids an LLM here), and the alternative — the name alone — measured 10
    promotions of which 0 survived. MEASURED manifest instances: 0 of 108. Pinned deliberately: a
    future narrowing must fail this test and read why, rather than rediscover the limit as a surprise.
    """
    documenting_the_tool = _ti(
        name="Release Note Workflow", tool_name="Release Note Workflow",
        syntax="release_note(note)", parameters=[{"name": "note"}],
        description=(
            "First the edit is staged, then the reviewer approves it, then the release is cut. "
            "Repeat until no further edits are requested."
        ),
    )
    assert ct.has_procedure_evidence(documenting_the_tool) is True
    assert ct.reroute_content_type(documenting_the_tool) == "process_template"  # the limit, on purpose


def test_an_underspecified_ti_without_a_procedure_name_still_quarantines() -> None:
    """Tier 4 is untouched by this change (a TI with neither syntax nor parameters is held)."""
    record = _ti(name="Zorp Widget", tool_name="Zorp", syntax="", parameters=[])
    assert ct.reroute_content_type(record) == "quarantine"
