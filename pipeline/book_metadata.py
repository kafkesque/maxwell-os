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
    from pipeline.book_metadata import resolve_source_id, resolve_source_ids
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

# ── Cache (lazy-loaded once per process) ─────────────────────────────────────
_metadata_cache: dict[str, dict[str, str]] | None = None
_normalized_index: dict[str, str] | None = None  # normalized-key → cache key
# D2176: use DATA_DIR from pipeline_paths (no hardcoded paths per C12a)
try:
    from pipeline.pipeline_paths import DATA_DIR
    METADATA_PATH: Path = DATA_DIR / "checkpoints" / "book_metadata.jsonl"
except ImportError:
    METADATA_PATH: Path = Path("knowledge pipeline/checkpoints/book_metadata.jsonl")


def _unicode_fold(text: str) -> str:
    """Fold Unicode to a canonical ASCII-ish form (D2507/BUG-205).

    NFKC (compatibility: full-width, ligatures, curly quotes) → NFKD (canonical
    decomposition: "é" → "e" + combining acute) → strip combining marks. This makes
    "Brené" == "Brene", "ﬁ" == "fi", "ｆｕｌｌ" == "full" so near-duplicate book
    metadata collapses to one canonical source_id.
    """
    text = unicodedata.normalize("NFKC", text or "")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _normalize_key(name: str) -> str:
    """Normalize a filename for fuzzy matching (alphanumerics only, lower).

    D2507 (BUG-205): Unicode-fold first so equivalent filenames (curly quotes,
    composed/decomposed accents, full-width chars) collapse.
    """
    return re.sub(r"[^a-z0-9]", "", _unicode_fold(name.lower()))


# ── Source-filename noise sanitization (D2449) ──────────────────────────────
# Piracy-site / archive artifacts ("(z-library.sk, 1lib.sk, z-lib.sk)",
# "(z-lib.org)", "-- Anna's Archive", "-- <32-hex hash>") pollute source_books /
# source_text / citation. Markers are config-driven (C12) — config/filtering.yaml.
def _load_noise_markers() -> list[str]:
    """Load source-noise markers from config/filtering.yaml (C12 config-first)."""
    try:
        import yaml

        from pipeline.pipeline_paths import PROJECT_ROOT
        cfg_path = PROJECT_ROOT / "config" / "filtering.yaml"
        with open(cfg_path) as _f:
            _cfg = yaml.safe_load(_f) or {}
        markers = (_cfg.get("source_noise") or {}).get("markers") or []
        return [str(m).strip() for m in markers if str(m).strip()]
    except Exception:
        # Never let a config read failure break extraction (fail-open on markers).
        return []


_SOURCE_NOISE_MARKERS: list[str] = _load_noise_markers()


def _has_noise_marker(text: str) -> bool:
    # Normalize apostrophes (curly ' / ' vs straight ') so "Anna's Archive"
    # matches the config marker regardless of quote style.
    norm = re.sub(r"['\u2019\u2018\u201b]", "", text.lower())
    return any(
        re.sub(r"['\u2019\u2018\u201b]", "", m.lower()) in norm
        for m in _SOURCE_NOISE_MARKERS
    )


def sanitize_source_book(filename: str) -> str:
    """Strip piracy-site / archive noise from a source filename (D2449).

    Removes parenthetical groups (e.g. "(z-library.sk, 1lib.sk, z-lib.sk)")
    and trailing "-- <noise>" segments (e.g. "-- Anna's Archive", "-- <32-hex
    hash>") so persisted source_books / source_text / citation carry only the
    real author/title. Idempotent; returns the original when nothing matches.
    """
    name = (filename or "").strip()
    if not name:
        return name
    # Remove any parenthetical group containing a noise marker.
    name = re.sub(
        r"\([^()]*\)",
        lambda m: "" if _has_noise_marker(m.group(0)) else m.group(0),
        name,
    )
    # Remove trailing "-- <noise>" segments (site name or 32-hex identifier).
    def _strip_dash(seg: re.Match) -> str:
        seg_text = seg.group(0)
        if _has_noise_marker(seg_text):
            return ""
        if re.search(r"[0-9a-f]{32}", seg_text):
            return ""
        return seg_text

    name = re.sub(r"--[^-]*(?=$|--)", _strip_dash, name)
    # Tidy: empty parens, doubled whitespace, stray leading/trailing separators,
    # and whitespace left before a file extension (".md") after noise removal.
    name = re.sub(r"\(\s*\)", "", name)
    name = re.sub(r"\s{2,}", " ", name)
    name = re.sub(r"\s+\.", ".", name)
    name = name.strip(" -()")
    return name or (filename or "").strip()


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
                    # D2459 (BUG-175): blank hallucinated placeholder authors
                    # ("string", "Unknown", ...) so the filename heuristic /
                    # "Unknown Author" fallback runs instead of propagating.
                    author_raw = str(d.get("author", "") or "").strip()
                    author_val = "" if is_sentinel_author(author_raw) else author_raw
                    cache[key] = {
                        "author": author_val,
                        "title": str(d.get("title", "") or "").strip(),
                        "year": str(d.get("year", "") or "").strip(),
                    }
                    nk = _normalize_key(key)
                    if nk and nk not in norm_index:  # first occurrence wins
                        norm_index[nk] = key
    _metadata_cache = cache
    _normalized_index = norm_index
    return cache


