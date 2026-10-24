#!/usr/bin/env python3
"""
MTP A/B instrument — Lightning MTP (multi-token prediction) before/after decode throughput.

D-293 re-scope (2026-09-22, community-benchmark-first rule D-332): oMLX 0.7's Lightning MTP
claim (+34-58% decode on Qwen3/DeepSeek/GLM) is a VENDOR number measured on M4/M5. Community
evidence on the EXACT M1 Max hardware (ARahim3/mlx-dspark#38) shows speculative decode is a
NET LOSS (0.55-0.91x) because the old GPU is compute-bound on multi-token verify while the
single-token baseline is bandwidth-bound. So we MEASURE, not assume.

This script is the instrument (A10 pattern: "instrument, not a vibe"):
  1. --toggle on|off   : patch mtp_enabled for the target model in ~/.omlx/model_settings.json
                         (crash-safe: tempfile -> fsync -> os.replace, plus .bak; C6/C13), then
                         ask oMLX to reload (scripts/omlx_reload.py) so the change takes effect.
  2. --measure --label : run a FROZEN batch of S2-style prompts through the oMLX chat/completions
                         endpoint with stream=True, measuring ttft (prefill) and decode tok/s,
                         and append labelled results to a JSONL results file (crash-safe).
  3. --compare A B     : load two labelled runs and report the decode-tok/s ratio (+win/-loss).

Workflow (operator gates the disruptive reload explicitly):
    python3 scripts/mtp_ab.py --toggle off                 # ensure MTP off, reload
    python3 scripts/mtp_ab.py --measure --label mtp_off
    python3 scripts/mtp_ab.py --toggle on                  # enable MTP, reload
    python3 scripts/mtp_ab.py --measure --label mtp_on
    python3 scripts/mtp_ab.py --compare mtp_off mtp_on     # the verdict

Generator != Verifier (R5): this measures SPEED only. It never asserts a quality/accuracy
conclusion — adoption still requires the D-293 golden-gate on a frozen S2 batch.

temp=0.0 is enforced on every call (R7). Model name + OMLX URL come from config (C12).
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests  # noqa: E402

from pipeline.pipeline_paths import GEN_MODEL, OMLX_URL, OMLX_API_KEY  # noqa: E402  (C12: config-sourced)

# oMLX has API-key auth enabled (401 without it) — same header as omlx_call.py.
AUTH_HEADERS = {"Authorization": f"Bearer {OMLX_API_KEY}"}

# ── De-hardcoded defaults (C12): CLI-overridable, config/env-backed where it exists ──
MODEL_SETTINGS_DEFAULT = Path.home() / ".omlx" / "model_settings.json"
RESULTS_DEFAULT = PROJECT_ROOT / "governance" / "mtp_ab_results.jsonl"
TEMPERATURE = 0.0  # R7 — never override
DEFAULT_MAX_TOKENS = 512
DEFAULT_N_PROMPTS = 8

# Frozen S2-style extraction prompts (deterministic). Content is a throughput control, not a
# quality eval: input length drives prefill, --max-tokens drives decode (the MTP-affected axis).
_FROZEN_PROMPTS = [
    "Extract every convergent principle from the following excerpt as a structured Foundation Block "
    "(name, definition, mechanism, boundary). Respond with JSON only. Excerpt: "
    + ("Feedback loops appear across biology, economics, and organizations. When a system's output "
       "feeds back to modulate its own input, stability or runaway growth can result. ") * 6,
    "Classify the depth of this principle and list its source disciplines. Principle: entropy "
    "increases in closed systems. " + ("Irreversibility, heat, and disorder are all manifestations "
       "of the same underlying asymmetry. ") * 6,
    "Merge these two principles into one convergent Foundation Block and justify the merge. "
    + ("Principle A concerns anchoring: initial values bias later estimates. Principle B concerns "
       "the default effect: pre-selected options are chosen disproportionately. ") * 6,
]


def read_model_settings(path: Path) -> dict:
    """Load the oMLX model_settings.json file as a dict."""
    with open(path) as f:
        return json.load(f)


def find_model_block(settings: dict, model: str) -> dict:
    """Return the per-model settings dict, tolerating top-level 'models' nesting."""
    models = settings.get("models", settings)
    if model not in models:
        raise KeyError(f"model {model!r} not found in {MODEL_SETTINGS_DEFAULT}")
    return models[model]


def crash_safe_write(path: Path, data: dict) -> None:
    """Crash-safe JSON write: tempfile -> fsync -> os.replace (C6)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def toggle_mtp(model: str, enable: bool, settings_path: Path) -> bool:
    """Patch mtp_enabled for the target model and return the new value."""
    settings = read_model_settings(settings_path)
    block = find_model_block(settings, model)
    prev = block.get("mtp_enabled", False)
    block["mtp_enabled"] = enable
    # Backup before overwrite (C13) — governance-side safety, not a silent mutation.
    backup = settings_path.with_suffix(settings_path.suffix + ".bak")
    crash_safe_write(backup, read_model_settings(settings_path))
    crash_safe_write(settings_path, settings)
    print(f"[toggle] {model}: mtp_enabled {prev} -> {enable}  (backup: {backup.name})")
    return enable


