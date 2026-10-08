#!/usr/bin/env python3
"""regenerate_anchor_208_v8.py — regenerate ANCHOR_208_CONSOLIDATED from the OWNER-DERIVED RULER (D-2867, BUG-684 fixed).

WHY (closes BUG-684, the mechanism behind BUG-679). This script used to carry the drop set as
PYTHON LITERALS (`NOISE_DROP = {R021,R084,R106,R148}`, `EMERGING = {R040,R080,R091}`) and re-populate
the pipeline-facing face from the STALE authority `discipline_anchor_rederived_v8_20261007.json` for
every row it did not name. That is TWO homes for one fact: the owner's ratified DROP(13) + R040 could
never reach the face the pipeline reads (the BUG-682 cross-face error-leak class).

FIX: the drop / abstention sets are read from the owner-ruling config (C12/C12c — every ruling is DATA,
never code), and the discipline / domain / primary_domain axis is projected from the OWNER-DERIVED RULER
(`governance/DOMAIN_RULER_FROZEN_20261008.json`, 194 rows, sha256-pinned) — the ONE derivation
(D-2879/BUG-682 anti-REVERT limb; `build_domain_ruler.py` is retired as a writer).

Join:
    depth axis            <- ANCHOR_208_DEPTH_CORRECTED_20261002.json (208 rows; depth is NOT menu-derived, D-2820)
    discipline + domain   <- DOMAIN_RULER_FROZEN_20261008.json (194 axis-bearing rows; R091 carries systems thinking)

Every anchor row is EXACTLY one of: axis-bearing (in the ruler), or a declared noise_drop (in the
config#noise_drop_excluded set). A declared drop carries no axis value (D-2813: for a noise_drop row
depth and discipline do NOT apply); a discipline abstention carries discipline='' (BUG-676: an ABSENCE,
never the 'emerging' token). Deterministic, LLM-free; crash-safe write (C6).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEPTH = ROOT / "governance" / "ANCHOR_208_DEPTH_CORRECTED_20261002.json"
RULER = ROOT / "governance" / "DOMAIN_RULER_FROZEN_20261008.json"
RULINGS = ROOT / "config" / "owner_domain_rulings_20261008.yaml"
OUT = ROOT / "governance" / "ANCHOR_208_CONSOLIDATED_20261007.json"

DEPTH_GOLDEN_SOURCES = {"canonical_adjudicated", "owner_finalized"}


def _norm_name(s: str) -> str:
    return s.replace("\xa0", " ").strip()


def _load_cfg() -> dict:
    cfg = yaml.safe_load(RULINGS.read_text(encoding="utf-8"))
    drops = [str(i) for i in (cfg.get("noise_drop_excluded") or [])]
    abstained = {str(i) for i in (cfg.get("discipline_abstention") or [])}
    return {"drops": drops, "drop_set": set(drops), "abstained": abstained}


def main() -> int:
    cfg = _load_cfg()
    depth_rows = json.loads(DEPTH.read_text(encoding="utf-8"))
    ruler_rows = json.loads(RULER.read_text(encoding="utf-8"))["rows"]
    ruler_by_id = {r["item_id"]: r for r in ruler_rows}

    out_rows: list[dict] = []
    for d in depth_rows:
        iid = d["item_id"]
        r = ruler_by_id.get(iid)

        if r is not None:
            discipline = r["discipline"]
            domains = r["domains"]
            domain = "|".join(domains)
            primary = domains[0] if domains else None
            dstatus = "abstained" if iid in cfg["abstained"] else "owner_finalized"
            dsource = "abstained" if iid in cfg["abstained"] else "owner_finalized"
        elif iid in cfg["drop_set"]:
            discipline, domains, domain, primary = None, [], None, None
            dstatus, dsource = "noise_drop", "noise_drop"
        else:
            # Partition invariant (BUG-679): an anchor row is axis-bearing OR a declared drop, never neither.
            print("FAIL-CLOSED: anchor row " + iid + " is NEITHER in the ruler NOR a declared noise_drop")
            return 1

        is_emerging = discipline == "emerging"
        is_noise = discipline is None or d["depth_label"] == "noise_drop" or "noise_drop" in str(d.get("depth_source", ""))
        is_abstained = iid in cfg["abstained"]
        out_rows.append({
            "item_id": iid,
            "name": _norm_name(d["name"]),
            "depth": d["depth"],
            "depth_label": d["depth_label"],
            "depth_source": d["depth_source"],
            "depth_golden_eligible": d["depth_source"] in DEPTH_GOLDEN_SOURCES,
            "discipline": discipline,
            "discipline_status": dstatus,
            "discipline_source": dsource,
            "discipline_golden_eligible": (not is_emerging) and (not is_noise) and (not is_abstained),
            "golden_eligible": (not is_emerging) and (not is_noise) and (not is_abstained),
            "domain": domain,
            "primary_domain": primary,
        })

    artifact = {
        "_provenance": {
            "schema_version": "1.0",
            "gen_model": "none",
            "generated_by": "scripts/regenerate_anchor_208_v8.py (D-2867, BUG-684 fixed)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "depth": str(DEPTH.relative_to(ROOT)),
                "ruler": str(RULER.relative_to(ROOT)),
                "rulings": str(RULINGS.relative_to(ROOT)),
            },
        },
        "rows": out_rows,
    }

    n_with_domains = sum(1 for r in out_rows if r["domain"])
    n_golden = sum(1 for r in out_rows if r["golden_eligible"])
    n_drop = sum(1 for r in out_rows if r["discipline_status"] == "noise_drop")
    stale = [r["item_id"] for r in out_rows
             if r["domain"] and any(x in (r["domain"] or "").split("|") for x in ("social sciences", "science & research", "research & methodology"))]

    if "--check" in sys.argv:
        print(f"CHECK: {len(out_rows)} rows (depth={len(depth_rows)}, ruler={len(ruler_rows)}), "
              f"{n_with_domains} with v8 domain, {n_golden} golden_eligible, {n_drop} noise_drop")
        print(f"CHECK: stale domains in output = {stale}")
        ok = len(out_rows) == len(depth_rows) and not stale
        print("CHECK " + ("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    fd, tmp = tempfile.mkstemp(dir=OUT.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, OUT)

    print(f"wrote {OUT.relative_to(ROOT)}: {len(out_rows)} rows, "
          f"{n_with_domains} with v8 domain, {n_golden} golden_eligible, {n_drop} noise_drop, stale={stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
