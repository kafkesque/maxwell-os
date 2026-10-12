#!/usr/bin/env python3
"""scripts/diff_bug712_reroute.py — BUG-712 retro re-stamp READ-ONLY diff (no mutation).

WHY: D-2938 (persist_resolved_content_type) landed as the PRODUCER fix, but rows committed
before it may still carry the RAW S2 content_type where the deterministic D-2747 reroute would
correct it (BUG-719: principle-typed rows that actually belong in a non-principle sidecar).
This script is the GOVERNED RE-STAMP gate's first pass: it computes, for every row in the live
store, what `reroute_content_type` (the ONE deterministic router, C21) would emit, and reports
the BEFORE→AFTER diff. It WRITES NOTHING (read-only DSN, R-D410): the apply step is a separate,
C13-backed, owner-gated mutation.

This is a SPOT-CHECK tool, not the apply path: it exists so a human (and the owner gate) can see
exactly which rows would move, before any store mutation is approved.

Exit: 0 ok | 1 diff found (expected until the governed re-stamp is applied) | 2 cannot evaluate.
Usage: python3 scripts/diff_bug712_reroute.py [--limit N] [--csv path]
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.content_types import reroute_content_type  # noqa: E402 — the ONE router (C21)
from pipeline.pipeline_paths import DB_PATH  # noqa: E402

# The S6 row columns reroute_content_type needs, reconstructed into the S2-shaped dict it expects.
_BODY_KEYS = ("definition", "mechanism", "boundary", "consequence", "elaboration")
# TI-only body lives in type_body JSON (D-2943); contested is a growth_edge field there too.
_TYPE_BODY_KEYS = ("tool_name", "syntax", "parameters", "contested")

# Extra columns carried into the CSV so the owner can spot-check the WHY of each move.
_SPOT_CHECK_COLS = ("discipline", "extraction_type", "status", "pipeline_run_id", "provenance")


def _fb_from_row(row: sqlite3.Row) -> dict[str, Any]:
    """Reconstruct the S2-shaped dict reroute_content_type expects, from an S6 row."""
    fb: dict[str, Any] = {
        "fb_id": row["fb_id"],
        # `name` MATTERS: `_principle_form_violation` builds its haystack from
        # (name, mechanism, boundary, consequence, elaboration) — omitting it computes the verdict
        # on a TRUNCATED haystack. Measured 2026-10-12 (BUG-712 calibration): 0 manifest effect on
        # the then-current 7,640 rows, i.e. a latent unfaithfulness, not a live wrong number.
        "name": row["name"] or "",
        "content_type": row["content_type"],
    }
    for k in _BODY_KEYS:
        fb[k] = row[k] or ""
    tb = row["type_body"]
    if tb:
        try:
            body = json.loads(tb)
        except (json.JSONDecodeError, TypeError):
            body = {}
        if isinstance(body, dict):
            for k in _TYPE_BODY_KEYS:
                if k in body:
                    fb[k] = body[k]
    return fb


def read_rows(conn: sqlite3.Connection, limit: int | None) -> list[sqlite3.Row]:
    cols = ["fb_id", "name", "content_type", *_BODY_KEYS, "type_body", *_SPOT_CHECK_COLS]
    sql = f"SELECT {', '.join(cols)} FROM fbs"
    if limit:
        sql += f" LIMIT {limit}"
    return list(conn.execute(sql))


def main() -> int:
    ap = argparse.ArgumentParser(description="BUG-712 retro re-stamp read-only diff.")
    ap.add_argument("--limit", type=int, default=None, help="cap the rows read (spot-check)")
    ap.add_argument("--csv", type=str, default=None, help="write the diff to CSV (read-only output)")
    args = ap.parse_args()

    if not DB_PATH.exists():
        print(f"FAIL diff-bug712: DB not found at {DB_PATH}")
        return 2
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = read_rows(conn, args.limit)
    finally:
        conn.close()

    # (fb_id, name, before, after, discipline, extraction_type, status, pipeline_run_id, provenance)
    changes: list[tuple[str, str, str, str, str, str, str, str, str]] = []
    for row in rows:
        fb = _fb_from_row(row)
        before = (row["content_type"] or "").strip()
        after = reroute_content_type(fb)
        if after != before:
            changes.append(
                (
                    row["fb_id"],
                    row["name"] or "",
                    before,
                    after,
                    row["discipline"] or "",
                    row["extraction_type"] or "",
                    row["status"] or "",
                    row["pipeline_run_id"] or "",
                    row["provenance"] or "",
                )
            )

    print(f"read {len(rows)} row(s); {len(changes)} would move under deterministic reroute")
    by_from: dict[str, int] = {}
    by_to: dict[str, int] = {}
    for c in changes:
        before, after = c[2], c[3]
        by_from[before] = by_from.get(before, 0) + 1
        by_to[after] = by_to.get(after, 0) + 1
    if by_from:
        print("  by FROM:", dict(sorted(by_from.items())))
    if by_to:
        print("  by TO:  ", dict(sorted(by_to.items())))

    for fid, name, before, after, *_ in changes[:20]:
        print(f"  {fid}  {name[:48]!r:50}  {before} -> {after}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["fb_id", "name", "before", "after", *_SPOT_CHECK_COLS])
            w.writerows(changes)
        print(f"  wrote {args.csv}")

    if not changes:
        print("ok diff-bug712: store already agrees with the deterministic router — nothing to re-stamp")
        return 0
    print("note diff-bug712: diff is EXPECTED until the governed re-stamp applies (read-only here — never mutates)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
