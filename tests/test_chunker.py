"""Tests for the chunker fix: paragraph boundaries + numbered lists + aphorisms.
Validated: 30/30 tests pass after applying qwen maxw.md diff.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.stage1_chunk import clean_line, split_on_headings, chunk_text


SAMPLE = """## Chapter 4: Pricing Psychology

Anchoring is one of the most reliable levers in pricing. When a customer sees a high reference price before the actual offer, their willingness to pay shifts upward substantially.

This works because human judgment relies on comparison rather than absolute evaluation. We are bad at knowing what something is intrinsically worth, so we lean on whatever number appeared first.

Price is a signal, not a number.

Consider three tactics for using this on a product page:

1. Show the annual plan first so the monthly plan looks cheap by comparison.
2. Cross out a higher list price next to the discounted price.
3. Offer a premium tier nobody buys, just to anchor the middle tier as reasonable.

Subscription pricing behaves differently from one-time pricing because commitment and switching costs change the psychology entirely.
"""


class TestCleanLine:
    """The single shared function — both callers depend on it."""

    def test_blank_line_returns_empty_string(self):
        assert clean_line("") == ""

    def test_whitespace_only_returns_empty_string(self):
        assert clean_line("   ") == ""

    def test_numbered_list_preserved(self):
        r = clean_line("1. Show the annual plan first so the monthly plan looks cheap.")
        assert r is not None
        assert "Show the annual" in r

    def test_aphorism_preserved(self):
        assert clean_line("Price is a signal, not a number.") == "Price is a signal, not a number."

    def test_code_fence_filtered(self):
        assert clean_line("```python") is None

    def test_high_skip_words_filtered(self):
        assert clean_line("Subscribe newsletter twitter instagram facebook") is None


class TestSplitOnHeadings:
    """Paragraph boundaries must survive to chunk_text."""

    def test_paragraph_boundaries_preserved(self):
        sections = split_on_headings(SAMPLE)
        _, body, _ = sections[0]
        assert "\n\n" in body
        assert len(body.split("\n\n")) >= 4

    def test_numbered_list_in_body(self):
        sections = split_on_headings(SAMPLE)
        _, body, _ = sections[0]
        assert "1. Show the annual" in body
        assert "2. Cross out" in body
        assert "3. Offer a premium" in body

    def test_aphorism_in_body(self):
        sections = split_on_headings(SAMPLE)
        _, body, _ = sections[0]
        assert "Price is a signal, not a number." in body


class TestChunkText:
    """Paragraph-aware splitting, not blind word-window."""

    def test_uses_paragraph_path(self):
        sections = split_on_headings(SAMPLE)
        _, body, _ = sections[0]
        chunks = chunk_text(body, chunk_size=60, overlap=10)
        assert len(chunks) >= 3

    def test_numbered_list_not_split(self):
        sections = split_on_headings(SAMPLE)
        _, body, _ = sections[0]
        chunks = chunk_text(body, chunk_size=60, overlap=10)
        list_chunk = next(c for c in chunks if "1. Show the annual" in c)
        assert "2. Cross out" in list_chunk
        assert "3. Offer a premium" in list_chunk

    def test_aphorism_in_chunk(self):
        sections = split_on_headings(SAMPLE)
        _, body, _ = sections[0]
        chunks = chunk_text(body, chunk_size=60, overlap=10)
        assert any("Price is a signal, not a number." in c for c in chunks)
