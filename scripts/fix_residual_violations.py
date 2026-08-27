#!/usr/bin/env python3
"""fix_residual_violations.py — drop/fill the 20 skeleton-gap residuals (D2474).

Operates on singleton_fbs.jsonl (canonical) and writes in-place (D2479 option-a:
no .fixed/.final dead-end siblings). Deterministic, verifiable, crash-safe (C6).

Three classes of residual S2-contract violation (the ones fix_singleton_quality.py
could NOT deterministically repair):

  1. FILL — empty `extraction_type` → config-driven weakest-honest default from
     content_to_extraction_type (D2417). VERIFIABLE (pure config lookup), zero
     hallucination risk.
  2. DROP — `principle` with empty `elaboration` (D2448: elaboration REQUIRED for
     principle). Cannot be filled without LLM re-derivation of "deeper nuance"
     (that IS hallucination). Dropped to a manifest, not silently deleted.
  3. NOTE — `tool_instruction` with empty shared skeleton (mechanism/boundary/
     consequence): a WELL-FORMED TI (description/output/caveats/parameters all
     populated); the empty skeleton is a principle-centric schema-fit artifact,
     not a data gap. Flagged `skeleton_schema_fit_note`, NOT dropped.

R14 stamps are NOT re-stamped (repair, not re-generation). Drops are recorded in
a drop manifest (fb_id + name + reason) for auditability/reversibility.

Usage:
    python3 scripts/fix_residual_violations.py --dry-run
    python3 scripts/fix_residual_violations.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.content_types import CONTENT_TO_EXTRACTION_TYPE  # D2417 config-first

INPUT = "knowledge pipeline/stage2_extract/t11/singleton_fbs.jsonl"  # D2479: canonical (no .fixed)

_SKELETON = ("mechanism", "boundary", "consequence")


def _empty(v) -> bool:
    return v is None or (isinstance(v, (str, list, dict)) and len(v) == 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--input", default=INPUT)
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"❌ {src} not found", file=sys.stderr)
        return 2

    records = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]

    filled = 0
    dropped: list[dict] = []
    noted = 0
    kept: list[dict] = []

    for rec in records:
        ct = rec.get("content_type")

        # 2. DROP principle with empty elaboration (cannot fill without hallucination)
        if ct == "principle" and _empty(rec.get("elaboration")):
            dropped.append({
                "fb_id": rec.get("fb_id"),
                "name": rec.get("name"),
                "reason": "principle empty elaboration (D2448 REQUIRED) — not fillable without LLM re-derivation",
            })
            continue

        # 1. FILL empty extraction_type via weakest-honest config default (D2417)
        if _empty(rec.get("extraction_type")):
            rec["extraction_type"] = CONTENT_TO_EXTRACTION_TYPE.get(ct, "descriptive_model")
            rec["extraction_type_repaired"] = "weakest_honest_default"
            filled += 1

        # 3. NOTE tool_instruction with empty shared skeleton (schema-fit, not data gap)
        if ct == "tool_instruction" and any(_empty(rec.get(k)) for k in _SKELETON):
            rec["skeleton_schema_fit_note"] = (
                "shared_skeleton_empty_principle_centric — TI body populated via "
                "description/output/caveats/parameters; schema decision pending (D2474)"
            )
            noted += 1

        kept.append(rec)

    print(f"Records in:  {len(records)}")
    print(f"  FILLED extraction_type (weakest-honest): {filled}")
    print(f"  DROPPED principle (empty elaboration):  {len(dropped)}")
    print(f"  NOTED TI empty-skeleton (schema-fit):   {noted}")
    print(f"  Records out: {len(kept)}")

    if args.dry_run:
        for d in dropped:
            print(f"    DROP  {d['fb_id']}  {d['name']}")
        print("DRY-RUN — no write.")
        return 0

    # Crash-safe write (C6): tempfile → fsync → os.replace. Never overwrite pipeline
    # output in place (R-D410).
    out = src  # D2479 option-(a): write in-place to canonical (no .final dead-end)
    manifest = src.with_name("drop_manifest.jsonl")
    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in kept) + "\n"

    for path, data in ((out, content),
                       (manifest, "\n".join(json.dumps(d, ensure_ascii=False) for d in dropped) + "\n")):
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    print(f"WROTE {out}")
    print(f"WROTE {manifest} ({len(dropped)} dropped)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
