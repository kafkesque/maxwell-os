#!/usr/bin/env python3
"""scripts/check_label_provenance.py - BUG-497 / D-2640: the declared pre-provenance boundary, as a rail.

WHY: menu_hash and all three *_source tiers are empty on 7,995 / 7,995 rows of the governed store
because the corpus predates the R1/D-279 stamp. An empty stamp read as "there was no menu" is
indistinguishable from "the stamp is broken", so the boundary is DECLARED in
config/label_provenance.yaml and this rail is what makes the declaration falsifiable:

  1. the boundary's population is compared against its DECLARED measured_rows (a population that is
     only computed cannot disagree with anything - BUG-501/D-2638), so a boundary that grows silently
     is DRIFT;
  2. every row OUTSIDE the boundary MUST be `stamped` -- a row that is not is a broken stamp and the
     rail exits 1, so a future batch committed without the R1 stamp is REPORTED rather than absorbed
     into the boundary (the failure mode this rail exists for);
  3. no row may be `unstampable`: if the store carries none of the stamp columns the boundary cannot
     be evaluated at all, and an un-evaluable rail is never a pass (C16).

WHAT THIS DOES NOT DO: it does not re-implement the classification. It imports traceability_of from
pipeline/label_traceability.py (C21) -- a change to the declared ontology changes this rail in the same
commit. It WRITES NOTHING (read-only DSN, R-D410) and it never backfills: D-277 forbids manufacturing
a provenance claim, so a pre-boundary row stays pre_boundary and the remedy is an owner decision, not
a stamp.

Exit: 0 ok | 1 defect | 2 owner-owed (loud, NOT fatal - BUG-457 convention).
Usage: python3 scripts/check_label_provenance.py [--selftest]
"""

from __future__ import annotations

import argparse
import collections
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.label_traceability import (  # noqa: E402 - the ONE classifier, imported (C21)
    boundary_runs,
    load_config,
    stamp_columns,
    traceability_of,
)

EXIT_OK, EXIT_DEFECT, EXIT_OWED = 0, 1, 2
PREFIX = "check-label-provenance"


