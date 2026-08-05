#!/usr/bin/env python3
"""book_metadata.py — Author/title/year resolution + primary-source selection.
=================================================================================
D2117: Joins book_metadata.jsonl (Stage 0.5 authoritative cache) into FBs.
Fixes: provenance swap bug (filename parens), empty cache key bug ("file" vs
"source_book"), and adds primary_source designation for convergent FBs.

Authoritative order:
  1. book_metadata.jsonl cache (keyed by source_book filename)
  2. Robust filename heuristic (handles leading-paren filenames)
  3. "Unknown" fallback — never fabricate

Usage:
    from pipeline.book_metadata import resolve_book_metadata, select_primary_source
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# ── Cache (lazy-loaded once per process) ─────────────────────────────────────
_metadata_cache: dict[str, dict[str, str]] | None = None
_normalized_index: dict[str, str] | None = None  # normalized-key → cache key
METADATA_PATH: Path = Path("knowledge pipeline/checkpoints/book_metadata.jsonl")


def _normalize_key(name: str) -> str:
    """Normalize a filename for fuzzy matching (alphanumerics only, lower)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def load_metadata_cache(force: bool = False) -> dict[str, dict[str, str]]:
    """Load book_metadata.jsonl → {source_book: {author, title, year}}.

    BUG-061 FIX: previously keyed by d.get("file") which never exists in
    the actual records (they use source_book) → cache was always empty →
    every FB fell back to fragile filename parsing (author/title swap).

    Args:
        force: Reload even if already cached.

    Returns:
        Dict mapping source_book filename → {author, title, year}.
    """
    global _metadata_cache, _normalized_index
    if _metadata_cache is not None and not force:
        return _metadata_cache

    cache: dict[str, dict[str, str]] = {}
    norm_index: dict[str, str] = {}
    if METADATA_PATH.exists():
        with open(METADATA_PATH) as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (d.get("source_book") or "").strip()
                if not key:
                    # Fall back to source_path stem if source_book missing
                    sp = d.get("source_path", "")
                    if sp:
                        key = Path(sp).name
                if key:
                    cache[key] = {
                        "author": str(d.get("author", "") or "").strip(),
                        "title": str(d.get("title", "") or "").strip(),
                        "year": str(d.get("year", "") or "").strip(),
                    }
                    nk = _normalize_key(key)
                    if nk and nk not in norm_index:  # first occurrence wins
                        norm_index[nk] = key
    _metadata_cache = cache
    _normalized_index = norm_index
    return cache


# ── Filename heuristic fallback (robust, handles leading parens) ────────────
_AUTHOR_JUNK = re.compile(
    r"^(z-library|libgen|anna|isbn|http|www\.|\d{4})$", re.IGNORECASE
)


def parse_filename_metadata(filename: str) -> dict[str, str]:
    """Best-effort author/title from filename. Handles parens at START.

    Patterns handled (in priority order):
      "Title -- Author -- ..."          (double-dash convention)
      "Title (Author) (publisher)"      (paren convention, title first)
      "(Leading Paren) Title (Author)"  (leading-paren; strip leading parens)

    Args:
        filename: Source book filename (with or without extension).

    Returns:
        {"author": str, "title": str} — empty strings when not resolvable.
    """
    stem = Path(filename).stem

    # 1. Double-dash convention: "Title -- Author -- rest"
    m = re.match(r"^(.+?)\s+--\s+(.+?)(?:\s+--.*)?$", stem)
    if m:
        title = m.group(1).strip()
        author = m.group(2).strip()
        if not _AUTHOR_JUNK.match(author):
            return {"author": author, "title": title}

    # 2. Paren convention: "Title (Author) (rest)"
    m = re.match(r"^(.+?)\s*\(([^)]+?)\)\s*(?:\(.*)?$", stem)
    if m:
        title = m.group(1).strip()
        author = m.group(2).strip()
        if not _AUTHOR_JUNK.match(author) and not re.match(r"^\d{4}$", author):
            return {"author": author, "title": title}

    # 3. Leading-paren filenames: "(X) (Y) Title (Author)" or "(X) Title"
    m = re.match(r"^(?:\([^)]*\)\s*)+(.+?)\s*\(([^)]+?)\)\s*$", stem)
    if m:
        title = m.group(1).strip()
        author = m.group(2).strip()
        if not _AUTHOR_JUNK.match(author) and not re.match(r"^\d{4}$", author):
            return {"author": author, "title": title}

    # 4. Fallback: strip leading parens entirely, take whole stem as title
    cleaned = re.sub(r"^(?:\([^)]*\)\s*)+", "", stem).strip()
    if cleaned:
        return {"author": "", "title": cleaned}

    return {"author": "", "title": ""}


