#!/usr/bin/env python3
"""tests/test_open_tension_strict.py — the D-2953 tier-2 tension modes (BUG-712 calibration).

WHY. `_OPEN_TENSION` (loose) fires on bare words, so an ordinary first-order predicate about a
record's SUBJECT is read as an epistemic statement about its CLAIM. Measured on 7,640 rows: 88% of
the 100 `principle -> growth_edge` moves are that error. These tests pin BOTH modes so the flag is
a measured switch rather than a hopeful one, and so the loose form cannot be re-enabled without a
failing test telling the next agent why it was narrowed.
"""

from __future__ import annotations

import pytest

from pipeline import content_types as ct


def _fb(**over: object) -> dict:
    """A minimal Stage-2-shaped record; body fields default to empty."""
    base: dict = {
        "fb_id": "fb-probe",
        "name": "Probe",
        "content_type": "principle",
        "definition": "",
        "mechanism": "",
        "boundary": "",
        "consequence": "",
        "elaboration": "",
    }
    base.update(over)
    return base


SUBJECT_MATTER = {
    "consequence": "The model may generate untraceable or contradictory information.",
    "mechanism": "Edge cases arise when the training data contains contradictory context cues.",
}
CLAIM_STATUS = {
    "mechanism": "The evidence is contested, and the causal link remains unresolved.",
}
TRUE_OPEN_QUESTION = {
    "boundary": "Whether the effect generalises beyond the sampled population is an open question.",
}


def test_the_configured_mode_is_read_loudly_and_matches_the_config() -> None:
    """C12/zero-drift: the flag is a CONFIG value, so this test binds CODE to CONFIG, not to a constant.

    It landed DISABLED (D-2953) and the owner RATIFIED it ENABLED on 2026-10-12 after the two-sided
    measurement, so a hardcoded `is False` would now pin a value the owner has overruled — and a
    hardcoded `is True` would hide a future config edit. What must never drift is the READ.
    """
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load((Path(ct.__file__).resolve().parent.parent / "config" / "content_types.yaml")
                        .read_text(encoding="utf-8"))
    assert ct.OPEN_TENSION_STRICT is bool(cfg["reroute"]["open_tension_strict"]), "code must read config"
    assert ct.OPEN_TENSION_STRICT is True, "ratified enabled by the owner 2026-10-12 (D-2953)"


def test_loose_form_fires_on_a_subject_matter_predicate() -> None:
    """The defect, pinned: 'contradictory information' is about the SUBJECT, not the claim."""
    assert ct.principle_tension_hit(_fb(**SUBJECT_MATTER), strict=False) is True


def test_strict_form_does_not_fire_on_a_subject_matter_predicate() -> None:
    """The fix, pinned: the same text must stop being read as an epistemic status."""
    assert ct.principle_tension_hit(_fb(**SUBJECT_MATTER), strict=True) is False


def test_both_forms_fire_on_a_genuine_claim_status() -> None:
    """Precision must not be bought with recall on the tier's INTENDED meaning."""
    record = _fb(**CLAIM_STATUS)
    assert ct.principle_tension_hit(record, strict=False) is True
    assert ct.principle_tension_hit(record, strict=True) is True


def test_unambiguous_constructions_survive_the_strict_form() -> None:
    """'open question' / 'unknown whether' / 'not established' stay standalone in both forms."""
    record = _fb(**TRUE_OPEN_QUESTION)
    assert ct.principle_tension_hit(record, strict=True) is True


def test_monkeypatching_the_flag_moves_the_router(monkeypatch: pytest.MonkeyPatch) -> None:
    """The router must read the mode at CALL time — a config flip cannot be frozen by import."""
    record = _fb(**SUBJECT_MATTER)
    monkeypatch.setattr(ct, "OPEN_TENSION_STRICT", True)
    assert ct.principle_tension_hit(record) is False
    assert ct.reroute_content_type(record) == "principle"
    monkeypatch.setattr(ct, "OPEN_TENSION_STRICT", False)
    assert ct.reroute_content_type(record) == "growth_edge"
