"""pipeline/closed_menu.py — Closed-menu renderer (R1 / D-279).

Builds the canonical classification menu from config/taxonomy.yaml +
config/content_types.yaml, with `emerging` as a FIRST-CLASS abstention value
(D-275b/D-277/D-2830: the classifier may answer "does not fit" rather than force-fit).

Returns a stable canonical JSON. Its sha256 is the `menu_hash` provenance stamp
(D-279): any label can be traced to the EXACT menu it was classified against,
which is the binding prerequisite for `min_human_share` (F-44) — without a menu
hash, a label is untraceable and its provenance share is unsatisfiable.

Read-only. No DB writes. Consumed by:
  - scripts/render_closed_menu.py (freeze the menu + hash to a file)
  - pipeline/stage4_merge.py  (stamp `menu_hash` on every classified FB)
  - scripts/definition_nli_verify.py (R2: NLI premise from menu definitions)

Config-first (C12): the menu is DERIVED from config, never hardcoded.
"""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TAXONOMY_PATH = _ROOT / "config" / "taxonomy.yaml"
_CONTENT_TYPES_PATH = _ROOT / "config" / "content_types.yaml"


def live_menu_path() -> Path:
    """Return the live frozen closed-menu path from the SINGLE config pointer.

    BUG-694 future-tax fix (C12/C27): the menu filename is owned by
    ``config/version.yaml#closed_menu`` — every consumer reads this one key instead
    of hardcoding ``closed_menu_v<N>.json``, so a menu revision can no longer
    silently leave a stale consumer behind.
    """
    version = _load_yaml(_ROOT / "config" / "version.yaml")
    rel = version.get("closed_menu")
    if not rel:
        raise RuntimeError(
            "config/version.yaml is missing the 'closed_menu' pointer "
            "(BUG-694 single-source fix)"
        )
    return _ROOT / rel

# Content-type roles (the 5 closed roles, D2323) + 2 dispositions (D2591).
_CONTENT_TYPE_ROLES = (
    "principle",
    "process_template",
    "process_instance",
    "tool_instruction",
    "growth_edge",
)
_CONTENT_TYPE_DISPOSITIONS = (
    "noise_drop",
    "quarantine",
)
_ABSTENTION_VALUE = "emerging"


def _load_yaml(path: Path) -> dict:
    import yaml

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _abstention() -> dict[str, str]:
    return {
        "value": _ABSTENTION_VALUE,
        "description": "first-class abstention (R1/D-279): does not fit any closed-menu value",
    }


def _taxonomy_entries(section: str, tax: dict) -> list[dict]:
    """Build {value, definition, group} for a taxonomy section (domains/disciplines)."""
    entries = []
    for e in tax.get(section, []):
        entries.append(
            {
                "value": e["canonical"],
                "definition": (e.get("definition") or "").strip(),
                "group": (e.get("group") or "").strip(),
            }
        )
    entries.sort(key=lambda d: d["value"])
    # catch-all (meta.catch_all_domain / catch_all_discipline → 'emerging')
    entries.append(
        {
            "value": "emerging",
            "definition": (tax.get("meta", {}).get("catch_all_description", "") or "").strip(),
            "group": "",
        }
    )
    return entries


def _content_type_entries(ct: dict) -> list[dict]:
    entries: list[dict] = []
    roles = ct.get("content_types", {})
    for name in _CONTENT_TYPE_ROLES:
        entries.append(
            {
                "value": name,
                "description": (roles.get(name, {}).get("description", "") or "").strip(),
            }
        )
    dispositions = ct.get("dispositions", {})
    for name in _CONTENT_TYPE_DISPOSITIONS:
        entries.append(
            {
                "value": name,
                "description": (dispositions.get(name, "") or "").strip(),
            }
        )
    entries.append(_abstention())
    return entries


def _extraction_type_entries(ct: dict) -> list[dict]:
    entries = [
        {"value": name, "description": (e.get("description", "") or "").strip()}
        for name, e in sorted(ct.get("extraction_types", {}).items())
    ]
    return entries


