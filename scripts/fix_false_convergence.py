#!/usr/bin/env python3
"""fix_false_convergence.py — BUG-232 fix: re-tier same-author echoes.

The convergent bar requires >=2 INDEPENDENT sources. `audit_false_convergence.py`
found 96 golden FBs where `source_diversity >= 2` but there is < 2 distinct
authors (same-author echo / citation echo) — two editions/files of the SAME
work, or two works by the SAME author. Neither provides independent
cross-source corroboration, so these are FALSE convergence.

This script applies the accepted recommendation (senior RAG engineer):
  1. RECOMPUTE `source_diversity` as distinct PRIMARY WORKS (author + normalized
     title dedup), not distinct file hashes.
  2. RE-TIER the echoes: `is_convergent = 0` (they are not independent
     convergence; treat as single-source provenance for downstream mining /
     classifier quality signals).
  3. Record every change in a manifest (auditable, last-wins per fb_id).

Deterministic, LLM-free. Crash-safe (C6) + C13 backup before --apply. Dry-run by
default; nothing mutates without --apply.

Usage:
    python3 scripts/fix_false_convergence.py            # dry-run (report only)
    python3 scripts/fix_false_convergence.py --apply    # C13 backup + UPDATE fbs
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ECHOES = ROOT / "governance" / "false_convergence_echoes.json"
EXPORT = ROOT / "knowledge pipeline" / "parquet" / "fbs_export_20260902_final.jsonl"
DB = ROOT / "knowledge pipeline" / "maxwell.db"
MANIFEST_JSON = ROOT / "governance" / "false_convergence_fix_manifest.json"
MANIFEST_MD = ROOT / "governance" / "false_convergence_fix_manifest.md"

# Noise tokens stripped from titles before primary-work dedup (C20 — named,
# not magic; these are edition/archive markers, not book-title content).
_TITLE_NOISE_RE = re.compile(
    r"\((z-lib\.org|z-library\.sk|1lib\.sk|z-lib\.sk|libgen|anna'?s archive|"
    r"anna.s archive)\)|"
    r"\[.*?\]|"
    r"\(z-lib\)|"
    r"liber3|"
    r"--\s*[0-9a-f]{8,}\s*--|"
    r"revised edition|2nd ed(ition)?|3rd ed(ition)?|"
    r"@\.md$|\.md$",
    re.IGNORECASE,
)


def normalize_title(title: str | None) -> str:
    """Normalize a book title for primary-work dedup (strip edition/archive noise)."""
    if not title:
        return ""
    t = _TITLE_NOISE_RE.sub(" ", title)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def normalize_author(author: str | None) -> str:
    """Normalize an author string (drop casing/whitespace; keep co-author set order)."""
    if not author:
        return ""
    # Co-author trios ("A, B, C") are kept as one normalized string — they are a
    # single corroborating entity, not independent sources.
    parts = [p.strip() for p in author.lower().split(",") if p.strip()]
    return "|".join(sorted(parts))


def distinct_primary_works(source_authors) -> int:
    """Count distinct (normalized author, normalized title) primary works."""
    works: set[tuple[str, str]] = set()
    data = source_authors
    if isinstance(source_authors, str):
        try:
            data = json.loads(source_authors)
        except json.JSONDecodeError:
            return 0
    if not isinstance(data, list):
        return 0
    for entry in data:
        if isinstance(entry, dict):
            a = normalize_author(entry.get("author"))
            t = normalize_title(entry.get("title"))
            if t or a:
                works.add((a, t))
        elif isinstance(entry, str):
            works.add((normalize_author(entry), ""))
    return len(works)


def build_fix_plan() -> list[dict]:
    """Load the 96 echoes + their export metadata → ordered fix plan."""
    echoes = json.loads(ECHOES.read_text(encoding="utf-8"))["echoes"]
    export_by_id: dict[str, dict] = {}
    with EXPORT.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            export_by_id[o["fb_id"]] = o

    plan: list[dict] = []
    for e in echoes:
        fb_id = e["fb_id"]
        rec = export_by_id.get(fb_id, {})
        works = distinct_primary_works(rec.get("source_authors"))
        # Conservative floor: never claim more diversity than distinct authors.
        n_authors = e.get("distinct_authors", 0)
        new_diversity = max(1, min(works, n_authors)) if n_authors > 0 else 1
        plan.append({
            "fb_id": fb_id,
            "name": e.get("name"),
            "old_source_diversity": e.get("source_diversity"),
            "distinct_authors": n_authors,
            "distinct_primary_works": works,
            "new_source_diversity": new_diversity,
            "new_is_convergent": 0,
        })
    plan.sort(key=lambda p: p["fb_id"])
    return plan


def apply_to_db(plan: list[dict], ts: str) -> tuple[str, int]:
    """C13 backup + atomic UPDATE of fbs.is_convergent / source_diversity."""
    bak = DB.with_name(f"maxwell.db.bak_{ts}_pre_falseconv")
    shutil.copy2(DB, bak)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    updated = 0
    try:
        cur.execute("BEGIN")
        for p in plan:
            cur.execute(
                "UPDATE fbs SET is_convergent=?, source_diversity=? WHERE fb_id=?",
                (p["new_is_convergent"], p["new_source_diversity"], p["fb_id"]),
            )
            updated += cur.rowcount
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return bak.name, updated


def write_manifest(plan: list[dict], ts: str, applied: bool) -> None:
    """Emit the audit manifest (JSON + MD)."""
    doc = {
        "note": "BUG-232 false-convergence re-tier: same-author echoes -> single-source provenance",
        "ts": ts,
        "applied": applied,
        "echo_count": len(plan),
        "primary_work_recompute": {
            "same_work_2_editions": sum(1 for p in plan if p["distinct_primary_works"] == 1),
            "same_author_distinct_works": sum(1 for p in plan if p["distinct_primary_works"] >= 2),
        },
        "fixes": plan,
    }
    MANIFEST_JSON.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = [
        "# FALSE-CONVERGENCE FIX MANIFEST (BUG-232)",
        "",
        f"- Applied: **{applied}** | ts: {ts} | echoes: {len(plan)}",
        f"- Same work (2 editions/files) → 1 primary work: "
        f"{sum(1 for p in plan if p['distinct_primary_works'] == 1)}",
        f"- Same author, distinct works: "
        f"{sum(1 for p in plan if p['distinct_primary_works'] >= 2)}",
        "",
        "| fb_id | name | old_div | authors | works | new_div | new_convergent |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in plan:
        md.append(
            f"| {p['fb_id'][:12]}… | {p['name']} | {p['old_source_diversity']} | "
            f"{p['distinct_authors']} | {p['distinct_primary_works']} | "
            f"{p['new_source_diversity']} | {p['new_is_convergent']} |"
        )
    md.append("")
    MANIFEST_MD.write_text("\n".join(md), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="C13 backup + UPDATE fbs")
    args = ap.parse_args()

    plan = build_fix_plan()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"echoes: {len(plan)}")
    print(f"  same work (2 editions) -> diversity 1: "
          f"{sum(1 for p in plan if p['distinct_primary_works'] == 1)}")
    print(f"  same author, distinct works:         "
          f"{sum(1 for p in plan if p['distinct_primary_works'] >= 2)}")
    for p in plan:
        print(f"  {p['fb_id'][:14]}… {p['name'][:44]:44s} "
              f"div {p['old_source_diversity']}->{p['new_source_diversity']} "
              f"conv 1->{p['new_is_convergent']}")

    if not args.apply:
        print("\nDRY-RUN: no changes. Re-run with --apply to mutate maxwell.db (C13 backup).")
        write_manifest(plan, ts, applied=False)
        return 0

    bak, updated = apply_to_db(plan, ts)
    write_manifest(plan, ts, applied=True)
    print(f"\nmaxwell.db: {updated} rows updated (backup: {bak})")
    print(f"manifest: {MANIFEST_JSON.name} / {MANIFEST_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