# ── BUG-175 (D2459): Phi-4-mini author-hallucination sentinels ─────────────
# Phi-4-mini-instruct-8bit occasionally returns a JSON *type name* ("string")
# or a generic placeholder ("Unknown") instead of a real author on open-ended
# filename→author extraction (BUG-053 hallucination pattern). These are NEVER
# valid author names. Case-SENSITIVE by design: "Anonymous" and "Various" are
# legitimate corpus values and MUST NOT match.
_AUTHOR_SENTINELS: frozenset[str] = frozenset({
    "", "string", "str", "none", "null", "undefined",
    "unknown", "Unknown", "missing", "todo", "tbd",
    "n/a", "na", "number", "integer", "int", "float",
    "boolean", "bool", "object", "array", "any",
    "author", "title", "unknown author",
})


def is_sentinel_author(author: str) -> bool:
    """True if author is a known hallucination/placeholder sentinel (D2459).

    BUG-175: Phi-4-mini emitted the type-name "string" as an author on 7 books
    (253 S2 records) and "Unknown" on 3 more. Sentinel authors are treated as
    unknown so the deterministic filename heuristic / "Unknown Author" fallback
    runs instead of propagating the bogus value into provenance.
    """
    return str(author or "").strip() in _AUTHOR_SENTINELS


# ── Canonical source identity (D2176: prevents false convergence) ──────────

# Cache: source_book filename → canonical source_id
_source_id_cache: dict[str, str] = {}


# ── D2308: Canonicalization (prevent duplicate-edition false convergence) ──
_SUBTITLE_SPLIT = re.compile(r"[:—–-]")
_COAUTHOR_SPLIT = re.compile(r",|\band\b|&", re.IGNORECASE)
_CAMEL_CONCAT = re.compile(r"([a-z0-9])([A-Z])")
# D2315: camelCase-concatenated subtitle opener (no separator). "The Black
# SwanThe Impact of the Highly Improbable" -> split at "The" boundary, drop
# the subtitle so it collapses with "The Black Swan" (same work, different
# edition). Lookahead requires a lowercase/digit before + word boundary after.
_CONCAT_SUBTITLE_SPLIT = re.compile(r"(?<=[a-z0-9])(?=(?:The|A|An|How|Why|What)\b)")
# D2507 (BUG-205): SPACE-separated subtitle opener — the "Blink The Power of
# Thinking Without Thinking" vs "Blink: The Power…" asymmetry. A title whose
# subtitle-opener word ("the"/"how"/"why"/"what") is separated by a SPACE
# (not a colon/dash, not concatenated) also splits, so edition variants collapse.
# Applied AFTER lowercasing (so the opener list is lowercase); requires whitespace
# BEFORE the opener so a leading "The" ("The Compound Effect") is never split.
# D2509 (BUG-205 residual): `a`/`an` REMOVED from the opener list — a mid-title
# article ("Build a Large Language Model" vs "Build a Reasoning Model") was
# falsely treated as a subtitle opener, collapsing 2 DISTINCT Raschka books into
# one source_id. The colon/dash `_SUBTITLE_SPLIT` path still handles "a/an"
# subtitle openers ("Sapiens: A Brief History"), so only the ambiguous
# space-separated article is dropped (missed-collapse is safer than false-merge).
_SPACE_SUBTITLE_SPLIT = re.compile(r"\s+(?=(?:the|how|why|what)\b)")


def normalize_author(author: str) -> str:
    """D2308/D2507: Canonicalize an author string to primary-author form.

    'Anthony Dunne, Fiona Raby' -> 'anthony dunne'
    Collapses co-author lists (','/'and'/'&'), case, punctuation, and Unicode
    drift (NFKC) so that edition variants of the same work resolve to the same
    author key.
    """
    a = (author or "").strip().lower()
    a = _unicode_fold(a)
    a = _COAUTHOR_SPLIT.split(a, maxsplit=1)[0].strip()
    a = re.sub(r"[^a-z ]", "", a)
    return re.sub(r"\s+", " ", a).strip()


