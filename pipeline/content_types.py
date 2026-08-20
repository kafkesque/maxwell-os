"""content_types.py — Load the content-type ontology from config/content_types.yaml.

D2323 (2026-08-13): content_type (functional ROLE) and extraction_type (epistemic
FORM) are TWO ORTHOGONAL AXES. They were previously conflated. This module is the
single source-of-truth LOADER — pipeline code imports enums/mappings from here and
never re-declares them (C12 config-first).

Two routing mappings live here:
  - EXTRACTION_TO_CONTENT_TYPE (D2150): extraction_type → content_type default.
    Used by single-source extraction (SINGLETON path) where one passage can be a
    process template, case study, tool instruction, or speculative edge.
  - ROUTE_TO_CONTENT_TYPE (D2128): legacy S2 `route` field → content_type. Closes
    the gap where S2's `route` (FB/PT/PI/GE/TI) was silently ignored by S4.

Note on convergent vs single-source (D2323 resolution):
  - Convergent (multi-source) S2 extraction emits `content_type: principle`
    (foundation block) with `extraction_type` carrying the epistemic form. The
    golden file (stage2_fewshot_convergent.yaml) reflects this: 75/75 principle.
  - Single-source extraction may emit any of the 5 roles, using
    EXTRACTION_TO_CONTENT_TYPE as the deterministic default.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_CT_PATH = Path(__file__).resolve().parent.parent / "config" / "content_types.yaml"
with open(_CT_PATH, encoding="utf-8") as _f:
    _CT = yaml.safe_load(_f)

# ── AXIS 1 — content_type: functional ROLE (5 values) ─────────────────────
CONTENT_TYPES: frozenset[str] = frozenset(_CT["content_types"].keys())

# ── AXIS 2 — extraction_type: epistemic FORM (4 values) ───────────────────
EXTRACTION_TYPES: frozenset[str] = frozenset(_CT["extraction_types"].keys())

# ── D2150 — extraction_type → content_type (single-source routing default) ─
EXTRACTION_TO_CONTENT_TYPE: dict[str, str] = dict(
    _CT.get("extraction_to_content_type", {})
)

# ── D2128 — legacy S2 `route` field → content_type ────────────────────────
ROUTE_TO_CONTENT_TYPE: dict[str, str] = dict(_CT.get("route_to_content_type", {}))

# ── D2417 — content_type → extraction_type (conflation-rescue default) ─────
# BUG-145: when the model writes a content_type ROLE into extraction_type, remap
# to a weakest-honest epistemic default rather than fail-closed. S4 may re-derive.
CONTENT_TO_EXTRACTION_TYPE: dict[str, str] = dict(
    _CT.get("content_to_extraction_type", {})
)

# ── D2323 — vestigial content_type values, never used ─────────────────────
DROPPED_CONTENT_TYPES: frozenset[str] = frozenset(
    _CT.get("dropped_content_types", [])
)

# ── P2-1 — S2-extractable body fields per content_type (beyond core_body) ─
# Sourced from content_types.yaml `s2_body_fields`. The single-source/singleton
# prompt emits these fields when it chooses the corresponding content_type role.
# Cross-reference/metadata fields are DERIVED later (S4.5/D2345), not extracted.
S2_BODY_FIELDS: dict[str, list[str]] = {
    str(k): [str(f) for f in v] for k, v in _CT.get("s2_body_fields", {}).items()
}

# Default role emitted by convergent S2 extraction (foundation block).
DEFAULT_CONTENT_TYPE: str = "principle"

# Enum strings for prompt interpolation (sorted for deterministic output).
CONTENT_TYPE_ENUM: str = '"' + '"|"'.join(sorted(CONTENT_TYPES)) + '"'
EXTRACTION_TYPE_ENUM: str = '"' + '"|"'.join(sorted(EXTRACTION_TYPES)) + '"'
