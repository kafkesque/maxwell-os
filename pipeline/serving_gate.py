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
