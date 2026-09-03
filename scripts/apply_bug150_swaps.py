#!/usr/bin/env python3
"""D2538: BUG-150 closed-loop canonical swaps (2 user-approved).

Promote a raw discipline to canonical, demote a low-count canonical to raw — the
D2378/D2399 closed-loop: 1-in / 1-out, the 61 canonical count stays flat.

This turn's approved swaps:
  promote 'computational theory'    ↔ demote 'agentic architecture' (2 FBs)
  promote 'computer networking'     ↔ demote 'prompt engineering'  (3 FBs)

Demote-to-raw (D2536/Q2): the demoted canonical is NOT deleted — its FBs revert to
`discipline='emerging'` with `discipline_raw=<demoted label>` preserved, so the label
remains retrievable via the raw-label surface.

Mechanics (C13 / C6):
1. Back up DB + taxonomy_v5.yaml + S4/S5 checkpoints.
2. YAML: remove the demoted canonical entries; append the promoted canonicals
   (with group + raw alias list).
3. fbs (single atomic txn):
     promote → discipline='emerging' + LOWER(discipline_raw)=LOWER(promote)
                → discipline=promote, taxonomy_match_method='exact'
     demote  → discipline=demote
                → discipline='emerging', discipline_raw=demote, taxonomy_match_method='emerging_real'
4. Integrity gate pre/post; reconcile taxonomy_counts; sync checkpoints.

Usage:
  python3 scripts/apply_bug150_swaps.py            # dry-run
  python3 scripts/apply_bug150_swaps.py --apply    # backup + integrity + write
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

SWAPS: list[dict] = [
    {
        "promote": "computational theory",
        "group": "AI & Computing",
        "raw": ["computational theory", "Computational Theory",
                "theory of computation", "Theory of Computation"],
        "demote": "agentic architecture",
    },
    {
        "promote": "computer networking",
        "group": "AI & Computing",
        "raw": ["computer networking", "Computer Networking",
                "computer networks", "Computer Networks"],
        "demote": "prompt engineering",
    },
]

TAXONOMY_PATH = _PROJECT_ROOT / "config" / "taxonomy_v5.yaml"
S4_CHECKPOINT = _PROJECT_ROOT / "knowledge pipeline" / "stage4_merge" / "t11" / "checkpoint_enriched.jsonl"
S5_CHECKPOINT = _PROJECT_ROOT / "knowledge pipeline" / "stage5_verify" / "t11" / "checkpoint.jsonl"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_file(path: Path, tag: str) -> Path:
    if not path.exists():
        print(f"  ⚠️  backup skipped (not found): {path}")
        return Path(str(path) + f".bak_{_ts()}_{tag}")
    bak = Path(str(path) + f".bak_{_ts()}_{tag}")
    shutil.copy2(str(path), str(bak))
    with open(bak, "rb") as _f:
        os.fsync(_f.fileno())
    if path.stat().st_size != bak.stat().st_size:
        raise RuntimeError(f"backup size mismatch — aborting: {path}")
    print(f"  🔒 backup: {bak} ({bak.stat().st_size:,} bytes)")
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
        raise RuntimeError(f"integrity gate FAILED ({len(fk)} foreign_key violations)")
    print("  ✅ integrity gate: quick_check ok, foreign_key_check clean")


def _edit_taxonomy_yaml(dry_run: bool) -> None:
    data = yaml.safe_load(TAXONOMY_PATH.read_text())
    disc = data["disciplines"]
    for sw in SWAPS:
        demote = sw["demote"]
        before = len(disc)
        disc[:] = [d for d in disc if d["canonical"] != demote]
        if len(disc) == before:
            raise RuntimeError(f"demote canonical not found: {demote}")
        disc.append({"canonical": sw["promote"], "group": sw["group"], "raw": sw["raw"]})
        if dry_run:
            print(f"  [dry-run] remove canonical {demote!r}; add canonical {sw['promote']!r} (group {sw['group']!r})")
    if dry_run:
        return
    out = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    fd, tmp = tempfile.mkstemp(dir=str(TAXONOMY_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(out)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(TAXONOMY_PATH))
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print("  ✅ taxonomy_v5.yaml updated (atomic)")


def _counts(db_path: Path) -> dict:
    conn = sqlite3.connect(str(db_path))
    try:
        out = {}
        for sw in SWAPS:
            p = sw["promote"]
            d = sw["demote"]
            out[f"promote:{p}"] = conn.execute(
                "SELECT COUNT(*) FROM fbs WHERE discipline='emerging' AND LOWER(TRIM(discipline_raw))=LOWER(?)", (p,)
            ).fetchone()[0]
            out[f"demote:{d}"] = conn.execute(
                "SELECT COUNT(*) FROM fbs WHERE discipline=?", (d,)
            ).fetchone()[0]
        return out
    finally:
        conn.close()


def _apply(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    n = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for sw in SWAPS:
            p, d = sw["promote"], sw["demote"]
            cur = conn.execute(
                "UPDATE fbs SET discipline=?, taxonomy_match_method='exact' "
                "WHERE discipline='emerging' AND LOWER(TRIM(discipline_raw))=LOWER(?)",
                (p, p),
            )
            n += cur.rowcount
            cur = conn.execute(
                "UPDATE fbs SET discipline='emerging', discipline_raw=?, taxonomy_match_method='emerging_real' "
                "WHERE discipline=?",
                (d, d),
            )
            n += cur.rowcount
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return n


def _sync_checkpoints() -> None:
    for s in [_PROJECT_ROOT / "scripts" / "sync_checkpoint_from_db.py",
              _PROJECT_ROOT / "scripts" / "sync_s5_checkpoint_from_db.py"]:
        if not s.exists():
            print(f"  ⚠️  sync script missing: {s.name}", file=sys.stderr)
            continue
        print(f"  🔄 re-syncing checkpoint: {s.name} ...")
        r = subprocess.run([sys.executable, str(s)], cwd=str(_PROJECT_ROOT),
                           capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            print(f"  ⚠️  {s.name} FAILED (rc={r.returncode}): {r.stderr[-500:]}", file=sys.stderr)
        else:
            print(f"  ✅ {s.name} re-synced")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-backup", action="store_true")
    ap.add_argument("--skip-integrity", action="store_true")
    ap.add_argument("--no-sync", action="store_true")
    args = ap.parse_args()

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"❌ DB not found: {db_path}", file=sys.stderr)
        return 1

    counts = _counts(db_path)
    for sw in SWAPS:
        p, d = sw["promote"], sw["demote"]
        print(f"  promote {p!r} ({counts[f'promote:{p}']} FBs)  ↔  demote {d!r} ({counts[f'demote:{d}']} FBs)")

    if not args.apply:
        print("\n  [dry-run] no writes. Re-run with --apply.")
        _edit_taxonomy_yaml(dry_run=True)
        return 0

    print("\n  🔒 backing up pre-write ...")
    if not args.skip_backup:
        _backup_file(db_path, "pre_swap")
        _backup_file(TAXONOMY_PATH, "pre_swap")
        _backup_file(S4_CHECKPOINT, "pre_swap")
        _backup_file(S5_CHECKPOINT, "pre_swap")

    if not args.skip_integrity:
        _integrity_gate(db_path)

    print("\n  ✏️  updating taxonomy_v5.yaml ...")
    _edit_taxonomy_yaml(dry_run=False)

    print("\n  💾 applying swaps ...")
    n = _apply(db_path)
    print(f"  ✅ applied {n} row updates")

    if not args.skip_integrity:
        _integrity_gate(db_path)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
        reconcile_canonical_status(conn)
        update_counts_from_fbs(conn)
        conn.commit()
    finally:
        conn.close()
    print("  ✅ taxonomy_counts reconciled")

    if not args.no_sync:
        _sync_checkpoints()

    print("\n✅ BUG-150 swaps complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
