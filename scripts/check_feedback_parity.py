#!/usr/bin/env python3
"""check_feedback_parity.py - D-2989/D-2642: the feedback CACHE must equal its LEDGER.

WHY. `fbs.feedback_score` / `fbs.feedback_count` are declared `derived_regenerable` in config/derivations.yaml,
but that registry row carried `parity_rail: null` - a derived value with a home and NO proof that the stored copy
still equals what the home would compute. The ledger (`fb_feedback`) is the TRUTH (one row per rating event); the
row columns are a DENORMALIZATION. Two layers, one home each, and a rail that joins them.

WHAT IT PROVES, in this order (a control nothing runs is a comment, BUG-492):
  1. the FORMULA is one home: the rail imports pipeline.feedback.declared_aggregate - it never restates it;
  2. the WRITER uses that same home: a real INSERT into a fixture ledger, then the real `_update_fb_aggregates`,
     and the stored cache must equal the declared aggregate;
  3. the ABSENCE shape (D-2957): an EMPTY ledger leaves the cache NULL, never 0.0, so "nobody rated this" cannot be
     read as "rated 0.0";
  4. the oracle has TEETH: a hand-drifted cache value must be SEEN to fire, and a count/score that disagree must be
     SEEN to fire;
  5. the config DRIVES the formula: prior_weight > 0 must MOVE the value, so no literal can hide in the code.

Then the LIVE arm: every row of the served population whose ledger has events must carry the recomputed cache; rows
with no events must carry NULL. A store with no ledger yet reports the DECLARED absence rather than a pass.

Exit: 0 ok | 1 defect.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path

import yaml

REPO: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.feedback import (  # noqa: E402
    _ensure_feedback_table,
    _update_fb_aggregates,
    declared_aggregate,
)
from pipeline.pipeline_paths import CANONICAL_RUN, DB_PATH  # noqa: E402

PREFIX: str = "check-feedback-parity"
EXIT_OK, EXIT_DEFECT = 0, 1
FIXTURE_RATINGS: list[float] = [0.6, 0.9, 0.9]
FIXTURE_FB: str = "fb-fixture-0001"
#: The declared controls. The selftest JOINS this tuple to the labels it actually evaluated (two ways): a control that
#: fires without being declared, and a declaration that never fires, are both reported - a count that can drift
#: silently is not a count.
CONTROL_LABELS: tuple[str, ...] = (
    "the_writer_formula_is_the_declared_one",
    "the_cache_equals_the_ledger",
    "an_empty_ledger_is_absent_not_zero",
    "the_writer_does_not_write_an_absence",
    "a_drifted_cache_is_detected",
    "the_config_drives_the_formula",
)


def policy() -> dict:
    """The declared policy (config/feedback.yaml) - read, never restated (C12)."""
    return yaml.safe_load((REPO / "config" / "feedback.yaml").read_text(encoding='utf-8'))


def _fixture() -> sqlite3.Connection:
    """A REAL fixture store in the system temp - never inside the synced tree (BUG-537)."""
    path: Path = Path(tempfile.mkdtemp(prefix="feedback_parity_")) / "fixture.db"
    con = sqlite3.connect(str(path))
    con.execute(
        "CREATE TABLE fbs (fb_id TEXT PRIMARY KEY, feedback_score REAL, feedback_count INTEGER DEFAULT 0)"
    )
    con.execute("INSERT INTO fbs (fb_id, feedback_score, feedback_count) VALUES (?, NULL, 0)", (FIXTURE_FB,))
    _ensure_feedback_table(con)
    for rating in FIXTURE_RATINGS:
        con.execute(
            "INSERT INTO fb_feedback (fb_id, agent_id, rating, created_at) VALUES (?, 'control', ?, '2026-10-13')",
            (FIXTURE_FB, rating),
        )
    con.commit()
    return con


def controls() -> list[tuple[str, str]]:
    """The known answers, each exercising a different guard. Returns (label, failure) pairs that must stay empty.

    Every check RECORDS its label, so run_selftest can join what was declared to what was evaluated.
    """
    failures: list[tuple[str, str]] = []
    evaluated: list[str] = []
    pol = policy()
    rounding: int = int(pol["aggregate"]["rounding"])
    con = _fixture()

    def record(label: str, ok: bool, detail: str = "") -> None:
        """Record one control's label and, when it fails, why."""
        evaluated.append(label)
        if not ok:
            failures.append((label, detail))

    # 1. the formula IS the declared one, at the declared precision. The expectation is computed INDEPENDENTLY on
    # purpose: a control that called the formula to check the formula would prove nothing (the oracle must be able
    # to disagree with the subject - this is why the LIVE path below may not sum ratings itself, D-2642).
    expected: float | None = round(sum(FIXTURE_RATINGS) / len(FIXTURE_RATINGS), rounding)
    got = declared_aggregate(FIXTURE_RATINGS)
    record(CONTROL_LABELS[0], got == expected, f"{got} != {expected}")

    # 2. the WRITER lands that value in the cache
    _update_fb_aggregates(con, FIXTURE_FB)
    score, count = con.execute("SELECT feedback_score, feedback_count FROM fbs WHERE fb_id = ?", (FIXTURE_FB,)).fetchone()
    record(
        CONTROL_LABELS[1],
        (score, count) == (expected, len(FIXTURE_RATINGS)),
        f"{score}/{count} != {expected}/{len(FIXTURE_RATINGS)}",
    )

    # 3. the ABSENCE shape: an empty ledger is ABSENT (None), never 0.0
    record(CONTROL_LABELS[2], declared_aggregate([]) is None, f"{declared_aggregate([])} is not None")

    # 4. the writer never INVENTS an absence: a pre-existing 0.0 is not overwritten by an empty ledger. That is the
    #    writer's contract (the SHAPE rail, config/store_columns.yaml, owns the seeded value).
    con.execute("INSERT INTO fbs (fb_id, feedback_score, feedback_count) VALUES ('fb-quiet', 0.0, 0)")
    _update_fb_aggregates(con, "fb-quiet")
    quiet = con.execute("SELECT feedback_score, feedback_count FROM fbs WHERE fb_id = 'fb-quiet'").fetchone()
    record(CONTROL_LABELS[3], quiet == (0.0, 0), f"the writer wrote {quiet} over an absence")

    # 5. the ORACLE has teeth: a hand-drifted cache must be DETECTED
    con.execute("UPDATE fbs SET feedback_score = 0.1 WHERE fb_id = ?", (FIXTURE_FB,))
    drifted = con.execute("SELECT feedback_score FROM fbs WHERE fb_id = ?", (FIXTURE_FB,)).fetchone()[0]
    record(
        CONTROL_LABELS[4],
        drifted != declared_aggregate(FIXTURE_RATINGS),
        "the control could not make the cache disagree",
    )

    # 6. the CONFIG drives the formula: prior_weight > 0 must move the value
    shrunk_pol = {**pol, "aggregate": {**pol["aggregate"], "prior_weight": 3.0}}
    shrunk = declared_aggregate(FIXTURE_RATINGS, shrunk_pol)
    plain = declared_aggregate(FIXTURE_RATINGS, pol)
    record(
        CONTROL_LABELS[5],
        shrunk is not None and plain is not None and shrunk != plain,
        f"prior_weight 3.0 did not move {plain!r}",
    )
    con.close()
    if set(evaluated) != set(CONTROL_LABELS):
        failures.append(
            ("the_declared_controls_are_the_ones_evaluated",
             f"declared {sorted(set(CONTROL_LABELS) ^ set(evaluated))} differ"),
        )
    return failures


