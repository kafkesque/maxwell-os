#!/usr/bin/env python3
"""ARM-4c — OMLX-served re-test (fair gpt-oss: OMLX handles its harmony/reasoning format).

Runs the 10 capability tasks + 30-row classification + S2 convergent extraction
(6 frozen canary clusters) through the OMLX HTTP API.

Usage: python3 scripts/arm4_omlx.py --models gpt-oss-20b-MXFP4-Q8 Qwen3.8-27B-MLX-4bit
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from arm4_capabilities import TASKS  # noqa: E402
from arm4_benchmark import (  # noqa: E402
    SYSTEM_PROMPT, build_convergent_prompt, classify_prompt, fetch_texts,
    load_clusters, load_gold_sample, load_probe_targets, load_segments,
    load_taxonomy, normalize_route, parse_json, validate_fb_output,
)

URL = "http://127.0.0.1:11435/v1/chat/completions"
KEY = "sk-maxwell-local"


def call(model: str, system: str, user: str, max_tokens: int = 1024) -> str:
    r = requests.post(
        URL,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.0,
            "max_tokens": max_tokens,
        },
        timeout=900,
    )
    r.raise_for_status()
    return (r.json()["choices"][0]["message"].get("content") or "").strip()


def run_extraction(m, clusters, targets, segments) -> dict:
    selected = []
    for t in targets:
        cid = t.get("cluster_id", "")
        if cid in clusters:
            selected.append(t)
        if len(selected) >= 6:
            break
    rows = []
    for t in selected:
        cluster = clusters[t["cluster_id"]]
        prompt, _ = build_convergent_prompt(cluster, segments)
        try:
            out = call(m, SYSTEM_PROMPT, prompt, 4096)
            p = parse_json(out)
            if p is None:
                p = {"_raw": out[:200]}
            route = normalize_route(p)
            valid = False
            if route == "FB" and isinstance(p, dict):
                valid, _ = validate_fb_output(p)
            elif route == "FB" and isinstance(p, list):
                valid = all(validate_fb_output(x)[0] for x in p if isinstance(x, dict))
            elif route == "NULL":
                valid = True
            rows.append({"route": route, "valid": valid})
        except Exception:
            rows.append({"route": "ERROR", "valid": False})
    return {
        "n": len(rows),
        "fb": sum(1 for r in rows if r["route"] == "FB"),
        "null": sum(1 for r in rows if r["route"] == "NULL"),
        "valid": sum(1 for r in rows if r["valid"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--n-classify", type=int, default=30)
    ap.add_argument("--out", default=str(ROOT / "governance" / "arm4_omlx.json"))
    args = ap.parse_args()

    disciplines, domains = load_taxonomy()
    sample = load_gold_sample(args.n_classify)
    texts = fetch_texts([r["fb_id"] for r in sample])
    for r in sample:
        r["_text"] = texts.get(r["fb_id"], r.get("name", ""))
    targets = load_probe_targets()
    segments = load_segments()
    clusters = load_clusters()

    results: dict[str, dict] = {}
    for m in args.models:
        print(f"\n{'='*66}\nMODEL (OMLX): {m}\n{'='*66}", flush=True)
        caps: dict[str, list] = {}
        for cap, tid, system, user, check in TASKS:
            try:
                out = call(m, system, user, 1024)
                ok = check(out)
            except Exception as e:
                out, ok = f"ERR {e}", False
            caps.setdefault(cap, []).append(1 if ok else 0)
            print(f"  [{'PASS' if ok else 'FAIL'}] {cap:14s} {tid:10s} {repr(out[:65])}", flush=True)

        ok = 0
        dom_f1 = 0.0
        n = 0
        for r in sample:
            try:
                out = call(m, "You are a precise taxonomy classifier.",
                           classify_prompt(r["_text"], disciplines, domains), 1024)
            except Exception:
                continue
            p = parse_json(out)
            if not p:
                continue
            n += 1
            if str(p.get("discipline", "")).strip().lower() == r["discipline"].strip().lower():
                ok += 1
            gold = {x.strip().lower() for x in r["domains"]}
            pred = {x.strip().lower() for x in (p.get("domains") or [])}
            tp, fp, fn = len(gold & pred), len(pred - gold), len(gold - pred)
            dom_f1 += 2 * tp / (2 * tp + fp + fn + 1e-9)
        cls = {"discipline_acc": round(ok / max(n, 1), 4), "domain_f1": round(dom_f1 / max(n, 1), 4), "n": n}
        print(f"  [classify] discipline_acc={cls['discipline_acc']:.3f} domain_f1={cls['domain_f1']:.3f} n={cls['n']}", flush=True)

        ext = run_extraction(m, clusters, targets, segments)
        print(f"  [extract] valid={ext['valid']}/{ext['n']} (FB={ext['fb']} NULL={ext['null']})", flush=True)

        results[m] = {
            **{c: round(sum(v) / len(v), 3) for c, v in caps.items()},
            "_overall_capability": round(sum(sum(v) for v in caps.values()) / sum(len(v) for v in caps.values()), 3),
            "classify": cls,
            "extract": ext,
        }

    Path(args.out).write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
