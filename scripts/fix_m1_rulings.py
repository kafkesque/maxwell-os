#!/usr/bin/env python3
"""scripts/fix_m1_rulings.py — apply the user's M1 batch-ratification rulings.

User rulings 2026-09-20:
  A1 color psychology  -> color theory (drop from visual perception)
  A2 computational models of social life -> complex adaptive systems (drop from comp phys & sim)
  A3 decision science  -> decision making (drop from operations research)
  A4 simulation        -> computational physics & simulation (drop from operations research)
  B1 rhetoric          -> linguistics (drop from behavioral economics)
  B2 persuasion is design psychology: split the 'behavioural economics+persuasion' compound
     -> keep 'behavioural economics' head in behavioral economics; persuasion already in design psychology
  C  macroeconomics    -> economics (drop from political economy)

Surgical + section-aware (raw section only). Crash-safe write (C6) + backup (C13). --apply commits.
"""
from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TAX = _ROOT / "config" / "taxonomy_v5.yaml"

REMOVE: list[tuple[str, str]] = [
    ("visual perception", "Color Psychology"),
    ("computational physics & simulation", "Computational Models of Social Life"),
    ("operations research", "Decision Science"),
    ("operations research", "Simulation"),
    ("behavioral economics", "Rhetoric"),
    ("behavioral economics", "rhetoric"),
    ("behavioral economics", "behavioural economics+persuasion"),
    ("political economy", "macroeconomics"),
]

ADD: list[tuple[str, str]] = [
    ("linguistics", "Rhetoric"),
    ("linguistics", "rhetoric"),
    ("behavioral economics", "behavioural economics"),
    ("economics", "macroeconomics"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    lines = open(_TAX, encoding="utf-8").readlines()
    remove_by = {}
    for c, r in REMOVE:
        remove_by.setdefault(c, []).append(r)
    add_by = {}
    for c, r in ADD:
        add_by.setdefault(c, []).append(r)

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
            removes = remove_by.get(canon, [])
            adds = add_by.get(canon, [])
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
            # add missing raw lines before the definition line
            existing = {l.strip()[2:].strip() for l in new_block if l.strip().startswith("- ")}
            missing = [a for a in adds if a not in existing]
            if missing:
                insert_at = len(new_block)
                for j, l in enumerate(new_block):
                    if l.strip().startswith("definition:"):
                        insert_at = j
                        break
                for a in missing:
                    new_block.insert(insert_at, f"  - {a}\n")
                    insert_at += 1
                    log.append(f"  + {canon!r}: added {a!r}")
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
    bak = _TAX.with_name(f"taxonomy_v5.yaml.bak_{ts}_pre_m1")
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
