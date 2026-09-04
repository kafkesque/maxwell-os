#!/usr/bin/env python3
"""scripts/cascade_deregister_domains.py — label-wide cascade deregistration (D2547 follow-up).

Applies the human-review "systematic" verdicts (from `governance/relabel_plan.json`)
label-wide: for each catch-all domain judged SYSTEMATICALLY mislabeled (project
management / business operations / legal & public policy), remove that domain from
every FB the k-NN ∩ T-NLI audit flagged under it (the high-confidence mislabel set in
`governance/mislabel_triage.json`).

Policy (surgical, no label invented):
  * multi-domain flagged FB   → drop the catch-all domain, keep the rest.
  * single-domain flagged FB  → replace with the taxonomy catch-all (`emerging`); the
    raw provenance (`domains_raw`) is preserved for future enrichment.

Read-only by default (dry-run). `--apply` follows the C13/C6 write pattern:
timestamped DB backup → integrity gate (quick_check + foreign_key_check) → single
atomic transaction → idempotent taxonomy_counts recount.

No hardcoded domain names: the systematic set is derived from relabel_plan.json, the
flagged set from mislabel_triage.json, and the catch-all placeholder from
taxonomy_v5.yaml meta.

Run:
    python3 scripts/cascade_deregister_domains.py            # dry-run
    python3 scripts/cascade_deregister_domains.py --apply    # backup + atomic write
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_RELABEL_PLAN = _ROOT / "governance" / "relabel_plan.json"
_MISLABEL_TRIAGE = _ROOT / "governance" / "mislabel_triage.json"
_TAXONOMY = _ROOT / "config" / "taxonomy_v5.yaml"

_AXIS_PREFIX = "domain:"  # C20: the audit encodes axes as "domain:<label>"


def _load_systematic_domains() -> list[str]:
    """Derive the SYSTEMATIC (catch-all) domain set from relabel_plan.json."""
    plan = json.loads(_RELABEL_PLAN.read_text(encoding="utf-8"))
    doms: list[str] = []
    for v in plan.get("label_verdicts", []):
        if v.get("verdict") == "systematic" and v.get("label", "").startswith(_AXIS_PREFIX):
            doms.append(v["label"][len(_AXIS_PREFIX):])
    return doms


def _load_flagged_fbs(domains: list[str]) -> dict[str, set[str]]:
    """Return domain -> set(fb_id) from the k-NN ∩ T-NLI intersection triage."""
    triage = json.loads(_MISLABEL_TRIAGE.read_text(encoding="utf-8"))
    out: dict[str, set[str]] = {d: set() for d in domains}
    for rec in triage.get("triage", []):
        for axis in rec.get("nli_axes", []) + rec.get("knn_axes", []):
            if not axis.startswith(_AXIS_PREFIX):
                continue
            dom = axis[len(_AXIS_PREFIX):]
            if dom in out:
                out[dom].add(rec["fb_id"])
    return out


def _load_catch_all() -> str:
    tax = yaml.safe_load(open(_TAXONOMY, encoding="utf-8"))
    return str((tax.get("meta") or {}).get("catch_all_domain", "emerging"))


def _parse_domains(raw: str | None) -> list[str]:
    if not raw:
        return []
    s = raw.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return [x.strip() for x in s.split("|") if x.strip()]


def _backup_db(db_path: Path) -> Path:
    """C13: timestamped pre-write DB backup, fsync'd + size-verified (C6)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_cascade_dereg")
    shutil.copy2(str(db_path), str(bak))
    with open(bak, "rb") as f:
        os.fsync(f.fileno())
    if db_path.stat().st_size != bak.stat().st_size:
        raise RuntimeError("backup size mismatch — aborting write")
    print(f"  🔒 Backup: {bak} ({bak.stat().st_size:,} bytes)")
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


def _compute_updates(conn: sqlite3.Connection, domains: list[str], catch_all: str) -> list[dict]:
    """Compute per-FB updates, unioning ALL flagged catch-all domains per FB.

    A single FB can be flagged under two catch-all domains (e.g. domains
    ["project management", "business operations"] flagged under both). We must
    remove ALL of them in ONE update — issuing two separate updates from the same
    snapshot would let the second overwrite the first.
    """
    flagged = _load_flagged_fbs(domains)
    # fb_id -> set of catch-all domains to remove
    removals: dict[str, set[str]] = {}
    for dom, ids in flagged.items():
        for fb_id in ids:
            removals.setdefault(fb_id, set()).add(dom)

    updates: list[dict] = []
    for fb_id, remove in sorted(removals.items()):
        row = conn.execute(
            "SELECT name, domains FROM fbs WHERE fb_id = ?", (fb_id,)
        ).fetchone()
        if row is None:
            continue
        name, domains_raw = row["name"], row["domains"]
        cur = _parse_domains(domains_raw)
        drop = {d for d in remove if d in cur}
        if not drop:
            continue
        new = [d for d in cur if d not in drop]
        if not new:
            new = [catch_all]
        updates.append({
            "fb_id": fb_id,
            "name": name,
            "domain": "|".join(sorted(drop)),
            "old": cur,
            "new": new,
        })
    return updates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write (default = dry-run).")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    if not args.db.exists():
        print(f"❌ DB not found: {args.db}")
        return 1

    domains = _load_systematic_domains()
    catch_all = _load_catch_all()
    if not domains:
        print("❌ no SYSTEMATIC domains in relabel_plan.json")
        return 1
    print(f"systematic catch-all domains: {domains}")
    print(f"catch-all placeholder: {catch_all!r}\n")

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    updates = _compute_updates(conn, domains, catch_all)
    conn.close()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} FB domain change(s)\n")
    from collections import Counter
    per_dom = Counter()
    for u in updates:
        for d in u["domain"].split("|"):
            per_dom[d] += 1
    for d in domains:
        print(f"  {d}: {per_dom.get(d, 0)} FBs")

    for u in updates[:20]:
        print(f"    {u['name'][:40]:40s} [{u['domain']}] {u['old']} -> {u['new']}")
    if len(updates) > 20:
        print(f"    … (+{len(updates) - 20} more)")

    if not args.apply:
        print("\n  (dry-run — no write. Re-run with --apply to commit.)")
        return 0

    _backup_db(args.db)
    _integrity_gate(args.db)

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute(
                "UPDATE fbs SET domains=? WHERE fb_id=?",
                (json.dumps(u["new"]), u["fb_id"]),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    # Idempotent recount (separate from the atomic data write; these helpers
    # manage their own transactions via conn.commit()).
    from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
    reconcile_canonical_status(conn)
    update_counts_from_fbs(conn)
    conn.close()

    print(f"\n✅ committed {len(updates)} FB domain deregistration(s) atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
