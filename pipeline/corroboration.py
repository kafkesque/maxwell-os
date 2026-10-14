#!/usr/bin/env python3
"""pipeline/corroboration.py - D-2993/T-107: the WIRE SHAPE of corroboration, in ONE home.

WHY. `borp_score` was a single float that told an agent nothing true: MEASURED 2026-10-14, it is `0.0` on
7,640/7,640 canonical rows while 1,393 of those rows ARE corroborated (938 of them served). It was published by
THREE surfaces (the MCP payload, the OKF export, the Anytype push), so a fix written three times would be the
BUG-499/BUG-502 class - one rule in two places - applied to a CONTRACT. This module is therefore the ONE place the
graded tuple is assembled, and the three surfaces call it.

THE ONTOLOGY (D-2990/D-2992/D-2993). A row has THREE independent times, and only one of them is corroboration:
  * the READING (the body: one model's reading of one text at one commit);
  * the WORK (identity: `source_id = SHA-256(normalize_author|normalize_title)`, edition-collapsed, D-2308);
  * the CORROBORATION - a MEASURE over the row's own evidence set, never the memory of one run's clustering.
The tuple states that measure as a GRADED object rather than a scalar, because a scalar cannot say "two voices that
are one author and one domain" - and MEASURED, 35 of the 938 count-corroborated served rows ARE one-author or
one-domain. The independence axis is NOT computed here: its home is `pipeline/schema_accessor.py::isor_score`
(D2284/D2309) and this module READS the value that home persisted on the row.

ABSENCE IS NULL, NEVER A DEFAULT (D-2957). A row that was never rated publishes `independence: null` - not
`weak`, which would read as "measured, and bad", and not `0.0`. `sources` and `convergent` are null only when the
row carries no usable evidence set, never 0/False for an unreadable one.

WHAT IS DELIBERATELY NOT HERE. No threshold, no gate, no policy: this module publishes what the row measured. The
POLICY about a row the principle does not cover (T-118, owner word `tier`) lives in
config/served_fields.yaml#tier_policy - keeping the measure and the policy in separate homes is what stops a
measure from silently becoming a gate (D-2990).
"""
from __future__ import annotations

import json
from typing import Any

#: The tuple's keys IN ORDER. Declared in config/served_fields.yaml#promotions.corroboration.keys and asserted
#: against this module by scripts/check_served_fields.py: the shape a surface publishes may not drift from the
#: shape the declaration names (one contract, one home).
TUPLE_KEYS: tuple[str, ...] = (
    "sources",
    "convergent",
    "independence",
    "independence_score",
    "home",
)

#: The home STRING the tuple publishes: an agent (or a bug report) can go from the value to the rule that decided
#: it. A claim with a resolvable home is auditable; an orphan float is not.
MEASURE_HOME: str = "pipeline/schema_accessor.py::isor_score"


def _parsed(fb: dict[str, Any], field: str) -> Any:
    """One stored JSON field of a row, parsed, or None when it is absent or unreadable (never a silent default)."""
    raw: Any = fb.get(field)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(str(raw))
    except (ValueError, TypeError):
        return None


def measure_of(fb: dict[str, Any]) -> dict[str, Any] | None:
    """The row's persisted ISOR measure (`fbs.isor`, D2284/D2309) - None when the row was never rated.

    Args:
        fb: a row (or payload dict).

    Returns:
        The measured dict, or None. A missing measure is ABSENT, never a fabricated `weak`/0.0.
    """
    stored: Any = _parsed(fb, "isor")
    return stored if isinstance(stored, dict) else None


def corroboration_tuple(fb: dict[str, Any]) -> dict[str, Any]:
    """The graded corroboration of ONE row - the measure, never the policy.

    Args:
        fb: a row (or payload dict) carrying `source_ids`, `is_convergent` and, when available, `isor`.

    Returns:
        `{sources, convergent, independence, independence_score, home}`:
          * `sources` - the canonical WORKS the row's evidence set names (D2185/D2309). Re-derivable, and the
            parity rail scripts/check_corroboration_bit.py proves it against `source_diversity` on every row.
          * `convergent` - the stored bit (`>= 2 works` under the declared threshold), or None when unreadable.
          * `independence` / `independence_score` - the persisted measure, or null/null when never rated.
          * `home` - the rule's home, so the value is auditable from the wire alone.
    """
    ids: Any = _parsed(fb, "source_ids")
    sources: int | None = None
    if isinstance(ids, (list, tuple, set)):
        sources = len({str(x) for x in ids})
    elif isinstance(ids, dict):
        sources = len(ids)

    convergent: bool | None = None
    if fb.get("is_convergent") is not None:
        convergent = bool(int(fb.get("is_convergent") or 0))

    measure: dict[str, Any] | None = measure_of(fb)
    if measure is None:
        #: D-2957: an unrated row has NO tier. The measure's own `n_sources` is not used as a fallback either -
        #: the tuple reports what THIS row's evidence set holds, and only the persisted measure may rate it.
        independence: str | None = None
        independence_score: float | None = None
    else:
        independence = str(measure.get("rating") or "") or None
        raw_score: Any = measure.get("score")
        independence_score = float(raw_score) if isinstance(raw_score, (int, float)) else None

    return {
        "sources": sources,
        "convergent": convergent,
        "independence": independence,
        "independence_score": independence_score,
        "home": MEASURE_HOME,
    }
