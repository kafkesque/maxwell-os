#!/usr/bin/env python3
"""Materialize a frozen domain-axis ruler from the 208-row anchor authority.

The domain axis of the D-312/D-349 calibrated-abstention framework was declared
UNMEASURABLE because "no ruler truth column exists" (D-348,
governance/R2_GATE_MEASUREMENT_20260923.json `unmeasurable_axes.domains`). The
208-row consolidated anchor authority (ANCHOR_208_CONSOLIDATED_20261007.json)
DOES carry owner-finalized domain truth (`domain` multi-label + `primary_domain`).
This script freezes that truth into a fingerprinted ruler so a domain abstention
curve can be measured — following the same "measure, never transplant" rule as the
discipline/content_type axes (D-312 role-specificity).

Read-only: modifies neither pipeline output nor the anchor authority.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "governance" / "ANCHOR_208_CONSOLIDATED_20261007.json"
OUT = ROOT / "governance" / "DOMAIN_RULER_FROZEN_20261008.json"


def _domain_list(raw: str) -> list[str]:
    """Split a pipe-separated domain string into a de-duplicated ordered list."""
    if not raw:
        return []
    return [d for d in (x.strip() for x in raw.split("|")) if d]


def _git_head() -> str:
    """Return the current git commit short hash, or 'unknown' if unavailable."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    data = json.loads(SRC.read_text())
    rows = data["rows"]

    ruler_rows: list[dict] = []
    skipped_empty: int = 0
    for r in rows:
        dom = _domain_list(r.get("domain", ""))
        if not dom:
            skipped_empty += 1
            continue
        ruler_rows.append({
            "item_id": r["item_id"],
            "name": r["name"],
            "discipline": r.get("discipline", ""),
            "domains": dom,
            "primary_domain": (r.get("primary_domain") or "").strip(),
        })

    payload = json.dumps(ruler_rows, sort_keys=True, ensure_ascii=False)
    artifact = {
        "schema_version": 1,
        "gen_model": "none",
        "pipeline_commit": _git_head(),
        "source": SRC.name,
        "n_anchor_rows": len(rows),
        "n_ruler_rows": len(ruler_rows),
        "n_skipped_empty": skipped_empty,
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "rows": ruler_rows,
    }
    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")
    print(
        f"wrote {OUT.name}: n_ruler_rows={len(ruler_rows)} "
        f"skipped_empty={skipped_empty} sha256={artifact['sha256'][:16]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
