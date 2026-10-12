#!/usr/bin/env python3
"""pipeline/growth_edge_ontology.py — ONE home (C21) for the growth_edge category facet.

D-2924 (owner-approved 2026-10-11): the growth_edge `category`/`tags` fields imply a
SKILL/CAPABILITY ontology that does NOT exist. The discipline axis is a KNOWLEDGE-axis
and does NOT cover GE's open-tension / capability-growth space (D-2923 invariant: GE is
keyed by body+status, NEVER discipline/domain).

This module is the single source of truth for the CLOSED, provenance-stamped, calibrated
GE category vocabulary. Consumers:
  - stage4_merge.py (route GE records)  [future]
  - Stage R typed extraction (emit GE)  [future — gate: calibration.requires_gold_before_volume]

Config (C12 — no hardcoded ontology):
  config/growth_edge_ontology.yaml

Fail-closed: an off-vocabulary category (that is not the abstention token) raises,
mirroring the discipline_macro loader (BUG-622 class). The calibration gate is
`advisory` until a gold set is minted; once `enforcing`, volume GE emission without
a stamped calibration_decision refuses (D-2924).
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_GE_ONTOLOGY = _REPO / "config" / "growth_edge_ontology.yaml"
EMERGING = "emerging"


@lru_cache(maxsize=1)
def load_ontology() -> dict[str, Any]:
    """Return the parsed growth_edge_ontology.yaml (cached once)."""
    import yaml

    doc = yaml.safe_load(_GE_ONTOLOGY.read_text(encoding="utf-8")) or {}
    if not doc.get("category") or not doc["category"].get("values"):
        raise SystemExit(f"FAIL: {_GE_ONTOLOGY.name} has no closed category vocabulary (D-2924)")
    return doc


def category_values() -> frozenset[str]:
    """Return the closed category vocabulary (values + abstention token)."""
    cat = load_ontology()["category"]
    return frozenset(cat["values"]) | {str(cat.get("abstention", EMERGING))}


def tag_values() -> frozenset[str]:
    """Return the closed bootstrap tag vocabulary (bootstrap + abstention token)."""
    tags = load_ontology()["tags"]
    return frozenset(tags.get("bootstrap", [])) | {str(tags.get("abstention", EMERGING))}


def validate_category(value: str) -> str:
    """Fail-closed: a category off the closed vocabulary (and not the abstention token)
    raises — never free-gen (D-2924). Returns the normalized value otherwise."""
    v = (value or "").strip()
    if not v:
        raise SystemExit("FAIL: empty growth_edge.category (D-2924)")
    cat = load_ontology()["category"]
    if v in cat["values"]:
        return v
    if v == str(cat.get("abstention", EMERGING)):
        return v
    raise SystemExit(
        f"FAIL: growth_edge.category {v!r} is OFF the closed D-2924 vocabulary "
        f"{sorted(cat['values'])} (or {cat.get('abstention', EMERGING)!r}); never free-gen (C16)"
    )


def validate_tags(values: list[str]) -> list[str]:
    """Fail-closed: any tag off the closed bootstrap (and not the abstention token) raises."""
    allowed = tag_values()
    out: list[str] = []
    for t in values or []:
        t = str(t).strip()
        if t in allowed:
            out.append(t)
        else:
            raise SystemExit(
                f"FAIL: growth_edge tag {t!r} is OFF the closed D-2924 bootstrap "
                f"{sorted(tag_values())}; extend via the calibrated raw->canonical path (D2066), never free-gen"
            )
    return out


def calibration_enforcing() -> bool:
    """True once the category classifier must refuse volume GE emission without a stamped
    calibration decision (D-2924)."""
    cal = load_ontology().get("calibration", {})
    return bool(cal.get("gate_mode") == "enforcing" and cal.get("requires_gold_before_volume"))


def calibration_decision() -> str | None:
    """Return the minted calibration decision id, or None (not yet calibrated)."""
    return load_ontology().get("calibration", {}).get("calibration_decision")
