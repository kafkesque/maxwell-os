#!/usr/bin/env python3
"""judge_suffix_duplicates.py — mechanism-aware judge for the 32 "(N)"-suffix pairs.

D2621/D2626: the 32 high_confidence_suffix_candidates are name-collision pairs
(base name vs "base name (N)"). A "(N)" suffix is the STRONGEST duplicate signal
(D2069 disambiguation), but D2621 is explicit: name-stem collision is NOT enough —
a true duplicate must share the same mechanism AND application. So each pair is
sent to the mechanism-aware judge (Qwen3.8-27B) which decides TRUE-duplicate vs
DISTINCT by comparing definition + mechanism + application.

Read-only + plan-only: emits governance/dedup_suffix_judgments.json (per-pair
verdict + the duplicate_of map), NEVER mutates the DB. Dedup policy (D2625, user
locked): mark duplicate_of + QUARANTINE, never delete (R-D410 safe_delete is the
only destructive path and is NOT invoked here).

Usage:
    python3 scripts/judge_suffix_duplicates.py --limit 5   # smoke-test first 5 pairs
    python3 scripts/judge_suffix_duplicates.py             # all 32 pairs
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.omlx_call import call_omlx_json  # noqa: E402

PLAN = ROOT / "governance" / "dedup_merge_plan.json"
DB = ROOT / "knowledge pipeline" / "maxwell.db"
OUT = ROOT / "governance" / "dedup_suffix_judgments.json"

MODEL = "Qwen3.8-27B-MLX-4bit"
MAX_TOKENS = 2048


def _load_plan() -> List[Dict[str, Any]]:
    return json.loads(PLAN.read_text()).get("high_confidence_suffix_candidates", [])


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


def _judge_pair(base: Dict[str, Any], dup: Dict[str, Any]) -> Dict[str, Any]:
    prompt = (
        "You are deduplicating Foundation Blocks (reusable design principles) in a RAG "
        "knowledge base. Two FBs are TRUE duplicates ONLY if they share the SAME mechanism "
        "AND application — i.e. the same principle stated in different words. They are "
        "DISTINCT if the mechanism differs (even slightly), or if one is a specific facet "
        "of the other.\n\n"
        "Return ONLY JSON (no markdown): {\"verdict\": \"duplicate\"|\"distinct\", \"reason\": \"...\"}\n\n"
        f"[A] Name: {base['name']}\nDefinition: {base['definition']}\nMechanism: {base['mechanism']}\n"
        f"Application: {base['application'] or ''}\n\n"
        f"[B] Name: {dup['name']}\nDefinition: {dup['definition']}\nMechanism: {dup['mechanism']}\n"
        f"Application: {dup['application'] or ''}"
    )
    raw = call_omlx_json(prompt, model=MODEL, max_tokens=MAX_TOKENS)
    if not isinstance(raw, dict):
        return {"verdict": "error", "reason": f"non-dict response: {type(raw).__name__}"}
    verdict = raw.get("verdict", "error")
    if verdict not in ("duplicate", "distinct"):
        return {"verdict": "error", "reason": f"bad verdict {verdict!r}: {raw}"}
    return {"verdict": verdict, "reason": raw.get("reason", "")}


def _load_prior() -> Dict[str, Dict[str, Any]]:
    """Load previously-judged pairs (resumable: skip already-judged dup_fb_ids)."""
    if not OUT.exists():
        return {}
    try:
        d = json.loads(OUT.read_text())
    except Exception:
        return {}
    return {v["dup_fb_id"]: v for v in d.get("verdicts", [])}


def judge(limit: int = 0) -> None:
    cands = _load_plan()
    prior = _load_prior()
    todo = [c for c in cands if c["dup_fb_id"] not in prior]
    if limit:
        todo = todo[:limit]
    print(f"suffix pairs to judge: {len(todo)} (already judged: {len(prior)})")

    verdicts: List[Dict[str, Any]] = [v for v in prior.values()]
    for c in todo:
        base = _load_row(c["base_fb_id"])
        dup = _load_row(c["dup_fb_id"])
        if not base or not dup:
            verdicts.append({
                "base_fb_id": c["base_fb_id"], "dup_fb_id": c["dup_fb_id"],
                "base_name": c["base"], "verdict": "error",
                "reason": "missing row in DB",
            })
        else:
            res = _judge_pair(base, dup)
            verdicts.append({
                "base_fb_id": c["base_fb_id"], "dup_fb_id": c["dup_fb_id"],
                "base_name": base["name"], "dup_name": dup["name"],
                **res,
            })
            print(f"  {res['verdict']:10} {base['name'][:40]:42} vs {dup['name'][:40]}", flush=True)
        _write(verdicts)

    dup_count = sum(1 for v in verdicts if v["verdict"] == "duplicate")
    distinct_count = sum(1 for v in verdicts if v["verdict"] == "distinct")
    err_count = sum(1 for v in verdicts if v["verdict"] == "error")
    print(f"\nduplicates: {dup_count}, distinct: {distinct_count}, errors: {err_count}")
    print(f"wrote {OUT}")


def _write(verdicts: List[Dict[str, Any]]) -> None:
    """C6: incremental atomic write so a mid-run kill never loses completed pairs."""
    import os
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=str(OUT.parent), prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({
                "policy": "mark duplicate_of + QUARANTINE (NEVER delete; R-D410 safe_delete only destructive path)",
                "model": MODEL,
                "duplicate_of": {
                    v["dup_fb_id"]: v["base_fb_id"] for v in verdicts if v["verdict"] == "duplicate"
                },
                "distinct_kept": [
                    v["dup_fb_id"] for v in verdicts if v["verdict"] == "distinct"
                ],
                "errors": [v for v in verdicts if v["verdict"] == "error"],
                "verdicts": verdicts,
            }, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, OUT)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Mechanism-aware judge for (N)-suffix duplicate pairs (D2621/D2626).")
    ap.add_argument("--limit", type=int, default=0, help="judge only the first N pairs (smoke test)")
    args = ap.parse_args()
    judge(limit=args.limit)
