#!/usr/bin/env python3
"""tests/test_governance_faces_spec.py - the paired contract for specs/governance_faces.spec.md (D-2978).

One test per invariant, named in the spec, driving the rail's PURE functions: no 12-minute scan, no write to a
face, no reliance on the live registers' VALUES (they move daily). Where an invariant is about the real files
(INV-8's ordering, INV-9's mutation entry), the test reads the file - because that IS the subject.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = PROJECT_ROOT / "specs" / "governance_faces.spec.md"
RAIL = PROJECT_ROOT / "scripts" / "check_governance_faces.py"

_spec = importlib.util.spec_from_file_location("check_governance_faces", RAIL)
rail = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(rail)

MARKER = "<!-- GOV-HISTORY:START (D-2981) -->"
FACES = (PROJECT_ROOT / "DECISION-LOG.md",
         PROJECT_ROOT / "MASTER-TASK-REGISTER.md",
         PROJECT_ROOT / "governance" / "buglog.md")
STATES = {"D1": "ACTIVE", "D2": "RESOLVED", "D3": "RESOLVED", "D4": "SUPERSEDED"}
CLOSED, KNOWN = {539, 631}, {539, 631, 700}


def faults(body: list[str]) -> list[str]:
    """The rail's claim surface, driven with a synthetic face body below a real marker."""
    return rail.history_faults(Path("FACE.md"), [MARKER] + body, STATES, CLOSED, KNOWN)


def first_fault(body: list[str]) -> str:
    out = faults(body)
    assert len(out) == 1, f"expected exactly one fault, got {out}"
    return out[0]


def test_the_spec_is_paired_1to1_with_its_contract() -> None:
    """The pairing is the contract's own subject (D-2978): one invariant, one named test, no orphans."""
    text = SPEC.read_text(encoding="utf-8")
    invariants = re.findall(r"(?m)^### (INV-\d+)", text)
    named = re.findall(r"\*\*Test:\*\*\s*`([a-z0-9_]+)`", text)
    assert len(invariants) == len(named) == 9, "one invariant, one named test (D-2978)"
    for name in named:
        assert name in globals(), f"the spec names {name}, which the contract does not define"


def test_the_live_claim_label_has_one_home() -> None:
    """INV-1: a line that LEADS with the label fires; prose that discusses it does not."""
    assert len(faults(["> **CURRENT OPEN INDEX (the live face).**"])) == 1
    assert faults(["> **SNAPSHOT 2026-10-12 (history).**"]) == []
    discussed = ["> Gap 1 - the MTR 'CURRENT OPEN INDEX' (the machine-derived live face) sits in a section."]
    assert faults(discussed) == []
    # the same words ABOVE the marker are not a claim about the history region
    assert rail.history_faults(Path("FACE.md"), ["> the live face", MARKER], STATES, CLOSED, KNOWN) == []


def test_the_live_census_marker_may_not_stand_in_history() -> None:
    """INV-2: the marker is live by definition, so it may not stand in a region declared NOT a register."""
    assert len(faults(["Register truth: 1111 decisions / 523 bugs (184 open / 339 closed)."])) == 1
    assert faults(["SNAPSHOT 2026-10-12 (dated history): as measured then, 1111 decisions."]) == []


def test_a_decision_row_joins_to_the_register() -> None:
    """INV-3: joined to the register, or its SECTION declares the moment (bounded by the marker)."""
    assert "claims D2 is ACTIVE" in first_fault(["| D2 | ACTIVE | something |"])
    assert faults(["| D2 | RESOLVED | something |"]) == []
    assert "does not carry" in first_fault(["| D9 | ACTIVE | something |"])
    assert faults(["## 2026-10-03 - the flips", "| D2 | ACTIVE | something |"]) == []
    # the row SHAPES the first version of this rule could not see (BUG-760 verification pass)
    assert "claims D2 is ACTIVE" in first_fault(["| **D2** | **ACTIVE** | something |"])
    assert "claims D2 is ACTIVE" in first_fault(["| D2 practicality filter | ACTIVE | something |"])
    assert faults(["| BUG-625 | RESOLVED | the D2 follow-on |"]) == []
    # a tier label ABOVE the marker can never date a claim inside the region
    assert rail.history_faults(Path("FACE.md"), ["## 2026-01-01 live tier", MARKER, "| D2 | ACTIVE | x |"],
                               STATES, CLOSED, KNOWN) != []


