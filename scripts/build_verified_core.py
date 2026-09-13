#!/usr/bin/env python3
"""Freeze the human+joint-vote verified core into governance/verified_core.jsonl.

Deterministic, LLM-free (C12 / $0 marginal cost). Merges the two Phase-1
verified sources by fb_id (DB primary key), R14-stamps every row, and emits the
sole eval target that retires BUG-241's "93.3% unverified silver" at the data
level (D2613 / D2616 Phase 1).

Sources (all read-only, never mutated):
  - governance/phase0_adjudication_ledger.jsonl  (149-core, example_id keyed)
  - governance/golden_synced_4axis.jsonl         (merged 4-axis labels)
  - governance/flagged_core_human_verdicts.jsonl (28 human verdicts)
  - governance/s4_active_learning_sample.jsonl   (298-sample, fb_id keyed)

Output (C6 atomic write):
  - governance/verified_core.jsonl   (R14-stamped rows)
  - governance/verified_core_manifest.json (summary + per-status counts)

verification_status semantics (honest provenance):
  - human-verified       -> a human verdict exists (flagged_core_human_verdicts.jsonl)
  - joint-vote-verified  -> reliable pair unanimous, materialized into golden_synced
  - pending-human        -> active-learning boundary sample (D2615), NOT yet adjudicated
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# Config (C12: no magic values inline; every path/threshold here is a named   #
# constant so a future config extraction is a pure move, not a rewrite).      #
# --------------------------------------------------------------------------- #
GOV_DIR = "governance"
CORE_LEDGER = os.path.join(GOV_DIR, "phase0_adjudication_ledger.jsonl")
GOLDEN_SYNCED = os.path.join(GOV_DIR, "golden_synced_4axis.jsonl")
HUMAN_VERDICTS = os.path.join(GOV_DIR, "flagged_core_human_verdicts.jsonl")
ACTIVE_SAMPLE = os.path.join(GOV_DIR, "s4_active_learning_sample.jsonl")

OUT_CORE = os.path.join(GOV_DIR, "verified_core.jsonl")
OUT_MANIFEST = os.path.join(GOV_DIR, "verified_core_manifest.json")

SCHEMA_VERSION = "3.0"
GEN_MODEL = "verified-core-freezer (deterministic; no generation)"
PIPELINE_COMMIT = "v3.0-D2617-phase1"

STATUS_HUMAN = "human-verified"
STATUS_JOINT = "joint-vote-verified"
STATUS_PENDING = "pending-human"


def _load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load a JSONL file into a list of dicts (fail-loud, C16)."""
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _now_iso() -> str:
    """UTC ISO-8601 timestamp for R14 created_at stamps."""
    return datetime.now(timezone.utc).isoformat()


def _stamp(row: Dict[str, Any]) -> Dict[str, Any]:
    """Attach the R14 provenance stamp to a verified-core row."""
    row["schema_version"] = SCHEMA_VERSION
    row["gen_model"] = GEN_MODEL
    row["pipeline_commit"] = PIPELINE_COMMIT
    row["created_at"] = _now_iso()
    return row


