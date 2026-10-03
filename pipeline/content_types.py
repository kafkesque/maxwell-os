"""content_types.py — Load the content-type ontology from config/content_types.yaml.

D2323 (2026-08-13): content_type (functional ROLE) and extraction_type (epistemic
FORM) are TWO ORTHOGONAL AXES. They were previously conflated. This module is the
single source-of-truth LOADER — pipeline code imports enums/mappings from here and
never re-declares them (C12 config-first).

One routing mapping lives here:
  - ROUTE_TO_CONTENT_TYPE (D2128): legacy S2 `route` field → content_type. Closes
    the gap where S2's `route` (FB/PT/PI/GE/TI) was silently ignored by S4.

Note on convergent vs single-source (D2323 resolution):
  - Convergent (multi-source) S2 extraction emits `content_type: principle`
    (foundation block) with `extraction_type` carrying the epistemic form. The
    golden file (stage2_fewshot_convergent.yaml) is NOT that assertion: it holds
    84 examples / 61 should_extract with NO top-level content_type field — any
    apparent all-principle skew is few-shot bias, not an axis invariant (BUG-229).
  - Single-source extraction may emit any of the 5 roles; the model chooses the
    role directly (independent of extraction_type, per D2323).
"""
from __future__ import annotations

from pathlib import Path

import re

import yaml

_CT_PATH = Path(__file__).resolve().parent.parent / "config" / "content_types.yaml"
with open(_CT_PATH, encoding="utf-8") as _f:
    _CT = yaml.safe_load(_f)

# ── AXIS 1 — content_type: functional ROLE (5 values) ─────────────────────
CONTENT_TYPES: frozenset[str] = frozenset(_CT["content_types"].keys())

# ── AXIS 2 — extraction_type: epistemic FORM (4 values) ───────────────────
EXTRACTION_TYPES: frozenset[str] = frozenset(_CT["extraction_types"].keys())

# ── D2128 — legacy S2 `route` field → content_type ────────────────────────
ROUTE_TO_CONTENT_TYPE: dict[str, str] = dict(_CT.get("route_to_content_type", {}))

# ── D2417 — content_type → extraction_type (conflation-rescue default) ─────
# BUG-145: when the model writes a content_type ROLE into extraction_type, remap
# to a weakest-honest epistemic default rather than fail-closed. S4 may re-derive.
CONTENT_TO_EXTRACTION_TYPE: dict[str, str] = dict(
    _CT.get("content_to_extraction_type", {})
)

# ── D2587 — content-type classification rules (Q1/Q2/Q3) ───────────────────
# Loaded so the auditor can ENFORCE the rules (process_template.min_steps, etc.)
# rather than leave them as decorative YAML. C12: read from YAML, never re-declare.
CONTENT_TYPE_RULES: dict = dict(_CT.get("content_type_rules", {}))
PROCESS_TEMPLATE_MIN_STEPS: int = int(
    CONTENT_TYPE_RULES.get("process_template_min_steps", 2)
)

# ── D2587 — full 7-value content_type axis (5 roles + 2 dispositions) ──────
# The S4 router only COMMITS the 5 roles (content_types); noise_drop + quarantine
# are DISPOSITIONS (drop / hold) that a classification pass may still emit. The
# D2587 adjudication and the joint content_type+depth vote use all 7.
# NOTE: `dispositions:` also carries the `classified` STATUS flag ("already has a
# role"), which is NOT a classification outcome — it is excluded from the axis.
_DISPOSITION_STATUS_KEYS: frozenset[str] = frozenset({"classified"})
CONTENT_TYPE_DISPOSITIONS: frozenset[str] = frozenset(
    k for k in _CT.get("dispositions", {}).keys() if k not in _DISPOSITION_STATUS_KEYS
)
CONTENT_TYPES_ALL: frozenset[str] = CONTENT_TYPES | CONTENT_TYPE_DISPOSITIONS

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

# D2591 dispositions (from config/content_types.yaml `dispositions:`): what to DO
# when an object has no clean role. QUARANTINE = HOLD for later identification
# (ambiguous); NOISE_DROP = DROP (descriptive/historical summary or fact). BUG-148
# (D2616 Phase 0): a record reaching S4 with NO explicit content_type is routed to
# QUARANTINE (never silently forced to `principle` via the legacy `route` field).
QUARANTINE_CONTENT_TYPE: str = "quarantine"
NOISE_DROP_CONTENT_TYPE: str = "noise_drop"

