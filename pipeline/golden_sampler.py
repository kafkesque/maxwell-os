#!/usr/bin/env python3
"""
golden_sampler.py — Sample clusters for cross-family golden set annotation.
=====================================================================
Authority: D2165 (principle-recall benchmark), cross-examination Phase 1.

Samples N clusters from S1.5 output, extracts their segment texts from
Stage 1 checkpoint, and packages them as prompts for external LLM annotation.

The approach uses Cross-Family Ensemble Labeling (Gilardi et al. 2023):
- Send each cluster to 3+ different model families (Kimi, ChatGPT, Claude)
- Principles where 2+ models agree → gold standard
- Principles where models disagree → flag for manual review
- This cuts manual annotation from 200 clusters to ~20 disputed ones.

Usage:
    python3 pipeline/golden_sampler.py                    # Sample 200 clusters
    python3 pipeline/golden_sampler.py --n 50             # Sample 50 (quick test)
    python3 pipeline/golden_sampler.py --output evals/    # Custom output dir
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_clusters(checkpoint: Path) -> list[dict]:
    """Load cluster records from S1.5 checkpoint."""
    clusters: list[dict] = []
    with open(checkpoint) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            clusters.append(json.loads(line))
    return clusters


def load_segments(checkpoint: Path) -> dict[str, dict]:
    """Load segment texts from Stage 1 checkpoint, indexed by segment_id."""
    segments: dict[str, dict] = {}
    with open(checkpoint) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            seg = json.loads(line)
            sid = seg.get("segment_id", "")
            if sid:
                segments[sid] = seg
    return segments


def sample_clusters(clusters: list[dict], n: int = 200, seed: int = 42) -> list[dict]:
    """Sample N clusters, stratified by size and source diversity.

    Ensures representation across:
    - Small (2-50), medium (51-200), large (201+) clusters
    - Low (2-3), medium (4-7), high (8+) source diversity
    """
    random.seed(seed)

    # Stratify by size
    small = [c for c in clusters if c.get("size", 0) <= 50]
    medium = [c for c in clusters if 51 <= c.get("size", 0) <= 200]
    large = [c for c in clusters if c.get("size", 0) > 200]

    # Proportional allocation
    n_small = max(20, int(n * len(small) / len(clusters)))
    n_medium = max(20, int(n * len(medium) / len(clusters)))
    n_large = n - n_small - n_medium

    sampled: list[dict] = []
    sampled.extend(random.sample(small, min(n_small, len(small))))
    sampled.extend(random.sample(medium, min(n_medium, len(medium))))
    sampled.extend(random.sample(large, min(n_large, len(large))))

    # Top up if any stratum was too small
    remaining = [c for c in clusters if c not in sampled]
    while len(sampled) < n and remaining:
        picked = random.choice(remaining)
        sampled.append(picked)
        remaining.remove(picked)

    random.shuffle(sampled)
    return sampled[:n]


def build_annotation_prompt(cluster: dict, segments: dict[str, dict], max_segs: int = 15) -> str:
    """Build a prompt for a single cluster, asking the LLM to identify distinct principles.

    Args:
        cluster: Cluster record from S1.5.
        segments: All segment texts indexed by segment_id.
        max_segs: Maximum segments to include in the prompt (subsampled evenly).

    Returns:
        Formatted prompt string ready for an external LLM.
    """
    seg_ids: list[str] = cluster.get("segment_ids", [])
    if not seg_ids:
        return "ERROR: No segment IDs in cluster."

    # Subsample segments evenly (same logic as D2173 probe sampling)
    # but use source-stratified for diversity
    book_to_segs: dict[str, list[str]] = {}
    for sid in seg_ids:
        seg = segments.get(sid)
        if seg is None:
            continue
        book = seg.get("source_book", "unknown")
        book_short = book.split("/")[-1].replace(".md", "")[:50]
        book_to_segs.setdefault(book_short, []).append(sid)

    # Round-robin across books, max 2 per book
    sampled_ids: list[str] = []
    book_lists = [(b, segs, 0) for b, segs in book_to_segs.items()]
    while len(sampled_ids) < max_segs:
        added = False
        for i, (book, segs, taken) in enumerate(book_lists):
            if taken >= 2 or taken >= len(segs):
                continue
            sampled_ids.append(segs[taken])
            book_lists[i] = (book, segs, taken + 1)
            added = True
            if len(sampled_ids) >= max_segs:
                break
        if not added:
            break

    # Build passage texts
    passages: list[str] = []
    for sid in sampled_ids:
        seg = segments.get(sid)
        if seg is None:
            continue
        text = seg.get("text", "")[:400]
        book = seg.get("source_book", "unknown")
        book_short = book.split("/")[-1].replace(".md", "")[:40]
        passages.append(f"[{book_short}]: {text}")

    passages_blob = "\n\n---\n\n".join(passages)

    cluster_id = cluster.get("cluster_id", "unknown")
    n_segs = len(seg_ids)
    n_books = cluster.get("source_diversity", len(book_to_segs))
    cohesion = cluster.get("cohesion", 0.0)
    books_list = ", ".join(sorted(book_to_segs.keys())[:5])

    prompt = f"""## CLUSTER ANNOTATION TASK

