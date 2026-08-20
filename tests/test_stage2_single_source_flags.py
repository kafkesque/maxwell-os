"""CI test: --only-single-source / --reset-single-source flag guards (P2-1 / BUG-152).

The t11 single-source rerun adds two flags to stage2_extract.py:
  --only-single-source   extract only single-source clusters (skip convergent)
  --reset-single-source  on resume, drop old single-source FBs + re-extract them

These flags must be guarded so a fat-fingered invocation cannot silently corrupt
the checkpoint (e.g. dropping single-source FBs without limiting to single-source).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage2_extract import _validate_mode_flags


def test_only_convergent_and_only_single_source_are_mutually_exclusive() -> None:
    """Combining the two mode flags must fail fast (before any extraction)."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        _validate_mode_flags(True, True, False)


def test_reset_single_source_requires_only_single_source() -> None:
    """--reset-single-source without --only-single-source would drop single-source
    FBs while still extracting convergent clusters — a silent data-loss footgun."""
    with pytest.raises(ValueError, match="requires --only-single-source"):
        _validate_mode_flags(False, False, True)


def test_valid_combinations_pass() -> None:
    """The sanctioned rerun invocation must pass the guard."""
    _validate_mode_flags(False, True, True)   # the t11 single-source rerun
    _validate_mode_flags(False, False, False)  # default full run
    _validate_mode_flags(True, False, False)   # --only-convergent


if __name__ == "__main__":
    test_only_convergent_and_only_single_source_are_mutually_exclusive()
    test_reset_single_source_requires_only_single_source()
    test_valid_combinations_pass()
    print("single-source flag guard tests OK")
