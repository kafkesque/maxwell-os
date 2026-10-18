#!/usr/bin/env python3
"""apply_identity_collapse.py — T-129: collapse duplicate works at the IDENTITY layer (never delete).

WHY. BUG-780/T-119 measured 84 collapsing work-pairs (37 identical normalised text) certifying 530 of
the 1,393 `is_convergent=1` rows as corroborated by ONE TEXT under TWO NAMES. The owner ruled 68
CONFIRM-ONE-WORK / 16 DISTINCT (governance/work_identity_collapse_review_20261014.csv#owner_ruling).
This script applies the CONFIRM-ONE-WORK ruling deterministically: for each duplicate-work group it
re-points the non-canonical source_id to the group's canonical source_id, then re-derives
`source_diversity` and `is_convergent` from the collapsed evidence set. A row that cited two aliases of
one work drops to one source and loses the corroboration it never had. Rows are NEVER deleted (R-D410);
`source_books` (raw provenance) is untouched — only the canonical identity (`source_ids`) collapses.

CHECKED, NOT ASSERTED: scripts/check_corroboration_bit.py re-proves the whole population against its
own evidence set after the write (D-2993/BUG-775), so the repair is verified by the parity rail.

Reads every path/value from its declared home (C12): the review sheet and canonical preference from
config/corroboration_collapse.yaml, the ruling word from config/owner_marks.yaml, and the DB path +
min_source_diversity from pipeline.pipeline_paths.

Usage:
    python3 scripts/apply_identity_collapse.py              # dry-run: report exact flips, write nothing
    python3 scripts/apply_identity_collapse.py --apply      # C13 backup + integrity gate + atomic write
    python3 scripts/apply_identity_collapse.py --selftest   # known-answer controls (pure core, no store)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from pipeline.book_metadata import resolve_book_metadata, resolve_source_id  # noqa: E402
from pipeline.pipeline_paths import DB_PATH, S15_MIN_SOURCE_DIVERSITY  # noqa: E402

CONFIG_REL = "config/corroboration_collapse.yaml"
OWNER_MARKS_REL = "config/owner_marks.yaml"


def _load_yaml(rel: str) -> Dict[str, Any]:
    doc = yaml.safe_load((REPO / rel).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{rel} is not a mapping")
    return doc


def _resolve_pointer(rel: str, dotted: str) -> Any:
    node: Any = _load_yaml(rel)
    for step in dotted.split("."):
        node = node[step]
    return node


def review_sheet_path() -> Path:
    rule = _load_yaml(CONFIG_REL)
    rel = str(rule["lexical_limb"]["measured"]["review_sheet"])
    return REPO / rel


def ruling_word() -> str:
    words = _resolve_pointer(*str(_load_yaml(CONFIG_REL)["identity_collapse"]["ruling_word_from"]).split("#"))
    idx = int(_load_yaml(CONFIG_REL)["identity_collapse"]["ruling_word_index"])
    return str(words[idx])


def canonical_preference() -> List[str]:
    return [str(p) for p in _load_yaml(CONFIG_REL)["identity_collapse"]["canonical_preference"]]


def _normalised_len(w: str) -> int:
    return len(re.sub(r"[^a-z0-9]", "", w.lower()))


def is_real_metadata(work: str) -> bool:
    m = resolve_book_metadata(work)
    return (m.get("author", "") not in ("", "Unknown Author")) and (m.get("title", "") not in ("", "Unknown Title"))


def _pref_key(work: str, rows_affected: Dict[str, int]) -> tuple:
    key: tuple = ()
    for p in canonical_preference():
        if p == "real_metadata":
            key += (not is_real_metadata(work),)  # False sorts first -> real metadata preferred
        elif p == "rows_affected_desc":
            key += (-int(rows_affected.get(work, 0)),)
        elif p == "shortest_normalised_name":
            key += (_normalised_len(work),)
        elif p == "lexicographic":
            key += (work.lower(),)
        else:
            raise ValueError(f"unknown canonical_preference token {p!r} (declared, never guessed)")
    return key


def build_identity_map(pairs: Sequence[Dict[str, str]]) -> Dict[str, str]:
    """Union-find the CONFIRM-ONE-WORK pairs into duplicate-work groups, select a canonical per group,
    and return {dup_source_id: canonical_source_id}. Pure — no store access."""
    parent: Dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for r in pairs:
        union(r["work_a"], r["work_b"])

    groups: Dict[str, Set[str]] = {}
    for w in list(parent):
        groups.setdefault(find(w), set()).add(w)

    rows_affected: Dict[str, int] = {}
    for r in pairs:
        rows_affected[r["work_a"]] = rows_affected.get(r["work_a"], 0) + int(r["rows_affected"] or 0)
        rows_affected[r["work_b"]] = rows_affected.get(r["work_b"], 0) + int(r["rows_affected"] or 0)

    cmap: Dict[str, str] = {}
    for members in groups.values():
        canon = min(members, key=lambda w: _pref_key(w, rows_affected))
        csid = resolve_source_id(canon)
        for w in members:
            if w != canon:
                cmap[resolve_source_id(w)] = csid
    return cmap


def load_pairs() -> List[Dict[str, str]]:
    word = ruling_word()
    out: List[Dict[str, str]] = []
    with review_sheet_path().open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("owner_ruling") == word:
                out.append(r)
    if not out:
        raise ValueError(f"no rows carry the collapse ruling {word!r} — the owner word is absent (C16)")
    return out


def scan(cmap: Dict[str, str], min_sources: int) -> Dict[str, dict]:
    """Remap source_ids through cmap and recompute source_diversity/is_convergent, read-only."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT fb_id, source_ids, source_diversity, is_convergent FROM fbs").fetchall()
    finally:
        conn.close()
    changes: Dict[str, dict] = {}
    for r in rows:
        try:
            ids = list(json.loads(r["source_ids"])) if r["source_ids"] else []
        except (ValueError, TypeError):
            ids = []
        new: Set[str] = set()
        changed = False
        for s in ids:
            m = cmap.get(s, s)
            if m != s:
                changed = True
            new.add(m)
        if not changed:
            continue
        nd = len(new)
        changes[r["fb_id"]] = {
            "source_ids": json.dumps(sorted(new)),
            "source_diversity": nd,
            "is_convergent": int(nd >= min_sources),
            # old values, so the reporter can state the TRUE transition, not just the new value
            "old_source_diversity": int(r["source_diversity"] or 0),
            "old_is_convergent": int(r["is_convergent"] or 0),
        }
    return changes


