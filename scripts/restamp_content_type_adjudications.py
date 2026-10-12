#!/usr/bin/env python3
"""scripts/restamp_content_type_adjudications.py - the BUG-712 retro re-stamp GATE (dry-run by default).

WHY. Two fixes landed (the producer persists the resolved content_type; the tier-2 tension test is calibrated and
ENABLED), and what remains of BUG-712 is a GOVERNED WRITE: rows already in the store whose label the owner has
since adjudicated. This tool exists so that write is a MEASURED JOIN of two declared homes - the owner's
adjudication map and the store's live pre-state - instead of a hand-typed list or a wholesale map replay.

THE WRITE SET IS A JOIN, NOT A MAP REPLAY (MEASURED 2026-10-12): of the map's 546 rows, 527 do not resolve to the
live store, 7 already hold their proposed value, 0 are stale and 12 are applicable. A map replay would report
"546 applied" while moving 12 cells; this tool reports the four buckets SEPARATELY and names the refused ids.

THE WARRANT RULE. A router PREDICTION alone never writes: the calibrated router would move 14 rows and 2 of them
are 50% precise at n=2 (BUG-735); only an owner warrant moves a label. The map is the warrant, the router diff
(scripts/diff_bug712_reroute.py, the ONE router consumer) is CONTEXT for the owner, not a grant.

REFUSALS, each fail-closed and each named in the receipt:
  * DISPOSITION destination - `noise_drop`/`quarantine` are DISPOSITIONS, not content types (BUG-741): writing one
    as a content_type mints a value the schema does not declare. Escalated as an owner ruling.

D-2967 (BUG-741, 2026-10-12). THE DESTINATION IS SPLIT BY VOCABULARY: a map row carries exactly one of
`proposed_content_type` (a declared role) or `proposed_disposition` (a declared disposition), so a disposition can
never be read as a content_type BY CONSTRUCTION rather than by a membership test that has to remember the
difference. The two keys are declared in ONE home (config/content_types.yaml#adjudication_map) and this gate READS
them there instead of restating them. MEASURED CONSEQUENCE of the old conflated key, fixed in the same change:
the ROUTER's tier 1 (pipeline/content_types.py::_load_adjudication_map) admitted `CONTENT_TYPES_ALL` - which
INCLUDES the two dispositions - so it returned a DISPOSITION as a role for 375 of the 542 entries it admitted,
which the D-2938 persist flag would write into the FB checkpoint and the D-2965 leaf gate would then refuse at S6,
where stage6.max_failed_ratio 0.0 turns ONE refused row into a HALTED commit.

BUG-741(b), THE GENERAL CASE, IS DECLARED AND LOUD RATHER THAN SILENT. A disposition ruling on a row that is IN
the store splits in two:
  * NOT served -> bucket `disposition`: the ruling is ALREADY TRUE (measured 2026-10-12: the one applicable
    disposition row's stored state is not in the default answer path), so the store owes nothing.
  * SERVED -> bucket `disposition_served`: BLOCKING (exit 1). The store has no home for the ruling - `status` is a
    VERIFICATION verdict, not a curation decision (BUG-499 drift class), and a disposition COLUMN has no writer
    (D-2952/C28) - so the act declared in config (`dispositions.act_for_stored_row`) is OWED and named by id.
"whether this row is served" is ANSWERED BY THE SERVING LAYER'S OWN predicate (pipeline/retrieve.py, D2330), never
by a copy of `status = 'PASS'` here: a copy would be a second home for the serving contract (C21).
  * UNKNOWN destination - neither a declared content_type nor a declared disposition: the map is not interpretable.
  * STALE warrant - the live label no longer equals the map's `current`: the adjudication was made against a
    pre-state that has since moved, so it grants nothing.

WRITES are C13-backed (backup first), take ONE BEGIN IMMEDIATE, and are RE-READ afterwards: a cell that did not
take is a failure, not a note (C16). --apply REFUSES while the authorship value is a sentinel (BUG-742).

Exit: 0 the queue is exactly what the receipt says | 1 a ruling is OWED (loud) | 2 cannot evaluate.
Usage: python3 scripts/restamp_content_type_adjudications.py [--apply] [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402 - the ONE home for the store path (C12)

CONFIG = ROOT / "config" / "content_type_restamp.yaml"
SENTINEL = "OWNER_RULING_OWED"


def load_config() -> dict[str, Any]:
    """Load the gate's declarations; a missing or partial config is a DEFECT, not an empty config (C16)."""
    if not CONFIG.exists():
        raise SystemExit(f"FAIL-CLOSED: {CONFIG.relative_to(ROOT)} is absent - a gate with no declarations is not a gate")
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    for key in ("map_schema_home", "label_column", "provenance_column", "provenance_value", "receipt",
                "vocab_home", "table", "id_column", "dispositions"):
        if not str(cfg.get(key) or "").strip():
            raise SystemExit(f"FAIL-CLOSED: {CONFIG.relative_to(ROOT)} is missing '{key}' - the gate cannot state what it acts on")
    return cfg


