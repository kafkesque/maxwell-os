"""tests/test_dedup_gate.py — D-2950/D-2951 commit-time dedup decision tests."""
import json

import pytest

from pipeline.dedup_gate import (
    BODY_FIELDS,
    DISPOSITION_CROSS_SOURCE,
    DISPOSITION_DIVERGENT,
    DISPOSITION_MERGE,
    CommitDedupGate,
    candidate_kind,
    duplicate_marker,
    group_key,
    load_committed_index,
    pick_richer,
    richness,
)


def _fb(name, source_ids, definition, mechanism="m", **extra):
    fb = {"name": name, "source_ids": frozenset(source_ids),
          "definition": definition, "mechanism": mechanism}
    fb.update(extra)
    return fb


def _row(fb, fb_id):
    """A committed row in the STORE's shape: a plain tuple with source_ids as JSON TEXT."""
    return (fb_id, fb["name"], fb["definition"], fb.get("mechanism", ""),
            json.dumps(sorted(fb.get("source_ids") or [])),
            fb.get("source_diversity"), fb.get("confidence_score"))


class _FakeCursor:
    def __init__(self, columns, rows):
        self.description = [(c,) for c in columns]
        self._rows = rows

    def __iter__(self):
        return iter(self._rows)


class _FakeConn:
    """sqlite-shaped double: the gate must not depend on the driver or its row_factory (C21)."""

    def __init__(self, rows):
        self._rows = rows

    def execute(self, sql):
        columns = [c.strip() for c in sql.split("SELECT", 1)[1].split(" FROM", 1)[0].split(",")]
        return _FakeCursor(columns, self._rows)


def test_insert_when_no_existing():
    c = _fb("X", {"s1"}, "def")
    assert candidate_kind(c, []) == "insert"


def test_keep_both_cross_source():
    c = _fb("X", {"s2"}, "def")
    existing = [_fb("X", {"s1"}, "def")]
    assert candidate_kind(c, existing) == "keep_both_cross_source"


def test_keep_both_divergent_same_source():
    c = _fb("X", {"s1"}, "type check required fields", mechanism="check keys and data types")
    existing = [_fb("X", {"s1"}, "schema quantity unit constraints",
                    mechanism="schema membership max quantity allowed units")]
    assert candidate_kind(c, existing) == "keep_both_divergent"


def test_merge_convergent_same_source():
    c = _fb("X", {"s1"}, "validate item fields", mechanism="check required keys")
    existing = [_fb("X", {"s1"}, "validate item fields", mechanism="check required keys")]
    assert candidate_kind(c, existing) == "merge_convergent"


def test_review_missing_source():
    c = _fb("X", set(), "def")
    existing = [_fb("X", set(), "def")]
    assert candidate_kind(c, existing) == "review"


def test_richness_counts_filled_body_fields():
    lean = _fb("X", {"s1"}, "def")
    rich = _fb("X", {"s1"}, "def", mechanism="m", consequence="c", boundary="b",
               failure_mode="f", elaboration="e", jargon="j", evidence_passages=["e"],
               source_diversity=3, confidence_score=0.9)
    assert richness(rich) > richness(lean)
    assert richness(lean) >= 1  # definition always counted
    assert len(BODY_FIELDS) == 8


def test_pick_richer_prefers_richer_and_ties_to_existing():
    lean = _fb("X", {"s1"}, "def")
    rich = _fb("X", {"s1"}, "def", mechanism="m", consequence="c")
    assert pick_richer(lean, [rich]) is rich
    # tie: existing wins (stability)
    a = _fb("X", {"s1"}, "def")
    b = _fb("X", {"s1"}, "def")
    assert pick_richer(b, [a]) is a


def test_group_key_folds_name_and_preserves_source_set():
    assert group_key("  Item Validation  Protocol! ", frozenset({"s1"})) == \
        ("item validation protocol", frozenset({"s1"}))


# ── D-2951 hardening: shape, mode, batch side, and the JSON-text trap ──────────────────────

def test_duplicate_marker_has_one_shape():
    """The store wrote '' for 'absent', so `duplicate_of IS NULL` (D-271d) matched ZERO rows."""
    assert duplicate_marker(None) is None
    assert duplicate_marker("") is None
    assert duplicate_marker("   ") is None
    assert duplicate_marker("abc123") == "abc123"


def test_gate_report_mode_records_without_linking():
    gate = CommitDedupGate({}, mode="report")
    d = gate.decide(_fb("X", {"s1"}, "def", "m"))
    assert d["kind"] == "insert" and d["action"] == "insert" and d["would"] == "insert"
    assert gate.receipt()["candidates"] == 1


