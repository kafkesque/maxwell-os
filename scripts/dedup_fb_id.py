#!/usr/bin/env python3
"""dedup_fb_id.py — post-S4 fb_id collision dedup (BUG-150 recurrence guard).

S4's D2069 name-collision disambiguation renames near-duplicate FBs with a
" (N)" suffix but PRESERVES the S2 fb_id (D2350 "never re-hash"). When two FBs
from DIFFERENT clusters share an identical (name, definition), they collide on
fb_id — and S6's `INSERT OR REPLACE INTO fbs` (fb_id TEXT PRIMARY KEY) silently
overwrites the earlier row (data loss). Verified live: 4 collision groups / 9
records / 5 rows silently lost.

This script runs AFTER S4 completes, BEFORE remap/gate/S5/S6. It:
  1. Groups FBs by fb_id.
  2. For each collision group, VERIFIES the members are true duplicates
     (identical definition; names differing only by a trailing " (N)" suffix).
     A group that fails this check is a genuine hash collision → fail-closed.
  3. Merges each verified group into ONE convergent FB: unions provenance
     (source_clusters/source_ids/source_segments/source_books/source_authors/
     evidence_passages/evidence_passages_shown), strips the " (N)" suffix,
     sets is_convergent=True, origin="convergent".
  4. Writes the deduped checkpoint via safe_write_jsonl (crash-safe).

Invariants: fb_id is never re-hashed (D2350); *_raw fields are untouched.

Usage:
    python3 scripts/dedup_fb_id.py [--input PATH] [--output PATH] [--dry-run]
Exit codes:
    0  success (no collisions, or all collisions safely merged)
    1  genuine hash collision (ambiguous — refused to write)
    2  input checkpoint missing/unreadable
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write_jsonl
from pipeline.pipeline_paths import STAGE4_CHECKPOINT

DEDUPED_CHECKPOINT = STAGE4_CHECKPOINT.parent / "checkpoint_deduped.jsonl"
_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")


def _dedup(items: list) -> list:
    """Order-preserving dedup (list `in` uses ==, so works for str and dict)."""
    out: list = []
    for x in items:
        if x not in out:
            out.append(x)
    return out


def merge_group(group: list[dict]) -> tuple[dict | None, str | None]:
    """Merge a verified duplicate group into one convergent FB. Returns (fb, err)."""
    # 1) Verify definitions identical
    defs = {g.get("definition", "") for g in group}
    if len(defs) > 1:
        return None, f"definitions differ across {len(group)} records"

    # 2) Verify names identical modulo a trailing " (N)" suffix
    base_names = {_SUFFIX_RE.sub("", g.get("name", "")) for g in group}
    if len(base_names) > 1:
        return None, f"base names differ: {sorted(base_names)}"

    base = dict(group[0])
    base["name"] = _SUFFIX_RE.sub("", base.get("name", ""))

    # 3) Union provenance (order-preserving, deduped)
    for key in ("source_clusters", "source_ids", "source_principle_ids",
                "source_segments", "source_books", "evidence_passages",
                "evidence_passages_shown"):
        merged: list = []
        for g in group:
            merged.extend(g.get(key) or [])
        base[key] = _dedup(merged)

    authors: list = []
    for g in group:
        authors.extend(g.get("source_authors") or [])
    base["source_authors"] = _dedup(authors)

    texts: list = []
    for g in group:
        t = g.get("source_text")
        if t and t not in texts:
            texts.append(t)
    base["source_text"] = "\n\n".join(texts)

    divs = [g.get("source_diversity") for g in group]
    if divs and isinstance(divs[0], (int, float)):
        base["source_diversity"] = max(d for d in divs if d is not None)

    # 4) Mark as convergent (multi-source)
    base["is_convergent"] = True
    base["origin"] = "convergent"
    return base, None


def main() -> int:
    ap = argparse.ArgumentParser(description="post-S4 fb_id collision dedup (BUG-150)")
    ap.add_argument("--input", type=Path, default=STAGE4_CHECKPOINT)
    ap.add_argument("--output", type=Path, default=DEDUPED_CHECKPOINT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"❌ input checkpoint not found: {args.input}", file=sys.stderr)
        return 2

    fbs = load_jsonl(args.input, context="S4 checkpoint (dedup)")
    groups: dict[str, list[dict]] = defaultdict(list)
    for fb in fbs:
        groups[fb.get("fb_id")].append(fb)

    collisions = {k: v for k, v in groups.items() if len(v) > 1}
    print("=" * 60)
    print("🧹 fb_id COLLISION DEDUP")
    print(f"   total FBs: {len(fbs)}")
    print(f"   collision groups: {len(collisions)}")
    for fb_id, grp in collisions.items():
        print(f"   - {fb_id[:16]}… ({len(grp)} records): {[g['name'] for g in grp]}")
    print("=" * 60)

    seen: set = set()
    output: list[dict] = []
    ambiguous = 0
    merged_count = 0
    for fb in fbs:
        fid = fb.get("fb_id")
        if fid in seen:
            continue
        seen.add(fid)
        g = groups[fid]
        if len(g) > 1:
            merged, err = merge_group(g)
            if err:
                print(f"🛑 AMBIGUOUS collision {fid[:16]}…: {err}", file=sys.stderr)
                ambiguous += 1
                continue
            output.append(merged)
            merged_count += 1
        else:
            output.append(fb)

    out_ids = [fb.get("fb_id") for fb in output]
    if len(out_ids) != len(set(out_ids)):
        print("🛑 post-merge fb_id collision remains — aborting.", file=sys.stderr)
        return 1

    print(f"   merged {merged_count} groups → {len(output)} FBs (was {len(fbs)})")

    if ambiguous:
        print("🛑 Refusing to write: ambiguous collision(s) require manual review.", file=sys.stderr)
        return 1

    if not args.dry_run:
        safe_write_jsonl(args.output, output)
        print(f"✅ wrote {args.output}")
    else:
        print("(dry-run — nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
