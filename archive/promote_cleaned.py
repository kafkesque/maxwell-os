#!/usr/bin/env python3
"""promote_cleaned.py — atomically promote post-hoc cleaned S2 files to canonical.

ROOT CAUSE of the 2026-08-27 file-drift (D2478): the non-destructive cleanup tools
(fix_singleton_quality.py → .fixed, fix_residual_violations.py → .final, S2 dedup →
.deduped) write to NEW filenames and rely on a manual promote step that never ran.
The pipeline reads the CANONICAL filenames (checkpoint.jsonl / singleton_fbs.jsonl),
so the cleaned-but-unpromoted siblings are dead ends.

This script performs that promote: atomically copies each cleaned variant over the
canonical, with a timestamped backup (crash-safe tempfile → fsync → os.replace, C6).

Promotion map (t11):
  singleton_fbs.final.jsonl → singleton_fbs.jsonl   (5,244 — dropped 10 + filled/blanked)
  checkpoint.deduped.jsonl  → checkpoint.jsonl      (8,402 — deduped 8 + passage-cleaned)

Usage:
    python3 scripts/promote_cleaned.py --dry-run     # show what WOULD be promoted
    python3 scripts/promote_cleaned.py --apply       # promote (backs up canonical first)
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
T11 = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11"

# (canonical name, cleaned name)
PROMOTIONS = [
    ("singleton_fbs.jsonl", "singleton_fbs.final.jsonl"),
    ("checkpoint.jsonl", "checkpoint.deduped.jsonl"),
]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _atomic_copy(src: Path, dst: Path) -> None:
    tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".tmp", delete=False, dir=str(dst.parent))
    try:
        tmp.write(src.read_bytes())
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, dst)
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="promote (backs up canonical first)")
    ap.add_argument("--dry-run", action="store_true", help="show what WOULD be promoted")
    args = ap.parse_args()

    ts = time.strftime("%Y%m%d_%H%M%S")
    for canon_name, cleaned_name in PROMOTIONS:
        canon = T11 / canon_name
        cleaned = T11 / cleaned_name
        if not cleaned.exists():
            print(f"  ⏭️  {cleaned_name} missing — skip")
            continue
        if not canon.exists():
            print(f"  ⏭️  {canon_name} missing — cannot promote (nothing to back up)")
            continue
        same = _sha(canon) == _sha(cleaned)
        status = "identical (no-op)" if same else f"differs → would promote ({cleaned_name} → {canon_name})"
        print(f"  {'✓' if same else '→'} {cleaned_name} vs {canon_name}: {status}")
        if args.apply and not same:
            bak = canon.with_name(f"{canon_name}.pre_promote_{ts}")
            shutil.copy2(canon, bak)
            _atomic_copy(cleaned, canon)
            print(f"     ✅ promoted. backup: {bak.name}")

    if args.dry_run:
        print("\n(dry-run — re-run with --apply to promote)")
    elif args.apply:
        print("\n✅ promotion complete. Re-run `just integrity` to confirm check #18 clears.")
    else:
        print("\n💡 re-run with --apply to promote (backs up canonical first).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
