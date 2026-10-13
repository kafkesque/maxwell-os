#!/usr/bin/env python3
"""tests/test_label_store_write_spec.py - the paired contract for specs/label_store_write.spec.md (D-2978).

One test per invariant, named in the spec, driving scripts/apply_relabel_store_write.py's PURE core (`plan`) plus
the two subjects that ARE the claim rather than an abstraction: the module's own source (INV-8: the write set and
the imported homes) and the LIVE receipt joined back to the store (INV-7: the write is measured, not claimed).
"""
from __future__ import annotations

import importlib.util
import json
import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = PROJECT_ROOT / "specs" / "label_store_write.spec.md"
SRC = PROJECT_ROOT / "scripts" / "apply_relabel_store_write.py"
RECEIPT = PROJECT_ROOT / "config" / "label_store_write_receipt.json"
STORE = PROJECT_ROOT / "knowledge pipeline" / "maxwell.db"

_spec = importlib.util.spec_from_file_location("apply_relabel_store_write", SRC)
aw = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(aw)

TIERS = ("human_verbatim", "llm_extracted_from_source", "llm_hypothesis", "deterministic")
SEG = "computer science -> software engineering"
CORRECT_UNIT = "marketing strategy -> emerging"
ESCALATE_UNIT = "narrative theory -> literary theory"


def _license(units: list[str], cap: int = 163, tier: str = "deterministic") -> dict:
    """The license block as config/relabel_rulings.yaml carries it (a block of the rulings document)."""
    return {"store_write_license": {"decision": "D-2988", "granted": "2026-10-13", "units": units,
                                    "row_cap": cap, "provenance_tier": tier}}


def _rulings(**over: dict) -> dict:
    """The owner's words: a class rule for LATE-HOME and a unit word for the ABSTAIN unit."""
    doc = {
        "class_rules": {"LATE-HOME": {"policy": "CORRECT", "owner_canonical": "marketing"},
                        "ALIAS-LAYER-RETIRED": {"policy": "CONFIRM"},
                        "PROVENANCE-UNRESOLVED": {"policy": "ESCALATE"}},
        "unit_rulings": {SEG: {"action": "ABSTAIN"}},
    }
    doc.update(over)
    return doc


def _units() -> dict:
    return {CORRECT_UNIT: {"unit_key": CORRECT_UNIT, "cause": "LATE-HOME (D-2975)", "n_rows": "2"},
            SEG: {"unit_key": SEG, "cause": "PROVENANCE-UNRESOLVED", "n_rows": "2"},
            ESCALATE_UNIT: {"unit_key": ESCALATE_UNIT, "cause": "ALIAS-LAYER-RETIRED (D-2814)", "n_rows": "1"}}


def _segments() -> list[dict]:
    return [{"unit_key": CORRECT_UNIT, "fb_id": "a1", "stored_canonical": "emerging",
             "raw_label": "marketing strategy", "live_mapper_says": "marketing"},
            {"unit_key": CORRECT_UNIT, "fb_id": "a2", "stored_canonical": "emerging",
             "raw_label": "marketing strategy", "live_mapper_says": "marketing"},
            {"unit_key": SEG, "fb_id": "b1", "stored_canonical": "software engineering",
             "raw_label": "computer science", "live_mapper_says": "emerging"},
            {"unit_key": SEG, "fb_id": "b2", "stored_canonical": "software engineering",
             "raw_label": "computer science", "live_mapper_says": "emerging"}]


def _store() -> dict:
    return {"a1": {"discipline": "emerging", "discipline_raw": "marketing strategy"},
            "a2": {"discipline": "emerging", "discipline_raw": "marketing strategy"},
            "b1": {"discipline": "software engineering", "discipline_raw": "computer science"},
            "b2": {"discipline": "software engineering", "discipline_raw": "computer science"}}


def _mapper(raw: str) -> str:
    return "emerging" if raw == "computer science" else "marketing"


def _macro(discipline: str) -> str:
    return "emerging" if discipline == "emerging" else "Method & Business"


def _plan(lic: dict, rulings: dict | None = None, units: dict | None = None,
          segments: list[dict] | None = None, store: dict | None = None,
          mapper=_mapper) -> tuple[list, list]:
    return aw.plan(lic, rulings or _rulings(), units or _units(), segments or _segments(),
                   store or _store(), mapper, _macro, TIERS)


