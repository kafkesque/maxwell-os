#!/usr/bin/env python3
"""omlx_lever_ab.py — generic oMLX per-model setting A/B on THIS M1 Max (D-294).

A/B any single model_settings.json flag against decode throughput, reusing the
D-293 instrument pattern (frozen prompts, stream=True ttft/decode split, temp=0.0,
API-key auth). Covers the immediately-runnable M1 Max levers (no download needed):
  - turboquant_kv_enabled  (KV-cache quant -> cuts decode bandwidth)
  - specprefill_enabled    (speculative prefill, long-prefill-only)

Usage:
    python3 scripts/omlx_lever_ab.py --toggle turboquant_kv_enabled true  --model Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
    python3 scripts/omlx_lever_ab.py --measure --label kv_off --model Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
    python3 scripts/omlx_lever_ab.py --compare kv_off kv_on

D-332: adopt the new value ONLY if the compare is a WIN on this M1 Max. Quant
VARIANT A/B (oQ4e/oQe vs 4bit) needs a model download first and is out of scope here.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from pipeline.pipeline_paths import OMLX_API_KEY, OMLX_URL  # noqa: E402 (C12)

SETTINGS_PATH = Path.home() / ".omlx" / "model_settings.json"
AUTH = {"Authorization": f"Bearer {OMLX_API_KEY}"}
RESULTS = ROOT / "governance" / "omlx_lever_ab_results.jsonl"
PROMPTS = [
    "Extract every convergent principle from this passage and return them as JSON: '{text}'",
    "Classify the epistemic form (causal_mechanism/descriptive_model/design_principle/prescriptive_rule) and return JSON: '{text}'",
    "Decompose the mechanism, application, boundary, and source of this principle as JSON: '{text}'",
    "Return a JSON list of named principles with definition and mechanism from: '{text}'",
]


def _load() -> dict:
    with open(SETTINGS_PATH, encoding='utf-8') as f:
        return json.load(f)


def _save(data: dict) -> None:
    bak = SETTINGS_PATH.with_suffix(f".json.bak-leverab-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(SETTINGS_PATH, bak)
    with open(SETTINGS_PATH, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"  backup: {bak.name}")


def toggle(key: str, value: str, model: str) -> None:
    """Set one flag on one model (crash-safe backup), then admin reload (D-2637)."""
    val = value.lower() not in ("false", "off", "0", "no")
    data = _load()
    cfg = data["models"].get(model)
    if cfg is None:
        raise SystemExit(f"model {model!r} not in model_settings.json")
    old = cfg.get(key)
    cfg[key] = val
    _save(data)
    print(f"[toggle] {model}.{key}: {old!r} -> {val!r}")
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "scripts" / "omlx_reload.py")],
                   capture_output=True, text=True, timeout=240)


def _measure_one(model: str, prompt: str, timeout: int) -> dict:
    """Stream one generation; split ttft (prefill) from decode tok/s."""
    payload = {"model": model, "temperature": 0.0, "stream": True, "max_tokens": 512,
               "messages": [{"role": "user", "content": prompt.format(text="a" * 200)}]}
    t0 = time.time()
    n, first = 0, None
    with requests.post(f"{OMLX_URL}/v1/chat/completions", json=payload,
                       stream=True, timeout=timeout, headers=AUTH) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                delta = json.loads(chunk)["choices"][0]["delta"].get("content", "")
            except (KeyError, json.JSONDecodeError):
                continue
            if delta:
                if first is None:
                    first = time.time()
                n += len(delta)
    end = time.time()
    ttft = (first - t0) if first else (end - t0)
    decode = max((end - first), 1e-6) if first else 1e-6
    return {"tok_s": round(n / decode, 2), "ttft": round(ttft, 3), "n_tok": n}


def measure(model: str, label: str, n_prompts: int, max_tokens: int, timeout: int) -> None:
    """Run the frozen batch and append labelled rows (crash-safe)."""
    rates = []
    for i in range(n_prompts):
        r = _measure_one(model, PROMPTS[i % len(PROMPTS)], timeout)
        rates.append(r["tok_s"])
        print(f"[{label}] {r['tok_s']} tok/s (ttft {r['ttft']}s, {r['n_tok']} tok)")
    mean = sum(rates) / len(rates)
    med = sorted(rates)[len(rates) // 2]
    print(f"[{label}] mean decode {mean:.2f} tok/s (median {med:.2f}, n={len(rates)})")
    row = {"label": label, "model": model, "mean": round(mean, 2),
           "median": round(med, 2), "n": len(rates), "ts": datetime.now().isoformat()}
    with open(RESULTS, "a", encoding='utf-8') as f:
        f.write(json.dumps(row) + "\n")


def compare(a: str, b: str) -> None:
    """Ratio + WIN/LOSS/NEUTRAL verdict (D-332)."""
    rows = [json.loads(l) for l in open(RESULTS, encoding='utf-8') if l.strip()]
    d = {r["label"]: r for r in rows}
    if a not in d or b not in d:
        raise SystemExit(f"need both labels {a!r},{b!r} in {RESULTS}")
    ra, rb = d[a], d[b]
    ratio = rb["mean"] / ra["mean"]
    verdict = "WIN" if ratio > 1.02 else ("LOSS" if ratio < 0.98 else "NEUTRAL")
    print(f"[{a}] mean {ra['mean']} tok/s (n={ra['n']})")
    print(f"[{b}] mean {rb['mean']} tok/s (n={rb['n']})")
    print(f"[compare] {b}/{a} = {ratio:.2f}x -> {verdict} (D-332: adopt only if WIN on THIS M1 Max)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--toggle", nargs=2, metavar=("KEY", "VALUE"))
    ap.add_argument("--model", default="Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--label")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    ap.add_argument("--n-prompts", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    if args.toggle:
        toggle(args.toggle[0], args.toggle[1], args.model)
    elif args.measure:
        measure(args.model, args.label or "unlabelled", args.n_prompts, args.max_tokens, args.timeout)
    elif args.compare:
        compare(args.compare[0], args.compare[1])
    else:
        ap.print_help()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
