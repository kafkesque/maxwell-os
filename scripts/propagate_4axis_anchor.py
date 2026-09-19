#!/usr/bin/env python3
"""propagate_4axis_anchor.py — put the adjudicated 4-axis truth into the runtime KB.

WHY (FORENSIC AUDIT F-01, 2026-09-17). `governance/gold_4axis.jsonl` is the project's own
statement of truth for content_type / depth / discipline / domains. `scripts/
propagate_content_type_decisions.py` (D2598) pushed content_type only, so the runtime DB still
disagrees with the anchor on depth (4.0%), discipline (43.4%) and domains (79.3%). The product
therefore serves labels the project has already adjudicated as wrong.

GUARDS (fail-closed, C16):
  * an axis is only written when the gold row's `<axis>_source` is inside the matching
    authoritative set in `pipeline/axis_authority.py` (a silver/golden source can never
    overwrite the runtime);
  * every gold row must exist in the DB, and every gated axis must be non-empty, or the run
    aborts before writing anything;
  * `--apply` is required; the default is a dry run;
  * C13 backup of the DB into `backup/deletions/<stamp>/` before any write;
  * R14 manifest with per-axis and per-source counts written next to the backup.

NOTE: the `fbs` table has no per-axis provenance columns, so the manifest — not the row —
is the record of what moved. Adding those columns is a separate, schema-level decision.

Usage:
    python3 scripts/propagate_4axis_anchor.py                 # dry run, prints the diff
    python3 scripts/propagate_4axis_anchor.py --apply         # backup + write + manifest
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.axis_authority import (  # noqa: E402  (D2626: single source of truth)
    CT_AUTH,
    DEPTH_AUTH,
    DISC_AUTH,
    DOM_AUTH,
    DP_ORIG,
)

# The anchor marks depth as legitimately NOT APPLICABLE for non-principle content types with the
# sentinel that axis_authority already carries (`n/a-non-principle`). An empty depth with that
# source is a DESIGN decision, not a gap - it must not abort the run (F-03 owns the sentinel
# stamping; this script only propagates adjudicated values).
NON_APPLICABLE_DEPTH_SOURCES = frozenset(str(v) for v in DP_ORIG if str(v).startswith("n/a"))

GOLD = REPO / "governance" / "gold_4axis.jsonl"
DB = REPO / "knowledge pipeline" / "maxwell.db"
BACKUP_ROOT = REPO / "backup" / "deletions"
AXIS_COLUMN = {
    "content_type": ("content_type", CT_AUTH),
    "depth": ("depth", DEPTH_AUTH),
    "discipline": ("discipline", DISC_AUTH),
    "domains": ("domains", DOM_AUTH),
}
DOMAIN_SEP = ", "


def _s(value: Any) -> str:
    """Normalise a scalar label cell to a comparable stripped string."""
    return "" if value is None else str(value).strip()


def _domains(value: Any) -> list[str]:
    """Parse a domains cell (JSON list, comma string, or NULL) into a sorted list."""
    if isinstance(value, list):
        return sorted(_s(v) for v in value if _s(v))
    text = _s(value)
    if text.startswith("["):
        try:
            return sorted(_s(v) for v in json.loads(text) if _s(v))
        except Exception:
            pass
    return sorted(part.strip() for part in text.split(",") if part.strip())


def _encode_domains(values: Any) -> str:
    """Serialise a domain list exactly the way the pipeline stores it (JSON list string)."""
    parts = _domains(values)
    return "[" + ", ".join(json.dumps(p, ensure_ascii=False) for p in parts) + "]"


def plan_updates(gold_rows: list[dict[str, Any]], con: sqlite3.Connection) -> tuple[list[tuple], dict]:
    """Build the update list without writing anything. Aborts on any guard violation."""
    updates: list[tuple] = []
    stats: dict[str, Counter] = {axis: Counter() for axis in AXIS_COLUMN}
    problems: list[str] = []
    for row in gold_rows:
        fb_id = row.get("fb_id")
        stored = con.execute(
            "select content_type, depth, discipline, domains from fbs where fb_id = ?", (fb_id,)
        ).fetchone()
        if stored is None:
            problems.append("gold row missing from DB: " + str(fb_id))
            continue
        current = {"content_type": stored[0], "depth": stored[1], "discipline": stored[2],
                   "domains": stored[3]}
        for axis, (column, auth) in AXIS_COLUMN.items():
            source = _s(row.get(axis + "_source"))
            value = row.get(axis)
            if axis == "depth" and source in NON_APPLICABLE_DEPTH_SOURCES:
                stats[axis]["skipped:n/a-non-principle"] += 1
                continue
            empty = (not _domains(value)) if axis == "domains" else (not _s(value))
            if empty:
                problems.append(str(fb_id) + ": " + axis + " is empty in the anchor")
                continue
            if source not in auth:
                stats[axis]["skipped:source-not-authoritative"] += 1
                continue
            if axis == "domains":
                same = _domains(value) == _domains(current[column])
            else:
                same = _s(value) == _s(current[column])
            if same:
                stats[axis]["already-correct"] += 1
                continue
            stats[axis][source] += 1
            updates.append((column, _encode_domains(value) if axis == "domains" else _s(value), fb_id))
    return updates, {"stats": stats, "problems": problems}


def main() -> int:
    """Diff the anchor against the runtime KB; write only with --apply."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="back up and write (default: dry run)")
    ap.add_argument("--gold", default=str(GOLD))
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()

    gold_rows = [json.loads(line) for line in Path(args.gold).read_text().splitlines() if line.strip()]
    con = sqlite3.connect(args.db)
    updates, report = plan_updates(gold_rows, con)
    if report["problems"]:
        print("ABORT: " + str(len(report["problems"])) + " guard violation(s), nothing written")
        for problem in report["problems"][:10]:
            print("   " + problem)
        con.close()
        return 2

    print("anchor rows: " + str(len(gold_rows)) + " | planned cell updates: " + str(len(updates)))
    for axis in AXIS_COLUMN:
        counts = report["stats"][axis]
        print("  " + axis.ljust(13) + " ".join(k + "=" + str(v) for k, v in sorted(counts.items())))
    if not args.apply:
        print("DRY RUN — nothing written. Re-run with --apply (a backup is taken first).")
        con.close()
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.db, backup_dir / Path(args.db).name)
    print("C13 backup: " + str(backup_dir / Path(args.db).name))

    for column, value, fb_id in updates:
        con.execute("update fbs set " + column + " = ? where fb_id = ?", (value, fb_id))
    con.commit()

    verify_updates, verify = plan_updates(gold_rows, con)
    con.close()
    manifest = {
        "schema_version": "3.0",
        "gen_model": "propagate_4axis_anchor.py (deterministic; no generation)",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "anchor": str(Path(args.gold).name),
        "db": str(Path(args.db).name),
        "backup": str(backup_dir),
        "cells_written": len(updates),
        "per_axis": {axis: dict(report["stats"][axis]) for axis in AXIS_COLUMN},
        "remaining_updates_after_write": len(verify_updates),
        "residual": {axis: dict(verify["stats"][axis]) for axis in AXIS_COLUMN},
    }
    out = REPO / "governance" / ("axis_propagation_manifest_" + stamp + ".json")
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print("rows remaining to update after write: " + str(len(verify_updates)))
    print("R14 manifest: " + str(out.relative_to(REPO)))
    if verify_updates:
        print("WARNING: the write did not converge - inspect the manifest before claiming done")
        return 1
    print("OK: the runtime KB now carries the adjudicated 4-axis labels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
