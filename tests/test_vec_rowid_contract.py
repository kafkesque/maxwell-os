#!/usr/bin/env python3
"""tests/test_vec_rowid_contract.py - the vec store is keyed by ROWID, not by count.

BUG-387/D-359 regression test. The D2185 completeness check compared COUNTS, so a
store where the fbs spine had been re-rowided and vec_fbs had doubled printed
"Vector: READY 15990/7995" while 7995 index entries were already dead.

Under test: the rowid churn that INSERT OR REPLACE INTO fbs causes on a re-commit
(the fbs PK is the TEXT fb_id, so REPLACE deletes + re-inserts and the implicit
rowid MOVES). The previous rowid's vector must be retired in the same transaction,
and the completeness assertion must be ROWID-level, not a count.

Runs under pytest AND directly (python3 tests/test_vec_rowid_contract.py). That
second path exists because vec0 needs enable_load_extension, which the python.org
framework build lacks (BUG-104) - so pytest skips here while the homebrew
interpreter, which CAN load vec0 but has no pytest, runs the real assertions.
A skip is never a pass, and the file prints its own skip reason.
"""
from __future__ import annotations

import sqlite3
import struct
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.stage6_commit import (  # noqa: E402
    assert_vector_integrity,
    delete_embedding,
    fbs_rowid,
)

_DIM = 512


class _Skip(Exception):
    """sqlite-vec cannot load here (BUG-104) - a skip, never a silent pass."""


def _open(tmp: Path) -> sqlite3.Connection:
    """A minimal fbs + vec0 store. Skips when vec0 cannot load (BUG-104).

    The schema is deliberately minimal: these tests exercise stage6's ROWID
    helpers, not the 75-column FB contract (that is test_vector_dim_contract_d2509).
    """
    conn = sqlite3.connect(tmp / "vec_contract.db")
    try:
        conn.enable_load_extension(True)
        import sqlite_vec

        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except Exception as e:
        conn.close()
        reason = f"sqlite-vec unavailable (BUG-104: {e})"
        try:
            import pytest  # noqa: F401
        except ImportError:
            raise _Skip(reason) from None
        pytest.skip(reason)
    conn.execute("CREATE TABLE fbs (fb_id TEXT PRIMARY KEY, name TEXT, definition TEXT)")
    conn.execute(
        "CREATE VIRTUAL TABLE vec_fbs USING vec0("
        "rowid INTEGER PRIMARY KEY, definition_embedding float[512])"
    )
    return conn


def _db() -> sqlite3.Connection:
    return _open(Path(tempfile.mkdtemp(prefix="vec_contract_")))


def _vec(seed: float) -> bytes:
    """Deterministic 512d float32 blob (dimension contract D2509)."""
    return struct.pack(f"{_DIM}f", *([seed] * _DIM))


def _seed(conn: sqlite3.Connection, fb_id: str) -> int:
    """INSERT OR REPLACE a row and return the rowid it now holds."""
    conn.execute(
        "INSERT OR REPLACE INTO fbs (fb_id, name, definition) VALUES (?, ?, ?)",
        (fb_id, "name " + fb_id, "definition " + fb_id),
    )
    rid = fbs_rowid(conn, fb_id)
    assert rid is not None
    return rid


def test_replace_moves_the_rowid_precondition() -> None:
    """The defect's precondition: REPLACE re-issues the rowid."""
    conn = _db()
    try:
        first, second = _seed(conn, "FB-1"), _seed(conn, "FB-1")
        assert first != second, "REPLACE no longer moves the rowid - re-derive BUG-387"
    finally:
        conn.close()


def test_recommit_retires_the_previous_rowid() -> None:
    """The commit loop's repair: stale vector retired, new rowid keyed, no orphans."""
    conn = _db()
    try:
        conn.execute(
            "INSERT INTO vec_fbs(rowid, definition_embedding) VALUES (?, ?)",
            (_seed(conn, "FB-1"), _vec(0.1)),
        )
        ok, msg = assert_vector_integrity(conn)
        assert ok and "READY 1/1" in msg, msg

        stale = fbs_rowid(conn, "FB-1")
        new = _seed(conn, "FB-1")  # re-commit of the SAME fb_id
        assert stale != new
        assert delete_embedding(conn, stale) is True
        conn.execute(
            "INSERT INTO vec_fbs(rowid, definition_embedding) VALUES (?, ?)",
            (new, _vec(0.2)),
        )
        ok, msg = assert_vector_integrity(conn)
        assert ok, msg
        assert "READY 1/1" in msg, msg
        assert conn.execute("SELECT COUNT(*) FROM vec_fbs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0] == 1
    finally:
        conn.close()


def test_delete_embedding_is_idempotent() -> None:
    """Deleting an absent rowid is a no-op, not an error (repair must be repeatable)."""
    conn = _db()
    try:
        assert delete_embedding(conn, 4242) is True
        ok, msg = assert_vector_integrity(conn)
        assert ok, msg
    finally:
        conn.close()


def test_a_count_cannot_see_an_orphan_but_the_assertion_does() -> None:
    """The BUG-387 signature: a lie-free count, a half-dead store."""
    conn = _db()
    try:
        live = [_seed(conn, "FB-A"), _seed(conn, "FB-B")]
        for rid, seed in ((live[0], 0.1), (live[1], 0.2), (9999, 0.3)):
            conn.execute(
                "INSERT INTO vec_fbs(rowid, definition_embedding) VALUES (?, ?)",
                (rid, _vec(seed)),
            )
        n_fbs = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
        n_vec = conn.execute("SELECT COUNT(*) FROM vec_fbs").fetchone()[0]
        assert n_vec != n_fbs, "fixture must not be count-ambiguous"
        ok, msg = assert_vector_integrity(conn)
        assert ok is False, msg
        assert "CORRUPT" in msg and "1 orphaned" in msg, msg
    finally:
        conn.close()


def test_missing_vector_is_degraded_not_corrupt() -> None:
    """An fbs row with no vector keeps answering via FTS: DEGRADED, not corruption."""
    conn = _db()
    try:
        conn.execute(
            "INSERT INTO vec_fbs(rowid, definition_embedding) VALUES (?, ?)",
            (_seed(conn, "FB-1"), _vec(0.1)),
        )
        _seed(conn, "FB-2")  # no vector on purpose
        ok, msg = assert_vector_integrity(conn)
        assert ok is True, msg
        assert "DEGRADED" in msg and "1 fbs rows" in msg, msg
    finally:
        conn.close()


def _main() -> int:
    """Run every test_* in this module without pytest (see the module docstring)."""
    tests = sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f))
    failed = skipped = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except _Skip as e:
            skipped += 1
            print(f"SKIP {name} - {e}")
        except Exception as e:  # noqa: BLE001 - a runner reports, it does not crash
            failed += 1
            print(f"FAIL {name} - {type(e).__name__}: {e}")
    print(f"vec rowid contract: {len(tests)} tests, {failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
