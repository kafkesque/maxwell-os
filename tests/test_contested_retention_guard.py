"""D-2747 retention guard: a `contested` record is NEVER noise_drop'd / quarantined.

The guard lives in pipeline/content_types.reroute_content_type() and fires FIRST
(before tier-1 adjudication, tier-2 keyword denylist, tier-3 structural) so no other
rule can silently drop a contested/unfalsifiable record. This test pins that contract
so a future edit cannot regress the D-2747 ruling (conspiracy = growth_edge ROLE +
contested retention flag, NOT a 6th content_type).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.content_types import reroute_content_type, _is_contested  # noqa: E402


def test_contested_noise_drop_reroutes_to_growth_edge():
    fb = {"content_type": "noise_drop", "contested": True, "fb_id": "f1"}
    assert reroute_content_type(fb) == "growth_edge"


def test_contested_quarantine_reroutes_to_growth_edge():
    fb = {"content_type": "quarantine", "contested": True, "fb_id": "f1"}
    assert reroute_content_type(fb) == "growth_edge"


def test_contested_principle_is_not_touched():
    # a principle is a role, not a disposition; the guard only rescues drops/quarantines.
    fb = {"content_type": "principle", "contested": True, "fb_id": "f1"}
    assert reroute_content_type(fb) == "principle"


def test_uncontested_noise_drop_is_unchanged():
    fb = {"content_type": "noise_drop", "contested": False, "fb_id": "f1"}
    assert reroute_content_type(fb) == "noise_drop"


def test_is_contested_truthy_strings():
    for v in ("1", "true", "yes", "contested", "TRUE"):
        assert _is_contested({"contested": v}) is True, v
    for v in ("0", "false", "no", "", "   "):
        assert _is_contested({"contested": v}) is False, v


def test_is_contested_absent_is_false():
    assert _is_contested({"fb_id": "f1"}) is False
