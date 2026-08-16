#!/usr/bin/env python3
"""A/B test harness: grammar-constrained decoding ON vs OFF (D2385).

Samples N FBs from the S2 checkpoint and runs the real S4 ``merged_cribs_classify``
path (VERIFY_MODEL = gpt-oss-20b, ``Reasoning: low``, ``response_format=json_object``)
for each. Records JSON validity, latency, and status so the OFF (xgrammar absent) and
ON (xgrammar installed) states can be diffed directly.

Run the SAME sample once in each state, then diff the two JSON summaries:

    python3 tools/ab_test_grammar.py --n 30 --out ab_off.json   # before reinstall
    brew reinstall omlx --with-grammar                          # install xgrammar
    # restart OMLX (launchctl kickstart -k gui/$UID/com.maxwell.omlx)
    python3 tools/ab_test_grammar.py --n 30 --out ab_on.json    # after reinstall

Note: do NOT run while another stage is using OMLX (it competes for the single
resident model and would distort latency).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure `pipeline` is importable when run as `python3 tools/ab_test_grammar.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.pipeline_paths import S2_DIR, STAGE2_CHECKPOINT
from pipeline.stage4_merged_call import merged_cribs_classify


def _resolve_checkpoint() -> Path:
    """Return the active S2 checkpoint (auto-detect run-id if needed)."""
    if STAGE2_CHECKPOINT.exists():
        return STAGE2_CHECKPOINT
    candidates = sorted(S2_DIR.glob("*/checkpoint.jsonl"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else STAGE2_CHECKPOINT


def sample_fbs(n: int) -> list[dict]:
    """Return n FBs sampled evenly across the S2 checkpoint."""
    checkpoint = _resolve_checkpoint()
    fbs = [json.loads(line) for line in checkpoint.read_text().splitlines() if line.strip()]
    step = max(1, len(fbs) // n)
    return fbs[::step][:n]


def run_one(fb: dict) -> dict:
    """Run the real S4 merged CRIBS+classification call for one FB (D2385).

    Uses ``merged_cribs_classify`` so the model is pinned to VERIFY_MODEL
    (gpt-oss-20b, same as S4) with the correct ``Reasoning: low`` prefix and
    ``response_format=json_object`` — the exact path the grammar flag governs.
    """
    start = time.monotonic()
    try:
        result = merged_cribs_classify(fb)
        valid = isinstance(result, dict) and bool(result.get("application"))
        status = "ok" if valid else "sparse/empty-application"
    except Exception as e:  # noqa: BLE001 — capture any failure for the A/B record
        valid = False
        status = f"{type(e).__name__}: {str(e)[:80]}"
    latency = time.monotonic() - start
    return {
        "name": fb.get("name"),
        "valid_json": valid,
        "latency_s": round(latency, 1),
        "status": status,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="A/B test: grammar-constrained decoding ON vs OFF (D2385)")
    ap.add_argument("--n", type=int, default=30, help="sample size (default 30)")
    ap.add_argument("--out", default=None, help="write JSON summary to this path")
    args = ap.parse_args()

    fbs = sample_fbs(args.n)
    print(f"Running {len(fbs)} FBs through call_omlx_json (response_format=json_object)...")
    results = [run_one(fb) for fb in fbs]

    n_ok = sum(1 for r in results if r["valid_json"])
    avg_lat = sum(r["latency_s"] for r in results) / max(len(results), 1)
    summary = {
        "n": len(results),
        "valid_json": n_ok,
        "valid_rate": round(n_ok / max(len(results), 1), 4),
        "avg_latency_s": round(avg_lat, 1),
        "results": results,
    }
    print(f"valid JSON: {n_ok}/{len(results)} ({n_ok / max(len(results), 1):.0%}) | avg latency {avg_lat:.1f}s")
    for r in results:
        if not r["valid_json"]:
            print(f"  ❌ {r['name'][:40]:40} -> {r['status']}")
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
