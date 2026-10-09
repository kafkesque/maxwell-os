#!/usr/bin/env python3
"""scripts/offmenu_stratify.py — BUG-693 step 3: deterministic offmenu stratification.

Partitions the canonical-run `discipline='emerging'` offmenu population (the 1309
rows whose `discipline_raw` is a real label that has no verbatim closed-menu home)
into three strata via the SAME fail-closed `match_to_canonical` synonym index the
pipeline already uses. This is READ-ONLY analysis: it emits a report + JSON and
performs NO mutation. The owner signs the re-map table before any --apply step.

Strata (STier ontological decomposition):
  A  alias-merge     discipline_raw resolves to an EXISTING canonical discipline
                     via the curated synonym index (same-axis). The decider's
                     definition-anchored closed menu (D-2814) rejects non-verbatim
                     aliases, so these are wrongly dumped to 'emerging' even though
                     a canonical home already exists. Deterministic reclaim.
  B  cross-axis      discipline_raw resolves ONLY to a canonical DOMAIN (not a
                     discipline). Ontologically ambiguous: promote-as-discipline,
                     kind-swap-to-domain (BUG-150 machinery), or leave. Owner rules.
  C  homeless        no canonical home on either axis. Split by mission scope:
                     in-scope-coherent (promote) vs out-of-scope (whitelist-emerging)
                     vs ambiguous (leave). Owner rules.

D-2896 alignment: raw labels are NEVER rewritten here — only the CANONICAL field
would be set on a downstream --apply (discipline_raw stays verbatim provenance).

Run:
    python3 scripts/offmenu_stratify.py                 # stratify canonical run
    python3 scripts/offmenu_stratify.py --min-count 2   # lower the head/tail split
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.schemas import match_to_canonical  # noqa: E402

CANONICAL_RUN_ID = "rechunk-v4-20260929"  # owner-ruled canonical run (D-2891); t11 NEVER included
_DB_PATH = _ROOT / "knowledge pipeline" / "maxwell.db"
_OUT = _ROOT / "temp" / "offmenu_stratify.json"
_MIN_COUNT = 3  # C20: labels below this frequency are the long tail (leave/whitelist)


def _to_list(v: str | None) -> list[str]:
    """Parse a discipline_raw cell (JSON array, bare string, or empty) into labels."""
    if not v:
        return []
    if isinstance(v, str):
        try:
            x = json.loads(v)
            return [str(i).strip().lower() for i in x] if isinstance(x, list) else [v.strip().lower()]
        except (json.JSONDecodeError, TypeError):
            return [v.strip().lower()]
    return [str(i).strip().lower() for i in v]


def _emerging_raw_counts(db_path: Path, run_id: str) -> Counter[str]:
    """Return {discipline_raw: count} for the canonical run's emerging rows (non-empty raw only)."""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT discipline_raw FROM fbs WHERE pipeline_run_id = ? AND discipline = 'emerging'",
            (run_id,),
        ).fetchall()
    finally:
        conn.close()
    counts: Counter[str] = Counter()
    for (raw,) in rows:
        for label in _to_list(raw):
            if label:
                counts[label] += 1
    return counts


def stratify(counts: Counter[str]) -> dict[str, list[dict]]:
    """Partition raw labels into strata A/B/C via the fail-closed synonym index."""
    strata: dict[str, list[dict]] = {"A_alias_merge": [], "B_cross_axis": [], "C_homeless": [],
                                     "homonym": []}
    for label, n in counts.most_common():
        d = match_to_canonical(label, "discipline")
        m = match_to_canonical(label, "domain")
        row = {"label": label, "count": n, "discipline_home": d, "domain_home": m}
        if d and m:
            strata["homonym"].append(row)
        elif d:
            strata["A_alias_merge"].append(row)
        elif m:
            strata["B_cross_axis"].append(row)
        else:
            strata["C_homeless"].append(row)
    return strata


def _rows_and_count(entries: list[dict]) -> tuple[int, int]:
    return len(entries), sum(e["count"] for e in entries)


def _fmt(label: str, n: int, target: str | None, axis: str) -> str:
    return f"  {n:4d}  {label!r} -> {axis} {target!r}"


def _render(strata: dict[str, list[dict]], min_count: int) -> str:
    lines: list[str] = []
    a_l, a_r = _rows_and_count(strata["A_alias_merge"])
    b_l, b_r = _rows_and_count(strata["B_cross_axis"])
    c_l, c_r = _rows_and_count(strata["C_homeless"])
    h_l, h_r = _rows_and_count(strata["homonym"])
    lines.append(f"A alias-merge  : {a_l} labels / {a_r} rows  (deterministic same-axis reclaim)")
    lines.append(f"B cross-axis   : {b_l} labels / {b_r} rows  (owner rules: promote/kind-swap/leave)")
    lines.append(f"C homeless     : {c_l} labels / {c_r} rows  (owner rules: in-scope/out-of-scope/leave)")
    if h_l:
        lines.append(f"homonym (A∩B)  : {h_l} labels / {h_r} rows  (matches BOTH axes — needs ruling)")
    lines.append("")
    lines.append("=== A: deterministic alias-merge (discipline_raw -> existing canonical discipline) ===")
    for e in strata["A_alias_merge"]:
        lines.append(_fmt(e["label"], e["count"], e["discipline_home"], "discipline"))
    lines.append("")
    lines.append("=== B: cross-axis (discipline_raw -> canonical DOMAIN only) ===")
    for e in strata["B_cross_axis"]:
        lines.append(_fmt(e["label"], e["count"], e["domain_home"], "domain"))
    lines.append("")
    lines.append("=== C: homeless (no canonical home) — head (count >= {}) ===".format(min_count))
    head = [e for e in strata["C_homeless"] if e["count"] >= min_count]
    for e in head:
        lines.append(f"  {e['count']:4d}  {e['label']!r}")
    tail = [e for e in strata["C_homeless"] if e["count"] < min_count]
    lines.append(f"  ... + {len(tail)} tail labels (< {min_count}) / {sum(e['count'] for e in tail)} rows")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-count", type=int, default=_MIN_COUNT,
                    help=f"head/tail split threshold (default {_MIN_COUNT})")
    args = ap.parse_args()

    counts = _emerging_raw_counts(_DB_PATH, CANONICAL_RUN_ID)
    strata = stratify(counts)
    print(f"offmenu population (canonical run {CANONICAL_RUN_ID}): "
          f"{sum(counts.values())} rows / {len(counts)} distinct raw labels")
    print()
    print(_render(strata, args.min_count))

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(_OUT, "w", encoding="utf-8") as f:
        json.dump({"run_id": CANONICAL_RUN_ID, "strata": strata,
                   "totals": {k: _rows_and_count(v) for k, v in strata.items()}},
                  f, indent=2, ensure_ascii=False)
    print(f"\n✅ JSON -> {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
