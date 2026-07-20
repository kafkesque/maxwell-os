#!/usr/bin/env python3
"""
S1 Chunking — Chonkie-powered semantic chunking for Maxwell OS knowledge pipeline.

Replaces sumy LexRank with Chonkie chunkers (Semantic, Sentence, Token, Recursive).
Maintains backward-compatible JSON output format with s1_extractive.py.

Usage:
    python3 tools/s1_chunking.py input.md [--chunker sentence] [--chunk-size 512] [--output out.json]
    python3 tools/s1_chunking.py input.md --dry-run

Authority:
    D911_CHONKIE_ADOPT (ACTIVE)
    D_S1_CHONKIE (OPEN → superseded by D911)
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Path setup ──────────────────────────────────────────────────────────
# Match s1_extractive.py pattern: add tools/ to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

# ── Pipeline paths ───────────────────────────────────────────────────────
from pipeline_paths import (
    PIPELINE_ROOT,
    STAGE_PATHS,
    GEN_MODEL,
    GEN_PROVIDER,
)

# ── Constants ────────────────────────────────────────────────────────────
SCHEMA_VERSION = "2.0"
PIPELINE_COMMIT = "v2.1.0"
GEN_MODEL_STAMP = f"{GEN_MODEL} (via chonkie)"

# Chunk size defaults (words ≈ tokens for most text types)
CHUNK_SIZES = {
    "token": 512,
    "sentence": 512,
    "semantic": 512,
    "recursive": 512,
}
CHUNK_OVERLAP = 64  # token overlap for sliding window

# ── Text cleaning ────────────────────────────────────────────────────────
SKIP_PATTERNS = [
    re.compile(r"^#{1,6}\s"),                # headings
    re.compile(r"^\[.*\]\(.*\)$"),           # bare links
    re.compile(r"^!\[.*\]\(.*\)$"),          # images
    re.compile(r"^\s*[-*+]\s"),              # list items (might be content)
    re.compile(r"^\s*\d+[.\)]\s"),           # numbered lists
    re.compile(r"^\s*\|.*\|$"),             # tables - keep minimal
    re.compile(r"^\s*$"),                    # blank lines
    re.compile(r"^>\s"),                     # blockquotes (light weight)
    re.compile(r"^```"),                     # code fences
    re.compile(r"^---"),                     # horizontal rules
]

SKIP_WORDS = {"twitter", "x.com", "instagram", "facebook", "subscribe", "newsletter", "disclaimer", "copyright"}


def _is_skip_line(line: str) -> bool:
    """Check if a line should be skipped."""
    stripped = line.strip()
    if not stripped:
        return True
    if len(stripped) < 15:
        return True  # too short to be meaningful
    for pattern in SKIP_PATTERNS:
        if pattern.match(stripped):
            return True
    words = stripped.lower().split()
    skip_count = sum(1 for w in words if w in SKIP_WORDS)
    return skip_count > len(words) * 0.3  # >30% skip words


def clean_markdown(text: str) -> str:
    """Clean markdown text for chunking."""
    lines = text.split("\n")
    cleaned = [line for line in lines if not _is_skip_line(line)]
    text = "\n".join(cleaned)
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_and_clean_md(filepath: str) -> str:
    """Load a markdown file and return cleaned text."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return clean_markdown(text)


# ── Chonkie chunkers ─────────────────────────────────────────────────────

