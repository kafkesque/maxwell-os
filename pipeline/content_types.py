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

# D-2644 / BUG-731 — EVERY read of `_CT` below is LOUD (subscript, no literal default). This module's
# ontology is not optional: a renamed or deleted key must fail at IMPORT (C16) rather than resolve
# silently to an empty mapping and quietly disable a rule — the BUG-730 defect class, where one
# emptied key killed the whole tool_instruction→process_template tier with every rail green. Those
# defaults were also why this file was invisible to the D-2644 census; `_CT` is now a declared census
# receiver (config/derivations.yaml#config_reads.receivers).

# ── AXIS 1 — content_type: functional ROLE (5 values) ─────────────────────
CONTENT_TYPES: frozenset[str] = frozenset(_CT["content_types"].keys())

# ── AXIS 2 — extraction_type: epistemic FORM (4 values) ───────────────────
EXTRACTION_TYPES: frozenset[str] = frozenset(_CT["extraction_types"].keys())

# ── D2128 — legacy S2 `route` field → content_type ────────────────────────
ROUTE_TO_CONTENT_TYPE: dict[str, str] = dict(_CT["route_to_content_type"])

# ── D2417 — content_type → extraction_type (conflation-rescue default) ─────
# BUG-145: when the model writes a content_type ROLE into extraction_type, remap
# to a weakest-honest epistemic default rather than fail-closed. S4 may re-derive.
CONTENT_TO_EXTRACTION_TYPE: dict[str, str] = dict(
    _CT["content_to_extraction_type"]
)

# ── D2587 — content-type classification rules (Q1/Q2/Q3) ───────────────────
# Loaded so the auditor can ENFORCE the rules (process_template.min_steps, etc.)
# rather than leave them as decorative YAML. C12: read from YAML, never re-declare.
CONTENT_TYPE_RULES: dict = dict(_CT["content_type_rules"])
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
    k for k in _CT["dispositions"].keys() if k not in _DISPOSITION_STATUS_KEYS
)
CONTENT_TYPES_ALL: frozenset[str] = CONTENT_TYPES | CONTENT_TYPE_DISPOSITIONS

# ── D-2965 (BUG-712 / BUG-741 / BUG-726) — LEAF-LABEL ADMISSION ───────────
# The ORDINARY producer write path (stage6_commit.insert_fb) may admit ONLY a declared ROLE into the
# `content_type` column. Three shapes are refused, and each is a DIFFERENT defect that could reach
# the store silently before this gate:
#   (a) ABSENT/BLANK -> the D-2938 "computed then discarded" defect, and invisible to the store
#       ruler ('' is not HOLLOW, BUG-726). An absent label AT S6 means the producer path was
#       bypassed: S4 already routes a missing label to `quarantine` (_resolve_content_type, D2616).
#   (b) DISPOSITION -> quarantine | noise_drop are AXIS-1 outcomes, not ROLES (BUG-741).
#       validate_fb_content_type deliberately keeps the FULL 7-value vocabulary for the
#       S2/pre-classification layer, so the narrowing belongs HERE, at the leaf (asserted by a control).
#   (c) UNDECLARED -> already fail-closed at S6 (D2616); kept so that this function IS the one
#       admission rule rather than one of two (D-2964 = the same rule for an owner warrant).
def _validate_admission(raw: object) -> dict:
    """Fail-closed load of `commit_gate` (D-2965): every key is REQUIRED and must be a bool.

    A control that a missing key can silently disable is not a control; and a
    `.get(key, default)` here would also add a shadowed-declared census key (BUG-731).

    Args:
        raw: The parsed `commit_gate` value, or None when the block is absent.

    Returns:
        The validated declaration.

    Raises:
        SystemExit: When the block is missing, not a mapping, incomplete, or mistyped.
    """
    if not isinstance(raw, dict):
        raise SystemExit(
            "FAIL-CLOSED: config/content_types.yaml#commit_gate must be a mapping "
            f"(got {type(raw).__name__}) — D-2965"
        )
    out: dict = {}
    for key in ("require_role", "refuse_dispositions"):
        if key not in raw:
            raise SystemExit(
                f"FAIL-CLOSED: config/content_types.yaml#commit_gate is missing '{key}' — a control "
                "whose declaration can go missing is not a control (D-2965)"
            )
        if not isinstance(raw[key], bool):
            raise SystemExit(
                f"FAIL-CLOSED: commit_gate.{key} must be a bool, got {raw[key]!r} (D-2965)"
            )
        out[key] = raw[key]
    return out


