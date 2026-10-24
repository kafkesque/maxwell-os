#!/usr/bin/env python3
"""tests/test_governance_faces_spec.py - the paired contract for specs/governance_faces.spec.md (D-2978).

One test per invariant, named in the spec, driving the rail's PURE functions: no 12-minute scan, no write to a
face, no reliance on the live registers' VALUES (they move daily). Where an invariant is about the real files
(INV-8's ordering, INV-9's mutation entry), the test reads the file - because that IS the subject.
"""
from __future__ import annotations

import importlib.util
import re
import tempfile
from pathlib import Path

import pytest
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
    assert len(invariants) == len(named) == 16, "one invariant, one named test (D-2978)"
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
    assert len(entries) == 6, ("both claim surfaces (history and LIVE), both heading limbs and both state "
                                  "limbs (the sign's completeness, the partition) must be locked")
    for entry in entries:
        assert entry.get("expect") == "red"
        assert str(entry.get("marker", "")).strip()
        source = RAIL.read_text(encoding="utf-8")
        assert source.count(str(entry["find"])) == 1, f"{entry['id']}: the find-text must match the bytes exactly once"
        assert str(entry["marker"]) not in source, f"{entry['id']}: the marker must be absent at baseline"


# ------------------------------------------------------------------ D-2985: the LIVE region
SYNC_CFG = yaml.safe_load((PROJECT_ROOT / "config" / "gov_sync.yaml").read_text(encoding="utf-8"))
LANE_CFG = {"face_owner_lane_label": SYNC_CFG["face_owner_lane_label"], "task_movers": SYNC_CFG["task_movers"]}


def live(body: list[str], owner: int = 0) -> list[str]:
    """The rail's LIVE-region join, driven with a synthetic face body (no write, no scan of the tree)."""
    return rail.live_faults(Path("FACE.md"), body, LANE_CFG, owner)


def test_a_hand_line_may_not_claim_to_be_the_live_index() -> None:
    """INV-10: the label has ONE home - and the shape the first rule was blind to is the one that counted."""
    assert len(live(["## 🔴 CURRENT OPEN / PENDING INDEX (machine-derived 2026-10-03 — the live face)."])) == 1
    assert live(["## 🔴 OPEN / PENDING — tier heading (the DERIVED block below owns the current state)."]) == []
    assert live(["> Gap 1 - the MTR 'CURRENT OPEN INDEX' (the machine-derived live face) sits in a section."]) == []
    # the real faces: the claim must be absent, above the marker, TODAY
    for face in FACES:
        lines = face.read_text(encoding="utf-8").splitlines()
        assert not [f for f in rail.live_faults(face, lines, LANE_CFG, 0) if "claims to BE" in f], \
            f"{face.name}: still claims to be the live index"


def test_a_citation_in_the_live_region_resolves() -> None:
    """INV-11 (D-405): a live claim naming a file that does not exist is an assertion, not a citation."""
    assert len(live(["see scripts/no_such_rail_at_all.py for the join"])) == 1
    assert live(["see config/gov_sync.yaml for the join"]) == []
    for face in FACES:
        lines = face.read_text(encoding="utf-8").splitlines()
        bad = [f for f in rail.live_faults(face, lines, LANE_CFG, 0) if "does not exist" in f]
        assert not bad, f"{face.name}: cites a file that does not exist: {bad}"


def test_the_face_leads_with_the_owner_lane_when_the_register_has_one() -> None:
    """INV-12: where the register says only the OWNER can move work, the face says so, and says it FIRST."""
    assert len(live(["the face says nothing about who moves what"], owner=2)) == 1
    lane = f"> **{LANE_CFG['face_owner_lane_label']} (1) — what ONLY YOU can move:**"
    assert live([lane], owner=2) == []
    reg = yaml.safe_load((PROJECT_ROOT / "config" / "task_register.yaml").read_text(encoding="utf-8"))
    owner_moved = [t for t in reg["tasks"]
                   if str(t.get("state")) not in ("done", "superseded", "rule") and t.get("mover") == "owner"]
    if not owner_moved:
        pytest.skip("the register declares no owner-moved task right now; INV-12 is CONDITIONAL (D-3142): "
                    "a cleared owner lane is a valid end-state, not a drift")
    for face in FACES:
        text = face.read_text(encoding="utf-8")[: face.read_text(encoding="utf-8").index("GOV-HISTORY:START")]
        lane_at, pipe_at = text.find("**OWNER LANE"), text.find("**PIPELINE LANE")
        assert -1 < lane_at < pipe_at, f"{face.name}: the OWNER lane does not LEAD the pipeline lane"


def test_the_census_recut_never_rewrites_history() -> None:
    """INV-13 (R-D410): the writer owns the LIVE region; below the marker it must not touch a single byte."""
    gs = importlib.util.spec_from_file_location("gov_sync", PROJECT_ROOT / "scripts" / "gov_sync.py")
    mod = importlib.util.module_from_spec(gs)
    assert gs and gs.loader
    gs.loader.exec_module(mod)
    x = {"decisions_total": 7, "stamp": "deadbeefdeadbeef", "date": "2026-01-02",
         "bugs_total": 5, "bugs_open": 3, "bugs_closed": 2}
    tail = "SNAPSHOT: 99 decisions (census stamp 27, 1999-01-01) · 42 bugs (1 open / 41 closed;"
    out, n = mod._recut_census("live 99 decisions (census stamp 27, 1999-01-01)\n" + mod.HIS + "\n" + tail, "", {}, x)
    assert n >= 1 and out.endswith(tail), "the history region must survive the re-cut BYTE-IDENTICAL (R-D410)"
    assert "7 decisions (census stamp deadbeefdeadbeef, 2026-01-02)" in out, "the live region must be re-cut"


