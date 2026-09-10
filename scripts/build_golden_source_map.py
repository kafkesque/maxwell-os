#!/usr/bin/env python3
"""scripts/build_golden_source_map.py — D2585 P5 Step 1 (source map).

Joins each golden example to its source FB's provenance metadata so the P5
GOLD-A/B/CHALLENGE freeze can enforce BOOK/AUTHOR-DISJOINT strata.

  config/golden/stage4_golden_mined.yaml   (example id + rationale -> 64-hex fb_id)
  knowledge pipeline/maxwell.db  fbs       (fb_id -> source_books/source_authors/
                                             primary_source/source_ids/citation)

Read-only. Writes temp/golden_source_map.json (+ a coverage report to
governance/golden_source_map.md).
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_GOLDEN_YAML = _ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
_OUT_JSON = _ROOT / "temp" / "golden_source_map.json"
_OUT_MD = _ROOT / "governance" / "golden_source_map.md"

_FB_ID_RE = re.compile(r"([0-9a-f]{64})")


def _parse_json_field(raw) -> list:
    """Parse a JSON-encoded DB column safely; return [] on null/empty/bad."""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        v = json.loads(raw)
        return v if isinstance(v, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def main() -> int:
    doc = yaml.safe_load(_GOLDEN_YAML.read_text(encoding="utf-8")) or {}
    examples: list[dict] = doc.get("examples", [])

    # example_id -> 64-hex fb_id (from rationale).
    fb_of: dict[str, str] = {}
    no_fb: list[str] = []
    for ex in examples:
        m = _FB_ID_RE.search(ex.get("rationale", ""))
        if m:
            fb_of[str(ex["id"])] = m.group(1)
        else:
            no_fb.append(str(ex["id"]))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = {
        r["fb_id"]: r
        for r in conn.execute(
            "SELECT fb_id, source_books, source_authors, source_ids, primary_source, "
            "citation FROM fbs"
        )
    }
    conn.close()

    out: list[dict] = []
    missing_db: list[str] = []
    n_books = n_authors = 0
    for ex in examples:
        eid = str(ex["id"])
        fb = fb_of.get(eid)
        rec = rows.get(fb) if fb else None
        if rec is None:
            missing_db.append(eid)
            out.append({
                "example_id": eid, "fb_id": fb, "discipline":
                (ex.get("expected_classification") or {}).get("discipline"),
                "books": [], "authors": [], "primary_source": None,
                "citation": None, "has_provenance": False,
            })
            continue
        books = _parse_json_field(rec["source_books"])
        authors_raw = _parse_json_field(rec["source_authors"])
        # authors is a list of {book, author} — collapse to distinct author names.
        author_names = sorted({
            (a.get("author") or "").strip()
            for a in authors_raw if isinstance(a, dict) and (a.get("author") or "").strip()
        })
        n_books += bool(books)
        n_authors += bool(author_names)
        out.append({
            "example_id": eid,
            "fb_id": fb,
            "discipline": (ex.get("expected_classification") or {}).get("discipline"),
            "depth": (ex.get("expected_classification") or {}).get("depth"),
            "is_backfill": bool(ex.get("is_backfill", False)),
            "books": books,
            "authors": author_names,
            "primary_source": rec["primary_source"],
            "citation": rec["citation"],
            "source_ids": _parse_json_field(rec["source_ids"]),
            "has_provenance": bool(books or author_names),
        })

    _OUT_JSON.write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    n = len(out)
    prov = sum(1 for r in out if r["has_provenance"])
    b = sum(1 for r in out if r["books"])
    a = sum(1 for r in out if r["authors"])
    # Book/author overlap within the golden set (authors appearing in >1 example).
    author_counts: Counter = Counter()
    book_counts: Counter = Counter()
    for r in out:
        for author in r["authors"]:
            author_counts[author] += 1
        for book in r["books"]:
            book_counts[book] += 1
    shared_authors = {k: v for k, v in author_counts.items() if v > 1}
    shared_books = {k: v for k, v in book_counts.items() if v > 1}

    report = {
        "n_examples": n,
        "n_with_fb_id": len(fb_of),
        "n_missing_db": len(missing_db),
        "n_with_provenance": prov,
        "n_with_books": b,
        "n_with_authors": a,
        "distinct_authors": len(author_counts),
        "distinct_books": len(book_counts),
        "authors_shared_across_examples": len(shared_authors),
        "books_shared_across_examples": len(shared_books),
        "top_shared_authors": dict(sorted(shared_authors.items(), key=lambda t: -t[1])[:10]),
        "top_shared_books": dict(sorted(shared_books.items(), key=lambda t: -t[1])[:10]),
        "out": str(_OUT_JSON),
    }
    _OUT_MD.write_text(
        "\n".join([
            "# GOLDEN SOURCE MAP (D2585 P5 Step 1)",
            "",
            f"**{n} examples** → {len(fb_of)} with fb_id → {n - len(missing_db)} in DB.",
            f"Provenance present on {prov} ({prov / n:.0%}); books {b} ({b / n:.0%}); "
            f"authors {a} ({a / n:.0%}).",
            "",
            f"- distinct authors: {report['distinct_authors']} | "
            f"distinct books: {report['distinct_books']}",
            f"- authors spanning >1 golden example: {len(shared_authors)}",
            f"- books spanning >1 golden example: {len(shared_books)}",
            "",
            "**Shared authors** (book/author-disjointness constraint):",
            "",
            *[f"- `{k}` ({v} examples)" for k, v in list(sorted(
                shared_authors.items(), key=lambda t: -t[1]))[:10]],
            "",
            "**Shared books**:",
            "",
            *[f"- `{k}` ({v} examples)" for k, v in list(sorted(
                shared_books.items(), key=lambda t: -t[1]))[:10]],
            "",
        ]),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