# LOUD read: no literal default, so an absent block is an IMPORT defect (BUG-731 census stays exact).
LEAF_ADMISSION: dict = _validate_admission(_CT.get("commit_gate"))


def leaf_label_fault(value: str | None) -> str | None:
    """Return a NAMED fault when `value` may not be a leaf's `content_type`, else None.

    The ONE admission rule for the content_type column (D-2965, C21). Named faults keep a
    refusal auditable instead of merely loud: 'absent' | 'disposition:<value>' | 'undeclared:<value>'.

    Args:
        value: The candidate content_type about to be written (may be None).

    Returns:
        A named fault string, or None when the value is an admitted ROLE.
    """
    ct: str = (value or "").strip()
    if ct == "":
        return "absent" if LEAF_ADMISSION["require_role"] else None
    if ct in CONTENT_TYPES:
        return None
    if ct in CONTENT_TYPE_DISPOSITIONS:
        return f"disposition:{ct}" if LEAF_ADMISSION["refuse_dispositions"] else None
    return f"undeclared:{ct}"

# ── ROLE-SPECIFIC BODY (D2590 / D-2943) ───────────────────────────────────
# `s2_body_fields` declares, per role, the fields S2 emits BEYOND the shared core body. `core_body`
# is the set whose home is a first-class `fbs` column, so a role's `type_body` is s2_body_fields
# MINUS core_body: the column IS the home of a core field, and a JSON copy of it would be a SECOND
# source of truth (drift + bloat, C12/C19). Measured against the rechunk-v4 sidecars (2026-10-12):
#   process_template {trigger, prerequisite, steps, done_condition}          (failure_mode is core)
#   process_instance {instance_text, actors, outcome_metric, outcome_qualitative, domain_context}
#   tool_instruction {tool_name, platform, description, syntax, parameters, output, example, caveats}
#   growth_edge      {body, category, actionable, status, priority}
# NOTE growth_edge.status is the epistemic state of the TENSION (open|speculative|conceptual) and is
# NOT the governed verification `status` column (S5-owned, D-2933): it survives namespaced inside
# type_body, and the S6 commit path never writes an S5-owned column from a sidecar row.
_S2_BODY_FIELDS: dict[str, tuple[str, ...]] = {
    str(_k): tuple(str(_f) for _f in (_v or [])) for _k, _v in dict(_CT["s2_body_fields"]).items()
}
CORE_BODY: frozenset[str] = frozenset(str(_f) for _f in (_CT["core_body"] or []))


def type_body_fields(content_type: str | None) -> tuple[str, ...]:
    """The role-specific body fields for `content_type` (D-2943); () when the role has none.

    Spec: a role's `type_body` holds exactly these fields, and only those PRESENT on the record. An
    undeclared role returns () — the caller decides whether that is acceptable, and S6 refuses to
    invent a body for a role the ontology does not declare (C12/C16).
    """
    if not content_type:
        return ()
    return tuple(_f for _f in _S2_BODY_FIELDS.get(str(content_type), ()) if _f not in CORE_BODY)

# ── D2323 — vestigial content_type values, never used ─────────────────────
DROPPED_CONTENT_TYPES: frozenset[str] = frozenset(
    _CT["dropped_content_types"]
)