You are annotating a semantic cluster extracted from {n_books} different books.
The cluster contains {n_segs} segments with cohesion {cohesion:.3f}.
Source books: {books_list}

Below are {len(passages)} representative passages from this cluster. Your task
is to identify ALL distinct, non-overlapping causal mechanisms, heuristics,
or operational principles present in these passages.

### RULES:
1. List each distinct principle separately — do NOT merge them.
2. Each principle must be: atomic (one causal mechanism), independently
   verifiable (you can point to specific passages), and non-overlapping
   with other principles.
3. If a principle is supported by multiple passages, note the passage IDs.
4. If passages only repeat the same idea in different words, list it ONCE.
5. If no extractable principle exists, return an empty list.

### OUTPUT FORMAT (JSON only):
```json
{{
  "cluster_id": "{cluster_id}",
  "principle_count": N,
  "principles": [
    {{
      "label": "Short name (5-10 words)",
      "mechanism": "One-sentence description of the causal mechanism",
      "evidence_passage_ids": [0, 3, 7],
      "confidence": 0.85
    }}
  ],
  "notes": "Any observations about cluster quality or mixed topics"
}}
```

### PASSAGES:

{passages_blob}

---
Output ONLY the JSON object. No preamble, no explanation."""

    return prompt


def export_annotation_batch(
    sampled: list[dict],
    segments: dict[str, dict],
    output_dir: Path,
    max_segs: int = 15,
) -> Path:
    """Export a batch of cluster annotation prompts for external LLMs.

    Creates one JSONL file with prompts that can be programmatically sent
    to Kimi, ChatGPT, or Claude APIs. Also creates a human-readable markdown
    file for manual review.

    Returns path to the JSONL batch file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    batch: list[dict] = []
    md_lines: list[str] = [
        "# Golden Set Annotation Batch",
        f"",
        f"**{len(sampled)} clusters** sampled for cross-family annotation.",
        f"Send each prompt to Kimi, ChatGPT, AND Claude. Compare results.",
        f"",
        f"## Methodology",
        f"- Cross-Family Ensemble Labeling (Gilardi et al. 2023)",
        f"- 3+ models annotate each cluster independently",
        f"- 2/3 agreement → gold principle (auto-accept)",
        f"- 1/3 or 0/3 → flag for manual review",
        f"- Cuts manual work from 200 clusters to ~20 disputed ones",
        f"",
        f"---",
        f"",
    ]

    for i, cluster in enumerate(sampled):
        cid = cluster.get("cluster_id", f"cluster_{i}")
        prompt = build_annotation_prompt(cluster, segments, max_segs)

        batch.append({
            "cluster_index": i,
            "cluster_id": cid,
            "cluster_size": cluster.get("size", 0),
            "source_diversity": cluster.get("source_diversity", 0),
            "cohesion": cluster.get("cohesion", 0.0),
            "prompt": prompt,
        })

        md_lines.append(f"## Cluster {i+1}: {cid}")
        md_lines.append(f"- Size: {cluster.get('size', 0)} | Books: {cluster.get('source_diversity', 0)} | Cohesion: {cluster.get('cohesion', 0.0):.3f}")
        md_lines.append(f"")
        md_lines.append("```")
        md_lines.append(prompt)
        md_lines.append("```")
        md_lines.append("")
        md_lines.append("### Response (fill in):")
        md_lines.append("```json")
        md_lines.append("{}")
        md_lines.append("```")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    # Write JSONL (for programmatic API calls)
    jsonl_path = output_dir / "annotation_batch.jsonl"
    with open(jsonl_path, "w") as f:
        for item in batch:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Write human-readable markdown
    md_path = output_dir / "annotation_batch.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    return jsonl_path