def read_rows(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Read the declared run column + stamp columns from the declared DB, READ-ONLY.

    Returns (rows, notes). Raises SystemExit when a declared column is absent: a rail checking a
    different table than the one it declares is a rail that cannot fail for the right reason.
    """
    db = ROOT / str(cfg["db"])
    if not db.exists():
        raise SystemExit(f"FAIL {PREFIX}: declared db {cfg['db']} does not exist")
    table = str(cfg["table"])
    cols = [str(cfg["run_column"]), *stamp_columns(cfg)]
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)  # a check must not be able to write
    try:
        present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        missing = [c for c in cols if c not in present]
        if missing:
            raise SystemExit(f"FAIL {PREFIX}: declared column(s) absent from {table}: {missing}")
        rows = [dict(zip(cols, r, strict=True))
                for r in conn.execute(f"SELECT {', '.join(cols)} FROM {table}")]
    finally:
        conn.close()
    return rows, [f"{table} carries {len(present)} column(s), {len(rows)} row(s)"]


def selftest(cfg: dict[str, Any]) -> int:
    """KNOWN-ANSWER CONTROLS through the same classifier the stored rows go through.

    A guardrail never observed failing is not a guardrail. The critical control is the PAIR that
    differs only in the declared run: it proves the boundary is what decides, so a classifier that
    has stopped consulting it fails loudly here instead of going quiet on the live store.
    """
    empty_row = {c: "" for c in stamp_columns(cfg)}
    run_column = str(cfg["run_column"])
    runs = sorted(boundary_runs(cfg))
    inside_run = runs[0] if runs else "t11"
    outside_run = "not-a-declared-run"
    controls = [
        ("a full quartet is stamped",
         {**empty_row, "menu_hash": "abc", "content_type_source": "human_verbatim",
          "discipline_source": "model", "extraction_type_source": "model", run_column: inside_run},
         "stamped"),
        ("a declared pre-boundary run with no stamp is pre_boundary",
         {**empty_row, run_column: inside_run}, "pre_boundary"),
        ("the SAME row outside the boundary is missing - the teeth (BUG-497)",
         {**empty_row, run_column: outside_run}, "missing"),
        ("a PARTIAL quartet outside the boundary is missing, never stamped",
         {"menu_hash": "abc" if "menu_hash" in empty_row else "", run_column: outside_run}, "missing"),
        ("a row dict with none of the stamp columns is unstampable, never pre_boundary",
         {run_column: inside_run}, "unstampable"),
    ]
    failed = 0
    for name, row, want in controls:
        got = traceability_of(row, cfg)
        if got != want:
            failed += 1
            print(f"FAIL {PREFIX} --selftest: {name} -> {got!r}; expected {want!r}")
        else:
            print(f"  control ok: {got:14s} {name}")
    if not runs:
        failed += 1
        print(f"FAIL {PREFIX} --selftest: the boundary declares NO generation run, so it can classify "
              f"nothing as pre_boundary - the declared boundary is empty (BUG-501 class)")
    total = len(controls) + 1
    if failed:
        print(f"FAIL {PREFIX} --selftest: {failed} of {total} known-answer control(s) did not fire")
        return EXIT_DEFECT
    print(f"ok {PREFIX} --selftest: {total}/{total} known-answer control(s) fire")
    return EXIT_OK


def main() -> int:
    """Classify every stored row, compare the boundary against its declaration, exit 0/1/2."""
    ap = argparse.ArgumentParser(description="BUG-497/D-2640 pre-provenance-boundary rail.")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    args = ap.parse_args()

    try:
        cfg = load_config()
    except ValueError as exc:
        print(f"FAIL {PREFIX}: the declared boundary is unusable: {exc}")
        return EXIT_DEFECT
    if args.selftest:
        return selftest(cfg)

    rows, notes = read_rows(cfg)
    tally: collections.Counter[str] = collections.Counter()
    missing_samples: list[str] = []
    boundary_stamped = 0
    inside = 0
    run_column = str(cfg["run_column"])
    runs = boundary_runs(cfg)
    for row in rows:
        state = traceability_of(row, cfg)
        tally[state] += 1
        if str(row.get(run_column) or "") in runs:
            inside += 1
            if state == "stamped":
                boundary_stamped += 1
        elif state != "stamped" and len(missing_samples) < 3:
            missing_samples.append(f"{str(row.get(run_column) or '<none>')} -> {state}")

    declared = int(cfg["boundary"]["measured_rows"])
    n = len(rows)
    if tally["unstampable"]:
        print(f"FAIL {PREFIX}: {tally['unstampable']} row(s) carry NONE of the declared stamp columns "
              f"{stamp_columns(cfg)}: traceability cannot be evaluated, so the boundary is unverifiable "
              f"(C16). {n} row(s) read from the declared store.")
        return EXIT_DEFECT
    if inside != declared:
        print(f"FAIL {PREFIX}: the boundary's population CHANGED - {inside} row(s) belong to the declared "
              f"generation runs {sorted(runs)} but config/label_provenance.yaml#boundary.measured_rows "
              f"declares {declared}. A boundary that grows silently absorbs a new gap: either the store "
              f"changed or the declaration must be updated deliberately (BUG-501/D-2638).")
        return EXIT_DEFECT
    if tally["missing"]:
        print(f"FAIL {PREFIX}: {tally['missing']} row(s) are OUTSIDE the declared boundary and carry an "
              f"incomplete R1/D-279 stamp quartet {stamp_columns(cfg)} - a BROKEN STAMP, not a boundary "
              f"case (the R1 stamp is written by pipeline/stage4_merge.py for every classified FB). "
              f"samples {missing_samples}")
        return EXIT_DEFECT

    headline = (f"{n} row(s) classified: {tally['stamped']} stamped, {tally['pre_boundary']} pre_boundary, "
                f"{tally['missing']} missing, {tally['unstampable']} unstampable ({'; '.join(notes)})")
    note = (f" [DECLARED BOUNDARY: {inside} row(s) in runs {sorted(runs)} = the declared {declared}; "
            f"their provenance is NEVER imputed and NEVER backfilled (D-277). "
            f"{boundary_stamped} boundary row(s) have since become stamped"
            + (" - dissolving a boundary is an OWNER act, reported not written" if boundary_stamped else "")
            + "]")
    print(f"ok {PREFIX}: {headline}{note}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
