#!/usr/bin/env python3
"""D-2820 helper — convert the owner-filled adjudication CSV back to the decisions JSON
that scripts/rederive_anchor_axes_v6.py --adjudicate --decisions <file> expects.

Fail-closed (C16): every row MUST have a non-empty owner_discipline and owner_domains.
Off-menu labels (other than the abstention token) are rejected so typos surface BEFORE
--adjudicate, not after.

Usage:
    python3 scripts/rederive_csv_to_decisions.py --csv <filled csv> --out decisions.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

MENU_JSON = REPO / "config" / "closed_menu_v7.json"
ABSTENTION = "emerging"
DOMAIN_SEP = "|"


def load_menu_sets() -> tuple[set[str], set[str]]:
    """Return the full on-menu discipline/domain label sets (including the abstention token)."""
    menu = json.loads(MENU_JSON.read_text(encoding="utf-8"))
    disc = {str(e.get("value") or "").strip() for e in menu.get("disciplines", [])}
    doms = {str(e.get("value") or "").strip() for e in menu.get("domains", [])}
    disc.discard("")
    doms.discard("")
    return disc, doms


def parse_domains(cell: str) -> list[str]:
    """Split a pipe-separated domains cell into a trimmed, non-empty list."""
    return [d.strip() for d in (cell or "").split(DOMAIN_SEP) if d.strip()]


def build_decisions(csv_path: Path, disc_set: set[str], dom_set: set[str]) -> dict:
    """Read the filled CSV into a decisions dict. Raises on unadjudicated or off-menu rows (C16)."""
    decisions: dict = {}
    with open(csv_path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            item_id = (row.get("item_id") or "").strip()
            if not item_id:
                raise SystemExit("FAIL: CSV row missing item_id (C16)")
            discipline = (row.get("owner_discipline") or "").strip()
            domains = parse_domains(row.get("owner_domains"))
            if not discipline:
                raise SystemExit(f"FAIL: row {item_id} has empty owner_discipline (unadjudicated, D-2839 c2)")
            if not domains:
                raise SystemExit(f"FAIL: row {item_id} has empty owner_domains (unadjudicated, D-2839 c2)")
            if discipline not in disc_set:
                raise SystemExit(f"FAIL: row {item_id} discipline {discipline!r} is OFF menu v7 (typo?)")
            off = [d for d in domains if d not in dom_set]
            if off:
                raise SystemExit(f"FAIL: row {item_id} domains {off} are OFF menu v7 (typo?)")
            decisions[item_id] = {"discipline": discipline, "domains": domains}
    if not decisions:
        raise SystemExit("FAIL: no rows read from CSV (C16)")
    return decisions


def _crash_safe_write(path: Path, payload: dict) -> None:
    """C6 crash-safe write: tempfile -> replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _selftest() -> int:
    """Pure controls: round-trip a filled CSV -> decisions dict. No LLM/DB."""
    disc, doms = load_menu_sets()
    assert ABSTENTION in disc, "abstention token not in menu discipline set"

    import tempfile

    # real menu-v7 labels (verified against config/closed_menu_v7.json)
    disc_ok = "aesthetics"
    dom_ok = ["design strategy", "ai & agents"]

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "filled.csv"
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("item_id,name,definition,candidate_discipline,candidate_domains,owner_discipline,owner_domains,owner_note\n")
            fh.write(f"fb-1,One,def,{disc_ok},{'|'.join(dom_ok)},{disc_ok},{'|'.join(dom_ok)},ok\n")
            fh.write("fb-2,Two,def,emerging,emerging,cognitive science,code & computation,abstained\n")
        dec = build_decisions(p, disc, doms)
        assert dec["fb-1"] == {"discipline": disc_ok, "domains": dom_ok}, "round-trip mismatch"
        assert dec["fb-2"] == {"discipline": "cognitive science", "domains": ["code & computation"]}, "round-trip mismatch"

        # fail-closed: empty owner_discipline must raise
        p2 = Path(td) / "empty.csv"
        p2.write_text(
            "item_id,name,owner_discipline,owner_domains,owner_note\nfb-3,Three,,design strategy,\n",
            encoding="utf-8",
        )
        try:
            build_decisions(p2, disc, doms)
            raise AssertionError("empty owner_discipline did not fail-closed")
        except SystemExit:
            pass

        # fail-closed: off-menu discipline must raise
        p3 = Path(td) / "offmenu.csv"
        p3.write_text(
            "item_id,name,owner_discipline,owner_domains,owner_note\nfb-4,Four,not_a_real_label,design strategy,\n",
            encoding="utf-8",
        )
        try:
            build_decisions(p3, disc, doms)
            raise AssertionError("off-menu discipline did not fail-closed")
        except SystemExit:
            pass
    print("  OK CSV->decisions round-trip + fail-closed (empty / off-menu)")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Convert the filled adjudication CSV to decisions JSON for --adjudicate")
    ap.add_argument("--csv", default=None, help="path to the filled adjudication CSV (required unless --selftest)")
    ap.add_argument("--out", default=None, help="output decisions JSON path (required unless --selftest)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if not args.csv or not args.out:
        raise SystemExit("FAIL: --csv and --out are required (or run --selftest)")

    disc_set, dom_set = load_menu_sets()
    decisions = build_decisions(Path(args.csv), disc_set, dom_set)
    _crash_safe_write(Path(args.out), decisions)
    print(f"wrote {len(decisions)} decisions -> {args.out}")
    print("NEXT: python3 scripts/rederive_anchor_axes_v6.py --adjudicate --decisions " + args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
