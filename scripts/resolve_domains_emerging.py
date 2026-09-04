#!/usr/bin/env python3
"""scripts/resolve_domains_emerging.py — D2566 deterministic DOMAIN-axis emerging resolution.

Resolves FBs whose `domains` array contains "emerging" by re-mapping their
`domains_raw` through the full domain index (taxonomy_v5 raw + synonym_map
SYNONYMS-only + alias_map domain_aliases + canonical-self + compound split). The
"emerging" placeholder is REPLACED by the mapped canonical domain(s); any existing
non-emerging domain is preserved. No LLM — deterministic and kind-safe.

This is the domain-axis counterpart of resolve_emerging_deterministic.py (which
handles the discipline axis). Catch-all domains are NOT excluded here (unlike
enrichment): a raw label that genuinely maps to a catch-all still resolves the
"emerging" placeholder, which is strictly better than leaving it unmapped.

Safety (C13/C6/C12): default DRY-RUN; --apply requires a timestamped DB backup +
integrity gate and commits in a single atomic transaction.

Usage:
  python3 scripts/resolve_domains_emerging.py          # dry-run
  python3 scripts/resolve_domains_emerging.py --apply  # backup + integrity + write
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

from scripts.apply_enrichment import _domain_index, _expand, _parse  # noqa: E402


def _backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_domains_emerging")
    shutil.copy2(str(db_path), str(bak))
    with open(bak, "rb") as f:
        os.fsync(f.fileno())
    if db_path.stat().st_size != bak.stat().st_size:
        raise RuntimeError("backup size mismatch — aborting write")
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


def _compute(idx: dict[str, list[str]], conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT fb_id, name, domains, domains_raw FROM fbs").fetchall()
    out: list[dict] = []
    for r in rows:
        d = _parse(r["domains"])
        if "emerging" not in d:
            continue
        keep = [x for x in d if x != "emerging"]
        mapped: set[str] = set()
        for x in _parse(r["domains_raw"]):
            mapped |= _expand(x, idx)
        new = sorted(set(keep) | mapped)
        if new and new != sorted(keep):
            out.append({
                "fb_id": r["fb_id"], "name": r["name"],
                "old": d, "new": new, "raw": r["domains_raw"],
            })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="deterministic DOMAIN-axis emerging resolution (D2566).")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    idx = _domain_index()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    updates = _compute(idx, conn)
    conn.close()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} FB(s) with domains ∋ emerging resolvable\n")
    for u in updates[:40]:
        print(f"  {u['name'][:44]:44s} {u['old']} -> {u['new']}")
    if len(updates) > 40:
        print(f"  … and {len(updates) - 40} more")

    if not args.apply:
        print("\n  (dry-run — no write. Re-run with --apply to commit.)")
        return 0

    _backup_db(DB_PATH)
    _integrity_gate(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute("UPDATE fbs SET domains=? WHERE fb_id=?",
                         (json.dumps(u["new"]), u["fb_id"]))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    print(f"\n✅ committed {len(updates)} DOMAIN-axis emerging resolutions atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
