#!/usr/bin/env python3
"""scripts/check_verification_sequence.py — T-196/D-3136: ONE home for the per-record verification sequence.

WHY THIS RAIL EXISTS (MEASURED 2026-10-23). The S5 per-record sequence — mechanism gate, then the factual
check, then enrichment, then `(status, s5_reason)`, then ISOR, then the score axis, then the epistemic label,
then the facet tier — existed in FOUR files. Each copy had drifted a little:

  pipeline/stage5_verify.py              the owner; the other three claim to mirror it
  pipeline/insert_single_concept.py      no ISOR (cost: the store's only blank `isor` cell), label derived from None
  scripts/reverify_one_row.py            ISOR echoed from the store instead of computed
  scripts/reinject_bug198_singletons.py  a hardcoded verifier identity naming `threshold 0.10` — a threshold the
                                         calibration retired (D-2863 set 0.5), so the copy named a rule it did not run

That is the BUG-978/979/980/981 class: four writers, one rule, four behaviours. The rule now has ONE home
(`pipeline/verify_record.py::verify_one_record`) and this rail is what keeps it single. It fails when:

  (i)   the home does not resolve — a declaration with no referent (D-3034);
  (ii)  a module outside the home CALLS a decision check — the restatement that regenerates the class. The two
        decision checks are `check_mechanism_quality` and `deberta_check`, because they decide WHICH stage
        answered and what its outcome MEANS. `_check_enrichment_quality` is a score input, not a decision, so
        the re-derivation rails may keep asking it: they re-derive a record, they never run the sequence;
  (iii) the home no longer preserves the ORDER it declares — a failing mechanism gate must BE the factual
        verdict and must never ask the NLI (MEASURED: 2,086/2,086 stored rows whose record carries
        mechanism_quality=false are QUARANTINE — there is no counter-example);
  (iv)  the home re-types the score axis — its confidence must be the derivation's (ceiling 0.60 without an
        ISOR rating), never the raw NLI score (the 0.9885 that BUG-980 wrote);
  (v)   a derived cell comes back blank, or disagrees with its declared deriver — a blank no reader can
        interpret is the empty slot D-2952 refuses.

The census reads CALLS from the AST, never from text: a docstring that names a check is a sentence, and a
sentence is not a call (the first draft of this rail matched its own documentation).

READ-ONLY. It writes no store, no artifact and no receipt (BUG-563: a health rail must not dirty the worktree it
is judged by).

Exit: 0 = the rule has one home and the home still behaves; 1 = a named fault (fail closed, C16).
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Any

ROOT: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# THE DECLARED HOMES this rail reads: the facet deriver (D2622) and the quarantine cap (D2310).
from pipeline.pipeline_paths import S5_QUARANTINE_CONF_CAP  # noqa: E402
from pipeline.practicality import classify_practicality  # noqa: E402

HOME_MODULE: str = "pipeline/verify_record.py"
HOME_FUNCTION: str = "verify_one_record"
#: The module that DEFINES the instruments by necessity; naming them here is not restating the rule.
DEFINITION_MODULE: str = "pipeline/stage5_verify.py"
#: The two checks that DECIDE which stage answered. A third caller of either is a fifth truth.
DECISION_CHECKS: frozenset[str] = frozenset({"check_mechanism_quality", "deberta_check"})
#: The live surface a writer can live in. History (archive/, temp/, backup/) is read as history, never as code.
SCAN_ROOTS: tuple[str, ...] = ("pipeline", "scripts")


def _python_files() -> list[Path]:
    """Return every live .py file the census governs (pipeline/ + scripts/, no caches, no history)."""
    out: list[Path] = []
    for root in SCAN_ROOTS:
        for path in (ROOT / root).rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if "/__pycache__/" in rel:
                continue
            out.append(path)
    return sorted(out)


def _called_names(tree: ast.AST) -> set[str]:
    """Return the bare names this module CALLS (`f(...)` and `mod.f(...)` both yield `f`)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            names.add(func.attr)
        elif isinstance(func, ast.Name):
            names.add(func.id)
    return names


def check_restatements() -> list[str]:
    """Fault (ii): any module other than the home CALLING a decision check is a second truth (C21)."""
    faults: list[str] = []
    allowed = {HOME_MODULE, DEFINITION_MODULE}
    for path in _python_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in allowed:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:  # C16: a file we cannot parse is a fault, never a silent skip
            faults.append(f"{rel}: cannot be parsed ({exc.msg} at line {exc.lineno})")
            continue
        offenders = sorted(_called_names(tree) & DECISION_CHECKS)
        for name in offenders:
            faults.append(f"{rel}: calls {name}() outside the ONE home (T-196/D-3136)")
    return faults


