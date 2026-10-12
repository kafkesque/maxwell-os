"""tests/test_stage6_duplicate_marker.py — D-2951: the marker WRITE is real, not declared.

BUG-726 was a claim the code could not keep: the schema comment said duplicate_of is "NULL
otherwise" while `_safe_str` wrote '' on every row, so the predicate D-271d documents
(`duplicate_of IS NULL`) matched ZERO rows. These tests exercise the REAL insert path against
the REAL schema, and assert that the pair the dedup gate writes is the pair the serving rail
re-derives (`store_verdict`, D274a) — i.e. the writer half and the rail half of BUG-502 agree.
"""
import sqlite3

from pipeline.serving_gate import MATCH, derive_status, store_verdict
from pipeline.stage6_commit import CREATE_FBS_TABLE, insert_fb

CANON = "b" * 64
ROLE_WITHOUT_FACTUAL_CLAIM = "tool_instruction"  # D-2942: no NLI claim, so no record is CORRECT


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(CREATE_FBS_TABLE)
    return conn


def _fb(fb_id: str, **extra) -> dict:
    fb = {
        "fb_id": fb_id,
        "name": "Marker Contract Probe",
        "definition": "A probe row that exercises the duplicate_of write path.",
        "domains": ["emerging"],
        "discipline": "software engineering",
        "content_type": ROLE_WITHOUT_FACTUAL_CLAIM,
        "depth": "specialized",
        "verification_results": [],
    }
    fb.update(extra)
    return fb


def _marker(conn: sqlite3.Connection, fb_id: str) -> tuple:
    return conn.execute(
        "SELECT duplicate_of, typeof(duplicate_of) FROM fbs WHERE fb_id = ?", (fb_id,)
    ).fetchone()


def test_absent_marker_is_stored_as_NULL_not_empty_string():
    """The whole of BUG-726: '' made the documented predicate match zero rows."""
    conn = _conn()
    fb = _fb("a" * 64)
    fb["status"], fb["s5_reason"] = derive_status(None, content_type=ROLE_WITHOUT_FACTUAL_CLAIM)
    assert insert_fb(conn, fb) is True
    assert _marker(conn, fb["fb_id"]) == (None, "null")


def test_link_marker_is_stored_and_the_serving_rail_re_derives_the_same_pair():
    """D-2951: a linked duplicate carries duplicate_of + QUARANTINE/'duplicate' (D2627)."""
    conn = _conn()
    fb = _fb("c" * 64, duplicate_of=CANON)
    fb["status"], fb["s5_reason"] = derive_status(None, duplicate_of=CANON)
    assert (fb["status"], fb["s5_reason"]) == ("QUARANTINE", "duplicate")
    assert insert_fb(conn, fb) is True
    assert _marker(conn, fb["fb_id"]) == (CANON, "text")
    verdict, detail = store_verdict(
        fb["status"], fb["s5_reason"], fb["verification_results"],
        duplicate_of=CANON, content_type=ROLE_WITHOUT_FACTUAL_CLAIM,
    )
    assert verdict == MATCH, detail


def test_marker_survives_the_ordinary_row_path_unmarked():
    """A row with no marker must not acquire one (the gate only marks what it links)."""
    conn = _conn()
    first = _fb("d" * 64, duplicate_of=CANON)
    first["status"], first["s5_reason"] = derive_status(None, duplicate_of=CANON)
    assert insert_fb(conn, first) is True
    second = _fb("e" * 64)
    second["status"], second["s5_reason"] = derive_status(None, content_type=ROLE_WITHOUT_FACTUAL_CLAIM)
    assert insert_fb(conn, second) is True
    assert _marker(conn, second["fb_id"]) == (None, "null")
    assert conn.execute("SELECT COUNT(*) FROM fbs WHERE duplicate_of IS NOT NULL").fetchone()[0] == 1
