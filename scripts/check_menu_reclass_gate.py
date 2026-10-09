#!/usr/bin/env python3
"""scripts/check_menu_reclass_gate.py — BUG-693 step 4: the menu-widening re-classification gate.

WHY (root cause, not symptom). The canonical run rechunk-v4-20260929 was classified under taxonomy
v5.6 (menu_hash 99e1df82...), but the live menu is v8 (menu_hash 8218d6db...). The menu widened
(v5 -> v8: +3 Business & Management disciplines, D-2815) AFTER classification and the rows were never
re-classified — that is the whole of BUG-693: 1779 'emerging' rows that were never given a chance to
land in the widened menu. The fix is not a prompt tweak; it is a rail that makes "menu changed after
classification" IMPOSSIBLE to miss.

RAIL (read-only, fail-closed). Every FB row carries `menu_hash` + `taxonomy_version` provenance stamps
(D-279: a label must be traceable to the EXACT menu it was classified against). This gate compares those
stamps against the LIVE menu identity and reports any pipeline run whose classification is STALE. A stale
CANONICAL run is RED and exits non-zero (fail-closed): the serving layer must never read a menu that no
longer describes the classified rows.

SEVERITY MODEL:
  * fresh  — recorded menu_hash == live menu_hash  -> GREEN.
  * stale  — recorded menu_hash != live menu_hash  -> RED (a re-classification pass is MANDATORY).
  * unstamped — menu_hash is empty (pre-D-279 or non-canonical run) -> INFO (skipped; never canonical).

Config-first (C12): DB path, canonical run id, live menu identity and live taxonomy version are all
DERIVED from config, never hardcoded. Read-only: no DB or config writes (C16, BUG-491 class).

Usage:
    python3 scripts/check_menu_reclass_gate.py            # fail-closed (exit 1 if canonical run stale)
    python3 scripts/check_menu_reclass_gate.py --report   # informational (exit 0), always prints per-run
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from pipeline.closed_menu import menu_hash  # noqa: E402
from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_ANCHOR_FAMILY = ROOT / "config" / "anchor_family.yaml"
_VERSION = ROOT / "config" / "version.yaml"


def _canonical_run_id() -> str:
    """The canonical pipeline_run_id, from the ONE declared home (anchor_family.store_bridge.canonical_run)."""
    doc = yaml.safe_load(_ANCHOR_FAMILY.read_text(encoding="utf-8")) or {}
    run_id = (doc.get("store_bridge") or {}).get("canonical_run")
    if not run_id:
        raise SystemExit(f"FAIL-CLOSED: {_ANCHOR_FAMILY.relative_to(ROOT)} declares no "
                         "store_bridge.canonical_run - the gate cannot name the run it protects (C16)")
    return str(run_id)


def _live_taxonomy_version() -> str:
    """The live taxonomy version, from config/version.yaml (the same home apply_taxonomy_v8.py promotes)."""
    doc = yaml.safe_load(_VERSION.read_text(encoding="utf-8")) or {}
    ver = doc.get("taxonomy_version")
    if not ver:
        raise SystemExit(f"FAIL-CLOSED: {_VERSION.relative_to(ROOT)} declares no taxonomy_version (C16)")
    return str(ver)


def _run_identity() -> list[tuple[str, str, str, int]]:
    """Distinct (run_id, menu_hash, taxonomy_version, count) across all fbs rows."""
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT pipeline_run_id, COALESCE(menu_hash,''), COALESCE(taxonomy_version,''), COUNT(*) "
            "FROM fbs GROUP BY pipeline_run_id, menu_hash, taxonomy_version ORDER BY pipeline_run_id"
        ).fetchall()
    return [(str(r[0]), str(r[1]), str(r[2]), int(r[3])) for r in rows]


def _classify(run_id: str, recorded_hash: str, live_hash: str) -> tuple[str, str]:
    """Map one run to (verdict, reason)."""
    if not recorded_hash:
        return "INFO", "unstamped (pre-D-279 or non-canonical) - never served as canonical"
    if recorded_hash == live_hash:
        return "GREEN", "fresh - classified against the live menu"
    return "RED", f"STALE - classified under {recorded_hash[:16]}..., live is {live_hash[:16]}... " \
                  "-> re-classification pass MANDATORY"


def main(argv: list[str]) -> int:
    """Compare every run's provenance stamps against the live menu; fail-closed on a stale canonical run."""
    report_only = "--report" in argv
    live_hash: str = menu_hash()
    live_ver: str = _live_taxonomy_version()
    canonical: str = _canonical_run_id()

    print(f"live menu_hash  : {live_hash}")
    print(f"live taxonomy   : {live_ver}")
    print(f"canonical run   : {canonical}")
    print("-" * 78)

    stale_canonical = False
    for run_id, recorded_hash, recorded_ver, count in _run_identity():
        verdict, reason = _classify(run_id, recorded_hash, live_hash)
        mark = {"GREEN": "ok ", "RED": "RED", "INFO": "   "}[verdict]
        print(f"{mark} {run_id:22s} rows={count:6d} menu_hash={recorded_hash[:16] or '':16s} "
              f"tax={recorded_ver:6s} {reason}")
        if verdict == "RED" and run_id == canonical:
            stale_canonical = True

    print("-" * 78)
    if stale_canonical:
        print("FAIL-CLOSED: the canonical run is STALE vs the live menu - a menu-widening (or any menu "
              "answer-space change) has occurred since classification and the rows were never re-classified. "
              "This is the BUG-693 root cause; the re-classification pass (and, going forward, this gate) must "
              "run before the canonical run can be trusted.")
        return 1
    print("ok: the canonical run is fresh against the live menu (no menu-widening drift).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