# ------------------------------------------------------------------ D-2986: the HEADINGS between the two regions
HEAD_CFG = {k: SYNC_CFG[k] for k in ("face_index_head_tokens", "face_hand_index_token",
                                     "face_head_declaration_re")}


def heads(body: list[str]) -> list[str]:
    """The rail's heading rule, driven with a synthetic face body below a real marker."""
    return rail.heading_faults(Path("FACE.md"), [MARKER] + body, HEAD_CFG)


def test_every_declared_state_carries_a_sign() -> None:
    """INV-15: the SIGN map is keyed by the DECLARED axes and the AUTHORITY renders every sign it declares.

    MEASURED 2026-10-13: the derived block printed bare words while the hand indexes below the marker - which
    INV-14 declares make no live claim - led with the tier icons, so the colour sat on the region that claims
    NOTHING. Two limbs, both driven here in both directions."""
    # limb 1 (completeness, PURE): the real map must cover every declared axis, and a hole must fire
    assert rail.glyph_faults(SYNC_CFG) == [], "the real state_glyphs must cover every declared state"
    hole = {k: v for k, v in SYNC_CFG["state_glyphs"].items() if k != "MED"}
    assert any("'MED'" in f for f in rail.glyph_faults({**SYNC_CFG, "state_glyphs": hole})), \
        "a declared state with no sign must fire"
    # ...and the required set is the DECLARED AXIS, never the census's keys. MEASURED 2026-10-13: the first
    # version of this limb read the census's `summary` and so demanded signs for `total` and `by_category` -
    # a fault of the RULE, not of the map (the D-2986 lesson). One signed state, everything else missing:
    only_med = rail.glyph_faults({**SYNC_CFG, "state_glyphs": {"MED": "x"}})
    assert any("'CRITICAL'" in f for f in only_med), "a declared severity with no sign must fire"
    assert not any("'by_category'" in f or "'total'" in f for f in only_med), \
        "the census's non-state keys are NOT part of the axis (this limb's own first defect)"
    # limb 2 (presence): a face whose derived block renders no sign must fire, and the real faces must be clean
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "FACE.md"
        p.write_text("a face with no derived block at all\n", encoding="utf-8")
        assert any("does not render the sign" in f for f in rail.glyph_faults(SYNC_CFG, p))
    for face in FACES:
        bad = rail.glyph_faults(SYNC_CFG, face)
        assert not bad, f"{face.name}: {bad}"


def test_the_decision_state_buckets_partition_the_census() -> None:
    """INV-16 (BUG-765): the DECLARED buckets are disjoint and their union EQUALS the states the census counts.

    The defect that created this invariant: the decisions line summed to 981 of 1114, missing exactly the 133
    'ratified' decisions - a state no file under governance declared, printed or signed."""
    assert rail.partition_faults(SYNC_CFG) == [], "the real buckets must partition the census"
    # the exact shape of BUG-765: a state the census counts that NO bucket holds
    orphan = rail.partition_faults(SYNC_CFG, {"summary": {"total": 100, "open": 60, "active": 30,
                                                        "quiesced": 10}})
    assert any("NO declared bucket holds" in f for f in orphan), "an unaccounted state must fire"
    # a state in TWO buckets would be counted twice by whoever reads either
    doubled = rail.partition_faults({**SYNC_CFG,
                                     "decision_void_states": list(SYNC_CFG["decision_void_states"]) + ["open"]})
    assert any("BOTH" in f for f in doubled), "a doubly-bucketed state must fire"
    # and the buckets are DISJOINT on the real config
    seen: set = set()
    for k in rail.DECISION_BUCKET_KEYS:
        group = set(SYNC_CFG[k])
        assert not (seen & group), f"{k} overlaps another bucket"
        seen |= group


def test_an_index_heading_declares_what_it_is_and_carries_no_count() -> None:
    """INV-14: a heading that LEADS with a tier/state token is an INDEX heading; below the marker it must say
    what it is and may not restate a count. MEASURED 2026-10-13: twelve such headings, two of them carrying a
    number the register had moved on from."""
    # the shape that fired: an index heading naming a state, declaring nothing
    assert len(heads(["## 🟢 ACTIVE — in effect (477)"])) == 2, "both limbs must fire on the measured shape"
    # limb 1: the declaration. Both true shapes are accepted (the D-2984 snapshot form already names the authority)
    assert heads(["## 🟢 ACTIVE — in effect — HAND INDEX, not a register (the DERIVED block above owns it)"]) == []
    assert heads(["### Pending from registry (SNAPSHOT 2026-10-03 — the DERIVED index at the top owns it)"]) == []
    # limb 2: the count. A count-free label is fine; the same label with a number is not (BUG-588/D-2642)
    assert len(heads(["## 🟢 ACTIVE — in effect (477) — HAND INDEX, not a register"])) == 1
    # NOT the rule: a RECORD heading is the register's own status slot (bug_status.py), not an index heading
    assert heads(["## BUG-331 — Serving-gate write to the production DB (MED, OPEN)"]) == []
    assert heads(["### BUG-254 - RESOLVED"]) == []
    # and the live tier heading above the marker is not a history claim
    assert rail.heading_faults(Path("FACE.md"), ["## 🔴 OPEN — MUST", MARKER], HEAD_CFG) == []
    # the real faces: TODAY every index heading in the three faces declares itself, and none carries a count
    for face in FACES:
        lines = face.read_text(encoding="utf-8").splitlines()
        bad = rail.heading_faults(face, lines, HEAD_CFG)
        assert not bad, f"{face.name}: {bad}"
