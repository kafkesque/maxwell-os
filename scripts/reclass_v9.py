#!/usr/bin/env python3
"""reclass_v9.py — D-2897 v9 menu-edit deterministic re-classification (96 + 1 alias rows).

Deterministic, LLM-free. Re-stamps the directly-affected canonical rows ONLY:
  visual semiotics(44)->semiotics, information retrieval(9)->information science,
  computational theory(16)->emerging, creative writing(+studies, 15)->creative writing,
  museum studies(13)->museum studies. Preserves discipline_raw/domains_raw VERBATIM.
Crash-safe: DB backup (C13) + single txn. --apply to write.
"""
from __future__ import annotations

import sqlite3
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.closed_menu import menu_hash  # noqa: E402
from pipeline.discipline_macro import macro_for  # noqa: E402

RUN = "rechunk-v4-20260929"
LIVE_HASH = menu_hash()
TAX_V = "v9"

# deterministic (canonical -> macro derived from discipline_macro_groups.yaml)
MOVES = [
    ("visual semiotics", "semiotics"),
    ("information retrieval", "information science"),
    ("computational theory", "emerging"),
]
RAW_PROMOTES = [  # (raw discipline label(s), new canonical)
    (("creative writing", "creative writing studies"), "creative writing"),
    (("museum studies",), "museum studies"),
]


def main() -> int:
    apply = "--apply" in sys.argv
    with sqlite3.connect(DB_PATH) as conn:
        plan = []
        for old, new in MOVES:
            n = conn.execute(
                "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id=? AND discipline=?",
                (RUN, old)).fetchone()[0]
            plan.append((old, new, n))
        for raws, new in RAW_PROMOTES:
            ph = ",".join("?" * len(raws))
            n = conn.execute(
                f"SELECT COUNT(*) FROM fbs WHERE pipeline_run_id=? AND discipline='emerging' "
                f"AND discipline_raw IN ({ph})", (RUN, *raws)).fetchone()[0]
            plan.append(("/".join(raws), new, n))
        total = sum(p[2] for p in plan)
        print(f"live menu_hash: {LIVE_HASH}")
        for old, new, n in plan:
            print(f"  {old!r:32s} -> {new!r:22s} {n} rows")
        print(f"TOTAL: {total} rows (expected 97)")
        if not apply:
            return 0
        if total != 97:
            print("FAIL-CLOSED: expected 97 rows, got %d" % total, file=sys.stderr)
            return 1
        bak = DB_PATH.with_name(DB_PATH.name + f".bak-v9-{int(time.time())}")
        shutil.copy2(DB_PATH, bak)
        print(f"backup: {bak.name}")
        cur = conn.cursor()
        for old, new, n in plan:
            if "/" in old:
                raws = tuple(old.split("/"))
                ph = ",".join("?" * len(raws))
                cur.execute(
                    f"UPDATE fbs SET discipline=?, discipline_macro=?, menu_hash=?, taxonomy_version=? "
                    f"WHERE pipeline_run_id=? AND discipline='emerging' AND discipline_raw IN ({ph})",
                    (new, macro_for(new), LIVE_HASH, TAX_V, RUN, *raws))
            else:
                cur.execute(
                    "UPDATE fbs SET discipline=?, discipline_macro=?, menu_hash=?, taxonomy_version=? "
                    "WHERE pipeline_run_id=? AND discipline=?",
                    (new, macro_for(new), LIVE_HASH, TAX_V, RUN, old))
            print(f"  updated {old!r} -> {new!r}: {cur.rowcount}")
        conn.commit()
        # verify raw invariance
        bad = conn.execute(
            "SELECT COUNT(*) FROM fbs WHERE pipeline_run_id=? AND discipline_raw IS NULL", (RUN,)).fetchone()[0]
        print(f"rows with NULL discipline_raw after update: {bad}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
