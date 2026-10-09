#!/usr/bin/env python3
"""scripts/bug693_reclaim.py — BUG-693 deterministic emerging reclaim (D-2893).

Owner-signed (2026-10-09, D-2891/D-2892) deterministic reclaim of the canonical-run
emerging bucket. Root cause (BUG-693) = MENU-WIDENING DRIFT: the discipline menu
widened v5->v8 (added ``marketing``, ``business administration``,
``entrepreneurship studies``) and those rows were never re-classified, so they sat as
``discipline='emerging'`` even though ``discipline_raw`` already held an EXACT
canonical label.

SCOPE (D-2891): canonical run ``rechunk-v4-20260929`` ONLY. The t11 checkpoint
(7855 rows) is FOREVER excluded. This script hard-fails if any selected row is not
in the canonical run.

TWO deterministic, LLM-free actions (no synonym coercion — EXACT canonical match only,
case-insensitive, so no silent cross-kind drift):

  A. mapfail (280): ``discipline_raw`` is a SINGLE label that is EXACTLY a canonical
     DISCIPLINE. Lift it: ``discipline = <canonical discipline>`` and set
     ``discipline_macro`` to the macro bucket owning that discipline (keeps the two
     derived fields 1:1 consistent — D-2884(b)/D-2792).

  B. dombleed (190): ``discipline_raw`` is a SINGLE label that is EXACTLY a canonical
     DOMAIN (axis leak). Kind-swap onto the domain axis (BUG-150/BUG-197 direction B):
     add the canonical domain to ``domains`` (dedup), add the raw label to
     ``domains_raw`` (dedup), clear ``discipline_raw``. ``discipline`` stays
     'emerging' — its re-classification is a SEPARATE LLM step, NOT deterministic.

Kind-safety (D2133/D2422): a label canonical on BOTH axes is ambiguous → LEFT ALONE.
Empty/multi-label ``discipline_raw`` → LEFT ALONE (not this script's job).

Crash-safe (C6/C13): DB backup + integrity gate before write; single atomic txn;
idempotent recount via reconcile_canonical_status() + update_counts_from_fbs().

FAIL-CLOSED audit: the computed mapfail/dombleed counts must equal the owner-signed
proposal (280 / 190). Any drift → abort with a forensic report (D-2893 no-drift rule).

Run:
  python3 scripts/bug693_reclaim.py            # dry-run
  python3 scripts/bug693_reclaim.py --apply    # backup + integrity + write
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
)
from pipeline.taxonomy_manager import (  # noqa: E402
    reconcile_canonical_status,
    update_counts_from_fbs,
)

# Owner-signed scope (D-2891/D-2892, governance/bug693_reclaim_proposal.json).
EXPECTED_MAPFAIL = 280
EXPECTED_DOMBLEED = 190
CANONICAL_RUN_ID = "rechunk-v4-20260929"


def _to_list(value) -> list[str]:
    """Normalize a stored pipe/JSON list field to a list of trimmed strings."""
    if value is None:
        return []
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return []
        if s.startswith("["):
            try:
                return [x.strip() for x in json.loads(s) if str(x).strip()]
            except (json.JSONDecodeError, TypeError):
                return []
        return [x.strip() for x in s.split("|") if x.strip()]
    return [str(x).strip() for x in value if str(x).strip()]


def _normalize(label: str) -> str:
    """Case-fold + collapse internal whitespace for exact-match comparison."""
    return " ".join(label.strip().lower().split())


def _load_macro_owner() -> dict[str, str]:
    """Map discipline canonical -> 3-way macro bucket (config, C12)."""
    import yaml

    menu = json.loads((_ROOT / "config" / "closed_menu_v8.json").read_text(encoding="utf-8"))
    groups_cfg = yaml.safe_load(
        (_ROOT / "config" / "discipline_macro_groups.yaml").read_text(encoding="utf-8")
    )
    three_way = groups_cfg["macros"]["3-way"]
    group_to_macro: dict[str, str] = {}
    for macro, group_names in three_way.items():
        for g in group_names:
            group_to_macro[_normalize(g)] = macro
    disc_to_macro: dict[str, str] = {}
    for entry in menu["disciplines"]:
        value = entry["value"]
        if value == "emerging":
            continue
        group = _normalize(entry.get("group", ""))
        disc_to_macro[_normalize(value)] = group_to_macro.get(group, "emerging")
    return disc_to_macro


def _backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_bug693_reclaim")
    shutil.copy2(str(db_path), str(bak))
    with open(bak, "rb") as f:
        os.fsync(f.fileno())
    if db_path.stat().st_size != bak.stat().st_size:
        raise RuntimeError("backup size mismatch — aborting write")
    return bak


def _integrity_gate(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if qc != "ok":
        raise RuntimeError(f"integrity gate FAILED (quick_check={qc})")
    if fk:
        raise RuntimeError(f"integrity gate FAILED ({len(fk)} FK violations)")


def _compute(conn: sqlite3.Connection) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (mapfail, dombleed, skipped) with full forensic detail."""
    disc_norm = {_normalize(d): d for d in CANONICAL_DISCIPLINES}
    dom_norm = {_normalize(d): d for d in CANONICAL_DOMAINS}
    disc_to_macro = _load_macro_owner()

    rows = conn.execute(
        "SELECT fb_id, discipline_raw, domains, domains_raw, discipline_macro, pipeline_run_id "
        "FROM fbs WHERE discipline='emerging'"
    ).fetchall()

    mapfail: list[dict] = []
    dombleed: list[dict] = []
    skipped: list[dict] = []

    for fb_id, d_raw, doms, doms_raw, macro, run_id in rows:
        if run_id != CANONICAL_RUN_ID:
            skipped.append({"fb_id": fb_id, "reason": f"non-canonical run {run_id}"})
            continue
        raw = _to_list(d_raw)
        if len(raw) != 1:
            skipped.append({"fb_id": fb_id, "reason": f"raw label count {len(raw)} != 1"})
            continue
        label = raw[0]
        ln = _normalize(label)
        is_disc = ln in disc_norm
        is_dom = ln in dom_norm
        if is_disc and is_dom:
            skipped.append({"fb_id": fb_id, "reason": f"ambiguous both-axis label {label!r}"})
            continue
        if is_disc:
            canonical = disc_norm[ln]
            mapfail.append(
                {
                    "fb_id": fb_id,
                    "raw": label,
                    "discipline": canonical,
                    "macro": disc_to_macro.get(ln, "emerging"),
                }
            )
        elif is_dom:
            canonical = dom_norm[ln]
            dombleed.append(
                {
                    "fb_id": fb_id,
                    "raw": label,
                    "domain": canonical,
                    "domains": _to_list(doms),
                    "domains_raw": _to_list(doms_raw),
                }
            )
        else:
            skipped.append({"fb_id": fb_id, "reason": f"offmenu label {label!r}"})

    return mapfail, dombleed, skipped


