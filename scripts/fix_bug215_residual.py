#!/usr/bin/env python3
"""scripts/fix_bug215_residual.py — repair the 66-FB BUG-215 residual + stale provenance flag.

PROBLEM (verified against the live DB at commit 7350507):
  66 FBs carry `discipline != 'emerging'` BUT an empty `discipline_raw` AND
  `taxonomy_match_method = 'emerging_real'`. That combination is self-contradictory:
  `emerging_real` means "real-but-unmapped raw label → discipline forced to 'emerging'",
  yet the discipline is canonical and the raw label was discarded. Two defects:

  1. Empty `discipline_raw` — re-introduces the BUG-215 regression (non-emerging FBs
     must retain raw-label provenance).
  2. Stale `taxonomy_match_method='emerging_real'` — claims "emerging" when the
     discipline is canonical.

The 66 split into two populations (verified against backups, mtime-sorted):

  * 24 VERIFIED — raw label resolves to the assigned discipline via the current
    alias index (Information Systems / Health Informatics → `information science`).
    Fix: restore raw + method='alias' (discipline unchanged).

  * 42 UNVERIFIED — the recovered raw label does NOT resolve to the assigned
    discipline (e.g. "Applied Mathematics"→"theoretical physics", "Marketing"→
    "finance", "music education"→"psychology", plus a large over-assignment to the
    `information science` catch-all). The promotion was not index-backed.
    Fix (honest, per D2399 "do not bulk-promote; leave as emerging"): restore raw,
    revert `discipline='emerging'`, method='emerging_real' — an honest open-world
    state, not a failure state.

Read-only by default (dry-run). `--apply` = C13 backup + integrity gate + atomic
write + idempotent recount (mirrors reclassify_merged_axis.py).

Run:
    python3 scripts/fix_bug215_residual.py            # dry-run
    python3 scripts/fix_bug215_residual.py --apply    # backup + atomic write
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import match_to_canonical  # noqa: E402

# C20: named constant — empty raw representations the DB currently uses.
_EMPTY_RAW = frozenset({"", "[]"})

# C20: the promotion method recorded when a raw label maps to canonical via the
# alias index (consistent with scripts/apply_bug150_aliases.py, which preserves raw).
_METHOD_ALIAS = "alias"
# C20: the honest method for "real-but-unmapped raw label → discipline='emerging'".
_METHOD_EMERGING_REAL = "emerging_real"


def _empty(v: str | None) -> bool:
    """True if a raw-label column value is empty in any known representation."""
    return v is None or v.strip() == "" or v.strip() == "[]"


# C20: filename timestamp pattern (YYYYMMDD[_[H]HMMSS]) — the reliable creation time.
_BACKUP_TS_RE = re.compile(r"(\d{8})(?:_(\d{6}))?")


def _backup_key(path: Path) -> tuple[int, int]:
    """Extract (date, time) from the backup filename as a sortable key.

    Filename timestamps (not mtime) are the true chronological order — `shutil.copy2`
    preserves the *source* mtime, so mtime is unreliable for ordering backups.
    """
    m = _BACKUP_TS_RE.search(path.name)
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)


def _iter_backups(db_path: Path) -> list[Path]:
    """Return backup DBs in true chronological order (filename timestamp)."""
    pattern = str(db_path) + ".bak_*"
    return sorted((Path(p) for p in glob.glob(pattern)), key=_backup_key)


def _recover_raw(db_path: Path, fb_ids: list[str]) -> dict[str, str]:
    """Recover each FB's last non-empty raw label from the backup chain.

    Walks backups oldest→newest (mtime) and keeps the most recent non-empty
    `discipline_raw`. Fails loudly (C16) if any FB has no recoverable raw label.
    """
    recovered: dict[str, str] = {}
    seen: set[str] = set()
    qmarks = ",".join("?" * len(fb_ids))
    for bak in _iter_backups(db_path):
        conn = sqlite3.connect(str(bak))
        try:
            conn.row_factory = sqlite3.Row
            # Query the FULL id list every iteration (placeholder count constant).
            rows = conn.execute(
                f"SELECT fb_id, discipline_raw FROM fbs WHERE fb_id IN ({qmarks})",
                fb_ids,
            ).fetchall()
        finally:
            conn.close()
        # Overwrite on every non-empty hit → the newest (chronologically last)
        # non-empty raw wins, which is the provenance that was actually cleared.
        for r in rows:
            raw = r["discipline_raw"]
            if not _empty(raw):
                recovered[r["fb_id"]] = raw
                seen.add(r["fb_id"])
    missing = set(fb_ids) - seen
    if missing:
        raise RuntimeError(
            f"Cannot recover raw label for {len(missing)} FB(s) from backups: "
            f"{sorted(missing)[:5]!r} … — aborting (fail-closed, C16)."
        )
    return recovered


def _classify(fb_id: str, raw: str, discipline: str) -> tuple[str, str, str]:
    """Re-derive the honest (discipline, raw, method) for one FB.

    Returns (new_discipline, new_raw, new_method).
    """
    mapped = match_to_canonical(raw, "discipline")
    if mapped == discipline:
        # The current index backs the assignment → keep discipline, mark 'alias'.
        return discipline, raw, _METHOD_ALIAS
    # Raw label is unmapped (or maps elsewhere) → the promotion was not index-backed.
    # Revert to an honest open-world state rather than bless an unverified label.
    return "emerging", raw, _METHOD_EMERGING_REAL


def _backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_bug215_residual")
    shutil.copy2(str(db_path), str(bak))
    with open(bak, "rb") as f:
        os.fsync(f.fileno())
    if db_path.stat().st_size != bak.stat().st_size:
        raise RuntimeError("backup size mismatch — aborting write (C13)")
    print(f"  🔒 Backup: {bak} ({bak.stat().st_size:,} bytes)")
    return bak


def _integrity_gate(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if qc != "ok":
        raise RuntimeError(f"integrity gate FAILED (quick_check={qc})")
    if fk:
        raise RuntimeError(f"integrity gate FAILED ({len(fk)} FK violations)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write (default = dry-run).")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT fb_id, name, discipline, discipline_raw FROM fbs "
            "WHERE discipline != 'emerging' AND "
            "taxonomy_match_method = 'emerging_real' AND "
            "(discipline_raw IS NULL OR discipline_raw = '' OR discipline_raw = '[]')"
        ).fetchall()
    finally:
        conn.close()

    fb_ids = [r["fb_id"] for r in rows]
    if not fb_ids:
        print("No residual FBs found — nothing to do.")
        return 0

    recovered = _recover_raw(args.db, fb_ids)

    updates: list[dict] = []
    n_verified = 0
    n_reverted = 0
    for r in rows:
        raw = recovered[r["fb_id"]]
        new_disc, new_raw, new_method = _classify(r["fb_id"], raw, r["discipline"])
        if new_disc == r["discipline"] and new_method == _METHOD_ALIAS:
            n_verified += 1
        else:
            n_reverted += 1
        updates.append({
            "fb_id": r["fb_id"],
            "name": r["name"],
            "discipline": new_disc,
            "discipline_raw": new_raw,
            "taxonomy_match_method": new_method,
        })

    print(
        f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} FB(s) "
        f"({n_verified} verified restore, {n_reverted} reverted to emerging)\n"
    )
    for u in updates:
        flag = "ALIAS" if u["taxonomy_match_method"] == _METHOD_ALIAS else "REVERT"
        print(
            f"  [{flag:6s}] {u['name'][:42]:42s} disc={u['discipline']:22s} "
            f"raw={u['discipline_raw']!r}"
        )

    if not args.apply:
        print("\n(dry-run — no write. Re-run with --apply.)")
        return 0

    _backup_db(args.db)
    _integrity_gate(args.db)

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute(
                "UPDATE fbs SET discipline=?, discipline_raw=?, taxonomy_match_method=? "
                "WHERE fb_id=?",
                (u["discipline"], u["discipline_raw"], u["taxonomy_match_method"], u["fb_id"]),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    try:
        from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
        reconcile_canonical_status(conn)
        update_counts_from_fbs(conn)
    finally:
        conn.close()

    print(f"\n✅ committed {len(updates)} FB provenance repair(s) atomically.")
    print(f"   verified (alias restore): {n_verified}")
    print(f"   reverted to emerging (honest gap): {n_reverted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
