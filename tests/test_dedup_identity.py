"""tests/test_dedup_identity.py — D-2950 deterministic dedup identity unit tests."""
from pipeline.dedup_identity import (
    classify_group,
    is_divergent,
    jaccard,
    normalize_name,
    seq_ratio,
    source_set,
)


def test_normalize_name_folds_case_diacritics_punct():
    assert normalize_name("  Item Validation  Protocol! ") == "item validation protocol"
    assert normalize_name("VJ Performance Méthod") == "vj performance method"


def test_same_source_divergent_bodies_are_same_source_collide():
    members = [
        {
            "source_ids": frozenset({"s1"}),
            "definition": "type check required fields",
            "mechanism": "check keys and data types",
        },
        {
            "source_ids": frozenset({"s1"}),
            "definition": "schema quantity unit constraints",
            "mechanism": "schema membership max quantity allowed units",
        },
    ]
    assert is_divergent(members)
    assert classify_group(members) == "same_source_collide"


def test_same_source_convergent_bodies_are_merge():
    members = [
        {"source_ids": frozenset({"s1"}), "definition": "validate item fields", "mechanism": "check required keys"},
        {"source_ids": frozenset({"s1"}), "definition": "validate item fields", "mechanism": "check required keys"},
    ]
    assert not is_divergent(members)
    assert classify_group(members) == "merge"


def test_multi_source_is_name_collide():
    members = [
        {"source_ids": frozenset({"s1"}), "definition": "d", "mechanism": "m"},
        {"source_ids": frozenset({"s2"}), "definition": "d", "mechanism": "m"},
    ]
    assert classify_group(members) == "name_collide"


def test_no_source_is_no_source():
    members = [
        {"source_ids": frozenset(), "definition": "d", "mechanism": "m"},
        {"source_ids": frozenset(), "definition": "d", "mechanism": "m"},
    ]
    assert classify_group(members) == "no_source"


def test_single_is_unique():
    assert classify_group([{"source_ids": frozenset({"s1"}), "definition": "d", "mechanism": "m"}]) == "unique"


def test_jaccard_bounds():
    assert jaccard("a b c", "a b c") == 1.0
    assert jaccard("a b c", "x y z") == 0.0
    assert 0.0 <= jaccard("a b", "b c") <= 1.0


def test_seq_ratio_bounds():
    assert seq_ratio("same", "same") == 1.0
    assert 0.0 <= seq_ratio("same", "different") <= 1.0


# ── D-2951 hardening: order independence, work identity by overlap, shape of source cells ──

def test_divergence_is_pairwise_so_row_order_cannot_change_the_verdict():
    """The pre-D-2951 form compared members[0] vs members[1] and ignored the rest."""
    a = {"source_ids": frozenset({"s1"}), "definition": "alpha beta gamma", "mechanism": "one two three"}
    b = {"source_ids": frozenset({"s1"}), "definition": "alpha beta gamma", "mechanism": "one two three"}
    # convergent with A, divergent with BOTH A and the group's tail
    c = {"source_ids": frozenset({"s1"}), "definition": "zeta eta theta iota",
         "mechanism": "four five six seven"}
    assert is_divergent([a, b]) is False
    assert is_divergent([a, b, c]) is True
    assert is_divergent([c, a, b]) is True  # same group, different order -> same verdict
    assert classify_group([a, b, c]) == "same_source_collide"


def test_same_work_is_decided_by_source_OVERLAP_not_set_equality():
    """Row A {s1} and row B {s1, s2} are the SAME work with different convergence evidence."""
    members = [
        {"source_ids": frozenset({"s1"}), "definition": "same body", "mechanism": "same mech"},
        {"source_ids": frozenset({"s1", "s2"}), "definition": "same body", "mechanism": "same mech"},
    ]
    assert classify_group(members) == "merge"


def test_one_blank_source_fails_the_group_closed_to_review():
    """A row with unknown provenance may not be merged on its neighbour's source (C16)."""
    members = [
        {"source_ids": frozenset({"s1"}), "definition": "d", "mechanism": "m"},
        {"source_ids": frozenset(), "definition": "d", "mechanism": "m"},
    ]
    assert classify_group(members) == "no_source"


def test_source_set_normalizes_json_text_lists_and_blank():
    """The store holds JSON TEXT; `frozenset(text)` would explode it into characters."""
    assert source_set('["s1", "s2"]') == frozenset({"s1", "s2"})
    assert source_set(["s1"]) == frozenset({"s1"})
    assert source_set(frozenset({"s1"})) == frozenset({"s1"})
    assert source_set("") == frozenset()
    assert source_set(None) == frozenset()
    assert source_set("s1") == frozenset({"s1"})  # a bare id, not JSON
    assert source_set('["s1"]') != frozenset('["s1"]')
