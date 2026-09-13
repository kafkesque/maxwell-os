#!/usr/bin/env python3
"""reconcile_review_queue.py — D2618 P0.4: reconcile the 25 missing abstained fb_ids.

Root cause (verified): the joint-vote checkpoint has 25 fb_ids DUPLICATED (8,016
lines / 7,991 unique). Of those 25, under union-abstain semantics (a fb_id is an
abstain if ANY record abstained), all 25 are genuine abstains — but the review
queue (2,431) + active-learning sample (298) were built from a LAST-RECORD view,
so the 25 fell out of the abstain set (17 of them had a later "agreed" record
that masked an earlier "abstain" record).

Fix (deterministic, fail-closed):
  1. Dedup the checkpoint to one record per fb_id, with needs_review = True if
     ANY record abstained (union; abstain-wins). Emits joint_vote_production_checkpoint.dedup.jsonl
     as a sidecar (does NOT clobber the production checkpoint).
  2. Append the 25 missing abstain rows to s4_review_queue.jsonl with the correct
     review_axis + disagreement_pair + proposals (derived from the abstaining
     record's votes).

Usage:
  python3 scripts/reconcile_review_queue.py            # dry-run: report only
  python3 scripts/reconcile_review_queue.py --apply    # dedup sidecar + append queue
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = ROOT / "governance" / "joint_vote_production_checkpoint.jsonl"
DEDUP_OUT = ROOT / "governance" / "joint_vote_production_checkpoint.dedup.jsonl"
QUEUE = ROOT / "governance" / "s4_review_queue.jsonl"
SAMPLE = ROOT / "governance" / "s4_active_learning_sample.jsonl"

SCHEMA_VERSION = "3.0"
PIPELINE_COMMIT = "v3.0-D2618-p0"
RELIABLE = ("deepseek-v4-pro", "Qwen3.8-27B-MLX-4bit")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_records() -> Dict[str, List[Dict[str, Any]]]:
    recs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for line in CHECKPOINT.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        recs[r["fb_id"]].append(r)
    return recs


def _load_ids(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    ids: Set[str] = set()
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        ids.add(json.loads(line)["fb_id"])
    return ids


def _abstain_record(rs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The abstaining record (first with needs_review=True); else the last."""
    for r in rs:
        if r.get("needs_review") is True:
            return r
    return rs[-1]


def _review_axis(votes: Dict[str, Any]) -> tuple[str, tuple[str, str]]:
    """Derive (review_axis, disagreement_pair) from the abstaining record's votes."""
    ds = votes.get(RELIABLE[0], {})
    qw = votes.get(RELIABLE[1], {})
    ds_ct = str(ds.get("content_type") or "")
    qw_ct = str(qw.get("content_type") or "")
    ds_dp = str(ds.get("depth") or "")
    qw_dp = str(qw.get("depth") or "")
    if ds_ct != qw_ct:
        return ("content_type", tuple(sorted([ds_ct, qw_ct])))
    if ds_dp != qw_dp:
        return ("depth", tuple(sorted([ds_dp, qw_dp])))
    return ("content_type", tuple(sorted([ds_ct, qw_ct])))


def _build_queue_row(rec: Dict[str, Any]) -> Dict[str, Any]:
    axis, pair = _review_axis(rec.get("votes", {}))
    proposals = {
        RELIABLE[0]: rec.get("votes", {}).get(RELIABLE[0], {}).get("content_type"),
        RELIABLE[1]: rec.get("votes", {}).get(RELIABLE[1], {}).get("content_type"),
    }
    return {
        "fb_id": rec["fb_id"],
        "name": rec.get("name"),
        "review_axis": axis,
        "disagreement_pair": list(pair),
        "proposals": proposals,
        "status": "abstain_review_queue",
        "schema_version": SCHEMA_VERSION,
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": _now_iso(),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Reconcile the 25 missing abstained fb_ids (D2618 P0.4).")
    ap.add_argument("--apply", action="store_true", help="write dedup sidecar + append queue (default: dry-run)")
    args = ap.parse_args()

    recs = _load_records()
    dup = [fb for fb, rs in recs.items() if len(rs) > 1]
    union_abstain = {fb for fb, rs in recs.items() if any(r.get("needs_review") is True for r in rs)}
    q = _load_ids(QUEUE)
    s = _load_ids(SAMPLE)
    missing = union_abstain - (q | s)

    print(f"checkpoint unique fb_ids: {len(recs)}")
    print(f"duplicated fb_ids: {len(dup)}")
    print(f"union-abstain fb_ids: {len(union_abstain)}")
    print(f"queue {len(q)} + sample {len(s)} = {len(q | s)}")
    print(f"MISSING abstains: {len(missing)}")

    rows = [_build_queue_row(_abstain_record(recs[fb])) for fb in sorted(missing)]
    axes = Counter(r["review_axis"] for r in rows)
    print(f"missing review_axis: {dict(axes)}")

    if not args.apply:
        print("[dry-run] nothing written. use --apply.")
        return

    # 1. dedup sidecar (union-abstain) — C6 atomic.
    dedup_rows = []
    for fb in sorted(recs):
        rs = recs[fb]
        base = _abstain_record(rs)
        base = dict(base)
        base["needs_review"] = any(r.get("needs_review") is True for r in rs)
        base["deduped_from"] = len(rs)
        dedup_rows.append(base)
    content = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in dedup_rows)
    d = DEDUP_OUT.parent
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".jsonl")
    with open(fd, "w", encoding="utf-8") as fh:
        fh.write(content)
        fh.flush()
        import os
        os.fsync(fh.fileno())
    import os
    os.replace(tmp, DEDUP_OUT)

    # 2. append missing rows to the review queue (C13 backup of queue first).
    shutil.copy2(QUEUE, QUEUE.with_name(QUEUE.name + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"))
    with QUEUE.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")

    print(f"wrote dedup sidecar: {DEDUP_OUT} ({len(dedup_rows)} unique)")
    print(f"appended {len(rows)} rows to {QUEUE}")


if __name__ == "__main__":
    main()
