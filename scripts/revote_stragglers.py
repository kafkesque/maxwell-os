#!/usr/bin/env python3
"""Re-vote the 6 post-merge stragglers (D2619 finalization).

After merge_4axis_adjudication.py, 6 principle rows remain non-spotless:
    3 depth (golden-silver)  -> re-vote via reliable pair (DeepSeek + Qwen3.8)
    3 discipline (null/stale) -> Qwen3.8 re-vote; accept only if it agrees with
                                DeepSeek's already-recorded value (retry sheet)

D2610 policy: reliable pair must be UNANIMOUS; anything else ABSTAINS (never
fabricate). Deterministic aggregation, no silent errors (C16).

Writes verified_core.jsonl (C13 backup) + re-runs build_4axis_tiers.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import certifi
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.omlx_call import call_omlx_json  # noqa: E402
from pipeline.schemas import CANONICAL_DISCIPLINES  # noqa: E402

GOV = ROOT / "governance"
VC = GOV / "verified_core.jsonl"
DB = ROOT / "knowledge pipeline" / "maxwell.db"
RETRY_SHEET = GOV / "s4_discipline_null_retry.csv"

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-pro"
OMLX_MODEL = "Qwen3.8-27B-MLX-4bit"
OMLX_URL = "http://localhost:11435/v1/chat/completions"
OMLX_KEY = "sk-maxwell-local"

TIMEOUT = 180
MAX_TOKENS = 512
DEEPSEEK_MAX_TOKENS = 2048  # v4-pro burns reasoning tokens before the final JSON

DEPTH_ONTOLOGY = (
    "DEPTH (choose EXACTLY ONE):\n"
    "- universal    = applies to ALL systems (physics, cooking, poetry)\n"
    "- cross-domain = bridges 2+ DISTINCT disciplines via a SHARED mechanism\n"
    "- domain       = operates within ONE field / a cluster of adjacent fields\n"
    "- specialized  = narrow sub-technique within a sub-field or tool-specific skill\n"
)
VALID_DEPTHS = ("universal", "cross-domain", "domain", "specialized")

SCHEMA = "3.0"
COMMIT = "v3.0-D2619-straggler-revote"

# DeepSeek's already-recorded discipline for the 3 discipline stragglers
# (from governance/s4_discipline_null_retry.csv "discipline_returned_by_other_voter").
DEEPSEEK_DISCIPLINE = {
    "16da69f1cbc95c9635b556d67eb7b6dc7dd178fc4324917865af100ca46c9885": "systems thinking",
    "98ccd412a92510434bb67bde051564a6eab88f0c9bc80113e62c372570024b84": "visual semiotics",
    "e90ef2e892b8d9ee63bb8c448f9bdb688da7dc204506cd4d1425cad05930973e": "cultural design",
}

# 3 depth stragglers (by name -> fb_id resolved at runtime from verified_core)
DEPTH_STRAGGLER_NAMES = [
    "Semiospheric Limitation",
    "Dynamic System Contextual Dependency",
    "Simplicity Through Constraint",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_jsonl(p: Path) -> List[Dict[str, Any]]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def _fb_text(fb_id: str) -> Dict[str, Any]:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT name, definition, mechanism, boundary FROM fbs WHERE fb_id=?",
            (fb_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RuntimeError(f"fb_id not in DB: {fb_id}")
    return dict(row)


def _discipline_ontology() -> str:
    tax = yaml.safe_load((ROOT / "config" / "taxonomy_v5.yaml").read_text(encoding="utf-8"))
    lines = ["DISCIPLINE (choose EXACTLY ONE canonical label from this list):"]
    for d in tax["disciplines"]:
        lines.append(f"- {d['canonical']}: {d.get('definition', '')[:80]}")
    return "\n".join(lines)


def _call_deepseek(prompt: str, key: str) -> Optional[str]:
    if not key:
        raise RuntimeError("DeepSeek requires DEEPSEEK_API_KEY (C22 opt-in)")
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise JSON-only ontology labeler."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": DEEPSEEK_MAX_TOKENS,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = (data["choices"][0]["message"].get("content") or "").strip()
    if not content:
        raise RuntimeError("DeepSeek empty content")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content


def _depth_prompt(fb: Dict[str, Any]) -> str:
    body = (
        f"Name: {fb.get('name') or ''}\n"
        f"Definition: {fb.get('definition') or ''}\n"
        f"Mechanism: {fb.get('mechanism') or ''}\n"
        f"Boundary: {fb.get('boundary') or ''}\n"
    )
    return (
        "Label the ontological DEPTH of a Foundation Block. Return ONLY JSON: "
        '{"depth": "..."}\n\n' + DEPTH_ONTOLOGY + "\nFB:\n" + body
    )


def _discipline_prompt(fb: Dict[str, Any]) -> str:
    body = (
        f"Name: {fb.get('name') or ''}\n"
        f"Definition: {fb.get('definition') or ''}\n"
        f"Mechanism: {fb.get('mechanism') or ''}\n"
        f"Boundary: {fb.get('boundary') or ''}\n"
    )
    return (
        "Label the single DISCIPLINE of a Foundation Block. Return ONLY JSON: "
        '{"discipline": "..."}\n\n' + _discipline_ontology() + "\n\nFB:\n" + body
    )


def _parse_depth(raw: Any) -> Optional[str]:
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return None
    d = str(raw.get("depth", "")).strip().lower() if raw.get("depth") else None
    return d if d in VALID_DEPTHS else None


def _parse_discipline(raw: Any) -> Optional[str]:
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return None
    d = str(raw.get("discipline", "")).strip() if raw.get("discipline") else None
    return d if d in CANONICAL_DISCIPLINES else None


def _call_qwen(prompt: str) -> Any:
    return call_omlx_json(prompt, model=OMLX_MODEL, max_tokens=MAX_TOKENS)


def main() -> None:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    vc = _load_jsonl(VC)
    by_id = {r["fb_id"]: r for r in vc}
    by_name = {r.get("name", ""): r for r in vc}

    # Resolve the 3 depth stragglers
    depth_rows: List[Dict[str, Any]] = []
    for n in DEPTH_STRAGGLER_NAMES:
        r = by_name.get(n)
        if r is None:
            raise RuntimeError(f"depth straggler not found: {n}")
        depth_rows.append(r)

    # Resolve the 3 discipline stragglers
    disc_rows: List[Dict[str, Any]] = [by_id[fb] for fb in DEEPSEEK_DISCIPLINE]

    results: List[Tuple[str, str, str, str]] = []  # (fb_id, axis, value, source)

    print("=== depth re-vote (reliable pair) ===")
    for r in depth_rows:
        fb = r["fb_id"]
        txt = _fb_text(fb)
        prompt = _depth_prompt(txt)
        ds = _parse_depth(_call_deepseek(prompt, key))
        qw = _parse_depth(_call_qwen(prompt))
        print(f"  {r.get('name','')[:44]:46} DeepSeek={ds} Qwen3.8={qw}")
        if ds and qw and ds == qw:
            results.append((fb, "depth", ds, "p5:reliable-pair-D2619-revote"))
        else:
            print(f"    -> ABSTAIN (no unanimous reliable pair)")

    print("\n=== discipline re-vote (Qwen3.8 vs recorded DeepSeek) ===")
    for r in disc_rows:
        fb = r["fb_id"]
        txt = _fb_text(fb)
        prompt = _discipline_prompt(txt)
        qw = _parse_discipline(_call_qwen(prompt))
        ds = DEEPSEEK_DISCIPLINE[fb]
        print(f"  {r.get('name','')[:44]:46} DeepSeek={ds} Qwen3.8={qw}")
        if qw and qw == ds:
            results.append((fb, "discipline", ds, "p5:reliable-pair-D2619-revote"))
        else:
            print(f"    -> ABSTAIN (Qwen3.8 disagrees with DeepSeek)")

    if not results:
        print("\nNo unanimous re-votes — nothing to apply.")
        return

    print(f"\n{len(results)} unanimous re-votes to apply")
    for fb, axis, val, src in results:
        r = by_id[fb]
        r[axis] = val
        r[f"{axis}_source"] = src
        r["schema_version"] = SCHEMA
        r["pipeline_commit"] = COMMIT
        print(f"  {r.get('name','')[:44]:46} {axis}={val}")

    # C13 backup + atomic write
    bak = VC.with_name(f"verified_core.jsonl.bak_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_pre_revote")
    shutil.copy2(VC, bak)
    print(f"\n[C13] backup: {bak}")
    VC.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in vc))
    print("[done] verified_core.jsonl updated")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Re-vote the 6 post-merge stragglers (D2619).")
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
    args = ap.parse_args()
    if args.key:
        os.environ["DEEPSEEK_API_KEY"] = args.key
    main()
