"""D-2748/D-2749 tier-2: a principle whose FORM is not a transferable rule is rerouted.

Pins the fail-closed contract of _principle_form_violation(): it only ever returns a
RETAINED disposition (growth_edge / process_template / quarantine), never noise_drop
(auto-DROP is owner-gated via the tier-1 adjudication map, D-2748).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.content_types import _principle_form_violation, reroute_content_type  # noqa: E402


def test_definitional_without_prescriptive_is_quarantined():
    fb = {"content_type": "principle", "definition": "A knowledge graph is a data structure that represents entities as nodes and edges."}
    assert _principle_form_violation(fb) == "quarantine"


def test_open_tension_is_growth_edge():
    fb = {"content_type": "principle", "definition": "This principle describes a contested correlation that remains unverified."}
    assert _principle_form_violation(fb) == "growth_edge"


def test_procedure_with_done_condition_is_process_template():
    fb = {"content_type": "principle", "definition": "First you collect data, then you analyze it. Repeat until convergence."}
    assert _principle_form_violation(fb) == "process_template"


def test_prescriptive_rule_passes_through():
    fb = {"content_type": "principle", "definition": "To avoid bias you should validate assumptions before scaling."}
    assert _principle_form_violation(fb) is None
    assert reroute_content_type(fb) == "principle"


def test_never_returns_noise_drop():
    # a definitional principle is HELD (quarantine), never auto-DROPPED.
    fb = {"content_type": "principle", "definition": "This concept refers to a type of memory."}
    assert _principle_form_violation(fb) != "noise_drop"
