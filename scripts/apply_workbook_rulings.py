#!/usr/bin/env python3
"""scripts/apply_workbook_rulings.py - replay the OWNER-RULED cell changes (D-387/D-388).

WHY: an owner ruling on a gold cell is a DECLARED, replayable, checkable transformation - never a hand
edit. Three failure modes this closes:
  1. an unrecorded edit of the owner's bytes (the gold is corrupted silently);
  2. a REVERT: `normalize_owner_workbook.py --apply` re-derives a blank, so a ruling that lives only in
     the CSV is destroyed by the next normalize run. `--check` is a ladder line, so a revert is a RED
     rail, not a surprise;
  3. an INVENTED value: every ruling carries `basis` + `source` in config, and this script refuses to
     apply a ruling that does not declare one.

BUG-560 (2026-09-27, D-2685) - this applier is a WRITER OF CELLS THE OWNER OWNS, so it passes through the
same guard as every other owner-cell writer:
  * the workbook write is write_guard.write_rows(mode="merge", owned_keys=<the ruled columns>): a cell
    outside the ruled columns that would change is REFUSED, and the change lands with a receipt in
    governance/MUTATION_JOURNAL.jsonl (before: mkstemp->os.replace and NO receipt - invisible to the one
    rail whose population is DECLARED writers);
  * the CELL SCOPE is DECLARED (rulings_io.owned_columns) and the column map below is JOINED to it, so a
    ruling that would reach outside the scope is refused HERE, not discovered in the gold (C12d/C16);
  * the fixlog append is write_guard.append_lines: a SUFFIX-ONLY append that proves the pre-image bytes
    survive. MEASURED: this ledger holds 14 CRLF and 9 LF lines, so append_rows - which regenerates every
    pre-image line through csv.DictWriter - would re-terminate 23 lines of a ledger this writer does not
    own, and the old code fed it the WORKBOOK's terminator.
  * each artifact's terminator is READ from that artifact's own last line (artifact_terminator): the old
    workbook guess was INERT (read_text() had already translated CRLF away), and the old ledger terminator
    was the workbook's. Two artifacts, two conventions, and neither may borrow the other's (D-2676 ii).
MEASURED while fixing it (same session): the `--check` rail this docstring claimed was wired into `just
health` was DECLARED in three homes (this docstring, config#rulings_io, CONTEXT_INDEX) and RUN in none -
the BUG-582 shape, on the one rail whose whole job is to stop a normalize re-run reverting an owner
ruling. `--selftest` and `--check` are both ladder lines now.

Config owns the paths, the values, the scope and the provenance (C12). Exit: 0 ok | 1 a ruling is not
applied | 2 config error. Usage:
    python3 scripts/apply_workbook_rulings.py --check | --apply | --selftest
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.fixture import outside_tree  # noqa: E402 - ONE home of the fixture refusal (BUG-537/BUG-577)
from lib.write_guard import BACKUP_DIR, WriteRefused, append_lines, write_rows  # noqa: E402 - D-401/I1 (BUG-560)

_ROOT = Path(__file__).resolve().parent.parent
_CFG_PATH = _ROOT / "config" / "anchor_workbook_fixes.yaml"
WRITER = "scripts/apply_workbook_rulings.py"


def targets(ruling: dict[str, Any]) -> dict[str, str]:
    """Map one declared ruling onto the workbook columns it writes - a CLAIM, joined to the declared scope.

    The column names live in code; WHICH of them this applier may touch is declared in
    config/anchor_workbook_fixes.yaml#rulings_io.owned_columns and checked by scope_faults(), so this map
    cannot widen its own reach by an edit (C12d, BUG-560).
    """
    col = ruling["column"]
    if col == "depth_final":
        return {"depth_final": str(ruling["value"]), "depth_final_class": str(ruling.get("class", ""))}
    if col == "domains_final":
        out = {"domains_final": str(ruling["value"])}
        for key, wcol in (("raw", "domains_final_raw"), ("primary", "primary_domain")):
            if ruling.get(key) is not None:
                out[wcol] = str(ruling[key])
        return out
    return {}


def scope_faults(rulings: dict[str, dict[str, Any]], owned: set[str]) -> list[str]:
    """PURE (BUG-560): every column the ruling map would WRITE must be declared in the applier's scope.

    Both sides are PARAMETERS, so the controls that drive this are synthetic - a control reading this
    repository's own configuration cannot fail for a reason the repository chose (BUG-492).
    """
    faults: list[str] = []
    for item in sorted(rulings):
        for col in sorted(targets(rulings[item])):
            if col not in owned:
                faults.append(item + " would write '" + col + "', which is NOT in "
                              "config/anchor_workbook_fixes.yaml#rulings_io.owned_columns " + str(sorted(owned)))
    return faults


def header_faults(header: list[str], wanted: set[str]) -> list[str]:
    """PURE: a ruled column absent from the artifact's header is a declaration that cannot be falsified (BUG-492)."""
    return ["ruled column '" + c + "' is not among the workbook's columns " + str(header)
            for c in sorted(wanted) if c not in header]


