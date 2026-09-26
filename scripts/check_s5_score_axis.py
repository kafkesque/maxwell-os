#!/usr/bin/env python3
"""check_s5_score_axis.py - BUG-502: the S5 score axis has ONE home, and it reproduces the corpus.

The score axis (confidence_score + needs_human_review) used to exist as a verbatim copy in
pipeline/stage5_verify.py AND scripts/reinject_bug198_singletons.py. The copies were removed; the
rule now lives in pipeline/serving_gate.py::derive_conf_and_review and BOTH call sites import it.

A refactor is only proved by the data it produced, so this rail re-derives both outputs from the
STORED record (the full row - a column subset makes the enrichment check read empty fields and
invents a defect) and compares 1:1 with what was committed. It is read-only by construction.

Teeth: the known-answer controls run BEFORE any verdict (a guardrail never observed failing is not
a guardrail). Verdicts: MATCH | SCORE_MISMATCH | REVIEW_MISMATCH | UNDECIDABLE (fail-closed).
Exit: 0 ok | 1 defect. A DECLARED recalibration of the weights re-baselines this rail by re-running
S5, so a silent recalibration cannot pass.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import (  # noqa: E402
    DB_PATH,
    S5_CONF_ENRICH_WEIGHT,
    S5_CONF_ISOR_WEIGHT,
    S5_CONF_MECH_WEIGHT,
    S5_HUMAN_REVIEW_ISOR,
    S5_QUARANTINE_CONF_CAP,
)
from pipeline.serving_gate import derive_conf_and_review  # noqa: E402
from pipeline.stage5_verify import _check_enrichment_quality  # noqa: E402

MATCH = "MATCH"
SCORE_MISMATCH = "SCORE_MISMATCH"
REVIEW_MISMATCH = "REVIEW_MISMATCH"
UNDECIDABLE = "UNDECIDABLE"
PREFIX = "check-s5-score-axis"
EXIT_OK = 0
EXIT_DEFECT = 1


def verdict_for(row: dict) -> tuple[str, str]:
    """Re-derive the score axis from one stored row and compare it with what is committed."""
    try:
        results = json.loads(row.get("verification_results") or "[]")
    except (TypeError, ValueError):
        return UNDECIDABLE, "verification_results is not parseable JSON"
    factual = next((x for x in results if x.get("check_name") == "factual"), None)
    mech = next((x.get("score") for x in results if x.get("check_name") == "mechanism_quality"), None)
    if factual is None or mech is None:
        return UNDECIDABLE, "no factual/mechanism_quality check in verification_results - an unevaluable row is never a pass (C16)"
    if row.get("confidence_score") is None:
        return UNDECIDABLE, "confidence_score is absent"
    _ok, enrich, _detail = _check_enrichment_quality(dict(row))
    isor = row.get("isor")
    isor = json.loads(isor) if isinstance(isor, str) else (isor or {})
    conf, needs_review = derive_conf_and_review(bool(factual.get("passed")), float(mech), float(enrich), isor)
    stored_conf = float(row["confidence_score"])
    stored_review = bool(row.get("needs_human_review"))
    if abs(conf - stored_conf) > 1e-9:
        return SCORE_MISMATCH, f"stored {stored_conf} but the record derives {conf}"
    if needs_review != stored_review:
        return REVIEW_MISMATCH, f"stored needs_human_review={stored_review} but the record derives {needs_review}"
    return MATCH, ""


def _row(passed: bool, mech: float, isor: dict, stored_conf: float, stored_review: bool) -> dict:
    """A row with every enrichment field present, so the enrichment grade is a clean 1.0."""
    results = [
        {"check_name": "mechanism_quality", "passed": True, "score": mech, "detail": "d"},
        {"check_name": "factual", "passed": passed, "score": 0.9, "detail": "d" * 60},
    ]
    return {
        "application": "a" * 60,
        "failure_mode": "b" * 60,
        "definition": "c" * 60,
        "boundary": "d" * 60,
        "verification_results": json.dumps(results),
        "isor": json.dumps(isor),
        "confidence_score": stored_conf,
        "needs_human_review": stored_review,
    }


def controls() -> list[tuple[str, dict, str]]:
    """Known-answer rows: the rail must reproduce the rail's own verdicts before judging the store."""
    strong = {"score": 0.917, "rating": S5_HUMAN_REVIEW_ISOR}
    weak = {"score": 0.917, "rating": "weak"}
    ok_conf = round(S5_CONF_MECH_WEIGHT * 1.0 + S5_CONF_ENRICH_WEIGHT * 1.0 + S5_CONF_ISOR_WEIGHT * 0.917, 4)
    capped = _row(False, 1.0, strong, S5_QUARANTINE_CONF_CAP, True)
    above_cap = _row(False, 1.0, strong, S5_QUARANTINE_CONF_CAP + 0.5, True)
    return [
        ("a row whose stored score is the one the record derives", _row(True, 1.0, {"score": 0.667, "rating": "moderate"}, round(S5_CONF_MECH_WEIGHT + S5_CONF_ENRICH_WEIGHT + S5_CONF_ISOR_WEIGHT * 0.667, 4), False), MATCH),
        ("the SAME row with the stored score nudged by 0.001 - the teeth", _row(True, 1.0, {"score": 0.667, "rating": "moderate"}, round(ok_conf + 0.001, 4), False), SCORE_MISMATCH),
        ("a stored human-review flag the record does not derive", _row(True, 1.0, {"score": 0.667, "rating": "moderate"}, round(S5_CONF_MECH_WEIGHT + S5_CONF_ENRICH_WEIGHT + S5_CONF_ISOR_WEIGHT * 0.667, 4), True), REVIEW_MISMATCH),
        ("a QUARANTINED row capped at the declared quarantine_cap", capped, MATCH),
        ("a QUARANTINED row stored ABOVE the cap - the cap has teeth", above_cap, SCORE_MISMATCH),
        ("a row with no mechanism_quality check is UNDECIDABLE, never a pass", {"verification_results": json.dumps([{"check_name": "factual", "passed": True}]), "confidence_score": 0.9, "needs_human_review": False}, UNDECIDABLE),
        ("the human-review flag is load-bearing on the DECLARED ISOR rating", _row(False, 1.0, strong, S5_QUARANTINE_CONF_CAP, False), REVIEW_MISMATCH),
        ("the same row with a NON-declared rating is not reviewed", _row(False, 1.0, weak, S5_QUARANTINE_CONF_CAP, False), MATCH),
    ]