def chunk_with_chonkie(
    text: str,
    chunker_type: str = "sentence",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> List[str]:
    """Chunk text using Chonkie. Returns list of chunk strings."""
    from chonkie import SentenceChunker, TokenChunker, RecursiveChunker

    if chunker_type == "sentence":
        chunker = SentenceChunker(chunk_size=chunk_size)
    elif chunker_type == "token":
        chunker = TokenChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif chunker_type == "recursive":
        chunker = RecursiveChunker(chunk_size=chunk_size)
    else:
        raise ValueError(f"Unknown chunker type: {chunker_type}")

    chunks = chunker.chunk(text)
    return [str(c) for c in chunks]


def chunk_semantic(text: str, chunk_size: int = 512) -> List[str]:
    """Chunk text using SemanticChunker (requires embeddings)."""
    from chonkie import SemanticChunker

    chunker = SemanticChunker(chunk_size=chunk_size)
    chunks = chunker.chunk(text)
    return [str(c) for c in chunks]


# ── LexRank fallback (from s1_extractive.py) ──────────────────────────────

def _load_sumy_or_none():
    """Try importing sumy LexRank. Returns None if not available."""
    try:
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.summarizers.lex_rank import LexRankSummarizer
        from sumy.nlp.stemmers import Stemmer
        from sumy.utils import get_stop_words
        import nltk

        nltk.data.path.append("/usr/local/share/nltk_data")
        return {
            "tokenizer": Tokenizer,
            "parser": PlaintextParser,
            "summarizer": LexRankSummarizer,
            "stemmer": Stemmer,
            "stop_words": get_stop_words,
        }
    except Exception:
        return None


SUMY_AVAILABLE = _load_sumy_or_none()


def extract_lexrank(
    text: str,
    sentence_count: int = 10,
    language: str = "english",
) -> Optional[List[str]]:
    """Extract top sentences using sumy LexRank. Returns None if unavailable."""
    if SUMY_AVAILABLE is None:
        return None

    try:
        from io import StringIO

        tokenizer = SUMY_AVAILABLE["tokenizer"](language)
        parser = SUMY_AVAILABLE["parser"].from_string(text, tokenizer)
        stemmer = SUMY_AVAILABLE["stemmer"](language)
        summarizer = SUMY_AVAILABLE["summarizer"](stemmer)
        summarizer.stop_words = SUMY_AVAILABLE["stop_words"](language)

        sentences = summarizer(parser.document, sentence_count)
        return [str(s) for s in sentences]
    except Exception:
        return None


# ── Assemble passages (shared logic) ─────────────────────────────────────

def assemble_passages(chunks: List[str], max_words: int = 500) -> List[str]:
    """Group chunks into passages of max_words each."""
    passages = []
    current = []
    current_words = 0

    for chunk in chunks:
        words = chunk.split()
        if current_words + len(words) > max_words and current:
            passages.append(" ".join(current))
            current = []
            current_words = 0
        current.append(chunk)
        current_words += len(words)

    if current:
        passages.append(" ".join(current))

    return passages if passages else [" ".join(chunks)]


# ── LLM fallback ─────────────────────────────────────────────────────────

def llm_fallback(text: str) -> List[str]:
    """Fallback: use local LLM to extract passages when chunking fails."""
    try:
        import requests

        # Truncate if too long
        if len(text) > 8000:
            text = text[:8000]

        prompt = f"""Extract the most information-dense passages from this text. Return each passage as a separate paragraph, separated by blank lines. Focus on concrete facts, data, and actionable insights.

TEXT:
{text}

PASSAGES:"""

        response = requests.post(
            "http://127.0.0.1:11435/v1/chat/completions",
            json={
                "model": "Phi-4-mini-instruct-8bit",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 2048,
            },
            timeout=180,
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        passages = [p.strip() for p in content.split("\n\n") if p.strip()]
        return passages if passages else [content]
    except Exception as e:
        print(f"   LLM fallback failed: {e}", file=sys.stderr)
        # Last resort: return first 500 words as single passage
        words = text.split()[:500]
        return [" ".join(words)]


# ── Main entry point ─────────────────────────────────────────────────────

def _add_stamps(passages: List[str], source_file: str, source_path: str, method: str) -> List[Dict[str, Any]]:
    """Add stamp metadata to each passage."""
    results = []
    for i, passage in enumerate(passages):
        results.append({
            "text": passage,
            "source_file": source_file,
            "source_path": source_path,
            "method": method,
            "passage_index": i + 1,
            "word_count": len(passage.split()),
            "schema_version": SCHEMA_VERSION,
            "gen_model": GEN_MODEL_STAMP,
            "pipeline_commit": PIPELINE_COMMIT,
        })
    return results


def main():
    parser = argparse.ArgumentParser(
        description="S1 Chunking — Chonkie-powered semantic chunking for knowledge pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="Source .md file to chunk")
    parser.add_argument(
        "--chunker",
        choices=["sentence", "token", "recursive", "semantic", "lexrank"],
        default="sentence",
        help="Chunking strategy (default: sentence)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Target chunk size in tokens (default: 512)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=64,
        help="Chunk overlap in tokens (default: 64, token chunker only)",
    )
    parser.add_argument(
        "--output",
        help="Write results to JSON file (default: stdout)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show chunk stats without writing output",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Skip LLM fallback if chunking fails",
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"📖 Loading: {input_path.name}", file=sys.stderr)
    start = time.time()

    # ── Load and clean ────────────────────────────────────────────────────
    clean_text = load_and_clean_md(str(input_path))
    print(
        f"   Cleaned text: {len(clean_text)} chars, {len(clean_text.split())} words",
        file=sys.stderr,
    )

    # ── Chunk ─────────────────────────────────────────────────────────────
    chunks = None
    method = args.chunker

    try:
        if args.chunker == "lexrank":
            sentences = extract_lexrank(clean_text, sentence_count=10)
            if sentences:
                chunks = assemble_passages(sentences, max_words=500)
                method = "lexrank"
        elif args.chunker == "semantic":
            chunks = chunk_semantic(clean_text, chunk_size=args.chunk_size)
        else:
            chunks = chunk_with_chonkie(
                clean_text,
                chunker_type=args.chunker,
                chunk_size=args.chunk_size,
                chunk_overlap=args.overlap,
            )
    except Exception as e:
        print(f"   Chunker '{args.chunker}' failed: {e}", file=sys.stderr)
        chunks = None

    # ── Fallback chain ────────────────────────────────────────────────────
    if chunks is None or len(chunks) == 0:
        if args.no_fallback:
            print("ERROR: Chunking failed and --no-fallback is set.", file=sys.stderr)
            sys.exit(1)

        # Try lexrank fallback
        if args.chunker != "lexrank":
            print("   Falling back to LexRank...", file=sys.stderr)
            try:
                sentences = extract_lexrank(clean_text, sentence_count=10)
                if sentences:
                    chunks = assemble_passages(sentences, max_words=500)
                    method = "lexrank_fallback"
            except Exception:
                pass

        # Try LLM fallback
        if chunks is None or len(chunks) == 0:
            print("   Falling back to LLM extraction...", file=sys.stderr)
            chunks = llm_fallback(clean_text)
            method = "llm_fallback"

    print(f"   Got {len(chunks)} chunks using '{method}'", file=sys.stderr)

    # ── Build output ──────────────────────────────────────────────────────
    results = _add_stamps(chunks, input_path.name, str(input_path.resolve()), method)
    elapsed = time.time() - start

    if args.dry_run:
        print(f"\n📊 DRY RUN — {len(results)} passages extracted\n", file=sys.stderr)
        for r in results:
            print(
                f"  [{r['passage_index']}] {r['word_count']:>4} words  "
                f"({r['method']})  {r['text'][:80]}...",
                file=sys.stderr,
            )
        print(f"\n⏱  {elapsed:.1f}s", file=sys.stderr)
        return

    # ── Write output ──────────────────────────────────────────────────────
    output_json = json.dumps(results, indent=2, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"✅ Wrote {len(results)} passages to {output_path}", file=sys.stderr)
    else:
        print(output_json)

    print(f"⏱  {elapsed:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