def artifact_terminator(path: Path) -> str:
    """The ARTIFACT's OWN line terminator, read from its last line - never another artifact's (BUG-560).

    The old applier handed the fixlog the WORKBOOK's terminator: two artifacts, one convention, and the one
    that did not own it was rewritten. The old workbook side was worse than wrong - it was INERT: it tested
    `"\r\n" in raw` on a string read by read_text(), which has already translated CRLF away, so it could
    only ever answer "\n". Read the BYTES of the artifact whose bytes are about to change; assume nothing.
    Called for BOTH artifacts, so neither convention can be borrowed from the other.
    """
    raw = path.read_bytes()
    if raw.endswith(b"\r\n"):
        return "\r\n"
    if raw.endswith(b"\n"):
        return "\n"
    raise SystemExit("FAIL-CLOSED (C16): " + str(path) + " does not end with a line terminator - a rewrite or "
                     "an append would JOIN its last line to the next, and this writer owns no such join")


def run(cfg_path: Path, root: Path, *, check: bool, apply: bool, journal: bool = True,
        backup: bool = True) -> int:
    """The whole applier, parameterised by its config and root so the selftest can drive THROWAWAY paths."""
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    io_cfg = cfg.get("rulings_io") or {}
    for key in ("workbook", "fixlog", "owned_columns"):
        if not io_cfg.get(key):
            print("ERROR config: " + str(cfg_path) + " carries no rulings_io." + key, file=sys.stderr)
            return 2
    rulings: dict[str, dict[str, Any]] = cfg.get("owner_rulings") or {}
    for item, r in rulings.items():
        if r.get("basis") is None or r.get("source") is None:
            print("ERROR config: ruling " + item + " declares no basis/source - provenance is mandatory",
                  file=sys.stderr)
            return 2

    owned = {str(c) for c in io_cfg["owned_columns"]}
    offenders = scope_faults(rulings, owned)
    if offenders:
        print("FAIL-CLOSED (C16) workbook rulings: a declared ruling reaches OUTSIDE the applier's declared cell "
              "scope - nothing was written:", file=sys.stderr)
        for o in offenders:
            print("  !! " + o, file=sys.stderr)
        print("  fix the scope declaration or the ruling - never this check", file=sys.stderr)
        return 2

    wb = root / io_cfg["workbook"]
    raw = wb.read_text(encoding="utf-8")
    # the WORKBOOK's own terminator, MEASURED from its bytes (the old read_text() guess was inert)
    newline = artifact_terminator(wb)
    reader = csv.DictReader(io.StringIO(raw))
    header = list(reader.fieldnames or [])
    rows = list(reader)
    by_id = {r["item_id"]: r for r in rows}
    missing = sorted(set(rulings) - set(by_id))
    if missing:
        print("ERROR: ruling names rows absent from the workbook: " + str(missing), file=sys.stderr)
        return 2

    changes: list[tuple[str, str, str, str, str]] = []
    not_applied: list[str] = []
    for item, r in rulings.items():
        row = by_id[item]
        for col, want in targets(r).items():
            if row.get(col, "") != want:
                not_applied.append(item + "." + col + ": on disk " + repr(row.get(col, ""))
                                   + " != ruled " + repr(want))
                if apply:
                    changes.append((item, col, row.get(col, ""), want, str(r["status"])))
                    row[col] = want

    if check:
        if not_applied:
            print("RED workbook rulings: a declared owner ruling is NOT in the workbook (a normalize re-run "
                  "reverts it):", file=sys.stderr)
            for line in not_applied:
                print("  - " + line, file=sys.stderr)
            print("  run: python3 scripts/apply_workbook_rulings.py --apply", file=sys.stderr)
            return 1
        declared = len([1 for r in rulings.values() if targets(r)])
        print("  ok   workbook rulings: " + str(declared) + " cell ruling(s) present, " + str(len(rulings))
              + " row declaration(s), scope " + str(sorted(owned)))
        return 0

    if not changes:
        print("  ok   workbook rulings: already applied (idempotent, no write)")
        return 0

    written = {c for _, c, _, _, _ in changes}
    absent = header_faults(header, written)
    if absent:
        print("FAIL-CLOSED (C16) workbook rulings: nothing was written:", file=sys.stderr)
        for a in absent:
            print("  !! " + a, file=sys.stderr)
        return 2
    fixlog = root / io_cfg["fixlog"]
    # measured BEFORE any write: a refusal here must not leave half a change
    term = artifact_terminator(fixlog)

    try:
        rep = write_rows(wb, rows, owned_keys=written, writer=WRITER, mode="merge", columns=header,
                         encoding="utf-8", lineterminator=newline, journal=journal, backup=backup)
        buf = io.StringIO(newline="")
        cw = csv.writer(buf, lineterminator="\n")
        for item, col, old, new, status in changes:
            cw.writerow([item, col, old, new, status])
        frep = append_lines(fixlog, buf.getvalue().splitlines(), writer=WRITER, encoding="utf-8",
                            lineterminator=term, journal=journal, backup=False)
    except WriteRefused as exc:
        print("FAIL-CLOSED (C16) workbook rulings: " + str(exc), file=sys.stderr)
        return 2
    print("  ok   workbook rulings applied: " + str(len(changes)) + " cell(s); pre-image "
          + str(rep.backup) + ", receipt " + str(rep.pre_sha16) + " -> " + str(rep.post_sha16))
    print("       fixlog: +" + str(frep.added) + " row(s), pre-image bytes preserved (suffix-only append)")
    for item, col, old, new, status in changes:
        print("       " + item + " " + col + ": " + repr(old) + " -> " + repr(new) + " [" + status + "]")
    return 0


