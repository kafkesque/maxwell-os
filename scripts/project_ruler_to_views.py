#!/usr/bin/env python3
"""project_ruler_to_views.py — Stage 2 place 5: project the frozen RULER's discipline/domain/
primary_domain axis values into BOTH five-axis views, and clear the declared noise_drop rows.

WHY (BUG-682, one level down). The five-axis views
(governance/ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv,
 governance/ANCHOR_150_FIVE_AXIS_VIEW_20260927.csv) still carry the PRE-ruling
discipline/domain/primary_domain cells. The owner's rulings landed in the frozen ruler
(governance/DOMAIN_RULER_FROZEN_20261008.json) and the CONSOLIDATED face, but the views —
which are the declared authority for the content_type / extraction_type axes and carry their
OWN copies of the OntoClean axis — stayed stale. A reader of a view (or a golden few-shot
derived from one) would carry a label the owner's ruling contradicts.

THE RULE (deterministic, LLM-free, config-driven):
    * every axis-bearing row (in the ruler)     -> discipline = ruler.discipline,
                                                   domain      = '|'.join(ruler.domains),
                                                   primary     = ruler.primary_domain
    * every declared noise_drop row             -> discipline = '', domain = '', primary = ''
                                                   (a noise_drop row is a valid exemplar on NO
                                                   axis — D-2813 / D-2879)
    * any row that is NEITHER axis-bearing NOR a declared noise_drop -> FAIL-CLOSED (BUG-679
      partition invariant: a row is accounted for exactly once)

The discipline abstention rows carry discipline='' in the ruler already (BUG-676: the abstention
is an ABSENCE, not a token), so they project to '' verbatim.

Does NOT touch the status columns (disc / domain_status / ct / et) — those are separate axes.

Usage:
    python3 scripts/project_ruler_to_views.py            # dry-run report
    python3 scripts/project_ruler_to_views.py --apply    # write (crash-safe)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULER = ROOT / "governance" / "DOMAIN_RULER_FROZEN_20261008.json"
RULINGS = ROOT / "config" / "owner_domain_rulings_20261008.yaml"
VIEWS = [
    ROOT / "governance" / "ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv",
    ROOT / "governance" / "ANCHOR_150_FIVE_AXIS_VIEW_20260927.csv",
]


def _load_drops() -> set[str]:
    """The declared noise_drop set (config-driven, C12)."""
    cfg = yaml.safe_load(RULINGS.read_text(encoding="utf-8"))
    return {str(i) for i in (cfg.get("noise_drop_excluded") or [])}


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Crash-safe write: tempfile -> fsync -> os.replace (C6)."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def project(path: Path, ruler_by: dict[str, dict], drops: set[str], apply: bool) -> int:
    """Project the ruler's three axis values into one view; return the changed-cell count."""
    fieldnames, rows = _read_csv(path)
    changed = 0
    for r in rows:
        iid = r.get("item_id")
        if iid in ruler_by:
            ru = ruler_by[iid]
            want = {
                "discipline": ru.get("discipline") or "",
                "domain": "|".join(ru.get("domains") or []),
                "primary_domain": ru.get("primary_domain") or "",
            }
        elif iid in drops:
            want = {"discipline": "", "domain": "", "primary_domain": ""}
        else:
            raise SystemExit("FAIL-CLOSED: view row " + str(iid) + " is NEITHER axis-bearing "
                             "NOR a declared noise_drop (BUG-679 partition invariant)")
        for col in ("discipline", "domain", "primary_domain"):
            cur = " ".join(str(r.get(col) or "").split())
            if cur != want[col]:
                r[col] = want[col]
                changed += 1
    if apply and changed:
        _write_csv(path, fieldnames, rows)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Project the frozen ruler into both five-axis views.")
    parser.add_argument("--apply", action="store_true", help="write (default dry-run)")
    args = parser.parse_args()

    if not RULER.exists():
        raise SystemExit("FAIL-CLOSED: frozen ruler missing: " + str(RULER))
    ruler = json.loads(RULER.read_text(encoding="utf-8"))
    ruler_by = {r["item_id"]: r for r in ruler["rows"]}
    drops = _load_drops()
    if not drops:
        raise SystemExit("FAIL-CLOSED: config declares no noise_drop_excluded set")

    total = 0
    for path in VIEWS:
        if not path.exists():
            raise SystemExit("FAIL-CLOSED: declared view missing: " + str(path))
        n = project(path, ruler_by, drops, args.apply)
        total += n
        print(f"  {path.name}: {n} axis cell(s) {'changed' if args.apply else 'would change'}")
    print(f"{'applied' if args.apply else 'dry-run'}: {total} total discipline/domain/primary_domain "
          f"cell(s) across {len(VIEWS)} view(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
