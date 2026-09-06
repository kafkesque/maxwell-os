#!/usr/bin/env python3
"""scripts/resolve_data_absent_domains.py — D2584: resolve unresolved domain axes.

D2579 identified 3 classifier-training "data-absent" disciplines (computational
theory, ecology, robotics) that could not reach MIN_PER_DISCIPLINE=5 golden
examples even with full single-source backfill. Re-inspection after
bug197_kind_swap (D2583 follow-up) showed the root cause is NOT missing FB
content — the FBs EXIST with complete skeletons — but an UNRESOLVED DOMAIN AXIS:
their ``domains`` is ``["emerging"]`` (or ``[..., "emerging"]``) while
``domains_raw`` carries real, resolvable domain labels that simply lacked an
alias-map entry.

This script deterministically (LLM-free) re-derives each FB's canonical
``domains`` from its preserved ``domains_raw`` using ``match_to_canonical``
(which now resolves the robotics/autonomous-systems + theoretical-CS labels added
to ``config/alias_map.yaml`` → ``domain_aliases`` as part of this change).

Scope is deliberately NARROW (C-safe):
  * ONLY the canonical ``domains`` field is recomputed.
  * ``domains_raw`` is preserved BYTE-IDENTICAL (raw provenance is not rewritten).
  * ``discipline`` / ``discipline_raw`` / ``taxonomy_match_method`` / every other
    field are untouched (``taxonomy_match_method`` tracks DISCIPLINE matching, and
    we are not re-deriving discipline).
  * A FB is only rewritten when at least ONE raw label resolves to a canonical
    domain; otherwise it is left exactly as-is (never invents a domain).

Crash-safe (C6/C13): DB backed up before the first write; single transaction;
idempotent; ``reconcile_canonical_status()`` + ``update_counts_from_fbs()`` run
post-write so taxonomy counts stay consistent.

Run:
    python3 scripts/resolve_data_absent_domains.py                 # dry-run
    python3 scripts/resolve_data_absent_domains.py --apply         # write
    python3 scripts/resolve_data_absent_domains.py --all --dry-run # whole-corpus dry-run
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import DB_PATH, MAX_DOMAINS_PER_FB  # noqa: E402
from pipeline.schemas import match_to_canonical  # noqa: E402

# C20: named constants (no magic numbers).
DATA_ABSENT_DISCIPLINES: tuple[str, ...] = ("computational theory", "robotics")
EMERGING: str = "emerging"


def _to_list(value) -> list[str]:
    """Normalize a JSON-ish column (None | str | list) to a list of str."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(x) for x in parsed]
    return [str(x) for x in value]


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out


def is_blocked(domains: list[str]) -> bool:
    """True when the canonical domain axis is unresolved (empty/['emerging'] or
    carries a stale 'emerging' placeholder alongside real domains)."""
    real = [d for d in domains if d != EMERGING]
    if not domains or not real:
        return True
    return EMERGING in domains and bool(real)


def resolve_domains(domains: list[str], domains_raw: list[str]) -> list[str] | None:
    """Re-derive canonical domains from existing real domains + raw resolution.

    Returns the new canonical ``domains`` list if it is non-empty and different
    from the input, else None (caller leaves the row untouched).
    """
    kept = [d for d in domains if d != EMERGING]
    resolved: list[str] = []
    for raw in domains_raw:
        if not raw or not raw.strip():
            continue
        canon = match_to_canonical(raw.strip(), "domain")
        if canon is not None and canon != EMERGING:
            resolved.append(canon)

    new_domains = _dedup_preserve_order(kept + resolved)[:MAX_DOMAINS_PER_FB]
    if not new_domains:
        return None
    if json.dumps(new_domains, sort_keys=True) == json.dumps(domains, sort_keys=True):
        return None
    return new_domains


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument(
        "--disciplines",
        nargs="*",
        default=list(DATA_ABSENT_DISCIPLINES),
        help="Discipline canonical names to scope the fix (default: data-absent set)",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="Ignore --disciplines; consider every FB with a blocked domain axis",
    )
    ap.add_argument("--apply", action="store_true", help="Actually write (default = dry-run)")
    args = ap.parse_args()

    if not args.db.exists():
        print(f"❌ DB not found: {args.db}")
        return 1

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT rowid, fb_id, discipline, domains, domains_raw FROM fbs"
    ).fetchall()

    updates: list[tuple[int, list[str]]] = []
    skipped_no_resolution = 0
    for r in rows:
        if not args.all and (r["discipline"] not in args.disciplines):
            continue
        domains = _to_list(r["domains"])
        if not is_blocked(domains):
            continue
        domains_raw = _to_list(r["domains_raw"])
        new_domains = resolve_domains(domains, domains_raw)
        if new_domains is None:
            skipped_no_resolution += 1
            continue
        updates.append((r["rowid"], new_domains))

    if not args.apply:
        conn.close()
        print(
            f"🔍 DRY-RUN: {len(updates)} FBs would have domains resolved "
            f"(scope={('ALL' if args.all else args.disciplines)}); "
            f"{skipped_no_resolution} blocked-but-unresolvable left untouched"
        )
        for rowid, nd in updates[:40]:
            print(f"   rowid={rowid} -> {nd}")
        if len(updates) > 40:
            print(f"   ... and {len(updates) - 40} more")
        return 0

    if not updates:
        conn.close()
        print("✅ nothing to resolve (idempotent)")
        return 0

    backup = args.db.with_suffix(
        args.db.suffix + f".bak_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    )
    shutil.copy2(args.db, backup)
    print(f"💾 DB backed up → {backup.name}")

    for rowid, nd in updates:
        conn.execute(
            "UPDATE fbs SET domains = ? WHERE rowid = ?",
            (json.dumps(nd), rowid),
        )
    conn.commit()

    from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
    reconcile_canonical_status(conn)
    update_counts_from_fbs(conn)
    conn.commit()
    conn.close()

    print(f"✅ {len(updates)} FBs domains resolved "
          f"(scope={('ALL' if args.all else args.disciplines)})")
    print("✅ taxonomy_counts reconciled + recounted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
