#!/usr/bin/env python3
"""depth_pass_agreement.py — the FIRST consumer of config/agreement_floor.yaml (BUG-462).

WHAT IT MEASURES
----------------
Krippendorff's alpha for the depth axis panel: the four blind LLM coders against the owner's
INDEPENDENT blind pass (`owner_depth`, the 2026-09-24 drop-in). The owner's ADJUDICATED answer
(`depth_final`) is deliberately NOT a rater: the coder panel was shown to the owner while they
adjudicated, so scoring `depth_final` against the panel is circular. Alpha needs an independent
second reading, and the write-locked blind pass is one.

WHY ALPHA AND NOT RAW AGREEMENT (config/agreement_floor.yaml, must_not_be_cited_as)
----------------------------------------------------------------------------------
Raw agreement is not chance-corrected and cannot tolerate a rater who skipped a row; pairwise
kappa is not single-valued and silently drops skipped rows. Alpha is missing-cell capable and
single-valued, which is what a panel with 2-4 raters per row requires.

WHAT IS EXCLUDED, AND WHY (all config-declared, C12 — nothing is hardcoded here)
-------------------------------------------------------------------------------
* CARRY-FORWARD rows (config/anchor_workbook_fixes.yaml, status: CARRY-FORWARD): the answer was
  carried from an earlier owner pass under D-387, so it is not an independent second reading.
* DECLARED axis-exempt rows (config/depth_domain_contract.yaml, abstention.axis_exempt_rows):
  the row asserts no claim, so no axis reads it (AXIS_EXEMPT_DECLARED).
* ABSENT rows (config/cohort_declaration.yaml): never returned, never imputed (BUG-466).

BANDS, NOT A VERDICT
--------------------
The band is read from the floor file and printed. `--gate` exits 1 only when the instrument is
declared in the floor's `applies_to` AND the value is below `operative_floor`; `--report-only`
(the form wired into `just health`) never fails the aggregate rail, because a measurement below a
floor is a FINDING the owner acts on, not a broken rail.

Usage:
    python3 scripts/depth_pass_agreement.py                 # measure + report
    python3 scripts/depth_pass_agreement.py --gate          # the same, exit 1 below the floor
    python3 scripts/depth_pass_agreement.py --check-cohort   # denominator check only, no statistic
"""
from __future__ import annotations

import argparse
import csv
from lib import artifact_encoding  # noqa: E402 - the ONE home for reading a declared encoding (D-2644)
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "config"
FLOOR = CONFIG / "agreement_floor.yaml"
WORKBOOK_FIXES = CONFIG / "anchor_workbook_fixes.yaml"
CONTRACT = CONFIG / "depth_domain_contract.yaml"
COHORT = CONFIG / "cohort_declaration.yaml"
DEPTH_MENU = CONFIG / "depth_classes.yaml"
PANEL_KEY = "depth_axis_panel"


class AgreementError(RuntimeError):
    """A declared input is missing or a datum is outside the declared menu (fail closed, C16)."""


def _load(path: Path) -> dict[str, Any]:
    """Load a YAML document, failing closed when it is missing."""
    if not path.exists():
        raise AgreementError(f"declared input missing: {path.relative_to(REPO)}")
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def krippendorff_alpha(
    units: Iterable[dict[str, Any]],
    value_order: list[Any],
    metric: str = "nominal",
) -> dict[str, float]:
    """Krippendorff's alpha over units, each a {rater: value} mapping.

    Args:
        units: one mapping per unit; a missing rater is an ABSENT cell (never a value).
        value_order: the closed menu, ordered — required for the ordinal metric.
        metric: 'nominal' (delta = 1 for any disagreement) or 'ordinal'.

    Returns:
        {'alpha', 'Do', 'De', 'n', 'units_used'} where n is the number of pairable values.

    A unit with fewer than 2 ratings carries no information about agreement and is dropped
    (that is the missing-cell capability the floor file requires).
    """
    units = [u for u in units if len(u) >= 2]
    coincidence: dict[tuple[Any, Any], float] = {}

    for unit in units:
        values = list(unit.values())
        m = len(values)
        for i, c in enumerate(values):
            for j, k in enumerate(values):
                if i == j:
                    continue
                coincidence[(c, k)] = coincidence.get((c, k), 0.0) + 1.0 / (m - 1)

    # marginals are the coincidence ROW SUMS (Krippendorff 2004, eq. 2.5).
    n_c: dict[Any, float] = {v: 0.0 for v in value_order}
    for (c, _k), o in coincidence.items():
        n_c[c] += o
    n = sum(n_c.values())
    if n <= 1:
        raise AgreementError("fewer than two pairable ratings — alpha is undefined")

    def delta2(c: Any, k: Any) -> float:
        if metric == "nominal":
            return 0.0 if c == k else 1.0
        if metric != "ordinal":
            raise AgreementError(f"unknown metric {metric!r}")
        lo, hi = value_order.index(c), value_order.index(k)
        if lo > hi:
            lo, hi = hi, lo
        inner = sum(n_c[v] for v in value_order[lo : hi + 1]) - (n_c[c] + n_c[k]) / 2.0
        return inner * inner

    do = sum(o * delta2(c, k) for (c, k), o in coincidence.items()) / n
    de = sum(n_c[c] * n_c[k] * delta2(c, k) for c in value_order for k in value_order) / (n * (n - 1))
    if de == 0:
        raise AgreementError("expected disagreement is 0 (every rater used one value) — alpha undefined")
    return {"alpha": 1.0 - do / de, "Do": do, "De": de, "n": n, "units_used": len(units)}