def _fixture(**over: Any) -> dict[str, Any]:
    """A minimal but VALID FB: long mechanism, non-tautological, enrichment fields present, one source."""
    fb: dict[str, Any] = {
        "fb_id": "f" * 64,
        "name": "Rail Fixture",
        "definition": "A fixture concept used to assert an ordering invariant of the verification sequence.",
        "mechanism": (
            "The sequence moves from the cheapest measurement to the most expensive one, because a regex gate "
            "that already contradicts the claim makes the entailment model's opinion irrelevant, and asking it "
            "anyway would let a low-precision score outvote a deterministic refusal."
        ),
        "application": (
            "Use this fixture whenever a control must observe which stage of the sequence answered, and not how "
            "confident a downstream model felt about the wording of a claim."
        ),
        "failure_mode": (
            "The control silently passes because a check answered from an empty fixture, so the assertion it "
            "makes is never exercised and the rail becomes a comment that prints a green line."
        ),
        "boundary": "Does not apply to a claim-free role, whose axis is ABSENT by D-2942.",
        "consequence": "A restated sequence would ship as a behaviour change nobody ruled on.",
        "discipline": "Software Engineering",
        "domains": ["verification"],
        "content_type": "principle",
        "evidence": "cited",
        "source_ids": ["rail-fixture-source-1"],
        "source_books": ["Rail Fixture Source"],
        "evidence_passages": ["The cheapest decisive measurement runs first, and its verdict is final."],
        "is_summary": 0,
        "is_convergent": 0,
    }
    fb.update(over)
    return fb


def _with_nli_stub(expected: tuple[bool, float, str]):
    """Install a counting stub for the NLI and return (restore, calls)."""
    from pipeline import stage5_verify

    original = stage5_verify.deberta_check
    calls: list[dict[str, Any]] = []

    def stub(fb: dict) -> tuple[bool, float, str]:
        calls.append(dict(fb))
        return expected

    stage5_verify.deberta_check = stub

    def restore() -> None:
        stage5_verify.deberta_check = original

    return restore, calls


