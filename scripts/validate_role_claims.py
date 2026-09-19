#!/usr/bin/env python3
"""validate_role_claims.py — stop role assignments from drifting away from measurements.

WHY THIS EXISTS (2026-09-16): the consolidation drafts assigned roles by inheritance, and at least
one was asserted as measured when the repo already contained a study REFUTING it
(`governance/S4_DEPTH_EMPIRICAL_RESULTS_2026-08-14.md`: gemma-4-E4B depth 62.5% vs gpt-oss 75%,
"gemma-4-E4B is NOT accurate enough for depth", and the flag was disabled). The role map said
`depth_model: gemma-4-E4B` with no citation, and the claim got repeated in conversation as if
verified. Prose does not prevent that. A validator does.

RULE (proposed as a governance rule): every model role must carry an `evidence:` field naming the
artifact, the date and the sample size, e.g.
    evidence: "governance/voting_verdict_20260916.md 2026-09-16 n=251"
    evidence: "governance/S4_DEPTH_EMPIRICAL_RESULTS_2026-08-14.md 2026-08-14 n=8 (REFUTED)"
A role whose evidence is missing, empty, or `UNVERIFIED` is reported. Exit code 1 if any role is
unverified, so this can gate the freeze.

Usage:
  python3 scripts/validate_role_claims.py
  python3 scripts/validate_role_claims.py --file governance/consolidation_drafts_20260916/02_model_assignments.yaml.draft
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "governance" / "consolidation_drafts_20260916" / "02_model_assignments.yaml.draft"
# A citation must name a file that looks like an artifact and carry a date or a sample size.
CITATION = re.compile(r"[A-Za-z0-9_./-]+\.(md|json|jsonl|csv|log)", re.I)
SIZE = re.compile(r"n\s*=\s*\d+|\d+\s*rows|n=\d+", re.I)
DATE = re.compile(r"20\d\d-\d\d-\d\d")


def collect_roles(obj: object, path: str = "") -> list[tuple[str, dict]]:
    """Walk the YAML and return every (role_name, node) that declares a `model:`."""
    found: list[tuple[str, dict]] = []
    if isinstance(obj, dict):
        if "model" in obj:
            found.append((path.strip("/") or "(root)", obj))
        for k, v in obj.items():
            found.extend(collect_roles(v, path + "/" + str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found.extend(collect_roles(v, path + "/" + str(i)))
    return found


def main() -> int:
    """Report every role whose evidence does not cite a dated, sized measurement."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=DEFAULT)
    args = ap.parse_args()
    if not args.file.exists():
        print(f"missing file: {args.file}")
        return 1

    data = yaml.safe_load(args.file.read_text(encoding="utf-8"))
    roles = collect_roles(data)
    verified, unverified = [], []
    for name, node in roles:
        ev = str(node.get("evidence") or "").strip()
        if ev and ev.upper() != "UNVERIFIED" and CITATION.search(ev) and (SIZE.search(ev) or DATE.search(ev)):
            verified.append((name, node.get("model"), ev))
        else:
            unverified.append((name, node.get("model"), ev or "(none)"))

    print(f"ROLE CLAIM VALIDATION — {args.file.name}")
    print(f"  roles declaring a model: {len(roles)}   verified: {len(verified)}   unverified: {len(unverified)}")
    print("-" * 100)
    if unverified:
        print("  UNVERIFIED — no dated/sized artifact citation. Do not state these as measured:")
        for name, model, ev in unverified:
            print(f"    {str(name)[:34]:36s} {str(model)[:34]:36s} {ev[:40]}")
    if verified:
        print()
        print("  VERIFIED:")
        for name, model, ev in verified:
            print(f"    {str(name)[:34]:36s} {str(model)[:34]:36s} {ev[:60]}")
    print("-" * 100)
    print("VERDICT: " + ("every role is cited" if not unverified
                         else f"{len(unverified)} role(s) uncited — annotate or freeze them as UNVERIFIED"))
    return 1 if unverified else 0


if __name__ == "__main__":
    sys.exit(main())
