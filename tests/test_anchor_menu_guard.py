"""test_anchor_menu_guard.py — control tests for the BUG-650 / D-2839 pre-A/B guard.

Proves the fail-closed anchor-referee guard fires on every invalid state and
passes only a genuinely menu-v6-stamped anchor. The pins are read from
config/menu_axis_hashes.yaml (single source) so the test never hardcodes a hash.
"""
from __future__ import annotations

import pytest

from pipeline.anchor_menu_guard import (
    load_menu_v6_pins,
    referee_menu_v6_verdict,
    assert_referee_menu_v6,
)


@pytest.fixture(scope="module")
def pins() -> dict[str, str]:
    return load_menu_v6_pins()


def _live_anchor(pins: dict[str, str]) -> dict:
    return {
        "menu_hash": pins["composite_hash_live"],
        "answer_space_sha256": pins["answer_space_hash"],
    }


def test_pins_are_present_and_distinct(pins):
    live = {pins["composite_hash_live"], pins["answer_space_hash"]}
    frozen = {pins["composite_hash_frozen_pin"], pins["answer_space_hash_frozen_pin"]}
    assert len(live) == 2 and len(frozen) == 2
    assert live.isdisjoint(frozen)  # live != frozen is the whole point of the guard


def test_no_stamp_refuses(pins):
    v = referee_menu_v6_verdict({}, label="anchor.json", axis="discipline")
    assert v["ok"] is False
    assert "NO menu stamp" in v["reason"]
    with pytest.raises(SystemExit) as e:
        assert_referee_menu_v6({}, label="anchor.json", axis="discipline")
    assert "FAIL-CLOSED" in str(e.value)


def test_frozen_v5_composite_refuses(pins):
    doc = {"menu_hash": pins["composite_hash_frozen_pin"]}
    v = referee_menu_v6_verdict(doc, label="key.json", axis="discipline")
    assert v["ok"] is False
    assert v["frozen_hits"] == [pins["composite_hash_frozen_pin"]]
    assert "FROZEN" in v["reason"]


def test_frozen_v5_answer_space_refuses(pins):
    doc = {"answer_space_sha256": pins["answer_space_hash_frozen_pin"]}
    v = referee_menu_v6_verdict(doc, label="manifest.json", axis="domains")
    assert v["ok"] is False
    assert pins["answer_space_hash_frozen_pin"] in v["frozen_hits"]


def test_live_stamp_passes(pins):
    v = referee_menu_v6_verdict(_live_anchor(pins), label="re-derived.json", axis="discipline")
    assert v["ok"] is True
    assert v["live_hits"]


def test_live_composite_only_passes(pins):
    # A re-derived anchor may stamp only the composite (menu_hash). It matches the
    # live pin, so the guard certifies it (D-2839 criterion #1: matches menu v6).
    v = referee_menu_v6_verdict(
        {"menu_hash": pins["composite_hash_live"]}, label="x.json", axis="discipline"
    )
    assert v["ok"] is True


def test_unknown_stamp_refuses(pins):
    v = referee_menu_v6_verdict(
        {"menu_hash": "deadbeef" * 8}, label="x.json", axis="discipline"
    )
    assert v["ok"] is False
    assert "NEITHER" in v["reason"]


def test_frozen_wins_over_live_when_both_present(pins):
    # A manifest that stamps BOTH live and frozen is inconsistent -> refuse.
    doc = {
        "menu_hash": pins["composite_hash_live"],
        "answer_space_sha256": pins["answer_space_hash_frozen_pin"],
    }
    v = referee_menu_v6_verdict(doc, label="x.json", axis="discipline")
    assert v["ok"] is False
    assert v["frozen_hits"] == [pins["answer_space_hash_frozen_pin"]]


def test_provenance_nested_stamp_is_found(pins):
    doc = {"_provenance": {"menu_hash": pins["composite_hash_frozen_pin"]}}
    v = referee_menu_v6_verdict(doc, label="x.json", axis="discipline")
    assert v["ok"] is False
    assert v["frozen_hits"] == [pins["composite_hash_frozen_pin"]]
