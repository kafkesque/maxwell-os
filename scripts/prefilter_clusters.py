#!/usr/bin/env python3
"""Cheap deterministic pre-LLM gate for un-extracted clusters (single-source AND singletons).

Looks up each cluster's source segment text and applies model-free actionability/
generality signals to decide whether the cluster is worth LLM extraction. Emits a
keep-list so the expensive S2 LLM never runs on noise/summary/narrative clusters.

Works for BOTH cluster shapes because both carry 'segment_ids':
  - single-source clusters (S1.5 checkpoint.jsonl): source_diversity==1, is_convergent==False
  - singletons (singletons.jsonl): size==1, is_singleton==True

Usage:
  python3 scripts/prefilter_clusters.py \
      --clusters "knowledge pipeline/stage1_5_embed_cluster/t11/singletons.jsonl" \
      --chunks "knowledge pipeline/stage1_chunk/t11/checkpoint.jsonl" \
      --config config/filtering.yaml \
      --out "knowledge pipeline/stage1_5_embed_cluster/t11/singletons.prefiltered.jsonl"
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml


def load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def atomic_write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_segments(chunks_path: str, needed_ids: set[str]) -> dict[str, dict[str, Any]]:
    """Load only the chunk records whose segment_id is in needed_ids."""
    segs: dict[str, dict[str, Any]] = {}
    with open(chunks_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            sid = d.get("segment_id", "")
            if sid in needed_ids:
                segs[sid] = d
    return segs


def count_hits(text: str, phrases: list[str]) -> int:
    low = text.lower()
    return sum(low.count(p.lower()) for p in phrases)


def score_text(text: str, imp_verbs: list[str], proc: list[str], anti: list[str]) -> dict[str, int]:
    return {
        "text_len": len(text),
        "imperatives": count_hits(text, imp_verbs),
        "procedural": count_hits(text, proc),
        "anti": count_hits(text, anti),
    }


def decide(s: dict[str, int], pf: dict[str, Any]) -> str:
    if s["text_len"] < int(pf["min_text_chars"]):
        return "SKIP"
    if s["anti"] > 0:
        return "SKIP"
    if s["imperatives"] >= int(pf["min_imperative_verbs"]) and s["procedural"] >= int(pf["min_procedural_phrases"]):
        return "EXTRACT"
    return "SKIP"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", required=True, help="S1.5 checkpoint.jsonl or singletons.jsonl")
    ap.add_argument("--chunks", required=True, help="stage1_chunk checkpoint.jsonl (segment_id -> text)")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=0, help="0 = process all clusters")
    args = ap.parse_args()

    cfg = load_config(args.config)
    imp_verbs: list[str] = cfg["imperative_verbs"]
    proc: list[str] = cfg["procedural_phrases"]
    anti: list[str] = cfg["anti_patterns"]

    clusters: list[dict[str, Any]] = []
    needed: set[str] = set()
    with open(args.clusters, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            clusters.append(d)
            needed.update(d.get("segment_ids", []))
            if args.max and len(clusters) >= args.max:
                break

    segs = load_segments(args.chunks, needed)

    out: list[dict[str, Any]] = []
    missing = 0
    for cl in clusters:
        texts: list[str] = []
        for sid in cl.get("segment_ids", []):
            seg = segs.get(sid)
            if seg and seg.get("text"):
                texts.append(seg["text"])
            else:
                missing += 1
        joined = "\n".join(texts)
        s = score_text(joined, imp_verbs, proc, anti)
        verdict = decide(s, cfg["prefilter"])
        out.append({
            "cluster_id": cl.get("cluster_id"),
            "is_singleton": bool(cl.get("is_singleton")),
            "is_convergent": bool(cl.get("is_convergent")),
            "source_diversity": cl.get("source_diversity"),
            "size": cl.get("size"),
            "verdict": verdict,
            **s,
        })

    atomic_write_jsonl(Path(args.out), out)

    counts = Counter(o["verdict"] for o in out)
    total = len(out)
    print(f"clusters: {total} (missing segments: {missing})")
    for v in sorted(counts, key=lambda k: -counts[k]):
        print(f"  {v:10s} {counts[v]:6d}  ({counts[v]/total*100:5.1f}%)")
    print(f"wrote: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
