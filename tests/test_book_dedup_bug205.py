"""D2507 (BUG-205) — book-level dedup regression tests.

BUG-205: `source_diversity` was inflated by near-duplicate book files (same book,
different download source / edition). `resolve_source_id` must collapse those to a
single canonical source_id so `source_diversity >= 3` is a trustworthy B2 synthesis
discriminator again.

Fixed:
  1. Unicode fold (NFKC → NFKD → strip combining marks): "Brené" == "Brene".
  2. SPACE-separated subtitle-opener split: "Blink The Power…" == "Blink: The Power…".
  3. Download-source strip on the fallback key (cache-miss with unknown author/title).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import pipeline.book_metadata as bm


# ── Unicode fold (NFKC → NFKD → strip combining marks) ────────────────────

def test_unicode_fold_accents_collapse():
    assert bm.normalize_author("Brené Brown") == bm.normalize_author("Brene Brown")
    assert bm.normalize_author("Höllerer, Markus A.") == bm.normalize_author("Hollerer, Markus A.")


def test_unicode_fold_fullwidth():
    assert bm.normalize_title("ｆｕｌｌ ｗｉｄｔｈ") == "full width"


# ── Space-separated subtitle-opener split (D2507) ─────────────────────────

def test_space_subtitle_opener_collapses_colon_editions():
    # "Blink The Power of Thinking Without Thinking" (no colon) must equal
    # "Blink: The Power of Thinking Without Thinking" (colon) — the BUG-205 root case.
    assert bm.normalize_title("Blink The Power of Thinking Without Thinking") == "blink"
    assert bm.normalize_title("Blink: The Power of Thinking Without Thinking") == "blink"


def test_leading_subtitle_opener_word_is_never_split():
    # "The" as the FIRST word must not be treated as a subtitle opener.
    assert bm.normalize_title("The Compound Effect") == "the compound effect"
    assert bm.normalize_title("The Elements of Typographic Style") == "the elements of typographic style"


# ── source_id collapse on the concrete BUG-205 examples ───────────────────

@pytest.mark.parametrize("files", [
    # Blink — subtitle colon asymmetry (D2507 space-subtitle-opener split).
    [
        "Blink The Power Of Thinking Without Thinking (Malcolm Gladwell) (z-library.sk, 1lib.sk, z-lib.sk).md",
        "Blink The Power of Thinking Without Thinking - Little, Brown and Company. Malcolm Gladwell (2005).md",
    ],
    # Atomic Design — different download sources (already collapsed pre-D2507; regression guard).
    [
        "Atomic Design (Brad Frost) (z-library.sk, 1lib.sk, z-lib.sk).md",
        "Atomic Design by Brad Frost.md",
    ],
    # Typographic Style — underscore vs dash filename conventions (regression guard).
    [
        "The Elements of Typographic Style_Robert Bringhurst_liber3.md",
        "_Bringhurst, Robert - The Elements of Typographic Style.md",
    ],
])
def test_near_duplicate_files_collapse(files):
    ids = {bm.resolve_source_id(f) for f in files}
    assert len(ids) == 1, f"expected collapse to 1 source_id, got {len(ids)}: {files}"


def test_distinct_books_do_not_collapse():
    # Same author, genuinely different works → must NOT collapse.
    a = bm.resolve_source_id("Outliers (Malcolm Gladwell) (z-library.sk).md")
    b = bm.resolve_source_id("Blink The Power Of Thinking Without Thinking (Malcolm Gladwell) (z-library.sk, 1lib.sk, z-lib.sk).md")
    assert a != b
