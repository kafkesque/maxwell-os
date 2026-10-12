#!/usr/bin/env python3
"""scripts/check_serving_gate.py - the D274a CI invariant, as a rail over the LIVE store (BUG-499).

WHY: D274a ruled that status is a function of the VERIFICATION RECORD and required a CI invariant
(status=PASS implies factual.passed and s5_reason not in the negative set). The derivation and its
assertion exist in pipeline/serving_gate.py and the WRITER calls them
(scripts/apply_serving_gate.py:97) - but until this rail NOTHING evaluated a single STORED row, so the
invariant could never fail. A rule checkable only by the code that writes the data is the BUG-482
class: the rail built to be un-silent was itself silent.

WHAT THIS DOES NOT DO: it does not re-implement any rule. It imports derive_status AND
derive_epistemic_status from the ONE implementation (C21), so a change to a rule changes this check in
the same commit. A second implementation here would be a second truth.

OUTCOME PER ROW (fail-closed, C16 - an un-evaluable row is NOT a pass):
  MATCH           the stored status equals what the verification record derives
  STATUS_MISMATCH the row was written by something other than the one writer (DEFECT)
  REASON_MISMATCH a PASS row whose s5_reason is not the reason the record implies (DEFECT)
  UNDECIDABLE     no factual check and no dedup marker: the record cannot be evaluated (DEFECT)

BUG-499, RULED 2026-09-25 - the ontology question (which of status / epistemic_status is canonical).
MEASURED: epistemic_status is a FORWARD determinant of status (every label maps to exactly ONE status)
AND every stored label re-derives from the SAME record (factual.passed + isor.rating) with 0/7,995
mismatch. The label is therefore a strict REFINEMENT of the status partition - the 1:1 is a theorem
about one shared record, not a hidden gate - and the honest declaration is co_derived, under which this
rail must PROVE the shared source by re-deriving every stored label. The three relationships below are
declared in config/serving_gate.yaml (a config act, C12 - never an edit in this file):
  unruled        report the coupling and exit 2 (owner-owed, loud not fatal)
  derived_mirror status is declared a mirror OF the label - shape only, checks NO provenance
  independent    the two must decouple, so a 1:1 is a DEFECT (exit 1)
  co_derived     both are functions of the SAME record; the rail re-derives the label per row

Exit: 0 ok | 1 defect | 2 owner-owed (loud, NOT fatal - BUG-457 convention).
Usage: python3 scripts/check_serving_gate.py [--selftest]
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.serving_gate import (  # noqa: E402 - the ONE rule, imported never re-implemented (C21)
    MATCH,
    REASON_MISMATCH,
    STATUS_MISMATCH,
    UNDECIDABLE,
    derive_epistemic_status,
    derive_status,
    factual_check,
    load_config,
    load_label_config,
    negative_reasons,
    store_verdict,
)

GATE_CONFIG = ROOT / "config" / "serving_gate.yaml"
EXIT_OK, EXIT_DEFECT, EXIT_OWED = 0, 1, 2
PASS = "PASS"
LABEL_MATCH, LABEL_MISMATCH = "LABEL_MATCH", "LABEL_MISMATCH"
LABEL_RELATIONSHIPS = ("unruled", "derived_mirror", "independent", "co_derived")
REQUIRED_KEYS = (
    "db", "table", "col_status", "col_reason", "col_verification", "col_duplicate_of", "col_label",
    "col_isor", "max_status_mismatch", "max_reason_mismatch", "max_undecidable", "max_label_mismatch",
    "label_relationship",
)


def load_rail_config() -> dict[str, Any]:
    """The declared rail block. Raises SystemExit naming any missing key - a rail with a guessed
    path or column is a rail that can check the wrong table (C12). An unknown label_relationship is
    fatal too: a rail that does not understand its own declaration cannot check anything (C16)."""
    doc = yaml.safe_load(GATE_CONFIG.read_text(encoding="utf-8"))
    rail = (doc or {}).get("rail")
    if not isinstance(rail, dict):
        raise SystemExit("FAIL check-serving-gate: config/serving_gate.yaml has no 'rail' block")
    missing = [k for k in REQUIRED_KEYS if k not in rail]
    if missing:
        raise SystemExit("FAIL check-serving-gate: config/serving_gate.yaml#rail is missing " + ", ".join(missing))
    if str(rail["label_relationship"]) not in LABEL_RELATIONSHIPS:
        raise SystemExit("FAIL check-serving-gate: rail.label_relationship=" + str(rail["label_relationship"])
                         + " is not one of " + ", ".join(LABEL_RELATIONSHIPS))
    return rail


def load_ontology() -> dict[str, Any]:
    """The declared label ontology, fail-closed: an unreadable rule is not a rule (C16/BUG-499)."""
    try:
        return load_label_config()
    except ValueError as exc:
        raise SystemExit("FAIL check-serving-gate: the declared label ontology is malformed: " + str(exc))


# BUG-502: this file used to keep its own copy of the row comparator. Two implementations of one
# rule are two truths, so the comparison now lives in pipeline/serving_gate.py::store_verdict and
# is imported above; the alias keeps the call sites and the known-answer controls unchanged, which
# is what proves the refactor preserved behaviour.
evaluate_row = store_verdict


def rating_of(isor_raw: object) -> str | None:
    """Read the ISOR rating from the stored column (JSON string or parsed dict); None when absent."""
    isor = isor_raw
    if isinstance(isor, str):
        try:
            isor = json.loads(isor)
        except (json.JSONDecodeError, TypeError):
            return None
    return isor.get("rating") if isinstance(isor, dict) else None


def evaluate_label(
    stored_label: object, verification_results: object, isor_raw: object, lab_cfg: dict[str, Any]
) -> tuple[str, str]:
    """BUG-499: re-derive the label from the SAME record and compare with what is stored.

    This is what makes co_derived a rail with teeth rather than an assertion of intent: it inspects
    the label's PROVENANCE, not just the shape of its coupling with status. A stored label that no
    longer re-derives from the record was hand-set (a second writer) or the one rule moved and the
    rows did not - both are drift. Absent record: the status rail already fails that row closed.
    """
    factual = factual_check(verification_results)
    if factual is None:
        return LABEL_MATCH, ""
    passed = bool(factual.get("passed"))
    rating = rating_of(isor_raw)
    expected = derive_epistemic_status(passed, rating, lab_cfg)
    if str(stored_label or "") != expected:
        return LABEL_MISMATCH, (f"stored label {str(stored_label)!r} but the record derives {expected!r} "
                               f"(fact_passed={passed}, isor_rating={rating!r})")
    return LABEL_MATCH, ""


def read_rows(rail: dict[str, Any]) -> tuple[list[tuple[Any, ...]], list[str]]:
    """Read (status, reason, verification, duplicate_of, label, isor, content_type) READ-ONLY.

    Returns (rows, schema_notes). Raises SystemExit when a declared column does not exist - a declared
    column that is absent means this rail is checking a different table than the one it claims.
    READ-ONLY BY CONSTRUCTION (mode=ro): a check must not be able to write (BUG-491 class, R-D410).
    """
    db = ROOT / str(rail["db"])
    if not db.exists():
        raise SystemExit(f"FAIL check-serving-gate: declared db {rail['db']} does not exist")
    table = str(rail["table"])
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        present = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        keys = ("col_status", "col_reason", "col_verification", "col_duplicate_of", "col_label",
                "col_isor", "col_content_type")
        cols = [str(rail[k]) for k in keys]
        missing = [c for c in cols if c not in present]
        if missing:
            raise SystemExit(f"FAIL check-serving-gate: declared column(s) absent from {table}: {missing}")
        rows = list(conn.execute(f"SELECT {', '.join(cols)} FROM {table}"))
    finally:
        conn.close()
    return rows, [f"{table} carries {len(present)} column(s)"]


def selftest(cfg: dict[str, Any], neg: set[str], lab_cfg: dict[str, Any]) -> int:
    """KNOWN-ANSWER CONTROLS through the same classifiers the DB rows go through.

    A guardrail that has never been observed failing is not a guardrail. Each control names the class
    it must produce, so a classifier that has stopped detecting that class fails LOUDLY here instead of
    going quiet on the live store.
    """
    good = '[{"check_name": "factual", "passed": true, "detail": "ENTAIL 3/3"}]'
    bad_nli = '[{"check_name": "factual", "passed": false, "detail": "CONTRA 3/3"}]'
    no_factual = '[{"check_name": "mechanism", "passed": true, "detail": "ok"}]'
    controls = [
        ("a verified row stored as PASS is a MATCH", (PASS, "entail", good, None, None), MATCH),
        ("PASS with factual.passed False is a STATUS_MISMATCH", (PASS, "entail", bad_nli, None, None), STATUS_MISMATCH),
        ("PASS carrying the negative reason contra is a REASON_MISMATCH", (PASS, "contra", good, None, None), REASON_MISMATCH),
        ("a verified row stored as QUARANTINE is a STATUS_MISMATCH", ("QUARANTINE", "neutral", good, None, None), STATUS_MISMATCH),
        ("no factual check at all is UNDECIDABLE, never a pass", (PASS, "entail", no_factual, None, None), UNDECIDABLE),
        # D-2942 (D2590) known-answer controls: a disposition nobody has watched fire is a comment.
        ("a principle with NO record is still UNDECIDABLE (the scoping control)",
         (PASS, "entail", no_factual, None, "principle"), UNDECIDABLE),
        ("a role with no factual claim + no record derives not-applicable, NOT undecidable",
         ("QUARANTINE", "s5_not_applicable", no_factual, None, "process_template"), MATCH),
        ("the same role stored with the WRONG reason is a REASON_MISMATCH",
         ("QUARANTINE", "unknown", no_factual, None, "tool_instruction"), REASON_MISMATCH),
        ("a role with no factual claim can NEVER be stored as PASS",
         (PASS, "entail", no_factual, None, "growth_edge"), STATUS_MISMATCH),
    ]
    failed = 0
    for name, row, want in controls:
        got, detail = evaluate_row(row[0], row[1], row[2], row[3], cfg, neg, content_type=row[4])
        if got != want:
            failed += 1
            print(f"FAIL check-serving-gate --selftest: {name} -> {got} ({detail}); expected {want}")
        else:
            print(f"  control ok: {got:15s} {name}")
    label_controls = [
        ("a strong-ISOR passed row derives corroborated", ("corroborated", good, '{"rating": "strong"}'), LABEL_MATCH),
        ("a strong-ISOR failed row derives cross-source-unverified",
         ("cross-source-unverified", bad_nli, '{"rating": "strong"}'), LABEL_MATCH),
        ("a weak-ISOR passed row derives source-supported", ("source-supported", good, '{"rating": "weak"}'), LABEL_MATCH),
        ("a weak-ISOR failed row derives speculative", ("speculative", bad_nli, '{"rating": "weak"}'), LABEL_MATCH),
        ("a HAND-SET label contradicts the record -> LABEL_MISMATCH (BUG-499 teeth)",
         ("corroborated", bad_nli, '{"rating": "weak"}'), LABEL_MISMATCH),
    ]
    for name, row, want in label_controls:
        got, detail = evaluate_label(row[0], row[1], row[2], lab_cfg)
        if got != want:
            failed += 1
            print(f"FAIL check-serving-gate --selftest: {name} -> {got} ({detail}); expected {want}")
        else:
            print(f"  control ok: {got:15s} {name}")
    total = len(controls) + len(label_controls)
    if failed:
        print(f"FAIL check-serving-gate --selftest: {failed} of {total} known-answer control(s) did not fire")
        return EXIT_DEFECT
    print(f"ok check-serving-gate --selftest: {total}/{total} known-answer control(s) fire")
    return EXIT_OK


def main() -> int:
    """Evaluate every stored row, report the label coupling, and exit 0/1/2 (see module docstring)."""
    ap = argparse.ArgumentParser(description="D274a serving-gate CI invariant + BUG-499 label rail.")
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    args = ap.parse_args()

    cfg = load_config()
    neg = negative_reasons(cfg)
    lab_cfg = load_ontology()
    if args.selftest:
        return selftest(cfg, neg, lab_cfg)

    rail = load_rail_config()
    rows, notes = read_rows(rail)
    tally: collections.Counter[str] = collections.Counter()
    label_tally: collections.Counter[str] = collections.Counter()
    xtab: collections.Counter[tuple[str, str]] = collections.Counter()
    samples: dict[str, list[str]] = collections.defaultdict(list)
    label_samples: list[str] = []
    for status, reason, vr, dup, label, isor, content_type in rows:
        verdict, detail = evaluate_row(status, reason, vr, dup, cfg, neg, content_type=content_type)
        tally[verdict] += 1
        xtab[(str(label or ""), str(status or ""))] += 1
        if verdict != MATCH and len(samples[verdict]) < 3:
            samples[verdict].append(f"{str(label or '')}={str(status or '')}: {detail}")
        lv, ld = evaluate_label(label, vr, isor, lab_cfg)
        label_tally[lv] += 1
        if lv == LABEL_MISMATCH and len(label_samples) < 3:
            label_samples.append(ld)

    bad = {
        "status mismatch": tally[STATUS_MISMATCH] - int(rail["max_status_mismatch"]),
        "reason mismatch": tally[REASON_MISMATCH] - int(rail["max_reason_mismatch"]),
        "undecidable": tally[UNDECIDABLE] - int(rail["max_undecidable"]),
        "label mismatch": label_tally[LABEL_MISMATCH] - int(rail["max_label_mismatch"]),
    }
    over = {k: v for k, v in bad.items() if v > 0}
    n = len(rows)

    forward: dict[str, set[str]] = collections.defaultdict(set)
    for (label, status), _c in xtab.items():
        forward[label].add(status)
    label_is_function = bool(forward) and all(len(v) == 1 for v in forward.values())
    relationship = str(rail["label_relationship"])

    if over:
        for cls, verdict in (("status mismatch", STATUS_MISMATCH), ("reason mismatch", REASON_MISMATCH),
                             ("undecidable", UNDECIDABLE)):
            if bad[cls] > 0:
                print(f"FAIL check-serving-gate: {tally[verdict]} row(s) {cls} over the declared baseline "
                      f"({rail['max_' + cls.replace(' ', '_')]}); the stored status was not written by the one "
                      f"writer D274a defines; samples {samples[verdict]}")
        if bad["label mismatch"] > 0:
            print(f"FAIL check-serving-gate: {label_tally[LABEL_MISMATCH]} row(s) label mismatch over the "
                  f"declared baseline ({rail['max_label_mismatch']}): the stored label does NOT re-derive from "
                  f"the same record, so either a second writer set it or the one rule moved and the rows did "
                  f"not (BUG-499); samples {label_samples}")
        return EXIT_DEFECT

    headline = (f"{n} row(s) re-derived from the verification record: {tally[MATCH]} MATCH, "
                f"{tally[STATUS_MISMATCH]} status mismatch, {tally[REASON_MISMATCH]} reason mismatch, "
                f"{tally[UNDECIDABLE]} undecidable ({'; '.join(notes)})")
    counted = {k: sorted(v) for k, v in forward.items()}

    if relationship == "independent" and label_is_function:
        print(f"FAIL check-serving-gate: rail.label_relationship=independent but the LABEL column still "
              f"determines status 1:1: {counted} - a label-derived gate is D274a's original defect "
              f"(BUG-499). {headline}")
        return EXIT_DEFECT
    if relationship == "co_derived" and not label_is_function:
        print(f"FAIL check-serving-gate: rail.label_relationship=co_derived declares that the label REFINES "
              f"status, but it does not (a label maps to several statuses): {counted} - the declared "
              f"ontology and the store disagree (BUG-499). {headline}")
        return EXIT_DEFECT
    if relationship == "unruled" and label_is_function:
        print(f"owner_owed check-serving-gate: the LABEL column epistemic_status is a FORWARD determinant of "
              f"status (every label maps to exactly one status: {counted}) - D274a forbade a LABEL column "
              f"from gating serving, and this is a MEASURED coupling, not a proven cause. The invariant "
              f"itself HOLDS. Declare rail.label_relationship in config/serving_gate.yaml (co_derived = both "
              f"derive from the SAME record and this rail must re-derive the label; derived_mirror = shape "
              f"only; independent = it must decouple, and then this is a DEFECT) [BUG-499]. {headline}")
        return EXIT_OWED
    markers = {
        "co_derived": (f" [DECLARED co_derived: all {label_tally[LABEL_MATCH]} stored label(s) re-derived from "
                       f"the SAME record, {label_tally[LABEL_MISMATCH]} mismatch - the 1:1 coupling is a "
                       f"theorem about one shared record, not a gate (BUG-499)]"),
        "derived_mirror": (" (DECLARED derived_mirror: the 1:1 is declared intended - shape only, so the "
                           "label's own provenance is NOT checked)") if label_is_function else "",
    }
    print(f"ok check-serving-gate: {headline}{markers.get(relationship, '')}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
