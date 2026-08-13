#!/usr/bin/env python3
"""
omlx_wired_stress.py — OMLX wired-memory leak stress test (G10 / P0.0 / D2020 Layer 1).
========================================================================================
Authority: D2020 (3-layer memory defense), P0.0, BUG-017, GitHub #2184, GitHub #702

Purpose: Detect OMLX kernel-level wired-memory leaks BEFORE a 26h pipeline run.

A wired-memory leak (GitHub #2184) is unrecoverable without reboot — macOS jetsam
kills OMLX and the leaked wired pages are NOT reclaimed by the kernel. The existing
defenses do not cover this:
  - memory_guard.py  → pre-flight check of *available* memory (not wired growth)
  - stress_test.py   → chat health/latency at 50/1K/5K chars (not memory leak)
  - omlx_watchdog.py → OMLX RSS trend monitor (D2027, restarts on +2GB)

This test implements D2020 Layer 1: N consecutive sustained inference rounds while
monitoring `vm_stat` "Pages wired down" (system wired memory, per spec — not RSS).

Kill criteria (D2020 Layer 1):
  - Cumulative wired growth > growth_threshold_pct (default 10%)  → FAIL (leak)
  - Any round with an HTTP error or timeout                        → FAIL (infra)
  - Per-round wired growth > round_trend_gb (default 2GB)          → WARN (BUG-017)

Config (C12): config/pipeline_config.yaml → omlx_wired_stress section.
Env overrides: MAXWELL_WIRED_STRESS_{ROUNDS,PROMPTS_PER_ROUND,PROMPT_SIZE_CHARS,
  MAX_TOKENS,GROWTH_THRESHOLD_PCT,ROUND_TREND_GB,PER_REQUEST_TIMEOUT,MODEL}

Usage:
    python3 pipeline/omlx_wired_stress.py                # full test (default config)
    python3 pipeline/omlx_wired_stress.py --rounds 3 --prompts-per-round 10
    python3 pipeline/omlx_wired_stress.py --json         # emit machine-readable report
    python3 pipeline/omlx_wired_stress.py --baseline-only  # just record wired baseline

Exit 0 = PASS (no leak detected), Exit 1 = FAIL (leak or infra unhealthy).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

from pipeline.pipeline_paths import GEN_MODEL, OMLX_API_KEY, OMLX_URL

_CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "pipeline_config.yaml"

_PAGE_SIZE_DEFAULT = 16384  # macOS page size fallback (overridden by vm_stat output)


def _load_config() -> dict:
    """Load the omlx_wired_stress section from pipeline_config.yaml (C12)."""
    import yaml
    with open(_CFG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("omlx_wired_stress", {}) or {}


def _cfg_value(cfg: dict, key: str, default, cast=None):
    """Resolve a config value with MAXWELL_WIRED_STRESS_* env override."""
    env = f"MAXWELL_WIRED_STRESS_{key.upper()}"
    raw = os.environ.get(env)
    val = raw if raw is not None else cfg.get(key, default)
    return cast(val) if cast is not None else val


def _wired_gb() -> float:
    """Measure system wired memory (GB) via `vm_stat` "Pages wired down".

    Returns -1.0 if vm_stat is unavailable or unparseable (non-fatal — caller
    must decide how to handle an unmeasurable baseline).
    """
    try:
        result = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return -1.0
        page_size = _PAGE_SIZE_DEFAULT
        wired_pages = 0
        for line in result.stdout.splitlines():
            if ":" not in line:
                continue
            key, val = line.rsplit(":", 1)
            key = key.strip()
            try:
                n = int(val.strip().rstrip("."))
            except ValueError:
                continue
            if key == "page size of":
                page_size = n
            elif key == "Pages wired down":
                wired_pages = n
        return (wired_pages * page_size) / (1024 ** 3)
    except Exception as e:  # noqa: BLE001 — measurement is best-effort, must not crash the gate
        print(f"  ⚠️  vm_stat unavailable ({type(e).__name__}: {e})")
        return -1.0


def _send_one(model: str, prompt: str, max_tokens: int, timeout: int) -> tuple[float, str | None]:
    """Send a single chat request. Returns (elapsed_s, error_or_None)."""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Respond concisely."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {OMLX_API_KEY}"}
        resp = requests.post(
            f"{OMLX_URL}/v1/chat/completions",
            json=body,
            headers=headers,
            timeout=timeout,
        )
        elapsed = time.time() - start
        if resp.status_code == 200:
            return elapsed, None
        return elapsed, f"HTTP {resp.status_code}: {resp.text[:120]}"
    except requests.Timeout:
        return time.time() - start, f"TIMEOUT after {timeout}s"
    except Exception as e:  # noqa: BLE001 — per-request errors are collected, not fatal
        return time.time() - start, str(e)[:200]


def _build_prompt(size_chars: int) -> str:
    """Build a prompt of ~size_chars characters (pipeline-realistic filler)."""
    base = "The convergent principle framework examines how reusable mechanisms "
    base += "operate across distinct domains, including their boundary conditions, "
    base += "failure modes, and the structural isomorphism between fields. "
    repeats = max(1, size_chars // len(base))
    return (base * repeats)[:size_chars]


def run_wired_stress(
    rounds: int,
    prompts_per_round: int,
    prompt_size_chars: int,
    max_tokens: int,
    growth_threshold_pct: float,
    round_trend_gb: float,
    timeout: int,
    model: str | None,
    verbose: bool = True,
) -> dict:
    """Run the wired-memory leak stress test and return a structured report."""
    model = model or GEN_MODEL
    report: dict = {
        "model": model,
        "rounds": rounds,
        "prompts_per_round": prompts_per_round,
        "baseline_gb": None,
        "final_gb": None,
        "cumulative_growth_pct": None,
        "per_round_gb": [],
        "per_round_errors": [],
        "verdict": "UNKNOWN",
        "warnings": [],
    }

    # 1. Warm-up: ensure model is loaded BEFORE measuring baseline.
    if verbose:
        print(f"🔥 Warm-up request (model={model})...")
    _, warm_err = _send_one(model, _build_prompt(prompt_size_chars), max_tokens, timeout)
    if warm_err is not None:
        report["verdict"] = "FAIL_INFRA"
        report["warnings"].append(f"warm-up failed: {warm_err}")
        if verbose:
            print(f"  ❌ Warm-up failed: {warm_err}")
        return report

    # 2. Baseline wired memory.
    baseline = _wired_gb()
    if baseline < 0:
        report["verdict"] = "UNMEASURABLE"
        if verbose:
            print("  ❌ Could not measure baseline wired memory — cannot run leak test")
        return report
    report["baseline_gb"] = round(baseline, 2)
    if verbose:
        print(f"📏 Baseline wired: {baseline:.2f} GB")

    # 3. Sustained rounds.
    prev = baseline
    infra_failed = False
    for r in range(1, rounds + 1):
        errs = 0
        t0 = time.time()
        for _ in range(prompts_per_round):
            _, err = _send_one(model, _build_prompt(prompt_size_chars), max_tokens, timeout)
            if err is not None:
                errs += 1
                if verbose:
                    print(f"  ❌ round {r}: {err}")
        elapsed = time.time() - t0
        wired = _wired_gb()
        if wired < 0:
            wired = prev  # keep last known; measurement hiccup is not a leak
        report["per_round_gb"].append(round(wired, 2))
        report["per_round_errors"].append(errs)

        delta = wired - prev
        if errs > 0:
            infra_failed = True
        if delta > round_trend_gb:
            report["warnings"].append(
                f"round {r}: wired grew {delta:.2f} GB (>{round_trend_gb} GB trend threshold)"
            )
        if verbose:
            status = "✅" if errs == 0 else f"❌ ({errs} errors)"
            print(
                f"  Round {r}/{rounds}: {prompts_per_round} reqs in {elapsed:.1f}s, "
                f"wired {wired:.2f} GB (Δ {delta:+.2f} GB) {status}"
            )
        prev = wired

    report["final_gb"] = round(prev, 2)
    report["cumulative_growth_pct"] = round(
        (prev - baseline) / baseline * 100.0, 2
    )

    # 4. Verdict.
    if infra_failed:
        report["verdict"] = "FAIL_INFRA"
    elif report["cumulative_growth_pct"] > growth_threshold_pct:
        report["verdict"] = "FAIL_LEAK"
        report["warnings"].append(
            f"cumulative wired growth {report['cumulative_growth_pct']:.2f}% "
            f"exceeds threshold {growth_threshold_pct:.1f}%"
        )
    else:
        report["verdict"] = "PASS"

    return report


def main() -> int:
    """CLI entry point."""
    cfg = _load_config()
    parser = argparse.ArgumentParser(
        description="OMLX wired-memory leak stress test (G10 / P0.0 / D2020 Layer 1)"
    )
    parser.add_argument("--rounds", type=int,
                        default=int(_cfg_value(cfg, "rounds", 5, int)))
    parser.add_argument("--prompts-per-round", type=int,
                        default=int(_cfg_value(cfg, "prompts_per_round", 20, int)))
    parser.add_argument("--prompt-size-chars", type=int,
                        default=int(_cfg_value(cfg, "prompt_size_chars", 1000, int)))
    parser.add_argument("--max-tokens", type=int,
                        default=int(_cfg_value(cfg, "max_tokens", 128, int)))
    parser.add_argument("--growth-threshold-pct", type=float,
                        default=float(_cfg_value(cfg, "growth_threshold_pct", 10.0, float)))
    parser.add_argument("--round-trend-gb", type=float,
                        default=float(_cfg_value(cfg, "round_trend_gb", 2.0, float)))
    parser.add_argument("--timeout", type=int,
                        default=int(_cfg_value(cfg, "per_request_timeout", 30, int)))
    parser.add_argument("--model", type=str,
                        default=_cfg_value(cfg, "model", None))
    parser.add_argument("--baseline-only", action="store_true",
                        help="Only measure and print current wired memory, then exit")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON report to stdout")
    args = parser.parse_args()

    if args.baseline_only:
        wired = _wired_gb()
        print(json.dumps({"wired_gb": round(wired, 2)}))
        return 0 if wired >= 0 else 1

    report = run_wired_stress(
        rounds=args.rounds,
        prompts_per_round=args.prompts_per_round,
        prompt_size_chars=args.prompt_size_chars,
        max_tokens=args.max_tokens,
        growth_threshold_pct=args.growth_threshold_pct,
        round_trend_gb=args.round_trend_gb,
        timeout=args.timeout,
        model=args.model,
        verbose=not args.json,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "=" * 70)
        print(f"   Verdict: {report['verdict']}")
        print(f"   Baseline wired: {report['baseline_gb']} GB")
        print(f"   Final wired:    {report['final_gb']} GB")
        print(f"   Cumulative growth: {report['cumulative_growth_pct']}% "
              f"(threshold {args.growth_threshold_pct}%)")
        if report["warnings"]:
            print("   Warnings:")
            for w in report["warnings"]:
                print(f"     ⚠️  {w}")
        print("=" * 70)

    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
