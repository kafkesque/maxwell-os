#!/usr/bin/env python3
"""
stage0_5_extract_metadata.py — Extract Author/Title from MD Book Preambles.
============================================================================
Authority: D2114 | CONSTITUTION.md §3 (Runs after Stage 0, before Stage 1)

Input:  MD files from books/ directory
Output: book_metadata.jsonl — maps source_book filename → {author, title, year}

Problem: Stage 0 converts EPUB/PDF → MD, but filenames are inconsistent:
  - Good: "How to Read a Person Like a Book - Gerard I. Nierenberg.md"
  - Bad:  "kaczynski2.md", "SSRN-id2594754.md", "Epistemology In The Cloud.md"
  - Ugly: "[Guy_Debord]_The_Society_of_the_Spectacle_(Annotat(z-lib.org).md"

Solution: Feed first ~1500 chars of each MD file to Phi-4-mini (OMLX, temp=0.0)
to extract structured author/title/year. Results cached in book_metadata.jsonl.

Process:
  1. Scan books/ for all .md files
  2. Check book_metadata.jsonl cache — skip if already extracted
  3. For each uncached file: read first 1500 chars, send to LLM
  4. Validate JSON response, write to cache
  5. Stage 1 chunking reads cache to populate normalized metadata

Usage:
    python3 pipeline/stage0_5_extract_metadata.py
    python3 pipeline/stage0_5_extract_metadata.py --force  # Re-extract all
    python3 pipeline/stage0_5_extract_metadata.py --model Phi-4-mini-instruct-8bit
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import safe_write
from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import BOOKS_DIR, CHECKPOINT_DIR, OMLX_URL
from pipeline.stamp import get_pipeline_commit, stamp_record

# ── Constants ──────────────────────────────────────────────────────────────
METADATA_CACHE: str = "book_metadata.jsonl"
PREAMBLE_CHARS: int = 1500  # First N chars of MD file sent to LLM
DEFAULT_MODEL: str = "Phi-4-mini-instruct-8bit"  # Fast, temp=0.0
BATCH_DELAY: float = 0.5  # Seconds between LLM calls (rate limit courtesy)

# ── System prompt for metadata extraction ──────────────────────────────────

METADATA_SYSTEM: str = """You are a bibliographic metadata extraction engine. You receive the first 1500
characters of a book's Markdown file. Extract the author, title, and publication year.

The filename may be truncated or contain artifacts like (z-lib.org), [Author_Name], 
SSRN IDs, or opaque slugs like "kaczynski2". The actual title and author are in 
the TEXT, not the filename.

RULES:
- Title: the book's main title, not a chapter or section heading. Clean up artifacts.
- Author: full name of the primary author. If multiple, list first author or "Various".
  If truly anonymous, use "Anonymous".
- Year: 4-digit publication year if findable. If not, use null.
- Never hallucinate. If you cannot determine a field, use "" for strings or null for year.
- Strip Z-Library, libgen, Anna's Archive, and other distributor artifacts.

Return ONLY valid JSON with no markdown fences:"""

# ── Extraction prompt template ──────────────────────────────────────────────

METADATA_PROMPT: str = """Filename: {filename}

Text preamble:
{text}