def _fixture(tmp: Path, *, header: str, rows: list[str], owned: list[str], ruling: dict[str, Any],
             wb_term: str = "\n", led_term: str = "\r\n") -> Path:
    """Build a THROWAWAY workbook + ledger + config; returns the config path (never a real artifact).

    The two artifacts' terminators are PARAMETERS (BUG-560): a fixture where both are "\n" cannot tell a
    writer that READS the ledger's terminator from one that BORROWS the workbook's. The writes are
    BYTE-exact - write_text() translates "\n" on some platforms, which would make a control's subject
    depend on the host (C26).
    """
    def put(name: str, lines: list[str], term: str) -> None:
        (tmp / name).write_bytes((term.join(lines) + term).encode("utf-8"))

    put("wb.csv", [header, *rows], wb_term)
    put("fixlog.csv", ["item_id,column,old,new,status", "R000,x,y,z,FIXED"], led_term)
    cfg = tmp / "cfg.yaml"
    cfg.write_text(yaml.safe_dump({"rulings_io": {"workbook": "wb.csv", "fixlog": "fixlog.csv",
                                                  "owned_columns": owned},
                                   "owner_rulings": {"R001": ruling}}, sort_keys=False), encoding="utf-8")
    return cfg


def selftest() -> int:
    """Known-answer controls on a THROWAWAY fixture: a control nothing runs is a comment (BUG-492)."""
    ok = True
    ran = 0
    live_backups = sorted(p.name for p in BACKUP_DIR.iterdir()) if BACKUP_DIR.exists() else []

    def control(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok, ran
        ok = ok and passed
        ran += 1
        print(("ok   selftest/" if passed else "FAIL selftest/") + name + ((" - " + detail) if detail else ""))

    r_depth = {"column": "depth_final", "value": "domain", "class": "3", "status": "CARRY-FORWARD",
               "basis": "fixture", "source": "fixture"}
    HDR = "item_id,name,owner_note,depth_final,depth_final_class"
    ROW = "R001,Some Name,KEEP THIS,,''" if False else "R001,Some Name,KEEP THIS,,"

    control("scope_join_reports_a_column_outside_the_declaration",
            bool(scope_faults({"R001": r_depth}, {"depth_final"})), "the map may not widen its own reach")
    control("scope_join_is_silent_inside_the_declaration",
            scope_faults({"R001": r_depth}, {"depth_final", "depth_final_class"}) == [])
    control("header_join_reports_a_column_the_artifact_lacks",
            bool(header_faults(["item_id", "depth_final"], {"depth_final_class"})))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        outside_tree(tmp, where=WRITER + " selftest fixture")   # ONE home (BUG-537): never the audited tree
        full = tmp / "full"; full.mkdir()
        cfg = _fixture(full, header=HDR, rows=[ROW], owned=["depth_final", "depth_final_class"], ruling=r_depth)
        control("check_is_red_when_the_ruling_is_absent", run(cfg, full, check=True, apply=False) == 1)
        wb = full / "wb.csv"; fl = full / "fixlog.csv"
        pre_wb, pre_fl = wb.read_bytes(), fl.read_bytes()
        control("apply_lands_the_ruling_through_the_guard", run(cfg, full, check=False, apply=True, journal=False, backup=False) == 0)
        after = list(csv.DictReader(io.StringIO(wb.read_text(encoding="utf-8"))))[0]
        control("apply_wrote_the_ruled_cells", after["depth_final"] == "domain" and after["depth_final_class"] == "3")
        control("apply_preserved_the_foreign_cell", after["owner_note"] == "KEEP THIS" and after["name"] == "Some Name")
        control("check_is_green_after_apply", run(cfg, full, check=True, apply=False) == 0)
        post_fl = fl.read_bytes()
        suffix = post_fl[len(pre_fl):]
        control("the_fixlog_append_preserves_its_pre_image_bytes", post_fl[: len(pre_fl)] == pre_fl
                and suffix == b"R001,depth_final,,domain,CARRY-FORWARD\r\n"
                             b"R001,depth_final_class,,3,CARRY-FORWARD\r\n",
                "a ledger is append-only: its pre-image bytes survive as a PREFIX, one line per RULED CELL")
        control("the_two_artifacts_keep_their_own_terminators",
                b"\n" not in suffix.replace(b"\r\n", b"") and b"\r" not in wb.read_bytes()
                and pre_wb != wb.read_bytes(),
                "the ledger's own CRLF, never the workbook's LF - the BUG-560 sub-defect")

        narrow = tmp / "narrow"; narrow.mkdir()
        cfg2 = _fixture(narrow, header=HDR, rows=[ROW], owned=["depth_final"], ruling=r_depth)
        pre2 = (narrow / "wb.csv").read_bytes()
        rc2 = run(cfg2, narrow, check=False, apply=True, journal=False, backup=False)
        control("ruling_outside_the_declared_scope_is_refused", rc2 == 2 and (narrow / "wb.csv").read_bytes() == pre2,
                "rc=" + str(rc2))

        head = tmp / "head"; head.mkdir()
        cfg3 = _fixture(head, header="item_id,name,owner_note,depth_final", rows=["R001,Some Name,KEEP,"],
                        owned=["depth_final", "depth_final_class"], ruling=r_depth)
        pre3 = (head / "wb.csv").read_bytes()
        rc3 = run(cfg3, head, check=False, apply=True, journal=False, backup=False)
        control("a_target_column_absent_from_the_header_is_refused",
                rc3 == 2 and (head / "wb.csv").read_bytes() == pre3, "rc=" + str(rc3))

        crlf = tmp / "crlf"; crlf.mkdir()
        cfg4 = _fixture(crlf, header=HDR, rows=[ROW], owned=["depth_final", "depth_final_class"],
                        ruling=r_depth, wb_term="\r\n", led_term="\n")
        rc4 = run(cfg4, crlf, check=False, apply=True, journal=False, backup=False)
        wb4 = (crlf / "wb.csv").read_bytes()
        row4 = list(csv.DictReader(io.StringIO(wb4.decode("utf-8"))))[0]
        control("the_workbook_keeps_its_own_terminator",
                rc4 == 0 and b"\n" not in wb4.replace(b"\r\n", b"")
                and b"\r" not in (crlf / "fixlog.csv").read_bytes()
                and row4["owner_note"] == "KEEP THIS" and row4["depth_final"] == "domain",
                "a CRLF workbook rewritten with the ledger's LF re-terminates every line it does not own")

        after_live = sorted(p.name for p in BACKUP_DIR.iterdir()) if BACKUP_DIR.exists() else []
        control("the_selftest_deposits_nothing_in_the_live_tree", after_live == live_backups,
                "a fixture whose PRE-IMAGE lands in the tree it audits is the BUG-537 class one level down; "
                + str(len(after_live) - len(live_backups)) + " file(s) appeared under backups/")

    if not ok:
        print("FAIL apply_workbook_rulings selftest: a known-answer control did not answer as declared (BUG-492)")
        return 1
    print("ok apply_workbook_rulings selftest: " + str(ran) + " controls hold (the scope join and the header "
          "join over synthetic inputs, a RED check, an in-scope apply that lands through the guard and preserves a "
          "foreign cell, a GREEN check after it, a fixlog append that preserves its pre-image bytes and keeps the "
          "LEDGER's own terminator, a CRLF workbook rewritten under ITS OWN terminator, and out-of-scope and "
          "missing-header columns refused with nothing written)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="replay declared owner rulings on the adjudication workbook")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="exit 1 if any declared ruling is not applied")
    g.add_argument("--apply", action="store_true", help="guard, receipt, apply and log to the fix log")
    g.add_argument("--selftest", action="store_true", help="known-answer controls on a throwaway fixture")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    return run(_CFG_PATH, _ROOT, check=args.check, apply=args.apply)


if __name__ == "__main__":
    sys.exit(main())
