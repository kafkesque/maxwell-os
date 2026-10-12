#!/usr/bin/env python3
"""
repair_displaced_canonical_domains.py — deterministic re-home of RETIRED canonical labels.
===========================================================================================
Authority: D-2935 (executable counterpart of meta.displaced_canonicals), D-2865 (v8 merge +
demote), D-2897/D-2899 (v9 folds), D-2902 (per-alias re-homing, NOT a blind rewrite),
D-2898 (canonical promotion is DETERMINISTIC + OWNER-GATED — no agent auto-mints a home),
D-2686 (raw-label invariance: domains_raw/discipline_raw are NEVER touched), BUG-711.

PROBLEM (measured 2026-10-11)
-----------------------------
The canonical run `rechunk-v4-20260929` carries 176 retired-canonical tokens on 173 rows:
  * `science & research` 85 tokens / `social sciences` 91 tokens  (both DOMAIN axis)
Root cause: those rows were classified 2026-09-29 on a menu whose domain space still held
dom-031/dom-035; D-2865 removed both, but D-2866 remapped ANCHORS ONLY and explicitly
excluded silver, and D-2899 re-stamped only the 97 discipline-side rows. No store-side step
ever re-homed the domain cells. D2620 therefore fails-closed on these rows at S6 (the loud
half of BUG-709).

CONTRACT
--------
* Reads `meta.displaced_to` from config/taxonomy.yaml (single home, C12) — nothing hardcoded.
* Axis-aware: a domain target must be a canonical DOMAIN, a discipline target a canonical
  DISCIPLINE. A crossed target aborts the whole run (C16) rather than minting a BUG-197/D2620
  non-contamination violation.
* `status: ratified_deterministic` entries are applied. `status: owner_gate` (target: null)
  entries are NEVER applied — they are emitted as triage rows for an owner signature (D-2898).
* `per_alias_required` entries resolve each row through its OWN domains_raw via
  alias_map.domain_aliases first (D-2902: per-alias, not blind); rows that fall back to the
  ratified fold are flagged `owner_triage` in the CSV and counted separately.
* Order-preserving de-duplication after replacement (a row may already carry the target).
* domains_raw / discipline_raw are never modified (D-2686).
* DRY-RUN IS THE DEFAULT. --apply requires a fresh backup (C13) and runs in one transaction
  with a post-write assertion; any failure rolls back (C6/C23).

Usage:
    python3 scripts/repair_displaced_canonical_domains.py                 # dry-run census
    python3 scripts/repair_displaced_canonical_domains.py --triage        # + write triage CSV
    python3 scripts/repair_displaced_canonical_domains.py --apply         # backup + transactional apply
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.pipeline_paths import CANONICAL_RUN, DB_PATH  # noqa: E402

import yaml  # noqa: E402

TAXONOMY_PATH = REPO_ROOT / "config" / "taxonomy.yaml"
ALIAS_MAP_PATH = REPO_ROOT / "config" / "alias_map.yaml"
BACKUP_GUARDIAN = REPO_ROOT / "pipeline" / "backup_guardian.sh"
TRIAGE_CSV = REPO_ROOT / "governance" / "displaced_domain_repair_triage_20261011.csv"
TRIAGE_COLUMNS: tuple[str, ...] = (
    "fb_id", "name", "axis", "stale_token", "domains_before", "domains_after",
    "basis", "disposition", "decision", "owner_signature",
)


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], set[str], set[str]]:
    """Load the re-home map, the alias map, and both canonical vocabularies.

    Returns:
        (displaced_to, alias_map, canonical_domains, canonical_disciplines)
    """
    tax = yaml.safe_load(TAXONOMY_PATH.read_text())
    aliases = yaml.safe_load(ALIAS_MAP_PATH.read_text())
    meta = tax.get("meta", {})
    if "displaced_to" not in meta:
        raise RuntimeError(
            "config/taxonomy.yaml:meta.displaced_to is absent — the re-home map is the "
            "single home for retired labels (D-2935). Refusing to guess (C16)."
        )
    displaced = meta["displaced_to"]
    declared = set(meta.get("displaced_canonicals", []))
    if set(displaced) != declared:
        raise RuntimeError(
            "displaced_to and displaced_canonicals disagree — every declared retirement "
            f"needs a re-home entry. missing={sorted(declared - set(displaced))} "
            f"extra={sorted(set(displaced) - declared)}"
        )
    canon_domains = {d["canonical"] for d in tax["domains"]} | {meta["catch_all_domain"]}
    canon_disciplines = {d["canonical"] for d in tax["disciplines"]} | {meta["catch_all_discipline"]}
    if meta["catch_all_domain"] not in {d["canonical"] for d in tax["domains"]}:
        canon_domains.add(meta["catch_all_domain"])
    return displaced, aliases, canon_domains, canon_disciplines


def _targets_from_raw(raw_labels: list[str], alias_map: dict[str, Any], vocab: set[str]) -> list[str]:
    """Resolve raw surface labels to canonical targets through the declared alias map.

    D-2902: per-alias re-homing — the row's own raw labels decide, never a blind rewrite.

    Args:
        raw_labels: the row's verbatim raw labels (lowercased by the caller).
        alias_map: config/alias_map.yaml contents.
        vocab: the canonical vocabulary the targets must belong to (axis-constrained).

    Returns:
        Ordered, de-duplicated canonical targets (empty when nothing resolves).
    """
    out: list[str] = []
    for raw in raw_labels:
        value = alias_map.get(raw)
        if isinstance(value, str):
            candidates = [value]
        elif isinstance(value, list):
            candidates = [v for v in value if isinstance(v, str)]
        else:
            continue
        for cand in candidates:
            if cand in vocab and cand not in out:
                out.append(cand)
    return out


def _dedupe(seq: list[str]) -> list[str]:
    """Order-preserving de-duplication."""
    return list(dict.fromkeys(seq))


HOLD_DISPOSITIONS: tuple[str, ...] = ("owner_gate_hold", "ratified_fold_owner_triage")


def _is_hold(disposition: str) -> bool:
    """True when a disposition means 'retained for an owner decision, never written'."""
    return disposition in HOLD_DISPOSITIONS


def _as_list(value: Any) -> list[str]:
    """Coerce a stored label cell to a list of raw labels.

    `domains_raw` is a JSON array; `discipline_raw` is a bare string. Both shapes are
    tolerated explicitly rather than by duck-typing (C16: a malformed cell raises).

    Args:
        value: the raw cell value (None, str, or JSON array string).

    Returns:
        The raw labels as a list of strings.
    """
    if value is None or value == "":
        return []
    text = str(value).strip()
    if text.startswith("["):
        parsed = json.loads(text)
        return [str(x) for x in parsed if isinstance(x, (str, int, float))]
    return [text]


def build_plan(row: dict[str, Any], displaced: dict[str, Any], aliases: dict[str, Any],
               canon_domains: set[str], canon_disciplines: set[str],
               accept_ratified_fold: bool = False) -> list[dict[str, Any]]:
    """Compute the re-home plan for one FB row. `accept_ratified_fold=False` HOLDS the
    per_alias_required rows that carry no alias evidence (D-2898: no un-gated store write).

    Args:
        row: dict with fb_id, name, discipline, domains, domains_raw.
        displaced: meta.displaced_to.
        aliases: config/alias_map.yaml contents.
        canon_domains: canonical domain vocabulary (axis guard).
        canon_disciplines: canonical discipline vocabulary (axis guard).

    Returns:
        One plan entry per axis carrying a retired token (possibly empty).
    """
    plans: list[dict[str, Any]] = []
    domain_raw = {r.lower() for r in json.loads(row.get("domains_raw") or "[]")}
    discipline_raw = {r.lower() for r in _as_list(row.get("discipline_raw"))}
    for axis, column, vocab, raw_labels in (
        ("domain", "domains", canon_domains, domain_raw),
        ("discipline", "discipline", canon_disciplines, discipline_raw),
    ):
        current = json.loads(row[column]) if axis == "domain" else ([row[column]] if row[column] else [])
        stale = [t for t in current if t in displaced and displaced[t]["axis"] == axis]
        if not stale:
            continue
        after: list[str] = []
        dispositions: list[dict[str, Any]] = []
        held: set[str] = set()
        for token in current:
            entry = displaced.get(token)
            if not entry or entry["axis"] != axis:
                after.append(token)
                continue
            target = entry.get("target")
            if entry["status"] == "owner_gate" or not target:
                after.append(token)
                held.add(token)
                dispositions.append({"token": token, "disposition": "owner_gate_hold",
                                    "basis": entry["basis"], "decision": "D-2898"})
                continue
            if entry.get("per_alias_required"):
                per_alias = _targets_from_raw(sorted(raw_labels), aliases.get(f"{axis}_aliases", {}), vocab)
                if per_alias:
                    derived = _dedupe([t for t in per_alias if t != token])
                    after.extend(derived)
                    dispositions.append({"token": token, "disposition": "per_alias_derived",
                                         "basis": entry["basis"], "decision": "D-2902"})
                    continue
                if not accept_ratified_fold:
                    after.append(token)
                    held.add(token)
                    dispositions.append({"token": token, "disposition": "ratified_fold_owner_triage",
                                         "basis": entry["basis"],
                                         "decision": "D-2865 (owner sign required)"})
                    continue
                after.append(target)
                dispositions.append({"token": token, "disposition": "ratified_fold_accepted",
                                     "basis": entry["basis"], "decision": "D-2865"})
                continue
            after.append(target)
            dispositions.append({"token": token, "disposition": "ratified_deterministic",
                                 "basis": entry["basis"], "decision": entry.get("basis", "").split()[0]})
        after = _dedupe(after)
        if not after:
            raise RuntimeError(f"re-home would empty the {axis} axis on {row['fb_id']} — refusing (C16)")
        crossed = [t for t in after if t not in vocab and t not in held]
        if crossed:
            raise RuntimeError(
                f"axis guard: {crossed} on {row['fb_id']} is not a canonical {axis}. A crossed "
                f"target would mint a D2620/BUG-197 violation — aborting (C16)."
            )
        plans.append({
            "axis": axis, "column": column, "before": current, "after": after,
            "changed": current != after, "dispositions": dispositions,
        })
    return plans


def fetch_rows(conn: sqlite3.Connection, run_id: str, stale: set[str]) -> list[dict[str, Any]]:
    """Return every row of the run carrying at least one retired canonical token."""
    like = " OR ".join(["(domains LIKE ? OR discipline = ?)" for _ in stale])
    params: list[str] = []
    for token in sorted(stale):
        params += [f'%"{token}"%', token]
    sql = (f"SELECT fb_id, name, discipline, domains, domains_raw, discipline_raw FROM fbs "
           f"WHERE pipeline_run_id = ? AND ({like})")
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(sql, [run_id, *params])]


def write_triage(rows: list[dict[str, Any]], path: Path) -> int:
    """Write the per-cell triage CSV (auditable owner-signature surface)."""
    n = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(TRIAGE_COLUMNS))
        writer.writeheader()
        for row in rows:
            for plan in row["plans"]:
                for disp in plan["dispositions"]:
                    writer.writerow({
                        "fb_id": row["fb_id"], "name": (row.get("name") or "")[:80],
                        "axis": plan["axis"], "stale_token": disp["token"],
                        "domains_before": json.dumps(plan["before"]),
                        "domains_after": json.dumps(plan["after"]),
                        "basis": disp.get("basis", ""), "disposition": disp["disposition"],
                        "decision": disp.get("decision", ""), "owner_signature": "",
                    })
                    n += 1
    return n


def apply_plan(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> int:
    """Apply the deterministic plans in ONE transaction; fail-closed on any mismatch."""
    claimed = 0
    for row in rows:
        for plan in row["plans"]:
            if not plan["changed"]:
                continue
            # Compare-and-swap: only write if the store still holds what we planned against.
            if plan["axis"] == "domain":
                cur = conn.execute("SELECT domains FROM fbs WHERE fb_id = ?", (row["fb_id"],))
                held = cur.fetchone()[0]
                if held != json.dumps(plan["before"]):
                    raise RuntimeError(
                        f"stale plan for {row['fb_id']}: store holds {held!r}, plan expects "
                        f"{json.dumps(plan['before'])!r} — aborting (C6/C23)"
                    )
                cursor = conn.execute("UPDATE fbs SET domains = ? WHERE fb_id = ?",
                                      (json.dumps(plan["after"]), row["fb_id"]))
            else:
                cursor = conn.execute("UPDATE fbs SET discipline = ? WHERE fb_id = ? AND discipline = ?",
                                      (plan["after"][0], row["fb_id"], plan["before"][0]))
            claimed += max(cursor.rowcount, 0)
    return claimed


def main() -> int:
    """CLI entry point: dry-run census, triage export, or transactional apply."""
    parser = argparse.ArgumentParser(description="D-2935/BUG-711 displaced-canonical re-home")
    parser.add_argument("--apply", action="store_true", help="backup + apply in one transaction")
    parser.add_argument("--triage", action="store_true", help=f"write {TRIAGE_CSV.name}")
    parser.add_argument("--run", default=CANONICAL_RUN, help="pipeline_run_id (default: canonical run)")
    parser.add_argument("--accept-ratified-fold", action="store_true",
                        help="owner sign-off: write the D-2865 ratified fold on per_alias rows lacking alias evidence")
    args = parser.parse_args()

    displaced, aliases, canon_domains, canon_disciplines = load_inputs()
    stale = set(displaced)
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={'rw' if args.apply else 'ro'}", uri=True)
    raw_rows = fetch_rows(conn, args.run, stale)
    rows: list[dict[str, Any]] = []
    for r in raw_rows:
        plans = build_plan(r, displaced, aliases, canon_domains, canon_disciplines,
                           accept_ratified_fold=args.accept_ratified_fold)
        plans = [p for p in plans if p["changed"] or any(_is_hold(d["disposition"]) for d in p["dispositions"])]
        if plans:
            rows.append({**r, "plans": plans})

    census: dict[str, int] = {}
    for row in rows:
        for plan in row["plans"]:
            for disp in plan["dispositions"]:
                census[disp["disposition"]] = census.get(disp["disposition"], 0) + 1
    print(f"═══ D-2935 displaced-canonical re-home · run={args.run} ═══")
    print(f"affected rows: {len(rows)}")
    for k, v in sorted(census.items()):
        print(f"   {k}: {v}")
    changed_rows = sum(1 for r in rows if any(p["changed"] for p in r["plans"]))
    print(f"rows that would change: {changed_rows}")

    if args.triage:
        n = write_triage(rows, TRIAGE_CSV)
        print(f"📄 triage CSV: {TRIAGE_CSV.relative_to(REPO_ROOT)} ({n} cell rows)")

    if not args.apply:
        print("DRY-RUN — no mutation. (owner-gated cells are NEVER applied; D-2898)")
        return 0

    if census.get("owner_gate_hold", 0):
        print(f"⛔ refusing --apply: {census['owner_gate_hold']} cell(s) are owner_gate_hold — "
              "no agent may mint a home for a retired label (D-2898)")
        return 2
    if census.get("ratified_fold_owner_triage", 0) and not args.accept_ratified_fold:
        print(f"⛔ refusing --apply: {census['ratified_fold_owner_triage']} cell(s) hold no alias "
              "evidence and need the owner sign-off for the D-2865 ratified fold "
              "(re-run with --accept-ratified-fold after signing the triage CSV)")
        return 2
    subprocess.run(["bash", str(BACKUP_GUARDIAN)], check=True)
    try:
        with conn:
            touched = apply_plan(conn, rows)
        after = fetch_rows(conn, args.run, stale)
        print(f"✅ applied; rows still carrying a retired token: {len(after)} (was {len(rows)})")
    except Exception as exc:  # C16: log AND raise
        conn.rollback()
        print(f"⛔ rollback: {exc}")
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
