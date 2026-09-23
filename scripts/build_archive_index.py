#!/usr/bin/env python3
"""scripts/build_archive_index.py — the writer and checker for archive/index.yaml (D-365).

WHY this exists: the shipped archive/index.yaml declared `authority: D2226`, a decision whose
state in config/decisions.yaml is REJECTED. It was generated 2026-08-10 against an out-of-repo
archive_root, so the in-repo archive/ (16 GB, 36 top-level entries) was unindexed, and no reader
anywhere consumes the file. An index that is hand-built, never regenerated and never checked
drifts silently — that is BUG-342's class (never re-derive a governance count by hand).

This script READS the bytes on disk and WRITES the index. It never moves, edits or deletes an
archive entry: it registers them. Deletion is a separate, owner-gated act.

Usage:
    python3 scripts/build_archive_index.py            # regenerate archive/index.yaml
    python3 scripts/build_archive_index.py --check    # exit 1 if the index does not match the bytes

Exit codes: 0 ok | 1 drift (--check) or a declared input is missing | 2 config error.
Config: config/archive_index.yaml (C12 — every path and rule lives there, none here).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CFG_PATH = _ROOT / "config" / "archive_index.yaml"


def write_atomic(path: Path, text: str) -> None:
    """Write text via tempfile -> fsync -> os.replace so a crash cannot leave a torn index (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_idx_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load_cfg() -> dict[str, Any]:
    """Load and minimally validate the index contract. Raises on a malformed declaration (C16)."""
    cfg = yaml.safe_load(_CFG_PATH.read_text())
    if not isinstance(cfg, dict) or "rules" not in cfg or "local_archive" not in cfg:
        raise ValueError(f"{_CFG_PATH}: must be a mapping carrying 'local_archive' and 'rules'")
    for rule in cfg["rules"]:
        for key in ("match", "category", "disposition", "reason"):
            if key not in rule:
                raise ValueError(f"{_CFG_PATH}: rule missing '{key}': {rule}")
        re.compile(rule["match"])  # fail loud on a bad pattern, not silently at match time
    return cfg


def classify(name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Return the FIRST matching rule's disposition claim for a top-level archive entry."""
    for rule in cfg["rules"]:
        if re.search(rule["match"], name):
            return {
                "category": rule["category"],
                "disposition": rule["disposition"],
                "authority": rule.get("authority"),
                "reason": rule["reason"],
            }
    return dict(cfg["default"])


def measure(path: Path) -> dict[str, Any]:
    """Measure one entry: bytes, child counts and mtime. Symlinks are resolved for size only."""
    if path.is_dir():
        files = dirs = 0
        total = 0
        for sub in path.rglob("*"):
            if sub.is_dir():
                dirs += 1
            elif sub.is_file():
                files += 1
                try:
                    total += sub.stat().st_size
                except OSError:
                    pass
        return {"kind": "dir", "bytes": total, "files": files, "dirs": dirs}
    return {"kind": "file", "bytes": path.stat().st_size, "files": 1, "dirs": 0}


def scan_local(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Scan the in-repo archive and return (entries, disposition histogram)."""
    root = _ROOT / cfg["local_archive"]
    if not root.is_dir():
        raise FileNotFoundError(f"declared local_archive is not a directory: {root}")
    self_name = Path(cfg["output"]).name
    entries: list[dict[str, Any]] = []
    hist: dict[str, int] = {}
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.name == self_name:
            continue  # the index does not index itself
        claim = classify(child.name, cfg)
        m = measure(child)
        entries.append(
            {
                "name": child.name,
                "kind": m["kind"],
                "bytes": m["bytes"],
                "files": m["files"],
                "dirs": m["dirs"],
                "modified": dt.datetime.fromtimestamp(child.stat().st_mtime).strftime("%Y-%m-%d"),
                **claim,
            }
        )
        hist[claim["disposition"]] = hist.get(claim["disposition"], 0) + 1
    return entries, hist


def scan_external(cfg: dict[str, Any]) -> dict[str, Any]:
    """Report the out-of-repo archive_root the previous index described. Never operated on."""
    spec = cfg.get("external_archive_root") or {}
    out: dict[str, Any] = dict(spec)
    path = Path(spec.get("path", ""))
    out["present"] = path.is_dir()
    out["entries"] = len(list(path.iterdir())) if out["present"] else 0
    return out


def build_body(cfg: dict[str, Any]) -> dict[str, Any]:
    """Build the deterministic body of the index (everything except stamps)."""
    entries, hist = scan_local(cfg)
    total = sum(e["bytes"] for e in entries)
    return {
        "schema_version": cfg["schema_version"],
        "authority": cfg["decision"],
        "scope": cfg["local_archive"],
        "note": (
            "Regenerated by scripts/build_archive_index.py; every entry is MEASURED from the bytes "
            "on disk. Nothing here is hand-written, and this script never moves or deletes an entry."
        ),
        "local_archive": {
            "path": cfg["local_archive"],
            "entries": len(entries),
            "bytes": total,
            "dispositions": dict(sorted(hist.items())),
            "index": entries,
        },
        "external_archive_root": scan_external(cfg),
        "dispositions_vocabulary": cfg["dispositions"],
    }


def body_hash(body: dict[str, Any]) -> str:
    """Stable hash of the derived body, so --check can see any drift in the inventory."""
    canon = yaml.safe_dump(body, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def render(cfg: dict[str, Any], body: dict[str, Any], stamp: str) -> str:
    """Render the final document: body + body hash + generation stamp."""
    doc = {"generated": stamp, "body_sha256": body_hash(body), **body}
    return (
        "# archive/index.yaml — GENERATED by scripts/build_archive_index.py (D-365). Do not hand-edit.\n"
        "# Authority: " + cfg["decision"] + " | check: just health -> scripts/build_archive_index.py --check\n"
        + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
    )


def main() -> int:
    """Regenerate the index, or verify it against the bytes on disk."""
    ap = argparse.ArgumentParser(description="archive index writer/checker (D-365)")
    ap.add_argument("--check", action="store_true", help="exit 1 if the index does not match the bytes")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    try:
        cfg = load_cfg()
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR config: {exc}", file=sys.stderr)
        return 2
    try:
        body = build_body(cfg)
    except FileNotFoundError as exc:
        print(f"ERROR declared input: {exc}", file=sys.stderr)
        return 1

    out = _ROOT / cfg["output"]
    want = body_hash(body)

    if args.check:
        if not out.is_file():
            print(f"RED archive index: {cfg['output']} is missing", file=sys.stderr)
            return 1
        have = yaml.safe_load(out.read_text()).get("body_sha256")
        if have != want:
            print(
                f"RED archive index: {cfg['output']} is STALE — stored body_sha256 {str(have)[:12]} "
                f"!= measured {want[:12]}. Run: python3 scripts/build_archive_index.py",
                file=sys.stderr,
            )
            return 1
        la = body["local_archive"]
        print(
            f"  ok   archive index in sync ({la['entries']} entries, "
            f"{la['bytes'] / 1e9:.1f} GB, dispositions {la['dispositions']})"
        )
        return 0

    stamp = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    write_atomic(out, render(cfg, body, stamp))
    la = body["local_archive"]
    if not args.quiet:
        print(f"archive index written: {cfg['output']} ({la['entries']} entries, {la['bytes'] / 1e9:.1f} GB)")
        for name, n in sorted(la["dispositions"].items()):
            print(f"  {name}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
