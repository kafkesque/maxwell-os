"""anchor_menu_guard.py — BUG-650 / D-2839 fail-closed pre-A/B anchor-referee guard.

WHY (BUG-650, 2026-10-05)
-------------------------
The full-204 A/B (D-2767) computes Cohen's kappa of the S4 classifier against the
204-row human-owner discipline/domain anchor. That anchor was adjudicated against
the PRE-D-2814 free-gen menu (menu v5), and menu v6 (D-2814/D-2815/D-2816) changed
the discipline slots, domain slots and the abstention token to 'emerging'. The
anchor's discipline/domain axis is therefore FROZEN-INVALID until re-derived against
menu v6 (D-2820), and the re-derived output must be owner-signed-off (D-2839).

A kappa computed before that re-derivation is CIRCULAR (the classifier is measured
against its own pre-D-2814 output) and would silently pass the 0.800 floor. This
module is the ENFORCEMENT limb of D-2839: it refuses to certify a menu-derived
anchor as a valid kappa referee unless its declared menu stamp matches menu v6's
LIVE pins (never the frozen v5 pins).

CONTRACT
--------
    assert_referee_menu_v6(doc, label=..., axis=...)  -> raises SystemExit unless valid
    referee_menu_v6_verdict(doc, label=..., axis=...) -> verdict dict, NEVER raises (testable)

The pins (live + frozen) are read from config/menu_axis_hashes.yaml (C12: single
source, never hardcoded). A missing/corrupt pin file fails closed (C16).

A valid anchor must carry a NON-EMPTY menu stamp (menu_hash / closed_menu_sha256 /
answer_space_sha256) matching menu v6's live pins and must NOT carry a frozen v5 pin.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# C12: pins live in config. These are only the SOURCE keys, never pin VALUES.
PINS_PATH = REPO_ROOT / "config" / "menu_axis_hashes.yaml"
_LIVE_COMPOSITE_KEY = "composite_hash_live"
_LIVE_ANSWER_KEY = "answer_space_hash"
_FROZEN_COMPOSITE_KEY = "composite_hash_frozen_pin"
_FROZEN_ANSWER_KEY = "answer_space_hash_frozen_pin"

# Canonical field names a re-derived (menu-v6) anchor/key carries. `closed_menu_sha256`
# is the composite; `answer_space_sha256` is the real answer-space pin (D-371/D-NEW-1).
# Aliases are accepted for back-compat with earlier manifests.
_COMPOSITE_FIELDS: tuple[str, ...] = ("menu_hash", "closed_menu_sha256", "composite_hash")
_ANSWER_SPACE_FIELDS: tuple[str, ...] = ("answer_space_hash", "answer_space_sha256")


def load_menu_v6_pins() -> dict[str, str]:
    """Read the menu-v6 live + frozen pins from config (C12, single source).

    Fail-closed (C16) if any pin is missing or empty: the referee guard must never
    silently default its pin source — that would be the exact circular-kappa hole
    this file exists to close.
    """
    import yaml

    raw = yaml.safe_load(PINS_PATH.read_text(encoding="utf-8")) or {}
    keys = (
        _LIVE_COMPOSITE_KEY,
        _LIVE_ANSWER_KEY,
        _FROZEN_COMPOSITE_KEY,
        _FROZEN_ANSWER_KEY,
    )
    missing = [k for k in keys if not raw.get(k)]
    if missing:
        raise SystemExit(
            f"FAIL: {PINS_PATH} is missing menu pin(s) {missing} — cannot run the "
            f"anchor-referee guard (C16: never silently default the pin source)."
        )
    return {k: str(raw[k]).strip() for k in keys}


def _pick(doc: dict[str, Any], fields: tuple[str, ...]) -> str | None:
    """Return the first non-empty declared value for ``fields`` (top-level or _provenance)."""
    for f in fields:
        v = doc.get(f)
        if v:
            return str(v).strip()
    prov = doc.get("_provenance")
    if isinstance(prov, dict):
        for f in fields:
            v = prov.get(f)
            if v:
                return str(v).strip()
    return None


def _find_menu_stamp(doc: dict[str, Any]) -> dict[str, str | None]:
    """Collect the declared composite + answer-space stamps from an anchor/key doc."""
    return {
        "composite": _pick(doc, _COMPOSITE_FIELDS),
        "answer_space": _pick(doc, _ANSWER_SPACE_FIELDS),
    }


def referee_menu_v6_verdict(
    doc: dict[str, Any], *, label: str, axis: str
) -> dict[str, Any]:
    """Return the menu-v6 referee verdict for a menu-derived anchor. NEVER raises.

    ``label`` names the artifact (a filename) and ``axis`` names the menu-derived
    axis under evaluation (e.g. 'discipline', 'domains') — both appear verbatim in
    the reason string so a refusal is auditable back to its source.
    """
    pins = load_menu_v6_pins()
    stamp = _find_menu_stamp(doc)
    declared = {k: v for k, v in stamp.items() if v}

    if not declared:
        return {
            "ok": False,
            "reason": (
                f"{label}: menu-derived axis {axis!r} carries NO menu stamp "
                f"(menu_hash/closed_menu_sha256/answer_space_sha256) — cannot certify "
                f"it as a menu-v6 referee; re-derive via D-2820 before any A/B (BUG-650)."
            ),
            "stamp": stamp,
            "live_hits": [],
            "frozen_hits": [],
        }

    frozen_pins = {pins[_FROZEN_COMPOSITE_KEY], pins[_FROZEN_ANSWER_KEY]}
    live_pins = {pins[_LIVE_COMPOSITE_KEY], pins[_LIVE_ANSWER_KEY]}
    frozen_hits = sorted({v for v in declared.values() if v in frozen_pins})
    live_hits = sorted({v for v in declared.values() if v in live_pins})

    if frozen_hits:
        return {
            "ok": False,
            "reason": (
                f"{label}: anchor stamped with FROZEN menu-v5 pin(s) {frozen_hits} — "
                f"frozen-invalid referee (D-2820); refuse kappa (BUG-650)."
            ),
            "stamp": stamp,
            "live_hits": live_hits,
            "frozen_hits": frozen_hits,
        }
    if not live_hits:
        return {
            "ok": False,
            "reason": (
                f"{label}: anchor menu stamp(s) {sorted(declared.values())} match "
                f"NEITHER menu-v6 live pin — cannot certify referee (BUG-650)."
            ),
            "stamp": stamp,
            "live_hits": [],
            "frozen_hits": [],
        }
    return {
        "ok": True,
        "reason": f"{label}: anchor is menu-v6-stamped ({live_hits}); referee valid.",
        "stamp": stamp,
        "live_hits": live_hits,
        "frozen_hits": [],
    }


def assert_referee_menu_v6(
    doc: dict[str, Any], *, label: str, axis: str
) -> dict[str, Any]:
    """Fail-closed (C16): raise SystemExit unless the anchor is a valid menu-v6 referee.

    Returns the verdict dict on success so callers can log/attach the live hits.
    """
    verdict = referee_menu_v6_verdict(doc, label=label, axis=axis)
    if not verdict["ok"]:
        raise SystemExit("BUG-650 FAIL-CLOSED: " + verdict["reason"])
    return verdict
