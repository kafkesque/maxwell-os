"""Serving gate — `status` is a function of the verification record (D274a / G17).

Exactly one writer may set `status` (D274h): it derives `status` from the
`factual` check in `verification_results` plus a typed `s5_reason`. A
label-derived status write is a hard error, and the CI invariant asserts
`status=PASS ⟹ factual.passed and s5_reason not in the negative set`.

This module holds the pure derivation + invariant logic — imported by the apply
script, the stage 5/6 wiring, and the tests — so the rule lives in exactly one
place. Config: `config/serving_gate.yaml` (C12; nothing here is hardcoded).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "serving_gate.yaml"

_cache: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    """Load (and cache) the serving-gate config block."""
    global _cache
    if _cache is None:
        with CONFIG_PATH.open(encoding="utf-8") as f:
            _cache = yaml.safe_load(f)["serving_gate"]
    return _cache


def factual_check(verification_results: Any) -> dict[str, Any] | None:
    """Return the `factual` check dict from `verification_results`, else None.

    Accepts the JSON-array string stored in the DB column or an already-parsed
    list. Returns None when the record is empty or has no factual check, so the
    caller can fail closed.
    """
    if isinstance(verification_results, str):
        try:
            verification_results = json.loads(verification_results)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(verification_results, list):
        return None
    for check in verification_results:
        if isinstance(check, dict) and check.get("check_name") == "factual":
            return check
    return None


def derive_s5_reason(detail: str, cfg: dict[str, Any]) -> str:
    """Map a persisted factual `detail` string to the typed reason vocabulary."""
    for rule in cfg["detail_rules"]:
        if detail.startswith(rule["prefix"]):
            return rule["reason"]
    return cfg["fallback_reason"]


def negative_reasons(cfg: dict[str, Any] | None = None) -> set[str]:
    """Reasons that a PASS row must never carry (D274a invariant)."""
    cfg = cfg or load_config()
    return {
        name for name, spec in cfg["reason_vocabulary"].items() if spec.get("negative")
    }


def derive_status(
    verification_results: Any,
    cfg: dict[str, Any] | None = None,
    duplicate_of: str | None = None,
) -> tuple[str, str]:
    """Derive `(status, s5_reason)` from the verification record (D274a).

    `status = PASS` iff the factual check passed; otherwise QUARANTINE.
    A passed row always maps to `entail` (a passed check is ENTAIL by definition,
    even if its detail string were unrecognised). A missing/malformed record
    fails closed to `(QUARANTINE, unknown)`.

    Hard quarantine (D2627 / D-271d): a duplicate (`duplicate_of` set) is never
    served, even if verification passed — returned as `(QUARANTINE, "duplicate")`.
    """
    cfg = cfg or load_config()
    if duplicate_of:
        return cfg["quarantine_status"], cfg["duplicate_reason"]
    factual = factual_check(verification_results)
    if factual is None:
        return cfg["quarantine_status"], cfg["fallback_reason"]
    passed = bool(factual.get("passed"))
    detail = str(factual.get("detail", ""))
    reason = derive_s5_reason(detail, cfg)
    if passed and reason == cfg["fallback_reason"]:
        reason = "entail"
    status = cfg["pass_status"] if passed else cfg["quarantine_status"]
    return status, reason


def assert_invariant(
    status: str,
    verification_results: Any,
    s5_reason: str,
    cfg: dict[str, Any] | None = None,
) -> None:
    """CI invariant (D274a): status=PASS ⟹ factual.passed and reason not negative.

    Raises AssertionError on violation. QUARANTINE rows are unconstrained (they
    may be verified-but-hidden — the exact situation 0a fixes — or genuinely bad).
    """
    cfg = cfg or load_config()
    if status != cfg["pass_status"]:
        return
    factual = factual_check(verification_results)
    if factual is None or not bool(factual.get("passed")):
        raise AssertionError("status=PASS but factual.passed is not True")
    if s5_reason in negative_reasons(cfg):
        raise AssertionError(f"status=PASS but s5_reason={s5_reason!r} is a negative reason")


_label_cache: dict[str, Any] | None = None


def load_label_config() -> dict[str, Any]:
    """Load (and cache) the epistemic_label block, failing closed on a malformed ontology.

    BUG-499: the D2284 label rule existed as THREE inline copies (stage 5, the S5 checkpoint sync,
    the BUG-198 re-inject) with no config and no single home, so the question 'which column is
    canonical?' could not be answered from the repo at all. It is answered here: one function, its
    rating classes and rule order declared in config/serving_gate.yaml (C12/C20), one home (C21).
    """
    global _label_cache
    if _label_cache is None:
        with CONFIG_PATH.open(encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        block = (doc or {}).get("epistemic_label")
        if not isinstance(block, dict):
            raise ValueError("config/serving_gate.yaml has no 'epistemic_label' block")
        vocab = set(block.get("vocabulary") or [])
        if not vocab:
            raise ValueError("epistemic_label.vocabulary is empty - the label has no declared values")
        named = [str(r.get("label")) for r in block.get("rules") or []]
        named.append(str(block.get("fallback")))
        unknown = [n for n in named if n not in vocab]
        if unknown:
            raise ValueError(f"epistemic_label names label(s) outside its vocabulary: {unknown}")
        _label_cache = block
    return _label_cache


def derive_epistemic_status(
    factual_passed: bool,
    rating: str | None,
    cfg: dict[str, Any] | None = None,
) -> str:
    """Derive the D2284 label from the SAME verification record that derives status (BUG-499).

    CO-DERIVATION: status is derived from the factual check alone; this label is derived from the
    factual check PLUS the ISOR rating. The label therefore REFINES the status partition - each label
    implies exactly one status by construction - so the measured 1:1 coupling is a theorem about a
    shared record and not a hidden gate. Both remain functions of the record, and a label-derived
    STATUS write remains a hard error (D274a / D274h).

    Rules are read from epistemic_label.rules in declared order (first match wins), so no rating
    literal and no magic index sits in code. Fails closed to the declared fallback.
    """
    cfg = cfg or load_label_config()
    for rule in cfg["rules"]:
        if bool(rule.get("requires_factual_pass")) != bool(factual_passed):
            continue
        allowed = rule.get("ratings")
        if allowed is not None and rating not in allowed:
            continue
        return str(rule["label"])
    return str(cfg["fallback"])


# ── THE STORE COMPARATOR (BUG-502) ──────────────────────────────────────────────────────────────
# D274a declares the invariant; the WRITER (pipeline/stage6_commit.insert_fb) and the RAIL
# (scripts/check_serving_gate.py) both have to evaluate it. Two implementations of that evaluation
# would be two truths (the BUG-499/BUG-502 class: three copies that happened to agree), so the
# comparison lives HERE and both sites import it: the rail imports it, the writer imports it.
MATCH = "MATCH"
STATUS_MISMATCH = "STATUS_MISMATCH"
REASON_MISMATCH = "REASON_MISMATCH"
UNDECIDABLE = "UNDECIDABLE"

# The only implemented pre-write policy. Declared in config/serving_gate.yaml#serving_gate so the
# guard's behaviour is auditable; an unknown value is fatal, so the key cannot become an off switch.
PRE_WRITE_POLICIES = ("reject",)


def derive_conf_and_review(
    fact_passed: bool,
    mech_score: float,
    enrich_score: float,
    isor: dict[str, Any],
) -> tuple[float, bool]:
    """The ONE derivation of the S5 score axis (BUG-502): confidence + human-review flag.

    The score axis is a rule about the verification record, so it belongs with the other
    serving-gate derivations (derive_status, derive_epistemic_status) instead of being re-typed at
    every call site: two implementations of one rule are two truths (BUG-499 / BUG-502). The weights
    are DECLARED once, in config/pipeline_config.yaml#stage5.confidence, and read through
    pipeline.pipeline_paths - never re-declared here (a second declaration of one weight would
    recreate the defect this function removes).

    Contract (behaviour-preserving by construction, MEASURED 2026-09-25):
      * confidence = round(W_MECH*mech + W_ENRICH*enrich + W_ISOR*isor.score, 4)
      * a failed NLI gate CAPS the confidence at quarantine_cap (fail-closed, D2093);
      * the human-review flag is raised only for a QUARANTINED row whose ISOR rating is the
        declared human_review_isor_rating.
    Reproduces the stored corpus on 7,995/7,995 rows for BOTH outputs
    (scripts/check_s5_score_axis.py); the weights were silently code-defaulted until BUG-504, so
    that measurement also pins the pre-existing behaviour.
    """
    from pipeline.pipeline_paths import (  # BUG-504: declared values, never silent defaults
        S5_CONF_ENRICH_WEIGHT,
        S5_CONF_ISOR_WEIGHT,
        S5_CONF_MECH_WEIGHT,
        S5_HUMAN_REVIEW_ISOR,
        S5_QUARANTINE_CONF_CAP,
    )

    confidence = round(
        S5_CONF_MECH_WEIGHT * float(mech_score)
        + S5_CONF_ENRICH_WEIGHT * float(enrich_score)
        + S5_CONF_ISOR_WEIGHT * float(isor.get("score", 0.0)),
        4,
    )
    if not fact_passed:
        confidence = min(confidence, S5_QUARANTINE_CONF_CAP)
    needs_review = bool((not fact_passed) and isor.get("rating") == S5_HUMAN_REVIEW_ISOR)
    return confidence, needs_review


def store_verdict(
    status: object,
    reason: object,
    verification_results: object,
    duplicate_of: object = None,
    cfg: dict[str, Any] | None = None,
    neg: set[str] | None = None,
) -> tuple[str, str]:
    """Compare ONE row against the one D274a rule. Returns (verdict, detail); never guesses.

    Fail-closed (C16): a row with no factual check AND no dedup marker is UNDECIDABLE, not a pass --
    an un-evaluable row must not be able to read as verified. An absent status can never match,
    because derive_status always answers with a declared status.
    """
    cfg = cfg or load_config()
    neg = negative_reasons(cfg) if neg is None else neg
    if factual_check(verification_results) is None and not duplicate_of:
        return UNDECIDABLE, "no factual check in verification_results and no dedup marker"
    exp_status, exp_reason = derive_status(verification_results, cfg, duplicate_of=duplicate_of)
    if str(status or "") != exp_status:
        return STATUS_MISMATCH, f"stored {str(status)!r} but the verification record derives {exp_status!r}"
    if exp_status == cfg["pass_status"]:
        if str(reason or "") in neg:
            return REASON_MISMATCH, f"PASS carries the negative reason {str(reason)!r}"
        if str(reason or "") != exp_reason:
            return REASON_MISMATCH, f"stored reason {str(reason)!r} but the record derives {exp_reason!r}"
    return MATCH, ""


def pre_write_verdict(fb: dict[str, Any], cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    """The WRITER HALF of D274a: may this row be persisted? Returns (ok, complaint).

    Until this existed, D274a's "a label-derived status write is a hard error" was enforced only
    AFTER the fact, by a rail over stored rows -- so a violating writer could still mutate the store
    and the rail would merely report it later. The commit path now evaluates the SAME comparator
    (store_verdict) BEFORE the INSERT, so the governed store can never hold a status its own
    verification record does not derive.

    Absent status is NOT repaired here: deriving a value on the commit path would make this stage a
    second writer of status, which is exactly the defect D274h names. The row is refused instead.
    """
    cfg = cfg or load_config()
    policy = str(cfg.get("pre_write_enforcement", ""))
    if policy not in PRE_WRITE_POLICIES:
        raise ValueError(
            f"serving_gate.pre_write_enforcement={policy!r} is not one of {PRE_WRITE_POLICIES} - "
            "an unknown policy must not silently disable the pre-write guard (C16/D274a)"
        )
    verdict, detail = store_verdict(
        fb.get("status"), fb.get("s5_reason"), fb.get("verification_results"),
        fb.get("duplicate_of"), cfg,
    )
    if verdict == MATCH:
        return True, ""
    return False, f"{verdict}: {detail}"
