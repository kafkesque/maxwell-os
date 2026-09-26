#!/usr/bin/env python3
"""store-columns: every column of the governed store must declare a lifecycle the MEASUREMENT supports.

WHY THIS EXISTS (BUG-524, MEASURED 2026-09-26). Six of eight audit axes had NO machine; every finding that closed
the gap came from the two with none - STORES and COLUMNS. Nothing could answer "does this column have a writer, a
reader, or a declared reserved status?". Measured by hand: `content_type` is 'principle' on 7995/7995 rows (a LABEL
that cannot vary); `classification_status` is 'CLEAN' on 7995/7995 while a sibling records 2 real errors and 2972
rows are QUARANTINEd (a status column that is FALSE); 7 columns are content-empty while code still NAMES all 7; the
three `*_source` columns are blank 0/7995 while the eval anchor is 100% stamped per axis (R14 holds at ROW level,
FAILS at LABEL level).

THE RULER IS THE BLIND SPOT (the BUG-521 lesson applied to a store). `count(col)` counts '' as present, so a
NON-NULL census cannot see a blank; `has(col)` cannot see '[]'. This rail therefore measures FIVE numbers per column
and never one - nonnull | nonblank | hollow | distinct | mentions - and checks a declaration against the ruler its
role implies.

ENTRY RULES
  default_role (required): the role of every column NOT listed under `columns:`. The default is a DECLARATION with
      a `default_why`, never an implicit convenience (C12).
  columns.<name>.role: value | sparse | state | reserved - each a DISTINCT machine rule, so no role here is a
      distinction no machine enforces (BUG-492):
        value    : nonblank == rows and distinct >= 2   <- the approved "a label must VARY" rule
        sparse   : 0 < nonblank < rows                  <- a row-carried diagnostic
        state    : nonblank == rows and distinct == 1 and hollow == 0 (requires `why`)
        reserved : nonblank - hollow == 0               (requires `filled_by`: nothing has written it yet)
      A column that must VARY but is constant is NOT a role - it is `role: value` + `status: debt`: OWED and
      shrink-only, which is exactly how the approved varying-column rule fails closed.
  columns.<name>.status: debt -> a KNOWN defect, excluded from role checks, counted against ceiling.debt.
  measured: / ceiling: / measured_by: are written ONLY by --record (D-2642); a hand edit there is DRIFT.
      A moved STORE ruler (nonnull | nonblank | hollow | distinct) is DRIFT - the store changed. A moved `mentions`
      census is CODE-CENSUS-MOVED: it counts .py FILES under scan_roots that NAME the column, so the CODE changed,
      not the store; it is LOUD and OWED (exit 2), never fatal (BUG-533/D-2649).
  NO ENTRY (and no default) = UNDECLARED (fail); a declaration with no store column = STALE (fail).
"""

from __future__ import annotations

import re
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import yaml_guard  # noqa: E402 - D-2648: verify the bytes PARSE before writing them
from lib.write_guard import OWNED_ANY, write_document  # noqa: E402 - D-401: the only legal whole-document write

PREFIX = "store-columns"
ROOT = Path(__file__).resolve().parent.parent
REGISTER = ROOT / "config" / "store_columns.yaml"
RAIL_REL = "scripts/check_store_columns.py"
EXIT_CLEAN, EXIT_DRIFT, EXIT_OWED = 0, 1, 2
# BUG-533 (D-2649): the FIVE rulers are not one kind of fact. Four are measured FROM THE STORE (nonnull | nonblank
# | hollow | distinct) and `mentions` is a census of the CODE - the number of .py FILES under `scan_roots` that
# NAME the column. A code edit is not a store change, and `mentions` is the one ruler role_faults never reads, so
# comparing it as a store invariant made every new script that names a column abort `just health` at this line and
# hide every rail after it. A moved census is OWNER-OWED here: LOUD, not fatal (BUG-457/BUG-533).
STORE_RULERS = ("nonnull", "nonblank", "hollow", "distinct")
CENSUS_RULERS = ("mentions",)
CENSUS_FAULT = "CODE-CENSUS-MOVED"
NON_FATAL_FAULTS = ("NOT-RECORDED", CENSUS_FAULT)
ROLES = ("value", "sparse", "state", "reserved")
HOLLOW = ("[]", "{}", "null", "none", "nan", "n/a", "na")
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MIN_WHY = 20


