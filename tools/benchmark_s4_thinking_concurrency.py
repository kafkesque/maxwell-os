#!/usr/bin/env python3
"""
X8 + X9 benchmark — S4 thinking_budget sweep + concurrency (2026-08-15).

X8 (thinking_budget on the MERGED CRIBS call): sweep the oMLX-native
`thinking_budget` (None/256/384/512) on the production merged classification
prompt and measure wall time + response completeness (content present + valid
JSON). Config currently has `thinking_budget: null` for the merged call; this
measures whether capping CoT helps or truncates the 10-field JSON.

X9 (concurrency): run the S4 focused-depth classification with 1/2/3 concurrent
workers and measure total wall time, to determine whether OMLX parallelizes
concurrent requests or serializes them (the premise behind any ThreadPool
optimization in stage4_merge.py).

SAFETY: sequential batches (one model, no parallel model loading — BUG-130).
Direct API via requests (same pattern as ab_test_d2359_depth.py).
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.stage4_merged_call import (  # noqa: E402
    DEPTH_FOCUSED_PROMPT,
    MERGED_CRIBS_CLASSIFY_SYSTEM,
    build_merged_prompt,
)
from pipeline.pipeline_paths import (  # noqa: E402  (C12: no hardcoded URL/key/model/tokens)
    OMLX_API_KEY,
    OMLX_URL,
    S4_DEPTH_MAX_TOKENS,
    VERIFY_MODEL,
    _CFG,
)

GOLDEN_PATH = ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
OUT_PATH = ROOT / "governance" / "s4_thinking_concurrency_benchmark.json"

URL = f"{OMLX_URL}/v1/chat/completions"
H = {"Authorization": f"Bearer {OMLX_API_KEY}", "Content-Type": "application/json"}
MODEL = VERIFY_MODEL
MERGED_MAX_TOKENS = int(_CFG.get("stage4", {}).get("merged_call_max_tokens", 2048))
DEPTH_MAX_TOKENS = S4_DEPTH_MAX_TOKENS


def load_fbs() -> list[dict]:
    import yaml
    with open(GOLDEN_PATH) as f:
        d = yaml.safe_load(f)
    fbs = []
    for ex in d["examples"]:
        if not ex.get("should_extract"):
            continue
        fb = ex.get("expected_fb", {})
        if isinstance(fb, list):
            fb = fb[0] if fb else {}
        if isinstance(fb, dict) and fb.get("depth"):
            fbs.append({
                "name": fb.get("name", ""),
                "definition": fb.get("definition", ""),
                "mechanism": fb.get("mechanism", ""),
                "boundary": fb.get("boundary", ""),
                "consequence": fb.get("consequence", ""),
                "extraction_type": fb.get("extraction_type", ""),
                "gold_depth": fb["depth"],
            })
    return fbs


def call_api(prompt: str, system: str, max_tokens: int, thinking_budget: int | None) -> tuple[float, dict]:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if thinking_budget is not None:
        payload["thinking_budget"] = thinking_budget
    t0 = time.time()
    resp = requests.post(URL, json=payload, headers=H, timeout=300)
    elapsed = time.time() - t0
    resp.raise_for_status()
    data = resp.json()
    msg = data["choices"][0]["message"]
    return elapsed, {
        "content": msg.get("content"),
        "reasoning_chars": len(msg.get("reasoning_content") or ""),
        "finish_reason": data["choices"][0].get("finish_reason"),
    }


def run_x8(fbs: list[dict]) -> list[dict]:
    """thinking_budget sweep on the merged CRIBS call (2 representative FBs)."""
    # One cross-domain + one domain FB (representative of the dominant classes).
    cross = next((f for f in fbs if f["gold_depth"] == "cross-domain"), fbs[0])
    domain = next((f for f in fbs if f["gold_depth"] == "domain"), fbs[0])
    sample = [cross, domain]
    budgets = [None, 256, 384, 512]
    rows = []
    for fb in sample:
        prompt = build_merged_prompt(fb)
        for b in budgets:
            t, r = call_api(prompt, MERGED_CRIBS_CLASSIFY_SYSTEM, MERGED_MAX_TOKENS, b)
            content = r["content"] or ""
            valid_json = False
            try:
                json.loads(content)
                valid_json = True
            except Exception:
                valid_json = False
            rows.append({
                "fb": fb["name"][:40],
                "gold_depth": fb["gold_depth"],
                "thinking_budget": b,
                "time_s": round(t, 2),
                "reasoning_chars": r["reasoning_chars"],
                "content_chars": len(content),
                "valid_json": valid_json,
                "finish_reason": r["finish_reason"],
            })
            print(f"  X8 {fb['name'][:28]:28s} budget={str(b):5s} t={t:6.1f}s "
                  f"reason={r['reasoning_chars']:4d} chars={len(content):4d} "
                  f"json={'✅' if valid_json else '❌'} ({r['finish_reason']})")
    return rows


def run_x9(fbs: list[dict]) -> list[dict]:
    """Concurrency benchmark: depth classify with 1/2/3 workers."""
    import re
    sample = fbs[:6]  # 6 FBs
    rows = []

    def classify(fb: dict) -> str:
        prompt = DEPTH_FOCUSED_PROMPT.format(
            name=fb["name"], definition=fb["definition"],
            mechanism=fb["mechanism"], extraction_type=fb["extraction_type"],
        )
        _, r = call_api(prompt, "", DEPTH_MAX_TOKENS, None)
        content = (r["content"] or "").strip().lower()
        m = re.search(r"(specialized|cross-domain|domain|universal)", content)
        return m.group(1) if m else "?" + content[:20]

    for workers in (1, 2, 3):
        t0 = time.time()
        if workers == 1:
            results = [classify(fb) for fb in sample]
        else:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                results = list(ex.map(classify, sample))
        wall = time.time() - t0
        rows.append({
            "workers": workers,
            "total_s": round(wall, 2),
            "per_fb_s": round(wall / len(sample), 2),
            "results": results,
        })
        print(f"  X9 workers={workers}: {len(sample)} depth calls in {wall:.1f}s "
              f"({wall/len(sample):.1f}s/FB) → {results}")
    return rows


def main() -> None:
    fbs = load_fbs()
    print(f"Golden FBs loaded: {len(fbs)}")
    print("=" * 66)
    print("X8 — thinking_budget sweep on merged CRIBS call")
    print("=" * 66)
    x8 = run_x8(fbs)
    print("\n" + "=" * 66)
    print("X9 — concurrency (depth classify, 6 FBs)")
    print("=" * 66)
    x9 = run_x9(fbs)

    out = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "model": MODEL, "x8": x8, "x9": x9}
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
