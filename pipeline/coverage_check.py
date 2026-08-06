#!/usr/bin/env python3
"""Coverage gap analysis for Stage 2 FBs — residual embedding check (D2149)."""

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    COVERAGE_FLAG_FRACTION,
    COVERAGE_THRESHOLD,
    STAGE1_CHECKPOINT,
    STAGE2_CHECKPOINT,
)

# ── Constants (T0.3: de-hardcoded — sourced from pipeline_config.yaml) ────
# COVERAGE_THRESHOLD and FLAG_FRACTION are now imported directly from pipeline_paths.py
# (which reads them from config/pipeline_config.yaml → coverage: section)
_COVERAGE_FLAG_FRACTION: float = COVERAGE_FLAG_FRACTION  # re-export for backward compat

# D2158: read embedding model from config, not hardcoded
try:
    from pipeline.pipeline_paths import S15_EMBED_MODEL_HF as _cfg_embed_model
    MODEL_NAME: str = _cfg_embed_model
except ImportError:
    MODEL_NAME: str = "BAAI/bge-m3"  # D2182: unified — was bge-small; now bge-m3 via Ollama (D2190)


def load_segments():
    segments = {}
    if not STAGE1_CHECKPOINT.exists():
        print(f"ERROR: Stage 1 checkpoint missing: {STAGE1_CHECKPOINT}")
        sys.exit(1)
    with open(STAGE1_CHECKPOINT) as f:
        for line in f:
            if not line.strip():
                continue
            seg = json.loads(line)
            sid = seg.get("segment_id", "")
            if sid:
                segments[sid] = seg
    return segments


def compute_coverage(fbs, segments, model, threshold):
    results = []
    for fb in fbs:
        fb_def = fb.get("definition", fb.get("name", ""))
        if not fb_def:
            continue
        fb_emb = model.encode([fb_def], normalize_embeddings=True)[0]
        seg_ids = fb.get("source_segments", [])
        covered, under, sims = 0, [], []
        for sid in seg_ids:
            seg = segments.get(sid)
            if not seg or not seg.get("text", "").strip():
                continue
            seg_emb = model.encode([seg["text"][:1000]], normalize_embeddings=True)[0]
            sim = float(np.dot(fb_emb, seg_emb))
            sims.append(sim)
            if sim >= threshold:
                covered += 1
            else:
                under.append(sid)
        total = len(sims)
        frac = len(under) / total if total else 0.0
        results.append({
            "fb_id": fb.get("fb_id", "?"),
            "cluster_id": fb.get("source_cluster", "?"),
            "name": fb.get("name", "?")[:60],
            "total_segments": total,
            "covered": covered,
            "under_covered": len(under),
            "under_covered_fraction": round(frac, 4),
            "mean_similarity": round(float(np.mean(sims)) if sims else 1.0, 4),
            "flagged": frac > _COVERAGE_FLAG_FRACTION,
            "under_covered_segment_ids": under[:20],
        })
    return results


def main():
    parser = argparse.ArgumentParser(description="Coverage gap analysis (D2149)")
    parser.add_argument("--threshold", type=float,
                        default=COVERAGE_THRESHOLD)          # T0.3: from config
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    if not STAGE2_CHECKPOINT.exists():
        print("No S2 checkpoint. Run stage2_extract.py first.")
        sys.exit(1)

    fbs = [json.loads(line) for line in open(STAGE2_CHECKPOINT) if line.strip()]
    print(f"Loaded {len(fbs)} FBs")
    segments = load_segments()
    print(f"Loaded {len(segments)} segments")

    from sentence_transformers import SentenceTransformer
    print(f"Loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, device="mps")

    results = compute_coverage(fbs, segments, model, args.threshold)
    flagged = [r for r in results if r["flagged"]]
    clean = [r for r in results if not r["flagged"]]

    bar = "=" * 60
    print(f"\n{bar}")
    print("COVERAGE ANALYSIS")
    print(f"  Total FBs:            {len(results)}")
    print(f"  Clean (>70% covered): {len(clean)}")
    print(f"  Flagged (<70%):       {len(flagged)} ({len(flagged)/max(len(results),1)*100:.1f}%)")
    if results:
        all_sims = [r["mean_similarity"] for r in results]
        all_under = [r["under_covered_fraction"] for r in results]
        print(f"  Mean similarity:      {statistics.mean(all_sims):.4f}")
        print(f"  Median similarity:    {statistics.median(all_sims):.4f}")
        print(f"  Mean under-covered:   {statistics.mean(all_under)*100:.1f}%")

    if flagged:
        print("\nFLAGGED CLUSTERS (potential under-extraction):")
        for r in sorted(flagged, key=lambda x: -x["under_covered_fraction"])[:10]:
            print(f"  [{r['under_covered_fraction']*100:.0f}%] {r['name'][:55]} ({r['under_covered']}/{r['total_segments']} segs)")
        if args.output:
            with open(args.output, "w") as f:
                for r in flagged:
                    f.write(json.dumps(r) + "\n")
            print(f"\nExported {len(flagged)} flagged to {args.output}")


if __name__ == "__main__":
    main()
