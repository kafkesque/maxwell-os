#!/usr/bin/env python3
"""build_anchor_ruler_from_adjudication.py - derive the 208-ruler from OWNER RULINGS (T-191 / D-3116).

WHY. The 208-row bridge ruler names dangle after the D-2881 re-chunk (BUG-956): 195/208 names no longer
match any corpus row under ``rechunk-v4-20260929``. T-191 re-anchors them by OWNER ADJUDICATION, recorded in
the adjudication sheet's ``owner_ruling_fb_id`` / ``owner_ruling_note`` columns - the ONLY authoritative
rulings (suggested_fb_id is advisory, D-2658: the bridge never guesses).

WHAT IT DOES. It is the missing CONSUMER of ``owner_ruling_fb_id``. For each MATCH ruling it resolves the
owner's 64-hex ``fb_id`` to that row's corpus NAME and emits a ruler row keyed by CONTENT (an exact join).
For each NONE ruling it records the row in a DECLARED-NONE manifest (the ceiling shrinks LOUDLY, never
silently). It carries forward every non-adjudicated ruler row unchanged. Output is a new ruler CSV that the
existing ``build_anchor_store_bridge.py`` consumes - this script does NOT re-implement the join.

WHY NAME-FROM-FB_ID. The owner ruled "this concept IS this fb_id". The ruler row's content-name therefore
becomes the fb_id's own corpus name, which joins BYTE-IDENTICALLY (exact). Joining on the old dangling name
would fail again. A MATCH whose fb_id is absent from the store is a HARD ERROR, never a silent drop.

FORMAT GUARD (MEASURED 2026-10-22, the no-b sheet). A row whose ``owner_ruling_fb_id`` is the literal
"MATCH" or "NONE" (not a 64-hex) is a BROKEN write - the placeholder sits in the id column. This script
REFUSES such a sheet rather than treat the placeholder as a ruling (a declaration must RESOLVE, D-3034).

Usage: python3 scripts/build_anchor_ruler_from_adjudication.py [--print-config|--selftest]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "config" / "anchor_family.yaml"
FB_ID_RE = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDERS = frozenset({"MATCH", "NONE"})
NOTE_MATCH = "MATCH"
NOTE_NONE = "NONE"
SCHEMA_VERSION = "1.0"
GEN_MODEL = "none (deterministic ruling consumer; no LLM)"
EXIT_OK, EXIT_DEFECT = 0, 1


def sha256_file(path: Path) -> str:
    """Return the hex sha256 of a file, streamed so a large store never has to fit in memory."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config() -> dict:
    """Load the store_bridge block (C12: no path or rule lives in this file)."""
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    cfg = (data or {}).get("store_bridge")
    if not isinstance(cfg, dict):
        raise KeyError(f"{REGISTRY} carries no store_bridge block")
    ra = cfg.get("ruler_apply")
    if not isinstance(ra, dict):
        raise KeyError(f"{REGISTRY} store_bridge carries no ruler_apply block")
    for key in ("adjudication_sheet", "carried_forward_from", "declared_none_manifest"):
        if not ra.get(key):
            raise KeyError(f"{REGISTRY} store_bridge.ruler_apply.{key} is not declared")
    return cfg


def read_adjudication(path: Path) -> List[Dict[str, str]]:
    """Read the adjudication sheet, stripped of BOM/whitespace, and refuse a broken-format sheet (D-3034)."""
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k is not None} for r in csv.DictReader(fh)]
    rows = [r for r in rows if r.get("item_id")]
    bad = [r["item_id"] for r in rows if r.get("owner_ruling_fb_id", "") in PLACEHOLDERS]
    if bad:
        raise ValueError(
            f"REFUSED: {len(bad)} row(s) carry a literal 'MATCH'/'NONE' in owner_ruling_fb_id - a broken "
            f"write, not a ruling: {bad[:8]} (use the correctly-formatted sheet)")
    return rows


def read_fb_names(cfg: dict, fb_ids: List[str]) -> Dict[str, str]:
    """Resolve fb_id -> corpus name for the MATCH rulings, READ-ONLY against the store."""
    import sqlite3

    names: Dict[str, str] = {}
    if not fb_ids:
        return names
    con = sqlite3.connect(f"file:{ROOT / cfg['store']}?mode=ro", uri=True)
    try:
        placeholders = ",".join("?" * len(fb_ids))
        sql = (f"SELECT {cfg['store_key']}, {cfg['store_name_column']} FROM {cfg['store_table']} "
               f"WHERE {cfg['store_key']} IN ({placeholders})")
        for key, name in con.execute(sql, fb_ids):
            names[str(key).strip()] = str(name or "")
    finally:
        con.close()
    return names


