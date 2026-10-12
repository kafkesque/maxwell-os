#!/usr/bin/env python3
"""scripts/normalize_runtime_absents.py — retire the `''`-as-absent SHAPE on declared `runtime` columns.

FINDING (measured on the live 7,640-row store, 2026-10-12). BUG-726 was diagnosed as one column
(`duplicate_of`) whose absent value was `''` while its documented predicate was `IS NULL`. The
census that followed says it is not one column and not one bug: **20 of the 78 columns carry a
NON-NULL blank, and NOT ONE column carries a NULL** — `stage6_commit._safe_str` maps an absent
value to `""` for every TEXT cell it writes, so the store's absent shape is `''` while the code's
own contract is `None` (`pipeline/schemas.py`: `last_retrieved_at: str | None = Field(default=None)`).
A shape the code cannot keep is the BUG-498 class.

This script is deliberately NARROW. It touches ONLY the columns the register declares
`role: runtime` (config/store_columns.yaml, D-2957) — a serving-path state column whose absent
state must be NULL — and it reads that column set from the register rather than naming it in code,
so a newly declared runtime column is covered the moment the declaration exists (C12/C21). The
other 19 blank-as-absent columns are NOT touched here: each needs its own verdict against its own
schema field before its shape moves, and a single bulk rewrite of 20 columns would be exactly the
unmeasured change this repository's rules exist to prevent (file: BUG-738).

WHY THIS IS IDENTITY-PRESERVING (checked BEFORE the write, not after): no reader of a runtime
column distinguishes `''` from NULL. `pipeline/schema_accessor.py` passes the value through,
`maxwell_mcp_server` formats both to `""` (`fb.get(...) or ""`), and every rule that consumes the
cell treats a blank as absent. The write therefore removes a second shape for one meaning; it
changes no verdict, no status and no rank.

C13/R-D410: `--apply` takes a crash-safe backup FIRST, writes in ONE `BEGIN IMMEDIATE`
transaction, verifies the post-state, and rolls back on any mismatch. Dry-run is the default and
never writes.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REGISTER = ROOT / "config" / "store_columns.yaml"
RUNTIME_ROLE = "runtime"          # D-2957: the one role whose absent state is NULL
BLANK_PREDICATE = "({col} IS NOT NULL AND LENGTH(TRIM(CAST({col} AS TEXT))) = 0)"


def runtime_columns(reg: dict) -> list[str]:
    """Return the columns the register declares `runtime` — the script's whole population (C12)."""
    cols = reg.get("columns") or {}
    return sorted(str(name) for name, decl in cols.items() if str((decl or {}).get("role") or "") == RUNTIME_ROLE)


def column_names(cur: sqlite3.Cursor, table: str) -> list[str]:
    """Return the real column names of `table`, failing CLOSED if the table is absent (C16)."""
    names = [str(r[1]) for r in cur.execute('PRAGMA table_info("%s")' % table)]
    if not names:
        raise SystemExit("FAIL-CLOSED: table " + repr(table) + " has no columns — the register is STALE.")
    return names


def census(cur: sqlite3.Cursor, table: str, columns: list[str]) -> dict[str, dict[str, int]]:
    """Measure, per runtime column, the blank-non-NULL count and the NULL count (read-only)."""
    out: dict[str, dict[str, int]] = {}
    for col in columns:
        quoted = '"' + col + '"'
        q = ('SELECT SUM(CASE WHEN ' + BLANK_PREDICATE.format(col=quoted) + ' THEN 1 ELSE 0 END), '
             'SUM(CASE WHEN ' + quoted + ' IS NULL THEN 1 ELSE 0 END) FROM "' + table + '"')
        blank, nulls = cur.execute(q).fetchone()
        out[col] = {"blank": int(blank or 0), "null": int(nulls or 0)}
    return out


def normalize(cur: sqlite3.Cursor, table: str, columns: list[str]) -> dict[str, int]:
    """Set NULL where a declared runtime column holds a non-NULL blank. Returns rows changed per column."""
    changed: dict[str, int] = {}
    for col in columns:
        cur.execute('UPDATE "' + table + '" SET "' + col + '" = NULL WHERE '
                    + BLANK_PREDICATE.format(col='"' + col + '"'))
        changed[col] = int(cur.rowcount)
    return changed


def _backup(db: Path) -> Path:
    """C13: crash-safe copy of the live store before the mutation."""
    backup_dir = db.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / ("maxwell.db.pre_runtime_absents_" + time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(db, dest)
    return dest


def main() -> int:
    """CLI: dry-run by default; `--apply` writes with a C13 backup and a verified post-state."""
    ap = argparse.ArgumentParser(description="Normalize declared runtime columns: blank-non-NULL -> NULL.")
    ap.add_argument("--apply", action="store_true", help="write (default is dry-run; C13 backup first)")
    ap.add_argument("--column", default="", help="limit to ONE declared runtime column (default: all)")
    args = ap.parse_args()

    reg = yaml.safe_load(REGISTER.read_text(encoding="utf-8")) or {}
    table = str(reg.get("table") or "")
    db = ROOT / str(reg.get("store") or "")
    if not db.is_file() or not table:
        raise SystemExit("FAIL-CLOSED: the register names store " + repr(str(db)) + " / table " + repr(table))

    declared = runtime_columns(reg)
    if args.column:
        if args.column not in declared:
            raise SystemExit("FAIL-CLOSED: " + repr(args.column) + " is not declared `role: " + RUNTIME_ROLE
                             + "` — refusing to reshape an undeclared column (C12).")
        declared = [args.column]
    if not declared:
        print("no column is declared `role: " + RUNTIME_ROLE + "` — nothing to do.")
        return 0

    con = sqlite3.connect(str(db))
    cur = con.cursor()
    real = column_names(cur, table)
    staging = [c for c in declared if c in real]
    stale = [c for c in declared if c not in real]
    before = census(cur, table, staging)

    print("store: " + str(db) + "#" + table)
    print("declared `" + RUNTIME_ROLE + "`: " + ", ".join(declared))
    if stale:
        print("  STALE declaration(s) (no such column): " + ", ".join(stale))
    for col, m in before.items():
        print("  " + col.ljust(22) + " blank-non-NULL " + str(m["blank"]).ljust(6) + " NULL " + str(m["null"]))
    todo = {c: m["blank"] for c, m in before.items() if m["blank"]}
    print("rows to normalize: " + str(sum(todo.values())) + " across " + str(len(todo)) + " column(s)")

    if not args.apply:
        print("\n[dry-run] nothing written. Re-run with --apply (C13 backup first).")
        con.close()
        return 0
    if not todo:
        print("\n[no-op] every declared runtime cell already uses ONE shape (NULL for absent).")
        con.close()
        return 0

    bak = _backup(db)
    print("\nC13 backup: " + str(bak))
    try:
        con.execute("BEGIN IMMEDIATE")
        changed = normalize(cur, table, sorted(todo))
        after = census(cur, table, staging)
        residual = {c: m["blank"] for c, m in after.items() if m["blank"]}
        if residual:
            raise RuntimeError("post-state still holds blank-non-NULL cells " + str(residual) + " — rolling back")
        if sum(changed.values()) != sum(todo.values()):
            raise RuntimeError("changed " + str(sum(changed.values())) + " row(s), expected "
                               + str(sum(todo.values())) + " — rolling back")
        con.commit()
    except BaseException:
        con.rollback()
        con.close()
        raise
    print("normalized: " + str(changed))
    print("post-state: " + str({c: m for c, m in after.items()}))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
