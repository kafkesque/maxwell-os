#!/usr/bin/env python3
"""dedup_scan.py — Phase B distinct-facet-aware dedup candidate scan (D2621).

Deterministic, LLM-free, READ-ONLY (never mutates the DB). Two candidate signals:

  1. SHA-256 exact-dup: identical normalized (name + definition) — these are
     the same FB extracted from different clusters (true duplicates).
  2. Name-stem collision: name tokens share a stem (Jaccard >= 0.5 after
     stripping stopwords and a trailing " (N)" suffix) — near-duplicates that
     need a MECHANISM-AWARE judge (same definition+mechanism => merge; different
     mechanism => keep, e.g. Visual-Hierarchy-Through-[Contrast/Spacing/...]).

Outputs (dry-run, no DB write):
  - governance/dedup_candidates.jsonl  : one row per candidate GROUP, with every
    member's {fb_id, name, definition, mechanism, application} for the judge.
  - governance/dedup_candidates_summary.json : counts + the confirmed-dup groups.

D2621 rule: embedding cosine OVER-MERGES distinct facets. This scan does NOT use
embeddings for the merge decision — it only surfaces name/stem collisions for the
mechanism-aware reliable-pair judge (the next stage).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB = ROOT / "knowledge pipeline" / "maxwell.db"
OUT_CAND = ROOT / "governance" / "dedup_candidates.jsonl"
OUT_SUM = ROOT / "governance" / "dedup_candidates_summary.json"

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "of", "in", "for", "to", "with", "by", "on", "as",
    "or", "from", "through", "vs", "into", "using", "via", "at", "is", "are",
})
_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")

# Known confirmed-duplicate stems (user-confirmed, D2621): these are the groups
# the judge must resolve; listed for the summary report only (not auto-merged).
CONFIRMED_STEMS = frozenset({
    "squash and stretch",
    "responsible ai",
    "responsible artificial intelligence",
    "foot-in-the-door",
    "foot in the door",
    "iterative refinement",
})


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = _SUFFIX_RE.sub("", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _name_tokens(name: str) -> frozenset:
    return frozenset(t for t in _norm(name).split() if t and t not in _STOPWORDS)


def _first_sig_token(name: str) -> str:
    """First significant (non-stopword) token in original name order — the stem."""
    toks = [t for t in _norm(name).split() if t and t not in _STOPWORDS]
    return toks[0] if toks else ""


def _sha256_key(name: str, definition: str) -> str:
    return hashlib.sha256(f"{_norm(name)}|{_norm(definition)}".encode("utf-8")).hexdigest()


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _load_principle_rows() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT fb_id, name, definition, mechanism, application, status, is_convergent "
            "FROM fbs WHERE content_type='principle' AND definition IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def scan() -> None:
    rows = _load_principle_rows()
    print(f"principle rows scanned: {len(rows)}")

    # 1. exact SHA-256 dupes
    by_sha: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_sha[_sha256_key(r["name"], r["definition"])].append(r)
    exact_groups = [g for g in by_sha.values() if len(g) > 1]
    print(f"exact-duplicate groups (same normalized name+definition): {len(exact_groups)}")

    # 2. name-stem collision (Jaccard >= 0.5 on name tokens) via inverted index
    #    (bucket by first significant token, then compare Jaccard within buckets).
    name_tokens = {r["fb_id"]: _name_tokens(r["name"]) for r in rows}
    by_first: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        key = _first_sig_token(r["name"])
        if not key:
            continue
        # bucket on first significant token (captures "squash and stretch",
        # "responsible ai", "foot in the door", "iterative refinement" stems)
        by_first[key].append(r)
    seen: set = set()
    stem_groups: List[List[Dict[str, Any]]] = []
    for bucket in by_first.values():
        for i, r in enumerate(bucket):
            if r["fb_id"] in seen:
                continue
            group = [r]
            for j in range(i + 1, len(bucket)):
                other = bucket[j]
                if other["fb_id"] in seen:
                    continue
                if _jaccard(name_tokens[r["fb_id"]], name_tokens[other["fb_id"]]) >= 0.5:
                    group.append(other)
            if len(group) > 1:
                for m in group:
                    seen.add(m["fb_id"])
                stem_groups.append(group)

    # merge exact + stem groups (dedup by fb_id)
    all_groups: List[List[Dict[str, Any]]] = list(exact_groups)
    seen_ids = {m["fb_id"] for g in exact_groups for m in g}
    for g in stem_groups:
        fresh = [m for m in g if m["fb_id"] not in seen_ids]
        if len(fresh) > 1:
            all_groups.append(fresh)
            seen_ids.update(m["fb_id"] for m in fresh)

    print(f"name-stem collision groups: {len(stem_groups)}")
    print(f"total candidate groups (exact + stem, deduped): {len(all_groups)}")

    # report confirmed stems
    confirmed = []
    for g in all_groups:
        stems = {_norm(m["name"]) for m in g}
        if any(cs in s or s in cs for s in stems for cs in CONFIRMED_STEMS):
            confirmed.append(g)
    print(f"groups matching CONFIRMED_STEMS: {len(confirmed)}")
    for g in confirmed:
        for m in g:
            print(f"    {m['name'][:50]:52} conv={m['is_convergent']} status={m['status']}")

    # write candidates (dry-run)
    cand_rows = []
    for g in all_groups:
        cand_rows.append({
            "group_id": g[0]["fb_id"][:16],
            "n_members": len(g),
            "members": [
                {
                    "fb_id": m["fb_id"],
                    "name": m["name"],
                    "definition": m["definition"],
                    "mechanism": m["mechanism"],
                    "application": m["application"],
                    "status": m["status"],
                    "is_convergent": m["is_convergent"],
                }
                for m in g
            ],
        })

    OUT_CAND.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in cand_rows))
    OUT_SUM.write_text(json.dumps({
        "principle_rows": len(rows),
        "exact_dup_groups": len(exact_groups),
        "stem_collision_groups": len(stem_groups),
        "total_candidate_groups": len(all_groups),
        "confirmed_stem_groups": len(confirmed),
        "confirmed_stems": sorted(CONFIRMED_STEMS),
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"\nwrote {OUT_CAND} ({len(cand_rows)} groups)")
    print(f"wrote {OUT_SUM}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Phase B distinct-facet-aware dedup candidate scan (read-only).")
    ap.add_argument("--limit", type=int, default=0, help="limit rows scanned (debug)")
    args = ap.parse_args()
    scan()
