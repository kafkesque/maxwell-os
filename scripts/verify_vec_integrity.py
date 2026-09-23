#!/usr/bin/env python3
"""D-354 control: referential integrity of the sqlite-vec stores in the RUN database.

Why this exists: the stage6 vector insert path is append-only, so a re-commit that replaces
fbs rows leaves the previous generation's vectors behind as orphans. A row COUNT cannot see
that (the recorded check printed 'Vector: READY 15990/7995' while only 7995 rows were live).

  live    = vec rowid present in fbs           -> useful index entry
  orphan  = vec rowid absent from fbs          -> dead entry: wastes k-NN slots; at 100 percent
                                                  the hit->fbs join drops every hit (silent empty)
  missing = fbs rowid with no vec entry        -> the row is unreachable by the vector leg

Exit 0 = every listed table is exactly the live set. Exit 1 = RED (C16: fail loud, no silent pass).
Read-only: opens the DB with mode=ro and never writes. No LLM, no network, deterministic.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CFG_PATH = _ROOT / "config" / "vec_integrity.yaml"


def shadow_rowids_table(conn: sqlite3.Connection, vec_table: str, suffix: str) -> str | None:
    """Resolve the sqlite-vec shadow rowid table for a vec0 virtual table (or None).

    sqlite-vec exposes the rowid column of a vec0 table as a plain shadow table named
    '<vec_table><suffix>'. The name is resolved from sqlite_master rather than assumed,
    so a version that renames it fails as an explicit RED instead of a silent zero.
    """
    name = vec_table + suffix
    row = conn.execute("select name from sqlite_master where type='table' and name=?", (name,)).fetchone()
    return row[0] if row else None


def measure(conn: sqlite3.Connection, fbs_table: str, rowids_table: str) -> dict[str, int]:
    """Count live/orphaned/missing vector rows for one vec0 table (see module docstring)."""
    sql_live = ("select count(*) from {r} v join {f} b on b.rowid = v.rowid").format(r=rowids_table, f=fbs_table)
    sql_orph = ("select count(*) from {r} v left join {f} b on b.rowid = v.rowid where b.rowid is null").format(r=rowids_table, f=fbs_table)
    sql_miss = ("select count(*) from {f} b left join {r} v on v.rowid = b.rowid where v.rowid is null").format(r=rowids_table, f=fbs_table)
    return {
        "live": conn.execute(sql_live).fetchone()[0],
        "orphans": conn.execute(sql_orph).fetchone()[0],
        "missing": conn.execute(sql_miss).fetchone()[0],
    }


def main() -> int:
    """Check every configured vec0 table and print one line per table; return 1 on any RED."""
    cfg = yaml.safe_load(_CFG_PATH.read_text())
    db = _ROOT / cfg["db_path"]
    fbs = cfg["fbs_table"]
    suffix = cfg.get("shadow_rowids_suffix", "_rowids")
    if not db.exists():
        print("RED vec_integrity: db missing: " + str(db))
        return 1
    conn = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True)
    red: list[str] = []
    n_fbs = conn.execute("select count(*) from {f}".format(f=fbs)).fetchone()[0]
    for vec_table in cfg["vec_tables"]:
        rowids = shadow_rowids_table(conn, vec_table, suffix)
        if rowids is None:
            red.append(vec_table + ": cannot resolve shadow rowid table " + vec_table + suffix + " -- refusing (C16)")
            continue
        m = measure(conn, fbs, rowids)
        live_pct = (100.0 * m["live"] / (m["live"] + m["orphans"])) if (m["live"] + m["orphans"]) else 0.0
        print("{t}: live={l} orphans={o} missing={mi} live_pct={p:.1f}".format(
            t=vec_table, l=m["live"], o=m["orphans"], mi=m["missing"], p=live_pct))
        if m["orphans"] > 0:
            red.append(vec_table + ": " + str(m["orphans"]) + " orphaned rows (dead index entries, " + ("ALL" if m["live"] == 0 else "some") + " of the table)")
        if m["missing"] > 0:
            red.append(vec_table + ": " + str(m["missing"]) + " fbs rows are unreachable by the vector leg")
        if m["live"] != n_fbs:
            red.append(vec_table + ": live " + str(m["live"]) + " != fbs " + str(n_fbs))
    conn.close()
    for r in red:
        print("RED vec_integrity: " + r)
    print("vec integrity: " + str(len(cfg["vec_tables"])) + " tables checked, " + str(len(red)) + " RED")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
