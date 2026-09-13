#!/usr/bin/env python3
"""repass_pair_agreed.py — D2618 P0.3: re-PASS the 1,750 wrongly-quarantined rows.

The reliable-pair joint vote (D2612) UNANIMOUSLY agreed (content_type=principle
+ depth agreed, high confidence) on 1,750 production rows that are currently
sitting in `status=QUARANTINE` with `needs_human_review=0`. These are clean
principle rows that got fail-closed to quarantine during the Phase-0/1 relabel
cascade; the pair's vote is the authoritative label, so they should serve (PASS).

Deterministic, LLM-free, idempotent. Does NOT touch the 1,246 genuine abstains
(860 content_type-abstain + 386 depth-abstain) or the 517 needs_human_review=1
rows — those remain quarantined for human review.

Actions (single transaction):
  - status: QUARANTINE -> PASS
  - depth:  pair-agreed vote depth (fixes the 381 stale silver depths)

Safety:
  - C13: timestamped DB backup before any write.
  - C6:  single transaction; rollback on any error.
  - Idempotent: rows already PASS with matching depth are skipped.
  - --check (default): dry-run, reports the exact change set, writes nothing.
  - --apply: backup + transaction + R14 manifest.

Usage:
  python3 scripts/repass_pair_agreed.py            # dry-run
  python3 scripts/repass_pair_agreed.py --apply    # back up + apply + manifest
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"
CHECKPOINT = ROOT / "governance" / "joint_vote_production_checkpoint.jsonl"
MANIFEST = ROOT / "governance" / "repass_pair_agreed_manifest.jsonl"

SCHEMA_VERSION = "3.0"
GEN_MODEL = "repass_pair_agreed.py (deterministic; no generation)"
PIPELINE_COMMIT = "v3.0-D2618-p0"


def _load_checkpoint() -> Dict[str, Dict[str, Any]]:
    cp: Dict[str, Dict[str, Any]] = {}
    for line in CHECKPOINT.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        cp[rec["fb_id"]] = rec
    return cp


def _plan() -> Tuple[List[Dict[str, Any]], int, int]:
    """Return the exact change set: pair-agreed clean rows in QUARANTINE."""
    cp = _load_checkpoint()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT fb_id, content_type, depth, status FROM fbs "
        "WHERE content_type='principle' AND status='QUARANTINE' AND needs_human_review=0"
    ).fetchall()
    conn.close()

    changes: List[Dict[str, Any]] = []
    skipped_missing = 0
    skipped_already = 0
    for r in rows:
        rec = cp.get(r["fb_id"])
        if rec is None:
            skipped_missing += 1
            continue
        if rec.get("content_type_agreed") is not True or rec.get("agreed") is not True:
            # content_type or depth abstain -> NOT a clean row, leave quarantined.
            continue
        vote_depth = rec.get("depth")
        if r["depth"] == vote_depth and r["status"] == "PASS":
            skipped_already += 1
            continue
        changes.append({
            "fb_id": r["fb_id"],
            "old_status": r["status"],
            "new_status": "PASS",
            "old_depth": r["depth"],
            "new_depth": vote_depth,
        })
    return changes, skipped_missing, skipped_already


def _backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB_PATH.with_name(f"maxwell.db.bak_{ts}_pre_repass")
    shutil.copy2(DB_PATH, bak)
    return bak


def _apply(changes: List[Dict[str, Any]]) -> Path:
    bak = _backup()
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            for c in changes:
                conn.execute(
                    "UPDATE fbs SET status=?, depth=? WHERE fb_id=?",
                    (c["new_status"], c["new_depth"], c["fb_id"]),
                )
    except Exception:
        conn.close()
        raise
    conn.close()
    return bak


def _manifest(changes: List[Dict[str, Any]], bak: Path) -> None:
    depth_fixes = sum(1 for c in changes if c["old_depth"] != c["new_depth"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rows_repassed": len(changes),
        "rows_depth_synced": depth_fixes,
        "backup": str(bak),
        "depth_distribution": dict(Counter(c["new_depth"] for c in changes)),
    }
    lines = [json.dumps(summary, ensure_ascii=False)]
    lines += [json.dumps(c, ensure_ascii=False) for c in changes]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Re-PASS the 1,750 pair-agreed clean rows (D2618 P0.3).")
    ap.add_argument("--apply", action="store_true", help="back up + apply + manifest (default: dry-run)")
    args = ap.parse_args()

    changes, skipped_missing, skipped_already = _plan()
    depth_fixes = sum(1 for c in changes if c["old_depth"] != c["new_depth"])
    print(f"pair-agreed clean rows to re-PASS: {len(changes)}")
    print(f"  of which depth needs sync: {depth_fixes}")
    print(f"  depth distribution: {dict(Counter(c['new_depth'] for c in changes))}")
    print(f"  skipped (no checkpoint record): {skipped_missing}")
    print(f"  skipped (already PASS + matching depth): {skipped_already}")

    if not args.apply:
        print("[dry-run] nothing written. use --apply to execute.")
        return

    bak = _apply(changes)
    _manifest(changes, bak)
    print(f"applied {len(changes)} re-PASSes; backup {bak}")
    print(f"manifest written: {MANIFEST}")


if __name__ == "__main__":
    main()