# Enum strings for prompt interpolation (sorted for deterministic output).
CONTENT_TYPE_ENUM: str = '"' + '"|"'.join(sorted(CONTENT_TYPES)) + '"'
EXTRACTION_TYPE_ENUM: str = '"' + '"|"'.join(sorted(EXTRACTION_TYPES)) + '"'

# ── D-2747 — deterministic non-principle REROUTE (BUG-611 / BUG-170) ──────────
# S4 routes non-principle records WITHOUT re-classifying them (BUG-170), so an S2
# mislabel reaches S6 unverified. D-343: content_type must NOT be LLM-classified
# (measured -2.98pp vs constant baseline). The correction is therefore DETERMINISTIC:
#   1. owner-adjudicated map (fb_id → corrected role)  — highest authority
#   2. keyword denylist (config-driven, C12)           — structural
#   3. structural checks (TI with no syntax/params → quarantine)
# The contested retention guard is ORTHOGONAL: a `contested: true` record is NEVER
# noise_drop/quarantine. `contested` is a growth_edge RECORD field (bool), NOT a new
# epistemic_status value — the epistemic_status axis is S5-DERIVED (serving_gate) and
# stays 4-valued; `contested` answers "do sources contradict?", not S5's tier question.
_REROUTE: dict = dict(_CT.get("reroute", {}))
TI_TO_PT_KEYWORDS: tuple[str, ...] = tuple(
    str(k).strip().lower() for k in _REROUTE.get("ti_to_pt_keywords", []) if str(k).strip()
)
_ADJUDICATION_PATH: Path = Path(__file__).resolve().parent.parent / "governance" / "content_type_adjudication.json"
CONTESTED_FLAG: str = "contested"
GROWTH_EDGE_CONTENT_TYPE: str = "growth_edge"


