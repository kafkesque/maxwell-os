#!/usr/bin/env python3
"""ARM-4 — lightweight model bake-off (in-process MLX inference).

Tasks:
  1. S4 classification sanity — discipline/domain agreement vs gold_4axis (reviewer/classifier role).
  2. S2 convergent extraction — route/validity on the 6 frozen canary clusters (generator role).

Models (all MLX, loaded via mlx_lm + optiq):
  candidates: Ornith-1.5-9B, gemma-4-12B-qat, Ornith-1.5-35B-A3B-REAP-19B
  baselines : Phi-4-mini-instruct-8bit (current probe), DeepSeek-R1-0528-Qwen3-8B (llmfit pick)

Deterministic (temp default 0 via mlx_lm, seed 42 for sampling), read-only (no DB writes).
"""
from __future__ import annotations

import argparse
import json
import re
import random
import sqlite3
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import optiq  # noqa: F401  (registers OptiQ arch for mlx_lm)
from mlx_lm import load, generate  # noqa: E402

from benchmark_s2_qwen38_vs_coder import (  # noqa: E402
    SYSTEM_PROMPT, build_convergent_prompt, load_clusters, load_probe_targets,
    load_segments, normalize_route, validate_fb_output,
)

DB = ROOT / "knowledge pipeline" / "maxwell.db"
GOLD = ROOT / "governance" / "gold_4axis.jsonl"
TAX = ROOT / "config" / "taxonomy_v5.yaml"

MODELS = [
    "mlx-community/Ornith-1.5-9B-OptiQ-4bit",
    "mlx-community/gemma-4-12B-it-qat-OptiQ-4bit",
    "mlx-community/Ornith-1.5-35B-A3B-OptiQ-4bit-REAP-19B",
    "mlx-community/Phi-4-mini-instruct-8bit",
]


def load_taxonomy() -> tuple[list, list]:
    t = yaml.safe_load(TAX.read_text(encoding="utf-8"))
    def _canon(v):
        return v["canonical"] if isinstance(v, dict) else v
    return [_canon(x) for x in t["disciplines"]], [_canon(x) for x in t["domains"]]


def load_gold_sample(n: int) -> list[dict]:
    rows = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("discipline") and r.get("domains")]
    random.seed(42)
    return random.sample(rows, min(n, len(rows)))


def fetch_texts(fb_ids: list[str]) -> dict[str, str]:
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    q = "SELECT fb_id, name, definition, mechanism, boundary FROM fbs WHERE fb_id IN (%s)" % (
        ",".join("?" * len(fb_ids))
    )
    out: dict[str, str] = {}
    for r in db.execute(q, fb_ids):
        parts = [p for p in (r["name"], r["definition"], r["mechanism"], r["boundary"]) if p]
        out[r["fb_id"]] = " ".join(parts)[:2048]
    db.close()
    return out


def classify_prompt(text: str, disciplines: list, domains: list) -> str:
    return (
        "Classify this principle into exactly ONE discipline and ONE OR MORE domains.\n"
        f"Disciplines: {', '.join(disciplines)}\n"
        f"Domains: {', '.join(domains)}\n\n"
        f"Principle: {text}\n\n"
        'Return ONLY JSON: {"discipline": "<one>", "domains": ["<d1>", ...]}'
    )


