#!/usr/bin/env python3
"""apply_content_type_human_decisions.py — apply a human review batch to the backlog.

Reads a decisions JSON (example_id -> {final, model, agree, note}), appends to the
append-only ledger `governance/content_type_human_decisions.jsonl`, and re-stamps the
backlog `governance/content_type_verification_backlog.json` so those rows become
`human_confirmed` (rank 6). Deterministic, no DB mutation, crash-safe writes.

Usage:
    python3 scripts/apply_content_type_human_decisions.py <decisions.json>
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "governance" / "content_type_verification_backlog.json"
LEDGER = ROOT / "governance" / "content_type_human_decisions.jsonl"


def atomic_write_json(path: Path, obj) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    decisions = json.loads(Path(sys.argv[1]).read_text())
    ts = datetime.now(timezone.utc).isoformat()

    # 1. append to ledger
    with LEDGER.open("a") as f:
        for eid, d in decisions.items():
            rec = {
                "example_id": eid,
                "content_type": d["final"],
                "model_proposal": d.get("model"),
                "agreed": d.get("agree"),
                "note": d.get("note", ""),
                "decided_at": ts,
                "source": "human",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # 2. update backlog
    bl = json.loads(BACKLOG.read_text())
    by_id = {r["example_id"]: r for r in bl["backlog"]}
    for eid, d in decisions.items():
        r = by_id.get(eid)
        if r is None:
            print(f"WARN: {eid} not in backlog")
            continue
        r["status"] = "human_confirmed"
        r["rank"] = 6
        r["content_type"] = d["final"]
        r["confidence"] = "human"
        if d.get("note"):
            r["reason"] = f"human: {d['note']}"

    # recompute counts
    counts: dict[str, int] = {}
    for r in bl["backlog"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    bl["counts"] = counts
    atomic_write_json(BACKLOG, bl)

    print(f"applied {len(decisions)} human decisions to ledger + backlog")
    print("new counts:", json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