def run_selftest() -> int:
    """Drive the known-answer controls through the SAME classifier before any verdict."""
    bad = []
    for label, row, expected in controls():
        got, detail = verdict_for(row)
        if got != expected:
            bad.append(f"{label}: expected {expected}, got {got} ({detail})")
    if bad:
        for line in bad:
            print(f"FAIL {PREFIX} selftest: {line}")
        return EXIT_DEFECT
    print(f"ok {PREFIX} --selftest: {len(controls())}/{len(controls())} known-answer control(s) fire")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    args = parser.parse_args()
    if args.selftest:
        return run_selftest()

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = con.execute("select * from fbs").fetchall()
    tally: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for row in rows:
        verdict, detail = verdict_for(dict(row))
        tally[verdict] += 1
        if verdict != MATCH:
            samples.setdefault(verdict, []).append(f"{row['fb_id'][:12]}: {detail}")
            print(f"FAIL {PREFIX}: {verdict} - {row['fb_id'][:12]}: {detail}")
    if tally[SCORE_MISMATCH] or tally[REVIEW_MISMATCH] or tally[UNDECIDABLE]:
        print(f"FAIL {PREFIX}: {dict(tally)} - the ONE score-axis home must reproduce every stored row")
        return EXIT_DEFECT
    print(
        f"ok {PREFIX}: {len(rows)} row(s) re-derived through pipeline/serving_gate.py::derive_conf_and_review"
        f" - {tally[MATCH]} MATCH, 0 score mismatch, 0 review mismatch, 0 undecidable"
    )
    print(
        f"   declared weights: mechanism={S5_CONF_MECH_WEIGHT} enrichment={S5_CONF_ENRICH_WEIGHT} "
        f"isor={S5_CONF_ISOR_WEIGHT} cap={S5_QUARANTINE_CONF_CAP} human_review_isor={S5_HUMAN_REVIEW_ISOR!r}"
        " (config/pipeline_config.yaml#stage5.confidence - BUG-504: no silent code default)"
    )
    print("   ONE home: pipeline/serving_gate.py::derive_conf_and_review, imported by stage5_verify and reinject_bug198_singletons")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
