"""BUG-737 (column 2 of 14, `elaboration`) + D-2957 — the ABSENT shape is NULL, and every reader of it must agree.

The store's absent shape was a NON-NULL BLANK while the code's contract says absent. Retiring that shape ONE
column at a time is only safe if the SAME change (a) closes the manufacturing point in the producer, so a new
run cannot reintroduce the blank, and (b) proves no reader renders the new NULL as the literal string "None" —
the failure that bit the MCP reader when `last_retrieved_at` was reshaped.

These controls FAIL if either half is lost:

  1. the PRODUCER writes NULL for an absent `elaboration` — never '' (the `_safe_str(default="")` defect);
  2. a PRESENT value survives verbatim, so the fix cannot become "blank the column";
  3. the READER renders EVERY absent shape (None and '') identically as N/A, and never the literal "None"
     (a `.get(key, default)` does not fall back on a present-but-NULL key — it prints the NULL).
"""

from __future__ import annotations

import contextlib
import io

import pytest


@pytest.fixture()
def conn(tmp_path):
    """A migrated store in a TMP DIR (tests may not write outside tmp — tests/conftest.py)."""
    from pipeline.stage6_commit import init_db

    try:
        c = init_db(tmp_path / "t.db")
    except RuntimeError as exc:  # sqlite-vec unavailable in this interpreter
        pytest.skip(f"sqlite-vec unavailable: {exc}")
    yield c
    c.close()


def _row(**overrides) -> dict:
    """A minimal row that satisfies the NOT NULL columns (content_type is a DECLARED role, D-2965).

    The disposition is STAMPED rather than hand-written: the store's own gate derives (QUARANTINE,
    s5_not_applicable) for a role that carries no factual claim (D-2942) and refuses the row otherwise —
    so these controls exercise the real writer path instead of a hand-tuned row that would bypass it.
    """
    from pipeline.stage6_commit import stamp_non_fb_disposition

    row = {"fb_id": "fb_absent_shape_1", "name": "A procedure", "definition": "A definition.",
           "content_type": "process_template"}
    row.update(overrides)
    stamp_non_fb_disposition(row)
    return row


def _stored_elaboration(conn) -> object:
    """Read the WRITTEN cell back, and report non-NULL-ness separately (the `nonnull` ruler's own reading)."""
    row = conn.execute("SELECT elaboration, count(elaboration) FROM fbs WHERE fb_id = ?",
                       ("fb_absent_shape_1",)).fetchone()
    return row[0], row[1]


# ── the producer half ────────────────────────────────────────────────────────────────────────────


def test_absent_elaboration_is_written_as_null_not_a_blank(conn):
    """Control 1: no `elaboration` key at all -> the store cell IS NULL, so count(elaboration) cannot claim it."""
    from pipeline.stage6_commit import insert_fb

    assert insert_fb(conn, _row()) is True
    value, nonnull = _stored_elaboration(conn)
    assert value is None, f"absent must be NULL, got {value!r}"
    assert nonnull == 0, "count(elaboration) must not claim a row that carries no elaboration"


def test_an_explicit_empty_string_is_also_absent_not_a_blank(conn):
    """Control 2: '' and a missing key are the SAME absence — the two shapes must not diverge in the store."""
    from pipeline.stage6_commit import insert_fb

    assert insert_fb(conn, _row(elaboration="")) is True
    value, nonnull = _stored_elaboration(conn)
    assert value is None, f"'' is absent, not a value, got {value!r}"
    assert nonnull == 0


def test_a_present_elaboration_survives_verbatim(conn):
    """Control 3: the fix must not blank the column — a written value is a value (D-2956 clause 3)."""
    from pipeline.stage6_commit import insert_fb

    body = "Edge cases and second-order effects, spelled out for the row that really carries one."
    assert insert_fb(conn, _row(elaboration=body)) is True
    value, nonnull = _stored_elaboration(conn)
    assert value == body
    assert nonnull == 1


# ── the reader half ──────────────────────────────────────────────────────────────────────────────


def _elaboration_line(fb: dict) -> str:
    """Capture the exact line the reader prints under the ELABORATION heading."""
    from pipeline.query import _print_fb_full

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        _print_fb_full(fb)
    lines = out.getvalue().splitlines()
    return lines[lines.index("  ── ELABORATION ──") + 1]


def test_reader_renders_every_absent_shape_as_na_never_the_none_string():
    """Control 4: BOTH absent shapes render as N/A — and never the literal 'None' (the last_retrieved_at bite)."""
    for absent in (None, ""):
        line = _elaboration_line({"name": "x", "elaboration": absent})
        assert line == "  N/A", f"absent {absent!r} rendered {line!r}"
        assert "None" not in line


def test_reader_renders_a_present_value_verbatim():
    """Control 5: the reader is not a blanket N/A — a real value is shown unchanged."""
    line = _elaboration_line({"name": "x", "elaboration": "a real elaboration"})
    assert line == "  a real elaboration"
