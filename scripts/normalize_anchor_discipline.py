#!/usr/bin/env python3
"""Deterministic normalization of the ANCHOR-208 discipline axis.

Reads the 208-row five-axis view's `discipline` column, reconciles it against
the closed_menu_v5 discipline/domain label space, and emits a provenance-stamped
normalized artifact plus an owner review queue for the rows whose discipline
cells are NOT clean on-menu labels.

Rules (deterministic, no LLM):
  * trim whitespace  -> collapse trailing-space dupes (e.g. 'economics ' -> 'economics')
  * on-menu          -> status 'ok'
  * 'emerging'       -> status 'emerging' (on-menu catchall, under-specified)
  * off-menu but IS a domain  -> status 'domain_bleed' (owner must re-classify)
  * off-menu and not a domain -> status 'off_menu'

We NEVER silently remap an off-menu value (C12d: no invented labels); those rows
go to the owner review queue.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIEW = ROOT / "governance" / "ANCHOR_208_FIVE_AXIS_VIEW_20260930.csv"
MENU = ROOT / "config" / "closed_menu_v5.json"
OUT = ROOT / "governance" / "ANCHOR_208_DISCIPLINE_NORMALIZED_20261002.json"
REVIEW = ROOT / "governance" / "discipline_domain_bleed_review_20261002.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _pipeline_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()[:12]
    except Exception:
        return "unknown"


def load_menu() -> tuple[set[str], set[str], dict[str, str], dict[str, str]]:
    menu = json.loads(MENU.read_text())
    disc_norm: dict[str, str] = {}
    dom_norm: dict[str, str] = {}
    for x in menu["disciplines"]:
        disc_norm[x["value"].strip().lower()] = x["value"].strip()
    for x in menu["domains"]:
        dom_norm[x["value"].strip().lower()] = x["value"].strip()
    return (
        set(disc_norm),
        set(dom_norm),
        disc_norm,
        dom_norm,
    )


def classify(raw: str, disc_menu: set[str], dom_menu: set[str]) -> tuple[str, str]:
    """Return (normalized_label, status)."""
    if not raw:
        return "", "empty"
    t = raw.strip()
    tl = t.lower()
    if t != raw and tl in disc_menu:
        return t, "whitespace_fixed"
    if tl in disc_menu:
        if tl == "emerging":
            return t, "emerging"
        return t, "ok"
    if tl in dom_menu:
        return t, "domain_bleed"
    return t, "off_menu"


def main() -> int:
    disc_set, dom_set, disc_norm, dom_norm = load_menu()

    with VIEW.open(newline="") as f:
        rows = list(csv.DictReader(f))

    out_rows: list[dict] = []
    review_rows: list[dict] = []
    stats: dict[str, int] = {}

    for r in rows:
        raw = r.get("discipline", "")
        label, status = classify(raw, disc_set, dom_set)
        stats[status] = stats.get(status, 0) + 1
        rec = {
            "item_id": r.get("item_id", ""),
            "name": r.get("name", ""),
            "discipline_raw": raw,
            "discipline": label,
            "discipline_status": status,
            "domain": r.get("domain", ""),
            "primary_domain": r.get("primary_domain", ""),
            "discipline_source": (
                "anchor_adjudication" if status in ("ok", "emerging") else status
            ),
        }
        out_rows.append(rec)
        if status in ("domain_bleed", "off_menu", "emerging"):
            review_rows.append(rec)

    stamp = {
        "schema_version": "1.0",
        "gen_model": "none",
        "generated_by": "scripts/normalize_anchor_discipline.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(VIEW.relative_to(ROOT)),
        "input_sha256": _sha256(VIEW),
        "menu": str(MENU.relative_to(ROOT)),
        "pipeline_commit": _pipeline_commit(),
        "status_counts": stats,
    }
    out_rows.sort(key=lambda x: x["item_id"])
    artifact = {"_provenance": stamp, "rows": out_rows}
    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")

    review = {"_provenance": stamp, "review": review_rows}
    REVIEW.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n")

    print(f"normalized {len(out_rows)} rows -> {OUT.name}")
    print(f"status counts: {stats}")
    print(f"owner review queue ({len(review_rows)} rows) -> {REVIEW.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
