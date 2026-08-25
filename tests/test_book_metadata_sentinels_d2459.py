"""D2459 (BUG-175) — author-sentinel validation regression tests.

BUG-175: Phi-4-mini-instruct-8bit hallucinated the JSON type-name "string" as
an author on 7 books (253 S2 records) and "Unknown" on 3 more (BUG-053
pattern). These tests lock in the sentinel detection + heuristic fallback so
placeholder authors can never propagate into provenance again.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import pipeline.book_metadata as bm


# ── Sentinel detection ───────────────────────────────────────────────────────

def test_is_sentinel_author_catches_type_names():
    for bad in ("string", "str", "Unknown", "unknown", "null", "none",
                "undefined", "n/a", "number", "object", "array", "author"):
        assert bm.is_sentinel_author(bad), f"{bad!r} should be a sentinel"


def test_is_sentinel_author_preserves_legit_values():
    # Case-SENSITIVE: "Anonymous" / "Various" are legitimate corpus values.
    for good in ("Anonymous", "Various", "Seth Godin", "Thinknetic",
                 "Brian Christian, Tom Griffiths", "Liz Blazer", "string of pearls"):
        assert not bm.is_sentinel_author(good), f"{good!r} must NOT be a sentinel"


def test_is_sentinel_author_blank_and_none():
    assert bm.is_sentinel_author("")
    assert bm.is_sentinel_author(None)


# ── Cache load blanking (read boundary) ──────────────────────────────────────

def _write_temp_metadata(tmp_path, entries):
    p = tmp_path / "book_metadata.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return p


def test_cache_blanks_sentinel_author(tmp_path, monkeypatch):
    p = _write_temp_metadata(tmp_path, [
        {"source_book": "Bug Book.md", "author": "string", "title": "Bug Book", "year": "2020"},
        {"source_book": "Good Book.md", "author": "Seth Godin", "title": "Purple Cow", "year": "2003"},
    ])
    monkeypatch.setattr(bm, "METADATA_PATH", p)
    cache = bm.load_metadata_cache(force=True)
    assert cache["Bug Book.md"]["author"] == ""      # sentinel blanked
    assert cache["Good Book.md"]["author"] == "Seth Godin"  # untouched


def test_resolve_book_metadata_never_returns_sentinel(tmp_path, monkeypatch):
    p = _write_temp_metadata(tmp_path, [
        {"source_book": "Bug Book.md", "author": "Unknown", "title": "Bug Book", "year": None},
    ])
    monkeypatch.setattr(bm, "METADATA_PATH", p)
    # title is known → heuristic is skipped → blank author must resolve to Unknown Author
    meta = bm.resolve_book_metadata("Bug Book.md")
    assert meta["author"] == "Unknown Author"
    assert "string" not in meta["author"] and "Unknown" != meta["author"]


def test_resolve_mental_models_thinknetic(tmp_path, monkeypatch):
    """The backfilled cache value (Thinknetic) must survive resolution."""
    fn = ("Mental Models In A Nutshell Practical Thinking Frameworks (Thinknetic) "
          "(z-library.sk, 1lib.sk, z-lib.sk).md")
    p = _write_temp_metadata(tmp_path, [
        {"source_book": fn, "author": "Thinknetic", "title": "Mental Models In A Nutshell", "year": None},
    ])
    monkeypatch.setattr(bm, "METADATA_PATH", p)
    meta = bm.resolve_book_metadata(fn)
    assert meta["author"] == "Thinknetic"


# ── Heuristic junk rejection (D2459: _AUTHOR_JUNK extended) ──────────────────

def test_author_junk_rejects_etc_and_domains():
    p = bm.parse_filename_metadata(
        bm.sanitize_source_book("Silent Weapons for Quiet Wars - An Introduction Programming Manual ( etc.) (Z-Library).md")
    )
    assert p["author"] == ""  # "etc." is junk, not an author
    p2 = bm.parse_filename_metadata(
        bm.sanitize_source_book("The Basics of Color Psychology (ColorPsychology.org) (z-lib.org).md")
    )
    assert p2["author"] == ""  # a domain is junk, not an author


def test_author_junk_preserves_real_authors():
    p = bm.parse_filename_metadata("Algorithms to Live By (Brian Christian, Tom Griffiths).md")
    assert p["author"] == "Brian Christian, Tom Griffiths"


# ── Backfill script sanity ───────────────────────────────────────────────────

def test_backfill_script_importable_and_crash_safe(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "backfill_author_sentinels",
        Path(__file__).resolve().parent.parent / "scripts" / "backfill_author_sentinels.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # dry-run on a temp copy must not modify the source file
    p = _write_temp_metadata(tmp_path, [
        {"source_book": "Bug.md", "author": "string", "title": "Bug", "year": None},
    ])
    monkeypatch.setattr(mod, "METADATA_PATH", p)
    fixed, unchanged = mod.backfill(dry_run=True)
    assert len(fixed) == 1
    # file untouched by dry-run
    raw = p.read_text(encoding="utf-8")
    assert '"string"' in raw
    assert "backfilled_by" not in raw
    # real run rewrites crash-safe (tempfile → os.replace leaves no .tmp)
    fixed2, _ = mod.backfill(dry_run=False)
    assert len(fixed2) == 1
    assert not list(tmp_path.glob(".*.tmp"))
    content = json.loads(p.read_text(encoding="utf-8").strip())
    assert content["author"] == ""
    assert content["backfilled_by"] == "D2459/BUG-175"
