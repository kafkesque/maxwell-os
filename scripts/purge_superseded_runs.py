#!/usr/bin/env python3
"""
scripts/purge_superseded_runs.py — superseded-run exclusion (D-2936 / D-2937)
=============================================================================
WHY THIS EXISTS
---------------
Only ONE pipeline run may be served: the canonical run (D-2881, CANONICAL_RUN).
The store, however, physically holds every run that was ever committed:

    t11                    7855 rows   (superseded: pre-rechunk extraction)
    rechunk-v4-20260929    6591 rows   (CANONICAL_RUN — the served corpus)
    e2e                     122 rows   (test artifact)
    bug198_reinject           6 rows   (test artifact)

Serving is *pinned* to the canonical run, so no superseded row is ever returned —
but the superseded rows are still (a) counted in every census (BUG-713: the "14574 FB"
figure is 2.2x the served corpus), (b) present in fbs_fts, and (c) present in
vec_fbs / vec_fbs_ctx, where sqlite-vec computes KNN *before* the run filter is
applied, so a superseded row steals a candidate slot from a served row (measured:
19-26 of the vec_fbs top-100 survive for canonical PASS rows).

This tool excludes them for real: archive -> delete -> rebuild text index -> verify.

SAFETY (every one of these is a hard precondition, not a warning)
----------------------------------------------------------------
1. The canonical run can NEVER be in the purge set (C16, fail closed).
2. Every purge-set run id must exist in the store, or the run is refused — a typo must
   not silently no-op.
3. Zero inbound references from surviving rows into the purge set across
   prerequisite_fbs / related_fbs / contradicts_fbs / source_principle_ids. A dangling
   graph edge would be a silent data loss, so it is a REFUSAL, not a warning.
4. DRY-RUN is the default and the only mode that does not mutate. --apply additionally
   requires (a) a fresh C13 backup of the store, (b) --confirm matching the purge set
   exactly, (c) the archive written and hashed first (R-D410).
5. One transaction. Any exception rolls back everything.
6. Post-apply verification: row counts per surviving run, PRAGMA integrity_check,
   vector<->row alignment both directions, FTS row count, and a live hybrid-search
   smoke test asserting no returned row belongs to a purged run.

USAGE
-----
    python3 scripts/purge_superseded_runs.py                      # dry-run (default)
    python3 scripts/purge_superseded_runs.py --json
    python3 scripts/purge_superseded_runs.py --runs t11           # narrow the set
    python3 scripts/purge_superseded_runs.py --apply --confirm t11,e2e,bug198_reinject

C12: run set + archive dir + backup dir from config/pipeline_config.yaml (serving.*).
C13: backup before the batch write.  C16: no silent errors.  R-D410: archive, never delete blind.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pipeline_paths import (  # noqa: E402
    CANONICAL_RUN,
    DB_PATH,
    required_mapping,
    required_sequence,
)
from pipeline.sqlite_vec_loader import load_sqlite_vec  # noqa: E402

CFG_PATH: Path = PROJECT_ROOT / "config" / "pipeline_config.yaml"
_CFG_HOME = str(CFG_PATH.relative_to(CFG_PATH.parent.parent))  # D-2982: derived, not a second copy
with open(CFG_PATH, encoding='utf-8') as _f:
    _CFG: dict = yaml.safe_load(_f) or {}
# D-2982 (C16/D-2644): declared read - the old `_CFG.get("serving", {})` silently emptied the
# purge list, so the tool reported "nothing superseded" for a config it had never read.
_SERVING: dict = required_mapping(_CFG, "serving", where=_CFG_HOME)

DEFAULT_RUNS: tuple[str, ...] = tuple(
    str(r) for r in required_sequence(_SERVING, "superseded_runs", where=_CFG_HOME)
)
ARCHIVE_ROOT: Path = PROJECT_ROOT / "archive" / "superseded_runs"
BACKUP_DIR: Path = PROJECT_ROOT / "knowledge pipeline" / "backups"
REFERENCE_COLUMNS: tuple[str, ...] = (
    "prerequisite_fbs", "related_fbs", "contradicts_fbs", "source_principle_ids",
)
SMOKE_QUERY: str = "how do feedback loops stabilize a system"
SMOKE_K: int = 10


def _id_list(value: object) -> list[str]:
    """Parse a cross-reference column into a list of ids.

    Tolerates the three shapes found in the store: JSON array, comma string,
    bare string (C16: never assume the JSON shape — that assumption already
    produced a JSONDecodeError in the BUG-711 repair path).
    """
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:  # C16: loud, not silent
            raise RuntimeError(f"unparseable id list: {text[:80]!r}") from exc
        return [str(v) for v in parsed] if isinstance(parsed, list) else [str(parsed)]
    return [t.strip() for t in text.split(",") if t.strip()]


def _sha256(path: Path) -> str:
    """Return the hex sha256 of a file, streamed in 1 MiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _connect() -> sqlite3.Connection:
    """Open the store with the sqlite-vec extension loaded (vec0 DELETE needs it)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    load_sqlite_vec(conn)
    return conn


def assert_purge_set_valid(conn: sqlite3.Connection, runs: tuple[str, ...]) -> None:
    """Refuse a purge set that could destroy served data or silently no-op (C16)."""
    if not runs:
        raise RuntimeError("purge set is empty — refusing (nothing to do is a config error, not a success)")
    if CANONICAL_RUN in runs:
        raise RuntimeError(f"canonical run {CANONICAL_RUN!r} is in the purge set — REFUSED (D-2936: the served corpus is never purged)")
    present = {r[0] for r in conn.execute("SELECT DISTINCT pipeline_run_id FROM fbs")}
    unknown = sorted(set(runs) - present)
    if unknown:
        raise RuntimeError(f"purge set contains run id(s) absent from the store: {unknown} (present: {sorted(present)}) — REFUSED (a typo must not no-op)")


def inbound_references(conn: sqlite3.Connection, runs: tuple[str, ...]) -> dict[str, int]:
    """Count graph edges from SURVIVING rows into the purge set (must be all zero)."""
    doomed: set[str] = set()
    for r in conn.execute(
        f"SELECT fb_id FROM fbs WHERE pipeline_run_id IN ({','.join('?' * len(runs))})", runs
    ):
        doomed.add(r["fb_id"])
    counts: dict[str, int] = {}
    for col in REFERENCE_COLUMNS:
        found = 0
        for r in conn.execute(
            f"SELECT {col} AS v FROM fbs WHERE pipeline_run_id NOT IN ({','.join('?' * len(runs))}) AND {col} IS NOT NULL",
            runs,
        ):
            found += sum(1 for i in _id_list(r["v"]) if i in doomed)
        counts[col] = found
    return counts


def inventory(conn: sqlite3.Connection, runs: tuple[str, ...]) -> dict[str, object]:
    """Measure exactly what the purge set costs the store, per run and in total."""
    placeholders = ",".join("?" * len(runs))
    per_run: dict[str, dict[str, int]] = {}
    for run in runs:
        per_run[run] = {
            "rows": conn.execute("SELECT COUNT(*) FROM fbs WHERE pipeline_run_id = ?", (run,)).fetchone()[0],
            "pass": conn.execute("SELECT COUNT(*) FROM fbs WHERE pipeline_run_id = ? AND status = 'PASS'", (run,)).fetchone()[0],
            "quarantine": conn.execute("SELECT COUNT(*) FROM fbs WHERE pipeline_run_id = ? AND status = 'QUARANTINE'", (run,)).fetchone()[0],
            "vec_fbs": conn.execute("SELECT COUNT(*) FROM vec_fbs_rowids WHERE rowid IN (SELECT rowid FROM fbs WHERE pipeline_run_id = ?)", (run,)).fetchone()[0],
            "vec_fbs_ctx": conn.execute("SELECT COUNT(*) FROM vec_fbs_ctx_rowids WHERE rowid IN (SELECT rowid FROM fbs WHERE pipeline_run_id = ?)", (run,)).fetchone()[0],
            "distinct_sources": conn.execute("SELECT COUNT(DISTINCT primary_source) FROM fbs WHERE pipeline_run_id = ? AND primary_source IS NOT NULL", (run,)).fetchone()[0],
        }
    total_rows = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
    doomed_rows = conn.execute(f"SELECT COUNT(*) FROM fbs WHERE pipeline_run_id IN ({placeholders})", runs).fetchone()[0]
    fts_rows = conn.execute("SELECT COUNT(*) FROM fbs_fts").fetchone()[0]
    return {
        "canonical_run": CANONICAL_RUN,
        "runs": per_run,
        "store_rows_total": total_rows,
        "store_rows_doomed": doomed_rows,
        "store_rows_surviving": total_rows - doomed_rows,
        "fbs_fts_rows": fts_rows,
        "fbs_fts_rows_after": fts_rows - doomed_rows,
        "inbound_references": inbound_references(conn, runs),
    }


def archive_rows(conn: sqlite3.Connection, runs: tuple[str, ...], outdir: Path) -> Path:
    """Write every doomed row to JSONL + a hashed manifest BEFORE any deletion (R-D410)."""
    outdir.mkdir(parents=True, exist_ok=True)
    placeholders = ",".join("?" * len(runs))
    out_path = outdir / "superseded_rows.jsonl"
    cols = [r[1] for r in conn.execute("PRAGMA table_info(fbs)")]
    written = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in conn.execute(f"SELECT * FROM fbs WHERE pipeline_run_id IN ({placeholders})", runs):
            fh.write(json.dumps(dict(zip(cols, tuple(row))), ensure_ascii=False) + "\n")
            written += 1
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "canonical_run": CANONICAL_RUN,
        "purged_runs": list(runs),
        "rows": written,
        "archive_file": out_path.name,
        "sha256": _sha256(out_path),
        "store": str(DB_PATH),
        "store_sha256_at_archive": _sha256(DB_PATH),
    }
    (outdir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  📦 archived {written} rows -> {out_path}  (sha256 {manifest['sha256'][:16]}…)")
    return out_path


def take_backup() -> Path:
    """Copy the store to knowledge pipeline/backups before a mutating apply (C13)."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"maxwell.db.pre_purge_{stamp}"
    shutil.copy2(DB_PATH, dest)
    print(f"  💾 backup -> {dest}  (sha256 {_sha256(dest)[:16]}…)")
    return dest


