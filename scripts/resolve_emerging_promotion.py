#!/usr/bin/env python3
"""scripts/resolve_emerging_promotion.py — D2568 BUG-150 promotion (deterministic leg).

The kind-swap (bug197_kind_swap) already moved DOMAIN-mapped `discipline_raw` labels
to the domain axis. This script handles the REMAINING discipline=emerging FBs whose
`discipline_raw` is unmapped by `match_to_canonical` — it resolves them
deterministically via the SAME transformations extend_alias_index.py already ships
(suffix strip + compound split), which `match_to_canonical` does NOT apply at runtime:

  * suffix strip  : "Entrepreneurship Studies" -> "entrepreneurship" (domain)
  * compound split: "Graphic Design Theory"    -> "graphic design"   (domain)

Resolution policy (surgical, no label invented):
  * resolved to a DOMAIN     -> add to `domains` (dedup), clear `discipline_raw`
  * resolved to a DISCIPLINE -> set `discipline`
  * a small curated EXCLUSION list skips resolutions that the alias index maps
    wrongly (e.g. "Graph Theory" -> data visualization via the "graph" alias);
    those stay `emerging` (honest gap) rather than gain a wrong label.

Read-only by default (dry-run). `--apply` = C13 backup + integrity gate + atomic
write + idempotent recount (mirrors reclassify_merged_axis.py).

Run:
    python3 scripts/resolve_emerging_promotion.py            # dry-run
    python3 scripts/resolve_emerging_promotion.py --apply    # backup + atomic write
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import match_to_canonical  # noqa: E402

_COMPOUND_RE = re.compile(r"\s*(?:&|\+|/|\band\b|\bvs\.?\b|,)\s*", re.IGNORECASE)
# C20: suffix list mirrors extend_alias_index.py _SUFFIXES.
_SUFFIXES = (
    "research", "studies", "practice", "design", "development", "management",
    "theory", "engineering", "science", "technology", "informatics", "systems",
    "analytics", "processing", "signal",
)
# Curated quality gate: resolutions the alias index gets wrong (stays emerging).
_EXCLUDE = frozenset({
    "graph theory", "industrial/organizational psychology",
    "spirituality studies", "customer experience research",
    "music technology",
})


def _fold(s: str) -> str:
    return s.strip().lower()


def _to_list(v) -> list:
    if not v:
        return []
    if isinstance(v, str):
        try:
            x = json.loads(v)
            return x if isinstance(x, list) else [v]
        except (json.JSONDecodeError, TypeError):
            return [v]
    return list(v)


def _resolve(label: str) -> tuple[str, str] | None:
    """Deterministic suffix/compound resolution to an existing canonical.

    Returns (kind, canonical) or None. Kind is 'domain' or 'discipline'.
    """
    key = _fold(label)
    if key in _EXCLUDE:
        return None
    for kind in ("domain", "discipline"):
        m = match_to_canonical(label, kind)
        if m and m != "emerging":
            return kind, m
    toks = [t for t in _COMPOUND_RE.split(key) if t]
    if len(toks) > 1:
        for kind in ("domain", "discipline"):
            hits = []
            for t in toks:
                m = match_to_canonical(t, kind)
                if m and m != "emerging":
                    hits.append(m)
            if hits:
                return kind, hits[0] if len(hits) == 1 else hits
    for suf in _SUFFIXES:
        if key.endswith(" " + suf):
            stem = key[: -(len(suf) + 1)].strip()
            for kind in ("domain", "discipline"):
                m = match_to_canonical(stem, kind)
                if m and m != "emerging":
                    return kind, m
    return None


def _backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_promotion")
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


def _compute(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT fb_id, name, discipline, discipline_raw, domains "
        "FROM fbs WHERE discipline = 'emerging'"
    ).fetchall()
    updates: list[dict] = []
    for r in rows:
        raw_list = _to_list(r["discipline_raw"])
        if not raw_list:
            continue
        dom_hits: list[str] = []
        disc_hits: list[str] = []
        resolved_raw: set[str] = set()
        for x in raw_list:
            res = _resolve(x)
            if res is None:
                continue
            kind, canon = res
            if kind == "domain":
                dom_hits.append(canon)
            else:
                disc_hits.append(canon)
            resolved_raw.add(x)
        if not dom_hits and not disc_hits:
            continue
        domains = _to_list(r["domains"])
        new_domains = list(domains)
        for d in dom_hits:
            if not new_domains or new_domains == ["emerging"]:
                new_domains = [d]
            elif d not in new_domains:
                new_domains.append(d)
        new_disc = r["discipline"]
        if disc_hits:
            new_disc = disc_hits[0]
        # clear only the RESOLVED raw labels, keep unresolved ones (raw provenance)
        new_raw = [x for x in raw_list if x not in resolved_raw]
        updates.append({
            "fb_id": r["fb_id"],
            "name": r["name"],
            "raw": new_raw,
            "domains": new_domains,
            "discipline": new_disc,
        })
    return updates


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write (default = dry-run).")
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    updates = _compute(conn)
    conn.close()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} FB promotion(s)\n")
    for u in updates[:25]:
        print(f"  {u['name'][:40]:40s} disc={u['discipline']} domains={u['domains']}")
    if len(updates) > 25:
        print(f"  … (+{len(updates) - 25} more)")

    if not args.apply:
        print("\n(dry-run — no write. Re-run with --apply.)")
        return 0

    _backup_db(args.db)
    _integrity_gate(args.db)

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute(
                "UPDATE fbs SET domains=?, discipline=?, discipline_raw=? WHERE fb_id=?",
                (json.dumps(u["domains"]), u["discipline"], json.dumps(u["raw"]), u["fb_id"]),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
    reconcile_canonical_status(conn)
    update_counts_from_fbs(conn)
    conn.close()

    print(f"\n✅ committed {len(updates)} FB promotion(s) atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
