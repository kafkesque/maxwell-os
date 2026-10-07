#!/usr/bin/env python3
"""Build the S4 golden/eval split manifest (D-2813, OG-1 = OPTION A).

WHY (D-2729/D-2731/D-2813): the 208 anchors split into a 46-id golden pool (S4 few-shot
exemplars) and a 162-id eval set. The golden pool must NEVER overlap eval, or S4 is evaluated
on data it was few-shot on and every downstream number becomes circular. This builder emits the
manifest deterministically (no RNG, no LLM) so the same committed anchor artifact always yields
the same split, and scripts/verify_split_manifest.py enforces the disjointness fail-closed.

Sampling design (config-first; all numbers come from config/eval_integrity.yaml):
  1. Start from the 203 golden-eligible anchors (golden_eligible == true in the consolidated
     artifact; R021 noise_drop + R040/R053/R080/R091 emerging are excluded by construction).
  2. Depth-proportional allocation (largest remainder) across the 4 depth classes, with a forced
     `minority_depth_floor` so the single universal-depth anchor is always an exemplar (F-10).
  3. Maximize distinct-discipline coverage: one exemplar per distinct discipline, rarest-first
     (few-shot exemplars are MOST valuable for rare labels where the frozen model's prior is
     weakest; common labels are already covered by the prior + the always-injected closed menu),
     gated by the remaining depth-seat budget so depth proportionality is preserved. Deterministic
     tiebreak on item_id.

The manifest also records a coverage table (which depth x discipline cells have zero exemplars ->
zero-shot + declared) and a `non_golden_declared` ledger naming the 5 excluded rows and why.

Usage:  python3 scripts/build_split_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "eval_integrity.yaml"

# Canonical form for the ids_sha256 immutability pin (BUG-603: the pin's serialization is now
# DOCUMENTED here so it is reproducible): sha256 of the newline-joined, sorted golden_pool_ids.
IDS_SHA256_CANON = "sha256(\\n.join(sorted(golden_pool_ids)))"


def _load_config() -> dict:
    """Return the split_manifest block from config/eval_integrity.yaml (C12: no hardcoded values)."""
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    block = cfg.get("split_manifest") or {}
    for key in ("source", "golden_pool_count", "total_anchors"):
        if not block.get(key):
            raise SystemExit(f"FAIL-CLOSED: {CONFIG} split_manifest.{key} is unset (C12)")
    return block


def _largest_remainder(counts: dict[str, int], seats: int) -> dict[str, int]:
    """Largest-remainder seat allocation over `counts` (all >0) summing to `seats`."""
    total = sum(counts.values())
    alloc: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    used = 0
    for k, c in counts.items():
        quota = seats * c / total
        alloc[k] = int(quota)
        used += int(quota)
        remainders.append((quota - int(quota), k))
    for _, k in sorted(remainders, reverse=True):
        if used >= seats:
            break
        alloc[k] += 1
        used += 1
    return alloc


def _ids_sha256(ids: list[str]) -> str:
    """Return the documented canonical sha256 pin over the sorted golden id list (BUG-603)."""
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def main() -> int:
    cfg = _load_config()
    source = ROOT / cfg["source"]
    artifact = json.loads(source.read_text(encoding="utf-8"))
    rows = artifact.get("rows") or []

    golden = [r for r in rows if r.get("golden_eligible")]
    non_golden = [r for r in rows if not r.get("golden_eligible")]
    if len(golden) + len(non_golden) != cfg["total_anchors"]:
        raise SystemExit(f"FAIL-CLOSED: golden+non_golden {len(golden)+len(non_golden)} != total {cfg['total_anchors']}")

    depth_order: list[str] = cfg["depth_order"]
    floor: dict[str, int] = cfg.get("minority_depth_floor") or {}
    n = cfg["golden_pool_count"]

    # Group golden rows by depth; discipline frequency computed globally (for rarest-first).
    by_depth: dict[str, list[dict]] = defaultdict(list)
    disc_freq = Counter(r["discipline"] for r in golden)
    for r in golden:
        by_depth[r["depth_label"]].append(r)

    # Depth seat allocation: force minority floors first, then largest-remainder on the rest.
    seats: dict[str, int] = {d: floor.get(d, 0) for d in depth_order}
    forced = sum(seats.values())
    remaining_seats = n - forced
    unfilled = {d: len(by_depth[d]) for d in depth_order if floor.get(d, 0) == 0}
    if unfilled:
        lr = _largest_remainder(unfilled, remaining_seats)
        for d, s in lr.items():
            seats[d] += s

    # Select exemplars to MAXIMIZE distinct-discipline coverage while honoring depth seats:
    #   pass 1 = one exemplar per distinct discipline, rarest-discipline-first (weakest prior -> most
    #            marginal value), gated by the remaining depth seat budget so depth stays proportional;
    #   pass 2 = (unused at 46 < 51) second exemplars for any discipline, for robustness.
    # Deterministic: sorted rows, no RNG.
    rows_sorted = sorted(
        golden, key=lambda r: (disc_freq[r["discipline"]], r["item_id"])
    )
    remaining_seats = dict(seats)
    covered: set[str] = set()
    selected: list[str] = []
    for r in rows_sorted:
        d = r["depth_label"]
        if r["discipline"] in covered or remaining_seats.get(d, 0) <= 0:
            continue
        covered.add(r["discipline"])
        selected.append(r["item_id"])
        remaining_seats[d] -= 1
    if sum(remaining_seats.values()) > 0:
        for r in rows_sorted:
            d = r["depth_label"]
            if remaining_seats.get(d, 0) <= 0:
                continue
            selected.append(r["item_id"])
            remaining_seats[d] -= 1
            if sum(remaining_seats.values()) == 0:
                break

    selected_sorted = sorted(selected)
    golden_set = set(selected_sorted)
    eval_ids = sorted(r["item_id"] for r in rows if r["item_id"] not in golden_set)

    # Coverage table: depth x discipline cells with ZERO exemplars among the 46.
    pool_cells = Counter((r["depth_label"], r["discipline"]) for r in golden)
    sel_cells = Counter(
        (r["depth_label"], r["discipline"]) for r in golden if r["item_id"] in golden_set
    )
    uncovered_cells = sorted(
        (d, disc) for (d, disc), c in pool_cells.items() if sel_cells.get((d, disc), 0) == 0
    )
    disc_in_sel = sorted({r["discipline"] for r in golden if r["item_id"] in golden_set})
    uncovered_disc = sorted(
        {r["discipline"] for r in golden} - {r["discipline"] for r in golden if r["item_id"] in golden_set}
    )

    manifest = {
        "schema_version": "2.0",
        "generated_by": "D-2813 (scripts/build_split_manifest.py)",
        "owner_gate": "OG-1",
        "option": "A",
        "policy": "disjoint split + machine-enforced manifest",
        "leakage_guard": "D-337/D-300/D-345",
        "total_anchors": cfg["total_anchors"],
        "golden_pool_count": cfg["golden_pool_count"],
        "eval_count": cfg["eval_count"],
        "golden_pool_source": str(source.relative_to(ROOT)),
        "stratification": {
            "method": cfg["stratification"],
            "depth_seats": seats,
            "minority_depth_floor": floor,
        },
        "golden_pool_ids": selected_sorted,
        "eval_ids": eval_ids,
        "coverage": {
            "depth_seats": seats,
            "discipline_distinct_in_golden_pool": len({r["discipline"] for r in golden}),
            "discipline_distinct_in_exemplars": len(disc_in_sel),
            "uncovered_disciplines": uncovered_disc,
            "uncovered_depth_discipline_cells": [
                {"depth": d, "discipline": disc, "n_examples": 0}
                for d, disc in uncovered_cells
            ],
        },
        "non_golden_declared": [
            {
                "item_id": r["item_id"],
                "reason": "noise_drop" if r.get("discipline") is None and r.get("depth_label") is None else "emerging",
                "depth": r.get("depth_label"),
                "discipline": r.get("discipline"),
            }
            for r in sorted(non_golden, key=lambda x: x["item_id"])
        ],
        "ids_sha256": _ids_sha256(selected_sorted),
        "ids_sha256_canonical_form": IDS_SHA256_CANON,
        "rail": "sha256-pinned: a check MUST fail if any golden_pool id re-enters eval (208->162 invariant)",
        "bootstrap": "cross-model vote >=2/3 (D2362); POST-rerun; owner adjudicates disagreements only",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    out = ROOT / cfg["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"split manifest -> {out.relative_to(ROOT)}")
    print(f"  golden {len(selected_sorted)} / eval {len(eval_ids)} / total {cfg['total_anchors']}")
    print(f"  depth seats: {seats}")
    print(f"  discipline coverage: {len(disc_in_sel)}/{len({r['discipline'] for r in golden})} distinct")
    print(f"  uncovered disciplines ({len(uncovered_disc)}): {uncovered_disc}")
    print(f"  uncovered depth x discipline cells: {len(uncovered_cells)}")
    print(f"  non-golden declared: {[r['item_id'] for r in sorted(non_golden, key=lambda x: x['item_id'])]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