def reload_omlx() -> None:
    """Ask oMLX to reload so the model-settings change takes effect (operator-gated)."""
    reload_script = PROJECT_ROOT / "scripts" / "omlx_reload.py"
    if not reload_script.exists():
        print("[toggle] WARN: scripts/omlx_reload.py not found — restart oMLX manually.")
        return
    import subprocess
    subprocess.run([sys.executable, str(reload_script)], check=False)


def frozen_prompts(n: int) -> list[str]:
    """Return a deterministic frozen batch of n prompts (cycled, length-controlled)."""
    return [_FROZEN_PROMPTS[i % len(_FROZEN_PROMPTS)] for i in range(n)]


def measure_one(prompt: str, model: str, max_tokens: int, timeout: int) -> dict:
    """Measure ttft + decode tok/s for a single prompt via stream=True (fallback: non-stream)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
        "stream": True,
    }
    t0 = time.monotonic()
    n_tokens = 0
    t_ttft = None
    t_end = t0
    try:
        with requests.post(
            f"{OMLX_URL}/v1/chat/completions", json=payload, stream=True,
            timeout=timeout, headers=AUTH_HEADERS,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                chunk = json.loads(data)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    if t_ttft is None:
                        t_ttft = time.monotonic()
                    n_tokens += 1
                    t_end = time.monotonic()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        return _measure_fallback(prompt, model, max_tokens, timeout, error=str(exc))

    if t_ttft is None:
        return _measure_fallback(prompt, model, max_tokens, timeout, error="no stream tokens")
    total = t_end - t0
    ttft = t_ttft - t0
    decode_time = max(t_end - t_ttft, 1e-6)
    return {
        "error": None,
        "n_tokens": n_tokens,
        "ttft_s": round(ttft, 3),
        "total_s": round(total, 3),
        "decode_tok_s": round((n_tokens - 1) / decode_time, 2) if n_tokens > 1 else 0.0,
        "wall_tok_s": round(n_tokens / total, 2) if total > 0 else 0.0,
    }


def _measure_fallback(prompt: str, model: str, max_tokens: int, timeout: int, error: str) -> dict:
    """Non-streaming fallback: report wall tok/s (includes prefill) + the error note."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE,
        "max_tokens": max_tokens,
        "stream": False,
    }
    t0 = time.monotonic()
    try:
        resp = requests.post(
            f"{OMLX_URL}/v1/chat/completions", json=payload, timeout=timeout,
            headers=AUTH_HEADERS,
        )
        resp.raise_for_status()
        body = resp.json()
        n_tokens = body.get("usage", {}).get("completion_tokens", 0)
    except requests.RequestException as exc:
        return {"error": f"{error}; fallback failed: {exc}", "n_tokens": 0}
    total = time.monotonic() - t0
    return {
        "error": error,
        "n_tokens": n_tokens,
        "total_s": round(total, 3),
        "wall_tok_s": round(n_tokens / total, 2) if total > 0 else 0.0,
    }