def load_panel() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (floor panel block, cohort block), validating every declared path."""
    floor = _load(FLOOR)
    panel = (floor.get("panels") or {}).get(PANEL_KEY)
    if not panel:
        raise AgreementError(f"{FLOOR.name} declares no panels.{PANEL_KEY} — nothing to measure")
    return floor, panel


def excluded_rows() -> dict[str, list[str]]:
    """Rows excluded from the panel, each set read from the artifact that OWNS the declaration."""
    fixes = _load(WORKBOOK_FIXES)
    carry = sorted(
        item for item, r in (fixes.get("owner_rulings") or {}).items() if str(r.get("status")) == "CARRY-FORWARD"
    )
    contract = _load(CONTRACT)
    exempt = sorted((contract.get("abstention") or {}).get("axis_exempt_rows") or [])
    cohort_cfg = _load(COHORT)
    cohort = (cohort_cfg.get("cohorts") or {}).get(PANEL_KEY_COHORT, {})
    absent = sorted(cohort.get("absent_rows") or [])
    return {"carry_forward": carry, "axis_exempt": exempt, "absent": absent}


PANEL_KEY_COHORT = "anchor4_depth"


def check_cohort(panel: dict[str, Any], verbose: bool = True) -> dict[str, Any]:
    """Verify the declared denominator against the manifest and the workbook (BUG-466)."""
    cohort_cfg = _load(COHORT)
    cohort = (cohort_cfg.get("cohorts") or {}).get(PANEL_KEY_COHORT, {})
    manifest = json.loads((REPO / cohort["declared_by"].split("#")[0]).read_text(encoding='utf-8'))
    declared_rows = int(manifest["sheet"]["rows"])
    if declared_rows != int(cohort["declared_rows"]):
        raise AgreementError(
            f"cohort declaration says {cohort['declared_rows']} rows; {cohort['declared_by']} says {declared_rows}"
        )
    # MEASURED 2026-09-26 (BUG-506 class, second reader): a bare .open() read this OWNER-DROPPED workbook as
    # strict UTF-8 and CRASHED on its MacRoman bytes, with a bare UnicodeDecodeError naming no artifact. The
    # artifact's encoding is DECLARED (scripts/lib/artifact_encoding.py is the one home for reading it).
    with artifact_encoding.open_artifact(REPO / cohort["measured_from"], REPO) as fh:
        rows = list(csv.DictReader(fh))
    measured = len(rows)
    declared_measured = cohort.get("measured_rows")
    if declared_measured is None:
        raise AgreementError(
            "cohort declaration carries no measured_rows: a count computed only at run time cannot "
            "DISAGREE with the artifact it counts, so a silently changed denominator stays invisible "
            "(BUG-501/D-402). Declare the expected count."
        )
    if int(declared_measured) != measured:
        raise AgreementError(
            f"declared measured_rows {declared_measured} != workbook rows {measured} "
            f"({cohort['measured_from']}) - the denominator changed and the declaration did not (BUG-466)"
        )
    absent = sorted(cohort.get("absent_rows") or [])
    ids = {r["item_id"] for r in rows}
    if ids & set(absent):
        raise AgreementError(f"declared-absent rows are PRESENT in the workbook: {sorted(ids & set(absent))}")
    if measured + len(absent) != declared_rows:
        raise AgreementError(
            f"denominator does not close: measured {measured} + absent {len(absent)} != declared {declared_rows}"
        )
    if verbose:
        print(f"cohort {PANEL_KEY_COHORT}: declared {declared_rows} | measured {measured} | absent {absent} (declared, never imputed)")
    return {"declared": declared_rows, "measured": measured, "absent": absent}


def build_units(panel: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build the rafter matrix from the workbook: units are rows, raters are declared columns."""
    cohort = (_load(COHORT).get("cohorts") or {})[PANEL_KEY_COHORT]
    with artifact_encoding.open_artifact(REPO / cohort_measured(cohort), REPO) as fh:
        rows = list(csv.DictReader(fh))
    alias = {str(k): int(v) for k, v in (_load(WORKBOOK_FIXES).get("depth_alias") or {}).items()}
    menu = [int(c["id"]) for c in _load(DEPTH_MENU)["classes"]]
    abstain = set(panel.get("abstention_tokens") or [])
    excluded = excluded_rows()
    drop = {r for group in excluded.values() for r in group}

    units: list[dict[str, Any]] = []
    skipped: list[tuple[str, str]] = []
    for row in rows:
        item = row["item_id"]
        if item in drop:
            skipped.append((item, "excluded (declared)"))
            continue
        ratings: dict[str, int] = {}
        for rater in panel["rater_columns"]:
            raw = (row.get(rater) or "").strip()
            if raw == "" or raw in abstain:
                continue  # absent cell: alpha tolerates it (missing_cells: capable)
            if raw in alias:
                ratings[rater] = alias[raw]
            elif raw.lstrip("-").isdigit() and int(raw) in menu:
                ratings[rater] = int(raw)
            else:
                raise AgreementError(
                    f"{item}: rater {rater} holds {raw!r}, which is neither in {DEPTH_MENU.name} nor an "
                    f"declared abstention token {sorted(abstain)} — fail closed, never coerced"
                )
        units.append(ratings)

    # BUG-476: alpha is missing-cell capable, so a declared rater whose column is EMPTY is silently
    # tolerated and the receipt claims a panel that was never run. Make the gap visible (C16).
    rated = {r: sum(1 for u in units if r in u) for r in panel["rater_columns"]}
    empty = [r for r in panel["rater_columns"] if rated[r] == 0]
    if empty:
        print(
            f"⚠️  BUG-476: {len(empty)} of {len(panel['rater_columns'])} DECLARED rater column(s) hold NO ratings "
            f"at all: {', '.join(empty)}"
        )
        print(
            "    the measured panel is therefore smaller than the declared one; alpha cannot see this because a "
            "missing cell is legal (fail-visible, never silent)"
        )
    return units, {
        "rows": len(rows),
        "units": len(units),
        "excluded": excluded,
        "skipped": skipped,
        "menu": menu,
        "rated": rated,
        "empty_raters": empty,
    }


