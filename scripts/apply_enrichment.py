#!/usr/bin/env python3
"""scripts/apply_enrichment.py — cross-domain enrichment (D2566).

Adds missing canonical domains to under-labeled FBs whose raw labels map through
the FULL domain alias index (taxonomy_v5.yaml raw + synonym_map.yaml + alias_map.yaml
domain_aliases + canonical-self), EXCLUDING the catch-all domains that the audits
flagged as systematically over-assigned (those are removed in Phase 1, never
re-added here). Updates only the `domains` canonical array; `domains_raw` untouched.

Compound raw labels ("marketing & branding", "ux/ui design") are decomposed so a
cross-disciplinary FB gains ALL its constituent canonical domains (semantic-first
retrieval, D2565).

Usage:
  python3 scripts/apply_enrichment.py              # dry-run
  python3 scripts/apply_enrichment.py --apply      # backup + integrity + atomic write
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

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_TAXONOMY = _ROOT / "config" / "taxonomy_v5.yaml"
_SYNONYM_MAP = _ROOT / "config" / "synonym_map.yaml"
_ALIAS_MAP = _ROOT / "config" / "alias_map.yaml"

# catch-all domains the audits flagged as systematically over-assigned (Phase 1 removes these)
_CATCHALL: frozenset[str] = frozenset({
    "project management", "business operations", "organizational behavior",
    "leadership", "marketing & communications", "legal & public policy",
    "editorial & advertising",
})

_COMPOUND_RE = re.compile(r"\s*(?:&|\+|/|\band\b|\bvs\.?\b|,)\s*", re.IGNORECASE)


def _domain_index() -> dict[str, list[str]]:
    """Build the full domain raw->canonical index (list-valued, D2566).

    Sources: taxonomy_v5.yaml (raw + canonical-self), synonym_map.yaml (synonyms
    + keywords), alias_map.yaml domain_aliases (single OR compound list).
    """
    idx: dict[str, list[str]] = {}

    def add(raw: str, canon: str) -> None:
        key = raw.strip().lower()
        if not key:
            return
        if canon not in idx.setdefault(key, []):
            idx[key].append(canon)

    tax = yaml.safe_load(open(_TAXONOMY, encoding="utf-8")) or {}
    for d in tax.get("domains", []):
        add(d["canonical"], d["canonical"])
        for r in d.get("raw", []):
            add(r, d["canonical"])

    if _SYNONYM_MAP.exists():
        sm = yaml.safe_load(open(_SYNONYM_MAP, encoding="utf-8")) or {}
        for entry in (sm.get("synonyms", {}) or {}).values():
            c = entry.get("canonical", "").strip()
            if not c:
                continue
            add(c, c)
            # SYNONYMS only — keywords are loose search terms (e.g. "e-commerce" →
            # "finance & investment") and would produce false enrichments (D2566).
            for s in entry.get("synonyms", []):
                add(s, c)

    if _ALIAS_MAP.exists():
        am = yaml.safe_load(open(_ALIAS_MAP, encoding="utf-8")) or {}
        for raw, tgt in (am.get("domain_aliases", {}) or {}).items():
            tgts = tgt if isinstance(tgt, list) else [tgt]
            for t in tgts:
                add(str(raw), str(t))

    return idx


def _expand(raw: str, idx: dict[str, list[str]]) -> set[str]:
    """Map one raw domain label to its canonical set (incl. compound split)."""
    out: set[str] = set()
    key = raw.strip().lower()
    if key in idx:
        out.update(idx[key])
    toks = [t for t in _COMPOUND_RE.split(key) if t]
    if len(toks) > 1:
        for t in toks:
            if t in idx:
                out.update(idx[t])
    return out


def _parse(v: str | None) -> list[str]:
    if not v:
        return []
    s = v.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return [x.strip() for x in s.split("|") if x.strip()]


def _backup_db(db_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_enrich")
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


def _compute(idx: dict[str, list[str]], conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT fb_id, name, domains, domains_raw FROM fbs").fetchall()
    out: list[dict] = []
    for r in rows:
        d = _parse(r["domains"])
        dr = _parse(r["domains_raw"])
        if len(d) == 1 and d[0] != "emerging" and len(dr) >= 2:
            canon: set[str] = set()
            for x in dr:
                canon |= _expand(x, idx)
            added = sorted(canon - set(d) - _CATCHALL)
            if added:
                out.append({
                    "fb_id": r["fb_id"], "name": r["name"],
                    "old": d, "new": sorted(set(d) | set(added)), "added": added,
                })
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="cross-domain enrichment (D2566).")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    idx = _domain_index()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    updates = _compute(idx, conn)
    conn.close()

    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(updates)} FB(s) to enrich\n")
    for u in updates[:40]:
        print(f"  {u['name'][:48]:48s} {u['old']} -> +{u['added']}")
    if len(updates) > 40:
        print(f"  … and {len(updates) - 40} more")

    if not args.apply:
        print("\n  (dry-run — no write. Re-run with --apply to commit.)")
        return 0

    _backup_db(DB_PATH)
    _integrity_gate(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute("UPDATE fbs SET domains=? WHERE fb_id=?",
                         (json.dumps(u["new"]), u["fb_id"]))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    print(f"\n✅ committed {len(updates)} enrichment(s) atomically.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
