#!/usr/bin/env python3
"""Finalize Phase 1 (D2616): apply the merged 4-axis golden labels for the
149-core verified set to maxwell.db, plus the #85 human verdict (cross-domain).

Deterministic, LLM-free. The authoritative merged 4-axis source is
`governance/golden_synced_4axis.jsonl` (content_type + depth from the
DeepSeek+Qwen reliable pair / human / 298-human; discipline + domains from
golden-silver / p5 review). The production DB was only partially synced by the
earlier passes (Phase 0 relabels, Phase 1 298-row adjudication, 27 flagged-core
human verdicts, 200 p5 discipline/domain fields) — the 72 RESOLVED + 49 clean
149-core rows never had their joint-vote content_type/depth materialised.

This script closes that gap:

    target for each 149-core row (from golden_synced_4axis):
        content_type = golden content_type
        depth        = golden depth if content_type == 'principle' else ''
        status       = 'PASS'        if content_type == 'principle' else 'QUARANTINE'
        needs_human_review = 0       (human-reviewed / reliable-pair confirmed)

    plus #85 Iterative Design Refinement: depth 'domain' -> 'cross-domain'
    (pair split cross-domain vs universal; user ruled cross-domain).

Safety (mirrors apply_phase1_adjudication.py):
  - C13: timestamped DB backup BEFORE any write.
  - C6:  single SQLite transaction; rolls back on any failure.
  - Idempotent: skips rows already at target state.
  - --check (default): dry-run; --apply: back up + apply + R14 manifest + integrity.

Manifest: governance/phase1_finalize_manifest.jsonl (one row per FB, R14-stamped).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.io_guard import safe_write  # noqa: E402  C6 atomic write

DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"
LEDGER = ROOT / "governance" / "phase0_adjudication_ledger.jsonl"
GOLDEN = ROOT / "governance" / "golden_synced_4axis.jsonl"
MANIFEST = ROOT / "governance" / "phase1_finalize_manifest.jsonl"

SCHEMA_VERSION = "3.0"
GEN_MODEL = "human+reliable-pair"  # deterministic materialisation of verified labels
PIPELINE_COMMIT = "v3.0-D2616-phase1-finalize"

# #85 Iterative Design Refinement — user ruled cross-domain (pair split).
EXTRA_DEPTH = {
    "dec446fd98e0c78a422db8e21733068041bd4a4b0c3cdca399d85218ce651954": "cross-domain",
}


def _load_golden_by_id() -> dict[str, dict]:
    by_id: dict[str, dict] = {}
    for line in GOLDEN.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        g = json.loads(line)
        by_id[g["id"]] = g
    return by_id


def _plan(golden_by_id: dict[str, dict]) -> tuple[list[dict], int, int]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT fb_id, content_type, depth, status, needs_human_review FROM fbs"
    ).fetchall()
    db = {r["fb_id"]: dict(r) for r in rows}
    conn.close()

    # 149-core example ids from the ledger (100 flagged + 49 clean).
    core_ids: set[str] = set()
    for line in LEDGER.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        core_ids.add(json.loads(line)["example_id"])

    changes: list[dict] = []
    skipped_missing = 0
    skipped_already = 0

    for eid in sorted(core_ids):
        g = golden_by_id.get(eid)
        if g is None:
            skipped_missing += 1
            continue
        fb = g["fb_id"]
        cur = db.get(fb)
        if cur is None:
            skipped_missing += 1
            continue

        ct = g["content_type"] or ""
        if not ct:
            # No reliable-pair/human content_type — leave untouched (fail-closed).
            continue
        depth = (g["depth"] or "") if ct == "principle" else ""
        status = "PASS" if ct == "principle" else "QUARANTINE"

        # #85 human override (depth only, already principle/PASS).
        if fb in EXTRA_DEPTH:
            depth = EXTRA_DEPTH[fb]
            status = "PASS"

        nhr = 0
        if (
            cur["content_type"] == ct
            and (cur["depth"] or "") == depth
            and cur["status"] == status
            and (cur["needs_human_review"] or 0) == nhr
        ):
            skipped_already += 1
            continue

        changes.append({
            "fb_id": fb,
            "name": g["name"],
            "golden_id": eid,
            "old_content_type": cur["content_type"],
            "new_content_type": ct,
            "old_depth": cur["depth"],
            "new_depth": depth,
            "old_status": cur["status"],
            "new_status": status,
            "old_needs_human_review": cur["needs_human_review"],
            "new_needs_human_review": nhr,
        })

    return changes, skipped_missing, skipped_already


def _backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB_PATH.with_name(f"maxwell.db.bak_{ts}_pre_phase1_finalize")
    shutil.copy2(DB_PATH, bak)
    return bak


def _apply(changes: list[dict]) -> None:
    bak = _backup()
    print(f"  🔒 C13 backup: {bak}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for c in changes:
            conn.execute(
                "UPDATE fbs SET content_type=?, depth=?, status=?, needs_human_review=? "
                "WHERE fb_id=?",
                (c["new_content_type"], c["new_depth"], c["new_status"],
                 c["new_needs_human_review"], c["fb_id"]),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"❌ apply failed, rolled back (DB intact): {e}", file=sys.stderr)
        raise
    conn.close()

    now = datetime.now(timezone.utc).isoformat()
    lines = []
    for c in changes:
        rec = dict(c)
        rec.update({
            "schema_version": SCHEMA_VERSION,
            "gen_model": GEN_MODEL,
            "pipeline_commit": PIPELINE_COMMIT,
            "created_at": now,
            "source": "governance/golden_synced_4axis.jsonl (merged 4-axis)",
        })
        lines.append(json.dumps(rec, ensure_ascii=False))
    safe_write(MANIFEST, "\n".join(lines) + "\n")

    conn = sqlite3.connect(DB_PATH)
    ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    print(f"  ✅ integrity_check: {ok}")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Phase 1 finalize: 149-core 4-axis → DB (D2616)")
    ap.add_argument("--apply", action="store_true", help="back up + apply (default: dry-run)")
    args = ap.parse_args(argv)

    golden_by_id = _load_golden_by_id()
    changes, skipped_missing, skipped_already = _plan(golden_by_id)

    print("🧭 Phase 1 finalize (D2616) — 149-core merged 4-axis → DB")
    print(f"   golden examples loaded:  {len(golden_by_id)}")
    print(f"   → to apply (state change): {len(changes)}")
    print(f"   → skipped missing:         {skipped_missing}")
    print(f"   → skipped already applied: {skipped_already}")

    if not changes:
        print("   ✅ nothing to do.")
        return 0

    ct = Counter(c["new_content_type"] for c in changes)
    st = Counter(c["new_status"] for c in changes)
    ctflip = sum(1 for c in changes if c["old_content_type"] != c["new_content_type"])
    dflip = sum(1 for c in changes if (c["old_depth"] or "") != c["new_depth"])
    print(f"   new content_type dist: {dict(ct)}")
    print(f"   new status dist:       {dict(st)}")
    print(f"   content_type flips: {ctflip} | depth flips: {dflip}")
    print(f"   #85 override rows: {sum(1 for c in changes if c['fb_id'] in EXTRA_DEPTH)}")

    if not args.apply:
        print("\n   (dry-run) pass --apply to back up + write.")
        return 0

    _apply(changes)
    print(f"   ✅ applied {len(changes)} changes. Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
