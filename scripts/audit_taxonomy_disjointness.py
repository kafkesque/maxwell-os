#!/usr/bin/env python3
"""audit_taxonomy_disjointness.py — enforce the discipline<->domain non-contamination rule.

WHY THIS EXISTS (D2620/BUG-197, strengthened 2026-09-17). `pipeline/schemas.py` has claimed since
D2620 that "the 61 disciplines and 43 domains are DISJOINT vocabularies" — and
`tests/test_taxonomy_disjointness.py` checked that claim by comparing **exact strings**. Both were
wrong to be satisfied: `research methodology` is a canonical DISCIPLINE while
`research & methodology` is a canonical DOMAIN — the same concept, differing only in punctuation —
and they sat together on 909 live rows while every guard reported clean. The guard validated
MEMBERSHIP, not DISJOINTNESS, and the test could not see past the `&`.

This audit checks three things and fails closed on the first two:

  1. TAXONOMY — is any canonical label present in BOTH vocabularies, compared NORMALISED
     (case + punctuation insensitive)? Every such collision must be DECLARED in
     `config/eval_integrity.yaml::label_axes` (as `shared_labels` for a documented catch-all, or as
     `known_collisions` for recorded debt). Undeclared => exit 1.
  2. RUNTIME — does any of the 7,995 KB rows carry a label that is invalid for its axis, or that
     collides across axes? Undeclared => exit 1.
  3. DEBT — declared collisions are printed with their live row counts on EVERY run, so debt can be
     seen but not silently inherited.

Exit 0 = no undeclared collision. Exit 1 = a collision that nobody has declared.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.schemas import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    _axis_contract,
    parse_domains,
    validate_discipline_domain,
)

DB = ROOT / "knowledge pipeline" / "maxwell.db"


def norm(value: object) -> str:
    """Normalise a label the same way the runtime guard does (case + punctuation insensitive)."""
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def check_taxonomy() -> list[str]:
    """Return the undeclared normalised collisions between the two vocabularies."""
    contract = _axis_contract()
    shared = {norm(x) for x in (contract.get("shared_labels") or [])}
    declared = {(norm(c.get("discipline")), norm(c.get("domain")))
                for c in (contract.get("known_collisions") or [])}
    dom_norm = {norm(d): d for d in CANONICAL_DOMAINS}
    bad: list[str] = []
    for discipline in sorted(CANONICAL_DISCIPLINES):
        key = norm(discipline)
        if key in shared or key not in dom_norm:
            continue
        if any(key == a and norm(dom_norm[key]) == b for a, b in declared):
            continue
        bad.append("discipline '" + discipline + "' collides with domain '" + dom_norm[key] + "'")
    return bad


def scan_runtime() -> tuple[int, list[str], int]:
    """Return (rows scanned, undeclared runtime flags, rows carrying declared debt)."""
    if not DB.exists():
        return 0, ["runtime DB missing: " + str(DB)], 0
    con = sqlite3.connect(str(DB))
    rows = con.execute("select fb_id, discipline, domains from fbs").fetchall()
    con.close()
    undeclared: list[str] = []
    debt = 0
    for fb_id, discipline, domains in rows:
        flags = validate_discipline_domain(discipline, parse_domains(domains))
        for flag in flags:
            if flag.startswith("declared-axis-collision"):
                debt += 1
            else:
                undeclared.append(str(fb_id)[:12] + ": " + flag)
    return len(rows), undeclared, debt


def main() -> int:
    """Run all three checks and report; exit 1 on any undeclared collision."""
    contract = _axis_contract()
    if not contract:
        print("FAIL: label_axes contract unreadable — refusing to assume a collision is allowed")
        return 1
    print("label axis contract: shared=" + str(contract.get("shared_labels"))
          + " declared_debt=" + str(len(contract.get("known_collisions") or [])))
    taxonomy_bad = check_taxonomy()
    scanned, runtime_bad, debt = scan_runtime()
    print("taxonomy: " + str(len(CANONICAL_DISCIPLINES)) + " disciplines vs "
          + str(len(CANONICAL_DOMAINS)) + " domains | normalised collisions undeclared: "
          + str(len(taxonomy_bad)))
    for item in taxonomy_bad:
        print("  UNDECLARED " + item)
    print("runtime: " + str(scanned) + " rows scanned | undeclared flags: " + str(len(runtime_bad))
          + " | rows on declared debt: " + str(debt))
    for item in runtime_bad[:10]:
        print("  UNDECLARED " + item)
    for collision in contract.get("known_collisions") or []:
        print("  KNOWN DEBT (printed every run): discipline '" + str(collision.get("discipline"))
              + "' vs domain '" + str(collision.get("domain")) + "' | rows "
              + str(collision.get("rows_discipline")) + " as discipline / "
              + str(collision.get("rows_domain")) + " as domain | decision: "
              + str(collision.get("decision") or "PENDING"))
    if taxonomy_bad or runtime_bad:
        print("DRIFT: an undeclared discipline<->domain collision exists — declare it or fix it")
        return 1
    if debt:
        print("WARN: " + str(debt) + " row(s) carry a DECLARED collision RULED 2026-09-17: two concepts; G8 adjudicates the 167 overlap rows")
    print("OK: no undeclared discipline<->domain collision in the taxonomy or the runtime KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
