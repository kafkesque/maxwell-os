"""D2449: content-type schema conformance against config/content_types.yaml.

Guards two things so the D2449 alignment cannot silently regress:
  1. The single-source golden set's `expected_fb` for all 5 content types
     (principle / process_template / process_instance / tool_instruction /
     growth_edge) conforms to the S2 contract (shared core_body + PRINCIPLE-ONLY
     elaboration + per-type s2_body_fields + valid classification labels).
  2. The singleton builder (`_singleton_result_to_fb`) emits the same conforming
     S2 contract for each content type (no forked-schema drift).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts.audit_content_type_contract import audit_golden, audit_s2, _load_ontology  # noqa: E402
from pipeline.stage2_extract import _capture_type_specific_fields, _singleton_result_to_fb  # noqa: E402
from pipeline.stamp import stamp_record  # noqa: E402

_ITEM = {
    "text": "A passage long enough to satisfy the singleton minimum-length check and provide evidence.",
    "source_book": "Test Book (Author Name).md",
    "segment_id": "seg1",
    "singleton": {"cluster_id": "singleton_0", "source_books": ["Test Book (Author Name).md"], "source_ids": ["s1"]},
}

# One well-formed LLM result per content type.
_RESULTS = {
    "principle": {
        "name": "Compounding Gains", "definition": "Small improvements compound because each gain builds on the previous one.",
        "mechanism": "Each increment raises the baseline.", "boundary": "Applies when gains are retained.",
        "consequence": "Marginal improvement yields outsized results.", "elaboration": "The curve is flat at first then diverges.",
        "is_summary": False, "extraction_type": "causal_mechanism", "content_type": "principle", "route": "FB",
    },
    "process_template": {
        "name": "Pilot Memory Protocol", "definition": "A repeatable three-step method for managing critical information under pressure.",
        "mechanism": "Externalizing offloads memory.", "boundary": "Applies under time pressure.",
        "consequence": "Retention improves.", "elaboration": "",
        "is_summary": False, "extraction_type": "normative_heuristic", "content_type": "process_template", "route": "FB",
        "trigger": "Under time pressure", "prerequisite": "", "steps": ["write down", "enter into equipment", "remember selectively"],
        "done_condition": "All items externalized", "failure_mode": "Items cannot be externalized",
    },
    "process_instance": {
        "name": "Oxford Street Con", "definition": "A concrete case study of a confidence trick executed at a London cafe.",
        "mechanism": "The scam delayed the victim's realization.", "boundary": "A specific executed instance.",
        "consequence": "Demonstrates how quickly theft completes.", "elaboration": "",
        "is_summary": False, "extraction_type": "descriptive_model", "content_type": "process_instance", "route": "FB",
        "instance_text": "Researchers ran a scam at a cafe.", "actors": ["researcher", "accomplice", "mark"],
        "outcome_metric": "", "outcome_qualitative": "Victim realized after thief left", "domain_context": "theft",
    },
    "tool_instruction": {
        "name": "FAISS read_index", "definition": "Load a persisted FAISS vector index from a file so it can be reused.",
        "mechanism": "read_index deserializes a saved index file.", "boundary": "Applies to saved FAISS indexes.",
        "consequence": "Avoids rebuilding the index.", "elaboration": "",
        "is_summary": False, "extraction_type": "normative_heuristic", "content_type": "tool_instruction", "route": "FB",
        "tool_name": "faiss", "platform": "Python", "description": "Load a persisted index",
        "syntax": "faiss.read_index(path)", "parameters": [{"name": "path", "type": "str", "description": "file path"}],
        "output": "the index object", "example": "faiss.read_index('i.index')", "caveats": "Fails on bad path",
    },
    "growth_edge": {
        "name": "Temporary Mind-Blindness", "definition": "A speculative open question whether mind-blindness can be temporary.",
        "mechanism": "Poses a correlation, no causal chain.", "boundary": "Unresolved hypothesis.",
        "consequence": "Would reframe mind-blindness as a state.", "elaboration": "",
        "is_summary": False, "extraction_type": "empirical_pattern", "content_type": "growth_edge", "route": "FB",
        "body": "Whether mind-blindness could be temporary.", "category": "neuroscience hypothesis",
        "actionable": False, "status": "open", "priority": "medium",
    },
}


def test_golden_set_conforms_to_ontology():
    onto = _load_ontology()
    results, ok = audit_golden(onto)
    assert ok, f"golden set has S2-contract violations: {results}"


def test_singleton_builder_conforms_per_type():
    onto = _load_ontology()
    for ct, result in _RESULTS.items():
        fb = _singleton_result_to_fb(dict(result), _ITEM, gate_enabled=True)
        assert fb is not None and "_null" not in fb and "_gate" not in fb, f"{ct}: builder returned {fb}"
        issues: list[str] = []
        audit_s2(fb, ct, onto, issues)
        assert not issues, f"{ct}: singleton builder violates S2 contract: {issues}"


def test_omitted_s2_body_fields_get_typed_placeholders():
    """D2452 regression guard — the "31-missing-parameters / 45-missing-outcome_metric"
    stale-artifact class (BUG-169 follow-up).

    Root cause was `_capture_type_specific_fields` dropping absent/empty fields
    (`if val is None: continue` + `if val:` string/list guards) at commit 01f4ad3.
    D2452 changed it to ALWAYS emit a typed placeholder (`[]`/`False`/`""`) so the
    per-type s2_body_fields can never be missing again, regardless of what the
    model omits. This test pins that guarantee at both the unit and the singleton
    integration level — a future regression that reintroduces the drop re-fails here.
    """
    # tool_instruction with the `parameters` key ABSENT (model omitted it)
    ti = _capture_type_specific_fields(
        {"tool_name": "faiss", "platform": "Python", "description": "load index",
         "syntax": "read_index(path)", "output": "index", "example": "x", "caveats": ""},
        "tool_instruction",
    )
    assert "parameters" in ti, "parameters key must always be present (D2452)"
    assert ti["parameters"] == [], f"omitted parameters must default to [] — got {ti['parameters']!r}"

    # process_instance with the `outcome_metric` key ABSENT (model omitted it)
    pi = _capture_type_specific_fields(
        {"instance_text": "x", "actors": ["a"], "outcome_qualitative": "y", "domain_context": "z"},
        "process_instance",
    )
    assert "outcome_metric" in pi, "outcome_metric key must always be present (D2452)"
    assert pi["outcome_metric"] == "", f"omitted outcome_metric must default to '' — got {pi['outcome_metric']!r}"

    # Singleton integration: a tool_instruction result with `parameters` omitted must
    # still land on the final record (builder must not re-drop the placeholder).
    result = {
        "name": "FAISS read_index", "definition": "Load a persisted FAISS vector index from a file.",
        "mechanism": "deserializes a saved index file", "boundary": "saved indexes only",
        "consequence": "avoids rebuilding the index", "elaboration": "",
        "is_summary": False, "extraction_type": "normative_heuristic",
        "content_type": "tool_instruction", "route": "FB",
        "tool_name": "faiss", "platform": "Python", "description": "load index",
        "syntax": "read_index(path)", "output": "index", "example": "x", "caveats": "",
        # `parameters` intentionally omitted
    }
    fb = _singleton_result_to_fb(dict(result), _ITEM, gate_enabled=True)
    assert fb is not None and "_null" not in fb and "_gate" not in fb, f"builder returned {fb}"
    assert "parameters" in fb, "singleton builder must persist parameters even when the model omits it"
    assert fb["parameters"] == [], f"got {fb['parameters']!r}"


def test_d2475_principle_only_skeleton_not_required_for_non_principle():
    """D2475 — mechanism/boundary/consequence are PRINCIPLE-ONLY.

    A non-principle record that OMITS the causal skeleton must still conform to the
    S2 contract (the old shared-skeleton contract wrongly required it — the source of
    the "9 TI skeleton" false positives). A principle that omits them MUST be flagged.
    """
    onto = _load_ontology()

    # tool_instruction with NO mechanism/boundary/consequence (only name/definition
    # shared skeleton + full per-type s2_body_fields).
    ti = {
        "name": "FAISS read_index", "definition": "Load a persisted FAISS vector index from a file.",
        "elaboration": "", "is_summary": False,
        "extraction_type": "normative_heuristic", "content_type": "tool_instruction", "route": "FB",
        "tool_name": "faiss", "platform": "Python", "description": "Load a persisted index",
        "syntax": "faiss.read_index(path)", "parameters": [{"name": "path", "type": "str", "description": "file path"}],
        "output": "the index object", "example": "faiss.read_index('i.index')", "caveats": "Fails on bad path",
    }
    ti_issues: list[str] = []
    audit_s2(ti, "tool_instruction", onto, ti_issues)
    assert not ti_issues, f"non-principle without causal skeleton must conform (D2475): {ti_issues}"

    # principle with mechanism/boundary/consequence OMITTED must be flagged.
    p = {
        "name": "Compounding Gains", "definition": "Small improvements compound.",
        "elaboration": "The curve diverges over time.", "is_summary": False,
        "extraction_type": "causal_mechanism", "content_type": "principle", "route": "FB",
    }
    p_issues: list[str] = []
    audit_s2(p, "principle", onto, p_issues)
    assert p_issues, f"principle missing mechanism/boundary/consequence must be flagged: {p_issues}"
    assert any("principle-only" in i for i in p_issues), p_issues


def test_d2476_classify_model_stamp():
    """D2476 — classify_model stamp is distinct from gen_model and principle-only.

    stamp_record must emit classify_model ONLY when passed (S4 classifier), and must
    NOT emit it when omitted (S2-side generation).
    """
    stamped = stamp_record({}, gen_model="Qwen3-Coder-30B", classify_model="gpt-oss-20b")
    assert stamped["classify_model"] == "gpt-oss-20b", stamped.get("classify_model")
    assert stamped["gen_model"] == "Qwen3-Coder-30B"

    unstamped = stamp_record({}, gen_model="Qwen3-Coder-30B")
    assert "classify_model" not in unstamped, "classify_model must be absent when None (S2 generation)"
