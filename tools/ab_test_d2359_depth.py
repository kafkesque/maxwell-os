#!/usr/bin/env python3
"""
D2359 A/B test — S4 focused-depth on GPT-OSS, accuracy + quality + speed.

Compares three configs on the 50-FB golden depth set (production prompt +
fail-closed parser), measuring:
  * accuracy  — agreement with gold depth label
  * speed     — wall seconds per FB
  * quality   — reasoning chars (CoT length), answer validity, fail-closed rate

Config A = CURRENT production (omlx_call.py): top-level `reasoning_effort=low`
           + `enable_thinking=false` (both SILENTLY DROPPED by oMLX pydantic)
Config B = D2359 fix, lever 1: `chat_template_kwargs={"enable_thinking": false}`
           + system "Reasoning: low" (valid harmony level)
Config C = D2359 fix, lever 2: B + `thinking_budget` (oMLX-native CoT cap)

Sequential, one model (gpt-oss-20b-MXFP4-Q8, ~4.3GB MoE), fail-closed parser.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.stage4_merged_call import DEPTH_FOCUSED_PROMPT, _parse_depth_token  # noqa: E402
from pipeline.pipeline_paths import OMLX_API_KEY  # noqa: E402  (C12: single source, D2552)

GOLDEN_PATH = ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
OUT_PATH = ROOT / "governance" / "s4_depth_d2359_ab_benchmark.json"

URL = "http://127.0.0.1:11435/v1/chat/completions"
H = {"Authorization": f"Bearer {OMLX_API_KEY}", "Content-Type": "application/json"}
MODEL = "gpt-oss-20b-MXFP4-Q8"

DEPTH_ORDER = ["specialized", "domain", "cross-domain", "universal"]


def load_golden() -> list[dict]:
    import yaml
    with open(GOLDEN_PATH) as f:
        d = yaml.safe_load(f)
    fbs = []
    for ex in d["examples"]:
        if not ex.get("should_extract"):
            continue
        fb = ex.get("expected_fb", {})
        if isinstance(fb, dict) and fb and fb.get("depth"):
            fbs.append({
                "name": fb.get("name", ""),
                "definition": fb.get("definition", ""),
                "mechanism": fb.get("mechanism", ""),
                "extraction_type": fb.get("extraction_type", ""),
                "gold_depth": fb["depth"],
            })
    return fbs


def call_depth(fb: dict, config: str, thinking_budget: int | None = None) -> dict:
    """Call depth classification under a given config. Returns rich result dict."""
    prompt = DEPTH_FOCUSED_PROMPT.format(**fb)

    payload: dict = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    if config == "A":
        # CURRENT production: top-level (dropped) + "Reasoning: none" prefix
        payload["messages"] = [
            {"role": "system", "content": "Reasoning: none\n\nAnswer EXACTLY ONE WORD."},
            {"role": "user", "content": prompt},
        ]
        payload["reasoning_effort"] = "low"
        payload["enable_thinking"] = False
    elif config in ("B", "C"):
        payload["messages"] = [
            {"role": "system", "content": "Reasoning: low\n\nAnswer EXACTLY ONE WORD."},
            {"role": "user", "content": prompt},
        ]
        payload["chat_template_kwargs"] = {"enable_thinking": False}
        if config == "C" and thinking_budget:
            payload["thinking_budget"] = thinking_budget

    t0 = time.perf_counter()
    r = requests.post(URL, json=payload, headers=H, timeout=400)
    dt = time.perf_counter() - t0
    r.raise_for_status()
    d = r.json()
    msg = d["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""
    usage = d.get("usage", {})

    pred = None
    error = None
    try:
        if not content.strip():
            raise ValueError("empty content")
        pred = _parse_depth_token(content)
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)[:80]}"

    return {
        "config": config,
        "name": fb["name"],
        "gold_depth": fb["gold_depth"],
        "pred": pred,
        "error": error,
        "secs": round(dt, 2),
        "gen_secs": round(usage.get("total_time", 0.0), 2),
        "completion_tokens": usage.get("completion_tokens", 0),
        "reasoning_chars": len(reasoning),
        "answer": content.strip()[:40],
    }


def summarize(name: str, rows: list[dict]) -> dict:
    ok = [r for r in rows if r["pred"] is not None]
    correct = [r for r in ok if r["pred"] == r["gold_depth"]]
    fail_closed = [r for r in rows if r["error"]]
    times = [r["secs"] for r in rows]
    reas = [r["reasoning_chars"] for r in rows]
    # per-class accuracy
    by_class = {}
    for cls in DEPTH_ORDER:
        cls_rows = [r for r in ok if r["gold_depth"] == cls]
        if cls_rows:
            by_class[cls] = {
                "n": len(cls_rows),
                "correct": sum(1 for r in cls_rows if r["pred"] == r["gold_depth"]),
            }
    return {
        "name": name,
        "n": len(rows),
        "valid_answers": len(ok),
        "fail_closed": len(fail_closed),
        "accuracy": round(len(correct) / len(ok), 3) if ok else 0.0,
        "n_correct": len(correct),
        "avg_secs": round(sum(times) / len(times), 2),
        "median_secs": round(sorted(times)[len(times) // 2], 2),
        "avg_reasoning_chars": round(sum(reas) / len(reas), 1),
        "avg_completion_tokens": round(sum(r["completion_tokens"] for r in rows) / len(rows), 1),
        "by_class": by_class,
    }


def main() -> None:
    fbs = load_golden()
    print(f"Golden depth set: {len(fbs)} FBs")
    print(f"depth dist: {dict(Counter(fb['gold_depth'] for fb in fbs))}")
    print(f"Model: {MODEL}\n")

    configs = [
        ("A", "CURRENT (dropped top-level flags + 'Reasoning: none')", None),
        ("B", "D2359: chat_template_kwargs enable_thinking=false + 'Reasoning: low'", None),
        ("C", "D2359: B + thinking_budget=128", 128),
    ]

    all_rows: dict[str, list[dict]] = {}

    for cfg, label, budget in configs:
        print(f"\n{'='*72}\nCONFIG {cfg}: {label}\n{'='*72}")
        rows = []
        for i, fb in enumerate(fbs, 1):
            try:
                r = call_depth(fb, cfg, budget)
                rows.append(r)
                status = f"{r['pred'] or r['error']}"
                mark = "✓" if r["pred"] == r["gold_depth"] else ("✗" if r["pred"] else "!")
                print(f"  [{i:2d}/{len(fbs)}] {mark} {r['gold_depth']:>12s} -> {status:>15s} "
                      f"{r['secs']:5.1f}s reas={r['reasoning_chars']:4d}  {r['name'][:32]}")
            except Exception as e:
                rows.append({"config": cfg, "name": fb["name"], "gold_depth": fb["gold_depth"],
                             "pred": None, "error": f"TRANSPORT: {str(e)[:80]}", "secs": 0.0,
                             "gen_secs": 0.0, "completion_tokens": 0, "reasoning_chars": 0,
                             "answer": ""})
                print(f"  [{i:2d}/{len(fbs)}] !! TRANSPORT ERROR {e}")
        all_rows[cfg] = rows

    # warm-up: drop the first row of config A (cold reload skew)
    print(f"\n\n{'='*72}\nSUMMARY\n{'='*72}")
    summaries = {}
    for cfg, label, _ in configs:
        rows = all_rows[cfg]
        # drop first call of each config if it's a cold-reload outlier (>2x median of rest)
        if len(rows) >= 4:
            rest = sorted(r["secs"] for r in rows[1:])
            if rows[0]["secs"] > 2 * rest[len(rest) // 2]:
                print(f"  (dropped cold-reload outlier: {cfg} first call {rows[0]['secs']}s)")
                rows = rows[1:]
        s = summarize(f"{cfg} ({label.split(':')[0].strip()})", rows)
        summaries[cfg] = s
        print(f"\n  {s['name']}: acc={s['accuracy']:.1%} ({s['n_correct']}/{s['valid_answers']}) "
              f"valid={s['valid_answers']}/{s['n']} fail_closed={s['fail_closed']} "
              f"avg={s['avg_secs']}s med={s['median_secs']}s "
              f"reas_chars={s['avg_reasoning_chars']} comp_tok={s['avg_completion_tokens']}")
        for cls in DEPTH_ORDER:
            bc = s["by_class"].get(cls)
            if bc:
                print(f"      {cls:>13s}: {bc['correct']}/{bc['n']}")

    # speedup
    if summaries.get("A") and summaries.get("B"):
        a, b = summaries["A"]["avg_secs"], summaries["B"]["avg_secs"]
        if a and b:
            print(f"\n  B vs A speedup: {a/b:.2f}x   C vs A speedup: {a/summaries['C']['avg_secs']:.2f}x")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump({"created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "model": MODEL, "n_fbs": len(fbs),
                   "summaries": summaries, "rows": all_rows}, f, indent=2, default=str)
    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