Return JSON: {{"author": "string", "title": "string", "year": int|null}}"""


def load_cache(cache_path: Path) -> dict[str, dict]:
    """Load existing metadata cache, keyed by source_book filename."""
    cache: dict[str, dict] = {}
    if cache_path.exists():
        with open(cache_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec: dict = json.loads(line)
                        if "source_book" in rec:
                            cache[rec["source_book"]] = rec
                    except json.JSONDecodeError:
                        continue
    return cache


def extract_from_text(text: str, filename: str, model: str) -> Optional[dict]:
    """Extract author/title/year from MD preamble text via LLM.

    Args:
        text: First PREAMBLE_CHARS characters of the MD file.
        filename: Original filename (for context in prompt).
        model: OMLX model to use.

    Returns:
        dict with author/title/year, or None on failure.
    """
    prompt: str = METADATA_PROMPT.format(
        filename=filename,
        text=text[:PREAMBLE_CHARS],
    )

    try:
        result: dict | None = call_omlx_json(
            prompt=prompt,
            model=model,
            system=METADATA_SYSTEM,
            max_tokens=256,
        )
        if isinstance(result, dict):
            return {
                "author": str(result.get("author", "")).strip(),
                "title": str(result.get("title", "")).strip(),
                "year": result.get("year"),  # int or None
            }
    except Exception as e:
        print(f"   ⚠️  LLM call failed for {filename}: {e}")

    return None


def _looks_like_person(name: str) -> bool:
    """Check if a string looks like a person's name (First Last or F. Last).

    Returns True for: 'Gerard I. Nierenberg', 'Robert B. Cialdini', 'Chase Hughes', 'Anonymous'
    Returns False for: 'Silent Weapons', 'The New Abnormal', 'Epistemology In The', 'Taylor & Francis'
    """
    name = name.strip()
    # Special case: explicit anonymous attribution
    if name.lower() == "anonymous":
        return True
    # Must be 2-4 words starting with capitals
    words = name.split()
    if not (2 <= len(words) <= 4):
        return False
    # First word must NOT be a common title/article or corporate indicator
    first_lower = words[0].lower()
    if first_lower in {"the", "a", "an", "for", "of", "in", "on", "to", "and", "or"}:
        return False
    # Reject corporate/organizational names
    if first_lower in {"taylor", "penguin", "harper", "oxford", "cambridge", "routledge", "springer", "wiley"}:
        return False
    # All words must start with uppercase (names) or be initials
    for w in words:
        if not w[0].isupper():
            return False
        # Allow middle initials like "I." or "B."
        if len(w) == 2 and w[1] == ".":
            continue
        if len(w) < 2:
            return False
    return True


def parse_filename_heuristic(filename: str) -> dict:
    """Regex-based fallback for well-formed filenames.

    Conservative: only matches clear patterns. Returns empty dict on ambiguity.
    LLM fallback handles everything the regex can't.

    Patterns (ordered — first match wins):
      1. [Author]_Title...          (Z-Library bracket)
      2. Title (Author) (Source)    (parenthetical author)
      3. Title by Author            (explicit attribution)
      4. Title -- Author -- Year -- ... (Anna's Archive)
      5. Author_Last_First_-_Title  (underscore separator)
      6. Title_-_Author             (underscore-dash-underscore)
      7. Title - Author Name         (dash separator, author must look like person)
      8. Title AuthorName liberN     (title then author before 'liber'/'pdfdrive')
    """
    name: str = Path(filename).stem

    # ── 1. [Author]_Title (Z-Library bracket) ──────────────────────────
    m: re.Match[str] | None = re.match(r"^\[([^\]]+)\]_?(.+)$", name)
    if m:
        author_candidate: str = m.group(1).replace("_", " ")
        title_candidate: str = re.sub(r"\([^)]*$", "", m.group(2)).strip()
        title_candidate = title_candidate.replace("_", " ")
        if _looks_like_person(author_candidate) and len(title_candidate) > 3:
            return {"author": author_candidate, "title": title_candidate, "year": None}

    # ── 2. Title (Author Name) [(Source)] ─────────────────────────────────
    m = re.match(r"^(.+?)\s+\(([A-Z][A-Za-z\s.]+)\)(?:\s*\([^)]*\))*\s*$", name)
    if m:
        title_candidate = m.group(1).strip()
        author_candidate = m.group(2).strip()
        if _looks_like_person(author_candidate) and len(title_candidate) > 3:
            return {"author": author_candidate, "title": title_candidate, "year": None}

    # ── 3. Title by Author ───────────────────────────────────────────────
    m = re.match(r"^(.+?)\s+by\s+((?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)|(?:[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+))", name)
    if m:
        author_candidate = m.group(2).strip()
        title_candidate = re.sub(r"\s*\([^)]*\)\s*$", "", m.group(1)).strip()
        if _looks_like_person(author_candidate) and len(title_candidate) > 3:
            return {"author": author_candidate, "title": title_candidate, "year": None}

    # ── 4. Title -- Author -- Year -- ... (Anna's Archive) ──────────────
    # Must avoid matching ISBN digits (9780...) as year. Year must be 1900-2099
    # and followed by --, end, or non-digit.
    m = re.match(r"^(.+?)\s*--\s*(.+?)\s*--\s*((?:19|20)\d{2})(?:\s*--.*|$)", name)
    if m:
        author_candidate = m.group(2).strip()
        title_candidate = m.group(1).strip()
        # Only accept if the author looks like a person (not "Taylor & Francis")
        if _looks_like_person(author_candidate) and len(title_candidate) > 3:
            return {"author": author_candidate, "title": title_candidate, "year": int(m.group(3))}

    # ── 5. Author_Last_Author_First_-_Title (underscore separator) ──────
    m = re.match(r"^([A-Z][a-z]+)_([A-Z][a-z]+)_-_([^_].+)$", name)
    if m:
        author = f"{m.group(1)} {m.group(2)}"
        title = m.group(3).replace("_", " ")
        if _looks_like_person(author):
            return {"author": author, "title": title, "year": None}

    # ── 6. Title_-_Author (underscore-dash-underscore) ──────────────────
    m = re.match(r"^(.+?)_-_([A-Z][a-z]+_[A-Z][a-z]+)$", name)
    if m:
        title_candidate = m.group(1).replace("_", " ")
        author_candidate = m.group(2).replace("_", " ")
        if _looks_like_person(author_candidate) and len(title_candidate) > 3:
            return {"author": author_candidate, "title": title_candidate, "year": None}

    # ── 7. Title - Author Name (dash, person-looking author required) ───
    m = re.match(r"^(.+?)\s*[-–—]\s*(.+)$", name)
    if m:
        title_candidate = m.group(1).strip()
        author_candidate = m.group(2).strip()
        # MUST look like a person, and title must NOT be empty/short
        if _looks_like_person(author_candidate) and len(title_candidate) > 5:
            # Extra guard: title shouldn't look like a person name
            if not _looks_like_person(title_candidate):
                return {"author": author_candidate, "title": title_candidate, "year": None}

    # ── 8. Title AuthorName liberN / pdfdrive / z-lib ──────────────────
    # Strategy: find the suffix, then work backwards to find the last 2-3
    # capitalized words before it that look like a person name.
    m = re.match(r"^(.+)\s+(liber\d*|pdfdrive|z-lib|ebook\d*)", name, re.IGNORECASE)
    if m:
        before_suffix = m.group(1).strip()
        words = before_suffix.split()
        # Try last 2 words, then last 3, then last 4 as author candidate
        for n in (4, 3, 2):
            if len(words) >= n + 2:  # Need at least 2 words for title
                author_candidate = " ".join(words[-n:])
                title_candidate = " ".join(words[:-n])
                if _looks_like_person(author_candidate) and len(title_candidate) > 3:
                    return {"author": author_candidate, "title": title_candidate, "year": None}

    return {"author": "", "title": "", "year": None}


def run_stage0_5(model: str = DEFAULT_MODEL, force: bool = False) -> None:
    """Main extraction loop."""
    cache_path: Path = CHECKPOINT_DIR / METADATA_CACHE
    cache: dict[str, dict] = load_cache(cache_path)

    # Find all MD files
    md_files: list[Path] = sorted(BOOKS_DIR.rglob("*.md"), key=lambda p: p.name)
    print(f"📚 Stage 0.5: Extract Author/Title — {len(md_files)} MD files")
    print(f"   Model: {model} | Cache: {len(cache)} cached")
    if force:
        print("   ⚠️  --force: re-extracting all files")

    pipeline_commit: str = get_pipeline_commit()
    extracted: int = 0
    skipped: int = 0
    heuristic: int = 0
    failed: int = 0

    for md_path in md_files:
        filename: str = md_path.name

        # Skip if cached
        if not force and filename in cache:
            skipped += 1
            continue

        # Try heuristic first (fast, no LLM cost)
        h_result: dict = parse_filename_heuristic(filename)
        if h_result["author"] and h_result["title"]:
            record: dict = {
                "source_book": filename,
                "author": h_result["author"],
                "title": h_result["title"],
                "year": h_result["year"],
                "extraction_method": "heuristic",
                "source_path": str(md_path),
            }
            record = stamp_record(record, gen_model="regex")
            record["pipeline_commit"] = pipeline_commit
            cache[filename] = record
            heuristic += 1
            print(f"   📋 {filename[:60]:60s} → {h_result['author'][:25]:25s} | {h_result['title'][:40]} [regex]")
            continue

        # LLM extraction for ambiguous filenames
        try:
            with open(md_path) as f:
                text: str = f.read(PREAMBLE_CHARS)
        except Exception as e:
            print(f"   ❌ Cannot read {filename}: {e}")
            failed += 1
            continue

        print(f"   🤖 {filename[:60]:60s} → ", end="", flush=True)
        result: Optional[dict] = extract_from_text(text, filename, model)

        if result and (result["author"] or result["title"]):
            record = {
                "source_book": filename,
                "author": result["author"],
                "title": result["title"],
                "year": result["year"],
                "extraction_method": f"llm:{model}",
                "source_path": str(md_path),
            }
            record = stamp_record(record, gen_model=model)
            record["pipeline_commit"] = pipeline_commit
            cache[filename] = record
            extracted += 1
            print(f"{result['author'][:25]:25s} | {result['title'][:40]}")
        else:
            # Fallback: use filename as title
            fallback_title: str = Path(filename).stem.replace("_", " ").replace("-", " ")
            record = {
                "source_book": filename,
                "author": "",
                "title": fallback_title,
                "year": None,
                "extraction_method": "fallback",
                "source_path": str(md_path),
            }
            record = stamp_record(record, gen_model="fallback")
            record["pipeline_commit"] = pipeline_commit
            cache[filename] = record
            failed += 1
            print(f"[FALLBACK] → {fallback_title[:60]}")

        time.sleep(BATCH_DELAY)

    # Write cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = list(cache.values())
    records.sort(key=lambda r: r["source_book"])

    with open(cache_path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {len(md_files)} files")
    print(f"   🤖 LLM extracted:  {extracted}")
    print(f"   📋 Regex/heuristic: {heuristic}")
    print(f"   ⏭️  Cached (skipped): {skipped}")
    print(f"   ❌ Fallback:        {failed}")
    print(f"📋 Cache: {cache_path}")


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Stage 0.5: Extract author/title metadata from MD book preambles"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-extract all files (ignore cache)",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"OMLX model for LLM extraction (default: {DEFAULT_MODEL})",
    )
    args: argparse.Namespace = parser.parse_args()
    run_stage0_5(model=args.model, force=args.force)


if __name__ == "__main__":
    main()
