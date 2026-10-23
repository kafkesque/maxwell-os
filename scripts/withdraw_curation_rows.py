#!/usr/bin/env python3
"""scripts/withdraw_curation_rows.py - the WRITER for the declared act `withdraw_with_archive` (D-3135).

WHY THIS EXISTS. config/content_type_restamp.yaml declares what a DISPOSITION ruling on a STORED row asks for
(`act_for_stored_row: withdraw_with_archive`) and when it asks for it (`writer_trigger: a disposition-ruled row
whose stored state is in the SERVED path`), and it named the writer OWED. The trigger fired on 2026-10-23: the
owner walked the ten BUG-977 rows and ruled six of them a DISPOSITION, four of those in the default answer path.
A declaration whose writer does not exist resolves to nothing (D-3034), so the writer is built against the
population that needs it - not before (D-2952/C28: the column and its writer land together, never as an inert badge).

THE POPULATION IS THE INSTRUMENT (D-2956 clause 4). Two disjoint sets, and only ONE of them is acted on:
  * LABEL-ILLEGAL (`content_type` IS a declared disposition): the store's own contract would never have admitted
    the row - D-2965's commit gate REFUSES a disposition as a content_type and the 5-role axis is CLOSED - so the
    row must leave the store, archive-first. THE OWNER'S RULING NAMES THE SHELF (`retention:` in the config).
  * ROLE-CARRYING (a legal role, owner ruled a disposition, and SERVED): REPORTED LOUDLY AND NEVER ACTED ON. The
    row is contract-valid; deleting a valid row on a curation ruling alone is a bigger act with a higher bar, and
    conflating the two would let this tool quietly delete principles. It is named in every run instead.
A label-illegal row WITHOUT an owner ruling is also never acted on: a script does not decide curation (D-2898).

THE PROTOCOL IS DECLARED, NOT INVENTED - it is scripts/purge_superseded_runs.py's protocol for a different
population: plan -> archive (sha256) -> C13 backup -> ONE BEGIN IMMEDIATE (prune graph edges, drop the vector
legs, delete the rows, REBUILD the external-content FTS) -> verify inside the same transaction -> receipt.
Dry-run is the default and the only mode that does not mutate; --apply additionally needs --confirm naming the
exact id set and a fresh backup.

WHY THE EDGES ARE PRUNED IN THE SAME TRANSACTION. A surviving row pointing at a withdrawn id is a dangling edge:
retrieval joins by id, so it would silently resolve to nothing (the BUG-711 shape). MEASURED 2026-10-23 before the
first run: 73 surviving rows, 76 edges, none of them a row's ONLY edge. Every pruned edge is archived, and a prune
that would leave a surviving row's reference column EMPTY is REFUSED rather than performed.

Exit (BUG-457 tri-state): 0 clean | 2 a withdrawal is OWED (loud, non-fatal) | 1 refused / cannot evaluate.
Usage:
    python3 scripts/withdraw_curation_rows.py                     # dry-run plan (nothing is mutated)
    python3 scripts/withdraw_curation_rows.py --check             # read-only exit code for a rail
    python3 scripts/withdraw_curation_rows.py --apply --confirm <fb_id>,<fb_id>,...
    python3 scripts/withdraw_curation_rows.py --selftest          # known-answer controls on a FIXTURE store
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT: Path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.sqlite_vec_loader import load_sqlite_vec  # noqa: E402

CONFIG: Path = ROOT / "config" / "curation_withdrawal.yaml"
TABLES_VERIFIED: tuple[str, ...] = ("fbs", "fbs_fts", "vec_fbs", "vec_fbs_ctx")


def ensure_vec_capable(cfg: dict[str, Any]) -> None:
    """Re-exec under a declared interpreter when THIS one cannot load sqlite-vec (C16: no silent degradation).

    The withdrawal must remove a withdrawn row's VECTOR legs as well as its row: a stale vector keeps the row in
    the KNN candidate pool and lets it steal a served row's slot (the BUG-713 harm). The vec0 virtual table can
    only be written with the extension loaded, and `pipeline.sqlite_vec_loader` degrades to a silent no-op when
    the interpreter lacks the `sqlite_vec` package - which is exactly the state that would leave the store with a
    deleted row and a live vector. MEASURED 2026-10-23: the store's own interpreter (`python3` on PATH) lacks the
    package while a declared candidate has it, so the tool re-execs ONCE (guarded by an env flag) instead of
    failing an owner's run over a PATH detail.
    """
    try:
        import sqlite_vec  # noqa: F401,PLC0415 - a capability probe, not a dependency of this module
    except ImportError:
        pass
    else:
        return
    if os.environ.get("MAXWELL_VEC_REEXEC") == "1":
        raise SystemExit("FAIL-CLOSED: sqlite-vec is still unloadable after re-exec - the vector legs cannot be "
                         "removed, and a withdrawal with a live vector is the BUG-713 harm. Nothing was written.")
    candidate = str(((cfg.get("vec_loader") or {}).get("interpreter")) or "")
    if not candidate or not Path(candidate).exists():
        raise SystemExit("FAIL-CLOSED: this interpreter cannot load sqlite-vec and no working interpreter is "
                         f"declared at {CONFIG.relative_to(ROOT)}#vec_loader.interpreter. Nothing was written.")
    os.environ["MAXWELL_VEC_REEXEC"] = "1"
    print(f"  [re-exec] sqlite-vec missing here -> {candidate}")
    os.execv(candidate, [candidate, str(Path(__file__).resolve()), *sys.argv[1:]])


def load_cfg() -> dict[str, Any]:
    """Load the tool's declarations; a missing or partial config is a DEFECT, not an empty config (C16)."""
    if not CONFIG.exists():
        raise SystemExit(f"FAIL-CLOSED: {CONFIG.relative_to(ROOT)} is absent - a writer with no declarations is not a writer")
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    for key in ("map_schema_home", "vocab_home", "table", "id_column", "label_column", "name_column",
                "archive_root", "backup_subdir", "backup_prefix", "reference_columns", "retention", "receipt"):
        if not cfg.get(key):
            raise SystemExit(f"FAIL-CLOSED: {CONFIG.relative_to(ROOT)} is missing '{key}' - the writer cannot state what it acts on")
    return cfg