# ── INV-1 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_no_license_no_write() -> None:
    """The owner word is the whole authority: no license block -> no operations, one named reason."""
    ops, faults = aw.plan({}, _rulings(), _units(), _segments(), _store(), _mapper, _macro, TIERS)
    assert ops == [], "no license means NO write"
    assert len(faults) == 1 and "store_write_license" in faults[0], faults


# ── INV-2 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_a_licensed_unit_without_a_ruling_is_refused() -> None:
    """A licensed unit no ruling reaches (ESCALATE) is refused, and emits nothing - D-2898."""
    ops, faults = _plan(_license([ESCALATE_UNIT]))
    assert ops == [], ops
    assert any(f.startswith("scope/not-ruled:") and ESCALATE_UNIT in f for f in faults), faults
    # a HELD owner word escalates rather than writes (the plan applier's own semantics, reused)
    held = _rulings(unit_rulings={SEG: {"action": "ABSTAIN"},
                                 CORRECT_UNIT: {"action": "CORRECT", "held": True}})
    ops2, faults2 = _plan(_license([CORRECT_UNIT, SEG]), held)
    assert any(f.startswith("scope/not-ruled:") for f in faults2), faults2
    assert sorted({o["fb_id"] for o in ops2}) == ["b1", "b2"], ops2


# ── INV-3 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_an_unlicensed_ruled_unit_is_a_fault() -> None:
    """A ruled unit the license omits is a fault, and the plan still never touches it."""
    ops, faults = _plan(_license([SEG]))
    assert any(f.startswith("scope/not-licensed:") and CORRECT_UNIT in f for f in faults), faults
    assert sorted({o["unit_key"] for o in ops}) == [SEG], "the scope may never widen"
    assert sorted({o["fb_id"] for o in ops}) == ["b1", "b2"], ops


# ── INV-4 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_the_target_is_triply_agreed() -> None:
    """mapper == owner target == recorded packet answer; any disagreement is refused, never resolved."""
    both = _license([CORRECT_UNIT, SEG])
    ops, faults = _plan(both)
    assert faults == [], faults
    assert sorted({(o["from"], o["to"], o["method"], o["source"]) for o in ops}) == [
        ("emerging", "marketing", "synonym", "deterministic"),
        ("software engineering", "emerging", "emerging_real", "deterministic")], ops
    _o, f_mapper = _plan(both, mapper=lambda raw: "design thinking")
    assert any(f.startswith("target/disagreement: fb_id a1") for f in f_mapper), f_mapper
    segs = [{**s, "live_mapper_says": "design thinking"} if s["fb_id"] == "a1" else s for s in _segments()]
    _o2, f_packet = _plan(both, segments=segs)
    assert any(f.startswith("target/disagreement: fb_id b1 is not in the surface".split(" is ")[0]) or
               f.startswith("target/disagreement:") for f in f_packet), f_packet


# ── INV-5 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_a_stale_surface_is_refused() -> None:
    """The store moved under the reviewed surface -> refuse; a packet disagreeing with its own rows -> refuse."""
    both = _license([CORRECT_UNIT, SEG])
    stale = dict(_store(), a1={"discipline": "marketing", "discipline_raw": "marketing strategy"})
    _o, f_stale = _plan(both, store=stale)
    assert any(f.startswith("surface/stale: fb_id a1") for f in f_stale), f_stale
    units = dict(_units(), **{CORRECT_UNIT: {"unit_key": CORRECT_UNIT, "cause": "LATE-HOME", "n_rows": "9"}})
    _o2, f_count = _plan(both, units=units)
    assert any(f.startswith("surface/stale: the packet declares 9 row(s)") for f in f_count), f_count
    missing = {k: v for k, v in _store().items() if k != "b1"}
    _o3, f_missing = _plan(both, store=missing)
    assert any(f.startswith("surface/stale: fb_id b1") for f in f_missing), f_missing


