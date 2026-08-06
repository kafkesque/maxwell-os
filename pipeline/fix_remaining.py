#!/usr/bin/env python3
"""
fix_remaining.py — Two fixes in one pass:
  1. Fuzzy-match + convert 120 unmatched EPUBs → overwrite/create pipeline MDs
  2. LLM pass on 183 stubborn books using Gemma for header insertion
==================================================================================
Authority: D2134
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import pypandoc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import BOOKS_DIR, SOURCE_EPUB_DIR, SOURCE_PDF_DIR

EPUB_BASE = SOURCE_EPUB_DIR
PDF_BASE = SOURCE_PDF_DIR
MD_BASE = BOOKS_DIR
OMLX_CALL = Path("pipeline/omlx_call.py")

# ── TASK 1: Fuzzy-match + convert unmatched EPUBs ──

def build_md_index() -> dict[str, str]:
    """Index all pipeline MDs by cleaned stem."""
    idx = {}
    for md in MD_BASE.rglob("*.md"):
        # Clean: remove common suffixes, normalize
        clean = re.sub(r'[^a-z0-9]', '', md.stem.lower())
        idx[clean] = str(md)
    return idx


def fuzzy_find(epub_stem: str, md_index: dict[str, str]) -> tuple[str | None, int]:
    """Find best fuzzy match for an EPUB stem in the MD index."""
    ep_clean = re.sub(r'[^a-z0-9]', '', epub_stem.lower())
    best_path = None
    best_score = 0
    for md_clean, md_path in md_index.items():
        score = 0
        for a, b in zip(ep_clean, md_clean):
            if a == b:
                score += 1
            else:
                break
        if score > best_score:
            best_score = score
            best_path = md_path
    return best_path, best_score


def convert_epub(epub_path: Path) -> str | None:
    """Convert EPUB to clean MD via pypandoc."""
    try:
        text = pypandoc.convert_file(str(epub_path), 'markdown',
                                     extra_args=['--wrap=none', '--from=epub'])
        # Strip SVG/HTML noise
        lines = []
        skip_svg = False
        for line in text.split('\n'):
            s = line.strip()
            if '<svg' in s.lower() or 'viewbox=' in s.lower():
                skip_svg = True; continue
            if skip_svg:
                if '</svg>' in s.lower() or s == '```': skip_svg = False
                continue
            if re.match(r'^!\[\]\(cover', s): continue
            if re.match(r'^\[\]{#', s): continue
            if re.match(r'^:::\s*\{', s): continue
            if s == ':::': continue
            lines.append(line)
        return '\n'.join(lines)
    except Exception as e:
        print(f"    ❌ pypandoc: {e}")
        return None


def crash_safe_write(path: Path, content: str):
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


def task1_fix_unmatched_epubs(dry_run: bool = True):
    """Fuzzy-match and convert all unmatched EPUBs."""
    md_index = build_md_index()

    # Find unmatched + fuzzy match
    to_convert = []  # (epub_path, md_path_or_None, score, category)
    for ep in EPUB_BASE.rglob("*.epub"):
        ep_clean = re.sub(r'[^a-z0-9]', '', ep.stem.lower())
        if ep_clean in md_index:
            continue  # already matched

        best_path, score = fuzzy_find(ep.stem, md_index)
        if score > 30:
            to_convert.append((ep, Path(best_path), score, "strong"))
        elif score > 15:
            to_convert.append((ep, Path(best_path), score, "weak"))
        else:
            # New book — determine target domain folder from EPUB path
            ep_rel = ep.relative_to(EPUB_BASE)
            domain_dir = MD_BASE / ep_rel.parent
            md_name = ep.stem + ".md"
            target = domain_dir / md_name
            to_convert.append((ep, target, 0, "new"))

    print("📚 Task 1: Fix Unmatched EPUBs")
    print(f"   Strong fuzzy matches (auto-overwrite): {sum(1 for t in to_convert if t[3]=='strong')}")
    print(f"   Weak fuzzy matches (review needed):    {sum(1 for t in to_convert if t[3]=='weak')}")
    print(f"   New books (create MD):                 {sum(1 for t in to_convert if t[3]=='new')}")
    print(f"   Mode: {'DRY RUN' if dry_run else 'WRITE'}")
    print(f"{'='*70}")

    converted = 0
    for epub_path, md_target, score, category in to_convert:
        name = epub_path.name[:60]

        # Convert
        md_text = convert_epub(epub_path)
        if md_text is None:
            print(f"  ❌ [{category}] FAILED convert: {name}")
            continue

        # Count headers
        h_count = len(re.findall(r'^#{1,3}\s+\S', md_text, re.MULTILINE))

        if category == "new":
            if not dry_run:
                md_target.parent.mkdir(parents=True, exist_ok=True)
                crash_safe_write(md_target, md_text)
            print(f"  🆕 [{category}] CREATED: {md_target.name[:50]} ({len(md_text):,}c, {h_count}h)")
        else:
            if not dry_run:
                crash_safe_write(md_target, md_text)
            flag = "✅" if category == "strong" else "⚠️"
            print(f"  {flag} [{category}] score={score} → {md_target.name[:50]} ({len(md_text):,}c, {h_count}h)")

        converted += 1

    print(f"\n   Converted: {converted}/{len(to_convert)}")
    if dry_run:
        print("   Run without --dry-run to apply.")
    return converted


# ── TASK 2: LLM pass on stubborn books ──

LLM_SYSTEM_PROMPT = """You are a document structure analyzer. Given a flat markdown document with no section headers, identify where ## section headers should be inserted at natural topic boundaries.

