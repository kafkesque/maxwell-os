#!/usr/bin/env python3
"""scripts/bug197_kind_swap.py — D2519 (BUG-197) deterministic axis-leak kind-swap.

BUG-197 = semantic axis leakage: the S4 classifier emitted DISCIPLINE labels into the
domain axis (`domains_raw`) and DOMAIN labels into the discipline axis
(`discipline_raw`). This is corrected deterministically (LLM-free) via
`match_to_canonical(label, kind)` with the D2422 opposite-axis guard — a label that
resolves to a discipline canonical (and NOT a domain canonical) is a pure discipline
leak, and vice versa. Ambiguous labels that resolve on BOTH axes are LEFT ALONE (they
are legitimately resolvable on either axis — re-adjudicating them is an LLM decision,
not a deterministic swap).

Two directions, field-scoped to `domains`/`domains_raw`/`discipline`/`discipline_raw`
ONLY (definition/mechanism/boundary/consequence/evidence/stamps are untouched):

  A. Discipline label in domains_raw:
     - removed from domains_raw (it belongs on the discipline axis)
     - if discipline == 'emerging' and EXACTLY ONE discipline label recovered:
         discipline = that canonical (recover the lost discipline)
       else (≥2 recovered, or discipline already set): leave discipline as-is
         (redundant leak → just dropped from domains_raw)

  B. Domain label in discipline_raw:
     - added to domains (canonical, dedup) + domains_raw (raw, dedup)
     - discipline_raw cleared (it held a domain label, not a discipline)

Crash-safe (C6/C13): DB backed up before write; single transaction; idempotent full
recount via reconcile_canonical_status() + update_counts_from_fbs().

Run:
    /opt/homebrew/bin/python3 scripts/bug197_kind_swap.py --dry-run
    /opt/homebrew/bin/python3 scripts/bug197_kind_swap.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import match_to_canonical  # noqa: E402


def _to_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return [value]
    return list(value)


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def compute_swap(row) -> tuple[list, list, str, str, bool]:
    """Compute the kind-swap for one FB row. Returns (new_domains, new_domains_raw,
    new_discipline, new_discipline_raw, changed)."""
    domains = _to_list(row["domains"])
    domains_raw = _to_list(row["domains_raw"])
    discipline = (row["discipline"] or "")
    discipline_raw = (row["discipline_raw"] or "")

    # ── Direction A: discipline labels leaked into domains_raw ──
    kept_domains_raw: list[str] = []
    recovered_disciplines: list[str] = []
    for label in domains_raw:
        disc = match_to_canonical(label, "discipline")
        dom = match_to_canonical(label, "domain")
        if disc is not None and dom is None:
            # pure discipline leak → drop from domain axis, recover as discipline
            if disc not in recovered_disciplines:
                recovered_disciplines.append(disc)
        else:
            kept_domains_raw.append(label)

    # ── Direction B: domain label leaked into discipline_raw ──
    recovered_domain: str | None = None
    new_discipline_raw = discipline_raw
    if discipline_raw and discipline_raw.strip():
        dom = match_to_canonical(discipline_raw, "domain")
        disc = match_to_canonical(discipline_raw, "discipline")
        if dom is not None and disc is None:
            # pure domain leak → move to domain axis, clear discipline_raw
            recovered_domain = dom
            new_discipline_raw = ""

    # ── Rebuild discipline (Direction A recovery) ──
    new_discipline = discipline
    if discipline in ("emerging", ""):
        if len(recovered_disciplines) == 1:
            new_discipline = recovered_disciplines[0]
        # ≥2 recovered → ambiguous, leave 'emerging' (conservative, no guess)

    # ── Rebuild domains (Direction B recovery) ──
    new_domains = list(domains)
    if recovered_domain is not None:
        if not new_domains or new_domains == ["emerging"]:
            new_domains = [recovered_domain]
        elif recovered_domain not in new_domains:
            new_domains.append(recovered_domain)

    # ── Rebuild domains_raw (drop A-leaks; preserve B's raw domain label) ──
    new_domains_raw = list(kept_domains_raw)
    if recovered_domain is not None and discipline_raw.strip():
        # preserve the raw domain label (it was emitted, just on the wrong axis)
        if discipline_raw not in new_domains_raw:
            new_domains_raw.append(discipline_raw)

    changed = (
        json.dumps(new_domains, sort_keys=True) != json.dumps(domains, sort_keys=True)
        or json.dumps(new_domains_raw, sort_keys=True) != json.dumps(domains_raw, sort_keys=True)
        or new_discipline != discipline
        or new_discipline_raw != discipline_raw
    )
    return new_domains, new_domains_raw, new_discipline, new_discipline_raw, changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"❌ DB not found: {args.db}")
        return 1

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT rowid, fb_id, domains, domains_raw, discipline, discipline_raw FROM fbs").fetchall()

    updates: list[tuple] = []
    recov_disc = 0
    recov_dom = 0
    dropped_leaks = 0
    for r in rows:
        nd, ndr, ndisc, ndraw, changed = compute_swap(r)
        if not changed:
            continue
        if ndisc != (r["discipline"] or ""):
            recov_disc += 1
        if json.dumps(nd, sort_keys=True) != json.dumps(_to_list(r["domains"]), sort_keys=True):
            recov_dom += 1
        dropped_leaks += 1
        updates.append((r["rowid"], nd, ndr, ndisc, ndraw))

    if args.dry_run:
        conn.close()
        print(f"🔍 --dry-run: {len(updates)} FBs would change "
              f"(discipline recovered: {recov_disc}, domain recovered: {recov_dom})")
        return 0

    if not updates:
        conn.close()
        print("✅ nothing to kind-swap (idempotent)")
        return 0

    backup = args.db.with_suffix(args.db.suffix + f".bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(args.db, backup)
    print(f"💾 DB backed up → {backup.name}")

    for rowid, nd, ndr, ndisc, ndraw in updates:
        conn.execute(
            "UPDATE fbs SET domains = ?, domains_raw = ?, discipline = ?, discipline_raw = ? WHERE rowid = ?",
            (json.dumps(nd), json.dumps(ndr), ndisc, ndraw, rowid),
        )
    conn.commit()

    from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
    reconcile_canonical_status(conn)
    update_counts_from_fbs(conn)
    conn.commit()
    conn.close()

    print(f"✅ {len(updates)} FBs kind-swapped "
          f"(discipline recovered: {recov_disc}, domain recovered: {recov_dom})")
    print("✅ taxonomy_counts reconciled + recounted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
