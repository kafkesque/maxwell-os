#!/usr/bin/env python3
"""pipeline/discipline_macro.py — ONE home (C21) for the fine->macro discipline collapse.

D-2884(a) / D-2798 (BUG-622): the fine 62-way `discipline` axis is ADVISORY (provenance
tags); the OPERATIVE routing facet is the 3-way MACRO (Technical / Human & Design /
Method & Business) + domains.

This module is the single source of truth for the deterministic collapse. Consumers:
  - stage6_commit.py                       (persists fbs.discipline_macro)
  - scripts/discipline_macro_classify.py   (Condition C instrument)
  - scripts/discipline_advisory_rescore.py (D-2798 advisory baseline)

Config (C12 — no hardcoded ontology):
  config/discipline_macro_groups.yaml  (scheme + group->bucket map)
  live closed-menu (config/version.yaml#closed_menu)  (disciplines[].group)

Fail-closed: a menu group absent from the active scheme raises (BUG-622 class drift);
a discipline with an empty group maps to the explicit ``emerging`` routing bucket
(never folded into a macro — D-2884).
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.pipeline_paths import PROJECT_ROOT  # noqa: E402
from pipeline.closed_menu import live_menu_path  # noqa: E402

_MACRO_GROUPS = PROJECT_ROOT / "config" / "discipline_macro_groups.yaml"
_MENU = live_menu_path()  # single source: config/version.yaml#closed_menu (BUG-694 fix)
EMERGING = "emerging"


@lru_cache(maxsize=1)
def load_macro() -> tuple[str, dict[str, list[str]], dict[str, str]]:
    """Return ``(scheme, bucket_members, disc_to_bucket)``.

    - scheme:          the active macro scheme ("3-way").
    - bucket_members:  macro bucket -> [canonical discipline values] (prompt menus).
    - disc_to_bucket:  canonical fine discipline -> macro bucket ('' group -> emerging).

    Cached once; fail-closed on any config drift (BUG-622 class).
    """
    import yaml

    doc: dict[str, Any] = yaml.safe_load(_MACRO_GROUPS.read_text(encoding="utf-8")) or {}
    scheme = str(doc.get("scheme", "3-way"))
    bucket_to_groups: dict[str, list[str]] = doc.get("macros", {}).get(scheme) or {}
    if not bucket_to_groups:
        raise SystemExit(f"FAIL: macro scheme {scheme!r} has no bucket map in {_MACRO_GROUPS.name}")
    emerging = str(doc.get("emerging_routing", EMERGING))

    group_to_bucket: dict[str, str] = {}
    for bucket, groups in bucket_to_groups.items():
        for g in groups or []:
            group_to_bucket[str(g)] = str(bucket)

    menu = json.loads(_MENU.read_text(encoding="utf-8"))
    disc_to_bucket: dict[str, str] = {}
    bucket_members: dict[str, list[str]] = {}
    for d in menu.get("disciplines", []):
        canon = str(d.get("value", ""))
        if not canon:
            continue
        group = str(d.get("group", ""))
        bucket = emerging if group == "" else group_to_bucket.get(group)
        if bucket is None:
            raise SystemExit(
                f"FAIL: macro scheme {scheme!r} does not cover group {group!r} "
                f"(discipline {canon!r}) — config drift, BUG-622 class"
            )
        disc_to_bucket[canon] = bucket
        bucket_members.setdefault(bucket, []).append(canon)

    # Guard: every non-emerging bucket must have members (fail-closed on empty bucket).
    for bucket in bucket_to_groups:
        if bucket not in bucket_members:
            raise SystemExit(f"FAIL: macro bucket {bucket!r} has zero member disciplines")
    return scheme, bucket_members, disc_to_bucket


def to_macro(disc: str, disc_to_bucket: dict[str, str]) -> str:
    """Map a canonical fine discipline to its macro bucket ('emerging' if off-menu)."""
    return disc_to_bucket.get(disc, EMERGING)


def macro_for(discipline: str) -> str:
    """Convenience: macro bucket for a single discipline (loads the map once)."""
    _, _, disc_to_bucket = load_macro()
    return to_macro(discipline, disc_to_bucket)
