#!/usr/bin/env python3
"""scripts/sync_checkpoint_from_db.py — re-sync S4 checkpoint to the corrected DB.

D2519 follow-up: the BUG-197 deterministic kind-swap and BUG-198 singleton re-inject
mutated the SQLite DB DIRECTLY (they are post-commit data fixes), so the S4
checkpoint (`stage4_merge/t11/checkpoint_enriched.jsonl`) is now STALE in two ways:
  1. 3,694 FBs still carry the PRE-swap (axis-leaked) domains/domains_raw/
     discipline/discipline_raw values.
  2. The 6 BUG-198 re-injected FBs are missing (checkpoint 7,867 vs DB 7,873).

This script re-syncs the checkpoint to the DB (the authoritative post-commit truth):
  * For every FB present in BOTH: overwrite ONLY the 4 taxonomy fields from the DB.
    Every other field (classification, provenance, stamps) is preserved byte-identical.
  * For the 6 DB-only FBs: reconstruct an S4-format record from the DB row
    (S5 verification fields stripped; S4-only `classify_model`/`is_specialized`/
    `manifest_hash`/`classification_errors` re-derived).
  * Update `checkpoint_enriched.jsonl.expected_count.json` → 7,873.

Crash-safe (C6): backs up the checkpoint, writes tempfile → fsync → os.replace.
Idempotent: re-running produces the same output.

Run: /usr/local/bin/python3 scripts/sync_checkpoint_from_db.py
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH, VERIFY_MODEL  # noqa: E402
from pipeline.stamp import get_manifest_hash  # noqa: E402

CHECKPOINT = Path("knowledge pipeline/stage4_merge/t11/checkpoint_enriched.jsonl")
EXPECTED = Path("knowledge pipeline/stage4_merge/t11/checkpoint_enriched.jsonl.expected_count.json")

# JSON-encoded columns in the fbs table (stored as text, must be parsed back to
# list/dict for the checkpoint's in-memory object form).
_JSON_FIELDS = {
    "domains", "domains_raw", "keywords",  # keywords is CSV string, NOT JSON — handled below
    "source_clusters", "source_books", "source_ids", "source_authors",
    "primary_source", "source_principle_ids", "source_segments",
    "evidence_passages", "evidence_passages_shown", "classification_errors",
    "prerequisite_fbs", "contradicts_fbs", "related_fbs",
}
# Columns that are JSON arrays/objects (multi-value), excluding keywords/jargon.
_JSON_LIST_FIELDS = {
    "domains", "domains_raw", "source_clusters", "source_books", "source_ids",
    "source_authors", "source_principle_ids", "source_segments",
    "evidence_passages", "evidence_passages_shown", "classification_errors",
    "prerequisite_fbs", "contradicts_fbs", "related_fbs",
}
_JSON_DICT_FIELDS = {"primary_source"}

# S5 verification fields that must NOT leak into the S4 checkpoint record.
_DB_ONLY_FIELDS = {
    "contradicts_fbs", "last_retrieved_at", "confidence_score",
    "verification_results", "borp_score", "status", "needs_human_review",
    "verifier_model", "committed_at",
}


def _parse(val):
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def _s4_record_from_db(row: sqlite3.Row) -> dict:
    """Reconstruct an S4-format checkpoint record from a DB row (strip S5 fields)."""
    rec: dict = {}
    for key in row.keys():
        if key in _DB_ONLY_FIELDS:
            continue
        val = row[key]
        if key in _JSON_LIST_FIELDS:
            v = _parse(val)
            rec[key] = v if isinstance(v, list) else ([] if v is None else [v])
        elif key in _JSON_DICT_FIELDS:
            v = _parse(val)
            rec[key] = v if isinstance(v, dict) else None
        else:
            rec[key] = val
    # S4-only derived fields (computed at S4, not persisted in the DB)
    rec["classify_model"] = VERIFY_MODEL
    rec["is_specialized"] = (rec.get("depth") == "specialized")
    rec["classification_errors"] = None
    rec["manifest_hash"] = get_manifest_hash()
    return rec


def main() -> int:
    if not CHECKPOINT.exists():
        print(f"❌ checkpoint not found: {CHECKPOINT}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    db_rows = {r["fb_id"]: r for r in conn.execute("SELECT * FROM fbs").fetchall()}
    conn.close()
    print(f"📊 DB has {len(db_rows)} FBs")

    # Load checkpoint records, keyed by fb_id (preserving full objects)
    checkpoint_recs: list[dict] = []
    checkpoint_ids: set[str] = set()
    with open(CHECKPOINT, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            rec = json.loads(line)
            checkpoint_recs.append(rec)
            checkpoint_ids.add(rec.get("fb_id", ""))

    print(f"📦 checkpoint has {len(checkpoint_recs)} records")

    # 1. In-place: overwrite ONLY the 4 taxonomy fields from the DB.
    updated = 0
    for rec in checkpoint_recs:
        fid = rec.get("fb_id")
        row = db_rows.get(fid)
        if row is None:
            continue
        nd = _parse(row["domains"])
        ndr = _parse(row["domains_raw"])
        ndisc = row["discipline"]
        ndraw = row["discipline_raw"]
        changed = (
            json.dumps(nd, sort_keys=True) != json.dumps(rec.get("domains"), sort_keys=True)
            or json.dumps(ndr, sort_keys=True) != json.dumps(rec.get("domains_raw"), sort_keys=True)
            or ndisc != rec.get("discipline")
            or ndraw != rec.get("discipline_raw")
        )
        if changed:
            rec["domains"] = nd
            rec["domains_raw"] = ndr
            rec["discipline"] = ndisc
            rec["discipline_raw"] = ndraw
            updated += 1

    # 2. Append the DB-only FBs (BUG-198 re-injected) as S4-format records.
    appended = 0
    for fid, row in db_rows.items():
        if fid in checkpoint_ids:
            continue
        checkpoint_recs.append(_s4_record_from_db(row))
        appended += 1

    print(f"   taxonomy fields re-synced: {updated}")
    print(f"   DB-only FBs appended: {appended}")

    # 3. Backup + crash-safe write.
    backup = CHECKPOINT.with_name(CHECKPOINT.name + f".bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(CHECKPOINT, backup)
    fd, tmp = tempfile.mkstemp(dir=CHECKPOINT.parent, suffix=".tmp")
    with open(fd, "w", encoding="utf-8") as out:
        for rec in checkpoint_recs:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, CHECKPOINT)
    print(f"✅ wrote {len(checkpoint_recs)} records → {CHECKPOINT} (backup {backup.name})")

    # 4. Update expected count.
    if EXPECTED.exists():
        with open(EXPECTED) as f:
            ec = json.load(f)
        ec["expected_fb_count"] = len(checkpoint_recs)
        ec["s4_expected_fb_count"] = len(checkpoint_recs)
        ec["written_at"] = datetime.now(timezone.utc).timestamp()
        with open(EXPECTED, "w") as f:
            json.dump(ec, f, indent=2)
        print(f"✅ expected_count → {len(checkpoint_recs)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