def test_a_transition_row_is_read_by_its_last_state() -> None:
    """INV-4: the four-column form makes the claim its END state; a prose cell makes no claim."""
    assert faults(["| D3 | PROPOSED | RESOLVED | the ship |"]) == []
    assert "claims D3 is ACTIVE" in first_fault(["| D3 | PROPOSED | ACTIVE | the ship |"])
    assert faults(["| D3 | something that discusses resolved at length |"]) == []


def test_the_highest_open_field_states_its_moment() -> None:
    """INV-5: the derived field carries its moment ON ITS OWN LINE."""
    assert "highest-OPEN" in first_fault(["Registry unchanged: highest OPEN BUG-750."])
    assert faults(["The register then stood at 460 bugs (163 open, highest OPEN then BUG-695)."]) == []
    assert faults(["Highest OPEN on 2026-10-05 = BUG-695."]) == []


def test_a_present_tense_open_assertion_declares_its_moment() -> None:
    """INV-6: adjacent id+claim, joined to the register unless the ENTRY names the moment."""
    assert "says CLOSED" in first_fault(["BUG-539 still OPEN."])
    assert faults(["## 2026-09-26 - carried", "BUG-539 still OPEN."]) == []
    assert faults(["BUG-700 is OPEN; BUG-539 was the same class."]) == []
    assert "does not carry" in first_fault(["BUG-999 is OPEN."])


def test_every_fault_names_its_repair() -> None:
    """INV-7: a fault that names no remedy is prose (D-405). Every limb carries one."""
    battery = [
        ["> **CURRENT OPEN INDEX (the live face).**"],
        ["Register truth: 1 decisions / 2 bugs (1 open / 1 closed)."],
        ["| D2 | ACTIVE | x |"],
        ["| D9 | ACTIVE | x |"],
        ["Registry unchanged: highest OPEN BUG-750."],
        ["BUG-539 still OPEN."],
        ["BUG-999 is OPEN."],
    ]
    remedies = ("relabel", "name the moment", "date-scope", "leave the number", "leave it", "correct")
    for body in battery:
        for fault in faults(body):
            assert any(word in fault for word in remedies), f"no remedy named: {fault}"


def test_the_derived_block_stands_above_the_history_marker() -> None:
    """INV-8: the ordering is load-bearing - the claim surface must never judge the derived bytes."""
    for face in FACES:
        text = face.read_text(encoding="utf-8")
        assert "<!-- GOV-INDEX:START" in text, f"{face.name}: no derived block"
        assert "GOV-HISTORY:START" in text, f"{face.name}: no declared history"
        assert text.index("<!-- GOV-INDEX:START") < text.index("GOV-HISTORY:START"), \
            f"{face.name}: the history marker precedes the derived block, so the rail would judge its own output"


def test_the_rule_is_mutation_locked_and_its_controls_run() -> None:
    """INV-9 (D-2676 iv): the mutation exists, is expected RED, and its find-text is in the bytes TODAY."""
    doc = yaml.safe_load((PROJECT_ROOT / "config" / "rail_mutations.yaml").read_text(encoding="utf-8"))
    entries = [e for e in doc.get("mutations", []) if e.get("subject") == "scripts/check_governance_faces.py"]
    assert len(entries) == 1, "the claim surface must be mutation-locked exactly once"
    entry = entries[0]
    assert entry.get("expect") == "red"
    assert str(entry.get("marker", "")).strip()
    source = RAIL.read_text(encoding="utf-8")
    assert source.count(str(entry["find"])) == 1, "the declared find-text must match the bytes exactly once"
    assert str(entry["marker"]) not in source, "the marker must not be present at baseline"