@lru_cache(maxsize=1)
def render_closed_menu() -> dict:
    """Render the canonical closed menu (content_types, extraction_types, disciplines, domains).

    Cached: the menu is deterministic given the config files. `emerging` is included as
    a first-class abstention on BOTH the content_type and (implicitly) the label axes
    (D-2830 single abstention token; D-2834 confirms it for the definition-anchored path).
    """
    tax = _load_yaml(_TAXONOMY_PATH)
    ct = _load_yaml(_CONTENT_TYPES_PATH)
    return {
        "schema_version": "1.0",
        "decision": "D-279",
        "abstention": _ABSTENTION_VALUE,
        "content_types": _content_type_entries(ct),
        "extraction_types": _extraction_type_entries(ct),
        "disciplines": _taxonomy_entries("disciplines", tax),
        "domains": _taxonomy_entries("domains", tax),
    }


def definition_anchored_block(menu: dict | None = None) -> str:
    """Render the definition-anchored closed menu (label + definition + abstention).

    D-2814 (2026-10-05): the free-generation prompt told the model to INVENT precise
    labels ("computational neuroscience > neuroscience"); the mapper then remapped those
    off-menu inventions to 'emerging' (~27%, BUG-629) or coerced them onto the wrong axis
    (BUG-630). The definition-anchored closed menu is the ROOT fix: the model sees every
    canonical label WITH its definition and picks VERBATIM, so it never free-generates.

    Fail-closed (C16): an enabled-but-empty menu raises rather than silently degrading
    back to free generation.

    D-2974/BUG-748: an optional menu makes a FROZEN revision renderable from this ONE home, which is
    what a re-scope differential needs (the same production injection path, only the menu differs). The
    default is the LIVE menu, so no production caller changes behaviour by one byte.

    Returns:
        A stable block (deterministic given config) for injection into the S4
        classification system prompt. Uses the menu's abstention token.
    """
    if menu is None:
        menu = render_closed_menu()
    abstention = menu["abstention"]
    disciplines = [e for e in menu["disciplines"] if e["value"] != abstention]
    domains = [e for e in menu["domains"] if e["value"] != abstention]
    if not disciplines or not domains:
        raise RuntimeError("D-2814: definition-anchored menu empty — fail closed (C16)")
    disc_lines = "\n".join(f'- "{e["value"]}" = {e["definition"]}' for e in disciplines)
    dom_lines = "\n".join(f'- "{e["value"]}" = {e["definition"]}' for e in domains)
    return (
        "CLOSED DISCIPLINE MENU — choose EXACTLY ONE label, verbatim; the definition is the anchor:\n"
        + disc_lines
        + "\n\nCLOSED DOMAIN MENU — choose 1-7 labels, verbatim; the definition is the anchor:\n"
        + dom_lines
        + f'\n\nABSTENTION — each axis abstains INDEPENDENTLY: if NO label fits ontologically AND '
        f'pragmatically for a given axis, output the literal token "{abstention}" AS THE VALUE for '
        f'that axis (in place of a label — e.g. discipline: "{abstention}", or "{abstention}" inside '
        f'domains). A real label on one axis and "{abstention}" on the other is VALID. NEVER invent '
        f'a new label, a more-specific variant, or a hyphenated merge — "{abstention}" is a valid answer.'
    )


def canonical_json(menu: dict | None = None) -> str:
    """Deterministic canonical JSON serialization of the menu (stable hash input)."""
    if menu is None:
        menu = render_closed_menu()
    return json.dumps(menu, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def menu_hash(menu: dict | None = None) -> str:
    """SHA-256 of the canonical menu — the provenance stamp recorded on every label."""
    return hashlib.sha256(canonical_json(menu).encode("utf-8")).hexdigest()


def menu_summary(menu: dict | None = None) -> dict:
    """Human-readable menu cardinalities + hash (for reports/logs)."""
    if menu is None:
        menu = render_closed_menu()
    return {
        "menu_hash": menu_hash(menu),
        "content_types": len(menu["content_types"]),
        "extraction_types": len(menu["extraction_types"]),
        "disciplines": len(menu["disciplines"]),
        "domains": len(menu["domains"]),
        "abstention": menu["abstention"],
    }


if __name__ == "__main__":  # pragma: no cover — quick self-check
    import sys

    s = menu_summary()
    print(f"menu_hash={s['menu_hash']}")
    print(f"content_types={s['content_types']} extraction_types={s['extraction_types']} "
          f"disciplines={s['disciplines']} domains={s['domains']} abstention={s['abstention']!r}")
    sys.exit(0)