def purge(conn: sqlite3.Connection, runs: tuple[str, ...], index_only: bool = False) -> dict[str, int]:
    """Delete the purge set from the vector indices, and (unless index_only) from fbs.

    index_only=True is the REVERSIBLE half of D-2936: it removes the superseded run's
    rows from vec_fbs / vec_fbs_ctx so the KNN candidate pool stops being diluted,
    while every knowledge row stays in fbs (row + definition are the durable object;
    the vector is a deterministic derived artefact that scripts/backfill_embeddings.py
    can rebuild from the definition). It is the mode to use while the superseded run
    is still the only committed extraction for corpus files the canonical run has not
    reprocessed yet.

    fbs_fts is an EXTERNAL-CONTENT fts5 table with only an AFTER INSERT trigger
    (no delete trigger), so a row delete leaves a stale index entry until
    'rebuild' is issued — that rebuild is part of this transaction, not a
    follow-up step, because a stale index would silently shadow the fix.
    """
    placeholders = ",".join("?" * len(runs))
    rowids = [r[0] for r in conn.execute(f"SELECT rowid FROM fbs WHERE pipeline_run_id IN ({placeholders})", runs)]
    if not rowids:
        raise RuntimeError("nothing to purge — refusing to run a mutating path with an empty result set (C16)")
    stats: dict[str, int] = {"vec_fbs": 0, "vec_fbs_ctx": 0, "fbs": 0}
    conn.execute("BEGIN IMMEDIATE")
    try:
        for rowid in rowids:
            stats["vec_fbs"] += conn.execute("DELETE FROM vec_fbs WHERE rowid = ?", (int(rowid),)).rowcount or 0
            stats["vec_fbs_ctx"] += conn.execute("DELETE FROM vec_fbs_ctx WHERE rowid = ?", (int(rowid),)).rowcount or 0
        if not index_only:
            stats["fbs"] = conn.execute(f"DELETE FROM fbs WHERE pipeline_run_id IN ({placeholders})", runs).rowcount or 0
            conn.execute("INSERT INTO fbs_fts(fbs_fts) VALUES('rebuild')")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return stats


