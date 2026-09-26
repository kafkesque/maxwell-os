"""Label traceability (BUG-497 / D-2640): the pre-provenance boundary is DECLARED and load-bearing.

Asserts the declared vocabulary, that the boundary is the only thing separating a legitimate
pre-boundary row from a broken stamp, and that half a stamp is never traceability.
"""

from __future__ import annotations

import pytest

from pipeline.label_traceability import (
    boundary_runs,
    load_config,
    stamp_columns,
    traceability_of,
)


def _row(**kw: object) -> dict:
    """Build a row dict with every declared stamp column empty, then apply overrides."""
    row: dict = {c: "" for c in stamp_columns()}
    row.update(kw)
    return row


def test_the_declared_vocabulary_is_complete_and_the_boundary_is_not_empty():
    cfg = load_config()
    for state in ("stamped", "pre_boundary", "missing", "unstampable"):
        assert state in cfg["states"], state
    assert boundary_runs() , "an empty boundary classifies nothing as pre_boundary"


def test_a_full_quartet_is_stamped():
    assert traceability_of(_row(menu_hash="sha", content_type_source="human_verbatim",
                                discipline_source="model", extraction_type_source="model")) == "stamped"


def test_the_boundary_is_load_bearing():
    """The ONLY difference is the declared generation run, so the boundary decides the verdict."""
    run_column = str(load_config()["run_column"])
    inside = _row(**{run_column: sorted(boundary_runs())[0]})
    outside = _row(**{run_column: "a-run-nobody-declared"})
    assert traceability_of(inside) == "pre_boundary"
    assert traceability_of(outside) == "missing"


def test_a_partial_quartet_is_never_traceability():
    run_column = str(load_config()["run_column"])
    row = {"menu_hash": "sha", run_column: "a-run-nobody-declared"}
    assert traceability_of(row) == "missing"


def test_a_row_without_the_stamp_columns_is_unstampable_not_pre_boundary():
    run_column = str(load_config()["run_column"])
    assert traceability_of({run_column: sorted(boundary_runs())[0]}) == "unstampable"


def test_a_malformed_declaration_fails_closed(tmp_path, monkeypatch):
    """C16: a boundary that cannot classify must raise, never report no findings."""
    import pipeline.label_traceability as lt

    bad = tmp_path / "label_provenance.yaml"
    bad.write_text(
        "label_provenance:\n  db: x\n  table: fbs\n  run_column: r\n"
        "  stamp_columns: [a]\n  states: {}\n  boundary: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lt, "CONFIG_PATH", bad)
    monkeypatch.setattr(lt, "_cache", None)
    with pytest.raises(ValueError):
        lt.load_config()
