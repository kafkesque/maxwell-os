#!/usr/bin/env python3
"""check_corroboration_bit.py - D-2993/BUG-775: the CORROBORATION value must EQUAL its own re-derivation.

WHY. `fbs.is_convergent` and `fbs.source_diversity` decide whether a row counts as corroborated, and until D-2993
NOTHING declared where either value is decided: no row in config/derivations.yaml, no parity rail, no home. MEASURED
2026-10-14 on the canonical run (7,640 rows): `is_convergent = 1` <=> `source_diversity >= 2` <=> `|source_ids| >= 2`
on 7,640/7,640 rows - THREE governed columns carrying ONE bit, and the falsifier D-2992 attached to its own ruling
(`P(n_voices >= 2 | is_convergent = 1)`) measured 1.0000 against a counterfactual 0.0000. A value that is exactly
re-derivable must be DECLARED as such: a derivation nobody can recompute is a claim, and a claim that drifts is
discovered as an unexplainable number, never as an error (D-2646, the BUG-499/BUG-502 class).

WHAT IT PROVES, in this order (a control nothing runs is a comment, BUG-492):
  1. the RULE is one function: `recompute_bit` is the only place the rail decides anything - the threshold is READ
     from its declared home (pipeline.pipeline_paths.S15_MIN_SOURCE_DIVERSITY, config stage1_5.min_source_diversity),
     never restated as a literal (C12);
  2. the stored bit EQUALS it on every row of the DECLARED population (the canonical run), so `is_convergent` is a
     FUNCTION of the row's own evidence set rather than the memory of the run that clustered it;
  3. the COUNT agrees with the bit's input: `source_diversity == |source_ids|` - two columns that claim one quantity
     must not drift apart (D-2309: canonical WORKS, never filenames);
  4. the oracle has TEETH: a hand-drifted bit and a hand-drifted count must both be SEEN to fire, and an
     unparseable `source_ids` must be reported rather than read as zero;
  5. the FALSIFIER and the INDEPENDENCE DISAGREEMENT are MEASURED and printed - `P(n>=2 | convergent)` against its
     counterfactual, and how many count-corroborated rows the independence axis rates WEAK. These are measurements,
     never faults: a measure that disagrees with a count is the finding, not a defect (D-2284/D-2309).

SCOPE (stated, because an unstated scope reads as coverage). This rail does NOT decide whether the threshold is
right, does NOT re-cluster anything, and does NOT write: it reads the store read-only and re-derives the two columns
from `source_ids`. It follows that a DECLARED threshold change without a re-derivation is exactly the drift it
reports - the bit is a function of (source_ids, threshold), so moving the threshold moves every stored bit.

Exit: 0 ok | 1 the stored value disagrees with its re-derivation (a WRONG VALUE is not the owner's to decide, D-2642).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.pipeline_paths import (  # noqa: E402
    CANONICAL_RUN,
    DB_PATH,
    S15_MIN_SOURCE_DIVERSITY,
)

PREFIX: str = "check-corroboration-bit"
EXIT_OK, EXIT_DEFECT = 0, 1
#: The declared controls, joined to the labels actually evaluated (two ways): a control that fires without being
#: declared, and a declaration that never fires, are both reported - a count that can drift silently is not a count.
CONTROL_LABELS: tuple[str, ...] = (
    "a_two_work_row_is_convergent",
    "a_one_work_row_is_not_convergent",
    "a_drifted_bit_is_detected",
    "a_drifted_count_is_detected",
    "an_unparseable_source_set_is_reported",
    "the_threshold_comes_from_its_declared_home",
)


def works_of(source_ids: Any) -> int | None:
    """The row's canonical WORK count (D-2185/D-2309) - None when the evidence set cannot be read.

    Args:
        source_ids: the stored `fbs.source_ids` value (a JSON array, a comma string, or absent).

    Returns:
        The number of distinct works, or None when the value is unparseable rather than zero (C16: an unreadable
        value is ABSENT, never a silent 0).
    """
    if source_ids is None:
        return 0
    text: str = str(source_ids).strip()
    if not text:
        return 0
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        if text.startswith("[") or text.startswith("{"):
            return None
        return len({part.strip() for part in text.split(",") if part.strip()})
    if isinstance(parsed, list):
        return len({str(item) for item in parsed})
    if isinstance(parsed, dict):
        return len(parsed)
    return None


def recompute_bit(source_ids: Any, min_sources: int) -> tuple[int, int] | None:
    """The ONE implementation of the corroboration rule: (works, bit) for one row.

    Args:
        source_ids: the stored evidence set.
        min_sources: the DECLARED threshold (its home is config stage1_5.min_source_diversity).

    Returns:
        (works, 1|0), or None when the evidence set cannot be read.
    """
    works: int | None = works_of(source_ids)
    if works is None:
        return None
    return works, int(works >= int(min_sources))


def disagreements(rows: list[dict[str, Any]], min_sources: int) -> tuple[list[str], int]:
    """Re-derive every row and report the ones whose STORED values disagree with the rule.

    Args:
        rows: dicts with fb_id / source_ids / is_convergent / source_diversity.
        min_sources: the declared threshold.

    Returns:
        (one message per disagreeing row, the number of rows whose evidence set could not be read).
    """
    faults: list[str] = []
    unreadable: int = 0
    for row in rows:
        recomputed = recompute_bit(row.get("source_ids"), min_sources)
        if recomputed is None:
            unreadable += 1
            faults.append(f"{row.get('fb_id')}: source_ids cannot be read - an unreadable evidence set is not zero")
            continue
        works, bit = recomputed
        if int(row.get("is_convergent") or 0) != bit:
            faults.append(
                f"{row.get('fb_id')}: stored is_convergent={int(row.get('is_convergent') or 0)} but "
                f"{works} canonical work(s) with threshold {min_sources} recompute to {bit}"
            )
        if int(row.get("source_diversity") or 0) != works:
            faults.append(
                f"{row.get('fb_id')}: stored source_diversity={int(row.get('source_diversity') or 0)} but the "
                f"evidence set holds {works} distinct canonical work(s)"
            )
    return faults, unreadable


def controls(min_sources: int) -> list[tuple[str, list[dict[str, Any]], bool]]:
    """The known-answer controls: every guard named in CONTROL_LABELS, driven through the SAME function."""
    two = json.dumps(["work-a", "work-b"])
    one = json.dumps(["work-a"])
    return [
        ("a_two_work_row_is_convergent",
         [{"fb_id": "c1", "source_ids": two, "is_convergent": 1, "source_diversity": 2}], False),
        ("a_one_work_row_is_not_convergent",
         [{"fb_id": "c2", "source_ids": one, "is_convergent": 0, "source_diversity": 1}], False),
        ("a_drifted_bit_is_detected",
         [{"fb_id": "c3", "source_ids": two, "is_convergent": 0, "source_diversity": 2}], True),
        ("a_drifted_count_is_detected",
         [{"fb_id": "c4", "source_ids": two, "is_convergent": 1, "source_diversity": 7}], True),
        ("an_unparseable_source_set_is_reported",
         [{"fb_id": "c5", "source_ids": "[oops", "is_convergent": 0, "source_diversity": 0}], True),
        ("the_threshold_comes_from_its_declared_home",
         [{"fb_id": "c6", "source_ids": json.dumps(["a", "b"]), "is_convergent": 1, "source_diversity": 2}],
         min_sources != 2),
    ]


def run_selftest(min_sources: int) -> int:
    """Drive every declared control through the SAME re-derivation the live arm uses."""
    faults: list[str] = []
    total: int = 0
    for label, rows, should_fire in controls(min_sources):
        total += 1
        found, _ = disagreements(rows, min_sources)
        if bool(found) != should_fire:
            faults.append(f"{label}: expected fire={should_fire}, got {found}")
    if faults:
        for line in faults:
            print(f"  !!  {line}")
        print(f"FAIL {PREFIX} selftest: {len(faults)} of {total} known-answer control(s) failed")
        return EXIT_DEFECT
    print(f"ok {PREFIX} --selftest: {total}/{total} known-answer control(s) fire")
    return EXIT_OK


def live_rows() -> list[dict[str, Any]]:
    """Every row of the DECLARED population (the canonical run) with the three joined columns, read-only."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [
            dict(row)
            for row in con.execute(
                "SELECT fb_id, source_ids, is_convergent, source_diversity FROM fbs WHERE pipeline_run_id = ?",
                (CANONICAL_RUN,),
            )
        ]
    finally:
        con.close()