def load_schema(cfg: dict[str, Any]) -> dict[str, Any]:
    """Load the adjudication map's SCHEMA from its ONE home (config/content_types.yaml#adjudication_map).

    The map's path and its destination keys are declared ONCE (D-2967/BUG-741). This gate needs them to find its
    input and to tell a role from a disposition, and the ROUTER needs the same keys to read tier 1 - so restating
    them here would let a rename leave one reader looking at a key the writer no longer produces. A missing block
    is a DEFECT, never an empty default (C16).
    """
    home, _, keypath = str(cfg["map_schema_home"]).partition("#")
    if not keypath:
        raise SystemExit(f"FAIL-CLOSED: map_schema_home '{cfg['map_schema_home']}' names no block (expected <file>#<key>)")
    doc = yaml.safe_load((ROOT / home).read_text(encoding="utf-8")) or {}
    schema = doc.get(keypath)
    if not isinstance(schema, dict):
        raise SystemExit(f"FAIL-CLOSED: {cfg['map_schema_home']} is not a mapping - the gate cannot find the warrant map")
    for key in ("path", "rows_key", "current_key", "role_key", "disposition_key"):
        if not str(schema.get(key) or "").strip():
            raise SystemExit(f"FAIL-CLOSED: {cfg['map_schema_home']} is missing '{key}'")
    return schema


