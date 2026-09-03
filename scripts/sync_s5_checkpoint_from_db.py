#!/usr/bin/env python3
"""scripts/sync_s5_checkpoint_from_db.py — re-sync the S5 checkpoint to the DB.

D2521 follow-up: the user correctly observed that the S5 checkpoint
(`stage5_verify/t11/checkpoint.jsonl`) was STALE after BUG-197 (deterministic
kind-swap) + BUG-198 (singleton re-inject) mutated the SQLite DB DIRECTLY.

The S5 checkpoint was renamed `.stale_*` (D2507b hard-discard pattern) and no
current `checkpoint.jsonl` exists — but `stage6_commit.load_stage5_fbs()` reads
it, so a future S6 commit would fail. This script rebuilds it from the DB
(authoritative post-commit truth):

  * Base = the newest stale checkpoint (7,867 verified FBs, correct NLI results).
  * Overwrite ONLY the 4 taxonomy fields (domains/domains_raw/discipline/
    discipline_raw) from the DB — mirrors BUG-197's field-scoped swap.
  * Append the 6 BUG-198 re-injected FBs missing from the checkpoint,
    reconstructing S5-format from the DB row + re-deriving the S5-only fields
    (classify_model/is_specialized/manifest_hash/isor/epistemic_status/
    verification_method) DETERMINISTICALLY (no NLI re-run — verification_results
    is already in the DB).

No NLI re-verification is performed: BUG-197 swapped only taxonomy labels (NLI
verifies classification CONTENT, not taxonomy), and the 6 BUG-198 FBs already
carry their DeBERTa verdicts in the DB (verifier_model=DeBERTa,
pipeline_run_id=bug198_reinject).

Crash-safe (C6): backups the checkpoint, writes tempfile → fsync → os.replace.
Idempotent: re-running produces the same output.

Run: /usr/local/bin/python3 scripts/sync_s5_checkpoint_from_db.py
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
from pipeline.schema_accessor import isor_score  # noqa: E402

S5_DIR = Path("knowledge pipeline/stage5_verify/t11")
CHECKPOINT = S5_DIR / "checkpoint.jsonl"
STALE_BASE = S5_DIR / "checkpoint.jsonl.stale_20260902_154337"
EXPECTED = S5_DIR / "checkpoint.jsonl.expected_count.json"

# DB-only columns (written at S6, absent from the S5 checkpoint).
_DB_ONLY_FIELDS = {"borp_score", "committed_at", "contradicts_fbs", "last_retrieved_at"}

# JSON-encoded DB text columns → parsed back to list/dict for the S5 checkpoint.
_JSON_LIST_FIELDS = {
    "domains", "domains_raw", "source_clusters", "source_books", "source_ids",
    "source_authors", "source_principle_ids", "source_segments",
    "evidence_passages", "evidence_passages_shown", "classification_errors",
    "prerequisite_fbs", "related_fbs", "verification_results",
}
_JSON_DICT_FIELDS = {"primary_source"}


def _parse(val):
    if val is None:
        return None
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def _fact_passed(verification_results) -> bool:
    """Extract the DeBERTa factual verdict from the DB's verification_results."""
    results = _parse(verification_results)
    if not isinstance(results, list):
        return False
    for r in results:
        if isinstance(r, dict) and r.get("check_name") == "factual":
            return bool(r.get("passed", False))
    return False


def _s5_record_from_db(row: sqlite3.Row, manifest_hash: str) -> dict:
    """Reconstruct an S5-format checkpoint record from a DB row (deterministic)."""
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

    # S4-only fields (computed at S4, not persisted in the DB).
    rec["classify_model"] = VERIFY_MODEL
    rec["is_specialized"] = (rec.get("depth") == "specialized")
    rec["manifest_hash"] = manifest_hash

    # S5-only fields — re-derived deterministically (NO NLI re-run).
    fact_passed = _fact_passed(row["verification_results"])
    isor = isor_score(rec)
    if isor.get("rating") == "strong" and fact_passed:
        epistemic_status = "corroborated"
    elif isor.get("rating") in ("strong", "medium") and not fact_passed:
        epistemic_status = "cross-source-unverified"
    elif fact_passed:
        epistemic_status = "source-supported"
    else:
        epistemic_status = "speculative"
    rec["epistemic_status"] = epistemic_status
    rec["isor"] = isor
    rec["verification_method"] = "deberta-nli"
    return rec


def main() -> int:
    if not STALE_BASE.exists():
        print(f"❌ stale S5 checkpoint not found: {STALE_BASE}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    db_rows = {r["fb_id"]: r for r in conn.execute("SELECT * FROM fbs").fetchall()}
    conn.close()
    print(f"📊 DB has {len(db_rows)} FBs")

    # Load the stale S5 checkpoint as the base (preserving verified fields).
    checkpoint_recs: list[dict] = []
    checkpoint_ids: set[str] = set()
    with open(STALE_BASE, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            rec = json.loads(line)
            checkpoint_recs.append(rec)
            checkpoint_ids.add(rec.get("fb_id", ""))
    print(f"📦 stale S5 checkpoint has {len(checkpoint_recs)} records")

    manifest_hash = checkpoint_recs[0].get("manifest_hash") if checkpoint_recs else get_manifest_hash()

    # 1. In-place: overwrite ONLY the 4 taxonomy fields from the DB.
    updated = 0
    for rec in checkpoint_recs:
        row = db_rows.get(rec.get("fb_id"))
        if row is None:
            continue
        nd, ndr = _parse(row["domains"]), _parse(row["domains_raw"])
        ndisc, ndraw = row["discipline"], row["discipline_raw"]
        changed = (
            json.dumps(nd, sort_keys=True) != json.dumps(rec.get("domains"), sort_keys=True)
            or json.dumps(ndr, sort_keys=True) != json.dumps(rec.get("domains_raw"), sort_keys=True)
            or ndisc != rec.get("discipline")
            or ndraw != rec.get("discipline_raw")
        )
        if changed:
            rec["domains"], rec["domains_raw"] = nd, ndr
            rec["discipline"], rec["discipline_raw"] = ndisc, ndraw
            updated += 1

    # 2. Append the 6 BUG-198 re-injected FBs (in DB but missing from checkpoint).
    appended = 0
    for fid, row in db_rows.items():
        if fid in checkpoint_ids:
            continue
        checkpoint_recs.append(_s5_record_from_db(row, manifest_hash))
        appended += 1

    print(f"   taxonomy fields re-synced: {updated}")
    print(f"   DB-only FBs appended:      {appended}")

    # 3. Backup existing (if any) + crash-safe write.
    if CHECKPOINT.exists():
        backup = CHECKPOINT.with_name(CHECKPOINT.name + f".bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(CHECKPOINT, backup)
        print(f"   backed up existing → {backup.name}")
    fd, tmp = tempfile.mkstemp(dir=S5_DIR, suffix=".tmp")
    with open(fd, "w", encoding="utf-8") as out:
        for rec in checkpoint_recs:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, CHECKPOINT)
    print(f"✅ wrote {len(checkpoint_recs)} records → {CHECKPOINT}")

    # 4. Write expected count sidecar.
    ec = {
        "expected_fb_count": len(checkpoint_recs),
        "written_at": datetime.now(timezone.utc).timestamp(),
        "pipeline_run_id": "t11",
    }
    with open(EXPECTED, "w", encoding="utf-8") as f:
        json.dump(ec, f, indent=2)
    print(f"✅ expected_count → {len(checkpoint_recs)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