def main() -> int:
    """Re-derive the bit on every row of the declared population and report the measurement."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    args = parser.parse_args()
    min_sources: int = int(S15_MIN_SOURCE_DIVERSITY)
    if args.selftest:
        return run_selftest(min_sources)

    rows: list[dict[str, Any]] = live_rows()
    faults, unreadable = disagreements(rows, min_sources)
    convergent: list[dict[str, Any]] = [r for r in rows if int(r.get("is_convergent") or 0) == 1]
    non_convergent: list[dict[str, Any]] = [r for r in rows if int(r.get("is_convergent") or 0) == 0]
    hit: int = sum(1 for r in convergent if (works_of(r.get("source_ids")) or 0) >= min_sources)
    miss: int = sum(1 for r in non_convergent if (works_of(r.get("source_ids")) or 0) >= min_sources)
    print(
        f"   measured: {len(rows)} row(s) on the canonical run {CANONICAL_RUN!r}, threshold {min_sources} "
        f"work(s) (config stage1_5.min_source_diversity)"
    )
    print(
        f"   the bit is EXACT: P(works >= {min_sources} | is_convergent = 1) = {hit}/{len(convergent)} and "
        f"P(works >= {min_sources} | is_convergent = 0) = {miss}/{len(non_convergent)}"
    )
    if faults:
        for line in faults[:10]:
            print(f"FAIL {PREFIX}: {line}")
        if len(faults) > 10:
            print(f"FAIL {PREFIX}: ... and {len(faults) - 10} more")
        print(f"FAIL {PREFIX}: {len(faults)} row(s) whose STORED corroboration disagrees with its re-derivation")
        return EXIT_DEFECT
    print(f"ok {PREFIX}: {len(rows)}/{len(rows)} row(s) re-derive exactly from their OWN evidence set")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
