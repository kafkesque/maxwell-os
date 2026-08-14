#!/usr/bin/env python3
"""
A/B Test — S4 depth bottleneck: existing sequential vs D2354 batched (D2354).
================================================================================
Compares, side-by-side, the EXISTING production path (A) and the proposed
D2354 path (B) for the S4 focused-depth classification:

  Path A (existing):  classify_depth_focused() — ONE GPT-OSS call per FB
                      (serialized ~10s/FB; reasoning-model CoT paid per call).

  Path B (proposed):  batch_depth_classify() — N FBs per GPT-OSS call
                      (amortized ~1-2s/FB; same SHORT prompt + ontology).

Measures, against the golden set (config/golden/stage2_fewshot_convergent.yaml):
  1. latency (per-FB + total) and the A→B speedup
  2. accuracy vs golden depth label
  3. A↔B parity (agreement %)
  4. fail-closed events (empty content / ambiguous answer / missing batch entry)

Gate (D2354 PHASE 2): adopt B only if (B vs A agreement ≥ 90%) AND (zero silent
failures). A silent failure is an exception the old code would have swallowed
into "domain" — now surfaced by the fail-closed M1 change.

Usage:
    python3 tools/ab_test_s4_bottleneck.py                 # live (needs OMLX)
    python3 tools/ab_test_s4_bottleneck.py --n 6 --seed 42
    python3 tools/ab_test_s4_bottleneck.py --dry-run       # validate wiring, no OMLX
    python3 tools/ab_test_s4_bottleneck.py --model gemma-4-E4B-it-MLX-4bit
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.stage4_merged_call import (  # noqa: E402
    DepthClassificationError,
    batch_depth_classify,
    classify_depth_focused,
)

GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
OUT_MD = PROJECT_ROOT / "governance" / "s4_bottleneck_ab_test.md"
OUT_JSON = PROJECT_ROOT / "governance" / "s4_bottleneck_ab_test.json"

DEPTH_ORDER = ["specialized", "domain", "cross-domain", "universal"]
DEFAULT_MODEL = "gpt-oss-20b-MXFP4-Q8"


def load_test_set() -> list[dict]:
    """Load golden FBs with depth labels (same source as the depth benchmark)."""
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
                "extraction_type": fb.get("extraction_type", "causal_mechanism"),
                "gold_depth": fb["depth"],
                "golden_id": ex.get("id", "?"),
            })
    return fbs


def stratified_sample(test_fbs: list[dict], per_class: int, seed: int) -> list[dict]:
    """Stratified sample across the 4 depth classes (reproducible)."""
    random.seed(seed)
    stratified = {d: [] for d in DEPTH_ORDER}
    for fb in test_fbs:
        if fb["gold_depth"] in stratified:
            stratified[fb["gold_depth"]].append(fb)
    sampled = []
    for d in DEPTH_ORDER:
        n = min(len(stratified[d]), per_class)
        sampled.extend(random.sample(stratified[d], n))
    random.shuffle(sampled)
    return sampled


def run_path_a(fbs: list[dict], model: str, max_tokens: int) -> tuple[list, list]:
    """Path A — existing sequential classify_depth_focused()."""
    results, times, failures = [], [], []
    for fb in fbs:
        t0 = time.time()
        try:
            depth = classify_depth_focused(fb, model=model, max_tokens=max_tokens)
            results.append(depth)
            failures.append(None)
        except Exception as e:  # fail-closed: surfaced, not swallowed
            results.append(None)
            failures.append(f"{type(e).__name__}: {str(e)[:120]}")
        times.append(round(time.time() - t0, 2))
    return results, times, failures


def run_path_b(fbs: list[dict], model: str, max_tokens: int, batch_size: int) -> tuple[list, list]:
    """Path B — proposed batch_depth_classify()."""
    # One batched call for the whole set (function chunks internally), but we
    # time per-FB by measuring the single call and dividing, since the call is
    # the only work. Record the wall-clock of the whole call for fairness.
    t0 = time.time()
    try:
        results = batch_depth_classify(fbs, model=model, max_tokens=max_tokens, batch_size=batch_size)
        failures = [None] * len(fbs)
    except Exception as e:
        results = [None] * len(fbs)
        failures = [f"{type(e).__name__}: {str(e)[:120]}"] * len(fbs)
    wall = time.time() - t0
    per_fb = round(wall / max(len(fbs), 1), 2)
    times = [per_fb] * len(fbs)
    return results, times, failures


def main() -> None:
    ap = argparse.ArgumentParser(description="A/B test S4 depth bottleneck (D2354)")
    ap.add_argument("--n", type=int, default=8, help="per-class sample size (default 8)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="validate wiring without OMLX")
    args = ap.parse_args()

    test_fbs = load_test_set()
    fbs = stratified_sample(test_fbs, per_class=args.n, seed=args.seed)
    print(f"Golden FBs available: {len(test_fbs)} | sampled: {len(fbs)}")
    print(f"Model: {args.model} | max_tokens={args.max_tokens} | batch_size={args.batch_size}")
    print(f"Depth distribution (sampled): {dict(Counter(f['gold_depth'] for f in fbs))}")

    if args.dry_run:
        # Validate wiring only — substitute deterministic fake responses at the
        # SOURCE module (classify_depth_focused lazy-imports call_omlx).
        import pipeline.omlx_call as oc
        import pipeline.stage4_merged_call as sm
        import re as _re

        def _fake_depth_reply(prompt, model=None, system=None, max_tokens=1024, timeout=120, **kw):
            # Deterministic: return the depth token appearing in the prompt, else "domain".
            m = _re.search(r"Type:\s*(specialized|domain|cross-domain|universal)", prompt or "")
            return m.group(1) if m else "domain"

        def _fake_json_reply(prompt, model=None, system=None, max_tokens=1024, timeout=120, **kw):
            n_fb = (prompt or "").count("--- FB ")
            return [{"fb_index": i, "depth": "domain"} for i in range(max(1, n_fb))]

        # Patch BOTH import paths: lazy `from pipeline.omlx_call import call_omlx`
        # (used by classify_depth_focused) and the top-level binding in
        # stage4_merged_call (used by batch_depth_classify).
        oc.call_omlx = _fake_depth_reply
        oc.call_omlx_json = _fake_json_reply
        sm.call_omlx_json = _fake_json_reply
        print("  (dry-run: OMLX calls stubbed at pipeline.omlx_call + stage4_merged_call)")

    a_results, a_times, a_failures = run_path_a(fbs, args.model, args.max_tokens)
    b_results, b_times, b_failures = run_path_b(fbs, args.model, args.max_tokens, args.batch_size)

    # ── Metrics ──
    n = len(fbs)
    a_total = sum(a_times)
    b_total = sum(b_times)
    a_acc = sum(1 for r, f in zip(a_results, fbs) if r == f["gold_depth"]) / n
    b_acc = sum(1 for r, f in zip(b_results, fbs) if r == f["gold_depth"]) / n
    parity = sum(1 for a, b in zip(a_results, b_results) if a == b) / n
    a_fail_count = sum(1 for x in a_failures if x)
    b_fail_count = sum(1 for x in b_failures if x)
    speedup = (a_total / b_total) if b_total else float("inf")

    rows = []
    for i, fb in enumerate(fbs):
        rows.append({
            "id": fb["golden_id"],
            "gold": fb["gold_depth"],
            "A": a_results[i],
            "A_t": a_times[i],
            "A_ok": a_results[i] == fb["gold_depth"],
            "B": b_results[i],
            "B_t": b_times[i],
            "B_ok": b_results[i] == fb["gold_depth"],
            "agree": a_results[i] == b_results[i],
        })

    gate_pass = (parity >= 0.90) and (b_fail_count == 0)

    # ── Console report ──
    print("\n" + "=" * 78)
    print("A/B RESULT — S4 focused depth (D2354)")
    print("=" * 78)
    print(f"  Path A (sequential)  total={a_total:.1f}s  avg={a_total/n:.1f}s/FB  acc={a_acc:.1%}  failures={a_fail_count}")
    print(f"  Path B (batched)     total={b_total:.1f}s  avg={b_total/n:.1f}s/FB  acc={b_acc:.1%}  failures={b_fail_count}")
    print(f"  A↔B parity={parity:.1%}   speedup={speedup:.1f}×")
    print(f"  GATE (parity≥90% + 0 silent failures): {'✅ PASS' if gate_pass else '❌ FAIL'}")
    print("\n  Per-FB:")
    for r in rows:
        flag = "✅" if r["agree"] else "❌"
        print(f"    {r['id']:>8s} gold={r['gold']:14s} A={str(r['A']):14s} ({r['A_t']:5.1f}s) "
              f"B={str(r['B']):14s} ({r['B_t']:5.1f}s) {flag}")
    if a_fail_count or b_fail_count:
        print("\n  Fail-closed events (surfaced, not swallowed):")
        for i, fb in enumerate(fbs):
            if a_failures[i]:
                print(f"    [A] {fb['golden_id']}: {a_failures[i]}")
            if b_failures[i]:
                print(f"    [B] {fb['golden_id']}: {b_failures[i]}")

    # ── Write markdown report ──
    md = [
        "# S4 Depth Bottleneck — A/B Test (D2354)",
        "",
        f"> Generated: {time.strftime('%Y-%m-%d %H:%M:%S')} · Model: `{args.model}` · "
        f"max_tokens={args.max_tokens} · batch_size={args.batch_size} · seed={args.seed}",
        "",
        "## Summary",
        "",
        "| Path | Strategy | Total | Avg/FB | Accuracy vs golden | Fail-closed events |",
        "|---|---|---|---|---|---|",
        f"| **A — existing** | sequential `classify_depth_focused()` | {a_total:.1f}s | {a_total/n:.1f}s | {a_acc:.1%} | {a_fail_count} |",
        f"| **B — proposed** | `batch_depth_classify()` (batch={args.batch_size}) | {b_total:.1f}s | {b_total/n:.1f}s | {b_acc:.1%} | {b_fail_count} |",
        "",
        f"- **A↔B parity:** {parity:.1%}",
        f"- **Speedup:** {speedup:.1f}×",
        f"- **Gate (≥90% parity + 0 silent failures):** {'✅ PASS' if gate_pass else '❌ FAIL'}",
        "",
        "## Per-FB",
        "",
        "| Golden | Depth | A (existing) | A time | B (proposed) | B time | Agree |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        md.append(
            f"| {r['id']} | {r['gold']} | {r['A']} | {r['A_t']}s | {r['B']} | {r['B_t']}s | "
            f"{'✅' if r['agree'] else '❌'} |"
        )
    md += ["", "## Fail-closed events (surfaced by M1, not swallowed into `domain`)", ""]
    ev = []
    for i, fb in enumerate(fbs):
        if a_failures[i]:
            ev.append(f"- **[A] {fb['golden_id']}:** `{a_failures[i]}`")
        if b_failures[i]:
            ev.append(f"- **[B] {fb['golden_id']}:** `{b_failures[i]}`")
    md += ev if ev else ["_None — both paths returned a valid depth label for every FB._"]
    md += ["", "## Verdict", ""]
    if gate_pass:
        md += [
            "Path B (batched) meets the D2354 PHASE-2 gate. It is safe to adopt the batched "
            "focused-depth path in production — same prompt/ontology, ~%.1f× faster, no silent failures." % speedup,
        ]
    else:
        md += [
            "Path B does **not** yet meet the gate. Do not adopt until parity ≥ 90% and zero "
            "silent failures are reproduced. Investigate the per-FB mismatches above.",
        ]

    OUT_MD.write_text("\n".join(md) + "\n")
    OUT_JSON.write_text(json.dumps({
        "model": args.model, "n": n, "seed": args.seed,
        "batch_size": args.batch_size, "max_tokens": args.max_tokens,
        "path_a": {"total_s": a_total, "avg_s": a_total / n, "accuracy": a_acc, "failures": a_fail_count},
        "path_b": {"total_s": b_total, "avg_s": b_total / n, "accuracy": b_acc, "failures": b_fail_count},
        "parity": parity, "speedup_x": speedup, "gate_pass": gate_pass,
        "rows": rows,
    }, indent=2) + "\n")

    print(f"\n📄 Report: {OUT_MD}")
    print(f"📄 Data:   {OUT_JSON}")


if __name__ == "__main__":
    main()
