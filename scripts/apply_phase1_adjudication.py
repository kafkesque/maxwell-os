#!/usr/bin/env python3
"""Apply the D2615 human adjudication (298 rows) to maxwell.db (Phase 1, D2616).

Deterministic, LLM-free. Reads governance/d2615_human_adjudication.jsonl
(295 human + 3 agent-rubric rows, R14-stamped) and materialises the human's
two-axis (content_type + depth) verdicts into `knowledge pipeline/maxwell.db`:

    content_type axis:
        principle            -> keep principle, un-quarantine (status=PASS)
        non-principle label  -> demote out of principle index:
                                content_type=label, depth='', status=QUARANTINE
    depth axis:
        <label>              -> set depth=<label>, un-quarantine (status=PASS)
    bonus_depth (human volunteered a depth on a content_type row):
        -> also set depth=<bonus_depth>

Provenance:
  - source == 'human'        -> needs_human_review=0 (authoritative, freeze)
  - source == 'agent-rubric' -> needs_human_review=1 (rubric-applied, human
                                confirm still pending; not silently merged)

Safety (mirrors apply_phase0_relabels.py):
  - C13: timestamped DB backup BEFORE any write.
  - C6:  single SQLite transaction; rolls back on any failure.
  - Idempotent: skips rows already at the target state.
  - --check (default): dry-run, reports the exact change set, writes nothing.
  - --apply: back up + apply + R14 manifest + integrity_check.

Manifest: governance/phase1_relabel_manifest.jsonl (one row per FB, R14-stamped).
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
ADJ = ROOT / "governance" / "d2615_human_adjudication.jsonl"
MANIFEST = ROOT / "governance" / "phase1_relabel_manifest.jsonl"

SCHEMA_VERSION = "3.0"
GEN_MODEL = "human+agent-rubric"  # deterministic application of human ground truth
PIPELINE_COMMIT = "v3.0-D2616-phase1"


def _load_adjudications() -> list[dict]:
    recs: list[dict] = []
    for line in ADJ.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        recs.append(json.loads(line))
    return recs


def _plan(adjs: list[dict]) -> tuple[list[dict], int, int]:
    """Join adjudications to DB and produce the exact change set (idempotent)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT fb_id, content_type, depth, status, needs_human_review FROM fbs"
    ).fetchall()
    db = {r["fb_id"]: dict(r) for r in rows}
    conn.close()

    changes: list[dict] = []
    skipped_missing = 0
    skipped_already = 0

    for a in adjs:
        fb = a["fb_id"]
        axis = a["axis"]
        label = a["label"]
        src = a.get("source", "human")
        bonus = a.get("bonus_depth")
        cur = db.get(fb)
        if cur is None:
            skipped_missing += 1
            continue

        if axis == "content_type":
            if label == "principle":
                new_ct = "principle"
                new_depth = bonus if bonus else cur["depth"]
                new_status = "PASS"
            else:
                new_ct = label
                new_depth = ""
                new_status = "QUARANTINE"
        else:  # depth axis
            new_ct = cur["content_type"]  # principle (unchanged)
            new_depth = label
            new_status = "PASS"

        new_nhr = 1 if src == "agent-rubric" else 0

        if (
            cur["content_type"] == new_ct
            and cur["depth"] == new_depth
            and cur["status"] == new_status
            and (cur["needs_human_review"] or 0) == new_nhr
        ):
            skipped_already += 1
            continue

        changes.append({
            "fb_id": fb,
            "axis": axis,
            "label": label,
            "source": src,
            "old_content_type": cur["content_type"],
            "new_content_type": new_ct,
            "old_depth": cur["depth"],
            "new_depth": new_depth,
            "old_status": cur["status"],
            "new_status": new_status,
            "old_needs_human_review": cur["needs_human_review"],
            "new_needs_human_review": new_nhr,
        })

    return changes, skipped_missing, skipped_already


def _backup() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB_PATH.with_name(f"maxwell.db.bak_{ts}_pre_phase1_adjudication")
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
                "UPDATE fbs SET content_type=?, depth=?, status=?, needs_human_review=? WHERE fb_id=?",
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
            "source": f"governance/d2615_human_adjudication.jsonl ({c['source']})",
        })
        lines.append(json.dumps(rec, ensure_ascii=False))
    safe_write(MANIFEST, "\n".join(lines) + "\n")

    conn = sqlite3.connect(DB_PATH)
    ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    print(f"  ✅ integrity_check: {ok}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Phase 1 human adjudication apply (D2616)")
    parser.add_argument("--apply", action="store_true", help="back up + apply (default: dry-run)")
    args = parser.parse_args(argv)

    adjs = _load_adjudications()
    changes, skipped_missing, skipped_already = _plan(adjs)

    print("🧭 Phase 1 adjudication apply (D2616) — D2615 298-row human review")
    print(f"   adjudications loaded:    {len(adjs)}")
    print(f"   → to apply (state change): {len(changes)}")
    print(f"   → skipped missing from DB: {skipped_missing}")
    print(f"   → skipped already applied: {skipped_already}")

    if not changes:
        print("   ✅ nothing to do.")
        return 0

    kind = Counter(c["new_status"] for c in changes)
    demote = [c for c in changes if c["new_status"] == "QUARANTINE"]
    unquar = [c for c in changes if c["new_status"] == "PASS" and c["old_status"] == "QUARANTINE"]
    src = Counter(c["source"] for c in changes)
    ct = Counter(c["new_content_type"] for c in changes if c["new_content_type"] != "principle")
    print(f"   new_status dist:        {dict(kind)}  (demotions={len(demote)}, un-quarantine={len(unquar)})")
    print(f"   non-principle demote:   {dict(ct)}")
    print(f"   source dist:            {dict(src)}")

    if not args.apply:
        print("\n   (dry-run) pass --apply to back up + write.")
        return 0

    _apply(changes)
    print(f"   ✅ applied {len(changes)} changes. Manifest: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
