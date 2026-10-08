#!/usr/bin/env python3
"""apply_owner_domain_rulings_v8.py — fold the 8 owner-gated domain rulings into the
v8 domain authority (D-2874 follow-through).

WHY (closes the domain-axis "emerging" catch-all blindspot). After the D-2865/D-2866
v8 domain remap, eight 201-row authority anchors still carried `domains=["emerging"]`
(domain-axis abstention) because no applied-domain role had been owner-adjudicated.
The owner finalized those eight on 2026-10-08 (config/owner_domain_rulings_20261008.yaml).
This script applies them to the AUTHORITY (`discipline_anchor_rederived_v8_20261007.json`)
so the deterministic consumers (regenerate_anchor_208_v8.py -> build_domain_ruler.py ->
export_anchor_all_axes_csv.py) re-derive the folded truth. Consumers are NEVER hand-patched.

Deterministic, LLM-free — a data transform, not generation; R5 not implicated
(same reasoning as scripts/remint_anchor2_v8.py).

FAIL-CLOSED (C16): a ruling id missing from the authority, a row not in `["emerging"]`
state, an OOV domain, or `primary != domains[0]` all raise SystemExit — never a silent skip.
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
CONFIG = ROOT / "config" / "owner_domain_rulings_20261008.yaml"
AUTHORITY = ROOT / "governance" / "discipline_anchor_rederived_v8_20261007.json"
TAXONOMY = ROOT / "config" / "taxonomy_v8.yaml"


def _canonical_domains() -> set[str]:
    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))
    doms = tax["domains"]
    if isinstance(doms, list):
        return {d["canonical"] if isinstance(d, dict) else d for d in doms}
    return set(doms.keys())


def _crash_safe_write_json(path: Path, obj: object) -> None:
    """C6: tempfile -> fsync -> os.replace."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main() -> int:
    canon = _canonical_domains()
    rulings = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["rows"]
    src = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    rows = src["rows"]
    by_id = {r["item_id"]: r for r in rows}

    changed: list[str] = []
    for iid, rl in rulings.items():
        if iid not in by_id:
            raise SystemExit(f"FAIL-CLOSED: ruling {iid} not found in authority ({AUTHORITY.name})")
        r = by_id[iid]
        if r.get("domains") != ["emerging"]:
            raise SystemExit(
                f"FAIL-CLOSED: {iid} expected domains==['emerging'], got {r.get('domains')!r}"
            )
        primary = rl["primary"]
        domains = [str(d) for d in rl["domains"]]
        if not domains or primary != domains[0]:
            raise SystemExit(f"FAIL-CLOSED: {iid} primary {primary!r} != domains[0] {domains[0]!r}")
        oov = [d for d in domains if d not in canon]
        if oov:
            raise SystemExit(f"FAIL-CLOSED: {iid} OOV domains {oov} not in 41-domain menu")
        if len(domains) > 7:
            raise SystemExit(f"FAIL-CLOSED: {iid} exceeds multi-label cap (7): {len(domains)}")

        r["domains"] = domains
        r["domain"] = "|".join(domains)
        r["primary_domain"] = primary
        r["domain_source"] = "owner_finalized"
        stamp = r.setdefault("_stamp", {})
        stamp["abstention"] = ""
        stamp["domains_abstained"] = False
        stamp["domain_ruling"] = f"owner 2026-10-08 primary={primary}"
        stamp["date"] = datetime.now(timezone.utc).isoformat()
        changed.append(iid)
        print(f"  {iid}: ['emerging'] -> {domains} (primary={primary})")

    if len(changed) != len(rulings):
        raise SystemExit(f"FAIL-CLOSED: applied {len(changed)} but config declares {len(rulings)}")

    # assert no OTHER authority row still carries the domain-axis catch-all
    residual = [r["item_id"] for r in rows if r.get("domains") == ["emerging"]]
    if residual:
        raise SystemExit(f"FAIL-CLOSED: residual emerging-domain rows after fold: {residual}")

    if "--check" in sys.argv:
        print(f"CHECK PASS: {len(changed)} rulings validated (nothing written). "
              f"re-run without --check to apply.")
        return 0

    _crash_safe_write_json(AUTHORITY, src)
    print(f"wrote {AUTHORITY.relative_to(ROOT)}: folded {len(changed)} owner domain rulings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
