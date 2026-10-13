#!/usr/bin/env python3
"""scripts/apply_relabel_store_write.py - T-103 / D-2988: the LICENSED store write for OWNER-RULED labels.

WHY THIS EXISTS. Five units of the D-2976/D-2977 review (4 CORRECT, 1 ABSTAIN) already carry an OWNER ruling and
the plan renders them as OWED to a licensed store pass: `scripts/apply_relabel_rulings.py` applies the CONFIRM
half only, because a canonical relabel is a STORE WRITE and D-2898 forbids an agent minting a LABEL. The owner
word that licenses it lives in the ONE home: config/relabel_rulings.yaml#store_write_license.

WHAT THE WRITE IS, ONTOLOGICALLY. It is NOT a re-classification. It copies the PRODUCTION MAPPER's own answer
(the ONE home: `_map_discipline` of scripts/audit_menu_rescope_cohort.py - the same function the packet's
`live_mapper_says` column came from) into the store for rows an OWNER RULING already reaches, so the stored
canonical becomes REPRODUCIBLE from the row's own raw label (R14). Every row's new value must therefore be
TRIPLY agreed: the mapper's answer == the owner's ruling == the packet's recorded mapper answer.

WHAT IT WRITES - four columns of `fbs`, for LICENSED fb_ids only:
    discipline            <- the triply agreed target
    discipline_macro      <- pipeline.discipline_macro.macro_for (D-2884a: the ONE fine->macro collapse home)
    discipline_source     <- the C29 tier the LICENSE declares (a PROVENANCE_LITERAL member)
    taxonomy_match_method <- the S4 method rule (pipeline/stage4_merge.run_stage4, the raw->canonical block):
                             the declared ABSENCE when the mapper returns it, 'exact' when the mapper returns
                             the raw verbatim, else 'synonym'. The token set stays the S4 vocabulary, which is
                             what the store's own `taxonomy_match_method` declaration measures (3 distinct).
WHAT IT NEVER TOUCHES: `discipline_raw` (the raw IS the provenance), `menu_hash` (a relabel moves no menu), and
ANY row outside the licensed set. THE SCOPE IS BY fb_id, NEVER BY A PREDICATE: a predicate over the raw label
would sweep in rows no owner ruling reaches - the difference between executing a decision and minting one.

FAIL-CLOSED (C16). Each guard is NAMED because it is mutation-locked in config/rail_mutations.yaml (D-2676):
    scope/not-licensed   a unit whose effective ruling is CORRECT/ABSTAIN that the license does not name
    scope/not-ruled      a LICENSED unit whose effective ruling is NOT CORRECT/ABSTAIN (ESCALATE is the owner's
                         remaining decision - D-2898)
    target/disagreement  mapper(raw) != the owner's target, or != the packet's `live_mapper_says`
    surface/stale        a licensed row's stored value != the packet's stored value, or the packet's own per-unit
                         row count != the segments it ships (the surface moved under the write)
    cap/exceeded         the licensed row count exceeds the license's SHRINK-ONLY cap (D-2644)
    tier/undeclared      the license's provenance tier is not a member of PROVENANCE_LITERAL (C29)

DEFAULT IS A DRY RUN. `--apply` requires the license, a timestamped DB backup, a PRAGMA integrity gate, ONE
transaction, the counts recount (pipeline.taxonomy_manager - the ONE counts home) and a RECEIPT that records
before/after BYTES (the menu_hash set, every input's sha256, each row's from->to). A receipt that is a claim
rather than a measurement is the defect D-2660 names.

Usage:
    python3 scripts/apply_relabel_store_write.py --selftest
    python3 scripts/apply_relabel_store_write.py                 # dry run: plan + guards, writes nothing
    python3 scripts/apply_relabel_store_write.py --apply         # backup + integrity + transaction + receipt
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

_GOV = ROOT / "governance"
_RULINGS = ROOT / "config" / "relabel_rulings.yaml"
_TAXONOMY = ROOT / "config" / "taxonomy.yaml"
RULED_ACTIONS = ("CORRECT", "ABSTAIN")
ABSENCE = "emerging"  # D-2830: the declared absence a relabel to "no home" writes
_COLUMNS = ("discipline", "discipline_macro", "discipline_source", "taxonomy_match_method")


# ── pure helpers ──────────────────────────────────────────────────────────────────────────────────────
def _norm(x: object) -> str:
    """Collapse a label for comparison (case- and whitespace-insensitive)."""
    return re.sub(r"\s+", " ", str(x or "")).strip().lower()


def _cause_of(text: str) -> str:
    """The cause class of a packet row's free-text cause (the class, not its parenthetical)."""
    return str(text or "").split(" (")[0].strip()


