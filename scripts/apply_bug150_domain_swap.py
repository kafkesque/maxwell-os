#!/usr/bin/env python3
"""D2535: BUG-150 domain-axis kind-swap (8 business + 3 cross-axis domain-skips).

Moves 11 raw labels that are actually DOMAINS (leaked into `discipline_raw`) onto
the DOMAIN axis. Deterministic, no LLM. These were human-reviewed (Q3 accepted +
cross-axis triage): business/management practice areas are subjects (domains), not
academic fields (disciplines).

Mechanics (C13 / C6):
1. Back up DB + taxonomy_v5.yaml + S4/S5 checkpoints (timestamped, fsync'd).
2. ALIAS: append each raw label to the target DOMAIN canonical's `raw:` list in
   taxonomy_v5.yaml (permanent, so future classification maps it onto the domain axis).
3. KIND-SWAP each affected FB (discipline='emerging' + case-insensitive discipline_raw match):
     domains      += [target canonical]  (dedup; empty/['emerging'] → [target])
     domains_raw  += [raw label]         (dedup, preserved)
     discipline_raw = ''                 (it held a domain label, not a discipline)
     discipline     = 'emerging'         (unchanged)
4. Integrity gate pre/post; single atomic txn; reconcile taxonomy_counts; sync checkpoints.

Usage:
  python3 scripts/apply_bug150_domain_swap.py            # dry-run
  python3 scripts/apply_bug150_domain_swap.py --apply    # backup + integrity + write
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

# raw label (exact DB string, lowercase) -> target DOMAIN canonical
DOMAIN_SWAP: dict[str, str] = {
    # business / management (Q3 accepted)
    "human resource management": "business operations",
    "sales management": "business development",
    "retail management": "business operations",
    "technology management": "business operations",
    "entrepreneurial management": "entrepreneurship",
    "marketing management": "marketing & communications",
    "change management": "organizational behavior",
    "creative management": "leadership",
    # cross-axis residue (triage ② DOMAIN-SKIP)
    "marketing": "marketing & communications",
    "design studies": "design strategy",
    "visual arts": "arts & culture",
}

TAXONOMY_PATH = _PROJECT_ROOT / "config" / "taxonomy_v5.yaml"
S4_CHECKPOINT = _PROJECT_ROOT / "knowledge pipeline" / "stage4_merge" / "t11" / "checkpoint_enriched.jsonl"
S5_CHECKPOINT = _PROJECT_ROOT / "knowledge pipeline" / "stage5_verify" / "t11" / "checkpoint.jsonl"


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_file(path: Path, tag: str) -> Path:
    if not path.exists():
        print(f"  ⚠️  backup skipped (not found): {path}")
        return Path(str(path) + f".bak_{_ts()}_{tag}")
    bak = Path(str(path) + f".bak_{_ts()}_{tag}")
    shutil.copy2(str(path), str(bak))
    with open(bak, "rb") as _f:
        os.fsync(_f.fileno())
    if path.stat().st_size != bak.stat().st_size:
        raise RuntimeError(f"backup size mismatch — aborting: {path}")
    print(f"  🔒 backup: {bak} ({bak.stat().st_size:,} bytes)")
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
        raise RuntimeError(f"integrity gate FAILED ({len(fk)} foreign_key violations)")
    print("  ✅ integrity gate: quick_check ok, foreign_key_check clean")


def _norm(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKC", s or "").replace("–", "-").replace("—", "-").strip().lower()


def _to_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return [v]
    return list(v)


def _edit_taxonomy_yaml(dry_run: bool) -> dict[str, list[str]]:
    data = yaml.safe_load(TAXONOMY_PATH.read_text())
    doms = data["domains"]
    # group raw labels by canonical, with a TitleCase variant per label
    added: dict[str, list[str]] = {}
    for raw, canonical in DOMAIN_SWAP.items():
        entry = next((d for d in doms if d["canonical"] == canonical), None)
        if entry is None:
            raise RuntimeError(f"domain canonical not found: {canonical}")
        existing = {_norm(r) for r in entry.get("raw", [])}
        variants = [raw, " ".join(w.capitalize() for w in raw.split())]
        to_add = [v for v in variants if _norm(v) not in existing and _norm(v) != _norm(canonical)]
        added.setdefault(canonical, []).extend(to_add)
        if to_add:
            entry["raw"] = entry.get("raw", []) + to_add
    if dry_run:
        print("  [dry-run] taxonomy_v5.yaml would add:")
        for c, vs in added.items():
            if vs:
                print(f"    {c}: {vs}")
        return added
    out = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    fd, tmp = tempfile.mkstemp(dir=str(TAXONOMY_PATH.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(out)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(TAXONOMY_PATH))
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print("  ✅ taxonomy_v5.yaml updated (atomic)")
    return added


def _affected(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = []
        for raw, canonical in DOMAIN_SWAP.items():
            cur = conn.execute(
                "SELECT rowid, domains, domains_raw, discipline, discipline_raw FROM fbs "
                "WHERE discipline='emerging' AND LOWER(TRIM(discipline_raw))=LOWER(?) "
                "ORDER BY rowid",
                (raw,),
            )
            for r in cur.fetchall():
                rows.append({"rowid": r["rowid"], "raw": raw, "canonical": canonical,
                             "domains": r["domains"], "domains_raw": r["domains_raw"],
                             "discipline": r["discipline"], "discipline_raw": r["discipline_raw"]})
        return rows
    finally:
        conn.close()


def _compute(row: dict) -> tuple[list, list, str, str, bool]:
    domains = _to_list(row["domains"])
    domains_raw = _to_list(row["domains_raw"])
    canonical = row["canonical"]
    raw = row["raw"]

    new_domains = list(domains)
    if not new_domains or new_domains == ["emerging"]:
        new_domains = [canonical]
    elif canonical not in new_domains:
        new_domains.append(canonical)

    new_domains_raw = list(domains_raw)
    if raw not in new_domains_raw:
        new_domains_raw.append(raw)

    new_discipline_raw = ""  # held a domain label, not a discipline
    new_discipline = "emerging"

    changed = (
        json.dumps(new_domains, sort_keys=True) != json.dumps(domains, sort_keys=True)
        or json.dumps(new_domains_raw, sort_keys=True) != json.dumps(domains_raw, sort_keys=True)
        or new_discipline_raw != (row["discipline_raw"] or "")
    )
    return new_domains, new_domains_raw, new_discipline, new_discipline_raw, changed


def _sync_checkpoints() -> None:
    for s in [_PROJECT_ROOT / "scripts" / "sync_checkpoint_from_db.py",
              _PROJECT_ROOT / "scripts" / "sync_s5_checkpoint_from_db.py"]:
        if not s.exists():
            print(f"  ⚠️  sync script missing: {s.name}", file=sys.stderr)
            continue
        print(f"  🔄 re-syncing checkpoint: {s.name} ...")
        r = subprocess.run([sys.executable, str(s)], cwd=str(_PROJECT_ROOT),
                           capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            print(f"  ⚠️  {s.name} FAILED (rc={r.returncode}): {r.stderr[-500:]}", file=sys.stderr)
        else:
            print(f"  ✅ {s.name} re-synced")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write (backup + integrity gate). Default dry-run.")
    ap.add_argument("--skip-backup", action="store_true")
    ap.add_argument("--skip-integrity", action="store_true")
    ap.add_argument("--no-sync", action="store_true")
    args = ap.parse_args()

    db_path = Path(DB_PATH)
    if not db_path.exists():
        print(f"❌ DB not found: {db_path}", file=sys.stderr)
        return 1

    rows = _affected(db_path)
    from collections import Counter
    by_canonical = Counter(r["canonical"] for r in rows)
    print(f"📊 affected FBs (domain kind-swap): {len(rows)}")
    for c, n in sorted(by_canonical.items()):
        print(f"    {c!r:28} ← {n} FBs")

    if not args.apply:
        print("\n  [dry-run] no writes. Re-run with --apply.")
        _edit_taxonomy_yaml(dry_run=True)
        return 0

    print("\n  🔒 backing up pre-write ...")
    if not args.skip_backup:
        _backup_file(db_path, "pre_domain_swap")
        _backup_file(TAXONOMY_PATH, "pre_domain_swap")
        _backup_file(S4_CHECKPOINT, "pre_domain_swap")
        _backup_file(S5_CHECKPOINT, "pre_domain_swap")

    if not args.skip_integrity:
        _integrity_gate(db_path)

    print("\n  ✏️  updating taxonomy_v5.yaml ...")
    _edit_taxonomy_yaml(dry_run=False)

    print(f"\n  💾 kind-swapping {len(rows)} FBs ...")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for r in rows:
            nd, ndr, ndisc, ndraw, changed = _compute(r)
            if not changed:
                continue
            conn.execute(
                "UPDATE fbs SET domains=?, domains_raw=?, discipline=?, discipline_raw=? WHERE rowid=?",
                (json.dumps(nd), json.dumps(ndr), ndisc, ndraw, r["rowid"]),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    print("  ✅ applied")

    if not args.skip_integrity:
        _integrity_gate(db_path)

    # reconcile taxonomy_counts (domain raw aliases now seeded)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        from pipeline.taxonomy_manager import reconcile_canonical_status, update_counts_from_fbs
        reconcile_canonical_status(conn)
        update_counts_from_fbs(conn)
        conn.commit()
    finally:
        conn.close()
    print("  ✅ taxonomy_counts reconciled")

    if not args.no_sync:
        _sync_checkpoints()

    print("\n✅ BUG-150 domain-axis kind-swap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
