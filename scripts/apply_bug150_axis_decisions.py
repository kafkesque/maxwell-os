#!/usr/bin/env python3
"""D2539: BUG-150 axis decisions — 5 domain moves + 5 discipline aliases (user-approved).

Adds alias mappings to taxonomy_v5.yaml so the existing deterministic kind-swap
(bug197_kind_swap) resolves each both-axes label onto its correct axis:
  - 5 DOMAIN moves   → alias to a DOMAIN canonical;   kind-swap direction B moves the
                       label off the discipline axis (clears discipline_raw, adds domain).
  - 5 DISCIPLINE aliases → alias to a DISCIPLINE canonical; kind-swap direction A moves
                       the label off the domain axis (removes from domains_raw, recovers
                       as the canonical discipline).

Kept unique (no mapping here): technical communication, health informatics, urban economics.
Deferred (deeper review): human factors engineering.

Mechanics (C13 / C6):
1. Back up DB + taxonomy_v5.yaml + S4/S5 checkpoints.
2. Append alias raw labels to the target canonicals' `raw:` lists (atomic).
3. Re-run bug197_kind_swap (fresh process → re-reads taxonomy; deterministic, backed up).
4. Re-sync S4/S5 checkpoints.

Usage:
  python3 scripts/apply_bug150_axis_decisions.py            # dry-run
  python3 scripts/apply_bug150_axis_decisions.py --apply    # backup + integrity + write
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

# raw label -> target DOMAIN canonical
DOMAIN_ALIASES: dict[str, str] = {
    "educational technology": "education",
    "public health policy": "health & wellness",
    "audio engineering": "media & entertainment",
    "cartography": "data visualization",
    "printing technology": "editorial & advertising",
}
# raw label -> target DISCIPLINE canonical
DISCIPLINE_ALIASES: dict[str, str] = {
    "econometrics": "economics",
    "constitutional law": "law",
    "international relations": "political economy",
    "bioethics": "philosophy",
    "formal logic": "philosophy",
}

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


def _norm(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKC", s or "").replace("–", "-").replace("—", "-").strip().lower()


def _edit_taxonomy(dry_run: bool) -> None:
    data = yaml.safe_load(TAXONOMY_PATH.read_text())
    added = []
    for section, mapping in (("domains", DOMAIN_ALIASES), ("disciplines", DISCIPLINE_ALIASES)):
        entries = data[section]
        for raw, canonical in mapping.items():
            entry = next((e for e in entries if e["canonical"] == canonical), None)
            if entry is None:
                raise RuntimeError(f"{section} canonical not found: {canonical}")
            existing = {_norm(r) for r in entry.get("raw", [])}
            variants = [raw, " ".join(w.capitalize() for w in raw.split())]
            to_add = [v for v in variants if _norm(v) not in existing and _norm(v) != _norm(canonical)]
            if to_add:
                entry["raw"] = entry.get("raw", []) + to_add
                added.append((section, canonical, to_add))
    if dry_run:
        for section, canonical, vs in added:
            print(f"  [dry-run] {section}:{canonical} += {vs}")
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

    print(f"📊 domain aliases: {len(DOMAIN_ALIASES)} | discipline aliases: {len(DISCIPLINE_ALIASES)}")

    if not args.apply:
        print("\n  [dry-run] no writes. Re-run with --apply.")
        _edit_taxonomy(dry_run=True)
        return 0

    print("\n  🔒 backing up pre-write ...")
    if not args.skip_backup:
        _backup_file(db_path, "pre_axis_decision")
        _backup_file(TAXONOMY_PATH, "pre_axis_decision")
        _backup_file(S4_CHECKPOINT, "pre_axis_decision")
        _backup_file(S5_CHECKPOINT, "pre_axis_decision")

    if not args.skip_integrity:
        _integrity_gate(db_path)

    print("\n  ✏️  updating taxonomy_v5.yaml ...")
    _edit_taxonomy(dry_run=False)

    print("\n  🔄 re-running deterministic kind-swap (fresh process) ...")
    r = subprocess.run([sys.executable, str(_PROJECT_ROOT / "scripts" / "bug197_kind_swap.py")],
                       cwd=str(_PROJECT_ROOT), capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        print(f"  ❌ kind-swap FAILED (rc={r.returncode}): {r.stderr[-500:]}", file=sys.stderr)
        return 1
    print("  " + r.stdout.strip().replace("\n", "\n  "))

    if not args.skip_integrity:
        _integrity_gate(db_path)

    if not args.no_sync:
        _sync_checkpoints()

    print("\n✅ BUG-150 axis decisions applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
