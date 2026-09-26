#!/usr/bin/env python3
"""scripts/apply_workbook_rulings.py — replay the OWNER-RULED cell changes (D-387/D-388).

WHY: an owner ruling on a gold cell is a DECLARED, replayable, checkable transformation — never a hand
edit. Three failure modes this closes:
  1. an unrecorded edit of the owner's bytes (the gold is corrupted silently);
  2. a REVERT: `normalize_owner_workbook.py --apply` re-derives a blank, so a ruling that lives only in
     the CSV is destroyed by the next normalize run. `--check` is wired into `just health`, so a revert
     is a RED rail, not a surprise;
  3. an INVENTED value: every ruling carries `basis` + `source` in config, and this script refuses to
     apply a ruling that does not declare one.

Config owns the paths, the values and the provenance (C12). Exit: 0 ok | 1 a ruling is not applied |
2 config error.

Usage:
    python3 scripts/apply_workbook_rulings.py --check     # exit 1 if the workbook does not carry a ruling
    python3 scripts/apply_workbook_rulings.py --apply     # back up, apply, log to the fix log
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CFG_PATH = _ROOT / "config" / "anchor_workbook_fixes.yaml"


def write_atomic(path: Path, text: str) -> None:
    """tempfile -> fsync -> os.replace, so a crash cannot leave a torn gold file (C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_rul_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def targets(ruling: dict[str, Any]) -> dict[str, str]:
    """Map one declared ruling onto the workbook columns it writes (never a code literal elsewhere)."""
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


def main() -> int:
    ap = argparse.ArgumentParser(description="replay declared owner rulings on the adjudication workbook")
    ap.add_argument("--check", action="store_true", help="exit 1 if any declared ruling is not applied")
    ap.add_argument("--apply", action="store_true", help="back up, apply and append to the fix log")
    args = ap.parse_args()
    if not (args.check or args.apply):
        ap.error("pass --check or --apply")

    cfg = yaml.safe_load(_CFG_PATH.read_text())
    io_cfg = cfg.get("rulings_io") or {}
    if not io_cfg.get("workbook"):
        print(f"ERROR config: {_CFG_PATH} carries no rulings_io.workbook", file=sys.stderr)
        return 2
    rulings: dict[str, dict[str, Any]] = cfg.get("owner_rulings") or {}
    for item, r in rulings.items():
        if r.get("basis") is None or r.get("source") is None:
            print(f"ERROR config: ruling {item} declares no basis/source - provenance is mandatory", file=sys.stderr)
            return 2

    wb = _ROOT / io_cfg["workbook"]
    raw = wb.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    rows = list(csv.DictReader(io.StringIO(raw)))
    by_id = {r["item_id"]: r for r in rows}
    missing = sorted(set(rulings) - set(by_id))
    if missing:
        print(f"ERROR: ruling names rows absent from the workbook: {missing}", file=sys.stderr)
        return 2

    changes: list[tuple[str, str, str, str, str]] = []
    not_applied: list[str] = []
    for item, r in rulings.items():
        row = by_id[item]
        for col, want in targets(r).items():
            if row.get(col, "") != want:
                not_applied.append(f"{item}.{col}: on disk {row.get(col, '')!r} != ruled {want!r}")
                if args.apply:
                    changes.append((item, col, row.get(col, ""), want, r["status"]))
                    row[col] = want

    if args.check:
        if not_applied:
            print("RED workbook rulings: a declared owner ruling is NOT in the workbook "
                  "(a normalize re-run reverts it):", file=sys.stderr)
            for line in not_applied:
                print(f"  - {line}", file=sys.stderr)
            print(f"  run: python3 scripts/apply_workbook_rulings.py --apply", file=sys.stderr)
            return 1
        declared = len([1 for r in rulings.values() if targets(r)])
        print(f"  ok   workbook rulings: {declared} cell ruling(s) present, {len(rulings)} row declaration(s)")
        return 0

    if not changes:
        print("  ok   workbook rulings: already applied (idempotent, no write)")
        return 0

    backup = _ROOT / (io_cfg.get("backup_dir") or "backups") / (
        wb.stem + "." + str(io_cfg.get("backup_suffix", "PRE_RULINGS")) + ".csv")
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wb, backup)

    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator=newline)
    w.writeheader()
    w.writerows(rows)
    write_atomic(wb, buf.getvalue())

    fixlog = _ROOT / (io_cfg.get("fixlog") or "")
    with fixlog.open("a", encoding="utf-8", newline="") as fh:
        fw = csv.writer(fh, lineterminator=newline)
        for item, col, old, new, status in changes:
            fw.writerow([item, col, old, new, status])
    print(f"  ok   workbook rulings applied: {len(changes)} cell(s); backup -> {backup.relative_to(_ROOT)}")
    for item, col, old, new, status in changes:
        print(f"       {item} {col}: {old!r} -> {new!r} [{status}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
