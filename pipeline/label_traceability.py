"""Declared label-provenance traceability for a stored FB (BUG-497 / D-2640).

WHY: fbs.menu_hash is NULL/empty on 7,995 / 7,995 rows and so are all three per-axis `*_source`
tiers (MEASURED 2026-09-25). That is not a stage-6 write bug: the corpus predates the R1/D-279 stamp
at pipeline/stage4_merge.py, so the labels of those rows can never point back at the menu they were
produced against. But an EMPTY stamp read as "there was no menu" is indistinguishable from "the stamp
is broken", and the F-44 `min_human_share` gate is defined on menu_hash + *_source -- so the state is
DECLARED per row here instead of being inferred, differently, by each consumer (D-2638: a denominator
that is only COMPUTED cannot disagree with anything, so a measured population is declared).

ONE home (C21). The boundary itself -- scope columns, generation runs, measured population -- lives in
config/label_provenance.yaml (C12); this module hardcodes none of it and returns the state KEY so a
rename is a config edit, not a code edit. Nothing is backfilled: D-277 forbids manufacturing a
provenance claim, so a pre-boundary row stays `pre_boundary` for ever.

This axis is TRACEABILITY. It is NOT the C29 per-label source vocabulary (human_verbatim |
llm_extracted_from_source | llm_hypothesis) and NOT the eval provenance tiers of
config/eval_integrity.yaml. Three axes, three names, one meaning each.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "label_provenance.yaml"

# The declared vocabulary the module returns. Kept as a module constant so a config that renames a
# state fails CLOSED at load instead of returning a string no consumer knows (C16).
REQUIRED_STATES = ("stamped", "pre_boundary", "missing", "unstampable")
REQUIRED_KEYS = ("db", "table", "run_column", "stamp_columns", "states", "boundary")

_cache: dict[str, Any] | None = None


def load_config() -> dict[str, Any]:
    """Load (and cache) the `label_provenance` block, failing closed on an unusable declaration.

    Raises ValueError when the block is absent, a required key is missing, the state vocabulary is
    incomplete, or there is nothing to look for. A boundary that cannot classify a row is not a
    boundary -- it would silently read as "no findings" (C16).
    """
    global _cache
    if _cache is None:
        doc = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        block = (doc or {}).get("label_provenance")
        if not isinstance(block, dict):
            raise ValueError("config/label_provenance.yaml has no 'label_provenance' block")
        missing_keys = [k for k in REQUIRED_KEYS if k not in block]
        if missing_keys:
            raise ValueError(f"label_provenance is missing {missing_keys}")
        missing_states = [s for s in REQUIRED_STATES if s not in (block["states"] or {})]
        if missing_states:
            raise ValueError(f"label_provenance.states does not declare {missing_states}")
        if not block["stamp_columns"]:
            raise ValueError("label_provenance.stamp_columns is empty - there is nothing to look for")
        _cache = block
    return _cache


def stamp_columns(cfg: dict[str, Any] | None = None) -> list[str]:
    """The declared traceability quartet (menu_hash + the per-axis source tiers)."""
    cfg = cfg or load_config()
    return [str(c) for c in cfg["stamp_columns"]]


def boundary_runs(cfg: dict[str, Any] | None = None) -> set[str]:
    """The DECLARED pre-boundary generation runs -- a closed set, deliberately not a date.

    A date predicate would let a NEW run silently join the boundary and absorb its own gap; a closed
    set can only grow by an explicit edit of config/label_provenance.yaml.
    """
    cfg = cfg or load_config()
    return {str(r) for r in (cfg["boundary"].get("generation_runs") or [])}


def is_inside_boundary(row: dict[str, Any], cfg: dict[str, Any] | None = None) -> bool:
    """True when the row's declared generation run is inside the pre-provenance boundary."""
    cfg = cfg or load_config()
    return str(row.get(cfg["run_column"]) or "") in boundary_runs(cfg)


def traceability_of(row: dict[str, Any], cfg: dict[str, Any] | None = None) -> str:
    """Classify ONE row as stamped | pre_boundary | missing | unstampable (the declared vocabulary).

    `unstampable` is checked FIRST and read as a defect by the rail: a row dict with none of the
    stamp columns cannot be shown to be pre-boundary, and an un-evaluable row is never a pass
    (C16). A PARTIAL quartet is `missing`, not `stamped` -- half a traceability stamp is not
    traceability.
    """
    cfg = cfg or load_config()
    declared = [str(c) for c in cfg["stamp_columns"]]
    present = [c for c in declared if c in row]
    if not present:
        return "unstampable"
    complete = len(present) == len(declared)
    if complete and all(str(row.get(c) or "").strip() for c in present):
        return "stamped"
    return "pre_boundary" if is_inside_boundary(row, cfg) else "missing"
