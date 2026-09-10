#!/usr/bin/env python3
"""propagate_frontier_labels.py — H4: back-propagate frontier-verified
depth / discipline / domains into the golden objects + runtime DB.

Closes the stale-silver-label gap the 2026-09-09 forensic audit flagged (H4):
the 69 frontier-Qwen3.8 objects carry human-merged final_depth / final_discipline /
final_domains (frontier Qwen3.8 + DeepSeek cross-check + human overrides), but
gold_frozen.yaml / stage4_golden_mined.yaml / maxwell.db still hold the OLD silver
labels (e.g. 00547 discipline "information security" vs frontier "privacy &
surveillance"). This script mirrors propagate_content_type_decisions.py but for the
depth/domain/discipline axes.

Safety: only CANONICAL domains are written (non-canonical kind-leaks — e.g.
"performing arts" in a domains list — are dropped and logged, per D2574 kind-leak
discipline). Depth must be one of the 4 closed values.

Usage:
    python3 scripts/propagate_frontier_labels.py          # golden YAML only
    python3 scripts/propagate_frontier_labels.py --db     # + DB (C13 backup)
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
ADJUDICATION = ROOT / "governance" / "frontier69_final_adjudication.json"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
STAGE4 = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
GOLD_FROZEN = ROOT / "config" / "golden" / "gold_frozen.yaml"
SOURCE_MAP = ROOT / "temp" / "golden_source_map.json"
DB = ROOT / "knowledge pipeline" / "maxwell.db"

VALID_DEPTH = {"universal", "cross-domain", "domain", "specialized"}


def canon_domains(tax: dict) -> set[str]:
    out: set[str] = set()
    for e in tax.get("domains", []):
        if isinstance(e, dict) and e.get("canonical"):
            out.add(str(e["canonical"]))
        elif isinstance(e, str):
            out.add(e)
    return out


def load_frontier_labels(dom_canon: set[str]) -> tuple[dict[str, dict], list[str]]:
    adj = json.loads(ADJUDICATION.read_text(encoding="utf-8"))
    labels: dict[str, dict] = {}
    dropped: list[str] = []
    for eid, o in adj.items():
        depth = o.get("final_depth", "")
        disc = o.get("final_discipline", "")
        doms = [d for d in o.get("final_domains", []) if d in dom_canon]
        raw_doms = o.get("final_domains", [])
        for d in raw_doms:
            if d not in dom_canon:
                dropped.append(f"{eid}: dropped non-canonical domain '{d}'")
        if depth in VALID_DEPTH:
            labels[eid] = {"depth": depth, "discipline": disc, "domains": doms}
    return labels, dropped


def atomic_write_yaml(path: Path, obj) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(obj, f, sort_keys=False, default_flow_style=False,
                       allow_unicode=True, width=100)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def apply_to_yaml(path: Path, labels: dict[str, dict], ts: str) -> int:
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    examples = d["examples"] if isinstance(d, dict) and "examples" in d else d
    applied = 0
    for ex in examples:
        if isinstance(ex, dict) and ex.get("id") in labels:
            ec = ex.get("expected_classification") or {}
            L = labels[ex["id"]]
            ec["discipline"] = L["discipline"]
            ec["domains"] = L["domains"]
            ec["depth"] = L["depth"]
            ex["expected_classification"] = ec
            applied += 1
    if isinstance(d, dict) and "meta" in d:
        d["meta"]["frontier_labels_note"] = (
            f"depth/discipline/domains back-propagated from frontier69_final_adjudication "
            f"({applied} objects) {ts}"
        )
    atomic_write_yaml(path, d)
    return applied


def apply_to_db(labels: dict[str, dict], source_map: dict[str, str]) -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    applied = 0
    try:
        cur.execute("BEGIN")
        for eid, L in labels.items():
            fid = source_map.get(eid)
            if not fid:
                continue
            cur.execute(
                "UPDATE fbs SET discipline=?, domains=?, depth=? WHERE fb_id=?",
                (L["discipline"], json.dumps(L["domains"]), L["depth"], fid),
            )
            if cur.rowcount > 0:
                applied += 1
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
    return applied


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", action="store_true")
    args = ap.parse_args()

    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}
    dom_canon = canon_domains(tax)
    labels, dropped = load_frontier_labels(dom_canon)
    print(f"frontier labels loaded: {len(labels)}")
    if dropped:
        print("kind-leak drops:")
        for d in dropped:
            print(f"  {d}")

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    n1 = apply_to_yaml(STAGE4, labels, ts)
    n2 = apply_to_yaml(GOLD_FROZEN, labels, ts)
    print(f"stage4_golden_mined.yaml: {n1} objects updated")
    print(f"gold_frozen.yaml:        {n2} objects updated")

    if args.db:
        sm = {r["example_id"]: r.get("fb_id") for r in json.loads(SOURCE_MAP.read_text(encoding="utf-8"))}
        bak = DB.with_name(f"maxwell.db.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}_pre_frontier")
        shutil.copy2(DB, bak)
        n3 = apply_to_db(labels, sm)
        print(f"maxwell.db: {n3} rows updated (backup: {bak.name})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
