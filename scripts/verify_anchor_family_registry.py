#!/usr/bin/env python3
"""Verify config/anchor_family.yaml against the artifacts it describes.

WHY
    The owner asked twice whether the anchor family contains the domain axis, and could not find
    the frozen anchor at all (BUG-424/BUG-425). Both answers existed only as prose, and a prose
    registry cannot be checked: it drifts silently (BUG-416 class). Every count in the YAML is
    therefore re-derived here from the artifacts, and any disagreement is a hard failure.

CONTRACT
    exit 0 -> every declared value reproduces from the artifacts.
    exit 1 -> at least one declared value does not; the offending field is named.

Rule (BUG-402): a count is never typed by hand, and a claim about an axis is never read from a
derived or copied column.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config" / "anchor_family.yaml"
MENU = REPO / "config" / "closed_menu_v5.json"
ENCODINGS = ("utf-8", "latin-1")  # repo carries latin-1 sheets (see buglog)


def load_config(path: Path = CONFIG) -> dict[str, Any]:
    """Load the registry YAML."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    """Return the hex sha256 of a file, streamed (files can be large)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV, falling back to latin-1 (the repo stores some sheets that way)."""
    for enc in ENCODINGS:
        try:
            with path.open(newline="", encoding=enc) as fh:
                return list(csv.DictReader(fh))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"undecodable with {ENCODINGS}: {path}")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping blank lines."""
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def menu_values(name: str) -> set[str]:
    """Return the lowercased canonical values of a menu block in closed_menu_v5.json."""
    entries = json.loads(MENU.read_text(encoding="utf-8"))[name]
    return {str(e["value"]).strip().lower() for e in entries}


