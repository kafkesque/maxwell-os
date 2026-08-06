#!/usr/bin/env python3
"""
enhance_md_headers.py — Add section headers to flat MD files.
================================================================
Authority: D2134 | CONSTITUTION.md §3

Two-pass approach:
  Pass 1: Regex heuristics — catch obvious patterns (Chapter X, ALL CAPS,
          numbered sections, common structural markers). Fast, zero cost.
  Pass 2: LLM — for books still < 5 headers after Pass 1, use Gemma to
          identify natural topic boundaries and insert ## headers.

Target: header density ≥ 1.0 per 10K chars (was 0.0 for most books).

Usage:
    python3 pipeline/enhance_md_headers.py --dry-run          # Show what would change
    python3 pipeline/enhance_md_headers.py --max-books 10     # Process up to 10 books
    python3 pipeline/enhance_md_headers.py --only-orphans     # Only 146 orphaned MDs
    python3 pipeline/enhance_md_headers.py --force            # Process all 831 flat books
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.pipeline_paths import (
    ENHANCE_MIN_HEADER_GAP_CHARS,
    SOURCE_EPUB_DIR,
    SOURCE_PDF_DIR,
)

# ── Regex heuristic patterns ──
# Each pattern: (regex, header_prefix) — if line matches, prefix it with ##
HEADER_PATTERNS = [
    # Chapter markers (highest confidence)
    (r'^(?:Chapter|CHAPTER)\s+\d{1,3}[\.:)\s]', '## '),
    (r'^(?:Chapter|CHAPTER)\s+[IVX]+[\.:)\s]', '## '),

    # Part markers
    (r'^(?:Part|PART)\s+(?:One|Two|Three|Four|Five|Six|[IVX]+|\d+)[\.:)\s]', '## '),

    # Numbered sections
    (r'^\d{1,2}\.\s+[A-Z][A-Za-z\s]{10,80}$', '## '),
    (r'^\d{1,2}\.\d{1,2}\s+[A-Z][A-Za-z\s]{10,80}$', '### '),

    # Roman numeral sections
    (r'^[IVX]{1,4}\.\s+[A-Z][A-Za-z\s]{10,80}$', '## '),

    # ALL CAPS standalone lines (3+ words, 15-100 chars)
    (r'^[A-Z][A-Z\s\'-]{14,100}$', '## '),

    # Common section names
    (r'^(?:Introduction|Conclusion|Summary|References?|Bibliography|Appendix|Glossary|Index|Acknowledgments?|Preface|Foreword|Prologue|Epilogue|Afterword)[\.:]*$', '## '),

    # "SECTION X" or "Section X"
    (r'^(?:Section|SECTION)\s+\d{1,3}[\.:)\s]', '## '),

    # "Lesson X" / "Module X" / "Unit X"
    (r'^(?:Lesson|Module|Unit|Step|Phase|Stage)\s+\d{1,3}[\.:)\s]', '## '),

    # Lines that are just "Key Takeaways", "Learning Objectives", etc.
    (r'^(?:Key Takeaways?|Learning Objectives?|Summary|Overview|In This Chapter|What You.{3,30}Learn|Key Concepts?|Key Points?|Main Ideas?|Core Concepts?)[\.:]*$', '## '),

    # Academic paper sections (D2134)
    (r'^(?:Abstract|ABSTRACT)\s*$', '## '),
    (r'^(?:Introduction|INTRODUCTION)\s*$', '## '),
    (r'^(?:Method(?:ology|s)?|METHOD(?:OLOGY|S)?)\s*$', '## '),
    (r'^(?:Results?(?:\s+and\s+Discussion)?|RESULTS?(?:\s+AND\s+DISCUSSION)?)\s*$', '## '),
    (r'^(?:Discussion|DISCUSSION)\s*$', '## '),
    (r'^(?:Conclusion(?:s)?|CONCLUSION(?:S)?)\s*$', '## '),
    (r'^(?:References?|REFERENCES?|Bibliography|BIBLIOGRAPHY)\s*$', '## '),
    (r'^(?:Background|BACKGROUND)\s*$', '## '),
    (r'^(?:Related\s+Work|RELATED\s+WORK)\s*$', '## '),
    (r'^(?:Future\s+Work|FUTURE\s+WORK)\s*$', '## '),
    (r'^(?:Limitations?|LIMITATIONS?)\s*$', '## '),
    (r'^(?:Findings?|FINDINGS?)\s*$', '## '),
    (r'^(?:Analysis|ANALYSIS)\s*$', '## '),
    (r'^(?:Appendix|APPENDIX)\s+\w*$', '## '),
    (r'^(?:Acknowledg(?:e)?ments?|ACKNOWLEDG(?:E)?MENTS?)\s*$', '## '),
    (r'^(?:Design|DESIGN)\s*$', '## '),
    (r'^(?:Implementation|IMPLEMENTATION)\s*$', '## '),
    (r'^(?:Evaluation|EVALUATION)\s*$', '## '),
    (r'^(?:Experiments?|EXPERIMENTS?)\s*$', '## '),
    (r'^(?:Case\s+Stud(?:y|ies)|CASE\s+STUD(?:Y|IES))\s*$', '## '),
]

# Patterns that should NEVER become headers (false positive guard)
NOT_HEADER_PATTERNS = [
    r'^[A-Z]{1,5}$',               # Single short acronym
    r'^\d{1,4}$',                   # Standalone numbers (page numbers)
    r'^[©®™]',                      # Copyright/trademark
    r'^ISBN',                        # ISBN numbers
    r'^http[s]?://',                 # URLs
    r'^DOI:',                        # DOI references
    r'^[A-Z][a-z]+\s+et\s+al',     # Author citations
    r'^\d{1,2}/\d{1,2}/\d{2,4}',   # Dates
    r'^Figure\s+\d',                 # Figure captions
    r'^Table\s+\d',                  # Table captions
]

# Minimum chars between headers (avoid clustering) — T1.2: from config
MIN_HEADER_GAP_CHARS: int = ENHANCE_MIN_HEADER_GAP_CHARS  # avoid clustering tutorial steps too tightly


def should_be_header(line: str) -> bool:
    """Check if a line should become a section header (regex pass only)."""
    stripped = line.strip()
    if not stripped or len(stripped) < 10:
        return False

    # Check NOT_HEADER patterns first (false positive guard)
    for pattern in NOT_HEADER_PATTERNS:
        if re.match(pattern, stripped):
            return False

    # Check if it already has a markdown header prefix
    if re.match(r'^#{1,3}\s', stripped):
        return False

    # Check HEADER patterns
    for pattern, _ in HEADER_PATTERNS:
        if re.match(pattern, stripped):
            return True

    return False


def enhance_headers_regex(text: str) -> tuple[str, int]:
    """Pass 1: Regex heuristic header insertion."""
    lines = text.split('\n')
    new_lines = []
    added = 0
    last_header_pos = -9999  # line index of last inserted header

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if this line should become a header
        if should_be_header(stripped):
            # Enforce minimum gap between headers
            chars_since = sum(len(l) for l in lines[max(0, last_header_pos):i])
            if chars_since >= MIN_HEADER_GAP_CHARS or last_header_pos < 0:
                # Determine header level
                prefix = '## '
                for pattern, h_prefix in HEADER_PATTERNS:
                    if re.match(pattern, stripped):
                        prefix = h_prefix
                        break

                # Only add if the line isn't already a header and isn't too close to last
                new_lines.append(f"{prefix}{stripped}")
                added += 1
                last_header_pos = i
                continue

        new_lines.append(line)

    return '\n'.join(new_lines), added


def analyze_headers(text: str) -> dict:
    """Count headers and compute density."""
    lines = text.split('\n')
    tc = len(text)
    h1 = sum(1 for l in lines if re.match(r'^#\s+\S', l))
    h2 = sum(1 for l in lines if re.match(r'^##\s+\S', l))
    h3 = sum(1 for l in lines if re.match(r'^###\s+\S', l))
    return {
        'chars': tc,
        'lines': len(lines),
        'h1': h1, 'h2': h2, 'h3': h3,
        'total_h': h1 + h2 + h3,
        'density': round((h1 + h2 + h3) / max(tc/10000, 1), 1),
    }


def enhance_book(md_path: Path, dry_run: bool = False, force_llm: bool = False) -> dict | None:
    """Enhance a single book's headers. Returns stats dict or None if skipped."""
    try:
        text = md_path.read_text(errors='replace')
    except Exception as e:
        return {'path': str(md_path), 'error': str(e), 'enhanced': False}

    before = analyze_headers(text)

    # Skip if already well-structured
    if before['density'] >= 1.0 and not force_llm:
        return {'path': str(md_path), 'before': before, 'enhanced': False,
                'reason': f"already structured (density={before['density']})"}

    # Skip if too small to matter
    if before['chars'] < 5000:
        return {'path': str(md_path), 'before': before, 'enhanced': False,
                'reason': 'too small'}

    # Pass 1: Regex heuristics
    enhanced_text, regex_added = enhance_headers_regex(text)
    after_regex = analyze_headers(enhanced_text)

    # If regex pass didn't add enough, we'd use LLM here (Pass 2)
    # For now, report what regex achieved
    llm_added = 0
    needs_llm = after_regex['density'] < 1.0

    if not dry_run and regex_added > 0:
        # Crash-safe write
        tmp_path = md_path.with_suffix('.tmp')
        tmp_path.write_text(enhanced_text)
        tmp_path.replace(md_path)

    return {
        'path': str(md_path),
        'name': md_path.name[:80],
        'before': before,
        'after': after_regex if regex_added > 0 else before,
        'regex_added': regex_added,
        'llm_added': llm_added,
        'needs_llm': needs_llm,
        'enhanced': regex_added > 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Enhance flat MD files with section headers")
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without writing')
    parser.add_argument('--max-books', type=int, default=0, help='Process up to N books (0=all)')
    parser.add_argument('--only-orphans', action='store_true', help='Only process MDs without EPUB/PDF originals')
    parser.add_argument('--force', action='store_true', help='Process all flat books, not just orphans')
    parser.add_argument('--domain', type=str, help='Only process specific domain folder')
    args = parser.parse_args()

    pipeline_books = Path("knowledge pipeline/books")
    orig_epub_base = SOURCE_EPUB_DIR
    orig_pdf_base = SOURCE_PDF_DIR

    # Build originals index
    epub_names = {f.name.lower().replace('.epub', '.md') for f in orig_epub_base.rglob("*.epub")}
    pdf_names = {f.name.lower().replace('.pdf', '.md') for f in orig_pdf_base.rglob("*.pdf")}

    # Collect candidates
    candidates = []
    for md_path in pipeline_books.rglob("*.md"):
        if args.domain and args.domain not in str(md_path):
            continue

        text = md_path.read_text(errors='replace')
        stats = analyze_headers(text)

        has_epub = md_path.name.lower() in epub_names
        has_pdf = md_path.name.lower() in pdf_names
        is_orphan = not (has_epub or has_pdf)

        if args.only_orphans and not is_orphan:
            continue
        if not args.force and not args.only_orphans and not is_orphan:
            continue

        if stats['density'] < 1.0:
            candidates.append((md_path, stats, is_orphan))

    # Sort by density (flattest first)
    candidates.sort(key=lambda x: x[1]['density'])

    if args.max_books > 0:
        candidates = candidates[:args.max_books]

    print("📚 Header Enhancement")
    print(f"   Candidates: {len(candidates)} books")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'WRITE'}")
    print(f"   Orphans only: {args.only_orphans}")
    print(f"{'='*70}")

    results = []
    enhanced_count = 0
    needs_llm_count = 0

    for i, (md_path, before_stats, is_orphan) in enumerate(candidates):
        tag = "🟠" if is_orphan else "🟢"
        result = enhance_book(md_path, dry_run=args.dry_run)

        if result is None:
            continue

        results.append(result)

        if result['enhanced']:
            enhanced_count += 1
            b = result['before']
            a = result['after']
            print(f"  {tag} [{i+1}/{len(candidates)}] +{result['regex_added']} headers | "
                  f"d={b['density']}→{a['density']} | {result['name'][:50]}")
        elif result.get('needs_llm'):
            needs_llm_count += 1
            print(f"  🔴 [{i+1}/{len(candidates)}] NEEDS LLM | d={result['before']['density']} | {result.get('name', '?')[:50]}")

    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"   Processed: {len(results)}")
    print(f"   Enhanced (regex): {enhanced_count}")
    print(f"   Needs LLM: {needs_llm_count}")

    if results:
        total_added = sum(r.get('regex_added', 0) for r in results)
        densities_before = [r['before']['density'] for r in results if 'before' in r]
        densities_after = [r['after']['density'] for r in results if r.get('enhanced') and 'after' in r]
        if densities_before:
            print(f"   Avg density before: {sum(densities_before)/len(densities_before):.1f}")
        if densities_after:
            print(f"   Avg density after:  {sum(densities_after)/len(densities_after):.1f}")
        print(f"   Total headers added: {total_added}")

    if not args.dry_run and enhanced_count > 0:
        print(f"\n✅ {enhanced_count} books enhanced. Run --only-orphans --force to process all 146 orphans.")


if __name__ == "__main__":
    main()
