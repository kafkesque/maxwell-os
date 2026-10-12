#!/usr/bin/env python3
"""sqlite_vec_loader.py — single home for loading the sqlite-vec extension.

Authority: C21 (swappable infra) + C23 (resilient) + C26 (cross-platform) +
C16 (no silent errors) + C19 (no duplicated code).

The sqlite-vec load sequence was duplicated in four call sites (retrieve.py,
backfill_embeddings.py, stage6_commit.py, repair_vec_integrity.py), each with a
subtly different failure mode and message — a drift/bloat hazard. This module is
the single, drift-proof home.

Failure modes are DISTINGUISHED (C16), never masked:
  * ImportError      -> sqlite_vec package missing from this interpreter.
  * no load-extension -> the interpreter's sqlite3 was built with
                        SQLITE_OMIT_LOAD_EXTENSION (python.org framework build);
                        the `enable_load_extension` / `load_extension` METHODS
                        are absent from the Python wrapper.
  * ctypes fallback  -> when the methods are absent but the C symbols still
                        exist in the `_sqlite3` shared library, call them
                        directly via ctypes.

The ctypes fallback restores vector search on python.org framework builds where
the symbols exist but the methods are not exposed. It is best-effort and NEVER
raises: on any failure we return method='none' so callers degrade to FTS (C23)
or fail closed (stage6.vec_require, C16/D-2717).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class SqliteVecLoad:
    """Structured result of a sqlite-vec load attempt (C16 diagnostics)."""

    loaded: bool
    method: str  # 'extension' | 'ctypes' | 'none'
    error: str | None  # human-readable failure reason when loaded is False


def load_sqlite_vec(conn: sqlite3.Connection) -> SqliteVecLoad:
    """Load sqlite-vec into `conn`; return a structured result, never raise.

    Layered strategy (C23): (1) standard enable_load_extension path,
    (2) ctypes C-API path when the methods are absent, (3) degrade to 'none'.
    """
    try:
        import sqlite_vec
    except ImportError:
        return SqliteVecLoad(
            False, "none",
            "sqlite-vec not installed in this interpreter (pip install sqlite-vec)",
        )

    if hasattr(conn, "enable_load_extension") and hasattr(conn, "load_extension"):
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            return SqliteVecLoad(True, "extension", None)
        except Exception as exc:  # noqa: BLE001 — resilience boundary (C23)
            return SqliteVecLoad(False, "none", f"sqlite-vec load failed: {exc}")

    ctypes_load = _load_via_ctypes(conn, sqlite_vec)
    if ctypes_load is not None:
        return ctypes_load

    return SqliteVecLoad(
        False, "none",
        "sqlite3 load-extension unavailable and ctypes fallback failed",
    )


def _load_via_ctypes(conn: sqlite3.Connection, sqlite_vec) -> SqliteVecLoad | None:
    """Best-effort ctypes load of sqlite-vec on builds missing the methods.

    Returns None when the interpreter's shared library cannot be used, so the
    caller degrades to FTS. Never raises.
    """
    try:
        import _sqlite3  # the C extension bound into this interpreter

        db = _connection_pointer(conn)
        if not db:
            return None
        lib = _load_sqlite3_library(_sqlite3.__file__)
        if lib is None:
            return None
        enable = getattr(lib, "sqlite3_enable_load_extension", None)
        load_ext = getattr(lib, "sqlite3_load_extension", None)
        if enable is None or load_ext is None:
            return None

        enable.argtypes = [ctypes.c_void_p, ctypes.c_int]
        enable.restype = ctypes.c_int
        load_ext.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_char_p),
        ]
        load_ext.restype = ctypes.c_int

        if enable(db, 1) != 0:
            return None
        path = sqlite_vec.loadable_path().encode("utf-8")
        err = ctypes.c_char_p()
        rc = load_ext(db, path, None, ctypes.byref(err))
        enable(db, 0)
        if rc != 0:
            msg = err.value.decode("utf-8", "replace") if err.value else f"rc={rc}"
            return SqliteVecLoad(
                False, "none", f"ctypes sqlite3_load_extension failed: {msg}"
            )
        return SqliteVecLoad(True, "ctypes", None)
    except Exception as exc:  # noqa: BLE001
        return SqliteVecLoad(False, "none", f"ctypes fallback failed: {exc}")


class _PyObject(ctypes.Structure):
    """CPython ``PyObject`` header — used only to reach the raw sqlite3* handle."""

    _fields_ = [("ob_refcnt", ctypes.c_ssize_t), ("ob_type", ctypes.c_void_p)]


class _PysqliteConnection(ctypes.Structure):
    """CPython ``pysqlite_Connection`` — ``db`` is the first member after the header."""

    _fields_ = [("ob", _PyObject), ("db", ctypes.c_void_p)]


def _connection_pointer(conn: sqlite3.Connection) -> int | None:
    """Extract the raw ``sqlite3*`` from a CPython Connection (best-effort).

    CPython stores the handle as the first member after ``PyObject_HEAD``. This
    is a CPython-internal detail and is guarded: any mismatch returns None and
    the caller degrades to FTS (C23).
    """
    try:
        ptr = ctypes.cast(id(conn), ctypes.POINTER(_PysqliteConnection))
        return ptr.contents.db or None
    except Exception:  # noqa: BLE001
        return None


def _load_sqlite3_library(first_path: str):
    """Return a ctypes handle exposing the sqlite3 C symbols, or None."""
    candidates = [first_path]
    found = ctypes.util.find_library("sqlite3")
    if found:
        candidates.append(found)
    for candidate in candidates:
        try:
            lib = ctypes.CDLL(candidate)
        except Exception:  # noqa: BLE001
            continue
        if hasattr(lib, "sqlite3_enable_load_extension"):
            return lib
    return None
