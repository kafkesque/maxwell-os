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
    content_types_without_factual_claim,
    derive_epistemic_status,
    derive_status,
    load_label_config,
    negative_reasons,
    pre_write_verdict,
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


# ── BUG-499: the epistemic label is CO-DERIVED, and its rule has ONE home ────────────────────────
# The module docstring above says "a label can never determine status" - but until BUG-499 nothing
# tested the label at all: its rule lived as three inline copies (stage 5 + two scripts), with no
# config and no single home. These tests pin the one home and the co-derivation.

def test_label_rule_is_declared_in_config_and_names_only_its_vocabulary():
    """C12/C21: the rule is config-declared and can only name declared labels (fail-closed)."""
    cfg = load_label_config()
    assert set(cfg["vocabulary"]) == {
        "corroborated", "source-supported", "cross-source-unverified", "speculative",
    }
    assert len(cfg["rules"]) == 4
    assert {r["label"] for r in cfg["rules"]} <= set(cfg["vocabulary"])
    assert cfg["fallback"] in cfg["vocabulary"]


@pytest.mark.parametrize(
    ("passed", "rating", "expected"),
    [
        (True, "strong", "corroborated"),
        (True, "medium", "source-supported"),
        (True, "weak", "source-supported"),
        (False, "strong", "cross-source-unverified"),
        (False, "medium", "cross-source-unverified"),
        (False, "weak", "speculative"),
        (False, None, "speculative"),
    ],
)
def test_label_derives_from_the_same_record(passed, rating, expected):
    assert derive_epistemic_status(passed, rating) == expected


def test_label_refines_status_so_the_1_to_1_is_a_theorem_not_a_gate():
    """BUG-499: every label implies exactly ONE status, and the label is strictly finer."""
    labels: dict[str, set[str]] = {}
    per_status: dict[str, set[str]] = {}
    for passed in (True, False):
        for rating in ("weak", "medium", "strong"):
            label = derive_epistemic_status(passed, rating)
            status, _reason = derive_status(_vr("ENTAIL (majority 1/1): ent=1.00", passed))
            labels.setdefault(label, set()).add(status)
            per_status.setdefault(status, set()).add(label)
    assert all(len(v) == 1 for v in labels.values()), labels
    assert any(len(v) > 1 for v in per_status.values()), per_status


def test_a_label_outside_the_derivation_is_detectable():
    """The teeth: the label is a FUNCTION of the record, so a hand-set label cannot match."""
    assert derive_epistemic_status(True, "weak") != "corroborated"
    assert derive_epistemic_status(False, "strong") != "speculative"


def _fb(status: str, reason: str, detail: str = "ENTAIL (majority 1/1): ent=1.00",
        passed: bool = True, **extra: object) -> dict:
    """Build a stage-5/6-shaped row dict for the pre-write guard."""
    row: dict = {"fb_id": "fb_test", "status": status, "s5_reason": reason,
                 "verification_results": _vr(detail, passed)}
    row.update(extra)
    return row


def test_pre_write_guard_accepts_a_row_its_record_derives():
    ok, complaint = pre_write_verdict(_fb("PASS", "entail"))
    assert ok, complaint


def test_pre_write_guard_refuses_a_status_the_record_does_not_derive():
    """D274a writer half: a hand-set or label-derived status can never reach the store."""
    ok, complaint = pre_write_verdict(_fb("PASS", "entail", detail="CONTRA 3/3", passed=False))
    assert not ok and "STATUS_MISMATCH" in complaint


def test_pre_write_guard_refuses_a_pass_row_carrying_a_negative_reason():
    ok, complaint = pre_write_verdict(_fb("PASS", "contra"))
    assert not ok and "REASON_MISMATCH" in complaint


def test_pre_write_guard_refuses_an_unverifiable_row_instead_of_guessing():
    ok, complaint = pre_write_verdict({"fb_id": "x", "status": "PASS", "s5_reason": "entail",
                                       "verification_results": "[]"})
    assert not ok and "UNDECIDABLE" in complaint


def test_pre_write_guard_accepts_the_declared_duplicate_quarantine():
    ok, complaint = pre_write_verdict(_fb("QUARANTINE", "duplicate", duplicate_of="fb_canon"))
    assert ok, complaint


# ── D-2942 (D2590): the THIRD disposition — a non-principle role carries NO NLI factual claim ────
# Three invariants: (1) an absent record on a role WITHOUT a factual claim derives
# s5_not_applicable, NEVER undecidable and NEVER PASS; (2) the writer guard accepts the declared
# not-applicable disposition and refuses a non-principle PASS; (3) the config declares EXACTLY the
# four roles (a 5th would silently change the gate's partition — C12 fail-closed).

def test_d2942_absent_record_on_non_principle_is_not_applicable_not_unknown():
    """S5 verifies truth claims; a PT/PI/TI/GE has none, so 'no record' is DERIVABLE, not undecidable."""
    for role in ("process_template", "process_instance", "tool_instruction", "growth_edge"):
        status, reason = derive_status(json.dumps([]), content_type=role)
        assert status == "QUARANTINE", (role, status)
        assert reason == "s5_not_applicable", (role, reason)


def test_d2942_absent_record_on_principle_is_still_unknown():
    """A principle carries a factual claim; an absent record is still undecidable (fallback)."""
    status, reason = derive_status(json.dumps([]), content_type="principle")
    assert (status, reason) == ("QUARANTINE", "unknown")


def test_d2942_non_principle_role_can_never_pass_without_a_record():
    """NEVER PASS: an unverified non-principle row must not read as verified (R5/D2298)."""
    for role in ("process_template", "process_instance", "tool_instruction", "growth_edge"):
        status, _reason = derive_status(json.dumps([]), content_type=role)
        assert status != "PASS", role


def test_d2942_config_declares_exactly_the_four_roles_without_factual_claim():
    """A role added/removed from the list is a gate-partition change, caught here (C12)."""
    assert content_types_without_factual_claim() == frozenset(
        {"process_template", "process_instance", "tool_instruction", "growth_edge"}
    )


def test_d2942_writer_guard_accepts_the_declared_not_applicable_disposition():
    """The one writer may persist QUARANTINE + s5_not_applicable for a routed non-principle row."""
    ok, complaint = pre_write_verdict(_fb(
        "QUARANTINE", "s5_not_applicable", detail="", passed=False,
        content_type="process_template", verification_results=json.dumps([]),
    ))
    assert ok, complaint


def test_d2942_writer_guard_refuses_a_non_principle_pass():
    """A non-principle row can never carry status=PASS (the invariant's writer half)."""
    ok, complaint = pre_write_verdict(_fb(
        "PASS", "entail", detail="ENTAIL (majority 1/1): ent=1.00", passed=True,
        content_type="process_template", verification_results=json.dumps([]),
    ))
    assert not ok and complaint
# ── BUG-502")[1].join(["