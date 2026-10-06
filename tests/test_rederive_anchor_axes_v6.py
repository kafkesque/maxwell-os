"""tests/test_rederive_anchor_axes_v6.py — control tests for the D-2820 re-derivation harness.

Proves the pure, inference-free surface: pin drift guard, D-274d stamp builder, owner-adjudication
fail-closed semantics (unadjudicated / off-menu), manifest assembly, and BUG-650 guard acceptance.
No LLM and no DeBERTa inference are exercised here (those stages are owner-gated).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.rederive_anchor_axes_v6 import (  # noqa: E402
    ABSTENTION,
    apply_owner_decisions,
    build_cell_stamp,
    finalize_manifest,
    validate_on_menu,
)

PINS = {
    "composite": "c" * 64,
    "answer_space": "a" * 64,
    "frozen_composite": "f" * 64,
    "frozen_answer": "g" * 64,
}


def _row(i: int) -> dict:
    return {
        "item_id": f"R{i:03d}",
        "name": f"name{i}",
        "definition": "def",
        "mechanism": "mech",
        "boundary": "bound",
        "consequence": "cons",
        "source_text": "src",
    }


def test_stamp_carries_all_d274d_fields() -> None:
    s = build_cell_stamp(
        pins=PINS, taxonomy_version="v5.7", anchor_version="v6", coder="owner",
        second_coder="gemma", date="2026-10-05T00:00:00+00:00",
        discipline_abstained=False, domains_abstained=True,
    )
    for field in ("anchor_version", "menu_hash", "taxonomy_version", "coder", "date", "abstention"):
        assert field in s and s[field], f"missing D-274d field {field}"
    assert s["menu_hash"] == PINS["composite"]
    assert s["answer_space_hash"] == PINS["answer_space"]
    assert s["abstention"] == ABSTENTION
    assert s["discipline_abstained"] is False and s["domains_abstained"] is True


def test_adjudicate_requires_every_row() -> None:
    rows = [_row(0), _row(1)]
    decisions = {"R000": {"discipline": "physics", "domains": ["ai & agents"]}}
    with pytest.raises(SystemExit):
        apply_owner_decisions(rows, decisions)


def test_adjudicate_rejects_unknown_id() -> None:
    rows = [_row(0)]
    decisions = {"R999": {"discipline": "physics", "domains": ["ai & agents"]}}
    with pytest.raises(SystemExit):
        apply_owner_decisions(rows, decisions)


def test_adjudicate_applies_owner_labels() -> None:
    rows = [_row(0), _row(1)]
    decisions = {
        "R000": {"discipline": "physics", "domains": ["ai & agents"]},
        "R001": {"discipline": ABSTENTION, "domains": [ABSTENTION]},
    }
    out = apply_owner_decisions(rows, decisions)
    assert out[0]["discipline"] == "physics"
    assert out[0]["discipline_source"] == "owner_finalized"
    assert out[1]["discipline"] == ABSTENTION


def test_validate_on_menu_fails_closed_off_menu() -> None:
    menu = {"disciplines": ["physics"], "domains": ["ai & agents"]}
    good = [{**_row(0), "discipline": "physics", "domains": ["ai & agents"]}]
    validate_on_menu(good, menu)  # must not raise
    bad = [{**_row(0), "discipline": "alchemy", "domains": ["ai & agents"]}]
    with pytest.raises(SystemExit):
        validate_on_menu(bad, menu)


def test_manifest_passes_bug650_guard() -> None:
    from pipeline.anchor_menu_guard import referee_menu_v6_verdict
    from scripts.rederive_anchor_axes_v6 import load_pins

    rows = [{**_row(0), "discipline": "physics", "domains": ["ai & agents"],
             "discipline_source": "owner_finalized", "domain_source": "owner_finalized"}]
    # The BUG-650 guard reads the REAL live pins from config, so the manifest under test
    # must be stamped with the real pins for the guard to accept it.
    real_pins = load_pins()
    manifest = finalize_manifest(
        finalized=rows, pins=real_pins, taxonomy_version="v5.7", anchor_version="v6",
        coder="owner", second_coder="gemma",
    )
    assert manifest["menu_hash"] == real_pins["composite"]
    assert manifest["answer_space_hash"] == real_pins["answer_space"]
    assert manifest["total"] == 1
    v = referee_menu_v6_verdict(manifest, label="test.json", axis="discipline")
    assert v["ok"], f"guard rejected: {v['reason']}"
    assert not v["frozen_hits"]
