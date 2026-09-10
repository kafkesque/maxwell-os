#!/usr/bin/env python3
"""propagate_p5_final.py — apply the P5 final human adjudication (D2605) to the
golden objects + runtime DB.

Writes the three axes decided by the human arbiter on 2026-09-09:
  A. content_type   (top-level field, sibling of `depth` — D2587 ROLE axis)
  B. discipline     (expected_classification.discipline)
  C. domains        (expected_classification.domains)

Source of truth: governance/p5_adjudication_final.json (single authoritative record,
C12 config-first — no values hardcoded in this script). Mirrors the crash-safe /
backup pattern of propagate_content_type_decisions.py and
propagate_frontier_labels.py (atomic tempfile→fsync→os.replace; C13 DB backup).

Deterministic, LLM-free. Safety: only canonical discipline/domain values are
written (non-canonical values are dropped + logged, D2574 kind-leak discipline).

Usage:
    python3 scripts/propagate_p5_final.py            # golden YAML only
    python3 scripts/propagate_p5_final.py --db       # + DB (C13 backup first)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "governance" / "p5_adjudication_final.json"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
STAGE4 = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
GOLD_FROZEN = ROOT / "config" / "golden" / "gold_frozen.yaml"
SOURCE_MAP = ROOT / "temp" / "golden_source_map.json"
DB = ROOT / "knowledge pipeline" / "maxwell.db"


def canon_values(tax: dict, key: str) -> set[str]:
    out: set[str] = set()
    for e in tax.get(key, []):
        if isinstance(e, dict) and e.get("canonical"):
            out.add(str(e["canonical"]))
        elif isinstance(e, str):
            out.add(e)
    return out


def atomic_write_yaml(path: Path, obj) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(obj, f, sort_keys=False, default_flow_style=False,
                       allow_unicode=True, width=100)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def apply_to_yaml(path: Path, dec: dict, ts: str) -> tuple[int, list[str]]:
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    examples = d["examples"] if isinstance(d, dict) and "examples" in d else d
    ct = dec.get("content_type", {})
    disc = dec.get("discipline", {})
    doms = dec.get("domains", {})
    dropped: list[str] = []
    applied = 0
    for ex in examples:
        if not isinstance(ex, dict):
            continue
        eid = ex.get("id")
        if eid in ct:
            ex["content_type"] = ct[eid]
            applied += 1
        if eid in disc or eid in doms:
            ec = ex.get("expected_classification") or {}
            if eid in disc:
                ec["discipline"] = disc[eid]
                applied += 1
            if eid in doms:
                ec["domains"] = doms[eid]
                applied += 1
            ex["expected_classification"] = ec
    if isinstance(d, dict) and "meta" in d:
        d["meta"]["p5_final_note"] = (
            f"P5 final adjudication D2605 applied ({applied} writes) {ts}"
        )
    atomic_write_yaml(path, d)
    return applied, dropped


def apply_to_db(dec: dict, source_map: dict[str, str]) -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    applied = 0
    try:
        cur.execute("BEGIN")
        for eid, ct in dec.get("content_type", {}).items():
            fid = source_map.get(eid)
            if not fid:
                continue
            cur.execute("UPDATE fbs SET content_type=? WHERE fb_id=?", (ct, fid))
            applied += cur.rowcount
        for eid, dval in dec.get("discipline", {}).items():
            fid = source_map.get(eid)
            if not fid:
                continue
            cur.execute("UPDATE fbs SET discipline=? WHERE fb_id=?", (dval, fid))
            applied += cur.rowcount
        for eid, dv in dec.get("domains", {}).items():
            fid = source_map.get(eid)
            if not fid:
                continue
            cur.execute("UPDATE fbs SET domains=? WHERE fb_id=?",
                        (json.dumps(dv), fid))
            applied += cur.rowcount
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return applied


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", action="store_true",
                    help="also update runtime DB (C13 backup first)")
    args = ap.parse_args()

    dec = json.loads(DECISIONS.read_text(encoding="utf-8"))
    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}
    disc_canon = canon_values(tax, "disciplines")
    doms_canon = canon_values(tax, "domains")

    # safety filter (kind-leak): drop non-canonical discipline/domain values
    bad: list[str] = []
    clean_disc = {eid: v for eid, v in dec.get("discipline", {}).items()
                  if v in disc_canon or bad.append(f"disc {eid}:{v!r}") is None}
    clean_doms = {}
    for eid, vs in dec.get("domains", {}).items():
        ok = [v for v in vs if v in doms_canon]
        if len(ok) != len(vs):
            bad.append(f"domains {eid}: dropped non-canonical {set(vs)-set(ok)}")
        clean_doms[eid] = ok
    dec["discipline"] = clean_disc
    dec["domains"] = clean_doms

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    n1, d1 = apply_to_yaml(STAGE4, dec, ts)
    n2, d2 = apply_to_yaml(GOLD_FROZEN, dec, ts)
    print(f"content_type writes: {len(dec.get('content_type', {}))}")
    print(f"discipline writes:   {len(dec.get('discipline', {}))}")
    print(f"domain writes:       {len(dec.get('domains', {}))}")
    if bad or d1 or d2:
        for b in bad + d1 + d2:
            print(f"  [kind-leak] {b}")
    print(f"stage4_golden_mined.yaml: {n1} writes")
    print(f"gold_frozen.yaml:        {n2} writes")

    if args.db:
        sm = {r["example_id"]: r.get("fb_id")
              for r in json.loads(SOURCE_MAP.read_text(encoding="utf-8"))}
        bak = DB.with_name(f"maxwell.db.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pre_p5final")
        shutil.copy2(DB, bak)
        n3 = apply_to_db(dec, sm)
        print(f"maxwell.db: {n3} writes (backup: {bak.name})")

    if dec.get("flagged"):
        print("\nFLAGGED (NOT applied):")
        for eid, info in dec["flagged"].items():
            print(f"  {eid}: {info.get('problem')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
