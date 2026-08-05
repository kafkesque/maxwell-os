#!/usr/bin/env python3
"""
batch_convert_epubs.py — Re-convert all 505 EPUBs via Pandoc, overwriting pipeline MDs.
========================================================================================
Authority: D2134

For each EPUB in education/books/epub/:
  1. Find matching MD in knowledge pipeline/books/
  2. Convert EPUB → MD via pypandoc (Pandoc 3.9)
  3. Overwrite the existing MD (crash-safe: tempfile → fsync → os.replace per C6)
  4. Skip if no matching MD exists

Usage:
    python3 pipeline/batch_convert_epubs.py --dry-run     # Show what would change
    python3 pipeline/batch_convert_epubs.py --max 10       # Convert up to 10
    python3 pipeline/batch_convert_epubs.py                # Convert all 505
"""

import argparse, os, re, sys, tempfile, time
from pathlib import Path

import pypandoc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.pipeline_paths import SOURCE_EPUB_DIR, SOURCE_PDF_DIR, BOOKS_DIR

EPUB_BASE = SOURCE_EPUB_DIR
MD_BASE = Path("knowledge pipeline/books")


def find_matching_md(epub_path: Path) -> Path | None:
    """Find the matching MD file in the pipeline books directory by filename stem."""
    md_name = epub_path.stem + ".md"
    # Search recursively in MD_BASE
    for md_path in MD_BASE.rglob(md_name):
        return md_path
    return None


def count_headers(text: str) -> dict:
    """Count headers in text."""
    lines = text.split('\n')
    return {
        'h1': sum(1 for l in lines if re.match(r'^#\s+\S', l)),
        'h2': sum(1 for l in lines if re.match(r'^##\s+\S', l)),
        'h3': sum(1 for l in lines if re.match(r'^###\s+\S', l)),
        'chars': len(text),
    }


def convert_epub(epub_path: Path) -> str | None:
    """Convert EPUB to clean Markdown via pypandoc."""
    try:
        md_text = pypandoc.convert_file(
            str(epub_path), 'markdown',
            extra_args=['--wrap=none', '--from=epub']
        )
        return md_text
    except Exception as e:
        print(f"    ❌ pypandoc error: {e}")
        return None


def clean_pandoc_output(text: str) -> str:
    """Strip Pandoc noise: SVG blocks, empty front matter, cover images."""
    lines = text.split('\n')
    cleaned = []
    skip_svg = False
    for line in lines:
        stripped = line.strip()
        
        # Skip SVG blocks
        if '<svg' in stripped.lower() or 'viewbox=' in stripped.lower():
            skip_svg = True
            continue
        if skip_svg:
            if '</svg>' in stripped.lower() or stripped == '```':
                skip_svg = False
            continue
        
        # Skip cover image references
        if re.match(r'^!\[\]\(cover', stripped):
            continue
        
        # Skip empty anchor tags
        if re.match(r'^\[\]{#', stripped):
            continue
        
        # Skip raw HTML div wrappers
        if re.match(r'^:::\s*\{', stripped):
            continue
        if stripped == ':::':
            continue
        
        cleaned.append(line)
    
    return '\n'.join(cleaned)


def crash_safe_write(path: Path, content: str) -> None:
    """C6: tempfile → fsync → os.replace."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, prefix='.tmp_', suffix='.md')
    try:
        with os.fdopen(tmp_fd, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Batch re-convert EPUBs to MD via Pandoc")
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max', type=int, default=0, help='Max books to convert')
    args = parser.parse_args()
    
    # Find all EPUBs
    epubs = list(EPUB_BASE.rglob("*.epub"))
    print(f"📚 Found {len(epubs)} EPUBs")
    
    # Find matching MDs
    matched = []
    unmatched = []
    for ep in epubs:
        md = find_matching_md(ep)
        if md:
            matched.append((ep, md))
        else:
            unmatched.append(ep)
    
    print(f"   With matching MD: {len(matched)}")
    print(f"   No matching MD:   {len(unmatched)}")
    
    if args.max > 0:
        matched = matched[:args.max]
    
    mode = "DRY RUN" if args.dry_run else "CONVERTING"
    print(f"\n🔄 {mode}: {len(matched)} books")
    print(f"{'='*70}")
    
    converted = 0
    skipped = 0
    failed = 0
    total_headers_before = 0
    total_headers_after = 0
    
    for i, (epub_path, md_path) in enumerate(matched):
        epub_size = epub_path.stat().st_size
        name = epub_path.name[:70]
        
        # Read existing MD stats
        try:
            old_text = md_path.read_text(errors='replace')
        except:
            old_text = ""
        before = count_headers(old_text)
        
        # Convert
        pandoc_text = convert_epub(epub_path)
        if pandoc_text is None:
            failed += 1
            print(f"  ❌ [{i+1}/{len(matched)}] FAILED: {name}")
            continue
        
        # Clean
        cleaned = clean_pandoc_output(pandoc_text)
        after = count_headers(cleaned)
        
        # Quality check: did we get meaningful headers?
        total_h_before = before['h1'] + before['h2'] + before['h3']
        total_h_after = after['h1'] + after['h2'] + after['h3']
        
        # Reject if Pandoc output is clearly worse (much smaller, fewer headers)
        if after['chars'] < before['chars'] * 0.3 and total_h_after <= total_h_before:
            print(f"  ⚠️  [{i+1}/{len(matched)}] DEGRADED: {name} ({before['chars']:,}→{after['chars']:,}c, h#{total_h_before}→{total_h_after})")
            skipped += 1
            continue
        
        if not args.dry_run:
            crash_safe_write(md_path, cleaned)
        
        h_delta = total_h_after - total_h_before
        flag = "✅" if h_delta > 5 else "📈" if h_delta > 0 else "➡️"
        print(f"  {flag} [{i+1}/{len(matched)}] {epub_size/1e6:.1f}MB | "
              f"h#{total_h_before}→{total_h_after} (+{h_delta}) | "
              f"{before['chars']:,}→{after['chars']:,}c | {name[:45]}")
        
        converted += 1
        total_headers_before += total_h_before
        total_headers_after += total_h_after
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 SUMMARY")
    print(f"   Converted: {converted}")
    print(f"   Skipped (degraded): {skipped}")
    print(f"   Failed: {failed}")
    if converted > 0:
        print(f"   Total headers: {total_headers_before} → {total_headers_after} (+{total_headers_after - total_headers_before})")
        print(f"   Avg headers/book: {total_headers_before/converted:.0f} → {total_headers_after/converted:.0f}")
    
    if args.dry_run:
        print(f"\n   Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
