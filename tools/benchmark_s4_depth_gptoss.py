#!/usr/bin/env python3
"""
S4 Depth Classification Benchmark — GPT-OSS-20B-MXFP4-Q8 (D2245).

Third entrant after Phi-4-mini (37.5%) and Gemma-4-31B (50%, too slow 143.8s/call).
Same seed-42 stratified sample as benchmark_s4_depth.py for apples-to-apples.

SAFETY (D2243): served via OMLX API only — single Metal client, memory guard 55GB.
GPT-OSS-20B is a reasoning model: emits reasoning_content then content; parse content.
"""
from __future__ import annotations

import json
import random
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
OUT_PATH = PROJECT_ROOT / "governance" / "s4_depth_benchmark_gptoss.json"

OMLX_URL = "http://localhost:11435/v1/chat/completions"
MODEL = "gpt-oss-20b-MXFP4-Q8"

DEPTH_ORDER = ["specialized", "domain", "cross-domain", "universal"]

DEPTH_PROMPT = """Classify the DEPTH of this Foundation Block (a convergent principle from multiple books).

ONTOLOGY:
- specialized: Requires technical expertise in one narrow field. (e.g., optical kerning in typography)
- domain: Applies broadly within one discipline only. (e.g., price anchoring in behavioral economics)
- cross-domain: Same principle applies across multiple disciplines. (e.g., feedback loops in biology AND orgs)
- universal: A law of nature or mathematics — applies everywhere. (e.g., entropy, power laws)

FB:
Name: {name}
Definition: {definition}
Mechanism: {mechanism}
Type: {extraction_type}

Answer EXACTLY ONE WORD: specialized, domain, cross-domain, or universal. No reasoning."""


def load_test_set() -> list[dict]:
    """Load FBs with depth labels from golden set (same as original benchmark)."""
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
                "golden_id": ex.get("id", "?"),
            })
    return fbs


def classify_via_omlx(prompt: str, max_tokens: int = 512) -> tuple[str, float]:
    """Classify via OMLX API. Returns (prediction, elapsed)."""
    import requests
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    t0 = time.time()
    try:
        resp = requests.post(OMLX_URL, json=payload, timeout=300)
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        elapsed = time.time() - t0
        content = msg.get("content", "").strip().lower()
        reasoning = msg.get("reasoning_content", "").strip().lower()
        if not content and reasoning:
            content = reasoning.split()[-1] if reasoning.split() else ""
        return content, elapsed
    except Exception as e:
        return f"ERROR: {e}", time.time() - t0


def main() -> None:
    print("=" * 62)
    print("S4 DEPTH CLASSIFICATION BENCHMARK — GPT-OSS-20B-MXFP4-Q8 (D2245)")
    print(f"Model: {MODEL} (12.1GB MXFP4-Q8, OpenAI reasoning MoE 3.6B active)")
    print("=" * 62)

    test_fbs = load_test_set()
    print(f"\n📊 Golden set: {len(test_fbs)} FBs")
    depth_dist = Counter(fb["gold_depth"] for fb in test_fbs)
    for d in DEPTH_ORDER:
        print(f"   {d}: {depth_dist.get(d, 0)}")

    # Stratified sample — SAME seed 42 as original benchmark (reproducibility)
    random.seed(42)
    stratified = {d: [] for d in DEPTH_ORDER}
    for fb in test_fbs:
        stratified[fb["gold_depth"]].append(fb)
    sampled = []
    for d in DEPTH_ORDER:
        n = min(len(stratified[d]), 3)
        sampled.extend(random.sample(stratified[d], n))
    random.shuffle(sampled)
    print(f"📊 Benchmark sample: {len(sampled)} FBs (stratified, seed=42)")

    results: list[dict] = []

    print("\n" + "─" * 40)
    print(f"🤖 {MODEL} (reasoning model, ~6s/call after load)")
    print("  ⚠️ First call loads 12GB model — allow ~30s extra")
    for i, fb in enumerate(sampled):
        prompt = DEPTH_PROMPT.format(**fb)
        pred, elapsed = classify_via_omlx(prompt)
        parsed = next((d for d in DEPTH_ORDER if d in pred), pred)
        correct = parsed == fb["gold_depth"]
        results.append({"fb": fb["golden_id"], "gold": fb["gold_depth"], "pred": parsed, "correct": correct, "t": elapsed})
        print(f"  {i+1:2d}/{len(sampled)} {'✅' if correct else '❌'} gold={fb['gold_depth']:15s} pred={parsed:15s} ({elapsed:.1f}s)")

    # ── COMPARISON vs recorded baselines ──
    print("\n" + "=" * 62)
    print("📊 COMPARISON (vs D2244 recorded baselines)")
    print("=" * 62)
    n = len(results)
    acc = sum(1 for r in results if r["correct"]) / n if n else 0
    avg_t = sum(r["t"] for r in results) / n if n else 0
    total_t = sum(r["t"] for r in results)
    print(f"  GPT-OSS-20B     n={n:2d}  acc={acc:.1%}  avg={avg_t:7.1f}s  total={total_t:7.1f}s")
    print(f"  (recorded) Phi  n=8  acc=37.5%  avg=0.5s   (D2244)")
    print(f"  (recorded) Gemma n=8  acc=50.0%  avg=143.8s (D2244)")

    print("\n  Per-depth accuracy (gpt-oss only):")
    for d in DEPTH_ORDER:
        sub = [r for r in results if r["gold"] == d]
        acc_d = sum(1 for r in sub if r["correct"]) / len(sub) if sub else float("nan")
        print(f"  {d:<15s} GPT-OSS={acc_d:>6.1%}   (Phi 0/2  Gemma 1/2 on cross-domain)")

    print(f"\n  🏆 Speed vs Gemma: {143.8 / avg_t:.1f}× faster per call")
    print(f"  🏆 Accuracy: {'BEATS Gemma (50%)' if acc > 0.5 else 'below Gemma (50%)'} | {'BEATS Phi (37.5%)' if acc > 0.375 else 'below Phi (37.5%)'}")

    out = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n": len(sampled),
        "model": MODEL,
        "accuracy": acc,
        "avg_time_s": avg_t,
        "total_time_s": total_t,
        "results": results,
        "comparison": {
            "phi4_mini": {"accuracy": 0.375, "avg_time_s": 0.5, "source": "D2244"},
            "gemma_4_31b": {"accuracy": 0.50, "avg_time_s": 143.8, "source": "D2244"},
        },
        "speedup_vs_gemma_x": round(143.8 / avg_t, 1) if avg_t else None,
        "safety": "OMLX API only — single Metal client (D2243)",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
