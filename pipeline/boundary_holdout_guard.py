#!/usr/bin/env python3
"""boundary_holdout_guard.py — D2609 (BUG-233 resolution, option b+).

The D2587 boundary corpus (config/golden/d2587_boundary_corpus.yaml) is an
EVAL-ONLY, rules-regression set for content_type classification. Its 150
example_ids overlap the Tier2 discipline/domain training golden
(stage4_golden_mined.yaml) 150/150 — but that overlap is CROSS-TASK
(discipline/domain TRAINING vs content_type EVAL), and content_type is
rules-based today (not trained), so there is no contamination now.

BUG-233 ruling (D2609): the corpus is NOT a model-eval benchmark. To keep it
future-proof against a FUTURE trained content_type classifier, its example_ids
are declared a HELD-OUT set that any future content_type training MUST exclude.
This module is the single source of truth for that invariant.

Usage:
    from pipeline.boundary_holdout_guard import load_held_out_ids, assert_no_training_overlap
    held = load_held_out_ids()
    assert_no_training_overlap(training_ids, task="content_type")
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterable, Set

import yaml

logger = logging.getLogger(__name__)

# C12: configurable path — default to the canonical repo location, overridable
# via BOUNDARY_CORPUS env var (R5 review: path must not be __file__-derived only).
_BOUNDARY_CORPUS = Path(
    os.environ.get(
        "BOUNDARY_CORPUS",
        Path(__file__).resolve().parent.parent
        / "config" / "golden" / "d2587_boundary_corpus.yaml",
    )
)

# Only content_type training is restricted. The same FB text legitimately
# appears in discipline/domain training (a different label space), so
# discipline/domain training is NOT required to exclude these IDs.
RESTRICTED_TASKS = ("content_type",)


def load_held_out_ids(corpus_path: Path = _BOUNDARY_CORPUS) -> Set[str]:
    """Return the set of example_ids that must never enter content_type training.

    Args:
        corpus_path: Path to the boundary corpus YAML.

    Returns:
        Set of example_id strings declared held-out.

    Raises:
        FileNotFoundError: If the corpus does not exist (fail loud — C16).
        ValueError: If the corpus is missing the held_out_from_training schema field.
    """
    if not corpus_path.exists():
        raise FileNotFoundError(f"Boundary corpus not found: {corpus_path}")
    try:
        data = yaml.safe_load(corpus_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.error("Failed to parse boundary corpus %s: %s", corpus_path, exc)
        raise ValueError(
            f"Boundary corpus {corpus_path} is unreadable/invalid YAML: {exc}"
        ) from exc
    if data.get("held_out_from_training") is not True:
        raise ValueError(
            f"{corpus_path.name} is missing held_out_from_training=true "
            "(D2609 schema field). Re-run the BUG-233 resolution before training."
        )
    cases = data.get("cases", [])
    ids = {
        c.get("example_id")
        for c in cases
        if isinstance(c, dict) and c.get("example_id")
    }
    return ids


def assert_no_training_overlap(training_ids: Iterable[str], *, task: str) -> None:
    """Raise if a training set overlaps the held-out boundary corpus.

    Args:
        training_ids: example_ids in a candidate training set.
        task: Classification task the training set targets (e.g. "content_type",
            "discipline", "domain"). Only RESTRICTED_TASKS are enforced.

    Raises:
        ValueError: If task is restricted and overlap is detected.
    """
    if task not in RESTRICTED_TASKS:
        return
    train_set = set(training_ids)
    held = load_held_out_ids()
    overlap = held & train_set
    if overlap:
        sample = sorted(overlap)[:5]
        raise ValueError(
            f"{task} training set overlaps {len(overlap)} held-out boundary "
            f"example_ids (e.g. {sample}). Exclude them before training — see "
            "pipeline/boundary_holdout_guard.py and BUG-233 (D2609)."
        )


if __name__ == "__main__":
    ids = load_held_out_ids()
    print(f"boundary hold-out ids: {len(ids)}")
