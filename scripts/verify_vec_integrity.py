#!/usr/bin/env python3
"""D-354/D-357 control: referential integrity of the sqlite-vec stores in the RUN database.

Why this exists: the stage6 vector insert path is append-only, so a re-commit that replaces
fbs rows leaves the previous generation's vectors behind as orphans. A row COUNT cannot see
that (the recorded check printed 'Vector: READY 15990/7995' while only 7995 rows were live).

  live    = vec rowid present in fbs           -> useful index entry
  orphan  = vec rowid absent from fbs          -> dead entry: wastes k-NN slots; at 100 percent
                                                  the hit->fbs join drops every hit (silent empty)
  missing = fbs rowid with no vec entry        -> the row is unreachable by the vector leg

Per-table contract (D-357, applying D-355: assert the state you are in):
  required: true   -> the store must MIRROR fbs: live == fbs, orphans == 0, missing == 0.
  required: false  -> the store is DORMANT (production must not read it, R26): it must be EMPTY,
                      so orphans == 0 and live == 0. Here missing == fbs is the EXPECTED state,
                      and an absent table PASSES.
A bare string in vec_tables is treated as required: true (fail-closed default).

Exit 0 = every listed table satisfies its contract. Exit 1 = RED (C16: fail loud, no silent pass).
Read-only: opens the DB mode=ro and reads only the shadow rowid table, so auditing needs no
vec0 module (only REPAIR does). No LLM, no network, deterministic.
"""
from __future__ import annotations

import argparse
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
    sql_miss = ("select count(*) from {f} b left join {r} v on v.rowid = b.rowid where v.rowid is null").format(f=fbs_table, r=rowids_table)
    return {
        "live": conn.execute(sql_live).fetchone()[0],
        "orphans": conn.execute(sql_orph).fetchone()[0],
        "missing": conn.execute(sql_miss).fetchone()[0],
    }


def table_spec(entry) -> tuple[str, bool]:
    """Resolve one vec_tables entry to (table_name, required). A bare string is required."""
    if isinstance(entry, dict):
        return str(entry["name"]), bool(entry.get("required", True))
    return str(entry), True


def main(argv: list[str] | None = None) -> int:
    """Check every configured vec0 table against its state-dependent contract; return 1 on any RED."""
    ap = argparse.ArgumentParser(description="D-354/D-357 vec store referential integrity")
    ap.add_argument("--db", default=None, help="override the configured db path (e.g. a repaired copy)")
    args = ap.parse_args(argv)
    cfg = yaml.safe_load(_CFG_PATH.read_text(encoding='utf-8'))
    db = Path(args.db) if args.db else _ROOT / cfg["db_path"]
    fbs = cfg["fbs_table"]
    suffix = cfg.get("shadow_rowids_suffix", "_rowids")
    if not db.exists():
        print("RED vec_integrity: db missing: " + str(db))
        return 1
    conn = sqlite3.connect("file:" + str(db) + "?mode=ro", uri=True)
    red: list[str] = []
    n_required = 0
    n_dormant = 0
    n_fbs = conn.execute("select count(*) from {f}".format(f=fbs)).fetchone()[0]
    for entry in cfg["vec_tables"]:
        vec_table, required = table_spec(entry)
        state = "REQUIRED" if required else "DORMANT"
        rowids = shadow_rowids_table(conn, vec_table, suffix)
        if rowids is None:
            if required:
                red.append(vec_table + " (required): cannot resolve shadow rowid table " + vec_table + suffix + " - refusing (C16)")
            else:
                print("{t}: {s} - table absent (strongest form of empty)".format(t=vec_table, s=state))
            continue
        m = measure(conn, fbs, rowids)
        denom = m["live"] + m["orphans"]
        live_pct = (100.0 * m["live"] / denom) if denom else 0.0
        print("{t}: {s} live={l} orphans={o} missing={mi} live_pct={p:.1f}".format(
            t=vec_table, s=state, l=m["live"], o=m["orphans"], mi=m["missing"], p=live_pct))
        if required:
            n_required += 1
            if m["orphans"] > 0:
                red.append(vec_table + ": " + str(m["orphans"]) + " orphaned rows (dead index entries, " + ("ALL" if m["live"] == 0 else "some") + " of the table)")
            if m["missing"] > 0:
                red.append(vec_table + ": " + str(m["missing"]) + " fbs rows are unreachable by the vector leg")
            if m["live"] != n_fbs:
                red.append(vec_table + ": live " + str(m["live"]) + " != fbs " + str(n_fbs))
        else:
            n_dormant += 1
            if m["orphans"] > 0:
                red.append(vec_table + " (dormant): " + str(m["orphans"]) + " orphaned rows - a dormant store must hold NO entries (R26: production must not read it)")
            if m["live"] > 0:
                red.append(vec_table + " (dormant): " + str(m["live"]) + " live rows - a dormant store must be EMPTY (R26: production must not read it)")
    conn.close()
    for r in red:
        print("RED vec_integrity: " + r)
    print("vec integrity: " + str(n_required + n_dormant) + " tables checked (" + str(n_required) + " required, " + str(n_dormant) + " dormant), " + str(len(red)) + " RED")
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