def _sha256(path: Path) -> str:
    """Full content hash of an input, so a receipt cites the BYTES it consumed (D-2660)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _effective_action(unit_key: str, cause: str, rulings: dict[str, Any]) -> tuple[str, str]:
    """The owner's effective action for a unit - the SAME precedence the plan applier publishes.

    unit_rulings[unit_key] wins outright (a HELD word escalates: it was put back to the owner); otherwise the
    CLASS policy applies; otherwise ESCALATE - a unit no ruling reaches is the owner's, never a guess (C16).
    """
    ur = (rulings.get("unit_rulings") or {}).get(unit_key) or {}
    if ur.get("action"):
        if ur.get("held"):
            return "ESCALATE", "unit ruling HELD - put back to the owner"
        return str(ur["action"]).upper(), "unit ruling"
    policy = str(((rulings.get("class_rules") or {}).get(cause) or {}).get("policy") or "").upper()
    return (policy or "ESCALATE"), (f"class {cause} ruled {policy}" if policy else "no ruling reaches it")


def _owner_target(unit_key: str, cause: str, action: str, rulings: dict[str, Any]) -> str | None:
    """The target the OWNER named for a unit: `owner_canonical`, or the declared ABSENCE for ABSTAIN."""
    if action == "ABSTAIN":
        return ABSENCE
    ur = (rulings.get("unit_rulings") or {}).get(unit_key) or {}
    target = ur.get("owner_canonical")
    if not target:
        target = ((rulings.get("class_rules") or {}).get(cause) or {}).get("owner_canonical")
    return str(target) if target else None


def _method_for(target: str, raw: str) -> str:
    """The S4 match-method token (stage4_merge.run_stage4's raw->canonical block, verbatim rule)."""
    if _norm(target) == _norm(ABSENCE):
        return "emerging_real"
    if _norm(target) == _norm(raw):
        return "exact"
    return "synonym"


def plan(
    license_doc: dict[str, Any],
    rulings: dict[str, Any],
    units: dict[str, dict[str, Any]],
    segments: list[dict[str, str]],
    store_rows: dict[str, dict[str, Any]],
    resolver: Callable[[str], str],
    macro: Callable[[str], str],
    tiers: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Pure core: (operations, faults). No I/O, so every guard is exercised by a known answer in --selftest."""
    faults: list[str] = []
    lic = license_doc.get("store_write_license") or {}
    if not isinstance(lic, dict) or not lic:
        return [], ["FAIL-CLOSED (store-write): config/relabel_rulings.yaml carries no `store_write_license` - "
                    "a ruled row may not be written without the owner word that licenses it (D-2898)"]
    tier = str(lic.get("provenance_tier") or "")
    if tier not in tiers:
        faults.append(f"tier/undeclared: the license names the provenance tier {tier!r}, which is NOT a member "
                      f"of the C29 vocabulary {list(tiers)} - a stamp nothing declares is a manufactured claim")
    licensed = [str(u) for u in (lic.get("units") or [])]
    cap = int(lic.get("row_cap") or 0)

    # scope/not-licensed - a ruled unit the license does not name (the license may not be narrower than the rulings)
    for unit_key, meta in sorted(units.items()):
        action, _why = _effective_action(unit_key, _cause_of(meta.get("cause", "")), rulings)
        if action in RULED_ACTIONS and unit_key not in licensed:
            faults.append(f"scope/not-licensed: the unit {unit_key!r} carries the owner ruling {action} but the "
                          f"license does not name it - the write would leave a ruled row owed")
    # scope/not-ruled - a licensed unit whose ruling is ESCALATE (no agent mints a LABEL, D-2898)
    for unit_key in licensed:
        if unit_key not in units:
            faults.append(f"scope/not-licensed: the license names the unit {unit_key!r}, which the packet does "
                          f"not carry - the license and the decision surface disagree (BUG-751 class)")
            continue
        action, why = _effective_action(unit_key, _cause_of(units[unit_key].get("cause", "")), rulings)
        if action not in RULED_ACTIONS:
            faults.append(f"scope/not-ruled: the license names {unit_key!r} but no owner ruling reaches it "
                          f"({why}) - ESCALATE is the owner's remaining decision, never the applier's")

    ops: list[dict[str, Any]] = []
    for unit_key in licensed:
        meta = units.get(unit_key)
        if not meta:
            continue
        cause = _cause_of(meta.get("cause", ""))
        action, _why = _effective_action(unit_key, cause, rulings)
        if action not in RULED_ACTIONS:
            continue
        target = _owner_target(unit_key, cause, action, rulings)
        if not target:
            faults.append(f"target/disagreement: unit {unit_key!r} is ruled {action} and names NO target "
                          f"(owner_canonical absent) - the write has nothing it is licensed to write")
            continue
        rows = [r for r in segments if r.get("unit_key") == unit_key]
        declared = meta.get("n_rows")
        if declared is not None and int(declared) != len(rows):
            faults.append(f"surface/stale: the packet declares {declared} row(s) for {unit_key!r} while its own "
                          f"segments file carries {len(rows)} - the surface moved under the write")
        for row in rows:
            fb_id = str(row.get("fb_id") or "")
            live = str(row.get("live_mapper_says") or "")
            raw = str(row.get("raw_label") or "")
            stored = str(row.get("stored_canonical") or "")
            actual = store_rows.get(fb_id)
            if actual is None:
                faults.append(f"surface/stale: fb_id {fb_id} ({unit_key!r}) is on the decision surface and NOT "
                              f"in the store - the packet cites a row the store does not hold")
                continue
            if _norm(actual.get("discipline")) != _norm(stored):
                faults.append(f"surface/stale: fb_id {fb_id} stores {actual.get('discipline')!r} while the "
                              f"packet reviewed {stored!r} - refusing to write a row the owner did not see")
                continue
            mapped = resolver(str(actual.get("discipline_raw") or raw))
            if _norm(mapped) != _norm(target) or _norm(live) != _norm(target):
                faults.append(f"target/disagreement: fb_id {fb_id} ({unit_key!r}) - the mapper says {mapped!r}, "
                              f"the packet recorded {live!r}, the owner ruled {target!r}; the write copies the "
                              f"mapper's answer and may not invent one")
                continue
            ops.append({
                "fb_id": fb_id, "unit_key": unit_key, "cause": cause, "action": action,
                "discipline_raw": str(actual.get("discipline_raw") or ""), "from": stored,
                "to": mapped, "macro": macro(mapped), "method": _method_for(mapped, raw),
                "source": tier,
            })
    if cap and len(ops) > cap:
        faults.append(f"cap/exceeded: the plan reaches {len(ops)} row(s) and the license's SHRINK-ONLY cap is "
                      f"{cap} (D-2644) - a wider write needs a NEW owner word, not a bigger ceiling")
    return ops, faults


# ── real I/O ─────────────────────────────────────────────────────────────────────────────────────────
def _packet() -> tuple[Path, Path, str]:
    """The newest D-2976 UNIT csv + its segments sibling. Asserted by header, never by a glob's convenience."""
    cands = sorted((p for p in _GOV.glob("canonical_relabel_review_*.csv") if "_segments_" not in p.stem),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        raise SystemExit("FAIL-CLOSED (store-write): no canonical_relabel_review_*.csv - build the packet first "
                         "(scripts/build_relabel_review_packet.py) (C16)")
    packet = cands[0]
    segments = packet.with_name("canonical_relabel_review_segments_" + packet.stem.split("_")[-1] + ".csv")
    if not segments.exists():
        raise SystemExit(f"FAIL-CLOSED (store-write): the row-level surface {segments.name} is absent - a write "
                         f"keyed on unit keys alone cannot name the rows it touches (C16)")
    return packet, segments, packet.stem.split("_")[-1]


def _units(packet: Path) -> dict[str, dict[str, Any]]:
    """The unit table (unit_key -> must-carry fields), asserted field by field."""
    with packet.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in ("unit_key", "cause", "n_rows") if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"FAIL-CLOSED (store-write): {packet.name} lacks the column(s) {missing} - reading "
                             f"a surface without its cause/n_rows columns is a blind spot, not a convenience")
        return {r["unit_key"]: r for r in reader}


def _segments(path: Path) -> list[dict[str, str]]:
    """The row-level surface, asserted to carry the identity and both sides of the claim."""
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        need = ("unit_key", "fb_id", "stored_canonical", "raw_label", "live_mapper_says")
        missing = [c for c in need if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"FAIL-CLOSED (store-write): {path.name} lacks {missing} (C16)")
        return list(reader)


def _store_rows(conn: sqlite3.Connection, fb_ids: list[str]) -> dict[str, dict[str, Any]]:
    """The store side of the claim, read by IDENTITY (never by a predicate over the raw label)."""
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(fb_ids), 500):
        chunk = fb_ids[i:i + 500]
        marks = ",".join("?" * len(chunk))
        for row in conn.execute(f"SELECT fb_id, discipline, discipline_raw, discipline_macro, "
                                f"discipline_source, taxonomy_match_method FROM fbs WHERE fb_id IN ({marks})",
                                chunk):
            out[str(row[0])] = {"discipline": row[1], "discipline_raw": row[2], "discipline_macro": row[3],
                                "discipline_source": row[4], "taxonomy_match_method": row[5]}
    return out


def _production_mapper() -> Callable[[str], str]:
    """The PRODUCTION mapper, imported from its ONE home - never a restatement of it (C12/C21)."""
    import importlib.util

    path = ROOT / "scripts" / "audit_menu_rescope_cohort.py"
    spec = importlib.util.spec_from_file_location("audit_menu_rescope_cohort", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"FAIL-CLOSED (store-write): cannot load the production mapper {path} (C16)")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._map_discipline


def _tiers() -> tuple[str, ...]:
    """The C29 provenance vocabulary, read from its ONE home (C12)."""
    from pipeline.schemas import (
        PROVENANCE_LITERAL,  # noqa: PLC0415 - lazy: --selftest must run without pipeline/
    )

    return tuple(str(x) for x in PROVENANCE_LITERAL.__args__)


def _macro() -> Callable[[str], str]:
    """The fine->macro collapse, read from its ONE home (D-2884a/C21)."""
    from pipeline.discipline_macro import macro_for  # noqa: PLC0415

    return macro_for


def _db_default() -> Path:
    """The governed store path, read from its ONE home (C12)."""
    from pipeline.pipeline_paths import DB_PATH  # noqa: PLC0415

    return Path(DB_PATH)


def _backup(path: Path) -> Path:
    """C13/C6: a timestamped copy, fsync'd, size-verified before any write is allowed to start."""
    bak = Path(str(path) + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pre_relabel_store_write")
    shutil.copy2(str(path), str(bak))
    with bak.open("rb") as fh:
        os.fsync(fh.fileno())
    if path.stat().st_size != bak.stat().st_size:
        raise SystemExit("FAIL-CLOSED (store-write): the backup size differs from the store - refusing to write")
    return bak


def _integrity(path: Path) -> None:
    """The pre-write integrity gate: a store that is already inconsistent may not be mutated (C16)."""
    conn = sqlite3.connect(str(path))
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if qc != "ok" or fk:
        raise SystemExit(f"FAIL-CLOSED (store-write): integrity gate failed (quick_check={qc}, "
                         f"{len(fk)} FK violation(s)) - repair the store before writing it")


def _menu_hashes(conn: sqlite3.Connection) -> list[str]:
    """The menu the corpus was classified against, as a SET (a relabel must not move it)."""
    return sorted(str(r[0]) for r in conn.execute("SELECT DISTINCT menu_hash FROM fbs WHERE menu_hash IS NOT NULL"))


def _atomic_json(path: Path, doc: dict[str, Any]) -> None:
    """C6 crash-safe write: tempfile -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=False)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, str(path))


def run(apply_now: bool, db: Path | None) -> int:
    """Dry-run (default) or the licensed write: plan, guard, back up, mutate in ONE transaction, receipt."""
    rulings = yaml.safe_load(_RULINGS.read_text(encoding="utf-8"))
    if not isinstance(rulings, dict):
        raise SystemExit("FAIL-CLOSED (store-write): config/relabel_rulings.yaml is not a mapping (C16)")
    packet, segments_path, stamp = _packet()
    units, segments = _units(packet), _segments(segments_path)
    store = Path(db) if db else _db_default()
    if not store.exists():
        raise SystemExit(f"FAIL-CLOSED (store-write): the store {store} does not exist (C16)")

    conn = sqlite3.connect(str(store))
    try:
        ids = sorted({str(r["fb_id"]) for r in segments if str(r.get("unit_key") or "") in
                      {str(u) for u in ((rulings.get("store_write_license") or {}).get("units") or [])}})
        # the license IS a block of this file (one home), so the doc is read once and joined to itself
        ops, faults = plan(rulings, rulings, units, segments, _store_rows(conn, ids),
                           _production_mapper(), _macro(), _tiers())
        if faults:
            print("FAIL-CLOSED (store-write): the write refused. Nothing was written.")
            for f in faults:
                print("  - " + f)
            return 2
        by_unit: dict[str, list[dict[str, Any]]] = {}
        for op in ops:
            by_unit.setdefault(op["unit_key"], []).append(op)
        print(f"surface        : {packet.name} + {segments_path.name} (stamp {stamp})")
        print(f"license        : {(rulings.get('store_write_license') or {}).get('decision')} "
              f"granted {(rulings.get('store_write_license') or {}).get('granted')} "
              f"(cap {(rulings.get('store_write_license') or {}).get('row_cap')})")
        print(f"rows to write  : {len(ops)} across {len(by_unit)} unit(s)")
        for unit_key, group in sorted(by_unit.items()):
            tally: dict[tuple[str, str], int] = {}
            for op in group:
                tally[(op["from"], op["to"])] = tally.get((op["from"], op["to"]), 0) + 1
            moves = ", ".join(f"{src!r} -> {dst!r} x{n}" for (src, dst), n in sorted(tally.items()))
            print(f"  {unit_key} [{group[0]['action']}] {moves} | method={group[0]['method']} "
                  f"macro={group[0]['macro']!r} tier={group[0]['source']}")
        if not ops:
            print("nothing to do: every licensed row already carries the mapper's answer.")
            return 0
        if not apply_now:
            print("\n(dry run - nothing written; re-run with --apply)")
            return 0

        before_menus = _menu_hashes(conn)   # the menu SET: a relabel must leave it byte-identical
        conn.close()
        _integrity(store)
        bak = _backup(store)
        print(f"\nbackup         : {bak.name} ({bak.stat().st_size:,} bytes)")
        conn = sqlite3.connect(str(store))
        try:
            conn.execute("BEGIN IMMEDIATE")
            changed = 0
            for op in ops:
                cur = conn.execute(
                    f"UPDATE fbs SET {', '.join(c + '=?' for c in _COLUMNS)} WHERE fb_id = ?",
                    (op["to"], op["macro"], op["source"], op["method"], op["fb_id"]))
                changed += cur.rowcount
            try:
                from pipeline.taxonomy_manager import update_counts_from_fbs  # noqa: PLC0415

                counts = update_counts_from_fbs(conn)
            except Exception as exc:  # noqa: BLE001 - a counts home that cannot be reached is FATAL, never silent
                conn.execute("ROLLBACK")
                raise SystemExit(f"FAIL-CLOSED (store-write): the counts recount failed ({exc}) - rolled back") from exc
            conn.commit()
        finally:
            conn.close()

        conn = sqlite3.connect(str(store))
        try:
            after_menus = _menu_hashes(conn)
            verified = 0   # re-READ every written row: the receipt records a measurement, not a rowcount claim
            for op in ops:
                row = conn.execute("SELECT discipline, discipline_macro, discipline_source, "
                                   "taxonomy_match_method FROM fbs WHERE fb_id = ?", (op["fb_id"],)).fetchone()
                if row and str(row[0]) == op["to"] and str(row[1]) == op["macro"] and \
                        str(row[2]) == op["source"] and str(row[3]) == op["method"]:
                    verified += 1
            census = {c: [tuple(r) for r in conn.execute(f"SELECT {c}, COUNT(*) FROM fbs GROUP BY {c} ORDER BY 2 DESC")]
                      for c in _COLUMNS}
        finally:
            conn.close()
        if changed != len(ops) or verified != len(ops):
            print(f"⚠️  changed={changed} verified={verified} planned={len(ops)} - the write did NOT land exactly; "
                  f"the receipt records it as a FAULT, not a success")
        receipt = {
            "decision": (rulings.get("store_write_license") or {}).get("decision"),
            "granted": (rulings.get("store_write_license") or {}).get("granted"),
            "owner_word": (rulings.get("store_write_license") or {}).get("owner_word"),
            "written_utc": datetime.now(UTC).isoformat(),
            "store": str(store), "store_bytes": store.stat().st_size,
            "inputs": {"rulings": str(_RULINGS), "rulings_sha256": _sha256(_RULINGS),
                       "packet": packet.name, "packet_sha256": _sha256(packet),
                       "segments": segments_path.name, "segments_sha256": _sha256(segments_path),
                       "taxonomy_sha256": _sha256(_TAXONOMY) if _TAXONOMY.exists() else None},
            "plan": {"rows": len(ops), "units": {k: len(v) for k, v in sorted(by_unit.items())},
                     "moves": sorted({f"{op['from']} -> {op['to']}" for op in ops})},
            "measurement": {"changed": changed, "verified": verified, "planned": len(ops),
                            "menu_hash_before": before_menus, "menu_hash_after": after_menus,
                            "menu_unmoved": before_menus == after_menus,
                            "counts_recount": {k: (v if not isinstance(v, dict) else len(v))
                                               for k, v in (counts or {}).items()},
                            "column_census_after": {c: [list(x) for x in v] for c, v in census.items()}},
            "rows": [{"fb_id": op["fb_id"], "unit_key": op["unit_key"], "raw": op["discipline_raw"],
                      "from": op["from"], "to": op["to"], "macro": op["macro"],
                      "source": op["source"], "method": op["method"]} for op in ops],
            "fault": changed != len(ops) or verified != len(ops),
        }
        out = ROOT / str((rulings.get("store_write_license") or {}).get("receipt")
                         or "config/label_store_write_receipt.json")
        _atomic_json(out, receipt)
        print(f"receipt        : {out.relative_to(ROOT)} ({len(ops)} row(s), "
              f"changed={changed}, verified={verified}, menu_unmoved={before_menus == after_menus})")
        return 1 if receipt["fault"] else 0
    finally:
        conn.close()


# ── known-answer controls ─────────────────────────────────────────────────────────────────────────────
def selftest() -> int:
    """Every guard is SEEN to fire, and the happy path is SEEN to plan (a control that cannot pass is not one)."""
    fails: list[str] = []
    seen: list[str] = []   # the control count is DERIVED, never restated (BUG-588)
    tiers = ("human_verbatim", "llm_extracted_from_source", "llm_hypothesis", "deterministic")

    def expect(name: str, got: object, want: object) -> None:
        seen.append(name)
        if got != want:
            fails.append(f"selftest/{name}")
            print(f"  !!  {name}: got {got!r}, want {want!r}")

    def lic(units: list[str], cap: int = 163, tier: str = "deterministic") -> dict[str, Any]:
        return {"store_write_license": {"decision": "D-2988", "granted": "2026-10-13", "units": units,
                                        "row_cap": cap, "provenance_tier": tier}}

    rulings = {
        "class_rules": {"LATE-HOME": {"policy": "CORRECT", "owner_canonical": "marketing"},
                        "PROVENANCE-UNRESOLVED": {"policy": "ESCALATE"},
                        "ALIAS-LAYER-RETIRED": {"policy": "CONFIRM"}},
        "unit_rulings": {"computer science -> software engineering": {"action": "ABSTAIN"},
                         "entrepreneurial studies -> emerging": {"action": "CORRECT",
                                                                 "owner_canonical": "entrepreneurship studies"}},
    }
    units = {"marketing strategy -> emerging": {"unit_key": "marketing strategy -> emerging",
                                                "cause": "LATE-HOME (D-2975)", "n_rows": "2"},
             "computer science -> software engineering": {"unit_key": "computer science -> software engineering",
                                                          "cause": "PROVENANCE-UNRESOLVED", "n_rows": "2"},
             "narrative theory -> literary theory": {"unit_key": "narrative theory -> literary theory",
                                                     "cause": "ALIAS-LAYER-RETIRED (D-2814)", "n_rows": "1"}}
    segs = [{"unit_key": "marketing strategy -> emerging", "fb_id": "a1", "stored_canonical": "emerging",
             "raw_label": "marketing strategy", "live_mapper_says": "marketing"},
            {"unit_key": "marketing strategy -> emerging", "fb_id": "a2", "stored_canonical": "emerging",
             "raw_label": "marketing strategy", "live_mapper_says": "marketing"},
            {"unit_key": "computer science -> software engineering", "fb_id": "b1",
             "stored_canonical": "software engineering", "raw_label": "computer science",
             "live_mapper_says": "emerging"},
            {"unit_key": "computer science -> software engineering", "fb_id": "b2",
             "stored_canonical": "software engineering", "raw_label": "computer science",
             "live_mapper_says": "emerging"}]
    store = {"a1": {"discipline": "emerging", "discipline_raw": "marketing strategy"},
             "a2": {"discipline": "emerging", "discipline_raw": "marketing strategy"},
             "b1": {"discipline": "software engineering", "discipline_raw": "computer science"},
             "b2": {"discipline": "software engineering", "discipline_raw": "computer science"}}
    mapper = lambda raw: "emerging" if raw == "computer science" else "marketing"  # noqa: E731
    macro = lambda d: "emerging" if d == "emerging" else "Method & Business"  # noqa: E731

    try:   # the mutation fixture carries no pipeline/: there the fixture IS the vocabulary
        real_tiers = _tiers()
    except Exception:  # noqa: BLE001 - a fixture without the home is a DECLARED condition, not a swallow
        real_tiers = tiers
    expect("fixture_tier_vocabulary_matches_its_home", tuple(real_tiers), tiers)

    both = ["marketing strategy -> emerging", "computer science -> software engineering"]
    ops, faults = plan(lic(both), rulings, units, segs, store, mapper, macro, tiers)
    expect("happy_path_plans_the_licensed_rows", (len(ops), faults), (4, []))
    expect("happy_path_is_triply_agreed",
           sorted({(o["from"], o["to"], o["method"], o["source"]) for o in ops}),
           [("emerging", "marketing", "synonym", "deterministic"),
            ("software engineering", "emerging", "emerging_real", "deterministic")])

    # scope/not-licensed: a ruled unit the license omits (here: the class-CORRECT unit is ruled, not licensed)
    ops2, f2 = plan(lic(["computer science -> software engineering"]), rulings, units, segs, store, mapper, macro, tiers)
    expect("scope_refuses_a_licensed_escalated_unit",
           any(f.startswith("scope/not-licensed: the unit 'marketing strategy") for f in f2), True)
    expect("scope_never_widens_the_write", sorted({o["unit_key"] for o in ops2}),
           ["computer science -> software engineering"])

    # scope/not-ruled: a LICENSED unit nobody ruled (ESCALATE) must be refused, not swept in
    esc = {"narrative theory -> literary theory": {"unit_key": "narrative theory -> literary theory",
                                                   "cause": "ALIAS-LAYER-RETIRED (D-2814)", "n_rows": "1"}}
    _o3, f3 = plan(lic(["narrative theory -> literary theory"]), rulings, esc, segs, store, mapper, macro, tiers)
    expect("scope_refuses_an_unruled_licensed_unit",
           (any(f.startswith("scope/not-ruled: the license names 'narrative theory") for f in f3), _o3),
           (True, []))

    # target/disagreement: the mapper and the owner must agree, and the packet's record must agree too
    _o4, f4 = plan(lic(both), rulings, units, segs, store, lambda raw: "design thinking", macro, tiers)
    expect("mapper_disagreement_is_refused",
           any(f.startswith("target/disagreement: fb_id a1") for f in f4), True)

    # surface/stale: the store moved under the reviewed surface
    stale = dict(store, a1={"discipline": "marketing", "discipline_raw": "marketing strategy"})
    _o5, f5 = plan(lic(both), rulings, units, segs, stale, mapper, macro, tiers)
    expect("stale_surface_is_refused",
           any(f.startswith("surface/stale: fb_id a1") for f in f5), True)

    # cap/exceeded: the shrink-only ceiling (D-2644)
    _o6, f6 = plan(lic(both, cap=3), rulings, units, segs, store, mapper, macro, tiers)
    expect("cap_is_enforced", any(f.startswith("cap/exceeded:") for f in f6), True)

    # tier/undeclared: a provenance tier outside the C29 vocabulary is a manufactured claim
    _o7, f7 = plan(lic(both, tier="owner_ruled"), rulings, units, segs, store, mapper, macro, tiers)
    expect("tier_must_be_declared", any(f.startswith("tier/undeclared:") for f in f7), True)

    # no license at all: the word is the whole authority for the write
    _o8, f8 = plan({}, rulings, units, segs, store, mapper, macro, tiers)
    expect("no_license_refuses_the_write", (any("carries no `store_write_license`" in f for f in f8), _o8 == []),
           (True, True))

    # a held owner word escalates rather than writes (the plan applier's own semantics)
    held = dict(rulings, unit_rulings=dict(rulings["unit_rulings"],
                                           **{"marketing strategy -> emerging": {"action": "CORRECT",
                                                                                 "held": True}}))
    _o9, f9 = plan(lic(both), held, units, segs, store, mapper, macro, tiers)
    expect("a_held_owner_word_escalates",
           any(f.startswith("scope/not-ruled: the license names 'marketing strategy") for f in f9), True)

    if fails:
        print(f"FAIL store-write selftest: {len(fails)} of {len(seen)} known answer(s) did not fire: {fails}")
        return 1
    print(f"OK store-write selftest: {len(seen)} known answers (each refusal NAMED by its guard)")
    return 0


def main(argv: list[str]) -> int:
    """CLI: --selftest | a read-only plan (default) | --apply for the licensed write."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true", help="run the known-answer controls only")
    ap.add_argument("--apply", action="store_true", help="perform the licensed write (backup + transaction)")
    ap.add_argument("--db", type=Path, default=None, help="store path (default: pipeline config DB_PATH)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return run(args.apply, args.db)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
