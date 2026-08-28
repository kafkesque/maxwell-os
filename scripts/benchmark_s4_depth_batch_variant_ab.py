#!/usr/bin/env python3
"""benchmark_s4_depth_batch_variant_ab.py — confirm the D2483 goldilocks fix on the BATCH depth path.

The focused-path A/B (benchmark_s4_depth_prompt_ab.py) proved the V3 contrastive
prompt breaks the BUG-185 "domain" collapse. But production's depth pre-pass uses
the BATCHED prompt (DEPTH_BATCH_SYSTEM), which carries the SAME two bias lines
(`DEFAULT to "domain"` + `DO NOT over-assign ...`). This harness A/Bs the batch path:
baseline (production DEPTH_BATCH_SYSTEM) vs v3_contrastive (bias stripped + forced
4-way + contrastive anchors), using the real `batch_depth_classify()` transport so
the result is production-representative.

Measures: golden accuracy (5 few-shot goldens), label distribution over ~20 unseen
principle FBs, baseline-vs-v3 agreement, and wall-clock ms/FB.

temp=0.0 enforced by call_omlx; no production file modified (monkeypatches the
in-memory DEPTH_BATCH_SYSTEM only).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MODEL = "gpt-oss-20b-MXFP4-Q8"
CHECKPOINT = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.jsonl"
GOLDEN_PATH = REPO_ROOT / "config" / "golden" / "stage4_golden.yaml"
RESULTS_JSON = REPO_ROOT / "temp" / "s4_depth_batch_variant_ab_results.json"

VALID_DEPTHS = ("universal", "cross-domain", "domain", "specialized")


def load_goldens(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = []
    for ex in data["examples"]:
        inp = ex["input_fb"]
        out.append({
            "name": inp.get("name", ""),
            "definition": inp.get("definition", ""),
            "mechanism": inp.get("mechanism", ""),
            "extraction_type": inp.get("extraction_type", ""),
            "gold_depth": ex["expected_classification"]["depth"],
            "id": ex.get("id", ""),
        })
    return out


def load_samples(path: Path, n: int, seed: int) -> list[dict]:
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (r.get("content_type") == "principle"
                    and r.get("name") and r.get("definition") and r.get("mechanism")):
                recs.append(r)
    rng = random.Random(seed)
    rng.shuffle(recs)
    return [{
        "name": r.get("name", ""),
        "definition": r.get("definition", ""),
        "mechanism": r.get("mechanism", ""),
        "extraction_type": r.get("extraction_type", ""),
    } for r in recs[:n]]


def run_batch(fbs: list[dict]) -> tuple[list[str], float]:
    """Run production batch_depth_classify (whatever DEPTH_BATCH_SYSTEM currently is)."""
    import pipeline.stage4_merged_call as m
    t0 = time.time()
    labels = m.batch_depth_classify(fbs, model=MODEL, batch_size=4)
    return labels, time.time() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    import pipeline.stage4_merged_call as m

    goldens = load_goldens(GOLDEN_PATH)
    samples = load_samples(CHECKPOINT, args.n, args.seed)
    fbs = goldens + samples
    n_gold = len(goldens)

    print(f"BATCH A/B: {n_gold} goldens + {len(samples)} samples = {len(fbs)} FBs, model={MODEL}")

    # baseline = production DEPTH_BATCH_SYSTEM (as loaded, flag=baseline)
    print("Running BASELINE (production batch prompt)...")
    base_labels, base_t = run_batch(fbs)

    # v3 = apply the goldilocks transform to the in-memory batch system prompt only
    orig_system = m.DEPTH_BATCH_SYSTEM
    m.DEPTH_BATCH_SYSTEM = m._apply_depth_prompt_variant(orig_system)
    print("Running V3_contrastive (bias stripped + forced 4-way + anchors)...")
    try:
        v3_labels, v3_t = run_batch(fbs)
    finally:
        m.DEPTH_BATCH_SYSTEM = orig_system  # restore

    n = len(fbs)
    agree = sum(1 for a, b in zip(base_labels, v3_labels) if a == b)
    base_golden = sum(1 for i in range(n_gold) if base_labels[i] == goldens[i]["gold_depth"])
    v3_golden = sum(1 for i in range(n_gold) if v3_labels[i] == goldens[i]["gold_depth"])

    def dist(labels):
        return {d: labels.count(d) for d in VALID_DEPTHS} | {"ERR": sum(1 for l in labels if l.startswith("ERR"))}

    base_dist = dist(base_labels[n_gold:])
    v3_dist = dist(v3_labels[n_gold:])
    n_s = len(samples)

    print("\n══════════ BATCH A/B SUMMARY ══════════")
    print(f"baseline: golden {base_golden}/{n_gold}, domain {100*base_dist.get('domain',0)/max(1,n_s):.0f}%, "
          f"non-domain {100*sum(base_dist.get(d,0) for d in ('universal','cross-domain','specialized'))/max(1,n_s):.0f}%, "
          f"{base_t/n:.2f}s/FB")
    print(f"v3      : golden {v3_golden}/{n_gold}, domain {100*v3_dist.get('domain',0)/max(1,n_s):.0f}%, "
          f"non-domain {100*sum(v3_dist.get(d,0) for d in ('universal','cross-domain','specialized'))/max(1,n_s):.0f}%, "
          f"{v3_t/n:.2f}s/FB")
    print(f"baseline-vs-v3 label AGREEMENT: {agree}/{n} = {100*agree/n:.0f}%")

    print("\nper-FB labels (flips marked):")
    for i, fb in enumerate(fbs):
        a, b = base_labels[i], v3_labels[i]
        mark = " " if a == b else "⚠"
        tag = " [GOLD=" + goldens[i]["gold_depth"] + "]" if i < n_gold else ""
        print(f"  {mark} {fb['name'][:42]:44s} base={a:12s} v3={b}{tag}")

    payload = {
        "model": MODEL, "n_goldens": n_gold, "n_samples": n_s,
        "base": {"labels": base_labels, "sec": base_t, "distribution": base_dist, "golden": base_golden},
        "v3": {"labels": v3_labels, "sec": v3_t, "distribution": v3_dist, "golden": v3_golden},
        "agreement": f"{agree}/{n}",
        "names": [fb["name"] for fb in fbs],
        "gold_depths": [g["gold_depth"] for g in goldens],
    }
    import json as _json
    RESULTS_JSON.write_text(_json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {RESULTS_JSON.name}")


if __name__ == "__main__":
    main()