def classify(rows: List[Dict[str, str]], names: Dict[str, str]) -> Tuple[List[dict], List[dict], List[str]]:
    """Split rows into (match_ruler_rows, declared_none_rows, missing_fb_ids). Pure over its inputs."""
    match_rows: List[dict] = []
    none_rows: List[dict] = []
    missing: List[str] = []
    for r in rows:
        item = r["item_id"]
        fb = r.get("owner_ruling_fb_id", "")
        note = (r.get("owner_ruling_note", "") or "").upper()
        if fb:
            if not FB_ID_RE.match(fb):
                raise ValueError(f"{item}: owner_ruling_fb_id {fb!r} is not a 64-hex content address")
            if note and note != NOTE_MATCH:
                raise ValueError(f"{item}: carries an fb_id but note {note!r} != {NOTE_MATCH!r}")
            name = names.get(fb)
            if not name:
                missing.append(f"{item}:{fb}")
                continue
            match_rows.append({"item_id": item, "name": name, "fb_id": fb})
        elif note == NOTE_NONE:
            none_rows.append({"item_id": item, "ruler_name": r.get("ruler_name", ""), "note": NOTE_NONE})
        elif note in ("", NOTE_MATCH):
            # Empty id + empty note = no ruling yet; an empty id with note MATCH is a contradiction.
            if note == NOTE_MATCH:
                raise ValueError(f"{item}: note MATCH but owner_ruling_fb_id is empty")
            none_rows.append({"item_id": item, "ruler_name": r.get("ruler_name", ""), "note": ""})
        else:
            raise ValueError(f"{item}: unrecognised owner_ruling_note {note!r}")
    return match_rows, none_rows, missing


def read_carried_forward(old_ruler: Path, adjudicated: set) -> List[dict]:
    """Ruler rows NOT covered by the adjudication sheet are carried forward unchanged (they already join)."""
    with old_ruler.open(newline="", encoding="utf-8-sig") as fh:
        rows = [{k.strip(): (v or "").strip() for k, v in r.items() if k is not None} for r in csv.DictReader(fh)]
    return [{"item_id": r["item_id"], "name": r["name"]}
            for r in rows if r.get("item_id") and r["item_id"] not in adjudicated]


def verify_join(cfg: dict, ruler_rows: List[dict]) -> dict:
    """Re-use the BRIDGE's own resolver to prove every emitted ruler row joins exactly (0 ambiguous, 0 unresolved)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_anchor_store_bridge as bridge

    raw_names, index, run_of = bridge.read_store(cfg)
    res = bridge.resolve(ruler_rows, index, cfg, raw_names, run_of, cfg.get("canonical_run"))
    return res


def write_crash_safe(path: Path, render: Any) -> None:
    """Crash-safe write (C6): tempfile -> fsync -> os.replace; ``render(fh)`` writes the body."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            render(fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_ruler(path: Path, rows: List[dict]) -> None:
    """Write the ruler CSV (columns item_id,name) crash-safe."""
    def render(fh: Any) -> None:
        w = csv.DictWriter(fh, fieldnames=["item_id", "name"])
        w.writeheader()
        for r in rows:
            w.writerow({"item_id": r["item_id"], "name": r["name"]})
    write_crash_safe(path, render)


def write_manifest(path: Path, sheet: Path, rows: List[dict], carried: int) -> None:
    """Write the DECLARED-NONE manifest: the shrunk ceiling, recorded loudly."""
    doc = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "ANCHOR-208-RECHUNKV4-DECLARED-NONE",
        "generated_by": "scripts/build_anchor_ruler_from_adjudication.py",
        "gen_model": GEN_MODEL,
        "pipeline_commit": os.environ.get("MAXWELL_COMMIT", "uncommitted"),
        "source_sheet": {"path": str(sheet.relative_to(ROOT)), "sha256": sha256_file(sheet)},
        "carried_forward_rows": carried,
        "count": len(rows),
        "rows": rows,
    }
    def render(fh: Any) -> None:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    write_crash_safe(path, render)


