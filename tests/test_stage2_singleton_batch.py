"""Tests for batched singleton extraction (D2xxx, option-1 speedup).

Covers the shared helpers used by both the per-singleton and batched singleton
paths in process_singletons:
  - _map_batch_results: alignment of a batched JSON-array LLM response.
  - _singleton_result_to_fb: LLM-result -> FB conversion (NULL/gate/valid).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage2_extract import _map_batch_results, _singleton_result_to_fb

ITEM = {
    "text": "A 300-char passage about some method or concept that is long enough.",
    "source_book": "Test Book",
    "segment_id": "seg123",
    "singleton": {"cluster_id": "singleton_0", "source_books": ["Test Book"], "source_ids": ["b1"]},
}


def test_map_perfect_array():
    raw = [{"index": 1, "name": "A"}, {"index": 2, "name": "B"}, {"index": 3, "name": "C"}, {"index": 4, "name": "D"}]
    out = _map_batch_results(raw, 4)
    assert [o["name"] for o in out] == ["A", "B", "C", "D"]


def test_map_reordered_by_index():
    raw = [{"index": 3, "name": "C"}, {"index": 1, "name": "A"}, {"index": 4, "name": "D"}, {"index": 2, "name": "B"}]
    out = _map_batch_results(raw, 4)
    assert [o["name"] for o in out] == ["A", "B", "C", "D"]


def test_map_short_array_leaves_none():
    raw = [{"index": 1, "name": "A"}]
    out = _map_batch_results(raw, 4)
    assert out[0]["name"] == "A"
    assert out[1] is None and out[2] is None and out[3] is None


def test_map_single_dict():
    out = _map_batch_results({"name": "Only"}, 4)
    assert out[0]["name"] == "Only"
    assert out[1] is None


def test_map_empty_and_garbage():
    assert _map_batch_results([], 3) == [None, None, None]
    assert _map_batch_results(None, 3) == [None, None, None]


def test_map_positional_without_index():
    raw = [{"name": "P1"}, {"name": "P2"}]
    out = _map_batch_results(raw, 2)
    assert [o["name"] for o in out] == ["P1", "P2"]


def test_singleton_result_valid():
    result = {
        "name": "Test Principle", "definition": "A sufficiently long definition that passes the 30-char check.",
        "mechanism": "m", "boundary": "b", "consequence": "c", "elaboration": "e",
        "is_summary": False, "extraction_type": "causal_mechanism", "content_type": "principle", "route": "FB",
    }
    fb = _singleton_result_to_fb(result, ITEM, gate_enabled=True)
    assert fb is not None and "_null" not in fb and "_gate" not in fb
    assert fb["content_type"] == "principle"
    assert fb["source_segments"] == ["seg123"]
    assert fb["is_singleton_fb"] is True


def test_singleton_result_null():
    assert _singleton_result_to_fb({"route": "NULL"}, ITEM, True) == {"_null": True}


def test_singleton_result_short_definition():
    r = {"name": "X", "definition": "too short", "route": "FB"}
    assert _singleton_result_to_fb(r, ITEM, True) == {"_null": True}


def test_singleton_result_gated_summary():
    r = {"name": "S", "definition": "A sufficiently long definition that passes the check.", "is_summary": True,
         "extraction_type": "descriptive_model", "content_type": "principle", "route": "FB"}
    assert _singleton_result_to_fb(r, ITEM, True) == {"_gate": True}


def test_singleton_result_non_principle_not_gated():
    r = {"name": "PT", "definition": "A sufficiently long definition that passes the check.", "is_summary": True,
         "extraction_type": "normative_heuristic", "content_type": "process_template", "route": "FB",
         "trigger": "t", "steps": ["s1"]}
    fb = _singleton_result_to_fb(r, ITEM, True)
    assert fb is not None and "_gate" not in fb
    assert fb["content_type"] == "process_template"
    assert fb["steps"] == ["s1"]


# ── D2457 — code-detection (PT-vs-TI disambiguation) ──────────────────────
def test_detect_code_r_import():
    from pipeline.stage2_extract import detect_code_in_text
    r = 'import data into R: setwd("C:/x") dir() data<-read.csv("p.csv") View(data)'
    assert detect_code_in_text(r) is True


def test_detect_code_human_method_not_code():
    from pipeline.stage2_extract import detect_code_in_text
    human = 'organize a fruit party: invite guests, buy fruit, set up tables, serve drinks'
    assert detect_code_in_text(human) is False


def test_code_role_guard_reclassifies_empty_pt():
    from pipeline.stage2_extract import _code_role_guard
    ev = 'import data into R: setwd("C:/x") dir() data<-read.csv("p.csv") View(data)'
    result = {
        "content_type": "process_template", "steps": [], "name": "R Data Import",
        "definition": "A workflow to import data into R for analysis",
        "mechanism": "setwd then read.csv then View", "boundary": "applies to R",
        "consequence": "data loaded",
    }
    ct, body, flag = _code_role_guard("process_template", result, ev)
    assert flag is True
    assert ct == "tool_instruction"
    assert body["tool_name"] == "R"


def test_code_role_guard_preserves_populated_pt():
    from pipeline.stage2_extract import _code_role_guard
    ev = 'organize a fruit party: invite guests, buy fruit'
    result = {"content_type": "process_template", "steps": ["invite guests", "buy fruit"], "name": "Fruit Party"}
    ct, body, flag = _code_role_guard("process_template", result, ev)
    assert flag is False
    assert ct == "process_template"


def test_code_hint_empty_without_code():
    from pipeline.stage2_extract import _code_hint
    assert _code_hint("a plain principle about design systems") == ""
