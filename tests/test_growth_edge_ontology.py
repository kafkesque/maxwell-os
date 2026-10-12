"""Contract tests for the D-2924 growth_edge category ontology + loader."""

from __future__ import annotations


def test_ge_category_vocabulary_closed() -> None:
    from pipeline.growth_edge_ontology import category_values, validate_category

    vals = category_values()
    assert "open_tension" in vals
    assert "capability_gap" in vals
    assert "emerging" in vals
    # all 4 grounded values present
    assert {"open_tension", "unverified_correlation", "contested_claim", "capability_gap"} <= vals
    for v in ("open_tension", "unverified_correlation", "contested_claim", "capability_gap", "emerging"):
        assert validate_category(v) == v


def test_ge_category_fail_closed_on_off_vocab() -> None:
    from pipeline.growth_edge_ontology import validate_category

    try:
        validate_category("aerospace engineering")
        assert False, "expected SystemExit on off-vocabulary category"
    except SystemExit:
        pass


def test_ge_tags_closed_bootstrap() -> None:
    from pipeline.growth_edge_ontology import tag_values, validate_tags

    vals = tag_values()
    assert {"extraction", "retrieval", "orchestration", "emerging"} <= vals
    assert validate_tags(["extraction", "retrieval"]) == ["extraction", "retrieval"]


def test_ge_calibration_advisory_by_default() -> None:
    from pipeline.growth_edge_ontology import calibration_decision, calibration_enforcing

    assert calibration_enforcing() is False
    assert calibration_decision() is None