def declared_vocab(cfg: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return (content_types, dispositions) READ from their one home - never restated in this file (D-2646)."""
    doc = yaml.safe_load((ROOT / str(cfg["vocab_home"])).read_text(encoding="utf-8")) or {}
    types: set[str] = set()
    for key in cfg.get("vocab_type_keys") or []:
        types |= {str(k) for k in (doc.get(key) or {})}
    dispositions: set[str] = set()
    for key in cfg.get("vocab_disposition_keys") or []:
        dispositions |= {str(k) for k in (doc.get(key) or {})}
    if not types or not dispositions:
        raise SystemExit(f"FAIL-CLOSED: {cfg['vocab_home']} yielded content_types={sorted(types)} dispositions={sorted(dispositions)}")
    return types, dispositions


def load_map(cfg: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Load the owner's adjudication map - the WARRANT. Rows that are not mappings are refused, not skipped."""
    doc = json.loads((ROOT / str(schema["path"])).read_text(encoding="utf-8"))
    rows = doc.get(str(schema["rows_key"]))
    if not isinstance(rows, list):
        raise SystemExit(f"FAIL-CLOSED: {schema['path']}#{schema['rows_key']} is not a list")
    return [r for r in rows if isinstance(r, dict)]


def served_ids(con: sqlite3.Connection, cfg: dict[str, Any], ids: list[str]) -> set[str]:
    """The ids the SERVING layer would place in the DEFAULT answer path - asked of its OWN home.

    D2330's predicate lives in pipeline/retrieve.py; a copy of `status = 'PASS'` here would be a second home for
    the serving contract (C21) and the two would be free to drift. Imported lazily: this gate needs the predicate,
    not the retrieval stack.
    """
    from pipeline.retrieve import (
        _status_predicate,  # noqa: PLC0415 - the serving layer owns this predicate
    )

    cur, out = con.cursor(), set()
    for i in range(0, len(ids), 400):
        part = ids[i:i + 400]
        sql = (f"SELECT {cfg['id_column']} FROM {cfg['table']} "
               f"WHERE {cfg['id_column']} IN ({','.join('?' * len(part))}) AND ({_status_predicate(False)})")
        out |= {str(r[0]) for r in cur.execute(sql, part)}
    return out


def live_state(con: sqlite3.Connection, cfg: dict[str, Any], ids: list[str]) -> dict[str, dict[str, Any]]:
    """Return {id: row} for the ids the map names, straight from the store (the PRE-STATE the warrant was made against)."""
    cur = con.cursor()
    out: dict[str, dict[str, Any]] = {}
    chunk = 400
    for i in range(0, len(ids), chunk):
        part = ids[i:i + chunk]
        sql = (f"SELECT {cfg['id_column']}, {cfg['label_column']}, {cfg['provenance_column']} "
               f"FROM {cfg['table']} WHERE {cfg['id_column']} IN ({','.join('?' * len(part))})")
        for row in cur.execute(sql, part):
            out[str(row[0])] = {cfg["label_column"]: row[1], cfg["provenance_column"]: row[2]}
    return out


def classify(cfg: dict[str, Any], schema: dict[str, Any], rows: list[dict[str, Any]],
             live: dict[str, dict[str, Any]], types: set[str], served: set[str]) -> dict[str, list[dict[str, Any]]]:
    """Bucket every map row; nothing is dropped and every refusal carries its reason (C16).

    D-2967 (BUG-741a): the destination is read from the SPLIT keys, so a DISPOSITION can never be read as a
    content_type BY CONSTRUCTION rather than by a membership test that has to remember the difference.
    D-2967 (BUG-741b): a disposition row then splits by whether the store ALREADY satisfies the ruling -
    NOT served -> `disposition` (the ruling is already true, nothing is owed), SERVED -> `disposition_served`
    (BLOCKING: the act declared in config is owed, and the gate names the id rather than absorbing it).
    """
    cur_key = str(schema["current_key"])
    role_key, disp_key = str(schema["role_key"]), str(schema["disposition_key"])
    label = str(cfg["label_column"])
    out: dict[str, list[dict[str, Any]]] = {k: [] for k in
        ("apply", "already", "absent", "stale", "disposition", "disposition_served", "unknown")}
    for r in rows:
        rid, current = str(r.get("fb_id")), str(r.get(cur_key) or "")
        role, disposition = str(r.get(role_key) or "").strip(), str(r.get(disp_key) or "").strip()
        entry = {"fb_id": rid, "current": current, "proposed": role or disposition,
                 "destination_kind": "content_type" if role else "disposition",
                 "warrant": str(r.get(str(cfg.get("map_warrant_key") or "confidence")) or ""),
                 "reason": str(r.get("reason") or "")}
        row = live.get(rid)
        if row is None:
            out["absent"].append(entry)
            continue
        got = str(row.get(label) or "")
        if disposition:
            out["disposition_served" if rid in served else "disposition"].append(entry)
        elif role not in types:
            out["unknown"].append(entry)
        elif got == role:
            out["already"].append(entry)
        elif got != current:
            entry["live"] = got
            out["stale"].append(entry)
        else:
            out["apply"].append(entry)
    return out


def apply_rows(con: sqlite3.Connection, cfg: dict[str, Any], entries: list[dict[str, Any]], value: str) -> int:
    """Write label + provenance for every granted row inside ONE transaction; return the number written."""
    cur = con.cursor()
    for e in entries:
        cur.execute(f"UPDATE {cfg['table']} SET {cfg['label_column']}=?, {cfg['provenance_column']}=? "
                    f"WHERE {cfg['id_column']}=? AND {cfg['label_column']}=?",
                    (e["proposed"], value, e["fb_id"], e["current"]))
        if cur.rowcount != 1:
            raise SystemExit(f"FAIL-CLOSED: {e['fb_id'][:12]} was not in its adjudicated pre-state "
                             f"({e['current']}) - the warrant did not hold at write time; transaction rolled back")
    return len(entries)


def verify(con: sqlite3.Connection, cfg: dict[str, Any], entries: list[dict[str, Any]], value: str) -> list[str]:
    """Re-read every written cell; a cell that did not take is a FAILURE, never a note (C16)."""
    cur = con.cursor()
    bad: list[str] = []
    for e in entries:
        row = next(cur.execute(f"SELECT {cfg['label_column']}, {cfg['provenance_column']} FROM {cfg['table']} "
                               f"WHERE {cfg['id_column']}=?", (e["fb_id"],)), None)
        if row is None or str(row[0]) != e["proposed"] or str(row[1]) != value:
            bad.append(str(e["fb_id"]))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description="BUG-712 governed re-stamp gate (dry-run by default)")
    ap.add_argument("--apply", action="store_true", help="write (default is dry-run: nothing is mutated)")
    ap.add_argument("--json", default=None, help="receipt path override (default: the config's receipt)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls for this gate's OWN decisions (BUG-492)")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    cfg = load_config()
    schema = load_schema(cfg)
    types, dispositions = declared_vocab(cfg)
    rows = load_map(cfg, schema)
    con = sqlite3.connect(DB_PATH)
    try:
        ids = [str(r.get("fb_id")) for r in rows]
        live = live_state(con, cfg, ids)
        served = served_ids(con, cfg, ids)
        buckets = classify(cfg, schema, rows, live, types, served)
        print(f"map rows {len(rows)} | resolve to store {len(rows) - len(buckets['absent'])} | "
              f"declared content_types {sorted(types)} | dispositions {sorted(dispositions)}")
        for name in ("apply", "already", "absent", "stale", "disposition", "disposition_served", "unknown"):
            print(f"  {name:18} {len(buckets[name])}")
        for name in ("stale", "unknown"):
            for e in buckets[name][:12]:
                print(f"    REFUSED {name}: {e['fb_id'][:12]} {e.get('current')} -> {e['proposed']} "
                      f"(kind={e['destination_kind']}, live={e.get('live', '-')}, warrant={e['warrant']})")
        # A DISPOSITION is not a REFUSAL: this gate cannot write it into content_type (it is not a role), and
        # whether anything is OWED depends on the store, so the two states are printed apart (D-2967/BUG-741b).
        for e in buckets["disposition"][:12]:
            print(f"    NOT OWED {e['fb_id'][:12]} {e.get('current')} -> {e['proposed']} (kind=disposition): the "
                  f"ruling's practical content is ALREADY TRUE - the row is not in the served path, so nothing is written")
        for e in buckets["disposition_served"][:12]:
            print(f"    BLOCKING {e['fb_id'][:12]} {e.get('current')} -> {e['proposed']} (kind=disposition): SERVED, "
                  f"so the declared act is OWED - the store has no home for a curation ruling")
        if buckets["disposition_served"]:
            disp = cfg.get("dispositions") or {}
            print(f"    BLOCKING (BUG-741b): {len(buckets['disposition_served'])} disposition-ruled row(s) ARE in the "
                  f"served path - the act '{disp.get('act_for_stored_row')}' is OWED (writer: {disp.get('writer')}). "
                  f"The store has no home for a curation ruling: status is a VERIFICATION verdict (BUG-499 class).")
        value = str(cfg["provenance_value"])
        owed = value == SENTINEL
        receipt = {
            "schema_version": 1, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "tool": "scripts/restamp_content_type_adjudications.py",
            "map": str(schema["path"]), "store_rows_resolved": len(rows) - len(buckets["absent"]),
            "counts": {k: len(v) for k, v in buckets.items()},
            "apply_ids": [e["fb_id"] for e in buckets["apply"]],
            "refused": {k: buckets[k] for k in ("stale", "disposition", "disposition_served", "unknown")},
            "disposition_act": str((cfg.get("dispositions") or {}).get("act_for_stored_row") or ""),
            "disposition_writer": str((cfg.get("dispositions") or {}).get("writer") or ""),
            "provenance_value": value, "provenance_ruling_owed": owed,
            "applied": 0, "wrote": False,
        }
        if not args.apply:
            print(f"\n[dry-run] the write set is {len(buckets['apply'])} row(s); nothing was mutated. "
                  f"Authorship value for an owner-adjudicated label: {'OWED (BUG-742)' if owed else value}.")
        else:
            reason = apply_gate(value)
            if reason:
                print(reason)
                return int((cfg.get("exit") or {}).get("refused", 1))
            if not buckets["apply"]:
                print("nothing to apply - the store already holds every adjudicated value")
            else:
                bak = DB_PATH.parent / str(cfg["backup_subdir"])
                bak.mkdir(exist_ok=True)
                target = bak / f"{cfg['backup_prefix']}{time.strftime('%Y%m%d_%H%M%S')}"
                print(f"[C13] backup -> {target.relative_to(ROOT)}")
                shutil.copy2(DB_PATH, target)
                con.execute("BEGIN IMMEDIATE")
                try:
                    n = apply_rows(con, cfg, buckets["apply"], value)
                    con.commit()
                except BaseException:
                    con.rollback()
                    raise
                bad = verify(con, cfg, buckets["apply"], value)
                if bad:
                    raise SystemExit(f"FAIL-CLOSED: {len(bad)} cell(s) did not take after commit: {bad[:5]} - investigate before proceeding")
                receipt["applied"], receipt["wrote"] = n, True
                print(f"[apply] wrote {n} label(s) + provenance '{value}' and RE-READ every cell: all took")
        out = Path(args.json) if args.json else ROOT / str(cfg["receipt"])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"receipt -> {out.relative_to(ROOT)}")
        # A NOT-served disposition row is NOT a refusal: an inert RED is as uninformative as a green lie, so
        # only a refusal and a SERVED disposition (the owed act) hold the exit code at "ruling OWED".
        refused = sum(len(buckets[k]) for k in ("stale", "disposition_served", "unknown"))
        return int((cfg.get("exit") or {}).get("refused", 1)) if refused else int((cfg.get("exit") or {}).get("clean", 0))
    finally:
        con.close()