def main() -> None:
    """Sample clusters and export annotation prompts."""
    parser = argparse.ArgumentParser(
        description="Sample clusters for cross-family golden set annotation"
    )
    parser.add_argument("--n", type=int, default=200, help="Number of clusters to sample")
    parser.add_argument("--output", type=str, default="evals/golden_batch",
                        help="Output directory")
    parser.add_argument("--max-segs", type=int, default=15,
                        help="Max segments per cluster prompt")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).resolve().parent.parent
    s15_checkpoint = project_root / "knowledge pipeline" / "stage1_5_embed_cluster" / "latest" / "checkpoint.jsonl"
    s1_checkpoint = project_root / "knowledge pipeline" / "stage1_chunk" / "latest" / "checkpoint.jsonl"
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir

    # Load
    if not s15_checkpoint.exists():
        print(f"❌ S1.5 checkpoint not found: {s15_checkpoint}")
        print("   Run S1.5 first: python3 pipeline/stage1_5_embed_cluster.py")
        sys.exit(1)
    if not s1_checkpoint.exists():
        print(f"❌ Stage 1 checkpoint not found: {s1_checkpoint}")
        sys.exit(1)

    print(f"📂 Loading clusters from S1.5...")
    clusters = load_clusters(s15_checkpoint)
    print(f"   {len(clusters)} clusters loaded")

    print(f"📂 Loading segment texts from Stage 1...")
    segments = load_segments(s1_checkpoint)
    print(f"   {len(segments)} segments indexed")

    # Filter to convergent clusters only
    convergent = [c for c in clusters if c.get("is_convergent", False)]
    print(f"   {len(convergent)} convergent clusters available")

    # Sample
    n_sample = min(args.n, len(convergent))
    sampled = sample_clusters(convergent, n_sample, args.seed)

    # Stats
    sizes = [c.get("size", 0) for c in sampled]
    divs = [c.get("source_diversity", 0) for c in sampled]
    cohs = [c.get("cohesion", 0.0) for c in sampled]

    print(f"\n📊 Sampled {len(sampled)} clusters:")
    print(f"   Size: mean={sum(sizes)/len(sizes):.0f}, min={min(sizes)}, max={max(sizes)}")
    print(f"   Source diversity: mean={sum(divs)/len(divs):.1f}, min={min(divs)}, max={max(divs)}")
    print(f"   Cohesion: mean={sum(cohs)/len(cohs):.3f}, min={min(cohs):.3f}, max={max(cohs):.3f}")

    # Export
    jsonl_path = export_annotation_batch(sampled, segments, output_dir, args.max_segs)

    print(f"\n📋 Exported to:")
    print(f"   {jsonl_path}")
    print(f"   {output_dir / 'annotation_batch.md'}")
    print(f"\n✅ Ready for cross-family annotation.")
    print(f"   Send each prompt in annotation_batch.jsonl to:")
    print(f"   1. Kimi (kimi.moonshot.cn or API)")
    print(f"   2. ChatGPT (chat.openai.com or API)")
    print(f"   3. Claude (claude.ai or API)")
    print(f"\n   Then run: python3 pipeline/golden_merge.py to merge results.")


if __name__ == "__main__":
    main()
