#!/usr/bin/env python3
"""D2503 — rename canonical domain `ai systems` → `ml systems & infrastructure`.

Disambiguation (roundtable finding): `ai systems` and `ai & agents` are BOTH
canonical domains and BOTH had the raw alias "AI Systems" (case-variant), so the
synonym index collided and the open-set S4 classifier emitted the two
interchangeably. They are semantically DISTINCT:
  - `ai & agents` = agentic / multi-agent systems
  - `ml systems & infrastructure` = ML/LLM engineering + serving + MLOps

This script post-hoc renames ONLY the canonical `domains` value in the promoted
checkpoint (order-preserving, non-destructive). `domains_raw` is left untouched
(raw labels are what S4 emitted). Deterministic + crash-safe (tempfile→fsync→
os.replace). Backs up the original before writing.

Usage: python3 scripts/rename_ai_systems_domain.py [checkpoint.jsonl]
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

OLD = "ai systems"
NEW = "ml systems & infrastructure"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT = PROJECT_ROOT / "knowledge pipeline" / "stage4_merge" / "t11" / "checkpoint_enriched.jsonl"


def rename_domains(record: dict) -> bool:
    """Rename OLD→NEW in the canonical `domains` list; return True if changed."""
    doms = record.get("domains")
    if not isinstance(doms, list) or OLD not in doms:
        return False
    # Preserve order + uniqueness semantics: replace in place, drop dupes.
    new_doms: list[str] = []
    seen: set[str] = set()
    for d in doms:
        d = NEW if d == OLD else d
        if d not in seen:
            new_doms.append(d)
            seen.add(d)
    record["domains"] = new_doms
    return True


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.exists():
        print(f"❌ checkpoint not found: {path}", file=sys.stderr)
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = path.parent / f"backup_pre_ai_systems_rename_{stamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_dir / path.name)
    print(f"📦 backed up to {backup_dir}")

    records: list[dict] = []
    changed = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if rename_domains(r):
                changed += 1
            records.append(r)

    # Crash-safe write (C6)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)

    print(f"✅ renamed {OLD!r} → {NEW!r} in {changed}/{len(records)} records")
    if changed == 0:
        print("   (no records contained the old canonical — nothing to do)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
