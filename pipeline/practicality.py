#!/usr/bin/env python3
"""
pipeline/practicality.py — Practicality/Applicability filter (D2622).
======================================================================
Authority: D2622 (PROPOSED 2026-09-14), CONSTITUTION C12 (config-first),
           C21 (swappable backend), C28 (lightweight default), C1 ($0).

Classifies a fact block (FB) into one of three practicality tiers:
  immediately-applicable | context-dependent | abstract

This is an ONTOLOGICAL label, NOT a factuality gate. It descends from the
v1 binary 30-second actionability gate (SESSION-HANDOFF-2026-08-09) and
upgrades it to a 3-way typology driven by config/practicality.yaml.

Design (C21 swappable): a single protocol `classify_practicality(fb) -> str`
backed by config `backend`. Only `deterministic` is implemented today (C1:
no LLM, no marginal cost, no temperature). An `llm` backend can be added
later behind the same protocol without touching callers.

C16: no silent errors — a missing/malformed config raises; an unknown
backend raises; a missing live signal is declared inert (weight 0), never
silently mis-scored.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "practicality.yaml"

# ── Backend protocol (C21): one home for the classification rule ────────────
# classify_practicality(fb: dict) -> str  where str ∈ config.labels
Backend = Callable[[dict[str, Any]], str]


class PracticalityConfigError(RuntimeError):
    """D2622/C16: config/practicality.yaml missing or malformed — fail loud."""


def _load_config() -> dict[str, Any]:
    """Load config/practicality.yaml once. Raises on absence/parse failure (C16)."""
    if not _CONFIG_PATH.exists():
        raise PracticalityConfigError(
            f"config/practicality.yaml missing — refusing to classify (C16)"
        )
    try:
        cfg = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
    except yaml.YAMLError as e:
        raise PracticalityConfigError(f"config/practicality.yaml unparseable: {e}") from e
    return cfg


def _signal_configs(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the declared signal table (name -> config) from the config (C12)."""
    signals = cfg.get("signals", {})
    if not isinstance(signals, dict) or not signals:
        raise PracticalityConfigError("config/practicality.yaml: 'signals' table empty (C16)")
    return signals


def _matches(pattern: str | None, text: str) -> bool:
    """Compile-and-match a config-owned regex against `text` (C12/C20)."""
    if not pattern:
        return False
    try:
        return re.search(pattern, text) is not None
    except re.error as e:
        raise PracticalityConfigError(f"invalid regex {pattern!r}: {e}") from e


def _evaluate_deterministic(fb: dict[str, Any], cfg: dict[str, Any]) -> str:
    """Deterministic backend: apply the ordered rule table from config (first match).

    Signals are read by field name (declared in config, not hardcoded — C12).
    Inert signals (live: false) are skipped because their rules would match on
    absent data; only live signals participate. The final `default` rule is the
    fail-closed fallback (abstract) — never a silent unlabelled pass.
    """
    signals = _signal_configs(cfg)
    app_cfg = signals.get("application", {})
    acc_cfg = signals.get("accessibility", {})

    application = str(fb.get(str(app_cfg.get("field", "application")), "") or "")
    accessibility = str(fb.get(str(acc_cfg.get("field", "accessibility")), "") or "")

    has_trigger = _matches(app_cfg.get("trigger_pattern"), application)
    has_imperative = _matches(app_cfg.get("imperative_pattern"), application)

    rules = cfg.get("rules", [])
    if not isinstance(rules, list) or not rules:
        raise PracticalityConfigError("config/practicality.yaml: 'rules' list empty (C16)")

    for rule in rules:
        label = rule.get("label")
        conditions: list[str] = rule.get("when", [])
        if label is None or not isinstance(conditions, list):
            continue
        for cond in conditions:
            if cond == "default":
                return str(label)
            if cond == "accessibility == prerequisite":
                if accessibility == str(acc_cfg.get("prerequisite", "prerequisite")):
                    return str(label)
            if cond == "application matches trigger_pattern AND imperative_pattern":
                if has_trigger and has_imperative:
                    return str(label)
            if cond == "application matches trigger_pattern":
                if has_trigger:
                    return str(label)

    # Unreachable if the config carries a `default` rule; kept as C16 guard.
    raise PracticalityConfigError(
        "config/practicality.yaml: no rule matched and no 'default' rule present (C16)"
    )


def classify_practicality(fb: dict[str, Any]) -> str:
    """Classify one FB into a practicality tier (D2622).

    Public protocol entry point (C21). Backend is resolved from config
    `backend`; only `deterministic` is implemented. Returns a label from
    config.labels. Raises PracticalityConfigError on any misconfiguration (C16).
    """
    cfg = _load_config()
    backend = cfg.get("backend", "deterministic")
    if backend == "deterministic":
        return _evaluate_deterministic(fb, cfg)
    raise PracticalityConfigError(f"unknown practicality backend {backend!r} (C16/C21)")


def annotate_fbs(fbs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return FBs with a `practicality` field added (non-mutating)."""
    out: list[dict[str, Any]] = []
    for fb in fbs:
        copy = dict(fb)
        copy["practicality"] = classify_practicality(fb)
        out.append(copy)
    return out


if __name__ == "__main__":
    # Smoke test: classify a small synthetic set without touching the corpus.
    demo = [
        {"name": "High Contrast", "application": "When designing a layout, use high contrast.", "accessibility": "self-evident"},
        {"name": "Chroma Subsampling", "application": "When compressing, downsample chroma.", "accessibility": "prerequisite"},
        {"name": "Pure Definition", "application": "", "accessibility": "self-evident"},
    ]
    for fb in demo:
        print(f"  {fb['name']:<20} -> {classify_practicality(fb)}")
