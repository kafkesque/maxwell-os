#!/usr/bin/env python3
"""Dedup the S2 checkpoint (task #2 / BUG-164 / R1.4).

Auto-drops exact fb_id duplicates (same name + definition -> same fb_id). Flags
near-duplicate name groups as REVIEW candidates (auto-drop would risk merging
genuinely distinct same-titled records). Deterministic, no LLM.

Usage:
  python3 scripts/dedup_s2.py \
      --checkpoint "knowledge pipeline/stage2_extract/t11/checkpoint.jsonl" \
      --out-dir "knowledge pipeline/stage2_extract/t11"
"""
from __future__ import annotations
import argparse, json, os, re, tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any


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


def norm_name(name: Any) -> str:
    n = re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()
    return " ".join(sorted(n.split()))


def rank_key(r: dict[str, Any]) -> tuple[int, int]:
    text = f"{r.get('definition') or ''} {r.get('mechanism') or ''}"
    return (0 if r.get("is_convergent") else 1, -len(text))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.checkpoint, encoding="utf-8") if l.strip()]

    drop_idx: set[int] = set()
    report: list[dict[str, Any]] = []

    # 1. exact fb_id duplicates -> auto-drop surplus
    by_fid: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        by_fid[r["fb_id"]].append(i)
    for fid, idxs in by_fid.items():
        if len(idxs) > 1:
            idxs.sort(key=lambda i: rank_key(rows[i]))
            for i in idxs[1:]:
                drop_idx.add(i)
                report.append({"kind": "exact_fb_id", "drop": True, "review": False,
                               "fb_id": fid, "name": rows[i]["name"]})

    # 2. near-duplicate name groups -> REVIEW candidates (not auto-dropped)
    by_name: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        by_name[norm_name(r["name"])].append(i)
    for nm, idxs in by_name.items():
        uniq = {rows[i]["fb_id"] for i in idxs}
        if len(uniq) > 1:
            idxs.sort(key=lambda i: rank_key(rows[i]))
            for i in idxs[1:]:
                report.append({"kind": "near_dup_name", "drop": False, "review": True,
                               "fb_id": rows[i]["fb_id"], "name": rows[i]["name"],
                               "norm_name": nm})

    kept = [r for i, r in enumerate(rows) if i not in drop_idx]
    out = Path(args.out_dir)
    atomic_write_jsonl(out / "s2_dedup_report.jsonl", report)
    atomic_write_jsonl(out / "s2_dedup_drop_ids.jsonl",
                       [{"fb_id": rows[i]["fb_id"], "name": rows[i]["name"]} for i in sorted(drop_idx)])
    atomic_write_jsonl(out / "checkpoint.deduped.jsonl", kept)

    exact = sum(1 for r in report if r["kind"] == "exact_fb_id")
    neardup = sum(1 for r in report if r["kind"] == "near_dup_name")
    print(f"total: {len(rows)}")
    print(f"auto-dropped (exact fb_id): {exact}")
    print(f"near-dup name REVIEW candidates: {neardup}")
    print(f"kept in checkpoint.deduped.jsonl: {len(kept)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
