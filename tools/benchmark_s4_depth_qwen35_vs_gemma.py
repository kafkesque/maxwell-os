#!/usr/bin/env python3
"""
S4 Focused-Depth — Qwen3.5 (FrugalGPT candidate) vs Gemma vs GPT-OSS baseline.

Purpose (user request 2026-08-14):
  Determine whether Qwen3.5-9B-4bit (thinking disabled) is a BETTER FrugalGPT
  depth model than the current candidate gemma-4-E4B-it-MLX-4bit.

Methodology (D2243-compatible):
  - Uses the PRODUCTION prompt `DEPTH_FOCUSED_PROMPT` verbatim.
  - Uses the PRODUCTION fail-closed parser `_parse_depth_token` (raises on
    ambiguous/empty — never fabricates a depth label).
  - Transport: OMLX /v1/chat/completions (same endpoint as call_omlx).
    Qwen3.5-9B is a *thinking* model, so it receives
    `chat_template_kwargs={"enable_thinking": False}` — otherwise it emits
    chain-of-thought and fails the one-word parser. GPT-OSS and Gemma are
    called without that flag (Gemma is non-reasoning; GPT-OSS is the baseline).

Gate reference (D2354): a FrugalGPT candidate is acceptable only if it shows
  >= 90% parity with GPT-OSS AND >= 90% held-out accuracy AND zero failures.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.stage4_merged_call import DEPTH_FOCUSED_PROMPT, _parse_depth_token, DepthClassificationError  # noqa: E402
from pipeline.pipeline_paths import VERIFY_MODEL, S4_DEPTH_MODEL  # noqa: E402

GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
OUT_PATH = PROJECT_ROOT / "governance" / "s4_depth_qwen35_vs_gemma_benchmark.json"
OMLX_URL = "http://127.0.0.1:11435/v1/chat/completions"
API_KEY = "sk-maxwell-local"

QWEN35_MODEL = "Qwen3.5-9B-4bit"
GEMMA_MODEL = S4_DEPTH_MODEL  # gemma-4-E4B-it-MLX-4bit
GPTOSS_MODEL = VERIFY_MODEL  # gpt-oss-20b-MXFP4-Q8


def load_test_set() -> list[dict]:
    """Load all depth-labeled FBs from the golden set."""
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


def make_prompt(fb: dict) -> str:
    return DEPTH_FOCUSED_PROMPT.format(
        name=fb["name"],
        definition=fb["definition"],
        mechanism=fb["mechanism"],
        extraction_type=fb["extraction_type"],
    )


def call_depth(fb: dict, model: str, enable_thinking: bool | None = None) -> tuple[str, float, str | None]:
    """Classify depth through OMLX using the PRODUCTION prompt + fail-closed parser.

    Returns (pred, elapsed_s, error). `enable_thinking` only for Qwen3.5-9B.
    """
    prompt = make_prompt(fb)
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    if enable_thinking is not None:
        payload["chat_template_kwargs"] = {"enable_thinking": enable_thinking}

    t0 = time.time()
    try:
        r = requests.post(
            OMLX_URL,
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            timeout=180,
        )
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        content = msg.get("content")
        if not content or not content.strip():
            raise DepthClassificationError("empty content")
        pred = _parse_depth_token(content)
        return pred, time.time() - t0, None
    except DepthClassificationError as e:
        return "FAIL", time.time() - t0, f"DepthClassificationError: {e}"
    except Exception as e:
        return "FAIL", time.time() - t0, f"{type(e).__name__}: {str(e)[:160]}"


def run_model(fbs: list[dict], model: str, enable_thinking: bool | None = None) -> list[dict]:
    print(f"\n  ▶ {model}" + (f"  (enable_thinking={enable_thinking})" if enable_thinking is not None else ""))
    rows = []
    for i, fb in enumerate(fbs):
        pred, elapsed, err = call_depth(fb, model, enable_thinking)
        rows.append({"gold": fb["gold_depth"], "pred": pred, "t": elapsed, "err": err, "id": fb["golden_id"]})
        flag = "✅" if pred == fb["gold_depth"] else ("⚠️" if pred != "FAIL" else "❌")
        print(f"     {i+1:2d}/{len(fbs)} gold={fb['gold_depth']:12s} pred={pred:12s} {flag} {elapsed:5.1f}s" + (f"  {err}" if err else ""))
    return rows


def summarize(name: str, rows: list[dict], gold: list[dict], gptoss_rows: list[dict] | None = None) -> dict:
    n = len(rows)
    acc = sum(1 for r in rows if r["pred"] == r["gold"]) / n
    fails = sum(1 for r in rows if r["pred"] == "FAIL")
    times = [r["t"] for r in rows]
    avg = sum(times) / n
    warm = sum(times[1:]) / (n - 1) if n > 1 else avg
    parity = None
    if gptoss_rows is not None:
        parity = sum(1 for r, g in zip(rows, gptoss_rows) if r["pred"] == g["pred"]) / n
    print(f"\n  {name}: acc={acc:.1%}  failures={fails}  avg={avg:.1f}s  warm={warm:.1f}s"
          + (f"  parity_vs_gptoss={parity:.1%}" if parity is not None else ""))
    return {"name": name, "n": n, "accuracy": acc, "failures": fails,
            "avg_time_s": round(avg, 2), "warm_time_s": round(warm, 2),
            "parity_vs_gptoss": parity}


def main() -> None:
    fbs = load_test_set()
    print("=" * 70)
    print("S4 DEPTH — Qwen3.5 vs Gemma vs GPT-OSS (production prompt + fail-closed parser)")
    print(f"Golden FBs: {len(fbs)}")
    dist = Counter(fb["gold_depth"] for fb in fbs)
    print(f"  distribution: " + ", ".join(f"{k}={v}" for k, v in sorted(dist.items())))
    print("=" * 70)

    gptoss = run_model(fbs, GPTOSS_MODEL)
    gemma = run_model(fbs, GEMMA_MODEL)
    qwen35 = run_model(fbs, QWEN35_MODEL, enable_thinking=False)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    s_gpt = summarize("GPT-OSS (baseline)", gptoss, fbs)
    s_gem = summarize("Gemma 4B (current candidate)", gemma, fbs, gptoss)
    s_qw = summarize("Qwen3.5-9B (thinking-off)", qwen35, fbs, gptoss)

    # per-depth-class breakdown for the two candidates
    def breakdown(rows):
        b = {}
        for r in rows:
            b.setdefault(r["gold"], {"n": 0, "correct": 0, "fail": 0})
            b[r["gold"]]["n"] += 1
            b[r["gold"]]["correct"] += 1 if r["pred"] == r["gold"] else 0
            b[r["gold"]]["fail"] += 1 if r["pred"] == "FAIL" else 0
        return b

    print("\n  per-depth breakdown (correct/total, fails):")
    gb, qb = breakdown(gemma), breakdown(qwen35)
    for d in ["universal", "cross-domain", "domain", "specialized"]:
        g = gb.get(d, {"n": 0, "correct": 0, "fail": 0})
        q = qb.get(d, {"n": 0, "correct": 0, "fail": 0})
        print(f"    {d:13s}  gemma {g['correct']}/{g['n']} (fail {g['fail']})   "
              f"qwen3.5 {q['correct']}/{q['n']} (fail {q['fail']})")

    # divergence matrix: where do gemma vs qwen3.5 differ, and who is right?
    diffs = [i for i in range(len(fbs)) if gemma[i]["pred"] != qwen35[i]["pred"]]
    gem_better = sum(1 for i in diffs if gemma[i]["pred"] == fbs[i]["gold_depth"] and qwen35[i]["pred"] != fbs[i]["gold_depth"])
    qw_better = sum(1 for i in diffs if qwen35[i]["pred"] == fbs[i]["gold_depth"] and gemma[i]["pred"] != fbs[i]["gold_depth"])
    print(f"\n  gemma vs qwen3.5 disagreements: {len(diffs)}/{len(fbs)}")
    print(f"    gemma right, qwen3.5 wrong: {gem_better}")
    print(f"    qwen3.5 right, gemma wrong: {qw_better}")

    speedup = s_gem["avg_time_s"] / s_qw["avg_time_s"] if s_qw["avg_time_s"] else None
    print(f"\n  speed: gemma {s_gem['warm_time_s']:.1f}s/warm vs qwen3.5 {s_qw['warm_time_s']:.1f}s/warm")

    out = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "golden_n": len(fbs),
        "golden_distribution": dict(dist),
        "models": {
            "baseline": GPTOSS_MODEL,
            "gemma": GEMMA_MODEL,
            "qwen35": QWEN35_MODEL,
        },
        "qwen35_thinking": False,
        "summary": {"gptoss": s_gpt, "gemma": s_gem, "qwen35": s_qw},
        "gemma_vs_qwen35": {
            "disagreements": len(diffs),
            "gemma_right_qwen_wrong": gem_better,
            "qwen_right_gemma_wrong": qw_better,
        },
        "results": {"gptoss": gptoss, "gemma": gemma, "qwen35": qwen35},
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to {OUT_PATH}")


if __name__ == "__main__":
    main()