def check_ordering() -> list[str]:
    """Faults (iii)-(v): the home must keep the declared order and the declared derivations."""
    faults: list[str] = []
    try:
        from pipeline.verify_record import verify_one_record
    except Exception as exc:  # noqa: BLE001 — an unimportable home IS the fault this rail reports
        return [f"{HOME_MODULE}: cannot import {HOME_FUNCTION} ({type(exc).__name__}: {exc})"]

    # (iii-a) a failing mechanism gate IS the factual verdict, and the NLI is never asked
    restore, calls = _with_nli_stub((True, 0.99, "ENTAIL"))
    try:
        short = verify_one_record(_fixture(mechanism="Too short to be a mechanism."))
    finally:
        restore()
    if short.fact_passed:
        faults.append("ORDER: a failing mechanism gate produced fact_passed=True (S5's order lost)")
    if short.verification_method != "mech_quality":
        faults.append(f"ORDER: a failing mechanism gate must name method 'mech_quality', got {short.verification_method!r}")
    if calls:
        faults.append(f"ORDER: the NLI was ASKED {len(calls)} time(s) after the mechanism gate already failed")
    if short.status != "QUARANTINE":
        faults.append(f"ORDER: a failed mechanism gate must be QUARANTINE, got {short.status!r}")

    # (iii-b) an S4 classification failure short-circuits before the gate result is used
    restore, calls = _with_nli_stub((True, 0.99, "ENTAIL"))
    try:
        failed = verify_one_record(_fixture(classification_status="FAILED", classification_error="menu miss"))
    finally:
        restore()
    if failed.verification_method != "classification_failed":
        faults.append(
            f"ORDER: a FAILED classification must name method 'classification_failed', got {failed.verification_method!r}"
        )
    if calls:
        faults.append("ORDER: the NLI was asked for a row whose S4 classification FAILED (D2405)")

    # (iii-c) contaminated evidence short-circuits too
    restore, calls = _with_nli_stub((True, 0.99, "ENTAIL"))
    try:
        contaminated = verify_one_record(_fixture(), severe_evidence_ids={_fixture()["fb_id"]})
    finally:
        restore()
    if contaminated.verification_method != "evidence_contaminated":
        faults.append(
            f"ORDER: severe evidence must name method 'evidence_contaminated', got {contaminated.verification_method!r}"
        )
    if calls:
        faults.append("ORDER: the NLI was asked for a row whose evidence is contaminated (BUG-181#1)")

    # (iv) the score axis is the DERIVATION's, never the raw NLI score (BUG-980)
    restore, _ = _with_nli_stub((True, 0.9885, "ENTAIL"))
    try:
        clean = verify_one_record(_fixture())
    finally:
        restore()
    if clean.verification_method != "deberta-nli":
        faults.append(f"ORDER: a clean row must name method 'deberta-nli', got {clean.verification_method!r}")
    if clean.status != "PASS":
        faults.append(f"ORDER: a passed factual check must derive PASS, got {clean.status!r}")
    # BUG-980's exact shape: `confidence = round(nli_score, 4)` — the axis copied a CHECK's score instead of deriving.
    if clean.confidence_score == clean.fact_score and clean.fact_score > 0.0:
        faults.append(
            f"SCORE AXIS: confidence {clean.confidence_score} EQUALS the raw NLI score — the check's score was "
            "re-typed as the derivation's (BUG-980)"
        )
    # and the declared CAP must hold on a quarantined row (BUG-980 wrote 0.9885 onto a FAILED verdict).
    if short.confidence_score > float(S5_QUARANTINE_CONF_CAP):
        faults.append(
            f"SCORE AXIS: a QUARANTINED row carries confidence {short.confidence_score}, above the declared cap "
            f"{S5_QUARANTINE_CONF_CAP} (BUG-980)"
        )

    # (v) every derived cell is non-blank and AGREES with its declared deriver
    if clean.practicality != classify_practicality(_fixture()):
        faults.append(
            f"CELL: practicality {clean.practicality!r} disagrees with the declared deriver "
            f"({classify_practicality(_fixture())!r}) — a re-typed facet (BUG-981)"
        )
    if not clean.epistemic_status:
        faults.append("CELL: epistemic_status came back blank (D2284 label unwritten)")
    if not clean.verifier_model or "threshold" not in clean.verifier_model:
        faults.append(f"CELL: verifier_model {clean.verifier_model!r} does not name the threshold it ran under")
    if not clean.isor or "rating" not in clean.isor:
        faults.append("CELL: isor came back empty — the row would be the store's only blank ISOR cell (BUG-981 class)")

    # (vi) THE INPUT CONTRACT: a STORE-SHAPED row (JSON text) must derive what the NATIVE row derives. MEASURED
    #      twice in one day: `evidence_passages` as text made the NLI answer "No evidence" (BUG-979) and
    #      `source_ids` as text made ISOR report n_sources=0 for a row carrying one source id (2026-10-23).
    import json as _json

    native = _fixture()
    store_shaped = _fixture(
        evidence_passages=_json.dumps(native["evidence_passages"]),
        source_ids=_json.dumps(native["source_ids"]),
        source_books=_json.dumps(native["source_books"]),
    )
    restore, _ = _with_nli_stub((True, 0.9, "ENTAIL"))
    try:
        from_store = verify_one_record(store_shaped)
    finally:
        restore()
    if from_store.isor.get("n_sources") != clean.isor.get("n_sources"):
        faults.append(
            f"INPUT CONTRACT: a store-shaped row derives n_sources={from_store.isor.get('n_sources')} while the "
            f"native row derives {clean.isor.get('n_sources')} — the JSON-TEXT column was read as a string "
            "(the BUG-979 trap, MEASURED again on source_ids 2026-10-23)"
        )
    if from_store.confidence_score != clean.confidence_score:
        faults.append(
            f"INPUT CONTRACT: confidence differs between the native ({clean.confidence_score}) and store-shaped "
            f"({from_store.confidence_score}) row — the score axis consumed a shape-dependent ISOR"
        )

    # the two typed faces of one record: the store takes JSON text + int flags, the checkpoint takes natives
    store = clean.store_cells()
    checkpoint = clean.checkpoint_cells()
    if not isinstance(store.get("verification_results"), str):
        faults.append("FACE: store_cells().verification_results must be JSON TEXT for the store")
    if not isinstance(checkpoint.get("verification_results"), list):
        faults.append("FACE: checkpoint_cells().verification_results must stay a LIST for the checkpoint")
    if store.get("needs_human_review") not in (0, 1):
        faults.append("FACE: store_cells().needs_human_review must be 0/1 for the store column")
    if not isinstance(checkpoint.get("needs_human_review"), bool):
        faults.append("FACE: checkpoint_cells().needs_human_review must stay a BOOL for the checkpoint")
    return faults


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--census", action="store_true", help="print the scanned file count and exit 0")
    args = ap.parse_args()

    files = _python_files()
    if args.census:
        print(f"scanned {len(files)} live .py file(s) under {', '.join(SCAN_ROOTS)}")
        return 0

    faults = check_restatements()
    faults += check_ordering()

    if faults:
        print(f"FAIL verification-sequence: {len(faults)} fault(s) | scanned {len(files)} live .py file(s)")
        for fault in faults:
            print(f"  - {fault}")
        return 1
    print(
        f"ok check-verification-sequence: the per-record sequence has ONE home ({HOME_MODULE}), no module outside "
        f"it calls a decision check, and the home preserves S5's declared order (scanned {len(files)} file(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
