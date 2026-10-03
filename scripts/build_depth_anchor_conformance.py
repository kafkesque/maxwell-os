#!/usr/bin/env python3
"""build_depth_anchor_conformance.py — build the human-provenanced depth anchor.

WHAT THIS PRODUCES
------------------
`governance/depth_anchor_conformance_<date>.json` — the first DURABLE, HUMAN-OWNER
depth ground truth (fixes the BUG-617 gap: "depth axis lacks human-provenanced
ground truth"). It is a CONFORMANCE set (D-274f), NOT a training set and NOT a
few-shot injection: "the first thing NOT to do with the anchor is fine-tune on it."

JOIN (deterministic, no LLM)
----------------------------
Three inputs, joined by item_id under the declared `collapse_whitespace`
normalization (D-2658 — join is by content, never by position):
  1. governance/ANCHOR_208_DEPTH_CORRECTED_20261002.json  (owner-finalized depth, D-2760)
  2. governance/ANCHOR_STORE_BRIDGE_20260926.json          (item_id -> fb_id, 150/150 joined)
  3. knowledge pipeline/maxwell.db  table fbs              (full FB text by fb_id)

Only the 207 golden-eligible rows are emitted. Excluded: R021 (owner noise_drop).
The 58 formerly-mapped extras are now owner-adjudicated and folded (D-2785) and ARE emitted.

Every output row is provenance-stamped (schema_version, gen_model, source sha256)
per R14.

Usage:
    python3 scripts/build_depth_anchor_conformance.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

DEPTH_MAP = REPO / "governance" / "ANCHOR_208_DEPTH_CORRECTED_20261002.json"
STORE_BRIDGE = REPO / "governance" / "ANCHOR_STORE_BRIDGE_20260926.json"
STORE = REPO / "knowledge pipeline" / "maxwell.db"

DEPTH_LABELS = ("universal", "cross-domain", "domain", "specialized")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _collapse(s: str) -> str:
    """collapse_whitespace per the declared store-bridge normalization (D-2658)."""
    return " ".join((s or "").split())


def build(out: Path) -> dict:
    depth_map = json.loads(DEPTH_MAP.read_text(encoding="utf-8"))
    bridge = json.loads(STORE_BRIDGE.read_text(encoding="utf-8"))
    by_id = {r["item_id"]: r for r in depth_map}

    db = sqlite3.connect(str(STORE))
    cur = db.cursor()

    examples: list[dict] = []
    excluded: list[dict] = []
    name_normalized: list[str] = []  # (item_id, why) — whitespace-only diffs are expected

    for fb_id, entry in bridge["entries"].items():
        item_id = entry["item_id"]
        rec = by_id.get(item_id)
        if rec is None:
            raise SystemExit(f"FAIL: bridge item_id {item_id} missing from depth map")
        label = rec.get("depth_label")
        if label == "noise_drop":
            excluded.append({"item_id": item_id, "reason": "owner noise_drop (R021)"})
            continue
        cur.execute(
            "SELECT name, definition, mechanism, boundary, extraction_type FROM fbs WHERE fb_id=?",
            (fb_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise SystemExit(f"FAIL: fb_id {fb_id} (item {item_id}) not in store")
        name, definition, mechanism, boundary, extraction_type = row
        if _collapse(name) != _collapse(rec.get("name", "")):
            name_normalized.append(item_id)
        examples.append(
            {
                "item_id": item_id,
                "name": name,
                "definition": definition or "",
                "mechanism": mechanism or "",
                "boundary": boundary or "",
                "extraction_type": extraction_type or "",
                "depth": rec.get("depth"),
                "depth_label": label,
                "depth_source": rec.get("depth_source"),
                "fb_id": fb_id,
            }
        )

    db.close()

    # integrity: exactly the golden-eligible count (all non-noise_drop rows), all depth labels on-menu
    expected = sum(1 for r in depth_map if r.get("depth_label") != "noise_drop")
    if len(examples) != expected:
        raise SystemExit(f"FAIL: expected {expected} golden rows, got {len(examples)}")
    off = [e["item_id"] for e in examples if e["depth_label"] not in DEPTH_LABELS]
    if off:
        raise SystemExit(f"FAIL: off-menu depth labels: {off}")

    by_label: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for e in examples:
        by_label[e["depth_label"]] = by_label.get(e["depth_label"], 0) + 1
        by_source[e["depth_source"]] = by_source.get(e["depth_source"], 0) + 1

    # pipeline stamp (R14) — read live, never hardcode
    try:
        from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: F401
        commit = PIPELINE_COMMIT
        schema_version = SCHEMA_VERSION
    except Exception:
        commit = "unknown"
        schema_version = "unknown"

    doc = {
        "schema_version": "1.0",
        "artifact_id": "DEPTH_ANCHOR_CONFORMANCE",
        "generated_by": "scripts/build_depth_anchor_conformance.py",
        "gen_model": "none (deterministic join; no LLM)",
        "pipeline_commit": commit,
        "maxwell_schema_version": schema_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authority": [
            "D-2760 (owner finalized 42 depth mismatches; corrected depth map)",
            "D-274f (anchor is a conformance set, NOT a training set)",
            "D-2611 (report chance-corrected kappa, never bare accuracy)",
            "config/agreement_floor.yaml (operative floor 0.800)",
        ],
        "inputs": {
            "depth_map": {"path": str(DEPTH_MAP), "sha256": _sha256(DEPTH_MAP)},
            "store_bridge": {"path": str(STORE_BRIDGE), "sha256": _sha256(STORE_BRIDGE)},
            "store": {"path": str(STORE), "table": "fbs"},
        },
        "join": {"key": "item_id", "normalization": "collapse_whitespace"},
        "counts": {
            "total": len(examples),
            "by_depth_label": by_label,
            "by_depth_source": by_source,
            "name_normalized": name_normalized,
        },
        "depth_labels": list(DEPTH_LABELS),
        "excluded": excluded,
        "examples": examples,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        default=str(REPO / "governance" / "depth_anchor_conformance_20261002.json"),
    )
    args = ap.parse_args()
    doc = build(Path(args.out))
    print(f"wrote {args.out}")
    print(f"  total owner rows: {doc['counts']['total']}")
    print(f"  by_depth_label: {doc['counts']['by_depth_label']}")
    print(f"  name_normalized (whitespace-only): {doc['counts']['name_normalized']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
