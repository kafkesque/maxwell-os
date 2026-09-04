#!/usr/bin/env python3
"""scripts/classify_promotion_labels.py — D2568 BUG-150 promotion (LLM leg).

Classifies the remaining unmapped recurring raw labels (discipline=emerging) using
Qwen3.8-27B as the WORKER. Each label is judged: map -> existing canonical,
promote -> new canonical, or leave -> ambiguous. The proposal is written to JSONL
so an independent verifier (DeepSeek) can confirm it in a separate step (R5).

Run:
    python3 scripts/classify_promotion_labels.py            # classify current recurring labels
    python3 scripts/classify_promotion_labels.py --labels "Ecology,Musicology"  # explicit
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.omlx_call import call_omlx  # noqa: E402
from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.schemas import match_to_canonical  # noqa: E402

_TAXONOMY = _ROOT / "config" / "taxonomy_v5.yaml"
_OUT = _ROOT / "temp" / "promotion_classify_qwen38.jsonl"
_MODEL = "Qwen3.8-27B-MLX-4bit"
_SYSTEM = "You are a precise JSON generator. Return ONLY valid JSON. No markdown, no explanation."
_MIN_COUNT = 3  # C20: only classify labels with >= this many FBs


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


def _recurring_unmapped() -> Counter:
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT discipline_raw FROM fbs WHERE discipline = 'emerging'"
    ).fetchall()
    conn.close()
    c: Counter = Counter()
    for (r,) in rows:
        for x in _to_list(r):
            if not match_to_canonical(x, "domain") and not match_to_canonical(x, "discipline"):
                c[x.strip()] += 1
    return c


def _canonicals() -> dict[str, list[str]]:
    tax = yaml.safe_load(open(_TAXONOMY, encoding="utf-8"))
    return {
        "domain": [d["canonical"] for d in tax["domains"]],
        "discipline": [d["canonical"] for d in tax["disciplines"]],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", type=str, default="", help="Comma-separated explicit labels (default: auto-recurring).")
    ap.add_argument("--min-count", type=int, default=_MIN_COUNT)
    args = ap.parse_args()

    canon = _canonicals()
    if args.labels.strip():
        labels = [l.strip() for l in args.labels.split(",") if l.strip()]
    else:
        c = _recurring_unmapped()
        labels = [l for l, n in c.most_common() if n >= args.min_count]

    if not labels:
        print("no labels to classify")
        return 0
    print(f"classifying {len(labels)} labels: {labels}")

    prompt = (
        "You are a taxonomy designer. Classify each raw label (currently discipline=emerging).\n"
        f"DOMAINS: {', '.join(canon['domain'])}\n"
        f"DISCIPLINES: {', '.join(canon['discipline'])}\n"
        "For each raw label decide one of:\n"
        "  map     -> map to an existing canonical (give target + axis)\n"
        "  promote -> promote to a NEW canonical (no existing fit; give lowercase name + axis)\n"
        "  leave   -> too ambiguous, keep emerging\n"
        f"Labels: {', '.join(labels)}\n"
        'Return ONLY a JSON array like [{"label":"...","action":"map|promote|leave","axis":"domain|discipline","target":"..."}] in the same order. No markdown.'
    )

    text = call_omlx(prompt=prompt, model=_MODEL, system=_SYSTEM, max_tokens=2000, timeout=600)
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("["), t.rfind("]")
    if start < 0 or end < 0:
        print(f"⚠️ no JSON array in response: {text[:300]!r}")
        return 1
    arr = json.loads(t[start:end + 1])

    with open(_OUT, "w", encoding="utf-8") as f:
        for obj in arr:
            f.write(json.dumps(obj) + "\n")
    print(f"\n✅ {len(arr)} classifications -> {_OUT.name}")
    for obj in arr:
        print(f"  {obj}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
