#!/usr/bin/env python3
"""Apply the 1,365 vote-confirmed non-principle relabels to maxwell.db (Phase 0, D2616).

Deterministic, LLM-free data repair. Reads the reliable-pair joint vote
(governance/joint_vote_production_checkpoint.jsonl), selects the rows where BOTH
reliable voters (DeepSeek-v4-pro + Qwen3.8-27B) unanimously agreed the object is
NON-principle (content_type in {noise_drop, process_template, process_instance,
tool_instruction, growth_edge} and content_type_agreed == true), and demotes them
out of the principle index in `knowledge pipeline/maxwell.db`:

    content_type: 'principle' -> voted non-principle value   (demote out of principle index)
    depth:        (any)         -> ''                        (depth is principle-only, BUG-242/D2612)
    status:       (any)         -> 'QUARANTINE'              (stop serving mislabeled noise; fail-closed)

Safety:
  - C13: backs up the DB to maxwell.db.bak_<ts>_pre_phase0_relabel BEFORE any write.
  - C6:  single SQLite transaction; on any error the transaction rolls back.
  - Idempotent: skips rows whose DB content_type is already the target (no double-write).
  - --check (default): dry-run, reports the exact change set, writes nothing.
  - --apply: performs the backup + transaction + manifest.

Usage:
  python3 scripts/apply_phase0_relabels.py            # dry-run (safe)
  python3 scripts/apply_phase0_relabels.py --apply    # back up + apply

Manifest: governance/phase0_relabel_manifest.jsonl (one row per FB, R14-stamped).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.io_guard import safe_write  # noqa: E402  C6 atomic write

DB_PATH = ROOT / "knowledge pipeline" / "maxwell.db"
CHECKPOINT = ROOT / "governance" / "joint_vote_production_checkpoint.jsonl"
MANIFEST = ROOT / "governance" / "phase0_relabel_manifest.jsonl"

# D2616 Phase 0: the 5 non-principle content_type roles + dispositions that the
# reliable-pair vote may have unanimously assigned (never re-declare the enum —
# these are read from the checkpoint, this set is only the target FILTER).
NON_PRINCIPLE_TYPES = frozenset({
    "noise_drop",
    "process_template",
    "process_instance",
    "tool_instruction",
    "growth_edge",
})

# R14 stamps for the manifest rows.
SCHEMA_VERSION = "3.0"
GEN_MODEL = "python"  # deterministic repair — no generative model involved
PIPELINE_COMMIT = "v3.0-D2616"


def _load_targets() -> list[dict]:
    """Return the vote-confirmed non-principle rows (fb_id -> content_type)."""
    targets: list[dict] = []
    if not CHECKPOINT.exists():
        raise SystemExit(f"❌ checkpoint not found: {CHECKPOINT}")
    for line in CHECKPOINT.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        ct = (rec.get("content_type") or "").strip()
        if ct and ct != "principle" and ct in NON_PRINCIPLE_TYPES and rec.get("content_type_agreed"):
            targets.append({"fb_id": rec["fb_id"], "content_type": ct})
    return targets


def _plan(targets: list[dict]) -> list[dict]:
    """Join targets to the DB and produce the exact change set (idempotent)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT fb_id, content_type, depth, status FROM fbs"
    ).fetchall()
    db = {r["fb_id"]: dict(r) for r in rows}
    conn.close()

    changes: list[dict] = []
    skipped_missing = 0
    skipped_already = 0
    for t in targets:
        cur = db.get(t["fb_id"])
        if cur is None:
            skipped_missing += 1
            continue
        if cur["content_type"] == t["content_type"] and cur["depth"] == "" and cur["status"] == "QUARANTINE":
            skipped_already += 1
            continue
        changes.append({
            "fb_id": t["fb_id"],
            "old_content_type": cur["content_type"],
            "new_content_type": t["content_type"],
            "old_depth": cur["depth"],
            "new_depth": "",
            "old_status": cur["status"],
            "new_status": "QUARANTINE",
        })
    return changes, skipped_missing, skipped_already


def _backup() -> Path:
    """C13: timestamped copy of the DB before any write."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB_PATH.with_name(f"maxwell.db.bak_{ts}_pre_phase0_relabel")
    shutil.copy2(DB_PATH, bak)
    return bak


def _apply(changes: list[dict]) -> None:
    """C6: single transaction + R14 manifest. Rolls back on any failure."""
    bak = _backup()
    print(f"  🔒 C13 backup: {bak}")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("BEGIN IMMEDIATE")
        for c in changes:
            conn.execute(
                "UPDATE fbs SET content_type=?, depth=?, status=? WHERE fb_id=?",
                (c["new_content_type"], "", "QUARANTINE", c["fb_id"]),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"❌ apply failed, rolled back (DB intact): {e}", file=sys.stderr)
        raise
    conn.close()

    # R14-stamped manifest (atomic, C6).
    now = datetime.now(timezone.utc).isoformat()
    manifest_lines = []
    for c in changes:
        rec = dict(c)
        rec.update({
            "schema_version": SCHEMA_VERSION,
            "gen_model": GEN_MODEL,
            "pipeline_commit": PIPELINE_COMMIT,
            "created_at": now,
            "source": "governance/joint_vote_production_checkpoint.jsonl",
        })
        manifest_lines.append(json.dumps(rec, ensure_ascii=False))
    safe_write(MANIFEST, "\n".join(manifest_lines) + "\n")

    # Integrity check (C6: verify the write is consistent).
    conn = sqlite3.connect(DB_PATH)
    ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    print(f"  ✅ integrity_check: {ok}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Phase 0 relabel (D2616)")
    parser.add_argument("--apply", action="store_true", help="back up + apply (default: dry-run)")
    args = parser.parse_args(argv)

    targets = _load_targets()
    changes, skipped_missing, skipped_already = _plan(targets)

    print(f"🧭 Phase 0 relabel (D2616) — vote-confirmed non-principle demotion")
    print(f"   checkpoint targets (non-principle, unanimous): {len(targets)}")
    print(f"   → to apply (content_type/depth/status change):   {len(changes)}")
    print(f"   → skipped (missing from DB):                     {skipped_missing}")
    print(f"   → skipped (already demoted, idempotent):         {skipped_already}")

    if not changes:
        print("   ✅ nothing to do.")
        return 0

    from collections import Counter
    ct = Counter(c["new_content_type"] for c in changes)
    st = Counter(c["old_status"] for c in changes)
    print(f"   new content_type distribution: {dict(ct)}")
    print(f"   old status distribution:       {dict(st)}")

    if not args.apply:
        print("\n   (dry-run) pass --apply to back up + write.")
        return 0

    _apply(changes)
    print(f"   ✅ applied {len(changes)} relabels. Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
