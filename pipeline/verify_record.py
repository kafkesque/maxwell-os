#!/usr/bin/env python3
"""pipeline/verify_record.py — THE ONE HOME of S5's per-record verification sequence (T-196 / D-3136).

WHY THIS MODULE EXISTS (MEASURED 2026-10-23). The sequence below is a RULE, and it had four implementations:

    pipeline/stage5_verify.py              the owner; the other three claim to mirror it
    pipeline/insert_single_concept.py      no ISOR at all (cost: the store's only blank `isor` cell), a label
                                           derived from `None` instead of the row's rating
    scripts/reverify_one_row.py            ISOR echoed from the store rather than computed
    scripts/reinject_bug198_singletons.py  a hardcoded verifier identity naming `threshold 0.10`, a threshold the
                                           calibration retired (D-2863 set 0.5) — the copy named a rule it did not run

Four copies, four behaviours, five bugs (BUG-978 holes 1-6, BUG-979, BUG-980, BUG-981). A rule with four homes
tells four truths; the fix is not a fourth correction but one home and one caller-side contract.

THE SEQUENCE (declared ORDER, and the order is the rule):

  1. `check_mechanism_quality` — the cheapest decisive gate. Its FAILURE IS the factual verdict: the NLI is
     never asked (MEASURED: 2,086/2,086 stored rows whose record carries `mechanism_quality=false` are
     QUARANTINE — there is no counter-example in the corpus, so any other outcome would be a new state).
  2. Short-circuits that outrank the gate's outcome: an S4 classification FAILURE (D2405) and contaminated
     evidence (BUG-181#1). Both were declared in `stage5_verify.py` and were MISSING from two of the copies.
  3. `deberta_check` — the factual check (DeBERTa-v3-large NLI, D2298), only when 1 and 2 allow it.
  4. `_check_enrichment_quality` — a score input, never a verdict; its failure is APPENDED to the record and
     degrades the score axis (D2277/D2283).
  5. `derive_status` — `(status, s5_reason)` from the record (the ONE serving-gate rule, D274a/D274h).
  6. `isor_score` — BEFORE confidence, because confidence consumes it (D2310).
  7. `derive_conf_and_review` — the score axis, ONE rule with two outputs (BUG-502). Re-typing it here produced
     a confidence equal to the raw NLI score (0.9885) — a value the rule cannot reach without an ISOR rating,
     whose ceiling is 0.60 (BUG-980).
  8. `derive_epistemic_status` — the D2284 label CO-DERIVED from the same record (BUG-499).
  9. `classify_practicality` — the declared deterministic facet tier (D2622); advisory, never a gate.

TWO TYPED FACES OF ONE OUTCOME. The store keeps `verification_results` and `isor` as JSON TEXT and the human-review
flag as 0/1; the S5 checkpoint keeps them native (list/dict/bool). Both faces are produced HERE
(`store_cells()` / `checkpoint_cells()`) so no caller re-types a cell — the conversion is part of the rule, not a
detail each writer retypes.

WHAT THIS MODULE DOES NOT DO. It stamps nothing (no `pipeline_commit`, no schema version): that is the caller's
provenance duty (R14). It writes nothing. It decides no curation. It refuses no role — the claim-free-role refusal
(D-2942) is a REPAIR-tool policy and stays in the tool that owns it.

THE INSTRUMENTS ARE LOOKED UP AT CALL TIME (`from pipeline import stage5_verify`), never bound at import, for two
reasons: `stage5_verify` holds the models and imports this module's neighbours (a module-level import would be a
cycle), and a control must be able to observe WHICH stage answered (`scripts/check_verification_sequence.py`
monkeypatches `deberta_check` and asserts it was never asked after a failed gate).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# THE INSTRUMENTS ARE IMPORTED HERE, never by `stage5_verify` at module level: the cycle is broken on the OTHER
# side, where `run_stage5` imports `verify_one_record` inside the function. This module may therefore be imported
# first (a rail, a repair tool) without a partially-initialised `stage5_verify`.
from pipeline import stage5_verify
from pipeline.pipeline_paths import S5_NLI_MODEL_LARGE, S5_NLI_PASS_THRESHOLD
from pipeline.practicality import classify_practicality
from pipeline.schema_accessor import isor_score
from pipeline.serving_gate import derive_conf_and_review, derive_epistemic_status, derive_status

#: The identity this sequence verifies UNDER. It is DERIVED from the declared model + threshold, never typed:
#: MEASURED 2026-10-23, the store holds exactly two values in `verifier_model` — this string on 6,586 rows and
#: '' on the 1,049 sidecar rows (role with no factual claim, D-2942) — so a writer that types it can drift
#: silently, and one copy already named `threshold 0.10` after D-2863 moved the threshold to 0.5.
VERIFIER_IDENTITY: str = f"{S5_NLI_MODEL_LARGE} (threshold {S5_NLI_PASS_THRESHOLD})"

#: THE INPUT CONTRACT (BUG-979, generalised 2026-10-23). Every column a checker or a deriver reads AS A LIST is
#: declared here. The checks accept the NATIVE shape (JSONL) while the STORE keeps these cells as JSON TEXT, so a
#: raw store row silently answers "no evidence" to the NLI check and "0 sources" to ISOR — MEASURED twice: the
#: first on `evidence_passages` (BUG-979: a row with evidence answered "No evidence — QUARANTINE"), the second on
#: `source_ids` (2026-10-23: an ISOR of n_sources=0 was written for a row carrying one source id). The contract
#: is part of the RULE, so it is enforced HERE rather than in each caller that happens to remember.
#: `source_books` is included because `fb_source_ids` FALLS BACK to it when `source_ids` is empty.
JSON_LIST_COLUMNS: tuple[str, ...] = ("evidence_passages", "evidence_passages_shown", "source_ids", "source_books")


def hydrate_json_lists(fb: dict[str, Any]) -> dict[str, Any]:
    """Return `fb` with every declared LIST column holding a list, parsing the store's JSON TEXT.

    Idempotent: a native list is left exactly as it is (the S4 checkpoint path already holds lists).

    Args:
        fb: a record shaped like a store row or like an S4 checkpoint entry.

    Returns:
        A shallow copy whose JSON_LIST_COLUMNS hold lists.

    Raises:
        SystemExit: when a declared column holds text that is not parseable JSON (C16: fail closed, never empty).
    """
    out = dict(fb)
    for col in JSON_LIST_COLUMNS:
        value = out.get(col)
        if isinstance(value, str) and value.strip().startswith("["):
            try:
                out[col] = json.loads(value)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"FAIL-CLOSED: {col} is not parseable JSON: {value[:80]!r}") from exc
    return out


#: The methods this sequence can NAME. A method outside this set would be an unexplained verdict.
VERIFICATION_METHODS: frozenset[str] = frozenset(
    {"deberta-nli", "mech_quality", "classification_failed", "evidence_contaminated"}
)


@dataclass(frozen=True)
class VerificationOutcome:
    """Everything the sequence decides about ONE record, with no store access and no side effect.

    Attributes:
        verification_results: the ordered check list, exactly as S5 records it (mechanism first, factual second,
            enrichment appended only when it failed).
        fact_passed: the factual verdict (the value `status` is derived from).
        fact_score: the factual check's score (the NLI entailment score, 0.0 on a short-circuit).
        mech_passed: whether the mechanism gate passed.
        mech_score: the gate's score (0.0 blocked, 0.5 citation-echo escalate, 1.0 clean) — a score-axis input.
        enrich_passed: whether the enrichment check passed.
        enrich_score: the enrichment grade (0.0-1.0) — a score-axis input.
        isor: the D2284 independence rating for THIS row (never an echo, never empty).
        status: the derived verdict (PASS | QUARANTINE | NOT_APPLICABLE via derive_status).
        s5_reason: the derived reason string.
        confidence_score: the score axis' confidence (the derivation's value, never a check's raw score).
        needs_human_review: the score axis' review flag (bool; the store face is 0/1).
        epistemic_status: the D2284 label, co-derived from the same record.
        practicality: the D2622 advisory facet tier.
        verification_method: which stage answered (one of VERIFICATION_METHODS).
        verifier_model: the declared verifier identity string.
    """

    verification_results: list[dict[str, Any]]
    fact_passed: bool
    fact_score: float
    mech_passed: bool
    mech_score: float
    enrich_passed: bool
    enrich_score: float
    isor: dict[str, Any]
    status: str
    s5_reason: str
    confidence_score: float
    needs_human_review: bool
    epistemic_status: str
    practicality: str
    verification_method: str
    verifier_model: str

    def store_cells(self) -> dict[str, Any]:
        """Return the row's cells in the shape the STORE holds them (JSON text, 0/1 flags).

        Returns:
            A dict of column -> value, ready for an INSERT or an UPDATE. `pipeline_commit` is NOT included:
            provenance is the caller's duty (R14).
        """
        return {
            "verification_results": json.dumps(self.verification_results),
            "confidence_score": self.confidence_score,
            "needs_human_review": 1 if self.needs_human_review else 0,
            "epistemic_status": self.epistemic_status,
            "status": self.status,
            "s5_reason": self.s5_reason,
            "verification_method": self.verification_method,
            "isor": json.dumps(self.isor),
            "practicality": self.practicality,
            "verifier_model": self.verifier_model,
        }

    def checkpoint_cells(self) -> dict[str, Any]:
        """Return the row's cells in the shape the S5 CHECKPOINT holds them (native types).

        Returns:
            A dict of field -> value with `verification_results` a list, `isor` a dict and
            `needs_human_review` a bool (the shape every stored S5 record already has).
        """
        return {
            "verification_results": self.verification_results,
            "confidence_score": self.confidence_score,
            "needs_human_review": self.needs_human_review,
            "epistemic_status": self.epistemic_status,
            "status": self.status,
            "s5_reason": self.s5_reason,
            "verification_method": self.verification_method,
            "isor": self.isor,
            "practicality": self.practicality,
            "verifier_model": self.verifier_model,
        }


def verify_one_record(
    fb: dict[str, Any],
    *,
    severe_evidence_ids: Any = frozenset(),
    strict: bool = False,
) -> VerificationOutcome:
    """Run S5's per-record verification sequence over ONE record and return what it decided.

    Args:
        fb: the record to verify. Must be the FULL row: the checks and the derivers read body fields, so a column
            subset makes them grade empty fields (the trap BUG-979 measured on the NLI check).
        severe_evidence_ids: ids whose evidence is contaminated (BUG-181#1); such a record is quarantined on the
            evidence, never on a model's opinion.
        strict: S5's `--strict` posture — any non-PASS verdict is written as QUARANTINE.

    Returns:
        A `VerificationOutcome`. The caller owns provenance (`pipeline_commit`, schema version) and the write.

    Raises:
        Exception: any exception raised by a check propagates EXCEPT the NLI's: an NLI error is a QUARANTINE
            verdict, not an aborted run (parity with `stage5_verify.py`).
    """
    # 1. the cheapest decisive gate. Its failure IS the factual verdict.
    fb = hydrate_json_lists(fb)  # the INPUT CONTRACT above: a store row's TEXT cells become the lists the
    #                              checks and `isor_score` read. A caller cannot get this wrong.

    mech_passed, mech_score, mech_detail = stage5_verify.check_mechanism_quality(fb)
    results: list[dict[str, Any]] = [
        {"check_name": "mechanism_quality", "passed": bool(mech_passed), "score": float(mech_score), "detail": str(mech_detail)}
    ]

    # 2-3. the factual verdict, in the declared order of the short-circuits.
    fact_passed: bool
    fact_score: float
    fact_detail: str
    method = "deberta-nli"
    if str(fb.get("classification_status") or "") == "FAILED":
        fact_passed = False
        fact_score = 0.0
        fact_detail = f"S4 classification FAILED: {str(fb.get('classification_error', 'unknown'))[:120]}"
        method = "classification_failed"
    elif fb.get("fb_id") in severe_evidence_ids:
        fact_passed = False
        fact_score = 0.0
        fact_detail = "BUG-181#1: evidence_passages carry EPUB→MD conversion artifacts — QUARANTINE (no NLI)"
        method = "evidence_contaminated"
    elif not mech_passed:
        fact_passed = False
        fact_score = 0.0
        fact_detail = f"MECH FAIL: {mech_detail}"
        method = "mech_quality"
    else:
        try:
            fact_passed, fact_score, fact_detail = stage5_verify.deberta_check(fb)
        except Exception as exc:  # noqa: BLE001 — an NLI failure is a verdict (QUARANTINE), not an aborted run
            fact_passed, fact_score = False, 0.0
            fact_detail = f"Dual-encoder error — QUARANTINE: {exc}"

    results.append(
        {"check_name": "factual", "passed": bool(fact_passed), "score": float(fact_score), "detail": str(fact_detail)}
    )

    # 4. enrichment is a SCORE INPUT, appended only when it fails (D2277/D2283 — never a verdict).
    enrich_passed, enrich_score, enrich_detail = stage5_verify._check_enrichment_quality(fb)  # noqa: SLF001
    if not enrich_passed:
        results.append(
            {
                "check_name": "enrichment_quality",
                "passed": bool(enrich_passed),
                "score": float(enrich_score),
                "detail": str(enrich_detail),
            }
        )

    # 5. the verdict, from the ONE serving-gate rule.
    status, s5_reason = derive_status(results)
    if strict and status != "PASS":
        status = "QUARANTINE"

    # 6-7. ISOR before confidence (D2310); the axis itself is ONE rule with two outputs (BUG-502).
    isor = isor_score(fb)
    confidence_score, needs_human_review = derive_conf_and_review(fact_passed, mech_score, enrich_score, isor)

    # 8-9. the label co-derived from the same record, and the advisory facet tier.
    epistemic_status = derive_epistemic_status(fact_passed, isor.get("rating"))

    return VerificationOutcome(
        verification_results=results,
        fact_passed=bool(fact_passed),
        fact_score=float(fact_score),
        mech_passed=bool(mech_passed),
        mech_score=float(mech_score),
        enrich_passed=bool(enrich_passed),
        enrich_score=float(enrich_score),
        isor=isor,
        status=str(status),
        s5_reason=str(s5_reason),
        confidence_score=float(confidence_score),
        needs_human_review=bool(needs_human_review),
        epistemic_status=str(epistemic_status),
        practicality=classify_practicality(fb),
        verification_method=method,
        verifier_model=VERIFIER_IDENTITY,
    )
