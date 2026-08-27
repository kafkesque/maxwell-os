#!/usr/bin/env python3
"""benchmark_s4_ab.py — A/B test the S4 bottleneck enhancements head-to-head.

Measures SPEED + QUALITY/ACCURACY (agreement vs the serial gpt-oss reference)
for each enhancement, so a full-run decision is data-driven, not vibes.

Enhancements tested (all gpt-oss-20b, VERIFY_MODEL):
  * Depth   : serial classify_depth_focused()  vs  batch batch_classify_depth() (D2354/D2477)
  * CRIBS+classify: serial merged_cribs_classify() vs batch batch_cribs_classify() (D2265)

Methodology (no external gold exists for S4 labels):
  * SPEED     — wall-clock per FB, serial vs batch, on an IDENTICAL sample.
  * RELIABILITY — malformed/exception rate (batch CRIBS historically hit 45% malformed).
  * ACCURACY  — label AGREEMENT % of batch vs the serial reference (temp=0.0 greedy
                is deterministic, so the serial gpt-oss output IS the reference).
    For depth: exact-label agreement. For CRIBS: discipline exact, domains set-equality,
    evidence exact — plus a Jaccard on domains for near-misses.

Usage:
    python3 scripts/benchmark_s4_ab.py --n 12 --seed 42
    python3 scripts/benchmark_s4_ab.py --n 12 --skip-cribs   # depth only (fast)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

CONVERGENT = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.deduped.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    try:
        return [json.loads(l) for l in raw.splitlines() if l.strip()]
    except json.JSONDecodeError:
        d = json.loads(raw)
        return d if isinstance(d, list) else [d]


def _sample_principles(n: int, seed: int) -> list[dict]:
    import random
    rng = random.Random(seed)
    recs = [r for r in _load_jsonl(CONVERGENT)
            if r.get("content_type") == "principle"
            and r.get("name") and r.get("definition") and r.get("mechanism")]
    rng.shuffle(recs)
    return recs[:n]


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = a | b
    return len(a & b) / len(u) if u else 0.0


def _bench_depth(fbs: list[dict]) -> None:
    from pipeline.stage4_merged_call import batch_depth_classify, classify_depth_focused
    from pipeline.pipeline_paths import VERIFY_MODEL

    print("\n════════ DEPTH A/B (serial vs batch) ════════")
    # serial
    t0 = time.time()
    serial_labels = []
    serial_errs = 0
    for fb in fbs:
        try:
            serial_labels.append(classify_depth_focused(fb, model=VERIFY_MODEL))
        except Exception as e:
            serial_labels.append(f"ERR:{type(e).__name__}")
            serial_errs += 1
    serial_t = time.time() - t0

    # batch
    t0 = time.time()
    batch_labels = []
    batch_errs = 0
    try:
        batch_labels = batch_depth_classify(fbs, model=VERIFY_MODEL, batch_size=4)
    except Exception as e:
        batch_labels = [f"ERR:{type(e).__name__}"] * len(fbs)
        batch_errs = len(fbs)
    batch_t = time.time() - t0

    n = len(fbs)
    agree = sum(1 for a, b in zip(serial_labels, batch_labels) if a == b)
    print(f"  serial: {serial_t:.1f}s total = {serial_t/n:.2f}s/FB  (errors={serial_errs})")
    print(f"  batch : {batch_t:.1f}s total = {batch_t/n:.2f}s/FB  (errors={batch_errs})")
    print(f"  speedup: {serial_t/batch_t:.2f}x")
    print(f"  depth label AGREEMENT: {agree}/{n} = {100*agree/n:.0f}%")
    print("  per-FB serial vs batch labels:")
    for i, (fb, a, b) in enumerate(zip(fbs, serial_labels, batch_labels)):
        mark = "✓" if a == b else "✗"
        print(f"    {mark} {fb.get('name','')[:38]:40s} serial={a:12s} batch={b}")


def _canonicalize(raw_label: str, kind: str, synonym_index, canonicals) -> str:
    """Map a raw label to canonical via the SAME path stage4_merge uses (D2138)."""
    from pipeline.stage4_merge import map_to_canonical_with_fallback
    return map_to_canonical_with_fallback(raw_label, kind, synonym_index, canonicals)


def _bench_cribs(fbs: list[dict]) -> None:
    from pipeline.stage4_merged_call import batch_cribs_classify, merged_cribs_classify
    from pipeline.pipeline_paths import VERIFY_MODEL
    from pipeline.schemas import CANONICAL_DISCIPLINES, CANONICAL_DOMAINS, get_synonym_index

    synonym_index = get_synonym_index()

    print("\n════════ CRIBS+CLASSIFY A/B (merged vs batch) ════════")
    # serial merged
    t0 = time.time()
    serial_results = []
    serial_errs = 0
    for fb in fbs:
        try:
            r = merged_cribs_classify(dict(fb), model=VERIFY_MODEL)
            if isinstance(r, list):
                r = r[0] if r else {}
            serial_results.append(r if isinstance(r, dict) else {})
        except Exception as e:
            serial_results.append({})
            serial_errs += 1
    serial_t = time.time() - t0

    # batch
    t0 = time.time()
    batch_results = []
    batch_errs = 0
    try:
        batch_results = batch_cribs_classify([dict(fb) for fb in fbs], model=VERIFY_MODEL)
        if isinstance(batch_results, dict):
            batch_results = [batch_results]
        if not isinstance(batch_results, list):
            batch_results = []
    except Exception as e:
        batch_results = []
        batch_errs = len(fbs)
    batch_t = time.time() - t0

    n = len(fbs)
    # pad batch results to n for alignment
    if len(batch_results) < n:
        batch_results = batch_results + [{}] * (n - len(batch_results))
    batch_results = batch_results[:n]

    disc_agree = evid_agree = dom_exact = 0
    jacc_sum = 0.0
    malformed = 0
    for s, b in zip(serial_results, batch_results):
        if not b:  # empty batch result → malformed
            malformed += 1
            continue
        sd = s.get("discipline", "")
        bd = b.get("discipline", "")
        if isinstance(sd, list):
            sd = sd[0] if sd else ""
        if isinstance(bd, list):
            bd = bd[0] if bd else ""
        # canonicalize discipline (case-insensitive + synonym index)
        sd_c = _canonicalize(str(sd), "discipline", synonym_index, CANONICAL_DISCIPLINES)
        bd_c = _canonicalize(str(bd), "discipline", synonym_index, CANONICAL_DISCIPLINES)
        if sd and bd and sd_c.lower() == bd_c.lower():
            disc_agree += 1
        se = s.get("evidence", "")
        be = b.get("evidence", "")
        if se == be:
            evid_agree += 1
        # canonicalize domains (raw → canonical, then compare as sets)
        sdom = set()
        for d in (s.get("domains") or []):
            sdom.add(_canonicalize(str(d), "domain", synonym_index, CANONICAL_DOMAINS))
        bdom = set()
        for d in (b.get("domains") or []):
            bdom.add(_canonicalize(str(d), "domain", synonym_index, CANONICAL_DOMAINS))
        if sdom == bdom:
            dom_exact += 1
        jacc_sum += _jaccard(sdom, bdom)

    valid = max(n - malformed, 1)
    print(f"  merged (serial): {serial_t:.1f}s total = {serial_t/n:.2f}s/FB  (errors={serial_errs})")
    print(f"  batch:            {batch_t:.1f}s total = {batch_t/n:.2f}s/FB  (errors={batch_errs})")
    print(f"  speedup: {serial_t/batch_t:.2f}x")
    print(f"  batch malformed/empty rate: {malformed}/{n} = {100*malformed/n:.0f}%  ← reliability")
    print(f"  discipline agreement (CANONICAL): {disc_agree}/{valid} = {100*disc_agree/valid:.0f}%")
    print(f"  evidence agreement:   {evid_agree}/{valid} = {100*evid_agree/valid:.0f}%")
    print(f"  domains exact-match (CANONICAL):  {dom_exact}/{valid} = {100*dom_exact/valid:.0f}%")
    print(f"  domains mean Jaccard (CANONICAL): {jacc_sum/valid:.2f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-cribs", action="store_true", help="depth only (fast)")
    args = ap.parse_args()

    fbs = _sample_principles(args.n, args.seed)
    if len(fbs) < 2:
        print("❌ Not enough principle samples.")
        return 2
    print(f"📊 Sampled {len(fbs)} principles for A/B (seed={args.seed})")

    _bench_depth(fbs)
    if not args.skip_cribs:
        _bench_cribs(fbs)

    print("\n✅ A/B complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