def _open(store: Path) -> sqlite3.Connection:
    """Open the governed store read-only, failing CLOSED with the artifact named (C16)."""
    if not store.is_file():
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the declared store " + str(store) + " does not exist - a "
                         "declaration that cannot be measured is not a check.")
    try:
        return sqlite3.connect("file:" + str(store) + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): cannot open " + str(store) + ": " + str(exc)) from exc


def columns_of(con: sqlite3.Connection, table: str) -> list[str]:
    """Return the column names of `table`, refusing any name this rail cannot quote safely."""
    names = [str(r[1]) for r in con.execute('PRAGMA table_info("%s")' % table)]
    if not names:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): table " + repr(table) + " has no columns or does not exist.")
    for name in names:
        if not NAME_RE.match(name):
            raise SystemExit("FAIL-CLOSED (" + PREFIX + "): column name " + repr(name) + " is not quotable.")
    return names


def mention_census(root: Path, scan_roots: list[str], columns: list[str]) -> dict[str, int]:
    """Count, per column, how many .py files NAME it. A census, not proof of a read: named, not intended."""
    pat = {c: re.compile(r"(?<![\w.])" + re.escape(c) + r"(?![\w])") for c in columns}
    out = {c: 0 for c in columns}
    for scan in scan_roots:
        base = root / scan
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for col in columns:
                if pat[col].search(text):
                    out[col] += 1
    return out


def measure(store: Path, table: str, columns: list[str], mentions: dict[str, int]) -> dict[str, Any]:
    """Measure the FIVE rulers per column: nonnull, nonblank, hollow, distinct, mentions."""
    con = _open(store)
    try:
        rows = int(con.execute('select count(*) from "%s"' % table).fetchone()[0])
        hollow_in = ", ".join("'" + h + "'" for h in HOLLOW)
        out: dict[str, Any] = {}
        for col in columns:
            q = ('select count("%(c)s"), count(nullif(trim("%(c)s"), \'\')), '
                 'sum(case when lower(trim(coalesce("%(c)s", \'\'))) in (%(h)s) then 1 else 0 end), '
                 'count(distinct nullif(trim("%(c)s"), \'\')) from "%(t)s"') % {"c": col, "t": table, "h": hollow_in}
            nonnull, nonblank, hollow, distinct = con.execute(q).fetchone()
            out[col] = {"rows": rows, "nonnull": int(nonnull), "nonblank": int(nonblank),
                        "hollow": int(hollow or 0), "distinct": int(distinct), "mentions": int(mentions.get(col, 0))}
        return {"rows": rows, "columns": out}
    finally:
        con.close()


def role_faults(col: str, decl: dict[str, Any], m: dict[str, int], default_why: str) -> list[str]:
    """Return the faults for ONE column: its declared role against the five rulers."""
    role = str(decl.get("role") or "")
    rows = m["rows"]
    if role not in ROLES:
        return ["UNKNOWN-ROLE: " + col + " declares role " + repr(role) + " which is not one of " + ", ".join(ROLES)]
    why = str(decl.get("why") or default_why).strip()
    faults: list[str] = []
    if role == "value":
        if m["nonblank"] != rows or m["distinct"] < 2:
            faults.append("CONSTANT-OR-BLANK: " + col + " is declared role `value` (must VARY and be non-blank) but "
                          "measures nonblank " + str(m["nonblank"]) + "/" + str(rows) + " and distinct "
                          + str(m["distinct"]) + " - a column that cannot vary cannot carry a label; declare "
                          "status: debt with a why, or fix the writer.")
    elif role == "sparse":
        if not (0 < m["nonblank"] < rows):
            faults.append("SPARSE-VIOLATION: " + col + " is declared role `sparse` (0 < nonblank < rows) but "
                          "measures nonblank " + str(m["nonblank"]) + "/" + str(rows) + ".")
    elif role == "state":
        if m["nonblank"] != rows or m["distinct"] != 1 or m["hollow"] > 0:
            faults.append("STATE-VIOLATION: " + col + " is declared role `state` (one fact per row) but measures "
                          "nonblank " + str(m["nonblank"]) + "/" + str(rows) + ", distinct " + str(m["distinct"])
                          + ", hollow " + str(m["hollow"]) + ".")
        if len(why) < MIN_WHY:
            faults.append("MISSING-WHY: " + col + " is declared `state` with no adequate why (" + str(len(why))
                          + " chars) - a single value must say WHICH fact it is.")
    elif role == "reserved":
        if m["nonblank"] - m["hollow"] != 0:
            faults.append("RESERVED-VIOLATION: " + col + " is declared `reserved` (nothing written yet) but "
                          + str(m["nonblank"] - m["hollow"]) + " row(s) carry content.")
        if len(str(decl.get("filled_by") or "").strip()) < 3:
            faults.append("MISSING-FILLED-BY: " + col + " is `reserved` with no `filled_by` - a reservation that "
                          "does not name its writer is a comment (C12).")
    return faults


