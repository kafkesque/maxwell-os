#!/usr/bin/env python3
"""Count SCORED rows per suite for the live model portfolio (M2: done = a counted artifact).

WHY: a raw line count lets three kinds of non-measurement inflate a suite and hide a missing
cell: transport errors (err), preflight-invalid cells (na), and models that are no longer in the
portfolio. This counts only rows that are genuine measurements by models in
environment.expected_models, and it fails if any expected model contributed ZERO rows.

    python3 scripts/check_suite_coverage.py --suite toolcalling --min 120
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from bench_preflight import load_config  # noqa: E402


def main() -> int:
    """Report scored rows per expected model. Returns 0 when coverage is complete."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--min", type=int, required=True)
    ap.add_argument("--allow-missing", default="", help="comma list of models whose absence is acceptable (NA cells)")
    args = ap.parse_args()

    cfg = load_config()
    expected = list(cfg["environment"]["expected_models"])
    allowed = {m.strip() for m in args.allow_missing.split(",") if m.strip()}
    path = REPO / str(cfg["stale_row_guards"]["checkpoint"])

    scored: Counter = Counter()
    skipped: Counter = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("suite") != args.suite or r.get("model") not in expected:
            continue
        key = str(r.get("model"))
        if r.get("err") or r.get("na") or str(r.get("id", "")).startswith("__preflight__"):
            skipped[key] += 1
            continue
        scored[key] += 1

    total = sum(scored.values())
    print("suite=" + args.suite + "  scored=" + str(total) + "  min=" + str(args.min))
    missing: list[str] = []
    for m in expected:
        n = scored.get(m, 0)
        tag = "" if n else (" (NA or err rows only, allowed)" if m in allowed else "  <-- NO SCORED ROWS")
        if not n and m not in allowed:
            missing.append(m)
        print("   " + m[:38].ljust(38) + str(n).rjust(4) + " scored" + tag)
    if total < args.min:
        print("  FAIL: " + str(total) + " < " + str(args.min))
        return 1
    if missing:
        print("  FAIL: no scored rows for " + ", ".join(missing))
        return 1
    print("  PASS: coverage complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
