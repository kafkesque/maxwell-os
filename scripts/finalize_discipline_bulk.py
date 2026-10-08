#!/usr/bin/env python3
"""Finalize the ANCHOR-208 DISCIPLINE axis with the owner's bulk adjudication (D-2766).

The owner ruled (2026-10-02): "all discipline are human approved" — i.e. every one of the
199 unreviewed discipline rows (197 anchor_adjudication silver + 2 whitespace_fixed) is ratified
as-is.  This converts the discipline axis to 208/208 human-provenanced labels and closes BUG-620.

Deterministic + fail-closed (C12d: no silent remap).  Emits three provenance-stamped artifacts:
  1. [RETIRED, D-2868] governance/discipline_anchor_conformance_20261002.json (204 gold rows) —
     superseded by governance/discipline_anchor_rederived_v8_20261007.json; this one-shot is COMPLETE.
  2. governance/discipline_finalization_owner_bulk_20261002.json (the ruling record)
  3. an UPDATED governance/ANCHOR_208_CONSOLIDATED_20261002.json (discipline_source -> owner_finalized)

Crash-safe (tempfile -> fsync -> os.replace) and backed up (C13) before the in-place rewrite.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONSOLIDATED = REPO / "governance" / "ANCHOR_208_CONSOLIDATED_20261002.json"
OUT_CONFORMANCE = REPO / "governance" / "discipline_anchor_conformance_20261002.json"  # RETIRED (D-2868): superseded by rederived_v8; one-shot COMPLETE, self-guarded vs re-run
OUT_BULK = REPO / "governance" / "discipline_finalization_owner_bulk_20261002.json"
BACKUP = REPO / "governance" / "ANCHOR_208_CONSOLIDATED_20261002.json.bak_20261002_discipline"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:  # noqa: BLE001 - fall back to 'unknown' rather than crash the write
        return "unknown"


def _atomic_write(path: Path, payload: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main() -> int:
    src = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
    rows = src["rows"]
    if len(rows) != 208:
        raise SystemExit(f"FAIL: expected 208 rows, got {len(rows)}")

    # Invariant check: 9 owner_finalized + 197 anchor_adjudication + 2 whitespace_fixed == 208
    from collections import Counter

    dist = Counter(r.get("discipline_source") for r in rows)
    if dist.get("owner_finalized", 0) != 9 or dist.get("anchor_adjudication", 0) != 197 or dist.get("whitespace_fixed", 0) != 2:
        raise SystemExit(f"FAIL: unexpected discipline_source distribution {dict(dist)}")

    # Bulk-ratify every non-owner row.
    ratified = 0
    for r in rows:
        if r.get("discipline_source") in ("anchor_adjudication", "whitespace_fixed"):
            r["discipline_source"] = "owner_finalized"
            ratified += 1
    if ratified != 199:
        raise SystemExit(f"FAIL: expected 199 to ratify, got {ratified}")

    stamp = {
        "schema_version": "1.0",
        "generated_by": "scripts/finalize_discipline_bulk.py",
        "gen_model": "human_owner (bulk adjudication 2026-10-02)",
        "pipeline_commit": _git_commit(),
        "source_sha256": _sha256(CONSOLIDATED),
        "decision": "D-2766",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 1. Conformance gold set: golden-eligible rows only (excludes 3 emerging + 1 noise_drop).
    gold = [r for r in rows if r.get("discipline_golden_eligible")]
    if len(gold) != 204:
        raise SystemExit(f"FAIL: expected 204 golden-eligible, got {len(gold)}")
    conformance = {
        "artifact_id": "discipline_anchor_conformance_20261002",
        "total": len(gold),
        "by_discipline_source": dict(Counter(r["discipline_source"] for r in gold)),
        "rows": [
            {
                "item_id": r["item_id"],
                "name": r["name"],
                "discipline": r["discipline"],
                "discipline_source": r["discipline_source"],
                "domain": r.get("domain"),
                "primary_domain": r.get("primary_domain"),
            }
            for r in gold
        ],
        "_provenance": stamp,
    }

    # 2. Bulk ruling record.
    bulk = {
        "artifact_id": "discipline_finalization_owner_bulk_20261002",
        "ruling": "all discipline are human approved (owner, 2026-10-02)",
        "ratified_rows": ratified,
        "final_distribution": dict(Counter(r["discipline_source"] for r in rows)),
        "_provenance": stamp,
    }

    # 3. Updated consolidated anchor (crash-safe + backup first).
    if not BACKUP.exists():
        BACKUP.write_bytes(CONSOLIDATED.read_bytes())
    src["_provenance"] = {**src.get("_provenance", {}), "discipline_finalized": stamp}
    _atomic_write(CONSOLIDATED, src)

    _atomic_write(OUT_CONFORMANCE, conformance)
    _atomic_write(OUT_BULK, bulk)

    print(f"ratified {ratified} discipline rows -> owner_finalized (208/208 human-provenanced)")
    print(f"wrote {OUT_CONFORMANCE.name} ({len(gold)} gold rows)")
    print(f"wrote {OUT_BULK.name}")
    print(f"updated {CONSOLIDATED.name} (backup: {BACKUP.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
