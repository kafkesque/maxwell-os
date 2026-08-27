#!/usr/bin/env python3
"""fix_s2_posthoc.py — post-hoc (LLM-free) repair of the S2 "stale" classes.

The 451-record forensic audit splits into two tiers:
  * POST-HOC fixable (this script, deterministic, zero LLM):
      - elaboration non-empty on a NON-principle → blank it (elaboration is
        PRINCIPLE-ONLY, D2448/D2452 — the empty string is the schema-correct value).
      - process_instance missing outcome_metric → fill "" (D2452 typed placeholder;
        "" = "no metric recorded", legitimate).
  * LLM re-extraction (NOT this script — see rerun_s2_targeted.py):
      - tool_instruction missing parameters → cannot be fabricated; parameters:[] would
        falsely claim "no inputs" (BUG-169). Must re-extract.
      - singleton empty-shell (empty steps/actors/parameters) → must re-extract.

Safety (C6 + R-D410): backs up checkpoint.deduped.jsonl before mutation, then writes
via tempfile → fsync → os.replace. Idempotent — re-running changes nothing further.

Usage:
    python3 scripts/fix_s2_posthoc.py --dry-run     # report only
    python3 scripts/fix_s2_posthoc.py --apply       # mutate (backs up first)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CKPT = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.deduped.jsonl"


def _load() -> list[dict]:
    raw = CKPT.read_text(encoding="utf-8")
    try:
        return [json.loads(l) for l in raw.splitlines() if l.strip()]
    except json.JSONDecodeError:
        d = json.loads(raw)
        return d if isinstance(d, list) else [d]


def _atomic_write(path: Path, content: str) -> None:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".tmp", delete=False, dir=str(path.parent))
    try:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, path)
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="mutate checkpoint (backs up first)")
    ap.add_argument("--dry-run", action="store_true", help="report only")
    args = ap.parse_args()

    recs = _load()
    blanked_elab = 0
    filled_outcome = 0
    for r in recs:
        ct = r.get("content_type")
        if ct == "principle":
            continue
        # 1. blank elaboration on non-principle (PRINCIPLE-ONLY)
        if str(r.get("elaboration") or "").strip():
            r["elaboration"] = ""
            blanked_elab += 1
        # 2. fill outcome_metric placeholder on process_instance
        if ct == "process_instance" and "outcome_metric" not in r:
            r["outcome_metric"] = ""
            filled_outcome += 1

    print(f"📊 post-hoc fixes applied:")
    print(f"   elaboration blanked (non-principle): {blanked_elab}")
    print(f"   outcome_metric filled ('' on PI):     {filled_outcome}")
    print(f"   total records touched: {len({id(r) for r in recs if True})} / {len(recs)} loaded")

    if args.dry_run:
        print("   (dry-run — no writes)")
        return 0

    if args.apply:
        bak = CKPT.with_name(f"{CKPT.name}.pre_posthoc_{time.strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(CKPT, bak)
        _atomic_write(CKPT, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs))
        print(f"✅ Wrote {len(recs)} records → {CKPT}")
        print(f"   backup: {bak}")
    else:
        print("\n💡 re-run with --apply to mutate (backs up first).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