def fatal_faults(faults: list[str]) -> list[str]:
    """The faults that FAIL this rail; a census move and an unrecorded block are loud but not fatal (BUG-457)."""
    return [f for f in faults if not f.startswith(NON_FATAL_FAULTS)]


def audit(root: Path, reg: dict[str, Any], fresh: dict[str, Any] | None = None) -> tuple[list[str], int]:
    """Return (faults, debt_count). `fresh` lets controls inject a measurement instead of reading the real store."""
    store = root / str(reg.get("store") or "")
    table = str(reg.get("table") or "")
    declared = {str(k): dict(v or {}) for k, v in (reg.get("columns") or {}).items()}
    default_role = str(reg.get("default_role") or "")
    default_why = str(reg.get("default_why") or "")
    if default_role not in ROLES:
        raise SystemExit("FAIL-CLOSED (" + PREFIX + "): the register declares no usable `default_role` (got "
                         + repr(default_role) + ") - every column must be covered by a declaration (C12).")
    if fresh is None:
        con = _open(store)
        try:
            cols = columns_of(con, table)
        finally:
            con.close()
        mentions = mention_census(root, [str(s) for s in (reg.get("scan_roots") or ["scripts"])], cols)
        fresh = measure(store, table, cols, mentions)
    cols = list(fresh["columns"])
    faults: list[str] = []
    debt = 0
    for col in cols:
        decl = declared.get(col, {"role": default_role, "why": default_why})
        if str(decl.get("status") or "") == "debt":
            debt += 1
            if len(str(decl.get("why") or "").strip()) < MIN_WHY:
                faults.append("MISSING-WHY: " + col + " is declared status `debt` with no adequate why - a defect "
                              "must name itself.")
            continue
        faults.extend(role_faults(col, decl, fresh["columns"][col], default_why))
    for col in sorted(set(declared) - set(cols)):
        faults.append("STALE: column " + col + " is declared but NOT in " + table + " - a declaration that cannot "
                      "be measured is not a check.")
    stored = ((reg.get("measured") or {}).get("columns") or {})
    if not stored:
        faults.append("NOT-RECORDED: the register carries no `measured:` block - run --record (the measurement is "
                      "what the next check is compared against).")
    for col in sorted(set(stored) & set(cols)):
        for key, value in sorted(stored[col].items()):
            got = fresh["columns"][col].get(key)
            if got == value:
                continue
            if key in CENSUS_RULERS:
                # BUG-533: `mentions` counts the .py FILES under scan_roots that NAME the column - it is the one
                # ruler no role reads. The old wording said "the store changed", which was false for this key.
                faults.append(CENSUS_FAULT + ": " + col + "." + key + " was recorded as " + repr(value)
                              + " and now counts " + repr(got) + " .py file(s) naming the column - the CODE moved, "
                              "not the store; the census counts " + ", ".join(str(s) for s in
                              (reg.get("scan_roots") or ["scripts"]))
                              + ", so it moves on any code change. Re-record with --record when the move is"
                              " intended (D-2649/BUG-533).")
            else:
                faults.append("MEASUREMENT-DRIFT: " + col + "." + key + " was recorded as " + repr(value)
                              + " and now measures " + repr(got) + " - the store changed under a declaration that "
                              "still claims the old number (D-2649).")
    return faults, debt


