#!/usr/bin/env python3
"""bridge_s2_to_s4.py — Convert v3.0 Stage 2 FBs to Stage 4 compatible format.

One-time bridge for E2E testing: the new convergent extraction (stage2)
produces final FBs directly, but stages 3/4 still expect old-architecture
principle→cluster→merge flow. This passes the FBs through to stage4 format
so stage5 (DeBERTa NLI) can verify them.

Usage:
    python3 pipeline/bridge_s2_to_s4.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl  # D2332: fail-closed JSONL boundary
from pipeline.pipeline_paths import STAGE2_CHECKPOINT, STAGE4_CHECKPOINT


def convert() -> None:
    if not STAGE2_CHECKPOINT.exists():
        print("❌ Stage 2 checkpoint not found.")
        sys.exit(1)

    fbs: list[dict] = load_jsonl(STAGE2_CHECKPOINT, context="S2 checkpoint")

    print(f"📦 Converting {len(fbs)} FBs from Stage 2 → Stage 4 format")

    stage4_records: list[dict] = []
    for fb in fbs:
        record: dict = {
            "fb_id": fb["fb_id"],
            "name": fb.get("name", ""),
            "definition": fb.get("definition", ""),
            "description": fb.get("definition", "")[:500],
            "classification_data": {
                "discipline": fb.get("discipline", "emerging"),
                "domains": fb.get("domain", []),
                "depth": fb.get("depth", "domain"),
                "evidence": fb.get("evidence", "cited"),
            },
            "discipline": fb.get("discipline", "emerging"),
            "domains": fb.get("domain", []),
            "depth": fb.get("depth", "domain"),
            "evidence": fb.get("evidence", "cited"),
            "route": fb.get("route", "FB"),
            "source_principle_ids": [fb.get("fb_id", "")],
            "source_books": fb.get("source_books", []),
            "source_ids": fb.get("source_ids", []),  # D2376: canonical hashes (D2176) — restore provenance
            "source_segments": fb.get("source_segments", []),
            "source_cluster": fb.get("source_cluster", ""),
            "is_convergent": fb.get("is_convergent", False),
            "cluster_cohesion": fb.get("cluster_cohesion", 0.0),
            "mechanism": fb.get("mechanism", ""),
            "boundary": fb.get("boundary", ""),
            "consequence": fb.get("consequence", ""),
            "evidence_passages": fb.get("evidence_passages", []),
            "schema_version": fb.get("schema_version", "2.2"),
            "gen_model": fb.get("gen_model", ""),
            "pipeline_commit": fb.get("pipeline_commit", ""),
        }
        stage4_records.append(record)

    STAGE4_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    with open(STAGE4_CHECKPOINT, "w") as f:
        for r in stage4_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"✅ Wrote {len(stage4_records)} records to {STAGE4_CHECKPOINT}")


if __name__ == "__main__":
    convert()