def _load_adjudication_map() -> dict[str, str]:
    """Load the owner-adjudicated fb_id → corrected content_type map (C16: loud on corrupt)."""
    if not _ADJUDICATION_PATH.exists():
        return {}
    try:
        import json
        doc = json.loads(_ADJUDICATION_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — C16: log AND raise
        raise RuntimeError(f"content_type adjudication map is corrupt ({_ADJUDICATION_PATH}): {exc}") from exc
    rows = doc.get("rows", []) if isinstance(doc, dict) else []
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        fb_id = str(row.get("fb_id") or "").strip()
        proposed = str(row.get("proposed") or "").strip()
        if fb_id and proposed in CONTENT_TYPES_ALL:
            out[fb_id] = proposed
    return out


_ADJUDICATION_MAP: dict[str, str] = _load_adjudication_map()


# ── D-2748/D-2749 — principle FORM invariant (tier-2 structural) ─────────────
# A principle is a single self-contained transferable rule (KNOW/APPLY, D275b). A
# definitional "X is/describes/refers to" framing with NO prescriptive core is a
# descriptive FACT, not a rule. This guard is FAIL-CLOSED: it only ever returns a
# RETAINED disposition (growth_edge / process_template / quarantine) — never
# noise_drop — because auto-DROP is owner-gated via the tier-1 adjudication map.
_DEFINITIONAL_START = re.compile(
    r"^(this (principle|pattern|approach|method|model|framework|concept|insight|idea|"
    r"phenomenon|law|rule|strategy|heuristic|tendency|effect|technique|process|dynamic|"
    r"trajectory|mechanism|practice)\b"
    r"|the (principle|pattern|approach|method|model|framework|concept|phenomenon|law|rule|"
    r"strategy|tendency|effect|technique|process|practice)\b"
    r"|[a-z][a-z -]{2,40} (describes|refers to|is (a|an|the) |means|involves|represents|"
    r"functions as|operates as|constitutes)\b)",
    re.IGNORECASE,
)
_PRESCRIPTIVE = re.compile(
    r"\b(should|must|ought|requires?|demands|necessitates|"
    r"to (achieve|avoid|maximi[sz]e|minimi[sz]e|improve|prevent|build|design|create|ensure|"
    r"reduce|increase|optimi[sz]e|mitigate|detect|identify|leverage|maintain|sustain|"
    r"encourage|discourage|select|prioriti[sz]e|reject|accept|adopt|isolate|reframe|"
    r"validate|frame|elicit|structure))\b",
    re.IGNORECASE,
)
_PROCEDURE_STEPS = re.compile(
    r"\b(first|second|third|fourth|finally|next|then|subsequently|thereafter)\b[^.]*"
    r"\b(then|next|finally|until|once|repeat)\b|\b(step|stage|phase)\s*[1-9]",
    re.IGNORECASE,
)
_DONE_CONDITION = re.compile(
    r"\b(until|once .{0,40} (then|stop|complete|done)|repeat until|keep .{0,20} until|"
    r"iterate .{0,20} (until|converge)|gate|exit condition|termination)\b",
    re.IGNORECASE,
)
_OPEN_TENSION = re.compile(
    r"\b(contested|contradict|contradictory|disputed|unverified|unresolved|open question|"
    r"debated|not (yet )?(established|verified|proven)|unknown whether|"
    r"correlation .{0,20} unproven)\b",
    re.IGNORECASE,
)


def _principle_form_violation(fb: dict) -> str | None:
    """Return a RETAINED disposition when a `principle` record's FORM is not a rule.

    D-275b discriminator: a principle is a single self-contained transferable claim you
    KNOW/APPLY — NOT a procedure (EXECUTE), NOT an open tension/unverified correlation,
    NOT a bare definitional fact. Fail-closed: never returns noise_drop (auto-DROP is
    owner-gated via the tier-1 map).
    """
    definition = str(fb.get("definition") or "")
    body = " ".join(
        str(fb.get(k) or "") for k in ("name", "mechanism", "boundary", "consequence", "elaboration")
    )
    hay = (definition + " " + body).lower()
    if _OPEN_TENSION.search(hay):
        return GROWTH_EDGE_CONTENT_TYPE            # retained — investigate the tension
    if _PROCEDURE_STEPS.search(hay) and _DONE_CONDITION.search(hay):
        return "process_template"                   # retained — a method, not a principle
    if _DEFINITIONAL_START.search(definition) and not _PRESCRIPTIVE.search(hay):
        return QUARANTINE_CONTENT_TYPE              # hold — bare descriptive fact, owner review
    return None


def reroute_content_type(fb: dict) -> str:
    """Deterministically correct a non-principle record's content_type (D-2747).

    D-343: content_type must NOT be LLM-classified (worse than constant baseline), so
    this is pure deterministic rules — no model call. First-match-wins across three tiers:
      1. owner-adjudicated map (fb_id → role)  — highest authority
      2. keyword denylist (TI tool_name → process_template)
      3. structural (TI with neither syntax nor parameters → quarantine)

    The contested retention guard is applied FIRST: a `contested: true` record is
    growth_edge by construction, never dropped.

    Args:
        fb: A Stage 2 record dict with content_type + body fields.

    Returns:
        The corrected content_type role (or the original when no rule fires).
    """
    current = str(fb.get("content_type") or "").strip()
    # Retention guard (D-2747): contested records are growth_edge, never dropped.
    if _is_contested(fb) and current in (QUARANTINE_CONTENT_TYPE, NOISE_DROP_CONTENT_TYPE):
        return GROWTH_EDGE_CONTENT_TYPE
    if current not in CONTENT_TYPES:
        return current  # only roles are rerouted; dispositions resolve elsewhere
    fb_id = str(fb.get("fb_id") or fb.get("principle_id") or "").strip()
    # Tier 1 — owner adjudication (highest authority).
    if fb_id and fb_id in _ADJUDICATION_MAP:
        return _ADJUDICATION_MAP[fb_id]
    # Tier 2 — principle FORM invariant (D-2748/D-2749): fail-closed, retained-only.
    if current == "principle":
        violation = _principle_form_violation(fb)
        if violation:
            return violation
    # Tier 3 — keyword denylist (TI named like a system/protocol/workflow → PT).
    if current == "tool_instruction":
        tool_name = str(fb.get("tool_name") or "").strip().lower()
        if tool_name and any(k in tool_name for k in TI_TO_PT_KEYWORDS):
            return "process_template"
        # Tier 4 — structural: a TI with neither syntax nor parameters is underspecified.
        syntax = str(fb.get("syntax") or "").strip()
        params = fb.get("parameters")
        if not syntax and not params:
            return QUARANTINE_CONTENT_TYPE
    return current


def _is_contested(fb: dict) -> bool:
    """True when the record is flagged contested/unfalsifiable (D-2747 retention guard)."""
    val = fb.get(CONTESTED_FLAG)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "contested")
    return bool(val)