def record(reg: dict[str, Any], text: str) -> int:
    """Write the freshly measured tail; a raise of ceiling.debt is REFUSED once measured_by names this rail."""
    faults, debt = audit(ROOT, reg)
    handover = str(reg.get("measured_by") or "") != RAIL_REL
    ceiling = dict(reg.get("ceiling") or {})
    old = int(ceiling.get("debt") if ceiling.get("debt") is not None else -1)
    if not handover and debt > old:
        raise SystemExit("FAIL (" + PREFIX + "): a raise of the debt ceiling is REFUSED (D-2642): measured " + str(debt)
                         + " > declared " + str(old) + ". Fix the store or declare the new defect with a why; the "
                         "ceiling is shrink-only.")
    con = _open(ROOT / str(reg.get("store") or ""))
    try:
        cols = columns_of(con, str(reg.get("table") or ""))
    finally:
        con.close()
    mentions = mention_census(ROOT, [str(s) for s in (reg.get("scan_roots") or ["scripts"])], cols)
    fresh = measure(ROOT / str(reg.get("store") or ""), str(reg.get("table") or ""), cols, mentions)
    tail: dict[str, Any] = {"measured_by": RAIL_REL, "measured": fresh,
                            "ceiling": {"debt": debt, "direction": "shrink_only"}}
    if handover:
        print("  handover: measured_by probe -> rail; the ceiling is now SHRINK-ONLY (D-2642)")
    body = yaml.safe_dump(tail, default_flow_style=False, sort_keys=True, width=100)
    # BUG-525: the tail RE-DECLARES `ceiling`, so the replaced region must begin at the FIRST of the two anchors.
    # Starting at `measured:` (as this rail first did) leaves the old `ceiling:` standing above it and the register
    # then carries the key TWICE - which PyYAML resolves silently by last-wins, so the rail recorded a number and
    # a shadowed declaration of the same fact survived. Measured 2026-09-26 on this rail's own register.
    anchors = [index for index in (text.find("\nceiling:"), text.find("\nmeasured:")) if index >= 0]
    if not anchors:
        raise SystemExit("FAIL (" + PREFIX + "): the register has neither a `ceiling:` nor a `measured:` anchor to"
                         " replace - refusing to guess where the declarations end (C16).")
    cut = min(anchors)
    new_text = text[:cut + 1] + body
    yaml_guard.assert_yaml(new_text, str(REGISTER), RAIL_REL)  # D-2648: the bytes must PARSE before the write
    report = write_document(REGISTER, new_text, writer=RAIL_REL, owned_keys={OWNED_ANY}, backup=True)
    print("  recorded " + str(len(cols)) + " column(s) | debt " + str(debt) + " | " + str(report))
    return EXIT_OWED if debt else EXIT_CLEAN


def _seed(base: Path, values: dict[str, list[str | None]]) -> Path:
    """Create a synthetic store for the controls: {column: [value per row]} (controls only)."""
    path = base / "gov" / "store.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    try:
        cols = sorted(values)
        con.execute('create table fbs (' + ", ".join('"%s" text' % c for c in cols) + ")")
        for i in range(len(next(iter(values.values())))):
            con.execute('insert into fbs values (' + ", ".join("?" for _ in cols) + ")",
                        [values[c][i] for c in cols])
        con.commit()
    finally:
        con.close()
    return path