Rules:
- Insert headers at MAJOR topic transitions only (not every paragraph)
- Target: 1 header per 3000-8000 characters of text
- Header text should be 3-8 words, descriptive of the section's topic
- Do NOT insert headers for front matter (title, author, TOC)
- Output ONLY a JSON array of {"position": line_number, "header": "Section Title"}
- Position is 1-indexed line number in the document
- Return {"headers": []} if no clear boundaries exist"""


def llm_insert_headers(text: str) -> str | None:
    """Use OMLX Gemma to identify section boundaries in flat text."""
    # Truncate if too large (send first 40K chars — enough to find patterns)
    truncated = text[:40000] if len(text) > 40000 else text

    # Number the lines for the LLM
    numbered_lines = []
    for i, line in enumerate(truncated.split('\n'), 1):
        numbered_lines.append(f"{i:5d}|{line}")
    numbered_text = '\n'.join(numbered_lines)

    prompt = f"""Document ({len(truncated.split(chr(10)))} lines, {len(truncated)} chars):

{numbered_text}

Identify natural section boundaries. Return JSON:"""

    try:
        from pipeline.omlx_call import call_omlx_json
        result = call_omlx_json(
            prompt=prompt,
            model="gemma-4-E4B-it-MLX-4bit",
            system=LLM_SYSTEM_PROMPT,
            max_tokens=1024,
        )

        if isinstance(result, dict) and 'headers' in result:
            headers = result['headers']
            if not headers:
                return None

            # Apply headers to the original text
            lines = text.split('\n')
            # Sort by position descending so inserts don't shift indices
            for h in sorted(headers, key=lambda x: x.get('position', 0), reverse=True):
                pos = h.get('position', 0) - 1  # convert to 0-indexed
                header_text = h.get('header', 'Section').strip()
                if 0 <= pos < len(lines):
                    lines.insert(pos, f"## {header_text}")

            return '\n'.join(lines)
    except Exception as e:
        print(f"      ❌ LLM error: {e}")

    return None


def task2_llm_stubborn(dry_run: bool = True, max_books: int = 0):
    """LLM pass on books still needing headers."""
    from pipeline.enhance_md_headers import analyze_headers

    # Scan for books needing LLM
    orig_epub_base = SOURCE_EPUB_DIR
    orig_pdf_base = SOURCE_PDF_DIR
    epub_names = {f.name.lower().replace('.epub', '.md') for f in orig_epub_base.rglob("*.epub")}
    pdf_names = {f.name.lower().replace('.pdf', '.md') for f in orig_pdf_base.rglob("*.pdf")}

    candidates = []
    for md_path in MD_BASE.rglob("*.md"):
        try:
            text = md_path.read_text(errors='replace')
        except Exception as e:
            print(f"    ⚠️  Cannot read {md_path.name}: {e}")
            continue
        stats = analyze_headers(text)
        if stats['density'] < 1.0:
            is_orphan = md_path.name.lower() not in epub_names and md_path.name.lower() not in pdf_names
            candidates.append((md_path, stats, is_orphan))

    # Sort: smallest first (cheaper to process, learn from)
    candidates.sort(key=lambda x: x[1]['chars'])

    if max_books > 0:
        candidates = candidates[:max_books]

    print("\n📚 Task 2: LLM Header Pass")
    print(f"   Candidates: {len(candidates)} books (density < 1.0)")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LLM PROCESSING'}")
    print(f"{'='*70}")

    enhanced = 0
    for i, (md_path, stats, is_orphan) in enumerate(candidates):
        if stats['chars'] < 3000:  # too small
            continue

        tag = "🟠" if is_orphan else "🟡"

        if not dry_run:
            text = md_path.read_text(errors='replace')
            enhanced_text = llm_insert_headers(text)
            if enhanced_text:
                from pipeline.enhance_md_headers import analyze_headers
                after = analyze_headers(enhanced_text)
                if after['density'] > stats['density']:
                    crash_safe_write(md_path, enhanced_text)
                    enhanced += 1
                    print(f"  {tag} [{i+1}/{len(candidates)}] d={stats['density']}→{after['density']} | "
                          f"h#{stats['total_h']}→{after['total_h']} | {md_path.name[:50]}")
                else:
                    print(f"  ➡️  [{i+1}/{len(candidates)}] no improvement | {md_path.name[:50]}")
            else:
                print(f"  🔴 [{i+1}/{len(candidates)}] LLM returned no headers | {md_path.name[:50]}")
        else:
            print(f"  {tag} [{i+1}/{len(candidates)}] d={stats['density']} | {stats['chars']:,}c | {md_path.name[:50]}")

    print(f"\n   Enhanced: {enhanced}/{len(candidates)}")
    if dry_run:
        print("   Run without --dry-run to apply LLM pass.")


def main():
    parser = argparse.ArgumentParser(description="Fix remaining unmatched EPUBs + stubborn LLM books")
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would change (default: dry run)')
    parser.add_argument('--apply', action='store_true',
                        help='Actually apply changes')
    parser.add_argument('--task', choices=['epubs', 'llm', 'all'], default='all')
    parser.add_argument('--max-llm', type=int, default=0,
                        help='Max books for LLM pass (0=all)')
    args = parser.parse_args()

    dry = not args.apply

    if args.task in ('epubs', 'all'):
        task1_fix_unmatched_epubs(dry_run=dry)

    if args.task in ('llm', 'all'):
        task2_llm_stubborn(dry_run=dry, max_books=args.max_llm)


if __name__ == "__main__":
    main()