def _report(mapfail, dombleed, skipped) -> None:
    print(f"mapfail (exact canonical discipline lift): {len(mapfail)}")
    print(f"dombleed (exact canonical domain kind-swap): {len(dombleed)}")
    print(f"skipped (non-canonical run / multi-label / ambiguous / offmenu): {len(skipped)}")
    mf = Counter(m["discipline"] for m in mapfail)
    for k, v in mf.most_common():
        print(f"    lift -> {k}: {v}")
    db = Counter(d["domain"] for d in dombleed)
    for k, v in db.most_common():
        print(f"    kind-swap -> {k}: {v}")


def _apply(conn: sqlite3.Connection, mapfail, dombleed) -> int:
    now = datetime.now(timezone.utc).isoformat()
    changes = 0

    for m in mapfail:
        conn.execute(
            "UPDATE fbs SET discipline=?, discipline_macro=?, discipline_source=? "
            "WHERE fb_id=? AND discipline='emerging' AND pipeline_run_id=?",
            (m["discipline"], m["macro"], "llm_extracted_from_source", m["fb_id"], CANONICAL_RUN_ID),
        )
        changes += 1

    for d in dombleed:
        doms = d["domains"]
        if "emerging" in doms:
            doms = [x for x in doms if x != "emerging"]
        if d["domain"] not in doms:
            doms.append(d["domain"])
        doms_raw = d["domains_raw"]
        if d["raw"] not in doms_raw:
            doms_raw.append(d["raw"])
        conn.execute(
            "UPDATE fbs SET domains=?, domains_raw=?, discipline_raw='' "
            "WHERE fb_id=? AND discipline='emerging' AND pipeline_run_id=?",
            (json.dumps(doms), json.dumps(doms_raw), d["fb_id"], CANONICAL_RUN_ID),
        )
        changes += 1

    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description="BUG-693 deterministic emerging reclaim (D-2893)")
    ap.add_argument("--apply", action="store_true", help="backup + integrity gate + write")
    args = ap.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        mapfail, dombleed, skipped = _compute(conn)
    finally:
        conn.close()

    _report(mapfail, dombleed, skipped)

    # FAIL-CLOSED drift audit (D-2893): computed set must equal owner-signed proposal.
    if len(mapfail) != EXPECTED_MAPFAIL or len(dombleed) != EXPECTED_DOMBLEED:
        print(
            f"\nFAIL-CLOSED: drift vs owner-signed scope (mapfail {EXPECTED_MAPFAIL}/"
            f"dombleed {EXPECTED_DOMBLEED}). Got mapfail={len(mapfail)} dombleed={len(dombleed)}. "
            "Aborting — re-run the forensic audit."
        )
        return 1

    if not args.apply:
        print("\n(dry-run — no write. Re-run with --apply to commit.)")
        return 0

    bak = _backup_db(DB_PATH)
    print(f"  🔒 Backup: {bak}")
    _integrity_gate(DB_PATH)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        changes = _apply(conn, mapfail, dombleed)
        reconcile_canonical_status(conn)
        update_counts_from_fbs(conn)
        conn.commit()
        print(f"  ✅ committed {changes} FB updates in one transaction")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _integrity_gate(DB_PATH)
    print("  ✅ post-write integrity gate clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
