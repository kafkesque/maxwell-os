#!/usr/bin/env python3
"""Sweep source-referential meta-commentary from S2 (task #4 / R1.3).

Strips LEADING framing ("The passage suggests that ..." -> keeps the content)
from mechanism/elaboration/definition/body. Flags EMBEDDED occurrences for
review rather than auto-stripping. Deterministic, no LLM.

Usage:
  python3 scripts/sweep_passage_meta.py \
      --checkpoint "knowledge pipeline/stage2_extract/t11/checkpoint.jsonl" \
      --config config/filtering.yaml \
      --out-dir "knowledge pipeline/stage2_extract/t11"
"""
from __future__ import annotations
import argparse, json, os, tempfile
from pathlib import Path
from typing import Any

import yaml

FIELDS = ("mechanism", "elaboration", "definition", "body")


def atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, str(path))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def build_patterns(cfg: dict[str, Any]) -> tuple[Any, Any]:
    subj = "|".join(cfg["passage_meta"]["subjects"])
    verb = "|".join(cfg["passage_meta"]["verbs"])
    lead = "|".join(cfg["passage_meta"]["verbs"])
    # leading framing at string start: "The/This <subject> <verb> [that/how/...] "
    lead_re = "^(The|This) (" + subj + ") (" + verb + ")( (that|how|why|whether|what|the))?"
    import re
    lead_pat = re.compile(lead_re, re.IGNORECASE)
    any_pat = re.compile("(The|This) (" + subj + ") (" + verb + ")", re.IGNORECASE)
    return lead_pat, any_pat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    lead_pat, any_pat = build_patterns(cfg)

    rows = [json.loads(l) for l in open(args.checkpoint, encoding="utf-8") if l.strip()]
    report: list[dict[str, Any]] = []
    stripped = 0

    for r in rows:
        stripped_fields: list[str] = []
        embedded: list[str] = []
        for f in FIELDS:
            v = r.get(f)
            if not isinstance(v, str):
                continue
            if lead_pat.search(v):
                new = lead_pat.sub("", v, count=1)
                if new:
                    new = new[0].upper() + new[1:]
                r[f] = new
                stripped_fields.append(f)
            elif any_pat.search(v):
                embedded.append(f)
        if stripped_fields:
            stripped += 1
        if stripped_fields or embedded:
            report.append({"fb_id": r["fb_id"], "name": r["name"],
                           "stripped_fields": stripped_fields, "embedded_remaining": embedded})

    out = Path(args.out_dir)
    atomic_write_jsonl(out / "s2_passage_meta_report.jsonl", report)
    atomic_write_jsonl(out / "checkpoint.passage_cleaned.jsonl", rows)

    print(f"records flagged: {len(report)}")
    print(f"leading-framing stripped: {stripped}")
    print(f"wrote: s2_passage_meta_report.jsonl, checkpoint.passage_cleaned.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
