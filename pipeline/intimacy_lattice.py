#!/usr/bin/env python3
"""
intimacy_lattice.py — INTIMACY_BOUNDARY + space routing (ported from v1 D369/D383).
================================================================================
Authority: config/intimacy_policy.yaml + config/domain_anchors.yaml `routing:`.

Restores the v1 three-signal intimacy lattice that was lost in the v2→v3
migration (S4 hardcoded `intimacy_boundary="public"`). Resolution is a
lattice-MAX over three 2.0-native signals — order-independent, always
escalating toward private (D369):

  1. source_sensitivity — field routing: the FB's discipline/domains map to a
     `field_*` in domain_anchors.yaml whose `routing:` is `private`
     (field_5 personal_practice / field_7 influence_power).
  2. topic_sensitivity  — the FB's discipline is in
     `topic_sensitive_disciplines` (v1 R5: sensitive topic from an innocent book).
  3. context            — personal-only → private (R7), mixed-personal → selective (R8).

Usage:
    from pipeline.intimacy_lattice import resolve_intimacy, route_space

    boundary, rule = resolve_intimacy(fb)   # -> ("private", "R7")
    space = route_space(fb)                 # -> "private" | "non_private"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = ROOT / "config" / "intimacy_policy.yaml"
ANCHORS_FILE = ROOT / "config" / "domain_anchors.yaml"

# Level hierarchy (private > selective > public) — read from YAML (C12), with a
# code fallback ONLY so a missing config still resolves (never silently public).
_FALLBACK_LEVELS: dict[str, int] = {"private": 3, "selective": 2, "public": 1}

_POLICY_CACHE: dict[str, Any] | None = None
_ANCHOR_CACHE: dict[str, Any] | None = None
_CONFIG_ERROR: str | None = None  # set if a config file failed to load (privacy fail-safe)


def _record_config_error(which: str, exc: Exception) -> None:
    """Record a config-load failure loudly (C16) — never swallow silently.

    A policy/anchor load failure must not silently degrade the lattice toward
    public. It is logged AND recorded so resolve_intimacy() can fail closed to
    private (the declared privacy floor).
    """
    global _CONFIG_ERROR
    _CONFIG_ERROR = f"{which}: {type(exc).__name__}: {exc}"
    import sys
    print(f"⚠️  intimacy_lattice: {_CONFIG_ERROR} — resolving private (fail-safe)", file=sys.stderr)


def _load_policy() -> dict[str, Any]:
    """Load config/intimacy_policy.yaml (cached)."""
    global _POLICY_CACHE
    if _POLICY_CACHE is not None:
        return _POLICY_CACHE
    if POLICY_FILE.exists():
        try:
            _POLICY_CACHE = yaml.safe_load(POLICY_FILE.read_text()) or {}
        except Exception as e:
            _record_config_error("intimacy_policy.yaml", e)
            _POLICY_CACHE = {}
    else:
        _record_config_error("intimacy_policy.yaml missing", FileNotFoundError(POLICY_FILE))
        _POLICY_CACHE = {}
    return _POLICY_CACHE


def _load_anchors() -> dict[str, Any]:
    """Load config/domain_anchors.yaml (cached)."""
    global _ANCHOR_CACHE
    if _ANCHOR_CACHE is not None:
        return _ANCHOR_CACHE
    if ANCHORS_FILE.exists():
        try:
            _ANCHOR_CACHE = yaml.safe_load(ANCHORS_FILE.read_text()) or {}
        except Exception as e:
            _record_config_error("domain_anchors.yaml", e)
            _ANCHOR_CACHE = {}
    else:
        _record_config_error("domain_anchors.yaml missing", FileNotFoundError(ANCHORS_FILE))
        _ANCHOR_CACHE = {}
    return _ANCHOR_CACHE


def _levels() -> dict[str, int]:
    """Resolve the level hierarchy from YAML (C12), falling back to code only if absent."""
    policy = _load_policy()
    raw = policy.get("levels") or {}
    levels: dict[str, int] = {}
    for name, val in raw.items():
        try:
            levels[str(name)] = int(val)
        except (TypeError, ValueError):
            continue
    return levels or _FALLBACK_LEVELS


def _norm(name: Any) -> str:
    """Normalize a name for fuzzy matching (lowercase + strip)."""
    return str(name or "").strip().lower()


def _build_field_index() -> dict[str, str]:
    """Reverse index: normalized discipline/domain name → field id.

    Walks each field anchor's `subfolders` and `cross_domains` (and the field
    `name` itself) and maps every name to the field id. Used to resolve which
    field an FB belongs to, then look up that field's space routing.
    """
    anchors = _load_anchors()
    index: dict[str, str] = {}
    for anchor in anchors.get("anchors", []):
        field_id = anchor.get("id", "")
        if not field_id:
            continue
        names = [anchor.get("name", "")]
        for section in ("subfolders", "cross_domains"):
            for entry in anchor.get(section, []) or []:
                if isinstance(entry, dict) and entry.get("name"):
                    names.append(entry["name"])
        for n in names:
            key = _norm(n)
            if key and key not in index:
                index[key] = field_id
    return index


def get_source_sensitivity(fb: dict[str, Any]) -> str:
    """Signal 1 — source sensitivity via field routing + explicit private list.

    Returns "private" if:
      (a) the FB's discipline is in `source_private_disciplines` (config), or
      (b) the discipline/domains map to a field whose `routing:` is `private`
          (domain_anchors.yaml).
    Otherwise "public" (not source-sensitive).
    """
    policy = _load_policy()
    private_disc = {_norm(d) for d in policy.get("source_private_disciplines", []) or []}
    if _norm(fb.get("discipline", "")) in private_disc:
        return "private"

    anchors = _load_anchors()
    routing = anchors.get("routing", {}) or {}
    index = _build_field_index()

    names = [fb.get("discipline", "")]
    domains = fb.get("domains", []) or []
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]
    names.extend(domains)

    for n in names:
        field_id = index.get(_norm(n))
        if field_id and routing.get(field_id) == "private":
            return "private"
    return "public"


def get_topic_sensitivity(fb: dict[str, Any]) -> bool:
    """Signal 2 — topic sensitivity (v1 R5)."""
    policy = _load_policy()
    sensitive = {_norm(d) for d in policy.get("topic_sensitive_disciplines", []) or []}
    return _norm(fb.get("discipline", "")) in sensitive


def get_annotation_sensitivity(fb: dict[str, Any]) -> bool:
    """Signal (v1 R4) — personal annotation, if the curation fields are present.

    v2 curation fields (`why_this_matters_to_me`, `embodiment_tag`) are not
    produced by the pipeline, so this is normally False. Preserved for parity
    with the v1 lattice and for post-pipeline curation enrichments.
    """
    wtm = fb.get("why_this_matters_to_me", fb.get("WHY_THIS_MATTERS_TO_ME", ""))
    if wtm not in (None, "", "NULL"):
        return True
    emb = fb.get("embodiment_tag", fb.get("EMBODIMENT_TAG", ""))
    if emb not in (None, ""):
        return True
    return False


def _context_labels(fb: dict[str, Any]) -> list[str]:
    """Extract the S4 `context` label list from an FB dict."""
    raw = fb.get("context", "")
    if isinstance(raw, list):
        return [_norm(c) for c in raw]
    return [_norm(c) for c in str(raw).split(",") if c.strip()]


def resolve_intimacy(fb: dict[str, Any]) -> tuple[str, str]:
    """Resolve INTIMACY_BOUNDARY from the three-signal lattice.

    Args:
        fb: FB dict with (at minimum) `context`, `discipline`, `domains`.

    Returns:
        (intimacy_value, fired_rule_id) — value is "private" | "selective" | "public".

    Fail-safe (D369 null escalation + C16): a config-load failure or a wholly
    absent/ambiguous signal set resolves PRIVATE, never silently public.
    """
    levels = _levels()

    # D369 / sovereignty floor: if the policy/anchors failed to load, we cannot
    # trust the lattice to route correctly — fail closed to private.
    if _CONFIG_ERROR is not None:
        return ("private", "R0-config-failure")

    source_sens = get_source_sensitivity(fb)
    topic_sensitive = get_topic_sensitivity(fb)
    has_annotation = get_annotation_sensitivity(fb)
    ctx = _context_labels(fb)

    has_personal = "personal" in ctx
    personal_only = len(ctx) == 1 and has_personal
    mixed_personal = has_personal and not personal_only

    source_private = source_sens == "private"

    # D369 null escalation: if NO signal is evaluable (no discipline, no domains,
    # no context), ambiguity resolves UPWARD to private — never public.
    discipline = _norm(fb.get("discipline", ""))
    domains = fb.get("domains", []) or []
    if isinstance(domains, str):
        domains = [d.strip() for d in domains.split(",") if d.strip()]
    if not discipline and not domains and not ctx:
        return ("private", "R0-null")

    max_level = levels.get("public", 1)
    fired_rule = "R9"

    # (rule_id, level, matches) — order-independent lattice MAX (v1).
    rule_checks: list[tuple[str, int, bool]] = [
        ("R2", levels.get("private", 3), source_private),                      # source is private
        ("R3", levels.get("private", 3), has_annotation and has_personal),     # annotation on personal context
        ("R4", levels.get("selective", 2), has_annotation),                    # any personal annotation
        ("R5", levels.get("selective", 2), topic_sensitive),                   # topic is sensitive
        ("R7", levels.get("private", 3), personal_only),                       # personal-only context (D314 floor)
        ("R8", levels.get("selective", 2), mixed_personal),                    # mixed personal context
    ]
    for rule_id, level, matches in rule_checks:
        if matches and level > max_level:
            max_level = level
            fired_rule = rule_id

    level_to_name = {v: k for k, v in levels.items()}
    return (level_to_name.get(max_level, "private"), fired_rule)


def route_space(fb: dict[str, Any]) -> str:
    """Resolve the target Anytype space: "private" | "non_private".

    private/selective → private space; public → non-private (Knowledge base).
    Mirrors v1 `push_anytype.resolve_space`.

    Fail-safe (sovereignty floor): an unexpected boundary resolves PRIVATE, not
    non_private — routing must never leak toward public on a config drift.
    """
    boundary, _ = resolve_intimacy(fb)
    policy = _load_policy()
    space_routing = policy.get("space_routing") or {
        "private": "private",
        "selective": "private",
        "public": "non_private",
    }
    return space_routing.get(boundary, "private")
