#!/usr/bin/env python3
"""reverify_content_type_108.py — re-verify content_type of the 108 queue rows.

D2619/D2626: the 108 expansion_queue_108.jsonl rows carry `d2615_content_type:
principle` but were kept OUT of the frozen 216 anchor because a ~10% forensic
sample showed methods/case-studies mislabeled as principle. This script re-verifies
the content_type axis (7-way: principle | process_template | process_instance |
tool_instruction | growth_edge | noise_drop | quarantine) using Qwen3.8-27B as the
worker with a focused D2587-rule prompt.

Read-only + plan-only: emits governance/content_type_reverify_108.json (verdicts),
NEVER mutates the DB. The depth+discipline+domains re-vote for the rows that stay
principle is a SEPARATE follow-up (grows the anchor beyond 216).

Usage:
    python3 scripts/reverify_content_type_108.py --limit 5
    python3 scripts/reverify_content_type_108.py
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.omlx_call import call_omlx_json  # noqa: E402

QUEUE = ROOT / "governance" / "expansion_queue_108.jsonl"
DB = ROOT / "knowledge pipeline" / "maxwell.db"
OUT = ROOT / "governance" / "content_type_reverify_108.json"

MODEL = "Qwen3.8-27B-MLX-4bit"
MAX_TOKENS = 1024

# D2587: the 7-value axis (5 roles + 2 dispositions). Read from config/content_types.yaml
# via pipeline.content_types (C12: no hardcoded enum).
from pipeline.content_types import CONTENT_TYPES, CONTENT_TYPE_DISPOSITIONS  # noqa: E402

CT_ENUM = '"' + '"|"'.join(sorted(CONTENT_TYPES | CONTENT_TYPE_DISPOSITIONS)) + '"'

PROMPT = """Classify the CONTENT-TYPE of this extracted knowledge object. Content-type is the
functional ROLE (what kind of object), one of: {enum}.

- principle: a single TRANSFERABLE prescriptive/conceptual insight (why/when something
  works; a normative heuristic that filters across 3+ domains). NOT a concrete case study.
- process_template: a repeatable how-to METHOD with >=2 ordered steps/gates (a sequence
  of actions to follow).
- process_instance: a CONCRETE case study / worked example of a method actually executed
  (names specific actors, a specific event, a specific outcome).
- tool_instruction: a tool/software-specific command or feature (how to use a named tool).
- growth_edge: a speculative/unresolved open tension or unverified correlation.
- noise_drop: a bare descriptive fact/historical summary with no prescriptive filter.
- quarantine: carries SOME value but no clean role (ambiguous) — hold, do not force.

Return ONLY JSON (no markdown): {{"content_type": "one of the above", "reason": "..."}}

Name: {name}
Definition: {definition}
Mechanism: {mechanism}
Application: {application}
"""


def _load_queue() -> List[Dict[str, Any]]:
    return [json.loads(l) for l in QUEUE.read_text().splitlines() if l.strip()]


def _load_row(fb_id: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        r = conn.execute(
            "SELECT fb_id, name, definition, mechanism, application FROM fbs WHERE fb_id=?",
            (fb_id,),
        ).fetchone()
    finally:
        conn.close()
    return dict(r) if r else {}


def _load_prior() -> Dict[str, Dict[str, Any]]:
    if not OUT.exists():
        return {}
    try:
        d = json.loads(OUT.read_text())
    except Exception:
        return {}
    return {v["fb_id"]: v for v in d.get("verdicts", [])}


def _judge(row: Dict[str, Any]) -> Dict[str, Any]:
    prompt = PROMPT.format(
        enum=CT_ENUM,
        name=row["name"],
        definition=row["definition"],
        mechanism=row["mechanism"],
        application=row["application"] or "",
    )
    raw = call_omlx_json(prompt, model=MODEL, max_tokens=MAX_TOKENS)
    if not isinstance(raw, dict):
        return {"content_type": "error", "reason": f"non-dict: {type(raw).__name__}"}
    ct = raw.get("content_type", "error")
    valid = CONTENT_TYPES | CONTENT_TYPE_DISPOSITIONS
    if ct not in valid:
        return {"content_type": "error", "reason": f"bad content_type {ct!r}: {raw}"}
    return {"content_type": ct, "reason": raw.get("reason", "")}


def _write(verdicts: List[Dict[str, Any]]) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(OUT.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({
                "policy": "content_type re-verify (D2587 7-way); read-only, never mutates DB",
                "model": MODEL,
                "verdicts": verdicts,
            }, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, OUT)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run(limit: int = 0) -> None:
    rows = _load_queue()
    prior = _load_prior()
    todo = [r for r in rows if r["fb_id"] not in prior]
    if limit:
        todo = todo[:limit]
    print(f"queue rows: {len(rows)}, to re-verify: {len(todo)}, already done: {len(prior)}")

    verdicts: List[Dict[str, Any]] = [v for v in prior.values()]
    for r in todo:
        row = _load_row(r["fb_id"])
        if not row:
            verdicts.append({"fb_id": r["fb_id"], "content_type": "error", "reason": "missing DB row"})
        else:
            res = _judge(row)
            verdicts.append({
                "fb_id": r["fb_id"],
                "name": row["name"],
                "d2615_content_type": r.get("d2615_content_type"),
                **res,
            })
            print(f"  {res['content_type']:18} {row['name'][:48]}", flush=True)
        _write(verdicts)

    from collections import Counter
    dist = Counter(v["content_type"] for v in verdicts)
    print(f"\ndistribution: {dict(dist)}")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Re-verify content_type of the 108 expansion-queue rows (D2619/D2626).")
    ap.add_argument("--limit", type=int, default=0, help="re-verify only first N rows (smoke test)")
    args = ap.parse_args()
    run(limit=args.limit)
