#!/usr/bin/env python3
"""scripts/normalize_absent_shape.py - retire the '-as-absent SHAPE on ONE declared column at a time.

FINDING (BUG-737, mechanism landed 2026-10-12). The store's ABSENT shape is a NON-NULL BLANK while
the code's own contract is None: pipeline/schemas.py declares verifier_model as
str | None = Field(default=None), and pipeline/stage6_commit._safe_str maps every absent TEXT cell
to the empty string, so the store cannot tell "no verifier judged this row" from "a verifier wrote
nothing". Measured on the live 7,640-row store: 14 register-declared columns each hold 1,049 non-NULL
blanks - exactly the D-2590 sidecar rows, exactly where the register says outside: absent.

WHY ONE COLUMN AT A TIME (and never a bulk rewrite). A blank is not one fact. In-tier blanks are
MEANINGFUL and stay VISIBLE (discipline_raw is declared sparse INSIDE s5_verified and keeps its
in-tier blanks). Out-of-tier blanks are NOT-APPLICABLE. A HOLLOW literal ('[]', 'n/a') is a VALUE
someone wrote, not an absence, so this script REFUSES any column whose outside population carries
hollows and reports it for its own verdict. One column, one reader audit, one write, one measurement.

THE QUEUE IS DERIVED, NEVER NAMED (C12). A column is in the queue iff the register declares BOTH a
population AND outside: absent. --column is required and is validated against that queue, so this
script cannot be pointed at a column the ontology has not scoped.

EVERY NUMBER COMES FROM THE RAIL (D-2642 - no second home for a measured fact). The rulers
nonnull/nonblank/hollow are read through scripts/check_store_columns.py itself, in BOTH scopes (the
whole table and the declared population), and the outside numbers are the differences the rail uses
for POPULATION-SPILL / POPULATION-SHAPE. So this script cannot disagree with the rail about the
store; if it ever did, the write is refused.

WHAT THE WRITE IS, AND IS NOT. One UPDATE, on rows OUTSIDE the declared population whose value is a
non-NULL blank, writing NULL. It never touches an in-population row, a non-blank value, a hollow, or
a row count. The write's own WHERE clause carries the blank test, and the rows it actually changed
must EQUAL the count the rail measured - a mismatch rolls the transaction back, so a drifting
predicate cannot land (fail closed, C16).

C13/R-D410: --apply takes a crash-safe backup FIRST, writes in ONE BEGIN IMMEDIATE transaction,
verifies the post-state against the pre-state, and rolls back on any mismatch. Dry-run is the
default and never writes.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "config" / "store_columns.yaml"
BACKUP_DIR = ROOT / "backups"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
ABSENT_OUTSIDE = "absent"
# The write predicate. Deliberately NOT a measurement: every COUNT comes from the rail, and the UPDATE
# must change exactly that many rows or the transaction is rolled back (see WHAT THE WRITE IS).
WRITE_BLANK = "({col} IS NOT NULL AND LENGTH(TRIM(CAST({col} AS TEXT))) = 0)"


def load_rail():
    """Import the store-columns rail so the ruler vocabulary has ONE home (C12/D-2642/C21)."""
    path = ROOT / "scripts" / "check_store_columns.py"
    spec = importlib.util.spec_from_file_location("check_store_columns", path)
    if spec is None or spec.loader is None:
        raise SystemExit("FAIL (absent-shape): the store-columns rail is not importable - refusing to re-invent its vocabulary")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RAIL = load_rail()


def read_register() -> dict:
    """Return the parsed store-columns register, failing CLOSED if it is unreadable (C16)."""
    with open(REGISTER, encoding="utf-8") as fh:
        reg = yaml.safe_load(fh) or {}
    if not reg.get("columns"):
        raise SystemExit("FAIL (absent-shape): the register declares no columns - refusing to run blind")
    return reg


def queue(reg: dict) -> dict[str, str]:
    """Return the DERIVED work queue: declared column -> its population, for outside: absent only (C12)."""
    out: dict[str, str] = {}
    for name, decl in sorted((reg.get("columns") or {}).items()):
        row = dict(decl or {})
        pop = str(row.get("population") or "").strip()
        outside = str(row.get("outside") or "").strip()
        if pop and outside == ABSENT_OUTSIDE:
            out[str(name)] = pop
    return out


def population_predicate(reg: dict, pop: str) -> str:
    """Return the declared predicate for a population, refusing anything that could end the WHERE (C16)."""
    pops = reg.get("populations") or {}
    if pop not in pops:
        raise SystemExit("FAIL (absent-shape): a column names population '" + pop + "' which the register does not declare (UNKNOWN-POPULATION)")
    pred = str((pops[pop] or {}).get("predicate") or "").strip()
    if not pred:
        raise SystemExit("FAIL (absent-shape): population '" + pop + "' declares no predicate (BAD-POPULATION-PREDICATE)")
    for bad in RAIL.PREDICATE_BAD:
        if bad in pred:
            raise SystemExit("FAIL (absent-shape): population '" + pop + "' predicate contains '" + bad + "' - refused (it is interpolated into SQL)")
    return pred


def store_path(reg: dict) -> tuple[Path, str]:
    """Return (store path, table) from the register, refusing to guess a target."""
    store = str(reg.get("store") or "").strip()
    table = str(reg.get("table") or "").strip()
    if not store or not table:
        raise SystemExit("FAIL (absent-shape): the register declares no store/table - refusing to guess a target")
    path = ROOT / store
    if not path.exists():
        raise SystemExit("FAIL (absent-shape): the register's store does not exist: " + str(path))
    return path, table


def measure(path: Path, table: str, col: str, pop: str, pred: str) -> dict[str, int]:
    """Measure the column in BOTH scopes through the rail, and derive the outside numbers by difference (D-2642)."""
    table_rulers = RAIL.measure(path, table, [col], {col: 0})
    t = table_rulers["columns"][col]
    rows = int(table_rulers["rows"])
    pops = RAIL.measure_populations(path, table, [col], {pop: {"predicate": pred, "why": "measured by scripts/normalize_absent_shape.py"}})
    if pop not in pops:
        raise SystemExit("FAIL (absent-shape): the rail could not measure population '" + pop + "' - refusing to act on an unmeasurable universe (C16)")
    in_rows = int(pops[pop]["rows"])
    p = pops[pop]["columns"][col]
    con = sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True)
    try:
        src = '"{t}"'.format(t=table)
        out_rows_by_id = int(con.execute("SELECT COUNT(*) FROM " + src + " WHERE fb_id NOT IN (SELECT fb_id FROM " + src + " WHERE (" + pred + "))").fetchone()[0])
    finally:
        con.close()
    in_blank = int(p["nonnull"]) - int(p["nonblank"])
    return {
        "rows": rows,
        "in_rows": in_rows,
        "out_rows": rows - in_rows,
        "out_rows_by_id": out_rows_by_id,
        "in_nonnull": int(p["nonnull"]),
        "in_nonblank": int(p["nonblank"]),
        "in_blank": in_blank,
        "out_nonblank": int(t["nonblank"]) - int(p["nonblank"]),
        "out_hollow": int(t["hollow"]) - int(p["hollow"]),
        "out_blank": (int(t["nonnull"]) - int(t["nonblank"])) - in_blank,
        "out_null": (rows - int(t["nonnull"])) - (in_rows - int(p["nonnull"])),
    }


def backup(path: Path, col: str) -> Path:
    """C13: copy the store aside and fsync the copy before a single row is rewritten."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / (path.name + ".bak_" + time.strftime("%Y%m%d_%H%M%S") + "_pre_absent_shape_" + col)
    shutil.copy2(path, dest)
    fd = os.open(str(dest), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return dest


def report(name: str, pop: str, m: dict[str, int]) -> None:
    """Print the measurement that justifies (or refuses) the write."""
    print("  column            " + name + "   (population: " + pop + ", declared outside: " + ABSENT_OUTSIDE + ")")
    print("  rows              " + str(m["rows"]) + " | in population " + str(m["in_rows"]) + " | outside " + str(m["out_rows"]) + " (by id " + str(m["out_rows_by_id"]) + ")")
    print("  in-tier blanks    " + str(m["in_blank"]) + "   KEPT VISIBLE (a blank inside a declared tier is a measurement)")
    print("  outside blanks    " + str(m["out_blank"]) + "   -> the rows this script rewrites to NULL")
    print("  outside hollow    " + str(m["out_hollow"]) + "   REFUSED if non-zero (a hollow literal is a value, not an absence)")
    print("  outside nonblank  " + str(m["out_nonblank"]) + "   not this script's business (that is POPULATION-SPILL, the rail's fatal)")
    print("  outside NULL      " + str(m["out_null"]) + "   already shaped correctly")


def main(argv: list[str]) -> int:
    """Parse one mode, measure through the rail, and either write (--apply) or report; never both silently (C16)."""
    ap = argparse.ArgumentParser(description="retire the -as-absent shape on ONE declared store column (BUG-737)")
    ap.add_argument("--list", action="store_true", help="print the DERIVED queue and the pending row count per column (read-only)")
    ap.add_argument("--column", default=None, help="the ONE column to normalize (must be in the derived queue)")
    ap.add_argument("--apply", action="store_true", help="take the C13 backup and write; default is a dry run")
    args = ap.parse_args(argv)

    reg = read_register()
    path, table = store_path(reg)
    work = queue(reg)

    if args.list == bool(args.column):
        raise SystemExit("FAIL (absent-shape): pass exactly ONE of --list or --column (the rail's own contract at C16)")

    if args.list:
        print("DERIVED QUEUE (" + str(len(work)) + " column(s) declaring a population AND outside: absent):")
        for name, pop in work.items():
            m = measure(path, table, name, pop, population_predicate(reg, pop))
            print(str(m["out_blank"]).rjust(6) + "  " + name + "  [" + pop + "]  hollow " + str(m["out_hollow"]))
        return EXIT_OWED if work else EXIT_CLEAN

    col = str(args.column)
    if col not in work:
        raise SystemExit("FAIL (absent-shape): '" + col + "' is not in the derived queue - either the register does not declare it, or it does not declare outside: absent. Refusing to rewrite a column the ontology has not scoped")
    pop = work[col]
    pred = population_predicate(reg, pop)

    before = measure(path, table, col, pop, pred)
    print("absent-shape: " + col + ("  APPLY" if args.apply else "  dry-run"))
    report(col, pop, before)

    if before["out_rows"] != before["out_rows_by_id"]:
        print("FAIL (absent-shape): the predicate complement and the count complement DISAGREE (" + str(before["out_rows"]) + " vs " + str(before["out_rows_by_id"]) + ") - the population does not cover every tier (D-2959). Refusing.")
        return EXIT_DRIFT
    if before["out_nonblank"]:
        print("FAIL (absent-shape): " + str(before["out_nonblank"]) + " non-blank value(s) live outside the population - that is POPULATION-SPILL, the rail's fatal, and no shape fix may touch it. Refusing.")
        return EXIT_DRIFT
    if before["out_hollow"]:
        print("REFUSED (absent-shape): " + str(before["out_hollow"]) + " HOLLOW literal(s) outside the population. A hollow is a written value, not an absence; it needs its own verdict per column (BUG-737). Refusing.")
        return EXIT_DRIFT
    if not before["out_blank"]:
        print("ok (absent-shape): nothing to normalize - " + col + " already carries NULL outside '" + pop + "'")
        return EXIT_CLEAN
    if not args.apply:
        print("OWED (absent-shape): dry run - " + str(before["out_blank"]) + " row(s) would be reshaped. Re-run with --apply to take the C13 backup and write.")
        return EXIT_OWED

    dest = backup(path, col)
    print("  C13 backup        " + str(dest.relative_to(ROOT)) + "  (" + str(dest.stat().st_size) + " bytes)")
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        src = '"{t}"'.format(t=table)
        sql = ("UPDATE " + src + " SET " + col + " = NULL WHERE fb_id NOT IN (SELECT fb_id FROM " + src
               + " WHERE (" + pred + ")) AND " + WRITE_BLANK.format(col=col))
        cur.execute(sql)
        changed = int(cur.rowcount)
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        conn.close()
        raise SystemExit("FAIL (absent-shape): sqlite refused the write (" + str(exc) + ") - nothing written")
    finally:
        try:
            conn.close()
        except sqlite3.Error:
            pass

    after = measure(path, table, col, pop, pred)
    problems: list[str] = []
    if changed != before["out_blank"]:
        problems.append("rows changed " + str(changed) + " != rows the rail measured " + str(before["out_blank"]))
    if after["rows"] != before["rows"] or after["in_rows"] != before["in_rows"]:
        problems.append("a row count moved")
    if after["in_nonblank"] != before["in_nonblank"] or after["in_blank"] != before["in_blank"] or after["in_nonnull"] != before["in_nonnull"]:
        problems.append("the IN-population census moved (in-tier blanks must stay VISIBLE)")
    if after["out_blank"] != 0:
        problems.append("blanks remain outside the population")
    if after["out_nonblank"] != before["out_nonblank"] or after["out_hollow"] != before["out_hollow"]:
        problems.append("a non-blank or hollow value outside the population changed")
    if after["out_null"] != before["out_null"] + changed:
        problems.append("the new outside NULL count is not old NULLs + rows rewritten (" + str(after["out_null"]) + " vs " + str(before["out_null"] + changed) + ")")
    if problems:
        print("FAIL (absent-shape): post-state mismatch - " + "; ".join(problems))
        print("  ROLLBACK       restoring from " + str(dest.relative_to(ROOT)))
        shutil.copy2(dest, path)
        return EXIT_DRIFT

    report(col, pop, after)
    print("ok (absent-shape): " + str(changed) + " row(s) reshaped to NULL; in-tier census unchanged; backup " + dest.name)
    print("  NEXT              re-run scripts/check_store_columns.py --check, then --record (D-2642: the measured tail moves, the ceiling only DOWN)")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
