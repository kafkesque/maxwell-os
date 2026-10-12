"""tests/test_s5_score_axis_write_scope.py - D-2970 / BUG-745: the score axis is WRITTEN as an axis.

WHY THIS FILE EXISTS
--------------------
`confidence_score` and `needs_human_review` are ONE rule with TWO outputs
(pipeline/serving_gate.py::derive_conf_and_review, BUG-502). The verification-scoped commit
(D-2933 rule V) declared only the SECOND half in `stage6.s5_owned_columns`, so the D-2822
re-verification rewrote the record of all 6,591 rows and left 2,247 confidences derived from the
SUPERSEDED aggregation (BUG-745, measured by A/B against the pre-re-verification store).

The defect was not a wrong value - it was a WRITE SCOPE that could split an axis. These controls pin
the scope, the coercer, the preflight refusal and the two READERS (the rail and the repair script) so
that the same split cannot return silently, and so that the rail and the repair cannot drift apart.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from pipeline.pipeline_paths import S6_S5_AXIS_COLUMNS, S6_S5_OWNED_COLUMNS
from pipeline.serving_gate import content_types_without_factual_claim, validate_s5_axis_scope
from pipeline.stage6_commit import S5_COLUMN_COERCERS, _coerce_s5_value

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str) -> Any:
    """Load a scripts/ module by path (scripts/ is not a package, and these modules run top-level code)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader, f"cannot load {rel}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rail = _load("check_s5_score_axis_mod", "scripts/check_s5_score_axis.py")
repair = _load("repair_s5_score_axis_mod", "scripts/repair_s5_score_axis.py")

NO_CLAIM_ROLE = sorted(content_types_without_factual_claim())[0]


def _row(conf: float, review: bool) -> dict[str, Any]:
    """A claim-carrying row whose score axis is fully evaluable (enrichment grade 1.0)."""
    results = [
        {"check_name": "mechanism_quality", "passed": True, "score": 1.0, "detail": "d"},
        {"check_name": "factual", "passed": True, "score": 0.9, "detail": "d" * 60},
    ]
    return {
        "fb_id": "a" * 64,
        "content_type": "principle",
        "application": "a" * 60,
        "failure_mode": "b" * 60,
        "definition": "c" * 60,
        "boundary": "d" * 60,
        "verification_results": json.dumps(results),
        "isor": json.dumps({"score": 0.667, "rating": "moderate"}),
        "confidence_score": conf,
        "needs_human_review": review,
    }


def _derived() -> tuple[float, bool]:
    out = repair.derive_axis(_row(0.0, False))
    assert out is not None, "the fixture must be evaluable"
    return out


def test_the_declared_write_scope_carries_the_whole_score_axis() -> None:
    """The split of BUG-745 is the assertion: every declared axis must be complete in the scope."""
    assert S6_S5_AXIS_COLUMNS.get("score_axis"), "the score axis must be DECLARED (config, C12)"
    for axis, columns in S6_S5_AXIS_COLUMNS.items():
        missing = [c for c in columns if c not in S6_S5_OWNED_COLUMNS]
        assert not missing, f"axis {axis!r} is written only partially: {missing} is not in s5_owned_columns"
    assert "confidence_score" in S6_S5_OWNED_COLUMNS and "needs_human_review" in S6_S5_OWNED_COLUMNS


def test_every_declared_s5_owned_column_has_a_declared_coercer() -> None:
    """A column written without a declared storage shape is refused at runtime - prove it cannot happen."""
    undeclared = [c for c in S6_S5_OWNED_COLUMNS if c not in S5_COLUMN_COERCERS]
    assert not undeclared, f"s5_owned_columns {undeclared} have no declared coercer"


def test_confidence_score_is_coerced_to_a_number_and_absence_stays_absent() -> None:
    """A score is a NUMBER or the declared ABSENCE - never the string '0.9' and never 0.0."""
    coerced = _coerce_s5_value("confidence_score", 0.9332)
    assert isinstance(coerced, float) and coerced == 0.9332
    assert _coerce_s5_value("confidence_score", None) is None


def test_the_stage6_preflight_refuses_a_scope_that_splits_a_declared_axis() -> None:
    """The WRITER half: half an axis is refused before any row is touched (C16)."""
    axes = {"score_axis": ("confidence_score", "needs_human_review")}
    with pytest.raises(RuntimeError, match="split truth"):
        validate_s5_axis_scope(("confidence_score", "status"), axes)
    with pytest.raises(RuntimeError, match="split truth"):
        validate_s5_axis_scope(("needs_human_review",), axes)
    validate_s5_axis_scope(("confidence_score", "needs_human_review"), axes)  # whole axis: allowed
    validate_s5_axis_scope(("status",), axes)  # neither half: not this rule's subject


def test_the_rail_reads_a_no_factual_claim_role_as_a_declared_absence() -> None:
    """D-2942: an absent axis on a claim-free role is DERIVABLE; a VALUE there is never a pass."""
    absent = {"content_type": NO_CLAIM_ROLE, "verification_results": json.dumps([]),
              "confidence_score": None, "needs_human_review": False}
    assert rail.verdict_for(absent)[0] == rail.NOT_APPLICABLE
    assert rail.verdict_for({**absent, "confidence_score": 0.9})[0] == rail.UNDECIDABLE
    assert rail.verdict_for({**absent, "content_type": "principle"})[0] == rail.UNDECIDABLE


def test_the_repair_never_writes_a_role_whose_axis_is_declared_absent() -> None:
    """The repair's population is DECLARED (D-2960): a claim-free role is reported, never written."""
    rows = [
        {"fb_id": "b" * 64, "content_type": NO_CLAIM_ROLE, "verification_results": json.dumps([]),
         "confidence_score": 0.9, "needs_human_review": False},
        {"fb_id": "c" * 64, "content_type": NO_CLAIM_ROLE, "verification_results": json.dumps([]),
         "confidence_score": None, "needs_human_review": False},
    ]
    buckets = repair.classify(rows, content_types_without_factual_claim())
    assert not buckets["stale"], "a claim-free role must never enter the repair population"
    assert len(buckets["no_claim_value"]) == 1 and len(buckets["no_claim_ok"]) == 1


def test_the_rail_and_the_repair_agree_on_the_same_row() -> None:
    """One rule, two readers (C21): a stale row must be STALE to the repair and a MISMATCH to the rail."""
    conf, review = _derived()
    stale = _row(round(conf + 0.01, 4), review)
    assert rail.verdict_for(dict(stale))[0] == rail.SCORE_MISMATCH
    assert len(repair.classify([dict(stale)], content_types_without_factual_claim())["stale"]) == 1
    clean = _row(conf, review)
    assert rail.verdict_for(dict(clean))[0] == rail.MATCH
    assert len(repair.classify([dict(clean)], content_types_without_factual_claim())["stale"]) == 0
