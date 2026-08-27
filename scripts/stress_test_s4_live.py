#!/usr/bin/env python3
"""stress_test_s4_live.py — LIVE S4 stress test: diverse batch, all types × origins.

Unlike smoke_matrix_5x3.py (which picks ONE representative per cell and recycles
the same principle/TI/PT), this stress test samples a DIVERSE batch from the real
S2 corpora across every populated (origin × content_type) cell, stages it into an
isolated run-id, runs LIVE S4 classification (OMLX), audits the fresh output
against content_types.yaml, and measures per-FB speed.

Structural reality (BUG-166): convergent → principle only. So the honest matrix is:
    convergent      → principle (+ 1 PT anomaly in corpus)
    single_source   → principle, process_template, process_instance, tool_instruction, growth_edge
    singleton       → principle, process_template, process_instance, tool_instruction, growth_edge

Audit cross-checks (vs config/content_types.yaml):
  * metadata    — R14 stamps (schema_version/gen_model/pipeline_commit/pipeline_run_id/created_at)
  * properties  — per-type s2_body_fields + classification (content_type/extraction_type/depth/discipline/domains/evidence)
  * segments    — source_segments / source_cluster(s) / evidence_passages
  * provenance  — source_books / source_authors / citation / source_diversity / primary_source

Usage:
    python3 scripts/stress_test_s4_live.py [--per-cell 4] [--run-id stress_s4_live] [--seed 42]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline import pipeline_paths as pp  # noqa: E402
from audit_content_type_contract import audit_s4_dir, _load_ontology  # noqa: E402

VALID_CT = {"principle", "process_template", "process_instance", "growth_edge", "tool_instruction"}
DEDUP = pp.S2_DIR / "t11" / "checkpoint.jsonl"
SINGLETON = pp.S2_DIR / "t11" / "singleton_fbs.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _origin_of(r: dict) -> str:
    if r.get("is_singleton_fb") is True:
        return "singleton"
    if r.get("is_convergent") is True:
        return "convergent"
    return "single_source"


def sample_diverse(per_cell: int, seed: int) -> tuple[list[dict], list[dict], dict]:
    """Sample ≤per_cell records per populated (origin × type) cell.

    Returns (checkpoint_records, singleton_records, cell_map) where checkpoint_records
    hold single-source + convergent FBs and singleton_records hold singleton FBs.
    """
    rng = random.Random(seed)
    dedup = _load_jsonl(DEDUP)
    singleton = _load_jsonl(SINGLETON)

    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in dedup + singleton:
        ct = r.get("content_type")
        if ct not in VALID_CT:
            continue
        buckets[(_origin_of(r), ct)].append(r)

    cell_map: dict[tuple[str, str], int] = {}
    checkpoint_recs: list[dict] = []
    singleton_recs: list[dict] = []
    for (origin, ct), pool in sorted(buckets.items()):
        rng.shuffle(pool)
        sample = pool[:per_cell]
        cell_map[(origin, ct)] = len(sample)
        for r in sample:
            if origin == "singleton":
                singleton_recs.append(r)
            else:
                checkpoint_recs.append(r)
    return checkpoint_recs, singleton_recs, cell_map


def patch_paths(run_id: str) -> None:
    """Point pipeline_paths + stage4_merge at the per-run isolated dirs (no clobber)."""
    s2_dir = pp.S2_DIR / run_id
    s4_dir = pp.S4_DIR / run_id
    s2_dir.mkdir(parents=True, exist_ok=True)
    s4_dir.mkdir(parents=True, exist_ok=True)

    import pipeline.stage4_merge as s4m
    s4m.STAGE2_CHECKPOINT = s2_dir / "checkpoint.jsonl"
    # NOTE: load_stage2_fbs_via_clusters imports STAGE2_SINGLETON_OUTPUT via
    # `from pipeline.pipeline_paths import STAGE2_SINGLETON_OUTPUT` (a local import),
    # so it must be patched on pipeline_paths — not on stage4_merge.
    pp.STAGE2_SINGLETON_OUTPUT = s2_dir / "singleton_fbs.jsonl"
    s4m.STAGE4_CHECKPOINT = s4_dir / "checkpoint.jsonl"
    s4m.CHECKPOINT_DIR = s4_dir


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-cell", type=int, default=4)
    ap.add_argument("--run-id", default="stress_s4_live")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    checkpoint_recs, singleton_recs, cell_map = sample_diverse(args.per_cell, args.seed)
    total = len(checkpoint_recs) + len(singleton_recs)
    print(f"📂 Sampled {total} FBs across {len(cell_map)} populated cells:")
    for (origin, ct), n in sorted(cell_map.items()):
        print(f"     {origin:13s} × {ct:18s} = {n}")
    if total == 0:
        print("❌ No records sampled — check corpora paths.")
        return 2

    patch_paths(args.run_id)

    import pipeline.stage4_merge as s4m
    s2_dir = pp.S2_DIR / args.run_id
    (s2_dir / "checkpoint.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in checkpoint_recs), encoding="utf-8")
    (s2_dir / "singleton_fbs.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in singleton_recs), encoding="utf-8")

    print(f"\n🚀 === LIVE S4 MERGE + CLASSIFICATION ({total} FBs) ===\n")
    t0 = time.time()
    s4m.run_stage4()
    elapsed = time.time() - t0
    # Count actual classified principles (non-principle routing is LLM-free).
    s4_dir = pp.S4_DIR / args.run_id
    n_principle = 0
    if (s4_dir / "checkpoint.jsonl").exists():
        with open(s4_dir / "checkpoint.jsonl", encoding="utf-8") as f:
            n_principle = sum(1 for l in f if l.strip())
    per_principle = elapsed / n_principle if n_principle else 0.0
    print(f"\n⏱️  S4 SPEED: {elapsed:.1f}s total | {n_principle} principles classified | "
          f"{per_principle:.1f}s per principle (single-FB merged path)")

    # Audit fresh output against content_types.yaml
    onto = _load_ontology()
    s4_dir = pp.S4_DIR / args.run_id
    print(f"\n🔍 === S4 CONTRACT AUDIT (metadata/properties/segments/classification) ===\n")
    results, _ = audit_s4_dir(s4_dir, onto)
    hard_total = 0
    for ct, issues in results.items():
        hard = [i for i in issues if "DEFERRED" not in i]
        deferred = [i for i in issues if "DEFERRED" in i]
        hard_total += len(hard)
        print(f"  {ct:18s} — {len(hard)} hard / {len(deferred)} deferred (BUG-170)")
        for i in hard[:6]:
            print(f"        ❌ {i}")
    ok = hard_total == 0
    print("\n" + ("✅ S4 OUTPUT CONFORMS (0 hard gaps; deferred = BUG-170 non-principle enrichment)"
                 if ok else f"❌ S4 OUTPUT HAS {hard_total} HARD GAPS"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
