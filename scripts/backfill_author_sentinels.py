#!/usr/bin/env python3
"""backfill_author_sentinels.py — BUG-175 / D2459 metadata cache backfill.

Replaces hallucinated placeholder authors in
`knowledge pipeline/checkpoints/book_metadata.jsonl` with the deterministic
filename-heuristic result. Phi-4-mini-instruct-8bit (BUG-053 pattern) emitted
the JSON type-name "string" on 7 books and "Unknown" on 3 more — contaminating
`citation` / `source_authors` / `primary_source` on 253 S2 records.

Backfill rule (never fabricate):
  - author := parse_filename_metadata(sanitize_source_book(source_book))["author"]
    → "Thinknetic" when the filename carries it (paren convention); "" otherwise.
  - "" resolves to "Unknown Author" at read time via resolve_book_metadata().

Crash-safe (C6): tempfile → fsync → os.replace. Idempotent: sentinel entries
only; real authors untouched.

Usage:
    python3 scripts/backfill_author_sentinels.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.book_metadata import (  # noqa: E402
    is_sentinel_author,
    parse_filename_metadata,
    sanitize_source_book,
)

METADATA_PATH: Path = _PROJECT_ROOT / "knowledge pipeline" / "checkpoints" / "book_metadata.jsonl"


def backfill(dry_run: bool = False) -> tuple[list[dict], list[dict]]:
    """Rewrite sentinel-author entries with heuristic authors.

    Returns (fixed_rows, unchanged_rows).
    """
    if not METADATA_PATH.exists():
        print(f"❌ {METADATA_PATH} not found")
        sys.exit(1)

    rows: list[dict] = []
    for line in METADATA_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping malformed line: {e}")
            continue

    fixed: list[tuple[str, dict]] = []  # (original_author, new_row)
    unchanged: list[dict] = []
    for row in rows:
        author = str(row.get("author") or "").strip()
        # Skip legitimately-empty authors (already resolve to "Unknown Author");
        # only non-empty placeholder contamination ("string", "Unknown", ...)
        # needs replacing.
        if not is_sentinel_author(author) or author == "":
            unchanged.append(row)
            continue
        source_book = str(row.get("source_book") or "")
        heuristic_author = parse_filename_metadata(
            sanitize_source_book(source_book)
        ).get("author", "")
        fixed.append(
            (
                author,
                {
                    **row,
                    "author": heuristic_author,  # "" → "Unknown Author" at read time
                    "backfilled_by": "D2459/BUG-175",
                },
            )
        )

    if dry_run:
        print(f"🔍 DRY RUN — would fix {len(fixed)} entries (leave {len(unchanged)} untouched):")
        for orig_author, row in fixed:
            print(f"   - {row.get('source_book')!r}\n       author: {orig_author!r} → {row.get('author')!r}")
        return fixed, unchanged

    # C6 crash-safe write: tempfile → fsync → os.replace
    fd, tmp_path = tempfile.mkstemp(
        dir=str(METADATA_PATH.parent), prefix=".book_metadata.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for row in unchanged + [new for _, new in fixed]:  # preserve original line order
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, METADATA_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    print(f"✅ Backfilled {len(fixed)} sentinel-author entries (crash-safe replace):")
    for orig_author, row in fixed:
        print(f"   - {row.get('source_book')!r}\n       author: {orig_author!r} → {row.get('author')!r}")
    print(f"   Untouched: {len(unchanged)} entries")
    return fixed, unchanged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)
