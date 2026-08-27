#!/usr/bin/env python3
"""
text_cleaner.py — Pre-processing quality: markdown cleaning + paragraph normalization.
Authority: asad.txt #15-17, Phase 0.5

H1: clean_markdown() — Strip formatting artifacts that corrupt embeddings.
H2: normalize_paragraphs() — Produce embedding-friendly paragraphs (30-250 words).

The 30-250 word window is NOT arbitrary:
  - < 30 words: too little context, embeds near every short assertion
  - > 250 words: multiple topics dilute the vector, landing equidistant between clusters
  - 30-250: single topic, complete thought, discriminative embedding — what bge-m3 was trained on

Why this matters for embeddings specifically:
  "**Price anchoring** increases WTP" and "Price anchoring increases WTP"
  produce DIFFERENT embedding vectors because ** tokens are in the tokenizer vocabulary.
  You're clustering on formatting, not meaning. This is a real, measurable quality issue.
"""

import re
import sys

# ── H1: Markdown Cleaning (~30 LOC) ──────────────────────────────────────

# Boilerplate patterns to strip (non-semantic content)
BOILERPLATE_PATTERNS: list[str] = [
    r'(?i)copyright\s.*?reserved',
    r'(?i)all rights reserved',
    r'(?i)table of contents',
    r'(?i)\bchapter\s+\d+\b',
    r'(?i)\bpage\s+\d+\b',
    r'https?://\S+',
    r'\bISBN\b[:\s]*[\d\-Xx]+',
    r'(?i)published by\b.*',
    r'(?i)click here to buy',
    r'(?i)visit our website',
    r'(?i)subscribe to our newsletter',
    r'(?i)follow us on\s+(twitter|facebook|instagram|linkedin)',
    r'(?i)all rights? reserved',
    r'(?i)no part of this publication may be reproduced',
    r'(?i)printed in the united states of america',
    r'(?i)first edition|second edition|third edition',
    r'(?i)library of congress catalog',
]


def clean_markdown(text: str) -> str:
    """
    Strip formatting artifacts that corrupt embedding vectors.

    Handles: headings, bold/italic, links, code, blockquotes, boilerplate.

    Args:
        text: Raw markdown text from Stage 0 conversion.

    Returns:
        Clean plain text with normalized whitespace.
    """
    # Headings → plain text (strip # markers, keep heading text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Bold → plain (**text** → text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)

    # Italic → plain (*text* → text, but not bullet points)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)

    # Links → link text only (URLs embed differently from concepts)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Inline code → plain (`text` → text)
    text = re.sub(r'`([^`]+)`', r'\1', text)

    # Blockquotes → plain (> text → text)
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)

    # Horizontal rules → remove
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Image syntax → remove entirely
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

    # HTML tags → strip
    text = re.sub(r'<[^>]+>', '', text)

    # Boilerplate removal
    for pattern in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, '', text)

    # Normalize whitespace: collapse multiple newlines, spaces
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # Trim per-line whitespace
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


# ── BUG-181#1: Pandoc/calibre converter-artifact stripper (D2471) ────────
# clean_markdown() above strips standard Markdown/HTML but MISSES Pandoc's
# {...} attribute syntax, ::: fenced divs, and calibre span markers — the exact
# residue that leaked into evidence_passages (BUG-181#1). Imported by
# stage1_3_prefilter (root-cause) and scripts/fix_singleton_quality.py (post-hoc).

_CLEAN_SUBS: tuple[tuple[str, str], ...] = (
    (r'\{[^}]*\.(?:keep-together|num-string|calibre\d+)[^}]*\}', ' '),
    (r'\{=(?:html|latex)\}', ' '),
    (r'\{align="[^"]*"\}', ' '),
    (r'\{width="[^"]*"\}', ' '),
    (r'\{height="[^"]*"\}', ' '),
    (r'\{bgcol[^}]*\}', ' '),
    (r'\{#(?:chapter|part|sec|ch)[^}]*\}', ' '),
    (r'!Image\{[^}]*\}', ' '),
    (r':::\s*imagel[^:]*:::*', ' '),
    (r':{3,}', ' '),
    (r'\^\d+\^', ' '),
    (r'&#\d+;', ' '),
    (r'\[\s*\]\{[^}]*\}', ' '),
    (r'\.\s*xhtml_p\d+', ' '),
)


