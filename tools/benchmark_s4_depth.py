#!/usr/bin/env python3
"""
S4 Depth Classification Benchmark: Phi-4-mini-8bit vs Gemma-4-31B-8bit
SAFE VERSION — both models served via OMLX API (port 11435).

⚠️ SAFETY (panic prevention, D2243):
- NEVER load Gemma-4-31B via mlx_lm while OMLX is serving — this caused
  kernel panic "completeMemory() prepare count underflow" @IOGPUMemory.cpp:492
  (concurrent Metal GPU memory allocation under ~50GB/64GB pressure).
- OMLX enforces --memory-guard-gb 55 and handles model eviction.
- Gemma-4-31B-it is a reasoning model: needs max_tokens=1024 (~90s/call),
  emits reasoning_content then content. Parse content first.

Depth ontology: specialized < domain < cross-domain < universal
"""

import json
import time
import sys
import random
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from pipeline.io_guard import safe_write  # D2487: atomic + fsync + fail-loud

GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
DEPTH_ORDER = ["specialized", "domain", "cross-domain", "universal"]
OMLX_URL = "http://localhost:11435/v1/chat/completions"
PHI_MODEL = "Phi-4-mini-instruct-8bit"
GEMMA_MODEL = "gemma-4-31B-it-MLX-8bit"

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
    """Load FBs with depth labels from golden set."""
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


def classify_via_omlx(prompt: str, model: str, max_tokens: int) -> tuple[str, float]:
    """Classify via OMLX API. Returns (prediction, elapsed)."""
    import requests
    payload = {
        "model": model,
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
        # Prefer content, fall back to last word in reasoning
        if not content and reasoning:
            content = reasoning.split()[-1] if reasoning.split() else ""
        return content, elapsed
    except Exception as e:
        return f"ERROR: {e}", time.time() - t0


def main():
    print("=" * 62)
    print("S4 DEPTH CLASSIFICATION BENCHMARK (SAFE — OMLX for both models)")
    print("Phi-4-mini-8bit  vs  Gemma-4-31B-it-MLX-8bit")
    print("=" * 62)

    test_fbs = load_test_set()
    print(f"\n📊 Golden set: {len(test_fbs)} FBs")
    depth_dist = Counter(fb["gold_depth"] for fb in test_fbs)
    for d in DEPTH_ORDER:
        print(f"   {d}: {depth_dist.get(d, 0)}")

    # Stratified sample: min(6, available) per class, up to 12 total
    random.seed(42)
    stratified = {d: [] for d in DEPTH_ORDER}
    for fb in test_fbs:
        stratified[fb["gold_depth"]].append(fb)
    sampled = []
    for d in DEPTH_ORDER:
        n = min(len(stratified[d]), 3)
        sampled.extend(random.sample(stratified[d], n))
    random.shuffle(sampled)
    print(f"📊 Benchmark sample: {len(sampled)} FBs (stratified)")

    results = {"phi": [], "gemma": []}

    # ── PHI-4-MINI ──
    print("\n" + "─" * 40)
    print(f"🤖 {PHI_MODEL} (~1.3s/call)")
    for i, fb in enumerate(sampled):
        prompt = DEPTH_PROMPT.format(**fb)
        pred, elapsed = classify_via_omlx(prompt, PHI_MODEL, max_tokens=8)
        parsed = next((d for d in DEPTH_ORDER if d in pred), pred)
        correct = parsed == fb["gold_depth"]
        results["phi"].append({"fb": fb["golden_id"], "gold": fb["gold_depth"], "pred": parsed, "correct": correct, "t": elapsed})
        print(f"  {i+1:2d}/{len(sampled)} {'✅' if correct else '❌'} gold={fb['gold_depth']:15s} pred={parsed:15s} ({elapsed:.1f}s)")

    # ── GEMMA-4-31B ──
    print("\n" + "─" * 40)
    print(f"🤖 {GEMMA_MODEL} (~90s/call, reasoning model)")
    print("  ⚠️ First call loads 31GB model — allow ~60s extra")
    for i, fb in enumerate(sampled):
        prompt = DEPTH_PROMPT.format(**fb)
        pred, elapsed = classify_via_omlx(prompt, GEMMA_MODEL, max_tokens=1024)
        parsed = next((d for d in DEPTH_ORDER if d in pred), pred)
        correct = parsed == fb["gold_depth"]
        results["gemma"].append({"fb": fb["golden_id"], "gold": fb["gold_depth"], "pred": parsed, "correct": correct, "t": elapsed})
        print(f"  {i+1:2d}/{len(sampled)} {'✅' if correct else '❌'} gold={fb['gold_depth']:15s} pred={parsed:15s} ({elapsed:.0f}s)")

    # ── COMPARISON ──
    print("\n" + "=" * 62)
    print("📊 COMPARISON")
    print("=" * 62)
    for model in ["phi", "gemma"]:
        n = len(results[model])
        acc = sum(1 for r in results[model] if r["correct"]) / n if n else 0
        avg_t = sum(r["t"] for r in results[model]) / n if n else 0
        total_t = sum(r["t"] for r in results[model])
        print(f"  {model.upper():<15} n={n:2d}  acc={acc:.1%}  avg={avg_t:7.1f}s  total={total_t:7.1f}s")

    # Per-depth
    print("\n  Per-depth accuracy:")
    for d in DEPTH_ORDER:
        row = []
        for model in ["phi", "gemma"]:
            sub = [r for r in results[model] if r["gold"] == d]
            acc = sum(1 for r in sub if r["correct"]) / len(sub) if sub else float("nan")
            row.append(f"{acc:>6.1%}")
        print(f"  {d:<15s} Phi={row[0]}  Gemma={row[1]}")

    phi_acc = sum(1 for r in results["phi"] if r["correct"]) / len(results["phi"])
    gemma_acc = sum(1 for r in results["gemma"] if r["correct"]) / len(results["gemma"])
    print(f"\n  🏆 Winner: {'Gemma-4-31B' if gemma_acc > phi_acc else 'Phi-4-mini'}")

    # Save
    out = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n": len(sampled),
        "phi4_mini": {"accuracy": phi_acc, "results": results["phi"]},
        "gemma_4_31b": {"accuracy": gemma_acc, "results": results["gemma"]},
        "winner": "gemma" if gemma_acc > phi_acc else "phi",
        "safety": "OMLX-served both models; no mlx_lm direct load (D2243 panic prevention)",
    }
    out_path = PROJECT_ROOT / "governance" / "s4_depth_benchmark.json"
    safe_write(out_path, json.dumps(out, indent=2, ensure_ascii=False), force_shrink=True)  # D2487: fsync + atomic
    print(f"\n📁 Saved: {out_path}")


if __name__ == "__main__":
    main()