def parse_json(s: str):
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def gen_chat(model, tok, system: str, user: str, max_tokens: int = 512) -> str:
    """Chat generate. Disables thinking for reasoning models (else the trace eats the budget)."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kw = {"tokenize": False, "add_generation_prompt": True}
    if "enable_thinking" in (tok.chat_template or ""):
        kw["enable_thinking"] = False
    prompt = tok.apply_chat_template(messages, **kw)
    return generate(model, tok, prompt=prompt, max_tokens=max_tokens)


def run_classification(model, tok, sample, disciplines, domains) -> dict:
    ok = 0
    dom_f1 = 0.0
    n = 0
    for r in sample:
        gold_disc = r["discipline"].strip().lower()
        gold_dom = {x.strip().lower() for x in r["domains"]}
        try:
            out = gen_chat(model, tok, "You are a precise taxonomy classifier.",
                           classify_prompt(r["_text"], disciplines, domains), 512)
        except Exception:
            continue
        parsed = parse_json(out)
        if not parsed:
            continue
        n += 1
        pred_disc = str(parsed.get("discipline", "")).strip().lower()
        if pred_disc == gold_disc:
            ok += 1
        pred_dom = {x.strip().lower() for x in (parsed.get("domains") or [])}
        tp = len(gold_dom & pred_dom)
        fp = len(pred_dom - gold_dom)
        fn = len(gold_dom - pred_dom)
        dom_f1 += 2 * tp / (2 * tp + fp + fn + 1e-9)
    return {"discipline_acc": round(ok / max(n, 1), 4), "domain_f1": round(dom_f1 / max(n, 1), 4), "n": n}


def run_extraction(model, tok, clusters, targets, segments) -> dict:
    selected = []
    for t in targets:
        cid = t.get("cluster_id", "")
        if cid in clusters:
            selected.append(t)
        if len(selected) >= 6:
            break
    rows = []
    for t in selected:
        cid = t["cluster_id"]
        cluster = clusters[cid]
        prompt, _ = build_convergent_prompt(cluster, segments)
        t0 = time.perf_counter()
        try:
            out = gen_chat(model, tok, SYSTEM_PROMPT, prompt, 4096)
            parsed = parse_json(out)
            if parsed is None:
                parsed = {"_raw": out[:200]}
            route = normalize_route(parsed)
            valid = False
            if route == "FB" and isinstance(parsed, dict):
                valid, _ = validate_fb_output(parsed)
            elif route == "FB" and isinstance(parsed, list):
                valid = all(validate_fb_output(x)[0] for x in parsed if isinstance(x, dict))
            elif route == "NULL":
                valid = True
            rows.append({"route": route, "valid": valid, "secs": round(time.perf_counter() - t0, 1)})
        except Exception as e:
            rows.append({"route": "ERROR", "valid": False, "secs": round(time.perf_counter() - t0, 1), "error": str(e)[:100]})
    n_fb = sum(1 for r in rows if r["route"] == "FB")
    n_null = sum(1 for r in rows if r["route"] == "NULL")
    n_valid = sum(1 for r in rows if r["valid"])
    return {"n": len(rows), "fb": n_fb, "null": n_null, "valid": n_valid, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-classify", type=int, default=30)
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--skip-extract", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "governance" / "arm4_benchmark.json"))
    args = ap.parse_args()

    disciplines, domains = load_taxonomy()
    sample = load_gold_sample(args.n_classify)
    fb_ids = [r["fb_id"] for r in sample]
    texts = fetch_texts(fb_ids)
    for r in sample:
        r["_text"] = texts.get(r["fb_id"], r.get("name", ""))

    targets = load_probe_targets()
    segments = load_segments()
    clusters = load_clusters()

    print(f"ARM-4: {len(args.models)} models | {len(sample)} classify rows | 6 extract clusters\n")

    results = {}
    for m in args.models:
        print(f"\n{'='*70}\nMODEL: {m}\n{'='*70}", flush=True)
        t0 = time.perf_counter()
        try:
            model, tok = load(m)
            load_secs = time.perf_counter() - t0
            print(f"  loaded in {load_secs:.1f}s", flush=True)
        except Exception as e:
            print(f"  LOAD FAILED: {e}", flush=True)
            results[m] = {"load_error": str(e)[:200]}
            continue

        cls = run_classification(model, tok, sample, disciplines, domains)
        print(f"  [classify] discipline_acc={cls['discipline_acc']:.3f} domain_f1={cls['domain_f1']:.3f} n={cls['n']}", flush=True)

        ext = None
        if not args.skip_extract:
            ext = run_extraction(model, tok, clusters, targets, segments)
            print(f"  [extract] valid={ext['valid']}/{ext['n']} (FB={ext['fb']} NULL={ext['null']})", flush=True)

        results[m] = {"classify": cls, "extract": ext, "load_secs": round(load_secs, 1)}
        del model, tok

    out = Path(args.out)
    out.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
