#!/usr/bin/env python3
"""Post-hoc deterministic value triage for already-extracted S2 records.

Scores each record with model-free signals (convergence, actionability, richness)
and assigns a keep/drop/dedup verdict. No LLM calls — minutes, not hours.

Usage:
  python3 scripts/score_single_source.py \
      --checkpoint "knowledge pipeline/stage2_extract/t11/checkpoint.jsonl" \
      --config config/filtering.yaml \
      --out-dir "knowledge pipeline/stage2_extract/t11"
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

KEEP_VERDICTS = frozenset({
    "KEEP_CONVERGENT", "KEEP_TOOL", "KEEP_ACTIONABLE", "KEEP_RICH", "KEEP_GROWTH_EDGE",
})


def load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Crash-safe write: tempfile -> fsync -> os.replace (C6)."""
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


def count_hits(text: str, phrases: list[str]) -> int:
    low = text.lower()
    return sum(low.count(p.lower()) for p in phrases)


def _truthy(v: Any) -> bool:
    if isinstance(v, (list, str, dict)):
        return len(v) > 0
    return bool(v)


def score_record(rec: dict[str, Any], imp_verbs: list[str]) -> dict[str, Any]:
    text = f"{rec.get('definition') or ''} {rec.get('mechanism') or ''}"
    steps = rec.get("steps")
    n_steps = len(steps) if isinstance(steps, list) else 0
    return {
        "fb_id": rec.get("fb_id"),
        "name": rec.get("name"),
        "content_type": rec.get("content_type"),
        "extraction_type": rec.get("extraction_type"),
        "is_convergent": bool(rec.get("is_convergent")),
        "source_diversity": int(rec.get("source_diversity") or 0),
        "n_steps": n_steps,
        "has_trigger": _truthy(rec.get("trigger")),
        "has_done": _truthy(rec.get("done_condition")),
        "has_params": _truthy(rec.get("parameters")),
        "has_example": _truthy(rec.get("example")),
        "richness": len(text),
        "imperatives": count_hits(text, imp_verbs),
    }


def classify(s: dict[str, Any], cfg: dict[str, Any]) -> tuple[str, str]:
    ph: dict[str, Any] = cfg["post_hoc"]
    if s["is_convergent"]:
        return "KEEP_CONVERGENT", "cross-source synthesis (the product)"
    ct = s["content_type"]
    if ct == "process_instance":
        if s["n_steps"] > 0:
            return "KEEP_ACTIONABLE", "process_instance with explicit steps"
        return "DROP_ANECDOTE", "process_instance without steps (case study/anecdote)"
    if ct == "tool_instruction":
        return "KEEP_TOOL", "tool_instruction (concrete, reusable)"
    if ct == "process_template":
        if s["n_steps"] > 0 and s["has_trigger"] and s["has_done"]:
            return "KEEP_ACTIONABLE", "process_template with steps+trigger+done"
        return "DROP_THIN", "process_template missing trigger/done structure"
    if ct == "growth_edge":
        return "KEEP_GROWTH_EDGE", "rare speculative object"
    # single-source principle
    if s["richness"] >= int(ph["min_richness_chars"]) and s["imperatives"] >= int(ph["min_imperative_verbs"]):
        return "KEEP_RICH", "substantive + actionable principle"
    return "DROP_THIN", "thin/descriptive paraphrase"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    imp_verbs: list[str] = cfg["imperative_verbs"]

    rows: list[dict[str, Any]] = []
    with open(args.checkpoint, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            s = score_record(rec, imp_verbs)
            verdict, reason = classify(s, cfg)
            s["verdict"] = verdict
            s["reason"] = reason
            rows.append(s)

    # dedup by fb_id (BUG-164): first occurrence keeps its verdict, rest -> DEDUP
    seen: dict[str, int] = {}
    for i, s in enumerate(rows):
        fid = s["fb_id"]
        if fid in seen:
            rows[i]["verdict"] = "DEDUP"
            rows[i]["reason"] = "duplicate fb_id (near-dup of earlier record)"
        else:
            seen[fid] = i

    out_dir = Path(args.out_dir)
    atomic_write_jsonl(out_dir / "value_triage.jsonl", rows)
    keep_ids = [{"fb_id": s["fb_id"]} for s in rows if s["verdict"] in KEEP_VERDICTS]
    atomic_write_jsonl(out_dir / "value_keep_ids.jsonl", keep_ids)

    counts = Counter(s["verdict"] for s in rows)
    total = len(rows)
    print(f"total records: {total}")
    for v in sorted(counts, key=lambda k: -counts[k]):
        print(f"  {v:20s} {counts[v]:5d}  ({counts[v]/total*100:4.1f}%)")
    kept = sum(1 for s in rows if s["verdict"] in KEEP_VERDICTS)
    print(f"KEEP total: {kept} ({kept/total*100:.1f}%)")
    print(f"wrote: {out_dir / 'value_triage.jsonl'}")
    print(f"wrote: {out_dir / 'value_keep_ids.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
