#!/usr/bin/env python3
"""tests/test_task_register_spec.py - the paired contract for specs/task_register.spec.md (D-2978).

One test per invariant, named in the spec, driving scripts/gov_sync.py's PURE functions: the register's schema
validator, the severity join and the re-cut scope. Where an invariant is about the register or the faces
themselves, the test reads the real files - because those ARE the subject (the printed line the owner reads is
not an abstraction).
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = PROJECT_ROOT / "specs" / "task_register.spec.md"
SRC = PROJECT_ROOT / "scripts" / "gov_sync.py"
REGISTER = PROJECT_ROOT / "config" / "task_register.yaml"

_spec = importlib.util.spec_from_file_location("gov_sync", SRC)
gs = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(gs)

CFG = gs.cfg()
TASKS = yaml.safe_load(REGISTER.read_text(encoding="utf-8"))["tasks"]
BASE = {"priority": "MUST", "evidence": "e (2026-01-02)", "gate": "none"}


def faults(*entries: dict) -> list[str]:
    """The register's schema validator, driven with synthetic entries (no I/O, no live values)."""
    return gs.task_faults(list(entries), CFG)


def test_the_spec_is_paired_1to1_with_its_contract() -> None:
    """The pairing is the contract's own subject (D-2978): one invariant, one named test, no orphans."""
    text = SPEC.read_text(encoding="utf-8")
    invariants = re.findall(r"(?m)^### (INV-\d+)", text)
    named = re.findall(r"\*\*Test:\*\*\s*`([a-z0-9_]+)`", text)
    assert len(invariants) == len(named) == 6, "one invariant, one named test (D-2978)"
    for name in named:
        assert name in globals(), f"the spec names {name}, which the contract does not define"


def test_a_standing_rule_is_not_a_task() -> None:
    """INV-1: an `R-` id carries state: rule, is never counted as open work, and is rendered apart."""
    rule = {**BASE, "id": "R-1", "state": "rule", "mover": "pipeline", "title": "the faces are derived"}
    assert faults(rule) == []
    out = faults({**rule, "state": "open"})
    assert any("STANDING RULE" in f for f in out), "a rule registered as an open task must fire"
    assert "standing rule(s) never close" in gs.register_truth(CFG, gs.derive(CFG)), \
        "the census line must count rules APART from open tasks"
    # the real register: no R- entry may be counted as open work
    live_ids = {t["id"] for t in TASKS if str(t.get("state")) not in ("done", "superseded", "rule")}
    assert not {i for i in live_ids if str(i).startswith("R-")}, "an R- entry is counted as open work"


def test_every_entry_declares_who_must_move_it() -> None:
    """INV-2: mover is REQUIRED, declared (never defaulted, C12), and the real register always declares it."""
    assert any("WHO must act" in f for f in faults({**BASE, "id": "T-1", "state": "open", "title": "t"}))
    assert any("WHO must act" in f for f in faults({**BASE, "id": "T-1", "state": "open", "mover": "someone", "title": "t"}))
    assert faults({**BASE, "id": "T-1", "state": "open", "mover": "pipeline", "title": "t"}) == []
    declared = set(CFG["task_movers"])
    assert declared == {"owner", "pipeline"}, "the movers are DECLARED in config/gov_sync.yaml"
    for t in TASKS:
        assert t.get("mover") in declared, f"{t['id']} declares no declared mover (C12: no default)"
    assert gs.task_faults(TASKS, CFG) == [], "the real register must obey its own schema"