# ── P2-1 — S2-extractable body fields per content_type (beyond core_body) ─
# Sourced from content_types.yaml `s2_body_fields`. The single-source/singleton
# prompt emits these fields when it chooses the corresponding content_type role.
# Cross-reference/metadata fields are DERIVED later (S4.5/D2345), not extracted.
S2_BODY_FIELDS: dict[str, list[str]] = {
    str(k): [str(f) for f in v] for k, v in _CT["s2_body_fields"].items()
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
_REROUTE: dict = dict(_CT["reroute"])
# D-2955 (BUG-729): this vocabulary is PROCEDURE-DENOTING only ('system'/'framework' named software
# ARTIFACTS and were removed), and even then it is a PRIOR — tier 3 below additionally requires BODY
# evidence unless the owner turns that gate off.
TI_TO_PT_KEYWORDS: tuple[str, ...] = tuple(
    str(k).strip().lower() for k in _REROUTE["ti_to_pt_keywords"] if str(k).strip()
)
TI_TO_PT_REQUIRE_BODY_EVIDENCE: bool = bool(_REROUTE["ti_to_pt_require_body_evidence"])
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
# D-2949 (BUG-712 spot-check): the OLD _DONE_CONDITION matched a BARE "until"/"gate"/
# "termination"/"once X then" and fired on ordinary prose ("first as analysis then as
# communication until clarity emerges" → misrouted "Dual Nature of Information
# Visualization" to process_template). The discriminator is a GENUINE loop/termination
# condition, not a step-sequence width — so _PROCEDURE_STEPS stays loose (ordinal
# sequence OR numbered steps) while _DONE_CONDITION now requires a real loop signal.
_PROCEDURE_STEPS = re.compile(
    r"\b(first|second|third|fourth|finally|next|then|subsequently|thereafter)\b[^.]*"
    r"\b(then|next|finally|until|once|repeat)\b|\b(step|stage|phase)\s*[1-9]",
    re.IGNORECASE,
)
_DONE_CONDITION = re.compile(
    r"\b(repeat until|iterate (until|while|over)|loop (until|while)|"
    r"while .{0,60} (repeat|loop|continue)|until .{0,60} (stop|complete|done|converge|satisfied)|"
    r"exit condition|termination condition)\b",
    re.IGNORECASE,
)
_OPEN_TENSION = re.compile(
    r"\b(contested|contradict|contradictory|disputed|unverified|unresolved|open question|"
    r"debated|not (yet )?(established|verified|proven)|unknown whether|"
    r"correlation .{0,20} unproven)\b",
    re.IGNORECASE,
)

# ── D-2953 (BUG-712 CALIBRATION): the tier-2 tension test, STRICT form ─────────────────────
# `_OPEN_TENSION` above fires on BARE words, so an ordinary first-order predicate about the
# record's SUBJECT is read as an epistemic statement about the CLAIM: "generating untraceable or
# contradictory information", "sites of contested identity", "visual cues contradict the
# audience's expectations". MEASURED 2026-10-12 over 7,640 rows
# (scripts/calibrate_content_type_router.py): of 100 `principle -> growth_edge` moves, 88 (88%)
# are subject-matter FALSE POSITIVES and only 12 survive even a permissive claim-status test. The
# strict form requires the token to be PREDICATED of an epistemic subject — the SAME discipline
# D-2949 applied to `_DONE_CONDITION` (bare "until"/"gate"), applied here to its sibling.
_EPISTEMIC_SUBJECT = (
    r"(claim|claims|evidence|finding|findings|result|results|theory|hypothesis|assumption|"
    r"correlation|causal link|conclusion|conclusions|knowledge|literature|research|consensus)"
)
# STATUS ASSERTION, not adjacency. Adjacency ALONE is not evidence of epistemic status: the first
# draft of this regex accepted "the training data contains contradictory context cues" via a
# generic subject noun, which measured 68% false positives — barely better than the loose form.
# The strict form therefore requires AFFIRMATIVE STRUCTURE:
#   (a) SUBJECT ... copula ... STATUS   "the evidence is/remains contested"
#   (b) STATUS → SUBJECT                "contested claim", "disputed finding"
#   (c) unambiguous constructions       "open question", "unknown whether", "not established"
# A relational use ("X contradicts Y") or a subject-matter modifier ("contradictory information")
# matches none of the three, which is the entire point of the narrowing.
_OPEN_TENSION_STRICT = re.compile(
    r"\b" + _EPISTEMIC_SUBJECT + r"\b[^.]{0,40}\b(is|are|was|were|remains?|seems?|appears?)\b"
    r"[^.]{0,20}\b(contested|disputed|unresolved|unverified|debated)\b"
    r"|\b(contested|disputed|unresolved|unverified|debated)\s+" + _EPISTEMIC_SUBJECT + r"\b"
    r"|\b(open question|unknown whether|not (yet )?(established|verified|proven)|"
    r"correlation .{0,20} unproven)\b",
    re.IGNORECASE,
)
# C12: the mode is CONFIG-owned (config/content_types.yaml -> reroute.open_tension_strict) and the
# default preserves today's behaviour exactly. Flipping it is an OWNER call — content_type is
# S4-owned ontology (D-2933) — and the strict form's own move count is re-measured BEFORE any
# re-stamp. The destructive direction is the loose one, so the flag's safe value is reachable
# without an owner and its risky value is not.
#
# Read LOUDLY, with NO code default (D-2644: "declare the key and read it loudly, or stop reading
# it"). The key IS declared in config/content_types.yaml, so a missing key is a CONFIG DEFECT and
# must fail at import (C16 fail-closed) rather than be papered over by a fallback default.
# NOTE (BUG-731): this module reads through `_CT`, which is NOT one of the receivers the D-2644
# census watches (`[_CFG, cfg, config, conf, settings]`), so reads here are invisible to that rail —
# which is exactly why the loud read is a convention this module must keep by hand.
OPEN_TENSION_STRICT: bool = bool(_CT["reroute"]["open_tension_strict"])


def _tension_haystack(fb: dict) -> str:
    """The text every tier-2 test reads (C21: ONE home for this shape).

    Args:
        fb: A Stage 2 record dict.

    Returns:
        Lower-cased "definition + name/mechanism/boundary/consequence/elaboration".
    """
    return (
        str(fb.get("definition") or "")
        + " "
        + " ".join(str(fb.get(k) or "") for k in ("name", "mechanism", "boundary", "consequence", "elaboration"))
    ).lower()


def principle_tension_hit(fb: dict, strict: bool | None = None) -> bool:
    """Whether the tier-2 open-tension test would fire on `fb` (calibration/tests only).

    Args:
        fb: A Stage 2 record dict.
        strict: force the strict or loose form; None uses the configured mode.

    Returns:
        True when the tension tier fires.
    """
    use_strict: bool = OPEN_TENSION_STRICT if strict is None else strict
    return bool((_OPEN_TENSION_STRICT if use_strict else _OPEN_TENSION).search(_tension_haystack(fb)))


_TI_BODY_KEYS: tuple[str, ...] = (
    "tool_name", "platform", "description", "syntax", "parameters", "output", "example", "caveats"
)


def _ti_haystack(fb: dict) -> str:
    """The text the tier-3 body-evidence test reads (C21: ONE home for this shape).

    A tool_instruction's OWN body is the fields the ontology declares for that role
    (`s2_body_fields.tool_instruction`, D-2943); the shared core body is appended because a TI may
    carry it too (D2475 makes it optional for the non-principle roles, never forbidden).

    Args:
        fb: A Stage 2 record dict.

    Returns:
        Lower-cased shared body + the role's own TI fields.
    """
    own = " ".join(str(fb.get(k) or "") for k in _TI_BODY_KEYS)
    return (_tension_haystack(fb) + " " + own).lower()


def has_procedure_evidence(fb: dict) -> bool:
    """Whether a record's BODY evidences a procedure: ordered steps AND a done-condition/gate.

    D275b defines a process_template as "trigger + ordered steps + a done-condition/gate", and D-2747
    tier 2 already decides `principle -> process_template` on exactly this pair. Tier 3 REUSES it
    rather than inventing a second procedure test (C21: one rule, one home).

    Public because the BUG-729 calibration measures it directly — the rule and the instrument that
    judges it must read the SAME haystack and the SAME two regexes.

    Args:
        fb: A Stage 2 record dict.

    Returns:
        True when the body carries both an ordered sequence and a termination/loop condition.
    """
    hay = _ti_haystack(fb)
    return bool(_PROCEDURE_STEPS.search(hay) and _DONE_CONDITION.search(hay))


def _principle_form_violation(fb: dict) -> str | None:
    """Return a RETAINED disposition when a `principle` record's FORM is not a rule.

    D-275b discriminator: a principle is a single self-contained transferable claim you
    KNOW/APPLY — NOT a procedure (EXECUTE), NOT an open tension/unverified correlation,
    NOT a bare definitional fact. Fail-closed: never returns noise_drop (auto-DROP is
    owner-gated via the tier-1 map).
    """
    definition = str(fb.get("definition") or "")
    hay = _tension_haystack(fb)
    # Read the mode at CALL time (not import time) so the flag is monkeypatchable and a config
    # change cannot be silently frozen into a long-lived process.
    if (_OPEN_TENSION_STRICT if OPEN_TENSION_STRICT else _OPEN_TENSION).search(hay):
        return GROWTH_EDGE_CONTENT_TYPE            # retained — investigate the tension
    if _PROCEDURE_STEPS.search(hay) and _DONE_CONDITION.search(hay):
        return "process_template"                   # retained — a method, not a principle
    if _DEFINITIONAL_START.search(definition) and not _PRESCRIPTIVE.search(hay):
        return QUARANTINE_CONTENT_TYPE              # hold — bare descriptive fact, owner review
    return None


def reroute_content_type(fb: dict, require_body_evidence: bool | None = None) -> str:
    """Deterministically correct a non-principle record's content_type (D-2747).

    D-343: content_type must NOT be LLM-classified (worse than constant baseline), so
    this is pure deterministic rules — no model call. First-match-wins across three tiers:
      1. owner-adjudicated map (fb_id → role)  — highest authority
      2. principle FORM invariant (D-2748/D-2749) — fail-closed, retained-only
      3. TI → process_template: a PROCEDURE-denoting name PLUS body evidence of a procedure
         (D-2955/BUG-729) — then structural (TI with neither syntax nor parameters → quarantine)

    The contested retention guard is applied FIRST: a `contested: true` record is
    growth_edge by construction, never dropped.

    Args:
        fb: A Stage 2 record dict with content_type + body fields.
        require_body_evidence: force tier 3's evidence gate on/off; None (the normal path) uses the
            configured policy. The override exists so the BUG-729 calibration can measure BOTH sides
            without editing config — the same shape as `principle_tension_hit(strict=...)`.

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
    # Tier 3 — PROCEDURE-DENOTING NAME + BODY EVIDENCE (D-2747 tier 3, narrowed by D-2955/BUG-729).
    # The name alone is not a discriminator: the ratified D275b procedure tests "tool/software-specific
    # command, syntax, or feature" FIRST, so a name-suffix promotion both inverts that order and reads
    # a software ARTIFACT as a method. Both conditions are read at CALL time so a config flip (or a
    # monkeypatch in the calibration) cannot be frozen into a long-lived process.
    if current == "tool_instruction":
        tool_name = str(fb.get("tool_name") or "").strip().lower()
        name_prior = bool(tool_name) and any(k in tool_name for k in TI_TO_PT_KEYWORDS)
        require: bool = TI_TO_PT_REQUIRE_BODY_EVIDENCE if require_body_evidence is None else require_body_evidence
        if name_prior and (has_procedure_evidence(fb) or not require):
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
_APPLICABILITY: dict = dict(_CT["applicability"])
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
