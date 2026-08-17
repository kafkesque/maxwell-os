"""Tests for the post-S4 enrichment stage (F1/D2400).

Pure-logic tests only — no OMLX/Ollama required. The LLM call boundaries
(`classify_procedural_skill`, `classify_fb_edge`) are exercised via monkeypatched
`call_omlx_json` so the fail-closed validation is covered without a live model.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import stage4_5_enrich as s4e


# ── _normalize_snake_case ───────────────────────────────────────────────────
def test_normalize_snake_case_basic():
    assert s4e._normalize_snake_case("Frame Price as Loss Avoidance") == "frame_price_as_loss_avoidance"


def test_normalize_snake_case_empty_and_nonstr():
    assert s4e._normalize_snake_case("") == ""
    assert s4e._normalize_snake_case(None) == ""
    assert s4e._normalize_snake_case(123) == ""


def test_normalize_snake_case_leading_digit():
    assert s4e._normalize_snake_case("2 factor auth") == "f_2_factor_auth"


def test_normalize_snake_case_collapses_underscores():
    assert s4e._normalize_snake_case("  Weird   __Spacing__ ") == "weird_spacing"


# ── prompt formatting (must not KeyError on missing optional fields) ─────────
def test_prompts_format_without_keyerror():
    fb = {"name": "X", "definition": "D", "mechanism": "M",
          "application": "A", "extraction_type": "causal_mechanism"}
    s4e.PROCEDURAL_SKILL_PROMPT.format(**{
        "name": fb["name"], "definition": fb["definition"], "mechanism": fb["mechanism"],
        "application": fb["application"], "extraction_type": fb["extraction_type"],
    })
    s4e.EDGE_PROMPT.format(
        name_a="A", definition_a="D1", mechanism_a="M1",
        name_b="B", definition_b="D2", mechanism_b="M2",
    )


def test_reasoning_off_system_prefixes_reasoning_models(monkeypatch):
    monkeypatch.setattr(s4e, "VERIFY_REASONING_OFF_MODELS", {"gpt-oss-20b-MXFP4-Q8"})
    monkeypatch.setattr(s4e, "VERIFY_REASONING_OFF_PREFIX", "Reasoning: low")
    out = s4e._reasoning_off_system("BASE", "gpt-oss-20b-MXFP4-Q8")
    assert out.startswith("Reasoning: low")
    assert "BASE" in out
    assert s4e._reasoning_off_system("BASE", "other-model") == "BASE"


# ── edge application semantics (must match retrieve.py graph_expand) ─────────
def _fb(fb_id):
    return {"fb_id": fb_id, "prerequisite_fbs": [], "contradicts_fbs": []}


def test_apply_edge_relation_a_requires_b():
    fbs = [_fb("a"), _fb("b")]
    s4e._apply_edge_relation(fbs, 0, 1, {"prerequisite": "A_requires_B", "contradicts": False})
    assert fbs[0]["prerequisite_fbs"] == ["b"]  # A requires B → B is A's prerequisite
    assert fbs[1]["prerequisite_fbs"] == []


def test_apply_edge_relation_b_requires_a():
    fbs = [_fb("a"), _fb("b")]
    s4e._apply_edge_relation(fbs, 0, 1, {"prerequisite": "B_requires_A", "contradicts": False})
    assert fbs[1]["prerequisite_fbs"] == ["a"]
    assert fbs[0]["prerequisite_fbs"] == []


def test_apply_edge_relation_contradicts_is_bidirectional():
    fbs = [_fb("a"), _fb("b")]
    s4e._apply_edge_relation(fbs, 0, 1, {"prerequisite": "none", "contradicts": True})
    assert fbs[0]["contradicts_fbs"] == ["b"]
    assert fbs[1]["contradicts_fbs"] == ["a"]


# ── fail-closed classification (C16) via monkeypatched LLM ──────────────────
def test_classify_procedural_skill_missing_key_raises(monkeypatch):
    def fake_json(**kwargs):
        return {"not_the_key": "x"}
    monkeypatch.setattr(s4e, "call_omlx_json", fake_json)
    with pytest.raises(ValueError):
        s4e.classify_procedural_skill({"name": "X", "definition": "D", "mechanism": "M",
                                       "application": "A", "extraction_type": "causal_mechanism"})


def test_classify_procedural_skill_valid(monkeypatch):
    def fake_json(**kwargs):
        return {"procedural_skill": "Frame Price as Loss Avoidance"}
    monkeypatch.setattr(s4e, "call_omlx_json", fake_json)
    out = s4e.classify_procedural_skill({"name": "X", "definition": "D", "mechanism": "M",
                                         "application": "A", "extraction_type": "causal_mechanism"})
    assert out == "frame_price_as_loss_avoidance"


def test_classify_fb_edge_invalid_prerequisite_raises(monkeypatch):
    def fake_json(**kwargs):
        return {"prerequisite": "A_does_something_weird", "contradicts": False}
    monkeypatch.setattr(s4e, "call_omlx_json", fake_json)
    with pytest.raises(ValueError):
        s4e.classify_fb_edge({"name": "A", "definition": "D1", "mechanism": "M1"},
                             {"name": "B", "definition": "D2", "mechanism": "M2"})


def test_classify_fb_edge_non_bool_contradicts_raises(monkeypatch):
    def fake_json(**kwargs):
        return {"prerequisite": "none", "contradicts": "true"}
    monkeypatch.setattr(s4e, "call_omlx_json", fake_json)
    with pytest.raises(ValueError):
        s4e.classify_fb_edge({"name": "A", "definition": "D1", "mechanism": "M1"},
                             {"name": "B", "definition": "D2", "mechanism": "M2"})