def normalize_title(title: str) -> str:
    """D2308/D2315/D2507: Canonicalize a title string (strip subtitle, fix concatenation).

    'Make Bootstrappers Handbook: Learn to build...' -> 'make bootstrappers handbook'
    'The Black SwanThe Impact of...' -> 'the black swan' (D2315: split at concat
    subtitle-opener and drop the subtitle, so edition variants collapse).
    'Blink The Power of Thinking...' -> 'blink' (D2507: split at the SPACE-separated
    subtitle-opener so the colon-less edition collapses with the colon edition).
    """
    raw = (title or "").strip()
    # D2315: camelCase-concatenated subtitle — split at the concat boundary
    # before a subtitle-opener word and drop the remainder.
    m = _CONCAT_SUBTITLE_SPLIT.search(raw)
    if m:
        raw = raw[:m.start()].rstrip()
    t = _unicode_fold(raw.lower())
    t = _CAMEL_CONCAT.sub(r"\1 \2", t)
    t = _SUBTITLE_SPLIT.split(t, maxsplit=1)[0]
    t = _SPACE_SUBTITLE_SPLIT.split(t, maxsplit=1)[0]
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


def compute_source_id(author: str, title: str, fallback_key: str = "") -> str:
    """Generate a canonical source_id from author + title.

    Stable across filename variations. Same book with different filenames
    (editions, formats, naming conventions) resolves to the same source_id.

    Priority:
      1. SHA-256(author + "|" + title) if author and title are known
      2. SHA-256("unknown|" + normalized_fallback) if only fallback available

    Args:
        author: Resolved author name (may be "Unknown Author").
        title: Resolved title (may be "Unknown Title").
        fallback_key: Normalized filename (used only if author/title unknown).

    Returns:
        16-char hex source_id (first 16 of SHA-256).
    """
    if author and author != "Unknown Author" and title and title != "Unknown Title":
        canonical = f"{normalize_author(author)}|{normalize_title(title)}"
    elif fallback_key:
        canonical = f"unknown|{_normalize_key(fallback_key)}"
    else:
        canonical = f"unknown|{normalize_title(title)}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def resolve_source_id(source_book: str) -> str:
    """Resolve a source_book filename → canonical source_id.

    Uses metadata cache for author/title; falls back to filename heuristics.
    Results are cached in _source_id_cache for O(1) subsequent lookups.

    Args:
        source_book: Raw source_book filename from segment/cluster metadata.

    Returns:
        16-char hex source_id.
    """
    fname: str = (source_book or "").strip()
    if not fname:
        return hashlib.sha256(b"unknown|empty").hexdigest()[:16]

    if fname in _source_id_cache:
        return _source_id_cache[fname]

    meta: dict[str, str] = resolve_book_metadata(fname)
    # D2507 (BUG-205): sanitize the fallback key (download-source strip) so a
    # cache-miss with unknown author/title does not hash piracy-site noise into
    # the source_id ("…_liber3", "…(z-lib.org)" etc. would otherwise diverge).
    fallback_key = sanitize_source_book(Path(fname).name)
    sid: str = compute_source_id(
        author=meta.get("author", ""),
        title=meta.get("title", ""),
        fallback_key=fallback_key,
    )
    _source_id_cache[fname] = sid
    return sid


def resolve_source_ids(source_books: list[str]) -> set[str]:
    """Resolve a list of source_book filenames → set of canonical source_ids.

    Use this for source diversity counting. Unlike counting distinct filenames,
    this collapses duplicates (same book, different editions/formats).

    Args:
        source_books: List of source_book filename strings.

    Returns:
        Set of unique 16-char hex source_ids.
    """
    return {resolve_source_id(b) for b in (source_books or []) if b}


# ── Filename heuristic fallback (robust, handles leading parens) ────────────
_AUTHOR_JUNK = re.compile(
    r"^(z-library|libgen|anna|isbn|http|www\.|etc\.?|unknown|\d{4}|"
    r"[\w.-]+\.(org|com|net|io|edu|gov|co))$",
    re.IGNORECASE,
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

    # 1. Authoritative cache (exact key → name → sanitized → normalized fuzzy).
    # D2449: also try the sanitized name so a caller that already stripped
    # piracy markers still hits the raw-keyed cache.
    fname_san = sanitize_source_book(fname)
    cache = load_metadata_cache()
    cached = (
        cache.get(fname)
        or cache.get(Path(fname).name)
        or cache.get(fname_san)
        or cache.get(Path(fname_san).name)
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

    # D2459 (BUG-175): defense-in-depth — a sentinel author can never propagate
    # past this resolver, even from a stale/uncached path.
    if is_sentinel_author(author):
        author = ""

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
