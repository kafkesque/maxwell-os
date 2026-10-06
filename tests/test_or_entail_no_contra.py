"""D-2822 (Gate A(d)) — OR-entail + AND-no-contradiction aggregation regression tests.

D-2822 replaces the D2507/B2 strict-majority rule with the correct ontological semantics:
a convergent FB is VERIFIED only when the evidence set OR-entails the claim (at least ONE
clean passage entails) AND no passage contradicts it (AND-no-contra: ZERO contradicting
passages). The majority rule can HIDE a supported claim (a single strong entailment buried
under neutral passages) and can PASS a claim carrying both entailment and contradiction.

These tests exercise the pure aggregation primitive — no DeBERTa model load.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline.stage5_verify import (
    NLI_AGGREGATION,
    _aggregate_verdict,
    _or_entail_and_no_contra_verdict,
)


THRESH = 0.10


# ── OR-entail: one clean entailing passage is sufficient ──────────────────

def test_single_entail_alone_passes():
    passed, score, detail = _or_entail_and_no_contra_verdict([0.7], [0.1], [0.2], THRESH)
    assert passed is True
    assert "ENTAIL" in detail


def test_single_entail_among_neutral_passes():
    # 1 of 3 passages entails, 0 contradict — the majority rule FAILS this (hides the claim);
    # OR-entail + AND-no-contra must PASS it.
    entail = [0.7, 0.03, 0.02]
    contra = [0.1, 0.1, 0.1]
    neutral = [0.2, 0.87, 0.88]
    passed, _, detail = _or_entail_and_no_contra_verdict(entail, contra, neutral, THRESH)
    assert passed is True
    assert "ENTAIL" in detail


# ── AND-no-contradiction: a single contradicting passage vetoes ───────────

def test_entail_with_single_contra_vetoes():
    # 1 entailing + 1 contradicting passage → contradiction vetoes despite the entailment.
    entail = [0.7, 0.05]
    contra = [0.1, 0.8]
    neutral = [0.2, 0.15]
    passed, _, detail = _or_entail_and_no_contra_verdict(entail, contra, neutral, THRESH)
    assert passed is False
    assert "CONTRA" in detail


def test_many_entail_with_one_contra_vetoes():
    # 2 entailing + 1 contradicting → the contradiction vetoes; the claim is NOT verified.
    entail = [0.7, 0.6, 0.05]
    contra = [0.1, 0.1, 0.8]
    neutral = [0.2, 0.3, 0.15]
    passed, _, detail = _or_entail_and_no_contra_verdict(entail, contra, neutral, THRESH)
    assert passed is False
    assert "CONTRA" in detail


# ── No entail → QUARANTINE ─────────────────────────────────────────────────

def test_no_entail_quarantines():
    entail = [0.03, 0.02, 0.05]
    contra = [0.1, 0.1, 0.1]
    neutral = [0.87, 0.88, 0.85]
    passed, _, detail = _or_entail_and_no_contra_verdict(entail, contra, neutral, THRESH)
    assert passed is False
    assert "NEUTRAL" in detail


# ── Score contract (backward-compatible with nli_calibrate) ───────────────

def test_score_is_max_entailment_probability():
    passed, score, _ = _or_entail_and_no_contra_verdict([0.05, 0.9], [0.1, 0.1], [0.85, 0.0], THRESH)
    assert score == pytest.approx(0.9)


# ── Config dispatch: default stays majority (no silent behavior change) ───

def test_config_owned_aggregation_mode():
    # The aggregation mode is a config-first value, not a hardcoded literal (C12).
    assert NLI_AGGREGATION in ("majority", "or_entail_and_no_contra")


def test_dispatch_default_majority_preserves_b2():
    # With 'majority' (current default), the single-entail-among-neutral case must still FAIL
    # (the D2507/B2 behavior) so no behavior change leaks in before recalibration.
    entail = [0.7, 0.03, 0.02]
    contra = [0.1, 0.1, 0.1]
    neutral = [0.2, 0.87, 0.88]
    passed, _, _ = _aggregate_verdict(entail, contra, neutral, THRESH)
    if NLI_AGGREGATION == "majority":
        assert passed is False
    else:
        assert passed is True