def controls() -> list[tuple[str, Callable[[], bool]]]:
    """Known-answer controls (BUG-492): every control is handed a THUNK and must be able to FAIL."""
    def _faults(values: dict[str, list[str | None]], columns: dict[str, dict[str, Any]],
                default_role: str = "value", default_why: str = "synthetic control default declaration",
                recorded: bool = True, recorded_over: dict[str, dict[str, int]] | None = None) -> list[str]:
        # `recorded_over` hands the audit a RECORDED number that differs from the fresh measurement - the only way
        # to exercise the DRIFT / census split (BUG-533). The 14 original controls always passed fresh == recorded,
        # so no control could ever fire on a drift at all (BUG-492: an unexercised rule is a comment).
        # BUG-525/bug-492: the harness must be able to hand the audit a register whose DEFAULT why is empty and
        # one whose `measured:` block is ABSENT, otherwise the harness's own defaults satisfy the rule it is
        # testing and two controls can never fire (measured 2026-09-26: c10 and c13 were exactly that).
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            _seed(base, values)
            rows = len(next(iter(values.values())))
            m = {"rows": rows, "columns": {c: {"rows": rows, "nonnull": sum(1 for v in values[c] if v is not None),
                                               "nonblank": sum(1 for v in values[c] if v is not None and str(v).strip()),
                                               "hollow": sum(1 for v in values[c] if str(v).strip().lower() in HOLLOW),
                                               "distinct": len({str(v).strip() for v in values[c] if v is not None
                                                                and str(v).strip()}),
                                               "mentions": 0} for c in values}}
            reg = {"store": "gov/store.db", "table": "fbs", "columns": columns, "default_role": default_role,
                   "default_why": default_why,
                   "measured": {"columns": {c: dict(v) for c, v in m["columns"].items()}} if recorded else {},
                   "scan_roots": ["code"]}
            for col, over in (recorded_over or {}).items():
                reg["measured"]["columns"].setdefault(col, {}).update(over)
            faults, _ = audit(base, reg, fresh=m)
            return faults

    long_why = "a single value that IS the fact of this synthetic run, declared deliberately"

    def c15_census_move_is_owed() -> bool:
        """BUG-533: a moved `mentions` census is the CODE moving - LOUD and OWED, never DRIFT."""
        f = _faults({"a": ["x", "y"]}, {}, recorded_over={"a": {"mentions": 99}})
        return (any(x.startswith(CENSUS_FAULT) for x in f)
                and not any(x.startswith("MEASUREMENT-DRIFT") for x in f)
                and not fatal_faults(f))

    def c16_store_ruler_move_is_fatal() -> bool:
        """BUG-533: the four STORE rulers keep failing CLOSED - the census split must not shadow them."""
        f = _faults({"a": ["x", "y"]}, {}, recorded_over={"a": {"nonblank": 99}})
        return len(fatal_faults(f)) == 1 and fatal_faults(f)[0].startswith("MEASUREMENT-DRIFT")

    def c17_severity_split() -> bool:
        """BUG-492: a control on the CLASSIFIER itself - only a store ruler may reach the fatal set."""
        mixed = [CENSUS_FAULT + ": a.mentions moved", "MEASUREMENT-DRIFT: a.nonblank moved"]
        return (fatal_faults(mixed) == [mixed[1]]
                and fatal_faults([mixed[0], "NOT-RECORDED: no `measured:` block"]) == [])
    return [
        ("c01 a varying non-blank column passes the default `value` rule",
         lambda: not _faults({"a": ["x", "y", "z"]}, {}, "value")),
        ("c02 a CONSTANT column under `value` fails (the varying-label rule)",
         lambda: any(f.startswith("CONSTANT-OR-BLANK") for f in _faults({"a": ["p", "p", "p"]}, {"a": {"role": "value"}}))),
        ("c03 a BLANK-only column fails `value` even though count(col) is full (the '' ruler)",
         lambda: any(f.startswith("CONSTANT-OR-BLANK") for f in _faults({"a": ["", "", ""]}, {"a": {"role": "value"}}))),
        ("c04 a blank column passes `reserved` when it names its writer",
         lambda: not _faults({"a": ["", "", ""]}, {"a": {"role": "reserved", "filled_by": "stage4_5_enrich.py"}})),
        ("c05 the literal [] passes `reserved` (the hollow ruler) but NOT `value`",
         lambda: not _faults({"a": ["[]", "[]"]}, {"a": {"role": "reserved", "filled_by": "stage4_5_enrich.py"}})
         and any(f.startswith("CONSTANT-OR-BLANK") for f in _faults({"a": ["[]", "[]"]}, {"a": {"role": "value"}}))),
        ("c06 a `reserved` column with content fails CLOSED",
         lambda: any(f.startswith("RESERVED-VIOLATION") for f in _faults(
             {"a": ["v", ""]}, {"a": {"role": "reserved", "filled_by": "somewhere.py"}}))),
        ("c07 a `reserved` column without filled_by fails (C12)",
         lambda: any(f.startswith("MISSING-FILLED-BY") for f in _faults({"a": ["", ""]}, {"a": {"role": "reserved"}}))),
        ("c08 a sparse column must be neither full nor empty",
         lambda: not _faults({"a": ["v", "", ""]}, {"a": {"role": "sparse"}})
         and any(f.startswith("SPARSE-VIOLATION") for f in _faults({"a": ["v", "v"]}, {"a": {"role": "sparse"}}))),
        ("c09 a `state` column with a hollow token fails",
         lambda: any(f.startswith("STATE-VIOLATION") for f in _faults(
             {"a": ["none", "none"]}, {"a": {"role": "state", "why": long_why}}))),
        ("c10 a `state` column passes only with an adequate why",
         lambda: not _faults({"a": ["3.0", "3.0"]}, {"a": {"role": "state", "why": long_why}})
         and any(f.startswith("MISSING-WHY") for f in _faults({"a": ["3.0", "3.0"]}, {"a": {"role": "state"}},
                                                              default_why=""))),
        ("c11 a declaration with no store column is STALE",
         lambda: any(f.startswith("STALE") for f in _faults({"a": ["x", "y"]}, {"gone": {"role": "value"}}))),
        ("c12 status debt is OWED, not DRIFT, and must carry a why",
         lambda: not [f for f in _faults({"a": ["p", "p"]}, {"a": {"role": "value", "status": "debt",
                                                                  "why": long_why}}) if "CONSTANT" in f]
         and any(f.startswith("MISSING-WHY") for f in _faults(
             {"a": ["p", "p"]}, {"a": {"role": "value", "status": "debt"}}))),
        ("c13 an unrecorded measurement is reported, not assumed",
         lambda: any(f.startswith("NOT-RECORDED") for f in _faults({"a": ["x", "y"]}, {}, recorded=False))),
        ("c14 a role outside the vocabulary fails",
         lambda: any(f.startswith("UNKNOWN-ROLE") for f in _faults({"a": ["x", "y"]}, {"a": {"role": "label"}}))),
        ("c15 a moved `mentions` census is OWNER-OWED (the CODE moved), never DRIFT (BUG-533)",
         c15_census_move_is_owed),
        ("c16 a moved STORE ruler is still fatal DRIFT - the census split must not shadow it",
         c16_store_ruler_move_is_fatal),
        ("c17 the severity split sends only a store ruler to the fatal set (BUG-492)",
         c17_severity_split),
    ]