# ── INV-6 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_the_cap_and_the_tier_are_declared() -> None:
    """The ceiling is shrink-only (D-2644) and the tier must be a C29 member read from its ONE home."""
    both = [CORRECT_UNIT, SEG]
    _o, f_cap = _plan(_license(both, cap=3))
    assert any(f.startswith("cap/exceeded:") for f in f_cap), f_cap
    _o2, f_tier = _plan(_license(both, tier="owner_ruled"))
    assert any(f.startswith("tier/undeclared:") for f in f_tier), f_tier
    assert "deterministic" in aw._tiers(), "the tier vocabulary must come from pipeline.schemas (C12)"


# ── INV-7 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_the_receipt_records_a_measurement() -> None:
    """The live receipt: every input hashed, changed==verified==planned, and the rows re-verified in the store."""
    assert RECEIPT.exists(), f"{RECEIPT} is the measurement of the licensed write (D-2988)"
    doc = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert doc["decision"] == "D-2988" and doc["granted"] == "2026-10-13"
    assert doc["fault"] is False
    m = doc["measurement"]
    assert m["changed"] == m["verified"] == m["planned"] == len(doc["rows"]) > 0, m
    assert m["menu_unmoved"] is True and m["menu_hash_before"] == m["menu_hash_after"], m
    for key in ("rulings_sha256", "packet_sha256", "segments_sha256"):
        assert len(doc["inputs"][key]) == 64, key
    assert doc["plan"]["rows"] == len(doc["rows"]) and doc["plan"]["units"], doc["plan"]
    conn = sqlite3.connect(str(STORE))
    try:
        bad = [r for r in doc["rows"]
               if (conn.execute("SELECT discipline, discipline_macro, discipline_source, "
                                "taxonomy_match_method FROM fbs WHERE fb_id = ?", (r["fb_id"],)).fetchone()
                   or ()) != (r["to"], r["macro"], r["source"], r["method"])]
    finally:
        conn.close()
    assert bad == [], f"the receipt claims rows the store does not hold: {bad[:2]}"


# ── INV-8 ─────────────────────────────────────────────────────────────────────────────────────────────
def test_the_raw_and_the_macro_home_are_untouched() -> None:
    """The write set is exactly four columns; the raw is not one of them; the derived homes are IMPORTED."""
    src = SRC.read_text(encoding="utf-8")
    assert aw._COLUMNS == ("discipline", "discipline_macro", "discipline_source", "taxonomy_match_method")
    assert "discipline_raw" not in aw._COLUMNS
    update = re.search(r"UPDATE fbs SET ([^\n]*)", src)
    assert update is not None, "the applier must carry ONE UPDATE"
    assert "for c in _COLUMNS" in update.group(1), \
        f"the write set must be BUILT from the declared columns, not written by hand: {update.group(1)!r}"
    assert not re.search(r"SET\s+(discipline|discipline_macro|discipline_source|taxonomy_match_method)\s*=", src), \
        "no hand-written column list may exist beside the declared one (D-2642)"
    assert "from pipeline.discipline_macro import macro_for" in src, "the macro home is imported (D-2884a)"
    assert "from pipeline.taxonomy_manager import update_counts_from_fbs" in src, "the counts home is imported"
    body = src.split("def selftest(")[0]   # the known-answer fixture may stub the macro; the WRITER may not
    assert "Method & Business" not in body, "no macro bucket may be restated in the writer (D-2884a)"
    assert "discipline_macro_groups" not in src, "the scheme is never read directly: macro_for IS the home"
    assert "SELECT menu_hash" in src or "_menu_hashes" in src, "the menu set is measured, not assumed"


# ── the pairing contract (D-2978) ─────────────────────────────────────────────────────────────────────
def test_spec_and_tests_are_paired_one_to_one() -> None:
    """One invariant, one named test: the count is DERIVED from both sides, never restated."""
    invariants = re.findall(r"^### (INV-\d+)", SPEC.read_text(encoding="utf-8"), re.M)
    named = re.findall(r"^- \*\*Test:\*\* `(test_[a-z_]+)`", SPEC.read_text(encoding="utf-8"), re.M)
    assert len(invariants) == len(named) == 8, (invariants, named)
    mod = Path(__file__).read_text(encoding="utf-8")
    for test in named:
        assert f"def {test}(" in mod, f"{test} is named in the spec and missing here"
