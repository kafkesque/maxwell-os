#!/usr/bin/env python3
"""scripts/fix_bug309_unambiguous.py — resolve the 7 unambiguous BUG-309 cross-listings.

BUG-309 = 11 non-core raw-alias cross-listings left after the D-285 fix. This script
resolves ONLY the 7 where one canonical is objectively correct (the other claims a term
whose exclude-list or whose very field-of-study excludes it). The 4 genuinely-ambiguous
ones (color psychology / computational models of social life / decision science /
simulation) + 2 misplacements (rhetoric / behavioural economics+persuasion) are left for
human batch-ratification (governance/bug309_batch_ratification.md).

SURGICAL + section-aware (removes only from the `raw:` section, never `exclude:`, and
never re-wraps the file). Crash-safe write (C6) + backup (C13). --apply commits.
"""
from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TAX = _ROOT / "config" / "taxonomy.yaml"

# (wrong canonical, exact raw string to remove) — keep in the TRUE home, drop from the wrong one.
REMOVE: list[tuple[str, str]] = [
    ("political economy", "economic theory"),        # -> economics
    ("political economy", "microeconomics"),          # -> economics
    ("systems engineering", "Software Architecture"), # -> software engineering
    ("systems thinking", "Systems Design"),           # -> systems engineering
    ("decision making", "Strategic Decision Making"), # -> strategic thinking
    ("machine learning", "Large Language Models"),    # -> generative ai
    ("visual perception", "computer vision"),         # -> machine learning
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    lines = open(_TAX, encoding="utf-8").readlines()
    remove_by_canon: dict[str, list[str]] = {}
    for c, r in REMOVE:
        remove_by_canon.setdefault(c, []).append(r)

    out: list[str] = []
    log: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("- canonical: "):
            canon = line[len("- canonical: "):].strip()
            start = i
            i += 1
            while i < len(lines) and not lines[i].startswith("- canonical: "):
                i += 1
            block = lines[start:i]
            removes = remove_by_canon.get(canon, [])
            new_block: list[str] = []
            in_raw = False
            removed: set[str] = set()
            for bl in block:
                s = bl.strip()
                if s == "raw:":
                    in_raw = True
                    new_block.append(bl)
                    continue
                if in_raw and s.startswith(("group:", "definition:", "exclude:", "disposition:")):
                    in_raw = False
                if in_raw and s.startswith("- ") and s[2:].strip() in removes and s[2:].strip() not in removed:
                    removed.add(s[2:].strip())
                    log.append(f"  - {canon!r}: removed {s[2:].strip()!r}")
                    continue
                new_block.append(bl)
            out.extend(new_block)
        else:
            out.append(line)
            i += 1

    print("planned changes:")
    for l in log:
        print(l)
    if not args.apply:
        print("\n(dry-run — re-run with --apply)")
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = _TAX.with_name(f"taxonomy.yaml.bak_{ts}_pre_bug309")
    os.replace(_TAX, bak)
    fd, tmp = tempfile.mkstemp(dir=str(_TAX.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("".join(out))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, _TAX)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    print(f"   ✅ wrote {_TAX.name} (backup: {bak.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
