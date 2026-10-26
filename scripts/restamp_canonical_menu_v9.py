#!/usr/bin/env python3
"""scripts/restamp_canonical_menu_v9.py — D-2907: deterministic menu_hash re-stamp (D-2894, owner-approved).

WHY (root cause, not symptom). The canonical run rechunk-v4-20260929 (6591 rows) was classified under
taxonomy v5.6 (menu_hash 99e1df82...). The v9 menu edits (D-2897) touched exactly FIVE labels
(computational theory -> emerging, information retrieval -> information science, visual semiotics ->
semiotics, creative writing + museum studies -> Heterodox promotion) — those 97 rows were already
re-stamped to the live v9 menu by scripts/reclass_v9.py. The remaining 6494 rows carry disciplines whose
v9 definitions are IDENTICAL to their v5.6 definitions, so their label assignments are UNCHANGED across
the menu edit. Forensic audit (D-2905) confirmed they are already v9-clean on the discipline axis
(computational theory 0 / information retrieval 0 / visual semiotics 0) and every one of their 59 distinct
disciplines is a member of the live v9 menu.

This script therefore performs a PROVENANCE REFRESH, not a re-classification: it re-stamps the stale
6494 rows' menu_hash + taxonomy_version to the live v9 identity, WITHOUT touching discipline/domains
(or any raw field). This makes scripts/check_menu_reclass_gate.py report GREEN, unblocking the serving
layer's trust in the canonical run.

FAIL-CLOSED assertions (before any write):
  G1: the stale cohort (menu_hash = pre-v9 hash, taxonomy_version = v5.6) is EXACTLY 6494 rows.
  G2: ZERO pre-v9 leftover disciplines (computational theory / information retrieval / visual semiotics)
      in that cohort — a re-stamp over non-v9-clean labels would be a whitewash, not a refresh.
  G3: every distinct discipline in the cohort is a member of the LIVE v9 menu.
  G4: no row with a non-empty menu_hash outside the known two stamps exists (no hidden third cohort).

Crash-safe (C6/C13): DB backup + integrity gate (quick_check + foreign_key_check) before AND after the
write, in a single atomic transaction. Deterministic + LLM-free (C12: menu identity derived from
pipeline.closed_menu.menu_hash() and config/version.yaml, never hardcoded).

Run:
    python3 scripts/restamp_canonical_menu_v9.py            # dry-run (assertions + plan only)
    python3 scripts/restamp_canonical_menu_v9.py --apply    # backup + integrity gate + atomic write
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.closed_menu import menu_hash, render_closed_menu  # noqa: E402
from pipeline.pipeline_paths import CANONICAL_RUN, DB_PATH  # noqa: E402

CANONICAL_RUN_ID = CANONICAL_RUN  # D-2881 single source of truth (config/anchor_family.yaml store_bridge.canonical_run)
# Pre-v9 leftover labels (D-2897): any of these in the stale cohort means re-stamping would whitewash.
_PRE_V9_LEFTOVERS = ("computational theory", "information retrieval", "visual semiotics")


def _live_identity() -> tuple[str, str]:
    """Return (live_menu_hash, live_taxonomy_version) from the declared config homes (C12)."""
    import yaml

    live_hash = menu_hash()
    ver_doc = yaml.safe_load((_ROOT / "config" / "version.yaml").read_text(encoding="utf-8")) or {}
    live_tax = str(ver_doc.get("taxonomy_version"))
    if not live_hash or not live_tax:
        raise SystemExit("FAIL-CLOSED: could not derive live menu identity (menu_hash/taxonomy_version)")
    return live_hash, live_tax


def _stale_hash() -> str:
    """Return the pre-v9 menu_hash present on the canonical run's stale cohort (derived, never hardcoded)."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            "SELECT DISTINCT menu_hash FROM fbs WHERE pipeline_run_id=? AND menu_hash IS NOT NULL "
            "AND menu_hash != ''",
            (CANONICAL_RUN_ID,),
        ).fetchall()
    finally:
        conn.close()
    hashes = {r[0] for r in rows}
    if len(hashes) > 2:
        raise SystemExit(f"FAIL-CLOSED (G4): expected <=2 distinct menu_hash on canonical run, found {len(hashes)}: {hashes}")
    live, _ = _live_identity()
    stale = [h for h in hashes if h != live]
    if len(stale) != 1:
        raise SystemExit(f"FAIL-CLOSED (G4): expected exactly 1 stale menu_hash, found {len(stale)}")
    return stale[0]


def _stale_tax(stale_hash: str) -> str:
    """Return the taxonomy_version stamped alongside the stale menu_hash (derived, never hardcoded)."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            "SELECT DISTINCT taxonomy_version FROM fbs WHERE pipeline_run_id=? AND menu_hash=?",
            (CANONICAL_RUN_ID, stale_hash),
        ).fetchall()
    finally:
        conn.close()
    taxes = {r[0] for r in rows if r[0]}
    if len(taxes) != 1:
        raise SystemExit(f"FAIL-CLOSED: expected exactly 1 stale taxonomy_version, found {len(taxes)}: {taxes}")
    return taxes.pop()


def _backup_db(db_path: Path) -> Path:
    """C13: copy the DB to a timestamped backup and fsync it; verify byte size."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_restamp_v9")
    shutil.copy2(str(db_path), str(bak))
    with open(bak, "rb") as f:
        os.fsync(f.fileno())
    if db_path.stat().st_size != bak.stat().st_size:
        raise RuntimeError("backup size mismatch — aborting write")
    return bak


