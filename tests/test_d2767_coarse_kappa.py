"""test_d2767_coarse_kappa.py — BUG-690 part 1 regression.

The D-2767 C+B gate (D-2884) needs BOTH the fine 62-way kappa AND the coarse 3-way
macro kappa. d2767_ab_eval.py used to report only the fine kappa (BUG-690 part 1).
This test pins two things:

  (a) the deterministic fine->3-way collapse covers the corrected closed_menu_v8
      ontology — including the 'Business & Management' group that the v5-built map
      missed (BUG-690 part 2) — and never folds 'emerging';
  (b) d2767_ab_eval.coarse_report emits a coarse_kappa/coarse_pass, not only fine.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import d2767_ab_eval  # noqa: E402
from discipline_conformance_gate import cohen_kappa  # noqa: E402
from discipline_macro_classify import load_macro, to_macro  # noqa: E402


def test_macro_collapse_covers_all_v8_groups():
    """BUG-690 part 2 regression: every v8 group maps; Business & Management included."""
    scheme, bucket_members, disc_to_bucket = load_macro()
    assert scheme == "3-way"
    # load_macro() also keys 'emerging' (empty-group disciplines collect there); the three
    # real macro buckets must all be present with members.
    assert {"Technical", "Human & Design", "Method & Business"} <= set(bucket_members.keys())
    # The v5-built map was missing 'Business & Management' (first in v6) -> UNMAPPED rows.
    assert to_macro("business administration", disc_to_bucket) == "Method & Business"
    assert to_macro("entrepreneurship studies", disc_to_bucket) == "Method & Business"
    assert to_macro("marketing", disc_to_bucket) == "Method & Business"


def test_macro_collapse_known_disciplines():
    _, _, disc_to_bucket = load_macro()
    assert to_macro("machine learning", disc_to_bucket) == "Technical"
    assert to_macro("neuroscience", disc_to_bucket) == "Human & Design"
    assert to_macro("strategic thinking", disc_to_bucket) == "Method & Business"
    # emerging / off-menu -> explicit routing bucket, never folded into a macro.
    assert to_macro("emerging", disc_to_bucket) == "emerging"
    assert to_macro("bogus-discipline", disc_to_bucket) == "emerging"


def test_coarse_collapse_is_deterministic_and_identity_preserving():
    _, _, disc_to_bucket = load_macro()
    gold = ["machine learning", "neuroscience", "strategic thinking", "emerging"]
    cg = d2767_ab_eval.coarse_collapse(gold, disc_to_bucket)
    assert cg == ["Technical", "Human & Design", "Method & Business", "emerging"]
    cp = d2767_ab_eval.coarse_collapse(gold, disc_to_bucket)
    assert cp == cg
    assert cohen_kappa(cg, cp) == 1.0


def test_coarse_report_shape_and_pass_flag():
    _, _, disc_to_bucket = load_macro()
    gold = ["machine learning", "neuroscience"]
    pred = ["machine learning", "strategic thinking"]
    rep = d2767_ab_eval.coarse_report(gold, pred, 0.73)
    assert rep["scheme"] == "3-way"
    assert rep["n"] == 2
    assert "coarse_kappa" in rep
    assert "coarse_pass" in rep
    assert rep["coarse_floor"] == 0.73
    # one agreement, one cross-bucket disagreement -> kappa < 1.0, not passing 0.73.
    assert rep["coarse_kappa"] < 1.0
    assert rep["coarse_pass"] is False
