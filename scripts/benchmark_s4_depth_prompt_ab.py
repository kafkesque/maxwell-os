#!/usr/bin/env python3
"""benchmark_s4_depth_prompt_ab.py — A/B the S4 depth PROMPT to find the goldilocks fix for BUG-185.

BUG-185: the depth classifier (gpt-oss-20b-MXFP4-Q8) collapses to "domain" 39/40 (97.5%).
Hypothesis (roundtable + repo): the production prompt literally instructs
`DEFAULT to "domain" unless the mechanism clearly transcends a single discipline`,
biasing the reasoning model toward "domain".

This harness tests the production prompt (V0) against three progressively stronger
prompt-only variants, on the 5 golden FBs (known depth labels) + a deterministic
sample of principle FBs. It measures:
  * GOLDEN accuracy (does each variant get the 5 known labels right?)
  * label DISTRIBUTION over the sample (is "domain" still ~97.5%? = the collapse metric)
  * wall-clock ms/FB (prompt-only changes must not regress speed)
  * ERR rate (fail-closed parse failures)

Safety: temp=0.0 is enforced inside call_omlx (R7) — this script never touches it.
No production file is modified. Results written atomically (tempfile + os.replace).

Usage:
    python3 scripts/benchmark_s4_depth_prompt_ab.py --n 8 --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MODEL = "gpt-oss-20b-MXFP4-Q8"
CHECKPOINT = REPO_ROOT / "knowledge pipeline" / "stage2_extract" / "t11" / "checkpoint.jsonl"
GOLDEN_PATH = REPO_ROOT / "config" / "golden" / "stage4_golden.yaml"
RESULTS_JSON = REPO_ROOT / "temp" / "s4_depth_prompt_ab_results.json"
RESULTS_MD = REPO_ROOT / "temp" / "s4_depth_prompt_ab_report.md"

VALID_DEPTHS = ("universal", "cross-domain", "domain", "specialized")

# ── The two biasing lines we hypothesize drive the collapse ────────────────
BIAS_LINE_1 = 'DEFAULT to "domain" unless the mechanism clearly transcends a single discipline.'
BIAS_LINE_2 = 'DO NOT over-assign "universal" or "cross-domain" — most principles are domain-bound.'

FORCED_CHOICE = """Choose among EXACTLY these four labels, evaluating each before answering:
- universal  = mechanism applies to ALL systems (physics, cooking, poetry)
- cross-domain = bridges 2+ DISTINCT disciplines via a SHARED mechanism
- domain = operates within ONE field and requires that field's context
- specialized = narrow sub-technique within a sub-field or a tool-specific skill"""

CONTRASTIVE_ANCHORS = """BOUNDARY ANCHORS (disambiguation):
- universal, NOT domain: a heavy-tailed power law holds across wealth, earthquakes, word frequency, city sizes.
- cross-domain, NOT domain: a feedback loop bridges biology homeostasis + engineering control + economics supply/demand.
- domain, NOT universal: color gamut is meaningful only within color science — strip its vocabulary and it is meaningless.
- specialized, NOT cross-domain: backpropagation is a narrow ML sub-technique, not a field-spanning principle."""


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


def build_variants(base_prompt: str) -> dict[str, str]:
    """Return {variant_name: prompt_template}. V0 is the production prompt verbatim."""
    v0 = base_prompt
    v1 = base_prompt.replace(BIAS_LINE_1 + "\n", "").replace(BIAS_LINE_2 + "\n", "")
    v2 = v1.replace(
        "Answer EXACTLY ONE WORD: specialized, domain, cross-domain, or universal. No reasoning.",
        FORCED_CHOICE + "\n\nAnswer with EXACTLY ONE of the four labels. No reasoning.",
    )
    v3 = v2.replace(
        "Answer with EXACTLY ONE of the four labels. No reasoning.",
        CONTRASTIVE_ANCHORS + "\n\nAnswer with EXACTLY ONE of the four labels. No reasoning.",
    )
    return {"V0_baseline": v0, "V1_no_bias": v1, "V2_forced_choice": v2, "V3_contrastive": v3}


def classify(prompt: str, fb: dict) -> tuple[str, float]:
    """Classify one FB depth via call_omlx. Returns (label_or_ERR, ms)."""
    from pipeline.omlx_call import call_omlx
    from pipeline.stage4_merged_call import _parse_depth_token, DepthClassificationError
    text = prompt.format(
        name=fb["name"],
        definition=fb["definition"],
        mechanism=fb["mechanism"],
        extraction_type=fb.get("extraction_type", ""),
    )
    t0 = time.time()
    try:
        raw = call_omlx(prompt=text, model=MODEL, max_tokens=512, thinking_budget=128)
        label = _parse_depth_token(raw)
    except DepthClassificationError as e:
        label = f"ERR:ambiguous"
        sys.stderr.write(f"    [parse] {fb['name'][:40]} -> {e}\n")
    except Exception as e:
        label = f"ERR:{type(e).__name__}"
        sys.stderr.write(f"    [call] {fb['name'][:40]} -> {type(e).__name__}: {e}\n")
    return label, (time.time() - t0) * 1000.0


def atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())  # D2177/D2487: flush to disk before replace
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from pipeline.stage4_merged_call import DEPTH_FOCUSED_PROMPT  # production prompt (goldens baked in at import)

    goldens = load_goldens(GOLDEN_PATH)
    samples = load_samples(CHECKPOINT, args.n, args.seed)
    fbs = goldens + samples  # goldens first → golden accuracy is the first 5 rows
    variants = build_variants(DEPTH_FOCUSED_PROMPT)

    print(f"FBs: {len(goldens)} goldens + {len(samples)} samples = {len(fbs)} total; model={MODEL}")
    results = {}
    for vname, vprompt in variants.items():
        labels, times = [], []
        for i, fb in enumerate(fbs):
            lab, ms = classify(vprompt, fb)
            labels.append(lab)
            times.append(ms)
            print(f"  {vname:16s} fb={i:2d} {lab:16s} {ms:7.0f}ms  {fb['name'][:38]}")
        results[vname] = {"labels": labels, "ms_per_fb": times}
        print()

    # ── Aggregate ──
    n_gold = len(goldens)
    summary = {}
    for vname, r in results.items():
        labels = r["labels"]
        golden_acc = sum(1 for i in range(n_gold) if labels[i] == goldens[i]["gold_depth"])
        sample_labels = labels[n_gold:]
        dist = {d: sample_labels.count(d) for d in VALID_DEPTHS}
        dist["ERR"] = sum(1 for l in sample_labels if l.startswith("ERR"))
        non_domain = sum(1 for l in sample_labels if l in ("universal", "cross-domain", "specialized"))
        mean_ms = sum(r["ms_per_fb"]) / len(r["ms_per_fb"])
        summary[vname] = {
            "golden_accuracy": f"{golden_acc}/{n_gold}",
            "golden_hits": [i for i in range(n_gold) if labels[i] == goldens[i]["gold_depth"]],
            "sample_distribution": dist,
            "sample_non_domain_pct": round(100 * non_domain / max(1, len(sample_labels)), 1),
            "mean_ms_per_fb": round(mean_ms, 0),
        }

    print("══════════════ A/B SUMMARY ══════════════")
    header = f"{'variant':16s} {'golden':9s} {'domain%':9s} {'non-dom%':9s} {'ms/FB':8s}"
    print(header)
    print("-" * len(header))
    for vname in variants:
        s = summary[vname]
        d = s["sample_distribution"]
        dom_pct = round(100 * d.get("domain", 0) / max(1, sum(d.values())), 1)
        print(f"{vname:16s} {s['golden_accuracy']:9s} {dom_pct:8.1f}% {s['sample_non_domain_pct']:8.1f}% {s['mean_ms_per_fb']:7.0f}")

    payload = {
        "model": MODEL,
        "n_goldens": n_gold,
        "n_samples": len(samples),
        "goldens": goldens,
        "variants": {v: {"labels": results[v]["labels"], "ms_per_fb": results[v]["ms_per_fb"]} for v in results},
        "summary": summary,
    }
    atomic_write(RESULTS_JSON, json.dumps(payload, indent=2))

    # markdown report
    lines = ["# S4 Depth Prompt A/B — BUG-185 goldilocks search\n",
             f"- model: {MODEL} (temp=0.0 enforced by call_omlx)", f"- FBs: {n_gold} goldens + {len(samples)} samples",
             "", "| variant | golden acc | domain% | non-domain% | ms/FB |", "|---|---|---|---|---|"]
    for vname in variants:
        s = summary[vname]
        d = s["sample_distribution"]
        dom_pct = round(100 * d.get("domain", 0) / max(1, sum(d.values())), 1)
        lines.append(f"| {vname} | {s['golden_accuracy']} | {dom_pct:.1f}% | {s['sample_non_domain_pct']:.1f}% | {s['mean_ms_per_fb']:.0f} |")
    lines += ["", "## Golden per-FB labels", ""]
    for vname in variants:
        lines.append(f"### {vname}")
        for i in range(n_gold):
            lines.append(f"- {goldens[i]['id']} (gold={goldens[i]['gold_depth']}) → {results[vname]['labels'][i]}")
        lines.append("")
    atomic_write(RESULTS_MD, "\n".join(lines))
    print(f"\nWrote {RESULTS_JSON.name} + {RESULTS_MD.name}")


if __name__ == "__main__":
    main()