def test_gate_enforce_links_convergent_to_the_richer_incumbent():
    incumbent = _fb("X", {"s1"}, "def", "m", source_diversity=3)  # richer
    gate = CommitDedupGate(load_committed_index(_FakeConn([_row(incumbent, "fb-inc")])), mode="enforce")
    d = gate.decide(_fb("X", {"s1"}, "def", "m"))  # identical body, leaner
    assert d["kind"] == "merge_convergent"
    assert d["action"] == "link_duplicate" and d["canonical_fb_id"] == "fb-inc"
    assert gate.receipt()["linked_duplicates"][0]["canonical_fb_id"] == "fb-inc"


def test_gate_never_links_when_the_candidate_is_richer():
    """Demoting the store's richer row is a supersession act — owner call (D-2933 rule V)."""
    incumbent = _fb("X", {"s1"}, "def", "m")  # leaner
    gate = CommitDedupGate(load_committed_index(_FakeConn([_row(incumbent, "fb-inc")])), mode="enforce")
    d = gate.decide(_fb("X", {"s1"}, "def", "m", source_diversity=3, fb_id="fb-new"))
    assert d["kind"] == "merge_convergent" and d["candidate_richer"] is True
    assert d["action"] == "insert" and d["would"] == "supersede_review"
    assert gate.receipt()["advisories"]["supersede_candidates"][0]["fb_id"] == "fb-new"


def test_gate_catches_a_collision_created_within_one_batch():
    """D-2949 #4: stage1 dedups segments, so nothing catches two rows from ONE run but the gate."""
    gate = CommitDedupGate({}, mode="enforce")
    first = _fb("X", {"s1"}, "def", "m")
    first["fb_id"] = "fb-a"
    assert gate.decide(first)["action"] == "insert"
    gate.observe(first)
    second = _fb("X", {"s1"}, "def", "m")
    second["fb_id"] = "fb-b"
    d = gate.decide(second)
    assert d["kind"] == "merge_convergent" and d["action"] == "link_duplicate"
    assert d["canonical_fb_id"] == "fb-a"


def test_gate_rejects_an_unknown_mode_fail_closed():
    with pytest.raises(ValueError):
        CommitDedupGate({}, mode="reporting")  # a typo must not become a silent no-op gate


def test_store_rows_carry_source_ids_as_json_text_and_are_not_exploded():
    """`frozenset('["s1"]')` is a set of CHARACTERS — that bug would break identity silently."""
    gate = CommitDedupGate(load_committed_index(_FakeConn([_row(_fb("X", {"s1"}, "def", "m"), "fb-inc")])),
                           mode="report")
    assert gate.stored_names == 1
    assert gate.decide(_fb("X", {"s1"}, "def", "m"))["kind"] == "merge_convergent"
    # a DIFFERENT work must stay a name collision, not a same-work group
    assert gate.decide(_fb("X", {"s2"}, "def", "m"))["kind"] == "keep_both_cross_source"


def test_receipt_advisories_agree_with_its_own_kinds_block():
    """Measured 2026-10-12 by scripts/simulate_commit_dedup_gate: the receipt filtered advisories
    by classify_group's vocabulary ('same_source_collide') while `kind` held candidate_kind's
    ('keep_both_divergent') — so it printed 0 advisories beside kinds={'keep_both_divergent': 2}.
    Two vocabularies one hop apart is the drift the DISPOSITION_* constants now prevent."""
    gate = CommitDedupGate({}, mode="report")
    inc = _fb("X", {"s1"}, "type check required fields", "check keys and data types", fb_id="fb-1")
    gate.decide(inc)
    gate.observe(inc)
    d = gate.decide(_fb("X", {"s1"}, "schema quantity unit constraints",
                        "schema membership max quantity allowed units", fb_id="fb-2"))
    assert d["kind"] == DISPOSITION_DIVERGENT
    r = gate.receipt()
    assert r["kinds"][DISPOSITION_DIVERGENT] == 1
    assert len(r["advisories"][DISPOSITION_DIVERGENT]) == 1
    assert sum(r["kinds"].values()) == r["candidates"] == 2


def test_vocabulary_constants_are_the_only_spelling_of_the_dispositions():
    """A literal would compile and silently disagree with the map (the defect above)."""
    assert DISPOSITION_MERGE == "merge_convergent"
    assert DISPOSITION_DIVERGENT == "keep_both_divergent"
    assert DISPOSITION_CROSS_SOURCE == "keep_both_cross_source"
    c = _fb("X", {"s1"}, "def", "m")
    assert candidate_kind(c, []) == "insert"
    assert candidate_kind(c, [_fb("X", {"s1"}, "def", "m")]) == DISPOSITION_MERGE
    assert candidate_kind(c, [_fb("X", {"s2"}, "def", "m")]) == DISPOSITION_CROSS_SOURCE
