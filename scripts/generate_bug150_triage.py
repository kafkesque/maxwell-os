#!/usr/bin/env python3
"""D2534: Generate the BUG-150 triage table for the 822 distinct raw discipline labels.

READ-ONLY. Buckets every distinct `discipline_raw` on `discipline='emerging'` FBs
into a deterministic taxonomy using `match_to_canonical` (both axes):

  ① ALIAS-AVAILABLE  — raw label already maps to a DISCIPLINE canonical via the
                        synonym index (mapping exists; only the DB row is stale).
                        Deterministic reclassify, no LLM, no taxonomy edit.
  ② DOMAIN-SKIP      — raw label maps to a DOMAIN canonical (cross-axis leak),
                        or IS a domain canonical. Do NOT promote as discipline.
  ③ TRUE-GAP         — maps to NEITHER axis. Genuinely missing label; needs a
                        human decision: swap-promote (demote a low-count canonical)
                        vs keep-unique vs keep-emerging (method/topic/grab-bag).

Outputs `governance/bug150_triage.md` (human-review artifact) + a stdout summary.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import match_to_canonical  # noqa: E402

OUT_PATH = _PROJECT_ROOT / "governance" / "bug150_triage.md"


def _load_labels(db_path: Path) -> list[tuple[str, int]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT discipline_raw, COUNT(*) c FROM fbs "
            "WHERE discipline='emerging' AND discipline_raw IS NOT NULL AND TRIM(discipline_raw)<>'' "
            "GROUP BY discipline_raw ORDER BY c DESC, discipline_raw"
        ).fetchall()
        return [(r["discipline_raw"], r["c"]) for r in rows]
    finally:
        conn.close()


def _bucket(label: str) -> tuple[str, str]:
    disc = match_to_canonical(label, "discipline")
    dom = match_to_canonical(label, "domain")
    if disc:
        return "ALIAS-AVAILABLE", disc
    if dom:
        return "DOMAIN-SKIP", dom
    return "TRUE-GAP", ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    labels = _load_labels(Path(DB_PATH))
    bucketed: list[tuple[str, int, str, str]] = []
    for label, cnt in labels:
        bucket, target = _bucket(label)
        bucketed.append((label, cnt, bucket, target))

    counts = Counter(b[2] for b in bucketed)
    fb_coverage = Counter()
    for _, cnt, bucket, _ in bucketed:
        fb_coverage[bucket] += cnt

    print(f"📊 {len(labels)} distinct raw labels on {sum(c for _, c in labels)} emerging FBs")
    for b in ["ALIAS-AVAILABLE", "DOMAIN-SKIP", "TRUE-GAP"]:
        print(f"    {b:16} labels={counts.get(b,0):4}  FBs={fb_coverage.get(b,0):5}")

    # Build markdown artifact
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = []
    lines.append(f"# BUG-150 Triage Table — {len(labels)} raw discipline labels")
    lines.append("")
    lines.append(f"Generated: {now} · DB: `{DB_PATH}` · read-only (no mutation)")
    lines.append("")
    lines.append("| Bucket | Labels | FBs | Meaning |")
    lines.append("|---|---|---|---|")
    for b in ["ALIAS-AVAILABLE", "DOMAIN-SKIP", "TRUE-GAP"]:
        lines.append(f"| {b} | {counts.get(b,0)} | {fb_coverage.get(b,0)} | " + {
            "ALIAS-AVAILABLE": "mapping exists → deterministic reclassify (no LLM)",
            "DOMAIN-SKIP": "cross-axis (label is a domain) → do NOT promote as discipline",
            "TRUE-GAP": "no mapping on either axis → human decision (swap / keep-unique / keep-emerging)",
        }[b] + " |")
    lines.append("")

    def _section(title: str, bucket: str) -> None:
        rows = [(l, c, t) for l, c, b, t in bucketed if b == bucket]
        if not rows:
            return
        lines.append(f"## {title} ({len(rows)})")
        lines.append("")
        lines.append("| raw label | FBs | target |")
        lines.append("|---|---|---|")
        for l, c, t in rows:
            lines.append(f"| `{l}` | {c} | `{t or '—'}` |")
        lines.append("")

    _section("① ALIAS-AVAILABLE — deterministic reclassify (bulk-approvable)", "ALIAS-AVAILABLE")
    _section("② DOMAIN-SKIP — cross-axis, do NOT promote as discipline", "DOMAIN-SKIP")
    _section("③ TRUE-GAP — human decision required", "TRUE-GAP")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"\n✅ wrote {out} ({len(bucketed)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
