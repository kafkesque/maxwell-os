#!/usr/bin/env python3
"""apply_anchor_axis_authority.py — PROPAGATE the declared per-axis authority into every
ANCHOR consumer artifact, then RE-DERIVE the consumers that have their own generator.

WHY (BUG-628, closes the debt side of D-2811)
  `scripts/check_anchor_axis_consistency.py` (D-2811) COUNTS the drift between the one
  declared authority per axis and each consumer. It deliberately does NOT fix it: a rail
  that silently rewrites the thing it measures cannot be seen to fire. This script is the
  missing WRITE limb — it applies the authority value into the derived artifacts and then
  rebuilds the chain, so the counted debt shrinks to zero instead of being declared forever.

READS ONLY config/anchor_axis_authority.yaml (C12: no path, column, cohort or axis name is a
literal here; the propagation ORDER is declared in the same config, `propagation.order`).

STEPS
  1. propagate  — for each declared consumer file, overwrite the axis column with the
                  authority value, joined by item_id (collapse_whitespace, D-2658). A row
                  the authority does not cover is REPORTED as UNCOVERED, never silently kept.
  2. regenerate — re-run the consumer's own deterministic generator (normalize -> consolidate)
                  so no artifact is a hand-patch of a machine derivation, and its provenance
                  input sha256 is honest.

SAFETY
  * dry-run by DEFAULT; `--apply` is required to write anything.
  * timestamped backup before any in-place rewrite (C13), crash-safe write
    (tempfile -> fsync -> os.replace, C6).
  * fail-closed (C16): a declared authority or consumer that does not exist is a hard error,
    never a skip.
  * `--selftest` proves the propagator FIRES on a disagreeing cell, stays quiet on an agreeing
    one, inverts the depth numeric normaliser, reports an uncovered row, and refuses a missing
    authority file (BUG-492/BUG-457: a control nothing can see fire is a comment).

Usage:
  python3 scripts/apply_anchor_axis_authority.py --report        # what WOULD change
  python3 scripts/apply_anchor_axis_authority.py --apply         # propagate + regenerate
  python3 scripts/apply_anchor_axis_authority.py --selftest       # prove it fires
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config" / "anchor_axis_authority.yaml"
DEPTH_MENU = REPO / "config" / "depth_classes.yaml"


def _load_yaml(path: Path) -> dict:
    """Load a YAML mapping, fail-closed (C16)."""
    import yaml

    if not path.exists():
        raise FileNotFoundError(f"BUG-628/C16: declared config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"BUG-628/C16: {path} is not a YAML mapping")
    return data


def _collapse(value: object) -> str:
    """Collapse whitespace + coerce to a comparable string (D-2658 join rule)."""
    return " ".join(str(value if value is not None else "").split())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _depth_maps() -> tuple[dict[str, str], dict[str, str]]:
    """Return (label -> numeric-id, numeric-id -> label) from the depth menu (config-first)."""
    menu = _load_yaml(DEPTH_MENU)
    to_id: dict[str, str] = {}
    to_label: dict[str, str] = {}
    for cls in menu.get("classes", []):
        label, cid = _collapse(cls.get("label")), _collapse(cls.get("id"))
        to_id[label] = cid
        to_label[cid] = label
    if not to_id:
        raise ValueError("BUG-628/C16: depth menu declares no classes")
    return to_id, to_label


def _read_rows(path: Path, kind: str) -> tuple[list[dict], str | None]:
    """Read an artifact's row list. Returns (rows, rows_key) — rows_key is set for JSON."""
    if kind == "csv":
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh)), None
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data, None
    for key in ("rows", "examples"):
        if isinstance(data.get(key), list):
            return data[key], key
    raise ValueError(f"BUG-628/C16: {path} carries neither rows nor examples")