def measure_batch(model: str, label: str, max_tokens: int, n_prompts: int, timeout: int) -> None:
    """Run the frozen batch and append labelled aggregate + per-prompt rows to the results file."""
    results_path = RESULTS_DEFAULT
    rows = []
    for p in frozen_prompts(n_prompts):
        r = measure_one(p, model, max_tokens, timeout)
        r.update({"label": label, "model": model, "ts": time.strftime("%F %T")})
        rows.append(r)
        print(f"[{label}] {r.get('decode_tok_s', r.get('wall_tok_s', 0))} tok/s "
              f"(ttft {r.get('ttft_s', '-')}s, {r.get('n_tokens')} tok)")
    decodes = [r["decode_tok_s"] for r in rows if r.get("decode_tok_s")]
    if decodes:
        print(f"[{label}] mean decode {statistics.mean(decodes):.2f} tok/s "
              f"(median {statistics.median(decodes):.2f}, n={len(decodes)})")
    # Crash-safe append (C6): read, extend, rewrite via tempfile+replace.
    existing = []
    if results_path.exists():
        with open(results_path) as f:
            existing = [json.loads(l) for l in f if l.strip()]
    existing.extend(rows)
    tmp = results_path.with_suffix(results_path.suffix + ".tmp")
    with open(tmp, "w", encoding='utf-8') as f:
        for r in existing:
            f.write(json.dumps(r) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, results_path)
    print(f"[measure] appended {len(rows)} rows -> {results_path}")


def compare(label_a: str, label_b: str) -> None:
    """Compare two labelled runs: mean/median decode tok/s and the ratio (the verdict)."""
    results_path = RESULTS_DEFAULT
    if not results_path.exists():
        print(f"[compare] no results at {results_path}")
        return
    with open(results_path) as f:
        rows = [json.loads(l) for l in f if l.strip()]
    for label in (label_a, label_b):
        decodes = [r["decode_tok_s"] for r in rows if r.get("label") == label and r.get("decode_tok_s")]
        walls = [r["wall_tok_s"] for r in rows if r.get("label") == label and r.get("wall_tok_s")]
        if not decodes and walls:
            decodes = walls  # fallback: wall tok/s (includes prefill)
        if decodes:
            print(f"[{label}] mean {statistics.mean(decodes):.2f} tok/s "
                  f"(median {statistics.median(decodes):.2f}, n={len(decodes)})")
        else:
            print(f"[{label}] no measurable rows")
    a = [r["decode_tok_s"] or r.get("wall_tok_s", 0) for r in rows if r.get("label") == label_a]
    b = [r["decode_tok_s"] or r.get("wall_tok_s", 0) for r in rows if r.get("label") == label_b]
    if a and b and statistics.mean(a) > 0:
        ratio = statistics.mean(b) / statistics.mean(a)
        verdict = "WIN" if ratio > 1.03 else ("LOSS" if ratio < 0.97 else "NEUTRAL")
        print(f"[compare] {label_b}/{label_a} = {ratio:.2f}x -> {verdict} "
              f"(D-332: community-benchmark-first — adopt MTP only if WIN on THIS M1 Max)")


def main() -> None:
    ap = argparse.ArgumentParser(description="MTP A/B decode-throughput instrument (D-293 re-scope).")
    ap.add_argument("--toggle", choices=["on", "off"], help="patch mtp_enabled + reload oMLX")
    ap.add_argument("--measure", action="store_true", help="run the frozen batch, append labelled rows")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"), help="compare two labels (B/A ratio)")
    ap.add_argument("--model", default=GEN_MODEL, help=f"target model (default from config: {GEN_MODEL})")
    ap.add_argument("--label", help="run label for --measure (e.g. mtp_off / mtp_on)")
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--n-prompts", type=int, default=DEFAULT_N_PROMPTS)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--settings-path", type=Path, default=MODEL_SETTINGS_DEFAULT)
    args = ap.parse_args()

    if args.toggle:
        toggle_mtp(args.model, args.toggle == "on", args.settings_path)
        reload_omlx()
    if args.measure:
        if not args.label:
            ap.error("--measure requires --label")
        measure_batch(args.model, args.label, args.max_tokens, args.n_prompts, args.timeout)
    if args.compare:
        compare(args.compare[0], args.compare[1])
    if not (args.toggle or args.measure or args.compare):
        ap.print_help()


if __name__ == "__main__":
    main()
