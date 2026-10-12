#!/usr/bin/env python3
"""scripts/audit_duplicate_identity.py — READ-ONLY duplicate/collision landscape audit (D-2950).

Root cause (D-2949): fb_id = SHA256(name + definition) is definition-sensitive, so two
chunks of the same source describing the same concept with slightly different
definitions produce different fb_ids and both survive commit. The canonical SOURCE
identity (source_ids = SHA-256 author|title, D2176/D2376) ALREADY collapses editions
(D2308) — but is wired for diversity COUNTING, not as a commit dedup key.

Classification (see pipeline/dedup_identity.py, D-2950):
  MERGE               same name + ONE source + CONVERGENT body  -> merge (keep richer)
  SAME_SOURCE_COLLIDE same name + ONE source + DIVERGENT body   -> KEEP BOTH (distinct
                      concepts that share a name inside one book — disambiguate names)
  NAME_COLLIDE        same name + >1 source identity            -> KEEP BOTH (distinct works)
  NO_SOURCE           duplicate name, missing source_ids        -> owner review

READ-ONLY. No mutation. Pre-audit for the D-2950 dedup-identity design.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.dedup_identity import classify_group, normalize_name  # noqa: E402

DEFAULT_DB = Path("knowledge pipeline/maxwell.db")


def _parse_source_ids(raw: str) -> frozenset[str]:
    if not raw:
        return frozenset()
    try:
        val = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return frozenset()
    if isinstance(val, list):
        return frozenset(str(s) for s in val if s)
    return frozenset()


def audit(db_path: Path) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT fb_id, name, content_type, discipline, definition, mechanism, source_ids "
            "FROM fbs WHERE name IS NOT NULL AND name != ''"
        ).fetchall()
    finally:
        conn.close()

    by_name: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        nk = normalize_name(r["name"])
        if not nk:
            continue
        by_name[nk].append(
            {
                "fb_id": r["fb_id"],
                "name": r["name"],
                "content_type": r["content_type"],
                "definition": (r["definition"] or "")[:160],
                "mechanism": (r["mechanism"] or "")[:160],
                "source_ids": _parse_source_ids(r["source_ids"]),
            }
        )

    merge: list[list[dict]] = []
    same_source_collide: list[list[dict]] = []
    name_collide: list[list[dict]] = []
    no_source: list[list[dict]] = []
    for _nk, members in by_name.items():
        if len(members) < 2:
            continue
        kind = classify_group(members)
        if kind == "merge":
            merge.append(members)
        elif kind == "same_source_collide":
            same_source_collide.append(members)
        elif kind == "no_source":
            no_source.append(members)
        else:
            name_collide.append(members)

    return {
        "total_rows": len(rows),
        "distinct_names": len(by_name),
        "merge": merge,
        "same_source_collide": same_source_collide,
        "name_collide": name_collide,
        "no_source": no_source,
    }


def _report(res: dict) -> None:
    print(f"rows={res['total_rows']}  distinct normalized names={res['distinct_names']}")
    print("=" * 78)
    print(f"MERGE (same name + one source + CONVERGENT body -> merge keep richer): {len(res['merge'])}")
    for m in sorted(res["merge"], key=lambda x: -len(x)):
        print(f"\n  [{len(m)} rows] name={m[0]['name']!r} source={sorted(m[0]['source_ids'])}")
        for x in m:
            print(f"    - {x['fb_id'][:14]} ct={x['content_type']:18} def={x['definition']!r}")
    print("\n" + "=" * 78)
    print(f"SAME_SOURCE_COLLIDE (same name+source, DIVERGENT body -> KEEP BOTH): {len(res['same_source_collide'])}")
    for m in sorted(res["same_source_collide"], key=lambda x: x[0]["name"]):
        print(f"\n  [{len(m)} rows] name={m[0]['name']!r} source={sorted(m[0]['source_ids'])}")
        for x in m:
            print(f"    - {x['fb_id'][:14]} ct={x['content_type']:18} def={x['definition']!r}")
    print("\n" + "=" * 78)
    print(f"NAME_COLLIDE (same name + >1 source -> KEEP BOTH): {len(res['name_collide'])}")
    for m in sorted(res["name_collide"], key=lambda x: x[0]["name"]):
        print(f"\n  [{len(m)} rows] name={m[0]['name']!r}")
        for x in m:
            print(f"    - {x['fb_id'][:14]} ct={x['content_type']:18} src={sorted(x['source_ids'])} def={x['definition']!r}")
    print("\n" + "=" * 78)
    print(f"NO_SOURCE (dup name, missing source_ids): {len(res['no_source'])}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    res = audit(Path(ap.parse_args().db))
    _report(res)


if __name__ == "__main__":
    main()
