#!/usr/bin/env python3
"""propagate_content_type_decisions.py — P1: write human-adjudicated content_type
back into the golden objects + runtime DB (closes the C1 inert-adjudication gap).

Forensic audit (2026-09-09) found content_type decisions lived ONLY in review-
tracking artifacts (ledger + boundary corpus) and never reached the objects the
pipeline consumes. This script propagates the merged human verdicts to:

  1. config/golden/stage4_golden_mined.yaml  (adds top-level content_type)
  2. config/golden/gold_frozen.yaml          (adds top-level content_type)
  3. knowledge pipeline/maxwell.db           (fbs.content_type, --db flag, C13 backup)

Source of truth (merged, ledger wins on conflict):
  - governance/content_type_human_decisions.jsonl  (append-only, last-wins)
  - config/golden/d2587_boundary_corpus.yaml       (9 cases + 4 principle flips)

Deterministic, LLM-free, crash-safe writes (C6). content_type is a top-level field
(sibling of `depth`), NOT nested in expected_classification — content_type is the
D2587 ROLE axis, verified separately from the S4 discipline/domains/depth classifier.

Usage:
    python3 scripts/propagate_content_type_decisions.py            # golden YAML only
    python3 scripts/propagate_content_type_decisions.py --db       # + DB (backup first)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "governance" / "content_type_human_decisions.jsonl"
BOUNDARY = ROOT / "config" / "golden" / "d2587_boundary_corpus.yaml"
STAGE4 = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
GOLD_FROZEN = ROOT / "config" / "golden" / "gold_frozen.yaml"
SOURCE_MAP = ROOT / "temp" / "golden_source_map.json"
DB = ROOT / "knowledge pipeline" / "maxwell.db"


def load_ledger() -> dict[str, str]:
    """Append-only ledger, last-wins per example_id."""
    out: dict[str, str] = {}
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("content_type"):
                out[r["example_id"]] = r["content_type"]
    return out


def load_boundary() -> dict[str, str]:
    """d2587_boundary_corpus: 9 seed cases + 4 confirmed principle flips."""
    out: dict[str, str] = {}
    d = yaml.safe_load(BOUNDARY.read_text(encoding="utf-8")) or {}
    for c in d.get("cases", []):
        eid = c.get("example_id")
        ct = c.get("disposition") or c.get("content_type_derived")
        if eid and ct:
            out[eid] = ct
    for eid in d.get("confirmed_principle_flips", []):
        if eid:
            out[eid] = "principle"
    return out


def merged_decisions() -> dict[str, str]:
    merged = load_boundary()
    merged.update(load_ledger())  # ledger wins
    return merged


def atomic_write_yaml(path: Path, obj) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(obj, f, sort_keys=False, default_flow_style=False,
                       allow_unicode=True, width=100)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def apply_to_yaml(path: Path, decisions: dict[str, str], note_suffix: str) -> int:
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    examples = d["examples"] if isinstance(d, dict) and "examples" in d else d
    applied = 0
    for ex in examples:
        if isinstance(ex, dict) and ex.get("id") in decisions:
            ex["content_type"] = decisions[ex["id"]]
            applied += 1
    # provenance note (R14 — no silent changes)
    if isinstance(d, dict) and "meta" in d:
        prev = d["meta"].get("content_type_note", "")
        d["meta"]["content_type_note"] = (
            f"content_type added by propagate_content_type_decisions.py "
            f"({applied} human-adjudicated rows) {note_suffix}"
        )
    atomic_write_yaml(path, d)
    return applied


def backup_db() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = DB.with_name(f"maxwell.db.bak_{ts}_pre_contenttype")
    shutil.copy2(DB, bak)
    return bak


def apply_to_db(decisions: dict[str, str], source_map: dict[str, str]) -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    applied = 0
    try:
        cur.execute("BEGIN")
        for eid, ct in decisions.items():
            fid = source_map.get(eid)
            if not fid:
                continue
            cur.execute("UPDATE fbs SET content_type=? WHERE fb_id=?", (ct, fid))
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
    ap.add_argument("--db", action="store_true", help="also update runtime DB (C13 backup first)")
    args = ap.parse_args()

    decisions = merged_decisions()
    print(f"merged human decisions: {len(decisions)}")
    print("distribution:", dict(Counter(decisions.values())))

    ts = datetime.now(timezone.utc).isoformat()
    n1 = apply_to_yaml(STAGE4, decisions, f"| {ts}")
    n2 = apply_to_yaml(GOLD_FROZEN, decisions, f"| {ts}")
    print(f"stage4_golden_mined.yaml: {n1} rows tagged")
    print(f"gold_frozen.yaml:        {n2} rows tagged")

    if args.db:
        sm = {r["example_id"]: r.get("fb_id") for r in json.loads(SOURCE_MAP.read_text(encoding="utf-8"))}
        bak = backup_db()
        n3 = apply_to_db(decisions, sm)
        print(f"maxwell.db: {n3} rows updated (backup: {bak.name})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
