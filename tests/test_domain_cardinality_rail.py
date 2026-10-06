"""D-2838 / BUG-631 writer-limb control: the domain cardinality rail must be SEEN to fire.

A rail that nothing runs is a comment (D-2816 verification requirement). These tests
import the helper directly (no OMLX needed) and prove: (1) a within-cap label set is
unchanged and stays CLEAN; (2) a 7-label set is truncated to the cap with a receipt and
degraded CLEAN -> FALLBACK; (3) a pre-degraded row is never re-labelled CLEAN; (4) the
detector still flags the over-cap before the helper enforces it.
"""
from __future__ import annotations

from pipeline.pipeline_paths import MAX_DOMAINS_PER_FB as CFG_CAP
from pipeline.stage4_merge import (
    MAX_DOMAINS_PER_FB,
    _enforce_domain_cardinality,
    validate_classification,
)


def test_cap_value_is_config_owned():
    # C12: the cap is config-owned (pipeline.max_domains_per_fb), never hardcoded here.
    # Both the pipeline-path reader and the schema reader resolve from the same YAML.
    assert MAX_DOMAINS_PER_FB == CFG_CAP
    assert isinstance(MAX_DOMAINS_PER_FB, int) and MAX_DOMAINS_PER_FB > 0


def test_within_cap_is_noop_and_stays_clean():
    cd = {"classification_status": "CLEAN"}
    out = _enforce_domain_cardinality(["graphic design", "branding"], cd)
    assert out == ["graphic design", "branding"]
    assert cd["classification_status"] == "CLEAN"
    assert "classification_error" not in cd


def test_over_cap_truncates_with_receipt_and_degrades():
    cd = {"classification_status": "CLEAN"}
    out = _enforce_domain_cardinality(["a", "b", "c", "d", "e", "f", "g"], cd)
    assert out == ["a", "b", "c", "d", "e"]
    assert cd["classification_status"] == "FALLBACK"
    assert "7>5" in cd["classification_error"]
    assert "dropped ['f', 'g']" in cd["classification_error"]


def test_predegraded_row_not_relabelled_clean():
    cd = {
        "classification_status": "FALLBACK",
        "classification_error": "depth: invalid raw_depth",
    }
    out = _enforce_domain_cardinality(["a", "b", "c", "d", "e", "f"], cd)
    assert len(out) == MAX_DOMAINS_PER_FB
    assert cd["classification_status"] == "FALLBACK"
    assert "depth: invalid raw_depth" in cd["classification_error"]
    assert "truncated to cap" in cd["classification_error"]


def test_detector_flags_over_cap_before_enforcement():
    # The detector (validate_classification) is the trigger; the helper is the enforce.
    result = {
        "discipline": "physics",
        "domains": ["a", "b", "c", "d", "e", "f", "g"],
        "depth": "domain",
        "evidence": "cited",
    }
    is_valid, errors = validate_classification(result)
    assert not is_valid
    assert any("Too many domains" in e for e in errors)
