#!/usr/bin/env python3
"""Compact an append-only JSONL checkpoint to one line per id (last-wins).

The joint-vote checkpoint is append-only (C23): re-votes append NEW lines for an
id instead of mutating prior lines. `_load_checkpoint()` dedupes last-wins, so
duplicate lines are cosmetically harmless, but compacting is cleaner and matches
the loader's exact output (BUG-234).

Contract:
  * Read-only on the input; writes via tempfile + fsync + os.replace (C6).
  * Last-wins: for each id, the final line's record wins.
  * Output order = first-occurrence order of ids (stable, deterministic), so the
    compacted file is byte-for-byte equivalent to `_load_checkpoint()` output.
  * The id key defaults to "fb_id" (the joint-vote checkpoint key); it is a CLI
    arg so the script is reusable for other append-only checkpoints.

Usage:
  python3 scripts/compact_checkpoint_lastwins.py \
      --in  governance/joint_vote_production_checkpoint.jsonl \
      --out governance/joint_vote_production_checkpoint.jsonl \
      --key fb_id
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List


def _load_lastwins(path: Path, key: str) -> tuple[List[str], Dict[str, dict]]:
    """Return (first-occurrence id order, id -> last-wins record)."""
    order: List[str] = []
    last: Dict[str, dict] = {}
    raw_lines = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw_lines += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                print(f"WARN: skipping unparseable line {raw_lines}", file=sys.stderr)
                continue
            if key not in rec:
                print(f"WARN: line {raw_lines} missing key '{key}', skipping", file=sys.stderr)
                continue
            rid = rec[key]
            if rid not in last:
                order.append(rid)
            last[rid] = rec
    return order, last


def _atomic_write(path: Path, lines: List[str]) -> None:
    """Write lines via tempfile + fsync + os.replace (crash-safe, C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".compact_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for line in lines:
                fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description="Compact append-only JSONL to last-wins one-line-per-id")
    ap.add_argument("--in", dest="inp", required=True, help="input checkpoint path")
    ap.add_argument("--out", required=True, help="output checkpoint path (may equal --in for in-place)")
    ap.add_argument("--key", default="fb_id", help="id field key (default: fb_id)")
    args = ap.parse_args()

    inp = Path(args.inp)
    if not inp.exists():
        print(f"FATAL: input not found: {inp}", file=sys.stderr)
        return 1

    order, last = _load_lastwins(inp, args.key)
    lines = [json.dumps(last[rid], ensure_ascii=False) + "\n" for rid in order]

    _atomic_write(Path(args.out), lines)

    print(f"input:  {inp}")
    print(f"output: {args.out}")
    print(f"ids:    {len(order)} unique (last-wins)")
    print(f"lines:  {len(lines)} written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
