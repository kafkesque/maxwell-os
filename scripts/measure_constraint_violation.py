#!/usr/bin/env python3
"""Measure the facet constraint-violation rate (D273a / G12).

For every discipline facet with >= min_rows PASS rows, issue `probes` probe
queries drawn from that discipline's OWN PASS FBs through search_hybrid with the
discipline facet set, and count how many of the top-N FUSED results carry a
DIFFERENT discipline. This is the "does the filter actually filter" measurement:
a facet-bearing query should return only rows that match the facet.

Baseline (before 0b): expected NON-ZERO — the FTS/vector legs receive no facet
and the query-blind keyword leg is the only facet-bearing leg.
Target (after 0b / G12): exactly 0 violations.

Usage:
    python3 scripts/measure_constraint_violation.py                       # full baseline
    python3 scripts/measure_constraint_violation.py --max-disciplines 5    # smoke run
    python3 scripts/measure_constraint_violation.py --min-rows 10 --probes 10 --top 10
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.retrieve import get_conn, search_hybrid  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Facet constraint-violation measurement (D273a/G12)")
    ap.add_argument("--min-rows", type=int, default=10, help="min PASS rows for a discipline to be measured")
    ap.add_argument("--probes", type=int, default=10, help="probe queries per discipline (drawn from its own FBs)")
    ap.add_argument("--top", type=int, default=10, help="top-N fused results to inspect")
    ap.add_argument("--max-disciplines", type=int, default=0, help="cap disciplines (0=all) for smoke runs")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for probe sampling")
    args = ap.parse_args(argv)

    conn = get_conn()
    disciplines = [
        r["discipline"]
        for r in conn.execute(
            "SELECT discipline FROM fbs WHERE status='PASS' "
            "GROUP BY discipline HAVING COUNT(*) >= ? ORDER BY discipline",
            (args.min_rows,),
        ).fetchall()
    ]
    if args.max_disciplines:
        disciplines = disciplines[: args.max_disciplines]
    print(f"measuring {len(disciplines)} disciplines (>= {args.min_rows} PASS rows each)")

    rng = random.Random(args.seed)
    per_discipline: dict[str, dict] = {}
    total_probes = 0
    total_violations = 0
    violator_disciplines: Counter = Counter()

    for d in disciplines:
        probes = [
            dict(r)
            for r in conn.execute(
                "SELECT fb_id, name, definition FROM fbs "
                "WHERE status='PASS' AND discipline = ? ORDER BY fb_id",
                (d,),
            ).fetchall()
        ]
        if len(probes) > args.probes:
            probes = rng.sample(probes, args.probes)

        n_probes = 0
        n_violations = 0
        for p in probes:
            query = (p.get("name") or "").strip() or (p.get("definition") or "").strip()[:80]
            if not query:
                continue
            results = search_hybrid(conn, query, discipline=d, limit=args.top, rerank=False)
            n_probes += 1
            for r in results:
                if (r.get("discipline") or "") != d:
                    n_violations += 1
                    violator_disciplines[(r.get("discipline") or "<none>")] += 1
        total_probes += n_probes
        total_violations += n_violations
        rate = n_violations / (n_probes * args.top) if n_probes else 0.0
        per_discipline[d] = {"probes": n_probes, "violations": n_violations, "rate": rate}

    conn.close()

    print(f"\n{'discipline':32} {'probes':>6} {'violations':>10} {'rate':>8}")
    for d in sorted(per_discipline, key=lambda k: -per_discipline[k]["rate"]):
        pd = per_discipline[d]
        flag = "  ⚠️" if pd["violations"] else ""
        print(f"{d:32} {pd['probes']:>6} {pd['violations']:>10} {pd['rate']:>8.3f}{flag}")

    denom = total_probes * args.top
    overall = total_violations / denom if denom else 0.0
    print(f"\n{'TOTAL':32} {total_probes:>6} {total_violations:>10} {overall:>8.3f}")
    print(f"constraint-violation rate: {overall:.4f}  (target after 0b: 0.0000)")
    if violator_disciplines:
        print("\nnon-matching disciplines that leaked into faceted results:")
        for disc, cnt in violator_disciplines.most_common(15):
            print(f"   {disc}: {cnt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
