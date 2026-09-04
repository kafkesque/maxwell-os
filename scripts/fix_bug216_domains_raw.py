#!/usr/bin/env python3
"""
fix_bug216_domains_raw.py — BUG-216 repair (D2378 raw-preserve violation).

FBs with `domains=['emerging']` but EMPTY `domains_raw` lost their raw domain
labels during the kind-safe rederive. Those raw labels survive verbatim in
`checkpoint_enriched_kindsafe.jsonl` (fallback: `checkpoint.jsonl`). This script
backfills `domains_raw` from the checkpoint — deterministic, LLM-free, fb_id
never touched.

Recovery rule (D2378): backfill ONLY where the source checkpoint carries a
NON-empty `domains_raw` for the same fb_id and the DB row is empty. A row whose
raw label genuinely never existed (S4 emitted `emerging` with no raw domain) is
left untouched and reported separately.

Safety (C6/C13):
  * MUTATION IS OPT-IN via `--apply`; default is read-only `--manifest`.
  * `--apply` backs up the DB first (shutil.copy2 → timestamped .bak).
  * UPDATE runs in a single transaction (all-or-nothing), then re-verifies.

Run:
  python3 scripts/fix_bug216_domains_raw.py --manifest
  python3 scripts/fix_bug216_domains_raw.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

S4_T11 = REPO / "knowledge pipeline" / "stage4_merge" / "t11"
RECOVERY_SOURCES = [
    S4_T11 / "checkpoint_enriched_kindsafe.jsonl",
    S4_T11 / "checkpoint.jsonl",
]


def _recovery_map() -> dict[str, list]:
    """fb_id -> non-empty domains_raw (first source wins)."""
    out: dict[str, list] = {}
    for src in RECOVERY_SOURCES:
        if not src.exists():
            continue
        with open(src, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                fid = rec.get("fb_id")
                raw = rec.get("domains_raw")
                if not fid or fid in out:
                    continue
                if isinstance(raw, list) and raw:
                    out[fid] = raw
    return out


def _targets(con: sqlite3.Connection) -> list[tuple[str, str]]:
    cur = con.cursor()
    cur.execute(
        "SELECT fb_id, name FROM fbs "
        "WHERE domains LIKE '%emerging%' "
        "AND (domains_raw IS NULL OR domains_raw='' OR domains_raw='[]')"
    )
    return cur.fetchall()


def main() -> int:
    ap = argparse.ArgumentParser(description="BUG-216: backfill empty domains_raw (D2378)")
    ap.add_argument("--manifest", action="store_true", help="list targets + recovery coverage (read-only)")
    ap.add_argument("--apply", action="store_true", help="backup DB then transactional backfill")
    args = ap.parse_args()

    rmap = _recovery_map()
    con = sqlite3.connect(DB_PATH)
    targets = _targets(con)

    print(f"📋 {len(targets)} BUG-216 target FBs (domains~emerging, empty domains_raw)")
    recoverable = []
    unrecoverable = []
    for fid, name in targets:
        raw = rmap.get(fid)
        if raw:
            recoverable.append((fid, name, raw))
        else:
            unrecoverable.append((fid, name))

    for fid, name, raw in recoverable:
        print(f"  ✅ recover {fid[:12]} {name[:40]:40} → {len(raw)} raw label(s)")
    for fid, name in unrecoverable:
        print(f"  ⚠️  no source raw label: {fid[:12]} {name[:40]:40} (genuine `emerging`, left as-is)")

    if args.manifest or not args.apply:
        con.close()
        print(f"\nRecoverable: {len(recoverable)} / {len(targets)}. Run --apply to write.")
        return 0

    if not recoverable:
        con.close()
        print("Nothing to backfill.")
        return 0

    # C13: backup before batch write.
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup = DB_PATH.with_name(DB_PATH.name + f".bak_bug216_{ts}")
    con.close()
    shutil.copy2(DB_PATH, backup)
    print(f"\n💾 backed up {DB_PATH.name} -> {backup.name}")

    con = sqlite3.connect(DB_PATH)
    try:
        con.execute("BEGIN")
        cur = con.cursor()
        for fid, _name, raw in recoverable:
            cur.execute(
                "UPDATE fbs SET domains_raw=? WHERE fb_id=?",
                (json.dumps(raw, ensure_ascii=False), fid),
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    # Verify.
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM fbs WHERE domains LIKE '%emerging%' "
        "AND (domains_raw IS NULL OR domains_raw='' OR domains_raw='[]')"
    )
    remaining = cur.fetchone()[0]
    con.close()
    print(f"✅ backfilled {len(recoverable)} FBs; remaining empty domains_raw: {remaining} "
          f"(expect {len(unrecoverable)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
