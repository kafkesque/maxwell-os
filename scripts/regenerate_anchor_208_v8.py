#!/usr/bin/env python3
"""regenerate_anchor_208_v8.py — regenerate ANCHOR_208_CONSOLIDATED from rederived_v8 (D-2867).

WHY (closes the authority orphan). The legacy ANCHOR_208_CONSOLIDATED_20261002.json (208 rows)
carries pre-v8 domains ('social sciences'/'science & research') and 86 discipline disagreements
vs the owner-finalized rederived lineage. discipline_anchor_rederived_v8_20261007.json (201 rows,
D-2844/D-2864/D-2866) is the correct discipline+domain authority. This script re-joins:

    depth axis      <- ANCHOR_208_DEPTH_CORRECTED_20261002.json (208 rows; depth is NOT menu-derived, D-2820)
    discipline+domain <- discipline_anchor_rederived_v8_20261007.json (201 rows)

The 7 rows present in depth but dropped from rederived (D-2844) are carried with their drop
disposition — NEVER a stale v8 domain:
    R021                    -> noise_drop   (discipline=None, domain=None)
    R040 / R080 / R091      -> emerging     (discipline='emerging', domain=None)
    R084 / R106 / R148      -> noise_drop   (discipline=None, domain=None)

Deterministic, LLM-free. `domain` is the pipe-joined string (legacy schema), `primary_domain`
is the first domain (matches the legacy "first pipe token" invariant, measured 0 drift).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPTH = ROOT / "governance" / "ANCHOR_208_DEPTH_CORRECTED_20261002.json"
REDERIVED = ROOT / "governance" / "discipline_anchor_rederived_v8_20261007.json"
OUT = ROOT / "governance" / "ANCHOR_208_CONSOLIDATED_20261007.json"

DEPTH_GOLDEN_SOURCES = {"canonical_adjudicated", "owner_finalized"}
NOISE_DROP = {"R021", "R084", "R106", "R148"}       # D-2844 noise rows
EMERGING = {"R040", "R080", "R091"}                 # emerging-discipline rows (dropped from rederive)


def _norm_name(s: str) -> str:
    return s.replace("\xa0", " ").strip()


def main() -> int:
    depth_rows = json.loads(DEPTH.read_text(encoding="utf-8"))
    red_rows = json.loads(REDERIVED.read_text(encoding="utf-8"))["rows"]
    red_by_id = {r["item_id"]: r for r in red_rows}

    out_rows: list[dict] = []
    for d in depth_rows:
        iid = d["item_id"]
        is_noise_depth = d["depth_label"] == "noise_drop" or "noise_drop" in str(d.get("depth_source", ""))
        r = red_by_id.get(iid)

        if r is not None:
            discipline = r["discipline"]
            domains = r["domains"]
            dstatus = r.get("discipline_source") or "owner_finalized"
            dsource = dstatus
            domain = "|".join(domains)
            primary = domains[0] if domains else None
        elif iid in EMERGING:
            discipline, domains = "emerging", []
            dstatus, dsource, domain, primary = "owner_finalized", "owner_finalized", None, None
        else:  # noise_drop (R021 / R084 / R106 / R148)
            discipline, domains = None, []
            dstatus, dsource, domain, primary = "noise_drop", "noise_drop", None, None

        is_emerging = discipline == "emerging"
        is_noise = discipline is None or is_noise_depth
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
            "discipline_golden_eligible": (not is_emerging) and (not is_noise),
            "golden_eligible": (not is_emerging) and (not is_noise),
            "domain": domain,
            "primary_domain": primary,
        })

    artifact = {
        "_provenance": {
            "schema_version": "1.0",
            "gen_model": "none",
            "generated_by": "scripts/regenerate_anchor_208_v8.py (D-2867)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "depth": str(DEPTH.relative_to(ROOT)),
                "discipline_domain": str(REDERIVED.relative_to(ROOT)),
            },
        },
        "rows": out_rows,
    }

    # verification counters
    n_with_domains = sum(1 for r in out_rows if r["domain"])
    n_golden = sum(1 for r in out_rows if r["golden_eligible"])
    stale = [r["item_id"] for r in out_rows
             if r["domain"] and any(x in (r["domain"] or "").split("|") for x in ("social sciences", "science & research", "research & methodology"))]

    if "--check" in sys.argv:
        print(f"CHECK: {len(out_rows)} rows (depth={len(depth_rows)}), "
              f"{n_with_domains} with v8 domain, {n_golden} golden_eligible")
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
          f"{n_with_domains} with v8 domain, {n_golden} golden_eligible, stale={stale}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
