#!/usr/bin/env python3
"""D-2820 helper — export the --generate candidate worklist to a clean, owner-fillable CSV.

The re-derivation harness writes JSON only (rederive_v6_worklist_<date>.json). The owner
adjudicates every row by hand (D-2839 c2: never auto-finalize), so this script exports a
clean CSV with the classifier's candidate pre-filled in the owner_* columns for REVIEW + EDIT.

    leave  = accept the candidate
    edit   = override
    'emerging' = abstain (no menu label fits)

Domains are pipe-separated. A companion menu reference CSV is emitted so the owner can see
every valid label + its definition while filling.

Usage:
    python3 scripts/rederive_worklist_to_csv.py [--worklist PATH] [--out PATH] [--menu-out PATH]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

WORKLIST_DIR = REPO / "governance"
MENU_JSON = REPO / "config" / "closed_menu_v7.json"

ABSTENTION = "emerging"
DOMAIN_SEP = "|"
DEF_TRUNC = 400

CSV_HEADER = [
    "item_id",
    "name",
    "definition",
    "candidate_discipline",
    "candidate_domains",
    "owner_discipline",
    "owner_domains",
    "owner_note",
]


def _collapse(s: str) -> str:
    return " ".join((s or "").split())


def _trunc(s: str, n: int = DEF_TRUNC) -> str:
    s = _collapse(s)
    return s if len(s) <= n else s[: n - 1] + "…"


def discover_latest_worklist(directory: Path) -> Path | None:
    """Return the most recently modified rederive_v6_worklist_*.json, or None."""
    hits = sorted(
        directory.glob("rederive_v6_worklist_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return hits[0] if hits else None


def load_worklist(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("rows") or []
    if not rows:
        raise SystemExit(f"FAIL: worklist has no rows: {path}")
    return rows


def load_menu_reference() -> list[dict]:
    """Flatten menu v6 into (axis, value, definition) rows for the owner's cheat sheet."""
    menu = json.loads(MENU_JSON.read_text(encoding="utf-8"))
    out: list[dict] = []
    for axis in ("disciplines", "domains"):
        for e in menu.get(axis, []):
            value = str(e.get("value") or "").strip()
            if not value:
                continue
            out.append(
                {"axis": axis[:-1], "value": value, "definition": _collapse(e.get("definition") or "")}
            )
    out.append(
        {
            "axis": "special",
            "value": ABSTENTION,
            "definition": "ABSTENTION token — choose this when NO menu label fits (counts toward the emerging-rate budget).",
        }
    )
    return out


def build_csv_rows(worklist_rows: list[dict]) -> list[dict]:
    """Map worklist rows to CSV rows; owner_* pre-filled with the candidate for review-and-edit."""
    out: list[dict] = []
    for r in worklist_rows:
        cand_domains = r.get("candidate_domains") or []
        if not isinstance(cand_domains, list):
            cand_domains = [cand_domains]
        joined_domains = DOMAIN_SEP.join(str(d) for d in cand_domains)
        out.append(
            {
                "item_id": r.get("item_id", ""),
                "name": r.get("name", ""),
                "definition": _trunc(r.get("definition", "")),
                "candidate_discipline": r.get("candidate_discipline", ""),
                "candidate_domains": joined_domains,
                "owner_discipline": r.get("candidate_discipline", ""),
                "owner_domains": joined_domains,
                "owner_note": "",
            }
        )
    return out


def write_csv(rows: list[dict], header: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in header})


def _selftest() -> int:
    """Pure controls: header/row fidelity + menu reference shape. No LLM/DB/writes to repo."""
    import tempfile

    synth = [
        {
            "item_id": "fb-1",
            "name": "Synthetic FB",
            "definition": "A test foundation block definition.",
            "candidate_discipline": "aesthetics",
            "candidate_domains": ["design", "ai & agents"],
        }
    ]
    rows = build_csv_rows(synth)
    assert rows[0]["owner_discipline"] == "aesthetics", "owner_discipline not pre-filled"
    assert rows[0]["owner_domains"] == "design|ai & agents", "domains not pipe-joined"
    assert rows[0]["item_id"] == "fb-1", "item_id lost"

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test.csv"
        write_csv(rows, CSV_HEADER, p)
        with open(p, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == CSV_HEADER, "header mismatch"
            got = next(reader)
            assert got["owner_note"] == "", "owner_note not empty"
    ref = load_menu_reference()
    assert any(r["value"] == ABSTENTION for r in ref), "abstention missing from reference"
    print("  OK worklist->CSV fidelity + menu reference shape")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Export the re-derive candidate worklist to an owner-fillable CSV")
    ap.add_argument("--worklist", default=None, help="path to rederive_v6_worklist_*.json (default: latest in governance/)")
    ap.add_argument("--out", default=None, help="output CSV path (default: governance/rederive_v6_adjudication_<date>.csv)")
    ap.add_argument("--menu-out", default=None, help="menu reference CSV path (default: governance/closed_menu_v7_reference.csv)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    worklist_path = Path(args.worklist) if args.worklist else discover_latest_worklist(WORKLIST_DIR)
    if worklist_path is None or not worklist_path.exists():
        raise SystemExit("FAIL: no worklist found — run scripts/rederive_anchor_axes_v6.py --generate first")

    csv_rows = build_csv_rows(load_worklist(worklist_path))

    out_path = Path(args.out) if args.out else WORKLIST_DIR / f"rederive_v6_adjudication_{datetime.now(timezone.utc):%Y%m%d}.csv"
    write_csv(csv_rows, CSV_HEADER, out_path)

    menu_ref = load_menu_reference()
    menu_out = Path(args.menu_out) if args.menu_out else WORKLIST_DIR / "closed_menu_v7_reference.csv"
    write_csv(menu_ref, ["axis", "value", "definition"], menu_out)

    print(f"wrote {len(csv_rows)} adjudication rows -> {out_path}")
    print(f"wrote menu reference ({len(menu_ref)} labels) -> {menu_out}")
    print("HOW TO FILL: leave owner_discipline/owner_domains to ACCEPT the candidate,")
    print(f"  edit them to OVERRIDE, or set both to '{ABSTENTION}' to abstain. Domains are '{DOMAIN_SEP}'-separated.")
    print("THEN: python3 scripts/rederive_csv_to_decisions.py --csv <that csv> --out decisions.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
