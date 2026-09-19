#!/usr/bin/env python3
"""vote_remaining_axes.py — reliable-pair vote on the 190 incomplete rows.

Targets the rows in governance/remaining_verification_audit.csv with status
"incomplete" (>=1 axis non-authoritative). Votes depth + discipline + domains
(3 axes in ONE prompt) via the reliable pair (DeepSeek-v4-pro + Qwen3.8-27B),
D2610 unanimous-else-abstain per axis. Only the MISSING axes of a row are later
applied; agreed axes on already-complete rows are discarded.

Reuses revote_queue_59.py's prompt/parse/aggregate/vote machinery (single source
of truth for the 3-axis vote). Resumable checkpoint + preflight + report.

Usage:
  python3 scripts/vote_remaining_axes.py --list
  python3 scripts/vote_remaining_axes.py --run --preflight
  python3 scripts/vote_remaining_axes.py --run --limit 5
  python3 scripts/vote_remaining_axes.py --report
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import revote_queue_59 as rq  # noqa: E402  (single source of truth for the vote)

DB = ROOT / "knowledge pipeline" / "maxwell.db"
AUDIT = ROOT / "governance" / "remaining_verification_audit.csv"
CHECKPOINT = ROOT / "governance" / "remaining_axes_vote_checkpoint.jsonl"
DEFAULT_WORKERS = 2


def _load_cp() -> Dict[str, Dict[str, Any]]:
    """Load MY checkpoint (independent of revote_queue_59's module-level one)."""
    if not CHECKPOINT.exists():
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            out[rec["fb_id"]] = rec
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def _write_cp(records: Dict[str, Dict[str, Any]]) -> None:
    rq._atomic_write(CHECKPOINT, "".join(json.dumps(v, ensure_ascii=False) + "\n" for v in records.values()))


def _load_audit_targets() -> List[str]:
    import csv
    fbids = []
    for row in csv.DictReader(open(AUDIT, encoding="utf-8")):
        if row.get("status") == "incomplete":
            fbids.append(row["fb_id"])
    return fbids


def select_targets(limit: int = 0) -> List[Dict[str, Any]]:
    """Load the incomplete fb_ids + full text (name/definition/mechanism/boundary)."""
    fbids = _load_audit_targets()
    if limit:
        fbids = fbids[:limit]
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    q = "SELECT fb_id, name, definition, mechanism, boundary FROM fbs WHERE fb_id IN (%s)" % (
        ",".join("?" * len(fbids)))
    rows = {r["fb_id"]: r for r in db.execute(q, fbids)}
    db.close()
    out = []
    for fb in fbids:
        r = rows.get(fb)
        if not r:
            continue
        out.append({
            "fb_id": fb,
            "name": r["name"] or "",
            "definition": r["definition"] or "",
            "mechanism": r["mechanism"] or "",
            "boundary": r["boundary"] or "",
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--key", default="")
    args = ap.parse_args()

    if args.list:
        t = select_targets()
        print(f"incomplete targets: {len(t)}")
        for x in t[:10]:
            print("  ", x["fb_id"], x["name"][:50])
        return

    if args.report:
        cp = _load_cp()
        recs = list(cp.values())
        d = sum(1 for r in recs if r.get("depth_agreed"))
        di = sum(1 for r in recs if r.get("discipline_agreed"))
        do = sum(1 for r in recs if r.get("domains_agreed"))
        print(f"voted: {len(recs)} | depth {d} | discipline {di} | domains {do}")
        return

    if args.run:
        import os
        key = args.key or os.environ.get("DEEPSEEK_API_KEY", "")
        if args.preflight:
            rq.preflight(key)
            return
        targets = select_targets(args.limit)
        policy = rq._load_policy()
        voters = rq._load_voters()
        cp = _load_cp()
        todo = [t for t in targets if t["fb_id"] not in cp]
        print(f"targets: {len(targets)} | already voted: {len(targets) - len(todo)} | todo: {len(todo)}")
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(rq.vote_once, fb, voters, key, policy): fb for fb in todo}
            for fut in as_completed(futs):
                fb = futs[fut]
                try:
                    verdict = fut.result()
                except Exception as e:  # noqa: BLE001
                    print(f"  error {fb['fb_id']}: {e}", flush=True)
                    continue
                cp[fb["fb_id"]] = verdict
                done += 1
                if done % 5 == 0:
                    _write_cp(cp)
                    print(f"progress {done}/{len(todo)} (flushed checkpoint)", flush=True)
        _write_cp(cp)
        print(f"done {done}/{len(todo)}")


if __name__ == "__main__":
    main()
