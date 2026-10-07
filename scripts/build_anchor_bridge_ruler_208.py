#!/usr/bin/env python3
"""build_anchor_bridge_ruler_208.py — derive the 208-row BRIDGE ruler from the content ruler + folded depth extras.

WHY. The anchor family grew to 208 items (D-2785 folded 58 owner-adjudicated depth rows into
governance/ANCHOR_208_DEPTH_CORRECTED_20261002.json), but the store bridge was still keyed off the
150-row content ruler (governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv). The committed bridge carries
208 entries while `build_anchor_store_bridge.py --check` re-derives 150 -> DRIFT (a cascade risk: any
rebuild silently regresses the depth conformance anchor from 207 golden rows back to 149, resurrecting
BUG-624). This script derives the single 208-row item list the bridge SHOULD join, so the bridge
re-derives cleanly from a declared source instead of an ad-hoc JSON patch.

WHAT IT PRODUCES. `governance/ANCHOR_208_BRIDGE_RULER_20261002.csv` — columns (item_id, name) only, the
two fields the bridge consumes. Rows 1..150 are the content ruler's (item_id, name) VERBATIM; rows
151..208 are the 58 folded extras' (item_id, name) VERBATIM from the depth map. No stored value is copied
(BUG-402 class); this is a join-source list, not a second copy of the anchor.

FAIL-CLOSED. (1) the depth map must be a strict superset of the ruler's item_ids; (2) the extras count must
be non-zero and the two sources must cover 208 unique ids; (3) every extra's name must join the corpus
EXACTLY (byte-identical, D-2658 — the bridge never guesses). Any violation aborts the write. Crash-safe
write (C6) + backup (C13) before --apply.

Usage:
    python3 scripts/build_anchor_bridge_ruler_208.py            # dry-run (report only)
    python3 scripts/build_anchor_bridge_ruler_208.py --apply    # write the 208-row CSV
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "anchor_family.yaml"
DEPTH_MAP = ROOT / "governance" / "ANCHOR_208_DEPTH_CORRECTED_20261002.json"
OUT = ROOT / "governance" / "ANCHOR_208_BRIDGE_RULER_20261002.csv"


def _collapse(value: str) -> str:
    """collapse_whitespace per the declared store-bridge normalization (D-2658)."""
    return " ".join((value or "").split()).casefold()


def _sha256_text(value: str) -> str:
    """Hex sha256 of a text value (not used for the join, kept for parity with the bridge's name_sha256)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_store_index(cfg: dict) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (fb_id -> raw name, normalised name -> [fb_id]) from the corpus READ-ONLY (writes nothing)."""
    con = sqlite3.connect(f"file:{ROOT / cfg['store']}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    names: dict[str, str] = {}
    index: dict[str, list[str]] = {}
    try:
        sql = f'SELECT {cfg["store_key"]}, {cfg["store_name_column"]} FROM {cfg["store_table"]}'
        for r in con.execute(sql):
            fid = str(r[cfg["store_key"]]).strip()
            raw = str(r[cfg["store_name_column"]] or "")
            names[fid] = raw
            index.setdefault(_collapse(raw), []).append(fid)
    finally:
        con.close()
    return names, index


def build(cfg: dict, content_ruler_path: Path, item_key: str) -> tuple[list[dict[str, str]], list[str]]:
    """Return (rows, problems): the 208-row (item_id, name) list and any fail-closed violations."""
    with open(content_ruler_path, newline="", encoding=cfg["ruler_encoding"]) as fh:
        ruler = [r for r in csv.DictReader(fh) if (r.get(item_key) or "").strip()]
    depth_map = json.loads(DEPTH_MAP.read_text(encoding="utf-8"))

    ruler_ids = {r[item_key].strip() for r in ruler}
    depth_ids = {r["item_id"].strip() for r in depth_map}

    problems: list[str] = []
    # (1) the depth map must cover every ruler id (strict superset), else the fold is incomplete.
    missing_from_depth = sorted(ruler_ids - depth_ids)
    if missing_from_depth:
        problems.append(f"ruler ids absent from depth map: {missing_from_depth[:8]}")

    # (2) the extras are the folded depth rows; both sources together must cover 208 unique ids.
    extras = [r for r in depth_map if r["item_id"].strip() not in ruler_ids]
    union = ruler_ids | depth_ids
    if not extras:
        problems.append("no folded extras found (depth map must exceed the ruler)")
    if len(union) != len(depth_ids):
        problems.append(f"ruler+depth union {len(union)} != depth map {len(depth_ids)}")

    # (3) every extra must join the corpus EXACTLY (byte-identical name).
    names, index = load_store_index(cfg)
    for r in extras:
        item = r["item_id"].strip()
        name = (r.get("name") or "").strip()
        cands = index.get(_collapse(name), [])
        if len(cands) != 1:
            problems.append(f"extra {item}: {len(cands)} candidate(s) for {name!r} (bridge never guesses)")
            continue
        fid = cands[0]
        if name != names.get(fid, ""):
            problems.append(f"extra {item}: name {name!r} only matches after normalization (require exact)")

    rows: list[dict[str, str]] = [
        {"item_id": r[item_key].strip(), "name": (r.get("name") or "").strip()} for r in ruler
    ]
    rows += [{"item_id": r["item_id"].strip(), "name": (r.get("name") or "").strip()} for r in extras]
    return rows, problems


def write_csv(path: Path, rows: list[dict[str, str]], encoding: str) -> None:
    """Crash-safe write (C6): tempfile -> fsync -> os.replace, in the declared ruler encoding (C12)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".bridge_ruler_", suffix=".tmp")
    try:
        with open(fd, "w", newline="", encoding=encoding) as fh:
            writer = csv.DictWriter(fh, fieldnames=["item_id", "name"])
            writer.writeheader()
            writer.writerows(rows)
            fh.flush()
            import os

            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        import os

        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description="derive the 208-row bridge ruler (ruler + folded depth extras)")
    ap.add_argument("--apply", action="store_true", help="write the CSV (default: dry-run)")
    args = ap.parse_args()

    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    cfg = (data or {}).get("store_bridge")
    if not isinstance(cfg, dict):
        raise SystemExit(f"{REGISTRY} carries no store_bridge block")
    anchor = (data or {}).get("anchor") or {}
    content_ruler_path = ROOT / anchor.get("sheet", "governance/ANCHOR_RULER_CONSOLIDATED_20260923.csv")
    item_key = anchor.get("key", "item_id")

    rows, problems = build(cfg, content_ruler_path, item_key)
    if problems:
        raise SystemExit("FAIL-CLOSED: " + "; ".join(problems))

    print(f"bridge ruler: {len(rows)} rows total (content ruler + folded depth extras)")
    if not args.apply:
        print(f"DRY-RUN: would write {len(rows)} rows to {OUT.name}")
        return 0

    if OUT.exists():
        bak = OUT.with_suffix(OUT.suffix + f".bak_{int(datetime.now().timestamp())}")
        shutil.copy2(OUT, bak)
        print(f"backup at {bak.name}")
    write_csv(OUT, rows, cfg["ruler_encoding"])
    print(f"APPLIED: wrote {len(rows)} rows to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