def _integrity_gate(db_path: Path, label: str) -> None:
    """C16: quick_check + foreign_key_check; raise loudly on any violation."""
    conn = sqlite3.connect(str(db_path))
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if qc != "ok":
        raise RuntimeError(f"{label} integrity gate FAILED (quick_check={qc})")
    if fk:
        raise RuntimeError(f"{label} integrity gate FAILED ({len(fk)} FK violations)")


def _assertions(conn: sqlite3.Connection, stale_hash: str, live_hash: str, live_tax: str, stale_tax: str) -> int:
    """Run G1-G4 fail-closed assertions and return the stale-cohort row count."""
    # G1: exact stale-cohort size
    n_stale = conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id=? AND menu_hash=? AND taxonomy_version=?",
        (CANONICAL_RUN_ID, stale_hash, stale_tax),
    ).fetchone()[0]
    if n_stale != 6494:
        raise SystemExit(
            f"FAIL-CLOSED (G1): expected 6494 stale rows, found {n_stale}. "
            "The canonical-run provenance changed since D-2905; re-audit before re-stamping."
        )

    # G2: zero pre-v9 leftover disciplines in the stale cohort
    leftover_hits = conn.execute(
        "SELECT discipline, COUNT(*) FROM fbs WHERE pipeline_run_id=? AND menu_hash=? "
        "AND discipline IN (?, ?, ?) GROUP BY discipline",
        (CANONICAL_RUN_ID, stale_hash, *_PRE_V9_LEFTOVERS),
    ).fetchall()
    if leftover_hits:
        raise SystemExit(
            f"FAIL-CLOSED (G2): pre-v9 leftover discipline(s) still in the stale cohort: {leftover_hits}. "
            "Re-stamping would whitewash non-v9-clean labels. Re-run RATIFY-2 re-classification first."
        )

    # G3: every distinct discipline in the cohort is a member of the live v9 menu
    live_disciplines = {d["value"] for d in render_closed_menu()["disciplines"]}
    cohort_disciplines = conn.execute(
        "SELECT DISTINCT discipline FROM fbs WHERE pipeline_run_id=? AND menu_hash=?",
        (CANONICAL_RUN_ID, stale_hash),
    ).fetchall()
    invalid = [r[0] for r in cohort_disciplines if r[0] not in live_disciplines and r[0] != "emerging"]
    if invalid:
        raise SystemExit(
            f"FAIL-CLOSED (G3): {len(invalid)} discipline(s) in the stale cohort are NOT in the live v9 menu: {invalid}"
        )

    # G4: no third menu_hash cohort (already enforced in _stale_hash, but assert here for the fresh-cohort side)
    fresh = conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id=? AND menu_hash=?",
        (CANONICAL_RUN_ID, live_hash),
    ).fetchone()[0]
    total = conn.execute(
        "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id=?", (CANONICAL_RUN_ID,)
    ).fetchone()[0]
    if fresh + n_stale != total:
        raise SystemExit(
            f"FAIL-CLOSED (G4): fresh({fresh}) + stale({n_stale}) != total({total}); a hidden cohort exists."
        )

    return n_stale


def main(argv: list[str]) -> int:
    """Dry-run by default; --apply performs backup + integrity gate + atomic re-stamp."""
    apply = "--apply" in argv
    live_hash, live_tax = _live_identity()
    stale_hash = _stale_hash()
    stale_tax = _stale_tax(stale_hash)

    print(f"live menu_hash : {live_hash}")
    print(f"live taxonomy  : {live_tax}")
    print(f"stale menu_hash: {stale_hash}")
    print(f"canonical run  : {CANONICAL_RUN_ID}")
    print("-" * 78)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        n_stale = _assertions(conn, stale_hash, live_hash, live_tax, stale_tax)
        print(f"G1-G4 PASS: {n_stale} stale rows are v9-clean and safe to re-stamp.")
        print(f"  plan: UPDATE fbs SET menu_hash={live_hash[:16]}..., taxonomy_version={live_tax!r} "
              f"WHERE pipeline_run_id={CANONICAL_RUN_ID!r} AND menu_hash={stale_hash[:16]}...")

        if not apply:
            print("\n(dry-run — no write. Re-run with --apply to commit.)")
            return 0

        _integrity_gate(DB_PATH, "pre-write")
        bak = _backup_db(DB_PATH)
        print(f"  backup: {bak.name}")

        cur = conn.cursor()
        cur.execute(
            "UPDATE fbs SET menu_hash=?, taxonomy_version=? WHERE pipeline_run_id=? AND menu_hash=?",
            (live_hash, live_tax, CANONICAL_RUN_ID, stale_hash),
        )
        updated = cur.rowcount
        conn.commit()
        print(f"  updated: {updated} rows")

        # post-write verify: no stale cohort remains, all rows carry the live identity
        remaining = conn.execute(
            "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id=? AND menu_hash=?",
            (CANONICAL_RUN_ID, stale_hash),
        ).fetchone()[0]
        if remaining != 0:
            raise RuntimeError(f"post-write: {remaining} stale rows remain (atomic txn should have prevented this)")
        print("  post-write: 0 stale rows remain; canonical run now v9-stamped.")
    finally:
        conn.close()

    _integrity_gate(DB_PATH, "post-write")
    print("  ✅ post-write integrity gate clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