def test_an_owner_gate_is_a_mover_never_a_state() -> None:
    """INV-3: gatehood is mover: owner + the owner's word; the two fields may never disagree (C16)."""
    assert any("mover: owner but gate is 'none'" in f
               for f in faults({**BASE, "id": "T-1", "state": "open", "mover": "owner", "title": "t"}))
    assert any("the two fields disagree" in f
               for f in faults({**BASE, "id": "T-1", "state": "open", "mover": "pipeline", "title": "t",
                                "gate": "the owner word that licenses the write"}))
    assert faults({**BASE, "id": "T-1", "state": "open", "mover": "owner", "title": "t",
                   "gate": "the owner word that licenses the write"}) == []
    assert "gate" not in CFG["task_states"], "state: gate is RETIRED - gatehood is a MOVER (one home per fact)"
    for t in TASKS:
        if t.get("mover") == "owner":
            assert str(t.get("gate", "none")).strip().lower() != "none", f"{t['id']}: owner-gated with no gate text"


def test_a_count_a_register_owns_has_one_home() -> None:
    """INV-4: a count in the printed line is refused; a measurement belongs to `evidence`, dated (D-2660)."""
    assert any("ONE home" in f
               for f in faults({**BASE, "id": "T-1", "state": "open", "mover": "pipeline",
                                "title": "108 of 185 open bugs carry no severity"}))
    assert any("ONE home" in f
               for f in faults({**BASE, "id": "T-1", "state": "open", "mover": "pipeline",
                                "title": "t", "why": "the register reads open = 185 today"}))
    assert any("MOMENT OF MINT" in f
               for f in faults({**BASE, "id": "T-1", "state": "open", "mover": "pipeline", "title": "t",
                                "evidence": "185 open bugs"}))
    assert faults({**BASE, "id": "T-1", "state": "open", "mover": "pipeline", "title": "t",
                   "why": "the census owns the number", "evidence": "185 open (2026-10-13)"}) == []
    # the real register: no title/why restates a count, and every evidence line that carries one is dated
    for t in TASKS:
        for field in ("title", "why"):
            m = gs.COUNT_NOUN_RE.search(str(t.get(field, ""))) or gs.CENSUS_SCALAR_RE.search(str(t.get(field, "")))
            assert m is None, f"{t['id']}.{field} restates a count: {m and m.group(0)!r}"


def test_open_ness_is_the_census_s_and_the_severity_line_partitions_it() -> None:
    """INV-5: the population IS the census's open ids and the parts sum to it (a checkable line, D-2642)."""
    bugs = yaml.safe_load((PROJECT_ROOT / gs.CFG_PATH.parent / ".." / "governance" / "bug_status.json")
                          .resolve().read_text(encoding="utf-8"))
    open_ids = {str(b["id"]) for b in bugs["open"]}
    sev, unlab = gs.severity_census(CFG, open_ids)
    assert sum(sev.values()) + len(unlab) == len(open_ids), \
        "the severity line must PARTITION the census's open count (the old parts summed to 255 for 185)"
    assert len(unlab) <= int(CFG["severity_grandfathered"]), "the gap may not exceed its shrink-only ceiling"
    # the visibility class: a three-hash heading is SEEN (BUG-426/427 - the lesson the old reader never got)
    assert gs.BUG_HEAD.search("### BUG-426 (HIGH, OPEN - UNRESOLVED) - twice asserted") is not None
    assert gs.BUG_HEAD.search("## BUG-539 (MED - CLOSED) - x") is not None


def test_the_rule_is_mutation_locked_and_its_controls_run() -> None:
    """INV-6 (D-2676 iv): both entries exist, are expected RED, and their find-text matches the bytes TODAY."""
    doc = yaml.safe_load((PROJECT_ROOT / "config" / "rail_mutations.yaml").read_text(encoding="utf-8"))
    entries = [e for e in doc.get("mutations", []) if e.get("subject") == "scripts/gov_sync.py"]
    assert len(entries) >= 2, "the mover axis and the re-cut scope must each be mutation-locked"
    for entry in entries:
        assert entry.get("expect") == "red"
        assert str(entry.get("marker", "")).strip()
        source = SRC.read_text(encoding="utf-8")
        assert source.count(str(entry["find"])) == 1, f"{entry['id']}: the find-text must match the bytes exactly once"
        assert str(entry["marker"]) not in source, f"{entry['id']}: the marker must be absent at baseline"
