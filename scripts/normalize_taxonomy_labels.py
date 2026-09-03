#!/usr/bin/env python3
"""
scripts/normalize_taxonomy_labels.py — D2515 data re-derivation (Drift G + compound + alias).
====================================================================================
Applies the three label-normalization fixes (schemas.py D2515) POST-HOC to the
committed `fbs` table, deterministically and LLM-free:

  1. NFKC + dash-fold normalization of every label string (domains / domains_raw /
     discipline / discipline_raw) — collapses unicode variants like
     "human‑computer interaction" (U+2011) ≡ "human–computer interaction" (U+2013)
     ≡ "human-computer interaction" (U+002D).

  2. Compound-label decomposition — a `domains` value of "emerging" whose
     `domains_raw` is a compound ("marketing & advertising") is re-resolved to its
     constituent canonicals via match_domains_to_canonical().

  3. Alias re-resolution — "emerging" domains/disciplines whose raw label is one of
     the newly-added aliases resolve to their canonical.

Merge-based (never destructive): existing non-"emerging" canonical domains are
preserved and unioned with any newly-resolved canonicals; only the "emerging"
placeholder is replaced. Crash-safe (C6): backs up the DB before writing; a single
transaction. Idempotent: re-running finds 0 changes.

Usage:
    /opt/homebrew/bin/python3 scripts/normalize_taxonomy_labels.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH
from pipeline.schemas import match_domains_to_canonical, match_to_canonical, normalize_label


def _to_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return [value]
    return list(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="NFKC-normalize + re-resolve FB taxonomy labels (D2515)")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"  ❌ DB not found: {args.db}")
        return 1

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT rowid, domains, domains_raw, discipline, discipline_raw FROM fbs").fetchall()

    # Phase 1 (read-only): compute the change set.
    updates: list[tuple] = []
    dom_decomposed = 0
    disc_resolved = 0
    nfkc_edits = 0

    for r in rows:
        domains = _to_list(r["domains"])
        domains_raw = _to_list(r["domains_raw"])
        discipline = (r["discipline"] or "")
        discipline_raw = (r["discipline_raw"] or "")

        domains_norm = [normalize_label(d) for d in domains]
        domains_raw_norm = [normalize_label(d) for d in domains_raw]
        discipline_norm = normalize_label(discipline) if discipline else ""
        discipline_raw_norm = normalize_label(discipline_raw) if discipline_raw else ""

        # Merge-based domain re-resolution (only replaces the "emerging" placeholder).
        new_domains = list(domains_norm)
        resolved_domains: list[str] = []
        if "emerging" in new_domains and domains_raw_norm:
            resolved_domains = match_domains_to_canonical(domains_raw_norm)
            existing = [d for d in new_domains if d != "emerging"]
            merged = list(existing)
            for rd in resolved_domains:
                if rd and rd != "emerging" and rd not in merged:
                    merged.append(rd)
            new_domains = merged if merged else ["emerging"]
            if resolved_domains:
                dom_decomposed += 1

        # Discipline re-resolution (only when currently "emerging").
        new_discipline = discipline_norm
        if new_discipline == "emerging" and discipline_raw_norm:
            resolved_disc = match_to_canonical(discipline_raw_norm, "discipline")
            if resolved_disc:
                new_discipline = resolved_disc
                disc_resolved += 1

        domains_changed = json.dumps(new_domains, sort_keys=True) != json.dumps(domains, sort_keys=True)
        discipline_changed = new_discipline != discipline
        if domains_changed or discipline_changed:
            # classify whether an NFKC-only edit contributed
            if (json.dumps(domains_norm, sort_keys=True) != json.dumps(domains, sort_keys=True)
                    or json.dumps(domains_raw_norm, sort_keys=True) != json.dumps(domains_raw, sort_keys=True)
                    or discipline_norm != discipline
                    or discipline_raw_norm != discipline_raw):
                nfkc_edits += 1
            updates.append((r["rowid"], new_domains, domains_raw_norm, new_discipline, discipline_raw_norm))

    if args.dry_run:
        conn.close()
        print(f"  🔍 --dry-run: {len(updates)} FBs would change "
              f"(domains decomposed: {dom_decomposed}, disciplines re-resolved: {disc_resolved}, NFKC edits: {nfkc_edits})")
        return 0

    if not updates:
        conn.close()
        print("  ✅ nothing to re-derive (idempotent)")
        return 0

    # Backup before write (C6)
    backup = args.db.with_suffix(args.db.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(args.db, backup)
    print(f"  💾 DB backed up → {backup.name}")

    # Phase 2 (write): apply in a single transaction.
    for rowid, new_domains, domains_raw_norm, new_discipline, discipline_raw_norm in updates:
        conn.execute(
            "UPDATE fbs SET domains = ?, domains_raw = ?, discipline = ?, discipline_raw = ? WHERE rowid = ?",
            (json.dumps(new_domains), json.dumps(domains_raw_norm), new_discipline, discipline_raw_norm, rowid),
        )
    conn.commit()

    # Recount taxonomy_counts (idempotent full recount, D2514) + reconcile (D2512).
    from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
    reconcile_canonical_status(conn)
    update_counts_from_fbs(conn)
    conn.commit()

    conn.close()
    print(f"  ✅ {len(updates)} FBs re-derived "
          f"(domains decomposed: {dom_decomposed}, disciplines re-resolved: {disc_resolved}, NFKC edits: {nfkc_edits})")
    print(f"  ✅ taxonomy_counts reconciled + recounted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
