#!/usr/bin/env python3
"""repair_single_concept_diversity.py — re-derive `source_diversity` on the single-concept rows (BUG-989).

WHY THIS EXISTS (MEASURED 2026-10-24). pipeline/insert_single_concept.py writes `source_ids=[<one work>]` and
`is_convergent: 0` but never writes `source_diversity`, so the 14 PASS single-concept rows carry NULL where the
derivation registry says the value MUST equal `|source_ids|` (config/derivations.yaml#fbs.source_diversity,
kind=derived_regenerable, parity rail scripts/check_corroboration_bit.py). That rail goes RED on those 14 rows:
"stored source_diversity=0 but the evidence set holds 1 distinct canonical work(s)".

THE VALUE IS DERIVED, NEVER INVENTED (D-3034/D-3109): `source_diversity = |distinct source_ids|` — the SAME rule
the parity rail re-derives with, read from the row's OWN `source_ids`. A row whose `source_ids` cannot be read is
REFUSED, never defaulted to 1.

SCOPE (fail-closed). Only PASS rows whose `source_diversity` IS NULL are touched — the QUARANTINE BUG-990 evidence
row (f523504e…) is deliberately blank and is NOT in the PASS scope, so it is never written. The producer is fixed
separately so future inserts cannot reintroduce the gap.

NEVER OVERWRITES. A cell is written only when NULL; a second run is a no-op. Dry-run by default; --apply writes
ONE transaction with a C13 backup first and re-derives the post-state INSIDE the transaction before COMMIT.

spec: BUG-989 / D-3130. LLM-free, deterministic (D-343/C1).

usage: python3 scripts/repair_single_concept_diversity.py [--db PATH] [--apply]
exit:  0 nothing owed | 0 applied (with --apply) | 1 refused | 2 cannot evaluate
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_DEFAULT = "knowledge pipeline/maxwell.db"


def works_of(source_ids: object) -> int | None:
    """Distinct canonical WORK count from the row's own `source_ids` (D-2185/D-2309); None when unreadable."""
    if source_ids is None:
        return 0
    text = str(source_ids).strip()
    if not text:
        return 0
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return None
    if isinstance(parsed, list):
        return len({str(item) for item in parsed})
    if isinstance(parsed, dict):
        return len(parsed)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-derive source_diversity on single-concept PASS rows (BUG-989).")
    ap.add_argument("--db", default=DB_DEFAULT)
    ap.add_argument("--apply", action="store_true", help="write (default: dry-run)")
    ap.add_argument("--backup-dir", default="backups")
    args = ap.parse_args()

    db = PROJECT_ROOT / args.db
    if not db.exists():
        print(f"CANNOT EVALUATE: store not found at {db}")
        return 2

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "select fb_id, source_ids, source_diversity, status from fbs "
            "where status = 'PASS' and source_diversity is null order by fb_id"
        ).fetchall()
        if not rows:
            print("NOT OWED: no PASS row carries a NULL source_diversity (idempotent — nothing written).")
            return 0

        writes: dict[str, int] = {}
        refused: list[str] = []
        for r in rows:
            works = works_of(r["source_ids"])
            if works is None:
                refused.append(f"{r['fb_id']}: source_ids unreadable")
                continue
            writes[str(r["fb_id"])] = works

        if refused:
            for line in refused:
                print(f"REFUSED: {line} (D-3034: a value must resolve, never be invented)")
            return 1

        print(f"plan  : {len(writes)} PASS row(s) would have source_diversity re-derived to |source_ids|")
        for fid, works in writes.items():
            print(f"  {fid}  -> source_diversity = {works}")
        if not args.apply:
            print("[dry-run] rerun with --apply to write.")
            return 0

        # C13: a store mutation gets a backup, taken with sqlite's own backup API (consistent under WAL).
        backup_dir = PROJECT_ROOT / args.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"maxwell.db.pre_bug989_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        dest = sqlite3.connect(backup_path)
        try:
            conn.backup(dest)
        finally:
            dest.close()
        print(f"backup: {backup_path.relative_to(PROJECT_ROOT)} "
              f"({backup_path.stat().st_size / 1_048_576:.1f} MiB)")

        conn.execute("BEGIN IMMEDIATE")
        try:
            for fid, works in writes.items():
                cur = conn.execute("update fbs set source_diversity = ? where fb_id = ?", (works, fid))
                if cur.rowcount != 1:
                    raise RuntimeError(f"expected 1 row for {fid}, updated {cur.rowcount} — rolling back")
            # post-state re-derived INSIDE the transaction, before COMMIT (D-2970)
            after = conn.execute(
                "select fb_id, source_diversity from fbs where fb_id in (%s) order by fb_id"
                % ",".join("?" * len(writes)),
                tuple(writes.keys()),
            ).fetchall()
            for a in after:
                if int(a["source_diversity"] or 0) != writes[str(a["fb_id"])]:
                    raise RuntimeError(f"post-state {a['fb_id']}={a['source_diversity']!r} != {writes[str(a['fb_id'])]}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise

        print(f"APPLIED: source_diversity re-derived on {len(writes)} row(s).")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
