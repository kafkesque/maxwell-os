"""CI test: depth-aware golden few-shot selection (D2425) + gated-ID pruning (D2421-fix).

The golden positive selector must span BOTH extraction_type (D2377) and depth (D2425),
so that adding universal/specialized golden examples actually reaches the S2 few-shot
prompt. Selection is deterministic for a given seed.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage2_extract import (
    _golden_depth,
    _golden_primary_type,
    _stratified_positive_sample,
)


def _mk(depth: str, etype: str, iid: str) -> dict:
    return {"id": iid, "expected_fb": {"depth": depth, "extraction_type": etype}}


def test_stratified_covers_types_and_depths() -> None:
    """One example per extraction_type with a distinct depth -> 4 distinct of each."""
    pos = [
        _mk("universal", "causal_mechanism", "c"),
        _mk("specialized", "descriptive_model", "d"),
        _mk("domain", "normative_heuristic", "n"),
        _mk("cross-domain", "empirical_pattern", "e"),
    ]
    picked = _stratified_positive_sample(pos, 4, 42)
    assert len(picked) == 4
    assert {_golden_primary_type(x) for x in picked} == {
        "causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern",
    }
    assert {_golden_depth(x) for x in picked} == {"universal", "specialized", "domain", "cross-domain"}


def test_depth_aware_prefers_underrepresented_depth() -> None:
    """Within a type, the least-picked depth must be surfaced (D2425 core behavior).

    causal_mechanism is dominated by cross-domain but carries a single universal; the
    depth-aware selector must surface that universal rather than always picking the
    majority cross-domain example.
    """
    pos = [_mk("cross-domain", "causal_mechanism", f"c-cd-{i}") for i in range(8)]
    pos.append(_mk("universal", "causal_mechanism", "c-univ"))
    pos += [_mk("cross-domain", "descriptive_model", "d")]
    pos += [_mk("cross-domain", "normative_heuristic", "n")]
    pos += [_mk("cross-domain", "empirical_pattern", "e")]
    picked = _stratified_positive_sample(pos, 4, 42)
    depths = [_golden_depth(x) for x in picked]
    assert "universal" in depths


def test_deterministic_selection() -> None:
    """Same seed -> same selection (stable few-shot, R7 temp=0.0 analogue)."""
    pos = [
        _mk("cross-domain", t, f"{t}{i}")
        for t in ("causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern")
        for i in range(3)
    ]
    a = _stratified_positive_sample(pos, 4, 42)
    b = _stratified_positive_sample(pos, 4, 42)
    assert [x["id"] for x in a] == [x["id"] for x in b]


if __name__ == "__main__":
    test_stratified_covers_types_and_depths()
    test_depth_aware_prefers_underrepresented_depth()
    test_deterministic_selection()
    print("golden selection tests OK")
