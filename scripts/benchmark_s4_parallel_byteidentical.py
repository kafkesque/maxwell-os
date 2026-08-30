#!/usr/bin/env python3
"""benchmark_s4_parallel_byteidentical.py — 6-FB A/B: serial vs parallel merged S4 call.

D2492: prove (or disprove) that running the dominant S4 cost — the gpt-oss-20b
`merged_cribs_classify` call (~19.5s/FB serial) — as PARALLEL separate prompts
(ThreadPoolExecutor, continuous batching) is quality-neutral: byte-identical
temp=0.0 output AND faster.

This is the quality-neutral lever, UNLIKE rejected batch-CRIBS (D2265) which
degrades domain granularity (12% exact / Jaccard 0.48). Batch CRIBS packs N FBs
into ONE prompt (coarse, lossy); THIS runs N independent merged calls concurrently
(each prompt identical to serial, only the transport scheduling changes).

Measures:
  * THROUGHPUT  — FBs/sec + speedup vs serial.
  * BYTE-IDENTITY — full JSON field equality (sorted keys) of every returned dict
                    vs the serial reference. temp=0.0 greedy + continuous batching
                    ⇒ any drift = serving nondeterminism (real finding), not model noise.
  * RELIABILITY — error/empty rate (server thrash shows up as failures).

Usage:
    python3 scripts/benchmark_s4_parallel_byteidentical.py --n 6 --workers 4 --seed 42
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


def _canonical(r: dict) -> str:
    """Canonical JSON of a result dict (sorted keys) for byte-identity comparison."""
    return json.dumps(r, sort_keys=True, default=str)


def _run_once(fb: dict, model: str) -> dict:
    from pipeline.stage4_merged_call import merged_cribs_classify
    r = merged_cribs_classify(dict(fb), model=model)
    if isinstance(r, list):
        r = r[0] if r else {}
    if not isinstance(r, dict) or not r:
        return {}
    return r


def _run(n_workers: int, fbs: list[dict], model: str) -> tuple[dict, list[dict]]:
    t0 = time.time()
    errors = 0
    results: list[dict] = [{}] * len(fbs)
    if n_workers == 1:
        for i, fb in enumerate(fbs):
            try:
                results[i] = _run_once(fb, model)
                if not results[i]:
                    errors += 1
            except Exception as e:
                print(f"   ⚠️  serial FB[{i}] error: {type(e).__name__}: {e}", file=sys.stderr)
                errors += 1
    else:
        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            fut = {ex.submit(_run_once, fb, model): i for i, fb in enumerate(fbs)}
            for f in as_completed(fut):
                i = fut[f]
                try:
                    results[i] = f.result()
                    if not results[i]:
                        errors += 1
                except Exception as e:
                    print(f"   ⚠️  parallel FB[{i}] error: {type(e).__name__}: {e}", file=sys.stderr)
                    errors += 1
    elapsed = time.time() - t0
    return {"workers": n_workers, "elapsed": elapsed, "errors": errors}, results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from pipeline.pipeline_paths import VERIFY_MODEL
    fbs = _sample(args.n, args.seed)
    if len(fbs) < 2:
        print("❌ not enough samples")
        return 2
    print(f"📊 {len(fbs)} principles | model={VERIFY_MODEL} | workers=1 vs {args.workers}\n")

    print("  ⚙️  serial reference (1 worker)...")
    ref_meta, ref_results = _run(1, fbs, VERIFY_MODEL)
    print(f"  ⚙️  parallel ({args.workers} workers)...")
    par_meta, par_results = _run(args.workers, fbs, VERIFY_MODEL)

    n = len(fbs)
    ref_rate = n / ref_meta["elapsed"] if ref_meta["elapsed"] > 0 else 0.0
    par_rate = n / par_meta["elapsed"] if par_meta["elapsed"] > 0 else 0.0
    speedup = ref_meta["elapsed"] / par_meta["elapsed"] if par_meta["elapsed"] > 0 else 0.0

    # Byte-identity: compare canonical JSON of every FB (order-aligned).
    identical = 0
    diff_fields: list[tuple[int, str, str, str]] = []
    for i, (r_ref, r_par) in enumerate(zip(ref_results, par_results)):
        if r_ref and r_par and _canonical(r_ref) == _canonical(r_par):
            identical += 1
        elif r_ref and r_par:
            keys = sorted(set(r_ref) | set(r_par))
            for k in keys:
                a, b = r_ref.get(k), r_par.get(k)
                if a != b:
                    diff_fields.append((i, k, str(a)[:80], str(b)[:80]))
        else:
            diff_fields.append((i, "<whole-result>", "non-empty" if r_ref else "EMPTY",
                                "non-empty" if r_par else "EMPTY"))

    print(f"\n{'run':>10} {'elapsed':>9} {'FBs/s':>8} {'speedup':>8} {'errors':>7}")
    print(f"{'serial-1':>10} {ref_meta['elapsed']:>8.1f}s {ref_rate:>8.3f} {'1.00x':>8} {ref_meta['errors']:>7}")
    print(f"{'parallel':>10} {par_meta['elapsed']:>8.1f}s {par_rate:>8.3f} {speedup:>7.2f}x {par_meta['errors']:>7}")

    print(f"\n🧬 BYTE-IDENTITY: {identical}/{n} results identical")
    if diff_fields:
        print(f"   ⚠️  {len(diff_fields)} diverging field(s):")
        for i, k, a, b in diff_fields[:20]:
            print(f"      FB[{i}].{k}: serial={a!r} vs parallel={b!r}")
    verdict = "✅ PARALLEL IS QUALITY-NEUTRAL" if identical == n and par_meta["errors"] == 0 else "🛑 PARALLEL IS NOT BYTE-IDENTICAL"
    print(f"\n{verdict} | speedup={speedup:.2f}x | identical={identical}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
