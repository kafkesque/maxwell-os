#!/usr/bin/env python3
"""D-354 repair: delete DEAD vec rows (entries whose rowid is not an fbs rowid).

Dry-run by default: prints the plan and writes nothing. --apply performs one DELETE per
configured vec table inside a SINGLE transaction, re-measures with the D-354 gate, and exits
non-zero if any table is still RED (C16: no silent pass).

Why a script and not the one-line sqlite3 CLI recipe this task was handed before the recipe had
ever been run: opening a vec0 table needs the sqlite-vec extension, so the repair must run on an
interpreter that can load it. The default /usr/local/bin/python3 is a python.org framework build
with enable_load_extension UNAVAILABLE (BUG-104) and the macOS sqlite3 CLI rejects .load, so both
fail with "no such module: vec0". Run this with /opt/homebrew/bin/python3.

Safety: never pipeline/safe_delete.py (BUG-261); fbs is never touched; the plan and the deletes are
both derived from fbs rowids, so an entry that is live for some row is never removed. Because the
only way back is the backup, --apply makes its own timestamped copy first (--no-backup to skip).
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CFG_PATH = _ROOT / "config" / "vec_integrity.yaml"
_GATE = _ROOT / "scripts" / "verify_vec_integrity.py"


def _spec(entry) -> tuple[str, bool]:
    """Resolve one vec_tables entry to (table_name, required); a bare string is required."""
    if isinstance(entry, dict):
        return str(entry["name"]), bool(entry.get("required", True))
    return str(entry), True


def plan(conn: sqlite3.Connection, fbs: str, vec_tables: list) -> dict[str, int]:
    """Count the dead rows per vec table (read via the shadow rowid table: no vec0 needed)."""
    dead: dict[str, int] = {}
    for entry in vec_tables:
        table, _required = _spec(entry)
        shadow = table + "_rowids"
        exists = conn.execute("select name from sqlite_master where type='table' and name=?", (shadow,)).fetchone()
        if not exists:
            dead[table] = -1
            continue
        dead[table] = conn.execute(
            "select count(*) from {r} v left join {f} b on b.rowid = v.rowid where b.rowid is null".format(r=shadow, f=fbs)
        ).fetchone()[0]
    return dead


def main(argv: list[str] | None = None) -> int:
    """Plan (default) or apply the dead-row deletion, then re-measure with the D-354 gate."""
    ap = argparse.ArgumentParser(description="D-354 repair: delete dead vec rows")
    ap.add_argument("--apply", action="store_true", help="perform the deletes (default: dry run)")
    ap.add_argument("--db", default=None, help="override the configured db path")
    ap.add_argument("--no-backup", action="store_true", help="skip the internal pre-repair copy")
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(_CFG_PATH.read_text(encoding='utf-8'))
    db = Path(args.db) if args.db else _ROOT / cfg["db_path"]
    fbs = cfg["fbs_table"]
    if not db.exists():
        print("RED repair_vec_integrity: db missing: " + str(db))
        return 1

    conn = sqlite3.connect(str(db))
    dead = plan(conn, fbs, cfg["vec_tables"])
    total = sum(v for v in dead.values() if v > 0)
    for table, n in dead.items():
        print("  {t}: {n} dead rows".format(t=table, n=("shadow rowid table absent" if n < 0 else n)))
    print("plan: " + str(total) + " dead vec rows would be deleted (fbs untouched)")

    if not args.apply:
        print("dry run - nothing written. Re-run with --apply to delete.")
        conn.close()
        return 0

    if total == 0:
        print("nothing to do: the stores already satisfy the contract")
        conn.close()
        return 0

    if not args.no_backup:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = db.with_name(db.name + ".pre_d354_" + stamp)
        shutil.copy2(str(db), str(backup))
        print("backup: " + str(backup))
    try:
        conn.enable_load_extension(True)
        import sqlite_vec
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
    except AttributeError as e:
        print("RED repair_vec_integrity: this interpreter cannot load extensions (" + str(e) + ").")
        print("   Use the interpreter named in config/vec_integrity.yaml (interpreter: /opt/homebrew/bin/python3).")
        conn.close()
        return 1
    except Exception as e:
        print("RED repair_vec_integrity: sqlite-vec failed to load: " + str(e))
        conn.close()
        return 1

    try:
        conn.execute("BEGIN IMMEDIATE")
        for table, n in dead.items():
            if n <= 0:
                continue
            cur = conn.execute(
                "delete from {t} where rowid not in (select rowid from {f})".format(t=table, f=fbs)
            )
            print("  deleted " + str(cur.rowcount) + " from " + table)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("RED repair_vec_integrity: repair failed and was rolled back: " + str(e))
        conn.close()
        return 1
    conn.close()

    print("re-measuring with the D-354 gate:")
    proc = subprocess.run([sys.executable, str(_GATE), "--db", str(db)], capture_output=True, text=True)
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print("RED repair_vec_integrity: gate still reports RED after the repair (C16)")
        return 1
    print("PASS repair_vec_integrity: every configured vec table satisfies its D-354/D-357 contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