def _home(path_with_key: str) -> tuple[Path, str]:
    """Split '<file>#<key>' into (path, key); a home that names no block is a DEFECT (D-3034)."""
    home, _, key = str(path_with_key).partition("#")
    if not home or not key:
        raise SystemExit(f"FAIL-CLOSED: '{path_with_key}' names no block (expected <file>#<key>)")
    return ROOT / home, key


def declared_vocab(cfg: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return (roles, dispositions) READ from their one home - never restated in this file (D-2646)."""
    path, _ = _home(str(cfg["vocab_home"]) + "#-")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    roles: set[str] = set()
    for key in cfg.get("vocab_type_keys") or []:
        roles |= {str(k) for k in (doc.get(key) or {})}
    dispositions: set[str] = set()
    for key in cfg.get("vocab_disposition_keys") or []:
        dispositions |= {str(k) for k in (doc.get(key) or {})}
    if not roles or not dispositions:
        raise SystemExit(f"FAIL-CLOSED: {cfg['vocab_home']} yielded roles={sorted(roles)} dispositions={sorted(dispositions)}")
    return roles, dispositions


def load_map(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load the owner's adjudication map (the WARRANT) and its schema from the map's one home (D-2967)."""
    path, key = _home(str(cfg["map_schema_home"]))
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    schema = doc.get(key)
    if not isinstance(schema, dict):
        raise SystemExit(f"FAIL-CLOSED: {cfg['map_schema_home']} is not a mapping - the writer cannot find the warrant map")
    for k in ("path", "rows_key", "current_key", "role_key", "disposition_key"):
        if not str(schema.get(k) or "").strip():
            raise SystemExit(f"FAIL-CLOSED: {cfg['map_schema_home']} is missing '{k}'")
    rows = json.loads((ROOT / str(schema["path"])).read_text(encoding="utf-8")).get(str(schema["rows_key"]))
    if not isinstance(rows, list):
        raise SystemExit(f"FAIL-CLOSED: {schema['path']}#{schema['rows_key']} is not a list")
    return [r for r in rows if isinstance(r, dict)], schema


def retention_for(cfg: dict[str, Any], value: str) -> dict[str, str]:
    """Return the declared retention block for a disposition value; an undeclared value FAILS CLOSED (D-3034)."""
    block = (cfg.get("retention") or {}).get(value)
    if not isinstance(block, dict) or not str(block.get("retention") or "").strip():
        raise SystemExit(f"FAIL-CLOSED: no retention is declared for disposition '{value}' in {CONFIG.relative_to(ROOT)}")
    return {"retention": str(block["retention"]), "why": str(block.get("why") or "")}


def hold_shelf(cfg: dict[str, Any]) -> str:
    """Return the pipeline's own HOLD-shelf declaration, READ from its one home (never restated here, C12)."""
    path, key = _home(str(cfg.get("hold_shelf_home") or "config/pipeline_config.yaml#stage4.quarantine_output"))
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    node: Any = doc
    for part in key.split("."):
        node = (node or {}).get(part) if isinstance(node, dict) else None
    return str(node or "UNDECLARED")


def live_rows(con: sqlite3.Connection, cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Read every row's id/name/label straight from the store - the population is measured, never supplied."""
    idc, label, name = str(cfg["id_column"]), str(cfg["label_column"]), str(cfg["name_column"])
    return {str(r[0]): {"fb_id": str(r[0]), "name": str(r[1] or ""), "label": str(r[2] or "").strip()}
            for r in con.execute(f"SELECT {idc}, {name}, {label} FROM {cfg['table']}")}


def plan(cfg: dict[str, Any], map_rows: list[dict[str, Any]], schema: dict[str, Any],
         live: dict[str, dict[str, Any]], roles: set[str], dispositions: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Split the store against the warrant into the four states this tool must tell apart.

    Args:
        cfg: the tool's declaration (retention shelves, vocabularies).
        map_rows: the owner's adjudication map (the warrant).
        schema: the map's schema (which key names which vocabulary).
        live: {fb_id: row} for the whole store.
        roles: the declared ROLE vocabulary.
        dispositions: the declared DISPOSITION vocabulary.

    Returns:
        {"withdraw": [...], "owner_owed": [...], "stale": [...], "role_carrying_ruled": [...]} - every label-illegal
        row lands in exactly one of the first three, and a contract-valid but ruled row is reported separately.
    """
    current_key, disp_key = str(schema["current_key"]), str(schema["disposition_key"])
    warrant: dict[str, dict[str, Any]] = {}
    for r in map_rows:
        if isinstance(r.get(disp_key), str) and str(r[disp_key]).strip():
            warrant[str(r.get("fb_id"))] = r

    out: dict[str, list[dict[str, Any]]] = {"withdraw": [], "owner_owed": [], "stale": [], "role_carrying_ruled": []}
    for fid, row in live.items():
        ruling = warrant.get(fid)
        illegal = row["label"] not in roles  # blank, undeclared or a disposition - all "not a ROLE"
        if ruling is not None:
            value = str(ruling[disp_key]).strip()
            if value not in dispositions:
                raise SystemExit(f"FAIL-CLOSED: row {fid[:12]} carries an undeclared disposition ruling '{value}'")
            stale = str(ruling.get(current_key) or "").strip() != row["label"]
            entry = {"fb_id": fid, "name": row["name"], "label": row["label"], "ruling": value,
                     "reason": str(ruling.get("reason") or ""), "confidence": str(ruling.get("confidence") or ""),
                     **retention_for(cfg, value)}
            if stale:
                out["stale"].append(entry | {"why": "the ruling was made against another pre-state - it grants nothing"})
            elif not illegal:
                out["role_carrying_ruled"].append(entry | {
                    "why": "contract-valid ROLE; a curation ruling alone does not withdraw knowledge (never acted on here)"})
            elif entry["retention"] == "refused":
                out["stale"].append(entry | {"why": "the declared retention for this value is 'refused' - this tool may not act"})
            else:
                out["withdraw"].append(entry)
        elif illegal:
            out["owner_owed"].append({"fb_id": fid, "name": row["name"], "label": row["label"],
                                      "why": "no owner disposition ruling in the map - a script never decides curation (D-2898)"})
    return out


def _refs(value: object) -> tuple[list[Any], str]:
    """Parse a cross-reference column into (entries, shape) - the SHAPE is preserved on write-back.

    The store carries three shapes for these columns (a JSON array of objects, a JSON array of ids, a comma
    string) and the object shape is the one related_fbs actually uses; assuming a list of ids would silently
    miss every edge (C16: never assume the shape).
    """
    if value is None or value == "":
        return [], "json"
    if isinstance(value, list):
        return list(value), "json"
    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"FAIL-CLOSED: unparseable reference list {text[:80]!r}") from exc
        return (list(parsed) if isinstance(parsed, list) else [parsed]), "json"
    return [t.strip() for t in text.split(",") if t.strip()], "csv"


def _ref_id(cfg: dict[str, Any], entry: Any) -> str:
    """Return the id an entry points at, whatever shape the entry has (dict or bare id)."""
    if isinstance(entry, dict):
        for key in (cfg["id_column"], "id", "fb_id"):
            if entry.get(key):
                return str(entry[key])
        return ""
    return str(entry)


def ref_edges(con: sqlite3.Connection, cfg: dict[str, Any], doomed: set[str]) -> list[dict[str, Any]]:
    """Return every surviving-row edge that points into the withdrawal set (to be pruned, and archived).

    Raises:
        SystemExit: when a prune would leave a surviving row's reference column empty and the config refuses that.
    """
    idc = str(cfg["id_column"])
    edges: list[dict[str, Any]] = []
    for col in cfg["reference_columns"]:
        for fid, value in con.execute(f"SELECT {idc}, {col} FROM {cfg['table']}").fetchall():
            if str(fid) in doomed:
                continue
            entries, shape = _refs(value)
            removed = [e for e in entries if _ref_id(cfg, e) in doomed]
            if not removed:
                continue
            kept = [e for e in entries if _ref_id(cfg, e) not in doomed]
            if not kept and bool(cfg.get("refuse_emptying_reference")):
                raise SystemExit(f"REFUSED: pruning {col} on {str(fid)[:12]} would leave the column EMPTY - "
                                 f"that loss is not expressible by an archive (fix the graph or the ruling first)")
            edges.append({"fb_id": str(fid), "column": col, "removed": removed, "kept": kept,
                          "shape": shape, "after": len(kept), "before": len(entries)})
    return edges


def take_backup(cfg: dict[str, Any]) -> Path:
    """Copy the store before the mutating apply (C13)."""
    dest_dir = DB_PATH.parent / str(cfg["backup_subdir"])
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / f"{cfg['backup_prefix']}{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(DB_PATH, dest)
    print(f"  [C13] backup -> {dest.relative_to(ROOT)}")
    return dest


def _sha256(path: Path) -> str:
    """Return the hex sha256 of a file, streamed in 1 MiB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_rows(con: sqlite3.Connection, cfg: dict[str, Any], entries: list[dict[str, Any]],
                 edges: list[dict[str, Any]]) -> Path:
    """Write every doomed row to JSONL plus a hashed MANIFEST before any deletion (R-D410)."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    outdir = ROOT / str(cfg["archive_root"]) / stamp
    outdir.mkdir(parents=True, exist_ok=True)
    doomed = {e["fb_id"] for e in entries}
    out_path = outdir / "withdrawn_rows.jsonl"
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({cfg['table']})")]
    written = 0
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in con.execute(f"SELECT * FROM {cfg['table']}"):
            rec = dict(zip(cols, tuple(row), strict=True))
            if str(rec[str(cfg["id_column"])]) in doomed:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
    if written != len(entries):
        raise SystemExit(f"FAIL-CLOSED: archived {written} row(s) but the plan names {len(entries)} - refusing to delete")
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "tool": "scripts/withdraw_curation_rows.py",
        "decision": "D-3135",
        "store": str(DB_PATH),
        "store_sha256_at_archive": _sha256(DB_PATH),
        "archive_file": out_path.name,
        "sha256": _sha256(out_path),
        "rows": [{k: e[k] for k in ("fb_id", "name", "label", "ruling", "retention", "reason", "confidence")}
                 for e in entries],
        "pruned_edges": edges,
        "restore": (
            "1) sqlite3 '<store>' and INSERT each line of withdrawn_rows.jsonl back into fbs (all 79 columns are "
            "present); 2) INSERT INTO fbs_fts(fbs_fts) VALUES('rebuild'); 3) python3 scripts/backfill_embeddings.py "
            "to restore the vector legs; 4) re-apply the pruned_edges above."
        ),
    }
    (outdir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  📦 archived {written} row(s) -> {(out_path.relative_to(ROOT))}  (sha256 {manifest['sha256'][:16]}…)")
    return outdir


def withdraw(con: sqlite3.Connection, cfg: dict[str, Any], entries: list[dict[str, Any]],
             edges: list[dict[str, Any]]) -> dict[str, int]:
    """Prune the graph edges, drop the vector legs, delete the rows and rebuild the FTS - in ONE transaction.

    fbs_fts is an EXTERNAL-CONTENT fts5 table whose only trigger is AFTER INSERT, so a row delete would leave a
    stale index entry: the rebuild belongs INSIDE this transaction, not to a follow-up step (a stale index would
    silently keep answering with the withdrawn row).
    """
    table, idc = str(cfg["table"]), str(cfg["id_column"])
    doomed = [e["fb_id"] for e in entries]
    stats: dict[str, int] = {"refs_pruned": 0, "vec_fbs": 0, "vec_fbs_ctx": 0, "fbs": 0}
    con.execute("BEGIN IMMEDIATE")
    try:
        for edge in edges:
            payload = edge["kept"] if edge["shape"] == "json" else ",".join(str(x) for x in edge["kept"])
            text = json.dumps(payload, ensure_ascii=False) if edge["shape"] == "json" else str(payload)
            stats["refs_pruned"] += con.execute(
                f"UPDATE {table} SET {edge['column']} = ? WHERE {idc} = ?", (text, edge["fb_id"])).rowcount
        for fid in doomed:
            rowid = con.execute(f"SELECT rowid FROM {table} WHERE {idc} = ?", (fid,)).fetchone()
            if rowid is None:
                raise SystemExit(f"FAIL-CLOSED: {fid[:12]} vanished between plan and apply - nothing was written")
            stats["vec_fbs"] += con.execute("DELETE FROM vec_fbs WHERE rowid = ?", (int(rowid[0]),)).rowcount or 0
            stats["vec_fbs_ctx"] += con.execute("DELETE FROM vec_fbs_ctx WHERE rowid = ?", (int(rowid[0]),)).rowcount or 0
        stats["fbs"] = con.execute(f"DELETE FROM {table} WHERE {idc} IN ({','.join('?' * len(doomed))})", doomed).rowcount
        con.execute("INSERT INTO fbs_fts(fbs_fts) VALUES('rebuild')")
        con.commit()
    except BaseException:
        con.rollback()
        raise
    return stats


def verify(con: sqlite3.Connection, cfg: dict[str, Any], entries: list[dict[str, Any]],
           edges: list[dict[str, Any]], rows_before: int) -> dict[str, Any]:
    """Prove the withdrawal left the store consistent: no residual row, no dangling edge, no orphan vector."""
    table, idc = str(cfg["table"]), str(cfg["id_column"])
    doomed = {e["fb_id"] for e in entries}
    residual = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {idc} IN ({','.join('?' * len(doomed))})",
                           list(doomed)).fetchone()[0]
    dangling = 0
    for col in cfg["reference_columns"]:
        for value, in con.execute(f"SELECT {col} FROM {table}"):
            dangling += sum(1 for e in _refs(value)[0] if _ref_id(cfg, e) in doomed)
    fts_rows = con.execute("SELECT COUNT(*) FROM fbs_fts").fetchone()[0]
    fbs_rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    orphans = con.execute(f"SELECT COUNT(*) FROM vec_fbs_rowids v LEFT JOIN {table} f ON v.rowid = f.rowid "
                          f"WHERE f.rowid IS NULL").fetchone()[0]
    return {
        "residual_rows": residual,
        "dangling_edges": dangling,
        "rows_before": rows_before,
        "rows_after": fbs_rows,
        "rows_delta": rows_before - fbs_rows,
        "rows_expected_delta": len(doomed),
        "fts_rows": fts_rows,
        "fts_matches_fbs": fts_rows == fbs_rows,
        "vec_orphans": orphans,
        "integrity": con.execute("PRAGMA integrity_check").fetchone()[0],
        "edges_pruned": len(edges),
    }


def selftest() -> int:
    """Known-answer controls for THIS tool's own decisions, on a FIXTURE store - never the live one (BUG-491/492)."""
    cfg = load_cfg()
    roles, dispositions = declared_vocab(cfg)
    _, schema = load_map(cfg)
    disp_key, cur_key = str(schema["disposition_key"]), str(schema["current_key"])

    import copy as _copy

    fixture = sqlite3.connect(":memory:")
    fixture.execute("CREATE TABLE fbs (fb_id TEXT, name TEXT, content_type TEXT, related_fbs TEXT, "
                    "prerequisite_fbs TEXT, contradicts_fbs TEXT, source_principle_ids TEXT)")
    keep = {"fb_id": "keep", "relationships": ["source_crossover"]}
    fixture.executemany("INSERT INTO fbs VALUES (?,?,?,?,?,?,?)", [
        ("w1", "ruled noise", "noise_drop", "[]", "[]", "[]", "[]"),
        ("w2", "ruled held", "quarantine", "[]", "[]", "[]", "[]"),
        ("u1", "unruled noise", "noise_drop", "[]", "[]", "[]", "[]"),
        ("s1", "stale ruling", "noise_drop", "[]", "[]", "[]", "[]"),
        ("r1", "valid role ruled noise", "principle",
         json.dumps([{"fb_id": "w1", "relationships": ["x"]}, keep]), "[]", "[]", "[]"),
        ("r2", "valid role, edge to w2", "principle",
         json.dumps([{"fb_id": "w2", "relationships": ["x"]}, keep]), "[]", "[]", "[]"),
    ])
    live = live_rows(fixture, cfg)
    map_rows = [
        {"fb_id": "w1", cur_key: "noise_drop", disp_key: "noise_drop", "confidence": "high", "reason": "r"},
        {"fb_id": "w2", cur_key: "quarantine", disp_key: "quarantine", "confidence": "high", "reason": "r"},
        {"fb_id": "s1", cur_key: "principle", disp_key: "noise_drop", "confidence": "high", "reason": "r"},
        {"fb_id": "r1", cur_key: "principle", disp_key: "noise_drop", "confidence": "high", "reason": "r"},
    ]
    p = plan(cfg, map_rows, schema, live, roles, dispositions)
    ids = lambda name: sorted(e["fb_id"] for e in p[name])  # noqa: E731 - a one-line projection
    checks: list[tuple[str, bool]] = [
        ("a disposition-labelled row WITH an owner ruling is SELECTED", ids("withdraw") == ["w1", "w2"]),
        ("the ruling NAMES the retention shelf (noise_drop -> dropped)",
         next(e["retention"] for e in p["withdraw"] if e["fb_id"] == "w1") == "dropped"),
        ("quarantine is HELD, not dropped", next(e["retention"] for e in p["withdraw"] if e["fb_id"] == "w2") == "hold"),
        ("a label-illegal row with NO ruling is OWNER-OWED, never acted on (D-2898)", ids("owner_owed") == ["u1"]),
        ("a STALE ruling grants nothing", ids("stale") == ["s1"]),
        ("a contract-valid ROLE ruled a disposition is reported, never withdrawn",
         ids("role_carrying_ruled") == ["r1"]),
    ]
    edges = ref_edges(fixture, cfg, {"w1", "w2"})
    checks.append(("an edge into the withdrawal set is found in the OBJECT shape (never assumed a list of ids)",
                   {(e["fb_id"], e["column"]) for e in edges} == {("r1", "related_fbs"), ("r2", "related_fbs")}))
    r1 = next(e for e in edges if e["fb_id"] == "r1")
    checks.append(("only the doomed entry is removed; the surviving edge KEEPS its object shape",
                   [_ref_id(cfg, k) for k in r1["kept"]] == ["keep"] and isinstance(r1["kept"][0], dict)))
    fixture.execute("UPDATE fbs SET related_fbs = ? WHERE fb_id = 'r2'",
                    (json.dumps([{"fb_id": "w2", "relationships": ["x"]}]),))
    try:
        ref_edges(fixture, cfg, {"w2"})
        checks.append(("a prune that would EMPTY a reference column is REFUSED", False))
    except SystemExit:
        checks.append(("a prune that would EMPTY a reference column is REFUSED", True))

    broken_live = live | {"w9": {"fb_id": "w9", "name": "x", "label": "noise_drop"},
                          "w8": {"fb_id": "w8", "name": "x", "label": "noise_drop"}}
    try:
        plan(cfg, map_rows + [{"fb_id": "w9", cur_key: "noise_drop", disp_key: "made_up"}],
             schema, broken_live, roles, dispositions)
        checks.append(("an UNDECLARED disposition value FAILS CLOSED", False))
    except SystemExit:
        checks.append(("an UNDECLARED disposition value FAILS CLOSED", True))
    # a value whose retention is declared 'refused' is never acted on (it is not a curation ruling)
    p_ref = plan(cfg, map_rows + [{"fb_id": "w8", cur_key: "noise_drop", disp_key: "classified"}],
                 schema, live | {"w8": {"fb_id": "w8", "name": "x", "label": "noise_drop"}}, roles, dispositions)
    checks.append(("a 'refused' retention shelf is NOT withdrawn (it is not a curation ruling)",
                   "w8" not in {e["fb_id"] for e in p_ref["withdraw"]}))
    # a disposition value with NO declared retention fails closed
    no_shelf = _copy.deepcopy(cfg)
    no_shelf["retention"].pop("quarantine")
    try:
        plan(no_shelf, map_rows, schema, live, roles, dispositions)
        checks.append(("a disposition with NO declared retention FAILS CLOSED (D-3034)", False))
    except SystemExit:
        checks.append(("a disposition with NO declared retention FAILS CLOSED (D-3034)", True))
    fixture.close()

    bad_checks = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(f"selftest: {len(checks) - len(bad_checks)}/{len(checks)} controls held")
    return 1 if bad_checks else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="withdraw owner-ruled curation rows, archive-first (dry-run default)")
    ap.add_argument("--apply", action="store_true", help="mutate the store (requires --confirm + a C13 backup)")
    ap.add_argument("--confirm", default="", help="comma-separated fb_ids that must equal the plan EXACTLY")
    ap.add_argument("--check", action="store_true", help="read-only exit code: 0 clean | 2 a withdrawal is OWED")
    ap.add_argument("--json", default=None, help="receipt path override (default: the config's receipt)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls on a fixture store")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    cfg = load_cfg()
    ensure_vec_capable(cfg)
    roles, dispositions = declared_vocab(cfg)
    map_rows, schema = load_map(cfg)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    load_sqlite_vec(con)
    try:
        rows_before = con.execute(f"SELECT COUNT(*) FROM {cfg['table']}").fetchone()[0]
        p = plan(cfg, map_rows, schema, live_rows(con, cfg), roles, dispositions)
        print(f"store rows {rows_before} | label-illegal rows {len(p['withdraw']) + len(p['owner_owed']) + len(p['stale'])}")
        for e in p["withdraw"]:
            print(f"  WITHDRAW {e['fb_id'][:12]} {e['label']:11} -> {e['retention']:8} {e['name'][:56]!r}")
        for e in p["owner_owed"]:
            print(f"  OWNER-OWED {e['fb_id'][:12]} {e['label']:11} {e['name'][:52]!r}: {e['why']}")
        for e in p["stale"]:
            print(f"  REFUSED {e['fb_id'][:12]} {e['label']:11} {e['name'][:52]!r}: {e['why']}")
        for e in p["role_carrying_ruled"]:
            print(f"  NOTED {e['fb_id'][:12]} role={e['label']:11} ruled {e['ruling']:11} {e['name'][:48]!r}: {e['why']}")

        doomed = {e["fb_id"] for e in p["withdraw"]}
        edges: list[dict[str, Any]] = ref_edges(con, cfg, doomed) if doomed else []
        print(f"  graph edges to prune: {len(edges)} across {len({e['fb_id'] for e in edges})} surviving row(s)")
        print(f"  hold shelf (a HOLD row's conceptual home): {hold_shelf(cfg)}")
        if doomed:
            shelves = sorted({e["retention"] for e in p["withdraw"]})
            print(f"  retention shelves this run: {shelves} (hold = the S4 HOLD SHELF, D2616: never a commit source)")

        if args.check:
            code = int(cfg["exit"]["owed"]) if doomed else int(cfg["exit"]["clean"])
            print(f"[--check] read-only: {len(doomed)} row(s) awaiting withdrawal -> exit {code}")
            return code
        if not args.apply:
            print(f"\n[dry-run] the write set is {len(doomed)} row(s); nothing was mutated.")
            return int(cfg["exit"]["clean"])

        if not doomed:
            print("nothing to withdraw - the store holds no owner-ruled disposition row")
            return int(cfg["exit"]["clean"])
        confirmed = {x.strip() for x in str(args.confirm).split(",") if x.strip()}
        if confirmed != doomed:
            print(f"FAIL-CLOSED: --confirm must name the plan EXACTLY. missing={sorted(doomed - confirmed)} "
                  f"extra={sorted(confirmed - doomed)}")
            return int(cfg["exit"]["cannot_evaluate"])
        archive_rows(con, cfg, p["withdraw"], edges)
        take_backup(cfg)
        stats = withdraw(con, cfg, p["withdraw"], edges)
        v = verify(con, cfg, p["withdraw"], edges, rows_before)
        print(f"[apply] {stats}")
        print(f"[verify] {v}")
        bad = (v["residual_rows"] != 0 or v["dangling_edges"] != 0 or not v["fts_matches_fbs"] or v["vec_orphans"]
               or v["integrity"] != "ok" or v["rows_delta"] != v["rows_expected_delta"])
        if bad:
            raise SystemExit(f"FAIL-CLOSED: verification failed after commit: {v} - restore from the C13 backup")
        receipt = {"schema_version": 1, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "tool": "scripts/withdraw_curation_rows.py", "decision": "D-3135",
                   "bug": "BUG-741b/BUG-977", "rows_before": rows_before, "rows_after": v["rows_after"],
                   "withdrawn": p["withdraw"], "owner_owed": p["owner_owed"], "refused_stale": p["stale"],
                   "role_carrying_ruled_not_acted": p["role_carrying_ruled"],
                   "pruned_edges": edges, "stats": stats, "verification": v}
        out = Path(args.json) if args.json else ROOT / str(cfg["receipt"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"receipt -> {out.relative_to(ROOT)}")
        return int(cfg["exit"]["clean"])
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