def as_list(value: Any) -> list[str]:
    """Accept either a python list or a repr/JSON string of one (both occur in this repo)."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(v) for v in parsed]
        return [v.strip().strip("'\"") for v in value.strip("[]").split(",") if v.strip()]
    return []


def derive(cfg: dict[str, Any]) -> dict[str, Any]:
    """Re-derive every declared quantity from the artifacts. Pure measurement, no policy."""
    anchor = REPO / cfg["anchor"]["sheet"]
    sheet = read_csv_rows(anchor)
    derived_sheet = read_csv_rows(REPO / cfg["derived_sheet"]["sheet"])
    menu_disc = menu_values("disciplines")
    menu_dom = menu_values("domains")
    norm = lambda s: str(s or "").strip().lower()

    out: dict[str, Any] = {
        "anchor_sha256": sha256(anchor),
        "anchor_rows": len(sheet),
        "anchor_columns": len(sheet[0]) if sheet else 0,
    }
    for axis in ("content_type", "discipline", "extraction_type"):
        col = cfg["axes"][axis]["column"]
        out[f"anchor_filled_{axis}"] = sum(1 for r in sheet if norm(r.get(col)))

    # ANCHOR-4 must be a re-keyed view of ANCHOR-3 with DEPTH still blind.
    out["derived_sheet_rows"] = len(derived_sheet)
    out["derived_sheet_key_matches_anchor"] = (
        {r[cfg["derived_sheet"]["key"]] for r in derived_sheet}
        == {r[cfg["anchor"]["key"]] for r in sheet}
    )
    out["derived_sheet_depth_blank"] = sum(
        1 for r in derived_sheet if not norm(r.get(cfg["axes"]["depth"]["column"]))
    )

    # The disowned axis: cohort size and BOTH joins into the anchor.
    dom_cfg = cfg["axes"]["domains"]
    cohort = read_jsonl(REPO / dom_cfg["artifact"])
    out["domains_cohort"] = len(cohort)
    out["domains_cohort_human_adjudicated"] = sum(
        1 for d in cohort if d.get("domains_status") == "human-adjudicated"
    )
    key_rows = json.loads((REPO / "governance" / "ruler_sheet_key_20260917.json").read_text(encoding="utf-8"))
    fb_by_item = {r["item_id"]: r.get("fb_id") for r in key_rows}
    name_by_item = {r["item_id"]: (r.get("name") or "").strip() for r in key_rows}
    cohort_fb = {d.get(dom_cfg["cohort_artifact_key"]) for d in cohort}
    cohort_names = {(d.get("name") or "").strip() for d in cohort}
    hits_fb = sorted(item for item, fb in fb_by_item.items() if fb in cohort_fb)
    hits_name = sorted(item for item, nm in name_by_item.items() if nm in cohort_names)
    out["domains_intersection_default_key"] = len(hits_fb)
    out["domains_intersection_alternate_key"] = len(hits_name)
    out["domains_intersection_rows"] = hits_fb

    # Machine-side observations about the anchor rows (NOT owner labels).
    machine = cfg["machine_observations"]
    raw = {d.get("fb_id"): d for d in read_jsonl(REPO / machine["anchor_domains_source"])}
    rows_with = tokens = 0
    distinct: set[str] = set()
    off_menu = catchall = 0
    for r in sheet:
        vals = as_list((raw.get(fb_by_item.get(r["item_id"]), {}) or {}).get("domains"))
        if vals:
            rows_with += 1
        tokens += len(vals)
        for v in vals:
            distinct.add(v)
            if norm(v) not in menu_dom:
                off_menu += 1
            if norm(v) == "emerging":
                catchall += 1
    out["anchor_domains_rows_with_values"] = rows_with
    out["anchor_domains_tokens"] = tokens
    out["anchor_domains_distinct"] = len(distinct)
    out["anchor_domains_off_menu"] = off_menu
    out["anchor_domains_catchall_emerging_rows"] = catchall

    dcol = cfg["axes"]["discipline"]["column"]
    off_rows = [r["item_id"] for r in sheet if norm(r.get(dcol)) and norm(r.get(dcol)) not in menu_disc]
    out["off_menu_discipline_cells"] = len(off_rows)
    out["off_menu_discipline_rows"] = sorted(off_rows)
    out["off_menu_discipline_values"] = sorted({norm(r[dcol]) for r in sheet if r["item_id"] in set(off_rows)})
    return out


def compare(cfg: dict[str, Any], got: dict[str, Any]) -> list[str]:
    """Return a list of human-readable disagreements between the YAML and the measurements."""
    bad: list[str] = []

    def need(field: str, declared: Any) -> None:
        if declared != got.get(field):
            bad.append(f"{field}: config={declared!r} measured={got.get(field)!r}")

    need("anchor_sha256", cfg["anchor"]["sha256"])
    need("anchor_rows", cfg["anchor"]["rows"])
    need("anchor_columns", cfg["anchor"]["columns"])
    for axis in ("content_type", "discipline", "extraction_type"):
        need(f"anchor_filled_{axis}", cfg["axes"][axis]["intersection"])
    need("derived_sheet_key_matches_anchor", True)
    need("derived_sheet_depth_blank", cfg["derived_sheet"].get("depth_blank_expected", cfg["anchor"]["rows"]))
    dom = cfg["axes"]["domains"]
    need("domains_cohort", dom["cohort"])
    need("domains_cohort_human_adjudicated", dom["cohort_human_adjudicated"])
    need("domains_intersection_default_key", dom["intersection_default_key"])
    need("domains_intersection_alternate_key", dom["intersection_alternate_key"])
    if got["domains_intersection_rows"] != sorted(dom["intersection_rows"]):
        bad.append(f"domains_intersection_rows: config={sorted(dom['intersection_rows'])} measured={got['domains_intersection_rows']}")
    for key in (
        "anchor_domains_rows_with_values",
        "anchor_domains_tokens",
        "anchor_domains_distinct",
        "anchor_domains_off_menu",
        "anchor_domains_catchall_emerging_rows",
        "off_menu_discipline_cells",
    ):
        need(key, cfg["machine_observations"][key])
    if got["off_menu_discipline_rows"] != sorted(cfg["machine_observations"]["off_menu_discipline_rows"]):
        bad.append(
            f"off_menu_discipline_rows: config={sorted(cfg['machine_observations']['off_menu_discipline_rows'])} "
            f"measured={got['off_menu_discipline_rows']}"
        )
    return bad


def main() -> int:
    """Entry point: verify, and optionally emit the measured block for a config refresh."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print-config", action="store_true", help="emit the measured values as YAML")
    args = ap.parse_args()
    cfg = load_config()
    got = derive(cfg)
    if args.print_config:
        print(yaml.safe_dump(got, sort_keys=True, allow_unicode=True))
        return 0
    bad = compare(cfg, got)
    if bad:
        print("RED anchor family registry: config/anchor_family.yaml disagrees with the artifacts:")
        for line in bad:
            print(f"  - {line}")
        print("Fix: correct the YAML from the artifacts (never the reverse), then re-run.")
        return 1
    print(
        "ok anchor family registry: "
        f"ANCHOR-3 {got['anchor_rows']}x{got['anchor_columns']} {got['anchor_sha256'][:12]} | "
        f"owned axes CT/DISC/ET {got['anchor_filled_content_type']}/"
        f"{got['anchor_filled_discipline']}/{got['anchor_filled_extraction_type']} | "
        f"depth blind {got['derived_sheet_depth_blank']}/{got['derived_sheet_rows']} | "
        f"domains DISOWNED cohort {got['domains_cohort']} intersection "
        f"{got['domains_intersection_default_key']}/{got['anchor_rows']} {got['domains_intersection_rows']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