# ── D-2757 — APPLICABILITY AXIS (consumer/teleology, orthogonal Axis 3) ──────
# The 234-record quarantine blob (BUG-611) was heterogeneous: definitional/
# terminological (educational), prescriptive (operational), ethics/values
# (philosophical_educational) and tip/trick (heuristic_tip) records were held as
# one undifferentiated blob. This axis answers WHO consumes the object and WHY.
# DETERMINISTIC (never LLM-classified — D-343): adjudication map first, then
# lexical markers. Provenance is stamped alongside the label.
_APPLICABILITY: dict = dict(_CT.get("applicability", {}))
APPLICABILITY_VALUES: tuple[str, ...] = tuple(str(v) for v in _APPLICABILITY.get("values", []))
DEFAULT_APPLICABILITY: str = str(_APPLICABILITY.get("default", "operational"))
_APPLICABILITY_ADJUDICATION_PATH: Path = (
    Path(__file__).resolve().parent.parent / "governance" / "applicability_adjudication.json"
)

# ethics/values teleology → philosophical_educational (subtype of educational).
# TIGHT (D-2757): strong ethics/values reflection terms ONLY — generic operational
# words (trust, collective, responsibility, freedom, autonomy, rights, equity,
# cooperation, solidarity, duty, obligation) are EXCLUDED because they appear in
# ordinary prescriptive principles ("build trust", "degrees of freedom", "equity
# in UX") and would contaminate the axis. Gated on NON-prescriptive text (a
# prescriptive ethics rule → operational; a reflective values stance → philosophical).
_VALUES = re.compile(
    r"\b(justice|fairness|moral|morality|ethical|ethics|virtue|dignity|"
    r"human condition|human nature|the commons|the good|social contract)\b",
    re.IGNORECASE,
)
# tip/trick/surface wisdom → heuristic_tip (no causal skeleton, no done-condition).
_TIP = re.compile(
    r"\b(tip for|a tip|pro tip|trick|rule of thumb|hack|quick win|best practice|"
    r"handy hint|suggestion|in practice,? (try|consider|use))\b",
    re.IGNORECASE,
)


def _load_applicability_map() -> dict[str, str]:
    """Load owner-adjudicated fb_id → applicability map (C16: loud on corrupt)."""
    if not _APPLICABILITY_ADJUDICATION_PATH.exists():
        return {}
    try:
        import json
        doc = json.loads(_APPLICABILITY_ADJUDICATION_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — C16: log AND raise
        raise RuntimeError(
            f"applicability adjudication map is corrupt ({_APPLICABILITY_ADJUDICATION_PATH}): {exc}"
        ) from exc
    rows = doc.get("rows", []) if isinstance(doc, dict) else []
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        fb_id = str(row.get("fb_id") or "").strip()
        appl = str(row.get("applicability") or "").strip()
        if fb_id and appl in APPLICABILITY_VALUES:
            out[fb_id] = appl
    return out


_APPLICABILITY_MAP: dict[str, str] = _load_applicability_map()


def derive_applicability(fb: dict, content_type: str) -> tuple[str, str]:
    """Deterministically derive the applicability (consumer/teleology) label.

    D-2757: applicability is ORTHOGONAL to content_type and is NEVER LLM-classified
    (D-343). First-match-wins across two tiers, provenance stamped:
      1. owner-adjudicated map (fb_id → applicability)  — highest authority
      2. lexical markers over the body (values → philosophical_educational;
         tip/trick → heuristic_tip; definitional-without-prescriptive → educational)
    Default is ``operational`` (the normal target of a principle/PT/TI).

    Args:
        fb: Stage 2 record dict with body fields.
        content_type: the RESOLVED content_type role (for provenance context only).

    Returns:
        (applicability, source) where source ∈ {owner_adjudicated, deterministic}.
    """
    fb_id = str(fb.get("fb_id") or fb.get("principle_id") or "").strip()
    # Tier 1 — owner adjudication (highest authority).
    if fb_id and fb_id in _APPLICABILITY_MAP:
        return _APPLICABILITY_MAP[fb_id], "owner_adjudicated"
    definition = str(fb.get("definition") or "")
    body = " ".join(
        str(fb.get(k) or "") for k in ("name", "mechanism", "boundary", "consequence", "elaboration")
    )
    hay = (definition + " " + body).lower()
    _prescriptive = bool(_PRESCRIPTIVE.search(hay))
    # Tier 2 — lexical markers (deterministic, order matters).
    if _TIP.search(hay):
        return "heuristic_tip", "deterministic"
    if _VALUES.search(hay) and not _prescriptive:
        # reflective values/ethics stance (non-prescriptive) → philosophical.
        return "philosophical_educational", "deterministic"
    if _DEFINITIONAL_START.search(definition) and not _prescriptive:
        # terminological/descriptive without a prescriptive core → educational.
        return "educational", "deterministic"
    # prescriptive (or default) → operational: the normal target of a rule.
    return DEFAULT_APPLICABILITY, "deterministic"