def cohort_measured(cohort: dict[str, Any]) -> str:
    """Return the measured-artifact path declared for a cohort."""
    return str(cohort["measured_from"])


def report(floor: dict[str, Any], panel: dict[str, Any], units: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    """Compute alpha (nominal + ordinal), classify the band, and print the receipt."""
    menu = meta["menu"]
    nominal = krippendorff_alpha(units, menu, "nominal")
    ordinal = krippendorff_alpha(units, menu, "ordinal")
    bands = floor.get("bands") or {}
    operative = float(floor["operative_floor"])
    reporting = float(floor["reporting_floor"])
    if nominal["alpha"] >= operative:
        band = "at_or_above_operative"
    elif nominal["alpha"] >= reporting:
        band = "reporting_to_operative"
    else:
        band = "below_reporting"

    print(f"depth panel — {len(units)} independent unit(s), {len(panel['rater_columns'])} declared rater column(s)")
    rated = meta.get("rated") or {}
    print(f"  raters        : {', '.join(panel['rater_columns'])}")
    if rated:
        print("  raters rated  : " + ", ".join(f"{r}={rated.get(r, 0)}" for r in panel["rater_columns"]))
    print(f"  excluded      : " + "; ".join(f"{k}={v}" for k, v in meta['excluded'].items() if v))
    print(f"  alpha nominal : {nominal['alpha']:.4f}   (Do {nominal['Do']:.4f} / De {nominal['De']:.4f}, n={nominal['n']:.0f})")
    print(f"  alpha ordinal : {ordinal['alpha']:.4f}   (Do {ordinal['Do']:.4f} / De {ordinal['De']:.4f})")
    print(f"  floor         : reporting {reporting} / operative {operative}  ({floor.get('statistic')})")
    print(f"  band          : {band} — {bands.get(band, '')}")
    return {
        "alpha_nominal": nominal,
        "alpha_ordinal": ordinal,
        "band": band,
        "units": len(units),
        "measured_rows": meta["rows"],
        "excluded": meta["excluded"],
        "operative_floor": operative,
        "reporting_floor": reporting,
    }


def main(argv: list[str] | None = None) -> int:
    """Entry point: measure the declared panel, classify the band, optionally gate."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", action="store_true", help="exit 1 when the instrument is declared and alpha < operative_floor")
    ap.add_argument("--report-only", action="store_true", help="never exit non-zero (the form wired into `just health`)")
    ap.add_argument("--check-cohort", action="store_true", help="denominator check only, no statistic")
    args = ap.parse_args(argv)

    floor, panel = load_panel()
    check_cohort(panel)
    if args.check_cohort:
        return 0

    units, meta = build_units(panel)
    result = report(floor, panel, units, meta)

    if meta.get("empty_raters") and args.gate:
        print(
            f"🛑 BUG-476: declared rater(s) with ZERO ratings: {meta['empty_raters']} — the declared panel was not "
            "run, so this alpha is not the panel's figure and gates nothing"
        )
        return 1

    gated = PANEL_KEY in (floor.get("applies_to") or [])
    if args.gate and gated and result["alpha_nominal"]["alpha"] < result["operative_floor"]:
        print(
            f"🛑 depth panel alpha {result['alpha_nominal']['alpha']:.4f} < operative floor "
            f"{result['operative_floor']} — the depth axis may NOT be frozen on this number (D2130: the band informs)"
        )
        return 1
    if not gated:
        print(f"note: {PANEL_KEY} is not listed in {FLOOR.name}:applies_to — this number gates nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