def resolve_book_metadata(filename: str) -> dict[str, str]:
    """Resolve author/title/year for a book filename.

    Priority: metadata cache → robust filename heuristic → Unknown.

    Args:
        filename: Source book filename.

    Returns:
        {"author": str, "title": str, "year": str} — never empty author/title
        (uses "Unknown Author" / "Unknown Title" as final fallback).
    """
    fname = (filename or "").strip()
    if not fname:
        return {"author": "Unknown Author", "title": "Unknown Title", "year": ""}

    # 1. Authoritative cache (exact key → name → normalized fuzzy)
    cache = load_metadata_cache()
    cached = (
        cache.get(fname)
        or cache.get(Path(fname).name)
        or {}
    )
    if not cached:
        # BUG-061: filenames differ by dash/paren variants between stages
        # (e.g. "A -- Mostafa" vs "A - Mostafa"). Normalized match bridges it.
        nk = _normalize_key(Path(fname).name)
        hit_key = _normalized_index.get(nk) if nk else None
        if hit_key:
            cached = cache.get(hit_key, {})
    author = (cached.get("author") or "").strip()
    title = (cached.get("title") or "").strip()
    year = (cached.get("year") or "").strip()

    # 2. Filename heuristic
    if not author and not title:
        parsed = parse_filename_metadata(fname)
        author = parsed.get("author", "")
        title = parsed.get("title", "")

    return {
        "author": author or "Unknown Author",
        "title": title or "Unknown Title",
        "year": year or "",
    }


def build_citation(author: str, title: str, filename: str) -> str:
    """Build a human-readable citation string.

    Args:
        author: Resolved author name.
        title: Resolved title.
        filename: Original source filename (used if title is unknown).

    Returns:
        "Author (Title)" or "Unknown Author (Unknown Title)".
    """
    a = author if author and author != "Unknown Author" else "Unknown Author"
    t = title if title and title != "Unknown Title" else Path(filename).name
    return f"{a} ({t})"


def select_primary_source(
    source_books: list[str],
    evidence_passages: list[str] | None = None,
) -> dict[str, str]:
    """Select the most established/origin source for a convergent FB.

    Heuristic (deterministic, config-free):
      1. Earliest publication year (metadata), if available and distinct.
      2. Tie-break: most evidence_passages attributed to that book
         (proxied by source_books order match — evidence quotes carry
         no per-book tag, so we fall back to source order).
      3. Final fallback: first book in source_books.

    Args:
        source_books: List of distinct source book filenames.
        evidence_passages: Unused today; reserved for per-quote attribution.

    Returns:
        {"book": str, "reason": str} — primary source + selection reason.
    """
    books = [b for b in (source_books or []) if b]
    if not books:
        return {"book": "Unknown Source", "reason": "no source books"}
    if len(books) == 1:
        return {"book": books[0], "reason": "single source"}

    cache = load_metadata_cache()
    best_book = books[0]
    best_year: int | None = None

    for b in books:
        meta = cache.get(b) or {}
        y = (meta.get("year") or "").strip()
        try:
            y_int = int(y)
        except (TypeError, ValueError):
            continue  # missing year → cannot rank
        if best_year is None or y_int < best_year:
            best_year = y_int
            best_book = b

    if best_year is not None:
        return {
            "book": best_book,
            "reason": f"earliest publication year ({best_year})",
        }
    return {"book": books[0], "reason": "no year metadata; first source"}
