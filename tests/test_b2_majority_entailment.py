"""D2507 (B2) — cross-passage majority aggregation regression tests.

B2 weak max-entailment rule (ChatGPT B2 / MTR task 32): the OLD deberta_check used
`max(entail_scores)` so a SINGLE passage could pass an otherwise-unsupported FB, and a
single contradicting passage was ignored when max-entail cleared the threshold first.
The NEW `_b2_majority_verdict` requires a STRICT majority of clean passages to entail
(to PASS) or to contradict (to veto); otherwise NEUTRAL.

These tests exercise the pure aggregation primitive — no DeBERTa model load.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from pipeline.stage5_verify import _b2_majority_verdict


THRESH = 0.10


# ── Single passage (n=1) behaves like the old max rule ────────────────────

def test_single_passage_entail_passes():
    passed, score, detail = _b2_majority_verdict([0.7], [0.1], [0.2], THRESH)
    assert passed is True
    assert "ENTAIL" in detail


def test_single_passage_contradict_vetoes():
    passed, score, detail = _b2_majority_verdict([0.05], [0.8], [0.15], THRESH)
    assert passed is False
    assert "CONTRA" in detail


def test_single_passage_neutral_quarantines():
    passed, score, detail = _b2_majority_verdict([0.05], [0.1], [0.85], THRESH)
    assert passed is False
    assert "NEUTRAL" in detail


# ── Cross-passage majority: a single passage must NOT pass a synthesis ─────

def test_single_entail_among_many_neutral_does_not_pass():
    # 1 of 3 passages entails — the OLD max rule would PASS this; the majority rule must not.
    entail = [0.7, 0.03, 0.02]
    contra = [0.1, 0.1, 0.1]
    neutral = [0.2, 0.87, 0.88]
    passed, _, detail = _b2_majority_verdict(entail, contra, neutral, THRESH)
    assert passed is False
    assert "NEUTRAL" in detail


def test_majority_entail_passes_synthesis():
    # 2 of 3 passages entail → strict majority → PASS.
    entail = [0.7, 0.6, 0.03]
    contra = [0.1, 0.1, 0.1]
    neutral = [0.2, 0.3, 0.87]
    passed, _, detail = _b2_majority_verdict(entail, contra, neutral, THRESH)
    assert passed is True
    assert "ENTAIL" in detail


# ── Contradiction veto: a single contradicting passage cannot outvote a majority ─

def test_mixed_single_entail_single_contradict_quarantines():
    # 1 entailing + 1 contradicting passage (n=2) → NEITHER has a strict majority → NEUTRAL.
    # The OLD rule would PASS on the single entailing passage, ignoring the contradiction.
    entail = [0.7, 0.05]
    contra = [0.1, 0.8]
    neutral = [0.2, 0.15]
    passed, _, detail = _b2_majority_verdict(entail, contra, neutral, THRESH)
    assert passed is False
    assert "NEUTRAL" in detail


def test_majority_contradiction_vetoes_against_single_entail():
    # 1 entail + 2 contradict (n=3) → majority contradiction → CONTRA.
    entail = [0.7, 0.05, 0.05]
    contra = [0.1, 0.8, 0.7]
    neutral = [0.2, 0.15, 0.25]
    passed, _, detail = _b2_majority_verdict(entail, contra, neutral, THRESH)
    assert passed is False
    assert "CONTRA" in detail


# ── Score contract (backward-compatible with nli_calibrate) ───────────────

def test_score_is_max_entailment_probability():
    # The returned continuous score stays `max(entail)` for the calibration sweep.
    passed, score, _ = _b2_majority_verdict([0.05, 0.9], [0.1, 0.1], [0.85, 0.0], THRESH)
    assert score == pytest.approx(0.9)
