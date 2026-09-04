#!/usr/bin/env python3
"""
S2 Convergent Extraction — Qwen3.8-27B vs Qwen3-Coder-30B-A3B benchmark.

Purpose (user request 2026-08-14):
    Determine whether Qwen3.8-27B-MLX-4bit can be FASTER than the current
    S2 generator Qwen3-Coder-30B-A3B-Instruct-MLX-4bit, and at what accuracy
    cost. Uses the PRODUCTION convergent-extraction prompt + SYSTEM_PROMPT
    and real canary clusters/segments — not synthetic data.

    "find the fastest most accurate way" → for each model we measure:
      1. wall-clock seconds per extraction (and tokens/sec)
      2. output validity (JSON parses, schema-valid, route FB/NULL)
      3. route agreement with the baseline (Qwen3-Coder is ground-truth
         proxy; it produced the 277 accepted canary FBs)

Safety:
    Sequential (NOT parallel) per post-crash guidance. One model at a time.
    Config: N_CLUSTERS, MODELS via argv/env.

Usage:
    python3 tools/benchmark_s2_qwen38_vs_coder.py --n 10
    python3 tools/benchmark_s2_qwen38_vs_coder.py --n 10 --models Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
    python3 tools/benchmark_s2_qwen38_vs_coder.py --n 10 --models Qwen3.8-27B-MLX-4bit
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.pipeline_paths import OMLX_API_KEY  # noqa: E402  (C12: single source, D2552)

# Reuse the PRODUCTION prompt + validation, not reimplementations.
from pipeline.stage2_extract import (  # noqa: E402
    SYSTEM_PROMPT,
    build_convergent_prompt,
    validate_fb_output,
)

DEFAULT_MODELS = [
    "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit",
    "Qwen3.8-27B-MLX-4bit",
]


def load_probe_targets() -> list[dict]:
    """Load convergent probe targets (cluster_id -> segment_ids)."""
    p = ROOT / "knowledge pipeline" / "stage2_extract" / "canary" / "probe_targets.jsonl"
    with open(p) as f:
        data = json.load(f)
    return data.get("targets", [])


def load_segments() -> dict[str, dict]:
    """Load segments indexed by segment_id (Stage 1 checkpoint)."""
    p = ROOT / "knowledge pipeline" / "stage1_chunk" / "canary" / "checkpoint.jsonl"
    segs: dict[str, dict] = {}
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("segment_id"):
                segs[d["segment_id"]] = d
    return segs


def load_clusters() -> dict[str, dict]:
    """Load convergent clusters from Stage 1.5 checkpoint, keyed by cluster_id."""
    p = ROOT / "knowledge pipeline" / "stage1_5_embed_cluster" / "canary" / "checkpoint.jsonl"
    clusters: dict[str, dict] = {}
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("is_convergent"):
                clusters[d["cluster_id"]] = d
    return clusters


def call_omlx_raw(prompt: str, system: str, model: str, max_tokens: int = 2048) -> tuple[dict, float]:
    """Call OMLX chat completions, return (parsed_json, wall_seconds)."""
    import requests

    url = "http://127.0.0.1:11435/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OMLX_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    t0 = time.perf_counter()
    resp = requests.post(url, json=payload, headers=headers, timeout=400)
    dt = time.perf_counter() - t0
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"].get("content")
    usage = data.get("usage", {})
    if content is None:
        raise ValueError("empty content (reasoning-model cold reload?)")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Fall back to robust parse if available
        try:
            from pipeline.json_fixer import parse_json_robust
            parsed = parse_json_robust(content)
        except Exception:
            parsed = {"_raw": content[:200]}
    return {"json": parsed, "usage": usage, "content": content}, dt


def normalize_route(result: dict | list) -> str:
    """Return the route of an extraction result (FB / NULL / ARRAY / ERROR)."""
    if isinstance(result, list):
        routes = []
        for r in result:
            routes.append(str(r.get("route", "FB")).strip().upper() if isinstance(r, dict) else "?")
        # if any FB, treat as FB (multi-principle)
        return "FB" if "FB" in routes else ("NULL" if routes else "ERROR")
    if not isinstance(result, dict):
        return "ERROR"
    return str(result.get("route", "FB")).strip().upper()


def summarize(name: str, rows: list[dict], baseline_rows: list[dict] | None = None) -> dict:
    """Summarize a model's benchmark rows."""
    if not rows:
        return {"name": name, "n": 0}
    times = [r["secs"] for r in rows]
    n_fb = sum(1 for r in rows if r["route"] == "FB")
    n_null = sum(1 for r in rows if r["route"] == "NULL")
    n_invalid = sum(1 for r in rows if r["route"] == "ERROR" or not r["valid"])
    n_schema_fail = sum(1 for r in rows if r["route"] == "FB" and not r["valid"])

    agreement = None
    if baseline_rows:
        agree = sum(
            1 for a, b in zip(rows, baseline_rows) if a["route"] == b["route"]
        )
        agreement = agree / len(rows) if rows else None

    return {
        "name": name,
        "n": len(rows),
        "avg_secs": sum(times) / len(times),
        "median_secs": sorted(times)[len(times) // 2],
        "min_secs": min(times),
        "max_secs": max(times),
        "total_secs": sum(times),
        "n_fb": n_fb,
        "n_null": n_null,
        "n_invalid": n_invalid,
        "n_schema_fail": n_schema_fail,
        "fb_rate": n_fb / len(rows) if rows else 0,
        "route_agreement": agreement,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="number of clusters to benchmark")
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--out", default=str(ROOT / "governance" / "s2_qwen38_vs_coder_benchmark.json"))
    args = ap.parse_args()

    targets = load_probe_targets()
    segments = load_segments()
    clusters = load_clusters()

    # Select N targets that map to convergent clusters
    selected: list[dict] = []
    for t in targets:
        cid = t.get("cluster_id", "")
        if cid in clusters:
            selected.append(t)
        if len(selected) >= args.n:
            break

    print(f"Benchmarking {len(selected)} convergent clusters across {len(args.models)} models (SEQUENTIAL)")
    print(f"Models: {args.models}\n")

    # Pre-build prompts (identical for both models)
    prompts: list[tuple[dict, str]] = []
    for t in selected:
        cid = t["cluster_id"]
        cluster = clusters[cid]
        prompt, _ = build_convergent_prompt(cluster, segments)
        prompts.append((cluster, prompt))

    all_results: dict[str, list[dict]] = {}
    per_model_rows: dict[str, list[dict]] = {}

    for model in args.models:
        print(f"\n{'='*70}\nMODEL: {model}\n{'='*70}")
        rows: list[dict] = []
        for i, (cluster, prompt) in enumerate(prompts, 1):
            cid = cluster["cluster_id"]
            nsegs = len(cluster.get("segment_ids", []))
            t0 = time.perf_counter()
            try:
                out, call_secs = call_omlx_raw(prompt, SYSTEM_PROMPT, model)
                parsed = out["json"]
                route = normalize_route(parsed)
                valid = False
                if route == "FB" and isinstance(parsed, dict):
                    valid, _ = validate_fb_output(parsed)
                elif route == "FB" and isinstance(parsed, list):
                    valid = all(validate_fb_output(r)[0] for r in parsed if isinstance(r, dict))
                elif route == "NULL":
                    valid = True
                row = {
                    "cluster_id": cid,
                    "n_segments": nsegs,
                    "route": route,
                    "valid": valid,
                    "secs": round(call_secs, 2),
                    "usage": out.get("usage", {}),
                    "name": parsed.get("name", "") if isinstance(parsed, dict) else "",
                }
                rows.append(row)
                print(f"  [{i:2d}/{len(prompts)}] {cid} nsegs={nsegs} route={route} valid={valid} "
                      f"{call_secs:6.1f}s  {row['name'][:40]}")
            except Exception as e:
                rows.append({"cluster_id": cid, "n_segments": nsegs, "route": "ERROR",
                             "valid": False, "secs": round(time.perf_counter() - t0, 2),
                             "error": str(e)[:150]})
                print(f"  [{i:2d}/{len(prompts)}] {cid} ERROR {e}")
        per_model_rows[model] = rows
        all_results[model] = rows

    # Summaries
    baseline = per_model_rows.get(args.models[0])
    print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
    summaries = {}
    for model in args.models:
        s = summarize(model, per_model_rows[model], baseline)
        summaries[model] = s
        print(f"\n  {s['name']}: n={s['n']} avg={s['avg_secs']:.1f}s median={s['median_secs']:.1f}s "
              f"FB={s['n_fb']} NULL={s['n_null']} invalid={s['n_invalid']} schema_fail={s['n_schema_fail']} "
              f"agreement={s['route_agreement']}")

    # Speedup
    if len(args.models) >= 2:
        b = summaries[args.models[0]]
        c = summaries[args.models[1]]
        if b["avg_secs"] and c["avg_secs"]:
            print(f"\n  Speedup ({c['name']} vs {b['name']}): {b['avg_secs']/c['avg_secs']:.2f}x")

    # Write output
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_clusters": len(selected),
        "models": args.models,
        "summaries": summaries,
        "per_model_rows": per_model_rows,
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