def _core_row(
    golden: Dict[str, Any],
    status: str,
    core_source: str,
    review_axis: Optional[str] = None,
    disagreement_pair: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a verified-core row from a golden_synced record + provenance."""
    row: Dict[str, Any] = {
        "fb_id": golden["fb_id"],
        "example_id": golden.get("id"),
        "name": golden.get("name"),
        "content_type": golden.get("content_type"),
        "content_type_source": golden.get("content_type_source"),
        "depth": golden.get("depth"),
        "depth_source": golden.get("depth_source"),
        "discipline": golden.get("discipline"),
        "discipline_source": golden.get("discipline_source"),
        "domains": golden.get("domains"),
        "domains_source": golden.get("domains_source"),
        "verification_status": status,
        "review_axis": review_axis,
        "disagreement_pair": disagreement_pair,
        "core_source": core_source,
    }
    return _stamp(row)


def _sample_row(sample: Dict[str, Any], golden: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a verified-core row from an active-learning sample record.

    The 298-sample is the D2615 boundary batch awaiting human adjudication:
    content_type/depth are still pending (the pair disagreed), so they carry
    ``verification_status = pending-human`` and the disagreement pair is
    preserved. Any discipline/domains present in golden_synced are carried
    through with their honest (silver) source, never re-branded as verified.
    """
    confirmed_ct = sample.get("confirmed_content_type")
    row: Dict[str, Any] = {
        "fb_id": sample["fb_id"],
        "example_id": golden.get("id") if golden else None,
        "name": sample.get("name"),
        "content_type": confirmed_ct,
        "content_type_source": "joint-vote" if confirmed_ct == "principle" else None,
        "depth": None,
        "depth_source": None,
        "discipline": golden.get("discipline") if golden else None,
        "discipline_source": golden.get("discipline_source") if golden else None,
        "domains": golden.get("domains") if golden else None,
        "domains_source": golden.get("domains_source") if golden else None,
        "verification_status": STATUS_PENDING,
        "review_axis": sample.get("review_axis"),
        "disagreement_pair": sample.get("disagreement_pair"),
        "core_source": "298-sample",
    }
    return _stamp(row)


def build() -> None:
    """Merge 149-core + 298-sample into the R14-stamped verified core."""
    core = _load_jsonl(CORE_LEDGER)
    golden = _load_jsonl(GOLDEN_SYNCED)
    verdicts = _load_jsonl(HUMAN_VERDICTS)
    sample = _load_jsonl(ACTIVE_SAMPLE)

    golden_by_id: Dict[str, Dict[str, Any]] = {r["id"]: r for r in golden}
    golden_by_fb: Dict[str, Dict[str, Any]] = {r["fb_id"]: r for r in golden}

    # Human-verified golden ids (flagged_core_human_verdicts.jsonl).
    human_ids = {v.get("golden_id") for v in verdicts}

    # ---- 149-core -------------------------------------------------------- #
    rows: Dict[str, Dict[str, Any]] = {}
    missing_golden: List[str] = []
    for ledger_row in core:
        eid = ledger_row["example_id"]
        g = golden_by_id.get(eid)
        if g is None:
            missing_golden.append(eid)
            continue
        status = STATUS_HUMAN if eid in human_ids else STATUS_JOINT
        rows[g["fb_id"]] = _core_row(g, status, core_source="149-core")

    # ---- 298-sample ------------------------------------------------------ #
    sample_fbids = [r["fb_id"] for r in sample]
    overlap_fbids = [fb for fb in sample_fbids if fb in rows]
    for srow in sample:
        fb = srow["fb_id"]
        g = golden_by_fb.get(fb)
        if fb in rows:
            # Present in both: 149-core verification is authoritative; record
            # the sample's pending axis as supplementary provenance.
            rows[fb]["core_source"] = "149-core+298-sample"
            rows[fb]["review_axis"] = srow.get("review_axis")
            rows[fb]["disagreement_pair"] = srow.get("disagreement_pair")
            continue
        rows[fb] = _sample_row(srow, g)

    # ---- Emit (C6 atomic) ------------------------------------------------ #
    ordered = sorted(rows.values(), key=lambda r: r["fb_id"])
    out_rows = [json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in ordered]
    _atomic_write(OUT_CORE, "".join(out_rows))

    # ---- Manifest -------------------------------------------------------- #
    status_counts = Counter(r["verification_status"] for r in ordered)
    core_source_counts = Counter(r["core_source"] for r in ordered)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": GEN_MODEL,
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": _now_iso(),
        "input_ledger_rows": len(core),
        "input_sample_rows": len(sample),
        "input_human_verdicts": len(verdicts),
        "golden_synced_rows": len(golden),
        "missing_golden_for_core": missing_golden,
        "overlap_fbids_between_core_and_sample": overlap_fbids,
        "total_unique_rows": len(ordered),
        "verification_status_counts": dict(status_counts),
        "core_source_counts": dict(core_source_counts),
    }
    _atomic_write(OUT_MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    # ---- Console summary ------------------------------------------------- #
    print(f"verified_core.jsonl written: {len(ordered)} unique rows")
    print(f"  verification_status: {dict(status_counts)}")
    print(f"  core_source:         {dict(core_source_counts)}")
    print(f"  overlap fb_ids (149-core AND 298-sample): {len(overlap_fbids)}")
    print(f"  core example_ids missing from golden_synced: {len(missing_golden)}")


def _atomic_write(path: str, content: str) -> None:
    """C6 crash-safe write: tempfile -> fsync -> os.replace."""
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


if __name__ == "__main__":
    build()
