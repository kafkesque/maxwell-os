"""Serving gate (D274a / G17): status is a function of the verification record.

Asserts the pure derivation logic and the CI invariant: a PASS row must carry
factual.passed=True and a non-negative s5_reason; a label can never determine
status.
"""

from __future__ import annotations

import json

import pytest

from pipeline.serving_gate import (
    assert_invariant,
    derive_status,
    negative_reasons,
)


def _vr(detail: str, passed: bool) -> str:
    """Build a verification_results JSON string with a single factual check."""
    return json.dumps([
        {"check_name": "mechanism_quality", "passed": True, "score": 1.0, "detail": "Mechanism quality OK"},
        {"check_name": "factual", "passed": passed, "score": 0.9, "detail": detail},
    ])


@pytest.mark.parametrize(
    ("detail", "passed", "expected_status", "expected_reason"),
    [
        ("ENTAIL (majority 1/1): ent=1.00 max=0.99", True, "PASS", "entail"),
        ("NEUTRAL (ent 0/1, cont 0/1): max=0.01", False, "QUARANTINE", "neutral"),
        ("CONTRA (majority 1/1): ent=0.00 cont=1.00", False, "QUARANTINE", "contra"),
        ("All 1 evidence passages are non-evidence fragments — QUARANTINE (no clean premise for NLI)",
         False, "QUARANTINE", "no_evidence"),
        ("MECH FAIL: Mechanism contains tautological pattern 'because it can' — restates definition rather than explaining causal chain. QUARANTINE.",
         False, "QUARANTINE", "mech_fail"),
        ("MECH FAIL: Mechanism too short (139 chars < 150) — likely vacuous. QUARANTINE.",
         False, "QUARANTINE", "vacuous"),
        ("BUG-181#1: evidence_passages carry EPUB→MD conversion artifacts — QUARANTINE (no NLI)",
         False, "QUARANTINE", "evidence_contaminated"),
    ],
)
def test_derive_status(detail, passed, expected_status, expected_reason):
    status, reason = derive_status(_vr(detail, passed))
    assert status == expected_status
    assert reason == expected_reason


def test_missing_factual_fails_closed():
    status, reason = derive_status(json.dumps([]))
    assert status == "QUARANTINE"
    assert reason == "unknown"


def test_malformed_json_fails_closed():
    status, reason = derive_status("not-json")
    assert status == "QUARANTINE"
    assert reason == "unknown"


def test_pass_invariant_holds_for_entail():
    assert_invariant("PASS", _vr("ENTAIL (majority 1/1): ent=1.00", True), "entail")


def test_invariant_rejects_pass_with_false_factual():
    with pytest.raises(AssertionError):
        assert_invariant("PASS", _vr("NEUTRAL (ent 0/1, cont 0/1)", False), "neutral")


def test_invariant_rejects_pass_with_negative_reason():
    # Belt-and-suspenders: even if factual.passed were True, a negative reason must not pass.
    with pytest.raises(AssertionError):
        assert_invariant("PASS", _vr("CONTRA (majority 1/1): cont=1.00", True), "contra")


def test_quarantine_is_unconstrained():
    # A verified-but-hidden row (the 0a bug) is still QUARANTINE; no invariant fires.
    assert_invariant("QUARANTINE", _vr("ENTAIL (majority 1/1): ent=1.00", True), "entail")


def test_negative_reasons_exclude_entail_and_neutral():
    neg = negative_reasons()
    assert "contra" in neg
    assert "entail" not in neg
    assert "neutral" not in neg  # neutral is passed=False but not a "negative" verdict


def test_duplicate_hard_quarantine_overrides_verification():
    # A duplicate is never served, even when its verification passed (D2627 / D-271d).
    status, reason = derive_status(
        _vr("ENTAIL (majority 1/1): ent=1.00", True), duplicate_of="canon-fb-id"
    )
    assert status == "QUARANTINE"
    assert reason == "duplicate"