def apply_gate(value: str) -> str | None:
    """Return the REFUSAL reason if --apply must not run for this authorship value, else None (BUG-742)."""
    if value == SENTINEL:
        return ("FAIL-CLOSED: --apply refused - the authorship value is the sentinel " + SENTINEL
                + " (BUG-742). The owner names the value; a label written without its true authorship is a "
                "provenance lie (the BUG-725 class, inverted).")
    return None


def selftest() -> int:
    """Known-answer controls for this gate's OWN decisions (BUG-492: a control nothing runs is a comment).

    The controls hand classify() a synthetic warrant map and a synthetic pre-state, so they assert the RULES -
    a granted row is granted, a row whose live label MOVED is refused rather than overwritten, a DISPOSITION is
    never written as a content_type (BUG-741a), a disposition-ruled row that IS served BLOCKS while one that is NOT
    served owes nothing (BUG-741b), an undeclared destination is refused, a row absent from the store is REPORTED
    and never dropped, a row already at its destination value is not re-applied, and the declared disposition act
    is NAMED rather than implied. No store is touched.
    """
    cfg = load_config()
    schema = load_schema(cfg)
    types, dispositions = declared_vocab(cfg)
    label, prov = str(cfg["label_column"]), str(cfg["provenance_column"])

    def live_row(ct: str) -> dict[str, Any]:
        return {label: ct, prov: "llm_extracted_from_source"}

    # NOTE (found BY these controls, 2026-10-12): "moved" must hold a value that is neither the map's pre-state
    # NOR the proposed value. A live label that already EQUALS the proposed value is correctly bucketed as
    # ALREADY-AT-PROPOSED (it needs no warrant at all), so a fixture that reuses the proposed value tests the
    # wrong branch - the ordering (already before stale) is the rule, not a bug.
    role_key, disp_key = str(schema["role_key"]), str(schema["disposition_key"])
    live = {"granted": live_row("tool_instruction"), "moved": live_row("growth_edge"),
            "disposed": live_row("principle"), "served_disposed": live_row("principle"),
            "undeclared": live_row("principle"), "stable": live_row("tool_instruction")}
    rows = [
        {"fb_id": "granted", "current": "tool_instruction", role_key: "principle", "confidence": "high"},
        {"fb_id": "moved", "current": "tool_instruction", role_key: "principle", "confidence": "high"},
        {"fb_id": "disposed", "current": "principle", disp_key: "noise_drop", "confidence": "high"},
        {"fb_id": "served_disposed", "current": "principle", disp_key: "noise_drop", "confidence": "high"},
        {"fb_id": "undeclared", "current": "principle", role_key: "made_up_type", "confidence": "high"},
        {"fb_id": "stable", "current": "tool_instruction", role_key: "tool_instruction", "confidence": "high"},
        {"fb_id": "gone", "current": "tool_instruction", role_key: "principle", "confidence": "high"},
    ]
    b = classify(cfg, schema, rows, live, types, served={"served_disposed"})
    ids = lambda name: [e["fb_id"] for e in b[name]]  # noqa: E731 - a one-line projection, not a rule

    checks: list[tuple[str, bool]] = [
        ("a granted row (live == the map's pre-state) is APPLIED", ids("apply") == ["granted"]),
        ("a row whose live label MOVED is refused as STALE, never overwritten", ids("stale") == ["moved"]),
        ("a DISPOSITION is never written as a content_type (BUG-741a)", ids("disposition") == ["disposed"]),
        ("a disposition row NOT in the served path owes nothing (ruling already true)", ids("disposition") == ["disposed"]),
        ("a disposition row IN the served path BLOCKS, by id (BUG-741b)", ids("disposition_served") == ["served_disposed"]),
        ("an UNDECLARED destination is refused (fail closed)", ids("unknown") == ["undeclared"]),
        ("a row ABSENT from the store is reported, never silently dropped", ids("absent") == ["gone"]),
        ("a row already at its destination value is NOT re-applied", ids("already") == ["stable"]),
        ("the authorship SENTINEL keeps --apply closed (BUG-742)", apply_gate(SENTINEL) is not None),
        ("a NAMED authorship value opens --apply", apply_gate("owner_adjudication") is None),
        ("the disposition ACT is DECLARED, not implied (BUG-741b)",
         str((cfg.get("dispositions") or {}).get("act_for_stored_row") or "") != ""),
        ("the act is not expressed through the verification verdict (BUG-499 class)",
         str((cfg.get("dispositions") or {}).get("act_for_stored_row") or "") != "status"),
    ]
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    print("selftest: " + str(len(checks) - len(bad)) + "/" + str(len(checks)) + " controls held")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
