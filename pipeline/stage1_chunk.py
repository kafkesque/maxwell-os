#!/usr/bin/env python3
"""
stage1_chunk.py — Chunk Markdown into segments with SHA-256 exact dedup.
=========================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 1)

Input:  .md files from Stage 0 checkpoint
Output: Segments with SHA-256 dedup, checkpoint at stage1_chunk.jsonl

Chunking strategy:
  1. Split on section boundaries (## headings)
  2. Further split large sections into ~300-word chunks with ~50-word overlap
  3. SHA-256 hash each chunk for exact dedup
  4. Skip boilerplate lines (headers, links, blank lines)

Usage:
    python3 pipeline/stage1_chunk.py
    python3 pipeline/stage1_chunk.py --book "some_book.md"
    python3 pipeline/stage1_chunk.py --chunk-size 400
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (
    STAGE0_CHECKPOINT,
    STAGE1_CHECKPOINT,
    CHECKPOINT_DIR,
    CHUNK_SIZE_WORDS,
    CHUNK_OVERLAP_WORDS,
)
from pipeline.stamp import stamp_record, make_hash_id, get_pipeline_commit
from pipeline.io_guard import safe_write

# ── Constants ──────────────────────────────────────────────────────────────
MIN_CHUNK_WORDS = 30  # Skip chunks shorter than this
SECTION_HEADING_RE = re.compile(r"^#{1,6}\s+")
SKIP_PATTERNS = [
    re.compile(r"^```"),           # code fence
    re.compile(r"^---"),           # horizontal rule
    re.compile(r"^!\[.*\]\(.*\)$"),  # image
    re.compile(r"^\s*$"),          # blank line
    re.compile(r"^\s*\d+[.\)]\s"),  # numbered list (may contain content, but skip standalone)
]
SKIP_WORDS = {"twitter", "x.com", "instagram", "facebook", "subscribe", "newsletter",
              "copyright", "disclaimer", "all rights reserved"}


def clean_line(line: str) -> str | None:
    """Clean a single line. Returns None if it should be skipped."""
    stripped = line.strip()
    if not stripped:
        return None
    if len(stripped) < 15:
        return None
    for pattern in SKIP_PATTERNS:
        if pattern.match(stripped):
            return None
    # Skip lines with >30% skip words
    words = stripped.lower().split()
    if not words:
        return None
    skip_count = sum(1 for w in words if w in SKIP_WORDS)
    if skip_count > len(words) * 0.3:
        return None
    return stripped


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_WORDS,
               overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """Split text into overlapping chunks of approximately chunk_size words."""
    paragraphs = text.split("\n\n")
    # If only one paragraph (no \n\n found), use word-based sliding window
    if len(paragraphs) <= 1:
        words = text.split()
        if len(words) <= chunk_size:
            return [text] if len(words) >= MIN_CHUNK_WORDS else []
        chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunks.append(" ".join(chunk_words))
            i += max(chunk_size - overlap, 1)
        return chunks
    chunks = []
    current_words: list[str] = []
    current_chars = 0

    for para in paragraphs:
        cleaned = clean_line(para)
        if cleaned is None:
            continue
        para_words = cleaned.split()
        if len(para_words) + len(current_words) > chunk_size and current_words:
            chunk_text = " ".join(current_words)
            chunks.append(chunk_text)
            # Keep overlap words
            if overlap > 0:
                overlap_words = current_words[-overlap:] if len(current_words) > overlap else current_words
                current_words = overlap_words[:]
            else:
                current_words = []
        current_words.extend(para_words)
        current_chars += len(cleaned)

    # Final chunk
    if len(current_words) >= MIN_CHUNK_WORDS:
        chunks.append(" ".join(current_words))

    return chunks


def split_on_headings(text: str) -> list[tuple[str, str, str]]:
    """Split markdown on ## headings. Returns [(heading, section_text, section_title)].

    Also handles # (H1) and ### (H3+) as section boundaries.
    """
    lines = text.split("\n")
    sections = []
    current_heading = ""
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if SECTION_HEADING_RE.match(line):
            # Save previous section
            if current_lines:
                body = "\n".join(current_lines)
                sections.append((current_heading, body, current_title))
            current_heading = line.strip()
            current_title = line.lstrip("#").strip()
            current_lines = []
        else:
            cleaned = clean_line(line)
            if cleaned:
                current_lines.append(cleaned)

    # Last section
    if current_lines:
        body = "\n".join(current_lines)
        sections.append((current_heading, body, current_title))

    return sections


def load_stage0_md_files() -> list[dict]:
    """Load successfully converted .md files from Stage 0 checkpoint."""
    if not STAGE0_CHECKPOINT.exists():
        print("❌ Stage 0 checkpoint not found. Run stage0_convert.py first.")
        sys.exit(1)

    md_files = []
    with open(STAGE0_CHECKPOINT) as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                md_path = Path(rec.get("output_path", ""))
                if md_path.exists() and md_path.suffix == ".md":
                    md_files.append(rec)
    return md_files


def run_stage1(chunk_size: int = CHUNK_SIZE_WORDS,
               overlap: int = CHUNK_OVERLAP_WORDS,
               single_book: str = None):
    """Run Stage 1: Chunk all .md files into segments."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    md_files = load_stage0_md_files()
    if single_book:
        md_files = [r for r in md_files if single_book in r.get("source_file", "")]
        if not md_files:
            print(f"❌ Book not found in Stage 0 output: {single_book}")
            sys.exit(1)

    print(f"📝 Stage 1: Chunk — {len(md_files)} markdown files")
    print(f"{'='*60}")

    seen_hashes: set[str] = set()
    all_segments: list[dict] = []
    total_chunks = 0
    skipped_chunks = 0

    pipeline_commit = get_pipeline_commit()

    for i, rec in enumerate(md_files, 1):
        md_path = Path(rec["output_path"])
        book_name = rec["source_file"]
        print(f"  [{i}/{len(md_files)}] {book_name}", end=" ")

        start = time.time()
        try:
            with open(md_path, encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"→ ❌ Read error: {e}")
            continue

        # Split on headings, then chunk each section
        sections = split_on_headings(text)
        book_chunks = []

        for heading, body, title in sections:
            if not body.strip():
                continue
            # For short sections, keep as single chunk
            body_words = body.split()
            if len(body_words) <= chunk_size:
                short_chunk = body.strip()
                if len(body_words) >= MIN_CHUNK_WORDS:
                    book_chunks.append((short_chunk, heading, title))
            else:
                # Split large sections into overlapping chunks
                for c in chunk_text(body, chunk_size=chunk_size, overlap=overlap):
                    book_chunks.append((c, heading, title))

        # Create segments with SHA-256 dedup
        book_segments = 0
        for chunk_body, heading, title in book_chunks:
            segment_id = make_hash_id(chunk_body)
            if segment_id in seen_hashes:
                skipped_chunks += 1
                continue
            seen_hashes.add(segment_id)

            seg = {
                "segment_id": segment_id,
                "text": chunk_body,
                "source_book": book_name,
                "source_path": str(md_path),
                "section_title": title,
                "section_heading": heading,
                "word_count": len(chunk_body.split()),
            }
            seg = stamp_record(seg, gen_model="python")
            seg["pipeline_commit"] = pipeline_commit
            all_segments.append(seg)
            book_segments += 1

        elapsed = time.time() - start
        total_chunks += book_segments
        print(f"→ {book_segments} chunks ({elapsed:.1f}s)")

    # Write checkpoint
    safe_write(
        STAGE1_CHECKPOINT,
        "\n".join(json.dumps(s, ensure_ascii=False) for s in all_segments) + "\n",
    )

    # Summary
    unique_hashes = len(set(s["segment_id"] for s in all_segments))
    print(f"\n{'='*60}")
    print(f"✅ Total segments:  {len(all_segments)}")
    print(f"🔑 Unique hashes:   {unique_hashes}")
    print(f"🗑️  Duplicates:      {skipped_chunks}")
    print(f"📋 Checkpoint:      {STAGE1_CHECKPOINT}")


def main():
    parser = argparse.ArgumentParser(description="Stage 1: Chunk Markdown → Segments")
    parser.add_argument("--book", help="Process a single book (by source filename)")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE_WORDS,
                        help=f"Target chunk size in words (default: {CHUNK_SIZE_WORDS})")
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP_WORDS,
                        help=f"Overlap in words (default: {CHUNK_OVERLAP_WORDS})")
    args = parser.parse_args()

    run_stage1(chunk_size=args.chunk_size, overlap=args.overlap, single_book=args.book)


if __name__ == "__main__":
    main()
