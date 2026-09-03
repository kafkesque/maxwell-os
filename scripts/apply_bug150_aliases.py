#!/usr/bin/env python3
"""D2534: Deterministic BUG-150 alias application (6 user-approved labels).

Maps 6 user-approved raw discipline labels onto existing canonical disciplines
via ALIAS (significant subfield/synonym overlap). This is DETERMINISTIC — no LLM.

The 6 aliases were human-approved and verified clean against cross-axis
contamination (none of the raw labels appear in the DOMAIN axis raw lists, and
all 6 canonical targets exist in the DISCIPLINE list).

Mechanics (C13 / C6 / C12):
1. Back up DB + taxonomy_v5.yaml + S4/S5 checkpoints (timestamped, fsync'd).
2. Append the raw labels to the canonical entries' `raw:` lists in
   taxonomy_v5.yaml (permanent alias so future classification maps them via
   match_to_canonical → get_synonym_index).
3. Integrity gate (PRAGMA quick_check + foreign_key_check) — refuse on failure.
4. Reclassify the affected FBs: discipline 'emerging' → canonical,
   taxonomy_match_method='alias', discipline_raw PRESERVED (single atomic txn).
   Domains and every other committed field are untouched (discipline-only scope).
5. Post-write integrity gate + count verification.
6. Re-sync S4/S5 checkpoints (scripts/sync_checkpoint_from_db.py +
   scripts/sync_s5_checkpoint_from_db.py) to fix DB↔checkpoint drift.

Usage:
  python3 scripts/apply_bug150_aliases.py            # dry-run (no writes)
  python3 scripts/apply_bug150_aliases.py --apply    # backup + integrity gate + write
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

# canonical -> [exact-DB-raw-string, TitleCase variant, ...]
# The first entry is the exact `discipline_raw` string present in the DB.
ALIASES: list[tuple[str, list[str]]] = [
    ("research methodology", ["survey methodology", "Survey Methodology"]),
    ("machine learning", ["reinforcement learning", "Reinforcement Learning"]),
    ("artificial intelligence", ["AI safety", "AI Safety"]),
    ("sociology", ["social movement theory", "Social Movement Theory"]),
    ("psychology", ["environmental psychology", "Environmental Psychology"]),
    ("engineering", ["manufacturing engineering", "Manufacturing Engineering"]),
]

TAXONOMY_PATH = _PROJECT_ROOT / "config" / "taxonomy_v5.yaml"
S4_CHECKPOINT = _PROJECT_ROOT / "knowledge pipeline" / "stage4_merge" / "t11" / "checkpoint_enriched.jsonl"
S5_CHECKPOINT = _PROJECT_ROOT / "knowledge pipeline" / "stage5_verify" / "t11" / "checkpoint.jsonl"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_file(path: Path, tag: str) -> Path:
    """C13/C6: timestamped backup, size-verified + fsync'd."""
    if not path.exists():
        print(f"  ⚠️  backup skipped (not found): {path}")
        return Path(str(path) + f".bak_{_ts()}_{tag}")
    bak = Path(str(path) + f".bak_{_ts()}_{tag}")
    shutil.copy2(str(path), str(bak))
    with open(bak, "rb") as _f:
        os.fsync(_f.fileno())
    if path.stat().st_size != bak.stat().st_size:
        raise RuntimeError(f"backup size mismatch — aborting write: {path}")
    print(f"  🔒 backup: {bak} ({bak.stat().st_size:,} bytes)")
    return bak


def _integrity_gate(db_path: Path) -> None:
    """C13: refuse to write if quick_check or foreign_key_check fails."""
    conn = sqlite3.connect(str(db_path))
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if qc != "ok":
        raise RuntimeError(f"integrity gate FAILED (quick_check={qc}) — aborting write")
    if fk:
        raise RuntimeError(f"integrity gate FAILED ({len(fk)} foreign_key violations) — aborting write")
    print("  ✅ integrity gate: quick_check ok, foreign_key_check clean")


def _norm(s: str) -> str:
    """Case/dash-fold for dedup against existing raw lists (mirrors normalize_label)."""
    import unicodedata
    return unicodedata.normalize("NFKC", s or "").replace("–", "-").replace("—", "-").strip().lower()


def _edit_taxonomy_yaml(dry_run: bool) -> dict[str, list[str]]:
    """Append alias raw labels to the 6 canonical entries. Returns what was added."""
    data = yaml.safe_load(TAXONOMY_PATH.read_text())
    disc = data["disciplines"]
    added: dict[str, list[str]] = {}
    for canonical, variants in ALIASES:
        entry = next((d for d in disc if d["canonical"] == canonical), None)
        if entry is None:
            raise RuntimeError(f"canonical not found in taxonomy disciplines: {canonical}")
        existing = {_norm(r) for r in entry.get("raw", [])}
        to_add = [v for v in variants if _norm(v) not in existing]
        added[canonical] = to_add
        if to_add:
            entry["raw"] = entry.get("raw", []) + to_add
    if dry_run:
        print("  [dry-run] taxonomy_v5.yaml would add:")
        for c, vs in added.items():
            if vs:
                print(f"    {c}: {vs}")
        return added
    # Atomic write (C6): tempfile → fsync → os.replace
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
    return added