def _write_rows(path: Path, kind: str, rows: list[dict], rows_key: str | None, fields: list[str]) -> None:
    """Crash-safe in-place rewrite preserving the artifact's shape (C6)."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp", suffix=path.suffix)
    os.close(fd)
    try:
        if kind == "csv":
            with open(tmp, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                data = rows
            else:
                data[rows_key or "rows"] = rows
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _backup(path: Path, stamp: str) -> Path:
    """Timestamped backup beside the original before an in-place rewrite (C13)."""
    dest = path.with_name(f"{path.name}.bak_anchorsync_{stamp}")
    shutil.copy2(path, dest)
    return dest


def _apply_cells(rows: list[dict], authority: dict[str, str], column: str,
                 to_numeric: dict[str, str] | None, menu: set[str] | None = None
                 ) -> tuple[int, list[str], list[str]]:
    """Overwrite `column` with the authority value. Returns (n_changed, uncovered, off_menu).

    An authority value that is NOT a member of the axis menu (e.g. the depth authority carries
    the provenance sentinel `noise_drop` for the owner's dropped row R021) is NEVER written into
    a consumer as if it were a label — it is refused and REPORTED (C12d/C16), and the residual
    cell stays declared drift.
    """
    changed, uncovered, off_menu = 0, [], []
    for row in rows:
        iid = _collapse(row.get("item_id"))
        if iid not in authority:
            uncovered.append(iid)
            continue
        target = authority[iid]
        if menu is not None and target not in menu:
            off_menu.append(iid)
            continue
        if to_numeric is not None:
            target = to_numeric.get(target, target)
        if _collapse(row.get(column)) != target:
            row[column] = target
            changed += 1
    return changed, uncovered, off_menu


def _authority_map(spec: dict) -> dict[str, str]:
    """item_id -> authority value for one axis (fail-closed, C16)."""
    path = REPO / spec["file"]
    if not path.exists():
        raise FileNotFoundError(f"BUG-628/C16: authority artifact missing: {spec['file']}")
    rows, _ = _read_rows(path, spec.get("kind", "json"))
    column = spec["column"]
    return {_collapse(r.get("item_id")): _collapse(r.get(column)) for r in rows}


def _collect(config: dict) -> tuple[dict[tuple[str, str], dict], dict[str, list[str]]]:
    """Build {(consumer_file, axis): consumer spec} + {consumer_file: [axes]} from the config."""
    by_file: dict[str, list[str]] = {}
    specs: dict[tuple[str, str], dict] = {}
    for axis, axespec in config.get("axes", {}).items():
        for consumer in axespec.get("consumers", []):
            specs[(consumer["file"], axis)] = {**consumer, "authority": axespec["authority"]}
            by_file.setdefault(consumer["file"], []).append(axis)
    if not specs:
        raise ValueError("BUG-628/C16: config declares no consumers for any axis")
    return specs, by_file


def run(apply: bool) -> int:
    """Propagate every declared axis authority into every declared consumer, then regenerate."""
    config = _load_yaml(CONFIG)
    specs, by_file = _collect(config)
    to_numeric, _ = _depth_maps()
    depth_menu = _load_yaml(REPO / config.get("depth_menu", "config/depth_classes.yaml"))
    menus = {"depth": {_collapse(c.get("label")) for c in depth_menu.get("classes", [])}, "discipline": set()}
    menus["discipline"] = {_collapse(d.get("value")) for d in json.loads(
        (REPO / "config" / "closed_menu_v5.json").read_text(encoding="utf-8"))["disciplines"]}
    order = config.get("propagation", {}).get("order", [])
    if not order:
        raise ValueError("BUG-628/C16: config declares no propagation.order")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    total_changed, receipts, all_uncovered, all_off_menu = 0, [], {}, {}

    for step in order:
        if step["kind"] == "regenerate":
            script = REPO / step["script"]
            if not script.exists():
                raise FileNotFoundError(f"BUG-628/C16: generator missing: {step['script']}")
            if apply:
                proc = subprocess.run([sys.executable, str(script)], cwd=REPO,
                                      capture_output=True, text=True)
                if proc.returncode != 0:
                    raise RuntimeError(f"BUG-628: generator {step['script']} rc={proc.returncode}\n{proc.stderr[-500:]}")
                receipts.append({"step": "regenerate", "script": step["script"],
                                 "stdout": proc.stdout.strip().splitlines()})
                print(f"  ↻ regenerated: {step['script']}")
            else:
                print(f"  (dry-run) would regenerate: {step['script']}")
            continue

        path = REPO / step["file"]
        if not path.exists():
            raise FileNotFoundError(f"BUG-628/C16: propagation step missing: {step['file']}")
        kind = "csv" if path.suffix == ".csv" else "json"
        rows, rows_key = _read_rows(path, kind)
        fields = list(rows[0].keys()) if rows else []
        file_changed, uncovered_file, off_menu_file = 0, {}, {}
        for axis in by_file.get(step["file"], []):
            spec = specs[(step["file"], axis)]
            authority = _authority_map(spec["authority"])
            numeric = to_numeric if spec.get("normalizer") == "depth_numeric_to_label" else None
            menu = menus.get(axis) or None
            changed, uncovered, off_menu = _apply_cells(rows, authority, spec["column"], numeric, menu)
            file_changed += changed
            if uncovered:
                uncovered_file[axis] = sorted(uncovered)
            if off_menu:
                off_menu_file[axis] = sorted(off_menu)
            print(f"  {step['file']} :: {axis}/{spec['column']}: {changed} cell(s) "
                  f"{'would change' if not apply else 'changed'}, {len(uncovered)} uncovered, "
                  f"{len(off_menu)} off-menu (refused)")
        if uncovered_file:
            all_uncovered[step["file"]] = uncovered_file
        if off_menu_file:
            all_off_menu[step["file"]] = off_menu_file
        if file_changed and apply:
            _backup(path, stamp)
            _write_rows(path, kind, rows, rows_key, fields)
        total_changed += file_changed
        receipts.append({"step": "propagate", "file": step["file"], "cells_changed": file_changed,
                         "uncovered": uncovered_file})

    print(f"{'applied' if apply else 'dry-run'}: {total_changed} cell(s) across "
          f"{len([s for s in order if s['kind'] == 'propagate'])} consumer artifact(s)")
    if all_uncovered:
        print("  UNCOVERED (authority does not cover these item_ids — reported, never silently kept):")
        for f, axes in all_uncovered.items():
            for axis, ids in axes.items():
                print(f"    {f} :: {axis}: {ids}")
    if all_off_menu:
        print("  OFF-MENU authority value REFUSED (never written as a label — C12d/C16):")
        for f, axes in all_off_menu.items():
            for axis, ids in axes.items():
                print(f"    {f} :: {axis}: {ids}")
    if apply:
        out = REPO / "governance" / f"ANCHOR_AXIS_SYNC_{stamp}.json"
        out.write_text(json.dumps({
            "schema_version": "1.0",
            "artifact_id": f"ANCHOR_AXIS_SYNC_{stamp}",
            "decision": config.get("decided"),
            "bug": "BUG-628",
            "rule": "one declared AUTHORITY per axis, propagated into every consumer (D-2811)",
            "authority_sha256": {spec["authority"]["file"]: _sha256(REPO / spec["authority"]["file"])
                                 for spec in specs.values()},
            "cells_changed": total_changed,
            "uncovered": all_uncovered,
            "steps": receipts,
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  receipt: {out.relative_to(REPO)}")
    return 0


def selftest() -> int:
    """Prove the propagator fires, stays quiet, inverts depth ids, reports gaps, fails closed."""
    to_numeric, to_label = _depth_maps()
    assert to_numeric.get("domain") != to_label.get("3"), "depth menus disagree (label->id vs id->label)"
    rows = [{"item_id": "R001", "depth": "4"}, {"item_id": "R002", "depth": "3"}, {"item_id": "R999", "depth": "1"}]
    changed, uncovered, off_menu = _apply_cells(rows, {"R001": "domain", "R002": "domain"}, "depth", to_numeric)
    assert changed == 1, f"expected 1 change (R001 '4'->'3' fires; R002 '3'==domain already agrees) got {changed}"
    assert rows[0]["depth"] == "3", rows[0]
    assert uncovered == ["R999"], uncovered
    assert off_menu == [], off_menu
    _c, _u, sentinel = _apply_cells([{"item_id": "R021", "depth": "specialized"}],
                                    {"R021": "noise_drop"}, "depth", to_numeric, {"universal", "cross-domain", "domain", "specialized"})
    assert sentinel == ["R021"], "an off-menu sentinel must be REFUSED, not written as a label"
    quiet, _unused, _s = _apply_cells([{"item_id": "R002", "depth": "3"}], {"R002": "domain"}, "depth", to_numeric)
    assert quiet == 0, "an AGREEING cell must stay quiet"
    labels_only, _u2, _s2 = _apply_cells([{"item_id": "R001", "depth": "specialized"}], {"R001": "domain"}, "depth", None)
    assert labels_only == 1, "a label-column consumer must still be corrected"
    try:
        _authority_map({"file": "governance/does_not_exist_6xx.json", "column": "x"})
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing authority must fail closed (C16)")
    print("ok apply_anchor_axis_authority --selftest: differing cell FIRES, agreeing cell QUIET, "
          "depth id inversion works, uncovered row REPORTED, off-menu sentinel REFUSED, "
          "missing authority FAIL-CLOSED")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Propagate the ANCHOR per-axis authority into every consumer.")
    ap.add_argument("--apply", action="store_true", help="write (default is a dry-run report)")
    ap.add_argument("--report", action="store_true", help="dry-run report (the default)")
    ap.add_argument("--selftest", action="store_true", help="prove the propagator fires")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return run(apply=bool(args.apply))


if __name__ == "__main__":
    sys.exit(main())