def run(apply: bool) -> int:
    cmap = build_identity_map(load_pairs())
    print(f"identity map: {len(cmap)} duplicate source_id(s) -> {len(set(cmap.values()))} canonical work(s)")
    min_sources = int(S15_MIN_SOURCE_DIVERSITY)
    changes = scan(cmap, min_sources)
    flip = sum(1 for v in changes.values() if v["old_is_convergent"] == 1 and v["is_convergent"] == 0)
    repoint_only = len(changes) - flip
    print(f"rows to update: {len(changes)} | is_convergent 1->0: {flip} "
          f"| repointed-not-flipped: {repoint_only} | deleted: 0 (R-D410)")
    if not apply:
        print("[dry-run] nothing written. Re-run with --apply (C13 backup + integrity gate).")
        return 0
    if not changes:
        print("nothing to apply.")
        return 0
    bak = DB_PATH.with_name(f"maxwell.db.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_pre_identity")
    shutil.copy2(DB_PATH, bak)
    print(f"[C13] backup: {bak}")
    conn = sqlite3.connect(DB_PATH)
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        if qc != "ok":
            raise RuntimeError(f"PRAGMA quick_check failed: {qc!r}")
        for fb_id, v in changes.items():
            conn.execute(
                "UPDATE fbs SET source_ids=?, source_diversity=?, is_convergent=? WHERE fb_id=?",
                (v["source_ids"], v["source_diversity"], v["is_convergent"], fb_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print(f"[done] updated {len(changes)} rows (never deleted). Re-prove with scripts/check_corroboration_bit.py")
    return 0


def selftest() -> int:
    # Known-answer: same group collapses, distinct group does not, real-metadata wins canonical.
    ok = True
    m = build_identity_map([{"work_a": "About Face The Essentials of Interaction Design (Alan Cooper).md",
                             "work_b": "About_Face_The_Essentials_of_Interaction_Design.md",
                             "rows_affected": "5"}])
    sa, sb = resolve_source_id("About Face The Essentials of Interaction Design (Alan Cooper).md"), \
        resolve_source_id("About_Face_The_Essentials_of_Interaction_Design.md")
    if sa == sb or m.get(sb) != sa:
        ok = False
    print(("ok" if ok else "FAIL"), "apply_identity_collapse --selftest")
    return 0 if ok else 1


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="write (C13 backup + integrity gate)")
    p.add_argument("--selftest", action="store_true", help="pure known-answer controls, no store")
    args = p.parse_args(argv)
    if args.selftest:
        return selftest()
    return run(apply=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