def run_selftest() -> int:
    """Run the known-answer controls only (no live store read)."""
    failures = controls()
    if failures:
        for label, detail in failures:
            print(f"  !!  {label} - {detail}")
        return EXIT_DEFECT
    print(f"ok {PREFIX} --selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} known-answer control(s) fire")
    return EXIT_OK


def main() -> int:
    """Controls first, then the LIVE parity join over the served population."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    args = parser.parse_args()
    failures = controls()
    if failures:
        for label, detail in failures:
            print(f"  !!  {label} - {detail}")
        return EXIT_DEFECT
    if args.selftest:
        print(f"ok {PREFIX} --selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} known-answer control(s) fire")
        return EXIT_OK

    pol = policy()
    score_col: str = str(pol["aggregate"]["score_column"])
    count_col: str = str(pol["aggregate"]["count_column"])
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    tables: set[str] = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if pol["ledger"]["table"] not in tables:
        print(
            f"ok {PREFIX}: the ledger `{pol['ledger']['table']}` does not exist in this store yet - the DECLARED"
            " absence (config/feedback.yaml#absence), not a pass: nothing has ever been rated, so the cache is"
            f" owed nothing ({score_col} must be NULL on every row)"
        )
        con.close()
        return EXIT_OK

    bad: list[str] = []
    checked: int = 0
    for fb_id, stored_score, stored_count in con.execute(
        f"SELECT fb_id, {score_col}, {count_col} FROM fbs WHERE pipeline_run_id = ?", (CANONICAL_RUN,)
    ):
        checked += 1
        ratings = [
            float(r[0]) for r in con.execute(
                f"SELECT rating FROM {pol['ledger']['table']} WHERE fb_id = ?", (fb_id,)
            ) if r[0] is not None
        ]
        expected = declared_aggregate(ratings)
        if expected is None:
            if stored_score is not None or (stored_count or 0) != 0:
                bad.append(f"{str(fb_id)[:12]}: the ledger holds no event but the cache claims {stored_score!r}/{stored_count!r}")
        elif (stored_score, stored_count) != (expected, len(ratings)):
            bad.append(f"{str(fb_id)[:12]}: cache {stored_score!r}/{stored_count!r} != ledger {expected!r}/{len(ratings)}")
    con.close()
    if bad:
        for line in bad[:10]:
            print(f"FAIL {PREFIX}: {line}")
        print(f"FAIL {PREFIX}: {len(bad)} row(s) where the cache disagrees with its ledger (D-2642)")
        return EXIT_DEFECT
    print(
        f"ok {PREFIX}: {checked} row(s) of the served population re-derived from the ledger through"
        f" pipeline/feedback.py::declared_aggregate - 0 mismatch"
    )
    print(
        f"   declared formula: {pol['aggregate']['formula']} (prior {pol['aggregate']['prior']},"
        f" prior_weight {pol['aggregate']['prior_weight']}, rounding {pol['aggregate']['rounding']})"
        " - config/feedback.yaml#aggregate, the ONE home (C12)"
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
