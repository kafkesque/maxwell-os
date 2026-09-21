"""test_axis_authority_consolidation.py — D2626: authority sets single-source-of-truth.

Locks the forensic-audit finding #2 (authority-set drift between merge and tiers):
both consumers MUST import from pipeline.axis_authority and agree on the same
post-merge authoritative sets. A future edit that adds a provenance source to one
consumer but not the shared module fails this test.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_script(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_shared_module_derives_correct_sets() -> None:
    from pipeline import axis_authority as aa

    # The post-merge authoritative sets are exactly ORIG | FILL.
    assert aa.CT_AUTH == aa.CT_ORIG | aa.CT_FILL
    assert aa.DEPTH_AUTH == aa.DP_ORIG | aa.DP_FILL
    assert aa.DISC_AUTH == aa.DISC_ORIG | aa.DISC_FILL
    assert aa.DOM_AUTH == aa.DOM_ORIG | aa.DOM_FILL

    # The pre-merge verified subset is never outside the authoritative set.
    assert aa.CT_ORIG <= aa.CT_AUTH
    assert aa.DP_ORIG <= aa.DEPTH_AUTH
    assert aa.DISC_ORIG <= aa.DISC_AUTH
    assert aa.DOM_ORIG <= aa.DOM_AUTH


def test_consumers_import_from_shared_module() -> None:
    """merge + tiers must NOT re-declare the sets inline (drift bug class)."""
    merge = _load_script(ROOT / "scripts" / "merge_4axis_adjudication.py")
    tiers = _load_script(ROOT / "scripts" / "build_4axis_tiers.py")

    assert "from pipeline.axis_authority import" in merge
    assert "from pipeline.axis_authority import" in tiers
    # Neither consumer may redefine the authoritative sets as inline literals.
    assert not re.search(r"^\s*CT_AUTH\s*=\s*frozenset", tiers, re.M)
    assert not re.search(r"^\s*DEPTH_AUTH\s*=\s*frozenset", tiers, re.M)
    assert not re.search(r"^\s*CT_ORIG\s*=\s*frozenset", merge, re.M)
    assert not re.search(r"^\s*DP_ORIG\s*=\s*frozenset", merge, re.M)


def test_guard_wired_into_s4_and_s6() -> None:
    """D2620 guard must be wired fail-closed into S4 classification + S6 commit."""
    s4 = _load_script(ROOT / "pipeline" / "stage4_merge.py")
    s6 = _load_script(ROOT / "pipeline" / "stage6_commit.py")

    assert "validate_discipline_domain" in s4
    assert "validate_discipline_domain" in s6


if __name__ == "__main__":
    test_shared_module_derives_correct_sets()
    test_consumers_import_from_shared_module()
    test_guard_wired_into_s4_and_s6()
    print("axis_authority consolidation OK")
