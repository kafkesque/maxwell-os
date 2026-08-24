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
from pipeline.stage2_extract import _singleton_result_to_fb  # noqa: E402

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
