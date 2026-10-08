#!/usr/bin/env python3
"""project_ruler_to_rederived_v8.py — project the frozen RULER onto the rederived_v8 authority (BUG-682 Stage 2).

WHY (closes BUG-682's second face). The rederived_v8 lineage
(`governance/discipline_anchor_rederived_v8_20261007.json`, 201 rows) is the declared
authority_of_record for the discipline/domain/primary_domain axis (config/anchor_family.yaml +
config/anchor_axis_authority.yaml). It is STALE: it pre-dates the owner's round-3/round-4 rulings
(R091 = systems thinking; 14 noise_drop; 7 discipline abstentions) and still carries the 'emerging'
token as an abstention placeholder. The frozen RULER (`governance/DOMAIN_RULER_FROZEN_20261008.json`,
194 rows) is the owner-derived truth. This script projects the ruler's three axis columns onto the
rederived_v8 rows:
    axis-bearing  -> discipline/domains/domain/primary_domain from the ruler; abstentions discipline=''
                     + source 'abstained'
    declared drop -> axis cleared + source 'noise_drop' (D-2813: depth/discipline do NOT apply)
    missing row   -> R091 (axis-bearing) is ADDED so the authority is complete (194 ruler rows present)
Deterministic, LLM-free; crash-safe write (C6). ONE derivation, ONE home (D-2646/D-2649).
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
RULER = ROOT / "governance" / "DOMAIN_RULER_FROZEN_20261008.json"
RULINGS = ROOT / "config" / "owner_domain_rulings_20261008.yaml"
REDERIVED = ROOT / "governance" / "discipline_anchor_rederived_v8_20261007.json"


def _load_cfg() -> tuple[set[str], set[str]]:
    cfg = yaml.safe_load(RULINGS.read_text(encoding="utf-8"))
    drops = {str(i) for i in (cfg.get("noise_drop_excluded") or [])}
    abstained = {str(i) for i in (cfg.get("discipline_abstention") or [])}
    return drops, abstained


def main() -> int:
    drops, abstained = _load_cfg()
    ruler_rows = json.loads(RULER.read_text(encoding="utf-8"))["rows"]
    ruler_by_id = {r["item_id"]: r for r in ruler_rows}
    red = json.loads(REDERIVED.read_text(encoding="utf-8"))
    red_rows = red["rows"]
    red_by_id = {str(r["item_id"]): r for r in red_rows}

    menu_hash = red.get("menu_hash")
    answer_hash = red.get("answer_space_hash")

    out_rows: list[dict] = []
    for r in red_rows:
        iid = str(r["item_id"])
        if iid in ruler_by_id:
            ru = ruler_by_id[iid]
            discipline = ru["discipline"]
            domains = list(ru["domains"])
            r["discipline"] = discipline
            r["domains"] = domains
            r["domain"] = "|".join(domains)
            r["primary_domain"] = ru["primary_domain"]
            if iid in abstained:
                r["discipline_source"] = "abstained"
                r["domain_source"] = "owner_finalized"
                r.setdefault("_stamp", {})["discipline_abstained"] = True
                r.setdefault("_stamp", {})["domains_abstained"] = False
            else:
                r["discipline_source"] = "owner_finalized"
                r["domain_source"] = "owner_finalized"
                r.setdefault("_stamp", {})["discipline_abstained"] = False
                r.setdefault("_stamp", {})["domains_abstained"] = False
            out_rows.append(r)
        elif iid in drops:
            r["discipline"] = None
            r["domains"] = []
            r["domain"] = None
            r["primary_domain"] = None
            r["discipline_source"] = "noise_drop"
            r["domain_source"] = "noise_drop"
            r.setdefault("_stamp", {})["discipline_abstained"] = True
            r.setdefault("_stamp", {})["domains_abstained"] = True
            out_rows.append(r)
        else:
            print("FAIL-CLOSED: rederived_v8 row " + iid + " is NEITHER axis-bearing NOR a declared noise_drop")
            return 1

    # Add ruler rows missing from rederived_v8 (R091): the authority must cover all 194 ruler rows.
    added: list[str] = []
    for iid, ru in ruler_by_id.items():
        if iid not in red_by_id:
            domains = list(ru["domains"])
            out_rows.append({
                "item_id": ru["item_id"],
                "name": ru["name"],
                "discipline": ru["discipline"],
                "domains": domains,
                "discipline_source": "owner_finalized",
                "domain_source": "owner_finalized",
                "_stamp": {
                    "anchor_version": "v8",
                    "menu_hash": menu_hash,
                    "answer_space_hash": answer_hash,
                    "taxonomy_version": "v8",
                    "coder": "owner",
                    "date": datetime.now(timezone.utc).isoformat(),
                    "abstention": red.get("abstention", "emerging"),
                    "discipline_abstained": iid in abstained,
                    "domains_abstained": False,
                    "second_coder": "gemma-4-E4B-it-MLX-4bit",
                },
                "_crosscheck": {"note": "projected from the frozen ruler (BUG-682 Stage 2); no re-adjudication"},
                "domain": "|".join(domains),
                "primary_domain": ru["primary_domain"],
            })
            added.append(iid)

    # Preserve original row order for the pre-existing rows; append added rows at the end.
    # (reinstated R091 has no sheet cell, so it has no natural sheet position to preserve.)
    out_rows.sort(key=lambda r: str(r["item_id"]))

    n_drop = sum(1 for r in out_rows if r.get("discipline_source") == "noise_drop")
    n_abst = sum(1 for r in out_rows if r.get("discipline_source") == "abstained")
    n_axis = sum(1 for r in out_rows if r.get("discipline") not in (None, ""))

    red["rows"] = out_rows
    red["total"] = len(out_rows)
    red["axes_rederived"] = ["discipline", "domains"]
    red["_provenance"] = {
        "schema_version": "1.0",
        "generated_by": "scripts/project_ruler_to_rederived_v8.py (BUG-682 Stage 2)",
        "gen_model": "none (deterministic projection from the frozen ruler, LLM-free)",
        "decision": "D-2867",
        "date": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "ruler": str(RULER.relative_to(ROOT)),
            "rulings": str(RULINGS.relative_to(ROOT)),
        },
        "note": ("axis columns projected from the owner-derived RULER: drops cleared + stamped noise_drop, "
                 "abstentions discipline='' + source abstained, R091 added; depth axis untouched (D-2820)"),
    }

    if "--check" in sys.argv:
        print(f"CHECK: {len(out_rows)} rows ({n_axis} axis-bearing, {n_abst} abstained, {n_drop} noise_drop, "
              f"added {added})")
        ok = len(out_rows) == len(red_by_id) + len(added) and added == ["R091"]
        print("CHECK " + ("PASS" if ok else "FAIL"))
        return 0 if ok else 1

    fd, tmp = tempfile.mkstemp(dir=REDERIVED.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(red, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, REDERIVED)
    print(f"wrote {REDERIVED.relative_to(ROOT)}: {len(out_rows)} rows ({n_axis} axis, {n_abst} abstained, "
          f"{n_drop} noise_drop, added {added})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
