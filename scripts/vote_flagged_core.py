#!/usr/bin/env python3
"""Targeted reliable-pair vote for the 25 flagged 149-core FBs missing from the
production joint-vote checkpoint (D2616 Phase 1, user-directed).

Reuses build_joint_vote_set's vote_once() (DeepSeek-v4-pro + Qwen3.8-27B reliable
pair, D2610 unanimous-or-abstain policy) but targets SPECIFIC fb_ids instead of a
seeded sample. Results are APPENDED to the production checkpoint
(governance/joint_vote_production_checkpoint.jsonl) — resumable, last-wins dedup.

Usage:
  python3 scripts/vote_flagged_core.py            # dry-run: list the 25, no calls
  python3 scripts/vote_flagged_core.py --run      # vote (DeepSeek cloud + OMLX local)
  python3 scripts/vote_flagged_core.py --run --workers 3
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(ROOT / "scripts"))
import build_joint_vote_set as bjv  # noqa: E402

DB = ROOT / "knowledge pipeline" / "maxwell.db"
CHECKPOINT = ROOT / "governance" / "joint_vote_production_checkpoint.jsonl"
VOTE_SET = ROOT / "governance" / "flagged_core_vote_set.jsonl"


def _load_targets() -> list[str]:
    """The 25 flagged 149-core source fb_ids missing from the checkpoint."""
    if not VOTE_SET.exists():
        raise SystemExit(f"❌ vote set not found: {VOTE_SET}")
    return [json.loads(l)["fb_id"] for l in VOTE_SET.open() if l.strip()]


def _load_fb_data(fb_ids: list[str]) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    q = ",".join("?" * len(fb_ids))
    rows = con.execute(
        f"SELECT fb_id, name, definition, mechanism, boundary, depth FROM fbs "
        f"WHERE fb_id IN ({q}) ORDER BY fb_id", fb_ids).fetchall()
    con.close()
    return [dict(r) for r in rows]


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="vote (default: dry-run)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
    args = ap.parse_args(argv)

    fb_ids = _load_targets()
    fbs = _load_fb_data(fb_ids)
    policy = bjv._load_policy()
    voters = bjv._load_voters()
    voters = [v for v in voters if v.get("model") in set(policy["reliable"])]

    # Point the checkpoint reader at the PRODUCTION checkpoint (last-wins dedup).
    bjv.OUT_CHECKPOINT = CHECKPOINT

    # DeepSeek key: env var, else .env (C22 opt-in, same as run_joint_vote.sh).
    key = args.key or os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for ln in env.read_text().splitlines():
                if ln.strip().startswith("DEEPSEEK_API_KEY="):
                    key = ln.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        raise SystemExit("FATAL: no DEEPSEEK_API_KEY in env or .env (C22 opt-in)")

    done = bjv._load_checkpoint()
    # Re-vote incomplete rows (pass prior votes -> only the failed voter re-pays).
    work = []
    for fb in fbs:
        prior = done.get(fb["fb_id"])
        if prior is None:
            work.append((fb, None))
        else:
            v = prior.get("votes", {})
            if any(isinstance(x, dict) and "error" in x for x in v.values()):
                work.append((fb, v))

    print(f"🧭 targeted reliable-pair vote — flagged 149-core")
    print(f"   vote set: {len(fb_ids)} | loaded: {len(fbs)} | to vote (new+retry): {len(work)}")
    print(f"   voters: {[v['model'] for v in voters]} | policy: {policy['policy']} | key: {'set' if key else 'MISSING'}")

    if not args.run:
        print("\n   (dry-run) pass --run to vote.")
        return 0

    if not work:
        print("   ✅ nothing to vote.")
        return 0

    lock = Lock()
    n = 0
    with CHECKPOINT.open("a", encoding="utf-8") as fh:
        def _handle(fb, pv):
            return bjv.vote_once(fb, voters, key, policy, pv)

        def _emit(rec):
            nonlocal n
            with lock:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
            n += 1
            print(f"[{n}/{len(work)}] {rec['fb_id'][:10]} ct={rec['content_type'] or '(abstain)'} "
                  f"depth={rec['depth'] or '(none)'} review={rec['needs_review']}", flush=True)

        if args.workers > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                futs = {pool.submit(_handle, fb, pv): fb for fb, pv in work}
                for fut in as_completed(futs):
                    _emit(fut.result())
        else:
            for fb, pv in work:
                _emit(_handle(fb, pv))

    records = list(bjv._load_checkpoint().values())
    print(f"\n✅ checkpoint now: {len(records)} unique FBs")
    print(f"   flagged-core voted: {len(work)} new rows")
    ct = Counter(r.get("content_type") or "(abstain)" for r in records if r["fb_id"] in fb_ids)
    dp = Counter(r.get("depth") or "(abstain)" for r in records if r["fb_id"] in fb_ids)
    print(f"   content_type: {dict(ct)}")
    print(f"   depth (principle): {dict(dp)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
