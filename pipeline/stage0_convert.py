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
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write  # D2332 fail-closed read + D2487 atomic write
from pipeline.pipeline_paths import (
    BOOKS_DIR,
    CHECKPOINT_DIR,
    S0_MAX_FAILED_RATIO,
    SMOKE_BOOK_LIMIT,
    STAGE0_CHECKPOINT,
)
from pipeline.stamp import get_pipeline_commit, stamp_record
from pipeline.text_cleaner import check_conversion_quality

# ── Constants ──────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".epub", ".pdf", ".md"}  # .md = already converted
MD_EXTENSION = ".md"


def find_books(books_dir: Path, subdir: str | None = None) -> list[Path]:
    """Find all supported files recursively in the books directory.

    Args:
        books_dir: Root books directory.
        subdir: Optional relative subdirectory to restrict the search (D2316:
            domain-coherent e2e sampling — avoids the alphabetical grab-bag that
            produced 3% convergence).
    """
    search_root = books_dir / subdir if subdir else books_dir
    if subdir and not search_root.is_dir():
        return []
    books = []
    for ext in SUPPORTED_EXTENSIONS:
        books.extend(search_root.rglob(f"*{ext}"))
    return sorted(books, key=lambda p: p.name)


def convert_epub(epub_path: Path, output_path: Path) -> bool:
    """Convert EPUB to Markdown using Pandoc."""
    try:
        result = subprocess.run(
            [
                "pandoc",
                str(epub_path),
                "-t",
                "markdown",
                "--wrap=none",
                "-o",
                str(output_path),
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
    except FileNotFoundError as e:
        print(f"  ⚠️  Docling not found ({e}) — falling back to Pandoc for PDF (C16)", file=sys.stderr)
    except subprocess.TimeoutExpired as e:
        print(f"  ⚠️  Docling timed out after {e.timeout}s — falling back to Pandoc for PDF (C16)", file=sys.stderr)

    # Fallback to Pandoc
    print("  ℹ️  Docling not available, trying Pandoc for PDF...")
    try:
        result = subprocess.run(
            [
                "pandoc",
                str(pdf_path),
                "-t",
                "markdown",
                "--wrap=none",
                "-o",
                str(output_path),
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
    """Load already-converted books from checkpoint (fail-closed, D2332).

    Previously swallowed json.JSONDecodeError — a truncated/corrupt S0 line was
    silently skipped, dropping that book from the resume set (C16 violation).
    load_jsonl raises on any unparseable non-empty line so a corrupt checkpoint
    is loud, not silent.
    """
    existing: dict[str, dict] = {}
    if STAGE0_CHECKPOINT.exists():
        for rec in load_jsonl(STAGE0_CHECKPOINT, context="S0 checkpoint"):
            src = rec.get("source_file")
            if src:
                existing[src] = rec
    return existing


def run_stage0(
    books_dir: Path = None, force: bool = False, single_book: str = None, limit: int = None
):
    """Run Stage 0: Convert all books to Markdown.

    Args:
        books_dir: Directory containing source books.
        force: Reconvert already-converted books.
        single_book: Convert only the named book.
        limit: Maximum number of books to process (applied after finding all books).
               If None and MAXWELL_RUN_ID=smoke, defaults to 3.
    """
    if books_dir is None:
        books_dir = BOOKS_DIR

    # ── Auto-limit for smoke tests + runner --books flag ────────────────
    if limit is None:
        if os.environ.get("MAXWELL_RUN_ID") == "smoke":
            limit = SMOKE_BOOK_LIMIT
        else:
            env_limit = os.environ.get("MAXWELL_BOOK_LIMIT", "")
            if env_limit.isdigit():
                limit = int(env_limit)

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
        # D2316: domain-coherent sampling — restrict to a subdirectory when
        # MAXWELL_BOOK_SUBDIR is set (e.g. e2e test).
        subdir = os.environ.get("MAXWELL_BOOK_SUBDIR", "").strip() or None
        books = find_books(books_dir, subdir=subdir)

    # ── Apply limit ─────────────────────────────────────────────────────
    if limit is not None and limit > 0:
        books = books[:limit]

    if not books:
        print("📭 No EPUB or PDF files found in books/")
        return

    print(f"📚 Stage 0: Convert — {len(books)} books found")
    if limit:
        print(f"   (limited to first {limit})")
    print(f"{'=' * 60}")

    # ── Checkpoint handling ──────────────────────────────────────────────
    # When a limit is active (e.g. smoke test), don't load accumulated
    # checkpoints from prior full runs — they pollute the limited run.
    if limit is not None and limit > 0 and not force:
        existing = {}  # Fresh checkpoint for limited runs
    else:
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
                rec = stamp_record(
                    {
                        "source_file": book_path.name,
                        "source_path": str(book_path),
                        "output_path": str(md_path),
                        "format": "md",
                        "sha256": sha,
                        "size_kb": round(size_kb, 1),
                        "elapsed_s": 0.0,
                    },
                    gen_model="pandoc/docling",
                )
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
            # ── H4: Post-conversion quality check (D2326: tri-state, never silent) ──
            quality_warnings = []
            quality_status = "passed"
            try:
                with open(md_path, encoding="utf-8") as _qf:
                    q_result = check_conversion_quality(_qf.read(), book_path.name)
                if not q_result["ok"]:
                    print(f"→ ⚠️  {q_result['error']}")
                    quality_warnings.append(q_result["error"])
                    quality_status = "failed"
                for w in q_result.get("warnings", []):
                    print(f"   ⚠️  {w}")
                    quality_warnings.append(w)
            except Exception as e:
                # D2326/C16: the checker is a verification step, not best-effort —
                # a broken checker is indistinguishable from success unless recorded.
                quality_status = "unavailable"
                msg = f"quality check raised: {type(e).__name__}: {e}"
                quality_warnings.append(msg)
                print(f"   ⚠️  {msg}")

            rec = stamp_record(
                {
                    "source_file": book_path.name,
                    "source_path": str(book_path),
                    "output_path": str(md_path),
                    "format": ext,
                    "sha256": sha,
                    "size_kb": round(size_kb, 1),
                    "elapsed_s": round(elapsed, 1),
                    "quality_warnings": quality_warnings,
                    "quality_status": quality_status,
                },
                gen_model="pandoc/docling",
            )
            rec["pipeline_commit"] = pipeline_commit
            converted.append(rec)
            print(f"→ ✅ {size_kb:.0f}KB ({elapsed:.1f}s)")
        else:
            failed.append({"file": book_path.name, "format": ext})
            print("→ ❌ Failed")

    # Write checkpoint
    all_records = list(existing.values()) + converted
    safe_write(
        STAGE0_CHECKPOINT,
        "\n".join(json.dumps(r, ensure_ascii=False) for r in all_records) + "\n",
    )

    # Summary
    print(f"\n{'=' * 60}")
    print(f"✅ Converted: {len(converted)}")
    print(f"⏭️  Skipped:   {skipped}")
    print(f"❌ Failed:    {len(failed)}")
    if failed:
        for f in failed:
            print(f"     - {f['file']}")
    print(f"📋 Checkpoint: {STAGE0_CHECKPOINT}")

    # D2326: fail-closed ingestion — a failed conversion must not look like success.
    # Return (failed_count, converted_count) so the caller (main) can enforce the
    # config-defined tolerance stage0.max_failed_ratio.
    return len(failed), len(converted)


def main():
    parser = argparse.ArgumentParser(description="Stage 0: Convert EPUB/PDF → Markdown")
    parser.add_argument("--book", help="Convert a single book (filename only)")
    parser.add_argument("--force", action="store_true", help="Reconvert already-converted books")
    parser.add_argument("--books-dir", help="Override books directory")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max books to process (auto: 3 when MAXWELL_RUN_ID=smoke)",
    )
    args = parser.parse_args()

    books_dir = Path(args.books_dir) if args.books_dir else BOOKS_DIR
    result = run_stage0(books_dir=books_dir, force=args.force, single_book=args.book, limit=args.limit)

    # D2326: fail-closed — exit non-zero when the conversion failure ratio exceeds
    # the operator-approved tolerance (config stage0.max_failed_ratio).
    if result is None:
        sys.exit(0)  # no books found — nothing to do, not a failure
    failed_count, converted_count = result
    total_attempted = failed_count + converted_count
    if total_attempted == 0:
        sys.exit(0)
    failure_ratio = failed_count / total_attempted
    if failure_ratio > S0_MAX_FAILED_RATIO:
        print(
            f"❌ Stage 0 FAILED: {failed_count}/{total_attempted} book(s) failed conversion "
            f"({failure_ratio:.1%} > max_failed_ratio={S0_MAX_FAILED_RATIO})"
        )
        sys.exit(1)
    if failed_count > 0:
        print(f"⚠️  Stage 0: {failed_count} book(s) failed — within operator tolerance ({failure_ratio:.1%} ≤ {S0_MAX_FAILED_RATIO})")


if __name__ == "__main__":
    main()
