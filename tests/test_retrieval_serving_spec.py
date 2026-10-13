"""Executable contract for specs/retrieval_serving.spec.md.

The machine runner (pytest) is the grader. Do NOT edit a test to make it pass unless the
SPEC changes (R5: generator != verifier; R7: temp=0 on the runner). A local LLM may draft
a spec/test; the runner is the grade.
"""
from pathlib import Path

import pytest

import pipeline.retrieve as retrieve
from pipeline.pipeline_paths import CANONICAL_RUN

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "retrieval_queries.yaml"


def _load_goldens():
    import yaml

    return yaml.safe_load(GOLDEN_PATH.read_text())["queries"]


def test_golden_set_pinned_to_canonical_run():
    """INV-1 (BUG-710): goldens must live in the served run, never a superseded one."""
    queries = _load_goldens()
    assert queries, "golden set is empty"
    for q in queries:
        assert q["verified_run"] == CANONICAL_RUN, (
            f"golden {q['query']!r} pinned to {q['verified_run']!r}, expected {CANONICAL_RUN!r}"
        )


def test_golden_anchors_are_names():
    """INV-1 (D-2939): the anchor is a NAME; the id is resolved per run."""
    for q in _load_goldens():
        assert q.get("expected_names"), f"golden {q['query']!r} has no expected_names"


def test_every_pool_leg_pins_to_canonical_run():
    """INV-2 (D-2881): each pool leg filters pipeline_run_id and binds CANONICAL_RUN."""
    import inspect

    for name in ("search_keyword", "search_fts", "search_vector"):
        src = inspect.getsource(getattr(retrieve, name))
        assert "pipeline_run_id" in src, f"{name} does not filter pipeline_run_id"
        assert "CANONICAL_RUN" in src, f"{name} does not bind CANONICAL_RUN"


def test_ranking_signal_is_not_a_dead_constant():
    """INV-3 (D-2537): the ranking ORDER BY must use a non-degenerate signal.

    The dead fallback is `ORDER BY borp_score DESC` — borp_score is retired debt (constant
    0.0, nothing writes it). Correct: _rank_sql() references confidence_score (D-2537), and
    that signal must VARY across served PASS rows. Red before the config flip; green after.
    """
    # Code-level: the rank clause must not be the dead borp_score fallback.
    rank_sql = retrieve._rank_sql()
    assert "borp_score" not in rank_sql, f"ranking still falls back to dead borp_score: {rank_sql!r}"
    assert "confidence_score" in rank_sql, f"ranking does not use confidence_score: {rank_sql!r}"

    # Data-level: the effective signal must vary across served PASS rows.
    conn = retrieve.get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*), COUNT(DISTINCT confidence_score) FROM fbs "
            "WHERE pipeline_run_id = ? AND status = 'PASS'",
            (CANONICAL_RUN,),
        ).fetchone()
    finally:
        conn.close()
    n, distinct_vals = row[0], row[1]
    assert distinct_vals > 1, (
        f"effective ranking signal (confidence_score) is constant: {distinct_vals} distinct "
        f"across {n} served PASS rows"
    )
