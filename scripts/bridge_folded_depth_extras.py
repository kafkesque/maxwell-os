#!/usr/bin/env python3
"""bridge_folded_depth_extras.py — extend the anchor store bridge with the 58 folded depth extras (BUG-624).

WHY. D-2785 folded 58 owner-adjudicated depth rows (R151..R203) into
governance/ANCHOR_208_DEPTH_CORRECTED_20261002.json (depth golden 149 -> 207), but
governance/ANCHOR_STORE_BRIDGE_20260926.json still carries only the 150 rows it was built
from (149 owner + R021 noise_drop). build_depth_anchor_conformance.py iterates the bridge
entries, so the conformance anchor is silently underpowered at 149 vs the 207 golden.

WHAT IT DOES. Re-joins the 58 extras to the corpus with the SAME deterministic rule as the
bridge (collapse_whitespace name -> fb_id; exact-first; never guesses, D-2658) and adds them
to the bridge's `entries`, updating `join.counts` and recording provenance in a `depth_fold`
note. It copies NO stored value (BUG-402 class) — only the join.

FAIL-CLOSED. Every extra must join EXACTLY (byte-identical name). Any normalized, ambiguous,
or unresolved extra ABORTS the whole write (the bridge never guesses). Crash-safe write
(C6: tempfile -> fsync -> os.replace) + backup (C13: copy2) before --apply.

Usage:
    python3 scripts/bridge_folded_depth_extras.py            # dry-run (report only)
    python3 scripts/bridge_folded_depth_extras.py --apply    # write the extended bridge
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPTH_MAP = ROOT / "governance" / "ANCHOR_208_DEPTH_CORRECTED_20261002.json"
BRIDGE = ROOT / "governance" / "ANCHOR_STORE_BRIDGE_20260926.json"
STORE = ROOT / "knowledge pipeline" / "maxwell.db"


def _collapse(s: str) -> str:
    return " ".join((s or "").split()).casefold()


def _load_store() -> tuple[dict[str, str], dict[str, list[str]]]:
    """Return (fb_id -> raw name, normalized name -> [fb_id]) from the corpus (read-only)."""
    con = sqlite3.connect(f"file:{STORE}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    names: dict[str, str] = {}
    index: dict[str, list[str]] = {}
    try:
        for r in con.execute("SELECT fb_id, name FROM fbs"):
            fid = str(r["fb_id"]).strip()
            raw = str(r["name"] or "")
            names[fid] = raw
            index.setdefault(_collapse(raw), []).append(fid)
    finally:
        con.close()
    return names, index


def extend(dry: bool) -> dict:
    depth_map = json.loads(DEPTH_MAP.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    bridged_ids = {e["item_id"] for e in bridge["entries"].values()}
    extras = [r for r in depth_map if r["item_id"] not in bridged_ids]

    names, index = _load_store()
    added: dict[str, dict] = {}
    problems: list[str] = []
    for r in extras:
        item = r["item_id"]
        name = (r.get("name") or "").strip()
        cands = index.get(_collapse(name), [])
        if len(cands) != 1:
            problems.append(f"{item}: {len(cands)} candidate(s) for {name!r} (bridge never guesses)")
            continue
        fid = cands[0]
        if name != names.get(fid, ""):
            problems.append(f"{item}: name {name!r} only matches after normalization (require exact)")
            continue
        added[fid] = {
            "item_id": item,
            "name": name,
            "name_sha256": __import__("hashlib").sha256(name.encode("utf-8")).hexdigest(),
            "join": "exact",
            "join_note": "byte-identical name (folded depth extra, D-2785)",
        }

    if problems:
        raise SystemExit("FAIL-CLOSED: bridge extension aborted — " + "; ".join(problems))

    new_entries = dict(bridge["entries"])
    new_entries.update(added)
    counts = bridge["join"]["counts"]
    new_counts = dict(counts)
    new_counts["rows"] = counts["rows"] + len(added)
    new_counts["joined"] = counts["joined"] + len(added)
    new_counts["exact"] = counts["exact"] + len(added)

    doc = json.loads(json.dumps(bridge))
    doc["entries"] = new_entries
    doc["join"]["counts"] = new_counts
    doc.setdefault("depth_fold", {})
    doc["depth_fold"] = {
        "folded_extras_added": len(added),
        "added_item_ids": sorted(a["item_id"] for a in added.values()),
        "fold_decision": "D-2785",
        "bug": "BUG-624",
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }

    if dry:
        print(f"DRY-RUN: would add {len(added)} folded extras to the bridge")
        print(f"  join.counts rows {counts['rows']} -> {new_counts['rows']}")
        print(f"  join.counts joined {counts['joined']} -> {new_counts['joined']}")
        print(f"  join.counts exact {counts['exact']} -> {new_counts['exact']}")
        print(f"  added item_ids: {sorted(a['item_id'] for a in added.values())}")
        return doc

    # crash-safe write (C6) after backup (C13)
    bak = BRIDGE.with_suffix(BRIDGE.suffix + f".bak_{int(datetime.now().timestamp())}")
    shutil.copy2(BRIDGE, bak)
    fd, tmp = tempfile.mkstemp(dir=str(BRIDGE.parent), prefix=".bridge_", suffix=".tmp")
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            import os
            os.fsync(fh.fileno())
        os.replace(tmp, BRIDGE)
    except BaseException:
        import os
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print(f"APPLIED: added {len(added)} folded extras; backup at {bak.name}")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the extended bridge (default: dry-run)")
    args = ap.parse_args()
    extend(dry=not args.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
