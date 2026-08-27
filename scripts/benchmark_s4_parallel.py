#!/usr/bin/env python3
"""benchmark_s4_parallel.py — A/B test gpt-oss-20b (128-expert MoE) parallelism.

The last untested quality-neutral S4 lever: does the gpt-oss classifier scale with
concurrent requests (ThreadPoolExecutor), or does the MoE server serialize/thrash
(D2459 observed 6-worker DEGRADATION — server serializes + KV-store dispatch thrash)?

Tests the DOMINANT S4 cost — merged_cribs_classify (~19.5s/FB serial) — at
1 / 2 / 3 workers on an IDENTICAL sample, measuring:
  * THROUGHPUT  — FBs/sec and speedup vs serial.
  * RELIABILITY — error/timeout/empty-result rate (thrash shows up as failures).
  * CONSISTENCY — discipline label agreement vs the serial reference (temp=0.0 greedy
                  is deterministic per-request, so label drift = genuine serving problem,
                  not a model difference).

Usage:
    python3 scripts/benchmark_s4_parallel.py --n 8 --workers 1,2,3 --seed 42
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

CONVERGENT = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    try:
        return [json.loads(l) for l in raw.splitlines() if l.strip()]
    except json.JSONDecodeError:
        d = json.loads(raw)
        return d if isinstance(d, list) else [d]


def _sample(n: int, seed: int) -> list[dict]:
    import random
    rng = random.Random(seed)
    recs = [r for r in _load_jsonl(CONVERGENT)
            if r.get("content_type") == "principle" and r.get("mechanism")]
    rng.shuffle(recs)
    return recs[:n]


def _run_once(fb: dict, model: str):
    from pipeline.stage4_merged_call import merged_cribs_classify
    r = merged_cribs_classify(dict(fb), model=model)
    if isinstance(r, list):
        r = r[0] if r else {}
    if not isinstance(r, dict) or not r:
        return None
    return r


def _bench(n_workers: int, fbs: list[dict], model: str) -> dict:
    t0 = time.time()
    errors = 0
    results = [None] * len(fbs)
    if n_workers == 1:
        for i, fb in enumerate(fbs):
            try:
                results[i] = _run_once(fb, model)
                if results[i] is None:
                    errors += 1
            except Exception:
                errors += 1
    else:
        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            fut = {ex.submit(_run_once, fb, model): i for i, fb in enumerate(fbs)}
            for f in as_completed(fut):
                i = fut[f]
                try:
                    results[i] = f.result()
                    if results[i] is None:
                        errors += 1
                except Exception:
                    errors += 1
    elapsed = time.time() - t0
    return {"workers": n_workers, "elapsed": elapsed, "errors": errors, "results": results}


def _discipline(r) -> str:
    d = r.get("discipline", "")
    if isinstance(d, list):
        d = d[0] if d else ""
    return str(d).strip().lower() if d else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--workers", default="1,2,3")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from pipeline.pipeline_paths import VERIFY_MODEL
    worker_list = [int(x) for x in args.workers.split(",") if x.strip()]
    fbs = _sample(args.n, args.seed)
    if len(fbs) < 2:
        print("❌ not enough samples")
        return 2
    print(f"📊 {len(fbs)} principles, workers={worker_list}, model={VERIFY_MODEL}\n")

    runs = {}
    for w in worker_list:
        print(f"  ⚙️  benchmarking {w} worker(s)...")
        runs[w] = _bench(w, fbs, VERIFY_MODEL)

    base = runs[worker_list[0]]
    ref_disc = [_discipline(r) if r else "ERR" for r in base["results"]]

    print(f"\n{'workers':>8} {'elapsed':>9} {'FBs/s':>8} {'speedup':>8} {'errors':>7} {'disc-agree':>11}")
    for w in worker_list:
        r = runs[w]
        n = len(fbs)
        rate = n / r["elapsed"] if r["elapsed"] > 0 else 0.0
        speedup = base["elapsed"] / r["elapsed"] if r["elapsed"] > 0 else 0.0
        disc = [_discipline(x) if x else "ERR" for x in r["results"]]
        agree = sum(1 for a, b in zip(ref_disc, disc) if a == b and a != "ERR")
        valid = sum(1 for d in disc if d != "ERR")
        agree_pct = f"{100*agree/max(valid,1):.0f}%" if valid else "n/a"
        print(f"{w:>8} {r['elapsed']:>8.1f}s {rate:>8.3f} {speedup:>7.2f}x {r['errors']:>7} {agree_pct:>11}")

    print("\n✅ parallelism A/B complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