def selftest() -> int:
    """Known-answer controls: every rule this script depends on fails LOUDLY if inverted."""
    bad = 0
    def check(label: str, got: Any, want: Any) -> None:
        nonlocal bad
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            bad += 1

    names = {"a" * 64: "Alpha"}
    rows = [
        {"item_id": "R1", "ruler_name": "x", "owner_ruling_fb_id": "a" * 64, "owner_ruling_note": "MATCH"},
        {"item_id": "R2", "ruler_name": "y", "owner_ruling_fb_id": "", "owner_ruling_note": "NONE"},
        {"item_id": "R3", "ruler_name": "z", "owner_ruling_fb_id": "", "owner_ruling_note": ""},
    ]
    m, n, miss = classify(rows, names)
    check("MATCH resolves to store name", m[0]["name"], "Alpha")
    check("NONE recorded", [x["item_id"] for x in n if x["note"] == "NONE"], ["R2"])
    check("empty ruling recorded", [x["item_id"] for x in n if x["note"] == ""], ["R3"])
    check("no missing", miss, [])
    try:
        classify([{"item_id": "R9", "owner_ruling_fb_id": "MATCH", "owner_ruling_note": ""}], names)
        check("placeholder rejected", "accepted", "raised")
    except ValueError:
        check("placeholder rejected", "raised", "raised")
    _m2, _n2, miss2 = classify([{"item_id": "R9", "owner_ruling_fb_id": "f" * 64,
                                  "owner_ruling_note": "MATCH"}], {})
    check("missing fb_id is flagged, never silently dropped", len(miss2), 1)
    print(f"ruler-apply selftest: {'ok' if bad == 0 else f'{bad} FAILED'}")
    return EXIT_OK if bad == 0 else EXIT_DEFECT


def main(argv: List[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="derive the 208-ruler from owner rulings (T-191)")
    ap.add_argument("--print-config", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    cfg = load_config()
    if args.print_config:
        print(yaml.safe_dump(cfg.get("ruler_apply"), sort_keys=True))
        return EXIT_OK

    ra = cfg["ruler_apply"]
    sheet = ROOT / ra["adjudication_sheet"]
    old_ruler = ROOT / ra["carried_forward_from"]
    manifest = ROOT / ra["declared_none_manifest"]
    out_ruler = ROOT / cfg["ruler_sheet"]

    rows = read_adjudication(sheet)
    fb_ids = [r["owner_ruling_fb_id"] for r in rows if r.get("owner_ruling_fb_id")]
    names = read_fb_names(cfg, fb_ids)
    match_rows, none_rows, missing = classify(rows, names)
    if missing:
        print(f"DEFECT: {len(missing)} MATCH ruling(s) point at an fb_id absent from the store: {missing[:8]}",
              file=sys.stderr)
        return EXIT_DEFECT

    carried = read_carried_forward(old_ruler, {r["item_id"] for r in rows})
    ruler_rows = [{"item_id": r["item_id"], "name": r["name"]} for r in match_rows] + carried
    ruler_rows.sort(key=lambda r: r["item_id"])

    res = verify_join(cfg, ruler_rows)
    c = res["counts"]
    print(f"adjudication: {len(rows)} rows -> {len(match_rows)} MATCH, "
          f"{len([x for x in none_rows if x['note'] == NOTE_NONE])} NONE, "
          f"{len([x for x in none_rows if not x['note']])} unruled")
    print(f"ruler: {c['rows']} rows ({len(match_rows)} owner-MATCH + {len(carried)} carried forward)")
    print(f"join: exact={c['exact']} normalized={c['normalized']} run_canonical={c['run_canonical']} "
          f"ambiguous={c['ambiguous']} unresolved={c['unresolved']}")
    if c["ambiguous"] or c["unresolved"]:
        print(f"DEFECT: the derived ruler has ambiguous={res['ambiguous']} unresolved={res['unresolved']}",
              file=sys.stderr)
        return EXIT_DEFECT

    write_ruler(out_ruler, ruler_rows)
    write_manifest(manifest, sheet, [x for x in none_rows if x["note"] == NOTE_NONE], len(carried))
    print(f"wrote {out_ruler.relative_to(ROOT)} ({len(ruler_rows)} rows)")
    print(f"wrote {manifest.relative_to(ROOT)} ({len([x for x in none_rows if x['note'] == NOTE_NONE])} declared NONE)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