def clean_evidence_passage(text: str, collapse: bool = True) -> str:
    """Strip Pandoc/calibre converter residue from one evidence passage (D2471).

    Conservative: only removes the unambiguous artifacts above; never touches
    prose. collapse=True collapses whitespace runs to a single space (correct for
    short evidence passages); pass collapse=False for S1 segments to preserve
    line structure.
    """
    if not text:
        return text
    t = text
    for pat, rep in _CLEAN_SUBS:
        t = re.sub(pat, rep, t)
    if collapse:
        return re.sub(r'\s+', ' ', t).strip()
    return t.strip()


# ── H2: Paragraph Normalization (~30 LOC) ────────────────────────────────

def _is_index_or_table(text: str) -> bool:
    """
    Detect index entries, table of contents, and other non-prose structures.

    Heuristic: if text has <1 sentence-ending punctuation per 100 words and
    is >200 words, it's likely an index, TOC, or data table — not prose.
    """
    words = text.split()
    if len(words) < 200:
        return False
    # Count sentence-ending punctuation
    sentence_ends = sum(1 for c in text if c in '.!?')
    ratio = sentence_ends / max(len(words), 1)
    # Normal prose has ~3-5 sentence ends per 100 words
    return ratio < 0.01  # <1 per 100 words = likely index/table


def normalize_paragraphs(
    text: str,
    min_words: int = 30,
    max_words: int = 250,
) -> list[str]:
    """
    Produce embedding-friendly paragraphs: complete sentences, single topic.

    Strategy:
      - Split on paragraph boundaries (double newlines)
      - Too short (< min_words): merge with previous paragraph or skip
      - Too long (> max_words): split at sentence boundaries
      - Aphorisms (15-29 words): keep if they appear substantive

    Args:
        text: Cleaned plain text from clean_markdown().
        min_words: Minimum words for a standalone paragraph (default 30).
        max_words: Maximum words before splitting (default 250).

    Returns:
        List of normalized paragraph strings.
    """
    # Split on paragraph boundaries
    raw = [p.strip() for p in text.split('\n\n') if p.strip()]

    normalized: list[str] = []

    for para in raw:
        words = para.split()
        word_count = len(words)

        # ── Skip index/table entries ──
        if _is_index_or_table(para):
            continue

        # ── Too short: merge or skip ──
        if word_count < min_words:
            if word_count >= 15:
                # Aphorisms: "Price anchoring works because the first number sets the frame."
                # Keep if substantive — has at least one meaningful clause.
                if _has_substantive_content(para):
                    normalized.append(para)
                continue
            elif normalized:
                # Merge with previous paragraph if it fits
                prev_words = len(normalized[-1].split())
                if prev_words + word_count <= max_words:
                    normalized[-1] += ' ' + para
            # Too short to merge or standalone → skip
            continue

        # ── Too long: split at sentence boundaries ──
        if word_count > max_words:
            # Primary: split on sentence-ending punctuation followed by capital letter
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', para)

            # If splitting produced <2 pieces, try splitting on bullet points
            if len(sentences) < 2:
                sentences = re.split(r'(?<=[.!?])\s+(?=[•\-\*\d])', para)

            # If still <2, try all newlines (table rows, list items)
            if len(sentences) < 2:
                sentences = [s.strip() for s in para.split('\n') if s.strip()]

            # If STILL <2, force-split at word boundary near max_words
            if len(sentences) < 2:
                words = para.split()
                mid = max_words
                while mid < len(words) and not words[mid][0].isupper():
                    mid += 1
                if mid >= len(words):
                    mid = max_words
                sentences = [' '.join(words[:mid]), ' '.join(words[mid:])]

            current: list[str] = []
            current_words = 0

            for sent in sentences:
                if not sent.strip():
                    continue
                sw = len(sent.split())
                if current_words + sw > max_words and current:
                    normalized.append(' '.join(current))
                    current = []
                    current_words = 0
                current.append(sent)
                current_words += sw

            if current:
                normalized.append(' '.join(current))
            continue

        # ── Goldilocks: 30-250 words, keep as-is ──
        normalized.append(para)

    return normalized


def _has_substantive_content(text: str) -> bool:
    """
    Check if a short paragraph has substantive content (not just transition phrases).

    Returns True if the text has content worth keeping as a standalone segment.
    """
    # Skip pure transition/connective phrases
    transition_patterns = [
        r'^(in|by|for|with|from|to|as|of|the|a|an|this|that|these|those)\s',
        r'^(however|therefore|moreover|furthermore|additionally|consequently)\b',
        r'^(see|refer|note|consider|imagine|suppose|assume)\b',
    ]
    for pat in transition_patterns:
        if re.match(pat, text.lower()):
            return False

    # Must have at least one substantive word (noun, verb, concept)
    substantive_indicators = [
        r'\b(principle|concept|theory|model|framework|strategy|effect|bias|law|rule)\b',
        r'\b(increases|decreases|improves|reduces|creates|enables|prevents|drives)\b',
        r'\b(because|therefore|results in|leads to|causes|correlates)\b',
        r'\b(should|must|always|never|typically|often|rarely)\b',
    ]
    for pat in substantive_indicators:
        if re.search(pat, text.lower()):
            return True

    # Default: if it's a complete sentence with subject+verb, keep it
    return bool(re.match(r'^[A-Z].*[.!?]$', text.strip()))


