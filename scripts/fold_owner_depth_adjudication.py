"""Fold owner-adjudicated depth labels for the 58 mapped rows into the depth anchor.

Reads the owner's final depth decisions (owner_depth column) and updates the
consolidated anchor + depth-map source of truth: mapped -> owner_finalized.

Crash-safe write (tempfile -> fsync -> os.replace) per C6; backup before write per C13.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path

VALID_LABELS = {"domain", "cross-domain", "specialized", "universal"}


def load_owner_decisions(path: Path) -> dict[str, str]:
    """Return {item_id: owner_depth} from the owner-filled worksheet CSV."""
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    out: dict[str, str] = {}
    for r in rows:
        oid = (r.get("item_id") or "").strip()
        od = (r.get("owner_depth") or "").strip()
        if oid and od:
            if od not in VALID_LABELS:
                raise ValueError(f"invalid owner_depth {od!r} for {oid}")
            out[oid] = od
    return out


def label_to_depth(rows: list[dict]) -> dict[str, int]:
    """Infer numeric depth for each label from already-adjudicated rows."""
    by_label: dict[str, Counter] = {}
    for r in rows:
        src = r.get("depth_source")
        if src in ("canonical_adjudicated", "owner_finalized"):
            by_label.setdefault(r["depth_label"], Counter())[r["depth"]] += 1
    return {lbl: c.most_common(1)[0][0] for lbl, c in by_label.items()}


def safe_write_json(path: Path, data: object) -> None:
    """Crash-safe JSON write: tempfile -> fsync -> os.replace (C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def backup(path: Path) -> Path:
    """Copy path to a timestamped .bak sibling (C13)."""
    bak = path.with_suffix(path.suffix + f".bak_{int(__import__('time').time())}")
    shutil.copy2(path, bak)
    return bak


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner-csv", default="temp/depth_58_owner_filled.csv")
    ap.add_argument("--depth-map", default="governance/ANCHOR_208_DEPTH_CORRECTED_20261002.json")
    ap.add_argument("--consolidated", default="governance/ANCHOR_208_CONSOLIDATED_20261002.json")
    ap.add_argument("--apply", action="store_true", help="write (otherwise dry-run)")
    args = ap.parse_args()

    owner = load_owner_decisions(Path(args.owner_csv))
    print(f"owner decisions loaded: {len(owner)}")

    # --- depth-map source of truth (list) ---
    depth_map = json.load(open(args.depth_map))
    l2d = label_to_depth(depth_map)
    print(f"label->depth map: {l2d}")
    changed = []
    for r in depth_map:
        oid = r["item_id"]
        if oid in owner:
            r["depth_label"] = owner[oid]
            r["depth"] = l2d[owner[oid]]
            r["depth_source"] = "owner_finalized"
            changed.append(oid)

    # --- consolidated anchor (dict with rows) ---
    cons = json.load(open(args.consolidated))
    for r in cons["rows"]:
        oid = r["item_id"]
        if oid in owner:
            r["depth_label"] = owner[oid]
            r["depth"] = l2d[owner[oid]]
            r["depth_source"] = "owner_finalized"
            r["depth_golden_eligible"] = True

    # report
    print(f"folded rows: {len(changed)}")
    if len(changed) != 58:
        print("WARNING: expected 58 folded rows, got", len(changed))
    ds = Counter(r["depth_source"] for r in depth_map)
    dl = Counter(r["depth_label"] for r in depth_map if r["depth_source"] == "owner_finalized")
    print("depth_map depth_source:", dict(ds))
    print("depth_map label dist (post-fold):", dict(Counter(r['depth_label'] for r in depth_map)))
    elig = Counter(r["depth_golden_eligible"] for r in cons["rows"])
    print("consolidated golden_eligible:", dict(elig))

    if args.apply:
        b1 = backup(Path(args.depth_map))
        b2 = backup(Path(args.consolidated))
        safe_write_json(Path(args.depth_map), depth_map)
        safe_write_json(Path(args.consolidated), cons)
        print(f"backed up -> {b1.name}, {b2.name}")
        print("WROTE (applied)")
    else:
        print("DRY RUN — pass --apply to write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