def _affected_rows(db_path: Path) -> list[tuple[str, str]]:
    """Return (fb_id, discipline_raw) for the 51 FBs matching the 6 aliases."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = []
        for canonical, variants in ALIASES:
            raw_exact = variants[0]
            cur = conn.execute(
                "SELECT fb_id, discipline_raw FROM fbs "
                "WHERE discipline='emerging' AND LOWER(TRIM(discipline_raw))=LOWER(?) "
                "ORDER BY fb_id",
                (raw_exact,),
            )
            for r in cur.fetchall():
                rows.append((r["fb_id"], canonical, r["discipline_raw"]))
        return rows
    finally:
        conn.close()


def _apply_fbs(db_path: Path, rows: list[tuple[str, str, str]]) -> int:
    """C6: single atomic transaction — discipline + match_method only."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for fb_id, canonical, raw in rows:
            conn.execute(
                "UPDATE fbs SET discipline=?, taxonomy_match_method='alias' WHERE fb_id=?",
                (canonical, fb_id),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return len(rows)


def _sync_checkpoints() -> None:
    """Blindspot fix (D2533): re-sync S4/S5 checkpoints after DB mutation."""
    scripts = [
        _PROJECT_ROOT / "scripts" / "sync_checkpoint_from_db.py",
        _PROJECT_ROOT / "scripts" / "sync_s5_checkpoint_from_db.py",
    ]
    for s in scripts:
        if not s.exists():
            print(f"  ⚠️  sync script missing: {s.name}", file=sys.stderr)
            continue
        print(f"  🔄 re-syncing checkpoint: {s.name} ...")
        r = subprocess.run(
            [sys.executable, str(s)], cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=1800,
        )
        if r.returncode != 0:
            print(f"  ⚠️  {s.name} FAILED (rc={r.returncode}): {r.stderr[-500:]}", file=sys.stderr)
        else:
            print(f"  ✅ {s.name} re-synced")


def _emerging_count(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT COUNT(*) FROM fbs WHERE discipline='emerging'").fetchone()[0]
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply 6 user-approved BUG-150 discipline aliases (deterministic).")
    ap.add_argument("--apply", action="store_true", help="Write (backup + integrity gate). Default dry-run.")
    ap.add_argument("--skip-backup", action="store_true", help="DANGER: skip pre-write backup.")
    ap.add_argument("--skip-integrity", action="store_true", help="DANGER: skip integrity gate.")
    ap.add_argument("--no-sync", action="store_true", help="Skip checkpoint re-sync.")
    args = ap.parse_args()

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"❌ DB not found: {db_path}", file=sys.stderr)
        return 1

    before_emerging = _emerging_count(db_path)
    rows = _affected_rows(db_path)
    print(f"📊 affected FBs (emerging → canonical): {len(rows)}")
    print(f"📊 discipline='emerging' before: {before_emerging}")
    for canonical, variants in ALIASES:
        n = sum(1 for _, c, _ in rows if c == canonical)
        print(f"    {canonical!r:24} ← {variants[0]!r:28} ({n} FBs)")

    if not args.apply:
        print("\n  [dry-run] no writes performed. Re-run with --apply to commit.")
        _edit_taxonomy_yaml(dry_run=True)
        return 0

    # ── Pre-write backups (C13) ──
    print("\n  🔒 backing up pre-write ...")
    if not args.skip_backup:
        _backup_file(db_path, "pre_alias")
        _backup_file(TAXONOMY_PATH, "pre_alias")
        _backup_file(S4_CHECKPOINT, "pre_alias")
        _backup_file(S5_CHECKPOINT, "pre_alias")
    else:
        print("  ⚠️  --skip-backup: NO backup taken")

    # ── Integrity gate ──
    if not args.skip_integrity:
        _integrity_gate(db_path)

    # ── 1. taxonomy YAML alias (permanent) ──
    print("\n  ✏️  updating taxonomy_v5.yaml ...")
    _edit_taxonomy_yaml(dry_run=False)

    # ── 2. reclassify FBs ──
    print(f"\n  💾 reclassifying {len(rows)} FBs ...")
    n = _apply_fbs(db_path, rows)
    print(f"  ✅ applied {n} rows")

    # ── post-write integrity + count ──
    if not args.skip_integrity:
        _integrity_gate(db_path)
    after_emerging = _emerging_count(db_path)
    print(f"📊 discipline='emerging' after: {after_emerging} (delta {-before_emerging + after_emerging:+d})")

    # ── 3. checkpoint sync ──
    if not args.no_sync:
        _sync_checkpoints()

    print("\n✅ BUG-150 alias application complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
