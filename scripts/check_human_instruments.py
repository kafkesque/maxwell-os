#!/usr/bin/env python3
"""RAIL 1 (BUG-430): refuse any drift in an owner-authored artifact, column by column.

The owner's classifications are the one thing a session must never edit. Whole-file sha256 is too strict
(the append-only sheets legitimately gain rows and columns) and per-column is exactly right: a protected
column - any column whose name contains `human` or `owner` - must be byte-identical to its lock.
Adding a column: allowed. Removing or rewriting one: FAIL, naming the column.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
LOCKS = REPO / "config" / "human_instrument_locks.yaml"
HINT = ("human", "owner")


def load_records(path: Path) -> list[dict]:
    """Read a locked instrument as records: CSV by header, JSONL by object keys.

    A JSONL instrument read with `csv.DictReader` yields one nonsense "column" per raw line, which made the
    first run of this rail fail with a fake column name. The reader must match the format (BUG-431).
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        import json
        return [json.loads(l) for l in text.splitlines() if l.strip()]
    return list(csv.DictReader(text.splitlines()))


def col_sha(rows: list[dict], col: str) -> str:
    """Stable hash of one column's cells, row order preserved."""
    vals = [(v if isinstance(v, str) else json.dumps(v, sort_keys=True)) if (v := r.get(col)) is not None else "" for r in rows]
    return hashlib.sha256("|".join(vals).encode()).hexdigest()


def main() -> int:
    """Re-derive every lock and report any divergence."""
    cfg = yaml.safe_load(LOCKS.read_text(encoding="utf-8"))
    bad: list[str] = []
    for inst in cfg["instruments"]:
        path = REPO / inst["path"]
        if not path.exists():
            bad.append(f"MISSING  {inst['path']}")
            continue
        rows = load_records(path)
        cols = list(rows[0].keys()) if rows else []
        for col, want in (inst.get("protected_columns") or {}).items():
            if col not in cols:
                bad.append(f"REMOVED  {inst['path']}::{col}")
            elif col_sha(rows, col) != want:
                bad.append(f"REWRITTEN {inst['path']}::{col}")
        extra = [c for c in cols if any(h in c.lower() for h in HINT) and c not in (inst.get("protected_columns") or {})]
        if extra:
            bad.append(f"NEW PROTECTED COLUMN (needs an explicit lock + owner note) {inst['path']}::{extra}")
    if bad:
        print("FAIL human instruments:")
        for b in bad:
            print("  ", b)
        return 1
    print(f"ok human instruments: {len(cfg['instruments'])} locked, all protected columns byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
