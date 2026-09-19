#!/usr/bin/env python3
"""Purge harness-artifact checkpoint rows that _done_keys() will never re-measure (BUG-262).

WHY: model_eval_suite._done_keys() skips any (model, suite, id) already present without err.
The 20 gpt-oss toolcalling rows measured BEFORE the reasoning-off prefix was applied therefore
survive every re-run: the suite prints '0 new results' and the model keeps a 0.00 it never earned.
Deleting rows silently would also be wrong, so --apply ARCHIVES the original first.

    python3 scripts/purge_stale_rows.py            # dry-run
    python3 scripts/purge_stale_rows.py --apply    # archive + rewrite (crash-safe)
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from check_stale_toolcall_rows import find_stale, load_guards  # noqa: E402
from pipeline.io_guard import safe_write  # noqa: E402


def main() -> int:
    """Report or purge stale rows. Returns the exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="archive the original, then rewrite")
    args = ap.parse_args()

    guards = load_guards()
    markers = list(guards.get("markers") or [])
    path = REPO / str(guards["checkpoint"])
    if not path.exists():
        print("checkpoint missing: " + str(path))
        return 2
    original = path.read_text(encoding="utf-8").splitlines()
    stale = find_stale(path, markers)
    total = len([l for l in original if l.strip()])
    print("checkpoint: " + str(path.relative_to(REPO)))
    print("  rows: " + str(total))
    print("  stale: " + str(len(stale)))
    for r in stale[:10]:
        print("    " + str(r.get("_bug")) + " " + str(r.get("model")) + " " + str(r.get("suite"))
              + " " + str(r.get("id")))
    if not stale:
        return 0
    if not args.apply:
        print("  dry-run: pass --apply to archive and rewrite")
        return 0

    import json

    stale_keys = {(str(r.get("model")), str(r.get("suite")), str(r.get("id"))) for r in stale}
    kept: list[str] = []
    for line in original:
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            kept.append(line)
            continue
        key = (str(r.get("model")), str(r.get("suite")), str(r.get("id")))
        if key in stale_keys:
            continue
        kept.append(line)

    archive = REPO / "backup" / "deletions" / ("model_eval_checkpoint_pre_bug262_" + time.strftime("%Y%m%d_%H%M%S") + ".jsonl")
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, archive)
    print("  archived original -> " + str(archive.relative_to(REPO)))
    safe_write(str(path), "\n".join(kept) + "\n")
    after = len([l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()])
    print("  rows after: " + str(after) + " (removed " + str(total - after) + ")")
    if find_stale(path, markers):
        print("  VERIFY FAILED: stale rows still present")
        return 1
    print("  verified: guard now clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