def run_controls() -> int:
    """Run every known-answer control; a control that cannot fail is reported, not passed (BUG-492)."""
    checks = controls()
    ok = 0
    for name, thunk in checks:
        try:
            good = bool(thunk())
        except Exception as exc:  # C16: report, never swallow
            good = False
            print("  FAIL " + name + " -> raised " + type(exc).__name__ + ": " + str(exc))
            continue
        print(("  ok   " if good else "  FAIL ") + name)
        ok += 1 if good else 0
    print(("ok " if ok == len(checks) else "FAIL ") + PREFIX + ": " + str(ok) + "/" + str(len(checks))
          + " known-answer control(s) fire")
    return EXIT_CLEAN if ok == len(checks) else EXIT_DRIFT


def main(argv: list[str]) -> int:
    """Entry point: exactly ONE mode is required (C16 - an ambiguous invocation must not silently scan)."""
    modes = [a for a in argv if a in ("--selftest", "--check", "--list", "--record")]
    if len(argv) != 1 or len(modes) != 1:
        raise SystemExit("FAIL " + PREFIX + ": exactly ONE of --selftest | --check | --list | --record is required "
                         "(C16); got " + repr(argv))
    if modes[0] == "--selftest":
        return run_controls()
    text = REGISTER.read_text(encoding="utf-8")
    reg = yaml.safe_load(text) or {}
    if modes[0] == "--record":
        return record(reg, text)
    faults, debt = audit(ROOT, reg)
    ceiling = int((reg.get("ceiling") or {}).get("debt") or 0)
    if modes[0] == "--list":
        store = ROOT / str(reg.get("store") or "")
        table = str(reg.get("table") or "")
        con = _open(store)
        try:
            cols = columns_of(con, table)
        finally:
            con.close()
        listed = measure(store, table, cols,
                         mention_census(ROOT, [str(s) for s in (reg.get("scan_roots") or ["scripts"])], cols))
        for col, m in sorted(listed["columns"].items()):
            print("  " + col.ljust(26) + " nonblank " + str(m["nonblank"]).ljust(6) + " distinct "
                  + str(m["distinct"]).ljust(6) + " hollow " + str(m["hollow"]).ljust(6) + " mentions "
                  + str(m["mentions"]))
        return EXIT_CLEAN
    fatal = fatal_faults(faults)
    moved = [f for f in faults if f.startswith(CENSUS_FAULT)]
    for fault in faults:
        print(("  DRIFT " if fault in fatal else "  OWED  ") + fault)
    mark = "FAIL " if fatal else ("OWED " if (debt or moved) else "ok ")
    print(mark + PREFIX + ": debt " + str(debt) + " of ceiling " + str(ceiling)
          + " | " + str(len(reg.get("columns") or {})) + " declared column(s) | census moves " + str(len(moved))
          + " | store " + str(reg.get("store")) + "#" + str(reg.get("table")))
    if fatal:
        return EXIT_DRIFT
    return EXIT_OWED if (debt or moved) else EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
