#!/usr/bin/env python3
"""
stage0_convert.py — Convert EPUB/PDF to Markdown via Pandoc/Docling.
====================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 0)

Input:  EPUB/PDF files from books/ directory
Output: Clean .md files, checkpoint at data/checkpoints/stage0_convert.jsonl

Uses Pandoc for EPUB, Docling for PDF. Falls back to Pandoc for PDF
if Docling is not installed.

Usage:
    python3 pipeline/stage0_convert.py                          # Convert all books
    python3 pipeline/stage0_convert.py --book "some_book.epub"  # Convert single book
    python3 pipeline/stage0_convert.py --force                  # Reconvert existing
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    BOOKS_DIR,
    STAGE0_CHECKPOINT,
    CHECKPOINT_DIR,
    SCHEMA_VERSION,
)
from pipeline.stamp import stamp_record, get_pipeline_commit
from pipeline.io_guard import safe_write

# ── Constants ──────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".epub", ".pdf", ".md"}  # .md = already converted
MD_EXTENSION = ".md"


def find_books(books_dir: Path) -> list[Path]:
    """Find all EPUB and PDF files recursively in the books directory."""
    books = []
    for ext in SUPPORTED_EXTENSIONS:
        books.extend(books_dir.rglob(f"*{ext}"))
    return sorted(books, key=lambda p: p.name)


def convert_epub(epub_path: Path, output_path: Path) -> bool:
    """Convert EPUB to Markdown using Pandoc."""
    try:
        result = subprocess.run(
            [
                "pandoc",
                str(epub_path),
                "-t", "markdown",
                "--wrap=none",
                "-o", str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  ⚠️  Pandoc error: {result.stderr[:200]}")
            return False
        return output_path.exists() and output_path.stat().st_size > 100
    except FileNotFoundError:
        print("  ❌ Pandoc not found. Install with: brew install pandoc")
        return False
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Pandoc timeout on {epub_path.name}")
        return False


def convert_pdf(pdf_path: Path, output_path: Path) -> bool:
    """Convert PDF to Markdown. Tries Docling first, falls back to Pandoc."""
    # Try Docling first
    try:
        result = subprocess.run(
            ["docling", str(pdf_path), "--to", "md", "--output", str(output_path.parent)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            # Docling output name may differ — find it
            docling_output = output_path.parent / f"{pdf_path.stem}.md"
            if docling_output.exists():
                if docling_output != output_path:
                    docling_output.rename(output_path)
                return True
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    # Fallback to Pandoc
    print(f"  ℹ️  Docling not available, trying Pandoc for PDF...")
    try:
        result = subprocess.run(
            [
                "pandoc",
                str(pdf_path),
                "-t", "markdown",
                "--wrap=none",
                "-o", str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  ⚠️  Pandoc error: {result.stderr[:200]}")
            return False
        return output_path.exists() and output_path.stat().st_size > 100
    except FileNotFoundError:
        print("  ❌ Neither Docling nor Pandoc found for PDF conversion")
        return False


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def load_existing_checkpoint() -> dict[str, dict]:
    """Load already-converted books from checkpoint."""
    existing = {}
    if STAGE0_CHECKPOINT.exists():
        with open(STAGE0_CHECKPOINT) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        existing[rec["source_file"]] = rec
                    except json.JSONDecodeError:
                        continue
    return existing


def run_stage0(books_dir: Path = None, force: bool = False, single_book: str = None):
    """Run Stage 0: Convert all books to Markdown."""
    if books_dir is None:
        books_dir = BOOKS_DIR

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # Find books
    if single_book:
        book_path = books_dir / single_book
        if not book_path.exists():
            # Try recursive search
            candidates = list(books_dir.rglob(single_book))
            if candidates:
                book_path = candidates[0]
            else:
                print(f"❌ Book not found: {single_book}")
                sys.exit(1)
        books = [book_path]
    else:
        books = find_books(books_dir)

    if not books:
        print("📭 No EPUB or PDF files found in books/")
        return

    print(f"📚 Stage 0: Convert — {len(books)} books found")
    print(f"{'='*60}")

    existing = load_existing_checkpoint() if not force else {}
    converted = []
    failed = []
    skipped = 0

    pipeline_commit = get_pipeline_commit()

    for i, book_path in enumerate(books, 1):
        book_key = book_path.name
        if book_key in existing and not force:
            skipped += 1
            continue

        ext = book_path.suffix.lower()
        md_dir = book_path.parent
        md_path = md_dir / f"{book_path.stem}.md"

        print(f"  [{i}/{len(books)}] {book_path.name} ({ext})", end=" ")

        # .md books are already converted — just record them
        if ext == ".md":
            md_path = book_path
            if book_path.stat().st_size > 100:
                sha = compute_sha256(book_path)
                size_kb = book_path.stat().st_size / 1024
                rec = stamp_record({
                    "source_file": book_path.name,
                    "source_path": str(book_path),
                    "output_path": str(md_path),
                    "format": "md",
                    "sha256": sha,
                    "size_kb": round(size_kb, 1),
                    "elapsed_s": 0.0,
                }, gen_model="pandoc/docling")
                rec["pipeline_commit"] = pipeline_commit
                converted.append(rec)
                print(f"→ ✅ {size_kb:.0f}KB (native MD)")
            else:
                print(f"→ ⏭️  Too small ({book_path.stat().st_size} bytes)")
            continue

        start = time.time()
        if ext == ".epub":
            success = convert_epub(book_path, md_path)
        elif ext == ".pdf":
            success = convert_pdf(book_path, md_path)
        else:
            print("→ ⏭️  Unsupported format")
            continue

        elapsed = time.time() - start

        if success:
            size_kb = md_path.stat().st_size / 1024
            sha = compute_sha256(md_path)
            rec = stamp_record({
                "source_file": book_path.name,
                "source_path": str(book_path),
                "output_path": str(md_path),
                "format": ext,
                "sha256": sha,
                "size_kb": round(size_kb, 1),
                "elapsed_s": round(elapsed, 1),
            }, gen_model="pandoc/docling")
            rec["pipeline_commit"] = pipeline_commit
            converted.append(rec)
            print(f"→ ✅ {size_kb:.0f}KB ({elapsed:.1f}s)")
        else:
            failed.append({"file": book_path.name, "format": ext})
            print(f"→ ❌ Failed")

    # Write checkpoint
    all_records = list(existing.values()) + converted
    safe_write(
        STAGE0_CHECKPOINT,
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_records) + "\n",
    )

    # Summary
    print(f"\n{'='*60}")
    print(f"✅ Converted: {len(converted)}")
    print(f"⏭️  Skipped:   {skipped}")
    print(f"❌ Failed:    {len(failed)}")
    if failed:
        for f in failed:
            print(f"     - {f['file']}")
    print(f"📋 Checkpoint: {STAGE0_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(description="Stage 0: Convert EPUB/PDF → Markdown")
    parser.add_argument("--book", help="Convert a single book (filename only)")
    parser.add_argument("--force", action="store_true", help="Reconvert already-converted books")
    parser.add_argument("--books-dir", help="Override books directory")
    args = parser.parse_args()

    books_dir = Path(args.books_dir) if args.books_dir else BOOKS_DIR
    run_stage0(books_dir=books_dir, force=args.force, single_book=args.book)


if __name__ == "__main__":
    main()