# ── Combined pipeline entry point ─────────────────────────────────────────

def clean_text_pipeline(text: str, min_words: int = 30, max_words: int = 250) -> list[str]:
    """
    Full cleaning pipeline: markdown strip → paragraph normalize.
    Returns list of clean, normalized paragraphs ready for chunking.

    Args:
        text: Raw markdown text from Stage 0.
        min_words: Minimum words per paragraph.
        max_words: Maximum words per paragraph.

    Returns:
        List of normalized paragraph strings.
    """
    cleaned = clean_markdown(text)
    return normalize_paragraphs(cleaned, min_words=min_words, max_words=max_words)


# ── Post-conversion quality check (H4) ────────────────────────────────────

def check_conversion_quality(text: str, file_name: str = "") -> dict:
    """
    Post-conversion quality check for garbled PDFs (H4).
    Detects common conversion artifacts: mojibake, truncated text, empty output.

    Args:
        text: Converted markdown text.
        file_name: Source file name for reporting.

    Returns:
        Dict with 'ok' (bool), 'warnings' (list[str]), 'error' (Optional[str]).
    """
    warnings: list[str] = []
    error: str | None = None

    if not text or len(text.strip()) < 100:
        error = f"Empty or near-empty conversion ({len(text)} chars)"
        return {"ok": False, "warnings": warnings, "error": error, "file": file_name}

    # Check for mojibake (garbled character sequences)
    mojibake_count = len(re.findall(r'[^\x20-\x7E\xA0-\xFF\u00C0-\u024F\u2010-\u205F\n\r\t]', text))
    char_ratio = mojibake_count / max(len(text), 1)
    if char_ratio > 0.02:
        warnings.append(f"Mojibake detected: {mojibake_count} non-printable chars ({char_ratio:.1%})")

    # Check for repeated single characters (OCR garbage)
    garbage_runs = len(re.findall(r'([^\s\w])\1{4,}', text))
    if garbage_runs > 10:
        warnings.append(f"Garbage runs: {garbage_runs} repeated-character sequences (possible OCR artifact)")

    # Check for excessive short lines (table of contents, etc.)
    lines = text.split('\n')
    short_lines = [l for l in lines if 0 < len(l.strip()) < 10]
    if len(short_lines) > len(lines) * 0.3:
        warnings.append(f"Excessive short lines: {len(short_lines)}/{len(lines)} lines < 10 chars")

    # Check for sudden truncation (ends mid-sentence)
    last_100 = text.strip()[-100:]
    if last_100 and last_100[-1] not in '.!?)\'"' and len(text) < 50000:
        warnings.append("Text may be truncated (ends mid-sentence)")

    ok = error is None

    return {
        "ok": ok,
        "warnings": warnings,
        "error": error,
        "file": file_name,
        "char_count": len(text),
        "line_count": len(lines),
    }


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Text Cleaner (H1-H4)")
    parser.add_argument("--clean", action="store_true", help="Clean markdown from stdin, print to stdout")
    parser.add_argument("--normalize", action="store_true", help="Normalize paragraphs from cleaned stdin")
    parser.add_argument("--quality", type=str, help="Run quality check on a converted .md file")
    parser.add_argument("--min-words", type=int, default=30, help="Min words per paragraph")
    parser.add_argument("--max-words", type=int, default=250, help="Max words per paragraph")

    args = parser.parse_args()

    if args.quality:
        with open(args.quality) as f:
            text = f.read()
        result = check_conversion_quality(text, args.quality)
        import json as _json
        print(_json.dumps(result, indent=2))
        sys.exit(0 if result["ok"] else 1)

    if args.clean:
        text = sys.stdin.read()
        cleaned = clean_markdown(text)
        sys.stdout.write(cleaned)

    elif args.normalize:
        text = sys.stdin.read()
        paragraphs = normalize_paragraphs(text, args.min_words, args.max_words)
        sys.stdout.write('\n\n'.join(paragraphs))

    else:
        parser.print_help()
