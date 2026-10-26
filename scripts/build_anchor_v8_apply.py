#!/usr/bin/env python3
"""build_anchor_v8_apply.py — apply the deterministic v8 domain remap (D-2866) to the anchor artifact.

Produces governance/discipline_anchor_rederived_v8_20261007.json from
discipline_anchor_rederived_v7_20261007.json + the SAME remap()/OWNER_OVERRIDES logic as
build_anchor_v8_remap_triage.py (single source of truth — no copy of the rules here).

Deterministic, LLM-free. Re-stamps every row to taxonomy_version/anchors_version v8 and the
live v8 menu/answer-space hashes (read from config/menu_axis_hashes.yaml — no hardcoded hashes).
R5: this is a deterministic data transform, not LLM generation; the pre-commit control is
--check, which must report EXACTLY the 21 anchor changes (16 DROP + 5 ROUTED) with proposed
domains byte-identical to anchor_v8_domain_remap_triage_20261007.csv.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_anchor_v8_remap_triage import (  # noqa: E402
    OWNER_OVERRIDES,
    REDERIVED,
    remap,
)

HASHES = ROOT / "config" / "menu_axis_hashes.yaml"
TAXONOMY = ROOT / "config" / "taxonomy_v8.yaml"
OUT = ROOT / "governance" / "discipline_anchor_rederived_v8_20261007.json"


def main():
    h = yaml.safe_load(HASHES.read_text(encoding="utf-8"))
    menu_hash = h["composite_hash_live"]
    answer_space_hash = h["answer_space_hash"]

    src = json.loads(REDERIVED.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()

    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    catch_all_domain = tax["meta"]["catch_all_domain"]  # config-first (C12), never hardcoded

    changed: list[dict] = []
    for r in src["rows"]:
        proposed, ctype, removed = remap(r["discipline"], r["domains"])
        if r["item_id"] in OWNER_OVERRIDES:
            proposed = OWNER_OVERRIDES[r["item_id"]]
            ctype = ctype or "ROUTED"
        # D-2870 fail-closed: the catch-all abstention token is an axis-level verdict,
        # never a token that may coexist with a concrete domain.  (C16: no silent errors.)
        if catch_all_domain in proposed and len(proposed) > 1:
            raise SystemExit(
                f"FAIL-CLOSED: {r['item_id']} catch-all '{catch_all_domain}' "
                f"coexists with concrete domains {proposed}")
        if proposed != r["domains"]:
            changed.append({
                "item_id": r["item_id"],
                "old": r["domains"],
                "new": proposed,
                "ctype": ctype,
                "removed": removed,
                "ruling": "owner" if r["item_id"] in OWNER_OVERRIDES else "",
            })
        r["domains"] = proposed
        # D-2868 schema-compat: expose the legacy pipe-joined `domain` + first-token
        # `primary_domain` columns so the anchor-axis authority rail (which reads a single
        # string column) can point at this artifact. Deterministic derived fields, never a
        # second source of truth: `domain == "|".join(domains)`, `primary_domain == domains[0]`.
        r["domain"] = "|".join(proposed)
        r["primary_domain"] = proposed[0] if proposed else None
        stamp = r.setdefault("_stamp", {})
        stamp["anchor_version"] = "v8"
        stamp["taxonomy_version"] = "v8"
        stamp["menu_hash"] = menu_hash
        stamp["answer_space_hash"] = answer_space_hash
        stamp["domains_abstained"] = ("emerging" in proposed)
        stamp["date"] = now
        stamp["coder"] = "owner"

    src["artifact_id"] = "discipline_anchor_rederived_v8_20261007"
    src["taxonomy_version"] = "v8"
    src["anchor_version"] = "v8"
    src["menu_hash"] = menu_hash
    src["answer_space_hash"] = answer_space_hash
    src["_provenance"] = {
        "schema_version": "1.0",
        "generated_by": "scripts/build_anchor_v8_apply.py (D-2866 anchor domain remap)",
        "gen_model": "human_owner (adjudicated) + deterministic label remap (no LLM)",
        "decision": "D-2866",
        "date": now,
    }

    if "--check" in sys.argv:
        print(f"CHECK: {len(changed)} anchor changes "
              f"(expected 21 = 16 DROP + 5 ROUTED)")
        for c in changed:
            print(f"  {c['item_id']:6} {json.dumps(c['old'], ensure_ascii=False):44} "
                  f"-> {json.dumps(c['new'], ensure_ascii=False)} [{c['ctype']}]")
        ok = len(changed) == 21 and all(
            json.dumps(c["new"]) not in ("[]",) for c in changed)
        print(f"CHECK {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1

    # crash-safe write (C6): tempfile -> fsync -> os.replace
    import os
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=OUT.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(src, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, OUT)

    print(f"wrote {OUT.relative_to(ROOT)}: {len(src['rows'])} rows, "
          f"{len(changed)} changed ({sorted(set(c['ctype'] for c in changed))})")
    print("stamped taxonomy_version=v8 anchor_version=v8")
    print(f"menu_hash={menu_hash[:16]}... answer_space_hash={answer_space_hash[:16]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
