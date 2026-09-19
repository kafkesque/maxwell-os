#!/usr/bin/env python3
"""ARM-2 CRIBS fair re-test — gpt-oss-20b-MXFP4-Q8 WITHOUT response_format.

Diagnosis (2026-09-15): gpt-oss-20b-MXFP4-Q8 returns a message with ONLY `role`
(no `content`) under `response_format: {"type": "json_object"}` — the naive
benchmark path raised "empty content". WITHOUT response_format it returns valid
JSON in `content` (+ `reasoning_content`). This re-runs the frozen 6 canary
clusters against gpt-oss WITHOUT response_format to get a fair route/validity
number vs the Qwen3-Coder baseline (governance/s2_qwen38_vs_coder_benchmark.json).

Read-only (no DB writes). Reuses the proven loaders + validate from
tools/benchmark_s2_qwen38_vs_coder.py.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from benchmark_s2_qwen38_vs_coder import (  # noqa: E402
    SYSTEM_PROMPT,
    build_convergent_prompt,
    load_clusters,
    load_probe_targets,
    load_segments,
    normalize_route,
    summarize,
    validate_fb_output,
)
from pipeline.pipeline_paths import OMLX_API_KEY  # noqa: E402

MODEL = "gpt-oss-20b-MXFP4-Q8"
URL = "http://127.0.0.1:11435/v1/chat/completions"  # match proven benchmark path


def call_no_rf(prompt: str, system: str, retries: int = 3) -> tuple[dict, float]:
    """Call OMLX WITHOUT response_format (gpt-oss returns empty content with it)."""
    h = {"Authorization": f"Bearer {OMLX_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
    }
    last_err: str = "unknown"
    for _ in range(retries):
        t0 = time.perf_counter()
        r = requests.post(URL, json=payload, headers=h, timeout=400)
        dt = time.perf_counter() - t0
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning_content") or ""
        if not content.strip():
            last_err = "empty content"
            continue
        try:
            return json.loads(content), dt
        except json.JSONDecodeError:
            try:
                from pipeline.json_fixer import parse_json_robust
                return parse_json_robust(content), dt
            except Exception as e:
                last_err = f"unparseable: {e}"
                continue
    raise ValueError(f"no valid JSON after {retries} attempts ({last_err})")


def main() -> int:
    targets = load_probe_targets()
    segments = load_segments()
    clusters = load_clusters()

    selected = []
    for t in targets:
        cid = t.get("cluster_id", "")
        if cid in clusters:
            selected.append(t)
        if len(selected) >= 6:
            break

    print(f"fair re-test: {MODEL} WITHOUT response_format on {len(selected)} frozen clusters\n")
    rows = []
    for i, t in enumerate(selected, 1):
        cid = t["cluster_id"]
        cluster = clusters[cid]
        prompt, _ = build_convergent_prompt(cluster, segments)
        nsegs = len(cluster.get("segment_ids", []))
        t0 = time.perf_counter()
        try:
            parsed, call_secs = call_no_rf(prompt, SYSTEM_PROMPT)
            route = normalize_route(parsed)
            valid = False
            if route == "FB" and isinstance(parsed, dict):
                valid, _ = validate_fb_output(parsed)
            elif route == "FB" and isinstance(parsed, list):
                valid = all(validate_fb_output(x)[0] for x in parsed if isinstance(x, dict))
            elif route == "NULL":
                valid = True
            name = parsed.get("name", "") if isinstance(parsed, dict) else ""
            rows.append({"cluster_id": cid, "n_segments": nsegs, "route": route,
                         "valid": valid, "secs": round(call_secs, 2), "name": name})
            print(f"  [{i}/6] {cid} nsegs={nsegs} route={route} valid={valid} {call_secs:.1f}s  {name[:40]}")
        except Exception as e:
            rows.append({"cluster_id": cid, "n_segments": nsegs, "route": "ERROR",
                         "valid": False, "secs": round(time.perf_counter() - t0, 2), "error": str(e)[:140]})
            print(f"  [{i}/6] {cid} ERROR {e}")

    s = summarize(f"{MODEL} (no response_format)", rows)
    print("\nSUMMARY:")
    print(json.dumps(s, indent=2, default=str))

    out = ROOT / "governance" / "arm2_gptoss_fair.json"
    payload = {
        "model": MODEL,
        "note": "no response_format (gpt-oss returns only `role` under json_object)",
        "summary": s,
        "rows": rows,
    }
    out.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