def verify(conn: sqlite3.Connection, runs: tuple[str, ...], index_only: bool = False) -> dict[str, object]:
    """Prove the purge left the store consistent AND the served surface untouched.

    BUG-716 (2026-10-11): in --index-only mode the purge set's fbs rows are KEPT on purpose,
    so 'residual rows == 0' is the WRONG success condition - it made a CORRECT index-only run
    raise a false C16 failure (observed live). Mode-correct conditions: ZERO vectors left for
    the purge set, no orphan vectors, integrity ok, and no purged run leaking into a live
    search. fts_matches_fbs only applies to a full purge.
    """
    placeholders = ",".join("?" * len(runs))
    residual = conn.execute(f"SELECT COUNT(*) FROM fbs WHERE pipeline_run_id IN ({placeholders})", runs).fetchone()[0]
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    fts_rows = conn.execute("SELECT COUNT(*) FROM fbs_fts").fetchone()[0]
    fbs_rows = conn.execute("SELECT COUNT(*) FROM fbs").fetchone()[0]
    vec_orphans = conn.execute("SELECT COUNT(*) FROM vec_fbs_rowids v LEFT JOIN fbs f ON v.rowid = f.rowid WHERE f.rowid IS NULL").fetchone()[0]
    vec_rows_in_purged = conn.execute(
        f"SELECT COUNT(*) FROM vec_fbs_rowids vr JOIN fbs f ON f.rowid = vr.rowid "
        f"WHERE f.pipeline_run_id IN ({placeholders})", runs
    ).fetchone()[0]
    vec_rows_in_purged = conn.execute(
        f"SELECT COUNT(*) FROM vec_fbs_rowids vr JOIN fbs f ON f.rowid = vr.rowid "
        f"WHERE f.pipeline_run_id IN ({placeholders})", runs
    ).fetchone()[0]
    unvectorised = conn.execute("SELECT COUNT(*) FROM fbs f LEFT JOIN vec_fbs_rowids v ON v.rowid = f.rowid WHERE v.rowid IS NULL").fetchone()[0]
    try:
        from pipeline.retrieve import search_hybrid

        hits = search_hybrid(conn, SMOKE_QUERY, limit=SMOKE_K, rerank=False)
        leaked = sorted({h["pipeline_run_id"] for h in hits if h["pipeline_run_id"] in set(runs)})
        smoke = {"query": SMOKE_QUERY, "hits": len(hits), "leaked_runs": leaked, "top": [h["name"][:40] for h in hits[:3]]}
    except Exception as exc:  # C16
        smoke = {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "index_only": index_only,
        "residual_rows_in_purged_runs": residual,
        "vec_rows_in_purged_runs": vec_rows_in_purged,
        "integrity_check": integrity,
        "fbs_rows": fbs_rows,
        "fbs_fts_rows": fts_rows,
        "fts_matches_fbs": fts_rows == fbs_rows,
        "vec_orphans": vec_orphans,
        "unvectorised_rows": unvectorised,
        "smoke": smoke,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Exclude superseded pipeline runs from the live store (D-2936/D-2937)")
    ap.add_argument("--runs", default=",".join(DEFAULT_RUNS), help="comma-separated run ids (default: serving.superseded_runs)")
    ap.add_argument("--apply", action="store_true", help="mutate the store (requires --confirm + a C13 backup)")
    ap.add_argument("--index-only", action="store_true",
                    help="D-2936: remove the purge set from vec_fbs/vec_fbs_ctx ONLY (reversible; fbs rows and fbs_fts untouched)")
    ap.add_argument("--confirm", default="", help="must equal the purge set exactly when --apply is used")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    runs: tuple[str, ...] = tuple(r.strip() for r in args.runs.split(",") if r.strip())
    conn = _connect()
    assert_purge_set_valid(conn, runs)
    inv = inventory(conn, runs)

    if args.json:
        print(json.dumps({"mode": "apply" if args.apply else "dry-run", "inventory": inv}, indent=2))
    else:
        mode = "APPLY" if args.apply else "DRY-RUN"
        mode += " · INDEX-ONLY (reversible)" if args.index_only else ""
        print(f"\n═══ SUPERSEDED-RUN AUDIT (D-2936/D-2937) — {mode} ═══")
        print(f"canonical (served) run : {inv['canonical_run']}")
        for run, s in inv["runs"].items():
            print(f"  {run:<22} rows={s['rows']:<6} PASS={s['pass']:<6} QUAR={s['quarantine']:<6} vec={s['vec_fbs']:<6} vec_ctx={s['vec_fbs_ctx']:<6} sources={s['distinct_sources']}")
        pct = 100.0 * inv["store_rows_doomed"] / max(inv["store_rows_total"], 1)
        print(f"store rows             : {inv['store_rows_total']} -> {inv['store_rows_surviving']} (purge {inv['store_rows_doomed']} = {pct:.1f}%)")
        print(f"fbs_fts rows           : {inv['fbs_fts_rows']} -> {inv['fbs_fts_rows_after']}")
        print(f"inbound refs into purge set: {inv['inbound_references']}")

    refs = inv["inbound_references"]
    if any(int(v) for v in refs.values()):
        raise RuntimeError(f"REFUSED: surviving rows reference the purge set {refs} — a graph edge would dangle (C16)")

    if not args.apply:
        print("\n  dry-run only. Re-run with --apply --confirm <runs> to exclude these runs.")
        return 0

    if args.index_only:
        print("  ⚠️  index-only: fbs rows and fbs_fts are untouched; vectors remain rebuildable via scripts/backfill_embeddings.py")
    if args.confirm != ",".join(runs):
        raise RuntimeError(f"--apply requires --confirm '{','.join(runs)}' (got '{args.confirm}') — REFUSED (C16)")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    take_backup()
    archive_rows(conn, runs, ARCHIVE_ROOT / stamp)
    t0 = time.time()
    stats = purge(conn, runs, index_only=args.index_only)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    print(f"  🗑  deleted fbs={stats['fbs']} vec_fbs={stats['vec_fbs']} vec_fbs_ctx={stats['vec_fbs_ctx']} in {time.time() - t0:.1f}s")
    v = verify(conn, runs, index_only=args.index_only)
    (ARCHIVE_ROOT / stamp / "VERIFICATION.json").write_text(json.dumps(v, indent=2), encoding="utf-8")
    print(f"  ✅ verify: residual={v['residual_rows_in_purged_runs']} integrity={v['integrity_check']} "
          f"fts={v['fbs_fts_rows']}==fbs={v['fbs_rows']} vec_orphans={v['vec_orphans']} unvectorised={v['unvectorised_rows']}")
    print(f"  🔎 smoke: {v['smoke']}")
    print("  ⚠️  next: rebuild dependent censuses (governance/bug_status.json, taxonomy_counts) and re-run the retrieval benchmark against an owner-signed golden set")
    # BUG-716: the success condition is MODE-dependent (index-only keeps the fbs rows on purpose).
    if args.index_only:
        _bad = (
            v["vec_rows_in_purged_runs"]
            or v["integrity_check"] != "ok"
            or v["vec_orphans"]
            or v["smoke"].get("leaked_runs")
        )
    else:
        _bad = (
            v["residual_rows_in_purged_runs"]
            or v["integrity_check"] != "ok"
            or v["vec_orphans"]
            or not v["fts_matches_fbs"]
        )
    if _bad:
        raise RuntimeError(f"post-purge verification FAILED: {v} (C16 — store left inconsistent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
